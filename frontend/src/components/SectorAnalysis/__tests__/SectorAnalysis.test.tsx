// RED: Specification tests for SectorAnalysis container component
import type { ReactElement } from 'react'
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

// Mock TabContext useNavIntent (M3) — navigate spy; SectorAnalysis uses it for TR-4 detail-panel button.
const mockNavigate = vi.fn()
vi.mock('../../../contexts/TabContext', () => ({
  useNavIntent: () => ({ navigate: mockNavigate, intent: null }),
}))

// Import after mocks
import { SectorAnalysis } from '../SectorAnalysis'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { SelectionProvider } from '../../../contexts/SelectionContext'

// AC-SUX-008/018 + M3: SectorAnalysis 는 AnalysisParamsContext(market/period) + SelectionContext(selectedSector) 소비.
// 실제 SelectionProvider 로 감싸 selectSector/clearSector 가 상태를 갱신하도록 한다 (TR-3/3b 검증).
function renderWithProviders(ui: ReactElement) {
  return render(
    <AnalysisParamsProvider><DataLoadProvider>
      <SelectionProvider>{ui}</SelectionProvider>
    </DataLoadProvider></AnalysisParamsProvider>,
  )
}

describe('SectorAnalysis — initial render', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  it('renders the sector-analysis container', () => {
    renderWithProviders(<SectorAnalysis />)
    expect(document.querySelector('.sector-analysis')).toBeInTheDocument()
  })

  it('renders period toggle buttons', () => {
    renderWithProviders(<SectorAnalysis />)
    // Use getAllByText since '1W', '1M', '3M' also appear as table column headers
    expect(screen.getAllByText('1W').length).toBeGreaterThan(0)
    expect(screen.getAllByText('1M').length).toBeGreaterThan(0)
    expect(screen.getAllByText('3M').length).toBeGreaterThan(0)
    // Specifically verify period-toggle buttons exist
    const buttons = document.querySelectorAll('.period-toggle button')
    expect(buttons.length).toBe(3)
  })

  it('1M period toggle is active by default', () => {
    renderWithProviders(<SectorAnalysis />)
    const buttons = document.querySelectorAll('.period-toggle button')
    const activeButton = Array.from(buttons).find(btn => btn.classList.contains('active'))
    expect(activeButton?.textContent).toBe('1M')
  })

  it('renders sector ranking table with sector names', () => {
    renderWithProviders(<SectorAnalysis />)
    expect(screen.getByText('Technology')).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
  })

  it('does not render detail panel initially (no sector selected)', () => {
    renderWithProviders(<SectorAnalysis />)
    expect(document.querySelector('.sector-detail-panel')).not.toBeInTheDocument()
  })
})

describe('SectorAnalysis — sector selection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  it('shows detail panel when a sector row is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
    await user.click(screen.getByText('Technology'))
    expect(document.querySelector('.sector-detail-panel')).toBeInTheDocument()
  })

  it('shows detail panel with correct sector name after click', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
    await user.click(screen.getByText('Technology'))
    const panel = document.querySelector('.sector-detail-panel')!
    expect(within(panel as HTMLElement).getByText('Technology')).toBeInTheDocument()
  })
})

describe('SectorAnalysis — period toggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  it('changes active period when 1W button is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
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
    renderWithProviders(<SectorAnalysis />)
    const periodToggle = document.querySelector('.period-toggle')!
    const btn3M = Array.from(periodToggle.querySelectorAll('button')).find(b => b.textContent === '3M')!
    await user.click(btn3M)
    const buttons = document.querySelectorAll('.period-toggle button')
    const activeButton = Array.from(buttons).find(btn => btn.classList.contains('active'))
    expect(activeButton?.textContent).toBe('3M')
  })
})

describe('SectorAnalysis — TR-3/TR-3b row click (REQ-SUX-009 / AC-SUX-011)', () => {
  it('TR-3: row click opens detail panel WITHOUT navigate', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
    await user.click(screen.getByText('Technology'))
    // 행 클릭은 selectedSector 설정 + 패널 오픈 — navigate 는 호출하지 않는다.
    expect(document.querySelector('.sector-detail-panel')).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('TR-3b: re-clicking the selected row clears selection + closes panel', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
    await user.click(screen.getByText('Technology'))
    expect(document.querySelector('.sector-detail-panel')).toBeInTheDocument()
    // 재클릭 — 테이블 행(첫 번째 'Technology' 매치) 클릭 → clearSector → 패널 닫힘.
    const matches = screen.getAllByText('Technology')
    await user.click(matches[0])
    expect(document.querySelector('.sector-detail-panel')).not.toBeInTheDocument()
  })
})

describe('SectorAnalysis — TR-4 detail-panel button (REQ-SUX-010 / AC-SUX-012)', () => {
  it('[이 섹터 종목 보기 →] 클릭 시 stock-explorer 로 navigate 한다', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
    await user.click(screen.getByText('Technology'))
    // 상세 패널에 버튼이 실제 렌더된다 (현행 부재 → M3 신설).
    const btn = screen.getByRole('button', { name: /view technology stocks/i })
    await user.click(btn)
    expect(mockNavigate).toHaveBeenCalledWith({ target: 'stock-explorer' })
  })
})

describe('SectorAnalysis — sorting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  it('clicking column header changes sort', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
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
    mockNavigate.mockClear()
  })

  it('renders market toggle buttons', () => {
    renderWithProviders(<SectorAnalysis />)
    expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /kospi/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /kosdaq/i })).toBeInTheDocument()
  })

  it('All market button is active by default', () => {
    renderWithProviders(<SectorAnalysis />)
    const allBtn = screen.getByRole('button', { name: /all/i })
    expect(allBtn.classList.contains('active')).toBe(true)
  })

  it('clicking KOSPI button sets it as active', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
    const kospiBtn = screen.getByRole('button', { name: /kospi/i })
    await user.click(kospiBtn)
    expect(kospiBtn.classList.contains('active')).toBe(true)
  })

  it('clicking KOSDAQ button sets it as active', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SectorAnalysis />)
    const kosdaqBtn = screen.getByRole('button', { name: /kosdaq/i })
    await user.click(kosdaqBtn)
    expect(kosdaqBtn.classList.contains('active')).toBe(true)
  })
})

// AC-SUX-008: 컨트롤 단일 인스턴스 (SM-7) — sector-analysis 화면당 period/market 토글이 각각 1개
describe('AC-SUX-008 — 컨트롤 단일 인스턴스', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  it('기간 토글 인스턴스가 정확히 1개 (getAllByTestId("period-toggle").length === 1)', () => {
    renderWithProviders(<SectorAnalysis />)
    expect(screen.getAllByTestId('period-toggle')).toHaveLength(1)
  })

  it('시장 토글 인스턴스가 정확히 1개 (getAllByTestId("market-toggle").length === 1)', () => {
    renderWithProviders(<SectorAnalysis />)
    expect(screen.getAllByTestId('market-toggle')).toHaveLength(1)
  })
})
