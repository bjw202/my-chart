"""HTTP 호출 — JSON 응답, 단일 thread, specific exception (REQ-NT2-C-005)."""

import json
import time
from typing import Optional

import requests

from . import config

# @MX:NOTE: 매너 호출 정책 — 비공식 endpoint이므로 sleep 0.7s + 단일 thread 정책 (REQ-NT2-NF-001)
_SESSION: Optional[requests.Session] = None
_LAST_REQUEST_TIME: float = 0.0


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
    return _SESSION


def _enforce_sleep_policy() -> None:
    # @MX:NOTE: 매너 호출 정책 — 비공식 endpoint이므로 sleep 0.7s + 단일 thread 정책 (REQ-NT2-NF-001)
    global _LAST_REQUEST_TIME
    elapsed = time.monotonic() - _LAST_REQUEST_TIME
    if elapsed < config.REQUEST_SLEEP_SECONDS:
        time.sleep(config.REQUEST_SLEEP_SECONDS - elapsed)


def _build_headers() -> dict:
    # REQ-NT2-NF-001, REQ-NT2-C-001 — anonymous, mobile UA, Cookie/Authorization 절대 없음
    return {
        "User-Agent": config.MOBILE_USER_AGENT,
        "Referer": config.DEFAULT_REFERER,
        "Accept": config.ACCEPT_HEADER,
    }


def _verify_content_type(response: requests.Response) -> None:
    # REQ-NT2-NF-002: Content-Type 검증
    ct = response.headers.get("Content-Type", "")
    if "application/json" not in ct:
        raise ValueError(f"Unexpected Content-Type: {ct!r}")


def fetch_theme_list(page: int, page_size: int = config.LIST_PAGE_SIZE) -> dict:
    """List endpoint 호출. 5xx/timeout → 1회 retry. 영속 실패 시 raise."""
    # @MX:WARN: 비공식 endpoint 재시도 — endpoint URL 변경 시 schema_validation 필요
    # @MX:REASON: research.md §5 R-1, R-3 위험 mitigation
    url = (
        f"{config.NAVER_MOBILE_BASE_URL}"
        f"{config.NAVER_MOBILE_FRONT_API_PREFIX}"
        f"{config.LIST_ENDPOINT_PATH}"
    )
    params = {
        "sectorType": "theme",
        "businessDayCategory": "daily",
        "sectorSortType": "CHANGE_RATE",
        "nationType": "domestic",
        "page": page,
        "pageSize": page_size,
    }

    _enforce_sleep_policy()
    session = _get_session()

    last_exc: Optional[Exception] = None
    for attempt in (0, 1):
        try:
            response = session.get(
                url,
                params=params,
                headers=_build_headers(),
                timeout=config.REQUEST_TIMEOUT_SECONDS,
            )
            global _LAST_REQUEST_TIME
            _LAST_REQUEST_TIME = time.monotonic()

            if response.status_code >= 500:
                last_exc = requests.HTTPError(f"5xx: {response.status_code}")
                if attempt == 0:
                    time.sleep(config.RETRY_BACKOFF_SECONDS)
                    continue
                raise last_exc

            _verify_content_type(response)
            return response.json()
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            last_exc = e
            if attempt == 0:
                time.sleep(config.RETRY_BACKOFF_SECONDS)
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("unreachable")


def fetch_theme_detail(theme_id: int, page_size: int = config.DETAIL_PAGE_SIZE) -> dict:
    """Detail endpoint 호출. 동일한 retry 정책."""
    # @MX:WARN: 비공식 endpoint 재시도 — endpoint URL 변경 시 schema_validation 필요
    # @MX:REASON: research.md §5 R-1, R-3 위험 mitigation
    url = (
        f"{config.NAVER_MOBILE_BASE_URL}"
        f"{config.NAVER_MOBILE_FRONT_API_PREFIX}"
        f"{config.DETAIL_ENDPOINT_PATH}"
    )
    params = {
        "sectorType": "theme",
        "sectorCode": str(theme_id),
        "sectorSortType": "CHANGE_RATE",
        "page": 1,
        "pageSize": page_size,
    }

    _enforce_sleep_policy()
    session = _get_session()

    last_exc: Optional[Exception] = None
    for attempt in (0, 1):
        try:
            response = session.get(
                url,
                params=params,
                headers=_build_headers(),
                timeout=config.REQUEST_TIMEOUT_SECONDS,
            )
            global _LAST_REQUEST_TIME
            _LAST_REQUEST_TIME = time.monotonic()

            if response.status_code >= 500:
                last_exc = requests.HTTPError(f"5xx: {response.status_code}")
                if attempt == 0:
                    time.sleep(config.RETRY_BACKOFF_SECONDS)
                    continue
                raise last_exc

            _verify_content_type(response)
            return response.json()
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            last_exc = e
            if attempt == 0:
                time.sleep(config.RETRY_BACKOFF_SECONDS)
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("unreachable")
