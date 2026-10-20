/**
 * SPEC-AI-REPORT-004 M6 — 셀 AI 버튼의 goose 활성 표시 (design §7.2, AC-AIR4-022).
 *
 * SSE 구독은 모달 안에서만 쓰고, 셀은 가벼운 조회(GET /ai-report/goose/active)로 상태를 안다.
 * - 같은 탭 저장 키 `goose_job:{code}`가 없으면 폴링하지 않는다.
 * - 있으면(J) 즉시 1회, 이후 주기마다 조회. 응답 job_id가 J면 활성, null이거나 다른 job_id면
 *   비활성으로 바꾸고 폴링을 멈춘다(저장값 삭제는 모달이 결과를 보여 준 뒤 한다).
 * - 같은 탭에서 새 작업을 시작하면 `goose-job-started` 신호로 폴링을 다시 시작한다.
 */
import { useEffect, useState } from 'react'
import { fetchGooseActive } from '../api/aiReport'
import { GOOSE_JOB_STARTED_EVENT, readGooseJob, type GooseJobStartedDetail } from '../utils/gooseJob'

/** 폴링 주기 (design §7.2 "기본 5초, 구현 단계에서 확정") */
export const GOOSE_ACTIVE_POLL_MS = 5000

export function useGooseActive(code: string, intervalMs: number = GOOSE_ACTIVE_POLL_MS): boolean {
  const [jobId, setJobId] = useState<string | null>(() => readGooseJob(code))
  // 서버가 실행 중이라고 확인해 준 job_id
  const [confirmed, setConfirmed] = useState<string | null>(null)

  useEffect(() => {
    const onStarted = (e: Event) => {
      const detail = (e as CustomEvent<GooseJobStartedDetail>).detail
      if (detail?.code === code) setJobId(detail.jobId)
    }
    window.addEventListener(GOOSE_JOB_STARTED_EVENT, onStarted)
    return () => window.removeEventListener(GOOSE_JOB_STARTED_EVENT, onStarted)
  }, [code])

  // @MX:WARN: [AUTO] 주기 폴링 타이머 — 정리 함수가 타이머를 지워야 셀이 사라진 뒤 요청이 남지 않는다.
  // @MX:REASON: 작업이 끝나면(null 또는 다른 job_id) 스스로 멈춘다. 모든 셀이 폴링하면 셀 수만큼
  //             요청이 생기므로 저장 키가 있는 셀만 폴링한다(AC-022 (3)(5)).
  useEffect(() => {
    if (!jobId) return
    let stopped = false
    const poll = async () => {
      try {
        const active = await fetchGooseActive()
        if (stopped) return
        if (active && active.job_id === jobId) {
          setConfirmed(jobId)
        } else {
          setConfirmed(null)
          stop()
        }
      } catch {
        // 일시적인 조회 실패 — 다음 주기에 다시 묻는다
      }
    }
    const timer = setInterval(() => void poll(), intervalMs)
    function stop() {
      stopped = true
      clearInterval(timer)
    }
    void poll()
    return stop
  }, [jobId, intervalMs])

  return jobId !== null && confirmed === jobId
}
