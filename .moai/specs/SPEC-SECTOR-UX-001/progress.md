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

### M6 (로딩·오류·빈 상태 — commit 55720f2 / c2f7e38 / 148b873)

**Claim**: M6 의 9 AC(033~037 / 052~055)를 3 commit 으로 구현했고, §1.2 보존 10항목 회귀 0 · tsc 비증가(28) · vitest 회귀 0(603 pass)이다.
**Evidence(verbatim)**: 아래 AC matrix 각 행의 명령·출력 + 검증 배치 V1~V6(아래 §검증 배치).
**Baseline-attribution**: M5 종료 baseline(§E.2 M5) tsc **28** / TS2353 **0** / vitest **540 pass** / eslint(src/ 전체) **35 errors**(worktree `1dba4b0` 실측). M6 종료 실측 tsc **28**(비증가) / TS2353 **0** / vitest **603 pass** / eslint **42 errors**.
**Gaps**:
- AC-SUX-033 의 "부팅 시 비활성 탭 fetch 0" 은 **useQuery 계층에서만 실증**했다. 앱 최상단 `MarketProvider`(§1.2 보존 6·7·8 대상 — 미수정)는 여전히 boot 시 `/api/sectors/ranking` 을 즉시 호출하므로, 앱 전체 관점의 "부팅 시 섹터 엔드포인트 fetch 0" 은 성립하지 않는다 → **PASS-WITH-DEBT**.
- 섹터 분석 Table 서브탭은 여전히 MarketContext 소스다(PRESERVE 6 유지). 따라서 Table 의 TTL·백오프·stale-but-showing 은 MarketContext 기존 구현이 담당하고, 신설 조회 계층은 Bubble/종목탐색/상세가 소비한다.
- RRG/Bump 서브탭은 자체 조회를 소유하며 M6 에서 useQuery 로 전환하지 않았다 — 두 화면의 기준일 배지는 `AnalysisParamsContext` 에 기록된 전역 값으로 폴백한다(SN-4 노출은 충족, 화면별 조회 계약은 미전환).
- AC-SUX-052 의 "5개 화면 동일 렌더" 는 React DOM 을 가진 3개 화면(순위표·종목표·섹터상세)에서 공용 컴포넌트로 실증했다. 차트 3종(섹터버블·RRG·Bump)의 결측 표기는 ECharts tooltip 문자열이라 MetricCell 이 렌더할 수 없다 → **PASS-WITH-DEBT**.
**Residual-risk**: `useQuery` 는 렌더 identity 에 민감하다(fetcher/meta/retryDelays/recordAsOf 를 ref 로 읽는 이유). 소비자가 이 계약을 어기고 dep 에 인라인 값을 넣으면 무한 재조회가 재발할 수 있다 — 구현 중 실제로 2회 발생(OOM/18739회 호출)했고 ref + 버전당 1회 무효화로 차단했다. 라이브 브라우저 스모크는 미실시(M7 §6-6 소관).

**AC PASS/FAIL matrix (M6)** — 9 AC
| AC | Status | Verification (verbatim command + output) |
|----|--------|------------------------------------------|
| AC-SUX-033 (쿼리 키·조회 시점) | **PASS-WITH-DEBT** | `vitest DataLoadContext.test` — enabled:false → fetch 0 / 활성화 시 1회 / TTL 내 왕복 추가 0회 / 키 변경 시 활성만 즉시·비활성은 활성화 시점. `vitest BubbleChart.m6` — `active=false` 에서 `fetchSectorBubble`·`fetchStockBubble` **미호출**. **Debt**: 앱 최상단 MarketProvider 는 boot 시 ranking 을 호출(§1.2 보존 6 유지) — 앱 전체 "부팅 시 0 fetch" 는 미성립 |
| AC-SUX-034 (TTL 1시간) | **PASS** | `vitest DataLoadContext.test` — `Date.now` 스텁으로 59분 → fetch 1회 유지, +2분(총 61분) → fetch 2회. TTL 상수는 `queryCache.ts CACHE_TTL_MS` 단일 위치이며 전 엔드포인트가 이 캐시를 공유 |
| AC-SUX-035 (stale-but-showing) | **PASS** | `vitest DataLoadContext.test` — 재조회 중 `data` 유지 + `refetching=true` + `loading=false`. `vitest BubbleChart.m6` — **DOM 노드 동일성 단언**(`expect(during).toBe(before)`) 통과 + `refetch-spinner` 렌더. 실패 시 `갱신 실패 — 표시 중인 데이터는 2026-08-07 기준입니다` + `[다시 시도]`. **되돌림 RED 관측**(아래 verbatim) |
| AC-SUX-036 (재시도·수동 새로고침) | **PASS** | `vitest DataLoadContext.test` — fake timer 로 2s/4s/8s 3회 재시도 후 **정지**(60s 추가 경과에도 4회 유지) + `retryExhausted=true`; 4회째 성공 시 데이터 채워지고 exhausted 미설정. `vitest BubbleChart.m6` — `⟳ 새로고침` 최초 로딩·성공 양쪽에서 상설 렌더 + 클릭 시 TTL 내에도 재조회(1→2회). 워밍업 실패 후 재활성화 자가 복구 1 passed |
| AC-SUX-037 (기준일 합치) | **PASS** | `vitest DataLoadContext.test` — 다른 날짜 2패널 → `conflict.dates=['2026-08-07','2026-08-11']` + `panels=['섹터 순위','종목 탐색']`; 같은 날짜 → conflict null; grid_version 변경 → 전 캐시 무효 + 타 패널 재조회; 응답 메타가 `AnalysisParams.asOfDate/asOfIsPartialWeek/gridVersion` 에 기록. `vitest asof-screens` — Table/RRG/Bump 3 pane 이 각자 `data-status-bar` + 내부 `as-of-badge` 보유(루프 단언), 충돌 띠에 두 날짜·두 패널명·`[새로고침]`. `vitest BubbleChart.m6` — 배지 텍스트 `'기준일 2026-08-11'` **문자열 동등** + `as_of_is_partial_week` true/false 분기. **되돌림 RED 관측**(아래 verbatim) |
| AC-SUX-052 (셀 5상태) | **PASS-WITH-DEBT** | `vitest MetricCell.test` 13 passed — `–` / `0.00%` / `계산 불가` / `42 ⚠` / `42 ❗` 5상태 텍스트가 서로 다르고(5종 distinct), 상태별 class 5종 distinct, 계산불가·⚠·❗ 에 title 툴팁. `vitest er2-screens` — 순위표·종목표의 결측 셀이 **같은 텍스트·같은 className**. **Debt**: 차트 3종(섹터버블·RRG·Bump)의 결측 표기는 ECharts tooltip 문자열이라 MetricCell 미적용 |
| AC-SUX-053 (0/50.0/NaN 금지) | **PASS** | `vitest MetricCell.test` — null/undefined/NaN/`{value:null}` 전부 `–`, `0.0` 은 `0.00%`. `vitest er2-screens` — null 픽스처 렌더에서 DOM 텍스트에 `NaN` 0건 · `50.0` 0건 · 런타임 예외 없음(`expect(...).not.toThrow()`), 결측 7셀 `–` / 실제 0 셀만 `0.0%`. `SectorRankingTable.formatReturn` 의 무조건 `toFixed(1)` 경로 제거(= `percent1` 재export, 결측은 MetricCell 이 선차단). **되돌림 RED 관측 2건**(아래 verbatim) |
| AC-SUX-054 (빈 상태 원인) | **PASS** | `vitest StockExplorer.m6` 5 passed — 섹터=디스플레이+Stage=2+시장=KOSPI 로 0건일 때 라벨 **3개**(`Stage 2`/`시장 KOSPI`/`섹터 디스플레이`) + 액션 3개(`[Stage 필터 해제]`/`[시장 전체로]`/`[섹터 스코프 해제]`). `[시장 전체로]` 클릭 → 시장만 해제(행 복귀) + `setSectorScopeFollow` **미호출**; `[섹터 스코프 해제]` → `setSectorScopeFollow(false)` **1회만**. 결과가 있으면 빈 상태 미렌더. **되돌림 RED 관측**(아래 verbatim) |
| AC-SUX-055 (섹터 상세 오류) | **PASS** | `vitest SectorDetailPanel.m6` 3 passed — 실패 시 `sector-detail-error` + `[다시 시도]`, 재시도 성공 시 오류 소멸, 빈 응답은 "이 섹터에는 표시할 세부 구성이 없습니다". 정적 스캔: `grep -n "catch(() => {})" frontend/src/components/SectorAnalysis/SectorDetailPanel.tsx` → **0행**(exit 1), `grep -rn "Sub-sector breakdown available in future update" frontend/src/` → **0행**(exit 1). **되돌림 RED 관측**(아래 verbatim) |

#### Lesson #9 [HARD] 대조 단언 — 되돌림 RED 관측 verbatim (7건)

각 변형은 scratchpad `cp` 백업 → 변형 주입 → RED 관측 → `cp` 복원 → `diff` 빈 결과 + 변형 마커 `grep -c` **0** 순으로 실증했다(`git checkout-index` 미사용 — 미커밋 작업물 보호, feedback_mutation_restore).

1. **`mut_er2_null_to_zero`** (MetricCell.normalize: `null → {value: 0}`)
   ```
   AssertionError: expected '0.0%' not to contain '0.0'
   AssertionError: expected '0.0%' to be '–' // Object.is equality
   Tests  2 failed | 11 passed (13)
   ```
2. **`mut_er2_rs_neutral_fill`** (순위표 rs_avg 를 `(x ?? 50).toFixed(1)` 로 중립값 대체)
   ```
   AssertionError: expected 6 to be 7 // Object.is equality
   AssertionError: expected 'Rank ▲Sector1Wⓦ1Mⓦ3MⓦRS AvgⓔRS Top %ⓔ…' not to contain '50.0'
   Tests  2 failed | 5 passed (7)
   ```
3. **`mut_ld_c_unmount_on_refetch`** (BubbleChart: `refetching` 시 차트 언마운트 — 현행 깜빡임 복원)
   ```
   TestingLibraryElementError: Unable to find an element by: [data-testid="sector-bubble"]
   AssertionError: expected <div …(2)></div> to be <div …(2)></div> // Object.is equality
   Tests  2 failed | 6 passed (8)
   ```
4. **`mut_asof_frontend_reformat`** (배지에서 응답 날짜를 `08/11` 로 가공)
   ```
   AssertionError: expected '기준일 08/11' to be '기준일 2026-08-11' // Object.is equality
   AssertionError: expected '기준일 08/11' to contain '2026-08-11'
   Tests  2 failed | 13 passed (15)
   ```
5. **`mut_ac055_silent_swallow`** (SectorDetailPanel: `detailError` 를 null 고정 — 조용한 삼킴 복원)
   ```
   TestingLibraryElementError: Unable to find an element by: [data-testid="sector-detail-error"]
   TestingLibraryElementError: Unable to find an element by: [data-testid="sector-detail-error"]
   Tests  2 failed | 3 passed (5)
   ```
6. **`mut_ac054_global_clear`** (`[시장 전체로]` 가 Stage·섹터 스코프까지 함께 해제 — 전역 clear)
   ```
   AssertionError: expected "vi.fn()" to not be called at all, but actually been called 1 times
   Tests  1 failed | 4 passed (5)
   ```
7. **복원 실증(전 7건 공통)**: `diff <scratchpad backup> <file>` → **빈 결과(DIFF_EMPTY)**, `grep -c "<변형 마커>" <file>` → **0**. 복원 후 각 테스트 재실행 GREEN 복귀 확인.

**판정**: 6개 변형 전부에서 GREEN 이 아닌 **RED 를 실제로 관측**했다 → 항진명제 아님 실증(Lesson #9 충족).

#### 검증 배치 (read-only, M6 종료 시점 실측)
| # | 항목 | 결과 |
|---|------|------|
| V1 | `vitest run` 전체 | `Test Files 2 failed \| 66 passed (68)` / `Tests 603 passed (603)` — 실패 2건은 선행 e2e file-load(수집 테스트 0건) 불변 |
| V2 | `tsc -p tsconfig.app.json --noEmit` | `error TS` **28**(baseline 28, 비증가) / `TS2353` **0** / M6 수정·신규 파일 NEW **0** |
| V3 | AC-SUX-055 grep 1 | `grep -n "catch(() => {})" .../SectorDetailPanel.tsx` → **0행**(exit 1) |
| V4 | AC-SUX-055 grep 2 | `grep -rn "Sub-sector breakdown available in future update" frontend/src/` → **0행**(exit 1) |
| V5 | eslint `src/` 전체 | **42 errors** vs M5 baseline **35**(worktree `1dba4b0` 실측). 클래스별 delta: `react-refresh/only-export-components` 13→**20**(+7). 그 외 전 클래스 불변(`react-hooks/refs` 4=ChartCell 선행분, `set-state-in-effect` 6, `no-unused-vars` 8, `no-explicit-any` 2, `immutability` 2). **신규 error class 0** |
| V6 | §1.2 PRESERVE 10항목 | `git diff 1dba4b0 -- <file>` 이 BumpChart/StockBubbleChart/RRGChart/MarketContext/StageDistributionBar **전부 0행**. 계약 grep: `connectNulls: false` 1 · `focus: 'series'` RRG 1/Bump 1 · `Promise.allSettled` 1 · `RETRY_DELAYS_MS = [2000, 4000, 8000]` MarketContext 1/StockExplorer 1 · `CACHE_TTL_MS` 2 |

### §1.2 보존 대상 회귀 확인 (M6 — PRESERVE 10항목) [PASS]
M6 는 §1.2 보존 항목을 **한 파일도 수정하지 않았다**(V6 — 5개 소유 파일 전부 `git diff 1dba4b0` 0행). 항목별:
1 Bump `connectNulls:false` · 2 Bump 날짜 합집합 축 · 5 RRG/Bump `focus:'series'` → `BumpChart.tsx`/`RRGChart.tsx` 미수정. 3 종목 버블 색상 = 산업명(중) · 4 `기타` 범례 · 10 tooltip XSS 이스케이프 → `StockBubbleChart.tsx` 미수정(AC-SUX-048 가드 5 passed 지속). 6 MarketContext TTL+refresh · 7 `Promise.allSettled` · 8 지수 백오프 2/4/8초 → `MarketContext.tsx` 미수정(StockExplorer 의 `RETRY_DELAYS_MS` 도 값·export 유지, useQuery 에 그대로 주입). 9 Stage 세그먼트 토글 해제 → `StageDistributionBar.tsx` 미수정.

### 커밋 + push (Route A Hybrid Trunk) — M6 관심사별 3 commit
- `55720f2` — M6 (1/3) MetricCell 공용 5상태 셀 + 0/50.0/NaN 렌더 금지 (8 files)
- `c2f7e38` — M6 (2/3) 공용 조회 계층 — 쿼리키·TTL·stale-but-showing·재시도·기준일 (22 files)
- `148b873` — M6 (3/3) 빈 상태 원인 표기 + 섹터 상세 오류 표시 (6 files)
- `git show --stat` 3 commit 전수 확인 → `.agency/*` · `.claude/**` · `.moai/config|rules|project` migration mass · `frontend/coverage/` · `frontend/test-results/` · 루트 `*.txt` **미유입**(B8/B10 git-add discipline — 명시 경로만 staging).

### M7 (회귀 게이트 + 성능 측정 + F1 수정 + D2 해소)

**Claim**: AC-SUX-056(R1~R5)을 구현하고, F1(캐시 적중 경로의 전역 기준일 누락)을 수정했으며, D2(텍스트 헬퍼 추출)로 AC-SUX-052 의 텍스트 병행을 해소했다. §0.3 X1~X6 제거·§1.2 보존 10항목·§0.2 성능·모바일 hover-only 를 기계적으로 실측했다. 미판정으로 남아 있던 AC-SUX-010 을 함께 판정했다.
**Evidence(verbatim)**: 아래 AC matrix 각 행 + 검증 배치 W1~W5 + Lesson #9 되돌림 RED 8건.
**Baseline-attribution**: M6 종료 baseline(`6a941a6` 실측) — tsc **28** / TS2353 **0** / vitest **603 pass** + e2e file-load 실패 2 file / eslint(src/) **42 errors**. M7 종료 실측 — tsc **28**(비증가) / TS2353 **0** / vitest **655 pass**(+52) / e2e 실패 2 file **불변** / eslint **45 errors**.
**Gaps**:
- **§0.2 "종목 표 500행 +20% 이내"는 판정 불가** — 비교 기준인 *3열 추가 이전* baseline 이 M4 착수 전에 측정되지 않았다. 현재 코드에는 기간 3열을 끌 수 있는 스위치가 없어 사후 재현도 불가능하다. 절대 실측값과 비교 가능한 대리 지표(접기 3단계 = 다른 3열 제거 시 델타)만 기록한다. **수치를 지어내지 않는다.**
- **§0.2 INP P95 / FCP / 기간·시장 토글 P95 지연은 미측정** — 실브라우저 계측이 필요하며 jsdom 에서 산출할 수 없다. 헤드리스 대리 측정으로 갈음하지 않는다.
- **AC-SUX-052 의 스타일 병행은 범위 밖(N/A)** — debt 가 아니라 물리적 불가다. ECharts tooltip 은 formatter 가 만드는 **문자열**이며 스타일시트가 닿는 DOM 이 아니다. 본 SPEC 이 통일한 것은 텍스트다.
- **§0.2 리렌더 가드의 한 방향은 구조적으로 보장되어 변형 불가** — `selectedSector` 변경 → Params 소비자 리렌더 0 은 Provider 중첩 순서(AnalysisParams 가 Selection 의 조상)로 React 가 보장한다. 두 파일 안에서 이를 falsify 하는 변형을 만들지 못했다. 반대 방향(period → Selection 소비자 0)은 Context 병합 변형으로 RED 를 관측했다.
- **AC-SUX-056 R1 의 원문 grep 은 0행이 아니라 1행** — 아래 R1 행에 실측과 명시 제외 근거를 그대로 남긴다.
**Residual-risk**: 정적 스캔(X1~X6 · 보존 10항목)은 **문자열 계약**을 고정한다. 구현이 같은 의미를 유지한 채 표현만 바꾸면(예: `connectNulls: false` 를 변수로 추출) 스캔이 거짓 실패한다 — 그때는 스캔을 갱신할 것이지 계약을 바꾸지 말 것. 라이브 브라우저 스모크는 여전히 미실시다.

**AC PASS/FAIL matrix (M7)**

| AC | Status | Verification (verbatim command + output) |
|----|--------|------------------------------------------|
| AC-SUX-056 R1 (기간 변경 → 로딩) | **PASS** | 긍정: `vitest M7.regression-gate` — period `1m→3m` 후 `findByTestId('refetch-spinner')` 렌더 + `closest('[data-testid="data-status-bar"]')` 비-null(기준일 배지와 같은 상태 바). 부재 확인 **원문 grep = 1행**: `BubbleChart.m6.test.tsx:88 expect(screen.queryByTestId('refetch-spinner')).not.toBeInTheDocument()`. 이 1건은 재조회 **완료 후 소멸** 단언이며(같은 파일 78행이 등장을 긍정 단언) R1 이 막는 '기간 변경 **시점**의 로딩 부재 요구'와 다른 경로다 → R2 가 규정한 "라인 주석 표시" 방식을 라인 단위로 적용해 `AC-SUX-056-R1-ALLOW` 마커로 명시 제외. **제외 후 0행**. 원문 1행이 2행으로 늘면 테스트가 먼저 실패한다(`toHaveLength(1)` 고정) |
| AC-SUX-056 R2 (정렬 변경 → 고지 띠) | **PASS** | 긍정: AC-SUX-022 와 동일 대상 — `SectorAnalysis.m4.test` 가 `getByTestId('sort-notice')` 렌더를 실증(M7 이 해당 단언의 실재를 재확인). 부재 확인 grep(allowlist=`SectorAnalysis.m4.test.tsx`) → **0행**. allowlist 근거: rank 정렬 상태의 띠 부재 단언은 고지 띠 계약 자체의 일부(acceptance.md R2 명시 조항) |
| AC-SUX-056 R3 (버블 크기 분포) | **PASS** | `vitest M7.regression-gate` — 거래대금 15종(1.2e10~8.2e12) 기준 로그 매핑 표준편차 > 선형 매핑 표준편차, 최소밴드(하위 2px) 뭉침 개수 선형 > 로그. **대조군 설계 정정**: 최초 작성한 대조군은 구현과 두 군데(로그 u + 면적 sqrt)가 달라 구현을 선형화해도 RED 가 나지 않았다 — **항진명제였다.** 대조군을 "면적 sqrt 는 동일, u 만 선형"으로 좁힌 뒤 되돌림 RED 관측(아래 변형 3) |
| AC-SUX-056 R4 (RRG 궤적 단축) | **PASS** | `vitest M7.regression-gate` — 응답 trail 20주 픽스처에서 그려진 점 수 **8** < 20. "짧다"가 아니라 `toBe(8)`(TRAIL_WINDOW 계약)로 고정 |
| AC-SUX-056 R5 (KOSPI 필터 행 감소 + 제외 영역) | **PASS** | **검증 범위 = Table · 섹터 Bubble · RRG 한정**(O-U9). Table: `tbody tr` 3→2 감소 + `excluded-sectors` 텍스트 `순위 대상 제외 (1)` → `(2)`, 제외 섹터명 본문 노출. 섹터 Bubble: 응답 `sectors[]` 밖 섹터의 데이터 포인트 미생성(`['반도체','은행']`). RRG: 시리즈 이름 `['반도체']`(`__bg__` 제외). **Bump 는 대상 아님** — 반대 방향 단언(제외 섹터 선이 Bump 에 남는다)은 `BumpChart.m4.test.tsx` 의 AC-SUX-019 describe 가 M4 부터 담당하며 M7 에서 중복 추가하지 않았다 |
| AC-SUX-010 (탭 왕복 컨텍스트 보존) | **PASS** | **M1~M6 에서 미판정으로 누락**되어 있던 AC 를 M7 에서 판정했다(M7 착수 시 progress 기록 58 AC vs acceptance 60 AC 대사로 발견). `vitest M7.static-scan` — `AppContent.tsx` 의 상단 5탭이 전부 `display: activeTab === '…' ? 'flex' : 'none'` keep-mounted(조건부 언마운트 `activeTab === '…' && <` 패턴 0건) → subTab·sortField·stageFilter·체크 등 로컬 상태가 탭 왕복에 소멸하지 않는다. 서브탭도 `mountedTabs` + `display: subTab ===` keep-mounted(M5 AC-SUX-017). `period`·`selectedSector` 는 탭 위 Provider 소유(AppContent 로컬 state 아님). 탭 내비게이션 전용 뒤로가기 부재: `history.back|goBack|<BackButton` 소스 전량 **0행**. **주의**: `BubbleChart` 의 `← 섹터 목록` 은 Bubble 서브탭 **내부 드릴다운 복귀**이며 탭 내비게이션용이 아니다 — AC-SUX-010 금지 대상 아님 |
| AC-SUX-037 (기준일 합치) | **PASS** (F1 적합성 결함 수정 포함) | M6 판정 유지 + **F1 수정**: `DataLoadContext.useQuery` 의 **캐시 적중 분기**가 `registerAsOf` 만 호출하고 `recordAsOf`(전역 `AnalysisParams.asOfDate`)를 건너뛰었다. 전역 값은 `asOfDate` prop 을 넘기지 않는 화면(**RRG·Bump**)의 `DataStatusBar` 폴백 소스라 자기 배지와 전역 배지가 어긋나고, `registerAsOf` 는 갱신되므로 **합치 경고 띠도 뜨지 않는 조용한 불일치**였다. 재현 테스트(키 A→B→A 캐시 적중) 선행 RED verbatim: `AssertionError: expected '2026-08-11' to be '2026-08-01' // Object.is equality`. 수정 후 GREEN(`contexts/__tests__` 49 passed). `noteGridVersion` 은 적중 경로에서 호출하지 않는다 — `QueryCache.setGridVersion` 이 버전 변경 시 Map 을 통째로 비우므로(queryCache.ts:27) 살아남은 엔트리는 반드시 현재 버전이며 재통지는 `prev === version` 무동작이다(코드 주석에 근거 기록) |
| AC-SUX-052 (셀 5상태 화면 간 동일) | **PASS** (M6 PASS-WITH-DEBT → 해소) | **D2 해소**: `MetricCell` 에서 상태 해석 + 표시 문자열 생성을 순수 함수 `metricDisplay` / `metricText` 로 추출하고, `MetricCell`(표 DOM)과 `SectorBubbleChart`·`RRGChart`·`BumpChart` 의 ECharts tooltip formatter 가 **같은 함수**를 호출한다. `vitest MetricTextParity.m7` 12 passed — 동일 픽스처 7종(null/undefined/NaN/표본부족/저신뢰/경고/실제0)에서 표 셀 렌더 텍스트 == `metricText` 출력. 섹터버블 결측 3지표 전부 `–`(NaN 누출 0), RRG 결측 좌표 `–`, Bump 결측 종합점수 `–`(종전 ASCII `-` 이탈 제거). 값이 있을 때의 포맷은 종전 유지(`초과수익률: 2.50%` / `RS 평균: 60.0` / `기간수익률: +4.00%` / `RS-Ratio: 108.12` / `종합점수: 80.00`). **스타일 병행은 범위 밖 N/A**(위 Gaps — ECharts tooltip 은 DOM 이 아님). 구현 중 `Number(null) === 0` 으로 결측이 실제 0 으로 둔갑하는 경로를 테스트가 잡아내 `toMetricValue`(null 보존 변환)를 추가했다 |
| AC-SUX-033 (쿼리 키·조회 시점) | **PASS-WITH-DEBT** (유지) | M6 판정 유지. **2026-08-14 사용자 결정 — MarketProvider 현행 유지, 부팅 시 sector fetch 1회 잔존은 후속 SPEC 항목.** 따라서 M7 에서 `MarketContext.tsx` / MarketProvider 마운트 시점을 수정하지 않았다(파일 변경 0). useQuery 계층의 비활성 탭 fetch 0 은 M6 실증 그대로 유효하며, 앱 전체 관점의 "부팅 시 섹터 엔드포인트 fetch 0" 은 미성립 상태로 남는다 |

#### §0.2 성능 실측 (기계적 측정 — Profiler 미사용 근거는 위 Gaps)

| 측정 지점 | 실측 | 판정 |
|---|---|---|
| `selectedSector` 변경 시 무관 컴포넌트 리렌더 수 | **0** (AnalysisParams 만 소비하는 컴포넌트 리렌더 델타 0, Selection 소비자는 정확히 1) | 목표(0) **충족** |
| `period` 변경 시 Selection 만 소비하는 컴포넌트 리렌더 수 | **0** (Params 소비자는 정확히 1) | Context 분리 목적 **충족** — 병합 변형 시 RED |
| 부팅 시 비활성 탭 fetch 수 | **0** (`BubbleChart` `active=false` 에서 `fetchSectorBubble`·`fetchStockBubble` 미호출 — M6 실증 유지) | 활성 탭만 조회 **충족**. 단 MarketProvider 잔존분은 AC-SUX-033 debt |
| 종목 표 500행 렌더 (12열, collapseLevel 0) | median **104.9ms** (5회: 119.7 / 104.9 / 99.7 / 97.9 / 146.1) | 절대 실측 기록 |
| 종목 표 500행 렌더 (9열, collapseLevel 3) | median **101.2ms** (5회: 115.0 / 102.2 / 101.2 / 96.6 / 99.9) | 3열 델타 **+3.6%** — 대리 지표 |
| 종목 표 3열 추가 전후 +20% 이내 | **판정 불가 (Gap)** | 비교 기준 baseline 부재 — 위 Gaps 참조 |
| INP P95 / FCP / 토글 P95 지연 | **미측정 (Gap)** | 실브라우저 계측 필요 |

#### §0.3 제거 목록 X1~X6 실측 (`vitest M7.static-scan` — 소스 전량 173파일, `__tests__` 제외)

| # | 대상 | 실측 |
|---|---|---|
| X1 | Table 툴바 별도 기간 토글 | `data-testid="period-toggle"` 소스 전량 **1곳**(SectorAnalysis 헤더 단일 인스턴스) |
| X2 | Bubble 툴바 별도 기간·시장 토글 | `BubbleChart.tsx` 에 `(period\|market)-toggle` **0행** + `useAnalysisParams()` 소비 확인 |
| X3 | 섹터 버블 `axisPointer` 값 라벨 상자 | 주석행 제외 실코드 **0행**(`@MX:NOTE` 재도입 금지 주석만 잔존) |
| X4 | `Sub-sector breakdown available in future update` | 소스 전량 **0행** |
| X5 | `crossTabParams` / `CrossTabParams` | 소스 전량 **0행** |
| X6 | RRG 축 하드코딩 `min:75` / `max:125` | 소스 전량 **0행** + 대체 구현 `rrgHalf` 실재 확인. **오탐 처리**: `RRGChart.m5.test.tsx:35` 의 `/min: 75\|max: 125/` 는 부재를 단언하는 정규식 리터럴이므로 스캔 대상에서 구조적으로 제외(테스트 파일 미포함) |

#### §1.2 보존 대상 10항목 실측 (`vitest M7.static-scan`)

| # | 항목 | 실측 |
|---|---|---|
| 1 | Bump `connectNulls: false` | `connectNulls:\s*false` **1건**, `true` **0건** |
| 2 | Bump 날짜 합집합 축 | `const dateSet = new Set<string>()` + `sector.history.forEach(w => dateSet.add(w.date))` + `Array.from(dateSet).sort()` 3구조 전부 잔존 |
| 3 | 종목 버블 색상 = 산업명(중) | `@MX:ANCHOR: [AUTO] 색상 결정성 매핑` + `sector_minor` 잔존, Stage 재배정 패턴 **0행** |
| 4 | 종목 버블 `기타` 범례 처리 | `'기타'` + `legendFormatter` 잔존 |
| 5 | RRG/Bump `focus: 'series'` | RRG **1건** / Bump **1건** |
| 6 | MarketContext TTL + `refresh()` | `CACHE_TTL_MS` + `refresh` 잔존 (파일 미수정 — AC-SUX-033 사용자 결정) |
| 7 | `Promise.allSettled` 독립 실패 | **1건** |
| 8 | 지수 백오프 2/4/8초 | MarketContext **1건** + StockExplorer **1건** |
| 9 | Stage 세그먼트 토글 해제 | `if (activeStage === stageKey) { onStageClick(null)` 잔존 |
| 10 | tooltip XSS 이스케이프 | `function escapeHtml` 정의 + 호출 **2건 초과**. **D2 는 `StockBubbleChart.tsx` 를 수정하지 않았다** — `metricText` 미유입(**0행**) + `const name = escapeHtml(` 경로 그대로 |

> D2 대상 3파일(섹터버블·RRG·Bump)의 tooltip 은 사용자 입력을 싣지 않으며 `metricText` 출력은 숫자 포맷 문자열 또는 상수(`–` / `계산 불가` / `⚠` / `❗`)뿐이라 HTML 메타문자를 만들지 않는다. 3파일 모두 `innerHTML` **0행**.

#### 모바일 폭(E6 / A5) — hover-only 정보 0건

- 순위표(제외 영역 포함): `title` 을 가졌으나 본문 텍스트가 빈 요소 **0건**. 제외 섹터의 섹터명·종목 수가 본문 텍스트로 노출.
- 종목 표 접기 3단계(가장 좁은 폭): `title` 전용 요소 **0건**.
- 접기 전후 행 수 동일(30 = 30) — 열이 접혀도 행 정보가 소실되지 않는다.
- **기간 3열(1W/1M/3M)은 접기 0~3 전 단계에서 헤더에 잔존**(AC-SUX-061 Lesson #3 게이트).
- 한정: `title` 에 담긴 **부연 설명**(예: `표본이 부족해 계산할 수 없습니다`)은 여전히 hover 로만 읽힌다. 본 단언이 보장하는 것은 "값 자체가 hover 뒤에만 숨지 않는다"이다.

#### Lesson #9 [HARD] 대조 단언 — 되돌림 RED 관측 verbatim (8건)

각 변형은 scratchpad `cp` 백업 → 변형 주입(마커 삽입 확인) → RED 관측 → `cp` 복원 → `diff` **0행** + 마커 `grep -c` **0** 순으로 실증했다(`git checkout-index` 미사용 — 미커밋 작업물 보호).

1. **F1 (수정 전 상태 자체가 RED)** — 캐시 적중 분기의 `recordAsOf` 부재
   ```
   AssertionError: expected '2026-08-11' to be '2026-08-01' // Object.is equality
   Expected: "2026-08-01"  Received: "2026-08-11"
   Tests  1 failed | 20 passed (21)
   ```
2. **`mut_d2_bypass_metrictext`** (섹터버블 tooltip 이 `metricText` 를 우회해 `Number(d[0]).toFixed(2)` 로 복귀)
   ```
   AssertionError: expected '<b>결측섹터</b><br/>초과수익률: 0.00%<br/>RS 평…' to contain '초과수익률: –'
   Tests  1 failed | 11 passed (12)
   ```
3. **`mut_r3_linear_size`** (`bubbleRadius` 의 로그 u 를 선형 u 로 치환)
   ```
   AssertionError: expected 15.354038008892609 to be greater than 15.354038008892609
   AssertionError: expected 7 to be greater than 7
   Tests  2 failed | 8 passed (10)
   ```
   → 두 값이 **정확히 같아진다**. 이것이 대조군을 "u 만 다르게" 좁힌 뒤에야 관측된 RED다(좁히기 전에는 GREEN — 항진명제였음을 실측으로 확인하고 정정).
4. **`mut_r4_full_trail`** (`winStart = Math.max(0, windowEnd - TRAIL_WINDOW)` → `0`)
   ```
   AssertionError: expected 20 to be less than 20
   Tests  1 failed | 9 passed (10)
   ```
5. **`mut_r5_no_excluded_area`** (`excluded && excluded.length > 0 &&` → `false &&`)
   ```
   Tests  1 failed | 9 passed (10)   ("행 수가 줄고(3→2) 하단 제외 영역이 커진다(1→2)" 실패)
   ```
6. **`mut_preserve1_connectnulls_true`** (`connectNulls: false` → `true`)
   ```
   AssertionError: expected +0 to be 1 // Object.is equality
   Tests  1 failed | 17 passed (18)
   ```
7. **`mut_ctx_merge`** (SelectionContext 가 `useAnalysisParams().period` 를 value 의존성에 포함 — 두 Context 병합 효과)
   ```
   AssertionError: expected 1 to be +0 // Object.is equality
   Tests  1 failed | 6 passed (7)   ("period 변경 → Selection 만 소비하는 컴포넌트 리렌더 0" 실패)
   ```
8. **`mut_a010_conditional_unmount`** (AppContent 섹터분석 탭을 `display` 토글 → 조건부 언마운트로 치환)
   ```
   AssertionError: expected 4 to be greater than or equal to 5
   Tests  1 failed | 21 passed (22)
   ```

**무효 변형 2건도 함께 기록한다** (RED 미관측 = 항진명제 아님):
- `Math.log10` 치환 시도 → 대상 문자열 부재(`bubbleRadius.ts` 는 `Math.log` 사용)로 **replace 무동작**. GREEN 은 테스트의 문제가 아니라 변형의 문제였고, 대상을 정정해 위 변형 3에서 RED 를 관측했다.
- AnalysisParamsProvider 에 미사용 `selectedSector` state 추가 → 아무 것도 그 state 를 쓰지 않아 **결합이 발생하지 않음**. 실제 결합 변형(위 변형 7)으로 대체해 RED 를 관측했다.

**판정**: 8개 변형 전부에서 **RED 를 실제로 관측**했다 → 항진명제 아님 실증(Lesson #9 충족). 무효 변형 2건은 "테스트가 약하다"가 아니라 "변형이 안 걸렸다"임을 구분해 기록한다.

#### 검증 배치 (read-only, M7 종료 시점 실측 — 증거: `.moai/state/verify/m7/`)

| # | 항목 | 결과 |
|---|------|------|
| W1 | `npx vitest run` 전체 | `Test Files 2 failed \| 70 passed (72)` / `Tests 655 passed (655)` — 실패 2건은 선행 e2e file-load(`e2e/ai-report-deep.spec.ts` · `e2e/preset-flow.spec.ts`, 수집 테스트 0건) **불변**. M6 종료 603 → **+52**(M7 신규), 기존 603 전량 통과 = **회귀 0** |
| W2 | `npx tsc -p tsconfig.app.json --noEmit` | `error TS` **28**(baseline 28, 비증가) / `TS2353` **0**(HARD 게이트 (a) 유지) / M7 수정·신규 파일 NEW **0**. 중간에 신규 5건(M7 테스트 2파일)이 발생했으나 prop 명 오류(`sortKey`/`sortDir` → 실제는 `sortField`/`sortDirection`/`selectedSector`)와 타입 미사용을 정정해 0으로 되돌림 |
| W3 | `npx eslint src/` | **45 errors / 2 warnings** vs M6 baseline **42 errors**. 클래스별: `react-refresh/only-export-components` 20→**23**(+3 — `MetricCell.tsx` 의 신규 export 3종 `metricDisplay`/`metricText`/`toMetricValue`). 그 외 전 클래스 baseline 불변(`no-unused-vars` 8 · `set-state-in-effect` 6 · `react-hooks/refs` 4 · `immutability` 2 · `no-explicit-any` 2). **신규 error class 0** — 작성 중 발생한 신규 클래스 `react-hooks/globals` 4건과 `immutability` +3건은 테스트를 콜백 기반으로 재구성해 **전부 제거**했다 |
| W4 | 정적 스캔 공허통과 방지 | `M7.static-scan` 이 글롭 대상 **173파일** 미만(<50)이면 즉시 throw — `toEqual([])` 단언이 빈 글롭으로 무의미하게 통과하는 경로를 구조적으로 차단(작성 중 실제로 경로 정규화 때문에 빈 결과가 나온 사례가 있어 가드 추가) |
| W5 | pre-commit fetch (L44) | `git fetch origin main` 후 `git rev-list --count --left-right origin/main...HEAD` → `0	0`(동기 상태, 병렬 세션 race 무) |

### §1.2 보존 대상 회귀 확인 (M7 — PRESERVE 10항목) [PASS]
M7 은 §1.2 보존 소유 파일 중 `BumpChart.tsx` · `RRGChart.tsx` 2개를 **tooltip formatter 의 결측 문자열 경로만** 수정했다(D2). `StockBubbleChart.tsx` · `MarketContext.tsx` · `StageDistributionBar.tsx` 는 **미수정**. 항목별 계약 grep 결과는 위 §1.2 실측 표 10행 전부 잔존이며, 특히 보존 3(색상 결정성 매핑)·4(`기타` 범례)·10(XSS 이스케이프)의 소유 파일 `StockBubbleChart.tsx` 는 `metricText` 미유입 0행으로 D2 범위 밖임을 확인했다. 보존 1(`connectNulls:false`)·2(날짜 합집합)·5(`focus:'series'`)는 수정한 2파일 안에서 그대로 잔존한다.

### 커밋 + push (Route A Hybrid Trunk) — M7 관심사별 3 commit
- `e5e057f` — M7 (1/3) 캐시 적중 경로의 전역 기준일 누락 수정 (F1) + F2 트레이드오프 주석 (2 files)
- `4eb5bd5` — M7 (2/3) 지표 텍스트 헬퍼 추출 — 표 셀 ↔ 차트 툴팁 문자열 통일 (D2) (5 files)
- `ccb9068` — M7 (3/3) 회귀 게이트 + 성능 실측 + run-phase close (5 files)
- `git show --stat` 3 commit 전수 확인 → `.agency/*` · `.claude/**` · `.moai/config|rules|project|state` migration mass · `frontend/coverage/` · `frontend/test-results/` · 루트 `*.txt` **미유입**(B8/B10 git-add discipline — 명시 경로만 staging).
- push: `6a941a6..ccb9068  main -> main`. 사후 `git rev-list --count --left-right origin/main...HEAD` → `0	0`.

## §E.3 Run-phase Audit-Ready Signal

> **run-phase 완료** — M1~M7 GREEN. M7(회귀 게이트 + 성능 측정 + F1 수정 + D2 해소)까지 포함한 전 구간 신호다.

```yaml
run_complete_at: 2026-08-14
run_commit_sha: ccb9068          # M7-3(최신). M7=e5e057f(F1/F2),4eb5bd5(D2),ccb9068(게이트+close). M1=c27a050 / M2=fc3dfc1 / M3=7975c7c / M4=dc4ad26,d28d505,cfdb87a / M5=597eaf0,62ade59,2e23dd2,e23d7a0,01120f3,1dba4b0 / M6=55720f2,c2f7e38,148b873.
run_status: complete             # M1~M7 GREEN. run-phase 전 구간 완료. 다음은 sync-phase.
ac_pass_count: 54                # 60 AC 중 PASS. M1-M6 누적 51 + M7 신규 판정 3(056 / 010 미판정분 / 052 debt→PASS) = 54. 052 는 M6 debt 에서 승격, 010 은 M1~M6 미기록분을 M7 에서 판정
ac_pass_with_debt_count: 6       # AC-SUX-018(M2) / 032(M4) / 042·046·060(M5) / 033(M6, 2026-08-14 사용자 결정으로 유지). M6 의 052 는 D2 로 해소되어 PASS 승격, 017 은 M5 에서 이미 PASS 로 재판정(M4 debt 행은 상위 기록에 보존)
ac_fail_count: 0
ac_total_this_segment: 60        # acceptance.md 실측 AC 61개 헤딩 중 057 은 결번(묘비) → 실 AC 60개. 54 PASS + 6 PASS-WITH-DEBT = 60, FAIL 0
ac_bookkeeping_note: "M7 착수 시 progress 기록 58 AC vs acceptance 60 AC 대사에서 AC-SUX-010(미판정)·AC-SUX-056(M7 대상) 2건 누락을 발견해 둘 다 M7 에서 판정했다. AC-SUX-017 은 M4 PASS-WITH-DEBT 행과 M5 PASS 행이 함께 남아 있으며 후행(M5) 판정이 유효하다."
preserve_list_post_run_count: 10 # §1.2 보존 10항목 전부 계약 유지. M7 은 BumpChart/RRGChart 의 tooltip 결측 문자열 경로만 수정했고 보존 계약 grep 10행 전부 잔존(§E.2 §1.2 실측 표)
l44_pre_commit_fetch: "synced — git fetch origin main 후 rev-list --left-right origin/main...HEAD → 0 0 (동기 상태, 병렬 세션 race 무)"
l44_post_push_fetch: "M7 3 commit push 후 git fetch origin main → rev-list --left-right origin/main...HEAD = 0 0 (6a941a6..ccb9068, 병렬 세션 개입 무)"
new_warnings_or_lints_introduced: 0   # 신규 eslint error class 0. 신규 인스턴스 +3(전부 기존 클래스 react-refresh/only-export-components — MetricCell 신규 export 3종; M6 baseline 42 → M7 45). 작성 중 발생한 신규 클래스 react-hooks/globals 4건 + immutability +3건은 테스트 재구성으로 전부 제거. tsc 수정파일 NEW 0
cross_platform_build:
  applicable: false              # 프론트엔드 전용 SPEC (Go 빌드 태그 / C-HRA-008 N/A)
tsc_gate_b_total: 28             # baseline 28 == 최종 28 (M7 비증가; 수정·신규 파일 NEW 0)
tsc_gate_a_ts2353: 0             # HARD 게이트 (a) 유지(M3 달성 후 불변)
modified_files_new_tsc_errors: 0
total_run_phase_files: 101       # M1(8)+M2(9)+M3(20)+M4(24)+M5(11)+M6(22)+M7(7: 신규 test 3 + 수정 4 = MetricCell/DataLoadContext/SectorBubbleChart/RRGChart/BumpChart/BubbleChart.m6.test/DataLoadContext.test, 중복 제외)
m1_to_mN_commit_strategy: per-concern  # M7 관심사별 커밋(F1+F2 / D2 / M7 게이트 / progress) + 각 conventional commit + 🗿 MoAI trailer
regression_tests: "655 pass (M6 종료 603 + M7 신규 52) / 2 e2e file-load baseline 불변 / 기존 603 전량 통과, 신규 회귀 0"
perf_measurement_status: "부분 실측 — 리렌더 범위(0/0) · 비활성 탭 fetch(0) · 500행 렌더(median 104.9ms) 실측 완료. '3열 추가 +20% 이내'와 INP/FCP/토글 P95 는 측정 불가로 §E.2 Gap 기록(수치 미생성)"
lesson9_mutation_count: 8        # 되돌림 RED 8건 관측 + 무효 변형 2건도 구분 기록. R3 는 최초 대조군이 항진명제였음을 변형으로 적발해 대조군을 정정한 뒤 RED 확보
next_checkpoint: "/moai sync SPEC-SECTOR-UX-001"
```

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_complete_at: 2026-08-14
sync_commit_sha: pending-backfill-sync   # 커밋 자신의 SHA는 커밋 시점에 알 수 없음 — 후속 커밋에서 backfill
changelog:
  status: added
  duplicate_guard_pre_count: 0           # grep -c 'SPEC-SECTOR-UX-001' CHANGELOG.md (작성 전)
  section: "### Added (SPEC-SECTOR-UX-001 v0.4.0, 2026-08-14)"
  placement: "[Unreleased] 최상단 — SPEC-SECTOR-AGGREGATION-001 v0.5.0 항목 바로 위"
readme:
  status: unchanged
  reason: "섹터 분석 화면은 README §2 Sector Analysis(SPEC-TOPDOWN-002 귀속)로 이미 개괄 서술됨. 형제 SPEC(SECTOR-GRID-001/SECTOR-AGGREGATION-001)도 동일 사유로 README 미등재 — 기존 관례 유지, 신규 사용자 표면 기능 없음(내부 상태모델·시각화 규약 리팩터)"
frontmatter_status_transitions:
  spec_md: "in-progress -> completed (updated: 2026-08-14 불변, 동일 날짜)"
  plan_md: "frontmatter 없음 — 전환 대상 아님"
  acceptance_md: "frontmatter 없음 — 전환 대상 아님"
  progress_md: "frontmatter 없음 — 전환 대상 아님"
mx_tag_validation:
  navintent_consume_guard: "PASS — frontend/src/contexts/TabContext.tsx:24 @MX:ANCHOR (TabProvider active-tab + NavIntent hub, fan_in>=5)"
  analysis_params_ownership: "PASS — frontend/src/contexts/AnalysisParamsContext.tsx:30 @MX:ANCHOR"
  bubble_size_mapping: "PASS — frontend/src/components/SectorAnalysis/bubbleRadius.ts:3 @MX:ANCHOR"
  stock_bubble_color_anchor_preserved: "PASS — frontend/src/components/SectorAnalysis/StockBubbleChart.tsx:37 @MX:ANCHOR (M5 미수정, §1.2 보존)"
  metric_cell_note: "PASS — frontend/src/components/common/MetricCell.tsx:4,57 @MX:NOTE + @MX:ANCHOR(metricDisplay)"
  axispointer_removed_note: "PASS — frontend/src/components/SectorAnalysis/SectorBubbleChart.tsx:150 @MX:NOTE (VZ-4 재도입 금지)"
  dataload_context_note: "PASS(추가 확인) — frontend/src/contexts/DataLoadContext.tsx:45 @MX:ANCHOR + :56 @MX:NOTE"
  missing: "없음 — plan.md mx_plan 6항목 전부 확인"
ac_tally_final:
  total: 60
  pass: 54
  pass_with_debt: 6
  fail: 0
  source: acceptance.md (SSOT)
```

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
