// @MX:NOTE: Fullscreen modal rendering 7 financial analysis sections.
// Uses React.createPortal to mount in document.body, isolated from chart grid stacking context.
import React, { useEffect, useCallback, useRef, useState } from 'react'
import ReactDOM from 'react-dom'
import type {
  AnalysisResponse,
  BusinessPerformance,
  HealthIndicators,
  BalanceSheet,
  RateDecomposition,
  ProfitWaterfall,
  TrendSignals,
  FiveQuestions,
  ActivityRatios,
} from '../types/analysis'

// ── Locale formatting helpers ─────────────────────────────────────────────────

/** Format value in 억원 units with comma separator. */
function fmtAmount(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '-'
  return `${Math.round(val).toLocaleString('ko-KR')}억원`
}

/** Convert decimal ratio (e.g. 0.143) to "14.3%" string. */
function fmtPct(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '-'
  return `${(val * 100).toFixed(1)}%`
}

/** Format multiplier value like "71.9x배". */
function fmtMultiple(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '-'
  return `${val.toFixed(1)}x배`
}

/** Format health indicator value: 배율 as multiple, others as percentage. */
function fmtHealthValue(name: string, val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '-'
  if (name.includes('배율')) return fmtMultiple(val)
  return fmtPct(val)
}

/** Get CSS class for signed change values (YoY, spread). */
function signColorClass(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return ''
  return val >= 0 ? 'analysis-positive' : 'analysis-negative'
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: 'ok' | 'warn' | 'danger' }): React.ReactElement {
  const label = status === 'ok' ? '양호' : status === 'warn' ? '주의' : '위험'
  return <span className={`analysis-badge analysis-badge--${status}`}>{label}</span>
}

// ── Tooltip component ─────────────────────────────────────────────────────────

function Tooltip({ text, children }: { text: string; children: React.ReactNode }): React.ReactElement {
  const [show, setShow] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const ref = useRef<HTMLSpanElement>(null)

  const handleEnter = useCallback(() => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect()
      setPos({ top: rect.bottom + 6, left: rect.left })
    }
    setShow(true)
  }, [])

  return (
    <span
      className="analysis-tooltip-wrap"
      ref={ref}
      onMouseEnter={handleEnter}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && pos && ReactDOM.createPortal(
        <span className="analysis-tooltip" style={{ top: pos.top, left: pos.left }}>{text}</span>,
        document.body,
      )}
    </span>
  )
}

// ── Section 0: 사업 개요 ─────────────────────────────────────────────────────

function SectionBusinessSummary({ summary }: { summary: string }): React.ReactElement {
  return (
    <section className="analysis-section">
      <h2 className="analysis-section-title">사업 개요</h2>
      <p className="analysis-business-summary">{summary}</p>
    </section>
  )
}

// ── Section 1: 사업 성과 ─────────────────────────────────────────────────────

function SectionBusinessPerformance({ data }: { data: BusinessPerformance }): React.ReactElement {
  const { periods, revenue, operating_profit, net_income, operating_cf, opm, npm, yoy_revenue, yoy_op, yoy_ni, profit_quality } = data

  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">사업 성과</h3>
      <div className="analysis-table-wrap">
        <table className="analysis-table">
          <thead>
            <tr>
              <th>항목</th>
              {periods.map((p) => <th key={p}>{p}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>매출액</td>
              {revenue.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtAmount(v)}</td>)}
            </tr>
            <tr>
              <td>영업이익</td>
              {operating_profit.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtAmount(v)}</td>)}
            </tr>
            <tr>
              <td>당기순이익</td>
              {net_income.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtAmount(v)}</td>)}
            </tr>
            <tr>
              <td>
                <Tooltip text="영업활동현금흐름(Operating Cash Flow). 기업이 본업인 영업활동을 통해 실제로 벌어들인 현금입니다. 매출채권 회수, 재고 변동, 감가상각비 등 비현금 항목을 반영하여 당기순이익과 달리 실제 현금 유입·유출을 보여줍니다. 영업이익보다 높으면 이익이 현금으로 뒷받침되는 건전한 기업입니다.">
                  <span className="analysis-indicator-name">영업CF</span>
                </Tooltip>
              </td>
              {operating_cf.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtAmount(v)}</td>)}
            </tr>
            <tr>
              <td>영업이익률</td>
              {opm.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtPct(v)}</td>)}
            </tr>
            <tr>
              <td>순이익률</td>
              {npm.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtPct(v)}</td>)}
            </tr>
            <tr>
              <td>매출 YoY</td>
              {yoy_revenue.map((v, i) => (
                <td key={i} className={signColorClass(v)}>
                  {v === null ? '-' : `${v >= 0 ? '+' : ''}${fmtPct(v)}`}
                </td>
              ))}
            </tr>
            <tr>
              <td>영업이익 YoY</td>
              {yoy_op.map((v, i) => (
                <td key={i} className={signColorClass(v)}>
                  {v === null ? '-' : `${v >= 0 ? '+' : ''}${fmtPct(v)}`}
                </td>
              ))}
            </tr>
            <tr>
              <td>순이익 YoY</td>
              {yoy_ni.map((v, i) => (
                <td key={i} className={signColorClass(v)}>
                  {v === null ? '-' : `${v >= 0 ? '+' : ''}${fmtPct(v)}`}
                </td>
              ))}
            </tr>
            <tr>
              <td>
                <Tooltip text="이익 품질 = 영업CF ÷ 영업이익. 영업이익 대비 실제 현금이 얼마나 들어왔는지를 측정합니다. 1.0 이상이면 이익이 현금으로 온전히 뒷받침되는 양질의 이익이며, 1.0 미만이면 매출채권·재고 증가 등으로 현금 회수가 지연되고 있음을 의미합니다. 지속적으로 0.5 미만이면 분식회계 가능성도 점검할 필요가 있습니다.">
                  <span className="analysis-indicator-name">이익 품질</span>
                </Tooltip>
              </td>
              {profit_quality.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtMultiple(v)}</td>)}
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ── Section 2: 건전성 ─────────────────────────────────────────────────────────

const HEALTH_DESCRIPTIONS: Record<string, string> = {
  '외부차입/자기자본': '외부 차입금이 자기자본 대비 얼마나 되는지를 측정합니다. 낮을수록 자기자본으로 운영하는 안정적 기업입니다.',
  '부채비율': '총 부채(외부차입+영업부채)가 자기자본 대비 얼마인지를 나타냅니다. 100% 이하가 안정적입니다.',
  '차입금의존도': '총자산 중 외부 차입금의 비중입니다. 낮을수록 차입에 덜 의존합니다.',
  '순차입금의존도': '(외부차입 - 여유자금) / 총자산. 음수이면 보유 현금이 차입금보다 많아 재무적으로 우수합니다.',
  '이자보상배율': '영업이익으로 이자비용을 몇 배 갚을 수 있는지를 나타냅니다. 높을수록 안정적입니다.',
  '영업자산비율': '총자산 중 영업에 실제 사용되는 자산의 비중입니다. 높을수록 본업에 집중하는 기업입니다.',
  '비지배귀속비율': '당기순이익 중 비지배주주에게 귀속되는 비율입니다. 낮을수록 지배주주에게 유리합니다.',
}

const HEALTH_THRESHOLDS: Record<string, string> = {
  '외부차입/자기자본': '< 20%',
  '부채비율': '< 100%',
  '차입금의존도': '< 5%',
  '순차입금의존도': '< 0%',
  '이자보상배율': '> 10x',
  '영업자산비율': '> 70%',
  '비지배귀속비율': '< 5%',
}

function SectionHealthIndicators({ data }: { data: HealthIndicators }): React.ReactElement {
  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">건전성</h3>
      <div className="analysis-table-wrap">
        <table className="analysis-table">
          <thead>
            <tr>
              <th>지표</th>
              <th>값</th>
              <th>기준</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            {data.indicators.map((ind) => (
              <tr key={ind.name}>
                <td>
                  <Tooltip text={HEALTH_DESCRIPTIONS[ind.name] ?? ''}>
                    <span className="analysis-indicator-name">{ind.name}</span>
                  </Tooltip>
                </td>
                <td className={ind.status === 'ok' ? 'analysis-positive' : ind.status === 'danger' ? 'analysis-negative' : 'analysis-warn-text'}>
                  {fmtHealthValue(ind.name, ind.value)}
                </td>
                <td className="analysis-muted">{HEALTH_THRESHOLDS[ind.name] ?? ind.threshold}</td>
                <td><StatusBadge status={ind.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ── Section 3: B/S 재분류 (Stacked Bar Chart) ────────────────────────────────

const BS_COLORS: Record<string, string> = {
  '신용조달': '#ef5350',
  '외부차입': '#ff7043',
  '주주몫': '#26a69a',
  '비지배주주지분': '#66bb6a',
  '설비투자': '#42a5f5',
  '운전자산': '#5c6bc0',
  '금융투자': '#ab47bc',
  '여유자금': '#78909c',
}

function SectionBalanceSheet({ data }: { data: BalanceSheet }): React.ReactElement {
  const { periods, financing, assets } = data
  const financingKeys = Object.keys(financing)
  const assetsKeys = Object.keys(assets)

  // Compute totals per period for stacked bars
  const financingTotals = periods.map((_, i) =>
    financingKeys.reduce((sum, key) => sum + Math.abs(financing[key][i] ?? 0), 0)
  )
  const assetsTotals = periods.map((_, i) =>
    assetsKeys.reduce((sum, key) => sum + Math.abs(assets[key][i] ?? 0), 0)
  )
  const maxTotal = Math.max(...financingTotals, ...assetsTotals, 1)

  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">B/S 재분류</h3>
      <p className="analysis-section-desc">
        기업이 자금을 어디서 조달하여(부채+자본) 어디에 투자했는지(자산) 한눈에 비교합니다.
        주주몫이 클수록 자기자본 중심, 설비투자 비중이 높을수록 본업 집중도가 높은 기업입니다.
      </p>
      <div className="analysis-bs-chart">
        {/* Legend */}
        <div className="analysis-bs-legend">
          <span className="analysis-bs-legend-group">조달:</span>
          {financingKeys.map((key) => (
            <span key={key} className="analysis-bs-legend-item">
              <span className="analysis-bs-legend-dot" style={{ background: BS_COLORS[key] ?? '#6b7280' }} />
              {key}
            </span>
          ))}
          <span className="analysis-bs-legend-sep" />
          <span className="analysis-bs-legend-group">운용:</span>
          {assetsKeys.map((key) => (
            <span key={key} className="analysis-bs-legend-item">
              <span className="analysis-bs-legend-dot" style={{ background: BS_COLORS[key] ?? '#6b7280' }} />
              {key}
            </span>
          ))}
        </div>

        {/* Bars per period */}
        {periods.map((period, pi) => (
          <div key={period} className="analysis-bs-period">
            <span className="analysis-bs-period-label">{period}</span>
            <div className="analysis-bs-bars">
              {/* Financing bar */}
              <div className="analysis-bs-bar-row">
                <span className="analysis-bs-bar-label">조달</span>
                <div className="analysis-bs-bar-track">
                  {financingKeys.map((key) => {
                    const val = Math.abs(financing[key][pi] ?? 0)
                    const widthPct = (val / maxTotal) * 100
                    return (
                      <div
                        key={key}
                        className="analysis-bs-bar-segment"
                        style={{ width: `${widthPct}%`, background: BS_COLORS[key] ?? '#6b7280' }}
                        title={`${key}: ${fmtAmount(financing[key][pi])}`}
                      />
                    )
                  })}
                </div>
                <span className="analysis-bs-bar-total">{fmtAmount(financingTotals[pi])}</span>
              </div>
              {/* Assets bar */}
              <div className="analysis-bs-bar-row">
                <span className="analysis-bs-bar-label">운용</span>
                <div className="analysis-bs-bar-track">
                  {assetsKeys.map((key) => {
                    const val = Math.abs(assets[key][pi] ?? 0)
                    const widthPct = (val / maxTotal) * 100
                    return (
                      <div
                        key={key}
                        className="analysis-bs-bar-segment"
                        style={{ width: `${widthPct}%`, background: BS_COLORS[key] ?? '#6b7280' }}
                        title={`${key}: ${fmtAmount(assets[key][pi])}`}
                      />
                    )
                  })}
                </div>
                <span className="analysis-bs-bar-total">{fmtAmount(assetsTotals[pi])}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

// ── Section 4: 이익률 분해 ────────────────────────────────────────────────────

function SectionRateDecomposition({ data }: { data: RateDecomposition }): React.ReactElement {
  const { periods, operating_asset_return, non_operating_return, borrowing_rate, roe } = data

  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">이익률 분해</h3>
      <div className="analysis-table-wrap">
        <table className="analysis-table">
          <thead>
            <tr>
              <th>항목</th>
              {periods.map((p) => <th key={p}>{p}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>영업자산수익률</td>
              {operating_asset_return.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtPct(v)}</td>)}
            </tr>
            <tr>
              <td>비영업수익률</td>
              {non_operating_return.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtPct(v)}</td>)}
            </tr>
            <tr>
              <td>차입금금리</td>
              {borrowing_rate.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtPct(v)}</td>)}
            </tr>
            <tr>
              <td>ROE</td>
              {roe.map((v, i) => <td key={i} className={signColorClass(v)}>{fmtPct(v)}</td>)}
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ── Section 5: 이익 워터폴 (Redesigned) ──────────────────────────────────────

// Steps: [영업이익, 비영업이익, 이자비용, 세전이익, 법인세비용, 당기순이익, 비지배주주순이익, 지배주주순이익]
const SUBTOTAL_INDICES = new Set([0, 3, 5, 7])
const SUBTRACT_INDICES = new Set([2, 4, 6]) // 이자비용, 법인세비용, 비지배주주순이익

function SectionProfitWaterfall({ data }: { data: ProfitWaterfall }): React.ReactElement {
  const { steps } = data

  // First pass: compute bar positions with running total
  let running = 0
  const bars = steps.map((step, idx) => {
    if (SUBTOTAL_INDICES.has(idx)) {
      running = step.value
      return {
        ...step, isSubtotal: true, isAdd: true,
        barLeft: Math.min(0, step.value),
        barRight: Math.max(0, step.value),
      }
    }

    // Delta step: determine add or subtract
    const isSubtract = SUBTRACT_INDICES.has(idx) || step.value < 0
    if (isSubtract) {
      const absVal = Math.abs(step.value)
      const barRight = running
      const barLeft = running - absVal
      running = barLeft
      return { ...step, isSubtotal: false, isAdd: false, barLeft, barRight }
    } else {
      const barLeft = running
      const barRight = running + step.value
      running = barRight
      return { ...step, isSubtotal: false, isAdd: true, barLeft, barRight }
    }
  })

  // Compute global range across all bars
  let globalMin = 0
  let globalMax = 0
  for (const bar of bars) {
    globalMin = Math.min(globalMin, bar.barLeft)
    globalMax = Math.max(globalMax, bar.barRight)
  }
  const range = globalMax - globalMin || 1

  // Map position to percentage
  const toPct = (x: number): number => ((x - globalMin) / range) * 100

  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">이익 워터폴</h3>
      <div className="analysis-wf">
        {bars.map((bar, idx) => {
          const leftPct = toPct(bar.barLeft)
          const widthPct = Math.max(toPct(bar.barRight) - leftPct, 0.4)

          let barClass: string
          if (bar.isSubtotal) {
            barClass = idx === bars.length - 1 ? 'analysis-wf-bar--result' : 'analysis-wf-bar--subtotal'
          } else {
            barClass = bar.isAdd ? 'analysis-wf-bar--add' : 'analysis-wf-bar--sub'
          }

          const prefix = bar.isSubtotal ? '' : (bar.isAdd ? '+' : '\u2212')
          const showConnector = !bar.isSubtotal && idx > 0

          return (
            <div key={bar.name} className={`analysis-wf-row ${bar.isSubtotal ? 'analysis-wf-row--subtotal' : ''}`}>
              <span className={`analysis-wf-label ${bar.isSubtotal ? 'analysis-wf-label--bold' : ''}`}>
                {!bar.isSubtotal && (
                  <span className={`analysis-wf-sign ${bar.isAdd ? 'analysis-positive' : 'analysis-negative'}`}>{prefix}</span>
                )}
                {bar.name}
              </span>
              <div className="analysis-wf-track">
                {showConnector && (
                  <div
                    className="analysis-wf-connector"
                    style={{ left: `${bar.isAdd ? leftPct : leftPct + widthPct}%` }}
                  />
                )}
                <div
                  className={`analysis-wf-bar ${barClass}`}
                  style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                />
              </div>
              <span className={`analysis-wf-value ${bar.isSubtotal ? 'analysis-wf-value--bold' : (bar.isAdd ? 'analysis-positive' : 'analysis-negative')}`}>
                {bar.isSubtotal ? fmtAmount(bar.value) : `${bar.isAdd ? '' : '\u2212'}${fmtAmount(Math.abs(bar.value))}`}
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

// ── Section 6: 추세 ───────────────────────────────────────────────────────────

const DIRECTION_LABEL: Record<string, string> = { up: '상승', flat: '횡보', down: '하락' }

function TrendDirectionBadge({ direction }: { direction: 'up' | 'flat' | 'down' }): React.ReactElement {
  return (
    <span className={`analysis-trend-badge analysis-trend-badge--${direction}`}>
      {DIRECTION_LABEL[direction] ?? direction}
    </span>
  )
}

function SectionTrendSignals({ data }: { data: TrendSignals }): React.ReactElement {
  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">추세 신호</h3>
      <div className="analysis-table-wrap">
        <table className="analysis-table">
          <thead>
            <tr>
              <th>지표</th>
              <th>방향</th>
              <th>설명</th>
            </tr>
          </thead>
          <tbody>
            {data.signals.map((sig) => (
              <tr key={sig.name}>
                <td>{sig.name}</td>
                <td><TrendDirectionBadge direction={sig.direction} /></td>
                <td className="analysis-muted">{sig.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ── Section 7: 5대 질문 ───────────────────────────────────────────────────────

const STATUS_ICON: Record<string, string> = { ok: '\u2713', warn: '!', danger: '\u2717' }

function SectionFiveQuestions({ data }: { data: FiveQuestions }): React.ReactElement {
  const verdictClass =
    data.verdict === '양호' ? 'analysis-verdict--ok'
    : data.verdict === '보통' ? 'analysis-verdict--warn'
    : 'analysis-verdict--danger'

  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">
        5대 질문
        <span className={`analysis-verdict ${verdictClass}`}>{data.verdict}</span>
      </h3>
      <ul className="analysis-questions">
        {data.questions.map((q) => (
          <li key={q.question} className={`analysis-question analysis-question--${q.status}`}>
            <span className={`analysis-question-icon analysis-question-icon--${q.status}`}>
              {STATUS_ICON[q.status]}
            </span>
            <div className="analysis-question-body">
              <span className="analysis-question-text">{q.question}</span>
              <span className="analysis-question-detail">{q.detail}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

// ── Section 8: 활동성 ────────────────────────────────────────────────────────

const ACTIVITY_TOOLTIPS: Record<string, string> = {
  '매출채권 회전율': '매출액 ÷ 평균 매출채권. 외상 매출을 현금으로 회수하는 속도입니다. 높을수록 빠르게 현금화합니다.',
  '매출채권 회수기간': '365 ÷ 매출채권 회전율. 외상 매출 후 현금을 받기까지 걸리는 평균 일수입니다. 짧을수록 좋습니다.',
  '재고자산 회전율': '매출원가 ÷ 평균 재고자산. 재고가 팔려 나가는 속도입니다. 높을수록 재고 관리가 효율적입니다.',
  '재고 보유기간': '365 ÷ 재고자산 회전율. 재고를 매입해서 판매까지 걸리는 평균 일수입니다. 짧을수록 재고 부담이 적습니다.',
  '매입채무 회전율': '매출원가 ÷ 평균 매입채무. 공급업체에 대금을 지급하는 속도입니다. 낮을수록 결제 여유가 있습니다.',
  '매입채무 지급기간': '365 ÷ 매입채무 회전율. 원재료 매입 후 대금을 지급하기까지 걸리는 평균 일수입니다. 길수록 현금 여유가 있습니다.',
  '총자산 회전율': '매출액 ÷ 평균 총자산. 보유 자산 대비 매출 창출 효율입니다. 높을수록 자산을 효율적으로 활용합니다.',
  '현금전환주기': '현금을 투입해서 다시 현금으로 회수하기까지 걸리는 일수. 매입 대금 지급 전에 매출 현금이 들어오면 음수가 되어 자금 여유가 생깁니다.',
}

function fmtTurnover(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '-'
  return `${val.toFixed(1)}회`
}

function fmtDays(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '-'
  return `${val}일`
}

function CCCTimeline({ data }: { data: ActivityRatios }): React.ReactElement | null {
  // Use most recent year with valid CCC
  let idx = data.ccc.length - 1
  while (idx >= 0 && data.ccc[idx] === null) idx--
  if (idx < 0) return null

  const ccc = data.ccc[idx]!
  const recDays = data.receivable_days[idx] ?? 0
  const invDays = data.inventory_days[idx] ?? 0
  const payDays = data.payable_days[idx] ?? 0
  const totalSpan = Math.max(invDays + recDays, payDays, 1)

  const invPct = (invDays / totalSpan) * 100
  const recPct = (recDays / totalSpan) * 100
  const payPct = (payDays / totalSpan) * 100

  const cccColor = ccc < 0 ? 'var(--analysis-positive-color, #26a69a)' : ccc > 60 ? 'var(--analysis-negative-color, #ef5350)' : 'var(--analysis-muted-color, #78909c)'

  let interpretation: string
  if (ccc < 0) {
    interpretation = '매입 대금 지급 전에 매출이 현금화됩니다. 우수한 현금 순환 구조입니다.'
  } else if (ccc <= 60) {
    interpretation = `현금 투입 후 약 ${ccc}일 만에 회수됩니다.`
  } else {
    interpretation = `현금 회수에 ${ccc}일이 소요됩니다. 운전자본 부담에 주의가 필요합니다.`
  }

  return (
    <div className="analysis-ccc-timeline">
      <div className="analysis-ccc-bar-group">
        <div className="analysis-ccc-bar-row">
          <span className="analysis-ccc-bar-label">재고 보유</span>
          <div className="analysis-ccc-bar-track">
            <div className="analysis-ccc-bar analysis-ccc-bar--inventory" style={{ width: `${invPct}%`, left: '0%' }} />
          </div>
          <span className="analysis-ccc-bar-value">{invDays}일</span>
        </div>
        <div className="analysis-ccc-bar-row">
          <span className="analysis-ccc-bar-label">매출채권 회수</span>
          <div className="analysis-ccc-bar-track">
            <div className="analysis-ccc-bar analysis-ccc-bar--receivable" style={{ width: `${recPct}%`, left: `${invPct}%` }} />
          </div>
          <span className="analysis-ccc-bar-value">{recDays}일</span>
        </div>
        <div className="analysis-ccc-bar-row">
          <span className="analysis-ccc-bar-label">매입채무 지급</span>
          <div className="analysis-ccc-bar-track">
            <div className="analysis-ccc-bar analysis-ccc-bar--payable" style={{ width: `${payPct}%`, left: '0%' }} />
          </div>
          <span className="analysis-ccc-bar-value">{payDays}일</span>
        </div>
      </div>
      <div className="analysis-ccc-result" style={{ color: cccColor }}>
        <Tooltip text={ACTIVITY_TOOLTIPS['현금전환주기']}>
          <span className="analysis-indicator-name">현금전환주기 (CCC) = {ccc}일</span>
        </Tooltip>
      </div>
      <p className="analysis-ccc-interpretation">{interpretation}</p>
    </div>
  )
}

function SectionActivityRatios({ data }: { data: ActivityRatios }): React.ReactElement {
  const { periods } = data

  const rows: { name: string; values: (number | null)[]; fmt: (v: number | null) => string }[] = [
    { name: '매출채권 회전율', values: data.receivable_turnover, fmt: fmtTurnover },
    { name: '매출채권 회수기간', values: data.receivable_days, fmt: fmtDays },
    { name: '재고자산 회전율', values: data.inventory_turnover, fmt: fmtTurnover },
    { name: '재고 보유기간', values: data.inventory_days, fmt: fmtDays },
    { name: '매입채무 회전율', values: data.payable_turnover, fmt: fmtTurnover },
    { name: '매입채무 지급기간', values: data.payable_days, fmt: fmtDays },
    { name: '총자산 회전율', values: data.asset_turnover, fmt: fmtTurnover },
  ]

  return (
    <section className="analysis-section">
      <h3 className="analysis-section-title">활동성</h3>
      <div className="analysis-table-wrap">
        <table className="analysis-table">
          <thead>
            <tr>
              <th>지표</th>
              {periods.map((p) => <th key={p}>{p}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name}>
                <td>
                  <Tooltip text={ACTIVITY_TOOLTIPS[row.name] ?? ''}>
                    <span className="analysis-indicator-name">{row.name}</span>
                  </Tooltip>
                </td>
                {row.values.map((v, i) => <td key={i}>{row.fmt(v)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <CCCTimeline data={data} />
    </section>
  )
}

// ── Modal loading / error states ──────────────────────────────────────────────

function ModalLoading(): React.ReactElement {
  return (
    <div className="analysis-state-center">
      <span className="loading-spinner" />
      <span className="analysis-state-text">분석 중...</span>
    </div>
  )
}

function ModalError({ message, onRetry }: { message: string; onRetry: () => void }): React.ReactElement {
  return (
    <div className="analysis-state-center">
      <span className="analysis-state-error">{message}</span>
      <button className="analysis-retry-btn" onClick={onRetry}>다시 시도</button>
    </div>
  )
}

// ── Main AnalysisModal ────────────────────────────────────────────────────────

interface AnalysisModalProps {
  code: string
  companyName: string
  sectorMajor?: string | null
  sectorMinor?: string | null
  product?: string | null
  status: 'loading' | 'success' | 'error'
  data: AnalysisResponse | null
  errorMessage: string
  onClose: () => void
  onRetry: () => void
}

// @MX:ANCHOR: Fullscreen modal component — renders 7 analysis sections via portal
// @MX:REASON: Public component boundary; consumed by ChartCell via useAnalysis hook
export function AnalysisModal({
  code,
  companyName,
  sectorMajor,
  sectorMinor,
  product,
  status,
  data,
  errorMessage,
  onClose,
  onRetry,
}: AnalysisModalProps): React.ReactElement {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const handleBackdropClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose()
  }, [onClose])

  const modal = (
    <div
      className="analysis-backdrop"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label={`${companyName} (${code}) 재무 분석`}
    >
      <div className="analysis-modal">
        <div className="analysis-modal-header">
          <div className="analysis-modal-title">
            <div className="analysis-modal-title-row">
              <span className="analysis-modal-name">{companyName}</span>
              <span className="analysis-modal-code">{code}</span>
              <span className="analysis-modal-subtitle">재무 분석</span>
            </div>
            {sectorMajor && (
              <div className="analysis-modal-sector">
                {sectorMajor}
                {sectorMinor && <span className="analysis-modal-sector-sep">›</span>}
                {sectorMinor && sectorMinor}
                {product && <span className="analysis-modal-sector-sep">›</span>}
                {product && product}
              </div>
            )}
          </div>
          <button className="analysis-modal-close" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </div>

        <div className="analysis-modal-body" ref={scrollRef}>
          {status === 'loading' && <ModalLoading />}
          {status === 'error' && <ModalError message={errorMessage} onRetry={onRetry} />}
          {status === 'success' && data && (
            <>
              {data.summary && <SectionBusinessSummary summary={data.summary} />}
              {data.business_performance && <SectionBusinessPerformance data={data.business_performance} />}
              {data.health_indicators && <SectionHealthIndicators data={data.health_indicators} />}
              {data.balance_sheet && <SectionBalanceSheet data={data.balance_sheet} />}
              {data.rate_decomposition && <SectionRateDecomposition data={data.rate_decomposition} />}
              {data.profit_waterfall && <SectionProfitWaterfall data={data.profit_waterfall} />}
              {data.activity_ratios && <SectionActivityRatios data={data.activity_ratios} />}
              {data.trend_signals && <SectionTrendSignals data={data.trend_signals} />}
              {data.five_questions && <SectionFiveQuestions data={data.five_questions} />}
              {!data.business_performance && !data.health_indicators && !data.balance_sheet && (
                <div className="analysis-state-center">
                  <span className="analysis-state-error">이 종목은 재무 분석을 지원하지 않습니다.</span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )

  return ReactDOM.createPortal(modal, document.body)
}
