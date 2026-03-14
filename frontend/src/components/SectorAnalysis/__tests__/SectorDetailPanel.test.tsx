// RED: Specification tests for SectorDetailPanel component
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { SectorRankItem } from '../../../types/market'

// Import the component under test (does not exist yet — RED phase)
import { SectorDetailPanel } from '../SectorDetailPanel'

const mockSector: SectorRankItem = {
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
}

describe('SectorDetailPanel — rendering', () => {
  it('renders sector name as title', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('Technology')).toBeInTheDocument()
  })

  it('renders the panel container with correct class', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(document.querySelector('.sector-detail-panel')).toBeInTheDocument()
  })

  it('renders RS Avg metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('RS Avg')).toBeInTheDocument()
    expect(screen.getByText('75')).toBeInTheDocument()
  })

  it('renders RS Top % metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('RS Top %')).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
  })

  it('renders 52W High % metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('52W High %')).toBeInTheDocument()
    expect(screen.getByText('20%')).toBeInTheDocument()
  })

  it('renders Stage 2 % metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('Stage 2 %')).toBeInTheDocument()
    expect(screen.getByText('40%')).toBeInTheDocument()
  })

  it('renders Composite Score metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('Composite Score')).toBeInTheDocument()
    expect(screen.getByText('80')).toBeInTheDocument()
  })

  it('renders sub-sector placeholder text', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText(/sub-sector/i)).toBeInTheDocument()
  })

  it('renders returns section with 1W, 1M, 3M labels', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    // Returns section should display at least the period labels
    expect(screen.getByText('1W')).toBeInTheDocument()
    expect(screen.getByText('1M')).toBeInTheDocument()
    expect(screen.getByText('3M')).toBeInTheDocument()
  })
})
