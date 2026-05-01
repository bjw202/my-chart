// @MX:ANCHOR: [AUTO] themes.ts는 /themes/snapshot, /themes/quick API 클라이언트 함수를 노출
// @MX:REASON: ThemeAnalysis 컴포넌트에서 참조; SPEC-NAVER-THEME-001 API 계약 단일 진입점
// @MX:SPEC: SPEC-NAVER-THEME-001 REQ-NT-R-001, REQ-NT-R-002
import client from './client'

export interface ThemeItem {
  theme_id: number
  theme_name: string
  change_pct: number
  change_pct_3d: number
  momentum_score?: number
  breadth_ratio?: number
  top_stocks_preview?: string
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
  const response = await client.get('/themes/snapshot', {
    params: { top_n: topN, leaders_per_theme: leadersPerTheme },
  })
  return response.data as ThemesSnapshotResponse
}

export async function fetchThemesQuick(topN?: number): Promise<ThemesQuickResponse> {
  const response = await client.get('/themes/quick', { params: { top_n: topN } })
  return response.data as ThemesQuickResponse
}
