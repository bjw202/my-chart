# SPEC-WEB-001 Implementation Plan

## Development Methodology

DDD (ANALYZE-PRESERVE-IMPROVE) per quality.yaml

## Implementation Phases

### Phase 1: Backend Foundation (Priority: CRITICAL)

**Goal**: Complete FastAPI backend with all 6 endpoints, stock_meta table, and DB enhancement.

#### Step 1.1: DB Schema Enhancement
| Task | File | Description |
|------|------|-------------|
| Add SMA100 to daily DB | my_chart/db/daily.py | Add `SMA100 = df['Close'].rolling(100).mean()` to `_fetch_daily_stock()`. For stocks with < 100 days history, SMA100 will be NaN (stored as NULL in SQLite). |
| Add stock fetch error handling | my_chart/db/daily.py, weekly.py | Wrap per-stock fetch in try/except. On failure: log warning, increment skip counter, continue to next stock. Return `{success, skipped, errors, skipped_codes}` summary. |
| Create stock_meta build function | backend/services/meta_service.py | LEFT JOIN daily + weekly + RS + sectormap + market_cap. Exclude stocks with no DB data or stale data (> 5 business days old). NULL for missing cross-DB columns. |
| Add db_metadata table | backend/services/db_service.py | `(key TEXT PK, value TEXT)` for last_updated timestamp |

#### Step 1.2: Backend Infrastructure
| Task | File | Description |
|------|------|-------------|
| DB connection helper | backend/deps.py | Import DB paths from my_chart.config, `get_db_conn()` with check_same_thread=False |
| Progress store | backend/services/progress_store.py | Thread-safe dict for SSE progress streaming |
| FastAPI app | backend/main.py | App init, CORS localhost, lifespan (registry pre-init, WAL enable) |

#### Step 1.3: Pydantic Schemas
| Task | File | Description |
|------|------|-------------|
| Screen schemas | backend/schemas/screen.py | PatternCondition (indicator Literal enum), ScreenRequest, StockItem, SectorGroup, ScreenResponse |
| Chart schemas | backend/schemas/chart.py | CandleBar, VolumeBar, MAOverlay, ChartResponse |
| DB schemas | backend/schemas/db.py | UpdateProgress, LastUpdated |

#### Step 1.4: Services
| Task | File | Description |
|------|------|-------------|
| Sector service | backend/services/sector_service.py | Cache sectormap data, return sector list with counts |
| Chart service | backend/services/chart_service.py | Query daily DB, convert DataFrame to TradingView format |
| Screen service | backend/services/screen_service.py | Build parameterized SQL WHERE from ScreenRequest, query stock_meta, group by sector |
| DB service | backend/services/db_service.py | Orchestrate update with Lock, call my_chart generate functions, rebuild stock_meta |
| Meta service | backend/services/meta_service.py | Build stock_meta from multi-DB JOIN + sectormap + pykrx market_cap |

#### Step 1.5: Routers
| Task | File | Description |
|------|------|-------------|
| Chart router | backend/routers/chart.py | `GET /api/chart/{code}` |
| Screen router | backend/routers/screen.py | `POST /api/screen` |
| DB router | backend/routers/db.py | `POST /api/db/update`, `GET /api/db/status` (SSE), `GET /api/db/last-updated` |
| Sectors router | backend/routers/sectors.py | `GET /api/sectors` |

#### Step 1.6: Integration & Testing
| Task | File | Description |
|------|------|-------------|
| Backend tests | tests/test_backend/ | Characterization tests for SQL builder, chart conversion, meta join |
| pyproject.toml update | pyproject.toml | Add fastapi, uvicorn, sse-starlette dependencies |
| requirements.txt update | requirements.txt | Add web dependencies |

**Phase 1 Deliverable**: `uvicorn backend.main:app --reload` serves all 6 endpoints with real DB data.

---

### Phase 2: Frontend Core (Priority: HIGH)

**Goal**: Complete React frontend with all UI components, chart grid, and scroll sync.

#### Step 2.1: Project Setup
| Task | File | Description |
|------|------|-------------|
| Vite + React + TS init | frontend/ | `npm create vite@latest frontend -- --template react-ts` |
| Dependencies | frontend/package.json | Add lightweight-charts, react-window, axios |
| Vite proxy | frontend/vite.config.ts | Proxy `/api` to `http://localhost:8000` |
| Types | frontend/src/types/ | stock.ts, filter.ts, chart.ts type definitions |

#### Step 2.2: API Client Layer
| Task | File | Description |
|------|------|-------------|
| Base client | frontend/src/api/client.ts | Axios instance with base URL and error handling |
| Screen API | frontend/src/api/screen.ts | `screenStocks(filters): Promise<ScreenResponse>` |
| Chart API | frontend/src/api/chart.ts | `fetchChartData(code, start?, end?): Promise<ChartResponse>` |
| DB API | frontend/src/api/db.ts | `startDbUpdate()`, `subscribeDbStatus()` (EventSource) |
| Sectors API | frontend/src/api/sectors.ts | `fetchSectors(): Promise<Sector[]>` |

#### Step 2.3: State Management
| Task | File | Description |
|------|------|-------------|
| Screen context | frontend/src/contexts/ScreenContext.tsx | Filters state, results, loading, applyFilters() |
| Navigation context | frontend/src/contexts/NavigationContext.tsx | selectedIndex, currentPage, gridSize |

#### Step 2.4: FilterBar Components
| Task | File | Description |
|------|------|-------------|
| FilterBar container | frontend/src/components/FilterBar/FilterBar.tsx | Layout + apply button |
| Market cap filter | frontend/src/components/FilterBar/MarketCapFilter.tsx | Dropdown: 1000억+, 5000억+, 1조+ |
| Return filter | frontend/src/components/FilterBar/ReturnFilter.tsx | Period select + threshold input |
| Pattern builder | frontend/src/components/FilterBar/PatternBuilder.tsx | Indicator × Operator × Indicator × Multiplier |
| RS filter | frontend/src/components/FilterBar/RSFilter.tsx | Threshold input |
| Sector filter | frontend/src/components/FilterBar/SectorFilter.tsx | Multi-select dropdown |
| Market filter | frontend/src/components/FilterBar/MarketFilter.tsx | KOSPI/KOSDAQ checkboxes |
| DB update button | frontend/src/components/FilterBar/DbUpdateButton.tsx | Button + progress bar |

#### Step 2.5: ChartGrid Components
| Task | File | Description |
|------|------|-------------|
| ChartGrid | frontend/src/components/ChartGrid/ChartGrid.tsx | Grid layout (2x2/3x3 toggle) |
| ChartCell | frontend/src/components/ChartGrid/ChartCell.tsx | TradingView chart wrapper with useEffect lifecycle |
| ChartPagination | frontend/src/components/ChartGrid/ChartPagination.tsx | Page navigation controls |
| useChartGrid hook | frontend/src/components/ChartGrid/useChartGrid.ts | Grid state, page calculation |

#### Step 2.6: StockList Components
| Task | File | Description |
|------|------|-------------|
| StockList | frontend/src/components/StockList/StockList.tsx | react-window VariableSizeList container |
| SectorGroup | frontend/src/components/StockList/SectorGroup.tsx | Collapsible sector header |
| StockItem | frontend/src/components/StockList/StockItem.tsx | Stock row (name, code, change%, RS) |
| useStockNavigation hook | frontend/src/components/StockList/useStockNavigation.ts | ↑↓ keyboard handler |

#### Step 2.7: Integration Hooks & Layout
| Task | File | Description |
|------|------|-------------|
| useScrollSync | frontend/src/hooks/useScrollSync.ts | Bidirectional chart↔list sync |
| useDbUpdate | frontend/src/hooks/useDbUpdate.ts | SSE subscription for progress |
| StatusBar | frontend/src/components/StatusBar/StatusBar.tsx | Result count + last updated |
| App.tsx | frontend/src/App.tsx | Main layout: FilterBar + ChartGrid + StockList + StatusBar |
| global.css | frontend/src/styles/global.css | Layout grid, scrollbar styling |

**Phase 2 Deliverable**: Full UI with working filters, chart grid, stock list, and scroll sync.

---

### Phase 3: Integration & Polish (Priority: MEDIUM)

| Task | File | Description |
|------|------|-------------|
| Error boundaries | frontend/src/components/ErrorBoundary.tsx | React error boundary wrapper |
| Loading states | (various) | Skeleton loaders for chart, list |
| Empty state | frontend/src/components/EmptyState.tsx | "No stocks match filters" message |
| DB empty state | (various) | "Run DB Update first" guidance |
| Frontend tests | frontend/src/tests/ | Vitest component tests |
| E2E test | tests/e2e/ | Playwright full-flow test |

**Phase 3 Deliverable**: Production-ready local web application.

---

## Key Architecture Decisions

### Decision A: stock_meta Denormalized Table
**Choice**: Create a single denormalized `stock_meta` table joining daily + weekly + RS + sectormap + market cap data.
**Rationale**: Single-table SQL queries are fastest. Avoids runtime JOINs across 3 DBs. Rebuilt at end of each DB update cycle.
**Trade-off**: Data only as fresh as last DB update (acceptable for end-of-day analysis).

### Decision B: SQL WHERE Builder (Not pandas query)
**Choice**: Translate filter conditions to parameterized SQL WHERE clauses.
**Rationale**: Sub-100ms response with SQLite indexes. Prevents SQL injection via Literal enum column whitelist. Avoids pandas df.query() injection risk.
**Trade-off**: More code than pandas query, but much safer and faster.

### Decision C: Single-Process uvicorn
**Choice**: Run uvicorn with 1 worker (no gunicorn multi-worker).
**Rationale**: registry.py globals are module-level singletons. Multi-worker would duplicate 50MB of sectormap data per worker. Single-user local app doesn't need multi-worker throughput.
**Trade-off**: Limited concurrent request handling, acceptable for localhost.

### Decision D: EMA→MA Name Mapping
**Choice**: API uses SMA/EMA naming consistently. Frontend maps: MA10=EMA10, MA20=EMA20, MA50=SMA50, MA100=SMA100, MA200=SMA200.
**Rationale**: Daily DB uses EMA for short periods, SMA for long. PRD uses generic "MA". Document the semantic difference.

### Decision E: SSE over WebSocket for DB Progress
**Choice**: Server-Sent Events via sse-starlette.
**Rationale**: One-directional server→client push is sufficient. Simpler than WebSocket. Built-in browser reconnection.

### Decision F: Graceful Handling of Missing/Stale Stock Data
**Choice**: Skip-and-log strategy for DB update; exclude-from-meta for screening; NULL-display for frontend.
**Rationale**: sectormap.xlsx includes ~2,570 stocks but some are delisted, newly listed (< 100 days history), or suspended. These cases should never crash the batch or return errors to the user.
**Implementation**:
- DB update: per-stock try/except in ThreadPoolExecutor workers, skip counter, summary report
- stock_meta rebuild: LEFT JOIN from sectormap to DB tables; stocks with no recent DB data (> 5 business days stale) are excluded
- Newly listed stocks: store available data, NULL for insufficient-history indicators (SMA100/200, CHG_3M+)
- API: SQL WHERE naturally excludes NULL values from filtered results
- Frontend: display "-" for NULL values in StockList

---

## File Change Summary

| Category | New Files | Modified Files | Total |
|----------|-----------|---------------|-------|
| Backend | ~18 | 2 (daily.py, pyproject.toml) | ~20 |
| Frontend | ~26 | 0 | ~26 |
| Tests | ~5 | 0 | ~5 |
| Config | ~2 (requirements.txt) | 1 (pyproject.toml) | ~3 |
| **Total** | **~51** | **~3** | **~54** |

---

## Estimated Implementation Order

```
Phase 1 (Backend):
  1.1 DB Enhancement    → daily.py SMA100, stock_meta schema
  1.2 Infrastructure    → deps.py, progress_store.py, main.py
  1.3 Schemas           → screen.py, chart.py, db.py
  1.4 Services          → sector → chart → screen → db → meta
  1.5 Routers           → chart → screen → db → sectors
  1.6 Testing           → characterization tests

Phase 2 (Frontend):
  2.1 Setup             → Vite project, deps, proxy
  2.2 API Client        → client, screen, chart, db, sectors
  2.3 State             → ScreenContext, NavigationContext
  2.4 FilterBar         → all filter components
  2.5 ChartGrid         → grid, cell (TradingView), pagination
  2.6 StockList         → list, sector group, stock item, keyboard
  2.7 Integration       → scroll sync, status bar, App.tsx

Phase 3 (Polish):
  3.1 Error handling    → boundaries, empty states
  3.2 Testing           → Vitest + Playwright
```

---

## MX Tag Strategy

| Target | Tag Type | Reason |
|--------|----------|--------|
| screen_service.build_where_clause() | @MX:ANCHOR | High fan_in: called by screen router, tests, meta validation |
| meta_service.rebuild_stock_meta() | @MX:ANCHOR | Critical data pipeline: JOIN from 4 sources, handles missing/stale stocks |
| progress_store | @MX:WARN | Global mutable state, thread safety critical |
| deps.get_db_conn() | @MX:ANCHOR | Fan_in >= 5: all services use this |
| ChartCell useEffect | @MX:WARN | Memory leak risk if chart.remove() not called |
| PatternCondition.indicator | @MX:NOTE | Literal enum whitelist prevents SQL injection |
