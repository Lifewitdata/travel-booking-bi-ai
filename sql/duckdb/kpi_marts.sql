-- DuckDB mirror of the BigQuery KPI marts, run against fact_bookings
-- (built by src/run_pipeline.py). The pipeline writes the same tables
-- from pandas; these queries are the SQL cross-check for them.
CREATE OR REPLACE TABLE kpi_weekly_sql AS
SELECT
  date_trunc('week', arrival_date) AS arrival_week,
  COUNT(*) AS bookings,
  AVG(is_canceled) AS cancellation_rate,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(gross_margin_eur) AS gross_margin_eur
FROM fact_bookings
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE TABLE kpi_by_channel_sql AS
SELECT
  distribution_channel,
  COUNT(*) AS bookings,
  AVG(is_canceled) AS cancellation_rate,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(gross_margin_eur) / SUM(realized_revenue_eur) AS gross_margin_pct
FROM fact_bookings
GROUP BY 1
ORDER BY bookings DESC;
