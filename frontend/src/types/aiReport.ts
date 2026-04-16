/** AI 리포트 관련 타입 정의. */

export interface HistoryItem {
  filename: string
  date: string
  created_at: string
}

export interface HistoryResponse {
  items: HistoryItem[]
}

export interface ReportContentResponse {
  content: string
  filename: string
  date: string
}

export type AiReportStatus = 'idle' | 'streaming' | 'done' | 'error' | 'loading-history'

// ── SPEC-AI-REPORT-002 v1.0.4: 진행 상태 패널용 phase 이벤트 타입 ────────────────

/** 5-소스 딥 리서치에서 수집 대상 소스 이름. */
export type SourceName = 'perplexity' | 'brave' | 'tavily' | 'naver' | 'youtube'

/** 백엔드 SSE `event: phase` 이벤트의 JSON payload 타입. */
export type PhaseEvent =
  | { phase: 'collecting' }
  | { phase: 'source_start'; source: SourceName }
  | {
      phase: 'source_done'
      source: SourceName
      success: boolean
      duration_ms: number
      count: number
      cached: boolean
      error?: string
    }
  | { phase: 'collecting_done'; successful: number; total: number }
  | { phase: 'staging' }
  | { phase: 'staging_done' }
  | { phase: 'synthesizing' }
  | { phase: 'synthesis_start'; model: string }
  | { phase: 'synthesis_first_chunk' }

/** 단일 소스 진행 상태 (ProgressPanel 렌더용). */
export interface SourceProgress {
  state: 'pending' | 'running' | 'done' | 'failed'
  durationMs?: number
  count?: number
  cached?: boolean
  error?: string
}

/** 합성 단계 진행 상태. */
export interface SynthesisProgress {
  state: 'idle' | 'waiting' | 'streaming'
  model?: string
}

/** 진행 상태 스냅샷 — 딥 모드 한 회차 동안 누적되는 소스별 + 합성 상태. */
export interface DeepProgress {
  sources: Record<SourceName, SourceProgress>
  synthesis: SynthesisProgress
  /** collecting_done 이벤트 수신 여부 (수집 단계 종료 플래그). */
  collectingDone: boolean
  successful?: number
  total?: number
}
