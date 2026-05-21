import feedparser
import hashlib
from newspulse.db import get_conn

def fetch_feed(rss_url):
    feed = feedparser.parse(rss_url)

    return feed.entries

def save_articles(entries, source_id):
    conn = get_conn()
    cur = conn.cursor()

    for entry in entries:
        url_hash = hashlib.sha256(entry.link.encode()).hexdigest()

        cur.execute("INSERT OR IGNORE INTO articles (url_hash, url, title, summary, source_id, published_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (url_hash, entry.link, entry.title, entry.summary, source_id, entry.published)
        )

    conn.commit()

def run_all():
    conn = get_conn()
    cur = conn.cursor()

    sources = cur.execute("SELECT * FROM sources WHERE active=1").fetchall()

    for source in sources:
        entries = fetch_feed(source["rss_url"])
        save_articles(entries, source["id"])
