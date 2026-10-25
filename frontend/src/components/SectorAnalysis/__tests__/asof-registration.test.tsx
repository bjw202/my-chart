// RRG·Bump 가 응답 as_of_date 를 기준일 레지스트리(AC-SUX-037 / SN-3)에 등록하고,
// 언마운트되면 빠진다. 자체 조회를 소유한 화면도 합치 경고의 대상이 된다.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactElement } from 'react'

const mockFetchRRG = vi.fn()
vi.mock('../../../api/rrg', () => ({ fetchRRGData: (...a: unknown[]) => mockFetchRRG(...(a as [])) }))
const mockFetchHistory = vi.fn()
vi.mock('../../../api/history', () => ({ fetchSectorHistory: (...a: unknown[]) => mockFetchHistory(...(a as [])) }))
vi.mock('echarts-for-react', () => ({ default: () => null }))

import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider, useAsOfCoherence, useAsOfRegistration } from '../../../contexts/DataLoadContext'
import { RRGChart } from '../RRGChart'
import { BumpChart } from '../BumpChart'

// 기준 패널 — 고정 날짜를 등록해 두고, 대상 패널이 다른 날짜를 등록하면 충돌이 드러난다.
function Anchor(): null {
  useAsOfRegistration('기준', '2026-10-22')
  return null
}

function Coherence(): ReactElement {
  const { conflict } = useAsOfCoherence()
  return (
    <div data-testid="coherence">
      {conflict ? `${conflict.panels.join(',')}|${conflict.dates.join(',')}` : 'none'}
    </div>
  )
}

function tree(chart: ReactElement | null): ReactElement {
  return (
    <AnalysisParamsProvider><DataLoadProvider>
      <Anchor />
      {chart}
      <Coherence />
    </DataLoadProvider></AnalysisParamsProvider>
  )
}

beforeEach(() => {
  mockFetchRRG.mockReset()
  mockFetchHistory.mockReset()
})

describe('(d) RRG·Bump 기준일 레지스트리 등록', () => {
  it('RRG 가 응답 as_of_date 를 "RRG" 패널로 등록하고, 언마운트 시 빠진다', async () => {
    mockFetchRRG.mockResolvedValue({ date: '2026-10-23', as_of_date: '2026-10-23', sectors: [], kospi: [] })
    const { rerender } = render(tree(<RRGChart />))
    await waitFor(() =>
      expect(screen.getByTestId('coherence').textContent).toBe('기준,RRG|2026-10-22,2026-10-23'),
    )
    rerender(tree(null))
    await waitFor(() => expect(screen.getByTestId('coherence').textContent).toBe('none'))
  })

  it('Bump 가 응답 as_of_date 를 "Bump" 패널로 등록하고, 언마운트 시 빠진다', async () => {
    mockFetchHistory.mockResolvedValue({ weeks: 12, span_days: 77, sectors: [], as_of_date: '2026-10-23' })
    const { rerender } = render(tree(<BumpChart period="1m" market="all" />))
    await waitFor(() =>
      expect(screen.getByTestId('coherence').textContent).toBe('기준,Bump|2026-10-22,2026-10-23'),
    )
    rerender(tree(null))
    await waitFor(() => expect(screen.getByTestId('coherence').textContent).toBe('none'))
  })

  it('as_of_date 가 없는 응답은 등록하지 않는다 (충돌을 만들지 않는다)', async () => {
    mockFetchRRG.mockResolvedValue({ date: '2026-10-23', sectors: [], kospi: [] })
    render(tree(<RRGChart />))
    await waitFor(() => expect(mockFetchRRG).toHaveBeenCalled())
    await new Promise(r => setTimeout(r, 30))
    expect(screen.getByTestId('coherence').textContent).toBe('none')
  })

  it('Provider 밖에서는 등록 훅이 아무 일도 하지 않는다 (차트 단독 렌더 허용)', async () => {
    mockFetchHistory.mockResolvedValue({ weeks: 12, span_days: 77, sectors: [], as_of_date: '2026-10-23' })
    expect(() => render(<BumpChart />)).not.toThrow()
    await waitFor(() => expect(mockFetchHistory).toHaveBeenCalled())
  })
})
