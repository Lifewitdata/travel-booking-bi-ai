-- Published extracts, one view per cut, in the column order the dashboard and
-- the Google Sheets tracker expect. The old port exposed bookings,
-- cancellation and revenue only here, which left the margin and ROI story -
-- the actual finding - reproducible only through Python.
CREATE OR REPLACE VIEW travel_bi.vw_kpi_by_channel AS
SELECT distribution_channel, bookings, cancellation_rate,
       realized_revenue_eur, channel_cost_eur, gross_margin_eur,
       gross_margin_pct, channel_roi
FROM travel_bi.kpi_by_channel
ORDER BY bookings DESC;

CREATE OR REPLACE VIEW travel_bi.vw_kpi_by_segment AS
SELECT market_segment, bookings, cancellation_rate,
       realized_revenue_eur, channel_cost_eur, gross_margin_eur,
       gross_margin_pct, channel_roi
FROM travel_bi.kpi_by_segment
ORDER BY realized_revenue_eur DESC;

CREATE OR REPLACE VIEW travel_bi.vw_kpi_by_country AS
SELECT country, bookings, cancellation_rate,
       realized_revenue_eur, avg_adr_eur, gross_margin_pct
FROM travel_bi.kpi_by_country
ORDER BY bookings DESC;

CREATE OR REPLACE VIEW travel_bi.vw_kpi_by_lead_band AS
SELECT lead_band, bookings, avg_lead_time_days, cancellation_rate,
       realized_revenue_eur, gross_margin_pct
FROM travel_bi.kpi_by_lead_band
ORDER BY avg_lead_time_days;

CREATE OR REPLACE VIEW travel_bi.vw_kpi_weekly AS
SELECT arrival_week, bookings, cancellation_rate, realized_revenue_eur,
       channel_cost_eur, gross_margin_eur, gross_margin_pct, channel_roi
FROM travel_bi.kpi_weekly
ORDER BY arrival_week;
