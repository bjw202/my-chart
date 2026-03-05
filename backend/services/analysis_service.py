"""Analysis service: call analyze_dashboard with TTL caching.

Bridges backend API to fnguide.dashboard.analyze_dashboard.
Cache: TTLCache(maxsize=100, ttl=300) — 5 minute TTL per stock code.
"""

from __future__ import annotations

import logging

from cachetools import TTLCache, cached

from fnguide.dashboard import DashboardResult, analyze_dashboard

logger = logging.getLogger(__name__)

# @MX:NOTE: [AUTO] TTL cache: 100 stock codes, 5 minute expiry
_cache: TTLCache[str, DashboardResult] = TTLCache(maxsize=100, ttl=300)


@cached(cache=_cache)
def get_dashboard(code: str) -> DashboardResult:
    """Fetch and cache dashboard result for the given stock code.

    Args:
        code: 6-digit KRX stock code.

    Returns:
        DashboardResult from analyze_dashboard.

    Raises:
        ValueError: if code format is invalid.
        ConnectionError: if FnGuide crawling fails.
        Exception: propagated from analyze_dashboard on unexpected errors.
    """
    logger.info("Computing dashboard for %s (cache miss)", code)
    return analyze_dashboard(code)
