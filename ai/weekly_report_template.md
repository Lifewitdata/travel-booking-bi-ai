# Weekly insight - week of {{week}}

- Bookings: {{bookings}} ({{bookings_vs_prev4_pct}}% vs the previous 4-week average)
- Realized revenue: EUR {{realized_revenue_eur}}
- Cancellation rate: {{cancellation_rate}}

All numbers above were computed from kpi_weekly before any text was written,
then substituted into this template by src/ai_insight.py. No LLM call sits in
this path, so there is no way for a prompt to change a figure on the page.
