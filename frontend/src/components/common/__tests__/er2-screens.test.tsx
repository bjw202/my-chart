// RED: AC-SUX-053 (ER-2) — null 섞인 픽스처를 전 화면에 넣어도 NaN / 0.0% / 50.0 대체가 없다.
//      AC-SUX-052 마지막 절 — 같은 결측 상태가 화면들에서 같은 텍스트·같은 class 로 렌더된다.
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import type { SectorRankItem } from '../../../types/market'
import type { Stage2Candidate } from '../../../types/stage'
import { SectorRankingTable } from '../../SectorAnalysis/SectorRankingTable'
import { StockTable } from '../../StockExplorer/StockTable'

afterEach(() => cleanup())

// null 이 잔뜩 섞인 섹터 — 응답 결측을 그대로 반영한 픽스처
function nullSector(name: string): SectorRankItem {
  return {
    name,
    stock_count: 3,
    returns: { w1: 0, m1: 0, m3: 0 },
    // 의도적으로 null 주입 — 백엔드가 결측을 내리는 실제 상황
    excess_returns: { w1: null, m1: 0, m3: null } as unknown as SectorRankItem['excess_returns'],
    rs_avg: null as unknown as number,
    rs_top_pct: null as unknown as number,
    nh_pct: null as unknown as number,
    stage2_pct: null as unknown as number,
    composite_score: null as unknown as number,
    rank: 1,
    rank_change: 0,
  }
}

function nullStock(over: Partial<Stage2Candidate>): Stage2Candidate {
  return {
    code: '000001',
    name: 'N주',
    market: 'KOSPI',
    sector_major: '반도체',
    sector_minor: '반도체장비',
    stage: 2,
    stage_detail: 'stage2',
    rs_12m: null as unknown as number,
    chg_1m: null as unknown as number,
    volume_ratio: null as unknown as number,
    close: 1000,
    sma50: 900,
    sma200: 800,
    chg_1w: null,
    chg_3m: null,
    weight_in_sector: null,
    near_52w_high: null,
    ...over,
  }
}

const tableProps = {
  sortField: 'rank',
  sortDirection: 'asc' as const,
  onSort: vi.fn(),
  onSectorClick: vi.fn(),
  selectedSector: null,
}

const stockProps = {
  stageFilter: null,
  sectorFilter: null,
  onStockSelect: vi.fn(),
  onSelectAll: vi.fn(),
  selectedStocks: new Set<string>(),
  collapseLevel: 0,
}

describe('AC-SUX-053 — 순위표: null 픽스처에서 NaN / 0.0% / 50.0 대체 없음', () => {
  it('런타임 예외 없이 렌더되고 DOM 텍스트에 "NaN" 이 0건이다', () => {
    expect(() =>
      render(<SectorRankingTable {...tableProps} sectors={[nullSector('A')]} />),
    ).not.toThrow()
    const text = document.body.textContent ?? ''
    expect(text).not.toContain('NaN')
  })

  it('결측 셀은 "–" 이고, 실제 0 인 셀만 "0.0%" 로 렌더된다 — 둘이 섞이지 않는다', () => {
    render(<SectorRankingTable {...tableProps} sectors={[nullSector('A')]} />)
    const cells = screen.getAllByTestId('metric-cell')
    const missing = cells.filter(c => c.getAttribute('data-state') === 'missing')
    const ok = cells.filter(c => c.getAttribute('data-state') === 'ok')
    // excess w1/m3 + rs_avg + rs_top + nh + stage2 + composite = 7 결측
    expect(missing.length).toBe(7)
    expect(missing.every(c => c.textContent === '–')).toBe(true)
    // excess m1 = 0 → 실제 0 이므로 0.0% 로 렌더 (결측이 아님)
    expect(ok.map(c => c.textContent)).toEqual(['0.0%'])
  })

  it('결측 자리에 RS 중립값 50.0 이 대체되지 않는다', () => {
    render(<SectorRankingTable {...tableProps} sectors={[nullSector('A')]} />)
    expect(document.body.textContent ?? '').not.toContain('50.0')
  })
})

describe('AC-SUX-053 — 종목 표: null 픽스처에서 NaN / 대체값 없음', () => {
  it('런타임 예외 없이 렌더되고 "NaN" 이 0건이다', () => {
    expect(() =>
      render(<StockTable {...stockProps} candidates={[nullStock({})]} />),
    ).not.toThrow()
    expect(document.body.textContent ?? '').not.toContain('NaN')
  })

  it('rs_12m·chg_1m·chg_1w·chg_3m·volume_ratio·섹터비중 결측이 전부 "–" 다', () => {
    render(<StockTable {...stockProps} candidates={[nullStock({})]} />)
    const missing = screen.getAllByTestId('metric-cell')
      .filter(c => c.getAttribute('data-state') === 'missing')
    expect(missing.length).toBe(6)
    expect(new Set(missing.map(c => c.textContent))).toEqual(new Set(['–']))
  })

  it('chg_1m 이 0 이면 결측이 아니라 "0.00%" 로 렌더된다', () => {
    render(<StockTable {...stockProps} candidates={[nullStock({ chg_1m: 0 })]} />)
    const ok = screen.getAllByTestId('metric-cell')
      .filter(c => c.getAttribute('data-state') === 'ok')
    expect(ok.map(c => c.textContent)).toContain('0.00%')
  })
})

describe('AC-SUX-052 — 화면 간 결측 표기 동일성 (공용 컴포넌트 단언)', () => {
  it('순위표와 종목 표의 결측 셀이 같은 텍스트·같은 class 를 낸다', () => {
    const { unmount } = render(<SectorRankingTable {...tableProps} sectors={[nullSector('A')]} />)
    const fromRanking = screen.getAllByTestId('metric-cell')
      .find(c => c.getAttribute('data-state') === 'missing')!
    const rankingText = fromRanking.textContent
    const rankingClass = fromRanking.className
    unmount()

    render(<StockTable {...stockProps} candidates={[nullStock({})]} />)
    const fromStock = screen.getAllByTestId('metric-cell')
      .find(c => c.getAttribute('data-state') === 'missing')!

    expect(fromStock.textContent).toBe(rankingText)
    expect(fromStock.className).toBe(rankingClass)
  })
})
