/** AI 리포트 SSE 스트리밍 및 히스토리 상태 관리 훅. */

import { useState, useCallback, useRef } from 'react'
import {
  createAiReportStream,
  fetchAiReportHistory,
  fetchAiReportContent,
  type AiReportMode,
} from '../api/aiReport'
import type {
  AiReportStatus,
  DeepProgress,
  HistoryItem,
  PhaseEvent,
  SourceName,
  SourceProgress,
  SynthesisProgress,
} from '../types/aiReport'

interface UseAiReportReturn {
  /** 현재 상태 */
  status: AiReportStatus
  /** 스트리밍 중 누적된 마크다운 텍스트 */
  markdown: string
  /** 에러 메시지 */
  errorMessage: string
  /** 히스토리 목록 */
  history: HistoryItem[]
  /** 심층 분석 진행 상태 (v1.0.4) */
  progress: DeepProgress
  /** 스트리밍 시작 (mode 생략 시 'perplexity' 기본값) */
  startStream: (code: string, mode?: AiReportMode) => void
  /** 스트리밍 중단 및 상태 초기화 */
  abort: () => void
  /** 히스토리 목록 로드 */
  loadHistory: (code: string) => Promise<void>
  /** 저장된 리포트 로드 */
  loadSavedReport: (code: string, filename: string) => Promise<void>
  /** 상태 초기화 */
  reset: () => void
}

// ── SPEC-AI-REPORT-002 v1.0.4: 진행 상태 패널 기본값 ────────────────────────────

const SOURCE_NAMES: readonly SourceName[] = [
  'perplexity',
  'brave',
  'tavily',
  'naver',
  'youtube',
] as const

function makeInitialProgress(): DeepProgress {
  const sources = Object.fromEntries(
    SOURCE_NAMES.map((name) => [name, { state: 'pending' } as SourceProgress]),
  ) as Record<SourceName, SourceProgress>
  return {
    sources,
    synthesis: { state: 'idle' },
    collectingDone: false,
  }
}

// @MX:ANCHOR: [AUTO] AI 리포트 SSE 스트리밍 훅 - ChartCell에서 AI 버튼으로 호출
// @MX:REASON: fan_in >= 2: ChartCell 트리거, AiReportModal 소비
export function useAiReport(): UseAiReportReturn {
  const [status, setStatus] = useState<AiReportStatus>('idle')
  const [markdown, setMarkdown] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [history, setHistory] = useState<HistoryItem[]>([])
  // SPEC-AI-REPORT-002 v1.0.4: 딥 모드 진행 상태
  const [progress, setProgress] = useState<DeepProgress>(makeInitialProgress())
  const abortRef = useRef<AbortController | null>(null)

  const applyPhase = useCallback((phase: PhaseEvent) => {
    setProgress((prev) => {
      switch (phase.phase) {
        case 'source_start': {
          const updated: SourceProgress = { ...prev.sources[phase.source], state: 'running' }
          return { ...prev, sources: { ...prev.sources, [phase.source]: updated } }
        }
        case 'source_done': {
          const updated: SourceProgress = {
            state: phase.success ? 'done' : 'failed',
            durationMs: phase.duration_ms,
            count: phase.count,
            cached: phase.cached,
            error: phase.error,
          }
          return { ...prev, sources: { ...prev.sources, [phase.source]: updated } }
        }
        case 'collecting_done':
          return {
            ...prev,
            collectingDone: true,
            successful: phase.successful,
            total: phase.total,
          }
        case 'synthesis_start': {
          const synth: SynthesisProgress = { state: 'waiting', model: phase.model }
          return { ...prev, synthesis: synth }
        }
        case 'synthesis_first_chunk': {
          const synth: SynthesisProgress = { ...prev.synthesis, state: 'streaming' }
          return { ...prev, synthesis: synth }
        }
        default:
          // collecting/staging/staging_done/synthesizing: legacy, 현재 패널에서는 무시
          return prev
      }
    })
  }, [])

  // SPEC-AI-REPORT-002 D5: mode 파라미터 추가 (기본값 'perplexity', 기존 호출부 호환 유지)
  const startStream = useCallback(
    (code: string, mode: AiReportMode = 'perplexity') => {
      // 이전 스트림이 있으면 중단
      if (abortRef.current) {
        abortRef.current.abort()
      }

      setStatus('streaming')
      setMarkdown('')
      setErrorMessage('')
      // 딥 모드에서만 진행 이벤트가 오지만, 빠른 모드에서도 UI가 일관되도록 초기화한다.
      setProgress(makeInitialProgress())

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
        // SPEC-AI-REPORT-002 v1.0.4: onPhase — 딥 모드 per-source 진행 상태 수신
        applyPhase,
      )

      abortRef.current = controller
    },
    [applyPhase],
  )

  const abort = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
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
    setStatus('idle')
    setMarkdown('')
    setErrorMessage('')
    setHistory([])
    setProgress(makeInitialProgress())
  }, [abort])

  return {
    status,
    markdown,
    errorMessage,
    history,
    progress,
    startStream,
    abort,
    loadHistory,
    loadSavedReport,
    reset,
  }
}
