// AC-SUX-028 (REQ-SUX-026) + AC-SUX-019 Bump 반대 방향 단언 — BumpChart M4 (SPEC-SECTOR-UX-001 M4).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { SectorHistoryResponse } from '../../../api/history'

// ReactECharts mock — option 을 캡처해 series 이름을 data-attr 로 노출 (AC-SUX-019 series 단언용).
let capturedOption: { series?: Array<{ name?: string }> } | null = null
vi.mock('echarts-for-react', () => ({
  default: (props: { option: unknown }) => {
    capturedOption = props.option as { series?: Array<{ name?: string }> }
    const names = (capturedOption?.series ?? []).map((s) => s.name).filter(Boolean)
    return (
      <div data-testid="bump-echarts">
        {names.map((n) => (
          <span key={n} data-series-name={n}>{n}</span>
        ))}
      </div>
    )
  },
}))

// fetchSectorHistory mock — 호출 인자(weeks) 기록 + 픽스처 반환.
const mockFetchSectorHistory = vi.fn()
vi.mock('../../../api/history', () => ({
  fetchSectorHistory: (...args: unknown[]) => mockFetchSectorHistory(...args),
}))

import { BumpChart } from '../BumpChart'

// 픽스처: 디스플레이·스마트폰 은 Table data[] 에서 AG-5 제외 대상이지만 Bump 에는 전 섹터가 포함.
function makeHistoryFixture(): SectorHistoryResponse {
  return {
    weeks: 12,
    span_days: 84,
    sectors: [
      { name: '반도체', history: [{ date: '2026-08-04', rank: 1, composite_score: 80, sector_return_1w: 1, sector_excess_return_1w: 0.5, rs_avg: 70 }] },
      { name: '디스플레이', history: [{ date: '2026-08-04', rank: 5, composite_score: 50, sector_return_1w: 0, sector_excess_return_1w: 0, rs_avg: 40 }] },
      { name: '스마트폰', history: [{ date: '2026-08-04', rank: 6, composite_score: 45, sector_return_1w: -1, sector_excess_return_1w: -0.5, rs_avg: 35 }] },
      { name: '은행', history: [{ date: '2026-08-04', rank: 2, composite_score: 70, sector_return_1w: 0.5, sector_excess_return_1w: 0.2, rs_avg: 60 }] },
    ],
  }
}

beforeEach(() => {
  capturedOption = null
  mockFetchSectorHistory.mockReset()
  mockFetchSectorHistory.mockResolvedValue(makeHistoryFixture())
})

// AC-SUX-028 (REQ-SUX-026): Bump 구간 컨트롤
describe('AC-SUX-028 — weeks 컨트롤 + span_days 표기', () => {
  it('8주/12주/26주 토글이 렌더되고 기본 선택이 12주다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())
    const filter = screen.getByTestId('bump-weeks-filter')
    const buttons = filter.querySelectorAll('button')
    expect(buttons.length).toBe(3)
    expect(Array.from(buttons).map((b) => b.textContent)).toEqual(['8주', '12주', '26주'])
    // 기본 12주 활성
    const activeBtn = filter.querySelector('button.active') as HTMLButtonElement
    expect(activeBtn?.textContent).toBe('12주')
  })

  it('최초 조회가 weeks=12 로 발행된다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())
    expect(mockFetchSectorHistory).toHaveBeenLastCalledWith(12, expect.any(Object))
  })

  it('26주 선택 시 weeks=26 을 포함한 요청이 발행된다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())
    mockFetchSectorHistory.mockClear()
    fireEvent.click(screen.getByText('26주'))
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalledWith(26, expect.any(Object)))
  })

  it('축 하단에 응답의 weeks 와 span_days 가 병기된다 (12주 (84일)) — 프론트 계산 금지', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(screen.getByTestId('bump-span-caption')).toBeInTheDocument())
    expect(screen.getByTestId('bump-span-caption').textContent).toBe('12주 (84일)')
  })

  it('span_days 가 없으면 주수만 표기한다', async () => {
    mockFetchSectorHistory.mockResolvedValue({ weeks: 8, sectors: makeHistoryFixture().sectors })
    render(<BumpChart />)
    await waitFor(() => expect(screen.getByTestId('bump-span-caption')).toBeInTheDocument())
    expect(screen.getByTestId('bump-span-caption').textContent).toBe('8주')
  })
})

// AC-SUX-019 (REQ-SUX-017) Bump 반대 방향 단언 — AG-5 미적용 계약 실증 (GREEN)
// Bump 에는 순위 대상 제외 영역이 렌더되지 않으며, excluded 섹터의 선이 정상 존재한다.
// 대조 변형 mut_bump_applies_ag5 되돌림 RED 는 progress.md §E.2 에 verbatim 기록(Lesson #9).
describe('AC-SUX-019 — Bump 반대 방향 단언 (AG-5 미적용 계약)', () => {
  it('Bump 에는 순위 대상 제외 영역이 렌더되지 않는다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(screen.getByTestId('bump-echarts')).toBeInTheDocument())
    expect(screen.queryByText(/순위 대상 제외/)).not.toBeInTheDocument()
    expect(screen.queryByTestId('excluded-sectors')).not.toBeInTheDocument()
  })

  it('excluded 로 분류된 섹터(디스플레이·스마트폰)의 선이 Bump 에 정상적으로 존재한다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(screen.getByTestId('bump-echarts')).toBeInTheDocument())
    // AG-5 미적용 — 전 섹터(디스플레이·스마트폰 포함)가 Bump series 에 존재
    expect(screen.getByText('디스플레이')).toBeInTheDocument()
    expect(screen.getByText('스마트폰')).toBeInTheDocument()
    expect(screen.getByText('반도체')).toBeInTheDocument()
    expect(screen.getByText('은행')).toBeInTheDocument()
  })
})

// 표와 같은 기준(2026-10-21 사용자 결정): Bump 는 헤더의 기간·시장 토글을 그대로 조회에 싣고,
// 툴팁은 순위 기준인 그 기간의 초과수익률을 보여준다(종합점수 아님).
describe('표와 같은 기준 — 기간·시장 전달', () => {
  it('period·market 을 조회 요청에 싣는다', async () => {
    render(<BumpChart period="3m" market="kospi" />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())
    expect(mockFetchSectorHistory).toHaveBeenLastCalledWith(12, { period: '3m', market: 'kospi' })
  })

  it('기간이 바뀌면 다시 조회한다', async () => {
    const { rerender } = render(<BumpChart period="1m" market="all" />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())
    mockFetchSectorHistory.mockClear()
    rerender(<BumpChart period="1w" market="all" />)
    await waitFor(() =>
      expect(mockFetchSectorHistory).toHaveBeenCalledWith(12, { period: '1w', market: 'all' }))
  })

  it('툴팁은 순위 기준 기간의 초과수익률을 보여준다', async () => {
    const fx = makeHistoryFixture()
    fx.sectors[0].history[0].rank_basis_excess_return = 12.34
    mockFetchSectorHistory.mockResolvedValue({ ...fx, period: '3m' })
    render(<BumpChart period="3m" market="all" />)
    await waitFor(() => expect(screen.getByTestId('bump-echarts')).toBeInTheDocument())
    const opt = capturedOption as unknown as { tooltip: { formatter: (p: unknown) => string } }
    const html = opt.tooltip.formatter({ seriesName: '반도체', name: '2026-08-04', value: 1 })
    expect(html).toContain('3M 초과수익률: +12.3%')
    expect(html).not.toContain('종합점수')
  })

  it('순위 기준 캡션을 표시한다', async () => {
    render(<BumpChart period="1w" market="kosdaq" />)
    await waitFor(() => expect(screen.getByTestId('bump-basis-caption')).toBeInTheDocument())
    // 감사 F2: 표는 진행 중인 주까지, Bump 마지막 점은 끝난 주까지라 '동일'이 아니라 '같은 기준'이다.
    expect(screen.getByTestId('bump-basis-caption').textContent).toBe(
      '순위 기준: 1W 초과수익률 · KOSDAQ (표와 같은 기준 · 5종목 미만 섹터 포함 · 마지막 점 2026-08-04, 끝난 주)')
  })

  // 감사 F1: 기간을 빠르게 바꾸면 늦게 도착한 이전 요청의 응답이 새 응답을 덮어쓰면 안 된다.
  it('늦게 도착한 이전 요청의 응답은 버린다', async () => {
    const resolvers: Array<(v: SectorHistoryResponse) => void> = []
    mockFetchSectorHistory.mockImplementation(
      () => new Promise<SectorHistoryResponse>(res => { resolvers.push(res) }))
    const one = (name: string): SectorHistoryResponse => ({
      weeks: 12,
      sectors: [{ name, history: [{ date: '2026-08-04', rank: 1, composite_score: 50, sector_return_1w: 0, sector_excess_return_1w: 0, rs_avg: 50 }] }],
    })
    const { rerender } = render(<BumpChart period="1w" market="all" />)
    await waitFor(() => expect(resolvers.length).toBe(1))
    rerender(<BumpChart period="3m" market="all" />)
    await waitFor(() => expect(resolvers.length).toBe(2))
    resolvers[1](one('새응답3M'))
    await waitFor(() => expect(screen.getByText('새응답3M')).toBeInTheDocument())
    resolvers[0](one('옛응답1W'))
    await new Promise(r => setTimeout(r, 20))
    expect(screen.queryByText('옛응답1W')).not.toBeInTheDocument()
    expect(screen.getByText('새응답3M')).toBeInTheDocument()
  })
})
