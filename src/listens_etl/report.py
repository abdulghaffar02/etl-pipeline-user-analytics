"""Write the Task 2 answers as a Markdown file (RESULTS.md)."""

from pathlib import PureWindowsPath

import duckdb

from listens_etl import analysis

# Long results are cut in the Markdown; the CSVs always have everything.
PREVIEW_ROWS = 20


def markdown_report(con: duckdb.DuckDBPyConnection, names: list[str], csv_dir=None) -> str:
    lines = ["# Results", "", _source_line(con), ""]
    if csv_dir:
        lines += [f"Full results for every query are in [`{csv_dir}/`]({csv_dir}/).", ""]
    lines += [
        "Regenerate with `make analyze`. How each question was interpreted is in the "
        "[README](README.md#analysis).",
        "",
    ]
    for name in names:
        result = analysis.run(con, name)
        rows = result.fetchall()
        lines += [f"## {name}", "", analysis.describe(name), ""]
        lines += markdown_table(result.columns, rows[:PREVIEW_ROWS])
        if len(rows) > PREVIEW_ROWS:
            more = f"First {PREVIEW_ROWS} of {len(rows)} rows"
            if csv_dir:
                more += f", all of them in [`{csv_dir}/{name}.csv`]({csv_dir}/{name}.csv)"
            lines += ["", f"{more}."]
        lines.append("")
    return "\n".join(lines)


def markdown_table(columns: list[str], rows: list[tuple]) -> list[str]:
    def cell(value) -> str:
        return "" if value is None else str(value).replace("|", "\\|")

    out = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    out += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return out


def _source_line(con) -> str:
    # File name only: the full path is machine-specific and not worth publishing.
    # PureWindowsPath understands both / and \ separators.
    runs = con.execute(
        """
        SELECT source_file, source_sha256, rows_inserted
        FROM ingestion_runs
        WHERE status = 'succeeded' AND rows_inserted > 0
        ORDER BY run_id
        """
    ).fetchall()
    total = con.execute("SELECT count(*) FROM listens").fetchone()[0]
    files = [f"`{PureWindowsPath(f).name}` (sha256 `{sha[:12]}`)" for f, sha, _ in runs]
    if len(runs) > 1:
        files = [f"{desc}: {n:,}" for desc, (_, _, n) in zip(files, runs, strict=True)]
    return f"Computed from {total:,} listens loaded from {', '.join(files)}."
