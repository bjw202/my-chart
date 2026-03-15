import client from './client'
import type { TreemapResponse } from '../types/treemap'

// @MX:NOTE: [AUTO] 트리맵 API 호출 - GET /api/market/treemap?period={period}
export async function fetchTreemap(period: string): Promise<TreemapResponse> {
  const response = await client.get<TreemapResponse>('/market/treemap', {
    params: { period },
  })
  return response.data
}
