"""Disposable database helper.

Real TenantDesk tests run against a throwaway Postgres (testcontainers or a
pooled test DSN), TRUNCATEd before every test so state never leaks between
runs. This demo uses SQLite instead so the whole suite runs with zero extra
infrastructure (no Docker required) — the pattern being demonstrated is
"every test gets a known-empty database," not the specific engine.
"""
from __future__ import annotations

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_SCHEMA = """
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    summary TEXT NOT NULL
);
"""


@contextmanager
def fresh_db() -> Iterator[sqlite3.Connection]:
    """Create a brand-new on-disk SQLite DB, yield a connection, delete it after."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "eval_harness.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
            yield conn
        finally:
            conn.close()


def insert_ticket(conn: sqlite3.Connection, message: str, category: str, urgency: str, summary: str) -> int:
    cur = conn.execute(
        "INSERT INTO tickets (message, category, urgency, summary) VALUES (?, ?, ?, ?)",
        (message, category, urgency, summary),
    )
    conn.commit()
    return cur.lastrowid


def count_tickets(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
