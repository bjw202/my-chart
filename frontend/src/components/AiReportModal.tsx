/**
 * AI 기업 분석 리포트 모달.
 *
 * Codex CLI SSE 스트리밍(Fast)은 실시간 마크다운으로, goose 작업(SPEC-AI-REPORT-004)은 진행 패널 +
 * sandbox iframe HTML 리포트로 보여 주고, 히스토리 탭에서 이전 분석(markdown / goose)을 조회할 수 있다.
 * AnalysisModal 패턴(portal + ESC + backdrop) 동일 적용.
 * SPEC-AI-REPORT-002 D4: 헤더에 2단 모드 토글(빠른 분석 / Goose) — 값은 'fast' | 'deep'.
 */
import React, { useEffect, useCallback, useRef, useState } from 'react'
import ReactDOM from 'react-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { AiReportStatus, GooseJobState, HistoryItem } from '../types/aiReport'
import { gooseReportUrl, type AiReportMode } from '../api/aiReport'
import { ProgressPanel } from './ProgressPanel'
import { GooseReportView } from './GooseReportView'

// ── 탭 타입 ─────────────────────────────────────────────────────────────────

type TabType = 'result' | 'history'

// ── Props ───────────────────────────────────────────────────────────────────

interface AiReportModalProps {
  code: string
  companyName: string
  status: AiReportStatus
  markdown: string
  errorMessage: string
  history: HistoryItem[]
  /**
   * SPEC-AI-REPORT-004 M6: goose 작업 상태(진행·결과·오류).
   * 미제공 시 goose 화면을 렌더하지 않음 (backward compat — 테스트 호환).
   */
  goose?: GooseJobState
  /** goose 실행 중 취소 버튼 */
  onCancelGoose?: () => void
  onClose: () => void
  /**
   * 스트림 재시작 콜백. mode 인자를 받아 해당 모드로 분석 시작.
   * 기존 ChartCell의 () => void 호출부와 호환 (mode 생략 시 모달 내 선택 모드 사용).
   */
  onRetry: (mode?: AiReportMode) => void
  /**
   * SPEC-AI-REPORT-002 v1.0.3: 사용자가 모드 선택 후 명시적으로 분석을 시작할 때 호출.
   * idle 상태에서만 표시되는 "분석 시작" 버튼이 트리거. 미제공 시 idle 분기는 안내 메시지만 표시.
   */
  onStart?: (mode: AiReportMode) => void
  onLoadHistory: () => void
  /** markdown 기록 항목 선택. goose 기록 항목은 모달 안에서 iframe으로 바로 연다. */
  onSelectHistory: (filename: string) => void
}

// goose 시작 거부(429) 안내에 덧붙이는 한 줄 (design §7.1)
const GOOSE_NOTICE_HINTS: Record<string, string> = {
  goose_busy: '진행 중인 분석이 끝난 뒤 다시 시도하세요.',
}

// ── 컴포넌트 ────────────────────────────────────────────────────────────────

// @MX:NOTE: [AUTO] v1.1.4+D4 - 5-state UI 상태 머신(idle/streaming/done/error/loading-history).
// useAiReport 훅의 status와 완전 동기. 신규 상태 추가 시 useAiReport의 AiReportStatus 타입도
// 함께 업데이트 필요. 탭 전환(analysis/history) 시 historyLoaded 플래그로 중복 로드 방지.
// SPEC-AI-REPORT-002 D4: mode 상태 추가 — 스트리밍 중 토글 비활성화.
export function AiReportModal({
  code,
  companyName,
  status,
  markdown,
  errorMessage,
  history,
  goose,
  onCancelGoose,
  onClose,
  onRetry,
  onStart,
  onLoadHistory,
  onSelectHistory,
}: AiReportModalProps): React.ReactElement {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [activeTab, setActiveTab] = useState<TabType>('result')
  const [copied, setCopied] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const gooseActive = goose !== undefined && goose.status !== 'idle'
  const gooseBusy = goose?.status === 'starting' || goose?.status === 'running'
  // SPEC-AI-REPORT-002 FR-011: 2단 모드 선택 상태 ('fast' 기본값).
  // SPEC-AI-REPORT-004: 다시 열 때 goose 작업이 있으면 Goose 모드로 연다(모달은 열 때마다 새로 마운트).
  const [mode, setMode] = useState<AiReportMode>(() => (gooseActive ? 'deep' : 'fast'))
  // 기록 탭에서 연 goose 리포트 (선택 시 결과 탭에 iframe으로 표시)
  const [selectedGoose, setSelectedGoose] = useState<HistoryItem | null>(null)
  const toggleDisabled = status === 'streaming' || gooseBusy
  // Fast 화면(스트리밍·완료·오류·기록 로딩)이 있으면 그것을 우선한다. 훅이 두 화면을 동시에 만들지 않는다.
  const showGoose = mode === 'deep' && gooseActive && status === 'idle' && !selectedGoose

  // 새 분석을 시작하면 기록에서 연 goose 리포트 화면을 내린다.
  const handleStart = (m: AiReportMode) => {
    setSelectedGoose(null)
    onStart?.(m)
  }
  const handleRetry = (m: AiReportMode) => {
    setSelectedGoose(null)
    onRetry(m)
  }

  // ESC 키로 모달 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // body 스크롤 잠금
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  // 스트리밍 중 자동 스크롤
  useEffect(() => {
    if (status === 'streaming' && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [markdown, status])

  // backdrop 클릭으로 닫기
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose()
    },
    [onClose],
  )

  // 히스토리 탭 전환 시 목록 로드
  const handleTabChange = useCallback(
    (tab: TabType) => {
      setActiveTab(tab)
      if (tab === 'history' && !historyLoaded) {
        onLoadHistory()
        setHistoryLoaded(true)
      }
    },
    [historyLoaded, onLoadHistory],
  )

  // 클립보드 복사
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // 복사 실패 시 무시
    }
  }, [markdown])

  const today = new Date().toISOString().split('T')[0]

  const modal = (
    <div
      className="ai-report-backdrop"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label={`${companyName} (${code}) AI 분석`}
    >
      <div className="ai-report-modal">
        {/* 헤더 */}
        <div className="ai-report-header">
          <div className="ai-report-title">
            <div className="ai-report-title-row">
              <span className="ai-report-name">{companyName}</span>
              <span className="ai-report-code">{code}</span>
              <span className="ai-report-subtitle">AI 분석</span>
            </div>
            <div className="ai-report-date">{today}</div>
          </div>
          {/* SPEC-AI-REPORT-002 FR-011: 2단 모드 토글 — 스트리밍 중 비활성화 */}
          <div
            className="ai-report-mode-selector"
            role="tablist"
            aria-label="분석 모드"
          >
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'fast'}
              className={`ai-report-mode-btn${mode === 'fast' ? ' active' : ''}`}
              onClick={() => setMode('fast')}
              disabled={toggleDisabled}
            >
              빠른 분석
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'deep'}
              className={`ai-report-mode-btn${mode === 'deep' ? ' active' : ''}`}
              onClick={() => setMode('deep')}
              disabled={toggleDisabled}
            >
              Goose
            </button>
          </div>
          <div className="ai-report-actions">
            {/* 복사 버튼: 분석 완료 후에만 표시 */}
            {status === 'done' && markdown && (
              <button
                className={`ai-report-copy-btn${copied ? ' ai-report-copy-btn--copied' : ''}`}
                onClick={handleCopy}
                title="마크다운 복사"
              >
                {copied ? '복사됨' : '복사'}
              </button>
            )}
            <button className="ai-report-close" onClick={onClose} aria-label="닫기">
              ✕
            </button>
          </div>
        </div>

        {/* 탭 */}
        <div className="ai-report-tabs">
          <button
            className={`ai-report-tab${activeTab === 'result' ? ' ai-report-tab--active' : ''}`}
            onClick={() => handleTabChange('result')}
          >
            분석 결과
          </button>
          <button
            className={`ai-report-tab${activeTab === 'history' ? ' ai-report-tab--active' : ''}`}
            onClick={() => handleTabChange('history')}
          >
            히스토리
          </button>
        </div>

        {/* 본문 */}
        <div className="ai-report-body" ref={scrollRef}>
          {activeTab === 'result' && (
            <>
              {/* SPEC-AI-REPORT-004 M6: 기록 탭에서 연 goose 리포트 */}
              {selectedGoose && selectedGoose.run && (
                <GooseReportView
                  reportUrl={gooseReportUrl(code, selectedGoose.run)}
                  deliveryStatus={selectedGoose.delivery_status === 'final' ? 'final' : 'draft'}
                  interrupted={selectedGoose.interrupted === true}
                />
              )}

              {/* SPEC-AI-REPORT-004 M6: goose 작업 화면 (진행 패널 + 취소 / 결과 iframe / 오류·취소 안내) */}
              {showGoose && goose && (
                <>
                  {gooseBusy && (
                    <>
                      <ProgressPanel progress={goose.progress} />
                      <div className="ai-report-goose-actions">
                        <button
                          type="button"
                          className="ai-report-retry-btn"
                          onClick={onCancelGoose}
                          disabled={goose.status !== 'running'}
                        >
                          분석 취소
                        </button>
                      </div>
                    </>
                  )}
                  {goose.result && (
                    <GooseReportView
                      reportUrl={goose.result.reportUrl}
                      deliveryStatus={goose.result.deliveryStatus}
                      interrupted={goose.result.interrupted}
                    />
                  )}
                  {(goose.status === 'error' || goose.status === 'cancelled') && (
                    <div className="ai-report-error">
                      <span className="ai-report-error-text">{goose.message}</span>
                      {goose.errorKind && GOOSE_NOTICE_HINTS[goose.errorKind] && (
                        <span className="ai-report-state-text">{GOOSE_NOTICE_HINTS[goose.errorKind]}</span>
                      )}
                      {onStart && (
                        <button className="ai-report-retry-btn" onClick={() => handleStart('deep')}>
                          다시 시도
                        </button>
                      )}
                    </div>
                  )}
                </>
              )}

              {/* Fast 화면 — 기록에서 연 goose 리포트가 있으면 숨긴다 */}
              {!selectedGoose && (
                <>
                  {/* 스트리밍 / 완료: 마크다운 렌더링 */}
                  {(status === 'streaming' || status === 'done') && markdown && (
                    <div className="ai-report-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
                    </div>
                  )}

                  {/* 완료 후: 선택한 모드(빠른/심층)로 다시 분석 (SPEC-AI-REPORT-002 v1.0.1 UI 보완) */}
                  {status === 'done' && markdown && (
                    <div className="ai-report-rerun">
                      <button className="ai-report-retry-btn" onClick={() => handleRetry(mode)}>
                        {mode === 'deep' ? 'Goose로 다시 시도' : '빠른 분석으로 다시 시도'}
                      </button>
                    </div>
                  )}

                  {/* 스트리밍 중 타이핑 인디케이터 */}
                  {status === 'streaming' && (
                    <div className="ai-report-typing">
                      <span className="ai-report-typing-dot" />
                      <span className="ai-report-typing-dot" />
                      <span className="ai-report-typing-dot" />
                    </div>
                  )}

                  {/* 저장된 리포트 로딩 중 */}
                  {status === 'loading-history' && (
                    <div className="ai-report-state-center">
                      <span className="ai-report-state-text">리포트를 불러오는 중...</span>
                    </div>
                  )}

                  {/* 에러 상태 */}
                  {status === 'error' && (
                    <div className="ai-report-state-center">
                      {markdown && (
                        <div className="ai-report-content ai-report-content--partial">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
                        </div>
                      )}
                      <div className="ai-report-error">
                        <span className="ai-report-error-text">{errorMessage}</span>
                        <button className="ai-report-retry-btn" onClick={() => handleRetry(mode)}>
                          다시 시도
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* 초기 / idle 상태 — SPEC-AI-REPORT-002 v1.0.3: 모드 선택 후 명시적 시작 */}
              {status === 'idle' && !showGoose && !selectedGoose && (
                <div className="ai-report-idle-launcher">
                  <h3 className="ai-report-idle-title">분석 모드를 선택하세요</h3>
                  <p className="ai-report-idle-desc">
                    상단 토글에서 빠른 분석 또는 심층 분석을 고른 뒤 아래 버튼으로 시작합니다.
                  </p>
                  <ul className="ai-report-idle-modes">
                    <li>
                      <strong>빠른 분석</strong> — Codex CLI 단일 호출, 약 2~9분 (진행 상태 실시간 표시)
                    </li>
                    <li>
                      <strong>Goose</strong> — Claude 기반 AI 애널리스트가 원문 근거로 HTML 리포트 작성, 수분~15분 소요
                      <br />
                      <span className="ai-report-idle-hint">
                        💡 창을 닫아도 분석은 계속되고, 다시 열면 진행 상황을 이어서 봅니다.
                      </span>
                    </li>
                  </ul>
                  {onStart && (
                    <button
                      className="ai-report-start-btn"
                      onClick={() => handleStart(mode)}
                      type="button"
                    >
                      {mode === 'deep' ? 'Goose 분석 시작' : '빠른 분석 시작'}
                    </button>
                  )}
                </div>
              )}
            </>
          )}

          {activeTab === 'history' && (
            <div className="ai-report-history">
              {history.length === 0 ? (
                <div className="ai-report-state-center">
                  <span className="ai-report-state-text">아직 분석 이력이 없습니다</span>
                </div>
              ) : (
                <ul className="ai-report-history-list">
                  {history.map((item) => {
                    const isGoose = item.kind === 'goose'
                    return (
                      <li key={`${item.kind ?? 'markdown'}:${item.run ?? item.filename}`}>
                        <button
                          className="ai-report-history-item"
                          onClick={() => {
                            if (isGoose) {
                              setSelectedGoose(item)
                            } else {
                              setSelectedGoose(null)
                              onSelectHistory(item.filename)
                            }
                            setActiveTab('result')
                          }}
                        >
                          <span className="ai-report-history-date">{item.date}</span>
                          <span className="ai-report-history-time">{item.created_at}</span>
                          {isGoose ? (
                            <>
                              <span className="ai-report-history-kind">Goose</span>
                              <span className="ai-report-history-badge">
                                {item.delivery_status === 'final' ? '최종' : '초안'}
                                {item.interrupted ? ' · 중단' : ''}
                              </span>
                            </>
                          ) : (
                            <span className="ai-report-history-file">{item.filename}</span>
                          )}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )

  return ReactDOM.createPortal(modal, document.body)
}
