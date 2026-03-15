// 섹터 히스토리(랭크 변동) API 클라이언트 - Bump Chart용 데이터 fetch
import client from './client'

// 개별 주별 섹터 데이터
export interface SectorHistoryWeek {
  date: string
  rank: number
  composite_score: number
  sector_return_1w: number
  sector_excess_return_1w: number
  rs_avg: number
}

// 섹터별 히스토리 아이템
export interface SectorHistoryItem {
  name: string
  history: SectorHistoryWeek[]
}

// API 응답 타입
export interface SectorHistoryResponse {
  weeks: number
  sectors: SectorHistoryItem[]
}

// 섹터 히스토리 데이터 조회 (기본 12주)
export async function fetchSectorHistory(weeks: number = 12): Promise<SectorHistoryResponse> {
  const response = await client.get<SectorHistoryResponse>('/sectors/history', { params: { weeks } })
  return response.data
}
