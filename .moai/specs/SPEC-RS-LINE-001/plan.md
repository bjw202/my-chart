# SPEC-RS-LINE-001: Implementation Plan

## TAG: SPEC-RS-LINE-001

## Overview

Add RS Line (Relative Strength Line = Stock Price / KOSPI Index) visualization to the chart, following IBD-style overlay with hidden axis. Implementation spans the full stack: DB schema, data pipeline, API, and frontend chart rendering.

## Milestones

### Milestone 1: Daily DB RS_Line Data Pipeline (Priority High)

**Goal:** Add RS_Line column to daily DB and populate during DB update.

**Tasks:**
1. Modify `my_chart/db/daily.py` schema: add `RS_Line REAL` column to `stock_prices`
2. Add migration logic: `ALTER TABLE stock_prices ADD COLUMN RS_Line REAL` with error handling for existing DBs
3. Fetch KOSPI daily close data during daily DB generation using `price_naver("KOSPI", ...)`
4. Calculate `RS_Line = stock Close / KOSPI Close` for each stock during daily DB insert
5. Handle missing KOSPI data gracefully (RS_Line = NULL for affected dates)

**Technical Approach:**
- KOSPI data should be fetched once at the start of the daily DB update cycle and held in memory as a date-indexed Series
- Join stock dates with KOSPI dates for RS_Line calculation
- Use pandas merge/join for date alignment (some dates may not match due to holidays)

**Risks:**
- KOSPI data fetch failure: Mitigate by allowing partial RS_Line (NULL for missing dates)
- Date alignment: KOSPI and individual stocks may have slightly different trading days. Use `merge(how='left')` to keep all stock dates, filling missing KOSPI values with NaN

**Files:**
- `my_chart/db/daily.py` (primary)
- `my_chart/price.py` (reference for KOSPI fetch pattern)

### Milestone 2: Chart API RS Line Response (Priority High)

**Goal:** Include RS_Line data in the chart API response.

**Tasks:**
1. Add `rs_line: list[MAPoint] = []` to `ChartResponse` in `backend/schemas/chart.py`
2. Update `get_chart_data()` in `chart_service.py` to query RS_Line column
3. Update `get_weekly_chart_data()` to query RS_Line column from weekly DB
4. Build RS Line data points, filtering out NULL values
5. Return rs_line in ChartResponse

**Technical Approach:**
- Reuse existing `MAPoint` schema (time + value) for RS Line data points
- Add RS_Line to the SELECT query in both daily and weekly chart services
- Default to empty array when RS_Line column doesn't exist (backward compat with old DBs)

**Risks:**
- Old DBs without RS_Line column: Use `sqlite3.OperationalError` catch or conditional query
- Performance: No risk since RS_Line is just one additional column in existing query

**Files:**
- `backend/schemas/chart.py`
- `backend/services/chart_service.py`

### Milestone 3: Frontend RS Line Rendering (Priority High)

**Goal:** Display RS Line on the chart with IBD-style hidden axis overlay.

**Tasks:**
1. Add `rs_line: MAPoint[]` to `ChartResponse` TypeScript interface
2. In `ChartCell.tsx`, add RS Line series using `chart.addLineSeries()` with dedicated `priceScaleId`
3. Configure RS Line price scale: hidden axis, appropriate margins
4. Set RS Line styling: purple color (#6c5ce7), lineWidth 2, no price line, no last value
5. Load RS Line data from API response via `rsLineSeries.setData()`

**Technical Approach:**
- Use `priceScaleId: 'rs-line'` for independent scaling
- Set `priceScale('rs-line').applyOptions({ visible: false, scaleMargins: { top: 0.1, bottom: 0.3 } })`
- RS Line auto-scales within its margin region, no manual normalization needed
- Clean up RS Line series in the useEffect cleanup function

**Risks:**
- Visual overlap with MA lines: Mitigate with distinct color and wider line
- Chart performance with additional series: Negligible (just one more line series)

**Files:**
- `frontend/src/types/chart.ts`
- `frontend/src/components/ChartGrid/ChartCell.tsx`

### Milestone 4: RS Line Toggle (Priority Low, Optional)

**Goal:** Allow users to show/hide RS Line via UI toggle.

**Tasks:**
1. Add RS toggle button to `ChartCell` header (similar to existing measure/watchlist buttons)
2. Manage toggle state with React useState (session-scoped)
3. Show/hide RS Line series using `rsLineSeries.applyOptions({ visible })` or conditional rendering

**Technical Approach:**
- Session-level state (not persisted to localStorage)
- Toggle shows/hides the line without re-fetching data
- Consider a global toggle vs per-chart toggle

**Files:**
- `frontend/src/components/ChartGrid/ChartCell.tsx`

## Architecture Design Direction

```
                    Daily DB Update Flow
                    ====================
price_naver("KOSPI", daily)
      |
      v
  KOSPI Close prices (in-memory Series, indexed by date)
      |
      v
  For each stock:
    price_naver(stock, daily) -> stock Close prices
    RS_Line = stock Close / KOSPI Close
    INSERT INTO stock_prices (... RS_Line ...)

                    API Request Flow
                    ================
GET /api/chart/{code}?timeframe=daily
      |
      v
  chart_service.get_chart_data(code)
      |
      v
  SELECT ... RS_Line FROM stock_prices WHERE Name = ?
      |
      v
  ChartResponse { candles, volume, ma, rs_line: [{time, value}, ...] }

                    Frontend Rendering
                    ==================
  ChartCell receives ChartResponse
      |
      v
  chart.addLineSeries({ priceScaleId: 'rs-line' })
  priceScale('rs-line').visible = false
  rsLineSeries.setData(data.rs_line)
```

## Dependency Order

```
Milestone 1 (DB) -> Milestone 2 (API) -> Milestone 3 (Frontend) -> Milestone 4 (Toggle)
```

Milestones must be implemented sequentially as each depends on the previous layer.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| KOSPI data unavailable during DB update | Low | Medium | Allow NULL RS_Line, log warning |
| Date alignment mismatch (stock vs KOSPI) | Medium | Low | Left join on dates, NULL for missing |
| Old DB without RS_Line column | High | Low | ALTER TABLE migration with error handling |
| RS Line visually overlaps important chart data | Medium | Low | Distinct color + adjustable margins |
| TradingView hidden axis doesn't scale well | Low | Medium | Test with various stock price ranges |
| Weekly DB RS_Line column naming differs | Low | Low | Verify column name in weekly schema |

## Testing Strategy

- **Unit tests:** RS_Line calculation correctness (stock price / KOSPI close)
- **Integration tests:** Chart API returns rs_line field with valid data
- **Edge cases:** Stocks with no KOSPI overlap dates, newly listed stocks, delisted stocks
- **Visual verification:** RS Line displays correctly across different price ranges (penny stocks vs blue chips)
- **Regression:** Existing chart functionality unaffected when rs_line is empty
