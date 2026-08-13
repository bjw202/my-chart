# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 — AC-SAG-050 (INV-CAP-1 작성 규약의 기계적 집행).

`cap_eff` 축퇴를 리터럴 `0.10` 으로 잘못 적는 결함이 **네 번 따로** 적발됐다 —
AC-SAG-002(D16) / 003(D17) / 010(D22) / 041(N1). §0 INV-CAP-1 이 불변식을 한 곳에
못 박았지만 **문서에 적힌 규약은 새 AC 가 위반형으로 작성되는 것을 스스로 막지 못한다.**
이 파일이 그 집행 장치다 — 다섯 번째 사례가 작성되면 여기서 즉시 붉어진다.

스캔 명령은 acceptance.md AC-SAG-050 본문의 `grep` 을 **그대로** 실행한다. 손으로 옮겨
적은 스캔은 드리프트하므로(Lesson #9), 실행 전에 `bash -n` 으로 문법을 검증한다
(§8.4 규약 8 과 같은 관용).
"""
from __future__ import annotations

import shutil
import subprocess
import token
import tokenize
from pathlib import Path

import pytest

from my_chart.analysis.aggregate_types import WEIGHT_CAP as WEIGHT_CAP_VALUE

REPO = Path(__file__).resolve().parent.parent
ACCEPTANCE = REPO / ".moai" / "specs" / "SPEC-SECTOR-AGGREGATION-001" / "acceptance.md"

# --- acceptance.md AC-SAG-050 본문의 스캔 명령 (verbatim) --------------------

SCAN_1A = r"""grep -rnE '(capped_weight|weight_in_sector)[^=<>!]*[=!]=[^=]*0\.10?([^0-9]|$)' \
     my_chart/ backend/ tests/ --include='*.py'"""

SCAN_1B = r"""grep -rnE 'min\([^,]*,\s*(0\.10?|WEIGHT_CAP|weight_cap)\s*\)' \
     my_chart/ backend/ --include='*.py'"""

SCAN_2 = r"""grep -nE '(weight_in_sector|capped_weight)' \
     .moai/specs/SPEC-SECTOR-AGGREGATION-001/acceptance.md \
  | grep -vE 'cap_eff|mut_reintroduce_cap_literal' | grep -E '0\.10?([^0-9]|$)'"""

ALL_SCANS = {"scan-1a": SCAN_1A, "scan-1b": SCAN_1B, "scan-2": SCAN_2}


def _bash() -> str:
    path = shutil.which("bash")
    if path is None:                                    # pragma: no cover
        pytest.skip("bash 미설치 — 정적 스캔 실행 불가")
    return path


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run([_bash(), "-c", script], cwd=REPO,
                          capture_output=True, text=True)


@pytest.mark.parametrize("name", sorted(ALL_SCANS))
def test_ac_sag_050_scan_commands_are_syntactically_valid(name: str) -> None:
    """스캔 명령이 `bash -n` 문법 검증을 통과한다 — 손으로 옮겨 적은 드리프트 방지."""
    proc = subprocess.run([_bash(), "-n"], input=ALL_SCANS[name],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"{name} 문법 오류: {proc.stderr}"


def test_ac_sag_050_scan1_no_capped_weight_compared_to_cap_literal() -> None:
    """스캔 1a — 상한 적용 후 가중치를 `weight_cap` 리터럴과 비교하는 표현이 0건."""
    proc = _run(SCAN_1A)
    assert proc.stdout.strip() == "", (
        "INV-CAP-1 위반 — 상한 후 가중치를 0.10 리터럴과 비교한다:\n" + proc.stdout)


def test_ac_sag_050_scan1_no_min_cap_shortcut() -> None:
    """스캔 1b — `min(raw, 0.10)` 형태의 상한 적용이 0건(반드시 `cap_eff` 를 경유한다)."""
    proc = _run(SCAN_1B)
    assert proc.stdout.strip() == "", (
        "INV-CAP-1 위반 — cap_eff 를 경유하지 않고 상한을 적용한다:\n" + proc.stdout)


def test_ac_sag_050_scan2_spec_body_has_no_cap_literal_expectation() -> None:
    """스캔 2 — acceptance.md 본문에 `cap_eff` 없이 `0.10` 기대값을 적은 절이 0건."""
    proc = _run(SCAN_2)
    assert proc.stdout.strip() == "", (
        "acceptance.md 가 INV-CAP-1 작성 규약을 위반한다:\n" + proc.stdout)


def test_ac_sag_050_scan2_is_actually_capable_of_firing(tmp_path: Path) -> None:
    """대조 단언 `mut_reintroduce_cap_literal` 의 **검출력 실측**(§8.4 규약 10).

    상한 적용 후 가중치의 기대값을 `weight_cap` 리터럴로 적은 절(위반형)을 담은 사본에
    같은 스캔을 걸면 **1행 이상**을 반환한다. 원본을 건드리지 않고 사본으로 실증하므로
    이 테스트 자체는 SPEC 본문을 수정하지 않는다 — 원본 대상 되돌림 실증과 복원 후
    `git status --short` 공백은 progress.md §E.2 에 별도로 기록한다.
    """
    # 위반형 문자열을 **조립해서** 만든다 — 이 파일도 스캔 1의 대상(`tests/`)이므로
    # 리터럴로 적으면 스캔 1이 자기 자신을 잡는다(첫 실행에서 실제로 RED 였다).
    violating = "- **And** 상한이 적용된 종목의 `weight_in_sector {} {}` 이다.".format(
        "==", "0." + "10")
    copy = tmp_path / "acceptance.md"
    copy.write_text(
        ACCEPTANCE.read_text(encoding="utf-8") + "\n" + violating + "\n",
        encoding="utf-8")
    mutated_scan = SCAN_2.replace(
        ".moai/specs/SPEC-SECTOR-AGGREGATION-001/acceptance.md", str(copy))
    proc = _run(mutated_scan)
    assert proc.stdout.strip() != "", "위반형 절을 넣었는데도 스캔이 아무것도 잡지 못했다"


def test_ac_sag_050_weight_cap_has_a_single_definition_site() -> None:
    """`weight_cap` 상수가 **단일 정의 위치**에만 존재한다(spec.md D3).

    정의 지점(`aggregate_types.WEIGHT_CAP`)을 제외하면 가중 산출 경로에 `0.10` 리터럴이
    나타나지 않는다.
    """
    proc = _run(
        r"""grep -rn '^WEIGHT_CAP\s*=' my_chart/ backend/ --include='*.py'""")
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1, f"WEIGHT_CAP 정의가 {len(lines)}곳이다:\n{proc.stdout}"
    assert "my_chart/analysis/aggregate_types.py" in lines[0], lines[0]

    # 가중 산출 경로(실행 토큰)에는 상한 리터럴이 없다 — 기본값은 WEIGHT_CAP 심볼을
    # 참조한다. 주석·독스트링의 설명 문구는 산출 경로가 아니므로 토큰 단위로 판정한다.
    path = REPO / "my_chart" / "analysis" / "weighting.py"
    with path.open("rb") as fh:
        numbers = [
            tok.string for tok in tokenize.tokenize(fh.readline)
            if tok.type == token.NUMBER
        ]
    assert not [s for s in numbers if float(s) == WEIGHT_CAP_VALUE], (
        f"weighting.py 실행 경로에 상한 리터럴이 있다: {numbers}")
