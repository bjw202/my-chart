// Bump Top-N 필터 — 기준일(최신 날짜) 순위 기준 회귀 테스트.
// 종전 구현은 `history.some(w => w.rank <= n)` 이라 "기간 중 한 번이라도 Top-N 진입"이면
// 통과시켰고, 그 결과 Top 5 를 골라도 20개 이상이 그려졌다. 아래 '과거상위' 픽스처가
// 그 되돌림을 RED 로 잡는다.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { SectorHistoryResponse } from '../../../api/history'

let capturedOption: { series?: Array<{ name?: string }> } | null = null
vi.mock('echarts-for-react', () => ({
  default: (props: { option: unknown }) => {
    capturedOption = props.option as { series?: Array<{ name?: string }> }
    return <div data-testid="bump-echarts" />
  },
}))

const mockFetchSectorHistory = vi.fn()
vi.mock('../../../api/history', () => ({
  fetchSectorHistory: (...args: unknown[]) => mockFetchSectorHistory(...args),
}))

import { BumpChart } from '../BumpChart'

const PREV = '2026-08-07'
const LATEST = '2026-08-14'

function week(date: string, rank: number) {
  return { date, rank, composite_score: 100 - rank, sector_return_1w: 0, sector_excess_return_1w: 0, rs_avg: 50 }
}

// 기준일 순위 1~5 는 A/B/D/E/F, 과거상위(C) 는 이전 주에 2위였다가 기준일 9위로 밀렸다.
function makeFixture(): SectorHistoryResponse {
  return {
    weeks: 12,
    span_days: 84,
    sectors: [
      { name: 'A', history: [week(PREV, 1), week(LATEST, 1)] },
      { name: 'B', history: [week(PREV, 10), week(LATEST, 2)] },
      { name: '과거상위', history: [week(PREV, 2), week(LATEST, 9)] },
      { name: 'D', history: [week(PREV, 20), week(LATEST, 3)] },
      { name: 'E', history: [week(PREV, 6), week(LATEST, 4)] },
      { name: 'F', history: [week(PREV, 7), week(LATEST, 5)] },
      { name: '하위', history: [week(PREV, 3), week(LATEST, 20)] },
    ],
  }
}

function seriesNames(): string[] {
  return (capturedOption?.series ?? []).map((s) => s.name).filter((n): n is string => Boolean(n))
}

beforeEach(() => {
  capturedOption = null
  mockFetchSectorHistory.mockReset()
  mockFetchSectorHistory.mockResolvedValue(makeFixture())
})

describe('Bump Top-N 필터 — 기준일 순위 기준', () => {
  it('기본 전체 선택에서는 모든 섹터가 그려진다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(seriesNames().length).toBe(7))
  })

  it('Top 5 선택 시 기준일 1~5위 섹터 정확히 5개만 남는다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())

    fireEvent.click(screen.getByText('Top 5'))

    await waitFor(() => expect(seriesNames().length).toBe(5))
    expect(seriesNames().sort()).toEqual(['A', 'B', 'D', 'E', 'F'])
  })

  it('기준일에 Top-N 밖인 섹터는 과거에 상위였어도 제외된다 (되돌림 방지)', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())

    fireEvent.click(screen.getByText('Top 5'))

    // '과거상위'(직전 주 2위)와 '하위'(직전 주 3위)는 기준일 순위가 5위 밖이라 빠진다.
    await waitFor(() => expect(seriesNames()).not.toContain('과거상위'))
    expect(seriesNames()).not.toContain('하위')
  })

  it('Top 10 선택 시 기준일 1~10위 섹터가 포함된다', async () => {
    render(<BumpChart />)
    await waitFor(() => expect(mockFetchSectorHistory).toHaveBeenCalled())

    fireEvent.click(screen.getByText('Top 10'))

    await waitFor(() => expect(seriesNames().length).toBe(6))
    expect(seriesNames()).toContain('과거상위')
    expect(seriesNames()).not.toContain('하위')
  })
})
