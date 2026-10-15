import time

import feedparser

from newspulse import db, fetcher


def _entry(**fields):
    return feedparser.FeedParserDict(fields)


def test_published_iso_converts_feed_time_to_utc():
    parsed = time.strptime("2026-05-21 10:00:00", "%Y-%m-%d %H:%M:%S")
    assert fetcher.published_iso(_entry(published_parsed=parsed)) == "2026-05-21T10:00:00+00:00"


def test_save_articles_handles_missing_fields_and_duplicates(source_id):
    entries = [
        _entry(link="https://example.com/a", title="A"),           # no summary, no date
        _entry(title="no link"),                                    # skipped
        _entry(link="https://example.com/b", title="B", summary="s"),
    ]
    assert fetcher.save_articles(entries, source_id) == 2
    assert fetcher.save_articles(entries, source_id) == 0  # deduplicated by URL hash

    with db.get_conn() as conn:
        titles = sorted(row["title"] for row in conn.execute("SELECT title FROM articles"))
    assert titles == ["A", "B"]


def test_run_all_skips_a_failing_feed(monkeypatch):
    with db.get_conn() as conn:
        conn.executemany(
            "INSERT INTO sources (name, rss_url, category) VALUES (?, ?, 'news')",
            [("Dead", "https://dead/rss"), ("Live", "https://live/rss")],
        )
        conn.commit()

    def fake_fetch(url):
        if "dead" in url:
            raise RuntimeError("could not read feed")
        return [_entry(link="https://live/1", title="Live story")]

    monkeypatch.setattr(fetcher, "fetch_feed", fake_fetch)
    assert fetcher.run_all() == 1
