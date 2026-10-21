-- BigQuery staging: raw hotel bookings -> typed staging view.
-- The source CSV writes missing values as the literal text NULL, so every
-- cast here is SAFE_CAST over NULLIF: a plain CAST('NULL' AS INT64) fails
-- the whole query in BigQuery, and SAFE_CAST turns it into a NULL the
-- quarantine rule can see instead.
CREATE OR REPLACE VIEW travel_bi.stg_bookings AS
SELECT
  hotel,
  SAFE_CAST(NULLIF(is_canceled, 'NULL') AS INT64) AS is_canceled,
  SAFE_CAST(NULLIF(lead_time, 'NULL') AS INT64) AS lead_time,
  DATE(SAFE_CAST(NULLIF(arrival_date_year, 'NULL') AS INT64),
       CASE arrival_date_month
         WHEN 'January' THEN 1 WHEN 'February' THEN 2 WHEN 'March' THEN 3
         WHEN 'April' THEN 4 WHEN 'May' THEN 5 WHEN 'June' THEN 6
         WHEN 'July' THEN 7 WHEN 'August' THEN 8 WHEN 'September' THEN 9
         WHEN 'October' THEN 10 WHEN 'November' THEN 11 ELSE 12 END,
       SAFE_CAST(NULLIF(arrival_date_day_of_month, 'NULL') AS INT64)) AS arrival_date,
  SAFE_CAST(NULLIF(stays_in_weekend_nights, 'NULL') AS INT64) AS stays_in_weekend_nights,
  SAFE_CAST(NULLIF(stays_in_week_nights, 'NULL') AS INT64) AS stays_in_week_nights,
  SAFE_CAST(NULLIF(stays_in_weekend_nights, 'NULL') AS INT64)
    + SAFE_CAST(NULLIF(stays_in_week_nights, 'NULL') AS INT64) AS total_nights,
  SAFE_CAST(NULLIF(adults, 'NULL') AS INT64) AS adults,
  SAFE_CAST(NULLIF(children, 'NULL') AS FLOAT64) AS children,
  SAFE_CAST(NULLIF(babies, 'NULL') AS INT64) AS babies,
  SAFE_CAST(NULLIF(adults, 'NULL') AS INT64)
    + COALESCE(SAFE_CAST(NULLIF(children, 'NULL') AS FLOAT64), 0)
    + SAFE_CAST(NULLIF(babies, 'NULL') AS INT64) AS guests,
  COALESCE(NULLIF(country, 'NULL'), 'Unknown') AS country,
  market_segment,
  distribution_channel,
  deposit_type,
  customer_type,
  SAFE_CAST(NULLIF(adr, 'NULL') AS FLOAT64) AS adr,
  reservation_status,
  SAFE_CAST(NULLIF(reservation_status_date, 'NULL') AS DATE) AS reservation_status_date
FROM travel_bi.raw_hotel_bookings;
