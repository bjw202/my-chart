// SPEC-RS-REBALANCE-001 M5 — AC-RSR-011: 종목 버블 툴팁 열기 배지.
// 툴팁 formatter 는 ECharts 옵션 안 익명 함수 — echarts-for-react 목으로 옵션을 붙잡아
// formatter 를 직접 호출한다(StockBubbleChart.test.tsx 선례).
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import { StockBubbleChart } from '../StockBubbleChart'
import type { StockBubbleItem } from '../../../types/bubble'
import { RS_TOP_THRESHOLD } from '../../../utils/rsMetrics'

let capturedOption: Record<string, unknown> = {}

vi.mock('echarts-for-react', () => ({
  default: vi.fn((props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  }),
}))

function makeStock(name: string, rs_1m: number | null): StockBubbleItem {
  return {
    name,
    price_change: 1,
    rs_12m: 50,
    trading_value: 1_000_000_000,
    stage: 2,
    stage_detail: null,
    market_cap: 1_000_000_000,
    volume_ratio: 1,
    sector_minor: '반도체',
    product: null,
    rs_1m,
  }
}

type Datum = { value: unknown[] }

function tooltipHtml(stockName: string): string {
  const series = capturedOption.series as Array<{ data?: Datum[] }>
  const datum = series.flatMap((s) => s.data ?? []).find((d) => d.value[4] === stockName)
  if (!datum) throw new Error(`series 에서 ${stockName} 를 찾지 못했다`)
  const tooltip = capturedOption.tooltip as { formatter: (p: { data: Datum }) => string }
  return tooltip.formatter({ data: datum })
}

beforeEach(() => {
  capturedOption = {}
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
    matches: false, media: '', onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
  cleanup()
})

describe('StockBubbleChart 툴팁 — 열기 배지 (AC-RSR-011)', () => {
  it('rs_1m 80, 80.01 만 배지를 갖고 79.99, null 은 갖지 않는다', () => {
    render(
      <StockBubbleChart
        stocks={[makeStock('종목A', 79.99), makeStock('종목B', 80), makeStock('종목C', 80.01), makeStock('종목D', null)]}
        sectorName="IT"
      />,
    )
    expect(tooltipHtml('종목A')).not.toContain('rs-heat-badge')
    expect(tooltipHtml('종목B')).toContain('rs-heat-badge')
    expect(tooltipHtml('종목C')).toContain('rs-heat-badge')
    expect(tooltipHtml('종목D')).not.toContain('rs-heat-badge')
  })

  it('배지 title 에 RS_TOP_THRESHOLD 값이 문자열로 들어 있다', () => {
    render(<StockBubbleChart stocks={[makeStock('종목B', 80)]} sectorName="IT" />)
    const m = tooltipHtml('종목B').match(/class="rs-heat-badge"[^>]*title="([^"]*)"/)
    expect(m).not.toBeNull()
    expect(m![1]).toContain(String(RS_TOP_THRESHOLD))
  })
})
