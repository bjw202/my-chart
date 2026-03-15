// RED: Specification tests for SectorAnalysis container component
import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock MarketContext
const mockMarketState = {
  sectorRanking: {
    date: '2025-01-01',
    sectors: [
      {
        name: 'Technology',
        stock_count: 50,
        returns: { w1: 2.5, m1: 5.0, m3: 10.0 },
        excess_returns: { w1: 1.0, m1: 2.0, m3: 4.0 },
        rs_avg: 75,
        rs_top_pct: 30,
        nh_pct: 20,
        stage2_pct: 40,
        composite_score: 80,
        rank: 1,
        rank_change: 2,
      },
      {
        name: 'Finance',
        stock_count: 30,
        returns: { w1: -1.0, m1: -2.0, m3: 1.0 },
        excess_returns: { w1: -0.5, m1: -1.0, m3: 0.5 },
        rs_avg: 45,
        rs_top_pct: 10,
        nh_pct: 5,
        stage2_pct: 15,
        composite_score: 40,
        rank: 2,
        rank_change: -1,
      },
    ],
  },
  overview: null,
  loading: false,
  error: null,
  refresh: vi.fn(),
}

vi.mock('../../../contexts/MarketContext', () => ({
  useMarket: () => mockMarketState,
}))

// Mock TabContext — default: no crossTabParams
let mockCrossTabParams: { sectorName?: string } | null = null
const mockClearCrossTabParams = vi.fn()

vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({
    crossTabParams: mockCrossTabParams,
    clearCrossTabParams: mockClearCrossTabParams,
  }),
}))

// Import after mocks
import { SectorAnalysis } from '../SectorAnalysis'

describe('SectorAnalysis — initial render', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCrossTabParams = null
  })

  it('renders the sector-analysis container', () => {
    render(<SectorAnalysis />)
    expect(document.querySelector('.sector-analysis')).toBeInTheDocument()
  })

  it('renders period toggle buttons', () => {
    render(<SectorAnalysis />)
    // Use getAllByText since '1W', '1M', '3M' also appear as table column headers
    expect(screen.getAllByText('1W').length).toBeGreaterThan(0)
    expect(screen.getAllByText('1M').length).toBeGreaterThan(0)
    expect(screen.getAllByText('3M').length).toBeGreaterThan(0)
    // Specifically verify period-toggle buttons exist
    const buttons = document.querySelectorAll('.period-toggle button')
    expect(buttons.length).toBe(3)
  })

  it('1M period toggle is active by default', () => {
    render(<SectorAnalysis />)
    const buttons = document.querySelectorAll('.period-toggle button')
    const activeButton = Array.from(buttons).find(btn => btn.classList.contains('active'))
    expect(activeButton?.textContent).toBe('1M')
  })

  it('renders sector ranking table with sector names', () => {
    render(<SectorAnalysis />)
    expect(screen.getByText('Technology')).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
  })

  it('does not render detail panel initially (no sector selected)', () => {
    render(<SectorAnalysis />)
    expect(document.querySelector('.sector-detail-panel')).not.toBeInTheDocument()
  })
})

describe('SectorAnalysis — sector selection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCrossTabParams = null
  })

  it('shows detail panel when a sector row is clicked', async () => {
    const user = userEvent.setup()
    render(<SectorAnalysis />)
    await user.click(screen.getByText('Technology'))
    expect(document.querySelector('.sector-detail-panel')).toBeInTheDocument()
  })

  it('shows detail panel with correct sector name after click', async () => {
    const user = userEvent.setup()
    render(<SectorAnalysis />)
    await user.click(screen.getByText('Technology'))
    const panel = document.querySelector('.sector-detail-panel')!
    expect(within(panel as HTMLElement).getByText('Technology')).toBeInTheDocument()
  })
})

describe('SectorAnalysis — period toggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCrossTabParams = null
  })

  it('changes active period when 1W button is clicked', async () => {
    const user = userEvent.setup()
    render(<SectorAnalysis />)
    // Click the button inside .period-toggle, not the table header
    const periodToggle = document.querySelector('.period-toggle')!
    const btn1W = Array.from(periodToggle.querySelectorAll('button')).find(b => b.textContent === '1W')!
    await user.click(btn1W)
    const buttons = document.querySelectorAll('.period-toggle button')
    const activeButton = Array.from(buttons).find(btn => btn.classList.contains('active'))
    expect(activeButton?.textContent).toBe('1W')
  })

  it('changes active period when 3M button is clicked', async () => {
    const user = userEvent.setup()
    render(<SectorAnalysis />)
    const periodToggle = document.querySelector('.period-toggle')!
    const btn3M = Array.from(periodToggle.querySelectorAll('button')).find(b => b.textContent === '3M')!
    await user.click(btn3M)
    const buttons = document.querySelectorAll('.period-toggle button')
    const activeButton = Array.from(buttons).find(btn => btn.classList.contains('active'))
    expect(activeButton?.textContent).toBe('3M')
  })
})

describe('SectorAnalysis — cross-tab navigation', () => {
  it('auto-selects sector from crossTabParams on mount', () => {
    mockCrossTabParams = { sectorName: 'Technology' }
    render(<SectorAnalysis />)
    // Detail panel should be shown with the pre-selected sector
    expect(document.querySelector('.sector-detail-panel')).toBeInTheDocument()
  })

  it('calls clearCrossTabParams after handling cross-tab navigation', () => {
    mockCrossTabParams = { sectorName: 'Technology' }
    render(<SectorAnalysis />)
    expect(mockClearCrossTabParams).toHaveBeenCalled()
  })
})

describe('SectorAnalysis — sorting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCrossTabParams = null
  })

  it('clicking column header changes sort', async () => {
    const user = userEvent.setup()
    render(<SectorAnalysis />)
    // Click RS Avg column header in the table (the th element)
    const headers = document.querySelectorAll('.sector-ranking-table th')
    const rsAvgHeader = Array.from(headers).find(th => th.textContent?.includes('RS Avg'))
    expect(rsAvgHeader).toBeTruthy()
    await user.click(rsAvgHeader!)
    // Sort arrow should now appear on RS Avg column
    expect(rsAvgHeader!.querySelector('.sort-arrow')).toBeInTheDocument()
  })
})

// R6: Market filter toggle
describe('SectorAnalysis — market filter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCrossTabParams = null
  })

  it('renders market toggle buttons', () => {
    render(<SectorAnalysis />)
    expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /kospi/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /kosdaq/i })).toBeInTheDocument()
  })

  it('All market button is active by default', () => {
    render(<SectorAnalysis />)
    const allBtn = screen.getByRole('button', { name: /all/i })
    expect(allBtn.classList.contains('active')).toBe(true)
  })

  it('clicking KOSPI button sets it as active', async () => {
    const user = userEvent.setup()
    render(<SectorAnalysis />)
    const kospiBtn = screen.getByRole('button', { name: /kospi/i })
    await user.click(kospiBtn)
    expect(kospiBtn.classList.contains('active')).toBe(true)
  })

  it('clicking KOSDAQ button sets it as active', async () => {
    const user = userEvent.setup()
    render(<SectorAnalysis />)
    const kosdaqBtn = screen.getByRole('button', { name: /kosdaq/i })
    await user.click(kosdaqBtn)
    expect(kosdaqBtn.classList.contains('active')).toBe(true)
  })
})
