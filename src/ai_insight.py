"""AI insight layer: guarded NL-to-SQL plus a deterministic weekly report.

1. NL-to-SQL. The model gets ai/prompts/nl_to_sql.txt with
   ai/schema_description.md inlined and is told to output SQL only. What it
   returns goes through validate_and_cap() - one read-only query (SELECT,
   WITH, or set operations between them), a nine-table allowlist, no file or
   introspection functions, automatic row cap - and only then runs against
   DuckDB in read-only mode. A rejected query never reaches the database.
   Needs OPENAI_API_KEY (exported, or in the gitignored .env).
2. Weekly insight report. No LLM in its path at all: every number is computed
   in Python from kpi_weekly before any text is written.
"""
import os
import sys
from pathlib import Path

import duckdb
import pandas as pd
import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"fact_bookings", "kpi_weekly", "kpi_weekly_by_hotel",
                  "kpi_by_hotel", "kpi_by_channel", "kpi_by_segment",
                  "kpi_by_country", "kpi_by_lead_band", "kpi_monthly_by_hotel"}
ROW_CAP = 5000
FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
             exp.Alter, exp.Copy, exp.Command)
DEFAULT_MODEL = "gpt-4o-mini"
PROMPT_PATH = Path("ai/prompts/nl_to_sql.txt")
SCHEMA_PATH = Path("ai/schema_description.md")
REPORT_TEMPLATE_PATH = Path("ai/weekly_report_template.md")


def validate_and_cap(sql: str) -> str:
    try:
        parsed = sqlglot.parse(sql, read="duckdb")
    except sqlglot.errors.SqlglotError as exc:
        raise ValueError(f"SQL did not parse: {exc}") from exc
    if len(parsed) != 1:
        raise ValueError("exactly one statement allowed")
    stmt = parsed[0]
    # exp.Query covers SELECT, WITH...SELECT and set operations (UNION /
    # INTERSECT / EXCEPT); no DML or DDL node is a Query subclass.
    if not isinstance(stmt, (exp.Select, exp.With, exp.Query)):
        raise ValueError("SELECT / WITH only")
    _reject_dangerous_nodes(stmt)
    tables = {t.name.lower() for t in stmt.find_all(exp.Table)}
    ctes = {c.alias_or_name.lower() for c in stmt.find_all(exp.CTE)}
    unknown = tables - ALLOWED_TABLES - ctes
    if unknown:
        raise ValueError(f"tables not allowed: {sorted(unknown)}")
    if stmt.args.get("limit") is None:
        stmt = stmt.limit(ROW_CAP)
    return stmt.sql(dialect="duckdb")


def _reject_dangerous_nodes(stmt):
    # A read-only DuckDB session still exposes the filesystem through table
    # functions, so anything sqlglot cannot name is refused.
    for node in stmt.walk():
        if isinstance(node, FORBIDDEN):
            raise ValueError("forbidden statement node")
        if isinstance(node, exp.Table) and not isinstance(node.this, exp.Identifier):
            raise ValueError("only named tables from the allowlist")
        if isinstance(node, exp.Func):
            name = (node.sql_name() or getattr(node, "name", "") or "").upper()
            if (isinstance(node, exp.Anonymous) or name.startswith("READ_")
                    or name.endswith("_SCAN")):
                raise ValueError(f"function not allowed: {name}")


def run_question(sql: str, db_path: str = "data/travel_booking.duckdb") -> pd.DataFrame:
    safe_sql = validate_and_cap(sql)
    with duckdb.connect(db_path, read_only=True) as con:
        return con.execute(safe_sql).fetchdf()


def load_env_file(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def build_prompt(question: str) -> str:
    return (PROMPT_PATH.read_text()
            .replace("{{schema}}", SCHEMA_PATH.read_text())
            .replace("{{allowed_tables}}", ", ".join(sorted(ALLOWED_TABLES)))
            .replace("{{row_cap}}", str(ROW_CAP))
            .replace("{{question}}", question))


def _openai_client():
    load_env_file()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set - export it or put it in .env (gitignored)")
    from openai import OpenAI
    return OpenAI()


def _strip_fences(text: str) -> str:
    kept = [ln for ln in text.strip().splitlines() if not ln.lstrip().startswith("```")]
    return "\n".join(kept).strip().rstrip(";").strip()


def question_to_sql(question: str, client=None, model: str | None = None) -> str:
    client = client or _openai_client()
    response = client.chat.completions.create(
        model=model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        temperature=0,
        max_tokens=700,
        messages=[{"role": "user", "content": build_prompt(question)}],
    )
    raw = (response.choices[0].message.content or "").strip()
    if "CANNOT_ANSWER" in raw.upper():
        raise ValueError("model declined: the question is not answerable from the allowed tables")
    return validate_and_cap(_strip_fences(raw))


def answer_question(question: str, client=None,
                    db_path: str = "data/travel_booking.duckdb"):
    """Returns (rows_from_duckdb, sql_that_ran). The model writes SQL; DuckDB
    and Python produce every number in the answer."""
    safe_sql = question_to_sql(question, client=client)
    return run_question(safe_sql, db_path), safe_sql


def weekly_insight_numbers(weekly: pd.DataFrame) -> dict:
    w = weekly.sort_values("arrival_week")
    # The final week in the source is partial (arrivals end Thu
    # 2017-08-31), so the insight is written for the last COMPLETE
    # week. A partial week must never be reported as a -50% crash.
    w = w.iloc[:-1]
    last, prev = w.iloc[-1], w.iloc[-5:-1]
    return {
        "week": str(last["arrival_week"].date()),
        "bookings": int(last["bookings"]),
        "bookings_vs_prev4_pct": round(
            100 * (last["bookings"] / prev["bookings"].mean() - 1), 1),
        "realized_revenue_eur": round(float(last["realized_revenue_eur"]), 2),
        "cancellation_rate": round(float(last["cancellation_rate"]), 4),
    }


def render_report(numbers: dict) -> str:
    """Fills ai/weekly_report_template.md - Python owns every figure."""
    values = {
        "week": numbers["week"],
        "bookings": f"{numbers['bookings']:,}",
        "bookings_vs_prev4_pct": f"{numbers['bookings_vs_prev4_pct']:+.1f}",
        "realized_revenue_eur": f"{numbers['realized_revenue_eur']:,.0f}",
        "cancellation_rate": f"{numbers['cancellation_rate']:.1%}",
    }
    text = REPORT_TEMPLATE_PATH.read_text()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        raise ValueError(f"unfilled placeholder in report: {text}")
    return text


def main(argv=None) -> int:
    question = " ".join(sys.argv[1:] if argv is None else argv) or (
        "Which distribution channel has the highest channel ROI?")
    try:
        frame, safe_sql = answer_question(question)
    except (RuntimeError, ValueError) as exc:
        print(f"blocked before the database: {exc}")
        return 1
    print(f"Q: {question}\nSQL that ran: {safe_sql}\n")
    print(frame.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
