# coding: utf-8
"""SPEC-RS-REBALANCE-001 M4 — `stock_meta.rs_1m` (AC-RSR-007, AC-RSR-008, AC-RSR-008b).

검증 대상: `backend.services.meta_service.rebuild_stock_meta()` (REQ-RSR-010·011).

- AC-RSR-007: 최신 주차의 `RS_1M_Rating`이 종목명 기준으로 `stock_meta.rs_1m`에 복사되고,
  RS 행이 없는 종목은 NULL. 픽스처는 한 주 앞선 주차에 다른 값을, 같은 주차의
  `RS_12M_Rating`에도 다른 값을 둬서 "앞 주차 연결"·"12M 연결" 되돌림을 구분한다.
- AC-RSR-008: 라이브와 같은 컬럼명(`ma50_w ma150_w ma200_w`)의 27컬럼 레거시 `stock_meta`에
  멱등 ALTER로 `rs_1m`이 끝에 붙고, 기존 27개 컬럼의 값이 제자리에 들어간다.
- AC-RSR-008b: 새 DB에서 `rs_1m`은 `cid = 27`(마지막)이고 28번째 값이다.

테스트 DB는 전부 `tmp_path`에 만든다. 라이브 `Output/` DB는 읽지도 쓰지도 않는다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import backend.services.meta_service as svc
from backend.services.meta_service import rebuild_stock_meta

LATEST_W = "2026-10-16"   # 최신 주차(금)
PREV_W = "2026-10-09"     # 한 주 앞선 주차(금)
DAILY_DATE = "2026-10-16"

# 레거시 27컬럼 — 라이브 일봉 DB의 실제 컬럼명(research.md R6)
_LEGACY_COLS = [
    "code", "name", "market", "market_cap", "sector_major", "sector_minor", "product",
    "close", "change_1d", "ema10", "ema20", "sma50", "sma100", "sma200", "high52w",
    "chg_1w", "chg_1m", "chg_3m", "rs_12m", "ma50_w", "ma150_w", "ma200_w",
    "last_updated", "sma150", "low52w", "sma200_20d_ago", "sma5",
]


# ---------------------------------------------------------------------------
# 픽스처 빌더
# ---------------------------------------------------------------------------

def _make_weekly(path: Path, rs_rows: list[tuple[str, str, float, float]],
                 price_names: list[str]) -> None:
    """주간 DB: stock_prices(두 주차) + 운영 스키마 relative_strength.

    rs_rows: (Name, Date, RS_12M_Rating, RS_1M_Rating)
    """
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE stock_prices (
            Name TEXT NOT NULL, Date TEXT NOT NULL, Close REAL, Volume REAL,
            CHG_1W REAL, CHG_1M REAL, CHG_3M REAL, SMA10 REAL, SMA20 REAL, SMA40 REAL,
            PRIMARY KEY (Name, Date))"""
    )
    conn.execute(
        """CREATE TABLE relative_strength (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            RS_12M_Rating REAL, RS_6M_Rating REAL, RS_3M_Rating REAL, RS_1M_Rating REAL,
            PRIMARY KEY (Name, Date))"""
    )
    for i, name in enumerate(price_names):
        for date in (PREV_W, LATEST_W):
            conn.execute(
                "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?)",
                (name, date, 1000.0 + i, 1e6, 0.01 * (i + 1), 0.02 * (i + 1),
                 0.03 * (i + 1), 900.0 + i, 800.0 + i, 700.0 + i),
            )
    conn.executemany(
        "INSERT INTO relative_strength (Name, Date, RS_12M_Rating, RS_1M_Rating) "
        "VALUES (?,?,?,?)",
        rs_rows,
    )
    conn.commit()
    conn.close()


def _make_daily(path: Path, stocks: dict[str, dict[str, float]],
                legacy_meta: bool = False) -> None:
    """일봉 DB: Minervini + SMA5 컬럼을 가진 stock_prices (+ 선택: 레거시 stock_meta)."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE stock_prices (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            Close REAL, Change REAL, EMA10 REAL, EMA20 REAL, SMA5 REAL, SMA50 REAL,
            SMA100 REAL, SMA200 REAL, High52W REAL,
            SMA150 REAL, LOW_52W REAL, SMA200_20D_AGO REAL,
            PRIMARY KEY (Name, Date))"""
    )
    for name, v in stocks.items():
        conn.execute(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, DAILY_DATE, v["close"], v["change"], v["ema10"], v["ema20"], v["sma5"],
             v["sma50"], v["sma100"], v["sma200"], v["high52w"], v["sma150"],
             v["low52w"], v["sma200_20d_ago"]),
        )
    if legacy_meta:
        col_defs = ", ".join(
            f"{c} TEXT PRIMARY KEY" if c == "code"
            else f"{c} {'INTEGER' if c == 'market_cap' else 'TEXT' if c in ('name', 'market', 'sector_major', 'sector_minor', 'product', 'last_updated') else 'REAL'}"
            for c in _LEGACY_COLS
        )
        conn.execute(f"CREATE TABLE stock_meta ({col_defs})")
        # 이전 갱신이 남긴 낡은 행 — 재구축의 DELETE로 사라져야 한다
        conn.execute(
            "INSERT INTO stock_meta (code, name) VALUES ('999999', '낡은종목')"
        )
    conn.commit()
    conn.close()


def _daily_values(seed: int) -> dict[str, float]:
    """컬럼마다 서로 다른 값 — 위치 시프트가 일어나면 값이 다른 컬럼으로 새어 단언이 깨진다."""
    base = 1000.0 * (seed + 1)
    return {
        "close": base + 1, "change": 0.5 + seed, "ema10": base + 2, "ema20": base + 3,
        "sma5": base + 4, "sma50": base + 5, "sma100": base + 6, "sma200": base + 7,
        "high52w": base + 8, "sma150": base + 9, "low52w": base + 10,
        "sma200_20d_ago": base + 11,
    }


def _patch_sources(monkeypatch, names: list[str]) -> None:
    codes = [f"{100010 + 10 * i:06d}" for i in range(len(names))]
    df = pd.DataFrame({
        "Code": codes, "Name": names, "Market": ["KOSPI"] * len(names),
        "산업명(대)": ["반도체"] * len(names), "산업명(중)": ["메모리"] * len(names),
        "주요제품": ["D램"] * len(names),
    })
    monkeypatch.setattr(svc, "get_sector_registry", lambda: df)
    monkeypatch.setattr(svc, "REFERENCE_STOCK", names[0])
    # basic_data.xlsx 부재 재현 — market_cap은 NULL로 고정(값 비교를 결정적으로)
    orig_exists = Path.exists
    monkeypatch.setattr(
        Path, "exists",
        lambda self: False if self.name == "basic_data.xlsx" else orig_exists(self),
    )


def _code_of(names: list[str], name: str) -> str:
    return f"{100010 + 10 * names.index(name):06d}"


# ---------------------------------------------------------------------------
# AC-RSR-007 — rs_1m 복사 (REQ-RSR-010)
# ---------------------------------------------------------------------------

NAMES_007 = ["가종목", "나종목", "다종목", "라종목"]  # 라종목: RS 행 없음

# (Name, Date, RS_12M_Rating, RS_1M_Rating) — 12M과 1M, 최신과 앞 주차가 모두 다르다
RS_ROWS_007 = [
    ("가종목", LATEST_W, 91.0, 15.5), ("가종목", PREV_W, 90.0, 61.0),
    ("나종목", LATEST_W, 42.0, 77.25), ("나종목", PREV_W, 41.0, 33.0),
    ("다종목", LATEST_W, 12.0, 88.0), ("다종목", PREV_W, 13.0, 44.0),
]
EXPECTED_RS1M_007 = {"가종목": 15.5, "나종목": 77.25, "다종목": 88.0, "라종목": None}


def test_ac_rsr_007_rs_1m_copied_from_latest_week(monkeypatch, tmp_path):
    weekly = tmp_path / "weekly.db"
    daily = tmp_path / "daily.db"
    _make_weekly(weekly, RS_ROWS_007, NAMES_007)
    _make_daily(daily, {n: _daily_values(i) for i, n in enumerate(NAMES_007)})
    _patch_sources(monkeypatch, NAMES_007)

    rebuild_stock_meta(str(daily), str(weekly))

    conn = sqlite3.connect(daily)
    got = dict(conn.execute("SELECT name, rs_1m FROM stock_meta").fetchall())
    rs12 = dict(conn.execute("SELECT name, rs_12m FROM stock_meta").fetchall())
    conn.close()

    assert got == EXPECTED_RS1M_007, f"stock_meta.rs_1m={got!r}"
    # rs_12m은 이전과 같은 의미(같은 주차 RS_12M_Rating)로 남는다
    assert rs12 == {"가종목": 91.0, "나종목": 42.0, "다종목": 12.0, "라종목": None}


# ---------------------------------------------------------------------------
# AC-RSR-008 — 레거시 27컬럼 stock_meta 보강 (REQ-RSR-011)
# ---------------------------------------------------------------------------

NAMES_008 = ["갑종목", "을종목"]
RS_ROWS_008 = [
    ("갑종목", LATEST_W, 81.0, 21.0), ("갑종목", PREV_W, 80.0, 20.0),
    ("을종목", LATEST_W, 55.0, 66.0), ("을종목", PREV_W, 54.0, 65.0),
]


def _expected_legacy_row(names: list[str], name: str, i: int, rs12: float) -> dict:
    d = _daily_values(i)
    return {
        "code": _code_of(names, name), "name": name, "market": "KOSPI", "market_cap": None,
        "sector_major": "반도체", "sector_minor": "메모리", "product": "D램",
        "close": d["close"], "change_1d": d["change"], "ema10": d["ema10"],
        "ema20": d["ema20"], "sma50": d["sma50"], "sma100": d["sma100"],
        "sma200": d["sma200"], "high52w": d["high52w"],
        # 주간 stock_prices 최신 주차 값(_make_weekly: i번째 종목)
        "chg_1w": 0.01 * (i + 1), "chg_1m": 0.02 * (i + 1), "chg_3m": 0.03 * (i + 1),
        "rs_12m": rs12,
        "ma50_w": 900.0 + i, "ma150_w": 800.0 + i, "ma200_w": 700.0 + i,
        "sma150": d["sma150"], "low52w": d["low52w"],
        "sma200_20d_ago": d["sma200_20d_ago"], "sma5": d["sma5"],
    }


def test_ac_rsr_008_legacy_stock_meta_gets_rs_1m_appended(monkeypatch, tmp_path):
    weekly = tmp_path / "weekly.db"
    daily = tmp_path / "daily.db"
    _make_weekly(weekly, RS_ROWS_008, NAMES_008)
    _make_daily(daily, {n: _daily_values(i) for i, n in enumerate(NAMES_008)},
                legacy_meta=True)
    _patch_sources(monkeypatch, NAMES_008)

    conn = sqlite3.connect(daily)
    before = [r[1] for r in conn.execute("PRAGMA table_info(stock_meta)")]
    conn.close()
    assert before == _LEGACY_COLS, "전제: 27컬럼 레거시 스키마, rs_1m 없음"

    rebuild_stock_meta(str(daily), str(weekly))
    # 멱등: 두 번째 실행도 오류 없이 같은 결과
    rebuild_stock_meta(str(daily), str(weekly))

    conn = sqlite3.connect(daily)
    conn.row_factory = sqlite3.Row
    cols = [r[1] for r in conn.execute("PRAGMA table_info(stock_meta)")]
    rows = {r["name"]: dict(r) for r in conn.execute("SELECT * FROM stock_meta")}
    conn.close()

    assert cols == _LEGACY_COLS + ["rs_1m"], f"컬럼 순서={cols!r}"
    assert set(rows) == set(NAMES_008), "낡은 행은 DELETE로 사라지고 등록부 종목만 남는다"
    for i, (name, rs12) in enumerate([("갑종목", 81.0), ("을종목", 55.0)]):
        row = rows[name]
        expected = _expected_legacy_row(NAMES_008, name, i, rs12)
        actual = {k: row[k] for k in expected}
        assert actual == pytest.approx(expected), f"{name}: {actual!r}"
        assert row["last_updated"], "last_updated는 채워진다"
    assert rows["갑종목"]["rs_1m"] == 21.0
    assert rows["을종목"]["rs_1m"] == 66.0


# ---------------------------------------------------------------------------
# AC-RSR-008b — 새 DB의 컬럼 위치와 28번째 값 (REQ-RSR-011)
# ---------------------------------------------------------------------------

def test_ac_rsr_008b_new_db_rs_1m_is_last_column_and_28th_value(monkeypatch, tmp_path):
    names = ["병종목"]
    weekly = tmp_path / "weekly.db"
    daily = tmp_path / "daily.db"
    _make_weekly(weekly, [("병종목", LATEST_W, 22.0, 11.0), ("병종목", PREV_W, 1.0, 2.0)],
                 names)
    values = _daily_values(0)
    values["sma5"] = 5.555
    _make_daily(daily, {"병종목": values})
    _patch_sources(monkeypatch, names)

    rebuild_stock_meta(str(daily), str(weekly))

    conn = sqlite3.connect(daily)
    info = conn.execute("PRAGMA table_info(stock_meta)").fetchall()
    row = conn.execute("SELECT sma5, rs_1m, rs_12m, sma200_20d_ago FROM stock_meta").fetchone()
    conn.close()

    assert (info[-1][0], info[-1][1]) == (27, "rs_1m"), f"마지막 컬럼={info[-1]!r}"
    assert len(info) == 28
    assert row[0] == 5.555, f"sma5={row[0]!r}"
    assert row[1] == 11.0, f"rs_1m={row[1]!r}"
    assert row[2] == 22.0, f"rs_12m={row[2]!r}"
    assert row[3] == values["sma200_20d_ago"]
