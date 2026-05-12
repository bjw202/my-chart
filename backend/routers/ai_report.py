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
    stream_codex_fast,
)
from backend.services.deep_research_service import (
    _active_deep_analyses,
    DeepRateLimitError,
    check_deep_rate_limit,
    stream_deep_analysis,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_CODE_PATTERN = re.compile(r"^\d{6}$")


# @MX:ANCHOR generate_report — fan_in >= 2 (HTTP 클라이언트 + 테스트). 외부 HTTP 진입점.
# @MX:REASON: Invariant: guard chain ordering (code → stock → binary → duplicate → rate-limit) applies to both modes.
#             SPEC-AI-REPORT-003: mode=fast (Codex) + mode=deep. "perplexity" 는 backward-compat 알리아스 → fast.
@router.post("/ai-report/{code}")
async def generate_report(
    code: str,
    mode: str = Query("fast", pattern="^(fast|deep|perplexity)$"),
) -> EventSourceResponse:
    """종목 분석 리포트를 SSE 스트리밍으로 생성.

    - **code**: 6자리 KRX 종목 코드 (예: "005930")
    - **mode**: 분석 모드. "fast"(기본, Codex 기반) 또는 "deep" 또는 "perplexity"(deprecated alias → fast).

    스트리밍 완료 시 리포트 자동 저장.

    SSE 이벤트 타입:
    - phase: 단계 진행 알림 (Fast Mode heartbeat 포함)
    - (기본): 마크다운 텍스트 청크
    - done: 스트리밍 완료
    - error: 오류 발생

    Returns 422 if code format is invalid or mode is not 'fast'/'deep'/'perplexity'.
    Returns 404 if stock not found in registry.
    Returns 503 if required binary is missing.
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

    # ── 모드별 분기 (SPEC-AI-REPORT-003: perplexity → fast 알리아스) ──
    if mode == "deep":
        return await _handle_deep_mode(code, stock_name)
    # mode == "fast" 또는 "perplexity" (deprecated)
    if mode == "perplexity":
        logger.info(
            "mode='perplexity' 는 SPEC-AI-REPORT-003 에서 deprecated. 'fast' 로 라우팅됨 [code=%s]",
            code,
        )
    return await _handle_fast_mode(code, stock_name)


async def _handle_fast_mode(code: str, stock_name: str) -> EventSourceResponse:
    """Fast Mode 처리 (SPEC-AI-REPORT-003): codex CLI 체크 → 중복 체크 → rate limit → 스트리밍."""
    # codex CLI 체크 (SPEC-AI-REPORT-003 NFR-001)
    if shutil.which("codex") is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "codex_cli_missing",
                "detail": (
                    "codex CLI가 설치되지 않아 Fast 분석을 사용할 수 없습니다. "
                    "`codex login` 으로 인증하고 PATH 에 바이너리를 추가하세요."
                ),
            },
        )

    # 중복 분석 체크 (Fast Mode 전용)
    if code in _active_analyses:
        raise HTTPException(
            status_code=429,
            detail={"error": "already_running", "detail": f"{stock_name}({code}) 분석이 이미 진행 중입니다."},
        )

    # @MX:NOTE: ChatGPT 구독 쿼터 보호 rate limit (SPEC-AI-REPORT-003 NFR-002).
    try:
        check_rate_limit()
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limit", "detail": str(exc)},
        ) from exc

    async def event_generator():
        """SSE 이벤트 제너레이터: stream_codex_fast 이벤트를 클라이언트에 전달."""
        _active_analyses.add(code)
        try:
            async for event in stream_codex_fast(stock_name, code):
                yield event
        except Exception as exc:  # noqa: BLE001
            logger.error("리포트 생성 오류 [%s]: %s", code, exc)
            yield {"event": "error", "data": f"리포트 생성 중 오류가 발생했습니다: {exc}"}
        finally:
            _active_analyses.discard(code)

    return EventSourceResponse(event_generator())


async def _handle_deep_mode(code: str, stock_name: str) -> EventSourceResponse:
    """Deep 분석 모드 처리: claude CLI 체크 → 중복 체크 → rate limit → 스트리밍."""
    # claude CLI 체크
    if shutil.which("claude") is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "claude_cli_missing", "detail": "claude CLI가 설치되지 않아 Deep 분석을 사용할 수 없습니다. Fast 모드를 사용하세요."},
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
