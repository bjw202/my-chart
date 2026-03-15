# SPEC-WEEKLY-CHART-001: Weekly DB SMA Rename + Daily/Weekly Chart Toggle

| Field       | Value                                          |
|-------------|------------------------------------------------|
| SPEC ID     | SPEC-WEEKLY-CHART-001                          |
| Title       | Weekly DB SMA Rename + Daily/Weekly Chart Toggle |
| Status      | Planned                                        |
| Priority    | High                                           |
| Created     | 2026-03-04                                     |
| Lifecycle   | spec-anchored                                  |

---

## 1. Environment

### 1.1 Daily DB (`Output/stock_data_daily.db`, table: `stock_prices`)

- MA columns: EMA10, EMA20, SMA21, SMA50, EMA65, SMA100, SMA200
- Chart API currently serves **only** this DB via `backend/services/chart_service.py`
- Chart endpoint: `GET /api/chart/{code}` (no timeframe parameter)
- Daily price generation: `my_chart/db/daily.py` -- **no changes needed**

### 1.2 Weekly DB (`Output/stock_data_weekly.db`, table: `stock_prices`)

- Current MA columns: MA50, MA150, MA200 (confusingly named after daily-equivalent trading days)
- Actual rolling windows: MA50=rolling(10), MA150=rolling(30), MA200=rolling(40)
- Also has: MA200_Trend_1M/2M/3M/4M, CHG_1W/1M/2M/3M/6M/9M/12M, RS_Line, Volume50MA
- Source calculation: `my_chart/price.py` `price_naver_rs()` (lines 133-144)
- DB generation: `my_chart/db/weekly.py` (DDL + column tuples)

### 1.3 Meta Service (`backend/services/meta_service.py`)

- `stock_meta` table DDL includes: `ma50_w`, `ma150_w`, `ma200_w`
- Reads weekly.stock_prices columns: `MA50, MA150, MA200` (line 136)
- Maps to stock_meta: w[3]=ma50_w, w[4]=ma150_w, w[5]=ma200_w

### 1.4 Frontend

- `ChartCell.tsx` renders TradingView Lightweight Charts with MA overlays
- `ChartGrid.tsx` manages grid layout (2x2/3x3 toggle, pagination)
- `chart.ts` API client calls `GET /chart/{code}` with no timeframe support
- `chart.ts` types define `MAOverlay` with ema10/ema20/sma50/sma100/sma200

---

## 2. Assumptions

| ID | Assumption | Confidence | Risk if Wrong |
|----|-----------|------------|---------------|
| A1 | Weekly DB can be regenerated after schema change (no migration needed) | High | Must regenerate entire weekly DB; ~10 min process |
| A2 | stock_meta rebuild (`meta_service.py`) runs after weekly DB update | High | Stale meta columns if not rebuilt |
| A3 | Users do not depend on MA50/MA150/MA200 column names externally | High | No external API consumers; only internal |
| A4 | Timeframe toggle should be grid-level (affects all visible charts) | High | Per-cell toggle would require individual re-fetch per cell |
| A5 | Default timeframe is "daily" for backward compatibility | High | Changing default would break existing links/bookmarks |
| A6 | Weekly chart needs fewer data points (LIMIT ~200 weeks vs 504 days) | Medium | Over-fetching wastes bandwidth but is not harmful |
| A7 | Weekly volume unit is raw Volume, not VolumeWon (no HLC*Volume conversion in weekly) | High | Different display unit; frontend must handle |

---

## 3. Requirements

### Domain A: Weekly DB Schema Update

**R1 -- SMA Column Rename (DB generation)**

**When** the weekly DB generation (`generate_price_db`) executes, **then** the system **shall** store weekly moving averages under columns named `SMA10`, `SMA20`, `SMA40` instead of `MA50`, `MA150`, `MA200`.

- SMA10 = Close.rolling(window=10) -- 10-week SMA (~50 daily trading days)
- SMA20 = Close.rolling(window=20) -- 20-week SMA (~100 daily trading days)
- SMA40 = Close.rolling(window=40) -- 40-week SMA (~200 daily trading days)

NOTE: SMA20 window changes from 30 to 20 (intentional recalculation, not just rename).

**R2 -- SMA Trend Columns**

**When** SMA40 is computed, **then** the system **shall** calculate and store trend columns as `SMA40_Trend_1M`, `SMA40_Trend_2M`, `SMA40_Trend_3M`, `SMA40_Trend_4M` using `SMA40.pct_change(4 * months)`.

**R3 -- Volume MA Rename**

**When** the weekly DB generation executes, **then** the system **shall** rename the volume moving average column from `Volume50MA` / `Volume MA50` to `VolumeSMA10` / `Volume SMA10` for naming consistency.

**R4 -- DDL and Column Tuple Update**

The system **shall** update all column definition locations for the weekly DB:

| Location | File | What Changes |
|----------|------|-------------|
| `_STOCK_PRICES_COLS` | `my_chart/db/weekly.py` (line 32) | MA50->SMA10, MA150->SMA20, MA200->SMA40, Volume50MA->VolumeSMA10, MA200_Trend_*->SMA40_Trend_* |
| `_PRICE_DF_COLS` | `my_chart/db/weekly.py` (line 45) | Matching DataFrame column name updates |
| `_ensure_stock_prices_table` DDL | `my_chart/db/weekly.py` (line 68) | SQL column names in CREATE TABLE |
| `price_naver_rs()` | `my_chart/price.py` (line 133) | DataFrame column assignments and references |

**R5 -- Meta Service Update**

**When** the stock_meta rebuild runs, **then** the system **shall**:
- Read weekly columns `SMA10, SMA20, SMA40` instead of `MA50, MA150, MA200`
- Rename stock_meta DDL columns: `ma50_w` -> `sma10_w`, `ma150_w` -> `sma20_w`, `ma200_w` -> `sma40_w`
- Update the SELECT query and tuple index mapping in `_rebuild()`

Files affected:
- `backend/services/meta_service.py`: DDL (line 20), SELECT (line 136), mapping (lines 219-221)

### Domain B: Backend API -- Timeframe Support

**R6 -- Chart Endpoint Timeframe Parameter**

**When** a client requests `GET /api/chart/{code}?timeframe=weekly`, **then** the system **shall** return weekly candlestick + MA data from the weekly DB.

**If** the `timeframe` parameter is omitted, **then** the system **shall** default to `daily` (backward compatible).

Valid values: `daily`, `weekly`.

**R7 -- Weekly Chart Data Query**

**When** timeframe is `weekly`, **then** `chart_service.py` **shall**:
- Connect to the weekly DB (`WEEKLY_DB_PATH`)
- SELECT: Date, Open, High, Low, Close, Volume, VolumeSMA10, SMA10, SMA20, SMA40
- Resolve stock name from daily DB's `stock_meta` table (weekly DB has no stock_meta)
- ORDER BY Date DESC, LIMIT 200 (approximately 4 years of weekly data)
- Return data in chronological order (reversed)

**R8 -- Weekly MA Response Schema**

**When** timeframe is `weekly`, **then** the response `ma` field **shall** contain:
- `sma10`: list of MAPoint (10-week SMA series)
- `sma20`: list of MAPoint (20-week SMA series)
- `sma40`: list of MAPoint (40-week SMA series)

The response schema **shall** use a discriminated union or conditional structure:
- Daily response: `ma` contains `{ ema10, ema20, sma50, sma100, sma200 }`
- Weekly response: `ma` contains `{ sma10, sma20, sma40 }`

Recommended approach: Make all MA fields optional in a single `MAOverlays` model, populating only the relevant fields per timeframe. The `timeframe` field in ChartResponse indicates which set is populated.

**R9 -- Weekly Volume Handling**

**When** timeframe is `weekly`, **then** the system **shall** return `Volume` as raw share count (not VolumeWon). The weekly DB does not store VolumeWon.

Frontend must handle the display unit difference:
- Daily: VolumeWon in 100M KRW units
- Weekly: Raw Volume share count

### Domain C: Frontend -- Timeframe Toggle UI

**R10 -- Grid-Level Timeframe Toggle**

The system **shall** provide a timeframe toggle button in the `ChartGrid` toolbar (next to the existing grid size toggle).

- Toggle label: `D` (daily, default) / `W` (weekly)
- Toggling changes the timeframe for **all** visible chart cells simultaneously
- Toggle state persists during the session (not across page reloads)

**R11 -- Chart Re-fetch on Toggle**

**When** the user toggles the timeframe, **then** each visible `ChartCell` **shall**:
- Show a loading spinner
- Call `fetchChartData(code, timeframe)` with the new timeframe
- Destroy and recreate the TradingView chart (to clear old series)
- Apply timeframe-appropriate MA colors and series

**R12 -- Weekly MA Color Scheme**

**While** the timeframe is `weekly`, the `ChartCell` **shall** render MA overlays with:

| MA Key | Color | Label Equivalent |
|--------|-------|-----------------|
| sma10  | `#06d6a0` (green) | ~Daily SMA50 |
| sma20  | `#118ab2` (blue) | ~Daily SMA100 |
| sma40  | `#073b4c` (dark) | ~Daily SMA200 |

NOTE: Weekly mode displays 3 MA lines vs daily mode's 5 MA lines.

**R13 -- Visible Range for Weekly Charts**

**When** timeframe is `weekly`, **then** the chart **shall** set the initial visible range to approximately 52 weeks (1 year), allowing the user to zoom/scroll to see the full ~200 weeks of data.

### Domain D: Backward Compatibility

**R14 -- Default Timeframe**

**If** no `timeframe` query parameter is provided, **then** the system **shall** behave identically to the current implementation (daily data, daily MA overlays).

The system **shall not** break any existing frontend calls that omit the timeframe parameter.

**R15 -- API Response Envelope**

The `ChartResponse` **shall** include a `timeframe` string field (`"daily"` or `"weekly"`) so the frontend can confirm which dataset was returned.

---

## 4. Specifications

### 4.1 File Impact Summary

| File | Change Type | Domain |
|------|-----------|--------|
| `my_chart/price.py` | Modify | A (SMA rename + window change) |
| `my_chart/db/weekly.py` | Modify | A (columns, DDL) |
| `backend/services/meta_service.py` | Modify | A (DDL, SELECT, mapping) |
| `backend/services/chart_service.py` | Modify | B (add weekly query function) |
| `backend/routers/chart.py` | Modify | B (add timeframe param) |
| `backend/schemas/chart.py` | Modify | B (add weekly MA fields, timeframe field) |
| `frontend/src/api/chart.ts` | Modify | C (add timeframe param) |
| `frontend/src/types/chart.ts` | Modify | C (add weekly MA type, timeframe field) |
| `frontend/src/components/ChartGrid/ChartCell.tsx` | Modify | C (timeframe prop, MA switching) |
| `frontend/src/components/ChartGrid/ChartGrid.tsx` | Modify | C (toggle button, state) |

Total: **10 files** modified, **0 files** created.

### 4.2 Database Schema Changes

**Weekly `stock_prices` table (new DDL):**

```sql
CREATE TABLE IF NOT EXISTS stock_prices (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    Open REAL, High REAL, Low REAL, Close REAL,
    Volume REAL, VolumeSMA10 REAL,
    CHG_1W REAL, CHG_1M REAL, CHG_2M REAL, CHG_3M REAL,
    CHG_6M REAL, CHG_9M REAL, CHG_12M REAL,
    SMA10 REAL, SMA20 REAL, SMA40 REAL,
    SMA40_Trend_1M REAL, SMA40_Trend_2M REAL,
    SMA40_Trend_3M REAL, SMA40_Trend_4M REAL,
    MAX10 REAL, MAX52 REAL, min52 REAL, Close_52min REAL,
    RS_1M REAL, RS_2M REAL, RS_3M REAL,
    RS_6M REAL, RS_9M REAL, RS_12M REAL, RS_Line REAL,
    PRIMARY KEY (Name, Date)
)
```

**`stock_meta` table DDL changes:**

```sql
-- Old columns:
ma50_w REAL, ma150_w REAL, ma200_w REAL
-- New columns:
sma10_w REAL, sma20_w REAL, sma40_w REAL
```

### 4.3 API Contract

**Request:**
```
GET /api/chart/{code}?timeframe=daily   (default)
GET /api/chart/{code}?timeframe=weekly
```

**Response (daily):**
```json
{
  "timeframe": "daily",
  "candles": [...],
  "volume": [...],
  "ma": {
    "ema10": [...], "ema20": [...],
    "sma50": [...], "sma100": [...], "sma200": [...]
  }
}
```

**Response (weekly):**
```json
{
  "timeframe": "weekly",
  "candles": [...],
  "volume": [...],
  "ma": {
    "sma10": [...], "sma20": [...], "sma40": [...]
  }
}
```

### 4.4 Constraints

- Weekly DB must be regenerated after schema change (DROP + recreate, or delete the .db file and regenerate)
- stock_meta rebuild must run after weekly DB regeneration
- No migration script needed; weekly DB is regenerated from scratch via API fetches
- Weekly chart volume is raw share count (different unit from daily's VolumeWon in 100M KRW)

### 4.5 Traceability

| Requirement | Implementation Files | Test Scenario |
|-------------|---------------------|---------------|
| R1-R4 | price.py, weekly.py | AC-1, AC-2 |
| R5 | meta_service.py | AC-3 |
| R6-R9 | chart_service.py, chart.py, chart.py (schema) | AC-4, AC-5, AC-6 |
| R10-R13 | ChartCell.tsx, ChartGrid.tsx, chart.ts, chart.ts (types) | AC-7, AC-8, AC-9 |
| R14-R15 | chart.py (router), chart.py (schema) | AC-10 |
