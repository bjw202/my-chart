// RED: Tests for StockExplorer container component
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { StageOverviewResponse } from '../../../types/stage'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'

// M6: StockExplorer 는 공용 조회 계층(DataLoadProvider)과 헤더 파라미터(AnalysisParamsProvider)를 소비한다.
// 매 호출마다 새 element 를 만든다 — 동일 element 를 rerender 하면 React 가 bail-out 한다.
const SE = () => (
  <AnalysisParamsProvider><DataLoadProvider><StockExplorer /></DataLoadProvider></AnalysisParamsProvider>
)
function renderSE() {
  return render(SE())
}

// Mock stage API
vi.mock('../../../api/stage', () => ({
  fetchStageOverview: vi.fn(),
}))

// Mock TabContext (M3: activeTab + NavIntent) + SelectionContext (selectedSector/scopeFollow)
const mockNavigate = vi.fn()
const mockSetSectorScopeFollow = vi.fn()
let mockSelectedSector: string | null = null
let mockSectorScopeFollow = true

vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({ activeTab: 'stock-explorer', setActiveTab: vi.fn() }),
  useNavIntent: () => ({ intent: null, navigate: mockNavigate }),
}))
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({
    selectedSector: mockSelectedSector,
    sectorScopeFollow: mockSectorScopeFollow,
    setSectorScopeFollow: mockSetSectorScopeFollow,
  }),
}))

import { fetchStageOverview } from '../../../api/stage'
import { StockExplorer, RETRY_DELAYS_MS } from '../StockExplorer'

const mockStageData: StageOverviewResponse = {
  distribution: { stage1: 120, stage2: 85, stage3: 45, stage4: 30, total: 280 },
  by_sector: [{ sector: 'IT', stage1: 10, stage2: 15, stage3: 5, stage4: 2 }],
  stage2_candidates: [
    {
      code: '005930',
      name: '삼성전자',
      market: 'KOSPI',
      sector_major: 'IT',
      sector_minor: '반도체',
      stage: 2,
      stage_detail: 'Stage 2 Strong',
      rs_12m: 75.5,
      chg_1m: 3.2,
      volume_ratio: 1.5,
      close: 75000,
      sma50: 72000,
      sma200: 68000,
    },
    {
      code: '000660',
      name: 'SK하이닉스',
      market: 'KOSPI',
      sector_major: 'IT',
      sector_minor: '반도체',
      stage: 2,
      stage_detail: 'Stage 2 entry',
      rs_12m: 45.0,
      chg_1m: 1.5,
      volume_ratio: 1.2,
      close: 180000,
      sma50: 175000,
      sma200: 160000,
    },
  ],
  // all_stocks: 종목 표 전체 목록. 이 픽스처는 stage2_candidates 폴백 경로를 검증하므로 빈 배열.
  all_stocks: [],
}

const originalDelays = [...RETRY_DELAYS_MS]

describe('StockExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSelectedSector = null
    mockSectorScopeFollow = true
    vi.mocked(fetchStageOverview).mockResolvedValue(mockStageData)
    RETRY_DELAYS_MS.splice(0, RETRY_DELAYS_MS.length, 0, 0, 0)
  })

  afterEach(() => {
    RETRY_DELAYS_MS.splice(0, RETRY_DELAYS_MS.length, ...originalDelays)
  })

  it('should fetch stage overview on mount', async () => {
    renderSE()

    await waitFor(() => {
      expect(fetchStageOverview).toHaveBeenCalledTimes(1)
    })
  })

  it('should show loading state initially', () => {
    vi.mocked(fetchStageOverview).mockReturnValue(new Promise(() => {})) // never resolves

    renderSE()

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('should show stage distribution bar after data loads', async () => {
    renderSE()

    await waitFor(() => {
      // Stage distribution bar should be visible
      expect(screen.getByRole('button', { name: /stage 1/i })).toBeInTheDocument()
    })
  })

  it('should show stock table after data loads', async () => {
    renderSE()

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
      expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    })
  })

  it('should show error message if fetch fails after retries', async () => {
    vi.mocked(fetchStageOverview).mockRejectedValue(new Error('Failed to fetch'))

    renderSE()

    // 재시도 지연 0ms이므로 빠르게 완료됨
    await waitFor(() => {
      expect(screen.getByText(/failed to fetch/i)).toBeInTheDocument()
    })
    // 초기 1회 + 재시도 3회 = 총 4회 호출
    expect(fetchStageOverview).toHaveBeenCalledTimes(4)
  })

  it('should apply sector filter from SelectionContext (selectedSector + scopeFollow)', async () => {
    // M3: sectorFilter = sectorScopeFollow ? selectedSector : null (AC-SUX-007).
    mockSelectedSector = 'Healthcare'
    mockSectorScopeFollow = true

    renderSE()

    // Sector filter chip should be shown
    await waitFor(() => {
      expect(screen.getByText('Healthcare')).toBeInTheDocument()
    })
  })

  it('should enable View Charts button when stocks are selected', async () => {
    const user = userEvent.setup()
    renderSE()

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
    })

    // Initially disabled
    const viewChartsBtn = screen.getByRole('button', { name: /view charts/i })
    expect(viewChartsBtn).toBeDisabled()

    // Select a stock (checkboxes[0] is header "select all", checkboxes[1] is first stock row)
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[1])

    // Now should be enabled
    expect(viewChartsBtn).not.toBeDisabled()
  })

  it('should navigate to chart-grid with selected stock codes on View Charts click', async () => {
    const user = userEvent.setup()
    renderSE()

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
    })

    // Select a stock (checkboxes[0] is header "select all", checkboxes[1] is first stock row)
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[1])

    // Click View Charts
    await user.click(screen.getByRole('button', { name: /view charts/i }))

    expect(mockNavigate).toHaveBeenCalledWith({
      target: 'chart-grid',
      payload: { stockCodes: ['005930'] },
    })
  })

  it('AC-SUX-015 / TR-16: selectedSector change resets selectedStocks (no stale count)', async () => {
    const user = userEvent.setup()
    const { rerender } = renderSE()
    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
    })
    // 2 stocks selected
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[1])
    await user.click(checkboxes[2])
    expect(screen.getByText(/2 selected/i)).toBeInTheDocument()

    // 모집단 변경: selectedSector 전환 → selectedStocks 초기화 (TR-16).
    mockSelectedSector = 'Healthcare'
    mockSectorScopeFollow = true
    rerender(SE())

    await waitFor(() => {
      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument()
    })
  })

  it('should filter table by stage when distribution bar segment is clicked', async () => {
    const user = userEvent.setup()
    renderSE()

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
    })

    // Both stocks have stage "Stage 2" initially shown.
    // Click Stage 1 filter - both should be hidden since none are Stage 1
    const s1Btn = screen.getByRole('button', { name: /stage 1/i })
    await user.click(s1Btn)

    await waitFor(() => {
      expect(screen.queryByText('삼성전자')).not.toBeInTheDocument()
    })
  })
})
