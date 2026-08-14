// AC-SUX-017 (TR-7/TR-8) — SectorAnalysis keep-mounted: RRG/Bump 로컬 state 가 탭 전환에 보존된다.
// M3/M4 deferred debt 해소 (M5). 마운트 카운터로 "재방문 시 remount 아님" 을 실증.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { ReactElement } from 'react'

const mockMarketState = {
  sectorRanking: {
    date: '2026-08-11',
    sectors: [
      { name: '반도체', stock_count: 30, returns: { w1: 1, m1: 2, m3: 3 }, excess_returns: { w1: 0.5, m1: 1, m3: 2 }, rs_avg: 70, rs_top_pct: 25, nh_pct: 15, stage2_pct: 35, composite_score: 80, rank: 1, rank_change: 2 },
      { name: '은행', stock_count: 20, returns: { w1: -1, m1: -2, m3: 1 }, excess_returns: { w1: -0.5, m1: -1, m3: 0.5 }, rs_avg: 45, rs_top_pct: 10, nh_pct: 5, stage2_pct: 15, composite_score: 40, rank: 2, rank_change: -1 },
    ],
    excluded: [], baseline_date: '2026-08-01', as_of_date: '2026-08-11',
  },
  overview: null, loading: false, error: null, refresh: vi.fn(),
}
vi.mock('../../../contexts/MarketContext', () => ({ useMarket: () => mockMarketState }))
vi.mock('../../../contexts/TabContext', () => ({ useNavIntent: () => ({ navigate: vi.fn(), intent: null }) }))

// 자식 차트를 마운트 카운터 목으로 교체 — 재방문 시 remount(카운트 증가) 되는지 검증.
// 빈 deps useEffect 로 "마운트"만 카운트 (재렌더는 카운트하지 않음).
import { useEffect } from 'react'
let rrgMounts = 0
let bumpMounts = 0
let bubbleMounts = 0
vi.mock('../RRGChart', () => ({
  RRGChart: () => { useEffect(() => { rrgMounts++ }, []); return null as unknown as ReactElement },
}))
vi.mock('../BumpChart', () => ({
  BumpChart: () => { useEffect(() => { bumpMounts++ }, []); return null as unknown as ReactElement },
}))
vi.mock('../BubbleChart', () => ({
  BubbleChart: () => { useEffect(() => { bubbleMounts++ }, []); return null as unknown as ReactElement },
}))

import { SectorAnalysis } from '../SectorAnalysis'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { SelectionProvider } from '../../../contexts/SelectionContext'

function renderSA() {
  return render(
    <AnalysisParamsProvider><SelectionProvider><SectorAnalysis /></SelectionProvider></AnalysisParamsProvider>,
  )
}

beforeEach(() => { rrgMounts = 0; bumpMounts = 0; bubbleMounts = 0; vi.clearAllMocks() })

describe('AC-SUX-017 — keep-mounted: RRG/Bump 로컬 state 가 탭 왕복에 보존된다', () => {
  it('RRG 방문 → table → RRG 재방문 시 RRG 가 remount 되지 않는다 (마운트 1회)', () => {
    renderSA()
    // 최초: table 만 마운트 (RRG/Bump/Bubble 미방문 → 미마운트 = AC-SUX-033 lazy)
    expect(rrgMounts).toBe(0)
    expect(bumpMounts).toBe(0)
    // RRG 방문
    fireEvent.click(screen.getByRole('button', { name: 'RRG' }))
    expect(rrgMounts).toBe(1)
    // table 로 전환 (RRG 는 display:none, 언마운트 아님)
    fireEvent.click(screen.getByRole('button', { name: 'Table' }))
    expect(rrgMounts).toBe(1)
    // RRG 재방문 — remount 없이 동일 인스턴스 (visibleSectors/windowEnd 보존)
    fireEvent.click(screen.getByRole('button', { name: 'RRG' }))
    expect(rrgMounts).toBe(1)
  })

  it('Bump 방문 → table → Bump 재방문 시 마운트 1회 (topFilter 보존)', () => {
    renderSA()
    fireEvent.click(screen.getByRole('button', { name: 'Bump' }))
    expect(bumpMounts).toBe(1)
    fireEvent.click(screen.getByRole('button', { name: 'Table' }))
    fireEvent.click(screen.getByRole('button', { name: 'Bump' }))
    expect(bumpMounts).toBe(1)
  })

  it('Bubble 방문 → table → Bubble 재방문 시 마운트 1회', () => {
    renderSA()
    fireEvent.click(screen.getByRole('button', { name: 'Bubble' }))
    expect(bubbleMounts).toBe(1)
    fireEvent.click(screen.getByRole('button', { name: 'Table' }))
    fireEvent.click(screen.getByRole('button', { name: 'Bubble' }))
    expect(bubbleMounts).toBe(1)
  })

  it('미방문 탭은 마운트되지 않는다 (AC-SUX-033 lazy 와 양립)', () => {
    renderSA()
    // table 기본 — RRG/Bump/Bubble 전부 미방문
    expect(rrgMounts).toBe(0)
    expect(bumpMounts).toBe(0)
    expect(bubbleMounts).toBe(0)
  })
})
