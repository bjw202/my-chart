"""Weekly database generation: price DB and relative strength DB.

Optimized with:
- ThreadPoolExecutor for parallel API fetching
- Batch INSERT via executemany
- WAL mode for better concurrent performance
- INSERT OR REPLACE (UPSERT) instead of DROP TABLE
- Sorted insertion for B-tree locality
"""

from __future__ import annotations

import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from my_chart.config import DEFAULT_DB_WEEKLY, REFERENCE_STOCK
from my_chart.price import price_naver_rs
from my_chart.registry import get_stock_registry

logger = logging.getLogger(__name__)

# DB generation tuning parameters
MAX_WORKERS = 10
BATCH_SIZE = 500
API_THROTTLE_SLEEP = 0.1

_STOCK_PRICES_COLS = (
    "Name", "Date", "Open", "High", "Low", "Close",
    "Volume", "Volume50MA",
    "CHG_1W", "CHG_1M", "CHG_2M", "CHG_3M",
    "CHG_6M", "CHG_9M", "CHG_12M",
    "MA50", "MA150", "MA200",
    "MA200_Trend_1M", "MA200_Trend_2M",
    "MA200_Trend_3M", "MA200_Trend_4M",
    "MAX10", "MAX52", "min52", "Close_52min",
    "RS_1M", "RS_2M", "RS_3M",
    "RS_6M", "RS_9M", "RS_12M", "RS_Line",
)

_PRICE_DF_COLS = (
    "Open", "High", "Low", "Close",
    "Volume", "Volume MA50",
    "CHG_1W", "CHG_1M", "CHG_2M", "CHG_3M",
    "CHG_6M", "CHG_9M", "CHG_12M",
    "MA50", "MA150", "MA200",
    "MA200_Trend(1M)", "MA200_Trend(2M)",
    "MA200_Trend(3M)", "MA200_Trend(4M)",
    "MAX 10W", "MAX 52W", "min 52W", "Close-min 52W",
    "RS 1M", "RS 2M", "RS 3M",
    "RS 6M", "RS 9M", "RS 12M", "RS_Line",
)


def _setup_db(db_path: str) -> sqlite3.Connection:
    """Create connection with WAL mode and optimized pragmas."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    return conn


def _ensure_stock_prices_table(conn: sqlite3.Connection) -> None:
    """Create stock_prices table if not exists (UPSERT-compatible with unique key)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_prices (
            Name TEXT NOT NULL,
            Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Volume REAL, Volume50MA REAL,
            CHG_1W REAL, CHG_1M REAL, CHG_2M REAL, CHG_3M REAL,
            CHG_6M REAL, CHG_9M REAL, CHG_12M REAL,
            MA50 REAL, MA150 REAL, MA200 REAL,
            MA200_Trend_1M REAL, MA200_Trend_2M REAL,
            MA200_Trend_3M REAL, MA200_Trend_4M REAL,
            MAX10 REAL, MAX52 REAL, min52 REAL, Close_52min REAL,
            RS_1M REAL, RS_2M REAL, RS_3M REAL,
            RS_6M REAL, RS_9M REAL, RS_12M REAL, RS_Line REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stock_prices_name ON stock_prices(Name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices(Date)"
    )
    conn.commit()


def _df_to_rows(name: str, df: pd.DataFrame) -> list[tuple]:
    """Convert a DataFrame of price data into a list of row tuples for insertion."""
    rows = []
    for index, row in df.iterrows():
        vals = [name, index.strftime("%Y-%m-%d")]
        for col in _PRICE_DF_COLS:
            try:
                vals.append(float(row[col]))
            except (KeyError, ValueError, TypeError):
                vals.append(None)
        rows.append(tuple(vals))
    return rows


# @MX:WARN: [AUTO] ThreadPoolExecutor worker with blocking time.sleep(0.1)
# @MX:REASON: Sleep throttles Naver API rate (~100 req/min) but wastes worker thread time
def _fetch_one_stock(
    company: str, benchmark: pd.DataFrame, start: str
) -> tuple[str, list[tuple]]:
    """Fetch price data for one stock and convert to row tuples (thread-safe)."""
    try:
        data = price_naver_rs(company, benchmark, start, freq="week")
        if data.empty:
            return company, []
        time.sleep(API_THROTTLE_SLEEP)
        return company, _df_to_rows(company, data)
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", company, e)
        return company, []


def _batch_insert(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    """Batch insert rows using executemany with UPSERT."""
    if not rows:
        return
    placeholders = ", ".join(["?"] * len(_STOCK_PRICES_COLS))
    conn.executemany(
        f"INSERT OR REPLACE INTO stock_prices VALUES ({placeholders})",
        rows,
    )
    conn.commit()


def generate_price_db(
    db_name: str = DEFAULT_DB_WEEKLY,
    start: str = "20200101",
    max_workers: int = MAX_WORKERS,
) -> None:
    """Generate weekly price database for all stocks with parallel fetching.

    Args:
        db_name: Database file path (without .db extension).
        start: Start date in YYYYMMDD format.
        max_workers: Number of parallel API fetch threads.
    """
    st = time.time()
    db_path = f"{db_name}.db"
    conn = _setup_db(db_path)
    _ensure_stock_prices_table(conn)

    df_stock = get_stock_registry()
    total = len(df_stock)
    print(f"[weekly] Fetching data for {total} stocks with {max_workers} workers...")

    # Fetch KOSPI/KOSDAQ benchmarks first
    kospi = price_naver_rs("KOSPI", None, start, freq="week")
    kosdaq = price_naver_rs("KOSDAQ", None, start, freq="week")

    # Insert index data
    for label, idx_data in [("KOSPI", kospi), ("KOSDAQ", kosdaq)]:
        rows = _df_to_rows(label, idx_data)
        _batch_insert(conn, rows)

    # Parallel fetch individual stocks
    companies = sorted(df_stock["Name"].values)  # sorted for ordered insertion
    all_rows: list[tuple] = []
    done_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_one_stock, comp, kospi, start): comp
            for comp in companies
        }
        for future in as_completed(futures):
            company, rows = future.result()
            all_rows.extend(rows)
            done_count += 1

            if done_count % 50 == 0:
                print(f"  [{done_count}/{total}] fetched, inserting batch...")
                # Sort by (Name, Date) before insert for B-tree locality
                all_rows.sort(key=lambda r: (r[0], r[1]))
                _batch_insert(conn, all_rows)
                all_rows = []

    # Final batch
    if all_rows:
        all_rows.sort(key=lambda r: (r[0], r[1]))
        _batch_insert(conn, all_rows)

    conn.close()
    elapsed = time.time() - st
    print(f"[weekly] Price DB done: {done_count} stocks in {elapsed:.1f}s")

    # Generate RS rankings
    generate_rs_db(db_name)


def generate_rs_db(db_name: str = DEFAULT_DB_WEEKLY) -> None:
    """Generate relative_strength table from existing stock_prices.

    Processes all dates in parallel batches for speed.
    """
    db_path = f"{db_name}.db"
    conn = _setup_db(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS relative_strength (
            Name TEXT NOT NULL,
            Date TEXT NOT NULL,
            RS_12M_Rating REAL,
            RS_6M_Rating REAL,
            RS_3M_Rating REAL,
            RS_1M_Rating REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    conn.commit()

    # Get all dates from reference stock
    df_ref = pd.read_sql_query(
        "SELECT Date FROM stock_prices WHERE Name = ?",
        conn,
        params=(REFERENCE_STOCK,),
    )
    dates = df_ref["Date"].values
    total_dates = len(dates)
    print(f"[RS] Processing {total_dates} dates...")

    for i, date in enumerate(dates):
        df = pd.read_sql_query(
            "SELECT * FROM stock_prices WHERE Date = ?",
            conn,
            params=(date,),
        )
        df.dropna(inplace=True)

        if len(df) == 0:
            continue

        rank_1m = df["RS_1M"].rank(pct=True) * 100
        rank_3m = df["RS_3M"].rank(pct=True) * 100
        rank_6m = df["RS_6M"].rank(pct=True) * 100
        rank_9m = df["RS_9M"].rank(pct=True) * 100
        rank_12m = df["RS_12M"].rank(pct=True) * 100

        # @MX:NOTE: [AUTO] RS composite weighting: recent periods weighted higher (1.0, 0.8, 0.6, 0.4, 0.2)
        # Emphasizes recent momentum while incorporating long-term trend strength
        df["RS_12"] = (
            rank_1m + 0.8 * rank_3m + 0.6 * rank_6m
            + 0.4 * rank_9m + 0.2 * rank_12m
        )
        df["RS_12M_Rating"] = df["RS_12"].rank(pct=True) * 100

        df["RS_6"] = rank_1m + rank_3m + rank_6m
        df["RS_6M_Rating"] = df["RS_6"].rank(pct=True) * 100

        df["RS_3"] = rank_1m + rank_3m
        df["RS_3M_Rating"] = df["RS_3"].rank(pct=True) * 100

        df["RS_1M_Rating"] = rank_1m

        rs_rows = [
            (row["Name"], row["Date"],
             float(row["RS_12M_Rating"]), float(row["RS_6M_Rating"]),
             float(row["RS_3M_Rating"]), float(row["RS_1M_Rating"]))
            for _, row in df.iterrows()
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?, ?, ?, ?)",
            rs_rows,
        )

        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"  [RS {i + 1}/{total_dates}]")

    conn.commit()
    conn.close()
    print(f"[RS] Done: {total_dates} dates processed")
