// AC-SUX-024 (REQ-SUX-022): 정렬 시 null/NaN 값을 항상 마지막에 둔다 (정렬 방향 무관).
// 현행 getSortValue 의 NaN 비교로 순서가 흔들리던 결함(ST-... )을 제거한다.
// 동일 입력에 대해 정렬 결과가 항상 동일(결정성)하다.
// @MX:SPEC: SPEC-SECTOR-UX-001 M4 AC-SUX-024

export function compareNumericNullsLast(
  a: number | null | undefined,
  b: number | null | undefined,
  direction: 'asc' | 'desc',
): number {
  const aAbsent = a == null || Number.isNaN(a)
  const bAbsent = b == null || Number.isNaN(b)
  // null/NaN 은 방향과 무관하게 항상 뒤로 — asc/desc 모두 마지막.
  if (aAbsent && bAbsent) return 0
  if (aAbsent) return 1
  if (bAbsent) return -1
  const av = a as number
  const bv = b as number
  return direction === 'asc' ? av - bv : bv - av
}
