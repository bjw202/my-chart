import client from './client'
import type { MarketOverviewResponse, SectorRankingResponse } from '../types/market'

// @MX:ANCHOR: [AUTO] External API integration point - market data endpoints
// @MX:REASON: Called by MarketContext on mount and refresh, high fan_in from context layer

export async function fetchMarketOverview(): Promise<MarketOverviewResponse> {
  const { data } = await client.get<MarketOverviewResponse>('/market/overview')
  return data
}

export async function fetchSectorRanking(): Promise<SectorRankingResponse> {
  const { data } = await client.get<SectorRankingResponse>('/sector/ranking')
  return data
}
