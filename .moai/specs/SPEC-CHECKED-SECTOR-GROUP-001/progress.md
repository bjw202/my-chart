# SPEC-CHECKED-SECTOR-GROUP-001 — Progress

- spec_id: SPEC-CHECKED-SECTOR-GROUP-001
- tier: M
- status: draft
- req_count: 14   # REQ-CSG-010 철회 결번
- ac_count: 15    # AC-CSG-012 철회 결번
- open_questions: [O-C1, O-C2]  # 둘 다 의도적 미결 — 착수를 막지 않는다
- blocking_before_run: []       # 선행 SPEC·차단 항목 없음

---

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-08-17
- artifacts: spec.md, plan.md, acceptance.md, progress.md (Tier M = 3 + progress)
- spec_id_check: `[[ "SPEC-CHECKED-SECTOR-GROUP-001" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` → `PASS`
- audit_iteration_1: FAIL 0.72 (Tier M thresh 0.80, testability 0.55) → spec.md v0.2.0 + acceptance/plan 개정으로 BLOCKING 3건(D1 자멸적 스캔 / D2 관측자 부재 / D3 거짓 3자 항등) + SHOULD-FIX 4건(D4~D7) + MINOR 4건(D8~D11) 반영. **plan-audit 재실행 필수** — plan-artifact hash가 바뀌었으므로 iteration 1의 판정은 skip 근거로 쓸 수 없다.
- audit_delta_verified: D1·D2·D3·D4·D6·D8 주장을 실물 대조로 확인 — `AppContent.test.tsx:25-27` 목킹 / `test-setup.ts` ResizeObserver no-op / 체크 변경 지점 3곳 단일 종목 / zsh glob 중단 재현 / `StockList/` 내 목록 인스턴스 1건.
- audit_iteration_2: PASS-WITH-DEBT 0.875 (Δ +0.155, thresh 0.80). iteration-1 BLOCKING 3건 종결 확인 + D4 철회 처분 승인. 잔여 R1~R6을 debt로 넘기지 않고 plan-phase에서 전량 해소(spec.md v0.3.0).
- r1_measured_baseline: |
    # bash, 손대지 않은 트리 — 결함 형태(필터 없음) → 2건
    frontend/src/components/StockList/StockList.tsx:45:  const listRef = useRef<VariableSizeList | null>(null)
    frontend/src/components/StockList/StockList.tsx:212:          <VariableSizeList
    # 정정 형태(| grep -v 'useRef<') → 1건
    frontend/src/components/StockList/StockList.tsx:212:          <VariableSizeList
- r1_note: AC-CSG-013 (b)의 기대값 1은 추론이 아니라 위 측정에 귀속된다 (verification-claim-integrity §2).
- r2_disposition: characterization 테스트를 M3 → M0으로 이관 (변경 전 트리 GREEN이 완료 조건, 단독 commit).
- r3_disposition: 픽스처 규약 (f) 종목 10건 → 헤더+종목 총 15항목. AC-CSG-001/006 전제 동반 수정.
- r4_r5_r6_disposition: plan.md §H AC 총계 15 정정 / spec.md §1.4 REQ-CSG-009→011 · §2 D-4 AC-CSG-005→006 정정 / AC-CSG-016(b) Then을 ①기본·②대체 양 경로로 재기술.
- third_audit_required: false  # 편집이 R1~R6에 한정됨. 코디네이터가 R1 측정값을 spot-verify.
- audit_iteration_3: PASS 0.92 (2026-08-17, run-gate Phase 1 delta re-audit — sticky-cache MISS 후 R1~R6 해소 범위 재심사) — R1~R6 전량 RESOLVED, 신규 차단 결함 0건, 점수 회귀 없음(0.875 → 0.92). 잔여 optional 2건(D1 plan B-12 "≈11행" 수치 표현 / D2 plan §A 신설 파일 목록에 sectorKey.test.ts 누락)은 run 위임 프롬프트에서 보완해 진행. R1 기대값은 감사자 독립 재측정으로 문서 baseline과 일치 확인.
- audit_verdict: PASS
- audit_report: .moai/reports/plan-audit/SPEC-CHECKED-SECTOR-GROUP-001-review-3.md
- audit_at: 2026-08-17
- notes: 설계 결정 4건(D-1 접기 상태 격리 / D-2 결측 섹터 `기타` / D-3 라이브 재그룹핑 / D-4 헤더 카운트 의미)을 `spec.md §2`에서 해결. 정렬 기준은 백엔드 `sorted()` 파리티를 위해 코드포인트 비교를 채택(`localeCompare` 기각, REQ-CSG-003 근거).

## §F Phase 4 Mode Selection

Input parameters:

| 파라미터 | 값 |
| --- | --- |
| tier | M |
| scope (files) | 5 — 수정 1 (`StockList.tsx`) · 신설 4 (`sectorKey.ts`, `sectorKey.test.ts`, `StockList.alltab.characterization.test.tsx`, `StockList.grouping.test.tsx`) |
| domain count | 1 (frontend React/TS) |
| file language mix | 100% TypeScript/TSX |
| concurrency benefit | LOW — coding-heavy (Anthropic coding-task parallelism caveat) |
| Agent Teams prereqs | N/A (Mode 3 RETIRED) |

Mode evaluation:

| Mode | Selected | Rationale |
| --- | --- | --- |
| 1 trivial | no | Tier M 구현, 15 AC — 자명하지 않다 |
| 2 background | no | write-capable 구현 작업 — M0→M2 순서 강제 때문에 순차 게이팅 필요 |
| 3 agent-team | RETIRED | tombstone — 선택 불가 |
| 4 parallel | no | 단일 도메인 + coding-heavy — 병렬 팬아웃이 해로움 (상태 수술 대상이 `StockList.tsx` 한 파일) |
| 5 sub-agent | **YES** | coding-heavy 단일 도메인, 마일스톤 순차 실행 (M0 characterization → M1 헬퍼 → M2 상태 수술 → M3 통합 테스트 → M4 되돌림 실증) |
| 6 workflow | no | 5 files ≪ ~30 · semantic/new-code 작업 (기계적 단일 변환 아님) |

Decision: sub-agent (Mode 5) — files: 5, domains: 1

Justification: 구현의 핵심은 `StockList.tsx` 한 파일 안의 상태 소유권 수술(접기 Set 분리 + `checkedItems` 교체)이며 M0의 관측자-선행 제약(characterization 테스트가 변경 전 트리에서 GREEN + 단독 커밋)이 전체 순서를 직렬로 강제한다. Anthropic의 코딩-과제 병렬성 경고("most coding tasks involve fewer truly parallelizable tasks than research")가 그대로 적용되는 형태로, 병렬화 이득이 없고 순차 위임이 유일한 안전한 형태다. 단일 manager-develop 위임이 M0~M4를 순차 수행한다(마일스톤별 재스폰 대신 — 5파일 규모에서 컨텍스트 재구축 비용이 이득을 초과).

Mode 6 confirmation: N/A (Mode 5 선택 — Implementation Kickoff Approval은 lead 세션에서 승인 완료, 카드 t1 run 컬럼 진입)

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
