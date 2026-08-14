// RED: AC-SUX-018 — 시장 토글 실동작 (market 파라미터가 실제로 fetch 에 전달된다 — ST-4 무동작 해소)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// api/market 를 스파이로 mock — fetchSectorRanking 에 전달되는 인자(market)를 단언한다
const mockFetchSectorRanking = vi.fn()
const mockFetchMarketOverview = vi.fn()
vi.mock('../../../api/market', () => ({
  fetchSectorRanking: (...args: unknown[]) => mockFetchSectorRanking(...(args as [])),
  fetchMarketOverview: (...args: unknown[]) => mockFetchMarketOverview(...(args as [])),
}))

// SectorAnalysis (M3) 는 useNavIntent + useSelection 을 소비
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
import { MarketProvider } from '../../../contexts/MarketContext'
import { SectorAnalysis } from '../SectorAnalysis'

function makeRanking() {
  return { date: '2026-08-11', sectors: [] }
}

describe('AC-SUX-018 — 시장 토글 실동작 (market=kospi 파라미터 전달)', () => {
  beforeEach(() => {
    mockFetchSectorRanking.mockReset()
    mockFetchMarketOverview.mockReset()
    mockFetchSectorRanking.mockResolvedValue(makeRanking())
    mockFetchMarketOverview.mockResolvedValue({})
  })

  it('KOSPI 토글 클릭 시 fetchSectorRanking 가 market="kospi" 인자로 호출된다', async () => {
    const user = userEvent.setup()
    render(
      <AnalysisParamsProvider>
        <MarketProvider>
          <SectorAnalysis />
        </MarketProvider>
      </AnalysisParamsProvider>,
    )
    // 마운트 시 최초 조회 (market=all)
    await waitFor(() => expect(mockFetchSectorRanking).toHaveBeenCalled())
    expect(mockFetchSectorRanking).toHaveBeenLastCalledWith('all')

    // KOSPI 버튼 클릭 → market 변경
    const kospiBtn = screen.getByRole('button', { name: /kospi/i })
    await user.click(kospiBtn)

    // market=kospi 로 재조회 발생 (무동작 ST-4 해소)
    await waitFor(() => {
      expect(mockFetchSectorRanking).toHaveBeenLastCalledWith('kospi')
    })
  })

  it('KOSDAQ 토글 클릭 시 fetchSectorRanking 가 market="kosdaq" 인자로 호출된다', async () => {
    const user = userEvent.setup()
    render(
      <AnalysisParamsProvider>
        <MarketProvider>
          <SectorAnalysis />
        </MarketProvider>
      </AnalysisParamsProvider>,
    )
    await waitFor(() => expect(mockFetchSectorRanking).toHaveBeenCalled())
    const kosdaqBtn = screen.getByRole('button', { name: /kosdaq/i })
    await user.click(kosdaqBtn)
    await waitFor(() => {
      expect(mockFetchSectorRanking).toHaveBeenLastCalledWith('kosdaq')
    })
  })
})
