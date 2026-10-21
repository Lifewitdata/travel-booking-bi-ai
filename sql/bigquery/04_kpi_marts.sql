-- KPI marts: the same eight aggregates kpi_by() in src/run_pipeline.py writes
-- to DuckDB and to data/tableau/. Change the measure block in one place and
-- change it in all eight, then re-run the DuckDB cross-check.
--
-- SAFE_DIVIDE returns NULL where the Python layer writes NaN (a channel with
-- no cost, a week with no realized revenue). The Python marts round to 4
-- decimals, so compare these with a tolerance rather than for exact equality.
CREATE OR REPLACE TABLE travel_bi.kpi_weekly AS
SELECT
  arrival_week,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY arrival_week;

CREATE OR REPLACE TABLE travel_bi.kpi_weekly_by_hotel AS
SELECT
  arrival_week, hotel,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY arrival_week, hotel;

CREATE OR REPLACE TABLE travel_bi.kpi_monthly_by_hotel AS
SELECT
  arrival_month, hotel,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY arrival_month, hotel;

CREATE OR REPLACE TABLE travel_bi.kpi_by_hotel AS
SELECT
  hotel,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY hotel;

CREATE OR REPLACE TABLE travel_bi.kpi_by_channel AS
SELECT
  distribution_channel,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY distribution_channel;

CREATE OR REPLACE TABLE travel_bi.kpi_by_segment AS
SELECT
  market_segment,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY market_segment;

-- Small markets are dropped the same way the Python layer does it, so the two
-- engines return the same country rows.
CREATE OR REPLACE TABLE travel_bi.kpi_by_country AS
SELECT
  country,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY country
HAVING COUNT(*) >= 200;

CREATE OR REPLACE TABLE travel_bi.kpi_by_lead_band AS
SELECT
  lead_band,
  COUNT(*) AS bookings,
  SUM(is_canceled) AS cancelled,
  SUM(is_realized) AS realized_stays,
  SUM(is_noshow) AS noshows,
  SUM(total_nights) AS total_nights,
  SUM(booked_revenue_eur) AS booked_revenue_eur,
  SUM(realized_revenue_eur) AS realized_revenue_eur,
  SUM(channel_cost_eur) AS channel_cost_eur,
  SUM(gross_margin_eur) AS gross_margin_eur,
  AVG(adr) AS avg_adr_eur,
  AVG(lead_time) AS avg_lead_time_days,
  SAFE_DIVIDE(SUM(is_canceled), COUNT(*)) AS cancellation_rate,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(realized_revenue_eur)) AS gross_margin_pct,
  SAFE_DIVIDE(SUM(gross_margin_eur), SUM(channel_cost_eur)) AS channel_roi
FROM travel_bi.fact_bookings
GROUP BY lead_band;
