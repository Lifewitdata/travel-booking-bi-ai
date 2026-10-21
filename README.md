# Travel Booking BI & AI Insight Platform

BI and decision support for a two-hotel travel business (Lisbon City
Hotel + Algarve Resort Hotel), built for Marketing, Operations and
Finance stakeholders: KPI warehouse, a Streamlit dashboard, a revenue
forecast, an A/B test readout, a Google Sheets KPI tracker with Apps
Script automation, and a weekly-insight layer whose SQL passes an
allowlist guard before it runs.

Data: Hotel Booking Demand (Antonio, Almeida & Nunes 2019, via
TidyTuesday) - 119,390 real bookings, arrivals Jul 2015 to Aug 2017.
Two layers are synthetic and labelled everywhere they appear: channel
costs (needed for margin/ROI) and the A/B test users.

## Headline results
Every number below is printed by `python -m src.run_pipeline` and
`python -m src.run_analysis`. The test suite asserts the reconciliation, the
revenue definition, the forecast model ranking and the SQL guardrails; it
does not assert each figure individually.
- Clean fact: 119,209 bookings (raw 119,390 = clean + 181 quarantined)
- Cancellation rate 37.1% overall; realized revenue EUR 25,986,912;
  gross margin EUR 20,679,670 (79.6%)
- Channel economics invert the volume story: TA/TO = 82% of bookings,
  41.1% cancellation, ROI 3.15 - Direct = 12% of bookings, 17.5%
  cancellation, margin 95.3%, ROI 20.40
- Cancellation rises with lead time: 9.6% (0-7 days) to 67.7% (366+)
- Forecast (weekly realized revenue, 8-week holdout): Holt-Winters
  MAE EUR 19,101 vs seasonal naive 48,154 vs 4-week average 97,405;
  next 13 weeks forecast EUR 3,668,172
- A/B test (simulated): conversion 11.99% -> 13.16% (+9.7%, p = 0.013),
  SRM clean (p = 0.381); cancellation guardrail unresolved (p = 0.182,
  underpowered) - decision: ship with monitoring

## Data quality catches (docs/data_quality_rules.md)
- 31,994 byte-identical rows KEPT: the source has no booking ID, so
  identical rows are separate bookings; dedupe would delete 27%
- No-Show rows (1,207) are marked is_canceled = 1 by the source
- 'Non Refund' deposit rows are 99.4% canceled in the source - flagged
  as a quirk for Finance verification, never used for a policy claim

## Run it
```
pip install -r requirements.txt
python -m src.run_pipeline     # raw -> clean fact -> KPI marts -> DuckDB
python -m src.run_analysis     # forecast, A/B readout, anomaly scan
streamlit run dashboard/app.py # dashboard (needs both commands above first)
pytest tests/                  # 10 tests
```
Notebooks 01-03 are executed and tell the same story step by step.

## Dashboards and automation
- Dashboard: Streamlit app at `dashboard/app.py` - run
  `streamlit run dashboard/app.py`. Five tabs (Executive, Marketing,
  Operations, Finance & Forecast, Experiment & AI) with sidebar filters
  for hotel, channel, segment and arrival dates. The header metrics and the
  hotel, channel, segment, country, lead-time and deposit views recompute
  from the clean fact table under those filters; the forecast, A/B readout
  and anomaly scan are global (the app labels them where they appear).
  `tests/test_dashboard.py` runs it under Streamlit AppTest and asserts 0
  exceptions, the unfiltered header (119,209 bookings, EUR 25,986,912,
  37.1% cancellation, 79.6% margin) and that filtering to Direct alone
  moves it to 14,611 bookings at 17.5% cancellation.
  The CSV extracts in `data/tableau/` are the KPI marts the project
  publishes for external tools (Sheets import uses them).
- Google Sheets: `sheets/KPI_TRACKER_SPEC.md` + `sheets/apps_script/Code.gs`
  (reads the imported `Weekly KPIs` tab, finds columns by header name, flags
  anomalies at |z| >= 3 against the trailing 4-week window, emails a
  snapshot, and installs a Monday-8am trigger via `setupTrigger()`). Not
  deployed yet: `RECIPIENTS` still holds a placeholder address, so run the
  six setup steps in the `Code.gs` header before the first `sendSnapshotNow()`.
- AI: `src/ai_insight.py` - a sqlglot guard over the DuckDB marts (single
  SELECT/WITH, table allowlist, forbidden-node block, automatic row cap)
  plus a weekly insight report whose every number is computed in Python
  before any text is written. Be precise about what runs: the guard
  executes and is tested; no model is called. `ai/prompts/nl_to_sql.txt`
  holds the prompt that would feed it, but nothing imports `anthropic`,
  so natural-language questions are not answered end to end yet.

## Honest limits
- BigQuery SQL in `sql/bigquery/` is a **partial** mirror of the executed
  DuckDB pipeline and has never run on a live account. It builds
  `stg_bookings`, `kpi_weekly` and two channel/segment views, while DuckDB
  builds `fact_bookings` plus eight marts. `raw_hotel_bookings`,
  `dim_channel_costs` and `experiment_users` are referenced but have no DDL
  and no upload script, so the SQL needs a loader before it can run. The
  channel view also omits margin and ROI, so the Direct-vs-TA/TO economics
  are reproducible only through the Python layer today.
- The 13-week Holt-Winters total is optimizer-sensitive. Holdout MAE is
  stable (EUR 19,101 within 0.31 across runs), but `fit(optimized=True)`
  lands on slightly different parameters and the extrapolation amplifies
  that: a fresh run here gives EUR 3,668,172 from `src/forecast.py` and
  EUR 3,668,177 from the notebook's inline fit, where an earlier artifact
  said EUR 3,971,283. Quote the holdout MAE, not the 13-week total, as the
  accuracy claim.
- Margin/ROI depend on the synthetic channel-cost rates in
  `data/reference/channel_costs.csv` - change the rates, the ranking
  of Direct vs TA/TO does not change, the exact ROI values do.
- The A/B test is simulated (seed 42) and labelled as such everywhere.
