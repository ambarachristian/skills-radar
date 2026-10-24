"""Everything about the SQLite database lives here."""
import sqlite3
from pathlib import Path

# The database file: data/radar.db (the data/ folder is in .gitignore)
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "radar.db"

SCHEMA = """
-- Cache: a raw copy of every item we download from HN.
CREATE TABLE IF NOT EXISTS hn_items (
    id          INTEGER PRIMARY KEY,   -- HN item id
    json        TEXT    NOT NULL,      -- the item exactly as HN sent it
    fetched_at  INTEGER NOT NULL       -- when we downloaded it
);

-- One row per "Who is hiring?" thread.
CREATE TABLE IF NOT EXISTS threads (
    id      INTEGER PRIMARY KEY,       -- HN id of the thread
    month   TEXT NOT NULL UNIQUE,      -- e.g. '2026-10'
    title   TEXT NOT NULL
);

-- One row per job post (a direct reply in a thread).
CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY,    -- HN id of the post
    thread_id  INTEGER NOT NULL REFERENCES threads(id),
    month      TEXT NOT NULL,
    author     TEXT,
    posted_at  INTEGER,                -- Unix timestamp
    text       TEXT NOT NULL           -- plain text, HTML removed
);
"""


def connect() -> sqlite3.Connection:
    """Open the database, creating the file and tables if needed."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us read columns by name: row["month"]
    conn.executescript(SCHEMA)
    return conn
