# Business Impact — What a Club Does With This

*(All money figures below are labeled assumptions for a mid-table top-flight
club, not citations — they exist so the logic can be stress-tested with a
club's real numbers.)*

## What changes operationally

1. **A ranked retention watchlist, refreshed each window.** The model scores
   every squad member; the sporting director reviews the top of the list, not
   the whole squad. At the model's measured precision (0.547), roughly every
   second flagged player genuinely departs — enough signal to redirect
   scarce renewal-conversation time, nowhere near enough to automate decisions.
2. **Sell-don't-lose.** A high-risk player the club can't or won't retain
   should be sold *while a fee exists*. A departure the club sees coming is a
   transfer fee; one it doesn't is often a cut-price sale or a free. The
   driver profile to watch (from `output/driver_analysis.md`): **forwards
   (44% churn), top-3-rated players (42%), and top-quartile earners relative
   to squad median (42%)** — star drain, not dead-wood clearance.
3. **Succession scouting starts earlier.** High-risk starters get a
   replacement shortlist before the window opens, not after the player is gone.

## The cost-benefit sketch

| Input (assumption) | Value |
|---|---|
| Replacement cost for a first-team starter (fee + agent + signing bonus) | €8M |
| Discount on a forced/late sale vs. a planned one | 30–50% |
| Cost of an early renewal (wage premium to re-sign 12 months early) | +10–15% on one salary |
| Cost to run this pipeline | ~€0 (open data, embedded DB, laptop compute) |

At those assumptions, converting **one** unanticipated star departure per
season into either a planned sale (recovering, say, 40% of €8M ≈ €3.2M) or a
successful early renewal pays for an analytics function many times over. The
model doesn't need to be an oracle — at 0.535 recall it sees roughly half of
departures coming, and the status quo it replaces is gut feel.

## What this is NOT

- Not a transfer-fee predictor and not an automation of renewal decisions —
  it triages human attention.
- Not causal: "paid above squad median → 42% churn" flags a risk profile;
  it doesn't say a raise causes departures.
- The same framework is domain-portable: swap players for subscribers and
  clubs for plans, and this is the standard telco churn playbook — the
  dataset is football, the discipline is identical.
