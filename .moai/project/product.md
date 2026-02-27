# my_chart Product Documentation

## Project Overview

**Project Name:** my_chart

**Tagline:** Korean stock market analysis and visualization toolkit for Jupyter notebooks and REPL environments

**Description:** my_chart is a comprehensive Python library that fetches historical stock price data from the Korean market via Naver Finance API, calculates advanced technical indicators, generates professional candlestick charts with mplfinance, screens stocks based on momentum and daily filters, and exports analysis results to PPTX presentations and TradingView format. Designed for individual investors and quantitative analysts working with Korean stocks (KOSPI, KOSDAQ, KONEX markets).

## Core Features

1. **Market Data Integration** - Fetch historical OHLC (Open, High, Low, Close) data from Naver Finance API with automatic handling of Korean market hours and holidays

2. **Technical Indicators** - Calculate MACD, RSI, Stochastic, Bollinger Bands, ImpulseMACD, and moving averages with optimized implementations for large datasets

3. **Candlestick Charting** - Generate professional candlestick charts with mplfinance integration, supporting single and multi-stock visualizations with technical overlay indicators

4. **Stock Screening** - Momentum-based screening (12-month, 6-month, 3-month returns), daily filter screening (volume, price movement, volatility), and overheated stock detection

5. **Database Management** - SQLite-based persistent storage for weekly price data and Relative Strength (RS) scores, with efficient query interfaces and incremental updates

6. **PPTX Export** - Generate professional PowerPoint presentations containing stock charts, analysis tables, and performance reports for client delivery

7. **TradingView Integration** - Export screened stocks in TradingView-compatible format for further analysis and charting in external platforms

8. **Market Cap Analysis** - Analyze stocks by market capitalization segments and generate analyst-style reports with comparative metrics

9. **Relative Strength Calculation** - Calculate RS scores comparing individual stocks to KOSPI index for relative performance measurement

## Target Users

- Korean stock market investors using Jupyter notebooks for analysis
- Quantitative analysts building systematic screening strategies
- Portfolio managers requiring technical analysis and reporting tools
- Financial advisors needing professional chart generation for client presentations
- Retail traders analyzing KOSPI, KOSDAQ, and KONEX stocks

## Key Use Cases

**Momentum Screening:** Identify stocks with strong 12-month, 6-month, or 3-month performance trends using `mmt_companies()` function

**Daily Trading Signals:** Apply daily filter screens for volume surges, price movements, and volatility patterns to find intraday trading opportunities

**Chart Generation:** Create publication-ready candlestick charts with technical indicators overlays for individual stock analysis

**Portfolio Performance Reports:** Generate PPTX presentations containing multiple stock charts and performance metrics for stakeholder communication

**Market Segment Analysis:** Analyze stocks grouped by market cap categories using `analyze_by_market_cap()` for market structure insights

**TradingView Export:** Export screening results directly to TradingView notation for collaborative analysis and multi-timeframe studies

**Systematic Backtesting:** Use screened stock lists and historical data for systematic strategy backtesting and validation

## Technology Stack

**Core Libraries:** pandas (data manipulation), numpy (numerical computing), requests (HTTP client for data fetching)

**Visualization:** matplotlib (low-level plotting), mplfinance (candlestick charts), pillow (image processing)

**Data Storage:** sqlite3 (relational database), openpyxl (Excel generation), xlrd (Excel reading), xlsxwriter (Excel writing)

**Korean Market Data:** pykrx (Korean exchange API), Naver Finance (web scraping for historical prices)

**Office Documents:** python-pptx (PowerPoint generation), lxml (XML processing)

## Market Coverage

- **KOSPI:** Korea Composite Stock Price Index (Korean large-cap stocks)
- **KOSDAQ:** Korean Securities Dealers Automated Quotations (Korean mid-cap and small-cap stocks)
- **KONEX:** Korea New Exchange (Korean emerging market stocks)

Data includes historical daily prices (open, high, low, close, volume) with automatic Korean market holiday handling and business day calculations.

## Installation & Quick Start

The package integrates seamlessly with Jupyter notebooks and IPython REPL environments. Standard installation via pip with required dependencies for data processing, visualization, and office document generation. Supports Python 3.8+ with macOS (AppleGothic font) and Windows (Malgun Gothic font) system font detection for chart readability.

## Quality Standards

- Modular architecture with clear separation of concerns
- Pure functions for data transformation enabling composition
- Lazy-loaded registry patterns minimizing startup time
- SQLite database for reproducible analysis and version control
- Comprehensive error handling for API failures and data inconsistencies
