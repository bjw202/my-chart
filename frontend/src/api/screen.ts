import client from './client'
import type { ScreenRequest } from '../types/filter'
import type { ScreenResponse } from '../types/stock'

export async function screenStocks(filters: ScreenRequest): Promise<ScreenResponse> {
  const response = await client.post<ScreenResponse>('/screen', filters)
  return response.data
}
