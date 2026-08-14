// 공용 지표 셀 — SPEC-SECTOR-UX-001 M6 / D6 / 규칙 ER-1·ER-2 (AC-SUX-052, AC-SUX-053)
import type { ReactElement } from 'react'

// @MX:NOTE: [AUTO] MetricCell — ER-1 셀 5상태(결측 – / 실제 0 / 계산 불가 / 저신뢰 ⚠ / 경고 ❗)를
//   단일 컴포넌트가 전부 처리한다. 화면(순위표·섹터버블·RRG·Bump·종목탐색)마다 표기가 갈리는 것을
//   구조적으로 막기 위한 D6 결정이며, 5개 화면이 이 컴포넌트만 사용한다.
//   0/50.0 렌더 금지 사유(ER-2): 결측을 0 이나 중립값(50.0)으로 채우면 "값이 0이다" 와
//   "값이 없다" 가 화면에서 구분 불가해진다. 특히 RS 의 50.0 은 '평균 수준'이라는 실제 의미가
//   있어 결측 대체값으로 쓰면 사용자가 오독한다. 결측은 반드시 '–' 로만 렌더한다.
//   무조건 toFixed 경로도 같은 이유로 금지 — null.toFixed 는 런타임 예외, NaN.toFixed 는 'NaN' 누출.

export const MISSING_TEXT = '–'
export const INSUFFICIENT_TEXT = '계산 불가'

const INSUFFICIENT_TITLE = '표본이 부족해 계산할 수 없습니다'
const LOW_CONFIDENCE_TITLE = '표본 커버리지가 낮아 값의 신뢰도가 낮습니다'

// 결측 사유 — 'missing'(값이 아예 없음) vs 'insufficient'(표본 부족으로 계산 불가)
export type MetricReason = 'missing' | 'insufficient'

export interface MetricObject {
  value: number | null | undefined
  reason?: MetricReason
  low_confidence?: boolean
  warnings?: string[]
}

// 셀이 받을 수 있는 값 — 원시 숫자 / null / undefined / 봉투 객체
export type MetricValue = number | null | undefined | MetricObject

type CellState = 'missing' | 'insufficient' | 'ok' | 'low-confidence' | 'warning'

// 숫자 전용 포맷터 — 결측을 받지 않는다. 호출 전에 MetricCell 이 결측을 걸러낸다.
export function percent1(n: number): string {
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`
}

export function percent2(n: number): string {
  return `${n > 0 ? '+' : ''}${n.toFixed(2)}%`
}

function normalize(value: MetricValue): MetricObject {
  if (value === null || value === undefined) return { value: null }
  if (typeof value === 'number') return { value }
  return value
}

function resolveState(obj: MetricObject): CellState {
  const n = obj.value
  const isMissing = n === null || n === undefined || Number.isNaN(n)
  if (isMissing) return obj.reason === 'insufficient' ? 'insufficient' : 'missing'
  if (obj.warnings && obj.warnings.length > 0) return 'warning'
  if (obj.low_confidence) return 'low-confidence'
  return 'ok'
}

export interface MetricCellProps {
  value: MetricValue
  // 숫자 → 표시 문자열. 기본은 숫자 그대로 (예: RS 42 → "42").
  format?: (n: number) => string
  className?: string
}

export function MetricCell({ value, format, className }: MetricCellProps): ReactElement {
  const obj = normalize(value)
  const state = resolveState(obj)
  const cls = ['metric-cell', `metric-cell--${state}`, className].filter(Boolean).join(' ')

  if (state === 'missing') {
    return <span className={cls} data-testid="metric-cell" data-state={state}>{MISSING_TEXT}</span>
  }
  if (state === 'insufficient') {
    return (
      <span className={cls} data-testid="metric-cell" data-state={state} title={INSUFFICIENT_TITLE}>
        {INSUFFICIENT_TEXT}
      </span>
    )
  }

  // 여기부터 obj.value 는 유한 숫자임이 resolveState 로 보장된다.
  const text = format ? format(obj.value as number) : String(obj.value)

  if (state === 'warning') {
    return (
      <span className={cls} data-testid="metric-cell" data-state={state} title={(obj.warnings ?? []).join(' / ')}>
        {text} ❗
      </span>
    )
  }
  if (state === 'low-confidence') {
    return (
      <span className={cls} data-testid="metric-cell" data-state={state} title={LOW_CONFIDENCE_TITLE}>
        {text} ⚠
      </span>
    )
  }
  return <span className={cls} data-testid="metric-cell" data-state={state}>{text}</span>
}
