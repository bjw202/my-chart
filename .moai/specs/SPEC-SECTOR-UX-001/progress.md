# SPEC-SECTOR-UX-001 Progress

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-08-12
tier: L
artifacts: [spec.md, plan.md, acceptance.md, progress.md]
design_research_substitute:
  - docs/sector-ux/02-screen-flow.md     # design (§3.3 상태 소유권 표가 계약 본체)
  - docs/sector-ux/01-data-contract.md   # research (실측)
ac_count: 60                              # AC-SUX-001~061 중 057 결번 (v0.1.0의 57에서 갱신)
contract_divergence_resolved:
  - "01 §8.5 sector_minor 전송 필터 — 옵션(a) 구현 채택 (REQ-SUX-054). 중분류 단위 집계는 O-A2/O-7로 미결 유지"
invariants_mirrored: [SN-3, "§8.6"]      # 직접 소유 불변식 없음 — 클라이언트 측 검증자
depends_on: [SPEC-SECTOR-AGGREGATION-001]
preserve_contract: [SPEC-SECTOR-MINOR-COLOR-001]
open_questions: [O-U2, O-U3, O-U5, O-U8]   # 전부 착수 차단 항목 아님 (O-U9는 2026-08-14 해결)
resolved_open_questions:
  - "O-U1 (2026-08-12, 잠정): 기간 토글 비활성 + 툴팁. §0.1 재평가 시점에 '정보인가 소음인가' 재확인 → 소음이면 숨김 amendment"
  - "O-U4 (2026-08-12): 크기 범례 기간별 고정 눈금"
  - "O-U6 (2026-08-12): focusStock — 있으면 스크롤·하이라이트, 없으면 추가. 교체 금지"
  - "O-U7 (2026-08-12): 열 접기 섹터비중 → Vol배 → 52W고. 기간 3열·Stage·RS·Name 불변 (REQ-SUX-058 / AC-SUX-061)"
  - "O-U9 (2026-08-14, ②의 O-A7): AG-5를 Bump에 미적용 확정. ②의 출하 구현이 이미 미적용(sector_metrics.py:947-948 + get_sector_history의 excluded= 미전달) → ② 백엔드 변경 없음, amendment 불필요. ③ 조치: AC-SUX-019 / AC-SUX-056 R5 범위를 Table·섹터 Bubble·RRG로 한정 + Bump 반대 방향 단언(mut_bump_applies_ag5 되돌림 RED 필수) 신설 + REQ-SUX-017에 적용 범위 명문화"
blocking_before_run: []                   # 2026-08-14 v0.4.0: 착수 차단 항목 없음. ② status: completed(v0.5.0, sync 13d74d0) + O-U9 결정 두 조건 모두 충족
run_entry_verified_at: 2026-08-14         # 착수 게이트 실측: tsc 총 33건 / TS2353 1건(SPEC 기록 baseline N=33과 일치, 재측정 불필요) · CrossTabParams 참조 13파일(M3 서술과 일치) · 봉투 필드 7종 전부 backend/schemas/envelope.py 존재
plan_audit_cache: invalidated-2026-08-14-v0.4.0   # v0.4.0에서 spec.md/plan.md/acceptance.md 변경 → plan-artifact hash 재변경. v0.3.0 PASS 0.87은 skip 4조건 중 artifact-hash 조건 불충족 → /moai run Phase 1에서 plan-audit 재실행 필수
rollback_boundary: "M3 직전 commit (NavIntent 교체 이후 부분 rollback 불가)"
```

Tier L이나 `design.md` / `research.md`를 신규 작성하지 않는다 — `docs/sector-ux/02-screen-flow.md`(설계 확정안)와 `01-data-contract.md`(실측)가 그 역할을 수행하며, 중복 작성은 SSOT 분기를 만든다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
