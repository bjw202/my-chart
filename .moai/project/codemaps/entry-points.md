# KR Stock Screener Entry Points Reference

## API Entry Points

### POST /api/screen - Stock Screening

Primary endpoint for filtering stocks by multiple criteria.

**Request Body (ScreenRequest):**
```json
{
  "market_cap": {"min": 1000000000000},
  "returns": {"period": "3m", "min": 10},
  "patterns": [
    {
      "indicator_a": "close",
      "operator": "<=",
      "indicator_b": "ma10",
      "multiplier": 1.05
    }
  ],
  "pattern_logic": "AND",
  "rs_min": 80,
  "markets": ["KOSPI", "KOSDAQ"],
  "sectors": ["반도체", "배터리"]
}
```

**Response (ScreenResponse):**
```json
{
  "total": 127,
  "sectors": [
    {
      "name": "반도체",
      "stocks": [
        {
          "code": "005930",
          "name": "삼성전자",
          "market": "KOSPI",
          "market_cap": 350000000000000,
          "chg_1d": 1.5,
          "rs_score": 85.3
        }
      ]
    }
  ]
}
```

**Route:** backend/routers/screen.py → backend/services/screen_service.py

---

### GET /api/chart/{code} - Chart Data

Returns OHLCV + MA time series data for TradingView rendering.

**Path Parameters:**
- `code` (str): 6-digit Korean stock code

**Query Parameters:**
- `start` (str, optional): Start date "YYYY-MM-DD" (default: 1 year ago)
- `end` (str, optional): End date "YYYY-MM-DD" (default: today)

**Response:**
```json
{
  "code": "005930",
  "name": "삼성전자",
  "candles": [
    {"time": "2024-01-02", "open": 70000, "high": 71500, "low": 69500, "close": 71000},
    {"time": "2024-01-03", "open": 71000, "high": 72000, "low": 70500, "close": 71500}
  ],
  "volume": [
    {"time": "2024-01-02", "value": 15000000},
    {"time": "2024-01-03", "value": 12000000}
  ],
  "ma": {
    "sma10": [{"time": "2024-01-02", "value": 70200}],
    "sma20": [{"time": "2024-01-02", "value": 69800}],
    "sma50": [{"time": "2024-01-02", "value": 68500}],
    "sma100": [{"time": "2024-01-02", "value": 67000}],
    "sma200": [{"time": "2024-01-02", "value": 65000}]
  }
}
```

**Route:** backend/routers/chart.py → backend/services/chart_service.py → my_chart.db.queries

---

### POST /api/db/update - Start DB Update

Triggers background database update for all stocks.

**Request:** No body required

**Response (202 Accepted):**
```json
{
  "status": "started",
  "message": "Database update started in background"
}
```

**Route:** backend/routers/db.py → backend/services/db_service.py (BackgroundTask)

---

### GET /api/db/status - Update Progress (SSE)

Server-Sent Events stream for real-time DB update progress.

**Response (SSE stream):**
```
event: progress
data: {"phase": "weekly", "progress": 45, "current": "삼성전자", "total": 2570, "eta_seconds": 180}

event: progress
data: {"phase": "daily", "progress": 72, "current": "SK하이닉스", "total": 2570, "eta_seconds": 90}

event: progress
data: {"phase": "complete", "progress": 100}
```

**Route:** backend/routers/db.py → SSE generator from db_service.py

---

### GET /api/db/last-updated - Last Update Timestamp

Returns the timestamp of the most recent DB update.

**Response:**
```json
{
  "last_updated": "2024-01-15T18:30:00",
  "weekly_db_size_mb": 520,
  "daily_db_size_mb": 180
}
```

**Route:** backend/routers/db.py → file metadata check

---

### GET /api/sectors - Sector List

Returns available sectors for filter dropdown.

**Response:**
```json
{
  "sectors": [
    {"name": "반도체", "stock_count": 45},
    {"name": "배터리", "stock_count": 23},
    {"name": "바이오", "stock_count": 67},
    {"name": "자동차", "stock_count": 31}
  ]
}
```

**Route:** backend/routers/sectors.py → backend/services/sector_service.py → my_chart.registry

---

## Frontend Entry Points

### App.tsx - Application Root

Main layout component rendering the 3-panel UI:
```
App
├── FilterBar (top)
├── MainContent (center + right)
│   ├── ChartGrid (center)
│   └── StockList (right)
└── StatusBar (bottom)
```

### Hooks as Entry Points

**useScreenResults()**
- Manages filter state and triggers POST /api/screen
- Returns: `{stocks, sectors, loading, error, applyFilters}`
- Called from: FilterBar (filter changes) and App (initial load)

**useScrollSync()**
- Coordinates ChartGrid pagination with StockList scroll position
- Returns: `{activeStock, setActiveStock, currentPage, setCurrentPage}`
- Called from: App, passed to ChartGrid and StockList

**useDbUpdate()**
- Manages SSE connection for DB update progress
- Returns: `{isUpdating, progress, phase, startUpdate}`
- Called from: DbUpdateButton and StatusBar

**useStockNavigation()**
- Handles keyboard ↑↓ navigation in StockList
- Returns: `{selectedIndex, onKeyDown}`
- Called from: StockList

---

## Backend Startup Entry Point

### backend/main.py

```python
# Application lifecycle
app = FastAPI(lifespan=lifespan)

@asynccontextmanager
async def lifespan(app):
    # Startup: pre-initialize registry to avoid first-request delay
    from my_chart.registry import get_stock_registry
    get_stock_registry()  # triggers lazy singleton init
    yield
    # Shutdown: cleanup if needed

# Routers
app.include_router(chart_router, prefix="/api")
app.include_router(screen_router, prefix="/api")
app.include_router(db_router, prefix="/api")
app.include_router(sectors_router, prefix="/api")

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"])
```

**Run command:** `uvicorn backend.main:app --reload --port 8000`

---

## Existing my_chart Entry Points (Library API)

These functions are called by backend services, not directly by users in the web context:

### Data Acquisition
- `price_naver(code, start, end)` → Called by chart_service and db_service
- `price_naver_rs(code, start, end)` → Called by db_service for RS calculation

### Database Operations
- `generate_price_db(start_date)` → Called by db_service during update
- `generate_rs_db(base_code)` → Called by db_service during update
- `get_db_data(code, start, end)` → Called by chart_service and screen_service

### Screening
- `mmt_companies(min_12m, min_6m, min_3m)` → Reference for screen_service logic
- `daily_filtering(code)` → Reference for screen_service filter logic

### Registry
- `get_stock_registry()` → Called by sector_service
- `_code()`, `_name()`, `_market()`, `_sector()` → Called by various services

---

## CLI Entry Points (Development)

### Backend Development
```bash
# Start FastAPI dev server
uvicorn backend.main:app --reload --port 8000

# Run backend tests
pytest backend/tests/

# Access API docs
open http://localhost:8000/docs
```

### Frontend Development
```bash
# Start Vite dev server
cd frontend && npm run dev

# Build for production
cd frontend && npm run build

# Run frontend tests
cd frontend && npm test
```

### Database Management
```bash
# Python REPL for manual DB operations
python -c "from my_chart import generate_price_db; generate_price_db()"
```
