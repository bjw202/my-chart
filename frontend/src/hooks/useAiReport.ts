/** AI 리포트 SSE 스트리밍 및 히스토리 상태 관리 훅. */

import { useState, useCallback, useRef } from 'react'
import {
  createAiReportStream,
  fetchAiReportHistory,
  fetchAiReportContent,
  type AiReportMode,
} from '../api/aiReport'
import type { AiReportStatus, HistoryItem } from '../types/aiReport'

interface UseAiReportReturn {
  /** 현재 상태 */
  status: AiReportStatus
  /** 스트리밍 중 누적된 마크다운 텍스트 */
  markdown: string
  /** 에러 메시지 */
  errorMessage: string
  /** 히스토리 목록 */
  history: HistoryItem[]
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

// @MX:ANCHOR: [AUTO] AI 리포트 SSE 스트리밍 훅 - ChartCell에서 AI 버튼으로 호출
// @MX:REASON: fan_in >= 2: ChartCell 트리거, AiReportModal 소비
export function useAiReport(): UseAiReportReturn {
  const [status, setStatus] = useState<AiReportStatus>('idle')
  const [markdown, setMarkdown] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [history, setHistory] = useState<HistoryItem[]>([])
  const abortRef = useRef<AbortController | null>(null)

  // SPEC-AI-REPORT-002 D5: mode 파라미터 추가 (기본값 'perplexity', 기존 호출부 호환 유지)
  const startStream = useCallback((code: string, mode: AiReportMode = 'perplexity') => {
    // 이전 스트림이 있으면 중단
    if (abortRef.current) {
      abortRef.current.abort()
    }

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
  }, [])

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
  }, [abort])

  return {
    status,
    markdown,
    errorMessage,
    history,
    startStream,
    abort,
    loadHistory,
    loadSavedReport,
    reset,
  }
}
