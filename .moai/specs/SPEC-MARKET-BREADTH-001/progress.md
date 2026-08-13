# SPEC-MARKET-BREADTH-001 — 진행 기록

> Tier **S** / Route **A**(Hybrid Trunk main-direct) / 산출물 `spec.md` + `plan.md` + 본 파일

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-08-13
spec_version: "0.1.1"
tier: S
route: A
```

### plan-auditor 판정 (iter-1)

| 항목 | 값 |
| --- | --- |
| Verdict | **PASS-WITH-DEBT** |
| Overall Score | **0.85** (Tier S 임계 0.75) |
| Iteration | 1 / 3 |
| Must-Pass | **7 / 7** (MP-4·MP-7은 N/A 자동 통과) |
| 리포트 | `.moai/reports/plan-audit/SPEC-MARKET-BREADTH-001-review-1.md` |

| 차원 | 점수 |
| --- | ---: |
| Clarity | 0.90 |
| Completeness | 0.85 |
| Testability | 0.80 |
| Traceability | 0.85 |

감사자는 본 SPEC의 프로즌 리터럴 전량(V0 `52/2026-03-25/2026-08-11/139/21주`, V★ `52/2025-08-14/2026-08-07/358/52주`, V1 354, V2 351, V3 350, 385/346/345 원시·격자·히스토리, 다중 날짜 주 21개)을 독립 재현했고 전부 일치했다. 중심 함정(§1.4 — 개수 52는 V0·V★·V1 모두에서 동일하므로 판별자가 아니다)도 확인됐다. 기존 테스트 baseline `20 passed`도 독립 확인됐다.

### D1~D6 처분 (v0.1.1에서 전량 수리)

| # | 심각도 | 처분 | 요지 |
| --- | --- | --- | --- |
| **D1** | SHOULD-FIX | **수리 완료** | AC-MBR-010의 거짓 반증 주장 철회. 실측상 `history[:8]` span=49로 올바른 창(49)과 동일 → span 경계로는 판별 불가. **창 양끝 프로즌 리터럴 앵커**(`2026-06-19`/`2026-08-07`)를 신설해 실제로 잡도록 강화(실측 검증). 잡지 못하는 것(V3, 소비자 코드 변경)도 명시 고지 |
| **D2** | SHOULD-FIX | **수리 완료** | AC-MBR-004에 §3.0 (c) 필수 2절 추가. 실측 결과 V0/V1/V2/V3 전부 실패(판별력 있음)이나, 좌·우변이 같은 `compute_weekly_grid` 객체 파생이라는 **F2 근접 조건부 항진명제**임을 명시 공개하고 비게이팅 유지 사유로 연결 |
| **D3** | MINOR | **수리 완료** | L202 `뿐` 주장을 AC-MBR-003으로 범위 한정. V1이 AC-MBR-001의 세 리터럴을 **전부** 위반한다는 실측을 본문에 병기 |
| **D4** | MINOR | **수리 완료** | O-M1 근거 정정. `breadth.kosdaq`는 스키마 선언만 있고 `market_service.py` 0건·프론트 렌더 0건 → 동일성은 **잠재적(latent)이며 사용자 비가시**. 범위 제외 판정은 유지(오히려 강화) |
| **D5** | MINOR | **수리 완료** | AC-MBR-008에 감사 시점 독립 교차검증값 기록. **AC의 단언 우변이 아님**을 명시 — 계약은 "M1이 코드 변경 전에 직접 캡처"이며 이 값은 대조용 참조 |
| **D6** | MINOR | **수리 완료** | AC-MBR-010 span 하한 49 → **47**. 8바 창 45개 전수 실측 분포 48–50(48일 2건) 대비 여유 1일 확보. 46 이하는 V1(46)이 통과하므로 채택하지 않음 → 판별력 무손실. plan.md **R4 노후화 리터럴 목록에 등재** |

**이월(deferred) 없음.** 감사 리포트가 "opportunistically 수리, 블로킹 아님"으로 분류한 D3/D4/D5도 전량 수리했다.

### plan-audit 이월 항목 (run 단계 강제)

- **M6 리뷰는 "잡는 잘못된 구현" 열을 읽지 않고 실행한다.** D1이 그 열 자체가 거짓일 수 있음을 증명했으므로, 열에 이름 붙은 변형을 실제로 구성해 단언에 투입하고 실패를 관측한 축자 출력만이 증거로 인정된다. `spec.md` §9 품질 게이트 + `plan.md` M6 양쪽에 명문화됨

### 미결 질문 (사용자 확인 대기)

| # | 상태 |
| --- | --- |
| **O-M1** | 대기 — `compute_breadth`의 `market` 인자 미사용 필터가 의도인가 미구현인가. 동일성은 잠재적이며 사용자 비가시(D4 실측) |
| **O-M2** | 대기 — `detect_choppy` 입력 창 확대(§5 C6) 시 phase/choppy 판정 변화가 바람직한가. M6에서 실측 후 승격 |
| **O-M3** | 대기 — P2 차트 제목 최종 문구. M4에서 확정 + 테스트 상수 바이트 동등 고정 |
| **O-G7** | 범위 밖(§7.1) — 선행 SPEC allowlist 잔류 |

---

## §E.2 Run-phase Evidence

### M1 baseline 캡처 대조 (코드 변경 전, `9dfb74d` 무수정 트리)

| 항목 | M1 자체 캡처 | plan-audit iter-1 교차검증값 | 판정 |
| --- | --- | --- | --- |
| `pct_above_sma50` | `24.242424242424242` | `24.242424242424242` | 일치 |
| `pct_above_sma200` | `15.151515151515152` | `15.151515151515152` | 일치 |
| `nh_nl_ratio` / `nh_nl_diff` | `0.2` / `-3` | `0.2` / `-3` | 일치 |
| `ad_ratio` / `total_stocks` | `1.5` / `33` | `1.5` / `33` | 일치 |
| `compute_breadth_composite` | `33.598484848484844` | `33.598484848484844` | 일치 |

§3.0 변형표 리터럴(V0 `52/2026-03-25/2026-08-11/139/21주`, V★ `52/2025-08-14/2026-08-07/358/52주`,
V1 `354`, V2 `351`, V3 `350`)도 전량 독립 재현해 일치했다. 불일치 0건이므로 M2 로 진행했다.

### AC PASS/FAIL 행렬

| AC | 판정 | 검증 명령 | 실제 출력 |
| --- | --- | --- | --- |
| AC-MBR-001 | **PASS** | `pytest -k ac_mbr_001` | `1 passed` (RED→GREEN: M1 `first=2026-03-25` 실패 → M2 통과) |
| AC-MBR-002 | **PASS** | `pytest -k ac_mbr_002` | `1 passed` (RED→GREEN: M1 `진행 중인 주 2026-08-11 포함` 실패 → M2 통과) |
| AC-MBR-003 | **PASS** | `pytest -k ac_mbr_003` | `1 passed` (RED→GREEN: M1 `고유 ISO 주=21` 실패 → M2 통과) |
| AC-MBR-004 | **XPASS (비게이팅)** | `pytest -rX -k ac_mbr_004` | `1 xpassed` — 창 집합 동등 성립. F2 근접 조건부 항진명제이므로 `xfail(strict=False)` 로 리포트만 남긴다 |
| AC-MBR-005 | **PASS** | `pytest -k ac_mbr_005` | `2 passed` (RED→GREEN: `요청값/반환 개수를 함께 담은 WARNING 부재: []` → 통과). 이력 충분 시 침묵 대조 포함 |
| AC-MBR-006 | **PASS** | `grep -nE '<3종 관용구>' my_chart/analysis/market_breadth.py` | 매칭 0건, `exit=1`. 되돌림 사본에서 `DISTINCT Date` 매칭 `exit=0` (검출력 증명) |
| AC-MBR-007 | **PASS** | `pytest -k ac_mbr_007` | `1 passed` (RED→GREEN: `assert '12-week' not in router` 실패 → 통과). 호출부 `weeks=52` 유지 확인 |
| AC-MBR-008 | **PASS** | `pytest -k ac_mbr_008` | `1 passed` — 전 필드 + composite 가 M1 baseline 리터럴과 동등 |
| AC-MBR-009 | **PASS (한계 명시)** | `pytest tests/test_market_breadth.py -q` | `20 passed`. `<= 4` → `== 4` 승격 완료. 해당 픽스처는 주당 1날짜라 V0/V★ 결과가 동일 — 핵심 결함을 잡지 못하며 기대해서도 안 된다 |
| AC-MBR-010 | **PASS** | `pytest -k ac_mbr_010` | `8 passed` (본 단언 1 + 변형 하네스 7) |

### 변형 실행 행렬 [HARD — 열을 읽지 않고 실행했다]

축자 출력: `.moai/state/verify/SPEC-MARKET-BREADTH-001/variant-matrix.log`

| 변형 | 적용 방법 | AC-MBR-001 | AC-MBR-002 | AC-MBR-003 | AC-MBR-010 |
| --- | --- | --- | --- | --- | --- |
| V★ 올바른 구현 | `history(grid, 52)` | PASS | PASS | PASS | PASS |
| V0 현행 출하 | 원시 `DISTINCT Date … LIMIT 52` (테스트 내 직접 쿼리) | **CATCH** `first=2026-03-25` | **CATCH** `진행 중인 주 2026-08-11 포함` | **CATCH** `고유 ISO 주=21` | **CATCH** `창 시작=2026-07-16` |
| V1 CG-2 누락 | `grid.dates[-52:]` | **CATCH** `first=2025-08-22` | **CATCH** `진행 중인 주 2026-08-11 포함` | PASS (CG-1 은 올바름) | **CATCH** `창 시작=2026-06-26` |
| V2 off-by-one | `history(grid,52).bars[:-1]` | **CATCH** `last=2026-07-31` | PASS | **CATCH** `고유 ISO 주=51` | **CATCH** `창 시작=2026-06-12` |
| V3 오배선 | `history(grid, 51)` | **CATCH** `first=2025-08-22` | PASS | **CATCH** `고유 ISO 주=51` | PASS (문서화된 한계 — 마지막 8바가 V★ 와 동일) |
| 창 오배선 앞쪽 | `history[:8]` | — | — | — | **CATCH** `창 시작=2025-08-14` |
| 창 오배선 2배 | `history[-16:]` | — | — | — | **CATCH** `창 시작=2026-04-24` |
| AC-006 스캔 되돌림 | 임시 사본에 원시 쿼리 재삽입 | — | — | — | 스캔 `exit=0` + `DISTINCT Date` 매칭 |

세 개의 PASS 는 전부 **사전에 문서화된 한계**이며 결함이 아니다. AC-MBR-002×V2/V3 는
AC-MBR-001 이, AC-MBR-003×V1 은 AC-MBR-002 가, AC-MBR-010×V3 는 AC-MBR-001(`span == 358`)이
각각 전담한다. 이 PASS 행들도 하네스에 `should_catch=False` 로 고정해 회귀로 보호한다.

**M2 docstring 사건**: M5 의 AC-MBR-006 스캔이 M2 에서 내가 작성한 docstring 의
`DISTINCT Date` 리터럴을 잡아냈다. 산문 잔류만으로도 선행 SPEC 의 잔류 집합 동등을
통과시켜 제거를 **가리고 있었다**(선행 스위트가 M2 직후에도 84 passed 로 초록이었던 이유).
AC-MBR-006 이 없었다면 이 은폐가 그대로 출하됐다.

### 회귀 — 전체 스위트

| 구간 | passed | failed | skipped | xpassed | errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline (`9dfb74d`) | 584 | 8 | 68 | 0 | 25 |
| M6 종료 | **618** | 8 | 68 | 1 | 25 |

델타 `+34 passed / +1 xpassed` 는 전량 신규 `tests/test_market_breadth_grid.py` 이며
실패·에러 집합은 불변이다. 기존 8건(`test_screen_service` ×3, `test_rs_line` ×2,
`test_meta_service` ×2, `test_api` ×1)과 `tests/fnguide/` 25 에러는 사전 존재 항목으로
본 SPEC 범위 밖이다. 축자: `.moai/state/verify/SPEC-MARKET-BREADTH-001/full-suite.log`.

프론트엔드: `npx vitest run src/components/MarketOverview` → `5 files / 50 passed`.

### 교차 SPEC — 선행 allowlist 정리 (M5, plan.md R2)

| 시점 | 선행 게이팅 스위트 |
| --- | --- |
| M2 직후 | `84 passed` (docstring 리터럴이 L5 잔류를 유지해 은폐) |
| M5 docstring 수정 직후 | `83 passed / 1 failed` — `test_ac005_residual_set_equality_with_allowlist` (부족: L5 소실) |
| M5 동기화 완료 | **`84 passed`** (baseline 복귀) |

`acceptance.md` 기대 잔류 표(10행 → 9행) · 상한(5 → 4) · 품질 게이트 체크리스트와
`tests/test_consumer_dates.py` 의 `EXECUTABLE_ALLOWLIST` · 상한 단언 · 총행수를 함께 옮겼다.
집합 동등과 상한은 반드시 동시에 움직여야 한다 — 하나만 고치면 선행이 붉어진다.
되돌림은 필요하지 않았다.

**미수행 잔여 [후속 필요]**: allowlist 원본 표인 선행 `spec.md` §1.2.2 의 L5 행과
§7 O-G6 항목은 갱신하지 않았다. plan.md M5 가 승인한 범위가 `acceptance.md` 로 한정되며,
완료된 SPEC 의 `spec.md` 본문 수정은 별도 결정 사안이다. 두 곳은 여전히 L5 를 유효한
allowlist 항목으로, O-G6 을 미결로 기술한다. `acceptance.md` amendment 블록에 명시했다.

### 릴리스 노트 반영 대상 (spec.md §5 C1~C6 — sync 단계 CHANGELOG 소관)

`CHANGELOG` · `README` 는 plan.md §G PRESERVE 대상이므로 run 단계에서 편집하지 않고
아래 문구를 sync 단계로 인계한다. **전부 의도된 변화이며 되돌림 대상이 아니다.**

| # | 변화 | 프로즌 실측 |
| --- | --- | --- |
| C1 | 시장 개요 breadth 차트의 구간이 크게 늘어난다 | span 139일 → **358일** (약 20주 → 52주) |
| C2 | **포인트 개수는 그대로 52다** — "점이 줄었다"는 신고는 이 변경 때문이 아니다 | 52 → 52 |
| C3 | x축 간격이 균등해진다 (다중 날짜 주 중복 소멸) | 고유 ISO 주 21 → **52** |
| C4 | 차트의 마지막 점이 현재 주가 아니라 직전 완료 주가 된다 | 2026-08-11(진행 중) → **2026-08-07** |
| C5 | 차트 제목이 "12-week" 에서 1년 기준 문구로 바뀐다 | `Market Breadth (1-year)` |
| C6 | `detect_choppy` 판정이 바뀔 수 있다 | 프로즌 실측에서는 **변화 없음** (아래 O-M2) |

### 미결 질문 (사용자 확인 대기)

| # | 상태 |
| --- | --- |
| **O-M1** | **대기 — 코드 미변경.** `compute_breadth` 의 `market` 인자가 종목을 필터하지 않는 동작을 run 단계에서 관측했으나 plan.md R5 에 따라 기록만 하고 건드리지 않았다. `"KOSPI"` 와 `"KOSDAQ"` 은 여전히 동일 모집단 위에서 계산되며, 동일성은 잠재적(latent)이고 사용자 비가시다(D4 실측). 의도인지 미구현인지는 여전히 사용자 확인 대상 |
| **O-M2** | **실측 완료 → 사용자 확인 대기.** 프로즌 스냅샷에서 창 확대 전후 `detect_choppy` 판정은 **양쪽 모두 `False`** 로 변하지 않았다(축자: `choppy-delta.log`). 다만 조건 2 의 입력인 최근 4주 `pct_above_sma50` 은 `[42.42, 57.58, 57.58, 72.73]` → `[20.59, 18.18, 24.24, 57.58]` 로 실질 변화했다 — 이번 스냅샷에서 판정이 뒤집히지 않은 것이지 임계값이 안전하다는 뜻은 아니다. **임계값은 재튜닝하지 않았다**(plan.md R3). "이 변화가 바람직한가"는 요구사항 질문으로 남는다 |
| **O-M3** | **run 단계 확정 → 사용자 확인 대기.** P2 차트 제목을 `Market Breadth (1-year)`, P1 docstring 을 `1-year (52-week) history` 로 확정했다. 근거: 제목은 영문·범례 설명은 한글인 기존 스타일을 유지하는 최소 변경. 테스트 상수와 바이트 동등으로 고정했다. 한글 병기 등 대안 문구는 사용자 결정 사안 |
| **O-G7** | 범위 밖 — 선행 allowlist 잔류(L3/L4) |

### 발견 사항 — 프로즌 리터럴의 벽시계 의존 [잔여 위험, plan.md R4 추가 대상]

`compute_breadth_history` 는 `as_of` 인자를 갖지 않고 REQ-MBR-001 이 그 계약을
`compute_weekly_grid(weekly_db_path, as_of=None)` 으로 못박으므로, CG-2(진행 중인 주 배제)
판정이 **벽시계에 의존**한다. W33 이 실제로 종료되는 시점부터는 `2026-08-11` 이 더 이상
미완성 주가 아니게 되어 AC-MBR-001/002/003/010 의 프로즌 리터럴이 **코드 변경 없이** 깨진다.

프로덕션 시그니처를 바꾸지 않기 위해(REQ-MBR-001 의 `as_of=None` 공식 보존) 테스트에서만
`frozen_clock` 픽스처로 `date.today()` 를 `2026-08-12` 에 고정했다. 선행 SPEC 의 테스트들은
`compute_weekly_grid(..., as_of="2026-08-12")` 로 직접 전달해 같은 문제를 회피하고 있었으나,
본 SPEC 의 대상 함수는 그 경로가 없다. **plan.md R4 노후화 리터럴 목록에 "⑦ frozen_clock
고정일" 을 추가할 것을 권고한다** — 스냅샷 갱신 시 함께 이동해야 한다.

---

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-08-13
run_commit_sha: dbcbab2
run_status: complete
ac_pass_count: 10
ac_fail_count: 0
ac_nongating_count: 1          # AC-MBR-004 (xfail strict=False → XPASS)
preserve_list_post_run_count: 0
full_suite_baseline: "584 passed / 8 failed / 68 skipped / 25 errors"
full_suite_post_run: "618 passed / 8 failed / 68 skipped / 1 xpassed / 25 errors"
new_warnings_or_lints_introduced: 0
predecessor_gating_suite: "84 passed (baseline 84, 복귀 확인)"
frontend_suite: "5 files / 50 passed"
variant_execution: "V0/V1/V2/V3/history[:8]/history[-16:]/AC-006 되돌림 — 전량 실행, 축자 기록"
total_run_phase_files: 6
m1_to_mN_commit_strategy: "마일스톤별 단일 커밋, main 직접 push (Route A)"
evidence_dir: .moai/state/verify/SPEC-MARKET-BREADTH-001/
```

---

## §E.4 Sync-phase Audit-Ready Signal

_&lt;pending sync-phase&gt;_

## §F Phase 4 Mode Selection

Decision: sub-agent (Mode 5)

**Phase 1 (Plan Audit Gate)**: 실행됨 — plan-auditor iter-1 **PASS-WITH-DEBT 0.85** (Tier S 임계 0.75). 스킵 자격 없음(감사 이력 0건)이므로 정규 실행. D1/D2/D6 결함은 run 진입 전 수리 완료(`b165947`).

**Implementation Kickoff Approval**: 획득 (2026-08-13, 사용자 결정 = "D1+D2+D6 수리 → 수리 후 바로 착수"). 진행 모드 = 세미자율(마일스톤마다 보고).

Input parameters:
- tier: S
- scope: 구현 1지점(`market_breadth.py:472`) + 표기 정정 2지점 + 신규 테스트 1파일 + 선행 SPEC allowlist 동기화 1건
- domain count: 1 (주봉 격자 계약 소비)
- file language mix: Python 90% / TypeScript 10%(차트 제목 문자열)
- concurrency benefit: LOW (coding-heavy, 단일 도메인, M1→M6 순차 의존)

Mode evaluation:
- Mode 1 trivial: N — 의미 변경 동반(기간 계약), 단일 라인 아님
- Mode 2 background: N — write 작업
- Mode 3 agent-team: N — RETIRED (tombstone)
- Mode 4 parallel: N — coding-heavy 단일 도메인, Anthropic coding-task parallelism caveat
- **Mode 5 sub-agent: SELECTED**
- Mode 6 workflow: N — 파일 수 ~5로 ~30 임계 미달, 기계적 균일 변환 아님

Decision: sub-agent (Mode 5)
Justification: Tier S 최소 범위이며 M1(baseline 캡처·변형 하네스) → M2(격자 전환) → M3~M6이 순차 의존이다. M1이 코드 변경 전 게이트라 병렬화 여지가 구조적으로 없다. manager-develop 단일 순차 위임, 마일스톤마다 보고.

Route: A (Hybrid Trunk main-direct) — Tier S 기본, PR·브랜치 없음.
Development: cycle_type=tdd (quality.yaml `development_mode: tdd`).
