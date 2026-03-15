# Research: Top-Down Market Analysis Feature

## Codebase Analysis Summary

### Technology Stack

- **Backend**: FastAPI 0.115+ / Python 3.13 / SQLite (WAL) / Pandas
- **Frontend**: React 19 / TypeScript 5.9 / Vite 7.3 / Lightweight Charts 4.2
- **Data**: \~2,571 KOSPI/KOSDAQ stocks, weekly + daily data
- **Tests**: pytest (374 tests), 85% coverage target (TDD mode)

### Database Schema (Current)

**stock_prices** (weekly):

- OHLCV, SMA10/20/40, CHG_1W\~12M, RS_1M\~12M, RS_Line
- MAX10, MAX52, min52, VolumeSMA10

**stock_prices** (daily):

- OHLCV, EMA10/20/65, SMA21/50/100/200
- FromEMA10/20, FromSMA50/200, ADR20, RS_Line

**stock_meta** (screening snapshot):

- code, name, market, market_cap, sector_major/minor
- close, ema10/20, sma50/100/200, high52w
- chg_1w/1m/3m, rs_12m

**relative_strength**:

- RS_12M/6M/3M/1M_Rating (0-100 percentile)

### Sector Mapping (sectormap.xlsx)

- \~20-25 major sectors (산업명(대)): 반도체, Auto, 배터리, 헬스케어, etc.
- \~80-100 minor sectors (산업명(중)): 메모리반도체, 완성차, etc.
- Loaded via registry.py, cached as singleton DataFrame

### Key Findings

1. **SMA50/SMA200**: Daily DB has SMA50/100/200. Weekly DB only has SMA10/20/40.

   - Weekly SMA40 ≈ 200-day SMA (40 weeks × 5 days). Can be used as proxy.
   - Need to add SMA50 (weekly 10-week = \~50 days) to weekly DB for Stage analysis.

2. **KOSPI Index**: Stored in stock_prices table as Name='KOSPI'. Both daily and weekly.

3. **RS Rating**: Already computed (0-100 percentile). RS_12M_Rating available in relative_strength.

4. **52-Week High/Low**: MAX52, min52 already in stock_prices.

5. **Volume**: Volume + VolumeSMA10 available in weekly. Volume20MA in daily.

6. **Market Cap**: Available via pykrx API call during meta rebuild. Stored in stock_meta.

7. **Sector Service**: Basic sector_service.py exists (returns unique sector_major values).

### Data Availability Assessment

| Required Data | Available | Notes |
| --- | --- | --- |
| KOSPI vs SMA50/200 | Yes (daily) | Daily DB has SMA50/200 for KOSPI |
| SMA slope | Yes | Computed from SMA time series |
| % &gt; SMA50 | Computable | Count stocks where Close &gt; SMA50 |
| % &gt; SMA200 | Computable | Count stocks where Close &gt; SMA200 (daily) |
| NH-NL ratio | Yes | MAX52, min52 in stock_prices |
| AD Line | Computable | From weekly CHG_1W sign |
| Breadth Composite | Computable | Weighted sum of above |
| Stage Classification | Computable | Close, SMA, RS Rating all available |
| Sector price index | Computable | Market-cap weighted avg of sector stocks |
| RRG (RS-Ratio, RS-Momentum) | Computable | From sector price index + KOSPI |
| Volume Ratio | Yes | Volume / VolumeSMA10 |
| Sector trading value | Partial | Volume available, need to aggregate |

**Conclusion**: 80%+ of research-proposed features implementable with existing data. No external data required for MVP.

### Frontend Architecture Notes

- Current layout: FilterBar (top) + StockList (left sidebar) + ChartGrid (main)
- State management: React Context API (ScreenContext, NavigationContext, WatchlistContext)
- No router (single-page, no tabs)
- Need to add: Tab navigation, new contexts for market/sector analysis
- Charting: Lightweight Charts handles candlestick/line/histogram well
- For RRG/heatmap: Need additional charting (canvas-based or D3.js)

### API Extension Points

Current pattern: `backend/routers/*.py` → `backend/services/*.py` → `my_chart/db/*.py`

New endpoints needed:

- `/api/market/breadth` - Market breadth indicators
- `/api/market/cycle` - Market cycle determination
- `/api/sector/ranking` - Sector strength ranking
- `/api/sector/rrg` - RRG data (Phase 2)
- `/api/stage/classify` - Stage classification for all stocks
- `/api/stage/screen` - Stage 2 entry candidates