import pytest

from newspulse import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Point every test at a fresh SQLite file."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return tmp_path / "test.db"


@pytest.fixture
def source_id():
    with db.get_conn() as conn:
        cur = conn.execute("INSERT INTO sources (name, rss_url, category) VALUES ('Test', 'https://example.com/rss', 'news')")
        conn.commit()
        return cur.lastrowid
