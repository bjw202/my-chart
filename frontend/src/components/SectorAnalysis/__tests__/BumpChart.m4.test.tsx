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
    expect(mockFetchSectorHistory).toHaveBeenLastCalledWith(12)
  })

  it('26주 선택 시 weeks=26 을 포함한 요청이 발행된다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())
    mockFetchSectorHistory.mockClear()
    fireEvent.click(screen.getByText('26주'))
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalledWith(26))
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
