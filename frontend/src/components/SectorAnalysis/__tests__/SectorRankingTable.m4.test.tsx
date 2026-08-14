// AC-SUX-019 / 021 / 025 / 026 / 058 — SectorRankingTable M4 행동 단언 (SPEC-SECTOR-UX-001 M4).
import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import type { SectorRankItem, ExcludedSector } from '../../../types/market'
import { SectorRankingTable } from '../SectorRankingTable'

function makeSector(over: Partial<SectorRankItem>): SectorRankItem {
  return {
    name: 'X',
    stock_count: 10,
    returns: { w1: 0, m1: 0, m3: 0 },
    excess_returns: { w1: 0, m1: 0, m3: 0 },
    rs_avg: 50,
    rs_top_pct: 20,
    nh_pct: 10,
    stage2_pct: 30,
    composite_score: 60,
    rank: 1,
    rank_change: 0,
    ...over,
  }
}

const baseProps = {
  sortField: 'rank',
  sortDirection: 'asc' as const,
  onSort: vi.fn(),
  onSectorClick: vi.fn(),
  selectedSector: null,
}

// AC-SUX-058 (REQ-SUX-055): 순위 총수 병기 7 / 27
describe('AC-SUX-058 — rank total 병기 (분모 = rank !== null 개수)', () => {
  it('rank 셀이 {rank} / {총수} 형태로 렌더된다', () => {
    const sectors = [
      makeSector({ name: 'A', rank: 7, rank_change: 0 }),
      makeSector({ name: 'B', rank: 1, rank_change: 0 }),
      makeSector({ name: 'C', rank: 27, rank_change: 0 }),
    ]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    const rankCells = screen.getAllByTestId('rank-value')
    expect(rankCells.map(c => c.textContent)).toEqual(['7', '1', '27'])
    // 분모는 모든 행에서 동일 — 3개 (rank !== null 인 섹터 수)
    const totals = document.querySelectorAll('.rank-total')
    expect(totals.length).toBe(3)
    expect(totals[0].textContent).toBe(' / 3')
  })

  it('29 같은 상수로 하드코딩하지 않는다 — 시장 필터로 섹터가 줄면 분모도 준다', () => {
    // kospi 필터로 1개만 남은 픽스처
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    expect(screen.getAllByTestId('rank-value')[0].textContent).toBe('1')
    expect(document.querySelectorAll('.rank-total')[0].textContent).toBe(' / 1')
  })
})

// AC-SUX-021 (REQ-SUX-019): Rank 열은 응답 rank 값을 그대로 표시 — 재계산 금지
describe('AC-SUX-021 — rank 열이 응답 값을 그대로 반영 (재계산 금지)', () => {
  it('rank 가 불연속·비정렬 [3,1,2] 인 픽스처에서 행 순서대로 3,1,2 가 표시된다', () => {
    // 클라이언트가 재계산했다면 1,2,3 이 되어 실패한다.
    const sectors = [
      makeSector({ name: 'Alpha', rank: 3, rank_change: 0 }),
      makeSector({ name: 'Bravo', rank: 1, rank_change: 0 }),
      makeSector({ name: 'Charlie', rank: 2, rank_change: 0 }),
    ]
    // 이름 정렬 상태로 행 순서 = Alpha,Bravo,Charlie (배열 순서 보존)
    render(
      <SectorRankingTable
        {...baseProps}
        sectors={sectors}
        sortField="name"
        sortDirection="asc"
      />,
    )
    const rankCells = screen.getAllByTestId('rank-value')
    expect(rankCells.map(c => c.textContent)).toEqual(['3', '1', '2'])
  })
})

// AC-SUX-025 (REQ-SUX-023): 순위변동 4상태 + 기준일 헤더
describe('AC-SUX-025 — rank_change 4상태 + baseline_date 헤더', () => {
  it('rank_change 가 3/-2/0/null 일 때 각각 ▲3 / ▼2 / – / 신규 로 렌더된다', () => {
    const sectors = [
      makeSector({ name: 'Up', rank: 1, rank_change: 3 }),
      makeSector({ name: 'Down', rank: 2, rank_change: -2 }),
      makeSector({ name: 'Flat', rank: 3, rank_change: 0 }),
      makeSector({ name: 'New', rank: 4, rank_change: null }),
    ]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    expect(screen.getByText('▲3')).toBeInTheDocument()
    expect(screen.getByText('▼2')).toBeInTheDocument()
    expect(screen.getByText('–')).toBeInTheDocument()
    expect(screen.getByText('신규')).toBeInTheDocument()
  })

  it('0(유지) 과 null(신규) 이 서로 다른 텍스트/클래스로 구분된다', () => {
    const sectors = [
      makeSector({ name: 'Flat', rank: 1, rank_change: 0 }),
      makeSector({ name: 'New', rank: 2, rank_change: null }),
    ]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    expect(document.querySelectorAll('.rank-change--flat').length).toBe(1)
    expect(document.querySelectorAll('.rank-change--new').length).toBe(1)
    // 신규에 툴팁이 붙는다
    const newEl = document.querySelector('.rank-change--new')
    expect(newEl?.getAttribute('title')).toBeTruthy()
  })

  it('baseline_date 가 Rank 열 헤더에 표기된다', () => {
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    render(
      <SectorRankingTable
        {...baseProps}
        sectors={sectors}
        baselineDate="2026-07-25"
      />,
    )
    // 헤더 텍스트에 응답의 baseline_date 문자열이 포함된다
    expect(screen.getByText(/2026-07-25/)).toBeInTheDocument()
  })

  it('baseline_date 가 없으면 기준일 표기가 렌더되지 않는다', () => {
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    expect(document.querySelectorAll('.rank-baseline-date').length).toBe(0)
  })
})

// AC-SUX-026 (REQ-SUX-024): 가중 방식 배지
describe('AC-SUX-026 — 가중 방식 배지 (본문 상설)', () => {
  it('초과수익률 3열(1W/1M/3M) 헤더에 ⓦ, RS/신고가/Stage 계열 헤더에 ⓔ 가 텍스트로 상설 렌더된다', () => {
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    // 헤더 영역(thead) 의 배지만 집계 — 하단 범례의 배지와 구분.
    const badges = Array.from(document.querySelectorAll('thead .weight-badge'))
    const glyphs = badges.map(b => b.textContent)
    // ⓦ 3개 (1W/1M/3M) + ⓔ 4개 (RS Avg/RS Top%/52W High%/Stage 2%)
    expect(glyphs.filter(g => g === 'ⓦ').length).toBe(3)
    expect(glyphs.filter(g => g === 'ⓔ').length).toBe(4)
  })

  it('표 하단에 가중 방식 범례 한 줄이 렌더된다', () => {
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    const legend = document.querySelector('.weight-badge-legend')
    expect(legend).toBeTruthy()
    expect(legend?.textContent).toContain('시총가중')
    expect(legend?.textContent).toContain('등가중')
  })
})

// AC-SUX-019 (REQ-SUX-017): 제외 섹터 가시성 (Table 범위)
describe('AC-SUX-019 — 순위 대상 제외 영역 (Table)', () => {
  it('excluded 가 있으면 표 하단에 순위 대상 제외 (N) 영역이 렌더되고 각 항목에 섹터명/사유/종목수가 표시된다', () => {
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    const excluded: ExcludedSector[] = [
      { sector: '디스플레이', reason: 'insufficient_members', count: 4 },
      { sector: '스마트폰', reason: 'insufficient_members', count: 4 },
    ]
    render(<SectorRankingTable {...baseProps} sectors={sectors} excluded={excluded} />)
    const area = screen.getByTestId('excluded-sectors')
    expect(within(area).getByText(/순위 대상 제외 \(2\)/)).toBeInTheDocument()
    expect(within(area).getByText('디스플레이')).toBeInTheDocument()
    expect(within(area).getByText('스마트폰')).toBeInTheDocument()
    // 사유·종목수는 각 항목마다 1회씩 (2개 항목 → 2회)
    expect(within(area).getAllByText(/insufficient_members/).length).toBe(2)
    expect(within(area).getAllByText(/n=4/).length).toBe(2)
  })

  it('해당 섹터가 sectors[] 에 없어도 제외 영역에 표시되어 화면에서 사라지지 않는다', () => {
    const sectors = [makeSector({ name: '반도체', rank: 1, rank_change: 0 })]
    const excluded: ExcludedSector[] = [
      { sector: '디스플레이', reason: 'insufficient_members', count: 4 },
    ]
    render(<SectorRankingTable {...baseProps} sectors={sectors} excluded={excluded} />)
    // 디스플레이는 sectors[] 에 없지만 제외 영역에 보인다
    expect(screen.getByText('디스플레이')).toBeInTheDocument()
  })

  it('excluded 가 빈 배열이면 제외 영역 자체를 렌더하지 않는다 (E2)', () => {
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    render(<SectorRankingTable {...baseProps} sectors={sectors} excluded={[]} />)
    expect(screen.queryByTestId('excluded-sectors')).not.toBeInTheDocument()
  })

  it('excluded 를 전달하지 않으면 제외 영역을 렌더하지 않는다', () => {
    const sectors = [makeSector({ name: 'A', rank: 1, rank_change: 0 })]
    render(<SectorRankingTable {...baseProps} sectors={sectors} />)
    expect(screen.queryByTestId('excluded-sectors')).not.toBeInTheDocument()
  })
})
