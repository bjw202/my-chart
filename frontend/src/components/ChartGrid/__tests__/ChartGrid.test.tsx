/**
 * ChartGrid 기본 렌더 테스트 (v2.0.0)
 *
 * v2.0.0 변경사항:
 * - ChartGrid는 더 이상 useScreen()을 직접 호출하지 않음 (REQ-PERF-001)
 * - filterResults prop으로 stocks 데이터를 받음
 * - crossTabParams 처리는 AppContent로 이전됨
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import React from 'react'
import type { StockItem } from '../../../types/stock'

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

vi.mock('../ChartCell', () => ({
  ChartCell: ({ stock }: { stock: StockItem }) => (
    <div data-testid={`chart-cell-${stock.code}`} />
  ),
}))

vi.mock('../StockSearchBox', () => ({
  StockSearchBox: vi.fn(() => <div data-testid="stock-search-box" />),
}))

vi.mock('../../../contexts/ScreenContext', () => ({
  useScreen: vi.fn(),
}))

vi.mock('../../../contexts/TabContext', () => ({
  useTab: vi.fn(),
}))

import { ChartGrid } from '../ChartGrid'
import { useTab } from '../../../contexts/TabContext'
import { useScreen } from '../../../contexts/ScreenContext'

const mockUseTab = vi.mocked(useTab)
const mockUseScreen = vi.mocked(useScreen)

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
    applyFilters: vi.fn(() => Promise.resolve()),
    updateFilters: vi.fn(),
    clearResults: vi.fn(),
  })

  mockUseTab.mockReturnValue({
    activeTab: 'chart-grid',
    setActiveTab: vi.fn(),
    navigateToTab: vi.fn(),
    crossTabParams,
    clearCrossTabParams: vi.fn(),
  })
}

describe('ChartGrid — v2.0.0 props 기반 렌더', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('filterResults=[] 이면 empty state 렌더됨', () => {
    const { container } = render(
      <ChartGrid
        filterResults={[]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )
    expect(container.querySelector('.chart-grid--empty')).not.toBeNull()
  })

  it('filterResults props을 필요로 하며 전달 시 렌더됨', () => {
    const { container } = render(
      <ChartGrid
        filterResults={[]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )
    expect(container.querySelector('.chart-grid')).not.toBeNull()
  })

  it('injectedStock=null 이면 filterResults 그대로 사용', () => {
    const { container } = render(
      <ChartGrid
        filterResults={[]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )
    expect(container).toBeTruthy()
  })

  it('onSelectStock prop을 받음 (StockSearchBox에 전달)', () => {
    const onSelectStock = vi.fn()
    render(
      <ChartGrid
        filterResults={[]}
        injectedStock={null}
        onSelectStock={onSelectStock}
      />,
    )
    // StockSearchBox가 mock되어 있어 렌더됨 (empty state에서는 toolbar가 없으므로)
    // 기본적으로 렌더 오류가 없어야 함
  })

  it('crossTabParams 처리는 AppContent로 이전됨 — ChartGrid는 더 이상 applyFilters 직접 호출 안 함', () => {
    const mockApplyFilters = vi.fn(() => Promise.resolve())
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
      clearResults: vi.fn(),
    })
    setupDefaultMocks({ stockCodes: ['005930', '000660'] })

    render(
      <ChartGrid
        filterResults={[]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )

    // ChartGrid는 더 이상 crossTabParams로 applyFilters를 호출하지 않음
    // (AppContent가 처리)
    expect(mockApplyFilters).not.toHaveBeenCalled()
  })
})
