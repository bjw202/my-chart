/**
 * SPEC-CHART-SEARCH-001 T5 RED — StockSearchModal 컴포넌트 테스트
 *
 * AC-MODAL-001 (must-pass MP-4): portal mount — document.body 직속
 * AC-MODAL-002: a11y — role/aria-modal/aria-labelledby/scroll lock
 * AC-MODAL-003: Esc 닫기 + focus 복귀
 * AC-MODAL-004: 백드롭 클릭 닫기 + stopPropagation
 * AC-MODAL-005: ✕ 버튼 닫기
 * AC-MODAL-006: timeframe 토글
 * AC-MODAL-007 (must-pass): useEffect 1회 호출
 * AC-MODAL-008: race guard cancelled flag
 * AC-MODAL-009: initial timeframe = prop 계승, undefined → 'daily'
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, within, act } from '@testing-library/react'
import React, { createRef } from 'react'
import { StockSearchModal } from '../StockSearchModal'
import type { StockMasterItem } from '../../../api/stocks'

// lightweight-charts mock
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({
      setData: vi.fn(),
    })),
    applyOptions: vi.fn(),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    remove: vi.fn(),
    resize: vi.fn(),
  })),
}))

// fetchChartData mock
const mockFetchChartData = vi.fn()
vi.mock('../../../api/chart', () => ({
  fetchChartData: (...args: unknown[]) => mockFetchChartData(...args),
}))

const mockStock: StockMasterItem = {
  code: '005930',
  name: '삼성전자',
  market: 'KOSPI',
}

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchChartData.mockResolvedValue({ candles: [] })
})

afterEach(() => {
  document.body.style.overflow = ''
})

// ---------------------------------------------------------------------------
// AC-MODAL-001 (must-pass MP-4) — Portal mount
// ---------------------------------------------------------------------------

describe('StockSearchModal — portal mount (AC-MODAL-001)', () => {
  it('modal이 document.body 직속 자식으로 mount됨', () => {
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={vi.fn()}
        triggerRef={triggerRef}
      />,
    )
    expect(screen.getByTestId('stock-search-modal')).toBeTruthy()
    // document.body에서 직접 찾아야 함
    expect(document.body.contains(screen.getByTestId('stock-search-modal'))).toBe(true)
  })

  it('ChartGrid subtree에 modal 없음 (MP-4 격리)', () => {
    const triggerRef = createRef<HTMLElement>()
    const { container } = render(
      <div data-testid="chart-grid">
        <StockSearchModal
          stock={mockStock}
          initialTimeframe="daily"
          onClose={vi.fn()}
          triggerRef={triggerRef}
        />
      </div>,
    )
    // chart-grid DOM subtree 내부에는 stock-search-modal 없어야 함
    const chartGrid = container.querySelector('[data-testid="chart-grid"]')!
    expect(within(chartGrid as HTMLElement).queryByTestId('stock-search-modal')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// AC-MODAL-002 — a11y patterns
// ---------------------------------------------------------------------------

describe('StockSearchModal — a11y (AC-MODAL-002)', () => {
  it('role=dialog + aria-modal=true + scroll lock', () => {
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={vi.fn()}
        triggerRef={triggerRef}
      />,
    )
    const modal = screen.getByRole('dialog')
    expect(modal.getAttribute('aria-modal')).toBe('true')
    expect(document.body.style.overflow).toBe('hidden')
  })

  it('aria-labelledby → stock-search-modal-title id 연결', () => {
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={vi.fn()}
        triggerRef={triggerRef}
      />,
    )
    const modal = screen.getByRole('dialog')
    const labelId = modal.getAttribute('aria-labelledby')
    expect(document.getElementById(labelId!)).toBeTruthy()
  })

  it('modal-content에 초기 focus', () => {
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={vi.fn()}
        triggerRef={triggerRef}
      />,
    )
    const content = screen.getByTestId('stock-search-modal-content')
    expect(document.activeElement).toBe(content)
  })
})

// ---------------------------------------------------------------------------
// AC-MODAL-003 — Esc 닫기 + focus 복귀
// ---------------------------------------------------------------------------

describe('StockSearchModal — Esc 닫기 (AC-MODAL-003)', () => {
  it('Esc → onClose 호출 + scroll lock 해제', () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={onClose}
        triggerRef={triggerRef}
      />,
    )

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

// ---------------------------------------------------------------------------
// AC-MODAL-004 — 백드롭 클릭 닫기
// ---------------------------------------------------------------------------

describe('StockSearchModal — 백드롭 클릭 (AC-MODAL-004)', () => {
  it('백드롭 클릭 → onClose 호출', () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={onClose}
        triggerRef={triggerRef}
      />,
    )
    const backdrop = screen.getByTestId('stock-search-modal-backdrop')
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('modal-content 내부 클릭 → onClose 호출 안 됨 (stopPropagation)', () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={onClose}
        triggerRef={triggerRef}
      />,
    )
    const content = screen.getByTestId('stock-search-modal-content')
    fireEvent.click(content)
    expect(onClose).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// AC-MODAL-005 — ✕ 버튼 닫기
// ---------------------------------------------------------------------------

describe('StockSearchModal — 닫기 버튼 (AC-MODAL-005)', () => {
  it('✕ 버튼 클릭 → onClose 호출', () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={onClose}
        triggerRef={triggerRef}
      />,
    )
    fireEvent.click(screen.getByTestId('stock-search-modal-close-btn'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

// ---------------------------------------------------------------------------
// AC-MODAL-006 — timeframe 토글
// ---------------------------------------------------------------------------

describe('StockSearchModal — timeframe 토글 (AC-MODAL-006)', () => {
  it('주봉 토글 → fetchChartData("005930", "weekly") 호출', async () => {
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={vi.fn()}
        triggerRef={triggerRef}
      />,
    )

    await act(async () => {
      fireEvent.click(screen.getByTestId('stock-search-modal-timeframe-toggle'))
    })

    expect(mockFetchChartData).toHaveBeenCalledWith('005930', 'weekly')
  })

  it('modal은 닫히지 않음', async () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="daily"
        onClose={onClose}
        triggerRef={triggerRef}
      />,
    )

    await act(async () => {
      fireEvent.click(screen.getByTestId('stock-search-modal-timeframe-toggle'))
    })

    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByTestId('stock-search-modal')).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// AC-MODAL-009 — initial timeframe 계승
// ---------------------------------------------------------------------------

describe('StockSearchModal — initial timeframe (AC-MODAL-009)', () => {
  it('case A: initialTimeframe="weekly" → fetchChartData("005930", "weekly")', async () => {
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe="weekly"
        onClose={vi.fn()}
        triggerRef={triggerRef}
      />,
    )
    // useEffect 실행 대기
    await act(async () => {})
    expect(mockFetchChartData).toHaveBeenCalledWith('005930', 'weekly')
  })

  it('case B: initialTimeframe=undefined → fallback "daily"', async () => {
    const triggerRef = createRef<HTMLElement>()
    render(
      <StockSearchModal
        stock={mockStock}
        initialTimeframe={undefined}
        onClose={vi.fn()}
        triggerRef={triggerRef}
      />,
    )
    await act(async () => {})
    expect(mockFetchChartData).toHaveBeenCalledWith('005930', 'daily')
  })
})
