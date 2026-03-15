# SPEC-TOPDOWN-001: Top-Down Market Analysis System

## Overview

- **Feature**: Top-Down 시장분석 시스템 (Market Cycle → Sector Rotation → Stage Analysis → Chart Grid)
- **Branch**: feature/sector-rotation
- **Methodology**: TDD (RED-GREEN-REFACTOR)
- **Scope**: Full-stack (Backend data layer + Frontend UI)

---

## Implementation Roadmap

This feature is divided into 5 SPECs, ordered by dependency and value delivery:

| SPEC | Name | Scope | Dependency |
| --- | --- | --- | --- |
| SPEC-TOPDOWN-001A | Backend Data Engine | Backend only | None |
| SPEC-TOPDOWN-001B | Tab Navigation & Context Bar | Frontend shell | 001A |
| SPEC-TOPDOWN-001C | Market Overview Tab | Frontend + API | 001A, 001B |
| SPEC-TOPDOWN-001D | Sector Analysis Tab | Frontend + API | 001A, 001B |
| SPEC-TOPDOWN-001E | Stock Explorer Tab + Chart Grid Enhancement | Frontend + API | 001A, 001B |

Phase 2 (future):

| SPEC | Name | Scope |
| --- | --- | --- |
| SPEC-TOPDOWN-002A | RRG (Relative Rotation Graph) | Backend + Frontend |
| SPEC-TOPDOWN-002B | Sector RS Trend Chart | Frontend |
| SPEC-TOPDOWN-002C | Full-size Treemap Heatmap | Frontend |

---

## SPEC-TOPDOWN-001A: Backend Data Engine

### Purpose

Market breadth, sector metrics, stage classification 계산 엔진을 백엔드에 구축한다.

### Requirements (EARS Format)

**R1: Market Breadth Calculation**

- WHEN the system calculates market breadth indicators,
- THE system SHALL compute the following for KOSPI and KOSDAQ separately:
  - `pct_above_sma50`: % of stocks with Close &gt; SMA50 (use weekly SMA10 as \~50-day proxy, or daily SMA50)
  - `pct_above_sma200`: % of stocks with Close &gt; SMA200 (use weekly SMA40 as \~200-day proxy, or daily SMA200)
  - `nh_nl_ratio`: 52-week new high count / (new high + new low count), 0\~1 scale
  - `nh_nl_diff`: 52-week new high count - new low count
  - `ad_ratio`: advancing stocks / declining stocks (from CHG_1W sign)
  - `ad_line`: cumulative sum of (advancing - declining) over N weeks

**R2: Breadth Composite Score**

- WHEN the system computes the breadth composite,
- THE system SHALL normalize each indicator to 0-100 scale and compute:
  - `breadth_score = 0.25 * pct_above_sma50_norm + 0.25 * pct_above_sma200_norm + 0.25 * nh_nl_ratio_norm + 0.25 * ad_ratio_norm`
- WHERE normalization maps min-max to 0-100

**R3: Market Cycle Determination**

- WHEN the system determines market cycle phase,
- THE system SHALL evaluate 6 criteria and assign Bull/Sideways/Bear:

| \# | Criterion | Bull | Sideways | Bear |
| --- | --- | --- | --- | --- |
| 1 | KOSPI vs SMA50/200 | Price &gt; both MAs | Between MAs | Price &lt; both MAs |
| 2 | SMA50 slope (4-week) | Positive | Near zero | Negative |
| 3 | % &gt; SMA50 | &gt; 60% | 40-60% | &lt; 40% |
| 4 | % &gt; SMA200 | &gt; 55% | 40-55% | &lt; 40% |
| 5 | NH-NL ratio | &gt; 0.6 | 0.4-0.6 | &lt; 0.4 |
| 6 | Breadth Score | &gt; 65 | 35-65 | &lt; 35 |

- WHEN 4+ criteria point same direction, THE system SHALL confirm that phase
- WHEN criteria are mixed, THE system SHALL classify as "Sideways/Uncertain"

**R4: Choppy Market Detection**

- WHEN the system detects choppy conditions,
- THE system SHALL check:
  - MA Spread &lt; 5% (convergence of SMA20/50/200)
  - Breadth oscillation (pct_above_sma50 range &lt; 15%p within 40-60% band over 4 weeks)
  - Weekly return sign changes &gt;= 5 out of 8 weeks
  - NH + NL total &lt; 5% of universe
- WHEN 3+ conditions met, THE system SHALL flag "Choppy" overlay on market phase

**R5: Stage Classification Engine**

- WHEN the system classifies a stock's Weinstein Stage,
- THE system SHALL apply the following algorithm (priority order):

```
1. Stage 4 (Decline): Close < SMA50_proxy AND Close < SMA200_proxy AND SMA200_slope < -1%
2. Stage 2 (Advance): Close > SMA50_proxy AND Close > SMA200_proxy AND SMA50 > SMA200 AND SMA200_slope > 0.5%
   - Stage 2 Strong: RS_12M_Rating > 60
   - Stage 2 Weak: RS_12M_Rating <= 60
3. Stage 3 (Top): Close near SMA200 (±3%) AND SMA200_slope flattening AND SMA50_slope < 0
4. Stage 1 (Base): abs(SMA200_slope) < 0.5% AND Close within SMA200 ±5%
5. Default: Close > SMA200 → Stage 2 Early; else → Stage 4 Late
```

- WHERE SMA50_proxy = weekly SMA10, SMA200_proxy = weekly SMA40
- WHERE slope = (SMA_current - SMA_4weeks_ago) / SMA_4weeks_ago

**R6: Stage 2 Entry Screening**

- WHEN the system screens for Stage 2 entry candidates,
- THE system SHALL filter stocks meeting ALL of:
  1. Classified as Stage 2 (any sub-type)
  2. Close &gt; SMA50_proxy AND Close &gt; SMA200_proxy
  3. SMA50_proxy &gt; SMA200_proxy (Golden Cross)
  4. Volume &gt; VolumeSMA10 \* 1.5 (volume surge)
  5. RS_12M_Rating &gt;= 70 (top 30%)
  6. CHG_1M &gt; 0 (positive 1-month return)

**R7: Sector Strength Metrics**

- WHEN the system computes sector strength,
- THE system SHALL calculate for each sector (산업명(대)):
  - `sector_return_1w/1m/3m`: market-cap weighted average return of sector stocks
  - `sector_excess_return`: sector_return - KOSPI_return (per period)
  - `sector_rs_avg`: market-cap weighted average RS_12M_Rating
  - `sector_rs_top_pct`: % of sector stocks with RS_12M_Rating &gt;= 80
  - `sector_nh_pct`: % of sector stocks at 52-week high
  - `sector_stage2_pct`: % of sector stocks classified as Stage 2
  - `sector_rank_change`: current rank - rank_4weeks_ago

**R8: Sector Ranking**

- WHEN the system ranks sectors,
- THE system SHALL compute composite score:
  - `composite = 0.3 * excess_return_1w_norm + 0.4 * excess_return_1m_norm + 0.3 * excess_return_3m_norm`
- AND rank sectors by composite score descending

### API Endpoints

```
GET /api/market/overview
Response: {
  kospi: { close, chg_1w, sma50, sma200, sma50_slope, sma200_slope },
  kosdaq: { close, chg_1w, sma50, sma200, sma50_slope, sma200_slope },
  breadth: {
    kospi: { pct_above_sma50, pct_above_sma200, nh_nl_ratio, nh_nl_diff, ad_ratio, breadth_score },
    kosdaq: { ... }
  },
  cycle: { phase: "bull"|"sideways"|"bear", choppy: bool, criteria: [...], confidence: int },
  breadth_history: [ { date, pct_above_sma50, nh_nl_ratio, breadth_score, ... } ]  // 12-week
}

GET /api/sector/ranking
Response: {
  date: string,
  sectors: [
    {
      name: string,
      stock_count: int,
      returns: { w1: float, m1: float, m3: float },
      excess_returns: { w1: float, m1: float, m3: float },
      rs_avg: float,
      rs_top_pct: float,
      nh_pct: float,
      stage2_pct: float,
      composite_score: float,
      rank: int,
      rank_change: int  // vs 4 weeks ago
    }
  ]
}

GET /api/stage/overview
Response: {
  distribution: { stage1: int, stage2: int, stage3: int, stage4: int, total: int },
  by_sector: [
    { sector: string, stage1: int, stage2: int, stage3: int, stage4: int }
  ],
  stage2_candidates: [
    {
      code: string, name: string, market: string,
      sector_major: string, sector_minor: string,
      stage: string, stage_detail: string,
      rs_12m: float, chg_1m: float, volume_ratio: float,
      close: float, sma50: float, sma200: float
    }
  ]
}
```

### Data Layer Changes

**New module**: `my_chart/analysis/market_breadth.py`

- `compute_breadth(db_path, market, date) -> BreadthResult`
- `compute_breadth_history(db_path, market, weeks=12) -> list[BreadthResult]`
- `determine_cycle(breadth, kospi_data) -> CycleResult`
- `detect_choppy(breadth_history, kospi_data) -> bool`

**New module**: `my_chart/analysis/stage_classifier.py`

- `classify_stage(stock_row) -> StageResult`
- `classify_all(db_path, date) -> DataFrame`
- `screen_stage2_entry(db_path, date) -> DataFrame`

**New module**: `my_chart/analysis/sector_metrics.py`

- `compute_sector_ranking(db_path, date) -> list[SectorRank]`
- `compute_sector_history(db_path, weeks=12) -> list[list[SectorRank]]`

**DB Schema additions**: None needed for MVP. All computations are derived from existing stock_prices + relative_strength + stock_meta tables at query time.

### Acceptance Criteria

- [ ] AC1: `compute_breadth()` returns correct pct_above_sma50 for test dataset

- [ ] AC2: `determine_cycle()` returns "bull" when 4+ criteria are bullish

- [ ] AC3: `determine_cycle()` returns "sideways" when criteria are mixed

- [ ] AC4: `detect_choppy()` returns True when MA spread &lt; 5% and breadth oscillates

- [ ] AC5: `classify_stage()` correctly classifies Stage 2 Strong (Close &gt; SMAs, RS &gt; 60)

- [ ] AC6: `classify_stage()` correctly classifies Stage 4 (Close &lt; both SMAs, declining slope)

- [ ] AC7: `screen_stage2_entry()` filters only stocks meeting all 6 entry conditions

- [ ] AC8: `compute_sector_ranking()` ranks sectors by composite score

- [ ] AC9: Sector rank_change correctly compares current vs 4-week-ago rank

- [ ] AC10: All API endpoints return valid JSON matching schema

- [ ] AC11: API response time &lt; 500ms for full market overview

- [ ] AC12: 85%+ test coverage for all new modules

---

## SPEC-TOPDOWN-001B: Tab Navigation & Context Bar

### Purpose

기존 단일 화면 UI를 4-탭 구조로 전환하고, 시장 맥락 바를 추가한다.

### Requirements (EARS Format)

**R1: Tab Navigation**

- WHEN the user views the application,
- THE system SHALL display 4 tabs at the top:
  - \[Market Overview\] \[Sector Analysis\] \[Stock Explorer\] \[Chart Grid\]
- WHERE \[Chart Grid\] is the current default active tab
- AND clicking a tab switches the main content area

**R2: Context Bar**

- WHEN any tab is active,
- THE system SHALL display a context bar below the tabs showing:
  - Market phase indicator (Bull/Sideways/Bear + Choppy flag)
  - Top 2-3 strong sectors (by composite rank)
  - Top 2-3 weak sectors
- AND the context bar SHALL update when market data refreshes

**R3: Tab State Persistence**

- WHEN the user switches tabs,
- THE system SHALL preserve each tab's internal state (scroll position, selections)
- AND switching back to a tab SHALL restore its previous state

**R4: Cross-tab Navigation**

- WHEN the user clicks a sector in Market Overview tab,
- THE system SHALL navigate to Sector Analysis tab with that sector highlighted
- WHEN the user clicks a stock in Stock Explorer tab,
- THE system SHALL navigate to Chart Grid tab with that stock loaded

**R5: Backward Compatibility**

- WHEN the user opens the application,
- THE system SHALL default to Chart Grid tab
- AND the Chart Grid tab SHALL function identically to the current UI
- AND existing URL bookmarks/state SHALL continue to work

### Frontend Changes

**New files:**

- `frontend/src/components/TabNavigation/TabNavigation.tsx`
- `frontend/src/components/ContextBar/ContextBar.tsx`
- `frontend/src/contexts/MarketContext.tsx` (market overview data)
- `frontend/src/contexts/TabContext.tsx` (active tab state)

**Modified files:**

- `frontend/src/App.tsx` - Add TabNavigation wrapper, conditional content rendering

### Acceptance Criteria

- [ ] AC1: 4 tabs render at top of screen

- [ ] AC2: Chart Grid tab is active by default

- [ ] AC3: Context bar shows market phase from API

- [ ] AC4: Tab switching preserves each tab's state

- [ ] AC5: Clicking sector in Market Overview navigates to Sector Analysis

- [ ] AC6: Existing Chart Grid functionality is unchanged

---

## SPEC-TOPDOWN-001C: Market Overview Tab

### Purpose

시장 사이클 판단, Breadth 지표 차트, 미니 섹터 히트맵을 제공하는 시장 개요 탭.

### Requirements (EARS Format)

**R1: Market Phase Display**

- WHEN the Market Overview tab is active,
- THE system SHALL display:
  - KOSPI current price, weekly change %, phase label (Bull/Sideways/Bear)
  - KOSDAQ current price, weekly change %, phase label
  - Choppy warning badge if applicable

**R2: Breadth Line Chart**

- WHEN the Market Overview tab is active,
- THE system SHALL display a 12-week line chart with:
  - % &gt; SMA50 line (primary)
  - NH-NL ratio line (secondary axis)
  - Breadth composite score line
- AND horizontal reference lines at key thresholds (60%, 40% for SMA50)
- AND the chart SHALL use Lightweight Charts line series

**R3: Mini Sector Heatmap**

- WHEN the Market Overview tab is active,
- THE system SHALL display a compact heatmap grid showing:
  - All major sectors as colored blocks
  - Color: green gradient (positive return) to red gradient (negative return)
  - Text: sector name + 1-week return %
- AND clicking a sector block SHALL navigate to Sector Analysis tab

**R4: Weekly Highlights**

- WHEN the Market Overview tab is active,
- THE system SHALL display a "This Week's Notable Changes" section:
  - Market phase changes (if any)
  - Sectors with biggest rank changes (top 3)
  - Stage 2 entry count change vs last week

### Frontend Components

**New files:**

- `frontend/src/components/MarketOverview/MarketOverview.tsx`
- `frontend/src/components/MarketOverview/MarketPhaseCard.tsx`
- `frontend/src/components/MarketOverview/BreadthChart.tsx`
- `frontend/src/components/MarketOverview/MiniHeatmap.tsx`
- `frontend/src/components/MarketOverview/WeeklyHighlights.tsx`
- `frontend/src/api/market.ts`
- `frontend/src/types/market.ts`

### Acceptance Criteria

- [ ] AC1: Market phase card shows KOSPI/KOSDAQ with correct phase labels

- [ ] AC2: Breadth chart renders 12-week history with correct data

- [ ] AC3: Threshold reference lines appear at correct levels

- [ ] AC4: Mini heatmap shows all sectors with appropriate colors

- [ ] AC5: Clicking sector in heatmap navigates to Sector Analysis tab

- [ ] AC6: Weekly highlights section shows meaningful change data

---

## SPEC-TOPDOWN-001D: Sector Analysis Tab

### Purpose

섹터 상대강도 순위표와 섹터 상세 패널을 제공하는 섹터 분석 탭.

### Requirements (EARS Format)

**R1: Sector Ranking Table**

- WHEN the Sector Analysis tab is active,
- THE system SHALL display a sortable table with columns:
  - Rank (with rank change arrow: up/down/flat)
  - Sector name
  - 1W return, 1M return, 3M return (excess vs KOSPI)
  - RS avg score
  - RS top % (% of stocks with RS &gt;= 80)
  - 52W high % (% of stocks at 52-week high)
  - Stage 2 % (% of stocks in Stage 2)
- AND each cell SHALL have background color gradient based on value
- AND clicking a column header SHALL sort by that column

**R2: Sector Detail Panel**

- WHEN the user clicks a sector row,
- THE system SHALL display a detail panel below showing:
  - Sub-sector (산업명(중)) breakdown with same metrics
  - Sector's top 5 stocks by RS rating
  - Sector's Stage 2 entry candidates
- AND clicking a sub-sector SHALL navigate to Stock Explorer with that filter

**R3: Period Toggle**

- WHEN the user selects a different base period,
- THE system SHALL recalculate excess returns and re-rank sectors accordingly
- THE system SHALL support: 1W, 1M, 3M base periods

**R4: Market Filter**

- WHEN the user toggles KOSPI/KOSDAQ filter,
- THE system SHALL show sector rankings for selected market(s) only

### Frontend Components

**New files:**

- `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx`
- `frontend/src/components/SectorAnalysis/SectorRankingTable.tsx`
- `frontend/src/components/SectorAnalysis/SectorDetailPanel.tsx`
- `frontend/src/api/sector.ts` (extend existing)
- `frontend/src/types/sector.ts`

### Acceptance Criteria

- [ ] AC1: Sector ranking table renders all sectors with correct metrics

- [ ] AC2: Table is sortable by all columns

- [ ] AC3: Cell colors correctly reflect value (green=strong, red=weak)

- [ ] AC4: Rank change arrows show correct direction

- [ ] AC5: Clicking sector row opens detail panel with sub-sectors

- [ ] AC6: Clicking sub-sector navigates to Stock Explorer with filter

- [ ] AC7: Period toggle re-sorts and updates all values

---

## SPEC-TOPDOWN-001E: Stock Explorer Tab + Chart Grid Enhancement

### Purpose

종목 Stage 분류, Stage 2 스크리닝, Chart Grid에 Stage/RS 배지 오버레이.

### Requirements (EARS Format)

**R1: Stage Distribution Bar**

- WHEN the Stock Explorer tab is active,
- THE system SHALL display a horizontal bar showing:
  - Stage 1/2/3/4 distribution (count and percentage)
  - Each segment clickable to filter to that stage

**R2: Stock Table with Stage**

- WHEN the Stock Explorer tab is active,
- THE system SHALL display a table with columns:
  - Stock name, code, market
  - Stage badge (S1/S2/S2+/S3/S4 with color)
  - RS rating (0-100)
  - 12-week sparkline (mini price chart)
  - Key checklist: MA alignment, Volume surge, RS strength
- AND the table SHALL be filterable by: sector, stage, RS range
- AND the table SHALL be sortable by all columns

**R3: Sector Filter Integration**

- WHEN the user navigates from Sector Analysis tab,
- THE system SHALL pre-apply the selected sector as filter
- AND the user SHALL be able to change or clear the filter

**R4: Stage 2 Highlight**

- WHEN viewing Stage 2 stocks,
- THE system SHALL visually distinguish:
  - Stage 2 Strong (RS &gt; 60): bold border
  - Stage 2 Entry candidates (meeting all 6 criteria): star badge
  - Stage 2 Weak: normal display

**R5: Chart Grid Stage/RS Badge**

- WHEN the Chart Grid tab displays charts,
- THE system SHALL overlay in each chart cell header:
  - Stage badge (S1/S2/S2+/S3/S4)
  - RS rating number
- AND these badges SHALL use the same color scheme as Stock Explorer

**R6: Cross-tab Stock Selection**

- WHEN the user selects stocks in Stock Explorer (checkbox),
- AND clicks "View Charts",
- THE system SHALL navigate to Chart Grid with selected stocks loaded

### Frontend Components

**New files:**

- `frontend/src/components/StockExplorer/StockExplorer.tsx`
- `frontend/src/components/StockExplorer/StageDistributionBar.tsx`
- `frontend/src/components/StockExplorer/StockTable.tsx`
- `frontend/src/components/StockExplorer/Sparkline.tsx`
- `frontend/src/components/StockExplorer/StageChecklist.tsx`
- `frontend/src/api/stage.ts`
- `frontend/src/types/stage.ts`

**Modified files:**

- `frontend/src/components/ChartGrid/ChartCell.tsx` - Add Stage/RS badge overlay

### Acceptance Criteria

- [ ] AC1: Stage distribution bar shows correct counts per stage

- [ ] AC2: Stage badges display correct stage with appropriate colors

- [ ] AC3: Stock table is filterable by sector, stage, and RS range

- [ ] AC4: Sparkline renders 12-week price history for each stock

- [ ] AC5: Stage 2 entry candidates show star badge

- [ ] AC6: Chart Grid shows Stage/RS badge in each cell header

- [ ] AC7: "View Charts" button loads selected stocks in Chart Grid

- [ ] AC8: Pre-applied sector filter works from Sector Analysis navigation

---

## Implementation Order & Dependencies

```
Week 1-2: SPEC-TOPDOWN-001A (Backend Data Engine)
  ├── market_breadth.py (R1-R4)
  ├── stage_classifier.py (R5-R6)
  ├── sector_metrics.py (R7-R8)
  └── API endpoints + tests

Week 3: SPEC-TOPDOWN-001B (Tab Navigation & Context Bar)
  ├── TabNavigation component
  ├── ContextBar component
  ├── MarketContext provider
  └── App.tsx refactor

Week 4: SPEC-TOPDOWN-001C (Market Overview Tab)
  ├── MarketPhaseCard
  ├── BreadthChart (Lightweight Charts)
  ├── MiniHeatmap
  └── WeeklyHighlights

Week 5: SPEC-TOPDOWN-001D (Sector Analysis Tab)
  ├── SectorRankingTable
  ├── SectorDetailPanel
  └── Cross-tab navigation

Week 6: SPEC-TOPDOWN-001E (Stock Explorer + Chart Grid)
  ├── StageDistributionBar
  ├── StockTable with Stage badges
  ├── Sparkline component
  ├── ChartCell badge overlay
  └── Cross-tab stock selection

Week 7: Integration & Polish
  ├── End-to-end testing
  ├── Performance optimization
  ├── Edge case handling
  └── UI polish
```

## Phase 2 Roadmap (Future SPECs)

| SPEC | Feature | Prerequisite |
| --- | --- | --- |
| SPEC-TOPDOWN-002A | RRG (4-quadrant + 8-week trail) | Sector price index computation |
| SPEC-TOPDOWN-002B | Sector RS Trend Line Chart (12-week) | Sector ranking history |
| SPEC-TOPDOWN-002C | Full-size Treemap Heatmap (Finviz-style) | D3.js or similar library |
| SPEC-TOPDOWN-002D | Sector Rank Bump Chart | Sector ranking history |
| SPEC-TOPDOWN-002E | Leading Sector Early Detection Alerts | RS rank change + volume surge |

## Phase 3 Roadmap (Future SPECs)

| SPEC | Feature |
| --- | --- |
| SPEC-TOPDOWN-003A | Market Cycle Gauge (semicircle visualization) |
| SPEC-TOPDOWN-003B | Risk-On/Off Area Chart |
| SPEC-TOPDOWN-003C | Theme Mapping & Tracker (manual 5-10 themes) |
| SPEC-TOPDOWN-003D | Market Phase Transition Alerts |
| SPEC-TOPDOWN-003E | Stage Transition Alerts (S1→S2, S2→S3) |

## Technical Decisions

1. **SMA proxy for weekly data**: Use SMA10 (weekly) as \~50-day SMA proxy, SMA40 (weekly) as \~200-day SMA proxy. This avoids adding new columns to the weekly DB schema.

2. **No new DB tables**: All computations are derived at query time from existing tables. Sector metrics and stage classification are computed on-the-fly. This keeps the data pipeline simple.

3. **Lightweight Charts for Breadth**: Reuse the existing charting library for breadth line charts. No new charting dependency needed for Phase 1.

4. **Mini Heatmap**: CSS grid with colored divs. No D3.js dependency until Phase 2 full-size treemap.

5. **Context API over Redux**: Continue with existing React Context pattern. Add MarketContext and TabContext. No state management library change.

6. **API caching strategy**: Market overview data changes weekly. Cache with 1-hour TTL on frontend (stale-while-revalidate pattern).