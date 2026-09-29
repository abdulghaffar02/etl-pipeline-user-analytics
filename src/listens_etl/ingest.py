"""Load a ListenBrainz export (one JSON listen per line) into DuckDB.

Safe to re-run: listens are keyed on (user_name, listened_at, recording_msid), so a
file that was already loaded, or overlaps an earlier one, only adds what's new.
Lines that can't be parsed go to rejected_records instead of stopping the run.
Each run is one transaction: it either lands completely or not at all.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, fields
from pathlib import Path

import duckdb
import pyarrow as pa

from listens_etl.parse import InvalidRecord, Listen, parse_line

log = logging.getLogger(__name__)

BATCH_SIZE = 100_000

LISTEN_COLUMNS = ["line_number"] + [f.name for f in fields(Listen)]
REJECT_COLUMNS = ["run_id", "line_number", "raw_line", "error"]


@dataclass
class RunStats:
    run_id: int
    lines_read: int = 0
    rows_inserted: int = 0
    rows_duplicate: int = 0
    rows_rejected: int = 0
    seconds: float = 0.0


def ingest_file(
    con: duckdb.DuckDBPyConnection, path: Path, batch_size: int = BATCH_SIZE
) -> RunStats:
    started = time.perf_counter()
    # The run row is committed on its own first, so a failed run still leaves a trace.
    run_id = con.execute(
        """
        INSERT INTO ingestion_runs (source_file, source_sha256, status, started_at)
        VALUES (?, ?, 'running', now()::TIMESTAMP)
        RETURNING run_id
        """,
        [str(path), _sha256(path)],
    ).fetchone()[0]
    stats = RunStats(run_id=run_id)
    log.info("run %d: loading %s", run_id, path)

    try:
        con.begin()
        _stage(con, path, stats, batch_size)
        _merge(con, stats)
        stats.seconds = round(time.perf_counter() - started, 2)
        con.execute(
            """
            UPDATE ingestion_runs
            SET status = 'succeeded', finished_at = now()::TIMESTAMP, lines_read = ?,
                rows_inserted = ?, rows_duplicate = ?, rows_rejected = ?
            WHERE run_id = ?
            """,
            [
                stats.lines_read,
                stats.rows_inserted,
                stats.rows_duplicate,
                stats.rows_rejected,
                run_id,
            ],
        )
        con.commit()
    except BaseException as e:  # includes Ctrl-C, so the run isn't left as 'running'
        con.rollback()
        con.execute(
            "UPDATE ingestion_runs SET status = 'failed', finished_at = now()::TIMESTAMP, "
            "error = ? WHERE run_id = ?",
            [f"{type(e).__name__}: {e}", run_id],
        )
        log.exception("run %d failed, nothing was loaded", run_id)
        raise

    log.info(
        "run %d: %d lines, %d inserted, %d duplicates, %d rejected (%.1fs)",
        run_id,
        stats.lines_read,
        stats.rows_inserted,
        stats.rows_duplicate,
        stats.rows_rejected,
        stats.seconds,
    )
    return stats


def _stage(con, path: Path, stats: RunStats, batch_size: int) -> None:
    """Parse the file into a temp table, writing unusable lines to rejected_records."""
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE staged_listens (
            line_number     BIGINT,
            user_name       VARCHAR,
            listened_at     TIMESTAMP,
            recording_msid  UUID,
            track_name      VARCHAR,
            artist_name     VARCHAR,
            artist_msid     UUID,
            release_name    VARCHAR,
            release_msid    UUID,
            recording_mbid  UUID,
            additional_info JSON
        )
        """
    )
    listens: list[tuple] = []
    rejects: list[tuple] = []

    # Binary mode, so a line with broken encoding is rejected on its own
    # instead of raising halfway through the file.
    with path.open("rb") as f:
        for line_number, raw in enumerate(f, start=1):
            stats.lines_read += 1
            try:
                listen = parse_line(raw)
            except InvalidRecord as e:
                raw_text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                rejects.append((stats.run_id, line_number, raw_text, str(e)))
                stats.rows_rejected += 1
                continue
            listens.append((line_number, *vars(listen).values()))
            if len(listens) >= batch_size:
                _flush(con, listens, rejects)
    _flush(con, listens, rejects)


def _flush(con, listens: list[tuple], rejects: list[tuple]) -> None:
    # DuckDB reads the local pyarrow table by variable name.
    if listens:
        listen_batch = _to_arrow(LISTEN_COLUMNS, listens)  # noqa: F841
        con.execute("INSERT INTO staged_listens SELECT * FROM listen_batch")
        log.debug("staged %d listens", len(listens))
        listens.clear()
    if rejects:
        reject_batch = _to_arrow(REJECT_COLUMNS, rejects)  # noqa: F841
        con.execute("INSERT INTO rejected_records SELECT * FROM reject_batch")
        rejects.clear()


def _to_arrow(columns: list[str], rows: list[tuple]) -> pa.Table:
    return pa.table(dict(zip(columns, zip(*rows, strict=True), strict=True)))


def _merge(con, stats: RunStats) -> None:
    # Metadata: when the same id shows up with different names, the one from the most
    # recent listen wins, whatever order the files arrive in. On an exact timestamp
    # tie the row that's already there is kept.
    con.execute(
        """
        INSERT INTO artists (artist_msid, artist_name, last_seen_at)
        SELECT artist_msid, artist_name, listened_at
        FROM staged_listens
        QUALIFY row_number() OVER (
            PARTITION BY artist_msid ORDER BY listened_at DESC, line_number DESC) = 1
        ON CONFLICT (artist_msid) DO UPDATE
            SET artist_name = excluded.artist_name, last_seen_at = excluded.last_seen_at
            WHERE excluded.last_seen_at > artists.last_seen_at
        """
    )
    con.execute(
        """
        INSERT INTO recordings (recording_msid, track_name, artist_msid, release_msid,
                                release_name, recording_mbid, last_seen_at)
        SELECT recording_msid, track_name, artist_msid, release_msid, release_name,
               recording_mbid, listened_at
        FROM staged_listens
        QUALIFY row_number() OVER (
            PARTITION BY recording_msid ORDER BY listened_at DESC, line_number DESC) = 1
        ON CONFLICT (recording_msid) DO UPDATE
            SET track_name = excluded.track_name, artist_msid = excluded.artist_msid,
                release_msid = excluded.release_msid, release_name = excluded.release_name,
                recording_mbid = excluded.recording_mbid, last_seen_at = excluded.last_seen_at
            WHERE excluded.last_seen_at > recordings.last_seen_at
        """
    )
    # Duplicates inside the file keep their first occurrence; listens that are
    # already in the table are skipped by the primary key. Sorting by time keeps
    # DuckDB's min/max block stats useful for date filters.
    stats.rows_inserted = con.execute(
        """
        INSERT INTO listens (user_name, listened_at, recording_msid, run_id, additional_info)
        SELECT user_name, listened_at, recording_msid, ?, additional_info
        FROM staged_listens
        QUALIFY row_number() OVER (
            PARTITION BY user_name, listened_at, recording_msid ORDER BY line_number) = 1
        ORDER BY listened_at
        ON CONFLICT DO NOTHING
        """,
        [stats.run_id],
    ).fetchone()[0]
    staged = con.execute("SELECT count(*) FROM staged_listens").fetchone()[0]
    stats.rows_duplicate = staged - stats.rows_inserted


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
