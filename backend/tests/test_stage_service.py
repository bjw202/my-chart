"""stage_service 테스트 — SPEC-SECTOR-AGGREGATION-001 M5.

담당 AC
-------
* **AC-SAG-026** [함수 절] SMA40/SMA10 결측 종목은 stage=None(분류 불가) + 분모 제외.
* **AC-SAG-027** [불변식 §8.6] `stage1+stage2+stage3+stage4+unclassified_count == total`
  이 `distribution` 및 `by_sector` **모든** 엔트리에서 성립. `unclassified_count`·
  `by_sector[i].total` 신설(REQ-SAG-024).
"""

from __future__ import annotations

import sqlite3
import tempfile

import pytest

from backend.services.stage_service import get_stage_overview

_WEEKLY_DDL = """
CREATE TABLE IF NOT EXISTS stock_prices (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    Open REAL, High REAL, Low REAL, Close REAL,
    Volume REAL, VolumeSMA10 REAL,
    CHG_1W REAL, CHG_1M REAL, CHG_2M REAL, CHG_3M REAL,
    CHG_6M REAL, CHG_9M REAL, CHG_12M REAL,
    SMA10 REAL, SMA20 REAL, SMA40 REAL,
    SMA40_Trend_1M REAL, SMA40_Trend_2M REAL,
    SMA40_Trend_3M REAL, SMA40_Trend_4M REAL,
    MAX10 REAL, MAX52 REAL, min52 REAL, Close_52min REAL,
    RS_1M REAL, RS_2M REAL, RS_3M REAL,
    RS_6M REAL, RS_9M REAL, RS_12M REAL, RS_Line REAL,
    PRIMARY KEY (Name, Date)
)
"""

_RS_DDL = """
CREATE TABLE IF NOT EXISTS relative_strength (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    RS_12M_Rating REAL,
    PRIMARY KEY (Name, Date)
)
"""

_DATE = "2026-08-07"


def _row(name: str, close: float, sma10: float | None, sma40: float | None,
         sma40_trend_4m: float | None = None) -> tuple:
    return (
        name, _DATE,
        close * 0.99, close * 1.01, close * 0.98, close,
        1_000_000.0, 800_000.0,
        0.02, 0.05, 0.08, 0.12, 0.20, 0.25, 0.30,
        sma10, 92.0, sma40,
        sma40_trend_4m, None, None, sma40_trend_4m,
        close * 1.05, close * 1.2, close * 0.7, close - close * 0.7,
        50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 1.1,
    )


def _make_db(rows: list[tuple], rs: dict[str, float] | None = None) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)
    conn.executemany(
        "INSERT INTO stock_prices VALUES (" + ",".join("?" * 33) + ")", rows)
    for name, rating in (rs or {}).items():
        conn.execute(
            "INSERT INTO relative_strength VALUES (?, ?, ?)", (name, _DATE, rating))
    conn.commit()
    conn.close()
    return tmp.name


def test_ac_sag_026_unclassified_excluded_with_stage_none() -> None:
    """SMA40/SMA10 결측 종목은 stage=None 처리되어 all_stocks/후보 목록에서 빠진다."""
    db_path = _make_db([
        _row("정상", close=120.0, sma10=100.0, sma40=80.0, sma40_trend_4m=78.0),
        _row("결측1", close=50.0, sma10=None, sma40=90.0),
        _row("결측2", close=50.0, sma10=80.0, sma40=None),
    ], rs={"정상": 80.0, "결측1": 60.0, "결측2": 60.0})

    resp = get_stage_overview(db_path)

    names = {s.name for s in resp.all_stocks}
    assert "정상" in names
    assert "결측1" not in names
    assert "결측2" not in names


def test_ac_sag_027_stage_sum_identity_distribution_and_by_sector() -> None:
    """AC-SAG-027 — distribution 및 by_sector 모든 엔트리에서 합계 항등식이 성립."""
    db_path = _make_db([
        _row("알파", close=120.0, sma10=100.0, sma40=80.0, sma40_trend_4m=78.0),
        _row("베타", close=50.0, sma10=80.0, sma40=90.0, sma40_trend_4m=95.0),
        _row("감마", close=200.0, sma10=None, sma40=None),  # 분류 불가
    ], rs={"알파": 80.0, "베타": 60.0, "감마": 60.0})

    resp = get_stage_overview(db_path)
    d = resp.distribution
    assert d.stage1 + d.stage2 + d.stage3 + d.stage4 + d.unclassified_count == d.total
    assert d.unclassified_count >= 1, "분류 불가 종목이 distribution 에 반영되지 않았다"

    assert resp.by_sector, "by_sector 항목이 비어있다"
    for b in resp.by_sector:
        assert b.stage1 + b.stage2 + b.stage3 + b.stage4 + b.unclassified_count == b.total, (
            f"{b.sector}: 합계 항등식 위반 — {b}")


def test_ac_sag_027_unclassified_not_absorbed_into_stage1() -> None:
    """분류 불가 종목이 Stage 1 카운트에 흡수되지 않는다."""
    db_path = _make_db([
        _row("결측", close=100.0, sma10=None, sma40=None),
    ], rs={"결측": 50.0})

    resp = get_stage_overview(db_path)
    assert resp.distribution.stage1 == 0
    assert resp.distribution.unclassified_count == 1
