# SPEC-001 Research: Data Pipeline Validation & DB Optimization

## Deep Codebase Analysis Results

### 1. price.py - Naver Finance API

**API Endpoint (hardcoded):**
```
https://api.finance.naver.com/siseJson.naver?symbol={code}&requestType=1&startTime={start}&endTime={end}&timeframe={freq}
```

**Bugs Found:**
| Bug | Severity | Description |
|-----|----------|-------------|
| MAX 10W = MAX 52W | P1 | `price["MAX 10W"]` and `price["MAX 52W"]` both use `rolling(window=52).max()` — identical calculation |
| No error handling | P1 | `requests.get()` has no try/except, timeout, or retry logic |
| MA naming mismatch | P2 | `MA50` uses `window=10` (weekly data: 10 weeks = ~2.5 months, not 50 days) — intentional for weekly but confusing |
| Empty data check order | P3 | Slices DataFrame before checking length |

**No parallel processing.** Purely synchronous requests.

### 2. registry.py - Lazy Loading

**pykrx calls:** `stock.get_market_ticker_list()`, `stock.get_market_ticker_name()`, `stock.get_market_cap()`

**Bugs Found:**
| Bug | Severity | Description |
|-----|----------|-------------|
| `_sector()` return type mismatch | P2 | Returns dict but `add_sector_info` checks `== "NoData"` (never True) |
| REFERENCE_STOCK duplicate | P3 | Defined in both config.py and registry.py |
| Sequential ticker loading | P2 | All tickers loaded one-by-one in loop |

**sectormap.xlsx:** 2,569 stocks, columns: Code, Name, Market, industry_large, industry_mid, main_product

### 3. db/weekly.py - Weekly DB Generation

**Critical Issues:**
- **DROP TABLE on every run** — destroys all existing data, no incremental update
- **Purely sequential** — each stock fetched one at a time
- **33 columns** in stock_prices table (price + indicators + RS)
- **100-stock sleep** of 0.5s for rate limiting
- `generate_rs_db` auto-called at end, adds relative_strength table
- `rank_9m` calculated but not stored in table

**Estimated time:** 2,500+ stocks x ~500ms = 20-30 minutes minimum (without RS)

### 4. db/daily.py - Daily DB Generation

**Critical Bug:** Date calculation `m - 1` fails in January (produces month 0)
```python
start = f"{y - 1}-{m - 1:02}-{d:02}"  # January → 2025-00-27 = INVALID
```

**Also:** DROP TABLE on every run, no incremental updates, no parallel processing.

### 5. db/queries.py - Query Interface

**Issues:**
- f-string SQL (injection risk, low practical concern for internal tool)
- `.cache` directory hardcoded, must exist or crashes
- `get_db_data` does too much (query + chart + PPTX in one function)

### 6. config.py - Constants

**DB path issue:** `DEFAULT_DB_WEEKLY = "stock_data_weekly"` — no directory prefix, DB files created in CWD not Output/

### 7. screening/momentum.py - Unified mmt_companies

**Issues:**
- Hardcoded `RS_12M_Rating` column regardless of `rs_period` parameter
- `.cache` directory assumption
- Uses DB data (good), but DB must exist first

### 8. Current State Summary

| Component | Status | Blocking Issues |
|-----------|--------|----------------|
| price.py (API fetch) | Likely working | No error handling, no retries |
| registry.py (pykrx) | Likely working | Sequential loading slow |
| db/weekly.py | Unknown | DROP TABLE destroys data |
| db/daily.py | BROKEN | January date bug |
| db/queries.py | Working with DB | .cache dir dependency |
| sectormap.xlsx | Present | 2,569 stocks available |

### 9. Performance Bottlenecks

1. **DB generation is O(n) sequential** — no parallelism
2. **Each stock = 1 API call** — ~500ms per stock
3. **No connection pooling** for requests
4. **No batch INSERT** — row-by-row insertion
5. **No WAL mode** for SQLite — default journal mode
6. **DROP TABLE + recreate** instead of UPSERT

### 10. Optimization Opportunities

| Optimization | Expected Improvement |
|-------------|---------------------|
| ThreadPoolExecutor for API calls | 5-10x faster (rate-limit bounded) |
| Batch INSERT with executemany | 3-5x faster DB writes |
| WAL mode for SQLite | Better concurrent read/write |
| UPSERT instead of DROP/CREATE | Incremental updates possible |
| Connection pooling (requests.Session) | 20-30% faster HTTP |
| Ordered insertion (sorted by code) | Better B-tree performance |
