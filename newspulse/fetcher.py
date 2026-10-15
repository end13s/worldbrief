import calendar
import hashlib
import logging
from contextlib import closing
from datetime import datetime, timezone

import feedparser

from newspulse.db import get_conn

log = logging.getLogger(__name__)

USER_AGENT = "WorldBrief/1.0 (+https://github.com/end13s/worldbrief)"


def fetch_feed(rss_url):
    feed = feedparser.parse(rss_url, agent=USER_AGENT)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"could not read feed: {feed.get('bozo_exception')}")
    return feed.entries


def published_iso(entry) -> str | None:
    """Publication time as ISO 8601 UTC, so it sorts and parses correctly."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc).isoformat()
    return entry.get("published") or entry.get("updated")


def save_articles(entries, source_id) -> int:
    """Insert new entries, skipping duplicates by URL hash. Returns how many were new."""
    saved = 0
    with closing(get_conn()) as conn, conn:
        for entry in entries:
            link = entry.get("link")
            if not link:
                continue
            url_hash = hashlib.sha256(link.encode()).hexdigest()
            cur = conn.execute(
                "INSERT OR IGNORE INTO articles (url_hash, url, title, summary, source_id, published_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (url_hash, link, entry.get("title"), entry.get("summary"), source_id, published_iso(entry)),
            )
            saved += cur.rowcount
    return saved


def run_all() -> int:
    """Fetch every active source. A failing feed is logged and skipped."""
    with closing(get_conn()) as conn:
        sources = conn.execute("SELECT * FROM sources WHERE active=1").fetchall()

    total = 0
    for source in sources:
        try:
            total += save_articles(fetch_feed(source["rss_url"]), source["id"])
        except Exception:
            log.exception("Fetching %s failed", source["name"])
    log.info("Fetched %d new articles from %d sources", total, len(sources))
    return total
