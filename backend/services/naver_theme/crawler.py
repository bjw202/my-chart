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
    RESPONSE_ENCODING,
)

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    # Session 싱글톤 with Retry adapter
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session


def _fetch(url: str) -> str:
    # REQ-NT-NF-002: EUC-KR 강제 설정 후 resp.text 접근
    sess = _get_session()
    resp = sess.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = RESPONSE_ENCODING  # 한글 깨짐 방지 — raise_for_status 직후 필수
    text = resp.text
    time.sleep(CRAWL_DELAY)
    return text


def fetch_theme_list_page(page: int) -> str:
    """네이버 테마 목록 페이지 HTML 반환."""
    return _fetch(NAVER_THEME_LIST_URL.format(n=page))


def fetch_theme_detail_page(theme_id: int) -> str:
    """테마 상세 페이지 HTML 반환."""
    return _fetch(NAVER_THEME_DETAIL_URL.format(theme_id=theme_id))
