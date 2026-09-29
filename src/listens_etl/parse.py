"""Turn one line of the export into a validated Listen, or explain why it can't be used."""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

# Pulled out into their own columns, so they aren't repeated in additional_info.
EXTRACTED_KEYS = {"artist_msid", "recording_msid", "release_msid", "recording_mbid"}
EMPTY = (None, "", [], {})


class InvalidRecord(ValueError):
    pass


@dataclass(frozen=True)
class Listen:
    user_name: str
    listened_at: datetime  # naive, UTC
    recording_msid: str
    track_name: str
    artist_name: str
    artist_msid: str
    release_name: str | None
    release_msid: str | None
    recording_mbid: str | None
    additional_info: str | None  # JSON text


def parse_line(raw: bytes) -> Listen:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise InvalidRecord(f"invalid utf-8: {e}") from None
    if not text.strip():
        raise InvalidRecord("empty line")
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidRecord(f"invalid json: {e}") from None
    if not isinstance(doc, dict):
        raise InvalidRecord("not a json object")

    user_name = _required_str(doc, "user_name")
    listened_at = _timestamp(doc.get("listened_at"))
    recording_msid = _uuid(doc.get("recording_msid"), "recording_msid")

    meta = doc.get("track_metadata")
    if not isinstance(meta, dict):
        raise InvalidRecord("missing track_metadata")
    track_name = _required_str(meta, "track_name")
    artist_name = _required_str(meta, "artist_name")

    info = meta.get("additional_info") or {}
    if not isinstance(info, dict):
        raise InvalidRecord("additional_info is not an object")
    artist_msid = _uuid(info.get("artist_msid"), "artist_msid")

    release_name = meta.get("release_name")
    extra = {k: v for k, v in info.items() if k not in EXTRACTED_KEYS and v not in EMPTY}

    return Listen(
        user_name=user_name,
        listened_at=listened_at,
        recording_msid=recording_msid,
        track_name=track_name,
        artist_name=artist_name,
        artist_msid=artist_msid,
        release_name=release_name if isinstance(release_name, str) and release_name else None,
        # optional ids: a bad value shouldn't cost us the listen
        release_msid=_optional_uuid(info.get("release_msid")),
        recording_mbid=_optional_uuid(info.get("recording_mbid")),
        additional_info=json.dumps(extra) if extra else None,
    )


def _required_str(doc: dict, key: str) -> str:
    value = doc.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRecord(f"missing {key}")
    return value


def _timestamp(value) -> datetime:
    # bool is a subclass of int, and floats would silently drop precision
    if type(value) is not int:
        raise InvalidRecord(f"listened_at is not an integer: {value!r}")
    if value < 0:
        raise InvalidRecord(f"listened_at is negative: {value}")
    try:
        return datetime.fromtimestamp(value, UTC).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        raise InvalidRecord(f"listened_at out of range: {value}") from None


def _uuid(value, key: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise InvalidRecord(f"invalid {key}: {value!r}") from None


def _optional_uuid(value) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError, AttributeError):
        return None
