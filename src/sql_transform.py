"""Stage 3 — SQL transformation: execute sql/*.sql in filename order.

The .sql files are the versioned source of truth for all set-level logic
(entity resolution, labeling, feature engineering); this module just runs
them and reports what they produced. Editing transformation logic means
editing SQL, not Python — the same separation a dbt project enforces.
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "churn.duckdb"
SQL_DIR = ROOT / "sql"
FEATURES_CSV = ROOT / "data" / "processed" / "features.csv"


def run() -> list[str]:
    con = duckdb.connect(str(DB))
    log = []
    for script in sorted(SQL_DIR.glob("*.sql")):
        con.execute(script.read_text(encoding="utf-8"))
        log.append(f"**Executed `sql/{script.name}`**")

    mapped, renamed = con.execute(
        "SELECT COUNT(*), SUM(CASE WHEN club_18 != club_19_canonical THEN 1 ELSE 0 END) FROM club_mapping").fetchone()
    log[-3] += (f" — resolved {mapped} FIFA 18 clubs to canonical FIFA 19 names by majority vote of retained "
                f"players; caught {renamed} pure renames (e.g. 'Real Madrid CF' → 'Real Madrid') that a naive "
                "string match would have counted as every squad member transferring at once.")

    n, churn = con.execute("SELECT COUNT(*), AVG(churned) FROM labeled").fetchone()
    log[-2] += (f" — labeled {n:,} players present in both editions; churn rate {churn:.1%} "
                f"(vs 45.2% before entity resolution — the mapping removed {45.2 - churn * 100:.1f} points of phantom churn).")

    nf, nc = con.execute(
        "SELECT COUNT(*), (SELECT COUNT(*) FROM pragma_table_info('features')) FROM features").fetchone()
    con.execute(f"COPY features TO '{FEATURES_CSV}' (HEADER, DELIMITER ',')")
    log[-1] += (f" — built the model-ready feature table: {nf:,} rows × {nc} columns "
                f"(squad-context windows + CASE bucketing), exported to `data/processed/features.csv`.")
    con.close()
    return log


if __name__ == "__main__":
    print("\n".join(run()))
