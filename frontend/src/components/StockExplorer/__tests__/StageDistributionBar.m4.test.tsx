// AC-SUX-029 / 030 — StageDistributionBar M4 행동 단언 (SPEC-SECTOR-UX-001 M4).
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { StageDistribution } from '../../../types/stage'
import { StageDistributionBar } from '../StageDistributionBar'

const dist: StageDistribution = {
  stage1: 38,
  stage2: 68,
  stage3: 31,
  stage4: 22,
  unclassified_count: 5,
  total: 164,
}

// AC-SUX-030 (REQ-SUX-028): 미분류 세그먼트
describe('AC-SUX-030 — 미분류 세그먼트', () => {
  it('미분류 세그먼트가 렌더된다', () => {
    const { container } = render(
      <StageDistributionBar
        distribution={dist}
        activeStage={null}
        onStageClick={vi.fn()}
      />,
    )
    expect(container.querySelector('[data-segment-key="unclassified"]')).toBeTruthy()
  })

  it('5개 세그먼트 너비 비율의 합이 100% 다', () => {
    const { container } = render(
      <StageDistributionBar
        distribution={dist}
        activeStage={null}
        onStageClick={vi.fn()}
      />,
    )
    const segments = container.querySelectorAll('.stage-distribution-segment')
    // width 는 inline style 의 width:<n>% 로 설정된다
    const widths = Array.from(segments).map((s) => {
      const m = (s.getAttribute('style') ?? '').match(/width:\s*([\d.]+)%/)
      return m ? parseFloat(m[1]) : 0
    })
    const sum = widths.reduce((a, b) => a + b, 0)
    // 5개 세그먼트 (S1..S4 + 미분류)
    expect(segments.length).toBe(5)
    expect(Math.round(sum)).toBe(100)
  })

  it('미분류 세그먼트 클릭 시 onStageClick 이 unclassified 로 호출된다', () => {
    const onStageClick = vi.fn()
    const { container } = render(
      <StageDistributionBar
        distribution={dist}
        activeStage={null}
        onStageClick={onStageClick}
      />,
    )
    const unclassifiedSeg = container.querySelector('[data-segment-key="unclassified"]') as HTMLElement
    expect(unclassifiedSeg).toBeTruthy()
    fireEvent.click(unclassifiedSeg)
    expect(onStageClick).toHaveBeenCalledWith('unclassified')
  })

  it('범례에 미분류(SMA40 부족) 항목이 존재한다', () => {
    render(
      <StageDistributionBar
        distribution={dist}
        activeStage={null}
        onStageClick={vi.fn()}
      />,
    )
    expect(screen.getByText(/미분류\(SMA40 부족\)/)).toBeInTheDocument()
  })

  it('unclassified_count 가 없으면(구버전 응답) 미분류 세그먼트 너비는 0 이다 (결손 방어)', () => {
    const { container } = render(
      <StageDistributionBar
        distribution={{ stage1: 10, stage2: 20, stage3: 30, stage4: 40, total: 100 }}
        activeStage={null}
        onStageClick={vi.fn()}
      />,
    )
    const unclassifiedSeg = container.querySelector('[data-segment-key="unclassified"]') as HTMLElement
    const style = unclassifiedSeg.getAttribute('style') ?? ''
    expect(style).toMatch(/width:\s*0%/)
  })
})

// AC-SUX-029 (REQ-SUX-027): 헤더 라벨
describe('AC-SUX-029 — 헤더 라벨 (선택 섹터 모집단 안내)', () => {
  it('headerLabel 이 전달되면 헤더에 표시된다', () => {
    render(
      <StageDistributionBar
        distribution={dist}
        activeStage={null}
        onStageClick={vi.fn()}
        headerLabel="반도체 · 164종목"
      />,
    )
    expect(screen.getByTestId('stage-distribution-header').textContent).toContain('반도체')
    expect(screen.getByTestId('stage-distribution-header').textContent).toContain('164')
  })
})
