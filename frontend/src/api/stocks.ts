/**
 * 종목 마스터 API — GET /api/stocks/master
 *
 * REQ-SEARCH-002: 503 stock_meta_not_ready 에러 변환
 * REQ-DATA-001: ETag + Cache-Control 응답 처리
 */

import client from './client'

export interface StockMasterItem {
  code: string
  name: string
  market: string
}

export interface StockMasterResponse {
  stocks: StockMasterItem[]
  generated_at: string
}

export async function fetchStockMaster(): Promise<StockMasterResponse> {
  try {
    const res = await client.get<StockMasterResponse>('/stocks/master')
    return res.data
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } }).response?.status
    if (status === 503) {
      throw new Error('stock_meta_not_ready')
    }
    throw err
  }
}
