"""Bump 잠정점: 진행 중인 주(부분 주)의 순위를 히스토리 끝에 한 점 더 싣는다.

버그(2026-10-22 라이브): 섹터 표(/sectors/ranking)는 진행 중인 주 바(as_of 2026-10-21,
``as_of_is_partial_week=true``)로 순위를 매기는데, Bump(/sectors/history)는 정규 격자
``history``(끝난 주만)를 써서 마지막 점이 2026-10-16 이었다 — 표와 Bump 의 마지막 순위가 달랐다.

기대 동작(사용자 결정): 최신 격자 바가 부분 주면 히스토리 응답이 그 날짜의 순위를 **잠정점**
하나로 덧붙인다. 잠정점 순위 == 같은 기준일·기간·시장의 표 ``data[].rank``(전 섹터 집합 일치).
최신 주가 끝났으면 잠정점이 없다. ``dates[]``/``rankings``/``span_days`` 는 끝난 주만 담는다
(AC-SAG-040 ``len(dates) == weeks`` 유지).

픽스처: 4섹터 × 5종목, 금요일 16주 + 마지막 금요일 다음 주 수요일 바 1개(금요일 바 없음 → CG-2 부분 주).
    1M 앵커는 두 기준일 모두 2024-03-22(종가 100).
    마지막 금요일 종가: A 110 / B 105 / C 100 / D 95  → 1M 순위 A1 B2 C3 D4
    수요일 종가      : A 90  / B 100 / C 120 / D 130 → 1M 순위 D1 C2 B3 A4 (뒤집힘)
as_of 는 §8.4 규약 8 에 따라 명시 인자로 고정한다(오늘 날짜에 기대지 않는다).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from tests.rsr_fixtures import make_weekly_db, price_row

_SECTORS = ("A", "B", "C", "D")
_MEMBERS = 5
_N_FRIDAYS = 16
_FIRST_FRIDAY = date(2024, 1, 5)
_FRIDAYS = [(_FIRST_FRIDAY + timedelta(weeks=i)).isoformat() for i in range(_N_FRIDAYS)]
_LAST_FRIDAY = _FRIDAYS[-1]                                              # 2024-04-19
_WED = (date.fromisoformat(_LAST_FRIDAY) + timedelta(days=5)).isoformat()  # 2024-04-24
_AS_OF_PARTIAL = _WED                                   # 주 진행 중(일요일 2024-04-28 이전)
_AS_OF_COMPLETE = "2024-04-29"                          # 그 주 일요일 이후 → 끝난 주
_FRI_CLOSE = {"A": 110.0, "B": 105.0, "C": 100.0, "D": 95.0}
_WED_CLOSE = {"A": 90.0, "B": 100.0, "C": 120.0, "D": 130.0}
_CAP = 1_000_000_000_000.0
_WEEKS = 8


@pytest.fixture
def partial_week_dbs(tmp_path: Path, monkeypatch) -> tuple[str, str]:
    names = {s: [f"{s}{i}" for i in range(_MEMBERS)] for s in _SECTORS}
    all_dates = [*_FRIDAYS, _WED]
    rows: list[tuple] = []
    rs_rows: list[tuple] = []
    for s in _SECTORS:
        closes = [100.0] * _N_FRIDAYS + [_WED_CLOSE[s]]
        closes[_N_FRIDAYS - 1] = _FRI_CLOSE[s]
        for n in names[s]:
            for d, c in zip(all_dates, closes):
                rows.append(price_row(n, d, Close=c, High=c, Low=c, Open=c))
                rs_rows.append((n, d, 50.0, 50.0, 50.0, 50.0))
    weekly_db = make_weekly_db(tmp_path, rows, rs_rows) + ".db"

    daily_db = str(tmp_path / "daily.db")
    conn = sqlite3.connect(daily_db)
    try:
        conn.execute("CREATE TABLE stock_meta (name TEXT PRIMARY KEY, market_cap REAL)")
        conn.execute("CREATE TABLE stock_prices (Name TEXT, Date TEXT, VolumeWon REAL)")
        flat = [n for ns in names.values() for n in ns]
        conn.executemany("INSERT INTO stock_meta VALUES (?, ?)", [(n, _CAP) for n in flat])
        conn.executemany("INSERT INTO stock_prices VALUES (?, ?, ?)",
                         [(n, d, 1.0e9) for n in flat for d in all_dates])
        conn.commit()
    finally:
        conn.close()

    registry = pd.DataFrame([
        {"Code": f"{i:06d}", "Name": n, "Market": "KOSPI", "산업명(대)": s,
         "산업명(중)": s, "주요제품": "-"}
        for i, (s, n) in enumerate((s, n) for s, ns in names.items() for n in ns)
    ])
    monkeypatch.setattr("my_chart.registry._load_sectormap", lambda *a, **k: registry.copy())
    monkeypatch.setattr("my_chart.registry._df_sector", None)
    # 유효 유니버스(UN-3)는 라이브 registry xlsx 를 읽는다 — 관심사 밖이라 제한 없음으로 고정.
    monkeypatch.setattr(
        "my_chart.analysis.sector_metrics._valid_universe", lambda *a, **k: None)
    return weekly_db, daily_db


def _table_ranks(weekly_db: str, daily_db: str, as_of: str) -> tuple[str, bool | None, dict]:
    from backend.services.sector_ranking_service import get_sector_ranking

    resp = get_sector_ranking(weekly_db, daily_db, as_of=as_of, market="all", period="1m")
    ranks = {a.name: a.rank for a in resp.data if a.rank is not None}
    return resp.as_of_date, resp.as_of_is_partial_week, ranks


def _history(weekly_db: str, daily_db: str, as_of: str):
    from backend.services.sector_advanced_service import get_sector_history

    return get_sector_history(
        weekly_db, weeks=_WEEKS, daily_db_path=daily_db, market="all", period="1m", as_of=as_of)


def test_provisional_point_ranks_equal_table_ranks_when_partial_week(partial_week_dbs) -> None:
    weekly_db, daily_db = partial_week_dbs
    table_date, partial, table = _table_ranks(weekly_db, daily_db, _AS_OF_PARTIAL)
    assert (table_date, partial) == (_WED, True)            # 픽스처 전제: 표는 부분 주 바로 순위
    assert table == {"D": 1, "C": 2, "B": 3, "A": 4}

    resp = _history(weekly_db, daily_db, _AS_OF_PARTIAL)

    assert resp.provisional_date == _WED
    provisional = {}
    for s in resp.sectors:
        last = s.history[-1]
        assert last.provisional is True and last.date == _WED, s.name
        assert all(w.provisional is False for w in s.history[:-1]), s.name
        provisional[s.name] = last.rank
    assert provisional == table, f"잠정점 {provisional} != 표 {table}"


def test_provisional_point_stays_out_of_dates_rankings_span(partial_week_dbs) -> None:
    """끝난 주 계약(AC-SAG-040) 유지 — 잠정 날짜는 dates[]/rankings/span_days 에 들어가지 않는다."""
    weekly_db, daily_db = partial_week_dbs
    resp = _history(weekly_db, daily_db, _AS_OF_PARTIAL)
    assert len(resp.dates) == _WEEKS
    assert resp.dates[-1] == _LAST_FRIDAY
    assert _WED not in resp.rankings
    assert resp.span_days == 7 * (_WEEKS - 1)
    # 마지막 끝난 주 점은 그대로(금요일 순위 A1 B2 C3 D4)
    assert {n: r for n, r in resp.rankings[_LAST_FRIDAY].items() if r is not None} == {
        "A": 1, "B": 2, "C": 3, "D": 4}


def test_no_provisional_point_when_latest_week_complete(partial_week_dbs) -> None:
    weekly_db, daily_db = partial_week_dbs
    table_date, partial, table = _table_ranks(weekly_db, daily_db, _AS_OF_COMPLETE)
    assert (table_date, partial) == (_WED, False)

    resp = _history(weekly_db, daily_db, _AS_OF_COMPLETE)

    assert resp.provisional_date is None
    assert all(w.provisional is False for s in resp.sectors for w in s.history)
    assert resp.dates[-1] == _WED                     # 끝난 주가 됐으므로 정규 히스토리 점
    last = {n: r for n, r in resp.rankings[_WED].items() if r is not None}
    assert last == table
