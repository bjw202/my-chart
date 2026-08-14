// 데이터 적재 계층 — SPEC-SECTOR-UX-001 M6 / D1·D4 / 규칙 LD-A~LD-E
// (AC-SUX-033 조회 시점 · 034 TTL · 035 stale-but-showing · 036 재시도/새로고침 · 037 기준일 합치)
//
// D1/D4 [HARD]: 외부 상태·캐시 라이브러리를 도입하지 않는다. React Context + useState +
// M1 에서 만든 QueryCache(Map + TTL) 만 사용한다. MarketContext 의 기존 패턴(TTL + refresh()
// + 2/4/8초 지수 백오프)을 전 엔드포인트로 확산하는 것이 목적이다 (Lesson #5).
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { QueryCache } from './queryCache'
import { useAnalysisParamsRecorder } from './AnalysisParamsContext'

// 백엔드 미응답 시 자동 재시도 간격 — MarketContext.RETRY_DELAYS_MS 와 같은 계약 (§1.2 보존 8).
export const RETRY_DELAYS_MS = [2000, 4000, 8000]

// 쿼리 키 — 엔드포인트 + 파라미터 조합. 파라미터 순서에 무관하게 같은 키를 낸다.
export function buildQueryKey(endpoint: string, params: Record<string, string | number | boolean | null | undefined> = {}): string {
  const parts = Object.keys(params)
    .sort()
    .map(k => `${k}=${params[k] ?? ''}`)
  return parts.length > 0 ? `${endpoint}?${parts.join('&')}` : endpoint
}

// 응답 봉투에서 뽑아내는 메타 — 기준일·진행중 주·격자 버전 (01 §7.1 SN-3/SN-4/SN-5).
export interface QueryMeta {
  asOfDate: string | null
  asOfIsPartialWeek: boolean
  gridVersion: string | null
}

interface AsOfEntry { panel: string; date: string }

interface DataLoadContextValue {
  cache: QueryCache<unknown>
  // refreshTick 이 바뀌면 마운트된 모든 useQuery 가 재조회한다 (수동 새로고침 / grid_version 무효화).
  refreshTick: number
  refreshAll: () => void
  registerAsOf: (panel: string, date: string | null) => void
  unregisterAsOf: (panel: string) => void
  asOfEntries: AsOfEntry[]
  // grid_version 변경 감지 → 캐시 통째로 비우고 전 화면 재조회 (SN-5).
  noteGridVersion: (version: string | null) => void
}

const DataLoadContext = createContext<DataLoadContextValue | null>(null)

// @MX:ANCHOR: [AUTO] DataLoadProvider — 전 엔드포인트 공용 조회 계층(TTL 캐시 + 재시도 + 기준일 레지스트리)
// @MX:REASON: 섹터 4탭 + 종목 탐색 + 상세 패널이 모두 useQuery 로 이 계층을 소비한다(fan_in >= 5).
//   TTL·백오프·기준일 합치 판정이 화면마다 갈리면 SN-3 불변식이 클라이언트에서 깨진다.
export function DataLoadProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  // 렌더 중(useMemo value 구성)에 읽어야 하므로 ref 가 아니라 lazy state 로 보관한다.
  const [cache] = useState<QueryCache<unknown>>(() => new QueryCache<unknown>())
  const [refreshTick, setRefreshTick] = useState(0)
  const [asOfMap, setAsOfMap] = useState<Record<string, string>>({})
  const gridVersionRef = useRef<string | null>(null)
  // 이미 무효화를 수행한 버전 집합 — 두 패널이 서로 다른 grid_version 을 번갈아 보고할 때
  // 무한 재조회 핑퐁이 생기지 않도록 버전당 1회로 무효화를 제한한다.
  const invalidatedVersionsRef = useRef<Set<string>>(new Set())

  const refreshAll = useCallback(() => {
    cache.clear()
    setRefreshTick(t => t + 1)
  }, [cache])

  const registerAsOf = useCallback((panel: string, date: string | null) => {
    setAsOfMap(prev => {
      if (date == null) {
        if (!(panel in prev)) return prev
        const next = { ...prev }
        delete next[panel]
        return next
      }
      if (prev[panel] === date) return prev
      return { ...prev, [panel]: date }
    })
  }, [])

  const unregisterAsOf = useCallback((panel: string) => {
    setAsOfMap(prev => {
      if (!(panel in prev)) return prev
      const next = { ...prev }
      delete next[panel]
      return next
    })
  }, [])

  // SN-5: 격자 규칙이 바뀌면(grid_version 변경) 캐시된 전 응답이 무효다 → 통째로 비우고 재조회.
  const noteGridVersion = useCallback((version: string | null) => {
    if (version == null) return
    const prev = gridVersionRef.current
    gridVersionRef.current = version
    cache.setGridVersion(version)
    if (prev !== null && prev !== version && !invalidatedVersionsRef.current.has(version)) {
      invalidatedVersionsRef.current.add(version)
      setRefreshTick(t => t + 1)
    }
  }, [cache])

  const asOfEntries = useMemo(
    () => Object.entries(asOfMap).map(([panel, date]) => ({ panel, date })),
    [asOfMap],
  )

  const value = useMemo<DataLoadContextValue>(
    () => ({
      cache,
      refreshTick,
      refreshAll,
      registerAsOf,
      unregisterAsOf,
      asOfEntries,
      noteGridVersion,
    }),
    [cache, refreshTick, refreshAll, registerAsOf, unregisterAsOf, asOfEntries, noteGridVersion],
  )

  return <DataLoadContext.Provider value={value}>{children}</DataLoadContext.Provider>
}

function useDataLoad(): DataLoadContextValue {
  const ctx = useContext(DataLoadContext)
  if (!ctx) throw new Error('useQuery/useDataRefresh must be used within DataLoadProvider')
  return ctx
}

// 수동 새로고침 — `⟳ 새로고침` 버튼이 소비 (AC-SUX-036).
export function useDataRefresh(): { refreshAll: () => void } {
  const { refreshAll } = useDataLoad()
  return useMemo(() => ({ refreshAll }), [refreshAll])
}

// 기준일 합치 검증 — 두 패널의 as_of_date 가 다르면 충돌 (AC-SUX-037 / SN-3 클라이언트 측).
export interface AsOfCoherence {
  conflict: { panels: string[]; dates: string[] } | null
}

export function useAsOfCoherence(): AsOfCoherence {
  const { asOfEntries } = useDataLoad()
  return useMemo(() => {
    const dates = [...new Set(asOfEntries.map(e => e.date))]
    if (dates.length <= 1) return { conflict: null }
    return { conflict: { panels: asOfEntries.map(e => e.panel), dates } }
  }, [asOfEntries])
}

export interface QueryOptions<T> {
  // 화면이 활성일 때만 true — 비활성 탭은 fetch 하지 않는다 (AC-SUX-033).
  enabled?: boolean
  // 기준일 레지스트리 키 (AC-SUX-037 충돌 보고에 패널명으로 노출된다).
  panel: string
  meta?: (data: T) => QueryMeta
  // 테스트에서 백오프를 끄기 위한 주입점. 기본은 2/4/8초.
  retryDelays?: number[]
}

export interface QueryResult<T> {
  data: T | null
  // 표시할 데이터가 없는 최초 로딩.
  loading: boolean
  // 표시 중인 데이터를 유지한 채 진행되는 재조회 (LD-C stale-but-showing).
  refetching: boolean
  error: string | null
  // 자동 재시도 3회를 모두 소진한 상태 — [다시 시도] 버튼 노출 조건 (AC-SUX-036).
  retryExhausted: boolean
  // 재조회 실패 시 "표시 중인 데이터"의 기준일 (AC-SUX-035 실패 띠 문구).
  staleAsOf: string | null
  asOfDate: string | null
  asOfIsPartialWeek: boolean
  retry: () => void
}

interface InternalState<T> {
  data: T | null
  loading: boolean
  refetching: boolean
  error: string | null
  retryExhausted: boolean
  asOfDate: string | null
  asOfIsPartialWeek: boolean
}

export function useQuery<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  options: QueryOptions<T>,
): QueryResult<T> {
  const { enabled = true, panel, meta, retryDelays = RETRY_DELAYS_MS } = options
  const { cache, refreshTick, registerAsOf, unregisterAsOf, noteGridVersion } = useDataLoad()
  const { recordAsOf } = useAnalysisParamsRecorder()

  const [state, setState] = useState<InternalState<T>>({
    data: null,
    loading: false,
    refetching: false,
    error: null,
    retryExhausted: false,
    asOfDate: null,
    asOfIsPartialWeek: false,
  })

  // 수동 [다시 시도] 트리거 — refreshTick 과 독립적으로 이 훅만 재조회한다.
  const [retryTick, setRetryTick] = useState(0)
  const retry = useCallback(() => setRetryTick(t => t + 1), [])

  // 조회 정체성의 단일 출처는 key 다. fetcher/meta/retryDelays/recordAsOf 는 렌더마다
  // identity 가 바뀔 수 있어(인라인 화살표·배열 리터럴·테스트 mock) effect dep 에 넣으면
  // 무한 재조회가 된다. ref 에 최신값만 실어 두고 조회 effect 안에서 읽는다.
  // 쓰기는 렌더 중이 아니라 commit 후(effect)에 한다 — 아래 조회 effect 보다 먼저 선언되어
  // 같은 commit 에서 항상 먼저 실행된다.
  const fetcherRef = useRef(fetcher)
  const metaRef = useRef(meta)
  const retryDelaysRef = useRef(retryDelays)
  const recordAsOfRef = useRef(recordAsOf)
  useEffect(() => {
    fetcherRef.current = fetcher
    metaRef.current = meta
    retryDelaysRef.current = retryDelays
    recordAsOfRef.current = recordAsOf
  })

  useEffect(() => {
    if (!enabled || !key) return
    let cancelled = false
    const timers: ReturnType<typeof setTimeout>[] = []

    const applyMeta = (data: T): { date: string | null; partial: boolean } => {
      const m = metaRef.current?.(data)
      if (!m) return { date: null, partial: false }
      registerAsOf(panel, m.asOfDate)
      recordAsOfRef.current(m.asOfDate, m.asOfIsPartialWeek, m.gridVersion)
      noteGridVersion(m.gridVersion)
      return { date: m.asOfDate, partial: m.asOfIsPartialWeek }
    }

    // TTL 내 캐시 적중 — fetch 없이 즉시 반영 (AC-SUX-033 재활성화 / AC-SUX-034 59분).
    const cached = cache.get(key) as T | undefined
    if (cached !== undefined) {
      const m = metaRef.current?.(cached)
      if (m) registerAsOf(panel, m.asOfDate)
      setState(prev => ({
        ...prev,
        data: cached,
        loading: false,
        refetching: false,
        error: null,
        retryExhausted: false,
        asOfDate: m?.asOfDate ?? prev.asOfDate,
        asOfIsPartialWeek: m?.asOfIsPartialWeek ?? prev.asOfIsPartialWeek,
      }))
      return
    }

    // LD-C: 표시 중인 데이터가 있으면 refetching(유지), 없으면 loading(최초).
    setState(prev => ({
      ...prev,
      loading: prev.data === null,
      refetching: prev.data !== null,
      error: null,
      retryExhausted: false,
    }))

    const attempt = (n: number): void => {
      fetcherRef.current()
        .then(data => {
          if (cancelled) return
          cache.set(key, data)
          const { date, partial } = applyMeta(data)
          setState(prev => ({
            ...prev,
            data,
            loading: false,
            refetching: false,
            error: null,
            retryExhausted: false,
            asOfDate: date ?? prev.asOfDate,
            asOfIsPartialWeek: partial,
          }))
        })
        .catch((e: unknown) => {
          if (cancelled) return
          const delays = retryDelaysRef.current
          if (n < delays.length) {
            timers.push(setTimeout(() => attempt(n + 1), delays[n]))
            return
          }
          // 재시도 소진 — 기존 데이터는 유지한다 (LD-C). 실패 띠 + [다시 시도] 노출.
          setState(prev => ({
            ...prev,
            loading: false,
            refetching: false,
            error: e instanceof Error ? e.message : '데이터 로드 실패',
            retryExhausted: true,
          }))
        })
    }
    attempt(0)

    return () => {
      cancelled = true
      timers.forEach(clearTimeout)
    }
    // key/enabled/refreshTick/retryTick 이 조회 트리거의 전부다.
  }, [key, enabled, refreshTick, retryTick, cache, panel, registerAsOf, noteGridVersion])

  // 화면이 사라지면 기준일 레지스트리에서 빠진다 — 언마운트된 패널이 충돌을 만들지 않는다.
  useEffect(() => () => unregisterAsOf(panel), [panel, unregisterAsOf])

  return useMemo(
    () => ({
      data: state.data,
      loading: state.loading,
      refetching: state.refetching,
      error: state.error,
      retryExhausted: state.retryExhausted,
      // 실패 시 "표시 중인 데이터"의 기준일 — 성공 시에는 노출하지 않는다.
      staleAsOf: state.error !== null && state.data !== null ? state.asOfDate : null,
      asOfDate: state.asOfDate,
      asOfIsPartialWeek: state.asOfIsPartialWeek,
      retry,
    }),
    [state, retry],
  )
}
