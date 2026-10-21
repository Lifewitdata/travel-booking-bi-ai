# Travel Booking BI & AI Insight Platform

Revenue, cancellation and channel economics for a two-hotel group (City Hotel
Lisbon + Resort Hotel Algarve), built for the three audiences that actually
argue about them - Marketing, Operations and Finance. A DuckDB KPI warehouse,
a five-tab Streamlit dashboard, a holdout-scored revenue forecast, an
experiment readout, a Google Sheets tracker with Apps Script automation, and
guarded natural-language querying: the model writes SQL, a sqlglot allowlist
passes nothing but a capped `SELECT`, and DuckDB answers in read-only mode.

**119,390 real bookings** (Hotel Booking Demand, Antonio / Almeida / Nunes
2019, via TidyTuesday), arrivals Jul 2015 to Aug 2017. 27 tests pass, all
three notebooks are executed, and the dashboard's headline numbers are
asserted by a Streamlit AppTest rather than claimed in prose.

## The call this data supports

Volume and profit point in opposite directions.

| Channel | Share of bookings | Cancellation | Gross margin | ROI |
|---|---|---|---|---|
| TA/TO | 82% | 41.1% | 75.9% | 3.15 |
| Direct | 12% | 17.5% | 95.3% | 20.40 |

Travel agents and tour operators fill beds at roughly one-sixth the return
Direct does. Optimising for booking count rewards exactly the channel that
earns least, which is the argument to bring to Marketing with revenue
attached: EUR 25,986,912 realized revenue, EUR 20,679,670 gross margin,
79.6%. ROI uses the rate card in `data/reference/channel_costs.csv`; the
ranking survives plausible changes to those rates, the exact multiples do not.

Cancellation also has a structure worth pricing: **9.6%** at 0-7 days lead
time, rising to **67.7%** beyond 365 days. Long-lead inventory is where a
deposit policy earns its keep, and short-lead is where flexible rates are
safe.

## Numbers

Reproduced by `python -m src.run_pipeline` and `python -m src.run_analysis`;
tests cover the reconciliation, the revenue definition, the forecast model
ranking and the SQL guardrails.

- Clean fact **119,209** bookings, reconciling exactly: 119,390 raw = 119,209
  clean + 181 quarantined
- Cancellation **37.1%** overall, average ADR EUR 102
- Weekly realized revenue, 8-week holdout: **Holt-Winters MAE EUR 19,101**
  against 48,154 for seasonal naive and 97,405 for a 4-week average - a 2.5x
  error reduction over the naive baseline the business would default to
- Next 13 weeks: **EUR 3,668,172** (quote the holdout MAE as the accuracy
  claim; the extrapolated total moves a few percent between runs)
- Experiment readout: conversion 11.99% to **13.16%** (+9.7%, p = 0.013),
  sample-ratio check clean (p = 0.381). The cancellation guardrail moved the
  wrong way but missed significance at p = 0.182, so the decision is **ship
  with monitoring and a pre-set stop rule**, not a win declaration

## Run it

```
pip install -r requirements.txt
python -m src.run_pipeline      # raw -> clean fact -> KPI marts -> DuckDB
python -m src.run_analysis      # forecast, experiment readout, anomaly scan
streamlit run dashboard/app.py  # dashboard
pytest tests/                   # 27 tests: pipeline, dashboard AppTest, SQL guard
```

Natural-language querying needs a key; everything above runs without one:

```
cp .env.example .env            # paste OPENAI_API_KEY (.env is gitignored)
python -m src.ai_insight "Which channel has the best gross margin?"
```

## Ask it in English

`src/ai_insight.py` holds the whole path, and the model sits outside the
numbers:

1. `ai/prompts/nl_to_sql.txt` + `ai/schema_description.md` (KPI definitions
   and six documented pitfalls) go to the model; it is told to return SQL or
   `CANNOT_ANSWER`.
2. `validate_and_cap()` parses the reply with sqlglot and rejects it unless
   it is exactly one read-only query (`SELECT`, `WITH`, or a `UNION` /
   `INTERSECT` / `EXCEPT` of them), reads only the nine allowlisted marts,
   and contains no file or introspection function (`read_csv`, `parquet_scan`,
   `duckdb_tables` and anything sqlglot cannot name). It appends
   `LIMIT 5000` itself.
3. Only a surviving query runs, on a `read_only=True` DuckDB connection, and
   the rows come back from DuckDB. The model never supplies a figure.

Tab 5 of the dashboard exposes it as a question box; with no key set the box
is hidden and the rest of the tab still renders. `tests/test_nl_sql.py` feeds
the guard hostile replies - `DROP TABLE`, a two-statement reply, `pg_catalog`,
a `read_csv` - and asserts each is rejected before the database is opened. The
weekly insight report has no LLM in its path at all: every number is computed
in Python from `kpi_weekly` before any text is written, and the last (partial)
week is dropped so a truncated week is never reported as a crash.

## Data calls worth defending

- **31,994 byte-identical rows kept.** The source has no booking ID, so
  identical rows are separate bookings that happen to look alike. Deduping
  the way a textbook would delete 27% of the revenue base.
- **No-Show rows (1,207) are marked `is_canceled = 1` by the source.** Handled
  as its own status rather than folded into cancellations.
- **'Non Refund' deposit rows are 99.4% canceled in the source.** Flagged for
  Finance verification as a recording quirk; never used to support a claim
  about deposit behaviour.

Full rules in `docs/data_quality_rules.md`.

## What is real, what is built

| Layer | Provenance |
|---|---|
| Bookings, ADR, lead time, cancellation, country | Real source data, 2015-2017 |
| Channel commission + acquisition costs | Synthetic rate card, labelled in-file via `is_synthetic` |
| A/B experiment users | Simulated at seed 42, labelled in the CSV, dashboard and README |
| NL-to-SQL answers | The model drafts SQL; every figure comes back from DuckDB |
| Forecast | Fit on the real weekly series; holdout-scored against two baselines |

Everything synthetic is marked where it appears rather than at the end.

## Layout

```
src/          pipeline, validation, forecast, experiment, guarded NL-to-SQL
sql/duckdb/   SQL cross-check against the pandas marts
sql/bigquery/ the same KPI logic written for BigQuery (see note below)
dashboard/    Streamlit app, five tabs, filters recompute from the fact table
notebooks/    01 cleaning & quality, 02 analysis & forecast, 03 experiment
sheets/       KPI tracker spec + Apps Script (anomaly flags + email)
ai/           NL-to-SQL prompt, LLM-facing schema contract, report template
data/         raw source, clean fact, KPI marts for external tools
```

**On the BigQuery files:** the DuckDB path is what runs and is tested here.
`sql/bigquery/` carries the same staging, quality and KPI logic in BQ dialect
and is a partial port - it builds `stg_bookings`, `kpi_weekly` and two views
against landing tables that need an upload job before they execute. The
BigQuery loader is the obvious next piece of work, not something already
done.
