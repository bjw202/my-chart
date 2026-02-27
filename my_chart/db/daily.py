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
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    conn.commit()


# @MX:WARN: [AUTO] ThreadPoolExecutor worker with blocking time.sleep(0.1)
# @MX:REASON: Sleep throttles Naver API rate (~100 req/min) but wastes worker thread time
def _fetch_daily_stock(company: str, start: str) -> tuple[str, list[tuple]]:
    """Fetch daily data for one stock and calculate indicators (thread-safe)."""
    try:
        price = price_naver(company, start, freq="day")
        if price is None or price.empty:
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

        rows = []
        for index, row in price.iterrows():
            rows.append((
                company,
                index.strftime("%Y-%m-%d"),
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                float(row["Change(%)"]),
                float(row["High_52w"]),
                float(row["Volume"]),
                float(row["Volume20MA"]),
                float(row["VolumeWon"]),
                float(row["EMA10"]),
                float(row["EMA20"]),
                float(row["SMA21"]),
                float(row["SMA50"]),
                float(row["EMA65"]),
                float(row["SMA100"]),
                float(row["SMA200"]),
                float(row["DailyRange(%)"]),
                float(row["HLC"]),
                float(row["FromEMA10(%)"]),
                float(row["FromEMA20(%)"]),
                float(row["FromSMA50(%)"]),
                float(row["FromSMA200(%)"]),
                float(row["Range"]),
                float(row["ADR20"]),
            ))

        time.sleep(API_THROTTLE_SLEEP)
        return company, rows
    except Exception as e:
        logger.warning("Failed to fetch daily %s: %s", company, e)
        return company, []


def price_daily_db(
    db_name: str = DEFAULT_DB_DAILY,
    max_workers: int = MAX_WORKERS,
) -> None:
    """Generate daily price database for all stocks with parallel fetching."""
    st = time.time()
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=365)
    start = start_date.strftime("%Y%m%d")

    db_path = f"{db_name}.db"
    conn = _setup_db(db_path)
    _ensure_daily_table(conn)

    df_stock = get_stock_registry()
    companies = sorted(df_stock["Name"].values)
    total = len(companies)
    print(f"[daily] Fetching data for {total} stocks with {max_workers} workers...")

    all_rows: list[tuple] = []
    done_count = 0
    placeholders = ", ".join(["?"] * len(_DAILY_COLS))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_daily_stock, comp, start): comp
            for comp in companies
        }
        for future in as_completed(futures):
            company, rows = future.result()
            all_rows.extend(rows)
            done_count += 1

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
