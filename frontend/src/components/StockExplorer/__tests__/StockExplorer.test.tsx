// RED: Tests for StockExplorer container component
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { StageOverviewResponse } from '../../../types/stage'

// Mock stage API
vi.mock('../../../api/stage', () => ({
  fetchStageOverview: vi.fn(),
}))

// Mock TabContext
const mockNavigateToTab = vi.fn()
const mockClearCrossTabParams = vi.fn()
let mockCrossTabParams: { sectorName?: string; stockCodes?: string[] } | null = null

vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({
    navigateToTab: mockNavigateToTab,
    crossTabParams: mockCrossTabParams,
    clearCrossTabParams: mockClearCrossTabParams,
  }),
}))

import { fetchStageOverview } from '../../../api/stage'
import { StockExplorer } from '../StockExplorer'

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
}

describe('StockExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCrossTabParams = null
    vi.mocked(fetchStageOverview).mockResolvedValue(mockStageData)
  })

  it('should fetch stage overview on mount', async () => {
    render(<StockExplorer />)

    await waitFor(() => {
      expect(fetchStageOverview).toHaveBeenCalledTimes(1)
    })
  })

  it('should show loading state initially', () => {
    vi.mocked(fetchStageOverview).mockReturnValue(new Promise(() => {})) // never resolves

    render(<StockExplorer />)

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('should show stage distribution bar after data loads', async () => {
    render(<StockExplorer />)

    await waitFor(() => {
      // Stage distribution bar should be visible
      expect(screen.getByRole('button', { name: /stage 1/i })).toBeInTheDocument()
    })
  })

  it('should show stock table after data loads', async () => {
    render(<StockExplorer />)

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
      expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    })
  })

  it('should show error message if fetch fails', async () => {
    vi.mocked(fetchStageOverview).mockRejectedValue(new Error('Failed to fetch'))

    render(<StockExplorer />)

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch/i)).toBeInTheDocument()
    })
  })

  it('should apply sector filter from crossTabParams', async () => {
    mockCrossTabParams = { sectorName: 'Healthcare' }

    render(<StockExplorer />)

    await waitFor(() => {
      expect(mockClearCrossTabParams).toHaveBeenCalled()
    })

    // Sector filter chip should be shown
    await waitFor(() => {
      expect(screen.getByText('Healthcare')).toBeInTheDocument()
    })
  })

  it('should enable View Charts button when stocks are selected', async () => {
    const user = userEvent.setup()
    render(<StockExplorer />)

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
    })

    // Initially disabled
    const viewChartsBtn = screen.getByRole('button', { name: /view charts/i })
    expect(viewChartsBtn).toBeDisabled()

    // Select a stock
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])

    // Now should be enabled
    expect(viewChartsBtn).not.toBeDisabled()
  })

  it('should navigate to chart-grid with selected stock codes on View Charts click', async () => {
    const user = userEvent.setup()
    render(<StockExplorer />)

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
    })

    // Select a stock
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])

    // Click View Charts
    await user.click(screen.getByRole('button', { name: /view charts/i }))

    expect(mockNavigateToTab).toHaveBeenCalledWith('chart-grid', {
      stockCodes: ['005930'],
    })
  })

  it('should filter table by stage when distribution bar segment is clicked', async () => {
    const user = userEvent.setup()
    render(<StockExplorer />)

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
