// SPEC-RS-REBALANCE-001 M5 — AC-RSR-012 (REQ-RSR-017): 섹터 테이블 중앙값·breadth 병기.
// 픽스처는 AC-RSR-010 의 P, Q: 평균은 둘 다 50 이지만 중앙값은 30 / 50 으로 갈린다.
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { SectorRankItem } from '../../../types/market'
import { SectorRankingTable } from '../SectorRankingTable'

function sector(name: string, rs_med: number, rs_top_pct: number, rank: number): SectorRankItem {
  return {
    name,
    stock_count: 5,
    returns: { w1: 0, m1: 0, m3: 0 },
    excess_returns: { w1: 0, m1: 0, m3: 0 },
    rs_avg: 50,
    rs_med,
    rs_top_pct,
    nh_pct: 0,
    stage2_pct: 0,
    composite_score: 0,
    rank,
    rank_change: 0,
  }
}

const P = sector('섹터P', 30, 40, 1)
const Q = sector('섹터Q', 50, 0, 2)

function renderTable(sectors: SectorRankItem[] = [P, Q]) {
  render(
    <SectorRankingTable
      sectors={sectors}
      sortField="rank"
      sortDirection="asc"
      onSort={vi.fn()}
      onSectorClick={vi.fn()}
      selectedSector={null}
    />,
  )
}

function headerLabels(): string[] {
  return Array.from(document.querySelectorAll('thead th')).map(
    (th) => th.querySelector('span')?.textContent ?? '',
  )
}

function cellText(name: string, col: number): string | null {
  return (screen.getByText(name).closest('tr') as HTMLTableRowElement).querySelectorAll('td')[col].textContent
}

describe('SectorRankingTable — rs_med 열 (AC-RSR-012)', () => {
  it('헤더에 RS Avg, 중앙값 열, RS 80+ 비중이 인접 순서로 있다', () => {
    renderTable()
    const labels = headerLabels()
    const i = labels.indexOf('RS Avg')
    expect(i).toBeGreaterThanOrEqual(0)
    expect(labels[i + 1]).toBe('RS Med')
    expect(labels[i + 2]).toBe('RS 80+ 비중')
  })

  it('P 행 중앙값 셀은 30, Q 행은 50 을 표시한다 (rs_avg 50 과 구분)', () => {
    renderTable()
    const col = headerLabels().indexOf('RS Med')
    expect(cellText('섹터P', col)).toBe('30')
    expect(cellText('섹터Q', col)).toBe('50')
  })

  it('rs_med 결측이면 0 이 아닌 결측 표기를 한다', () => {
    renderTable([{ ...P, rs_med: null }])
    const col = headerLabels().indexOf('RS Med')
    const text = cellText('섹터P', col)
    expect(text).not.toBe('0')
    expect(text).not.toBe('')
  })
})
