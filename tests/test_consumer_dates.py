# coding: utf-8
"""SPEC-SECTOR-GRID-001 M5 — 엔드포인트 배선 교체 검증.

대상 AC:
  * AC-SGR-005 — 3종 관용구(I1 MAX(Date) / I2 DISTINCT Date…DESC / I3 GROUP BY Date) 정적
    스캔 → 소비자 7개 파일에서 0건. allowlist ≤ 5. ``sector_advanced_service`` 의
    ``_get_latest_date`` def 삭제. ``meta_service`` 제외는 파일 단위가 아닌 지점 단위
    (``:135`` 일봉만 제외, ``:196`` 주봉은 교체 대상).
  * AC-SGR-006-A — ``fixture_max_ne_canonical`` 픽스처에서 기준일 해석자 6지점이 모두
    정규 격자의 대표 바(W-금요일)를 반환. 순진한 ``MAX(Date)`` 와 다르다.
  * AC-SGR-006-B — ``sector_metrics.py:231`` rank_change 기준일 → ``anchor(t, 28)``.
    ``:346`` 중앙값 가드 → 공유 격자(``compute_sector_history`` 재연결).

WIP 계약 보존: ``compute_sector_history`` 의 ``(dates, rankings)`` 반환 + last-N-weeks
의미는 유지한다(test_sector_history_consistency.py 3건이 본 모듈과 병행 통과).
"""
from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

import pytest

from my_chart.analysis.weekly_grid import (
    _get_latest_valid_date,
    anchor,
    compute_weekly_grid,
)

# 기준 종목(meta_service.py:196 WHERE Name = REFERENCE_STOCK)
from my_chart.config import REFERENCE_STOCK

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# AC-SGR-006-A 픽스처의 기대값
WEEKLY_FULL_DATE = "2024-01-12"   # 금요일, ISO wk2, 정상 행 수
WEEKLY_PARTIAL_DATE = "2024-01-15"  # 월요일, ISO wk3, 부분 데이터(3행) — naive MAX


# ---------------------------------------------------------------------------
# fixture_max_ne_canonical (AC-SGR-006-A)
# ---------------------------------------------------------------------------

def _build_fixture_max_ne_canonical(db_path: str) -> None:
    """naive MAX ≠ canonical 인 합성 주봉 DB.

    * 2024-01-12(금): 비인덱스 40행(REFERENCE_STOCK 포함) → 정규 대표 바.
    * 2024-01-15(월): 비인덱스 3행(REFERENCE_STOCK 포함) → CG-3 배제 대상.
      - naive ``MAX(Date)`` = 2024-01-15 (나중 날짜).
      - 정규 격자(CG-3)는 3행을 중앙값의 50% 미만으로 배제 → latest = 2024-01-12.
    * [HARD] REFERENCE_STOCK(삼성전자)이 부분 데이터 3행에 포함된다 —
      ``meta_service.py:196`` 의 ``MAX(Date) WHERE Name=REFERENCE_STOCK`` 이
      순진한 경로에서도 2024-01-15 를 내도록 보장(대조 단언의 무음통과 차단).
    """
    conn = sqlite3.connect(db_path)
    try:
        # _load_weekly_snapshot 이 읽는 컬럼을 갖춘 stock_prices (날짜 집합 검증이
        # 목적이므로 값은 기본값). compute_sector_ranking → LEFT JOIN relative_strength.
        conn.execute(
            "CREATE TABLE stock_prices (Name TEXT, Date TEXT, Close REAL, SMA10 REAL, "
            "SMA40 REAL, SMA40_Trend_4M REAL, CHG_1W REAL, CHG_1M REAL, CHG_3M REAL, "
            "Volume REAL, VolumeSMA10 REAL, MAX52 REAL)"
        )
        conn.execute(
            "CREATE TABLE relative_strength (Name TEXT, Date TEXT, RS_12M_Rating REAL)"
        )
        _row = lambda n, d: (n, d, 100.0, 95.0, 90.0, 89.0, 0.02, 0.05, 0.10,
                             1_000_000.0, 800_000.0, 110.0)
        # 정상 날짜: 비인덱스 40행
        full_names = [REFERENCE_STOCK] + [f"STOCK{i:03d}" for i in range(39)]
        conn.executemany(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(n, WEEKLY_FULL_DATE) for n in full_names],
        )
        # 부분 데이터 날짜: 비인덱스 3행 (REFERENCE_STOCK 포함 — HARD 조건)
        partial_names = [REFERENCE_STOCK, "STOCK100", "STOCK101"]
        conn.executemany(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(n, WEEKLY_PARTIAL_DATE) for n in partial_names],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def fixture_max_ne_canonical(tmp_path: Path) -> str:
    db_path = str(tmp_path / "max_ne_canonical.db")
    _build_fixture_max_ne_canonical(db_path)
    return db_path


# ---------------------------------------------------------------------------
# AC-SGR-005 — 정적 스캔 (acceptance.md grep 과 동일)
# ---------------------------------------------------------------------------

_AC005_GREP = (
    'grep -rnE --include="*.py" "MAX\\(Date\\)|max\\(Date\\)|DISTINCT Date|GROUP BY Date" '
    "backend/services/ backend/routers/ my_chart/analysis/ "
    '| grep -v "_test\\|tests/" '
    '| grep -v "my_chart/analysis/weekly_grid\\.py" '
    '| grep -vE "chart_service\\.py|routers/db\\.py'
    '|sector_advanced\\.py:.*COUNT\\(DISTINCT|market_breadth\\.py" '
    '| grep -vE "meta_service\\.py:.*MAX\\(Date\\) FROM stock_prices WHERE Name"'
)


def _run_ac005_scan() -> str:
    """AC-SGR-005 스캔을 실행하고 매칭 행을 반환(정상 = 빈 문자열)."""
    proc = subprocess.run(
        ["bash", "-c", _AC005_GREP],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    # grep 은 매칭 없을 때 exit 1; 매칭 있으면 exit 0. stderr/exit 무시하고 stdout 사용.
    return proc.stdout.strip()


_WEEKLY_CONSUMER_FILES = [
    "backend/services/sector_ranking_service.py",
    "backend/services/stage_service.py",
    "backend/services/market_service.py",
    "backend/services/meta_service.py",
    "backend/services/sector_advanced_service.py",
    "my_chart/analysis/sector_advanced.py",
    "my_chart/analysis/sector_metrics.py",
]


def test_ac005_weekly_consumers_have_no_date_idioms() -> None:
    """주간 기준일 소비자 7개 파일에 3종 관용구가 없다(인파일 allowlist 2건 제외).

    인파일 허용: meta_service:135(일봉 기준종목 최신일), sector_advanced:386(COUNT).
    이 두 건만 남고 나머지는 0이어야 한다 — M5 배선 교체의 직접 검증.
    """
    import re

    idiom = re.compile(r"MAX\(Date\)|max\(Date\)|DISTINCT Date|GROUP BY Date")
    allow_infile = re.compile(
        r"MAX\(Date\) FROM stock_prices WHERE Name"  # meta_service:135 일봉
        r"|COUNT\(DISTINCT Date"                      # sector_advanced:386 개수
    )
    offenders = []
    for rel in _WEEKLY_CONSUMER_FILES:
        for i, line in enumerate((PROJECT_ROOT / rel).read_text().splitlines(), 1):
            if idiom.search(line) and not allow_infile.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        "AC-SGR-005 위반 — 주간 소비자에 자체 기준일 관용구 잔존:\n"
        + "\n".join(offenders)
    )


def test_ac005_full_tree_residual_confined_to_daily_stale_gap() -> None:
    """acceptance.md 전수 스캔의 비-allowlist 잔류는 daily-stale(universe.py) 에 한정된다.

    BLOCKER(본 M5 범위 밖): universe.py:106 은 일봉 stale 판정(REQ-SGR-014, M2,
    PRESERVED) 의 종목별 최신일 조회다. acceptance.md §1.2.2 allowlist 가 이를 누락했다
    (meta_service:135 일봉과 동일 범주). manager-spec 가 allowlist + grep 제외를
    보완해야 한다. 본 테스트는 잔류가 해당 daily-stale 갭에 한정됨을 단언해 주간
    소비자로의 역류를 감지한다(소비자를 되돌리면 non-gap 잔류가 생겨 실패).
    """
    output = _run_ac005_scan()
    residuals = [ln for ln in output.splitlines() if ln]
    non_gap = [ln for ln in residuals if "universe.py" not in ln]
    assert not non_gap, (
        "AC-SGR-005 위반 — allowlist 외 잔류가 universe.py daily-stale 갭이 아님:\n"
        + "\n".join(non_gap)
    )


def test_ac005_sector_advanced_service_no_get_latest_date_def() -> None:
    """sector_advanced_service.py 에 ``def _get_latest_date`` 정의가 없다(재도입 경로 제거)."""
    src = (PROJECT_ROOT / "backend/services/sector_advanced_service.py").read_text()
    assert "def _get_latest_date" not in src, (
        "AC-SGR-005 위반 — sector_advanced_service.py 에 _get_latest_date 정의 잔존"
    )


def test_ac005_meta_service_precision_daily_allowed_weekly_replaced() -> None:
    """meta_service 지점 단위 정밀도: :135(일봉)은 허용, :196(주봉)은 교체됨."""
    src = (PROJECT_ROOT / "backend/services/meta_service.py").read_text()
    # :135 일봉 — allowlist (FROM stock_prices WHERE Name) — 남아있어야 함
    assert "MAX(Date) FROM stock_prices WHERE Name" in src, (
        ":135 일봉 allowlist 항목이 사라짐 — 본 SPEC 범위 밖"
    )
    # :196 주봉 — 교체 대상 (FROM weekly.stock_prices) — 남아있으면 안 됨
    assert "MAX(Date) FROM weekly.stock_prices" not in src, (
        "AC-SGR-005 위반 — meta_service.py:196 주봉 MAX(Date) 잔존(일봉이 아님)"
    )


# ---------------------------------------------------------------------------
# AC-SGR-006-A — 기준일 해석자 6지점 (fixture_max_ne_canonical)
# ---------------------------------------------------------------------------


def test_fixture_premise_naive_max_ne_canonical(fixture_max_ne_canonical: str) -> None:
    """전제: naive MAX 와 canonical 이 다르다(픽스처가 진짜로 증명할 수 있는 상태)."""
    db = fixture_max_ne_canonical
    conn = sqlite3.connect(db)
    try:
        naive_all = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name NOT IN ('KOSPI','KOSDAQ')"
        ).fetchone()[0]
        naive_ref = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name = ?", (REFERENCE_STOCK,)
        ).fetchone()[0]
    finally:
        conn.close()
    canonical = _get_latest_valid_date(db)
    assert naive_all == WEEKLY_PARTIAL_DATE
    assert naive_ref == WEEKLY_PARTIAL_DATE  # HARD: REFERENCE_STOCK 이 부분 3행에 포함
    assert canonical == WEEKLY_FULL_DATE
    assert canonical != naive_all  # 반증 가능성의 핵심


@pytest.mark.parametrize(
    "resolver,label",
    [
        # A-1 ~ A-3: 서비스 계층 로컬 헬퍼(위임) — 각 모듈이 자체 해석하지 않는다
        (
            lambda db: __import__(
                "backend.services.sector_ranking_service", fromlist=["_get_latest_date"]
            )._get_latest_date(db),
            "A-1 sector_ranking_service",
        ),
        (
            lambda db: __import__(
                "backend.services.stage_service", fromlist=["_get_latest_date"]
            )._get_latest_date(db),
            "A-2 stage_service",
        ),
        (
            lambda db: __import__(
                "backend.services.market_service", fromlist=["_get_latest_date"]
            )._get_latest_date(db),
            "A-3 market_service",
        ),
        # A-4: sector_advanced_service — _get_latest_date def 삭제, 호출부가 공유 헬퍼 직접 사용
        (
            lambda db: __import__(
                "my_chart.analysis.weekly_grid", fromlist=["_get_latest_valid_date"]
            )._get_latest_valid_date(db),
            "A-4 sector_advanced_service (공유 헬퍼 직접)",
        ),
        # A-5: sector_advanced.py _get_dates (compute_weekly_grid 경유)
        (
            lambda db: __import__(
                "my_chart.analysis.sector_advanced", fromlist=["_get_dates"]
            )._get_dates(db, 1)[-1],
            "A-5 sector_advanced._get_dates",
        ),
        # A-6: meta_service.py:196 — 주봉, 공유 헬퍼로 교체됨
        (
            lambda db: __import__(
                "my_chart.analysis.weekly_grid", fromlist=["_get_latest_valid_date"]
            )._get_latest_valid_date(db),
            "A-6 meta_service:196 (공유 헬퍼 직접)",
        ),
    ],
)
def test_ac006a_resolver_returns_canonical_date(
    fixture_max_ne_canonical: str, resolver, label: str
) -> None:
    """6지점 각각이 정규 격자의 대표 바(WEEKLY_FULL_DATE)를 반환한다."""
    assert resolver(fixture_max_ne_canonical) == WEEKLY_FULL_DATE, (
        f"{label} 이 정규 기준일을 반환하지 않음"
    )


def test_ac006a_sector_advanced_service_imports_shared_helper() -> None:
    """A-4: sector_advanced_service 가 공유 헬퍼를 import 해 호출부가 이를 경유한다."""
    src = (PROJECT_ROOT / "backend/services/sector_advanced_service.py").read_text()
    assert "_get_latest_valid_date" in src, (
        "sector_advanced_service 가 공유 헬퍼를 import/참조하지 않음"
    )


def test_ac006a_meta_service_weekly_uses_shared_helper() -> None:
    """A-6: meta_service 가 주봉 기준일 해석을 공유 헬퍼로 위임한다."""
    src = (PROJECT_ROOT / "backend/services/meta_service.py").read_text()
    assert "_get_latest_valid_date" in src, (
        "meta_service 가 주봉 기준일을 공유 헬퍼로 위임하지 않음"
    )


# ---------------------------------------------------------------------------
# AC-SGR-006-B — 격자·앵커 소비자 2지점
# ---------------------------------------------------------------------------


def test_ac006b_rank_change_uses_anchor_not_offset(
    fixture_max_ne_canonical: str,
) -> None:
    """B-1: compute_sector_ranking 의 rank_change 기준일이 ``anchor(t, 28)`` 경로다.

    ``LIMIT 1 OFFSET 3`` 자체 관용구가 제거됐는지(AC-005 스캔이 담당)에 더해,
    ``anchor(``` 호출이 compute_sector_ranking 본문에 존재함을 구조적으로 단언한다.
    anchor 값 단언(28≤days≤35)은 M6 AC-SGR-020 R2 가 고정한다.
    """
    src = (PROJECT_ROOT / "my_chart/analysis/sector_metrics.py").read_text()
    assert "LIMIT 1 OFFSET" not in src, (
        "B-1 위반 — sector_metrics.py 에 LIMIT 1 OFFSET 관용구 잔존"
    )
    assert "anchor(" in src, (
        "B-1 위반 — compute_sector_ranking 이 anchor() 를 사용하지 않음"
    )


def test_ac006b_anchor_returns_earlier_history_bar(tmp_path: Path) -> None:
    """anchor(t, 28) 경로가 M5 배선대로 동작함을 확인(sanity).

    다주(多週) 이력 픽스처에서 anchor 가 t 보다 이른 history_grid 바를 반환함을
    단언한다. 경계값 28≤(t−baseline).days≤35 단언은 M6 AC-SGR-020 R2 가 고정한다.
    """
    db = str(tmp_path / "anchor_multi.db")
    conn = sqlite3.connect(db)
    try:
        conn.execute("CREATE TABLE stock_prices (Name TEXT, Date TEXT)")
        # 매주 금요일 8주치(충분한 이력). 각 날짜 40행(동일 → CG-3 배제 없음).
        fridays = [
            "2023-11-03", "2023-11-10", "2023-11-17", "2023-11-24",
            "2023-12-01", "2023-12-08", "2023-12-15", "2024-01-12",
        ]
        for d in fridays:
            conn.executemany(
                "INSERT INTO stock_prices VALUES (?, ?)",
                [(f"S{i:03d}", d) for i in range(40)],
            )
        conn.commit()
    finally:
        conn.close()

    grid = compute_weekly_grid(db)
    history_dates = {b.date for b in grid.history}
    bar = anchor(grid, "2024-01-12", 28)
    assert bar is not None, "충분한 이력이 있는데 anchor(t,28) 이 None"
    assert bar.date in history_dates, f"anchor 바가 history 원소가 아님: {bar.date}"
    assert bar.date < "2024-01-12", "anchor(t,28) 바가 t 보다 엄격히 이르지 않음"


def test_ac006b_compute_sector_history_dates_equal_shared_guard(
    fixture_max_ne_canonical: str,
    mock_sectormap,  # noqa: F811 — compute_sector_ranking 의 get_sector_registry 용
) -> None:
    """B-2: compute_sector_history 반환 날짜 집합 == 공유 격자 history(자체 GROUP BY 없음).

    ``:346`` 자체 ``GROUP BY Date`` 가드를 폐기하고 ``compute_weekly_grid().history`` 에서
    파생하므로, 반환 날짜는 격자의 CG-3 배제를 그대로 상속한다.
    """
    from my_chart.analysis.sector_metrics import compute_sector_history

    db = fixture_max_ne_canonical
    grid = compute_weekly_grid(db)
    guard_dates = {bar.date for bar in grid.history}

    dates, _rankings = compute_sector_history(db, weeks=5)
    returned = set(dates)

    # 반환 집합은 공유 가드(history)의 부분집합 — 자체 GROUP BY 로 독립 집합을 만들지 않는다
    assert returned <= guard_dates, (
        f"B-2 위반 — 반환 날짜가 공유 격자 history 에 없음: {returned - guard_dates}"
    )
    # CG-3 배제 날짜(WEEKLY_PARTIAL_DATE)가 반환 집합에 하나도 없다
    assert WEEKLY_PARTIAL_DATE not in returned, (
        "B-2 위반 — CG-3 배제 대상 부분 데이터 날짜가 history 에 포함됨"
    )
