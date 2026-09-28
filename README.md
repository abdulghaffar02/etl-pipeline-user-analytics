# etl-pipeline-user-analytics

[![CI](https://github.com/abdulghaffar02/etl-pipeline-user-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulghaffar02/etl-pipeline-user-analytics/actions/workflows/ci.yml)

Python ETL that loads ListenBrainz listening history (JSON lines) into DuckDB and answers
analytics questions with SQL.

## Requirements

| Tool | Version | Notes |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.5+ | Installs Python 3.12 and all dependencies from `uv.lock` |
| make | any | Optional shortcut layer; every target has a plain-command equivalent |

DuckDB ships inside the `duckdb` Python package — no separate database install or server.

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

Requires Python 3.11+ and pip 25.1+ (for `--group`).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e . --group dev
pytest
```

## Common commands

| make | Plain command | Purpose |
|---|---|---|
| `make setup` | `uv sync && uv run pre-commit install` | Install deps and git hooks |
| `make test` | `uv run pytest` | Run tests |
| `make lint` | `uv run ruff check . && uv run ruff format --check .` | Lint + format check |
| `make fmt` | `uv run ruff check --fix . && uv run ruff format .` | Auto-fix and format |
| `make check` | lint + test | What CI runs |
| `make clean` | — | Remove `.venv`, caches, local DB files |

## Data

The dataset is not committed. Place the export file in `data/` (gitignored).

## Contributing

- `main` is protected: no direct pushes, changes land via squash-merged PRs.
- Branch names: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `test/…`, `ci/…`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org).
- The pre-commit hooks run ruff and block local commits to `main`.
- CI runs on every PR: `lint` (ruff) on Ubuntu, `test` (pytest) on macOS, Ubuntu and Windows.
  All must pass before merging.
- Dependabot opens weekly PRs for GitHub Actions and Python dependency updates.
