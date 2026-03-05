import client from './client'
import type { AnalysisResponse } from '../types/analysis'

// @MX:ANCHOR: Public API boundary for financial analysis data fetching
// @MX:REASON: Called from useAnalysis hook and potentially other consumers
export async function fetchAnalysis(code: string): Promise<AnalysisResponse> {
  const response = await client.get<AnalysisResponse>(
    `/analysis/${encodeURIComponent(code)}`
  )
  return response.data
}
