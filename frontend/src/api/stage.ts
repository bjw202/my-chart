import client from './client'
import type { StageOverviewResponse } from '../types/stage'

// @MX:ANCHOR: [AUTO] fetchStageOverview is the primary data access point for stage analysis
// @MX:REASON: Called by StockExplorer container on mount; primary API integration point for SPEC-TOPDOWN-001E

export async function fetchStageOverview(): Promise<StageOverviewResponse> {
  const { data } = await client.get<StageOverviewResponse>('/stage/overview')
  return data
}
