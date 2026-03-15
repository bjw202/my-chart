import client from './client'
import type { SectorInfo } from '../types/stock'
import type { SectorDetailResponse } from '../types/sector'

export async function fetchSectors(): Promise<SectorInfo[]> {
  const response = await client.get<SectorInfo[]>('/sectors')
  return response.data
}

export async function fetchSectorDetail(sectorName: string): Promise<SectorDetailResponse> {
  const encoded = encodeURIComponent(sectorName)
  const response = await client.get<SectorDetailResponse>(`/sectors/${encoded}/detail`)
  return response.data
}
