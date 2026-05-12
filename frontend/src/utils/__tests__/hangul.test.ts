/**
 * SPEC-CHART-SEARCH-001 T2/T2b RED — 한글 유틸 + 영문 alias 테스트
 *
 * AC-SEARCH-005: extractInitialConsonants 초성 추출 정확성
 * AC-SEARCH-006: matchesQuery 4단계 score + 동점 tiebreaker
 * AC-SEARCH-011: 영문 alias 매칭 score 5 (T2b)
 */

import { describe, it, expect } from 'vitest'
import { extractInitialConsonants, matchesQuery } from '../hangul'

// ---------------------------------------------------------------------------
// AC-SEARCH-005 — 초성 추출
// ---------------------------------------------------------------------------

describe('extractInitialConsonants', () => {
  it('삼성전자 → ㅅㅅㅈㅈ', () => {
    expect(extractInitialConsonants('삼성전자')).toBe('ㅅㅅㅈㅈ')
  })

  it('한화솔루션 → ㅎㅎㅅㄹㅅ', () => {
    expect(extractInitialConsonants('한화솔루션')).toBe('ㅎㅎㅅㄹㅅ')
  })

  it('ASCII 통과 — A → A', () => {
    expect(extractInitialConsonants('A')).toBe('A')
  })

  it('숫자 통과 — 1 → 1', () => {
    expect(extractInitialConsonants('1')).toBe('1')
  })

  it('혼합 — 삼A1 → ㅅA1', () => {
    expect(extractInitialConsonants('삼A1')).toBe('ㅅA1')
  })

  it('빈 문자열 → 빈 문자열', () => {
    expect(extractInitialConsonants('')).toBe('')
  })

  it('쌍방울 → ㅆㅂㅇ (쌍자음 ㅆ 포함)', () => {
    expect(extractInitialConsonants('쌍방울')).toBe('ㅆㅂㅇ')
  })
})

// ---------------------------------------------------------------------------
// AC-SEARCH-006 — matchesQuery 4단계 score + tiebreaker
// ---------------------------------------------------------------------------

describe('matchesQuery', () => {
  const items = [
    { code: '005930', name: '삼성전자' },
    { code: '000660', name: 'SK하이닉스' },
    { code: '005490', name: 'POSCO홀딩스' },
  ]

  it('코드 prefix (005) → score 4', () => {
    const r = matchesQuery(items[0], '005')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(4)
  })

  it('POSCO코드 prefix (005) → score 4 (동점)', () => {
    const r = matchesQuery(items[2], '005')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(4)
  })

  it('종목명 prefix (삼성) → score 3', () => {
    const r = matchesQuery(items[0], '삼성')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(3)
  })

  it('종목명 substring (전자) → score 2', () => {
    const r = matchesQuery(items[0], '전자')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(2)
  })

  it('초성 매칭 (ㅅㅅㅈㅈ) → score 1', () => {
    const r = matchesQuery(items[0], 'ㅅㅅㅈㅈ')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(1)
  })

  it('매칭 없음 → matched false', () => {
    const r = matchesQuery(items[0], 'xyz')
    expect(r.matched).toBe(false)
    expect(r.score).toBe(0)
  })

  it('빈 query → matched false', () => {
    const r = matchesQuery(items[0], '')
    expect(r.matched).toBe(false)
  })

  it('대소문자 — SK와 sk 모두 SK하이닉스 매칭', () => {
    expect(matchesQuery(items[1], 'SK').matched).toBe(true)
    expect(matchesQuery(items[1], 'sk').matched).toBe(true)
  })

  it('공백 trim — "  005  " → 005 동일 결과', () => {
    const r = matchesQuery(items[0], '  005  ')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(4)
  })
})

// ---------------------------------------------------------------------------
// AC-SEARCH-011 — 영문 alias 매칭 score 5 (T2b)
// ---------------------------------------------------------------------------

describe('matchesQuery — English alias (score 5)', () => {
  const samsung = { code: '005930', name: '삼성전자' }
  const skhynix = { code: '000660', name: 'SK하이닉스' }
  const koreanAir = { code: '003490', name: '대한항공' }

  it('samsung → 삼성전자 score 5', () => {
    const r = matchesQuery(samsung, 'samsung')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(5)
  })

  it('sk hynix → SK하이닉스 score 5', () => {
    const r = matchesQuery(skhynix, 'sk hynix')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(5)
  })

  it('SAMSUNG 대소문자 정규화 → score 5', () => {
    const r = matchesQuery(samsung, 'SAMSUNG')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(5)
  })

  it('  samsung   공백 trim 정규화 → score 5', () => {
    const r = matchesQuery(samsung, '  samsung  ')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(5)
  })

  it('alias prefix sams → 삼성전자 score 5', () => {
    const r = matchesQuery(samsung, 'sams')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(5)
  })

  it('samsung electronics (긴 alias) → score 5', () => {
    const r = matchesQuery(samsung, 'samsung electronics')
    expect(r.matched).toBe(true)
    expect(r.score).toBe(5)
  })

  it('대한항공은 alias 미보유 — korean air → matched false', () => {
    const r = matchesQuery(koreanAir, 'korean air')
    expect(r.matched).toBe(false)
  })

  it('사전에 없는 영문 unknown → matched false', () => {
    const r = matchesQuery(samsung, 'unknown')
    expect(r.matched).toBe(false)
  })
})
