// SPEC-SECTOR-MINOR-COLOR-001: StockBubbleChart sector_minor 색상 매핑 테스트
// RED 단계 — 모든 테스트는 GREEN-2 구현 전에 실패해야 합니다.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { StockBubbleChart } from '../StockBubbleChart'
import type { StockBubbleItem } from '../../../types/bubble'

// ──────────────────────────────────────────────────────────────
// echarts-for-react mock: option prop을 캡처하기 위한 전역 변수
// ──────────────────────────────────────────────────────────────
let capturedOption: Record<string, unknown> = {}

vi.mock('echarts-for-react', () => ({
  default: vi.fn((props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  }),
}))

// multi-series에서 종목명으로 색상을 찾는 헬퍼 (series 레벨 color 사용)
function getStockColor(
  series: Array<{ name?: string; itemStyle?: { color?: string }; data?: Array<{ value: unknown[] }> }>,
  stockName: string
): string | undefined {
  for (const s of series) {
    const found = s.data?.find((d) => (d.value as unknown[])[4] === stockName)
    if (found) return s.itemStyle?.color
  }
  return undefined
}

// ──────────────────────────────────────────────────────────────
// matchMedia mock 헬퍼 — jsdom은 matchMedia를 지원하지 않으므로 필수
// ──────────────────────────────────────────────────────────────
function mockMatchMedia(matches: boolean) {
  const mq = {
    matches,
    media: matches ? '(max-width: 767px)' : '(min-width: 768px)',
    onchange: null,
    addListener: vi.fn(),    // deprecated API 호환
    removeListener: vi.fn(), // deprecated API 호환
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue(mq))
  return mq
}

// ──────────────────────────────────────────────────────────────
// 합성 데이터 헬퍼
// ──────────────────────────────────────────────────────────────

/** sector_minor 그룹을 지정해 StockBubbleItem 배열 생성
 * sector_minor는 GREEN-2에서 StockBubbleItem 타입에 추가됩니다.
 * RED 단계에서는 unknown을 경유해 타입 단언을 우회합니다.
 */
function makeStocks(
  groups: Array<{ sector_minor: string | null; count: number; stage?: number }>
): StockBubbleItem[] {
  let nameIdx = 0
  const result: StockBubbleItem[] = []
  for (const { sector_minor, count, stage = 2 } of groups) {
    for (let i = 0; i < count; i++) {
      nameIdx++
      const item = {
        name: `종목${nameIdx}`,
        price_change: (nameIdx % 5) - 2.5,
        rs_12m: (nameIdx % 100),
        trading_value: nameIdx * 100_000_000,
        stage,
        stage_detail: stage === 2 ? 'entry' : null,
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor,
      } as unknown as StockBubbleItem // sector_minor는 GREEN-2에서 타입에 추가됩니다
      result.push(item)
    }
  }
  return result
}

// ──────────────────────────────────────────────────────────────
// 공통 setup / teardown
// ──────────────────────────────────────────────────────────────
beforeEach(() => {
  capturedOption = {}
  mockMatchMedia(false) // 기본: 데스크탑
})

afterEach(() => {
  vi.unstubAllGlobals()
  cleanup()
})

// ==============================================================
// AC-3: StockBubbleItem 타입에 sector_minor 필드 존재 여부
// ==============================================================
describe('AC-3: StockBubbleItem 타입 미러', () => {
  it('StockBubbleItem 타입에 sector_minor: string | null 필드가 존재한다', () => {
    // 소스 파일을 읽어 sector_minor 선언이 포함됐는지 정적 검사
    const typesPath = path.resolve(
      __dirname,
      '../../../types/bubble.ts'
    )
    const src = fs.readFileSync(typesPath, 'utf-8')

    // sector_minor 필드 선언 패턴 확인 (string | null)
    expect(src).toMatch(/sector_minor\s*[?:]/)
  })

  it('sector_minor가 string | null 타입으로 선언된다', () => {
    const typesPath = path.resolve(__dirname, '../../../types/bubble.ts')
    const src = fs.readFileSync(typesPath, 'utf-8')

    // "sector_minor?: string | null" 또는 "sector_minor: string | null" 형태
    expect(src).toMatch(/sector_minor\s*\??\s*:\s*string\s*\|\s*null/)
  })
})

// ==============================================================
// AC-4: 동일 sector_minor 종목들의 itemStyle.color 일치
// ==============================================================
describe('AC-4: 동일 sector_minor 종목들은 동일한 색상', () => {
  it('같은 sector_minor 종목들의 itemStyle.color가 모두 동일하다 (다른 stage여도)', () => {
    // 핵심: sector_minor='반도체' 종목에 서로 다른 stage를 부여
    // multi-series 구현: 같은 sector_minor는 동일 series → series.itemStyle.color가 동일
    const stocks: StockBubbleItem[] = [
      {
        name: '반도체A',
        price_change: 1,
        rs_12m: 70,
        trading_value: 100_000_000,
        stage: 1,
        stage_detail: null,
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
      } as unknown as StockBubbleItem,
      {
        name: '반도체B',
        price_change: 2,
        rs_12m: 80,
        trading_value: 200_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
      } as unknown as StockBubbleItem,
      {
        name: '반도체C',
        price_change: 3,
        rs_12m: 60,
        trading_value: 150_000_000,
        stage: 4,
        stage_detail: null,
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const series = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>
    expect(series).toBeDefined()

    // multi-series: 반도체 3개는 동일 series에 속하므로 같은 series.itemStyle.color
    const colorA = getStockColor(series, '반도체A')
    const colorB = getStockColor(series, '반도체B')
    const colorC = getStockColor(series, '반도체C')

    // 3개 모두 동일한 sector_minor 색상이어야 함
    expect(colorA).toBeDefined()
    expect(colorA).toBe(colorB)
    expect(colorA).toBe(colorC)
  })

  it('서로 다른 sector_minor 그룹은 서로 다른 색상을 가진다', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 2 },
      { sector_minor: '디스플레이', count: 2 },
      { sector_minor: null, count: 1 },
    ])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const series = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>
    expect(series).toBeDefined()

    // multi-series: 각 그룹은 별도 series → 서로 다른 itemStyle.color
    const semiColor = getStockColor(series, stocks[0].name) // 반도체 첫 번째
    const dispColor = getStockColor(series, stocks[2].name) // 디스플레이 첫 번째

    // 두 그룹은 서로 다른 색상
    expect(semiColor).not.toBe(dispColor)
  })

  it('sector_minor가 null인 종목은 회색(#9CA3AF)으로 표시된다', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 1 },
      { sector_minor: null, count: 1 },
    ])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const series = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>
    expect(series).toBeDefined()

    // multi-series: null 종목은 "기타" series에 속하고 해당 series.itemStyle.color가 #9CA3AF
    const nullStock = stocks[1]
    const nullColor = getStockColor(series, nullStock.name)
    expect(nullColor).toBe('#9CA3AF')
  })
})

// ==============================================================
// AC-5: 동적 범례 컨텐츠 — sector_minor 그룹 + 기타
// ==============================================================
describe('AC-5: 동적 범례는 sector_minor 그룹 + 기타로 구성된다', () => {
  it('legend.data 길이는 고유 sector_minor 수 + 1(기타), series.length === legend.data.length', () => {
    // sector_minor 3종류 + null 1개 → legend 4개 (반도체, 디스플레이, 장비, 기타)
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 3 },
      { sector_minor: '디스플레이', count: 2 },
      { sector_minor: '장비', count: 1 },
      { sector_minor: null, count: 1 },
    ])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legendData = (capturedOption?.legend as { data: Array<{ name: string }> })?.data
    expect(legendData).toBeDefined()
    expect(legendData.length).toBe(4) // 3개 그룹 + 기타

    // multi-series: series 수 === legend.data 수, 각 이름 일치 확인
    const series = capturedOption?.series as Array<{ name?: string }>
    expect(series).toBeDefined()
    expect(series.length).toBe(legendData.length)
    series.forEach((s, idx) => {
      expect(s.name).toBe(legendData[idx].name)
    })
  })

  it('"기타" 항목이 legend.data의 마지막에 위치한다', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 2 },
      { sector_minor: null, count: 1 },
    ])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legendData = (capturedOption?.legend as { data: Array<{ name: string }> })?.data
    expect(legendData).toBeDefined()

    const lastEntry = legendData[legendData.length - 1]
    expect(lastEntry?.name ?? lastEntry).toBe('기타')
  })

  it('sector_minor가 10개를 초과할 때(N=11) 초과분 + null은 "기타"로 흡수 → legend 길이 11', () => {
    // palette 10개 + 기타 1개 → total 11
    const groups = Array.from({ length: 11 }, (_, i) => ({
      sector_minor: `섹터${i + 1}`,
      count: 1,
    }))
    // null도 추가
    const stocks = makeStocks([...groups, { sector_minor: null, count: 1 }])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legendData = (capturedOption?.legend as { data: unknown[] })?.data
    expect(legendData).toBeDefined()
    // palette 10개까지만 개별 항목, 나머지는 기타로 → 총 11개
    expect(legendData.length).toBe(11)
  })
})

// ==============================================================
// AC-6: 범례 클릭 — series.name 기반 그룹 토글
// ==============================================================
describe('AC-6: 범례 선택 상태가 series 데이터에 반영된다', () => {
  it('series[i].name === legend.data[i].name 일치 → ECharts 범례 클릭 토글 보장', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 2 },
      { sector_minor: '디스플레이', count: 1 },
    ])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const series = capturedOption?.series as Array<{ name?: string }>
    const legendData = (capturedOption?.legend as { data: Array<{ name: string }> })?.data
    expect(series).toBeDefined()
    expect(legendData).toBeDefined()

    // multi-series: 각 series item이 name 속성을 가지고 있어야 legend 토글이 가능
    series.forEach((s) => {
      expect(s.name).toBeDefined()
    })

    // series[i].name === legend.data[i].name 일대일 매칭 (ECharts 범례 자동 토글 조건)
    expect(series.length).toBe(legendData.length)
    series.forEach((s, idx) => {
      expect(s.name).toBe(legendData[idx].name)
    })

    // '반도체' series가 legend.data에 있고 이름이 매칭됨
    const semiSeriesName = series.find((s) => s.name === '반도체')?.name
    const semiLegendName = legendData.find((d) => d.name === '반도체')?.name
    expect(semiSeriesName).toBe(semiLegendName)
    expect(semiSeriesName).toBeDefined()
  })
})

// ==============================================================
// AC-7 / AC-SUX-051 (VZ-13): 종목 버블 산점도 series.emphasis.focus === 'none'
// (개별 버블 hover 시 해당 버블만 강조 — 다른 series 블러 없음. M5 의도 변경: 기존 'series' → 'none')
// RRG/Bump 의 focus:'series' 는 유지(선 차트 궤적 추적). 본 단언은 종목 버블 산점도 한정.
// ==============================================================
describe('AC-7/AC-SUX-051: 종목 버블 hover emphasis.focus === "none" (VZ-13)', () => {
  it('모든 series의 emphasis.focus가 "none"으로 설정된다 (multi-series)', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 2 },
      { sector_minor: '디스플레이', count: 1 },
    ])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const series = capturedOption?.series as Array<{
      emphasis?: { focus?: string }
    }>
    expect(series).toBeDefined()
    expect(series.length).toBeGreaterThanOrEqual(1)

    // 모든 series에 emphasis.focus === 'none' 적용 확인 (VZ-13 의도 변경)
    series.forEach((s) => {
      expect(s.emphasis?.focus).toBe('none')
    })
  })
})

// ==============================================================
// AC-8: tooltip formatter — 산업명(중) 라인 + Stage 라인 보존
// ==============================================================
describe('AC-8: tooltip formatter에 산업명(중) + Stage 라인이 포함된다', () => {
  it('sector_minor가 있는 종목 tooltip에 "산업명(중): 반도체" 포함', () => {
    const stocks = makeStocks([{ sector_minor: '반도체', count: 1, stage: 2 }])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[] } }) => string
    }
    expect(tooltip?.formatter).toBeDefined()
    expect(typeof tooltip.formatter).toBe('function')

    // formatter 직접 호출 — sector_minor는 value 배열의 특정 인덱스에 위치 예상
    // GREEN-2에서 value 배열에 sector_minor 추가 예정
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]
    expect(firstItem).toBeDefined()

    const html = tooltip.formatter!({ data: firstItem as { value: unknown[] } })
    expect(html).toContain('산업명(중): 반도체')
  })

  it('sector_minor가 null인 종목 tooltip에 "산업명(중): 기타" 표시', () => {
    const stocks = makeStocks([{ sector_minor: null, count: 1, stage: 2 }])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[] } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip?.formatter!({ data: firstItem as { value: unknown[] } })
    expect(html).toContain('산업명(중): 기타')
  })

  it('Stage 라인이 tooltip에 여전히 포함된다 (회귀 방지)', () => {
    const stocks = makeStocks([{ sector_minor: '반도체', count: 1, stage: 2 }])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[] } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip?.formatter!({ data: firstItem as { value: unknown[] } })
    // Stage 라인 형식 유지 — "Stage:" 키워드 포함
    expect(html).toMatch(/Stage\s*:/)
  })
})

// ==============================================================
// AC-9: 색상 매핑 결정성 round-trip
// ==============================================================
describe('AC-9: 색상 매핑 결정성', () => {
  it('같은 stocks 입력으로 두 번 render해도 종목별 series 색상 배열이 동일하다', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 2 },
      { sector_minor: '디스플레이', count: 1 },
      { sector_minor: null, count: 1 },
    ])

    // 첫 번째 render
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)
    // multi-series: 각 종목의 색상은 해당 series.itemStyle.color에서 가져옴
    const series1 = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>
    const firstColorMap = stocks.map((s) => ({
      name: s.name,
      color: getStockColor(series1, s.name),
    }))

    cleanup()
    capturedOption = {}

    // 두 번째 render (같은 입력)
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)
    const series2 = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>
    const secondColorMap = stocks.map((s) => ({
      name: s.name,
      color: getStockColor(series2, s.name),
    }))

    expect(firstColorMap).toBeDefined()
    expect(secondColorMap).toBeDefined()
    expect(firstColorMap).toEqual(secondColorMap)
  })

  it('rerender() 2-pass 색상 일관성 (AC-9 amendment)', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 2 },
      { sector_minor: '디스플레이', count: 1 },
      { sector_minor: null, count: 1 },
    ])

    // 첫 번째 render
    const { rerender } = render(<StockBubbleChart stocks={stocks} sectorName="IT" />)
    const series1 = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>
    const colors1 = stocks.map((s) => ({
      name: s.name,
      color: getStockColor(series1, s.name),
    }))

    // 동일 props로 rerender
    rerender(<StockBubbleChart stocks={stocks} sectorName="IT" />)
    const series2 = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>
    const colors2 = stocks.map((s) => ({
      name: s.name,
      color: getStockColor(series2, s.name),
    }))

    // rerender 전후 색상 완전 일치
    expect(colors2).toEqual(colors1)
  })

  it('shuffle된 stocks 배열도 동일한 sector_minor→color 매핑을 반환한다', () => {
    const stocks = makeStocks([
      { sector_minor: '반도체', count: 2 },
      { sector_minor: '디스플레이', count: 2 },
    ])

    // 원래 순서로 render
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)
    const series1 = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>

    // sector_minor별 색상 맵 구성 (series 레벨)
    const colorMap1: Record<string, string> = {}
    stocks.forEach((s) => {
      const color = getStockColor(series1, s.name)
      if (color && s.sector_minor) {
        colorMap1[s.sector_minor] = color
      }
    })

    cleanup()
    capturedOption = {}

    // shuffle된 순서로 render
    const shuffled = [...stocks].reverse()
    render(<StockBubbleChart stocks={shuffled} sectorName="IT" />)
    const series2 = capturedOption?.series as Array<{
      name?: string
      itemStyle?: { color?: string }
      data?: Array<{ value: unknown[] }>
    }>

    const colorMap2: Record<string, string> = {}
    shuffled.forEach((s) => {
      const color = getStockColor(series2, s.name)
      if (color && s.sector_minor) {
        colorMap2[s.sector_minor] = color
      }
    })

    // 두 맵이 일치해야 결정성이 보장됨
    expect(colorMap1).toEqual(colorMap2)
  })
})

// ==============================================================
// SPEC-STOCK-TOOLTIP-PRODUCT-001: AC-3 ~ AC-7 product 필드 + tooltip 테스트
// ==============================================================

// ==============================================================
// AC-3 (product): StockBubbleItem 타입에 product 필드 존재 여부
// ==============================================================
describe('SPEC-STOCK-TOOLTIP-PRODUCT-001 AC-3: StockBubbleItem 타입에 product 필드 존재', () => {
  it('StockBubbleItem 타입에 product: string | null 필드가 존재한다 (정적 단언)', () => {
    const typesPath = path.resolve(__dirname, '../../../types/bubble.ts')
    const src = fs.readFileSync(typesPath, 'utf-8')
    // product 필드 선언 패턴 확인
    expect(src).toMatch(/product\s*[?:]/)
  })

  it('product가 string | null 타입으로 선언된다', () => {
    const typesPath = path.resolve(__dirname, '../../../types/bubble.ts')
    const src = fs.readFileSync(typesPath, 'utf-8')
    // "product?: string | null" 또는 "product: string | null" 형태
    expect(src).toMatch(/product\s*\??\s*:\s*string\s*\|\s*null/)
  })

  it('필드명이 정확히 product이다 (main_product, mainProduct 변형 없음, REQ-STP-007)', () => {
    const typesPath = path.resolve(__dirname, '../../../types/bubble.ts')
    const src = fs.readFileSync(typesPath, 'utf-8')
    // main_product 변형이 없어야 함
    expect(src).not.toMatch(/main_product/)
    expect(src).not.toMatch(/mainProduct/)
  })
})

// ==============================================================
// AC-4: tooltip formatter에 주요제품 라인 + 라인 순서
// ==============================================================
describe('SPEC-STOCK-TOOLTIP-PRODUCT-001 AC-4: tooltip에 주요제품 라인 포함 + 라인 순서', () => {
  it('product 값이 있는 종목 tooltip에 "주요제품: 반도체용 검사장비" 라인이 포함된다', () => {
    const stocks = [
      {
        name: '삼성전자',
        price_change: 1.5,
        rs_12m: 70,
        trading_value: 100_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
        product: '반도체용 검사장비',
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[]; sector_minor?: string | null; product?: string | null } }) => string
    }
    expect(tooltip?.formatter).toBeDefined()

    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]
    expect(firstItem).toBeDefined()

    const html = tooltip.formatter!({ data: firstItem as { value: unknown[]; sector_minor?: string | null; product?: string | null } })
    expect(html).toContain('주요제품: 반도체용 검사장비')
  })

  it('tooltip 라인 순서: 산업명(중) < 주요제품 < Stage 순서로 표시된다 (AC-4)', () => {
    const stocks = [
      {
        name: '삼성전자',
        price_change: 1.5,
        rs_12m: 70,
        trading_value: 100_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
        product: '반도체용 검사장비',
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[]; sector_minor?: string | null; product?: string | null } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip!.formatter!({ data: firstItem as { value: unknown[]; sector_minor?: string | null; product?: string | null } })
    const sectorMinorIdx = html.indexOf('산업명(중):')
    const productIdx = html.indexOf('주요제품:')
    const stageIdx = html.indexOf('Stage:')

    expect(sectorMinorIdx).toBeGreaterThanOrEqual(0)
    expect(productIdx).toBeGreaterThan(sectorMinorIdx)
    expect(stageIdx).toBeGreaterThan(productIdx)
  })

  it('tooltip에 산업명(중) + Stage 라인이 동시에 포함된다 (AC-4 회귀 방지)', () => {
    const stocks = [
      {
        name: '삼성전자',
        price_change: 1.5,
        rs_12m: 70,
        trading_value: 100_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
        product: '반도체용 검사장비',
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[]; sector_minor?: string | null; product?: string | null } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip!.formatter!({ data: firstItem as { value: unknown[]; sector_minor?: string | null; product?: string | null } })
    expect(html).toContain('산업명(중): 반도체')
    expect(html).toMatch(/Stage\s*:/)
  })
})

// ==============================================================
// AC-5: tooltip product NULL/빈 fallback → "주요제품: —"
// ==============================================================
describe('SPEC-STOCK-TOOLTIP-PRODUCT-001 AC-5: product NULL/빈 fallback', () => {
  it('product가 null인 종목 tooltip에 "주요제품: —" 라인이 표시된다', () => {
    const stocks = [
      {
        name: '종목A',
        price_change: 1.0,
        rs_12m: 60,
        trading_value: 100_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
        product: null,
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[]; sector_minor?: string | null; product?: string | null } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip!.formatter!({ data: firstItem as { value: unknown[]; sector_minor?: string | null; product?: string | null } })
    expect(html).toContain('주요제품: —')
  })

  it('product가 빈 문자열인 종목 tooltip에 "주요제품: —" 라인이 표시된다', () => {
    const stocks = [
      {
        name: '종목B',
        price_change: 1.0,
        rs_12m: 60,
        trading_value: 100_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
        product: '',
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[]; sector_minor?: string | null; product?: string | null } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip!.formatter!({ data: firstItem as { value: unknown[]; sector_minor?: string | null; product?: string | null } })
    expect(html).toContain('주요제품: —')
  })
})

// ==============================================================
// AC-6 (product): 직전 SPEC 회귀 게이트 재실행 — product 추가 후 회귀 없음
// ==============================================================
describe('SPEC-STOCK-TOOLTIP-PRODUCT-001 AC-6: 직전 SPEC 회귀 게이트 (product 추가 후)', () => {
  it('sector_minor 기준 색상 매핑이 product 추가 후에도 유지된다 (직전 AC-4 회귀)', () => {
    const stocks = [
      { name: '반도체A', price_change: 1, rs_12m: 70, trading_value: 100_000_000, stage: 1, stage_detail: null, market_cap: 1_000_000_000, volume_ratio: 1.0, sector_minor: '반도체', product: '메모리' },
      { name: '반도체B', price_change: 2, rs_12m: 80, trading_value: 200_000_000, stage: 2, stage_detail: 'entry', market_cap: 1_000_000_000, volume_ratio: 1.0, sector_minor: '반도체', product: '파운드리' },
      { name: '반도체C', price_change: 3, rs_12m: 60, trading_value: 150_000_000, stage: 4, stage_detail: null, market_cap: 1_000_000_000, volume_ratio: 1.0, sector_minor: '반도체', product: null },
      { name: '디스플레이A', price_change: -1, rs_12m: 50, trading_value: 80_000_000, stage: 3, stage_detail: null, market_cap: 500_000_000, volume_ratio: 0.8, sector_minor: '디스플레이', product: 'OLED' },
      { name: '디스플레이B', price_change: -2, rs_12m: 40, trading_value: 70_000_000, stage: 4, stage_detail: null, market_cap: 400_000_000, volume_ratio: 0.7, sector_minor: '디스플레이', product: null },
      { name: '기타종목', price_change: 0, rs_12m: 55, trading_value: 60_000_000, stage: 2, stage_detail: null, market_cap: 300_000_000, volume_ratio: 1.0, sector_minor: null, product: null },
    ] as unknown as StockBubbleItem[]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const series = capturedOption?.series as Array<{ name?: string; itemStyle?: { color?: string }; data?: Array<{ value: unknown[] }> }>
    expect(series).toBeDefined()

    // 반도체 3개 동일 색상
    const colorA = getStockColor(series, '반도체A')
    const colorB = getStockColor(series, '반도체B')
    const colorC = getStockColor(series, '반도체C')
    expect(colorA).toBeDefined()
    expect(colorA).toBe(colorB)
    expect(colorA).toBe(colorC)

    // 디스플레이 2개 동일 색상
    const colorDA = getStockColor(series, '디스플레이A')
    const colorDB = getStockColor(series, '디스플레이B')
    expect(colorDA).toBeDefined()
    expect(colorDA).toBe(colorDB)

    // null 종목은 회색 #9CA3AF
    const nullColor = getStockColor(series, '기타종목')
    expect(nullColor).toBe('#9CA3AF')

    // 반도체 ≠ 디스플레이 ≠ 기타
    expect(colorA).not.toBe(colorDA)
    expect(colorA).not.toBe(nullColor)
  })

  it('tooltip에 산업명(중) 라인이 product 추가 후에도 존재한다 (직전 AC-8 회귀)', () => {
    const stocks = makeStocks([{ sector_minor: '반도체', count: 1, stage: 2 }])
    // product 필드 추가
    const stocksWithProduct = stocks.map(s => ({ ...s, product: '테스트제품' })) as unknown as StockBubbleItem[]

    render(<StockBubbleChart stocks={stocksWithProduct} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as { formatter?: (params: { data: { value: unknown[] } }) => string }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip!.formatter!({ data: firstItem as { value: unknown[] } })
    expect(html).toContain('산업명(중):')
  })
})

// ==============================================================
// AC-7: XSS hardening — product에 <script> 페이로드 escape
// ==============================================================
describe('SPEC-STOCK-TOOLTIP-PRODUCT-001 AC-7: XSS hardening', () => {
  it('product에 <script> 페이로드가 있을 때 raw script 태그가 포함되지 않는다', () => {
    const stocks = [
      {
        name: '종목XSS',
        price_change: 1.0,
        rs_12m: 60,
        trading_value: 100_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '반도체',
        product: "<script>alert('xss')</script>",
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[]; sector_minor?: string | null; product?: string | null } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip!.formatter!({ data: firstItem as { value: unknown[]; sector_minor?: string | null; product?: string | null } })
    // raw <script> 태그가 없어야 함
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('</script>')
    // escape된 문자열이 포함되어야 함
    expect(html).toContain('&lt;script&gt;')
  })

  it('sector_minor에도 <img onerror> 같은 페이로드 시 escape된다 (sector_minor escapeHtml 일관성)', () => {
    const stocks = [
      {
        name: '종목XSS2',
        price_change: 1.0,
        rs_12m: 60,
        trading_value: 100_000_000,
        stage: 2,
        stage_detail: 'entry',
        market_cap: 1_000_000_000,
        volume_ratio: 1.0,
        sector_minor: '<img onerror="alert(1)">',
        product: '정상제품',
      } as unknown as StockBubbleItem,
    ]

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const tooltip = capturedOption?.tooltip as {
      formatter?: (params: { data: { value: unknown[]; sector_minor?: string | null; product?: string | null } }) => string
    }
    const seriesData = (capturedOption?.series as Array<{ data: Array<{ value: unknown[] }> }>)?.[0]?.data
    const firstItem = seriesData?.[0]

    const html = tooltip!.formatter!({ data: firstItem as { value: unknown[]; sector_minor?: string | null; product?: string | null } })
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })
})

// ==============================================================
// AC-10: Stage 시각 인코딩 회귀 방지
// ==============================================================
describe('AC-10: Stage 범례 항목이 제거되고 STAGE_COLORS 참조가 사라진다', () => {
  it('legend.data에 Stage 5-항목 라벨이 없다', () => {
    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])

    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legendData = (
      capturedOption?.legend as { data: Array<{ name: string } | string> }
    )?.data

    expect(legendData).toBeDefined()

    // Stage 라벨이 범례에 없어야 함
    const stageLabels = ['S1 (바닥)', 'S2 (상승)', 'S3 (천장)', 'S4 (하락)', '미분류']
    const legendNames = legendData.map((item) =>
      typeof item === 'string' ? item : item.name
    )

    stageLabels.forEach((label) => {
      expect(legendNames).not.toContain(label)
    })
  })

  it('StockBubbleChart.tsx 소스 파일에 STAGE_COLORS 할당이 없다 (정적 검사)', () => {
    const componentPath = path.resolve(
      __dirname,
      '../StockBubbleChart.tsx'
    )
    const src = fs.readFileSync(componentPath, 'utf-8')

    // STAGE_COLORS 변수 선언/할당이 없어야 함
    expect(src).not.toMatch(/STAGE_COLORS\s*[:=]/)
  })

  it('StockBubbleChart.tsx legend.data에 S[1-4] 패턴이 없다 (정적 검사)', () => {
    const componentPath = path.resolve(
      __dirname,
      '../StockBubbleChart.tsx'
    )
    const src = fs.readFileSync(componentPath, 'utf-8')

    // legend.data 블록에 S1~S4 라벨 포함 X
    // 단순히 소스에 'S1 (' 또는 'S2 (' 형태가 legend 관련 코드에 없는지 확인
    expect(src).not.toMatch(/['"]S[1-4]\s*\(/)
  })
})

// ==============================================================
// AC-11: 모바일 좁은 폭 — 범례 하단 배치 + grid 여백 조정
// ==============================================================
describe('AC-11: 모바일(max-width 767px) 시 범례 하단 배치', () => {
  it('matchMedia matches=true 시 legend.orient === "horizontal"', () => {
    // 모바일 환경 시뮬레이션
    mockMatchMedia(true)

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legend = capturedOption?.legend as {
      orient?: string
      bottom?: number | string
      type?: string
      right?: number | string
    }

    expect(legend?.orient).toBe('horizontal')
  })

  it('모바일 시 legend.bottom이 정의된다', () => {
    mockMatchMedia(true)

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legend = capturedOption?.legend as { bottom?: number | string }
    expect(legend?.bottom).toBeDefined()
  })

  it('모바일 시 legend.type === "scroll" (항목 수 초과 대응)', () => {
    mockMatchMedia(true)

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legend = capturedOption?.legend as { type?: string }
    expect(legend?.type).toBe('scroll')
  })

  it('모바일 시 grid.right === 60 (범례가 하단으로 이동하여 오른쪽 여백 축소)', () => {
    mockMatchMedia(true)

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const grid = capturedOption?.grid as { right?: number }
    expect(grid?.right).toBe(60)
  })

  it('모바일 시 grid.bottom === 80 (범례가 하단에 위치하므로 하단 여백 확장)', () => {
    mockMatchMedia(true)

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const grid = capturedOption?.grid as { bottom?: number }
    expect(grid?.bottom).toBe(80)
  })

  it('데스크탑(matches=false) 시 legend.orient === "vertical"', () => {
    mockMatchMedia(false) // beforeEach와 동일하지만 명시적으로

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legend = capturedOption?.legend as { orient?: string }
    expect(legend?.orient).toBe('vertical')
  })

  it('데스크탑 시 legend.right가 정의된다', () => {
    mockMatchMedia(false)

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const legend = capturedOption?.legend as { right?: number | string }
    expect(legend?.right).toBeDefined()
  })

  it('데스크탑 시 grid.right === 120 (현재 값 유지)', () => {
    mockMatchMedia(false)

    const stocks = makeStocks([{ sector_minor: '반도체', count: 2 }])
    render(<StockBubbleChart stocks={stocks} sectorName="IT" />)

    const grid = capturedOption?.grid as { right?: number }
    expect(grid?.right).toBe(120)
  })
})
