// 버블 차트 API 클라이언트 - 섹터/종목 버블 데이터 fetch
import client from './client'
import type { SectorBubbleResponse, StockBubbleResponse } from '../types/bubble'

// market 은 두 엔드포인트 모두 소문자 3값(all|kospi|kosdaq) 단일 규약이며 'all' 도 그대로 보낸다.
// 백엔드 pattern 이 ^(all|kospi|kosdaq)$ 이므로 생략/대문자 분기가 필요 없다 (routers/sectors.py).
const DEFAULT_MARKET = 'all'

// 섹터 버블 데이터 조회
export async function fetchSectorBubble(
  period: string,
  market: string = DEFAULT_MARKET,
): Promise<SectorBubbleResponse> {
  const response = await client.get<SectorBubbleResponse>('/sectors/bubble', {
    params: { period, market },
  })
  return response.data
}

// 특정 섹터의 종목 버블 데이터 조회
export async function fetchStockBubble(
  sectorName: string,
  period: string,
  market: string = DEFAULT_MARKET,
): Promise<StockBubbleResponse> {
  const encoded = encodeURIComponent(sectorName)
  const response = await client.get<StockBubbleResponse>(`/sectors/${encoded}/bubble`, {
    params: { period, market },
  })
  return response.data
}
