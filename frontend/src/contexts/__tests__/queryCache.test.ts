// RED: AC-SUX-034 — TTL 1h 단일 위치 정의 + 전 엔드포인트 공유 + grid_version 무효화
import { describe, it, expect } from 'vitest'
import { CACHE_TTL_MS, isStale, QueryCache } from '../queryCache'

describe('AC-SUX-034 — queryCache TTL + grid_version 무효화', () => {
  it('CACHE_TTL_MS 가 정확히 1시간(3_600_000ms)이며 단일 상수로 export 된다', () => {
    // 단일 위치 정의 — 전 엔드포인트가 이 값을 공유한다 (LD-B / AC-SUX-034)
    expect(CACHE_TTL_MS).toBe(60 * 60 * 1000)
    expect(CACHE_TTL_MS).toBe(3_600_000)
  })

  it('59분 경과 → fresh (fetch 불필요), 61분 경과 → stale (fetch 필요)', () => {
    const recordedAt = 0
    const min59 = 59 * 60 * 1000
    const min61 = 61 * 60 * 1000
    // 59분 — TTL 이내 → fresh
    expect(isStale(recordedAt, min59)).toBe(false)
    // 61분 — TTL 초과 → stale
    expect(isStale(recordedAt, min61)).toBe(true)
  })

  it('정확히 60분(경계)은 fresh 이다 — now - at > TTL 판정이므로 60분은 초과 아님', () => {
    expect(isStale(0, CACHE_TTL_MS)).toBe(false)
    expect(isStale(0, CACHE_TTL_MS + 1)).toBe(true)
  })

  it('QueryCache.get — fresh 엔트리는 데이터 반환, stale 엔트리는 undefined 반환 후 삭제', () => {
    const cache = new QueryCache<string>()
    cache.set('key-A', 'data-A', 0)
    // 59분 — fresh
    expect(cache.get('key-A', 59 * 60 * 1000)).toBe('data-A')
    // 61분 — stale → undefined
    expect(cache.get('key-A', 61 * 60 * 1000)).toBeUndefined()
  })

  it('grid_version 변경 시 전 캐시가 무효화된다 (SN-5: 격자 규칙 변경 → 전체 무효화)', () => {
    const cache = new QueryCache<string>()
    cache.setGridVersion('canonical-v1')
    cache.set('key-A', 'data-A')
    cache.set('key-B', 'data-B')
    expect(cache.size).toBe(2)

    // 동일 grid_version → 유지
    cache.setGridVersion('canonical-v1')
    expect(cache.size).toBe(2)

    // 다른 grid_version → 전체 비움
    cache.setGridVersion('canonical-v2')
    expect(cache.size).toBe(0)
    expect(cache.get('key-A')).toBeUndefined()
  })

  it('clear() 수동 무효화', () => {
    const cache = new QueryCache<string>()
    cache.setGridVersion('v1')
    cache.set('k', 'v')
    expect(cache.size).toBe(1)
    cache.clear()
    expect(cache.size).toBe(0)
  })
})
