// AC-SUX-031 / 061 / 030 — StockTable M4 행동 단언 (SPEC-SECTOR-UX-001 M4).
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { Stage2Candidate } from '../../../types/stage'
import { StockTable } from '../StockTable'

function makeCandidate(over: Partial<Stage2Candidate> = {}): Stage2Candidate {
  return {
    code: '005930',
    name: '삼성전자',
    market: 'KOSPI',
    sector_major: 'IT',
    sector_minor: '반도체',
    stage: 2,
    stage_detail: 'Stage 2 Strong',
    rs_12m: 75.5,
    chg_1m: 3.2,
    volume_ratio: 1.5,
    close: 75000,
    sma50: 72000,
    sma200: 68000,
    ...over,
  }
}

// AC-SUX-031 (REQ-SUX-029/030): 종목 표 신규 열 상설
describe('AC-SUX-031 — 종목 표 신규 열 (1W/1M/3M/섹터비중) 상설 렌더', () => {
  it('1W% / 1M% / 3M% / 섹터비중 4개 열 헤더가 렌더된다', () => {
    render(
      <StockTable
        candidates={[makeCandidate()]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />,
    )
    expect(screen.getByText('1W%')).toBeInTheDocument()
    expect(screen.getByText('1M%')).toBeInTheDocument()
    expect(screen.getByText('3M%')).toBeInTheDocument()
    expect(screen.getByText('섹터비중')).toBeInTheDocument()
  })

  it('weight_capped:true 인 종목의 섹터비중 셀에 ⊤ 마커가 붙는다', () => {
    const { container } = render(
      <StockTable
        candidates={[makeCandidate({ weight_in_sector: 0.1, weight_capped: true })]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />,
    )
    expect(container.querySelector('.weight-cap-marker')).toBeTruthy()
    expect(container.querySelector('.weight-cap-marker')?.textContent).toBe('⊤')
  })

  it('weight_capped 가 없으면 ⊤ 마커가 렌더되지 않는다', () => {
    const { container } = render(
      <StockTable
        candidates={[makeCandidate({ weight_in_sector: 0.05 })]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />,
    )
    expect(container.querySelector('.weight-cap-marker')).toBeFalsy()
  })
})

// AC-SUX-061 (REQ-SUX-058): 좁은 화면 열 접기 우선순위
describe('AC-SUX-061 — 열 접기 순서 + 불변 열', () => {
  it('collapseLevel 1 에서 섹터비중 열만 숨겨진다', () => {
    render(
      <StockTable
        candidates={[makeCandidate()]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
        collapseLevel={1}
      />,
    )
    expect(document.querySelector('[data-col-key="weight_in_sector"]')?.getAttribute('data-collapsed')).toBe('true')
    expect(document.querySelector('[data-col-key="volume_ratio"]')?.getAttribute('data-collapsed')).toBeFalsy()
    expect(document.querySelector('[data-col-key="near_52w_high"]')?.getAttribute('data-collapsed')).toBeFalsy()
  })

  it('collapseLevel 2 에서 섹터비중 + Vol배 가 숨겨진다', () => {
    render(
      <StockTable
        candidates={[makeCandidate()]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
        collapseLevel={2}
      />,
    )
    expect(document.querySelector('[data-col-key="weight_in_sector"]')?.getAttribute('data-collapsed')).toBe('true')
    expect(document.querySelector('[data-col-key="volume_ratio"]')?.getAttribute('data-collapsed')).toBe('true')
    expect(document.querySelector('[data-col-key="near_52w_high"]')?.getAttribute('data-collapsed')).toBeFalsy()
  })

  it('collapseLevel 3 에서 세 접기 대상 열이 모두 숨겨지고 가로 스크롤 표시가 켜진다', () => {
    const { container } = render(
      <StockTable
        candidates={[makeCandidate()]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
        collapseLevel={3}
      />,
    )
    expect(document.querySelector('[data-col-key="weight_in_sector"]')?.getAttribute('data-collapsed')).toBe('true')
    expect(document.querySelector('[data-col-key="volume_ratio"]')?.getAttribute('data-collapsed')).toBe('true')
    expect(document.querySelector('[data-col-key="near_52w_high"]')?.getAttribute('data-collapsed')).toBe('true')
    expect(container.querySelector('.stock-table-wrapper')?.getAttribute('data-overflow-scroll')).toBe('true')
  })

  it('불변 열(1W%/1M%/3M%/Stage/RS/Name) 은 어떤 collapseLevel 에서도 숨겨지지 않는다', () => {
    const invariantKeys = ['name', 'stage', 'rs_12m', 'chg_1w', 'chg_1m', 'chg_3m']
    for (const level of [0, 1, 2, 3]) {
      const { unmount } = render(
        <StockTable
          candidates={[makeCandidate()]}
          stageFilter={null}
          sectorFilter={null}
          onStockSelect={vi.fn()}
          selectedStocks={new Set()}
          collapseLevel={level}
        />,
      )
      for (const key of invariantKeys) {
        const el = document.querySelector(`[data-col-key="${key}"]`)
        expect(el?.getAttribute('data-collapsed')).toBeFalsy()
      }
      unmount()
    }
  })

  it('collapseLevel 0 (기본) 에서는 모든 열이 표시된다 (AC-SUX-032 default 진입 가시성)', () => {
    render(
      <StockTable
        candidates={[makeCandidate()]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />,
    )
    expect(document.querySelector('.stock-table-wrapper')?.getAttribute('data-collapse-level')).toBe('0')
    expect(document.querySelectorAll('[data-collapsed="true"]').length).toBe(0)
  })
})

// AC-SUX-030 (REQ-SUX-028): 미분류 세그먼트 클릭 → stageFilter 'unclassified' → 분류 불가 종목만
describe('AC-SUX-030 — stageFilter unclassified 처리 (StockTable)', () => {
  it("stageFilter='unclassified' 이면 stage 가 1~4 범위 밖인 종목만 렌더한다", () => {
    const candidates = [
      makeCandidate({ code: 'A', name: '정상1', stage: 2 }),
      makeCandidate({ code: 'B', name: '정상2', stage: 1 }),
      makeCandidate({ code: 'C', name: '미분류', stage: 0 }),
    ]
    render(
      <StockTable
        candidates={candidates}
        stageFilter="unclassified"
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />,
    )
    expect(screen.queryByText('정상1')).not.toBeInTheDocument()
    expect(screen.queryByText('정상2')).not.toBeInTheDocument()
    expect(screen.getByText('미분류')).toBeInTheDocument()
  })
})
