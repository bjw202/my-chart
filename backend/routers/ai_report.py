"""Router: AI 기반 종목 분석 리포트 (POST/GET /api/ai-report/{code})."""

from __future__ import annotations

import logging
import os
import re
import shutil

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from backend.schemas.ai_report import HistoryItem, HistoryResponse, ReportContentResponse
from backend.services.ai_report_service import (
    _active_analyses,
    RateLimitError,
    check_rate_limit,
    get_history,
    get_report_content,
    get_stock_name,
    stream_perplexity,
)
from backend.services.deep_research_service import (
    _active_deep_analyses,
    DeepRateLimitError,
    check_deep_rate_limit,
    stream_deep_analysis,
)
# perplexity_cache는 함수 내부에서 lazy import: backend.services.__init__ cascade
# (db_service → my_chart.db) 회피를 위해 module-level import는 사용하지 않음.

router = APIRouter()
logger = logging.getLogger(__name__)

_CODE_PATTERN = re.compile(r"^\d{6}$")


# @MX:ANCHOR generate_report — fan_in >= 2 (HTTP 클라이언트 + 테스트). 외부 HTTP 진입점.
# @MX:REASON: Invariant: guard chain ordering (code → stock → api-key/binary → duplicate → rate-limit) applies to both modes.
# Mode switches ONLY after all guards pass. 순서 변경/우회 시 과금 폭주 또는 잘못된 호출 발생.
@router.post("/ai-report/{code}")
async def generate_report(
    code: str,
    mode: str = Query("perplexity", pattern="^(perplexity|deep)$"),
) -> EventSourceResponse:
    """종목 분석 리포트를 SSE 스트리밍으로 생성.

    - **code**: 6자리 KRX 종목 코드 (예: "005930")
    - **mode**: 분석 모드. "perplexity"(기본) 또는 "deep"

    스트리밍 완료 시 리포트 자동 저장.

    SSE 이벤트 타입:
    - (기본): 마크다운 텍스트 청크
    - done: 스트리밍 완료
    - error: 오류 발생

    Returns 422 if code format is invalid or mode is not 'perplexity'/'deep'.
    Returns 404 if stock not found in registry.
    Returns 503 if required binary/key is missing.
    Returns 429 if rate limit exceeded or analysis already in progress.
    """
    # ── 공통 가드 1: 코드 형식 검증 (두 모드 모두 적용) ──
    if not _CODE_PATTERN.match(code):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_code", "detail": "종목 코드는 6자리 숫자여야 합니다."},
        )

    # ── 공통 가드 2: 종목 존재 여부 검증 (두 모드 모두 적용) ──
    stock_name = get_stock_name(code)
    if stock_name is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"종목 코드 {code}를 찾을 수 없습니다."},
        )

    # ── 모드별 분기 ──
    if mode == "deep":
        return await _handle_deep_mode(code, stock_name)
    else:
        return await _handle_perplexity_mode(code, stock_name)


async def _handle_perplexity_mode(code: str, stock_name: str) -> EventSourceResponse:
    """Perplexity 모드 처리: API 키 체크 → 중복 체크 → rate limit → 스트리밍."""
    # Perplexity API 키 체크
    if not os.environ.get("PERPLEXITY_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail={"error": "api_key_missing", "detail": "PERPLEXITY_API_KEY가 설정되지 않았습니다."},
        )

    # 중복 분석 체크 (Perplexity 전용)
    if code in _active_analyses:
        raise HTTPException(
            status_code=429,
            detail={"error": "already_running", "detail": f"{stock_name}({code}) 분석이 이미 진행 중입니다."},
        )

    # @MX:NOTE: [AUTO] v1.1.4 - 비용 폭주 방지 rate limit (일일 쿼터 + 분당 버스트)
    try:
        check_rate_limit()
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limit", "detail": str(exc)},
        ) from exc

    # Lazy import (테스트 격리용): backend.services.__init__의 cascade import 회피.
    # 테스트에서 stub이 없으면 silent skip — 캐시 누락은 기능 영향 없음 (Deep mode가 단지 재호출).
    try:
        from backend.services.perplexity_cache import put as _cache_put
    except ImportError:
        _cache_put = lambda *a, **k: None  # noqa: E731

    async def event_generator():
        """SSE 이벤트 제너레이터: 스트리밍 청크를 클라이언트에 전달.

        SPEC-AI-REPORT-002 v1.0.3: 종료 시 full markdown을 perplexity_cache에 저장하여
        같은 종목의 deep mode 호출이 재사용할 수 있도록 한다 (시나리오 C 비용 절감).
        """
        _active_analyses.add(code)
        accumulated: list[str] = []  # 캐시용 합본
        try:
            async for chunk in stream_perplexity(stock_name):
                accumulated.append(chunk)
                yield {"data": chunk}

            # 빠른 분석 종료 → perplexity 캐시에 저장 (TTL 10분, deep mode 재사용용)
            full_markdown = "".join(accumulated)
            if full_markdown:
                _cache_put(code, full_markdown)

            # 스트리밍 완료 이벤트 전송
            yield {"event": "done", "data": ""}

        except EnvironmentError as exc:
            logger.error("환경변수 오류: %s", exc)
            yield {"event": "error", "data": str(exc)}

        except Exception as exc:
            logger.error("리포트 생성 오류 [%s]: %s", code, exc)
            yield {"event": "error", "data": f"리포트 생성 중 오류가 발생했습니다: {exc}"}

        finally:
            # 완료 또는 오류 시 항상 active 상태 해제
            _active_analyses.discard(code)

    return EventSourceResponse(event_generator())


async def _handle_deep_mode(code: str, stock_name: str) -> EventSourceResponse:
    """Deep 분석 모드 처리: claude CLI 체크 → 중복 체크 → rate limit → 스트리밍."""
    # claude CLI 체크
    if shutil.which("claude") is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "claude_cli_missing", "detail": "claude CLI가 설치되지 않아 Deep 분석을 사용할 수 없습니다. Perplexity 모드를 사용하세요."},
        )

    # 중복 분석 체크 (Deep 전용)
    if code in _active_deep_analyses:
        raise HTTPException(
            status_code=429,
            detail={"error": "deep_already_running", "detail": f"{stock_name}({code}) 심층 분석이 이미 진행 중입니다."},
        )

    # Deep rate limit 체크
    try:
        check_deep_rate_limit()
    except DeepRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={"error": "deep_rate_limit", "detail": str(exc)},
        ) from exc

    return EventSourceResponse(stream_deep_analysis(code, stock_name))


@router.get("/ai-report/{code}/history", response_model=HistoryResponse)
async def get_report_history(code: str) -> HistoryResponse:
    """저장된 리포트 히스토리 조회.

    - **code**: 6자리 KRX 종목 코드

    Returns 422 if code format is invalid.
    Returns 404 if stock not found in registry.
    """
    if not _CODE_PATTERN.match(code):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_code", "detail": "종목 코드는 6자리 숫자여야 합니다."},
        )

    stock_name = get_stock_name(code)
    if stock_name is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"종목 코드 {code}를 찾을 수 없습니다."},
        )

    history = get_history(stock_name)
    items = [
        HistoryItem(
            filename=item["filename"],
            date=item["date"],
            created_at=item["created_at"],
        )
        for item in history
    ]
    return HistoryResponse(items=items)


@router.get("/ai-report/{code}/{filename}", response_model=ReportContentResponse)
async def get_saved_report(code: str, filename: str) -> ReportContentResponse:
    """저장된 리포트 내용 조회.

    - **code**: 6자리 KRX 종목 코드
    - **filename**: 조회할 파일명 (예: "2026-04-12.md")

    Returns 422 if code format is invalid.
    Returns 404 if stock or file not found.
    """
    if not _CODE_PATTERN.match(code):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_code", "detail": "종목 코드는 6자리 숫자여야 합니다."},
        )

    stock_name = get_stock_name(code)
    if stock_name is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"종목 코드 {code}를 찾을 수 없습니다."},
        )

    content = get_report_content(stock_name, filename)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "file_not_found", "detail": f"파일을 찾을 수 없습니다: {filename}"},
        )

    # 파일명에서 날짜 추출
    stem = filename.rsplit(".", 1)[0]  # 확장자 제거
    date_part = stem.split("_")[0] if "_" in stem else stem

    return ReportContentResponse(
        content=content,
        filename=filename,
        date=date_part,
    )
