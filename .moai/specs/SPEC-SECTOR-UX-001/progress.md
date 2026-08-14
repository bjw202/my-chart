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

> M1 + M2 구간 (반자율 progression — pre-M3 checkpoint 대기). cycle_type=tdd (RED-GREEN-REFACTOR).
> 측정 시각 2026-08-14. M1 SHA `c27a050` / M2 SHA `fc3dfc1` — origin main push 완료 (`3a87855..fc3dfc1`).

### Baseline (run 착수 시점 실측 — AC-SUX-004 (b) 게이트 NEW-0 판정 기준)
- tsc 총 오류: **N=33** (측정 시점 실측). TS2353=**1** (`MarketOverview.tsx:46` stockName — M3 소관).
- vitest: **400 tests pass** + 2 file-load failures (`e2e/*.spec.ts` Playwright/vitest 버전 충돌 — 선행 결함, 본 SPEC 무관, vitest config 에 include 필터 없음).
- HEAD `3a87855` / branch `main` (Route A Hybrid Trunk main-direct).

### tsc 게이트 (b) — 총량 비증가 + ③ 수정 파일 NEW 0건 [PASS]
- **Claim**: M1/M2 수정 파일이 NEW tsc 오류 0건, 총량 ≤ N.
- **Evidence (verbatim)**: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -c "error TS"` → **33** (최종) == baseline 33 (비증가). `grep -c "TS2353"` → **1** (불변). M1/M2 수정 파일 정확한 파일명 grep → **0건** (`api/market.ts`, `contexts/MarketContext.tsx`, `components/SectorAnalysis/SectorAnalysis.tsx`, `components/SectorAnalysis/BubbleChart.tsx`, `App.tsx`, 3 신규 context 파일 모두 tsc 오류 0).
- **Baseline-attribution**: baseline 33 (run 착수 시점). 도중 도입된 1건(TS6133 unused `React` import in `market-delivery.test.tsx`)은 즉시 제거 → 최종 NEW 0.
- **Gaps**: 없음. **Residual-risk**: 선행 결함 32건은 범위 밖(감소 미요구).

### AC PASS/FAIL matrix (M1 + M2)
| AC | Status | Verification (verbatim command + output) |
|----|--------|------------------------------------------|
| AC-SUX-001 (AnalysisParamsContext 계약) | **PASS** | `vitest run src/contexts/__tests__/AnalysisParamsContext.test.tsx` → 4 passed. 초기값 market=all/period=1m/asOfDate=null/asOfIsPartialWeek=false/gridVersion=null + 읽기전용 setter 비노출(Object.keys 단언: setAsOfDate/recordAsOf 미포함) + 세션지속(rerender 후 market=kospi 유지) |
| AC-SUX-002 (SelectionContext 계약) | **PASS** | `vitest run src/contexts/__tests__/SelectionContext.test.tsx` → 3 passed. 초기값 selectedSector=null/sectorScopeFollow=true + 화면 간 읽기(ReaderA selectSector('반도체') → ReaderB '반도체' 관측) + 비소멸(rerender 후 유지) |
| AC-SUX-034 (TTL + grid_version 무효화) | **PASS** | `vitest run src/contexts/__tests__/queryCache.test.ts` → 6 passed. CACHE_TTL_MS=3_600_000 단일 상수 export + 59min fresh(`isStale(0, 59*60*1000)`=false)/61min stale(=true)/60min 경계(=false) + grid_version 변경 시 `size` 0 + clear() |
| AC-SUX-008 (컨트롤 단일 인스턴스) | **PASS** | `getAllByTestId('period-toggle')` toHaveLength(1), `getAllByTestId('market-toggle')` toHaveLength(1) — SectorAnalysis.test.tsx AC-SUX-008 describe 2 passed. 헤더 단일 인스턴스(서브탭 전체 공유), Table/Bubble 로컬 토글 제거(X1/X2) |
| AC-SUX-009 (기간 표기 단일화) | **PASS** | `grep -rn "'w1'\|'m1'\|'m3'" src/ \| grep -v "excess_returns\|types/market.ts"` → **0행**. 상태값 '1w'/'1m'/'3m' 단일화(D5); 응답 키는 PERIOD_EXCESS_FIELD 변환 계층에서 흡수(`'excess_w1'` 등은 `'w1'` 리터럴 아님 → grep 미매치) |
| AC-SUX-018 (시장 토글 실동작) | **PASS-WITH-DEBT** | `vitest run .../SectorAnalysis.market-delivery.test.tsx` → 2 passed. KOSPI/KOSDAQ 클릭 시 `fetchSectorRanking` 가 `toHaveBeenLastCalledWith('kospi')`/`('kosdaq')`. **전달 경로**: Table(ranking via MarketContext) + Bubble(섹터, `fetchSectorBubble(period, market)`). **잔여(Debt)**: RRG/Bump/StockExplorer 3경로는 현재 market 미소구(기존 상태) → M4-M6 각 화면 리워크 시 맥락 소비로 전달 예정. ST-4 핵심 결함(버튼 CSS만 변경·요청 0)은 주 경로에서 해소됨 |

### §1.2 보존 대상 회귀 확인 (PRESERVE 10항목) [PASS]
- `git show --stat c27a050 fc3dfc1` → `StockBubbleChart.tsx`(색상 채널 @MX:ANCHOR)·`BumpChart.tsx`(connectNulls:false)·나머지 8항목 전부 **미수정**. M1/M2 는 contexts 신설 + 헤더 토글 + MarketContext market 소비만.

### 회귀 (기존 프론트엔드 테스트) [PASS — 회귀 0건]
- 최종 `vitest run` → **419 tests passed (419)** (baseline 400 + M1 신규 13 + M2 신규 6), 2 e2e file-load failures(선행 결함 불변). 기존 400 전량 통과, 신규 회귀 0건.
- M2 로 일시 깨진 기존 테스트 15건(ContextBar 9 / AppContent 5 / market API 1)은 AnalysisParamsProvider 래핑 + `fetchSectorRanking(market?)` 서명 변경 반영으로 복구 → 전량 GREEN.

### eslint (수정 파일) [신규 error class 0]
- M1/M2 신규 도입 eslint error class: **0**. 잔여는 전부 선행 baseline 패턴 — contexts 전량의 `react-refresh/only-export-components`(Provider+hook 동일 파일, MarketContext/ScreenContext/TabContext 도 동일), `MarketContext.tsx` fetchAll 자기참조(retry setTimeout)의 `react-hooks/immutability`(message="Cannot access variable before it is declared", baseline 동일 패턴), `SectorAnalysis.tsx` crossTabParams effect 의 setState-in-effect(M3 NavIntent 교체 시 제거 예정, 미변경 effect).

### 커밋 + push (Route A Hybrid Trunk)
- M1 `c27a050` — `feat(SPEC-SECTOR-UX-001): M1 ...` (8 files, draft→in-progress 전환 포함).
- M2 `fc3dfc1` — `feat(SPEC-SECTOR-UX-001): M2 ...` (9 files).
- `git push origin main` → `3a87855..fc3dfc1 main -> main` (fast-forward, 병렬 세션 race 무).
- `git show --stat` 로 양 커밋 파일 집합 확인 → `.agency/*`·`expert-*.md` 선행 deletion 미유입(B-CRITICAL git-add discipline 준수 — 명시적 경로만 staging).

### M3 (NavIntent 교체 — 전면 rollback 경계 단일 commit `7975c7c`)

> Baseline 재확인 (run 착수 시점): tsc 총 33 / TS2353 1 (`MarketOverview.tsx:46 stockName`). vitest 419 pass + e2e 2 file-load 선행 결함. CrossTabParams 참조 14 파일(grep `crossTabParams|CrossTabParams` src/).

**tsc 게이트 (a) HARD — TS2353 == 0 [PASS]**
- **Claim**: `CrossTabParams` 타입 자체 삭제로 `MarketOverview.tsx:46` stockName TS2353 근본 소멸.
- **Evidence (verbatim)**: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -c "TS2353"` → **0** (baseline 1 → 0).

**tsc 게이트 (b) — 총량 비증가 + ③ 수정 파일 NEW 0건 [PASS]**
- **Claim**: 총량 ≤ N(33) + M3 수정 파일 NEW tsc 오류 0건.
- **Evidence (verbatim)**: `grep -c "error TS"` → **28** (baseline 33 → 28, −5: MarketOverview TS2353 1 + ChartGrid test군 setCrossTabParams TS2741×3 + 기타 1). file#code baseline-vs-final diff → **NEW 0건** (`comm -13 base final` empty). `NavIntent['payload']` 필드: `subTab`/`stockCodes`/`focusStock` 정의.
- **Baseline-attribution**: run 착수 시점 baseline 33(위 §E.2 Baseline). `setCrossTabParams is missing` 계열(TS2741)은 X5 타입 삭제로 필연 감소 — 손대는 이상 남겨 둘 수 없다(acceptance.md:52).
- **Gaps**: 없음. **Residual-risk**: 선행 결함 28건(StockBubbleChart.test node:fs/__dirname 9건 등)은 범위 밖(감소 미요구).

**AC PASS/FAIL matrix (M3)**
| AC | Status | Verification (verbatim command + output) |
|----|--------|------------------------------------------|
| AC-SUX-003 (NavIntent 주소 지정) | **PASS** | `vitest run src/contexts/__tests__/TabContext.test.tsx` → 9 passed. target routing(주소 탭만 처리) + 재전송 id 증가(2회 처리) + 동일 id 리렌더 1회(dedup) + activeTab 가드 |
| AC-SUX-004 (타입 계약 (a)HARD+(b)) | **PASS** | (a) `grep -c TS2353` → **0**. (b) 총량 28 ≤ 33 + NEW-0. `NavIntentPayload` = {subTab,stockCodes,focusStock} (market.test.ts 4 passed) |
| AC-SUX-005 (전역 clear 부재) | **PASS** | `grep -rn "clearCrossTabParams\|crossTabParams\|CrossTabParams" src/` → **0행**. 각 소비자 `lastHandled` ref 로컬 중복제거(전역 clear 호출 無) |
| AC-SUX-006 (sectorName payload 제외) | **PASS** | NavIntentPayload 타입에 sectorName 無(`@ts-expect-error` type-level 단언). 전 navigate() 호출부 sectorName 無. 섹터 선택은 SelectionContext 직접 쓰기 |
| AC-SUX-007 (스코프 추종 토글) | **PASS** | StockExplorer `sectorFilter = sectorScopeFollow ? selectedSector : null`; 칩 × → setSectorScopeFollow(false)(selectedSector 유지) |
| AC-SUX-011 (TR-3/3b 행 클릭) | **PASS** | SectorAnalysis.test TR-3(행 클릭 → 패널 오픈, navigate 0회) + TR-3b(재클릭 → clearSector, 패널 닫힘) |
| AC-SUX-012 (TR-4 상세패널 진입) | **PASS** | SectorDetailPanel `[이 섹터 종목 보기 →]` 버튼 렌더 + 클릭 시 navigate({target:'stock-explorer'}) (SectorAnalysis.test TR-4) |
| AC-SUX-013 (TR-9 종목 버블 클릭) | **PASS** | BubbleChart.nav.test: onStockClick prop 전달(props 단언) + 클릭 → navigate({target:'stock-explorer',payload:{focusStock}}) + selectSector 동기화 |
| AC-SUX-014 (TR-2 트리맵 종목 클릭) | **PASS** | `grep -c "MarketOverview.tsx.*TS2353"` → **0**. ChartGrid.integration.test: focusStock intent → present 종목 data-focus-target marker 부착 / absent 시 marker 無(중복추가 無) |
| AC-SUX-015 (TR-16 종목 체크 초기화) | **PASS** | StockExplorer.test: selectedSector 변경 → selectedStocks reset("N selected" 소멸). Stage 필터는 별도 state(초기화 無) |
| AC-SUX-016 (TR-6 버블 뒤로가기) | **PASS** | BubbleChart.nav.test: `← 섹터 목록` → sector view 복귀, selectedSector 보존(handleBack setSelectedSector(null) 제거) |
| AC-SUX-017 (TR-7/8 RRG·Bump 클릭) | **PASS-WITH-DEBT** | SectorAnalysis RRG/Bump onSectorClick → selectSector + subTab 'table'. **Debt**: visibleSectors/windowEnd/topFilter 보존은 조건부 렌더(unmount) 구조상 미구현 — M5 keep-mounted 개편 시 보존(현재架构에서는 동일 미구현, 회귀 아님) |

### §1.2 보존 대상 회귀 확인 (PRESERVE 10항목) [PASS]
- `git diff 7975c7c^ 7975c7c -- frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` → **빈 diff**(색상 채널 @MX:ANCHOR 미수정). BumpChart.tsx(baseline dates-union)·나머지 보존 항목 전부 M3 미수정.

### 회귀 (기존 프론트엔드 테스트) [PASS — 회귀 0건]
- 최종 `vitest run` → **430 tests passed (430)** (baseline 419 + M3 신규 11), 2 e2e file-load failures(선행 결함 불변). 기존 419 전량 통과, 신규 회귀 0건.
- M3 로 일시 깨진 기존 테스트 43건(AppContent 5 / SectorAnalysis 12 / SectorAnalysis.market-delivery 2 / StockExplorer / MarketOverview)은 NavIntent/useSelection mock 전환 + SelectionProvider 래핑으로 복구 → 전량 GREEN.

### eslint (M3 수정 파일) [신규 error class 0]
- M3 신규 도입 eslint error class: **0**. 잔여는 전부 선행 baseline 패턴 — `react-refresh/only-export-components`(TabContext useNavIntent 2번째 hook export 추가, MarketContext/ScreenContext/SelectionContext 와 동일 패턴), `react-hooks/set-state-in-effect`(StockExplorer NavIntent consumer 1건 — 이벤트 응답 effect, 정당; SectorAnalysis crossTab effect 1건 제거로 상쇄). selectedSector reset 은 render-time adjustment 패턴으로 전환(effect 내 setState lint 회피).

### 커밋 + push (Route A Hybrid Trunk) — M3 단일 commit
- M3 `7975c7c` — `feat(SPEC-SECTOR-UX-001): M3 NavIntent 교체 ...` (20 files: 9 source + 11 test, +691/−198). 전면 rollback 경계 — 단일 commit(부분 revert 불가).
- `git push origin main` → `b9dc448..7975c7c main -> main` (fast-forward, 병렬 세션 race 무).
- `git show --stat 7975c7c` → 20 M3 파일 정확; `.agency/*`·`expert-*.md`·`BumpChart.tsx`(선행 변경)·`MarketContext.test.tsx`(선행 변경) 전부 **미유입**(B-CRITICAL git-add discipline — 명시적 경로만 staging, pre-existing uncommitted 변경 2건 제외).

## §E.3 Run-phase Audit-Ready Signal

> 반자율 progression: **M3 GREEN** (NavIntent 교체 — 전면 rollback 경계 통과). M4~M7 잔여(표·컨트롤 / 시각화 / 로딩상태 / 회귀게이트). 본 신호는 M1+M2+M3 구간 — 전 run-phase 완료 아님.

```yaml
run_complete_at: 2026-08-14
run_commit_sha: 7975c7c          # M3 (전면 rollback 경계 단일 commit). M1=c27a050 / M2=fc3dfc1 / M3=7975c7c.
run_status: M3-complete          # M1+M2+M3 GREEN. M4~M7 잔여(반자율 progression). 전 run-phase 아님.
ac_pass_count: 16                # M1(001/002/034)+M2(008/009)+M3(003/004/005/006/007/011/012/013/014/015/016) = 16
ac_pass_with_debt_count: 2       # AC-SUX-018(M2, RRG/Bump/StockExplorer 경로 잔여) + AC-SUX-017(M3, RRG/Bump 로컬 state 보존 미구현 — M5 keep-mounted)
ac_fail_count: 0
ac_total_this_segment: 18        # M1(3)+M2(3)+M3(12). 전 SPEC 60 AC 중 42 잔여(M4-M7)
preserve_list_post_run_count: 10 # §1.2 보존 10항목 전부 미변경(StockBubbleChart 색상 채널 포함, 회귀 0)
l44_pre_commit_fetch: "synced (단일 세션) — b9dc448 기준 0 0 divergence"
l44_post_push_fetch: "synced — b9dc448..7975c7c fast-forward, 병렬 세션 race 무"
new_warnings_or_lints_introduced: 0   # 신규 eslint error class 0; tsc 수정파일 NEW 0
cross_platform_build:
  applicable: false              # 프론트엔드 전용 SPEC (Go 빌드 태그 / C-HRA-008 N/A)
tsc_gate_b_total: 28             # baseline N=33 → 28 (비증가; X5 타입 삭제로 필연 −5)
tsc_gate_a_ts2353: 0             # M3 HARD 게이트 (a) 달성 — MarketOverview.tsx:46 TS2353 근본 소멸(CrossTabParams 타입 삭제)
modified_files_new_tsc_errors: 0
total_run_phase_files: 37        # M1(8)+M2(9)+M3(20) — 겹침 없음(각 마일스톤 독립 파일)
m1_to_mN_commit_strategy: per-milestone   # M1 c27a050 / M2 fc3dfc1 / M3 7975c7c 각 conventional commit + 🗿 MoAI trailer; push at end
regression_tests: "430 pass (419 baseline + M3 신규 11) / 2 e2e file-load baseline 불변 / 기존 419 전량 통과, 신규 회귀 0"
next_checkpoint: "M4 표·컨트롤 규약 (반자율 progression). M3 는 전면 rollback 경계 통과(단일 commit 7975c7c). M4~M7 순차 진행"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

---

## §F Phase 4 Mode Selection

### Phase 1 Plan Audit Gate (re-run — cache invalidated by v0.4.0)
- prior verdict: v0.3.0 PASS 0.87 (STALE — v0.4.0 commit 3a87855 changed spec/plan/acceptance → plan-artifact hash changed → skip condition #3 artifact-hash-unchanged FAILED)
- re-run verdict: **PASS 0.96** (iter-1/3, Tier L threshold 0.85) — 2026-08-14, session 22a815b7
- dimensions: Clarity 0.95 / Completeness 1.0 / Testability 0.95 / Traceability 0.95 (harmonic mean 0.962)
- defects: D1 [MINOR] §8.6 mirror 표기 정정 / D2 [MINOR] AC BDD 표기 관찰 — **no BLOCKING, no SHOULD-FIX**
- O-U9 delta verified consistent across all 5 artifacts; mut_bump_applies_ag5 되돌림 RED = textbook Lesson #9 compliance

### Implementation Kickoff Approval (plan→run HUMAN GATE)
- verdict: **APPROVED** (2026-08-14) — explicit user approval via AskUserQuestion (memory feedback_ambiguous_approval: no implicit approval)
- progression mode: **반자율 — M3 경계 checkpoint** (M1·M2 continuous → pre-M3 user checkpoint → M3 single-commit rollback boundary → M4~M7 continuous)

### Input parameters (§B.1)
- tier: L
- scope (files): ~15+ frontend files (M3 NavIntent replacement alone touches 13)
- domain count: 2 (React state/contexts, echarts visualization)
- file language mix: TypeScript/TSX 100%
- concurrency benefit: LOW (coding-heavy, strong inter-file dependencies, sequential build)

### Mode evaluation
| Mode | Selected | Rationale |
|------|----------|-----------|
| 1 trivial | no | 7-milestone Tier L, 60 ACs — not trivial |
| 2 background | no | implementation (write-capable), needs foreground verification |
| 3 agent-team | no | RETIRED (Phase 0.95 tombstone) |
| 4 parallel | no | coding-heavy → Anthropic coding-parallelism caveat; strong inter-file deps |
| 5 sub-agent | **YES** | coding-heavy Tier L, sequential per-Milestone TDD delegation |
| 6 workflow | no | new-code + inter-file dependencies, not mechanical-uniform transform |

### Decision: sub-agent (Mode 5)
Justification: Coding-heavy frontend implementation with strong inter-file dependencies — M3 NavIntent replacement touches 13 files in a single commit (partial-rollback-impossible boundary); M5 shares the `bubbleRadius` util across 2 charts; M2-M7 build sequentially on M1's Context layer. Per Anthropic's finding that coding tasks involve fewer truly parallelizable tasks than research, the sequential sub-agent path (Mode 5) is the safe default. SSE-stall mitigation for this Tier L scope is handled by per-Milestone delegation (no Round naming layer). Progression is 반자율 — the sole user checkpoint is the pre-M3 rollback boundary; M1·M2 and M4~M7 flow continuously with progress reporting.
