# SPEC-CHART-SEARCH-001 — Acceptance Criteria (v2.0.0)

문서 분류: Acceptance (TDD scenarios)
SPEC 버전: 2.0.0 (BREAKING amendment, Draft)
Development methodology: TDD
작성일: 2026-05-11 (v1.0.0)
업데이트: 2026-05-12 (v2.0.0 BREAKING amendment — modal AC 8건 제거, integration AC 6건 신규)
연관 문서: `spec.md`, `plan.md`, `research.md`, `spec-compact.md`

## HISTORY

| 일자 | 변경 |
| --- | --- |
| 2026-05-11 | v1.0.0 초안 작성 |
| 2026-05-11 | Amendment 1 — 신규 AC 3건 추가 (AC-SEARCH-011 / AC-SEARCH-012 / AC-MODAL-009). I-3 적용. |
| 2026-05-12 | **v2.0.0 BREAKING amendment** — modal AC 8건 (AC-MODAL-001~008, AC-MODAL-009)와 모달 종속 AC (AC-SEARCH-003 modal 부분, AC-SEARCH-012 modal close 부분) 제거. AC-INTEGRATE-001~006 신규 6건. AC-PERF-001~004 + AC-ARCH-001~003 재정의. Must-pass 15개 재정의. |
| 2026-05-12 | v2.0.0 (audit iter 1 minor improvements) — I-7 AC-INTEGRATE-001에 `setCurrentPage(0)` reset 동작 추가 (currentPage > 0 조건부, EARS-style IF/THEN/ELSE). I-2 AC-INTEGRATE-005 시나리오를 현실 cascade source 3종 (FilterBar typing / currentPage 변경 / `injectedStock` 변경)으로 교체 + 실패 path 흔한 원인 명시 (`useScreen()` 직접 호출 / inline new reference). |

---

## Conventions

- 모든 시나리오는 **Given / When / Then** 형식.
- `must-pass` 표기는 다른 기준으로 보상 불가.
- `data-testid` 값은 `spec.md §4 UI Element Mapping`과 1:1 일치.
- 각 시나리오는 unit (vitest/pytest) 또는 integration 단위에서 자동화 가능해야 한다.

---

## 1. Module: Stocks Master Data Endpoint (REQ-DATA-001 ~ 003) — v1.0.0 유지

### AC-DATA-001 (must-pass) — 정상 200 응답 + 정렬 + 헤더

REQ 매핑: REQ-DATA-001, REQ-DATA-002

v1.0.0 그대로 (변경 없음). 자세한 내용은 v1.0.0 acceptance.md 참조 또는 backend test 코드 확인.

**Given** — 임시 SQLite DB에 `stock_meta(code, name, market, last_updated)` 테이블 + 3 row (name NULL 1건 포함).

**When** — `GET /api/stocks/master` 호출.

**Then** — HTTP 200, body schema 일치, length === 2, name ascending 정렬, ETag + Cache-Control 헤더.

---

### AC-DATA-002 (must-pass) — stock_meta 빈 테이블 → 503

REQ 매핑: REQ-DATA-003. v1.0.0 그대로.

---

### AC-DATA-003 (must-pass) — stock_meta 테이블 부재 → 503

REQ 매핑: REQ-DATA-003. v1.0.0 그대로.

---

### AC-DATA-004 (must-pass) — SELECT-only invariant

REQ 매핑: REQ-DATA-002, NFR-CONST-002. v1.0.0 그대로.

---

## 2. Module: Hangul Matching Utility (REQ-SEARCH-003) — v1.0.0 유지

### AC-SEARCH-005 — 초성 추출 정확성

REQ 매핑: REQ-SEARCH-003 (score 1). v1.0.0 그대로.

---

### AC-SEARCH-006 — `matchesQuery` 5단계 score + 동점 tiebreaker

REQ 매핑: REQ-SEARCH-003. v1.0.0 그대로 (alias score 5 포함).

---

### AC-SEARCH-011 — 영문 alias 매칭 (Q-1 v1.0.0)

REQ 매핑: REQ-SEARCH-003 (score 5). v1.0.0 그대로.

---

## 3. Module: `useStockMaster` Hook (REQ-SEARCH-002, 006) — v1.0.0 유지

### AC-SEARCH-002 (must-pass) — SPA 세션 1회 fetch + cachedPromise

REQ 매핑: REQ-SEARCH-002. v1.0.0 그대로.

---

### AC-SEARCH-007 — 503 응답 시 `error: stock_meta_not_ready` 노출

REQ 매핑: REQ-SEARCH-002, REQ-SEARCH-006. v1.0.0 그대로.

---

## 4. Module: `StockSearchBox` Component (REQ-SEARCH-001 ~ 006) — v1.0.0 유지 (단, AC-SEARCH-012 재정의)

### AC-SEARCH-001 — 정상 시나리오: 한글 입력 → prefix 매치

REQ 매핑: REQ-SEARCH-001, 003. v1.0.0 그대로.

---

### AC-SEARCH-003 (v2 재정의) — 필터 우회: 필터 밖 종목 검색 → ChartGrid 첫 셀 prepend + highlight

REQ 매핑: REQ-SEARCH-001 + REQ-INTEGRATE-003 + MP-3 (필터 상태 보존)

**Given**
- ChartGrid가 시가총액 ≥ 1조원 필터 적용 상태 (`screenState.request.market_cap_min === 1_000_000_000_000`).
- 검색 대상 종목 `123456` (가상, 시총 100억 소형주)는 현재 필터 결과에 **불포함**.
- 검색 전 ChartGrid의 `displayedStocks = [...filterResults]` (예: 시총 1조 이상 25개).

**When**
- 사용자가 `chart-search-input`에 `123456` 입력 → debounce 경과 → `chart-search-option-123456` 클릭.

**Then**
- ChartGrid의 `displayedStocks[0] === { code: '123456', ... }` (prepend 됨).
- 첫 cell에 `data-testid="chart-cell-injected-123456"` 부여됨.
- 첫 cell outer container에 `cell-search-highlight` CSS class 적용됨.
- 기존 25개 cells는 그대로 displayedStocks[1..25]에 유지.
- `useScreen().screenState.request` 객체가 검색 전후 deep-equal (MP-3).
- 필터 outside 종목임에도 ChartGrid 내부에서 차트 표시 가능 (필터 우회 동선 성공).

**Edge case**
- 검색 후 ChartGrid 필터는 여전히 동일 상태.
- 2.5초 후 `cell-search-highlight` class 자동 제거.

---

### AC-SEARCH-004 — 초성 검색

REQ 매핑: REQ-SEARCH-003 (score 1). v1.0.0 그대로.

---

### AC-SEARCH-008 — 0건 결과 처리

REQ 매핑: REQ-SEARCH-004. v1.0.0 그대로.

---

### AC-SEARCH-009 — 503 disabled 상태

REQ 매핑: REQ-SEARCH-006. v1.0.0 그대로.

---

### AC-SEARCH-010 — 키보드 navigation

REQ 매핑: REQ-SEARCH-005. v1.0.0 그대로.

---

### AC-SEARCH-012 (v2 재정의) — 검색 후 input 상태 (modal close 부분 제거)

REQ 매핑: REQ-SEARCH-005 (Escape 거동)

**Given**
- 사용자가 `chart-search-input`에 `삼` 입력 → `chart-search-option-005930` 클릭 → ChartGrid 첫 셀에 prepend + highlight.

**When (case A — 사용자가 Escape 키 입력)**
- listbox 닫기 + input clear.

**Then (case A)**
- `chart-search-input` value === `''`.
- listbox 닫힌 상태.
- ChartGrid의 `displayedStocks[0]`은 여전히 검색 종목 (Escape는 search input만 reset, ChartGrid stocks는 유지).

**When (case B — 사용자가 새 검색어 입력)**
- 새 후보 listbox 노출.

**Then (case B)**
- 정상 동작. 이전 검색의 ChartGrid prepend는 여전히 유지 (다음 검색 선택 시 대체).

**Edge case**
- 검색 후 modal close 동선은 v2.0.0에서 제거됨 (modal 자체가 없음).

---

## 5. Module: ChartGrid Integration Injection (REQ-INTEGRATE-001 ~ 004) — v2.0.0 신규

> v1.0.0 AC-MODAL-001 ~ AC-MODAL-009는 모두 v2.0.0에서 제거됨 (modal 폐기).

### AC-INTEGRATE-001 (must-pass) — 필터 결과에 없는 종목 검색 → ChartGrid 첫 셀 prepend + page 0 reset (I-7)

REQ 매핑: REQ-INTEGRATE-001/003

**Given**
- ChartGrid 마운트, `stocks = [{code: 'A'}, ... 총 50개]` (filter 결과, `pageSize = 12` → 5 pages).
- AppContent state `searchedStock = null`.
- ChartGrid `setCurrentPage` spy 등록.

**When (case A — ChartGrid currentPage > 0 at injection time)**
- 사용자가 ChartGrid 3번째 페이지로 navigation (currentPage = 2).
- 사용자가 `chart-search-input`에 검색 → `chart-search-option-D` 클릭.
- AppContent `searchedStock = {code: 'D', ...}` set → ChartGrid에 `injectedStock={code: 'D'}` prop 전달.

**Then (case A)**
- ChartGrid의 `displayedStocks = [{code: 'D'}, {code: 'A'}, ... 총 51개]` (prepend, length=51).
- 첫 cell DOM에 `data-testid="chart-cell-injected-D"` 부여됨.
- `stocks` (filter results)는 그대로 unchanged.
- React reconciliation: 기존 cells (A/B/C/...)는 동일 cell instance 재사용 (key 동일성).
- **`setCurrentPage(0)` spy 1회 호출됨** — prepend 후 ChartGrid는 page index 0으로 reset되어 사용자에게 injected cell이 즉시 보임.
- ChartGrid의 page indicator (`data-testid="chart-grid-current-page"` 또는 동등 indicator) 컨텐츠가 "1 / 5" (또는 "1 / N+1") 표시.

**When (case B — ChartGrid currentPage === 0 at injection time)**
- 사용자가 첫 페이지에서 검색 → `chart-search-option-D` 클릭.

**Then (case B)**
- prepend 정상 동작 (case A의 `displayedStocks` 변경 부분과 동일).
- **`setCurrentPage` spy 호출 0회** — 이미 page 0이므로 reset 불필요.
- 단, ChartGrid가 currentPage check 없이 항상 `setCurrentPage(0)`을 호출하는 idempotent 구현도 허용 (React가 동일 값일 때 추가 commit 차단).
- 조건부 명세 (EARS-style): **IF** `currentPage > 0` at injection time, **THEN** ChartGrid **SHALL** `setCurrentPage(0)`. **ELSE** no page change required.

**Edge case**
- `injectedStock = null` 다시 set 시 prepend 되돌아감 (`displayedStocks = stocks` 복귀). currentPage는 reset되지 않고 사용자의 마지막 page를 유지.
- stocks가 0개일 때 (`displayedStocks = [injectedStock]`) currentPage=0 자동 보장.

---

### AC-INTEGRATE-002 (must-pass) — 필터 결과에 있는 종목 검색 → scroll + highlight, prepend 0

REQ 매핑: REQ-INTEGRATE-002

**Given**
- ChartGrid 마운트, `stocks = 100개`, `pageSize = 12` → 8.3 pages, 현재 `currentPage = 0` (첫 페이지).
- 검색 대상 stock `{code: 'X'}`는 `stocks[50]`에 존재 (4번째 페이지).
- ChartGrid setCurrentPage spy 등록.

**When**
- 사용자가 검색 → `chart-search-option-X` 클릭 → `injectedStock = {code: 'X'}` prop 전달.

**Then**
- `displayedStocks.length === 100` (prepend 없음, no duplicate).
- `displayedStocks === stocks` (배열 그대로).
- `setCurrentPage(4)` 호출 (page index = floor(50 / 12) = 4).
- `cell-search-highlight` CSS class가 stock X의 cell outer container에 적용됨.
- `data-testid="chart-cell-injected-X"`는 stock X의 기존 cell에 부여됨 (prepend cell이 아님).

**Edge case**
- 2.5초 후 highlight class 자동 제거.
- stock X가 마지막 페이지의 마지막 셀일 때도 정상 동작.

---

### AC-INTEGRATE-003 (must-pass MP-3) — ScreenContext.request deep-equal 보존

REQ 매핑: REQ-INTEGRATE-004, MP-3

**Given**
- `useScreen().screenState.request` 객체 snapshot 보관 (deep clone): 예 `{market_cap_min: 1e12, change_rate_min: 5.0, ...}`.

**When (sequence of search injections)**
- 검색 1: 필터 결과에 없는 종목 prepend → highlight.
- 검색 2: 필터 결과에 있는 종목 scroll + highlight.
- 검색 3: `searchedStock = null` reset.

**Then**
- 각 검색 후 `useScreen().screenState.request`가 snapshot과 deep-equal.
- 필터 객체의 어떤 field도 mutate되지 않음 (`market_cap_min`, `change_rate_min/max`, `rs_min/max`, `sector`, `codes` 등).

**검증 방법**
- vitest `expect(currentReq).toEqual(snapshotReq)` (deep-equal).
- Optionally: `expect(currentReq).toBe(snapshotReq)` (referential equality, ScreenContext는 새 객체 생성 안 함을 강제).

---

### AC-INTEGRATE-004 — Highlight CSS class 적용 + 자동 제거

REQ 매핑: REQ-INTEGRATE-002/003

**Given**
- ChartGrid 마운트, `vi.useFakeTimers()` 활성.
- 검색 종목 prepend 또는 scroll 발생 직전.

**When**
- `injectedStock` prop 변경.
- `vi.advanceTimersByTime(0)` (초기 effect run).
- `vi.advanceTimersByTime(2400)` (animation 진행 중).
- `vi.advanceTimersByTime(200)` (총 2600 ms 경과).

**Then**
- t=0 직후: 대상 cell outer container에 `cell-search-highlight` class 존재.
- t=2400 ms: class 여전히 존재.
- t=2600 ms: class 자동 제거됨.
- CSS animation은 ~2.5s duration (border-flash keyframes).

**Edge case**
- Animation 중 새 검색 발생: 이전 cell의 highlight class 즉시 제거 → 새 cell에 class 적용 (clearTimeout + 새 setTimeout).
- Component unmount during animation: cleanup에서 classList.remove + clearTimeout 호출.

---

### AC-INTEGRATE-005 (must-pass MP-1) — ChartGrid React.memo re-render count (I-2 현실 시나리오)

REQ 매핑: REQ-PERF-001, MP-1

**Given**
- React Profiler API로 ChartGrid commit count 측정 wrapper.
- ChartGrid + AppContent 마운트 → 초기 baseline commit count 기록 (예: 3회).
- AppContent 구조 전제: `useScreen()` 호출은 AppContent에서만 발생, `filterResults`는 ChartGrid에 prop으로 전달.

**When (sequence — I-2 현실 cascade source 3종)**

**(a) FilterBar input typing (compose 중, submit 전)** — 예: 사용자가 `market_cap_min` input에 `1000000000` 타이핑.
- FilterBar local state만 변경됨 (submit 전이므로 ScreenContext.request는 그대로).
- ChartGrid에 전달되는 `filterResults` prop reference 동일.

**(b) ChartGrid `currentPage` prop 변경 (페이지 navigation 클릭)** — 예: 사용자가 페이지 2로 이동.
- ChartGrid 자체 의도된 동작 — `currentPage` prop 변경은 ChartGrid render trigger (React.memo는 prop 변경을 cascade로 인정).
- 이 cascade는 baseline의 일부로 인정됨 (의도된 normal commit).

**(c) AppContent의 `searchedStock` state 변경 (search 트리거)** — `injectedStock` prop 변경.
- 의도된 1회 cascade — prepend + highlight effect 위해 필수.

**Then (3가지 시나리오 cascade 측정)**

| Step | Cascade 기대값 | Reason |
| --- | --- | --- |
| (a) FilterBar typing 후 | baseline +0 | React.memo가 동일 `filterResults` prop reference를 받아 차단. ChartGrid가 `useScreen()` 직접 호출 안 함이 전제. |
| (b) currentPage 변경 후 | baseline +1 (baseline 정의에 포함되는 normal commit) | `currentPage` prop 변경은 의도된 cascade. ChartGrid 자체 페이징 동작. |
| (c) `injectedStock` 변경 후 | baseline +1 (의도된 cascade) | prepend + highlight effect 위해 필수. |
| (a) + (b) + (c) 누적 | baseline + (b의 1) + (c의 1) = baseline +2 | total cascade = currentPage 변경 + injectedStock 변경. FilterBar typing은 0. |

**실패 path**
- step (a) FilterBar typing에서 ChartGrid commit count 증가 시 React.memo 차단 실패 → fail.
- 흔한 원인: ChartGrid가 `useScreen()`을 직접 호출 (context subscription) — REQ-PERF-001 아키텍처 전제 위반.
- 흔한 원인: AppContent에서 ChartGrid에 전달되는 prop이 매 render마다 새 object/array reference로 생성 (예: inline `{...rest}` spread, `[...filterResults]` copy 등) → React.memo shallow equal fail.

**Edge case**
- StrictMode dev 환경: 각 cascade가 2회 측정될 수 있음 (development double-invoke). production build로 측정 권장 또는 strict 분기 허용.
- `currentPage` 변경과 `injectedStock` 변경이 동시 발생 (예: AC-INTEGRATE-001 case A: prepend + setCurrentPage(0)): React batching으로 1회 cascade로 합쳐질 수 있음 — 이 경우 baseline +1 (not +2).

---

### AC-INTEGRATE-006 (must-pass MP-2) — 기존 ChartCell useEffect 재실행 0회 (cell key 동일성)

REQ 매핑: REQ-PERF-002, MP-2

**Given**
- `ChartCell.tsx`의 `useEffect(..., [stock.code, timeframe])` 본문에 `console.count(\`chart-cell-effect-\${stock.code}\`)` instrumentation.
- ChartGrid에 stocks `[{code: 'A'}, {code: 'B'}, {code: 'C'}]` 마운트 → baseline counts: `{A: 1, B: 1, C: 1}` (StrictMode dev 제외).

**When**
- 검색 주입: `injectedStock = {code: 'D'}` (필터에 없음, prepend).
- → `displayedStocks = [{code: 'D'}, {code: 'A'}, {code: 'B'}, {code: 'C'}]`.

**Then**
- baseline 이후 counts: `{A: 1, B: 1, C: 1, D: 1}` (A/B/C는 cell key 동일성으로 instance 재사용, useEffect 재실행 0회. D는 mount이므로 1회 호출).
- 검증: `expect(callCounts.A).toBe(1)` `expect(callCounts.B).toBe(1)` `expect(callCounts.C).toBe(1)` `expect(callCounts.D).toBe(1)`.

**When (continue)**
- `injectedStock = null` reset → `displayedStocks = [{code: 'A'}, {code: 'B'}, {code: 'C'}]`.

**Then (continue)**
- D는 unmount (useEffect cleanup 1회).
- A/B/C는 cell key 동일성으로 instance reuse → effect 재실행 0회.
- counts: `{A: 1, B: 1, C: 1, D: 1 + cleanup}`.

**실패 path**
- A/B/C 중 어느 cell이 count 증가 시 cell key 동일성 위반 → React reconciliation 실패 → MP-2 fail.

**Edge case**
- StrictMode dev에서 D의 mount는 2회 호출 가능 (허용). A/B/C는 여전히 0회 증가 (strict).

---

## 6. Architectural Invariants — v2.0.0 재정의

### AC-ARCH-001 (must-pass MP-4) — 검색 동선이 ScreenContext.request mutate 0회 (정적 분석)

REQ 매핑: REQ-INTEGRATE-004, MP-4

**Given**
- `AppContent.tsx`, `ChartGrid.tsx`, `StockSearchBox.tsx` 파일 정적 grep.

**When**
- 검색 동선 함수들 (`handleSelectStock`, `onSelect`, `setSearchedStock`, `setInjectedStock`)에서 `useScreen()` setter 또는 `applyFilters()` 호출 여부 확인.

**Then**
- 위 3개 파일에서 검색 관련 callback 내부에 `useScreen()` setter / `applyFilters()` / `screenState.request = ...` 호출 0건.
- 검색 동선은 오직 `setSearchedStock` (AppContent local state) 또는 `setInjectedStock` (ChartGrid prop)만 호출.

**검증 방법**
- vitest 정적 lint: `grep -E "applyFilters\\(|setRequest\\(|screenState\\.request\\s*=" frontend/src/AppContent.tsx frontend/src/components/ChartGrid/ChartGrid.tsx frontend/src/components/ChartGrid/StockSearchBox.tsx` → 0 results.

> v1.0.0 AC-ARCH-001 (modal portal scope)는 modal 폐기로 폐기됨.

---

### AC-ARCH-002 (must-pass MP-5) — 외부 라이브러리 추가 0

REQ 매핑: NFR-CONST-001, MP-5. v1.0.0 그대로.

**Given** - v1.0.0 ship 시 `package.json` + `requirements.txt` snapshot.

**When** - v2.0.0 ship 후 동일 파일 비교.

**Then** - 새 entry 0건.

---

### AC-ARCH-003 — `StockSearchBox` useScreen/useTab 미구독

REQ 매핑: REQ-PERF-001 (보조). v1.0.0 그대로.

**Then** - `StockSearchBox.tsx` 내부에서 `useScreen()` 또는 `useTab()` import/호출 0회.

---

## 7. Performance Invariants — v2.0.0 재정의

### AC-PERF-001 (must-pass MP-1 cross-ref) — ChartGrid React.memo cascade

AC-INTEGRATE-005에서 이미 다룸. cross-reference 표기.

---

### AC-PERF-002 (must-pass MP-2 cross-ref) — ChartCell useEffect 0회

AC-INTEGRATE-006에서 이미 다룸. cross-reference 표기.

---

### AC-PERF-003 (must-pass MP-3 cross-ref) — ScreenContext.request deep-equal

AC-INTEGRATE-003에서 이미 다룸. cross-reference 표기.

---

### AC-PERF-004 — 자동완성 latency ≤ 80 ms

REQ 매핑: NFR-PERF-001. v1.0.0 그대로.

**Then** - debounce 종료 후 setCandidates까지 ≤ 80 ms (JSDOM 임계값은 150 ms 완화 가능).

---

## 8. Definition of Done (v2.0.0)

다음 항목 **전부 충족** 시 SPEC v2.0.0 ship 가능.

- [ ] AC-DATA-001 ~ 004 PASS (must-pass, v1.0.0 그대로)
- [ ] AC-SEARCH-001, 004, 005, 006, 007, 008, 009, 010, 011 PASS (v1.0.0 그대로)
- [ ] AC-SEARCH-002 PASS (must-pass, cachedPromise invariant)
- [ ] AC-SEARCH-003 PASS (v2 재정의: 필터 우회 + prepend + highlight)
- [ ] AC-SEARCH-012 PASS (v2 재정의: Escape input clear, modal close 부분 제거)
- [ ] **AC-INTEGRATE-001 PASS (must-pass MP-1 baseline: prepend 동작)**
- [ ] **AC-INTEGRATE-002 PASS (must-pass: scroll + highlight, no duplicate)**
- [ ] **AC-INTEGRATE-003 PASS (must-pass MP-3: ScreenContext.request deep-equal)**
- [ ] **AC-INTEGRATE-004 PASS (highlight CSS class apply + 자동 제거)**
- [ ] **AC-INTEGRATE-005 PASS (must-pass MP-1: ChartGrid cascade ≤ +1)**
- [ ] **AC-INTEGRATE-006 PASS (must-pass MP-2: 기존 ChartCell useEffect 0회 증가)**
- [ ] AC-ARCH-001 PASS (must-pass MP-4: 검색 동선이 request mutate 0)
- [ ] AC-ARCH-002 PASS (must-pass MP-5: 외부 라이브러리 0)
- [ ] AC-ARCH-003 PASS (StockSearchBox useScreen/useTab 미구독)
- [ ] AC-PERF-004 PASS (latency)
- [ ] TRUST 5 quality gates 통과 (manager-quality 위임)
- [ ] `spec.md` frontmatter `status: Implemented` 갱신
- [ ] MX tags 추가 완료 (plan.md §4 v2.0.0 기준)
- [ ] v1.0.0 modal 자산 3개 파일 제거 완료 (`StockSearchModal.tsx`, `StockSearchModal.test.tsx`, `useFocusTrap.ts`)
- [ ] 라이브 사용 가설 (§spec.md §2) ship 후 2주 측정 일정 등록 (lesson #7 의무)
- [ ] **v2.0.0 폐기 기준 (plan.md §7.5) 명시 — mental model drift 재발 여부 추적 의무**

---

## 9. Must-pass Summary (v2.0.0, 15개)

| # | ID | 설명 | 매핑 |
| --- | --- | --- | --- |
| 1 | AC-DATA-001 | 정상 200 + 헤더 + 정렬 | REQ-DATA-001 |
| 2 | AC-DATA-002 | 빈 stock_meta → 503 | REQ-DATA-003 |
| 3 | AC-DATA-003 | stock_meta 부재 → 503 | REQ-DATA-003 |
| 4 | AC-DATA-004 | SELECT-only invariant | REQ-DATA-002 |
| 5 | AC-SEARCH-002 | cachedPromise invariant | REQ-SEARCH-002 |
| 6 | AC-INTEGRATE-001 | prepend 동작 | REQ-INTEGRATE-003 |
| 7 | AC-INTEGRATE-002 | scroll + highlight, no duplicate | REQ-INTEGRATE-002 |
| 8 | AC-INTEGRATE-003 | request deep-equal (MP-3) | REQ-INTEGRATE-004 |
| 9 | AC-INTEGRATE-005 | ChartGrid cascade ≤ +1 (MP-1) | REQ-PERF-001 |
| 10 | AC-INTEGRATE-006 | 기존 ChartCell useEffect 0회 (MP-2) | REQ-PERF-002 |
| 11 | AC-ARCH-001 | 검색 동선이 request mutate 0 (MP-4) | REQ-INTEGRATE-004 |
| 12 | AC-ARCH-002 | 외부 라이브러리 0 (MP-5) | NFR-CONST-001 |
| 13 | AC-SEARCH-001 | 한글 prefix 매치 | REQ-SEARCH-003 |
| 14 | AC-SEARCH-006 | 5단계 score | REQ-SEARCH-003 |
| 15 | AC-SEARCH-011 | 영문 alias 매칭 | REQ-SEARCH-003 |

---

## 10. Edge Case Catalog (v2.0.0)

| # | 케이스 | 결정 시점 |
| --- | --- | --- |
| EC-1 | 검색 도중 `cachedPromise`가 503으로 resolve된 경우 — 입력 상태 즉시 disabled | T3 REFACTOR (v1.0.0 유지) |
| EC-2 (v2 재정의) | 검색 후 사용자가 다른 탭으로 이동 (`useTab.activeTab` 변경) — `searchedStock` state 유지 여부 | T12 REFACTOR. 기본: state 유지 (다음 ChartGrid 활성 시 그대로 표시). |
| EC-3 | `useStockMaster` cachedPromise refresh trigger | future amendment (EX-12) |
| EC-4 | screen reader 사용자에게 "검색 결과 N건" 안내 (`aria-live` 영역) | T4 REFACTOR (v1.0.0 그대로) |
| EC-5 (v2 재정의) | ChartGrid pageSize 변경 시 page index 재계산 | T11 boundary check (R-4) |
| EC-6 | 사용자가 `chart-search-input`에 빠르게 입력+삭제 반복 | T4 (debounce reset, v1.0.0 그대로) |
| EC-7 | 동점 score `localeCompare` 결과가 사용자 의도와 다를 때 — secondary tiebreaker `code` ascending | T2 REFACTOR (v1.0.0 그대로) |
| EC-8 | 한자/일본어 종목명 (CJK extension) 매칭 | EX 처리 (v1.0.0 그대로) |
| EC-9 (v2 신규) | 검색 종목이 stocks의 마지막 페이지 마지막 셀일 때 | T11 boundary check |
| EC-10 (v2 신규) | stocks가 0개일 때 검색 → prepend 동작 | T10 boundary check (`displayedStocks = [injectedStock]`) |
| EC-11 (v2 신규) | Highlight animation 중 새 검색 발생 | T11 cleanup logic (이전 timeout clear + 새 setTimeout) |
| EC-12 (v2 신규) | Component unmount during animation | T11 cleanup (classList.remove + clearTimeout) |
| EC-13 (v2 신규) | ChartGrid filter 변경 후 `searchedStock` state 유지 여부 | T12. 기본: 유지 (다음 검색 또는 명시적 reset 까지). 향후 사용자 피드백에 따라 자동 reset 검토. |

---

## 11. Removed Acceptance Criteria (v1.0.0 → v2.0.0)

다음 AC들은 v2.0.0에서 폐기됨 (modal 패턴 폐기로 인한 일괄 제거):

| AC ID | 폐기 사유 |
| --- | --- |
| AC-MODAL-001 | modal portal scope — modal 자체 없음 |
| AC-MODAL-002 | modal a11y patterns — modal 자체 없음 |
| AC-MODAL-003 | Esc 닫기 + focus 복귀 — modal 자체 없음 |
| AC-MODAL-004 | 백드롭 클릭 닫기 — modal 자체 없음 |
| AC-MODAL-005 | ✕ 닫기 버튼 — modal 자체 없음 |
| AC-MODAL-006 | timeframe 토글 — modal timeframe 자체 없음 (EX-17) |
| AC-MODAL-007 | modal useEffect 1회 — modal 자체 없음 |
| AC-MODAL-008 | modal race guard cancelled flag — modal 자체 없음 |
| AC-MODAL-009 | Initial timeframe 계승 — modal 자체 없음 |

총 9개 modal AC 제거 + integration AC 6개 신규 + 기존 AC 2개 (AC-SEARCH-003, AC-SEARCH-012) 재정의 = AC 총 30개 (v1.0.0 32개 대비 net -2).

---

Version: 2.0.0
Last Updated: 2026-05-12
