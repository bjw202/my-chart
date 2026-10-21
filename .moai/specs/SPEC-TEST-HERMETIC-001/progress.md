# SPEC-TEST-HERMETIC-001 — 진행 기록 (progress.md)

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-10-21
tier: M
artifacts: [spec.md, plan.md, acceptance.md, progress.md]
spec_id: SPEC-TEST-HERMETIC-001
card: t12
notes: >
  plan-phase 산출물 4종 작성 완료. 조사 결과 중 핵심 파일 근거(config.py,
  backend/deps.py, conftest 픽스처, 양쪽 테스트 픽스처 갭, pyproject testpaths,
  vite.config.ts)를 plan 단계에서 직접 재확인했다. 조사 보고의
  test_response_time_under_500ms는 별도 파일이 아니라
  tests/test_market_api.py:194의 테스트 메서드로 확인해 본문에 정정 반영했다.
  plan-auditor 검토 대기.
```

## §E.2 Run-phase Evidence

### 실행 개요 (2026-10-21, run 워크트리 agent-a54a6df6c5c4a1636, HEAD 318ab2f에서 컷)

M0 기준선(정상 환경, 주 체크아웃) → M1 RED(워크트리 DB-less) → M2/M3 수정 →
M4 게이트 실측 → 최종 검증. 모든 수치는 실측 인용이며 원문 로그는
`.moai/state/verify/develop-hermetic/`(주 체크아웃 gitignored 증거 저장소)과
`evidence/`(커밋됨)에 보존된다.

### AC 매트릭스 (AC-001~AC-010)

| AC | 판정 | 검증 명령 | 실측 결과 (verbatim 요약) |
|----|------|-----------|---------------------------|
| AC-001 | **PASS** | `pytest tests/ -q` (워크트리 DB-less) | `1089 passed, 1 skipped, 95 deselected, 1 xpassed in 99.23s`, 종료 코드 0 — `0 failed` (`final-dbless-full-run.log`) |
| AC-002 | **PASS** | `evidence/m1-red-observations.md` 대조 | 실패 ID 전수 20건 목록 + 예상(16+5) vs 실측(16+4, ac_sag_045 미재현) 대조 절 존재 |
| AC-003 | **PASS** | `pytest tests/test_hermetic_db_patch.py -q` | `2 passed` (라우터 전 모듈 + config 계층). **되돌림 RED 실측**: autouse 일시 비활성화 → `2 failed`, 종료 코드 1 (`ac003-revert-red.log`), 복원 후 `2 passed` |
| AC-004 | **PASS** | `pytest tests/test_market_api.py -q` | `19 passed, 1 warning in 9.35s`, 종료 코드 0 |
| AC-005 | **PASS** | `pytest tests/test_response_contract.py -q` | `14 passed, 1 warning in 18.73s`, 종료 코드 0 |
| AC-006 | **PASS** | `evidence/m3-unexplained-diagnosis.md` 대조 | 관측 4건 각각 (트레이스백 요약\|원인\|처분\|RED/GREEN 참조) 기록, 미재현 1건은 결함 주장 없음으로 처리 |
| AC-007 | **PASS** | `evidence/m4-gate-measurement.md` 대조 | 단계 구성(gate.yaml 선언 + 시간 실측)과 Python test 트리거 판정 기록 (게이트 무출력 설계 실측 — 94초, exit 0, 0바이트) |
| AC-008 | **PASS (N/A 분기)** | 게이트 vitest 미트리거 실측 3건 | 루트 package.json/tsconfig 부재 + 시간 실측 + exit 0 → REQ-008 미실행 분기: `frontend/vite.config.ts` 변경 없음(no-op) |
| AC-009 | **PASS** | M0 기준선 vs 최종 DB-less 실행 결과 집합 비교 | 실패 0=0, skipped 1=1, deselected 95=95, xpassed 1=1, passed 1087→1089(+2=신규 검증 테스트 2건). 신규 실패 0 · 신규 skip 0. *Gap: 수정 후 스위트를 "실 DB 존재 환경"에서 직접 실행은 워크트리 DB 복사 금지(§B.3)로 미수행 — 회귀 부재는 DB-less GREEN + 파일별 패치가 autouse를 덮는 구조적 논증으로 닫음(아래 Gaps 참조)* |
| AC-010 | **PASS** | `find Output -name '*.db' \| wc -l` | `0` (AC-001 실행 직후 실측). 수정 전 RED 실행은 오히려 `Output/stock_data_daily.db` 1건을 생성(REQ-004 위반의 실측 증거) → 삭제 후 재실측 |

### RED/GREEN 증거 대장 (E8)

- **RED (수정 전, M1)**: `.moai/state/verify/develop-hermetic/m1-red-full-run.log`
  — `20 failed, 1067 passed, 1 skipped, 95 deselected, 1 xpassed in 87.24s`, 종료 코드 1.
  실패 ID 전수는 `evidence/m1-red-observations.md` §4.
- **GREEN (수정 후)**: `.moai/state/verify/develop-hermetic/final-dbless-full-run.log`
  — `1089 passed, 1 skipped, 95 deselected, 1 xpassed in 99.23s`, 종료 코드 0.
- **되돌림 RED (AC-003)**: `.moai/state/verify/develop-hermetic/ac003-revert-red.log`
  — `2 failed ... 종료 코드 1`, 복원 후 `2 passed`.

### LSP / lint

- pyright(venv 설치분): 변경 대상 5파일, 변경 전 `0 errors, 0 warnings, 0 informations` →
  변경 후 동일 `0 errors, 0 warnings, 0 informations` — 신규 진단 0.
- ruff: venv에 바이너리 부재 → `uvx ruff check`로 대체 실측. 변경 5파일에서
  `I001` 2건 — **base(HEAD 318ab2f)에서 동일하게 존재하는 기존 baseline 결함**
  (`git show HEAD:<file> | ruff check --stdin-filename`으로 전건 재확인).
  신규 발견 0건.

### 변경 파일 목록

- `tests/conftest.py` — autouse `hermetic_db_paths` 픽스처 신설(REQ-003, plan M2 기본안 (a))
- `tests/test_market_api.py` — `test_client`·`test_response_time_under_500ms` DAILY 패치 갭 수선(REQ-005)
- `tests/test_response_contract.py` — `client` 픽스처 stage.DAILY 패치 갭 수선(REQ-005)
- `tests/test_m6_gap_closure.py` — `sector_advanced.DEFAULT_DB_DAILY` 폴백 패치(M3 진단 처분)
- `tests/test_hermetic_db_patch.py` — 신설 AC-003 검증 테스트(m3 진단이 명명)
- `.moai/specs/SPEC-TEST-HERMETIC-001/**` — 증거 4종 + progress.md + spec.md frontmatter(status/updated)

백엔드 프로덕션 코드 변경: **0건**(최소 시임 예외도 불요 — 원인이 전부 테스트 계층에서 패치 가능한 모듈 상수였음). `pyproject.toml` 변경 없음. `frontend/vite.config.ts` 변경 없음(AC-008 미실행 분기).

### plan 대비 이탈 (사유 포함)

1. **커밋 분할 단순화**: 미션 §B.7의 병목 대비로 M1~M3을 단일 코드 커밋으로
   묶는 것은 계획된 이탈이 아니라 미션이 지정한 순서다. 증거·진행 문서는 후속
   docs 커밋으로 분리.
2. **신규 테스트 파일 1건**(tests/test_hermetic_db_patch.py): AC-003이 "신규
   검증 테스트(pkgutil 순회)"를 요구하나 허용 파일 목록에 신규 파일이 명시되지
   않아, M3 진단 문서가 해당 파일을 처분 산출물로 명명하는 경로로 정합화
   (m3-unexplained-diagnosis.md §3).
3. **AC-009의 직접 실행 갭**: "수정 후 스위트 × 실 DB 존재 환경"의 직접 실행은
   DB 복사 금지(§B.3)와 워크트리 분리 원칙(§7 안티패턴 4·5)으로 불가 — 결과
   집합 델타 비교 + 구조적 논증으로 대체하고 Gap으로 명시(아래 §E.3 gaps).
   ff-merge 후 주 체크아웃에서 동일 스위트가 실 DB로 실행되는 것이 잔여 확인
   경로다(오케스트레이터 검증 단계).

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-10-21
run_commit_sha: pending-backfill-first-run-phase-commit
run_status: audit-ready
ac_pass_count: 10
ac_fail_count: 0
ac_pass_with_debt_count: 0
ac_na_count: 0
preserve_list_post_run_count: 0
l44_pre_commit_fetch: not-run (worktree agent spawn — spawn 시 오케스트레이터가 동기화 점검 수행)
l44_post_push_fetch: pending-push
new_warnings_or_lints_introduced: 0
cross_platform_build:
  applicable: false
  note: 테스트 전용 변경(순수 Python) — 플랫폼 분기 코드 없음
total_run_phase_files: 6
m1_to_mN_commit_strategy: combined-code-commit(M1-M3) + evidence-docs-commit — pre-commit heavy gate(moai gate)가 still-broken 스위트를 실행하는 병목 회피 위해 코드 선완성 후 단일 커밋(미션 §B.7 지정 순서)
```

### Gaps (미검증 — VCI §3.4)

- AC-009의 "실 DB 존재 환경에서 수정 후 스위트 실행" 직접 관측 없음(§E.2 이탈 3 참조).
- 게이트 단계 이름 목록은 출력이 아닌 설정 선언 + 시간 실측으로 구성됨 — 게이트가
  성공 시 무출력인 실측 설계라 출력 기반 관측 불가(증거 로그 0바이트 보존).
- 신규 파일 `test_hermetic_db_patch.py`의 라우터 모듈 전수 import는 수집 시점에
  본 파일이 수행 — 스위트 내 다른 파일이 임포트하지 않는 신규 라우터는 autouse
  패치 순회가 테스트 중 최초 임포트 시점까지만 미패치로 노출될 수 있음(현 스위트는
  backend.main 경유 전수 임포트로 영향 없음 — 최종 전체 GREEN이 실측 보장).

### Residual-risk (잔여 위험)

- ff-merge 후 주 체크아웃(실 DB 환경)에서 첫 전체 실행 시 예외적 회귀가 관측되면
  위 Gap의 논증이 틀린 것이다 — 그때는 AC-009를 FAIL로 재판정해야 한다.
- `moai gate`의 무출력 설계는 향후 단계 추가(예: JS/TS 감지 방식 변경) 시 시간
  실측 추정을 무효화할 수 있다 — 게이트 동작 변경 후 본 실측 재수행 요망.


## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_complete_at: 2026-10-21
sync_commit_sha: pending-backfill-sync-commit
sync_status: complete
b12_self_test_a: 0 (CHANGELOG grep 'SPEC-TEST-HERMETIC-001' 사전 점검 — 중복 항목 없음 확인 후 기입)
b12_self_test_b: 10/10 (acceptance.md 고유 AC-ID 수와 CHANGELOG 인용 AC 수 일치 — AC-001~AC-010)
b12_self_test_c: pass (CHANGELOG에 명명한 파일 5종 모두 ls 실측 존재: tests/conftest.py, tests/test_market_api.py, tests/test_response_contract.py, tests/test_m6_gap_closure.py, tests/test_hermetic_db_patch.py)
changelog_entry_position: [Unreleased] 섹션 선두 (기존 SPEC-AI-REPORT-005 항목보다 앞)
frontmatter_status_transitions:
  in_progress_to_implemented: sync 커밋에서 수행 (merged close)
  implemented_to_completed: sync 커밋에서 수행 (merged close — 별도 Mx 커밋 없음)
canary_compliance_check:
  mx_tag_validation: sync 서브스텝으로 수행 — 테스트 전용 변경으로 신규 export 함수 없음, run-phase에서 MX 태그 결론 없음(변경 5파일 모두 테스트 파일)
  close_subject_full_id: docs(SPEC-TEST-HERMETIC-001): sync-phase 문서 동기화 및 3-phase close
readme_sync: no-op (테스트 인프라 변경 — 사용자 대상 기능·설치·사용법 불변)
```

## §F Phase 4 Mode Selection

- 날짜: 2026-10-21 · Implementation Kickoff Approval 통과 (구현 승인=승인, 진행 방식=자율 goal 무장)
- 입력 파라미터: tier=M · 파일 범위 약 5종 · 도메인 1-2개(Python 테스트 + 조건부 frontend 설정) · 코딩 중심 · 병렬 이익 LOW
- 모드 평가: direct 미선정(비자명 변경) / fanout 미선정(코딩 중심·다중 도메인 조사 아님) / sweep 미선정(대량 기계적 변형 아님) / agent-team 미선정(명시 요청 없음)
- Decision: serial (단일 manager-develop 위임, M1→M4 순차, L1 격리 워크트리)
- 근거: 코딩 중심 작업은 Anthropic coding-task parallelism caveat에 따라 serial이 기본이며, M2는 M1 관측에, M3는 M1·M2 결과에 종속되는 순서 고정 단계라 병렬화 이익이 없다.
- 자율 진행: 완료 조건 goal 무장 — `.moai/state/verify/develop-hermetic/run-complete.md` 존재 + `verdict: PASS` 포함 (에이전트가 DB-less 스위트 exit 0 + 기준선 회귀 0을 자체 검증한 뒤 기록하는 마커)
