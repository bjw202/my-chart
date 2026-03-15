// RED: Tests for RS badge display in ChartCell header
// This tests that ChartCell renders an RS badge with correct value and styling
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { StockItem } from '../../../types/stock'

// Mock all heavy dependencies for ChartCell
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    addHistogramSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    addLineSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ setVisibleRange: vi.fn(), fitContent: vi.fn(), applyOptions: vi.fn() })),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  })),
}))

vi.mock('../../../api/chart', () => ({
  fetchChartData: vi.fn(() => new Promise(() => {})), // never resolves in test
}))

vi.mock('../../../contexts/WatchlistContext', () => ({
  useWatchlist: () => ({
    isChecked: vi.fn(() => false),
    toggleStock: vi.fn(),
  }),
}))

vi.mock('../../../hooks/usePriceRangeMeasure', () => ({
  usePriceRangeMeasure: () => ({
    phase: 'idle',
    result: null,
    toggleMeasure: vi.fn(),
    reset: vi.fn(),
  }),
}))

vi.mock('../../../hooks/useAnalysis', () => ({
  useAnalysis: () => ({
    state: { status: 'idle' },
    load: vi.fn(),
    reset: vi.fn(),
  }),
}))

import { ChartCell } from '../ChartCell'

const makeStock = (overrides: Partial<StockItem> = {}): StockItem => ({
  code: '005930',
  name: '삼성전자',
  market: 'KOSPI',
  market_cap: 100000,
  sector_major: 'IT',
  sector_minor: '반도체',
  product: null,
  close: 75000,
  change_1d: 1.5,
  rs_12m: 75.5,
  ema10: null,
  ema20: null,
  sma50: 72000,
  sma100: null,
  sma200: 68000,
  ...overrides,
})

describe('ChartCell RS badge', () => {
  it('should display RS rating value in header', () => {
    render(
      <ChartCell
        stock={makeStock({ rs_12m: 75.5 })}
        isSelected={false}
        onClick={vi.fn()}
        timeframe="daily"
      />
    )

    // RS value should be shown (rounded to 76)
    expect(screen.getByText(/RS 76/)).toBeInTheDocument()
  })

  it('should show high RS highlight class when rs >= 80', () => {
    const { container } = render(
      <ChartCell
        stock={makeStock({ rs_12m: 85 })}
        isSelected={false}
        onClick={vi.fn()}
        timeframe="daily"
      />
    )

    const rsEl = container.querySelector('.chart-cell-rs--high')
    expect(rsEl).toBeTruthy()
  })

  it('should NOT show high RS highlight class when rs < 80', () => {
    const { container } = render(
      <ChartCell
        stock={makeStock({ rs_12m: 60 })}
        isSelected={false}
        onClick={vi.fn()}
        timeframe="daily"
      />
    )

    const rsEl = container.querySelector('.chart-cell-rs--high')
    expect(rsEl).toBeNull()
  })

  it('should display dash when rs_12m is null', () => {
    render(
      <ChartCell
        stock={makeStock({ rs_12m: null })}
        isSelected={false}
        onClick={vi.fn()}
        timeframe="daily"
      />
    )

    expect(screen.getByText(/RS -/)).toBeInTheDocument()
  })
})
