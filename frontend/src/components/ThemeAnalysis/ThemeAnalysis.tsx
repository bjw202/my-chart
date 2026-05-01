// @MX:ANCHOR: [AUTO] ThemeAnalysis는 테마 분석 탭의 컨테이너; 좌열=ThemeRankingTable, 우열=ThemeDetailPanel, 하단=멀티테마 위젯
// @MX:REASON: AppContent에서 theme-analysis 탭에 마운트되는 단일 진입 컴포넌트; SPEC-NAVER-THEME-001 Phase 3
// @MX:SPEC: SPEC-NAVER-THEME-001 REQ-NT-R-001, REQ-NT-R-002
import { useState, useMemo } from 'react'
import type { ReactElement } from 'react'
import { ThemeRankingTable } from './ThemeRankingTable'
import { ThemeDetailPanel } from './ThemeDetailPanel'
import type { ThemesSnapshotResponse, ThemeItem } from '../../api/themes'
import { fetchThemesSnapshot, fetchThemesQuick } from '../../api/themes'
import { useEffect } from 'react'

type LoadMode = 'quick' | 'full'

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
  const [mode, setMode] = useState<LoadMode>('quick')
  const [selectedThemeId, setSelectedThemeId] = useState<number | null>(null)
  const [sortField, setSortField] = useState('change_pct')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    setLoading(true)
    setError(null)
    const promise = mode === 'quick'
      ? fetchThemesQuick()
      : fetchThemesSnapshot()

    promise
      .then(result => {
        // quick 모드는 stocks/leaders/multi_theme_stocks가 없으므로 빈 배열로 정규화
        if (mode === 'quick') {
          setData({
            ...result,
            stocks: [],
            leaders: [],
            multi_theme_stocks: [],
          } as ThemesSnapshotResponse)
        } else {
          setData(result as ThemesSnapshotResponse)
        }
        if (selectedThemeId == null && (result.strong_themes ?? result.themes).length > 0) {
          setSelectedThemeId((result.strong_themes ?? result.themes)[0].theme_id)
        }
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : '데이터 로딩 실패')
      })
      .finally(() => {
        setLoading(false)
      })
  // mode 변경 시만 재실행
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

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
      {/* 툴바: 로딩 모드 선택 */}
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
        <div style={{ padding: 24, fontSize: 13, color: 'var(--negative)' }}>
          오류: {error}
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
