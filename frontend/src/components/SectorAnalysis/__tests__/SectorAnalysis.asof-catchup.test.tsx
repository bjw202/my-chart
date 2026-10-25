// 섹터 표 기준일 따라잡기 — 다른 패널이 더 새로운 as_of_date 를 등록하면 표가 1회 재조회한다.
// 배경(2026-10-25 관측): DB 가 2026-10-23 으로 갱신된 뒤 열어 둔 탭에서 Table 만 2026-10-22 에
// 머물렀다. MarketContext 는 마운트·기간·시장 변경 시에만 조회하고, 표는 기준일 레지스트리
// (AC-SUX-037 / SN-3)에 등록하지 않아 합치 경고도 뜨지 않았다.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import type { ReactElement } from 'react'

const mockFetchSectorRanking = vi.fn()
const mockFetchMarketOverview = vi.fn()
vi.mock('../../../api/market', () => ({
  fetchSectorRanking: (...args: unknown[]) => mockFetchSectorRanking(...(args as [])),
  fetchMarketOverview: (...args: unknown[]) => mockFetchMarketOverview(...(args as [])),
}))
const mockFetchRRG = vi.fn()
vi.mock('../../../api/rrg', () => ({ fetchRRGData: (...a: unknown[]) => mockFetchRRG(...(a as [])) }))
const mockFetchHistory = vi.fn()
vi.mock('../../../api/history', () => ({ fetchSectorHistory: (...a: unknown[]) => mockFetchHistory(...(a as [])) }))
vi.mock('echarts-for-react', () => ({ default: () => null }))
vi.mock('../../../contexts/TabContext', () => ({
  useNavIntent: () => ({ navigate: vi.fn(), intent: null }),
}))
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({
    selectedSector: null,
    selectSector: vi.fn(),
    clearSector: vi.fn(),
    sectorScopeFollow: true,
    setSectorScopeFollow: vi.fn(),
  }),
}))

import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider, useQuery } from '../../../contexts/DataLoadContext'
import { MarketProvider } from '../../../contexts/MarketContext'
import { SectorAnalysis } from '../SectorAnalysis'

function ranking(asOf: string) {
  return { date: asOf, as_of_date: asOf, sectors: [] }
}

// 응답이 실제 시간이 지나서 도착하게 한다 — 즉시 resolve 하면 MarketContext 의 loading
// true→false 가 한 렌더로 배칭되어, 실제 네트워크에서 생기는 '조회 끝 → effect 재실행'
// 경로(루프 방지 대상)가 테스트에서 재현되지 않는다(변이 검증에서 확인된 사각지대).
function delayedRanking(asOf: string) {
  return () => new Promise(resolve => setTimeout(() => resolve(ranking(asOf)), 5))
}

// 다른 패널을 흉내 내는 프로브 — 기존 공개 API(useQuery + meta)로 레지스트리에 기준일을 싣는다.
function Probe({ date }: { date: string }): ReactElement | null {
  useQuery(`probe:${date}`, async () => ({ date }), {
    panel: '프로브',
    meta: d => ({ asOfDate: d.date, asOfIsPartialWeek: false, gridVersion: null }),
    retryDelays: [],
  })
  return null
}

function tree(probeDate: string | null): ReactElement {
  return (
    <AnalysisParamsProvider><DataLoadProvider>
      <MarketProvider>
        <SectorAnalysis />
        {probeDate && <Probe date={probeDate} />}
      </MarketProvider>
    </DataLoadProvider></AnalysisParamsProvider>
  )
}

const settle = (): Promise<void> => new Promise(r => setTimeout(r, 60))

function tableBadge(): HTMLElement {
  const bar = document.querySelector('[data-screen="sector-table"]') as HTMLElement
  return within(bar).getByTestId('as-of-badge')
}

beforeEach(() => {
  mockFetchSectorRanking.mockReset()
  mockFetchMarketOverview.mockReset()
  mockFetchRRG.mockReset()
  mockFetchHistory.mockReset()
  mockFetchMarketOverview.mockResolvedValue({})
})

describe('섹터 표 기준일 따라잡기 — 더 새로운 기준일이 등록되면 1회 재조회', () => {
  it('(a) 다른 패널이 더 새로운 날짜를 등록하면 표가 재조회해 새 기준일을 보인다', async () => {
    mockFetchSectorRanking
      .mockImplementationOnce(delayedRanking('2026-10-22'))
      .mockImplementation(delayedRanking('2026-10-23'))
    render(tree('2026-10-23'))
    await waitFor(() => expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(tableBadge().textContent).toContain('2026-10-23'))
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2)
  })

  it('(b) 다른 패널의 날짜가 같으면 재조회하지 않는다', async () => {
    mockFetchSectorRanking.mockResolvedValue(ranking('2026-10-22'))
    render(tree('2026-10-22'))
    await waitFor(() => expect(tableBadge().textContent).toContain('2026-10-22'))
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(1)
  })

  it('(b) 다른 패널의 날짜가 더 오래되면 재조회하지 않는다 (경고 띠만 뜬다)', async () => {
    mockFetchSectorRanking.mockResolvedValue(ranking('2026-10-23'))
    render(tree('2026-10-22'))
    await waitFor(() => expect(tableBadge().textContent).toContain('2026-10-23'))
    await screen.findByTestId('asof-conflict-banner')
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(1)
  })

  it('(c) 재조회 후에도 불일치가 남으면 같은 날짜로는 다시 재조회하지 않는다 (루프 방지)', async () => {
    // 서버가 계속 10-22 를 돌려주는 상황 — 두 패널이 정당하게 다른 날짜를 말한다.
    mockFetchSectorRanking.mockImplementation(delayedRanking('2026-10-22'))
    const { rerender } = render(tree('2026-10-23'))
    await waitFor(() => expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2))
    await settle()
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2)
    // 불일치는 숨기지 않는다 — 합치 경고 띠가 그대로 남는다.
    expect(screen.getByTestId('asof-conflict-banner').textContent).toContain('섹터 표')

    // 또 다른, 더 새로운 날짜가 오면 그 날짜에 대해 한 번 더 시도한다.
    rerender(tree('2026-10-24'))
    await waitFor(() => expect(mockFetchSectorRanking).toHaveBeenCalledTimes(3))
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(3)
  })
})

describe('RRG·Bump 상태 띠가 자기 응답 기준일을 보인다', () => {
  it('RRG 탭의 기준일 배지가 RRG 응답 as_of_date 를 보인다', async () => {
    mockFetchSectorRanking.mockResolvedValue(ranking('2026-10-23'))
    mockFetchRRG.mockResolvedValue({ date: '2026-10-23', as_of_date: '2026-10-23', sectors: [], kospi: [] })
    render(tree(null))
    await waitFor(() => expect(tableBadge().textContent).toContain('2026-10-23'))
    fireEvent.click(screen.getByRole('button', { name: 'RRG' }))
    const bar = document.querySelector('[data-screen="sector-rrg"]') as HTMLElement
    await waitFor(() => expect(within(bar).getByTestId('as-of-badge').textContent).toContain('2026-10-23'))
  })

  it('Bump 탭의 기준일 배지가 Bump 응답 as_of_date 를 보인다', async () => {
    mockFetchSectorRanking.mockResolvedValue(ranking('2026-10-23'))
    mockFetchHistory.mockResolvedValue({ weeks: 12, span_days: 77, sectors: [], as_of_date: '2026-10-23' })
    render(tree(null))
    await waitFor(() => expect(tableBadge().textContent).toContain('2026-10-23'))
    fireEvent.click(screen.getByRole('button', { name: 'Bump' }))
    const bar = document.querySelector('[data-screen="sector-bump"]') as HTMLElement
    await waitFor(() => expect(within(bar).getByTestId('as-of-badge').textContent).toContain('2026-10-23'))
  })
})
