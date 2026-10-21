"""Load and clean the Hotel Booking Demand data into a fact table."""
import pandas as pd

from src.validation import quarantine_mask, quarantine_reasons

MONTH_NUM = {name: i + 1 for i, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def load_raw(path: str) -> pd.DataFrame:
    # The source writes missing values as the literal string NULL.
    return pd.read_csv(path, na_values=["NULL"])


def build_fact(raw: pd.DataFrame, channel_costs: pd.DataFrame):
    df = raw.copy()
    df["children"] = df["children"].fillna(0)
    df["country"] = df["country"].fillna("Unknown")
    df["arrival_date"] = pd.to_datetime({
        "year": df["arrival_date_year"],
        "month": df["arrival_date_month"].map(MONTH_NUM),
        "day": df["arrival_date_day_of_month"],
    })
    df["booking_date"] = df["arrival_date"] - pd.to_timedelta(df["lead_time"], unit="D")
    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]
    df["guests"] = df["adults"] + df["children"] + df["babies"]
    df["is_realized"] = (df["reservation_status"] == "Check-Out").astype(int)
    df["is_noshow"] = (df["reservation_status"] == "No-Show").astype(int)
    df["booked_revenue_eur"] = df["adr"] * df["total_nights"]
    df["realized_revenue_eur"] = df["booked_revenue_eur"] * df["is_realized"]
    df = df.merge(channel_costs, on="distribution_channel", how="left", validate="many_to_one")
    df["commission_cost_eur"] = df["realized_revenue_eur"] * df["commission_rate"]
    df["acquisition_cost_eur"] = df["acquisition_cost_per_booking_eur"] * df["is_realized"]
    df["channel_cost_eur"] = df["commission_cost_eur"] + df["acquisition_cost_eur"]
    df["gross_margin_eur"] = df["realized_revenue_eur"] - df["channel_cost_eur"]
    df["arrival_week"] = df["arrival_date"].dt.to_period("W-SUN").apply(lambda p: p.start_time)
    df["arrival_month"] = df["arrival_date"].dt.to_period("M").dt.to_timestamp()
    mask = quarantine_mask(df)
    df["quarantine_reason"] = quarantine_reasons(df)
    quarantined = df[mask].copy()
    clean = df[~mask].copy()
    return clean, quarantined
