/**
 * SPEC-AI-REPORT-004 M6 — goose 작업 API 클라이언트 시험.
 *
 * 실제 네트워크 없음: fetch와 EventSource를 가짜로 바꾼다(B3).
 * 백엔드 계약(routers/ai_report.py): POST /ai-report/{code}?mode=deep → 202/200 {job_id},
 * 429 {detail: {error: goose_busy, detail}} (하루 횟수 제한 없음 — 2026-10-21), SSE 이벤트 progress/done/error/cancelled,
 * 없는 작업 404, POST /ai-report/jobs/{id}/cancel, GET /ai-report/goose/active.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('../client', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

import client from '../client'
import {
  cancelGooseJob,
  fetchGooseActive,
  gooseReportUrl,
  startGooseJob,
  subscribeGooseJob,
} from '../aiReport'

// ── 가짜 EventSource ─────────────────────────────────────────────────────────

type Listener = (ev: MessageEvent) => void

class FakeEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2
  static instances: FakeEventSource[] = []
  url: string
  readyState = FakeEventSource.CONNECTING
  onerror: ((ev: Event) => void) | null = null
  listeners: Record<string, Listener[]> = {}
  closed = false

  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, fn: Listener) {
    ;(this.listeners[type] ??= []).push(fn)
  }

  close() {
    this.closed = true
    this.readyState = FakeEventSource.CLOSED
  }

  emit(type: string, data: unknown) {
    for (const fn of this.listeners[type] ?? []) {
      fn(new MessageEvent(type, { data: JSON.stringify(data) }))
    }
  }

  fail(readyState: number) {
    this.readyState = readyState
    this.onerror?.(new Event('error'))
  }
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('startGooseJob — 작업 시작 응답 해석', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('202 새 작업과 200 기존 작업은 모두 job_id를 돌려준다', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(202, { job_id: 'J1' }))
    expect(await startGooseJob('299030')).toEqual({ ok: true, jobId: 'J1' })
    expect(fetchMock).toHaveBeenCalledWith('/api/ai-report/299030?mode=deep', { method: 'POST' })
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { job_id: 'J1' }))
    expect(await startGooseJob('299030')).toEqual({ ok: true, jobId: 'J1' })
  })

  it('429 goose_busy는 서버 안내(실행 중 종목명 포함)를 그대로 쓴다', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(429, { detail: { error: 'goose_busy', detail: '하나기술 분석이 진행 중입니다' } }),
    )
    expect(await startGooseJob('005930')).toEqual({
      ok: false,
      error: 'goose_busy',
      message: '하나기술 분석이 진행 중입니다',
    })
  })

  it('본문이 없는 429 goose_busy도 기본 안내를 만든다', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(429, { detail: { error: 'goose_busy' } }))
    const busy = await startGooseJob('005930')
    expect(busy).toMatchObject({ ok: false, error: 'goose_busy' })
    expect(busy.ok === false && busy.message).toContain('분석이 진행 중입니다')
  })

  it('하루 횟수 제한 안내 문구는 더 이상 없다(알 수 없는 오류는 일반 안내)', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(429, { detail: { error: 'goose_rate_limit' } }))
    const rate = await startGooseJob('005930')
    expect(rate.ok === false && rate.message).not.toContain('일일 한도')
    expect(rate.ok === false && rate.message).toContain('HTTP 429')
  })

  it('그 밖의 실패(503·네트워크)는 오류로 돌려준다', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(503, { detail: { error: 'claude_cli_missing', detail: 'claude CLI가 설치되지 않아' } }),
    )
    expect(await startGooseJob('005930')).toEqual({
      ok: false,
      error: 'claude_cli_missing',
      message: 'claude CLI가 설치되지 않아',
    })
    fetchMock.mockRejectedValueOnce(new Error('network down'))
    expect(await startGooseJob('005930')).toEqual({ ok: false, error: 'network', message: 'network down' })
  })
})

describe('subscribeGooseJob — EventSource 구독', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function setup() {
    const handlers = { onProgress: vi.fn(), onTerminal: vi.fn(), onLost: vi.fn() }
    const unsubscribe = subscribeGooseJob('J1', handlers)
    const es = FakeEventSource.instances[0]
    return { handlers, unsubscribe, es }
  }

  it('작업 이벤트 URL로 EventSource를 1개 연다', () => {
    const { es } = setup()
    expect(FakeEventSource.instances).toHaveLength(1)
    expect(es.url).toBe('/api/ai-report/jobs/J1/events')
  })

  it('progress 이벤트를 {stage, detail}로 전달한다', () => {
    const { handlers, es } = setup()
    es.emit('progress', { stage: 'plan', detail: null })
    expect(handlers.onProgress).toHaveBeenCalledWith({ stage: 'plan', detail: null })
  })

  it.each(['done', 'error', 'cancelled'] as const)(
    '종료 이벤트 %s는 데이터를 전달하고 연결을 닫는다(서버가 닫은 뒤 자동 재접속 방지)',
    (type) => {
      const { handlers, es } = setup()
      const data = { run: '2026-10-20', delivery_status: 'draft', report_url: '/api/x', interrupted: true }
      es.emit(type, data)
      expect(handlers.onTerminal).toHaveBeenCalledWith(type, data)
      expect(es.closed).toBe(true)
    },
  )

  it('연결이 닫힌 오류(404 등)는 작업을 잃은 것으로 알리고, 재접속 중 오류는 기다린다', () => {
    const { handlers, es } = setup()
    es.fail(FakeEventSource.CONNECTING)
    expect(handlers.onLost).not.toHaveBeenCalled()
    expect(es.closed).toBe(false)
    es.fail(FakeEventSource.CLOSED)
    expect(handlers.onLost).toHaveBeenCalledTimes(1)
    expect(es.closed).toBe(true)
  })

  it('구독 해제는 연결만 닫고 이후 이벤트를 전달하지 않는다', () => {
    const { handlers, unsubscribe, es } = setup()
    unsubscribe()
    expect(es.closed).toBe(true)
    es.emit('progress', { stage: 'plan', detail: null })
    expect(handlers.onProgress).not.toHaveBeenCalled()
  })

  it('깨진 JSON 데이터는 무시한다', () => {
    const { handlers, es } = setup()
    for (const fn of es.listeners['progress'] ?? []) fn(new MessageEvent('progress', { data: '{oops' }))
    expect(handlers.onProgress).not.toHaveBeenCalled()
  })
})

describe('취소·실행 중 작업 조회·리포트 URL', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
  })

  it('cancelGooseJob은 취소 경로로 POST한다', async () => {
    vi.mocked(client.post).mockResolvedValueOnce({ data: { job_id: 'J1', status: 'cancelled' } })
    await cancelGooseJob('J1')
    expect(client.post).toHaveBeenCalledWith('/ai-report/jobs/J1/cancel')
  })

  it('fetchGooseActive는 실행 중 작업 또는 null을 돌려준다', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { job_id: 'J1', code: '299030', stock_name: '하나기술', status: 'running' },
    })
    expect(await fetchGooseActive()).toEqual({
      job_id: 'J1',
      code: '299030',
      stock_name: '하나기술',
      status: 'running',
    })
    expect(client.get).toHaveBeenCalledWith('/ai-report/goose/active')
    vi.mocked(client.get).mockResolvedValueOnce({ data: null })
    expect(await fetchGooseActive()).toBeNull()
  })

  it('gooseReportUrl은 백엔드 report_url과 같은 모양이다', () => {
    expect(gooseReportUrl('299030', '2026-10-19_2')).toBe(
      '/api/ai-report/299030/goose/2026-10-19_2/report.html',
    )
  })
})
