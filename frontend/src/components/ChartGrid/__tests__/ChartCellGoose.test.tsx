/**
 * SPEC-AI-REPORT-004 M6: ChartCell의 goose 연동 시험.
 *
 * - AC-AIR4-020: 같은 탭에 저장된 J1 → 모달 열기·닫기 → 구독 1회, 시작 POST 0회, 취소 POST 0회
 * - AC-AIR4-022: 셀 AI 버튼 `chart-cell-ai-btn--active`가 /goose/active 폴링으로 goose 작업 상태를 반영
 *
 * 무거운 의존성(lightweight-charts·차트 API·컨텍스트)은 ChartCellRsBadge.test.tsx와 같은 방식으로 막는다.
 * goose API 함수는 가짜, 저장 키 모듈(utils/gooseJob)은 실제 것을 쓴다(같은 탭 신호까지 시험).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import React from 'react'
import type { StockItem } from '../../../types/stock'

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    addHistogramSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    addLineSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ setVisibleRange: vi.fn(), fitContent: vi.fn(), applyOptions: vi.fn() })),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  })),
}))

vi.mock('../../../api/chart', () => ({
  fetchChartData: vi.fn(() => new Promise(() => {})),
}))

vi.mock('../../../contexts/WatchlistContext', () => ({
  useWatchlist: () => ({ isChecked: vi.fn(() => false), toggleStock: vi.fn() }),
}))

vi.mock('../../../hooks/usePriceRangeMeasure', () => ({
  usePriceRangeMeasure: () => ({ phase: 'idle', result: null, toggleMeasure: vi.fn(), reset: vi.fn() }),
}))

vi.mock('../../../hooks/useAnalysis', () => ({
  useAnalysis: () => ({ state: { status: 'idle' }, load: vi.fn(), reset: vi.fn() }),
}))

vi.mock('react-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-dom')>()
  return { ...actual, createPortal: (node: React.ReactNode) => node }
})

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}))

vi.mock('remark-gfm', () => ({ default: vi.fn() }))

vi.mock('../../../api/aiReport', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/aiReport')>()
  return {
    ...actual,
    startGooseJob: vi.fn(),
    subscribeGooseJob: vi.fn(),
    cancelGooseJob: vi.fn(),
    fetchGooseActive: vi.fn(),
    createAiReportStream: vi.fn(() => new AbortController()),
  }
})

import {
  cancelGooseJob,
  fetchGooseActive,
  startGooseJob,
  subscribeGooseJob,
} from '../../../api/aiReport'
import type { GooseActiveJob } from '../../../types/aiReport'
import { ChartCell } from '../ChartCell'
import { GOOSE_ACTIVE_POLL_MS } from '../../../hooks/useGooseActive'
import { readGooseJob, saveGooseJob } from '../../../utils/gooseJob'

const activeMock = vi.mocked(fetchGooseActive)
const subscribeMock = vi.mocked(subscribeGooseJob)
const startMock = vi.mocked(startGooseJob)
const cancelMock = vi.mocked(cancelGooseJob)

const makeStock = (overrides: Partial<StockItem> = {}): StockItem => ({
  code: '299030',
  name: '하나기술',
  market: 'KOSDAQ',
  market_cap: 100000,
  sector_major: 'IT',
  sector_minor: '2차전지 장비',
  product: null,
  close: 50000,
  change_1d: 1.5,
  rs_12m: 75.5,
  ema10: null,
  ema20: null,
  sma50: null,
  sma100: null,
  sma200: null,
  stage: null,
  ...overrides,
})

function running(jobId: string): GooseActiveJob {
  return { job_id: jobId, code: '299030', stock_name: '하나기술', status: 'running' }
}

function renderCell(stock = makeStock()) {
  return render(<ChartCell stock={stock} isSelected={false} onClick={vi.fn()} timeframe="daily" />)
}

function aiButton(container: HTMLElement): HTMLElement {
  return container.querySelector('.chart-cell-ai-btn') as HTMLElement
}

async function tick(ms = GOOSE_ACTIVE_POLL_MS) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  subscribeMock.mockImplementation(() => vi.fn())
  cancelMock.mockResolvedValue(undefined)
})

describe('AC-AIR4-020 — 모달 열기·닫기는 구독만 붙였다 뗀다', () => {
  it('저장된 J1: 열기 → 구독 1회 / 닫기 → 시작·취소 POST 0회, 저장값 유지', async () => {
    saveGooseJob('299030', 'J1')
    activeMock.mockResolvedValue(running('J1'))
    const unsubscribe = vi.fn<() => void>()
    subscribeMock.mockImplementation(() => unsubscribe)
    const { container } = renderCell()
    fireEvent.click(aiButton(container))
    expect(subscribeMock).toHaveBeenCalledTimes(1)
    expect(subscribeMock.mock.calls[0][0]).toBe('J1')
    fireEvent.click(screen.getByRole('button', { name: '닫기' }))
    expect(unsubscribe).toHaveBeenCalledTimes(1)
    expect(subscribeMock).toHaveBeenCalledTimes(1)
    expect(startMock).not.toHaveBeenCalled()
    expect(cancelMock).not.toHaveBeenCalled()
    expect(readGooseJob('299030')).toBe('J1')
  })

  it('J1이 이미 끝났으면 재생 끝 done으로 결과를 보이고 저장값을 지운다', async () => {
    saveGooseJob('299030', 'J1')
    activeMock.mockResolvedValue(null)
    const { container } = renderCell()
    fireEvent.click(aiButton(container))
    const handlers = subscribeMock.mock.calls[0][1]
    act(() =>
      handlers.onTerminal('done', {
        run: '2026-10-20',
        delivery_status: 'draft',
        report_url: '/api/ai-report/299030/goose/2026-10-20/report.html',
      }),
    )
    expect(document.body.querySelector('iframe')?.getAttribute('src')).toBe(
      '/api/ai-report/299030/goose/2026-10-20/report.html',
    )
    expect(screen.getAllByText('최종 감사 미통과 초안')).toHaveLength(1)
    expect(readGooseJob('299030')).toBeNull()
    expect(startMock).not.toHaveBeenCalled()
  })
})

describe('AC-AIR4-022 — 셀 활성 표시와 폴링', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('(1)~(3) 실행 중이면 --active, null을 받으면 해제하고 폴링을 멈춘다', async () => {
    saveGooseJob('299030', 'J1')
    activeMock.mockResolvedValue(running('J1'))
    const { container } = renderCell()
    await tick(0)
    // (1) 모달을 닫은 상태에서 주기 경과, J1 실행 중
    await tick()
    expect(aiButton(container)).toHaveClass('chart-cell-ai-btn--active')
    // (2) 다음 주기 응답 null
    activeMock.mockResolvedValue(null)
    await tick()
    expect(aiButton(container)).not.toHaveClass('chart-cell-ai-btn--active')
    // (3) 그 뒤 주기 경과 → 추가 폴링 0회
    const calls = activeMock.mock.calls.length
    await tick()
    await tick()
    expect(activeMock.mock.calls.length).toBe(calls)
  })

  it('(4) 새로 마운트(새로고침)해도 저장 키가 있으면 첫 폴링 후 --active', async () => {
    saveGooseJob('299030', 'J1')
    activeMock.mockResolvedValue(running('J1'))
    const { container } = renderCell()
    await tick(0)
    expect(activeMock).toHaveBeenCalledTimes(1)
    expect(aiButton(container)).toHaveClass('chart-cell-ai-btn--active')
  })

  it('(5) 저장 키가 없는 다른 셀은 폴링하지 않는다', async () => {
    saveGooseJob('299030', 'J1')
    activeMock.mockResolvedValue(running('J1'))
    const { container } = renderCell(makeStock({ code: '005930', name: '삼성전자' }))
    await tick(0)
    await tick()
    await tick()
    expect(activeMock).not.toHaveBeenCalled()
    expect(aiButton(container)).not.toHaveClass('chart-cell-ai-btn--active')
  })

  it('다른 작업이 실행 중이면(job_id 불일치) 활성 아님, 폴링 중지', async () => {
    saveGooseJob('299030', 'J1')
    activeMock.mockResolvedValue({ ...running('JX'), code: '005930', stock_name: '삼성전자' })
    const { container } = renderCell()
    await tick(0)
    await tick()
    expect(aiButton(container)).not.toHaveClass('chart-cell-ai-btn--active')
    expect(activeMock).toHaveBeenCalledTimes(1)
  })

  it('(6) 폴링이 멈춘 뒤 같은 셀에서 J2 시작 → 닫기 → 주기 경과: 폴링 재개, --active', async () => {
    saveGooseJob('299030', 'J1')
    activeMock.mockResolvedValue(null)
    const { container } = renderCell()
    await tick(0)
    await tick()
    const stoppedAt = activeMock.mock.calls.length
    expect(stoppedAt).toBe(1)

    // 모달 열기 → J1 구독(재생 끝 null 처리는 이 시험의 관심 밖) → Goose 시작
    startMock.mockResolvedValue({ ok: true, jobId: 'J2' })
    activeMock.mockResolvedValue(running('J2'))
    fireEvent.click(aiButton(container))
    const resumeHandlers = subscribeMock.mock.calls[0][1]
    act(() => resumeHandlers.onLost())
    fireEvent.click(screen.getByRole('tab', { name: 'Goose' }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Goose 분석 시작' }))
    })
    expect(startMock).toHaveBeenCalledTimes(1)
    expect(readGooseJob('299030')).toBe('J2')
    fireEvent.click(screen.getByRole('button', { name: '닫기' }))
    await tick()
    expect(activeMock.mock.calls.length).toBeGreaterThan(stoppedAt)
    expect(aiButton(container)).toHaveClass('chart-cell-ai-btn--active')
  })

  it('Fast 스트리밍 중 --active 조건은 그대로다', async () => {
    const { container } = renderCell()
    fireEvent.click(aiButton(container))
    fireEvent.click(screen.getByRole('button', { name: '빠른 분석 시작' }))
    expect(aiButton(container)).toHaveClass('chart-cell-ai-btn--active')
    expect(activeMock).not.toHaveBeenCalled()
  })
})
