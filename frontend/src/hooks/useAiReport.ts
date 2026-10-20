/** AI 리포트 상태 관리 훅: Fast SSE 스트리밍 + 히스토리 + goose 작업 구독(SPEC-AI-REPORT-004). */

import { useState, useCallback, useRef } from 'react'
import {
  cancelGooseJob,
  createAiReportStream,
  fetchAiReportHistory,
  fetchAiReportContent,
  startGooseJob,
  subscribeGooseJob,
  type AiReportMode,
} from '../api/aiReport'
import type {
  AiReportStatus,
  GooseJobState,
  GooseResult,
  GooseTerminalData,
  HistoryItem,
} from '../types/aiReport'
import {
  applyGooseStage,
  clearGooseJob,
  makeInitialGooseProgress,
  readGooseJob,
  saveGooseJob,
} from '../utils/gooseJob'

interface UseAiReportReturn {
  /** 현재 상태 */
  status: AiReportStatus
  /** 스트리밍 중 누적된 마크다운 텍스트 */
  markdown: string
  /** 에러 메시지 */
  errorMessage: string
  /** 히스토리 목록 */
  history: HistoryItem[]
  /** goose 작업 상태 (SPEC-AI-REPORT-004 M6) */
  goose: GooseJobState
  /** goose 작업 시작 → 저장 키 기록 → 이벤트 구독 */
  startGoose: (code: string) => Promise<void>
  /** 같은 탭에 저장된 작업이 있으면 다시 구독(처음부터 전체 재생) */
  resumeGoose: (code: string) => void
  /** 현재 goose 작업 취소 요청 */
  cancelGoose: () => Promise<void>
  /** Fast 스트리밍 시작 (mode 생략 시 'fast' 기본값 — SPEC-AI-REPORT-003 Codex 기반) */
  startStream: (code: string, mode?: AiReportMode) => void
  /** 스트리밍 중단 및 상태 초기화 */
  abort: () => void
  /** 히스토리 목록 로드 */
  loadHistory: (code: string) => Promise<void>
  /** 저장된 리포트 로드 */
  loadSavedReport: (code: string, filename: string) => Promise<void>
  /** 상태 초기화. goose는 구독만 끊는다(작업은 계속, 저장 키 유지 — design §7.1). */
  reset: () => void
}

// ── SPEC-AI-REPORT-004 M6: goose 작업 상태 ─────────────────────────────────

function makeInitialGoose(): GooseJobState {
  return { status: 'idle', jobId: null, progress: makeInitialGooseProgress(), result: null, message: '' }
}

function toGooseResult(data: GooseTerminalData): GooseResult | null {
  if (!data.report_url || (data.delivery_status !== 'final' && data.delivery_status !== 'draft')) {
    return null
  }
  return {
    reportUrl: data.report_url,
    deliveryStatus: data.delivery_status,
    interrupted: data.interrupted === true,
    run: data.run,
  }
}

const GOOSE_CANCELLED_MESSAGE = '분석을 취소했습니다.'
const GOOSE_ERROR_FALLBACK = 'Goose 분석 중 오류가 발생했습니다.'

// @MX:ANCHOR: [AUTO] AI 리포트 SSE 스트리밍 훅 - ChartCell에서 AI 버튼으로 호출
// @MX:REASON: fan_in >= 2: ChartCell 트리거, AiReportModal 소비
export function useAiReport(): UseAiReportReturn {
  const [status, setStatus] = useState<AiReportStatus>('idle')
  const [markdown, setMarkdown] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [history, setHistory] = useState<HistoryItem[]>([])
  const abortRef = useRef<AbortController | null>(null)
  // SPEC-AI-REPORT-004 M6: goose 작업 — 구독 해제 함수와 세대 번호(닫힘 뒤 늦게 온 시작 응답 무시)
  const [goose, setGoose] = useState<GooseJobState>(makeInitialGoose)
  const gooseUnsubRef = useRef<(() => void) | null>(null)
  const gooseJobIdRef = useRef<string | null>(null)
  const gooseGenRef = useRef(0)

  const detachGoose = useCallback(() => {
    gooseGenRef.current += 1
    gooseUnsubRef.current?.()
    gooseUnsubRef.current = null
    gooseJobIdRef.current = null
  }, [])

  const subscribeGoose = useCallback(
    (code: string, jobId: string) => {
      detachGoose()
      gooseJobIdRef.current = jobId
      setGoose({ ...makeInitialGoose(), status: 'running', jobId })
      gooseUnsubRef.current = subscribeGooseJob(jobId, {
        onProgress: (ev) => {
          setGoose((prev) => ({ ...prev, progress: applyGooseStage(prev.progress, ev) }))
        },
        onTerminal: (type, data) => {
          gooseUnsubRef.current = null
          clearGooseJob(code, jobId)
          const message =
            type === 'error'
              ? (data.message || GOOSE_ERROR_FALLBACK)
              : type === 'cancelled'
                ? GOOSE_CANCELLED_MESSAGE
                : ''
          setGoose((prev) => ({
            ...prev,
            status: type,
            result: toGooseResult(data),
            message,
            errorKind: type === 'error' ? (data.error_kind ?? undefined) : undefined,
          }))
        },
        onLost: () => {
          // 저장된 job_id가 없는 작업(서버 재시작·보관 한도) → 저장값 삭제 → idle (acceptance §F)
          gooseUnsubRef.current = null
          gooseJobIdRef.current = null
          clearGooseJob(code, jobId)
          setGoose(makeInitialGoose())
        },
      })
    },
    [detachGoose],
  )

  const resumeGoose = useCallback(
    (code: string) => {
      const jobId = readGooseJob(code)
      if (jobId) subscribeGoose(code, jobId)
    },
    [subscribeGoose],
  )

    // SPEC-AI-REPORT-003: mode 기본값 'fast' (Codex CLI 기반, 하위 호환 위해 라우터는 perplexity alias 수용)
  const startStream = useCallback(
    (code: string, mode: AiReportMode = 'fast') => {
      // 이전 스트림이 있으면 중단
      if (abortRef.current) {
        abortRef.current.abort()
      }

      // goose 화면은 내린다(작업은 서버에서 계속, 저장 키 유지 — 다시 열면 재구독).
      detachGoose()
      setGoose(makeInitialGoose())

      setStatus('streaming')
      setMarkdown('')
      setErrorMessage('')

      const controller = createAiReportStream(
        code,
        // onChunk: 마크다운 텍스트 누적
        (text) => {
          setMarkdown((prev) => prev + text)
        },
        // onDone: 스트리밍 완료
        () => {
          setStatus('done')
          abortRef.current = null
        },
        // onError: 오류 발생
        (message) => {
          setErrorMessage(message)
          setStatus('error')
          abortRef.current = null
        },
        mode,
      )

      abortRef.current = controller
    },
    [detachGoose],
  )

  const abort = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
  }, [])

  // @MX:NOTE: [AUTO] goose 시작 — 저장 키 기록(saveGooseJob이 같은 탭 셀에 신호)을 구독보다 먼저 한다.
  // 응답을 기다리는 사이 모달이 닫히면(세대 번호 변경) 구독하지 않지만 저장 키는 남겨 셀이 폴링한다.
  const startGoose = useCallback(
    async (code: string) => {
      if (abortRef.current) {
        abortRef.current.abort()
        abortRef.current = null
      }
      setStatus('idle')
      setMarkdown('')
      setErrorMessage('')
      detachGoose()
      const gen = gooseGenRef.current
      setGoose({ ...makeInitialGoose(), status: 'starting' })
      const res = await startGooseJob(code)
      if (res.ok) saveGooseJob(code, res.jobId)
      if (gen !== gooseGenRef.current) return
      if (!res.ok) {
        setGoose({ ...makeInitialGoose(), status: 'error', message: res.message, errorKind: res.error })
        return
      }
      subscribeGoose(code, res.jobId)
    },
    [detachGoose, subscribeGoose],
  )

  const cancelGoose = useCallback(async () => {
    const jobId = gooseJobIdRef.current
    if (!jobId) return
    try {
      await cancelGooseJob(jobId)
    } catch {
      // 취소 요청 실패 — 작업 상태는 구독 이벤트로 계속 받는다
    }
  }, [])

  const loadHistory = useCallback(async (code: string) => {
    try {
      const res = await fetchAiReportHistory(code)
      setHistory(res.items)
    } catch {
      setHistory([])
    }
  }, [])

  const loadSavedReport = useCallback(async (code: string, filename: string) => {
    try {
      setStatus('loading-history')
      const res = await fetchAiReportContent(code, filename)
      setMarkdown(res.content)
      setStatus('done')
    } catch {
      setErrorMessage('저장된 리포트를 불러올 수 없습니다.')
      setStatus('error')
    }
  }, [])

  const reset = useCallback(() => {
    abort()
    detachGoose()
    setStatus('idle')
    setMarkdown('')
    setErrorMessage('')
    setHistory([])
    setGoose(makeInitialGoose())
  }, [abort, detachGoose])

  return {
    status,
    markdown,
    errorMessage,
    history,
    goose,
    startGoose,
    resumeGoose,
    cancelGoose,
    startStream,
    abort,
    loadHistory,
    loadSavedReport,
    reset,
  }
}
