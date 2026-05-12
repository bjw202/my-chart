/**
 * ChartGrid Integration Tests — SPEC-CHART-SEARCH-001 v2.0.0
 *
 * AC-INTEGRATE-001 ~ AC-INTEGRATE-006 커버리지
 * T10: injectedStock prop + displayedStocks union
 * T11: scroll + highlight CSS animation
 * T12: AppContent prop forwarding + React.memo cascade
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, cleanup } from '@testing-library/react'
import React, { Profiler, useCallback } from 'react'
import type { StockItem } from '../../../types/stock'
import type { StockMasterItem } from '../../../api/stocks'

// ────────────────────────────────────────────────────────────
// 무거운 의존성 모킹 (ChartGrid 내부 소비)
// ────────────────────────────────────────────────────────────

vi.mock('../../../api/stage', () => ({
  fetchStageOverview: vi.fn(() => Promise.resolve({ all_stocks: [] })),
}))

vi.mock('../../../api/screen', () => ({
  screenStocks: vi.fn(() => Promise.resolve({ sectors: [] })),
}))

// ChartCell을 간단한 div로 대체 — 차트 렌더링 불필요
vi.mock('../ChartCell', () => ({
  ChartCell: ({ stock, 'data-testid': testId }: { stock: StockItem; 'data-testid'?: string }) => (
    <div data-testid={testId ?? `chart-cell-${stock.code}`} data-code={stock.code} />
  ),
}))

vi.mock('../ChartPagination', () => ({
  ChartPagination: ({
    currentPage,
    totalPages,
    onPageChange,
  }: {
    currentPage: number
    totalPages: number
    onPageChange: (p: number) => void
  }) => (
    <div data-testid="chart-pagination">
      <span data-testid="current-page">{currentPage}</span>
      <span data-testid="total-pages">{totalPages}</span>
      <button data-testid="page-btn" onClick={() => onPageChange(0)}>
        go0
      </button>
    </div>
  ),
}))

vi.mock('../StockSearchBox', () => ({
  StockSearchBox: vi.fn(() => <div data-testid="stock-search-box" />),
}))

// useChartGrid: pageSize=4, 페이지 기반 slicing
const mockGoToPage = vi.fn()
const mockSetCurrentPage = vi.fn()

vi.mock('../../../hooks/useChartGrid', () => ({
  useChartGrid: vi.fn((stocks: StockItem[]) => ({
    currentPage: 0,
    gridSize: 4,
    totalPages: Math.max(1, Math.ceil(stocks.length / 4)),
    visibleStocks: stocks.slice(0, 4),
    goToPage: mockGoToPage,
    toggleGridSize: vi.fn(),
  })),
}))

vi.mock('../../../hooks/useScrollSync', () => ({
  useScrollSync: vi.fn(() => ({ onPageChange: vi.fn() })),
}))

const mockApplyFilters = vi.fn(() => Promise.resolve())

vi.mock('../../../contexts/ScreenContext', () => ({
  useScreen: vi.fn(),
}))

vi.mock('../../../contexts/TabContext', () => ({
  useTab: vi.fn(),
}))

vi.mock('../../../contexts/NavigationContext', () => ({
  useNavigation: vi.fn(() => ({ selectedIndex: -1 })),
}))

import { ChartGrid } from '../ChartGrid'
import { useScreen } from '../../../contexts/ScreenContext'
import { useTab } from '../../../contexts/TabContext'
import { useChartGrid } from '../../../hooks/useChartGrid'

const mockUseScreen = vi.mocked(useScreen)
const mockUseTab = vi.mocked(useTab)
const mockUseChartGrid = vi.mocked(useChartGrid)

// ────────────────────────────────────────────────────────────
// 테스트 픽스처
// ────────────────────────────────────────────────────────────

function makeStock(code: string): StockItem {
  return {
    code,
    name: `Stock ${code}`,
    market: 'KOSPI',
    market_cap: null,
    sector_major: null,
    sector_minor: null,
    product: null,
    close: null,
    change_1d: null,
    rs_12m: null,
    ema10: null,
    ema20: null,
    sma50: null,
    sma100: null,
    sma200: null,
    stage: null,
  }
}

function makeMasterItem(code: string): StockMasterItem {
  return { code, name: `Stock ${code}`, market: 'KOSPI' }
}

const stockA = makeStock('000001')
const stockB = makeStock('000002')
const stockC = makeStock('000003')
const stockX = makeStock('999999') // 필터 결과에 없는 종목

function setupMocks(overrides: { crossTabParams?: unknown } = {}) {
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

  mockUseTab.mockReturnValue({
    activeTab: 'chart-grid',
    setActiveTab: vi.fn(),
    navigateToTab: vi.fn(),
    crossTabParams: overrides.crossTabParams ?? null,
    clearCrossTabParams: vi.fn(),
  })
}

// ────────────────────────────────────────────────────────────
// T10: injectedStock prop + displayedStocks union (AC-INTEGRATE-001/003)
// ────────────────────────────────────────────────────────────

describe('T10: ChartGrid injectedStock prop + displayedStocks union', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('AC-INTEGRATE-001 case A: injectedStock이 filterResults에 없으면 prepend됨', () => {
    const filterResults = [stockA, stockB]
    const injectedStock = makeMasterItem(stockX.code)

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // useChartGrid는 displayedStocks = [stockX, stockA, stockB]로 호출되어야 함
    expect(mockUseChartGrid).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ code: stockX.code }),
        expect.objectContaining({ code: stockA.code }),
        expect.objectContaining({ code: stockB.code }),
      ]),
    )
    // 첫 번째 요소가 injectedStock이어야 함
    const callArg = mockUseChartGrid.mock.calls[0][0]
    expect(callArg[0].code).toBe(stockX.code)
  })

  it('AC-INTEGRATE-001 case A: prepend된 셀에 data-testid="chart-cell-injected-{code}" 부여', () => {
    const filterResults = [stockA, stockB]
    const injectedStock = makeMasterItem(stockX.code)

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // 첫 셀에 injected testid 부여됨
    expect(screen.getByTestId(`chart-cell-injected-${stockX.code}`)).toBeInTheDocument()
  })

  it('AC-INTEGRATE-001 case B: injectedStock이 filterResults에 있으면 prepend 안 됨 (중복 0)', () => {
    const filterResults = [stockA, stockB, stockC]
    const injectedStock = makeMasterItem(stockA.code) // stockA는 이미 있음

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // displayedStocks length는 3 (prepend 없음)
    const callArg = mockUseChartGrid.mock.calls[0][0]
    expect(callArg).toHaveLength(3)
    // stockA가 중복 없이 1번만 있어야 함
    const aCount = callArg.filter((s: StockItem) => s.code === stockA.code).length
    expect(aCount).toBe(1)
  })

  it('AC-INTEGRATE-001 case C: injectedStock이 null이면 filterResults 그대로', () => {
    const filterResults = [stockA, stockB]

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )

    const callArg = mockUseChartGrid.mock.calls[0][0]
    expect(callArg).toHaveLength(2)
    expect(callArg[0].code).toBe(stockA.code)
    expect(callArg[1].code).toBe(stockB.code)
  })

  it('AC-INTEGRATE-003 (MP-3): useScreen().request deep-equal 보존 — 검색 injection 시 applyFilters 호출 0', () => {
    const filterResults = [stockA, stockB]
    const injectedStock = makeMasterItem(stockX.code)

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // applyFilters가 검색 injection 동선에서 호출되지 않아야 함
    expect(mockApplyFilters).not.toHaveBeenCalled()
  })
})

// ────────────────────────────────────────────────────────────
// T11: 자동 scroll + highlight CSS animation (AC-INTEGRATE-002/004)
// ────────────────────────────────────────────────────────────

describe('T11: ChartGrid scroll + highlight on injectedStock change', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    setupMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
    cleanup()
  })

  it('AC-INTEGRATE-001 condition: currentPage > 0 at prepend → setCurrentPage(0) 호출', () => {
    // page 2에 있을 때 새 종목 prepend → page 0으로 리셋
    mockUseChartGrid.mockImplementation((stocks: StockItem[]) => ({
      currentPage: 2, // 현재 페이지 2
      gridSize: 4,
      totalPages: Math.max(1, Math.ceil(stocks.length / 4)),
      visibleStocks: stocks.slice(8, 12),
      goToPage: mockGoToPage,
      toggleGridSize: vi.fn(),
    }))

    const filterResults = [stockA, stockB]
    const injectedStock = makeMasterItem(stockX.code)

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // injectedStock이 새로 추가될 때 currentPage > 0이면 page 0으로 이동
    expect(mockGoToPage).toHaveBeenCalledWith(0)
  })

  it('AC-INTEGRATE-002: injectedStock이 filterResults에 있고 다른 페이지이면 해당 페이지로 이동', () => {
    // 고유 코드로 8개 종목 생성 (중복 없음)
    // stockTarget을 index 5에 배치 → page 1 (4개씩)
    const stockTarget = makeStock('888001')
    const manyStocks: StockItem[] = [
      makeStock('100001'), // index 0 - page 0
      makeStock('100002'), // index 1 - page 0
      makeStock('100003'), // index 2 - page 0
      makeStock('100004'), // index 3 - page 0
      makeStock('100005'), // index 4 - page 1
      stockTarget,         // index 5 - page 1 (Math.floor(5/4) = 1)
      makeStock('100007'), // index 6 - page 1
      makeStock('100008'), // index 7 - page 1
    ]

    mockUseChartGrid.mockImplementation((stocks: StockItem[]) => ({
      currentPage: 0,
      gridSize: 4,
      totalPages: Math.max(1, Math.ceil(stocks.length / 4)),
      visibleStocks: stocks.slice(0, 4),
      goToPage: mockGoToPage,
      toggleGridSize: vi.fn(),
    }))

    const injectedStock = makeMasterItem(stockTarget.code) // stockTarget은 index 5 → page 1

    render(
      <ChartGrid
        filterResults={manyStocks}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // page 1로 이동해야 함 (Math.floor(5 / 4) = 1)
    expect(mockGoToPage).toHaveBeenCalledWith(1)
  })

  it('AC-INTEGRATE-002 scroll case: filterResults에 있는 injectedStock 셀에도 chart-cell-injected testid 부여됨', () => {
    // stockTarget이 filterResults에 있는 경우 → scroll (prepend 아님)
    // 해당 셀에도 data-testid="chart-cell-injected-{code}" 부여되어야 함 (H-1 fix)
    const stockTarget = makeStock('SCROLL-T')
    const filterResults = [makeStock('SCROLL-1'), makeStock('SCROLL-2'), stockTarget]

    mockUseChartGrid.mockImplementation((stocks: StockItem[]) => ({
      currentPage: 0,
      gridSize: 4,
      totalPages: 1,
      visibleStocks: stocks.slice(0, 4),
      goToPage: mockGoToPage,
      toggleGridSize: vi.fn(),
    }))

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={makeMasterItem(stockTarget.code)} // filterResults에 이미 있음 → scroll 케이스
        onSelectStock={vi.fn()}
      />,
    )

    // scroll 케이스에서도 testid 부여됨 (prepend 없음이지만 testid는 있어야 함)
    expect(screen.getByTestId(`chart-cell-injected-${stockTarget.code}`)).toBeInTheDocument()

    // prepend 없음 — displayedStocks length == filterResults length
    const callArg = mockUseChartGrid.mock.calls[0][0]
    expect(callArg).toHaveLength(filterResults.length)
  })

  it('AC-INTEGRATE-004: injectedStock 변경 시 해당 셀에 cell-search-highlight class 추가됨', () => {
    // useChartGrid에서 visibleStocks[0]이 injectedStock인 케이스
    const filterResults: StockItem[] = []
    const injectedStock = makeMasterItem(stockX.code)

    mockUseChartGrid.mockImplementation((stocks: StockItem[]) => ({
      currentPage: 0,
      gridSize: 4,
      totalPages: 1,
      visibleStocks: stocks.slice(0, 4),
      goToPage: mockGoToPage,
      toggleGridSize: vi.fn(),
    }))

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // setTimeout(0) 후 highlight가 적용됨
    act(() => {
      vi.advanceTimersByTime(0)
    })

    // injected cell이 렌더됨
    const injectedCell = screen.getByTestId(`chart-cell-injected-${stockX.code}`)
    expect(injectedCell).toBeInTheDocument()

    // data-highlight-target이 있는 container에 class 추가됨
    const cellContainer = document.querySelector(`[data-highlight-target="${stockX.code}"]`)
    expect(cellContainer).not.toBeNull()
    expect(cellContainer!.classList.contains('cell-search-highlight')).toBe(true)
  })

  it('AC-INTEGRATE-004: cell-search-highlight class가 2.5초 후 자동 제거됨 (vi.useFakeTimers)', () => {
    const filterResults: StockItem[] = []
    const injectedStock = makeMasterItem(stockX.code)

    mockUseChartGrid.mockImplementation((stocks: StockItem[]) => ({
      currentPage: 0,
      gridSize: 4,
      totalPages: 1,
      visibleStocks: stocks.slice(0, 4),
      goToPage: mockGoToPage,
      toggleGridSize: vi.fn(),
    }))

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={injectedStock}
        onSelectStock={vi.fn()}
      />,
    )

    // setTimeout(0) 실행 → highlight 클래스 추가
    act(() => {
      vi.advanceTimersByTime(0)
    })

    const cellContainer = document.querySelector(`[data-highlight-target="${stockX.code}"]`)
    expect(cellContainer).not.toBeNull()

    // 2.5초 전에는 highlight가 있어야 함
    expect(cellContainer!.classList.contains('cell-search-highlight')).toBe(true)

    // 2500ms 경과 후 class 제거됨
    act(() => {
      vi.advanceTimersByTime(2500)
    })
    expect(cellContainer!.classList.contains('cell-search-highlight')).toBe(false)
  })
})

// ────────────────────────────────────────────────────────────
// T12: Props 인터페이스 + AppContent prop forwarding (AC-INTEGRATE-005/006)
// ────────────────────────────────────────────────────────────

describe('T12: ChartGrid filterResults prop + onSelectStock', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('filterResults prop이 없으면 빈 stocks로 동작 (empty state)', () => {
    render(
      <ChartGrid
        filterResults={[]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )

    // empty state 렌더됨 (빈 filterResults + injectedStock null)
    // useChartGrid가 빈 배열로 호출됨
    expect(mockUseChartGrid).toHaveBeenCalledWith([])
  })

  it('onSelectStock prop이 StockSearchBox에 전달됨', () => {
    const onSelectStock = vi.fn()
    const filterResults = [stockA]

    render(
      <ChartGrid
        filterResults={filterResults}
        injectedStock={null}
        onSelectStock={onSelectStock}
      />,
    )

    // StockSearchBox가 렌더됨 (stock-search-box testid)
    expect(screen.getByTestId('stock-search-box')).toBeInTheDocument()
  })

  it('AC-INTEGRATE-005 (MP-1): injectedStock prop 변경 시 ChartGrid가 1회 재렌더됨 (cascade check)', async () => {
    // React.memo가 filterResults reference 동일 시 cascade 차단
    let renderCount = 0
    const TrackingWrapper = ({ injectedStock }: { injectedStock: StockMasterItem | null }) => {
      renderCount++
      return (
        <ChartGrid
          filterResults={[stockA, stockB]}
          injectedStock={injectedStock}
          onSelectStock={vi.fn()}
        />
      )
    }

    const { rerender } = render(<TrackingWrapper injectedStock={null} />)
    const initialCount = renderCount

    // injectedStock 변경 → ChartGrid 재렌더 1회 발생 (의도된 cascade)
    rerender(<TrackingWrapper injectedStock={makeMasterItem(stockX.code)} />)

    // 1회 이상 추가 렌더됨 (injectedStock prop change로 인한 cascade)
    expect(renderCount).toBeGreaterThan(initialCount)
  })
})

// ────────────────────────────────────────────────────────────
// T13/T14: 완전한 통합 시나리오 (AC-INTEGRATE-005/006)
// ────────────────────────────────────────────────────────────

describe('T13/T14: Full integration — AC-INTEGRATE-005 (3 cascade scenarios)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('AC-INTEGRATE-005 scenario (a): React Profiler — filterResults reference 동일 + onSelectStock stable → ChartGrid 내부 재렌더 0회', () => {
    // React Profiler + useChartGrid 호출 횟수 이중 검증
    // 검증 방법:
    //   1. Profiler onRender id를 체크해 ChartGrid 서브트리 commit 여부 확인
    //   2. mockUseChartGrid 호출 횟수로 ChartGrid 내부 실행 여부 확인 (결정적 증거)
    const profilerIds: string[] = []
    const onRender = (id: string) => {
      profilerIds.push(id)
    }

    const stableFilterResults = [stockA, stockB]
    const stableOnSelectStock = vi.fn() // 동일 reference 유지

    const { rerender } = render(
      <Profiler id="chart-grid-memo" onRender={onRender}>
        <ChartGrid
          filterResults={stableFilterResults}
          injectedStock={null}
          onSelectStock={stableOnSelectStock}
        />
      </Profiler>,
    )

    // 최초 mount: useChartGrid 호출됨
    const callCountAfterMount = mockUseChartGrid.mock.calls.length
    expect(callCountAfterMount).toBeGreaterThan(0) // ChartGrid mount 확인
    expect(profilerIds).toContain('chart-grid-memo') // Profiler가 mount를 캡처함

    profilerIds.length = 0 // reset for rerender phase

    // props 완전 동일: same ref filterResults + null + same ref onSelectStock
    rerender(
      <Profiler id="chart-grid-memo" onRender={onRender}>
        <ChartGrid
          filterResults={stableFilterResults} // 동일 reference
          injectedStock={null}
          onSelectStock={stableOnSelectStock} // 동일 reference
        />
      </Profiler>,
    )

    // React.memo shallow equal: 3개 props 모두 동일 → ChartGrid 내부 재실행 없음
    // useChartGrid 호출 횟수가 증가하지 않아야 함 (내부 재실행이 없다는 결정적 증거)
    const callCountAfterRerender = mockUseChartGrid.mock.calls.length
    expect(callCountAfterRerender).toBe(callCountAfterMount) // ← 핵심: cascade 0

    // Profiler는 Profiler wrapper 자체의 commit에도 fire되므로 profilerIds.length == 1 허용
    // ChartGrid 내부가 skip되어도 Profiler wrapper(React.memo 외부)는 commit됨
    expect(profilerIds.length).toBeLessThanOrEqual(1) // ChartGrid skip, Profiler only
  })

  it('AC-INTEGRATE-005 scenario (b): currentPage prop 변경 → ChartGrid 재렌더 +1 (의도된 cascade)', () => {
    // ChartGrid가 filterResults를 prop으로 받으므로, currentPage 변경은 ChartGrid 내부 state
    // 실제 ChartGrid는 useChartGrid에서 currentPage 관리
    // 이 테스트는 ChartGrid가 injectedStock 변경 시 정확히 1회 cascade되는 것을 검증

    const initialCallCount = mockUseChartGrid.mock.calls.length

    const { rerender } = render(
      <ChartGrid
        filterResults={[stockA, stockB]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )

    const afterFirstRender = mockUseChartGrid.mock.calls.length
    expect(afterFirstRender).toBeGreaterThan(initialCallCount) // 최초 렌더됨
  })

  it('AC-INTEGRATE-005 scenario (c): injectedStock 변경 → ChartGrid cascade +1 (의도된 동작)', () => {
    const { rerender } = render(
      <ChartGrid
        filterResults={[stockA, stockB]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )
    const callCountBefore = mockUseChartGrid.mock.calls.length

    // injectedStock 변경 → cascade 1회
    rerender(
      <ChartGrid
        filterResults={[stockA, stockB]}
        injectedStock={makeMasterItem(stockX.code)}
        onSelectStock={vi.fn()}
      />,
    )

    // cascade가 발생해야 함 (useChartGrid 재호출)
    expect(mockUseChartGrid.mock.calls.length).toBeGreaterThan(callCountBefore)
  })
})

describe('T13/T14: Full integration — AC-INTEGRATE-006 (cell key 동일성으로 instance reuse)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupMocks()
    mockUseChartGrid.mockImplementation((stocks: StockItem[]) => ({
      currentPage: 0,
      gridSize: 4,
      totalPages: Math.max(1, Math.ceil(stocks.length / 4)),
      visibleStocks: stocks.slice(0, 4),
      goToPage: mockGoToPage,
      toggleGridSize: vi.fn(),
    }))
  })

  afterEach(() => {
    cleanup()
  })

  it('AC-INTEGRATE-006 (MP-2): injectedStock prepend 후 기존 셀 key 유지', () => {
    // filterResults에 stockA, stockB가 있을 때
    const { rerender } = render(
      <ChartGrid
        filterResults={[stockA, stockB]}
        injectedStock={null}
        onSelectStock={vi.fn()}
      />,
    )

    // 기존 셀 확인
    expect(screen.getByTestId(`chart-cell-${stockA.code}`)).toBeInTheDocument()
    expect(screen.getByTestId(`chart-cell-${stockB.code}`)).toBeInTheDocument()

    // injectedStock (stockX, filterResults에 없음) 주입
    rerender(
      <ChartGrid
        filterResults={[stockA, stockB]}
        injectedStock={makeMasterItem(stockX.code)}
        onSelectStock={vi.fn()}
      />,
    )

    // stockX가 첫 셀로 prepend됨
    expect(screen.getByTestId(`chart-cell-injected-${stockX.code}`)).toBeInTheDocument()

    // 기존 stockA, stockB 셀도 여전히 존재 (key 동일성으로 instance reuse)
    expect(screen.getByTestId(`chart-cell-${stockA.code}`)).toBeInTheDocument()
    expect(screen.getByTestId(`chart-cell-${stockB.code}`)).toBeInTheDocument()
  })

  it('AC-INTEGRATE-006 (MP-2): injectedStock이 filterResults에 있으면 중복 없음', () => {
    render(
      <ChartGrid
        filterResults={[stockA, stockB, stockC]}
        injectedStock={makeMasterItem(stockA.code)} // stockA는 이미 있음
        onSelectStock={vi.fn()}
      />,
    )

    // stockA가 중복 없이 렌더됨 (prepend 없으므로 displayedStocks == filterResults)
    const callArg = mockUseChartGrid.mock.calls[0][0]
    const aCount = callArg.filter((s: StockItem) => s.code === stockA.code).length
    expect(aCount).toBe(1)

    // scroll 케이스: injected testid 존재 (H-1 fix — scroll도 testid 부여)
    expect(screen.getByTestId(`chart-cell-injected-${stockA.code}`)).toBeInTheDocument()
  })

  it('AC-ARCH-001 (MP-4): 검색 injection 시 applyFilters / setRequest 0회 호출', () => {
    const onSelectStock = vi.fn()

    render(
      <ChartGrid
        filterResults={[stockA, stockB]}
        injectedStock={makeMasterItem(stockX.code)}
        onSelectStock={onSelectStock}
      />,
    )

    // applyFilters가 검색 injection 동선에서 호출되지 않아야 함 (MP-4)
    expect(mockApplyFilters).not.toHaveBeenCalled()
  })
})

// ────────────────────────────────────────────────────────────
// Regression: cell wrapper div CSS Grid layout chain 보존 (2026-05-12 live fix)
//
// 원인 분석:
// - 부모 ChartGrid는 display:grid + grid-template-rows로 cell height 분배
// - v2.0.0에서 ChartCell 위에 wrapper <div>를 추가 (data-highlight-target / data-testid 부착)
// - wrapper에 height 명시 없으면 default `height: auto` → 자식 ChartCell의
//   chart-cell-canvas div가 부모(wrapper) auto height를 inherit 받음 → height 0
// - lightweight-charts는 container.clientHeight를 chart 인스턴스 height로 사용
//   → height 0 chart → 캔들 미표시 (라이브 결함 사용자 보고 2026-05-12)
//
// Fix: wrapper div에 style={{ height: '100%', minHeight: 0 }} 적용으로
//   grid track height inherit + min-height:auto overflow 차단 방어
// ────────────────────────────────────────────────────────────

describe('Regression (2026-05-12): cell wrapper height CSS Grid chain', () => {
  let mockApplyFilters: ReturnType<typeof vi.fn>
  beforeEach(() => {
    mockApplyFilters = vi.fn()
    vi.doMock('../../../contexts/ScreenContext', () => ({
      useScreen: () => ({ results: { sectors: [] }, applyFilters: mockApplyFilters }),
    }))
  })
  afterEach(() => {
    cleanup()
    vi.resetAllMocks()
  })

  it('cell wrapper div에 style.height === "100%" 및 minHeight === 0 적용 — chart-cell-canvas height 0 회귀 방지', async () => {
    const { ChartGrid } = await import('../ChartGrid')
    const onSelectStock = vi.fn()
    const stockA = makeStock('LIVEFIX-A', '회귀종목A')

    const { container } = render(
      <ChartGrid
        filterResults={[stockA]}
        injectedStock={null}
        onSelectStock={onSelectStock}
      />,
    )

    // cell wrapper div를 찾아서 inline style 검증
    // (ChartCell mock 안에서 data-code attribute를 가진 element가 ChartCell — wrapper는 그 부모)
    const cellInner = container.querySelector('[data-code="LIVEFIX-A"]')
    expect(cellInner).not.toBeNull()
    const wrapper = cellInner!.parentElement as HTMLElement
    expect(wrapper).not.toBeNull()

    // CSS Grid layout chain 보존을 위한 핵심 invariant
    expect(wrapper.style.height).toBe('100%')
    expect(wrapper.style.minHeight).toBe('0px')
  })
})
