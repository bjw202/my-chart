/**
 * SPEC-AI-REPORT-002 D4: AiReportModal 2단 모드 토글 동작 테스트.
 *
 * AC-014 인수 기준 검증:
 * - 두 모드 버튼 렌더링 (빠른 분석 기본 선택)
 * - 심층 분석 클릭 시 활성 상태 전환
 * - 스트리밍 중 양쪽 버튼 비활성화
 * - 심층 분석 선택 후 다시 시도 클릭 시 mode='deep' 전달
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

// ReactDOM.createPortal 모킹 (jsdom은 document.body 포털 지원하므로 직접 렌더링)
vi.mock('react-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-dom')>()
  return {
    ...actual,
    createPortal: (node: React.ReactNode) => node,
  }
})

// react-markdown 모킹 (무거운 의존성)
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}))

vi.mock('remark-gfm', () => ({
  default: vi.fn(),
}))

import { AiReportModal } from '../AiReportModal'

// ── 공통 props 헬퍼 ────────────────────────────────────────────────────────

function makeProps(overrides: Partial<Parameters<typeof AiReportModal>[0]> = {}) {
  return {
    code: '005930',
    companyName: '삼성전자',
    status: 'idle' as const,
    markdown: '',
    errorMessage: '',
    history: [],
    onClose: vi.fn(),
    onRetry: vi.fn(),
    onLoadHistory: vi.fn(),
    onSelectHistory: vi.fn(),
    ...overrides,
  }
}

// ── 테스트 ─────────────────────────────────────────────────────────────────

describe('AiReportModal — 2단 모드 토글', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('두 모드 버튼을 렌더링하고 기본값은 빠른 분석(perplexity)이다', () => {
    render(<AiReportModal {...makeProps()} />)

    const fastBtn = screen.getByRole('tab', { name: '빠른 분석' })
    const deepBtn = screen.getByRole('tab', { name: /심층 분석/ })

    expect(fastBtn).toBeInTheDocument()
    expect(deepBtn).toBeInTheDocument()

    // 기본 선택: 빠른 분석 (aria-selected=true)
    expect(fastBtn).toHaveAttribute('aria-selected', 'true')
    expect(deepBtn).toHaveAttribute('aria-selected', 'false')

    // 활성 CSS 클래스 확인
    expect(fastBtn).toHaveClass('active')
    expect(deepBtn).not.toHaveClass('active')
  })

  it('심층 분석 버튼 클릭 시 활성 상태가 전환된다', () => {
    render(<AiReportModal {...makeProps()} />)

    const deepBtn = screen.getByRole('tab', { name: /심층 분석/ })
    const fastBtn = screen.getByRole('tab', { name: '빠른 분석' })

    fireEvent.click(deepBtn)

    expect(deepBtn).toHaveAttribute('aria-selected', 'true')
    expect(fastBtn).toHaveAttribute('aria-selected', 'false')
    expect(deepBtn).toHaveClass('active')
    expect(fastBtn).not.toHaveClass('active')
  })

  it('status=streaming일 때 두 버튼 모두 비활성화된다', () => {
    render(<AiReportModal {...makeProps({ status: 'streaming' })} />)

    const fastBtn = screen.getByRole('tab', { name: '빠른 분석' })
    const deepBtn = screen.getByRole('tab', { name: /심층 분석/ })

    expect(fastBtn).toBeDisabled()
    expect(deepBtn).toBeDisabled()
  })

  it('idle / done / error 상태에서는 버튼이 활성화된다', () => {
    const { rerender } = render(<AiReportModal {...makeProps({ status: 'idle' })} />)
    let fastBtn = screen.getByRole('tab', { name: '빠른 분석' })
    expect(fastBtn).not.toBeDisabled()

    rerender(<AiReportModal {...makeProps({ status: 'done', markdown: '# 리포트' })} />)
    fastBtn = screen.getByRole('tab', { name: '빠른 분석' })
    expect(fastBtn).not.toBeDisabled()

    rerender(
      <AiReportModal {...makeProps({ status: 'error', errorMessage: '오류 발생' })} />,
    )
    fastBtn = screen.getByRole('tab', { name: '빠른 분석' })
    expect(fastBtn).not.toBeDisabled()
  })

  it('심층 분석 선택 후 다시 시도 클릭 시 onRetry가 mode="deep"으로 호출된다', () => {
    const onRetry = vi.fn()
    render(
      <AiReportModal
        {...makeProps({
          status: 'error',
          errorMessage: '네트워크 오류',
          onRetry,
        })}
      />,
    )

    // 심층 분석으로 전환
    const deepBtn = screen.getByRole('tab', { name: /심층 분석/ })
    fireEvent.click(deepBtn)

    // 다시 시도 버튼 클릭
    const retryBtn = screen.getByRole('button', { name: '다시 시도' })
    fireEvent.click(retryBtn)

    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(onRetry).toHaveBeenCalledWith('deep')
  })

  it('빠른 분석(기본)으로 다시 시도 클릭 시 onRetry가 mode="perplexity"로 호출된다', () => {
    const onRetry = vi.fn()
    render(
      <AiReportModal
        {...makeProps({
          status: 'error',
          errorMessage: '네트워크 오류',
          onRetry,
        })}
      />,
    )

    // 기본 모드 유지 (perplexity)
    const retryBtn = screen.getByRole('button', { name: '다시 시도' })
    fireEvent.click(retryBtn)

    expect(onRetry).toHaveBeenCalledWith('perplexity')
  })

  it('role=tablist 컨테이너와 role=tab 버튼이 올바른 ARIA 구조를 갖는다', () => {
    render(<AiReportModal {...makeProps()} />)

    const tablist = screen.getByRole('tablist', { name: '분석 모드' })
    expect(tablist).toBeInTheDocument()

    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(2)
  })
})
