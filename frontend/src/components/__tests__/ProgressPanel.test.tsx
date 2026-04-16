/**
 * SPEC-AI-REPORT-002 v1.0.4: ProgressPanel 단위 테스트.
 *
 * 5소스 상태별 아이콘 / duration 및 count 표시 / 캐시 재사용 라벨 /
 * 합성 단계 상태(idle/waiting/streaming)를 검증한다.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'

import { ProgressPanel } from '../ProgressPanel'
import type { DeepProgress } from '../../types/aiReport'

function baseProgress(): DeepProgress {
  return {
    sources: {
      perplexity: { state: 'pending' },
      brave: { state: 'pending' },
      tavily: { state: 'pending' },
      naver: { state: 'pending' },
      youtube: { state: 'pending' },
    },
    synthesis: { state: 'idle' },
    collectingDone: false,
  }
}

describe('ProgressPanel — 진행 상태 시각화', () => {
  it('초기 상태에서 5개 소스를 pending(대기)으로 렌더링한다', () => {
    render(<ProgressPanel progress={baseProgress()} />)
    // 모든 소스 이름 표시
    expect(screen.getByText('Perplexity')).toBeInTheDocument()
    expect(screen.getByText('Brave')).toBeInTheDocument()
    expect(screen.getByText('Tavily')).toBeInTheDocument()
    expect(screen.getByText('Naver')).toBeInTheDocument()
    expect(screen.getByText('YouTube')).toBeInTheDocument()
    // 대기 힌트가 5번 표시됨
    expect(screen.getAllByText('대기').length).toBe(5)
  })

  it('running 상태는 "진행 중…" 힌트를 보여준다', () => {
    const progress = baseProgress()
    progress.sources.brave = { state: 'running' }
    render(<ProgressPanel progress={progress} />)
    expect(screen.getByText('진행 중…')).toBeInTheDocument()
  })

  it('done 상태의 소스는 duration과 count를 표시한다', () => {
    const progress = baseProgress()
    progress.sources.brave = {
      state: 'done',
      durationMs: 519,
      count: 18,
    }
    render(<ProgressPanel progress={progress} />)
    expect(screen.getByText('519ms')).toBeInTheDocument()
    expect(screen.getByText('18건')).toBeInTheDocument()
  })

  it('perplexity cache hit은 "캐시 재사용" 라벨을 보여준다', () => {
    const progress = baseProgress()
    progress.sources.perplexity = {
      state: 'done',
      durationMs: 0,
      count: 1345,
      cached: true,
    }
    render(<ProgressPanel progress={progress} />)
    expect(screen.getByText('캐시 재사용')).toBeInTheDocument()
    // cached 모드에서는 duration/count 대신 "캐시 재사용" 라벨만 노출
    expect(screen.queryByText('0ms')).not.toBeInTheDocument()
  })

  it('failed 상태는 error 코드를 표시한다', () => {
    const progress = baseProgress()
    progress.sources.tavily = {
      state: 'failed',
      durationMs: 240,
      error: 'http_error',
    }
    render(<ProgressPanel progress={progress} />)
    expect(screen.getByText('http_error')).toBeInTheDocument()
  })

  it('collecting_done 이후 요약(successful/total)을 표시한다', () => {
    const progress = baseProgress()
    progress.collectingDone = true
    progress.successful = 4
    progress.total = 5
    render(<ProgressPanel progress={progress} />)
    expect(screen.getByText('수집 4/5')).toBeInTheDocument()
  })

  it('synthesis가 waiting이면 "5개 소스 분석 중…" 표시 + 모델명 노출', () => {
    const progress = baseProgress()
    progress.synthesis = { state: 'waiting', model: 'sonnet' }
    render(<ProgressPanel progress={progress} />)
    expect(screen.getByText(/5개 소스 분석 중/)).toBeInTheDocument()
    expect(screen.getByText(/sonnet/)).toBeInTheDocument()
  })

  it('synthesis가 streaming이면 "생성 중" 힌트를 보여준다', () => {
    const progress = baseProgress()
    progress.synthesis = { state: 'streaming', model: 'sonnet' }
    render(<ProgressPanel progress={progress} />)
    expect(screen.getByText(/생성 중/)).toBeInTheDocument()
  })

  it('perplexity의 count는 KB 단위로 표시된다 (1000자 이상일 때)', () => {
    const progress = baseProgress()
    progress.sources.perplexity = {
      state: 'done',
      durationMs: 12500,
      count: 5432,
    }
    render(<ProgressPanel progress={progress} />)
    // 5432자 → 5.4KB
    expect(screen.getByText('5.4KB')).toBeInTheDocument()
    expect(screen.getByText('12.5s')).toBeInTheDocument()
  })

  it('각 소스 항목에 상태 클래스가 적용된다', () => {
    const progress = baseProgress()
    progress.sources.brave = { state: 'done', durationMs: 100, count: 5 }
    progress.sources.tavily = { state: 'failed', error: 'timeout' }
    const { container } = render(<ProgressPanel progress={progress} />)
    expect(container.querySelector('.ai-report-progress-source--done')).toBeInTheDocument()
    expect(container.querySelector('.ai-report-progress-source--failed')).toBeInTheDocument()
    expect(container.querySelectorAll('.ai-report-progress-source--pending').length).toBe(3)
  })

  it('aria-live 속성으로 스크린 리더에게 동적 변경을 전파한다', () => {
    const { container } = render(<ProgressPanel progress={baseProgress()} />)
    const panel = container.querySelector('.ai-report-progress-panel')
    expect(panel).toHaveAttribute('aria-live', 'polite')
  })
})

// Silence lint: `within` import retained for potential future nested queries
void within
