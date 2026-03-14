// RED: Tests for ContextBar component
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('../../api/market', () => ({
  fetchMarketOverview: vi.fn(),
  fetchSectorRanking: vi.fn(),
}))

import { fetchMarketOverview, fetchSectorRanking } from '../../api/market'
import { MarketProvider } from '../../contexts/MarketContext'
import { ContextBar } from './ContextBar'
import type { MarketOverviewResponse, SectorRankingResponse } from '../../types/market'

const mockOverviewBull: MarketOverviewResponse = {
  kospi: { close: 2700, chg_1w: 1.5, sma50: 2650, sma200: 2600, sma50_slope: 0.1, sma200_slope: 0.05 },
  kosdaq: { close: 850, chg_1w: -0.5, sma50: 840, sma200: 820, sma50_slope: -0.02, sma200_slope: 0.01 },
  breadth: {
    kospi: { pct_above_sma50: 65, pct_above_sma200: 72, nh_nl_ratio: 1.5, nh_nl_diff: 50, ad_ratio: 0.6, breadth_score: 70 },
    kosdaq: { pct_above_sma50: 55, pct_above_sma200: 60, nh_nl_ratio: 1.2, nh_nl_diff: 30, ad_ratio: 0.55, breadth_score: 58 },
  },
  cycle: { phase: 'bull', choppy: false, criteria: [], confidence: 0.8 },
  breadth_history: [],
}

const mockOverviewBullChoppy: MarketOverviewResponse = {
  ...mockOverviewBull,
  cycle: { phase: 'bull', choppy: true, criteria: [], confidence: 0.6 },
}

const mockOverviewBear: MarketOverviewResponse = {
  ...mockOverviewBull,
  cycle: { phase: 'bear', choppy: false, criteria: [], confidence: 0.75 },
}

const mockRankingWithSectors: SectorRankingResponse = {
  date: '2025-01-01',
  sectors: [
    {
      name: 'IT', stock_count: 50,
      returns: { w1: 1.5, m1: 3.0, m3: 8.0 },
      excess_returns: { w1: 0.5, m1: 1.0, m3: 2.0 },
      rs_avg: 75, rs_top_pct: 60, nh_pct: 30, stage2_pct: 50,
      composite_score: 80, rank: 1, rank_change: 2,
    },
    {
      name: 'Health', stock_count: 30,
      returns: { w1: 1.0, m1: 2.5, m3: 6.0 },
      excess_returns: { w1: 0.3, m1: 0.8, m3: 1.5 },
      rs_avg: 70, rs_top_pct: 55, nh_pct: 25, stage2_pct: 45,
      composite_score: 72, rank: 2, rank_change: 0,
    },
    {
      name: 'Energy', stock_count: 20,
      returns: { w1: -1.0, m1: -2.5, m3: -6.0 },
      excess_returns: { w1: -0.3, m1: -0.8, m3: -1.5 },
      rs_avg: 30, rs_top_pct: 15, nh_pct: 5, stage2_pct: 10,
      composite_score: 20, rank: 3, rank_change: -1,
    },
  ],
}

function renderContextBar() {
  return render(
    <MarketProvider>
      <ContextBar />
    </MarketProvider>
  )
}

describe('ContextBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should show loading state while fetching', () => {
    vi.mocked(fetchMarketOverview).mockImplementation(() => new Promise(() => undefined))
    vi.mocked(fetchSectorRanking).mockImplementation(() => new Promise(() => undefined))

    renderContextBar()
    expect(screen.getByTestId('context-bar-loading')).toBeInTheDocument()
  })

  it('should show bull market phase badge', async () => {
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverviewBull)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRankingWithSectors)

    renderContextBar()

    await waitFor(() => {
      expect(screen.getByText('Bull')).toBeInTheDocument()
    })
  })

  it('should show bear market phase badge', async () => {
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverviewBear)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRankingWithSectors)

    renderContextBar()

    await waitFor(() => {
      expect(screen.getByText('Bear')).toBeInTheDocument()
    })
  })

  it('should show Choppy warning when choppy is true', async () => {
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverviewBullChoppy)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRankingWithSectors)

    renderContextBar()

    await waitFor(() => {
      expect(screen.getByText('Choppy')).toBeInTheDocument()
    })
  })

  it('should not show Choppy when not choppy', async () => {
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverviewBull)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRankingWithSectors)

    renderContextBar()

    await waitFor(() => {
      expect(screen.getByText('Bull')).toBeInTheDocument()
    })
    expect(screen.queryByText('Choppy')).not.toBeInTheDocument()
  })

  it('should show top 2 strong sectors', async () => {
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverviewBull)
    vi.mocked(fetchSectorRanking).mockResolvedValue(mockRankingWithSectors)

    renderContextBar()

    await waitFor(() => {
      expect(screen.getByTestId('strong-sectors')).toBeInTheDocument()
    })
    // Ranks 1 and 2 are strong (IT, Health)
    const strongEl = screen.getByTestId('strong-sectors')
    expect(strongEl.textContent).toContain('IT')
    expect(strongEl.textContent).toContain('Health')
  })

  it('should show top 2 weak sectors (bottom ranks)', async () => {
    const rankingWithMany: SectorRankingResponse = {
      date: '2025-01-01',
      sectors: [
        ...mockRankingWithSectors.sectors,
        {
          name: 'Steel', stock_count: 15,
          returns: { w1: -2.0, m1: -4.0, m3: -10.0 },
          excess_returns: { w1: -1.0, m1: -2.0, m3: -4.0 },
          rs_avg: 20, rs_top_pct: 10, nh_pct: 2, stage2_pct: 5,
          composite_score: 10, rank: 4, rank_change: -2,
        },
      ],
    }
    vi.mocked(fetchMarketOverview).mockResolvedValue(mockOverviewBull)
    vi.mocked(fetchSectorRanking).mockResolvedValue(rankingWithMany)

    renderContextBar()

    await waitFor(() => {
      expect(screen.getByTestId('weak-sectors')).toBeInTheDocument()
    })
    // Bottom 2 ranks are weak (Energy rank 3, Steel rank 4)
    const weakEl = screen.getByTestId('weak-sectors')
    expect(weakEl.textContent).toContain('Energy')
    expect(weakEl.textContent).toContain('Steel')
  })

  it('should show error state when fetch fails', async () => {
    vi.mocked(fetchMarketOverview).mockRejectedValue(new Error('API error'))
    vi.mocked(fetchSectorRanking).mockRejectedValue(new Error('API error'))

    renderContextBar()

    await waitFor(() => {
      expect(screen.getByText('Market data unavailable')).toBeInTheDocument()
    })
  })

  it('should render context bar container', () => {
    vi.mocked(fetchMarketOverview).mockImplementation(() => new Promise(() => undefined))
    vi.mocked(fetchSectorRanking).mockImplementation(() => new Promise(() => undefined))

    const { container } = renderContextBar()
    expect(container.querySelector('.context-bar')).toBeInTheDocument()
  })
})
