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
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd

from my_chart.config import DEFAULT_DB_WEEKLY, REFERENCE_STOCK
from my_chart.price import fix_zero_ohlc, price_naver_rs
from my_chart.registry import get_stock_registry

logger = logging.getLogger(__name__)

# DB generation tuning parameters
MAX_WORKERS = 10
BATCH_SIZE = 500
API_THROTTLE_SLEEP = 0.1

_STOCK_PRICES_COLS = (
    "Name", "Date", "Open", "High", "Low", "Close",
    "Volume", "VolumeSMA10",
    "CHG_1W", "CHG_1M", "CHG_2M", "CHG_3M",
    "CHG_6M", "CHG_9M", "CHG_12M",
    "SMA10", "SMA20", "SMA30", "SMA40",
    "SMA40_Trend_1M", "SMA40_Trend_2M",
    "SMA40_Trend_3M", "SMA40_Trend_4M",
    "MAX10", "MAX52", "min52", "Close_52min",
    "RS_1M", "RS_2M", "RS_3M",
    "RS_6M", "RS_9M", "RS_12M", "RS_Line",
)

# relative_strength 테이블 컬럼 순서 (CREATE TABLE DDL 순서와 동일).
# column-name INSERT 매핑용 — rs_rows 값 튜플 순서와 반드시 일치해야 한다.
_RELATIVE_STRENGTH_COLS = (
    "Name", "Date",
    "RS_12M_Rating", "RS_6M_Rating", "RS_3M_Rating", "RS_1M_Rating",
)

_PRICE_DF_COLS = (
    "Open", "High", "Low", "Close",
    "Volume", "Volume SMA10",
    "CHG_1W", "CHG_1M", "CHG_2M", "CHG_3M",
    "CHG_6M", "CHG_9M", "CHG_12M",
    "SMA10", "SMA20", "SMA30", "SMA40",
    "SMA40_Trend(1M)", "SMA40_Trend(2M)",
    "SMA40_Trend(3M)", "SMA40_Trend(4M)",
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


# SMA30 포함: 기존 주간 DB(SMA30 없음)는 구 스키마로 감지돼 DROP 후 재생성 —
# SMA30의 과거 값은 fetch 시점에 계산되므로 전체 재수집이 유일한 백필 경로다.
_REQUIRED_COLS = {"VolumeSMA10", "SMA10", "SMA20", "SMA30", "SMA40"}


def _ensure_stock_prices_table(conn: sqlite3.Connection) -> None:
    """Create stock_prices table, auto-migrating if old schema is detected."""
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(stock_prices)").fetchall()
    }
    if existing and not _REQUIRED_COLS.issubset(existing):
        # 구 스키마 감지 (MA50/MA150/MA200) → DROP 후 재생성
        conn.execute("DROP TABLE IF EXISTS stock_prices")
        conn.execute("DROP INDEX IF EXISTS idx_stock_prices_name")
        conn.execute("DROP INDEX IF EXISTS idx_stock_prices_date")
        conn.commit()

    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_prices (
            Name TEXT NOT NULL,
            Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Volume REAL, VolumeSMA10 REAL,
            CHG_1W REAL, CHG_1M REAL, CHG_2M REAL, CHG_3M REAL,
            CHG_6M REAL, CHG_9M REAL, CHG_12M REAL,
            SMA10 REAL, SMA20 REAL, SMA30 REAL, SMA40 REAL,
            SMA40_Trend_1M REAL, SMA40_Trend_2M REAL,
            SMA40_Trend_3M REAL, SMA40_Trend_4M REAL,
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
        vals: list[str | float | None] = [name, str(index)[:10]]
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
        data = fix_zero_ohlc(data)
        time.sleep(API_THROTTLE_SLEEP)
        return company, _df_to_rows(company, data)
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", company, e)
        return company, []


def _batch_insert(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    """Batch insert rows using executemany with UPSERT."""
    if not rows:
        return
    # @MX:ANCHOR: [AUTO] column-name 기반 INSERT — _STOCK_PRICES_COLS 순서가 라이브
    #             stock_prices 물리 컬럼 순서와 달라도 이름으로 안전 매핑된다.
    # @MX:REASON: positional `VALUES (?, ?, ...)` 패턴은 legacy ALTER ADD COLUMN이
    #             컬럼을 테이블 끝에 append해 물리 순서가 튜플 순서와 어긋나면 모든
    #             후속 컬럼이 시프트되어 무음 데이터 오염이 발생한다
    #             (Lesson #8 / daily.py:267 선행 사례 — SPEC-SMA5-FILTER-001 v1.0.4
    #             1.3M 행 부패 회귀, 2026-05-26).
    column_list = ", ".join(_STOCK_PRICES_COLS)
    placeholders = ", ".join(["?"] * len(_STOCK_PRICES_COLS))
    conn.executemany(
        f"INSERT OR REPLACE INTO stock_prices ({column_list}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()


def _batch_insert_rs(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    """Batch insert relative_strength rows via column-name UPSERT (no commit).

    커밋은 호출처(generate_rs_db)의 기존 cadence(20 iteration 단위 + 최종)를
    존중해 여기서 수행하지 않는다 — _batch_insert 와의 유일한 차이.
    """
    if not rows:
        return
    # @MX:ANCHOR: [AUTO] column-name 기반 INSERT — _RELATIVE_STRENGTH_COLS 순서가
    #             라이브 relative_strength 물리 컬럼 순서와 달라도 안전 매핑된다.
    # @MX:REASON: positional `VALUES (?, ?, ...)` 패턴은 legacy ALTER ADD COLUMN이
    #             컬럼을 테이블 끝에 append하면 물리 순서가 어긋나 시프트 부패가
    #             발생한다 (Lesson #8 / daily.py:267 선행 사례와 동일 인과).
    column_list = ", ".join(_RELATIVE_STRENGTH_COLS)
    placeholders = ", ".join(["?"] * len(_RELATIVE_STRENGTH_COLS))
    conn.executemany(
        f"INSERT OR REPLACE INTO relative_strength ({column_list}) VALUES ({placeholders})",
        rows,
    )


# DELETE 실행 시 SQLite 변수 상한(SQLITE_MAX_VARIABLE_NUMBER, 기본 999) 회피용
# 이름 청크 크기. (names × dates) 가 상한을 넘지 않도록 names 를 분할한다.
_SUPERSEDE_NAME_CHUNK = 500


def _iso_year_week(date_str: str) -> tuple[int, int] | None:
    """``YYYY-MM-DD`` → ``(iso_year, iso_week)``. 파싱 불가 시 None.

    SQL ``strftime('%W')`` 는 ISO 주 규칙(연초 처리)과 달라 사용 금지이므로
    Python ``date.isocalendar()`` 로 계산한다(plan §3.1).
    """
    try:
        iy, iw, _ = date.fromisoformat(date_str).isocalendar()
    except (ValueError, TypeError):
        return None
    return (iy, iw)


# @MX:WARN: [AUTO] 물리 DELETE 경로 — 같은 (Name, ISO 주) 에서 이번 실행이 기록한
#           바보다 이른 날짜의 행을 삭제한다(REQ-SGR-010 주중 재적재 supersede).
# @MX:REASON: 삭제 범위는 “이번 실행이 기록한 ISO 주”로 한정되며 과거 주는 절대
#             삭제하지 않는다. generate_price_db(supersede=False) / --no-supersede
#             로 호출 자체가 차단된다. supersede 활성 실행 전 DB 백업 권장(advisory).
def _supersede_same_iso_week_rows(
    conn: sqlite3.Connection,
    written_name_dates: list[tuple[str, str]],
) -> int:
    """이번 실행이 기록한 ``(Name, Date)`` 쌍을 받아 같은 ``(Name, ISO 주)`` 에서
    **이번 실행이 기록한 바보다 이른 날짜**의 행을 DELETE 한다(REQ-SGR-010).

    * 삭제 대상 ISO 주 = 이번 실행이 최소 1개 바를 기록한 주로 한정.
      이번 실행이 기록하지 않은 과거 주의 행은 절대 삭제하지 않는다(과거 이력 보존).
    * 각 ``(Name, ISO 주)`` 에서 이번 실행이 기록한 가장 큰 날짜(kept)는 남긴다.

    Args:
        conn: ``stock_prices`` 테이블을 가진 SQLite 연결.
        written_name_dates: 이번 실행이 기록한 ``(Name, Date)`` 쌍 목록.

    Returns:
        삭제된 행 수.

    Safety:
        물리 DELETE(되돌림 불가). ``generate_price_db(supersede=False)`` 또는
        ``--no-supersede`` 로 본 함수 호출을 차단한다 — 그 경로는 중복 행이 쌓이지만
        DELETE 위험은 0이다. supersede 활성 실행 전에는 DB 백업을 권장한다(advisory).
    """
    if not written_name_dates:
        return 0

    # 1) (Name, ISO 주) → 이번 실행이 기록한 최대 날짜(kept)
    max_written: dict[tuple[str, int, int], str] = {}
    for name, date_str in written_name_dates:
        iyw = _iso_year_week(date_str)
        if iyw is None:
            continue
        key = (name, iyw[0], iyw[1])
        prev = max_written.get(key)
        if prev is None or date_str > prev:
            max_written[key] = date_str
    if not max_written:
        return 0

    # 2) DB 기존 날짜를 ISO 주로 그룹핑(SELECT DISTINCT Date — 수백 건으로 가벼움)
    dates_by_week: dict[tuple[int, int], list[str]] = {}
    for (d,) in conn.execute("SELECT DISTINCT Date FROM stock_prices"):
        iyw = _iso_year_week(d)
        if iyw is None:
            continue
        dates_by_week.setdefault(iyw, []).append(d)
    if not dates_by_week:
        return 0

    # 3) 삭제 계획: (iso_year, iso_week, kept) → (earlier dates, names).
    #    kept(이번 실행 최대 날짜)가 같으면 earlier 집합도 같으므로 한 번에 묶는다.
    plan: dict[tuple[int, int, str], tuple[list[str], list[str]]] = {}
    for (name, iy, iw), kept in max_written.items():
        week_dates = dates_by_week.get((iy, iw))
        if not week_dates:
            continue
        earlier = sorted(d for d in week_dates if d < kept)
        if not earlier:
            continue
        plan.setdefault((iy, iw, kept), (earlier, []))[1].append(name)
    if not plan:
        return 0

    # 4) DELETE 실행 + INFO 로그({iso_week, deleted_rows}). past 주는 범위 밖.
    total = 0
    for (iy, iw, kept), (earlier, names) in plan.items():
        date_ph = ", ".join(["?"] * len(earlier))
        for i in range(0, len(names), _SUPERSEDE_NAME_CHUNK):
            chunk = names[i:i + _SUPERSEDE_NAME_CHUNK]
            name_ph = ", ".join(["?"] * len(chunk))
            cur = conn.execute(
                f"DELETE FROM stock_prices "
                f"WHERE Name IN ({name_ph}) AND Date IN ({date_ph})",
                (*chunk, *earlier),
            )
            if cur.rowcount:
                logger.info(
                    "supersede: ISO %d-W%02d kept_date=%s deleted_rows=%d "
                    "(earlier same-week rows removed; past ISO weeks untouched)",
                    iy, iw, kept, cur.rowcount,
                )
                total += cur.rowcount
    if total:
        conn.commit()
    return total


def generate_price_db(
    db_name: str = DEFAULT_DB_WEEKLY,
    start: str = "20200101",
    max_workers: int = MAX_WORKERS,
    progress_callback: Callable[[int, int, str], None] | None = None,
    supersede: bool = True,
) -> None:
    """Generate weekly price database for all stocks with parallel fetching.

    Args:
        db_name: Database file path (without .db extension).
        start: Start date in YYYYMMDD format.
        max_workers: Number of parallel API fetch threads.
        progress_callback: Optional (done, total, current) progress callback.
        supersede: REQ-SGR-010 — 같은 ``(Name, ISO 주)`` 에서 이번 실행이 기록한
            바보다 이른 날짜의 행을 삭제한다(주중 재적재 supersede, 기본 True).
            ``False``(``--no-supersede``)면 DELETE 를 수행하지 않는다(중복 허용,
            DELETE 위험 0). 삭제 범위는 이번 실행이 기록한 ISO 주로 한정된다.

    Note:
        ``supersede=True`` 실행 전에는 DB 백업을 권장한다(물리 DELETE 는 되돌릴
        수 없다 — 본 함수는 백업을 자동 생성하지 않는다, advisory).
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

    # 이번 실행이 기록한 (Name, Date) 쌍 — REQ-SGR-010 supersede 범위 산출용
    written_name_dates: list[tuple[str, str]] = []

    # Insert index data
    for label, idx_data in [("KOSPI", kospi), ("KOSDAQ", kosdaq)]:
        rows = _df_to_rows(label, idx_data)
        written_name_dates.extend((r[0], r[1]) for r in rows)
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
            _company, rows = future.result()
            all_rows.extend(rows)
            done_count += 1

            if progress_callback is not None:
                progress_callback(done_count, total, _company)

            if done_count % 50 == 0:
                print(f"  [{done_count}/{total}] fetched, inserting batch...")
                # Sort by (Name, Date) before insert for B-tree locality
                all_rows.sort(key=lambda r: (r[0], r[1]))
                written_name_dates.extend((r[0], r[1]) for r in all_rows)
                _batch_insert(conn, all_rows)
                all_rows = []

    # Final batch
    if all_rows:
        all_rows.sort(key=lambda r: (r[0], r[1]))
        written_name_dates.extend((r[0], r[1]) for r in all_rows)
        _batch_insert(conn, all_rows)

    # REQ-SGR-010: 같은 (Name, ISO 주) 의 이번 실행 이전 날짜 행을 supersede.
    # supersede=False(--no-supersede)면 호출하지 않는다(DELETE 위험 0).
    if supersede:
        _supersede_same_iso_week_rows(conn, written_name_dates)

    conn.close()
    elapsed = time.time() - st
    print(f"[weekly] Price DB done: {done_count} stocks in {elapsed:.1f}s")


def generate_rs_db(
    db_name: str = DEFAULT_DB_WEEKLY,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> None:
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
        params=[REFERENCE_STOCK],
    )
    dates = df_ref["Date"].values
    total_dates = len(dates)
    print(f"[RS] Processing {total_dates} dates...")

    for i, date in enumerate(dates):
        df = pd.read_sql_query(
            "SELECT * FROM stock_prices WHERE Date = ?",
            conn,
            params=[str(date)],
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
        _batch_insert_rs(conn, rs_rows)

        if progress_callback is not None:
            progress_callback(i + 1, total_dates, str(date))

        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"  [RS {i + 1}/{total_dates}]")

    conn.commit()
    conn.close()
    print(f"[RS] Done: {total_dates} dates processed")
