// 트리맵 히트맵에 사용되는 타입 정의

export interface TreemapStockNode {
  name: string
  market_cap: number
  price_change: number
  rs_12m: number
  stage: number | null
}

export interface TreemapSectorNode {
  name: string
  market_cap: number
  price_change: number
  stocks: TreemapStockNode[]
}

export interface TreemapResponse {
  date: string
  period: string
  total_market_cap: number
  sectors: TreemapSectorNode[]
}
