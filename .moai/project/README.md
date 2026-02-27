# my_chart Project Documentation

This directory contains comprehensive project documentation for the my_chart Korean stock market analysis toolkit.

## Documentation Files

### Core Documentation

- **product.md** (5.1 KB) - Product overview, features, target users, use cases, and technology stack summary
- **structure.md** (8.5 KB) - Directory organization, file purposes, module descriptions, and database architecture
- **tech.md** (11 KB) - Complete technology stack, platform requirements, architectural decisions, and development setup

### Codemaps (Detailed Reference)

Located in `codemaps/` subdirectory:

- **overview.md** (14 KB) - High-level system architecture, execution flows, design patterns, and system boundaries
- **modules.md** (14 KB) - Detailed module specifications with responsibilities and public interfaces
- **dependencies.md** (11 KB) - External and internal dependencies, version compatibility, and dependency risks
- **entry-points.md** (14 KB) - Complete public API reference with usage examples and workflow patterns
- **data-flow.md** (14 KB) - Core data flows, request lifecycles, performance characteristics, and optimization strategies

## Quick Navigation

### For Product Managers / Stakeholders
Start with **product.md** for overview, features, and target users.

### For Developers New to the Project
1. Read **structure.md** for file organization
2. Review **codemaps/overview.md** for architecture
3. Check **codemaps/entry-points.md** for API usage

### For Architecture / System Design
Review **codemaps/overview.md** for design patterns and **codemaps/data-flow.md** for processing flows.

### For Integration / API Usage
Consult **codemaps/entry-points.md** for complete API reference with examples.

### For Troubleshooting / Performance
See **tech.md** for error handling and **codemaps/data-flow.md** for performance characteristics.

## Documentation Statistics

- **Total Files:** 8 documents
- **Total Size:** ~114 KB of documentation
- **Code Examples:** 50+ usage examples
- **API Functions:** 40+ documented with signatures
- **Architecture Diagrams:** 5 ASCII diagrams

## Key Project Facts

- **Language:** Python 3.13
- **Architecture:** Modular library (7 functional submodules)
- **Total Code:** 3,587 LOC across 23 files
- **Testing:** 8 integration tests covering data pipeline (SPEC-001)
- **Primary Use:** Jupyter notebooks and IPython REPL
- **Latest SPEC:** SPEC-001 (Data Pipeline Validation & DB Performance) - COMPLETED 2026-02-27

## Core Modules

1. **price** - Naver Finance API data fetching
2. **indicators** - Technical indicator calculations (MACD, RSI, Stochastic, etc.)
3. **registry** - Stock metadata with lazy loading
4. **db** - SQLite database management (weekly/daily price data)
5. **screening** - Stock screening (momentum, daily filters, high stocks)
6. **charting** - Candlestick chart generation with mplfinance
7. **analysis** - Market analysis and reporting
8. **export** - PPTX and TradingView format export

## Technology Highlights

- **Data Processing:** pandas, numpy
- **Visualization:** mplfinance, matplotlib, pillow
- **Data Storage:** SQLite (no external DB needed)
- **Market Data:** Naver Finance API, pykrx
- **Export:** python-pptx, openpyxl, xlsxwriter

## Important Notes

### Database Files
System creates SQLite databases in Output/ directory:
- `Output/stock_data_weekly.db` - Historical OHLCV data
- `Output/stock_data_rs.db` - Relative Strength scores
- `Output/stock_data_daily.db` - Recent daily data

### Data Source
The project uses sectormap.xlsx as the primary data source for stock registry. The pykrx library is no longer reliable (broken KRX API integration in 2024+). All stock codes are loaded from sectormap.xlsx in the Input/ directory.

### Platform-Specific Fonts
- macOS: AppleGothic (auto-detected)
- Windows: Malgun Gothic (auto-detected)
- Charts adjust fonts automatically based on OS

### Entry Points
All public functions exported from `my_chart/__init__.py`:
- 40+ functions available in public API
- Organized by module in codemaps/entry-points.md

## Generated Documentation

This documentation was generated from the my_chart source code analysis.

**Analysis Date:** 2026-02-27
**Code Version:** Latest in repository
**Documentation Format:** Markdown with ASCII diagrams
**Target Audience:** Developers, architects, technical writers

---

For detailed information on any topic, refer to the specific documents listed above.
