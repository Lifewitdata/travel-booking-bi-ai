-- KPI mart: one row per arrival week. Revenue is realized only on
-- Check-Out; No-Show and Canceled earn nothing. Channel cost and margin
-- use the synthetic reference table dim_channel_costs (labelled as such).
CREATE OR REPLACE TABLE travel_bi.kpi_weekly AS
SELECT
  DATE_TRUNC(b.arrival_date, WEEK(MONDAY)) AS arrival_week,
  COUNT(*) AS bookings,
  AVG(b.is_canceled) AS cancellation_rate,
  SUM(IF(b.reservation_status = 'Check-Out', b.adr * b.total_nights, 0)) AS realized_revenue_eur,
  SUM(IF(b.reservation_status = 'Check-Out',
         b.adr * b.total_nights * (1 - c.commission_rate)
         - c.acquisition_cost_per_booking_eur, 0)) AS gross_margin_eur
FROM travel_bi.stg_bookings b
JOIN travel_bi.dim_channel_costs c USING (distribution_channel)
WHERE NOT (b.guests = 0 OR b.adr > 1000)
GROUP BY arrival_week;
