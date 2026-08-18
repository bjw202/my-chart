// AC-SUX-022 / 023 / 027 / 019(컨테이너) / 025(컨테이너) — SectorAnalysis M4 (SPEC-SECTOR-UX-001 M4).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// ② 봉투 필드(excluded / baseline_date) 포함 픽스처
const mockMarketState = {
  sectorRanking: {
    date: '2026-08-11',
    sectors: [
      { name: '반도체', stock_count: 30, returns: { w1: 1, m1: 2, m3: 3 }, excess_returns: { w1: 0.5, m1: 1, m3: 2 }, rs_avg: 70, rs_top_pct: 25, nh_pct: 15, stage2_pct: 35, composite_score: 80, rank: 1, rank_change: 2 },
      { name: '은행', stock_count: 20, returns: { w1: -1, m1: -2, m3: 1 }, excess_returns: { w1: -0.5, m1: -1, m3: 0.5 }, rs_avg: 45, rs_top_pct: 10, nh_pct: 5, stage2_pct: 15, composite_score: 40, rank: 2, rank_change: -1 },
      { name: '증권', stock_count: 15, returns: { w1: 0, m1: 0, m3: 0 }, excess_returns: { w1: 0, m1: 0, m3: 0 }, rs_avg: 50, rs_top_pct: 12, nh_pct: 8, stage2_pct: 20, composite_score: 55, rank: 3, rank_change: 0 },
    ],
    excluded: [
      { sector: '디스플레이', reason: 'insufficient_members', count: 4 },
    ],
    baseline_date: '2026-08-01',
    as_of_date: '2026-08-11',
  },
  overview: null,
  loading: false,
  error: null,
  refresh: vi.fn(),
}

vi.mock('../../../contexts/MarketContext', () => ({
  useMarket: () => mockMarketState,
}))

const mockNavigate = vi.fn()
vi.mock('../../../contexts/TabContext', () => ({
  useNavIntent: () => ({ navigate: mockNavigate, intent: null }),
}))

import { SectorAnalysis } from '../SectorAnalysis'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { SelectionProvider } from '../../../contexts/SelectionContext'

function renderSectorAnalysis() {
  return render(
    <AnalysisParamsProvider><DataLoadProvider>
      <SelectionProvider>
        <SectorAnalysis />
      </SelectionProvider>
    </DataLoadProvider></AnalysisParamsProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

// AC-SUX-022 (REQ-SUX-020): 비-rank 정렬 고지 띠
describe('AC-SUX-022 — 정렬 고지 띠', () => {
  it('rank 정렬 상태에서는 고지 띠가 렌더되지 않는다', () => {
    renderSectorAnalysis()
    expect(screen.queryByTestId('sort-notice')).not.toBeInTheDocument()
  })

  it('비-rank 열로 정렬하면 고지 띠가 렌더되고 현재 정렬 기준·period·market 가 포함된다', () => {
    renderSectorAnalysis()
    // RS Avg 헤더 클릭 (thead 내 "RS Avg" span)
    fireEvent.click(screen.getByText('RS Avg'))
    const notice = screen.getByTestId('sort-notice')
    expect(notice.textContent).toContain('rs_avg')
    // REQ-SDU-010 (M7): 고지 띠는 원시 상태값(1m/all)이 아니라 표시 라벨(1M/All)을 쓴다
    expect(notice.textContent).toContain('1M')   // period 표시 라벨 (초기)
    expect(notice.textContent).toContain('All')  // market 표시 라벨 (초기)
  })

  it('[순위순으로] 버튼 클릭 시 rank/asc 로 복귀하고 띠가 사라진다', () => {
    renderSectorAnalysis()
    fireEvent.click(screen.getByText('RS Avg'))
    expect(screen.getByTestId('sort-notice')).toBeInTheDocument()
    fireEvent.click(screen.getByText('[순위순으로]'))
    expect(screen.queryByTestId('sort-notice')).not.toBeInTheDocument()
  })
})

// AC-SUX-023 (REQ-SUX-021): 정렬 리셋
describe('AC-SUX-023 — period/market 변경 시 정렬 rank/asc 리셋', () => {
  it('rs_avg desc 정렬 상태에서 market 을 바꾸면 rank/asc 로 리셋된다 (띠 소멸)', () => {
    renderSectorAnalysis()
    fireEvent.click(screen.getByText('RS Avg'))
    expect(screen.getByTestId('sort-notice')).toBeInTheDocument()
    // market 토글 KOSPI 클릭
    fireEvent.click(screen.getByText('KOSPI'))
    expect(screen.queryByTestId('sort-notice')).not.toBeInTheDocument()
  })

  it('rs_avg desc 정렬 상태에서 period 를 바꾸면 rank/asc 로 리셋된다 (띠 소멸)', () => {
    renderSectorAnalysis()
    fireEvent.click(screen.getByText('RS Avg'))
    expect(screen.getByTestId('sort-notice')).toBeInTheDocument()
    // period 토글 3M 클릭
    const periodToggle = screen.getByTestId('period-toggle')
    fireEvent.click(periodToggle.querySelectorAll('button')[2]) // '3m'
    expect(screen.queryByTestId('sort-notice')).not.toBeInTheDocument()
  })
})

// AC-SUX-027 (REQ-SUX-025): RRG/Bump 서브탭에서 기간 토글 비활성 + 툴팁
describe('AC-SUX-027 — RRG/Bump 서브탭 기간 토글 비활성', () => {
  it('Table 서브탭에서는 기간 토글이 활성이다', () => {
    renderSectorAnalysis()
    const periodToggle = screen.getByTestId('period-toggle')
    const buttons = periodToggle.querySelectorAll('button')
    buttons.forEach(b => expect((b as HTMLButtonElement).disabled).toBe(false))
  })

  it('RRG 서브탭으로 전환하면 기간 토글이 disabled 로 여전히 렌더된다 (숨겨지지 않음)', () => {
    renderSectorAnalysis()
    fireEvent.click(screen.getByText('RRG'))
    const periodToggle = screen.getByTestId('period-toggle')
    expect(periodToggle).toBeInTheDocument()
    const buttons = periodToggle.querySelectorAll('button')
    expect(buttons.length).toBeGreaterThan(0)
    buttons.forEach(b => expect((b as HTMLButtonElement).disabled).toBe(true))
  })

  it('Bump 서브탭에서도 기간 토글이 disabled 다', () => {
    renderSectorAnalysis()
    fireEvent.click(screen.getByText('Bump'))
    const periodToggle = screen.getByTestId('period-toggle')
    const buttons = periodToggle.querySelectorAll('button')
    buttons.forEach(b => expect((b as HTMLButtonElement).disabled).toBe(true))
  })

  it('비활성 시 툴팁(자체 시간 파라미터 설명)이 title 에 포함된다', () => {
    renderSectorAnalysis()
    fireEvent.click(screen.getByText('RRG'))
    const periodToggle = screen.getByTestId('period-toggle')
    expect(periodToggle.getAttribute('title') ?? '').toMatch(/시간 파라미터|weeks|lookback/)
  })

  it('Table 로 돌아오면 다시 활성화된다', () => {
    renderSectorAnalysis()
    fireEvent.click(screen.getByText('RRG'))
    fireEvent.click(screen.getByText('Table'))
    const periodToggle = screen.getByTestId('period-toggle')
    const buttons = periodToggle.querySelectorAll('button')
    buttons.forEach(b => expect((b as HTMLButtonElement).disabled).toBe(false))
  })
})

// AC-SUX-019 / 025 컨테이너 통합 (② 봉투 필드가 SectorRankingTable 로 전달되는지)
describe('AC-SUX-019/025 컨테이너 — 봉투 필드 전달', () => {
  it('excluded 가 표 하단 제외 영역으로 렌더된다 (봉투 → 테이블 전달)', () => {
    renderSectorAnalysis()
    expect(screen.getByTestId('excluded-sectors')).toBeInTheDocument()
    expect(screen.getByText('디스플레이')).toBeInTheDocument()
  })

  it('baseline_date 가 Rank 열 헤더에 렌더된다 (봉투 → 테이블 전달)', () => {
    renderSectorAnalysis()
    expect(screen.getByText(/2026-08-01/)).toBeInTheDocument()
  })
})
