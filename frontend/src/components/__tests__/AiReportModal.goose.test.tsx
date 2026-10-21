/**
 * SPEC-AI-REPORT-004 M6: AiReportModal의 goose 화면 시험.
 *
 * - AC-AIR4-018: "Goose" 라벨, iframe sandbox 값 고정, ReactMarkdown 렌더 없음
 * - AC-AIR4-019: 초안 배너("최종 감사 미통과 초안")와 중단 안내 — 결과 탭·기록 탭 모두
 * - 진행 패널 + 취소 버튼, 429 goose_busy 안내(하루 횟수 제한 없음 — 2026-10-21), 기록 탭 kind별 표시
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}))

vi.mock('remark-gfm', () => ({ default: vi.fn() }))

import { AiReportModal } from '../AiReportModal'
import type { GooseJobState, GooseResult, HistoryItem } from '../../types/aiReport'
import { applyGooseStage, makeInitialGooseProgress } from '../../utils/gooseJob'

const SANDBOX = 'allow-popups allow-popups-to-escape-sandbox allow-downloads'
const BANNER = '최종 감사 미통과 초안'
const INTERRUPTED = '분석이 중단되었습니다'
const URL = '/api/ai-report/299030/goose/2026-10-20/report.html'

function gooseState(overrides: Partial<GooseJobState> = {}): GooseJobState {
  return {
    status: 'idle',
    jobId: null,
    progress: makeInitialGooseProgress(),
    result: null,
    message: '',
    ...overrides,
  }
}

function doneWith(result: Partial<GooseResult>): GooseJobState {
  return gooseState({
    status: 'done',
    jobId: 'J1',
    result: { reportUrl: URL, deliveryStatus: 'final', interrupted: false, run: '2026-10-20', ...result },
  })
}

function makeProps(overrides: Partial<Parameters<typeof AiReportModal>[0]> = {}) {
  return {
    code: '299030',
    companyName: '하나기술',
    status: 'idle' as const,
    markdown: '',
    errorMessage: '',
    history: [] as HistoryItem[],
    onClose: vi.fn(),
    onRetry: vi.fn(),
    onStart: vi.fn(),
    onLoadHistory: vi.fn(),
    onSelectHistory: vi.fn(),
    onCancelGoose: vi.fn(),
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AC-AIR4-018 — Goose 라벨과 iframe 렌더', () => {
  it('final 결과: 모드 버튼 "Goose", iframe sandbox 값 고정, ReactMarkdown 없음', () => {
    render(<AiReportModal {...makeProps({ goose: doneWith({}) })} />)
    expect(screen.getByRole('tab', { name: 'Goose' })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /심층 분석/ })).not.toBeInTheDocument()
    const iframes = document.body.querySelectorAll('iframe')
    expect(iframes).toHaveLength(1)
    expect(iframes[0].getAttribute('sandbox')).toBe(SANDBOX)
    expect(iframes[0].getAttribute('src')).toBe(URL)
    expect(iframes[0].getAttribute('title')).toBe('Goose 리포트')
    expect(screen.queryByTestId('markdown')).not.toBeInTheDocument()
    expect(document.body.innerHTML).not.toContain('allow-scripts')
    expect(document.body.innerHTML).not.toContain('allow-same-origin')
  })

  it('goose 작업이 있으면 모달은 Goose 모드로 열린다', () => {
    render(<AiReportModal {...makeProps({ goose: gooseState({ status: 'running', jobId: 'J1' }) })} />)
    expect(screen.getByRole('tab', { name: 'Goose' })).toHaveAttribute('aria-selected', 'true')
  })

  it('idle에서 Goose를 고르고 시작하면 onStart("deep")', () => {
    const onStart = vi.fn()
    render(<AiReportModal {...makeProps({ onStart, goose: gooseState() })} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Goose' }))
    fireEvent.click(screen.getByRole('button', { name: 'Goose 분석 시작' }))
    expect(onStart).toHaveBeenCalledWith('deep')
  })
})

describe('AC-AIR4-019 — 초안 배너와 중단 안내 (결과 탭)', () => {
  const cases: Array<[string, number, number, Partial<GooseResult>]> = [
    ['draft', 1, 0, { deliveryStatus: 'draft' }],
    ['final', 0, 0, { deliveryStatus: 'final' }],
    ['draft + interrupted', 1, 1, { deliveryStatus: 'draft', interrupted: true }],
    ['final + interrupted', 0, 1, { deliveryStatus: 'final', interrupted: true }],
  ]

  it.each(cases)('%s → 배너 %i개, 중단 안내 %i개', (_name, banners, notices, result) => {
    render(<AiReportModal {...makeProps({ goose: doneWith(result) })} />)
    expect(screen.queryAllByText(BANNER)).toHaveLength(banners)
    expect(screen.queryAllByText(INTERRUPTED)).toHaveLength(notices)
  })

  it('중단된 오류 종료(error + interrupted 리포트)도 리포트·배너·중단 안내·오류 문구를 함께 보인다', () => {
    const goose = gooseState({
      status: 'error',
      jobId: 'J1',
      errorKind: 'timeout',
      message: '분석 시간이 상한을 넘어 중단했습니다.',
      result: { reportUrl: URL, deliveryStatus: 'draft', interrupted: true, run: '2026-10-20' },
    })
    render(<AiReportModal {...makeProps({ goose })} />)
    expect(document.body.querySelectorAll('iframe')).toHaveLength(1)
    expect(screen.queryAllByText(BANNER)).toHaveLength(1)
    expect(screen.queryAllByText(INTERRUPTED)).toHaveLength(1)
    expect(screen.getByText('분석 시간이 상한을 넘어 중단했습니다.')).toBeInTheDocument()
  })
})

describe('AC-AIR4-019 — 기록 탭에서 연 goose 리포트', () => {
  const history: HistoryItem[] = [
    { filename: 'report.html', date: '2026-10-20', created_at: '10:00', kind: 'goose', run: '2026-10-20', delivery_status: 'draft', interrupted: false },
    { filename: 'report.html', date: '2026-10-19', created_at: '09:00', kind: 'goose', run: '2026-10-19_2', delivery_status: 'final', interrupted: false },
    { filename: 'report.html', date: '2026-10-19', created_at: '08:00', kind: 'goose', run: '2026-10-19', delivery_status: 'draft', interrupted: true },
    { filename: 'report.html', date: '2026-10-18', created_at: '07:00', kind: 'goose', run: '2026-10-18', delivery_status: 'final', interrupted: true },
    { filename: '2026-10-02.md', date: '2026-10-02', created_at: '06:00', kind: 'markdown', run: null, delivery_status: null, interrupted: false },
  ]

  function openHistory(onSelectHistory = vi.fn()) {
    const utils = render(<AiReportModal {...makeProps({ history, onSelectHistory, goose: gooseState() })} />)
    fireEvent.click(screen.getByRole('button', { name: '히스토리' }))
    return { ...utils, onSelectHistory }
  }

  it('기록 목록은 kind별로 표시하고 goose 항목은 전달 상태·중단 여부를 보인다', () => {
    openHistory()
    const items = document.body.querySelectorAll('.ai-report-history-item')
    expect(items).toHaveLength(5)
    expect(items[0]).toHaveTextContent('Goose')
    expect(items[0]).toHaveTextContent('초안')
    expect(items[1]).toHaveTextContent('최종')
    expect(items[2]).toHaveTextContent('중단')
    expect(items[4]).toHaveTextContent('2026-10-02.md')
    expect(items[4]).not.toHaveTextContent('Goose')
  })

  it.each([
    [0, 1, 0, '/api/ai-report/299030/goose/2026-10-20/report.html'],
    [1, 0, 0, '/api/ai-report/299030/goose/2026-10-19_2/report.html'],
    [2, 1, 1, '/api/ai-report/299030/goose/2026-10-19/report.html'],
    [3, 0, 1, '/api/ai-report/299030/goose/2026-10-18/report.html'],
  ])('기록 항목 %i 열기 → 배너 %i개, 중단 안내 %i개, iframe src %s', (index, banners, notices, src) => {
    const { onSelectHistory } = openHistory()
    fireEvent.click(document.body.querySelectorAll('.ai-report-history-item')[index])
    const iframe = document.body.querySelector('iframe')
    expect(iframe?.getAttribute('src')).toBe(src)
    expect(iframe?.getAttribute('sandbox')).toBe(SANDBOX)
    expect(screen.queryAllByText(BANNER)).toHaveLength(banners)
    expect(screen.queryAllByText(INTERRUPTED)).toHaveLength(notices)
    expect(onSelectHistory).not.toHaveBeenCalled()
  })

  it('markdown 기록 항목은 기존처럼 onSelectHistory(filename)을 부른다', () => {
    const { onSelectHistory } = openHistory()
    fireEvent.click(document.body.querySelectorAll('.ai-report-history-item')[4])
    expect(onSelectHistory).toHaveBeenCalledWith('2026-10-02.md')
    expect(document.body.querySelector('iframe')).not.toBeInTheDocument()
  })
})

describe('진행 패널·취소·429 안내', () => {
  it('실행 중: goose 단계 패널과 취소 버튼, 취소 클릭 → onCancelGoose', () => {
    const onCancelGoose = vi.fn()
    const progress = applyGooseStage(makeInitialGooseProgress(), { stage: 'plan', detail: null })
    render(
      <AiReportModal
        {...makeProps({ onCancelGoose, goose: gooseState({ status: 'running', jobId: 'J1', progress }) })}
      />,
    )
    expect(document.body.querySelector('.ai-report-progress-panel')).toBeInTheDocument()
    expect(document.body.querySelector('[data-stage="plan"]')?.getAttribute('data-state')).toBe('running')
    fireEvent.click(screen.getByRole('button', { name: '분석 취소' }))
    expect(onCancelGoose).toHaveBeenCalledTimes(1)
    expect(document.body.querySelector('iframe')).not.toBeInTheDocument()
  })

  it('실행 중에는 모드 토글을 잠근다', () => {
    render(<AiReportModal {...makeProps({ goose: gooseState({ status: 'running', jobId: 'J1' }) })} />)
    expect(screen.getByRole('tab', { name: '빠른 분석' })).toBeDisabled()
    expect(screen.getByRole('tab', { name: 'Goose' })).toBeDisabled()
  })

  it('429 goose_busy: 실행 중 종목 안내와 다시 시도 안내', () => {
    render(
      <AiReportModal
        {...makeProps({
          goose: gooseState({ status: 'error', errorKind: 'goose_busy', message: '삼성전자 분석이 진행 중입니다' }),
        })}
      />,
    )
    expect(screen.getByText('삼성전자 분석이 진행 중입니다')).toBeInTheDocument()
    expect(screen.getByText(/끝난 뒤 다시 시도/)).toBeInTheDocument()
  })

  it('하루 횟수 제한은 없으므로 "내일 다시 시도" 안내를 붙이지 않는다', () => {
    render(
      <AiReportModal
        {...makeProps({
          goose: gooseState({ status: 'error', errorKind: 'goose_rate_limit', message: '알 수 없는 거부' }),
        })}
      />,
    )
    expect(screen.getByText('알 수 없는 거부')).toBeInTheDocument()
    expect(screen.queryByText(/내일 다시/)).not.toBeInTheDocument()
  })

  it('취소로 끝나면 취소 안내와 다시 시도 버튼(onStart deep)', () => {
    const onStart = vi.fn()
    render(
      <AiReportModal
        {...makeProps({ onStart, goose: gooseState({ status: 'cancelled', jobId: 'J1', message: '분석을 취소했습니다.' }) })}
      />,
    )
    expect(screen.getByText('분석을 취소했습니다.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }))
    expect(onStart).toHaveBeenCalledWith('deep')
  })
})
