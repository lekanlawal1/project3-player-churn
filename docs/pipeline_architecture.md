# Pipeline Architecture

One command (`python src/run_pipeline.py`) runs the whole graph left to right;
every arrow is a stage boundary with a persisted artifact behind it.

```mermaid
flowchart LR
    subgraph raw["data/raw (immutable)"]
        A18["fifa18_players_raw.csv<br/>17,981 × 75"]
        A19["fifa19_players_raw.csv<br/>18,207 × 88"]
    end

    subgraph duck["DuckDB - data/processed/churn.duckdb"]
        B18["raw_fifa18<br/>(all VARCHAR)"]
        B19["raw_fifa19<br/>(all VARCHAR)"]
        C18["clean_f18"]
        C19["clean_f19_clubs"]
        D["club_mapping<br/><i>01 entity resolution</i>"]
        E["labeled<br/><i>02 churn label via join</i>"]
        F["features<br/><i>03 windows + bucketing</i>"]
    end

    subgraph model["Models - src/train.py"]
        G["logistic regression<br/>(interpretable baseline)"]
        H["gradient boosting<br/>(stronger learner)"]
    end

    A18 -->|"src/ingest.py"| B18
    A19 -->|"src/ingest.py"| B19
    B18 -->|"src/clean.py<br/>(logged decisions)"| C18
    B19 -->|"src/clean.py"| C19
    C18 --> D
    C19 --> D
    D --> E
    C18 --> E
    C19 --> E
    E --> F
    F --> G
    F --> H
    G --> I["output/: metrics · coefficients ·<br/>importances · driver crosstabs · chart"]
    H --> I
    F -->|"src/export_dashboard.py<br/>(out-of-fold scores)"| J["dashboard/ - interactive explorer<br/>(GitHub Pages)"]
```

## Stage responsibilities

| Stage | Owner | Why there |
|---|---|---|
| Ingest | `src/ingest.py` | Raw CSVs land in DuckDB as all-VARCHAR tables - byte-faithful raw layer, no parser-default type guesses. |
| Clean | `src/clean.py` (pandas) | Row-level work: money-string parsing, dedup, type coercion. Every decision emits a line in [cleaning_log.md](cleaning_log.md). |
| Transform | `sql/01–03` (DuckDB SQL) | Set-level work: majority-vote entity resolution, the label join, window-function squad features, CASE bucketing. Versioned `.sql` files are the source of truth - the dbt separation, without the dbt dependency. |
| Model | `src/train.py` | Two-model comparison, imbalance-aware metrics, interpretability artifacts. |

## Why DuckDB

An embedded analytical database: full SQL (window functions, `MEDIAN`,
`IS DISTINCT FROM`) running in-process against a single file - no server to
install, secure, or keep running, which is exactly the modern-data-stack
trade (DuckDB is to OLAP what SQLite is to OLTP). The pipeline stays
one-command reproducible on any machine, and the SQL is portable to a
warehouse (Snowflake/BigQuery) with minimal edits if the data outgrew a
laptop - which at 18K rows it does not.
