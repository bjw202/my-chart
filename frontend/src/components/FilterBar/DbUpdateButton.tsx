import React from 'react'
import { useDbUpdate } from '../../hooks/useDbUpdate'

export function DbUpdateButton(): React.ReactElement {
  const { progress, isRunning, error, triggerUpdate } = useDbUpdate()

  return (
    <div className="db-update">
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
