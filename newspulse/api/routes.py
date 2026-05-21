from fastapi import APIRouter
from newspulse.db import get_conn

router = APIRouter()


@router.get("/articles")
def get_articles(domain: str = None, source_id: int = None, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()

    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if domain:
        query += " AND domain=?"
        params.append(domain)
    if source_id:
        query += " AND source_id=?"
        params.append(source_id)

    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)

    articles = cur.execute(query, params).fetchall()
    return [dict(a) for a in articles]


@router.get("/articles/{article_id}")
def get_article(article_id: int):
    conn = get_conn()
    cur = conn.cursor()

    article = cur.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    return dict(article)


@router.get("/sources")
def get_sources():
    conn = get_conn()
    cur = conn.cursor()

    sources = cur.execute("SELECT * FROM sources WHERE active=1").fetchall()
    return [dict(s) for s in sources]


@router.post("/articles/{article_id}/mark-important")
def mark_important(article_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE articles SET sent_to_obsidian=1 WHERE id=?", (article_id,))
    conn.commit()
    return {"status": "ok"}