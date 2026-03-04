import client from './client'
import type { ChartResponse } from '../types/chart'

export async function fetchChartData(code: string, timeframe: string = 'daily'): Promise<ChartResponse> {
  const response = await client.get<ChartResponse>(
    `/chart/${encodeURIComponent(code)}?timeframe=${timeframe}`
  )
  return response.data
}
