# KPI definitions

- bookings = row count of the clean fact (one row = one booking)
- cancellation_rate = AVG(is_canceled). Note: the source flag also marks
  No-Show rows as canceled (1,207 rows), so this is canceled + no-show.
- realized_revenue_eur = SUM(adr * total_nights) over Check-Out rows only
- booked_revenue_eur = SUM(adr * total_nights) over all rows (never
  reported as revenue; used only to show the cancellation leakage)
- channel_cost_eur = realized revenue * commission rate + acquisition
  cost per realized booking, from the SYNTHETIC reference table
  data/reference/channel_costs.csv
- gross_margin_eur = realized revenue - channel cost
- gross_margin_pct = gross margin / realized revenue
- channel_roi = gross margin / channel cost
- arrival_week = Monday-start week of arrival_date
- forecast: Holt-Winters (trend + 52-week seasonality) on weekly realized
  revenue; chosen on an 8-week holdout, MAE quoted wherever it is used
