-- Views that feed the Tableau workbook (one extract per view).
CREATE OR REPLACE VIEW travel_bi.vw_kpi_by_channel AS
SELECT distribution_channel,
       COUNT(*) AS bookings,
       AVG(is_canceled) AS cancellation_rate,
       SUM(IF(reservation_status = 'Check-Out', adr * total_nights, 0)) AS realized_revenue_eur
FROM travel_bi.stg_bookings
WHERE NOT (guests = 0 OR adr > 1000)
GROUP BY distribution_channel;

CREATE OR REPLACE VIEW travel_bi.vw_kpi_by_segment AS
SELECT market_segment,
       COUNT(*) AS bookings,
       AVG(is_canceled) AS cancellation_rate,
       SUM(IF(reservation_status = 'Check-Out', adr * total_nights, 0)) AS realized_revenue_eur
FROM travel_bi.stg_bookings
WHERE NOT (guests = 0 OR adr > 1000)
GROUP BY market_segment;
