// 기준일 배지 + 로딩 인디케이터 + 수동 새로고침 + 갱신 실패 띠
// SPEC-SECTOR-UX-001 M6 — AC-SUX-035 (LD-C) / AC-SUX-036 (LD-D) / AC-SUX-037 (LD-E, SN-4)
import type { ReactElement } from 'react'
import { useDataRefresh, useAsOfCoherence } from '../../contexts/DataLoadContext'
import { useAnalysisParams } from '../../contexts/AnalysisParamsContext'

// @MX:NOTE: [AUTO] DataStatusBar — 섹터 4개 서브탭 + 종목 탐색 5개 화면 전부가 상단에 상설 렌더한다 (SN-4).
//   배지 텍스트는 응답 as_of_date 문자열을 그대로 쓴다 — 프론트에서 날짜를 계산·포맷 변환하지 않는다.
//   변환하면 서버가 보는 기준일과 화면이 말하는 기준일이 갈라져 SN-3 합치 검증이 무의미해진다.

export interface DataStatusBarProps {
  // 화면 이름 — 갱신 실패 띠·합치 경고에서 어떤 화면인지 식별한다.
  screen: string
  // 조회를 직접 소유하지 않는 화면(RRG/Bump 등)은 생략한다 —
  // AnalysisParamsContext 에 기록된 읽기전용 기준일로 폴백한다 (M1 recordAsOf 계약).
  asOfDate?: string | null
  asOfIsPartialWeek?: boolean
  // 재조회 중(기존 데이터 표시 유지) — 인디케이터만 띄운다 (LD-C).
  refetching?: boolean
  // 자동 재시도 소진 후의 실패. staleAsOf 가 있으면 "표시 중인 데이터" 문구를 쓴다.
  error?: string | null
  staleAsOf?: string | null
  onRetry?: () => void
}

export function DataStatusBar({
  screen,
  asOfDate,
  asOfIsPartialWeek,
  refetching = false,
  error = null,
  staleAsOf = null,
  onRetry,
}: DataStatusBarProps): ReactElement {
  const { refreshAll } = useDataRefresh()
  const { conflict } = useAsOfCoherence()
  const params = useAnalysisParams()
  const badgeDate = asOfDate !== undefined ? asOfDate : params.asOfDate
  const badgePartial = asOfIsPartialWeek !== undefined ? asOfIsPartialWeek : params.asOfIsPartialWeek
  const handleRetry = onRetry ?? refreshAll

  return (
    <div className="data-status-bar" data-testid="data-status-bar" data-screen={screen}>
      <div className="data-status-bar-row">
        <span className="as-of-badge" data-testid="as-of-badge">
          {/* 응답 값 문자열 그대로 — 포맷 변환 없음 (AC-SUX-037) */}
          기준일 {badgeDate ?? '—'}
          {badgePartial && (
            <span className="as-of-partial" data-testid="as-of-partial-week"> · 진행 중</span>
          )}
        </span>

        {/* LD-C: 재조회 중에는 표/차트를 유지한 채 배지 옆에만 인디케이터를 띄운다 */}
        {refetching && (
          <span className="refetch-spinner" data-testid="refetch-spinner" aria-label="갱신 중">
            갱신 중…
          </span>
        )}

        {/* AC-SUX-036: ⟳ 새로고침 은 상태와 무관하게 항상 렌더된다 */}
        <button
          type="button"
          className="refresh-btn"
          data-testid="refresh-btn"
          onClick={refreshAll}
          aria-label="새로고침"
        >
          ⟳ 새로고침
        </button>
      </div>

      {/* AC-SUX-035: 재조회 실패 — 기존 데이터를 유지한 채 띠로 고지 */}
      {error !== null && staleAsOf !== null && (
        <div className="stale-banner" data-testid="stale-banner" role="status">
          <span>갱신 실패 — 표시 중인 데이터는 {staleAsOf} 기준입니다</span>
          <button type="button" className="stale-retry-btn" data-testid="stale-retry-btn" onClick={handleRetry}>
            [다시 시도]
          </button>
        </div>
      )}

      {/* AC-SUX-035 / 036: 표시할 데이터 자체가 없는 실패 */}
      {error !== null && staleAsOf === null && (
        <div className="load-error-banner" data-testid="load-error-banner" role="alert">
          <span>불러오지 못했습니다 — {error}</span>
          <button type="button" className="stale-retry-btn" data-testid="stale-retry-btn" onClick={handleRetry}>
            [다시 시도]
          </button>
        </div>
      )}

      {/* AC-SUX-037 / SN-3: 패널 간 기준일 불일치 경고 — 두 날짜와 패널명을 모두 적는다 */}
      {conflict && (
        <div className="asof-conflict-banner" data-testid="asof-conflict-banner" role="alert">
          <span>
            기준일이 서로 다릅니다 — {conflict.panels.join(' · ')} / {conflict.dates.join(' vs ')}
          </span>
          <button
            type="button"
            className="asof-conflict-refresh"
            data-testid="asof-conflict-refresh"
            onClick={refreshAll}
          >
            [새로고침]
          </button>
        </div>
      )}
    </div>
  )
}
