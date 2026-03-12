"""Shared pytest fixtures for my_chart characterization and integration tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Registry global state reset
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_registry_globals():
    """Reset lazy-loaded registry singletons before each test to avoid test pollution."""
    import my_chart.registry as reg

    orig_stock = reg._df_stock
    orig_sector = reg._df_sector
    reg._df_stock = None
    reg._df_sector = None
    yield
    reg._df_stock = orig_stock
    reg._df_sector = orig_sector


@pytest.fixture(autouse=True)
def reset_price_session():
    """Reset shared HTTP session singleton before each test."""
    import my_chart.price as price_mod

    orig = price_mod._session
    price_mod._session = None
    yield
    price_mod._session = orig


# ---------------------------------------------------------------------------
# Mock sectormap (replaces _load_sectormap to avoid xlsx file dependency)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_sectormap(monkeypatch):
    """Patch _load_sectormap to return minimal in-memory test data."""
    df = pd.DataFrame(
        {
            "Code": ["005930", "000660", "005490"],
            "Name": ["삼성전자", "SK하이닉스", "POSCO홀딩스"],
            "Market": ["KOSPI", "KOSPI", "KOSPI"],
            "산업명(대)": ["전기전자", "전기전자", "철강금속"],
            "산업명(중)": ["반도체", "반도체", "철강"],
            "주요제품": ["메모리반도체", "D램/낸드", "열연강판"],
        }
    )
    monkeypatch.setattr("my_chart.registry._load_sectormap", lambda: df.copy())
    return df


# ---------------------------------------------------------------------------
# Mock Naver Finance HTTP response
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_naver_response(monkeypatch):
    """Patch _get_session so price_naver makes no real HTTP calls.

    The mock response returns a minimal CSV with 2 trading days of OHLCV data.
    Date values are quoted strings so pandas reads them as str (required for
    .str.extract() in price_naver).
    """
    # Use "D20240102" prefix so pandas reads Date column as str (object dtype),
    # not as int64. price_naver uses .str.extract(r"(\d+)") which requires str dtype.
    csv_data = (
        "Date,Open,High,Low,Close,Volume\n"
        "D20240102,100,105,98,102,1000000\n"
        "D20240103,102,106,100,104,1200000\n"
    ).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.content = csv_data
    mock_resp.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    monkeypatch.setattr("my_chart.price._get_session", lambda: mock_session)
    return mock_session


# ---------------------------------------------------------------------------
# Temporary SQLite DB fixtures for backend integration tests
# ---------------------------------------------------------------------------

_DAILY_DDL = """
CREATE TABLE IF NOT EXISTS stock_prices (
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
)
"""

_META_DDL = """
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

_WEEKLY_PRICES_DDL = """
CREATE TABLE IF NOT EXISTS stock_prices (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    Open REAL, High REAL, Low REAL, Close REAL,
    Volume REAL,
    CHG_1W REAL, CHG_1M REAL, CHG_3M REAL,
    SMA10 REAL, SMA20 REAL, SMA40 REAL,
    PRIMARY KEY (Name, Date)
)
"""

_WEEKLY_RS_DDL = """
CREATE TABLE IF NOT EXISTS relative_strength (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    RS_12M_Rating REAL,
    PRIMARY KEY (Name, Date)
)
"""


def _insert_daily_rows(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    """Insert rows into stock_prices with 26-column positional INSERT."""
    conn.executemany(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


def _make_daily_row(
    name: str,
    date: str,
    close: float = 100.0,
    ema10: float = 99.0,
    ema20: float = 98.0,
    sma50: float = 95.0,
    sma100: float = 90.0,
    sma200: float = 85.0,
) -> tuple:
    """Build a 26-element daily row tuple with sensible defaults."""
    return (
        name, date,
        close * 0.99,   # Open
        close * 1.01,   # High
        close * 0.98,   # Low
        close,          # Close
        1.0,            # Change
        close * 1.1,    # High52W
        1_000_000.0,    # Volume
        900_000.0,      # Volume20MA
        100.0,          # VolumeWon
        ema10, ema20,
        close * 0.97,   # SMA21
        sma50, close * 0.96,  # EMA65
        sma100, sma200,
        2.0,            # DailyRange
        close * 0.99,   # HLC
        1.0, 2.0, 5.0, 15.0,  # From* percentages
        3.0,            # Range
        2.5,            # ADR20
    )


@pytest.fixture
def daily_db(tmp_path: Path) -> str:
    """Create a temporary daily SQLite DB with stock_prices and stock_meta tables."""
    db_path = str(tmp_path / "test_daily.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_DAILY_DDL)
    conn.execute(_META_DDL)

    # Insert 3 days of OHLCV for two test stocks
    rows = [
        _make_daily_row("삼성전자", "2024-01-02"),
        _make_daily_row("삼성전자", "2024-01-03"),
        _make_daily_row("삼성전자", "2024-01-04"),
        _make_daily_row("SK하이닉스", "2024-01-02"),
        _make_daily_row("SK하이닉스", "2024-01-03"),
    ]
    _insert_daily_rows(conn, rows)

    # Insert stock_meta rows
    conn.executemany(
        "INSERT OR REPLACE INTO stock_meta VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("005930", "삼성전자", "KOSPI", 5000000, "전기전자", "반도체", "메모리반도체",
             100.0, 1.0, 99.0, 98.0, 95.0, 90.0, 85.0,
             110.0, 2.0, 5.0, 10.0, 75.0, 95.0, 90.0, 85.0, "2024-01-04T00:00:00"),
            ("000660", "SK하이닉스", "KOSPI", 1000000, "전기전자", "반도체", "D램/낸드",
             80.0, 0.5, 79.0, 78.0, 75.0, 70.0, 65.0,
             90.0, 1.0, 3.0, 8.0, 65.0, 75.0, 70.0, 65.0, "2024-01-03T00:00:00"),
            ("005490", "POSCO홀딩스", "KOSPI", 800000, "철강금속", "철강", "열연강판",
             50.0, -0.5, 49.0, 48.0, 47.0, 45.0, 43.0,
             55.0, 0.5, 2.0, 5.0, 50.0, 47.0, 45.0, 43.0, "2024-01-04T00:00:00"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def daily_db_no_meta(tmp_path: Path) -> str:
    """Daily DB with stock_prices but NO stock_meta table."""
    db_path = str(tmp_path / "test_daily_no_meta.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_DAILY_DDL)
    rows = [_make_daily_row("삼성전자", "2024-01-04")]
    _insert_daily_rows(conn, rows)
    conn.close()
    return db_path


@pytest.fixture
def weekly_db(tmp_path: Path) -> str:
    """Create a temporary weekly SQLite DB with stock_prices and relative_strength tables."""
    db_path = str(tmp_path / "test_weekly.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_PRICES_DDL)
    conn.execute(_WEEKLY_RS_DDL)

    conn.executemany(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("삼성전자", "2024-01-04", 100.0, 101.0, 99.0, 100.0, 1000000.0, 2.0, 5.0, 10.0, 95.0, 90.0, 85.0),
            ("SK하이닉스", "2024-01-04", 80.0, 81.0, 79.0, 80.0, 500000.0, 1.0, 3.0, 8.0, 75.0, 70.0, 65.0),
        ],
    )
    conn.executemany(
        "INSERT OR REPLACE INTO relative_strength VALUES (?,?,?)",
        [
            ("삼성전자", "2024-01-04", 75.0),
            ("SK하이닉스", "2024-01-04", 65.0),
        ],
    )
    conn.commit()
    conn.close()
    return db_path
