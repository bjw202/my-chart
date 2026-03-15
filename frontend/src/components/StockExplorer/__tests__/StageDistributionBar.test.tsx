// RED: Tests for StageDistributionBar component
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { StageDistribution } from '../../../types/stage'
import { StageDistributionBar } from '../StageDistributionBar'

const mockDistribution: StageDistribution = {
  stage1: 120,
  stage2: 85,
  stage3: 45,
  stage4: 30,
  total: 280,
}

describe('StageDistributionBar', () => {
  it('should render stage segments with correct labels', () => {
    render(
      <StageDistributionBar
        distribution={mockDistribution}
        activeStage={null}
        onStageClick={vi.fn()}
      />
    )

    // Each stage segment button should display its label + count
    expect(screen.getByText('S1 120')).toBeInTheDocument()
    expect(screen.getByText('S2 85')).toBeInTheDocument()
    expect(screen.getByText('S3 45')).toBeInTheDocument()
    expect(screen.getByText('S4 30')).toBeInTheDocument()
  })

  it('should display count and percentage for each stage', () => {
    render(
      <StageDistributionBar
        distribution={mockDistribution}
        activeStage={null}
        onStageClick={vi.fn()}
      />
    )

    // Stage 1: 120/280 = 42.9%
    expect(screen.getByText(/120/)).toBeInTheDocument()
    // Stage 2: 85/280 = 30.4%
    expect(screen.getByText(/85/)).toBeInTheDocument()
  })

  it('should call onStageClick with stage key when a segment is clicked', async () => {
    const user = userEvent.setup()
    const onStageClick = vi.fn()

    render(
      <StageDistributionBar
        distribution={mockDistribution}
        activeStage={null}
        onStageClick={onStageClick}
      />
    )

    // Click S2 segment
    const s2Segment = screen.getByRole('button', { name: /stage 2/i })
    await user.click(s2Segment)

    expect(onStageClick).toHaveBeenCalledWith('stage2')
  })

  it('should call onStageClick with null when active stage is clicked again (toggle)', async () => {
    const user = userEvent.setup()
    const onStageClick = vi.fn()

    render(
      <StageDistributionBar
        distribution={mockDistribution}
        activeStage="stage2"
        onStageClick={onStageClick}
      />
    )

    const s2Segment = screen.getByRole('button', { name: /stage 2/i })
    await user.click(s2Segment)

    expect(onStageClick).toHaveBeenCalledWith(null)
  })

  it('should apply active class to the active stage segment', () => {
    render(
      <StageDistributionBar
        distribution={mockDistribution}
        activeStage="stage2"
        onStageClick={vi.fn()}
      />
    )

    const s2Segment = screen.getByRole('button', { name: /stage 2/i })
    expect(s2Segment).toHaveClass('active')
  })

  it('should set segment widths proportional to distribution', () => {
    const { container } = render(
      <StageDistributionBar
        distribution={mockDistribution}
        activeStage={null}
        onStageClick={vi.fn()}
      />
    )

    // Stage 1 should be widest: 120/280 ≈ 42.9%
    const s1Segment = container.querySelector('.stage-segment--s1')
    expect(s1Segment).toBeTruthy()
    // Stage 4 should be narrowest: 30/280 ≈ 10.7%
    const s4Segment = container.querySelector('.stage-segment--s4')
    expect(s4Segment).toBeTruthy()
  })
})
