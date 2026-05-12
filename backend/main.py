"""FastAPI application entry point for the KR Stock Screener web service."""

from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# SPEC-AI-REPORT-002 v1.0.5: 애플리케이션 INFO 로그를 uvicorn 출력에 노출.
# uvicorn root logger는 기본적으로 uvicorn.* 네임스페이스만 INFO로 방출하므로,
# basicConfig로 root logger에 handler를 추가해 backend.services.* 로그도 표시한다.
# 진행 상태 패널의 per-source 이벤트 흐름을 운영 중 진단할 수 있게 한다.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from my_chart.config import initialize
from my_chart.registry import get_sector_registry, get_stock_registry
from backend.routers.ai_report import router as ai_report_router
from backend.routers.analysis import router as analysis_router
from backend.routers.chart import router as chart_router
from backend.routers.db import router as db_router
from backend.routers.market import router as market_router
from backend.routers.screen import router as screen_router
from backend.routers.sectors import router as sectors_router
from backend.routers.stage import router as stage_router
from backend.routers.stocks import stocks_router
from backend.routers.themes import router as themes_router
from backend.services.deep_research_service import (
    _cleanup_stale_staging_dirs,
    _load_synthesis_prompt,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Pre-initialize expensive singletons before accepting requests.

    get_stock_registry() and get_sector_registry() load sectormap.xlsx
    (~2,570 stocks). Pre-initializing here prevents race conditions when
    concurrent requests hit the lazy-loaded globals simultaneously.
    """
    logger.info("Initializing KRX session and registries...")
    initialize()
    get_stock_registry()
    get_sector_registry()
    logger.info("Registries loaded. Server ready.")

    # SPEC-AI-REPORT-003: Codex 프롬프트 템플릿 검증 (fail-fast)
    # 파일 부재/플레이스홀더 부재 시 서버 시작 즉시 중단 → 첫 요청 500 회피
    try:
        from backend.services.codex_cli_runner import load_codex_prompt

        template = load_codex_prompt(code="000000", stock_name="검증용")
        logger.info("Codex 프롬프트 로드 완료 (%d chars)", len(template))
    except (FileNotFoundError, ValueError) as e:
        logger.error("Codex 프롬프트 검증 실패: %s", e)
        raise

    # @MX:NOTE Fast/Deep 양모드 lifespan block — codex binary required, claude binary required for Deep.
    # SPEC-AI-REPORT-003 NFR-001: codex 바이너리 부재 시 Fast Mode 비활성 (경고), claude 없으면 Deep 비활성.
    if shutil.which("codex") is None:
        logger.warning("codex CLI 미설치: Fast Mode 비활성화. `codex login` 이후 사용 가능.")
    if shutil.which("claude") is None:
        logger.warning("claude CLI 미설치: Deep 분석 모드 비활성화. Fast 모드는 codex 설치 시 정상 운영.")

    # Deep 합성 프롬프트 fail-fast (FR-010): 파일 없으면 서버 시작 즉시 중단
    try:
        _load_synthesis_prompt()
        logger.info("Deep Research 합성 프롬프트 로드 완료")
    except (FileNotFoundError, ValueError) as e:
        logger.error("합성 프롬프트 검증 실패: %s", e)
        raise

    # /tmp 스테이징 디렉토리 정리 (FR-013): 7일 초과 디렉토리 삭제 (best-effort)
    try:
        deleted = _cleanup_stale_staging_dirs(max_age_days=7)
        if deleted > 0:
            logger.info("오래된 staging 디렉토리 %d개 정리 완료", deleted)
    except Exception as e:  # noqa: BLE001
        logger.warning("staging 디렉토리 정리 실패 (무시): %s", e)

    yield
    logger.info("Server shutting down.")


app = FastAPI(
    title="KR Stock Screener",
    version="0.1.0",
    description="Korean stock screener web service backed by my_chart",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_report_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(chart_router, prefix="/api")
app.include_router(db_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(screen_router, prefix="/api")
app.include_router(sectors_router, prefix="/api")
app.include_router(stage_router, prefix="/api")
app.include_router(themes_router, prefix="/api")
app.include_router(stocks_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe for the web service."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # Single worker: prevents registry singleton duplication across processes
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, workers=1, reload=False)
