# coding: utf-8
"""SPEC-SECTOR-GRID-001 M2 — 유니버스 규약 (universe) 모듈.

모든 섹터 집계의 단일 입력인 **유효 유니버스** 를 산출한다(규칙 UN-1~UN-5).

유효 유니버스 = ``registry(dedup) ∩ stock_meta ∩ {최신 정규 바에 가격 존재} ∩ {비-stale}``
(REQ-SGR-012, 규칙 UN-3). 방향 무관 교집합(A6) — ``stock_meta ⊂ registry`` 라는 실측 포함
관계에 의존하지 않는다.

단일 소스(REQ-SGR-011, UN-1/UN-2):
  * registry = 섹터 소속·산업명(대)·산업명(중)·시장 의 단일 원천.
  * stock_meta = market_cap 의 단일 원천.

stale 판정(REQ-SGR-014, 규칙 UN-5): 종목별 **일봉** ``stock_prices`` 의 ``MAX(Date)`` 가
최신 일봉 거래일 대비 14일 *초과* older 면 stale. ``stock_meta.last_updated`` 는 전 행이
동일 타임스탬프라 판정력이 없어 사용 금지(REQ-SGR-015).
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date

from my_chart.analysis.weekly_grid import compute_weekly_grid
from my_chart.registry import load_sector_registry_with_diagnostics

logger = logging.getLogger(__name__)

# 미분류 섹터 canonical 센티널(REQ-SGR-017, O-G5 = "기타").
# @MX:NOTE: [AUTO] 미분류 섹터 센티널 단일 값 — stage_service / sector_metrics 가 공유.
#   종목 버블 ETC_LABEL('기타') 와 일치하며 registry 0건 충돌 없음(잠재 발산 차단).
ETC_SECTOR = "기타"

# stale 임계값(일). 일봉 MAX(Date) 가 최신 거래일 대비 이 값보다 오래되면 stale(UN-5).
STALE_DAYS = 14


@dataclass(frozen=True)
class DuplicateRecord:
    """registry dedup 과정에서 drop 된 중복 행(UN-4 진단)."""

    code: str
    name: str


@dataclass(frozen=True)
class UniverseSnapshot:
    """유효 유니버스 + 진단 산출물(REQ-SGR-012/014/016).

    Attributes:
        valid_names: 유효 유니버스(4중 교집합). 모든 섹터 집계의 단일 입력.
        registry_only: ``registry \\ stock_meta`` (O-G1 진단 — 수집 누락 후보).
        stock_meta_only: ``stock_meta \\ registry`` (A6 방향 무관 검증용).
        stale_names: UN-5 로 배제된 종목(일봉 MAX(Date) > 14일 older).
        stale_excluded_count: ``len(stale_names)``.
        registry_only_count: ``len(registry_only)``.
        duplicates: registry Code-dedup 로 drop 된 (code, name) 목록(UN-4).
        as_of_date: 최신 정규 주간 바 날짜(유효 바 가격 존재 판정 기준).
        latest_daily_date: 일봉 최신 거래일(stale 판정 기준 T).
    """

    valid_names: frozenset[str]
    registry_only: tuple[str, ...]
    stock_meta_only: tuple[str, ...]
    stale_names: frozenset[str]
    stale_excluded_count: int
    registry_only_count: int
    duplicates: tuple[DuplicateRecord, ...]
    as_of_date: str | None
    latest_daily_date: str | None


# @MX:ANCHOR: [AUTO] 유효 유니버스 단일 산출 입구 — fan_in >= 3 (M5 집계 소비자 수렴).
# @MX:REASON: UN-3 4중 교집합(registry ∩ stock_meta ∩ 최신바가격 ∩ 비-stale) 의 단일 원천.
#   모든 섹터 집계가 이 집합을 입력으로 써야 TG/UN 불변식이 성립한다.
def compute_universe(
    weekly_db_path: str,
    daily_db_path: str,
    registry_path: str,
    as_of: str | None = None,
) -> UniverseSnapshot:
    """유효 유니버스 + 진단 산출.

    Args:
        weekly_db_path: 주봉 SQLite DB 경로(``stock_prices`` 테이블).
        daily_db_path: 일봉 SQLite DB 경로(``stock_meta`` + ``stock_prices``).
        registry_path: registry xlsx 경로(header=8 구조).
        as_of: 진행 중인 주 판정 기준일(ISO ``YYYY-MM-DD``). ``None`` 이면 오늘.

    Returns:
        ``UniverseSnapshot``. 빈 입력이면 빈 valid_names.
    """
    # 1. registry(dedup) — 섹터 소속·산업명·시장 단일 원천(UN-1, UN-4).
    reg_df, dup_pairs = load_sector_registry_with_diagnostics(registry_path)
    registry_names: set[str] = {str(n) for n in reg_df["Name"]}
    duplicates = tuple(DuplicateRecord(c, n) for c, n in dup_pairs)

    # 2. stock_meta names + 일봉 종목별 MAX(Date) (stale 판정용, UN-2/UN-5).
    conn = sqlite3.connect(daily_db_path)
    try:
        meta_names: set[str] = {
            str(r[0]) for r in conn.execute("SELECT name FROM stock_meta")
        }
        daily_max: dict[str, str] = dict(
            conn.execute("SELECT Name, MAX(Date) FROM stock_prices GROUP BY Name").fetchall()
        )
    finally:
        conn.close()

    # 3. stale 판정(UN-5): 일봉 MAX(Date) 가 최신 거래일 대비 STALE_DAYS 초과 older.
    latest_daily = max(daily_max.values()) if daily_max else None
    stale_names: set[str] = set()
    if latest_daily is not None:
        t_daily = date.fromisoformat(latest_daily)
        for nm, max_d in daily_max.items():
            if (t_daily - date.fromisoformat(max_d)).days > STALE_DAYS:
                stale_names.add(nm)
    # NOTE: last_updated 는 의도적으로 사용하지 않는다(REQ-SGR-015 — 전 행 동일 타임스탬프).

    # 4. 최신 정규 주간 바에 가격 존재하는 종목 집합(UN-3 세 번째 교집합 성분).
    grid = compute_weekly_grid(weekly_db_path, as_of)
    latest_date = grid.latest.date if grid.latest is not None else None
    latest_bar_names: set[str] = set()
    if latest_date is not None:
        wconn = sqlite3.connect(weekly_db_path)
        try:
            latest_bar_names = {
                str(r[0])
                for r in wconn.execute(
                    "SELECT Name FROM stock_prices WHERE Date = ?", (latest_date,)
                )
            }
        finally:
            wconn.close()

    # 5. 4중 교집합(방향 무관, A6): registry ∩ stock_meta ∩ 최신바가격 ∩ 비-stale.
    non_stale = set(daily_max) - stale_names
    valid = registry_names & meta_names & latest_bar_names & non_stale

    # 6. 진단(REQ-SGR-016): registry \\ stock_meta + WARNING.
    registry_only_sorted = sorted(registry_names - meta_names)
    stock_meta_only_sorted = sorted(meta_names - registry_names)
    if registry_only_sorted:
        logger.warning(
            "registry 전용 종목(registry \\ stock_meta) %d종: %s",
            len(registry_only_sorted),
            ", ".join(registry_only_sorted),
        )

    return UniverseSnapshot(
        valid_names=frozenset(valid),
        registry_only=tuple(registry_only_sorted),
        stock_meta_only=tuple(stock_meta_only_sorted),
        stale_names=frozenset(stale_names),
        stale_excluded_count=len(stale_names),
        registry_only_count=len(registry_only_sorted),
        duplicates=duplicates,
        as_of_date=latest_date,
        latest_daily_date=latest_daily,
    )
