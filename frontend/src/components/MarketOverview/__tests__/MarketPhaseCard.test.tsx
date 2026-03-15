// RED: Specification tests for MarketPhaseCard component
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarketPhaseCard } from '../MarketPhaseCard'

const defaultProps = {
  kospiClose: 2700.5,
  kospiChg1w: 1.5,
  kosdaqClose: 850.25,
  kosdaqChg1w: -0.5,
  phase: 'bull' as const,
  choppy: false,
  confidence: 0.8,
}

describe('MarketPhaseCard', () => {
  it('renders KOSPI price formatted with Korean locale', () => {
    render(<MarketPhaseCard {...defaultProps} />)
    // Korean number format: 2,700.5 or 2700.5 depending on locale
    expect(screen.getByText(/2,700/)).toBeInTheDocument()
  })

  it('renders KOSDAQ price when provided', () => {
    render(<MarketPhaseCard {...defaultProps} />)
    expect(screen.getByText(/850/)).toBeInTheDocument()
  })

  it('renders positive change with positive styling', () => {
    render(<MarketPhaseCard {...defaultProps} />)
    const positiveEl = screen.getByText(/\+1\.5%/)
    expect(positiveEl).toBeInTheDocument()
  })

  it('renders negative change for KOSDAQ', () => {
    render(<MarketPhaseCard {...defaultProps} />)
    const negativeEl = screen.getByText(/-0\.5%/)
    expect(negativeEl).toBeInTheDocument()
  })

  it('renders bull phase badge with correct class', () => {
    render(<MarketPhaseCard {...defaultProps} phase="bull" />)
    const badge = screen.getByText(/bull/i)
    expect(badge.className).toContain('phase-badge--bull')
  })

  it('renders sideways phase badge', () => {
    render(<MarketPhaseCard {...defaultProps} phase="sideways" />)
    const badge = screen.getByText(/sideways/i)
    expect(badge.className).toContain('phase-badge--sideways')
  })

  it('renders bear phase badge', () => {
    render(<MarketPhaseCard {...defaultProps} phase="bear" />)
    const badge = screen.getByText(/bear/i)
    expect(badge.className).toContain('phase-badge--bear')
  })

  it('does not render choppy badge when choppy is false', () => {
    render(<MarketPhaseCard {...defaultProps} choppy={false} />)
    expect(screen.queryByText(/choppy/i)).not.toBeInTheDocument()
  })

  it('renders choppy badge when choppy is true', () => {
    render(<MarketPhaseCard {...defaultProps} choppy={true} />)
    expect(screen.getByText(/choppy/i)).toBeInTheDocument()
  })

  it('handles null KOSDAQ gracefully', () => {
    render(<MarketPhaseCard {...defaultProps} kosdaqClose={null} kosdaqChg1w={null} />)
    // Should not throw; KOSPI should still render
    expect(screen.getByText(/2,700/)).toBeInTheDocument()
  })
})
