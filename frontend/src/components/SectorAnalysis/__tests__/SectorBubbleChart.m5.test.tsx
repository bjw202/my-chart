// AC-SUX-039/040(섹터)/041/042(섹터)/043/059 — SectorBubbleChart M5 (시각화 규약)
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import { SectorBubbleChart, sectorReturnColor } from '../SectorBubbleChart'
import type { SectorBubbleItem } from '../../../types/bubble'

let capturedOption: Record<string, unknown> = {}
vi.mock('echarts-for-react', () => ({
  default: vi.fn((props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  }),
}))

function makeSectors(
  overrides: Partial<SectorBubbleItem>[] = [],
): SectorBubbleItem[] {
  const base: SectorBubbleItem[] = [
    { name: '반도체', excess_return: 2.5, rs_avg: 60, trading_value: 5e11, period_return: 4 },
    { name: '디스플레이', excess_return: -1.2, rs_avg: 45, trading_value: 8e10, period_return: -3 },
    { name: '장비', excess_return: 5.0, rs_avg: 70, trading_value: 2e12, period_return: 15 },
  ]
  return [...base, ...overrides.map(o => ({ ...{
    name: 'x', excess_return: 0, rs_avg: 50, trading_value: 1e11, period_return: 0,
  }, ...o }))]
}

interface DataPoint { value: (string | number)[]; itemStyle?: { color?: string; borderType?: string; borderWidth?: number } }

beforeEach(() => { capturedOption = {} })
afterEach(() => { vi.restoreAllMocks(); cleanup() })

describe('AC-SUX-039 — 크기 범례 (VZ-2, 기간별 고정 눈금)', () => {
  // M5.5(SPEC-SECTOR-METRIC-UNIFY-001) — 섹터 버블 사다리가 SECTOR_PERIOD_SIZE_LADDER
  // (억원 VolumeWon 기준, AC-SMU-018 재산출)로 분리됨에 따라 참조 리터럴 갱신.
  it('1W 범례 참조값 3개 = 1,000억/3조/100조 리터럴 + 기간 병기 텍스트', () => {
    const { container } = render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="1w" />)
    const legend = container.querySelector('[data-testid="sector-size-legend"]')
    expect(legend).not.toBeNull()
    expect(legend!.textContent).toContain('1W')
    const values = Array.from(legend!.querySelectorAll('.bubble-size-legend-value')).map(e => e.textContent)
    expect(values).toEqual(['1,000억', '3조', '100조'])
  })

  it('3M 범례 참조값 = 1조/30조/1,000조', () => {
    const { container } = render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="3m" />)
    const values = Array.from(container.querySelectorAll('.bubble-size-legend-value')).map(e => e.textContent)
    expect(values).toEqual(['1조', '30조', '1,000조'])
  })

  it('데이터 불변 — 거래대금 분포가 전혀 달라도 범례 값 3개는 동일 (데이터 적응형이면 실패)', () => {
    const small = makeSectors([{ name: '소액', trading_value: 1e9, period_return: 1 }])
    const big = makeSectors([{ name: '거액', trading_value: 1e14, period_return: 1 }])
    const { container, rerender } = render(<SectorBubbleChart sectors={small} onSectorClick={() => {}} period="1w" />)
    const v1 = Array.from(container.querySelectorAll('.bubble-size-legend-value')).map(e => e.textContent)
    rerender(<SectorBubbleChart sectors={big} onSectorClick={() => {}} period="1w" />)
    const v2 = Array.from(container.querySelectorAll('.bubble-size-legend-value')).map(e => e.textContent)
    expect(v1).toEqual(v2)
    expect(v1).toEqual(['1,000억', '3조', '100조'])
  })
})

describe('AC-SUX-040 (섹터) — 결측 거래대금 → 최소크기 + 점선 테두리 + 툴팁', () => {
  it('trading_value:null 버블 symbolSize = 2×rMin(=14), borderType=dashed', () => {
    const sectors = makeSectors([{ name: '결측', trading_value: null, period_return: 1 }])
    render(<SectorBubbleChart sectors={sectors} onSectorClick={() => {}} period="1w" />)
    const seriesArr = capturedOption.series as unknown as Array<{ data: DataPoint[] }>
    const pts = seriesArr[0].data
    const missing = pts.find(p => Number(p.value[2]) === 14) // 지름 14 = 2×rMin
    expect(missing).toBeDefined()
    expect(missing!.itemStyle?.borderType).toBe('dashed')
  })

  it('결측이 아닌 버블은 점선 테두리가 아니다 (색상만)', () => {
    render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="1w" />)
    const pts = (capturedOption.series as unknown as Array<{ data: DataPoint[] }>)[0].data
    const normal = pts.find(p => Number(p.value[2]) !== 14)
    expect(normal).toBeDefined()
    expect(normal!.itemStyle?.borderType ?? 'solid').not.toBe('dashed')
    expect(normal!.itemStyle?.color).toBeDefined()
  })
})

describe('AC-SUX-041 — axisPointer 삭제 (VZ-4)', () => {
  it('xAxis 에 axisPointer 키가 없다; markLine 은 존재', () => {
    render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="1w" />)
    const xAxis = capturedOption.xAxis as Record<string, unknown>
    expect(xAxis.axisPointer).toBeUndefined()
    const series = (capturedOption.series as unknown as Array<{ markLine?: unknown }>)[0]
    expect(series.markLine).toBeDefined()
  })
})

describe('AC-SUX-042 (섹터) — 기준선 라벨에 벤치마크 이름 (VZ-5)', () => {
  it('market=all → X=0 markLine 라벨에 "전체 상한가중" 포함', () => {
    render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="1w" market="all" />)
    const series = (capturedOption.series as unknown as Array<{ markLine: { data: Array<{ label?: { formatter?: string } }> } }>)[0]
    const xLine = series.markLine.data.find(d => 'xAxis' in d)
    expect(xLine?.label?.formatter).toContain('전체 상한가중')
  })

  it('market=kospi → 라벨에 "KOSPI" 포함 (시장 토글 추종)', () => {
    render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="1w" market="kospi" />)
    const series = (capturedOption.series as unknown as Array<{ markLine: { data: Array<{ label?: { formatter?: string } }> } }>)[0]
    const xLine = series.markLine.data.find(d => 'xAxis' in d)
    expect(xLine?.label?.formatter).toContain('KOSPI')
  })
})

describe('AC-SUX-043 — 축 범위 (VZ-6: 0 항상 포함, Y 0-100 고정)', () => {
  it('xAxis.min 은 함수이며, 전부 양수 fixture 에서도 min <= 0 반환', () => {
    const allPositive = makeSectors([{ name: 'p1', excess_return: 3, period_return: 1 }, { name: 'p2', excess_return: 5, period_return: 2 }])
    render(<SectorBubbleChart sectors={allPositive} onSectorClick={() => {}} period="1w" />)
    const xAxis = capturedOption.xAxis as { min: (v: { min: number }) => number }
    expect(typeof xAxis.min).toBe('function')
    expect(xAxis.min({ min: 2.5 })).toBeLessThanOrEqual(0)
  })

  it('yAxis 는 min:0, max:100 고정', () => {
    render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="1w" />)
    const yAxis = capturedOption.yAxis as { min: number; max: number }
    expect(yAxis.min).toBe(0)
    expect(yAxis.max).toBe(100)
  })
})

describe('AC-SUX-059 — 섹터 버블 색상: 발산형 5단계 (REQ-SUX-056, 기준 0%)', () => {
  it('기간 수익률 [-12,-3,0,4,15] → 5개 서로 다른 색 (발산형 매핑)', () => {
    const returns = [-12, -3, 0, 4, 15]
    const colors = returns.map(r => sectorReturnColor(r))
    expect(new Set(colors).size).toBe(5)
  })

  it('0% → 중립색(팔레트 중앙 gray). 벤치마크 값과 무관 (기준점 0%)', () => {
    expect(sectorReturnColor(0)).toBe('#9CA3AF')
    // 벤치마크가 +1.88% 여도 0% 버블은 중립 — 발산 기준점은 0% 다
    expect(sectorReturnColor(0)).toBe(sectorReturnColor(0))
  })

  it('period_return:null → 결측 전용색 — 중립(0%) 회색과 구분된다 (B2, SPEC-SECTOR-METRIC-UNIFY-001)', () => {
    const missingColor = sectorReturnColor(null)
    expect(missingColor).not.toBe('#9CA3AF') // 중립(보합)과 같으면 B2 회귀
    const sectors = makeSectors([
      { name: '결측PR', excess_return: 1, period_return: null },
      { name: '보합', excess_return: 1, period_return: 0 },
    ])
    render(<SectorBubbleChart sectors={sectors} onSectorClick={() => {}} period="1w" />)
    const pts = (capturedOption.series as unknown as Array<{ data: DataPoint[] }>)[0].data
    const byName = (n: string) => pts.find(p => p.value[4] === n)!
    expect(byName('결측PR').itemStyle?.color).toBe(missingColor)
    expect(byName('보합').itemStyle?.color).toBe('#9CA3AF')
    expect(byName('결측PR').itemStyle?.color).not.toBe(byName('보합').itemStyle?.color)
  })

  it('색상 범례가 5개 구간을 실제 값 텍스트와 렌더', () => {
    const { container } = render(<SectorBubbleChart sectors={makeSectors()} onSectorClick={() => {}} period="1w" />)
    const legend = container.querySelector('[data-testid="sector-color-legend"]')
    expect(legend).not.toBeNull()
    const labels = Array.from(legend!.querySelectorAll('.bubble-color-legend-label')).map(e => e.textContent)
    expect(labels).toEqual(['≤−10%', '−10% ~ −3%', '−3% ~ +3%', '+3% ~ +10%', '≥+10%'])
  })

  it('채널 독립 — 기간수익률만 바꾸면 색이 바뀌고, 초과수익률만 바꾸면 색이 안 바뀐다 (VZ-0)', () => {
    // (1) 동일 초과수익률(excess=1), 기간수익률만 다른 두 버블 → 색 다름
    const sameExcess = makeSectors([
      { name: 'A', excess_return: 1, period_return: -8 },
      { name: 'B', excess_return: 1, period_return: 8 },
    ])
    render(<SectorBubbleChart sectors={sameExcess} onSectorClick={() => {}} period="1w" />)
    const pts1 = (capturedOption.series as unknown as Array<{ data: DataPoint[] }>)[0].data
    const colorA = pts1.find(p => p.value[4] === 'A')!.itemStyle?.color
    const colorB = pts1.find(p => p.value[4] === 'B')!.itemStyle?.color
    expect(colorA).not.toBe(colorB)
    // (2) 동일 기간수익률(period_return=5), 초과수익률만 다른 두 버블 → 색 동일 (X축 중복 인코딩 아님)
    const sameReturn = makeSectors([
      { name: 'C', excess_return: -3, period_return: 5 },
      { name: 'D', excess_return: 4, period_return: 5 },
    ])
    render(<SectorBubbleChart sectors={sameReturn} onSectorClick={() => {}} period="1w" />)
    const pts2 = (capturedOption.series as unknown as Array<{ data: DataPoint[] }>)[0].data
    const colorC = pts2.find(p => p.value[4] === 'C')!.itemStyle?.color
    const colorD = pts2.find(p => p.value[4] === 'D')!.itemStyle?.color
    expect(colorC).toBe(colorD)
  })

  it('렌더된 버블의 itemStyle.color 가 sectorReturnColor(period_return) 와 일치', () => {
    const sectors = makeSectors([
      { name: '강음', excess_return: 1, period_return: -12 },
      { name: '강양', excess_return: 2, period_return: 15 },
      { name: '중립', excess_return: 0, period_return: 0 },
    ])
    render(<SectorBubbleChart sectors={sectors} onSectorClick={() => {}} period="1w" />)
    const pts = (capturedOption.series as unknown as Array<{ data: DataPoint[] }>)[0].data
    const byName = (n: string) => pts.find(p => p.value[4] === n)!
    expect(byName('강음').itemStyle?.color).toBe(sectorReturnColor(-12))
    expect(byName('강양').itemStyle?.color).toBe(sectorReturnColor(15))
    expect(byName('중립').itemStyle?.color).toBe('#9CA3AF')
  })
})
