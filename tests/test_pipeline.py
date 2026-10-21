import json

import pandas as pd
import pytest

from src.ai_insight import validate_and_cap


@pytest.fixture(scope="module")
def fact():
    return pd.read_csv("data/fact_bookings_clean.csv")


def test_reconciliation():
    m = json.load(open("outputs/headline_metrics.json"))
    assert m["raw_rows"] == 119390
    assert m["clean_rows"] + m["quarantined_rows"] == m["raw_rows"]
    assert m["reconciles"] is True


def test_fact_shape_and_no_guests(fact):
    assert len(fact) == 119209
    assert (fact["guests"] == 0).sum() == 0
    assert fact["adr"].max() <= 1000


def test_revenue_definition(fact):
    realized = fact[fact["is_realized"] == 1]
    assert (realized["realized_revenue_eur"] > 0).mean() > 0.95
    assert (fact[fact["is_realized"] == 0]["realized_revenue_eur"] == 0).all()
    assert abs(fact["realized_revenue_eur"].sum() - 25986912.23) < 1.0


def test_duplicates_kept(fact):
    # No booking ID in source: identical rows are separate bookings.
    assert len(fact) > 119000


def test_forecast_winner():
    scores = pd.read_csv("outputs/forecast_holdout_scores.csv")
    assert scores.iloc[0]["model"] == "holt_winters"
    assert scores.iloc[0]["mae_eur"] < scores.iloc[1]["mae_eur"]


def test_ab_readout():
    r = pd.read_csv("data/tableau/ab_test_readout.csv").set_index("metric")["value"]
    assert float(r["srm_p_value"]) > 0.05
    assert float(r["conversion_p_value"]) < 0.05
    assert "SHIP with monitoring" in str(r["decision"])


def test_sql_guardrails():
    ok = validate_and_cap("SELECT * FROM kpi_weekly")
    assert "LIMIT" in ok.upper()
    with pytest.raises(ValueError):
        validate_and_cap("DROP TABLE kpi_weekly")
    with pytest.raises(ValueError):
        validate_and_cap("SELECT * FROM some_other_table")
    with pytest.raises(ValueError):
        validate_and_cap("SELECT 1; SELECT 2")
