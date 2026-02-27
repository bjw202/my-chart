import client from './client'
import type { ChartResponse } from '../types/chart'

export async function fetchChartData(code: string): Promise<ChartResponse> {
  const response = await client.get<ChartResponse>(`/chart/${encodeURIComponent(code)}`)
  return response.data
}
