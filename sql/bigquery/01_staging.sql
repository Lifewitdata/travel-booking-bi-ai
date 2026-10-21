-- BigQuery staging: raw hotel bookings -> typed staging view.
-- Source writes missing values as the literal string 'NULL'; the Python
-- loader converts them before upload, so staging only types and renames.
CREATE OR REPLACE VIEW travel_bi.stg_bookings AS
SELECT
  hotel,
  CAST(is_canceled AS INT64) AS is_canceled,
  CAST(lead_time AS INT64) AS lead_time,
  DATE(arrival_date_year,
       CASE arrival_date_month
         WHEN 'January' THEN 1 WHEN 'February' THEN 2 WHEN 'March' THEN 3
         WHEN 'April' THEN 4 WHEN 'May' THEN 5 WHEN 'June' THEN 6
         WHEN 'July' THEN 7 WHEN 'August' THEN 8 WHEN 'September' THEN 9
         WHEN 'October' THEN 10 WHEN 'November' THEN 11 ELSE 12 END,
       arrival_date_day_of_month) AS arrival_date,
  CAST(stays_in_weekend_nights + stays_in_week_nights AS INT64) AS total_nights,
  CAST(adults + COALESCE(children, 0) + babies AS INT64) AS guests,
  country, market_segment, distribution_channel, deposit_type,
  CAST(adr AS FLOAT64) AS adr,
  reservation_status, reservation_status_date
FROM travel_bi.raw_hotel_bookings;
