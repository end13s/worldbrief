import html
import logging
import re
from contextlib import closing
from typing import Literal

import anthropic
from pydantic import BaseModel

from newspulse.db import get_conn

log = logging.getLogger(__name__)

MODEL = "claude-haiku-5-5"
BATCH_LIMIT = 200  # articles classified per run; keeps a backlog from turning into one large bill

Domain = Literal["politics", "science", "tech", "economy", "crime", "history", "other"]


class Classification(BaseModel):
    domain: Domain
    importance_score: float
    location: str | None
    lat: float | None
    lng: float | None


SYSTEM_PROMPT = """You classify news articles for a personal world-news dashboard.

- domain: the single best fit.
- importance_score: 0.0 to 1.0, how much the story matters to a well-informed reader anywhere in the world. Use about 1.0 for major global events, 0.5 for notable national or regional news, and 0.1 for minor or local stories.
- location: the main place the story is about, as "City, Country" or just "Country". Use null when the story is not tied to one place.
- lat, lng: coordinates of that location, or null when location is null."""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment / .env
    return _client


def _plain_text(value: str | None) -> str:
    """Feed summaries often carry HTML; send the model plain text."""
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()


def classify(title: str | None, summary: str | None) -> Classification | None:
    """Classify one article. Returns None when the model declines it."""
    response = _get_client().messages.parse(
        model=MODEL,
        max_tokens=1024,  # room for adaptive thinking plus the short JSON answer
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": f"Title: {title or ''}\nSummary: {_plain_text(summary)}"}],
        output_format=Classification,
    )
    if response.stop_reason == "refusal":
        return None
    result = response.parsed_output
    if result is None:
        raise ValueError(f"no structured output (stop_reason={response.stop_reason})")
    result.importance_score = min(1.0, max(0.0, result.importance_score))
    return result


def classify_pending(limit: int = BATCH_LIMIT) -> int:
    """Classify the newest unclassified articles. Each result is saved as soon as it arrives."""
    with closing(get_conn()) as conn:
        articles = conn.execute(
            "SELECT id, title, summary FROM articles WHERE domain IS NULL ORDER BY published_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    done = 0
    for article in articles:
        try:
            result = classify(article["title"], article["summary"])
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            log.error("Anthropic credentials rejected, skipping classification: %s", e)
            break
        except TypeError as e:
            # The SDK raises TypeError when no API key or auth profile is configured at all.
            if "authentication method" not in str(e):
                log.exception("Classifying article %s failed, will retry next run", article["id"])
                continue
            log.error("No Anthropic credentials configured (set ANTHROPIC_API_KEY in .env); skipping classification")
            break
        except Exception:
            log.exception("Classifying article %s failed, will retry next run", article["id"])
            continue

        with closing(get_conn()) as conn, conn:
            if result is None:
                # Declined by the model: file under "other" so it is not retried every run.
                conn.execute("UPDATE articles SET domain='other' WHERE id=?", (article["id"],))
            else:
                conn.execute(
                    "UPDATE articles SET domain=?, importance_score=?, location=?, lat=?, lng=? WHERE id=?",
                    (result.domain, result.importance_score, result.location, result.lat, result.lng, article["id"]),
                )
        done += 1

    if articles:
        log.info("Classified %d of %d pending articles", done, len(articles))
    return done
