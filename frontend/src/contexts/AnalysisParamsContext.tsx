// AnalysisParamsContext — 02-screen-flow.md §3.3 상태 소유권 표의 계약 본체.
// market / period (사용자 제어) + asOfDate / asOfIsPartialWeek / gridVersion (읽기 전용, 서버 응답 기록 전용).
import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'

// 기간 값 단일화 (D5 / CT-12 / AC-SUX-009) — 상태는 '1w'|'1m'|'3m' 만 사용.
// 응답 스키마 키(w1/m1/m3)는 변환 계층에서 흡수한다 (별개 축).
export type Period = '1w' | '1m' | '3m'

// 시장 값 — 백엔드 전송 필터 all/kospi/kosdaq (소문자, 01-data-contract.md §8 / §3.3).
export type Market = 'all' | 'kospi' | 'kosdaq'

// 공개 읽기/쓰기 계약 — UI 소비자가 사용 (AC-SUX-001).
export interface AnalysisParamsValue {
  // 사용자 제어 필드 (토글이 쓴다)
  market: Market
  period: Period
  setMarket: (m: Market) => void
  setPeriod: (p: Period) => void
  // 읽기 전용 필드 — 서버 응답 기록 전용 내부 경로로만 갱신 (AC-SUX-001: 쓰기 API 비노출)
  asOfDate: string | null
  asOfIsPartialWeek: boolean
  gridVersion: string | null
}

// 내부 기록 계약 — 데이터 적재 경로(M6)가 사용. UI 소비자에게는 노출되지 않는다.
export interface AnalysisParamsRecorder {
  recordAsOf: (date: string | null, isPartialWeek: boolean, gridVer: string | null) => void
}

// @MX:ANCHOR: [AUTO] AnalysisParamsContext — 02 §3.3 상태 소유권 표. market/period 사용자 제어, asOf*·gridVersion 읽기전용
// @MX:REASON: 섹터 4탭 + Stock Explorer 전역 파라미터 단일 출처; 읽기전용 필드의 UI 쓰기 금지 계약 (fan_in >= 5 화면 소비 예정)
const AnalysisParamsContext = createContext<AnalysisParamsValue | null>(null)
const RecorderContext = createContext<AnalysisParamsRecorder | null>(null)

export function AnalysisParamsProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  // 사용자 제어 (초기값 — §3.3 소유권 표)
  const [market, setMarket] = useState<Market>('all')
  const [period, setPeriod] = useState<Period>('1m')
  // 읽기 전용 — 서버 응답 기록 전용 내부 경로(recordAsOf)로만 갱신 (AC-SUX-001)
  const [asOfDate, setAsOfDate] = useState<string | null>(null)
  const [asOfIsPartialWeek, setAsOfIsPartialWeek] = useState(false)
  const [gridVersion, setGridVersion] = useState<string | null>(null)

  // 서버 응답 기록 전용 내부 경로 — UI(useAnalysisParams)에는 노출되지 않는다 (AC-SUX-001 읽기전용 계약).
  // M6 데이터 적재 훅이 호출한다. M1-M5 에는 호출자가 없어도 계약은 존재한다.
  const recordAsOf = useCallback(
    (date: string | null, isPartialWeek: boolean, gridVer: string | null) => {
      setAsOfDate(date)
      setAsOfIsPartialWeek(isPartialWeek)
      setGridVersion(gridVer)
    },
    [],
  )

  // 공개 value — 읽기전용 필드의 setter 를 포함하지 않는다 (useMemo 안정화 — §3.4 리렌더 범위 통제).
  const value = useMemo<AnalysisParamsValue>(
    () => ({
      market,
      period,
      setMarket,
      setPeriod,
      asOfDate,
      asOfIsPartialWeek,
      gridVersion,
    }),
    [market, period, asOfDate, asOfIsPartialWeek, gridVersion],
  )

  const recorder = useMemo<AnalysisParamsRecorder>(() => ({ recordAsOf }), [recordAsOf])

  return (
    <AnalysisParamsContext.Provider value={value}>
      <RecorderContext.Provider value={recorder}>{children}</RecorderContext.Provider>
    </AnalysisParamsContext.Provider>
  )
}

// UI 소비자용 — 읽기전용 필드는 읽기만 가능 (setter 비노출, AC-SUX-001).
export function useAnalysisParams(): AnalysisParamsValue {
  const ctx = useContext(AnalysisParamsContext)
  if (!ctx) throw new Error('useAnalysisParams must be used within AnalysisParamsProvider')
  return ctx
}

// 데이터 적재 경로용 — 읽기전용 필드의 서버 응답 기록 (M6+).
export function useAnalysisParamsRecorder(): AnalysisParamsRecorder {
  const ctx = useContext(RecorderContext)
  if (!ctx) throw new Error('useAnalysisParamsRecorder must be used within AnalysisParamsProvider')
  return ctx
}
