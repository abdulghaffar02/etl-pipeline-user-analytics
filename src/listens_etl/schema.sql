-- Applied on every connect, so every statement must be safe to re-run.
-- All timestamps are UTC (the connection forces TimeZone = 'UTC').
--
-- No foreign keys on purpose: they slow down bulk inserts in DuckDB and block
-- updating referenced rows. The loader keeps the references consistent and the
-- tests check it.

CREATE SEQUENCE IF NOT EXISTS ingestion_run_id_seq;

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id         INTEGER PRIMARY KEY DEFAULT nextval('ingestion_run_id_seq'),
    source_file    VARCHAR NOT NULL,
    source_sha256  VARCHAR NOT NULL,
    status         VARCHAR NOT NULL,  -- running | succeeded | failed
    started_at     TIMESTAMP NOT NULL,
    finished_at    TIMESTAMP,
    lines_read     BIGINT,
    rows_inserted  BIGINT,
    rows_duplicate BIGINT,
    rows_rejected  BIGINT,
    error          VARCHAR
);

CREATE TABLE IF NOT EXISTS rejected_records (
    run_id      INTEGER NOT NULL,
    line_number BIGINT NOT NULL,
    raw_line    VARCHAR NOT NULL,
    error       VARCHAR NOT NULL,
    PRIMARY KEY (run_id, line_number)
);

CREATE TABLE IF NOT EXISTS artists (
    artist_msid  UUID PRIMARY KEY,
    artist_name  VARCHAR NOT NULL,
    -- listened_at of the listen this name came from; the most recent one wins
    last_seen_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS recordings (
    recording_msid  UUID PRIMARY KEY,
    track_name      VARCHAR NOT NULL,
    artist_msid     UUID NOT NULL,
    release_msid    UUID,
    release_name    VARCHAR,
    recording_mbid  UUID,
    last_seen_at    TIMESTAMP NOT NULL
);

-- One row per listen. A user can play two different recordings in the same
-- second (7k cases in the sample export), so the recording is part of the key.
CREATE TABLE IF NOT EXISTS listens (
    user_name      VARCHAR NOT NULL,
    listened_at    TIMESTAMP NOT NULL,
    recording_msid UUID NOT NULL,
    run_id         INTEGER NOT NULL,
    -- remaining non-empty track_metadata.additional_info keys. Kept per listen
    -- because some of them (dedup_tag, listening_from) describe the listen.
    additional_info JSON,
    listened_date  DATE GENERATED ALWAYS AS (CAST(listened_at AS DATE)) VIRTUAL,
    PRIMARY KEY (user_name, listened_at, recording_msid)
);

-- Derived from listens rather than stored, so it can never go stale.
CREATE OR REPLACE VIEW users AS
SELECT
    user_name,
    min(listened_at) AS first_listened_at,
    max(listened_at) AS last_listened_at,
    count(*)         AS listen_count
FROM listens
GROUP BY user_name;

CREATE OR REPLACE VIEW listens_enriched AS
SELECT
    l.user_name,
    l.listened_at,
    l.listened_date,
    l.recording_msid,
    r.track_name,
    a.artist_name,
    r.release_name,
    l.additional_info
FROM listens l
LEFT JOIN recordings r ON r.recording_msid = l.recording_msid
LEFT JOIN artists a ON a.artist_msid = r.artist_msid;
