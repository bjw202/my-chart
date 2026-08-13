# coding: utf-8
"""SPEC-MARKET-BREADTH-001 — breadth 히스토리 정규 주간 격자 전환 수용 기준.

`tests/fixtures/frozen/weekly-2026-08-12/weekly.db` (프로즌 스냅샷) 위에서만 실행한다.
게이팅 AC: AC-MBR-001 / 002 / 003 / 008 / 010.

§3.0 반증력 규약 [HARD]
  본 파일의 모든 주 단언 우변은 **프로즌 리터럴**(문자열/정수)이다. 구현이 호출하는
  헬퍼(`history(compute_weekly_grid(db), 52)`)를 테스트가 다시 호출해 자기 자신과
  비교하는 형태(F2)를 주 단언으로 쓰지 않는다.

§1.4 개수는 판별자가 아니다 [설계상 핵심]
  현행 출하 구현(V0) / 올바른 구현(V★) / CG-2 누락(V1) 모두 52개를 반환한다.
  따라서 `len(...) == 52` 단독 단언은 아무것도 잡지 못한다(F4). 판별자는
  날짜 집합 — 첫 날짜 / 마지막 날짜 / span / 고유 ISO 주 수 — 이다.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

FROZEN_DB = str(
    Path(__file__).parent / "fixtures" / "frozen" / "weekly-2026-08-12" / "weekly.db"
)

# ---------------------------------------------------------------------------
# 프로즌 리터럴 — 갱신 지점 단일화 (plan.md R4)
#
# 스냅샷을 갱신하면 아래 블록 **전체**를 재도출해야 한다. 개별 테스트에 리터럴을
# 흩뿌리지 않는 이유가 이것이다.
# ---------------------------------------------------------------------------

# 진행 중인 주 판정 기준일. 프로즌 스냅샷 MANIFEST.md 의 `as_of` 와 동일해야 한다.
FROZEN_AS_OF = date(2026, 8, 12)

# AC-MBR-001 — 히스토리 날짜 경계 (V★ = 올바른 구현)
EXPECTED_FIRST_DATE = "2025-08-14"
EXPECTED_LAST_DATE = "2026-08-07"
EXPECTED_SPAN_DAYS = 358

# AC-MBR-002 — 진행 중인 주 (CG-2 배제 대상)
PARTIAL_WEEK_DATE = "2026-08-11"
PARTIAL_WEEK_ISO = (2026, 33)

# AC-MBR-003 — ISO 주 고유성
EXPECTED_WEEKS = 52

# AC-MBR-008 — PRESERVE baseline (M1 에서 **코드 변경 전에** 캡처했다)
BASELINE_DATE = "2026-07-31"
BASELINE_FIELDS = {
    "date": "2026-07-31",
    "market": "KOSPI",
    "pct_above_sma50": 24.242424242424242,
    "pct_above_sma200": 15.151515151515152,
    "nh_nl_ratio": 0.2,
    "nh_nl_diff": -3,
    "ad_ratio": 1.5,
    "total_stocks": 33,
}
BASELINE_COMPOSITE = 33.598484848484844

# AC-MBR-010 — 하류 소비자 창(`history[-8:]`) 양끝 앵커 + span 경계
# span 하한 47 은 V★ 52바 계열의 8바 창 45개 전수 실측 분포(48–50)의 바닥 48에서
# 1일 여유를 뺀 값이다. 46 이하로 내리면 V1(46)이 통과하므로 채택하지 않는다.
WINDOW_SIZE = 8
EXPECTED_WINDOW_FIRST = "2026-06-19"
EXPECTED_WINDOW_LAST = "2026-08-07"
WINDOW_SPAN_MIN = 47
WINDOW_SPAN_MAX = 56

# §3.0 변형표 — 각 변형의 (n, 첫 날짜, 마지막 날짜, span)
VARIANT_LITERALS = {
    "V*": (52, "2025-08-14", "2026-08-07", 358),
    "V0": (52, "2026-03-25", "2026-08-11", 139),
    "V1": (52, "2025-08-22", "2026-08-11", 354),
    "V2": (51, "2025-08-14", "2026-07-31", 351),
    "V3": (51, "2025-08-22", "2026-08-07", 350),
}


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """`compute_weekly_grid(db, as_of=None)` 의 벽시계를 프로즌 as_of 로 고정한다.

    `compute_breadth_history` 는 as_of 인자를 갖지 않으며 REQ-MBR-001 이 그 계약을
    `compute_weekly_grid(weekly_db_path, as_of=None)` 으로 못박는다. 따라서 CG-2
    (진행 중인 주 배제) 판정이 **벽시계에 의존**한다 — W33 이 실제로 종료되는 날부터는
    `2026-08-11` 이 더 이상 미완성 주가 아니게 되어 프로즌 리터럴이 코드 변경 없이
    깨진다. 프로덕션 시그니처를 바꾸지 않고 결정성을 얻기 위해 테스트에서만
    `date.today()` 를 고정한다.
    """
    from my_chart.analysis import weekly_grid

    class _FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return FROZEN_AS_OF

    monkeypatch.setattr(weekly_grid, "date", _FrozenDate)


@pytest.fixture
def frozen_history_dates(frozen_clock: None) -> list[str]:
    """구현이 반환한 히스토리 날짜 리스트(게이팅 AC 의 좌변)."""
    from my_chart.analysis.market_breadth import compute_breadth_history

    results = compute_breadth_history(FROZEN_DB, "KOSPI", weeks=EXPECTED_WEEKS)
    return [r.date for r in results]


# AC-MBR-005 — 이력 부족 합성 픽스처
SHORT_HISTORY_WEEKS = 10
SHORT_HISTORY_REQUEST = 52

_SHORT_DDL = """
CREATE TABLE stock_prices (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    Close REAL, SMA10 REAL, SMA40 REAL, CHG_1W REAL,
    MAX52 REAL, min52 REAL, Volume REAL, VolumeSMA10 REAL,
    PRIMARY KEY (Name, Date)
)
"""


@pytest.fixture
def short_history_db(tmp_path: Path) -> str:
    """ISO 주 10개만 담은 합성 주봉 DB (주당 1날짜, 진행 중인 주 없음).

    프로즌 스냅샷은 격자 이력이 345바이므로 "가용 이력 < 요청"을 재현할 수 없다.
    모든 날짜를 **금요일**로 잡아 CG-2(진행 중인 주) 판정이 벽시계와 무관하게
    항상 False 가 되도록 고정한다.
    """
    db_path = str(tmp_path / "short_history.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_SHORT_DDL)

    last_friday = date(2024, 3, 1)  # 금요일
    for week in range(SHORT_HISTORY_WEEKS):
        dt = (last_friday - timedelta(weeks=week)).isoformat()
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?)",
                (f"Stock{i}", dt, 100.0, 90.0, 80.0, 0.01, 120.0, 70.0, 1e6, 8e5),
            )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# 단언 술어 — 실제 구현과 변형 하네스가 **동일한** 술어를 공유한다.
#
# 이것이 하네스의 핵심이다: 아래 술어들이 각 변형에 대해 실제로 실패하는지를
# 먼저 실행으로 증명해야 "이 AC 가 무엇을 잡는가"라는 주장이 근거를 갖는다.
# (plan-audit iter-1 D1 — SPEC v0.1.0 의 "잡는 잘못된 구현" 열은 거짓 주장을
#  담고 있었고, 열을 *읽는* 리뷰는 그 거짓을 통과시켰다.)
# ---------------------------------------------------------------------------


def _span_days(dates: list[str]) -> int:
    return (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days


def _iso_weeks(dates: list[str]) -> set[tuple[int, int]]:
    return {date.fromisoformat(d).isocalendar()[:2] for d in dates}


def assert_ac_mbr_001(dates: list[str]) -> None:
    """히스토리 날짜 경계 — 프로즌 리터럴 3중 고정."""
    assert dates[0] == EXPECTED_FIRST_DATE, f"first={dates[0]}"
    assert dates[-1] == EXPECTED_LAST_DATE, f"last={dates[-1]}"
    assert _span_days(dates) == EXPECTED_SPAN_DAYS, f"span={_span_days(dates)}"


def assert_ac_mbr_002(dates: list[str]) -> None:
    """진행 중인 주(CG-2) 배제."""
    assert PARTIAL_WEEK_DATE not in dates, f"진행 중인 주 {PARTIAL_WEEK_DATE} 포함"
    last_iso = date.fromisoformat(dates[-1]).isocalendar()[:2]
    assert last_iso != PARTIAL_WEEK_ISO, f"마지막 바가 진행 중인 주 {last_iso}"


def assert_ac_mbr_003(dates: list[str]) -> None:
    """ISO 주 고유성 — 날짜 하나당 ISO 주 하나(1:1)."""
    weeks = _iso_weeks(dates)
    assert len(weeks) == EXPECTED_WEEKS, f"고유 ISO 주={len(weeks)}"
    assert len(dates) == EXPECTED_WEEKS, f"바 개수={len(dates)}"


def assert_ac_mbr_010(window: list[str]) -> None:
    """하류 소비자 창 — 양끝 앵커 리터럴 + span 경계.

    입력은 `history[-8:]` **창 자체**다. 판별자는 "며칠인가"가 아니라
    "어느 8개인가"이므로 (1) 양끝 앵커가 주 판별자이고 (2) span 은 보조다.
    """
    assert window[0] == EXPECTED_WINDOW_FIRST, f"창 시작={window[0]}"
    assert window[-1] == EXPECTED_WINDOW_LAST, f"창 끝={window[-1]}"
    span = _span_days(window)
    assert WINDOW_SPAN_MIN <= span <= WINDOW_SPAN_MAX, f"창 span={span}"


# ---------------------------------------------------------------------------
# 변형 구성 — 구현(`compute_breadth_history`)을 호출하지 않고 직접 만든다.
# ---------------------------------------------------------------------------


def _build_variants() -> dict[str, list[str]]:
    """§3.0 변형표의 날짜 집합을 각 변형의 **정의대로** 구성한다."""
    from my_chart.analysis.weekly_grid import compute_weekly_grid, history

    grid = compute_weekly_grid(FROZEN_DB, as_of=FROZEN_AS_OF.isoformat())
    v_star = [b.date for b in history(grid, 52).bars]

    # V0: 현행 출하 구현 — 원시 `DISTINCT Date ... ORDER BY Date DESC LIMIT 52`
    conn = sqlite3.connect(FROZEN_DB)
    try:
        rows = conn.execute(
            """SELECT DISTINCT Date FROM stock_prices
               WHERE Name NOT IN ('KOSPI', 'KOSDAQ')
               ORDER BY Date DESC
               LIMIT ?""",
            (52,),
        ).fetchall()
    finally:
        conn.close()

    return {
        "V*": v_star,
        "V0": sorted(r[0] for r in rows),
        "V1": grid.dates[-52:],                            # CG-2 누락
        "V2": v_star[:-1],                                 # off-by-one
        "V3": [b.date for b in history(grid, 51).bars],    # 오배선
    }


# ---------------------------------------------------------------------------
# AC-MBR-008 — PRESERVE: 단일 날짜 breadth 불변
# ---------------------------------------------------------------------------


def test_ac_mbr_008_single_date_breadth_preserved() -> None:
    """AC-MBR-008: `compute_breadth`(:85) 의 모든 수치 필드가 baseline 과 동등하다.

    우변은 M1 이 **코드 변경 전에** 캡처한 리터럴이다. 히스토리 날짜 집합이 바뀌어도
    개별 날짜의 breadth 값은 바뀌면 안 된다(범위 이탈 탐지).
    """
    from my_chart.analysis.market_breadth import compute_breadth, compute_breadth_composite

    result = compute_breadth(FROZEN_DB, "KOSPI", BASELINE_DATE)

    for field_name, expected in BASELINE_FIELDS.items():
        assert getattr(result, field_name) == expected, field_name
    assert compute_breadth_composite(result) == BASELINE_COMPOSITE


# ---------------------------------------------------------------------------
# 게이팅 AC — 프로즌 스냅샷 위 실제 구현
# ---------------------------------------------------------------------------


def test_ac_mbr_001_history_date_boundaries(frozen_history_dates: list[str]) -> None:
    """AC-MBR-001: 첫 날짜 / 마지막 날짜 / span 3중 프로즌 리터럴 고정.

    잡는 잘못된 구현: V0 / V1 / V2 / V3 (네 변형 전부 — 하네스가 실행으로 증명).
    """
    assert_ac_mbr_001(frozen_history_dates)


def test_ac_mbr_002_partial_week_excluded(frozen_history_dates: list[str]) -> None:
    """AC-MBR-002: 진행 중인 주(W33 = 2026-08-11) 를 반환 집합에서 제외한다.

    `2026-08-11` 은 프로즌 DB 에 33행을 갖고 **실재**하므로, 격자 규칙을 적용하지
    않으면 반드시 반환 집합에 들어온다 — 존재하지 않는 날짜의 부재를 단언하는 것이
    아니다. AC-MBR-003 이 잡지 못하는 V1 의 사각을 이 단언이 메운다.
    """
    assert_ac_mbr_002(frozen_history_dates)


def test_ac_mbr_003_iso_week_uniqueness(frozen_history_dates: list[str]) -> None:
    """AC-MBR-003: 날짜 하나당 ISO 주 하나(1:1) — 다중 날짜 주 중복 소멸.

    잡는 잘못된 구현: V0 전용(52 날짜 / 21 ISO 주). 개수 단언만으로는 V0 을 잡지
    못하므로(§1.4, F4) 고유 주 수가 실제 판별자다.
    """
    assert_ac_mbr_003(frozen_history_dates)


# ---------------------------------------------------------------------------
# AC-MBR-005 — 이력 부족의 비침묵 공개 (REQ-MBR-004)
# ---------------------------------------------------------------------------


def test_ac_mbr_005_insufficient_history_is_disclosed(
    short_history_db: str, caplog: pytest.LogCaptureFixture
) -> None:
    """AC-MBR-005: 요청보다 적게 반환할 때 요청값과 반환 개수를 **둘 다** 남긴다.

    반환 타입 `list[BreadthResult]` 는 소비자 계약이라 바꾸지 않으므로(§4) 공개
    채널은 로그다. 레벨만 확인하거나 레코드 개수만 세는 검사는 금지한다 — 어느
    값이 부족했는지 식별할 수 없으면 진단 가치가 없다.

    잡는 잘못된 구현: 요청보다 적게 반환하면서 아무 신호도 남기지 않는 조용한 축소.
    """
    from my_chart.analysis.market_breadth import compute_breadth_history

    with caplog.at_level(logging.WARNING):
        results = compute_breadth_history(
            short_history_db, "KOSPI", weeks=SHORT_HISTORY_REQUEST
        )

    assert len(results) == SHORT_HISTORY_WEEKS
    assert any(
        str(SHORT_HISTORY_REQUEST) in r.message and str(SHORT_HISTORY_WEEKS) in r.message
        for r in caplog.records
    ), f"요청값/반환 개수를 함께 담은 WARNING 부재: {[r.message for r in caplog.records]}"


def test_ac_mbr_005_sufficient_history_is_silent(
    frozen_clock: None, caplog: pytest.LogCaptureFixture
) -> None:
    """이력이 충분하면 경고를 남기지 않는다 — 경고의 신호 가치를 지킨다.

    이 단언이 없으면 "항상 경고를 남기는" 구현도 위 테스트를 통과한다.
    """
    from my_chart.analysis.market_breadth import compute_breadth_history

    with caplog.at_level(logging.WARNING):
        compute_breadth_history(FROZEN_DB, "KOSPI", weeks=EXPECTED_WEEKS)

    assert [r.message for r in caplog.records] == []


# ---------------------------------------------------------------------------
# AC-MBR-007 — 기간 표기 3중 일치 (REQ-MBR-005)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent

# O-M3 확정 문구 — 각 표면과 **바이트 동등**으로 고정한다.
# 기존 차트 제목이 영문 + 범례 설명이 한글인 현 스타일을 유지하는 최소 변경이다.
CHART_TITLE_LITERAL = "Market Breadth (1-year)"
ROUTER_DOC_LITERAL = "1-year (52-week) history"

STALE_PERIOD_LITERAL = "12-week"


def test_ac_mbr_007_period_label_consistency() -> None:
    """AC-MBR-007: 기간 문구를 실제 호출부의 `weeks` 인자와 일치시킨다.

    셋째 조건이 나머지 둘과 **반대 방향**이라는 점이 이 AC 의 핵심이다 — 라벨을
    맞추는 가장 쉬운 방법(호출부를 12로 내리기)을 셋째 조건이 명시적으로 차단한다.

    잡는 잘못된 구현: (a) 백엔드 docstring 만 고치고 사용자가 실제로 보는 차트
    제목(P2)을 방치, (b) 반대로 프론트만 고침, (c) 라벨 대신 호출부를 12로 낮춰
    이미 출하된 정보량을 축소(§1.6 판정 위반).
    """
    router = (_REPO_ROOT / "backend" / "routers" / "market.py").read_text(encoding="utf-8")
    chart = (
        _REPO_ROOT / "frontend" / "src" / "components" / "MarketOverview" / "BreadthChart.tsx"
    ).read_text(encoding="utf-8")
    service = (
        _REPO_ROOT / "backend" / "services" / "market_service.py"
    ).read_text(encoding="utf-8")

    # P1 — 백엔드 docstring
    assert STALE_PERIOD_LITERAL not in router
    assert ROUTER_DOC_LITERAL in router

    # P2 — 사용자가 실제로 보는 차트 제목
    assert STALE_PERIOD_LITERAL not in chart
    assert CHART_TITLE_LITERAL in chart

    # P3 — 정본. 라벨을 맞추려고 호출부를 12로 낮추는 경로를 차단한다.
    calls = [
        line for line in service.splitlines() if "compute_breadth_history(" in line
    ]
    assert len(calls) == 1, calls
    assert "weeks=52" in calls[0], calls[0]


# ---------------------------------------------------------------------------
# 변형 하네스 — "AC 가 실제로 잡는지"를 구현 전에 증명한다 (M1 진입 게이트)
# ---------------------------------------------------------------------------


def test_variant_literals_match_spec_table() -> None:
    """변형 하네스 자체를 프로즌 리터럴에 고정한다.

    하네스가 잘못 구성되면(예: V1 을 `grid.history[-52:]` 로 잘못 만들면) 아래
    catch 행렬이 무의미해진다. 이 테스트가 하네스의 무결성을 지킨다.
    """
    variants = _build_variants()
    actual = {
        name: (len(d), d[0], d[-1], _span_days(d)) for name, d in variants.items()
    }
    assert actual == VARIANT_LITERALS


# (AC 이름, 술어, 창 입력 여부) — 술어는 게이팅 테스트와 **같은 함수**다.
_PREDICATES = {
    "AC-MBR-001": assert_ac_mbr_001,
    "AC-MBR-002": assert_ac_mbr_002,
    "AC-MBR-003": assert_ac_mbr_003,
}

# 실측한 catch 행렬. True = 이 AC 가 이 변형을 **잡는다**(AssertionError).
# 이 표는 SPEC 의 "잡는 잘못된 구현" 열을 옮겨 적은 것이 **아니라**, M1 에서 각
# 술어에 각 변형을 실제로 투입해 관측한 결과다(plan-audit iter-1 D1 이월 사항).
_CATCH_MATRIX = [
    ("AC-MBR-001", "V*", False),
    ("AC-MBR-001", "V0", True),
    ("AC-MBR-001", "V1", True),
    ("AC-MBR-001", "V2", True),
    ("AC-MBR-001", "V3", True),
    ("AC-MBR-002", "V*", False),
    ("AC-MBR-002", "V0", True),
    ("AC-MBR-002", "V1", True),
    ("AC-MBR-002", "V2", False),   # AC-MBR-001 이 전담
    ("AC-MBR-002", "V3", False),   # AC-MBR-001 이 전담
    ("AC-MBR-003", "V*", False),
    ("AC-MBR-003", "V0", True),
    ("AC-MBR-003", "V1", False),   # V1 은 CG-1 을 올바로 적용 → AC-MBR-002 가 전담
    ("AC-MBR-003", "V2", True),
    ("AC-MBR-003", "V3", True),
]


@pytest.mark.parametrize(("ac_name", "variant_name", "should_catch"), _CATCH_MATRIX)
def test_variant_harness_catch_matrix(
    ac_name: str, variant_name: str, should_catch: bool
) -> None:
    """각 AC 술어가 각 변형을 잡는지/놓치는지를 **실행으로** 확인한다.

    `should_catch=False` 행도 함께 고정한다 — "이 AC 는 이 변형을 잡지 못한다"는
    한계를 명문화해, 다른 AC 가 그 사각을 메우고 있음을 회귀로 보호한다.
    """
    variants = _build_variants()
    predicate = _PREDICATES[ac_name]
    dates = variants[variant_name]

    if should_catch:
        with pytest.raises(AssertionError):
            predicate(dates)
    else:
        predicate(dates)
