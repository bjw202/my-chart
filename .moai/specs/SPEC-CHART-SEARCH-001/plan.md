# SPEC-CHART-SEARCH-001 — Implementation Plan (v2.0.0)

문서 분류: Plan (manager-spec, Phase 1)
SPEC 버전: 2.0.0 (BREAKING amendment, Draft)
Development mode: TDD (RED → GREEN → REFACTOR)
작성일: 2026-05-11 (v1.0.0)
업데이트: 2026-05-12 (v2.0.0 BREAKING amendment — modal 폐기, ChartGrid 통합 패턴 도입)
연관 문서: `spec.md`, `acceptance.md`, `research.md`, `spec-compact.md`

## HISTORY

| 일자 | 변경 |
| --- | --- |
| 2026-05-11 | v1.0.0 초안 작성 (manager-spec) |
| 2026-05-11 | Amendment 1 — I-1~I-6 + Q-1~Q-7 smart defaults 반영. T2b(alias), T5a(focus trap) 추가. |
| 2026-05-12 | **v2.0.0 BREAKING amendment** — modal 패턴 폐기, ChartGrid 통합 주입 패턴 도입. 신규 task T9 (modal 자산 제거), T10 (stocks union 메커니즘), T11 (scroll + highlight), T12 (ChartGrid props 확장), T13 (integration tests). v1.0.0 T1~T4 (backend, hangul, hook, SearchBox)는 그대로 활용. T5~T8 (modal, integration, perf RED/GREEN)는 폐기 또는 재작성. |

---

## 1. Implementation Strategy (v2.0.0)

### 1.1 핵심 결정

| 결정 | v1.0.0 값 | v2.0.0 값 | 근거 |
| --- | --- | --- | --- |
| 검색 결과 표시 위치 | `ReactDOM.createPortal(modal, document.body)` portal | ChartGrid 표시 stocks 배열에 주입 (prepend 또는 기존 cell scroll) | 사용자 라이브 피드백 — modal 격리감이 mental model과 어긋남. ChartGrid UX 가치 활용 우선. |
| 검색 결과 ↔ 필터 결과 분리 | modal subtree (시각적 분리) | `displayedStocks` 배열 union, `screenState.request` deep-equal (논리적 분리) | filter state 보존 invariant 유지 (MP-3). ChartGrid stocks 배열은 derived state로 분리. |
| 중복 처리 | N/A (modal 재오픈) | scroll + highlight only (no prepend duplicate) | 사용자 결정 V2-Q2. |
| Highlight 스타일 | N/A | 셀 테두리 2~3초 CSS keyframes border-flash | 사용자 결정 V2-Q3. |
| 검색 종목 timeframe | modal 자체 토글 | ChartGrid 현재 timeframe 그대로 사용 (별도 토글 없음) | v2.0.0 EX-17. |
| 호스트 컴포넌트 | `AppContent.tsx` (modal sibling) | `AppContent.tsx` (`searchedStock` state → `injectedStock` prop forwarding) | search box → AppContent → ChartGrid prop drilling. |
| Development methodology | TDD | TDD (변경 없음) | `.moai/config/sections/quality.yaml`. |

### 1.2 외부 의존성 (변경 0)

NFR-CONST-001 강제: `package.json`, `requirements.txt` diff에서 신규 dependency 0건 확인.

Highlight CSS animation은 자체 keyframes로 구현 (no framer-motion, no react-spring 등).

### 1.3 archive 보존 정책

v1.0.0 modal 자산은 `feat/SPEC-CHART-SEARCH-001` 브랜치에 보존:
- `StockSearchModal.tsx`
- `useFocusTrap.ts`
- `StockSearchModal.test.tsx`
- `ChartGrid.perf.test.tsx` (modal-coupled scenarios)
- evaluator-active iter 2 PASS 84/100 평가 결과

본 SPEC v2.0.0은 새 브랜치 `feat/SPEC-CHART-SEARCH-001-v2`에서 작업. v3 후보(sidebar/route) 검토 시 archive 참고 가능.

---

## 2. File Change Matrix (v2.0.0)

### 2.1 Backend (변경 없음, v1.0.0 그대로)

| # | 파일 | Delta | 비고 |
| --- | --- | --- | --- |
| B1 | `backend/routers/stocks.py` | [EXISTING] | v1.0.0 그대로 |
| B2 | `backend/services/stocks_master_service.py` | [EXISTING] | v1.0.0 그대로 |
| B3 | `backend/main.py` | [EXISTING] | v1.0.0 그대로 |
| B4 | `backend/tests/test_stocks_master.py` | [EXISTING] | v1.0.0 그대로 |

### 2.2 Frontend Util (변경 없음, v1.0.0 그대로)

| # | 파일 | Delta | 비고 |
| --- | --- | --- | --- |
| F1 | `frontend/src/utils/hangul.ts` | [EXISTING] | v1.0.0 그대로 |
| F1b | `frontend/src/utils/hangul-aliases.ts` | [EXISTING] | v1.0.0 그대로 |
| F2 | `frontend/src/utils/__tests__/hangul.test.ts` | [EXISTING] | v1.0.0 그대로 |

### 2.3 Frontend API + Hook (변경 없음, v1.0.0 그대로)

| # | 파일 | Delta | 비고 |
| --- | --- | --- | --- |
| F3 | `frontend/src/api/stocks.ts` | [EXISTING] | v1.0.0 그대로 |
| F4 | `frontend/src/hooks/useStockMaster.ts` | [EXISTING] | v1.0.0 그대로 |
| F5 | `frontend/src/hooks/__tests__/useStockMaster.test.ts` | [EXISTING] | v1.0.0 그대로 |

### 2.4 Frontend Components — v2.0.0 변경

| # | 파일 | Delta | LOC | TDD Task | 매핑 REQ |
| --- | --- | --- | --- | --- | --- |
| F6 | `frontend/src/components/ChartGrid/StockSearchBox.tsx` | [EXISTING] | (재사용) | — | REQ-SEARCH-001~006 |
| F7 | `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` | [EXISTING] | (재사용) | — | AC-SEARCH-* |
| **F8** | `frontend/src/components/ChartGrid/StockSearchModal.tsx` | **[REMOVE]** | -250 | **T9** | (v1.0.0 폐기) |
| **F9** | `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx` | **[REMOVE]** | -180 | **T9** | (v1.0.0 폐기) |
| **F10** | `frontend/src/components/ChartGrid/useFocusTrap.ts` | **[REMOVE]** | -30 | **T9** | (modal 폐기로 불필요) |
| **F11** | `frontend/src/components/ChartGrid/ChartGrid.tsx` | **[MODIFY]** | +50 (props 확장 + scroll/highlight effect) | **T10, T11, T12** | REQ-INTEGRATE-001~003, REQ-PERF-001/002 |
| **F12** | `frontend/src/AppContent.tsx` | **[MODIFY]** | -15 (modal mount 제거) +10 (`injectedStock` prop 전달) = net -5 | **T9, T12** | REQ-INTEGRATE-001, REQ-INTEGRATE-004 |
| **F13** | `frontend/src/components/ChartGrid/cellHighlight.css` (or inline) | **[NEW]** | +30 (`@keyframes border-flash` + `.cell-search-highlight` class) | **T11** | REQ-INTEGRATE-002/003, §4 row 7 |
| **F14** | `frontend/src/components/ChartGrid/__tests__/ChartGrid.integration.test.tsx` | **[NEW]** | +250 (6+ scenarios) | **T13** | AC-INTEGRATE-001~006 |
| **F15** | `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` | **[MODIFY]** | modal-coupled 부분 제거 + integration-aware 시나리오 보강 | **T13** | MP-1/MP-2 검증 (재정의) |

### 2.5 합계 (v2.0.0)

- 제거: 3개 파일 (`StockSearchModal.tsx`, `StockSearchModal.test.tsx`, `useFocusTrap.ts`)
- 수정: 3개 파일 (`ChartGrid.tsx`, `AppContent.tsx`, `ChartGrid.perf.test.tsx`)
- 신규: 2개 파일 (`cellHighlight.css`, `ChartGrid.integration.test.tsx`)
- 외부 라이브러리 추가: 0

---

## 3. TDD Task Decomposition (T9 ~ T13, v2.0.0 신규)

> v1.0.0 T1~T4 (backend, hangul, hook, SearchBox)는 그대로 유지. T5~T8 (modal 관련)은 T9에서 일괄 제거.

### T9: v1.0.0 modal 자산 제거 + AppContent modal mount 코드 삭제

| 단계 | 작업 |
| --- | --- |
| RED (negative) | (선택) 기존 modal-coupled vitest가 v2.0.0 환경에서 fail함을 확인 후 제거. 또는 즉시 삭제. |
| GREEN | `StockSearchModal.tsx`, `useFocusTrap.ts`, `StockSearchModal.test.tsx` 파일 삭제. `AppContent.tsx`에서 `<StockSearchModal>` 마운트 코드 제거 (조건부 렌더 제거). `ChartGrid.perf.test.tsx` 내 modal-coupled 시나리오 (portal scope assertion 등) 제거. |
| REFACTOR | `AppContent.tsx`에 남은 `selectedStock` state는 일단 유지 (T12에서 `injectedStock` semantics로 재의미화). |
| Exit | `npm test` 통과 (modal 관련 테스트 제거 후 다른 테스트 영향 없음 확인). |
| 매핑 | (v1.0.0 모달 제거) |

### T10: ChartGrid `injectedStock` prop + stocks union 메커니즘 (REQ-INTEGRATE-001/003)

| 단계 | 작업 |
| --- | --- |
| RED | `ChartGrid.integration.test.tsx`에 작성: `<ChartGrid injectedStock={...} stocks={[A, B, C]} />` 마운트 → `displayedStocks` 검증. case A — `injectedStock.code`가 stocks에 없음 → `displayedStocks = [injectedStock, A, B, C]`. case B — `injectedStock.code`가 stocks에 있음 → `displayedStocks = stocks` (prepend 안 함, scroll은 T11). case C — `injectedStock === null` → `displayedStocks = stocks`. `data-testid="chart-cell-injected-{code}"`가 prepend 시 첫 cell에 부여됨. |
| GREEN | `ChartGrid.tsx` props 인터페이스에 `injectedStock?: StockMasterItem \| null` 추가. ChartGrid 내부에서 `displayedStocks` 계산: `useMemo(() => injectedStock && !stocks.find(s => s.code === injectedStock.code) ? [injectedStock, ...stocks] : stocks, [injectedStock, stocks])`. cell render 시 첫 cell이 `injectedStock`이면 `data-testid="chart-cell-injected-{code}"` 부여. 기존 cell key (`stock.code`)는 그대로 유지 → React reconciliation이 기존 cells 재사용. |
| REFACTOR | useMemo dependency 최소화. injectedStock 비교는 code 기반만 (전체 object compare 불필요). |
| Exit | RED 시나리오 6개 PASS. `useScreen().screenState.request`는 어디서도 mutate되지 않음 검증 (deep-equal). |
| 매핑 | REQ-INTEGRATE-001/003, AC-INTEGRATE-001 |

### T11: 자동 scroll + highlight CSS animation (REQ-INTEGRATE-002/003)

| 단계 | 작업 |
| --- | --- |
| RED | `ChartGrid.integration.test.tsx`에 작성: case A — `injectedStock` 변경 (existing in stocks) → ChartGrid의 `setCurrentPage`가 해당 stock의 page index로 호출됨 (mock spy). case B — `injectedStock` 변경 (not in stocks, prepend) → 첫 cell outer container에 `cell-search-highlight` class 추가됨. case C — 2~3초 후 `cell-search-highlight` class가 자동 제거됨 (vitest `vi.useFakeTimers` + advance 3000 ms). case D — useEffect cleanup 시 `clearTimeout` 호출 (unmount during animation 검증). |
| GREEN | (1) `ChartGrid.tsx`에 `useEffect(() => { ... }, [injectedStock])` 추가: `injectedStock`이 변경되면 (a) `stocks.findIndex(s => s.code === injectedStock.code)` 또는 `displayedStocks.findIndex(...)`로 target index 계산 (b) `setCurrentPage(Math.floor(targetIndex / pageSize))` 호출 (c) ref로 target cell outer container element 찾고 `classList.add('cell-search-highlight')` (d) `setTimeout` 등록 + cleanup에 `clearTimeout`. (2) `cellHighlight.css` (또는 inline `<style>`)에 `@keyframes border-flash` 정의 (blue glow, 2.5s duration) + `.cell-search-highlight { animation: border-flash 2.5s ease-in-out; }`. |
| REFACTOR | css 파일 vs inline style 결정 — 프로젝트 컨벤션에 맞춰 정함. setTimeout duration은 2500ms로 고정 (사용자 결정 "2~3초"). animation iteration 3회 (≈ 833ms each) 또는 single 2.5s에 ease-in-out — 시각적으로 매력적인 쪽으로. |
| Exit | RED 시나리오 4개 PASS. highlight class가 정확히 2.5s 후 제거됨. |
| 매핑 | REQ-INTEGRATE-002/003, AC-INTEGRATE-002, AC-INTEGRATE-004 |

### T12: ChartGrid props 확장 + AppContent prop forwarding

| 단계 | 작업 |
| --- | --- |
| RED | `ChartGrid.integration.test.tsx`에 작성: `<AppContent />` 통합 마운트 → search → ChartGrid `injectedStock` prop 수신 검증. `useScreen().screenState.request` 객체 reference가 검색 전후 동일 (vitest `expect(reqBefore).toBe(reqAfter)` 또는 deep-equal). React.memo가 ChartGrid에 적용되어 있어 다른 prop 변경 시 ChartGrid 재렌더 차단 검증 (React Profiler API). |
| GREEN | (1) `AppContent.tsx`: 기존 `selectedStock` state를 `searchedStock`으로 rename (또는 그대로 유지). `<ChartGrid onSelectStock={(stock) => setSearchedStock(stock)} injectedStock={searchedStock} ... />`. `<StockSearchModal>` 마운트 코드는 T9에서 이미 제거됨. (2) `ChartGrid.tsx`: props 인터페이스에 `injectedStock?: StockMasterItem \| null` 추가. React.memo는 v1.0.0에서 이미 적용되어 있으므로 유지. `onSelectStock` prop은 `useCallback`으로 안정화 (AppContent에서). |
| REFACTOR | `searchedStock` state는 검색 후 명시적으로 reset할 필요 없음 (다음 검색이 자연스럽게 대체). 단, ChartGrid filter 변경 시 `searchedStock`을 자동 reset할지 여부는 향후 결정 — v2.0.0 기본은 reset하지 않음 (사용자가 명시적으로 새 검색하기 전까지 첫 cell 유지). |
| Exit | RED 시나리오 PASS. `useScreen.request` deep-equal 보존 검증 PASS. |
| 매핑 | REQ-INTEGRATE-001/004, AC-INTEGRATE-003 |

### T13: Integration tests + anti-regression performance tests

| 단계 | 작업 |
| --- | --- |
| RED | `ChartGrid.integration.test.tsx`에 6+ 통합 시나리오 작성: (1) 필터 결과에 없는 종목 검색 → prepend + highlight, (2) 필터 결과에 있는 종목 검색 → scroll + highlight, prepend 0, (3) 검색 후 `useScreen().request` deep-equal, (4) 검색 후 ChartGrid React.memo re-render count baseline 대비 +0~1, (5) 검색 후 기존 ChartCells의 useEffect 재실행 0 (cell key 동일성 검증 — instance reuse 확인), (6) highlight CSS class 2.5s 후 자동 제거. `ChartGrid.perf.test.tsx`의 modal-coupled 시나리오 제거 + integration-aware 시나리오로 재작성. |
| GREEN | T10~T12 GREEN에서 이미 구현된 코드로 PASS 되어야 함. 실패 시 fix. ChartCell instance reuse 검증은 `ChartCell` mock spy에 cell key tracking 추가 — 동일 key의 cell은 effect 재호출 안 됨. |
| REFACTOR | StrictMode dev에서 새로 prepend된 cell의 useEffect 2회 호출 케이스 명시적 허용 — instrumentation 분기. 기존 cells에 대해서는 0회 strict (cell key 동일성으로 보장됨). |
| Exit | 6+ 통합 시나리오 PASS + 기존 vitest 전체 PASS (modal 관련 제거 후). |
| 매핑 | REQ-INTEGRATE-001~004, REQ-PERF-001/002, MP-1, MP-2, MP-3, MP-4 |

### 3.1 Task 순서 그래프 (v2.0.0)

```
v1.0.0 그대로 유지: T1 (backend), T2 (hangul), T2b (alias), T3 (hook), T4 (SearchBox)
v1.0.0 폐기: T5 (modal), T5a (focus trap), T7 (perf RED modal), T8 (perf GREEN modal)
v2.0.0 신규:
  T9 (modal 자산 제거) ─→ T10 (stocks union) ─→ T11 (scroll + highlight) ─→ T12 (props 확장) ─→ T13 (integration tests)
```

- T9는 다른 task와 독립적으로 먼저 수행 (cleanup).
- T10은 T9 이후 (stocks union 메커니즘 구현).
- T11은 T10 이후 (scroll + highlight, cell ref 필요).
- T12는 T10/T11과 병렬 가능하지만 순차 권장.
- T13은 T10/T11/T12 모두 이후.

---

## 4. MX Tag Plan (v2.0.0)

| 파일 | 태그 | 사유 |
| --- | --- | --- |
| `frontend/src/components/ChartGrid/StockSearchBox.tsx` | `@MX:ANCHOR` (유지) | ChartGrid 검색 진입점. fan_in ≥ 3 예상 (ChartGrid + 향후 다른 곳). public prop 인터페이스(`onSelect`). |
| `frontend/src/utils/hangul.ts` | `@MX:NOTE` (유지) | 한글 초성 산식 + 5단계 score 매칭 비즈니스 로직. |
| `frontend/src/utils/hangul-aliases.ts` | `@MX:NOTE` (유지) | 50종 영문 alias 사전. |
| `frontend/src/components/ChartGrid/StockSearchModal.tsx` | DELETED | v2.0.0에서 파일 제거. v1.0.0 @MX:NOTE + @MX:WARN race guard 태그는 함께 사라짐. |
| `frontend/src/components/ChartGrid/useFocusTrap.ts` | DELETED | v2.0.0에서 파일 제거. |
| `frontend/src/components/ChartGrid/ChartGrid.tsx` | `@MX:ANCHOR` (강화) | fan_in ≥ 3 (AppContent + 다른 호스트들). `injectedStock` prop + scroll/highlight effect 추가로 invariant 강화. |
| `frontend/src/AppContent.tsx` | `@MX:NOTE` | `searchedStock` state lift + ChartGrid prop forwarding 패턴 기록. |
| `frontend/src/components/ChartGrid/cellHighlight.css` | (CSS 파일은 @MX 미적용) | — |

---

## 5. Reference Implementations (v2.0.0)

run phase에서 다음 패턴을 참조:

| 패턴 | 참조 위치 | 사용 시 |
| --- | --- | --- |
| React.memo with custom areEqual | `frontend/src/components/ChartGrid/ChartGrid.tsx` (v1.0.0 commit 5ca5335) | T12 ChartGrid 재렌더 차단 |
| `useCallback` for stable handler | `frontend/src/components/ChartGrid/ChartGrid.tsx:56` (`handlePageChange`) | T12 `onSelectStock`, AppContent에서 전달 |
| `useMemo` for derived state | (project-wide 패턴) | T10 `displayedStocks` 계산 |
| ChartGrid `setCurrentPage` + page index 계산 | 기존 ChartGrid 페이징 로직 | T11 자동 scroll |
| CSS keyframes border animation | (general web pattern — research에서 발견된 일반 패턴, 라이브러리 불필요) | T11 `@keyframes border-flash` |
| `ReactDOM.createPortal` race guard (cancelled flag) | archive `feat/SPEC-CHART-NAV-001` commit `df3ca36` | v2에서는 modal 없으므로 직접 사용 안 하지만, ChartCell의 race guard 패턴 참조용 |
| `read-only sqlite URI` | `backend/services/stocks_master_service.py` (v1.0.0) | T1 (v1.0.0 그대로 유지) |

---

## 6. Risks + Mitigation (v2.0.0)

| Risk | 출처 | Mitigation 위치 | Severity |
| --- | --- | --- | --- |
| ~~R-1 (modal subtree leak)~~ | — | (modal 폐기로 불필요) | — |
| R-2 (재정의): ChartGrid re-render | research §4.3 잔여 위험 | **`React.memo(ChartGrid)`로 referential equality 보존** — AppContent의 `searchedStock` state 변경이 ChartGrid에 prop으로 전달될 때 cascade 1회 발생은 의도된 동작 (highlight 위해 필요). 다른 props 변경 시 cascade 차단. 기존 cells의 useEffect 재실행 0회는 cell key 동일성으로 보장 (React reconciliation). MP-1 honest threshold +1 ≤ 2 허용. | High |
| R-3 (재정의): highlight CSS animation 중단/cleanup | v2.0.0 신규 | useEffect cleanup으로 `classList.remove('cell-search-highlight')` + `setTimeout` clearTimeout 보장. unmount during animation 시에도 메모리 누수 0. animation 중 새 검색 발생 시 이전 highlight class 즉시 제거 → 새 cell에 적용. T11 RED scenario D로 검증. | Medium |
| R-4 (신규): page index 계산 edge case | v2.0.0 신규 | 검색 종목이 마지막 페이지의 마지막 셀일 때, stocks가 0개일 때, pageSize가 변경될 때 등. T11 GREEN에서 boundary check 필수 — `targetIndex < 0` 처리, `pageSize === 0` 처리. | Medium |
| R-5 (신규): prepend duplicate detection | v2.0.0 신규 | code 기반 비교 (`stocks.find(s => s.code === injectedStock.code)`)가 충분. code는 unique invariant. T10 case B로 검증. | Low |
| R-6 (재정의): React reconciliation 미보장 | v2.0.0 신규 | cell key가 `stock.code`로 안정하면 React가 동일 key의 instance를 재사용. prepend 시 새 key 추가일 뿐 기존 keys 동일성 보존. 단, key prop을 잊거나 index를 key로 쓰면 R-6 발생. T13 case 5에서 instance reuse 검증 (ChartCell mock spy with cell key tracking). | High |
| R-7 (재정의): archive cherry-pick 부담 | v1.0.0 유지 | v2.0.0은 v1.0.0의 backend + hangul + hook + SearchBox 자산을 그대로 활용. archive cherry-pick 추가 작업 없음. | Low |
| R-8 (재정의): 검색 동선이 filter state mutate | research §4.3 | **MP-4 강화**: `AppContent.tsx`, `ChartGrid.tsx`, `StockSearchBox.tsx`에서 `useScreen()` setter 또는 `applyFilters()` 호출이 검색 동선에서 발생하지 않음을 정적 grep으로 검증. AC-ARCH-001. | Critical |
| R-9 (재정의): cachedPromise 무효화 | v1.0.0 유지 | EX-12로 scope 외. | Medium |
| R-10 (v2 신규): 사용자 mental model drift 재발 | v2.0.0 신규 | lesson #7 lock-in. ship 후 2주 사용자 검증 (§2.4 폐기 기준). 만약 v2도 drift 발생 시 v3 후보(sidebar/route) 별도 SPEC 검토. | High |

---

## 7. Verification Strategy

### 7.1 Unit (Vitest + pytest)

- Backend: `pytest backend/tests/test_stocks_master.py` (v1.0.0 그대로, 8 PASS)
- Frontend hangul: `npm test -- hangul` (v1.0.0 그대로)
- Frontend hook: `npm test -- useStockMaster` (v1.0.0 그대로)
- Frontend SearchBox: `npm test -- StockSearchBox` (v1.0.0 그대로)

### 7.2 Integration (vitest, JSDOM, v2.0.0 신규)

- `ChartGrid.integration.test.tsx` — 6+ 시나리오 (T13):
  1. 필터 결과에 없는 종목 검색 → prepend + highlight
  2. 필터 결과에 있는 종목 검색 → scroll + highlight, prepend 0
  3. 검색 후 `useScreen().request` deep-equal
  4. 검색 후 ChartGrid React.memo re-render count baseline +0~1
  5. 검색 후 기존 ChartCells useEffect 재실행 0 (cell key 동일성)
  6. highlight CSS class 2.5s 후 자동 제거

### 7.3 Manual / e2e (optional Playwright)

- 시나리오 1: 검색 → 선택 → ChartGrid 첫 셀 prepend → highlight 깜박임 종료
- 시나리오 2: 검색 → 선택 (필터에 있음) → scroll to page + highlight
- 시나리오 3: 503 응답 시 input disabled + tooltip
- 시나리오 4: ChartGrid scroll FPS 측정 (DevTools Performance)

### 7.4 라이브 검증 (ship 후 2주, lesson #7 lock-in)

- §2.3 만족 신호 측정 (성공-1, 성공-2, 성공-3, 성공-5)
- §2.4 폐기 기준 위반 시 v3 후보 별도 SPEC 검토 (sidebar/route)
- **mental model drift 재발 여부 확인** — 사용자 피드백 1주 추적

### 7.5 v2.0.0 폐기 기준 명시 (lesson #7)

| 조건 | 임계값 | 액션 |
| --- | --- | --- |
| 사용자 세션당 검색 횟수 | < 1.0회 (2주 평균) | v3 후보 별도 SPEC 검토 |
| 검색 → ChartGrid 표시 latency | > 1000 ms | 성능 회귀 분석, fix 또는 폐기 |
| MP-1 ~ MP-5 invariant 위반 | 1건 이상 | 즉시 hotfix |
| 사용자 mental model drift 신호 | 명시적 "이것도 원하는 게 아님" 피드백 | v3 후보 별도 SPEC |

---

## 8. Rollback Strategy (v2.0.0)

본 SPEC v2.0.0 ship 후 폐기 결정 시:

1. 새 git branch `feat/SPEC-CHART-SEARCH-001-v2` archive 보존 (commits 그대로).
2. **v1.0.0 modal 패턴 부활은 NO** — 이미 사용자가 거부함.
3. v3.0.0 후보 패턴:
   - **Option A**: Sidebar fixed panel (검색 종목 차트를 ChartGrid 우측 사이드바에 고정 표시)
   - **Option B**: 별도 route (`/chart/:code` 페이지로 navigation)
   - **Option C**: 기능 자체 폐기 (Search 자체가 가치 없다는 결론 시)
4. v3 후보는 별도 SPEC으로 분리. `.moai/specs/SPEC-CHART-SEARCH-002/`로 신규 작성.
5. `retrospective.md` v2.0.0 신규 작성. lesson #7 강화 사례 #2로 추가 (NAV-001 rollback + v1.0.0 closure + v2.0.0 폐기 = 3-stage mental model drift).
6. `lessons.md` lesson #7 강화 — "modal 격리도 아니고 stocks union도 아니라면 v3 후보 카탈로그 + 사전 사용자 검증 의무" 추가.

archive 활용: v2.0.0 stocks union 패턴이 다른 SPEC에서 재호출 가능.

---

## 9. Acceptance Gate (manager-quality 위임)

T9 ~ T13 완료 후 다음을 manager-quality 또는 evaluator-active에 위임:

- [ ] TRUST 5 Tested: 85% 이상 coverage (신규/수정 코드 한정)
- [ ] TRUST 5 Readable: ruff / eslint clean
- [ ] TRUST 5 Unified: black / prettier 통과
- [ ] TRUST 5 Secured: SELECT-only (REQ-DATA-002) 강제 유지, bare except 0
- [ ] TRUST 5 Trackable: conventional commit + SPEC ID 참조 (`SPEC-CHART-SEARCH-001 v2.0.0`)
- [ ] MP-1 ~ MP-5 must-pass 검증 (v2.0.0 재정의 기준 적용)
- [ ] NFR-PERF-001 ~ 005 측정 결과 acceptance.md에 기록
- [ ] modal 자산 파일 3개 (`StockSearchModal.tsx`, `StockSearchModal.test.tsx`, `useFocusTrap.ts`) 제거 확인
- [ ] `ChartGrid.integration.test.tsx` 6+ 시나리오 모두 PASS

---

## 10. Decisions Resolved (v2.0.0 annotation cycle)

`spec.md §9 v2.0 Decisions` 표 참조. V2-Q1 ~ V2-Q6 6건 모두 사용자 명시 결정 완료. 추가 annotation cycle 불필요.

| Q | 결정 | plan.md 반영 위치 |
| --- | --- | --- |
| V2-Q1 | 검색 결과 표시 위치 = ChartGrid 첫 셀 prepend | T10, T12 |
| V2-Q2 | 중복 처리 = scroll + highlight only | T11 |
| V2-Q3 | Highlight 스타일 = 셀 테두리 2~3초 깜박임 | T11, F13 (cellHighlight.css) |
| V2-Q4 | modal 패턴 폐기 | T9 (제거) |
| V2-Q5 | 검색 종목 timeframe = ChartGrid 현재 timeframe 그대로 (별도 토글 없음) | EX-17, T11에서 timeframe 토글 코드 미작성 |
| V2-Q6 | 검색 종목 차트 닫기 동선 없음 | EX-18, T12에서 close handler 미작성 |

---

Version: 2.0.0
Last Updated: 2026-05-12
