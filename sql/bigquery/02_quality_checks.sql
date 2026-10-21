-- Data-quality checks. Quarantine rule (kept identical in Python and SQL):
-- a row leaves the clean fact only if it cannot describe a real stay:
-- guests = 0, or adr > 1000 (single 5,400 outlier in the source).
-- Byte-identical rows are NOT duplicates to drop: the source has no
-- booking ID, so identical rows are separate bookings.
SELECT
  COUNT(*) AS raw_rows,
  COUNTIF(guests = 0) AS no_guest_rows,
  COUNTIF(adr > 1000) AS adr_outlier_rows,
  COUNTIF(total_nights = 0) AS zero_night_rows_kept_flagged,
  COUNTIF(adr = 0) AS zero_adr_rows_kept_flagged,
  COUNTIF(reservation_status = 'No-Show' AND is_canceled = 1) AS noshow_flagged_canceled_in_source
FROM travel_bi.stg_bookings;
