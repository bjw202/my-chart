// SPEC-SECTOR-DISPLAY-UNIFY-001 M7 — REQ-SDU-006~011 / AC-SDU-006·007·009·010·011.
// Table 기간 토글 실동작: 봉투 data[] 의 기간별 rank 조인·폴백 캡션·열 마커·
// 안내 문구 표시 라벨·버블 축 거동(Y 불변/X 만 변화).
// AC-SDU-006/007/010/011 은 SectorAnalysis 를 end-to-end 로 렌더해 관측한다
// (조인 로직이 산출하는 값을 표가 실제로 그리는지 — 같은 헬퍼 양변 비교가 아니다).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import type { SectorRankItem, SectorRankingResponse } from '../../../types/market'
import type { SectorBubbleItem } from '../../../types/bubble'

const mockFetchSectorRanking = vi.fn()
const mockFetchMarketOverview = vi.fn()
vi.mock('../../../api/market', () => ({
  fetchSectorRanking: (...args: unknown[]) => mockFetchSectorRanking(...(args as [])),
  fetchMarketOverview: (...args: unknown[]) => mockFetchMarketOverview(...(args as [])),
}))

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

// AC-SDU-009: 버블 option 의 시리즈 데이터를 읽기 위해 ECharts 를 목킹한다.
vi.mock('echarts-for-react', () => ({
  default: vi.fn((): ReactElement => <div data-testid="echarts-mock" />),
}))

import ReactECharts from 'echarts-for-react'
import { SectorAnalysis } from '../SectorAnalysis'
import { SectorBubbleChart } from '../SectorBubbleChart'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { MarketProvider } from '../../../contexts/MarketContext'

const mockChart = vi.mocked(ReactECharts)

function sector(name: string, rank: number): SectorRankItem {
  return {
    name,
    stock_count: 10,
    returns: { w1: 1, m1: 2, m3: 3 },
    excess_returns: { w1: 0.5, m1: 1.5, m3: 2.5 },
    rs_avg: 50,
    rs_top_pct: 20,
    nh_pct: 10,
    stage2_pct: 30,
    composite_score: 60,
    rank,
    rank_change: 0,
  }
}

// sectors[] 순위 [1,2,3] ↔ data[] 순위 [3,1,2] — 서로 다른 순서여야 한다(항진명제 방지).
const RANKING_WITH_DATA: SectorRankingResponse = {
  date: '2026-08-11',
  sectors: [sector('A', 1), sector('B', 2), sector('C', 3)],
  data: [
    { name: 'A', rank: 3, rank_change: null },
    { name: 'B', rank: 1, rank_change: 2 },
    { name: 'C', rank: 2, rank_change: -1 },
  ],
}

const RANKING_NO_DATA: SectorRankingResponse = {
  date: '2026-08-11',
  sectors: [sector('A', 1), sector('B', 2), sector('C', 3)],
}

function renderAnalysis(ranking: SectorRankingResponse) {
  mockFetchSectorRanking.mockResolvedValue(ranking)
  mockFetchMarketOverview.mockResolvedValue({})
  return render(
    <AnalysisParamsProvider><DataLoadProvider>
      <MarketProvider>
        <SectorAnalysis />
      </MarketProvider>
    </DataLoadProvider></AnalysisParamsProvider>,
  )
}

function rowOrder(): string[] {
  return Array.from(document.querySelectorAll('tbody tr'))
    .map(tr => (tr.querySelector('td:nth-child(2)')?.textContent ?? '').trim())
}

describe('AC-SDU-006 — 기간별 순위 실반영 (data[] 조인)', () => {
  beforeEach(() => {
    mockFetchSectorRanking.mockReset()
    mockFetchMarketOverview.mockReset()
  })

  it('data[] 의 기간 순위가 화면 순서·rank 값으로 반영된다 (composite [1,2,3] → 기간 [3,1,2])', async () => {
    renderAnalysis(RANKING_WITH_DATA)
    await waitFor(() => expect(screen.getByText('A')).toBeInTheDocument())
    // 기간 순위: B=1, C=2, A=3 → rank asc 정렬은 B,C,A
    expect(rowOrder()).toEqual(['B', 'C', 'A'])
    // 섹터 A 의 rank 셀은 composite 1 이 아니라 기간값 3
    const rowA = screen.getByText('A').closest('tr') as HTMLTableRowElement
    expect(rowA.querySelector('[data-testid="rank-value"]')?.textContent).toBe('3')
  })

  it('기간 토글 전환 시 fetchSectorRanking 가 period 인자로 재호출된다', async () => {
    const user = userEvent.setup()
    renderAnalysis(RANKING_WITH_DATA)
    await waitFor(() => expect(mockFetchSectorRanking).toHaveBeenCalled())
    await user.click(screen.getByRole('button', { name: '1W' }))
    await waitFor(() => {
      expect(mockFetchSectorRanking).toHaveBeenLastCalledWith('all', '1w')
    })
  })
})

describe('AC-SDU-007 — data[] 부재 폴백 캡션', () => {
  beforeEach(() => {
    mockFetchSectorRanking.mockReset()
    mockFetchMarketOverview.mockReset()
  })

  it('data[] 없는 응답에서 composite 순위 사용 + 캡션이 그 사실을 말한다', async () => {
    renderAnalysis(RANKING_NO_DATA)
    await waitFor(() => expect(screen.getByText('A')).toBeInTheDocument())
    // composite 순서 그대로 A,B,C
    expect(rowOrder()).toEqual(['A', 'B', 'C'])
    expect(screen.getByTestId('ranking-basis-caption').textContent).toBe('순위 기준: 종합점수(3기간 가중)')
  })
})

describe('AC-SDU-010 — activePeriod 열 마커 + 세 수익률 열 유지', () => {
  beforeEach(() => {
    mockFetchSectorRanking.mockReset()
    mockFetchMarketOverview.mockReset()
  })

  it("activePeriod='1m' 렌더 시 1M 열에 (순위 기준), 1W/1M/3M 세 열 모두 존재", async () => {
    renderAnalysis(RANKING_WITH_DATA)
    await waitFor(() => expect(screen.getByText('A')).toBeInTheDocument())
    // 세 수익률 열 유지 (DEC-F4) — 열 헤더(thead)에 1W/1M/3M 전부 (토글 버튼과 구분해 스코프)
    const thead = document.querySelector('thead') as HTMLElement
    expect(within(thead).getByText('1W')).toBeInTheDocument()
    expect(within(thead).getByText('1M')).toBeInTheDocument()
    expect(within(thead).getByText('3M')).toBeInTheDocument()
    // 1M 헤더에만 (순위 기준) — 마커는 헤더 셀 안에 있다
    const headers = Array.from(document.querySelectorAll('thead th')).map(th => th.textContent ?? '')
    const oneM = headers.find(h => h.includes('1M'))
    expect(oneM).toContain('(순위 기준)')
    const oneW = headers.find(h => h.includes('1W'))
    expect(oneW).not.toContain('(순위 기준)')
    // data[] 있으므로 폴백 캡션은 없다
    expect(screen.queryByTestId('ranking-basis-caption')).toBeNull()
  })
})

describe('AC-SDU-011 — 안내 문구 표시 라벨', () => {
  beforeEach(() => {
    mockFetchSectorRanking.mockReset()
    mockFetchMarketOverview.mockReset()
  })

  it('비-rank 정렬 시 안내 문구가 원시 상태값(기간 1m)이 아니라 표시 라벨(기간 1M · 시장 All)을 쓴다', async () => {
    const user = userEvent.setup()
    renderAnalysis(RANKING_WITH_DATA)
    await waitFor(() => expect(screen.getByText('A')).toBeInTheDocument())
    // 비-rank 정렬 유도 — thead 의 1W 열 헤더 클릭 (기간 토글 버튼이 아님)
    const thead = document.querySelector('thead') as HTMLElement
    await user.click(within(thead).getByText('1W'))
    const notice = screen.getByTestId('sort-notice').textContent ?? ''
    expect(notice).toContain('기간 1M')
    expect(notice).toContain('시장 All')
    expect(notice).not.toContain('기간 1m')
  })
})

describe('AC-SDU-009 — 기간 토글 축 거동 (버블)', () => {
  // Y(rs_avg)는 기간 무변, X(초과수익률)만 기간별 값 — 백엔드 INV-3 의 화면측 회귀 방어.
  // 관측은 SectorBubbleChart 가 차트에 넘기는 프로덕션 series 데이터로 한다.
  const RS = 60

  function captureSeries(period: '1w' | '1m' | '3m', excess: number): { x: number; y: number } {
    mockChart.mockClear()
    const item: SectorBubbleItem = {
      name: 'A', excess_return: excess, rs_avg: RS, trading_value: 1e11, period_return: 2,
    }
    render(<SectorBubbleChart sectors={[item]} period={period} onSectorClick={() => {}} />)
    const call = mockChart.mock.calls.at(-1)
    if (!call) throw new Error('ECharts 렌더 없음')
    const series = (call[0].option as { series: { data: { value: number[] }[] }[] }).series
    const v = series[0].data[0].value
    return { x: v[0], y: v[1] }
  }

  it('기간 전환(1W→1M→3M)에서 Y(RS)는 불변이고 X(초과수익률)만 변한다', () => {
    const w = captureSeries('1w', 1.0)
    const m = captureSeries('1m', 2.0)
    const q = captureSeries('3m', 3.0)
    // Y 불변 — 둘 다 단언한다(한쪽만 두면 전체가 상수여도 통과)
    expect(w.y).toBe(m.y)
    expect(m.y).toBe(q.y)
    expect(w.y).toBe(RS)
    // X 만 변화
    expect(w.x).not.toBe(m.x)
    expect(m.x).not.toBe(q.x)
  })
})
