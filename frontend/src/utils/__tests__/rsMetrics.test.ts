// SPEC-SECTOR-DISPLAY-UNIFY-001 M6 — REQ-SDU-003 / AC-SDU-003 (G-F1 확정 형태)
// 교차 언어 상수 등식: 백엔드 my_chart/analysis/sector_metrics.py 의 비공개 심볼
// _RS_TOP_THRESHOLD (=80.0, float) 를 vite import 없이 Node fs 로 읽어 정규식 추출 +
// parseFloat → 수치 등식을 단언한다. 문자열 등식이 아니다 (80.0 !== '80').
//
// 경로는 import.meta.url 기준으로 해석한다 — vitest 실행 CWD 가정은 깨지기 쉽다(D6).
// .py 는 vite 모듈 그래프 밖이며 로더 대상도 아니므로 import 시도 자체가 금지다.
// 양변이 손으로 옮겨 적은 상수 비교가 되지 않도록 한쪽은 반드시 .py 원문에서 나온다.
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import {
  RS_TOP_THRESHOLD,
  RS_STRONG_THRESHOLD,
  RS_S2_STRONG_THRESHOLD,
  RS_UNIVERSE_MIDPOINT,
} from '../rsMetrics'

// frontend/src/utils/__tests__/ → 루트: ../../../../ (tests → utils → src → frontend → root)
// vitest(jsdom) 은 import.meta.url 을 file: 이 아닌 http://localhost/@fs/<절대경로> 형태로
// 주므로 두 형태를 모두 처리한다 — 어느 쪽이든 기준은 import.meta.url 이지 CWD 가 아니다(D6).
function resolveFromModuleUrl(rel: string): string {
  const url = import.meta.url.split('?')[0]
  if (url.startsWith('file://')) {
    return fileURLToPath(new URL(rel, url))
  }
  const marker = '/@fs/'
  const idx = url.indexOf(marker)
  if (idx === -1) throw new Error(`import.meta.url 에서 파일 경로를 유도할 수 없다: ${url}`)
  const absDir = decodeURIComponent(url.slice(idx + marker.length, url.lastIndexOf('/') + 1))
  return `${absDir}${rel}`
}

const PY_PATH = resolveFromModuleUrl('../../../../my_chart/analysis/sector_metrics.py')

function extractPyNumber(symbol: string): number {
  const src = readFileSync(PY_PATH, 'utf-8')
  const m = src.match(new RegExp(`^${symbol}\\s*=\\s*([0-9]+(?:\\.[0-9]+)?)`, 'm'))
  if (!m) throw new Error(`${symbol} 정의를 sector_metrics.py에서 찾지 못했다 — 경로/심볼 확인 필요`)
  return parseFloat(m[1])
}

describe('rsMetrics — 백엔드 상수 미러 (REQ-SDU-003)', () => {
  it('RS_TOP_THRESHOLD === 백엔드 _RS_TOP_THRESHOLD (수치 등식: 80 === 80.0)', () => {
    const backend = extractPyNumber('_RS_TOP_THRESHOLD')
    expect(Number.isFinite(backend)).toBe(true)
    expect(RS_TOP_THRESHOLD).toBe(backend)
  })

  it('프론트 소유 상수 3종은 명세 값을 유지한다', () => {
    // 70/60/50 은 백엔드에 같은 이름의 상수가 없는 프론트 소유 임계값이다
    // (REQ-SDU-003 이 값 자체를 규정). 값 고정으로 우발 변경을 방지한다.
    expect(RS_STRONG_THRESHOLD).toBe(70)
    expect(RS_S2_STRONG_THRESHOLD).toBe(60)
    expect(RS_UNIVERSE_MIDPOINT).toBe(50)
  })
})
