// Sector detail API response types - mirrors backend schemas/sector.py SectorDetailResponse

export interface SubSectorItem {
  name: string
  stock_count: number
  stage1_count: number
  stage2_count: number
  stage3_count: number
  stage4_count: number
}

export interface TopStockItem {
  code: string
  name: string
  rs_12m: number
  stage: number | null
}

export interface SectorDetailResponse {
  sector_name: string
  sub_sectors: SubSectorItem[]
  top_stocks: TopStockItem[]
}
