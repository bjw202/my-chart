"""재현 테스트: Bump(섹터 히스토리) 순위 ≠ 섹터 표 순위.

버그: ``compute_sector_history`` 가 레거시 ``compute_sector_ranking`` 경로를 타서 composite 를
      **min-max** 정규화(``_normalize_list``)로 계산한다. 섹터 표는
      ``compute_sector_aggregates`` → ``_rank_sectors`` 의 **순위 백분위**(AG-8 ``norm``)를 쓴다.
      가중치(1W 0.30 / 1M 0.40 / 3M 0.30)는 같지만 정규화가 달라, 3M 초과수익률이 극단값인
      섹터가 Bump 에서만 1위로 뛰어오른다(라이브 2026-10-16 비철금속: Bump 1위, 표 5위).

기대 동작(사용자 결정): **표에서 제외된 섹터가 없을 때** Bump 의 각 날짜 d 순위 ==
``compute_sector_aggregates(weekly, d, daily, as_of=d, period=None)`` 순위.

AC-SUX-019(Bump 는 AG-5 미적용): 표에서 AG-5(구성종목 < 5)·AG-4(유효 시총 < 5)로 빠진
섹터도 Bump 에서는 등가중 수익률 − 벤치마크로 순위를 받는다(전 섹터 같은 순위 백분위
composite). 이때 Bump 의 순위 분모는 표보다 크다 — 하단 ``exclusion_dbs`` 테스트 참조.

픽스처 설계(손으로 검산한 불일치):
    섹터별 수익률(%) — 구성종목 5개 모두 동일 경로, 시총 동일
        OUT(극단값): 1W 1.5 / 1M 2.5 / 3M 60
        LEAD       : 1W 2.0 / 1M 3.0 / 3M 5
        MID        : 1W 1.0 / 1M 2.0 / 3M 4
        LAG        : 1W -1  / 1M -1  / 3M 0
    순위 백분위 composite: LEAD 90.0 > OUT 76.7 → LEAD 1위
    min-max composite   : OUT 90.0 > LEAD 72.5 → OUT 1위 (버그)
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from my_chart.analysis.sector_metrics import compute_sector_aggregates, compute_sector_history
from tests.rsr_fixtures import make_weekly_db, price_row

# 섹터 → (1W, 1M, 3M) 수익률(%)
_SECTOR_RETURNS: dict[str, tuple[float, float, float]] = {
    "OUT": (1.5, 2.5, 60.0),
    "LEAD": (2.0, 3.0, 5.0),
    "MID": (1.0, 2.0, 4.0),
    "LAG": (-1.0, -1.0, 0.0),
}
_MEMBERS_PER_SECTOR = 5          # MIN_SECTOR_MEMBERS(AG-5) 충족
_N_WEEKS = 16                    # 마지막 3개 날짜가 3M(91일) 앵커를 가진다
_FIRST_FRIDAY = date(2024, 1, 5)


def _dates() -> list[str]:
    return [(_FIRST_FRIDAY + timedelta(weeks=i)).isoformat() for i in range(_N_WEEKS)]


def _close_path(r1w: float, r1m: float, r3m: float) -> list[float]:
    """마지막 날짜 t 기준 anchor(t,7/28/91) 수익률이 정확히 (r1w, r1m, r3m) 이 되는 종가 경로."""
    final = 100.0 * (1 + r3m / 100)
    closes = [100.0] * _N_WEEKS
    closes[-1] = final
    closes[-2] = final / (1 + r1w / 100)     # t − 1주
    closes[-5] = final / (1 + r1m / 100)     # t − 4주
    closes[-14] = 100.0                      # t − 13주(3M 앵커)
    return closes


_CAP = 1_000_000_000_000.0


def _build_dbs(
    tmp_path: Path,
    monkeypatch,
    sector_returns: dict[str, tuple[float, float, float]],
    members: dict[str, int] | None = None,
    cap_by_sector: dict[str, float | None] | None = None,
) -> tuple[str, str]:
    """(weekly_db, daily_db) 를 만든다. 섹터별 구성종목 수·시총(None → NULL)을 덮어쓸 수 있다."""
    members = members or {}
    cap_by_sector = cap_by_sector or {}
    dates = _dates()
    names_by_sector = {
        s: [f"{s}{i}" for i in range(members.get(s, _MEMBERS_PER_SECTOR))]
        for s in sector_returns
    }
    rows: list[tuple] = []
    rs_rows: list[tuple] = []
    for sector, (r1w, r1m, r3m) in sector_returns.items():
        closes = _close_path(r1w, r1m, r3m)
        for name in names_by_sector[sector]:
            for d, c in zip(dates, closes):
                rows.append(price_row(name, d, Close=c, High=c, Low=c, Open=c))
                rs_rows.append((name, d, 50.0, 50.0, 50.0, 50.0))
    weekly_db = make_weekly_db(tmp_path, rows, rs_rows) + ".db"

    daily_db = str(tmp_path / "daily.db")
    conn = sqlite3.connect(daily_db)
    try:
        conn.execute("CREATE TABLE stock_meta (name TEXT PRIMARY KEY, market_cap REAL)")
        conn.execute("CREATE TABLE stock_prices (Name TEXT, Date TEXT, VolumeWon REAL)")
        all_names = [n for ns in names_by_sector.values() for n in ns]
        conn.executemany("INSERT INTO stock_meta VALUES (?, ?)",
                         [(n, cap_by_sector.get(s, _CAP))
                          for s, ns in names_by_sector.items() for n in ns])
        conn.executemany("INSERT INTO stock_prices VALUES (?, ?, ?)",
                         [(n, d, 1.0e9) for n in all_names for d in dates])
        conn.commit()
    finally:
        conn.close()

    registry = pd.DataFrame([
        {"Code": f"{i:06d}", "Name": n, "Market": "KOSPI", "산업명(대)": s,
         "산업명(중)": s, "주요제품": "-"}
        for i, (s, n) in enumerate(
            (s, n) for s, ns in names_by_sector.items() for n in ns)
    ])
    monkeypatch.setattr("my_chart.registry._load_sectormap", lambda *a, **k: registry.copy())
    monkeypatch.setattr("my_chart.registry._df_sector", None)
    # 유효 유니버스(UN-3)는 라이브 registry xlsx 를 읽는다 — 이 테스트의 관심사가 아니므로
    # 제한 없음(None)으로 고정한다(daily DB 가 없을 때의 프로덕션 동작과 같다).
    monkeypatch.setattr(
        "my_chart.analysis.sector_metrics._valid_universe", lambda *a, **k: None)
    return weekly_db, daily_db


@pytest.fixture
def alignment_dbs(tmp_path: Path, monkeypatch) -> tuple[str, str]:
    """(weekly_db, daily_db) — 4섹터 × 5종목, 16주, 시총 동일. **제외 섹터 없음.**"""
    return _build_dbs(tmp_path, monkeypatch, _SECTOR_RETURNS)


# 제외 섹터가 있는 픽스처(AC-SUX-019): 표에서는 빠지지만 Bump 에는 선이 있어야 하는 두 섹터.
#   SMALL  — 구성종목 4개(AG-5 미달 → 표 excluded `insufficient_members`, AG-4 도 미달)
#   NOCAP  — 구성종목 5개지만 시총 전부 NULL(AG-4 미달 → 시총가중 null → 표 순위 제외)
_EXCLUSION_RETURNS: dict[str, tuple[float, float, float]] = {
    **_SECTOR_RETURNS,
    "SMALL": (3.0, 4.0, 6.0),
    "NOCAP": (0.0, 0.0, 1.0),
}


@pytest.fixture
def exclusion_dbs(tmp_path: Path, monkeypatch) -> tuple[str, str]:
    return _build_dbs(tmp_path, monkeypatch, _EXCLUSION_RETURNS,
                      members={"SMALL": 4}, cap_by_sector={"NOCAP": None})


def _table_ranks(weekly_db: str, daily_db: str, d: str) -> dict[str, int]:
    result = compute_sector_aggregates(
        weekly_db, d, daily_db, as_of=d, compute_rank_change=False, period=None)
    return {a.name: a.rank for a in result.aggregates if a.rank is not None}


def test_history_last_date_outlier_does_not_jump_to_rank_1(alignment_dbs) -> None:
    """3M 극단값 섹터(OUT)는 표와 같이 2위여야 한다 — min-max 였다면 1위로 뛴다."""
    weekly_db, daily_db = alignment_dbs
    dates, rankings = compute_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db)
    last = {r.name: r.rank for r in rankings[-1]}

    assert _table_ranks(weekly_db, daily_db, dates[-1]) == {
        "LEAD": 1, "OUT": 2, "MID": 3, "LAG": 4}  # 픽스처 전제(순위 백분위 검산값)
    assert last == _table_ranks(weekly_db, daily_db, dates[-1]), (
        f"Bump 마지막 날짜 순위가 표 순위와 다름: {last}")


def test_history_ranks_equal_table_ranks_for_every_date(alignment_dbs) -> None:
    """모든 히스토리 날짜에서 Bump 순위 == compute_sector_aggregates(period=None) 순위."""
    weekly_db, daily_db = alignment_dbs
    dates, rankings = compute_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db)
    assert len(dates) == len(rankings) > 0
    for d, week in zip(dates, rankings):
        got = {r.name: r.rank for r in week}
        assert got == _table_ranks(weekly_db, daily_db, d), f"{d}: Bump {got}"


def test_history_composite_score_matches_table(alignment_dbs) -> None:
    """Bump 툴팁의 composite_score 도 표의 composite_score 와 같은 값이어야 한다."""
    weekly_db, daily_db = alignment_dbs
    dates, rankings = compute_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db)
    table = compute_sector_aggregates(
        weekly_db, dates[-1], daily_db, as_of=dates[-1], compute_rank_change=False)
    expected = {a.name: a.composite_score.value for a in table.aggregates if a.rank is not None}
    # 반환 원소 타입은 무관하게 composite 의 수치만 비교한다(float / MetricValue).
    got = {r.name: getattr(r.composite_score, "value", r.composite_score) for r in rankings[-1]}
    assert got == pytest.approx(expected)


def test_history_computes_universe_once_per_call(alignment_dbs, monkeypatch) -> None:
    """날짜 무관 입력(유효 유니버스 — registry xlsx 재독)은 히스토리 호출당 1회만 계산한다.

    날짜마다 다시 계산하면 라이브에서 날짜당 ~0.5초가 더 든다(8주 16초 사례).
    """
    calls: list[tuple] = []

    def _counting(*args, **kwargs):
        calls.append(args)
        return None

    monkeypatch.setattr("my_chart.analysis.sector_metrics._valid_universe", _counting)
    weekly_db, daily_db = alignment_dbs
    dates, _rankings = compute_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db)
    assert len(dates) == _N_WEEKS
    assert len(calls) == 1, f"유효 유니버스가 {len(calls)}회 계산됨(기대 1회)"


# --- AC-SUX-019: Bump 는 AG-5 를 적용하지 않는다(표 excluded[] 섹터도 선이 있다) ----------
#
# 손 검산(6섹터, 순위 백분위는 순위에 단조이므로 순위 위치로 계산 — 6=최고):
#   1W: SMALL 3 > LEAD 2 > OUT 1.5 > MID 1 > NOCAP 0 > LAG -1
#   1M: SMALL 4 > LEAD 3 > OUT 2.5 > MID 2 > NOCAP 0 > LAG -1
#   3M: OUT 60 > SMALL 6 > LEAD 5 > MID 4 > NOCAP 1 > LAG 0
#   composite(0.3/0.4/0.3): SMALL 5.7 > LEAD 4.7 > OUT 4.6 > MID 3 > NOCAP 2 > LAG 1
#   (벤치마크는 모든 섹터에 같은 값을 빼므로 초과수익률 순서 = 수익률 순서)
_EXPECTED_BUMP_RANKS_WITH_EXCLUSIONS = {
    "SMALL": 1, "LEAD": 2, "OUT": 3, "MID": 4, "NOCAP": 5, "LAG": 6}


def test_table_still_excludes_small_and_nocap_sectors(exclusion_dbs) -> None:
    """대체(등가중) 경로가 표(data[])로 새지 않는다 — 표는 AG-5/AG-4 를 그대로 적용한다."""
    weekly_db, daily_db = exclusion_dbs
    d = _dates()[-1]
    result = compute_sector_aggregates(
        weekly_db, d, daily_db, as_of=d, compute_rank_change=False, period=None)
    assert _table_ranks(weekly_db, daily_db, d) == {"LEAD": 1, "OUT": 2, "MID": 3, "LAG": 4}
    assert "SMALL" not in {a.name for a in result.aggregates}
    excluded = {e.sector: e.reason for e in result.excluded}
    assert excluded.get("SMALL") == "insufficient_members"
    assert excluded.get("NOCAP") == "excess_return_missing"


def test_history_ranks_sectors_excluded_from_table(exclusion_dbs) -> None:
    """AG-5(구성종목 < 5)·AG-4(유효 시총 < 5) 로 표에서 빠진 섹터도 Bump 순위를 가진다."""
    weekly_db, daily_db = exclusion_dbs
    dates, rankings = compute_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db)
    last = {r.name: r.rank for r in rankings[-1]}
    assert last == _EXPECTED_BUMP_RANKS_WITH_EXCLUSIONS, f"Bump 마지막 날짜 순위: {last}"


def test_get_sector_history_includes_excluded_sectors_and_envelope_excluded_empty(
    exclusion_dbs,
) -> None:
    """API 응답 sectors[] 에 SMALL·NOCAP 선이 있고, 히스토리 봉투 excluded[] 는 비어 있다."""
    from backend.services.sector_advanced_service import get_sector_history

    weekly_db, daily_db = exclusion_dbs
    resp = get_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db)
    names = {s.name for s in resp.sectors}
    assert {"SMALL", "NOCAP"} <= names, f"sectors[]: {sorted(names)}"
    assert resp.excluded == []
    last = resp.dates[-1]
    assert resp.rankings[last]["SMALL"] == 1


# --- 기간 순위(표의 1W/1M/3M 탭과 같은 기준) ----------------------------------------
# 사용자 결정(2026-10-21): Bump 는 표와 같은 기준으로 순위를 매긴다 — 기간 탭을 주면 그 기간의
# 초과수익률 단독 순위(AC-SAG-021)를 쓴다. period 를 주지 않으면 종전 composite 순위를 유지한다.

def _table_period_ranks(weekly_db: str, daily_db: str, d: str, period: str) -> dict[str, int]:
    result = compute_sector_aggregates(
        weekly_db, d, daily_db, as_of=d, compute_rank_change=False, period=period)
    return {a.name: a.rank for a in result.aggregates if a.rank is not None}


@pytest.mark.parametrize("period", ["1w", "1m", "3m"])
def test_history_period_ranks_equal_table_period_ranks(alignment_dbs, period: str) -> None:
    """모든 히스토리 날짜에서 Bump(period) 순위 == 표의 같은 period 순위."""
    weekly_db, daily_db = alignment_dbs
    dates, rankings = compute_sector_history(
        weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db, period=period)
    assert len(dates) == len(rankings) > 0
    for d, week in zip(dates, rankings):
        got = {r.name: r.rank for r in week}
        assert got == _table_period_ranks(weekly_db, daily_db, d, period), (
            f"{period} {d}: Bump {got}")


def test_history_3m_period_puts_outlier_first(alignment_dbs) -> None:
    """3M 기준이면 3M 60% 섹터(OUT)가 1위 — composite 기준(LEAD 1위)과 갈리는 대조."""
    weekly_db, daily_db = alignment_dbs
    _dates, rankings = compute_sector_history(
        weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db, period="3m")
    assert {r.name: r.rank for r in rankings[-1]} == {"OUT": 1, "LEAD": 2, "MID": 3, "LAG": 4}


def test_service_history_period_passthrough(alignment_dbs) -> None:
    """서비스 응답이 period 를 되돌려 주고, 순위 기준 초과수익률을 주별로 싣는다."""
    from backend.services.sector_advanced_service import get_sector_history

    weekly_db, daily_db = alignment_dbs
    resp = get_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db, period="3m")
    assert resp.period == "3m"
    last = resp.dates[-1]
    assert {n: r for n, r in resp.rankings[last].items() if r is not None} == {
        "OUT": 1, "LEAD": 2, "MID": 3, "LAG": 4}
    table = compute_sector_aggregates(
        weekly_db, last, daily_db, as_of=last, compute_rank_change=False, period="3m")
    expected = {a.name: a.excess_returns["3m"].value for a in table.aggregates if a.rank is not None}
    got = {s.name: s.history[-1].rank_basis_excess_return for s in resp.sectors}
    assert got == pytest.approx(expected)


def test_service_history_default_is_composite(alignment_dbs) -> None:
    """period 미지정이면 종전대로 composite 순위이고 기간 초과수익률 필드는 비어 있다."""
    from backend.services.sector_advanced_service import get_sector_history

    weekly_db, daily_db = alignment_dbs
    resp = get_sector_history(weekly_db, weeks=_N_WEEKS, daily_db_path=daily_db)
    assert resp.period is None
    last = resp.dates[-1]
    assert resp.rankings[last]["LEAD"] == 1
    assert all(w.rank_basis_excess_return is None for s in resp.sectors for w in s.history)
