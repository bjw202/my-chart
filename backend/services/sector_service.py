"""Sector service: query unique sectors from stock_meta."""

from __future__ import annotations

import logging
import sqlite3

from backend.deps import get_db_conn

logger = logging.getLogger(__name__)


def get_sectors(daily_db_path: str) -> list[dict[str, object]]:
    """Return list of {sector_name, count} from stock_meta, ordered alphabetically.

    Returns an empty list if stock_meta does not exist yet.
    """
    conn = get_db_conn(daily_db_path)
    try:
        rows = conn.execute(
            """SELECT sector_major, COUNT(*) AS cnt
               FROM stock_meta
               WHERE sector_major IS NOT NULL
               GROUP BY sector_major
               ORDER BY sector_major"""
        ).fetchall()
        return [{"sector_name": row[0], "count": row[1]} for row in rows]
    except sqlite3.OperationalError:
        logger.warning("stock_meta table not found; returning empty sector list")
        return []
    finally:
        conn.close()
