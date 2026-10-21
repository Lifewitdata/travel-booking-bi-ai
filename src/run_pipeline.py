"""End-to-end pipeline: raw -> clean fact -> KPI marts -> KPI extracts
-> forecast -> simulated A/B test -> weekly anomaly table.

Run from the project root:  python -m src.run_pipeline
Every headline number is printed so the README can be checked against it.
"""
import json

import duckdb
import numpy as np
import pandas as pd

from src.load_data import build_fact, load_raw
from src.validation import quality_checks

ROOT = "."
RNG = np.random.default_rng(42)


def kpi_by(df, cols):
    g = df.groupby(cols).agg(
        bookings=("hotel", "size"),
        cancelled=("is_canceled", "sum"),
        realized_stays=("is_realized", "sum"),
        noshows=("is_noshow", "sum"),
        total_nights=("total_nights", "sum"),
        booked_revenue_eur=("booked_revenue_eur", "sum"),
        realized_revenue_eur=("realized_revenue_eur", "sum"),
        channel_cost_eur=("channel_cost_eur", "sum"),
        gross_margin_eur=("gross_margin_eur", "sum"),
        avg_adr_eur=("adr", "mean"),
        avg_lead_time_days=("lead_time", "mean"),
    ).reset_index()
    g["cancellation_rate"] = g["cancelled"] / g["bookings"]
    g["gross_margin_pct"] = g["gross_margin_eur"] / g["realized_revenue_eur"]
    g["channel_roi"] = np.where(g["channel_cost_eur"] > 0,
                                g["gross_margin_eur"] / g["channel_cost_eur"], np.nan)
    return g.round(4)


def main():
    raw = load_raw(f"{ROOT}/data/raw/hotel_bookings.csv")
    costs = pd.read_csv(f"{ROOT}/data/reference/channel_costs.csv")
    clean, quarantined = build_fact(raw, costs)
    checks = quality_checks(raw, clean, quarantined)
    assert checks["reconciles"], checks
    print(json.dumps(checks, indent=1))

    clean.to_csv(f"{ROOT}/data/fact_bookings_clean.csv", index=False)
    quarantined.to_csv(f"{ROOT}/data/quarantined_rows.csv", index=False)

    # ---- KPI marts -------------------------------------------------------
    weekly = kpi_by(clean.assign(arrival_week=clean["arrival_week"]), ["arrival_week", "hotel"])
    weekly_all = kpi_by(clean, ["arrival_week"])
    monthly = kpi_by(clean, ["arrival_month", "hotel"])
    by_channel = kpi_by(clean, ["distribution_channel"])
    by_segment = kpi_by(clean, ["market_segment"])
    by_country = kpi_by(clean, ["country"]).query("bookings >= 200").sort_values(
        "bookings", ascending=False)
    by_hotel = kpi_by(clean, ["hotel"])
    lead = clean.assign(lead_band=pd.cut(clean["lead_time"],
                      bins=[-1, 7, 30, 90, 180, 365, 800],
                      labels=["0-7", "8-30", "31-90", "91-180", "181-365", "366+"]))
    by_lead = kpi_by(lead, ["lead_band"])

    marts = {"kpi_weekly": weekly_all, "kpi_weekly_by_hotel": weekly,
             "kpi_monthly_by_hotel": monthly, "kpi_by_channel": by_channel,
             "kpi_by_segment": by_segment, "kpi_by_country": by_country,
             "kpi_by_hotel": by_hotel, "kpi_by_lead_band": by_lead}
    for name, frame in marts.items():
        frame.to_csv(f"{ROOT}/data/tableau/{name}.csv", index=False)

    con = duckdb.connect(f"{ROOT}/data/travel_booking.duckdb")
    con.execute("DROP TABLE IF EXISTS fact_bookings")
    con.register("clean_df", clean)
    con.execute("CREATE TABLE fact_bookings AS SELECT * FROM clean_df")
    for name, frame in marts.items():
        con.execute(f"DROP TABLE IF EXISTS {name}")
        con.register("tmp_df", frame)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")
    con.close()

    # ---- Headline numbers for README / memo ------------------------------
    total_realized = clean["realized_revenue_eur"].sum()
    total_margin = clean["gross_margin_eur"].sum()
    print(f"clean_rows={len(clean)} cancel_rate={clean['is_canceled'].mean():.4f}")
    print(f"realized_revenue_eur={total_realized:,.0f} gross_margin_eur={total_margin:,.0f} "
          f"margin_pct={total_margin/total_realized:.3f}")
    print("by_channel:\n", by_channel[["distribution_channel", "bookings",
          "cancellation_rate", "realized_revenue_eur", "gross_margin_pct", "channel_roi"]]
          .to_string(index=False))
    dep = clean.groupby("deposit_type")["is_canceled"].mean()
    dc = float(dep.get("No Deposit", float("nan")))
    rd = float(dep.get("Non Refund", float("nan")))
    # Source quirk, reported not smoothed over: 99%+ of 'Non Refund' rows
    # are marked Canceled in the source. Never read this as 'deposits
    # cause cancellations' - the segment needs Finance verification.
    print(f"cancel_rate_no_deposit={dc:.3f} cancel_rate_non_refund={rd:.3f}")
    print(f"lead_band_cancel:\n{by_lead[['lead_band','bookings','cancellation_rate']].to_string(index=False)}")
    checks.update({"clean_rows": int(len(clean)),
                   "overall_cancellation_rate": round(float(clean["is_canceled"].mean()), 4),
                   "realized_revenue_eur": round(float(total_realized), 2),
                   "gross_margin_eur": round(float(total_margin), 2),
                   "gross_margin_pct": round(float(total_margin / total_realized), 4),
                   "cancel_rate_no_deposit": round(float(dc), 4),
                   "cancel_rate_non_refund_source_quirk": round(float(rd), 4)})
    with open(f"{ROOT}/outputs/headline_metrics.json", "w") as fh:
        json.dump(checks, fh, indent=1)
    print("pipeline stage 1 done")


if __name__ == "__main__":
    main()
