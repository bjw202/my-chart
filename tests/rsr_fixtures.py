"""SPEC-RS-REBALANCE-001 공용 픽스처 빌더 — 주간 DB(stock_prices / relative_strength).

`generate_rs_db()`는 `SELECT * FROM stock_prices` 뒤 `df.dropna()`를 적용하므로
(REQ-RSR-023), 픽스처의 모든 가격 행은 `_STOCK_PRICES_COLS` 전 컬럼을 NULL 없이
채워야 한다. `price_row()`가 그 기본값을 채우고 지정 컬럼만 덮어쓴다. NULL을
의도한 경우(AC-RSR-018)에만 `overrides`로 `None`을 넣는다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from my_chart.db.weekly import (
    _RELATIVE_STRENGTH_COLS,
    _STOCK_PRICES_COLS,
    _batch_insert,
    _ensure_stock_prices_table,
)

# 가격 행 기본값 — 모든 컬럼이 NULL 아님. 수치 자체는 순위에 쓰이지 않는 컬럼용이다.
_PRICE_DEFAULTS: dict[str, float] = {
    "Open": 100.0, "High": 110.0, "Low": 90.0, "Close": 105.0,
    "Volume": 1_000_000.0, "VolumeSMA10": 900_000.0,
    "CHG_1W": 0.01, "CHG_1M": 0.02, "CHG_2M": 0.03, "CHG_3M": 0.04,
    "CHG_6M": 0.05, "CHG_9M": 0.06, "CHG_12M": 0.07,
    "SMA10": 100.0, "SMA20": 99.0, "SMA30": 98.0, "SMA40": 97.0,
    "SMA40_Trend_1M": 1.0, "SMA40_Trend_2M": 1.0,
    "SMA40_Trend_3M": 1.0, "SMA40_Trend_4M": 1.0,
    "MAX10": 110.0, "MAX52": 120.0, "min52": 80.0, "Close_52min": 0.3,
    "RS_1M": 0.1, "RS_2M": 0.1, "RS_3M": 0.1,
    "RS_6M": 0.1, "RS_9M": 0.1, "RS_12M": 0.1, "RS_Line": 1.0,
}

# 운영 DDL(`generate_rs_db()`의 CREATE TABLE)과 같은 스키마.
_RS_DDL = """CREATE TABLE IF NOT EXISTS relative_strength (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    RS_12M_Rating REAL,
    RS_6M_Rating REAL,
    RS_3M_Rating REAL,
    RS_1M_Rating REAL,
    PRIMARY KEY (Name, Date)
)"""


def price_row(name: str, date: str, **overrides) -> tuple:
    """`_STOCK_PRICES_COLS` 순서의 가격 행 튜플. 지정 컬럼만 덮어쓴다."""
    unknown = set(overrides) - set(_STOCK_PRICES_COLS)
    if unknown:
        raise KeyError(f"unknown stock_prices columns: {sorted(unknown)}")
    values = {"Name": name, "Date": date, **_PRICE_DEFAULTS, **overrides}
    return tuple(values[c] for c in _STOCK_PRICES_COLS)


def make_weekly_db(
    tmp_path: Path,
    rows: list[tuple],
    rs_rows: list[tuple] | None = None,
) -> str:
    """임시 주간 DB를 만들고 `generate_rs_db(db_name=...)`에 넘길 경로(확장자 제외)를 돌려준다.

    rows: `price_row()` 튜플 목록. rs_rows: 미리 심을 relative_strength 행
    (`_RELATIVE_STRENGTH_COLS` 순서) — 이전 실행이 남긴 낡은 행을 흉내 낸다.
    """
    db_path = tmp_path / "weekly.db"
    conn = sqlite3.connect(db_path)
    try:
        _ensure_stock_prices_table(conn)
        _batch_insert(conn, rows)
        conn.execute(_RS_DDL)
        if rs_rows:
            cols = ", ".join(_RELATIVE_STRENGTH_COLS)
            marks = ", ".join(["?"] * len(_RELATIVE_STRENGTH_COLS))
            conn.executemany(
                f"INSERT INTO relative_strength ({cols}) VALUES ({marks})", rs_rows
            )
        conn.commit()
    finally:
        conn.close()
    return str(db_path)[: -len(".db")]


def registry(*entries: tuple[str, str]) -> pd.DataFrame:
    """테스트 등록부 — `(Code, Name)` 쌍. `get_stock_registry()`와 같은 컬럼 구조."""
    return pd.DataFrame(
        [{"Code": code, "Name": name, "Market": "KOSPI"} for code, name in entries],
        columns=["Code", "Name", "Market"],
    )


def read_rs(db_name: str) -> pd.DataFrame:
    """relative_strength 전체를 (Name, Date) 정렬로 읽는다."""
    conn = sqlite3.connect(f"{db_name}.db")
    try:
        return pd.read_sql_query(
            "SELECT * FROM relative_strength ORDER BY Date, Name", conn
        )
    finally:
        conn.close()


def query_one(db_name: str, sql: str, params: tuple = ()):
    """단일 값 질의."""
    conn = sqlite3.connect(f"{db_name}.db")
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()
