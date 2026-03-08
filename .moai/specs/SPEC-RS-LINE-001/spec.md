# SPEC-RS-LINE-001: RS Line (Relative Strength Line) Chart Integration

## Metadata

| Field | Value |
| --- | --- |
| SPEC ID | SPEC-RS-LINE-001 |
| Title | RS Line Chart Integration |
| Created | 2026-03-08 |
| Status | Planned |
| Priority | High |
| Lifecycle | spec-first |
| Related SPECs | SPEC-WEB-001 (Chart Grid), SPEC-WEEKLY-CHART-001 |

## Environment

- **Platform:** Local-only web application (localhost)
- **Backend:** Python 3.11+, FastAPI, SQLite (daily_price.db, weekly_price.db)
- **Frontend:** React 18+, TypeScript, TradingView Lightweight Charts
- **Data:** \~2,570 KRX stocks with daily/weekly OHLCV data
- **Benchmark:** KOSPI index (daily close values)

## Assumptions

1. KOSPI daily close data can be fetched via existing `price_naver("KOSPI", ...)` function
2. Weekly RS_Line column already exists in `weekly_price.db` and is populated
3. TradingView Lightweight Charts supports multiple `priceScaleId` for independent Y-axis scaling
4. Users understand RS Line as a relative performance indicator (uptrend = outperforming market)
5. RS Line display is meaningful for both daily and weekly timeframes
6. The RS Line value (stock price / KOSPI close) has a fundamentally different scale from stock price

## Requirements

### R1: Daily RS_Line Data Pipeline

**WHEN** the daily DB update process runs (`price_daily_db()`), **THEN** the system shall fetch KOSPI daily close data and calculate RS_Line = stock Close / KOSPI Close for each stock, storing the result in the `stock_prices` table.

- R1.1: The system shall add an `RS_Line REAL` column to the daily `stock_prices` table schema.
- R1.2: **WHEN** KOSPI daily data is unavailable or fetch fails, **THEN** the system shall set RS_Line to NULL for affected dates and log a warning (not abort the entire update).
- R1.3: The system shall calculate RS_Line for all 504 days of daily data per stock (matching current daily DB depth).
- R1.4: RS_Line shall be calculated using **Close prices only** for both the stock and KOSPI index. No OHLC average, VWAP, or other price basis shall be used. Formula: `RS_Line = stock.Close / KOSPI.Close`.

### R2: Chart API RS Line Response

**WHEN** the client requests `GET /api/chart/{code}?timeframe=daily` or `timeframe=weekly`, **THEN** the system shall include RS Line data in the ChartResponse.

- R2.1: The ChartResponse schema shall include an `rs_line` field containing a list of `{time, value}` data points.
- R2.2: RS Line data points with NULL values shall be excluded from the response array.
- R2.3: **IF** no RS_Line data exists for the requested stock, **THEN** the `rs_line` field shall be an empty array (not cause an error).

### R3: Frontend RS Line Visualization (Daily and Weekly)

**WHEN** the chart receives RS Line data from the API for **either daily or weekly timeframe**, **THEN** the system shall render an RS Line overlay on the candlestick chart using IBD-style normalized display.

- R3.1: The RS Line shall be rendered as a line series using a dedicated `priceScaleId` with hidden Y-axis. This applies identically to both daily and weekly chart views.
- R3.2: The RS Line shall use a **semi-transparent** visually distinct color: `rgba(108, 92, 231, 0.5)` (purple, 50% opacity) to avoid obscuring candlestick bars and moving average lines.
- R3.3: The RS Line's price scale shall be configured with `scaleMargins` to occupy a defined vertical region of the chart area, preventing it from dominating the candlestick view.
- R3.4: The RS Line shall use `lineWidth: 2` for visual prominence and `lastValueVisible: false`.
- R3.5: The system shall **not** display the RS Line Y-axis labels (axis hidden), as the trend direction is what matters, not the absolute RS value.
- R3.6: The RS Line rendering logic shall be shared between daily and weekly chart modes, using the same `priceScaleId`, color, and opacity settings for visual consistency across timeframes.

### R4: RS Line Toggle (Optional)

**Where** the RS Line feature is enabled, **THEN** the system shall provide a toggle mechanism for users to show/hide the RS Line overlay.

- R4.1: The toggle state should persist within the session (not across browser refreshes).
- R4.2: The toggle shall not require re-fetching chart data from the API.

### R5: Unwanted Behaviors

- The system shall **not** block chart rendering if RS_Line data is missing or empty.
- The system shall **not** display RS Line values on the price Y-axis (they would be misleading at price scale).
- The system shall **not** re-compute RS_Line at API request time (DB-first approach, pre-computed only).

## Specifications

### Scaling Solution Decision: Option D - Overlay with Hidden Axis (IBD Style)

#### Options Evaluated

| Option | Approach | Pros | Cons | Verdict |
| --- | --- | --- | --- | --- |
| **A: Dual Y-Axis** | Separate right-side Y-axis for RS Line | Actual RS values visible, independent scaling | Two axes confuse users, cluttered UI | Rejected |
| **B: Normalized/Rebased** | Scale RS to match price percentage changes | Clean single axis, shows relative movement | RS display values are fake, misleading on hover | Rejected |
| **C: Separate Panel** | RS Line in own panel below price | No scaling conflicts | Takes chart real estate, loses direct comparison | Rejected |
| **D: Hidden Axis Overlay** | Separate priceScaleId with hidden axis | Clean IBD look, trend comparison, professional | Cannot read actual RS values | **Selected** |

#### Why Option D

1. **Matches IBD standard:** The reference implementation (IBD RS Line) uses exactly this approach. Users familiar with IBD charts will recognize the pattern.
2. **TradingView Lightweight Charts native support:** The library supports `priceScaleId` with `visible: false`, making implementation straightforward without data normalization hacks.
3. **Trend over value:** RS Line communicates direction (outperforming vs underperforming market). The absolute RS value (e.g., 26.9) has no intuitive meaning to users. The line's slope is what matters.
4. **Minimal chart clutter:** No second Y-axis, no panel splitting. The line overlays naturally on the chart.
5. **Data integrity:** Unlike Option B (normalization), Option D sends real RS_Line values. The chart library handles the visual scaling automatically via separate price scale.

#### Implementation Approach

```
Frontend (ChartCell.tsx):
  const rsLineSeries = chart.addLineSeries({
    color: 'rgba(108, 92, 231, 0.5)',  // Purple with 50% opacity
    lineWidth: 2,
    priceScaleId: 'rs-line',
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
  })
  chart.priceScale('rs-line').applyOptions({
    scaleMargins: { top: 0.1, bottom: 0.3 },
    visible: false,  // Hide RS Line Y-axis
  })
```

### Data Flow

```
[Daily DB Update]
  price_naver("KOSPI", daily) -> KOSPI close prices
  For each stock: RS_Line = stock Close / KOSPI Close
  INSERT INTO stock_prices (... RS_Line ...)

[Weekly DB]
  RS_Line already calculated and stored (no change needed)

[API Request]
  GET /api/chart/{code}?timeframe=daily
  -> SELECT ... RS_Line FROM stock_prices WHERE Name = ?
  -> ChartResponse { candles, volume, ma, rs_line }

[Frontend]
  ChartCell receives rs_line data
  -> addLineSeries with priceScaleId='rs-line'
  -> priceScale('rs-line').visible = false
  -> setData(rs_line)
```

### Schema Changes

**Daily DB (**`stock_prices` **table):**

```sql
ALTER TABLE stock_prices ADD COLUMN RS_Line REAL;
```

**Backend Schema (**`ChartResponse`**):**

```python
class ChartResponse(BaseModel):
    timeframe: str = "daily"
    candles: list[CandleBar]
    volume: list[VolumeBar]
    ma: MAOverlays
    rs_line: list[MAPoint] = []  # Reuse MAPoint (time + value)
```

**Frontend Type (**`ChartResponse`**):**

```typescript
export interface ChartResponse {
    timeframe: string
    candles: CandleBar[]
    volume: VolumeBar[]
    ma: MAOverlay
    rs_line: MAPoint[]  // Reuse MAPoint type
}
```

### File Impact Analysis

| File | Change | Complexity |
| --- | --- | --- |
| `my_chart/db/daily.py` | Add RS_Line column, calculate during DB gen | Medium |
| `backend/schemas/chart.py` | Add `rs_line` field to ChartResponse | Low |
| `backend/services/chart_service.py` | Query RS_Line, add to response | Low |
| `frontend/src/types/chart.ts` | Add `rs_line` to ChartResponse | Low |
| `frontend/src/components/ChartGrid/ChartCell.tsx` | Add RS Line series rendering | Medium |

### Constraints

- **Performance:** RS_Line is pre-computed in DB. No runtime computation at API request time.
- **Backward compatibility:** The `rs_line` field defaults to empty array `[]`, so existing clients without RS Line support will not break.
- **DB migration:** Use `ALTER TABLE ADD COLUMN` with fallback for existing DBs.
- **Data dependency:** RS_Line calculation depends on KOSPI data availability. KOSPI must be fetched before per-stock RS_Line calculation.

## Traceability

- **TAG:** SPEC-RS-LINE-001
- **Product Requirement:** RS-Based Screening (product.md line 49)
- **Related Data:** Weekly RS_Line already exists (price.py line 167)
- **Chart Library:** TradingView Lightweight Charts `priceScaleId` feature