"""Data-quality rules for the travel booking fact table.

Rules are deliberately conservative: a row is quarantined only when it
cannot describe a real stay. Everything else is kept and flagged.
"""
import pandas as pd

ADR_OUTLIER_CAP_EUR = 1000


def quarantine_mask(df: pd.DataFrame) -> pd.Series:
    """Rows that cannot be real bookings and must leave the clean fact."""
    no_guests = (df["adults"] + df["children"].fillna(0) + df["babies"]) == 0
    adr_outlier = df["adr"] > ADR_OUTLIER_CAP_EUR
    return no_guests | adr_outlier


def quarantine_reasons(df: pd.DataFrame) -> pd.Series:
    reasons = pd.Series("", index=df.index, dtype="string")
    no_guests = (df["adults"] + df["children"].fillna(0) + df["babies"]) == 0
    adr_outlier = df["adr"] > ADR_OUTLIER_CAP_EUR
    reasons.loc[no_guests] = reasons.loc[no_guests] + "no_guests;"
    reasons.loc[adr_outlier] = reasons.loc[adr_outlier] + "adr_outlier_over_1000;"
    return reasons


def quality_checks(raw: pd.DataFrame, clean: pd.DataFrame, quarantined: pd.DataFrame) -> dict:
    """Reconciliation: raw must equal clean + quarantined, exactly."""
    checks = {
        "raw_rows": int(len(raw)),
        "clean_rows": int(len(clean)),
        "quarantined_rows": int(len(quarantined)),
        "reconciles": bool(len(raw) == len(clean) + len(quarantined)),
        # No booking ID exists in the source, so byte-identical rows are
        # separate bookings that happen to look the same. Never dedupe.
        "full_duplicate_rows_kept": int(raw.duplicated().sum()),
        "children_nulls_filled": int(raw["children"].isna().sum()),
        "zero_night_rows_kept_flagged": int((clean["total_nights"] == 0).sum()),
        "zero_adr_rows_kept_flagged": int((clean["adr"] == 0).sum()),
        "noshow_rows_in_source_canceled_flag": int(
            ((raw["reservation_status"] == "No-Show") & (raw["is_canceled"] == 1)).sum()
        ),
    }
    return checks
