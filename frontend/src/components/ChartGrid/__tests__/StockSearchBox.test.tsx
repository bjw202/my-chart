/**
 * SPEC-CHART-SEARCH-001 T4 RED — StockSearchBox 컴포넌트 테스트
 *
 * AC-SEARCH-001: 한글 prefix 매칭 → listbox 노출
 * AC-SEARCH-004: 초성 검색
 * AC-SEARCH-008: 0건 결과 → chart-search-empty
 * AC-SEARCH-009: 503 disabled 상태
 * AC-SEARCH-010: 키보드 navigation (ArrowDown/Up/Enter/Escape)
 * AC-ARCH-003: StockSearchBox에 useScreen/useTab 미구독
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
import { StockSearchBox } from '../StockSearchBox'

// useStockMaster mock
const mockUseStockMaster = vi.fn()
vi.mock('../../../hooks/useStockMaster', () => ({
  useStockMaster: () => mockUseStockMaster(),
}))

const mockStocks = [
  { code: '005930', name: '삼성전자', market: 'KOSPI' },
  { code: '000660', name: 'SK하이닉스', market: 'KOSPI' },
  { code: '005380', name: '현대차', market: 'KOSPI' },
  { code: '005490', name: 'POSCO홀딩스', market: 'KOSPI' },
]

const defaultMockData = {
  data: { stocks: mockStocks, generated_at: '2026-05-10T18:00:00+09:00' },
  loading: false,
  error: null,
  dispatched: true,
}

beforeEach(() => {
  vi.clearAllMocks()
  mockUseStockMaster.mockReturnValue(defaultMockData)
})

// Helper: fake timer advance wrapped in act
async function advanceDebounce(): Promise<void> {
  await act(async () => {
    vi.advanceTimersByTime(200)
  })
}

// ---------------------------------------------------------------------------
// AC-SEARCH-001 — 한글 prefix 매칭 → listbox
// ---------------------------------------------------------------------------

describe('StockSearchBox — 검색 및 listbox', () => {
  it('AC-SEARCH-001: 삼 입력 → debounce 후 삼성전자 listbox 노출', async () => {
    vi.useFakeTimers()
    const onSelect = vi.fn()
    render(<StockSearchBox onSelect={onSelect} />)

    const input = screen.getByTestId('chart-search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: '삼' } })
    })

    // debounce 전 — listbox 없음
    expect(screen.queryByTestId('chart-search-listbox')).toBeNull()

    await advanceDebounce()

    expect(screen.getByTestId('chart-search-listbox')).toBeTruthy()
    expect(screen.getByTestId('chart-search-option-005930')).toBeTruthy()
    vi.useRealTimers()
  })

  it('입력 없으면 listbox 표시 안 됨', () => {
    render(<StockSearchBox onSelect={vi.fn()} />)
    expect(screen.queryByTestId('chart-search-listbox')).toBeNull()
  })

  it('최대 8개 option 노출', async () => {
    vi.useFakeTimers()
    const manyStocks = Array.from({ length: 15 }, (_, i) => ({
      code: `00${i}000`,
      name: `삼성종목${i}`,
      market: 'KOSPI',
    }))
    mockUseStockMaster.mockReturnValue({
      ...defaultMockData,
      data: { stocks: manyStocks, generated_at: '' },
    })

    render(<StockSearchBox onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: '삼' } })
    })
    await advanceDebounce()

    const options = screen.getAllByRole('option')
    expect(options.length).toBeLessThanOrEqual(8)
    vi.useRealTimers()
  })

  // AC-SEARCH-004 — 초성 검색
  it('AC-SEARCH-004: ㅅㅅㅈㅈ 입력 → 삼성전자 노출', async () => {
    vi.useFakeTimers()
    render(<StockSearchBox onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: 'ㅅㅅㅈㅈ' } })
    })
    await advanceDebounce()

    expect(screen.getByTestId('chart-search-option-005930')).toBeTruthy()
    expect(screen.queryByTestId('chart-search-option-005380')).toBeNull()
    vi.useRealTimers()
  })

  // AC-SEARCH-008 — 0건 결과
  it('AC-SEARCH-008: 0건 결과 → chart-search-empty + aria-disabled', async () => {
    vi.useFakeTimers()
    render(<StockSearchBox onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: 'xyz존재하지않는검색어' } })
    })
    await advanceDebounce()

    const empty = screen.getByTestId('chart-search-empty')
    expect(empty).toBeTruthy()
    expect(empty.getAttribute('aria-disabled')).toBe('true')
    vi.useRealTimers()
  })
})

// ---------------------------------------------------------------------------
// AC-SEARCH-009 — 503 disabled 상태
// ---------------------------------------------------------------------------

describe('StockSearchBox — 503 disabled 상태 (AC-SEARCH-009)', () => {
  it('503 에러 → input disabled + placeholder + title', () => {
    mockUseStockMaster.mockReturnValue({
      data: null,
      loading: false,
      error: new Error('stock_meta_not_ready'),
      dispatched: true,
    })

    render(<StockSearchBox onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input')
    expect(input).toBeDisabled()
    expect(input.getAttribute('placeholder')).toBe('DB 업데이트 필요')
    expect(input.getAttribute('title')).toBe('DB 업데이트가 필요합니다')
  })
})

// ---------------------------------------------------------------------------
// AC-SEARCH-010 — 키보드 navigation
// ---------------------------------------------------------------------------

describe('StockSearchBox — 키보드 navigation (AC-SEARCH-010)', () => {
  it('ArrowDown → 첫 item 하이라이트 + aria-activedescendant', async () => {
    vi.useFakeTimers()
    render(<StockSearchBox onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: '삼' } })
    })
    await advanceDebounce()

    await act(async () => {
      fireEvent.keyDown(input, { key: 'ArrowDown' })
    })

    expect(input.getAttribute('aria-activedescendant')).toContain('chart-search-option-')
    vi.useRealTimers()
  })

  it('Escape → listbox 닫힘 + input clear', async () => {
    vi.useFakeTimers()
    render(<StockSearchBox onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input') as HTMLInputElement
    await act(async () => {
      fireEvent.change(input, { target: { value: '삼' } })
    })
    await advanceDebounce()

    await act(async () => {
      fireEvent.keyDown(input, { key: 'Escape' })
    })

    expect(screen.queryByTestId('chart-search-listbox')).toBeNull()
    expect(input.value).toBe('')
    vi.useRealTimers()
  })

  it('Enter → onSelect 호출', async () => {
    vi.useFakeTimers()
    const onSelect = vi.fn()
    render(<StockSearchBox onSelect={onSelect} />)
    const input = screen.getByTestId('chart-search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: '005930' } })
    })
    await advanceDebounce()

    // 첫 item select via Enter (without ArrowDown, picks index 0)
    await act(async () => {
      fireEvent.keyDown(input, { key: 'Enter' })
    })

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ code: '005930' }),
    )
    vi.useRealTimers()
  })

  it('클릭 → onSelect 호출', async () => {
    vi.useFakeTimers()
    const onSelect = vi.fn()
    render(<StockSearchBox onSelect={onSelect} />)
    const input = screen.getByTestId('chart-search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: '삼성' } })
    })
    await advanceDebounce()

    await act(async () => {
      fireEvent.mouseDown(screen.getByTestId('chart-search-option-005930'))
    })

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ code: '005930', name: '삼성전자' }),
    )
    vi.useRealTimers()
  })
})

// ---------------------------------------------------------------------------
// AC-ARCH-003 — useScreen/useTab 미구독
// ---------------------------------------------------------------------------

describe('StockSearchBox — AC-ARCH-003', () => {
  it('StockSearchBox.tsx 파일에 useScreen/useTab import 없음', async () => {
    const src = await import('../StockSearchBox?raw')
    // 정적 import 문에 useScreen/useTab 이 없음을 검증 (주석은 허용)
    const importLines = src.default
      .split('\n')
      .filter((line: string) => line.trim().startsWith('import '))
    const hasUseScreen = importLines.some((line: string) => line.includes('useScreen'))
    const hasUseTab = importLines.some((line: string) => line.includes('useTab'))
    expect(hasUseScreen).toBe(false)
    expect(hasUseTab).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// F-1 — focus() imperative handle (focus restoration)
// ---------------------------------------------------------------------------

import React from 'react'
import type { StockSearchBoxHandle } from '../StockSearchBox'

describe('StockSearchBox — focus() imperative handle (F-1)', () => {
  it('ref.focus() 호출 시 input에 focus 이동', () => {
    const ref = React.createRef<StockSearchBoxHandle>()
    render(<StockSearchBox ref={ref} onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input')

    // focus 다른 곳에 두기
    input.blur()

    ref.current?.focus()
    expect(document.activeElement).toBe(input)
  })

  it('clearInput 후에도 focus() 가능', async () => {
    vi.useFakeTimers()
    const ref = React.createRef<StockSearchBoxHandle>()
    render(<StockSearchBox ref={ref} onSelect={vi.fn()} />)
    const input = screen.getByTestId('chart-search-input') as HTMLInputElement

    await act(async () => {
      fireEvent.change(input, { target: { value: '삼' } })
      vi.advanceTimersByTime(200)
    })

    await act(async () => {
      ref.current?.clearInput()
    })
    ref.current?.focus()
    expect(document.activeElement).toBe(input)
    vi.useRealTimers()
  })
})
