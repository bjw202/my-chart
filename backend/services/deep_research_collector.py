"""SPEC-AI-REPORT-002 Phase B: 5-소스 병렬 수집 + /tmp 스테이징.

5개 검색 API(Perplexity/Brave/Tavily/Naver/YouTube)를 asyncio.gather로 병렬 수집하여
/tmp/<uuid> 스테이징 디렉토리에 정규화된 데이터를 저장한다.

파이프라인에서 Phase B (수집 + 스테이징) 담당.
Phase C(claude_cli_streamer)에서 이 모듈의 create_staging_directory 결과를 소비한다.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 데이터 클래스
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SourceResult:
    """단일 소스 수집 결과."""

    name: str
    success: bool
    data: dict | list | str | None
    error_type: str | None = None  # "timeout" | "http_error" | "missing_key" | "parse_error"
    error_message: str | None = None
    duration_ms: int = 0
    # SPEC-AI-REPORT-002 v1.0.4: 캐시 재사용 여부 플래그.
    # 진행 상태 패널에서 "캐시 재사용 (0ms)" 표시 + 실제 HTTP 호출과 구분.
    # Perplexity만 cache hit 경로를 가지며 나머지 소스는 항상 False.
    cached: bool = False


@dataclass(frozen=True)
class CollectionResult:
    """5-소스 병렬 수집 결과.

    gate_passed: 2개 이상 소스 성공 여부.
    """

    code: str
    stock_name: str
    sources: dict[str, SourceResult]
    gate_passed: bool
    started_at: datetime
    completed_at: datetime

    @classmethod
    def build(
        cls,
        code: str,
        stock_name: str,
        sources: dict[str, SourceResult],
        started_at: datetime,
        completed_at: datetime,
    ) -> "CollectionResult":
        gate_passed = sum(1 for s in sources.values() if s.success) >= 2
        return cls(
            code=code,
            stock_name=stock_name,
            sources=sources,
            gate_passed=gate_passed,
            started_at=started_at,
            completed_at=completed_at,
        )


# ─────────────────────────────────────────────────────────────────────────────
# API URL 상수
# ─────────────────────────────────────────────────────────────────────────────

_PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
_TAVILY_URL = "https://api.tavily.com/search"
_NAVER_WEB_URL = "https://openapi.naver.com/v1/search/webkr.json"
_NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
_YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/search"


# ─────────────────────────────────────────────────────────────────────────────
# 파서 어댑터 (merge_results.py 포팅)
# ─────────────────────────────────────────────────────────────────────────────


def _strip_think_blocks(text: str) -> str:
    """<think>...</think> DOTALL 패턴을 모두 제거한다."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _normalize_brave(data: dict | None) -> list[dict]:
    # Adapted from docs/deep-research/scripts/merge_results.py::parse_brave
    if not data or "web" not in data:
        return []
    results = []
    for item in data.get("web", {}).get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "source": "brave",
            }
        )
    return results


def _normalize_tavily(data: dict | None) -> dict:
    # Adapted from docs/deep-research/scripts/merge_results.py::parse_tavily
    if not data:
        return {"results": [], "answer": None}
    results = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", 0),
                "source": "tavily",
            }
        )
    return {"results": results, "answer": data.get("answer")}


def _normalize_perplexity(data: dict | None) -> dict:
    # Adapted from docs/deep-research/scripts/merge_results.py::parse_perplexity
    # <think> 블록 제거 로직 추가
    if not data or "choices" not in data:
        return {"content": None, "citations": []}
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    raw_content = message.get("content", "")
    cleaned = _strip_think_blocks(raw_content)
    return {"content": cleaned, "citations": data.get("citations", [])}


def _normalize_naver(data: dict | None) -> list[dict]:
    # Adapted from docs/deep-research/scripts/merge_results.py::parse_naver
    if not data or "items" not in data:
        return []
    results = []
    for item in data.get("items", []):
        # HTML 태그 제거
        title = re.sub(r"<[^>]+>", "", item.get("title", ""))
        description = re.sub(r"<[^>]+>", "", item.get("description", ""))
        results.append(
            {
                "title": title,
                "url": item.get("link", ""),
                "snippet": description,
                "source": "naver",
            }
        )
    return results


def _normalize_youtube(data: dict | None) -> list[dict]:
    # Adapted from docs/deep-research/scripts/merge_results.py::parse_youtube
    if not data or "items" not in data:
        return []
    results = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("id", {}).get("videoId", "")
        results.append(
            {
                "title": snippet.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                "snippet": snippet.get("description", ""),
                "channel": snippet.get("channelTitle", ""),
                "published": snippet.get("publishedAt", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                "source": "youtube",
            }
        )
    return results


def _deduplicate_by_url(results: list[dict]) -> list[dict]:
    # Adapted from docs/deep-research/scripts/merge_results.py::deduplicate_results
    seen_urls: set[str] = set()
    unique = []
    for item in results:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(item)
    return unique


# ─────────────────────────────────────────────────────────────────────────────
# 소스별 수집 함수
# ─────────────────────────────────────────────────────────────────────────────


async def _collect_perplexity(
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> SourceResult:
    # curl 명령 구조 참조: docs/deep-research/skill.md §2
    # SPEC-AI-REPORT-002 v1.0.3: 시나리오 C(빠른→심층) 비용 절감 — 빠른 분석에서 캐시한
    # full markdown이 신선(TTL 10분)하면 HTTP 호출 스킵하고 그것을 perplexity 결과로 사용.
    # Lazy import: 테스트 격리 환경에서 stub 누락 시 silent skip → 일반 호출 흐름 유지.
    cached: str | None = None
    try:
        from backend.services.perplexity_cache import get as _cache_get
        cached = _cache_get(code)
    except ImportError:
        cached = None
    if cached:
        return SourceResult(
            name="perplexity",
            success=True,
            data={"content": cached, "citations": []},  # citations은 캐시에 별도 저장 X (재호출 시만 확보)
            duration_ms=0,
            cached=True,
        )

    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return SourceResult(
            name="perplexity",
            success=False,
            data=None,
            error_type="missing_key",
            error_message="PERPLEXITY_API_KEY 환경변수 미설정",
        )

    query = f"{stock_name}({code}) 한국 주식 스윙 트레이딩 분석"
    payload = {
        "model": "sonar-reasoning-pro",
        "messages": [{"role": "user", "content": query}],
        "return_citations": True,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.monotonic()
    try:
        _client = client or httpx.AsyncClient()
        async with (contextlib.nullcontext(_client) if client else _client) as c:
            response = await c.post(_PERPLEXITY_URL, json=payload, headers=headers)
        if response.status_code >= 400:
            return SourceResult(
                name="perplexity",
                success=False,
                data=None,
                error_type="http_error",
                error_message=f"HTTP {response.status_code}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        raw = response.json()
        normalized = _normalize_perplexity(raw)
        return SourceResult(
            name="perplexity",
            success=True,
            data=normalized,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except httpx.TimeoutException as exc:
        return SourceResult(
            name="perplexity",
            success=False,
            data=None,
            error_type="timeout",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SourceResult(
            name="perplexity",
            success=False,
            data=None,
            error_type="http_error",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _collect_brave(
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> SourceResult:
    # curl 명령 구조 참조: docs/deep-research/skill.md §2
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return SourceResult(
            name="brave",
            success=False,
            data=None,
            error_type="missing_key",
            error_message="BRAVE_API_KEY 환경변수 미설정",
        )

    query = f"{stock_name} {code} 주식 분석 스윙트레이딩"
    params = {"q": query, "count": 20}
    headers = {"X-Subscription-Token": api_key}

    start = time.monotonic()
    try:
        _client = client or httpx.AsyncClient()
        async with (contextlib.nullcontext(_client) if client else _client) as c:
            response = await c.get(_BRAVE_URL, params=params, headers=headers)
        if response.status_code >= 400:
            return SourceResult(
                name="brave",
                success=False,
                data=None,
                error_type="http_error",
                error_message=f"HTTP {response.status_code}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        raw = response.json()
        normalized = _normalize_brave(raw)
        return SourceResult(
            name="brave",
            success=True,
            data=normalized,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except httpx.TimeoutException as exc:
        return SourceResult(
            name="brave",
            success=False,
            data=None,
            error_type="timeout",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SourceResult(
            name="brave",
            success=False,
            data=None,
            error_type="http_error",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _collect_tavily(
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> SourceResult:
    # curl 명령 구조 참조: docs/deep-research/skill.md §2
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return SourceResult(
            name="tavily",
            success=False,
            data=None,
            error_type="missing_key",
            error_message="TAVILY_API_KEY 환경변수 미설정",
        )

    query = f"{stock_name}({code}) 스윙 트레이딩 기술적 분석"
    payload = {
        "query": query,
        "search_depth": "advanced",
        "max_results": 20,
        "include_answer": "advanced",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.monotonic()
    try:
        _client = client or httpx.AsyncClient()
        async with (contextlib.nullcontext(_client) if client else _client) as c:
            response = await c.post(_TAVILY_URL, json=payload, headers=headers)
        if response.status_code >= 400:
            return SourceResult(
                name="tavily",
                success=False,
                data=None,
                error_type="http_error",
                error_message=f"HTTP {response.status_code}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        raw = response.json()
        normalized = _normalize_tavily(raw)
        return SourceResult(
            name="tavily",
            success=True,
            data=normalized,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except httpx.TimeoutException as exc:
        return SourceResult(
            name="tavily",
            success=False,
            data=None,
            error_type="timeout",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SourceResult(
            name="tavily",
            success=False,
            data=None,
            error_type="http_error",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _collect_naver(
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> SourceResult:
    # curl 명령 구조 참조: docs/deep-research/skill.md §2
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return SourceResult(
            name="naver",
            success=False,
            data=None,
            error_type="missing_key",
            error_message="NAVER_CLIENT_ID/SECRET 환경변수 미설정",
        )

    # 종목 식별 모호성 회피: "{회사명} {6자리코드}" 패턴으로 동명이인 회사 결과 배제
    # (예: "우리로" → "우리은행/우리금융/우리이앤엘" 결과 섞임 방지)
    korean_query = f"{stock_name} {code} 주식"
    params = {"query": korean_query, "display": 10}
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    start = time.monotonic()
    try:
        _client = client or httpx.AsyncClient()
        async with (contextlib.nullcontext(_client) if client else _client) as c:
            response = await c.get(_NAVER_WEB_URL, params=params, headers=headers)
        if response.status_code >= 400:
            return SourceResult(
                name="naver",
                success=False,
                data=None,
                error_type="http_error",
                error_message=f"HTTP {response.status_code}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        raw = response.json()
        normalized = _normalize_naver(raw)
        return SourceResult(
            name="naver",
            success=True,
            data=normalized,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except httpx.TimeoutException as exc:
        return SourceResult(
            name="naver",
            success=False,
            data=None,
            error_type="timeout",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SourceResult(
            name="naver",
            success=False,
            data=None,
            error_type="http_error",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _collect_youtube(
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> SourceResult:
    # curl 명령 구조 참조: docs/deep-research/skill.md §2
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return SourceResult(
            name="youtube",
            success=False,
            data=None,
            error_type="missing_key",
            error_message="YOUTUBE_API_KEY 환경변수 미설정",
        )

    # 종목 식별 모호성 회피: 회사명 + 종목 코드 둘 다 포함 (Naver와 동일 이유)
    query = f"{stock_name} {code} 주식 분석"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 10,
        "key": api_key,
    }

    start = time.monotonic()
    try:
        _client = client or httpx.AsyncClient()
        async with (contextlib.nullcontext(_client) if client else _client) as c:
            response = await c.get(_YOUTUBE_URL, params=params)
        if response.status_code >= 400:
            return SourceResult(
                name="youtube",
                success=False,
                data=None,
                error_type="http_error",
                error_message=f"HTTP {response.status_code}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        raw = response.json()
        normalized = _normalize_youtube(raw)
        return SourceResult(
            name="youtube",
            success=True,
            data=normalized,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except httpx.TimeoutException as exc:
        return SourceResult(
            name="youtube",
            success=False,
            data=None,
            error_type="timeout",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SourceResult(
            name="youtube",
            success=False,
            data=None,
            error_type="http_error",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 오케스트레이션: 5-소스 병렬 수집
# ─────────────────────────────────────────────────────────────────────────────


# 소스별 권장 타임아웃 (초). docs/search.sh 레퍼런스 기준:
#   - perplexity sonar-reasoning-pro: 30~90s 응답이 정상 (search.sh: --max-time 120)
#   - tavily advanced: 60~120s (search.sh: --max-time 60~120)
#   - brave/naver/youtube: 단순 검색 API, ~3-5s 응답
_DEFAULT_TIMEOUTS: dict[str, float] = {
    "perplexity": 120.0,
    "tavily": 90.0,
    "brave": 15.0,
    "naver": 15.0,
    "youtube": 15.0,
}

# httpx.AsyncClient 기본 타임아웃: connect는 짧게, read는 source별 timeout이 wait_for로 잡으므로
# 충분히 길게 설정 (asyncio.wait_for가 외부에서 자른다).
_DEFAULT_HTTPX_TIMEOUT = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)

# SPEC-AI-REPORT-002 v1.0.4: 소스명 순서 (진행 상태 패널 표시 순 고정).
# collect_all_sources 내부와 _collect_one_source helper가 공유.
SOURCE_NAMES: tuple[str, ...] = ("perplexity", "brave", "tavily", "naver", "youtube")


# @MX:ANCHOR _collect_one_source — fan_in >= 2 (collect_all_sources, stream_deep_analysis).
# @MX:REASON SPEC-AI-REPORT-002 v1.0.4: 진행 상태 패널을 위해 소스별 개별 수집 + timeout wrapper 통합.
#            collector 함수는 모듈 attribute lookup으로 런타임 resolve — monkeypatch 호환성 보장.
async def _collect_one_source(
    name: str,
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | None = None,
) -> SourceResult:
    """단일 소스를 수집한다. timeout 초과 또는 예외 발생 시 실패 SourceResult를 반환한다.

    Args:
        name: 소스 이름 (SOURCE_NAMES 중 하나).
        code: 종목 코드.
        stock_name: 종목명.
        client: 테스트 주입용 httpx.AsyncClient.
        timeout: 단일 호출 timeout (초). None이면 _DEFAULT_TIMEOUTS[name].

    Returns:
        SourceResult — 성공/실패 정보 + duration_ms + cached(perplexity cache hit 시 True).
    """
    if name not in SOURCE_NAMES:
        raise ValueError(f"알 수 없는 소스: {name}")

    # 런타임에 모듈 globals로 resolve — pytest monkeypatch.setattr(_MOD, "_collect_xxx", ...)
    # 호환성 유지. globals()는 "이 함수가 정의된 모듈 인스턴스"의 __dict__를 반환하므로,
    # test helper가 sys.modules를 다른 인스턴스로 덮어써도 원본 인스턴스의 mock이 호출된다.
    collector_fn = globals()[f"_collect_{name}"]

    effective_timeout = timeout if timeout is not None else _DEFAULT_TIMEOUTS[name]
    start = time.monotonic()
    try:
        return await asyncio.wait_for(
            collector_fn(code, stock_name, client=client),
            timeout=effective_timeout,
        )
    except asyncio.TimeoutError:
        return SourceResult(
            name=name,
            success=False,
            data=None,
            error_type="timeout",
            error_message=f"asyncio.wait_for timeout ({effective_timeout}s)",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return SourceResult(
            name=name,
            success=False,
            data=None,
            error_type="http_error",
            error_message=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


ProgressCallback = Callable[[dict], Awaitable[None]]


# @MX:ANCHOR collect_all_sources — fan_in >= 2 (orchestrator + tests). Invariant: gate_passed == (successful_sources >= 2). progress_callback이 주어지면 소스별 시작/완료 이벤트를 실시간 emit.
# @MX:REASON SPEC-AI-REPORT-002 FR-002/v1.0.4: 5개 소스를 병렬 수집하며, 개별 소스 실패가 전체 파이프라인을 중단시켜서는 안 된다. progress_callback으로 실시간 진행 상황 전달 (None이면 기존 동작 유지).
async def collect_all_sources(
    code: str,
    stock_name: str,
    *,
    timeout_per_source: float | None = None,
    timeouts: dict[str, float] | None = None,
    client: httpx.AsyncClient | None = None,
    progress_callback: ProgressCallback | None = None,
) -> CollectionResult:
    """5개 검색 API를 병렬 수집한다.

    Args:
        code: 종목 코드 (예: "005930")
        stock_name: 종목명 (예: "삼성전자")
        timeout_per_source: 모든 소스에 동일하게 적용할 단일 timeout. None이면 source별 기본값
            사용. 테스트 호환을 위해 유지 (기존 시그니처).
        timeouts: source별 timeout override. {"perplexity": 60.0, ...} 형식. timeout_per_source
            보다 우선 적용된다.
        client: 테스트 주입용 httpx.AsyncClient
        progress_callback: SPEC-AI-REPORT-002 v1.0.4 — 실시간 진행 이벤트 콜백. 소스 시작 시
            `{"phase": "source_start", "source": name}`, 소스 완료 시
            `{"phase": "source_done", "result": SourceResult}`를 await 호출. None이면 기존 동작.

    Returns:
        CollectionResult — gate_passed == (성공 소스 수 >= 2)
    """
    started_at = datetime.now(timezone.utc)

    # 효과적 timeout 계산: 기본값 → timeout_per_source 단일값 → timeouts dict override
    effective_timeouts = dict(_DEFAULT_TIMEOUTS)
    if timeout_per_source is not None:
        effective_timeouts = {k: timeout_per_source for k in effective_timeouts}
    if timeouts:
        effective_timeouts.update(timeouts)

    async def _run(c: httpx.AsyncClient) -> dict[str, SourceResult]:
        # 5개 source_start 이벤트 — task 생성 직전 순서대로 emit.
        if progress_callback is not None:
            for name in SOURCE_NAMES:
                await progress_callback({"phase": "source_start", "source": name})

        task_to_name: dict[asyncio.Task, str] = {
            asyncio.create_task(
                _collect_one_source(
                    name,
                    code,
                    stock_name,
                    client=c,
                    timeout=effective_timeouts[name],
                )
            ): name
            for name in SOURCE_NAMES
        }

        collected: dict[str, SourceResult] = {}
        pending: set[asyncio.Task] = set(task_to_name.keys())
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for t in done:
                tname = task_to_name[t]
                exc = t.exception()
                if exc is not None:
                    src = SourceResult(
                        name=tname,
                        success=False,
                        data=None,
                        error_type="http_error",
                        error_message=str(exc),
                    )
                else:
                    src = t.result()
                collected[tname] = src
                if progress_callback is not None:
                    await progress_callback(
                        {"phase": "source_done", "result": src}
                    )
        return collected

    if client is not None:
        sources = await _run(client)
    else:
        async with httpx.AsyncClient(timeout=_DEFAULT_HTTPX_TIMEOUT) as shared_client:
            sources = await _run(shared_client)

    completed_at = datetime.now(timezone.utc)
    result = CollectionResult.build(
        code=code,
        stock_name=stock_name,
        sources=sources,
        started_at=started_at,
        completed_at=completed_at,
    )

    successful = sum(1 for s in sources.values() if s.success)
    logger.info(
        "소스 수집 완료: %d/5 성공 (gate_passed=%s) [코드=%s]",
        successful,
        result.gate_passed,
        code,
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 스테이징 디렉토리 생성
# ─────────────────────────────────────────────────────────────────────────────


def _build_summary_md(code: str, stock_name: str, result: CollectionResult) -> str:
    """summary.md 마크다운 생성.

    소스 상태 테이블 + 합성 지시 포함.
    """
    lines = [
        f"# Deep Research 스테이징: {stock_name}({code})",
        f"",
        f"## 수집 시간",
        f"- 시작: {result.started_at.isoformat()}",
        f"- 완료: {result.completed_at.isoformat()}",
        f"",
        f"## 소스 수집 현황",
        f"",
        f"| 소스 | 상태 | 오류 |",
        f"|------|------|------|",
    ]

    source_display = {
        "perplexity": "Perplexity",
        "brave": "Brave Search",
        "tavily": "Tavily",
        "naver": "Naver",
        "youtube": "YouTube",
    }

    for src_key, display_name in source_display.items():
        src = result.sources.get(src_key)
        if src is None:
            lines.append(f"| {display_name} | ❌ 미수집 | N/A |")
        elif src.success:
            lines.append(f"| {display_name} | ✅ 성공 | - |")
        else:
            err = src.error_type or "unknown"
            msg = src.error_message or ""
            lines.append(f"| {display_name} | ❌ 실패 | {err}: {msg} |")

    successful = sum(1 for s in result.sources.values() if s.success)
    lines += [
        f"",
        f"**성공: {successful}/5** | gate_passed: {result.gate_passed}",
        f"",
        f"## 합성 지시",
        f"",
        f"아래 sources/ 디렉토리의 파일을 교차 검증하여 한국 스윙 트레이딩 리포트를 생성하라:",
        f"",
        f"- `sources/perplexity.md` (Perplexity AI 분석, think 블록 제거됨)",
        f"- `sources/brave.json` (Brave 웹 검색 결과)",
        f"- `sources/tavily.json` (Tavily 심층 검색 + AI 요약)",
        f"- `sources/naver.json` (Naver 한국어 뉴스/웹 검색)",
        f"- `sources/youtube.json` (YouTube 관련 영상)",
        f"",
        f"없는 파일은 해당 소스가 수집 실패한 것이며, 가용 소스만으로 분석을 수행하라.",
        f"출처 인용 시 `[brave]`, `[tavily]`, `[naver]`, `[youtube]` 레이블을 사용하라.",
    ]
    return "\n".join(lines)


# @MX:ANCHOR create_staging_directory — fan_in >= 2 (orchestrator + tests). Invariant: UUID8 suffix, /tmp path safety check, 실패 소스는 JSON 파일 생성 안 함.
# @MX:REASON SPEC-AI-REPORT-002 FR-003: 스테이징 디렉토리 경로 탈출 방지 + 소스별 파일 선택적 생성.
def create_staging_directory(
    code: str,
    result: CollectionResult,
    *,
    base_dir: Path = Path("/tmp"),
) -> Path:
    """스테이징 디렉토리를 생성하고 수집 결과를 파일로 저장한다.

    디렉토리 이름 형식: analysis_<code>_<ISO8601-UTC>_<uuid8>/

    Args:
        code: 종목 코드
        result: CollectionResult (소스별 수집 결과)
        base_dir: 기본 디렉토리 (기본 /tmp; 테스트 시 tmp_path 전달)

    Returns:
        생성된 스테이징 디렉토리 Path

    Raises:
        ValueError: base_dir가 /tmp 외부를 가리키는 경우
    """
    # /tmp 경로 안전성 검사 (NFR-005)
    # 위험한 시스템 경로를 차단한다 (경로 탈출 방지).
    # 허용: /tmp, /tmp 하위, macOS /private/tmp, 시스템 임시 디렉토리.
    # 거부: /usr, /etc, /bin, /sbin, /lib, /root, /home, /var (tmp 제외).
    _BLOCKED_ROOTS = {"/usr", "/etc", "/bin", "/sbin", "/lib", "/root", "/home"}
    resolved = base_dir.resolve()
    resolved_str = str(resolved)
    # 차단 목록의 경로이거나 그 하위인 경우 거부
    for blocked in _BLOCKED_ROOTS:
        if resolved_str == blocked or resolved_str.startswith(blocked + "/"):
            raise ValueError(
                f"base_dir '{base_dir}' resolved to '{resolved}' which is outside /tmp"
            )

    # UUID8 생성 및 디렉토리 이름 조합
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uuid8 = uuid.uuid4().hex[:8]
    dir_name = f"analysis_{code}_{ts}_{uuid8}"
    staging_dir = resolved / dir_name
    sources_dir = staging_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    # summary.md 작성
    summary_content = _build_summary_md(code, result.stock_name, result)
    (staging_dir / "summary.md").write_text(summary_content, encoding="utf-8")

    # 소스별 파일 작성 (성공 소스만)
    for src_key, src_result in result.sources.items():
        if not src_result.success or src_result.data is None:
            continue

        if src_key == "perplexity":
            # perplexity.md로 저장, think 블록 제거
            if isinstance(src_result.data, dict):
                content = src_result.data.get("content", "")
                citations = src_result.data.get("citations", [])
            else:
                content = str(src_result.data)
                citations = []
            # think 블록 재차 제거 (이중 안전)
            cleaned = _strip_think_blocks(content)
            md_lines = [f"# Perplexity 분석\n\n{cleaned}"]
            if citations:
                md_lines.append("\n\n## 출처\n")
                md_lines.extend(f"- {c}" for c in citations)
            (sources_dir / "perplexity.md").write_text(
                "\n".join(md_lines), encoding="utf-8"
            )
        else:
            # JSON 파일로 저장
            json_path = sources_dir / f"{src_key}.json"
            json_path.write_text(
                json.dumps(src_result.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    logger.info(
        "스테이징 디렉토리 생성: %s (성공소스=%d/5)",
        staging_dir,
        sum(1 for s in result.sources.values() if s.success),
    )
    return staging_dir
