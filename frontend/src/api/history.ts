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
  // 순위 기준 기간(요청 period)의 초과수익률(%). period 미지정(composite 순위)이면 null.
  rank_basis_excess_return?: number | null
}

// 섹터별 히스토리 아이템
export interface SectorHistoryItem {
  name: string
  history: SectorHistoryWeek[]
}

// API 응답 타입
export interface SectorHistoryResponse {
  weeks: number
  // AC-SUX-028 (REQ-SUX-026): 축 하단에 weeks 와 span_days 를 병기. ② 봉투가 제공.
  span_days?: number | null
  sectors: SectorHistoryItem[]
  // 순위 기준 echo — '1w'/'1m'/'3m'(표의 기간 탭과 같은 기준) 또는 null(composite).
  period?: string | null
}

// 순위 기준 — 표(/sectors/ranking)의 기간·시장 토글과 같은 값을 넘기면 Bump 가 표와 같은 순위를 그린다.
export interface SectorHistoryBasis {
  period?: string
  market?: string
}

// 섹터 히스토리 데이터 조회 (기본 12주). 기준을 생략하면 서버 기본(composite·전체 시장)이다.
export async function fetchSectorHistory(
  weeks: number = 12,
  basis: SectorHistoryBasis = {},
): Promise<SectorHistoryResponse> {
  const params: Record<string, string | number> = { weeks }
  if (basis.period) params.period = basis.period
  if (basis.market) params.market = basis.market
  const response = await client.get<SectorHistoryResponse>('/sectors/history', { params })
  return response.data
}
