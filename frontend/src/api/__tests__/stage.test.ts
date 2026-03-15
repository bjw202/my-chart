// RED: Tests for stage API function
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { StageOverviewResponse } from '../../types/stage'

// Mock axios client
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
  },
}))

import client from '../client'
import { fetchStageOverview } from '../stage'

const mockResponse: StageOverviewResponse = {
  distribution: { stage1: 120, stage2: 85, stage3: 45, stage4: 30, total: 280 },
  by_sector: [{ sector: 'IT', stage1: 10, stage2: 15, stage3: 5, stage4: 2 }],
  stage2_candidates: [
    {
      code: '005930',
      name: '삼성전자',
      market: 'KOSPI',
      sector_major: 'IT',
      sector_minor: '반도체',
      stage: 2,
      stage_detail: 'Stage 2 Strong',
      rs_12m: 75.5,
      chg_1m: 3.2,
      volume_ratio: 1.5,
      close: 75000,
      sma50: 72000,
      sma200: 68000,
    },
  ],
}

describe('fetchStageOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should call GET /stage/overview', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockResponse })

    await fetchStageOverview()

    expect(client.get).toHaveBeenCalledWith('/stage/overview')
  })

  it('should return the response data', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockResponse })

    const result = await fetchStageOverview()

    expect(result).toEqual(mockResponse)
    expect(result.distribution.total).toBe(280)
    expect(result.stage2_candidates).toHaveLength(1)
  })

  it('should propagate errors from the API', async () => {
    vi.mocked(client.get).mockRejectedValue(new Error('Network error'))

    await expect(fetchStageOverview()).rejects.toThrow('Network error')
  })
})
