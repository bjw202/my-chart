/**
 * SPEC-AI-REPORT-004 M6: goose HTML 리포트 표시 (REQ-018·019, design §7.1).
 *
 * 리포트는 모델이 만든 HTML이므로 sandbox iframe으로만 띄운다. 서버 CSP sandbox(design §5.4)와 이중 방어.
 */
import React from 'react'
import type { GooseDeliveryStatus } from '../types/aiReport'

// @MX:ANCHOR: [AUTO] goose 리포트 iframe sandbox 값 — 결과 탭·기록 탭이 함께 쓰는 단일 정의.
// @MX:REASON: allow-scripts·allow-same-origin을 넣으면 모델이 만든 HTML이 앱 출처로 스크립트를
//             실행할 수 있다(REQ-018, AC-018). 값은 서버 CSP sandbox 지시어와 같게 고정한다.
export const GOOSE_IFRAME_SANDBOX = 'allow-popups allow-popups-to-escape-sandbox allow-downloads'

interface GooseReportViewProps {
  reportUrl: string
  deliveryStatus: GooseDeliveryStatus
  interrupted: boolean
}

export function GooseReportView({
  reportUrl,
  deliveryStatus,
  interrupted,
}: GooseReportViewProps): React.ReactElement {
  return (
    <div className="ai-report-goose-report">
      {interrupted && (
        <div className="ai-report-goose-interrupted" role="status">
          분석이 중단되었습니다
        </div>
      )}
      {deliveryStatus === 'draft' && (
        <div className="ai-report-goose-banner" role="note">
          <div className="ai-report-goose-banner-title">최종 감사 미통과 초안</div>
          <div className="ai-report-goose-banner-desc">
            goose 자체 감사를 통과하지 못한 리포트입니다. 수치와 근거를 원문과 대조해 보세요.
          </div>
        </div>
      )}
      <iframe
        className="ai-report-goose-frame"
        sandbox={GOOSE_IFRAME_SANDBOX}
        src={reportUrl}
        title="Goose 리포트"
      />
    </div>
  )
}
