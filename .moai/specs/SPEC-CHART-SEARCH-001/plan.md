# SPEC-CHART-SEARCH-001 — Implementation Plan

문서 분류: Plan (manager-spec, Phase 1)
SPEC 버전: 1.0.0 (Draft, amendment 1 applied 2026-05-11)
Development mode: TDD (RED → GREEN → REFACTOR)
작성일: 2026-05-11
업데이트: 2026-05-11 (audit iteration 1: I-1~I-6 + Q-1~Q-7 smart defaults)
연관 문서: `spec.md`, `acceptance.md`, `research.md`, `spec-compact.md`

## HISTORY

| 일자 | 변경 |
| --- | --- |
| 2026-05-11 | v1.0.0 초안 작성 (manager-spec) |
| 2026-05-11 | Amendment 1 — I-1~I-6 + Q-1~Q-7 smart defaults 반영. 신규 task T2b(alias 사전), T5a(focus trap helper) 추가. R-2 mitigation에 React.memo 주(主) 기법으로 명시(I-6). timeframe 파라미터 `'daily'/'weekly'` 단일 통일(I-3). |

---

## 1. Implementation Strategy

### 1.1 핵심 결정

| 결정 | 값 | 근거 |
| --- | --- | --- |
| 검색 결과 표시 위치 | `ReactDOM.createPortal(modal, document.body)` 포털 | research §4.3 — ChartGrid 부모 re-render 영향 0 |
| 모달 호스트 컴포넌트 | `AppContent.tsx` (ChartGrid sibling) | research §4.3 — `selectedStock` state를 ChartGrid 외부에 두어 ChartGrid 트리 격리 |
| 검색 매칭 자료구조 | naive array + `filter+sort` | research §5.3 — 2546개 규모에서 trie 이득 측정 불가 |
| 한글 초성 라이브러리 | 자체 구현 (47 LOC) | NFR-CONST-001 — 외부 라이브러리 0 |
| Cherry-pick 절차 | `git show feat/SPEC-CHART-NAV-001:<path> > <path>` 파일 단위 | research §2.3 — monolithic commit conflict 회피 |
| Development methodology | TDD | `.moai/config/sections/quality.yaml` `development_mode: tdd` |

### 1.2 외부 의존성 (변경 0)

| 영역 | 라이브러리 | 비고 |
| --- | --- | --- |
| Backend | `fastapi`, `pydantic`, `sqlite3` (stdlib) | 기존 사용 중 |
| Frontend | `react`, `axios` (있다면 fetch도 가능), `lightweight-charts`, `vitest`, `@testing-library/react` | 기존 사용 중 |
| 한글 매칭 | (자체 구현) | `frontend/src/utils/hangul.ts` |

NFR-CONST-001 강제: `package.json`, `requirements.txt`/`pyproject.toml` diff에서 신규 dependency 0건 확인.

---

## 2. File Change Matrix

### 2.1 Backend (3 new + 1 modify + 1 test new)

| # | 파일 | Delta | LOC (예상) | TDD 단계 | 매핑 REQ |
| --- | --- | --- | --- | --- | --- |
| B1 | `backend/routers/stocks.py` | [NEW] | +52 | T1-GREEN | REQ-DATA-001, REQ-DATA-003 |
| B2 | `backend/services/stocks_master_service.py` | [NEW] | +65 | T1-GREEN | REQ-DATA-002 |
| B3 | `backend/main.py` | [MODIFY] | +2 | T1-GREEN | REQ-DATA-001 (라우터 등록) |
| B4 | `backend/tests/test_stocks_master.py` | [NEW] | +120 | T1-RED | AC-DATA-001 ~ 004 |

### 2.2 Frontend Util (2 new + 2 test new)

| # | 파일 | Delta | LOC | TDD 단계 | 매핑 REQ |
| --- | --- | --- | --- | --- | --- |
| F1 | `frontend/src/utils/hangul.ts` | [NEW] | +60 (archive 47 + alias score 5 분기 +13) | T2-GREEN | REQ-SEARCH-003 (score 1, 5) |
| F1b | `frontend/src/utils/hangul-aliases.ts` (Q-1 신규) | [NEW] | ~50 (50종 mapping) | T2b-GREEN | REQ-SEARCH-003 (score 5 alias) |
| F2 | `frontend/src/utils/__tests__/hangul.test.ts` | [NEW] | +100 (alias 케이스 +20) | T2-RED, T2b-RED | AC-SEARCH-005, 006, 011 (신규) |

> `frontend/src/utils/` 디렉토리 자체가 신규.
> Q-1 결정에 따라 `hangul-aliases.ts`(50종 ko↔en hardcoded 사전) 신규 추가. 50종 selection은 시가총액 상위 + 외국인 거래 비중 상위 기준으로 manager-spec/run 단계에서 최종 확정. JSON 대신 TS export로 type safety 확보.

### 2.3 Frontend API + Hook (2 new + 1 test new)

| # | 파일 | Delta | LOC | TDD 단계 | 매핑 REQ |
| --- | --- | --- | --- | --- | --- |
| F3 | `frontend/src/api/stocks.ts` | [NEW] | +25 | T3-GREEN | REQ-SEARCH-002, REQ-SEARCH-006 |
| F4 | `frontend/src/hooks/useStockMaster.ts` | [NEW] | +42 | T3-GREEN | REQ-SEARCH-002 (cachedPromise) |
| F5 | `frontend/src/hooks/__tests__/useStockMaster.test.ts` | [NEW] | +100 | T3-RED | AC-SEARCH-002, AC-SEARCH-007 |

### 2.4 Frontend Components (2 new + 2 modify + 2 test new)

| # | 파일 | Delta | LOC | TDD 단계 | 매핑 REQ |
| --- | --- | --- | --- | --- | --- |
| F6 | `frontend/src/components/ChartGrid/StockSearchBox.tsx` | [NEW] | ~180 | T4-GREEN | REQ-SEARCH-001, 003, 004, 005, 006 |
| F7 | `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` | [NEW] | +200 | T4-RED | AC-SEARCH-001 ~ 008 |
| F8 | `frontend/src/components/ChartGrid/StockSearchModal.tsx` | [NEW] | ~250 | T5-GREEN | REQ-MODAL-001 ~ 004, REQ-PERF-002 |
| F9 | `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx` | [NEW] | +180 | T5-RED | AC-MODAL-001 ~ 008 |
| F10 | `frontend/src/components/ChartGrid/ChartGrid.tsx` | [MODIFY] | +5 | T6-GREEN | REQ-SEARCH-001 (mount만) |
| F11 | `frontend/src/AppContent.tsx` | [MODIFY] | +15 | T6-GREEN | REQ-MODAL-001, REQ-PERF-001 (modal host) |

### 2.5 Performance Invariant Tests (1 new)

| # | 파일 | Delta | LOC | TDD 단계 | 매핑 REQ |
| --- | --- | --- | --- | --- | --- |
| F12 | `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` | [NEW] | +120 | T7-RED + T8-GREEN | REQ-PERF-001, REQ-PERF-002, MP-1, MP-2 |

### 2.6 합계

- 신규: 11개 파일 (backend 2 + tests 1 + frontend src 6 + frontend tests 4 = 13개. 위 매트릭스 재집계 기준)
- 수정: 3개 파일 (`backend/main.py`, `ChartGrid.tsx`, `AppContent.tsx`)
- 외부 라이브러리 추가: 0

---

## 3. TDD Task Decomposition (T1 ~ T8)

각 task는 RED → GREEN → REFACTOR 사이클을 1회 수행한다. RED 단계에서 작성된 테스트가 실패함을 확인한 후 GREEN으로 진입한다.

### T1: Backend `GET /api/stocks/master` endpoint

| 단계 | 작업 |
| --- | --- |
| RED | `backend/tests/test_stocks_master.py` 작성: 정상 200, 빈 stock_meta 503, stock_meta 부재 503, ETag 헤더 존재, `Cache-Control: max-age=300`, name IS NOT NULL 정렬 검증. pytest fixture로 임시 SQLite DB 생성. |
| GREEN | archive `feat/SPEC-CHART-NAV-001:backend/routers/stocks.py` + `backend/services/stocks_master_service.py` 파일 단위 cherry-pick. `backend/main.py`에 `from backend.routers.stocks import stocks_router` + `app.include_router(stocks_router)` 2 line 추가. |
| REFACTOR | mode=ro URI 검증 (SELECT-only invariant 강제), bare except 없음 확인. |
| Exit | `pytest backend/tests/test_stocks_master.py` 4 PASS. |
| 매핑 | REQ-DATA-001, 002, 003 |

### T2: Hangul utility (초성 추출 + 4단계 매칭)

| 단계 | 작업 |
| --- | --- |
| RED | `frontend/src/utils/__tests__/hangul.test.ts` 작성: `extractInitialConsonants('삼성전자') === 'ㅅㅅㅈㅈ'`, `extractInitialConsonants('한화솔루션') === 'ㅎㅎㅅㄹㅅ'`, ASCII 통과(`'A' → 'A'`), 숫자 통과(`'1' → '1'`). `matchesQuery` 4단계 score 검증 (코드 prefix `'005'` → score 4, 종목명 prefix `'삼성'` → score 3, substring `'전자'` → score 2, 초성 `'ㅅㅅㅈㅈ'` → score 1). 동점 tiebreaker `localeCompare`. |
| GREEN | archive `feat/SPEC-CHART-NAV-001:frontend/src/utils/hangul.ts` 파일 단위 cherry-pick. `(code - 0xAC00) / 588` 알고리즘. |
| REFACTOR | tiebreaker `name.localeCompare(other.name)` 추가가 archive에 없다면 보강. |
| Exit | `npm test -- hangul` PASS. |
| 매핑 | REQ-SEARCH-003 (score 1~4) |

### T2b: English alias dictionary (Q-1 신규 task)

| 단계 | 작업 |
| --- | --- |
| RED | T2 `hangul.test.ts`에 alias 케이스 추가. `matchesQuery({name: '삼성전자', code: '005930'}, 'samsung')` → score 5. `matchesQuery({name: 'SK하이닉스', code: '000660'}, 'sk hynix')` → score 5. 사전에 없는 영문 입력(`'unknown'`)은 score 0 (matched: false). lowercase + trim 정규화 검증. |
| GREEN | `frontend/src/utils/hangul-aliases.ts` 작성. 50종 hardcoded export. 형식: `export const STOCK_ALIASES: Record<string, string[]> = { '삼성전자': ['samsung', 'samsung electronics'], 'SK하이닉스': ['sk hynix'], ... }`. `matchesQuery`에 alias prefix score 5 분기 추가 (입력값을 lowercase + trim 후 alias 사전 lookup → prefix match 확인). 50종 선정 리스트는 spec.md REQ-SEARCH-003 alias 사양 + manager-spec/run 단계 확정. |
| REFACTOR | alias 사전 lookup을 효율화 — Map 또는 reverse-index. 단, 50종 규모에서는 linear scan도 < 1 ms이므로 yagni 허용. |
| Exit | `npm test -- hangul` (alias 케이스 포함) PASS. AC-SEARCH-011 PASS. |
| 매핑 | REQ-SEARCH-003 (score 5 alias), AC-SEARCH-011 |

### T3: `useStockMaster` hook + API

| 단계 | 작업 |
| --- | --- |
| RED | `frontend/src/hooks/__tests__/useStockMaster.test.ts` 작성: 첫 호출 시 `fetchStockMaster` 1회 호출, 동일 hook 재호출 시 추가 fetch 0, 503 응답 시 `error: Error('stock_meta_not_ready')` 노출, ETag 헤더 mock. |
| GREEN | archive `feat/SPEC-CHART-NAV-001:frontend/src/api/stocks.ts` + `frontend/src/hooks/useStockMaster.ts` cherry-pick. module-level `cachedPromise` 보존. |
| REFACTOR | TypeScript strict 모드 호환 확인. |
| Exit | `npm test -- useStockMaster` PASS. |
| 매핑 | REQ-SEARCH-002, REQ-SEARCH-006 |

### T4: `StockSearchBox` component

| 단계 | 작업 |
| --- | --- |
| RED | `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` 작성. 시나리오: 입력 → debounce 150 ms 대기 → listbox 후보 노출. "삼" 입력 → 삼성전자 prefix 매치 score 3. "005" → 005930 등 코드 매치 score 4. "ㅅㅅㅈㅈ" → 삼성전자 초성 매치 score 1. 0건 → "검색 결과 없음". 503 → input disabled + placeholder "DB 업데이트 필요". ArrowDown/ArrowUp/Enter/Escape 키보드 navigation. `onSelect` prop 호출 검증. |
| GREEN | archive `StockSearchBox.tsx`(154 LOC) 기반으로 신규 작성. 변경: `useTab` import 제거, `navigateToTab` 호출 제거, `onSelect: (item: StockMasterItem) => void` prop 추가. 키보드 navigation 신규 추가(ArrowDown/Up/Enter/Escape + `aria-activedescendant`). a11y aria 속성 보강(`aria-autocomplete="list"`, `aria-controls`, `aria-expanded`). debounce 150 ms 유지. MAX_RESULTS=8 유지. |
| REFACTOR | useMemo 도입 검토 (매 debounce tick마다 sort+slice 비용 측정 후). a11y `aria-live` "검색 결과 N건" 영역 추가. |
| Exit | `npm test -- StockSearchBox` PASS. |
| 매핑 | REQ-SEARCH-001 ~ 006 |

### T5: `StockSearchModal` component

| 단계 | 작업 |
| --- | --- |
| RED | `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx` 작성. 시나리오: portal mount → `document.body` 자식으로 modal 노드 존재 검증 (MP-4). Esc 키 → onClose 호출. 백드롭 클릭 → onClose. 닫기 버튼 클릭 → onClose. `role="dialog" aria-modal="true"`. 초기 focus는 `stock-search-modal-content` (I-4 row 14). focus trap(Tab key가 modal 밖으로 나가지 않음). modal 닫힐 때 trigger ref로 focus 복귀(mock `triggerRef`). modal initial timeframe은 prop으로 전달된 ChartGrid 마지막 timeframe 계승 (없으면 `'daily'`) — AC-MODAL-009. timeframe 토글 → 새 fetch 호출, API 파라미터 `'daily'/'weekly'` (I-3). 차트 useEffect는 modal 열림당 1회만 호출(REQ-PERF-002 검증, `console.count` mock). |
| GREEN | 신규 작성. `ReactDOM.createPortal(<div>...modal markup...</div>, document.body)`. `frontend/src/components/AnalysisModal.tsx:810`, `frontend/src/components/AiReportModal.tsx:340` 마크업 패턴 답습 (Q-5: 기존 모달 scaffolding 채택). modal-content `<div tabIndex={-1} data-testid="stock-search-modal-content">`. lightweight-charts 인스턴스를 modal body에 자체 mount. 차트 useEffect는 dep `[selectedStock.code, timeframe]`, 본문에 cancelled flag 패턴(archive `df3ca36`). Initial timeframe은 prop `initialTimeframe: 'daily' \| 'weekly'`로 받는다 (Q-7 I-2). |
| REFACTOR | scroll lock(body `overflow:hidden`) on/off. modal close handler에 `onClose()` 콜백 호출 + StockSearchBox input clear 신호 위임 (Q-4 REQ-MODAL-002 step 4) — AppContent host가 `selectedStock = null` + `clearSearchInput` 양쪽 처리. |
| Exit | `npm test -- StockSearchModal` PASS (AC-MODAL-001~009 + AC-MODAL-010). |
| 매핑 | REQ-MODAL-001 ~ 004, REQ-PERF-002, Q-7 timeframe, Q-4 input clear |

### T5a: Focus trap helper (Q-5 — 기존 AnalysisModal 패턴 확인 후 결정)

| 단계 | 작업 |
| --- | --- |
| Pre-check | `frontend/src/components/AnalysisModal.tsx` + `AiReportModal.tsx`를 정독하여 기존 focus trap 구현이 존재하는지 확인. 존재 시 그대로 답습, 부재 시 본 task로 신규 헬퍼 작성. |
| RED (조건부) | 기존 모달이 focus trap 미구현 시 신규 헬퍼 `frontend/src/components/ChartGrid/useFocusTrap.ts` 단위 테스트 작성. Tab 순환 / Shift+Tab 역순환 / modal 외부 focusable 무시. |
| GREEN (조건부) | `useFocusTrap(modalContentRef)` 훅 작성. ~30 LOC. modal mount 시 first focusable element 찾기 → Tab keydown event 가로채기 → first/last 순환. |
| REFACTOR | T5 `StockSearchModal`에서 `useFocusTrap` 호출 통합. 기존 AnalysisModal에도 적용 가능하지만 본 SPEC scope 밖 (refactor 별도 SPEC). |
| Exit | AC-MODAL-002 focus trap 시나리오 PASS. |
| 매핑 | NFR-A11Y-001, Q-5 |

### T6: Integration into `ChartGrid` + `AppContent`

| 단계 | 작업 |
| --- | --- |
| RED | `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx`의 일부 시나리오 작성 (selectedStock state 전달, modal mount 위치 검증). DOM scope assertion: ChartGrid container 내부에 `data-testid="stock-search-modal"` 없음 (MP-4). AC-MODAL-009 — modal mount 시 initialTimeframe이 ChartGrid 현재 timeframe과 일치. AC-SEARCH-012 — modal close 후 search input 값 비어있음 (Q-4). |
| GREEN | `ChartGrid.tsx`: toolbar 좌측에 `<StockSearchBox onSelect={props.onSelectStock} ref={searchBoxRef} />` 추가, `onSelectStock` prop 수신. ChartGrid의 현재 `timeframe` state를 `props.onSelectStock(stock, currentTimeframe)` 시그니처로 함께 전달하거나, 또는 `props.currentTimeframeRef` read-only ref로 expose (선택은 GREEN 단계). 그 외 ChartGrid 로직 변경 0. `AppContent.tsx`: `const [selectedStock, setSelectedStock] = useState<StockMasterItem \| null>(null);` + `const [selectedTimeframe, setSelectedTimeframe] = useState<'daily' \| 'weekly'>('daily');` 추가. `<ChartGrid onSelectStock={(stock, tf) => { setSelectedStock(stock); setSelectedTimeframe(tf ?? 'daily'); }} />`. `{selectedStock && <StockSearchModal stock={selectedStock} initialTimeframe={selectedTimeframe} onClose={handleModalClose} />}` 조건부 렌더. `handleModalClose`는 `selectedStock=null` + `searchBoxRef.current?.clearInput()` 호출 (Q-4). |
| REFACTOR (I-6 주(主) mitigation) | **`React.memo`를 `ChartGrid` 컴포넌트에 적용** — `AppContent`의 `selectedStock` state 변경이 ChartGrid subtree로 전파되지 않도록 referential equality 보존. props로 전달되는 `onSelectStock`은 `useCallback`으로 안정화. ChartGrid 내부의 children에 전달되는 prop도 `useCallback`/`useMemo`로 referential equality 유지. 이는 R-2 (AppContent re-render → modal subtree 리렌더) 차단의 **주 기법**이며, `useCallback` 단독으로는 충분치 않다 (R-2 mitigation은 §6 참조). |
| Exit | `npm test -- ChartGrid` 회귀 PASS + 신규 통합 테스트 PASS + AC-MODAL-009 + AC-SEARCH-012 PASS. |
| 매핑 | REQ-SEARCH-001, REQ-MODAL-001 (timeframe lifting), REQ-PERF-001, Q-4 input clear, Q-7 timeframe inherit |

### T7: Anti-regression performance tests (RED)

| 단계 | 작업 |
| --- | --- |
| RED | `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` 본격 작성. 시나리오: (a) React Profiler API로 ChartGrid commit count 측정 baseline → modal 열기 → ChartGrid scroll → modal 닫기. baseline 대비 추가 commit 0회 검증(MP-1). (b) ChartCell mock의 useEffect 호출 횟수 측정 — modal open/close 동안 추가 호출 0(MP-2). (c) `useScreen().screenState.request` deep-equal 검증(MP-3). |
| Exit | RED 테스트가 의도대로 실패하는지 확인 (T6에서 작성한 통합 코드가 이미 실패 또는 PASS 중 하나). 이 단계의 목표는 invariant lock-in. |
| 매핑 | REQ-PERF-001, REQ-PERF-002, MP-1, MP-2, MP-3 |

### T8: Anti-regression performance — GREEN/REFACTOR

| 단계 | 작업 |
| --- | --- |
| GREEN | T7에서 실패하는 테스트를 PASS로 만들기 위한 미세 조정. 주로 `useCallback` / `useMemo` / portal 호스트 위치 보정. |
| REFACTOR | StrictMode dev에서 ChartCell useEffect 2회 호출 케이스 명시적 허용 — instrumentation에서 `process.env.NODE_ENV === 'development'` 분기. modal 차트 useEffect의 cancelled flag 패턴 검증. |
| Exit | T7 4개 시나리오 + T1~T6 회귀 모두 PASS. 자동완성 latency 단위 테스트 PASS (NFR-PERF-001). |
| 매핑 | REQ-PERF-001, REQ-PERF-002, NFR-PERF-001, NFR-PERF-002 |

### 3.1 Task 순서 그래프 (amendment 1: T2b, T5a 추가)

```
T1 (backend) ──┐
T2 (hangul) ───→ T2b (alias) ──┐
                               ├─→ T3 (hook) ──→ T4 (SearchBox) ──→ T6 (integration) ──→ T7 (perf RED) ──→ T8 (perf GREEN)
T1 ────────────────────────────┘                              ↗
                                                              │
                                T5 (Modal) ────→ T5a (focus trap helper, 조건부) ┘
```

- T1·T2는 독립이므로 병렬 가능.
- T2b는 T2 의존 (alias 사전 + matchesQuery score 5 분기는 T2 이후).
- T3은 T1(API endpoint)에 의존.
- T4는 T2b·T3 의존.
- T5는 독립적이지만 lightweight-charts 패턴 검증 위해 T4 이후 권장.
- T5a는 T5 Pre-check 단계에서 기존 AnalysisModal이 focus trap을 가지지 않을 때만 진행. 가진 경우 T5a skip하고 T5 REFACTOR에서 그대로 답습.
- T6은 T4·T5(·T5a) 모두 의존.
- T7·T8은 T6 이후.

---

## 4. MX Tag Plan

| 파일 | 태그 | 사유 |
| --- | --- | --- |
| `frontend/src/components/ChartGrid/StockSearchBox.tsx` | `@MX:ANCHOR` | ChartGrid 검색 진입점. ChartGrid + AppContent 양쪽에서 참조 가능 (fan_in ≥ 2 예상). public prop 인터페이스(`onSelect`). |
| `frontend/src/utils/hangul.ts` | `@MX:NOTE` | `(code - 0xAC00) / 588` 산식 + 4단계 score 매칭 — 도메인 비즈니스 로직. 참조: Wikipedia Hangul Syllables. |
| `frontend/src/components/ChartGrid/StockSearchModal.tsx` | `@MX:NOTE` + `@MX:WARN` (race guard 영역) | (a) portal mount + z-index/scroll lock/focus management — 복잡 invariant. (b) cancelled flag 패턴 영역은 `@MX:WARN` + `@MX:REASON: archive df3ca36 race race`. |
| `frontend/src/hooks/useStockMaster.ts` | `@MX:NOTE` | module-level `cachedPromise` — SPA 세션 1회 fetch invariant. 향후 `DbUpdateButton` 연동(Q-6) 시 reset 분기 위치. |
| `backend/services/stocks_master_service.py` | `@MX:ANCHOR` | `list_stock_master` public API. mode=ro URI invariant. |

MX tag는 RED → GREEN → REFACTOR 사이클의 GREEN/REFACTOR 단계에서 추가한다. RED 단계의 테스트 자체는 `@MX:TODO` 사용 가능(테스트 작성 → GREEN 통과 시 제거).

---

## 5. Reference Implementations (research에서 발견)

run phase에서 다음 file:line 코드 패턴을 그대로 답습한다.

| 패턴 | 참조 위치 | 사용 시 |
| --- | --- | --- |
| `ReactDOM.createPortal(modal, document.body)` | `frontend/src/components/AnalysisModal.tsx:810` | T5 modal portal mount |
| `role="dialog" aria-modal="true" aria-labelledby` | `frontend/src/components/AnalysisModal.tsx:757-758` | T5 a11y |
| Esc 키 onClose | `frontend/src/components/AnalysisModal.tsx:738` (Esc handler 패턴) | T5 keyboard close |
| 백드롭 클릭 close | `frontend/src/components/AnalysisModal.tsx`, `AiReportModal.tsx:340` | T5 |
| `useCallback` for stable handler | `frontend/src/components/ChartGrid/ChartGrid.tsx:56` (`handlePageChange`) | T6 `onSelectStock` |
| cancelled flag race guard | archive commit `df3ca36` `ChartCell.tsx:+6` | T5 modal chart useEffect |
| `read-only sqlite URI` | archive `backend/services/stocks_master_service.py` | T1 |
| ETag from `MAX(last_updated)` | archive `backend/routers/stocks.py` | T1 |

---

## 6. Risks + Mitigation

research §8에서 식별된 risk를 acceptance 시나리오로 lock-in한다.

| Risk | 출처 | Mitigation 위치 | Severity |
| --- | --- | --- | --- |
| R-1: 모달 차트도 부모 re-render로 fetch race 발생 | research §4.4 | T5 cancelled flag 패턴 + T7 perf 테스트(MP-2) | High |
| R-2: AppContent 자체 re-render 시 modal subtree 리렌더 | research §4.3 잔여 위험 | **주(主) mitigation (I-6): `React.memo`를 `ChartGrid` 컴포넌트에 적용** — AppContent의 `selectedStock`/`selectedTimeframe` state 변경이 ChartGrid subtree를 흔들지 않도록 referential equality로 차단. 보조: ChartGrid에 전달되는 child props(`onSelectStock` 등)을 `useCallback`/`useMemo`로 안정화. 추가: StockSearchModal 내부에서 useScreen·useTab 직접 구독 금지(AC-ARCH-003). 검증: T6 React Profiler commit count 측정 + MP-1 must-pass. | High |
| R-3: 동점 score 정렬 불안정 → 결과 순서 흔들림 | research §8.10 | T2 REFACTOR에서 `localeCompare` tiebreaker 추가 | Medium |
| R-4: 한글 복자모 매칭 누락 (ㅅ → ㅆ) | research §8.7 | 본 SPEC v1.0.0은 archive 그대로. 사용자 피드백 후 v2에서 보완. | Low |
| R-5: focus trap 구현 누락 | research §6.3 a11y | T5 REFACTOR Q-5 결정 후 적용 | Medium |
| R-6: 모바일 toolbar 가로 스크롤 (220 px input 추가) | research §8.9 | EX-16으로 scope 밖. 데스크탑 우선. | Low |
| R-7: archive cherry-pick conflict | research §2.3 | 파일 단위 `git show`로 우회 | Low |
| R-8: 모달 호스트가 ChartGrid 자식이 되면 격리 invariant 깨짐 | research §4.3 | T6에서 AppContent에 modal 마운트, MP-4 DOM scope 테스트로 강제 | Critical |
| R-9: `cachedPromise` 무효화 시점 미정 (DB 업데이트 후) | research §7.3 | Q-6 미해결. v1.0.0은 SPA 세션 1회 fetch로 ship, 후속 amendment에서 보완. | Medium |

---

## 7. Verification Strategy

### 7.1 Unit (Vitest + pytest)

- Backend: `pytest backend/tests/test_stocks_master.py` (T1)
- Frontend hangul: `npm test -- hangul` (T2)
- Frontend hook: `npm test -- useStockMaster` (T3)
- Frontend component: `npm test -- StockSearchBox StockSearchModal` (T4, T5)
- Frontend perf: `npm test -- ChartGrid.perf` (T7, T8)

### 7.2 Integration (vitest, JSDOM)

- T6 integration test: ChartGrid + AppContent 함께 마운트, 검색 선택 → modal 마운트 위치 검증.

### 7.3 Manual / e2e (optional Playwright)

- 시나리오 1: 검색 → 선택 → 모달 → Esc 닫기 → focus 복귀
- 시나리오 2: 503 응답 시 input disabled + tooltip
- 시나리오 3: ChartGrid scroll FPS 측정 (DevTools Performance)

### 7.4 라이브 검증 (ship 후 2주)

- §3.3 만족 신호 측정
- §3.4 폐기 기준 위반 시 rollback 검토

---

## 8. Rollback Strategy

본 SPEC ship 후 사용자 가치 재평가에서 폐기 결정 시:

1. 새 git branch에서 작업했다면 `chore/integrated-main-merge-2026-04-25`로 checkout.
2. 작업 branch는 `feat/SPEC-CHART-SEARCH-001` 명명, 9 commits 이내 archive 보존(SPEC-CHART-NAV-001 패턴 답습).
3. `.moai/specs/SPEC-CHART-SEARCH-001/` 산출물은 chore 브랜치에 남기되 `spec.md` frontmatter `status: Rolled-back` 갱신.
4. `retrospective.md` 신규 작성.
5. `lessons.md` 신규 lesson 추가 (Lesson #8 후보).

archive 활용: 모달 격리 패턴이 검증되었다면 그 자체는 재사용 가능 자산이므로 별도 SPEC에서 재호출 가능.

---

## 9. Acceptance Gate (manager-quality 위임)

T1 ~ T8 완료 후 다음을 manager-quality 또는 evaluator-active에 위임:

- [ ] TRUST 5 Tested: 85% 이상 coverage (신규 코드 한정)
- [ ] TRUST 5 Readable: ruff / eslint clean
- [ ] TRUST 5 Unified: black / prettier 통과
- [ ] TRUST 5 Secured: SELECT-only (REQ-DATA-002) 강제, bare except 0
- [ ] TRUST 5 Trackable: conventional commit + SPEC ID 참조
- [ ] MP-1 ~ MP-5 must-pass 검증
- [ ] NFR-PERF-001 ~ 005 측정 결과 acceptance.md에 기록

---

## 10. Decisions Resolved (Annotation cycle iteration 1)

`spec.md §9 v1.0 Decisions` 표 참조. Q-1 ~ Q-7 7건 일괄 smart default 적용 완료. status `Draft` 유지(amendment 1 적용 후 run phase 진입 가능).

| Q | 결정 | plan.md 반영 위치 |
| --- | --- | --- |
| Q-1 | alias 사전 50종 채택 | T2b 신규 task, F1b 신규 파일 |
| Q-2 | Cmd/Ctrl+K 제외 | (작업 없음) |
| Q-3 | empty state 링크 제외 | (작업 없음) |
| Q-4 | modal close → input 초기화 | T5 REFACTOR + T6 GREEN(`handleModalClose`) |
| Q-5 | AnalysisModal 패턴 답습 + focus trap 헬퍼 조건부 신규 | T5 GREEN + T5a 조건부 task |
| Q-6 | DbUpdateButton cache invalidation 제외 | (작업 없음) |
| Q-7 | modal initial timeframe = ChartGrid 마지막 | T5 GREEN(`initialTimeframe` prop) + T6 GREEN(`selectedTimeframe` state lifting) |

---

Version: 1.0.0
Last Updated: 2026-05-11
