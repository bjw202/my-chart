"""Meta service: rebuild the stock_meta screening snapshot table.

Joins daily DB (latest date) + weekly DB (latest date + RS) + sectormap + pykrx market cap
into a single denormalized table for sub-100ms SQL filtering.
"""

from __future__ import annotations

import datetime
import logging
import math
import sqlite3

from my_chart.config import REFERENCE_STOCK
from my_chart.registry import get_sector_registry
from backend.deps import get_db_conn

logger = logging.getLogger(__name__)

_STOCK_META_DDL = """
CREATE TABLE IF NOT EXISTS stock_meta (
    code TEXT PRIMARY KEY,
    name TEXT,
    market TEXT,
    market_cap INTEGER,
    sector_major TEXT,
    sector_minor TEXT,
    product TEXT,
    close REAL,
    change_1d REAL,
    ema10 REAL,
    ema20 REAL,
    sma50 REAL,
    sma100 REAL,
    sma200 REAL,
    high52w REAL,
    chg_1w REAL,
    chg_1m REAL,
    chg_3m REAL,
    rs_12m REAL,
    sma10_w REAL,
    sma20_w REAL,
    sma40_w REAL,
    last_updated TEXT
)
"""

_INDEX_DDLS = [
    "CREATE INDEX IF NOT EXISTS idx_meta_sector ON stock_meta(sector_major)",
    "CREATE INDEX IF NOT EXISTS idx_meta_market ON stock_meta(market)",
    "CREATE INDEX IF NOT EXISTS idx_meta_cap ON stock_meta(market_cap DESC)",
]


def _business_days_since(target: datetime.date) -> int:
    """Count business (Mon–Fri) days between target and today."""
    today = datetime.date.today()
    if target >= today:
        return 0
    total = 0
    current = target
    while current < today:
        current += datetime.timedelta(days=1)
        if current.weekday() < 5:  # Mon=0 … Fri=4
            total += 1
    return total


def rebuild_stock_meta(daily_db_path: str, weekly_db_path: str) -> None:
    """Rebuild stock_meta from latest daily + weekly + RS + sectormap + pykrx data.

    Stocks missing from daily DB are excluded from stock_meta.
    NULL is stored for pykrx market cap when the fetch fails.
    """
    conn = get_db_conn(daily_db_path)
    try:
        _rebuild(conn, weekly_db_path)
    finally:
        try:
            conn.execute("DETACH DATABASE weekly")
        except sqlite3.OperationalError:
            pass
        conn.close()


def _rebuild(conn: sqlite3.Connection, weekly_db_path: str) -> None:
    # Ensure stock_meta table exists
    conn.execute(_STOCK_META_DDL)
    for ddl in _INDEX_DDLS:
        conn.execute(ddl)

    # --- Latest daily date ---
    row = conn.execute(
        "SELECT MAX(Date) FROM stock_prices WHERE Name = ?", (REFERENCE_STOCK,)
    ).fetchone()
    latest_daily_date: str | None = row[0] if row else None

    if not latest_daily_date:
        logger.warning("No daily data found for reference stock; aborting stock_meta rebuild")
        return

    # Staleness guard: warn if DB data is older than 5 business days
    target_date = datetime.date.fromisoformat(latest_daily_date)
    stale_days = _business_days_since(target_date)
    if stale_days > 5:
        logger.warning(
            "Daily DB latest date %s is %d business days old (stale)",
            latest_daily_date,
            stale_days,
        )
        # Continue building stock_meta with whatever data we have

    # --- Load daily snapshot ---
    daily_rows = conn.execute(
        """SELECT Name, Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W
           FROM stock_prices
           WHERE Date = ?""",
        (latest_daily_date,),
    ).fetchall()
    # daily_by_name: Name -> (Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W)
    daily_by_name: dict[str, tuple] = {r[0]: r[1:] for r in daily_rows}

    # --- Attach weekly DB and load weekly snapshot ---
    conn.execute(f"ATTACH DATABASE '{weekly_db_path}' AS weekly")

    weekly_date_row = conn.execute(
        "SELECT MAX(Date) FROM weekly.stock_prices WHERE Name = ?", (REFERENCE_STOCK,)
    ).fetchone()
    latest_weekly_date: str | None = weekly_date_row[0] if weekly_date_row else None

    weekly_by_name: dict[str, tuple] = {}
    rs_by_name: dict[str, float | None] = {}

    if latest_weekly_date:
        w_rows = conn.execute(
            """SELECT Name, CHG_1W, CHG_1M, CHG_3M, SMA10, SMA20, SMA40
               FROM weekly.stock_prices
               WHERE Date = ?""",
            (latest_weekly_date,),
        ).fetchall()
        # weekly_by_name: Name -> (CHG_1W, CHG_1M, CHG_3M, SMA10, SMA20, SMA40)
        weekly_by_name = {r[0]: r[1:] for r in w_rows}

        rs_rows = conn.execute(
            "SELECT Name, RS_12M_Rating FROM weekly.relative_strength WHERE Date = ?",
            (latest_weekly_date,),
        ).fetchall()
        rs_by_name = {r[0]: r[1] for r in rs_rows}

    # --- Load sectormap ---
    df_sector = get_sector_registry()
    # sector_by_name: Name -> {code, market, sector_major, sector_minor, product}
    sector_by_name: dict[str, dict] = {}
    for _, srow in df_sector.iterrows():
        sector_by_name[str(srow["Name"])] = {
            "code": str(srow["Code"]).zfill(6),
            "market": str(srow["Market"]),
            "sector_major": srow.get("산업명(대)"),
            "sector_minor": srow.get("산업명(중)"),
            "product": srow.get("주요제품"),
        }

    # --- 시가총액 계산: basic_data.xlsx의 상장주식수 × 종가 ---
    market_cap_by_code: dict[str, int | None] = {}
    try:
        import pandas as pd
        from pathlib import Path

        basic_data_path = Path(__file__).resolve().parents[2] / "Input" / "basic_data.xlsx"
        if basic_data_path.exists():
            bd_df = pd.read_excel(
                basic_data_path,
                usecols=["단축코드", "상장주식수"],
                dtype={"단축코드": str},
            )
            shares_by_code: dict[str, int] = {}
            for _, brow in bd_df.iterrows():
                raw_code = brow.get("단축코드")
                # 결측치 방어: 코드나 상장주식수가 NaN/None이면 건너뜀
                if raw_code is None or (isinstance(raw_code, float) and math.isnan(raw_code)):
                    continue
                code = str(raw_code).zfill(6)
                shares = brow.get("상장주식수")
                if shares is None or (isinstance(shares, float) and math.isnan(shares)):
                    continue
                try:
                    shares_by_code[code] = int(shares)
                except (ValueError, TypeError):
                    continue

            # 종가(daily_by_name) × 상장주식수 = 시가총액(원)
            for name, sector_info in sector_by_name.items():
                code = sector_info["code"]
                if code in shares_by_code and name in daily_by_name:
                    close_price = daily_by_name[name][0]  # Close
                    if close_price and close_price > 0:
                        cap_won = int(close_price * shares_by_code[code])
                        market_cap_by_code[code] = cap_won
            logger.info(
                "basic_data.xlsx에서 %d개 종목 시가총액 계산 완료",
                len(market_cap_by_code),
            )
        else:
            logger.warning("Input/basic_data.xlsx 파일 없음 — 시가총액 미반영")
    except Exception as exc:
        logger.warning("basic_data.xlsx 시가총액 계산 실패 (%s)", exc)

    # --- Build and insert rows ---
    now_str = datetime.datetime.now().isoformat()
    rows_to_insert: list[tuple] = []

    for name, sector_info in sector_by_name.items():
        if name not in daily_by_name:
            # No daily data → skip (delisted, newly listed, or missing)
            continue

        d = daily_by_name[name]   # (Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W)
        w = weekly_by_name.get(name)  # (CHG_1W, CHG_1M, CHG_3M, SMA10, SMA20, SMA40) or None
        code = sector_info["code"]

        rows_to_insert.append((
            code,
            name,
            sector_info["market"],
            market_cap_by_code.get(code),        # nullable
            sector_info["sector_major"],
            sector_info["sector_minor"],
            sector_info["product"],
            d[0],   # close
            d[1],   # change_1d
            d[2],   # ema10
            d[3],   # ema20
            d[4],   # sma50
            d[5],   # sma100
            d[6],   # sma200
            d[7],   # high52w
            w[0] if w else None,  # chg_1w
            w[1] if w else None,  # chg_1m
            w[2] if w else None,  # chg_3m
            rs_by_name.get(name),             # rs_12m
            w[3] if w else None,  # sma10_w
            w[4] if w else None,  # sma20_w
            w[5] if w else None,  # sma40_w
            now_str,
        ))

    conn.execute("DELETE FROM stock_meta")
    conn.executemany(
        """INSERT OR REPLACE INTO stock_meta
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows_to_insert,
    )
    conn.commit()
    logger.info("stock_meta rebuilt: %d stocks inserted", len(rows_to_insert))
