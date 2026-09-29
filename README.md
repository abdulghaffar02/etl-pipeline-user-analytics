# etl-pipeline-user-analytics

[![CI](https://github.com/abdulghaffar02/etl-pipeline-user-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulghaffar02/etl-pipeline-user-analytics/actions/workflows/ci.yml)

Python ETL that loads ListenBrainz listening history (JSON lines) into DuckDB and answers
analytics questions with SQL.

## Requirements

| Tool | Version | Notes |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.5+ | Installs Python 3.12 and all dependencies from `uv.lock` |
| make | any | Optional shortcut layer; every target has a plain-command equivalent |

DuckDB comes with the `duckdb` Python package, so there's no separate database to install.

## Setup (macOS)

```bash
brew install uv          # or: curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/abdulghaffar02/etl-pipeline-user-analytics.git
cd etl-pipeline-user-analytics
make setup               # or: uv sync && uv run pre-commit install
```

Verify:

```bash
uv run listens-etl --version
make test                # or: uv run pytest
```

> If `make` or `git` fails with an Xcode license message, run `sudo xcodebuild -license accept` once.

### Linux / Windows

Same commands. On Windows without `make`, use the plain commands shown after each `#`.

### Without uv (pip fallback)

Requires Python 3.11+. Installs the same pinned, hash-checked versions as `uv.lock`
(`requirements*.txt` are generated from it; don't edit them by hand).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt    # runtime only: requirements.txt
pip install -e . --no-deps
pytest
```

## Common commands

| make | Plain command | Purpose |
|---|---|---|
| `make setup` | `uv sync && uv run pre-commit install` | Install deps and git hooks |
| `make init-db` | `uv run listens-etl init-db` | Create the database and tables |
| `make ingest` | `uv run listens-etl ingest data/dataset.txt` | Load the export (`FILE=...` for another file) |
| `make analyze` | `uv run listens-etl analyze --out results` | Run the Task 2 queries, save CSVs |
| `make pipeline` | ingest, then analyze | Everything in one go |
| `make test` | `uv run pytest` | Run tests |
| `make lint` | `uv run ruff check . && uv run ruff format --check .` | Lint + format check |
| `make fmt` | `uv run ruff check --fix . && uv run ruff format .` | Auto-fix and format |
| `make check` | lint + test | What CI runs |
| `make requirements` | see Makefile | Regenerate `requirements*.txt` (the pre-commit hook does this too) |
| `make clean` | | Remove `.venv`, caches, local DB files |

## Data

The dataset is not committed. Copy the export to `data/dataset.txt` (gitignored), then:

```bash
make ingest              # or: uv run listens-etl ingest data/dataset.txt
```

Loading the 333k-line export takes about 5 seconds. Running it again is safe: listens are
keyed on user, timestamp and recording, so nothing is inserted twice, and an overlapping
file only adds the new listens. Lines that can't be used (broken JSON, missing user,
bad timestamp or id, etc.) are skipped and stored in `rejected_records` with the line
number and reason. Each run is logged in `ingestion_runs`:

```sql
SELECT run_id, status, lines_read, rows_inserted, rows_duplicate, rows_rejected
FROM ingestion_runs ORDER BY run_id;
```

The database is created at `data/listens.duckdb`. To put it somewhere else, pass
`--db PATH` or set `LISTENS_DB` (the flag wins). The schema lives in
[`schema.sql`](src/listens_etl/schema.sql) and is applied on every connect, so it's safe
to run `init-db` more than once.

## Analysis

Each Task 2 question is one SQL file in [`src/listens_etl/queries/`](src/listens_etl/queries/):

| File | Question |
|---|---|
| `a1_top_users.sql` | Top 10 users by number of songs listened to |
| `a2_users_on_2019_03_01.sql` | Users who listened to a song on 1 March 2019 |
| `a3_first_song_per_user.sql` | First song each user listened to |
| `b_top_days_per_user.sql` | Each user's top 3 days by listens |
| `c_daily_active_users.sql` | Daily active users over a 7-day window, absolute and % |

```bash
make analyze                                   # all queries, full results in results/*.csv
uv run listens-etl analyze a1_top_users        # just one
uv run listens-etl analyze --rows 50           # print more rows
```

How I read the questions:

- All dates are UTC. `listened_at` is a Unix timestamp, so there's no other timezone to use.
- "Songs listened to" counts every listen, repeats included.
- a3: two users played two songs in the same second as their first listen. ListenBrainz
  marks the later ones with `dedup_tag`, so that decides the order.
- b: ties on the count go to the earlier date. 19 users have fewer than 3 active days, so
  they get fewer than 3 rows.
- c: the percentage is out of all 202 users in the data. The first 6 days have incomplete
  windows and 2019-04-15 only has a few minutes of data; both are left in, not hidden.

## Contributing

- `main` is protected: no direct pushes, changes land via squash-merged PRs.
- Branch names: `feat/`, `fix/`, `chore/`, `docs/`, `test/`, `ci/` prefixes.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org).
- The pre-commit hooks run ruff and block local commits to `main`.
- CI runs on every PR, and all jobs must pass before merging:
  - `lint`: ruff, plus a check that `requirements*.txt` match `uv.lock`.
  - `test`: pytest on macOS, Ubuntu and Windows.
  - `pip-fallback`: the "Without uv" steps above, on macOS.
- Dependabot opens weekly PRs for GitHub Actions and Python dependency updates.
