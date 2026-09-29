import pytest

from helpers import to_line
from listens_etl import db


@pytest.fixture
def con(tmp_path):
    con = db.connect(tmp_path / "test.duckdb")
    yield con
    con.close()


@pytest.fixture
def write_export(tmp_path):
    """Write lines (dicts or raw strings) to a JSONL file and return its path."""
    counter = iter(range(1000))

    def write(lines, name=None):
        path = tmp_path / (name or f"export_{next(counter)}.jsonl")
        path.write_text(
            "".join((to_line(x) if isinstance(x, dict) else x) + "\n" for x in lines),
            encoding="utf-8",
        )
        return path

    return write
