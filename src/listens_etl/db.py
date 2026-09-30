from importlib.resources import files
from pathlib import Path

import duckdb


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open (or create) the database and make sure the schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    # DuckDB uses the local timezone by default, which moves listens near midnight
    # to the wrong day
    con.execute("SET TimeZone = 'UTC'")
    init_schema(con)
    return con


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(files("listens_etl").joinpath("schema.sql").read_text())
