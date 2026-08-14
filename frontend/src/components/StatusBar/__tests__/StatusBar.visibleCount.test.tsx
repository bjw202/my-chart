// RED: 푸터 종목 수는 "지금 화면에 보이는 모집단"과 일치해야 한다.
// 기존 결함: StatusBar 가 useScreen().results.total(스크리닝 전체 수)만 읽어,
// StockExplorer 의 섹터/시장/Stage 필터 결과와 다른 숫자를 표시했다.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import type { ReactElement } from 'react'
import type { StageOverviewResponse, Stage2Candidate } from '../../../types/stage'
import { AnalysisParamsProvider, useAnalysisParams } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { ScreenProvider, useScreen } from '../../../contexts/ScreenContext'
import { WatchlistProvider } from '../../../contexts/WatchlistContext'
import { fetchStageOverview } from '../../../api/stage'
import { screenStocks } from '../../../api/screen'
import { fetchLastUpdated } from '../../../api/db'
import { DEFAULT_SCREEN_REQUEST } from '../../../types/filter'
import { StockExplorer } from '../../StockExplorer/StockExplorer'
import { StatusBar } from '../StatusBar'

vi.mock('../../../api/stage', () => ({ fetchStageOverview: vi.fn() }))
vi.mock('../../../api/screen', () => ({ screenStocks: vi.fn() }))
vi.mock('../../../api/db', () => ({ fetchLastUpdated: vi.fn() }))
vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({ activeTab: 'stock-explorer', setActiveTab: vi.fn() }),
  useNavIntent: () => ({ intent: null, navigate: vi.fn() }),
}))
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({
    selectedSector: '스마트폰',
    sectorScopeFollow: true,
    setSectorScopeFollow: vi.fn(),
  }),
}))

function stock(over: Partial<Stage2Candidate>): Stage2Candidate {
  return {
    code: '000100', name: '종목', market: 'KOSDAQ',
    sector_major: '스마트폰', sector_minor: '부품',
    stage: 4, stage_detail: 'stage4',
    rs_12m: 50, chg_1m: 1, volume_ratio: 1, close: 100, sma50: 90, sma200: 80,
    ...over,
  }
}

const overview = (rows: Stage2Candidate[]): StageOverviewResponse => ({
  distribution: { stage1: 0, stage2: 0, stage3: 0, stage4: rows.length, total: rows.length },
  by_sector: [],
  stage2_candidates: [],
  all_stocks: rows,
  as_of_date: '2026-08-11',
  as_of_is_partial_week: false,
} as never)

// 스크리닝 전체 수(52)를 ScreenContext 에 채우는 하네스 — 필터 결과(3)와 다른 값이어야
// "푸터가 어느 모집단을 따르는가"를 판별할 수 있다.
function ScreenSeed(): ReactElement {
  const { applyFilters } = useScreen()
  return <button onClick={() => void applyFilters(DEFAULT_SCREEN_REQUEST)}>seed-screen</button>
}

function MarketSwitch(): ReactElement {
  const { setMarket } = useAnalysisParams()
  return <button onClick={() => setMarket('kospi')}>to-kospi</button>
}

function renderApp(): void {
  render(
    <AnalysisParamsProvider>
      <DataLoadProvider>
        <ScreenProvider>
          <WatchlistProvider>
            <ScreenSeed />
            <MarketSwitch />
            <StockExplorer />
            <StatusBar />
          </WatchlistProvider>
        </ScreenProvider>
      </DataLoadProvider>
    </AnalysisParamsProvider>,
  )
}

beforeEach(() => {
  vi.mocked(fetchStageOverview).mockReset()
  vi.mocked(screenStocks).mockReset()
  vi.mocked(fetchLastUpdated).mockResolvedValue({ last_updated: '2026-08-11' } as never)
  vi.mocked(screenStocks).mockResolvedValue({ total: 52, sectors: [] })
})
afterEach(() => cleanup())

describe('푸터 종목 수 — 표시 중인 필터 결과와 일치', () => {
  it('섹터 필터가 걸린 상태에서 스크리닝 전체 수(52)가 아니라 보이는 행 수를 표시한다', async () => {
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([
      stock({ code: '000100', name: '스마트A' }),
      stock({ code: '000200', name: '스마트B' }),
      stock({ code: '000300', name: '스마트C' }),
      stock({ code: '000400', name: '기계A', sector_major: '기계' }),
      stock({ code: '000500', name: '기계B', sector_major: '기계' }),
    ]))
    renderApp()

    await screen.findByText('스마트A')
    fireEvent.click(screen.getByText('seed-screen'))
    await waitFor(() => expect(vi.mocked(screenStocks)).toHaveBeenCalled())

    // 표에 보이는 행은 스마트폰 3종목뿐이다.
    await waitFor(() => {
      expect(screen.getByText(/개 종목 검색됨/).textContent).toContain('3개 종목 검색됨')
    })
  })

  it('시장 토글로 모집단이 줄면 푸터도 함께 줄어든다', async () => {
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([
      stock({ code: '000100', name: '스마트A', market: 'KOSPI' }),
      stock({ code: '000200', name: '스마트B', market: 'KOSDAQ' }),
      stock({ code: '000300', name: '스마트C', market: 'KOSDAQ' }),
    ]))
    renderApp()

    await screen.findByText('스마트A')
    await waitFor(() => {
      expect(screen.getByText(/개 종목 검색됨/).textContent).toContain('3개 종목 검색됨')
    })

    fireEvent.click(screen.getByText('to-kospi'))
    await waitFor(() => {
      expect(screen.getByText(/개 종목 검색됨/).textContent).toContain('1개 종목 검색됨')
    })
  })

  it('Stage 세그먼트로 좁히면 푸터도 그 수를 따른다', async () => {
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([
      stock({ code: '000100', name: '스마트A', stage: 2 }),
      stock({ code: '000200', name: '스마트B', stage: 4 }),
      stock({ code: '000300', name: '스마트C', stage: 4 }),
    ]))
    renderApp()

    await screen.findByText('스마트A')
    fireEvent.click(screen.getByRole('button', { name: /Stage 2/i }))

    await waitFor(() => {
      expect(screen.getByText(/개 종목 검색됨/).textContent).toContain('1개 종목 검색됨')
    })
  })
})
