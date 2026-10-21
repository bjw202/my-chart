/**
 * SPEC-AI-REPORT-004 M6: ProgressPanel 단위 테스트 — goose 진행 단계(design §3.5 측정 표).
 *
 * 옛 5소스(Codex/Brave/Tavily/Naver/YouTube) + Claude 합성 패널을 goose 단계 10개로 바꿨다.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ProgressPanel } from '../ProgressPanel'
import type { GooseProgress } from '../../types/aiReport'
import { applyGooseStage, makeInitialGooseProgress } from '../../utils/gooseJob'

function progressOf(...stages: string[]): GooseProgress {
  return stages.reduce(
    (p, stage) => applyGooseStage(p, { stage, detail: stage === 'fetch_start' ? '네이버 금융 공시' : null }),
    makeInitialGooseProgress(),
  )
}

function stateOf(container: HTMLElement, stage: string): string | null {
  return container.querySelector(`[data-stage="${stage}"]`)?.getAttribute('data-state') ?? null
}

describe('ProgressPanel — goose 진행 단계', () => {
  it('단계 11개(공시 원문 수집 + 측정 표 10개)를 순서대로 렌더하고 옛 5소스 이름은 없다', () => {
    const { container } = render(<ProgressPanel progress={makeInitialGooseProgress()} />)
    const stages = Array.from(container.querySelectorAll('[data-stage]')).map((el) =>
      el.getAttribute('data-stage'),
    )
    expect(stages).toEqual([
      'dart_prefetch',
      'goose_start',
      'plan',
      'research_tick',
      'fetch_start',
      'fetch_done',
      'compose',
      'render_draft',
      'audit',
      'render_final',
      'session_end',
    ])
    for (const old of ['Brave', 'Tavily', 'YouTube', 'Claude 합성']) {
      expect(screen.queryByText(old)).not.toBeInTheDocument()
    }
    expect(stages.every((s) => stateOf(container, s!) === 'pending')).toBe(true)
  })

  it('공시 원문 수집 단계를 표시 문구와 함께 렌더한다(SPEC-AI-REPORT-005 AC-AIR5-003)', () => {
    const { container } = render(<ProgressPanel progress={progressOf('dart_prefetch')} />)
    expect(container.querySelector('[data-stage="dart_prefetch"]')).toHaveTextContent('공시 원문 수집')
    expect(stateOf(container, 'dart_prefetch')).toBe('running')
  })

  it('가장 늦게 도달한 단계는 진행 중, 앞의 도달 단계는 완료로 표시한다', () => {
    const { container } = render(
      <ProgressPanel progress={progressOf('goose_start', 'plan', 'research_tick', 'compose')} />,
    )
    expect(stateOf(container, 'goose_start')).toBe('done')
    expect(stateOf(container, 'plan')).toBe('done')
    expect(stateOf(container, 'research_tick')).toBe('done')
    expect(stateOf(container, 'compose')).toBe('running')
    expect(stateOf(container, 'render_draft')).toBe('pending')
  })

  it('도달하지 않고 지나간 단계는 건너뜀으로 표시한다', () => {
    const { container } = render(<ProgressPanel progress={progressOf('goose_start', 'compose')} />)
    expect(stateOf(container, 'fetch_start')).toBe('skipped')
    expect(stateOf(container, 'compose')).toBe('running')
  })

  it('검색 횟수·원문 열람 건수와 최근 열람 설명을 보여 준다', () => {
    const { container } = render(
      <ProgressPanel
        progress={progressOf('goose_start', 'research_tick', 'research_tick', 'research_tick', 'fetch_start', 'fetch_done')}
      />,
    )
    expect(container.querySelector('[data-stage="research_tick"]')).toHaveTextContent('3회')
    expect(container.querySelector('[data-stage="fetch_start"]')).toHaveTextContent('1건')
    expect(container.querySelector('[data-stage="fetch_start"]')).toHaveTextContent('네이버 금융 공시')
    expect(container.querySelector('[data-stage="fetch_done"]')).toHaveTextContent('1건')
  })

  it('session_end에 도달하면 마지막 단계도 완료다', () => {
    const { container } = render(<ProgressPanel progress={progressOf('goose_start', 'session_end')} />)
    expect(stateOf(container, 'session_end')).toBe('done')
  })

  it('aria-live 속성으로 스크린 리더에게 동적 변경을 전파한다', () => {
    const { container } = render(<ProgressPanel progress={makeInitialGooseProgress()} />)
    expect(container.querySelector('.ai-report-progress-panel')).toHaveAttribute('aria-live', 'polite')
  })
})
