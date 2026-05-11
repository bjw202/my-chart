"""라우터: GET /api/stocks/master — 클라이언트 검색용 전체 종목 목록.

REQ-DATA-001: ETag + Cache-Control headers
REQ-DATA-003: stock_meta 부재/빈 테이블 → 503 stock_meta_not_ready
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from backend.deps import DAILY_DB_PATH
from backend.services.stocks_master_service import list_stock_master

stocks_router = APIRouter(prefix="/api/stocks", tags=["stocks"])

_KST = ZoneInfo("Asia/Seoul")


class StockMasterItem(BaseModel):
    code: str
    name: str
    market: str


class StockMasterResponse(BaseModel):
    stocks: list[StockMasterItem]
    generated_at: str  # ISO-8601 KST


@stocks_router.get("/master", response_model=StockMasterResponse)
async def get_stock_master(response: Response) -> StockMasterResponse:
    """stock_meta 전체 종목 목록을 반환한다.

    - ETag: MAX(stock_meta.last_updated) 기반 (REQ-DATA-001)
    - Cache-Control: max-age=300 (NFR-PERF-004)
    - 503: stock_meta 부재 또는 빈 테이블 (REQ-DATA-003)
    """
    stocks_raw, max_updated = list_stock_master(DAILY_DB_PATH)

    if not stocks_raw:
        raise HTTPException(status_code=503, detail="stock_meta_not_ready")

    if max_updated:
        response.headers["ETag"] = f'"{max_updated}"'
    response.headers["Cache-Control"] = "max-age=300"

    generated_at = datetime.now(_KST).isoformat()

    return StockMasterResponse(
        stocks=[StockMasterItem(**s) for s in stocks_raw],
        generated_at=generated_at,
    )
