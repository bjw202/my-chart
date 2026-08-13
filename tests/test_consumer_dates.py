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

import ast
import re
import sqlite3
import subprocess
from collections import Counter
from pathlib import Path

import pandas as pd
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

# A-6 관측용 판별값: 두 날짜의 CHG_1W 를 다르게 둬, stock_meta.chg_1w 가 어느 날짜에서
# 왔는지 값으로 판별한다(순진한 경로면 PARTIAL 값이 실린다).
CHG_1W_ON_FULL = 0.1111
CHG_1W_ON_PARTIAL = 0.9999

# A-6(meta_service._rebuild) 용 일봉 기준일. 주봉 격자와 무관한 별도 축이다.
DAILY_DATE = "2024-01-15"


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
            "SMA20 REAL, SMA40 REAL, SMA40_Trend_4M REAL, CHG_1W REAL, CHG_1M REAL, "
            "CHG_3M REAL, Volume REAL, VolumeSMA10 REAL, MAX52 REAL)"
        )
        conn.execute(
            "CREATE TABLE relative_strength (Name TEXT, Date TEXT, RS_12M_Rating REAL)"
        )
        _row = lambda n, d, chg1w: (n, d, 100.0, 95.0, 93.0, 90.0, 89.0, chg1w, 0.05,
                                    0.10, 1_000_000.0, 800_000.0, 110.0)
        # 정상 날짜: 비인덱스 40행
        full_names = [REFERENCE_STOCK] + [f"STOCK{i:03d}" for i in range(39)]
        conn.executemany(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(n, WEEKLY_FULL_DATE, CHG_1W_ON_FULL) for n in full_names],
        )
        # 부분 데이터 날짜: 비인덱스 3행 (REFERENCE_STOCK 포함 — HARD 조건)
        partial_names = [REFERENCE_STOCK, "STOCK100", "STOCK101"]
        conn.executemany(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(n, WEEKLY_PARTIAL_DATE, CHG_1W_ON_PARTIAL) for n in partial_names],
        )
        conn.executemany(
            "INSERT INTO relative_strength VALUES (?,?,?)",
            [(n, WEEKLY_FULL_DATE, 80.0) for n in full_names]
            + [(n, WEEKLY_PARTIAL_DATE, 80.0) for n in partial_names],
        )
        conn.commit()
    finally:
        conn.close()


def _build_daily_db_for_meta(db_path: str, names: list[str]) -> None:
    """meta_service._rebuild 가 읽는 최소 일봉 스키마(레거시 분기: Minervini 컬럼 없음).

    ``_rebuild`` 는 ``SELECT MAX(Date) FROM stock_prices WHERE Name = REFERENCE_STOCK``
    으로 일봉 기준일을 잡으므로 REFERENCE_STOCK 일봉 행이 반드시 필요하다.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE stock_prices (Name TEXT, Date TEXT, Close REAL, Change REAL, "
            "EMA10 REAL, EMA20 REAL, SMA50 REAL, SMA100 REAL, SMA200 REAL, High52W REAL)"
        )
        conn.executemany(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(n, DAILY_DATE, 100.0, 0.01, 99.0, 98.0, 97.0, 96.0, 95.0, 120.0) for n in names],
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

ACCEPTANCE_MD = PROJECT_ROOT / ".moai" / "specs" / "SPEC-SECTOR-GRID-001" / "acceptance.md"

# acceptance.md §AC-SGR-005.2 의 규범 명령을 **문자 그대로** 담는다.
# [HARD] 옵션·제외를 테스트 판단으로 추가하지 않는다 — 추가가 필요하면 AC 를 먼저 개정한다.
# 바이트 동등은 test_ac005_grep_constant_is_byte_identical_to_acceptance 가 강제한다.
_AC005_GREP = r'''grep -rnE --include="*.py" \
     "MAX\(Date\)|max\(Date\)|DISTINCT Date|GROUP BY Date" \
     backend/services/ backend/routers/ my_chart/analysis/ \
  | grep -v "_test\|tests/" \
  | grep -v "my_chart/analysis/weekly_grid\.py"'''

# 3종 관용구(§1.2.1 I1~I3). 잔류 행을 (경로, 매칭 텍스트) 로 정규화할 때 쓰는 키.
_IDIOM_RE = re.compile(r"MAX\(Date\)|max\(Date\)|DISTINCT Date|GROUP BY Date")

# §1.2.2 allowlist — **실행 쿼리 지점** (상한 4).
# 축소 이력: v0.2.2 의 6 → v0.3.0 의 5(공허했던 chart_service.py 제거, 실측 grep -c → 0)
#   → 4 (L5 market_breadth.py 제거 — SPEC-MARKET-BREADTH-001 이 O-G6 을 격자로 전환).
EXECUTABLE_ALLOWLIST: set[tuple[str, str]] = {
    ("backend/routers/db.py", "MAX(Date)"),                    # L1 적재 상태 표시
    ("my_chart/analysis/sector_advanced.py", "DISTINCT Date"),  # L2 COUNT(개수)
    ("backend/services/meta_service.py", "MAX(Date)"),          # L3 일봉 (O-G7)
    ("my_chart/analysis/universe.py", "MAX(Date)"),             # L4 일봉 stale (O-G7)
}

# 비실행 산문 행(주석·docstring)은 실행 쿼리 상한과 **별도로** 집계한다 —
# 산문 증가가 실행 지점 상한을 잠식하지 못하게 한다(AC-SGR-005.3).
PROSE_ALLOWLIST: dict[tuple[str, str], int] = {
    ("my_chart/analysis/universe.py", "MAX(Date)"): 5,  # P1~P5 (:14/:35/:55/:99/:111)
}

# 기대 잔류 다중집합 = 실행 쿼리 5 + universe.py 산문 5 = 총 10행.
EXPECTED_RESIDUAL = Counter(dict.fromkeys(EXECUTABLE_ALLOWLIST, 1))
EXPECTED_RESIDUAL.update(PROSE_ALLOWLIST)


def _extract_ac005_command_from_acceptance() -> str:
    """acceptance.md §AC-SGR-005.2 직후의 첫 ```bash 펜스 본문을 반환."""
    text = ACCEPTANCE_MD.read_text(encoding="utf-8")
    anchor_idx = text.index("#### AC-SGR-005.2")
    fence_start = text.index("```bash", anchor_idx) + len("```bash\n")
    fence_end = text.index("```", fence_start)
    return text[fence_start:fence_end].rstrip("\n")


def _run_ac005_scan() -> tuple[str, int]:
    """AC-SGR-005 규범 스캔을 실행하고 ``(stdout, returncode)`` 를 반환."""
    proc = subprocess.run(
        ["bash", "-c", _AC005_GREP],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    return proc.stdout.strip(), proc.returncode


def _normalize_residual(output: str) -> Counter:
    """``경로:행:내용`` 행을 ``(경로, 매칭된 관용구 텍스트)`` 다중집합으로 정규화.

    판정 키에 **행 번호를 포함하지 않는다** — 무관한 편집으로 붉어지지 않고, 다른 줄을
    조용히 가리키지도 않는다(spec.md §1.2.1 상단 [HARD]).
    """
    keys: Counter = Counter()
    for line in output.splitlines():
        if not line.strip():
            continue
        path, _lineno, content = line.split(":", 2)
        m = _IDIOM_RE.search(content)
        assert m is not None, f"규범 스캔이 관용구 없는 행을 반환: {line!r}"
        keys[(path, m.group(0))] += 1
    return keys


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


def test_ac005_grep_constant_is_byte_identical_to_acceptance() -> None:
    """[HARD] ``_AC005_GREP`` 이 acceptance.md §AC-SGR-005.2 명령과 **바이트 동등**하다.

    **v0.3.0 개정 계기**: 0.2.2 의 규범 명령은 줄바꿈 이음(``\\``) 누락으로
    ``bash -n`` exit 2 였고, 테스트는 이를 신고하지 않고 **조용히 다른 명령을 썼다** —
    ``--include="*.py"`` 를 문서화 없이 추가하고 ``universe.py`` 제외를 파이프라인이
    아니라 Python 리스트 컴프리헨션으로 옮겼다. "acceptance.md grep 과 동일" 이라는
    주석과 달리 둘은 동일하지 않았다. 본 테스트가 그 드리프트를 기계적으로 차단한다.
    """
    expected = _extract_ac005_command_from_acceptance()
    assert _AC005_GREP == expected, (
        "AC-SGR-005.2 규범 명령과 테스트 상수가 다르다 (바이트 동등 위반).\n"
        f"--- acceptance.md ---\n{expected!r}\n--- _AC005_GREP ---\n{_AC005_GREP!r}"
    )


def test_ac005_grep_command_passes_bash_syntax_check() -> None:
    """[HARD] 규범 스캔 명령이 ``bash -n`` 을 **exit 0** 으로 통과한다.

    0.2.2 는 exit 2(``syntax error near unexpected token '|'``)여서 규범 명령을 있는
    그대로 실행할 수 없었다 — 실행 불가능한 규범은 검사가 아니다.
    """
    proc = subprocess.run(
        ["bash", "-n", "-c", _AC005_GREP], capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    assert proc.returncode == 0, (
        f"규범 명령이 bash -n 을 통과하지 못함 (exit={proc.returncode}): {proc.stderr}"
    )


def test_ac005_residual_set_equality_with_allowlist() -> None:
    """[HARD] 전수 스캔 잔류가 §1.2.2 allowlist 와 **집합 동등**하다.

    **제외 정규식 연쇄를 폐기하고 잔류 집합 동등으로 전환했다.** 이전 구조는 "제외
    패턴을 계속 덧붙여 0행을 만든다" 였고, 이는 **스캔을 점점 눈멀게 만드는 방향**이다
    — 정규식이 넓어질수록 진짜 위반도 함께 숨는다. 새 구조는 스캔을 넓게 유지하고
    잔류 전량을 allowlist 와 비교한다. 이는 이전보다 **엄격하다**: 초과(신규 위반)와
    부족(허용 지점 소실) **양쪽**이 모두 검출된다.

    대조: 주봉 소비자 한 곳을 순진한 경로로 되돌리면 잔류 집합에 **새 원소가 나타나**
    집합 동등이 깨진다.
    """
    output, _rc = _run_ac005_scan()
    observed = _normalize_residual(output)

    assert set(observed) == EXECUTABLE_ALLOWLIST, (
        "AC-SGR-005.2 잔류 집합 동등 위반.\n"
        f"  초과(신규 위반): {sorted(set(observed) - EXECUTABLE_ALLOWLIST)}\n"
        f"  부족(허용 지점 소실): {sorted(EXECUTABLE_ALLOWLIST - set(observed))}"
    )
    # 다중집합까지 고정 — 산문 행 증감(P1~P5)도 검출한다.
    assert observed == EXPECTED_RESIDUAL, (
        f"AC-SGR-005.2 잔류 다중집합 불일치.\n  실측: {dict(observed)}\n"
        f"  기대: {dict(EXPECTED_RESIDUAL)}"
    )
    assert sum(observed.values()) == 9, (
        f"기대 잔류 총 9행(실행 4 + 산문 5), 실측 {sum(observed.values())}행"
    )


def test_ac005_executable_allowlist_cap_is_four() -> None:
    """AC-SGR-005.3: 실행 쿼리 allowlist 지점 수가 **4개 이하**다.

    상한 축소 이력: v0.2.2 의 6 → v0.3.0 의 5(공허했던 ``chart_service.py`` 항목 제거
    — 실측 ``grep -c`` → 0, 3종 관용구를 하나도 갖지 않아 제외할 대상 자체가 없었다)
    → **4**(L5 ``market_breadth.py`` 제거 — SPEC-MARKET-BREADTH-001 이 §7 O-G6 을
    정규 주간 격자로 전환해 해당 관용구가 실측 0건이 되었다).
    **축소는 완화가 아니라 강화다** — 공허한 항목이 상한 1칸을 잠식해 실질 상한을
    부풀리고 있었다.
    """
    assert len(EXECUTABLE_ALLOWLIST) <= 4, (
        f"실행 쿼리 allowlist 상한 4 초과: {len(EXECUTABLE_ALLOWLIST)}개 — "
        f"신규 주봉 소비자를 allowlist 에 추가해 회피하는 경로는 여전히 위반이다"
    )
    # 산문 행은 실행 상한과 별도 집계 — 산문이 상한을 잠식하지 못한다.
    assert sum(PROSE_ALLOWLIST.values()) == 5


# AC-SGR-005.5 — 7개 모듈 전부의 격자 모듈 import (파일당 1개 테스트 케이스)
_GRID_MODULE = "my_chart.analysis.weekly_grid"
_EXPECTED_GRID_IMPORTS: list[tuple[str, tuple[str, ...]]] = [
    ("backend/services/sector_ranking_service.py", ("_get_latest_valid_date",)),
    ("backend/services/stage_service.py", ("_get_latest_valid_date",)),
    ("backend/services/market_service.py", ("_get_latest_valid_date",)),
    ("backend/services/meta_service.py", ("_get_latest_valid_date",)),
    ("backend/services/sector_advanced_service.py", ("_get_latest_valid_date",)),
    ("my_chart/analysis/sector_advanced.py", ("compute_weekly_grid",)),
    ("my_chart/analysis/sector_metrics.py", ("anchor", "compute_weekly_grid")),
]


@pytest.mark.parametrize(
    "rel_path,expected_symbols",
    _EXPECTED_GRID_IMPORTS,
    ids=[p for p, _ in _EXPECTED_GRID_IMPORTS],
)
def test_ac005_module_imports_grid_symbols(
    rel_path: str, expected_symbols: tuple[str, ...]
) -> None:
    """AC-SGR-005.5: 7개 파일 **전부**가 격자 모듈에서 기대 심볼을 import 한다.

    **7건을 개별 단언**한다 — 일부만 검사하면 나머지가 미배선인 채 통과한다(이전 판은
    ``sector_advanced_service`` 와 ``meta_service`` 2곳만 substring 으로 확인했다).
    파일당 1개 케이스로 보고되므로 어느 모듈이 미배선인지 실패 메시지에서 즉시 식별된다.

    판정은 substring 이 아니라 **AST 의 ImportFrom 노드**다 — 주석·docstring 안의
    심볼 이름이 통과시키지 못한다.
    """
    tree = ast.parse((PROJECT_ROOT / rel_path).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _GRID_MODULE:
            imported.update(alias.name for alias in node.names)

    missing = set(expected_symbols) - imported
    assert not missing, (
        f"AC-SGR-005.5 위반 — {rel_path} 가 {_GRID_MODULE} 에서 {sorted(missing)} 를 "
        f"import 하지 않음 (실측 import: {sorted(imported) or '없음'})"
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
        # A-4: sector_advanced_service — _get_latest_date def 삭제 후, 4개 호출부가 공유
        #      헬퍼를 직접 쓴다. **실제 진입점**(get_sector_bubble)의 응답 date 를 읽어,
        #      배선을 되돌리면 값이 갈라지도록 한다(공유 헬퍼 재호출은 자기 자신 검사였다).
        (
            lambda db: __import__(
                "backend.services.sector_advanced_service", fromlist=["get_sector_bubble"]
            ).get_sector_bubble(db).date,
            "A-4 sector_advanced_service.get_sector_bubble",
        ),
        # A-5: sector_advanced.py _get_dates (compute_weekly_grid 경유)
        (
            lambda db: __import__(
                "my_chart.analysis.sector_advanced", fromlist=["_get_dates"]
            )._get_dates(db, 1)[-1],
            "A-5 sector_advanced._get_dates",
        ),
    ],
)
def test_ac006a_resolver_returns_canonical_date(
    fixture_max_ne_canonical: str, resolver, label: str
) -> None:
    """기준일 해석자 각 지점이 정규 격자의 대표 바(WEEKLY_FULL_DATE)를 반환한다.

    **v0.3.0 반증력 복구**: 이전 판의 A-4·A-6 항목은 둘 다
    ``weekly_grid._get_latest_valid_date(db)`` 를 그대로 재호출했다 — 공유 헬퍼가
    자기 자신을 검사하는 구조라, ``sector_advanced_service`` 와 ``meta_service`` 의
    배선을 **전부 되돌려도 통과**했다. 광고된 6-way 대조는 실질 4-way 였다.
    A-4 는 실제 진입점 호출로, A-6 은 별도 테스트(rebuild_stock_meta 관측)로 옮겼다.
    """
    assert resolver(fixture_max_ne_canonical) == WEEKLY_FULL_DATE, (
        f"{label} 이 정규 기준일을 반환하지 않음"
    )


def test_ac006a_a6_meta_service_rebuild_uses_canonical_weekly_date(
    fixture_max_ne_canonical: str, tmp_path: Path, monkeypatch
) -> None:
    """A-6: ``meta_service._rebuild`` 의 **주봉** 기준일이 정규 대표 바다.

    **관측 방식**: ``_rebuild`` 는 ``latest_weekly_date`` 로 ``weekly.stock_prices`` 를
    조회해 ``stock_meta.chg_1w`` 를 채운다. 두 날짜의 ``CHG_1W`` 를 다르게 뒀으므로
    (CHG_1W_ON_FULL vs CHG_1W_ON_PARTIAL) 어느 날짜가 쓰였는지 **값으로 판별**된다 —
    정규 경로면 FULL 값, 순진한 ``MAX(Date) WHERE Name=REFERENCE_STOCK`` 이면
    PARTIAL 값이 실린다.

    **[HARD] 픽스처 전제**: ``REFERENCE_STOCK`` 이 부분 데이터 3행에 포함되어
    ``naive_max_for_reference_stock == WEEKLY_PARTIAL_DATE`` 여야 한다. 이 조건이
    없으면 순진한 경로도 FULL 날짜를 내므로 대조가 **무음 통과**한다. 전제를 먼저
    단언한다(acceptance.md AC-SGR-006-A `[HARD] A-6 전용 픽스처 조건`).
    """
    from backend.services.meta_service import rebuild_stock_meta

    weekly = fixture_max_ne_canonical

    # --- [HARD] 전제 단언: 순진한 기준종목 한정 MAX 가 PARTIAL 날짜여야 한다 ---
    conn = sqlite3.connect(weekly)
    try:
        naive_ref = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name = ?", (REFERENCE_STOCK,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert naive_ref == WEEKLY_PARTIAL_DATE, (
        "A-6 전제 위반 — REFERENCE_STOCK 이 부분 데이터 행에 없으면 대조가 무음 통과한다"
    )
    assert _get_latest_valid_date(weekly) == WEEKLY_FULL_DATE
    assert CHG_1W_ON_FULL != CHG_1W_ON_PARTIAL, "판별값이 같으면 관측이 불가능하다"

    # --- registry 를 픽스처 종목으로 한정(실제 xlsx 의존 제거) ---
    import my_chart.registry as reg

    reg_df = pd.DataFrame({
        "Code": ["005930"],
        "Name": [REFERENCE_STOCK],
        "Market": ["KOSPI"],
        "산업명(대)": ["전기전자"],
        "산업명(중)": ["반도체"],
        "주요제품": ["메모리"],
    })
    monkeypatch.setattr(reg, "_load_sectormap", lambda *a, **k: reg_df.copy())

    daily = str(tmp_path / "daily_for_meta.db")
    _build_daily_db_for_meta(daily, [REFERENCE_STOCK])

    rebuild_stock_meta(daily, weekly)

    conn = sqlite3.connect(daily)
    try:
        chg_1w = conn.execute(
            "SELECT chg_1w FROM stock_meta WHERE name = ?", (REFERENCE_STOCK,)
        ).fetchone()[0]
    finally:
        conn.close()

    assert chg_1w == pytest.approx(CHG_1W_ON_FULL), (
        f"A-6 위반 — stock_meta.chg_1w={chg_1w} 는 정규 대표 바({WEEKLY_FULL_DATE}, "
        f"{CHG_1W_ON_FULL})가 아니라 순진한 MAX({WEEKLY_PARTIAL_DATE}, "
        f"{CHG_1W_ON_PARTIAL}) 에서 왔다"
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
