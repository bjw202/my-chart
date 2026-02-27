# KR Stock Screener Technical Documentation

## Technology Stack Overview

### Backend (Python)

- **Python 3.11+** - Runtime for backend API and existing data library
- **FastAPI** - Async web framework for REST API endpoints
- **uvicorn** - ASGI server for running FastAPI application
- **my_chart package** - Existing data acquisition, indicators, screening, DB modules
- **pydantic** - Request/response validation via FastAPI integration

### Frontend (TypeScript)

- **React 18+** - UI component library
- **Vite** - Build tool and dev server with HMR
- **TypeScript** - Type-safe frontend development
- **TradingView Lightweight Charts** - Open-source financial charting library (npm: `lightweight-charts`)
- **react-window** - Virtualized list rendering for stock list performance

### Database

- **SQLite** - Embedded relational database (existing schema, no migration needed)
- **sqlite3** - Python built-in driver for database operations

### Data Sources (used during DB update only)

- **Naver Finance API** - Historical OHLCV data via HTTP scraping
- **pykrx** - Korean exchange API for stock metadata and market cap data

### Existing Python Dependencies (my_chart package)

- **pandas** (>= 1.3.0) - DataFrame operations for all data processing
- **numpy** (>= 1.21.0) - Vectorized numerical computation for indicators
- **requests** (>= 2.26.0) - HTTP client for Naver Finance API
- **mplfinance** (>= 0.12.9) - Chart generation (used in existing library, not in web service)
- **matplotlib** (>= 3.4.0) - Underlying chart engine (existing library dependency)
- **openpyxl** (>= 3.6.0) - Excel file handling for sectormap
- **pykrx** (>= 1.0.30) - Korean stock exchange API

### New Backend Dependencies

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **sse-starlette** - Server-Sent Events for DB update progress streaming
- **pydantic** - Data validation (bundled with FastAPI)

### New Frontend Dependencies

- **react**, **react-dom** - UI framework
- **typescript** - Language
- **lightweight-charts** - TradingView chart library
- **react-window** - Virtualized rendering
- **axios** or **fetch** - HTTP client for API calls

## Platform Requirements

### Python Environment

- Python 3.11+ (recommended: 3.13)
- Virtual environment (venv or conda)
- pip for package management

### Node.js Environment

- Node.js 20 LTS+
- npm or pnpm for package management
- Vite for build tooling

### Operating System

- macOS (primary development target)
- Windows, Linux (compatible)

## Database Architecture

### Existing Schema (No Changes Required)

**weekly_price.db:**
- Per-stock tables with columns: Date, Open, High, Low, Close, Volume, MA50, MA150, MA200, CHG_1W, CHG_1M, CHG_3M, CHG_6M, CHG_12M
- Composite index on (stock_code, date)

**weekly_rs.db:**
- RS scores per stock per date
- RS = (Stock return / KOSPI return) * 100

**daily_price.db:**
- Per-stock tables with columns: Date, Open, High, Low, Close, Volume, EMA10, EMA20, SMA50, SMA200, volume indicators, range indicators

### Schema Enhancement: Market Cap Storage

**New requirement:** Store market cap data in DB during update cycle.

**Approach:** Add market_cap column to existing stock metadata or create a separate `stock_meta` table:
```
stock_meta:
  stock_code (TEXT, PRIMARY KEY)
  market_cap (INTEGER)    -- 시가총액 in KRW
  last_updated (DATE)
```

**Rationale:** Currently market cap is fetched via `pykrx.stock.get_market_cap()` at runtime. Storing it during DB update enables pure SQL filtering without runtime API calls.

## Data Strategy: DB vs pykrx

### Current State

| Data | Source | Storage |
|------|--------|---------|
| OHLCV (weekly) | Naver Finance | weekly_price.db |
| OHLCV (daily) | Naver Finance | daily_price.db |
| MA/EMA/SMA | Computed from OHLCV | Stored in DB |
| Period returns | Computed from OHLCV | Stored in DB |
| RS scores | Computed vs KOSPI | weekly_rs.db |
| Market cap | pykrx API (runtime) | NOT stored |
| Stock metadata | pykrx + sectormap.xlsx | Runtime cache |

### Target State (Web Service)

| Data | Source | Storage | API Usage |
|------|--------|---------|-----------|
| OHLCV | Naver Finance | DB | `/api/chart/{code}` |
| Technical indicators | Computed | DB | `/api/screen` filters |
| RS scores | Computed | DB | `/api/screen` RS filter |
| Market cap | pykrx (batch) | DB | `/api/screen` market cap filter |
| Sector info | sectormap.xlsx | Runtime cache | `/api/sectors` |

### Key Decision: DB Update Includes Market Cap

During `/api/db/update`:
1. Fetch all stock OHLCV data (existing flow)
2. Fetch market cap via `pykrx.stock.get_market_cap(date)` (new)
3. Store market cap in `stock_meta` table (new)
4. All subsequent filtering uses SQL queries only (fast)

## Development Environment Setup

### Backend Setup

```bash
# Clone and enter project
cd kr-stock-screener

# Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install existing package + new dependencies
pip install -e .
pip install fastapi uvicorn sse-starlette

# Run backend
uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run dev server (proxied to backend)
npm run dev
```

### Full Stack Development

- Backend: `http://localhost:8000` (FastAPI + Swagger docs at `/docs`)
- Frontend: `http://localhost:5173` (Vite dev server with API proxy to :8000)

## Architectural Decisions

### 1. Reuse my_chart Package as Backend Core

**Decision:** Import existing `my_chart` modules directly into FastAPI services instead of rewriting

**Rationale:** The existing library has 40+ battle-tested functions for data acquisition, indicator calculation, and screening. Rewriting would introduce bugs and delay. Service layer bridges DataFrame outputs to JSON responses.

**Trade-offs:** Some functions (e.g., mmt_companies) make synchronous API calls during screening. For the web service, pre-computed DB data should be preferred over runtime API calls.

### 2. SQL-Based Filtering Over Runtime Computation

**Decision:** Pre-compute all filterable values during DB update and store as indexed columns

**Rationale:** With ~2,570 stocks, runtime computation of indicators and returns for each filter request would take 30-60 seconds. SQL WHERE clauses on indexed columns return in <100ms.

**Trade-offs:** Data freshness depends on last DB update. Acceptable for end-of-day analysis use case.

### 3. TradingView Lightweight Charts Over mplfinance

**Decision:** Use TradingView Lightweight Charts (npm) for frontend chart rendering instead of generating PNG charts with mplfinance

**Rationale:** Interactive browser-native charts with pan/zoom, tooltips, and crosshair. No server-side image generation overhead. Standard financial charting library with excellent documentation. Chart data transferred as JSON arrays, not image files.

**Trade-offs:** Requires TypeScript frontend integration. Cannot reuse existing mplfinance charting code (but chart generation was the output layer, not business logic).

### 4. SSE for DB Update Progress

**Decision:** Use Server-Sent Events (SSE) for real-time DB update progress instead of polling

**Rationale:** DB update takes 5-30 minutes. SSE provides server-push updates without client polling overhead. FastAPI supports SSE via `sse-starlette`. One-directional (server -> client) is sufficient for progress reporting.

**Trade-offs:** SSE is simpler than WebSocket but one-directional. Sufficient since client only needs to receive progress, not send messages during update.

### 5. SQLite Retained (No PostgreSQL Migration)

**Decision:** Keep SQLite as the database engine

**Rationale:** Local-only application with single-user access. SQLite provides adequate read performance for filtering queries. No concurrent write requirement (DB update runs as exclusive batch). Zero operational complexity.

**Trade-offs:** Single-writer limitation acceptable for batch update pattern. No connection pooling needed.

## Performance Considerations

| Area | Strategy |
|------|----------|
| Chart rendering | Viewport-only chart instantiation, `chart.remove()` on scroll-out |
| Chart data | Lazy-load per-stock data on pagination/scroll |
| Stock list | react-window virtualized rendering |
| DB query | SQL WHERE on indexed columns, <100ms response |
| DB update | FastAPI BackgroundTask, SSE progress push |
| Frontend bundle | Vite code splitting, lazy component loading |

## Thread Safety

### Known Issue: registry.py Global State

The existing `registry.py` uses a global singleton pattern with lazy initialization. In a multi-threaded FastAPI environment:

- **Read operations** (_code, _name, _market, _sector): Thread-safe after initialization (immutable cache)
- **Initialization**: Potential race condition on first access from concurrent requests
- **Mitigation**: Initialize registry during FastAPI startup (`lifespan` event) before accepting requests

### SQLite Concurrent Access

- **Reads**: Thread-safe with `check_same_thread=False`
- **Writes**: Single-writer model, DB update runs as exclusive background task
- **Mitigation**: Use WAL mode for concurrent reads during writes

## Error Handling & Recovery

### API Failures During DB Update

- Retry with exponential backoff (existing my_chart behavior)
- SSE reports failed stocks to frontend
- Partial update is valid (successfully updated stocks are persisted)

### Frontend Error States

- Network error: Show retry button with last known state
- Empty results: Show "No stocks match filters" message
- Chart load failure: Show placeholder with stock info

## Testing Infrastructure

### Current State

- No automated tests (0% coverage)
- Manual testing via Jupyter notebooks for my_chart package

### Target Approach

- **Backend:** pytest for API endpoint integration tests, mock my_chart functions
- **Frontend:** Vitest for component unit tests
- **E2E:** Playwright for full-stack user flow testing
- **Development mode:** DDD (Domain-Driven Development) per quality.yaml
