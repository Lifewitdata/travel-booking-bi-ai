# LLM-facing schema contract (DuckDB: data/travel_booking.duckdb)

Allowed tables only: fact_bookings, kpi_weekly, kpi_by_channel,
kpi_by_segment, kpi_by_country, kpi_monthly_by_hotel.

## fact_bookings (clean, 119,209 rows)
One row per booking. Key columns: hotel ('Resort Hotel' / 'City Hotel'),
arrival_date, arrival_week (Monday), arrival_month, lead_time (days),
is_canceled (0/1; in the source this flag also marks No-Show rows),
reservation_status ('Check-Out' / 'Canceled' / 'No-Show'),
is_realized (1 only for Check-Out), market_segment, distribution_channel,
country, deposit_type, adr (EUR per night), total_nights,
booked_revenue_eur = adr * total_nights,
realized_revenue_eur = booked revenue only when is_realized = 1,
gross_margin_eur = realized revenue minus channel cost.
Channel cost uses SYNTHETIC rates from data/reference/channel_costs.csv.

## KPI definitions
- bookings = COUNT(*)
- cancellation_rate = AVG(is_canceled)
- realized revenue: SUM(realized_revenue_eur) - never booked revenue
- gross_margin_pct = SUM(gross_margin_eur) / SUM(realized_revenue_eur)
- channel_roi = SUM(gross_margin_eur) / SUM(channel_cost_eur)
- week = arrival_week, Monday start

## Pitfalls (do not violate)
1. Never sum booked_revenue_eur and call it revenue.
2. Never dedupe fact_bookings: no booking ID exists; identical rows are
   separate bookings (31,994 such rows in the source).
3. 'Non Refund' deposit rows are 99.4% Canceled in the source - a data
   quirk to flag, never a causal claim about deposits.
4. adr = 0 rows (1,810) are complimentary stays, kept with revenue 0.
5. The A/B test tables are simulated; never present them as real guests.
6. Row cap 5,000 on every NL-to-SQL answer; one SELECT statement only.
