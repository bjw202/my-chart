# coding: utf-8
"""SPEC-SECTOR-GRID-001 M1 — weekly_grid 정규 주간 격자 TDD (RED).

AC-SGR-001/002/003/004/007/008 를 합성 픽스처 + 프로즌 스냅샷으로 단언한다.
합성 픽스처는 stock_prices(Name, Date) 최소 스키마로 구성하고, 게이팅 AC-SGR-001/002/007 은
tests/fixtures/frozen/weekly-2026-08-12/weekly.db (프로즌 스냅샷) 위에서 실행한다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from my_chart.analysis.weekly_grid import (
    GRID_VERSION,
    Anomaly,
    Exclusion,
    GridBar,
    HistorySlice,
    WeeklyGrid,
    anchor,
    compute_weekly_grid,
    history,
)

FROZEN = Path(__file__).parent / "fixtures" / "frozen" / "weekly-2026-08-12" / "weekly.db"

# SPEC v0.2.1 고정 예외 (A1 gap=5 정정). 전체 격자 5건 / history 4건.
A_FULL = {
    ("2020-04-24", "2020-04-29", 5),
    ("2020-09-25", "2020-09-29", 4),
    ("2021-02-05", "2021-02-10", 5),
    ("2023-09-22", "2023-09-27", 5),
    ("2026-08-07", "2026-08-11", 4),
}
A_HIST = A_FULL - {("2026-08-07", "2026-08-11", 4)}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path: Path, name: str, date_names: dict[str, list[str]]) -> str:
    """최소 stock_prices(Name, Date) DB 생성. date_names: {date: [name, ...]}."""
    db = tmp_path / name
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE stock_prices (Name TEXT NOT NULL, Date TEXT NOT NULL)")
    rows = [(n, d) for d, names in date_names.items() for n in names]
    conn.executemany("INSERT INTO stock_prices VALUES (?, ?)", rows)
    conn.commit()
    conn.close()
    return str(db)


def _week(n_names: int, prefix: str = "S") -> list[str]:
    return [f"{prefix}{i}" for i in range(n_names)]


# ---------------------------------------------------------------------------
# AC-SGR-001 — ISO 주당 1바, 대표 = MAX(Date) (불변식 TG-2)
# ---------------------------------------------------------------------------

def test_ac_sgr_001_synthetic_multidate_and_iso_boundary(tmp_path):
    """다중 날짜 주(2/3/4) + ISO 연도 경계(12/31↔01/01) → 주당 1바, 대표=MAX."""
    # 2020-W53: 12/31(목), 2021-01-01(금) → 같은 ISO 주, 대표 01-01
    # 4-날짜 주: 2021-01-05(화)~01-08(금) → 대표 01-08
    date_names = {
        "2020-12-31": _week(10), "2021-01-01": _week(10),          # ISO 2020-W53
        "2021-01-05": _week(10), "2021-01-06": _week(10),
        "2021-01-07": _week(10), "2021-01-08": _week(10),          # ISO 2021-W01 (4 dates)
        "2021-01-12": _week(10), "2021-01-13": _week(10),
        "2021-01-14": _week(10),                                    # ISO 2021-W02 (3 dates)
        "2021-01-19": _week(10), "2021-01-20": _week(10),          # ISO 2021-W03 (2 dates)
    }
    db = _make_db(tmp_path, "multi.db", date_names)
    grid = compute_weekly_grid(db, as_of="2021-02-01")

    # ISO 주당 정확히 1바
    seen_weeks = [date.fromisoformat(d).isocalendar()[:2] for d in grid.dates]
    assert len(seen_weeks) == len(set(seen_weeks)), "ISO 주당 2바 이상 존재"

    by_week = {date.fromisoformat(d).isocalendar()[:2]: d for d in grid.dates}
    assert by_week[(2020, 53)] == "2021-01-01"          # 12/31·01/01 → MAX=01-01
    assert by_week[(2021, 1)] == "2021-01-08"           # 4-날짜 주 → MAX=01-08
    assert by_week[(2021, 2)] == "2021-01-14"           # 3-날짜 주
    assert by_week[(2021, 3)] == "2021-01-20"           # 2-날짜 주
    assert grid.grid_version == GRID_VERSION == "canonical-v1"


def test_ac_sgr_001_frozen_rep_dates():
    """프로즌 픽스처: W32→2026-08-07, W28→2026-07-10, W27→2026-07-03."""
    grid = compute_weekly_grid(str(FROZEN), as_of="2026-08-12")
    by_week = {date.fromisoformat(d).isocalendar()[:2]: d for d in grid.dates}
    assert by_week[(2026, 32)] == "2026-08-07"
    assert by_week[(2026, 28)] == "2026-07-10"
    assert by_week[(2026, 27)] == "2026-07-03"
    assert len(grid.dates) == 346


# ---------------------------------------------------------------------------
# AC-SGR-002 — 인접 바 간격 6–10일, 범위 밖은 anomalies 에 집합 동등 기록 (불변식 TG-3)
# ---------------------------------------------------------------------------

def _out_of_range_pairs(dates: list[str]) -> set[tuple[str, str, int]]:
    out = set()
    for a, b in zip(dates, dates[1:]):
        g = (date.fromisoformat(b) - date.fromisoformat(a)).days
        if not (6 <= g <= 10):
            out.add((a, b, g))
    return out


def test_ac_sgr_002_frozen_anomalies_set_equality():
    """프로즌: 전체 anomalies == A1..A5, history anomalies == A1..A4 (집합 동등)."""
    grid = compute_weekly_grid(str(FROZEN), as_of="2026-08-12")

    got_full = {(a.from_date, a.to_date, a.gap_days) for a in grid.anomalies}
    assert got_full == A_FULL, f"전체 격자 anomalies 불일치: {got_full}"

    # A5(진행 중인 주)는 history 에 미출현 → history anomalies = A1..A4
    hist_dates = [b.date for b in grid.history]
    got_hist = _out_of_range_pairs(hist_dates)
    assert got_hist == A_HIST, f"history anomalies 불일치: {got_hist}"

    # 대조 단언(반증 가능성): anomalies 는 범위 밖 쌍을 하나도 빠짐없이 기록한다.
    # 기록을 비운 변형이라면 이 동등식이 성립하지 않는다(즉 게이트가 의미 있음).
    assert got_full == _out_of_range_pairs(grid.dates)
    # 범위 밖 바가 격자에서 제외되지 않는다 (len 감소 0)
    assert len(grid.dates) == 346
    assert len(hist_dates) == 345


# ---------------------------------------------------------------------------
# AC-SGR-003 — 진행 중인 주 플래그 + 두 뷰 분리
# ---------------------------------------------------------------------------

def test_ac_sgr_003_partial_week_flag_and_views(tmp_path):
    """최신 주 화요일 종료·금요일 바 부재 → is_partial=True, history 는 직전 완결 주."""
    # W33(2026-08-10..08-16): 월(08-10), 화(08-11) 만 있고 금요일(08-14) 바 없음
    # 직전 완결 주 W32: 금요일 08-07
    date_names = {
        "2026-07-31": _week(10), "2026-08-07": _week(10),   # W31, W32 (완결)
        "2026-08-10": _week(10), "2026-08-11": _week(10),   # W33 (진행 중)
    }
    db = _make_db(tmp_path, "partial.db", date_names)
    grid = compute_weekly_grid(db, as_of="2026-08-12")     # 수요일 → W33 미종료

    assert grid.latest.date == "2026-08-11"
    assert grid.latest.is_partial_week is True
    assert grid.latest.partial_week_trading_days == 2       # 08-10, 08-11
    # history 마지막은 직전 완결 주 대표(08-07), 화요일(08-11) 아님
    assert grid.history[-1].date == "2026-08-07"
    assert "2026-08-11" not in [b.date for b in grid.history]
    # latest(08-11) 는 dates 에 포함(스냅샷은 미완성 포함)
    assert "2026-08-11" in grid.dates


def test_ac_sgr_003_completed_week_not_partial(tmp_path):
    """최신 주에 금요일 바가 있으면 is_partial=False, 두 뷰의 마지막이 동일."""
    date_names = {
        "2026-07-31": _week(10), "2026-08-07": _week(10),
        "2026-08-10": _week(10), "2026-08-14": _week(10),   # W33 금요일 바 존재
    }
    db = _make_db(tmp_path, "complete.db", date_names)
    grid = compute_weekly_grid(db, as_of="2026-08-20")      # 주 종료 이후

    assert grid.latest.date == "2026-08-14"
    assert grid.latest.is_partial_week is False
    assert grid.history[-1].date == grid.latest.date


def test_ac_sgr_003_partial_when_week_not_ended(tmp_path):
    """E4: 판정은 요일이 아니라 '금요일 바 부재 + 주 미종료'. 주가 종료됐으면 partial 아님."""
    # W33 금요일 바 없지만 as_of 가 주 종료(08-16) 이후 → partial 아님
    date_names = {"2026-08-10": _week(10), "2026-08-11": _week(10)}
    db = _make_db(tmp_path, "ended.db", date_names)
    grid = compute_weekly_grid(db, as_of="2026-08-20")
    assert grid.latest.is_partial_week is False


# ---------------------------------------------------------------------------
# AC-SGR-004 — 부분 데이터 날짜 배제 (CG-3)
# ---------------------------------------------------------------------------

def test_ac_sgr_004_partial_data_exclusion_and_boundary(tmp_path):
    """중앙값 50% 미만 대표 바 배제 + exclusions 기록; 정확히 50% 경계는 포함(>=)."""
    # 6 주(금요일), 각 주 단일 날짜 → 대표 바. 행 수: 10,10,10,10,1,5
    fridays = ["2026-07-03", "2026-07-10", "2026-07-17", "2026-07-24",
               "2026-07-31", "2026-08-07"]
    counts = [10, 10, 10, 10, 1, 5]
    date_names = {d: _week(c, prefix=d.replace("-", "")) for d, c in zip(fridays, counts)}
    db = _make_db(tmp_path, "partial_data.db", date_names)
    grid = compute_weekly_grid(db, as_of="2026-12-31")     # partial 개입 방지

    # 중앙값 = 10, 임계 = 5. 07-31(1) 배제, 08-07(5)=경계 포함
    dates_in = set(grid.dates)
    assert "2026-07-31" not in dates_in                     # 1 < 5 → 배제
    assert "2026-08-07" in dates_in                         # 5 >= 5 → 경계 포함
    excl = {e.date: e.row_count for e in grid.exclusions}
    assert excl == {"2026-07-31": 1}
    assert len(grid.dates) == 5                             # 4 full + 1 경계


# ---------------------------------------------------------------------------
# AC-SGR-007 — 달력 앵커링: 364일 = 52±1 바 (불변식 TG-1)
# ---------------------------------------------------------------------------

def test_ac_sgr_007_frozen_52_bars_and_anchor():
    """프로즌: 최근 364일 = 52±1 바; anchor(t,Nd) ≤ t-Nd 최근 격자 바."""
    grid = compute_weekly_grid(str(FROZEN), as_of="2026-08-12")
    t = "2026-08-07"
    t_d = date.fromisoformat(t)

    window = [b for b in grid.history
              if (t_d - date.fromisoformat(b.date)).days <= 364]
    assert 51 <= len(window) <= 53, f"364일 창 바 수: {len(window)}"

    for days in (7, 28, 91, 182, 364):
        bar = anchor(grid, t, days)
        assert bar is not None
        bd = date.fromisoformat(bar.date)
        # 반환바 ≤ t-Nd (초과 금지) 이고 history 원소
        assert bd <= t_d - timedelta(days=days)
        assert bar.date in [h.date for h in grid.history]

    # anchor(t,28) 은 LIMIT 1 OFFSET 3 의 2026-07-31 이 아니라 t-28d 이하 최근 바
    a28 = anchor(grid, t, 28)
    delta = (t_d - date.fromisoformat(a28.date)).days
    assert 28 <= delta <= 35                                # AC-SGR-020 R2 양측 경계


# ---------------------------------------------------------------------------
# AC-SGR-008 — weeks=N 의미: N 개 정규 바 (불변식 TG-4)
# ---------------------------------------------------------------------------

def test_ac_sgr_008_weeks_meaning_frozen():
    """프로즌: history(weeks=N) → 정확히 N 바; N=12 span ∈[77,91]; 과요청 시 returned<requested."""
    grid = compute_weekly_grid(str(FROZEN), as_of="2026-08-12")

    for n in (8, 12, 26):
        sl = history(grid, n)
        assert isinstance(sl, HistorySlice)
        assert len(sl.bars) == n, f"N={n} 반환 바 수: {len(sl.bars)}"
        assert sl.requested_weeks == n and sl.returned_weeks == n
        span = (date.fromisoformat(sl.bars[-1].date)
                - date.fromisoformat(sl.bars[0].date)).days
        assert 7 * (n - 1) - 7 <= span <= 7 * n + 7

    # N=12 span 은 84±7 (AC-SGR-020 R1)
    sl12 = history(grid, 12)
    span12 = (date.fromisoformat(sl12.bars[-1].date)
              - date.fromisoformat(sl12.bars[0].date)).days
    assert 77 <= span12 <= 91

    # 가용 이력(345) 보다 큰 N 요청 → 가용한 만큼 + returned<requested (조용한 축소 금지)
    big = history(grid, 9999)
    assert big.returned_weeks == len(grid.history) < big.requested_weeks


# ---------------------------------------------------------------------------
# Edge: 빈 DB (E1)
# ---------------------------------------------------------------------------

def test_edge_empty_db(tmp_path):
    db = _make_db(tmp_path, "empty.db", {})
    grid = compute_weekly_grid(db, as_of="2026-08-12")
    assert grid.dates == []
    assert grid.history == []
    assert grid.latest is None
