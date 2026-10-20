// RS 임계값 상수 — SPEC-SECTOR-DISPLAY-UNIFY-001 REQ-SDU-003 (M6)
// 백엔드 my_chart/analysis/sector_metrics.py 의 비공개 상수들(_RS_TOP_THRESHOLD 등)의
// 프론트 미러. 교차 언어 등식은 __tests__/rsMetrics.test.ts 가 .py 파일을 직접 읽어
// 수치로 단언한다(문자열 등식 아님 — 80.0 !== '80').
// 술어에 이 상수를 쓰는 곳은 반드시 상수 유래 title 도 함께 달아
// "임계값이 왜 80인지"가 화면에서 읽히게 한다(REQ-SDU-003).

// RS 상위권 판정 임계값 — 백엔드 _RS_TOP_THRESHOLD = 80.0 의 거울.
// 'RS 80+ 비중' 열(RS≥80 종목 비율)의 정의와 rsHighlight 술어가 공유한다.
export const RS_TOP_THRESHOLD = 80

// 강세 등급 임계값 — 백엔드 stage_classifier._STAGE2_ENTRY_RS_MIN(Stage 2 진입 RS 하한)의 거울.
// 값 동일성은 __tests__/rsMetrics.test.ts 교차 언어 등식이 지킨다 (SPEC-RS-REBALANCE-001 D13).
export const RS_STRONG_THRESHOLD = 70

// Stage 2 strong 판정 임계값 — StockTable getStageBadgeClass 의 s2-strong 술어.
// 백엔드 stage_classifier._STAGE2_RS_STRONG 의 거울 (교차 언어 등식으로 고정).
export const RS_S2_STRONG_THRESHOLD = 60

// 유니버스 백분위 중앙 — 섹터 버블 markLine(RS 중앙선)의 Y 좌표.
export const RS_UNIVERSE_MIDPOINT = 50

// 열기(heat) 배지 — SPEC-RS-REBALANCE-001 REQ-RSR-015·016·022 (D3·Q4).
// 술어: 주간 RS_1M_Rating(응답의 rs_1m) >= 임계값. 결측(null/undefined)은 배지 없음 — 높은 값으로 메우지 않는다.
// 임계값은 인자로 받는다: 호출부가 RS_TOP_THRESHOLD 를 넘겨야 상수 교체가 배지 경계를 함께 움직인다
// (모듈 내부 바인딩을 쓰면 테스트의 상수 주입이 술어에 닿지 않는다 — rsHeat.injected.test.tsx).
export function isRsHeat(rs1m: number | null | undefined, threshold: number): boolean {
  return rs1m != null && rs1m >= threshold
}

// 열기 배지 표시 문구와 상수 유래 title (REQ-RSR-016, REQ-SDU-003 관행).
export const RS_HEAT_LABEL = '열기'

export function rsHeatTitle(threshold: number): string {
  return `최근 1개월 RS ${threshold} 이상 — 단기 강세(열기)`
}
