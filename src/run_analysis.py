"""Stage 2: forecast + A/B readout + weekly anomaly scan.

Run after src.run_pipeline:  python -m src.run_analysis
"""
import pandas as pd

from src.ab_test import analyse, simulate
from src.ai_insight import render_report, weekly_insight_numbers
from src.forecast import forecast_weekly


def weekly_anomalies(weekly: pd.DataFrame, baseline: int = 4, z_thresh: float = 3.0):
    w = weekly.sort_values("arrival_week").copy()
    for col in ["bookings", "realized_revenue_eur", "cancellation_rate"]:
        mu = w[col].shift(1).rolling(baseline).mean()
        sd = w[col].shift(1).rolling(baseline).std()
        w[f"{col}_z"] = (w[col] - mu) / sd
    flagged = w[w[["bookings_z", "realized_revenue_eur_z", "cancellation_rate_z"]]
                .abs().max(axis=1) >= z_thresh]
    return w, flagged


def main():
    weekly = pd.read_csv("data/tableau/kpi_weekly.csv", parse_dates=["arrival_week"])
    fc, scores = forecast_weekly(weekly)
    fc.to_csv("data/tableau/forecast_weekly_revenue.csv", index=False)
    scores.to_csv("outputs/forecast_holdout_scores.csv", index=False)
    print("forecast holdout:\n", scores.to_string(index=False))
    print(f"next-13-week forecast total EUR {fc['forecast_realized_revenue_eur'].sum():,.0f} "
          f"using {fc['forecast_model'].dropna().iloc[0]}")

    users = simulate()
    users.to_csv("data/experiment_users_simulated.csv", index=False)
    readout = analyse(users)
    readout.to_csv("data/tableau/ab_test_readout.csv", index=False)
    print("A/B readout:\n", readout.to_string(index=False))

    w, flagged = weekly_anomalies(weekly)
    w.to_csv("data/tableau/kpi_weekly_with_anomalies.csv", index=False)
    print(f"anomaly weeks flagged: {len(flagged)} of {len(w)}")
    print(flagged[["arrival_week", "bookings", "realized_revenue_eur",
                   "cancellation_rate"]].to_string(index=False))

    report = render_report(weekly_insight_numbers(w))
    with open("outputs/weekly_insight_report.md", "w") as fh:
        fh.write(report)
    print(f"weekly insight report written for week {report.split(chr(10))[0]}")


if __name__ == "__main__":
    main()
