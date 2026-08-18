---
id: SPEC-SECTOR-METRIC-UNIFY-001
title: Sector Analysis 지표 산출 원천 단일화
version: "0.5.0"
status: in-progress
created: 2026-08-18
updated: 2026-08-18
author: manager-spec
priority: P1
phase: "v0.5.0 target"
module: sector-analysis
lifecycle: spec-anchored
tags: "sector, metrics, consistency, backend, frontend, refactor"
tier: L
depends_on: [SPEC-SECTOR-AGGREGATION-001, SPEC-SECTOR-UX-001, SPEC-SECTOR-GRID-001, SPEC-MARKET-BREADTH-001]
---

# SPEC-SECTOR-METRIC-UNIFY-001 — Sector Analysis 지표 산출 원천 단일화

> 승인된 원본 계획: `.moai/plans/rs-purring-key.md` (169줄, 사용자 승인 완료).
> 본 SPEC은 그 계획의 전사(transcription)이며 재기획이 아니다. 조사·근거·실측치는 원본에서 확정된 것을 옮긴다.

## HISTORY

| 버전 | 날짜 | 변경 |
|---|---|---|
| 0.1.0 | 2026-08-18 | 승인된 계획 `rs-purring-key.md` 전사, 검증 절을 기계 검증 가능한 AC로 형식화 |
| 0.5.0 | 2026-08-18 | plan-audit iteration 3 (PASS 0.92) 잔여 2건. D-A: AC-SMU-001의 "왜 항진명제가 아닌가"에 남아 있던 stale "기준선 20건 실측" 주장 제거 → 구조적 근거(양변이 서로 다른 서비스 모듈)와 경험적 근거(M0 고정 `N`)로 분리. D-B: M4 스케치에 `excluded` 가드 밖 초기화 + 가드 안 `result.excluded` 바인딩 추가(누락 시 M5 배선에서 `NameError` → 503, E-6 분기 B 관측량 붕괴). M5에 `excluded=excluded` 전달 명시 |
| 0.4.0 | 2026-08-18 | plan-audit iteration 2 (PASS-WITH-DEBT 0.85) 대응. D-1: AC-SMU-001 RED 목표를 M0 고정값 `N`으로 전환 + 조정 규칙 신설(`N==0`은 blocker). D-2: E-6를 2분기 측정 게이트로 재작성(갭 G-8). D-3: `§4.4` 중복 → `§4.5`. D-4: ThemeAnalysis 이관처 정정. D-5: `types/bubble.ts` `:6-8` → `:6-9`. D-6/7/8: 인용 정정(`if date:` `:136`, `date=` `:58`, 라우터 `:89`). D-9: AC-SMU-015→REQ-SMU-012, AC-SMU-027→REQ-SMU-026 역참조 |
| 0.3.0 | 2026-08-18 | D7 결정(A) 반영 — M6/M7을 형제 SPEC `SPEC-SECTOR-DISPLAY-UNIFY-001`로 분리. 본 SPEC 범위는 M0~M5 + M8 기록. REQ-SMU-016~022·024는 tombstone(번호 재사용 금지). `PERIOD_SIZE_LADDER`(REQ-SMU-023)는 M4 완결 조건이므로 예외 잔류 |
| 0.2.0 | 2026-08-18 | plan-audit iteration 1 (FAIL 0.71) 대응. D1: 핵심 AC의 비교 대상을 봉투 `data[]` 필드 경로로 확정(레거시 `sectors[]`는 §5 M8에 따라 의도적 제외). D2: frontmatter `tags` 문자열화 + `version` 인용 + `related_specs`→`depends_on`. D3: REQ-SMU-013/020 AC 신설(+011/016 단언 보강). D4: `date` 해석 규약 + 빈 date 엣지. D5: "위치 인자 4건"을 실행 스캔 결과로 교체(호출부 5곳 확정). D6: `tier: L` 선언. D8: `grep -c` 종료코드 규약. D11: `compute_rank_change=False`. D7(REQ/AC 예산)은 조정 대기 — 미조치 |

---

## §1 배경 (Context)

Sector Analysis Bubble 차트에서 섹터 RS가 좁은 구간(26~63)에 뭉쳐 보인다는 관찰에서 조사가 시작됐다. **뭉침 자체는 결함이 아니다** — 백분위 평균의 통계적 성질이며, 실측 분산(SD 7.33)은 독립 가정 예측(3.77)보다 오히려 2배 넓다. 어떤 기간 지표로 바꿔도 SD는 7.3~7.7로 변하지 않는다.

대신 **같은 지표가 화면마다 다른 값을 내는 문제**가 드러났다. RS 정의(`RS_12M_Rating`)는 전 화면이 공유하지만 섹터 단위 집계 구현이 두 벌 존재하며, 결측 처리·벤치마크·거래대금 산식·유니버스가 모두 다르다. 실측 결과 Table 탭과 Bubble 탭에서 **29개 섹터 중 20개가 불일치**한다.

목표는 Sector Analysis의 모든 탭이 **하나의 산출 원천**(`compute_sector_aggregates`)을 공유하게 만드는 것이다. **지표를 바꾸거나 새로 만들지 않는다.**

### §1.1 기존 선례

`backend/services/sector_advanced_service.py:132-143`이 종목 버블에 이미 같은 방식(ranking 재호출로 단일 원천 공유)을 쓰고, 주석에 *"별도 산식을 두지 않는다"*(AC-SAG-042)라고 명시돼 있다. 본 SPEC은 새 원칙을 도입하는 것이 아니라 **이 선례를 섹터 버블로 확장**한다.

`my_chart/analysis/sector_metrics.py:564-567`의 기존 주석도 이 사태를 예고한다 — *"별도 벤치마크 구현을 두면 유니버스·상한·결측 처리가 조용히 갈릴 수 있다"*.

### §1.2 `compute_sector_ranking`이 아니라 `compute_sector_aggregates`인 이유

레거시 `SectorRank`에는 거래대금 필드가 아예 없고, `sector_metrics.py:993-996`이 모든 지표를 `or 0.0`으로 강제해 **동일한 0-대체 결함을 다른 옷으로 재현**하며, 초과수익률이 KOSPI 기준이다.

---

## §2 불변 조건 (건드리지 않는다) — [HARD]

| # | 불변 조건 | 근거 위치 |
|---|---|---|
| INV-1 | **RS 정의 고정.** `RS_12M_Rating` = 1M/3M/6M/9M/12M 백분위 순위의 최근 가중 혼합(1.0/0.8/0.6/0.4/0.2 → 1M이 33.3%로 최대). 생성기는 한 곳뿐 | `my_chart/db/weekly.py:434-454` |
| INV-2 | **RS 벤치마크 KOSPI 고정.** 전 종목이 KOSPI 기준으로 산출 | `my_chart/db/weekly.py:353` |
| INV-3 | **축 배치 현행 유지.** Y = RS(기간 무관 고정), X = 기간 초과수익률. RS를 기간별로 만들지 않는다 | — |
| INV-4 | **RRG의 `rs_ratio`/`rs_momentum`은 별개 지표.** `100 × 섹터지수/벤치마크지수`. 통합 대상 아니며 라벨 구분만 개선 | `my_chart/analysis/rrg.py:182-183` |

> **INV-2 보충 (결함 아님 확정)**: 원천 `RS_1M`~`RS_12M`은 `my_chart/db/price.py:161-164`에서 종목 자체 수익률이고, "상대" 강도는 `weekly.py:434`의 횡단면 `.rank(pct=True)`에서 나온다. 같은 날짜 모든 종목에 KOSPI라는 동일 상수를 적용해도 횡단면 순위는 불변이므로 이 구현은 "KOSPI 기준"과 **결과적으로 동치**다. **결함이 아니며 수정 대상이 아니다.** 이 판정은 재논의하지 않는다.

---

## §3 확인된 결함 (D1~D6, 원본 계획에서 확정)

### D1 — `rs_avg` 결측 처리 분기
ranking은 결측 제외(`my_chart/analysis/sector_metrics.py:450,529`, 사양 §9.1 "0 반환 금지"), bubble은 0점 대체 후 전체 N으로 나눔(`my_chart/analysis/sector_advanced.py:247,590,604`). 29개 섹터 전부 0-대체 예측과 정확히 일치. 방산 -5.92(18중 2결측), 조선 -4.90(30중 3결측).

### D2 — 초과수익률 정의 3개

| 정의 | 벤치마크 | 기계 1M | 쓰는 곳 |
|---|---|---|---|
| A `sectors[]` | KOSPI 지수 (+2.31%) | 22.36 | Table 화면 |
| **B `data[]` 봉투** | **상한 시총가중 유니버스 (+5.96%)** | **18.70** | 화면 미사용 |
| C bubble | KOSPI 지수, 등가중 | 18.05 | Bubble 화면 |

**결정: B로 통일.** 섹터도 상한재배분 시총가중이므로 같은 구성 기준의 유니버스와 비교하는 것이 정합적이고, All 시장을 보며 KOSPI만 잣대로 쓰는 A의 문제가 없으며, Bubble X축 라벨이 이미 B를 서술한다. 시장별 벤치마크 `ALL_CAPPED`(2546) / `KOSPI_CAPPED`(827) / `KOSDAQ_CAPPED`(1719) — **셋 다 지수가 아니라 상한 시총가중 유니버스**이므로 라벨 규칙이 세 시장에 동일 적용된다(실측 확인).

### D3 — 거래대금 산식 불일치
bubble `close * volume` 주봉 1개(`sector_advanced.py:592`) vs ranking VolumeWon 기간 누적(`sector_metrics.py:523-527`). 약 2.5e7배 차이.

### D4 — bubble이 봉투를 채우지 않음
`get_sector_bubble`이 `envelope_fields()`를 호출하지 않고 응답을 직접 생성(`backend/services/sector_advanced_service.py:72-78`). 결과: `data: []`·`benchmark: null`·`return_window_days` 전부 기본값이고, **`market_filter`가 모든 요청에 "all"로 고정**된다. 형제 엔드포인트는 전부 설정한다(`backend/services/sector_ranking_service.py:99`). 봉투가 어느 시장을 필터했는지 거짓을 말하는 유일한 엔드포인트.

### D5 — Table 기간 토글 무동작
`frontend/src/api/market.ts:12-19`가 `period`를 안 보냄. **중요**: `period`만 추가해도 화면은 안 바뀐다. 기간별 `rank` 재배정은 `data[]`에만 있고(`sector_metrics.py:695-706`), 프론트가 읽는 `sectors[]`는 `compute_sector_ranking`이 `period`를 받지 않아 항상 composite 기준이다. **`data[]`를 읽어야 실제로 동작한다.**

### D6 — 라벨·표시 부정확
`'RS 중앙'`이 계산된 중앙값이 아닌 50 상수(`SectorBubbleChart.tsx:217`) / `'RS Top %'`가 RS 점수처럼 보이나 실제로는 "RS≥80 비율"(임계값 미표기) / UI에서 "RS"가 세 가지를 지칭(등급·RRG RS-Ratio·RS Line, `ChartCell.tsx:326`과 `:352`가 한 셀에 공존) / 같은 지표 반올림 제각각(`Math.round` / `toFixed(1)` / 반올림 없음) / `MetricCard`가 null에 `null%` 문자열 렌더(ER-2 위반).

---

## §4 요구사항 (GEARS)

### §4.1 백엔드 — 단일 원천

- **REQ-SMU-001** (Ubiquitous) — `/api/sectors/bubble` 응답의 섹터 지표는 `compute_sector_aggregates` 산출을 투영한 값이어야 하며, `/api/sectors/ranking` 응답의 **봉투 `data[]`**(= `agg.aggregates`, `backend/services/sector_ranking_service.py:106`)와 일치해야 한다. 버블 전용 산식을 별도로 두지 않는다.
  > **일치 대상은 `data[]`이며 레거시 `sectors[]`가 아니다.** `SectorRankItem`(`backend/schemas/sector.py`)에는 `trading_value` 필드가 **존재하지 않으므로** 그 비교는 좌변 자체가 없고, `sectors[]`의 `excess_returns`는 정의 A(KOSPI)라 M5 이후에도 시장·기간별 상수만큼 다르다 — §5 M8이 그 잔여를 **설계상 의도된 것**으로 명시한다. 따라서 `sectors[]`는 일치 검증에서 **의도적으로 제외**한다.
- **REQ-SMU-002** (Ubiquitous) — 섹터 `rs_avg` 산출기는 `relative_strength` 결측 종목을 분모에서 제외해야 한다. 0점 대체 후 전체 N으로 나누지 않는다.
- **REQ-SMU-003** (When) — 섹터의 전 구성 종목이 RS 결측일 때, 산출기는 `0.0`이 아니라 `None`을 반환해야 한다.
- **REQ-SMU-004** (Ubiquitous) — 섹터 초과수익률은 정의 B(시장별 상한 시총가중 유니버스 벤치마크) 기준이어야 하며, `returns[p] - benchmark.returns[p] == excess_returns[p]` 항등식을 만족해야 한다.
- **REQ-SMU-005** (Ubiquitous) — 섹터 거래대금은 VolumeWon 기간 누적(`sector_metrics.py:523-527`)이어야 한다. 주봉 1개의 `close * volume`을 쓰지 않는다.
- **REQ-SMU-006** (Ubiquitous) — 섹터 `rs_avg`는 기간(1w/1m/3m)과 무관하게 동일해야 한다(INV-3 회귀 방어).

### §4.2 백엔드 — 배선·봉투·스키마

- **REQ-SMU-007** (Ubiquitous) — `get_sector_bubble`은 `daily_db_path: str | None = None`을 **키워드 기본값 인자**로 받아야 하며, 라우터(`backend/routers/sectors.py`)가 `DAILY_DB_PATH`를 전달해야 한다.
- **REQ-SMU-008** (unwanted) — `daily_db_path`를 위치 필수 인자로 만들지 않는다. 실행 스캔으로 확정한 기존 호출부는 아래 4곳이며(정의부 1곳 제외), 그중 **단일 위치 인자 호출 3곳**이 깨진다.
  ```
  $ grep -rn 'get_sector_bubble(' --include='*.py' . | grep -v '\.venv'
  tests/test_consumer_dates.py:438:            ).get_sector_bubble(db).date,
  tests/test_ac_sag_037_endpoint_date_consistency.py:87:    return get_sector_bubble(weekly).as_of_date
  tests/test_ac_sag_037_endpoint_date_consistency.py:184:        "/sectors/bubble": get_sector_bubble(weekly_db).grid_version,
  backend/routers/sectors.py:89:        return get_sector_bubble(WEEKLY_DB_PATH, period=period, market=market)
  backend/services/sector_advanced_service.py:41:def get_sector_bubble(
  ```
  > 원본 계획의 "4건"은 미검증 수치였고 `tests/test_consumer_dates.py:438`을 누락했다. 위 출력이 관측된 리터럴이다(2026-08-18, 미변경 트리).
- **REQ-SMU-009** (Ubiquitous) — `/api/sectors/bubble` 응답은 `envelope_fields(...)`로 구성되어야 하며, `market_filter`는 요청 `market` 값을 반영해야 한다.
- **REQ-SMU-010** (Ubiquitous) — 레거시 봉투 키 `date`/`period`/`market`/`sectors`는 유지되어야 한다(`tests/test_response_contract.py:327`이 고정).
- **REQ-SMU-011** (Ubiquitous) — `SectorBubbleItem`의 4개 수치 필드(`period_return`/`excess_return`/`rs_avg`/`trading_value`)와 `frontend/src/types/bubble.ts:6-9`은 nullable(`float | None` / `number | null`)로 동시 확장되어야 한다.
  > 원본 계획은 `:6-8`로 인용했으나 4개 필드는 `:6-9`에 걸쳐 있다(`period_return`이 `:9`). `:6-8`을 따르면 3개만 넓혀 AC-SMU-029("4개")와 어긋난다.
- **REQ-SMU-012** (unwanted) — 결측 섹터를 차트 데이터에서 드롭하지 않는다. `MetricCell.tsx:4-11`(ER-1/ER-2)이 "결측은 반드시 '–' 로만 렌더"를 명시적으로 요구한다.
- **REQ-SMU-013** (unwanted) — `MetricValueModel`을 버블 아이템에 싣지 않는다. `SectorBubbleChart.tsx:127`이 스칼라를 ECharts 튜플로 펼치므로 파괴적 변경이다. 결측 사유는 봉투 `data[]`로 전달한다.
- **REQ-SMU-014** (unwanted) — `compute_sector_bubble`을 삭제하지 않는다. `detect_sector_transitions`(`my_chart/analysis/sector_advanced.py:951`)가 `/market/overview` 경로(`backend/services/market_service.py:158-161`)로 소비한다.
- **REQ-SMU-015** (Ubiquitous) — `compute_sector_bubble`은 "HTTP 엔드포인트를 다시 지원하지 말 것"을 명시하는 deprecation docstring을 가져야 하고, `backend/services/sector_advanced_service.py`는 이 심볼을 더 이상 참조하지 않아야 한다.

### §4.3 프론트엔드 — M4 완결 조건 1건만 잔류

- **REQ-SMU-023** (Ubiquitous) — `PERIOD_SIZE_LADDER`의 `vMin`/`vMax`(`frontend/src/components/SectorAnalysis/bubbleRadius.ts`, 소비처 `SectorBubbleChart.tsx:95`)는 M4 이후의 실제 거래대금 분포를 담아야 한다.
  > **파일 경로는 프론트지만 이 항목은 M4의 완결 조건이지 표시 개선이 아니다.** 거래대금 단위를 바꾸는 당사자가 M4이며, 이 항목을 프론트 SPEC으로 미루면 **백엔드만 머지된 구간에서 모든 버블이 한쪽 끝으로 뭉친 채 배포된다.** 경로만 보고 `SPEC-SECTOR-DISPLAY-UNIFY-001`로 옮기지 말 것.

### §4.4 프론트엔드로 이관된 요구사항 (tombstone — 번호 재사용 금지)

아래 번호는 **본 SPEC에서 비어 있으며 다른 요구사항에 재할당하지 않는다.** 전부 `SPEC-SECTOR-DISPLAY-UNIFY-001`로 이관됐다.

| 이관된 번호 | 내용 | 이관처 |
|---|---|---|
| REQ-SMU-016 | 반올림 규약 단일 출처(`MetricCell.tsx`) | REQ-SDU-001 |
| REQ-SMU-017 | `MetricCard` `null%` 버그 해소 | REQ-SDU-002 |
| REQ-SMU-018 | RS 임계값 상수화(`rsMetrics.ts`) | REQ-SDU-003 |
| REQ-SMU-019 | 라벨 정확성 | REQ-SDU-004 |
| REQ-SMU-020 | 색 램프 분리 | REQ-SDU-005 |
| REQ-SMU-021 | Table 기간 토글 `data[]` 실동작 | REQ-SDU-006 |
| REQ-SMU-022 | `data[]` 부재 폴백 캡션 | REQ-SDU-007 |
| REQ-SMU-024 | RS 문자열 3면 동일성 | REQ-SDU-008 |

### §4.5 프로세스 (마일스톤 순서 자체가 요구사항)

- **REQ-SMU-025** (Ubiquitous) — 특성화 테스트(M0)는 프로덕션 코드를 손대지 않은 트리에서 GREEN으로 관측된 뒤 **단독 커밋**으로 먼저 랜딩되어야 한다.
- **REQ-SMU-026** (Ubiquitous) — M4 외의 모든 마일스톤은 산출 수치를 바꾸지 않아야 한다. M4 밖에서 숫자가 움직이면 다른 것이 깨진 것이다.

---

## §5 범위 밖 (exclusions)

아래 항목은 본 SPEC에서 **out of scope**이며, 구현하지 않는다.

### Out of Scope — 같은 유형·다른 화면의 0-대체
- `backend/services/sector_detail_service.py:120,130` 하위그룹 0-대체. 동일 결함 유형이지만 다른 화면이며 별도 SPEC 대상.

### Out of Scope — Stage 분류 결측 유입
- `my_chart/analysis/sector_advanced.py:706`, `my_chart/analysis/stage_classifier.py:79`에서 RS 없는 종목이 조용히 "Stage 2 Weak"로 분류되는 경로. 본 SPEC은 섹터 집계만 다룬다.

### Out of Scope — 레거시 스크립트
- `my_chart_home_v5-10_noterin.py`의 3M/6M 스크린 불일치. 백엔드에서 import되지 않아 죽은 경로로 보이나 미확인 상태로 남긴다.

### Out of Scope — RS 집계 방식 변경
- 중앙값·시총가중·breadth 전환 등 RS 집계 방식 변경. "뭉침은 결함 아님" 판정에 따라 보류한다.

### Out of Scope — ThemeAnalysis 동일 패턴
- `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx`가 같은 표시 패턴을 갖는지 미확인. **M6은 본 SPEC을 떠났으므로** 이 항목은 형제 SPEC `SPEC-SECTOR-DISPLAY-UNIFY-001`(갭 G-F2) 소관이다. 본 SPEC의 AC 대상이 아니다.

### Out of Scope — 프론트엔드 표시 통일 (M6·M7)
- 반올림 규약·임계값 상수화·라벨 정확성·색 램프 분리(M6)와 Table 기간 토글 실동작(M7)은 **형제 SPEC `SPEC-SECTOR-DISPLAY-UNIFY-001`** 소관이다. 본 SPEC은 M0~M5(+M8 기록)만 다룬다.
- **왜 둘로 나뉘었나 (재논의 금지)**: 절단면은 감사가 새로 그은 것이 아니라 **승인된 원본 계획서 자신이 이미 그어 둔 것**이다 — `.moai/plans/rs-purring-key.md`의 M6 헤더가 *"프론트 표시 통일 (백엔드 독립, 먼저 배포 가능)"*이라고 명시한다. 예산을 맞추려 자른 것이 아니라 원래 둘이던 것을 하나로 묶어 뒀던 것이며, 배포 순서(백엔드 선행 → 프론트 후행)와도 일치한다.
- 예외 1건: `PERIOD_SIZE_LADDER` 재산출은 프론트 파일이지만 M4 완결 조건이므로 본 SPEC에 잔류한다(§4.3).

### Out of Scope — M8 잔여 (별도 판단)
- M5 이후에도 레거시 `sectors[]`는 KOSPI 기준이라 Table과 Bubble이 **시장·기간별 상수**(`상한가중 벤치마크 − KOSPI 지수`)만큼 차이 난다. 모든 섹터에 동일하게 적용되므로 **순서는 같고 x=0 선만 이동**한다. 오늘의 섹터별 제각각 불일치보다 훨씬 작은 잔여이며, `sectors[]`를 `data[]`로 이관할지는 **별도 결정** 사항으로 본 SPEC에서 구현하지 않는다.

---

## §6 참조

- 승인된 원본 계획: `.moai/plans/rs-purring-key.md`
- 선행 SPEC: SPEC-SECTOR-AGGREGATION-001(`compute_sector_aggregates` 도입), SPEC-SECTOR-UX-001(버블 사다리·MetricCell 규약), SPEC-SECTOR-GRID-001(대조 단언 교훈)
- 프로젝트 교훈: `lessons.md` #9(대조 단언은 되돌림 RED 관측으로만 판정), #8(brownfield 컬럼 정합)
