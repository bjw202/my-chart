"""Router: AI 기반 종목 분석 리포트 (POST/GET /api/ai-report/{code})."""

from __future__ import annotations

import logging
import os
import re

from fastapi import APIRouter, HTTPException
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

router = APIRouter()
logger = logging.getLogger(__name__)

_CODE_PATTERN = re.compile(r"^\d{6}$")


# @MX:ANCHOR: [AUTO] v1.1.4 - AI 리포트 생성 공개 엔드포인트. 외부 HTTP 진입점.
# @MX:REASON: 순서 있는 가드 체인(코드 형식 → 종목 존재 → API 키 → 중복 → rate limit)이
# 비용 통제와 보안의 기본. 순서 변경/우회 시 Perplexity 과금 폭주 또는 잘못된 호출 발생.
@router.post("/ai-report/{code}")
async def generate_report(code: str) -> EventSourceResponse:
    """Perplexity API를 통해 종목 분석 리포트를 SSE 스트리밍으로 생성.

    - **code**: 6자리 KRX 종목 코드 (예: "005930")

    스트리밍 완료 시 리포트 자동 저장.

    SSE 이벤트 타입:
    - (기본): 마크다운 텍스트 청크
    - done: 스트리밍 완료
    - error: 오류 발생

    Returns 422 if code format is invalid.
    Returns 404 if stock not found in registry.
    Returns 503 if PERPLEXITY_API_KEY is not set.
    Returns 429 if same stock is already being analyzed.
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

    if not os.environ.get("PERPLEXITY_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail={"error": "api_key_missing", "detail": "PERPLEXITY_API_KEY가 설정되지 않았습니다."},
        )

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

    async def event_generator():
        """SSE 이벤트 제너레이터: 스트리밍 청크를 클라이언트에 전달."""
        _active_analyses.add(code)
        try:
            async for chunk in stream_perplexity(stock_name):
                yield {"data": chunk}

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
