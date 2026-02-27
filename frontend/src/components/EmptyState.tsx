import React from 'react'

interface EmptyStateProps {
  type: 'no-results' | 'no-data'
}

export function EmptyState({ type }: EmptyStateProps): React.ReactElement {
  return (
    <div className="empty-state">
      {type === 'no-data' ? (
        <>
          <span className="empty-state-icon">📊</span>
          <p className="empty-state-title">DB 업데이트가 필요합니다</p>
          <p className="empty-state-desc">상단의 [DB 업데이트] 버튼을 클릭하세요.</p>
        </>
      ) : (
        <>
          <span className="empty-state-icon">🔍</span>
          <p className="empty-state-title">조건에 맞는 종목이 없습니다</p>
          <p className="empty-state-desc">필터 조건을 변경해 보세요.</p>
        </>
      )}
    </div>
  )
}
