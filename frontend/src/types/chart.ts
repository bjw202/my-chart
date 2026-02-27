// TypeScript types mirroring backend schemas/chart.py and db.py

export interface CandleBar {
  time: string // "YYYY-MM-DD"
  open: number
  high: number
  low: number
  close: number
}

export interface VolumeBar {
  time: string // "YYYY-MM-DD"
  value: number
}

export interface MAPoint {
  time: string // "YYYY-MM-DD"
  value: number
}

export interface MAOverlay {
  ema10: MAPoint[]
  ema20: MAPoint[]
  sma50: MAPoint[]
  sma100: MAPoint[]
  sma200: MAPoint[]
}

export interface ChartResponse {
  candles: CandleBar[]
  volume: VolumeBar[]
  ma: MAOverlay
}

// DB update types (mirroring backend schemas/db.py)
export interface UpdateProgress {
  phase: string
  progress: number // 0.0 - 100.0
  current_stock: string | null
  total: number
  eta_seconds: number | null
}

export interface LastUpdated {
  last_updated: string | null
  daily_db_size: number // bytes
  weekly_db_size: number // bytes
}

export interface UpdateResult {
  status: string // "completed" | "error"
  success_count: number
  skipped_count: number
  error_count: number
  skipped_codes: string[]
}
