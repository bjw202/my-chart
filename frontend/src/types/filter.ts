// TypeScript types mirroring backend schemas/screen.py

export type IndicatorName =
  | 'Close'
  | 'Open'
  | 'High'
  | 'Low'
  | 'EMA10'
  | 'EMA20'
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
  patterns: PatternCondition[] // max 3
  pattern_logic: 'AND' | 'OR'
  rs_min: number | null
  markets: MarketName[]
  sectors: string[]
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
}
