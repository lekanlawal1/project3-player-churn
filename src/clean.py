"""Stage 2 - Clean: typed, deduplicated tables from the raw layer.

Python owns *row-level* cleaning (string parsing, dedup, type coercion);
SQL owns *set-level* transformation (joins, windows, aggregation) in stage 3.
Every decision returns a log line rendered into docs/cleaning_log.md - the
same what-and-why format as Projects 1 and 2.

Leakage rule: model features may come ONLY from the FIFA 18 snapshot. The
FIFA 19 file contributes nothing but the player's next-season club (the label
source) - anything else from the "future" edition would be information a real
squad planner wouldn't have at decision time.
"""

import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "churn.duckdb"

# The 34 outfield/GK skill ratings in FIFA 18 (plain 0-99 integers as strings)
SKILL_COLS = [
    "Acceleration", "Aggression", "Agility", "Balance", "Ball control", "Composure",
    "Crossing", "Curve", "Dribbling", "Finishing", "Free kick accuracy", "GK diving",
    "GK handling", "GK kicking", "GK positioning", "GK reflexes", "Heading accuracy",
    "Interceptions", "Jumping", "Long passing", "Long shots", "Marking", "Penalties",
    "Positioning", "Reactions", "Short passing", "Shot power", "Sliding tackle",
    "Sprint speed", "Stamina", "Standing tackle", "Strength", "Vision", "Volleys",
]


def parse_money(s):
    """'€110.5M' → 110_500_000, '€565K' → 565_000, '€0' → 0, junk → None."""
    if not isinstance(s, str):
        return None
    m = re.fullmatch(r"€([\d.]+)([MK]?)", s.strip())
    if not m:
        return None
    return float(m.group(1)) * {"M": 1_000_000, "K": 1_000, "": 1}[m.group(2)]


def run() -> list[str]:
    con = duckdb.connect(str(DB))
    log = []
    f18 = con.execute("SELECT * FROM raw_fifa18").df()
    f19 = con.execute("SELECT * FROM raw_fifa19").df()

    # --- FIFA 18: the feature snapshot ---
    f18 = f18.drop(columns=[c for c in f18.columns
                            if c in ("column00", "") or c in ("Photo", "Flag", "Club Logo")])
    log.append("**Dropped surrogate index and URL columns (Photo, Flag, Club Logo)** - "
               "presentation assets, not signal; keeping them invites accidental joins on junk.")

    pos_rating_cols = [c for c in f18.columns if re.fullmatch(r"[A-Z]{2,3}", c) and c != "ID"]
    f18 = f18.drop(columns=pos_rating_cols)
    log.append(f"**Dropped {len(pos_rating_cols)} per-position rating columns (CAM, ST, …)** - "
               "they are formula-derived from the 34 base skills (values like '88+2'), so they add "
               "collinearity, parsing pain, and zero new information.")

    f18["ID"] = pd.to_numeric(f18["ID"], errors="coerce").astype("Int64")
    before = len(f18)
    f18 = f18.dropna(subset=["ID"])
    f18["Overall"] = pd.to_numeric(f18["Overall"], errors="coerce")
    f18 = (f18.sort_values("Overall", ascending=False)
              .drop_duplicates(subset="ID", keep="first"))
    log.append(f"**Removed {before - len(f18)} duplicate/invalid player IDs (kept highest Overall)** - "
               "the scrape occasionally lists a player twice mid-update; the higher-rated row is the "
               "later snapshot. Duplicate IDs would double-count players and corrupt the join to FIFA 19.")

    for col in ("Value", "Wage"):
        f18[col.lower() + "_eur"] = f18[col].map(parse_money)
    bad_money = int(f18["value_eur"].isna().sum() + f18["wage_eur"].isna().sum())
    f18 = f18.drop(columns=["Value", "Wage"])
    log.append(f"**Parsed Value/Wage strings ('€110.5M', '€565K') into numeric EUR; {bad_money} unparseable → NULL** - "
               "money arrives as display text; models need numbers. NULLs are kept (not zeroed) so "
               "missing wages can't masquerade as free transfers.")

    f18["primary_position"] = (f18["Preferred Positions"].astype(str).str.strip()
                               .str.split().str[0].replace({"nan": None}))
    f18 = f18.drop(columns=["Preferred Positions"])
    log.append("**Derived primary_position (first listed preferred position)** - 'ST LW' collapses to 'ST'; "
               "one categorical with 15 levels beats a ragged multi-label string for both SQL bucketing and modeling.")

    for c in ("Age", "Potential", "Special") + tuple(SKILL_COLS):
        f18[c] = pd.to_numeric(f18[c], errors="coerce")
    f18.columns = [re.sub(r"[^a-z0-9]+", "_", c.lower()).strip("_") for c in f18.columns]
    log.append("**Coerced Age/Overall/Potential and 34 skill ratings to numeric; snake_cased all names** - "
               "GK rows legitimately lack some outfield ratings (kept as NULL, imputed at model time, "
               "not silently zero-filled - a 0 rating means 'terrible', not 'not applicable').")

    no_club = int(f18["club"].isna().sum())
    log.append(f"**Kept {no_club} club-less FIFA 18 rows in the clean layer but excluded them from modeling scope** - "
               "free agents have no club to churn *from*; the question is 'will we lose this squad member', "
               "which is undefined without a squad.")

    # --- FIFA 19: label source only ---
    f19 = f19[["ID", "Club"]].rename(columns={"ID": "id", "Club": "club_19"})
    f19["id"] = pd.to_numeric(f19["id"], errors="coerce").astype("Int64")
    f19 = f19.dropna(subset=["id"]).drop_duplicates(subset="id")
    log.append("**Reduced FIFA 19 to (id, club) only** - the next-season club is the label source; every other "
               "FIFA 19 column is future information a squad planner wouldn't have, i.e. leakage.")

    con.execute("DROP TABLE IF EXISTS clean_f18"); con.register("f18_df", f18)
    con.execute("CREATE TABLE clean_f18 AS SELECT * FROM f18_df")
    con.execute("DROP TABLE IF EXISTS clean_f19_clubs"); con.register("f19_df", f19)
    con.execute("CREATE TABLE clean_f19_clubs AS SELECT * FROM f19_df")
    log.append(f"**Wrote clean_f18 ({len(f18):,} rows) and clean_f19_clubs ({len(f19):,} rows) to DuckDB** - "
               "the clean layer is the contract the SQL stage builds on.")
    con.close()
    return log


if __name__ == "__main__":
    print("\n".join(run()))
