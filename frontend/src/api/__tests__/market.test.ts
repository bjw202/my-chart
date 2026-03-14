// RED: Tests for market API functions
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the axios client
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
  },
}))

import client from '../client'
import { fetchMarketOverview, fetchSectorRanking } from '../market'
import type { MarketOverviewResponse, SectorRankingResponse } from '../../types/market'

const mockMarketOverview: MarketOverviewResponse = {
  kospi: { close: 2700, chg_1w: 1.5, sma50: 2650, sma200: 2600, sma50_slope: 0.1, sma200_slope: 0.05 },
  kosdaq: { close: 850, chg_1w: -0.5, sma50: 840, sma200: 820, sma50_slope: -0.02, sma200_slope: 0.01 },
  breadth: {
    kospi: { pct_above_sma50: 65, pct_above_sma200: 72, nh_nl_ratio: 1.5, nh_nl_diff: 50, ad_ratio: 0.6, breadth_score: 70 },
    kosdaq: { pct_above_sma50: 55, pct_above_sma200: 60, nh_nl_ratio: 1.2, nh_nl_diff: 30, ad_ratio: 0.55, breadth_score: 58 },
  },
  cycle: { phase: 'bull', choppy: false, criteria: [], confidence: 0.8 },
  breadth_history: [],
}

const mockSectorRanking: SectorRankingResponse = {
  date: '2025-01-01',
  sectors: [
    {
      name: 'IT',
      stock_count: 50,
      returns: { w1: 1.5, m1: 3.0, m3: 8.0 },
      excess_returns: { w1: 0.5, m1: 1.0, m3: 2.0 },
      rs_avg: 75,
      rs_top_pct: 60,
      nh_pct: 30,
      stage2_pct: 50,
      composite_score: 80,
      rank: 1,
      rank_change: 2,
    },
  ],
}

describe('fetchMarketOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should call GET /market/overview', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockMarketOverview })

    await fetchMarketOverview()

    expect(client.get).toHaveBeenCalledWith('/market/overview')
  })

  it('should return MarketOverviewResponse data', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockMarketOverview })

    const result = await fetchMarketOverview()

    expect(result).toEqual(mockMarketOverview)
    expect(result.cycle.phase).toBe('bull')
  })

  it('should propagate errors', async () => {
    vi.mocked(client.get).mockRejectedValue(new Error('Network error'))

    await expect(fetchMarketOverview()).rejects.toThrow('Network error')
  })
})

describe('fetchSectorRanking', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should call GET /sector/ranking', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockSectorRanking })

    await fetchSectorRanking()

    expect(client.get).toHaveBeenCalledWith('/sector/ranking')
  })

  it('should return SectorRankingResponse data', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockSectorRanking })

    const result = await fetchSectorRanking()

    expect(result).toEqual(mockSectorRanking)
    expect(result.sectors).toHaveLength(1)
    expect(result.sectors[0].name).toBe('IT')
  })

  it('should propagate errors', async () => {
    vi.mocked(client.get).mockRejectedValue(new Error('Server error'))

    await expect(fetchSectorRanking()).rejects.toThrow('Server error')
  })
})
