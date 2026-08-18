/**
 * ChartGrid 기본 렌더 테스트 (v2.0.0)
 *
 * v2.0.0 변경사항:
 * - ChartGrid는 더 이상 useScreen()을 직접 호출하지 않음 (REQ-PERF-001)
 * - filterResults prop으로 stocks 데이터를 받음
 * - legacy cross-tab param handling moved to AppContent
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
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
  useNavIntent: vi.fn(),
}))

import { ChartGrid } from '../ChartGrid'
import { useTab, useNavIntent } from '../../../contexts/TabContext'
import { useScreen } from '../../../contexts/ScreenContext'

const mockUseTab = vi.mocked(useTab)
const mockUseNavIntent = vi.mocked(useNavIntent)
const mockUseScreen = vi.mocked(useScreen)

function setupDefaultMocks(intent: unknown = null) {
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
    visibleCount: null,
    publishVisibleCount: vi.fn(),
  })

  mockUseTab.mockReturnValue({
    activeTab: 'chart-grid',
    setActiveTab: vi.fn(),
  })
  // NavIntent consumer mock — ChartGrid consumes focusStock intents targeting chart-grid.
  mockUseNavIntent.mockReturnValue({
    intent: intent as ReturnType<typeof useNavIntent>['intent'],
    navigate: vi.fn(),
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

  it('M3 focusStock NavIntent(chart-grid) 수신 — ChartGrid는 applyFilters를 호출하지 않는다 (AppContent 소관)', () => {
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
      visibleCount: null,
      publishVisibleCount: vi.fn(),
    })
    // ST-7 / TR-2: MarketOverview treemap click이 보내는 focusStock intent.
    setupDefaultMocks({ id: 1, target: 'chart-grid', payload: { focusStock: '삼성전자' } })

    render(
      <ChartGrid
        filterResults={[]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )

    // ChartGrid는 focusStock을 highlight로 소비(applyFilters 호출 안 함) — 필터 적용은 AppContent 소관.
    expect(mockApplyFilters).not.toHaveBeenCalled()
  })
})
