// RED: SPEC-PRESET-001 AC-7 — PatternBuilder 한도 5 테스트 (Group D)
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PatternBuilder } from '../PatternBuilder'
import type { PatternCondition } from '../../../types/filter'

// 테스트용 패턴 팩토리
function makePattern(idx: number = 0): PatternCondition {
  return {
    indicator_a: 'Close',
    operator: 'gt',
    indicator_b: 'SMA50',
    multiplier: 1.0 + idx * 0.01,
  }
}

function makePatterns(count: number): PatternCondition[] {
  return Array.from({ length: count }, (_, i) => makePattern(i))
}

const defaultProps = {
  patternLogic: 'AND' as const,
  onPatternsChange: vi.fn(),
  onLogicChange: vi.fn(),
}

describe('PatternBuilder — 한도 5 (REQ-PST-008)', () => {
  // D1: 4개 patterns 상태에서 "조건 추가" 버튼이 렌더된다
  it('D1: 4개 patterns에서 "조건 추가" 버튼이 렌더된다', () => {
    render(
      <PatternBuilder
        {...defaultProps}
        patterns={makePatterns(4)}
      />
    )
    expect(screen.getByText('+ 조건 추가')).toBeInTheDocument()
  })

  // D2: 5개 patterns 상태에서 "조건 추가" 버튼이 DOM에 존재하지 않는다
  it('D2: 5개 patterns에서 "조건 추가" 버튼이 DOM에 없다', () => {
    render(
      <PatternBuilder
        {...defaultProps}
        patterns={makePatterns(5)}
      />
    )
    expect(screen.queryByText('+ 조건 추가')).not.toBeInTheDocument()
  })

  // D3: 5 → 4로 제거 후 "조건 추가" 버튼이 다시 렌더된다
  it('D3: 5개에서 1개 제거 후 "조건 추가" 버튼이 다시 나타난다', () => {
    const patterns = makePatterns(5)
    const onPatternsChange = vi.fn()

    const { rerender } = render(
      <PatternBuilder
        {...defaultProps}
        patterns={patterns}
        onPatternsChange={onPatternsChange}
      />
    )

    // 5개일 때 버튼 없음 확인
    expect(screen.queryByText('+ 조건 추가')).not.toBeInTheDocument()

    // 4개로 줄인 후 재렌더
    rerender(
      <PatternBuilder
        {...defaultProps}
        patterns={makePatterns(4)}
        onPatternsChange={onPatternsChange}
      />
    )

    expect(screen.getByText('+ 조건 추가')).toBeInTheDocument()
  })

  // 기존 동작 회귀 방어: 2개 상태에서도 버튼이 렌더된다
  it('기존 2개 patterns에서도 "조건 추가" 버튼이 렌더된다', () => {
    render(
      <PatternBuilder
        {...defaultProps}
        patterns={makePatterns(2)}
      />
    )
    expect(screen.getByText('+ 조건 추가')).toBeInTheDocument()
  })
})
