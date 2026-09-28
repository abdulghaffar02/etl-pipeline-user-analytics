import os
from pathlib import Path

DEFAULT_DB_PATH = Path("data/listens.duckdb")
DB_PATH_ENV_VAR = "LISTENS_DB"


def resolve_db_path(cli_value: str | None = None) -> Path:
    """--db flag wins, then the LISTENS_DB env var, then the default."""
    return Path(cli_value or os.environ.get(DB_PATH_ENV_VAR) or DEFAULT_DB_PATH)
