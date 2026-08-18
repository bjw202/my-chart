import { useState } from 'react'
import type { ReactElement } from 'react'
import type { Stage2Candidate } from '../../types/stage'
import { COLLAPSE_ORDER, hiddenColumnKeys, INVARIANT_COLUMN_KEYS } from './stockTableColumns'
// D6 / AC-SUX-052: 셀 5상태는 공용 MetricCell 이 전담한다 (화면별 표기 발산 방지).
import { MetricCell, percent1, percent2, rating0 } from '../common/MetricCell'
// REQ-SDU-003: s2-strong 술어 임계값 상수 — 라벨 없던 술어에 상수 유래 title 을 붙인다.
import { RS_S2_STRONG_THRESHOLD } from '../../utils/rsMetrics'
import { filterCandidates } from './stockFilter'

interface StockTableProps {
  candidates: Stage2Candidate[]
  // number = stage 1-4 필터; 'unclassified' = 분류 불가 종목만(AC-SUX-030); null = 전체
  stageFilter: number | 'unclassified' | null
  sectorFilter: string | null
  // AC-SUX-018/054: 헤더 시장 토글(all/kospi/kosdaq) — 'all' 이면 필터하지 않는다.
  marketFilter?: 'all' | 'kospi' | 'kosdaq'
  onStockSelect: (code: string) => void
  onSelectAll?: (codes: string[]) => void
  selectedStocks: Set<string>
  // AC-SUX-061 (REQ-SUX-058): 좁은 화면 열 접기 단계(0..3). 기본 0(전체 표시 — AC-SUX-032 default 가시성).
  collapseLevel?: number
}

type SortKey = 'name' | 'market' | 'stage' | 'rs_12m' | 'chg_1m' | 'volume_ratio'
type SortDir = 'asc' | 'desc'

// R5: Key checklist — evaluate the three criteria for a stock
interface ChecklistResult {
  ma: boolean    // close > sma50 > sma200
  vol: boolean   // volume_ratio >= 1.5
  rs: boolean    // rs_12m >= 70
}

function computeChecklist(c: Stage2Candidate): ChecklistResult {
  return {
    ma: c.close > c.sma50 && c.sma50 > c.sma200,
    vol: c.volume_ratio >= 1.5,
    rs: c.rs_12m >= 70,
  }
}

// Render a single check indicator dot
function CheckDot({ pass, label, checkKey }: { pass: boolean; label: string; checkKey: string }): ReactElement {
  return (
    <span
      className={`check-dot ${pass ? 'check-pass' : 'check-fail'}`}
      data-check={checkKey}
      title={label}
    >
      {pass ? '●' : '○'}
    </span>
  )
}

// Determine badge class based on stage (integer 1-4) and RS rating
function getStageBadgeClass(candidate: Stage2Candidate): string {
  const { stage, stage_detail, rs_12m } = candidate

  if (stage === 2) {
    // REQ-SDU-003: 60 매직넘버 제거 — RS_S2_STRONG_THRESHOLD 상수 사용.
    if (rs_12m > RS_S2_STRONG_THRESHOLD) return 'stage-badge--s2-strong'
    if (stage_detail?.toLowerCase().includes('entry')) return 'stage-badge--s2-entry'
    return 'stage-badge--s2'
  }
  if (stage === 1) return 'stage-badge--s1'
  if (stage === 3) return 'stage-badge--s3'
  if (stage === 4) return 'stage-badge--s4'
  return 'stage-badge--s1'
}

// @MX:NOTE: [AUTO] StockTable renders filtered/sorted stage candidates with multi-select support.
// AC-SUX-031 (REQ-SUX-029/030): 1W%/1M%/3M%/섹터비중 4열 상설 + ⊤(weight_capped) 마커.
// AC-SUX-061 (REQ-SUX-058): 좁은 화면 열 접기 — 섹터비중→Vol배→52W고 단일 상수 순서.
// 필터는 stageFilter(정수·'unclassified') + sectorFilter(sector_major 만 — REQ-SUX-054 철회, 중분류 분기 없음).

export function StockTable({
  candidates,
  stageFilter,
  sectorFilter,
  marketFilter = 'all',
  onStockSelect,
  onSelectAll,
  selectedStocks,
  collapseLevel = 0,
}: StockTableProps): ReactElement {
  const [sortKey, setSortKey] = useState<SortKey>('rs_12m')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  // 모집단 판정은 stockFilter.ts 단일 출처를 쓴다 — 푸터 종목 수도 같은 술어를 통과한다.
  const filtered = filterCandidates(candidates, { stageFilter, sectorFilter, marketFilter })

  // Apply sorting
  const sorted = [...filtered].sort((a, b) => {
    let aVal: string | number = a[sortKey] ?? ''
    let bVal: string | number = b[sortKey] ?? ''
    if (typeof aVal === 'string') aVal = aVal.toLowerCase()
    if (typeof bVal === 'string') bVal = bVal.toLowerCase()
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const renderSortIndicator = (key: SortKey) => {
    if (sortKey !== key) return null
    return sortDir === 'asc' ? ' ▲' : ' ▼'
  }

  // 전체선택 상태 계산
  const allSelected = sorted.length > 0 && sorted.every((c) => selectedStocks.has(c.code))
  const someSelected = sorted.some((c) => selectedStocks.has(c.code))

  const handleSelectAll = () => {
    if (onSelectAll) {
      if (allSelected) {
        onSelectAll([])  // 전체 해제
      } else {
        onSelectAll(sorted.map((c) => c.code))  // 전체 선택
      }
    }
  }

  // AC-SUX-061: 숨겨진 열 집합 + 가로 스크롤 한계 도달 여부
  const hidden = hiddenColumnKeys(collapseLevel)
  const allCollapsibleHidden = collapseLevel >= COLLAPSE_ORDER.length
  const colHidden = (key: string): boolean => hidden.has(key)
  // invariant 열은 어떤 collapseLevel 에서도 숨기지 않는다(Lesson #3).
  void INVARIANT_COLUMN_KEYS

  return (
    <div
      className="stock-table-wrapper"
      data-collapse-level={collapseLevel}
      data-overflow-scroll={allCollapsibleHidden ? 'true' : undefined}
    >
      <table className="stock-table" data-testid="stock-table">
        <thead>
          <tr>
            <th style={{ width: 32 }}>
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => {
                  if (el) el.indeterminate = someSelected && !allSelected
                }}
                onChange={handleSelectAll}
                aria-label="Select all"
              />
            </th>
            <th data-col-key="name" onClick={() => handleSort('name')}>
              Name{renderSortIndicator('name')}
            </th>
            <th data-col-key="market" onClick={() => handleSort('market')}>
              Market{renderSortIndicator('market')}
            </th>
            <th data-col-key="stage" onClick={() => handleSort('stage')}>
              Stage{renderSortIndicator('stage')}
            </th>
            <th data-col-key="rs_12m" onClick={() => handleSort('rs_12m')}>
              RS{renderSortIndicator('rs_12m')}
            </th>
            {/* AC-SUX-031 (REQ-SUX-029): 기간 3열 상설 */}
            <th data-col-key="chg_1w">1W%</th>
            <th data-col-key="chg_1m" onClick={() => handleSort('chg_1m')}>
              1M%{renderSortIndicator('chg_1m')}
            </th>
            <th data-col-key="chg_3m">3M%</th>
            <th data-col-key="volume_ratio" data-collapsed={colHidden('volume_ratio') || undefined}>
              Vol배
            </th>
            <th data-col-key="near_52w_high" data-collapsed={colHidden('near_52w_high') || undefined}>
              52W고
            </th>
            <th data-col-key="weight_in_sector" data-collapsed={colHidden('weight_in_sector') || undefined}>
              섹터비중
            </th>
            <th>Check</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const badgeClass = getStageBadgeClass(c)
            const isEntry = c.stage_detail.toLowerCase().includes('entry')
            // AC-SUX-053 (ER-2): 결측을 0 으로 대체하지 않는다 — 색·바 폭 채널도 결측이면 중립.
            const chgMissing = c.chg_1m == null || Number.isNaN(c.chg_1m)
            const chgColor = chgMissing ? 'neutral' : c.chg_1m >= 0 ? 'positive' : 'negative'
            // R4: Trend bar — width proportional to |chg_1m|, capped at 100% at 20%
            const trendBarWidth = chgMissing ? 0 : Math.min(Math.abs(c.chg_1m) / 20 * 100, 100)
            const trendBarClass = chgMissing ? 'trend-bar--neutral' : c.chg_1m >= 0 ? 'trend-bar--positive' : 'trend-bar--negative'

            const checklist = computeChecklist(c)


            // 접힌 열의 값을 행 툴팁으로 노출(AC-SUX-061 — 정보 소실 방지)
            const collapsedSummary: string[] = []
            if (colHidden('weight_in_sector') && c.weight_in_sector != null) {
              collapsedSummary.push(`섹터비중 ${(c.weight_in_sector * 100).toFixed(1)}%${c.weight_capped ? ' ⊤' : ''}`)
            }
            if (colHidden('volume_ratio') && c.volume_ratio != null) collapsedSummary.push(`Vol배 ${c.volume_ratio.toFixed(2)}`)
            if (colHidden('near_52w_high')) collapsedSummary.push(`52W고 ${c.near_52w_high ? '근접' : '–'}`)

            return (
              <tr key={c.code} title={collapsedSummary.length > 0 ? collapsedSummary.join(' / ') : undefined}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedStocks.has(c.code)}
                    onChange={() => onStockSelect(c.code)}
                    aria-label={`Select ${c.name}`}
                  />
                </td>
                <td data-col-key="name">
                  <span className="stock-name">{c.name}</span>
                  <span className="stock-code"> {c.code}</span>
                </td>
                <td data-col-key="market">{c.market}</td>
                <td data-col-key="stage">
                  <span
                    className={`stage-badge ${badgeClass}`}
                    // REQ-SDU-003: s2-strong 은 RS>60 판정 — 상수 유래 title 로 근거 노출.
                    title={badgeClass === 'stage-badge--s2-strong' ? `RS ${RS_S2_STRONG_THRESHOLD} 초과 강세 판정` : undefined}
                  >
                    S{c.stage}
                  </span>
                  {isEntry && <span className="entry-star">★</span>}
                </td>
                <td data-col-key="rs_12m"><MetricCell value={c.rs_12m} format={rating0} /></td>
                <td data-col-key="chg_1w"><MetricCell value={c.chg_1w} format={percent1} /></td>
                <td data-col-key="chg_1m" className={`chg-cell ${chgColor}`}>
                  <div className="chg-cell-inner">
                    <MetricCell value={c.chg_1m} format={percent2} />
                    <div
                      className={`trend-bar ${trendBarClass}`}
                      style={{ width: `${trendBarWidth}%` }}
                      aria-hidden="true"
                    />
                  </div>
                </td>
                <td data-col-key="chg_3m"><MetricCell value={c.chg_3m} format={percent1} /></td>
                <td data-col-key="volume_ratio" data-collapsed={colHidden('volume_ratio') || undefined}>
                  <MetricCell value={c.volume_ratio} format={(n) => n.toFixed(2)} />
                </td>
                <td data-col-key="near_52w_high" data-collapsed={colHidden('near_52w_high') || undefined}>
                  {c.near_52w_high ? '●' : '–'}
                </td>
                <td data-col-key="weight_in_sector" data-collapsed={colHidden('weight_in_sector') || undefined}>
                  <MetricCell value={c.weight_in_sector} format={(n) => `${(n * 100).toFixed(1)}%`} />
                  {/* AC-SUX-031 (REQ-SUX-030): 상한 적용 종목 ⊤ 마커 (본문 상설) */}
                  {c.weight_capped && <span className="weight-cap-marker" aria-label="시총 상한 적용">⊤</span>}
                </td>
                <td className="checklist-cell">
                  <CheckDot pass={checklist.ma} label="MA Aligned (close > SMA50 > SMA200)" checkKey="ma" />
                  <CheckDot pass={checklist.vol} label="Vol Surge (ratio ≥ 1.5)" checkKey="vol" />
                  <CheckDot pass={checklist.rs} label="RS Strong (≥ 70)" checkKey="rs" />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
