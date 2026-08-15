// SPEC-BUBBLE-ZOOM-001: 섹터 버블 차트 X축 줌 + 빈 공간 더블클릭 리셋 테스트
// RED 단계 — 모든 테스트는 GREEN 구현 전에 실패해야 합니다.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import { SectorBubbleChart } from '../SectorBubbleChart'
import type { SectorBubbleItem } from '../../../types/bubble'

// echarts-for-react mock: option/props 캡처 + ref(getEchartsInstance/getZr) 노출 (감사 D3)
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

// 합성 데이터 — SectorBubbleItem 전체 필드 (types/bubble.ts)
function makeSectors(n: number): SectorBubbleItem[] {
  return Array.from({ length: n }, (_, i) => ({
    name: `섹터${i}`,
    excess_return: (i - n / 2) * 2,
    rs_avg: 40 + i,
    trading_value: 10_000_000_000 * (i + 1),
    period_return: (i - n / 2) * 4,
  }))
}

describe('SectorBubbleChart X축 줌 (SPEC-BUBBLE-ZOOM-001)', () => {
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
    render(<SectorBubbleChart sectors={makeSectors(5)} onSectorClick={vi.fn()} period="1w" />)
    const dz = h.option?.dataZoom as Array<Record<string, unknown>> | undefined
    expect(dz).toBeDefined()
    expect(dz![0].type).toBe('inside')
    expect(dz![0].xAxisIndex).toBe(0)
    expect(dz![0].filterMode).toBe('none')
    expect(dz![0].zoomOnMouseWheel).toBe(true)
    expect(dz![0].minSpan).toBe(20) // 퍼센트 단위 — 분율 0.2로 쓰면 초기 창이 클램프되어 버블이 사라짐
    expect(dz![0].maxSpan).toBe(100)
  })

  it('REQ-BZ-001d: yAxisIndex 키가 부재해야 한다 (Y축 고정 — 감사 D1)', () => {
    render(<SectorBubbleChart sectors={makeSectors(5)} onSectorClick={vi.fn()} period="1w" />)
    const dz = h.option!.dataZoom as Array<Record<string, unknown>>
    expect('yAxisIndex' in dz[0]).toBe(false)
  })

  it('REQ-BZ-006a: notMerge 불변 유지', () => {
    render(<SectorBubbleChart sectors={makeSectors(5)} onSectorClick={vi.fn()} period="1w" />)
    expect(h.props!.notMerge).toBe(true)
  })

  it('Edge D-002: 빈 데이터에서는 dataZoom이 없다', () => {
    render(<SectorBubbleChart sectors={[]} onSectorClick={vi.fn()} period="1w" />)
    expect(h.option!.dataZoom).toBeUndefined()
  })

  it('REQ-BZ-003a: 빈 공간 더블클릭 → dataZoom 전체 범위 dispatchAction', () => {
    render(<SectorBubbleChart sectors={makeSectors(5)} onSectorClick={vi.fn()} period="1w" />)
    const dbl = h.zrHandlers['dblclick']
    expect(dbl).toBeDefined()
    dbl!({})
    expect(h.dispatchAction).toHaveBeenCalledWith({ type: 'dataZoom', start: 0, end: 100 })
  })

  it('REQ-BZ-003d: 버블 위 더블클릭 → dispatchAction 미호출', () => {
    render(<SectorBubbleChart sectors={makeSectors(5)} onSectorClick={vi.fn()} period="1w" />)
    h.zrHandlers['dblclick']!({ target: {} })
    expect(h.dispatchAction).not.toHaveBeenCalled()
  })

  it('REQ-BZ-007: 툴박스 영역 선택 줌(X축만) 설정이 존재한다', () => {
    render(<SectorBubbleChart sectors={makeSectors(5)} onSectorClick={vi.fn()} period="1w" />)
    const tb = h.option!.toolbox as {
      feature: { dataZoom: { xAxisIndex: unknown; yAxisIndex: unknown }; restore: unknown }
    } | undefined
    expect(tb).toBeDefined()
    expect(tb!.feature.dataZoom.xAxisIndex).toEqual([0])
    expect(tb!.feature.dataZoom.yAxisIndex).toBe(false) // false = Y축 제어 비활성 (공식 문서 방식)
    expect(tb!.feature.restore).toBeDefined()
  })

  it('REQ-BZ-007-1: 빈 데이터에서는 toolbox도 없다', () => {
    render(<SectorBubbleChart sectors={[]} onSectorClick={vi.fn()} period="1w" />)
    expect(h.option!.toolbox).toBeUndefined()
  })

  it('상단 마진 계약: grid.top ≥ 48 — 최대 버블 반지름(34)이 toolbox 밴드(10~30px)를 과도히 침범하지 않는다', () => {
    render(<SectorBubbleChart sectors={makeSectors(5)} onSectorClick={vi.fn()} period="1w" />)
    const grid = h.option!.grid as { top: number }
    expect(grid.top).toBeGreaterThanOrEqual(48)
  })
})
