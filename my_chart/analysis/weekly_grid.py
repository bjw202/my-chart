# coding: utf-8
"""SPEC-SECTOR-GRID-001 정규 주간 격자(canonical weekly grid) 모듈.

주봉 ``stock_prices`` 의 원시 날짜(다중 날짜 주·부분 데이터 날짘 포함)를 정규화해
ISO 주당 정확히 1개의 대표 바를 갖는 격자를 산출한다. 모든 기준일 소비자(M5 가 7개
모듈을 이 함수로 수렴)의 단일 원천(SSOT).

규칙:
  * CG-1: ISO 주(연, 주)당 1바, 대표 날짜 = 그 주 원시 날짜의 ``MAX(Date)``.
  * CG-2: 최신 주가 금요일 바 없이 아직 종료되지 않았으면 ``is_partial_week=True``.
          ``latest_snapshot`` 은 미완성 바를 포함, ``history`` 는 제외.
  * CG-3: 대표 바 후보의 행 수가 (조회 구간 대표 바 행 수 중앙값 × 50%) 미만이면
          격자에서 배제하고 ``exclusions`` 에 기록.

SQL ``strftime('%W')`` 는 ISO 주 규칙과 달라 사용 금지 — Python
``date.isocalendar()[:2]`` 로 그룹핑한다(SPEC-SECTOR-GRID-001 plan §3.1).
"""
from __future__ import annotations

import os
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

GRID_VERSION = "canonical-v1"
# @MX:NOTE: [AUTO] 격자 규칙(CG-1/CG-2/CG-3) 변경 시 본 버전 상수를 갱신해야 한다
#   (SPEC-SECTOR-GRID-001 SN-5 캐시 무효화 키). 프로즌 픽스처 기대값도 함께 재검토.

# 달력 앵커링 기간표(REQ-SGR-006, CP-1). anchor(t, days) 의 days 는 이 표의 값.
PERIOD_DAYS = {"1W": 7, "1M": 28, "3M": 91, "6M": 182, "12M": 364, "52W": 364}

# 주가가 아닌 지수 행 — 행 수(종목 수) 계산에서 제외(WIP compute_sector_history 와 동일 관용).
_INDEX_NAMES = ("KOSPI", "KOSDAQ")
_GAP_MIN, _GAP_MAX = 6, 10  # 정규 인접 바 간격(일)의 허용 범위(TG-3)


# ---------------------------------------------------------------------------
# 데이터 계약 (plan D2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GridBar:
    date: str
    is_partial_week: bool
    partial_week_trading_days: int
    row_count: int


@dataclass(frozen=True)
class Exclusion:
    date: str
    row_count: int


@dataclass(frozen=True)
class Anomaly:
    from_date: str
    to_date: str
    gap_days: int


@dataclass(frozen=True)
class WeeklyGrid:
    dates: list[str]            # 정규 격자 전체(미완성 latest 포함), 오름차순
    latest: GridBar | None      # 최근 바(빈 DB 면 None)
    history: list[GridBar]      # 미완성 latest 를 제외한 바(히스토리·롤링·기준일 비교용)
    exclusions: list[Exclusion] # CG-3 배제 날짜
    anomalies: list[Anomaly]    # 전체 격자 기준 간격 6~10일 범위 밖 인접 쌍
    grid_version: str


@dataclass(frozen=True)
class HistorySlice:
    bars: list[GridBar]
    requested_weeks: int
    returned_weeks: int


# ---------------------------------------------------------------------------
# 산출
# ---------------------------------------------------------------------------

def compute_weekly_grid(weekly_db_path: str, as_of: str | None = None) -> WeeklyGrid:
    """주봉 DB 경로(+ 선택 as_of 기준일) → 정규 주간 격자.

    Args:
        weekly_db_path: 주봉 SQLite DB 경로(``stock_prices`` 테이블 보유).
        as_of: 진행 중인 주 판정 기준일(ISO ``YYYY-MM-DD``). ``None`` 이면 오늘.

    Returns:
        ``WeeklyGrid``. 빈 DB 면 빈 리스트 + ``latest=None``.
    """
    as_of_str = as_of if as_of is not None else date.today().isoformat()
    # @MX:ANCHOR: [AUTO] 정규 주간 격자 단일 산출 입구 — fan_in >= 6 (M5 7 소비자 수렴).
    # @MX:REASON: 모든 기준일 소비자가 이 함수를 경유해야 TG-5(동일 격자) 가 성립한다.
    return _compute_cached(weekly_db_path, os.path.getmtime(weekly_db_path), as_of_str)


@lru_cache(maxsize=16)
def _compute_cached(weekly_db_path: str, db_mtime: float, as_of_str: str) -> WeeklyGrid:
    """(DB 경로, mtime, as_of) 키로 메모이즈(plan D7). mtime 변화→자동 무효화."""
    as_of_d = date.fromisoformat(as_of_str)
    conn = sqlite3.connect(weekly_db_path)
    try:
        date_counts: dict[str, int] = dict(conn.execute(
            f"SELECT Date, COUNT(*) FROM stock_prices "
            f"WHERE Name NOT IN ({', '.join(['?'] * len(_INDEX_NAMES))}) GROUP BY Date",
            _INDEX_NAMES,
        ).fetchall())
    finally:
        conn.close()

    if not date_counts:
        return WeeklyGrid([], None, [], [], [], GRID_VERSION)

    # CG-1: ISO 주 그룹핑 → 대표 = MAX(Date)
    weeks: dict[tuple[int, int], list[str]] = {}
    for d in date_counts:
        iy, iw, _ = date.fromisoformat(d).isocalendar()
        weeks.setdefault((iy, iw), []).append(d)
    rep_sorted = sorted(max(v) for v in weeks.values())

    # CG-3: 대표 바 행 수 중앙값의 50% 미만 배제
    median = statistics.median(date_counts[d] for d in rep_sorted)
    threshold = median * 0.5
    exclusions: list[Exclusion] = []
    kept: list[str] = []
    for d in rep_sorted:
        if date_counts[d] < threshold:
            exclusions.append(Exclusion(d, date_counts[d]))
        else:
            kept.append(d)

    week_td = {d: len(weeks[date.fromisoformat(d).isocalendar()[:2]]) for d in date_counts}
    anomalies = _anomalies(kept)

    # CG-2: 진행 중인 주 판정(최신 주 금요일 바 부재 + 주 미종료)
    latest_d = kept[-1]
    latest_week = date.fromisoformat(latest_d).isocalendar()[:2]
    has_friday = any(date.fromisoformat(d).weekday() == 4 for d in weeks[latest_week])
    week_sunday = date.fromisocalendar(latest_week[0], latest_week[1], 7)
    is_partial = (not has_friday) and as_of_d <= week_sunday
    latest_bar = GridBar(latest_d, is_partial, week_td[latest_d], date_counts[latest_d])

    hist_dates = kept[:-1] if is_partial else list(kept)
    history_bars = [GridBar(d, False, week_td[d], date_counts[d]) for d in hist_dates]
    return WeeklyGrid(kept, latest_bar, history_bars, exclusions, anomalies, GRID_VERSION)


def _anomalies(dates: list[str]) -> list[Anomaly]:
    """인접 바 간격이 6~10일 범위 밖인 쌍을 순서대로 기록(TG-3)."""
    out: list[Anomaly] = []
    for a, b in zip(dates, dates[1:]):
        gap = (date.fromisoformat(b) - date.fromisoformat(a)).days
        if not (_GAP_MIN <= gap <= _GAP_MAX):
            out.append(Anomaly(a, b, gap))
    return out


def anchor(grid: WeeklyGrid, t: str, days: int) -> GridBar | None:
    """``t - days`` 일 이하의 가장 최근 history_grid 바(REQ-SGR-006).

    SPEC 본문의 ``anchor(t, days)`` 표기는 ``grid`` 가 이미 바인딩된 줄임 표현이다.
    반환바는 항상 ``t`` 보다 엄격히 이르거나 같다(history 에 latest 미완성 바는 없다).
    """
    target = date.fromisoformat(t) - timedelta(days=days)
    for bar in reversed(grid.history):
        if date.fromisoformat(bar.date) <= target:
            return bar
    return None


def history(grid: WeeklyGrid, weeks: int) -> HistorySlice:
    """최근 N 개의 history_grid 바(REQ-SGR-007). 가용 이력이 N 미만이면 가용한 만큼."""
    take = grid.history[-weeks:] if weeks > 0 else []
    return HistorySlice(take, weeks, len(take))
