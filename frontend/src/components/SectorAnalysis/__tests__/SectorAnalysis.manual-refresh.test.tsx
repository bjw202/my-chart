// 수동 새로고침 신호(refreshAll → refreshTick)가 자체 조회 화면(섹터 표·RRG·Bump)까지 닿는다.
// 배경(감사 F1, 2026-10-26): refreshAll 은 QueryCache 를 비우고 refreshTick 만 올려 useQuery 소비자만
// 재조회했다. 표(MarketContext)·RRG·Bump 는 이 신호를 무시해, RRG/Bump 가 옛 기준일을 쥐고 있으면
// AC-SUX-037 합치 경고 띠가 모든 화면에 남고 그 [새로고침] 으로도 지워지지 않았다.
// 또 표의 `⟳ 새로고침` 은 MarketContext 를 한 번도 재조회하지 않았다(기존 결함).
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

// 응답이 실제 시간이 지나서 도착하게 한다 — 즉시 resolve 하면 loading true→false 가 한 렌더로
// 배칭되어 '조회 끝 → effect 재실행' 경로가 테스트에서 재현되지 않는다(이전 라운드 교훈).
function later<T>(value: T, ms = 5): () => Promise<T> {
  return () => new Promise(resolve => setTimeout(() => resolve(value), ms))
}

function ranking(asOf: string) {
  return { date: asOf, as_of_date: asOf, sectors: [] }
}

function rrg(asOf: string, weeks = 10) {
  const trail = (sign: number) =>
    Array.from({ length: weeks }, (_, i) => ({ date: `2026-W${String(i + 1).padStart(2, '0')}`, rs_ratio: 100 + sign * i, rs_momentum: 100 + sign * i }))
  return {
    date: asOf,
    as_of_date: asOf,
    sectors: [
      { name: '반도체', rs_ratio: 108, rs_momentum: 112, quadrant: 'leading', trail: trail(1) },
      { name: '디스플레이', rs_ratio: 95, rs_momentum: 90, quadrant: 'lagging', trail: trail(-1) },
    ],
    kospi: Array.from({ length: weeks }, (_, i) => ({ date: `2026-W${String(i + 1).padStart(2, '0')}`, close: 2000 + i * 10 })),
  }
}

function history(asOf: string) {
  return { weeks: 12, span_days: 77, sectors: [], as_of_date: asOf }
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

function tree(probeDate: string | null = null): ReactElement {
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

function bar(screenName: string): HTMLElement {
  return document.querySelector(`[data-screen="${screenName}"]`) as HTMLElement
}

// 세 화면을 모두 마운트한다 — 서브탭은 한 번 방문하면 keep-mounted 로 남는다(AC-SUX-017).
async function mountAllThree(): Promise<void> {
  fireEvent.click(screen.getByRole('button', { name: 'RRG' }))
  fireEvent.click(screen.getByRole('button', { name: 'Bump' }))
  fireEvent.click(screen.getByRole('button', { name: 'Table' }))
  await waitFor(() => {
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(1)
    expect(mockFetchRRG).toHaveBeenCalledTimes(1)
    expect(mockFetchHistory).toHaveBeenCalledTimes(1)
  })
  await waitFor(() => expect(within(bar('sector-rrg')).getByTestId('as-of-badge').textContent).toContain('2026-'))
  await waitFor(() => expect(within(bar('sector-bump')).getByTestId('as-of-badge').textContent).toContain('2026-'))
}

beforeEach(() => {
  mockFetchSectorRanking.mockReset()
  mockFetchMarketOverview.mockReset()
  mockFetchRRG.mockReset()
  mockFetchHistory.mockReset()
  mockFetchMarketOverview.mockResolvedValue({})
})

describe('수동 새로고침이 섹터 표·RRG·Bump 를 재조회한다 (감사 F1)', () => {
  it('(b) 최초 마운트에서는 각자 정확히 1회만 조회한다 — 새로고침 신호로 중복 조회하지 않는다', async () => {
    mockFetchSectorRanking.mockImplementation(later(ranking('2026-10-23')))
    mockFetchRRG.mockImplementation(later(rrg('2026-10-23')))
    mockFetchHistory.mockImplementation(later(history('2026-10-23')))
    render(tree())
    await mountAllThree()
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(1)
    expect(mockFetchRRG).toHaveBeenCalledTimes(1)
    expect(mockFetchHistory).toHaveBeenCalledTimes(1)
  })

  it('(a) 표의 ⟳ 새로고침 을 누르면 표·RRG·Bump 가 각각 정확히 1회 재조회한다', async () => {
    mockFetchSectorRanking.mockImplementation(later(ranking('2026-10-23')))
    mockFetchRRG.mockImplementation(later(rrg('2026-10-23')))
    mockFetchHistory.mockImplementation(later(history('2026-10-23')))
    render(tree())
    await mountAllThree()
    await settle()

    fireEvent.click(within(bar('sector-table')).getByTestId('refresh-btn'))
    await waitFor(() => {
      expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2)
      expect(mockFetchRRG).toHaveBeenCalledTimes(2)
      expect(mockFetchHistory).toHaveBeenCalledTimes(2)
    })
    await settle()
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2)
    expect(mockFetchRRG).toHaveBeenCalledTimes(2)
    expect(mockFetchHistory).toHaveBeenCalledTimes(2)
  })

  it('(a) RRG 가 옛 기준일이면 합치 경고 띠의 [새로고침] 이 RRG 를 재조회해 띠가 사라진다', async () => {
    // 감사가 재현한 도달 경로: RRG 는 D1, 표·Bump 는 D2 — 표는 이미 최신이라 따라잡기가 돌지 않는다.
    mockFetchSectorRanking.mockImplementation(later(ranking('2026-10-23')))
    mockFetchRRG
      .mockImplementationOnce(later(rrg('2026-10-22')))
      .mockImplementation(later(rrg('2026-10-23')))
    mockFetchHistory.mockImplementation(later(history('2026-10-23')))
    render(tree())
    await mountAllThree()
    const banner = await screen.findAllByTestId('asof-conflict-banner')
    expect(banner[0].textContent).toContain('RRG')

    fireEvent.click(within(bar('sector-table')).getByTestId('asof-conflict-refresh'))
    await waitFor(() => expect(mockFetchRRG).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByTestId('asof-conflict-banner')).toBeNull())
    expect(within(bar('sector-rrg')).getByTestId('as-of-badge').textContent).toContain('2026-10-23')
  })

  it('RRG 새로고침은 사용자가 고른 섹터 표시와 윈도우 위치를 보존한다', async () => {
    mockFetchSectorRanking.mockImplementation(later(ranking('2026-10-23')))
    mockFetchRRG.mockImplementation(later(rrg('2026-10-23')))
    mockFetchHistory.mockImplementation(later(history('2026-10-23')))
    render(tree())
    await mountAllThree()
    const rrgPane = bar('sector-rrg').parentElement as HTMLElement
    const display = within(rrgPane).getByRole('checkbox', { name: /디스플레이/, hidden: true }) as HTMLInputElement
    fireEvent.click(display)
    expect(display.checked).toBe(false)
    const slider = rrgPane.querySelector('.rrg-slider') as HTMLInputElement
    fireEvent.change(slider, { target: { value: '9' } })
    expect(slider.value).toBe('9')

    fireEvent.click(within(bar('sector-table')).getByTestId('refresh-btn'))
    await waitFor(() => expect(mockFetchRRG).toHaveBeenCalledTimes(2))
    await settle()
    const displayAfter = within(rrgPane).getByRole('checkbox', { name: /디스플레이/, hidden: true }) as HTMLInputElement
    expect(displayAfter.checked).toBe(false)
    expect((rrgPane.querySelector('.rrg-slider') as HTMLInputElement).value).toBe('9')
  })

  it('RRG 윈도우가 끝에 있었으면 새로고침 후 새 마지막 주로 따라간다', async () => {
    mockFetchSectorRanking.mockImplementation(later(ranking('2026-10-30')))
    mockFetchRRG
      .mockImplementationOnce(later(rrg('2026-10-23', 10)))
      .mockImplementation(later(rrg('2026-10-30', 11)))
    mockFetchHistory.mockImplementation(later(history('2026-10-30')))
    render(tree())
    await mountAllThree()
    const rrgPane = bar('sector-rrg').parentElement as HTMLElement
    expect((rrgPane.querySelector('.rrg-slider') as HTMLInputElement).value).toBe('10')

    fireEvent.click(within(bar('sector-table')).getByTestId('refresh-btn'))
    await waitFor(() => expect(mockFetchRRG).toHaveBeenCalledTimes(2))
    await waitFor(() => expect((rrgPane.querySelector('.rrg-slider') as HTMLInputElement).value).toBe('11'))
  })
})

describe('기준일 따라잡기의 rankingLoading 대기 — 진행 중 조회와 겹쳐 중복 조회하지 않는다 (감사 F2)', () => {
  it('기간 토글로 표 조회가 진행 중일 때 더 새로운 날짜가 등록돼도 추가 조회를 내지 않는다', async () => {
    mockFetchSectorRanking.mockImplementationOnce(later(ranking('2026-10-22')))
    const { rerender } = render(tree())
    await waitFor(() => expect(within(bar('sector-table')).getByTestId('as-of-badge').textContent).toContain('2026-10-22'))
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(1)

    // 기간 토글 → 느린 조회(새 날짜 응답)가 진행 중인 사이에 다른 패널이 새 날짜를 등록한다.
    mockFetchSectorRanking.mockImplementation(later(ranking('2026-10-23'), 80))
    fireEvent.click(screen.getByRole('button', { name: '3M' }))
    await waitFor(() => expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2))
    rerender(tree('2026-10-23'))

    await waitFor(() => expect(within(bar('sector-table')).getByTestId('as-of-badge').textContent).toContain('2026-10-23'))
    await settle()
    expect(mockFetchSectorRanking).toHaveBeenCalledTimes(2)
  })
})
