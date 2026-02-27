"""Thread-safe progress store for SSE DB update streaming."""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()

# Shared progress state; reset at start of each DB update
_progress: dict[str, Any] = {
    "running": False,
    "phase": "",
    "progress": 0.0,
    "current_stock": "",
    "total": 0,
    "eta_seconds": 0,
    "done": False,
    "error": None,
}


def get_progress() -> dict[str, Any]:
    """Return a snapshot of the current progress state."""
    with _lock:
        return dict(_progress)


def update_progress(**kwargs: Any) -> None:
    """Update one or more fields in the progress state (thread-safe)."""
    with _lock:
        _progress.update(kwargs)


def reset_progress() -> None:
    """Reset progress state to initial values before a new DB update."""
    with _lock:
        _progress.update({
            "running": True,
            "phase": "starting",
            "progress": 0.0,
            "current_stock": "",
            "total": 0,
            "eta_seconds": 0,
            "done": False,
            "error": None,
        })


def is_running() -> bool:
    """Return True if a DB update is currently in progress."""
    with _lock:
        return bool(_progress["running"])
