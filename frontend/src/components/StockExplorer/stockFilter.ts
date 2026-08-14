import type { Stage2Candidate } from '../../types/stage'

// @MX:ANCHOR: [AUTO] 종목 표 모집단 판정의 단일 출처 — 표(StockTable)·빈 상태·푸터 종목 수가
// 모두 이 술어를 통과한 같은 집합을 센다.
// @MX:REASON: 같은 조건을 두 곳에서 각각 구현했을 때 푸터(52)와 표(44)가 서로 다른 모집단을
// 가리키는 결함이 발생했다. 술어를 복제하면 같은 종류의 불일치가 재발한다.

// 분류 불가(unclassified) 종목 판정 — stage 가 1~4 범위 밖이면 분류 불가 (AC-SUX-030).
export function isUnclassified(c: Stage2Candidate): boolean {
  return c.stage == null || ![1, 2, 3, 4].includes(c.stage)
}

export interface StockFilterState {
  // number = stage 1-4 필터 · 'unclassified' = 분류 불가만(AC-SUX-030) · null = 전체
  stageFilter: number | 'unclassified' | null
  // sector_major 만 비교(REQ-SUX-054 철회 — 중분류 산업명 분기 추가 금지)
  sectorFilter: string | null
  // AC-SUX-018/054: 헤더 시장 토글 — 'all' 이면 필터하지 않는다.
  marketFilter?: 'all' | 'kospi' | 'kosdaq'
}

export function filterCandidates(
  candidates: Stage2Candidate[],
  { stageFilter, sectorFilter, marketFilter = 'all' }: StockFilterState,
): Stage2Candidate[] {
  return candidates.filter((c) => {
    if (stageFilter === 'unclassified') {
      if (!isUnclassified(c)) return false
    } else if (stageFilter !== null && c.stage !== stageFilter) {
      return false
    }
    if (sectorFilter && c.sector_major !== sectorFilter) return false
    if (marketFilter !== 'all' && (c.market ?? '').toLowerCase() !== marketFilter) return false
    return true
  })
}
