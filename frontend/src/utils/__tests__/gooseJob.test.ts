/**
 * SPEC-AI-REPORT-004 M6 — goose 작업 저장 키(design §7.1)와 진행 단계 누적(design §3.5) 시험.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  GOOSE_JOB_STARTED_EVENT,
  GOOSE_STAGES,
  applyGooseStage,
  clearGooseJob,
  gooseJobKey,
  makeInitialGooseProgress,
  readGooseJob,
  saveGooseJob,
} from '../gooseJob'

describe('goose 작업 저장 키 (sessionStorage goose_job:{code})', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('키 이름은 goose_job:{code}이고 값은 job_id다', () => {
    expect(gooseJobKey('299030')).toBe('goose_job:299030')
    saveGooseJob('299030', 'J1')
    expect(sessionStorage.getItem('goose_job:299030')).toBe('J1')
    expect(readGooseJob('299030')).toBe('J1')
    expect(readGooseJob('005930')).toBeNull()
  })

  it('저장하면 같은 탭 셀이 알 수 있도록 goose-job-started 이벤트를 보낸다', () => {
    const listener = vi.fn()
    window.addEventListener(GOOSE_JOB_STARTED_EVENT, listener)
    saveGooseJob('299030', 'J2')
    window.removeEventListener(GOOSE_JOB_STARTED_EVENT, listener)
    expect(GOOSE_JOB_STARTED_EVENT).toBe('goose-job-started')
    expect(listener).toHaveBeenCalledTimes(1)
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({ code: '299030', jobId: 'J2' })
  })

  it('지울 때 job_id가 다르면(새 작업이 저장됨) 지우지 않는다', () => {
    saveGooseJob('299030', 'J2')
    clearGooseJob('299030', 'J1')
    expect(readGooseJob('299030')).toBe('J2')
    clearGooseJob('299030', 'J2')
    expect(readGooseJob('299030')).toBeNull()
  })
})

describe('goose 진행 단계 누적 (design §3.5 측정 표)', () => {
  it('단계 11개를 순서대로 가진다 — 공시 원문 수집(dart_prefetch)이 맨 앞(SPEC-AI-REPORT-005)', () => {
    expect(GOOSE_STAGES[0]).toBe('dart_prefetch')
    expect(GOOSE_STAGES).toEqual([
      'dart_prefetch',
      'goose_start',
      'plan',
      'research_tick',
      'fetch_start',
      'fetch_done',
      'compose',
      'render_draft',
      'audit',
      'render_final',
      'session_end',
    ])
  })

  it('도달한 단계를 한 번씩 기록하고 검색·열람 횟수를 센다', () => {
    let p = makeInitialGooseProgress()
    for (const stage of ['goose_start', 'plan', 'research_tick', 'research_tick', 'fetch_start', 'fetch_done']) {
      p = applyGooseStage(p, { stage, detail: stage === 'fetch_start' ? '네이버 금융 원문' : null })
    }
    expect(p.reached).toEqual(['goose_start', 'plan', 'research_tick', 'fetch_start', 'fetch_done'])
    expect(p.researchTicks).toBe(2)
    expect(p.fetchStarted).toBe(1)
    expect(p.fetchDone).toBe(1)
    expect(p.lastFetch).toBe('네이버 금융 원문')
  })

  it('dart_prefetch 단계를 도달 목록에 넣는다(SPEC-AI-REPORT-005 AC-AIR5-003)', () => {
    let p = makeInitialGooseProgress()
    p = applyGooseStage(p, { stage: 'dart_prefetch', detail: null })
    p = applyGooseStage(p, { stage: 'goose_start', detail: null })
    expect(p.reached).toEqual(['dart_prefetch', 'goose_start'])
  })

  it('알 수 없는 단계는 무시한다(파서 불변 조건과 같은 태도)', () => {
    const p = makeInitialGooseProgress()
    expect(applyGooseStage(p, { stage: 'role_start', detail: null })).toBe(p)
  })
})
