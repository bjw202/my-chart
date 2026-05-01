// @MX:NOTE: [AUTO] ThemeRankingTable은 강세 테마 목록을 정렬 가능한 테이블로 렌더링
// @MX:SPEC: SPEC-NAVER-THEME-001 REQ-NT-005
import type { ReactElement } from 'react'
import type { ThemeItem } from '../../api/themes'

interface ThemeRankingTableProps {
  themes: ThemeItem[]
  sortField: string
  sortDirection: 'asc' | 'desc'
  onSort: (field: string) => void
  onThemeClick: (themeId: number) => void
  selectedThemeId: number | null
}

const COLUMNS: { label: string; field: string; align: 'left' | 'right' }[] = [
  { label: '테마명', field: 'theme_name', align: 'left' },
  { label: '등락률', field: 'change_pct', align: 'right' },
  { label: '3일등락률', field: 'change_pct_3d', align: 'right' },
  { label: '모멘텀점수', field: 'momentum_score', align: 'right' },
  { label: '상승비율', field: 'breadth_ratio', align: 'right' },
  { label: '대표종목', field: 'top_stocks_preview', align: 'left' },
]

function getChangePctColor(value: number): string {
  if (value > 0) return `rgba(38, 166, 154, ${Math.min(Math.abs(value) / 10, 0.4)})`
  if (value < 0) return `rgba(239, 83, 80, ${Math.min(Math.abs(value) / 10, 0.4)})`
  return 'transparent'
}

function formatPct(value: number): string {
  if (!isFinite(value)) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function formatBreadth(value: number | undefined): string {
  if (value == null || !isFinite(value)) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function formatMomentum(value: number | undefined): string {
  if (value == null || !isFinite(value)) return '-'
  return value.toFixed(2)
}

export function ThemeRankingTable({
  themes,
  sortField,
  sortDirection,
  onSort,
  onThemeClick,
  selectedThemeId,
}: ThemeRankingTableProps): ReactElement {
  return (
    <table className="sector-ranking-table">
      <thead>
        <tr>
          {COLUMNS.map(col => (
            <th
              key={col.field}
              style={{ textAlign: col.align }}
              onClick={() => onSort(col.field)}
            >
              {col.label}
              {sortField === col.field && (
                <span className="sort-arrow">{sortDirection === 'asc' ? ' ▲' : ' ▼'}</span>
              )}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {themes.map(theme => (
          <tr
            key={theme.theme_id}
            className={selectedThemeId === theme.theme_id ? 'selected' : undefined}
            onClick={() => onThemeClick(theme.theme_id)}
          >
            <td style={{ textAlign: 'left' }}>{theme.theme_name}</td>
            <td
              style={{
                textAlign: 'right',
                background: getChangePctColor(theme.change_pct),
              }}
            >
              {formatPct(theme.change_pct)}
            </td>
            <td
              style={{
                textAlign: 'right',
                background: getChangePctColor(theme.change_pct_3d),
              }}
            >
              {formatPct(theme.change_pct_3d)}
            </td>
            <td style={{ textAlign: 'right' }}>{formatMomentum(theme.momentum_score)}</td>
            <td style={{ textAlign: 'right' }}>{formatBreadth(theme.breadth_ratio)}</td>
            <td style={{ textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>
              {theme.top_stocks_preview ?? '-'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
