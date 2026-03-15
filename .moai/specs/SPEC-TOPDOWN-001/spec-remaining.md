# SPEC-TOPDOWN-001-REMAINING: Unimplemented Items from Top-Down Market Analysis System

## Overview

**Parent SPEC**: SPEC-TOPDOWN-001 (A through E)
**Branch**: feature/sector-rotation
**Methodology**: TDD (RED-GREEN-REFACTOR)
**Scope**: Backend API enhancements + Frontend UI completion
**Status**: Gap analysis of implemented SPEC-TOPDOWN-001A~E

This document captures all remaining unimplemented items from the original SPEC-TOPDOWN-001 and organizes them into prioritized implementation phases.

---

## Gap Summary

| # | Item | Priority | Domain | Original SPEC |
|---|------|----------|--------|---------------|
| R1 | Chart Grid stockCodes reception | High | Frontend | 001E R6 |
| R2 | Chart Grid Stage badge | High | Full-stack | 001E R5 |
| R3 | Sector Detail Panel sub-sector + Top 5 | High | Full-stack | 001D R2 |
| R4 | 12-week Sparkline | Medium | Frontend | 001E R2 |
| R5 | Key Checklist indicators | Medium | Frontend | 001E R2 |
| R6 | Market Filter (KOSPI/KOSDAQ) | Medium | Full-stack | 001D R4 |
| R7 | Weekly Highlights Stage 2 count | Medium | Frontend | 001C R4 |
| R8 | API response time < 500ms verification | Low | Backend | 001A AC11 |
| R9 | Backend 85%+ test coverage verification | Low | Backend | 001A AC12 |

---

## Requirements (EARS Format)

### R1: Chart Grid stockCodes Reception

**Original**: SPEC-TOPDOWN-001E R6 (Cross-tab Stock Selection)

**Current State**: `navigateToTab('chart-grid', { stockCodes })` is called in StockExplorer but ChartGrid does not consume `crossTabParams.stockCodes`. The ChartGrid component has no reference to `crossTabParams` or `stockCodes` at all.

**Requirement (Event-Driven)**:

- WHEN the Chart Grid tab becomes active AND `crossTabParams.stockCodes` is present,
- THE system SHALL load charts for the specified stock codes into the Chart Grid,
- AND clear `crossTabParams` after processing.

- WHEN `crossTabParams.stockCodes` contains codes not in the current screen results,
- THE system SHALL fetch chart data for those codes directly via `/api/chart/{code}`,
- AND display them alongside any existing charts.

**Frontend Changes**:

| File | Change |
|------|--------|
| `frontend/src/components/ChartGrid/ChartGrid.tsx` (or parent) | Read `crossTabParams.stockCodes` from `useTab()`, call `clearCrossTabParams()`, update displayed stocks |
| `frontend/src/contexts/ScreenContext.tsx` | May need method to inject external stock codes into the grid |

**Acceptance Criteria**:

- Given 2 stocks selected in Stock Explorer
- When the user clicks "View Charts"
- Then Chart Grid tab activates with exactly those 2 stock charts displayed

- Given Chart Grid already has charts displayed
- When new stockCodes arrive via crossTabParams
- Then Chart Grid replaces current charts with the new stock codes

---

### R2: Chart Grid Stage Badge

**Original**: SPEC-TOPDOWN-001E R5 (Chart Grid Stage/RS Badge)

**Current State**: ChartCell shows RS badge only. The `/api/screen` endpoint does not include `stage` data in its response. The ChartCell component has an RS badge but no Stage badge.

**Requirement (Event-Driven)**:

- WHEN the Chart Grid renders a ChartCell for a stock,
- THE system SHALL display a Stage badge (S1/S2/S2+/S3/S4) in the chart cell header,
- AND the Stage badge SHALL use the same color scheme as Stock Explorer:
  - S1: yellow, S2: green, S2+ (entry candidate): dark green with star, S3: orange, S4: red
- AND the Stage badge SHALL appear alongside the existing RS badge.

**Backend Changes**:

| File | Change |
|------|--------|
| `backend/schemas/screen.py` | Add `stage: str` and `stage_detail: str` fields to screen response schema |
| `backend/services/screen_service.py` | Join or compute stage data when building screen results; use `stage_classifier.classify_stage()` or pre-computed stage from `/api/stage/overview` data |

**Frontend Changes**:

| File | Change |
|------|--------|
| `frontend/src/components/ChartGrid/ChartCell.tsx` | Add Stage badge component next to RS badge |
| `frontend/src/types/stock.ts` | Add `stage` and `stage_detail` fields to stock type |

**API Change**:

The `/api/screen` response for each stock should include:
```json
{
  "code": "005930",
  "name": "Samsung Electronics",
  "stage": "2",
  "stage_detail": "Stage 2 Strong",
  "rs_rating": 85,
  ...
}
```

**Acceptance Criteria**:

- Given a stock classified as Stage 2 Strong (RS > 60)
- When it appears in Chart Grid
- Then ChartCell header shows [S2+] badge in dark green AND [RS 85] badge

- Given a stock classified as Stage 4
- When it appears in Chart Grid
- Then ChartCell header shows [S4] badge in red

---

### R3: Sector Detail Panel Sub-sector + Top 5 Stocks

**Original**: SPEC-TOPDOWN-001D R2 (Sector Detail Panel)

**Current State**: SectorDetailPanel displays excess return bars and metric cards but shows a placeholder message "Sub-sector analysis will be available in a future update" (in Korean). No sub-sector breakdown or top 5 stocks are shown.

**Requirement (Event-Driven)**:

- WHEN the user clicks a sector row in SectorRankingTable,
- THE SectorDetailPanel SHALL display:
  1. Sub-sector breakdown: a table of sub-sectors (saneopmyeong-jung / industry name medium level) with columns: name, stock count, RS avg, stage2_pct, 1W excess return
  2. Top 5 stocks by RS rating within the selected sector, showing: code, name, RS rating, stage badge, 1M return

- WHEN the user clicks a sub-sector row,
- THE system SHALL navigate to Stock Explorer with that sub-sector as a filter.

- WHEN the user clicks a stock in the Top 5 list,
- THE system SHALL navigate to Chart Grid with that stock loaded.

**Backend Changes**:

Option A (Expand existing endpoint):
| File | Change |
|------|--------|
| `backend/services/sector_service.py` (or equivalent) | Add sub-sector computation: group stocks by `sector_minor` within a given `sector_major`, compute RS avg and stage2_pct per sub-sector |
| API route handler | Add query parameter `?detail=true&sector=<name>` to `/api/sectors/ranking` OR create new endpoint `/api/sectors/{name}/detail` |

Option B (New endpoint - recommended):

```
GET /api/sectors/{sector_name}/detail
Response: {
  sector_name: string,
  sub_sectors: [
    {
      name: string,           // saneopmyeong-jung
      stock_count: int,
      rs_avg: float,
      stage2_pct: float,
      excess_return_1w: float
    }
  ],
  top_stocks: [
    {
      code: string,
      name: string,
      rs_12m: float,
      stage: string,
      stage_detail: string,
      chg_1m: float
    }
  ]
}
```

**Backend Implementation**:

| File | Change |
|------|--------|
| `my_chart/analysis/sector_metrics.py` | Add `compute_sector_detail(db_path, sector_name, date)` returning sub-sector breakdown and top 5 stocks |
| `backend/services/sector_service.py` | New service method for sector detail |
| `backend/schemas/sector.py` (new or extend) | Response schema for sector detail |
| `backend/main.py` or router | New route `/api/sectors/{sector_name}/detail` |

**Frontend Changes**:

| File | Change |
|------|--------|
| `frontend/src/components/SectorAnalysis/SectorDetailPanel.tsx` | Replace placeholder with sub-sector table and top 5 stocks list; add click handlers for cross-tab navigation |
| `frontend/src/api/sector.ts` | Add `fetchSectorDetail(sectorName)` API call |
| `frontend/src/types/sector.ts` | Add `SectorDetail`, `SubSector`, `TopStock` types |

**Acceptance Criteria**:

- Given the user selects "Semiconductor" (bando-che) sector
- When SectorDetailPanel opens
- Then sub-sectors like "Semiconductor Manufacturing", "Semiconductor Equipment" appear with metrics

- Given top 5 stocks are displayed
- When the user clicks on a stock name
- Then Chart Grid opens with that stock's chart

---

### R4: 12-Week Sparkline

**Original**: SPEC-TOPDOWN-001E R2 (Stock Table with Stage - sparkline column)

**Current State**: StockTable displays Name, Market, Stage, RS, 1M%, Vol Ratio columns. No sparkline column exists. A `Sparkline.tsx` component file may or may not exist.

**Requirement (State-Driven)**:

- WHILE the Stock Explorer tab is active,
- THE StockTable SHALL display a 12-week mini price chart (sparkline) for each stock row,
- WHERE the sparkline shows weekly closing prices for the most recent 12 weeks,
- AND the sparkline uses green color for uptrend (last close > first close) and red for downtrend.

**Data Requirement**:

The `/api/stage/overview` response currently returns stock data but does not include price history. Two approaches:

Option A: Add `price_history_12w: number[]` to each stock in the stage overview response.
Option B: Create a lightweight batch endpoint `/api/stocks/sparkline?codes=005930,000660,...` that returns 12-week close prices for multiple stocks.

Option A is simpler but increases the stage overview payload size significantly (2,551 stocks x 12 data points). Option B is recommended for performance.

**Frontend Changes**:

| File | Change |
|------|--------|
| `frontend/src/components/StockExplorer/Sparkline.tsx` | Create (or complete) inline SVG or canvas sparkline component |
| `frontend/src/components/StockExplorer/StockTable.tsx` | Add sparkline column to table |
| `frontend/src/api/stage.ts` | Add sparkline data fetch if using batch endpoint |

**Acceptance Criteria**:

- Given a stock with 12 weeks of price data [100, 102, 105, 103, 108, 110, 107, 112, 115, 113, 118, 120]
- When displayed in Stock Explorer
- Then a green upward-trending mini line chart appears in the sparkline column

---

### R5: Key Checklist Indicators

**Original**: SPEC-TOPDOWN-001E R2 (Stock Table - Key checklist column)

**Current State**: Not implemented. The StockTable has no checklist column.

**Requirement (State-Driven)**:

- WHILE the Stock Explorer tab is active,
- THE StockTable SHALL display visual indicators for each stock:
  1. **MA Alignment**: checkmark if Close > SMA50 > SMA200 (bullish alignment)
  2. **Volume Surge**: checkmark if volume_ratio > 1.5
  3. **RS Strength**: checkmark if RS_12M >= 70

- WHERE each indicator shows a green checkmark when met and a gray dash when not met.

**Data Requirement**:

The `/api/stage/overview` response already includes `close`, `sma50`, `sma200`, `volume_ratio`, and `rs_12m` for stage2_candidates. For all stocks (not just candidates), these fields need to be available. Verify that the full stock list in stage overview includes these fields.

**Frontend Changes**:

| File | Change |
|------|--------|
| `frontend/src/components/StockExplorer/StockTable.tsx` | Add checklist column with 3 visual indicators |
| `frontend/src/components/StockExplorer/KeyChecklist.tsx` | New component for the 3-indicator display |

**Acceptance Criteria**:

- Given a stock with Close > SMA50 > SMA200, volume_ratio = 2.0, RS = 80
- When displayed in Stock Explorer
- Then all three checkmarks appear in green

- Given a stock with Close < SMA50, volume_ratio = 0.8, RS = 45
- When displayed in Stock Explorer
- Then all three indicators show gray dashes

---

### R6: Market Filter (KOSPI/KOSDAQ)

**Original**: SPEC-TOPDOWN-001D R4 (Market Filter)

**Current State**: SectorRankingTable shows all sectors without market filtering. The backend `/api/sectors/ranking` does not accept a `market` query parameter.

**Requirement (Event-Driven)**:

- WHEN the user toggles KOSPI/KOSDAQ/ALL filter in Sector Analysis tab,
- THE system SHALL show sector rankings computed from only the selected market's stocks.

**Backend Changes**:

| File | Change |
|------|--------|
| `my_chart/analysis/sector_metrics.py` | Add `market` parameter to `compute_sector_ranking()` to filter stocks by market before aggregation |
| API route handler | Accept `?market=KOSPI` or `?market=KOSDAQ` query parameter on `/api/sectors/ranking` |

**Frontend Changes**:

| File | Change |
|------|--------|
| `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx` | Add market toggle buttons [ALL] [KOSPI] [KOSDAQ] |
| `frontend/src/api/sector.ts` | Pass `market` parameter to API call |
| `frontend/src/contexts/MarketContext.tsx` | Optionally store selected market filter |

**Acceptance Criteria**:

- Given the user selects KOSPI filter
- When sector ranking table renders
- Then rankings are computed from KOSPI stocks only

- Given the user selects ALL
- When sector ranking table renders
- Then rankings include both KOSPI and KOSDAQ stocks

---

### R7: Weekly Highlights Stage 2 Count

**Original**: SPEC-TOPDOWN-001C R4 (Weekly Highlights - Stage 2 entry count change)

**Current State**: WeeklyHighlights shows market phase and biggest sector rank movers. Stage 2 entry count section is deferred (marked with `@MX:NOTE` comment: "Stage 2 deferred to 001E").

**Requirement (State-Driven)**:

- WHILE the Market Overview tab is active,
- THE WeeklyHighlights component SHALL display a "Stage 2 Entries" section showing:
  - Current count of Stage 2 stocks
  - Change vs previous week (e.g., "+5" or "-3")
  - Link/button to navigate to Stock Explorer filtered to Stage 2

**Data Requirement**:

Stage 2 count is available from `/api/stage/overview` (`distribution.stage2`). However, week-over-week change requires either:
- Backend stores previous week's stage distribution (preferred)
- Frontend caches previous week's data (fragile)

Recommended: Add `stage2_count_change` field to `/api/market/overview` response, computed by comparing current vs 1-week-ago stage distribution.

**Backend Changes**:

| File | Change |
|------|--------|
| `my_chart/analysis/market_breadth.py` or new utility | Compute stage 2 count for current and previous week, return delta |
| API route handler for `/api/market/overview` | Add `stage2_count` and `stage2_count_change` fields to response |

**Frontend Changes**:

| File | Change |
|------|--------|
| `frontend/src/components/MarketOverview/WeeklyHighlights.tsx` | Add Stage 2 entry section with count, change indicator, and navigation link |
| `frontend/src/types/market.ts` | Add stage2 fields to market overview type |

**Acceptance Criteria**:

- Given current Stage 2 count is 120 and last week was 115
- When WeeklyHighlights renders
- Then "Stage 2 Entries: 120 (+5)" is displayed with green indicator

---

### R8: API Response Time < 500ms Verification

**Original**: SPEC-TOPDOWN-001A AC11

**Requirement (Ubiquitous)**:

- THE system SHALL respond to all API endpoints within 500ms for the full market dataset (approximately 2,551 stocks).

**Verification Approach**:

| Endpoint | Target | Method |
|----------|--------|--------|
| `/api/market/overview` | < 500ms | pytest benchmark or manual timing |
| `/api/sectors/ranking` | < 500ms | pytest benchmark or manual timing |
| `/api/stage/overview` | < 500ms | pytest benchmark or manual timing |
| `/api/screen` (POST) | < 500ms | pytest benchmark or manual timing |

**Implementation**:

- Add response time logging middleware or timing decorator to backend
- Create performance test suite with realistic data volume
- If any endpoint exceeds 500ms, profile and optimize (caching, query optimization, pre-computation)

**Acceptance Criteria**:

- Given the full market dataset (2,551 stocks)
- When each API endpoint is called
- Then response time is under 500ms (P95)

---

### R9: Backend 85%+ Test Coverage Verification

**Original**: SPEC-TOPDOWN-001A AC12

**Requirement (Ubiquitous)**:

- THE backend modules SHALL maintain 85%+ test coverage for all new analysis modules:
  - `my_chart/analysis/market_breadth.py`
  - `my_chart/analysis/stage_classifier.py`
  - `my_chart/analysis/sector_metrics.py`
  - `backend/services/` (all service modules)

**Verification Approach**:

- Run `pytest --cov=my_chart/analysis --cov=backend/services --cov-report=term-missing`
- Identify uncovered lines and add tests
- Focus on edge cases: empty datasets, single stock sectors, boundary conditions for stage classification

**Acceptance Criteria**:

- Given all backend analysis and service modules
- When coverage report is generated
- Then overall coverage is >= 85% with no module below 75%

---

## Implementation Phases

### Phase 1: High Priority - Core Feature Gaps (R1, R2, R3)

**Goal**: Complete the cross-tab navigation flow and essential data display.

**Dependencies**: None (builds on existing infrastructure)

**Tasks**:

1. **R1 - Chart Grid stockCodes reception**
   - Frontend only
   - Estimated files: 2-3
   - Risk: Low (pattern exists in StockExplorer for crossTabParams)

2. **R2 - Chart Grid Stage badge**
   - Backend: Add stage field to screen response
   - Frontend: Add Stage badge component to ChartCell
   - Estimated files: 4-5
   - Risk: Medium (requires backend schema change)

3. **R3 - Sector Detail sub-sector + Top 5**
   - Backend: New endpoint or expanded endpoint
   - Frontend: Replace placeholder in SectorDetailPanel
   - Estimated files: 6-8
   - Risk: Medium (new backend computation + API endpoint)

### Phase 2: Medium Priority - UX Enhancements (R4, R5, R6, R7)

**Goal**: Complete Stock Explorer table features and Sector Analysis filtering.

**Dependencies**: Phase 1 completion recommended but not strictly required

**Tasks**:

4. **R6 - Market Filter (KOSPI/KOSDAQ)** - start here, simpler
   - Backend: Add market parameter to sector ranking
   - Frontend: Add toggle buttons
   - Estimated files: 3-4

5. **R7 - Weekly Highlights Stage 2 count**
   - Backend: Add stage2 count/change to market overview
   - Frontend: Update WeeklyHighlights component
   - Estimated files: 3-4

6. **R5 - Key Checklist indicators**
   - Frontend only (data may already exist)
   - Estimated files: 2-3

7. **R4 - 12-week Sparkline**
   - May need backend batch endpoint
   - Frontend: Sparkline rendering component
   - Estimated files: 3-5
   - Risk: Medium (performance concern with many inline charts)

### Phase 3: Low Priority - Quality Verification (R8, R9)

**Goal**: Verify and enforce quality standards.

**Dependencies**: All feature work should be complete

**Tasks**:

8. **R8 - API response time verification**
   - Add performance tests / benchmarks
   - Profile and optimize if needed
   - Estimated files: 1-3

9. **R9 - Test coverage verification**
   - Run coverage report, add missing tests
   - Estimated files: varies

---

## Dependency Analysis

```
R1 (Chart Grid stockCodes) ── no dependencies, can start immediately
R2 (Stage badge) ── depends on backend screen schema update
R3 (Sub-sector detail) ── depends on new backend endpoint
R4 (Sparkline) ── may depend on new backend batch endpoint
R5 (Key Checklist) ── depends on stage overview data availability
R6 (Market Filter) ── depends on backend parameter support
R7 (Stage 2 count) ── depends on backend stage count computation
R8 (Response time) ── should run after all backend changes
R9 (Test coverage) ── should run after all backend changes
```

**Parallelization Opportunities**:

- R1 (frontend only) can be done in parallel with any backend work
- R2 backend + R3 backend can be developed together (both modify backend schemas)
- R5 (frontend only) can be done in parallel with R6/R7 backend work
- R8 and R9 are independent verification tasks

---

## API Changes Summary

### Modified Endpoints

| Endpoint | Change | Reason |
|----------|--------|--------|
| `POST /api/screen` | Add `stage`, `stage_detail` fields to response | R2: Stage badge in ChartGrid |
| `GET /api/sectors/ranking` | Add optional `?market=KOSPI\|KOSDAQ` parameter | R6: Market filter |
| `GET /api/market/overview` | Add `stage2_count`, `stage2_count_change` fields | R7: Weekly Highlights |

### New Endpoints

| Endpoint | Purpose | Reason |
|----------|---------|--------|
| `GET /api/sectors/{name}/detail` | Sub-sector breakdown + top 5 stocks | R3: Sector Detail Panel |
| `GET /api/stocks/sparkline?codes=...` (optional) | Batch 12-week price history | R4: Sparkline (if needed) |

---

## Frontend Changes Summary

| Component | File | Changes |
|-----------|------|---------|
| ChartGrid | `ChartGrid.tsx` or parent | Consume `crossTabParams.stockCodes` (R1) |
| ChartCell | `ChartCell.tsx` | Add Stage badge (R2) |
| SectorDetailPanel | `SectorDetailPanel.tsx` | Sub-sector table + Top 5 stocks (R3) |
| StockTable | `StockTable.tsx` | Add Sparkline column (R4), Key Checklist column (R5) |
| Sparkline | `Sparkline.tsx` (new) | 12-week inline chart component (R4) |
| KeyChecklist | `KeyChecklist.tsx` (new) | 3-indicator visual component (R5) |
| SectorAnalysis | `SectorAnalysis.tsx` | Market filter toggle (R6) |
| WeeklyHighlights | `WeeklyHighlights.tsx` | Stage 2 entry count section (R7) |

---

## Technical Notes

1. **Stage data in screen response**: The screen service currently queries `stock_prices` and `relative_strength` tables. Stage classification uses `stage_classifier.classify_stage()` which operates on the same data. The most efficient approach is to join stage classification during screen service execution rather than making a separate API call.

2. **Sparkline performance**: Rendering 2,551 inline SVG sparklines simultaneously will cause performance issues. Consider:
   - Virtual scrolling (only render visible rows)
   - Canvas-based sparkline instead of SVG
   - Lazy loading sparkline data on scroll

3. **Sub-sector data availability**: The `sector_minor` field (saneopmyeong-jung) exists in `stock_meta` table. Grouping and aggregation should be straightforward using existing query patterns in `sector_metrics.py`.

4. **Market filter impact on sector rankings**: When filtering by market (KOSPI only), some sectors may have very few stocks. Consider showing stock count prominently and hiding sectors with fewer than 3 stocks.

---

**Document Version**: 1.0
**Created**: 2026-03-15
**Parent SPEC**: SPEC-TOPDOWN-001
**Author**: manager-spec agent
