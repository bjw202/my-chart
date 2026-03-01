import React, { useEffect, useState } from 'react'
import { useDbUpdate } from '../../hooks/useDbUpdate'
import { fetchLastUpdated } from '../../api/db'

export function DbUpdateButton(): React.ReactElement {
  const { progress, isRunning, error, triggerUpdate } = useDbUpdate()
  const [latestDate, setLatestDate] = useState<string | null>(null)

  useEffect(() => {
    fetchLastUpdated()
      .then((data) => setLatestDate(data.latest_data_date))
      .catch(() => {/* ignore */})
  }, [])

  // Refresh date after update completes
  useEffect(() => {
    if (!isRunning && progress?.progress === 100) {
      fetchLastUpdated()
        .then((data) => setLatestDate(data.latest_data_date))
        .catch(() => {/* ignore */})
    }
  }, [isRunning, progress?.progress])

  return (
    <div className="db-update">
      {latestDate && (
        <span className="db-latest-date">기준일: {latestDate}</span>
      )}
      <button
        type="button"
        className="db-update-btn"
        onClick={() => void triggerUpdate()}
        disabled={isRunning}
      >
        {isRunning ? 'DB 업데이트 중...' : 'DB 업데이트'}
      </button>

      {isRunning && progress && (
        <div className="db-update-progress">
          <div
            className="db-update-progress-bar"
            style={{ width: `${progress.progress}%` }}
          />
          <span className="db-update-progress-label">
            {progress.phase} — {Math.round(progress.progress)}%
            {progress.current_stock && ` (${progress.current_stock})`}
          </span>
        </div>
      )}

      {error && <span className="db-update-error">{error}</span>}
    </div>
  )
}
