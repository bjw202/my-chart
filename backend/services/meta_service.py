"""Meta service: rebuild the stock_meta screening snapshot table.

Joins daily DB (latest date) + weekly DB (latest date + RS) + sectormap + pykrx market cap
into a single denormalized table for sub-100ms SQL filtering.
"""

from __future__ import annotations

import datetime
import logging
import math
import sqlite3

from my_chart.analysis.weekly_grid import _get_latest_valid_date
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
    last_updated TEXT,
    sma150 REAL,
    low52w REAL,
    sma200_20d_ago REAL,
    sma5 REAL
)
"""

# REQ-MIN-008 + SPEC-SMA5-FILTER-001 follow-up (2026-05-26):
# stock_meta 레거시 DB 마이그레이션 대상 컬럼. _STOCK_META_DDL은 CREATE TABLE IF NOT EXISTS이므로
# 기존 테이블은 신규 컬럼이 자동 추가되지 않는다. 멱등 ALTER 루프로 누락된 컬럼만 추가한다.
# sma5는 SPEC-SMA5-FILTER-001 ship 후 라이브 검증에서 'no such column: sma5' 오류로
# SMA5 패턴 필터가 0건 반환된 사례를 반영해 추가됨 (daily.py SMA5 ALTER 패턴과 대칭).
_MINERVINI_META_COLS = ("sma150", "low52w", "sma200_20d_ago", "sma5")

_INDEX_DDLS = [
    "CREATE INDEX IF NOT EXISTS idx_meta_sector ON stock_meta(sector_major)",
    "CREATE INDEX IF NOT EXISTS idx_meta_market ON stock_meta(market)",
    "CREATE INDEX IF NOT EXISTS idx_meta_cap ON stock_meta(market_cap DESC)",
]


def _normalize_sector(value) -> str:
    """섹터가 없거나 유효하지 않으면 '기타' 반환"""
    if value is None:
        return "기타"
    if isinstance(value, float) and math.isnan(value):
        return "기타"
    s = str(value).strip()
    if s in ("", "-", "nan", "NaN", "None"):
        return "기타"
    return s


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


def _ensure_meta_minervini_columns(conn: sqlite3.Connection) -> None:
    """REQ-MIN-008: stock_meta에 Minervini 신규 컬럼이 없으면 멱등 ALTER로 추가한다.

    Defense path: 레거시 DB에 신규 컬럼이 없을 때만 ALTER 실행.
    Primary path(새 DB): CREATE TABLE에 이미 포함되므로 ALTER가 실행되지 않는다.
    """
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(stock_meta)").fetchall()}
    for col in _MINERVINI_META_COLS:
        if col not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE stock_meta ADD COLUMN {col} REAL")
            except sqlite3.OperationalError:
                pass  # 동시 실행 등으로 이미 추가된 경우


def _rebuild(conn: sqlite3.Connection, weekly_db_path: str) -> None:
    # Ensure stock_meta table exists
    conn.execute(_STOCK_META_DDL)
    for ddl in _INDEX_DDLS:
        conn.execute(ddl)

    # REQ-MIN-008: 레거시 DB 방어 — 누락된 Minervini 컬럼 멱등 추가
    _ensure_meta_minervini_columns(conn)

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

    # --- Load daily snapshot (REQ-MIN-004: SMA150, HIGH_52W→high52w, LOW_52W, SMA200_20D_AGO 포함) ---
    # Defense path: 레거시 stock_prices에 신규 컬럼이 없을 경우를 방어
    daily_price_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(stock_prices)").fetchall()
    }
    has_minervini_price_cols = all(
        c in daily_price_cols for c in ("SMA150", "LOW_52W", "SMA200_20D_AGO")
    )

    # @MX:WARN: [AUTO] stock_prices SELECT ↔ stock_meta INSERT 위치 정합성 (SPEC-SMA5-FILTER-001 §1-B).
    #           sma5는 daily.py와 달리 SELECT/DDL/INSERT 모두 "맨 끝"에 둔다.
    # @MX:REASON: Minervini 가드가 d[8]/d[9]/d[10]을 위치로 읽으므로(아래 INSERT 튜플 참조),
    #             sma5를 SELECT 중간에 끼우면 인덱스가 시프트되어 무음 오염이 발생한다.
    #             끝에 append하면 기존 인덱스(d[8..10])가 보존된다. SMA5는 daily_by_name index 11.
    has_sma5_price_col = "SMA5" in daily_price_cols
    if has_minervini_price_cols:
        sma5_select = ", SMA5" if has_sma5_price_col else ""
        daily_rows = conn.execute(
            f"""SELECT Name, Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W,
                      SMA150, LOW_52W, SMA200_20D_AGO{sma5_select}
               FROM stock_prices
               WHERE Date = ?""",
            (latest_daily_date,),
        ).fetchall()
    else:
        # 레거시 경로: 신규 컬럼 없이 기존 컬럼만 조회
        sma5_select = ", SMA5" if has_sma5_price_col else ""
        daily_rows = conn.execute(
            f"""SELECT Name, Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W{sma5_select}
               FROM stock_prices
               WHERE Date = ?""",
            (latest_daily_date,),
        ).fetchall()
    # daily_by_name: Name -> (Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W
    #                         [, SMA150, LOW_52W, SMA200_20D_AGO] — Minervini 컬럼 있으면 포함
    #                         [, SMA5] — SMA5 컬럼 있으면 항상 맨 끝)
    daily_by_name: dict[str, tuple] = {r[0]: r[1:] for r in daily_rows}

    # --- Attach weekly DB and load weekly snapshot ---
    conn.execute(f"ATTACH DATABASE '{weekly_db_path}' AS weekly")

    # SPEC-SECTOR-GRID-001 REQ-SGR-005: 주봉 기준일은 정규 격자의 정규 대표 바로 해석
    # (CG-1 ISO 주당 1바·CG-3 부분 데이터 배제). weekly.stock_prices 의 자체
    # MAX(Date) WHERE Name=REFERENCE_STOCK 폐기 — 기준 종목 한정이 아니라 전 종목
    # 정규 격자로 수렴한다.
    latest_weekly_date = _get_latest_valid_date(weekly_db_path)

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
            "sector_major": _normalize_sector(srow.get("산업명(대)")),
            "sector_minor": _normalize_sector(srow.get("산업명(중)")),
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

    # @MX:WARN: [AUTO] sma5는 SELECT 분기에 따라 daily_by_name 튜플 위치가 다르다.
    #           Minervini 분기 → index 11(맨 끝), 레거시 분기 → index 8(맨 끝).
    # @MX:REASON: 위치를 잘못 읽으면 sma150/sma5가 뒤섞여 무음 오염된다. 분기 상태로
    #             명시 계산해 len(d) 모호성을 제거한다(레거시+SMA5 케이스 corruption 방지).
    if has_sma5_price_col:
        sma5_idx = 11 if has_minervini_price_cols else 8
    else:
        sma5_idx = None

    for name, sector_info in sector_by_name.items():
        if name not in daily_by_name:
            # No daily data → skip (delisted, newly listed, or missing)
            continue

        # d 인덱스: (Close[0], Change[1], EMA10[2], EMA20[3], SMA50[4], SMA100[5],
        #            SMA200[6], High52W[7], SMA150[8], LOW_52W[9], SMA200_20D_AGO[10], SMA5[11])
        #           (Minervini 컬럼 없는 레거시 분기에서는 High52W[7] 다음이 SMA5[8])
        d = daily_by_name[name]
        w = weekly_by_name.get(name)  # (CHG_1W, CHG_1M, CHG_3M, SMA10, SMA20, SMA40) or None
        code = sector_info["code"]

        # Minervini 컬럼은 신규 SELECT 분기에서만 존재 (레거시 분기에서는 항상 None)
        sma150 = d[8] if has_minervini_price_cols and len(d) > 8 else None
        low52w = d[9] if has_minervini_price_cols and len(d) > 9 else None
        sma200_20d_ago = d[10] if has_minervini_price_cols and len(d) > 10 else None
        sma5 = d[sma5_idx] if sma5_idx is not None and len(d) > sma5_idx else None

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
            d[7],   # high52w (기존 컬럼, HIGH_52W(window=250)로 갱신)
            w[0] if w else None,  # chg_1w
            w[1] if w else None,  # chg_1m
            w[2] if w else None,  # chg_3m
            rs_by_name.get(name),             # rs_12m
            w[3] if w else None,  # sma10_w
            w[4] if w else None,  # sma20_w
            w[5] if w else None,  # sma40_w
            now_str,
            sma150,           # sma150 (REQ-MIN-001)
            low52w,           # low52w (REQ-MIN-002)
            sma200_20d_ago,   # sma200_20d_ago (REQ-MIN-003)
            sma5,             # sma5 (SPEC-SMA5-FILTER-001 REQ-SMA5-003) — 맨 끝 append
        ))

    conn.execute("DELETE FROM stock_meta")
    conn.executemany(
        """INSERT OR REPLACE INTO stock_meta
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows_to_insert,
    )
    conn.commit()
    logger.info("stock_meta rebuilt: %d stocks inserted", len(rows_to_insert))
