// TypeScript types mirroring backend schemas/screen.py

export type IndicatorName =
  | 'Close'
  | 'Open'
  | 'High'
  | 'Low'
  | 'EMA10'
  | 'EMA20'
  | 'SMA5'
  | 'SMA50'
  | 'SMA100'
  | 'SMA200'

export type CompareOperator = 'gt' | 'gte' | 'lt' | 'lte'

export type MarketName = 'KOSPI' | 'KOSDAQ'

export interface PatternCondition {
  indicator_a: IndicatorName
  operator: CompareOperator
  indicator_b: IndicatorName
  multiplier: number // default 1.0
}

export interface ScreenRequest {
  market_cap_min: number | null
  chg_1d_min: number | null
  chg_1w_min: number | null
  chg_1m_min: number | null
  chg_3m_min: number | null
  patterns: PatternCondition[] // max 5
  pattern_logic: 'AND' | 'OR'
  rs_min: number | null
  markets: MarketName[]
  sectors: string[]
  codes: string[] // Stock codes to filter by (from cross-tab navigation)
  minervini_trend_template?: boolean | null
}

export interface StockItem {
  code: string
  name: string
  market: string
  market_cap?: number | null
  sector_major?: string | null
  sector_minor?: string | null
  product?: string | null
  close?: number | null
  change_1d?: number | null
  rs_12m?: number | null
  ema10?: number | null
  ema20?: number | null
  sma50?: number | null
  sma100?: number | null
  sma200?: number | null
  /** Minervini Trend Template 통과 시 항상 8, 플래그 꺼짐 시 null */
  trend_template_score?: number | null
}

// @MX:NOTE: [AUTO] Preset 타입 — 프리셋 레지스트리의 단일 진실 원천(SSOT) 단위
// @MX:SPEC: SPEC-PRESET-001 REQ-PST-001
export type PresetId = 'minervini_full' | 'breakout_init' | 'stage1_accumulation'

export interface Preset {
  id: PresetId
  label: string
  description: string
  /** 네이티브 title 속성 전용 안내 문구. 미지정 시 description을 fallback으로 사용한다 (REQ-PST-012). */
  tooltip?: string
  patch: Partial<ScreenRequest>
}

export const DEFAULT_SCREEN_REQUEST: ScreenRequest = {
  market_cap_min: null,
  chg_1d_min: null,
  chg_1w_min: null,
  chg_1m_min: null,
  chg_3m_min: null,
  patterns: [],
  pattern_logic: 'AND',
  rs_min: null,
  markets: [],
  sectors: [],
  codes: [],
  minervini_trend_template: null,
}
