// @MX:NOTE: [AUTO] SectorRankingTable renders sector ranking with sortable columns, color-coded cells,
//   rank-change 4-state (AC-SUX-025), rank total 병기 (AC-SUX-058), 가중 배지 (AC-SUX-026),
//   제외 섹터 영역 (AC-SUX-019). rank 는 응답 값을 그대로 표시 — 재계산하지 않는다 (AC-SUX-021).
// @MX:SPEC: SPEC-TOPDOWN-001D R1, SPEC-SECTOR-UX-001 M4
import type { ReactElement } from 'react'
import type { SectorRankItem, ExcludedSector } from '../../types/market'
// D6 / AC-SUX-052: 셀 5상태는 공용 MetricCell 이 전담한다 (화면별 표기 발산 방지).
import { MetricCell, percent1, rating0, pct0 } from '../common/MetricCell'
// REQ-SDU-003: RS 임계값 상수 — 라벨 title 이 상수에서 나온다.
import { RS_TOP_THRESHOLD } from '../../utils/rsMetrics'

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
  // M7 (REQ-SDU-009): 활성 기간 — 해당 기간 수익률 열 헤더에 (순위 기준) 마커.
  // 기간 랭킹이 실제 활성일 때만 부모가 넘긴다(마커가 거짓을 말하지 않게).
  activePeriod?: '1w' | '1m' | '3m'
  // M7 (REQ-SDU-007): data[] 부재/전량 조인 실패로 composite 폴백 중이면 캡션이 그 사실을 말한다.
  compositeFallback?: boolean
  // M7 (EF-2): 기간 랭킹 활성 중 이름 조인 실패로 composite 순위를 유지한 섹터 수.
  partialFallbackCount?: number
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
  // REQ-SDU-004: 'RS Top %' → 'RS 80+ 비중' — RS 점수가 아니라 "RS≥80 종목 비율"임을 정확히 서술.
  { label: 'RS 80+ 비중', field: 'rs_top_pct', align: 'right', badge: 'E' },
  { label: '52W High %', field: 'nh_pct', align: 'right', badge: 'E' },
  { label: 'Stage 2 %', field: 'stage2_pct', align: 'right', badge: 'E' },
  { label: 'Composite', field: 'composite_score', align: 'right', badge: undefined },
]

const BADGE_GLYPH: Record<NonNullable<WeightBadge>, string> = { W: 'ⓦ', E: 'ⓔ' }
const BADGE_TITLE: Record<NonNullable<WeightBadge>, string> = {
  W: '시총가중 (상한 10%)',
  E: '등가중',
}

// M7 (REQ-SDU-009): 활성 기간 → 수익률 열 필드 매핑. 세 열은 전부 유지된다(DEC-F4).
const PERIOD_COLUMN_FIELD: Record<'1w' | '1m' | '3m', string> = {
  '1w': 'excess_w1',
  '1m': 'excess_m1',
  '3m': 'excess_m3',
}

// AC-SUX-053 (ER-2): 결측은 배경색 채널에서도 0 으로 취급하지 않는다 — 색 없음.
// REQ-SDU-005 (M6): 세 번째 type 'rating' 추가 — 등급(rs_avg)과 비중(rs_top_pct)이
//   파란 램프를 공유하면 같은 값이 같은 색으로 보여 두 채널이 구분되지 않는다.
//   등급은 보라 채널, 비중은 기존 파란 채널을 쓴다(동일 값에서도 색이 다르다).
function getCellColor(value: number | null | undefined, type: 'return' | 'percentage' | 'rating'): string {
  if (value == null || Number.isNaN(value)) return 'transparent'
  if (type === 'return') {
    // Clamp to ±15 to handle large sector returns (API returns up to 16%+)
    if (value > 0) return `rgba(38, 166, 154, ${Math.min(Math.abs(value) / 15, 0.4)})`
    if (value < 0) return `rgba(239, 83, 80, ${Math.min(Math.abs(value) / 15, 0.4)})`
    return 'transparent'
  }
  if (type === 'rating') {
    // rating: RS 등급 0-100 — 보라 채널 (비중의 파란 채널과 구분)
    return `rgba(139, 92, 246, ${Math.min(value / 100, 0.3)})`
  }
  // percentage: 0-100 scale
  return `rgba(59, 130, 246, ${Math.min(value / 100, 0.3)})`
}

// AC-SUX-053 (ER-2): 무조건 toFixed(1) 경로는 제거되었다.
// 결측 처리는 MetricCell 이 담당하고, 이 포맷터는 유한 숫자만 받는다 (percent1 재export).
const formatReturn = percent1

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
  activePeriod,
  compositeFallback,
  partialFallbackCount,
}: SectorRankingTableProps): ReactElement {
  // AC-SUX-058 (REQ-SUX-055): 분모 = 순위 대상 총수. data[] 중 rank !== null 인 개수에서 도출.
  // 총 섹터 수를 상수로 박지 않는다 — 시장 필터로 제외가 늘면 분모가 줄어든다.
  const totalRanked = sectors.filter(s => s.rank != null).length

  return (
    <div className="sector-ranking-table-wrapper">
      {/* M7 (REQ-SDU-007): composite 폴백 중임을 캡션이 말한다 — 조용한 폴백 금지 */}
      {compositeFallback && (
        <div className="ranking-basis-caption" data-testid="ranking-basis-caption">
          순위 기준: 종합점수(3기간 가중)
        </div>
      )}
      {/* M7 (EF-2): 부분 조인 실패 — 남은 섹터의 순위 기준이 섞여 있음을 고지 */}
      {!compositeFallback && (partialFallbackCount ?? 0) > 0 && (
        <div className="ranking-basis-caption" data-testid="ranking-basis-partial">
          일부 {partialFallbackCount}개 섹터는 이름 조인 실패로 종합점수 순위 유지
        </div>
      )}
      <table className="sector-ranking-table" data-testid="sector-ranking-table">
        <thead>
          <tr>
            {COLUMNS.map(col => (
              <th
                key={col.field}
                style={{ textAlign: col.align }}
                onClick={() => onSort(col.field)}
                // REQ-SDU-003/004: 'RS 80+ 비중' 헤더 — 임계값이 상수에서 나온 title.
                title={col.field === 'rs_top_pct' ? `섹터 내 RS ${RS_TOP_THRESHOLD} 이상 종목의 비율` : undefined}
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
                {/* M7 (REQ-SDU-009): 선택 기간 열에 (순위 기준) — 세 수익률 열은 모두 유지(DEC-F4) */}
                {activePeriod && col.field === PERIOD_COLUMN_FIELD[activePeriod] && (
                  <span className="rank-basis-marker"> (순위 기준)</span>
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
                <MetricCell value={sector.excess_returns.w1} format={formatReturn} />
              </td>
              {/* 1M excess return */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.excess_returns.m1, 'return'),
                }}
              >
                <MetricCell value={sector.excess_returns.m1} format={formatReturn} />
              </td>
              {/* 3M excess return */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.excess_returns.m3, 'return'),
                }}
              >
                <MetricCell value={sector.excess_returns.m3} format={formatReturn} />
              </td>
              {/* RS Avg — REQ-SDU-005 'rating' 채널(보라), REQ-SDU-001 rating0(3면 동일성) */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.rs_avg, 'rating'),
                }}
              >
                <MetricCell value={sector.rs_avg} format={rating0} />
              </td>
              {/* RS 80+ 비중 — REQ-SDU-004 개명. 비중은 기존 파란 채널 유지 */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.rs_top_pct, 'percentage'),
                }}
              >
                <MetricCell value={sector.rs_top_pct} format={pct0} />
              </td>
              {/* 52W High % */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.nh_pct, 'percentage'),
                }}
              >
                <MetricCell value={sector.nh_pct} format={pct0} />
              </td>
              {/* Stage 2 % */}
              <td
                style={{
                  textAlign: 'right',
                  background: getCellColor(sector.stage2_pct, 'percentage'),
                }}
              >
                <MetricCell value={sector.stage2_pct} format={pct0} />
              </td>
              {/* Composite score (plan M4) */}
              <td style={{ textAlign: 'right' }}><MetricCell value={sector.composite_score} format={(n) => n.toFixed(2)} /></td>
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
