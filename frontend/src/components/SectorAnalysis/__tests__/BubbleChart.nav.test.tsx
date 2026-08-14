// RED: AC-SUX-013 (TR-9 stock bubble click) + AC-SUX-016 (TR-6 bubble-back sector preserve) — SPEC-SECTOR-UX-001 M3
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Capture handlers wired into StockBubbleChart (props 단언 — AC-SUX-013).
let capturedOnStockClick: ((name: string) => void) | null = null

vi.mock('../../../api/bubble', () => ({
  fetchSectorBubble: vi.fn().mockResolvedValue({ sectors: [{ name: '반도체', value: 100 } as never] }),
  fetchStockBubble: vi.fn().mockResolvedValue({ stocks: [] }),
}))

vi.mock('../SectorBubbleChart', () => ({
  SectorBubbleChart: (props: { sectors: unknown[]; onSectorClick: (name: string) => void }) => (
    <div data-testid="sector-bubble">
      <button onClick={() => props.onSectorClick('반도체')}>enter 반도체</button>
    </div>
  ),
}))

vi.mock('../StockBubbleChart', () => ({
  StockBubbleChart: (props: { onStockClick?: (name: string) => void }) => {
    capturedOnStockClick = props.onStockClick ?? null
    return (
      <div data-testid="stock-bubble">
        <button onClick={() => props.onStockClick?.('삼성전자')}>click stock</button>
      </div>
    )
  },
}))

const mockNavigate = vi.fn()
const mockSelectSector = vi.fn()
vi.mock('../../../contexts/TabContext', () => ({
  useNavIntent: () => ({ navigate: mockNavigate, intent: null }),
}))
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({ selectSector: mockSelectSector }),
}))
vi.mock('../../../contexts/AnalysisParamsContext', () => ({
  useAnalysisParams: () => ({ period: '1m', market: 'all' }),
}))

import { BubbleChart } from '../BubbleChart'

describe('AC-SUX-013 — TR-9 stock bubble click (ST-8 onStockClick wiring)', () => {
  beforeEach(() => {
    capturedOnStockClick = null
    mockNavigate.mockClear()
    mockSelectSector.mockClear()
  })

  it('BubbleChart passes onStockClick to StockBubbleChart (props 단언)', async () => {
    render(<BubbleChart initialSector={null} />)
    // sector data 비동기 로드 대기 → SectorBubbleChart 마운트
    await waitFor(() => expect(screen.getByText('enter 반도체')).toBeInTheDocument())
    fireEvent.click(screen.getByText('enter 반도체'))
    // stock view 진입
    await waitFor(() => expect(screen.getByTestId('stock-bubble')).toBeInTheDocument())
    // AC-SUX-013: onStockClick prop 이 실제로 전달된다.
    expect(capturedOnStockClick).not.toBeNull()
  })

  it('stock bubble click → navigate stock-explorer with focusStock + sync sector', async () => {
    render(<BubbleChart initialSector={null} />)
    await waitFor(() => expect(screen.getByText('enter 반도체')).toBeInTheDocument())
    fireEvent.click(screen.getByText('enter 반도체'))
    await waitFor(() => expect(screen.getByTestId('stock-bubble')).toBeInTheDocument())
    fireEvent.click(screen.getByText('click stock'))
    // TR-9: focusStock payload + 현재 섹터를 전역 슬롯에 동기화.
    expect(mockSelectSector).toHaveBeenCalledWith('반도체')
    expect(mockNavigate).toHaveBeenCalledWith({
      target: 'stock-explorer',
      payload: { focusStock: '삼성전자' },
    })
  })
})

describe('AC-SUX-016 — TR-6 bubble-back preserves selectedSector', () => {
  beforeEach(() => {
    capturedOnStockClick = null
  })

  it('← 섹터 목록 클릭 시 stock view → sector view 전환, stockData 초기화', async () => {
    render(<BubbleChart initialSector={null} />)
    await waitFor(() => expect(screen.getByText('enter 반도체')).toBeInTheDocument())
    fireEvent.click(screen.getByText('enter 반도체'))
    await waitFor(() => expect(screen.getByTestId('stock-bubble')).toBeInTheDocument())

    fireEvent.click(screen.getByText('← 섹터 목록'))
    // sector view 복귀 — StockBubbleChart 사라지고 SectorBubbleChart 재등장.
    await waitFor(() => {
      expect(screen.queryByTestId('stock-bubble')).not.toBeInTheDocument()
      expect(screen.getByTestId('sector-bubble')).toBeInTheDocument()
    })
  })
})
