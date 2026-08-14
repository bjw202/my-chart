// RED: AC-SUX-054 (ER-3) — 빈 상태는 원인을 말한다. 활성 필터 3개 텍스트 + 각각의 해제 액션.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import type { ReactElement } from 'react'
import type { StageOverviewResponse, Stage2Candidate } from '../../../types/stage'
import { AnalysisParamsProvider, useAnalysisParams } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { fetchStageOverview } from '../../../api/stage'
import { StockExplorer } from '../StockExplorer'

vi.mock('../../../api/stage', () => ({ fetchStageOverview: vi.fn() }))
vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({ activeTab: 'stock-explorer', setActiveTab: vi.fn() }),
  useNavIntent: () => ({ intent: null, navigate: vi.fn() }),
}))

const mockSetSectorScopeFollow = vi.fn()
let mockSectorScopeFollow = true
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({
    selectedSector: '디스플레이',
    sectorScopeFollow: mockSectorScopeFollow,
    setSectorScopeFollow: (v: boolean) => { mockSectorScopeFollow = v; mockSetSectorScopeFollow(v) },
  }),
}))

function stock(over: Partial<Stage2Candidate>): Stage2Candidate {
  return {
    code: '000100', name: '디스플A', market: 'KOSDAQ',
    sector_major: '디스플레이', sector_minor: '패널',
    stage: 3, stage_detail: 'stage3',
    rs_12m: 50, chg_1m: 1, volume_ratio: 1, close: 100, sma50: 90, sma200: 80,
    ...over,
  }
}

const overview = (rows: Stage2Candidate[]): StageOverviewResponse => ({
  distribution: { stage1: 0, stage2: 0, stage3: 1, stage4: 0, total: 1 } as never,
  by_sector: [],
  stage2_candidates: [],
  all_stocks: rows,
  as_of_date: '2026-08-11',
  as_of_is_partial_week: false,
} as never)

// 시장 토글을 KOSPI 로 바꾸는 하네스 (헤더 토글 대체)
function MarketSwitch(): ReactElement {
  const { setMarket, market } = useAnalysisParams()
  return <button onClick={() => setMarket('kospi')}>to-kospi:{market}</button>
}

function renderSE(): void {
  render(
    <AnalysisParamsProvider>
      <DataLoadProvider>
        <MarketSwitch />
        <StockExplorer />
      </DataLoadProvider>
    </AnalysisParamsProvider>,
  )
}

beforeEach(() => {
  vi.mocked(fetchStageOverview).mockReset()
  mockSectorScopeFollow = true
  mockSetSectorScopeFollow.mockClear()
})
afterEach(() => cleanup())

describe('AC-SUX-054 — 빈 상태는 원인을 말한다 (ER-3)', () => {
  it('섹터=디스플레이 + Stage=2 + 시장=KOSPI 로 0건이면 활성 필터 3개가 텍스트로 표시된다', async () => {
    // 모집단: 디스플레이 KOSDAQ Stage3 1종목 → 위 3필터 조합에서는 0건이 된다.
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([stock({})]))
    renderSE()
    await waitFor(() => expect(screen.getByTestId('stock-table')).toBeInTheDocument())

    // 시장 KOSPI + Stage 2 를 적용
    fireEvent.click(screen.getByText(/to-kospi/))
    await waitFor(() => expect(screen.getByTestId('empty-state-with-cause')).toBeInTheDocument())

    const labels = screen.getAllByTestId('empty-state-filter-label').map(e => e.textContent)
    // 시장·섹터 두 필터가 원인으로 명시된다 (Stage 는 아직 미적용)
    expect(labels.some(l => l?.includes('KOSPI'))).toBe(true)
    expect(labels.some(l => l?.includes('디스플레이'))).toBe(true)
  })

  it('3개 필터가 모두 활성이면 3개 라벨 + 3개 해제 액션이 렌더된다', async () => {
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([stock({})]))
    renderSE()
    await waitFor(() => expect(screen.getByTestId('stock-table')).toBeInTheDocument())
    fireEvent.click(screen.getByText(/to-kospi/))
    // Stage 2 세그먼트 클릭으로 stageFilter 적용
    const seg = document.querySelector('[data-segment-key="stage2"]') as HTMLElement
    expect(seg).not.toBeNull()
    fireEvent.click(seg)

    await waitFor(() => expect(screen.getByTestId('empty-state-with-cause')).toBeInTheDocument())
    const labels = screen.getAllByTestId('empty-state-filter-label').map(e => e.textContent)
    expect(labels).toHaveLength(3)
    expect(labels.some(l => l?.includes('Stage 2'))).toBe(true)
    expect(labels.some(l => l?.includes('KOSPI'))).toBe(true)
    expect(labels.some(l => l?.includes('디스플레이'))).toBe(true)

    const actionTexts = [...screen.getByTestId('empty-state-filters').querySelectorAll('button')]
      .map(a => a.textContent)
    expect(actionTexts).toEqual(
      expect.arrayContaining(['[Stage 필터 해제]', '[시장 전체로]', '[섹터 스코프 해제]']),
    )
  })

  it('[시장 전체로] 클릭은 시장만 해제한다 — 섹터 스코프는 유지된다', async () => {
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([stock({})]))
    renderSE()
    await waitFor(() => expect(screen.getByTestId('stock-table')).toBeInTheDocument())
    fireEvent.click(screen.getByText(/to-kospi/))
    await waitFor(() => expect(screen.getByTestId('empty-state-with-cause')).toBeInTheDocument())

    fireEvent.click(screen.getByText('[시장 전체로]'))
    // 시장이 all 로 돌아오면 KOSDAQ 종목이 다시 보인다
    await waitFor(() => expect(screen.getByText('디스플A')).toBeInTheDocument())
    // 섹터 스코프 해제는 호출되지 않았다 (각 액션은 자기 상태만 건드린다)
    expect(mockSetSectorScopeFollow).not.toHaveBeenCalled()
  })

  it('[섹터 스코프 해제] 클릭은 섹터만 해제한다 — setSectorScopeFollow(false) 만 호출', async () => {
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([stock({ sector_major: '반도체' })]))
    renderSE()
    // selectedSector='디스플레이' 인데 모집단은 반도체 → 0건
    await waitFor(() => expect(screen.getByTestId('empty-state-with-cause')).toBeInTheDocument())
    fireEvent.click(screen.getByText('[섹터 스코프 해제]'))
    expect(mockSetSectorScopeFollow).toHaveBeenCalledWith(false)
    expect(mockSetSectorScopeFollow).toHaveBeenCalledTimes(1)
  })

  it('결과가 있으면 빈 상태를 렌더하지 않는다', async () => {
    vi.mocked(fetchStageOverview).mockResolvedValue(overview([stock({})]))
    renderSE()
    await waitFor(() => expect(screen.getByText('디스플A')).toBeInTheDocument())
    expect(screen.queryByTestId('empty-state-with-cause')).not.toBeInTheDocument()
  })
})
