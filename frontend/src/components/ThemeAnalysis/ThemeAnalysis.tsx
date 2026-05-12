// @MX:ANCHOR: [AUTO] ThemeAnalysis는 테마 분석 탭의 컨테이너; 좌열=ThemeRankingTable, 우열=ThemeDetailPanel, 하단=멀티테마 위젯
// @MX:REASON: AppContent에서 theme-analysis 탭에 마운트되는 단일 진입 컴포넌트; SPEC-NAVER-THEME-003 V2 endpoint 채택 + retry 패턴 + localStorage 캐시
// @MX:SPEC: SPEC-NAVER-THEME-001 REQ-NT-R-001, REQ-NT-R-002, SPEC-NAVER-THEME-003 REQ-NT3-007 / REQ-NT3-015 / REQ-NT3-016
// @MX:NOTE: [AUTO] retry 패턴은 race-safe — useEffect cleanup(cancelled flag, ba3f20c) + retryNonce trigger
// @MX:NOTE: [AUTO] localStorage 캐시는 cache_version='v1' 매칭 시에만 사용. mount/mode 변경 시 cache 우선 → cache miss이면 fetch + 결과를 cache에 write. 갱신은 명시적 🔄 버튼만 트리거 (자동 만료 없음, REQ-NT3-015/016, v1.0.5)
import { useState, useMemo } from 'react'
import type { ReactElement } from 'react'
import { ThemeRankingTable } from './ThemeRankingTable'
import { ThemeDetailPanel } from './ThemeDetailPanel'
import type { ThemesSnapshotResponse, ThemeItem } from '../../api/themes'
import { fetchThemesSnapshot, fetchThemesQuick } from '../../api/themes'
import { useEffect } from 'react'

type LoadMode = 'quick' | 'full'

// REQ-NT3-015 (v1.0.5): localStorage 캐시 schema 버전. backend 응답 schema 변경 시 'v2'로 올려서 자동 무효화.
const CACHE_VERSION = 'v1'

function getCacheKey(mode: LoadMode): string {
  return `theme-analysis-cache-${mode}`
}

interface CacheEntry {
  cache_version: string
  saved_at: string
  data: ThemesSnapshotResponse
}

function readCache(mode: LoadMode): ThemesSnapshotResponse | null {
  try {
    const raw = localStorage.getItem(getCacheKey(mode))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<CacheEntry>
    if (parsed?.cache_version !== CACHE_VERSION) return null
    if (!parsed.data) return null
    return parsed.data as ThemesSnapshotResponse
  } catch {
    // 손상된 JSON, localStorage 접근 불가 등 → silent miss
    return null
  }
}

function writeCache(mode: LoadMode, data: ThemesSnapshotResponse): void {
  try {
    const entry: CacheEntry = {
      cache_version: CACHE_VERSION,
      saved_at: new Date().toISOString(),
      data,
    }
    localStorage.setItem(getCacheKey(mode), JSON.stringify(entry))
  } catch {
    // QuotaExceededError, SecurityError 등 → silent (캐시 부재로도 정상 동작)
  }
}

function clearCache(mode: LoadMode): void {
  try {
    localStorage.removeItem(getCacheKey(mode))
  } catch {
    // silent
  }
}

function getSortValue(theme: ThemeItem, field: string): number {
  switch (field) {
    case 'theme_name': return 0
    case 'change_pct': return theme.change_pct
    case 'change_pct_3d': return theme.change_pct_3d
    case 'momentum_score': return theme.momentum_score ?? 0
    case 'breadth_ratio': return theme.breadth_ratio ?? 0
    default: return theme.change_pct
  }
}

export function ThemeAnalysis(): ReactElement {
  const [data, setData] = useState<ThemesSnapshotResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<LoadMode>('full')  // v1.0.3 amendment: default 'full' (REQ-NT3-012) — quick 모드는 backend가 detail skip → theme_description/inclusion_reason null이라 사용자가 description 못 봄
  const [retryNonce, setRetryNonce] = useState(0) // retry trigger — useEffect deps에 포함 (REQ-NT3-007)
  const [selectedThemeId, setSelectedThemeId] = useState<number | null>(null)
  const [sortField, setSortField] = useState('change_pct')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    // race condition 방지: 이전 fetch가 진행 중일 때 mode가 변경되면
    // 이전 응답이 새 mode 화면을 덮어쓰지 않도록 cleanup flag로 무시한다.
    // 시나리오: quick(10s) 진행 중 사용자가 full 클릭 → 새 useEffect run.
    // 이전 quick의 then이 늦게 도착하면 cancelled=true이므로 setData 건너뜀.
    let cancelled = false

    // REQ-NT3-015 (v1.0.5): localStorage 캐시 우선 읽기. cache hit이면 fetch skip + 즉시 표시.
    const cached = readCache(mode)
    if (cached) {
      setData(cached)
      setLoading(false)
      setError(null)
      const list = cached.strong_themes ?? cached.themes
      if (selectedThemeId == null && list.length > 0) {
        setSelectedThemeId(list[0].theme_id)
      }
      return () => {
        cancelled = true
      }
    }

    setLoading(true)
    setError(null)
    const promise = mode === 'quick'
      ? fetchThemesQuick()
      : fetchThemesSnapshot()

    promise
      .then(result => {
        if (cancelled) return
        // quick 모드는 stocks/leaders/multi_theme_stocks가 없으므로 빈 배열로 정규화
        const normalized: ThemesSnapshotResponse = mode === 'quick'
          ? ({
              ...result,
              stocks: [],
              leaders: [],
              multi_theme_stocks: [],
            } as ThemesSnapshotResponse)
          : (result as ThemesSnapshotResponse)
        setData(normalized)
        if (selectedThemeId == null && (result.strong_themes ?? result.themes).length > 0) {
          setSelectedThemeId((result.strong_themes ?? result.themes)[0].theme_id)
        }
        // REQ-NT3-015 (v1.0.5): fetch 성공 시 localStorage에 캐시 쓰기
        writeCache(mode, normalized)
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : '데이터 로딩 실패')
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  // mode 변경 또는 retryNonce 증가 시 재실행 (REQ-NT3-007)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, retryNonce])

  const themes = data?.strong_themes ?? data?.themes ?? []

  const sortedThemes = useMemo((): ThemeItem[] => {
    const list = [...themes]
    list.sort((a, b) => {
      if (sortField === 'theme_name') {
        const cmp = a.theme_name.localeCompare(b.theme_name)
        return sortDirection === 'asc' ? cmp : -cmp
      }
      const aVal = getSortValue(a, sortField)
      const bVal = getSortValue(b, sortField)
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })
    return list
  }, [themes, sortField, sortDirection])

  // retry 핸들러 — retryNonce 증가로 useEffect 재실행 유도 (REQ-NT3-007, D-1)
  // V1 자동 폴백 없음 (REQ-NT3-C-006): setError 후 사용자가 직접 재시도
  const handleRetry = (): void => setRetryNonce(n => n + 1)

  // REQ-NT3-016 (v1.0.5): 명시적 갱신 핸들러 — 현재 mode 캐시 무효화 + 새 fetch 트리거.
  // 자동 만료 없음 — 사용자가 본 버튼을 누를 때만 새 데이터를 가져온다.
  const handleRefresh = (): void => {
    clearCache(mode)
    setRetryNonce(n => n + 1)
  }

  const handleSort = (field: string): void => {
    if (field === sortField) {
      setSortDirection(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection(field === 'theme_name' ? 'asc' : 'desc')
    }
  }

  const selectedTheme = selectedThemeId != null
    ? sortedThemes.find(t => t.theme_id === selectedThemeId) ?? null
    : null

  const multiThemeStocks = data?.multi_theme_stocks ?? []

  return (
    <div className="sector-analysis">
      {/* 툴바: 로딩 모드 선택 + 갱신 버튼 */}
      <div className="sector-analysis-toolbar">
        <div className="period-toggle">
          <button
            className={mode === 'quick' ? 'active' : undefined}
            onClick={() => setMode('quick')}
          >
            빠른 조회
          </button>
          <button
            className={mode === 'full' ? 'active' : undefined}
            onClick={() => setMode('full')}
          >
            전체 조회
          </button>
        </div>
        {/* REQ-NT3-016 (v1.0.5): 명시적 데이터 갱신 — 클릭 시 캐시 무효화 + 새 fetch */}
        <button
          type="button"
          data-testid="theme-refresh-button"
          onClick={handleRefresh}
          disabled={loading}
          style={{
            marginLeft: 8,
            padding: '4px 10px',
            fontSize: 12,
            background: 'var(--bg-surface)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.5 : 1,
          }}
          title="저장된 데이터를 무시하고 네이버에서 새로 받아옵니다 (약 30초)"
        >
          🔄 갱신
        </button>
        {data?.metadata && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 12 }}>
            {data.metadata.collected_at} | 테마 {data.metadata.theme_count}개 | {data.metadata.elapsed_sec}초
          </span>
        )}
      </div>

      {loading && (
        <div style={{ padding: 24, fontSize: 13, color: 'var(--text-muted)' }}>
          {mode === 'full' ? '전체 크롤링 중... (~30초)' : '빠른 조회 중...'}
        </div>
      )}

      {error && (
        <div className="theme-analysis-error" style={{ padding: 24, fontSize: 13 }}>
          <p style={{ color: 'var(--negative)', marginBottom: 12 }}>
            테마 데이터를 가져오지 못했습니다. 다시 시도해 주세요.
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 12 }}>
            오류: {error}
          </p>
          <button type="button" onClick={handleRetry}>
            다시 시도
          </button>
        </div>
      )}

      {!loading && !error && data && (
        <>
          <ThemeRankingTable
            themes={sortedThemes}
            sortField={sortField}
            sortDirection={sortDirection}
            onSort={handleSort}
            onThemeClick={setSelectedThemeId}
            selectedThemeId={selectedThemeId}
          />

          {/* 빠른 조회 모드 안내 (REQ-NT3-013, v1.0.3 amendment) */}
          {mode === 'quick' && (
            <div
              data-testid="theme-quick-advisory"
              style={{
                padding: '10px 14px',
                margin: '8px 0',
                fontSize: 12,
                color: 'var(--text-secondary)',
                background: 'var(--bg-surface)',
                borderRadius: 6,
                borderLeft: '3px solid var(--text-muted)',
                lineHeight: 1.55,
              }}
            >
              빠른 조회 모드는 테마 설명과 종목 편입설명을 포함하지 않습니다. 자세한 정보는 위의 <strong>[전체 조회]</strong>를 클릭해 주세요 (약 30초 소요).
            </div>
          )}

          {selectedTheme && (
            <ThemeDetailPanel
              theme={selectedTheme}
              stocks={data.stocks}
              leaders={data.leaders}
            />
          )}

          {/* 멀티테마 종목 위젯 */}
          {multiThemeStocks.length > 0 && (
            <div style={{ marginTop: 16, background: 'var(--bg-surface)', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
                멀티테마 종목 (2개 이상 테마 편입)
              </div>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    <th style={{ textAlign: 'left', padding: '4px 0' }}>종목명</th>
                    <th style={{ textAlign: 'right', padding: '4px 6px', width: 44 }}>테마수</th>
                    <th style={{ textAlign: 'right', padding: '4px 6px', width: 60 }}>평균등락</th>
                    <th style={{ textAlign: 'left', padding: '4px 0' }}>포함 테마</th>
                  </tr>
                </thead>
                <tbody>
                  {multiThemeStocks.map((stock, idx) => (
                    <tr key={stock.stock_code} style={{ background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                      <td style={{ padding: '5px 0' }}>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{stock.stock_name}</span>
                        <span style={{ color: 'var(--text-muted)', marginLeft: 4, fontSize: 11 }}>{stock.stock_code}</span>
                      </td>
                      <td style={{ textAlign: 'right', padding: '5px 6px', color: 'var(--text-secondary)' }}>
                        {stock.theme_count}
                      </td>
                      <td style={{ textAlign: 'right', padding: '5px 6px' }}>
                        <span style={{ color: stock.avg_change_pct > 0 ? 'var(--positive)' : stock.avg_change_pct < 0 ? 'var(--negative)' : 'var(--text-secondary)' }}>
                          {stock.avg_change_pct > 0 ? '+' : ''}{stock.avg_change_pct.toFixed(2)}%
                        </span>
                      </td>
                      <td style={{ padding: '5px 0', color: 'var(--text-muted)', fontSize: 11 }}>
                        {stock.theme_names.join(', ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
