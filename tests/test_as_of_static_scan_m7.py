# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M7 — §8.4 규약 8 게이팅 테스트 전수 정적 스캔.

``acceptance.md`` §8.4 규약 8: 게이팅 테스트는 `as_of="2026-08-11"`을 **명시
인자**로 전달한다. `as_of=None`(구현 기본값 → `date.today()`)에 의존하는 게이팅
호출을 금지한다.

이전 판(``tests/test_aggregation_fixture.py::test_gating_test_pins_as_of_explicitly``)
은 자기 파일 하나만 정적 스캔했다. 이 파일은 §8.4 규약 6이 열거하는 **7개 게이팅
테스트 파일 전부**를 대상으로 확장한다(M7 체크리스트 item 3).

acceptance.md §8.4 규약 8 원문에는 스캔 명령의 리터럴 코드 블록이 없다(산문 서술뿐).
따라서 이 스캔은 "acceptance.md에서 바이트 동일하게 추출"이 아니라 규약을 코드로
**최초 구현**한 것이며, 그 사실을 정직하게 기록한다(progress.md §E.2 참조).

AST 기반 — docstring/주석의 `as_of=None` 문자열(이 규약을 설명하는 산문)은 매치되지
않는다. 실제 함수 호출의 키워드 인자만 검사한다.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

GATING_FILES = [
    "test_sector_aggregation.py",
    "test_sector_benchmark_ranking.py",
    "test_ac_sag_024_high52.py",
    "test_ac_sag_030_rs_avg.py",
    "test_sag_m6_router_wiring.py",
    "test_golden_baseline.py",
    "test_aggregation_fixture.py",
]

#: 격자·집계·유니버스 진입점 함수명(§8.4 규약 8 대상).
ENTRY_POINTS = {
    "compute_weekly_grid",
    "compute_universe",
    "compute_sector_aggregates",
    "compute_sector_ranking",
    "anchor",
}

TESTS_DIR = Path(__file__).resolve().parent


def _call_name(node: ast.Call) -> str | None:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return None


@pytest.mark.parametrize("filename", GATING_FILES)
def test_no_as_of_none_literal_keyword(filename: str) -> None:
    """AST 기반 — `as_of=None` 키워드 인자가 실제 함수 호출에 0건이다."""
    path = TESTS_DIR / filename
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "as_of" and isinstance(kw.value, ast.Constant) and kw.value.value is None:
                violations.append(f"{filename}:{node.lineno} — as_of=None 키워드 인자")
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("filename", GATING_FILES)
def test_entry_point_calls_pass_as_of_explicitly(filename: str) -> None:
    """AST 기반 — 격자·집계·유니버스 진입점 호출에 `as_of=` 키워드(또는 그 함수의
    2번째 위치 인자에 값이 채워짐)가 누락된 호출이 0건이다.

    ``compute_sector_ranking(db_path, date, ...)`` 은 ``as_of`` 키워드가 없고
    ``date`` 를 위치 인자로 받는 별도 계약이므로(§8.4 규약 8은 as_of=None 기본값
    의존을 금지하는 것이지, 이 함수의 시그니처를 바꾸지 않는다) 이 함수는 위치
    인자 존재만 확인한다. ``anchor(grid, t, days)`` 도 동형(위치 인자 3개 필수,
    ``as_of`` 키워드가 없는 별도 계약)이다.
    """
    path = TESTS_DIR / filename
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    found_any = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in ENTRY_POINTS:
            continue
        found_any = True
        if name in ("compute_sector_ranking", "anchor"):
            # as_of 키워드가 없는 별도 계약 — 위치 인자 개수만 확인한다.
            min_args = 2 if name == "compute_sector_ranking" else 3
            if len(node.args) < min_args:
                violations.append(
                    f"{filename}:{node.lineno} — {name}() 필수 위치 인자 누락"
                )
            continue
        # compute_weekly_grid(path, as_of=None) / compute_universe(...) 등은
        # as_of 가 2번째 위치 인자로도 채워질 수 있다 — 키워드 또는 위치 인자
        # 둘 중 하나로 명시 값이 전달됐으면 규약 8을 만족한다(기본값 None 미의존).
        has_as_of_kw = any(kw.arg == "as_of" for kw in node.keywords)
        has_positional_as_of = len(node.args) >= 2
        if not (has_as_of_kw or has_positional_as_of):
            violations.append(f"{filename}:{node.lineno} — {name}() 호출에 as_of 값이 없다")
    if not found_any:
        pytest.skip(f"{filename} 에 격자·집계 진입점 호출이 없다(해당 없음)")
    assert not violations, "\n".join(violations)
