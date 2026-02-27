# KR Stock Screener Architecture Overview

## High-Level System Design

```
┌──────────────────────────────────────────────────────────────────┐
│                    Browser (localhost:5173)                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐ │
│  │FilterBar │  │ ChartGrid    │  │StockList │  │  StatusBar   │ │
│  │(filters) │  │ (TradingView)│  │(sectors) │  │  (status)    │ │
│  └──────────┘  └──────────────┘  └──────────┘  └──────────────┘ │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP / SSE (localhost:8000)
┌────────────────────────▼─────────────────────────────────────────┐
│              FastAPI Backend (backend/)                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Routers: chart | screen | db | sectors                  │    │
│  └────────────────────────┬─────────────────────────────────┘    │
│  ┌────────────────────────▼─────────────────────────────────┐    │
│  │  Services: chart_service | screen_service | db_service    │    │
│  │            sector_service                                 │    │
│  └────────────────────────┬─────────────────────────────────┘    │
└────────────────────────────┼─────────────────────────────────────┘
                             │ Python imports
┌────────────────────────────▼─────────────────────────────────────┐
│              my_chart Package (existing library)                   │
│                                                                    │
│    ┌────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐       │
│    │ Price  │  │Indicators │  │ Screening │  │ Registry │       │
│    │ Module │  │  Module   │  │  Module   │  │  Module  │       │
│    └───┬────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘       │
│        │             │              │              │              │
│        └─────────────┼──────────────┼──────────────┘              │
│                      │              │                             │
│              ┌───────▼──────────────▼───────┐                    │
│              │    Database Module (db/)     │                    │
│              └───────────────┬──────────────┘                    │
└──────────────────────────────┼───────────────────────────────────┘
                               │ SQL / File I/O
┌──────────────────────────────▼───────────────────────────────────┐
│                     SQLite Databases                               │
│   weekly_price.db  │  weekly_rs.db  │  daily_price.db            │
└──────────────────────────────────────────────────────────────────┘
```

## Core Execution Flows

### Web Request Flow (Screening)

1. User sets filter conditions in FilterBar
2. Frontend sends POST `/api/screen` with filter criteria JSON
3. FastAPI router validates request via Pydantic schema
4. screen_service converts filter criteria to SQL WHERE clauses
5. SQL query executes against SQLite DB (indexed columns)
6. Results joined with sector metadata from registry
7. Response: sector-grouped stock list with metadata
8. Frontend renders StockList + ChartGrid with results

### Web Request Flow (Chart Data)

1. User scrolls to stock in StockList or chart page advances
2. Frontend requests GET `/api/chart/{code}` for visible stocks
3. FastAPI router passes code to chart_service
4. chart_service queries DB for OHLCV + MA data
5. Data formatted as TradingView-compatible time series
6. Response: array of `{time, open, high, low, close, volume}` + MA overlays
7. Frontend renders TradingView Lightweight Chart instances

### DB Update Flow (Background)

1. User clicks [DB Update] button
2. Frontend sends POST `/api/db/update`
3. FastAPI creates BackgroundTask running db_service
4. db_service calls existing my_chart functions:
   - `generate_price_db()` for weekly OHLCV
   - `price_daily_db()` for daily data
   - `pykrx.stock.get_market_cap()` for market cap (new)
5. Progress streamed via SSE to GET `/api/db/status`
6. Frontend displays progress bar with ETA
7. On completion, frontend refreshes current filter results

## Design Patterns

### 1. Service Bridge Pattern (backend/services/)

```
FastAPI Router
    ↓ (Pydantic model)
Service Function
    ↓ (Python call)
my_chart Function → DataFrame
    ↓ (conversion)
Service Function → Pydantic Response Model
    ↓ (JSON serialization)
HTTP Response
```

**Purpose:** Decouple API layer from data library. All DataFrame-to-JSON conversion happens in services.

### 2. SQL-Based Screening

```
Filter Criteria (JSON)
    ↓
screen_service.build_where_clause()
    ↓
SQL: SELECT * FROM stocks WHERE market_cap > ? AND chg_3m > ? AND rs_score > ?
    ↓
SQLite indexed query (<100ms)
    ↓
DataFrame → Response with sector grouping
```

**Purpose:** Sub-second filtering by leveraging pre-computed indexed columns instead of runtime computation.

### 3. Viewport Virtualization (Frontend)

```
ChartGrid (3x3 = 9 visible slots)
    ↓
Page N: stocks[N*9 .. N*9+8]
    ↓
For each visible slot:
    Create TradingView chart instance
    Load data via /api/chart/{code}
    ↓
On page change:
    chart.remove() for old instances (free memory)
    Create new instances for new page
```

**Purpose:** Memory management for potentially hundreds of chart instances.

### 4. SSE Progress Streaming

```
POST /api/db/update → start BackgroundTask
    ↓
GET /api/db/status → SSE connection
    ↓
Server pushes: {"progress": 45, "current": "삼성전자", "eta": "3:22"}
    ↓
Frontend updates progress bar in real-time
```

**Purpose:** Real-time progress feedback for long-running DB update (5-30 minutes).

### 5. Scroll Sync Hook

```
useScrollSync(chartGridRef, stockListRef)
    ↓
StockList click/keyboard → setActiveStock(code)
    ↓
ChartGrid receives activeStock → navigate to page containing stock
    ↓
ChartGrid page change → StockList scrolls to corresponding position
```

**Purpose:** Bidirectional synchronization between stock selection and chart display.

## System Boundaries

### External Systems (Used During DB Update Only)

**Naver Finance API (HTTP)**
- Historical OHLCV data for all Korean stocks
- Called via my_chart/price.py
- Rate limited: 100 requests/minute

**pykrx Python Package**
- Stock metadata (codes, names, sectors, market caps)
- Called via my_chart/registry.py and db update service
- Network I/O: 3-5 seconds for initialization

### Internal Systems

**SQLite Databases** - All runtime data access goes through DB
**sectormap_original.xlsx** - Sector classification loaded into registry cache
**Frontend Static Assets** - Served by Vite dev server (dev) or FastAPI static files (prod)

## Module Dependency Graph

```
Frontend (React)
  ├── lightweight-charts (TradingView)
  ├── react-window (virtualization)
  └── HTTP API calls → Backend

Backend (FastAPI)
  ├── routers/ → services/
  ├── schemas/ (Pydantic models)
  └── services/ → my_chart package

my_chart/ (existing)
  ├── price.py → requests, Naver Finance
  ├── registry.py → pykrx, sectormap.xlsx
  ├── indicators.py → pandas, numpy
  ├── screening/ → price, registry, indicators
  ├── db/ → sqlite3, price
  ├── charting/ → mplfinance (NOT used in web service)
  └── export/ → python-pptx (NOT used in web service)
```

## Key Characteristics

**3-Tier Architecture:** Frontend → API → Data Library → Database

**DB-First Filtering:** All screening uses pre-computed SQL columns, no runtime API calls

**Existing Code Reuse:** 90% of backend logic is existing my_chart functions wrapped in services

**Memory-Conscious Frontend:** Viewport virtualization for both charts and stock lists

**Local-Only Deployment:** No cloud infrastructure, runs entirely on localhost

**Offline-Capable Screening:** After DB update, all filtering works without internet connection
