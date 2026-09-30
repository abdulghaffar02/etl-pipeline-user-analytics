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

Some choices that make the analysis easier:

- Listens are inserted in time order. DuckDB keeps min/max values per block, and a date
  filter can skip most of the table. The a2 query filters on a plain `listened_at` range
  for that reason.
- `listened_date` is a computed column, and the daily queries group by it directly.
- Ids use DuckDB's `UUID` type: 16 bytes each, and a malformed id fails on insert.
- The joins to track, artist and release names live in the `listens_enriched` view.
  Per-user stats are in `users`.
- I didn't add indexes. DuckDB is a column store and these queries read whole columns
  anyway. The primary key is only there to keep listens unique.

## Analysis

One SQL file per question in [`src/listens_etl/queries/`](src/listens_etl/queries/):

| File | Question |
|---|---|
| `a1_top_users.sql` | Top 10 users by number of songs listened to |
| `a2_users_on_2019_03_01.sql` | How many users listened to a song on 1 March 2019 |
| `a3_first_song_per_user.sql` | First song each user listened to |
| `b_top_days_per_user.sql` | Each user's top 3 days by listens |
| `c_daily_active_users.sql` | Daily active users over a 7-day window, count and % |

```bash
make analyze                                # all queries, CSVs in results/
uv run listens-etl analyze a1_top_users     # just one
uv run listens-etl analyze --rows 50        # print more rows
```

How I read the questions:

- Dates are UTC. `listened_at` is a Unix timestamp and the data has no user timezone.
- a1: I count every listen, repeats included. Counting distinct songs instead changes the
  top 10 a lot. hds is first with 46,885 listens but played only 102 different recordings.
  That's why the query also returns `distinct_songs`.
- a3: in two cases a user's first listen shares its second with another one. ListenBrainz
  sets `dedup_tag` on the later plays, and I use that to order them.
- b: ties go to the earlier date. Users with fewer than 3 active days get fewer rows.
- c: the percentage is out of all users in the data. I thought about dividing by the users
  seen so far, but then 1 January comes out at 100% and the first weeks mostly measure
  sign-ups. The first six days have incomplete windows and the last day only has a few
  minutes of data. I kept both.
- One user name contains the Unicode replacement character (`�`). It's like that in
  the export and I left it alone.

## Design decisions

- A listen is identified by `(user_name, listened_at, recording_msid)`. User and
  timestamp aren't unique on their own: the export has 7,126 cases of someone playing two
  recordings in the same second.
- That key is what makes re-runs safe. The same file again inserts nothing, an
  overlapping file only adds the new listens, and duplicates within a file keep the
  first copy.
- Validation is strict for what a listen needs (user, timestamp, recording id, track,
  artist and artist id). Malformed optional ids like `release_msid` become NULL. I'd
  rather keep the listen than lose it over an id nobody queries.
- If a recording or artist shows up with different names, the most recent listen wins.
  The order in which files are loaded doesn't change the result.
- The connection is set to UTC. DuckDB otherwise uses the machine's timezone, which put
  listens near midnight on the wrong day on my laptop (Berlin time).
- No foreign keys. In DuckDB they slow down bulk loads and get in the way of updating
  referenced rows. A test checks for orphans instead.
- `additional_info` is stored per listen with the empty keys dropped. Some of its keys,
  like `dedup_tag` and `listening_from`, are about the listen itself.
- For c, each (user, active day) is spread over the 7 days it counts for, and users are
  counted once per day. Summing the daily counts over a window would count people
  several times.
- Before writing the tests I cross-checked every answer with a quick Python script over
  the raw file.

## Trade-offs and next steps

- Parsing happens in Python, which lets every line be checked on its own. I also tried
  parsing in DuckDB with `json_transform`. It was more than twice as fast, but one
  unexpected value can fail a whole batch. For the full ListenBrainz dump I'd switch and
  use `TRY_CAST` everywhere.
- DuckDB's `read_json(ignore_errors=true)` is faster still. In my tests it loaded most of
  the deliberately broken lines as valid rows and dropped the rest without saying so.
- The file hash is recorded but not used to skip files that were already loaded.
  Reprocessing takes seconds and is always correct; skipping would need a `--force` flag.
- At a bigger scale I'd turn `users` into a table, partition listens by date and run the
  load from a scheduler, with an alert on the reject rate.
- Not done: a Docker image, type checking, a chart for c.

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
