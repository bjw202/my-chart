# Acceptance Criteria — SPEC-CHART-NAV-001

본 문서는 spec.md §4의 26개 AC에 대해 Given-When-Then 시나리오, 자동/수동 구분, 통과 기준, 라이브 검증 의무를 상세히 풀어 정의한다.

작성일: 2026-05-07
SPEC: `.moai/specs/SPEC-CHART-NAV-001/spec.md` v1.0.0

총 26 AC. 분류:
- A 동선 (테마→그리드): 6개 (AC-A1~A6)
- B 동선 (검색→그리드): 8개 (AC-B1~B8)
- 공통 (mismatch + chip + reset + 회귀): 4개 (AC-C1~C4)
- 백엔드 (/api/stocks/master): 4개 (AC-S1~S4)
- 회귀 (선행 SPEC + cross-tab): 4개 (AC-R1~R4)

---

## A 동선 (Feature A: Theme → Grid)

### AC-A1: ThemeDetailPanel 헤더 버튼 라이브 라벨

- 검증 대상 REQ: REQ-CN-005
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 A)
- **Given** ThemeAnalysis 탭이 활성화되어 있고 사용자가 한 테마(예: "반도체", stocks.length = 12)를 선택하여 ThemeDetailPanel이 렌더링된 상태
- **When** ThemeDetailPanel이 헤더를 렌더한다
- **Then** 헤더 영역에 primary 버튼이 표시되며 라벨은 정확히 `차트 그리드로 보기 (12종목)`이다 (N은 selectedTheme.stocks.length 라이브 값)
- 통과 기준: vitest에서 `screen.getByRole('button', { name: /차트 그리드로 보기 \(12종목\)/ })` 매칭. selectedTheme.stocks이 변경되면 라벨도 즉시 갱신된다.
- 라이브 검증: 시나리오 A에서 사용자가 직접 라벨이 라이브 종목 수와 일치함을 확인.

### AC-A2: 헤더 버튼 클릭 → ChartGrid 진입

- 검증 대상 REQ: REQ-CN-007, REQ-CN-008
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 A)
- **Given** AC-A1의 ThemeDetailPanel 상태이고 selectedTheme.stocks가 stock_meta에 모두 존재하는 경우
- **When** 사용자가 헤더 버튼을 클릭한다
- **Then** (1) navigateToTab이 `('chart-grid', { stockCodes: <theme stock_code 12개>, themeName: '반도체' })`로 호출된다. (2) activeTab이 'chart-grid'로 전환된다. (3) ChartGrid가 12개 종목 차트로 채워진다. (4) ScreenContext.appliedContext = `{ source: 'theme', label: '테마: 반도체 (12)', requestedCodeCount: 12 }`.
- 통과 기준: vitest mock의 navigateToTab 호출 인자 검증. 통합 시나리오에서 ChartGrid의 flatStocks.length === 12 (모든 종목이 stock_meta에 존재하는 경우).

### AC-A3: ThemeRankingTable 행별 chip 클릭

- 검증 대상 REQ: REQ-CN-006, REQ-CN-007
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 B)
- **Given** ThemeAnalysis 탭에서 ThemeRankingTable이 여러 테마 행을 렌더한 상태이고, ThemeDetailPanel은 닫혀있다
- **When** 사용자가 두 번째 테마 행의 trailing cell에 있는 "차트" chip을 클릭한다
- **Then** (1) chip onClick에서 `event.stopPropagation()`이 호출되어 행 click 핸들러(상세 패널 열기)는 발화하지 않는다. (2) navigateToTab이 그 두 번째 테마의 stock_code 목록과 themeName으로 호출된다. (3) ChartGrid가 그 테마 stocks만으로 채워진다.
- 통과 기준: vitest에서 chip click 후 `setSelectedTheme` mock 0회 호출 + navigateToTab mock 1회 호출 (그 테마의 stocks 인자) 검증.
- 라이브 검증: 시나리오 B에서 chip 클릭 시 상세 패널이 열리지 않고 ChartGrid로 즉시 이동함을 확인.

### AC-A4: FilterBar chip 표시 + ✕ reset

- 검증 대상 REQ: REQ-CN-015, REQ-CN-008
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 A)
- **Given** AC-A2 또는 AC-A3 완료 후 ChartGrid 탭에 진입한 상태 (appliedContext.label = "테마: 반도체 (12)")
- **When** FilterBar가 렌더링되고, 그 다음 사용자가 chip의 ✕ 버튼을 클릭한다
- **Then** (1) chip이 `테마: 반도체 (12) ✕` 라벨로 표시된다. (2) ✕ 클릭 시 `clearAppliedContext()` + `applyFilters(DEFAULT_SCREEN_REQUEST)`가 순서대로 호출된다. (3) ChartGrid의 flatStocks가 빈 배열로 비워진다. (4) appliedContext가 null이 되어 chip이 사라진다.
- 통과 기준: `screen.getByTestId('filter-bar-applied-context-chip')` 텍스트 매칭 + ✕ click 후 chip 미렌더 + ChartGrid empty state 검증.

### AC-A5: full reset 검증

- 검증 대상 REQ: REQ-CN-C-006, REQ-CN-016
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 A, G)
- **Given** ChartGrid 진입 전에 FilterBar에 market_cap_min=1조 등 필터가 활성화된 상태
- **When** 사용자가 ThemeDetailPanel 헤더 버튼을 클릭하여 ChartGrid로 진입한다 (AC-A2 동선)
- **Then** AppContent useEffect가 `applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: stockCodes })`를 호출하여 (1) market_cap_min이 null로 reset된다. (2) FilterBar의 모든 다른 필터(change_pct_min, rs_min, sectors 등)가 모두 DEFAULT 값으로 reset된다. (3) ChartGrid는 stockCodes에 해당하는 종목만 표시한다 (소형주 포함).
- 통과 기준: vitest에서 ScreenContext의 ScreenRequest가 `JSON.stringify` 비교로 DEFAULT_SCREEN_REQUEST + codes 형태와 정확히 일치 검증.

### AC-A6: mismatch banner

- 검증 대상 REQ: REQ-CN-014
- 자동/수동: 자동 (vitest fixture mismatch) + 수동 (manual 시나리오 C — 의도적 시뮬레이션)
- **Given** AC-A2 동선에서 selectedTheme.stocks가 12개이지만 그 중 3개가 stock_meta에 없는 경우 (상장폐지 / 신규상장 / 메타 미반영). `appliedContext.requestedCodeCount = 12`, `flatStocks.length = 9`
- **When** ChartGrid가 렌더링된다
- **Then** ChartGrid 상단에 dismissible inline notice가 다음과 정확히 일치하게 표시된다:
  > "요청한 12종목 중 9종목 표시 — 3종목은 현재 DB에서 조회되지 않는 종목입니다 (상장폐지 / 신규상장 / 메타 미반영)."
  - `data-testid="chart-grid-mismatch-banner"` 속성 존재.
  - 비개발자 친화 문구. `stock_meta`, `DB schema`, `JOIN failure` 등 내부 용어 미노출 (AC-C1 보강).
- 통과 기준: vitest에서 banner 텍스트 정확 매칭 + testid 존재 검증.
- 라이브 검증 (LESSON-NTC-001): 시나리오 C에서 사용자가 banner 문구를 직접 읽고 비개발자가 이해 가능한지 검증.

---

## B 동선 (Feature B: Search → Grid)

### AC-B1: stock master 1회 fetch (세션 내)

- 검증 대상 REQ: REQ-CN-010
- 자동/수동: 자동 (vitest mock count) + 수동 (manual 시나리오 H — DevTools Network)
- **Given** ChartGrid 탭이 활성화된 상태에서 사용자가 페이지 진입 후 검색 입력 필드를 처음 focus한다
- **When** focus가 발생하고 useStockMaster() 훅이 처음 invoke된다
- **Then** (1) `GET /api/stocks/master`가 1회 호출된다. (2) 같은 세션 내에서 입력 필드를 닫고 다시 열거나 다른 키 입력을 해도 추가 fetch 0회 (module-level cached promise reuse).
- 통과 기준: vitest에서 fetchStockMaster mock 호출 횟수 === 1.
- 라이브 검증: 시나리오 H의 DevTools Network 탭에서 `/api/stocks/master` 요청 1건만 발생함을 사용자가 직접 확인.

### AC-B2: 부분 일치 매칭 ("삼성")

- 검증 대상 REQ: REQ-CN-012 (score 2 — 종목명 substring)
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 D)
- **Given** stock master fixture에 "삼성전자" (005930), "삼성SDI" (006400), "현대차" (005380), "LG전자" (066570) 등 ~2,500 row가 있는 상태에서 검색 입력 focus 완료
- **When** 사용자가 "삼성"을 입력하고 150ms 디바운스 통과
- **Then** dropdown 상위에 "삼성전자", "삼성SDI" 등 종목명에 "삼성" substring을 포함하는 모든 항목이 score 2 (또는 score 3 prefix 매치)로 노출된다. 최대 8개. 의도된 종목 (삼성전자)이 상위 3개 안에 등장한다.
- 통과 기준: vitest에서 dropdown items[0].name === "삼성전자" 매칭 + items.length <= 8.
- 라이브 검증 (LESSON-NTC-001 + REQ-CN-NF-005): 시나리오 D에서 사용자가 "삼성" 입력 후 dropdown 상위에 의도된 결과가 등장함을 직접 확인.

### AC-B3: 코드 prefix 매칭 ("005")

- 검증 대상 REQ: REQ-CN-012 (score 4 — 코드 정확 prefix)
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 E)
- **Given** stock master fixture에 005380 (현대차), 005490 (POSCO홀딩스), 005930 (삼성전자) 등 005로 시작하는 종목들이 포함된 상태
- **When** 사용자가 "005"를 입력 (6자리 숫자 prefix)
- **Then** dropdown 상위에 005로 시작하는 코드를 가진 종목들이 score 4 (코드 prefix)로 우선 노출된다. 종목명에 "005" substring을 포함하는 종목보다 먼저 표시된다.
- 통과 기준: vitest에서 dropdown items[0].code.startsWith("005") === true + 정렬 검증.
- 라이브 검증: 시나리오 E.

### AC-B4: 초성 매칭 ("ㅅㅅㅈㅈ")

- 검증 대상 REQ: REQ-CN-011, REQ-CN-012 (score 1)
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 F)
- **Given** stock master fixture에 "삼성전자" (005930), "삼성SDI" (006400) 등이 포함된 상태
- **When** 사용자가 "ㅅㅅㅈㅈ" (초성 4자)을 입력
- **Then** extractInitialConsonants("삼성전자") === "ㅅㅅㅈㅈ" 매칭 결과로 dropdown 상위에 "삼성전자"가 score 1 (초성 매치)로 노출된다. "삼성SDI" 등 다른 초성도 부분 매칭되면 함께 노출.
- 통과 기준: vitest fixture 시나리오 — input "ㅅㅅㅈㅈ" → dropdown items[0].name === "삼성전자".
- 라이브 검증 (LESSON-NTC-001 + REQ-CN-NF-005): 시나리오 F에서 사용자가 "ㅅㅅㅈㅈ" 입력 시 의도된 종목(삼성전자)이 dropdown 상위에 등장함을 직접 확인.

### AC-B5: 항목 선택 → ChartGrid 렌더 + full reset

- 검증 대상 REQ: REQ-CN-013, REQ-CN-C-006
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 G)
- **Given** FilterBar에 market_cap_min=1조 등 필터가 활성화된 상태에서 사용자가 검색 입력 후 dropdown에서 "삼성전자" (005930) 선택
- **When** dropdown 항목이 선택되어 onSelect("005930", "삼성전자")이 호출된다
- **Then** (1) navigateToTab이 `('chart-grid', { stockCodes: ['005930'], searchLabel: '종목: 삼성전자 005930' })`로 호출된다. (2) AppContent useEffect가 applyFilters로 full reset 적용. (3) ChartGrid가 005930 단일 chart로 채워진다 (market_cap_min 등 필터와 무관). (4) FilterBar의 다른 필터는 모두 DEFAULT 상태가 된다.
- 통과 기준: vitest에서 navigateToTab mock 호출 인자 검증 + ScreenRequest === DEFAULT_SCREEN_REQUEST + codes:['005930'].
- 라이브 검증: 시나리오 G에서 사용자가 market_cap_min 필터 활성화된 상태에서 그 필터 미충족 종목 검색 후 ChartGrid에 정상 표시됨을 직접 확인 (필터 우회 검증).

### AC-B6: 검색 후 chip 표시

- 검증 대상 REQ: REQ-CN-015
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 G 일부)
- **Given** AC-B5 완료 후 ChartGrid 탭에 진입한 상태 (appliedContext.label = '종목: 삼성전자 005930')
- **When** FilterBar가 렌더된다
- **Then** chip `종목: 삼성전자 005930 ✕`이 표시된다. ✕ 클릭 시 AC-A4와 동일하게 reset.
- 통과 기준: `screen.getByTestId('filter-bar-applied-context-chip')` 텍스트 매칭.

### AC-B7: 0건 처리

- 검증 대상 REQ: REQ-CN-012 (0건)
- 자동/수동: 자동 (vitest)
- **Given** stock master fixture에 "ABCXYZ존재하지않음"과 같은 종목이 없는 상태
- **When** 사용자가 "ABCXYZ"를 입력 (디바운스 통과)
- **Then** dropdown에 "검색 결과 없음" 안내 문구가 표시된다 (D-6 사전 잠금). dropdown items.length === 0이지만 dropdown 자체는 열려 있고 안내 문구를 표시.
- 통과 기준: vitest에서 dropdown 텍스트에 "검색 결과 없음" 매칭.

### AC-B8: 503 처리

- 검증 대상 REQ: REQ-CN-004, AC-B8 (D-7)
- 자동/수동: 자동 (vitest mock 503)
- **Given** `GET /api/stocks/master`가 503 + `{"detail": "stock_meta_not_ready"}`를 반환하도록 mock된 상태
- **When** 사용자가 검색 입력 필드를 focus한다
- **Then** (1) useStockMaster()가 error state로 전환된다. (2) 검색 입력 필드는 disabled 속성을 가진다. (3) hover 시 tooltip "DB 업데이트가 필요합니다"가 노출된다. (4) dropdown은 열리지 않는다.
- 통과 기준: vitest에서 `input.disabled === true` + `title === 'DB 업데이트가 필요합니다'` 검증.

---

## 공통 (mismatch + chip + reset + 회귀)

### AC-C1: mismatch banner 비개발자 친화 문구

- 검증 대상 REQ: REQ-CN-014, D-3
- 자동/수동: 자동 (vitest) + 수동 (manual 시나리오 C)
- **Given** AC-A6의 mismatch 상황 (12개 요청, 9개 표시)
- **When** banner가 렌더된다
- **Then** banner 텍스트는 "요청한 12종목 중 9종목 표시 — 3종목은 현재 DB에서 조회되지 않는 종목입니다 (상장폐지 / 신규상장 / 메타 미반영)." 정확히 일치. **금지된 단어**: `stock_meta`, `DB schema`, `JOIN failure`, `null reference` 등 내부 용어. **포함되어야 할 단어**: "DB", "조회", "상장폐지", "신규상장", "메타 미반영".
- 통과 기준: vitest에서 banner 텍스트가 금지 단어 0건 + 포함 단어 모두 등장 검증.
- 라이브 검증 (LESSON-NTC-001): 시나리오 C에서 사용자가 banner를 직접 읽고 비개발자도 이해 가능한지 확인.

### AC-C2: chip dismiss → reset

- 검증 대상 REQ: REQ-CN-015
- 자동/수동: 자동 (vitest)
- **Given** appliedContext.label이 non-null 상태이고 chip이 렌더된 상태
- **When** 사용자가 chip의 ✕ 버튼을 클릭한다
- **Then** (1) `clearAppliedContext()`가 호출되어 appliedContext = null이 된다. (2) `applyFilters(DEFAULT_SCREEN_REQUEST)`가 호출된다. (3) ChartGrid의 flatStocks가 빈 배열로 비워진다. (4) chip이 미렌더된다.
- 통과 기준: vitest에서 chip click 후 appliedContext === null + ScreenRequest === DEFAULT_SCREEN_REQUEST + chip 미렌더 검증.

### AC-C3: appliedContext clear (자연 흐름)

- 검증 대상 REQ: REQ-CN-008, REQ-CN-016
- 자동/수동: 자동 (vitest)
- **Given** appliedContext.label이 non-null 상태이고 chip이 렌더된 상태
- **When** 사용자가 FilterBar의 슬라이더 등으로 다른 필터를 변경하여 applyFilters가 새 ScreenRequest로 호출된다
- **Then** appliedContext의 동작은 다음 정책 중 하나를 따른다:
  - **정책 A (보존)**: chip은 그대로 보존되며, 사용자가 명시적으로 ✕ 클릭 시에만 reset. 사용자가 검색/테마 진입 후 추가 필터를 결합할 수 있도록.
  - **정책 B (자동 reset)**: 새 필터 액션 시 appliedContext도 함께 reset. 의도 모호.
  - 본 SPEC 기본 정책: **A (보존)** — 단, 신규 navigateToTab 호출(다른 테마 클릭 또는 다른 종목 검색) 시에는 새 appliedContext로 덮어쓰기.
- 통과 기준: vitest에서 정책 A 동작 검증 — 사용자가 슬라이더 변경 시 appliedContext.label 그대로 + 사용자가 새 navigateToTab 트리거 시 appliedContext.label 갱신.

### AC-C4: cross-tab 회귀 0

- 검증 대상 REQ: REQ-CN-C-002
- 자동/수동: 수동 (manual 회귀 검증)
- **Given** SPEC 적용 전 baseline에서 StockExplorer→Grid 동선과 SectorAnalysis→StockExplorer 동선이 정상 작동하는 상태
- **When** SPEC-CHART-NAV-001 모든 변경사항이 적용된 후 동일 동선을 재실행한다
- **Then** (1) StockExplorer 시총 사진 클릭 → ChartGrid 진입 시 종목 차트가 정상 렌더 (기존 동작 보존). (2) SectorAnalysis에서 섹터 카드 클릭 → StockExplorer로 전환 + 해당 섹터 종목 리스트 정상 표시.
- 통과 기준: manual 회귀 검증에서 두 동선 모두 정상 작동 확인.

---

## 백엔드 (/api/stocks/master)

### AC-S1: 200 정상 응답

- 검증 대상 REQ: REQ-CN-001, REQ-CN-002
- 자동/수동: 자동 (pytest)
- **Given** fixture stock_meta DB가 다음 row를 포함한다:
  - `("005930", "삼성전자", "KOSPI", "2026-05-07T09:00:00")`
  - `("000660", "SK하이닉스", "KOSPI", "2026-05-07T09:00:00")`
  - `("035720", "카카오", "KOSPI", "2026-05-06T18:00:00")`
- **When** `GET /api/stocks/master`가 호출된다
- **Then** (1) HTTP 200. (2) 응답 body는 `{ "stocks": [{"code": "035720", "name": "카카오", "market": "KOSPI"}, {"code": "000660", "name": "SK하이닉스", "market": "KOSPI"}, {"code": "005930", "name": "삼성전자", "market": "KOSPI"}], "generated_at": "2026-05-07T09:00:00" }` (name ASC 정렬). (3) Pydantic 검증 통과.
- 통과 기준: pytest `response.status_code == 200` + `response.json()["stocks"]` 정렬 검증 + `generated_at` 검증.

### AC-S2: 503 응답 (stock_meta 부재)

- 검증 대상 REQ: REQ-CN-004
- 자동/수동: 자동 (pytest)
- **Given** fixture DB가 `stock_meta` 테이블을 포함하지 않거나 (CREATE TABLE 누락) 빈 테이블인 상태
- **When** `GET /api/stocks/master`가 호출된다
- **Then** (1) HTTP 503. (2) 응답 body `{"detail": "stock_meta_not_ready"}`. (3) bare except 사용 0건 — `sqlite3.OperationalError` 또는 specific exception만 catch.
- 통과 기준: pytest `response.status_code == 503` + `response.json() == {"detail": "stock_meta_not_ready"}` + bare except grep 0건 (정적 검증).

### AC-S3: ETag 헤더

- 검증 대상 REQ: REQ-CN-003
- 자동/수동: 자동 (pytest)
- **Given** fixture stock_meta DB의 last_updated MAX = "2026-05-07T09:00:00"
- **When** `GET /api/stocks/master`가 호출된다
- **Then** (1) 응답 헤더 `ETag` 값이 `"2026-05-07T09:00:00"` 또는 그 hash 값으로 설정된다. (2) `Cache-Control: max-age=300` 헤더 포함. (3) 두 번째 호출 시 ETag 값 동일 (DB last_updated 무변경).
- 통과 기준: pytest `response.headers["ETag"]` 존재 + `Cache-Control` 헤더 검증.

### AC-S4: 정렬 + name NULL 미포함

- 검증 대상 REQ: REQ-CN-002
- 자동/수동: 자동 (pytest)
- **Given** fixture stock_meta DB가 다음 row를 포함한다:
  - `("005930", "삼성전자", "KOSPI", ...)`
  - `("000001", NULL, "KOSPI", ...)` (name NULL)
  - `("035720", "카카오", "KOSPI", ...)`
- **When** `GET /api/stocks/master`가 호출된다
- **Then** (1) 응답 stocks 배열에 `code: "000001"` row 미포함 (name IS NOT NULL WHERE 절). (2) 나머지 2 row는 name ASC: 카카오 → 삼성전자.
- 통과 기준: pytest `len(response.json()["stocks"]) == 2` + `stocks[0]["name"] == "카카오"` + `stocks[1]["name"] == "삼성전자"` + 모든 row의 name이 non-null.

---

## 회귀 (선행 SPEC + cross-tab + 캐시)

### AC-R1: SPEC-NAVER-THEME-CONSOLIDATED 25 AC PASS 유지

- 검증 대상 REQ: REQ-CN-C-002
- 자동/수동: 자동 (pytest + vitest 회귀)
- **Given** SPEC-NAVER-THEME-CONSOLIDATED v1.0.0이 ship된 상태에서 25 AC 모두 PASS인 baseline
- **When** SPEC-CHART-NAV-001 모든 변경사항이 적용된 후 V1 + V2 backend + V2 frontend 테스트 스위트를 재실행한다
- **Then** (1) V1 단위 테스트 51개 모두 PASS. (2) V2 단위 테스트 24+ 모두 PASS. (3) frontend vitest baseline diff 0 (ChartGrid 1 fail pre-existing 외 신규 fail 0). (4) AC-01~AC-25 (선행 SPEC) 모두 PASS.
- 통과 기준: `pytest backend/tests/ -v` 통계가 baseline과 일치 + `npm run test -- --run` 통계가 baseline + 신규 테스트 수만큼 증가.

### AC-R2: StockExplorer→Grid 동선 정상

- 검증 대상 REQ: REQ-CN-C-001, REQ-CN-C-002
- 자동/수동: 수동 (manual 회귀)
- **Given** SPEC 적용 전 baseline에서 StockExplorer 탭의 시총 상위 사진 클릭 시 ChartGrid 진입 동선이 정상 작동하는 상태
- **When** SPEC-CHART-NAV-001 적용 후 동일 동선을 실행한다
- **Then** (1) 시총 사진 클릭 → activeTab='chart-grid' 전환. (2) ChartGrid에 시총 상위 종목들이 정상 표시. (3) AppContent useEffect가 기존 default 분기로 동작 (themeName/searchLabel 없음 → source='explorer').
- 통과 기준: manual 회귀 검증 통과.

### AC-R3: SectorAnalysis→StockExplorer 정상

- 검증 대상 REQ: REQ-CN-C-002
- 자동/수동: 수동 (manual 회귀)
- **Given** SPEC 적용 전 baseline에서 SectorAnalysis 탭의 섹터 카드 클릭 시 StockExplorer 탭으로 전환되어 해당 섹터 종목 리스트가 표시되는 상태
- **When** SPEC-CHART-NAV-001 적용 후 동일 동선을 실행한다
- **Then** (1) 섹터 카드 클릭 → activeTab='stock-explorer' 전환. (2) StockExplorer에 해당 섹터 종목 리스트 정상 표시. (3) 기존 cross-tab 인프라 무수정 보장 (REQ-CN-C-001).
- 통과 기준: manual 회귀 검증 통과.

### AC-R4: ThemeAnalysis localStorage 캐시 정상

- 검증 대상 REQ: REQ-CN-NF-004, SPEC-NAVER-THEME-CONSOLIDATED REQ-NT3-015/016
- 자동/수동: 자동 (vitest 기존 회귀 테스트) + 수동 (manual 회귀)
- **Given** SPEC 적용 전 baseline에서 ThemeAnalysis localStorage 캐시 (key `theme-analysis-cache-full`, `theme-analysis-cache-quick`) 동작이 정상인 상태 (cache hit / miss / 🔄 갱신 버튼 invalidate 모두 정상)
- **When** SPEC-CHART-NAV-001 적용 후 ThemeAnalysis 탭을 진입하고 캐시 hit / miss / 갱신 시나리오를 재실행한다
- **Then** (1) 캐시 schema 변경 0건. (2) cache hit 시 즉시 setData + fetch skip. (3) 🔄 갱신 버튼 클릭 시 캐시 invalidate + 새 fetch. (4) Feature A의 헤더 버튼 클릭은 캐시 read-only 활용만 (캐시 write 0건).
- 통과 기준: vitest에서 SPEC-NAVER-THEME-CONSOLIDATED AC-24/AC-25 그대로 PASS + manual 회귀 검증 통과.

---

## 라이브 검증 의무 요약 (LESSON-NTC-001)

다음 AC는 fixture 단위 테스트만으로 충분하지 않으며, manual browser 검증을 거쳐 잠근다:

| AC | manual 시나리오 | 검증 포인트 |
| --- | --- | --- |
| AC-A1 | A | 라이브 종목 수가 selectedTheme.stocks.length와 일치 |
| AC-A2 | A | navigateToTab + ChartGrid 진입 + appliedContext 설정 end-to-end |
| AC-A3 | B | chip event.stopPropagation 동작 + 상세 패널 미열림 |
| AC-A6 | C | banner 비개발자 친화 문구 가독성 |
| AC-B2 | D | "삼성" 입력 → 의도 종목 상위 3개 안 등장 |
| AC-B3 | E | "005" 입력 → 코드 prefix 매치 우선 노출 |
| AC-B4 | F | "ㅅㅅㅈㅈ" 입력 → 삼성전자 매칭 |
| AC-B5 | G | 필터 활성화 상태에서 검색 후 ChartGrid 정상 표시 (필터 우회 검증) |
| AC-B1 | H | DevTools Network 탭에서 `/api/stocks/master` 1회 호출 확인 |
| AC-C1 | C | banner 문구의 비개발자 친화성 라이브 확인 |
| AC-C4 | (회귀 manual) | StockExplorer→Grid + SectorAnalysis→StockExplorer 정상 |

---

## Definition of Done

본 SPEC이 "Implemented" 상태로 전환되기 위한 조건:

1. **모든 26 AC PASS** — 자동 + 수동 시나리오 모두.
2. **회귀 게이트**: AC-R1~R4 모두 PASS (선행 SPEC 25 AC + 기존 cross-tab + 캐시).
3. **라이브 검증 의무**: 위 표의 11개 AC가 manual browser 시나리오에서 사용자 직접 검증 완료.
4. **TRUST 5 quality gates**:
   - Tested: 신규 단위 테스트 7개 + 기존 baseline diff 0
   - Readable: ruff / eslint warnings 0
   - Unified: 기존 코드 스타일 일관 (black / prettier)
   - Secured: bare except 0건 + SQLite mode=ro 검증
   - Trackable: 5개 commit (Step 1~5) 분리 + commit message 규약 준수
5. **MX tag 적용**: 신규 함수에 @MX:NOTE (의도/단일책임) + ChartGrid mismatch banner / FilterBar chip 등 가시화 surface에 @MX:ANCHOR (high fan_in 검토).
6. **Documentation**: spec.md HISTORY 섹션에 ship 시점 commit 추가, README/CHANGELOG 갱신 (sync phase에서).
7. **PR description**: 본 acceptance.md의 26 AC 매핑 표 + 라이브 검증 시나리오 결과 포함.

---

Version: 1.0.0
Status: Ready for /moai run validation
Last Updated: 2026-05-07
