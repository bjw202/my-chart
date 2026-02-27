"""FastAPI dependency providers: DB paths and connections."""

from __future__ import annotations

import sqlite3

from my_chart.config import DEFAULT_DB_DAILY, DEFAULT_DB_WEEKLY

# Full paths including .db extension
DAILY_DB_PATH: str = f"{DEFAULT_DB_DAILY}.db"
WEEKLY_DB_PATH: str = f"{DEFAULT_DB_WEEKLY}.db"


def get_db_conn(path: str) -> sqlite3.Connection:
    """Open a SQLite connection safe for use across threads.

    FastAPI runs handlers in thread pools; check_same_thread=False
    allows the same connection to be used from multiple threads.
    Callers are responsible for closing the connection.
    """
    return sqlite3.connect(path, check_same_thread=False)
