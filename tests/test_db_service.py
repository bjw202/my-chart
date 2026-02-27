"""Tests for backend/services/progress_store.py and db_service.py."""

from __future__ import annotations

import threading
from unittest.mock import patch


# ---------------------------------------------------------------------------
# progress_store tests
# ---------------------------------------------------------------------------


class TestProgressStore:
    def setup_method(self):
        """Reset progress state before each test."""
        from backend.services.progress_store import _progress, _lock
        with _lock:
            _progress.update({
                "running": False,
                "phase": "",
                "progress": 0.0,
                "current_stock": "",
                "total": 0,
                "eta_seconds": 0,
                "done": False,
                "error": None,
            })

    def test_get_progress_returns_dict(self):
        from backend.services.progress_store import get_progress
        state = get_progress()
        assert isinstance(state, dict)

    def test_get_progress_has_required_keys(self):
        from backend.services.progress_store import get_progress
        state = get_progress()
        for key in ("running", "phase", "progress", "done", "error"):
            assert key in state

    def test_get_progress_returns_copy(self):
        """Mutating the returned dict must not affect the store."""
        from backend.services.progress_store import get_progress
        state = get_progress()
        state["running"] = True
        state2 = get_progress()
        assert state2["running"] is False  # original unchanged

    def test_update_progress_modifies_phase(self):
        from backend.services.progress_store import update_progress, get_progress
        update_progress(phase="weekly_prices")
        assert get_progress()["phase"] == "weekly_prices"

    def test_update_progress_modifies_progress_value(self):
        from backend.services.progress_store import update_progress, get_progress
        update_progress(progress=42.5)
        assert get_progress()["progress"] == 42.5

    def test_update_progress_sets_done(self):
        from backend.services.progress_store import update_progress, get_progress
        update_progress(done=True)
        assert get_progress()["done"] is True

    def test_update_progress_sets_error(self):
        from backend.services.progress_store import update_progress, get_progress
        update_progress(error="something went wrong")
        assert get_progress()["error"] == "something went wrong"

    def test_reset_progress_sets_running_true(self):
        from backend.services.progress_store import reset_progress, get_progress
        reset_progress()
        assert get_progress()["running"] is True

    def test_reset_progress_sets_phase_to_starting(self):
        from backend.services.progress_store import reset_progress, get_progress
        reset_progress()
        assert get_progress()["phase"] == "starting"

    def test_reset_progress_clears_done_and_error(self):
        from backend.services.progress_store import update_progress, reset_progress, get_progress
        update_progress(done=True, error="previous error")
        reset_progress()
        state = get_progress()
        assert state["done"] is False
        assert state["error"] is None

    def test_is_running_false_when_not_running(self):
        from backend.services.progress_store import is_running
        # setup_method set running=False
        assert is_running() is False

    def test_is_running_true_after_reset(self):
        from backend.services.progress_store import is_running, reset_progress
        reset_progress()
        assert is_running() is True

    def test_is_running_reflects_update(self):
        from backend.services.progress_store import is_running, update_progress
        update_progress(running=True)
        assert is_running() is True
        update_progress(running=False)
        assert is_running() is False


# ---------------------------------------------------------------------------
# db_service tests
# ---------------------------------------------------------------------------


class TestStartUpdate:
    def test_returns_false_when_lock_already_held(self):
        """Returns False without starting a thread when update is already running."""
        from backend.services.db_service import start_update, _update_lock

        acquired = _update_lock.acquire(blocking=False)
        assert acquired, "Lock should be available at test start"
        try:
            result = start_update("daily.db", "weekly.db")
            assert result is False
        finally:
            _update_lock.release()

    def test_returns_true_and_starts_thread(self):
        """Returns True and spawns a background thread when lock is free."""
        from backend.services import db_service

        threads_started: list = []

        class _FakeThread:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def start(self):
                threads_started.append(self)

        with patch.object(threading, "Thread", _FakeThread):
            with patch.object(db_service, "reset_progress") as mock_reset:
                result = db_service.start_update("daily.db", "weekly.db")

        assert result is True
        assert len(threads_started) == 1
        mock_reset.assert_called_once()

        # Clean up: release the lock that start_update acquired
        db_service._update_lock.release()

    def test_thread_is_daemon(self):
        """Background thread must be a daemon thread."""
        from backend.services import db_service

        thread_kwargs: dict = {}

        class _CapturingThread:
            def __init__(self, **kwargs):
                thread_kwargs.update(kwargs)

            def start(self):
                pass

        with patch.object(threading, "Thread", _CapturingThread):
            with patch.object(db_service, "reset_progress"):
                db_service.start_update("daily.db", "weekly.db")

        assert thread_kwargs.get("daemon") is True

        # Clean up
        db_service._update_lock.release()


class TestRunUpdate:
    def test_releases_lock_on_exception(self):
        """Even when an exception occurs, the lock must be released."""
        from backend.services import db_service

        with patch.object(db_service, "generate_price_db", side_effect=RuntimeError("DB error")):
            with patch.object(db_service, "generate_rs_db"):
                with patch.object(db_service, "price_daily_db"):
                    with patch.object(db_service, "rebuild_stock_meta"):
                        with patch.object(db_service, "update_progress"):
                            with patch.object(db_service, "reset_progress"):
                                # Acquire lock to simulate running state
                                db_service._update_lock.acquire(blocking=False)
                                db_service._run_update("daily.db", "weekly.db")

        # Lock should be released after exception
        acquired = db_service._update_lock.acquire(blocking=False)
        assert acquired, "Lock must be released even on exception"
        db_service._update_lock.release()

    def test_updates_progress_to_error_on_exception(self):
        """When _run_update fails, progress is updated to error state."""
        from backend.services import db_service

        progress_calls: list[dict] = []

        def capture_progress(**kwargs):
            progress_calls.append(kwargs)

        with patch.object(db_service, "generate_price_db", side_effect=RuntimeError("fail")):
            with patch.object(db_service, "generate_rs_db"):
                with patch.object(db_service, "price_daily_db"):
                    with patch.object(db_service, "rebuild_stock_meta"):
                        with patch.object(db_service, "update_progress", side_effect=capture_progress):
                            db_service._update_lock.acquire(blocking=False)
                            db_service._run_update("daily.db", "weekly.db")

        # Last call should be the error state update
        error_call = next(
            (c for c in progress_calls if c.get("phase") == "error"),
            None,
        )
        assert error_call is not None
        assert error_call.get("done") is True
        assert error_call.get("running") is False
        # _run_update releases the lock in finally; no need to release here
