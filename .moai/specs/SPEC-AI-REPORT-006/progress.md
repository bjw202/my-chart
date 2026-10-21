# SPEC-AI-REPORT-006 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_revised_at: 2026-10-21 (v0.3.0, plan-audit 2차 FAIL 반영 — 3차 감사 전)
- plan_status: draft (v0.3.0). 감사 보고서: 1차 `.moai/reports/t18/plan-audit.md`(결함 D1~D14), 2차 `.moai/reports/t18/plan-audit-iter2.md`(결함 N1~N10)
- artifacts: spec.md, plan.md, acceptance.md, design.md, research.md, progress.md (Tier L)
- counts: REQ 20개(REQ-AIR6-001~020), AC 22개(AC-AIR6-001~022). v0.3.0에서 개수 변동 없음(재계산 출력: `.moai/state/verify/t18-plan3/trace.py`)
- tier_rationale: Tier L — 새 서브시스템(브라우저 캡처) + 두 번째 `claude -p` 세션 + 전달 판정 변경 + 하네스 지침 + 프론트, 마일스톤 6개, 변경·신규 파일 약 20개
- needs_clarification: 0건. 구 2건은 운영자 결정(2026-10-21)으로 해소 — spec.md D7, plan.md T9에 결정으로 기록 (지원 브라우저 = Playwright 캐시의 chrome-headless-shell만, 외부 네트워크 전면 차단)
- probe_evidence: `.moai/state/verify/t18-plan/`(v0.1.0), `.moai/state/verify/t18-plan2/`(v0.2.0), `.moai/state/verify/t18-plan3/`(v0.3.0: `trace.py`와 그 출력) — 모두 git 무시 경로. v0.3.0에서 추가한 코드베이스·환경 주장은 research P32(대소문자 비구분 경로)·P33(`render_report.py --final`의 출력 파일)
- baseline: goose 백엔드 테스트 `267 passed, 214 deselected` (research P17, v0.1.0 측정; v0.2.0·v0.3.0에서 재실행하지 않음, 2차 감사자가 같은 값을 재관측); 라이브 실행 `a5becbb9…`의 감사 결함 10개 중 대상 8개 발생(research P2·P3)
- gaps: research §4 G1·G3~G15 (G1이 M1 GO/NO-GO 조건, G2는 범위 밖으로 종결). v0.3.0 신규: G13(`final/` 출처 미검증), G14(영수증 제거·교체 이중 실패), G15(`audit-review.json` 사후 변경 미탐지)
- lint: v0.1.0에서 `moai spec lint --strict --json`은 SPEC-AI-REPORT-006 대상 0건이었다. v0.2.0·v0.3.0 개정본에 대해서는 **재실행하지 않았다**(미검증)
- id_check: `[[ "SPEC-AI-REPORT-006" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` → `PASS`(v0.1.0 기록; ID 불변)
- 2차 감사 결함 처리 요약(v0.3.0): N1·N2·N3 수정(필수), N4 Gap(G13), N5·N6·N7·N8·N9 수정, N10 (a)(c)(e) 수정·(b) 안내 문구로 완화·(d) 기각(G15). 위치는 HISTORY 0.3.0 행과 반환 보고
- 알려진 불일치: SPEC-AI-REPORT-005 spec.md §5는 화면 확인을 "카드 t17"이 다룬다고 적었다. 이 카드는 t18이며 내용은 005가 예고한 범위와 같다. 005 문서는 수정하지 않았다

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
