/**
 * SPEC-AI-REPORT-003: 심층 분석 진행 상태 패널.
 *
 * 5개 소스(Codex/Brave/Tavily/Naver/YouTube) 수집 진행 상황과
 * Claude CLI 합성 단계 상태를 시각화한다. 본문 위에 렌더링되어
 * 사용자가 "언제쯤 끝나는지 / 어디서 걸려 있는지"를 파악할 수 있다.
 */

import React from 'react'
import type { DeepProgress, SourceName, SourceProgress } from '../types/aiReport'

// ── 표시용 상수 ─────────────────────────────────────────────────────────────

const SOURCE_LABELS: Record<SourceName, string> = {
  codex: 'Codex 심층 리서치',
  brave: 'Brave',
  tavily: 'Tavily',
  naver: 'Naver',
  youtube: 'YouTube',
}

const STATE_ICON: Record<SourceProgress['state'], string> = {
  pending: '⏸',
  running: '⏳',
  done: '✅',
  failed: '❌',
}

// ── 유틸 ────────────────────────────────────────────────────────────────────

function formatDuration(ms?: number): string {
  if (ms === undefined) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatCount(source: SourceName, count?: number): string {
  if (count === undefined || count === 0) return ''
  if (source === 'codex') {
    // SPEC-AI-REPORT-003: Codex 는 char_count 를 바로 제공. KB로 표시하면 직관적.
    if (count >= 1000) return `${(count / 1000).toFixed(1)}KB`
    return `${count}자`
  }
  // 나머지는 결과 건수
  return `${count}건`
}

// ── 컴포넌트 ────────────────────────────────────────────────────────────────

interface ProgressPanelProps {
  progress: DeepProgress
}

export function ProgressPanel({ progress }: ProgressPanelProps): React.ReactElement {
  const orderedSources: SourceName[] = ['codex', 'brave', 'tavily', 'naver', 'youtube']

  return (
    <div className="ai-report-progress-panel" aria-live="polite">
      <div className="ai-report-progress-header">
        <span className="ai-report-progress-title">
          🔄 분석 진행 상황
        </span>
        {progress.collectingDone && progress.successful !== undefined && progress.total && (
          <span className="ai-report-progress-summary">
            수집 {progress.successful}/{progress.total}
          </span>
        )}
      </div>

      <ul className="ai-report-progress-sources">
        {orderedSources.map((name) => {
          const src = progress.sources[name]
          const icon = STATE_ICON[src.state]
          const durationText = formatDuration(src.durationMs)
          const countText = formatCount(name, src.count)
          return (
            <li
              key={name}
              className={`ai-report-progress-source ai-report-progress-source--${src.state}`}
            >
              <span className="ai-report-progress-icon">{icon}</span>
              <span className="ai-report-progress-name">{SOURCE_LABELS[name]}</span>
              <span className="ai-report-progress-meta">
                {src.cached ? (
                  <span className="ai-report-progress-cached">캐시 재사용</span>
                ) : (
                  <>
                    {durationText && <span className="ai-report-progress-duration">{durationText}</span>}
                    {countText && <span className="ai-report-progress-count">{countText}</span>}
                  </>
                )}
                {src.state === 'failed' && src.error && (
                  <span className="ai-report-progress-error">{src.error}</span>
                )}
                {src.state === 'running' && <span className="ai-report-progress-hint">진행 중…</span>}
                {src.state === 'pending' && <span className="ai-report-progress-hint">대기</span>}
              </span>
            </li>
          )
        })}
      </ul>

      <div className="ai-report-progress-synthesis">
        <span className="ai-report-progress-synth-icon">🤖</span>
        <span className="ai-report-progress-synth-label">
          Claude 합성
          {progress.synthesis.model && (
            <span className="ai-report-progress-synth-model"> ({progress.synthesis.model})</span>
          )}
        </span>
        <span className="ai-report-progress-synth-state">
          {progress.synthesis.state === 'idle' && (
            <span className="ai-report-progress-hint">수집 대기</span>
          )}
          {progress.synthesis.state === 'waiting' && (
            <span className="ai-report-progress-hint">⏳ 5개 소스 분석 중…</span>
          )}
          {progress.synthesis.state === 'streaming' && (
            <span className="ai-report-progress-hint">✍️ 생성 중</span>
          )}
        </span>
      </div>
    </div>
  )
}
