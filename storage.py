"""SQLite deduplication ledger."""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "data" / "seen.db"


def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, source TEXT, score INTEGER, url TEXT, first_seen TEXT)")


def is_seen(iid):
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT 1 FROM seen WHERE id=?", (iid,)).fetchone() is not None


def mark_seen(iid, source, score, url, ts):
    with sqlite3.connect(DB) as c:
        c.execute("INSERT OR IGNORE INTO seen VALUES (?,?,?,?,?)", (iid, source, score, url, ts))

