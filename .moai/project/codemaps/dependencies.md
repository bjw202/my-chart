# KR Stock Screener Dependencies Reference

## Backend Dependencies

### New (Web Service Layer)

**fastapi**
- Purpose: Async web framework for REST API endpoints
- Used in: backend/main.py, backend/routers/
- Why: Modern Python web framework with auto-generated OpenAPI docs, Pydantic integration, and async support

**uvicorn**
- Purpose: ASGI server for running FastAPI
- Used in: Development server and production deployment
- Why: High-performance ASGI server recommended by FastAPI

**sse-starlette**
- Purpose: Server-Sent Events support for FastAPI
- Used in: backend/routers/db.py for update progress streaming
- Why: Enables real-time server-push updates without WebSocket complexity

**pydantic** (bundled with FastAPI)
- Purpose: Request/response data validation and serialization
- Used in: backend/schemas/ for all API models
- Why: Type-safe data validation with automatic JSON schema generation

### Existing (my_chart Package)

**pandas** (>= 1.3.0)
- Purpose: DataFrame-based data manipulation
- Used in: All data processing modules
- Impact: Core dependency, used throughout

**numpy** (>= 1.21.0)
- Purpose: Vectorized numerical computation
- Used in: indicators.py for technical indicator calculations

**requests** (>= 2.26.0)
- Purpose: HTTP client for Naver Finance API
- Used in: price.py during DB update

**pykrx** (>= 1.0.30)
- Purpose: Korean exchange API for stock metadata and market cap
- Used in: registry.py, db update for market cap fetch

**sqlite3** (built-in)
- Purpose: Embedded relational database
- Used in: db/ module for all data persistence

**openpyxl** (>= 3.6.0)
- Purpose: Excel file reading (sectormap_original.xlsx)
- Used in: registry.py for sector classification data

**matplotlib** (>= 3.4.0), **mplfinance** (>= 0.12.9)
- Purpose: Chart generation (existing library)
- Used in: charting/ module (NOT used in web service - replaced by TradingView)
- Note: Still installed as my_chart dependency but not invoked by web API

**python-pptx**, **pillow**, **xlrd**, **xlsxwriter**, **lxml**
- Purpose: Office document generation (existing library)
- Used in: export/ module (NOT used in web service)
- Note: Still installed as my_chart dependency but not invoked by web API

## Frontend Dependencies

### Core

**react** (18+), **react-dom**
- Purpose: UI component framework
- Used in: All frontend components

**typescript** (5+)
- Purpose: Type-safe JavaScript development
- Used in: All frontend source files

**vite**
- Purpose: Build tool and development server with HMR
- Used in: Frontend build pipeline and dev server

### Charting

**lightweight-charts** (TradingView)
- Purpose: Financial candlestick chart rendering in browser
- Used in: ChartGrid/ChartCell.tsx
- Why: Open-source, lightweight (~40KB), purpose-built for OHLC data with interactive features
- Alternative considered: Chart.js (lacks financial chart types), Recharts (no candlestick)

### Virtualization

**react-window**
- Purpose: Virtualized list rendering for large stock lists
- Used in: StockList/StockList.tsx
- Why: Only renders visible items, handles 2,570+ stocks efficiently
- Alternative considered: react-virtuoso (larger bundle), manual virtualization

### HTTP Client

**axios** or native **fetch**
- Purpose: HTTP requests to backend API
- Used in: frontend/src/api/

## Dependency Graph

```
Frontend
├── react, react-dom (UI framework)
├── typescript (language)
├── vite (build tool)
├── lightweight-charts (chart rendering)
├── react-window (list virtualization)
└── axios (HTTP client)
    └── HTTP → Backend API (localhost:8000)

Backend (FastAPI)
├── fastapi (web framework)
│   └── pydantic (data validation)
├── uvicorn (ASGI server)
├── sse-starlette (SSE support)
└── my_chart (data library)
    ├── pandas, numpy (data processing)
    ├── requests (HTTP client for Naver Finance)
    ├── pykrx (Korean exchange API)
    ├── sqlite3 (database, built-in)
    ├── openpyxl (Excel reading)
    └── matplotlib, mplfinance (not used in web)
```

## Dependency Risks & Mitigations

### Critical Path

**FastAPI + uvicorn**
- Risk: Version incompatibility
- Mitigation: Pin versions in requirements.txt

**lightweight-charts (TradingView)**
- Risk: Breaking API changes in chart library
- Mitigation: Pin npm version, wrapper component isolates chart API

**SQLite (data layer)**
- Risk: Database corruption during interrupted writes
- Mitigation: WAL mode, transaction management, single-writer pattern

**pykrx (market data)**
- Risk: API changes or service outage
- Mitigation: Only used during DB update (not runtime). Registry cached at startup.

### Optional / Low Risk

**react-window** - Fallback: native scrolling (slower for large lists)
**sse-starlette** - Fallback: polling-based progress check
**axios** - Fallback: native fetch API

## Version Compatibility

### Python

| Package | Minimum | Recommended |
|---------|---------|-------------|
| Python | 3.11 | 3.13 |
| FastAPI | 0.100+ | Latest |
| uvicorn | 0.20+ | Latest |
| pandas | 1.3.0 | 2.0+ |
| pykrx | 1.0.30 | Latest |

### Node.js

| Package | Minimum | Recommended |
|---------|---------|-------------|
| Node.js | 20 LTS | 22 LTS |
| React | 18 | 19 |
| TypeScript | 5.0 | 5.6+ |
| Vite | 5.0 | 6.0+ |
| lightweight-charts | 4.0 | Latest |
