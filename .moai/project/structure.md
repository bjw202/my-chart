# my_chart Project Structure

## Directory Organization

```
my_chart/
├── __init__.py                 # Package initialization with public API exports
├── config.py                   # Global configuration and constants
├── registry.py                 # Stock registry with lazy-loaded lookups
├── price.py                    # Naver Finance API data fetching
├── indicators.py               # Technical indicator calculations
├── analysis/                   # Market analysis and reporting
│   ├── __init__.py
│   ├── market.py              # Market cap analysis
│   └── reports.py             # Analyst report generation
├── charting/                   # Chart generation and visualization
│   ├── __init__.py
│   ├── single.py              # Single stock chart generation
│   ├── bulk.py                # Multi-stock batch charting
│   └── styles.py              # Chart styling and themes
├── db/                         # Database management
│   ├── __init__.py
│   ├── weekly.py              # Weekly price DB and RS DB generation
│   ├── daily.py               # Daily price DB management
│   └── queries.py             # Database query interfaces
├── export/                     # Export functionality
│   ├── __init__.py
│   ├── pptx_builder.py        # PPTX presentation generation
│   └── tradingview.py         # TradingView format export
└── screening/                  # Stock screening strategies
    ├── __init__.py
    ├── momentum.py            # Momentum-based screening
    ├── daily_filters.py       # Daily filter strategies
    └── high_stocks.py         # High performance stock detection
```

## File Descriptions

### Core Module Files

**__init__.py** - Package initialization exposing all public API functions. Provides convenient imports for end users via `from my_chart import ...` pattern. Contains comprehensive __all__ list for IDE support and star import clarity.

**config.py** - Central configuration file containing all constants and settings including database paths, chart parameters, font selection based on OS (macOS AppleGothic vs Windows Malgun Gothic), market holidays, and column naming conventions. Single source of truth for system configuration enabling easy customization.

**registry.py** - Stock registry with lazy-loaded lookups to minimize startup time. Provides functions `_code()`, `_name()`, `_market()`, `_sector()` for stock metadata queries. Uses global singleton pattern deferring pykrx API calls until first access.

**price.py** - Naver Finance API integration for historical data fetching. Core functions `price_naver()` and `price_naver_rs()` handle API calls, data parsing, and error recovery. Includes `fix_zero_ohlc()` for data cleaning.

**indicators.py** - Technical indicator calculations implemented as classes with pandas integration. Indicators: MACD, RSI, Stochastic, Bollinger Bands, ImpulseMACD, and moving averages. Each indicator calculates values into new DataFrame columns with optimized numpy/pandas operations.

### Analysis Submodule

**analysis/market.py** - Market cap analysis functionality including `analyze_by_market_cap()` for stock segmentation and `get_market_cap_stats()` for comparative metrics.

**analysis/reports.py** - Analyst report generation with `generate_analyst_report()` function producing structured market insights and stock rankings.

### Charting Submodule

**charting/single.py** - Single stock chart generation with `plot_chart()` for candlestick visualization, `rs_history()` for Relative Strength plots, and `plot_mdd()` for maximum drawdown analysis.

**charting/bulk.py** - Multi-stock batch chart generation including `plot_all_companies()` for systematic visualization of stock lists, `plot_companies()` for selective charting, and `excel_companies()` for Excel-based output.

**charting/styles.py** - Chart styling configuration including color schemes, font settings, indicator overlay styles, and layout templates for consistent professional appearance.

### Database Submodule

**db/weekly.py** - Weekly price database management with `generate_price_db()` for OHLC data storage and `generate_rs_db()` for Relative Strength score persistence. Creates weekly_price.db and weekly_rs.db SQLite files.

**db/daily.py** - Daily price database with `price_daily_db()` function handling daily price updates and queries.

**db/queries.py** - Database query interfaces including `get_db_data()` for DataFrame retrieval, `get_nearest_date()` for historical data alignment, and `get_query()` for custom SQL queries.

### Export Submodule

**export/pptx_builder.py** - PowerPoint presentation generation with automatic chart embedding, table creation, and report section organization for professional client delivery.

**export/tradingview.py** - TradingView format conversion with functions `tradingview()` for single stock export, `company_list_tradingview()` for batch export, and `sector_stocks()` for sector-based organization.

### Screening Submodule

**screening/momentum.py** - Momentum-based stock screening with `mmt_companies()` function calculating 12-month, 6-month, and 3-month return rankings and `mmt_filtering()` for threshold-based selection.

**screening/daily_filters.py** - Daily filter screening strategies with `daily_filtering()`, `daily_filtering_2()`, `daily_filtering_3()` for different filter combinations and `filter_1()`, `filter_2()`, `filter_etc()` for individual filter components.

**screening/high_stocks.py** - High performance stock detection with `get_high_stocks()` for volume surge detection and `투자과열예상종목()` (overheated stock detection) for market froth identification.

## Module Organization

The library follows a **modular pipeline architecture**:

1. **Data Acquisition** (price.py, registry.py) - Fetch market data and stock metadata
2. **Data Processing** (indicators.py, analysis/) - Calculate technical indicators and analytical metrics
3. **Data Storage** (db/) - Persist data in SQLite for reproducibility
4. **Analysis & Screening** (screening/) - Apply screens to identify opportunities
5. **Visualization** (charting/) - Generate professional charts
6. **Export** (export/) - Output results in various formats (PPTX, TradingView)

## Input/Output Conventions

### Input Data Formats

- **Stock Codes:** Korean 6-digit codes (e.g., "005930" for Samsung Electronics) or Korean names
- **Date Ranges:** Python datetime objects or strings "YYYY-MM-DD" format
- **OHLCV Data:** pandas DataFrames with columns (Open, High, Low, Close, Volume)
- **Screen Parameters:** Configuration objects or dictionaries with numeric thresholds

### Output Data Formats

- **Price Data:** pandas DataFrames with indexed datetime and OHLCV columns
- **Charts:** PNG/SVG files via mplfinance with technical overlays
- **Reports:** PPTX documents with embedded images and tables
- **Exports:** Text files in TradingView list format
- **Database:** SQLite .db files in project root with standard schema

## Database Files

The system creates the following SQLite database files in the project directory:

- **weekly_price.db** - Weekly OHLCV data indexed by stock code and date
- **weekly_rs.db** - Weekly Relative Strength scores comparing to KOSPI index
- **daily_price.db** - Daily OHLCV data for recent trading activity

All database operations use connection pooling and transaction management for data consistency.

## Configuration

The `config.py` file centrally manages:

- Database file paths and schema definitions
- Candlestick chart dimensions and colors
- Font selection (platform-aware: AppleGothic for macOS, Malgun Gothic for Windows)
- Technical indicator parameters (RSI period, Bollinger Band width)
- Market holidays and trading day calendars
- PPTX slide templates and styling

System automatically detects platform at startup and configures fonts accordingly, ensuring charts render correctly on macOS, Windows, and Linux systems.

## Key Design Patterns

**Lazy Loading:** Registry uses global singleton pattern deferring expensive pykrx API calls until first data access

**Configuration Centralization:** All constants in config.py enable easy customization without code modification

**Pure Functions:** Data processing functions return new DataFrames enabling composition and testing

**Modular Pipeline:** Clear separation between acquisition, processing, analysis, and export phases

**SQLite Persistence:** Weekly database updates enable incremental backups and reproducible analysis
