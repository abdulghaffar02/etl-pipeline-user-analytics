import json
from datetime import datetime

import pytest

from helpers import ARTIST, RECORDING, make_listen
from listens_etl.parse import InvalidRecord, parse_line


def parse(doc) -> object:
    raw = doc if isinstance(doc, bytes) else json.dumps(doc).encode()
    return parse_line(raw)


def test_valid_listen():
    listen = parse(make_listen())
    assert listen.user_name == "alice"
    assert listen.listened_at == datetime(2019, 3, 1, 0, 0, 0)
    assert listen.recording_msid == RECORDING
    assert listen.artist_msid == ARTIST
    assert listen.track_name == "Cornflake"
    assert listen.artist_name == "Withered Hand"
    assert listen.release_name == "Good News"
    assert listen.release_msid is None
    assert listen.additional_info is None  # only empty / extracted keys


def test_additional_info_keeps_only_non_empty_extra_keys():
    listen = parse(make_listen(dedup_tag=1, isrc=None, artist_mbids=[]))
    assert json.loads(listen.additional_info) == {"dedup_tag": 1}


def test_uuids_are_normalised():
    listen = parse(make_listen(recording=RECORDING.upper()))
    assert listen.recording_msid == RECORDING


def test_bad_optional_ids_become_null():
    listen = parse(make_listen(release_msid="garbage", recording_mbid=42))
    assert listen.release_msid is None
    assert listen.recording_mbid is None


def test_missing_release_name_is_allowed():
    doc = make_listen()
    del doc["track_metadata"]["release_name"]
    assert parse(doc).release_name is None


def without(key):
    doc = make_listen()
    del doc[key]
    return doc


def with_meta(**changes):
    doc = make_listen()
    doc["track_metadata"].update(changes)
    return doc


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (b"", "empty line"),
        (b"   \n", "empty line"),
        (b'{"user_name": ', "invalid json"),
        (b"\xff\xfe not utf-8", "invalid utf-8"),
        (b"[1, 2, 3]", "not a json object"),
        (without("user_name"), "missing user_name"),
        (make_listen(user="  "), "missing user_name"),
        (without("listened_at"), "listened_at is not an integer"),
        (make_listen(ts="1551398400"), "listened_at is not an integer"),
        (make_listen(ts=1551398400.5), "listened_at is not an integer"),
        (make_listen(ts=True), "listened_at is not an integer"),
        (make_listen(ts=-1), "listened_at is negative"),
        (make_listen(ts=10**20), "listened_at out of range"),
        (make_listen(recording="nope"), "invalid recording_msid"),
        (without("track_metadata"), "missing track_metadata"),
        (with_meta(track_name=""), "missing track_name"),
        (with_meta(artist_name=None), "missing artist_name"),
        (with_meta(additional_info="oops"), "additional_info is not an object"),
        (make_listen(artist_msid=None), "invalid artist_msid"),
    ],
)
def test_rejected(raw, reason):
    with pytest.raises(InvalidRecord, match=reason):
        parse(raw)
