from fastapi.testclient import TestClient

from newspulse import db
from newspulse.api.main import app

# Used without `with`, so the lifespan (and with it the scheduler) does not start.
client = TestClient(app)


def test_articles_are_newest_first(source_id):
    with db.get_conn() as conn:
        conn.executemany(
            "INSERT INTO articles (url_hash, url, title, source_id, published_at) VALUES (?, ?, ?, ?, ?)",
            [
                ("h1", "https://x/1", "older", source_id, "2026-05-20T09:00:00+00:00"),
                ("h2", "https://x/2", "newer", source_id, "2026-05-21T08:00:00+00:00"),
            ],
        )
        conn.commit()

    titles = [a["title"] for a in client.get("/articles").json()]
    assert titles == ["newer", "older"]


def test_missing_article_returns_404():
    assert client.get("/articles/999").status_code == 404
    assert client.post("/articles/999/mark-important").status_code == 404


def test_dashboard_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "<html" in response.text.lower()
