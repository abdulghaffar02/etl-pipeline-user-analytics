from helpers import make_listen
from listens_etl import report
from listens_etl.ingest import ingest_file


def test_markdown_table_escapes_pipes_and_nulls():
    assert report.markdown_table(["a", "b"], [("x|y", None)]) == [
        "| a | b |",
        "|---|---|",
        "| x\\|y |  |",
    ]


def test_report_links_csvs_and_cuts_long_results(con, write_export, monkeypatch):
    monkeypatch.setattr(report, "PREVIEW_ROWS", 1)
    path = write_export([make_listen(user="alice"), make_listen(user="bob")], name="export.jsonl")
    ingest_file(con, path)

    text = report.markdown_report(con, ["a1_top_users"], csv_dir="results")

    assert "loaded from `export.jsonl` (sha256" in text
    assert str(path.parent) not in text  # no local paths in a published file
    assert "## a1_top_users" in text
    assert "| alice | 1 |" in text
    assert "| bob | 1 |" not in text
    assert "First 1 of 2 rows, all of them in [`results/a1_top_users.csv`]" in text
