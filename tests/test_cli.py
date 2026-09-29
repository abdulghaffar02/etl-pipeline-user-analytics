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


def test_analyze(tmp_path, write_export, capsys):
    db_file = tmp_path / "cli.duckdb"
    main(["ingest", str(write_export([make_listen()])), "--db", str(db_file)])
    out_dir = tmp_path / "results"

    assert main(["analyze", "--db", str(db_file), "--out", str(out_dir)]) == 0
    printed = capsys.readouterr().out
    assert "a1_top_users: Top 10 users" in printed
    assert sorted(p.name for p in out_dir.iterdir()) == [
        "a1_top_users.csv",
        "a2_users_on_2019_03_01.csv",
        "a3_first_song_per_user.csv",
        "b_top_days_per_user.csv",
        "c_daily_active_users.csv",
    ]
    assert (out_dir / "a1_top_users.csv").read_text().splitlines() == [
        "user_name,number_of_listens",
        "alice,1",
    ]


def test_analyze_single_query(tmp_path, write_export, capsys):
    db_file = tmp_path / "cli.duckdb"
    main(["ingest", str(write_export([make_listen()])), "--db", str(db_file)])
    capsys.readouterr()

    assert main(["analyze", "a2_users_on_2019_03_01", "--db", str(db_file)]) == 0
    printed = capsys.readouterr().out
    assert "a2_users_on_2019_03_01" in printed
    assert "a1_top_users" not in printed


def test_analyze_without_data(tmp_path, capsys):
    assert main(["analyze", "--db", str(tmp_path / "missing.duckdb")]) == 1
    assert "Run `listens-etl ingest FILE` first" in capsys.readouterr().err

    main(["init-db", "--db", str(tmp_path / "empty.duckdb")])
    assert main(["analyze", "--db", str(tmp_path / "empty.duckdb")]) == 1
    assert "has no listens" in capsys.readouterr().err
