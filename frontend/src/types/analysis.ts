// TypeScript types mirroring backend/schemas/analysis.py (AnalysisResponse)

export interface BusinessPerformance {
  periods: string[]
  revenue: number[]
  operating_profit: number[]
  net_income: number[]
  controlling_profit: number[]
  operating_cf: number[]
  gpm: number[]
  opm: number[]
  npm: number[]
  yoy_revenue: (number | null)[]
  yoy_op: (number | null)[]
  yoy_ni: (number | null)[]
  profit_quality: (number | null)[]
}

export interface HealthIndicator {
  name: string
  value: number | null
  threshold: string
  status: 'ok' | 'warn' | 'danger'
}

export interface HealthIndicators {
  indicators: HealthIndicator[]
}

export interface BalanceSheet {
  periods: string[]
  financing: Record<string, number[]>
  assets: Record<string, number[]>
}

export interface RateDecomposition {
  periods: string[]
  operating_asset_return: number[]
  non_operating_return: number[]
  borrowing_rate: number[]
  roe: number[]
  weighted_avg_roe: number
  ke: number | null
  spread: number | null
}

export interface ProfitWaterfallStep {
  name: string
  value: number
}

export interface ProfitWaterfall {
  steps: ProfitWaterfallStep[]
}

export interface TrendSignal {
  name: string
  direction: 'up' | 'flat' | 'down'
  description: string
}

export interface TrendSignals {
  signals: TrendSignal[]
}

export interface FiveQuestion {
  question: string
  status: 'ok' | 'warn' | 'danger'
  detail: string
}

export interface FiveQuestions {
  questions: FiveQuestion[]
  verdict: '양호' | '보통' | '주의'
}

export interface ActivityRatios {
  receivable_turnover: (number | null)[]
  receivable_days: (number | null)[]
  inventory_turnover: (number | null)[]
  inventory_days: (number | null)[]
  payable_turnover: (number | null)[]
  payable_days: (number | null)[]
  ccc: (number | null)[]
  asset_turnover: (number | null)[]
  periods: string[]
}

export interface AnalysisResponse {
  code: string
  company_name: string
  summary: string
  business_performance: BusinessPerformance | null
  health_indicators: HealthIndicators | null
  balance_sheet: BalanceSheet | null
  rate_decomposition: RateDecomposition | null
  profit_waterfall: ProfitWaterfall | null
  trend_signals: TrendSignals | null
  five_questions: FiveQuestions | null
  activity_ratios: ActivityRatios | null
}
