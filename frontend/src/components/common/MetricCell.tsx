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

// @MX:ANCHOR: [AUTO] metricDisplay — 5상태 해석 + 표시 문자열 생성의 단일 출처.
//   MetricCell(표 DOM)과 ECharts tooltip formatter(섹터버블·RRG·Bump)가 같은 함수를 호출한다.
// @MX:REASON: D2 — 표 셀과 차트 툴팁이 각자 결측을 표기하면 같은 값이 화면마다 '–' / '-' /
//   'NaN' 으로 갈린다(M6 종료 시점 실측된 AC-SUX-052 debt). 두 소비자가 같은 함수를 호출해야
//   문자열 동등이 구조적으로 보장된다. ECharts tooltip 은 formatter 문자열이라 DOM 을 갖지 않으므로
//   스타일 병행은 불가능하다 — 이 함수가 통일하는 것은 '텍스트'다.
export interface MetricDisplay {
  state: CellState
  text: string
  // 상태 설명 툴팁. DOM 소비자(MetricCell)만 사용하며 차트 tooltip 문자열에는 싣지 않는다.
  title?: string
}

export function metricDisplay(value: MetricValue, format?: (n: number) => string): MetricDisplay {
  const obj = normalize(value)
  const state = resolveState(obj)

  if (state === 'missing') return { state, text: MISSING_TEXT }
  if (state === 'insufficient') return { state, text: INSUFFICIENT_TEXT, title: INSUFFICIENT_TITLE }

  // 여기부터 obj.value 는 유한 숫자임이 resolveState 로 보장된다.
  const text = format ? format(obj.value as number) : String(obj.value)

  if (state === 'warning') return { state, text: `${text} ❗`, title: (obj.warnings ?? []).join(' / ') }
  if (state === 'low-confidence') return { state, text: `${text} ⚠`, title: LOW_CONFIDENCE_TITLE }
  return { state, text }
}

// 표시 문자열만 필요한 소비자용 (ECharts tooltip formatter).
export function metricText(value: MetricValue, format?: (n: number) => string): string {
  return metricDisplay(value, format).text
}

// 차트 데이터 배열의 원시 좌표값 → MetricValue.
// Number(null) === 0 이므로 무조건 Number() 로 감싸면 결측이 실제 0 으로 둔갑한다(ER-2 위반).
// null/undefined 는 결측으로 보존하고, 유한수가 아닌 값도 결측으로 접는다.
export function toMetricValue(v: unknown): MetricValue {
  if (v === null || v === undefined) return null
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : null
}

export interface MetricCellProps {
  value: MetricValue
  // 숫자 → 표시 문자열. 기본은 숫자 그대로 (예: RS 42 → "42").
  format?: (n: number) => string
  className?: string
}

export function MetricCell({ value, format, className }: MetricCellProps): ReactElement {
  const { state, text, title } = metricDisplay(value, format)
  const cls = ['metric-cell', `metric-cell--${state}`, className].filter(Boolean).join(' ')
  return (
    <span className={cls} data-testid="metric-cell" data-state={state} title={title}>
      {text}
    </span>
  )
}
