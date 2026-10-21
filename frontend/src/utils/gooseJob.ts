/**
 * SPEC-AI-REPORT-004 M6 — goose 작업 저장 키와 진행 단계 누적.
 *
 * - 저장 키: sessionStorage `goose_job:{code}` = job_id (design §7.1). 탭을 닫으면 사라지고 새로고침에는 남는다.
 * - 같은 탭의 sessionStorage 쓰기는 `storage` 이벤트를 일으키지 않으므로 저장할 때
 *   window에 `goose-job-started` 사용자 정의 이벤트를 보내 셀 폴링을 다시 시작한다(design §7.2, AC-022 (6)).
 * - 진행 단계 순서는 design §3.5 측정 표를 따른다.
 */
import type { GooseProgress, GooseProgressEvent, GooseStage } from '../types/aiReport'

export const GOOSE_JOB_STARTED_EVENT = 'goose-job-started'

export interface GooseJobStartedDetail {
  code: string
  jobId: string
}

export function gooseJobKey(code: string): string {
  return `goose_job:${code}`
}

// sessionStorage 접근이 막힌 환경(사생활 보호 모드 등)에서도 화면은 동작해야 한다.
export function readGooseJob(code: string): string | null {
  try {
    return sessionStorage.getItem(gooseJobKey(code))
  } catch {
    return null
  }
}

export function saveGooseJob(code: string, jobId: string): void {
  try {
    sessionStorage.setItem(gooseJobKey(code), jobId)
  } catch {
    // 저장 실패 — 이번 모달 안의 구독은 그대로 동작한다
  }
  window.dispatchEvent(
    new CustomEvent<GooseJobStartedDetail>(GOOSE_JOB_STARTED_EVENT, { detail: { code, jobId } }),
  )
}

/** 저장값이 그 job_id일 때만 지운다(그 사이 새 작업이 저장됐으면 남긴다). */
export function clearGooseJob(code: string, jobId: string): void {
  try {
    if (sessionStorage.getItem(gooseJobKey(code)) === jobId) {
      sessionStorage.removeItem(gooseJobKey(code))
    }
  } catch {
    // 무시
  }
}

// ── 진행 단계 (design §3.5) ─────────────────────────────────────────────────

export const GOOSE_STAGES: readonly GooseStage[] = [
  'dart_prefetch', // SPEC-AI-REPORT-005: goose 단계보다 앞(서버 사전 수집)
  'goose_start',
  'plan',
  'research_tick',
  'fetch_start',
  'fetch_done',
  'compose',
  'render_draft',
  'audit',
  'session_end',
  'screenshot', // SPEC-AI-REPORT-006: 1차 세션 뒤 서버 후처리(화면 캡처 → 감수 → 최종본)
  'review',
  'render_final',
]

export function makeInitialGooseProgress(): GooseProgress {
  return { reached: [], researchTicks: 0, fetchStarted: 0, fetchDone: 0, lastFetch: '' }
}

function isGooseStage(stage: string): stage is GooseStage {
  return (GOOSE_STAGES as readonly string[]).includes(stage)
}

/** 진행 이벤트 하나를 누적한다. 알 수 없는 단계는 같은 객체를 그대로 돌려준다. */
export function applyGooseStage(prev: GooseProgress, ev: GooseProgressEvent): GooseProgress {
  const { stage } = ev
  if (!isGooseStage(stage)) return prev
  const next: GooseProgress = {
    ...prev,
    reached: prev.reached.includes(stage) ? prev.reached : [...prev.reached, stage],
  }
  if (stage === 'research_tick') next.researchTicks = prev.researchTicks + 1
  if (stage === 'fetch_start') {
    next.fetchStarted = prev.fetchStarted + 1
    if (ev.detail) next.lastFetch = ev.detail
  }
  if (stage === 'fetch_done') next.fetchDone = prev.fetchDone + 1
  return next
}
