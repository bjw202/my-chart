# SPEC-RS-LINE-001: Acceptance Criteria

## TAG: SPEC-RS-LINE-001

## Acceptance Scenarios

### AC-1: Daily DB RS_Line Column Exists

**Given** the daily DB update process has completed successfully,
**When** I inspect the `stock_prices` table schema in `daily_price.db`,
**Then** the table shall contain an `RS_Line REAL` column.

### AC-2: RS_Line Values Are Calculated Correctly

**Given** Samsung Electronics (005930) has a daily close of 70,000 KRW,
**And** KOSPI has a daily close of 2,600 on the same date,
**When** the daily DB update completes,
**Then** the RS_Line value for Samsung on that date shall be approximately 26.923 (70000 / 2600).

### AC-3: RS_Line Handles Missing KOSPI Data

**Given** a date where KOSPI daily data is unavailable,
**When** the daily DB update processes a stock with data on that date,
**Then** the RS_Line value for that date shall be NULL,
**And** the DB update shall NOT abort or raise an error.

### AC-4: DB Migration for Existing Databases

**Given** an existing `daily_price.db` without the RS_Line column,
**When** the daily DB update process runs,
**Then** the RS_Line column shall be added via ALTER TABLE migration,
**And** existing data rows shall have RS_Line = NULL until recalculated.

### AC-5: Chart API Returns RS Line Data (Daily)

**Given** a stock with RS_Line data in the daily DB,
**When** I call `GET /api/chart/{code}?timeframe=daily`,
**Then** the response JSON shall include an `rs_line` array,
**And** each element shall have `time` (string, YYYY-MM-DD) and `value` (float) fields,
**And** no element shall have a null value.

### AC-6: Chart API Returns RS Line Data (Weekly)

**Given** a stock with RS_Line data in the weekly DB,
**When** I call `GET /api/chart/{code}?timeframe=weekly`,
**Then** the response JSON shall include an `rs_line` array with valid data points.

### AC-7: Chart API Handles Missing RS Line Data

**Given** a stock with no RS_Line data (e.g., newly listed),
**When** I call `GET /api/chart/{code}`,
**Then** the `rs_line` field shall be an empty array `[]`,
**And** the response status shall be 200 (not an error).

### AC-8: Chart API Backward Compatibility

**Given** an old database without the RS_Line column,
**When** I call `GET /api/chart/{code}`,
**Then** the `rs_line` field shall be an empty array `[]`,
**And** the candlestick, volume, and MA data shall still be returned correctly.

### AC-9: RS Line Renders on Chart with Transparency (Visual)

**Given** the chart loads with RS Line data from the API (daily or weekly timeframe),
**When** the chart finishes rendering,
**Then** a semi-transparent purple line (color: rgba(108, 92, 231, 0.5)) shall be visible overlaid on the candlestick chart,
**And** the line shall NOT have a visible Y-axis on either side,
**And** the line shall have a width of 2px,
**And** candlestick bars and moving average lines shall remain clearly visible through the RS Line (50% opacity).

### AC-10: RS Line Does Not Interfere with Price Scale

**Given** the chart displays both candlesticks and RS Line,
**When** the user hovers over the chart crosshair,
**Then** the price scale on the right side shall show stock price values only (not RS Line values),
**And** the candlestick chart shall occupy its normal vertical space.

### AC-11: RS Line Scales Independently

**Given** two stocks with very different price levels (e.g., Samsung 70,000 vs a penny stock at 500),
**When** both charts render with RS Line,
**Then** the RS Line shall be visually proportional within each chart's area,
**And** the RS Line shall NOT be compressed to a flat line or extend beyond chart boundaries.

### AC-12: RS Line Absent Does Not Break Chart

**Given** a stock where `rs_line` is an empty array in the API response,
**When** the chart renders,
**Then** the candlestick, volume, and MA series shall render normally,
**And** no error shall appear in the browser console.

### AC-13: Chart Cleanup Includes RS Line

**Given** a ChartCell component is unmounted (e.g., user scrolls to different page),
**When** the cleanup function runs,
**Then** the RS Line series shall be properly disposed along with other chart resources,
**And** no memory leaks shall occur from RS Line series.

## Quality Gate Criteria

| Criteria | Target |
|----------|--------|
| RS_Line calculation accuracy | Within 0.001 of expected value |
| API response time increase | < 10ms additional latency |
| Frontend render time increase | < 50ms per chart cell |
| DB update time increase | < 30 seconds total (KOSPI fetch overhead) |
| Zero console errors | No JS errors from RS Line feature |
| Backward compatibility | Old DBs still return valid responses |

### AC-14: RS Line Uses Close Price Basis

**Given** a stock with Close=70,000 and KOSPI Close=2,600 on a given date,
**When** RS_Line is calculated,
**Then** the value shall be exactly stock.Close / KOSPI.Close (= 26.923),
**And** no other price basis (Open, High, Low, VWAP, OHLC average) shall be used.

### AC-15: RS Line Renders Identically on Weekly Chart

**Given** a stock with RS_Line data in both daily and weekly DBs,
**When** the user switches between daily and weekly timeframes,
**Then** the RS Line shall render with the same color (rgba(108, 92, 231, 0.5)), width (2px), and hidden axis behavior on both views.

## Definition of Done

- [ ] RS_Line column exists in daily DB schema
- [ ] RS_Line values calculated using Close price basis only
- [ ] KOSPI fetch failure handled gracefully (NULL values, no abort)
- [ ] Chart API returns `rs_line` field for both daily and weekly timeframes
- [ ] Empty `rs_line` array for stocks/DBs without RS data
- [ ] RS Line renders as semi-transparent purple overlay (50% opacity) with hidden axis
- [ ] RS Line does not obscure candlestick bars or MA lines
- [ ] RS Line scales independently from price data
- [ ] RS Line visual behavior identical on daily and weekly charts
- [ ] No regressions in existing chart functionality
- [ ] Unit tests for RS_Line calculation (Close-based)
- [ ] Integration tests for chart API rs_line field (both timeframes)
- [ ] Visual verification across different price ranges
