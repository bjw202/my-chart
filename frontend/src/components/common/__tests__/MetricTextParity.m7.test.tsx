// M7 / D2 — 표 셀 텍스트 ↔ 차트 툴팁 텍스트 문자열 동등 (AC-SUX-052 debt 해소분)
//
// 의도된 변화: M6 시점에는 결측 표기가 화면마다 갈렸다 — 표는 '–'(MISSING_TEXT),
// Bump 툴팁은 ASCII '-', 섹터버블·RRG 툴팁은 Number(null).toFixed() 로 'NaN'.
// D2 결정(텍스트 헬퍼 추출)에 따라 네 소비자가 모두 metricText 를 호출한다.
//
// 범위 밖(명시적 N/A): 스타일 병행. ECharts tooltip 은 formatter 가 만드는 문자열이며
// 스타일시트가 닿는 DOM 이 아니다 — className 병행은 물리적으로 불가능하다.
// 따라서 본 파일이 실증하는 것은 '텍스트 동등'이며, 스타일 동등은 주장하지 않는다.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup, waitFor } from '@testing-library/react'
import { MetricCell, metricText, MISSING_TEXT, INSUFFICIENT_TEXT } from '../MetricCell'
import type { MetricValue } from '../MetricCell'
import type { SectorBubbleItem } from '../../../types/bubble'
import type { RRGResponse } from '../../../types/rrg'
import type { SectorHistoryResponse } from '../../../api/history'

let capturedOption: Record<string, unknown> = {}
vi.mock('echarts-for-react', () => ({
  default: (props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  },
}))

const mockFetchRRG = vi.fn()
vi.mock('../../../api/rrg', () => ({ fetchRRGData: (...a: unknown[]) => mockFetchRRG(...a) }))
const mockFetchHistory = vi.fn()
vi.mock('../../../api/history', () => ({ fetchSectorHistory: (...a: unknown[]) => mockFetchHistory(...a) }))
vi.mock('../../../contexts/AnalysisParamsContext', () => ({
  useAnalysisParams: () => ({ market: 'all', period: '1m', setMarket: () => {}, setPeriod: () => {} }),
  AnalysisParamsProvider: ({ children }: { children: React.ReactNode }) => children,
}))

import { SectorBubbleChart } from '../../SectorAnalysis/SectorBubbleChart'
import { RRGChart } from '../../SectorAnalysis/RRGChart'
import { BumpChart } from '../../SectorAnalysis/BumpChart'

// 툴팁 formatter 를 option 에서 꺼내 호출한다.
type Formatter = (p: unknown) => string
function tooltipFormatter(): Formatter {
  const t = capturedOption.tooltip as { formatter: Formatter }
  return t.formatter
}

// 표 셀이 실제로 렌더한 텍스트.
function cellText(value: MetricValue, format?: (n: number) => string): string {
  const { container } = render(<MetricCell value={value} format={format} />)
  const text = container.querySelector('[data-testid="metric-cell"]')!.textContent!
  cleanup()
  return text
}

beforeEach(() => {
  capturedOption = {}
  mockFetchRRG.mockReset()
  mockFetchHistory.mockReset()
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

// 공용 픽스처 — 같은 지표 봉투를 표와 차트에 똑같이 흘린다.
const FIXTURES: Array<{ label: string; value: MetricValue; expect: string }> = [
  { label: 'null(결측)', value: null, expect: MISSING_TEXT },
  { label: 'undefined(결측)', value: undefined, expect: MISSING_TEXT },
  { label: 'NaN(결측)', value: NaN, expect: MISSING_TEXT },
  { label: '표본 부족', value: { value: null, reason: 'insufficient' }, expect: INSUFFICIENT_TEXT },
  { label: '저신뢰', value: { value: 42, low_confidence: true }, expect: '42 ⚠' },
  { label: '경고', value: { value: 42, warnings: ['정합성 불일치'] }, expect: '42 ❗' },
  { label: '실제 0', value: 0, expect: '0' },
]

describe('D2 — 표 셀과 metricText 가 같은 문자열을 낸다 (단일 출처)', () => {
  it.each(FIXTURES)('$label → $expect', ({ value, expect: want }) => {
    expect(cellText(value)).toBe(want)
    expect(metricText(value)).toBe(want)
    // 같은 봉투 → 표 셀과 헬퍼가 문자열 동등
    expect(cellText(value)).toBe(metricText(value))
  })

  it('format 을 주어도 표 셀과 헬퍼가 동등하다 (소수 자리·부호 포함)', () => {
    const fmt = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
    for (const v of [0, 4.5, -3.25, null, NaN] as MetricValue[]) {
      expect(cellText(v, fmt)).toBe(metricText(v, fmt))
    }
  })
})

describe('D2 — 섹터 버블 툴팁이 표 셀과 같은 결측 문자열을 쓴다', () => {
  function renderWithMissing() {
    const sectors: SectorBubbleItem[] = [
      { name: '반도체', excess_return: 2.5, rs_avg: 60, trading_value: 5e11, period_return: 4 },
      // 결측 지표 — 백엔드가 null 을 준 섹터
      { name: '결측섹터', excess_return: null as unknown as number, rs_avg: null as unknown as number,
        trading_value: 1e11, period_return: null as unknown as number },
    ]
    render(<SectorBubbleChart sectors={sectors} onSectorClick={() => {}} period="1m" />)
  }

  it('결측 지표 3종이 전부 표 셀과 같은 –(MISSING_TEXT) 로 렌더된다 — NaN 누출 0건', () => {
    renderWithMissing()
    const series = capturedOption.series as Array<{ data?: Array<{ value: (string | number)[] }> }>
    const point = series.flatMap(s => s.data ?? []).find(p => p.value[4] === '결측섹터')!
    const html = tooltipFormatter()({ data: point })

    expect(html).toContain(`초과수익률: ${MISSING_TEXT}`)
    expect(html).toContain(`RS 평균: ${MISSING_TEXT}`)
    expect(html).toContain(`기간수익률: ${MISSING_TEXT}`)
    // 표 셀이 같은 봉투에 대해 내는 문자열과 동등
    expect(cellText(null)).toBe(MISSING_TEXT)
    expect(html).not.toContain('NaN')
  })

  it('값이 있으면 종전 포맷을 그대로 유지한다 (결측 경로만 바뀌었다)', () => {
    renderWithMissing()
    const series = capturedOption.series as Array<{ data?: Array<{ value: (string | number)[] }> }>
    const point = series.flatMap(s => s.data ?? []).find(p => p.value[4] === '반도체')!
    const html = tooltipFormatter()({ data: point })
    expect(html).toContain('초과수익률: 2.50%')
    expect(html).toContain('RS 평균: 60.0')
    expect(html).toContain('기간수익률: +4.00%')
  })
})

describe('D2 — RRG 툴팁이 표 셀과 같은 결측 문자열을 쓴다', () => {
  const rrgFixture: RRGResponse = {
    date: '2026-08-14',
    sectors: [
      { name: '반도체', rs_ratio: 108, rs_momentum: 112, quadrant: 'leading',
        trail: Array.from({ length: 10 }, (_, i) => ({ date: `2026-W${i + 1}`, rs_ratio: 100 + i, rs_momentum: 100 + i })) },
    ],
    kospi: Array.from({ length: 10 }, (_, i) => ({ date: `2026-W${i + 1}`, close: 2000 + i * 10 })),
  }

  it('결측 좌표는 – 로, 값이 있으면 종전 toFixed(2) 로 렌더된다', async () => {
    mockFetchRRG.mockResolvedValue(rrgFixture)
    render(<RRGChart />)
    await waitFor(() => expect(capturedOption.tooltip).toBeDefined())
    const f = tooltipFormatter()

    const ok = f({ seriesName: '반도체', data: { value: [108.123, 112.456] } })
    expect(ok).toContain('RS-Ratio: 108.12')
    expect(ok).toContain('RS-Momentum: 112.46')

    const missing = f({ seriesName: '반도체', data: { value: [null, undefined] } })
    expect(missing).toContain(`RS-Ratio: ${MISSING_TEXT}`)
    expect(missing).toContain(`RS-Momentum: ${MISSING_TEXT}`)
    expect(missing).not.toContain('NaN')
    expect(cellText(null)).toBe(MISSING_TEXT)
  })
})

describe('D2 — Bump 툴팁이 표 셀과 같은 결측 문자열을 쓴다 (ASCII - 이탈 제거)', () => {
  const historyFixture: SectorHistoryResponse = {
    weeks: 12,
    span_days: 84,
    sectors: [
      { name: '반도체', history: [{ date: '2026-08-04', rank: 1, composite_score: 80, sector_return_1w: 1, sector_excess_return_1w: 0.5, rs_avg: 70 }] },
    ],
  }

  it('해당 주 데이터가 없으면 종합점수가 – 다 — 표 셀과 동등하며 ASCII - 가 아니다', async () => {
    mockFetchHistory.mockResolvedValue(historyFixture)
    render(<BumpChart />)
    await waitFor(() => expect(capturedOption.tooltip).toBeDefined())
    const f = tooltipFormatter()

    const ok = f({ seriesName: '반도체', name: '2026-08-04', value: 1 })
    expect(ok).toContain('종합점수: 80.00')

    const missing = f({ seriesName: '반도체', name: '2026-07-28', value: 3 })
    expect(missing).toContain(`종합점수: ${MISSING_TEXT}`)
    expect(missing).toBe(missing.replace('종합점수: -', 'SENTINEL'))
    expect(cellText(null)).toBe(MISSING_TEXT)
  })
})
