import os
import re
import json
from anthropic import Anthropic
from dotenv import load_dotenv
from newspulse.db import get_conn

def classify(title, summary):
    client = Anthropic(
        api_key = os.environ.get("ANTHROPIC_API_KEY") 
    )

    message = client.messages.create (
        model = "claude-haiku-4-5-20251001",
        max_tokens = 256,
        messages = [
            {
                "role": "user",
                "content": f"Classify this article.\nTitle: {title}\nSummary: {summary}\n\nReturn JSON only: {{\"domain\": \"politics|science|tech|economy|crime|history|other\", \"importance_score\": 0.0-1.0}}"
            }
        ]
    )

    text = message.content[0].text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(match.group())

def classify_pending():
    conn = get_conn()
    cur = conn.cursor()

    articles = cur.execute(
        "SELECT id, title, summary FROM articles WHERE domain IS NULL"
    ).fetchall()

    for article in articles:
        result = classify(article["title"], article["summary"])
        cur.execute(
            "UPDATE articles SET domain=?, importance_score=? WHERE id=?",
            (result["domain"], result["importance_score"], article["id"])
        )

    conn.commit()
