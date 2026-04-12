"""FastAPI application entry point for the KR Stock Screener web service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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

    # v1.1.5: AI Report 프롬프트 템플릿 검증 (fail-fast)
    # 파일 부재/플레이스홀더 부재 시 서버 시작 즉시 중단 → 첫 요청 500 회피
    try:
        from backend.services.ai_report_service import _load_prompt_template

        template = _load_prompt_template()
        logger.info("AI Report 프롬프트 로드 완료 (%d chars)", len(template))
    except (FileNotFoundError, ValueError) as e:
        logger.error("AI Report 프롬프트 검증 실패: %s", e)
        raise

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


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe for the web service."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # Single worker: prevents registry singleton duplication across processes
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, workers=1, reload=False)
