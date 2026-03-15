// RRG API 클라이언트 - Relative Rotation Graph 데이터 fetch
import client from './client'
import type { RRGResponse } from '../types/rrg'

// RRG 데이터 조회 (모든 섹터의 RS-Ratio / RS-Momentum + 트레일)
export async function fetchRRGData(): Promise<RRGResponse> {
  const response = await client.get<RRGResponse>('/sectors/rrg')
  return response.data
}
