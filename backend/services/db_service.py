"""DB service: orchestrate full DB update in a background thread.

Threading design:
- _update_lock prevents concurrent update runs
- progress_store provides thread-safe state for the SSE endpoint
- Single daemon thread writes to daily + weekly DBs then rebuilds stock_meta
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

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


def _make_progress_cb(
    phase: str, start_pct: float, end_pct: float,
) -> Callable[[int, int, str], None]:
    """종목/날짜별 진행률을 해당 phase 퍼센트 범위로 매핑하는 콜백을 생성한다."""
    def _cb(done: int, total: int, current: str) -> None:
        if total <= 0:
            return
        pct = start_pct + (end_pct - start_pct) * (done / total)
        update_progress(phase=phase, progress=round(pct, 1), current_stock=current, total=total)
    return _cb


def _run_update(daily_db_path: str, weekly_db_path: str) -> None:
    """Background thread: run all DB update phases sequentially."""
    try:
        # Phase 1: 주간 가격 데이터 (CHG_* 수익률, MA, RS_raw)
        logger.info("[db-update] Phase 1: generating weekly price DB")
        update_progress(phase="weekly_prices", progress=0.0)
        generate_price_db(
            db_name=weekly_db_path.removesuffix(".db"),
            progress_callback=_make_progress_cb("weekly_prices", 0.0, 20.0),
        )

        # Phase 2: 상대강도 순위
        logger.info("[db-update] Phase 2: generating weekly RS DB")
        update_progress(phase="weekly_rs", progress=20.0)
        generate_rs_db(
            db_name=weekly_db_path.removesuffix(".db"),
            progress_callback=_make_progress_cb("weekly_rs", 20.0, 40.0),
        )

        # Phase 3: 일별 가격 데이터 + 지표 (SMA100 포함)
        logger.info("[db-update] Phase 3: generating daily price DB")
        update_progress(phase="daily_prices", progress=40.0)
        price_daily_db(
            db_name=daily_db_path.removesuffix(".db"),
            progress_callback=_make_progress_cb("daily_prices", 40.0, 75.0),
        )

        # Phase 4: stock_meta 재구축 (pykrx 시가총액 포함)
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
