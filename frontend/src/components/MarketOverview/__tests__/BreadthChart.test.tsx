// RED: Specification tests for redesigned BreadthChart component
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

// Lightweight Charts requires Canvas API (not in jsdom); mock the entire module.
// vi.mock is hoisted, so we cannot reference variables declared outside the factory.
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
  { date: '2025-01-01', pct_above_sma50: 65.0, nh_nl_ratio: 0.65, breadth_score: 70.0 },
  { date: '2025-01-08', pct_above_sma50: 60.0, nh_nl_ratio: 0.55, breadth_score: 65.0 },
  { date: '2025-01-15', pct_above_sma50: 40.5, nh_nl_ratio: 0.38, breadth_score: 46.0 },
]

describe('BreadthChart', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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

  it('renders breadth-chart wrapper element', () => {
    render(<BreadthChart history={sampleHistory} />)
    expect(document.querySelector('.breadth-chart')).toBeInTheDocument()
  })

  it('renders both chart containers (main and mini)', () => {
    render(<BreadthChart history={sampleHistory} />)
    expect(screen.getByTestId('breadth-main-chart')).toBeInTheDocument()
    expect(screen.getByTestId('breadth-mini-chart')).toBeInTheDocument()
  })

  it('renders legend panel', () => {
    render(<BreadthChart history={sampleHistory} />)
    expect(screen.getByTestId('breadth-legend')).toBeInTheDocument()
  })

  it('legend shows current (latest) value for pct_above_sma50', () => {
    render(<BreadthChart history={sampleHistory} />)
    // Latest entry sorted by date is 2025-01-15 with pct_above_sma50 = 40.5
    expect(screen.getByTestId('breadth-legend').textContent).toContain('40.5%')
  })

  it('legend shows current (latest) value for breadth_score', () => {
    render(<BreadthChart history={sampleHistory} />)
    expect(screen.getByTestId('breadth-legend').textContent).toContain('46.0')
  })

  it('legend shows current (latest) value for nh_nl_ratio', () => {
    render(<BreadthChart history={sampleHistory} />)
    expect(screen.getByTestId('breadth-legend').textContent).toContain('0.38')
  })

  it('legend shows Korean descriptions', () => {
    render(<BreadthChart history={sampleHistory} />)
    const legend = screen.getByTestId('breadth-legend')
    expect(legend.textContent).toContain('50일 이평선 위 종목 비율')
    expect(legend.textContent).toContain('시장 건전성 종합점수')
    expect(legend.textContent).toContain('신고가 / (신고가+신저가)')
  })

  it('creates two separate chart instances (main + mini)', () => {
    render(<BreadthChart history={sampleHistory} />)
    expect(LWC.createChart).toHaveBeenCalledTimes(2)
  })

  it('handles empty history without throwing', () => {
    expect(() => render(<BreadthChart history={[]} />)).not.toThrow()
  })

  it('shows -- placeholders in legend when history is empty', () => {
    render(<BreadthChart history={[]} />)
    const legend = screen.getByTestId('breadth-legend')
    const dashes = legend.textContent?.match(/--/g) ?? []
    expect(dashes.length).toBeGreaterThanOrEqual(3)
  })
})
