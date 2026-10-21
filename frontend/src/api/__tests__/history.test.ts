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
})
