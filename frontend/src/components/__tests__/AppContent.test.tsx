// RED: Integration tests for App tab structure (AppContent component)
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock heavy dependencies
vi.mock('../../api/market', () => ({
  fetchMarketOverview: vi.fn().mockResolvedValue({
    kospi: { close: 2700, chg_1w: 1.5, sma50: 2650, sma200: 2600, sma50_slope: 0.1, sma200_slope: 0.05 },
    kosdaq: { close: 850, chg_1w: -0.5, sma50: 840, sma200: 820, sma50_slope: -0.02, sma200_slope: 0.01 },
    breadth: {
      kospi: { pct_above_sma50: 65, pct_above_sma200: 72, nh_nl_ratio: 1.5, nh_nl_diff: 50, ad_ratio: 0.6, breadth_score: 70 },
      kosdaq: { pct_above_sma50: 55, pct_above_sma200: 60, nh_nl_ratio: 1.2, nh_nl_diff: 30, ad_ratio: 0.55, breadth_score: 58 },
    },
    cycle: { phase: 'bull', choppy: false, criteria: [], confidence: 0.8 },
    breadth_history: [],
  }),
  fetchSectorRanking: vi.fn().mockResolvedValue({ date: '2025-01-01', sectors: [] }),
}))

vi.mock('../ChartGrid/ChartGrid', () => ({
  ChartGrid: () => <div data-testid="chart-grid">ChartGrid</div>,
}))

vi.mock('../StockList/StockList', () => ({
  StockList: () => <div data-testid="stock-list">StockList</div>,
}))

vi.mock('../FilterBar/FilterBar', () => ({
  FilterBar: () => <div data-testid="filter-bar">FilterBar</div>,
}))

vi.mock('../StatusBar/StatusBar', () => ({
  StatusBar: () => <div data-testid="status-bar">StatusBar</div>,
}))

vi.mock('../../api/screen', () => ({
  screenStocks: vi.fn().mockResolvedValue({ stocks: [], total: 0 }),
}))

vi.mock('../../api/sectors', () => ({
  fetchSectors: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../api/db', () => ({
  triggerUpdate: vi.fn(),
  fetchUpdateStatus: vi.fn(),
}))

// Mock MarketOverview to avoid lightweight-charts Canvas API issues in jsdom
vi.mock('../MarketOverview/MarketOverview', () => ({
  MarketOverview: () => <div data-testid="market-overview">MarketOverview</div>,
}))

import { MarketProvider } from '../../contexts/MarketContext'
import { TabProvider } from '../../contexts/TabContext'
import { ScreenProvider } from '../../contexts/ScreenContext'
import { NavigationProvider } from '../../contexts/NavigationContext'
import { WatchlistProvider } from '../../contexts/WatchlistContext'
import { AppContent } from '../../AppContent'

function renderApp() {
  return render(
    <MarketProvider>
      <TabProvider>
        <ScreenProvider>
          <NavigationProvider>
            <WatchlistProvider>
              <AppContent />
            </WatchlistProvider>
          </NavigationProvider>
        </ScreenProvider>
      </TabProvider>
    </MarketProvider>
  )
}

describe('AppContent tab structure', () => {
  it('should render TabNavigation with 4 tabs', () => {
    renderApp()
    expect(screen.getByText('Market Overview')).toBeInTheDocument()
    expect(screen.getByText('Sector Analysis')).toBeInTheDocument()
    expect(screen.getByText('Stock Explorer')).toBeInTheDocument()
    expect(screen.getByText('Chart Grid')).toBeInTheDocument()
  })

  it('should show Chart Grid content by default (chart-grid tab active)', () => {
    renderApp()
    expect(screen.getByTestId('chart-grid')).toBeInTheDocument()
    expect(screen.getByTestId('filter-bar')).toBeInTheDocument()
  })

  it('should show MarketOverview component when Market Overview tab is active', async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByText('Market Overview'))

    expect(screen.getByTestId('market-overview')).toBeInTheDocument()
  })

  it('should keep chart grid mounted but hidden when switching tabs', async () => {
    const user = userEvent.setup()
    renderApp()

    // Switch to market overview
    await user.click(screen.getByText('Market Overview'))

    // Chart grid should still be in DOM (display:none, not unmounted)
    expect(screen.getByTestId('chart-grid')).toBeInTheDocument()
  })

  it('should show StatusBar', () => {
    renderApp()
    expect(screen.getByTestId('status-bar')).toBeInTheDocument()
  })
})
