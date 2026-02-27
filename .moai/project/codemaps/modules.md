# my_chart Module Reference

## Price Module (price.py)

**Responsibility:** Fetch historical stock price data from Naver Finance API and provide data cleaning utilities.

### Public Functions

**`price_naver(code: str, start_date: str | datetime, end_date: str | datetime) -> DataFrame`**
- Fetches historical OHLCV data for specified stock code and date range
- Parameters: stock_code (string or integer), start_date, end_date
- Returns: DataFrame indexed by date with Open, High, Low, Close, Volume columns
- Raises: ValueError if code invalid, requests.RequestException if API fails
- Automatic retry with exponential backoff on network failures

**`price_naver_rs(code: str, start_date: str, end_date: str, base_code: str = "KOSPI") -> DataFrame`**
- Fetches price data and calculates Relative Strength vs base index (default KOSPI)
- Returns: DataFrame with additional RS column (0-200 scale)
- RS 100 means stock tracked index perfectly, >100 outperformed, <100 underperformed

**`fix_zero_ohlc(df: DataFrame) -> DataFrame`**
- Handles zero/invalid OHLC values sometimes returned by API
- Interpolates using adjacent valid prices
- Returns cleaned DataFrame

### Implementation Details

Uses requests library with session management for connection pooling. Implements HTML parsing to extract data from Naver Finance web pages. Handles Korean text encoding and date format conversions automatically. Respects Naver Finance rate limits (100 requests/minute).

### Dependencies

- requests: HTTP client
- pandas: Data structure and manipulation
- re: Regular expression parsing

---

## Indicators Module (indicators.py)

**Responsibility:** Calculate technical indicators and add them as new columns to price DataFrames.

### Public Classes/Functions

**`RSI(df: DataFrame, period: int = 14) -> DataFrame`**
- Relative Strength Index (0-100 scale)
- Momentum oscillator measuring overbought/oversold conditions
- Returns: df with added RSI column
- period: default 14 days

**`MACD(df: DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> DataFrame`**
- Moving Average Convergence Divergence
- Returns: df with MACD, MACD_signal, and MACD_diff columns
- MACD_diff = MACD - Signal line (crossover signals)

**`Stochastic(df: DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> DataFrame`**
- Stochastic oscillator measuring momentum
- Returns: df with %K and %D columns
- Values 0-100, <20 oversold, >80 overbought

**`BolingerBand(df: DataFrame, period: int = 20, std_dev: int = 2) -> DataFrame`**
- Bollinger Bands for volatility measurement
- Returns: df with upper_band, middle_band, lower_band columns
- Middle band is 20-day moving average, upper/lower are +/- 2 standard deviations

**`ImpulseMACD(df: DataFrame) -> DataFrame`**
- Specialized MACD variant for momentum confirmation
- Returns: df with impulse_macd column
- Combines price, MACD, and rate of change

**`add_moving_averages(df: DataFrame, periods: list[int] = [20, 50, 200]) -> DataFrame`**
- Adds simple moving averages for multiple periods
- Returns: df with SMA_20, SMA_50, SMA_200 columns
- Default periods: 20-day, 50-day, 200-day

### Usage Pattern

```python
df = price_naver("005930", "2020-01-01", "2024-01-01")
df = RSI(df, period=14)
df = MACD(df)
df = add_moving_averages(df, [20, 50, 200])
# df now has columns: Open, High, Low, Close, Volume, RSI, MACD, MACD_signal, MACD_diff, SMA_20, SMA_50, SMA_200
```

### Implementation Details

All indicators implemented as pure functions returning new DataFrames. Uses pandas rolling windows and expanding operations for efficient calculation. Handles NaN values gracefully (first N rows have NaN for indicators with lookback periods). NumPy used for fast mathematical operations.

---

## Registry Module (registry.py)

**Responsibility:** Provide lazy-loaded lookup functions for stock metadata without startup delay.

### Public Functions

**`_code(name: str) -> str | None`**
- Returns 6-digit Korean stock code for given stock name
- Example: _code("삼성전자") returns "005930"
- Returns None if name not found

**`_name(code: str) -> str | None`**
- Returns Korean stock name for given code
- Example: _name("005930") returns "삼성전자"
- Returns None if code not found

**`_market(code: str) -> str | None`**
- Returns market type for stock code
- Returns: "KOSPI", "KOSDAQ", or "KONEX"
- Returns None if code not found

**`_sector(code: str) -> str | None`**
- Returns sector classification for stock
- Example: _sector("005930") returns "전기전자"
- Returns None if code not found

### Usage Pattern

```python
code = _code("삼성전자")  # "005930"
name = _name("005930")  # "삼성전자"
market = _market("005930")  # "KOSPI"
sector = _sector("005930")  # "전기전자"
```

### Implementation Details

Uses lazy singleton pattern with global cache. First call to any _code/name/market/sector function triggers pykrx API initialization (expensive, 3-5 seconds). Subsequent calls return cached values instantly. Thread-safe via Python GIL for single-threaded REPL usage.

### Dependencies

- pykrx: Korean stock exchange API

---

## Database Module (db/)

**Responsibility:** Manage SQLite databases for price history and RS scores with efficient query interfaces.

### db/weekly.py - Database Generation

**`generate_price_db(start_date: str = None) -> None`**
- Creates/updates weekly_price.db with OHLCV data for all stocks
- Downloads historical data via price_naver() for each stock
- Resamples daily data to weekly for storage efficiency
- Upserts into SQLite (skips existing weeks)
- start_date: optional resume point for partial rebuilds

**`generate_rs_db(base_code: str = "KOSPI") -> None`**
- Creates/updates weekly_rs.db with Relative Strength scores
- Calculates RS for each stock vs base index (default KOSPI)
- RS = (Stock Return / Base Return) * 100
- Stores weekly RS values for trend analysis

### db/queries.py - Query Interface

**`get_db_data(code: str, start_date: str, end_date: str, db_name: str = "weekly") -> DataFrame`**
- Retrieves price data from specified database
- Returns: DataFrame indexed by date with OHLCV columns
- Handles date range queries efficiently with SQL WHERE

**`get_nearest_date(code: str, target_date: str, db_name: str = "weekly") -> datetime`**
- Finds nearest available trading date in database
- Useful for handling weekends and holidays
- Returns: closest date to target_date with available data

**`get_query(sql: str, db_name: str = "weekly") -> DataFrame`**
- Executes custom SQL query against database
- Returns: result as DataFrame
- Advanced queries for custom analysis

### db/daily.py - Daily Database

**`price_daily_db(code: str, start_date: str, end_date: str) -> DataFrame`**
- Retrieves daily data from daily_price.db
- Used for recent trading analysis
- Same interface as get_db_data() but for daily granularity

### Database Schema

**weekly_price table:**
```
stock_code (TEXT, PRIMARY KEY)
date (DATE, PRIMARY KEY)
open (REAL)
high (REAL)
low (REAL)
close (REAL)
volume (INTEGER)
PRIMARY KEY (stock_code, date)
```

**weekly_rs table:**
```
stock_code (TEXT, PRIMARY KEY)
date (DATE, PRIMARY KEY)
rs_score (REAL)
PRIMARY KEY (stock_code, date)
```

---

## Screening Module (screening/)

**Responsibility:** Identify stocks meeting specific criteria for trading opportunities.

### screening/momentum.py

**`mmt_companies(min_12m: float = 0, min_6m: float = 0, min_3m: float = 0, min_monthly: float = None) -> list[str]`**
- Screens stocks by momentum (price return) over different timeframes
- Parameters: minimum return thresholds (percentage)
- Returns: sorted list of qualifying stock codes
- Example: mmt_companies(min_12m=50) finds stocks up 50%+ in 12 months

**`mmt_filtering(codes: list[str], min_return: float) -> list[str]`**
- Filters existing code list by minimum return threshold
- Accepts pre-screened codes and applies additional filter
- Returns: subset of codes meeting return threshold

### screening/daily_filters.py

**`daily_filtering(code: str) -> bool`**
- Applies default daily filter criteria for short-term trading
- Checks: volume surge, volatility, price movement
- Returns: True if stock passes all filters

**`daily_filtering_2(code: str, params: dict) -> bool`**
- Alternative filtering with custom parameters
- params: dictionary of threshold overrides
- Returns: filtering result with custom criteria

**`daily_filtering_3(code: str) -> bool`**
- Another daily filter variant with different logic
- Useful for testing multiple filter strategies

**`filter_1(code: str) -> bool`**
- Individual filter components for volume surge
- Returns: True if volume exceeds threshold

**`filter_2(code: str) -> bool`**
- Individual filter for price volatility
- Returns: True if volatility meets criteria

**`filter_etc(code: str) -> bool`**
- Individual filter for miscellaneous criteria
- Returns: True if additional conditions met

### screening/high_stocks.py

**`get_high_stocks(threshold_percent: float = 5.0) -> list[str]`**
- Finds stocks reaching 52-week highs
- Parameters: percentage threshold for "near high" definition
- Returns: sorted list of high-performing stock codes

**`투자과열예상종목() -> list[str]`**
- Korean function name: "Anticipated overheated investment stocks"
- Detects potential market froth and overheating
- Returns: stocks showing warning signs of overvaluation

---

## Charting Module (charting/)

**Responsibility:** Generate professional candlestick charts with technical indicator overlays.

### charting/single.py

**`plot_chart(code: str, start_date: str = None, end_date: str = None, indicators: list = None, show: bool = True) -> str`**
- Generates candlestick chart for single stock
- Parameters: stock code, date range, optional indicators, display flag
- Returns: file path to saved PNG
- Automatic indicator calculation if not provided

**`rs_history(code: str, start_date: str, end_date: str) -> str`**
- Plots Relative Strength score over time
- Returns: file path to RS line chart PNG

**`plot_mdd(code: str, start_date: str, end_date: str) -> str`**
- Plots Maximum Drawdown analysis
- Shows underwater plot of peak-to-trough decline
- Returns: file path to MDD chart PNG

### charting/bulk.py

**`plot_all_companies(codes: list[str], start_date: str, end_date: str, output_dir: str = "output") -> list[str]`**
- Batch generates charts for multiple stocks
- Parallelizes chart generation for speed
- Returns: list of file paths for all generated charts

**`plot_companies(codes: list[str], start_date: str, end_date: str, specific_codes: list = None) -> list[str]`**
- Selective chart generation from code list
- specific_codes: optional subset to chart
- Returns: file paths for generated charts

**`plot_all_companies_rs_history(codes: list[str], start_date: str, end_date: str) -> list[str]`**
- Batch generates RS charts for comparison
- Returns: file paths for RS history charts

**`excel_companies(codes: list[str], output_file: str = "analysis.xlsx") -> str`**
- Generates Excel workbook with stock data and charts
- Multiple sheets (one per stock) with embedded images
- Returns: file path to generated XLSX

### charting/styles.py

**`apply_chart_style(chart, style_name: str = "default") -> None`**
- Internal function setting chart colors and fonts
- Handles platform-specific font selection (AppleGothic vs Malgun Gothic)
- Supports custom style templates

---

## Analysis Module (analysis/)

**Responsibility:** Provide market-level analysis and report generation.

### analysis/market.py

**`analyze_by_market_cap(codes: list[str] = None) -> DataFrame`**
- Analyzes stocks grouped by market capitalization
- Calculates statistics per market cap segment
- Returns: DataFrame with segment-level metrics

### analysis/reports.py

**`generate_analyst_report(codes: list[str], date_range: tuple) -> str`**
- Generates analyst-style market report
- Includes top performers, sector analysis, trends
- Returns: formatted report text or HTML file path

---

## Export Module (export/)

**Responsibility:** Convert analysis results to external formats for distribution.

### export/pptx_builder.py

**`generate_pptx(charts: list[str], title: str, output_file: str) -> str`**
- Creates PowerPoint presentation from chart files
- Auto-generates title slide, chart slides, summary slide
- Embeds images and formats professionally
- Returns: file path to generated PPTX

### export/tradingview.py

**`tradingview(codes: list[str]) -> str`**
- Exports stock codes in TradingView watchlist format
- Returns: TradingView-compatible text for import

**`company_list_tradingview(codes: list[str], output_file: str = "watchlist.txt") -> str`**
- Batch version writing to file
- Returns: file path to generated watchlist

**`company_to_tradingview_text(code: str) -> str`**
- Single stock conversion to TradingView symbol format
- Handles market-specific prefix (KS for KOSPI, KQ for KOSDAQ)

**`ticker_to_tradingview(code: str) -> str`**
- Converts Korean stock code to TradingView ticker
- Example: "005930" → "KS005930"

**`sector_stocks(sector: str) -> list[str]`**
- Returns all stock codes in specified sector
- Example: sector_stocks("전기전자") → ["005930", "000880", ...]

---

## Summary Table

| Module | Responsibility | Key Functions | Public API |
|--------|-----------------|---------------|-----------|
| price | Data fetching | price_naver, price_naver_rs | 3 functions |
| indicators | Technical indicators | RSI, MACD, Stochastic, Bollinger | 6 classes |
| registry | Stock metadata | _code, _name, _market, _sector | 4 functions |
| db | Data persistence | generate_price_db, get_db_data | 6 functions |
| screening | Stock selection | mmt_companies, daily_filtering | 7+ functions |
| charting | Visualization | plot_chart, plot_all_companies | 7 functions |
| analysis | Market analysis | analyze_by_market_cap | 2 functions |
| export | Format conversion | tradingview, generate_pptx | 5 functions |

Total Public API: **40+ functions exported from my_chart.__all__**
