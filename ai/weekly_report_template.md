# Weekly insight - week of {{week}}

- Bookings: {{bookings}} ({{bookings_vs_prev4_pct}}% vs previous 4-week average)
- Realized revenue: EUR {{realized_revenue_eur}}
- Cancellation rate: {{cancellation_rate}}

Numbers are computed from kpi_weekly in Python before this template is
filled. An LLM may rephrase the stakeholder wording; it never produces
or changes a number (tolerance check in src/ai_insight.py).
