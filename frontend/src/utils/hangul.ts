/**
 * 한글 초성 추출 + 종목 검색 매칭 유틸 (REQ-SEARCH-003)
 *
 * NFR-CONST-001: 외부 라이브러리 미사용 — 자체 구현
 *
 * @MX:NOTE: [AUTO] (code - 0xAC00) / 588 산식으로 초성 index 계산.
 *   5단계 score: alias(5) > 코드prefix(4) > 명prefix(3) > 명substring(2) > 초성prefix(1)
 *   alias 사전: frontend/src/utils/hangul-aliases.ts (시총·외국인 거래 비중 상위 50종)
 */

import { STOCK_ALIASES } from './hangul-aliases'

const INITIAL_CONSONANTS = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'

export function extractInitialConsonants(s: string): string {
  let result = ''
  for (const ch of s) {
    const code = ch.charCodeAt(0)
    if (code >= 0xac00 && code <= 0xd7a3) {
      result += INITIAL_CONSONANTS[Math.floor((code - 0xac00) / 588)]
    } else {
      result += ch
    }
  }
  return result
}

export interface MatchResult {
  matched: boolean
  score: number
}

export function matchesQuery(
  item: { code: string; name: string },
  query: string,
): MatchResult {
  if (!query) return { matched: false, score: 0 }
  const q = query.trim()
  if (!q) return { matched: false, score: 0 }

  const qLower = q.toLowerCase()

  // score 5: 영문 alias prefix 매칭
  const aliases = STOCK_ALIASES[item.name]
  if (aliases) {
    for (const alias of aliases) {
      if (alias.startsWith(qLower)) {
        return { matched: true, score: 5 }
      }
    }
  }

  // score 4: 숫자 query이고 종목코드가 해당 prefix로 시작
  if (/^\d+$/.test(q) && item.code.startsWith(q)) {
    return { matched: true, score: 4 }
  }

  const nameLower = item.name.toLowerCase()

  // score 3: 종목명이 query로 시작
  if (nameLower.startsWith(qLower)) {
    return { matched: true, score: 3 }
  }

  // score 2: 종목명에 query가 포함
  if (nameLower.includes(qLower)) {
    return { matched: true, score: 2 }
  }

  // score 1: 초성 매칭 (query 전체가 초성 문자로만 구성된 경우)
  if (/^[ㄱ-ㅎ]+$/.test(q) && extractInitialConsonants(item.name).startsWith(q)) {
    return { matched: true, score: 1 }
  }

  return { matched: false, score: 0 }
}
