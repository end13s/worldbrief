# newspulse — Documentation

Self-hosted news aggregator with RSS scraping, LLM classification, and a local dashboard.

---

## Stack

| Component | Tehnologie |
|---|---|
| Language | Python 3.11+ |
| Scraping | `feedparser` |
| Database | SQLite |
| API | FastAPI + Uvicorn |
| LLM | Claude Haiku (`claude-haiku-4-5-20251001`) |
| Scheduler | APScheduler |
| Package manager | `uv` |

---

## Project Structure

```
worldbrief/
├── newspulse/
│   ├── __init__.py
│   ├── db.py
│   ├── fetcher.py
│   ├── classifier.py
│   ├── scheduler.py
│   └── api/
│       ├── __init__.py
│       ├── main.py
│       └── routes.py
├── data/
│   └── newspulse.db       # auto-created on first run
├── sources.json
├── pyproject.toml
└── .env
```

---

## Environment Variables

`.env` file at the root:

```
ANTHROPIC_API_KEY=sk-ant-...
DB_PATH=data/newspulse.db
```

---

## Database Schema

### `sources`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| name | TEXT | Display name |
| rss_url | TEXT | Unique RSS URL |
| category | TEXT | e.g. news, tech, science |
| active | INTEGER | 1 = active, 0 = disabled |

### `articles`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| url_hash | TEXT | SHA-256 of URL, used for deduplication |
| url | TEXT | Original article URL |
| title | TEXT | Article title |
| summary | TEXT | Short description from RSS |
| content | TEXT | Full content (if available) |
| source_id | INTEGER | Foreign key → sources.id |
| domain | TEXT | Classified by LLM (politics, tech, science, etc.) |
| published_at | TEXT | Publication date from RSS |
| scraped_at | TEXT | When it was scraped (auto) |
| importance_score | REAL | 0.0–1.0, assigned by LLM |
| sent_to_obsidian | INTEGER | 1 = exported to Obsidian |

Indexes on `domain`, `published_at`, `importance_score`.

---

## Files

### `db.py`

**`get_conn()`**
- Loads `.env`, reads `DB_PATH`
- Creates `data/` folder if it doesn't exist
- Returns a SQLite connection with `row_factory = sqlite3.Row`

**`init_db()`**
- Calls `get_conn()`
- Creates `sources` and `articles` tables + indexes via `executescript()`

**`seed_sources()`**
- Reads `sources.json`
- Inserts each source into the DB with `INSERT OR IGNORE`

---

### `fetcher.py`

**`fetch_feed(rss_url)`**
- Calls `feedparser.parse(rss_url)`
- Returns `feed.entries`

**`save_articles(entries, source_id)`**
- For each entry: computes `url_hash = hashlib.sha256(entry.link.encode()).hexdigest()`
- Inserts into `articles` with `INSERT OR IGNORE` (deduplication)
- Commits at the end

**`run_all()`**
- Fetches all active sources from DB
- Calls `fetch_feed()` + `save_articles()` for each

---

### `classifier.py`

**`classify(title, summary)`**
- Calls Claude Haiku with a prompt asking for JSON classification
- Returns `{"domain": "...", "importance_score": 0.0–1.0}`

**`classify_pending()`**
- Fetches all articles where `domain IS NULL`
- Calls `classify()` for each
- Updates `domain` and `importance_score` in DB

---

### `scheduler.py`

**`start()`**
- Creates a `BackgroundScheduler`
- Adds `run_all` every 30 minutes
- Adds `classify_pending` every 35 minutes
- Starts the scheduler

---

### `api/main.py`

- Creates the FastAPI `app`
- On startup: calls `init_db()`, `seed_sources()`, `scheduler.start()`
- Includes the router from `routes.py`

---

### `api/routes.py`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/articles` | List articles. Optional params: `domain`, `source_id`, `limit` (default 50) |
| GET | `/articles/{id}` | Get a single article by ID |
| GET | `/sources` | List all active sources |
| POST | `/articles/{id}/mark-important` | Set `sent_to_obsidian=1` |

---

## Running the Server

```bash
uv run uvicorn newspulse.api.main:app --reload
```

Dashboard available at `http://localhost:8000`.
On Raspberry Pi: `http://raspberry.local:8000`.
