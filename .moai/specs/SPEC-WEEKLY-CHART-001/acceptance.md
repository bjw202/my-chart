# SPEC-WEEKLY-CHART-001: Acceptance Criteria

| Field       | Value                     |
|-------------|---------------------------|
| SPEC ID     | SPEC-WEEKLY-CHART-001     |
| Status      | Planned                   |

---

## AC-1: Weekly DB SMA Column Rename (R1, R3, R4)

**Given** the weekly DB generation code is updated with new column names
**When** `generate_price_db()` is executed (after deleting the old weekly .db file)
**Then**
- The `stock_prices` table contains columns: `SMA10`, `SMA20`, `SMA40`, `VolumeSMA10`
- The columns `MA50`, `MA150`, `MA200`, `Volume50MA` do NOT exist in the table
- `SMA10` values match `Close.rolling(window=10).mean()` for weekly bars
- `SMA20` values match `Close.rolling(window=20).mean()` for weekly bars
- `SMA40` values match `Close.rolling(window=40).mean()` for weekly bars

**Verification:**
```sql
-- Check column existence
PRAGMA table_info(stock_prices);
-- Verify SMA20 is NOT the same as old MA150 (window changed from 30 to 20)
SELECT Date, SMA10, SMA20, SMA40 FROM stock_prices WHERE Name = '삼성전자' ORDER BY Date DESC LIMIT 5;
```

---

## AC-2: SMA40 Trend Columns (R2)

**Given** SMA40 is computed during weekly DB generation
**When** the trend calculation runs
**Then**
- Columns `SMA40_Trend_1M`, `SMA40_Trend_2M`, `SMA40_Trend_3M`, `SMA40_Trend_4M` exist
- Values match `SMA40.pct_change(4 * months)` for each month period
- The old columns `MA200_Trend_1M` through `MA200_Trend_4M` do NOT exist

---

## AC-3: Meta Service Column Update (R5)

**Given** the weekly DB has new SMA column names
**When** `rebuild_stock_meta()` executes
**Then**
- `stock_meta` table contains columns `sma10_w`, `sma20_w`, `sma40_w`
- The old columns `ma50_w`, `ma150_w`, `ma200_w` do NOT exist
- Values are populated from weekly DB's latest-date snapshot

**Verification:**
```sql
-- In daily DB after meta rebuild
PRAGMA table_info(stock_meta);
SELECT code, name, sma10_w, sma20_w, sma40_w FROM stock_meta WHERE code = '005930';
```

---

## AC-4: Chart API Timeframe Parameter (R6, R14)

**Given** the chart endpoint supports the `timeframe` parameter
**When** client calls `GET /api/chart/005930` (no timeframe param)
**Then**
- Response is identical to current behavior (daily data)
- Response includes `"timeframe": "daily"`
- MA field contains `ema10`, `ema20`, `sma50`, `sma100`, `sma200`

**Given** the chart endpoint supports the `timeframe` parameter
**When** client calls `GET /api/chart/005930?timeframe=daily`
**Then**
- Response is identical to calling without the parameter

**Given** an invalid timeframe value
**When** client calls `GET /api/chart/005930?timeframe=monthly`
**Then**
- Response returns HTTP 400 with descriptive error message

---

## AC-5: Weekly Chart Data Response (R7, R8, R15)

**Given** weekly DB has been regenerated with new SMA columns
**When** client calls `GET /api/chart/005930?timeframe=weekly`
**Then**
- Response status is 200
- Response includes `"timeframe": "weekly"`
- `candles` array contains weekly OHLC bars ordered chronologically (oldest first)
- `ma.sma10` array has data points with `{time, value}` format
- `ma.sma20` array has data points with `{time, value}` format
- `ma.sma40` array has data points with `{time, value}` format
- Daily-specific MA fields (`ema10`, `ema20`, `sma50`, `sma100`, `sma200`) are empty or absent

---

## AC-6: Weekly Chart 404 Handling (R7)

**Given** a stock code that exists in daily DB but not in weekly DB
**When** client calls `GET /api/chart/{code}?timeframe=weekly`
**Then**
- Response returns HTTP 404 with `"error": "no_data"` detail

**Given** a completely unknown stock code
**When** client calls `GET /api/chart/999999?timeframe=weekly`
**Then**
- Response returns HTTP 404 with `"error": "stock_not_found"` detail

---

## AC-7: Frontend Timeframe Toggle Button (R10)

**Given** the ChartGrid component renders
**When** the user views the toolbar area
**Then**
- A timeframe toggle button is visible next to the grid size toggle
- Default label shows `D` (daily mode)
- Clicking the button switches label to `W` (weekly mode)
- Clicking again switches back to `D`

---

## AC-8: Chart Re-fetch on Toggle (R11)

**Given** daily charts are displayed for 4 stocks in a 2x2 grid
**When** the user clicks the timeframe toggle from D to W
**Then**
- All 4 chart cells show a loading spinner
- All 4 cells fetch `GET /api/chart/{code}?timeframe=weekly`
- On response, each cell displays weekly candlestick data
- MA overlay lines update to show SMA10/SMA20/SMA40 (3 lines)
- Loading spinner disappears after data renders

**When** the user toggles back from W to D
**Then**
- All cells re-fetch daily data and display 5 MA lines again

---

## AC-9: Weekly MA Color Scheme (R12)

**Given** the timeframe is `weekly`
**When** the chart renders MA overlays
**Then**
- SMA10 line renders in green (`#06d6a0`)
- SMA20 line renders in blue (`#118ab2`)
- SMA40 line renders in dark blue (`#073b4c`)
- No EMA10, EMA20, SMA50, SMA100, SMA200 lines are drawn

---

## AC-10: Weekly Visible Range (R13)

**Given** weekly chart data is loaded with ~200 weekly bars
**When** the chart finishes rendering
**Then**
- The initial visible range shows approximately 52 bars (1 year)
- The user can scroll left to see older weekly data
- Right offset margin of 5 bars is maintained

---

## Quality Gates

| Gate | Criterion | Threshold |
|------|----------|-----------|
| Schema Correctness | Weekly DB table_info matches new DDL | All SMA columns present, no old MA columns |
| API Backward Compat | `GET /chart/{code}` without timeframe returns daily data | 100% identical response structure |
| API Response | Weekly endpoint returns valid ChartResponse | Schema validation passes |
| Frontend Render | Toggle works without console errors | Zero JS errors in console |
| Data Integrity | SMA values match manual pandas calculation | Difference < 0.01% |
| No Stale References | Grep for `MA50`, `MA150`, `MA200` in weekly context | Zero matches in modified files |

---

## Definition of Done

- [ ] All 10 files modified per spec
- [ ] Weekly DB can be regenerated with new schema (SMA10/SMA20/SMA40)
- [ ] stock_meta rebuild works with new column names
- [ ] `GET /api/chart/{code}` (daily, no param) returns identical results to current behavior
- [ ] `GET /api/chart/{code}?timeframe=weekly` returns weekly data with correct MA fields
- [ ] Frontend toggle switches all visible charts between daily and weekly
- [ ] Weekly charts render 3 MA lines with correct colors
- [ ] No references to old column names remain in weekly-related code paths
- [ ] Volume display handles unit differences between daily and weekly
