# coding: utf-8
"""SPEC-RS-REBALANCE-001 M4 — 섹터 `rs_med` (AC-RSR-010, REQ-RSR-013·014).

섹터 P = [10, 20, 30, 90, 100], Q = [45, 48, 50, 52, 55] (두 섹터 평균 모두 50.0),
R = P의 다섯 값 + RS 행 없는 종목 1개. 기대값은 손으로 계산한 리터럴이다.

- P: rs_avg 50.0 / rs_med 30.0 / rs_top_pct 40.0
- Q: rs_avg 50.0 / rs_med 50.0 / rs_top_pct 0.0
- R: rs_avg 50.0 / rs_med 30.0 (결측 제외 — 0으로 채우면 중앙값 25.0)

양변 출처: `get_sector_ranking()` 응답(`sectors[]` 랭킹 항목과 봉투 `data[]`) vs 리터럴.
합성 주간 DB는 tmp_path에 만든다(관용: backend/tests/test_bubble_rs_missing_exclusion.py).

`sectors[]` 는 순위가 매겨진 섹터만 싣는다(집계 경로 통일 — 시총가중 수익률·3기간
초과수익률이 있어야 순위가 생긴다). 그래서 주간 DB 는 3M 앵커(91일)가 생기도록 16주로,
시총 원천(일봉 `stock_meta`)도 함께 만든다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from tests.rsr_fixtures import make_weekly_db, price_row

_DATES = [
    "2024-01-05", "2024-01-12", "2024-01-19", "2024-01-26",
    "2024-02-02", "2024-02-09", "2024-02-16", "2024-02-23",
    "2024-03-01", "2024-03-08", "2024-03-15", "2024-03-22",
    "2024-03-29", "2024-04-05", "2024-04-12", "2024-04-19",
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
    """운영 스키마 주간 DB(`price_row` 전 컬럼) — 집계 커버리지(AG-7)가 산출 가능해야 한다."""
    prices: list[tuple] = []
    rs_rows: list[tuple] = []
    for i, date in enumerate(_DATES):
        close = 2500.0 + i * 10.0
        prices.append(price_row("KOSPI", date, Close=close, Open=close, High=close, Low=close))
    for _sector, stocks in _PLAN:
        for j, (name, rs) in enumerate(stocks.items()):
            base = 50_000.0 + j * 10_000.0
            factor = 0.01 + j * 0.001
            for i, date in enumerate(_DATES):
                close = base * (1 + factor * i)
                prices.append(price_row(name, date, Close=close, Open=close, High=close,
                                        Low=close))
                if rs is not None:
                    # RS_1M_Rating은 일부러 다른 값 — rs_med가 12M에서 나오는지 구분
                    rs_rows.append((name, date, rs, None, None, 100.0 - rs))
    built = make_weekly_db(path.parent, prices, rs_rows) + ".db"
    assert built == str(path), built


def _make_daily(path: Path) -> None:
    """시총 원천 — 전 종목 동일 시총(시총가중 산출 가능 조건 AG-4). 거래대금 원천은 빈 표."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE stock_meta (name TEXT PRIMARY KEY, market_cap REAL)")
    conn.executemany("INSERT INTO stock_meta VALUES (?, ?)",
                     [(name, 1e12) for _s, stocks in _PLAN for name in stocks])
    conn.execute("CREATE TABLE stock_prices (Name TEXT, Date TEXT, VolumeWon REAL)")
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

    tmp = tmp_path_factory.mktemp("rsr_m4")
    db, daily = tmp / "weekly.db", tmp / "daily.db"
    _make_weekly(db)
    _make_daily(daily)
    # 유효 유니버스(UN-3)는 라이브 registry xlsx 를 읽는다 — 관심사가 아니므로 제한 없음.
    with patch("my_chart.analysis.sector_metrics.get_sector_registry", return_value=_registry()), \
            patch("my_chart.analysis.sector_metrics._valid_universe", return_value=None):
        return get_sector_ranking(str(db), str(daily))


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
