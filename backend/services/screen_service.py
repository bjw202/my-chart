"""Screen service: parameterized SQL filter against the stock_meta table."""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict

from backend.deps import get_db_conn
from backend.schemas.screen import (
    ScreenRequest,
    ScreenResponse,
    SectorGroup,
    StockItem,
)

logger = logging.getLogger(__name__)

# Maps Pydantic Literal indicator names to actual stock_meta column names.
# Column names are hardcoded here (not from user input) to prevent SQL injection.
# Open/High/Low map to close since stock_meta uses only close for daily price.
_INDICATOR_COLUMN: dict[str, str] = {
    "Close": "close",
    "Open": "close",
    "High": "close",
    "Low": "close",
    "EMA10": "ema10",
    "EMA20": "ema20",
    "SMA50": "sma50",
    "SMA100": "sma100",
    "SMA200": "sma200",
}

_OPERATOR_SQL: dict[str, str] = {
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}


# @MX:NOTE: [AUTO] research.md §2.1의 8조건을 SQL WHERE 식으로 직역한 상수 빌더.
# @MX:NOTE: 파라미터 바인딩이 필요 없는 순수 상수 식이므로 SQL injection 표면은 증가하지 않음.
def _build_minervini_where() -> str:
    """Minervini Trend Template 8조건 AND 결합 WHERE 절을 반환한다 (REQ-MIN-005).

    각 조건은 stock_meta 컬럼 기준:
    T1: close > sma150 AND close > sma200
    T2: sma150 > sma200
    T3: sma200 > sma200_20d_ago
    T4: sma50 > sma150 AND sma50 > sma200
    T5: close > sma50
    T6: close >= low52w * 1.25
    T7: close >= high52w * 0.75 AND close <= high52w
    T8: rs_12m >= 70
    """
    return (
        "("
        "close > sma150 AND close > sma200"              # T1
        " AND sma150 > sma200"                           # T2
        " AND sma200 > sma200_20d_ago"                   # T3
        " AND sma50 > sma150 AND sma50 > sma200"         # T4
        " AND close > sma50"                             # T5
        " AND close >= low52w * 1.25"                    # T6
        " AND close >= high52w * 0.75 AND close <= high52w"  # T7
        " AND rs_12m >= 70"                              # T8
        ")"
    )


def _minervini_columns_available(conn: sqlite3.Connection) -> bool:
    """stock_meta에 Minervini 필수 컬럼이 모두 존재하는지 확인한다 (REQ-MIN-007).

    컬럼 존재 여부를 PRAGMA로 선검사하여 불필요한 OperationalError를 방지한다.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(stock_meta)").fetchall()}
    required = {"sma150", "low52w", "sma200_20d_ago"}
    return required.issubset(existing)


def _build_where(req: ScreenRequest) -> tuple[str, list[object]]:
    """Build a parameterized SQL WHERE clause from ScreenRequest.

    Returns (where_sql, params) where params are bound positionally.
    Column names are ONLY sourced from _INDICATOR_COLUMN (server-side whitelist),
    never from user input directly.
    """
    conditions: list[str] = []
    params: list[object] = []

    if req.market_cap_min is not None:
        # 프론트엔드는 억원 단위로 전송, DB는 원 단위로 저장
        conditions.append("market_cap >= ?")
        params.append(int(req.market_cap_min) * 100_000_000)

    if req.chg_1d_min is not None:
        conditions.append("change_1d >= ?")
        params.append(req.chg_1d_min)

    # chg_1w/1m/3m are stored as decimals (0.30 = 30%) from pct_change(),
    # while the UI sends percentage values (30 = 30%), so divide by 100.
    if req.chg_1w_min is not None:
        conditions.append("chg_1w >= ?")
        params.append(req.chg_1w_min / 100)

    if req.chg_1m_min is not None:
        conditions.append("chg_1m >= ?")
        params.append(req.chg_1m_min / 100)

    if req.chg_3m_min is not None:
        conditions.append("chg_3m >= ?")
        params.append(req.chg_3m_min / 100)

    if req.rs_min is not None:
        conditions.append("rs_12m >= ?")
        params.append(req.rs_min)

    if req.markets:
        placeholders = ",".join("?" * len(req.markets))
        conditions.append(f"market IN ({placeholders})")
        params.extend(req.markets)

    if req.sectors:
        placeholders = ",".join("?" * len(req.sectors))
        conditions.append(f"sector_major IN ({placeholders})")
        params.extend(req.sectors)

    if req.codes:
        placeholders = ",".join("?" * len(req.codes))
        conditions.append(f"code IN ({placeholders})")
        params.extend(req.codes)

    # Pattern conditions: column names sourced exclusively from _INDICATOR_COLUMN
    pattern_clauses: list[str] = []
    for pat in req.patterns:
        col_a = _INDICATOR_COLUMN[pat.indicator_a]  # validated by Literal + dict lookup
        col_b = _INDICATOR_COLUMN[pat.indicator_b]
        op = _OPERATOR_SQL[pat.operator]             # validated by Literal + dict lookup
        pattern_clauses.append(f"{col_a} {op} {col_b} * ?")
        params.append(pat.multiplier)

    if pattern_clauses:
        joiner = " AND " if req.pattern_logic == "AND" else " OR "
        conditions.append(f"({joiner.join(pattern_clauses)})")

    where_sql = " AND ".join(conditions) if conditions else "1=1"
    return where_sql, params


# @MX:ANCHOR: [AUTO] 사용자-facing 스크리닝 엔트리포인트 (fan_in >= 3)
# @MX:REASON: router, 테스트, 향후 preset service가 모두 이 함수를 직접 호출. 변경 시 광범위한 영향 발생
def screen_stocks(req: ScreenRequest, daily_db_path: str) -> ScreenResponse:
    """Execute the screen filter against stock_meta and return sector-grouped results.

    Returns ScreenResponse with total=0 and empty sectors when nothing matches.
    Raises sqlite3.OperationalError (-> caught by router as 503) if stock_meta is missing.

    REQ-MIN-005/006: minervini_trend_template=True 시 8조건 strict gate 적용 + score=8 반환.
    REQ-MIN-007: 신규 컬럼 누락 시 HTTP 200 + empty + WARN log.
    """
    use_minervini = req.minervini_trend_template is True

    where_sql, params = _build_where(req)

    conn = get_db_conn(daily_db_path)
    try:
        # REQ-MIN-007: Minervini 플래그 ON이면 컬럼 존재 여부를 선검사
        if use_minervini:
            if not _minervini_columns_available(conn):
                logger.warning(
                    "[minervini] required columns missing; "
                    "delete DB files and re-run db-update pipeline"
                )
                return ScreenResponse(total=0, sectors=[])
            # 8조건 WHERE 추가
            minervini_clause = _build_minervini_where()
            if where_sql == "1=1":
                where_sql = minervini_clause
            else:
                where_sql = f"{where_sql} AND {minervini_clause}"

        # trend_template_score: minervini=True면 상수 8, 아니면 NULL
        score_expr = "CASE WHEN 1=1 THEN 8 ELSE NULL END" if use_minervini else "NULL"

        query = f"""
            SELECT code, name, market, market_cap, sector_major, sector_minor, product,
                   close, change_1d, rs_12m, ema10, ema20, sma50, sma100, sma200,
                   {score_expr} AS trend_template_score
            FROM stock_meta
            WHERE {where_sql}
            ORDER BY sector_major, sector_minor, market_cap DESC
        """

        try:
            rows = conn.execute(query, params).fetchall()
        except sqlite3.OperationalError:
            # 백업 방어: PRAGMA 검사를 통과했더라도 OperationalError 발생 시 빈 응답
            if use_minervini:
                logger.warning(
                    "[minervini] required columns missing; "
                    "delete DB files and re-run db-update pipeline"
                )
                return ScreenResponse(total=0, sectors=[])
            raise
    finally:
        conn.close()

    # Group by "sector_major > sector_minor"
    sector_map: dict[str, list[StockItem]] = defaultdict(list)
    for row in rows:
        (code, name, market, market_cap, sector_major, sector_minor, product,
         close, chg1d, rs12m, e10, e20, s50, s100, s200, score) = row
        item = StockItem(
            code=code,
            name=name,
            market=market or "",
            market_cap=market_cap,
            sector_major=sector_major,
            sector_minor=sector_minor,
            product=product,
            close=close,
            change_1d=chg1d,
            rs_12m=rs12m,
            ema10=e10,
            ema20=e20,
            sma50=s50,
            sma100=s100,
            sma200=s200,
            trend_template_score=score,
        )
        major = sector_major or "기타"
        minor = sector_minor or ""
        bucket = f"{major} > {minor}" if minor else major
        sector_map[bucket].append(item)

    sectors: list[SectorGroup] = [
        SectorGroup(sector_name=sector, stock_count=len(stocks), stocks=stocks)
        for sector, stocks in sorted(sector_map.items())
    ]

    return ScreenResponse(total=len(rows), sectors=sectors)
