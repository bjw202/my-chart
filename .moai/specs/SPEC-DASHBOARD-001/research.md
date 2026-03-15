# SPEC-DASHBOARD-001: S-RIM Dashboard Feature - Research Report

**Researcher**: team-researcher
**Date**: 2026-03-05
**Status**: Complete

---

## 1. Executive Summary

This report documents deep codebase analysis for the S-RIM Dashboard feature. The dashboard will:
1. Enhance the `fnguide` engine with B/S reclassification, 3-rate decomposition, profit waterfall, and health indicators
2. Add a FastAPI endpoint `GET /api/analysis/{code}` following existing patterns
3. Add a React frontend dashboard modal triggered from ChartCell buttons

**Key Finding**: The existing `fnguide` engine already performs ~80% of the required financial calculations in `analysis.py::fs_analysis()`. The primary gaps are: (a) gross profit/CFO data not yet extracted from the HTML tables, (b) health indicator calculations not computed, and (c) no API layer or frontend component exists yet.

---

## 2. fnguide Package Deep Analysis

### 2.1 Package Structure

```
fnguide/
  __init__.py      # Exports: CompResult, ProfitTrend, RateHistory, analyze_comp, ...
  parser.py        # Pure HTML/JSON parsing utilities - no network
  crawler.py       # HTTP crawling layer - FnGuide pages
  analysis.py      # Financial analysis: fs_analysis(), calc_weight_coeff()
  analyzer.py      # Orchestrator: analyze_comp() -> CompResult
```

### 2.2 parser.py - Parsing Utilities

**File**: `/Users/byunjungwon/Dev/my_chart/fnguide/parser.py`

Key functions:
- `table_parsing(table: Tag) -> (account_type: str, df: DataFrame)` (line 17): Parses FnGuide HTML `<table>` into DataFrame. Column = fiscal year (YYYY/MM), Index = IFRS account names. Handles th/td extraction.
- `convert_string_to_number(df, fillna=0) -> DataFrame` (line 49): Vectorized column-by-column conversion. Handles commas, dashes, empty strings.
- `remove_E(columns)` (line 79): Strips `(E)` suffix from consensus columns.
- `remove_space(index)` (line 84): Removes whitespace from index.
- `to_num(x: str) -> int | float` (line 89): Single value converter.

**Key observation**: `table_parsing` returns ALL rows from the HTML table, preserving all account names as the DataFrame index. This means `매출총이익`, `매출원가`, `영업활동으로인한현금흐름` are available IF they appear in FnGuide's HTML tables.

### 2.3 crawler.py - HTTP Crawling

**File**: `/Users/byunjungwon/Dev/my_chart/fnguide/crawler.py`

**URLs fetched**:
- Snapshot: `http://comp.fnguide.com/SVO2/asp/SVD_Main.asp?...&gicode=A{code}` (line 27)
- Financial statements: `http://comp.fnguide.com/SVO2/asp/SVD_Finance.asp?...&gicode=A{code}` (line 31)
- Consensus: `http://comp.fnguide.com/SVO2/json/data/01_06/01_A{code}_A_D.json` (line 35)

**`read_fs(code)` function** (line 169):
- Fetches 6 HTML tables from SVD_Finance.asp:
  - tables[0] = 연간 B/S (Balance Sheet annual)
  - tables[1] = 분기 B/S (Balance Sheet quarterly)
  - tables[2] = 연간 P/L (Income Statement annual)
  - tables[3] = 분기 P/L (Income Statement quarterly)
  - tables[4] = 연간 CF (Cash Flow annual)
  - tables[5] = 분기 CF (Cash Flow quarterly)
- Concatenates all into: `df_fs_ann = concat([df_bs_ann, df_income_ann, df_cash_ann])`, `df_fs_quar = concat([...quarterly...])`
- **Returns**: `(account_type, df_fs_ann, df_fs_quar)`
- Drops last 2 columns (forecast columns) via `iloc[:, :-2]`

**Critical finding**: The Cash Flow tables (tables[4], tables[5]) ARE already fetched and included in `df_fs_ann` and `df_fs_quar`. This means `영업활동으로인한현금흐름` (Operating Cash Flow) is already available in the DataFrame — it is just not surfaced in `analysis.py` or `CompResult`.

**`read_snapshot(code, account_type)` function** (line 41):
- Returns `(report: dict, df_snap: DataFrame, df_snap_ann: DataFrame)`
- `report` contains: 52주 최고/최저가, 거래대금, 시가총액, 베타, 발행주식수, 유통주식수, 자기주식, PER, 12M PER, 업종 PER, PBR, 배당수익률, Summary
- `df_snap` = quarterly snapshot (EPS, BPS, ROE, etc.)
- `df_snap_ann` = annual snapshot with forecasts

**`read_consensus(code, account_type)` function** (line 200):
- Fetches JSON from FnGuide consensus URL
- Returns DataFrame indexed by account name, columns = YYYY/MM forecast years
- Contains consensus estimates for EPS, BPS, ROE, etc.

**`get_fnguide(code)` function** (line 239):
- Orchestrates all three fetches with 0.1s delays
- Returns 7-tuple: `(df_fs_ann, df_fs_quar, df_snap, df_snap_ann, df_cons, report, account_type)`

### 2.4 analysis.py - Financial Analysis

**File**: `/Users/byunjungwon/Dev/my_chart/fnguide/analysis.py`

**`fs_analysis(df_fs_ann, df_fs_quar) -> (df_anal, df_invest)`** (line 39):

Already computes the following (matching dashboard requirements directly):

**B/S Reclassification (자금조달 측)**:
- `신용조달` (영업부채): 매입채무및기타유동채무 + 유동종업원급여충당부채 + 기타단기충당부채 + 당기법인세부채 + 기타유동부채 + 장기매입채무및기타비유동채무 + 비유동종업원급여충당부채 + 기타장기충당부채 + 이연법인세부채 + 장기당기법인세부채 + 기타비유동부채 (lines 64-76)
- `외부차입`: 단기사채 + 단기차입금 + 유동성장기부채 + 유동금융부채 + 사채 + 장기차입금 + 비유동금융부채 (lines 78-86)
- `유보이익`: 기타포괄손익누계액 + 이익잉여금(결손금) (line 88-90)
- `주주투자`: 자본금 + 신종자본증권 + 자본잉여금 + 기타자본 (lines 92-96)
- `비지배주주지분` (line 99-102): KeyError-safe, defaults to 0 for IFRS(별도)

**B/S Reclassification (자산투자 측)**:
- `설비투자`: 유형자산 + 무형자산 + 비유동생물자산 (lines 114-117)
- `운전자산`: 재고자산 + 유동생물자산 + 매출채권및기타유동채권 + 당기법인세자산 + 기타유동자산 + 장기매출채권및기타비유동채권 + 이연법인세자산 + 장기당기법인세자산 + 기타비유동자산 (lines 119-130)
- `금융투자`: 투자부동산 + 장기금융자산 + 관계기업등지분관련투자자산 (lines 132-136)
- `여유자금`: 현금및현금성자산 + 유동금융자산 (lines 138-140)

**3-Rate Decomposition (3대 수익률)**:
- `영업자산이익률`: 2 × 영업이익 / (전기영업자산 + 당기영업자산) — loop over years col[1], col[2], col[3] (lines 205-218)
- `비영업자산이익률`: 2 × 비영업이익 / (전기비영업자산 + 당기비영업자산) (lines 212-219)
- `차입이자율`: 2 × 이자비용 / (전기외부차입 + 당기외부차입) (lines 221-225)
- `지배주주ROE`: 2 × 지배주주순이익 / (전기주주몫 + 당기주주몫) (lines 228-232)
- `가중평균` computed for all 4 rates via `calc_weight_coeff` (lines 240-245)
- `1순위` selection: trend-based or weighted average (lines 247-276)

**Profit Waterfall (이익 귀속 흐름)**:
- Already computed in `df_anal`:
  - `영업이익`, `비영업이익`, `이자비용`, `법인세비용`, `지배주주순이익`, `비지배주주순이익` (lines 190-200)
  - `예상` column for all items computed by multiplying assets × rates (lines 281-314)

**What is NOT computed** in current `analysis.py`:
1. `매출총이익` / `GPM` (Gross Profit Margin) - data exists in df_fs_ann but not extracted
2. `영업CF` (Operating Cash Flow) - data exists in df_fs_ann (from cash flow tables) but not surfaced
3. `영업CF / 영업이익` ratio (profit quality)
4. `매출 YoY 성장률` (Revenue YoY growth) - raw data exists but not computed
5. `영업이익 YoY 성장률` (Operating profit YoY growth) - same
6. Health indicators: 외부차입/자기자본, 부채비율, 차입금의존도, 이자보상배율, 영업자산비율
7. `순차입금의존도` = (외부차입 - 여유자금) / 총자산
8. `비지배 귀속비율` = 비지배주주순이익 / 당기순이익
9. `ROE-Ke Spread` (requires CAPM Ke calculation)

### 2.5 analyzer.py - Orchestrator

**File**: `/Users/byunjungwon/Dev/my_chart/fnguide/analyzer.py`

**Data classes** (lines 18-93):
- `RateHistory`: year_minus_2, year_minus_1, recent, expected (all float)
- `ProfitTrend`: periods (list[str]), revenue, operating_profit, net_income, operating_margin (all list[float])
- `CompResult`: Full analysis result dataclass with 25+ fields

**`analyze_comp(code: str) -> CompResult`** (line 147):
- Calls `get_fnguide(code)` then `fs_analysis(df_fs_ann, df_fs_quar)`
- Extracts: market_cap, shares, trailing_eps, bps, profit_trend, rate histories, capital structure, asset structure, profit waterfall (expected), net_cash
- **Not extracted**: GPM, operating CF, health ratios, YoY growth rates

**IFRS(연결) vs IFRS(별도) handling** (lines 173-186):
- IFRS(연결): uses `지배기업주주지분계산에 참여한 계정 펼치기` or fallback to `지배기업주주지분` for BPS
- IFRS(별도): uses `자본` for BPS, `당기순이익` for trailing net income

**`net_cash` calculation** (lines 219-226):
- `net_cash = 여유자금 - (단기사채 + 단기차입금 + 유동금융부채 + 사채 + 장기차입금)`

### 2.6 Legacy Code Reference (rim_fnguide_ver20.py)

**File**: `/Users/byunjungwon/Dev/my_chart/rim_fnguide/rim_fnguide_ver20.py`

Key patterns from legacy code that confirm data availability:
- `매출원가 = df_fs_ann.loc['매출원가']` (line 204) — confirming account name
- `매출총이익 = df_fs_ann.loc['매출총이익']` (line 205) — confirming account name
- `영업활동으로인한현금흐름 = df_fs_ann.loc['영업활동으로인한현금흐름']` (line 2837) — confirming CFO account name
- `FCF = 영업활동현금흐름 - CAPEX` (line 1011 comment) — reference for FCF calculation

---

## 3. Backend API Layer Analysis

### 3.1 Application Setup

**File**: `/Users/byunjungwon/Dev/my_chart/backend/main.py`

- FastAPI app with CORS for `localhost:5173`
- Lifespan hook pre-initializes stock/sector registries
- Router prefix: `/api`
- Current routers: chart, db, screen, sectors

**Pattern for adding new router**:
```python
from backend.routers.analysis import router as analysis_router
app.include_router(analysis_router, prefix="/api")
```

### 3.2 Reference Implementation: Chart Endpoint

**Router**: `/Users/byunjungwon/Dev/my_chart/backend/routers/chart.py`
- `GET /api/chart/{code}` with `?timeframe=daily|weekly` query param
- Error handling: 400 for bad params, 404 for not found, 503 for DB schema issues
- Delegates to service layer: `get_chart_data(code, DAILY_DB_PATH)`
- Returns Pydantic response model: `ChartResponse`

**Schema**: `/Users/byunjungwon/Dev/my_chart/backend/schemas/chart.py`
- Pydantic `BaseModel` classes: `CandleBar`, `VolumeBar`, `MAPoint`, `MAOverlays`, `ChartResponse`
- Clean, typed response structure

**Service**: `/Users/byunjungwon/Dev/my_chart/backend/services/chart_service.py`
- Pure Python function, no FastAPI dependencies
- Raises `LookupError` with typed keys (`stock_not_found:code`, `no_data:code`)
- Uses `get_db_conn()` from `backend/deps.py`

**Deps**: `/Users/byunjungwon/Dev/my_chart/backend/deps.py`
- `DAILY_DB_PATH`, `WEEKLY_DB_PATH` constants
- `get_db_conn(path: str) -> sqlite3.Connection`

### 3.3 Analysis Endpoint Design Pattern

The new analysis endpoint should follow the chart endpoint pattern exactly:
1. `backend/routers/analysis.py` — `GET /api/analysis/{code}` router
2. `backend/schemas/analysis.py` — Pydantic response models for dashboard data
3. `backend/services/analysis_service.py` — Service calling `analyze_comp(code)` + extra computations
4. Register router in `backend/main.py`

**Error handling for fnguide**:
- `fnguide` makes HTTP requests — can fail with network errors, timeouts, or parsing errors
- Should return 503 Service Unavailable on crawler failures
- Return 404 if stock not found in fnguide

---

## 4. Frontend Architecture Analysis

### 4.1 App Structure

**File**: `/Users/byunjungwon/Dev/my_chart/frontend/src/App.tsx`
- Providers: ScreenProvider → NavigationProvider → WatchlistProvider → ErrorBoundary
- Main layout: FilterBar + (ChartGrid | StockList) + StatusBar
- No routing (single-page, no react-router)

### 4.2 ChartCell - Where Dashboard Button Goes

**File**: `/Users/byunjungwon/Dev/my_chart/frontend/src/components/ChartGrid/ChartCell.tsx`

Current header buttons (lines 228-257):
1. `%` button — toggles price range measure mode (line 228)
2. Check button (`+`/`✓`) — watchlist toggle (line 239)
3. `TR` button — opens TradingView (line 248)

**Dashboard button addition location**: Add a new `분석` (or `FS`) button in the header alongside TR button at line 248-257.

**Pattern for new button**:
```tsx
<button
  className="chart-cell-analysis-btn"
  onClick={(e) => {
    e.stopPropagation()
    // open analysis modal
  }}
  title="재무 분석 대시보드"
>
  FS
</button>
```

### 4.3 API Client Pattern

**File**: `/Users/byunjungwon/Dev/my_chart/frontend/src/api/client.ts`
- Axios client with baseURL `/api`
- Error interceptor: maps HTTP status codes to typed errors
- Pattern for new API file:

**File**: `/Users/byunjungwon/Dev/my_chart/frontend/src/api/chart.ts`
- Simple async function returning typed response
- Pattern: `client.get<ResponseType>('/endpoint/param')`

### 4.4 Type Definitions Pattern

**File**: `/Users/byunjungwon/Dev/my_chart/frontend/src/types/stock.ts`
- Plain TypeScript interfaces mirroring backend Pydantic models
- No Zod validation (existing pattern)
- New file needed: `frontend/src/types/analysis.ts`

### 4.5 ChartGrid Structure

**File**: `/Users/byunjungwon/Dev/my_chart/frontend/src/components/ChartGrid/ChartGrid.tsx`
- Manages `timeframe` state and grid layout
- Maps `visibleStocks` to `ChartCell` components
- Modal state should be managed here or in a new context

---

## 5. Test Infrastructure Analysis

### 5.1 Existing Test Structure

```
tests/fnguide/
  conftest.py      — session-scope fixtures: samsung_fs, samsung_fnguide, hynix_fnguide
  test_parser.py   — Unit tests (no network)
  test_crawler.py  — Live HTTP tests (@pytest.mark.live)
  test_analysis.py — Live HTTP tests using session fixtures
  test_analyzer.py — E2E tests (@pytest.mark.live @pytest.mark.slow)
```

69 tests, 93% coverage. Tests use `@pytest.mark.live` for network-dependent tests.

### 5.2 Test Patterns for New Code

**For analysis.py additions** (pure functions): Add to `tests/fnguide/test_analysis.py` using existing `samsung_fs` fixture.

**For new dashboard functions** (if added to analysis.py): No new HTTP calls needed — data comes from existing `df_fs_ann` fixture.

**For backend service** (`analysis_service.py`): Mock `analyze_comp()` return to avoid HTTP in unit tests. Live tests use actual fnguide data.

**For frontend**: New component tests using Vitest + React Testing Library.

---

## 6. Gap Analysis: Current vs Dashboard Requirements

### 6.1 Already Available in fnguide Engine

| Dashboard Section | Required Item | Status | Location |
|-------------------|---------------|--------|----------|
| Section 1 | 매출액 (4개년) | Available | `df_fs_ann.loc['매출액']` |
| Section 1 | 영업이익 (4개년) | Available | `df_anal.loc['영업이익']` |
| Section 1 | 당기순이익 (4개년) | Available | `df_anal.loc['지배주주순이익']` |
| Section 1 | 영업이익률 OPM | Available | `ProfitTrend.operating_margin` |
| Section 1 | 순이익률 NPM | Computable | `지배주주순이익 / 매출액` |
| Section 2 | 자기자본 (지배주주) | Available | `df_anal.loc['주주몫']` |
| Section 2 | 영업부채 | Available | `df_anal.loc['영업부채']` |
| Section 2 | 외부차입 | Available | `df_anal.loc['외부차입']` |
| Section 2 | 비지배지분 | Available | `df_anal.loc['비지배주주지분']` |
| Section 3 | 설비투자 | Available | `df_invest.loc['설비투자']` |
| Section 3 | 운전자산 | Available | `df_invest.loc['운전자산']` |
| Section 3 | 금융투자 | Available | `df_invest.loc['금융투자']` |
| Section 3 | 여유자금 | Available | `df_invest.loc['여유자금']` |
| Section 4 | 영업자산이익률 (3년 + 가중평균) | Available | `df_anal.loc['영업자산이익률']` |
| Section 4 | 비영업자산이익률 | Available | `df_anal.loc['비영업자산이익률']` |
| Section 4 | 차입이자율 | Available | `df_anal.loc['차입이자율']` |
| Section 4 | 지배주주 ROE | Available | `df_anal.loc['지배주주ROE']` |
| Section 5 | 영업이익 (예상) | Available | `df_anal.loc['영업이익', '예상']` |
| Section 5 | 비영업이익 (예상) | Available | `df_anal.loc['비영업이익', '예상']` |
| Section 5 | 이자비용 (예상) | Available | `df_anal.loc['이자비용', '예상']` |
| Section 5 | 법인세비용 (예상) | Available | `df_anal.loc['법인세비용', '예상']` |
| Section 5 | 지배주주순이익 (예상) | Available | `df_anal.loc['지배주주순이익', '예상']` |

### 6.2 Gaps — Data Available in df_fs_ann but Not Surfaced

| Dashboard Section | Required Item | Gap Type | Fix |
|-------------------|---------------|----------|-----|
| Section 1 | 매출총이익 (GPM) | Not extracted | `df_fs_ann.loc['매출총이익']` exists in fetched data |
| Section 1 | 영업CF (4개년) | Not extracted | `df_fs_ann.loc['영업활동으로인한현금흐름']` exists in fetched data |
| Section 1 | 매출 YoY 성장률 | Not computed | Compute from `매출액` time series |
| Section 1 | 영업이익 YoY 성장률 | Not computed | Compute from `영업이익` time series |
| Section 1 | 지배주주순이익 YoY 성장률 | Not computed | Compute from `지배주주순이익` time series |
| Section 1 | 영업CF / 영업이익 (이익의 질) | Not computed | Ratio of above two |

### 6.3 Gaps — New Calculations Needed

| Dashboard Section | Required Item | Gap Type | Formula |
|-------------------|---------------|----------|---------|
| Section 2 | 외부차입/자기자본 | New calc | `외부차입 / 주주몫` |
| Section 2 | 부채비율 | New calc | `(영업부채 + 외부차입) / (주주몫 + 비지배주주지분)` |
| Section 2 | 차입금의존도 | New calc | `외부차입 / 총자산` — need `총자산 = 자산` from df_fs_ann |
| Section 2 | 순차입금의존도 | New calc | `(외부차입 - 여유자금) / 총자산` |
| Section 2 | 이자보상배율 | New calc | `영업이익 / 이자비용` |
| Section 3 | 영업자산비율 | New calc | `영업자산 / 총자산` |
| Section 4 | Spread (ROE - Ke) | New calc | Requires CAPM: `Rf + Beta × MRP` — Beta from snapshot report |
| Section 5 | 비지배 귀속비율 | New calc | `비지배주주순이익 / 당기순이익` |
| Section 7 | 5대 체크리스트 | New logic | Boolean evaluations of health indicators |

### 6.4 Data Availability Summary

| Data Source | Available Now | Notes |
|-------------|---------------|-------|
| `df_fs_ann` index items | All B/S, P/L, CF accounts | CF tables fetched but not surfaced |
| `df_anal` | 자본구조, 3대수익률, 예상손익 | Already computed |
| `df_invest` | 4개 자산 분류 | Already computed |
| `report` dict | 시가총액, 주식수, 베타, PER, PBR | Beta available for Ke |
| Consensus `df_cons` | ROE, EPS forecasts | Available but not used in analysis |

---

## 7. Reference Implementations Found

### 7.1 B/S Reclassification (COMPLETE MATCH)

`fnguide/analysis.py` lines 59-145 implement the exact B/S reclassification mapping defined in `srim-dashboard-spec.md` Appendix B. The account groupings are identical.

### 7.2 3-Rate Decomposition (COMPLETE MATCH)

`fnguide/analysis.py` lines 204-276 implement the 3-rate decomposition with weighted average and 1순위 selection exactly as specified in `srim-dashboard-spec.md` Section C.

### 7.3 Profit Waterfall (COMPLETE MATCH)

`fnguide/analysis.py` lines 280-315 implement the profit waterfall calculation steps 1-7 from `srim-dashboard-spec.md` Appendix E.

### 7.4 Chart Endpoint Pattern (REFERENCE FOR NEW ENDPOINT)

`backend/routers/chart.py` + `backend/schemas/chart.py` + `backend/services/chart_service.py` is the exact 3-layer pattern to replicate for the analysis endpoint.

### 7.5 Legacy CFO Data Access (FROM LEGACY CODE)

`rim_fnguide/rim_fnguide_ver20.py` line 2837 confirms `영업활동으로인한현금흐름` is a valid index key in `df_fs_ann`.

---

## 8. Architecture Risks and Constraints

### 8.1 fnguide Crawling Latency

- `analyze_comp(code)` involves 3 HTTP requests with 0.1s delays
- Typical total latency: 2-5 seconds (network dependent)
- **Risk**: Frontend dashboard will feel slow on first load
- **Mitigation**: Show loading spinner; consider backend caching (TTL ~1 hour)

### 8.2 Account Name Variability

- FnGuide HTML account names may vary slightly between companies
- Current code uses `KeyError`-safe try/except for IFRS(별도) specific accounts
- **Risk**: Missing accounts for GPM (`매출총이익`) or CFO if FnGuide doesn't include them for some companies
- **Mitigation**: Use `df_fs_ann.loc.get('account_name', default_series)` pattern or try/except

### 8.3 pandas 3.0 Compatibility

- Existing tests note `read_snapshot` can fail with `FileNotFoundError` on pandas 3.0 (StringIO issue)
- **Impact**: `analyze_comp` pipeline may fail in some environments
- **Mitigation**: Already handled in existing code; new code should follow same try/except patterns

### 8.4 CAPM Ke Calculation Complexity

- Section 4 requires `Spread = ROE - Ke` where `Ke = Rf + Beta × MRP`
- `Beta` is available from `report['베타(1년)']` in the snapshot
- `Rf` (risk-free rate) and `MRP` (market risk premium) are external constants
- **Risk**: Hard-coded values may not reflect current market conditions
- **Recommendation**: Use configurable defaults (Rf=3.5%, MRP=5.5%) or omit Ke initially

### 8.5 Frontend Modal State Management

- Current app has no modal system
- Need to decide: local state in ChartGrid, new context, or prop drilling
- **Recommendation**: Local state `analysisCode: string | null` in ChartGrid, passed to a new `AnalysisModal` component

### 8.6 Total Asset Calculation

- `총자산 = df_fs_ann.loc['자산']` (confirmed by `test_crawler.py` line 44: `"자산"` is a required index item)
- Note: FnGuide uses `"자산"` not `"자산총계"` as the account name

---

## 9. Files to Create/Modify

### 9.1 fnguide Package Extensions

| File | Action | Changes |
|------|--------|---------|
| `fnguide/analysis.py` | Modify | Add `DashboardData` dataclass or extend `fs_analysis()` to return additional data: GPM, CFO, YoY growth, health indicators |
| `fnguide/analyzer.py` | Modify | Add `analyze_dashboard(code) -> DashboardResult` or extend `CompResult` with dashboard fields |
| `fnguide/__init__.py` | Modify | Export new types |

### 9.2 Backend Layer (New Files)

| File | Action | Content |
|------|--------|---------|
| `backend/schemas/analysis.py` | Create | Pydantic models: `AnalysisResponse`, `SectionPerformance`, `SectionFunding`, `SectionAssets`, `SectionRates`, `SectionWaterfall`, `HealthIndicators` |
| `backend/services/analysis_service.py` | Create | Service calling `analyze_comp()` + dashboard computations |
| `backend/routers/analysis.py` | Create | `GET /api/analysis/{code}` router |
| `backend/main.py` | Modify | Register analysis router |

### 9.3 Frontend Layer (New Files)

| File | Action | Content |
|------|--------|---------|
| `frontend/src/types/analysis.ts` | Create | TypeScript interfaces mirroring `AnalysisResponse` |
| `frontend/src/api/analysis.ts` | Create | `fetchAnalysis(code: string)` function |
| `frontend/src/components/Dashboard/AnalysisModal.tsx` | Create | Modal with 7 dashboard sections |
| `frontend/src/components/Dashboard/` | Create dir | Section components (optional) |
| `frontend/src/components/ChartGrid/ChartCell.tsx` | Modify | Add `FS` analysis button to header |
| `frontend/src/components/ChartGrid/ChartGrid.tsx` | Modify | Manage `analysisCode` state, render `AnalysisModal` |

### 9.4 Test Files

| File | Action | Content |
|------|--------|---------|
| `tests/fnguide/test_analysis.py` | Modify | Add tests for new dashboard computations |
| `tests/test_analysis_service.py` | Create | Backend service unit tests (mock fnguide) |
| `tests/test_api.py` | Modify | Add `GET /api/analysis/{code}` endpoint tests |

---

## 10. Recommended Implementation Approach

### Phase 1: fnguide Engine Extension

1. Add `dashboard_analysis()` function to `fnguide/analysis.py` that takes `(df_fs_ann, df_fs_quar, df_anal, df_invest, report)` and returns a new `DashboardResult` dataclass with:
   - Section 1 data: GPM, CFO, YoY growth rates, profit quality
   - Section 2 data: Health indicators with threshold signals
   - Section 3 data: Asset ratios and breakdown
   - Section 4 data: Already in df_anal, add Spread if Ke provided
   - Section 5 data: Already in df_anal (profit waterfall)
   - Section 7 data: Checklist boolean evaluations

2. Add `analyze_dashboard(code: str) -> DashboardResult` to `fnguide/analyzer.py`

### Phase 2: Backend API

1. Create Pydantic schemas for `DashboardResult` serialization
2. Create `analysis_service.py` calling `analyze_dashboard()`
3. Create router `GET /api/analysis/{code}` with 503 for crawler failures

### Phase 3: Frontend

1. Create `AnalysisModal` component with tabbed or scrollable sections
2. Add `FS` button to `ChartCell` header
3. Manage modal state in `ChartGrid`

---

## Appendix: Key File Line References

| File | Key Lines | Description |
|------|-----------|-------------|
| `fnguide/analysis.py:39` | `fs_analysis()` | Main analysis function signature |
| `fnguide/analysis.py:64-76` | 신용조달 | 영업부채 reclassification |
| `fnguide/analysis.py:78-86` | 외부차입 | Debt reclassification |
| `fnguide/analysis.py:204-276` | Rate calculations | 3-rate decomposition and 1순위 selection |
| `fnguide/analysis.py:280-315` | Profit waterfall | Expected profit calculations |
| `fnguide/crawler.py:169-197` | `read_fs()` | Fetches 6 HTML tables, concatenates all |
| `fnguide/analyzer.py:39-93` | Data classes | `RateHistory`, `ProfitTrend`, `CompResult` |
| `fnguide/analyzer.py:147-263` | `analyze_comp()` | Orchestrator with full pipeline |
| `rim_fnguide/rim_fnguide_ver20.py:204-205` | Legacy GPM | Confirms `매출총이익` account name |
| `rim_fnguide/rim_fnguide_ver20.py:2837` | Legacy CFO | Confirms `영업활동으로인한현금흐름` account name |
| `backend/routers/chart.py:18-55` | Chart router | Reference pattern for new analysis router |
| `backend/schemas/chart.py:8-56` | Chart schemas | Reference pattern for new analysis schemas |
| `backend/services/chart_service.py:14-91` | Chart service | Reference pattern for new analysis service |
| `backend/main.py:1-68` | App setup | Where to register new router |
| `frontend/src/components/ChartGrid/ChartCell.tsx:228-257` | Header buttons | Where to add analysis button |
| `frontend/src/components/ChartGrid/ChartGrid.tsx:1-93` | Grid container | Where to add modal state |
| `frontend/src/api/chart.ts:1-9` | API function | Reference for new analysis API function |
| `frontend/src/types/stock.ts:1-35` | Type definitions | Reference for new analysis types |
