# coding: utf-8
"""SPEC-RS-REBALANCE-001 M4 — 섹터 `rs_med` (AC-RSR-010, REQ-RSR-013·014).

섹터 P = [10, 20, 30, 90, 100], Q = [45, 48, 50, 52, 55] (두 섹터 평균 모두 50.0),
R = P의 다섯 값 + RS 행 없는 종목 1개. 기대값은 손으로 계산한 리터럴이다.

- P: rs_avg 50.0 / rs_med 30.0 / rs_top_pct 40.0
- Q: rs_avg 50.0 / rs_med 50.0 / rs_top_pct 0.0
- R: rs_avg 50.0 / rs_med 30.0 (결측 제외 — 0으로 채우면 중앙값 25.0)

양변 출처: `get_sector_ranking()` 응답(`sectors[]` 랭킹 항목과 봉투 `data[]`) vs 리터럴.
합성 주간 DB는 tmp_path에 만든다(관용: backend/tests/test_bubble_rs_missing_exclusion.py).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

_DATES = [
    "2024-01-05", "2024-01-12", "2024-01-19", "2024-01-26",
    "2024-02-02", "2024-02-09", "2024-02-16", "2024-02-23",
    "2024-03-01", "2024-03-08", "2024-03-15", "2024-03-22",
]

_P = (10.0, 20.0, 30.0, 90.0, 100.0)
_Q = (45.0, 48.0, 50.0, 52.0, 55.0)
# (섹터, {종목명: RS 값 또는 None(=RS 행 없음)})
_PLAN: list[tuple[str, dict[str, float | None]]] = [
    ("섹터P", {f"P{i}": v for i, v in enumerate(_P, 1)}),
    ("섹터Q", {f"Q{i}": v for i, v in enumerate(_Q, 1)}),
    ("섹터R", {**{f"R{i}": v for i, v in enumerate(_P, 1)}, "R6": None}),
]

EXPECTED = {
    "섹터P": {"rs_avg": 50.0, "rs_med": 30.0, "rs_top_pct": 40.0},
    "섹터Q": {"rs_avg": 50.0, "rs_med": 50.0, "rs_top_pct": 0.0},
    "섹터R": {"rs_avg": 50.0, "rs_med": 30.0, "rs_top_pct": 40.0},
}


def _make_weekly(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE stock_prices (
            Name TEXT, Date TEXT, Close REAL, Volume REAL,
            SMA10 REAL, SMA40 REAL, SMA40_Trend_4M REAL,
            CHG_1W REAL, CHG_1M REAL, CHG_3M REAL, MAX52 REAL,
            VolumeSMA10 REAL
        );
        CREATE TABLE relative_strength (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            RS_12M_Rating REAL, RS_6M_Rating REAL, RS_3M_Rating REAL, RS_1M_Rating REAL,
            PRIMARY KEY (Name, Date)
        );
    """)
    prices: list[tuple] = []
    rs_rows: list[tuple] = []
    for i, date in enumerate(_DATES):
        close = 2500.0 + i * 10.0
        prices.append(("KOSPI", date, close, 5e6, close * 0.98, close * 0.95, close * 0.93,
                       0.005 + i * 0.001, 0.015, 0.04, close * 1.05, 4.5e6))
    for _sector, stocks in _PLAN:
        for j, (name, rs) in enumerate(stocks.items()):
            base = 50_000.0 + j * 10_000.0
            factor = 0.01 + j * 0.001
            for i, date in enumerate(_DATES):
                close = base * (1 + factor * i)
                chg = factor * (1 + i * 0.1)
                prices.append((name, date, close, 1e6 + i * 5e4, close * 0.99, close * 0.97,
                               close * 0.95, chg, chg * 4, chg * 12, close * 1.1, 9e5))
                if rs is not None:
                    # RS_1M_Rating은 일부러 다른 값 — rs_med가 12M에서 나오는지 구분
                    rs_rows.append((name, date, rs, None, None, 100.0 - rs))
    conn.executemany("INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", prices)
    conn.executemany("INSERT INTO relative_strength VALUES (?,?,?,?,?,?)", rs_rows)
    conn.commit()
    conn.close()


def _registry() -> pd.DataFrame:
    return pd.DataFrame([
        {"Name": name, "산업명(대)": sector, "Market": "KOSPI"}
        for sector, stocks in _PLAN for name in stocks
    ])


@pytest.fixture(scope="module")
def ranking_response(tmp_path_factory):
    from backend.services.sector_ranking_service import get_sector_ranking

    db = tmp_path_factory.mktemp("rsr_m4") / "weekly.db"
    _make_weekly(db)
    with patch("my_chart.analysis.sector_metrics.get_sector_registry", return_value=_registry()):
        return get_sector_ranking(str(db), None)


@pytest.mark.parametrize("sector", sorted(EXPECTED))
def test_ac_rsr_010_ranking_items_rs_med(ranking_response, sector: str) -> None:
    items = {s.name: s for s in ranking_response.sectors}
    assert sector in items, f"{sector}가 /sectors/ranking 항목에 없다: {sorted(items)}"
    item = items[sector]
    exp = EXPECTED[sector]
    assert item.rs_med == pytest.approx(exp["rs_med"]), f"{sector} rs_med={item.rs_med!r}"
    assert item.rs_avg == pytest.approx(exp["rs_avg"]), f"{sector} rs_avg={item.rs_avg!r}"
    assert item.rs_top_pct == pytest.approx(exp["rs_top_pct"])


@pytest.mark.parametrize("sector", sorted(EXPECTED))
def test_ac_rsr_010_envelope_data_rs_med(ranking_response, sector: str) -> None:
    data = {d.name: d for d in ranking_response.data}
    assert sector in data, f"{sector}가 봉투 data[]에 없다: {sorted(data)}"
    agg = data[sector]
    exp = EXPECTED[sector]
    assert agg.rs_med.value == pytest.approx(exp["rs_med"]), f"{sector} rs_med={agg.rs_med!r}"
    assert agg.rs_avg.value == pytest.approx(exp["rs_avg"])
    assert agg.rs_top_pct.value == pytest.approx(exp["rs_top_pct"])


def test_ac_rsr_010_rs_med_missing_when_no_valid_rs() -> None:
    """유효 RS가 하나도 없는 섹터는 rs_med가 결측(REQ-RSR-013)."""
    from my_chart.analysis.sector_metrics import _aggregate_members, _Member

    members = [
        _Member(name=f"N{i}", rs=None, nh=None, stage2=None, market_cap=None,
                returns={"1w": None, "1m": None, "3m": None})
        for i in range(5)
    ]
    agg, _ = _aggregate_members("결측섹터", members)
    assert agg.rs_med.value is None
    assert agg.rs_med.reason == "missing"
