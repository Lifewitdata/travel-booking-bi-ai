-- Clean fact table: the quarantine applied, the measures attached, the
-- synthetic channel cost joined. This is the object every mart below reads,
-- and it mirrors build_fact() in src/load_data.py plus quarantine_mask() in
-- src/validation.py row for row: 119,390 raw = 119,209 clean + 181 rejected.
--
-- Byte-identical rows are kept, not deduped: the source has no booking ID, so
-- two identical rows are two bookings that happen to look the same.
CREATE OR REPLACE TABLE travel_bi.fact_bookings AS
WITH clean AS (
  SELECT * FROM travel_bi.stg_bookings
  WHERE COALESCE(guests, 0) <> 0
    AND COALESCE(adr, 0) <= 1000
),
derived AS (
  SELECT c.*,
    DATE_TRUNC(c.arrival_date, WEEK(MONDAY)) AS arrival_week,
    DATE_TRUNC(c.arrival_date, MONTH) AS arrival_month,
    DATE_SUB(c.arrival_date, INTERVAL c.lead_time DAY) AS booking_date,
    IF(c.reservation_status = 'Check-Out', 1, 0) AS is_realized,
    IF(c.reservation_status = 'No-Show', 1, 0) AS is_noshow,
    c.adr * c.total_nights AS booked_revenue_eur,
    IF(c.reservation_status = 'Check-Out', c.adr * c.total_nights, 0) AS realized_revenue_eur,
    k.commission_rate,
    k.acquisition_cost_per_booking_eur,
    CASE
      WHEN c.lead_time <= 7 THEN '0-7'
      WHEN c.lead_time <= 30 THEN '8-30'
      WHEN c.lead_time <= 90 THEN '31-90'
      WHEN c.lead_time <= 180 THEN '91-180'
      WHEN c.lead_time <= 365 THEN '181-365'
      ELSE '366+'
    END AS lead_band
  FROM clean c
  LEFT JOIN travel_bi.dim_channel_costs k USING (distribution_channel)
),
costed AS (
  SELECT d.*,
    d.realized_revenue_eur * d.commission_rate AS commission_cost_eur,
    IF(d.is_realized = 1, d.acquisition_cost_per_booking_eur, 0) AS acquisition_cost_eur
  FROM derived d
)
SELECT *,
  commission_cost_eur + acquisition_cost_eur AS channel_cost_eur,
  realized_revenue_eur - (commission_cost_eur + acquisition_cost_eur) AS gross_margin_eur
FROM costed;
