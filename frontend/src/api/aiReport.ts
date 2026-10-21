/** AI 리포트 API 클라이언트: Fast SSE 스트리밍 + 히스토리 조회 + goose 작업(SPEC-AI-REPORT-004). */

import client from './client'
import type {
  GooseActiveJob,
  GooseProgressEvent,
  GooseTerminalData,
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

// ── SPEC-AI-REPORT-004 M6: goose 작업 (mode=deep) ─────────────────────────────
// 백엔드 계약(routers/ai_report.py): POST /ai-report/{code}?mode=deep → 202(새 작업)/200(같은 종목 실행 중)
// {job_id}, 429 {detail: {error: goose_busy, detail}}. 하루 횟수 제한은 없다(2026-10-21). 진행은 작업 이벤트 SSE로 받는다.

export type GooseStartResult =
  | { ok: true; jobId: string }
  | { ok: false; error: string; message: string }

const GOOSE_DEFAULT_MESSAGES: Record<string, string> = {
  goose_busy: '다른 종목의 Goose 분석이 진행 중입니다',
}

/** goose 작업 시작. 429 본문을 읽어야 해서 axios 인터셉터 대신 fetch를 쓴다. */
export async function startGooseJob(code: string): Promise<GooseStartResult> {
  try {
    const response = await fetch(`/api/ai-report/${encodeURIComponent(code)}?mode=deep`, {
      method: 'POST',
    })
    const body = await response.json().catch(() => ({}))
    if (response.ok && typeof body?.job_id === 'string') {
      return { ok: true, jobId: body.job_id }
    }
    const detail = body?.detail
    const error: string =
      typeof detail?.error === 'string' ? detail.error : `http_${response.status}`
    const message: string =
      typeof detail?.detail === 'string'
        ? detail.detail
        : typeof detail === 'string'
          ? detail
          : (GOOSE_DEFAULT_MESSAGES[error] ?? `Goose 분석을 시작하지 못했습니다 (HTTP ${response.status})`)
    return { ok: false, error, message }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : '네트워크 오류가 발생했습니다.'
    return { ok: false, error: 'network', message }
  }
}

export interface GooseSubscriptionHandlers {
  onProgress: (event: GooseProgressEvent) => void
  onTerminal: (type: 'done' | 'error' | 'cancelled', data: GooseTerminalData) => void
  /** 연결이 닫힌 오류 — 없는 작업(404, 서버 재시작 등). 네트워크 끊김 재접속 중에는 부르지 않는다. */
  onLost: () => void
}

const GOOSE_TERMINAL_EVENTS = ['done', 'error', 'cancelled'] as const

// @MX:ANCHOR: [AUTO] goose 작업 이벤트 구독 — 모달(useAiReport)의 유일한 EventSource 진입점.
// @MX:REASON: 종료 이벤트에서 반드시 close()한다. 서버는 종료 이벤트 뒤 스트림을 닫는데, 닫지 않으면
//             EventSource가 Last-Event-ID로 재접속을 반복한다. 재접속 중 오류(CONNECTING)는 기다리고,
//             연결이 닫힌 오류(CLOSED — 404 등)만 작업 상실로 본다(design §4.4·§7.1).
export function subscribeGooseJob(jobId: string, handlers: GooseSubscriptionHandlers): () => void {
  const source = new EventSource(`/api/ai-report/jobs/${encodeURIComponent(jobId)}/events`)
  let closed = false
  const close = () => {
    closed = true
    source.close()
  }
  const parse = (ev: MessageEvent): unknown => {
    try {
      return JSON.parse(ev.data as string)
    } catch {
      return undefined
    }
  }

  source.addEventListener('progress', (ev) => {
    if (closed) return
    const data = parse(ev as MessageEvent) as GooseProgressEvent | undefined
    if (data && typeof data.stage === 'string') {
      handlers.onProgress({ stage: data.stage, detail: data.detail ?? null })
    }
  })
  for (const type of GOOSE_TERMINAL_EVENTS) {
    source.addEventListener(type, (ev) => {
      if (closed) return
      close()
      const data = parse(ev as MessageEvent)
      handlers.onTerminal(type, (data && typeof data === 'object' ? data : {}) as GooseTerminalData)
    })
  }
  source.onerror = () => {
    if (closed) return
    if (source.readyState === EventSource.CLOSED) {
      close()
      handlers.onLost()
    }
  }
  return close
}

/** 실행 중 작업 취소 (끝난 작업은 그대로, 결과는 구독 중인 cancelled 이벤트로 받는다). */
export async function cancelGooseJob(jobId: string): Promise<void> {
  await client.post(`/ai-report/jobs/${encodeURIComponent(jobId)}/cancel`)
}

/** 서버 전체에서 실행 중인 goose 작업 (셀 폴링 전용, design §4.5). */
export async function fetchGooseActive(): Promise<GooseActiveJob | null> {
  const res = await client.get<GooseActiveJob | null>('/ai-report/goose/active')
  return res.data ?? null
}

/** 보관된 goose 리포트 HTML 경로 — 백엔드 종료 이벤트의 report_url과 같은 모양. */
export function gooseReportUrl(code: string, run: string): string {
  return `/api/ai-report/${encodeURIComponent(code)}/goose/${encodeURIComponent(run)}/report.html`
}
