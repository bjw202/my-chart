# KR Stock Screener Data Flow Reference

## Core Data Flows

### Flow 1: Stock Screening (POST /api/screen)

**Entry Point:** User applies filters in FilterBar

```
Frontend FilterBar
    ↓ (user sets filters)
useScreenResults hook → POST /api/screen
    ↓ (JSON: FilterCondition)
backend/routers/screen.py
    ↓ (validated ScreenRequest)
backend/services/screen_service.py
    ↓ build_where_clause()
SQL Query:
    SELECT stock_code, name, market, sector, market_cap,
           chg_1d, chg_1w, chg_1m, chg_3m, rs_score, ...
    FROM stock_data
    WHERE market_cap > ?
      AND chg_3m > ?
      AND rs_score > ?
      AND market IN (?, ?)
    ORDER BY sector, market_cap DESC
    ↓ (<100ms, indexed query)
DataFrame result
    ↓ (group by sector)
ScreenResponse: SectorGroup[] with StockItem[]
    ↓ (JSON)
Frontend renders StockList + triggers ChartGrid
```

**Time Complexity:** <100ms (SQL indexed query)

**Key Characteristic:** No runtime API calls. All data pre-computed in DB.

---

### Flow 2: Chart Data (GET /api/chart/{code})

**Entry Point:** ChartGrid needs data for visible stock

```
ChartGrid/ChartCell mounts
    ↓ (stock code from current page)
GET /api/chart/{code}?start=2023-01-01&end=2024-01-01
    ↓
backend/routers/chart.py
    ↓
backend/services/chart_service.py
    ↓
my_chart.db.queries.get_db_data(code, start, end)
    ↓ (SQLite query, <100ms)
DataFrame: Date, Open, High, Low, Close, Volume, SMA10, SMA20, SMA50, SMA200
    ↓ (convert to TradingView format)
Response: {
    candles: [{time, open, high, low, close}],
    volume: [{time, value}],
    ma: {sma10: [{time, value}], sma20: [...], ...}
}
    ↓ (JSON)
ChartCell creates TradingView chart instance
    ↓
chart.addCandlestickSeries().setData(candles)
chart.addHistogramSeries().setData(volume)
chart.addLineSeries().setData(ma.sma10)  // per MA period
```

**Time Complexity:** <200ms (DB query + serialization)

**Memory Note:** ChartCell creates chart on mount, calls `chart.remove()` on unmount to free memory.

---

### Flow 3: DB Update (POST /api/db/update + SSE)

**Entry Point:** User clicks [DB Update] button

```
Frontend DbUpdateButton click
    ↓
POST /api/db/update
    ↓
backend/routers/db.py → create BackgroundTask
    ↓ (returns 202 Accepted immediately)
Frontend subscribes: GET /api/db/status (SSE)
    ↓
BackgroundTask runs db_service.run_full_update():
    ↓
    Step 1: Weekly price update
        my_chart.db.weekly.generate_price_db()
        → For each stock (~2,570):
            price_naver(code) → OHLCV DataFrame
            Calculate MA, period returns
            INSERT/UPDATE into weekly_price.db
        → SSE push: {"phase": "weekly", "progress": 45, "current": "삼성전자"}
    ↓
    Step 2: Daily price update
        my_chart.db.daily.price_daily_db()
        → Similar per-stock process for daily data
        → SSE push: {"phase": "daily", "progress": 72}
    ↓
    Step 3: RS score update
        my_chart.db.weekly.generate_rs_db()
        → Calculate RS vs KOSPI for all stocks
        → SSE push: {"phase": "rs", "progress": 85}
    ↓
    Step 4: Market cap update (new)
        pykrx.stock.get_market_cap(date)
        → Fetch market cap for all stocks
        → INSERT/UPDATE into stock_meta table
        → SSE push: {"phase": "market_cap", "progress": 95}
    ↓
    Step 5: Complete
        → SSE push: {"phase": "complete", "progress": 100}
        → Frontend dismisses progress bar
        → Frontend auto-refreshes current filter results
```

**Time Complexity:** 5-30 minutes (network-bound, ~2,570 stocks)

**Error Handling:** Failed stocks logged and skipped. Partial update is valid.

---

### Flow 4: Sector List (GET /api/sectors)

**Entry Point:** FilterBar SectorFilter dropdown initialization

```
Frontend SectorFilter mounts
    ↓
GET /api/sectors
    ↓
backend/routers/sectors.py
    ↓
backend/services/sector_service.py
    ↓ (cached after first call)
my_chart.registry.get_stock_registry()
    → Load from pykrx + sectormap_original.xlsx
    → Group by 산업명(대) + 산업명(중)
    ↓
Response: [{name: "반도체", count: 45}, {name: "배터리", count: 23}, ...]
    ↓
Frontend renders multi-select dropdown
```

**Time Complexity:** First call: 3-5 seconds (pykrx init). Subsequent: <10ms (cached).

---

### Flow 5: Scroll Synchronization

**Entry Point:** User interaction with StockList or ChartGrid

```
Case A: StockList click/keyboard
    StockItem.onClick(code) or ↑↓ key
        ↓
    useStockNavigation → setActiveStock(code)
        ↓
    useScrollSync detects activeStock change
        ↓
    Calculate target page: Math.floor(stockIndex / gridSize)
        ↓
    ChartGrid.setCurrentPage(targetPage)
        ↓
    ChartGrid loads charts for new page
    Active stock highlighted in first grid position

Case B: ChartGrid pagination
    ChartPagination.onClick(pageN)
        ↓
    ChartGrid.setCurrentPage(pageN)
        ↓
    useScrollSync detects page change
        ↓
    Calculate first stock of page: pageN * gridSize
        ↓
    StockList.scrollTo(firstStockIndex)
        ↓
    StockList scrolls to corresponding position
```

**No API calls:** Pure frontend state synchronization.

---

## Request Lifecycle: Complete User Workflow

```
1. App loads
   └→ GET /api/sectors → populate SectorFilter dropdown
   └→ GET /api/db/last-updated → show in StatusBar

2. User sets filters and clicks Apply
   └→ POST /api/screen {market_cap: ">1T", chg_3m: ">10%", rs: ">80"}
   └→ Response: 127 stocks in 15 sector groups
   └→ StockList renders sector-grouped results
   └→ ChartGrid loads first page (9 charts)
       └→ 9x parallel GET /api/chart/{code}

3. User scrolls through stocks (keyboard ↓)
   └→ StockList highlights next stock
   └→ Scroll sync: ChartGrid advances page when needed
   └→ New page: old charts removed, new charts loaded
       └→ Up to 9x GET /api/chart/{code}

4. User clicks [DB Update] (if data stale)
   └→ POST /api/db/update → 202 Accepted
   └→ GET /api/db/status (SSE) → progress bar
   └→ ... 5-30 minutes ...
   └→ SSE: {"phase": "complete"} → auto-refresh filters
```

## Performance Characteristics

### API Response Times

| Endpoint | Expected Latency | Bottleneck |
|----------|-----------------|------------|
| POST /api/screen | <100ms | SQL indexed query |
| GET /api/chart/{code} | <200ms | SQLite read + JSON serialization |
| GET /api/sectors | <10ms (cached) | First call: 3-5s (pykrx init) |
| GET /api/db/last-updated | <10ms | File metadata check |
| POST /api/db/update | 5-30 min (bg) | Network I/O to Naver/pykrx |

### Frontend Rendering

| Operation | Expected Time |
|-----------|--------------|
| StockList render (2,570 items) | <50ms (react-window virtualized) |
| ChartGrid page (9 charts) | <500ms (parallel data fetch + render) |
| Filter apply + re-render | <200ms (API + DOM update) |
| Scroll sync navigation | <16ms (single frame, no API) |

### Memory Usage

| Component | Approximate Memory |
|-----------|-------------------|
| 9 TradingView chart instances | ~50-100MB |
| StockList (virtualized, 2,570 items) | ~5MB |
| Backend process (FastAPI + my_chart) | ~200-500MB |
| SQLite databases (3 files) | ~700MB disk |

## Error Handling in Data Flows

### Screen API Errors

```
Invalid filter → Pydantic validation error → 422 response
Empty results → 200 with empty list → Frontend shows "No results"
DB not found → 500 with message → Frontend shows "Run DB Update first"
```

### Chart API Errors

```
Invalid code → 404 → ChartCell shows placeholder
No data for date range → 200 with empty array → ChartCell shows "No data"
DB read error → 500 → ChartCell shows error state with retry
```

### DB Update Errors

```
Network timeout → Retry 3x per stock → Skip on failure
pykrx API down → Skip market cap phase → Partial update
SSE disconnect → Frontend auto-reconnects → Resume progress
```
