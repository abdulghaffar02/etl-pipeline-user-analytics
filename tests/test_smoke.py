import duckdb
import pytest

from listens_etl import __version__
from listens_etl.cli import main


def test_duckdb_available():
    assert duckdb.sql("SELECT 42").fetchone() == (42,)


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
