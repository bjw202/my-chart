# SPEC-AI-REPORT-006 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_revised_at: 2026-10-21 (v0.2.0, plan-audit 1차 FAIL 반영 — 2차 감사 전)
- plan_status: draft (v0.2.0). 1차 감사 보고서: `.moai/reports/t18/plan-audit.md` (결함 D1~D14)
- artifacts: spec.md, plan.md, acceptance.md, design.md, research.md, progress.md (Tier L)
- counts: REQ 20개(REQ-AIR6-001~020), AC 22개(AC-AIR6-001~022)
- tier_rationale: Tier L — 새 서브시스템(브라우저 캡처) + 두 번째 `claude -p` 세션 + 전달 판정 변경 + 하네스 지침 + 프론트, 마일스톤 6개, 변경·신규 파일 약 20개
- needs_clarification: 0건. 구 2건은 운영자 결정(2026-10-21)으로 해소 — spec.md D7, plan.md T9에 결정으로 기록 (지원 브라우저 = Playwright 캐시의 chrome-headless-shell만, 외부 네트워크 전면 차단)
- probe_evidence: `.moai/state/verify/t18-plan/`(v0.1.0 프로브)와 `.moai/state/verify/t18-plan2/`(v0.2.0: `search_channel_probe.py/.out`, `final_path_probe.py/.out`, `heights_rerun.out`) — 모두 git 무시 경로
- baseline: goose 백엔드 테스트 `267 passed, 214 deselected` (research P17, v0.1.0 측정; v0.2.0에서 재실행하지 않음, 감사자가 같은 값을 재관측); 라이브 실행 `a5becbb9…`의 감사 결함 10개 중 대상 8개 발생(research P2·P3)
- gaps: research §4 G1·G3~G12 (G1이 M1 GO/NO-GO 조건, G2는 범위 밖으로 종결)
- lint: v0.1.0에서 `moai spec lint --strict --json`은 SPEC-AI-REPORT-006 대상 0건이었다. v0.2.0 개정본에 대해서는 **재실행하지 않았다**(미검증)
- id_check: `[[ "SPEC-AI-REPORT-006" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` → `PASS`(v0.1.0 기록; ID 불변)
- 알려진 불일치: SPEC-AI-REPORT-005 spec.md §5는 화면 확인을 "카드 t17"이 다룬다고 적었다. 이 카드는 t18이며 내용은 005가 예고한 범위와 같다. 005 문서는 수정하지 않았다

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
