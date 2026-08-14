// AC-SUX-028 (REQ-SUX-026): Bump 축 하단 weeks/span_days 병기 포맷.
// **프론트가 값을 계산하지 않고 응답을 그대로 표기**한다 — weeks*7 로 span_days 를
// 유도하지 않고 응답의 span_days 필드를 그대로 쓴다. 응답에 span_days 가 없으면 일수 표기 생략.
// @MX:SPEC: SPEC-SECTOR-UX-001 M4 AC-SUX-028
export function formatWeeksSpan(weeks: number, spanDays: number | null | undefined): string {
  if (spanDays == null) return `${weeks}주`
  return `${weeks}주 (${spanDays}일)`
}
