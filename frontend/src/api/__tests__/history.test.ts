// Bump 히스토리 API 가 표와 같은 기준(기간·시장)을 실제 요청 파라미터로 실어 보내는지 — 전송값을 단언한다.
// 배경(2026-10-21): fetchSectorHistory 가 weeks 만 보내 Bump 가 표의 기간·시장 토글과 무관하게
// composite·전체 시장 기준으로 그려졌다.
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../client', () => ({
  default: { get: vi.fn() },
}))

import client from '../client'
import { fetchSectorHistory } from '../history'

const mockGet = vi.mocked(client.get)

function lastRequest(): { url: string; params: Record<string, unknown> } {
  const call = mockGet.mock.calls[mockGet.mock.calls.length - 1]
  return {
    url: call[0] as string,
    params: ((call[1] as { params?: Record<string, unknown> })?.params ?? {}),
  }
}

beforeEach(() => {
  mockGet.mockReset()
  mockGet.mockResolvedValue({ data: {} } as never)
})

describe('fetchSectorHistory — 표와 같은 기준 전송', () => {
  it('period·market 이 요청 파라미터로 전달된다', async () => {
    await fetchSectorHistory(12, { period: '3m', market: 'kospi' })
    const { url, params } = lastRequest()
    expect(url).toBe('/sectors/history')
    expect(params).toEqual({ weeks: 12, period: '3m', market: 'kospi' })
  })

  it('기준을 주지 않으면 weeks 만 보낸다 (서버 기본 = composite·전체)', async () => {
    await fetchSectorHistory(8)
    expect(lastRequest().params).toStrictEqual({ weeks: 8 })
  })

  it('잠정점 필드(provisional_date·history[].provisional)를 가공 없이 돌려준다', async () => {
    const body = {
      weeks: 1,
      provisional_date: '2026-10-21',
      sectors: [{
        name: '반도체',
        history: [
          { date: '2026-10-16', rank: 2, composite_score: 0, sector_return_1w: 0, sector_excess_return_1w: 0, rs_avg: 0, provisional: false },
          { date: '2026-10-21', rank: 1, composite_score: 0, sector_return_1w: 0, sector_excess_return_1w: 0, rs_avg: 0, provisional: true },
        ],
      }],
    }
    mockGet.mockResolvedValue({ data: body } as never)
    const res = await fetchSectorHistory(1, { period: '1m' })
    expect(res.provisional_date).toBe('2026-10-21')
    expect(res.sectors[0].history.map(w => w.provisional)).toEqual([false, true])
  })
})
