"""Builders for test input shaped like the ListenBrainz export."""

import json

ARTIST = "f1d39567-27e7-40af-852a-abaed88ec838"
RECORDING = "1e1b2aa0-b2db-42ed-a8ba-89c303499408"
OTHER_RECORDING = "283062c8-75e2-406a-8c5e-f38136aa5a68"


def make_listen(
    user="alice",
    ts=1551398400,  # 2019-03-01 00:00:00 UTC
    recording=RECORDING,
    track="Cornflake",
    artist="Withered Hand",
    artist_msid=ARTIST,
    **extra_info,
) -> dict:
    """A listen shaped like the ListenBrainz export."""
    return {
        "track_metadata": {
            "additional_info": {
                "artist_msid": artist_msid,
                "recording_msid": recording,
                "release_msid": None,
                "tags": [],
                **extra_info,
            },
            "artist_name": artist,
            "track_name": track,
            "release_name": "Good News",
        },
        "listened_at": ts,
        "recording_msid": recording,
        "user_name": user,
    }


def to_line(listen: dict) -> str:
    return json.dumps(listen)


def msid(n: int) -> str:
    """A distinct, valid msid per number, for tests that need many recordings."""
    return f"00000000-0000-4000-8000-{n:012d}"
