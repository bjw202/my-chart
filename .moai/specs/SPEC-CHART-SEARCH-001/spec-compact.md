# SPEC-CHART-SEARCH-001 — Compact Reference (v2.0.0, Run Phase)

문서 분류: Compact (auto-generated for run phase context optimization)
SPEC 버전: 2.0.0 (BREAKING amendment, Draft)
생성일: 2026-05-11
업데이트: 2026-05-12 (v2.0.0 — modal 패턴 폐기, ChartGrid 통합 주입 패턴 도입)
참조 원본: `spec.md`, `acceptance.md`

> 이 문서는 run phase token budget 절약을 위해 spec.md / acceptance.md에서 핵심만 추출했다.

## HISTORY
- 2026-05-11 v1.0.0 초안 + Amendment 1
- 2026-05-12 **v2.0.0 BREAKING** — modal 폐기 + ChartGrid 통합 주입. REQ-MODAL-001~004 → REQ-INTEGRATE-001~004. AC-MODAL-001~009 (9건) 제거 → AC-INTEGRATE-001~006 (6건) 신규.
- 2026-05-12 v2.0.0 audit iter 1 minor improvements applied (I-1/I-2/I-7). plan-auditor frontmatter false positive (D-1/D-2) 무효 처리 (labels/created field 본 프로젝트 컨벤션 유지).

---

## REQ Index (v2.0.0)

### Search Input + Autocomplete (v1.0.0 그대로)

- **REQ-SEARCH-001** (Ubiquitous): The system SHALL mount a single `StockSearchBox` input on the left side of `chart-grid-toolbar` div in `ChartGrid.tsx`. Width ~220 px, `flexShrink: 0`.
- **REQ-SEARCH-002** (Event-Driven): WHEN user first focuses `StockSearchBox`, the system SHALL invoke `useStockMaster()` with module-level cachedPromise.
- **REQ-SEARCH-003** (Event-Driven): WHEN input passes 150 ms debounce, the system SHALL compute candidates via `matchesQuery` and render up to 8 in `<ul role="listbox">` sorted by score desc + tiebreaker. 5단계 score: (5) 영문 alias prefix / (4) 종목코드 prefix / (3) 종목명 prefix / (2) 종목명 substring / (1) 한글 초성 prefix.
- **REQ-SEARCH-004** (State-Driven): WHILE 결과 0건이고 input 비어있지 않음, render `<li data-testid="chart-search-empty" aria-disabled="true">검색 결과 없음</li>`.
- **REQ-SEARCH-005** (Ubiquitous): keyboard navigation — ArrowDown/Up (wrap + aria-activedescendant), Enter (select), Escape (close + clear), Tab (close + focus next).
- **REQ-SEARCH-006** (Unwanted Behavior): IF 503 stock_meta_not_ready, THEN disable input + placeholder `DB 업데이트 필요` + title tooltip.

### ChartGrid Integration Injection (v2.0.0 신규 — REQ-MODAL-001~004 폐기)

- **REQ-INTEGRATE-001** (Event-Driven): WHEN user selects a candidate from `StockSearchBox` (click OR Enter), THEN the system SHALL inject the searched stock into ChartGrid's displayed stocks list WITHOUT modifying ScreenContext filters. AppContent `searchedStock` state → ChartGrid `injectedStock` prop drilling.
- **REQ-INTEGRATE-002** (Event-Driven): WHEN the searched stock already exists in current filter results, THEN auto-scroll to that cell's page (via `setCurrentPage(targetPageIndex)`) + apply `cell-search-highlight` CSS class for 2~3 seconds, NOT prepend a duplicate. Duplicate count = 0.
- **REQ-INTEGRATE-003** (Event-Driven): WHEN the searched stock does NOT exist in current filter results, THEN prepend the stock as the first cell of ChartGrid (`displayedStocks = [injectedStock, ...filterResults]`) + apply `cell-search-highlight` to newly prepended cell. 기존 cells는 React key (`stock.code`) 동일성으로 ChartCell instance reuse.
- **REQ-INTEGRATE-004** (Ubiquitous): The system SHALL preserve `useScreen().screenState.request` deep-equal across search injection events. 검색 동선에서 `useScreen()` setter / `applyFilters()` 호출 0회 (정적 분석 가능).

### Performance Invariants (Anti-regression, v2.0.0 재작성)

- **REQ-PERF-001** (Unwanted Behavior, I-1 명확화): IF unrelated state change (FilterBar typing during compose / ScreenContext result reload / currentPage prop change), THEN React.memo SHALL block cascade — 추가 commit 0. EXCEPT `injectedStock` prop change (1회 cascade 허용 for prepend + highlight). **아키텍처 전제**: ChartGrid는 `useScreen()` 직접 호출 안 함. AppContent가 `filterResults` prop으로 전달 → React.memo shallow equal로 cascade 차단 가능.
- **REQ-PERF-002** (Unwanted Behavior): IF search injection event, THEN existing ChartCell instances' `useEffect (dep [stock.code, timeframe])` SHALL NOT be re-invoked. cell key (`stock.code`) 동일성으로 React reconciliation이 instance 재사용 → effect skip.

### Stocks Master Data (v1.0.0 그대로)

- **REQ-DATA-001** (Ubiquitous): `GET /api/stocks/master` returning `{stocks: [{code, name, market}], generated_at}` with ETag + Cache-Control: max-age=300.
- **REQ-DATA-002** (Ubiquitous): SQLite `mode=ro` URI. SELECT-only.
- **REQ-DATA-003** (Unwanted Behavior): IF stock_meta absent OR empty, THEN 503 `stock_meta_not_ready`.

### Non-Functional (v2.0.0 갱신)

- **NFR-PERF-001**: 검색 input → 후보 노출 ≤ 80 ms (debounce 종료 기준).
- **NFR-PERF-002**: 후보 선택 → ChartGrid 첫 셀 차트 first paint ≤ 300 ms (v2 의미 재정의: modal first paint → ChartGrid 첫 셀 first paint).
- **NFR-PERF-003**: 검색 주입 중 ChartGrid scroll/page FPS ≥ 55.
- **NFR-PERF-004**: `GET /api/stocks/master` — cold ≤ 500 ms, warm (304) ≤ 50 ms.
- **NFR-PERF-005**: payload < 50 KB (gzip).
- **NFR-A11Y-001** (v2 재정의): 검색 후 ChartGrid scroll/prepend 완료 후 `chart-search-input`에 keyboard focus 유지. modal focus trap 불필요 (modal 없음).
- **NFR-A11Y-002**: SearchBox listbox/option ARIA + 키보드 only navigation.
- **NFR-CONST-001**: 신규 외부 라이브러리 추가 0. highlight CSS도 자체 keyframes.
- **NFR-CONST-002**: stock_meta DB SELECT-only.

---

## Must-Pass Anti-Regression (v2.0.0 재정의, 15개)

- **MP-1** (AC-INTEGRATE-005): ChartGrid React.memo cascade — injectedStock prop 변경 시 +1 허용 (의도된 동작), 다른 cause는 0.
- **MP-2** (AC-INTEGRATE-006): 기존 ChartCell useEffect 재실행 0회 (cell key 동일성으로 instance reuse).
- **MP-3** (AC-INTEGRATE-003): `useScreen().screenState.request` deep-equal 보존.
- **MP-4** (AC-ARCH-001): 검색 동선이 ScreenContext.request mutate 0회 (정적 grep 분석).
- **MP-5** (AC-ARCH-002): `package.json` / `requirements.txt` 신규 entry 0.
- **MP-6 ~ MP-15** (AC-DATA-001~004, AC-SEARCH-001/002/006/011, AC-INTEGRATE-001/002): 정상 동작 + 503 + 5단계 score + alias + prepend + scroll/highlight.

> v1.0.0 MP-4 (portal subtree scope)는 modal 폐기로 폐기됨.

---

## Files to Modify (v2.0.0)

### Backend (변경 없음, v1.0.0 그대로)
- [EXISTING] `backend/routers/stocks.py`, `backend/services/stocks_master_service.py`, `backend/main.py`, `backend/tests/test_stocks_master.py`

### Frontend Util (변경 없음, v1.0.0 그대로)
- [EXISTING] `frontend/src/utils/hangul.ts`, `hangul-aliases.ts`, `__tests__/hangul.test.ts`

### Frontend API + Hook (변경 없음, v1.0.0 그대로)
- [EXISTING] `frontend/src/api/stocks.ts`, `useStockMaster.ts`, `__tests__/useStockMaster.test.ts`

### Frontend Components (v2.0.0 변경)
- [EXISTING] `frontend/src/components/ChartGrid/StockSearchBox.tsx`, `__tests__/StockSearchBox.test.tsx`
- **[REMOVE]** `frontend/src/components/ChartGrid/StockSearchModal.tsx` (~250 LOC, archive에 보존)
- **[REMOVE]** `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx`
- **[REMOVE]** `frontend/src/components/ChartGrid/useFocusTrap.ts` (~30 LOC, modal 폐기로 불필요)
- **[MODIFY]** `frontend/src/components/ChartGrid/ChartGrid.tsx` (+50: `injectedStock` prop, `displayedStocks` union, useEffect for scroll + highlight. React.memo 유지)
- **[MODIFY]** `frontend/src/AppContent.tsx` (net -5: modal mount 코드 제거, `searchedStock` → `injectedStock` prop forwarding)
- **[NEW]** `frontend/src/components/ChartGrid/cellHighlight.css` (or inline, +30: `@keyframes border-flash` + `.cell-search-highlight`)
- **[NEW]** `frontend/src/components/ChartGrid/__tests__/ChartGrid.integration.test.tsx` (+250: 6+ 통합 시나리오)
- **[MODIFY]** `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` (modal-coupled 시나리오 제거 + integration-aware 시나리오 보강)

### Files NOT to modify (anti-regression invariant)
- `frontend/src/components/ChartGrid/ChartCell.tsx` (cell key 동일성으로 instance reuse 보장)
- `frontend/src/contexts/ScreenContext.tsx`
- `frontend/src/components/FilterBar/FilterBar.tsx`
- `frontend/src/types/market.ts`

---

## Acceptance Scenarios (Given/When/Then summary, v2.0.0)

### Module: Stocks Master (v1.0.0 그대로)
- **AC-DATA-001** (must-pass): 정상 200 + headers + 정렬.
- **AC-DATA-002** (must-pass): 빈 stock_meta → 503.
- **AC-DATA-003** (must-pass): stock_meta 부재 → 503.
- **AC-DATA-004** (must-pass): SELECT-only invariant (mode=ro).

### Module: Hangul Util (v1.0.0 그대로)
- **AC-SEARCH-005**: 초성 추출.
- **AC-SEARCH-006**: matchesQuery 5단계 score + 동점 tiebreaker.
- **AC-SEARCH-011**: 영문 alias 매칭 score 5.

### Module: useStockMaster Hook (v1.0.0 그대로)
- **AC-SEARCH-002** (must-pass): cachedPromise — 1회 fetch.
- **AC-SEARCH-007**: 503 → error noti.

### Module: StockSearchBox (v1.0.0 그대로, AC-SEARCH-003/012 재정의)
- **AC-SEARCH-001**: 한글 prefix → listbox.
- **AC-SEARCH-003 (v2 재정의)**: 필터 우회 — 필터 밖 종목 검색 → ChartGrid 첫 셀 prepend + highlight + `useScreen.request` deep-equal.
- **AC-SEARCH-004**: 초성 검색.
- **AC-SEARCH-008**: 0건 결과 → empty.
- **AC-SEARCH-009**: 503 disabled.
- **AC-SEARCH-010**: 키보드 navigation.
- **AC-SEARCH-012 (v2 재정의)**: Escape → input clear + listbox 닫음. ChartGrid prepend는 유지 (modal close 부분 제거됨).

### Module: ChartGrid Integration (v2.0.0 신규)
- **AC-INTEGRATE-001 (must-pass, I-7 갱신)**: 필터에 없는 종목 → prepend (`displayedStocks[0] = injectedStock`, `data-testid="chart-cell-injected-{code}"`) **+ `setCurrentPage(0)` reset** (조건부: IF currentPage > 0 at injection time THEN setCurrentPage(0) ELSE no page change). page indicator "1 / N+1" 표시.
- **AC-INTEGRATE-002 (must-pass)**: 필터에 있는 종목 → `setCurrentPage(floor(idx/pageSize))` + highlight, prepend 0.
- **AC-INTEGRATE-003 (must-pass MP-3)**: `useScreen().screenState.request` deep-equal across all injections.
- **AC-INTEGRATE-004**: `cell-search-highlight` CSS class 적용 + 2.5s 후 자동 제거 (`setTimeout` + `clearTimeout` cleanup).
- **AC-INTEGRATE-005 (must-pass MP-1, I-2 현실 시나리오)**: ChartGrid cascade 측정 — 3가지 현실 source: (a) FilterBar typing during compose → +0 (React.memo 차단), (b) currentPage 변경 → +1 (의도된 baseline normal commit), (c) `injectedStock` 변경 → +1 (의도된 cascade). 실패 흔한 원인: ChartGrid가 `useScreen()` 직접 호출 / AppContent에서 inline new reference prop.
- **AC-INTEGRATE-006 (must-pass MP-2)**: 기존 ChartCell useEffect — cell key 동일성으로 0회 증가. 새 prepend cell은 mount 1회 (StrictMode 2회 허용).

### Module: Performance Invariants
- **AC-PERF-001** (cross-ref AC-INTEGRATE-005, MP-1).
- **AC-PERF-002** (cross-ref AC-INTEGRATE-006, MP-2).
- **AC-PERF-003** (cross-ref AC-INTEGRATE-003, MP-3).
- **AC-PERF-004**: autocomplete latency ≤ 80 ms (debounce 종료 기준).

### Module: Architectural
- **AC-ARCH-001 (must-pass MP-4, v2 재정의)**: 검색 동선이 `useScreen()` setter / `applyFilters()` 호출 0회 (정적 grep `applyFilters\(|setRequest\(|screenState\.request\s*=`).
- **AC-ARCH-002 (must-pass MP-5)**: 외부 라이브러리 추가 0.
- **AC-ARCH-003**: StockSearchBox useScreen/useTab 미구독.

### Removed (v2.0.0)
- AC-MODAL-001~009 (9개) — modal 폐기로 일괄 제거.

---

## Exclusions (What NOT to Build, v2.0.0)

- EX-1 Theme → ChartGrid 진입
- **EX-2 (v2 wording 수정)**: 검색 결과 → ChartGrid `filters/request` state mutation 금지 (단, 표시 stocks 배열에 추가는 허용 — REQ-INTEGRATE-001~003)
- EX-3 appliedContext chip / mismatch banner / FilterBar 검색 chip
- EX-4 검색 기록 / 최근 검색 / 인기 종목
- EX-5 Fuzzy matching, 오타 보정
- EX-6 매치 텍스트 highlight (listbox 텍스트 강조, cell highlight와 다름)
- EX-7 debounce 시간 조정
- EX-9 Cmd/Ctrl+K 단축키
- EX-10 ChartGrid empty state "검색해보기" 링크
- EX-11 URL deep linking (SPEC-TAB-URL-001)
- EX-12 DbUpdateButton → cachedPromise reset
- EX-13 백엔드 in-memory TTL 캐시
- EX-14 신규 pip / npm 의존성
- EX-15 ETF / 해외종목 / 5만 종목 scaling
- **EX-16 (v2 신규)**: modal / popover / overlay 패턴 (v1.0.0 archive에 보존)
- **EX-17 (v2 신규)**: 검색 종목 차트의 timeframe 토글 (modal 폐기로 함께 폐기, ChartGrid 현재 timeframe 사용)
- **EX-18 (v2 신규)**: 검색 종목 차트 닫기 동선 (ChartGrid 통합으로 불필요)
- **EX-19 (v2 신규)**: 사이드바 fixed panel, 별도 route 등 v3 후보 패턴 (별도 SPEC으로 분리)

---

## TDD Task Sequence (v2.0.0)

v1.0.0 T1~T4 (backend, hangul, hook, SearchBox)는 그대로 유지 (이미 ship됨).
v1.0.0 T5~T8 (modal, integration, perf RED/GREEN)는 폐기 또는 T9~T13으로 재작성.

| T# | Task | Files | Dependency |
| --- | --- | --- | --- |
| T1~T4 | (v1.0.0 그대로 유지, backend + hangul + hook + SearchBox) | (변경 없음) | — |
| **T9** | **v1.0.0 modal 자산 제거** + AppContent modal mount 코드 삭제 | StockSearchModal.tsx, useFocusTrap.ts, StockSearchModal.test.tsx 삭제 + AppContent.tsx modal mount 제거 | (cleanup) |
| **T10** | **ChartGrid `injectedStock` prop + stocks union** | ChartGrid.tsx (+30: props 인터페이스 + displayedStocks union) | T9 |
| **T11** | **자동 scroll + highlight CSS animation** | ChartGrid.tsx (+20: useEffect for setCurrentPage + classList.add/remove), cellHighlight.css (신규) | T10 |
| **T12** | **ChartGrid props 확장 + AppContent prop forwarding** | AppContent.tsx (+10), ChartGrid.tsx (React.memo 유지) | T10, T11 |
| **T13** | **Integration tests + anti-regression performance tests** | ChartGrid.integration.test.tsx (신규), ChartGrid.perf.test.tsx (modal 부분 제거 + integration-aware 보강) | T10, T11, T12 |

순서 그래프:
```
T9 (modal cleanup) → T10 (stocks union) → T11 (scroll + highlight) → T12 (props 확장) → T13 (integration tests)
```

---

## MX Tag Plan (v2.0.0)

- `StockSearchBox.tsx` — `@MX:ANCHOR` (유지, fan_in ≥ 3)
- `hangul.ts` — `@MX:NOTE` (유지)
- `hangul-aliases.ts` — `@MX:NOTE` (유지)
- `StockSearchModal.tsx` — **DELETED**
- `useFocusTrap.ts` — **DELETED**
- `useStockMaster.ts` — `@MX:NOTE` (유지)
- `stocks_master_service.py` — `@MX:ANCHOR` (유지)
- **`ChartGrid.tsx` — `@MX:ANCHOR` (강화)**: fan_in ≥ 3, `injectedStock` prop + scroll/highlight effect invariant 추가
- **`AppContent.tsx` — `@MX:NOTE` (신규)**: `searchedStock` state lift + ChartGrid prop forwarding 패턴

---

## v2.0.0 Live Validation Plan (lesson #7 lock-in)

| Signal | Threshold | Action |
| --- | --- | --- |
| 세션당 검색 횟수 | < 1.0회 (2주) | v3 후보 별도 SPEC 검토 |
| 검색 → ChartGrid 표시 latency | > 1000 ms | 성능 분석 |
| MP-1 ~ MP-5 위반 | 1건 이상 | 즉시 hotfix |
| 사용자 mental model drift | 명시적 "이것도 원하는 게 아님" 피드백 | v3 후보 별도 SPEC (sidebar / route) |

v3 후보 패턴 (rollback 시):
- **Option A**: Sidebar fixed panel
- **Option B**: 별도 route (`/chart/:code`)
- **Option C**: 기능 자체 폐기

---

Version: 2.0.0
Last Updated: 2026-05-12
