// @MX:NOTE: [AUTO] SectorRankingTable renders sector ranking with sortable columns, color-coded cells,
//   rank-change 4-state (AC-SUX-025), rank total 병기 (AC-SUX-058), 가중 배지 (AC-SUX-026),
//   제외 섹터 영역 (AC-SUX-019). rank 는 응답 값을 그대로 표시 — 재계산하지 않는다 (AC-SUX-021).
// @MX:SPEC: SPEC-TOPDOWN-001D R1, SPEC-SECTOR-UX-001 M4
import type { ReactElement } from 'react'
import type { SectorRankItem, ExcludedSector } from '../../types/market'

interface SectorRankingTableProps {
  sectors: SectorRankItem[]
  sortField: string
  sortDirection: 'asc' | 'desc'
  onSort: (field: string) => void
  onSectorClick: (sectorName: string) => void
  selectedSector: string | null
  // AC-SUX-019 (REQ-SUX-017): 순위 대상 제외 섹터 목록 — 표 하단 영역 렌더.
  excluded?: ExcludedSector[]
  // AC-SUX-025 (REQ-SUX-023): rank_change 기준일 — Rank 열 헤더에 표기.
  baselineDate?: string | null
}

// 가중 방식 배지 (AC-SUX-026 / REQ-SUX-024): 초과수익률 3열 = ⓦ(시총가중, 상한10%),
// RS/신고가/Stage 계열 = ⓔ(등가중). 배지는 본문 상설(hover-only 아님, A5 모바일 대응).
type WeightBadge = 'W' | 'E' | undefined

interface ColumnDef {
  label: string
  field: string
  align: 'left' | 'right'
  badge: WeightBadge
}

const COLUMNS: ColumnDef[] = [
  { label: 'Rank', field: 'rank', align: 'right', badge: undefined },
  { label: 'Sector', field: 'name', align: 'left', badge: undefined },
  { label: '1W', field: 'excess_w1', align: 'right', badge: 'W' },
  { label: '1M', field: 'excess_m1', align: 'right', badge: 'W' },
  { label: '3M', field: 'excess_m3', align: 'right', badge: 'W' },
  { label: 'RS Avg', field: 'rs_avg', align: 'right', badge: 'E' },
  { label: 'RS Top %', field: 'rs_top_pct', align: 'right', badge: 'E' },
  { label: '52W High %', field: 'nh_pct', align: 'right', badge: 'E' },
  { label: 'Stage 2 %', field: 'stage2_pct', align: 'right', badge: 'E' },
  { label: 'Composite', field: 'composite_score', align: 'right', badge: undefined },
]

const BADGE_GLYPH: Record<NonNullable<WeightBadge>, string> = { W: 'ⓦ', E: 'ⓔ' }
const BADGE_TITLE: Record<NonNullable<WeightBadge>, string> = {
  W: '시총가중 (상한 10%)',
  E: '등가중',
}

function getCellColor(value: number, type: 'return' | 'percentage'): string {
  if (type === 'return') {
    // Clamp to ±15 to handle large sector returns (API returns up to 16%+)
    if (value > 0) return `rgba(38, 166, 154, ${Math.min(Math.abs(value) / 15, 0.4)})`
    if (value < 0) return `rgba(239, 83, 80, ${Math.min(Math.abs(value) / 15, 0.4)})`
    return 'transparent'
  }
  // percentage: 0-100 scale
  return `rgba(59, 130, 246, ${Math.min(value / 100, 0.3)})`
}

function formatReturn(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

// AC-SUX-025 (REQ-SUX-023): rank_change 4상태 — >0 ▲n / <0 ▼n / ==0 –(muted) / null 신규(muted+툴팁).
// 0(유지) 과 null(신규) 은 서로 다른 텍스트로 구분된다 (현행 둘 다 '-' 였던 결함 해소).
function RankChange({ change }: { change: number | null }): ReactElement {
  if (change == null) {
    return (
      <span
        className="rank-change rank-change--new"
        title="이번 기간에 신규로 순위 대상에 편입된 섹터 (기준일 대비 이전 순위 없음)"
      >
        신규
      </span>
    )
  }
  if (change > 0) {
    return <span className="rank-change rank-change--up">▲{change}</span>
  }
  if (change < 0) {
    return <span className="rank-change rank-change--down">▼{Math.abs(change)}</span>
  }
  return <span className="rank-change rank-change--flat">–</span>
}

export function SectorRankingTable({
  sectors,
  sortField,
  sortDirection,
  onSort,
  onSectorClick,
  selectedSector,
  excluded,
  baselineDate,
}: SectorRankingTableProps): ReactElement {
  // AC-SUX-058 (REQ-SUX-055): 분모 = 순위 대상 총수. data[] 중 rank !== null 인 개수에서 도출.
  // 총 섹터 수를 상수로 박지 않는다 — 시장 필터로 제외가 늘면 분모가 줄어든다.
  const totalRanked = sectors.filter(s => s.rank != null).length

  return (
    <div className="sector-ranking-table-wrapper">
      <table className="sector-ranking-table" data-testid="sector-ranking-table">
        <thead>
          <tr>
            {COLUMNS.map(col => (
              <th
                key={col.field}
                style={{ textAlign: col.align }}
                onClick={() => onSort(col.field)}
              >
                <span>{col.label}</span>
                {/* AC-SUX-025: Rank 열 헤더에 rank_change 기준일(baseline_date) 표기 */}
                {col.field === 'rank' && baselineDate && (
                  <span className="rank-baseline-date"> 기준 {baselineDate}</span>
                )}
                {/* AC-SUX-026: 가중 방식 배지 (본문 상설) */}
                {col.badge && (
                  <span
                    className="weight-badge"
                    title={BADGE_TITLE[col.badge]}
                    aria-label={BADGE_TITLE[col.badge]}
                  >
                    {BADGE_GLYPH[col.badge]}
                  </span>
                )}
                {sortField === col.field && (
                  <span className="sort-arrow">{sortDirection === 'asc' ? ' ▲' : ' ▼'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sectors.map(sector => (
            <tr
              key={sector.name}
              className={selectedSector === sector.name ? 'selected' : undefined}
              onClick={() => onSectorClick(sector.name)}
            >
              {/* AC-SUX-021: rank 열은 응답 값을 그대로 표시 (재계산 금지). AC-SUX-058: 분자/분모 병기 */}
              <td style={{ textAlign: 'right' }}>
                <span data-testid="rank-value">{sector.rank}</span>
                <span className="rank-total"> / {totalRanked}</span>
                {' '}<RankChange change={sector.rank_change} />
              </td>
              {/* Sector name */}
              <td style={{ textAlign: 'left' }}>{sector.name}</td>
              {/* 1W excess return */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.excess_returns.w1, 'return'),
                }}
              >
                {formatReturn(sector.excess_returns.w1)}
              </td>
              {/* 1M excess return */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.excess_returns.m1, 'return'),
                }}
              >
                {formatReturn(sector.excess_returns.m1)}
              </td>
              {/* 3M excess return */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.excess_returns.m3, 'return'),
                }}
              >
                {formatReturn(sector.excess_returns.m3)}
              </td>
              {/* RS Avg */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.rs_avg, 'percentage'),
                }}
              >
                {sector.rs_avg}
              </td>
              {/* RS Top % */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.rs_top_pct, 'percentage'),
                }}
              >
                {sector.rs_top_pct}%
              </td>
              {/* 52W High % */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.nh_pct, 'percentage'),
                }}
              >
                {sector.nh_pct}%
              </td>
              {/* Stage 2 % */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.stage2_pct, 'percentage'),
                }}
              >
                {sector.stage2_pct}%
              </td>
              {/* Composite score (plan M4) */}
              <td style={{ textAlign: 'right' }}>{sector.composite_score.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* AC-SUX-026 (REQ-SUX-024): 가중 방식 범례 — 표 하단 한 줄 (본문 상설) */}
      <div className="weight-badge-legend">
        <span className="weight-badge">ⓦ</span> 시총가중(상한10%)
        {'  '}
        <span className="weight-badge">ⓔ</span> 등가중
      </div>

      {/* AC-SUX-019 (REQ-SUX-017): 순위 대상 제외 영역 — 표 하단. 빈 배열이면 렌더하지 않는다 (E2). */}
      {excluded && excluded.length > 0 && (
        <div className="excluded-sectors" data-testid="excluded-sectors">
          <div className="excluded-sectors-header">
            순위 대상 제외 ({excluded.length})
          </div>
          <ul className="excluded-sectors-list">
            {excluded.map(item => (
              <li key={item.sector} className="excluded-sector-item">
                <span className="excluded-sector-name">{item.sector}</span>
                <span className="excluded-sector-meta">
                  {' '}— {item.reason} (n={item.count})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
