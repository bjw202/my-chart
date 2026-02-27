import client from './client'
import type { SectorInfo } from '../types/stock'

export async function fetchSectors(): Promise<SectorInfo[]> {
  const response = await client.get<SectorInfo[]>('/sectors')
  return response.data
}
