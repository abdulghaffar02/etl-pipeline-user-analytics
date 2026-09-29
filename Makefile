# Thin convenience wrapper. Every target maps to a plain `uv run ...` command (see README),
# so the project also works on machines without `make` (e.g. Windows).

.DEFAULT_GOAL := help
FILE ?= data/dataset.txt
.PHONY: help setup check-uv requirements init-db ingest analyze pipeline test lint fmt check clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-13s %s\n", $$1, $$2}'

check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "uv not found. Install: brew install uv  (or see https://docs.astral.sh/uv/)"; exit 1; }

setup: check-uv ## Create .venv, install locked dependencies and git hooks
	uv sync
	uv run pre-commit install

requirements: ## Regenerate requirements*.txt from uv.lock (pip fallback)
	uv export --frozen --no-dev --no-emit-project --quiet --output-file=requirements.txt
	uv export --frozen --no-emit-project --quiet --output-file=requirements-dev.txt

init-db: ## Create the database (override location with LISTENS_DB=path)
	uv run listens-etl init-db

ingest: ## Load an export file (default FILE=data/dataset.txt)
	uv run listens-etl ingest $(FILE)

analyze: ## Run the Task 2 queries and save full results to results/
	uv run listens-etl analyze --out results

pipeline: ingest analyze ## ingest + analyze

test: ## Run the test suite
	uv run pytest

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

fmt: ## Auto-fix lint issues and format code
	uv run ruff check --fix .
	uv run ruff format .

check: lint test ## Lint + tests (what CI runs)

clean: ## Remove virtualenv, caches and local database files
	rm -rf .venv .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f data/*.duckdb data/*.duckdb.wal
