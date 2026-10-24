"""Stage 1 - Ingest: load both raw CSVs into DuckDB untouched.

Raw files land in DuckDB as all-VARCHAR tables on purpose: the database holds
an exact copy of what arrived, and every type decision happens downstream in
the cleaning stage where it can be logged. If cleaning rules change, we
re-derive from raw_* tables without re-downloading anything.
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "churn.duckdb"
RAW_18 = ROOT / "data" / "raw" / "fifa18_players_raw.csv"
RAW_19 = ROOT / "data" / "raw" / "fifa19_players_raw.csv"


def run() -> list[str]:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    log = []
    for table, path in [("raw_fifa18", RAW_18), ("raw_fifa19", RAW_19)]:
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(
            f"CREATE TABLE {table} AS SELECT * FROM read_csv(?, all_varchar=true, header=true)",
            [str(path)],
        )
        n, c = con.execute(f"SELECT COUNT(*), (SELECT COUNT(*) FROM pragma_table_info('{table}')) FROM {table}").fetchone()
        log.append(f"**Ingested {path.name} → `{table}`: {n:,} rows × {c} columns, all VARCHAR** - "
                   "raw layer stays byte-faithful; every type coercion is a logged decision in the cleaning stage, not a CSV-parser default.")
    con.close()
    return log


if __name__ == "__main__":
    print("\n".join(run()))
