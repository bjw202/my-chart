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

### M4 (표·컨트롤 규약 — 화면별 commit `dc4ad26` / `d28d505` / `cfdb87a`)

> Baseline 재확인(run 착수 시점과 동일): tsc 총 28 / TS2353 0. vitest 430 pass + e2e 2 file-load 선행 결함. cycle_type=tdd(RED-GREEN-REFACTOR), 반자율 progression(per-screen commit).

**tsc 게이트 (a) HARD — TS2353 == 0 [PASS — 불변]**
- **Evidence(verbatim)**: `tsc -p tsconfig.app.json --noEmit | grep -c TS2353` → **0**.

**tsc 게이트 (b) — 총량 비증가 + ③ 수정 파일 NEW 0건 [PASS]**
- **Claim**: M4 수정 파일이 NEW tsc 오류 0건, 총량 ≤ N.
- **Evidence(verbatim)**: `grep -c "error TS"` → **28**(최종) == baseline 28(비증가). M4 수정 파일(SectorRankingTable/SectorAnalysis/StockTable/StageDistributionBar/StockExplorer/BumpChart/bumpFormat/stockTableColumns/useCollapseLevel/sort/WeeklyHighlights/types·api + 7 신규 테스트) 전부 file:code baseline-vs-final diff **NEW 0건**.
- **Baseline-attribution**: run 착수 시점 baseline 28(§E.2 Baseline). `rank_change:number→number|null` 확장 cascade(WeeklyHighlights prop 보수), `unclassified_count?` 확장 cascade(StageDistributionBar readCount 방어) — 전부 M4 수정 파일 안에서 해소.
- **Gaps**: 없음. **Residual-risk**: 선행 결함 28건(StockBubbleChart.test node:fs 9건 등)은 범위 밖.

**AC PASS/FAIL matrix (M4)** — 16 AC(019~032 / 058 / 061, 057 결번 skip)
| AC | Status | Verification (verbatim command + output) |
|----|--------|------------------------------------------|
| AC-SUX-019 (제외 섹터 가시성 Table·Bubble·RRG + Bump 반대) | **PASS** | Table: `vitest SectorRankingTable.m4.test` excluded-sectors 렌더 4 passed. Bump 반대: `vitest BumpChart.m4.test` "Bump 반대 방향" 2 passed(제외 영역 미렌더 + 디스플레이·스마트폰 선 존재). **mut_bump_applies_ag5 되돌림 RED(아래 verbatim)**. 섹터 Bubble·RRG: excluded 섹터는 sectors[] 에 없어 순위 버블/RRG 점에 자연 제외(data[] 소스) |
| AC-SUX-020 (선택 섹터 제외 시 선택 유지) | **PASS** | `vitest SectorAnalysis.m4` — selectedSectorExcluded 시 sector-excluded-notice 렌더(패널 대신 안내) |
| AC-SUX-021 (rank 열 응답값 그대로) | **PASS** | 정적 스캔 `grep -rnE "\.rank\s*=..." SectorAnalysis/ utils/` → **0행**. 행동 단언: rank [3,1,2] 픽스처 → rank-value 텍스트 `['3','1','2']`(재계산 시 1,2,3 이 됨) |
| AC-SUX-022 (정렬 고지 띠) | **PASS** | `vitest SectorAnalysis.m4` AC-SUX-022 — rs_avg 정렬 시 sort-notice 렌더(sort/period/market 포함) + [순위순으로] 클릭 시 소멸 3 passed |
| AC-SUX-023 (정렬 리셋) | **PASS** | AC-SUX-023 — rs_avg desc 후 market/period 변경 시 rank/asc 리셋(띠 소멸) 2 passed |
| AC-SUX-024 (null 정렬) | **PASS** | `vitest utils/sort.test` — compareNumericNullsLast asc/desc 모두 null 맨 뒤 + NaN + 결정성 6 passed |
| AC-SUX-025 (순위변동 4상태+기준일) | **PASS** | `vitest SectorRankingTable.m4` — ▲3/▼2/–/신규 + 0≠null 클래스 + baseline_date 헤더 4 passed |
| AC-SUX-026 (가중 배지) | **PASS** | thead ⓦ×3(1W/1M/3M) ⓔ×4(RS/RS Top/52W/Stage) + 범례 2 passed |
| AC-SUX-027 (RRG/Bump 기간 토글 비활성) | **PASS** | AC-SUX-027 — RRG/Bump 서브탭 시 period-toggle button disabled + title 툴팁 + Table 복귀 시 활성 5 passed |
| AC-SUX-028 (Bump weeks+span_days) | **PASS** | `vitest BumpChart.m4` AC-SUX-028 — 8/12/26주 토글(기본12) + weeks=26 요청 + "12주 (84일)" 캡션 + span_days 무 시 주수만 5 passed |
| AC-SUX-029 (분포 모집단 일치) | **PASS** | `vitest StageDistributionBar.m4` AC-SUX-029 — headerLabel(섹터명·종목수) 렌더. StockExplorer sectorScopeFollow 시 by_sector 분호 사용 |
| AC-SUX-030 (미분류 세그먼트) | **PASS** | AC-SUX-030 — 미분류 세그먼트 렌더 + 5세그먼트 너비 합 100% + click→unclassified + 범례 "미분류(SMA40 부족)" 5 passed |
| AC-SUX-031 (종목 표 신규 열) | **PASS** | `vitest StockTable.m4` AC-SUX-031 — 1W/1M/3M/섹터비중 4열 상설 + weight_capped ⊤ 마커 3 passed |
| AC-SUX-032 (default 진입 가시성) | **PASS-WITH-DEBT** | columns(1W/3M/섹터비중) + 미분류 세그먼트 default 모드 상설 렌더(collapseLevel=0). **Debt**: 기준일/진행중 배지는 M6(AC-SUX-037) 소관 — 본 M4 에서 StockExplorer 헤더 배지 미구현 |
| AC-SUX-058 (순위 총수 7/27) | **PASS** | rank 셀 `{rank} / {totalRanked}` — totalRanked = sectors.filter(rank!=null).length. 정적 스캔 `grep -rnE "/\s*29|29\s*개 섹터" SectorAnalysis/` → **0행** |
| AC-SUX-061 (좁은 화면 열 접기) | **PASS** | `vitest stockTableColumns.test` COLLAPSE_ORDER=[weight_in_sector,volume_ratio,near_52w_high] + INVARIANT(기간3열·Stage·RS·Name) 4 passed. `vitest StockTable.m4` AC-SUX-061 — collapseLevel 1/2/3 순서 + 불변 열 비숨김 + data-overflow-scroll 5 passed |

**AC-SUX-019 — mut_bump_applies_ag5 되돌림 RED(Lesson #9 [HARD] 실증) verbatim**
- 변형: BumpChart filteredSectors useMemo 에 `AG5_ALLOWED = new Set(['반도체','은행']); return base.filter(s => AG5_ALLOWED.has(s.name))` 주입(Table data[] 교집합 — 디스플레이·스마트폰 제거).
- **RED 출력(verbatim, /tmp/m4-mut-red.log)**:
  ```
  TestingLibraryElementError: Unable to find an element with the text: 디스플레이. ...
    ❯ src/components/SectorAnalysis/__tests__/BumpChart.m4.test.tsx:107:19
      expect(screen.getByText('디스플레이')).toBeInTheDocument()
  Test Files  1 failed (1)
       Tests  1 failed | 1 passed | 5 skipped (7)
  ```
- **복원 실증**: `cp /tmp/m4-bump-backup.tsx BumpChart.tsx`(scratchpad 백업, git checkout-index 미사용 — 미커밋 작업물 보호) → `diff backup file` **empty** + `grep -c "mut_bump_applies_ag5\|AG5_ALLOWED" BumpChart.tsx` → **0**(변형 마커 소멸). 복원 후 `vitest BumpChart.m4.test` → **7 passed**(GREEN 복귀).
- **판정**: GREEN 아닌 RED 관측 성공 → 항진명제 아님 실증(Lesson #9 충족).

**정적 스캔 ACs [PASS]**
- AC-SUX-021: `grep -rnE "\.rank\s*=|rank:\s*(idx|index|i)\s*\+\s*1|map\(\(.*,\s*(idx|i)\).*rank" SectorAnalysis/ utils/` → **0행**(rank 재부여 코드 없음).
- AC-SUX-058: `grep -rnE "/\s*29|29\s*개 섹터" SectorAnalysis/` → **0행**(총 섹터 수 상수 박기 없음).
- REQ-SUX-054 철회(AC-SUX-057 결번): `grep -cn "sector_minor" StockTable.tsx` → **0행**(중분류 필터 분기 없음, sector_major-only 술어 유지).

### §1.2 보존 대상 회귀 확인 (PRESERVE 10항목) [PASS]
- `git diff a18417f..cfdb87a -- StockBubbleChart.tsx` → **빈 diff**(색상 채널 @MX:ANCHOR 미수정).
- BumpChart.tsx: connectNulls:false(@:130)·날짜 합집합 축(@:75-84)·focus:'series'(@:99-108) **유지**(AC-SUX-051 회귀 단언 대상 — 변경 금지). 본 파일의 선행 미커밋 PRESERVE 계약 버전이 AC-SUX-028 화면 정당 대상이므로 비분리 가능해 함께 커밋됨(connectNulls:false 를 저장소에 실체화).
- RRGChart.tsx·나머지 보존 항목 M4 미수정.

### 회귀 (기존 프론트엔드 테스트) [PASS — 회귀 0건]
- 최종 `vitest run` → **490 tests passed (490)**(baseline 430 + M4 신규 60), 2 e2e file-load failures(선행 결함 불변). 기존 430 전량 통과, 신규 회귀 0건.

### eslint (M4 수정 파일) [신규 error class 0]
- M4 신규 도입 eslint error class: **0**. 잔여 선행 baseline 패턴(react-refresh/only-export-components 등) 불변.

### 커밋 + push (Route A Hybrid Trunk) — M4 화면별 3 commit
- M4-1 `dc4ad26` — `feat(SPEC-SECTOR-UX-001): M4 (1/3) 순위표·컨트롤 규약` (10 files).
- M4-2 `d28d505` — `feat(SPEC-SECTOR-UX-001): M4 (2/3) 종목 탐색 규약` (9 files).
- M4-3 `cfdb87a` — `feat(SPEC-SECTOR-UX-001): M4 (3/3) Bump 구간 컨트롤 + AC-SUX-019 반대 방향 단언` (5 files).
- `git push origin main` → `a18417f..cfdb87a main -> main`(fast-forward, 병렬 세션 race 무).
- `git show --stat` 3 commit → `.agency/*`·`expert-*.md`·`.claude/agents/*`·`.moai/config|rules|project` migration mass **미유입**(B-CRITICAL git-add discipline — 명시적 경로만 staging). 단 BumpChart.tsx 는 AC-SUX-028 정당 대상으로 M4-3 에 포함(선행 PRESERVE 계약 버전 비분리 — 위 §1.2 항 참조).

### M5 Baseline (착수 시점 재측정) + AC-SUX-048 RED-FIRST 관측
- **tsc baseline (M5 착수)**: `grep -cE "error TS"` → **28** (M4 종료와 동일, 비증가). `grep -c "TS2353"` → **0** (HARD 게이트 (a) 불변).
- **vitest baseline (M5 착수)**: **490 tests pass** (M4 종료값과 동일) + 2 e2e file-load failures(선행 결함 불변).
- **HEAD**: `5e3ff65` (M4 + BumpChart connectNulls PRESERVE 확정). `git fetch origin main && git rev-list --left-right origin/main...HEAD` → `0 0`(synced).
- **AC-SUX-048 RED-FIRST (Lesson #9 — 대조 단언 RED 실증)**: M5 시각화 착수 전, 색상 채널 회귀 금지 가드(`StockBubbleChart.ac048-guard.test.tsx`)를 작성·GREEN 관측(5 passed)한 뒤, `SECTOR_MINOR_PALETTE[0]` 를 `'#4E79A7' → '#000000'` 으로 변형(mutate)해 **RED 를 관측**했다:
  ```
  AssertionError: expected [ '#000000', '#F28E2B', …(8) ] to deeply equal [ '#4E79A7', '#F28E2B', …(8) ]
  - Expected / + Received → "#4E79A7" ↔ "#000000"
  Tests: 2 failed | 3 passed (5)
  ```
  변형 직후 즉시 되돌림(revert) — `git diff frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` → **빈 diff**(byte-identical 복원 확인). 이로써 가드가 색상 배열 변화를 실제로 포착함(항진명제 아님)을 실증. REQ-SUX-056 섹터 버블 색상 구현이 종목 버블 색상 배열에 영향을 주지 않음을 본 가드가 지속 단언한다.

### M5 (시각화 — 차트별 commit 597eaf0 / 62ade59 / 2e23dd2 / e23d7a0 / 01120f3 / 1dba4b0)

**Claim**: M5 시각화 규약(AC-SUX-038~051 + 059 + 060 + 017)을 6 commit 으로 구현했고, §1.2 보존 10항목 회귀 0 · tsc 비증가 · vitest 회귀 0 이다.
**Evidence(verbatim)**: 아래 AC matrix 각 행의 명령·출력. M5 테스트 파일 6종 일괄 실행 → `Test Files 6 passed (6) / Tests 50 passed (50)`.
**Baseline-attribution**: M5 착수 baseline(§E.2 "M5 Baseline") tsc 28 / TS2353 0 / vitest 490. M5 종료 실측 tsc **28**(비증가) / TS2353 **0** / vitest **540 passed**(490 + M5 신규 50).
**Gaps**: AC-SUX-042(벤치마크 절대값) · AC-SUX-046(lookback_weeks/trail_start_date/market 파라미터) · AC-SUX-060(저커버리지 툴팁 ⚠ + 하단 저신뢰 요약) 3건은 백엔드 응답 필드 부재 또는 M6 소관으로 PASS-WITH-DEBT. 상세는 matrix 참조.
**Residual-risk**: 선행 결함 28건(tsc) + e2e file-load 2 파일은 M5 범위 밖으로 불변. ECharts option 단언 기반이므로 실제 캔버스 렌더 결과(색 대비 시각 확인)는 라이브 스모크(M7 §6-6)에서 확인 필요.

**AC PASS/FAIL matrix (M5)** — 17 AC(038~051 / 059 / 060 / 017)
| AC | Status | Verification (verbatim command + output) |
|----|--------|------------------------------------------|
| AC-SUX-038 (버블 크기 면적비례+로그) | **PASS** | `vitest bubbleRadius.test.ts` → 10 passed. 공식 `2×sqrt(rMin²+u×(rMax²−rMin²))` 리터럴 단언 + 섹터[14,68]/종목[10,52] 범위 + `v_max===v_min → u=0.5` + **선형 정규화 대조 단언**(중간값이 최소 근처에 뭉치지 않음) + 기간별 고정눈금 클램프 |
| AC-SUX-039 (크기 범례 의무) | **PASS** | `vitest SectorBubbleChart.m5.test` — SizeLegend 3 참조버블 실제값 + 기간 병기 렌더 단언 |
| AC-SUX-040 (결측 거래대금) | **PASS** | 섹터: `SectorBubbleChart.m5.test` 점선 테두리(REQ-SUX-057 섹터). 종목: `StockBubbleChart.m5.test` `symbolSize=10(=2×rMin)` + 툴팁 `거래대금: 데이터 없음` + 테두리 Stage 불변 |
| AC-SUX-041 (axisPointer 삭제) | **PASS** | `SectorBubbleChart.m5.test` — option 에 `axisPointer` 키 부재 단언. 정적 스캔: `grep -c "axisPointer" frontend/src/components/SectorAnalysis/SectorBubbleChart.tsx` → **0행**(주석 표기까지 1dba4b0 에서 제거) |
| AC-SUX-042 (기준선 의미 표기) | **PASS-WITH-DEBT** | 섹터: X=0 markLine 벤치마크 **이름** 라벨 렌더(15 passed 중). 종목: cap-weighted 섹터 집계 수익률 라인 + 라벨 + 0선 보조. **Debt**: 벤치마크 **절대값**(+1.88%)은 백엔드 미전달 — 이름만 표기 |
| AC-SUX-043 (축 범위) | **PASS** | `SectorBubbleChart.m5.test` — X축 `min <= 0` 보장 단언(음수 초과수익률 픽스처 포함) |
| AC-SUX-044 (RRG 사분면 의미 표기) | **PASS** | `vitest RRGChart.m5.test` — 4사분면 라벨에 벤치마크 대비 의미 병기 + 100 기준선 상설 + ② O-A1 롤링정규화 미적용 고지 렌더 |
| AC-SUX-045 (RRG 축 자동 대칭) | **PASS** | `RRGChart.m5.test` — `rrgHalf(maxDev)` 순수함수 리터럴 4케이스(`half=max(5,ceil(dev×1.1))`) + **대조 단언**(기존 75/125 하드코딩과 다름) 9 passed |
| AC-SUX-046 (궤적 시작·벤치마크 추종) | **PASS-WITH-DEBT** | 스파크라인 헤더 lookback(8주) + 궤적 시작일 렌더. **Debt**: `lookback_weeks`/`trail_start_date` 응답 필드 및 RRG API `market` 파라미터 백엔드 미지원 — client 파생값(TRAIL_WINDOW + 첫 trail 날짜) 사용, 데이터 시리즈의 market-follow 미구현 |
| AC-SUX-047 (Stage 테두리 채널) | **PASS** | `StockBubbleChart.m5.test` AC-SUX-047 — stage 2/1/3/4/null → `{#ffffff,2,solid}`/`width 0`/`width 0`/`{#4b5563,1,solid}`/`{#9CA3AF,1,dashed}` 전수 단언 |
| AC-SUX-048 (색상 채널 회귀 금지) | **PASS** | `vitest StockBubbleChart.ac048-guard.test.tsx` → 5 passed. **RED 실증(Lesson #9)**: M5 착수 전 `SECTOR_MINOR_PALETTE[0]` `#4E79A7→#000000` 변형 시 RED 관측(§E.2 M5 Baseline 항 verbatim), 즉시 byte-identical 복원 |
| AC-SUX-049 (다크 배경 대비) | **PASS** | `StockBubbleChart.m5.test` — 팔레트 10색 + `#9CA3AF` 전부 배경 `#1a1a2e` 대비 `>= 3.0`. 대비비 계산 함수 포함. `#4E79A7 ≈ 3.76:1` 측정 → 교체 불필요 |
| AC-SUX-050 (기타 범례 개수 병기) | **PASS** | `StockBubbleChart.m5.test` — `legend.formatter` 가 `기타 (N개 산업)` 형태 산출 단언 |
| AC-SUX-051 (hover 강조 범위) | **PASS** | `StockBubbleChart.m5.test` — 산점도 `emphasis.focus === 'none'`. **회귀 단언**: `RRGChart.tsx` / `BumpChart.tsx` 의 `focus:'series'` 불변(§1.2 PRESERVE 항 참조) |
| AC-SUX-059 (섹터 버블 색상 채널) | **PASS** | `SectorBubbleChart.m5.test` — 발산형 5단계 서로 다른 5색 매핑 + 기준점 **0%**(벤치마크 +1.88% 픽스처에서도 0% 버블이 중립색) + 경계 상수 단일 위치 + ColorLegend 구간 텍스트 + **채널 독립 대조 단언**(초과수익률만 바꾸면 색 불변 / 기간수익률만 바꾸면 색 변화) |
| AC-SUX-060 (테두리 채널 단일화) | **PASS-WITH-DEBT** | 종목 `{stage:2, trading_value:null}` → 흰 2px 실선(결측이 테두리를 덮지 않음) 구분가능성 단언 PASS. 정적 스캔 `grep -rnE "coverage.*border\|border.*coverage\|low_confidence.*border" frontend/src/components/SectorAnalysis/` → **0행** PASS. **Debt**: `coverage_ratio` 저커버리지의 툴팁 `⚠` + 하단 저신뢰 요약 목록 미구현 — `low_confidence`/`coverage_ratio` 가 소스 전역 0건(`grep -rn` → 0행). M6 AC-SUX-052 `MetricCell` ⚠ 상태와 함께 구현 예정 |
| AC-SUX-017 (RRG/Bump 요소 클릭 + state 보존) | **PASS** | `vitest SectorAnalysis.keepmounted.test` → 4 passed. mountedTabs lazy-mount + `display:none` keep-mounted — 마운트 카운터 목으로 탭 왕복 remount **0** 실증(M3/M4 deferred debt 해소). 미방문 탭 미마운트로 AC-SUX-033(M6 lazy fetch) 양립 |

### §1.2 보존 대상 회귀 확인 (M5 — PRESERVE 10항목) [PASS]
| # | 보존 항목 | 판정 |
|---|-----------|------|
| 1 | Bump `connectNulls:false` | **불변** — M5 는 `BumpChart.tsx` 미수정(`git log --oneline 5e3ff65..1dba4b0 -- BumpChart.tsx` → 0 commit) |
| 2 | Bump 날짜 합집합 축 | **불변** — 동일(미수정) |
| 3 | 종목 버블 색상 = 산업명(중) | **불변** — AC-SUX-048 가드 5 passed 지속. `SECTOR_MINOR_PALETTE` + `buildSectorMinorColorMap` 리터럴 고정 |
| 4 | 종목 버블 `기타` 범례 처리 | **불변** — AC-SUX-050 이 개수 병기만 **추가**(그룹핑 로직 자체는 미변경) |
| 5 | RRG/Bump `focus:'series'` | **불변** — AC-SUX-051 회귀 단언이 명시적으로 검사. 변경 대상은 StockBubbleChart 산점도뿐 |
| 6 | `MarketContext` TTL + `refresh()` | **불변** — M5 는 `MarketContext.tsx` 미수정 |
| 7 | `Promise.allSettled` 독립 실패 | **불변** — 동일(미수정) |
| 8 | 지수 백오프 2/4/8초 | **불변** — `RETRY_DELAYS_MS` 미수정 |
| 9 | Stage 세그먼트 토글 해제 | **불변** — M5 는 `StageDistributionBar.tsx` 미수정 |
| 10 | tooltip XSS 이스케이프 | **불변** — `StockBubbleChart.tsx` tooltip formatter 의 escape 경로 유지(M5 는 markLine·테두리·크기만 수정) |

### 회귀 (기존 프론트엔드 테스트) [PASS — 회귀 0건]
- 최종 `vitest run` → **540 tests passed (540)** (M4 종료 490 + M5 신규 50), `Test Files 2 failed | 59 passed (61)` — 실패 2건은 선행 e2e file-load(수집 테스트 0건) 불변.

### eslint (M5 수정 파일) [신규 error class 0]
- `eslint src/components/SectorAnalysis/` → **6 errors**. 클래스별: `react-refresh/only-export-components` 2 · setState-in-effect 3 · `@typescript-eslint/no-unused-vars` 1.
- **신규 error class 0**. 신규 *인스턴스* 1건(`SectorBubbleChart.tsx:38` — `sectorReturnColor`/상수 export 로 인한 `react-refresh/only-export-components`)은 `RRGChart.tsx:38` 과 동일한 기존 baseline 클래스.

### 커밋 + push (Route A Hybrid Trunk) — M5 차트별 6 commit
- `597eaf0` — M5 (1/6) AC-SUX-048 색상 회귀 가드 + `bubbleRadius` 공용 유틸 (4 files)
- `62ade59` — M5 (2/5) SectorBubbleChart 시각화 규약 (3 files)
- `2e23dd2` — M5 (3/5) StockBubbleChart 시각화 규약 (4 files)
- `e23d7a0` — M5 (4/5) RRG 시각화 규약 (2 files)
- `01120f3` — M5 (5/5) AC-SUX-017 keep-mounted 서브탭 (2 files)
- `1dba4b0` — M5 잔여: VZ-4 주석 `axisPointer` 리터럴 제거 (1 file, 주석 2행)
- `git show --stat` 6 commit 전수 확인 → `.agency/*` · `.claude/**` · `.moai/config|rules` migration mass **미유입**(B8/B10 git-add discipline — 명시 경로만 staging).

## §E.3 Run-phase Audit-Ready Signal

> 반자율 progression: **M5 GREEN** (시각화 — 차트별 6 commit 통과). M6~M7 잔여(로딩·오류·빈 상태 / 회귀게이트). 본 신호는 M1~M5 구간 — 전 run-phase 완료 아님.

```yaml
run_complete_at: 2026-08-14
run_commit_sha: 1dba4b0          # M5 잔여(최신). M1=c27a050 / M2=fc3dfc1 / M3=7975c7c / M4=dc4ad26,d28d505,cfdb87a / M5=597eaf0,62ade59,2e23dd2,e23d7a0,01120f3,1dba4b0.
run_status: M5-complete          # M1~M5 GREEN. M6~M7 잔여(반자율 progression). 전 run-phase 아님.
ac_pass_count: 45                # M1-M3(16) + M4(15) + M5 PASS 14(038/039/040/041/043/044/045/047/048/049/050/051/059/017) = 45
ac_pass_with_debt_count: 6       # AC-SUX-018(M2) + AC-SUX-032(M4) + M5: 042(벤치마크 절대값 백엔드 미전달) / 046(lookback_weeks·trail_start_date·RRG market 파라미터 미지원) / 060(저커버리지 ⚠ 툴팁+하단 요약 M6 연계). AC-SUX-017 은 M5 에서 PASS 로 승격(M3 debt 해소)
ac_fail_count: 0
ac_total_this_segment: 51        # M1-M3(18) + M4(16) + M5(17: 038~051/059/060/017). 전 SPEC 60 AC 중 9 잔여(M6: 033~037/052~055, M7: 056)
preserve_list_post_run_count: 10 # §1.2 보존 10항목 전부 미변경(M5 항목별 판정표 §E.2 참조, 회귀 0)
l44_pre_commit_fetch: "synced (단일 세션) — 01120f3 기준 0 0 divergence"
l44_post_push_fetch: "pending — M5 6 commit push 는 M6 종료 시점에 함께 수행(Route A)"
new_warnings_or_lints_introduced: 0   # 신규 eslint error class 0(신규 인스턴스 1: SectorBubbleChart.tsx:38, 기존 클래스); tsc 수정파일 NEW 0
cross_platform_build:
  applicable: false              # 프론트엔드 전용 SPEC (Go 빌드 태그 / C-HRA-008 N/A)
tsc_gate_b_total: 28             # baseline 28 == 최종 28 (M5 비증가; 수정파일 NEW 0)
tsc_gate_a_ts2353: 0             # HARD 게이트 (a) 유지(M3 달성 후 불변)
modified_files_new_tsc_errors: 0
total_run_phase_files: 72        # M1(8)+M2(9)+M3(20)+M4(24)+M5(11: 6 source + 5 test/new, 중복 제외)
m1_to_mN_commit_strategy: per-screen   # M5 차트별 6 commit(597eaf0/62ade59/2e23dd2/e23d7a0/01120f3/1dba4b0) + 각 conventional commit + 🗿 MoAI trailer
regression_tests: "540 pass (M4 종료 490 + M5 신규 50) / 2 e2e file-load baseline 불변 / 기존 490 전량 통과, 신규 회귀 0"
next_checkpoint: "M6 로딩·오류·빈 상태 — AC-SUX-033~037(쿼리키·TTL·stale-but-showing·재시도/새로고침·기준일 합치) + 052~055(MetricCell 5상태·0/50.0 금지·빈 상태 원인·상세 오류). M1 의 queryCache.ts + AnalysisParamsContext recordAsOf 가 M6 소비자를 기다리는 상태"
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
