import json

import anthropic
import httpx2
import pytest

from newspulse import classifier, db


def _add_articles(source_id, n):
    with db.get_conn() as conn:
        conn.executemany(
            "INSERT INTO articles (url_hash, url, title, summary, source_id, published_at) VALUES (?, ?, ?, '', ?, ?)",
            [(f"h{i}", f"https://x/{i}", f"Story {i}", source_id, f"2026-05-2{i}T00:00:00+00:00") for i in range(n)],
        )
        conn.commit()


def _rows():
    with db.get_conn() as conn:
        return {r["title"]: dict(r) for r in conn.execute("SELECT * FROM articles")}


@pytest.fixture
def mock_api():
    """Route the real SDK client to an in-process handler and record request bodies."""
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        body = {"domain": "science", "importance_score": 1.4, "location": "Houston, United States", "lat": 29.76, "lng": -95.37}
        return httpx2.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant", "model": classifier.MODEL,
            "content": [{"type": "text", "text": json.dumps(body)}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })

    classifier._client = anthropic.Anthropic(
        api_key="sk-ant-test", http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler))
    )
    yield requests
    classifier._client = None


def test_classify_sends_structured_low_effort_request(mock_api):
    result = classifier.classify("Probe launched", "<p>NASA &amp; partners</p>")

    request = mock_api[0]
    assert request["model"] == "claude-haiku-5-5"
    assert "temperature" not in request
    assert request["output_config"]["effort"] == "low"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert "NASA & partners" in request["messages"][0]["content"]
    assert result.domain == "science"
    assert result.importance_score == 1.0  # clamped


def test_classify_pending_saves_each_result_and_survives_failures(source_id, monkeypatch):
    _add_articles(source_id, 3)

    def fake_classify(title, summary):
        if title == "Story 1":
            raise RuntimeError("transient API error")
        if title == "Story 2":
            return None  # declined by the model
        return classifier.Classification(domain="tech", importance_score=0.7, location=None, lat=None, lng=None)

    monkeypatch.setattr(classifier, "classify", fake_classify)
    assert classifier.classify_pending() == 2

    rows = _rows()
    assert rows["Story 0"]["domain"] == "tech" and rows["Story 0"]["importance_score"] == 0.7
    assert rows["Story 1"]["domain"] is None      # retried next run
    assert rows["Story 2"]["domain"] == "other"   # not retried forever


def test_classify_pending_stops_once_without_credentials(source_id, monkeypatch):
    _add_articles(source_id, 3)
    calls = []

    def no_key(title, summary):
        calls.append(title)
        raise TypeError("Could not resolve authentication method. Expected one of api_key ...")

    monkeypatch.setattr(classifier, "classify", no_key)
    assert classifier.classify_pending() == 0
    assert len(calls) == 1
