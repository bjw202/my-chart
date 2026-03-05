# KR Stock Screener Project Structure

## Directory Organization

```
kr-stock-screener/
├── my_chart/                    # Existing Python library (backend core)
│   ├── __init__.py
│   ├── config.py
│   ├── registry.py
│   ├── price.py
│   ├── indicators.py
│   ├── analysis/
│   │   ├── market.py
│   │   └── reports.py
│   ├── charting/
│   │   ├── single.py
│   │   ├── bulk.py
│   │   └── styles.py
│   ├── db/
│   │   ├── weekly.py
│   │   ├── daily.py
│   │   └── queries.py
│   ├── export/
│   │   ├── pptx_builder.py
│   │   └── tradingview.py
│   └── screening/
│       ├── momentum.py
│       ├── daily_filters.py
│       └── high_stocks.py
│
├── backend/                     # FastAPI API layer
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point, CORS, lifespan
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chart.py            # GET /api/chart/{code}
│   │   ├── db.py               # POST /api/db/update, GET /api/db/status, /last-updated
│   │   ├── screen.py           # POST /api/screen
│   │   └── sectors.py          # GET /api/sectors
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chart.py            # ChartDataResponse, OHLCV models
│   │   ├── screen.py           # ScreenRequest, ScreenResponse, FilterCondition
│   │   └── db.py               # UpdateStatus, LastUpdated
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chart_service.py    # Bridges my_chart.price/db -> API response
│   │   ├── screen_service.py   # Bridges my_chart.screening -> filtered results
│   │   ├── db_service.py       # Bridges my_chart.db -> update orchestration
│   │   └── sector_service.py   # Bridges my_chart.registry -> sector data
│   └── deps.py                 # Shared dependencies (DB connections, registry)
│
├── frontend/                    # React + Vite + TypeScript
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                # API client functions
│       │   ├── client.ts       # Axios/fetch wrapper
│       │   ├── chart.ts        # Chart data API
│       │   ├── screen.ts       # Screen filter API
│       │   ├── db.ts           # DB update API
│       │   └── sectors.ts      # Sector list API
│       ├── components/
│       │   ├── FilterBar/      # Top filter area
│       │   │   ├── FilterBar.tsx
│       │   │   ├── MarketCapFilter.tsx
│       │   │   ├── ReturnFilter.tsx
│       │   │   ├── PatternBuilder.tsx  # Technical pattern condition builder
│       │   │   ├── RSFilter.tsx
│       │   │   ├── SectorFilter.tsx
│       │   │   └── DbUpdateButton.tsx
│       │   ├── ChartGrid/      # Center chart area
│       │   │   ├── ChartGrid.tsx
│       │   │   ├── ChartCell.tsx       # Single TradingView chart
│       │   │   ├── ChartPagination.tsx
│       │   │   └── useChartGrid.ts     # Grid state management hook
│       │   ├── StockList/      # Right sidebar stock list
│       │   │   ├── StockList.tsx
│       │   │   ├── SectorGroup.tsx     # Collapsible sector header + stocks
│       │   │   ├── StockItem.tsx
│       │   │   └── useStockNavigation.ts  # Keyboard navigation hook
│       │   └── StatusBar/      # Bottom status bar
│       │       └── StatusBar.tsx
│       ├── hooks/
│       │   ├── useScrollSync.ts        # Chart <-> StockList sync
│       │   ├── useScreenResults.ts     # Filter state + API call
│       │   └── useDbUpdate.ts          # SSE-based update progress
│       ├── types/
│       │   ├── stock.ts
│       │   ├── filter.ts
│       │   └── chart.ts
│       └── styles/
│           └── global.css
│
├── fnguide/                     # FnGuide 재무 분석 패키지 (독립형)
│   ├── __init__.py              # 패키지 export
│   ├── parser.py                # HTML/JSON 파싱 유틸리티
│   ├── crawler.py               # FnGuide HTTP 크롤링
│   ├── analysis.py              # 재무 분석 (fs_analysis)
│   └── analyzer.py              # 종합 분석 (analyze_comp → CompResult)
│
├── data/                        # SQLite databases (gitignored)
│   ├── weekly_price.db
│   ├── weekly_rs.db
│   └── daily_price.db
│
├── sectormap_original.xlsx      # Sector classification reference
├── pyproject.toml               # Python project config
├── requirements.txt             # Python dependencies
└── README.md
```

## Architecture Layers

```
┌─────────────────────────────────────────────────┐
│  Frontend (React + Vite + TypeScript)            │
│  - FilterBar, ChartGrid, StockList, StatusBar   │
│  - TradingView Lightweight Charts               │
│  - react-window for virtualized lists           │
└────────────────────┬────────────────────────────┘
                     │ HTTP (localhost)
┌────────────────────▼────────────────────────────┐
│  Backend (FastAPI)                               │
│  - Routers: chart, db, screen, sectors          │
│  - Services: bridge layer to my_chart package   │
│  - Schemas: Pydantic request/response models    │
└────────────────────┬────────────────────────────┘
                     │ Python imports
┌────────────────────▼────────────────────────────┐
│  my_chart Package (existing Python library)      │
│  - price, indicators, screening, db, registry   │
│  - Pure data acquisition and computation        │
└────────────────────┬────────────────────────────┘
                     │ SQL / File I/O
┌────────────────────▼────────────────────────────┐
│  SQLite Databases                                │
│  - weekly_price.db, weekly_rs.db, daily_price.db│
└─────────────────────────────────────────────────┘
```

## API Endpoint Mapping

| Endpoint | Router | Service | my_chart Function |
|----------|--------|---------|-------------------|
| `GET /api/chart/{code}` | chart.py | chart_service.py | `price_naver()`, `get_db_data()` |
| `POST /api/screen` | screen.py | screen_service.py | `mmt_companies()`, `daily_filtering()`, `load_price_with_rs()` |
| `POST /api/db/update` | db.py | db_service.py | `generate_price_db()`, `price_daily_db()` |
| `GET /api/db/status` | db.py | db_service.py | SSE progress stream |
| `GET /api/db/last-updated` | db.py | db_service.py | DB file metadata query |
| `GET /api/sectors` | sectors.py | sector_service.py | `get_stock_registry()`, `add_sector_info()` |

## Frontend Component Hierarchy

```
App
├── FilterBar (top, fixed)
│   ├── MarketCapFilter          # Range dropdown (1000억+, 5000억+, 1조+)
│   ├── ReturnFilter             # Period + threshold (1D/1W/1M/3M × %)
│   ├── PatternBuilder ×3        # Technical pattern conditions with AND/OR
│   ├── RSFilter                 # RS score threshold
│   ├── SectorFilter             # Multi-select sector/theme
│   └── DbUpdateButton           # Triggers /api/db/update
├── Main Content (flex row)
│   ├── ChartGrid (center)
│   │   ├── ChartCell ×(4|9)     # TradingView Lightweight Charts instances
│   │   └── ChartPagination      # ◀ Page N/M ▶
│   └── StockList (right sidebar)
│       └── SectorGroup ×N       # Collapsible sector headers
│           └── StockItem ×M     # Stock name, code, change%, RS
└── StatusBar (bottom, fixed)
    └── Filter count + DB update timestamp
```

## Module Organization

The project follows a **3-tier architecture**:

1. **Presentation Layer** (frontend/) - React UI with chart visualization and filter controls
2. **API Layer** (backend/) - FastAPI routers, Pydantic schemas, service bridge functions
3. **Data Layer** (my_chart/) - Existing Python library for data acquisition, computation, and storage

### Backend Service Layer Pattern

Services in `backend/services/` bridge the API layer to the existing `my_chart` package:

- Services import `my_chart` functions directly
- Services handle data format conversion (DataFrame -> Pydantic model -> JSON)
- Services manage async operations (DB update background tasks)
- No business logic duplication - all computation delegates to `my_chart`

## Input/Output Conventions

### API Request/Response Formats

- **Requests:** JSON body for POST, path/query params for GET
- **Responses:** JSON with Pydantic-validated schemas
- **Chart Data:** Array of `{time, open, high, low, close, volume}` objects (TradingView format)
- **Screen Results:** Array of stock objects with sector grouping metadata
- **DB Status:** SSE stream with progress percentage and estimated time

### Database Files

Located in `data/` directory (gitignored):
- **weekly_price.db** - Weekly OHLCV + MA + period returns + RS scores
- **weekly_rs.db** - Weekly Relative Strength scores vs KOSPI
- **daily_price.db** - Daily OHLCV + EMA/SMA + volume/range indicators

## Key Design Patterns

**Service Bridge Pattern:** Backend services wrap `my_chart` functions, converting between DataFrame and JSON without duplicating logic

**SSE for Long Operations:** DB update uses Server-Sent Events for real-time progress push to frontend

**Viewport Virtualization:** Only visible chart instances are created; scrolled-out charts are destroyed to manage memory

**Scroll Sync Hook:** Custom React hook coordinates state between ChartGrid pagination and StockList scroll position

**SQL-Based Filtering:** All screening runs as SQL WHERE clauses against pre-computed DB columns for sub-second response times
