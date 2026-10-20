# SPEC-RS-REBALANCE-001 — 구현 계획 (plan)

> 원천: `spec.md`(요구사항), `acceptance.md`(검증), `research.md`(관측 근거 R1~R12).
> 실행 주체: `manager-develop`, `cycle_type=tdd` (`.moai/config/sections/quality.yaml` `constitution.development_mode: "tdd"`).
> 이 문서는 바뀔 가능성이 큰 결정부터 적고(§B 조사 결정, §C 데이터 모델), 기계적 단계는 뒤(§F)에 둔다.

## §A 핵심 결정 요약 (전사, 재논의 금지)

| 항목 | 결정 | 출처 |
|---|---|---|
| `RS_12M_Rating` 산식 | 비율 기반 IBD식 `S = 0.4q1 + 0.2(q2+q3+q4)` → 백분위 × 100 | spec.md §2.3, Q1 |
| 섹터 RS 표시 | `rs_avg` 유지 + `rs_med` 추가 + `rs_top_pct` 병기 | Q2 |
| 분모 필터 | 지수 행 · 거래량 0 · 우선주 · 스팩. 50억 유동성 규칙은 분모에 쓰지 않음 | D5, Q3 |
| 열기 배지 | `rs_1m >= RS_TOP_THRESHOLD`(현재 80), 가속 배지 없음 | Q4 |
| 낡은 행 정리 | "이번 실행이 쓰지 않은 행은 모두 삭제": (i) 비처리 날짜 행 선행 삭제 + (ii) 날짜별 집합 차 삭제(같은 트랜잭션). 짝 없는 행은 (i)·(ii)에 포함되므로 별도 조항 없음. 테이블 전체 삭제는 기각 — `weekly.py:7`의 의도된 UPSERT 설계, 중단 시 빈 테이블 | D7 2판 + plan-audit iter-1 D1 (계획서 §4 "제외"의 잔재는 무효 처리) |
| 섹터 종합 점수 가중치 | 불변 | D1 |
| 임계값 | 측정 후 결정(M3), 숫자 선결정 금지 | D6 |

## §B 조사에서 드러난 결정 (2026-10-20 해소)

조사(research.md)에서 계획서가 다루지 않은 결정 세 가지가 드러났고, 같은 날 사용자가 결정했다. 결정 본문은 spec.md §2.4에 고정되어 있다.

| # | 채택 | 기각한 대안 | 실행 영향 |
|---|---|---|---|
| B-1 우선주·스팩 판별 | (a) 등록부 코드 끝자리 ≠ `0` → 우선주, 이름에 `스팩` → 스팩 | 이름 패턴 `우$`·`우B$`·`우C$`(보통주 3개 오탐, 허용 목록 수작업) / 규칙 생략 + 등록부 가드 테스트(D5를 코드로 이행하지 않음) | `generate_rs_db()`가 `get_stock_registry()`(`registry.py:108-119`, `Code, Name, Market`)의 `Code`를 이름으로 조인. 현재 등록부에서는 제외 대상 0개(R3) — 사전 가드 |
| B-2 `stock_meta.rs_1m` 소비처 | (a) Phase 4에서 채우고 API 노출까지만 | `screen_service.py` 응답 + `ChartGrid/ChartCell.tsx` 배지 연결(약 4개 파일) — 후속 과제 | 종목 테이블·버블 배지는 주간 `RS_1M_Rating`(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)에서 공급 |
| D13 70/60 소유권과 T8 | 소유권은 `SPEC-SECTOR-DISPLAY-UNIFY-001`에 그대로 두고 값만 양쪽에서 변경. T8(`screen_service.py:61`)은 `_STAGE2_ENTRY_RS_MIN` 참조 | T8 리터럴 70 독립 유지 | `rsMetrics.test.ts:50-54` 리터럴 단언을 백엔드 추출 비교로 교체 |
| B-3 재보정 범위 | (a) Stage 2 상수 70/60과 거울 `RS_STRONG_THRESHOLD`·`RS_S2_STRONG_THRESHOLD`만 | 80도 재보정하고 배지용 상수 분리 / 80을 재보정하고 배지가 따라감 | `_RS_TOP_THRESHOLD`/`RS_TOP_THRESHOLD`는 80 유지. 근거는 백분위 순위의 성질(80 이상 몫 ≈ 20%) — 라이브 DB 실측 20.08% / 20.04%(plan-audit iter-1), 재측정 20.02% / 20.01%(research.md R13). `momentum.py`·`queries.py`는 변경 대상에서 빠짐 |

## §C 데이터 모델 변경 (변경 가능성이 큰 순)

| 대상 | 변경 | 비고 |
|---|---|---|
| `relative_strength` | 스키마 불변, 값 의미 변경(`RS_12M_Rating`), 지수·거래량 0·고아 행 소거 | REQ-RSR-001~009 |
| `stock_meta` | `rs_1m REAL` 컬럼 1개, **테이블 끝** 추가 + 멱등 ALTER | REQ-RSR-010·011, research.md R6 |
| `StageStock`(`backend/schemas/stage.py:36`) · `StockBubbleItem`(`backend/schemas/sector_advanced.py:48`) | `rs_1m: float \| None` 추가 | REQ-RSR-012 |
| `SectorAggregate` 봉투(`backend/schemas/envelope.py:95-96`) · `SectorRankItem`(`backend/schemas/sector.py:26`) · 레거시 dataclass(`sector_metrics.py:107-108`) | `rs_med` 추가 (봉투는 `MetricValueModel`, 랭킹 항목은 `float \| None`) | REQ-RSR-013 |
| 프론트 타입 `types/stage.ts`, `types/bubble.ts`, `types/market.ts` | `rs_1m?`, `rs_med` 추가 | REQ-RSR-015·017 |

## §D 파일 목록과 Tier 판정

명령(재현용, 코드 cwd에서 실행):

```bash
for f in my_chart/db/weekly.py my_chart/analysis/stage_classifier.py my_chart/analysis/sector_metrics.py my_chart/analysis/sector_advanced.py backend/services/meta_service.py backend/services/stage_service.py backend/services/sector_advanced_service.py backend/services/sector_ranking_service.py backend/services/screen_service.py backend/schemas/stage.py backend/schemas/sector.py backend/schemas/sector_advanced.py backend/schemas/envelope.py frontend/src/utils/rsMetrics.ts frontend/src/types/stage.ts frontend/src/types/bubble.ts frontend/src/types/market.ts frontend/src/components/StockExplorer/StockTable.tsx frontend/src/components/SectorAnalysis/StockBubbleChart.tsx frontend/src/components/SectorAnalysis/SectorRankingTable.tsx scripts/rs_eval/stock_rs_eval.py docs/rs-timeline-eli5.html scripts/rs_eval/stage2_ratio_eval.py; do [ -f "$f" ] && e=$((e+1)) || echo "new: $f"; done; echo "existing=$e"
```

관측 출력: `new: scripts/rs_eval/stage2_ratio_eval.py`, `existing=22` — 합계 23개(기존 22 + M3 신설 1). 구성: Python(`my_chart/`·`backend/`) 13, 프론트 7, 스크립트 2, 문서 1. B-3 결정으로 `my_chart/screening/momentum.py`, `my_chart/db/queries.py`(80/90 기준)는 목록에서 빠졌다.

| # | 경로 | 변경 종류 | 마일스톤 |
|---|---|---|---|
| 1 | `my_chart/db/weekly.py` | 수정 — 선행 삭제, 분모 필터, IBD식 | M1, M2 |
| 2 | `my_chart/analysis/stage_classifier.py` | 수정 — 임계값(M3), 주간 질의에 `RS_1M_Rating` 추가(M4) | M3, M4 |
| 3 | `my_chart/analysis/sector_metrics.py` | 수정 — `rs_med` 집계·응답 | M4 |
| 4 | `my_chart/analysis/sector_advanced.py` | 수정 — `_get_rs_on_date()`에 `RS_1M_Rating` | M4 |
| 5 | `backend/services/meta_service.py` | 수정 — `rs_1m` 복사, ALTER 목록 | M4 |
| 6 | `backend/services/stage_service.py` | 수정 — `rs_1m` 전달 | M4 |
| 7 | `backend/services/sector_advanced_service.py` | 수정 — `rs_1m` 전달 | M4 |
| 8 | `backend/services/sector_ranking_service.py` | 수정 — `rs_med` 전달(`:69-83`) | M4 |
| 9 | `backend/services/screen_service.py` | 수정 — `:61` 리터럴 70 → 상수 참조 | M3 |
| 10 | `backend/schemas/stage.py` | 수정 — `rs_1m` | M4 |
| 11 | `backend/schemas/sector.py` | 수정 — `rs_med` | M4 |
| 12 | `backend/schemas/sector_advanced.py` | 수정 — `rs_1m` | M4 |
| 13 | `backend/schemas/envelope.py` | 수정 — `rs_med` | M4 |
| 14 | `frontend/src/utils/rsMetrics.ts` | 수정 — 재보정 값 반영, 열기 배지 술어 | M3, M5 |
| 15 | `frontend/src/types/stage.ts` | 수정 — `rs_1m` | M5 |
| 16 | `frontend/src/types/bubble.ts` | 수정 — `rs_1m` | M5 |
| 17 | `frontend/src/types/market.ts` | 수정 — `rs_med` | M5 |
| 18 | `frontend/src/components/StockExplorer/StockTable.tsx` | 수정 — `:39` 리터럴 → 상수(M3), 열기 배지(M5) | M3, M5 |
| 19 | `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` | 수정 — 툴팁 열기 배지 | M5 |
| 20 | `frontend/src/components/SectorAnalysis/SectorRankingTable.tsx` | 수정 — `rs_med` 열 | M5 |
| 21 | `scripts/rs_eval/stock_rs_eval.py` | 신규 추적 + `--production`·`--db <경로>` 모드 추가 | M2, M6 |
| 22 | `docs/rs-timeline-eli5.html` | 수정 — 새 산식 설명 | M6 |
| 23 | `scripts/rs_eval/stage2_ratio_eval.py` | 신규 — `--mode conditional`(조건부 RS 통과율, 70)·`--mode strong`(Stage 2 강세 비중, 60) 측정(REQ-RSR-018) | M3 |

테스트 파일은 별도(§G).

**Tier 판정: L.** 마일스톤 6개(≥3)이고 운영 코드 대상 파일이 23개(≥10)다. 경계값이 아니므로 "더 단순한 쪽" 규칙은 적용되지 않는다. Tier L 표준 산출물 중 `design.md`는 별도로 만들지 않는다 — 설계 결정은 spec.md §2와 이 문서 §A~§C에 이미 고정되어 있어 같은 내용을 한 번 더 쓰게 된다. `research.md`는 작성했다.

## §E 위험

| 위험 | 영향 | 완화 |
|---|---|---|
| (i)·(ii) 삭제 단계를 빼고 재생성 | 짝 없는 행 119,881개와 짝 있는 낡은 행이 옛 산식 값으로 남아 한 테이블에 두 공식이 섞임(D7) | M1을 M2보다 먼저 커밋. AC-RSR-001이 (i)·(ii) 제거 시 6행, (i)만 제거 시 5행으로 RED, AC-RSR-017이 짝 기준 삭제로 바꿔치기 시 3행으로 RED |
| 라이브 DB 재생성의 비가역성 | 재생성 후에는 변경 전 기준선을 같은 경로로 다시 잴 수 없음 | M2 착수 시 (1) 변경 전 기준선 측정을 재생성보다 먼저 수행 (2) `Output/stock_data_weekly.db`를 `.bak_<날짜>`로 복사(선례: `stock_data_weekly.db.bak_20260422_124345`) |
| 우선주 이름 패턴 오탐 | 보통주 3개가 RS 등급을 잃음 | B-1 코드 끝자리 규칙 + AC-RSR-003 음성 사례 |
| `stock_meta` 위치 삽입 시프트 | `rs_1m`을 튜플 중간에 넣으면 이후 컬럼 값이 한 칸씩 밀림(레거시 컬럼명 불일치까지 겹침, R6) | REQ-RSR-011 끝 덧붙임 + AC-RSR-008 레거시 테이블 왕복 |
| 고정 픽스처 기대값 표류 | `aggregation-2026-08-11/weekly.db`는 옛 산식 값·지수 행을 유지하므로, 픽스처를 읽는 테스트는 값이 바뀌지 않는다. 반대로 M3 임계값 변경은 이 픽스처 위의 Stage 2 분류 결과를 바꿀 수 있음 | M3에서 임계값이 바뀌면 영향 테스트(§G)를 재실행해 표류를 목록화하고, 기대값 갱신 근거를 progress.md에 기록 |
| 짝이 있는 낡은 행 | 지수 600행·거래량 0 행 16,369행·비기준 날짜 5행은 `stock_prices` 짝이 있어 쌍 기준 삭제로 지워지지 않고 UPSERT로도 덮이지 않음(R2.1) — 최신 주차의 거래량 0 행 101개가 `stock_meta.rs_12m`·섹터 `rs_avg`·Stage 분류로 흘러감 | REQ-RSR-001 (ii) 날짜별 집합 차 삭제 + AC-RSR-017 |
| 테스트의 축약 `relative_strength` DDL | 13개 테스트 파일이 `RS_12M_Rating`만 있는 축약 DDL을 만든다(§G). M4가 주간 질의에 `RS_1M_Rating`을 추가하면 이 경로를 타는 테스트가 `no such column`으로 실패 | M4에서 전체 테스트를 먼저 돌려 RED 파일을 확정하고 해당 DDL에 컬럼 추가. 운영 코드에 컬럼 부재 허용 분기는 넣지 않음(운영 스키마는 REQ-RSR-009로 고정) |
| 재보정이 Stage 2 모집단을 바꿈 | 스크리닝·섹터 `stage2_pct`가 달라짐 | REQ-RSR-018의 (a) 상대 ±10%·(b) ±5%p 목표와 기록 의무 |
| 70 기준의 판별력 부족 | 진입 비율은 RS 조건이 거의 묶지 않아(plan-audit iter-2: 임계값 50~80에서 1.057~1.074%) 어떤 값도 통과. 조건부 RS 통과율도 plan 단계 실측에서 60/70/80 폭 2.15%p로 상대 ±10%보다 작음(R15) | 판별력 사전 조건을 AC-RSR-015에 두고, 미충족이면 70은 "기록만"으로 격하 — 70 유지 |
| 회귀 계측이 프로덕션을 읽지 않음 | 스크립트 재실행이 산식 구현 오류를 잡지 못함(R9) | M2에서 `relative_strength`를 읽는 프로덕션 경로 모드 추가, AC-RSR-014 |
| `stock_prices`의 1~2행 주중 날짜 13개 | RS 처리 대상 아님 — 영향 없음. 다만 M1의 쌍 기준 삭제가 이 날짜의 RS 행(9,963행)을 지움 | 의도된 결과. 범위 밖 정리는 하지 않음 |

## §F 마일스톤

M1은 M2보다 반드시 먼저다(고아 행 정리가 재생성에 앞서야 한다). M3는 M2의 새 분포가 있어야 측정할 수 있다. M4는 M1~M3와 코드상 독립이나 계획서 순서를 유지한다.

### M1 — 분모 정리와 낡은 행 제거 (Priority High)

- RED 전 특성화: 현행 `generate_rs_db()`에 research.md R10 픽스처를 넣어 `RS_6M/3M/1M_Rating` 출력을 골든값으로 캡처하고 **단독 커밋**한다(AC-RSR-006의 기준).
- 공용 픽스처 빌더 `tests/rsr_fixtures.py`(`price_row`, `make_weekly_db`) 신설 — 모든 가격 행의 전 컬럼을 채운다(acceptance.md 머리말).
- (i) 비처리 날짜 행 선행 삭제, (ii) 필터 후 이름 집합에 없는 `Date = d` 행 삭제와 삽입을 같은 트랜잭션으로(REQ-RSR-001·004).
- 날짜별 분모 필터: 지수 행, 거래량 0, 우선주·스팩(B-1: 코드 끝자리 ≠ `0`, 이름에 `스팩`), `1+R ≤ 0` 행, 결측 수익률 행(현행 `dropna` 유지)(REQ-RSR-002·003·007·023).
- 종료 조건: AC-RSR-001·002·003·004·017·018 PASS(임시 DB 픽스처). 라이브 수치는 M2 재생성 후 확인한다.

### M2 — IBD식 재가중과 재생성 (Priority High)

- `scripts/rs_eval/stock_rs_eval.py`에 `--production`과 `--db <경로>`를 추가하고 추적 대상으로 넣는다. 프로덕션 모드는 점수만 `relative_strength.RS_12M_Rating`으로 바꾸고 유니버스 규칙(`:19-21`, `:71`, `:74`, `:76`, `:99`)은 그대로 쓴다.
- 라이브 DB를 `Output/snapshots/weekly_before_rsr.db`로 복사하고, **재생성 전에** 그 사본에서 기준선을 잰다(AC-RSR-014 첫 명령).
- `RS_12M_Rating`을 IBD식으로 바꾸고(REQ-RSR-005·006) 라이브 DB를 재생성한 뒤 `Output/snapshots/weekly_after_rsr.db`로 복사한다.
- 종료 조건: AC-RSR-005·006·014(목표 ≥ 60)·016 PASS. 재생성 후 라이브 DB에서 AC-RSR-001·002·017의 라이브 단계 질의가 모두 `0`.

### M3 — Stage 2 상수 재보정 (Priority High)

- `scripts/rs_eval/stage2_ratio_eval.py --db <경로> --weeks 12 --mode {conditional|strong} --threshold <값>` 신설. 주차 집합 W = 두 사본에 모두 있는 `삼성전자` 날짜 중 최근 12개. `conditional`은 RS 외 진입 조건 다섯 개를 통과한 종목 중 RS 조건 통과 비중(70 기준), `strong`은 Stage 2 종목 중 "Stage 2 Strong" 비중(60 기준). 분모는 모두 가격 테이블로 정해진다(REQ-RSR-018).
- 먼저 변경 전 사본에서 `conditional`을 임계값 60·70·80으로 측정해 판별력 사전 조건(엄격 단조 + `c60 − c80 > 0.10 × c70`)을 판정·기록한다. 미충족이면 70은 "기록만"(유지). plan 단계 실측은 미충족을 예고한다(research.md R15).
- 60은 (1) 변경 전·현행, (2) 변경 후·현행, (3) 변경 후·채택 값을 측정하고 ±5%p 안의 값을 채택한다. 채택 상수는 `stage_classifier.py` 한 곳에서만 바꾼다.
- `screen_service.py:61`(T8)을 `_STAGE2_ENTRY_RS_MIN` 참조로, `StockTable.tsx:39`를 상수 참조로 교체(REQ-RSR-019, D13). `_RS_TOP_THRESHOLD`(80)는 바꾸지 않는다(B-3).
- `rsMetrics.test.ts`의 리터럴 단언(`:50-54`)을 `stage_classifier.py` 상수 추출 비교로 교체. 소유권은 그대로 둔다(D13).
- 종료 조건: AC-RSR-013·015 PASS.

### M4 — 백엔드 필드 (Priority Medium)

- `stock_meta.rs_1m`: DDL 마지막 컬럼 + 멱등 ALTER + 튜플 28번째 값(REQ-RSR-010·011).
- `stage_classifier.py` 주간 질의와 `sector_advanced.py` `_get_rs_on_date()`에서 `RS_1M_Rating`을 함께 읽어 `StageStock`·`StockBubbleItem`에 `rs_1m` 전달(REQ-RSR-012). 축약 DDL 테스트의 RED를 §G 규칙으로 정리.
- `sector_metrics.py` 집계에 `rs_med`, 봉투·랭킹 응답 연결(REQ-RSR-013·014).
- 종료 조건: AC-RSR-007·008·008b·009·010 PASS. 갱신 1회 후 라이브 `stock_meta.rs_1m`이 채워짐(AC-RSR-007 라이브 단계).

### M5 — 프론트 표시 (Priority Medium)

- 열기 배지 술어(`rs_1m >= RS_TOP_THRESHOLD`, null 처리)와 상수 유래 title(REQ-RSR-015·016).
- 섹터 순위 테이블 `rs_med` 열(REQ-RSR-017).
- 종료 조건: AC-RSR-011·012 PASS, dev 서버 재시작 후 화면 확인(프로젝트 지침).

### M6 — 회귀 실측 기록과 문서 (Priority Low)

- M2의 두 측정값과 초과수익 재측정을 before/after 표로 progress.md에 기록(REQ-RSR-020).
- `docs/rs-timeline-eli5.html` 갱신. CHANGELOG는 sync 단계(manager-docs) 소관.
- 종료 조건: AC-RSR-014의 기록이 progress.md에 있음.

## §G 테스트 전략

**변경 기호를 참조하는 기존 테스트 전체 목록.** 세는 명령:

```bash
grep -rlE "RS_12M_Rating|rs_12m|RS_1M_Rating|generate_rs_db" tests backend/tests frontend/src --include='*.py' --include='*.ts' --include='*.tsx' \
  | grep -E '(^|/)(test_[^/]*\.py|conftest\.py|[^/]*\.test\.tsx?)$' | sort
```

관측: 49개(Python 25, 프론트 24). `--include`로 `.py`/`.ts`/`.tsx`만 보므로 `__pycache__`·`.pyc`·JSON은 들어오지 않는다. 열의 뜻: "축약 DDL" = 파일이 `RS_1M_Rating` 없는 `relative_strength`를 만든다(`CREATE TABLE … relative_strength` 뒤 8줄 안에 `RS_1M_Rating` 없음); "고정 픽스처" = `frozen` 언급 수; "임계값 리터럴" = `>= 70`·`> 60`·`RS_STRONG`·`S2_STRONG`·`_STAGE2_`·`T8` 언급 수. 판정은 이 신호에서 기계적으로 정했으며, "M4 조건부" 행은 M4 착수 직후 전체 테스트 실행으로 실제 RED 여부를 확정한다.

| # | 파일 | 축약 DDL | 고정 픽스처 | 임계값 리터럴 | 판정 |
|---|---|---|---|---|---|
| 1 | `backend/tests/test_bubble_rs_missing_exclusion.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 2 | `backend/tests/test_minervini_template.py` | Y | - | 7 | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가; M3 — 70/60 값이 바뀌면 경계 기대 재검토 |
| 3 | `backend/tests/test_sector_advanced.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 4 | `backend/tests/test_sector_detail_service.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 5 | `backend/tests/test_stage_service.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 6 | `frontend/src/api/__tests__/stage.test.ts` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 7 | `frontend/src/components/ChartGrid/__tests__/ChartCellRsBadge.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 8 | `frontend/src/components/ChartGrid/__tests__/ChartGrid.integration.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 9 | `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 10 | `frontend/src/components/common/__tests__/er2-screens.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 11 | `frontend/src/components/SectorAnalysis/__tests__/SectorDetailPanel.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 12 | `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.ac048-guard.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 13 | `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.m5.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 14 | `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.sectorSwitch.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 15 | `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 16 | `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.zoom.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 17 | `frontend/src/components/StatusBar/__tests__/StatusBar.visibleCount.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 18 | `frontend/src/components/StockExplorer/__tests__/M7.perf-mobile.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 19 | `frontend/src/components/StockExplorer/__tests__/StockExplorer.m6.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 20 | `frontend/src/components/StockExplorer/__tests__/StockExplorer.scroll.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 21 | `frontend/src/components/StockExplorer/__tests__/StockExplorer.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 22 | `frontend/src/components/StockExplorer/__tests__/StockTable.m4.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 23 | `frontend/src/components/StockExplorer/__tests__/StockTable.test.tsx` | - | - | 2 | M3 — 70/60 값이 바뀌면 경계 기대 재검토 |
| 24 | `frontend/src/components/StockExplorer/__tests__/stockTableColumns.test.ts` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 25 | `frontend/src/components/StockList/__tests__/sectorKey.test.ts` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 26 | `frontend/src/components/StockList/__tests__/StockList.alltab.characterization.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 27 | `frontend/src/components/StockList/__tests__/StockList.grouping.test.tsx` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 28 | `frontend/src/types/__tests__/stage.test.ts` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 29 | `frontend/src/types/__tests__/stock_stage.test.ts` | - | - | - | 변경 없음 — 목 응답의 `rs_12m` 리터럴 사용, 새 필드는 선택 필드 |
| 30 | `tests/conftest.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 31 | `tests/test_ac_sag_024_high52.py` | - | 1 | - | 변경 없음 — 고정 픽스처 읽기 |
| 32 | `tests/test_ac_sag_030_rs_avg.py` | - | 1 | - | 변경 없음 — 고정 픽스처 읽기 |
| 33 | `tests/test_ac_sag_037_endpoint_date_consistency.py` | - | - | - | 변경 없음 — RS 값을 리터럴로 심은 자체 DB, 산식 비호출 |
| 34 | `tests/test_api.py` | - | - | - | 변경 없음 — RS 값을 리터럴로 심은 자체 DB, 산식 비호출 |
| 35 | `tests/test_chart_service.py` | - | - | - | 변경 없음 — RS 값을 리터럴로 심은 자체 DB, 산식 비호출 |
| 36 | `tests/test_consumer_dates.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 37 | `tests/test_db_service.py` | - | - | - | 변경 없음 — `generate_rs_db`를 `patch.object`로 대체(`:176`, `:200`), 단계 순서만 검증 |
| 38 | `tests/test_market_api.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 39 | `tests/test_market_breadth.py` | Y | - | 1 | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가; M3 — 70/60 값이 바뀌면 경계 기대 재검토 |
| 40 | `tests/test_meta_service.py` | - | - | - | M4 — `rs_1m` 복사·ALTER 기대 추가(기존 단언 불변) |
| 41 | `tests/test_sag_m6_router_wiring.py` | - | 1 | - | 변경 없음 — 고정 픽스처 읽기 |
| 42 | `tests/test_screen_codes_filter.py` | - | - | - | 변경 없음 — RS 값을 리터럴로 심은 자체 DB, 산식 비호출 |
| 43 | `tests/test_screen_service.py` | - | - | - | 변경 없음 — RS 값을 리터럴로 심은 자체 DB, 산식 비호출 |
| 44 | `tests/test_sector_aggregation.py` | - | 6 | - | M4 — 봉투 `data[]`에 `rs_med` 기대 추가(기존 단언 불변). RS 값은 고정 픽스처에서 읽음 |
| 45 | `tests/test_sector_detail.py` | - | - | - | 변경 없음 — RS 값을 리터럴로 심은 자체 DB, 산식 비호출 |
| 46 | `tests/test_sector_history_consistency.py` | Y | - | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 47 | `tests/test_sector_metrics.py` | Y | - | - | M4 — `rs_med` 기대 추가; M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |
| 48 | `tests/test_stage_classifier.py` | Y | - | 4 | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가; M3 — 70/60 값이 바뀌면 경계 기대 재검토 |
| 49 | `tests/test_universe.py` | Y | 7 | - | M4 조건부 — 축약 `relative_strength` DDL에 `RS_1M_Rating` 없음. 테스트가 주간 RS 질의(`stage_classifier.py:183-193`, `sector_advanced.py:240-249`)를 타면 `no such column` RED → DDL에 컬럼 추가 |

변경 없이 통과해야 하는 테스트(위 목록 밖 포함): `tests/test_weekly_insert.py`(10건, 스키마 불변), `tests/test_db_service.py`(18건, 파이프라인 순서 불변), `tests/test_ac_sag_030_rs_avg.py`(4건, `rs_avg` 의미 불변), `composite_score`를 다루는 7개 파일(D1, research.md R8).

**AC별 신규 테스트**: acceptance.md 각 AC에 명시. 테스트 DB는 `tmp_path`에 새로 만들고, 라이브 `Output/` DB는 테스트에서 쓰지 않는다.

**회귀 계측 호출** (프로젝트 venv, 코드 cwd 기준):

```bash
/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db Output/snapshots/weekly_before_rsr.db   # M2 기준선(재생성 전)
/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db Output/snapshots/weekly_after_rsr.db    # M2 목표 ≥ 60
/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stage2_ratio_eval.py --db Output/snapshots/weekly_before_rsr.db --weeks 12 --mode conditional --threshold 70   # M3 (a) 기준선 (60, 80도 각각 실행해 판별력 사전 조건 판정)
/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stage2_ratio_eval.py --db Output/snapshots/weekly_before_rsr.db --weeks 12 --mode strong --threshold 60        # M3 (b) 기준선
```

venv 위치는 `/Users/byunjungwon/Dev/my_chart/.venv`이고 코드 cwd는 `/Users/byunjungwon/Dev/my-project-01/my_chart`이다(프로젝트 메모리 `project_server_runtime_env`).

## §H 참조

- 계획서: `docs/rs-rebalance-plan-brief.md`, 쉬운 설명판 `docs/rs-timeline-eli5.html`
- 계측 원문: `scripts/rs_eval/rs_final_h4.out`, `codex_round1.md`, `codex_round2.md`
- 관례: `SPEC-SECTOR-DISPLAY-UNIFY-001` REQ-SDU-003(상수 유래 title)·REQ-SDU-005(`rating` 셀 유형), `SPEC-SECTOR-METRIC-UNIFY-001`(봉투 `data[]`)
- 작업 트리 주의: `SPEC-AI-REPORT-004`의 미커밋 변경(`backend/main.py`, `backend/routers/ai_report.py`, 테스트 3개, 미추적 `backend/services/goose_job_service.py`)은 이 SPEC과 무관하다. 스테이징은 명시 경로로만 한다.
