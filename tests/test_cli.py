import pytest

from helpers import make_listen
from listens_etl import __version__
from listens_etl.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_init_db_with_flag(tmp_path, capsys):
    db_file = tmp_path / "nested" / "listens.duckdb"
    assert main(["init-db", "--db", str(db_file)]) == 0
    assert db_file.exists()
    assert str(db_file) in capsys.readouterr().out


def test_init_db_with_env_var(tmp_path, monkeypatch):
    db_file = tmp_path / "env.duckdb"
    monkeypatch.setenv("LISTENS_DB", str(db_file))
    assert main(["init-db"]) == 0
    assert db_file.exists()


def test_subcommand_is_required():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_ingest(tmp_path, write_export, caplog):
    db_file = tmp_path / "cli.duckdb"
    path = write_export([make_listen(), "{broken"])
    caplog.set_level("INFO")

    assert main(["ingest", str(path), "--db", str(db_file)]) == 0
    assert "1 inserted, 0 duplicates, 1 rejected" in caplog.text


def test_ingest_missing_file(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["ingest", str(tmp_path / "nope.jsonl"), "--db", str(tmp_path / "x.duckdb")])
    assert exc.value.code == 2
    assert "file not found" in capsys.readouterr().err
