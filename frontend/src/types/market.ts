// Tab navigation types for SPEC-TOPDOWN-001B
export type TabId = 'market-overview' | 'sector-analysis' | 'stock-explorer' | 'chart-grid' | 'theme-analysis'

// @MX:ANCHOR: [AUTO] NavIntent — cross-tab navigation single source of truth (SPEC-SECTOR-UX-001 M3, REQ-SUX-003)
// @MX:REASON: Replaces the legacy cross-tab navigation type. Consumer fan_in >= 3 (ChartGrid/StockExplorer/AppContent guard).
//   3-condition consumer guard: target === MY_TAB_ID && activeTab === MY_TAB_ID && id !== lastHandledId.
//   payload intentionally omits sectorName (REQ-SUX-005/SM-4) — sector selection writes to SelectionContext.

// NavIntent payload — subTab / stockCodes / focusStock only (AC-SUX-004 (b), AC-SUX-006).
// sectorName MUST NOT appear here (REQ-SUX-005).
export interface NavIntentPayload {
  subTab?: string
  stockCodes?: string[]
  focusStock?: string
}

// Addressed navigation intent. `id` is monotonic per navigate() call so consumers
// can distinguish a re-send (same payload, new id) from a re-render (same id).
export interface NavIntent {
  id: number
  target: TabId
  payload: NavIntentPayload
}

// Market overview API response types (matching GET /api/market/overview)
export interface MarketIndexData {
  close: number
  chg_1w: number
  sma50: number
  sma200: number
  sma50_slope: number
  sma200_slope: number
}

export interface BreadthData {
  pct_above_sma50: number
  pct_above_sma200: number
  nh_nl_ratio: number
  nh_nl_diff: number
  ad_ratio: number
  breadth_score: number
}

export interface MarketCycleCriterion {
  name: string
  value: string
  signal: string
}

export interface BreadthHistoryEntry {
  date: string
  pct_above_sma50: number
  nh_nl_ratio: number
  breadth_score: number
}

export interface MarketOverviewResponse {
  kospi: MarketIndexData
  // API returns null when KOSDAQ data is unavailable
  kosdaq: MarketIndexData | null
  breadth: {
    kospi: BreadthData
    kosdaq: BreadthData | null
  }
  cycle: {
    phase: 'bull' | 'sideways' | 'bear'
    choppy: boolean
    criteria: MarketCycleCriterion[]
    confidence: number
  }
  breadth_history: BreadthHistoryEntry[]
  sector_alerts?: SectorAlertsData | null
}

export interface SectorAlertItem {
  name: string
  signals: string[]
}

export interface SectorAlertsData {
  emerging_leaders: SectorAlertItem[]
  weakening_sectors: SectorAlertItem[]
}

// Sector ranking API response types (matching GET /api/sector/ranking)
export interface SectorRankItem {
  name: string
  stock_count: number
  returns: { w1: number; m1: number; m3: number }
  excess_returns: { w1: number; m1: number; m3: number }
  rs_avg: number
  rs_top_pct: number
  nh_pct: number
  stage2_pct: number
  composite_score: number
  rank: number
  rank_change: number
}

export interface SectorRankingResponse {
  date: string
  sectors: SectorRankItem[]
}
