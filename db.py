import sqlite3
from contextlib import contextmanager

DB_PATH = "bookmarks.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bookmark_tags (
    bookmark_id INTEGER NOT NULL REFERENCES bookmarks(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (bookmark_id, tag_id)
);
"""

SEED = [
    (
        "https://www.python.org",
        "Python",
        "The official Python language site.",
        ["python", "language"],
    ),
    (
        "https://fastapi.tiangolo.com",
        "FastAPI",
        "Modern, fast web framework for Python.",
        ["python", "web", "framework"],
    ),
    (
        "https://htmx.org",
        "HTMX",
        "High power tools for HTML.",
        ["web", "frontend", "htmx"],
    ),
    (
        "https://picocss.com",
        "Pico.css",
        "Minimal CSS framework for semantic HTML.",
        ["css", "frontend"],
    ),
    (
        "https://sqlite.org",
        "SQLite",
        "Self-contained, serverless SQL database engine.",
        ["database", "sqlite"],
    ),
    (
        "https://github.com",
        "GitHub",
        "Where the world builds software.",
        ["tools", "git"],
    ),
    (
        "https://news.ycombinator.com",
        "Hacker News",
        "Tech and startup news aggregator.",
        ["news", "tech"],
    ),
    (
        "https://developer.mozilla.org",
        "MDN Web Docs",
        "Resources for developers, by developers.",
        ["web", "docs", "reference"],
    ),
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connection() as conn:
        conn.executescript(SCHEMA)
        cur = conn.execute("SELECT COUNT(*) AS c FROM bookmarks")
        if cur.fetchone()["c"] == 0:
            for url, title, desc, tags in SEED:
                bid = conn.execute(
                    "INSERT INTO bookmarks (url, title, description) VALUES (?, ?, ?)",
                    (url, title, desc),
                ).lastrowid
                _attach_tags(conn, bid, tags)


def _normalize_tags(raw):
    if not raw:
        return []
    seen = set()
    out = []
    for t in raw.split(",") if isinstance(raw, str) else raw:
        n = t.strip().lower()
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _attach_tags(conn, bookmark_id, tag_names):
    for name in tag_names:
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tid = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[
            "id"
        ]
        conn.execute(
            "INSERT OR IGNORE INTO bookmark_tags (bookmark_id, tag_id) VALUES (?, ?)",
            (bookmark_id, tid),
        )


def _cleanup_orphan_tags(conn):
    conn.execute(
        "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM bookmark_tags)"
    )


def list_bookmarks(q=None, tag=None):
    sql = """
        SELECT DISTINCT b.* FROM bookmarks b
        LEFT JOIN bookmark_tags bt ON bt.bookmark_id = b.id
        LEFT JOIN tags t ON t.id = bt.tag_id
        WHERE 1=1
    """
    args = []
    if q:
        sql += " AND (LOWER(b.title) LIKE ? OR LOWER(b.description) LIKE ? OR LOWER(b.url) LIKE ?)"
        like = f"%{q.lower()}%"
        args += [like, like, like]
    if tag:
        sql += " AND b.id IN (SELECT bt2.bookmark_id FROM bookmark_tags bt2 JOIN tags t2 ON t2.id = bt2.tag_id WHERE t2.name = ?)"
        args.append(tag.lower())
    sql += " ORDER BY b.created_at DESC, b.id DESC"
    with connection() as conn:
        rows = conn.execute(sql, args).fetchall()
        results = []
        for r in rows:
            tags = conn.execute(
                "SELECT t.name FROM tags t JOIN bookmark_tags bt ON bt.tag_id = t.id WHERE bt.bookmark_id = ? ORDER BY t.name",
                (r["id"],),
            ).fetchall()
            d = dict(r)
            d["tags"] = [t["name"] for t in tags]
            results.append(d)
        return results


def get_bookmark(bookmark_id):
    with connection() as conn:
        r = conn.execute(
            "SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,)
        ).fetchone()
        if not r:
            return None
        tags = conn.execute(
            "SELECT t.name FROM tags t JOIN bookmark_tags bt ON bt.tag_id = t.id WHERE bt.bookmark_id = ? ORDER BY t.name",
            (bookmark_id,),
        ).fetchall()
        d = dict(r)
        d["tags"] = [t["name"] for t in tags]
        return d


def create_bookmark(url, title, description, tags_raw):
    tags = _normalize_tags(tags_raw)
    with connection() as conn:
        bid = conn.execute(
            "INSERT INTO bookmarks (url, title, description) VALUES (?, ?, ?)",
            (url, title, description or None),
        ).lastrowid
        _attach_tags(conn, bid, tags)
    return get_bookmark(bid)


def update_bookmark(bookmark_id, url, title, description, tags_raw):
    tags = _normalize_tags(tags_raw)
    with connection() as conn:
        conn.execute(
            "UPDATE bookmarks SET url = ?, title = ?, description = ? WHERE id = ?",
            (url, title, description or None, bookmark_id),
        )
        conn.execute("DELETE FROM bookmark_tags WHERE bookmark_id = ?", (bookmark_id,))
        _attach_tags(conn, bookmark_id, tags)
        _cleanup_orphan_tags(conn)
    return get_bookmark(bookmark_id)


def delete_bookmark(bookmark_id):
    with connection() as conn:
        conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        _cleanup_orphan_tags(conn)


def list_tags():
    with connection() as conn:
        return [
            dict(r)
            for r in conn.execute(
                """
                SELECT t.name, COUNT(bt.bookmark_id) AS count
                FROM tags t
                LEFT JOIN bookmark_tags bt ON bt.tag_id = t.id
                GROUP BY t.id
                ORDER BY t.name
                """
            ).fetchall()
        ]
