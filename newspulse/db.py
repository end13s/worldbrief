import json
import os
import sqlite3
from contextlib import closing
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from dotenv import load_dotenv

# Repository root: holds sources.json, static/, templates/ and the default data/ folder.
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = "data/newspulse.db"

load_dotenv(ROOT / ".env")


def db_path() -> Path:
    path = Path(os.getenv("DB_PATH") or DEFAULT_DB_PATH)
    return path if path.is_absolute() else ROOT / path


def get_conn() -> sqlite3.Connection:
    """Open a connection. Callers close it, e.g. `with closing(get_conn()) as conn`."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


SCHEMA = """
    CREATE TABLE IF NOT EXISTS sources (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT NOT NULL,
        rss_url   TEXT NOT NULL UNIQUE,
        category  TEXT NOT NULL,
        active    INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS articles (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        url_hash         TEXT NOT NULL UNIQUE,
        url              TEXT NOT NULL,
        title            TEXT,
        summary          TEXT,
        content          TEXT,
        source_id        INTEGER REFERENCES sources(id),
        domain           TEXT,
        published_at     TEXT,
        scraped_at       TEXT NOT NULL DEFAULT (datetime('now')),
        importance_score REAL,
        sent_to_obsidian INTEGER NOT NULL DEFAULT 0,
        location         TEXT,
        lat              REAL,
        lng              REAL
    );

    CREATE INDEX IF NOT EXISTS idx_articles_domain      ON articles(domain);
    CREATE INDEX IF NOT EXISTS idx_articles_published   ON articles(published_at);
    CREATE INDEX IF NOT EXISTS idx_articles_importance  ON articles(importance_score);
"""

# Columns added after the first release; databases created earlier get them via ALTER TABLE.
_ADDED_COLUMNS = {"location": "TEXT", "lat": "REAL", "lng": "REAL"}


def _to_iso(value: str | None) -> str | None:
    """Convert an RFC 822 feed date ("Wed, 21 May 2026 10:00:00 GMT") to ISO 8601."""
    if not value or value[:4].isdigit():
        return value
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def init_db():
    with closing(get_conn()) as conn, conn:
        conn.executescript(SCHEMA)

        existing = {row["name"] for row in conn.execute("PRAGMA table_info(articles)")}
        for column, sql_type in _ADDED_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE articles ADD COLUMN {column} {sql_type}")

        # Older rows stored raw RFC 822 dates, which sort incorrectly as text.
        rows = conn.execute(
            "SELECT id, published_at FROM articles WHERE published_at NOT GLOB '[0-9][0-9][0-9][0-9]-*'"
        ).fetchall()
        for row in rows:
            iso = _to_iso(row["published_at"])
            if iso != row["published_at"]:
                conn.execute("UPDATE articles SET published_at=? WHERE id=?", (iso, row["id"]))


def seed_sources(path: Path | None = None):
    """Sync the sources table with sources.json: add new feeds, deactivate removed ones."""
    with open(path or ROOT / "sources.json", encoding="utf-8") as f:
        sources = json.load(f)

    with closing(get_conn()) as conn, conn:
        for source in sources:
            conn.execute(
                "INSERT OR IGNORE INTO sources (name, rss_url, category) VALUES (?, ?, ?)",
                (source["name"], source["rss_url"], source["category"]),
            )
            conn.execute(
                "UPDATE sources SET name=?, category=?, active=1 WHERE rss_url=?",
                (source["name"], source["category"], source["rss_url"]),
            )

        urls = [s["rss_url"] for s in sources]
        placeholders = ",".join("?" * len(urls))
        conn.execute(f"UPDATE sources SET active=0 WHERE rss_url NOT IN ({placeholders})", urls)
