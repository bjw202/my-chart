import { useState, useCallback } from 'react'
import { fetchAnalysis } from '../api/analysis'
import type { AnalysisResponse } from '../types/analysis'

type AnalysisState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: AnalysisResponse }
  | { status: 'error'; message: string }

interface UseAnalysisReturn {
  state: AnalysisState
  load: (code: string) => Promise<void>
  reset: () => void
}

// @MX:ANCHOR: Custom hook managing analysis API state — used by AnalysisModal
// @MX:REASON: fan_in >= 2: ChartCell triggers via FS button, AnalysisModal consumes state
export function useAnalysis(): UseAnalysisReturn {
  const [state, setState] = useState<AnalysisState>({ status: 'idle' })

  const load = useCallback(async (code: string) => {
    setState({ status: 'loading' })
    try {
      const data = await fetchAnalysis(code)
      setState({ status: 'success', data })
    } catch (err) {
      const message = err instanceof Error ? err.message : '분석 데이터를 불러올 수 없습니다.'
      setState({ status: 'error', message })
    }
  }, [])

  const reset = useCallback(() => {
    setState({ status: 'idle' })
  }, [])

  return { state, load, reset }
}
