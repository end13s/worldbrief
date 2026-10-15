import json
import sqlite3

from newspulse import db


def test_init_db_migrates_phase_one_database(temp_db):
    temp_db.unlink()
    conn = sqlite3.connect(temp_db)
    conn.executescript("""
        CREATE TABLE sources (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            rss_url TEXT NOT NULL UNIQUE, category TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE articles (id INTEGER PRIMARY KEY AUTOINCREMENT, url_hash TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL, title TEXT, summary TEXT, content TEXT, source_id INTEGER, domain TEXT,
            published_at TEXT, scraped_at TEXT NOT NULL DEFAULT (datetime('now')), importance_score REAL,
            sent_to_obsidian INTEGER NOT NULL DEFAULT 0);
        INSERT INTO articles (url_hash, url, published_at) VALUES ('h1', 'https://a', 'Wed, 21 May 2026 10:00:00 +0200');
    """)
    conn.close()

    db.init_db()

    with db.get_conn() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(articles)")}
        published = conn.execute("SELECT published_at FROM articles").fetchone()["published_at"]
    assert {"location", "lat", "lng"} <= columns
    assert published == "2026-05-21T08:00:00+00:00"


def test_seed_sources_deactivates_removed_feeds(tmp_path):
    feeds = tmp_path / "sources.json"
    feeds.write_text(json.dumps([
        {"name": "A", "rss_url": "https://a/rss", "category": "news"},
        {"name": "B", "rss_url": "https://b/rss", "category": "tech"},
    ]))
    db.seed_sources(feeds)

    feeds.write_text(json.dumps([{"name": "A", "rss_url": "https://a/rss", "category": "news"}]))
    db.seed_sources(feeds)

    with db.get_conn() as conn:
        active = {row["name"]: row["active"] for row in conn.execute("SELECT name, active FROM sources")}
    assert active == {"A": 1, "B": 0}


def test_relative_db_path_resolves_from_repo_root(monkeypatch):
    monkeypatch.setenv("DB_PATH", "data/x.db")
    assert db.db_path() == db.ROOT / "data" / "x.db"
