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

_&lt;pending run-phase&gt;_

---

## §E.3 Run-phase Audit-Ready Signal

_&lt;pending run-phase&gt;_

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
