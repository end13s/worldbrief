import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import json
import os

def get_conn():
    load_dotenv()
    db_path = os.getenv('DB_PATH')

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
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
        """)

    conn.commit()

def seed_sources():
    conn = get_conn()
    cur = conn.cursor()

    with open("sources.json", "r") as f:
        sources = json.load(f)

    for source in sources:
        cur.execute(
            "INSERT OR IGNORE INTO sources (name, rss_url, category) VALUES (?, ?, ?)",
            (source["name"], source["rss_url"], source["category"])
        )

    conn.commit()