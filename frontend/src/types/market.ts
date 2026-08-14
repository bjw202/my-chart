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

// Sector ranking API response types (matching GET /api/sectors/ranking).
// backend/schemas/sector.py 의 SectorRankingResponse(EnvelopeMixin) 가 제공하는
// 봉투 필드(excluded / baseline_date / as_of_date 등)를 추가로 선언한다 — 기존
// {date, sectors} 에 더해 ② SPEC-SECTOR-AGGREGATION-001 봉투가 내려주는 값들.
// 전부 optional: 백엔드가 값을 주지 않으면 undefined 로 우아하게 결손 처리한다.
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
  rank_change: number | null   // AC-SUX-025: null = 신규 진입. 기존 number 호환
}

// 순위 대상 제외 섹터 (② 봉투 ExcludedSectorModel: sector/reason/count).
export interface ExcludedSector {
  sector: string
  reason: string
  count: number
}

export interface SectorRankingResponse {
  date: string
  sectors: SectorRankItem[]
  // ② 봉투(EnvelopeMixin) 선택 필드 — M4 AC-SUX-019/025/058 소비.
  excluded?: ExcludedSector[]
  baseline_date?: string | null   // AC-SUX-025: rank_change 기준일 헤더
  as_of_date?: string | null      // AC-SUX-037 기준일 배지 (M6 정식 소비)
  as_of_is_partial_week?: boolean | null
  grid_version?: string | null   // SN-5: 격자 규칙 버전 — 변경 시 전 캐시 무효화
}
