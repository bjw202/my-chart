# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M5 — AC-SAG-029: 거래대금 출처.

daily `stock_prices.VolumeWon` 원천, `Close*Volume` 재계산 금지(REQ-SAG-026).
집계 창 = 기간 토글 연동 `[anchor(t,N), t]`(O-A4 결정).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from my_chart.analysis.sector_metrics import compute_trading_value_by_period


def test_ac_sag_029_given_then_trading_value_from_volume_won_not_close_times_volume() -> None:
    """Given daily VolumeWon=1_000_000_000, Close*Volume=999_000_000 → trading_value==1e9."""
    tmp_conn = sqlite3.connect(":memory:")
    tmp_conn.execute(
        "CREATE TABLE stock_prices (Name TEXT, Date TEXT, Close REAL, Volume REAL, "
        "VolumeWon REAL)")
    # Close*Volume = 999,000,000 이지만 VolumeWon = 1,000,000,000 (서로 다른 값 — 재계산이면 걸린다)
    tmp_conn.execute(
        "INSERT INTO stock_prices VALUES ('S1', '2026-08-05', 999.0, 1_000_000.0, "
        "1_000_000_000.0)")
    tmp_conn.commit()
    rows = tmp_conn.execute(
        "SELECT Name, SUM(VolumeWon) FROM stock_prices "
        "WHERE Date > ? AND Date <= ? GROUP BY Name",
        ("2026-08-01", "2026-08-11")).fetchall()
    tmp_conn.close()

    assert dict(rows) == {"S1": 1_000_000_000.0}


def test_ac_sag_029_compute_trading_value_by_period_sums_volume_won_over_anchor_window(
    tmp_path,
) -> None:
    """`compute_trading_value_by_period` — anchor(t,N) 창 [anchor_date, t] 를 합산한다."""
    db_path = str(tmp_path / "daily.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE stock_prices (Name TEXT, Date TEXT, Close REAL, Volume REAL, "
        "VolumeWon REAL)")
    rows = [
        ("S1", "2026-08-04", 100.0, 10.0, 300.0),   # 창 밖(anchor=2026-08-05 초과 아님)
        ("S1", "2026-08-05", 100.0, 10.0, 500.0),   # anchor 경계(포함, > 아님 == 이라 제외)
        ("S1", "2026-08-06", 100.0, 10.0, 700.0),   # 창 안
        ("S1", "2026-08-11", 100.0, 10.0, 900.0),   # 창 안(t)
    ]
    for r in rows:
        conn.execute("INSERT INTO stock_prices VALUES (?,?,?,?,?)", r)
    conn.commit()
    conn.close()

    result = compute_trading_value_by_period(
        db_path, anchor_dates={"1w": "2026-08-05", "1m": None, "3m": None}, t="2026-08-11")

    assert result["1w"]["S1"] == pytest.approx(700.0 + 900.0), (
        "창은 (anchor_date, t] — anchor 당일(08-05)은 제외, 08-06/08-11 만 합산")
    assert result["1m"] == {}, "anchor 부재 기간은 빈 dict"


def test_ac_sag_029_static_scan_no_close_times_volume_recomputation() -> None:
    """정적 스캔 — 집계 경로(sector_metrics.py)에 종가×거래량 재계산 표현이 0건."""
    import re

    src = Path("my_chart/analysis/sector_metrics.py").read_text(encoding="utf-8")
    matches = re.findall(r"[Cc]lose\s*\*\s*[Vv]olume|[Vv]olume\s*\*\s*[Cc]lose", src)
    assert matches == [], f"Close*Volume 재계산 표현이 남아있다: {matches}"
