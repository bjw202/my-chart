import type { StockItem } from '../../types/stock'

// @MX:NOTE: [AUTO] 체크된 종목 그룹 키 규칙 — backend/services/screen_service.py:221-223의
//   버킷 규칙과 byte-exact 동일해야 함 (major 폴백 "기타", minor 폴백 "", 조인 " > ").
//   @MX:REASON: 정렬 순서는 Python sorted()와 동일한 코드포인트 오름차순(기본 .sort())이어야
//   백엔드 응답의 섹터 순서와 프론트 체크목록 순서가 일치함
export function sectorKeyOf(stock: StockItem): string {
  const major = stock.sector_major || '기타'
  const minor = stock.sector_minor || ''
  return minor ? `${major} > ${minor}` : major
}

export function buildCheckedGroups(stocks: StockItem[]): { sectorName: string; stocks: StockItem[] }[] {
  const buckets = new Map<string, StockItem[]>()
  for (const s of stocks) {
    const key = sectorKeyOf(s)
    const bucket = buckets.get(key)
    if (bucket) {
      bucket.push(s)
    } else {
      buckets.set(key, [s])
    }
  }
  // 기본 .sort() = UTF-16 코드 유닛 오름차순 ≡ BMP 내 코드포인트 순 (한글 섹터명 전역) — localeCompare 금지
  return [...buckets.keys()]
    .sort()
    .map((sectorName) => ({ sectorName, stocks: buckets.get(sectorName) as StockItem[] }))
}
