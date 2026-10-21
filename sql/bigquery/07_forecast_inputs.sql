-- Forecast inputs: complete arrival weeks only, realized revenue.
-- Partial first/last weeks are excluded in src/forecast.py by the same
-- rule (a week must be fully inside the source date range).
SELECT arrival_week, bookings, realized_revenue_eur, cancellation_rate
FROM travel_bi.kpi_weekly
ORDER BY arrival_week;
