"""BigQuery port runner: dry-run the plan locally, upload and run on GCP.

Run from the project root:
    python -m src.load_bigquery                 # dry-run, no credentials, no network
    python -m src.load_bigquery --upload --project YOUR_GCP_PROJECT

The dry run is what makes sql/bigquery/ checkable on a machine with no GCP
account: it parses every file in BigQuery dialect, lists the objects the port
creates, and proves the landing tables match the CSVs the repo ships. The
upload path needs `pip install google-cloud-bigquery` and application default
credentials, and is the part that cannot be verified here.
"""
import argparse
import csv
import re
from pathlib import Path

import sqlglot

SQL_DIR = Path("sql/bigquery")
LANDING_CSVS = {
    "travel_bi.raw_hotel_bookings": "data/raw/hotel_bookings.csv",
    "travel_bi.dim_channel_costs": "data/reference/channel_costs.csv",
    "travel_bi.experiment_users": "data/experiment_users_simulated.csv",
}
# BigQuery will not widen an INT64 into a STRING column during a load, and
# pandas infers user_id as a number, so the landing dtypes are pinned here.
LOAD_DTYPES = {"travel_bi.experiment_users": {"user_id": str}}


def sql_files():
    return sorted(SQL_DIR.glob("*.sql"))


def parse_all(text):
    return [s for s in sqlglot.parse(text, read="bigquery") if s is not None]


def created_objects(text):
    """Names this SQL creates, for the plan and the DuckDB parity check."""
    names = []
    for stmt in parse_all(text):
        if isinstance(stmt, sqlglot.exp.Create):
            kind = (stmt.args.get("kind") or "").upper()
            node = stmt.this
            table = node if isinstance(node, sqlglot.exp.Table) else node.find(sqlglot.exp.Table)
            names.append(f"{kind} {table.sql(dialect='bigquery')}" if table else f"{kind} statement")
    return names


def landing_columns(text):
    """{table: [column, ...]} for every CREATE TABLE in the schema file."""
    out = {}
    for stmt in parse_all(text):
        if isinstance(stmt, sqlglot.exp.Create) and (stmt.args.get("kind") or "").upper() == "TABLE":
            table = stmt.this
            name = table.this.sql(dialect="bigquery")
            out[name] = [col.name for col in table.expressions]
    return out


def check_landing_vs_csvs():
    """Each landing table must have exactly the columns of the CSV that fills it."""
    columns = landing_columns((SQL_DIR / "00_schema.sql").read_text())
    problems = []
    for table, path in LANDING_CSVS.items():
        header = next(csv.reader(open(path, newline="", encoding="utf-8-sig")))
        if table not in columns:
            problems.append(f"{table}: no CREATE TABLE in 00_schema.sql")
        elif columns[table] != header:
            problems.append(
                f"{table}: DDL has {len(columns[table])} columns, {path} has {len(header)}; "
                f"first difference at "
                f"{next((i for i, (a, b) in enumerate(zip(columns[table], header)) if a != b), 'length')}")
    return problems


def split_statements(text):
    """Top-level chunks, comments kept so the file stays self-documenting.
    These files carry no semicolon inside a literal, which is what makes the
    simple split safe here."""
    chunks = []
    for part in text.split(";"):
        body = re.sub(r"--[^\n]*", "", part).strip()
        if body:
            chunks.append(part.strip())
    return chunks


def dry_run():
    files = sql_files()
    print(f"{len(files)} BigQuery files in {SQL_DIR}:")
    created = []
    for path in files:
        text = path.read_text()
        statements = split_statements(text)
        objects = created_objects(text)
        created += [o.split(" ", 1)[1] for o in objects]
        queries = len(statements) - len(objects)
        print(f"  {path.name}: {len(statements)} statements, "
              f"{len(objects)} created, {queries} read-only query/queries")
        for obj in objects:
            print(f"      {obj}")
    problems = check_landing_vs_csvs()
    for table, path in LANDING_CSVS.items():
        rows = sum(1 for _ in open(path, encoding="utf-8-sig")) - 1
        print(f"  upload {table} <- {path} ({rows:,} rows)")
    if problems:
        print("LANDING SCHEMA MISMATCH:")
        for p in problems:
            print("  -", p)
        return 1
    print("landing DDL matches the shipped CSVs; nothing was sent to GCP.")
    return 0


def upload(project: str):
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise SystemExit("pip install google-cloud-bigquery and pyarrow first - they are not "
                         "in requirements.txt because the dashboard does not need them") from exc
    import pandas as pd

    client = bigquery.Client(project=project)

    def run(path):
        for statement in split_statements(path.read_text()):
            client.query(statement).result()
        print(f"ran {path.name}")

    # The landing tables have to exist before the CSVs land, and the fact needs
    # the data, so: DDL, then upload, then everything else in file order.
    files = sql_files()
    run(files[0])
    for table, path in LANDING_CSVS.items():
        df = pd.read_csv(path, dtype={"*": str} if table.endswith("raw_hotel_bookings")
                         else LOAD_DTYPES.get(table, {}))
        job = client.load_table_from_dataframe(
            df, table, job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"))
        job.result()
        print(f"loaded {table}: {job.output_rows:,} rows")
    for path in files[1:]:
        run(path)
    print("Compare travel_bi.kpi_weekly against data/tableau/kpi_weekly.csv "
          "before trusting either engine.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the BigQuery port.")
    ap.add_argument("--upload", action="store_true",
                    help="upload the landing CSVs and execute the SQL on GCP")
    ap.add_argument("--project", help="GCP project id (required with --upload)")
    args = ap.parse_args(argv)
    if args.upload:
        if not args.project:
            ap.error("--upload needs --project YOUR_GCP_PROJECT")
        upload(args.project)
        return 0
    return dry_run()


if __name__ == "__main__":
    raise SystemExit(main())
