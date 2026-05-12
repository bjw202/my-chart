/** AI 리포트 API 클라이언트: SSE 스트리밍 + 히스토리 조회. */

import client from './client'
import type {
  HistoryResponse,
  PhaseEvent,
  ReportContentResponse,
} from '../types/aiReport'

/** 저장된 리포트 히스토리 조회. */
export async function fetchAiReportHistory(code: string): Promise<HistoryResponse> {
  const res = await client.get<HistoryResponse>(`/ai-report/${code}/history`)
  return res.data
}

/** 저장된 리포트 내용 조회. */
export async function fetchAiReportContent(
  code: string,
  filename: string,
): Promise<ReportContentResponse> {
  const res = await client.get<ReportContentResponse>(`/ai-report/${code}/${filename}`)
  return res.data
}

// SPEC-AI-REPORT-003: 분석 모드 타입 (Fast Mode 는 Codex CLI 기반으로 전환됨).
// 백엔드 라우터는 'perplexity' 를 deprecated alias 로 수용하지만 프론트엔드는 'fast' 로 통일.
export type AiReportMode = 'fast' | 'deep'

/**
 * SSE 스트리밍으로 AI 리포트 생성.
 *
 * EventSource 대신 fetch API 사용 (POST 지원).
 */
/** SPEC-AI-REPORT-002 v1.0.4: 진행 상태 패널용 phase 이벤트 콜백. */
export type OnPhase = (event: PhaseEvent) => void

// @MX:ANCHOR: [AUTO] v1.1.4 - 프론트엔드 SSE 스트리밍 유일한 클라이언트. fan_in >= 1.
// @MX:REASON: CRLF/LF 혼합 처리, 이벤트 경계(빈 줄), multi-line data: 조인은 SSE 스펙 필수.
// 이 3개 규칙 중 하나라도 어기면 마크다운이 공백 분리/개행 손실 상태로 렌더링됨(v1.1.1 버그 경험).
// v1.0.4: optional onPhase 콜백 추가 — 심층 분석 진행 상태 패널용. 미제공 시 phase 이벤트 무시.
export function createAiReportStream(
  code: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (message: string) => void,
  mode: AiReportMode = 'fast',
  onPhase?: OnPhase,
): AbortController {
  const controller = new AbortController()

  ;(async () => {
    try {
      const url = `/api/ai-report/${encodeURIComponent(code)}?mode=${encodeURIComponent(mode)}`
      const response = await fetch(url, {
        method: 'POST',
        signal: controller.signal,
      })

      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        const detail = body?.detail?.detail ?? body?.detail ?? `HTTP ${response.status}`
        onError(typeof detail === 'string' ? detail : JSON.stringify(detail))
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError('스트리밍을 시작할 수 없습니다.')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''
      // SSE 이벤트 누적용 (빈 줄이 이벤트 경계)
      let currentEvent = ''
      const currentDataLines: string[] = []

      const dispatchEvent = () => {
        if (currentDataLines.length === 0 && !currentEvent) return
        // 여러 data: 라인을 \n으로 조인 (SSE 스펙)
        const data = currentDataLines.join('\n')

        if (currentEvent === 'done') {
          onDone()
          return 'done'
        }
        if (currentEvent === 'error') {
          onError(data || '스트리밍 중 오류가 발생했습니다.')
          return 'error'
        }
        // SPEC-AI-REPORT-002 v1.0.4: phase 이벤트는 onPhase 콜백이 있으면 JSON 파싱 후 전달.
        // 파싱 실패는 silent ignore (호환성 유지: 이전 버전은 phase 이벤트 자체가 없었음).
        if (currentEvent === 'phase') {
          if (onPhase && data) {
            try {
              const payload = JSON.parse(data) as PhaseEvent
              onPhase(payload)
            } catch {
              // malformed phase payload — ignore
            }
          }
          return null
        }
        // 기본 이벤트 (message): 마크다운 청크
        if (data) {
          onChunk(data)
        }
        return null
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        // CRLF / LF / CR 모두 처리 (SSE 스펙은 \r\n 기본, 서버에 따라 \n)
        const lines = buffer.split(/\r\n|\r|\n/)
        // 마지막 줄은 아직 완성되지 않았을 수 있으므로 버퍼에 보관
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          // 빈 줄 = 이벤트 경계: 누적된 이벤트 dispatch
          if (line === '') {
            const result = dispatchEvent()
            currentEvent = ''
            currentDataLines.length = 0
            if (result === 'done' || result === 'error') return
            continue
          }

          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            currentDataLines.push(line.slice(6))
          } else if (line.startsWith('data:')) {
            // "data:" 뒤에 공백 없는 경우도 대응
            currentDataLines.push(line.slice(5))
          }
          // 그 외 필드 (id:, retry: 등)는 무시
        }
      }

      // 스트림이 정상 종료되었으나 마지막 이벤트가 dispatch되지 않은 경우
      dispatchEvent()
      onDone()
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // 사용자가 모달을 닫아서 취소된 경우 - 무시
        return
      }
      const message = err instanceof Error ? err.message : '네트워크 오류가 발생했습니다.'
      onError(message)
    }
  })()

  return controller
}
