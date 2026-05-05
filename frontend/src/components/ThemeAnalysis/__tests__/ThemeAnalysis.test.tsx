// RED: ThemeAnalysis — V2 503 에러 메시지 + retry 버튼 검증 (SPEC-NAVER-THEME-003 AC-11, AC-12)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { ThemeAnalysis } from '../ThemeAnalysis'

// axios client mock — api client 모듈 경로 기준 (컴포넌트에서는 ../../api/client 참조)
vi.mock('../../../api/client', () => ({
  default: {
    get: vi.fn(),
  },
}))

import client from '../../../api/client'

// 정상 응답 mock 데이터 (retry 성공 시나리오용)
const mockOkResponse = {
  data: {
    themes: [],
    strong_themes: [],
    metadata: {
      collected_at: '2026-05-06T00:00:00+00:00',
      theme_count: 0,
      stock_count: 0,
      elapsed_sec: 0.5,
      errors: [],
    },
  },
}

// 503 에러 mock
const mock503Error = { response: { status: 503 }, message: 'Service Unavailable' }

describe('ThemeAnalysis — V2 503 에러 처리 (AC-11)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows error message + retry button on V2 503', async () => {
    // 503으로 계속 실패하도록 mock
    vi.mocked(client.get).mockRejectedValue(mock503Error)

    render(<ThemeAnalysis />)

    await waitFor(() => {
      // 에러 메시지 텍스트 존재 (AC-11)
      expect(screen.getByText(/테마 데이터를 가져오지 못했습니다/i)).toBeTruthy()
      // retry 버튼 존재
      const retryBtn = screen.getByRole('button', { name: /다시 시도|retry/i })
      expect(retryBtn).toBeTruthy()
    })

    // V1 endpoint 자동 폴백 호출 부재 검증 (REQ-NT3-C-006)
    const calls = vi.mocked(client.get).mock.calls
    const v1Calls = calls.filter(([url]) => url === '/themes/snapshot' || url === '/themes/quick')
    expect(v1Calls.length).toBe(0)
  })
})

describe('ThemeAnalysis — retry 버튼 V2 재호출 (AC-12)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('retry button triggers V2 endpoint re-fetch', async () => {
    // 첫 번째 호출: 503 실패
    vi.mocked(client.get).mockRejectedValueOnce(mock503Error)

    render(<ThemeAnalysis />)

    // 에러 상태 + retry 버튼 대기
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /다시 시도|retry/i })).toBeTruthy()
    })

    // 두 번째 호출(retry): 200 성공으로 mock 교체
    vi.mocked(client.get).mockResolvedValueOnce(mockOkResponse)

    // retry 버튼 클릭
    fireEvent.click(screen.getByRole('button', { name: /다시 시도|retry/i }))

    await waitFor(() => {
      // V2 endpoint 추가 호출 검증 (총 2회 이상 — 첫 503 + retry)
      const calls = vi.mocked(client.get).mock.calls
      const v2Calls = calls.filter(([url]) => typeof url === 'string' && url.startsWith('/themes/v2/'))
      expect(v2Calls.length).toBeGreaterThanOrEqual(2)
    })
  })
})
