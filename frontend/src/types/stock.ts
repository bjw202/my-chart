// TypeScript types mirroring backend schemas/screen.py (response models)

export interface StockItem {
  code: string
  name: string
  market: string
  market_cap: number | null
  sector_major: string | null
  sector_minor: string | null
  product: string | null
  close: number | null
  change_1d: number | null
  rs_12m: number | null
  ema10: number | null
  ema20: number | null
  sma50: number | null
  sma100: number | null
  sma200: number | null
}

export interface SectorGroup {
  sector_name: string
  stock_count: number
  stocks: StockItem[]
}

export interface ScreenResponse {
  total: number
  sectors: SectorGroup[]
}

export interface SectorInfo {
  sector_name: string
  stock_count: number
}
