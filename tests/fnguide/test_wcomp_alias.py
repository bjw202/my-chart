# SPEC-FNGUIDE-WCOMP-001: M2 계정명 단일 출처(fnguide/account_alias.py) 구조 테스트
"""계정명 표의 구조와 불변식만 검사한다(오프라인).

리더 동작(별칭 적용·접기·0 행 보충·가드 경고)은 M3의 AC-WC-002~010 테스트가
맡는다. 여기서는 표 자체가 SPEC과 분석 코드에 맞는지만 본다. 비교 기준은 손으로
옮겨 적지 않고 spec.md·analysis.py·실응답 fixture에서 실행 시점에 뽑는다(교훈 #9).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from fnguide import account_alias as aa

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / ".moai" / "specs" / "SPEC-FNGUIDE-WCOMP-001" / "spec.md"
ANALYSIS = REPO / "fnguide" / "analysis.py"
ALIAS_SRC = REPO / "fnguide" / "account_alias.py"
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "wcomp"

# spec.md D8·REQ-WC-010이 이름으로 지정한 대시보드 전용 필수 계정
DASHBOARD_ONLY = {"매출총이익", "매출원가", "영업활동으로인한현금흐름"}


def _norm(name: str) -> str:
    """REQ-WC-007 정규화: 공백과 \\xa0 제거."""
    return name.replace(" ", "").replace("\xa0", "")


def _fixture_names(code: str, consol: str) -> set[str]:
    """실응답 fixture(연간 세 재무제표)의 정규화 행 이름 집합."""
    names: set[str] = set()
    for ep in ("getFinIncome", "getFinBalance", "getFinCashFlow"):
        p = FIXTURE_DIR / f"{ep}_{code}_Y_{consol}.json"
        data = json.loads(p.read_text(encoding="utf-8"))["dataset"]["data"]
        names |= {_norm(r["NAME"]) for r in data}
    return names


def _analysis_labels() -> set[str]:
    """analysis.py가 df_fs_ann / df_fs_quar에서 문자열로 찾는 계정명."""
    src = ANALYSIS.read_text(encoding="utf-8")
    return set(re.findall(r'df_fs_(?:ann|quar)\.loc\["([^"]+)"\]', src))


def _spec_d7_list(marker: str) -> list[str]:
    """spec.md D7의 '소비 … 계정 N개' 줄에서 '소스 순서:' 뒤 계정명을 순서대로 뽑는다."""
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"- **{marker}"):
            return re.findall(r"`([^`]+)`", line.split("소스 순서:", 1)[1])
    raise AssertionError(f"spec.md에서 {marker} 줄을 찾지 못함")


def _alias_dict_literal_keys() -> list[str]:
    """account_alias.py의 ALIASES dict 리터럴 키를 소스 순서대로(중복 포함) 뽑는다."""
    tree = ast.parse(ALIAS_SRC.read_text(encoding="utf-8"))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) else None
        )
        if isinstance(target, ast.Name) and target.id == "ALIASES":
            return [k.value for k in node.value.keys]
    raise AssertionError("ALIASES 대입을 찾지 못함")


# --- (1) 일반 레이아웃 별칭표 ---


def test_alias_table_has_22_unique_entries_without_chains():
    keys = _alias_dict_literal_keys()
    assert len(keys) == 22
    assert len(set(keys)) == len(keys), "dict 리터럴에 중복 키가 있다"
    targets = list(aa.ALIASES.values())
    assert len(set(targets)) == len(targets), "두 원천이 같은 옛 이름으로 간다"
    assert not set(aa.ALIASES) & set(targets), "별칭이 다른 별칭의 원천이 된다(연쇄)"


def test_alias_sources_exist_in_general_layout_response():
    """별칭 원천은 실제 일반 레이아웃 응답(005930 C)에 있는 이름이어야 한다(오타 방지)."""
    names = _fixture_names("005930", "C")
    missing = sorted(set(aa.ALIASES) - names)
    assert missing == []


# --- (3) 필수 계정 목록 ---


def test_required_labels_equal_analysis_labels_plus_dashboard_only():
    req = list(aa.REQUIRED_LABELS)
    assert len(set(req)) == len(req)
    assert set(req) == _analysis_labels() | DASHBOARD_ONLY


@pytest.mark.parametrize("code,consol", [("005930", "C"), ("403870", "B"), ("330590", "B")])
def test_every_required_label_has_a_source(code, consol):
    """필수 계정마다 원명·별칭·0 행 보충 중 하나의 출처가 있다(일반 레이아웃 실응답)."""
    available = _fixture_names(code, consol) | set(aa.ALIASES.values()) | set(aa.ZERO_ROW_LABELS)
    assert sorted(set(aa.REQUIRED_LABELS) - available) == []


# --- (2) 0 행 보충 목록 ---


def test_zero_row_list_is_exactly_the_one_user_approved_label():
    assert aa.ZERO_ROW_LABELS == ("관계기업등지분관련투자자산",)
    assert set(aa.ZERO_ROW_LABELS) <= set(aa.REQUIRED_LABELS)
    # 응답에 원명도 별칭도 없을 때만 보충 대상이 의미가 있다
    assert not set(aa.ZERO_ROW_LABELS) & (_fixture_names("005930", "C") | set(aa.ALIASES.values()))


# --- (4) 재무제표 한정 개명 ---


def test_cashflow_rename_target_collides_with_no_consumed_label():
    assert aa.CASHFLOW_RENAMES == {"당기순이익": "당기순손익"}
    consumed = _analysis_labels() | set(aa.REQUIRED_LABELS) | set(aa.ALIASES.values())
    assert "당기순손익" not in consumed
    for path in ("fnguide/analysis.py", "fnguide/dashboard.py", "fnguide/analyzer.py"):
        assert "당기순손익" not in (REPO / path).read_text(encoding="utf-8")


# --- (5) 다중 행 필요 목록 ---


def test_multi_row_labels():
    assert aa.MULTI_ROW_LABELS == ("이자비용", "법인세비용")
    assert aa.MULTI_ROW_MIN == 2
    assert set(aa.MULTI_ROW_LABELS) <= _analysis_labels()


# --- (6) 접기 부모 코드 → 기타* ---


def test_fold_targets_are_the_four_other_accounts():
    assert aa.FOLD_PARENT_TO_OTHER == {
        "112830": "기타유동자산",
        "110010": "기타비유동자산",
        "131580": "기타유동부채",
        "130010": "기타비유동부채",
    }
    targets = set(aa.FOLD_PARENT_TO_OTHER.values())
    assert targets <= set(aa.REQUIRED_LABELS)
    assert targets <= set(aa.CONSUMED_ASSET_LABELS) | set(aa.CONSUMED_LIABILITY_LABELS)


@pytest.mark.parametrize("code,consol", [("005930", "C"), ("403870", "B"), ("330590", "B")])
def test_fold_parent_codes_are_the_four_subtotals(code, consol):
    """접기 부모 코드가 실응답에서 유동·비유동 자산·부채 소계 행이다."""
    data = json.loads(
        (FIXTURE_DIR / f"getFinBalance_{code}_Y_{consol}.json").read_text(encoding="utf-8")
    )["dataset"]["data"]
    by_code = {r["AC_CODE"]: _norm(r["NAME"]) for r in data}
    assert {c: by_code.get(c) for c in aa.FOLD_PARENT_TO_OTHER} == {
        "112830": "유동자산",
        "110010": "비유동자산",
        "131580": "유동부채",
        "130010": "비유동부채",
    }


# --- (7) 정합성 가드용 소비 계정 ---


def test_consumed_asset_labels_equal_spec_d7_in_order():
    assert list(aa.CONSUMED_ASSET_LABELS) == _spec_d7_list("소비 자산 계정 19개")
    assert len(aa.CONSUMED_ASSET_LABELS) == 19


def test_consumed_liability_labels_equal_spec_d7_in_order():
    assert list(aa.CONSUMED_LIABILITY_LABELS) == _spec_d7_list("소비 부채 계정 20개")
    assert len(aa.CONSUMED_LIABILITY_LABELS) == 20


def test_consumed_lists_are_disjoint_analysis_labels():
    assets, liabs = set(aa.CONSUMED_ASSET_LABELS), set(aa.CONSUMED_LIABILITY_LABELS)
    assert not assets & liabs
    assert (assets | liabs) <= _analysis_labels()


def test_layout_marker_and_selection_label():
    """레이아웃 표지(D3)는 매출액 별칭의 원천이고, 선택 판정 행(D2)은 개명 대상과 같은 이름이다."""
    assert aa.GENERAL_LAYOUT_MARKER == "매출액(수익)"
    assert aa.ALIASES[aa.GENERAL_LAYOUT_MARKER] == "매출액"
    assert aa.CONSOL_SELECTION_LABEL == "당기순이익"
    assert aa.CONSOL_SELECTION_LABEL in aa.CASHFLOW_RENAMES


def test_guard_totals_are_alias_targets():
    """가드가 비교하는 합계 행은 일반 레이아웃 별칭의 목적지다."""
    assert aa.ALIASES["자산총계"] == aa.ASSET_TOTAL_LABEL == "자산"
    assert aa.ALIASES["부채총계"] == aa.LIABILITY_TOTAL_LABEL == "부채"
