# etl-pipeline-user-analytics

[![CI](https://github.com/abdulghaffar02/etl-pipeline-user-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulghaffar02/etl-pipeline-user-analytics/actions/workflows/ci.yml)

Loads a ListenBrainz listening-history export (one JSON listen per line) into DuckDB and
answers the Task 2 questions in SQL. The answers are in [`results/`](results/), one CSV
per question.

## Quickstart (macOS)

You need [uv](https://docs.astral.sh/uv/) (`brew install uv`). It installs Python 3.12 and
the pinned dependencies. DuckDB is just a Python package here, there's no server to run.

```bash
git clone https://github.com/abdulghaffar02/etl-pipeline-user-analytics.git
cd etl-pipeline-user-analytics
cp /path/to/dataset.txt data/dataset.txt
```

```bash
make setup
make pipeline
```

`make pipeline` loads the file (a few seconds), runs the queries, prints the results and
writes them to `results/`.

If `make` or `git` complains about the Xcode license, run `sudo xcodebuild -license accept` once.

## Project layout

```
src/listens_etl/
  cli.py           listens-etl command: init-db, ingest, analyze
  parse.py         one line -> Listen or InvalidRecord
  ingest.py        stage, merge, run log
  db.py            connection (UTC) and schema
  schema.sql
  queries/*.sql    one file per Task 2 question
  analysis.py      runs the queries
  config.py        database path: --db, then $LISTENS_DB, then data/listens.duckdb
tests/             pytest, small hand-built exports in each test
results/           query results, one CSV per question
```

## Commands

| make | Plain command | Purpose |
|---|---|---|
| `make setup` | `uv sync && uv run pre-commit install` | Install deps and git hooks |
| `make init-db` | `uv run listens-etl init-db` | Create the database and tables |
| `make ingest` | `uv run listens-etl ingest data/dataset.txt` | Load the export (`FILE=...` for another file) |
| `make analyze` | `uv run listens-etl analyze --out results` | Run the queries, write the CSVs |
| `make pipeline` | ingest, then analyze | Everything in one go |
| `make test` | `uv run pytest` | Run tests |
| `make lint` | `uv run ruff check . && uv run ruff format --check .` | Lint and format check |
| `make fmt` | `uv run ruff check --fix . && uv run ruff format .` | Auto-fix and format |
| `make check` | lint, then test | What CI runs |
| `make clean` | | Remove `.venv`, caches, local database |

The database lives at `data/listens.duckdb`. Use `--db PATH` or `LISTENS_DB` to put it
somewhere else (the flag wins).

On Linux and Windows the commands are the same. Without `make` (usually the case on
Windows), use the plain commands.

## Contributing

- `main` is protected: no direct pushes, changes land through squash-merged PRs.
- Branch names start with `feat/`, `fix/`, `chore/`, `docs/`, `test/` or `ci/`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org).
- The pre-commit hooks run ruff and refuse commits to `main`.
- CI runs on every PR and has to pass before merging: `lint`, `test` on macOS, Ubuntu
  and Windows, and `test (python 3.11)` for the lowest supported Python.
- Dependabot opens weekly PRs to update the pinned GitHub Actions.

## How it works

1. [`parse.py`](src/listens_etl/parse.py) turns each line into a `Listen` or rejects it
   with a reason. The file is read in binary mode, which means one badly encoded line
   can't stop the run.
2. Valid listens are staged in a temp table in batches of 100k. Rejected lines go to
   `rejected_records` with their line number and the reason. That table is per run:
   loading the same file twice logs its bad lines twice.
3. [`ingest.py`](src/listens_etl/ingest.py) upserts artists and recordings, then inserts
   the listens with `ON CONFLICT DO NOTHING`.
4. Every run is logged in `ingestion_runs` with the file hash and counts. A run is one
   transaction. If anything fails nothing is loaded, and the run shows up as `failed`.

```sql
SELECT run_id, status, lines_read, rows_inserted, rows_duplicate, rows_rejected
FROM ingestion_runs ORDER BY run_id;
```

### Schema

Defined in [`schema.sql`](src/listens_etl/schema.sql) and applied on every connect.

| Table / view | One row per | Key |
|---|---|---|
| `listens` | listen | `user_name, listened_at, recording_msid` |
| `recordings` | recording | `recording_msid` |
| `artists` | artist | `artist_msid` |
| `users` (view) | user, with first/last listen and count | `user_name` |
| `listens_enriched` (view) | listen, with track, artist and release names | |
| `ingestion_runs` | load run | `run_id` |
| `rejected_records` | unusable line | `run_id, line_number` |

For the analysis:

- Each load inserts listens in time order, so date filters (like a2's `listened_at` range)
  skip most of the table.
- `listened_date` is a computed column the daily queries group by.
- Ids use DuckDB's `UUID` type: 16 bytes each, and a malformed id fails on insert.
- No extra indexes. DuckDB is a column store and these queries read whole columns.

## Analysis

One SQL file per question in [`src/listens_etl/queries/`](src/listens_etl/queries/). All
dates are UTC.

| File | Question | How I read it |
|---|---|---|
| `a1_top_users.sql` | Top 10 users by songs listened to | Every listen counts. `distinct_songs` covers the other reading (hds: 46,885 listens, 102 recordings) |
| `a2_users_on_2019_03_01.sql` | Users who listened on 1 March 2019 | The UTC day |
| `a3_first_song_per_user.sql` | First song per user | Same-second ties are ordered by ListenBrainz's `dedup_tag` |
| `b_top_days_per_user.sql` | Top 3 days per user | Ties go to the earlier date. Users with fewer than 3 active days get fewer rows |
| `c_daily_active_users.sql` | Daily active users, 7-day window | Percentage of all users. The first six days have incomplete windows, and 15 April has only a few minutes of data |

For c I divide by all users rather than the users seen so far, which would put 1 January
at 100%. One user name contains a replacement character (`�`); it's like that in the
export. Run a single query with `uv run listens-etl analyze a1_top_users`.

## Design decisions

- Listens are keyed on `(user_name, listened_at, recording_msid)`. User and timestamp
  alone aren't unique: the export has 7,126 same-second plays of two recordings.
- The key makes re-runs safe. The same file inserts nothing, an overlapping file only
  adds new listens, and duplicates within a file keep the first copy.
- Required fields are validated strictly. A malformed optional id like `release_msid`
  becomes NULL instead of dropping the listen.
- When a recording or artist has conflicting names, the most recent listen wins,
  whatever the load order.
- The session is set to UTC. DuckDB's default local timezone put listens near midnight
  on the wrong day.
- No foreign keys: they slow down bulk loads in DuckDB. A test checks for orphans.
- `additional_info` is kept per listen with empty keys dropped, since keys like
  `dedup_tag` describe the listen.
- c spreads each (user, active day) over the 7 days it counts for and counts users once
  per day. Summing daily counts would count some users several times.
- Every answer was cross-checked against a separate Python calculation on the raw file.

## Trade-offs and next steps

- Parsing in Python checks each line on its own. DuckDB's `json_transform` was more than
  twice as fast, but one bad value fails the whole batch. For the full dump I'd switch
  and use `TRY_CAST` everywhere.
- `read_json(ignore_errors=true)` is faster still, but it accepted most of my deliberately
  broken lines as valid rows.
- The file hash isn't used to skip files already loaded. Reprocessing is cheap and always
  correct.
- At a larger scale: `users` as a table, listens partitioned by date, and scheduled loads
  with an alert on the reject rate.
- Not done: a Docker image, type checking, a chart for c.
