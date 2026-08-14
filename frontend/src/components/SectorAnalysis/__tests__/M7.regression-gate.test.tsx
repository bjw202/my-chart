// AC-SUX-056 — M7 회귀 방지 게이트 (R1~R5).
//
// 의도된 변화 [docstring 의무 — acceptance.md §AC-SUX-056]:
// 아래 5건은 전부 **올바른 결과**이며 회귀가 아니다. 본 SPEC 이전의 동작이 결함이었다.
//   R1 기간 변경 시 로딩이 생긴다      — 이전엔 클라이언트 재정렬이라 즉시였다(서버 재조회 없음 = 값이 틀렸다)
//   R2 정렬 변경 시 고지 띠가 뜬다     — rank 열이 정렬과 무관해지는 사실을 숨기지 않는다
//   R3 버블 크기 분포가 바뀐다         — 선형 매핑에서 다수가 최소 밴드에 뭉치던 상태를 로그 매핑이 해소
//   R4 RRG 궤적이 짧아진다             — 전체 trail 이 아니라 8주 윈도우만 그린다
//   R5 KOSPI 필터 시 순위표 행이 줄고 하단 제외 영역이 생긴다
//                                      — **검증 범위 = Table · 섹터 Bubble · RRG 한정**. Bump 는 대상이 아니다
//                                        (O-U9 확정: AG-5 는 Bump 에 미적용. Bump 반대 방향 단언은
//                                         BumpChart.m4.test.tsx 의 AC-SUX-019 describe 가 담당한다).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import type { ReactElement } from 'react'
import { AnalysisParamsProvider, useAnalysisParams } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { fetchSectorBubble, fetchStockBubble } from '../../../api/bubble'
import { BubbleChart } from '../BubbleChart'
import { SectorBubbleChart } from '../SectorBubbleChart'
import { SectorRankingTable } from '../SectorRankingTable'
import { bubbleSymbolSize, PERIOD_SIZE_LADDER, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX } from '../bubbleRadius'
import type { SectorBubbleItem } from '../../../types/bubble'
import type { RRGResponse } from '../../../types/rrg'
import type { SectorRankItem } from '../../../types/market'

vi.mock('../../../api/bubble', () => ({
  fetchSectorBubble: vi.fn(),
  fetchStockBubble: vi.fn(),
}))
vi.mock('../../../contexts/TabContext', () => ({
  useNavIntent: () => ({ navigate: vi.fn(), intent: null }),
}))
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({ selectSector: vi.fn() }),
}))
vi.mock('../StockBubbleChart', () => ({
  StockBubbleChart: () => <div data-testid="stock-bubble">stock</div>,
}))

let capturedOption: Record<string, unknown> = {}
vi.mock('echarts-for-react', () => ({
  default: (props: { option: Record<string, unknown> }) => {
    capturedOption = props.option
    return null
  },
}))

const mockFetchRRG = vi.fn()
vi.mock('../../../api/rrg', () => ({ fetchRRGData: (...a: unknown[]) => mockFetchRRG(...a) }))

beforeEach(() => {
  capturedOption = {}
  vi.mocked(fetchSectorBubble).mockReset()
  vi.mocked(fetchStockBubble).mockReset()
  mockFetchRRG.mockReset()
})
afterEach(() => cleanup())

// ── 소스/테스트 전량 정적 스캔 (R1·R2 부재 확인용) ──────────────────────────
// ?raw + import.meta.glob — node:fs 미사용(브라우저 환경 테스트에서 동작, tsc NEW-0 유지).
const TEST_SOURCES = import.meta.glob(
  ['../__tests__/*.tsx', '../../StockExplorer/__tests__/*.tsx'],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>

// AC-SUX-022 의 정당한 단언(rank 정렬 상태에서 띠가 없어야 한다)은 명시 제외한다.
// 제외 사유: R2 가 막으려는 것은 '비-rank 정렬에서 띠 부재를 요구하는' 단언이며,
// rank 정렬 상태의 부재 단언은 고지 띠 계약 자체의 일부다.
const R2_ALLOWLIST = ['SectorAnalysis.m4.test.tsx']

// R1 은 acceptance.md 에 파일 단위 allowlist 조항이 없으므로 **라인 단위 마커**로 제외한다.
// 대상: 재조회 '완료 후' 인디케이터 소멸 단언 — R1 이 막으려는 '기간 변경 시점의 로딩 부재
// 요구'와 다른 경로다. 마커를 단언 바로 위 주석에 붙여 제외가 현장에서 보이게 한다
// (R2 가 규정한 "테스트 파일명 + 라인 주석으로 표시" 기준을 라인 단위로 적용).
const R1_LINE_MARKER = 'AC-SUX-056-R1-ALLOW'

function scanSources(re: RegExp, allowlist: string[] = [], lineMarker?: string): string[] {
  const hits: string[] = []
  for (const [path, src] of Object.entries(TEST_SOURCES)) {
    if (allowlist.some(a => path.endsWith(a))) continue
    const lines = src.split('\n')
    for (const [i, line] of lines.entries()) {
      if (!re.test(line)) continue
      // 직전 3행 안에 마커가 있으면 명시 제외.
      const near = lines.slice(Math.max(0, i - 3), i).join('\n')
      if (lineMarker && near.includes(lineMarker)) continue
      hits.push(`${path}:${i + 1}: ${line.trim()}`)
    }
  }
  return hits
}

// ── R1 — 기간을 바꾸면 로딩이 생긴다 ────────────────────────────────────────
const sectorEnv = (over: Record<string, unknown> = {}) => ({
  date: '2026-08-11', period: '1m', market: null,
  sectors: [{ name: '반도체' }, { name: '은행' }],
  as_of_date: '2026-08-11', as_of_is_partial_week: false, grid_version: 'g1',
  ...over,
})

function PeriodSwitch(): ReactElement {
  const { setPeriod } = useAnalysisParams()
  return <button onClick={() => setPeriod('3m')}>switch-3m</button>
}

describe('AC-SUX-056 R1 — 기간을 바꾸면 로딩이 생긴다 (의도된 변화)', () => {
  it('R1 긍정: period 1w→3m 변경 시 기준일 배지 옆에 로딩 인디케이터가 렌더된다', async () => {
    let resolveSecond: ((v: unknown) => void) | null = null
    vi.mocked(fetchSectorBubble)
      .mockResolvedValueOnce(sectorEnv() as never)
      .mockImplementationOnce(() => new Promise(res => { resolveSecond = res as (v: unknown) => void }))
    vi.mocked(fetchStockBubble).mockResolvedValue({ stocks: [] } as never)

    render(
      <AnalysisParamsProvider><DataLoadProvider>
        <PeriodSwitch />
        <BubbleChart initialSector={null} />
      </DataLoadProvider></AnalysisParamsProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('as-of-badge')).toBeInTheDocument())
    expect(screen.queryByTestId('refetch-spinner')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('switch-3m'))
    // 재조회가 진행되는 동안 로딩 인디케이터가 뜬다 — 이전 판에서는 즉시 재정렬이라 없었다.
    const spinner = await screen.findByTestId('refetch-spinner')
    expect(spinner).toBeInTheDocument()
    // 배지와 같은 상태 바 안에 있다 (기준일 배지 옆).
    expect(spinner.closest('[data-testid="data-status-bar"]')).not.toBeNull()

    resolveSecond!(sectorEnv({ period: '3m' }))
    await waitFor(() => expect(screen.queryByTestId('refetch-spinner')).not.toBeInTheDocument())
  })

  it('R1 부재 확인: 기간 변경 경로에서 로딩 부재를 요구하는 단언이 없다 (0행)', () => {
    const RE = /queryBy(TestId|Text)\(.*(spinner|loading|로딩).*\)\s*\)\.(toBeNull|not\.toBeInTheDocument)/
    // 원문 grep(제외 없음)의 실측 — 명시 제외 대상이 정확히 1건임을 고정한다.
    // 이 수가 늘면 새로운 부재 단언이 생긴 것이므로 아래 0행 단언 이전에 여기서 잡힌다.
    expect(scanSources(RE)).toHaveLength(1)
    // 명시 제외(완료 후 소멸 단언) 적용 후 0행.
    expect(scanSources(RE, [], R1_LINE_MARKER)).toEqual([])
  })
})

// ── R2 — 정렬을 바꾸면 안내 띠가 뜬다 ───────────────────────────────────────
// R2 긍정 단언(비-rank 정렬 → sort-notice 렌더)은 AC-SUX-022 와 동일 대상이며
// SectorAnalysis.m4.test.tsx 가 이미 실증한다. 여기서는 부재 확인(2단째)을 담당한다.
describe('AC-SUX-056 R2 — 정렬을 바꾸면 안내 띠가 뜬다 (의도된 변화)', () => {
  it('R2 부재 확인: 고지 띠 부재를 요구하는 단언이 allowlist 외에 없다 (0행)', () => {
    const hits = scanSources(
      /queryBy(TestId|Text)\(.*(sort-notice|정렬 고지|순위순으로).*\)\s*\)\.(toBeNull|not\.toBeInTheDocument)/,
      R2_ALLOWLIST,
    )
    expect(hits).toEqual([])
  })

  it('R2 긍정 대상이 실재한다 — AC-SUX-022 단언이 allowlist 파일에 살아 있다', () => {
    const src = Object.entries(TEST_SOURCES).find(([p]) => p.endsWith('SectorAnalysis.m4.test.tsx'))?.[1]
    expect(src).toBeDefined()
    expect(src).toContain("getByTestId('sort-notice')")
  })
})

// ── R3 — 버블 크기 분포가 바뀐다 ────────────────────────────────────────────
function stddev(xs: number[]): number {
  const m = xs.reduce((a, b) => a + b, 0) / xs.length
  return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length)
}

describe('AC-SUX-056 R3 — 버블 크기 분포가 바뀐다 (의도된 변화)', () => {
  // 실제 거래대금 분포를 모사: 소수 대형주가 상위를 독식하고 다수가 하위에 몰린다.
  // 선형 매핑에서는 하위 다수가 최소 반지름 근처 좁은 밴드에 뭉친다.
  const values = [
    1.2e10, 2.0e10, 3.1e10, 4.5e10, 6.0e10, 8.2e10, 1.1e11, 1.5e11,
    2.2e11, 3.4e11, 5.0e11, 8.0e11, 1.4e12, 2.6e12, 8.2e12,
  ]
  const { vMin, vMax } = PERIOD_SIZE_LADDER['1m']

  // 대조군은 구현과 **단 하나만** 다르다: 값→u 매핑이 로그가 아니라 선형이다.
  // 면적 비례(sqrt) 부분은 동일하게 유지한다 — 두 군데가 동시에 다르면
  // 구현을 선형화해도 차이가 남아 항진명제가 된다(실제로 그렇게 작성했다가 잡았다).
  const linearU = (v: number) => {
    const clamped = Math.max(vMin, Math.min(vMax, v))
    return vMax === vMin ? 0.5 : (clamped - vMin) / (vMax - vMin)
  }
  const areaFromU = (u: number) =>
    2 * Math.sqrt(SECTOR_BUBBLE_R_MIN ** 2 + u * (SECTOR_BUBBLE_R_MAX ** 2 - SECTOR_BUBBLE_R_MIN ** 2))

  const logRadii = values.map(v =>
    bubbleSymbolSize(v, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX))
  const linearRadii = values.map(v => areaFromU(linearU(v)))

  it('로그 매핑의 크기 표준편차가 선형 매핑보다 크다 (뭉침 해소)', () => {
    expect(stddev(logRadii)).toBeGreaterThan(stddev(linearRadii))
  })

  it('선형에서는 다수가 최소 밴드(하위 2px)에 뭉치고, 로그에서는 뭉치지 않는다', () => {
    const band = (rs: number[]) => rs.filter(r => r - Math.min(...rs) <= 2).length
    expect(band(linearRadii)).toBeGreaterThan(band(logRadii))
  })
})

// ── R4 — RRG 궤적이 짧아진다 ────────────────────────────────────────────────
describe('AC-SUX-056 R4 — RRG 궤적이 짧아진다 (의도된 변화)', () => {
  const FULL_TRAIL = 20
  const rrgFixture: RRGResponse = {
    date: '2026-08-14',
    sectors: [
      { name: '반도체', rs_ratio: 108, rs_momentum: 112, quadrant: 'leading',
        trail: Array.from({ length: FULL_TRAIL }, (_, i) => ({ date: `2026-W${i + 1}`, rs_ratio: 100 + i, rs_momentum: 100 + i })) },
    ],
    kospi: Array.from({ length: FULL_TRAIL }, (_, i) => ({ date: `2026-W${i + 1}`, close: 2000 + i })),
  }

  it('그려진 궤적 점 수 < 응답 trail 전체 길이 (8주 윈도우만 그린다)', async () => {
    mockFetchRRG.mockResolvedValue(rrgFixture)
    const { RRGChart } = await import('../RRGChart')
    render(<AnalysisParamsProvider><RRGChart /></AnalysisParamsProvider>)
    await waitFor(() => expect(capturedOption.series).toBeDefined())

    const series = capturedOption.series as Array<{ name?: string; data?: unknown[] }>
    const semi = series.find(s => s.name === '반도체')!
    const drawn = semi.data!.length
    expect(drawn).toBeLessThan(FULL_TRAIL)
    // 뭉뚱그린 "짧다"가 아니라 8주 윈도우라는 계약을 고정한다.
    expect(drawn).toBe(8)
  })
})

// ── R5 — KOSPI 필터 시 행이 줄고 제외 영역이 생긴다 (Table · 섹터Bubble · RRG 한정) ──
const row = (name: string, rank: number): SectorRankItem => ({
  name, stock_count: 20,
  returns: { w1: 1, m1: 2, m3: 3 }, excess_returns: { w1: 0.5, m1: 1, m3: 2 },
  rs_avg: 60, rs_top_pct: 20, nh_pct: 10, stage2_pct: 30,
  composite_score: 70, rank, rank_change: 0,
})

describe('AC-SUX-056 R5 — KOSPI 필터 시 행 감소 + 제외 영역 (Table)', () => {
  const ALL = [row('반도체', 1), row('은행', 2), row('증권', 3)]
  const KOSPI = [row('반도체', 1), row('은행', 2)]
  const EX_ALL = [{ sector: '디스플레이', reason: 'insufficient_members', count: 4 }]
  const EX_KOSPI = [
    { sector: '디스플레이', reason: 'insufficient_members', count: 4 },
    { sector: '증권', reason: 'insufficient_members', count: 3 },
  ]

  const rowsOf = (c: HTMLElement) => c.querySelectorAll('tbody tr').length

  it('행 수가 줄고(3→2) 하단 제외 영역이 커진다(1→2)', () => {
    const a = render(
      <SectorRankingTable sectors={ALL} excluded={EX_ALL} baselineDate="2026-08-01"
        onSectorClick={() => {}} selectedSector={null}
        sortField="rank" sortDirection="asc" onSort={() => {}} />,
    )
    const beforeRows = rowsOf(a.container)
    expect(a.container.querySelector('[data-testid="excluded-sectors"]')!.textContent).toContain('순위 대상 제외 (1)')
    cleanup()

    const b = render(
      <SectorRankingTable sectors={KOSPI} excluded={EX_KOSPI} baselineDate="2026-08-01"
        onSectorClick={() => {}} selectedSector={null}
        sortField="rank" sortDirection="asc" onSort={() => {}} />,
    )
    expect(rowsOf(b.container)).toBeLessThan(beforeRows)
    const ex = b.container.querySelector('[data-testid="excluded-sectors"]')!
    expect(ex.textContent).toContain('순위 대상 제외 (2)')
    // 제외 사유와 종목 수가 텍스트로 보인다 (hover-only 금지).
    expect(ex.textContent).toContain('증권')
  })
})

describe('AC-SUX-056 R5 — 제외 섹터가 섹터 Bubble 에 나타나지 않는다', () => {
  it('excluded 된 섹터는 버블 데이터 포인트로 렌더되지 않는다', () => {
    const kospiSectors: SectorBubbleItem[] = [
      { name: '반도체', excess_return: 2.5, rs_avg: 60, trading_value: 5e11, period_return: 4 },
      { name: '은행', excess_return: -1, rs_avg: 45, trading_value: 8e10, period_return: -2 },
    ]
    render(<SectorBubbleChart sectors={kospiSectors} onSectorClick={() => {}} period="1m" />)
    const series = capturedOption.series as Array<{ data?: Array<{ value: (string | number)[] }> }>
    const names = series.flatMap(s => s.data ?? []).map(p => p.value[4])
    expect(names).toEqual(['반도체', '은행'])
    expect(names).not.toContain('증권')
  })
})

describe('AC-SUX-056 R5 — 제외 섹터가 RRG 에 나타나지 않는다', () => {
  it('응답 sectors[] 에 없는 섹터의 시리즈가 생기지 않는다', async () => {
    mockFetchRRG.mockResolvedValue({
      date: '2026-08-14',
      sectors: [
        { name: '반도체', rs_ratio: 108, rs_momentum: 112, quadrant: 'leading',
          trail: Array.from({ length: 10 }, (_, i) => ({ date: `2026-W${i + 1}`, rs_ratio: 100 + i, rs_momentum: 100 + i })) },
      ],
      kospi: Array.from({ length: 10 }, (_, i) => ({ date: `2026-W${i + 1}`, close: 2000 + i })),
    } as RRGResponse)
    const { RRGChart } = await import('../RRGChart')
    render(<AnalysisParamsProvider><RRGChart /></AnalysisParamsProvider>)
    await waitFor(() => expect(capturedOption.series).toBeDefined())
    const names = (capturedOption.series as Array<{ name?: string }>)
      .map(s => s.name).filter(n => n && n !== '__bg__')
    expect(names).toEqual(['반도체'])
    expect(names).not.toContain('증권')
  })
})
