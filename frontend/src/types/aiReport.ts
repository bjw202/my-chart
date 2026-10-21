/** AI 리포트 관련 타입 정의. */

/** goose 리포트 전달 상태 (design §5.2 — final 판정 실패면 draft). */
export type GooseDeliveryStatus = 'final' | 'draft'

export interface HistoryItem {
  filename: string
  date: string
  created_at: string
  /** SPEC-AI-REPORT-004 §5.3: markdown(기존 Fast 리포트) | goose(HTML 리포트). 없으면 markdown. */
  kind?: 'markdown' | 'goose'
  /** goose 보관 폴더 이름(YYYY-MM-DD 또는 YYYY-MM-DD_N). markdown은 null. */
  run?: string | null
  delivery_status?: GooseDeliveryStatus | null
  /** 시간 초과·취소 등으로 중단됐지만 리포트를 보관한 실행 */
  interrupted?: boolean
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

/** 5-소스 딥 리서치에서 수집 대상 소스 이름 (SPEC-AI-REPORT-003: perplexity → codex). */
export type SourceName = 'codex' | 'brave' | 'tavily' | 'naver' | 'youtube'

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
  | { phase: 'staging_prepared' }
  | { phase: 'staging_done' }
  | { phase: 'synthesizing' }
  | { phase: 'synthesis_start'; model: string }
  | { phase: 'synthesis_first_chunk' }
  // SPEC-AI-REPORT-003 Fast Mode Codex 전환
  | { phase: 'codex_fast_start' }
  | { phase: 'codex_fast_progress'; message: string }

// ── SPEC-AI-REPORT-004 M6: goose 작업 (design §3.5 · §4.4 · §7) ────────────────

/** 진행 단계 (design §3.5 측정 표). 순서는 utils/gooseJob.ts의 GOOSE_STAGES. */
export type GooseStage =
  | 'dart_prefetch' // SPEC-AI-REPORT-005: 서버가 goose 실행 전에 DART 원문을 받는 단계
  | 'goose_start'
  | 'plan'
  | 'research_tick'
  | 'fetch_start'
  | 'fetch_done'
  | 'compose'
  | 'render_draft'
  | 'audit'
  | 'render_final'
  | 'session_end'

/** SSE `event: progress`의 데이터. 알 수 없는 stage는 무시한다. */
export interface GooseProgressEvent {
  stage: string
  detail: string | null
}

/** SSE 종료 이벤트(done / error / cancelled) 데이터 — 백엔드 goose_job_service·goose_storage 계약. */
export interface GooseTerminalData {
  run?: string
  delivery_status?: GooseDeliveryStatus
  report_url?: string
  interrupted?: boolean
  error_kind?: string | null
  message?: string
}

/** 진행 단계 누적 (ProgressPanel 렌더용). */
export interface GooseProgress {
  /** 한 번 이상 도달한 단계(도달 순서) */
  reached: GooseStage[]
  researchTicks: number
  fetchStarted: number
  fetchDone: number
  /** 가장 최근 원문 열람 설명(fetch_start detail) */
  lastFetch: string
}

/** 보관된 리포트 표시 정보 */
export interface GooseResult {
  reportUrl: string
  deliveryStatus: GooseDeliveryStatus
  interrupted: boolean
  run?: string
}

export type GooseStatus = 'idle' | 'starting' | 'running' | 'done' | 'error' | 'cancelled'

/** 모달이 보여 주는 goose 작업 상태 */
export interface GooseJobState {
  status: GooseStatus
  jobId: string | null
  progress: GooseProgress
  result: GooseResult | null
  message: string
  /** error일 때 종류(goose_busy, goose_rate_limit, timeout, …) */
  errorKind?: string
}

/** GET /ai-report/goose/active 응답 (design §4.5) */
export interface GooseActiveJob {
  job_id: string
  code: string
  stock_name: string
  status: 'running'
}
