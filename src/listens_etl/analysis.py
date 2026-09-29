"""Task 2 queries. Each one is a plain .sql file in queries/, named after its question."""

from importlib.resources import files

import duckdb

QUERIES = files("listens_etl") / "queries"


def query_names() -> list[str]:
    return sorted(p.name.removesuffix(".sql") for p in QUERIES.iterdir() if p.name.endswith(".sql"))


def query_sql(name: str) -> str:
    return (QUERIES / f"{name}.sql").read_text(encoding="utf-8")


def describe(name: str) -> str:
    """The question a query answers: its first comment line."""
    first = query_sql(name).splitlines()[0]
    return first.removeprefix("--").strip()


def run(con: duckdb.DuckDBPyConnection, name: str) -> duckdb.DuckDBPyRelation:
    return con.sql(query_sql(name))
