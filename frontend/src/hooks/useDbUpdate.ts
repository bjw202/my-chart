import { useCallback, useEffect, useRef, useState } from 'react'
import { startDbUpdate, subscribeDbStatus } from '../api/db'
import type { UpdateProgress } from '../types/chart'

interface DbUpdateState {
  progress: UpdateProgress | null
  isRunning: boolean
  error: string | null
  triggerUpdate: () => Promise<void>
}

export function useDbUpdate(): DbUpdateState {
  const [progress, setProgress] = useState<UpdateProgress | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    return () => {
      unsubscribeRef.current?.()
    }
  }, [])

  const triggerUpdate = useCallback(async () => {
    if (isRunning) return
    setIsRunning(true)
    setError(null)
    setProgress(null)

    try {
      await startDbUpdate()
      unsubscribeRef.current?.()
      unsubscribeRef.current = subscribeDbStatus(
        (p) => {
          setProgress(p)
          if (p.progress >= 100) {
            setIsRunning(false)
            unsubscribeRef.current?.()
            unsubscribeRef.current = null
          }
        },
        () => {
          // SSE error; stop showing running state
          setIsRunning(false)
        }
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'DB update failed')
      setIsRunning(false)
    }
  }, [isRunning])

  return { progress, isRunning, error, triggerUpdate }
}
