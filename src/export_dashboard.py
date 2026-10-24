"""Stage 5 - Dashboard export: score every player, ship data to the static dashboard.

Honesty rule for displayed risk scores: they are OUT-OF-FOLD predictions
(5-fold cross_val_predict), so no player's shown risk comes from a model that
saw that player in training. Displaying in-sample scores would flatter the
model exactly where the dashboard makes it easiest to check (every row shows
predicted risk next to what actually happened).

Output: dashboard/data.js - a single `const DATA = {...}` payload inlined the
same way Project 1 ships its dashboard data (works from file:// and Pages,
no fetch, no server).
"""

import json
from pathlib import Path

import duckdb
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from train import CATEGORICAL, NUMERIC, SEED

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "churn.duckdb"
OUT_JS = ROOT / "dashboard" / "data.js"


def run() -> list[str]:
    con = duckdb.connect(str(DB))
    df = con.execute("SELECT * FROM features ORDER BY id").df()
    con.close()

    model = Pipeline([
        ("prep", ColumnTransformer([
            ("num", "passthrough", NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
        ])),
        ("clf", HistGradientBoostingClassifier(class_weight="balanced", random_state=SEED)),
    ])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    df["risk"] = cross_val_predict(model, df[NUMERIC + CATEGORICAL], df["churned"],
                                   cv=cv, method="predict_proba")[:, 1]

    # Per-player rows for the watchlist (array-of-arrays keeps the payload small)
    cols = ["name", "club", "age", "position_group", "overall", "wage_eur", "risk", "churned"]
    players = df[cols].copy()
    players["wage_eur"] = players["wage_eur"].fillna(0).astype(int)
    players["risk"] = players["risk"].round(3)
    rows = players.values.tolist()

    # Calibration by risk decile: does predicted risk track reality?
    df["decile"] = pd.qcut(df["risk"], 10, labels=False)
    calib = (df.groupby("decile").agg(pred=("risk", "mean"), actual=("churned", "mean"))
               .round(3).reset_index().values.tolist())

    def crosstab(col):
        t = df.groupby(col)["churned"].agg(["mean", "count"]).round(3).reset_index()
        return t.values.tolist()

    df["wage_q"] = pd.qcut(df["wage_to_club_median"], 4,
                           labels=["bottom 25%", "lower mid", "upper mid", "top 25%"])
    imp = pd.read_csv(ROOT / "output" / "hgb_permutation_importance.csv").round(4)
    metrics = json.loads((ROOT / "output" / "model_metrics.json").read_text())

    payload = {
        "meta": {
            "n_players": len(df),
            "churn_rate": round(float(df["churned"].mean()), 3),
            "auc": metrics["gradient_boosting"]["roc_auc"],
            "renames_caught": 92,
            "clubs": sorted(df["club"].dropna().unique().tolist()),
        },
        "player_cols": cols,
        "players": rows,
        "calibration": calib,
        "by_age_band": crosstab("age_band"),
        "by_position": crosstab("position_group"),
        "by_wage_q": crosstab("wage_q"),
        "importance": imp.values.tolist(),
    }
    OUT_JS.parent.mkdir(exist_ok=True)
    OUT_JS.write_text("const DATA = " + json.dumps(payload) + ";", encoding="utf-8")
    kb = OUT_JS.stat().st_size // 1024
    return [f"**Exported dashboard/data.js ({kb} KB): out-of-fold risk scores for all "
            f"{len(df):,} players + aggregates** - every risk shown in the dashboard is a "
            "prediction from a model that never trained on that player (5-fold "
            "cross_val_predict); in-sample scores would flatter the model exactly where "
            "the UI invites checking predictions against actual outcomes."]


if __name__ == "__main__":
    print("\n".join(run()))
