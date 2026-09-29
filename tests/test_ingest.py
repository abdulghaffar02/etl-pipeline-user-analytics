import pytest

from helpers import OTHER_RECORDING, make_listen, msid
from listens_etl import ingest
from listens_etl.ingest import ingest_file

DAY = 86_400


def count(con, table):
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def listens(n, user="alice", start=1551398400):
    """n distinct listens, one per minute."""
    return [make_listen(user=user, ts=start + 60 * i) for i in range(n)]


def test_loads_all_tables(con, write_export):
    stats = ingest_file(con, write_export([*listens(3), make_listen(user="bob")]))

    assert (stats.lines_read, stats.rows_inserted, stats.rows_rejected) == (4, 4, 0)
    assert count(con, "listens") == 4
    assert count(con, "recordings") == 1
    assert count(con, "artists") == 1
    assert count(con, "users") == 2
    run = con.execute("SELECT status, rows_inserted FROM ingestion_runs").fetchone()
    assert run == ("succeeded", 4)


def test_running_twice_changes_nothing(con, write_export):
    path = write_export(listens(5))
    ingest_file(con, path)
    snapshot = con.execute("SELECT * FROM listens ORDER BY ALL").fetchall()

    stats = ingest_file(con, path)

    assert (stats.rows_inserted, stats.rows_duplicate) == (0, 5)
    assert con.execute("SELECT * FROM listens ORDER BY ALL").fetchall() == snapshot
    assert count(con, "ingestion_runs") == 2


def test_overlapping_files_only_add_new_listens(con, write_export):
    batch = listens(6)
    ingest_file(con, write_export(batch[:4]))
    stats = ingest_file(con, write_export(batch[2:]))

    assert (stats.rows_inserted, stats.rows_duplicate) == (2, 2)
    assert count(con, "listens") == 6


def test_duplicates_within_a_file_are_loaded_once(con, write_export):
    listen = make_listen()
    stats = ingest_file(con, write_export([listen, listen, listen]))

    assert (stats.rows_inserted, stats.rows_duplicate) == (1, 2)
    assert count(con, "listens") == 1


def test_same_second_different_recordings_are_both_kept(con, write_export):
    ingest_file(con, write_export([make_listen(), make_listen(recording=OTHER_RECORDING)]))
    assert count(con, "listens") == 2


def test_corrupt_lines_are_rejected_not_fatal(con, write_export):
    path = write_export(
        [make_listen(), "{not json", make_listen(ts="yesterday"), "", make_listen(user="bob")]
    )
    stats = ingest_file(con, path)

    assert (stats.rows_inserted, stats.rows_rejected) == (2, 3)
    rejected = con.execute(
        "SELECT line_number, split_part(error, ':', 1) FROM rejected_records ORDER BY 1"
    ).fetchall()
    assert rejected == [
        (2, "invalid json"),
        (3, "listened_at is not an integer"),
        (4, "empty line"),
    ]
    raw = con.execute("SELECT raw_line FROM rejected_records WHERE line_number = 2").fetchone()
    assert raw == ("{not json",)


def test_latest_metadata_wins_regardless_of_file_order(con, write_export):
    old = make_listen(ts=1551398400, track="Cornflake (demo)", artist="W. Hand")
    new = make_listen(ts=1551398400 + DAY, track="Cornflake", artist="Withered Hand")

    ingest_file(con, write_export([new]))
    ingest_file(con, write_export([old]))  # older file arrives later

    assert con.execute("SELECT track_name FROM recordings").fetchone() == ("Cornflake",)
    assert con.execute("SELECT artist_name FROM artists").fetchone() == ("Withered Hand",)
    assert count(con, "listens") == 2


def test_failed_run_leaves_no_data(con, write_export, monkeypatch):
    def broken_merge(con, stats):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(ingest, "_merge", broken_merge)
    path = write_export([*listens(3), "{not json"])

    with pytest.raises(RuntimeError):
        ingest_file(con, path)

    for table in ("listens", "recordings", "artists", "rejected_records"):
        assert count(con, table) == 0
    run = con.execute("SELECT status, error FROM ingestion_runs").fetchone()
    assert run == ("failed", "RuntimeError: disk on fire")


def test_batches_are_flushed(con, write_export):
    stats = ingest_file(con, write_export([*listens(7), "bad"]), batch_size=2)
    assert (stats.rows_inserted, stats.rows_rejected) == (7, 1)
    assert count(con, "listens") == 7


def test_references_are_consistent(con, write_export):
    other = make_listen(recording=OTHER_RECORDING, artist_msid=msid(1), artist="Someone")
    ingest_file(con, write_export([make_listen(), other]))
    orphans = con.execute(
        """
        SELECT
            (SELECT count(*) FROM listens ANTI JOIN recordings USING (recording_msid)),
            (SELECT count(*) FROM recordings ANTI JOIN artists USING (artist_msid))
        """
    ).fetchone()
    assert orphans == (0, 0)
