# SPEC-AI-REPORT-005 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-10-21T00:00:00+09:00
- plan_status: audit-ready (v0.3.1, plan-audit PASS)
- plan_audit:
  - 1회차 FAIL 0.77 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-1.md` (B1~B7·S1~S6·M1~M5 → v0.2.0에서 반영)
  - 2회차 FAIL 0.88 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-2.md` (N1~N5 → v0.3.0에서 반영)
  - 3회차 PASS 0.92 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-3.md` (R3-1 → v0.3.1에서 반영, R3-2·R3-3은 아래 부채)
- plan_debt (사용자 승인 2026-10-21, run 단계 처리):
  - R3-2: AC-AIR5-014 되돌림 (r3)이 대상 테스트를 지정하지 않아 결과가 비결정적이다. → run 단계는 (r1)·(r3)에 쓸 테스트 이름을 정확히 정해 `progress.md §E.2`에 적고, 수집 성공 여부와 무관한 단언(실행기 호출·작업 진행)만 가진 테스트를 고르거나 (r2)의 작업 서비스 변형으로 (r3)를 수행한다.
  - R3-3: 첨부 항목이 `section == "auditor_report"`·`document == "attachment"`를 갖는지 단언하는 AC가 없다. → run 단계는 새 AC를 만들지 말고 AC-AIR5-008 테스트 안에 eleId 1·2 항목에 대한 두 단언을 추가한다.
- R3-1 run 단계 주의: 네트워크 가드 범위는 테스트 파일 이름으로 판정하고, AC-AIR5-014 #4를 되돌림 관측보다 먼저 실행한다.
- artifacts: spec.md, plan.md, acceptance.md, research.md, progress.md
- counts: REQ 16개(REQ-AIR5-001~016), AC 16개(AC-AIR5-001~016) — Tier M 상한(각 16) 이내
- needs_clarification: 0건 (미확인 DART 사실 F4·F8은 run 단계 M1 관측 항목, research.md §3)
- baseline: 이전 실행 2건에서 대상 감사 결함 6종 모두 발생(research.md §2, P14), 매니페스트 = 원본 재생성 결과(P7)

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
