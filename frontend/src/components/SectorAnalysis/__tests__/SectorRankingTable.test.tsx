// RED: Specification tests for SectorRankingTable component
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { SectorRankItem } from '../../../types/market'

// Import the component under test (does not exist yet — RED phase)
import { SectorRankingTable } from '../SectorRankingTable'

const mockSectors: SectorRankItem[] = [
  {
    name: 'Technology',
    stock_count: 50,
    returns: { w1: 2.5, m1: 5.0, m3: 10.0 },
    excess_returns: { w1: 1.0, m1: 2.0, m3: 4.0 },
    rs_avg: 75,
    rs_top_pct: 30,
    nh_pct: 20,
    stage2_pct: 40,
    composite_score: 80,
    rank: 1,
    rank_change: 2,
  },
  {
    name: 'Finance',
    stock_count: 30,
    returns: { w1: -1.0, m1: -2.0, m3: 1.0 },
    excess_returns: { w1: -0.5, m1: -1.0, m3: 0.5 },
    rs_avg: 45,
    rs_top_pct: 10,
    nh_pct: 5,
    stage2_pct: 15,
    composite_score: 40,
    rank: 2,
    rank_change: -1,
  },
  {
    name: 'Healthcare',
    stock_count: 20,
    returns: { w1: 0.5, m1: 1.0, m3: 2.0 },
    excess_returns: { w1: 0.0, m1: 0.0, m3: 0.0 },
    rs_avg: 55,
    rs_top_pct: 20,
    nh_pct: 10,
    stage2_pct: 25,
    composite_score: 55,
    rank: 3,
    rank_change: 0,
  },
]

const defaultProps = {
  sectors: mockSectors,
  sortField: 'rank',
  sortDirection: 'asc' as const,
  onSort: vi.fn(),
  onSectorClick: vi.fn(),
  selectedSector: null,
}

describe('SectorRankingTable — column headers', () => {
  it('renders all required column headers', () => {
    render(<SectorRankingTable {...defaultProps} />)
    expect(screen.getByText('Rank')).toBeInTheDocument()
    expect(screen.getByText('Sector')).toBeInTheDocument()
    expect(screen.getByText('1W')).toBeInTheDocument()
    expect(screen.getByText('1M')).toBeInTheDocument()
    expect(screen.getByText('3M')).toBeInTheDocument()
    expect(screen.getByText('RS Avg')).toBeInTheDocument()
    expect(screen.getByText('RS Top %')).toBeInTheDocument()
    expect(screen.getByText('52W High %')).toBeInTheDocument()
    expect(screen.getByText('Stage 2 %')).toBeInTheDocument()
  })
})

describe('SectorRankingTable — sector data rows', () => {
  it('renders all sector names', () => {
    render(<SectorRankingTable {...defaultProps} />)
    expect(screen.getByText('Technology')).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('Healthcare')).toBeInTheDocument()
  })

  it('renders rank numbers', () => {
    render(<SectorRankingTable {...defaultProps} />)
    // Rank 1, 2, 3 should appear
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders excess_returns with correct format (+/-N.N%)', () => {
    render(<SectorRankingTable {...defaultProps} />)
    // Technology: excess_returns.m1 = 2.0 → "+2.0%"
    expect(screen.getByText('+2.0%')).toBeInTheDocument()
    // Finance: excess_returns.m1 = -1.0 → "-1.0%"
    expect(screen.getByText('-1.0%')).toBeInTheDocument()
  })

  it('renders RS avg values', () => {
    render(<SectorRankingTable {...defaultProps} />)
    expect(screen.getByText('75')).toBeInTheDocument()
    expect(screen.getByText('45')).toBeInTheDocument()
  })

  it('renders rank_change up arrow for positive change', () => {
    render(<SectorRankingTable {...defaultProps} />)
    // Technology rank_change = 2 → up arrow (▲)
    const upArrows = document.querySelectorAll('.rank-change--up')
    expect(upArrows.length).toBeGreaterThan(0)
  })

  it('renders rank_change down arrow for negative change', () => {
    render(<SectorRankingTable {...defaultProps} />)
    // Finance rank_change = -1 → down arrow (▼)
    const downArrows = document.querySelectorAll('.rank-change--down')
    expect(downArrows.length).toBeGreaterThan(0)
  })

  it('renders flat indicator for zero rank_change', () => {
    render(<SectorRankingTable {...defaultProps} />)
    // Healthcare rank_change = 0 → flat (-)
    const flatArrows = document.querySelectorAll('.rank-change--flat')
    expect(flatArrows.length).toBeGreaterThan(0)
  })
})

describe('SectorRankingTable — sorting interaction', () => {
  it('calls onSort with field name when column header is clicked', async () => {
    const onSort = vi.fn()
    const user = userEvent.setup()
    render(<SectorRankingTable {...defaultProps} onSort={onSort} />)
    await user.click(screen.getByText('RS Avg'))
    expect(onSort).toHaveBeenCalledWith('rs_avg')
  })

  it('calls onSort with "rank" when Rank header is clicked', async () => {
    const onSort = vi.fn()
    const user = userEvent.setup()
    render(<SectorRankingTable {...defaultProps} onSort={onSort} />)
    await user.click(screen.getByText('Rank'))
    expect(onSort).toHaveBeenCalledWith('rank')
  })

  it('shows sort arrow on active sort column', () => {
    render(<SectorRankingTable {...defaultProps} sortField="rs_avg" sortDirection="desc" />)
    // Active sort column should show sort indicator
    const sortArrows = document.querySelectorAll('.sort-arrow')
    expect(sortArrows.length).toBeGreaterThan(0)
  })
})

describe('SectorRankingTable — row selection', () => {
  it('calls onSectorClick when row is clicked', async () => {
    const onSectorClick = vi.fn()
    const user = userEvent.setup()
    render(<SectorRankingTable {...defaultProps} onSectorClick={onSectorClick} />)
    await user.click(screen.getByText('Technology'))
    expect(onSectorClick).toHaveBeenCalledWith('Technology')
  })

  it('applies selected class to selected sector row', () => {
    render(<SectorRankingTable {...defaultProps} selectedSector="Technology" />)
    // The selected row should have 'selected' class
    const selectedRows = document.querySelectorAll('tr.selected')
    expect(selectedRows.length).toBe(1)
  })

  it('does not apply selected class to non-selected rows', () => {
    render(<SectorRankingTable {...defaultProps} selectedSector="Technology" />)
    const selectedRows = document.querySelectorAll('tr.selected')
    // Only 1 row selected out of 3
    expect(selectedRows.length).toBe(1)
  })
})
