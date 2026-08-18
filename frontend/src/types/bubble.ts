// 버블 차트 API 응답 타입 - 섹터 버블 및 종목 버블
// @MX:NOTE: [AUTO] 섹터/종목 버블 차트 전용 타입 정의 (SPEC-TOPDOWN-002F)

export interface SectorBubbleItem {
  name: string
  // M3 (AC-SMU-029) — 백엔드 nullable 확장과 동시 적용, 값은 불변.
  excess_return: number | null  // KOSPI 대비 초과수익률 (%)
  rs_avg: number | null         // 섹터 평균 RS (0-100)
  trading_value: number | null  // 거래대금 합계 (원)
  period_return: number | null  // 기간 수익률 (%)
}

export interface SectorBubbleResponse {
  date: string
  period: string
  market: string | null
  sectors: SectorBubbleItem[]
  // ② 봉투(EnvelopeMixin) 선택 필드 — M6 AC-SUX-037 기준일 배지 / SN-5 격자 버전.
  as_of_date?: string | null
  as_of_is_partial_week?: boolean | null
  grid_version?: string | null
}

export interface StockBubbleItem {
  name: string
  price_change: number
  rs_12m: number
  trading_value: number
  stage: number | null     // Weinstein Stage 1~4
  stage_detail: string | null
  market_cap: number
  volume_ratio: number
  sector_minor: string | null  // 산업명(중) — SPEC-SECTOR-MINOR-COLOR-001
  product: string | null       // 주요제품 — SPEC-STOCK-TOOLTIP-PRODUCT-001
}

export interface StockBubbleResponse {
  date: string
  sector_name: string
  period: string
  stocks: StockBubbleItem[]
  // ② 봉투(EnvelopeMixin) 선택 필드 — M6 AC-SUX-037.
  as_of_date?: string | null
  as_of_is_partial_week?: boolean | null
  grid_version?: string | null
}
