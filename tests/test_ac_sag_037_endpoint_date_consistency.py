# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 — AC-SAG-037 전 엔드포인트 as_of_date 일치 (SN-3).

M7 종료 시점 재조사(2026-08-14)에서 AC-SAG-037 이 plan.md M1.1/M6 RED 목록
어디에도 없이 미구현 상태로 남아 있음이 확인됐다(progress.md §E.2 M7 Gap 항목).
본 파일이 그 결손을 닫는다.

**픽스처 재사용**: ``fixture_max_ne_canonical`` 은 ①SPEC-SECTOR-GRID-001 이
소유한 ``tests/test_consumer_dates.py`` 의 것을 **import 로만** 재사용한다(해당
파일은 완결 SPEC 소유라 수정하지 않는다 — read-only 의존). naive
``MAX(Date)`` ≠ 정규 대표 바(canonical)가 되도록 설계된 합성 주봉 DB다:

* 2024-01-12(금) — 40행 → 정규 대표 바(canonical).
* 2024-01-15(월) — 3행(부분 데이터, CG-3 배제) → naive ``MAX(Date)``.
"""
from __future__ import annotations

import sqlite3
import tempfile
import warnings
from pathlib import Path
from typing import Any, Callable

import pytest

from tests.test_consumer_dates import (
    WEEKLY_FULL_DATE,
    WEEKLY_PARTIAL_DATE,
    _build_fixture_max_ne_canonical,
)

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------


@pytest.fixture
def weekly_db(tmp_path: Path) -> str:
    """naive MAX ≠ canonical 인 합성 주봉 DB (①에서 read-only 재사용)."""
    db_path = str(tmp_path / "max_ne_canonical.db")
    _build_fixture_max_ne_canonical(db_path)
    return db_path


@pytest.fixture
def daily_db(tmp_path: Path) -> str:
    """``get_sector_detail`` / ``get_sector_ranking`` 이 요구하는 최소 stock_meta 스키마.

    빈 테이블이면 충분하다 — 이 테스트의 관심사는 ``as_of_date`` 배선이지 집계
    산출값이 아니다.
    """
    db_path = str(tmp_path / "daily_min.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE stock_meta (code TEXT, name TEXT, market TEXT, "
            "market_cap REAL, sector_major TEXT, sector_minor TEXT, "
            "rs_12m REAL, chg_1m REAL)"
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _naive_max_date(db_path: str, as_of: str | None = None) -> str | None:
    """엔드포인트별 순진 ``MAX(Date)`` 경로 — 되돌림 대조용 대체 구현.

    ``_get_latest_valid_date`` 와 동일한 시그니처를 갖는다(모듈 attr 로
    monkeypatch 되므로 호출부와 인자 개수가 일치해야 한다). CG-1/CG-3 정규화
    없이 부분 데이터 행도 그대로 포함한다 — 픽스처 전제상 반드시
    ``WEEKLY_PARTIAL_DATE`` 를 반환한다.
    """
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name NOT IN ('KOSPI','KOSDAQ')"
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def _call_bubble(weekly: str, daily: str) -> str | None:
    from backend.services.sector_advanced_service import get_sector_bubble

    return get_sector_bubble(weekly).as_of_date


def _call_stock_bubble(weekly: str, daily: str) -> str | None:
    from backend.services.sector_advanced_service import get_stock_bubble

    return get_stock_bubble(weekly, sector_name="아무섹터").as_of_date


def _call_rrg(weekly: str, daily: str) -> str | None:
    from backend.services.sector_advanced_service import get_rrg_data

    return get_rrg_data(weekly).as_of_date


def _call_history(weekly: str, daily: str) -> str | None:
    from backend.services.sector_advanced_service import get_sector_history

    return get_sector_history(weekly).as_of_date


def _call_ranking(weekly: str, daily: str) -> str | None:
    from backend.services.sector_ranking_service import get_sector_ranking

    return get_sector_ranking(weekly, daily).as_of_date


def _call_stage_overview(weekly: str, daily: str) -> str | None:
    from backend.services.stage_service import get_stage_overview

    return get_stage_overview(weekly, daily_db_path=daily).as_of_date


def _call_sector_detail(weekly: str, daily: str) -> str | None:
    from backend.services.sector_detail_service import get_sector_detail

    return get_sector_detail(daily, "아무섹터", weekly_db_path=weekly).as_of_date


# 7-엔드포인트 변형 행렬 — acceptance.md §9 DoD "엔드포인트별 순진 MAX(Date) 7회"
_ENDPOINTS: list[tuple[str, Callable[[str, str], str | None]]] = [
    ("/sectors/bubble", _call_bubble),
    ("/sectors/{name}/bubble", _call_stock_bubble),
    ("/sectors/rrg", _call_rrg),
    ("/sectors/history", _call_history),
    ("/sectors/ranking", _call_ranking),
    ("/stage/overview", _call_stage_overview),
    ("/sectors/{name}/detail", _call_sector_detail),
]

assert len(_ENDPOINTS) == 7, "AC-SAG-037 은 7개 엔드포인트 변형 행렬을 요구한다"


# ---------------------------------------------------------------------------
# 정판정 — 7개 전부 canonical 로 수렴한다
# ---------------------------------------------------------------------------


def test_ac_sag_037_all_seven_endpoints_converge_to_canonical_date(
    weekly_db: str, daily_db: str
) -> None:
    """7개 엔드포인트가 모두 동일한 ``as_of_date`` 이고, 정규 대표 바와 같다.

    naive ``MAX(Date)`` (``WEEKLY_PARTIAL_DATE``) 와는 다르다 — 양쪽 모두 단언한다.
    """
    results = {label: fn(weekly_db, daily_db) for label, fn in _ENDPOINTS}

    for label, as_of_date in results.items():
        assert as_of_date == WEEKLY_FULL_DATE, (
            f"{label}: as_of_date={as_of_date!r} != canonical({WEEKLY_FULL_DATE!r}) — "
            "정규 대표 바가 아니다"
        )
        assert as_of_date != WEEKLY_PARTIAL_DATE, (
            f"{label}: as_of_date 가 naive MAX(Date)({WEEKLY_PARTIAL_DATE!r}) 와 같다 — "
            "순진 경로를 쓰고 있다"
        )

    assert len(set(results.values())) == 1, (
        f"AC-SAG-037 위반 — 7개 엔드포인트 as_of_date 가 서로 다르다: {results}"
    )


def test_ac_sag_037_all_seven_endpoints_share_grid_version(
    weekly_db: str, daily_db: str
) -> None:
    """7개 ``grid_version`` 이 동일하고 ``canonical-v1`` 이다."""
    from backend.services.sector_advanced_service import (
        get_rrg_data,
        get_sector_bubble,
        get_sector_history,
        get_stock_bubble,
    )
    from backend.services.sector_detail_service import get_sector_detail
    from backend.services.sector_ranking_service import get_sector_ranking
    from backend.services.stage_service import get_stage_overview

    versions = {
        "/sectors/bubble": get_sector_bubble(weekly_db).grid_version,
        "/sectors/{name}/bubble": get_stock_bubble(
            weekly_db, sector_name="아무섹터"
        ).grid_version,
        "/sectors/rrg": get_rrg_data(weekly_db).grid_version,
        "/sectors/history": get_sector_history(weekly_db).grid_version,
        "/sectors/ranking": get_sector_ranking(weekly_db, daily_db).grid_version,
        "/stage/overview": get_stage_overview(
            weekly_db, daily_db_path=daily_db
        ).grid_version,
        "/sectors/{name}/detail": get_sector_detail(
            daily_db, "아무섹터", weekly_db_path=weekly_db
        ).grid_version,
    }
    assert set(versions.values()) == {"canonical-v1"}, (
        f"AC-SAG-037 위반 — grid_version 이 canonical-v1 로 수렴하지 않음: {versions}"
    )


# ---------------------------------------------------------------------------
# 대조 단언 — 엔드포인트를 하나씩 순진 MAX(Date) 경로로 되돌린 7개 변형
# ---------------------------------------------------------------------------

# (label, call_fn, monkeypatch target module, monkeypatch attr name)
_REVERT_TARGETS: list[tuple[str, Callable[[str, str], str | None], str, str]] = [
    ("/sectors/bubble", _call_bubble,
     "backend.services.sector_advanced_service", "_get_latest_valid_date"),
    ("/sectors/{name}/bubble", _call_stock_bubble,
     "backend.services.sector_advanced_service", "_get_latest_valid_date"),
    ("/sectors/rrg", _call_rrg,
     "backend.services.sector_advanced_service", "_get_latest_valid_date"),
    ("/sectors/history", _call_history,
     "backend.services.sector_advanced_service", "_get_latest_valid_date"),
    ("/sectors/ranking", _call_ranking,
     "backend.services.sector_ranking_service", "_get_latest_date"),
    ("/stage/overview", _call_stage_overview,
     "backend.services.stage_service", "_get_latest_date"),
    ("/sectors/{name}/detail", _call_sector_detail,
     "backend.services.sector_detail_service", "_get_latest_valid_date"),
]

assert len(_REVERT_TARGETS) == 7, "되돌림 대조는 7개 엔드포인트 각각에 대해 수행한다"


@pytest.mark.parametrize(
    "label,call_fn,target_module,target_attr",
    _REVERT_TARGETS,
    ids=[t[0] for t in _REVERT_TARGETS],
)
def test_ac_sag_037_naive_max_date_revert_fails_for_each_endpoint(
    weekly_db: str,
    daily_db: str,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
    call_fn: Callable[[str, str], str | None],
    target_module: str,
    target_attr: str,
) -> None:
    """[HARD] 되돌림 검출 — 7개 엔드포인트 각각을 순진 MAX(Date) 경로로 되돌리면
    그 엔드포인트의 ``as_of_date`` 가 canonical 이 아니라 naive 값이 된다.

    7회 반복해 7개 배선이 전부 실제로 정규 헬퍼를 경유함을 증명한다 — 1곳만
    배선하고 나머지가 우연히 (기본 인자 등으로) 일치하는 상태를 검출한다.
    """
    module = __import__(target_module, fromlist=[target_attr])
    monkeypatch.setattr(module, target_attr, _naive_max_date)

    reverted_date = call_fn(weekly_db, daily_db)

    assert reverted_date == WEEKLY_PARTIAL_DATE, (
        f"{label}: 되돌림 후 as_of_date={reverted_date!r} != naive({WEEKLY_PARTIAL_DATE!r}) "
        "— 이 엔드포인트가 되돌림 대상 헬퍼를 경유하지 않는다(배선 미확인)"
    )
    assert reverted_date != WEEKLY_FULL_DATE, (
        f"{label}: 되돌림 후에도 canonical({WEEKLY_FULL_DATE!r}) 을 반환한다 — "
        "이 AC 가 실패해야 하는데 실패하지 않았다(대조 단언 무음통과)"
    )


# ---------------------------------------------------------------------------
# 라이브 비게이팅 스모크 — 정보성 검사, 실패해도 테스트를 fail 시키지 않는다
# ---------------------------------------------------------------------------


def test_ac_sag_037_live_smoke_as_of_date_matches_across_endpoints() -> None:
    """라이브 DB 에서도 7개 값이 동일함을 확인하되 **정보성 검사**로 표시한다.

    오늘 라이브 통과는 ``naive_max == canonical`` 인 우연 때문일 수 있다 —
    이 스모크는 그 우연을 배제하지 못하므로(§9 DoD 명시), 실패해도 pytest
    실패로 이어지지 않고 경고만 남긴다. 실제 회귀 방어는 위 두 픽스처 기반
    테스트(정판정 + 되돌림 대조)가 전담한다.
    """
    from backend.deps import DAILY_DB_PATH, WEEKLY_DB_PATH

    if not (Path(WEEKLY_DB_PATH).exists() and Path(DAILY_DB_PATH).exists()):
        pytest.skip("라이브 weekly/daily DB 부재 — 정보성 스모크 스킵")

    results: dict[str, Any] = {}
    for label, fn in _ENDPOINTS:
        try:
            results[label] = fn(WEEKLY_DB_PATH, DAILY_DB_PATH)
        except Exception as exc:  # noqa: BLE001 — 정보성 검사, 예외도 경고로 강등
            results[label] = f"<error: {exc!r}>"

    distinct = set(results.values())
    if len(distinct) != 1:
        warnings.warn(
            "AC-SAG-037 라이브 스모크 — 7개 엔드포인트 as_of_date 불일치(정보성, "
            f"non-gating): {results}. 오늘 naive_max == canonical 우연 여부는 "
            "이 스모크가 배제하지 못한다(§9 DoD).",
            stacklevel=1,
        )
