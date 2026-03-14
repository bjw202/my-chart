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

  it('shows stage 2 placeholder text', () => {
    render(<WeeklyHighlights phase="bull" choppy={false} sectors={sampleSectors} />)
    expect(screen.getByText(/Stock Explorer/i)).toBeInTheDocument()
  })

  it('renders with empty sectors without error', () => {
    expect(() =>
      render(<WeeklyHighlights phase="bull" choppy={false} sectors={[]} />)
    ).not.toThrow()
  })
})
