// SPEC-RS-REBALANCE-001 M5 — AC-RSR-011: 종목 테이블 열기 배지 (DOM 검사)
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { Stage2Candidate } from '../../../types/stage'
import { StockTable } from '../StockTable'
import { RS_TOP_THRESHOLD } from '../../../utils/rsMetrics'

function makeCandidate(code: string, name: string, rs_1m: number | null): Stage2Candidate {
  return {
    code,
    name,
    market: 'KOSPI',
    sector_major: 'IT',
    sector_minor: '반도체',
    stage: 2,
    stage_detail: 'Stage 2',
    rs_12m: 50,
    chg_1m: 1,
    volume_ratio: 1,
    close: 100,
    sma50: 90,
    sma200: 80,
    rs_1m,
  }
}

const HEAT_CASES: Array<[string, string, number | null]> = [
  ['000001', '종목A', 79.99],
  ['000002', '종목B', 80],
  ['000003', '종목C', 80.01],
  ['000004', '종목D', null],
]

function renderTable() {
  render(
    <StockTable
      candidates={HEAT_CASES.map(([c, n, v]) => makeCandidate(c, n, v))}
      stageFilter={null}
      sectorFilter={null}
      onStockSelect={vi.fn()}
      selectedStocks={new Set()}
    />,
  )
}

function badgeOf(name: string): HTMLElement | null {
  const row = screen.getByText(name).closest('tr') as HTMLTableRowElement
  return row.querySelector('[data-testid="rs-heat-badge"]')
}

describe('StockTable — 열기 배지 (AC-RSR-011)', () => {
  it('rs_1m 80, 80.01 만 배지를 갖고 79.99, null 은 갖지 않는다', () => {
    renderTable()
    expect(badgeOf('종목A')).toBeNull()
    expect(badgeOf('종목B')).not.toBeNull()
    expect(badgeOf('종목C')).not.toBeNull()
    expect(badgeOf('종목D')).toBeNull()
  })

  it('배지 title 에 RS_TOP_THRESHOLD 값이 문자열로 들어 있다', () => {
    renderTable()
    const title = badgeOf('종목B')?.getAttribute('title') ?? ''
    expect(title).toContain(String(RS_TOP_THRESHOLD))
  })
})
