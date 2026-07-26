# Model Comparison — Accuracy vs. Interpretability

## The metrics (held-out test set, 2,458 players, stratified, seed 42)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Predict "nobody leaves" (baseline) | 0.632 | 0.000 | 0.000 | 0.000 | 0.500 |
| Logistic regression (balanced) | 0.607 | 0.474 | 0.599 | 0.529 | 0.641 |
| **Gradient boosting (balanced)** | **0.666** | **0.547** | 0.535 | **0.541** | **0.690** |

## Why accuracy alone would be a lie

36.8% of in-scope players churned, so a model that predicts *nobody ever
leaves* scores 63.2% accuracy while catching **zero** departures — it would
look "better" than the logistic regression while being operationally useless.
That's why the table leads with precision/recall/F1/ROC-AUC and keeps the
do-nothing baseline visible: every real model must justify itself against it
on the metrics that count catches, not agreement.

Note the logistic regression's accuracy (0.607) is *below* the baseline —
and that's fine. `class_weight='balanced'` deliberately spends accuracy on
the majority class to buy recall on the minority class (0.599 vs 0.000).
Which trade is right is a business question, not a modeling one.

## Reading the two models

- **Gradient boosting wins on ranking power**: +5 AUC points (0.690 vs
  0.641) and better precision at similar recall. It finds interactions the
  linear model can't — e.g., high wage *relative to squad* matters differently
  for a 23-year-old forward than a 33-year-old goalkeeper.
- **Logistic regression wins on explainability**: its standardized
  coefficients read as sentences. Higher market value → *stays* (clubs
  protect valuable contracted assets). Bigger squad → *stays*. Forward →
  *leaves*. Paid above squad median → *leaves*. Every claim is checkable
  against the raw crosstabs in `output/driver_analysis.md`.

## Recommendation to a business stakeholder

**Use the gradient boosting model as the ranking engine, and the logistic
regression + crosstabs as the explanation layer.** Retention decisions here
are made player-by-player by humans (sporting director, agent conversations);
the model's job is to order the watchlist so those humans spend time on the
right names, and a 5-point AUC edge is real triage value at that job. But no
renewal conversation should ever be justified with "the black box said so" —
the linear coefficients and churn-rate crosstabs supply the *why* ("he's our
3rd-highest earner but 9th-ranked player; that profile leaves 42% of the
time"). Two models, two jobs — that beats forcing one model to do both badly.

## Honest ceiling — and what would raise it

An AUC of 0.69 is a modest, honest number, and it should be: player
departures hinge on unobservables this snapshot simply lacks — most of all
**contract expiry dates** (absent from the FIFA 18 scrape), plus minutes
played, injuries, manager changes, and agent dynamics. The single highest-ROI
data investment would be joining contract-expiry data: "12 months left,
underpaid vs squad, top-3 rated" is the classic pre-departure profile, and
the model currently has to infer it indirectly. Claiming 0.9 AUC on this
feature set would be a red flag, not an achievement.
