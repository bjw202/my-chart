// SPEC-RS-REBALANCE-001 M5 — AC-RSR-011 대조: RS_TOP_THRESHOLD 를 85 로 주입하면
// 두 화면 모두 배지 경계가 85 로 움직여야 한다(리터럴 80 구현은 80.01 이 배지를 유지해 RED).
// 모듈 심볼 주입: vi.mock('../rsMetrics') — 컴포넌트가 import 하는 같은 모듈이 교체된다.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { StockTable } from '../../components/StockExplorer/StockTable'
import { StockBubbleChart } from '../../components/SectorAnalysis/StockBubbleChart'
import type { Stage2Candidate } from '../../types/stage'
import type { StockBubbleItem } from '../../types/bubble'

vi.mock('../rsMetrics', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../rsMetrics')>()
  return { ...actual, RS_TOP_THRESHOLD: 85 }
})

let capturedOption: Record<string, unknown> = {}
vi.mock('echarts-for-react', () => ({
  default: vi.fn((props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  }),
}))

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

function cand(code: string, name: string, rs_1m: number): Stage2Candidate {
  return {
    code, name, market: 'KOSPI', sector_major: 'IT', sector_minor: '반도체',
    stage: 2, stage_detail: 'Stage 2', rs_12m: 50, chg_1m: 1, volume_ratio: 1,
    close: 100, sma50: 90, sma200: 80, rs_1m,
  }
}

function bubble(name: string, rs_1m: number): StockBubbleItem {
  return {
    name, price_change: 1, rs_12m: 50, trading_value: 1_000_000_000, stage: 2,
    stage_detail: null, market_cap: 1_000_000_000, volume_ratio: 1,
    sector_minor: '반도체', product: null, rs_1m,
  }
}

describe('RS_TOP_THRESHOLD 주입(85) — 배지 경계가 상수를 따른다', () => {
  it('StockTable: 80.01 은 배지 없음, 85 는 배지 + title 에 "85"', () => {
    render(
      <StockTable
        candidates={[cand('000001', '종목C', 80.01), cand('000002', '종목E', 85)]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />,
    )
    const badge = (name: string) =>
      (screen.getByText(name).closest('tr') as HTMLTableRowElement).querySelector('[data-testid="rs-heat-badge"]')
    expect(badge('종목C')).toBeNull()
    expect(badge('종목E')).not.toBeNull()
    expect(badge('종목E')?.getAttribute('title') ?? '').toContain('85')
  })

  it('StockBubbleChart 툴팁: 80.01 은 배지 없음, 85 는 배지 + title 에 "85"', () => {
    render(<StockBubbleChart stocks={[bubble('종목C', 80.01), bubble('종목E', 85)]} sectorName="IT" />)
    const series = capturedOption.series as Array<{ data?: Array<{ value: unknown[] }> }>
    const html = (name: string) => {
      const d = series.flatMap((s) => s.data ?? []).find((x) => x.value[4] === name)
      const tooltip = capturedOption.tooltip as { formatter: (p: { data: unknown }) => string }
      return tooltip.formatter({ data: d })
    }
    expect(html('종목C')).not.toContain('rs-heat-badge')
    expect(html('종목E')).toContain('rs-heat-badge')
    expect(html('종목E')).toMatch(/title="[^"]*85[^"]*"/)
  })
})
