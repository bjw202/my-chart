// RED: Specification tests for MarketOverview container component
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock child components to isolate container logic
vi.mock('../MarketPhaseCard', () => ({
  MarketPhaseCard: (props: Record<string, unknown>) => (
    <div data-testid="market-phase-card" data-phase={props.phase as string}>MarketPhaseCard</div>
  ),
}))

vi.mock('../BreadthChart', () => ({
  BreadthChart: () => <div data-testid="breadth-chart">BreadthChart</div>,
}))

vi.mock('../MiniHeatmap', () => ({
  MiniHeatmap: (props: { sectors: unknown[]; onSectorClick: (name: string) => void }) => (
    <div data-testid="mini-heatmap">
      <button onClick={() => props.onSectorClick('Technology')}>Technology Cell</button>
    </div>
  ),
}))

vi.mock('../WeeklyHighlights', () => ({
  WeeklyHighlights: () => <div data-testid="weekly-highlights">WeeklyHighlights</div>,
}))

const mockNavigateToTab = vi.fn()

vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({ navigateToTab: mockNavigateToTab }),
}))

// MarketContext mock - uses a variable so we can change it per test
let mockMarketState = {
  overview: null as null | typeof mockOverview,
  sectorRanking: null as null | typeof mockSectorRanking,
  loading: false,
  error: null as string | null,
}

vi.mock('../../../contexts/MarketContext', () => ({
  useMarket: () => mockMarketState,
}))

const mockOverview = {
  kospi: { close: 2700, chg_1w: 1.5, sma50: 2650, sma200: 2600, sma50_slope: 0.1, sma200_slope: 0.05 },
  kosdaq: { close: 850, chg_1w: -0.5, sma50: 840, sma200: 820, sma50_slope: -0.02, sma200_slope: 0.01 },
  breadth: {
    kospi: { pct_above_sma50: 65, pct_above_sma200: 72, nh_nl_ratio: 1.5, nh_nl_diff: 50, ad_ratio: 0.6, breadth_score: 70 },
    kosdaq: { pct_above_sma50: 55, pct_above_sma200: 60, nh_nl_ratio: 1.2, nh_nl_diff: 30, ad_ratio: 0.55, breadth_score: 58 },
  },
  cycle: { phase: 'bull' as const, choppy: false, criteria: [], confidence: 0.8 },
  breadth_history: [
    { date: '2025-01-01', pct_above_sma50: 65.0, nh_nl_ratio: 1.5, breadth_score: 70.0 },
  ],
}

const mockSectorRanking = {
  date: '2025-01-01',
  sectors: [
    {
      name: 'Technology', stock_count: 50,
      returns: { w1: 2.5, m1: 5.0, m3: 10.0 },
      excess_returns: { w1: 1.0, m1: 2.0, m3: 4.0 },
      rs_avg: 75, rs_top_pct: 30, nh_pct: 20, stage2_pct: 40,
      composite_score: 80, rank: 1, rank_change: 2,
    },
  ],
}

import { MarketOverview } from '../MarketOverview'

describe('MarketOverview container', () => {
  it('renders loading state when loading is true', () => {
    mockMarketState = { overview: null, sectorRanking: null, loading: true, error: null }
    render(<MarketOverview />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('renders error state when error is present', () => {
    mockMarketState = { overview: null, sectorRanking: null, loading: false, error: 'Network error' }
    render(<MarketOverview />)
    expect(screen.getByText(/failed|error/i)).toBeInTheDocument()
  })

  it('renders error state when overview is null without error msg', () => {
    mockMarketState = { overview: null, sectorRanking: null, loading: false, error: null }
    render(<MarketOverview />)
    expect(screen.getByText(/failed/i)).toBeInTheDocument()
  })
})

describe('MarketOverview container (with data)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockMarketState = { overview: mockOverview, sectorRanking: mockSectorRanking, loading: false, error: null }
  })

  it('renders MarketPhaseCard with correct phase', () => {
    render(<MarketOverview />)
    expect(screen.getByTestId('market-phase-card')).toBeInTheDocument()
    expect(screen.getByTestId('market-phase-card').getAttribute('data-phase')).toBe('bull')
  })

  it('renders BreadthChart', () => {
    render(<MarketOverview />)
    expect(screen.getByTestId('breadth-chart')).toBeInTheDocument()
  })

  it('renders MiniHeatmap', () => {
    render(<MarketOverview />)
    expect(screen.getByTestId('mini-heatmap')).toBeInTheDocument()
  })

  it('renders WeeklyHighlights', () => {
    render(<MarketOverview />)
    expect(screen.getByTestId('weekly-highlights')).toBeInTheDocument()
  })

  it('navigates to sector-analysis tab when sector cell is clicked', async () => {
    const user = userEvent.setup()
    render(<MarketOverview />)
    await user.click(screen.getByText('Technology Cell'))
    expect(mockNavigateToTab).toHaveBeenCalledWith('sector-analysis', { sectorName: 'Technology' })
  })

  it('renders market-overview wrapper element', () => {
    render(<MarketOverview />)
    expect(document.querySelector('.market-overview')).toBeInTheDocument()
  })
})
