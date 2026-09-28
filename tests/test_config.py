from pathlib import Path

from listens_etl.config import DEFAULT_DB_PATH, resolve_db_path


def test_default(monkeypatch):
    monkeypatch.delenv("LISTENS_DB", raising=False)
    assert resolve_db_path() == DEFAULT_DB_PATH


def test_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("LISTENS_DB", "from_env.duckdb")
    assert resolve_db_path() == Path("from_env.duckdb")


def test_cli_flag_overrides_env_var(monkeypatch):
    monkeypatch.setenv("LISTENS_DB", "from_env.duckdb")
    assert resolve_db_path("from_cli.duckdb") == Path("from_cli.duckdb")
