# FIFA Player Churn - End-to-End Data Pipeline + Prediction Model

**Live dashboard:** https://lekanlawal1.github.io/project3-player-churn/ · **Stack:** Python (pandas) · DuckDB (SQL transformations) · scikit-learn · versioned SQL · Plotly.js

## Problem statement

Football clubs lose players the way subscription businesses lose customers - and usually see it coming only in hindsight. Joining two seasons of FIFA video-game rosters (FIFA 18 → FIFA 19, ~18K players each), this project predicts **which players will leave their club before next season**: the classic customer-churn problem (imbalanced binary classification, retention economics, "why is this one at risk?") wearing football boots. The pipeline takes genuinely raw data - wages as `€565K` display strings, duplicate IDs, club names that drift between editions - through ingestion, logged cleaning, and SQL transformation into two compared models.

## My approach

1. **Ingest** ([src/ingest.py](src/ingest.py)): both raw CSVs land in DuckDB as all-VARCHAR tables - a byte-faithful raw layer where no type was ever guessed by a CSV parser.
2. **Clean** ([src/clean.py](src/clean.py)): row-level fixes in Python - money-string parsing, duplicate-ID removal, type coercion - with every decision written to a generated [cleaning log](docs/cleaning_log.md), the same what-and-why format as Projects 1 and 2.
3. **Transform in SQL** ([sql/](sql/)): set-level logic lives in versioned `.sql` files run in order - **entity resolution** (01), the **leakage-safe label join** (02), and **feature engineering** with window functions and CASE bucketing (03). Squad-context features are the point: churn risk isn't who you are, it's where you stand in your squad's pecking order (`RANK() OVER (PARTITION BY club …)`).
4. **Model** ([src/train.py](src/train.py)): logistic regression (interpretable baseline) vs. gradient boosting (stronger learner), evaluated on precision/recall/F1/ROC-AUC against a visible do-nothing baseline.
5. **Interactive dashboard** ([dashboard/](dashboard/), [live](https://lekanlawal1.github.io/project3-player-churn/)): a static Plotly.js explorer - searchable retention watchlist showing every player's predicted risk **next to what actually happened**, churn-driver charts, and a risk-decile calibration check. Scores are out-of-fold (5-fold `cross_val_predict`), so no player is scored by a model that trained on them - in-sample scores would flatter the model exactly where the UI invites checking.

One command reproduces everything: see [Run it](#run-it). Architecture diagram: [docs/pipeline_architecture.md](docs/pipeline_architecture.md).

## Key decisions and why

- **This dataset, not another Superstore** - a deliberately different domain from Project 1's retail BI, and the mess is real: the headline data-quality finding was that club names drift between game editions ("Real Madrid CF" → "Real Madrid"), which a naive join counts as entire squads transferring. A **majority-vote entity resolution in SQL** (each FIFA 18 club maps to wherever most of its retained players "went") caught **92 pure renames and removed 8.4 points of phantom churn** (45.2% → 36.8%). Real transfers scatter; renames vote as a bloc.
- **DuckDB over a SQL server** - full analytical SQL (window functions, `MEDIAN`, `IS DISTINCT FROM`) embedded in-process against one file: nothing to install or host, one-command reproducible, and the SQL ports to Snowflake/BigQuery nearly unchanged if the data outgrew a laptop. The modern-data-stack trade, argued in [docs/pipeline_architecture.md](docs/pipeline_architecture.md).
- **Leakage rule** - features come *only* from the FIFA 18 snapshot; the FIFA 19 file contributes exactly one thing (next season's club, the label). Anything else would be information a squad planner couldn't have at decision time.
- **Never accuracy alone** - churn is 36.8%, so "nobody leaves" scores 63.2% accuracy while catching zero departures. Metrics and the accuracy-vs-interpretability call are in [docs/model_comparison.md](docs/model_comparison.md).
- **Two models, two jobs** - gradient boosting ranks the watchlist (AUC 0.690 vs 0.641); logistic regression + crosstabs explain it. A sporting director acts on reasons, not scores.

## Results

| Model | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| Baseline: predict "nobody leaves" | 0.00 | 0.00 | 0.00 | 0.500 |
| Logistic regression | 0.474 | 0.599 | 0.529 | 0.641 |
| **Gradient boosting** | **0.547** | 0.535 | **0.541** | **0.690** |

Top churn drivers, in plain language (full crosstabs in [output/driver_analysis.md](output/driver_analysis.md)):

1. **Forwards are the flight risks** - 44.3% churn vs 27.9% for goalkeepers.
2. **Star drain is real** - top-3-rated players in a squad churn *more* (41.5%) than the rest (35.7%).
3. **Paid above the squad, likelier to leave** - top wage quartile relative to club median churns 42.3% vs 32.4% for the bottom quartile.
4. **Ages 21–24 are peak departure years** (39.8%) - prime sell-window; veterans 33+ are the stickiest (31.8%).
5. **Market value protects** - higher-value players stay (clubs guard contracted assets); the strongest single coefficient in the linear model.

What a club should do with this - watchlist, sell-don't-lose, succession scouting, with the cost-benefit sketch: [docs/business_impact.md](docs/business_impact.md). Honest ceiling: AUC 0.69 is what this snapshot supports - the missing feature is contract expiry, and claiming more would be a red flag ([docs/model_comparison.md](docs/model_comparison.md)).

## Repo structure

```
data/raw/                  two seasons of raw player CSVs (immutable inputs)
data/processed/            DuckDB file + features.csv (git-ignored, regenerated)
src/ingest.py              raw CSVs → DuckDB, all VARCHAR
src/clean.py               logged row-level cleaning (money parsing, dedup, types)
sql/01_club_mapping.sql    entity resolution by majority vote (window functions)
sql/02_label.sql           leakage-safe churn label via cross-edition join
sql/03_features.sql        squad-context windows + CASE bucketing
src/train.py               LR vs GBM, imbalance-aware metrics, importances
src/export_dashboard.py    out-of-fold risk scores for every player → dashboard/data.js
src/run_pipeline.py        one-command orchestrator (also regenerates the cleaning log)
dashboard/index.html       interactive explorer (source of truth; root index.html mirrors it for Pages)
output/                    metrics.json · coefficients · importances · driver crosstabs · chart
docs/                      cleaning_log.md · pipeline_architecture.md · model_comparison.md ·
                           business_impact.md · case_study.md
```

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python src/run_pipeline.py
```

That's the whole pipeline: raw CSVs → DuckDB → cleaning (+ regenerated log) → SQL transforms → both models → metrics, importances, crosstabs, and the dashboard data. Deterministic end to end (seeded split, stable ordering); no API keys, no paid services, no server. After a re-run, sync the Pages mirror: `cp dashboard/index.html index.html && cp dashboard/data.js data.js`. The live dashboard is served by GitHub Pages from the repo root (`.nojekyll` disables Jekyll).

**Data sources:** FIFA 18 and FIFA 19 complete player datasets (SoFIFA scrapes, published on Kaggle and mirrored on GitHub) - public, free, and used here for a non-commercial portfolio demonstration.
