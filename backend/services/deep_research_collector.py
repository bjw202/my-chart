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


# @MX:ANCHOR _collect_codex — SPEC-AI-REPORT-003 FR-002/FR-003.
# @MX:REASON Codex CLI 호출 슬롯. 1회 재시도 (timeout/exit_error/empty_output) + 결정론적 실패 (binary_missing/auth) 재시도 금지.
#            staging_sources_dir 에 직접 codex.md 를 기록하므로 finalize_staging_directory 는 이 파일을 덮어쓰지 않는다.
async def _collect_codex(
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,  # 미사용, _collect_one_source 시그니처 호환용
    staging_sources_dir: Path | None = None,
) -> SourceResult:
    """Codex CLI 를 호출해 `staging_sources_dir/codex.md` 에 심층 리서치 마크다운을 생성.

    FR-003 — 1회 재시도: 첫 호출이 timeout / exit_error / empty_output 로 실패하면 동일
    프롬프트로 한 번 더 호출. `binary_missing` / `auth` 는 결정론적 실패로 재시도 금지.

    Args:
        code: 종목 코드.
        stock_name: 종목명.
        client: 미사용 (Codex 는 httpx 미사용). 시그니처는 `_collect_one_source` 호환용.
        staging_sources_dir: `<staging>/sources/` 디렉토리. prepare_staging_directory 가
            선행 생성한 경로. 이 함수는 `<staging_sources_dir>/codex.md` 를 생성한다.

    Returns:
        SourceResult(name="codex", success=..., data={"markdown_path": ..., "char_count": ...} | None)
    """
    if staging_sources_dir is None:
        # 호출자 로직 오류 — collect_all_sources 가 staging_sources_dir 을 전달하지 않은 경우
        return SourceResult(
            name="codex",
            success=False,
            data=None,
            error_type="missing_staging_dir",
            error_message="codex 수집은 staging_sources_dir 인자가 필수입니다",
        )

    output_path = staging_sources_dir / "codex.md"

    # Lazy import — 테스트 격리 환경에서 codex_cli_runner 미로드 대비
    try:
        from backend.services.codex_cli_runner import (
            load_codex_prompt,
            run_codex_research,
        )
    except ImportError as exc:
        return SourceResult(
            name="codex",
            success=False,
            data=None,
            error_type="import_error",
            error_message=f"codex_cli_runner import 실패: {exc}",
        )

    # 프롬프트 로드 실패 (템플릿 미존재 / malformed) 는 결정론적 실패 — 재시도 없음
    try:
        prompt = load_codex_prompt(code=code, stock_name=stock_name)
    except (FileNotFoundError, ValueError) as exc:
        return SourceResult(
            name="codex",
            success=False,
            data=None,
            error_type="prompt_error",
            error_message=str(exc),
        )

    start = time.monotonic()
    last_error_type: str | None = None
    last_error_message: str | None = None

    # FR-003: 최대 2회 시도 (최초 + 1회 재시도)
    for _attempt in range(2):
        # 이전 실패의 불완전 파일이 남아있으면 제거 → empty_output 오탐 방지
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass

        codex_result = await run_codex_research(
            code=code,
            stock_name=stock_name,
            output_path=output_path,
            prompt=prompt,
        )

        if codex_result.success:
            return SourceResult(
                name="codex",
                success=True,
                data={
                    "markdown_path": str(output_path),
                    "char_count": codex_result.char_count,
                },
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        last_error_type = codex_result.error_type
        last_error_message = codex_result.error_message

        # ER-001 / ER-002: 결정론적 실패는 재시도 금지 (FR-003 두 번째 문장)
        if codex_result.error_type in ("binary_missing", "auth"):
            break

    return SourceResult(
        name="codex",
        success=False,
        data=None,
        error_type=last_error_type or "unknown",
        error_message=last_error_message,
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


# 소스별 권장 타임아웃 (초):
#   - codex: 장시간 subprocess (plan.md NFR-001, 관측 2~9분) — 600s
#   - tavily advanced: 60~120s (search.sh: --max-time 60~120)
#   - brave/naver/youtube: 단순 검색 API, ~3-5s 응답
# SPEC-AI-REPORT-003: perplexity 키 제거, codex 추가.
_DEFAULT_TIMEOUTS: dict[str, float] = {
    "codex": 600.0,
    "tavily": 90.0,
    "brave": 15.0,
    "naver": 15.0,
    "youtube": 15.0,
}

# httpx.AsyncClient 기본 타임아웃: connect는 짧게, read는 source별 timeout이 wait_for로 잡으므로
# 충분히 길게 설정 (asyncio.wait_for가 외부에서 자른다).
_DEFAULT_HTTPX_TIMEOUT = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)

# SPEC-AI-REPORT-003 FR-002/FR-008: 소스명 순서 (진행 상태 패널 표시 순 고정).
# 이전 SPEC-AI-REPORT-002 의 "perplexity" 슬롯이 "codex" 로 교체됨.
SOURCE_NAMES: tuple[str, ...] = ("codex", "brave", "tavily", "naver", "youtube")


# @MX:ANCHOR _collect_one_source — fan_in >= 2 (collect_all_sources, stream_deep_analysis).
# @MX:REASON SPEC-AI-REPORT-003: 진행 상태 패널을 위해 소스별 개별 수집 + timeout wrapper 통합.
#            collector 함수는 모듈 attribute lookup 으로 런타임 resolve — monkeypatch 호환성 유지.
#            codex 는 staging_sources_dir kwarg 도 전달받는다 (다른 소스는 httpx client 만 사용).
async def _collect_one_source(
    name: str,
    code: str,
    stock_name: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | None = None,
    staging_sources_dir: Path | None = None,
) -> SourceResult:
    """단일 소스를 수집한다. timeout 초과 또는 예외 발생 시 실패 SourceResult 를 반환.

    Args:
        name: 소스 이름 (SOURCE_NAMES 중 하나).
        code: 종목 코드.
        stock_name: 종목명.
        client: 테스트 주입용 httpx.AsyncClient.
        timeout: 단일 호출 timeout (초). None이면 _DEFAULT_TIMEOUTS[name].
        staging_sources_dir: codex 소스 전용 — <staging>/sources/ 디렉토리 경로.

    Returns:
        SourceResult — 성공/실패 정보 + duration_ms.
    """
    if name not in SOURCE_NAMES:
        raise ValueError(f"알 수 없는 소스: {name}")

    collector_fn = globals()[f"_collect_{name}"]

    effective_timeout = timeout if timeout is not None else _DEFAULT_TIMEOUTS[name]
    start = time.monotonic()

    # codex 소스는 staging_sources_dir 를 추가로 전달. 다른 소스는 httpx client 만 사용.
    if name == "codex":
        coro = collector_fn(
            code, stock_name, client=client, staging_sources_dir=staging_sources_dir
        )
    else:
        coro = collector_fn(code, stock_name, client=client)

    try:
        return await asyncio.wait_for(coro, timeout=effective_timeout)
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
    staging_sources_dir: Path | None = None,
) -> CollectionResult:
    """5개 검색 API를 병렬 수집한다.

    SPEC-AI-REPORT-003 이후 codex 슬롯은 `staging_sources_dir` 이 제공되어야 하며,
    codex 는 `<staging_sources_dir>/codex.md` 에 직접 마크다운을 기록한다.

    Args:
        code: 종목 코드 (예: "005930")
        stock_name: 종목명 (예: "삼성전자")
        timeout_per_source: 모든 소스에 동일하게 적용할 단일 timeout. None이면 source별 기본값
            사용. 테스트 호환을 위해 유지 (기존 시그니처).
        timeouts: source별 timeout override. {"codex": 600.0, ...} 형식. timeout_per_source
            보다 우선 적용된다.
        client: 테스트 주입용 httpx.AsyncClient.
        progress_callback: 실시간 진행 이벤트 콜백. 소스 시작 시
            `{"phase": "source_start", "source": name}`, 소스 완료 시
            `{"phase": "source_done", "result": SourceResult}` 를 await 호출.
        staging_sources_dir: codex 수집에 필요. prepare_staging_directory 가 생성한
            `<staging>/sources/` 경로. 누락 시 codex 슬롯은 `missing_staging_dir` 로 실패.

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
                    staging_sources_dir=staging_sources_dir,
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
        "codex": "Codex 심층 리서치",
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
        f"- `sources/codex.md` (Codex 심층 리서치 결과, 원출처 URL 포함)",
        f"- `sources/brave.json` (Brave 웹 검색 결과)",
        f"- `sources/tavily.json` (Tavily 심층 검색 + AI 요약)",
        f"- `sources/naver.json` (Naver 한국어 뉴스/웹 검색)",
        f"- `sources/youtube.json` (YouTube 관련 영상)",
        f"",
        f"없는 파일은 해당 소스가 수집 실패한 것이며, 가용 소스만으로 분석을 수행하라.",
        f"출처 인용 시 `[codex]`, `[brave]`, `[tavily]`, `[naver]`, `[youtube]` 레이블을 사용하라.",
    ]
    return "\n".join(lines)


# @MX:ANCHOR create_staging_directory — fan_in >= 2 (orchestrator + tests). Invariant: UUID8 suffix, /tmp path safety check, 실패 소스는 JSON 파일 생성 안 함.
# @MX:REASON SPEC-AI-REPORT-002 FR-003: 스테이징 디렉토리 경로 탈출 방지 + 소스별 파일 선택적 생성.
# /tmp 경로 안전성 검사용 차단 목록 (NFR-005).
# 허용: /tmp, /tmp 하위, macOS /private/tmp, 시스템 임시 디렉토리.
# 거부: /usr, /etc, /bin, /sbin, /lib, /root, /home, /var (tmp 제외).
_BLOCKED_ROOTS: frozenset[str] = frozenset(
    {"/usr", "/etc", "/bin", "/sbin", "/lib", "/root", "/home"}
)


def _assert_safe_base_dir(base_dir: Path) -> Path:
    """base_dir 가 시스템 경로로 탈출하지 않는지 검증하고 resolved Path 반환.

    Raises:
        ValueError: base_dir 가 _BLOCKED_ROOTS 에 포함되거나 그 하위인 경우.
    """
    resolved = base_dir.resolve()
    resolved_str = str(resolved)
    for blocked in _BLOCKED_ROOTS:
        if resolved_str == blocked or resolved_str.startswith(blocked + "/"):
            raise ValueError(
                f"base_dir '{base_dir}' resolved to '{resolved}' which is outside /tmp"
            )
    return resolved


# @MX:ANCHOR prepare_staging_directory — fan_in >= 2 (service.py collect 전 + create_staging_directory wrapper).
# @MX:REASON SPEC-AI-REPORT-003 FR-006: Codex --output-last-message 가 호출 시점에 경로 존재를 요구하므로
#            staging 생성은 collect 이전 (prepare) 과 이후 (finalize) 로 분리되어야 한다.
def prepare_staging_directory(
    code: str,
    *,
    base_dir: Path = Path("/tmp"),
) -> Path:
    """스테이징 디렉토리와 `sources/` 하위 디렉토리를 **선행** 생성한다.

    Codex CLI 의 `--output-last-message` 인자는 호출 시점에 경로가 존재해야 하므로,
    SPEC-AI-REPORT-003 이후 staging 생성은 collect 이전 (prepare) 과 이후 (finalize) 로
    분리된다. 이 함수는 경로 안전 검사 + 디렉토리 생성만 수행하고, summary.md 나
    소스 파일 작성은 `finalize_staging_directory` 에서 수행한다.

    Args:
        code: 종목 코드.
        base_dir: 기본 디렉토리 (기본 /tmp; 테스트 시 tmp_path 전달).

    Returns:
        생성된 staging 디렉토리 Path. `<staging>/sources/` 는 이미 존재함.

    Raises:
        ValueError: base_dir 가 /tmp 외부를 가리키는 경우.
    """
    resolved = _assert_safe_base_dir(base_dir)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uuid8 = uuid.uuid4().hex[:8]
    dir_name = f"analysis_{code}_{ts}_{uuid8}"
    staging_dir = resolved / dir_name
    sources_dir = staging_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    logger.info("스테이징 디렉토리 선행 생성: %s", staging_dir)
    return staging_dir


# @MX:ANCHOR finalize_staging_directory — fan_in >= 2 (service.py collect 후 + create_staging_directory wrapper).
# @MX:REASON SPEC-AI-REPORT-003 FR-006: summary.md 와 JSON 소스 파일은 collect 완료 후에만 기록.
#            Codex 는 이미 staging/sources/codex.md 를 직접 썼으므로 여기서는 덮어쓰지 않는다.
def finalize_staging_directory(
    staging_dir: Path,
    code: str,
    stock_name: str,
    result: CollectionResult,
) -> None:
    """prepare 로 생성된 staging 디렉토리에 summary.md + 성공 소스 파일을 기록한다.

    Codex 가 이미 `staging/sources/codex.md` 를 직접 기록한 경우, 그 파일은 덮어쓰지
    않는다 (codex 의 SourceResult.data 는 markdown_path 정보만 담고 있으며, 이 함수는
    codex 소스에 대해 파일 쓰기를 스킵한다).

    Args:
        staging_dir: prepare_staging_directory 반환값.
        code: 종목 코드.
        stock_name: 종목명.
        result: CollectionResult.
    """
    sources_dir = staging_dir / "sources"

    # summary.md 작성
    summary_content = _build_summary_md(code, stock_name, result)
    (staging_dir / "summary.md").write_text(summary_content, encoding="utf-8")

    # 소스별 파일 작성 (성공 소스만). codex 는 subprocess 가 이미 직접 기록했으므로 스킵.
    for src_key, src_result in result.sources.items():
        if not src_result.success or src_result.data is None:
            continue

        if src_key == "codex":
            # codex 는 subprocess 가 이미 sources/codex.md 를 직접 기록함. 덮어쓰지 않음.
            continue

        # 나머지 소스 (brave/tavily/naver/youtube) 는 JSON 파일로 저장
        json_path = sources_dir / f"{src_key}.json"
        json_path.write_text(
            json.dumps(src_result.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    logger.info(
        "스테이징 디렉토리 finalize 완료: %s (성공소스=%d/%d)",
        staging_dir,
        sum(1 for s in result.sources.values() if s.success),
        len(result.sources),
    )


# @MX:ANCHOR create_staging_directory — fan_in >= 2 (orchestrator + tests).
# @MX:REASON SPEC-AI-REPORT-003 이후 prepare + finalize 를 순차 호출하는 얇은 wrapper 로 유지.
#            기존 호출자 (테스트 포함) 시그니처 호환성 보장.
def create_staging_directory(
    code: str,
    result: CollectionResult,
    *,
    base_dir: Path = Path("/tmp"),
) -> Path:
    """스테이징 디렉토리를 생성하고 수집 결과를 파일로 저장한다 (wrapper).

    SPEC-AI-REPORT-003 이후 `prepare_staging_directory` + `finalize_staging_directory`
    두 함수를 순차 호출하는 얇은 래퍼. 기존 호출자 시그니처 유지.

    Args:
        code: 종목 코드.
        result: CollectionResult.
        base_dir: 기본 디렉토리.

    Returns:
        생성된 staging 디렉토리 Path.

    Raises:
        ValueError: base_dir 가 /tmp 외부를 가리키는 경우.
    """
    staging_dir = prepare_staging_directory(code, base_dir=base_dir)
    finalize_staging_directory(staging_dir, code, result.stock_name, result)
    return staging_dir
