"""Router: AI 기반 종목 분석 리포트 (POST/GET /api/ai-report/{code})."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from sse_starlette.sse import EventSourceResponse

from backend.schemas.ai_report import HistoryItem, HistoryResponse, ReportContentResponse
from backend.services.ai_report_service import (
    _active_analyses,
    RateLimitError,
    check_rate_limit,
    get_goose_report_path,
    get_history,
    get_report_content,
    get_stock_name,
    stream_codex_fast,
)
from backend.services.goose_job_service import get_service as get_goose_service

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
) -> Response:
    """종목 분석 리포트 생성. fast는 SSE 스트리밍, deep은 goose 작업 시작(SPEC-AI-REPORT-004).

    - **code**: 6자리 KRX 종목 코드 (예: "005930")
    - **mode**: 분석 모드. "fast"(기본, Codex 기반) 또는 "deep"(goose 작업) 또는 "perplexity"(deprecated alias → fast).

    fast: 스트리밍 완료 시 리포트 자동 저장.
    deep: 202 {job_id}(새 작업 또는 무결성 실패 작업) / 200 {job_id}(같은 종목 실행 중) /
          429 goose_busy | goose_rate_limit. 진행은 GET /ai-report/jobs/{job_id}/events로 구독.

    SSE 이벤트 타입:
    - phase: 단계 진행 알림 (Fast Mode heartbeat 포함)
    - (기본): 마크다운 텍스트 청크
    - done: 스트리밍 완료
    - error: 오류 발생

    Returns 422 if code format is invalid or mode is not 'fast'/'deep'/'perplexity'.
    Returns 404 if stock not found in registry.
    Returns 503 if required binary is missing.
    Returns 429 if rate limit exceeded or analysis already in progress (deep: goose_busy / goose_rate_limit).
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


# @MX:NOTE: SPEC-AI-REPORT-004 — mode=deep는 goose 작업을 시작한다(옛 Deep 파이프라인은 M7에서 삭제).
#           라우터는 1~3단계(코드·종목·실행 파일)만 판정하고 4~8단계는 service.start()가 잠금 안에서 판정한다
#           (design §8). 여기서 4~8단계를 미리 판정하면 동시 요청이 모두 통과한다.
async def _handle_deep_mode(code: str, stock_name: str) -> Response:
    """goose 작업 시작: 202 {job_id} / 200 {기존 job_id} / 429 goose_busy | goose_rate_limit."""
    # 3. claude 실행 파일
    if shutil.which("claude") is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "claude_cli_missing", "detail": "claude CLI가 설치되지 않아 Goose 분석을 사용할 수 없습니다. Fast 모드를 사용하세요."},
        )

    outcome = await get_goose_service().start(code, stock_name)
    if outcome.kind == "existing":
        return JSONResponse(status_code=200, content={"job_id": outcome.job.job_id})
    if outcome.kind == "busy":
        raise HTTPException(
            status_code=429,
            detail={"error": "goose_busy", "detail": f"{outcome.job.stock_name} 분석이 진행 중입니다"},
        )
    if outcome.kind == "rate_limit":
        quota = get_goose_service().limiter.quota
        raise HTTPException(
            status_code=429,
            detail={"error": "goose_rate_limit", "detail": f"Goose 분석 일일 한도({quota}회)를 모두 사용했습니다."},
        )
    # started 또는 integrity(작업은 이미 error/integrity — 프론트는 이벤트 구독으로 받는다)
    return JSONResponse(status_code=202, content={"job_id": outcome.job.job_id})


# @MX:NOTE: 이 경로는 `/ai-report/{code}/{filename}`과 모양이 같다. 반드시 그보다 먼저 등록한다
#           (늦으면 `goose`가 종목 코드로 해석돼 422 — AC-021).
@router.get("/ai-report/goose/active")
async def get_goose_active() -> dict | None:
    """실행 중 goose 작업 {job_id, code, stock_name, status} 또는 null (셀 폴링 전용, design §4.5)."""
    return get_goose_service().active()


@router.get("/ai-report/jobs/{job_id}/events")
async def stream_goose_events(
    job_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> EventSourceResponse:
    """작업 이벤트 SSE: 지난 이벤트 재생 후 실시간 전달, 종료 이벤트 뒤 닫힘 (design §4.4)."""
    service = get_goose_service()
    if service.get(job_id) is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "job_not_found", "detail": f"작업을 찾을 수 없습니다: {job_id}"},
        )
    try:
        after = max(int(last_event_id), 0) if last_event_id else 0
    except ValueError:
        after = 0

    async def event_generator():
        try:
            async for event in service.subscribe(job_id, after=after):
                yield {
                    "id": str(event.seq),
                    "event": event.type,
                    "data": json.dumps(event.data, ensure_ascii=False),
                }
        except KeyError:  # 구독 직전 보관 한도로 정리된 작업
            return

    return EventSourceResponse(event_generator())


@router.post("/ai-report/jobs/{job_id}/cancel")
async def cancel_goose_job(job_id: str) -> dict:
    """실행 중이면 취소(cancelled), 끝난 작업은 현재 상태 그대로, 없는 작업은 404 (REQ-011)."""
    job = await get_goose_service().cancel(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "job_not_found", "detail": f"작업을 찾을 수 없습니다: {job_id}"},
        )
    return {"job_id": job.job_id, "status": job.status, "error_kind": job.error_kind}


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
            kind=item.get("kind", "markdown"),
            run=item.get("run"),
            delivery_status=item.get("delivery_status"),
            interrupted=item.get("interrupted", False),
        )
        for item in history
    ]
    return HistoryResponse(items=items)


# @MX:NOTE: goose 리포트는 모델이 만든 HTML이다. 스크립트·동일 출처를 허용하지 않는 CSP sandbox로만
#           서빙한다(REQ-AIR4-015, design §5.4). 프론트 iframe sandbox(REQ-018)와 이중 방어.
_GOOSE_REPORT_HEADERS = {
    "Content-Security-Policy": (
        "sandbox allow-popups allow-popups-to-escape-sandbox allow-downloads; "
        "default-src 'none'; style-src 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src https://cdn.jsdelivr.net https://fonts.gstatic.com; img-src data:"
    ),
    "X-Content-Type-Options": "nosniff",
}


@router.get("/ai-report/{code}/goose/{run}/report.html")
async def get_goose_report(code: str, run: str) -> Response:
    """보관된 goose 리포트 HTML (CSP sandbox). 코드·종목·run·경로 검증 실패는 모두 404 (design §5.4)."""
    not_found = HTTPException(
        status_code=404,
        detail={"error": "not_found", "detail": "리포트를 찾을 수 없습니다."},
    )
    if not _CODE_PATTERN.match(code):
        raise not_found
    stock_name = get_stock_name(code)
    if stock_name is None:
        raise not_found
    path = get_goose_report_path(stock_name, run)
    if path is None:
        raise not_found
    return Response(
        content=path.read_bytes(),
        media_type="text/html; charset=utf-8",
        headers=_GOOSE_REPORT_HEADERS,
    )


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
