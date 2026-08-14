// AC-SUX-034 / REQ-SUX-032 / LD-B — 쿼리 캐시 계층 (D4: Context 내부 Map + TTL 1h)
// 외부 캐시 라이브러리(React Query 등)는 도입하지 않는다 (D1 무도입, Lesson #5 — MarketContext 기존 패턴 확산).

// TTL 상수 — 단일 위치에 정의되며 전 엔드포인트가 공유한다 (AC-SUX-034 "TTL 상수가 단일 위치에 정의되고 전 엔드포인트가 공유한다").
// 근거: MarketContext.tsx 의 기존 CACHE_TTL_MS 값을 전 엔드포인트로 일관화 (A3 — 주봉 데이터 주 1회 갱신, 1h TTL 은 보수적).
export const CACHE_TTL_MS = 60 * 60 * 1000 // 1시간 (3_600_000ms)

export interface CacheEntry<T> {
  data: T
  // 기록 시각 (Date.now()). TTL 만료 판정에 사용.
  at: number
}

// TTL 만료 판정 — now - at > CACHE_TTL_MS (AC-SUX-034: 59분 fresh / 61분 stale).
export function isStale(at: number, now: number = Date.now()): boolean {
  return now - at > CACHE_TTL_MS
}

// Map 기반 쿼리 캐시 — queryKey → {data, at} (D4 / SN-5).
// grid_version 변경 감지 시 Map 을 통째로 비운다 (SN-5: 격자 규칙이 바뀌면 grid_version 변경으로 전 캐시 무효화).
export class QueryCache<T = unknown> {
  private readonly entries = new Map<string, CacheEntry<T>>()
  private gridVersion: string | null = null

  // grid_version 변경 시 전 캐시 무효화 (SN-5). 최초 설정(=null 통과)은 비우지 않는다.
  setGridVersion(version: string): void {
    if (this.gridVersion !== null && this.gridVersion !== version) {
      this.entries.clear()
    }
    this.gridVersion = version
  }

  get(key: string, now: number = Date.now()): T | undefined {
    const entry = this.entries.get(key)
    if (!entry) return undefined
    if (isStale(entry.at, now)) {
      // 만료 엔트리는 제거 후 누락 반환 (재조회 트리거).
      this.entries.delete(key)
      return undefined
    }
    return entry.data
  }

  set(key: string, data: T, now: number = Date.now()): void {
    this.entries.set(key, { data, at: now })
  }

  // 수동 전체 무효화 (새로고침 버튼 — REQ-SUX-034 ⟳ 새로고침).
  clear(): void {
    this.entries.clear()
  }

  get size(): number {
    return this.entries.size
  }
}
