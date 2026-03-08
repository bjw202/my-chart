# SPEC-RS-LINE-001 Research: RS Line Chart Integration

## Codebase Exploration Results

### 1. RS_Line in Weekly DB (EXISTS)

**File:** `my_chart/price.py` (lines 133-169)
- `price_naver_rs()` function calculates RS_Line for weekly data
- Formula: `RS_Line = stock Close / KOSPI Close` (line 167)
- KOSPI data fetched via `price_naver("KOSPI", ...)` and stored as benchmark
- Weekly `stock_prices` table has `RS_Line (REAL)` column

### 2. RS_Line in Daily DB (DOES NOT EXIST)

**File:** `my_chart/db/daily.py` (lines 52-79)
- Daily `stock_prices` table schema:
  ```
  Name, Date, Open, High, Low, Close, Change, High52W,
  Volume, Volume20MA, VolumeWon,
  EMA10, EMA20, SMA21, SMA50, EMA65, SMA100, SMA200,
  DailyRange, HLC, FromEMA10, FromEMA20, FromSMA50, FromSMA200,
  Range, ADR20
  ```
- NO RS_Line column
- KOSPI daily data is NOT currently fetched for daily DB

### 3. Chart API Layer

**File:** `backend/routers/chart.py`
- `GET /api/chart/{code}?timeframe=daily|weekly`
- Returns `ChartResponse` with candles, volume, ma (MAOverlays)
- NO RS_Line data in current response

**File:** `backend/services/chart_service.py`
- `get_chart_data()` — daily: 504 days, queries EMA10/20, SMA50/100/200
- `get_weekly_chart_data()` — weekly: 200 weeks, queries SMA10/20/40
- Neither function queries or returns RS_Line

**File:** `backend/schemas/chart.py`
- `ChartResponse`: timeframe, candles, volume, ma (MAOverlays)
- `MAOverlays`: ema10/20, sma50/100/200, sma10/20/40
- No RS Line types defined

### 4. Frontend Chart Rendering

**File:** `frontend/src/components/ChartGrid/ChartCell.tsx`
- Uses TradingView Lightweight Charts (`lightweight-charts` npm package)
- `createChart()` with dark theme (#1a1a2e)
- Candlestick series + volume histogram + MA line series
- Volume uses separate `priceScaleId: 'volume'` with margins {top: 0.85, bottom: 0}
- MA series use default price scale (same axis as candlesticks)
- Already has RS score display in header: `RS {rsDisplay}` (from stock list data, NOT chart overlay)

**File:** `frontend/src/types/chart.ts`
- Mirrors backend Pydantic schemas
- `ChartResponse`: timeframe, candles, volume, ma

### 5. Price Fetching Infrastructure

**File:** `my_chart/price.py`
- `price_naver("KOSPI", ...)` already works for fetching KOSPI daily/weekly OHLCV
- `price_naver_rs()` (weekly version) already calculates RS_Line = Close / benchmark Close
- Daily equivalent does NOT exist yet

### 6. TradingView Lightweight Charts Capabilities

- Supports multiple `priceScaleId` values for separate Y-axes
- `addLineSeries()` can take `priceScaleId` parameter for secondary axis
- `priceScale(id).applyOptions()` allows margin/position configuration
- Line series can use `priceFormat: { type: 'custom', formatter: ... }`

## Key Files Impact Map

| File | Change Type | Description |
|------|-------------|-------------|
| `my_chart/db/daily.py` | MODIFY | Add RS_Line column to stock_prices schema |
| `my_chart/db/daily.py` | MODIFY | Calculate RS_Line during daily DB generation |
| `my_chart/price.py` | MINOR | May need daily RS_Line calculation helper |
| `backend/schemas/chart.py` | MODIFY | Add RS Line data types to ChartResponse |
| `backend/services/chart_service.py` | MODIFY | Query RS_Line from DB, include in response |
| `backend/routers/chart.py` | NO CHANGE | Router delegates to service, no changes needed |
| `frontend/src/types/chart.ts` | MODIFY | Add RS Line types |
| `frontend/src/components/ChartGrid/ChartCell.tsx` | MODIFY | Add RS Line series rendering |

## Scaling Problem Analysis

The core challenge: RS_Line value = Stock Price / KOSPI Index

Example with Samsung Electronics (005930):
- Stock price: ~70,000 KRW
- KOSPI index: ~2,600
- RS_Line value: ~26.9 (70,000 / 2,600)

On same chart axis, RS_Line (26.9) would be invisible relative to price (70,000).

### IBD Reference Implementation

IBD (Investor's Business Daily) displays RS Line as:
- A single blue/purple line overlaid on the candlestick chart
- No visible second Y-axis
- The line shows TREND direction (up = outperforming market, down = underperforming)
- Actual RS values are not readable from the chart
- Uses normalized/rebased approach to fit within price chart area

### TradingView Lightweight Charts Technical Options

1. **Separate priceScaleId** (built-in support):
   ```typescript
   chart.addLineSeries({
     priceScaleId: 'rs-line',
     // ...
   })
   chart.priceScale('rs-line').applyOptions({
     scaleMargins: { top: 0.1, bottom: 0.3 },
     visible: false, // hide the axis
   })
   ```

2. **Normalized overlay** (pre-process data):
   ```typescript
   // RS_display[i] = price_first * (RS[i] / RS_first)
   const rsFirst = rsData[0].value
   const priceFirst = candles[0].close
   const normalizedRS = rsData.map(d => ({
     time: d.time,
     value: priceFirst * (d.value / rsFirst),
   }))
   ```

3. **Separate panel** (not easily supported by Lightweight Charts without second chart instance)
