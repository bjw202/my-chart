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
