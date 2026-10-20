"""재현 테스트: ``/api/sectors/ranking`` 의 ``sectors[]`` 가 ``data[]`` 와 다른 산식을 쓴다.

버그: ``sectors[]`` 는 레거시 ``compute_sector_ranking`` 에서 만들어진다.
      (a) composite 를 **min-max** 정규화(``_normalize_list``)로 계산하고,
      (b) 초과수익률을 **KOSPI 지수 행**(``CHG_*``)에 대해 계산한다.
      ``data[]`` 는 ``compute_sector_aggregates`` — **순위 백분위**(AG-8) composite 와
      **ALL_CAPPED** 벤치마크 초과수익률이다. 프론트 섹터 표는 ``sectors[]`` 를 기반으로
      rank/rank_change 만 ``data[]`` 로 덮어써서, 한 행에 두 산식의 숫자가 섞였다
      (라이브 1M: 방송미디어 sectors[] 초과 +23.84 vs data[] +15.53).

기대 동작(사용자 결정): ALL_CAPPED·집계 경로로 통일한다.
    sectors[] 의 rank / composite_score / excess_returns / returns ==
    compute_sector_aggregates(period=None) 결과(직렬화 반올림만 다름).
    순위 제외(``rank is None``) 섹터는 sectors[] 에서 빠진다(Bump·알림과 동일).

픽스처 설계(손으로 검산한 불일치):
    섹터별 수익률(%) — 구성종목 동일 경로, 시총 동일
        OUT(극단값): 1W 1.5 / 1M 2.5 / 3M 60      (5종목)
        LEAD       : 1W 2.0 / 1M 3.0 / 3M 5       (5종목)
        MID        : 1W 1.0 / 1M 2.0 / 3M 4       (5종목)
        LAG        : 1W -1  / 1M -1  / 3M 0       (5종목)
        SMALL      : 1W 0.5 / 1M 1.5 / 3M 3       (3종목 — AG-5 제외)
    순위 백분위 composite: LEAD 1위, OUT 2위 / min-max(SMALL 포함): OUT 90.0 > LEAD 72.5
    KOSPI 지수 행 CHG_1W/1M/3M = 5% / 10% / 20% — ALL_CAPPED(구성종목 평균)와 크게 다르다.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from tests.rsr_fixtures import make_weekly_db, price_row

_SECTOR_RETURNS: dict[str, tuple[float, float, float]] = {
    "OUT": (1.5, 2.5, 60.0),
    "LEAD": (2.0, 3.0, 5.0),
    "MID": (1.0, 2.0, 4.0),
    "LAG": (-1.0, -1.0, 0.0),
    "SMALL": (0.5, 1.5, 3.0),
}
_MEMBERS = {"OUT": 5, "LEAD": 5, "MID": 5, "LAG": 5, "SMALL": 3}
_N_WEEKS = 16
_FIRST_FRIDAY = date(2024, 1, 5)
_KOSPI_CHG = {"CHG_1W": 0.05, "CHG_1M": 0.10, "CHG_3M": 0.20}   # fraction(×100 = %)
#: LEAD 구성종목 RS_12M_Rating — 평균 71.4, RS>=80 비율 2/5 = 40%. 나머지 섹터는 50.
_LEAD_RS = (85.0, 72.0, 90.0, 60.0, 50.0)


def _dates() -> list[str]:
    return [(_FIRST_FRIDAY + timedelta(weeks=i)).isoformat() for i in range(_N_WEEKS)]


def _close_path(r1w: float, r1m: float, r3m: float) -> list[float]:
    """마지막 날짜 t 기준 anchor(t,7/28/91) 수익률이 정확히 (r1w, r1m, r3m) 이 되는 종가 경로."""
    final = 100.0 * (1 + r3m / 100)
    closes = [100.0] * _N_WEEKS
    closes[-1] = final
    closes[-2] = final / (1 + r1w / 100)
    closes[-5] = final / (1 + r1m / 100)
    closes[-14] = 100.0
    return closes


@pytest.fixture
def unify_dbs(tmp_path: Path, monkeypatch) -> tuple[str, str, str]:
    """(weekly_db, daily_db, as_of) — 5섹터, 16주, 시총 동일, KOSPI 지수 행 포함."""
    dates = _dates()
    names_by_sector = {s: [f"{s}{i}" for i in range(n)] for s, n in _MEMBERS.items()}
    rows: list[tuple] = []
    rs_rows: list[tuple] = []
    for sector, (r1w, r1m, r3m) in _SECTOR_RETURNS.items():
        closes = _close_path(r1w, r1m, r3m)
        for i, name in enumerate(names_by_sector[sector]):
            rs = _LEAD_RS[i] if sector == "LEAD" else 50.0
            for d, c in zip(dates, closes):
                rows.append(price_row(name, d, Close=c, High=c, Low=c, Open=c))
                rs_rows.append((name, d, rs, 50.0, 50.0, 50.0))
    # KOSPI 지수 행 — 레거시 `_load_kospi_returns` 가 읽는 원천. ALL_CAPPED 와 다르게 둔다.
    for d in dates:
        rows.append(price_row("KOSPI", d, Close=2500.0, High=2500.0, Low=2500.0,
                              Open=2500.0, **_KOSPI_CHG))
    weekly_db = make_weekly_db(tmp_path, rows, rs_rows) + ".db"

    daily_db = str(tmp_path / "daily.db")
    conn = sqlite3.connect(daily_db)
    try:
        conn.execute("CREATE TABLE stock_meta (name TEXT PRIMARY KEY, market_cap REAL)")
        conn.execute("CREATE TABLE stock_prices (Name TEXT, Date TEXT, VolumeWon REAL)")
        all_names = [n for ns in names_by_sector.values() for n in ns]
        conn.executemany("INSERT INTO stock_meta VALUES (?, ?)",
                         [(n, 1_000_000_000_000.0) for n in all_names])
        conn.executemany("INSERT INTO stock_prices VALUES (?, ?, ?)",
                         [(n, d, 1.0e9) for n in all_names for d in dates])
        conn.commit()
    finally:
        conn.close()

    # KOSPI 지수도 LEAD 소속으로 등록부에 넣는다 — 지수 행이 구성종목으로 섞이지 않는지
    # (``_INDEX_NAMES`` 제외) 를 의미 있게 검사하기 위함이다.
    registry = pd.DataFrame([
        {"Code": f"{i:06d}", "Name": n, "Market": "KOSPI", "산업명(대)": s,
         "산업명(중)": s, "주요제품": "-"}
        for i, (s, n) in enumerate(
            [(s, n) for s, ns in names_by_sector.items() for n in ns] + [("LEAD", "KOSPI")])
    ])
    monkeypatch.setattr("my_chart.registry._load_sectormap", lambda *a, **k: registry.copy())
    monkeypatch.setattr("my_chart.registry._df_sector", None)
    # 유효 유니버스(UN-3)는 라이브 registry xlsx 를 읽는다 — 관심사가 아니므로 제한 없음.
    monkeypatch.setattr(
        "my_chart.analysis.sector_metrics._valid_universe", lambda *a, **k: None)
    return weekly_db, daily_db, dates[-1]


def _ranking(weekly_db: str, daily_db: str, as_of: str, period: str | None = None):
    from backend.services.sector_ranking_service import get_sector_ranking

    return get_sector_ranking(weekly_db, daily_db, as_of=as_of, period=period)


def _composite_reference(weekly_db: str, daily_db: str, as_of: str):
    """기대값 원천 — 집계 경로의 composite 결과(period=None)."""
    from my_chart.analysis.sector_metrics import compute_sector_aggregates

    result = compute_sector_aggregates(weekly_db, as_of, daily_db, as_of=as_of, period=None)
    return {a.name: a for a in result.aggregates if a.rank is not None}


def test_sectors_rank_and_composite_equal_aggregate_composite(unify_dbs) -> None:
    """sectors[] 순위·composite == 집계 경로(순위 백분위) — min-max 였다면 OUT 이 1위다."""
    weekly_db, daily_db, as_of = unify_dbs
    ref = _composite_reference(weekly_db, daily_db, as_of)
    assert {n: a.rank for n, a in ref.items()} == {
        "LEAD": 1, "OUT": 2, "MID": 3, "LAG": 4}  # 픽스처 전제(순위 백분위 검산값)

    resp = _ranking(weekly_db, daily_db, as_of)
    got_rank = {s.name: s.rank for s in resp.sectors}
    got_comp = {s.name: s.composite_score for s in resp.sectors}
    assert got_rank == {n: a.rank for n, a in ref.items()}, f"sectors[] 순위: {got_rank}"
    assert got_comp == {n: round(a.composite_score.value, 2) for n, a in ref.items()}


def test_sectors_excess_returns_use_all_capped_benchmark(unify_dbs) -> None:
    """sectors[] 초과수익률 == data[] 초과수익률(ALL_CAPPED) — KOSPI 지수 행 기준이 아니다."""
    weekly_db, daily_db, as_of = unify_dbs
    resp = _ranking(weekly_db, daily_db, as_of)
    data = {a.name: a for a in resp.data}
    bench = resp.benchmark
    assert bench is not None and bench.name == "ALL_CAPPED"
    assert resp.sectors, "sectors[] 가 비었다"
    for s in resp.sectors:
        a = data[s.name]
        for key, p in (("w1", "1w"), ("m1", "1m"), ("m3", "3m")):
            assert getattr(s.excess_returns, key) == round(a.excess_returns[p].value, 4), (
                f"{s.name} {p}: sectors[] {getattr(s.excess_returns, key)} vs "
                f"data[] {a.excess_returns[p].value}")
            assert getattr(s.returns, key) == round(a.returns[p].value, 4)


def test_sectors_omit_unranked_sectors(unify_dbs) -> None:
    """AG-5 제외 섹터(SMALL)는 data[] 에 순위가 없으므로 sectors[] 에서도 빠진다."""
    weekly_db, daily_db, as_of = unify_dbs
    resp = _ranking(weekly_db, daily_db, as_of)
    ranked = {a.name for a in resp.data if a.rank is not None}
    assert {s.name for s in resp.sectors} == ranked == {"LEAD", "OUT", "MID", "LAG"}
    assert any(e.sector == "SMALL" for e in resp.excluded)


def test_sectors_stay_composite_when_period_is_set(unify_dbs) -> None:
    """period 지정 시 data[] 는 기간 순위, sectors[] 는 여전히 composite 순위다."""
    weekly_db, daily_db, as_of = unify_dbs
    ref = _composite_reference(weekly_db, daily_db, as_of)
    resp = _ranking(weekly_db, daily_db, as_of, period="3m")
    assert {a.name: a.rank for a in resp.data if a.rank is not None}["OUT"] == 1  # 3M 단독 1위
    assert {s.name: s.rank for s in resp.sectors} == {n: a.rank for n, a in ref.items()}


def test_sectors_rank_change_matches_composite_rank_change(unify_dbs) -> None:
    """sectors[].rank_change == 집계 경로 composite rank_change(None → 0, 스키마 int)."""
    weekly_db, daily_db, as_of = unify_dbs
    ref = _composite_reference(weekly_db, daily_db, as_of)
    resp = _ranking(weekly_db, daily_db, as_of)
    assert {s.name: s.rank_change for s in resp.sectors} == {
        n: (a.rank_change if a.rank_change is not None else 0) for n, a in ref.items()}


def test_bubble_sector_aggregate_equals_ranking_aggregate(unify_dbs, monkeypatch) -> None:
    """AC-SAG-042 — 버블 sector_aggregate == 같은 섹터·기간의 sectors[]/data[] 수익률.

    순위 대상이 아닌(AG-5 제외) 섹터는 랭킹에 행이 없으므로 기준선도 없다(None).
    """
    from backend.services import sector_advanced_service as svc

    weekly_db, daily_db, as_of = unify_dbs
    # 종목 버블 본체는 관심사가 아니다 — 기준선(sector_aggregate)만 검사한다.
    monkeypatch.setattr(svc, "compute_stock_bubble", lambda *a, **k: [])
    resp = _ranking(weekly_db, daily_db, as_of)
    lead = next(s for s in resp.sectors if s.name == "LEAD")

    bubble = svc.get_stock_bubble(weekly_db, "LEAD", period="1m", daily_db_path=daily_db)
    assert bubble.sector_aggregate == lead.returns.m1
    small = svc.get_stock_bubble(weekly_db, "SMALL", period="1m", daily_db_path=daily_db)
    assert small.sector_aggregate is None
