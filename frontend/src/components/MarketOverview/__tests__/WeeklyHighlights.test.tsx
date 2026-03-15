// RED: Specification tests for WeeklyHighlights component
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WeeklyHighlights } from '../WeeklyHighlights'

const sampleSectors = [
  { name: 'Technology', rank_change: 3 },
  { name: 'Healthcare', rank_change: -2 },
  { name: 'Finance', rank_change: 5 },
  { name: 'Energy', rank_change: -1 },
  { name: 'Materials', rank_change: 0 },
]

describe('WeeklyHighlights', () => {
  it('renders market phase section', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    expect(screen.getByText(/market phase/i)).toBeInTheDocument()
  })

  // R7: Stage 2 count display
  it('shows stage 2 count when stage2Count is provided', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} stage2Count={42} />)
    expect(screen.getByText(/42/)).toBeInTheDocument()
    expect(screen.getByText(/stage 2/i)).toBeInTheDocument()
  })

  it('shows placeholder when stage2Count is null', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} stage2Count={null} />)
    // Should show Stage 2 section header but no specific count
    expect(screen.getByText(/stage 2/i)).toBeInTheDocument()
  })

  it('shows stage2Count as 0 correctly', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} stage2Count={0} />)
    expect(screen.getByText(/0/)).toBeInTheDocument()
  })

  it('shows bull phase badge', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    expect(screen.getByText(/bull/i)).toBeInTheDocument()
  })

  it('shows bear phase badge', () => {
    render(<WeeklyHighlights phase="bear" choppy={false} sectors={sampleSectors} />)
    expect(screen.getByText(/bear/i)).toBeInTheDocument()
  })

  it('shows choppy warning when choppy is true', () => {
    render(<WeeklyHighlights phase="sideways" choppy={true} sectors={sampleSectors} />)
    expect(screen.getByText(/choppy/i)).toBeInTheDocument()
  })

  it('does not show choppy warning when choppy is false', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    // "Choppy" warning text should not appear in weekly highlights (phase badge is separate)
    const choppyWarning = screen.queryByText(/⚠|choppy warning/i)
    expect(choppyWarning).not.toBeInTheDocument()
  })

  it('shows biggest rank changes section', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    expect(screen.getByText(/rank change/i)).toBeInTheDocument()
  })

  it('shows top 3 sectors by absolute rank change', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    // Finance (+5), Technology (+3), Healthcare (-2) are top 3 by |rank_change|
    expect(screen.getByText(/Finance/)).toBeInTheDocument()
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
    expect(screen.getByText(/Healthcare/)).toBeInTheDocument()
    // Energy (-1) should not appear (4th by |rank_change|)
    expect(screen.queryByText(/Energy/)).not.toBeInTheDocument()
  })

  it('shows up arrow for positive rank changes', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    // Finance has +5 rank change
    expect(screen.getByText(/↑.*Finance/)).toBeInTheDocument()
  })

  it('shows down arrow for negative rank changes', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    // Healthcare has -2 rank change
    expect(screen.getByText(/↓.*Healthcare/)).toBeInTheDocument()
  })

  it('shows stage 2 section with stock explorer reference when no count provided', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    // Stage 2 section should be present
    expect(screen.getByText(/stage 2/i)).toBeInTheDocument()
  })

  it('renders with empty sectors without error', () => {
    expect(() =>
      render(<WeeklyHighlights phase="bull" choppy={false} sectors={[]} />)
    ).not.toThrow()
  })
})
