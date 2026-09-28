import duckdb
import pytest

from listens_etl import db

USER = "alice"
RECORDING = "1e1b2aa0-b2db-42ed-a8ba-89c303499408"
OTHER_RECORDING = "283062c8-75e2-406a-8c5e-f38136aa5a68"


def insert_listen(con, listened_at, recording=RECORDING, user=USER):
    con.execute(
        "INSERT INTO listens (user_name, listened_at, recording_msid, run_id) VALUES (?, ?, ?, 1)",
        [user, listened_at, recording],
    )


def scalar(con, sql, params=None):
    return con.execute(sql, params or []).fetchone()[0]


def columns(con, table):
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ? "
        "ORDER BY ordinal_position",
        [table],
    ).fetchall()
    return [r[0] for r in rows]


def test_schema_objects_exist(con):
    rows = con.execute("SELECT table_name FROM information_schema.tables").fetchall()
    tables = {r[0] for r in rows}
    assert {
        "ingestion_runs",
        "rejected_records",
        "artists",
        "recordings",
        "listens",
        "users",
        "listens_enriched",
    } <= tables
    assert columns(con, "listens") == [
        "user_name",
        "listened_at",
        "recording_msid",
        "run_id",
        "listened_date",
    ]


def test_schema_can_be_applied_again(tmp_path):
    path = tmp_path / "again.duckdb"
    con = db.connect(path)
    insert_listen(con, "2019-03-01 10:00:00")
    con.close()

    con = db.connect(path)
    db.init_schema(con)
    assert scalar(con, "SELECT count(*) FROM listens") == 1
    con.close()


def test_session_timezone_is_utc(con):
    assert scalar(con, "SELECT current_setting('TimeZone')") == "UTC"
    # 2019-03-01 00:00:00 UTC must not shift to another day
    assert scalar(con, "SELECT to_timestamp(1551398400)::DATE::VARCHAR") == "2019-03-01"


def test_duplicate_listen_is_rejected(con):
    insert_listen(con, "2019-03-01 10:00:00")
    with pytest.raises(duckdb.ConstraintException):
        insert_listen(con, "2019-03-01 10:00:00")


def test_same_second_different_recording_is_allowed(con):
    insert_listen(con, "2019-03-01 10:00:00")
    insert_listen(con, "2019-03-01 10:00:00", recording=OTHER_RECORDING)
    assert scalar(con, "SELECT count(*) FROM listens") == 2


def test_listened_date_follows_listened_at(con):
    insert_listen(con, "2019-02-28 23:59:59")
    insert_listen(con, "2019-03-01 00:00:00", recording=OTHER_RECORDING)
    rows = con.execute("SELECT listened_date::VARCHAR FROM listens ORDER BY listened_at")
    assert rows.fetchall() == [("2019-02-28",), ("2019-03-01",)]


def test_invalid_msid_is_rejected(con):
    with pytest.raises(duckdb.ConversionException):
        insert_listen(con, "2019-03-01 10:00:00", recording="not-a-uuid")


def test_users_view(con):
    insert_listen(con, "2019-03-01 10:00:00")
    insert_listen(con, "2019-03-02 10:00:00")
    row = con.execute(
        "SELECT user_name, first_listened_at::VARCHAR, listen_count FROM users"
    ).fetchone()
    assert row == (USER, "2019-03-01 10:00:00", 2)


def test_listens_enriched_view(con):
    artist = "f1d39567-27e7-40af-852a-abaed88ec838"
    seen = "2019-03-01 10:00:00"
    con.execute("INSERT INTO artists VALUES (?, 'Withered Hand', ?)", [artist, seen])
    con.execute(
        """
        INSERT INTO recordings (recording_msid, track_name, artist_msid, release_name, last_seen_at)
        VALUES (?, 'Cornflake', ?, 'Good News', ?)
        """,
        [RECORDING, artist, seen],
    )
    insert_listen(con, "2019-03-01 10:00:00")
    insert_listen(con, "2019-03-01 11:00:00", recording=OTHER_RECORDING)  # no metadata yet

    rows = con.execute(
        "SELECT track_name, artist_name, release_name FROM listens_enriched ORDER BY listened_at"
    ).fetchall()
    assert rows == [("Cornflake", "Withered Hand", "Good News"), (None, None, None)]
