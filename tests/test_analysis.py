from datetime import date, datetime

import pytest

from helpers import make_listen, msid
from listens_etl import analysis
from listens_etl.ingest import ingest_file

T0 = 1551398400  # 2019-03-01 00:00:00 UTC
DAY = 86_400


@pytest.fixture
def load(con, write_export):
    def load(lines):
        ingest_file(con, write_export(lines))
        return con

    return load


def listen(user, ts, n=0, **kw):
    """One listen of recording msid(n); each recording gets its own track name."""
    return make_listen(user=user, ts=ts, recording=msid(n), track=f"track {n}", **kw)


def rows(con, name):
    return analysis.run(con, name).fetchall()


def test_every_query_file_is_listed():
    assert analysis.query_names() == [
        "a1_top_users",
        "a2_users_on_2019_03_01",
        "a3_first_song_per_user",
        "b_top_days_per_user",
        "c_daily_active_users",
    ]
    assert analysis.describe("a1_top_users").startswith("Top 10 users")


def test_top_users_counts_every_listen_and_breaks_ties_by_name(load):
    lines = []
    for i in range(1, 13):  # u01 has 1 listen ... u12 has 12
        lines += [listen(f"u{i:02d}", T0 + 60 * k) for k in range(i)]
    lines += [listen("aaa", T0 + 60 * k) for k in range(12)]  # ties with u12
    con = load(lines)

    expected = [("aaa", 12), ("u12", 12)] + [(f"u{i:02d}", i) for i in range(11, 3, -1)]
    assert [(user, n) for user, n, _ in rows(con, "a1_top_users")] == expected


def test_top_users_ranks_by_plays_and_shows_distinct_songs(load):
    con = load(
        [
            *[listen("alice", T0 + 60 * k, n=1) for k in range(3)],  # one song on repeat
            listen("alice", T0 + 600, n=2),
            *[listen("bob", T0 + 60 * k, n=10 + k) for k in range(3)],  # three different songs
        ]
    )
    assert rows(con, "a1_top_users") == [("alice", 4, 2), ("bob", 3, 3)]


def test_users_on_march_first_uses_utc_day_boundaries(load):
    con = load(
        [
            listen("before", T0 - 1),  # 2019-02-28 23:59:59
            listen("start", T0),  # 2019-03-01 00:00:00
            listen("start", T0 + 12 * 3600, n=1),  # same user again, counted once
            listen("end", T0 + DAY - 1),  # 2019-03-01 23:59:59
            listen("after", T0 + DAY),  # 2019-03-02 00:00:00
        ]
    )
    assert rows(con, "a2_users_on_2019_03_01") == [(2,)]


def test_first_song_per_user(load):
    con = load(
        [
            listen("alice", T0 + 100, n=1),
            listen("alice", T0, n=2),
            # same second: the untagged play came first, even though its msid sorts later
            listen("bob", T0, n=3, dedup_tag=1),
            listen("bob", T0, n=4),
        ]
    )
    result = [(user, track) for user, _, track, *_ in rows(con, "a3_first_song_per_user")]
    assert result == [("alice", "track 2"), ("bob", "track 4")]


def test_first_song_row_has_time_and_metadata(load):
    con = load([listen("alice", T0)])
    assert rows(con, "a3_first_song_per_user") == [
        ("alice", datetime(2019, 3, 1), "track 0", "Withered Hand", "Good News")
    ]


def test_top_days_per_user(load):
    d1, d2, d3, d4 = T0, T0 + DAY, T0 + 2 * DAY, T0 + 3 * DAY
    per_day = {d1: 5, d2: 4, d3: 2, d4: 2}  # 3rd and 4th day tie
    lines = [listen("alice", day + 60 * k) for day, n in per_day.items() for k in range(n)]
    lines += [listen("bob", d1 + 60 * k) for k in range(2)]  # only one active day
    con = load(lines)

    assert rows(con, "b_top_days_per_user") == [
        ("alice", 5, date(2019, 3, 1)),
        ("alice", 4, date(2019, 3, 2)),
        ("alice", 2, date(2019, 3, 3)),  # earlier date wins the tie with 2019-03-04
        ("bob", 2, date(2019, 3, 1)),
    ]


def test_daily_active_users_rolling_window(load):
    con = load(
        [
            listen("alice", T0),  # day 0 only
            listen("carol", T0 + 2 * DAY),
            listen("carol", T0 + 3 * DAY),  # two days in one window, counted once
            listen("bob", T0 + 7 * DAY),
        ]
    )
    result = rows(con, "c_daily_active_users")

    # one row per calendar day, including days nobody listened
    assert [d for d, *_ in result] == [date(2019, 3, 1 + i) for i in range(8)]
    # alice is active through day 6 (window [X-6, X] includes day 0), gone on day 7
    assert [n for _, n, _ in result] == [1, 1, 2, 2, 2, 2, 2, 2]
    assert [float(p) for *_, p in result][:3] == [33.33, 33.33, 66.67]


def test_daily_active_users_on_empty_database(con):
    assert rows(con, "c_daily_active_users") == []
