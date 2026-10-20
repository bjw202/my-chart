"""재현 테스트: 섹터 전환 알림(WeeklyHighlights) 순위 ≠ 섹터 표 순위.

버그: ``detect_sector_transitions`` 가 레거시 ``compute_sector_ranking`` 으로 순위를 매긴다.
      (a) composite 를 **min-max** 정규화(``_normalize_list``)로 계산하고, (b) ``daily_db_path``
      없이 호출해 시총이 결측 → 등가중 폴백이 걸린다. 섹터 표는
      ``compute_sector_aggregates(period=None)`` 의 **순위 백분위**(AG-8)·시총가중 경로다.
      그래서 알림의 "순위 3단계 이상 상승/하락" 과 RS·Stage 2 입력이 표와 다른 기준으로
      계산된다(라이브 2026-10-16 비철금속: 레거시 1위, 표 5위).

기대 동작: 전환 감지가 쓰는 현재·4주 전 기준일 d 의 순위·composite·RS 평균·Stage 2 비율 ==
``compute_sector_aggregates(weekly, d, daily, as_of=d, compute_rank_change=False, period=None)``
값. 순위 제외(``rank is None``) 섹터는 표와 같이 빠진다.

픽스처는 Bump 정렬 재현 테스트(6ae45d7)와 같은 것을 쓴다 — 3M 극단값 섹터 OUT 이
min-max 에서만 1위로 뛴다(순위 백분위: LEAD 1위, OUT 2위).
"""

from __future__ import annotations

from my_chart.analysis.sector_advanced import _transition_rankings, detect_sector_transitions
from my_chart.analysis.sector_metrics import compute_sector_aggregates
from my_chart.analysis.weekly_grid import compute_weekly_grid
from tests.test_sector_history_rank_alignment import alignment_dbs  # noqa: F401 — pytest 픽스처


def _comparison_dates(weekly_db: str) -> tuple[str, str]:
    """``detect_sector_transitions`` 와 같은 (현재, 4주 전) 날짜 선택."""
    dates = compute_weekly_grid(weekly_db).dates[-5:]
    return dates[-1], dates[0]


def _table_metrics(weekly_db: str, daily_db: str, d: str) -> dict[str, tuple]:
    result = compute_sector_aggregates(
        weekly_db, d, daily_db, as_of=d, compute_rank_change=False, period=None)
    return {
        a.name: (a.rank, a.composite_score.value, a.rs_avg.value, a.stage2_pct.value)
        for a in result.aggregates if a.rank is not None
    }


def _as_tuples(by_name: dict) -> dict[str, tuple]:
    return {n: (m.rank, m.composite_score, m.rs_avg, m.stage2_pct) for n, m in by_name.items()}


def test_transition_current_ranks_follow_table_not_min_max(alignment_dbs) -> None:  # noqa: F811
    """3M 극단값 섹터(OUT)는 표와 같이 2위여야 한다 — min-max 였다면 1위로 뛴다."""
    weekly_db, daily_db = alignment_dbs
    cur_d, prev_d = _comparison_dates(weekly_db)
    current, _prev = _transition_rankings(weekly_db, cur_d, prev_d, daily_db_path=daily_db)

    assert {n: m.rank for n, m in current.items()} == {
        "LEAD": 1, "OUT": 2, "MID": 3, "LAG": 4}, (
        f"전환 감지 현재 순위가 표 순위와 다름: { {n: m.rank for n, m in current.items()} }")


def test_transition_metrics_equal_table_for_both_dates(alignment_dbs) -> None:  # noqa: F811
    """현재·4주 전 모두 순위·composite·RS 평균·Stage 2 비율이 표 집계값과 같다."""
    weekly_db, daily_db = alignment_dbs
    cur_d, prev_d = _comparison_dates(weekly_db)
    current, prev = _transition_rankings(weekly_db, cur_d, prev_d, daily_db_path=daily_db)

    assert _as_tuples(current) == _table_metrics(weekly_db, daily_db, cur_d)
    assert _as_tuples(prev) == _table_metrics(weekly_db, daily_db, prev_d)


def test_detect_sector_transitions_threads_daily_db(alignment_dbs, monkeypatch) -> None:  # noqa: F811
    """``detect_sector_transitions(daily_db_path=...)`` 는 그 일봉 DB 를 순위 산출에 넘긴다."""
    weekly_db, daily_db = alignment_dbs
    seen: list[str | None] = []

    import my_chart.analysis.sector_advanced as sa

    real = sa._transition_rankings

    def _spy(db_path, current_date, prev_date, daily_db_path=None):
        seen.append(daily_db_path)
        return real(db_path, current_date, prev_date, daily_db_path=daily_db_path)

    monkeypatch.setattr(sa, "_transition_rankings", _spy)
    detect_sector_transitions(weekly_db, daily_db_path=daily_db)
    assert seen == [daily_db]


def test_missing_metric_on_one_date_is_not_treated_as_zero(alignment_dbs, monkeypatch) -> None:  # noqa: F811
    """한쪽 기준일의 RS 평균·Stage 2 비율이 결측(None)이면 변화량을 판정하지 않는다.

    집계 경로는 결측을 None 으로 준다. 0 으로 메우면 "RS 평균 80pt 상승" 같은 가짜 변화가
    생기고, 그대로 빼면 TypeError 로 알림 전체가 실패한다 — 둘 다 아니어야 한다.
    """
    import my_chart.analysis.sector_advanced as sa

    weekly_db, daily_db = alignment_dbs
    cur = {"X": sa._TransitionMetrics(rank=1, composite_score=90.0, rs_avg=80.0, stage2_pct=60.0)}
    prev = {"X": sa._TransitionMetrics(rank=9, composite_score=10.0, rs_avg=None, stage2_pct=None)}
    monkeypatch.setattr(sa, "_transition_rankings", lambda *a, **k: (cur, prev))

    alerts = detect_sector_transitions(weekly_db, daily_db_path=daily_db)
    signals = [s for a in alerts.emerging_leaders + alerts.weakening_sectors for s in a.signals]
    assert not any(s.startswith(("RS 평균", "Stage 2")) for s in signals), signals


def test_market_overview_router_passes_daily_db(monkeypatch) -> None:
    """``/market/overview`` 라우터는 일봉 DB 경로를 서비스(→ 섹터 전환 알림)에 넘긴다."""
    import asyncio

    import backend.routers.market as market_router

    calls: list[tuple] = []
    monkeypatch.setattr(market_router, "WEEKLY_DB_PATH", "weekly.db")
    monkeypatch.setattr(market_router, "DAILY_DB_PATH", "daily.db")
    monkeypatch.setattr(market_router, "get_market_overview",
                        lambda *a, **k: calls.append((a, k)) or "ok")

    assert asyncio.run(market_router.market_overview()) == "ok"
    assert calls == [(("weekly.db",), {"daily_db_path": "daily.db"})]
