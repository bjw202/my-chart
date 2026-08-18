// RS 임계값 상수 — SPEC-SECTOR-DISPLAY-UNIFY-001 REQ-SDU-003 (M6)
// 백엔드 my_chart/analysis/sector_metrics.py 의 비공개 상수들(_RS_TOP_THRESHOLD 등)의
// 프론트 미러. 교차 언어 등식은 __tests__/rsMetrics.test.ts 가 .py 파일을 직접 읽어
// 수치로 단언한다(문자열 등식 아님 — 80.0 !== '80').
// 술어에 이 상수를 쓰는 곳은 반드시 상수 유래 title 도 함께 달아
// "임계값이 왜 80인지"가 화면에서 읽히게 한다(REQ-SDU-003).

// RS 상위권 판정 임계값 — 백엔드 _RS_TOP_THRESHOLD = 80.0 의 거울.
// 'RS 80+ 비중' 열(RS≥80 종목 비율)의 정의와 rsHighlight 술어가 공유한다.
export const RS_TOP_THRESHOLD = 80

// 강세 등급 임계값 — 백엔드 산출의 강세 판정과 정렬.
export const RS_STRONG_THRESHOLD = 70

// Stage 2 strong 판정 임계값 — StockTable getStageBadgeClass 의 s2-strong 술어.
export const RS_S2_STRONG_THRESHOLD = 60

// 유니버스 백분위 중앙 — 섹터 버블 markLine(RS 중앙선)의 Y 좌표.
export const RS_UNIVERSE_MIDPOINT = 50
