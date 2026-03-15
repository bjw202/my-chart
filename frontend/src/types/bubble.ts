// 버블 차트 API 응답 타입 - 섹터 버블 및 종목 버블
// @MX:NOTE: [AUTO] 섹터/종목 버블 차트 전용 타입 정의 (SPEC-TOPDOWN-002F)

export interface SectorBubbleItem {
  name: string
  excess_return: number  // KOSPI 대비 초과수익률 (%)
  rs_avg: number         // 섹터 평균 RS (0-100)
  trading_value: number  // 거래대금 합계 (원)
  period_return: number  // 기간 수익률 (%)
}

export interface SectorBubbleResponse {
  date: string
  period: string
  market: string | null
  sectors: SectorBubbleItem[]
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
}

export interface StockBubbleResponse {
  date: string
  sector_name: string
  period: string
  stocks: StockBubbleItem[]
}
