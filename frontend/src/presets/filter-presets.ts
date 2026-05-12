// @MX:NOTE: [AUTO] 프리셋 레지스트리 — 단일 진실 원천(SSOT)
// @MX:REASON: 프리셋 추가/변경 시 반드시 이 파일과 SPEC-PRESET-001 §4.2를 함께 업데이트해야 한다.
// @MX:SPEC: SPEC-PRESET-001 REQ-PST-001, §4.2
import type { Preset } from '../types/filter'

/**
 * v1 프리셋 레지스트리 (3종 고정).
 * 사용자 정의 프리셋은 별도 SPEC에서 다룬다.
 */
export const FILTER_PRESETS: readonly Preset[] = [
  {
    id: 'minervini_full',
    label: '미너비니 풀',
    description: 'Mark Minervini Trend Template 8조건 엄격 적용. SPEC-MINERVINI-001 필요.',
    // REQ-PST-012 v1.0.2: DB 안내 툴팁 (정확 일치 검증 대상)
    // SMA150 / LOW_52W / SMA200_20D_AGO 가 SPEC-MINERVINI-001 §1.4 의 신규 컬럼.
    // HIGH_52W 는 이미 존재하므로 "고저가" 가 아닌 "저가" 만 명시한다.
    tooltip:
      'SMA150 · 52주 저가(LOW_52W) · 20일 전 SMA200(SMA200_20D_AGO) 컬럼이 필요합니다. DB 업데이트(파일 재생성)를 먼저 실행하세요.',
    patch: {
      minervini_trend_template: true,
      rs_min: 70,
      market_cap_min: 1000,
    },
  },
  {
    id: 'breakout_init',
    label: 'Stage2 돌파',
    description: 'EMA20 위 거래 중이고 SMA50/SMA200을 넘어선 추세 전환 초입 종목. RS 70 이상, 1주 수익률 3%+.',
    patch: {
      market_cap_min: 1000,
      rs_min: 70,
      chg_1w_min: 3,
      pattern_logic: 'AND',
      patterns: [
        { indicator_a: 'Close', operator: 'gt', indicator_b: 'EMA20', multiplier: 1.0 },
        { indicator_a: 'EMA20', operator: 'gt', indicator_b: 'SMA50', multiplier: 1.0 },
        { indicator_a: 'Close', operator: 'gt', indicator_b: 'SMA200', multiplier: 1.0 },
      ],
    },
  },
  {
    id: 'stage1_accumulation',
    label: 'Stage1 매집',
    description: 'SMA200 ±5% 박스권에서 횡보하며 이평선이 수렴하는 바닥 형성 구간. 급락 종목 제외 (1개월 -5% 이상).',
    patch: {
      market_cap_min: 1000,
      chg_1m_min: -5,
      pattern_logic: 'AND',
      patterns: [
        { indicator_a: 'Close', operator: 'gt', indicator_b: 'SMA200', multiplier: 0.95 },
        { indicator_a: 'Close', operator: 'lt', indicator_b: 'SMA200', multiplier: 1.05 },
        { indicator_a: 'SMA50', operator: 'lt', indicator_b: 'SMA200', multiplier: 1.02 },
      ],
    },
  },
] as const
