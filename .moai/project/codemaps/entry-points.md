# my_chart Public API Reference

## Entry Points by Module

### Price Data Fetching

**`price_naver(code: str, start_date: str | datetime, end_date: str | datetime) -> DataFrame`**

Fetches historical OHLCV data from Naver Finance API.

```python
from my_chart import price_naver
import pandas as pd

# Single stock data
df = price_naver("005930", "2020-01-01", "2024-01-01")
# Returns DataFrame with columns: Open, High, Low, Close, Volume

# Date range query
df = price_naver("000660", "2023-06-01", "2023-12-31")
print(df.head())  # View first 5 rows
print(df[["Close", "Volume"]])  # Access specific columns
```

**Parameters:**
- code: Stock code (6-digit string) or stock name (Korean string)
- start_date: Start date as string "YYYY-MM-DD" or datetime object
- end_date: End date as string "YYYY-MM-DD" or datetime object

**Returns:** pandas DataFrame indexed by datetime with OHLCV columns

**`price_naver_rs(code: str, start_date: str, end_date: str, base_code: str = "KOSPI") -> DataFrame`**

Fetches price data with Relative Strength calculation vs base index.

```python
from my_chart import price_naver_rs

# RS vs KOSPI (default)
df = price_naver_rs("005930", "2023-01-01", "2024-01-01")
print(df[["Close", "RS"]])

# RS vs custom base (e.g., specific competitor)
df = price_naver_rs("005930", "2023-01-01", "2024-01-01", base_code="000660")
```

**Parameters:**
- base_code: Reference index (default "KOSPI"), can be any stock code

**Returns:** DataFrame with additional RS column (0-200 scale)

**`fix_zero_ohlc(df: DataFrame) -> DataFrame`**

Cleans DataFrame removing zero/invalid OHLC values.

```python
from my_chart import price_naver, fix_zero_ohlc

df = price_naver("005930", "2020-01-01", "2024-01-01")
df_clean = fix_zero_ohlc(df)  # Interpolate missing values
```

---

### Technical Indicators

**`RSI(df: DataFrame, period: int = 14) -> DataFrame`**

Relative Strength Index (momentum oscillator, 0-100 scale).

```python
from my_chart import price_naver, RSI

df = price_naver("005930", "2023-01-01", "2024-01-01")
df = RSI(df, period=14)
print(df[["Close", "RSI"]])  # RSI column added

# Identify overbought/oversold
overbought = df[df["RSI"] > 70]  # Potential resistance
oversold = df[df["RSI"] < 30]    # Potential support
```

**Common Interpretation:** >70 overbought, <30 oversold, 50 neutral

**`MACD(df: DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> DataFrame`**

Moving Average Convergence Divergence (trend and momentum).

```python
from my_chart import price_naver, MACD

df = price_naver("005930", "2023-01-01", "2024-01-01")
df = MACD(df)
print(df[["Close", "MACD", "MACD_signal", "MACD_diff"]])

# MACD crossover signals
bullish = df[df["MACD"] > df["MACD_signal"]]  # Bullish signal
bearish = df[df["MACD"] < df["MACD_signal"]]  # Bearish signal
```

**Columns Added:** MACD, MACD_signal, MACD_diff (crossover indicator)

**`Stochastic(df: DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> DataFrame`**

Stochastic oscillator (momentum, 0-100 scale).

```python
from my_chart import price_naver, Stochastic

df = price_naver("005930", "2023-01-01", "2024-01-01")
df = Stochastic(df)
print(df[["Close", "Stochastic_%K", "Stochastic_%D"]])

# Signals: <20 oversold, >80 overbought
strong_signal = df[(df["Stochastic_%K"] < 20) & (df["Close"].diff() > 0)]
```

**Columns Added:** Stochastic_%K, Stochastic_%D

**`BolingerBand(df: DataFrame, period: int = 20, std_dev: int = 2) -> DataFrame`**

Bollinger Bands (volatility measurement with trend).

```python
from my_chart import price_naver, BolingerBand

df = price_naver("005930", "2023-01-01", "2024-01-01")
df = BolingerBand(df)
print(df[["Close", "lower_band", "middle_band", "upper_band"]])

# Band squeeze indicates low volatility
band_width = df["upper_band"] - df["lower_band"]
low_vol_periods = df[band_width < band_width.quantile(0.25)]
```

**Columns Added:** upper_band, middle_band, lower_band

**`ImpulseMACD(df: DataFrame) -> DataFrame`**

ImpulseMACD variant for momentum confirmation.

```python
from my_chart import price_naver, ImpulseMACD

df = price_naver("005930", "2023-01-01", "2024-01-01")
df = ImpulseMACD(df)
print(df[["Close", "impulse_macd"]])
```

**`add_moving_averages(df: DataFrame, periods: list[int] = [20, 50, 200]) -> DataFrame`**

Simple moving averages for trend identification.

```python
from my_chart import price_naver, add_moving_averages

df = price_naver("005930", "2023-01-01", "2024-01-01")
df = add_moving_averages(df, [20, 50, 200])
print(df[["Close", "SMA_20", "SMA_50", "SMA_200"]])

# Golden cross: 50-day crosses above 200-day
golden_cross = df[(df["SMA_50"] > df["SMA_200"]) &
                  (df["SMA_50"].shift(1) <= df["SMA_200"].shift(1))]
```

**Columns Added:** SMA_N for each period

---

### Stock Metadata (Registry)

**`_code(name: str) -> str | None`**

Get 6-digit stock code from Korean name.

```python
from my_chart import _code, _name, _market, _sector

# Stock name to code
code = _code("삼성전자")
print(code)  # "005930"

name = _code("존재하지않는회사")
print(name)  # None
```

**`_name(code: str) -> str | None`**

Get Korean stock name from code.

```python
from my_chart import _name

name = _name("005930")
print(name)  # "삼성전자"
```

**`_market(code: str) -> str`**

Get market type (KOSPI, KOSDAQ, KONEX).

```python
from my_chart import _market

market = _market("005930")
print(market)  # "KOSPI" (large-cap)

market = _market("096110")  # Mid-cap example
print(market)  # "KOSDAQ"
```

**`_sector(code: str) -> str | None`**

Get sector classification.

```python
from my_chart import _sector

sector = _sector("005930")
print(sector)  # "전기전자" (Electronics)
```

---

### Database Operations

**`generate_price_db(start_date: str = None) -> None`**

Build/update weekly price database.

```python
from my_chart import generate_price_db

# Full database generation (very slow, 30+ minutes)
# generate_price_db()

# Incremental update (fetches recent weeks)
generate_price_db(start_date="2024-01-01")

# After completion, use get_db_data() for fast historical queries
```

**`generate_rs_db(base_code: str = "KOSPI") -> None`**

Build/update Relative Strength database.

```python
from my_chart import generate_rs_db

# Generate RS scores vs KOSPI
generate_rs_db(base_code="KOSPI")
```

**`price_daily_db(code: str, start_date: str, end_date: str) -> DataFrame`**

Get daily price data from daily database.

```python
from my_chart import price_daily_db

df = price_daily_db("005930", "2024-01-01", "2024-01-31")
print(df)  # Daily OHLCV data
```

**`get_db_data(code: str, start_date: str, end_date: str, db_name: str = "weekly") -> DataFrame`**

Query historical data from database (fast).

```python
from my_chart import get_db_data

# Weekly data (resampled)
df = get_db_data("005930", "2023-01-01", "2024-01-01", db_name="weekly")

# Daily data
df = get_db_data("005930", "2023-01-01", "2024-01-01", db_name="daily")
```

**`get_nearest_date(code: str, target_date: str, db_name: str = "weekly") -> datetime`**

Find nearest trading date with available data.

```python
from my_chart import get_nearest_date

# Find nearest date to 2024-01-01
nearest = get_nearest_date("005930", "2024-01-01")
print(nearest)  # datetime.date
```

**`get_query(sql: str, db_name: str = "weekly") -> DataFrame`**

Execute custom SQL query on database.

```python
from my_chart import get_query

# Custom SQL example
sql = "SELECT * FROM prices WHERE close > 50000 AND volume > 1000000"
df = get_query(sql)
```

---

### Stock Screening

**`mmt_companies(min_12m: float = 0, min_6m: float = 0, min_3m: float = 0, min_monthly: float = None) -> list[str]`**

Screen stocks by momentum (price returns).

```python
from my_chart import mmt_companies, _name

# Top performers (50%+ annual return)
strong_stocks = mmt_companies(min_12m=50)
print(f"Found {len(strong_stocks)} stocks with 50%+ annual return")

# Multi-timeframe screening
strong_short = mmt_companies(min_3m=10, min_6m=20, min_12m=30)

# Show top 5 with names
for code in strong_short[:5]:
    print(f"{code}: {_name(code)}")
```

**Parameters:** Minimum return percentage (positive number for gains)

**Returns:** Sorted list of stock codes

**`mmt_filtering(codes: list[str], min_return: float) -> list[str]`**

Filter code list by momentum threshold.

```python
from my_chart import mmt_filtering

codes = ["005930", "000660", "005380", ...]
gainers = mmt_filtering(codes, min_return=20)  # 20%+ return
```

**`daily_filtering(code: str) -> bool`**

Check if stock passes daily filter criteria.

```python
from my_chart import daily_filtering, mmt_companies

candidates = mmt_companies(min_12m=50)
today_best = [c for c in candidates if daily_filtering(c)]
print(f"Today's trading opportunities: {today_best}")
```

**Returns:** True if stock passes all filters

**`get_high_stocks(threshold_percent: float = 5.0) -> list[str]`**

Find stocks reaching 52-week highs.

```python
from my_chart import get_high_stocks

# Stocks within 5% of 52-week high
near_highs = get_high_stocks(threshold_percent=5.0)
print(f"Near 52-week high: {len(near_highs)} stocks")
```

**`투자과열예상종목() -> list[str]`**

Find stocks showing overheating signals (Korean name).

```python
from my_chart import 투자과열예상종목

overheated = 투자과열예상종목()
print(f"Potential market froth: {len(overheated)} stocks")
```

---

### Charting & Visualization

**`plot_chart(code: str, start_date: str = None, end_date: str = None, indicators: list = None, show: bool = True) -> str`**

Generate candlestick chart for single stock.

```python
from my_chart import plot_chart, RSI, MACD

# Simple chart
file_path = plot_chart("005930", "2023-01-01", "2024-01-01")
print(f"Chart saved to: {file_path}")

# Chart with indicators
def get_indicators(df):
    df = RSI(df)
    df = MACD(df)
    return df

file_path = plot_chart("005930", "2023-01-01", "2024-01-01",
                       indicators=[RSI, MACD])
```

**Returns:** File path to generated PNG chart

**`rs_history(code: str, start_date: str, end_date: str) -> str`**

Plot Relative Strength over time.

```python
from my_chart import rs_history

file_path = rs_history("005930", "2023-01-01", "2024-01-01")
print(f"RS chart: {file_path}")
```

**`plot_all_companies(codes: list[str], start_date: str, end_date: str, output_dir: str = "output") -> list[str]`**

Batch generate charts for multiple stocks.

```python
from my_chart import plot_all_companies, mmt_companies

# Chart top momentum stocks
top_stocks = mmt_companies(min_12m=50)[:10]
files = plot_all_companies(top_stocks, "2023-01-01", "2024-01-01")
print(f"Generated {len(files)} charts")
```

**`excel_companies(codes: list[str], output_file: str = "analysis.xlsx") -> str`**

Generate Excel workbook with stock data and charts.

```python
from my_chart import excel_companies, mmt_companies

candidates = mmt_companies(min_12m=50)[:5]
file_path = excel_companies(candidates, "market_analysis.xlsx")
print(f"Excel report: {file_path}")
```

---

### Export & Reporting

**`tradingview(codes: list[str]) -> str`**

Export stocks in TradingView watchlist format.

```python
from my_chart import tradingview, mmt_companies

candidates = mmt_companies(min_12m=50)
tv_list = tradingview(candidates)
print(tv_list)
# Output: KS005930,KS000660,KS005380,...
```

**Returns:** TradingView-compatible comma-separated symbol list

**`company_list_tradingview(codes: list[str], output_file: str = "watchlist.txt") -> str`**

Export to TradingView watchlist file.

```python
from my_chart import company_list_tradingview, daily_filtering, mmt_companies

candidates = mmt_companies(min_12m=50)
today_picks = [c for c in candidates if daily_filtering(c)]
file_path = company_list_tradingview(today_picks, "today_watchlist.txt")
print(f"Watchlist: {file_path}")
```

**`company_to_tradingview_text(code: str) -> str`**

Convert single code to TradingView symbol.

```python
from my_chart import company_to_tradingview_text

tv_symbol = company_to_tradingview_text("005930")
print(tv_symbol)  # "KS005930"
```

**`sector_stocks(sector: str) -> list[str]`**

Get all stocks in specified sector.

```python
from my_chart import sector_stocks, _sector

# All electronics stocks
electronics = sector_stocks("전기전자")
print(f"Electronics stocks: {len(electronics)}")

# By sector name
for code in electronics[:5]:
    print(f"{code}")
```

**Common Sectors:** 전기전자, 반도체, 은행, 의약품, 화학, 건설, 운송, 해운, 금융

---

## Complete Workflow Example

```python
from my_chart import (
    price_naver, RSI, MACD,
    mmt_companies, daily_filtering,
    plot_chart, tradingview, _name
)

# 1. Find momentum stocks
print("=== Momentum Screening ===")
momentum_stocks = mmt_companies(min_12m=50, min_6m=30)
print(f"Found {len(momentum_stocks)} strong momentum stocks")

# 2. Daily filter
print("\n=== Daily Filter ===")
today_candidates = [c for c in momentum_stocks if daily_filtering(c)]
print(f"Today's candidates: {today_candidates[:5]}")

# 3. Technical analysis on top candidate
code = today_candidates[0]
print(f"\n=== Analyzing {_name(code)} ({code}) ===")
df = price_naver(code, "2023-01-01", "2024-01-01")
df = RSI(df)
df = MACD(df)
print(df[["Close", "RSI", "MACD"]].tail())

# 4. Generate chart
print("\n=== Chart Generation ===")
chart_file = plot_chart(code, "2023-06-01", "2024-01-01")
print(f"Chart saved: {chart_file}")

# 5. Export to TradingView
print("\n=== TradingView Export ===")
tv_list = tradingview(today_candidates[:10])
print(f"TradingView symbols: {tv_list}")
```

**Output Example:**
```
=== Momentum Screening ===
Found 127 strong momentum stocks

=== Daily Filter ===
Today's candidates: ['005930', '000660', '005380', '051910', '035420']

=== Analyzing 삼성전자 (005930) ===
                 Close        RSI        MACD
2024-01-25  70500.0  45.234567  123.456789
2024-01-26  71200.0  48.567890  125.123456
2024-01-29  72300.0  52.345678  127.234567

=== Chart Generation ===
Chart saved: /output/005930_20231201_20240131.png

=== TradingView Export ===
TradingView symbols: KS005930,KS000660,KS005380,KS051910,KS035420,...
```

---

## API Organization by Use Case

**Quick Start:** price_naver(), plot_chart(), RSI(), MACD()

**Systematic Screening:** mmt_companies(), daily_filtering(), get_high_stocks()

**Database Analytics:** generate_price_db(), get_db_data(), get_query()

**Professional Reports:** plot_all_companies(), excel_companies(), tradingview()

**Advanced Analysis:** add_moving_averages(), Stochastic(), BolingerBand(), ImpulseMACD()

**Metadata Lookups:** _code(), _name(), _market(), _sector(), sector_stocks()
