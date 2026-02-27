# KR Stock Screener Module Reference

## Backend Modules (New)

### backend/main.py - FastAPI Application Entry Point

**Responsibility:** Initialize FastAPI app, configure CORS, mount routers, handle startup/shutdown lifecycle.

- Creates FastAPI app with CORS middleware (localhost origins)
- Mounts routers: chart, screen, db, sectors under `/api` prefix
- Lifespan event: pre-initializes registry singleton to avoid first-request delay
- Serves frontend static files in production mode

### backend/routers/ - API Route Handlers

**chart.py**
- `GET /api/chart/{code}` - Returns OHLCV + MA time series for a single stock
- Query params: start_date, end_date (optional, defaults to 1 year)
- Response: Array of candlestick data points in TradingView format

**screen.py**
- `POST /api/screen` - Accepts filter criteria, returns filtered stock list
- Request body: FilterCondition (market_cap, returns, patterns, rs, sectors)
- Response: Sector-grouped stock list with metadata

**db.py**
- `POST /api/db/update` - Starts background DB update task
- `GET /api/db/status` - SSE stream of update progress
- `GET /api/db/last-updated` - Returns last DB update timestamp

**sectors.py**
- `GET /api/sectors` - Returns list of available sectors for filter dropdown

### backend/services/ - Business Logic Bridge

**chart_service.py**
- Bridges `my_chart.db.queries.get_db_data()` → TradingView chart format
- Converts DataFrame columns to `{time, open, high, low, close, volume}` array
- Includes MA overlay data series

**screen_service.py**
- Converts filter criteria JSON to SQL WHERE clauses
- Executes optimized queries against SQLite indexed columns
- Joins results with sector metadata from registry
- Returns sector-grouped, market-cap-sorted stock list

**db_service.py**
- Orchestrates DB update using existing my_chart functions
- Runs `generate_price_db()`, `price_daily_db()`, and market cap fetch
- Streams progress via SSE callback

**sector_service.py**
- Loads sector data from `get_stock_registry()` and `sectormap_original.xlsx`
- Caches sector list for fast repeated access

### backend/schemas/ - Pydantic Models

**chart.py** - `ChartDataPoint`, `ChartDataResponse`, `MAOverlay`
**screen.py** - `ScreenRequest`, `FilterCondition`, `PatternCondition`, `ScreenResponse`, `StockItem`, `SectorGroup`
**db.py** - `UpdateStatus`, `LastUpdated`

---

## Existing my_chart Modules (Backend Core)

### Price Module (my_chart/price.py)

**Web Service Role:** Data source for `/api/chart/{code}` and DB update process.

**Key Functions:**
- `price_naver(code, start_date, end_date) -> DataFrame` - Fetch OHLCV from Naver Finance
- `price_naver_rs(code, start_date, end_date) -> DataFrame` - Fetch with RS calculation
- `fix_zero_ohlc(df) -> DataFrame` - Clean invalid OHLC values

### Indicators Module (my_chart/indicators.py)

**Web Service Role:** Pre-compute technical indicators during DB update for SQL-based filtering.

**Key Functions:**
- `RSI(df, period=14) -> DataFrame`
- `MACD(df, fast=12, slow=26, signal=9) -> DataFrame`
- `Stochastic(df, period=14) -> DataFrame`
- `BolingerBand(df, period=20, std_dev=2) -> DataFrame`
- `add_moving_averages(df, periods=[20,50,200]) -> DataFrame`

### Registry Module (my_chart/registry.py)

**Web Service Role:** Stock metadata for `/api/sectors` and stock list display.

**Key Functions:**
- `_code(name) -> str` - Stock name to code lookup
- `_name(code) -> str` - Stock code to name lookup
- `_market(code) -> str` - Get market type (KOSPI/KOSDAQ)
- `_sector(code) -> str` - Get sector classification
- `get_stock_registry() -> DataFrame` - Full registry with sector info
- `add_sector_info(df) -> DataFrame` - Add sector columns to stock list

### Database Module (my_chart/db/)

**Web Service Role:** Primary data persistence and query layer.

**db/weekly.py:**
- `generate_price_db(start_date=None) -> None` - Build/update weekly price DB
- `generate_rs_db(base_code="KOSPI") -> None` - Build/update RS score DB

**db/daily.py:**
- `price_daily_db(code, start_date, end_date) -> DataFrame` - Daily data access

**db/queries.py:**
- `get_db_data(code, start_date, end_date, db_name) -> DataFrame` - Query historical data
- `get_nearest_date(code, target_date, db_name) -> datetime` - Find nearest trading date
- `get_query(sql, db_name) -> DataFrame` - Execute custom SQL
- `load_price_with_rs(code, start_date, end_date) -> DataFrame` - Price + RS combined query

### Screening Module (my_chart/screening/)

**Web Service Role:** Filter logic for `/api/screen` endpoint.

**screening/momentum.py:**
- `mmt_companies(min_12m, min_6m, min_3m) -> list[str]` - Momentum screening
- `mmt_filtering(codes, min_return) -> list[str]` - Filter by return threshold

**screening/daily_filters.py:**
- `daily_filtering(code) -> bool` - Apply daily filter criteria
- `daily_filtering_2(code, params) -> bool` - Custom parameter filtering
- `filter_1(code) -> bool`, `filter_2(code) -> bool` - Individual filter components

**screening/high_stocks.py:**
- `get_high_stocks(threshold_percent) -> list[str]` - 52-week high detection

### Charting Module (my_chart/charting/) - NOT Used in Web Service

Existing charting with mplfinance is NOT used in the web service. TradingView Lightweight Charts replaces this functionality in the frontend.

### Export Module (my_chart/export/) - NOT Used in Web Service

PPTX and TradingView text export are NOT used in the web service.

---

## Frontend Modules (New)

### Components

**FilterBar/** - Top filter area with all filter controls
- `FilterBar.tsx` - Container with filter state management
- `MarketCapFilter.tsx` - Market cap range dropdown
- `ReturnFilter.tsx` - Period return threshold inputs
- `PatternBuilder.tsx` - Technical pattern condition builder UI
- `RSFilter.tsx` - RS score threshold input
- `SectorFilter.tsx` - Multi-select sector/theme dropdown
- `DbUpdateButton.tsx` - DB update trigger with progress indicator

**ChartGrid/** - Center chart area with TradingView instances
- `ChartGrid.tsx` - Grid layout manager (2x2 / 3x3 toggle)
- `ChartCell.tsx` - Single TradingView Lightweight Chart wrapper
- `ChartPagination.tsx` - Page navigation controls
- `useChartGrid.ts` - Grid state and lifecycle management hook

**StockList/** - Right sidebar virtualized stock list
- `StockList.tsx` - react-window virtualized container
- `SectorGroup.tsx` - Collapsible sector header with stock items
- `StockItem.tsx` - Individual stock row (name, code, change%, RS)
- `useStockNavigation.ts` - Keyboard arrow navigation hook

**StatusBar/** - Bottom status bar
- `StatusBar.tsx` - Filter result count + last DB update timestamp

### Hooks

- `useScrollSync.ts` - Bidirectional ChartGrid <-> StockList scroll synchronization
- `useScreenResults.ts` - Filter state management + API call orchestration
- `useDbUpdate.ts` - SSE connection for DB update progress tracking

### API Client

- `client.ts` - Base HTTP client with error handling
- `chart.ts` - `fetchChartData(code, start?, end?)` API function
- `screen.ts` - `screenStocks(filters)` API function
- `db.ts` - `startDbUpdate()`, `subscribeDbStatus()` API functions
- `sectors.ts` - `fetchSectors()` API function

---

## Summary Table

| Layer | Module | Responsibility | Status |
|-------|--------|----------------|--------|
| Frontend | FilterBar | Filter UI controls | New |
| Frontend | ChartGrid | TradingView chart grid | New |
| Frontend | StockList | Sector-grouped stock list | New |
| Frontend | StatusBar | Status display | New |
| Backend | routers/ | API endpoint handlers | New |
| Backend | services/ | my_chart bridge layer | New |
| Backend | schemas/ | Request/response models | New |
| Core | price.py | Naver Finance data fetch | Existing |
| Core | indicators.py | Technical indicator calc | Existing |
| Core | registry.py | Stock metadata lookup | Existing |
| Core | db/ | SQLite persistence/query | Existing |
| Core | screening/ | Stock filter logic | Existing |
| Core | charting/ | mplfinance charts | Existing (unused in web) |
| Core | export/ | PPTX/TradingView export | Existing (unused in web) |
