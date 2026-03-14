// RED: Specification tests for BreadthChart component
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

// Lightweight Charts requires Canvas API (not in jsdom); mock the entire module
// vi.mock is hoisted, so we cannot reference variables declared outside the factory
vi.mock('lightweight-charts', () => {
  const mockCreatePriceLine = vi.fn()
  const mockLineSeries = {
    setData: vi.fn(),
    createPriceLine: mockCreatePriceLine,
  }
  const mockChart = {
    addLineSeries: vi.fn().mockReturnValue(mockLineSeries),
    remove: vi.fn(),
    applyOptions: vi.fn(),
    timeScale: vi.fn().mockReturnValue({ fitContent: vi.fn() }),
  }
  return {
    createChart: vi.fn().mockReturnValue(mockChart),
    LineStyle: { Dashed: 1 },
  }
})

import { BreadthChart } from '../BreadthChart'
import * as LWC from 'lightweight-charts'

const sampleHistory = [
  { date: '2025-01-01', pct_above_sma50: 65.0, nh_nl_ratio: 1.5, breadth_score: 70.0 },
  { date: '2025-01-08', pct_above_sma50: 60.0, nh_nl_ratio: 1.2, breadth_score: 65.0 },
  { date: '2025-01-15', pct_above_sma50: 55.0, nh_nl_ratio: 1.0, breadth_score: 58.0 },
]

describe('BreadthChart', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Re-setup the mock return value after clearAllMocks
    const mockCreatePriceLine = vi.fn()
    const mockLineSeries = {
      setData: vi.fn(),
      createPriceLine: mockCreatePriceLine,
    }
    vi.mocked(LWC.createChart).mockReturnValue({
      addLineSeries: vi.fn().mockReturnValue(mockLineSeries),
      remove: vi.fn(),
      applyOptions: vi.fn(),
      timeScale: vi.fn().mockReturnValue({ fitContent: vi.fn() }),
    } as unknown as ReturnType<typeof LWC.createChart>)
  })

  it('renders chart container element', () => {
    render(<BreadthChart history={sampleHistory} />)
    const container = document.querySelector('.breadth-chart-container')
    expect(container).toBeInTheDocument()
  })

  it('renders without error with empty history', () => {
    expect(() => render(<BreadthChart history={[]} />)).not.toThrow()
  })

  it('renders without error with sample history', () => {
    expect(() => render(<BreadthChart history={sampleHistory} />)).not.toThrow()
  })

  it('calls createChart on mount', () => {
    render(<BreadthChart history={sampleHistory} />)
    expect(LWC.createChart).toHaveBeenCalled()
  })

  it('adds 3 line series for 3 data dimensions', () => {
    render(<BreadthChart history={sampleHistory} />)
    const chartInstance = vi.mocked(LWC.createChart).mock.results[0].value as ReturnType<typeof LWC.createChart>
    expect(chartInstance.addLineSeries).toHaveBeenCalledTimes(3)
  })

  it('creates reference lines at 60 and 40 on pct_above_sma50 series', () => {
    render(<BreadthChart history={sampleHistory} />)
    const chartInstance = vi.mocked(LWC.createChart).mock.results[0].value as ReturnType<typeof LWC.createChart>
    // First addLineSeries call = pct_above_sma50 series
    const pctSeries = vi.mocked(chartInstance.addLineSeries).mock.results[0].value as ReturnType<typeof chartInstance.addLineSeries>
    const priceCalls = vi.mocked(pctSeries.createPriceLine).mock.calls
    const prices = priceCalls.map((call: unknown[]) => (call[0] as { price: number }).price)
    expect(prices).toContain(60)
    expect(prices).toContain(40)
  })

  it('has breadth-chart wrapper element', () => {
    render(<BreadthChart history={sampleHistory} />)
    const wrapper = document.querySelector('.breadth-chart')
    expect(wrapper).toBeInTheDocument()
  })
})
