// RED: ChartGrid의 crossTabParams 수신 테스트
// R1 요구사항: crossTabParams.stockCodes가 있을 때 applyFilters를 호출하고 clearCrossTabParams를 실행해야 함
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import React from 'react'

// 무거운 의존성 모킹
vi.mock('../../../api/stage', () => ({
  fetchStageOverview: vi.fn(() => Promise.resolve({ all_stocks: [] })),
}))

vi.mock('../../../api/screen', () => ({
  screenStocks: vi.fn(() => Promise.resolve({ sectors: [] })),
}))

vi.mock('../../../hooks/useChartGrid', () => ({
  useChartGrid: vi.fn(() => ({
    currentPage: 0,
    gridSize: 4,
    totalPages: 1,
    visibleStocks: [],
    goToPage: vi.fn(),
    toggleGridSize: vi.fn(),
  })),
}))

vi.mock('../../../hooks/useScrollSync', () => ({
  useScrollSync: vi.fn(() => ({
    onPageChange: vi.fn(),
  })),
}))

vi.mock('../../../contexts/NavigationContext', () => ({
  useNavigation: () => ({ selectedIndex: -1 }),
}))

// useScreen과 useTab 모킹 (테스트마다 제어 가능하도록)
const mockApplyFilters = vi.fn(() => Promise.resolve())
const mockClearCrossTabParams = vi.fn()

vi.mock('../../../contexts/ScreenContext', () => ({
  useScreen: vi.fn(),
}))

vi.mock('../../../contexts/TabContext', () => ({
  useTab: vi.fn(),
}))

// 모킹 이후 import
import { ChartGrid } from '../ChartGrid'
import { useScreen } from '../../../contexts/ScreenContext'
import { useTab } from '../../../contexts/TabContext'

const mockUseScreen = vi.mocked(useScreen)
const mockUseTab = vi.mocked(useTab)

function setupDefaultMocks(crossTabParams = null) {
  mockUseScreen.mockReturnValue({
    filters: {
      market_cap_min: null,
      chg_1d_min: null,
      chg_1w_min: null,
      chg_1m_min: null,
      chg_3m_min: null,
      patterns: [],
      pattern_logic: 'AND',
      rs_min: null,
      markets: [],
      sectors: [],
      codes: [],
    },
    results: null,
    loading: false,
    error: null,
    applyFilters: mockApplyFilters,
    updateFilters: vi.fn(),
  })

  mockUseTab.mockReturnValue({
    activeTab: 'chart-grid',
    setActiveTab: vi.fn(),
    navigateToTab: vi.fn(),
    crossTabParams,
    clearCrossTabParams: mockClearCrossTabParams,
  })
}

describe('ChartGrid — crossTabParams 수신 (R1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('crossTabParams가 null이면 applyFilters를 호출하지 않아야 함', () => {
    setupDefaultMocks(null)
    render(<ChartGrid />)

    expect(mockApplyFilters).not.toHaveBeenCalled()
    expect(mockClearCrossTabParams).not.toHaveBeenCalled()
  })

  it('crossTabParams.stockCodes가 비어있으면 applyFilters를 호출하지 않아야 함', () => {
    setupDefaultMocks({ stockCodes: [] })
    render(<ChartGrid />)

    expect(mockApplyFilters).not.toHaveBeenCalled()
    expect(mockClearCrossTabParams).not.toHaveBeenCalled()
  })

  it('crossTabParams.stockCodes가 있으면 applyFilters를 codes와 함께 호출해야 함', async () => {
    const stockCodes = ['005930', '000660', '035420']
    setupDefaultMocks({ stockCodes })

    render(<ChartGrid />)

    await waitFor(() => {
      expect(mockApplyFilters).toHaveBeenCalledWith(
        expect.objectContaining({
          codes: stockCodes,
        })
      )
    })
  })

  it('crossTabParams.stockCodes 처리 후 clearCrossTabParams를 호출해야 함', async () => {
    const stockCodes = ['005930', '000660']
    setupDefaultMocks({ stockCodes })

    render(<ChartGrid />)

    await waitFor(() => {
      expect(mockClearCrossTabParams).toHaveBeenCalledTimes(1)
    })
  })

  it('applyFilters 호출 시 DEFAULT_SCREEN_REQUEST를 베이스로 codes만 설정해야 함', async () => {
    const stockCodes = ['005930']
    setupDefaultMocks({ stockCodes })

    render(<ChartGrid />)

    await waitFor(() => {
      expect(mockApplyFilters).toHaveBeenCalledWith({
        market_cap_min: null,
        chg_1d_min: null,
        chg_1w_min: null,
        chg_1m_min: null,
        chg_3m_min: null,
        patterns: [],
        pattern_logic: 'AND',
        rs_min: null,
        markets: [],
        sectors: [],
        codes: stockCodes,
      })
    })
  })
})
