from contextlib import closing

from fastapi import APIRouter, HTTPException, Query

from newspulse.db import get_conn

router = APIRouter()


@router.get("/articles")
def get_articles(domain: str | None = None, source_id: int | None = None, limit: int = Query(50, ge=1, le=1000)):
    query = "SELECT * FROM articles WHERE 1=1"
    params: list = []

    if domain:
        query += " AND domain=?"
        params.append(domain)
    if source_id:
        query += " AND source_id=?"
        params.append(source_id)

    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)

    with closing(get_conn()) as conn:
        return [dict(a) for a in conn.execute(query, params).fetchall()]


@router.get("/articles/{article_id}")
def get_article(article_id: int):
    with closing(get_conn()) as conn:
        article = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return dict(article)


@router.get("/sources")
def get_sources():
    with closing(get_conn()) as conn:
        return [dict(s) for s in conn.execute("SELECT * FROM sources WHERE active=1").fetchall()]


@router.post("/articles/{article_id}/mark-important")
def mark_important(article_id: int):
    with closing(get_conn()) as conn, conn:
        cur = conn.execute("UPDATE articles SET sent_to_obsidian=1 WHERE id=?", (article_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "ok"}
