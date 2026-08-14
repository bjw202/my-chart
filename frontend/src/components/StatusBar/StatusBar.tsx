import React, { useEffect, useState } from 'react'
import { fetchLastUpdated } from '../../api/db'
import { useScreen } from '../../contexts/ScreenContext'
import { useWatchlist } from '../../contexts/WatchlistContext'

export function StatusBar(): React.ReactElement {
  const { results, loading, visibleCount } = useScreen()
  const { checkedCount } = useWatchlist()
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  useEffect(() => {
    fetchLastUpdated()
      .then((d) => setLastUpdated(d.last_updated))
      .catch(() => setLastUpdated(null))
  }, [])

  // 화면에 보이는 모집단이 게시되어 있으면 그 수를 따른다 — 헤더·Stage 분포·표·푸터가
  // 모두 같은 숫자를 가리키게 한다. 게시자가 없는 탭에서는 스크리닝 전체 수로 되돌아간다.
  const total = visibleCount ?? results?.total ?? 0

  return (
    <footer className="status-bar">
      <span className="status-bar-count">
        {loading ? '검색 중...' : `${total}개 종목 검색됨`}
        {checkedCount > 0 && ` | 관심 ${checkedCount}개`}
      </span>
      <span className="status-bar-updated">
        {lastUpdated ? `마지막 업데이트: ${lastUpdated}` : 'DB 업데이트 필요'}
      </span>
    </footer>
  )
}
