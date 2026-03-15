// RED: Tests for MarketContext
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
vi.mock('../../api/market', () => ({
  fetchMarketOverview: vi.fn(),
  fetchSectorRanking: vi.fn(),
}))

import { fetchMarketOverview, fetchSectorRanking } from '../../api/market'
import { MarketProvider, useMarket } from '../MarketContext'
import type { MarketOverviewResponse, SectorRankingResponse } from '../../types/market'

const mockOverview: MarketOverviewResponse = {
  kospi: { close: 2700, chg_1w: 1.5, sma50: 2650, sma200: 2600, sma50_slope: 0.1, sma200_slope: 0.05 },
  kosdaq: { close: 850, chg_1w: -0.5, sma50: 840, sma200: 820, sma50_slope: -0.02, sma200_slope: 0.01 },
  breadth: {
    kospi: { pct_above_sma50: 65, pct_above_sma200: 72, nh_nl_ratio: 1.5, nh_nl_diff: 50, ad_ratio: 0.6, breadth_score: 70 },
    kosdaq: { pct_above_sma50: 55, pct_above_sma200: 60, nh_nl_ratio: 1.2, nh_nl_diff: 30, ad_ratio: 0.55, breadth_score: 58 },
  },
  cycle: { phase: 'bull', choppy: false, criteria: [], confidence: 0.8 },
  breadth_history: [],
}

const mockRanking: SectorRankingResponse = {
  date: '2025-01-01',
  sectors: [],
}

function TestConsumer(): React.ReactElement {
  const { overview, sectorRanking, loading, error, refresh } = useMarket()
  return (
    <div>
      <div data-testid="loading">{String(loading)}</div>
      <div data-testid="error">{error ?? 'none'}</div>
      <div data-testid="overview-phase">{overview?.cycle.phase ?? 'none'}</div>
      <div data-testid="ranking-date">{sectorRanking?.date ?? 'none'}</div>
      <button onClick={refresh}>Refresh</button>
    </div>
  )
}

describe('MarketProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch data in parallel on mount', async () => {
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverview)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRanking)

    render(
      <MarketProvider>
        <TestConsumer />
      </MarketProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('overview-phase').textContent).toBe('bull')
    })

    expect(fetchMarketOverview).toHaveBeenCalledTimes(1)
    expect(fetchSectorRanking).toHaveBeenCalledTimes(1)
  })

  it('should show loading state initially', () => {
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverview)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRanking)

    render(
      <MarketProvider>
        <TestConsumer />
      </MarketProvider>
    )

    // Initially loading should be true
    expect(screen.getByTestId('loading').textContent).toBe('true')
  })

  it('should handle fetch error gracefully', async () => {
    vi.mocked(fetchMarketOverview).mockRejectedValue(new Error('API error'))
    vi.mocked(fetchSectorRanking).mockRejectedValue(new Error('API error'))

    render(
      <MarketProvider>
        <TestConsumer />
      </MarketProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('error').textContent).not.toBe('none')
    })
    expect(screen.getByTestId('loading').textContent).toBe('false')
  })

  it('should refresh data when refresh is called', async () => {
    const user = userEvent.setup()
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverview)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRanking)

    render(
      <MarketProvider>
        <TestConsumer />
      </MarketProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('overview-phase').textContent).toBe('bull')
    })

    // Reset call counts
    vi.clearAllMocks()
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverview)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRanking)

    await user.click(screen.getByText('Refresh'))

    await waitFor(() => {
      expect(fetchMarketOverview).toHaveBeenCalledTimes(1)
    })
  })

  it('should expose sectorRanking data', async () => {
    const rankingWithData: SectorRankingResponse = {
      date: '2025-03-01',
      sectors: [
        {
          name: 'IT',
          stock_count: 50,
          returns: { w1: 1.5, m1: 3.0, m3: 8.0 },
          excess_returns: { w1: 0.5, m1: 1.0, m3: 2.0 },
          rs_avg: 75, rs_top_pct: 60, nh_pct: 30, stage2_pct: 50,
          composite_score: 80, rank: 1, rank_change: 2,
        },
      ],
    }
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverview)
    vi.mocked(fetchSectorRanking).mockResolvedValue(rankingWithData)

    render(
      <MarketProvider>
        <TestConsumer />
      </MarketProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('ranking-date').textContent).toBe('2025-03-01')
    })
  })
})

describe('useMarket hook', () => {
  it('should throw when used outside MarketProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(() => render(<TestConsumer />)).toThrow('useMarket must be used within MarketProvider')
    consoleError.mockRestore()
  })
})
