// @MX:ANCHOR: [AUTO] themes.ts는 /themes/v2/snapshot, /themes/v2/quick API 클라이언트 함수를 노출
// @MX:REASON: ThemeAnalysis 컴포넌트에서 참조; SPEC-NAVER-THEME-003 V2 endpoint 채택 단일 진입점
// @MX:SPEC: SPEC-NAVER-THEME-001 REQ-NT-R-001, REQ-NT-R-002, SPEC-NAVER-THEME-003 REQ-NT3-001, REQ-NT3-002, REQ-NT3-003
import client from './client'

export interface ThemeItem {
  theme_id: number
  theme_name: string
  change_pct: number
  change_pct_3d: number
  momentum_score?: number
  breadth_ratio?: number
  top_stocks_preview?: string
  theme_description?: string | null // V2 추가 (REQ-NT3-002): 테마 설명 — sectorDescription 매핑
}

export interface ThemeStockItem {
  theme_id: number
  theme_name: string
  stock_code: string
  stock_name: string
  inclusion_reason: string
  price: number
  change: number
  change_pct: number
  volume: number
  trade_value: number
  market_cap: number | null
  leader_score?: number
  rank?: number
  stock_description?: string | null // V2 forward-compat (REQ-NT3-003): 종목별 편입설명 — item.description 매핑
}

export interface MultiThemeStockItem {
  stock_code: string
  stock_name: string
  theme_names: string[]
  theme_count: number
  avg_change_pct: number
}

export interface ThemesSnapshotResponse {
  themes: ThemeItem[]
  stocks: ThemeStockItem[]
  strong_themes: ThemeItem[]
  leaders: ThemeStockItem[]
  multi_theme_stocks: MultiThemeStockItem[]
  metadata: {
    collected_at: string
    theme_count: number
    stock_count: number
    elapsed_sec: number
    errors: unknown[]
  }
}

export interface ThemesQuickResponse {
  themes: ThemeItem[]
  strong_themes: ThemeItem[]
  metadata: {
    collected_at: string
    theme_count: number
    stock_count: number
    elapsed_sec: number
    errors: unknown[]
  }
}

export async function fetchThemesSnapshot(topN?: number, leadersPerTheme?: number): Promise<ThemesSnapshotResponse> {
  // V2 endpoint URL swap (REQ-NT3-001): /themes/snapshot → /themes/v2/snapshot
  const response = await client.get('/themes/v2/snapshot', {
    params: { top_n: topN, leaders_per_theme: leadersPerTheme },
  })
  return response.data as ThemesSnapshotResponse
}

export async function fetchThemesQuick(topN?: number): Promise<ThemesQuickResponse> {
  // V2 endpoint URL swap (REQ-NT3-001): /themes/quick → /themes/v2/quick
  const response = await client.get('/themes/v2/quick', { params: { top_n: topN } })
  return response.data as ThemesQuickResponse
}
