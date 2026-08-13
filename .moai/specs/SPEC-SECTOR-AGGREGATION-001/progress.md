# SPEC-SECTOR-AGGREGATION-001 Progress

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-08-12
tier: L
artifacts: [spec.md, plan.md, acceptance.md, progress.md]
design_research_substitute:
  - docs/sector-ux/01-data-contract.md   # research (실측)
  - docs/sector-ux/02-screen-flow.md     # design (§12.3 서버 선행 조건)
ac_count: 47          # 0.4.0: AC-SAG-047(M1 종료 게이트 — 골든 baseline 캡처 완결성, D4) 신설. 0.3.0: AC-SAG-046(창 일수 실측)
invariants_owned: [EX-1, EX-2, RK-1, RK-2, RRG-1, RRG-2, RRG-3, RRG-4, BM-3, BM-6, SN-3, AG-6, "§8.6"]
depends_on: [SPEC-SECTOR-GRID-001]
open_questions: [O-A2, O-A5, O-A7]        # O-A5는 ① close로 착수 가능해졌으나 재측정이 run-phase M3 작업이라 미결 유지
resolved_open_questions:
  - "O-A1 (2026-08-12): RS-Ratio 롤링 정규화 미적용 — 100이 문자 그대로 벤치마크"
  - "O-A3 (2026-08-12): 상수 주식수 한계를 warnings[]에 명시 + '현재주가' = daily 최신 Close"
  - "O-A4 (2026-08-12): 거래대금 창 = 기간 토글 연동 [anchor(t,N), t]"
  - "O-A6 (2026-08-12): 지표별 coverage.* + 최상위 최소값 병행"
  - "O-A8 (2026-08-13): 선택지 (a) 미완성 주 포함 — as_of = latest, 앵커 = anchor(t,N)(완성 바). 창이 라벨보다 길어짐(실측 프로즌 11/32/95일, 라이브 12/33/96일 — 요일 의존). 파생: REQ-SAG-043 + AC-SAG-046(return_window_days) 신설, REQ-SAG-012에 BM-6 보존 조건(동일 anchor 호출) 명시"
blocking_before_run: []                   # 2026-08-13 v0.4.0: 착수 차단 항목 없음. ① status: completed(v0.3.0) + O-A8 결정 + plan-audit D1/D3/D5(BLOCKING, "before M1.0") 전부 SPEC 층에서 해소. 단 M1 내부 순서는 강제된다 — M1.0-a(집계 픽스처 빌드) → M1.0-b(골든 baseline 캡처) → M1.0-c(AC-SAG-047 종료 게이트) → M2
blocking_before_ux: [O-A7]                # ③의 AC-SUX-019 / AC-SUX-056 R5가 의존 (③의 O-U9)
as_of_pinned: "2026-08-11"                # 사용자 결정 2026-08-13 (D3). 기존 날짜 축 픽스처 유지, AC-SAG-046 리터럴 4개(11/32/95, 앵커 07-31/07-10/05-08, baseline 07-10) 불변. 게이팅 테스트의 as_of 기본값(None → today) 사용 금지 — acceptance.md §8 규약 8
fixtures:
  date_axis: "tests/fixtures/frozen/weekly-2026-08-12/"        # ① 소관, 읽기 전용. AC-SAG-046만 호스팅
  aggregation: "tests/fixtures/frozen/aggregation-2026-08-11/" # ② 소관, M1.0-a 신규 빌드. 횡단면 게이팅 AC 호스팅. 요건 = acceptance.md §8.2 F1~F11 (값이 아니라 구조)
plan_audit_history:
  - "iteration 1 (2026-08-13): FAIL 0.78 (L thresh 0.85). MUST-PASS 전항 통과. Clarity 0.80 / Completeness 0.82 / Testability 0.55 / Traceability 0.95. BLOCKING D1·D2·D3·D5, SHOULD-FIX D4·D6·D7, MINOR D8·D9"
plan_audit_resolution_v040:
  - "D1 (BLOCKING) RESOLVED: 프로즌 픽스처가 게이팅 기대값 7/8을 호스팅 불가 → 픽스처 2종 분리(§8.1) + 집계 픽스처 구조 요건 F1~F11(§8.2) + 게이팅 기대값을 리터럴에서 파생 규칙으로 전환(§8.3). 라이브 결속 7값은 비게이팅 스모크로 강등(규약 3)"
  - "D2 (BLOCKING) RESOLVED: 설계결정 3 반증 → 참 조건을 '최신 대표 바가 금요일'로 정정(spec.md REQ-SAG-043), AC-SAG-046 마감 주 대조를 금요일 종단 픽스처 변형으로 재작성. 실증: 절단본에서 latest=2026-08-07/partial=False/{7,28,91}"
  - "D3 (BLOCKING) RESOLVED: as_of=2026-08-11 리터럴 명기(§8 규약 7) + as_of 기본값 사용 금지 + 정적 스캔 강제(규약 8)"
  - "D4 (SHOULD-FIX) RESOLVED: AC-SAG-047 신설(기계적 M1 종료 게이트) + 캡처 목록을 무파라미터 엔드포인트 현실에 맞춰 단일 파일로 정정"
  - "D5 (BLOCKING) RESOLVED: R1을 골든 baseline에 결속(R4/R5와 동일), R5의 최상위>=95/최하위<=5를 등간격 파생 단언(R5-a)로 대체, R4는 F2(N>=12)로 degenerate 회피"
  - "D6 (SHOULD-FIX) RESOLVED: AC-SAG-014를 출력 동등에서 anchor() 호출 계측 구조 단언으로 전환. 실증으로 출력 동등의 검출력 0 확인(latest/history 양쪽에서 앵커 동일)"
  - "D7 (SHOULD-FIX) RESOLVED: 002/007/011/013/014/024/030/045 R1·R3·R4·R5·R6/046/047에 명명된 되돌림 변형 부여 + 전 대조 단언에 대해 관측된 RED verbatim 기록을 요구하는 DoD 항목 신설(Lesson #9)"
  - "D8 (MINOR) RESOLVED: REQ-SAG-029 → Unwanted Behavior, REQ-SAG-032 → Where"
  - "D9 (MINOR) RESOLVED: AC-SAG-007을 픽스처 구조 요건(F3) 기반으로 재기술하고 순수 합성 열거 → 게이팅 열거로 이동"
plan_audit_cache: invalidated-2026-08-13-v0.4.0  # v0.4.0에서 plan 산출물 4종 전부 변경 → plan-artifact hash 변경. 직전 판정 FAIL 0.78 무효. /moai run Phase 1에서 plan-audit 재실행 필수
```

Tier L이나 `design.md` / `research.md`를 신규 작성하지 않는다 — 그 역할은 이미 확정·교차검증된 `docs/sector-ux/01-data-contract.md`(연구·실측)와 `02-screen-flow.md`(설계)가 수행하며, 중복 작성은 SSOT 분기를 만든다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
