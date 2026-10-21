"""Travel Booking BI - Streamlit dashboard.

Run from the project root:  streamlit run dashboard/app.py
Reads the clean fact table and KPI extracts built by src/run_pipeline.py
and src/run_analysis.py. Filters recompute every KPI from the fact table,
so what you see is always the filtered truth, never a stale extract.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

st.set_page_config(page_title="Travel Booking BI", layout="wide")
st.title("Travel Booking BI & AI Insight Platform")
st.caption("119,390 real bookings (City Hotel Lisbon + Resort Hotel Algarve), "
           "Jul 2015 - Aug 2017. Channel costs and the A/B test are synthetic "
           "and labelled where they appear.")


@st.cache_data
def load():
    fact = pd.read_csv(DATA / "fact_bookings_clean.csv",
                       parse_dates=["arrival_date", "arrival_week", "arrival_month"])
    forecast = pd.read_csv(DATA / "tableau" / "forecast_weekly_revenue.csv",
                           parse_dates=["arrival_week"])
    ab = pd.read_csv(DATA / "tableau" / "ab_test_readout.csv")
    anomalies = pd.read_csv(DATA / "tableau" / "kpi_weekly_with_anomalies.csv",
                            parse_dates=["arrival_week"])
    return fact, forecast, ab, anomalies


fact, forecast, ab, anomalies = load()

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
hotels = st.sidebar.multiselect("Hotel", sorted(fact["hotel"].unique()),
                                default=sorted(fact["hotel"].unique()))
channels = st.sidebar.multiselect("Distribution channel",
                                  sorted(fact["distribution_channel"].unique()),
                                  default=sorted(fact["distribution_channel"].unique()))
segments = st.sidebar.multiselect("Market segment",
                                  sorted(fact["market_segment"].unique()),
                                  default=sorted(fact["market_segment"].unique()))
dmin, dmax = fact["arrival_date"].min(), fact["arrival_date"].max()
drange = st.sidebar.date_input("Arrival date range", value=(dmin, dmax),
                               min_value=dmin, max_value=dmax)

f = fact[fact["hotel"].isin(hotels) & fact["distribution_channel"].isin(channels)
         & fact["market_segment"].isin(segments)]
if len(drange) == 2:
    f = f[(f["arrival_date"] >= pd.Timestamp(drange[0]))
          & (f["arrival_date"] <= pd.Timestamp(drange[1]))]


def kpi_by(df, cols):
    g = df.groupby(cols).agg(
        bookings=("hotel", "size"), cancelled=("is_canceled", "sum"),
        revenue=("realized_revenue_eur", "sum"), margin=("gross_margin_eur", "sum"),
        cost=("channel_cost_eur", "sum"), adr=("adr", "mean")).reset_index()
    g["cancellation_rate"] = g["cancelled"] / g["bookings"]
    g["gross_margin_pct"] = g["margin"] / g["revenue"]
    g["channel_roi"] = g["margin"] / g["cost"]
    return g


# ---------------- KPI header ----------------
bookings = len(f)
revenue = f["realized_revenue_eur"].sum()
margin_pct = f["gross_margin_eur"].sum() / revenue if revenue else 0
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Bookings", f"{bookings:,}")
c2.metric("Realized revenue", f"EUR {revenue:,.0f}")
c3.metric("Cancellation rate", f"{f['is_canceled'].mean():.1%}" if bookings else "-")
c4.metric("Gross margin", f"{margin_pct:.1%}")
c5.metric("Avg ADR", f"EUR {f['adr'].mean():,.0f}" if bookings else "-")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Executive", "Marketing", "Operations", "Finance & Forecast", "Experiment & AI"])

with tab1:
    weekly = f.groupby("arrival_week").agg(
        revenue=("realized_revenue_eur", "sum"),
        bookings=("hotel", "size")).reset_index()
    st.plotly_chart(px.line(weekly, x="arrival_week", y="revenue",
                            title="Realized revenue by arrival week (EUR)"),
                    width="stretch")
    by_hotel = kpi_by(f, ["hotel"])
    st.plotly_chart(px.bar(by_hotel, x="hotel", y="bookings",
                           color="cancellation_rate",
                           title="Bookings by hotel (colour = cancellation rate)"),
                    width="stretch")
    st.dataframe(by_hotel.round(3), width="stretch")

with tab2:
    st.subheader("Channel economics - volume is not margin")
    by_channel = kpi_by(f, ["distribution_channel"]).sort_values("bookings", ascending=False)
    st.plotly_chart(px.bar(by_channel, x="distribution_channel", y="channel_roi",
                           title="Channel ROI (gross margin / channel cost, synthetic cost layer)"),
                    width="stretch")
    st.plotly_chart(px.bar(by_channel, x="distribution_channel", y="revenue",
                           color="gross_margin_pct",
                           title="Realized revenue by channel (colour = gross margin %)"),
                    width="stretch")
    st.dataframe(by_channel.round(3), width="stretch")
    by_segment = kpi_by(f, ["market_segment"]).sort_values("revenue", ascending=False)
    st.plotly_chart(px.bar(by_segment, x="market_segment", y="revenue",
                           color="cancellation_rate",
                           title="Realized revenue by market segment"),
                    width="stretch")
    top_country = kpi_by(f, ["country"]).query("bookings >= 200").nlargest(10, "bookings")
    st.dataframe(top_country.round(3), width="stretch")

with tab3:
    st.subheader("Cancellation risk")
    f2 = f.assign(lead_band=pd.cut(f["lead_time"], bins=[-1, 7, 30, 90, 180, 365, 800],
                                   labels=["0-7", "8-30", "31-90", "91-180", "181-365", "366+"]))
    by_lead = kpi_by(f2, ["lead_band"])
    st.plotly_chart(px.bar(by_lead, x="lead_band", y="cancellation_rate",
                           title="Cancellation rate by lead-time band (days)"),
                    width="stretch")
    monthly = f.groupby("arrival_month").agg(
        cancellation_rate=("is_canceled", "mean")).reset_index()
    st.plotly_chart(px.line(monthly, x="arrival_month", y="cancellation_rate",
                            title="Cancellation rate by arrival month"),
                    width="stretch")
    dep = kpi_by(f, ["deposit_type"])
    st.dataframe(dep.round(3), width="stretch")
    st.warning("Deposit quirk: 'Non Refund' rows are 99.4% canceled in the source "
               "data. That is a data-recording quirk under verification with Finance "
               "- do not use this view for deposit policy.")

with tab4:
    st.subheader("Revenue forecast - next 13 weeks")
    total_fc = forecast["forecast_realized_revenue_eur"].sum()
    st.metric("13-week forecast total (Holt-Winters)", f"EUR {total_fc:,.0f}")
    st.caption("Holdout MAE EUR 19,101 vs EUR 48,154 seasonal naive (Notebook 02). "
               "Forecast is global - sidebar filters do not change it.")
    st.plotly_chart(px.line(forecast, x="arrival_week",
                            y=["actual_realized_revenue_eur", "forecast_realized_revenue_eur"],
                            title="Weekly realized revenue: actual and forecast"),
                    width="stretch")
    by_month = f.groupby(["arrival_month", "hotel"]).agg(
        revenue=("realized_revenue_eur", "sum"),
        margin=("gross_margin_eur", "sum")).reset_index()
    by_month["gross_margin_pct"] = by_month["margin"] / by_month["revenue"]
    st.plotly_chart(px.line(by_month, x="arrival_month", y="gross_margin_pct",
                            color="hotel", title="Gross margin % by month and hotel"),
                    width="stretch")

with tab5:
    st.subheader("A/B test - flexible free-cancellation rate (SIMULATED, seed 42)")
    st.dataframe(ab, width="stretch")
    decision = ab.loc[ab["metric"] == "decision", "value"].iloc[0]
    st.info(f"Decision: {decision}")
    st.subheader("AI weekly insight")
    insight = ROOT / "outputs" / "weekly_insight_report.md"
    if insight.exists():
        st.markdown(insight.read_text())
    z_cols = ["bookings_z", "realized_revenue_eur_z", "cancellation_rate_z"]
    flagged = anomalies[anomalies[z_cols].abs().max(axis=1) >= 3.0]
    st.write(f"Anomaly scan: {len(flagged)} of {len(anomalies)} weeks flagged at "
             f"|z| >= 3 vs the trailing 4-week average. On a strongly seasonal "
             f"series this is a screening list, not a verdict - most flags sit "
             f"at seasonal turns.")
    st.dataframe(flagged[["arrival_week", "bookings", "realized_revenue_eur",
                          "cancellation_rate"]].tail(10), width="stretch")

st.caption("Source: Hotel Booking Demand (Antonio, Almeida & Nunes 2019). "
           "Realized revenue counts Check-Out stays only. Reconciliation: "
           "119,390 raw = 119,209 clean + 181 quarantined.")
