"""Stage 4 — Model: logistic regression baseline vs gradient-boosted trees.

Why these two: the comparison the business actually faces — an interpretable
model whose coefficients a sporting director can read, versus a stronger
learner that trades that transparency for ranking power. The metrics table
and the recommendation live in docs/model_comparison.md.

Why not accuracy alone: churn is ~30/70 imbalanced, so "nobody ever leaves"
scores ~70% while catching zero departures. Precision/recall/F1/ROC-AUC are
reported and the choice is argued in the docs.
"""

import json
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "churn.duckdb"
OUT = ROOT / "output"

NUMERIC = ["age", "overall", "potential", "growth_headroom", "wage_eur", "value_eur",
           "squad_size", "club_avg_overall", "overall_vs_club_avg",
           "overall_rank_in_club", "wage_rank_in_club", "wage_to_club_median",
           "is_top3_in_club"]
CATEGORICAL = ["position_group"]
SEED = 42


def metrics_row(y_true, y_pred, y_prob) -> dict:
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 3),
        "precision": round(precision_score(y_true, y_pred), 3),
        "recall": round(recall_score(y_true, y_pred), 3),
        "f1": round(f1_score(y_true, y_pred), 3),
        "roc_auc": round(roc_auc_score(y_true, y_prob), 3),
    }


def run() -> list[str]:
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB))
    # ORDER BY id: DuckDB's parallel CSV reader doesn't guarantee row order,
    # and an unstable order silently changes the train/test split between runs.
    df = con.execute("SELECT * FROM features ORDER BY id").df()

    X = df[NUMERIC + CATEGORICAL]
    y = df["churned"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)

    # Logistic regression: impute → scale → OHE → fit. class_weight='balanced'
    # counters the 30/70 imbalance instead of letting the model chase accuracy.
    lr = Pipeline([
        ("prep", ColumnTransformer([
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                              ("sc", StandardScaler())]), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ])),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
    ])
    lr.fit(X_tr, y_tr)

    # Gradient boosting: handles NaNs and categoricals natively, learns interactions.
    hgb = Pipeline([
        ("prep", ColumnTransformer([
            ("num", "passthrough", NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
        ])),
        ("clf", HistGradientBoostingClassifier(class_weight="balanced", random_state=SEED)),
    ])
    hgb.fit(X_tr, y_tr)

    results = {}
    for label, model in [("logistic_regression", lr), ("gradient_boosting", hgb)]:
        results[label] = metrics_row(y_te, model.predict(X_te), model.predict_proba(X_te)[:, 1])
    results["baseline_predict_no_churn"] = {
        "accuracy": round((y_te == 0).mean(), 3),
        "precision": 0.0, "recall": 0.0, "f1": 0.0, "roc_auc": 0.5,
    }
    results["meta"] = {"n_train": len(X_tr), "n_test": len(X_te),
                       "churn_rate": round(float(y.mean()), 3), "seed": SEED}
    (OUT / "model_metrics.json").write_text(json.dumps(results, indent=2))

    # Interpretability artifacts: standardized LR coefficients (direction + size)
    # and permutation importance for the boosted model (what it actually leans on).
    feat_names = NUMERIC + list(
        lr.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(CATEGORICAL))
    coefs = (pd.DataFrame({"feature": feat_names,
                           "coefficient": lr.named_steps["clf"].coef_[0]})
             .sort_values("coefficient", key=abs, ascending=False))
    coefs.to_csv(OUT / "lr_coefficients.csv", index=False)

    perm = permutation_importance(hgb, X_te, y_te, n_repeats=10,
                                  random_state=SEED, scoring="roc_auc")
    imp = (pd.DataFrame({"feature": NUMERIC + CATEGORICAL,
                         "importance": perm.importances_mean})
           .sort_values("importance", ascending=False))
    imp.to_csv(OUT / "hgb_permutation_importance.csv", index=False)

    top = imp.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(top["feature"], top["importance"], color="#4C78A8")
    ax.set_xlabel("Permutation importance (ROC-AUC drop when shuffled)")
    ax.set_title("What drives player churn — gradient boosting, test set")
    fig.tight_layout()
    fig.savefig(OUT / "feature_importance.png", dpi=150)

    # Business drivers: churn-rate crosstabs a non-technical reader can act on.
    lines = ["# Churn drivers — plain-language crosstabs", "",
             f"Base churn rate: **{y.mean():.1%}** of the {len(df):,} in-scope players.", ""]
    for col, title in [("age_band", "Age band"), ("position_group", "Position"),
                       ("is_top3_in_club", "Top-3 player in squad (by rating)")]:
        tab = df.groupby(col)["churned"].agg(["mean", "count"])
        lines += [f"## {title}", "", "| Group | Churn rate | Players |", "|---|---|---|"]
        lines += [f"| {g} | {r['mean']:.1%} | {int(r['count']):,} |" for g, r in tab.iterrows()]
        lines.append("")
    df["wage_pos"] = pd.qcut(df["wage_to_club_median"], 4,
                             labels=["bottom 25%", "lower mid", "upper mid", "top 25%"])
    tab = df.groupby("wage_pos", observed=True)["churned"].agg(["mean", "count"])
    lines += ["## Wage position within squad (vs club median)", "",
              "| Quartile | Churn rate | Players |", "|---|---|---|"]
    lines += [f"| {g} | {r['mean']:.1%} | {int(r['count']):,} |" for g, r in tab.iterrows()]
    (OUT / "driver_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    con.close()

    lr_m, gb_m = results["logistic_regression"], results["gradient_boosting"]
    return [
        f"**Trained both models on {len(X_tr):,} players, evaluated on a held-out {len(X_te):,} (stratified, seed {SEED})** — "
        f"LR: AUC {lr_m['roc_auc']}, recall {lr_m['recall']} · GBM: AUC {gb_m['roc_auc']}, recall {gb_m['recall']} "
        f"(vs no-churn baseline accuracy {results['baseline_predict_no_churn']['accuracy']}). "
        "Full table in `output/model_metrics.json`; interpretation in `docs/model_comparison.md`.",
    ]


if __name__ == "__main__":
    print("\n".join(run()))
