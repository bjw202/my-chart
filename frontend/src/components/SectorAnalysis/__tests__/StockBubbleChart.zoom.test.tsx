// SPEC-BUBBLE-ZOOM-001: 종목 버블 차트 X축 줌 + 빈 공간 더블클릭 리셋 테스트
// RED 단계 — 모든 테스트는 GREEN 구현 전에 실패해야 합니다.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import { StockBubbleChart } from '../StockBubbleChart'
import type { StockBubbleItem } from '../../../types/bubble'

// ──────────────────────────────────────────────────────────────
// echarts-for-react mock: option/props 캡처 + ref(getEchartsInstance/getZr) 노출
// 기존 capturedOption 관례(StockBubbleChart.test.tsx)를 dblclick 검증 가능형으로 확장 (감사 D3)
// ──────────────────────────────────────────────────────────────
const h = vi.hoisted(() => {
  return {
    option: null as Record<string, unknown> | null,
    props: null as Record<string, unknown> | null,
    zrHandlers: {} as Record<string, (e: { target?: unknown }) => void>,
    dispatchAction: vi.fn(),
    zrOff: vi.fn(),
  }
})

vi.mock('echarts-for-react', async () => {
  const React = await import('react')
  const mockZr = {
    on: (ev: string, fn: (e: { target?: unknown }) => void) => {
      h.zrHandlers[ev] = fn
    },
    off: h.zrOff,
  }
  const mockChart = { dispatchAction: h.dispatchAction, getZr: () => mockZr }
  return {
    default: React.forwardRef(function MockReactECharts(
      props: Record<string, unknown>,
      ref: React.ForwardedRef<unknown>,
    ) {
      h.option = props.option as Record<string, unknown>
      h.props = props
      React.useImperativeHandle(ref, () => ({ getEchartsInstance: () => mockChart }), [])
      return null
    }),
  }
})

// matchMedia mock — jsdom 미지원 대응 (기존 관례)
function mockMatchMedia() {
  const mq = {
    matches: false,
    media: '(min-width: 768px)',
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue(mq))
}

// 합성 데이터 — StockBubbleItem 전체 필드 (types/bubble.ts)
function makeStocks(n: number): StockBubbleItem[] {
  return Array.from({ length: n }, (_, i) => ({
    name: `종목${i}`,
    price_change: (i - n / 2) * 3,
    rs_12m: 50 + (i % 50),
    trading_value: 1_000_000_000 * (i + 1),
    stage: (i % 4) + 1,
    stage_detail: null,
    market_cap: 100_000_000_000,
    volume_ratio: 1,
    sector_minor: i % 2 ? '산업A' : '산업B',
    product: null,
  }))
}

describe('StockBubbleChart X축 줌 (SPEC-BUBBLE-ZOOM-001)', () => {
  beforeEach(() => {
    mockMatchMedia()
  })
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    h.option = null
    h.props = null
    h.zrHandlers = {}
  })

  it('REQ-BZ-001: dataZoom inside/X축 설정이 존재한다', () => {
    render(<StockBubbleChart stocks={makeStocks(5)} sectorName="테스트" />)
    const dz = h.option?.dataZoom as Array<Record<string, unknown>> | undefined
    expect(dz).toBeDefined()
    expect(dz![0].type).toBe('inside')
    expect(dz![0].xAxisIndex).toBe(0)
    expect(dz![0].filterMode).toBe('none')
    expect(dz![0].zoomOnMouseWheel).toBe(true)
    expect(dz![0].minSpan).toBe(20) // 퍼센트 단위 — 분율 0.2로 쓰면 초기 창이 20%…1%로 클램프되어 버블이 사라짐
    expect(dz![0].maxSpan).toBe(100)
  })

  it('REQ-BZ-001d: yAxisIndex 키가 부재해야 한다 (Y축 고정 — 감사 D1)', () => {
    render(<StockBubbleChart stocks={makeStocks(5)} sectorName="테스트" />)
    const dz = h.option!.dataZoom as Array<Record<string, unknown>>
    expect('yAxisIndex' in dz[0]).toBe(false)
  })

  it('REQ-BZ-006a: notMerge 불변 유지', () => {
    render(<StockBubbleChart stocks={makeStocks(5)} sectorName="테스트" />)
    expect(h.props!.notMerge).toBe(true)
  })

  it('Edge D-002: 빈 데이터에서는 dataZoom이 없다', () => {
    render(<StockBubbleChart stocks={[]} sectorName="테스트" />)
    expect(h.option!.dataZoom).toBeUndefined()
  })

  it('REQ-BZ-003a: 빈 공간 더블클릭 → dataZoom 전체 범위 dispatchAction', () => {
    render(<StockBubbleChart stocks={makeStocks(5)} sectorName="테스트" />)
    const dbl = h.zrHandlers['dblclick']
    expect(dbl).toBeDefined()
    dbl!({}) // e.target 부재 = 빈 공간
    expect(h.dispatchAction).toHaveBeenCalledWith({ type: 'dataZoom', start: 0, end: 100 })
  })

  it('REQ-BZ-003d: 버블 위 더블클릭 → dispatchAction 미호출', () => {
    render(<StockBubbleChart stocks={makeStocks(5)} sectorName="테스트" />)
    h.zrHandlers['dblclick']!({ target: {} }) // 그래픽 요소 위
    expect(h.dispatchAction).not.toHaveBeenCalled()
  })
})
