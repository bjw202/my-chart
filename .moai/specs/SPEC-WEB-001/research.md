# Research Findings: my_chart Codebase for KR Stock Screener Web Service

## Summary

This document captures deep research findings from the `my_chart` Python package codebase to validate reusability for the KR Stock Screener web service (FastAPI + React).

---

## 1. DB Schema Deep Dive

### Weekly DB (`stock_data_weekly.db`)

Two tables in `my_chart/db/weekly.py`:

#### Table: `stock_prices` (PRIMARY KEY: Name + Date)
| Column | Type | Notes |
|--------|------|-------|
| Name | TEXT NOT NULL | Company name in Korean |
| Date | TEXT NOT NULL | Format: YYYY-MM-DD |
| Open, High, Low, Close | REAL | OHLC price |
| Volume | REAL | Trading volume |
| Volume50MA | REAL | 50-week volume moving average |
| CHG_1W, CHG_1M, CHG_2M, CHG_3M | REAL | Period returns (pct_change) |
| CHG_6M, CHG_9M, CHG_12M | REAL | Period returns (pct_change) |
| MA50, MA150, MA200 | REAL | Moving averages (10/30/40 weekly windows) |
| MA200_Trend_1M to _4M | REAL | MA200 trend over 1-4 months |
| MAX10, MAX52 | REAL | 10-week and 52-week high |
| min52, Close_52min | REAL | 52-week low and ratio to low |
| RS_1M, RS_2M, RS_3M, RS_6M, RS_9M, RS_12M | REAL | Raw relative strength scores |
| RS_Line | REAL | RS line vs KOSPI benchmark |

Indexes: `idx_stock_prices_name(Name)`, `idx_stock_prices_date(Date)`

#### Table: `relative_strength` (PRIMARY KEY: Name + Date)
| Column | Type | Notes |
|--------|------|-------|
| Name, Date | TEXT NOT NULL | |
| RS_12M_Rating | REAL | Percentile rank 0-100 (composite weighted) |
| RS_6M_Rating | REAL | Percentile rank 0-100 |
| RS_3M_Rating | REAL | Percentile rank 0-100 |
| RS_1M_Rating | REAL | Percentile rank 0-100 |

**RS Composite Weighting (weekly.py:254-258):** `RS_12 = rank_1m + 0.8*rank_3m + 0.6*rank_6m + 0.4*rank_9m + 0.2*rank_12m`

### Daily DB (`stock_data_daily.db`)

One table in `my_chart/db/daily.py`:

#### Table: `stock_prices` (PRIMARY KEY: Name + Date)
| Column | Type | Notes |
|--------|------|-------|
| Name, Date | TEXT NOT NULL | |
| Open, High, Low, Close | REAL | |
| Change | REAL | Daily % change |
| High52W | REAL | 52-week high (rolling 252 days) |
| Volume | REAL | |
| Volume20MA | REAL | 20-day volume moving average |
| VolumeWon | REAL | Volume in 억원 (HLC * Volume / 1e8) |
| EMA10, EMA20 | REAL | Exponential moving averages |
| SMA21, SMA50, SMA200 | REAL | Simple moving averages |
| EMA65 | REAL | Exponential MA65 |
| DailyRange | REAL | (High - Low) / (High + Low) * 100 |
| HLC | REAL | (High + Low + Close) / 3 |
| FromEMA10, FromEMA20, FromSMA50, FromSMA200 | REAL | % deviation from each MA |
| Range | REAL | 100 * (High / Low - 1) |
| ADR20 | REAL | 20-day Average Daily Range |

Indexes: `idx_daily_name(Name)`, `idx_daily_date(Date)`

### What's MISSING for Web Filtering
- **Market Cap** - CRITICAL MISSING: Not stored in DB anywhere. Currently fetched via `pykrx.stock.get_market_cap()` at runtime. Must add `stock_meta` table during DB update.
- **MA100** - Not in either DB schema (PRD mentions MA10/20/50/100/200 in chart)
- **Daily CHG_1D/1W** - Daily DB has `Change` (daily %) but no 1-week return
- **Market tag** (KOSPI/KOSDAQ per stock) - Not stored in DB, comes from sectormap

---

## 2. Registry & Sector System (`my_chart/registry.py`)

### Global State (Lines 20-22)
```python
_df_stock: pd.DataFrame | None = None  # @MX:WARN global mutable
_df_sector: pd.DataFrame | None = None
```
**Thread Safety Risk:** Race condition on first concurrent access. Two requests could both see `None` and both load the Excel file.
**Fix:** Pre-initialize during FastAPI `lifespan` startup event.

### `get_stock_registry()` (Lines 33-44)
- Returns DataFrame with columns: `Code`, `Name`, `Market`
- Lazily loads sectormap_original.xlsx (skiprows=8, Korean header row at row 9)
- Code is zero-padded to 6 digits
- No lock protection on initialization

### `add_sector_info(df: pd.DataFrame)` (Lines 119-139)
- Mutates input DataFrame IN-PLACE (adds 3 columns: 산업명(대), 산업명(중), 주요제품)
- Iterates over `df.index` calling `_sector()` per company - **O(n) lookups**
- Input must be indexed by company Name
- Returns 3 sector columns for grouping

### `sectormap_original.xlsx` Contents
- 2,500+ stocks with columns: Code, Name, Market, 산업명(대), 산업명(중), 주요제품
- Header row at row 9 (skiprows=8 skips notes and merged headers)
- Sector columns: `산업명(대)` (major industry), `산업명(중)` (minor industry), `주요제품` (main product)

### `get_companies_by_market_cap()` (Lines 142-170)
- Still uses pykrx at runtime
- Calls `price_naver(REFERENCE_STOCK)` to get latest date, then `stock.get_market_cap(day)`
- Cannot be used in web screening path - must pre-compute during DB update

---

## 3. Screening Functions

### `mmt_companies()` (`my_chart/screening/momentum.py:66-154`)
**Signature:** `mmt_companies(date, rs_period="12M", start="2023-09-01", freq="day", summary=False, db_name=DEFAULT_DB_WEEKLY)`

**What it does:**
1. Calls `pykrx.stock.get_market_cap(date)` at RUNTIME (line 99) - **PROBLEMATIC for web service**
2. Loads weekly DB via `load_price_with_rs(date, db_name)`
3. Applies sequential pandas query filters from `_QUERY_FILTERS` dict
4. Calls `add_sector_info(df)` for sector columns
5. Generates PPTX charts (lines 150-153) - **MUST NOT be called in web service**
6. Writes Excel file (`mmt_{date}_{rs_period}.xlsx`) - side effect to avoid

**Filter Logic (`_QUERY_FILTERS`):**
```
12M: Close > 5000 & Volume50MA > 100000
     Close > MA50
     Close >= 0.75*MAX52 & Close >= 1.3*min52
     RS_12M_Rating > 80

6M:  same + MA50 > MA200 & MA150 > MA200
3M:  no MA filter, just price & volume
```

**Web Service Adaptation:** Replace with pure SQL WHERE clause. Remove pykrx call; use stock_meta table instead.

### `daily_filtering()` (`my_chart/screening/daily_filters.py:13-52`)
**Signature:** `daily_filtering(*query, db_name=DEFAULT_DB_DAILY)`

**What it does:**
1. Opens sqlite3 connection (context manager, safe)
2. Gets latest date from reference stock (삼성전자)
3. Loads ALL stocks for that date
4. Applies sequential pandas query filters
5. Writes Excel file - side effect

**GOOD for web service:** Pure DB queries, no runtime API calls.
**Issue:** Loads entire date snapshot into memory, then filters in pandas. For web service, better to push filters into SQL WHERE clause.

### `high_stocks.py` functions
- `get_high_stocks()`: ENTIRELY pykrx API calls (`stock.get_market_price_change`, `stock.get_market_cap`)
- `투자과열예상종목()`: Entirely pykrx API calls
- **NOT suitable** for web screening path. Only usable as periodic background task.

---

## 4. Price Functions (`my_chart/price.py`)

### `price_naver()` (Lines 55-90)
**Signature:** `price_naver(comp_name, start, end=None, freq="day")`

**Return DataFrame format:**
- Index: DatetimeIndex (Date)
- Columns: Open, High, Low, Close, Volume

**TradingView format needed:** `{time, open, high, low, close, volume}`
- `time`: convert from DatetimeIndex to Unix timestamp or "YYYY-MM-DD" string
- Direct mapping: Open->open, High->high, Low->low, Close->close, Volume->volume

**Global State (Line 20-21):**
```python
_session: requests.Session | None = None  # @MX:WARN global mutable
```
Thread-safe for concurrent reads after init (requests.Session is thread-safe), but lifecycle management concern.

### `price_naver_rs()` (Lines 93-169)
- Returns all OHLCV + full indicator set (MA50/150/200, CHG periods, RS metrics)
- Used for DB generation only; not needed in web service API layer
- The DB already stores all computed values

---

## 5. Config & Paths (`my_chart/config.py`)

### Key Constants
```python
REFERENCE_STOCK = "삼성전자"  # Used for date lookups in DB
INPUT_DIR = Path(__file__).parent.parent / "Input"   # sectormap xlsx here
OUTPUT_DIR = Path(__file__).parent.parent / "Output" # DB files here
SECTORMAP_PATH = INPUT_DIR / "sectormap_original.xlsx"
DEFAULT_DB_WEEKLY = str(OUTPUT_DIR / "stock_data_weekly")  # no .db extension
DEFAULT_DB_DAILY = str(OUTPUT_DIR / "stock_data_daily")    # no .db extension
MIN_CLOSE_PRICE = 5000
CACHE_DIR = Path("./.cache/")  # relative to CWD!
```

### Issues for Web Service
1. **CACHE_DIR is relative to CWD** - Creates `.cache/` wherever uvicorn is run from
2. **Matplotlib imported at module level** - Loads heavy font/rendering deps on import
3. **pptx imported at module level** (via `from pptx.util import Cm`) - Unnecessary for web service
4. **OUTPUT_DIR.mkdir() called at import** - Side effect on import
5. **DB paths lack .db extension** - Must append ".db" everywhere (done via f"{db_name}.db" pattern)

---

## 6. Thread Safety Audit

### Critical Issues

| Component | Risk | Severity | Fix |
|-----------|------|----------|-----|
| `registry.py:_df_stock` | Race condition on init | HIGH | Pre-init in lifespan |
| `registry.py:_df_sector` | Race condition on init | HIGH | Pre-init in lifespan |
| `price.py:_session` | Initialization race | MEDIUM | requests.Session is thread-safe post-init |
| `sqlite3.connect()` | Default check_same_thread=True | HIGH | Add check_same_thread=False or use per-request connections |
| `config.py:CACHE_DIR` | CWD-relative path | LOW | Set absolute path in web service |

### SQLite Connection Pattern
All DB files use context manager pattern (`with sqlite3.connect(f"{db_name}.db") as conn:`).
**Missing:** No `check_same_thread=False` parameter. In FastAPI async context, SQLite connections must be opened with `check_same_thread=False` or use per-request connections.

### `add_sector_info()` In-Place Mutation
Mutates the DataFrame passed as argument. If multiple concurrent requests share the same DataFrame reference, data corruption could occur. Web service must ensure each request gets its own DataFrame copy.

---

## 7. SQL Injection Analysis

### Safe: Parameterized Queries
- `get_nearest_date()` (queries.py:16): `params=[REFERENCE_STOCK]`
- `load_price_with_rs()` (queries.py:31-44): `params=[date]`
- `daily_filtering()` (daily_filters.py:31-37): `params=[REFERENCE_STOCK]`, `params=[today]`

### Risk: pandas df.query() with user input
- `get_query()` (queries.py:63): Accepts `query` string parameter passed to `df.query(query)`
- `daily_filtering()` (daily_filters.py:42): Same pattern with user-provided `*query` args
- **pandas.DataFrame.query() can execute arbitrary Python via `@variable` syntax**
- If web service exposes `POST /api/screen` with raw query strings -> injection risk
- **Mitigation:** Parse filter conditions server-side (e.g., a ScreenRequest Pydantic model) and construct safe SQL/pandas queries programmatically. Never pass user input directly to `df.query()`.

---

## 8. Key Findings for Web Service Implementation

### What Reuses Directly (No Changes)
- `daily_filtering()` logic (filter patterns) - translate to SQL WHERE clauses
- `load_price_with_rs()` - direct reuse for loading DB data
- `get_nearest_date()` - direct reuse
- `get_stock_registry()` - direct reuse (after pre-init in lifespan)
- `add_sector_info()` - direct reuse (ensure copy not shared)
- DB schemas for both weekly and daily (no migration needed)

### What Needs Adaptation
- `mmt_companies()` - Remove pykrx call (market_cap), remove PPTX/Excel output, expose as pure filter function
- `config.py` CACHE_DIR - Convert to absolute path
- sqlite3 connections - Add `check_same_thread=False`
- Registry initialization - Must call `get_stock_registry()` and `get_sector_registry()` in FastAPI lifespan

### What's Missing (New Development Required)
1. **Market Cap storage** - Add `stock_meta` table: `(code TEXT PK, market_cap INTEGER, last_updated DATE)`
2. **DB update triggers market_cap fetch** - During `generate_price_db()`, call `pykrx.stock.get_market_cap()` and store
3. **MA100** - Not in DB schema. Either add during DB generation or compute from price data in API
4. **KOSPI/KOSDAQ per-stock market flag** - Not in DB; comes from registry. Needs JOIN or pre-compute in stock_meta

### Performance Considerations
- `add_sector_info()` is O(n) lookups against pandas DataFrame - consider converting to dict lookup
- Loading all 2570+ stocks for a date: ~100-200KB per date snapshot, acceptable
- RS percentile ranking recalculated per date in `generate_rs_db()` - already pre-computed in `relative_strength` table

---

## 9. Chart Data API Mapping

### price_naver() -> TradingView format
```python
# my_chart price_naver() returns:
# DatetimeIndex, Open, High, Low, Close, Volume

# TradingView Lightweight Charts needs:
# {time: "YYYY-MM-DD", open, high, low, close, volume}

def to_tradingview(df):
    return [
        {"time": idx.strftime("%Y-%m-%d"),
         "open": row["Open"], "high": row["High"],
         "low": row["Low"], "close": row["Close"],
         "volume": row["Volume"]}
        for idx, row in df.iterrows()
    ]
```

### MA columns available from price_naver_rs() or DB:
- Weekly DB: MA50, MA150, MA200 (10/30/40 week windows)
- Daily DB: EMA10, EMA20, SMA21, SMA50, EMA65, SMA200
- **Missing MA100** - Need to add to daily DB or compute on-the-fly

---

## File Path Reference

| File | Purpose | Key Functions |
|------|---------|---------------|
| `my_chart/config.py` | Constants, paths | DB paths, MIN_CLOSE_PRICE |
| `my_chart/registry.py` | Stock/sector lookup | get_stock_registry(), add_sector_info(), _code() |
| `my_chart/price.py` | Naver API fetch | price_naver(), price_naver_rs() |
| `my_chart/db/weekly.py` | Weekly DB generation | generate_price_db(), generate_rs_db() |
| `my_chart/db/daily.py` | Daily DB generation | price_daily_db() |
| `my_chart/db/queries.py` | DB query patterns | load_price_with_rs(), get_nearest_date() |
| `my_chart/screening/momentum.py` | Weekly screening | mmt_companies(), mmt_filtering() |
| `my_chart/screening/daily_filters.py` | Daily screening | daily_filtering(), filter_1/2/etc |
| `my_chart/screening/high_stocks.py` | High performers | get_high_stocks() (pykrx-only) |
