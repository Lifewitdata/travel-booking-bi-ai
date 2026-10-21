"""Guarded NL-to-SQL tests.

A fake client supplies the model reply, so these run with no API key and no
network. They assert the property that matters: whatever the model returns,
the sqlglot guard sees it before DuckDB does.
"""
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.ai_insight import (ALLOWED_TABLES, ROW_CAP, answer_question,
                            build_prompt, question_to_sql)

DB = Path("data/travel_booking.duckdb")
MISSING_DB = "no_such_database.duckdb"


def fake_client(reply: str):
    calls = {}

    def create(**kwargs):
        calls.update(kwargs)
        message = SimpleNamespace(content=reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    client.calls = calls
    return client


def test_prompt_carries_schema_rules_and_question():
    prompt = build_prompt("Which channel has the best ROI?")
    assert "{{schema}}" not in prompt and "{{question}}" not in prompt
    assert "{{row_cap}}" not in prompt and "{{allowed_tables}}" not in prompt
    assert "realized_revenue_eur" in prompt
    assert "CANNOT_ANSWER" in prompt
    assert "Which channel has the best ROI?" in prompt
    for table in ALLOWED_TABLES:
        assert table in prompt


def test_fenced_reply_is_cleaned_and_capped():
    client = fake_client("```sql\nSELECT * FROM kpi_weekly\n```")
    sql = question_to_sql("weekly revenue", client=client)
    assert sql.upper().startswith("SELECT")
    assert f"LIMIT {ROW_CAP}" in sql
    assert "```" not in sql
    assert client.calls["temperature"] == 0


def test_hostile_reply_never_reaches_the_database():
    with pytest.raises(ValueError, match="SELECT / WITH only"):
        question_to_sql("drop it", client=fake_client("DROP TABLE fact_bookings"))
    # If the guard missed it, the read-only connect on a missing file would
    # raise an IOException instead, so this pins the order of operations.
    with pytest.raises(ValueError):
        answer_question("drop it", client=fake_client("DELETE FROM kpi_weekly"),
                        db_path=MISSING_DB)


def test_two_statement_reply_is_rejected():
    with pytest.raises(ValueError, match="exactly one statement"):
        question_to_sql("q", client=fake_client("SELECT 1 FROM kpi_weekly; DROP TABLE fact_bookings"))


def test_reply_outside_the_table_allowlist_is_rejected():
    with pytest.raises(ValueError, match="tables not allowed"):
        question_to_sql("q", client=fake_client("SELECT * FROM pg_catalog.pg_tables"))


@pytest.mark.parametrize("sql", [
    "SELECT * FROM read_csv('data/raw/hotel_bookings.csv')",
    "SELECT * FROM parquet_scan('outside.parquet')",
    "SELECT * FROM duckdb_tables()",
])
def test_file_and_introspection_functions_are_rejected(sql):
    with pytest.raises(ValueError):
        question_to_sql("q", client=fake_client(sql))


def test_cannot_answer_is_honoured_not_guessed():
    with pytest.raises(ValueError, match="model declined"):
        question_to_sql("what was RevPAR in 2019?", client=fake_client("CANNOT_ANSWER"))


def test_cte_names_are_not_treated_as_unknown_tables():
    sql = question_to_sql(
        "q", client=fake_client(
            "WITH w AS (SELECT * FROM kpi_weekly) SELECT MAX(realized_revenue_eur) FROM w"))
    assert "WITH w AS" in sql


def test_set_operations_pass_the_guard_and_still_get_capped():
    sql = question_to_sql("q", client=fake_client(
        "(SELECT arrival_week FROM kpi_weekly ORDER BY bookings DESC LIMIT 3) "
        "UNION ALL "
        "(SELECT arrival_week FROM kpi_weekly ORDER BY realized_revenue_eur DESC LIMIT 2)"))
    assert "UNION ALL" in sql
    assert sql.endswith(f"LIMIT {ROW_CAP}")


def test_every_build_mart_is_queryable():
    for sql in ["SELECT hotel, channel_roi FROM kpi_by_hotel",
                "SELECT arrival_week, hotel, bookings FROM kpi_weekly_by_hotel",
                "SELECT lead_band, cancellation_rate FROM kpi_by_lead_band"]:
        assert f"LIMIT {ROW_CAP}" in question_to_sql("q", client=fake_client(sql))


def test_ai_lead_band_answer_matches_the_published_extract():
    if not DB.exists():
        pytest.skip("run python -m src.run_pipeline first")
    frame, _ = answer_question(
        "q", client=fake_client(
            "SELECT lead_band, cancellation_rate FROM kpi_by_lead_band "
            "ORDER BY cancellation_rate DESC"), db_path=str(DB))
    mart = pd.read_csv("data/tableau/kpi_by_lead_band.csv")
    top = mart.sort_values("cancellation_rate", ascending=False).iloc[0]
    assert frame.iloc[0]["lead_band"] == top["lead_band"]
    assert frame.iloc[0]["cancellation_rate"] == pytest.approx(top["cancellation_rate"], abs=1e-3)


def test_ai_answer_matches_the_published_extract():
    if not DB.exists():
        pytest.skip("run python -m src.run_pipeline first")
    sql = "SELECT distribution_channel, channel_roi FROM kpi_by_channel ORDER BY channel_roi DESC"
    frame, _ = answer_question("q", client=fake_client(sql), db_path=str(DB))
    mart = pd.read_csv("data/tableau/kpi_by_channel.csv")
    best = mart.sort_values("channel_roi", ascending=False).iloc[0]
    assert frame.iloc[0]["distribution_channel"] == best["distribution_channel"]
    assert frame.iloc[0]["channel_roi"] == pytest.approx(best["channel_roi"], abs=1e-3)
