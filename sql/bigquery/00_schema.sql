-- Landing schema: the three tables the rest of this folder reads but never
-- created. `python -m src.load_bigquery --upload` fills them from the CSVs
-- the repo already ships; without --upload the same command prints the plan
-- and checks these column lists against the CSV headers without touching GCP.
--
-- raw_hotel_bookings is all STRING on purpose. The source CSV writes missing
-- values as the literal text NULL and mixes integer and date formats, so the
-- load stays dumb and 01_staging.sql does the typing with SAFE_CAST.
CREATE SCHEMA IF NOT EXISTS travel_bi;

CREATE TABLE IF NOT EXISTS travel_bi.raw_hotel_bookings (
  hotel STRING,
  is_canceled STRING,
  lead_time STRING,
  arrival_date_year STRING,
  arrival_date_month STRING,
  arrival_date_week_number STRING,
  arrival_date_day_of_month STRING,
  stays_in_weekend_nights STRING,
  stays_in_week_nights STRING,
  adults STRING,
  children STRING,
  babies STRING,
  meal STRING,
  country STRING,
  market_segment STRING,
  distribution_channel STRING,
  is_repeated_guest STRING,
  previous_cancellations STRING,
  previous_bookings_not_canceled STRING,
  reserved_room_type STRING,
  assigned_room_type STRING,
  booking_changes STRING,
  deposit_type STRING,
  agent STRING,
  company STRING,
  days_in_waiting_list STRING,
  customer_type STRING,
  adr STRING,
  required_car_parking_spaces STRING,
  total_of_special_requests STRING,
  reservation_status STRING,
  reservation_status_date STRING
) OPTIONS (description = 'Hotel Booking Demand as uploaded, no typing');

-- SYNTHETIC rate card. The commission and acquisition figures are invented
-- for margin and ROI work; the bookings themselves are real. Everything that
-- reads these columns has to keep that label.
CREATE TABLE IF NOT EXISTS travel_bi.dim_channel_costs (
  distribution_channel STRING,
  commission_rate FLOAT64,
  acquisition_cost_per_booking_eur FLOAT64,
  is_synthetic BOOL
) OPTIONS (description = 'SYNTHETIC channel cost rates, data/reference/channel_costs.csv');

-- SIMULATED experiment users (seed 42), written by src/ab_test.py.
CREATE TABLE IF NOT EXISTS travel_bi.experiment_users (
  user_id STRING,
  variant STRING,
  booked BOOL,
  cancelled BOOL,
  revenue_per_user_eur FLOAT64
) OPTIONS (description = 'SIMULATED A/B users, seed 42 - not real guests');
