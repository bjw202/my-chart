/**
 * SPEC-AI-REPORT-004 M6 — useAiReport의 goose 작업 흐름 시험 (design §7.1, AC-AIR4-020).
 *
 * api 모듈의 goose 함수는 가짜로 바꾸고, 저장 키 모듈(utils/gooseJob)은 실제 것을 쓴다.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'

vi.mock('../../api/aiReport', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/aiReport')>()
  return {
    ...actual,
    startGooseJob: vi.fn(),
    subscribeGooseJob: vi.fn(),
    cancelGooseJob: vi.fn(),
    createAiReportStream: vi.fn(() => new AbortController()),
  }
})

import {
  cancelGooseJob,
  createAiReportStream,
  startGooseJob,
  subscribeGooseJob,
  type GooseSubscriptionHandlers,
} from '../../api/aiReport'
import { useAiReport } from '../useAiReport'
import { readGooseJob, saveGooseJob } from '../../utils/gooseJob'

const startMock = vi.mocked(startGooseJob)
const subscribeMock = vi.mocked(subscribeGooseJob)
const cancelMock = vi.mocked(cancelGooseJob)

let unsubscribe: Mock<() => void>

function lastHandlers(): GooseSubscriptionHandlers {
  const calls = subscribeMock.mock.calls
  return calls[calls.length - 1][1]
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  unsubscribe = vi.fn<() => void>()
  subscribeMock.mockImplementation(() => unsubscribe)
  cancelMock.mockResolvedValue(undefined)
})

describe('useAiReport — goose 작업 시작', () => {
  it('시작 성공 시 저장 키에 job_id를 넣고 그 작업을 구독한다', async () => {
    startMock.mockResolvedValueOnce({ ok: true, jobId: 'J1' })
    const { result } = renderHook(() => useAiReport())
    await act(async () => {
      await result.current.startGoose('299030')
    })
    expect(startMock).toHaveBeenCalledWith('299030')
    expect(readGooseJob('299030')).toBe('J1')
    expect(subscribeMock).toHaveBeenCalledTimes(1)
    expect(subscribeMock.mock.calls[0][0]).toBe('J1')
    expect(result.current.goose.status).toBe('running')
    expect(result.current.goose.jobId).toBe('J1')
  })

  it('429 goose_busy는 구독하지 않고 안내를 남긴다', async () => {
    startMock.mockResolvedValueOnce({ ok: false, error: 'goose_busy', message: '하나기술 분석이 진행 중입니다' })
    const { result } = renderHook(() => useAiReport())
    await act(async () => {
      await result.current.startGoose('005930')
    })
    expect(subscribeMock).not.toHaveBeenCalled()
    expect(readGooseJob('005930')).toBeNull()
    expect(result.current.goose).toMatchObject({
      status: 'error',
      errorKind: 'goose_busy',
      message: '하나기술 분석이 진행 중입니다',
    })
  })

  it('진행 이벤트를 단계로 누적한다', async () => {
    startMock.mockResolvedValueOnce({ ok: true, jobId: 'J1' })
    const { result } = renderHook(() => useAiReport())
    await act(async () => {
      await result.current.startGoose('299030')
    })
    act(() => {
      lastHandlers().onProgress({ stage: 'goose_start', detail: null })
      lastHandlers().onProgress({ stage: 'research_tick', detail: null })
    })
    expect(result.current.goose.progress.reached).toEqual(['goose_start', 'research_tick'])
    expect(result.current.goose.progress.researchTicks).toBe(1)
  })

  it('goose를 시작하면 Fast 화면 상태는 비운다', async () => {
    startMock.mockResolvedValueOnce({ ok: true, jobId: 'J1' })
    const { result } = renderHook(() => useAiReport())
    act(() => result.current.startStream('299030', 'fast'))
    expect(result.current.status).toBe('streaming')
    await act(async () => {
      await result.current.startGoose('299030')
    })
    expect(result.current.status).toBe('idle')
    expect(createAiReportStream).toHaveBeenCalledTimes(1)
  })
})

describe('useAiReport — 재구독과 종료 (AC-AIR4-020)', () => {
  it('열기(resume) → 닫기(reset): 구독 1회, 시작 POST 0회, 취소 POST 0회, 저장값 유지', () => {
    saveGooseJob('299030', 'J1')
    const { result } = renderHook(() => useAiReport())
    act(() => result.current.resumeGoose('299030'))
    expect(subscribeMock).toHaveBeenCalledTimes(1)
    expect(subscribeMock.mock.calls[0][0]).toBe('J1')
    expect(result.current.goose.status).toBe('running')
    act(() => result.current.reset())
    expect(unsubscribe).toHaveBeenCalledTimes(1)
    expect(startMock).not.toHaveBeenCalled()
    expect(cancelMock).not.toHaveBeenCalled()
    expect(readGooseJob('299030')).toBe('J1')
    expect(result.current.goose.status).toBe('idle')
  })

  it('저장 키가 없으면 resume은 아무것도 하지 않는다', () => {
    const { result } = renderHook(() => useAiReport())
    act(() => result.current.resumeGoose('299030'))
    expect(subscribeMock).not.toHaveBeenCalled()
    expect(result.current.goose.status).toBe('idle')
  })

  it('재생 끝에 done이 오면 결과를 보여 주고 저장값을 지운다', () => {
    saveGooseJob('299030', 'J1')
    const { result } = renderHook(() => useAiReport())
    act(() => result.current.resumeGoose('299030'))
    act(() =>
      lastHandlers().onTerminal('done', {
        run: '2026-10-20',
        delivery_status: 'draft',
        report_url: '/api/ai-report/299030/goose/2026-10-20/report.html',
      }),
    )
    expect(readGooseJob('299030')).toBeNull()
    expect(result.current.goose.status).toBe('done')
    expect(result.current.goose.result).toEqual({
      reportUrl: '/api/ai-report/299030/goose/2026-10-20/report.html',
      deliveryStatus: 'draft',
      interrupted: false,
      run: '2026-10-20',
    })
  })

  it('중단된 오류 종료는 상태 error + 보관 리포트(interrupted)를 함께 가진다', () => {
    saveGooseJob('299030', 'J1')
    const { result } = renderHook(() => useAiReport())
    act(() => result.current.resumeGoose('299030'))
    act(() =>
      lastHandlers().onTerminal('error', {
        error_kind: 'timeout',
        message: '분석 시간이 상한을 넘어 중단했습니다.',
        run: '2026-10-20',
        delivery_status: 'final',
        report_url: '/api/r.html',
        interrupted: true,
      }),
    )
    expect(result.current.goose).toMatchObject({
      status: 'error',
      errorKind: 'timeout',
      message: '분석 시간이 상한을 넘어 중단했습니다.',
      result: { reportUrl: '/api/r.html', deliveryStatus: 'final', interrupted: true },
    })
    expect(readGooseJob('299030')).toBeNull()
  })

  it('작업을 잃으면(404) 저장값을 지우고 idle로 돌아간다', () => {
    saveGooseJob('299030', 'J1')
    const { result } = renderHook(() => useAiReport())
    act(() => result.current.resumeGoose('299030'))
    act(() => lastHandlers().onLost())
    expect(readGooseJob('299030')).toBeNull()
    expect(result.current.goose.status).toBe('idle')
  })

  it('취소 버튼은 현재 작업 취소를 POST하고 cancelled 이벤트로 끝난다', async () => {
    saveGooseJob('299030', 'J1')
    const { result } = renderHook(() => useAiReport())
    act(() => result.current.resumeGoose('299030'))
    await act(async () => {
      await result.current.cancelGoose()
    })
    expect(cancelMock).toHaveBeenCalledWith('J1')
    act(() => lastHandlers().onTerminal('cancelled', {}))
    expect(result.current.goose.status).toBe('cancelled')
    expect(result.current.goose.result).toBeNull()
  })

  it('시작 응답을 기다리는 사이 모달을 닫으면 구독하지 않는다(저장값은 남아 셀이 폴링한다)', async () => {
    let resolveStart: (v: { ok: true; jobId: string }) => void = () => {}
    startMock.mockReturnValueOnce(new Promise((r) => { resolveStart = r }))
    const { result } = renderHook(() => useAiReport())
    let pending: Promise<void> = Promise.resolve()
    act(() => {
      pending = result.current.startGoose('299030')
    })
    act(() => result.current.reset())
    await act(async () => {
      resolveStart({ ok: true, jobId: 'J9' })
      await pending
    })
    expect(readGooseJob('299030')).toBe('J9')
    expect(subscribeMock).not.toHaveBeenCalled()
    await waitFor(() => expect(result.current.goose.status).toBe('idle'))
  })
})
