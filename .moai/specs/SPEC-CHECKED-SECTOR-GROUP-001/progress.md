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

### M4a 되돌림 실증 (AC-001~007)

방법: 대상 파일 주입 → 해당 AC 테스트만 실행 → RED tail 확보 → 스크래치패드 백업(`cp`)으로 복원 → `git status --short` 클린 확인. 복원에 `git checkout --` 미사용 (mutation-restore 교훈; HEAD e8b5a74 기준 바이트 동등 복원을 `diff -q`로 매번 확인).

공통 명령 — V = `frontend/node_modules/.bin/vitest run --root <repo>/frontend` (절대경로):
`$V src/components/StockList/__tests__/StockList.grouping.test.tsx -t "AC-CSG-00X"`

| AC | 되돌림 (1줄) | 관측된 RED tail |
|----|--------------|-----------------|
| 001 | StockList.tsx checked 브랜치를 평면 리스트로 교체 (섹터 헤더 미생성) | `AssertionError: expected +0 to be 4` (`.sector-header` 0≠4) |
| 002 | sectorKey.ts 조인 `' > '`→`' - '` | `AssertionError: expected undefined to be defined` ('내수 > 리조트' 헤더 미발견) |
| 003 | `stock.sector_major \|\| '기타'` → `as string` (null 폴백 제거) | `AssertionError: expected undefined to deeply equal [ '132890' ]` ('기타' 그룹 실종) |
| 004 | `.sort()` 제거 (Map 삽입 순 반환) | `AssertionError: expected [ '내수 > 리조트', 'AI', '기타', '금융' ] to deeply equal [ 'AI', '금융', '기타', '내수 > 리조트' ]` |
| 005 | `stock_count`를 유니버스 값(`results.sectors` 조회)으로 교체 | `AssertionError: expected '3' to be '1'` ('금융' 헤더 카운트 3≠1) |
| 006 | buildCheckedGroups 루프에 `if (!s.sector_major) continue` 주입 | (DOM) `AssertionError: expected [ 'true', 'true', 'true' ] to deeply equal [ 'true', 'true', 'true', 'true' ]` + (모델) `AssertionError: expected 6 to be 7` — 두 테스트 모두 RED |
| 007 | `if (!collapsedCheckedSectors.has(...))` 행 렌더 가드 제거 | `AssertionError: expected <span class="stock-item-name"></span> to be null` (접힌 'AI' 그룹 케이아이엔엠 행 잔존) |

**AC-004 보조 관측 (R4b)** — `.sort((a,b)=>a.localeCompare(b,'ko'))` 재주입 후 AC-004 재실행: RED.
`AssertionError: expected [ '금융', '기타', '내수 > 리조트', 'AI' ] to deeply equal [ 'AI', '금융', '기타', '내수 > 리조트' ]`
→ localeCompare('ko') 축은 코드포인트 축과 순서 상이 (ICU 한국어 collation: 한글이 Latin 선행). `node -e` 교차확인: `["금융","기타","내수 > 리조트","AI"]` ≠ codepoint `["AI","금융","기타","내수 > 리조트"]`. 분류: **게이팅** — no-sort 축·localeCompare 축 모두 코드포인트 기대값과 어긋나 AC-004가 양 축을 구분함.

**복원 실증**

```text
$ $V src/components/StockList          # 풀스코프 재실행
Test Files  3 passed (3)
     Tests  26 passed (26)
$ git status --short -- frontend/src/components/StockList/
(빈 출력 — 수정된 추적 파일 0개)
```

`?? frontend/src/.moai/` (state/config-cache.json, 세션 시작 전 생성된 hook 산물)는 본 작업 무관 기존 항목. 7/7 되돌림 RED 관측 — 항진명제(되돌려도 GREEN) 없음.

### M4b 되돌림 실증 (AC-008~016) + 정적 스캔 + 커버리지

방법: M4a와 동일 — 주입 → 대상 AC 테스트만 실행 → RED tail 확보 → 스크래치패드 `cp` 복원 → `diff -q` 바이트 동등 + `git status --short` 확인. 기준선 GREEN 선행: grouping 스위트 14/14 passed. 전 되돌림 복원 `diff -q` 무출력 · StockList 디렉토리 `git status --short` 빈 출력.

| AC | 되돌림 (1줄) | 관측된 RED tail |
|----|--------------|-----------------|
| 008 | checked 리스트를 useState 스냅샷으로 동결 (최초 1회 파생 후 재계산 없음) | L390 `AssertionError: expected HTMLElement to be undefined` — KB금융 uncheck 후에도 '금융' 헤더 잔존 |
| 009 | 접기 상태를 공유 Set으로 재병합 (checked Row가 `collapsedSectors` 참조) | L419 `AssertionError: expected 'false' to be 'true'` — 전체 탭 접힘 → 체크 탭 전파 |
| 010 | `toggleSector`가 항상 `setCollapsedSectors` 타깃 | L442 `AssertionError: expected 'false' to be 'true'` — 체크 탭 접힘 → 전체 탭 전파 (역방향) |
| 011 | sectorKey.ts가 minor 무시 (`return major`) | L454 `AssertionError: expected '내수' to be '내수 > 리조트'` |
| 013a | (정적, 테스트 없음) 인라인 `<div className="sector-header">` 주입 | 스캔(a) EMPTY/exit 1 → 2 lines/exit 0 (MATCH ≥1 관측) |
| 013b | (정적, 2차) 두 번째 `<VariableSizeList />` JSX 주입 | 스캔(b) 1 line → 2 lines (정확히 1 위반 관측) |
| 014 | checkedItems 파생 안에 transient `fetch('sector-keys')` 주입 | L475 `AssertionError: expected "fetch" to not be called` — fetchMock 1회 호출 관측 |
| 015 | flatItems(전체 탭) 헤더 카운트를 CHECKED count로 교체 | alltab L131 `AssertionError: expected [ '0', '0', '0' ] to deeply equal [ '27', '2', '5' ]` |
| 016 | 빈 상태 분기 제거 → 빈 checked 리스트가 가상 목록으로 흐름 | L512 `TestingLibraryElementError: Unable to find an element with the text: 체크된 종목이 없습니다.` |

**클린 트리 정적 스캔 3-leg** (`bash -c`로 실행·exit code 캡처; HEAD e8b5a74):

```text
(a) grep -rn 'sector-header' src/components/StockList/StockList.tsx src/components/StockList/sectorKey.ts
    → (빈 출력) EXIT:1            [기대: EMPTY — 인라인 정의 0건]
(b) grep -n 'VariableSizeList\|FixedSizeList' src/components/StockList/StockList.tsx src/components/StockList/sectorKey.ts
    → StockList.tsx:234: <VariableSizeList  EXIT:0   [기대: 정확히 1 line]
(c) git diff e9c049b --stat -- frontend/package.json frontend/package-lock.json
    → (빈 출력) EXIT:0            [기대: 0 changed lines — 의존성 변동 없음]
```

**커버리지** (`npx vitest run src/components/StockList --coverage`, v8 provider):

```text
sectorKey.ts   — stmts 100% / branch 100% / funcs 100% / lines 100%
StockList.tsx  — stmts 83.83% / branch 80.76% / funcs 77.27% / lines 86.66%
```

**전체 스위트 회귀** (`npx vitest run`):

```text
Test Files  2 failed | 81 passed (83)
     Tests  720 passed (720)
```

2 failed files = `e2e/ai-report-deep.spec.ts` / `e2e/preset-flow.spec.ts` — "Playwright Test did not expect test.describe() to be called here". Playwright 스펙이 vitest 기본 include에 걸리는 사전 존재 harness mismatch (SPEC-PRESET-001 b775612 도입, `frontend/vite.config.ts` test 섹션에 include/exclude 없음, 클린 트리에서 측정 — 본 SPEC 무관 기준선 노이즈). 테스트 본체는 720/720 전부 통과.

**성능 노트 (§0.2)** — 사전 구현 baseline은 M2 전에 캡처되지 않음 (known process gap — 조작하지 않음). post-implementation only 단일 샘플 (jsdom, 임시 스크래치 파일로 측정 후 삭제): 탭 전환 렌더 46.08ms · uncheck 렌더 3.94ms. 영구 테스트 파일 신규 생성 없음.

**Gaps** — (1) 성능 사전 baseline 부재 (위) · (2) 전체 스위트 2 e2e 파일 실패는 기준선 노이즈로 본 SPEC 범위 밖 · (3) 커버리지는 StockList 스코프 측정값.

9/9 되돌림 RED(또는 스캔 변화) 관측 — 항진명제 없음.

### review 결함 수정 (접힘 키 잔존, AC-008/REQ-CSG-006 보강)

- **결함**: 체크 그룹 소멸 시 `collapsedCheckedSectors`의 접힘 키가 잔존 — 재체크로 그룹이 재등장해도 `aria-expanded="false"`로 시작해 새로 체크한 행이 보이지 않음 (review t1 실증, 사용자 승인 수정)
- **RED** (`npx vitest run src/components/StockList/__tests__/StockList.grouping.test.tsx -t "재등장"`):

```text
Test Files  1 failed (1)
     Tests  1 failed | 14 skipped (15)
AssertionError: expected 'false' to be 'true'
 ❯ src/components/StockList/__tests__/StockList.grouping.test.tsx:426:53
```

- **수정**: `StockList.tsx`에 prune `useEffect` 추가 (+10행) — `buildCheckedGroups`로 살아있는 키 산출, 잔존 키 존재 시에만 조건부 setter 호출. 전체 탭 경로(`flatItems`/`collapsedSectors`)·두 Set 분리 원칙 불변
- **GREEN** (동일 명령):

```text
Test Files  1 passed (1)
     Tests  1 passed | 14 skipped (15)
```

- **회귀**: StockList 스위트 `Test Files 3 passed (3) / Tests 27 passed (27)` · `tsc --noEmit` exit 0 · 전체 `npx vitest run` `Test Files 2 failed | 81 passed (83) / Tests 721 passed (721)` (2 failed = 사전 존재 e2e Playwright 기준선 노이즈, M4b와 동일)
- **커밋**: `e620657` `fix(SPEC-CHECKED-SECTOR-GROUP-001): 접힘 키 그룹 소멸 정리 — 재등장 그룹 펼침 보장` (2 files, +39 · pre-commit pytest 타임아웃으로 `SKIP_MOAI_PRECOMMIT=1` 문서화 오버라이드 사용 — `--no-verify` 아님)

## §E.3 Run-phase Audit-Ready Signal

- run_status: audit-ready
- run_complete_at: 2026-08-17
- baseline_commits (Hybrid Trunk main-direct): M0 `3acf05a` (characterization, 단독) · M1 `aeb249f` (+`status: draft → in-progress`) · plan산출물 `31c8fb6` · M2 `06d251f` (StockList.tsx +33/−11) · M3 `f819deb` + lint `e8b5a74` · evidence `ac907b9` · **review 결함 수정 `e620657` (접힘 키 prune + AC-008 보강 재등장 테스트 — §E.2 최신 서브섹션)**
- ac_matrix: **15/15 PASS + 결함 보강 1건 PASS** — BLOCKER 9 (001·002·003·005·006·008·011·015·016) / MAJOR 5 (004·007·009·010·014) / MINOR 1 (013) · review 실증 결함(접힘 키 잔존) AC-008/REQ-CSG-006 보강 단언 추가. AC-012 결번 (철회).
- 되돌림 실증: **16/16 RED 관측** (M4a AC-001~007 + M4b AC-008~016, AC-013 2-leg 포함) — 항진명제 0건. AC-004 localeCompare('ko') 보조축은 실측 결과 **게이팅**으로 승격 (ICU collation이 한글을 Latin 선행 — REQ-CSG-003 근거 실증).
- coverage (v8, `npx vitest run src/components/StockList --coverage`): `sectorKey.ts` lines 100% · `StockList.tsx` lines 86.66% — 게이트 ≥85% 충족 (attribution: this run, tree e8b5a74).
- regression: 전체 스위트 `npx vitest run` → **Tests 720/720 passed**. Test Files 2 failed = e2e 2종(ai-report-deep·preset-flow)의 Playwright/vitest harness mismatch — **사전 존재 기준선 노이즈, 본 SPEC 무관 실증**: 커밋 범위 e9c049b..HEAD에서 e2e/vite.config 변경 0건 (마지막 터처 b775612 = SPEC-PRESET-001). Gap으로 기록, 조작하지 않음.
- tsc: `npx tsc --noEmit` exit 0 (신규 오류 0).
- deps: `git diff e9c049b --stat -- frontend/package*.json` → 0 changed lines.
- static scan 3-leg (bash 재실행으로 독립 관측): (a) EMPTY exit 1 ✓ (b) 정확히 1 line `StockList.tsx:234` exit 0 ✓ (c) 0 lines ✓.
- gaps: ① §0.2 성능 사전-구현 baseline 미포착 (M2 선행 스폰 누락 — post-implementation 단일 jsdom 샘플만 기록: 탭 전환 46.08ms · uncheck 3.94ms). ② StockList.tsx branch coverage 80.76% (lines 게이트는 충족).
- disclosures: pre-commit moai gate가 TS-only 변경에 pytest 타임아웃으로 5회 실패 → hook의 문서화된 `SKIP_MOAI_PRECOMMIT=1` 오버라이드로 커밋 (전 건 대체 증거 tsc+eslint+vitest 수집, `--no-verify` 미사용). 스폰 실패 3건(초기 통합 스폰·M3·결함 수정 fix1) autocompact thrashing → 마일스톤 분할 재스폰(사용자 승인)으로 회복; M3·fix1은 스폰이 남긴 완성본(95%·100% — fix1은 커밋까지 완료 상태로 사망)을 orchestrator가 검증·마무리(exportText 리터럴 실측 확정·stale 참조 3건·시나리오 순서 1건·lint 정합·§E.3 갱신).

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
