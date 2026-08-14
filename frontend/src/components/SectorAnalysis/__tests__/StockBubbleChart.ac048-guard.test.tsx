// AC-SUX-048 (색상 채널 회귀 금지) — M5 착수 전 RED-FIRST 보존 계약 가드.
// REQ-SUX-056(섹터 버블 색상) 구현이 종목 버블(StockBubbleChart) 색상 배열에 영향을 주지 않음을 단언.
// @MX:SPEC: SPEC-SECTOR-UX-001 (AC-SUX-048), SPEC-SECTOR-MINOR-COLOR-001
//
// 이 테스트는 종목 버블 색상 배열을 "동결된 기대값"으로 고정한다. M5 가 SectorBubbleChart 에
// 발산형 색상(REQ-SUX-056)을 추가하더라도 본 테스트의 기대값은 변하지 않아야 한다(GREEN 유지).
// Lesson #9: 기대값은 리터럴 고정 — 색상 채널을 변형(mutate)하면 RED 가 관측되어야 한다.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import { StockBubbleChart } from '../StockBubbleChart'
import type { StockBubbleItem } from '../../../types/bubble'

// 동결된 기대값 — StockBubbleChart.tsx SECTOR_MINOR_PALETTE (SPEC-SECTOR-MINOR-COLOR-001 출하 계약).
// 이 리터럴이 곧 보존 계약이다. 소스의 상수를 import 하지 않고 하드코딩해 변형에 대한 RED 를 보장.
const EXPECTED_PALETTE = [
  '#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
  '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC',
] as const
const EXPECTED_ETC = '#9CA3AF'

let capturedOption: Record<string, unknown> = {}
vi.mock('echarts-for-react', () => ({
  default: vi.fn((props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  }),
}))

function mockMatchMedia(): void {
  const mq = {
    matches: false, media: '(min-width: 768px)', onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  }
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue(mq))
}

// groups → StockBubbleItem[]. stage 를 인자로 받아 stage-독립 단언에 사용.
function makeStocks(
  groups: Array<{ sector_minor: string | null; count: number }>,
  stage: number,
): StockBubbleItem[] {
  let nameIdx = 0
  const result: StockBubbleItem[] = []
  for (const { sector_minor, count } of groups) {
    for (let i = 0; i < count; i++) {
      nameIdx++
      result.push({
        name: `종목${nameIdx}`,
        price_change: (nameIdx % 5) - 2.5,
        rs_12m: nameIdx % 100,
        trading_value: nameIdx * 100_000_000,
        stage,
        stage_detail: stage === 2 ? 'entry' : null,
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor,
        product: null,
      } as unknown as StockBubbleItem)
    }
  }
  return result
}

// legend.data 에서 (name, color) 순서쌍 추출
function legendOrder(option: Record<string, unknown>): Array<{ name: string; color: string }> {
  const legend = option.legend as { data?: Array<{ name: string; itemStyle?: { color?: string } } | string> }
  return (legend?.data ?? []).map((d) => {
    if (typeof d === 'string') return { name: d, color: '' }
    return { name: d.name, color: d.itemStyle?.color ?? '' }
  })
}

beforeEach(() => {
  capturedOption = {}
  mockMatchMedia()
})
afterEach(() => { vi.unstubAllGlobals(); cleanup() })

describe('AC-SUX-048 — 색상 채널 회귀 금지 [보존 계약, RED-FIRST M5 가드]', () => {
  // fixture: 반도체(5) > 디스플레이(3) = 장비(3) → name asc → 디스플레이, 장비 / null(2) = 기타(마지막)
  const GROUPS = [
    { sector_minor: '반도체', count: 5 },
    { sector_minor: '디스플레이', count: 3 },
    { sector_minor: '장비', count: 3 },
    { sector_minor: null, count: 2 },
  ] as const

  it('색상 배열이 동결된 기대 팔레트(EXPECTED_PALETTE)와 정확히 일치한다', () => {
    render(<StockBubbleChart stocks={makeStocks([...GROUPS], 2)} sectorName="반도체" />)
    const order = legendOrder(capturedOption)
    const colors = order.map((o) => o.color)
    // 반도체=palette[0], 디스플레이=palette[1], 장비=palette[2], 기타=ETC
    expect(colors).toEqual([
      EXPECTED_PALETTE[0], EXPECTED_PALETTE[1], EXPECTED_PALETTE[2], EXPECTED_ETC,
    ])
  })

  it('legend.data 정렬 = (count desc, name asc), "기타"는 항상 마지막', () => {
    render(<StockBubbleChart stocks={makeStocks([...GROUPS], 2)} sectorName="반도체" />)
    const names = legendOrder(capturedOption).map((o) => o.name)
    expect(names).toEqual(['반도체', '디스플레이', '장비', '기타'])
  })

  it('색상 매핑은 stage 에 의존하지 않는다 — stage 만 바꾼 fixture 의 색상 배열이 동일', () => {
    const { rerender } = render(<StockBubbleChart stocks={makeStocks([...GROUPS], 2)} sectorName="반도체" />)
    const colorsStage2 = legendOrder(capturedOption).map((o) => o.color)
    // 동일 fixture, stage 전부 1(또는 null)로 교체 — sector_minor 는 동일
    rerender(<StockBubbleChart stocks={makeStocks([...GROUPS], 1)} sectorName="반도체" />)
    const colorsStage1 = legendOrder(capturedOption).map((o) => o.color)
    expect(colorsStage1).toEqual(colorsStage2)
  })

  it('리렌더 2회 간 색상 배열이 동일하다 (결정성)', () => {
    const { rerender } = render(<StockBubbleChart stocks={makeStocks([...GROUPS], 2)} sectorName="반도체" />)
    const first = legendOrder(capturedOption).map((o) => `${o.name}=${o.color}`)
    rerender(<StockBubbleChart stocks={makeStocks([...GROUPS], 2)} sectorName="반도체" />)
    const second = legendOrder(capturedOption).map((o) => `${o.name}=${o.color}`)
    expect(second).toEqual(first)
  })

  it('동일 sector_minor 종목은 동일 색상, 서로 다른 sector_minor 는 서로 다른 색상, null/overflow 는 #9CA3AF', () => {
    // 11개 그룹 → palette 10 초과 → 11번째 + null 은 기타로 흡수
    const manyGroups: Array<{ sector_minor: string | null; count: number }> =
      Array.from({ length: 11 }, (_, i) => ({ sector_minor: `G${i}` as string | null, count: 10 - i }))
    manyGroups.push({ sector_minor: null, count: 1 })
    render(<StockBubbleChart stocks={makeStocks(manyGroups, 2)} sectorName="반도체" />)
    const order = legendOrder(capturedOption)
    // 상위 10개만 palette, 나머지 G10 + null → 기타(마지막)
    const paletteColors = order.slice(0, 10).map((o) => o.color)
    expect(paletteColors).toEqual([...EXPECTED_PALETTE])
    expect(order[order.length - 1].name).toBe('기타')
    expect(order[order.length - 1].color).toBe(EXPECTED_ETC)
    // 상위 10개는 모두 서로 다름
    expect(new Set(paletteColors).size).toBe(10)
  })
})
