import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from listens_etl import __version__, db
from listens_etl.config import DB_PATH_ENV_VAR, resolve_db_path
from listens_etl.ingest import ingest_file


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
    common.add_argument("-v", "--verbose", action="store_true", help="debug logging")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", parents=[common], help="create the database and tables")

    ingest = sub.add_parser("ingest", parents=[common], help="load an export file")
    ingest.add_argument("file", type=Path, help="JSON lines export, one listen per line")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    db_path = resolve_db_path(args.db)

    if args.command == "init-db":
        db.connect(db_path).close()
        print(f"Database ready: {db_path}")

    elif args.command == "ingest":
        if not args.file.is_file():
            parser.error(f"file not found: {args.file}")
        con = db.connect(db_path)
        try:
            ingest_file(con, args.file)
        finally:
            con.close()
    return 0
