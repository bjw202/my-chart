// M7 — §0.3 제거 목록 X1~X6 + §1.2 보존 대상 10항목 정적 스캔.
//
// ?raw 소스 임포트로 수행한다(node:fs 미사용 — jsdom 환경에서 동작, tsc NEW-0 유지).
// 주의: 부재 확인 대상 문자열은 '부재를 단언하는 테스트 파일' 안에는 정당하게 등장한다
// (예: RRGChart.m5.test.tsx 의 /min: 75|max: 125/ 정규식 리터럴). 따라서 스캔 대상은
// **소스 파일만**이며 __tests__ 는 포함하지 않는다 — 오탐을 구조적으로 배제한다.
import { describe, it, expect } from 'vitest'

import sectorAnalysisSrc from '../SectorAnalysis.tsx?raw'
import bubbleChartSrc from '../BubbleChart.tsx?raw'
import sectorBubbleSrc from '../SectorBubbleChart.tsx?raw'
import sectorDetailSrc from '../SectorDetailPanel.tsx?raw'
import rrgSrc from '../RRGChart.tsx?raw'
import bumpSrc from '../BumpChart.tsx?raw'
import stockBubbleSrc from '../StockBubbleChart.tsx?raw'
import marketContextSrc from '../../../contexts/MarketContext.tsx?raw'
import stageBarSrc from '../../StockExplorer/StageDistributionBar.tsx?raw'
import stockExplorerSrc from '../../StockExplorer/StockExplorer.tsx?raw'

// 소스 전량(테스트 제외) — X4/X5 처럼 파일이 특정되지 않은 항목용.
const ALL_SOURCES = import.meta.glob(
  ['../../../**/*.ts', '../../../**/*.tsx'],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>

// 공허한 통과 방지 — 글롭이 비면 아래 모든 `toEqual([])` 가 무의미하게 통과한다.
// (import.meta.glob 은 경로를 임포트 파일 기준 상대경로로 정규화한다: '../SectorAnalysis.tsx')
if (Object.keys(ALL_SOURCES).length < 50) {
  throw new Error(`정적 스캔 대상이 비었다 (${Object.keys(ALL_SOURCES).length}개) — 글롭 패턴 확인 필요`)
}

function sourceHits(re: RegExp): string[] {
  const hits: string[] = []
  for (const [path, src] of Object.entries(ALL_SOURCES)) {
    if (path.includes('__tests__') || /\.(test|spec)\.tsx?$/.test(path)) continue
    for (const [i, line] of src.split('\n').entries()) {
      if (re.test(line)) hits.push(`${path}:${i + 1}: ${line.trim()}`)
    }
  }
  return hits
}

const count = (src: string, re: RegExp) => (src.match(new RegExp(re, 'g')) ?? []).length

// ── §0.3 제거 목록 X1~X6 ────────────────────────────────────────────────────
describe('§0.3 제거 목록 — X1~X6 가 실제로 제거되었다', () => {
  it('X1 — Table 툴바의 별도 기간 토글이 없다 (헤더 단일 인스턴스로 흡수)', () => {
    // 기간 토글 마크업은 SectorAnalysis 헤더에 정확히 1개.
    expect(count(sectorAnalysisSrc, /data-testid="period-toggle"/)).toBe(1)
    // 소스 전량에서도 정확히 1곳 — Table 툴바에 두 번째 인스턴스가 없다.
    expect(sourceHits(/data-testid="period-toggle"/)).toHaveLength(1)
  })

  it('X2 — Bubble 툴바의 별도 기간·시장 토글이 없다', () => {
    expect(bubbleChartSrc).not.toMatch(/data-testid="(period|market)-toggle"/)
    // period/market 을 헤더 Context 에서 소비한다는 계약이 살아 있다.
    expect(bubbleChartSrc).toMatch(/useAnalysisParams\(\)/)
  })

  it('X3 — 섹터 버블의 axisPointer 값 라벨 상자가 없다 (VZ-4)', () => {
    // @MX:NOTE 의 '재도입 금지' 주석은 실코드가 아니므로 주석행을 제외하고 센다.
    const codeLines = sectorBubbleSrc.split('\n').filter(l => !l.trim().startsWith('//'))
    expect(codeLines.filter(l => l.includes('axisPointer'))).toHaveLength(0)
  })

  it('X4 — `Sub-sector breakdown available in future update` 가 코드베이스에서 사라졌다', () => {
    expect(sourceHits(/Sub-sector breakdown available in future update/)).toEqual([])
    expect(sectorDetailSrc).not.toContain('Sub-sector breakdown available in future update')
  })

  it('X5 — crossTabParams / CrossTabParams 가 사라졌다 (NavIntent 로 대체)', () => {
    expect(sourceHits(/crossTabParams|CrossTabParams/)).toEqual([])
  })

  it('X6 — RRG 축 하드코딩 min:75 / max:125 가 사라졌다 (자동 대칭)', () => {
    // 소스 전량 기준 0행. RRGChart.m5.test.tsx 의 정규식 리터럴은 테스트 파일이라 스캔 대상 밖.
    expect(sourceHits(/min:\s*75|max:\s*125/)).toEqual([])
    expect(rrgSrc).not.toMatch(/min:\s*75|max:\s*125/)
    // 대체 구현(자동 대칭 반폭)이 실재한다 — 삭제만 하고 대체가 없으면 회귀다.
    expect(rrgSrc).toMatch(/export function rrgHalf/)
  })
})

// ── §1.2 보존 대상 10항목 ───────────────────────────────────────────────────
describe('§1.2 보존 대상 10항목 — 계약이 그대로 살아 있다', () => {
  it('1. Bump connectNulls: false (순위 제외 주를 선 끊김으로 표현)', () => {
    expect(count(bumpSrc, /connectNulls:\s*false/)).toBe(1)
    expect(bumpSrc).not.toMatch(/connectNulls:\s*true/)
  })

  it('2. Bump 날짜 합집합 축 (섹터별 길이가 달라도 축 일관)', () => {
    // 전 섹터 history 날짜를 Set 으로 합집합 후 정렬하는 구조 — 섹터별 길이가 달라도 축이 같다.
    expect(bumpSrc).toMatch(/const dateSet = new Set<string>\(\)/)
    expect(bumpSrc).toMatch(/sector\.history\.forEach\(w => dateSet\.add\(w\.date\)\)/)
    expect(bumpSrc).toMatch(/Array\.from\(dateSet\)\.sort\(\)/)
  })

  it('3. 종목 버블 색상 = 산업명(중) — @MX:ANCHOR 결정성 매핑 보존', () => {
    expect(stockBubbleSrc).toMatch(/@MX:ANCHOR: \[AUTO\] 색상 결정성 매핑/)
    expect(stockBubbleSrc).toMatch(/sector_minor/)
    // 색상을 Stage 로 재배정하지 않았다.
    expect(stockBubbleSrc).not.toMatch(/itemStyle.*color.*stage|color:\s*stageColor/)
  })

  it('4. 종목 버블 `기타` 범례 처리 (오버플로·null 흡수)', () => {
    expect(stockBubbleSrc).toMatch(/'기타'/)
    expect(stockBubbleSrc).toMatch(/legendFormatter/)
  })

  it('5. RRG/Bump focus: \'series\' (선 차트 궤적 추적)', () => {
    expect(count(rrgSrc, /focus:\s*'series'/)).toBe(1)
    expect(count(bumpSrc, /focus:\s*'series'/)).toBe(1)
  })

  it('6. MarketContext TTL + refresh()', () => {
    expect(marketContextSrc).toMatch(/CACHE_TTL_MS/)
    expect(marketContextSrc).toMatch(/refresh/)
  })

  it('7. Promise.allSettled 독립 실패', () => {
    expect(count(marketContextSrc, /Promise\.allSettled/)).toBe(1)
  })

  it('8. 지수 백오프 2/4/8초 (MarketContext + StockExplorer 공유 계약)', () => {
    expect(marketContextSrc).toMatch(/\[2000,\s*4000,\s*8000\]/)
    expect(stockExplorerSrc).toMatch(/\[2000,\s*4000,\s*8000\]/)
  })

  it('9. Stage 세그먼트 토글 해제 (같은 세그먼트 재클릭 → 해제)', () => {
    // 현재 선택과 같은 세그먼트를 다시 누르면 null 로 되돌린다 (TR-11 토글 해제).
    expect(stageBarSrc).toMatch(/if \(activeStage === stageKey\) \{\s*\n\s*onStageClick\(null\)/)
  })

  it('10. tooltip XSS 이스케이프 (StockBubbleChart 방어적 코딩)', () => {
    expect(stockBubbleSrc).toMatch(/function escapeHtml/)
    // tooltip formatter 안에서 실제로 사용된다 — 정의만 남고 호출이 빠지면 회귀다.
    expect(count(stockBubbleSrc, /escapeHtml\(/)).toBeGreaterThan(1)
  })
})

// ── M7 이 건드린 차트 3종에서 보존 계약이 깨지지 않았음 (D2 부수 확인) ──────
describe('D2 — 차트 tooltip 수정이 §1.2 보존 항목을 건드리지 않았다', () => {
  it('StockBubbleChart 는 D2 대상이 아니며 XSS 이스케이프 경로가 그대로다', () => {
    // D2 는 섹터버블·RRG·Bump 의 결측 문자열만 바꿨다. 종목 버블은 미수정.
    expect(stockBubbleSrc).not.toMatch(/metricText/)
    expect(stockBubbleSrc).toMatch(/const name = escapeHtml\(/)
  })

  it('섹터버블·RRG·Bump 는 metricText 를 쓰되 다른 계약은 그대로다', () => {
    expect(sectorBubbleSrc).toMatch(/metricText\(toMetricValue\(/)
    expect(rrgSrc).toMatch(/metricText\(toMetricValue\(/)
    expect(bumpSrc).toMatch(/metricText\(/)
    // metricText 출력은 숫자 포맷 문자열 또는 상수('–' / '계산 불가' / '⚠' / '❗')뿐이라
    // HTML 메타문자를 만들지 않는다 — 세 차트의 tooltip 은 사용자 입력을 싣지 않는다.
    expect(bumpSrc).not.toMatch(/innerHTML/)
    expect(rrgSrc).not.toMatch(/innerHTML/)
    expect(sectorBubbleSrc).not.toMatch(/innerHTML/)
  })
})

// ── AC-SUX-010 — 복귀 시 컨텍스트 보존 (SM-8). M1~M6 미기록분을 M7 에서 판정한다 ──
import appContentSrc from '../../../AppContent.tsx?raw'
import sectorAnalysisTabSrc from '../SectorAnalysis.tsx?raw'

describe('AC-SUX-010 — 탭 왕복 시 컨텍스트 보존 (SM-8)', () => {
  it('상단 탭이 keep-mounted 다 — 조건부 언마운트가 아니라 display 토글이다', () => {
    // 조건부 렌더(`activeTab === 'x' && <Comp/>`)면 탭을 떠날 때 로컬 상태가 소멸한다.
    // 5개 탭 전부 display 토글로 상시 마운트되어야 subTab·sortField·stageFilter·체크가 보존된다.
    const displayToggles = (appContentSrc.match(/display: activeTab === '[a-z-]+' \? 'flex' : 'none'/g) ?? [])
    expect(displayToggles.length).toBeGreaterThanOrEqual(5)
    // 탭 본문을 조건부로 언마운트하는 패턴이 없다.
    expect(appContentSrc).not.toMatch(/activeTab === '[a-z-]+' && </)
  })

  it('서브탭도 keep-mounted 다 (M5 AC-SUX-017 개편 — subTab/sortField 보존의 전제)', () => {
    expect(sectorAnalysisTabSrc).toMatch(/mountedTabs/)
    expect(sectorAnalysisTabSrc).toMatch(/display: subTab === /)
  })

  it('탭 내비게이션 전용 뒤로가기 버튼이 렌더 트리에 없다', () => {
    // 주의: BubbleChart 의 `← 섹터 목록` 은 Bubble 서브탭 **내부의 드릴다운 복귀**이며
    // 탭 내비게이션용이 아니다 — AC-SUX-010 이 금지하는 대상이 아니다. 아래는 탭 이동용
    // 뒤로가기(history/goBack/setActiveTab 되돌리기) 컴포넌트의 부재를 확인한다.
    expect(sourceHits(/history\.back|goBack|<BackButton/)).toEqual([])
  })

  it('period·selectedSector 는 탭 위 Provider 소유라 탭 전환과 무관하다', () => {
    // 두 값이 탭 컴포넌트의 로컬 state 였다면 탭을 떠날 때 소멸한다.
    expect(appContentSrc).not.toMatch(/useState.*selectedSector/)
    expect(appContentSrc).not.toMatch(/useState.*period/)
  })
})
