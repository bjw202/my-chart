---
id: SPEC-RS-REBALANCE-001
title: "RS 타임라인 재조정 — 종목 RS 12개월 중심 재가중·열기 배지 분리·섹터 RS 중앙값 병기"
version: "0.3.0"
status: draft
created: 2026-10-20
updated: 2026-10-20
author: manager-spec
priority: P1
phase: "v0.6.0 target"
module: "my_chart/db/weekly.py"
lifecycle: spec-anchored
tags: "rs, relative-strength, weekly, stock-meta, sector, frontend, threshold"
tier: L
depends_on: [SPEC-SECTOR-METRIC-UNIFY-001, SPEC-SECTOR-DISPLAY-UNIFY-001]
---

# SPEC-RS-REBALANCE-001 — RS 타임라인 재조정

> 승인된 원본 계획서: `docs/rs-rebalance-plan-brief.md` (2판, 2026-10-20). 본 SPEC은 그 계획서의 전사이며 재기획이 아니다. 계획서 §7의 미결 질문 Q1~Q4는 이번 plan 세션에서 사용자가 답했고, 그 답을 §2.2에 결정으로 고정한다.
> 코드베이스 주장마다 관측 명령은 `research.md`(R1~R12)에 있다. 이 문서의 수치 중 이 세션에서 직접 측정하지 않은 것은 "(계획서 §2, 2026-10-20 실측)"으로 출처를 단다.

## HISTORY

| 버전 | 날짜 | 변경 |
|---|---|---|
| 0.3.0 | 2026-10-20 | plan-audit iter-2 defects N1–N5 반영. N1: 70 재보정 기준을 진입 비율에서 "RS 외 진입 조건 통과 종목 중 RS 조건 통과 비중"(조건부 RS 통과율)으로 교체하고 상대 허용오차 ±10%와 판별력 사전 조건(60/70/80 단조·폭 > 허용오차, 미충족 시 70은 기록만)을 추가 — plan 단계 실측은 사전 조건 미충족을 예고. N2: REQ-RSR-001의 짝 없는 행 조항을 (i)·(ii)에 포함되는 중복으로 판정해 삭제. N3: 측정 분모를 가격 테이블 기준으로 고정. N4: REQ-RSR-023 shall 절에 전 컬럼 NULL 규칙 명시 |
| 0.2.0 | 2026-10-20 | plan-audit iter-1 defects D1–D14 반영. D1: REQ-RSR-001을 "이번 실행이 쓰지 않은 행은 모두 삭제"(선행 단계 + 날짜별 집합 차 삭제)로 재작성, AC-RSR-017 신설. D2: Stage 2 측정을 진입 비율(70)과 Strong 비중(60) 두 기준으로 분리하고 주차 집합·측정 명령·DB 사본 경로 고정. D4: 결측 수익률 행 규칙 REQ-RSR-023·AC-RSR-018 신설. D13: 70/60 소유권 유지와 T8 공유 상수 결정. 나머지 SHOULD-FIX·MINOR 정정 |
| 0.1.0 | 2026-10-20 | 계획서 2판 전사. Q1~Q4 결정 반영. 계획서 §4 "제외"의 "고아 행 정리(별도 카드)"는 D7 2판과 모순되는 초안 잔재로 판단해 삭제하고 범위에 포함. 조사에서 발견한 계획서 정정 3건(R2 고아 행 합계, R3 우선주 패턴 오탐, R6 `stock_meta` 비재생성)을 반영. 조사에서 새로 드러난 결정 3건(B-1 판별 규칙, B-2 `rs_1m` 소비처, B-3 재보정 범위)을 같은 날 사용자 결정으로 §2.4에 고정 |

`depends_on` 근거: `SPEC-SECTOR-METRIC-UNIFY-001`은 섹터 집계 봉투(`data[]`)와 `_RS_TOP_THRESHOLD` 비공개 상수 관례의 원천이고, `SPEC-SECTOR-DISPLAY-UNIFY-001`은 `frontend/src/utils/rsMetrics.ts` 거울 상수와 상수 유래 title 관례(REQ-SDU-003), `SectorRankingTable.tsx`의 `rating` 셀 유형(REQ-SDU-005)을 소유한다. 본 SPEC은 두 파일을 모두 수정한다(research.md R4, R7). 두 SPEC 모두 `status: completed`(R11).

---

## §1 배경 (Context)

### §1.1 한 줄 목표

종목 RS 등급의 과거 창을 "최근 1개월 과비중"에서 "12개월 중심"으로 옮기고, 1개월 신호는 별도 배지로 분리한다. 주도 섹터 탐지는 그대로 두면서 종목 명단의 안정성을 높이는 것이 목적이다.

### §1.2 근거 — 실측 요약 (계획서 §2, 2026-10-20 실측)

주봉 DB `Output/stock_data_weekly.db`(2020-01~2026-10), 20주 평균 주간거래대금 50억 원 이상 유니버스, 4주 보유 기준.

| 사실 | 수치 |
|---|---|
| 현행 `RS_12M_Rating` 상위 10%의 4주 뒤 잔존율 | 31% |
| 1개월 항만 제거 | 57% |
| IBD식(최근 분기 40%, 이전 세 분기 각 20%) | 65% |
| 12개월 단독 | 75% |
| 상위 10% 종목의 향후 4주 수익 − 유니버스 평균 | 모든 창에서 0 이하 (12M −0.08pp, 현행 −0.60pp) |
| 섹터 등가중 지수, 과거 1개월 창 상위 5 섹터 | IC 0.07, 승률 63%, 4주 뒤 잔존 23% |
| 섹터 3~6개월 창 | IC ≈ 0 |
| 핫 섹터(1개월 상위 5) 안 현행 RS 80+ 종목 − 섹터 평균 | 4주 −0.20pp(승률 46%), 8주 −0.47pp |
| 핫 섹터 종목 중 RS 80+ 비율: 현행 / 12M | 36% / 25% |

잔존율 네 수치는 이 세션에서 `scripts/rs_eval/rs_final_h4.out`의 `상위10_지속률` 열(30.88 / 57.46 / 65.28 / 74.78)로 다시 확인했다(research.md R9). 나머지 행은 계획서 수치를 옮긴 것이다.

**해석.** 종목 RS는 "오를 종목을 맞히는 식"이 아니라 "강한 종목을 흔들리지 않게 분류하는 필터"이며, 그 용도에서는 긴 창이 낫다. 섹터 탐지는 섹터 종합 점수(1w/1m/3m)가 이미 짧은 창으로 수행한다. 1개월 항을 종목 RS에 섞으면 탐지가 중복되고 명단만 흔들린다.

**검증 방법의 알려진 한계 (계획서 §8).** 2022~2026 단일 구간이고, 4주 수익률이 겹쳐 독립 표본이 아니며, 섹터 분류는 현재 등록부를 소급 적용했고, 상장폐지 종목은 forward 결측으로 탈락한다. 또한 계측 스크립트는 산식을 원시 컬럼에서 스스로 다시 계산하므로 프로덕션 테이블을 읽지 않는다(research.md R9). 본 SPEC은 이 마지막 한계를 프로덕션 경로 계측(REQ-RSR-020)으로 메운다.

### §1.3 조사로 확인·정정한 계획서 주장

| 계획서 주장 | 관측 | 처분 |
|---|---|---|
| 고아 행 "주중 날짜 42개 10만 4천 행, 옛 종목명 21개" | 42개 날짜 104,411행 + 21개 이름 5,507행에 더해 쌍 불일치 9,963행, 합계 119,881행 (R2). 그 밖에 `stock_prices` 짝이 **있어서** 쌍 기준 삭제로 지워지지 않고 `INSERT OR REPLACE`로도 덮이지 않는 낡은 행이 있다: 지수 600행(KOSPI 300, KOSDAQ 300), 거래량 0 행 16,369행(최신 주차 101행), 기준 종목 날짜가 아닌 날짜의 행 5행(4개 날짜) (R2.1) | 쌍 기준 삭제만으로는 부족하다. REQ-RSR-001을 "이번 실행이 쓰지 않은 행은 모두 지운다"(선행 단계 + 날짜별 집합 차 삭제)로 정한다 |
| 우선주·스팩은 이름 패턴(`…우`, `…우B`, `…스팩`)으로 판별 | 등록부에 우선주·스팩 0개. `…우` 패턴은 보통주 3개(성우, 에코글로우, 이오플로우)만 잡는다 (R3) | 코드 끝자리 규칙으로 고정(§2.4 B-1)하고 오탐 금지를 요구사항으로 고정 |
| `stock_meta`는 재구축 테이블이라 DDL만 바꾸면 됨 | `DELETE` 후 재삽입, `DROP` 없음. 위치 기반 27열 삽입. 라이브 테이블 컬럼명이 DDL과 다름 (R6) | 멱등 ALTER + 끝 덧붙임을 요구사항으로 고정 |
| 주간 소비처 목록 | `my_chart/analysis/sector_advanced.py:240` `_get_rs_on_date()` 누락 (R4) | 파일 목록에 추가 |
| 종목 테이블·버블에 열기 배지, 공급원은 `stock_meta.rs_1m` | 두 화면 모두 주간 `relative_strength`를 읽고 `stock_meta`를 읽지 않는다 (R7) | 두 화면은 주간 `RS_1M_Rating`을 공급원으로 하고, `stock_meta.rs_1m`은 채우기와 API 노출까지만 한다(§2.4 B-2) |

---

## §2 확정 결정

### §2.1 계획서 결정 D1~D7

| # | 결정 |
|---|---|
| D1 | 섹터 종합 점수 `_COMPOSITE_WEIGHTS = {"1w": 0.30, "1m": 0.40, "3m": 0.30}`(`my_chart/analysis/sector_metrics.py:181`)는 변경하지 않는다 |
| D2 | `RS_12M_Rating` 산식에서 1개월 항을 제거하고 12개월 중심으로 재가중한다. 산식은 Q1 결정(IBD식)으로 고정한다 |
| D3 | `RS_1M_Rating`은 삭제하지 않고 "열기(heat)" 배지로 종목 화면에 분리 표시한다 |
| D4 | 섹터 화면의 "RS 평균"(`sector_rs_avg`) 옆에 중앙값과 breadth(`sector_rs_top_pct`, 이미 존재)를 병기한다. 평균 열의 처리는 Q2 결정(병기)으로 고정한다 |
| D5 | 순위 분모에서 지수 행(`KOSPI`, `KOSDAQ`), 거래량 0 행, 우선주, 스팩을 제외한다. 이 SPEC에 포함한다 |
| D6 | 임계값 60/70/80은 새 분포에서 재보정한 뒤 결정한다. 숫자를 미리 정하지 않는다 |
| D7 | `relative_strength` 고아 행 정리는 재생성 직전 선행 단계로 이 SPEC에 포함한다(M1). `INSERT OR REPLACE`(`weekly.py:188`)는 `stock_prices`에 없는 날짜의 옛 공식 행을 지우지 못하므로, 정리 없이 재생성하면 두 공식의 값이 한 테이블에 섞인다 |

**계획서 내부 모순의 해소.** 계획서 §4 "제외" 목록에는 "고아 행 정리 (D7, 별도 카드)"가 남아 있으나, 같은 문서 §3 D7(2판)과 §4 "포함"은 이를 범위에 넣는다. 2판에서 D7을 번복했다고 명시한 만큼 "제외" 항목은 1판의 잔재로 판단한다. **고아 행 정리는 범위에 포함하며(M1 선행 단계), §6 범위 밖 목록에서 뺀다.**

### §2.2 미결 질문 Q1~Q4의 결정 (이번 plan 세션, 사용자 답)

| # | 결정 | 내용 |
|---|---|---|
| Q1 | IBD식 | `RS_12M_Rating` = IBD식 종합 점수의 백분위 순위 × 100. 분기 수익률은 기존 원시 컬럼 `RS_3M`, `RS_6M`, `RS_9M`, `RS_12M`에서 **비율 기반**으로 유도한다(§2.3). 기각한 대안: 12개월 단독(잔존율 75% 대 IBD식 65%, 계획서 §2) — 최근 분기를 전혀 보지 않아 추세 전환을 늦게 반영한다는 이유로 기각 |
| Q2 | 병기 | `sector_rs_avg`는 그대로 두고, 그 옆에 중앙값 `rs_med`를 추가하며, 이미 있는 `sector_rs_top_pct`(breadth)를 섹터 테이블에 나란히 둔다. 삭제·이름 변경 없음 |
| Q3 | 화면 필터로만 유지 | 20주 평균 주간거래대금 50억 원 이상 규칙은 RS 순위 분모에 적용하지 않는다. 분모 필터는 정확히 D5다. 50억 유니버스는 M2·M6 회귀 계측 스크립트 안에서만 재현한다 |
| Q4 | `RS_1M_Rating >= 80`, 가속 배지 제외 | 열기 배지는 `RS_1M_Rating >= 80`일 때 켠다. 기존 상수 쌍(`_RS_TOP_THRESHOLD = 80.0`, `sector_metrics.py:58` / `RS_TOP_THRESHOLD = 80`, `rsMetrics.ts:10`)을 재사용한다. "가속"(긴 창 RS 4주 상승폭) 배지는 미실측이므로 이 SPEC에 넣지 않고 후속 과제로 남긴다 |

### §2.3 IBD식 유도식 (Q1 고정)

원시 컬럼 `RS_kM`은 k개월 누적 자기 수익률이며 소수 비율이다(예: `0.12` = 12%, research.md R3). 분기 수익률을 다음과 같이 정의한다.

- `q1 = RS_3M` (최근 분기)
- `q2 = (1 + RS_6M) / (1 + RS_3M) − 1`
- `q3 = (1 + RS_9M) / (1 + RS_6M) − 1`
- `q4 = (1 + RS_12M) / (1 + RS_9M) − 1`
- 종합 점수 `S = 0.4·q1 + 0.2·q2 + 0.2·q3 + 0.2·q4`
- `RS_12M_Rating = percentile_rank(S) × 100` (현행과 같은 순위 함수: 같은 날짜, 같은 분모)

**비율 기반을 택하는 이유.** 누적 수익률은 곱으로 이어진다: `1 + RS_6M = (1 + q1)(1 + q2)`. 따라서 `q2`의 정확한 값은 비율식이다. 차분식 `RS_6M − RS_3M`은 수익률이 작을 때만 근사로 맞고, 큰 수익률에서는 크게 어긋난다(예: `RS_3M = 1.0`, `RS_6M = 1.2`이면 비율식 `q2 = 0.10`, 차분식 `0.20`). 게다가 차분식을 가중합하면 `0.2·RS_3M + 0.2·RS_12M`으로 줄어들어 중간 분기 정보가 사라진다. 계획서 §2의 IBD식 65%는 비율식으로 측정한 값이다(`scripts/rs_eval/stock_rs_eval.py:36-38`, research.md R9). 관측 데이터에서 `1 + RS_kM`의 최솟값은 양수다(`RS_kM` 최솟값 −0.99887…, `RS_kM <= -1` 행 0개, R3).

`0.4 : 0.2 : 0.2 : 0.2`와 스크립트의 `2 : 1 : 1 : 1`은 양의 상수배라 순위가 같다.

### §2.4 조사에서 드러난 결정 B-1~B-3 (2026-10-20, 사용자 결정)

| # | 결정 | 내용과 근거 |
|---|---|---|
| B-1 | 코드 끝자리 + 이름 `스팩` | D5의 우선주는 등록부 종목 코드(6자리)의 끝자리가 `0`이 아닌 종목, 스팩은 종목명에 `스팩`이 들어 있는 종목으로 판별한다. 실측(research.md R3): 등록부(`get_stock_registry()`) 2,559행의 코드 끝자리는 모두 `0`이고 이름에 `스팩`·`SPAC`이 든 종목은 0개다. 따라서 이 규칙의 **현재 즉시 효과는 없으며**, 등록부에 우선주·스팩이 들어올 때를 대비한 사전 가드다. 기각한 대안: 이름 패턴(`우$`·`우B$`·`우C$`) — 보통주 3개(성우, 에코글로우, 이오플로우)를 오탐하고 허용 목록을 손으로 관리해야 함. 규칙 생략 + 등록부 가드 테스트 — D5 문구를 코드로 이행하지 않음 |
| B-2 | API 노출까지만 | `stock_meta.rs_1m`은 Phase 4에서 채우고 API로 노출할 수 있게 두는 데까지만 한다. 일봉 화면(`ChartGrid/ChartCell.tsx` 등) 배지 연결은 후속 과제로 미룬다(§6). 종목 테이블과 종목 버블의 열기 배지는 **주간 `relative_strength.RS_1M_Rating`**에서 공급한다 — 경로는 `my_chart/analysis/stage_classifier.py:183-193`의 주간 조인 질의(→ `/stage/overview`)와 `my_chart/analysis/sector_advanced.py:240-249` `_get_rs_on_date()`(→ `/sectors/{name}/bubble`)다(research.md R7) |
| B-3 | 재보정 범위를 Stage 2 상수로 한정 | M3 재보정 대상은 `_STAGE2_ENTRY_RS_MIN`(70)·`_STAGE2_RS_STRONG`(60)과 그 프론트 거울 `RS_STRONG_THRESHOLD`·`RS_S2_STRONG_THRESHOLD`, 그리고 같은 값을 반복한 리터럴뿐이다. `_RS_TOP_THRESHOLD`/`RS_TOP_THRESHOLD`는 80으로 유지하고 열기 배지 술어는 `RS_1M_Rating >= 80`으로 유지한다. 근거: 두 등급은 같은 날짜 분모 안의 백분위 순위라 산식과 무관하게 80 이상인 몫이 약 20%다. 라이브 DB 실측 — plan-audit iter-1 프로브: `AVG(RS_12M_Rating>=80)` 20.08%, `AVG(RS_1M_Rating>=80)` 20.04%; 이 세션 재측정(전 행): 20.02% / 20.01% (research.md R13). D6의 "60/70/80 재보정" 중 80은 이 근거로 재보정 대상에서 뺀다 |
| D13 | 70/60 소유권 유지, T8은 공유 상수 | `RS_STRONG_THRESHOLD`·`RS_S2_STRONG_THRESHOLD`는 `SPEC-SECTOR-DISPLAY-UNIFY-001` REQ-SDU-003에서 프론트 소유 상수로 기록되어 있다(`rsMetrics.test.ts:50-54`). 이 SPEC은 소유권을 옮기지 않고 **값만** 양쪽에서 함께 바꾸며, 백엔드 값과의 동일성은 교차 언어 등식 테스트가 지킨다. Minervini T8(`backend/services/screen_service.py:61`, `stock_meta.rs_12m >= 70`)은 재보정된 Stage 2 진입 값을 **공유 상수 `_STAGE2_ENTRY_RS_MIN`으로 채택**한다(정의 지점 단일화). 기각한 대안: T8 리터럴 70을 독립 유지 — 같은 의미의 임계값이 두 값으로 갈라질 수 있음 |

---

## §3 요구사항 (GEARS)

### §3.1 주간 RS 재생성 — `generate_rs_db()`

- **REQ-RSR-001** (이번 실행이 쓰지 않은 행 삭제, D7) — **When** `generate_rs_db()`가 실행되면, the RS 생성기 shall 실행이 끝났을 때 `relative_strength`에 이번 실행이 기록한 `(Name, Date)` 행만 남도록, (i) 처리 날짜 집합(루프가 도는 기준 종목 날짜)에 속하지 않는 `Date`의 행을 루프 전에 삭제하고, (ii) 날짜 `d`마다 필터 후 이름 집합을 정한 뒤 같은 트랜잭션 안에서 `Date = d`이면서 그 집합에 없는 이름의 행을 삭제하고 새 행을 기록한다. 필터 후 행이 0개인 날짜는 그 날짜의 행을 모두 삭제한다. **`stock_prices` 짝이 없는 행은 이 두 단계에 이미 포함된다**: 그런 행은 날짜가 처리 날짜 집합 밖이면 (i)로, 안이면 그 날짜의 `stock_prices`에 이름이 없어 필터 후 집합에도 없으므로 (ii)로 지워진다. 따라서 별도의 "짝 없는 행 삭제" 조항은 두지 않는다. 기각한 대안: 실행 앞단의 테이블 전체 삭제 — `weekly.py` 머리말(`:7`)이 "INSERT OR REPLACE (UPSERT) instead of DROP TABLE"을 의도된 설계로 기록하고 있고, 전체 삭제는 실행이 중간에 멈추면 테이블을 빈 상태로 남긴다.
- **REQ-RSR-002** (지수·거래량 0 분모 제외, D5) — The RS 생성기 shall 각 날짜의 순위 분모에서 `Name`이 `KOSPI` 또는 `KOSDAQ`인 행과 그 날짜의 `Volume`이 0인 행을 제외한 뒤 백분위 순위를 계산한다. 제외는 순위 계산 **이전**에 적용되어 남은 종목의 등급 값에 반영되어야 한다.
- **REQ-RSR-003** (우선주·스팩 분모 제외, D5·B-1) — The RS 생성기 shall 등록부 종목 코드의 끝자리가 `0`이 아닌 종목(우선주)과 종목명에 `스팩`이 들어 있는 종목(스팩)을 순위 분모에서 제외한다. 이 규칙은 실측된 보통주 `성우`, `에코글로우`, `이오플로우`를 제외해서는 안 된다(research.md R3). 등록부에 코드가 없는 이름은 우선주로 판정하지 않는다.
- **REQ-RSR-004** (제외 행 미기록) — The RS 생성기 shall REQ-RSR-002·003·007·023으로 분모에서 제외된 `(Name, Date)`에 대해 `relative_strength` 행을 기록하지 않으며, 이전 실행이 남긴 같은 쌍의 행은 REQ-RSR-001 (ii)로 지운다.
- **REQ-RSR-005** (IBD식 산식, D2·Q1) — The RS 생성기 shall `RS_12M_Rating`을 §2.3의 비율 기반 IBD식 종합 점수의 백분위 순위 × 100으로 계산한다.
- **REQ-RSR-006** (나머지 등급 산식 불변) — The RS 생성기 shall `RS_6M_Rating`, `RS_3M_Rating`, `RS_1M_Rating`을 현행 산식(`weekly.py:450-455`) 그대로, REQ-RSR-002·003의 필터를 거친 같은 분모 위에서 계산한다.
- **REQ-RSR-007** (분모 무효 행) — **When** 어떤 행의 `1 + RS_3M`, `1 + RS_6M`, `1 + RS_9M` 중 하나가 0 이하로 검출되면, the RS 생성기 shall 그 행을 해당 날짜의 분모에서 제외하고 무한대·NaN 등급을 기록하지 않는다. (관측 데이터에서 해당 행은 0개다, research.md R3.)
- **REQ-RSR-008** (유동성 필터 비적용, Q3) — The RS 생성기 shall not 거래대금(50억 원 기준 포함)을 근거로 순위 분모에서 행을 제외한다.
- **REQ-RSR-009** (스키마 불변) — The `relative_strength` 테이블 shall 컬럼 이름·순서·기본 키(`Name`, `Date`, `RS_12M_Rating`, `RS_6M_Rating`, `RS_3M_Rating`, `RS_1M_Rating`, PK `(Name, Date)`)를 유지한다.
- **REQ-RSR-023** (결측 행, 현행 유지) — The RS 생성기 shall 날짜 `d`의 `stock_prices` 행(`SELECT *`로 읽은 전 컬럼) 중 **어느 컬럼이든 NULL이 하나라도 있는 행**에 등급을 매기지 않는다(현행 `df.dropna()`, `weekly.py:430`). 이 SPEC은 이 범위를 `RS_1M`~`RS_12M` 다섯 컬럼으로 좁히지도, 넓히지도 않는다. 최신 주차(2026-10-16) 실측: 가격 행 2,535개 중 RS 행은 2,490개이며, 빠진 45행은 `RS_*` 결측 44행과 `RS_*`는 있으나 `SMA40_Trend_4M`이 NULL인 1행(`명인제약`)이다(research.md R3.1). 따라서 상장 12개월 미만 종목은 `rs_1m`도 없고 열기 배지를 표시할 수 없다.

### §3.2 메타 재구축 — `rebuild_stock_meta()`

- **REQ-RSR-010** (`rs_1m` 복사) — **When** `rebuild_stock_meta()`가 실행되면, the 메타 재구축기 shall `rs_12m`과 같은 최신 주차(`latest_weekly_date`)의 `RS_1M_Rating`을 종목명 기준으로 `stock_meta.rs_1m`에 기록하고, 해당 종목의 RS 행이 없으면 NULL을 기록한다.
- **REQ-RSR-011** (레거시 테이블 보강) — **While** 기존 `stock_meta` 테이블에 `rs_1m` 컬럼이 없는 상태에서 **when** `rebuild_stock_meta()`가 실행되면, the 메타 재구축기 shall 멱등 `ALTER TABLE … ADD COLUMN`으로 그 컬럼을 테이블 끝에 추가한다. 새 DB용 DDL(`_STOCK_META_DDL`)에서도 `rs_1m`은 **마지막 컬럼**이며, 행 값은 위치 삽입 튜플의 끝(28번째)에 둔다. 기존 27개 컬럼의 값은 위치가 바뀌어서는 안 된다(research.md R6).

### §3.3 API 스키마

- **REQ-RSR-012** (종목 `rs_1m` 노출, D3·B-2) — The 종목 단위 응답(`/stage/overview`의 종목 항목, `/sectors/{name}/bubble`의 종목 항목) shall 기존 `rs_12m` 옆에 nullable 필드 `rs_1m`을 싣고, 그 값은 주간 `relative_strength.RS_1M_Rating`(같은 주차)에서 `stage_classifier.py` 주간 조인 질의와 `sector_advanced.py` `_get_rs_on_date()` 경로로 읽는다. 이 두 응답은 `stock_meta.rs_1m`을 읽지 않는다.
- **REQ-RSR-013** (섹터 `rs_med`, D4·Q2) — The 섹터 집계 응답(봉투 `data[]` 항목과 `/sectors/ranking` 항목) shall 기존 `rs_avg`, `rs_top_pct` 옆에 `rs_med`(구성 종목 `RS_12M_Rating`의 중앙값, 결측 종목 제외)를 싣는다. 구성 종목 중 유효 RS가 하나도 없으면 결측으로 표시한다.
- **REQ-RSR-014** (하위 호환) — The API shall 기존 필드의 이름·타입·의미를 바꾸지 않는다. `rs_avg`는 계속 평균, `rs_top_pct`는 계속 `_RS_TOP_THRESHOLD` 이상 비율이다.

### §3.4 프론트 표시

- **REQ-RSR-015** (열기 배지, D3·Q4) — **Where** 종목의 `rs_1m`이 `RS_TOP_THRESHOLD` 이상이면, the 종목 테이블 행(`StockExplorer/StockTable.tsx`)과 종목 버블 툴팁(`SectorAnalysis/StockBubbleChart.tsx`) shall 열기 배지를 표시한다. `rs_1m`이 null이거나 임계값 미만이면 표시하지 않는다.
- **REQ-RSR-016** (상수 유래 title, REQ-SDU-003 관행) — The 열기 배지 shall 임계값을 `RS_TOP_THRESHOLD` 상수에서 끌어온 title 텍스트를 함께 단다.
- **REQ-RSR-017** (중앙값·breadth 병기, D4·Q2) — The 섹터 순위 테이블(`SectorRankingTable.tsx`) shall `RS Avg` 열 옆에 `rs_med` 열을 표시하고, 기존 `RS 80+ 비중` 열(breadth)을 그 둘과 인접하게 유지한다.

### §3.5 임계값 재보정 절차 (D6)

- **REQ-RSR-018** (재보정 절차와 기록, D6·B-3) — **When** M2 재생성이 끝나면, the 재보정 절차 shall 측정 주차 집합 W = "변경 전·후 두 DB 사본에 모두 존재하는 기준 종목(`삼성전자`) 날짜 중 최근 12개"에서 두 기준을 각각 측정해 `progress.md`에 기록한다. 측정 명령은 `scripts/rs_eval/stage2_ratio_eval.py`(M3 신설)이고 DB 사본은 `Output/snapshots/weekly_before_rsr.db`, `Output/snapshots/weekly_after_rsr.db`다. 두 기준의 분모는 모두 가격 테이블(`stock_prices`)에서 정해지므로 두 사본에서 같은 종목 집합이다. 숫자는 측정 전에 정하지 않는다.
  - **(a) 진입 기준 `_STAGE2_ENTRY_RS_MIN`(현행 70) — 조건부 RS 통과율.** 날짜 `d`에서 `screen_stage2_entry()`(`stage_classifier.py:237-310`)의 RS 외 조건 다섯 개 — 조건 1 Stage 2 분류(`classify_stage(stock).stage == 2`, `:265-267`), 조건 2 `Close > SMA10`(`:278-280`), 조건 3 `SMA10 > SMA40`(`:282-284`), 조건 4 `Volume / max(VolumeSMA10, 1) >= _STAGE2_ENTRY_VOLUME_RATIO`(`:286-288`), 조건 6 `CHG_1M > 0`(`:294-296`) — 을 모두 통과한 종목 집합(지수 행은 `_load_stocks_for_classification()`이 이미 제외, `:199-200`; 거래량 0 행은 조건 4에서 탈락)을 분모로, 그중 `RS_12M_Rating >= _STAGE2_ENTRY_RS_MIN`(조건 5, `:290-292`)도 통과하는 비중을 구하고 W 평균을 낸다. 허용오차는 **상대 ±10%**다: `|변경 후 사본·채택 상수 값 − 변경 전 사본·현행 상수 값| <= 0.10 × 변경 전 사본·현행 상수 값`. 상대 허용오차를 쓰는 이유는 이 비중이 100% 근처에 몰릴 수 있어 절대 %p 폭이 값의 크기에 따라 다른 엄격도를 갖기 때문이며, 10%는 기준 (b)의 ±5%p가 기준선 33.53%에서 갖는 상대 폭(약 15%)보다 엄격하게 잡은 값이다. **판별력 사전 조건**: M3는 먼저 변경 전 사본에서 임계값 60·70·80의 조건부 RS 통과율을 측정해 기록하고, 세 값이 엄격한 단조 감소이면서 `(60 값 − 80 값) > 0.10 × 70 값`일 때만 (a)를 재보정 기준으로 쓴다. 사전 조건이 성립하지 않으면 (a)는 판별력이 없는 것으로 보고 **70의 재보정은 "기록만"으로 격하**한다 — 70을 유지하고 세 값과 변경 후 사본의 70 값을 기록한다. plan 단계 실측(현재 라이브 DB 사본, research.md R15)은 60 → 100.00%, 70 → 99.48%, 80 → 97.85%로 폭 2.15%p가 0.10 × 99.48 = 9.95%p보다 작아 사전 조건 미충족을 예고한다.
  - **(b) 강세 기준 `_STAGE2_RS_STRONG`(현행 60) — Stage 2 강세 비중.** 날짜 `d`에서 `classify_all(db, d)`(`:218`) 결과 중 `stage == 2`인 종목(분모 — Stage 판정은 RS를 쓰지 않으므로 가격 테이블로 결정됨, RS는 `:105`의 세부 라벨에만 쓰임)에서 `detail == "Stage 2 Strong"`인 비중의 W 평균. 허용오차는 기준선 대비 ±5%p다(plan-audit iter-2 실측 기준선 33.53%).
  - 각 기준에 대해 (1) 변경 전 사본·현행 상수, (2) 변경 후 사본·현행 상수, (3) 변경 후 사본·채택 상수를 측정하고, (3)이 (1)의 허용오차 안에 드는 상수를 채택한다.
- **REQ-RSR-019** (단일 정의 지점) — The 재보정으로 바뀌는 각 임계값 shall 정의 지점 한 곳에서만 값이 바뀌어야 하며, 같은 임계값을 상수 없이 숫자로 반복한 리터럴(`backend/services/screen_service.py:61`의 `rs_12m >= 70`, `frontend/src/components/StockExplorer/StockTable.tsx:39`의 `c.rs_12m >= 70`)은 상수 참조로 바뀌어야 하고, 프론트 거울 상수는 교차 언어 등식 테스트로 백엔드 값과 같음이 보장되어야 한다. T8(`screen_service.py:61`)은 `_STAGE2_ENTRY_RS_MIN`을 참조한다(§2.4 D13).

### §3.6 불변과 회귀 실측

- **REQ-RSR-020** (프로덕션 경로 회귀 실측) — **When** 재생성이 끝나면, the 회귀 계측 shall `scripts/rs_eval/stock_rs_eval.py`의 프로덕션 모드(`--production --db <경로>`)로 `relative_strength.RS_12M_Rating`만을 점수 입력으로 읽어(원시 수익률로 산식을 재계산하지 않고) 스크립트의 기존 유니버스 규칙 — ISO 주차 마지막 날짜(`:19-21`), `dates[52:-H]`(`:71`), 날짜당 200종목 이상(`:74`), 점수 ≥ 90을 상위 10%로(`:76`), `tv20 >= 5e9`(`:99`) — 을 그대로 적용해 4주 잔존율을 측정하고, 같은 명령으로 변경 전 DB 사본에서 측정한 기준선과 함께 `progress.md`에 기록한다.
- **REQ-RSR-021** (섹터 종합 점수 불변, D1) — The 섹터 종합 점수 shall `_COMPOSITE_WEIGHTS = {"1w": 0.30, "1m": 0.40, "3m": 0.30}`로 계속 계산된다.
- **REQ-RSR-022** (상위 임계값 유지, B-3·Q4) — The `_RS_TOP_THRESHOLD`(`sector_metrics.py:58`)와 `RS_TOP_THRESHOLD`(`rsMetrics.ts:10`) shall 80으로 유지되며, 열기 배지 술어는 이 상수를 그대로 쓴다.

---

## §4 비기능 요구사항

- **재생성 비용.** `generate_rs_db()`는 실행마다 기준 종목의 전 날짜(현재 355개, research.md R2)를 다시 계산한다. 본 변경은 루프 모양을 바꾸지 않고 실행 앞단의 삭제 한 번과 날짜별 행 필터·집합 차 삭제만 더하므로, 갱신 시간은 같은 차수에 머문다. 갱신 1회로 과거 전 주차가 새 산식으로 바뀐다.
- **스키마 변경 범위.** 테이블 스키마 변경은 `stock_meta.rs_1m` 컬럼 1개 추가뿐이다. `relative_strength`는 이름·의미가 같은 네 등급 컬럼을 유지하며 값만 바뀐다.
- **DB 갱신 파이프라인.** `POST /db/update` → `_run_update()`의 4단계 순서와 단계 이름은 바뀌지 않는다(research.md R5). Phase 1(원시 수익률 수집)과 Phase 3(일봉, `RS_Line`)은 변경하지 않는다.

---

## §5 의미 변화 고지

`RS_12M_Rating`과 `stock_meta.rs_12m`은 이름은 그대로지만 값의 의미가 바뀐다(1개월 과비중 → 12개월 중심). 이 값을 임계값과 비교하는 모든 소비처는 REQ-RSR-018의 재보정 대상이다(research.md R4 표). 차트(`charting/single.py:142`, `bulk.py:329,353`)는 값만 달라지고 코드는 바뀌지 않는다.

---

## §6 범위 밖 (Exclusions)

### Out of Scope — 섹터 종합 점수와 RRG

- `_COMPOSITE_WEIGHTS`(D1) 변경은 하지 않는다
- RRG 산식(`my_chart/analysis/rrg.py`)은 손대지 않는다

### Out of Scope — 데이터 수집과 분류 체계

- 섹터 분류 체계(FnGuide 산업명)는 바꾸지 않는다
- 일봉 DB의 `RS_Line`(종가/KOSPI)은 별개 지표이므로 다루지 않는다
- `my_chart/price.py`의 원시 수익률 컬럼(`RS_1M`~`RS_12M`) 수집 코드는 바꾸지 않는다. IBD식 분기 수익률은 기존 컬럼에서 유도한다
- `stock_prices`에 남은 1~2행짜리 주중 날짜 13개(research.md R2)의 정리는 하지 않는다. RS 루프가 기준 종목 날짜만 처리하므로 이 SPEC의 결과에 영향이 없다

### Out of Scope — 산식과 배지

- `RS_6M_Rating`, `RS_3M_Rating`, `RS_1M_Rating`의 산식은 바꾸지 않는다(분모 필터만 공유한다)
- "가속" 배지(긴 창 RS 4주 상승폭)는 미실측이므로 넣지 않는다. 후속 과제로 남긴다
- `stock_meta.rs_1m`을 일봉 화면(`ChartGrid/ChartCell.tsx` RS 배지, `screen_service.py` 경유 응답)에 연결하는 작업은 하지 않는다(B-2). 후속 과제로 남긴다
- `_RS_TOP_THRESHOLD`/`RS_TOP_THRESHOLD`(80)와 그것을 쓰는 `queries.py`·`momentum.py`의 80/90 기준은 재보정하지 않는다(B-3)
- 20주 평균 주간거래대금 50억 원 규칙을 순위 분모 필터로 쓰지 않는다(Q3). 이 규칙은 회귀 계측 스크립트 안에서만 쓴다
- 섹터 `rs_avg` 열의 삭제나 이름 변경은 하지 않는다(Q2)

### Out of Scope — 고정 픽스처

- `tests/fixtures/frozen/aggregation-2026-08-11/weekly.db`는 재생성하지 않는다. 이 픽스처의 `relative_strength`는 옛 산식 값과 지수 행(186행)을 그대로 담은 채 남는다(research.md R8)
