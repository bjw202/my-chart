# SPEC-CHART-SEARCH-001 — Compact Reference (Run Phase)

문서 분류: Compact (auto-generated for run phase context optimization)
SPEC 버전: 1.0.0 (amendment 1 applied 2026-05-11)
생성일: 2026-05-11
업데이트: 2026-05-11 (audit iteration 1: I-1~I-6 + Q-1~Q-7 smart defaults)
참조 원본: `spec.md`, `acceptance.md`

> 이 문서는 run phase token budget 절약을 위해 spec.md / acceptance.md에서 핵심만 추출했다. Overview / live use hypothesis / 거부된 대안 / open questions(이미 해결)는 제외.

## HISTORY
- 2026-05-11 v1.0.0 초안
- 2026-05-11 Amendment 1 — I-1 latency narrative 명확화 / I-2 timeframe 계승 commit / I-3 `'daily'/'weekly'` param 통일 / I-4 modal-content 매핑 행 추가 / I-5 NFR-PERF-004 warm cache target / I-6 R-2 mitigation에 `React.memo` 명시. Q-1 alias 50종 채택 / Q-4 modal close → input clear / Q-5 AnalysisModal 패턴 / Q-7 timeframe 계승 채택. Q-2/Q-3/Q-6 제외 확정.

---

## REQ Index

### Search Input + Autocomplete

- **REQ-SEARCH-001** (Ubiquitous): The system SHALL mount a single `StockSearchBox` input on the left side of `chart-grid-toolbar` div in `ChartGrid.tsx`. Width ~220 px, `flexShrink: 0`.
- **REQ-SEARCH-002** (Event-Driven): WHEN the user first focuses `StockSearchBox` within a session, the system SHALL invoke `useStockMaster()` which dispatches single `fetchStockMaster()` call and caches resolved promise at module level. 같은 세션 재호출 시 추가 fetch 0.
- **REQ-SEARCH-003** (Event-Driven): WHEN input passes 150 ms debounce, the system SHALL compute candidates via `matchesQuery` and render up to 8 in `<ul role="listbox">` sorted by score desc + `name.localeCompare` tiebreaker. **5단계 score (amendment 1, Q-1)**: (5) 영문 alias prefix — `frontend/src/utils/hangul-aliases.ts` 50종 사전 / (4) 종목코드 prefix / (3) 종목명 prefix / (2) 종목명 substring / (1) 한글 초성 prefix.
- **REQ-SEARCH-004** (State-Driven): WHILE 결과 0건이고 input 비어있지 않음, the system SHALL render `<li data-testid="chart-search-empty" aria-disabled="true">검색 결과 없음</li>`.
- **REQ-SEARCH-005** (Ubiquitous): The system SHALL support keyboard navigation — ArrowDown/Up (wrap-around + `aria-activedescendant`), Enter (select highlighted or first), Escape (close + clear), Tab (close + focus next).
- **REQ-SEARCH-006** (Unwanted Behavior): IF `GET /api/stocks/master` returns 503 `stock_meta_not_ready`, THEN the system SHALL disable input, replace placeholder with `DB 업데이트 필요`, surface `title` attribute `DB 업데이트가 필요합니다`.

### Stand-alone Modal Display

- **REQ-MODAL-001** (Event-Driven): WHEN user selects a candidate (click OR Enter), THEN the system SHALL lift `selectedStock` state to `AppContent` host and mount `StockSearchModal` via `ReactDOM.createPortal(modal, document.body)`. Stand-alone lightweight-charts instance. **Initial timeframe (Q-7, I-2)**: ChartGrid 마지막 사용 timeframe 계승, fallback `'daily'`. mount 시점 1회 snapshot으로만 사용 (ChartGrid context 미구독).
- **REQ-MODAL-002** (Event-Driven): WHEN modal close action (Escape / backdrop / ✕), THEN the system SHALL: (1) unmount portal, (2) `selectedStock=null`, (3) restore focus to `StockSearchBox` input via trigger ref, (4) **clear `StockSearchBox` input value to `''` (Q-4)** + close listbox.
- **REQ-MODAL-003** (Ubiquitous): The system SHALL apply WCAG 2.1 AA modal patterns — `role="dialog"`, `aria-modal="true"`, `aria-labelledby="stock-search-modal-title"`, 초기 focus는 modal-content (`tabIndex={-1}`, `data-testid="stock-search-modal-content"`), focus trap (기존 AnalysisModal 답습, Q-5), `body.style.overflow="hidden"` scroll lock + 닫힘 시 해제.
- **REQ-MODAL-004** (Optional): WHERE user clicks timeframe toggle, re-fetch chart data for new timeframe (UI: `일봉`/`주봉` ↔ API param: **`'daily'`/`'weekly'` (I-3)** — `'D'`/`'W'` 사용 금지) and re-render same chart instance without closing modal.

### Performance Invariants (Anti-regression)

- **REQ-PERF-001** (Unwanted Behavior): IF `StockSearchModal` open/close/active while user interacts with ChartGrid, THEN the system SHALL NOT trigger additional `ChartGrid` parent render commits beyond baseline.
- **REQ-PERF-002** (Unwanted Behavior): IF `StockSearchModal` opened, the modal chart's `useEffect (dep [selectedStock.code, timeframe])` SHALL NOT be invoked more than once per modal-open event (StrictMode dev 2회 허용). cancelled flag race guard 적용 (archive `df3ca36` 패턴).

### Stocks Master Data

- **REQ-DATA-001** (Ubiquitous): `GET /api/stocks/master` returning `{stocks: [{code, name, market}], generated_at}` with headers `ETag: <MAX(stock_meta.last_updated)>` + `Cache-Control: max-age=300`.
- **REQ-DATA-002** (Ubiquitous): `SELECT code, name, market FROM stock_meta WHERE name IS NOT NULL ORDER BY name` via SQLite `mode=ro` URI. INSERT/UPDATE/DELETE/CREATE/DROP/ALTER prohibited.
- **REQ-DATA-003** (Unwanted Behavior): IF `stock_meta` absent OR empty, THEN HTTP 503 `{"detail": "stock_meta_not_ready"}`.

### Non-Functional

- **NFR-PERF-001**: 검색 input → 후보 노출 ≤ 80 ms (**debounce 종료 시점 기준 — I-1**). 첫 keystroke 기준 debounce(150 ms) + compute+render ≤ 80 ms = 총 ≤ 230 ms.
- **NFR-PERF-002**: 후보 선택 → 모달 차트 first paint ≤ 300 ms.
- **NFR-PERF-003**: modal 열림 중 ChartGrid scroll/page FPS ≥ 55.
- **NFR-PERF-004** (I-5): `GET /api/stocks/master` — **cold start ≤ 500 ms, warm cache (ETag 304) ≤ 50 ms**.
- **NFR-PERF-005**: `GET /api/stocks/master` payload < 50 KB (gzip).
- **NFR-A11Y-001**: modal WCAG 2.1 AA.
- **NFR-A11Y-002**: SearchBox listbox/option ARIA + 키보드 only navigation.
- **NFR-CONST-001**: 신규 외부 라이브러리 추가 0건.
- **NFR-CONST-002**: `stock_meta` DB SELECT-only.

---

## Must-Pass Anti-Regression

- **MP-1** (AC-PERF-001): ChartGrid 부모 React Profiler commit count baseline 대비 추가 0회.
- **MP-2** (AC-PERF-002): ChartCell useEffect 재실행 0회.
- **MP-3** (AC-PERF-003): `useScreen().screenState.request` deep-equal 보존.
- **MP-4** (AC-MODAL-001, AC-ARCH-001): `StockSearchModal`은 `document.body` 직속 자식, ChartGrid DOM subtree에 부재.
- **MP-5** (AC-ARCH-002): `package.json` / `requirements.txt` 신규 entry 0.

---

## Files to Modify

### Backend
- [NEW] `backend/routers/stocks.py` (+52, archive cherry-pick)
- [NEW] `backend/services/stocks_master_service.py` (+65, archive cherry-pick)
- [NEW] `backend/tests/test_stocks_master.py` (+120, RED)
- [MODIFY] `backend/main.py` (+2)

### Frontend Util (amendment 1: alias 사전 추가)
- [NEW] `frontend/src/utils/hangul.ts` (+60, archive 47 + alias score 5 분기 +13)
- [NEW] `frontend/src/utils/hangul-aliases.ts` (~50 LOC, **Q-1 50종 ko↔en 사전**, 시총·외국인 거래 비중 상위 기준)
- [NEW] `frontend/src/utils/__tests__/hangul.test.ts` (+100, alias 케이스 포함)

### Frontend API + Hook
- [NEW] `frontend/src/api/stocks.ts` (+25, archive cherry-pick)
- [NEW] `frontend/src/hooks/useStockMaster.ts` (+42, archive cherry-pick. module-level cachedPromise)
- [NEW] `frontend/src/hooks/__tests__/useStockMaster.test.ts` (+100, RED)

### Frontend Components
- [NEW] `frontend/src/components/ChartGrid/StockSearchBox.tsx` (~180, archive 154 + 키보드 + onSelect prop + `clearInput` imperative handle)
- [NEW] `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` (+200, RED)
- [NEW] `frontend/src/components/ChartGrid/StockSearchModal.tsx` (~250, portal + lightweight-charts + cancelled flag + a11y + `initialTimeframe` prop)
- [NEW] `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx` (+180, RED, AC-MODAL-009 포함)
- [NEW] `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` (+120, anti-regression)
- [NEW (조건부, T5a)] `frontend/src/components/ChartGrid/useFocusTrap.ts` (~30, Q-5 — 기존 AnalysisModal에 focus trap 부재 시에만)
- [MODIFY] `frontend/src/components/ChartGrid/ChartGrid.tsx` (+5: toolbar `<StockSearchBox>` mount + onSelectStock 시 timeframe 동반 전달)
- [MODIFY] `frontend/src/AppContent.tsx` (+15: `selectedStock` + `selectedTimeframe` state, `<StockSearchModal>` 호스트, `handleModalClose`에서 input clear 위임, **`React.memo(ChartGrid)` 적용 — I-6 R-2 주(主) mitigation**)

### Files NOT to modify (anti-regression invariant)
- `frontend/src/components/ChartGrid/ChartCell.tsx`
- `frontend/src/contexts/ScreenContext.tsx`
- `frontend/src/components/FilterBar/FilterBar.tsx`
- `frontend/src/types/market.ts`

---

## Acceptance Scenarios (Given/When/Then summary)

### Module: Stocks Master
- **AC-DATA-001** (must-pass): 정상 200 + `{stocks, generated_at}` + ETag + Cache-Control + name NULL 제외 + name ascending 정렬.
- **AC-DATA-002** (must-pass): 빈 stock_meta → 503 `stock_meta_not_ready`.
- **AC-DATA-003** (must-pass): stock_meta 테이블 부재 → 503 + bare except 아님.
- **AC-DATA-004** (must-pass): SELECT-only invariant — `mode=ro` URI 사용.

### Module: Hangul Util
- **AC-SEARCH-005**: 초성 추출 — 삼성전자 → ㅅㅅㅈㅈ / 한화솔루션 → ㅎㅎㅅㄹㅅ / A → A / 1 → 1 / 쌍방울 → ㅆㅂㅇ.
- **AC-SEARCH-006**: matchesQuery 4단계 score (1~4) + 동점 `localeCompare` tiebreaker + lowercase + trim.
- **AC-SEARCH-011 (신규, amendment 1)**: 영문 alias 매칭 score 5 — `samsung` → 삼성전자 / `sk hynix` → SK하이닉스 / 대소문자·trim 정규화 / 사전에 없는 영문은 매치 안 됨.

### Module: useStockMaster Hook
- **AC-SEARCH-002** (must-pass): cachedPromise — 첫 호출 1회 fetch, 재호출·재마운트 추가 fetch 0.
- **AC-SEARCH-007**: 503 응답 → `error: Error('stock_meta_not_ready')`, `data: null`.

### Module: StockSearchBox
- **AC-SEARCH-001**: 한글 prefix 매칭 — `삼` 입력 → 삼성전자 listbox 노출 (debounce 150 ms 후).
- **AC-SEARCH-003**: 필터 우회 — 필터 밖 종목 검색 → modal 표시 + ChartGrid 변경 없음 + `useScreen.request` deep-equal.
- **AC-SEARCH-004**: 초성 검색 — `ㅅㅅㅈㅈ` → 삼성전자.
- **AC-SEARCH-008**: 0건 결과 → `chart-search-empty` 노드 + `aria-disabled="true"`.
- **AC-SEARCH-009**: 503 disabled — input disabled + placeholder `DB 업데이트 필요` + title tooltip.
- **AC-SEARCH-010**: 키보드 navigation — ArrowDown/Up wrap-around / Enter select / Escape clear / Tab focus next.
- **AC-SEARCH-012 (신규, amendment 1)**: modal 닫힘 시 `chart-search-input` value=`''` 자동 초기화 + listbox 닫힘. Esc/백드롭/✕ 모든 close 경로에서 동일.

### Module: StockSearchModal
- **AC-MODAL-001** (must-pass MP-4): portal mount — modal은 `document.body` 직속 자식, ChartGrid subtree에 없음.
- **AC-MODAL-002**: a11y — role="dialog" + aria-modal + aria-labelledby + 초기 focus는 `stock-search-modal-content` + scroll lock.
- **AC-MODAL-003**: Esc 닫기 + focus 복귀 + scroll lock 해제.
- **AC-MODAL-004**: 백드롭 클릭 닫기 + modal-content 내부 클릭 stopPropagation.
- **AC-MODAL-005**: ✕ 버튼 닫기.
- **AC-MODAL-006 (I-3)**: timeframe 토글 → `fetchChartData(code, 'weekly')` 1회 호출 (`'D'`/`'W'` 사용 금지) + 차트 인스턴스 reuse.
- **AC-MODAL-007** (must-pass): useEffect 호출 1회 (StrictMode dev 2회 허용).
- **AC-MODAL-008**: race guard cancelled flag — fetch in-flight 중 close 시 destroyed chart setData 0회.
- **AC-MODAL-009 (신규, amendment 1)**: initial timeframe = ChartGrid 마지막 timeframe (snapshot, modal은 context 미구독). prop 미제공 또는 undefined 시 `'daily'` fallback.

### Module: Performance Invariants
- **AC-PERF-001** (must-pass MP-1): ChartGrid commit count — modal 열기/닫기/active 시 baseline 대비 추가 0회.
- **AC-PERF-002** (must-pass MP-2): ChartCell useEffect — modal open/close 동안 count 변화 0.
- **AC-PERF-003** (must-pass MP-3): `useScreen.request` modal 전후 deep-equal.
- **AC-PERF-004**: autocomplete latency ≤ 80 ms (debounce 종료 기준, I-1).

### Module: Architectural
- **AC-ARCH-001** (must-pass MP-4): modal portal scope (AC-MODAL-001 cross-ref).
- **AC-ARCH-002** (must-pass MP-5): 외부 라이브러리 추가 0.
- **AC-ARCH-003**: `StockSearchBox` + `StockSearchModal`에 `useScreen`/`useTab` 미구독.

---

## Exclusions (What NOT to Build)

- EX-1 Theme → ChartGrid 진입 (이전 SPEC Feature A 전체)
- EX-2 검색 결과 → ChartGrid 필터 주입
- EX-3 appliedContext chip / mismatch banner / FilterBar 검색 chip
- EX-4 검색 기록 / 최근 검색 / 인기 종목
- EX-5 Fuzzy matching, 오타 보정
- EX-6 매치 텍스트 highlight (굵게/색상)
- EX-7 debounce 시간 조정 / 적응형
- (EX-8) Q-1 → v1.0 채택으로 이동 (영문 alias 50종 포함)
- **EX-9 Cmd/Ctrl+K 글로벌 단축키 (Q-2 결정)**
- **EX-10 ChartGrid empty state "검색해보기" 링크 (Q-3 결정)**
- EX-11 URL deep linking (SPEC-TAB-URL-001로 분리)
- **EX-12 DbUpdateButton → cachedPromise reset 연동 (Q-6 결정)**
- EX-13 백엔드 in-memory TTL 캐시
- EX-14 신규 pip / npm 의존성
- EX-15 ETF / 해외종목 / 5만 종목 규모 scaling
- EX-16 모바일 UX 최적화

---

## TDD Task Sequence (amendment 1: T2b, T5a 추가)

| T# | Task | Files | Dependency |
| --- | --- | --- | --- |
| T1 | Backend stocks endpoint | B1, B2, B3, B4 | (독립) |
| T2 | Hangul utility (score 1~4) | F1, F2 | (독립, T1과 병렬 가능) |
| **T2b** | **English alias 50종 사전 + score 5 분기 (Q-1)** | **F1b, F2 확장** | **T2** |
| T3 | useStockMaster hook | F3, F4, F5 | T1 |
| T4 | StockSearchBox (`clearInput` imperative handle 포함) | F6, F7 | T2b, T3 |
| T5 | StockSearchModal (`initialTimeframe` prop + AnalysisModal 패턴 답습) | F8, F9 | (T4 이후 권장) |
| **T5a** | **Focus trap helper (Q-5 조건부, AnalysisModal 부재 시)** | **`useFocusTrap.ts` 조건부** | **T5 Pre-check** |
| T6 | Integration (ChartGrid + AppContent, `React.memo(ChartGrid)` 적용 I-6) | F10, F11 | T4, T5(/T5a) |
| T7 | Anti-regression perf RED | F12 | T6 |
| T8 | Anti-regression perf GREEN | F12 (fix) | T7 |

---

## MX Tag Plan

- `StockSearchBox.tsx` — `@MX:ANCHOR` (검색 진입점, fan_in ≥ 2)
- `hangul.ts` — `@MX:NOTE` (한글 초성 산식 + 5단계 score 비즈니스 로직, amendment 1)
- `hangul-aliases.ts` — `@MX:NOTE` (Q-1 50종 사전, 시총·외국인 거래 비중 상위 기준)
- `StockSearchModal.tsx` — `@MX:NOTE` (portal + a11y) + `@MX:WARN` race guard 영역 + `@MX:REASON: archive df3ca36 race`
- `useStockMaster.ts` — `@MX:NOTE` (module-level cachedPromise invariant)
- `stocks_master_service.py` — `@MX:ANCHOR` (`list_stock_master` public API, mode=ro invariant)

---

Version: 1.0.0 (amendment 1)
Last Updated: 2026-05-11
