// AC-SUX-024 (REQ-SUX-022): 정렬 시 null 처리 단위 테스트.
import { describe, it, expect } from 'vitest'
import { compareNumericNullsLast } from '../sort'

describe('AC-SUX-024 — compareNumericNullsLast', () => {
  it('오름차순에서 null 이 맨 뒤로 간다', () => {
    const vals: (number | null)[] = [5, null, 3, null, 9]
    const sorted = [...vals].sort((a, b) => compareNumericNullsLast(a, b, 'asc'))
    expect(sorted).toEqual([3, 5, 9, null, null])
  })

  it('내림차순에서도 null 이 맨 뒤로 간다 (방향 무관)', () => {
    const vals: (number | null)[] = [5, null, 3, null, 9]
    const sorted = [...vals].sort((a, b) => compareNumericNullsLast(a, b, 'desc'))
    expect(sorted).toEqual([9, 5, 3, null, null])
  })

  it('NaN 도 null 처럼 마지막에 둔다 (NaN 비교로 순서 흔들림 방지)', () => {
    const vals: (number | null)[] = [5, NaN, 3, 9]
    const sorted = [...vals].sort((a, b) => compareNumericNullsLast(a, b, 'asc'))
    // 3,5,9 그 뒤에 NaN
    expect(sorted.slice(0, 3)).toEqual([3, 5, 9])
    expect(Number.isNaN(sorted[3])).toBe(true)
  })

  it('동일 입력 3회 정렬 결과가 동일하다 (결정성)', () => {
    const vals: (number | null)[] = [5, null, 3, null, 9, 1, null, 7]
    const r1 = [...vals].sort((a, b) => compareNumericNullsLast(a, b, 'asc'))
    const r2 = [...vals].sort((a, b) => compareNumericNullsLast(a, b, 'asc'))
    const r3 = [...vals].sort((a, b) => compareNumericNullsLast(a, b, 'asc'))
    expect(r1).toEqual(r2)
    expect(r2).toEqual(r3)
  })

  it('null 끼리는 순서를 바꾸지 않는다 (0 반환)', () => {
    expect(compareNumericNullsLast(null, null, 'asc')).toBe(0)
    expect(compareNumericNullsLast(null, null, 'desc')).toBe(0)
  })

  it('undefined 도 null 처럼 마지막으로 보낸다', () => {
    const vals: (number | null | undefined)[] = [5, undefined, 3]
    const sorted = [...vals].sort((a, b) => compareNumericNullsLast(a, b, 'asc'))
    expect(sorted).toEqual([3, 5, undefined])
  })
})
