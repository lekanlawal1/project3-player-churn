# Case Study - FIFA Player Churn: End-to-End Pipeline + Prediction

**The problem.** Football clubs lose key players the way subscription
businesses lose customers - predictably, in hindsight. Using two seasons of
FIFA game data (~18K players each), I built an end-to-end pipeline that
predicts which players will leave their club before the next season.

**The pipeline.** Raw CSVs (wages as "€565K" strings, duplicate IDs, drifting
club names) are ingested untouched into DuckDB, cleaned in Python with every
decision logged, then transformed in versioned SQL: a majority-vote entity
resolution that caught 92 club renames masquerading as mass transfers
(cutting phantom churn by 8 points), a leakage-safe label join, and
window-function features that capture each player's standing in their squad.
One command reproduces everything from raw data to trained models.

**The models.** An interpretable logistic regression versus gradient
boosting, scored on precision, recall, F1, and ROC-AUC - never accuracy
alone, because with 36.8% churn, "nobody leaves" scores 63% while catching
nothing. Gradient boosting wins ranking power (AUC 0.690); the regression
supplies the *why*: forwards, top-3-rated players, and above-median earners
are the flight risks.

**The recommendation.** Boosted model ranks the retention watchlist; linear
coefficients and churn crosstabs justify each conversation - because a
sporting director acts on reasons, not risk scores.
