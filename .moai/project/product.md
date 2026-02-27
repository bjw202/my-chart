# KR Stock Screener Product Documentation

## Project Overview

**Project Name:** KR Stock Screener

**Tagline:** Web-based Korean stock screening tool with real-time chart grid and advanced technical filters

**Description:** KR Stock Screener is a local-only web application that provides comprehensive screening of KOSPI/KOSDAQ stocks (~2,570 listings). Built on the existing `my_chart` Python library for data acquisition and technical analysis, it adds a FastAPI backend and React frontend with TradingView Lightweight Charts for interactive visualization. Users can apply complex filter combinations (market cap, period returns, technical patterns, RS scores, sectors), view results in a sector-grouped stock list, and scan through candlestick chart grids with synchronized scrolling.

## Core Features

1. **Filter System** - Complex multi-condition screening with market cap ranges, period-based return thresholds (1D/1W/1M/3M), technical pattern builder (price vs MA comparisons with AND/OR logic), RS score filters, market selection (KOSPI/KOSDAQ), and sector/theme multi-select

2. **Chart Grid** - TradingView Lightweight Charts displayed in 2x2 or 3x3 grid layout with daily candlestick, moving averages (10/20/50/100/200), and volume bars. Memory-optimized with viewport-only rendering and chart instance destruction on scroll-out

3. **Stock List** - Right sidebar showing filtered stocks grouped by sector (sectormap `산업명(대)` + `산업명(중)`), sorted by market cap within groups, with collapse/expand headers, keyboard navigation, and display of stock name, code, daily change, and RS score

4. **Scroll Sync** - Bidirectional synchronization between stock list and chart grid. Clicking a stock navigates to its chart page, keyboard arrows auto-advance chart pages, and chart page changes scroll the stock list

5. **DB Update** - One-click batch update of all stock data (daily/weekly OHLCV + moving averages + RS scores + market cap) via background task with progress bar and SSE-based status push. Recommended frequency: once daily after market close

6. **Technical Pattern Builder** - Condition builder UI for constructing custom technical patterns: `[Indicator A] [Operator] [Indicator B or Constant] [x Multiplier]`. Supports price, MA(10/20/50/100/200) as indicators with >, <, >=, <=, and proximity(%) operators. Up to 3 patterns combinable with AND/OR

## Target Users

- Korean stock market investors running a local screening tool on their machine
- Individual traders who want fast visual scanning of filtered stocks with chart grids
- Technical analysis practitioners applying custom MA and RS-based screening criteria

## Key Use Cases

**Daily Screening Workflow:** Launch app -> Update DB (if stale) -> Set filter criteria -> Browse sector-grouped results -> Scan charts via keyboard/scroll -> Identify trading candidates

**Technical Pattern Screening:** Build custom conditions (e.g., "Close <= 10-day MA x 1.05 AND 10/20/50 MA convergence <= 5%") to find stocks matching specific technical setups

**Sector Analysis:** Filter by specific sectors/themes, view all stocks in a sector with their charts side-by-side for relative comparison

**RS-Based Screening:** Filter stocks by Relative Strength score (e.g., RS >= 80) to identify outperformers vs KOSPI index

## Technology Stack

**Backend:** Python 3.11+, FastAPI, uvicorn, existing my_chart package (data acquisition, indicators, screening, DB management)

**Frontend:** React (Vite), TypeScript, TradingView Lightweight Charts, react-window (virtualized lists)

**Database:** SQLite (existing weekly_price.db, weekly_rs.db, daily_price.db schema)

**Deployment:** Local-only (localhost), no cloud infrastructure

## Data Strategy

### DB-First Approach

All filtering and screening operates on pre-computed data stored in SQLite, ensuring fast query response times. The DB update process (triggered by user) fetches data from external sources (Naver Finance, pykrx) and persists:

- **Weekly DB:** OHLCV, MA50/150/200, period returns (CHG_1W~12M), RS scores
- **Daily DB:** OHLCV, EMA/SMA(10/20/50/200), volume indicators, range indicators
- **Market Cap:** Fetched via pykrx during DB update and stored for SQL-based filtering

### Data Freshness

Data reflects the last DB update timestamp. Intended for end-of-day analysis (장 마감 후 1일 1회 업데이트).

## Reusable Existing Code

The following `my_chart` package functions serve as the backend data layer:

| Function | Module | Web Service Role |
|----------|--------|-----------------|
| `price_naver()` | price.py | `/api/chart/{code}` data source |
| `get_stock_registry()` | registry.py | `/api/sectors`, stock metadata |
| `add_sector_info()` | registry.py | Stock list sector grouping |
| `mmt_companies()` | screening/momentum.py | `/api/screen` momentum filter |
| `daily_filtering()` | screening/daily_filters.py | `/api/screen` daily filter |
| `generate_price_db()` | db/weekly.py | `/api/db/update` batch job |
| `price_daily_db()` | db/daily.py | `/api/db/update` daily batch |
| `load_price_with_rs()` | db/queries.py | Filtering data source |
| `MACD/RSI/BB` | indicators.py | Technical indicator calculation |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/db/update` | Start DB update (async background task) |
| GET | `/api/db/status` | Query update progress (SSE) |
| GET | `/api/db/last-updated` | Last update timestamp |
| POST | `/api/screen` | Apply filter conditions, return filtered stock list |
| GET | `/api/chart/{code}` | Stock chart data (OHLCV + MA) |
| GET | `/api/sectors` | Sector list for filter dropdown |

## Market Coverage

- **KOSPI:** Korea Composite Stock Price Index (~800 stocks)
- **KOSDAQ:** Korean Securities Dealers Automated Quotations (~1,700 stocks)
- Total: ~2,570 stocks with daily/weekly OHLCV and technical indicators

## Quality Standards

- Modular architecture separating API layer from existing data library
- Pure SQL-based filtering for performance (no runtime API calls during screening)
- Memory-optimized chart rendering with viewport virtualization
- Keyboard-accessible navigation for efficient stock scanning
- Parameterized SQL queries preventing injection
