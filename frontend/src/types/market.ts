// Tab navigation types for SPEC-TOPDOWN-001B
export type TabId = 'market-overview' | 'sector-analysis' | 'stock-explorer' | 'chart-grid'

// Cross-tab navigation parameters
export interface CrossTabParams {
  sectorName?: string
  stockCodes?: string[]
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
