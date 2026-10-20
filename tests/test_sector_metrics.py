"""섹터 순위 응답 ``sectors[]`` 의 값 단언(AC-SAG-044 의미 테스트).

종전에는 레거시 ``compute_sector_ranking`` → ``SectorRank`` 를 직접 검사했다(SPEC R7/R8).
그 함수는 집계 경로(``compute_sector_aggregates`` — ALL_CAPPED 벤치마크·순위 백분위)로
통일되며 제거됐고, 여전히 유효한 단언(순위·composite 범위·초과수익률 관계·RS 지표·
지수 행 제외)은 같은 산출을 싣는 응답 ``sectors[]`` 대상으로 이관했다.
검출력 실증(되돌림 3케이스)은 ``tests/test_ac_sag_044_regression.py`` 가 전담한다.
"""

from __future__ import annotations

import pytest

from tests.test_sector_ranking_sectors_unify import unify_dbs  # noqa: F401 — 픽스처 공유


@pytest.fixture
def ranking(unify_dbs):  # noqa: F811
    from backend.services.sector_ranking_service import get_sector_ranking

    weekly_db, daily_db, as_of = unify_dbs
    return get_sector_ranking(weekly_db, daily_db, as_of=as_of)


def test_ranks_are_contiguous_and_follow_composite_descending(ranking) -> None:
    """순위는 1..N 연속이며 rank 순서로 composite_score 가 내림차순이다(구 AC8)."""
    items = sorted(ranking.sectors, key=lambda s: s.rank)
    assert [s.rank for s in items] == list(range(1, len(items) + 1))
    scores = [s.composite_score for s in items]
    assert scores == sorted(scores, reverse=True)


def test_sector_rank_item_has_spec_values(ranking) -> None:
    """AC-SAG-044 — 각 필드가 타입·범위·관계를 실제로 만족한다(존재가 아니라 값)."""
    assert ranking.sectors
    bench = {p: ranking.benchmark.returns[p].value for p in ("1w", "1m", "3m")}
    for s in ranking.sectors:
        assert isinstance(s.name, str) and s.name
        assert isinstance(s.stock_count, int) and s.stock_count > 0
        for field in ("rs_avg", "rs_top_pct", "nh_pct", "stage2_pct"):
            assert 0.0 <= getattr(s, field) <= 100.0, f"{field} must be a 0-100 pct"
        assert 0.0 <= s.composite_score <= 100.0
        assert isinstance(s.rank, int) and s.rank >= 1
        assert isinstance(s.rank_change, int)
        # 관계 — 초과수익률 = 섹터수익률 − ALL_CAPPED 벤치마크 수익률(규칙 EX-2)
        for key, p in (("w1", "1w"), ("m1", "1m"), ("m3", "3m")):
            assert abs(getattr(s.excess_returns, key)
                       - (getattr(s.returns, key) - bench[p])) < 1e-3


def test_rs_avg_and_rs_top_pct(ranking) -> None:
    """rs_avg 는 구성종목 RS 평균, rs_top_pct 는 RS>=80 비율(%)이다(구 R7)."""
    lead = next(s for s in ranking.sectors if s.name == "LEAD")
    assert lead.rs_avg == pytest.approx((85 + 72 + 90 + 60 + 50) / 5, abs=0.01)
    assert lead.rs_top_pct == pytest.approx(40.0, abs=0.01)


def test_index_rows_are_not_sector_members(ranking) -> None:
    """KOSPI 지수 행은 등록부에 섹터 소속으로 있어도 구성종목으로 세지 않는다."""
    names = {s.name for s in ranking.sectors}
    assert "KOSPI" not in names and "KOSDAQ" not in names
    lead = next(s for s in ranking.sectors if s.name == "LEAD")
    assert lead.stock_count == 5
