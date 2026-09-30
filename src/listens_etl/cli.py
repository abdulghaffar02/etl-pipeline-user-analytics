import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from listens_etl import __version__, analysis, db
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

    analyze = sub.add_parser("analyze", parents=[common], help="run the Task 2 queries")
    # no choices=: with nargs="*" Python 3.11's argparse rejects an empty list
    analyze.add_argument(
        "queries",
        nargs="*",
        metavar="QUERY",
        help=f"which queries to run (default: all). One of: {', '.join(analysis.query_names())}",
    )
    analyze.add_argument("--out", type=Path, help="also write each full result to DIR/<query>.csv")
    analyze.add_argument("--rows", type=int, default=20, help="rows to print per query")
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

    elif args.command == "analyze":
        unknown = [q for q in args.queries if q not in analysis.query_names()]
        if unknown:
            parser.error(
                f"unknown query: {', '.join(unknown)} "
                f"(choose from {', '.join(analysis.query_names())})"
            )
        return _analyze(args, db_path)
    return 0


def _analyze(args, db_path: Path) -> int:
    hint = "Run `listens-etl ingest FILE` first."
    if not db_path.exists():
        print(f"No database at {db_path}. {hint}", file=sys.stderr)
        return 1
    con = db.connect(db_path)
    try:
        if con.execute("SELECT count(*) FROM listens").fetchone()[0] == 0:
            print(f"{db_path} has no listens. {hint}", file=sys.stderr)
            return 1
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)

        for name in args.queries or analysis.query_names():
            result = analysis.run(con, name)
            print(f"\n{name}: {analysis.describe(name)}")
            result.show(max_rows=args.rows)
            if args.out:
                result.write_csv(str(args.out / f"{name}.csv"))
        if args.out:
            print(f"\nFull results written to {args.out}/")
    finally:
        con.close()
    return 0
