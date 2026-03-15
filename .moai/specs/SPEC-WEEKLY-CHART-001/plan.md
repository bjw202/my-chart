# SPEC-WEEKLY-CHART-001: Implementation Plan

| Field       | Value                     |
|-------------|---------------------------|
| SPEC ID     | SPEC-WEEKLY-CHART-001     |
| Status      | Planned                   |
| Priority    | High                      |

---

## Milestone 1 (Primary Goal): Weekly DB Schema Rename

**Scope:** R1, R2, R3, R4

**Technical Approach:**

1. **`my_chart/price.py`** -- Update `price_naver_rs()`:
   - Rename `price["MA50"]` -> `price["SMA10"]` (rolling window stays 10)
   - Change `price["MA150"]` -> `price["SMA20"]` AND change window from 30 to 20
   - Rename `price["MA200"]` -> `price["SMA40"]` (rolling window stays 40)
   - Rename `price["Volume MA50"]` -> `price["Volume SMA10"]` (window stays 10)
   - Update MA200_Trend references to use `price["SMA40"]` and rename output columns to `SMA40_Trend(1M)` etc.
   - Update the `@MX:NOTE` comment to reflect new naming

2. **`my_chart/db/weekly.py`** -- Update column definitions:
   - `_STOCK_PRICES_COLS` tuple: MA50->SMA10, MA150->SMA20, MA200->SMA40, Volume50MA->VolumeSMA10, MA200_Trend_*->SMA40_Trend_*
   - `_PRICE_DF_COLS` tuple: Match the new DataFrame column names from price.py
   - `_ensure_stock_prices_table()` DDL: Update CREATE TABLE column names
   - Column count remains the same (32 columns); only names change

**Dependency:** None. This is the foundation for all other milestones.

**Risk:** Weekly DB must be fully regenerated after this change. The old .db file must be deleted before regeneration since column names in the schema will differ.

---

## Milestone 2 (Primary Goal): Meta Service Update

**Scope:** R5

**Technical Approach:**

1. **`backend/services/meta_service.py`**:
   - Update `_STOCK_META_DDL`: rename `ma50_w` -> `sma10_w`, `ma150_w` -> `sma20_w`, `ma200_w` -> `sma40_w`
   - Update weekly SELECT query (line 136): `MA50, MA150, MA200` -> `SMA10, SMA20, SMA40`
   - Update tuple index mapping (lines 219-221): w[3]->sma10_w, w[4]->sma20_w, w[5]->sma40_w
   - The daily DB's stock_meta table must be deleted and rebuilt (DROP TABLE stock_meta before rebuild)

**Dependency:** Milestone 1 (weekly DB must have new column names)

**Risk:** Any code that reads `ma50_w`, `ma150_w`, `ma200_w` from stock_meta will break. Grep for these column names before implementation to find all consumers.

---

## Milestone 3 (Primary Goal): Backend API Timeframe Support

**Scope:** R6, R7, R8, R9, R15

**Technical Approach:**

1. **`backend/schemas/chart.py`**:
   - Make all MA fields in `MAOverlays` optional (default `None` or empty list)
   - Add new fields: `sma10`, `sma20`, `sma40` (Optional[list[MAPoint]])
   - Add `timeframe: str` field to `ChartResponse`

2. **`backend/services/chart_service.py`**:
   - Add `get_weekly_chart_data(code: str, daily_db_path: str, weekly_db_path: str) -> ChartResponse`
   - Resolve stock name via daily DB's stock_meta (weekly DB has no stock_meta)
   - Query weekly DB: SELECT Date, Open, High, Low, Close, Volume, VolumeSMA10, SMA10, SMA20, SMA40
   - LIMIT 200 (approximately 4 years of weekly bars)
   - Build ChartResponse with weekly MA fields populated, daily MA fields as empty lists

3. **`backend/routers/chart.py`**:
   - Add `timeframe: str = Query(default="daily")` parameter
   - Validate: `if timeframe not in ("daily", "weekly"): raise HTTPException(400)`
   - Route to `get_chart_data()` or `get_weekly_chart_data()` based on timeframe
   - Import `WEEKLY_DB_PATH` from deps

**Dependency:** Milestone 1 (column names), Milestone 2 (stock_meta for name resolution)

**Risk:**
- Weekly DB may not have data for a stock that exists in daily DB (or vice versa). The weekly chart should return 404 in this case, same as daily.
- Volume units differ between daily (VolumeWon in 100M KRW) and weekly (raw share count). Document this clearly in API response.

---

## Milestone 4 (Primary Goal): Frontend Toggle UI

**Scope:** R10, R11, R12, R13, R14

**Technical Approach:**

1. **`frontend/src/api/chart.ts`**:
   - Change signature: `fetchChartData(code: string, timeframe: string = 'daily')`
   - Append `?timeframe=${timeframe}` to the API URL

2. **`frontend/src/types/chart.ts`**:
   - Add optional fields to `MAOverlay`: `sma10?`, `sma20?`, `sma40?`
   - Add `timeframe: string` to `ChartResponse`

3. **`frontend/src/components/ChartGrid/ChartGrid.tsx`**:
   - Add `timeframe` state: `useState<'daily' | 'weekly'>('daily')`
   - Add toggle button in toolbar (next to grid size toggle)
   - Pass `timeframe` as prop to each `ChartCell`

4. **`frontend/src/components/ChartGrid/ChartCell.tsx`**:
   - Accept `timeframe` prop
   - Add `timeframe` to the `useEffect` dependency array (triggers re-fetch on toggle)
   - Pass timeframe to `fetchChartData(stock.code, timeframe)`
   - Dynamically select MA color mapping based on timeframe:
     - Daily: `{ ema10, ema20, sma50, sma100, sma200 }` (current 5 colors)
     - Weekly: `{ sma10, sma20, sma40 }` (3 colors, green/blue/dark)
   - Set visible range: daily=200 candles, weekly=52 candles

**Dependency:** Milestone 3 (backend API ready)

**Risk:**
- Toggling timeframe destroys and recreates all chart instances (potential flicker). Mitigate with loading spinner overlay.
- Memory management: ensure `chart.remove()` cleanup runs before re-creation.

---

## Milestone 5 (Secondary Goal): Integration Verification

**Scope:** Cross-cutting

**Tasks:**
1. Delete existing weekly .db file and regenerate with new schema
2. Rebuild stock_meta after weekly DB regeneration
3. Verify daily chart endpoint still works identically (backward compatibility)
4. Test weekly chart for a sample of stocks (e.g., Samsung Electronics)
5. Verify the frontend toggle works across 2x2 and 3x3 grid modes
6. Verify MA series render correctly for both timeframes
7. Grep codebase for any remaining references to old column names (MA50, MA150, MA200 in weekly context)

---

## Architecture Design Direction

### Unified Schema vs Separate Schema

**Decision: Unified schema with optional fields**

The `MAOverlays` Pydantic model uses optional fields for all MA series. This avoids creating separate `DailyMAOverlays` / `WeeklyMAOverlays` classes and keeps the API contract simple. The `timeframe` field in `ChartResponse` tells the client which fields are populated.

### Volume Unit Handling

The weekly volume is raw share count (stored as-is from Naver API). The daily volume is converted to VolumeWon (100M KRW). The frontend should handle display formatting based on the timeframe value.

### stock_meta Column Impact

The stock_meta columns `sma10_w`, `sma20_w`, `sma40_w` are used by the screening/filter system. Any filter presets or saved queries that reference the old column names need to be updated. Check the frontend filter components.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Old weekly .db not deleted before regeneration | Medium | High (schema mismatch) | Document the DB deletion step clearly |
| MA150->SMA20 window change (30->20) alters screening results | High (intentional) | Medium | Accepted design decision; notify user |
| Frontend flicker on timeframe toggle | Medium | Low (cosmetic) | Loading spinner overlay during re-fetch |
| Weekly data missing for some stocks | Low | Low | Return 404, same as daily behavior |
| Remaining references to old column names | Medium | Medium | Grep verification in Milestone 5 |
