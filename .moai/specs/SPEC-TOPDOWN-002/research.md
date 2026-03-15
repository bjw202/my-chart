# Research: SPEC-TOPDOWN-002 Advanced Sector Visualization & Analytics

## Codebase Analysis Summary

### Current Technology Stack

- **Backend**: FastAPI 0.115+ / Python 3.13 / SQLite (WAL) / Pandas
- **Frontend**: React 19 / TypeScript 5.9 / Vite 7.3 / Lightweight Charts 4.2
- **Data**: \~2,571 KOSPI/KOSDAQ stocks, weekly + daily data
- **State Management**: React Context API (MarketContext, TabContext, ScreenContext, NavigationContext, WatchlistContext)
- **Virtualization**: react-window 1.8.10
- **Tests**: pytest (374 tests), Vitest + React Testing Library

### Phase 1 Status (SPEC-TOPDOWN-001)

**Implemented:**

- Backend data engine: market_breadth.py, stage_classifier.py, sector_metrics.py
- 3 API endpoints: /api/market/overview, /api/sectors/ranking, /api/stage/overview
- 4-tab navigation: Market Overview, Sector Analysis, Stock Explorer, Chart Grid
- Market Overview: MarketPhaseCard, BreadthChart, MiniHeatmap, WeeklyHighlights
- Sector Analysis: SectorRankingTable, SectorDetailPanel (partial)
- Stock Explorer: StageDistributionBar, StockTable
- Cross-tab navigation framework (TabContext + crossTabParams)

**Remaining (spec-remaining.md):**

- R1-R3 (High): Chart Grid stockCodes reception, Stage badge, Sector Detail sub-sector
- R4-R7 (Medium): Sparkline, Key Checklist, Market Filter, Stage 2 count
- R8-R9 (Low): Performance verification, test coverage

### Existing Data Availability for Phase 2

| Required Data | Available | Source | Notes |
| --- | --- | --- | --- |
| Sector price index | Computable | stock_prices + stock_meta (market_cap weighted) | Need new computation |
| Trading value (거래대금) | Computable | Close \* Volume from stock_prices | Aggregation needed |
| RS-Ratio for RRG | Computable | Sector price index / KOSPI index ratio | New module |
| RS-Momentum for RRG | Computable | Rate of change of RS-Ratio | New module |
| Sector ranking history | Partially available | sector_metrics.py computes current only | Need history storage |
| 12-week sector returns | Computable | CHG_1W\~12M in stock_prices | Weighted avg needed |
| Market cap per stock | Available | stock_meta.market_cap | Ready |
| Sector mapping | Available | sectormap.xlsx via registry.py | \~20-25 major, \~80-100 minor |

**Conclusion**: All Phase 2 features implementable with existing data. No external data sources required.

---

## Charting Library Research

### Current Charting: Lightweight Charts 4.2

- Handles: Candlestick, Line, Histogram (volume), Area
- Does NOT support: Scatter/Bubble, Treemap, Custom multi-quadrant, Bump chart
- Should be RETAINED for existing candlestick/line charts

### Phase 2 Requirements

| Feature | Chart Type Needed | Lightweight Charts? |
| --- | --- | --- |
| RRG (002B) | Scatter with trail animation | No |
| Treemap (002C) | Hierarchical rectangle layout | No |
| Bump Chart (002D) | Ranked line chart | No |
| Bubble Chart (002F) | Sized scatter plot | No |

### Library Evaluation

| Library | Bundle (min+gzip) | React | Bubble | Treemap | Custom (RRG) | Performance |
| --- | --- | --- | --- | --- | --- | --- |
| **ECharts** | \~300KB (tree-shake \~100KB) | Wrapper | Yes | Yes | Yes (custom series) | Canvas/WebGL |
| **Recharts** | \~45KB | Native | Yes | No | No | SVG |
| **Nivo** | \~40KB/module | Native | Yes | Yes | Limited | SVG/Canvas |
| **Highcharts** | \~80KB | Wrapper | Yes | Yes | Yes | SVG/Canvas |
| **D3.js** | \~200KB (tree-shake) | Manual | Yes | Yes | Yes | SVG |
| **Visx** | \~20KB/module | Native | Build own | Build own | Build own | SVG |

### Recommendation: ECharts (echarts-for-react)

**Rationale:**

1. Supports ALL required chart types natively (scatter/bubble, treemap, custom for RRG)
2. Canvas/WebGL rendering for 2,500+ data points (crucial for stock-level bubble charts)
3. Built-in `visualMap` for automatic color gradient mapping (price change → green/red)
4. Rich interaction: tooltips, zoom, brush selection, drill-down events
5. Tree-shakeable to reduce bundle impact
6. Active maintenance, extensive documentation
7. Can coexist with Lightweight Charts (different chart types)

**Trade-offs:**

- Wrapper-based React integration (not native JSX)
- Larger bundle than Recharts
- Chinese-origin docs (English available but sometimes lagging)

**Alternative Consideration: Recharts for Bubble Chart only**

- If only Bubble Chart is needed immediately, Recharts is lighter (\~45KB)
- However, RRG and Treemap would still need another library
- Using ECharts for all Phase 2 charts avoids multiple library dependencies

**Decision**: Install `echarts` + `echarts-for-react` for all Phase 2 visualization features.

---

## Bubble Chart Design Research

### Industry Examples

**Finviz Bubbles (finviz.com/bubbles.ashx):**

- Sector grouping with nested stock bubbles
- Bubble size = market cap
- Color = price change % (green/red gradient)
- Click to drill down from sector to stocks

**TradingView Heatmap:**

- Treemap layout with sector → stock hierarchy
- Size = market cap
- Color = price change % intensity

**Bloomberg Scatter:**

- X = metric A, Y = metric B, Size = metric C
- Interactive tooltips, zoom, filtering

### Recommended Bubble Chart Design

**Level 1: Sector Bubble View**

- X-axis: Excess return vs KOSPI (selected period: 1W/1M/3M)
- Y-axis: Sector RS average score (0-100)
- Bubble size: Sector total trading value (sum of Close × Volume)
- Bubble color: Green gradient (positive return) → Red gradient (negative return)
- Label: Sector name inside bubble
- Quadrant lines: X=0% (market return), Y=50 (median RS)

**Level 2: Stock Bubble View (drill-down from sector)**

- X-axis: Stock price change % (selected period)
- Y-axis: RS_12M rating (0-100)
- Bubble size: Individual stock trading value
- Bubble color: By Weinstein Stage (S1=yellow, S2=green, S3=orange, S4=red)
- Label: Stock name (top N by trading value)
- Filter: Pre-filtered to selected sector

**Interaction Patterns:**

1. Hover: Rich tooltip with name, exact values, stock count (sector level)
2. Click sector bubble → Drill down to stock-level view
3. Click stock bubble → Navigate to Chart Grid
4. Period toggle: 1W/1M/3M recalculates positions
5. Zoom/pan for dense areas
6. Legend: Size reference + color scale

### Data Mapping Strategy

**Trading Value (거래대금) Calculation:**

```python
# Per stock
trading_value = close_price * volume  # 주간 거래대금

# Per sector (market-cap weighted aggregation)
sector_trading_value = sum(stock.close * stock.volume for stock in sector_stocks)
```

**Color Encoding:**

- Diverging scale: green(+5%+) → light green(+1\~5%) → gray(0±1%) → light red(-1\~5%) → red(-5%-)
- 0.7 opacity for overlap handling
- Consider blue/orange alternative for accessibility

---

## RRG (Relative Rotation Graph) Research

### Concept

RRG plots sectors in a 4-quadrant space:

- X-axis: RS-Ratio (relative strength vs benchmark, normalized to 100)
- Y-axis: RS-Momentum (rate of change of RS-Ratio, normalized to 100)
- Trail: 8-week history showing rotation direction

### Quadrants

| Quadrant | X | Y | Meaning |
| --- | --- | --- | --- |
| Leading (top-right) | &gt;100 | &gt;100 | Strong and improving |
| Weakening (bottom-right) | &gt;100 | &lt;100 | Strong but losing momentum |
| Lagging (bottom-left) | &lt;100 | &lt;100 | Weak and deteriorating |
| Improving (top-left) | &lt;100 | &gt;100 | Weak but gaining momentum |

### Computation

```python
# 1. Compute sector price index (market-cap weighted)
sector_index = sum(stock.close * stock.market_cap) / sum(stock.market_cap)

# 2. Compute RS-Ratio (sector vs KOSPI)
rs_ratio_raw = sector_index / kospi_index * 100

# 3. Normalize RS-Ratio using JdK RS-Ratio formula
# Rolling z-score normalization over lookback period
rs_ratio = normalize(rs_ratio_raw, lookback=12)  # 12 weeks

# 4. Compute RS-Momentum (rate of change of RS-Ratio)
rs_momentum = rs_ratio - rs_ratio_prev_week  # or normalized rate of change
```

### Implementation Notes

- Trail animation: Array of 8 (x,y) coordinates per sector, connected by line
- Tail fading: Older points more transparent
- Interactive: Click trail head to see sector details
- Live sector labels at trail head position

---

## Treemap Heatmap Research

### Finviz-Style Design

- Hierarchical: Sector → Sub-sector → Individual Stock
- Rectangle size: Market capitalization
- Color: Price change % (green/red gradient)
- Text: Stock name + ticker + change %
- Interaction: Click to drill down, breadcrumb navigation

### ECharts Treemap Features

- Built-in hierarchical data support
- `visualMap` for automatic color mapping
- Drill-down with breadcrumb navigation
- Label overflow handling
- Tooltip on hover
- Performance-optimized canvas rendering

### Data Structure for ECharts Treemap

```json
{
  "name": "KRX",
  "children": [
    {
      "name": "반도체",
      "children": [
        { "name": "삼성전자", "value": 400000000000, "chg": 2.1 },
        { "name": "SK하이닉스", "value": 100000000000, "chg": -0.5 }
      ]
    }
  ]
}
```

Where `value` = market_cap and `chg` drives color mapping.

---

## Bump Chart Research

### Concept

Shows sector rank changes over time:

- X-axis: Time (12 weeks)
- Y-axis: Rank position (1 = top, inverted scale)
- Each line = one sector
- Line color: by current quadrant or return

### Implementation with ECharts

- Use line series with rank-based y-values
- Custom y-axis (inverted, integer ticks)
- Sector labels at line endpoints
- Hover to highlight single sector's path
- Click to see sector details at specific week

---

## Performance Considerations

### Data Volume

- \~20-25 sectors for sector-level views (low complexity)
- \~2,571 stocks for stock-level drill-down (needs optimization)
- 12 weeks of history for trails/bump chart

### Optimization Strategies

1. **Sector-level charts**: No optimization needed (20-25 data points)
2. **Stock-level bubble chart**: Filter by sector (50-200 stocks per sector), canvas rendering
3. **Treemap with all stocks**: ECharts canvas handles 2,500+ rectangles well
4. **RRG trails**: 20 sectors × 8 weeks = 160 data points (trivial)
5. **Data pre-computation**: Compute sector indices, RS-Ratio, RS-Momentum on backend
6. **Caching**: 1-hour TTL for all sector analytics (data changes weekly)

---

## Tab Placement Strategy

### Current Tab Structure

```
[Market Overview] [Sector Analysis] [Stock Explorer] [Chart Grid]
```

### Recommended Phase 2 Placement

**Market Overview tab additions:**

- Full-size Treemap Heatmap (002C) — replaces/supplements MiniHeatmap
- Toggle between: \[Mini Heatmap\] \[Full Treemap\]

**Sector Analysis tab additions:**

- Sub-navigation: \[Ranking Table\] \[Bubble Chart\] \[RRG\] \[Bump Chart\]
- These are all sector-level analysis views, logically grouped
- Share the same data context (sector metrics)

**No new top-level tabs needed** — keeps UI clean and focused.

---

## API Design for Phase 2

### New Endpoints Needed

```
GET /api/sectors/bubble?period=1w
→ Sector-level bubble chart data (excess return, RS avg, trading value)

GET /api/sectors/{name}/bubble?period=1w
→ Stock-level bubble chart data for a specific sector

GET /api/sectors/rrg
→ RRG data (RS-Ratio, RS-Momentum, 8-week trail per sector)

GET /api/sectors/history?weeks=12
→ Sector ranking history for bump chart

GET /api/market/treemap
→ Hierarchical market cap + return data for treemap
```

### Backend Modules

**New module**: `my_chart/analysis/sector_advanced.py`

- `compute_sector_price_index(db_path, sector_name, weeks=12) -> list[float]`
- `compute_rrg_data(db_path, date) -> list[RRGPoint]`
- `compute_sector_bubble(db_path, period, market=None) -> list[SectorBubble]`
- `compute_stock_bubble(db_path, sector_name, period) -> list[StockBubble]`
- `compute_sector_history(db_path, weeks=12) -> list[SectorWeekRank]`
- `compute_treemap_data(db_path, date) -> TreemapNode`

**Extend existing**: `my_chart/analysis/sector_metrics.py`

- Add `trading_value` computation to sector aggregation
- Add `market` filter parameter (aligns with Phase 1 remaining R6)

---

## Document Version

- **Version**: 1.0
- **Created**: 2026-03-15
- **Parent SPEC**: SPEC-TOPDOWN-001
- **Author**: MoAI Research Agent