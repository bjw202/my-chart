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
│   │   ├── sectors.py          # GET /api/sectors
│   │   ├── analysis.py         # GET /api/analysis/{code} (FnGuide S-RIM 대시보드)
│   │   └── ai_report.py        # POST/GET /api/ai-report/{code}* (Perplexity AI 분석)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chart.py            # ChartDataResponse, OHLCV models
│   │   ├── screen.py           # ScreenRequest, ScreenResponse, FilterCondition
│   │   ├── db.py               # UpdateStatus, LastUpdated
│   │   ├── analysis.py         # AnalysisResponse, ActivityRatiosSchema, etc.
│   │   └── ai_report.py        # HistoryItem, HistoryResponse, ReportContentResponse
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chart_service.py    # Bridges my_chart.price/db -> API response
│   │   ├── screen_service.py   # Bridges my_chart.screening -> filtered results
│   │   ├── db_service.py       # Bridges my_chart.db -> update orchestration
│   │   ├── sector_service.py   # Bridges my_chart.registry -> sector data
│   │   ├── analysis_service.py # FnGuide dashboard 래퍼 (TTL cache 5분)
│   │   └── ai_report_service.py # Perplexity API 스트리밍 + 파일 저장 (SPEC-AI-REPORT-001)
│   ├── reports/                # AI 분석 리포트 저장소 (종목명별 폴더)
│   │   └── {종목명}/{YYYY-MM-DD}.md
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
│       │   ├── sectors.ts      # Sector list API
│       │   ├── analysis.ts     # Financial analysis API (FS)
│       │   └── aiReport.ts     # AI report SSE streaming + history (AI)
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
│       │   ├── AnalysisModal.tsx  # S-RIM financial analysis modal (8 sections, FS 버튼)
│       │   ├── AiReportModal.tsx  # AI analysis modal (분석결과/히스토리 2탭, AI 버튼)
│       │   └── StatusBar/      # Bottom status bar
│       │       └── StatusBar.tsx
│       ├── hooks/
│       │   ├── useScrollSync.ts        # Chart <-> StockList sync
│       │   ├── useScreenResults.ts     # Filter state + API call
│       │   ├── useDbUpdate.ts          # SSE-based update progress
│       │   ├── useAnalysis.ts          # Financial analysis data fetching
│       │   └── useAiReport.ts          # AI report SSE streaming + history hook
│       ├── types/
│       │   ├── stock.ts
│       │   ├── filter.ts
│       │   ├── chart.ts
│       │   ├── analysis.ts            # Financial analysis TypeScript interfaces
│       │   └── aiReport.ts            # AI report TypeScript interfaces
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
├── sectormap-original.xlsx      # 단일 source — 53 컬럼 원본, registry.py가 header=8로 로드, 6 컬럼 사용 (Code/Name/Market/산업명(대)/산업명(중)/주요제품). 이전 sectormap.xlsx 는 2026-05-12 폐기
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
| `GET /api/analysis/{code}` | analysis.py | — (direct) | `fnguide.dashboard.analyze_dashboard()` |

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

The project follows a **4-tier architecture**:

1. **Presentation Layer** (frontend/) - React UI with chart visualization, filter controls, and financial analysis modal
2. **API Layer** (backend/) - FastAPI routers, Pydantic schemas, service bridge functions
3. **Data Layer** (my_chart/) - Existing Python library for data acquisition, computation, and storage
4. **Financial Analysis Layer** (fnguide/) - Independent financial analysis package crawling comp.fnguide.com for S-RIM dashboard data

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
