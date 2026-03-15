# SPEC-TOPDOWN-002: Advanced Sector Visualization & Analytics

## Overview

- **Feature**: Phase 2 of Top-Down Market Analysis — Advanced sector visualizations including Bubble Chart, RRG, Treemap Heatmap, Bump Chart, and Early Detection Alerts
- **Branch**: feature/sector-rotation
- **Methodology**: TDD (RED-GREEN-REFACTOR)
- **Scope**: Full-stack (Backend computation + Frontend visualization)
- **Parent SPEC**: SPEC-TOPDOWN-001
- **Prerequisites**: SPEC-TOPDOWN-001 Phase 1 remaining items R1-R3 (High priority) should be completed first

---

## Implementation Roadmap

| SPEC | Name | Scope | Dependency | Priority |
|------|------|-------|------------|----------|
| SPEC-TOPDOWN-002A | Backend - Sector Advanced Metrics Engine | Backend only | None | P0 (Foundation) |
| SPEC-TOPDOWN-002F | Sector/Stock Bubble Chart | Frontend + API | 002A | P1 (User Priority) |
| SPEC-TOPDOWN-002C | Full-size Treemap Heatmap | Frontend + API | 002A | P1 |
| SPEC-TOPDOWN-002B | RRG (Relative Rotation Graph) | Frontend + API | 002A | P2 |
| SPEC-TOPDOWN-002D | Sector Rank Bump Chart | Frontend + API | 002A | P2 |
| SPEC-TOPDOWN-002E | Leading Sector Early Detection Alerts | Backend + Frontend | 002A | P3 |

### Dependency Graph

```
SPEC-TOPDOWN-002A (Backend Foundation)
├── 002F (Bubble Chart)      ← User priority
├── 002C (Treemap Heatmap)   ← Can parallel with 002F
├── 002B (RRG)               ← Can parallel with 002D
├── 002D (Bump Chart)        ← Can parallel with 002B
└── 002E (Early Detection)   ← After 002B/002D
```

### Charting Library Decision

**Install**: `echarts` + `echarts-for-react`

ECharts is selected for all Phase 2 visualizations because:
1. Supports ALL required chart types (scatter/bubble, treemap, custom series for RRG trails)
2. Canvas/WebGL rendering handles 2,500+ data points efficiently
3. Built-in `visualMap` for automatic color gradient mapping
4. Rich interactivity (tooltip, zoom, drill-down, brush)
5. Coexists with existing Lightweight Charts (candlestick/line charts remain unchanged)

---

## SPEC-TOPDOWN-002A: Backend - Sector Advanced Metrics Engine

### Purpose

Sector price index, trading value aggregation, RRG metrics, ranking history computation engine.

### Requirements (EARS Format)

**R1: Sector Price Index**

- WHEN the system computes a sector's price index,
- THE system SHALL calculate a market-cap weighted average price:
  - `sector_price_index = sum(stock.close * stock.market_cap) / sum(stock.market_cap)`
- AND compute this for the most recent 12 weeks to produce a time series
- WHERE stocks are grouped by `sector_major` from sectormap

**R2: Sector Trading Value**

- WHEN the system computes sector trading value (거래대금),
- THE system SHALL calculate:
  - Per stock: `trading_value = close * volume`
  - Per sector: `sector_trading_value = sum(trading_value for all stocks in sector)`
- AND provide both current week and historical values

**R3: RRG Metrics (RS-Ratio & RS-Momentum)**

- WHEN the system computes RRG data for sectors,
- THE system SHALL calculate for each sector:
  - `rs_ratio_raw = sector_price_index / kospi_index * 100`
  - `rs_ratio = normalize(rs_ratio_raw, lookback=12)` (rolling z-score, centered at 100)
  - `rs_momentum = normalize(rate_of_change(rs_ratio), lookback=12)` (centered at 100)
- AND provide 8-week trail data (8 consecutive [rs_ratio, rs_momentum] pairs per sector)

**R4: Sector Ranking History**

- WHEN the system retrieves sector ranking history,
- THE system SHALL return the composite rank of each sector for the most recent N weeks (default 12)
- WHERE the ranking is computed using the same composite formula from SPEC-TOPDOWN-001A R8

**R5: Treemap Data Hierarchy**

- WHEN the system constructs treemap data,
- THE system SHALL return a hierarchical structure:
  - Level 1: Market (KOSPI / KOSDAQ)
  - Level 2: Sector (산업명(대))
  - Level 3: Individual stocks
- WHERE each stock node includes: name, code, market_cap (for rectangle size), price change % (for color)
- AND sector nodes include: aggregated market_cap, weighted return

### API Endpoints

```
GET /api/sectors/bubble?period=1w&market=all
Response: {
  period: "1w" | "1m" | "3m",
  sectors: [
    {
      name: string,
      stock_count: int,
      excess_return: float,
      rs_avg: float,
      trading_value: float,
      return_1w: float,
      return_1m: float,
      return_3m: float
    }
  ]
}

GET /api/sectors/{sector_name}/bubble?period=1w
Response: {
  sector_name: string,
  period: "1w" | "1m" | "3m",
  stocks: [
    {
      code: string,
      name: string,
      price_change: float,
      rs_12m: float,
      trading_value: float,
      stage: string,
      stage_detail: string,
      market_cap: float,
      volume_ratio: float
    }
  ]
}

GET /api/sectors/rrg
Response: {
  date: string,
  benchmark: "KOSPI",
  sectors: [
    {
      name: string,
      rs_ratio: float,
      rs_momentum: float,
      quadrant: "leading" | "weakening" | "lagging" | "improving",
      trail: [
        { week: string, rs_ratio: float, rs_momentum: float }
      ]  // 8 weeks, oldest to newest
    }
  ]
}

GET /api/sectors/history?weeks=12
Response: {
  weeks: [
    {
      date: string,
      rankings: [
        { name: string, rank: int, composite_score: float }
      ]
    }
  ]
}

GET /api/market/treemap?period=1w
Response: {
  name: "KRX",
  period: "1w" | "1m" | "3m",
  children: [
    {
      name: string,           // sector name
      market_cap: float,      // aggregated
      weighted_return: float,  // for sector color
      children: [
        {
          name: string,        // stock name
          code: string,
          market_cap: float,   // for rectangle size
          price_change: float, // for color
          rs_12m: float,
          stage: string
        }
      ]
    }
  ]
}
```

### Data Layer Changes

**New module**: `my_chart/analysis/sector_advanced.py`

- `compute_sector_price_index(db_path, sector_name, weeks=12) -> list[dict]`
- `compute_rrg_data(db_path, date) -> list[RRGSector]`
- `compute_sector_bubble(db_path, period="1w", market=None) -> list[SectorBubble]`
- `compute_stock_bubble(db_path, sector_name, period="1w") -> list[StockBubble]`
- `compute_sector_history(db_path, weeks=12) -> list[WeekRanking]`
- `compute_treemap_data(db_path, period="1w") -> TreemapNode`

**Extend existing**: `my_chart/analysis/sector_metrics.py`

- Add `trading_value` to sector aggregation output
- Add `market` filter parameter (also satisfies Phase 1 remaining R6)

### Acceptance Criteria

- [ ] AC1: `compute_sector_price_index()` returns market-cap weighted index for 12 weeks
- [ ] AC2: `compute_rrg_data()` returns normalized RS-Ratio and RS-Momentum centered at 100
- [ ] AC3: RRG quadrant assignment is correct (leading: >100/>100, lagging: <100/<100, etc.)
- [ ] AC4: `compute_sector_bubble()` returns trading value aggregated per sector
- [ ] AC5: `compute_stock_bubble()` returns individual stock metrics filtered by sector
- [ ] AC6: `compute_sector_history()` returns 12 weeks of rank data per sector
- [ ] AC7: `compute_treemap_data()` returns correct hierarchy (market → sector → stock)
- [ ] AC8: All API endpoints return valid JSON matching schema
- [ ] AC9: API response time < 500ms for each endpoint
- [ ] AC10: 85%+ test coverage for `sector_advanced.py`

---

## SPEC-TOPDOWN-002F: Sector/Stock Bubble Chart

### Purpose

Trading value (거래대금) vs excess return visualization with sector-level overview and stock-level drill-down.

### Requirements (EARS Format)

**R1: Sector Bubble Chart (Default View)**

- WHEN the Sector Analysis tab displays the Bubble Chart view,
- THE system SHALL display a scatter/bubble chart where:
  - X-axis: Sector excess return vs KOSPI (selected period)
  - Y-axis: Sector RS average score (0-100)
  - Bubble size: Sector total trading value (거래대금)
  - Bubble color: Green gradient (positive return) to Red gradient (negative return)
  - Bubble label: Sector name (displayed inside or adjacent to bubble)
- AND quadrant reference lines at X=0% and Y=50 SHALL be displayed
- AND a size legend showing trading value scale SHALL be visible

**R2: Bubble Chart Period Toggle**

- WHEN the user selects a different period (1W / 1M / 3M),
- THE system SHALL recalculate:
  - X-axis positions using the selected period's excess return
  - Bubble colors based on the selected period's return
- AND animate the transition smoothly

**R3: Stock-Level Drill-Down**

- WHEN the user clicks a sector bubble,
- THE system SHALL transition to a stock-level bubble chart showing:
  - X-axis: Stock price change % (selected period)
  - Y-axis: RS_12M rating (0-100)
  - Bubble size: Individual stock trading value (거래대금)
  - Bubble color: By Weinstein Stage (S1=yellow, S2=green, S3=orange, S4=red)
  - Labels: Stock names for top N stocks by trading value
- AND a "Back to Sector View" button SHALL be displayed
- AND the sector name SHALL be shown as the chart title

**R4: Bubble Chart Interactions**

- WHEN the user hovers over a bubble,
- THE system SHALL display a tooltip with:
  - Sector level: Sector name, exact excess return %, RS avg, trading value (formatted in 억원), stock count
  - Stock level: Stock name, code, exact price change %, RS rating, trading value (formatted in 억원), stage
- WHEN the user clicks a stock-level bubble,
- THE system SHALL navigate to the Chart Grid tab with that stock loaded

**R5: Bubble Chart Market Filter**

- WHEN the user toggles market filter (ALL / KOSPI / KOSDAQ),
- THE system SHALL recalculate bubble data using only the selected market's stocks

### Frontend Components

**New files:**

- `frontend/src/components/SectorAnalysis/BubbleChart.tsx` (main container with view toggle)
- `frontend/src/components/SectorAnalysis/SectorBubbleChart.tsx` (sector-level ECharts)
- `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` (stock-level ECharts)
- `frontend/src/api/bubble.ts` (API client for bubble data)
- `frontend/src/types/bubble.ts` (type definitions)

**Modified files:**

- `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx` (add sub-navigation for Bubble Chart view)

### Visual Design

**Sector Bubble Chart:**
```
┌─ Bubble Chart ──────────────────────────────────────────┐
│  Period: [1W] [1M] [3M]   Market: [ALL] [KOSPI] [KOSDAQ]│
│                                                          │
│         ↑ RS Average (0-100)                             │
│    90   │                                                │
│         │            ●반도체                             │
│    70   │     ○IT      (bubble size = 거래대금)          │
│         │                                                │
│    50   │──────────●자동차────────────────               │
│         │   ○금융                                        │
│    30   │              ○화학                              │
│         │                                                │
│    10   │                                                │
│         └──────────────────────────────────→             │
│         -5%    -2%    0%    +2%    +5%                   │
│                  Excess Return vs KOSPI                   │
│                                                          │
│  ● Size legend: ○ 100억  ● 500억  ● 1000억             │
│  Color: 🟢 positive return → 🔴 negative return         │
└──────────────────────────────────────────────────────────┘
```

**Stock Bubble Chart (drill-down):**
```
┌─ 반도체 Stocks ─────────────────────────────────────────┐
│  ← Back to Sectors   Period: [1W] [1M] [3M]             │
│                                                          │
│         ↑ RS Rating (0-100)                              │
│    90   │     ●삼성전자                                  │
│         │         ○SK하이닉스                            │
│    70   │   ○DB하이텍                                    │
│         │              ●한미반도체                        │
│    50   │────────────────────────────                    │
│         │   ○솔브레인                                    │
│    30   │         ○리노공업                              │
│         └──────────────────────────────────→             │
│         -10%   -5%    0%    +5%    +10%                  │
│                  Price Change                            │
│                                                          │
│  Color: 🟡S1  🟢S2  🟠S3  🔴S4                         │
└──────────────────────────────────────────────────────────┘
```

### Acceptance Criteria

- [ ] AC1: Sector bubble chart displays all sectors with correct X/Y/Size/Color mapping
- [ ] AC2: Quadrant reference lines appear at X=0% and Y=50
- [ ] AC3: Period toggle recalculates all bubble positions with smooth animation
- [ ] AC4: Clicking sector bubble drills down to stock-level view
- [ ] AC5: Stock-level bubbles show correct stage coloring
- [ ] AC6: Tooltip displays formatted trading value in 억원 units
- [ ] AC7: Clicking stock bubble navigates to Chart Grid
- [ ] AC8: Market filter recalculates data correctly
- [ ] AC9: "Back to Sectors" returns to sector-level view preserving period selection

---

## SPEC-TOPDOWN-002C: Full-size Treemap Heatmap

### Purpose

Finviz-style hierarchical treemap showing the entire market with sector → stock hierarchy.

### Requirements (EARS Format)

**R1: Treemap Display**

- WHEN the Market Overview tab displays the Treemap view,
- THE system SHALL display a full-width treemap where:
  - Top-level rectangles: Sectors (산업명(대))
  - Nested rectangles: Individual stocks
  - Rectangle size: Market capitalization (시가총액)
  - Rectangle color: Price change % (green gradient for positive, red gradient for negative)
  - Labels: Stock name + price change % (visible for rectangles above minimum size)

**R2: Treemap Color Mapping**

- WHEN the treemap renders stock rectangles,
- THE system SHALL apply a diverging color scale:
  - > +5%: Dark green (#006400)
  - +2% to +5%: Green (#228B22)
  - +0.5% to +2%: Light green (#90EE90)
  - -0.5% to +0.5%: Gray (#808080)
  - -2% to -0.5%: Light red (#FFB6C1)
  - -5% to -2%: Red (#DC143C)
  - < -5%: Dark red (#8B0000)

**R3: Treemap Period Toggle**

- WHEN the user selects a different period (1W / 1M / 3M),
- THE system SHALL recalculate rectangle colors based on the selected period's price change

**R4: Treemap Drill-Down**

- WHEN the user clicks a sector rectangle,
- THE system SHALL zoom into that sector showing only its stocks
- AND display a breadcrumb navigation (KRX > Sector Name)
- AND clicking "KRX" in breadcrumb SHALL return to full market view

**R5: Treemap Interaction**

- WHEN the user hovers over a stock rectangle,
- THE system SHALL display a tooltip with: stock name, code, market cap (억원), price change %, RS rating, stage
- WHEN the user clicks a stock rectangle (in zoomed view),
- THE system SHALL navigate to Chart Grid with that stock

**R6: Treemap/MiniHeatmap Toggle**

- WHEN the Market Overview tab is active,
- THE system SHALL provide a toggle between:
  - [Mini Heatmap] (existing CSS grid view)
  - [Full Treemap] (new ECharts treemap)
- WHERE Mini Heatmap is the default view

### Frontend Components

**New files:**

- `frontend/src/components/MarketOverview/TreemapHeatmap.tsx` (ECharts treemap)
- `frontend/src/api/treemap.ts` (API client)
- `frontend/src/types/treemap.ts` (type definitions)

**Modified files:**

- `frontend/src/components/MarketOverview/MarketOverview.tsx` (add toggle between MiniHeatmap and Treemap)

### Acceptance Criteria

- [ ] AC1: Treemap displays all sectors and stocks with correct hierarchy
- [ ] AC2: Rectangle sizes proportional to market cap
- [ ] AC3: Color scale correctly maps price change to green/red gradient
- [ ] AC4: Clicking sector drills down to stock-level view
- [ ] AC5: Breadcrumb navigation works for zoom-out
- [ ] AC6: Period toggle updates colors
- [ ] AC7: Toggle between Mini Heatmap and Full Treemap works
- [ ] AC8: Tooltip shows complete stock information

---

## SPEC-TOPDOWN-002B: RRG (Relative Rotation Graph)

### Purpose

4-quadrant relative rotation graph showing sector momentum dynamics with 8-week trail animation.

### Requirements (EARS Format)

**R1: RRG Quadrant Display**

- WHEN the Sector Analysis tab displays the RRG view,
- THE system SHALL display a scatter chart with:
  - X-axis: RS-Ratio (centered at 100, range ~90-110)
  - Y-axis: RS-Momentum (centered at 100, range ~90-110)
  - 4 quadrants with labeled backgrounds:
    - Top-right: "Leading" (light green background)
    - Bottom-right: "Weakening" (light yellow background)
    - Bottom-left: "Lagging" (light red background)
    - Top-left: "Improving" (light blue background)

**R2: Sector Trails**

- WHEN the RRG renders sector data,
- THE system SHALL display for each sector:
  - 8-week trail as a connected line path
  - Trail head (current position): Large filled circle with sector label
  - Trail body: Progressively more transparent towards older data points
  - Trail color: Unique per sector (from a predefined palette)

**R3: RRG Interaction**

- WHEN the user hovers over a sector trail head,
- THE system SHALL display a tooltip with: sector name, RS-Ratio, RS-Momentum, quadrant, 1W excess return
- WHEN the user clicks a sector trail head,
- THE system SHALL navigate to the Sector Analysis Ranking Table with that sector highlighted

**R4: RRG Sector Filter**

- WHEN the user wants to focus on specific sectors,
- THE system SHALL provide checkboxes to show/hide individual sectors
- AND a "Select All" / "Deselect All" toggle
- AND hidden sectors SHALL be removed from the chart (not just made transparent)

**R5: RRG Animation (Optional Enhancement)**

- WHEN the user clicks "Animate" button,
- THE system SHALL animate the trail from 8 weeks ago to current position
- AND sectors SHALL move along their trail paths over 3-5 seconds

### Frontend Components

**New files:**

- `frontend/src/components/SectorAnalysis/RRGChart.tsx` (ECharts custom scatter with trails)
- `frontend/src/api/rrg.ts` (API client)
- `frontend/src/types/rrg.ts` (type definitions)

**Modified files:**

- `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx` (add RRG to sub-navigation)

### Acceptance Criteria

- [ ] AC1: 4 quadrants display with correct labels and background colors
- [ ] AC2: Each sector shows 8-week trail with fading transparency
- [ ] AC3: Trail head shows sector label
- [ ] AC4: Tooltip shows RS-Ratio, RS-Momentum, and quadrant
- [ ] AC5: Sector filter shows/hides sectors correctly
- [ ] AC6: Clicking trail head navigates to sector detail

---

## SPEC-TOPDOWN-002D: Sector Rank Bump Chart

### Purpose

12-week sector ranking history as a bump chart (ranked line chart).

### Requirements (EARS Format)

**R1: Bump Chart Display**

- WHEN the Sector Analysis tab displays the Bump Chart view,
- THE system SHALL display a line chart where:
  - X-axis: Date (12 weeks, weekly intervals)
  - Y-axis: Rank position (1 at top, inverted scale, 1 = strongest)
  - Each line: One sector, distinct color
  - Right-side labels: Sector names at current rank position

**R2: Bump Chart Interaction**

- WHEN the user hovers over a data point,
- THE system SHALL:
  - Highlight that sector's full line (bold + elevated z-index)
  - Dim all other sectors
  - Show tooltip: sector name, rank, composite score, week date
- WHEN the user clicks a sector line,
- THE system SHALL navigate to Sector Analysis Ranking Table with that sector highlighted

**R3: Bump Chart Top-N Filter**

- WHEN the user selects top-N filter (Top 5 / Top 10 / All),
- THE system SHALL display only sectors that appeared in the top-N at any point during the 12-week period
- WHERE "All" shows all sectors

### Frontend Components

**New files:**

- `frontend/src/components/SectorAnalysis/BumpChart.tsx` (ECharts line chart with inverted rank axis)
- `frontend/src/api/history.ts` (API client for sector history)

**Modified files:**

- `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx` (add Bump Chart to sub-navigation)

### Acceptance Criteria

- [ ] AC1: Bump chart displays 12 weeks of rank data for all sectors
- [ ] AC2: Y-axis is inverted (rank 1 at top)
- [ ] AC3: Each sector has a distinct color
- [ ] AC4: Hover highlights the sector's full line and dims others
- [ ] AC5: Tooltip shows rank, composite score, and date
- [ ] AC6: Top-N filter correctly limits displayed sectors

---

## SPEC-TOPDOWN-002E: Leading Sector Early Detection Alerts

### Purpose

Automatic detection and alert when a sector shows early signs of strength or weakness transition.

### Requirements (EARS Format)

**R1: Sector Strength Transition Detection**

- WHEN the system analyzes sector data,
- THE system SHALL detect "emerging strength" when a sector meets 3+ of:
  1. Rank improvement >= 3 positions in last 4 weeks
  2. RS average increase >= 10 points in last 4 weeks
  3. Stage 2 % increase >= 10%p in last 4 weeks
  4. Volume surge: sector trading value > 1.5× 4-week average
  5. RRG quadrant moved from Lagging/Improving to Leading

**R2: Sector Weakness Transition Detection**

- WHEN the system analyzes sector data,
- THE system SHALL detect "emerging weakness" when a sector meets 3+ of:
  1. Rank decline >= 3 positions in last 4 weeks
  2. RS average decrease >= 10 points in last 4 weeks
  3. Stage 2 % decrease >= 10%p in last 4 weeks
  4. Volume dry-up: sector trading value < 0.5× 4-week average
  5. RRG quadrant moved from Leading/Weakening to Lagging

**R3: Alert Display in Weekly Highlights**

- WHEN the Market Overview tab is active AND there are sector alerts,
- THE system SHALL display in the WeeklyHighlights component:
  - "Emerging Leaders" section: sectors showing early strength signals
  - "Weakening Sectors" section: sectors showing early weakness signals
  - Each alert: sector name, key signal summary, link to Sector Analysis

**R4: Alert API**

- WHEN the system computes alerts,
- THE system SHALL include alert data in the `/api/market/overview` response:
  - `sector_alerts.emerging_leaders: [{name, signals: [string]}]`
  - `sector_alerts.weakening_sectors: [{name, signals: [string]}]`

### Backend Changes

**Extend**: `my_chart/analysis/sector_advanced.py`
- `detect_sector_transitions(db_path, date) -> SectorAlerts`

**Extend**: `/api/market/overview` response schema

### Frontend Changes

**Modified files:**
- `frontend/src/components/MarketOverview/WeeklyHighlights.tsx` (add alert sections)
- `frontend/src/types/market.ts` (add alert type definitions)

### Acceptance Criteria

- [ ] AC1: Emerging strength detected when 3+ criteria met
- [ ] AC2: Emerging weakness detected when 3+ criteria met
- [ ] AC3: Alerts appear in WeeklyHighlights with correct signal summaries
- [ ] AC4: Clicking alert sector navigates to Sector Analysis

---

## UI Integration: Sector Analysis Sub-Navigation

### Tab Structure

**Current Sector Analysis tab:**
```
[Sector Analysis]
└── SectorRankingTable + SectorDetailPanel
```

**Phase 2 Sector Analysis tab:**
```
[Sector Analysis]
├── Sub-nav: [Table] [Bubble] [RRG] [Bump]
├── [Table]: SectorRankingTable + SectorDetailPanel (existing)
├── [Bubble]: SectorBubbleChart / StockBubbleChart (002F)
├── [RRG]: RRGChart (002B)
└── [Bump]: BumpChart (002D)
```

### Market Overview Tab Enhancement

```
[Market Overview]
├── MarketPhaseCard (existing)
├── BreadthChart (existing)
├── Heatmap Toggle: [Mini] [Treemap]
│   ├── [Mini]: MiniHeatmap (existing)
│   └── [Treemap]: TreemapHeatmap (002C)
└── WeeklyHighlights (existing + 002E alerts)
```

---

## Implementation Phases

### Phase 2-1: Backend Foundation (SPEC-TOPDOWN-002A) — Priority P0

**Goal**: Build all backend computation and API endpoints for Phase 2 features.

**Tasks:**
1. Create `my_chart/analysis/sector_advanced.py` module
2. Implement sector price index computation (market-cap weighted, 12-week history)
3. Implement trading value (거래대금) aggregation
4. Implement RRG metrics (RS-Ratio, RS-Momentum normalization)
5. Implement sector ranking history retrieval
6. Implement treemap data hierarchy construction
7. Create API endpoints: `/api/sectors/bubble`, `/api/sectors/{name}/bubble`, `/api/sectors/rrg`, `/api/sectors/history`, `/api/market/treemap`
8. Add `market` filter parameter to sector ranking (also satisfies Phase 1 R6)
9. Write comprehensive tests (85%+ coverage)

**Estimated files**: 8-12
**Risk**: Medium (RRG normalization algorithm requires careful testing)

### Phase 2-2: Bubble Chart + Treemap (002F + 002C) — Priority P1

**Goal**: Deliver the two most impactful visualization features.

**Tasks:**
1. Install `echarts` + `echarts-for-react` dependencies
2. Create ECharts base configuration (dark theme matching existing UI)
3. Implement Sector Bubble Chart (sector-level view)
4. Implement Stock Bubble Chart (drill-down view)
5. Implement period toggle, market filter, tooltip interactions
6. Implement Full-size Treemap Heatmap
7. Implement treemap drill-down with breadcrumb
8. Add sub-navigation to Sector Analysis tab
9. Add heatmap toggle to Market Overview tab
10. Write frontend tests

**Estimated files**: 12-16
**Dependencies**: 002A backend APIs
**Risk**: Low-Medium (ECharts integration is well-documented)

### Phase 2-3: RRG + Bump Chart (002B + 002D) — Priority P2

**Goal**: Advanced sector rotation visualization.

**Tasks:**
1. Implement RRG 4-quadrant chart with custom ECharts series
2. Implement 8-week trail with fading transparency
3. Implement sector filter (show/hide sectors)
4. Implement Bump Chart with inverted rank axis
5. Implement hover highlight + dim interaction
6. Implement Top-N filter
7. Add views to Sector Analysis sub-navigation
8. Write frontend tests

**Estimated files**: 8-12
**Dependencies**: 002A backend APIs
**Risk**: Medium (RRG trail animation is custom, requires ECharts custom series)

### Phase 2-4: Early Detection + Polish (002E) — Priority P3

**Goal**: Intelligence layer and final polish.

**Tasks:**
1. Implement sector transition detection algorithm
2. Extend `/api/market/overview` with alert data
3. Update WeeklyHighlights with alert sections
4. Performance optimization for all Phase 2 endpoints
5. Integration testing across all new views
6. UI polish and responsive design validation

**Estimated files**: 6-8
**Dependencies**: 002A + 002B (for RRG quadrant data)
**Risk**: Low

---

## Technical Decisions

1. **ECharts for Phase 2**: Single library for all new chart types. Avoids multiple library dependencies. Canvas rendering ensures performance with 2,500+ data points.

2. **No new DB tables**: All computations derived at query time from existing `stock_prices`, `stock_meta`, and `relative_strength` tables. Sector price index and ranking history computed on-the-fly (cached with 1-hour TTL).

3. **Sub-navigation in Sector Analysis**: Keeps the 4-tab top-level structure clean. All sector-focused visualizations grouped under one tab.

4. **Trading value (거래대금) as bubble size**: More intuitive than market cap for showing "market activity". High trading value = high market interest, regardless of stock size.

5. **ECharts dark theme**: Must match existing Lightweight Charts dark theme (#1a1a2e background, #9ca3af text, #2d2d44 grid). Create a shared ECharts theme configuration.

6. **Coexistence with Lightweight Charts**: ECharts handles bubble/treemap/RRG. Lightweight Charts continues to handle candlestick/line charts in ChartGrid. No migration needed.

7. **RRG normalization**: Use JdK RS-Ratio method (rolling z-score over 12-week lookback, centered at 100, ±standard deviation). This matches industry standard RRG implementations.

8. **Stage color consistency**: Bubble chart stock-level colors MUST match existing stage badge colors: S1=yellow(#EAB308), S2=green(#22C55E), S3=orange(#F97316), S4=red(#EF4444).

---

## Estimated Timeline

```
Week 1:    SPEC-TOPDOWN-002A (Backend Foundation)
Week 2-3:  SPEC-TOPDOWN-002F (Bubble Chart) + 002C (Treemap)
Week 3-4:  SPEC-TOPDOWN-002B (RRG) + 002D (Bump Chart)
Week 4-5:  SPEC-TOPDOWN-002E (Early Detection) + Integration & Polish
```

---

**Document Version**: 1.0
**Created**: 2026-03-15
**Branch**: feature/sector-rotation
**Author**: manager-spec agent (MoAI)
