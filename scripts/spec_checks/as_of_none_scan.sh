#!/usr/bin/env bash
# SPEC-SECTOR-AGGREGATION-001 acceptance.md §8.4 규약 8 정적 스캔.
#
# 게이팅 테스트 파일에서 `as_of=None` 리터럴 사용 0건을 확인한다.
# `as_of=None`(구현 기본값 → date.today())에 의존하는 게이팅 호출을 금지한다.
#
# 사용법:
#   bash -n scripts/spec_checks/as_of_none_scan.sh   # 문법 검증
#   bash scripts/spec_checks/as_of_none_scan.sh       # 실행
#
# exit 0 = 위반 0건. exit 1 = 위반 발견(matched 라인을 stdout에 출력).
set -euo pipefail

GATING_FILES=(
  "tests/test_sector_aggregation.py"
  "tests/test_sector_benchmark_ranking.py"
  "tests/test_ac_sag_024_high52.py"
  "tests/test_ac_sag_030_rs_avg.py"
  "tests/test_sag_m6_router_wiring.py"
  "tests/test_golden_baseline.py"
  "tests/test_aggregation_fixture.py"
)

# 코드로서의 as_of=None(실제 함수 호출의 키워드 인자, 즉 `(...as_of=None...)` 형태)
# 만 대상으로 한다 — 이 규약을 설명하는 산문/docstring/에러 메시지 문자열 안의
# "as_of=None" 언급은 위반이 아니므로 제외한다. 이 grep은 1차 coarse 스캔이며,
# 정밀 판정(AST 기반, 실제 호출 구문만 매치, 문자열/주석 오탐 0)은
# tests/test_as_of_static_scan_m7.py::test_no_as_of_none_literal_keyword 가 담당한다.
MATCHES=$(grep -nE '[(,][[:space:]]*as_of=None[,)]' "${GATING_FILES[@]}" || true)

if [ -n "$MATCHES" ]; then
  echo "VIOLATION: as_of=None literal found in gating test files:"
  echo "$MATCHES"
  exit 1
fi

echo "PASS: 0 code-level as_of=None literal occurrences in ${#GATING_FILES[@]} gating test files (coarse grep; AST scan is authoritative)."
exit 0
