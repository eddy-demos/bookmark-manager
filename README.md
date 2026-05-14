# Bookmark Manager

A tiny CRUD bookmark manager built with FastAPI, SQLite, HTMX, and Pico.css.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000

The SQLite database (`bookmarks.db`) is created on first run and seeded with example bookmarks.

## Stack
- **Backend:** FastAPI + `sqlite3` (stdlib, no ORM)
- **Frontend:** HTMX + Jinja2 templates
- **Styling:** Pico.css (CDN) + small custom CSS

## Layout
- `main.py` — FastAPI app, routes
- `db.py` — SQLite schema, queries, seed
- `templates/` — `base.html`, `index.html`, `partials/`
- `static/styles.css` — custom tweaks
- `bookmarks.db` — SQLite database (gitignored)
