# my_chart Architecture Overview

## High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                   my_chart Application Layer                     │
│                    (Jupyter / IPython REPL)                      │
└────────────┬────────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────────┐
│                   Public API (my_chart/__init__.py)              │
│  - price_naver, mmt_companies, plot_chart, tradingview, etc    │
└────────────┬────────────────────────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────┬──────────────┬──────────────┐
    │                 │              │              │              │
    ▼                 ▼              ▼              ▼              ▼
┌─────────┐  ┌──────────────┐  ┌──────────────┐ ┌──────────┐ ┌──────────┐
│ Price   │  │ Indicators   │  │ Screening    │ │ Charting │ │ Analysis │
│ Module  │  │ Module       │  │ Module       │ │ Module   │ │ Module   │
└────┬────┘  └──────┬───────┘  └──────┬───────┘ └────┬─────┘ └────┬─────┘
     │              │                 │              │             │
     └──────────────┼─────────────────┼──────────────┼─────────────┘
                    │                 │              │
                    ▼                 ▼              ▼
            ┌────────────────────────────────────────────┐
            │      Database Module (SQLite)              │
            │  - weekly_price.db                         │
            │  - weekly_rs.db                            │
            │  - daily_price.db                          │
            └────────────┬─────────────────────────────┘
                         │
            ┌────────────┼──────────────┐
            │            │              │
            ▼            ▼              ▼
        ┌──────┐    ┌────────┐    ┌──────────┐
        │ PPTX │    │TradingV│    │ PNG/SVG  │
        │Export│    │ Export │    │  Charts  │
        └──────┘    └────────┘    └──────────┘
            │            │              │
            └────────────┼──────────────┘
                         │
            ┌────────────▼──────────────┐
            │  Output Files             │
            │  (Presentations, Exports) │
            └──────────────────────────┘
```

## Core Execution Flow

### Data Acquisition Flow

1. User calls `price_naver(code, start_date, end_date)` or similar API
2. Registry validates stock code via `_code()`, `_name()` lookups
3. Price module makes HTTP request to Naver Finance API
4. Response parsed and converted to DataFrame with OHLCV columns
5. Optional cleaning with `fix_zero_ohlc()` for invalid data
6. DataFrame returned to user for further analysis

### Technical Analysis Flow

1. User obtains price DataFrame via `price_naver()` or database query
2. User applies indicators: `RSI(df)`, `MACD(df)`, `Stochastic(df)`, etc.
3. Indicator functions return DataFrame with additional calculated columns
4. User optionally stacks multiple indicators on same DataFrame
5. Processed DataFrame ready for visualization or screening

### Screening Flow

1. User calls `mmt_companies()` with optional thresholds
2. Screening module fetches all stock codes from registry
3. For each stock, calculates 12-month/6-month/3-month returns
4. Ranks stocks by momentum score
5. Filters by user-provided thresholds
6. Returns sorted list of qualified stock codes

### Charting Flow

1. User calls `plot_chart(code, start_date, end_date)` with optional indicators
2. Charting module fetches price data if not provided
3. Optionally calculates technical indicators
4. Creates candlestick chart using mplfinance
5. Overlays indicators if requested
6. Saves PNG file and displays in Jupyter notebook
7. User can also batch process via `plot_all_companies()`

### Export Flow

1. User calls `tradingview(codes_list)` or `excel_companies()`
2. Export module formats data in target format
3. Generates output file (text for TradingView, XLSX for Excel)
4. Returns file path to user for distribution

## Design Patterns

### 1. Lazy Singleton Pattern (Registry)

```
registry.py:
  - Global variable: _stock_registry = None
  - First access to _code() triggers initialization
  - pykrx API calls happen once, results cached
  - Subsequent accesses return cached values
```

**Purpose:** Minimize startup latency (pykrx API calls take 3-5 seconds). Pay cost on first access, not on import.

**Trade-offs:** First call slower, subsequent calls instant. Thread-safety via Python GIL.

### 2. Configuration Centralization

```
config.py:
  - All constants defined in single file
  - Platform detection for fonts
  - Database paths
  - Technical indicator defaults
```

**Purpose:** Single source of truth for system configuration. Easy customization without code modification.

**Implementation:** Import config throughout codebase, read values at module initialization.

### 3. Pure Function Composition

```
price.py:
  price_naver() -> DataFrame

indicators.py:
  RSI(df) -> df.copy() with added RSI column
  MACD(df) -> df.copy() with added MACD/Signal columns

Usage:
  df = price_naver(code, start, end)
  df = RSI(df)
  df = MACD(df)
  plot_chart(df)
```

**Purpose:** Enable flexible function composition. Each function independent and testable.

**Trade-offs:** More intermediate DataFrames (memory cost) but functional purity enables caching and parallelization.

### 4. DataFrame Convention

All modules use consistent DataFrame structure:
- Index: datetime (business days only)
- Columns: Open, High, Low, Close, Volume (OHLCV)
- Technical indicators add columns without modifying existing

**Purpose:** Consistent interface across all modules. Users familiar with pandas can easily extend.

### 5. Database Abstraction Layer (db/ module)

```
db/queries.py:
  - get_db_data(code, start, end) -> DataFrame
  - get_nearest_date(code, date) -> datetime
  - get_query(sql) -> DataFrame
```

**Purpose:** Abstract SQLite implementation details. Allow database swapping without API changes.

**Implementation:** All database access goes through query functions, not direct SQL.

## System Boundaries

### External Systems

**Naver Finance API (HTTP)**
- Provides historical price data for Korean stocks
- Called via requests library in price.py
- Rate limited: 100 requests/minute
- No authentication required (public data)

**pykrx Python Package**
- Provides stock registry (codes, names, sectors)
- Called via registry.py lazy singleton
- Network I/O expensive (3-5 seconds per call)
- Cached to minimize calls

**Operating System**
- File system (SQLite databases, output files)
- System fonts (AppleGothic, Malgun Gothic)
- Platform detection (macOS/Windows/Linux)

### Internal Database

**SQLite Databases**
- weekly_price.db: Historical OHLCV data
- weekly_rs.db: Relative Strength scores
- daily_price.db: Recent daily data
- Located in project root directory

**Data Flow:** Fetch → Calculate → Store → Query → Visualize

## Module Dependency Graph

```
__init__.py (Public API)
  ├── price.py
  │   └── requests (external)
  │
  ├── registry.py
  │   └── pykrx (external)
  │
  ├── indicators.py
  │   ├── pandas, numpy (external)
  │   └── config.py
  │
  ├── charting/
  │   ├── single.py
  │   ├── bulk.py
  │   └── styles.py
  │       ├── mplfinance, matplotlib (external)
  │       └── config.py
  │
  ├── db/
  │   ├── weekly.py
  │   ├── daily.py
  │   └── queries.py
  │       └── sqlite3 (external)
  │
  ├── screening/
  │   ├── momentum.py
  │   ├── daily_filters.py
  │   └── high_stocks.py
  │       ├── price.py
  │       ├── indicators.py
  │       └── registry.py
  │
  ├── analysis/
  │   ├── market.py
  │   └── reports.py
  │       └── registry.py
  │
  └── export/
      ├── pptx_builder.py
      │   ├── python-pptx, pillow (external)
      │   └── charting/
      └── tradingview.py
          ├── registry.py
          └── config.py
```

## Key Characteristics

**Modularity:** 7 core modules with clear responsibilities and minimal coupling

**Layering:** Data acquisition → Processing → Analysis → Visualization → Export

**Statelessness:** Most functions pure (input DataFrame → output DataFrame)

**Caching:** Registry singleton reduces API calls, database enables data reuse

**Configurability:** Central config file, no hardcoded paths or constants

**Error Resilience:** API retry logic, data validation, graceful degradation

## Integration Points

**Jupyter Notebooks:** Primary integration point. Charts display inline, tables render as HTML

**IPython REPL:** All functions callable interactively with tab completion

**External Libraries:** mplfinance for visualization, pykrx for metadata, Naver Finance for data

**File System:** SQLite databases, output PNG/XLSX/PPTX files

**No Web API:** Not designed as web service (REPL/Jupyter focused)
