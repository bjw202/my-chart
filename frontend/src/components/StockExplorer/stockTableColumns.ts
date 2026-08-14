// REQ-SUX-058 / AC-SUX-061 (O-U7 결정): 종목 표 좁은 화면 열 접기 순서 — 단일 상수 배열.
// 컴포넌트마다 다시 적으면 발산하므로 이 한 곳에서 정의한다.
//
// 접기 순서: 섹터비중 → Vol배 → 52W고 (3단계).
// 기간 3열(1W%/1M%/3M%) · Stage · RS · Name 은 어떤 폭에서도 접지 않는다(Lesson #3 —
// default 진입 가시성 AC-SUX-032 의 취지). 3열 전부 접은 뒤에도 넘치면 가로 스크롤(추가 접기 금지).
//
// 값은 StockTable 의 column key 와 일치한다.
export const COLLAPSE_ORDER = [
  'weight_in_sector', // 섹터비중 — 1순위 접기
  'volume_ratio',     // Vol배 — 2순위
  'near_52w_high',    // 52W고 — 3순위
] as const

// 어떤 폭에서도 숨기지 않는 열(Lesson #3 게이트).
export const INVARIANT_COLUMN_KEYS = [
  'name',
  'stage',
  'rs_12m',
  'chg_1w',
  'chg_1m',
  'chg_3m',
] as const

// collapseLevel(0..3) 에서 숨겨야 할 column key 집합. COLLAPSE_ORDER 의 단일 소스에서 도출.
export function hiddenColumnKeys(collapseLevel: number): ReadonlySet<string> {
  const n = Math.max(0, Math.min(COLLAPSE_ORDER.length, collapseLevel))
  return new Set(COLLAPSE_ORDER.slice(0, n))
}
