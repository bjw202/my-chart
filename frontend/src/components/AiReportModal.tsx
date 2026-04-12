/**
 * AI 기업 분석 리포트 모달.
 *
 * Perplexity API SSE 스트리밍을 실시간 마크다운으로 렌더링하고,
 * 히스토리 탭에서 이전 분석을 조회할 수 있다.
 * AnalysisModal 패턴(portal + ESC + backdrop) 동일 적용.
 */
import React, { useEffect, useCallback, useRef, useState } from 'react'
import ReactDOM from 'react-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { AiReportStatus, HistoryItem } from '../types/aiReport'

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
  onClose: () => void
  onRetry: () => void
  onLoadHistory: () => void
  onSelectHistory: (filename: string) => void
}

// ── 컴포넌트 ────────────────────────────────────────────────────────────────

// @MX:NOTE: [AUTO] v1.1.4 - 5-state UI 상태 머신(idle/streaming/done/error/loading-history).
// useAiReport 훅의 status와 완전 동기. 신규 상태 추가 시 useAiReport의 AiReportStatus 타입도
// 함께 업데이트 필요. 탭 전환(analysis/history) 시 historyLoaded 플래그로 중복 로드 방지.
export function AiReportModal({
  code,
  companyName,
  status,
  markdown,
  errorMessage,
  history,
  onClose,
  onRetry,
  onLoadHistory,
  onSelectHistory,
}: AiReportModalProps): React.ReactElement {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [activeTab, setActiveTab] = useState<TabType>('result')
  const [copied, setCopied] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)

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
              {/* 스트리밍 / 완료: 마크다운 렌더링 */}
              {(status === 'streaming' || status === 'done') && markdown && (
                <div className="ai-report-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
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
                    <button className="ai-report-retry-btn" onClick={onRetry}>
                      다시 시도
                    </button>
                  </div>
                </div>
              )}

              {/* 초기 / idle 상태 */}
              {status === 'idle' && (
                <div className="ai-report-state-center">
                  <span className="ai-report-state-text">AI 분석을 시작하려면 AI 버튼을 클릭하세요.</span>
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
                  {history.map((item) => (
                    <li key={item.filename}>
                      <button
                        className="ai-report-history-item"
                        onClick={() => {
                          onSelectHistory(item.filename)
                          setActiveTab('result')
                        }}
                      >
                        <span className="ai-report-history-date">{item.date}</span>
                        <span className="ai-report-history-time">{item.created_at}</span>
                        <span className="ai-report-history-file">{item.filename}</span>
                      </button>
                    </li>
                  ))}
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
