import argparse
from collections.abc import Sequence

from listens_etl import __version__, db
from listens_etl.config import DB_PATH_ENV_VAR, resolve_db_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="listens-etl",
        description="Load ListenBrainz listens into DuckDB and run analytics queries.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # options shared by every subcommand
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--db",
        help=f"DuckDB file (default: ${DB_PATH_ENV_VAR} or data/listens.duckdb)",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", parents=[common], help="create the database and tables")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = resolve_db_path(args.db)

    if args.command == "init-db":
        db.connect(db_path).close()
        print(f"Database ready: {db_path}")
    return 0
