import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.services.naver_theme.config import (
    NAVER_THEME_LIST_URL,
    NAVER_THEME_DETAIL_URL,
    CRAWL_DELAY,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    USER_AGENT,
)

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    """Session 싱글톤 with Retry adapter."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session


def fetch_theme_list_page(page: int) -> str:
    """네이버 테마 목록 페이지 HTML 반환.

    @param page: 페이지 번호 (1부터 시작)
    @return: HTML 문자열
    """
    session = _get_session()
    url = NAVER_THEME_LIST_URL.format(n=page)
    resp = session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    time.sleep(CRAWL_DELAY)
    return resp.text


def fetch_theme_detail_page(theme_id: int) -> str:
    """테마 상세 페이지 HTML 반환.

    @param theme_id: 테마 ID
    @return: HTML 문자열
    """
    session = _get_session()
    url = NAVER_THEME_DETAIL_URL.format(theme_id=theme_id)
    resp = session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    time.sleep(CRAWL_DELAY)
    return resp.text
