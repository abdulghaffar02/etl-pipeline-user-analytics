import pytest

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
