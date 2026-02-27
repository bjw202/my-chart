# SPEC-WEB-001 Acceptance Criteria

## AC-001: DB Update (Background Task)

**Given** the application is running and no DB update is in progress
**When** the user sends POST /api/db/update
**Then** the system returns HTTP 202 with `{status: "started"}` within 1 second
**And** a background thread starts executing generate_price_db(), price_daily_db(), generate_rs_db(), market_cap fetch, and stock_meta rebuild

**Given** a DB update is already running
**When** another POST /api/db/update is sent
**Then** the system returns HTTP 409 with `{error: "update_in_progress"}`

**Given** a DB update is running
**When** GET /api/db/status is called
**Then** the system returns an SSE stream with events containing `{phase, progress, current_stock, total, eta_seconds}` at ~500ms intervals

**Given** a DB update fails midway (e.g., network error on stock fetch)
**When** the update process encounters an error
**Then** existing valid data is preserved (WAL mode guarantees this)
**And** the error is reported in SSE stream with `{phase: "error", message: "..."}`
**And** successfully fetched stocks remain in the DB

---

## AC-002: Market Cap Filter

**Given** stock_meta table contains market_cap data
**When** POST /api/screen includes `{market_cap_min: 1000000000000}` (1조원 = 10000억)
**Then** only stocks with market_cap >= 10000 (억원 unit) are returned

**Given** pykrx failed during last DB update (some stocks have NULL market_cap)
**When** market_cap filter is applied
**Then** stocks with NULL market_cap are excluded from results
**And** response includes `{warning: "market_cap_data_incomplete"}`

---

## AC-003: Period Return Filter

**Given** stock_meta table is populated
**When** POST /api/screen includes `{returns: [{period: "3m", min: 10}]}`
**Then** only stocks where chg_3m >= 10 are returned

**Given** stock_meta table is populated
**When** POST /api/screen includes `{returns: [{period: "1d", min: 5}]}`
**Then** only stocks where change_1d >= 5 are returned

**Supported periods**: 1d (daily Change), 1w (CHG_1W), 1m (CHG_1M), 3m (CHG_3M)

---

## AC-004: Technical Pattern Builder

**Given** stock_meta table is populated
**When** POST /api/screen includes pattern `{indicator_a: "close", op: "lte", indicator_b: "ema10", multiplier: 1.05}`
**Then** the system filters where `close <= ema10 * 1.05`
**And** responds with matching stocks within 100ms

**Given** a pattern with invalid indicator name (e.g., "DROP_TABLE")
**When** POST /api/screen is sent
**Then** HTTP 400 is returned with `{error: "invalid_indicator", detail: "DROP_TABLE is not a valid indicator"}`

**Given** 3 patterns with AND/OR logic
**When** POST /api/screen includes `{patterns: [p1, p2, p3], pattern_logic: "AND"}`
**Then** all 3 conditions are combined with AND in the SQL WHERE clause

**Whitelisted indicators**: close, open, high, low, ema10, ema20, sma50, sma100, sma200

---

## AC-005: RS Score Filter

**Given** stock_meta table has rs_12m values (from relative_strength JOIN)
**When** POST /api/screen includes `{rs_min: 80}`
**Then** only stocks where rs_12m >= 80 are returned

**Given** stock_meta table is populated with all filters
**When** a single-condition filter (rs_min only) is applied
**Then** response time is < 100ms for 2,570 stocks

---

## AC-006: Sector Filter

**Given** stock_meta table has sector_major column from sectormap
**When** POST /api/screen includes `{sectors: ["반도체", "배터리"]}`
**Then** only stocks in 산업명(대) = "반도체" OR "배터리" are returned

**When** GET /api/sectors is called
**Then** response contains unique sector_major values with stock counts
**And** response time is < 50ms (cached data)

---

## AC-007: Market Filter

**Given** stock_meta table has market column (KOSPI/KOSDAQ)
**When** POST /api/screen includes `{markets: ["KOSPI"]}`
**Then** only KOSPI stocks are returned

**When** POST /api/screen includes `{markets: ["KOSPI", "KOSDAQ"]}`
**Then** all stocks (both markets) are returned

---

## AC-008: Chart Data

**Given** daily DB contains stock data for code "005930"
**When** GET /api/chart/005930 is called
**Then** response contains candles (OHLC), volume, and MA overlays (ema10, ema20, sma50, sma100, sma200)
**And** data covers last 252 trading days
**And** response time is < 200ms
**And** time format is "YYYY-MM-DD" string

**Given** stock code "999999" does not exist in daily DB
**When** GET /api/chart/999999 is called
**Then** HTTP 404 is returned

---

## AC-009: Stock List Display

**Given** POST /api/screen returns 127 stocks across 15 sectors
**When** frontend renders StockList
**Then** stocks are grouped by sector_major with collapsible headers
**And** within each sector, stocks are sorted by market_cap DESC
**And** each stock item shows: name, code, change_1d %, rs_12m score

**Given** 2,570 stocks in results
**When** StockList renders
**Then** react-window virtualizes the list (only visible items rendered)
**And** scroll performance remains smooth (60fps)

---

## AC-010: Chart Grid

**Given** screen results contain 100 stocks
**When** ChartGrid renders in 3x3 mode
**Then** 9 TradingView chart instances are created for page 1
**And** page navigation shows "Page 1/12"

**Given** user navigates from page 1 to page 2
**When** page change occurs
**Then** 9 chart instances from page 1 are destroyed (chart.remove())
**And** 9 new chart instances are created for page 2
**And** no memory leak occurs

---

## AC-011: Scroll Sync

**Given** 100 filtered stocks displayed in 3x3 grid
**When** user clicks stock at index 15 in StockList
**Then** ChartGrid navigates to page 2 (stocks 9-17)
**And** the clicked stock is highlighted

**When** user presses ↓ key from stock at index 8 (last on page 1)
**Then** stock at index 9 is selected
**And** ChartGrid advances to page 2

**When** user clicks "▶" to go to ChartGrid page 3
**Then** StockList scrolls to show stock at index 18

---

## AC-012: Combined Filters

**Given** stock_meta table is fully populated
**When** POST /api/screen includes all filter types:
```json
{
  "market_cap_min": 5000,
  "markets": ["KOSPI"],
  "sectors": ["반도체"],
  "returns": [{"period": "3m", "min": 10}],
  "patterns": [{"indicator_a": "close", "op": "gte", "indicator_b": "sma50", "multiplier": 1.0}],
  "rs_min": 70
}
```
**Then** all conditions are combined with AND
**And** response time is < 100ms
**And** results are sector-grouped with market_cap sort

---

## AC-013: DB Empty State

**Given** no DB files exist (first run)
**When** POST /api/screen is called
**Then** HTTP 200 with `{total: 0, sectors: [], warning: "db_empty"}`

**When** frontend receives db_empty warning
**Then** UI shows guidance: "DB 업데이트를 먼저 실행하세요"

---

## AC-014: stock_meta Rebuild

**Given** DB update has completed successfully
**When** stock_meta rebuild is triggered
**Then** the stock_meta table contains one row per stock (~2,570 rows)
**And** each row has: code, name, market, market_cap, sector_major, sector_minor, close, change_1d, ema10, ema20, sma50, sma100, sma200, high52w, chg_1w, chg_1m, chg_3m, rs_12m, ma50_w, ma150_w, ma200_w

**Given** a stock exists in daily DB but not in weekly DB
**When** stock_meta is rebuilt
**Then** weekly columns (chg_1w, chg_1m, rs_12m, etc.) are NULL for that stock

---

## AC-015: Delisted/Missing Stock Handling (DB Update)

**Given** sectormap.xlsx contains stock code "999999" that has been delisted
**When** DB update runs and price_naver("999999") returns empty or raises an error
**Then** the system logs a warning `"Skipped 999999: no data available"`
**And** continues processing the remaining stocks without aborting
**And** the final SSE progress event includes `{success: 2450, skipped: 120, errors: 0}`

**Given** sectormap.xlsx contains a newly listed stock with only 30 trading days of history
**When** DB update computes indicators for that stock
**Then** SMA100, SMA200, CHG_3M, CHG_6M, CHG_12M are stored as NULL
**And** SMA50, EMA10, EMA20, Change (daily) are computed normally from available data

---

## AC-016: stock_meta Stale Data Exclusion

**Given** stock_meta rebuild runs after DB update
**When** a stock exists in sectormap.xlsx but has NO rows in daily or weekly DB
**Then** that stock is NOT inserted into stock_meta

**Given** a stock's latest DB date is more than 5 business days older than the most recent trading date
**When** stock_meta rebuild runs
**Then** that stock is excluded from stock_meta (considered stale/suspended)

**Given** a stock exists in daily DB but NOT in weekly DB
**When** stock_meta rebuild runs
**Then** the stock is included with daily columns populated and weekly columns (chg_1w, chg_1m, rs_12m, ma50_w, etc.) set to NULL

---

## AC-017: NULL Value Display in Frontend

**Given** stock_meta contains a stock with rs_12m = NULL (newly listed, no RS history)
**When** that stock appears in StockList results
**Then** the RS column displays "-" instead of "0" or causing a render error

**Given** a filter on RS >= 80 is applied
**When** POST /api/screen executes the SQL query
**Then** stocks with rs_12m = NULL are automatically excluded (SQL `NULL >= 80` evaluates to FALSE)
**And** no special NULL handling code is needed in the WHERE builder

---

## Performance Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| POST /api/screen response time | < 100ms | Server-side timer, 2,570 stocks |
| GET /api/chart/{code} response time | < 200ms | Server-side timer, 252 days data |
| GET /api/sectors response time | < 50ms | Server-side timer, cached |
| Frontend chart grid render (9 charts) | < 2s | First contentful paint |
| StockList scroll (2,570 items) | 60fps | No dropped frames |
| Memory (9 TradingView charts) | < 150MB | Browser DevTools heap |
| DB update (2,570 stocks) | < 30min | End-to-end timer |

## Quality Gates

- TRUST 5 compliance (Tested, Readable, Unified, Secured, Trackable)
- 85%+ code coverage for backend services
- No SQL injection vectors (pattern builder uses Literal enum whitelist)
- All SQLite connections use check_same_thread=False
- Registry pre-initialized before first request
- Chart instances properly destroyed on unmount
