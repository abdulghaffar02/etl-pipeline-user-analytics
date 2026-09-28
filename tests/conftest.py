import pytest

from listens_etl import db


@pytest.fixture
def con(tmp_path):
    con = db.connect(tmp_path / "test.duckdb")
    yield con
    con.close()
