// 버블 차트 API 클라이언트 - 섹터/종목 버블 데이터 fetch
import client from './client'
import type { SectorBubbleResponse, StockBubbleResponse } from '../types/bubble'

// 섹터 버블 데이터 조회
export async function fetchSectorBubble(
  period: string,
  market?: string | null,
): Promise<SectorBubbleResponse> {
  const params: Record<string, string> = { period }
  if (market && market !== 'ALL') {
    params.market = market
  }
  const response = await client.get<SectorBubbleResponse>('/sectors/bubble', { params })
  return response.data
}

// 특정 섹터의 종목 버블 데이터 조회
export async function fetchStockBubble(
  sectorName: string,
  period: string,
): Promise<StockBubbleResponse> {
  const encoded = encodeURIComponent(sectorName)
  const response = await client.get<StockBubbleResponse>(`/sectors/${encoded}/bubble`, {
    params: { period },
  })
  return response.data
}
