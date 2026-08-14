// AC-SUX-040(종목)/042(종목)/047/049/050/051 — StockBubbleChart M5 (시각화 규약)
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import { StockBubbleChart } from '../StockBubbleChart'
import type { StockBubbleItem } from '../../../types/bubble'

let capturedOption: Record<string, unknown> = {}
vi.mock('echarts-for-react', () => ({
  default: vi.fn((props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  }),
}))
function mockMatchMedia(): void {
  const mq = { matches: false, media: '(min-width: 768px)', onchange: null, addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn() }
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue(mq))
}
function mk(over: Partial<StockBubbleItem>[]): StockBubbleItem[] {
  return over.map((o, i) => ({
    name: `종목${i}`, price_change: (i % 5) - 2, rs_12m: 50 + i, trading_value: 1e11 + i * 1e10,
    stage: 2, stage_detail: null, market_cap: 1e9, volume_ratio: 1, sector_minor: '반도체', product: null,
    ...o,
  } as unknown as StockBubbleItem))
}
interface DataPt { value: (string | number)[]; itemStyle?: { borderColor?: string; borderWidth?: number; borderType?: string } }

beforeEach(() => { capturedOption = {}; mockMatchMedia() })
afterEach(() => { vi.unstubAllGlobals(); cleanup() })

const PALETTE = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']
const ETC = '#9CA3AF'

describe('AC-SUX-040 (종목) — 결측 거래대금: 최소크기 + 툴팁, 테두리는 Stage 불변 (REQ-SUX-057)', () => {
  it('trading_value:null → symbolSize(val[2]) = 2×rMin(=10), 툴팁 "데이터 없음"', () => {
    render(<StockBubbleChart stocks={mk([{ trading_value: null as unknown as number }])} sectorName="반도체" period="1w" />)
    const pts = (capturedOption.series as unknown as Array<{ data: DataPt[] }>)[0].data
    expect(Number(pts[0].value[2])).toBe(10) // 2 × STOCK_BUBBLE_R_MIN(5)
    const tooltip = (capturedOption.tooltip as { formatter: (p: { data: { value: (string|number)[]; sector_minor: string|null; product: string|null } }) => string }).formatter
    const out = tooltip({ data: { value: pts[0].value, sector_minor: '반도체', product: null } })
    expect(out).toContain('거래대금: 데이터 없음')
  })

  it('구분가능성 — {stage:2,tv:null} 테두리(흰2px실선) ≠ {stage:null,tv:거액} 테두리(회색1px점선)', () => {
    render(<StockBubbleChart stocks={mk([
      { name: 'A', stage: 2, trading_value: null as unknown as number },
      { name: 'B', stage: null, trading_value: 1e10 },
    ])} sectorName="반도체" period="1w" />)
    const pts = (capturedOption.series as unknown as Array<{ data: DataPt[] }>)[0].data
    const a = pts.find(p => p.value[4] === 'A')!
    const b = pts.find(p => p.value[4] === 'B')!
    expect(a.itemStyle?.borderColor).toBe('#ffffff')
    expect(a.itemStyle?.borderWidth).toBe(2)
    expect(a.itemStyle?.borderType).toBe('solid')
    expect(b.itemStyle?.borderColor).toBe('#9CA3AF')
    expect(b.itemStyle?.borderType).toBe('dashed')
  })
})

describe('AC-SUX-047 — Stage 테두리 채널 (VZ-0)', () => {
  it('stage 2/1/3/4/null → (흰2px실선)/(transparent 0)/(transparent 0)/(어두운회색1px)/(회색1px점선)', () => {
    render(<StockBubbleChart stocks={mk([
      { name: 's2', stage: 2 }, { name: 's1', stage: 1 }, { name: 's3', stage: 3 },
      { name: 's4', stage: 4 }, { name: 'sN', stage: null },
    ])} sectorName="반도체" period="1w" />)
    const pts = (capturedOption.series as unknown as Array<{ data: DataPt[] }>)[0].data
    const byName = (n: string) => pts.find(p => p.value[4] === n)!
    expect(byName('s2').itemStyle).toEqual({ borderColor: '#ffffff', borderWidth: 2, borderType: 'solid' })
    expect(byName('s1').itemStyle?.borderWidth).toBe(0)
    expect(byName('s3').itemStyle?.borderWidth).toBe(0)
    expect(byName('s4').itemStyle).toEqual({ borderColor: '#4b5563', borderWidth: 1, borderType: 'solid' })
    expect(byName('sN').itemStyle).toEqual({ borderColor: '#9CA3AF', borderWidth: 1, borderType: 'dashed' })
  })
})

describe('AC-SUX-042 (종목) — X 기준선 = 섹터 집계 수익률 (VZ-5)', () => {
  it('markLine 에 섹터 집계 수익률 선 + 라벨(섹터명·값), 0선 보조 존재', () => {
    render(<StockBubbleChart stocks={mk([{ price_change: 3, market_cap: 1e9 }, { price_change: 5, market_cap: 3e9 }])} sectorName="반도체" period="1w" />)
    // cap-weighted mean = (3*1e9 + 5*3e9)/(4e9) = (3+15)/4 = 4.5
    const series = (capturedOption.series as unknown as Array<{ markLine?: { data: Array<Record<string, unknown>> } }>)
    const ml = series.find(s => s.markLine)?.markLine
    expect(ml).toBeDefined()
    const xLines = ml!.data.filter((d) => 'xAxis' in d)
    // 섹터 집계선 + 0 보조선
    const aggLine = xLines.find(d => Number(d.xAxis) !== 0)
    expect(aggLine).toBeDefined()
    expect(Number(aggLine!.xAxis)).toBeCloseTo(4.5, 5)
    const label = (aggLine!.label as { formatter: string }).formatter
    expect(label).toContain('반도체')
    expect(label).toContain('4.50%')
    // 0 보조선도 존재
    const zeroLine = xLines.find(d => Number(d.xAxis) === 0)
    expect(zeroLine).toBeDefined()
  })
})

describe('AC-SUX-049 — 다크 배경 대비 (VZ-11, 팔레트 ≥ 3:1 on #1a1a2e)', () => {
  function luminance(hex: string): number {
    const c = (v: number) => { const x = v / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4) }
    const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16)
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)
  }
  function contrast(a: string, b: string): number {
    const la = luminance(a), lb = luminance(b)
    const hi = Math.max(la, lb), lo = Math.min(la, lb)
    return (hi + 0.05) / (lo + 0.05)
  }
  it('팔레트 10색 + ETC 전부 #1a1a2e 대비 >= 3.0', () => {
    const bg = '#1a1a2e'
    for (const color of [...PALETTE, ETC]) {
      const r = contrast(color, bg)
      expect(r).toBeGreaterThanOrEqual(3.0)
    }
  })
})

describe('AC-SUX-050 — 기타 범례 개수 병기 (VZ-12)', () => {
  it('오버플로+null → legend.formatter("기타") 가 "기타 (N개 산업)" 반환', () => {
    // 12개 고유 sector_minor → 10 palette + 2 overflow + null = 기타 3개
    const stocks: StockBubbleItem[] = []
    for (let i = 0; i < 12; i++) stocks.push({ name: `s${i}`, price_change: 1, rs_12m: 50, trading_value: 1e11, stage: 2, stage_detail: null, market_cap: 1e9, volume_ratio: 1, sector_minor: `G${i}`, product: null } as unknown as StockBubbleItem)
    stocks.push({ name: 'sN', price_change: 1, rs_12m: 50, trading_value: 1e11, stage: 2, stage_detail: null, market_cap: 1e9, volume_ratio: 1, sector_minor: null, product: null } as unknown as StockBubbleItem)
    render(<StockBubbleChart stocks={stocks} sectorName="반도체" period="1w" />)
    const legend = capturedOption.legend as { formatter?: (n: string) => string }
    expect(typeof legend.formatter).toBe('function')
    // overflow 2 (G10,G11) + null 1 = 3
    expect(legend.formatter!('기타')).toBe('기타 (3개 산업)')
    // 비-기타 이름은 그대로
    expect(legend.formatter!('G0')).toBe('G0')
  })
})

describe('AC-SUX-051 — 종목 버블 hover emphasis.focus === "none" (VZ-13)', () => {
  it('모든 series 의 emphasis.focus 가 "none" (RRG/Bump 의 series 는 본 테스트 범위 외)', () => {
    render(<StockBubbleChart stocks={mk([{ sector_minor: '반도체' }, { sector_minor: '디스플레이' }])} sectorName="반도체" period="1w" />)
    const series = capturedOption.series as Array<{ emphasis?: { focus?: string } }>
    series.forEach((s) => expect(s.emphasis?.focus).toBe('none'))
  })
})
