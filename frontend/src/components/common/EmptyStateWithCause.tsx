// 빈 상태는 원인을 말한다 — SPEC-SECTOR-UX-001 M6 / 규칙 ER-3 (AC-SUX-054)
import type { ReactElement } from 'react'

// @MX:NOTE: [AUTO] EmptyStateWithCause — "결과 없음"만 띄우면 사용자는 무엇을 풀어야 할지 모른다.
//   활성 필터를 전부 텍스트로 나열하고, 각 필터를 그것만 해제하는 액션을 함께 렌더한다.
//   각 액션은 자기 상태만 건드린다 — 전역 clear(모든 필터 초기화)는 금지 (AC-SUX-005 / SM-3).

export interface ActiveFilter {
  // 사용자가 읽을 필터 표기 (예: "Stage 2", "시장 KOSPI", "섹터 디스플레이")
  label: string
  // 해제 액션 라벨 (예: "[Stage 필터 해제]")
  actionLabel: string
  onClear: () => void
}

export interface EmptyStateWithCauseProps {
  // null 은 비활성 필터 — 렌더 대상에서 빠진다.
  filters: (ActiveFilter | null)[]
  message?: string
}

export function EmptyStateWithCause({ filters, message }: EmptyStateWithCauseProps): ReactElement {
  const active = filters.filter((f): f is ActiveFilter => f !== null)

  return (
    <div className="empty-state-with-cause" data-testid="empty-state-with-cause" role="status">
      <div className="empty-state-message">
        {message ?? (active.length > 0
          ? '조건에 맞는 종목이 없습니다 — 아래 필터가 적용되어 있습니다'
          : '표시할 데이터가 없습니다')}
      </div>
      {active.length > 0 && (
        <ul className="empty-state-filters" data-testid="empty-state-filters">
          {active.map(f => (
            <li key={f.label} className="empty-state-filter">
              <span className="empty-state-filter-label" data-testid="empty-state-filter-label">{f.label}</span>
              <button
                type="button"
                className="empty-state-filter-clear"
                onClick={f.onClear}
              >
                {f.actionLabel}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
