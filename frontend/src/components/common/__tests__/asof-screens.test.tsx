// RED: AC-SUX-037 (SN-4) — 기준일 배지가 섹터 분석 4개 서브탭 + 종목 탐색 전 화면에 상설 렌더된다.
//      + 패널 간 기준일 불일치 경고 띠 (SN-3 클라이언트 측)
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider, useQuery } from '../../../contexts/DataLoadContext'
import { SelectionProvider } from '../../../contexts/SelectionContext'
import { SectorAnalysis } from '../../SectorAnalysis/SectorAnalysis'
import { DataStatusBar } from '../DataStatusBar'

vi.mock('../../../contexts/MarketContext', () => ({
  useMarket: () => ({
    sectorRanking: {
      date: '2026-08-11',
      as_of_date: '2026-08-11',
      as_of_is_partial_week: false,
      sectors: [],
      excluded: [],
    },
    loading: false,
    error: null,
    refresh: vi.fn(),
  }),
}))
vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({ activeTab: 'sector-analysis', setActiveTab: vi.fn() }),
  useNavIntent: () => ({ navigate: vi.fn(), intent: null }),
}))
// 하위 차트는 조회를 수행하지 않는 더미로 대체 (배지 존재만 검증)
vi.mock('../../SectorAnalysis/BubbleChart', () => ({
  BubbleChart: () => <div data-testid="bubble-stub" />,
}))
vi.mock('../../SectorAnalysis/RRGChart', () => ({
  RRGChart: () => <div data-testid="rrg-stub" />,
}))
vi.mock('../../SectorAnalysis/BumpChart', () => ({
  BumpChart: () => <div data-testid="bump-stub" />,
}))

afterEach(() => cleanup())

function Providers({ children }: { children: ReactNode }) {
  return (
    <AnalysisParamsProvider>
      <DataLoadProvider>
        <SelectionProvider>{children}</SelectionProvider>
      </DataLoadProvider>
    </AnalysisParamsProvider>
  )
}

// 서브탭 라벨 → 그 pane 이 소유하는 배지의 data-screen 값.
// Bubble pane 의 배지는 BubbleChart 내부에 있어(여기서는 stub) 별도 파일에서 단언한다
// (BubbleChart.m6.test.tsx — 실물 컴포넌트로 as-of-badge / refresh-btn 단언).
const SECTOR_SUB_TABS = [
  ['Table', 'sector-table'],
  ['RRG', 'sector-rrg'],
  ['Bump', 'sector-bump'],
] as const

describe('AC-SUX-037 / SN-4 — 기준일 배지 상설 노출 (화면별 루프 단언)', () => {
  it.each(SECTOR_SUB_TABS)('섹터 분석 %s 서브탭 pane 이 자기 기준일 배지(%s)를 갖는다', (tab, screenId) => {
    render(<Providers><SectorAnalysis /></Providers>)
    fireEvent.click(screen.getByText(tab))
    const pane = screen.getAllByTestId('data-status-bar')
      .find(b => b.getAttribute('data-screen') === screenId)
    expect(pane).toBeDefined()
    // 배지는 그 pane 안에 있다 — 다른 pane 의 배지를 빌려오지 않는다.
    expect(pane!.querySelector('[data-testid="as-of-badge"]')).not.toBeNull()
  })

  it('4개 서브탭을 모두 방문하면 table/rrg/bump pane 이 각각 자기 배지를 갖는다', () => {
    render(<Providers><SectorAnalysis /></Providers>)
    ;['Table', 'Bubble', 'RRG', 'Bump'].forEach(t => fireEvent.click(screen.getByText(t)))
    const screens = screen.getAllByTestId('data-status-bar').map(b => b.getAttribute('data-screen'))
    expect(screens).toContain('sector-table')
    expect(screens).toContain('sector-rrg')
    expect(screens).toContain('sector-bump')
  })

  it('종목 탐색 화면도 같은 배지 컴포넌트를 쓴다 (공용 컴포넌트 단언)', () => {
    render(
      <Providers>
        <DataStatusBar screen="stock-explorer" asOfDate="2026-08-11" asOfIsPartialWeek={false} />
      </Providers>,
    )
    expect(screen.getByTestId('data-status-bar').getAttribute('data-screen')).toBe('stock-explorer')
    expect(screen.getByTestId('as-of-badge').textContent).toBe('기준일 2026-08-11')
  })
})

describe('AC-SUX-037 / SN-3 — 패널 간 기준일 불일치 경고', () => {
  function TwoPanels({ dateA, dateB }: { dateA: string; dateB: string }) {
    const meta = (d: { as_of_date: string }) => ({
      asOfDate: d.as_of_date, asOfIsPartialWeek: false, gridVersion: null,
    })
    useQuery('pa', () => Promise.resolve({ as_of_date: dateA }), { panel: '섹터 순위', meta })
    useQuery('pb', () => Promise.resolve({ as_of_date: dateB }), { panel: '종목 탐색', meta })
    return <DataStatusBar screen="probe" asOfDate={dateA} asOfIsPartialWeek={false} />
  }

  it('두 패널 기준일이 다르면 두 날짜와 패널명을 담은 경고 띠 + [새로고침] 이 렌더된다', async () => {
    render(<Providers><TwoPanels dateA="2026-08-07" dateB="2026-08-11" /></Providers>)
    await waitFor(() => expect(screen.getByTestId('asof-conflict-banner')).toBeInTheDocument())
    const text = screen.getByTestId('asof-conflict-banner').textContent ?? ''
    expect(text).toContain('2026-08-07')
    expect(text).toContain('2026-08-11')
    expect(text).toContain('섹터 순위')
    expect(text).toContain('종목 탐색')
    expect(screen.getByTestId('asof-conflict-refresh')).toBeInTheDocument()
  })

  it('두 패널 기준일이 같으면 경고 띠가 렌더되지 않는다', async () => {
    render(<Providers><TwoPanels dateA="2026-08-11" dateB="2026-08-11" /></Providers>)
    await waitFor(() => expect(screen.getByTestId('as-of-badge')).toBeInTheDocument())
    await new Promise(r => setTimeout(r, 20))
    expect(screen.queryByTestId('asof-conflict-banner')).not.toBeInTheDocument()
  })
})
