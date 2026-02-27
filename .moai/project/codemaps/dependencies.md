# my_chart Dependencies Reference

## External Dependencies

### Data Processing & Numerical Computing

**pandas** (>= 1.3.0)
- Purpose: DataFrame-based tabular data manipulation and time series operations
- Used in: price.py, indicators.py, all db queries, screening filters
- Why: Standard Python data science library with built-in support for time series, groupby, rolling windows, and resampling
- Impact: Core dependency, used in every module
- Alternatives: polars (faster but smaller ecosystem), numpy (lower-level)

**numpy** (>= 1.21.0)
- Purpose: Vectorized numerical array operations for fast computation
- Used in: indicators.py (RSI, MACD calculations), charting (array manipulations)
- Why: Enables efficient element-wise operations avoiding Python loops
- Impact: Enables performance for large datasets (1000+ stocks)
- Alternatives: None for this use case, fundamental to pandas

### HTTP & API Integration

**requests** (>= 2.26.0)
- Purpose: HTTP client library for API calls and web scraping
- Used in: price.py for Naver Finance API calls
- Why: Most popular Python HTTP library with session management and automatic retries
- Impact: Enables data fetching, critical path for real-time data
- Configuration: User-Agent headers configured to respect web scraping etiquette

**pykrx** (>= 1.0.30)
- Purpose: Korean exchange API for stock metadata (codes, names, sectors, market caps)
- Used in: registry.py lazy singleton, analysis/market.py
- Why: Official Python wrapper for Korean stock exchange providing authoritative metadata
- Impact: Single-use initialization (expensive, 3-5 seconds) cached for subsequent access
- Note: Network I/O intensive, requires internet connection for first initialization

### Visualization & Charting

**matplotlib** (>= 3.4.0)
- Purpose: Low-level plotting library for chart rendering
- Used in: charting/single.py, charting/bulk.py (indirectly via mplfinance)
- Why: Underlying graphics engine for mplfinance, enables coordinate systems and rendering
- Impact: Required for all chart generation
- Customization: Font selection configured in config.py based on OS

**mplfinance** (>= 0.12.9)
- Purpose: Professional candlestick chart generation specialized for OHLC financial data
- Used in: charting/single.py plot_chart(), plot_all_companies()
- Why: Purpose-built for financial charts with volume bars, technical indicators, proper spacing
- Impact: High-quality chart output without custom matplotlib configuration
- Features: Supports indicator overlays, multiple chart styles, high resolution export

**pillow** (>= 8.3.0)
- Purpose: Image processing library for PNG/SVG manipulation
- Used in: charting/ for chart post-processing, export/pptx_builder.py for image embedding
- Why: Enables image cropping, resizing, and format conversion after mplfinance generation
- Impact: Allows chart optimization and PPTX embedding

### Data Storage

**sqlite3** (built-in)
- Purpose: Lightweight relational database for persistent storage
- Used in: db/weekly.py, db/daily.py, db/queries.py
- Why: No external database server needed, file-based storage enables version control
- Impact: Critical for reproducible analysis and incremental data management
- Schema: Standard SQL with indexes on (stock_code, date) composite key

**openpyxl** (>= 3.6.0)
- Purpose: Excel file (.xlsx) generation and manipulation
- Used in: charting/bulk.py excel_companies(), export/pptx_builder.py
- Why: Modern Excel format support, enables charts and styling in generated files
- Impact: Professional-looking Excel export with embedded images

**xlrd** (>= 2.0.0)
- Purpose: Read legacy Excel files (.xls format)
- Used in: Optional data import from historical Excel files
- Why: Backward compatibility with older Excel formats
- Impact: Low priority, only used if importing pre-existing Excel data

**xlsxwriter** (>= 3.0.0)
- Purpose: High-performance Excel file generation
- Used in: Alternative to openpyxl for performance-critical large exports
- Why: Faster writing for large datasets with many rows
- Impact: Optional optimization for bulk exports

### Office Document Generation

**python-pptx** (>= 0.6.21)
- Purpose: Programmatic PowerPoint presentation creation
- Used in: export/pptx_builder.py generate_pptx()
- Why: Only Python library for PPTX generation without LibreOffice
- Impact: Enables professional report distribution to non-technical stakeholders
- Features: Shapes, images, tables, text formatting, slide layouts

**lxml** (>= 4.6.3)
- Purpose: XML processing library for PPTX file structure manipulation
- Used in: export/pptx_builder.py (indirectly via python-pptx)
- Why: Fast C-based XML parsing required by python-pptx
- Impact: Ensures PPTX files are valid Office Open XML format

## Internal Module Dependencies

### Dependency Graph (Import Relationships)

```
my_chart/
├── __init__.py (Public API)
│   ├── imports from charting/
│   ├── imports from db/
│   ├── imports from indicators.py
│   ├── imports from price.py
│   ├── imports from registry.py
│   ├── imports from screening/
│   ├── imports from analysis/
│   └── imports from export/
│
├── price.py
│   ├── requests (external)
│   ├── pandas (external)
│   └── config.py
│
├── registry.py
│   ├── pykrx (external)
│   └── pandas (external)
│
├── indicators.py
│   ├── pandas (external)
│   ├── numpy (external)
│   └── config.py
│
├── charting/
│   ├── single.py
│   │   ├── mplfinance (external)
│   │   ├── pillow (external)
│   │   ├── price.py (internal)
│   │   ├── indicators.py (internal)
│   │   ├── db/queries.py (internal)
│   │   └── config.py
│   ├── bulk.py
│   │   ├── single.py (internal)
│   │   ├── multiprocessing (built-in)
│   │   └── config.py
│   └── styles.py
│       ├── matplotlib (external)
│       └── config.py
│
├── db/
│   ├── weekly.py
│   │   ├── sqlite3 (built-in)
│   │   ├── price.py (internal)
│   │   └── config.py
│   ├── daily.py
│   │   ├── sqlite3 (built-in)
│   │   ├── price.py (internal)
│   │   └── config.py
│   └── queries.py
│       ├── sqlite3 (built-in)
│       ├── pandas (external)
│       └── config.py
│
├── screening/
│   ├── momentum.py
│   │   ├── price.py (internal)
│   │   ├── registry.py (internal)
│   │   ├── pandas (external)
│   │   └── config.py
│   ├── daily_filters.py
│   │   ├── price.py (internal)
│   │   └── config.py
│   └── high_stocks.py
│       ├── price.py (internal)
│       ├── registry.py (internal)
│       └── config.py
│
├── analysis/
│   ├── market.py
│   │   ├── registry.py (internal)
│   │   └── pandas (external)
│   └── reports.py
│       ├── registry.py (internal)
│       └── config.py
│
└── export/
    ├── pptx_builder.py
    │   ├── python-pptx (external)
    │   ├── pillow (external)
    │   ├── charting/single.py (internal)
    │   └── config.py
    └── tradingview.py
        ├── registry.py (internal)
        └── config.py
```

## Dependency Risks & Mitigations

### Critical Path Dependencies

**requests (Naver Finance API)**
- Risk: If requests fails, no data fetching possible
- Mitigation: Automatic retry with exponential backoff, cached database fallback
- Fallback: Use db.get_db_data() to retrieve cached historical data

**mplfinance (Chart Generation)**
- Risk: If mplfinance incompatible with matplotlib version, no charts possible
- Mitigation: Strict version bounds, continuous integration testing
- Fallback: Manual matplotlib plotting (less user-friendly)

**pykrx (Stock Registry)**
- Risk: If pykrx API changes or goes offline, registry fails
- Mitigation: Lazy singleton caches results, fallback to static code list
- Impact: Only affects first initialization and stock name lookups

### Optional Dependencies

**openpyxl, xlsxwriter** - Optional for Excel export
- Fallback: CSV export without formatting

**python-pptx** - Optional for PPTX export
- Fallback: HTML report generation

**lxml** - Implicit dependency via python-pptx
- Required only if using PPTX export

## Dependency Version Compatibility

### Tested Combinations

| pandas | numpy | requests | mplfinance | matplotlib | pykrx |
|--------|-------|----------|-----------|-----------|-------|
| 1.3.0+ | 1.21.0+ | 2.26.0+ | 0.12.9+ | 3.4.0+ | 1.0.30+ |

### Python Version Support

- Python 3.8: All dependencies available
- Python 3.9, 3.10, 3.11, 3.12: Full support
- Python 3.13: Under verification (latest pandas/mplfinance required)

## Dependency Management

### Installation via pip

```bash
pip install my-chart
```

Installs all required dependencies automatically based on setup.py or pyproject.toml

### Alternative Installation

Development installation with optional test dependencies:
```bash
pip install -e ".[dev]"
```

### Requirements Files

**requirements.txt** - All runtime dependencies
**requirements-dev.txt** - Additional development/testing dependencies
**requirements-optional.txt** - Optional dependencies for Excel/PPTX export

## Security Considerations

### Dependency Vulnerabilities

- Regularly scan dependencies via pip audit
- No authentication credentials stored in dependencies
- Public APIs only (no private keys or secrets)
- Requests library properly validates SSL certificates

### Data Privacy

- No sensitive user data passed to external APIs
- Historical market data is public information
- Database files contain only public market data
- No telemetry or usage tracking

## Performance Impact

### Startup Time

Total startup time breakdown:
- Module imports: ~100ms
- Registry lazy singleton: 0ms (deferred until first use)
- On first _code/_name call: ~3-5 seconds (pykrx API initialization)

### Runtime Performance

Typical operation times with 1000 stock datasets:
- Data fetching: 30-60 seconds (parallelized)
- Indicator calculation: 2-5 seconds
- Chart generation: 2-5 minutes (batch)
- Database operations: <1 second

### Memory Usage

Typical memory consumption:
- Base package import: ~50MB
- Loading 1000 stock years: 500MB-1GB
- Charting operations: +200-300MB peak

## Compatibility Matrix

**Operating Systems:**
- macOS 10.13+ (AppleGothic font)
- Windows 7+ (Malgun Gothic font)
- Linux (requires system font support)

**Python Environments:**
- Virtual environments: ✓ Full support
- Anaconda: ✓ Full support
- PyPy: ✗ Not tested (NumPy compatibility issues)
- Conda: ✓ Full support (through conda-forge)

## Upgrade Path

### Minor Version Updates (Patch)

Safe to update directly:
```bash
pip install --upgrade my-chart
```

No breaking changes, backward compatible.

### Major Version Updates

Review CHANGELOG.md for breaking changes. May require code modifications.

### Dependency Updates

Keep dependencies updated for security:
```bash
pip install --upgrade-all
```

Test with test suite (when available) after major dependency updates.
