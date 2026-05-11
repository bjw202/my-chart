# SPEC-CHART-SEARCH-001 — Acceptance Criteria

문서 분류: Acceptance (TDD scenarios)
SPEC 버전: 1.0.0 (amendment 1 applied 2026-05-11)
Development methodology: TDD
작성일: 2026-05-11
업데이트: 2026-05-11 (audit iteration 1: I-3 timeframe param 통일, 신규 AC-SEARCH-011/012/AC-MODAL-009 추가)
연관 문서: `spec.md`, `plan.md`, `research.md`, `spec-compact.md`

## HISTORY

| 일자 | 변경 |
| --- | --- |
| 2026-05-11 | v1.0.0 초안 작성 |
| 2026-05-11 | Amendment 1 — 신규 AC 3건 추가 (AC-SEARCH-011 영문 alias / AC-SEARCH-012 modal close → input clear / AC-MODAL-009 timeframe 계승). I-3 적용: AC-MODAL-006의 `'W' (또는 weekly)` 표기를 `'weekly'`로 단일 통일 (backend `backend/routers/chart.py:21` 확인). |

---

## Conventions

- 모든 시나리오는 **Given / When / Then** 형식.
- `must-pass` 표기는 다른 기준으로 보상 불가.
- `data-testid` 값은 `spec.md §4 UI Element Mapping`과 1:1 일치.
- 각 시나리오는 unit (vitest/pytest) 또는 integration 단위에서 자동화 가능해야 한다.

---

## 1. Module: Stocks Master Data Endpoint (REQ-DATA-001 ~ 003)

### AC-DATA-001 (must-pass) — 정상 200 응답 + 정렬 + 헤더

REQ 매핑: REQ-DATA-001, REQ-DATA-002

**Given**
- 임시 SQLite DB에 `stock_meta(code, name, market, last_updated)` 테이블 생성.
- 3개 row 삽입: `('005930', '삼성전자', 'KOSPI', '2026-05-10T18:00')`, `('000660', 'SK하이닉스', 'KOSPI', '2026-05-10T18:00')`, `('035720', null, 'KOSPI', '2026-05-10T18:00')` (name NULL 케이스).

**When**
- 클라이언트가 `GET /api/stocks/master` 호출.

**Then**
- HTTP 상태 200.
- 응답 body schema: `{ stocks: [...], generated_at: <ISO-8601 KST string> }`.
- `stocks` 배열 length === 2 (name NULL row 제외).
- 정렬: `[SK하이닉스, 삼성전자]` (name ascending — `localeCompare` 또는 SQLite collation 기준).
- 응답 헤더에 `ETag: "2026-05-10T18:00"` 존재.
- 응답 헤더에 `Cache-Control: max-age=300` 존재.

**Edge case**
- 같은 `last_updated`를 가진 row가 다수일 때 ETag는 단일 값.
- 한글 이름과 영문 이름 혼재 시 ASCII 우선 정렬 vs 한글 우선 정렬은 SQLite 기본(BINARY)에 위임. 본 SPEC은 이 정책을 변경하지 않는다.

---

### AC-DATA-002 (must-pass) — stock_meta 빈 테이블 → 503

REQ 매핑: REQ-DATA-003

**Given**
- 임시 SQLite DB에 `stock_meta` 테이블은 생성되었으나 row 0건.

**When**
- 클라이언트가 `GET /api/stocks/master` 호출.

**Then**
- HTTP 상태 503.
- 응답 body: `{"detail": "stock_meta_not_ready"}`.

**Edge case**
- name이 모두 NULL인 경우(row는 있으나 WHERE 절 통과 0): 같은 503 반환.

---

### AC-DATA-003 (must-pass) — stock_meta 테이블 부재 → 503

REQ 매핑: REQ-DATA-003

**Given**
- 임시 SQLite DB에 `stock_meta` 테이블 자체가 존재하지 않음 (다른 테이블만 존재).

**When**
- 클라이언트가 `GET /api/stocks/master` 호출.

**Then**
- HTTP 상태 503.
- 응답 body: `{"detail": "stock_meta_not_ready"}`.
- 백엔드 로그에 `sqlite3.OperationalError: no such table: stock_meta` catch 흔적 (bare except 아님).

---

### AC-DATA-004 — SELECT-only invariant (must-pass)

REQ 매핑: REQ-DATA-002, NFR-CONST-002

**Given**
- `stocks_master_service.py`의 SQLite connect 호출 코드를 정적 분석한다.

**When**
- `sqlite3.connect(...)` 인자를 검사.

**Then**
- URI 형식 `file:<path>?mode=ro` 사용. `uri=True` 키워드 인자 포함.
- 또는 동일 효과의 read-only 보장 메커니즘.

**실패 path 검증 (선택)**
- 임시 DB에 connect → 서비스 함수 내부에서 INSERT 시도 → `sqlite3.OperationalError` 발생 (read-only).

---

## 2. Module: Hangul Matching Utility (REQ-SEARCH-003)

### AC-SEARCH-005 — 초성 추출 정확성

REQ 매핑: REQ-SEARCH-003 (score 1)

**Given**
- `extractInitialConsonants(s: string): string` import.

**When / Then (case table)**

| 입력 | 출력 |
| --- | --- |
| `'삼성전자'` | `'ㅅㅅㅈㅈ'` |
| `'한화솔루션'` | `'ㅎㅎㅅㄹㅅ'` |
| `'A'` | `'A'` (ASCII 통과) |
| `'1'` | `'1'` (숫자 통과) |
| `'삼A1'` | `'ㅅA1'` (mixed) |
| `''` | `''` |
| `'쌍방울'` | `'ㅆㅂㅇ'` (ㅆ — 19자 중 4번째 index) |

**Edge case**
- 한자(`'株式'`) 통과 — 0xAC00 ~ 0xD7A3 범위 밖이므로 그대로.

---

### AC-SEARCH-006 — `matchesQuery` 4단계 score + 동점 tiebreaker

REQ 매핑: REQ-SEARCH-003

**Given**
- `matchesQuery(item: StockMasterItem, query: string): { matched: boolean; score: number }` import.
- mock items: `[{code: '005930', name: '삼성전자'}, {code: '000660', name: 'SK하이닉스'}, {code: '005490', name: 'POSCO홀딩스'}]`.

**When / Then (시나리오)**

| 입력 query | 기대 결과 |
| --- | --- |
| `'005'` | `005930` score 4, `005490` score 4 — 동점 → `name.localeCompare` → POSCO홀딩스 → 삼성전자 순서 |
| `'삼성'` | `삼성전자` score 3 |
| `'전자'` | `삼성전자` score 2 (substring) |
| `'ㅅㅅㅈㅈ'` | `삼성전자` score 1 |
| `'xyz'` | matched: false (모든 item) |
| `''` | matched: false 또는 무시 (UI에서 empty input은 listbox close 처리) |

**Edge case**
- 대소문자 — `'SK'`와 `'sk'` 모두 SK하이닉스 매칭 (lowercase 비교).
- 공백 trim — `'  005  '` → `'005'` 동일 결과.

---

## 3. Module: `useStockMaster` Hook (REQ-SEARCH-002, 006)

### AC-SEARCH-002 (must-pass) — SPA 세션 1회 fetch + cachedPromise

REQ 매핑: REQ-SEARCH-002

**Given**
- mocked `fetch('/api/stocks/master')` 반환 `{ stocks: [...], generated_at: '...' }`.
- vitest spy on `fetchStockMaster`.

**When**
- React component A에서 `useStockMaster()` 호출.
- 같은 세션, 다른 component B에서 `useStockMaster()` 호출.
- A 컴포넌트 unmount → 다시 mount → `useStockMaster()` 호출.

**Then**
- `fetchStockMaster` spy.call.count === 1.
- A·B 두 컴포넌트 모두 동일 `data` 객체 reference 수신 (cachedPromise resolve 결과 reuse).

**Edge case**
- vitest `beforeEach`로 module reset 시 cachedPromise도 reset (cross-test 오염 방지).

---

### AC-SEARCH-007 — 503 응답 시 `error: stock_meta_not_ready` 노출

REQ 매핑: REQ-SEARCH-002, REQ-SEARCH-006

**Given**
- mocked `fetch('/api/stocks/master')` 503 응답 + `{detail: 'stock_meta_not_ready'}`.

**When**
- `useStockMaster()` 호출.

**Then**
- hook 반환: `{ data: null, loading: false, error: Error('stock_meta_not_ready'), dispatched: true }`.

**Edge case**
- 네트워크 오류(`fetch` reject): error는 `Error('network_error')` 또는 원본 에러. 정확한 메시지는 implementation에서 결정하되 `data`는 null.

---

## 4. Module: `StockSearchBox` Component (REQ-SEARCH-001, 003, 004, 005, 006)

### AC-SEARCH-001 — 정상 시나리오: 한글 입력 → prefix 매치

REQ 매핑: REQ-SEARCH-001, 003

**Given**
- ChartGrid가 마운트되어 있고 `useStockMaster()` 반환값 `{data: [..., {code: '005930', name: '삼성전자', market: 'KOSPI'}, ...]}`.

**When**
- 사용자가 `chart-search-input`에 `삼` 입력.
- 150 ms debounce 경과.

**Then**
- `chart-search-listbox` 마운트.
- `chart-search-option-005930` 노드 존재.
- 최대 8개 option 노출.
- 첫 option은 score 가장 높은 매치 (`삼` prefix → 삼성전자 score 3).

**Edge case**
- 150 ms 이전에 추가 입력 발생 시 debounce 재시작 — 한 번만 setCandidates 호출.

---

### AC-SEARCH-003 — 필터 우회: 필터 밖 종목 검색 → modal 표시

REQ 매핑: REQ-SEARCH-001 + REQ-MODAL-001 + MP-3 (필터 상태 보존)

**Given**
- ChartGrid가 시가총액 ≥ 1조원 필터 적용 상태 (`screenState.request.market_cap_min === 1_000_000_000_000`).
- 검색 대상 종목 `005930` 삼성전자는 현재 필터 결과에 포함됨.
- 검색 대상 종목 `123456` (가상, 시총 100억 소형주)는 현재 필터 결과에 **불포함**.

**When**
- 사용자가 `chart-search-input`에 `123456` 입력 → debounce 경과 → `chart-search-option-123456` 클릭.

**Then**
- `stock-search-modal` 노드가 `document.body` 직계 자식으로 mount.
- modal에 종목 `123456`의 차트가 표시.
- ChartGrid의 표시 종목 list는 **변경 없음** (시가총액 ≥ 1조 종목 그대로 유지).
- `useScreen().screenState.request` 객체가 modal 열기 전후 deep-equal.
- 필터 outside 종목임에도 modal로 차트 표시 가능 (필터 우회 동선 성공).

**Edge case**
- modal 닫은 후 ChartGrid 필터는 여전히 동일 상태.

---

### AC-SEARCH-004 — 초성 검색

REQ 매핑: REQ-SEARCH-003 (score 1)

**Given**
- mock data에 `{code: '005930', name: '삼성전자'}`, `{code: '005380', name: '현대차'}`.

**When**
- 사용자가 `chart-search-input`에 `ㅅㅅㅈㅈ` 입력 → debounce 경과.

**Then**
- `chart-search-option-005930` 노드 존재.
- listbox의 첫 option은 삼성전자.
- `현대차`(ㅎㄷㅊ) option은 노출되지 않음.

---

### AC-SEARCH-008 — 0건 결과 처리

REQ 매핑: REQ-SEARCH-004

**Given**
- mock data 100개.

**When**
- 사용자가 `chart-search-input`에 `xyz존재하지않는검색어` 입력 → debounce 경과.

**Then**
- `chart-search-listbox` 노드 존재.
- `chart-search-empty` 노드 존재, 텍스트 `검색 결과 없음`.
- 일반 `chart-search-option-*` 노드 0개.
- `chart-search-empty`는 `aria-disabled="true"` 속성 보유.

---

### AC-SEARCH-009 — 503 disabled 상태

REQ 매핑: REQ-SEARCH-006

**Given**
- `useStockMaster()` mock이 `{data: null, error: Error('stock_meta_not_ready')}` 반환.

**When**
- `StockSearchBox` 마운트.

**Then**
- `chart-search-input` `disabled` 속성 존재.
- placeholder 텍스트가 `DB 업데이트 필요`.
- input hover 시 `title` 속성에서 `DB 업데이트가 필요합니다` 노출.
- 어떤 키 입력도 candidate dispatch 안 됨.

---

### AC-SEARCH-010 — 키보드 navigation

REQ 매핑: REQ-SEARCH-005

**Given**
- `StockSearchBox`에 후보 3개 (`A`, `B`, `C`) 노출.

**When / Then (시퀀스)**

| 키 입력 | 기대 상태 |
| --- | --- |
| ArrowDown | A 하이라이트 (`aria-activedescendant="chart-search-option-A"`) |
| ArrowDown | B 하이라이트 |
| ArrowDown | C 하이라이트 |
| ArrowDown | A 하이라이트 (wrap-around) |
| ArrowUp | C 하이라이트 (wrap-around) |
| Enter | `onSelect(B 또는 현재 하이라이트 item)` 호출 |
| Escape | listbox 닫힘 + input clear |

**Edge case**
- 후보 0건 상태에서 ArrowDown — no-op.
- Tab — listbox 닫힘 + 다음 focusable 요소로 focus 이동.

---

### AC-SEARCH-011 — 영문 alias 매칭 (Q-1 신규)

REQ 매핑: REQ-SEARCH-003 (score 5)

**Given**
- `frontend/src/utils/hangul-aliases.ts`에 50종 ko↔en 매핑 사전이 export됨. 예: `{ '삼성전자': ['samsung', 'samsung electronics'], 'SK하이닉스': ['sk hynix'] }`.
- mock items에 `{code: '005930', name: '삼성전자'}`, `{code: '000660', name: 'SK하이닉스'}`, `{code: '003490', name: '대한항공'}` (alias 미보유) 포함.

**When (case table)**

| 입력 query | 기대 결과 |
| --- | --- |
| `'samsung'` | 삼성전자 매치, score 5 (alias prefix) |
| `'sk hynix'` | SK하이닉스 매치, score 5 |
| `'SAMSUNG'` | 삼성전자 매치 (lowercase 정규화) |
| `'  samsung  '` | 삼성전자 매치 (trim 정규화) |
| `'samsung electronics'` | 삼성전자 매치 (긴 alias도 prefix로 인식) |
| `'korean air'` | 매치 안 됨 (대한항공은 alias 사전에 없음) |
| `'unknown'` | 매치 안 됨 |
| `'sams'` | 삼성전자 매치 (alias `'samsung'`의 prefix `'sams'`) |

**Then**
- alias prefix 일치 시 score === 5.
- 동일 query가 종목명·코드 prefix와도 일치하면 score 5(alias) 우선 노출. tiebreaker로 `localeCompare`.

**Edge case**
- 사전에 동일 query에 매핑되는 종목이 2개 이상이면 모두 score 5로 노출 + tiebreaker `localeCompare`.

---

### AC-SEARCH-012 — Modal 닫힘 시 input 자동 초기화 (Q-4 신규)

REQ 매핑: REQ-MODAL-002 step 4

**Given**
- 사용자가 `chart-search-input`에 `삼` 입력.
- `chart-search-option-005930` 클릭 → `StockSearchModal` 마운트 (입력값 `삼` 유지 상태에서).

**When (sequence)**

1. 사용자가 Esc 키 입력 → modal 닫힘.
2. focus가 `chart-search-input`으로 복귀.

**Then**
- modal unmount + `selectedStock` === null (AC-MODAL-003 동일).
- `chart-search-input`의 `value` 속성이 빈 문자열 `''`.
- `chart-search-listbox`는 닫힌 상태 (DOM에 없거나 hidden).
- 후속 시나리오: 사용자가 새 검색어 입력 시 정상 동작 (debounce → matchesQuery → 새 listbox).

**Edge case**
- 백드롭 클릭 / ✕ 버튼 클릭 / Esc 모두 동일하게 input 초기화.
- modal-content 내부 클릭으로 닫히지 않는 경우 (AC-MODAL-004 stopPropagation) input 초기화 발생 안 함 — modal 여전히 열림.

---

## 5. Module: `StockSearchModal` Component (REQ-MODAL-001 ~ 004, REQ-PERF-002)

### AC-MODAL-001 — Portal mount + 격리 (must-pass MP-4)

REQ 매핑: REQ-MODAL-001, MP-4

**Given**
- ChartGrid + AppContent 마운트.
- AppContent state `selectedStock: {code: '005930', name: '삼성전자', market: 'KOSPI'}`.

**When**
- `StockSearchModal` 마운트.

**Then**
- `document.body`의 직계 자식 (또는 portal 컨테이너 div의 자식)으로 `data-testid="stock-search-modal"` 노드 존재.
- ChartGrid root (`data-testid="chart-grid"`) subtree 내에는 `stock-search-modal` 노드가 **존재하지 않음**.
- vitest assertion: `within(chartGridRoot).queryByTestId('stock-search-modal') === null`.

**실패 path**
- modal이 ChartGrid 자식으로 마운트되면 MP-4 위반 → 즉시 fail.

---

### AC-MODAL-002 — a11y modal patterns

REQ 매핑: REQ-MODAL-003, NFR-A11Y-001

**Given**
- `StockSearchModal` 열림 상태.

**Then**
- modal container의 속성:
  - `role="dialog"`
  - `aria-modal="true"`
  - `aria-labelledby="stock-search-modal-title"` (또는 동일 id를 가진 헤더에 link)
- 초기 focus는 `stock-search-modal-close-btn` 또는 modal-content (`tabIndex={-1}`).
- `document.body.style.overflow === "hidden"` (scroll lock).

---

### AC-MODAL-003 — Esc 닫기 + focus 복귀

REQ 매핑: REQ-MODAL-002, NFR-A11Y-001

**Given**
- 사용자가 `chart-search-input`에서 `삼` 입력 → `chart-search-option-005930` 클릭 → modal 열림.
- input element에 `triggerRef` 저장됨.

**When**
- 사용자가 modal이 활성화된 상태에서 `Escape` 키 입력.

**Then**
- modal unmount.
- `selectedStock` state === null.
- 키보드 focus가 `chart-search-input`으로 복귀 (vitest `document.activeElement === input`).
- `document.body.style.overflow` scroll lock 해제.

---

### AC-MODAL-004 — 백드롭 클릭 닫기

REQ 매핑: REQ-MODAL-002

**Given**
- modal 열림.

**When**
- 사용자가 `stock-search-modal-backdrop` 노드 클릭.

**Then**
- modal unmount + focus 복귀 (AC-MODAL-003과 동일).
- modal-content 내부 클릭은 닫기를 트리거하지 **않는다** (event stopPropagation 검증).

---

### AC-MODAL-005 — 닫기 버튼

REQ 매핑: REQ-MODAL-002

**Given**
- modal 열림.

**When**
- 사용자가 `stock-search-modal-close-btn` 클릭.

**Then**
- AC-MODAL-003 동일 결과.

---

### AC-MODAL-006 — Timeframe 토글 (I-3 amendment: param 단일 통일)

REQ 매핑: REQ-MODAL-004

**Given**
- modal 열림, 차트 timeframe `'daily'` (UI 라벨 `일봉`).
- mocked `fetchChartData(code, timeframe)` spy.
- timeframe 파라미터 enum: `'daily' | 'weekly'` (backend `backend/routers/chart.py:21` 정의).

**When**
- 사용자가 `stock-search-modal-timeframe-toggle` 클릭 → `주봉` 선택 (internal value `'weekly'`).

**Then**
- `fetchChartData('005930', 'weekly')` 1회 호출.
- 차트 인스턴스는 동일 (`chart.remove()` 호출 0회, `setData()` 호출 1회).
- modal 닫히지 않음.

**Edge case**
- 토글 빠른 연속 클릭 시 마지막 toggle만 fetch 발화 (cancelled flag 패턴).
- `'D'`/`'W'` 표기는 사용 금지 — 어디서든 `'daily'`/`'weekly'` 사용.

---

### AC-MODAL-007 (must-pass) — useEffect 호출 1회 (StrictMode dev 제외 2회)

REQ 매핑: REQ-PERF-002, MP-2 변형

**Given**
- modal 차트의 `useEffect(..., [selectedStock.code, timeframe])` 본문에 `console.count('modal-chart-effect')` instrumentation.

**When**
- selectedStock 한 번 set → modal 열림 → Esc 닫기.

**Then**
- production 빌드 모드: `console.count` === 1.
- StrictMode dev 모드: `console.count` <= 2 허용.

**실패 path**
- ChartGrid 부모 re-render가 modal subtree로 전파되어 effect가 3회+ 호출되면 fail.

---

### AC-MODAL-008 — 차트 race guard (cancelled flag)

REQ 매핑: REQ-PERF-002 (보조)

**Given**
- mocked `fetchChartData`가 200 ms 지연 후 resolve.
- candleSeries.setData spy.

**When**
- modal 열림 → fetch in-flight 중에 timeframe 변경 또는 close.

**Then**
- cleanup 함수의 `cancelled = true` 후 fetch resolve.
- `candleSeries.setData` spy.call.count === 0 (destroyed chart 호출 차단).

---

### AC-MODAL-009 — Initial timeframe = ChartGrid 마지막 timeframe 계승 (Q-7 신규)

REQ 매핑: REQ-MODAL-001 (initial timeframe inheritance)

**Given (case A — ChartGrid의 현재 timeframe이 `'weekly'`)**
- `AppContent.tsx`에서 `selectedTimeframe = 'weekly'` 상태로 모달이 마운트되는 컨텍스트.
- mocked `fetchChartData(code, timeframe)` spy.

**When**
- 사용자가 `StockSearchBox`에서 종목 `005930` 선택 → modal mount.

**Then**
- Modal 마운트 시 첫 `fetchChartData` 호출 인자: `fetchChartData('005930', 'weekly')`.
- Modal 헤더의 timeframe 토글이 `주봉` 활성 상태 표시.
- ChartGrid에서 timeframe state가 `'daily'`로 변경되더라도 modal 차트 인스턴스의 timeframe은 mount snapshot으로 `'weekly'` 유지 (modal은 ChartGrid context 미구독, REQ-PERF-001 invariant 보존).

**Given (case B — ChartGrid timeframe 알 수 없음 또는 prop 미전달)**
- `<StockSearchModal stock={...} initialTimeframe={undefined} />`.

**When**
- modal mount.

**Then**
- Fallback to `'daily'`.
- `fetchChartData('005930', 'daily')` 호출.
- Modal 헤더 `일봉` 활성.

**Edge case**
- modal mount 직후 user가 timeframe 토글 → 정상 동작 (REQ-MODAL-004, AC-MODAL-006).
- AppContent에서 모달 닫기 후 다시 동일 종목 선택 → mount 시점의 ChartGrid timeframe을 다시 snapshot (이전 모달 상태와 무관).

---

## 6. Performance Invariants (Anti-regression must-pass)

### AC-PERF-001 (must-pass MP-1) — ChartGrid 부모 re-render 0회

REQ 매핑: REQ-PERF-001, MP-1

**Given**
- React Profiler API로 ChartGrid commit count 측정 wrapper.
- ChartGrid + AppContent 마운트 → 초기 commit count baseline 기록 (예: 3회).

**When (sequence)**
- (1) modal 열기 (selectedStock set).
- (2) modal 열린 채 ChartGrid scroll/page change 동작.
- (3) modal 열린 채 FilterBar에 키 입력 (submit 없음).
- (4) modal 닫기.

**Then**
- 각 step 후 ChartGrid commit count 비교.
  - step (1) 후: baseline 대비 0회 추가 commit.
  - step (4) 후: baseline 대비 0회 추가 commit.
- step (2)·(3)에서 ChartGrid 자체 동작에 의한 commit은 modal 영향 없음 (baseline ChartGrid scroll commit count와 동일).

**실패 path**
- 어느 step에서든 ChartGrid commit count가 baseline 대비 증가하면 fail.

---

### AC-PERF-002 (must-pass MP-2) — ChartCell useEffect 재실행 0회

REQ 매핑: REQ-PERF-001, MP-2

**Given**
- 기존 `ChartCell.tsx`의 `useEffect(..., [stock.code, timeframe])` 본문에 `console.count('chart-cell-effect')` instrumentation (test setup 단계 spy).
- ChartGrid에 4개 ChartCell 마운트.

**When**
- 초기 마운트 후 baseline `count === 4` 기록.
- modal 열기 → modal 닫기.

**Then**
- modal 열림 후 count === 4 (변화 없음).
- modal 닫힘 후 count === 4 (변화 없음).

**실패 path**
- count 증가 시 ChartGrid 부모 re-render 전파 발생 → MP-2 위반 → fail.

---

### AC-PERF-003 (must-pass MP-3) — 필터 상태 보존

REQ 매핑: REQ-PERF-001, MP-3

**Given**
- `useScreen().screenState.request` 객체 snapshot 보관 (deep clone).

**When**
- modal 열기 → modal 내부에서 timeframe 토글 → modal 닫기.

**Then**
- modal 닫힘 후 `useScreen().screenState.request`가 snapshot과 deep-equal.

---

### AC-PERF-004 — 자동완성 latency ≤ 80 ms

REQ 매핑: NFR-PERF-001

**Given**
- mock data 2546개.
- `performance.now()` 활용 가능한 vitest 환경.

**When**
- `chart-search-input`에 `삼` 입력 → debounce 종료 마크.
- `setCandidates` 호출 직전 / 직후 `performance.now()` diff 측정.

**Then**
- diff <= 80 ms (벤치마크 3회 평균).

**Edge case**
- JSDOM은 실제 V8 JIT 미적용 → 실 측정값보다 보수적. CI 임계값은 150 ms로 완화 가능 (실 브라우저는 < 80 ms 보장).

---

## 7. Architectural Invariants (Anti-regression must-pass)

### AC-ARCH-001 (must-pass MP-4) — Modal은 ChartGrid 외부에 mount

이미 AC-MODAL-001에서 다룸. 본 절은 cross-reference 표기.

---

### AC-ARCH-002 (must-pass MP-5) — 외부 라이브러리 추가 0

REQ 매핑: NFR-CONST-001, MP-5

**Given**
- 본 SPEC ship 전 `package.json` + `requirements.txt`/`pyproject.toml` snapshot.

**When**
- 본 SPEC ship 후 동일 파일 비교.

**Then**
- `dependencies` + `devDependencies` 새 entry 0건.
- pip dependencies 새 entry 0건.

**검증 방법**
- 수동 diff 또는 CI lint (있다면).

---

### AC-ARCH-003 — `StockSearchBox` useScreen/useTab 미구독

REQ 매핑: REQ-PERF-001 (보조)

**Given**
- `StockSearchBox.tsx` 정적 분석.

**Then**
- 파일 내부에서 `useScreen()` 또는 `useTab()` import 또는 호출 0회.
- 만약 import되면 vitest static lint fail.

---

## 8. Definition of Done

다음 항목 **전부 충족** 시 SPEC ship 가능.

- [ ] 모든 Module 1~7 시나리오 vitest/pytest PASS (amendment 1 신규 AC-SEARCH-011 / AC-SEARCH-012 / AC-MODAL-009 포함).
- [ ] AC-DATA-001, AC-DATA-002, AC-DATA-003, AC-DATA-004 PASS (must-pass).
- [ ] AC-SEARCH-002 PASS (must-pass — cachedPromise invariant).
- [ ] AC-PERF-001 / 002 / 003 PASS (must-pass — anti-regression).
- [ ] AC-MODAL-001 PASS (must-pass — portal scope).
- [ ] AC-ARCH-001 / 002 / 003 PASS (must-pass).
- [ ] TRUST 5 quality gates 통과 (manager-quality 위임).
- [ ] `spec.md` frontmatter `status: Implemented` 갱신 (LESSON #6).
- [ ] MX tags 추가 완료 (plan.md §4 기준).
- [ ] Open Question Q-1 ~ Q-7 → annotation cycle iteration 1 (옵션 A)에서 모두 결정됨. spec.md §9 v1.0 Decisions 표 참조.
- [ ] 라이브 사용 가설 (§spec.md §2) ship 후 2주 측정 일정 등록.

---

## 9. Edge Case Catalog

다음은 시나리오에 명시적으로 포함되지는 않았으나 implementation 시 고려해야 하는 케이스. plan phase에서 결정 또는 run phase의 GREEN 단계에서 결정.

| # | 케이스 | 결정 시점 |
| --- | --- | --- |
| EC-1 | 검색 도중 `cachedPromise`가 503으로 resolve된 경우 — 입력 상태 즉시 disabled | T3 REFACTOR |
| EC-2 | modal 열린 채 사용자가 다른 탭으로 이동 (`useTab.activeTab` 변경) — modal stale 처리 | T5/T6 |
| EC-3 | 검색 후 modal 열린 채 `useStockMaster` cachedPromise refresh trigger (없을 예정이지만 향후 Q-6 결정) | future amendment |
| EC-4 | screen reader 사용자에게 "검색 결과 N건" 안내 (`aria-live` 영역) | T4 REFACTOR |
| EC-5 | 모달 차트가 lightweight-charts 인스턴스 destroy 전에 새 fetch resolve — race guard로 차단 | T5 |
| EC-6 | 사용자가 `chart-search-input`에 빠르게 입력+삭제 반복 — 마지막 입력만 dispatch | T4 (debounce reset) |
| EC-7 | 동점 score `localeCompare` 결과가 사용자 의도와 다를 때 — secondary tiebreaker `code` ascending | T2 REFACTOR |
| EC-8 | 한자/일본어 종목명 (CJK extension) 매칭 — 본 SPEC은 한글+ASCII만 보장. CJK는 substring으로 우연 매칭. | EX 처리 |

---

Version: 1.0.0
Last Updated: 2026-05-11
