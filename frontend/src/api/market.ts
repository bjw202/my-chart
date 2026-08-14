import client from './client'
import type { MarketOverviewResponse, SectorRankingResponse } from '../types/market'

// @MX:ANCHOR: [AUTO] External API integration point - market data endpoints
// @MX:REASON: Called by MarketContext on mount and refresh, high fan_in from context layer

export async function fetchMarketOverview(): Promise<MarketOverviewResponse> {
  const { data } = await client.get<MarketOverviewResponse>('/market/overview')
  return data
}

export async function fetchSectorRanking(market?: string | null): Promise<SectorRankingResponse> {
  // market 전송 필터 (01-data-contract.md §8) — 'all' 은 파라미터 미전송, kospi/kosdaq 은 전송
  const params: Record<string, string> = {}
  if (market && market !== 'all') {
    params.market = market
  }
  const { data } = await client.get<SectorRankingResponse>('/sectors/ranking', { params })
  return data
}
