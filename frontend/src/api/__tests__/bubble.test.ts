// RED: 버블 API 가 market 을 실제 요청 파라미터로 실어 보내는지 — 인자 통과가 아니라 전송값을 단언한다.
// 배경: fetchStockBubble 에 market 파라미터 자체가 없어, 종목 버블 뷰에서 시장 토글이 무동작이었다.
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../client', () => ({
  default: { get: vi.fn() },
}))

import client from '../client'
import { fetchSectorBubble, fetchStockBubble } from '../bubble'

const mockGet = vi.mocked(client.get)

// 요청 1건의 (url, params) 를 뽑아낸다.
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

describe('fetchStockBubble — market 전송', () => {
  it.each(['all', 'kospi', 'kosdaq'])('market="%s" 가 요청 파라미터로 전달된다', async market => {
    await fetchStockBubble('반도체', '1m', market)
    const { url, params } = lastRequest()
    expect(url).toBe('/sectors/%EB%B0%98%EB%8F%84%EC%B2%B4/bubble')
    expect(params).toEqual({ period: '1m', market })
  })

  it('시장이 바뀌면 전송되는 market 값도 바뀐다 (드릴다운 뷰 토글 무동작 회귀 가드)', async () => {
    await fetchStockBubble('반도체', '1m', 'all')
    const first = lastRequest().params.market
    await fetchStockBubble('반도체', '1m', 'kospi')
    const second = lastRequest().params.market
    expect(first).toBe('all')
    expect(second).toBe('kospi')
    expect(second).not.toBe(first)
  })
})

describe('fetchSectorBubble — market 전송 (소문자 3값 단일 규약)', () => {
  it.each(['all', 'kospi', 'kosdaq'])('market="%s" 가 요청 파라미터로 전달된다', async market => {
    await fetchSectorBubble('1m', market)
    const { url, params } = lastRequest()
    expect(url).toBe('/sectors/bubble')
    expect(params).toEqual({ period: '1m', market })
  })
})
