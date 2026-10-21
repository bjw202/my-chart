/**
 * SPEC-AI-REPORT-004 M6: goose 분석 진행 상태 패널.
 *
 * 옛 5소스(Codex/Brave/Tavily/Naver/YouTube) + Claude 합성 패널을 goose 진행 단계로 바꿨다.
 * 단계와 순서는 design §3.5 측정 표(stream-json → 진행 단계)를 따른다.
 */

import React from 'react'
import type { GooseProgress, GooseStage } from '../types/aiReport'
import { GOOSE_STAGES } from '../utils/gooseJob'

// ── 표시용 상수 ─────────────────────────────────────────────────────────────

const STAGE_LABELS: Record<GooseStage, string> = {
  dart_prefetch: '공시 원문 수집',
  goose_start: '세션 시작',
  plan: '분석 지침 읽기',
  research_tick: '자료 검색',
  fetch_start: '원문 열람 시작',
  fetch_done: '원문 열람 완료',
  compose: '리포트 입력 작성',
  render_draft: '초안 만들기',
  audit: '최종 감사',
  session_end: '세션 종료',
  screenshot: '화면 캡처',
  review: '감수',
  render_final: '최종본 만들기',
}

type StageState = 'pending' | 'running' | 'done' | 'skipped'

const STATE_ICON: Record<StageState, string> = {
  pending: '⏸',
  running: '⏳',
  done: '✅',
  skipped: '➖',
}

const STATE_HINT: Record<StageState, string> = {
  pending: '대기',
  running: '진행 중…',
  done: '',
  skipped: '건너뜀',
}

// ── 유틸 ────────────────────────────────────────────────────────────────────

/** 가장 늦게 도달한 단계가 진행 중, 그 앞 단계는 완료(도달하지 않았으면 건너뜀). */
function stageStates(progress: GooseProgress): Record<GooseStage, StageState> {
  const reached = new Set(progress.reached)
  const maxIdx = GOOSE_STAGES.reduce((max, stage, i) => (reached.has(stage) ? i : max), -1)
  const states = {} as Record<GooseStage, StageState>
  GOOSE_STAGES.forEach((stage, i) => {
    if (i < maxIdx) states[stage] = reached.has(stage) ? 'done' : 'skipped'
    else if (i === maxIdx) states[stage] = stage === 'session_end' ? 'done' : 'running'
    else states[stage] = 'pending'
  })
  return states
}

function stageMeta(stage: GooseStage, progress: GooseProgress): string {
  if (stage === 'research_tick' && progress.researchTicks > 0) return `${progress.researchTicks}회`
  if (stage === 'fetch_start' && progress.fetchStarted > 0) return `${progress.fetchStarted}건`
  if (stage === 'fetch_done' && progress.fetchDone > 0) return `${progress.fetchDone}건`
  return ''
}

// ── 컴포넌트 ────────────────────────────────────────────────────────────────

interface ProgressPanelProps {
  progress: GooseProgress
}

export function ProgressPanel({ progress }: ProgressPanelProps): React.ReactElement {
  const states = stageStates(progress)

  return (
    <div className="ai-report-progress-panel" aria-live="polite">
      <div className="ai-report-progress-header">
        <span className="ai-report-progress-title">🔄 Goose 분석 진행 상황</span>
      </div>

      <ul className="ai-report-progress-sources">
        {GOOSE_STAGES.map((stage) => {
          const state = states[stage]
          const meta = stageMeta(stage, progress)
          return (
            <li
              key={stage}
              data-stage={stage}
              data-state={state}
              className={`ai-report-progress-source ai-report-progress-source--${state}`}
            >
              <span className="ai-report-progress-icon">{STATE_ICON[state]}</span>
              <span className="ai-report-progress-name">{STAGE_LABELS[stage]}</span>
              <span className="ai-report-progress-meta">
                {meta && <span className="ai-report-progress-count">{meta}</span>}
                {stage === 'fetch_start' && progress.lastFetch && (
                  <span className="ai-report-progress-detail">{progress.lastFetch}</span>
                )}
                {STATE_HINT[state] && <span className="ai-report-progress-hint">{STATE_HINT[state]}</span>}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
