// Sector detail API response types - mirrors backend schemas/sector.py SectorDetailResponse

export interface SubSectorItem {
  name: string
  stock_count: number
  stage1_count: number
  stage2_count: number
  stage3_count: number
  stage4_count: number
  rs_avg?: number        // 서브섹터 평균 RS (백엔드 확장 시 추가)
  stage2_pct?: number    // 서브섹터 Stage2 비율 % (백엔드 확장 시 추가)
}

export interface TopStockItem {
  code: string
  name: string
  rs_12m: number
  stage: number | null
  chg_1m?: number | null      // 1개월 수익률 % (백엔드 확장 시 추가)
  stage_detail?: string | null // 스테이지 상세 정보
}

export interface SectorDetailResponse {
  sector_name: string
  sub_sectors: SubSectorItem[]
  top_stocks: TopStockItem[]
}
