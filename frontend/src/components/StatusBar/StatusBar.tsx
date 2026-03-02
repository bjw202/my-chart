import React, { useEffect, useState } from 'react'
import { fetchLastUpdated } from '../../api/db'
import { useScreen } from '../../contexts/ScreenContext'
import { useWatchlist } from '../../contexts/WatchlistContext'

export function StatusBar(): React.ReactElement {
  const { results, loading } = useScreen()
  const { checkedCount } = useWatchlist()
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  useEffect(() => {
    fetchLastUpdated()
      .then((d) => setLastUpdated(d.last_updated))
      .catch(() => setLastUpdated(null))
  }, [])

  const total = results?.total ?? 0

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
