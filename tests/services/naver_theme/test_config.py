import pytest
from backend.services.naver_theme.config import (
    NAVER_THEME_LIST_URL,
    NAVER_THEME_DETAIL_URL,
    CRAWL_DELAY,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    USER_AGENT,
    MOMENTUM_WEIGHT_1D,
    MOMENTUM_WEIGHT_3D,
    LEADER_SCORE_WEIGHTS,
    DEFAULT_TOP_N_THEMES,
    DEFAULT_LEADERS_PER_THEME,
)


@pytest.mark.unit
def test_constants_defined():
    """All configuration constants are defined and have expected types."""
    assert isinstance(NAVER_THEME_LIST_URL, str)
    assert "page={" in NAVER_THEME_LIST_URL
    assert isinstance(NAVER_THEME_DETAIL_URL, str)
    assert "no={" in NAVER_THEME_DETAIL_URL
    assert CRAWL_DELAY == 0.7
    assert REQUEST_TIMEOUT == 10
    assert MAX_RETRIES == 1
    assert isinstance(USER_AGENT, str)
    assert "1.0" in USER_AGENT
    assert MOMENTUM_WEIGHT_1D == 0.6
    assert MOMENTUM_WEIGHT_3D == 0.4
    assert LEADER_SCORE_WEIGHTS['change_pct'] == 0.40
    assert LEADER_SCORE_WEIGHTS['volume'] == 0.30
    assert LEADER_SCORE_WEIGHTS['market_cap'] == 0.20
    assert LEADER_SCORE_WEIGHTS['trade_value'] == 0.10
    assert DEFAULT_TOP_N_THEMES == 20
    assert DEFAULT_LEADERS_PER_THEME == 3
