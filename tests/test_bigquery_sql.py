"""BigQuery port tests - all of them run without a GCP account.

They prove the two things that can be proven locally: the files are valid
BigQuery dialect, and the port covers the same objects the DuckDB pipeline
builds. That is deliberately not a claim that the SQL was executed on
BigQuery, and the README says so too.
"""
import csv
from pathlib import Path

import pandas as pd
import pytest
import sqlglot
from sqlglot import exp

from src.ai_insight import ALLOWED_TABLES
from src.load_bigquery import (LANDING_CSVS, check_landing_vs_csvs,
                               created_objects, dry_run, landing_columns,
                               parse_all, split_statements, sql_files)


@pytest.fixture(scope="module")
def port():
    return {p.name: p.read_text() for p in sql_files()}


MARTS = ["kpi_weekly", "kpi_weekly_by_hotel", "kpi_monthly_by_hotel", "kpi_by_hotel",
         "kpi_by_channel", "kpi_by_segment", "kpi_by_country", "kpi_by_lead_band"]


def created_select_columns(text):
    """{object_name: [output columns]} for each CREATE TABLE / CREATE VIEW AS SELECT."""
    out = {}
    for stmt in parse_all(text):
        kind = (stmt.args.get("kind") or "").upper()
        if isinstance(stmt, exp.Create) and kind in {"TABLE", "VIEW"}:
            name = stmt.this.find(exp.Table).name.lower()
            out[name] = [e.alias_or_name for e in stmt.expression.expressions]
    return out


def test_every_file_parses_as_bigquery(port):
    for name, text in port.items():
        statements = parse_all(text)
        assert statements, name
        assert split_statements(text), name


def test_port_covers_every_duckdb_object_the_ai_layer_can_query(port):
    built = {o.split(" ", 1)[1].replace("travel_bi.", "")
             for text in port.values() for o in created_objects(text)}
    missing = ALLOWED_TABLES - built
    assert not missing, f"BigQuery port never creates {sorted(missing)}"


def test_landing_ddl_matches_the_shipped_csvs(port):
    columns = landing_columns(port["00_schema.sql"])
    for table, path in LANDING_CSVS.items():
        header = next(csv.reader(open(path, newline="", encoding="utf-8-sig")))
        assert columns[table] == header, table
    assert not check_landing_vs_csvs()


def _code(text: str) -> str:
    """File contents with the comment lines removed."""
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("--"))


def test_staging_casts_the_literal_null_string_safely(port):
    # CAST('NULL' AS INT64) aborts the whole query in BigQuery, and the source
    # writes missing values as that literal, so staging must never bare-cast.
    staging = _code(port["01_staging.sql"])
    assert "SAFE_CAST(NULLIF(" in staging
    assert "CAST(" not in staging.replace("SAFE_CAST(", "")


def test_channel_view_publishes_margin_and_roi(port):
    views = port["05_dashboard_views.sql"]
    channel = views.split("CREATE OR REPLACE VIEW travel_bi.vw_kpi_by_segment")[0]
    for column in ("gross_margin_eur", "gross_margin_pct", "channel_roi"):
        assert column in channel


def test_quality_checks_can_prove_the_reconciliation(port):
    checks = port["02_quality_checks.sql"]
    assert "quarantined_rows" in checks and "clean_rows" in checks


def test_each_bigquery_mart_publishes_the_duckdb_columns(port):
    # Column names *and* order, against the extracts the Tableau workbook and
    # the Streamlit dashboard read. A renamed or reordered mart silently
    # breaks both, and this is the only place it can be caught before GCP.
    columns = created_select_columns(port["04_kpi_marts.sql"])
    for mart in MARTS:
        expected = list(pd.read_csv(Path("data/tableau") / f"{mart}.csv", nrows=0).columns)
        assert columns[mart] == expected, mart


def test_dry_run_exits_clean(port):
    assert dry_run() == 0


def test_file_order_runs_schema_first(port):
    names = list(port)
    assert names[0] == "00_schema.sql"
    assert names.index("03_fact_bookings.sql") < names.index("04_kpi_marts.sql")
