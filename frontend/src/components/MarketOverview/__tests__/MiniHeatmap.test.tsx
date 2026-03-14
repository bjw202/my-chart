// RED: Specification tests for MiniHeatmap component
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MiniHeatmap } from '../MiniHeatmap'

const sampleSectors = [
  { name: 'Technology', returns: { w1: 2.5 }, rank: 1 },
  { name: 'Healthcare', returns: { w1: -1.2 }, rank: 2 },
  { name: 'Finance', returns: { w1: 0.5 }, rank: 3 },
  { name: 'Energy', returns: { w1: -3.0 }, rank: 4 },
]

describe('MiniHeatmap', () => {
  it('renders all sector names', () => {
    render(<MiniHeatmap sectors={sampleSectors} onSectorClick={vi.fn()} />)
    expect(screen.getByText('Technology')).toBeInTheDocument()
    expect(screen.getByText('Healthcare')).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('Energy')).toBeInTheDocument()
  })

  it('renders return percentage for each sector', () => {
    render(<MiniHeatmap sectors={sampleSectors} onSectorClick={vi.fn()} />)
    expect(screen.getByText(/\+2\.5%/)).toBeInTheDocument()
    expect(screen.getByText(/-1\.2%/)).toBeInTheDocument()
    expect(screen.getByText(/\+0\.5%/)).toBeInTheDocument()
    expect(screen.getByText(/-3\.0%/)).toBeInTheDocument()
  })

  it('calls onSectorClick with sector name when cell is clicked', () => {
    const mockClick = vi.fn()
    render(<MiniHeatmap sectors={sampleSectors} onSectorClick={mockClick} />)
    fireEvent.click(screen.getByText('Technology').closest('.mini-heatmap-cell')!)
    expect(mockClick).toHaveBeenCalledWith('Technology')
  })

  it('renders grid container with correct class', () => {
    render(<MiniHeatmap sectors={sampleSectors} onSectorClick={vi.fn()} />)
    expect(document.querySelector('.mini-heatmap-grid')).toBeInTheDocument()
  })

  it('renders with empty sectors without error', () => {
    expect(() =>
      render(<MiniHeatmap sectors={[]} onSectorClick={vi.fn()} />)
    ).not.toThrow()
  })

  it('applies background color to cells based on return', () => {
    render(<MiniHeatmap sectors={sampleSectors} onSectorClick={vi.fn()} />)
    const cells = document.querySelectorAll('.mini-heatmap-cell')
    // Each cell should have an inline background color style
    cells.forEach(cell => {
      expect((cell as HTMLElement).style.backgroundColor).toBeTruthy()
    })
  })

  it('renders 4 cells for 4 sectors', () => {
    render(<MiniHeatmap sectors={sampleSectors} onSectorClick={vi.fn()} />)
    const cells = document.querySelectorAll('.mini-heatmap-cell')
    expect(cells).toHaveLength(4)
  })
})
