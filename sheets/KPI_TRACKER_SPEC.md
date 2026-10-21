# Google Sheets KPI tracker - spec

Workbook: `Travel Booking KPI Tracker`
Tabs:
1. `Weekly KPIs` - import `data/tableau/kpi_weekly.csv` once (File >
   Import > Insert new sheet(s), rename the tab to `Weekly KPIs`).
   Apps Script (`apps_script/Code.gs`, v2) reads this tab, finds its
   columns by header name, flags anomalies and emails the snapshot;
   a weekly Monday 8am trigger is set up with one run of setupTrigger().
2. `Channel ROI` - import `data/tableau/kpi_by_channel.csv`; columns for
   bookings, cancellation_rate, realized_revenue_eur, gross_margin_pct,
   channel_roi with conditional formatting (margin_pct < 0.80 = amber).
3. `Snapshot` - the stakeholder view: latest week bookings, revenue,
   cancellation rate (formulas point at `Weekly KPIs`, never typed in),
   plus the anomaly list from the last Apps Script run.

Key formulas used on `Snapshot` (expert-Sheets evidence, all live formulas):
- Latest week: `=INDEX('Weekly KPIs'!A:A, COUNTA('Weekly KPIs'!A:A))`
- 4-week average bookings: `=AVERAGE(OFFSET(...))` over the last 4 data rows
- Week-on-4-week change: latest / average - 1, formatted as %

Deployment is done in the owner's Google account (5 steps in Code.gs).
The code and formulas are the deliverable in this repo; the workbook
itself lives in the owner's Drive, not in git.
