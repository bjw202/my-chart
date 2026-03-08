"""Daily database generation.

Optimized with:
- ThreadPoolExecutor for parallel API fetching
- Batch INSERT via executemany
- WAL mode and UPSERT pattern
- Fixed January date calculation bug
"""

from __future__ import annotations

import datetime
import logging
import sqlite3
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

from my_chart.config import DEFAULT_DB_DAILY
from my_chart.price import price_naver
from my_chart.registry import get_stock_registry

logger = logging.getLogger(__name__)

MAX_WORKERS = 10
API_THROTTLE_SLEEP = 0.1

_DAILY_COLS = (
    "Name", "Date", "Open", "High", "Low", "Close",
    "Change", "High52W",
    "Volume", "Volume20MA", "VolumeWon",
    "EMA10", "EMA20", "SMA21", "SMA50", "EMA65", "SMA100", "SMA200",
    "DailyRange", "HLC",
    "FromEMA10", "FromEMA20", "FromSMA50", "FromSMA200",
    "Range", "ADR20",
    "RS_Line",
)


def _setup_db(db_path: str) -> sqlite3.Connection:
    """Create connection with WAL mode and optimized pragmas."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def _ensure_daily_table(conn: sqlite3.Connection) -> None:
    """Create daily stock_prices table if not exists."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_prices (
            Name TEXT NOT NULL,
            Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Change REAL, High52W REAL,
            Volume REAL, Volume20MA REAL, VolumeWon REAL,
            EMA10 REAL, EMA20 REAL, SMA21 REAL, SMA50 REAL, EMA65 REAL, SMA100 REAL, SMA200 REAL,
            DailyRange REAL, HLC REAL,
            FromEMA10 REAL, FromEMA20 REAL, FromSMA50 REAL, FromSMA200 REAL,
            Range REAL, ADR20 REAL,
            RS_Line REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_name ON stock_prices(Name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_date ON stock_prices(Date)"
    )
    # Migrate existing tables that lack SMA100 column
    try:
        conn.execute("ALTER TABLE stock_prices ADD COLUMN SMA100 REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # RS_Line 컬럼 마이그레이션
    try:
        conn.execute("ALTER TABLE stock_prices ADD COLUMN RS_Line REAL")
    except sqlite3.OperationalError:
        pass  # 컬럼이 이미 존재하는 경우
    conn.commit()


def _sanitize_ohlc(price: pd.DataFrame) -> pd.DataFrame:
    """Replace zero OHLC values with the nearest non-zero OHLC value in the same row.

    Handles trading halts and API fetch errors where one or more price fields is 0.
    Rows where all four OHLC values are 0 are dropped entirely.
    """
    ohlc_cols = ["Open", "High", "Low", "Close"]
    price[ohlc_cols] = price[ohlc_cols].replace(0, float("nan"))
    price[ohlc_cols] = price[ohlc_cols].bfill(axis=1).ffill(axis=1)
    return price.dropna(subset=["Close"])


# @MX:WARN: [AUTO] ThreadPoolExecutor worker with blocking time.sleep(0.1)
# @MX:REASON: Sleep throttles Naver API rate (~100 req/min) but wastes worker thread time
def _fetch_daily_stock(
    company: str, start: str, kospi_close: "pd.Series | None" = None
) -> tuple[str, list[tuple]]:
    """Fetch daily data for one stock and calculate indicators (thread-safe)."""
    try:
        price = price_naver(company, start, freq="day")
        if price is None or price.empty:
            return company, []

        price = _sanitize_ohlc(price)
        if price.empty:
            logger.warning("All OHLC rows were zero for %s, skipping", company)
            return company, []

        price["Change(%)"] = price["Close"].pct_change() * 100
        price["Volume20MA"] = price["Volume"].rolling(window=20).mean()
        price["EMA10"] = price["Close"].ewm(span=10).mean()
        price["EMA20"] = price["Close"].ewm(span=20).mean()
        price["SMA21"] = price["Close"].rolling(window=21).mean()
        price["SMA50"] = price["Close"].rolling(window=50).mean()
        price["EMA65"] = price["Close"].ewm(span=65).mean()
        price["SMA100"] = price["Close"].rolling(window=100).mean()
        price["SMA200"] = price["Close"].rolling(window=200).mean()
        price["DailyRange(%)"] = (
            (price["High"] - price["Low"]) / (price["High"] + price["Low"]) * 100
        )
        price["HLC"] = (price["High"] + price["Low"] + price["Close"]) / 3
        # @MX:NOTE: [AUTO] Convert volume to 억원 (100M KRW) units for readability
        price["VolumeWon"] = price["HLC"] * price["Volume"] / 1_0000_0000
        price["High_52w"] = price["High"].rolling(window=252).max()
        price["FromEMA10(%)"] = (price["Close"] - price["EMA10"]) / price["EMA10"] * 100
        price["FromEMA20(%)"] = (price["Close"] - price["EMA20"]) / price["EMA20"] * 100
        price["FromSMA50(%)"] = (price["Close"] - price["SMA50"]) / price["SMA50"] * 100
        price["FromSMA200(%)"] = (
            (price["Close"] - price["SMA200"]) / price["SMA200"] * 100
        )
        price["Range"] = 100 * (price["High"] / price["Low"] - 1)
        price["ADR20"] = price["Range"].rolling(window=20).mean()

        # RS_Line 계산: 주가 종가 / KOSPI 종가
        if kospi_close is not None and not price.empty:
            price["RS_Line"] = price["Close"] / kospi_close.reindex(price.index)
        else:
            price["RS_Line"] = float("nan")  # 스칼라 NaN을 전체 행에 브로드캐스트

        rows = []
        for index, row in price.iterrows():
            # pandas-stubs에서 row[key]의 반환 타입이 Any로 좁혀지지 않으므로
            # Any로 명시적 캐스팅 후 float() 호출
            r: Any = row
            # RS_Line: NaN → None (SQLite NULL)
            rs_raw: float | None = r["RS_Line"]
            if rs_raw is None:
                rs_line_value: float | None = None
            else:
                rs_line_value = None if rs_raw != rs_raw else rs_raw  # NaN != NaN
            rows.append((
                company,
                index.strftime("%Y-%m-%d"),  # type: ignore[union-attr]
                float(r["Open"]),
                float(r["High"]),
                float(r["Low"]),
                float(r["Close"]),
                float(r["Change(%)"]),
                float(r["High_52w"]),
                float(r["Volume"]),
                float(r["Volume20MA"]),
                float(r["VolumeWon"]),
                float(r["EMA10"]),
                float(r["EMA20"]),
                float(r["SMA21"]),
                float(r["SMA50"]),
                float(r["EMA65"]),
                float(r["SMA100"]),
                float(r["SMA200"]),
                float(r["DailyRange(%)"]),
                float(r["HLC"]),
                float(r["FromEMA10(%)"]),
                float(r["FromEMA20(%)"]),
                float(r["FromSMA50(%)"]),
                float(r["FromSMA200(%)"]),
                float(r["Range"]),
                float(r["ADR20"]),
                rs_line_value,
            ))

        time.sleep(API_THROTTLE_SLEEP)
        return company, rows
    except Exception as e:
        logger.warning("Failed to fetch daily %s: %s", company, e)
        return company, []


def price_daily_db(
    db_name: str = DEFAULT_DB_DAILY,
    max_workers: int = MAX_WORKERS,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> None:
    """Generate daily price database for all stocks with parallel fetching."""
    st = time.time()
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=730)  # 2 years for stable SMA200
    start = start_date.strftime("%Y%m%d")

    db_path = f"{db_name}.db"
    conn = _setup_db(db_path)
    _ensure_daily_table(conn)

    df_stock = get_stock_registry()
    companies = sorted(df_stock["Name"].values)
    total = len(companies)
    print(f"[daily] Fetching data for {total} stocks with {max_workers} workers...")

    # KOSPI 일별 종가 데이터 수집 (RS_Line 계산용) — ThreadPoolExecutor 시작 전에 반드시 실행
    kospi_close = None
    try:
        kospi_df = price_naver("KOSPI", start, freq="day")
        if kospi_df is not None and not kospi_df.empty:
            kospi_close: Any = kospi_df["Close"]
    except Exception as e:
        logger.warning("KOSPI 데이터 수집 실패: %s", e)

    all_rows: list[tuple] = []
    done_count = 0
    placeholders = ", ".join(["?"] * len(_DAILY_COLS))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_daily_stock, comp, start, kospi_close): comp
            for comp in companies
        }
        for future in as_completed(futures):
            _company, rows = future.result()
            all_rows.extend(rows)
            done_count += 1

            if progress_callback is not None:
                progress_callback(done_count, total, _company)

            if done_count % 50 == 0:
                print(f"  [{done_count}/{total}] fetched, inserting batch...")
                all_rows.sort(key=lambda r: (r[0], r[1]))
                conn.executemany(
                    f"INSERT OR REPLACE INTO stock_prices VALUES ({placeholders})",
                    all_rows,
                )
                conn.commit()
                all_rows = []

    # Final batch
    if all_rows:
        all_rows.sort(key=lambda r: (r[0], r[1]))
        conn.executemany(
            f"INSERT OR REPLACE INTO stock_prices VALUES ({placeholders})",
            all_rows,
        )
        conn.commit()

    conn.close()
    elapsed = time.time() - st
    print(f"[daily] Done: {done_count} stocks in {elapsed:.1f}s")
