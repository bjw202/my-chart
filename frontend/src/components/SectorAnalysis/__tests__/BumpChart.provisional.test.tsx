// Bump 잠정점(2026-10-22 사용자 결정) — 진행 중인 주의 순위를 마지막 점으로 그린다.
// 표는 진행 중인 주 바로 순위를 매기는데 Bump 마지막 점은 끝난 주라 마지막 순위가 표와 달랐다.
// 서버가 history 끝에 `provisional: true` 점을 한 개 덧붙이면, Bump 는 마지막 끝난 점 → 잠정점 구간을
// 점선으로, 잠정점을 속 빈 기호로 그리고, 축·툴팁·캡션에 '잠정'을 표기한다.
// Top-N 필터와 endLabel 은 잠정점 순위를 기준으로 한다(사용자 결정).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { SectorHistoryResponse } from '../../../api/history'

interface Series {
  name?: string
  data: Array<number | null | { value: number; symbol?: string }>
  lineStyle?: { type?: string }
  endLabel?: { show?: boolean }
}
interface Option {
  series: Series[]
  xAxis: { data: string[]; axisLabel: { formatter: (v: string) => string; showMaxLabel?: boolean } }
  tooltip: { formatter: (p: unknown) => string }
}

let capturedOption: Option | null = null
let capturedEvents: Record<string, (p: unknown) => void> | null = null
vi.mock('echarts-for-react', () => ({
  default: (props: { option: unknown; onEvents?: Record<string, (p: unknown) => void> }) => {
    capturedOption = props.option as Option
    capturedEvents = props.onEvents ?? null
    return <div data-testid="bump-echarts" />
  },
}))

const mockFetchSectorHistory = vi.fn()
vi.mock('../../../api/history', () => ({
  fetchSectorHistory: (...args: unknown[]) => mockFetchSectorHistory(...args),
}))

import { BumpChart } from '../BumpChart'

const P1 = '2026-10-09'
const P2 = '2026-10-16'
const PROV = '2026-10-21'

function week(date: string, rank: number, provisional = false) {
  return {
    date, rank, composite_score: 100 - rank, sector_return_1w: 0,
    sector_excess_return_1w: 0, rs_avg: 50, provisional,
  }
}

// 끝난 주(P2) 순위 A1 B2 C3 D4, 잠정점(PROV) 순위 B1 C2 A3 — D 는 잠정점이 없다.
function makeFixture(): SectorHistoryResponse {
  return {
    weeks: 2,
    span_days: 7,
    provisional_date: PROV,
    sectors: [
      { name: 'A', history: [week(P1, 1), week(P2, 1), week(PROV, 3, true)] },
      { name: 'B', history: [week(P1, 2), week(P2, 2), week(PROV, 1, true)] },
      { name: 'C', history: [week(P1, 3), week(P2, 3), week(PROV, 2, true)] },
      { name: 'D', history: [week(P1, 4), week(P2, 4)] },
    ],
  }
}

function opt(): Option {
  if (!capturedOption) throw new Error('option not captured')
  return capturedOption
}

function seriesOf(name: string): { solid: Series; dashed?: Series } {
  const all = opt().series.filter(s => s.name === name)
  const dashed = all.find(s => s.lineStyle?.type === 'dashed')
  const solid = all.find(s => s.lineStyle?.type !== 'dashed')
  if (!solid) throw new Error(`no solid series for ${name}`)
  return { solid, dashed }
}

function valueAt(s: Series, i: number): number | null {
  const v = s.data[i]
  return v === null || v === undefined ? null : typeof v === 'number' ? v : v.value
}

beforeEach(() => {
  capturedOption = null
  capturedEvents = null
  mockFetchSectorHistory.mockReset()
  mockFetchSectorHistory.mockResolvedValue(makeFixture())
})

async function renderChart(props: Parameters<typeof BumpChart>[0] = {}) {
  render(<BumpChart {...props} />)
  await waitFor(() => expect(capturedOption).not.toBeNull())
}

describe('Bump 잠정점 — 점선 구간·속 빈 기호', () => {
  it('끝난 주는 실선, 마지막 끝난 점 → 잠정점은 같은 이름의 점선 시리즈로 그린다', async () => {
    await renderChart()
    const dates = opt().xAxis.data
    expect(dates).toEqual([P1, P2, PROV])
    const iP2 = dates.indexOf(P2)
    const iProv = dates.indexOf(PROV)

    const { solid, dashed } = seriesOf('A')
    expect(valueAt(solid, iP2)).toBe(1)
    expect(valueAt(solid, iProv)).toBeNull()          // 실선은 잠정점까지 잇지 않는다
    expect(dashed).toBeDefined()
    expect(valueAt(dashed!, 0)).toBeNull()
    expect(valueAt(dashed!, iP2)).toBe(1)
    expect(valueAt(dashed!, iProv)).toBe(3)
    const provItem = dashed!.data[iProv] as { symbol?: string }
    expect(provItem.symbol).toBe('emptyCircle')
  })

  it('endLabel 은 잠정점이 있으면 점선 시리즈 끝에, 없으면 실선 끝에 붙는다', async () => {
    await renderChart()
    const a = seriesOf('A')
    expect(a.dashed?.endLabel?.show).toBe(true)
    expect(a.solid.endLabel?.show).toBe(false)
    const d = seriesOf('D')
    expect(d.dashed).toBeUndefined()
    expect(d.solid.endLabel?.show).toBe(true)
  })

  it('잠정점이 없으면 시리즈를 나누지 않는다 (섹터당 1개)', async () => {
    const fx = makeFixture()
    fx.provisional_date = null
    fx.sectors = fx.sectors.map(s => ({ ...s, history: s.history.filter(w => !w.provisional) }))
    mockFetchSectorHistory.mockResolvedValue(fx)
    await renderChart()
    expect(opt().series.map(s => s.name)).toEqual(['A', 'B', 'C', 'D'])
    expect(opt().series.every(s => s.lineStyle?.type !== 'dashed')).toBe(true)
  })
})

describe('Bump 잠정점 — 축·툴팁·캡션 표기', () => {
  it('x축 라벨에 (잠정)을 붙인다', async () => {
    await renderChart()
    const fmt = opt().xAxis.axisLabel.formatter
    expect(fmt(PROV)).toBe(`${PROV} (잠정)`)
    expect(fmt(P2)).toBe(P2)
  })

  it('툴팁에 잠정 줄을 더한다', async () => {
    await renderChart()
    const html = opt().tooltip.formatter({ seriesName: 'A', name: PROV, value: 3 })
    expect(html).toContain('순위: 3위')
    expect(html).toContain('잠정 — 주 진행 중')
    expect(opt().tooltip.formatter({ seriesName: 'A', name: P2, value: 1 })).not.toContain('잠정')
  })

  it('기준 캡션은 마지막 점을 잠정(주 진행 중)으로 표기한다', async () => {
    render(<BumpChart period="1m" market="all" />)
    await waitFor(() => expect(screen.getByTestId('bump-basis-caption').textContent).toContain(PROV))
    expect(screen.getByTestId('bump-basis-caption').textContent).toBe(
      `순위 기준: 1M 초과수익률 · All (표와 같은 기준 · 5종목 미만 섹터 포함 · 마지막 점 ${PROV} 잠정(주 진행 중))`)
  })

  // 감사 F1: 표는 AG-5 로 5종목 미만 섹터를 빼고 Bump 는 포함한다(AC-SUX-019) — 같은 기준이라도
  // 순위 숫자는 다를 수 있으므로 캡션이 '포함'을 밝혀 같은 순위로 읽히지 않게 한다.
  it('기준 캡션은 Bump 가 5종목 미만 섹터를 포함함을 밝힌다', async () => {
    render(<BumpChart period="1m" market="kospi" />)
    await waitFor(() => expect(screen.getByTestId('bump-basis-caption').textContent).toContain(PROV))
    expect(screen.getByTestId('bump-basis-caption').textContent).toContain('5종목 미만 섹터 포함')
  })

  // 감사 F3: 26주(날짜 27개, interval 3)면 마지막 라벨이 건너뛰어져 '(잠정)'이 안 보였다.
  it('x축은 마지막 라벨을 항상 그린다 (showMaxLabel)', async () => {
    await renderChart()
    expect(opt().xAxis.axisLabel.showMaxLabel).toBe(true)
  })

  // 감사 F4: 하단 구간 캡션은 응답 값 그대로(AC-SUX-028)라 잠정점이 빠진 점 개수로 보인다 — 꼬리표로 밝힌다.
  it('구간 캡션은 잠정점이 있으면 응답 값 뒤에 + 잠정 1점을 붙인다', async () => {
    await renderChart()
    await waitFor(() => expect(screen.getByTestId('bump-span-caption')).toBeInTheDocument())
    expect(screen.getByTestId('bump-span-caption').textContent).toBe('2주 (7일) + 잠정 1점')
  })

  it('구간 캡션은 잠정점이 없으면 응답 값 그대로다', async () => {
    const fx = makeFixture()
    fx.provisional_date = null
    fx.sectors = fx.sectors.map(s => ({ ...s, history: s.history.filter(w => !w.provisional) }))
    mockFetchSectorHistory.mockResolvedValue(fx)
    await renderChart()
    await waitFor(() => expect(screen.getByTestId('bump-span-caption')).toBeInTheDocument())
    expect(screen.getByTestId('bump-span-caption').textContent).toBe('2주 (7일)')
  })
})

describe('Bump 잠정점 — Top-N·클릭', () => {
  it('Top-N 기준일은 잠정점 날짜다 (끝난 주 4위 D 는 잠정점이 없어 Top 5 밖)', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(capturedOption).not.toBeNull())
    fireEvent.click(screen.getByText('Top 5'))
    await waitFor(() =>
      expect([...new Set(opt().series.map(s => s.name))].sort()).toEqual(['A', 'B', 'C']))
  })

  it('점선 구간을 클릭해도 섹터 이름으로 표 이동 콜백을 부른다', async () => {
    const onSectorClick = vi.fn()
    await renderChart({ onSectorClick })
    capturedEvents?.click({ seriesName: 'A', name: PROV })
    expect(onSectorClick).toHaveBeenCalledWith('A')
  })

  it('한 조각을 호버하면 같은 이름으로 highlight/downplay 를 보내 실선·점선을 함께 강조한다', async () => {
    await renderChart()
    const chart = { dispatchAction: vi.fn(), isDisposed: () => false }
    ;(capturedEvents?.mouseover as (p: unknown, c: unknown) => void)(
      { componentType: 'series', seriesName: 'A' }, chart)
    ;(capturedEvents?.mouseout as (p: unknown, c: unknown) => void)(
      { componentType: 'series', seriesName: 'A' }, chart)
    await Promise.resolve()
    expect(chart.dispatchAction.mock.calls).toEqual([
      [{ type: 'highlight', seriesName: 'A' }],
      [{ type: 'downplay', seriesName: 'A' }],
    ])
  })

  it('잠정점이 없으면 호버 연동을 보내지 않는다 (내장 강조 그대로)', async () => {
    const fx = makeFixture()
    fx.provisional_date = null
    fx.sectors = fx.sectors.map(s => ({ ...s, history: s.history.filter(w => !w.provisional) }))
    mockFetchSectorHistory.mockResolvedValue(fx)
    await renderChart()
    const chart = { dispatchAction: vi.fn(), isDisposed: () => false }
    ;(capturedEvents?.mouseover as (p: unknown, c: unknown) => void)(
      { componentType: 'series', seriesName: 'A' }, chart)
    await Promise.resolve()
    expect(chart.dispatchAction).not.toHaveBeenCalled()
  })
})
