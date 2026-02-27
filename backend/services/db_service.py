"""DB service: orchestrate full DB update in a background thread.

Threading design:
- _update_lock prevents concurrent update runs
- progress_store provides thread-safe state for the SSE endpoint
- Single daemon thread writes to daily + weekly DBs then rebuilds stock_meta
"""

from __future__ import annotations

import logging
import threading

from my_chart.db.daily import price_daily_db
from my_chart.db.weekly import generate_price_db, generate_rs_db
from backend.services.meta_service import rebuild_stock_meta
from backend.services.progress_store import is_running, reset_progress, update_progress

logger = logging.getLogger(__name__)

# Exclusive lock: only one update may run at a time
_update_lock = threading.Lock()


def start_update(daily_db_path: str, weekly_db_path: str) -> bool:
    """Launch DB update in a background daemon thread.

    Returns True if the update was started, False if one is already running.
    The caller should respond with HTTP 409 when False is returned.
    """
    if not _update_lock.acquire(blocking=False):
        return False

    # Lock acquired; reset progress and spawn background thread
    reset_progress()
    thread = threading.Thread(
        target=_run_update,
        args=(daily_db_path, weekly_db_path),
        daemon=True,
        name="db-update",
    )
    thread.start()
    return True


def _run_update(daily_db_path: str, weekly_db_path: str) -> None:
    """Background thread: run all DB update phases sequentially."""
    try:
        # Phase 1: Weekly price data (CHG_* returns, MA, RS_raw)
        logger.info("[db-update] Phase 1: generating weekly price DB")
        update_progress(phase="weekly_prices", progress=0.0)
        generate_price_db(db_name=weekly_db_path.removesuffix(".db"))

        # Phase 2: Relative strength ratings
        logger.info("[db-update] Phase 2: generating weekly RS DB")
        update_progress(phase="weekly_rs", progress=20.0)
        generate_rs_db(db_name=weekly_db_path.removesuffix(".db"))

        # Phase 3: Daily price data + indicators (incl. SMA100)
        logger.info("[db-update] Phase 3: generating daily price DB")
        update_progress(phase="daily_prices", progress=40.0)
        price_daily_db(db_name=daily_db_path.removesuffix(".db"))

        # Phase 4 + 5: Rebuild stock_meta (includes pykrx market cap fetch)
        logger.info("[db-update] Phase 4: rebuilding stock_meta")
        update_progress(phase="rebuilding_meta", progress=75.0)
        rebuild_stock_meta(daily_db_path, weekly_db_path)

        update_progress(phase="complete", progress=100.0, done=True, running=False)
        logger.info("[db-update] Complete")

    except Exception as exc:
        logger.exception("[db-update] Failed: %s", exc)
        update_progress(phase="error", progress=0.0, done=True, running=False, error=str(exc))

    finally:
        _update_lock.release()
