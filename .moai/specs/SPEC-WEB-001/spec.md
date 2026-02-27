---
id: SPEC-WEB-001
version: "1.0.0"
status: completed
created: "2026-02-28"
updated: "2026-02-28"
author: jw
priority: P1
---

## HISTORY

| Date | Version | Author | Change |
|------|---------|--------|--------|
| 2026-02-28 | 1.0.0 | jw | Initial SPEC creation |
| 2026-02-28 | 1.0.1 | jw | Add REQ-012: Stale/missing stock data safety |
| 2026-02-28 | 1.1.0 | jw | Mark completed: all requirements implemented, 166 tests passing |

---

# SPEC-WEB-001: KR Stock Screener Web Service

## Overview

Build a local-only web application for screening KOSPI/KOSDAQ stocks (~2,570) with advanced technical filters, TradingView chart grids, and sector-grouped stock lists. The web service wraps the existing `my_chart` Python library with a FastAPI backend and React frontend.

## Scope

**In Scope:**
- FastAPI backend with 6 API endpoints bridging to existing my_chart package
- New `stock_meta` denormalized screening table for sub-100ms SQL filtering
- DB schema enhancement: market cap storage, SMA100, sector/market info
- SSE-based DB update progress streaming
- React frontend with TradingView Lightweight Charts grid (2x2/3x3)
- Filter system: market cap, period returns, technical pattern builder, RS score, market, sector
- Virtualized stock list with sector grouping and keyboard navigation
- Bidirectional scroll sync between chart grid and stock list
- Thread safety fixes for FastAPI concurrent access

**Out of Scope:**
- Cloud deployment (localhost only)
- Real-time price streaming
- Filter preset save/load
- Watchlist/favorites
- Dark mode
- Chart period toggle (daily only, weekly later)
- Authentication/authorization

---

## Requirements (EARS Format)

### REQ-001: DB Update System

**When** the user clicks [DB 업데이트], **the system shall** start a background task that updates all stock data (daily OHLCV, weekly indicators, RS scores, market cap) and returns `{status: "started"}` within 1 second.

**While** DB update is running, **the system shall** stream progress via SSE at `GET /api/db/status` with `{phase, progress, current_stock, total, eta_seconds}` every 500ms.

**When** a second DB update request arrives while one is running, **the system shall** return HTTP 409 with `{error: "update_in_progress"}`.

**When** DB update completes, **the system shall** rebuild the `stock_meta` screening snapshot table by joining daily DB, weekly DB, relative_strength, pykrx market cap, and sectormap.xlsx data.

**Where** pykrx market cap fetch fails, **the system shall** store NULL for market_cap and continue with other data. Previous market_cap values are preserved via COALESCE.

### REQ-002: Stock Screening Filter

**When** `POST /api/screen` receives filter criteria, **the system shall** execute a parameterized SQL query against the `stock_meta` table and return sector-grouped results within 100ms.

**The system shall** support these filter types (combined with AND logic):
- Market cap: minimum threshold in 억원
- Period returns: CHG_1D (daily Change), CHG_1W, CHG_1M, CHG_3M with minimum percentage
- Technical patterns (up to 3): `[indicator_a] [operator] [indicator_b × multiplier]` with AND/OR between patterns
- RS score: minimum RS_12M_Rating threshold
- Market: KOSPI and/or KOSDAQ checkbox
- Sector: multi-select from 산업명(대) values

**Where** an indicator name is not in the whitelist (Close, Open, High, Low, EMA10, EMA20, SMA50, SMA100, SMA200), **the system shall** return HTTP 400 with `{error: "invalid_indicator"}`.

**When** no stocks match the filter, **the system shall** return HTTP 200 with `{total: 0, sectors: []}`.

### REQ-003: Chart Data API

**When** `GET /api/chart/{code}` is called with a valid stock code, **the system shall** return daily OHLCV + MA overlay data in TradingView Lightweight Charts format within 200ms.

Response format:
- `candles`: array of `{time: "YYYY-MM-DD", open, high, low, close}`
- `volume`: array of `{time, value}`
- `ma`: object with `{ema10, ema20, sma50, sma100, sma200}` each as `[{time, value}]`

**Where** the stock code does not exist in DB, **the system shall** return HTTP 404.

Default date range: latest 252 trading days (1 year).

### REQ-004: Sector List API

**When** `GET /api/sectors` is called, **the system shall** return unique 산업명(대) values with stock counts from the `stock_meta` table within 50ms.

### REQ-005: DB Metadata API

**When** `GET /api/db/last-updated` is called, **the system shall** return the last DB update timestamp and DB file sizes.

### REQ-006: Chart Grid UI

**The system shall** display TradingView Lightweight Charts in a toggleable 2x2 or 3x3 grid layout. Each chart shows daily candlestick with MA overlays (10/20/50/100/200) and volume bars.

**The system shall** only instantiate chart instances for currently visible grid slots. When page changes, **the system shall** call `chart.remove()` on previous instances before creating new ones.

### REQ-007: Stock List UI

**The system shall** display filtered stocks in a right sidebar, grouped by 산업명(대), sorted by market_cap DESC within each group. Each stock item shows: name, code, daily change %, RS score.

**The system shall** use react-window VariableSizeList for virtualized rendering.

**The system shall** support keyboard ↑↓ navigation and group collapse/expand.

### REQ-008: Scroll Sync

**When** the user clicks a stock in StockList or navigates with ↑↓ keys, **the system shall** navigate ChartGrid to the page containing that stock.

**When** ChartGrid page changes via pagination, **the system shall** scroll StockList to the corresponding position.

### REQ-009: stock_meta Screening Table

**When** DB update completes, **the system shall** create/replace the `stock_meta` table with this schema:

```sql
CREATE TABLE IF NOT EXISTS stock_meta (
    code TEXT PRIMARY KEY,
    name TEXT,
    market TEXT,              -- 'KOSPI' or 'KOSDAQ'
    market_cap INTEGER,       -- 억원, nullable if pykrx fails
    sector_major TEXT,        -- 산업명(대)
    sector_minor TEXT,        -- 산업명(중)
    product TEXT,             -- 주요제품
    close REAL,
    change_1d REAL,           -- daily Change %
    ema10 REAL,
    ema20 REAL,
    sma50 REAL,
    sma100 REAL,              -- NEW: computed during daily DB gen
    sma200 REAL,
    high52w REAL,
    chg_1w REAL,              -- from weekly DB
    chg_1m REAL,
    chg_3m REAL,
    rs_12m REAL,              -- from relative_strength table
    ma50_w REAL,              -- weekly MA50
    ma150_w REAL,             -- weekly MA150
    ma200_w REAL,             -- weekly MA200
    last_updated TEXT
);
CREATE INDEX IF NOT EXISTS idx_meta_sector ON stock_meta(sector_major);
CREATE INDEX IF NOT EXISTS idx_meta_market ON stock_meta(market);
CREATE INDEX IF NOT EXISTS idx_meta_cap ON stock_meta(market_cap DESC);
```

Data sources: daily stock_prices (latest date) + weekly stock_prices (latest date) + relative_strength (latest date) + sectormap_original.xlsx + pykrx market cap.

### REQ-010: Thread Safety

**The system shall** pre-initialize `get_stock_registry()` and `get_sector_registry()` in FastAPI lifespan startup event before accepting requests.

**The system shall** use `sqlite3.connect(db_path, check_same_thread=False)` for all DB connections in the web service context.

**The system shall** run as single-process uvicorn (1 worker) to avoid registry singleton duplication.

### REQ-011: SMA100 Addition to Daily DB

**When** `price_daily_db()` generates daily data, **the system shall** compute SMA100 (100-day simple moving average) and store it in the `stock_prices` table as `SMA100` column.

### REQ-012: Stale/Missing Stock Data Safety

sectormap_original.xlsx contains ~2,570 stocks, but some may be delisted, newly listed (insufficient history), suspended, or have no price data in the DB. The system must handle all these cases gracefully without raising errors.

#### DB Update Phase

**When** `generate_price_db()` or `price_daily_db()` fetches data for a stock from sectormap.xlsx that returns empty or error from Naver Finance API, **the system shall** log a warning with the stock code and skip to the next stock without aborting the batch.

**When** a stock has fewer than 100 trading days of history (newly listed), **the system shall** store available data and set SMA100/SMA200 and long-period CHG columns to NULL rather than raising a calculation error.

**The system shall** track and report fetch results at the end of DB update: `{success: N, skipped: M, errors: K, skipped_codes: [...]}`.

#### stock_meta Rebuild Phase

**When** rebuilding `stock_meta`, **the system shall** perform LEFT JOIN from sectormap stock list to daily/weekly DB tables. Stocks present in sectormap but absent from DB (no price data) are excluded from `stock_meta` (not inserted).

**When** a stock exists in daily DB but not in weekly DB (or vice versa), **the system shall** insert the row with available columns and set missing columns to NULL.

**The system shall** only include stocks whose latest DB date matches the most recent trading date (within 5 business days tolerance). Stocks with data older than 5 business days are considered stale and excluded from `stock_meta`.

#### API Response Phase

**When** `GET /api/chart/{code}` is called for a stock code that exists in sectormap but has no DB data, **the system shall** return HTTP 404 with `{error: "no_data", detail: "Stock {code} has no price data in DB. It may be delisted or newly listed."}`.

**When** `POST /api/screen` returns results, stocks with NULL values in filtered columns are automatically excluded by SQL WHERE (NULL fails comparison). This is the expected behavior for newly listed stocks with incomplete indicators.

#### Frontend Display

**When** stock_meta contains stocks with partial NULL columns (e.g., NULL market_cap, NULL rs_12m), **the system shall** display "-" in the StockList for NULL values rather than 0 or error.

---

## Technical Approach

### Architecture

```
React (Vite+TS)  →  FastAPI (Python)  →  my_chart package  →  SQLite
                                      →  stock_meta table   →  (denormalized)
```

### Backend Strategy

- **Service Bridge Pattern**: Services in `backend/services/` call existing `my_chart` functions, converting DataFrames to Pydantic models
- **SQL-First Screening**: All filtering runs as parameterized SQL against `stock_meta` indexed columns
- **SSE Progress**: `sse-starlette` streams DB update progress from thread-safe `progress_store`
- **DB Update Lock**: `threading.Lock` prevents concurrent update execution

### Frontend Strategy

- **State**: Two React Contexts (ScreenContext + NavigationContext), no Redux
- **Chart Lifecycle**: `useEffect` creates chart on mount, `chart.remove()` on cleanup
- **Virtualization**: react-window VariableSizeList for stock list (sector headers 40px, items 56px)
- **Scroll Sync**: `useScrollSync` hook with `isInternalUpdate` ref to prevent circular updates

### Data Flow

```
POST /api/screen → screen_service.build_where() → SQL on stock_meta → sector-grouped JSON
GET /api/chart/{code} → chart_service → daily DB SELECT → TradingView format JSON
POST /api/db/update → BackgroundThread → generate_price_db + market_cap + rebuild stock_meta
```

---

## File Change Map

| File | Action | Description |
|------|--------|-------------|
| my_chart/db/daily.py | MODIFY | Add SMA100 column computation |
| backend/__init__.py | CREATE | Package init |
| backend/main.py | CREATE | FastAPI app, CORS, lifespan |
| backend/deps.py | CREATE | DB paths, get_db_conn() |
| backend/routers/*.py | CREATE | 4 router files (chart, db, screen, sectors) |
| backend/schemas/*.py | CREATE | 3 schema files |
| backend/services/*.py | CREATE | 6 service files |
| frontend/ | CREATE | Full React+Vite+TS project (~26 files) |
| pyproject.toml | MODIFY | Add fastapi, uvicorn, sse-starlette deps |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| pykrx market cap fails | HIGH | MEDIUM | Store NULL, COALESCE with previous value |
| Delisted/missing stocks in sectormap | HIGH | MEDIUM | Skip with warning during DB update, exclude from stock_meta |
| Newly listed stocks (< 100 days) | MEDIUM | LOW | Store available data, NULL for insufficient-history indicators |
| SQL injection via pattern builder | HIGH | HIGH | Literal enum whitelist for column names |
| Thread-unsafe registry init | MEDIUM | HIGH | Lifespan pre-initialization |
| Chart memory leak | MEDIUM | MEDIUM | Strict useEffect cleanup with chart.remove() |
| matplotlib slow import | LOW | LOW | Lazy-import my_chart modules in services |
| Concurrent DB updates | MEDIUM | MEDIUM | threading.Lock + HTTP 409 |

---

## Dependencies on SPEC-001

This SPEC depends on SPEC-001 (completed) for:
- Parallel DB generation with ThreadPoolExecutor
- WAL mode SQLite configuration
- Retry logic in price.py
- sectormap.xlsx-based registry (pykrx workaround)
