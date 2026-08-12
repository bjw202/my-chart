---
id: SPEC-SECTOR-AGGREGATION-001
title: "섹터 집계 계층 — 시총가중·벤치마크·순위·RRG 지수·응답 공통 스키마"
version: "0.2.1"
status: draft
created: 2026-08-12
updated: 2026-08-12
author: manager-spec
priority: P0
phase: "sector-ux v1"
module: "my_chart/analysis, backend/services, backend/schemas, backend/routers"
lifecycle: spec-anchored
tags: "sector, aggregation, benchmark, rrg, ranking, api-contract"
depends_on: [SPEC-SECTOR-GRID-001]
related_specs: [SPEC-SECTOR-GRID-001, SPEC-SECTOR-UX-001]
tier: L
---

# SPEC-SECTOR-AGGREGATION-001: 섹터 집계 계층 — 시총가중·벤치마크·순위·RRG 지수·응답 공통 스키마

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 0.1.0 | 2026-08-12 | manager-spec | 초기 SPEC. `docs/sector-ux/01-data-contract.md` §2(지표 사전)·§5(집계)·§6(벤치마크)·§8(화면별 계약)·§9(결측 정책)을 구현 계약으로 전환. `02-screen-flow.md` §12.3 서버 선행 조건 전부 포함. Lesson #3/#4/#5/#7 반영. |
| 0.2.0 | 2026-08-12 | manager-spec | plan-audit 0.83 FAIL(L, thresh 0.85) 결함 델타 반영. **사용자 결정 4건 수용**: O-A1(RS-Ratio **롤링 정규화 미적용** — 100이 문자 그대로 벤치마크. 표준 JdK RRG와의 발산 및 강세장 사분면 편중이 정상임을 명시), O-A3(상수 주식수 가정 한계를 `warnings[]`에 명시 + **"현재주가" = daily 최신 `Close`**. 이벤트 감지는 과설계로 미구현), O-A4(**거래대금 창 = 기간 토글 연동** `[anchor(t,N), t]` + `trading_value_window_days` 동반), O-A6(**지표별 `coverage.*` + 최상위 최소값** 병행 — AG-7 임계는 최소값에 적용). **AC 반증 가능성 복구**: AC-SAG-037(라이브 `naive MAX == canonical`이라 SN-3 반증 불가 → `fixture_max_ne_canonical` + 엔드포인트별 되돌림 7회), AC-SAG-025(동일성 단독 단언은 양쪽이 모두 구 분류기여도 통과 → 주봉 Weinstein 기대 stage 리터럴 3케이스 + `_classify_stage_simple` 대조 + rename 내성 행동 단언), AC-SAG-016(`is not 0.0` float 아이덴티티 비교 삭제 — 결함 미검출 + `SyntaxWarning`), AC-SAG-045(R2 `10<=k<=24`는 29섹터의 34~83%로 무게이팅 + AC-SAG-013 중복 → **삭제**; R4/R5는 비교 대상 미보존으로 실행 불가였으므로 **골든 baseline 캡처를 plan.md M1.0 선행 작업으로 신설**; R7 "그런 테스트가 없음을 확인"을 행동 단언 + grep 2종으로 재작성). **§8 프로즌 픽스처 규약 신설** — 주 1회+ `/api/db/update`로 게이팅 AC가 코드 변경 없이 붉어지는 문제. **O-A8 신설** — ①의 O-G2(미완성 주 바와 기간 계산의 정합)를 인수, M3 차단 항목. **O-A7에 ③ 의존 교차 링크** 추가. |
| 0.2.1 | 2026-08-12 | manager-spec | plan-audit iteration 2 **PASS 0.88**(L, thresh 0.85; MUST-PASS 전항 통과, 단조 개선) 이후 잔여 결함 정리. **(D5) `AC-SAG-011`이 §8 프로즌 픽스처 규약 밖에 있었다** — 1W 벤치마크 실측값(KOSPI +1.03% / KOSDAQ +7.54% / All +1.88%, ±0.5%p)을 게이팅 기대값으로 못 박으면서 §8의 게이팅 표에도, §8.5 "순수 합성 · 해당 없음" 열거에도 없었다. `/api/db/update` 1회로 코드 변경 없이 붉어지는, §8이 막으려는 바로 그 형태다. **게이팅 표에 등재**하고 AC 본문에 프로즌 한정을 명시했다. `AC-SAG-044`(정적 스캔 + mutation 대조, 라이브 값 없음)도 어느 열거에도 없었으므로 **N/A로 명시 등재**했다 — 무해하지만 같은 누락 경로다. **§8.6 열거 완결성 규칙 신설**: `AC-SAG-001`~`045` 전부가 (게이팅 표) 또는 (순수 합성 열거) 중 정확히 한 곳에 나타나야 하며, 신규 AC는 반드시 한쪽에 등재한다 — 어느 쪽에도 없는 AC가 규약 밖에 방치되는 것이 011/044의 누락 경로였다. **(D6) 골든 baseline 캡처 문구의 잘못된 절 참조 정정** — `acceptance.md:416`이 프로즌 규약을 **§9**로 가리켰으나 §9는 품질 게이트이고 프로즌 규약은 **§8**이다(`plan.md:55`는 이미 §8로 정확했다). |

---

## 0. BRIEF (Lesson #7 [HARD] 의무 항목)

### 0.1 라이브 사용 가설 + 재평가 체크포인트

| 항목 | 내용 |
| --- | --- |
| 가설 | 사용자는 섹터 순위표를 "어느 섹터에 돈이 들어오고 있는가"의 1차 판단에 쓴다. 시총가중 전환 후, 사용자는 **대형주가 지배하는 섹터의 순위 하락을 납득**하고, 초과수익률 부호가 양방향으로 갈리는 것을 "시장 폭 신호"로 읽을 수 있어야 한다. |
| 기대 행동 | ship 후 1~2주 사용 시점에 (a) 상위 섹터 → 종목 탐색 진입 동선이 유지되는가, (b) "순위가 이상하다"는 신고가 발생하지 않는가, (c) RRG 사분면 편중을 사용자가 시장 방향으로 해석하는가. |
| 정량 지표 | 1W 초과수익률 양수 섹터 29/29 → **18/29**. 신고가 종목 99 → **56**. 순위 평균 이동 3.5계단. RRG 워밍업 12점 제거. |
| 재평가 시점 | ③ UI ship 이후 **라이브 사용 7일 시점**에 사용자에게 "시총가중 순위가 직관과 맞는가 / 상한 10%가 적절한가"를 확인한다. 상한값(10%)은 재평가 대상이며, 변경 시 `weight_cap` 단일 상수만 조정한다. |
| 폐기 조건 | 사용자가 시총가중 순위를 신뢰하지 않아 등가중으로 되돌리기를 원하면, `weight_cap` 대신 가중 모드 토글을 추가하는 후속 SPEC으로 대응한다. 본 SPEC 전체 폐기는 상정하지 않는다(격자·벤치마크 정합성은 가중 방식과 독립적으로 옳다). |

### 0.2 성능 baseline + 목표값

| 측정 지점 | baseline (측정 의무) | 목표 |
| --- | --- | --- |
| `GET /sectors/ranking` P50 / P95 | 현행 무파라미터 응답 실측 | (period, market) 조합별 P95 < baseline × 1.5 |
| `GET /sectors/rrg` P95 | 현행 실측 | 지수 연쇄 + 시총 역산 추가로 baseline × 2.0 이내 |
| `GET /sectors/history` P95 | 현행 실측 | baseline × 1.5 이내 |
| 상한 재배분 반복(AG-1) 수렴 횟수 | 신규 | 섹터당 <= 5회 (01 §5.2 실측) |
| 전 섹터 집계 1회 (29 섹터 × 2,546 종목) | 신규 | < 300ms |

**③ UI가 기간 토글마다 서버 재조회를 유발**하므로(CT-4 trade-off) 응답 지연이 곧 사용자 체감이다. baseline 미측정 상태에서 M 착수를 금지한다.

### 0.3 SPEC ID ↔ UI 요소 매핑 표

본 SPEC이 **값을 공급**하는 UI 요소 (렌더링은 ③ 소관):

| UI 요소 | 공급 필드 | 신규/변경 |
| --- | --- | --- |
| 순위표 `Rank` 열 | `rank` (period, market 함수) | 의미 변경 |
| 순위표 `복합점수` 열 | `composite_score` | 신규 열(값은 기존, 정규화 방식 변경) |
| 순위표 `Δ순위` 열 헤더의 기준일 | `baseline_date` | 신규 필드 |
| 헤더 벤치마크 표기 `전체 상한가중(10%) +1.88%` | `benchmark.name`, `benchmark.return_*`, `weight_cap` | 신규 |
| 기준일 배지 / 진행 중 배지 | `as_of_date`, `as_of_is_partial_week` | 신규 (값 출처는 ①) |
| 표 하단 `순위 대상 제외 (2)` 영역 | `excluded[]` | 신규 |
| 저신뢰 `⚠` 배지 | `coverage_ratio`, `low_confidence` | 신규 |
| 상세 패널 `가중치 상한 적용 3종목` | `capped_members[]` | 신규 |
| 상세 패널 `유효N` | `effective_n` | 신규 |
| 종목 표 `섹터비중` 열 | `weight_in_sector` | 신규 |
| Stage 분포 바 `미분류` 세그먼트 | `unclassified_count` | 신규 |
| 종목 버블 X 기준선 값 | `sector_aggregate` | 신규 |
| RRG 사분면 라벨의 벤치마크 이름 | `benchmark_name` | 신규 |
| RRG 궤적 시작 표기 | `trail_start_date`, `lookback_weeks` | 신규 |
| Bump 축 하단 `12주 (84일)` | `weeks`, `span_days` | 신규 |

**본 SPEC 단독으로는 화면에 아무 변화가 없다** — 필드를 추가할 뿐 렌더링은 ③이 한다. 사용자가 "이 SPEC의 결과"로 인식할 화면은 ③의 것이다.

### 0.4 rollback 시나리오

| 단계 | 안전 commit 경계 | rollback |
| --- | --- | --- |
| M1 (집계 코어) | 신규 함수 추가 + 기존 경로 미변경 | 파일 단위 revert |
| M2 (벤치마크) | 단일 commit | revert 시 초과수익률이 현행 편향 상태로 복귀 |
| M3 (순위/정규화) | 단일 commit | revert 시 min-max + 비대칭 반올림 복귀 |
| M4 (RRG) | 단일 commit | revert 시 횡단면 z-score 복귀. **③의 RRG 범례 변경과 짝** — ③ 배포 후 ②만 revert하면 라벨과 값이 어긋난다 |
| M5 (지표 정정: MAX52/Stage/volume) | 지표별 개별 commit | 지표 단위 revert 가능 |
| M6 (응답 스키마 + 라우터 파라미터) | 단일 commit | **추가 전용 필드 + optional 파라미터**라 기존 프론트와 하위 호환 → 단독 revert 안전 |

**설계 원칙**: M6의 응답 필드는 전부 **추가**이고, 라우터 파라미터는 전부 **optional + 기본값**이다. 따라서 ② 단독 ship이 안전하고 ③은 나중에 붙일 수 있다(Lesson #7 rollback 단순화).

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **선행 설계 (Tier L 산출물 대체)**: 본 SPEC은 Tier L이나 `design.md` / `research.md`를 새로 작성하지 않는다. 그 역할은 이미 확정·교차검증된 다음 두 문서가 수행한다.
  - 연구/실측: `docs/sector-ux/01-data-contract.md` (855줄, 전 수치가 read-only 쿼리 실측)
  - 설계: `docs/sector-ux/02-screen-flow.md` §12.3 (서버 선행 조건)
  - 중복 작성은 SSOT 분기를 만들므로 금지한다. 두 문서를 **인용**한다.
- **선행 SPEC**: `SPEC-SECTOR-GRID-001` (격자·유효 유니버스·`as_of_date`·`anchor(t,days)` 공급). **본 SPEC은 ①이 close된 뒤에 run 착수한다.**
- **변경 성격**: BROWNFIELD — 기존 엔드포인트의 의미가 바뀐다.
- **개발 방법론**: TDD.

### 1.2 기존 코드 현황 (01 부록 A 인용)

| 경로 | 현행 결함 | 본 SPEC의 조치 |
| --- | --- | --- |
| `sector_metrics.py:173-175` | `sum/n` 등가중 | 시총가중 + 상한 |
| `sector_metrics.py:42-44` 주석 | 시총가중이라 **거짓 기재** | 주석 정정 |
| `sector_metrics.py:151-154, 176, 179-184` | RS `or 0.0` + 분모 잔존 | 결측 제외 |
| `my_chart/price.py:148` | `MAX 52W = Close.rolling(52).max()` | 사용 중단, `MAX(High) over 364d`로 판정 |
| `sector_metrics.py:164` | `Close >= MAX52 × 0.98` | 실제 High 기준으로 판정 |
| `backend/services/sector_detail_service.py:23-47` | 일봉 근사 Stage 분류기 | **폐기** |
| `my_chart/analysis/stage_classifier.py:classify_stage` | 주봉 Weinstein | **단일 채택** |
| `sector_advanced.py:608, 705` | `volume_sma10 = sma10` (가격 SMA) | weekly `VolumeSMA10` 사용 |
| `sector_advanced.py:608, 705` | 거래대금 산출 | daily `VolumeWon` 사용 |
| `sector_metrics.py:285, 311` | 비결정 tie-break | `(−composite, sector_name)` |
| `sector_metrics.py:230-237` | `LIMIT 1 OFFSET 3` | ①의 `anchor(t, 28)` |
| `sector_metrics.py:275-280, 305-309` | 반올림 비대칭 | 반올림 전 값으로 비교 |
| `sector_metrics.py:109-117` | min-max 정규화 (`:115-116` 붕괴 시 50.0) | 순위 백분위 정규화 |
| `sector_metrics.py:94-106` | `_load_kospi_returns` 조용한 0.0 | 명시적 오류 상태 |
| `sector_advanced.py:145-178` | `_get_benchmark_return` KOSPI 고정, RRG 미사용 | 시장별 전환 + RRG 경로 연결 |
| `sector_advanced.py:285-304` | 날짜별 지수 재계산 | 수익률 연쇄 |
| `sector_advanced.py:328-331` | `_rolling_zscore` 상수 100 패딩 | 워밍업 미발행 |
| `sector_advanced.py:437-453` | RS-Ratio 횡단면 z-score | 벤치마크 기준 |
| `sector_advanced.py:537` | 혼합 방법론 초과수익률 | 방법론 일치 |
| `backend/routers/sectors.py:43-58` | `sector_ranking()` 무파라미터 | `period`·`market` 신설 |
| `backend/routers/sectors.py:82-83` | `sector_rrg()` 무파라미터 | `market` 신설 |
| `backend/routers/sectors.py:100-102` | `weeks`만 | `market` 신설 |
| `backend/routers/sectors.py:134-137` | 종목 버블 `period`만 | `market` 신설 |
| `backend/services/stage_service.py:81-91` | `by_sector` 이미 존재 | `unclassified_count` 추가 |
| `tests/test_sector_metrics.py:195-215` | 8개 `hasattr` 호출 — 값 단언 없음 | **의미 테스트로 대체** |

### 1.3 테스트 현황 (실측)

`tests/test_sector_metrics.py:195-215`는 `hasattr` 8회만 호출하고 값을 검증하지 않는다. 가중 방식을 등가중 ↔ 시총가중으로 바꿔도 **어떤 테스트도 실패하지 않는다.** 본 SPEC은 신규 의미 테스트를 **1급 산출물**로 취급한다(§4 Exclusions 아님).

---

## 2. Assumptions (가정, Lesson #5)

- **A1**: ①이 제공하는 `effective_universe(as_of_date, market)`가 집계의 유일한 모집단이다. ②는 유니버스를 직접 산출하지 않는다.
- **A2 (사용 패턴)**: 단일 사용자, 주 1회~수시 수동 갱신, 실시간 요구 없음. 따라서 집계는 **요청 시 계산**하고 사전 배치 계산 테이블을 만들지 않는다.
- **A3 (캐시 모델)**: 서버 캐시는 `(as_of_date, market_filter, period, grid_version)` 키의 **프로세스 내 메모이즈**만 둔다(01 §7.2 SN-5). Redis 등 외부 캐시는 도입하지 않는다 — `MarketContext` 수동 갱신 패턴(프로젝트 기존 모델)과 일관.
- **A4**: `stock_meta.market_cap`은 **현재 시점 스냅샷**이며 시점별 시총 이력 테이블은 존재하지 않는다(01 §10 O-3). RRG는 역산에 의존한다.
- **A5**: `VolumeWon`은 daily DB에 존재하며 최신일 NULL 0건(실측). 재계산하지 않는다.
- **A6 (dataframe 전파, Lesson #4)**: `sector_advanced.py`는 dict/dataclass 파이프라인이며 pandas derived dataframe 복사 의미 문제가 있는 경로는 `sector_metrics.py`의 집계 중간 구조다. 신규 필드(coverage/weight/capped)는 **dataclass → Pydantic → JSON 전 구간에서 명시 전파**되어야 하며 이를 AC로 검증한다.
- **A7**: 프론트엔드는 본 SPEC이 추가한 필드를 **무시해도 동작**한다(추가 전용). 따라서 ② 단독 ship이 안전하다.
- **A8**: 지수 행(`Name='KOSPI'`/`'KOSDAQ'`)은 **정합성 검증용**으로만 읽고 초과수익률 기준으로 쓰지 않는다. 지수 레벨·지수 High/Low는 **화면에 노출하지 않는다**(01 O-4 결정).

---

## 3. Requirements (요구사항, GEARS)

### 3.1 가중·집계

#### REQ-SAG-001 (Ubiquitous) — 시총가중 + 반복 상한 재배분

The aggregation module **shall** compute sector returns as `Σ(wᵢ×rᵢ)/Σwᵢ` where `wᵢ` is derived by the iterative capping algorithm: `wᵢ = capᵢ/Σcap`, `cap_eff = max(0.10, 1/N)`, then iteratively clip over-cap weights and redistribute the excess proportionally until no weight exceeds `cap_eff`, with `Σwᵢ = 1` (규칙 AG-1).

- 검증: AC-SAG-001, AC-SAG-002

#### REQ-SAG-002 (Ubiquitous) — 상한 적용 사실의 노출

Every sector aggregation response **shall** include `weight_cap` and `capped_members[]` (종목명 + 원비중 + 적용 후 비중) (규칙 AG-2).

- 검증: AC-SAG-003

#### REQ-SAG-003 (When) — 결측 종목의 완전 제외

When a constituent's period return (`CHG_*`) is NULL, the aggregation **shall** exclude it from numerator, denominator, and weight renormalization alike. 0 치환을 금지한다 (§2.0 분모 규칙).

- 검증: AC-SAG-004

#### REQ-SAG-004 (When) — NULL market_cap 처리

When a constituent's `market_cap` is NULL or `<= 0`, the aggregation **shall** exclude it from cap-weighted metrics while **including** it in equal-weighted metrics (RS 평균, Stage 비율, 신고가 비율, 종목 수), and **shall** report `cap_coverage_ratio` (규칙 UN-6, AG-3). 대체값(1.0·중앙값) 부여를 금지한다.

- 검증: AC-SAG-005

#### REQ-SAG-005 (Where) — 유효 시총 종목 부족 시

Where a sector's valid-market-cap constituent count falls below the §5.4 minimum, the cap-weighted metrics **shall** be `null` and only equal-weighted metrics are provided, with the methodology difference flagged in the response (규칙 AG-4).

- 검증: AC-SAG-006

#### REQ-SAG-006 (Where) — 최소 구성종목 수

Where a sector's post-filter effective constituent count is below 5, the sector **shall** be excluded from ranking / bubble / RRG output and listed in `excluded[]` with `reason: "insufficient_members"` and `count` (규칙 AG-5). 목록에서 숨기는 것을 금지한다.

- 검증: AC-SAG-007

#### REQ-SAG-007 (Ubiquitous) — 커버리지 필드 동반

Every sector aggregation entry **shall** carry `member_count`, `valid_count`, `coverage_ratio`, `cap_coverage_ratio` (규칙 AG-6).

**O-A6 결정 (2026-08-12) — 지표별 커버리지 + 최상위 최소값 병행**:

- `coverage: {rs, nh, stage, chg, trading_value}` 객체를 추가로 싣는다. `01 §5.5`의 `valid_count` 정의가 이미 지표별이므로 단일 필드로는 "어느 지표가 비었는가"를 알 수 없다.
- **동시에 최상위 `coverage_ratio = min(coverage.*)`을 유지한다** — 기존 단일 필드 소비자(§8.1 저신뢰 판정, REQ-SAG-008의 AG-7 임계, ③의 `⚠` 배지)를 깨지 않기 위한 하위 호환 장치다.
- **AG-7의 0.80 / 0.50 임계는 최상위 최소값에 적용한다.** 지표별 값에 개별 임계를 걸지 않는다 — 한 지표만 비어도 행 전체가 저신뢰로 표시되는 것이 보수적으로 옳다.
- `valid_count`도 동일하게 `valid_counts: {rs, nh, stage, chg, trading_value}` + 최상위 최소값 형태를 취한다.

- 검증: AC-SAG-008 (불변식 **AG-6**)

#### REQ-SAG-008 (Where) — 커버리지 하한

Where `coverage_ratio < 0.80`, the entry **shall** carry `low_confidence: true`. Where `coverage_ratio < 0.50`, the metric value **shall** be `null` with `reason: "insufficient"` (규칙 AG-7).

- 검증: AC-SAG-009

#### REQ-SAG-009 (Ubiquitous) — 유효 종목수 노출

The sector detail response **shall** include `effective_n = 1/Σwᵢ²` (상한 적용 후) (01 §5.1).

- 검증: AC-SAG-010

### 3.2 벤치마크

#### REQ-SAG-010 (Ubiquitous) — 시장별 벤치마크

The benchmark **shall** be the cap-applied market-cap-weighted aggregate of the filtered universe: KOSPI 필터 → KOSPI 구성종목, KOSDAQ → KOSDAQ, All → 전체 (규칙 BM-1).

- 검증: AC-SAG-011

#### REQ-SAG-011 (Ubiquitous) — 방법론 일치

The benchmark **shall** be computed with the same effective universe, the same 10% cap, the same canonical grid dates, and the same missing-value handling as the sector aggregates (규칙 BM-2).

- 검증: AC-SAG-012 (불변식 **EX-1**), AC-SAG-013 (불변식 **EX-2**)

#### REQ-SAG-012 (Ubiquitous) — 동일 날짜 창

Sector return and benchmark return **shall** use the same as-of date and the same past anchor date, and both dates **shall** appear in the response (불변식 BM-6).

- 검증: AC-SAG-014 (불변식 **BM-6**)

#### REQ-SAG-013 (When) — 지수 행 정합성 검증

When the difference between the uncapped pure cap-weighted constituent aggregate and the index row (`Name='KOSPI'`/`'KOSDAQ'`) exceeds the tolerance (1W <= 0.5%p, 1M <= 3%p, 3M <= 7%p), the response **shall** carry `benchmark_reconciliation_warning` with the measured difference (불변식 BM-3).

- 검증: AC-SAG-015 (불변식 **BM-3**)

#### REQ-SAG-014 (Unwanted Behavior) — 조용한 0.0 금지

The benchmark loader **shall not** return `0.0` when benchmark data is unavailable. It **shall** set `benchmark_return = null`, `benchmark_status = "unavailable"`, `benchmark_error = <사유>`, `excess_return = null`, `composite_score = null` (규칙 BM-4, BM-5).

- 검증: AC-SAG-016

### 3.3 순위·정규화

#### REQ-SAG-015 (Ubiquitous) — 순위 백분위 정규화

Normalization **shall** be `norm(v) = (rank_ascending(v) − 1)/(N − 1) × 100` with ties assigned the average rank; `N == 1` → 50.0; `N == 0` → 빈 결과. min-max 정규화를 폐기한다 (규칙 AG-8).

- 검증: AC-SAG-017

#### REQ-SAG-016 (Ubiquitous) — composite_score

`composite_score = 0.30×norm(excess_1w) + 0.40×norm(excess_1m) + 0.30×norm(excess_3m)`. 어느 기간이라도 `null`이면 composite는 `null`이며 순위 대상에서 제외한다(부분 점수 금지) (규칙 AG-9).

- 검증: AC-SAG-018

#### REQ-SAG-017 (Ubiquitous) — 결정적 tie-break

The ranking sort key **shall** be `(−composite_score_unrounded, sector_name)`. 레지스트리 삽입 순서 의존을 금지한다 (불변식 RK-1).

- 검증: AC-SAG-019 (불변식 **RK-1**)

#### REQ-SAG-018 (Ubiquitous) — 반올림 시점

Rounding **shall** occur exactly once, immediately before response serialization. 정렬·순위 비교·현재/과거 composite 대조는 모두 반올림 전 값으로 수행한다 (불변식 RK-2, 규칙 AG-10).

- 검증: AC-SAG-020 (불변식 **RK-2**)

#### REQ-SAG-019 (Ubiquitous) — rank = f(period, market)

`GET /sectors/ranking` **shall** accept `period` (`1w|1m|3m`) and `market` (`all|kospi|kosdaq`) and **shall** return `rank` computed for that (period, market) pair, so that ascending `rank` order and the returned row order agree (규칙 CT-4).

- 검증: AC-SAG-021

#### REQ-SAG-020 (Ubiquitous) — composite는 별도 열로 보존

The ranking response **shall** additionally return `composite_score` and `composite_rank` as independent fields, so the multi-period view survives the period-scoped ranking (규칙 CT-5).

- 검증: AC-SAG-022

#### REQ-SAG-021 (Ubiquitous) — rank_change 기준일

`rank_change = rank(baseline_date) − rank(as_of_date)` where `baseline_date = anchor(as_of_date, 28)` from SPEC-SECTOR-GRID-001. The response **shall** include `baseline_date`. 비교 기준일이 없거나 당시 순위 대상이 아니었으면 `rank_change = null`(0 아님) (§2.10).

- 검증: AC-SAG-023

### 3.4 지표 정정

#### REQ-SAG-022 (Ubiquitous) — 52주 신고가 판정

`nh_pct` **shall** be `count(Close >= high_52w × 0.98) / n_valid × 100` where `high_52w = MAX(High)` over the 364-day window. 저장된 `MAX52`(Close 기반)를 판정에 사용하지 않는다. 52주 최고가 산출 불가 종목은 분모에서 제외한다 (§2.5).

- 검증: AC-SAG-024

#### REQ-SAG-023 (Ubiquitous) — Stage 분류기 단일화

Stage classification **shall** use `my_chart/analysis/stage_classifier.py:classify_stage` (주봉) exclusively. `backend/services/sector_detail_service.py:23-47`의 일봉 근사 분류기를 **폐기(코드 삭제)** 한다. `SMA40` 또는 `SMA10`이 NULL인 종목은 **분류 불가**로 분모에서 제외한다 (§2.6).

- 검증: AC-SAG-025, AC-SAG-026

#### REQ-SAG-024 (Ubiquitous) — Stage 합계 항등식

`stage1_count + stage2_count + stage3_count + stage4_count + unclassified_count == total_count` **shall** hold for every stage distribution response, including the `by_sector` entries. 분류 불가를 Stage 1에 흡수시키는 것을 금지한다 (§8.6).

- 검증: AC-SAG-027 (불변식 **§8.6**)

#### REQ-SAG-025 (Ubiquitous) — volume_ratio

`volume_ratio = Volume / VolumeSMA10` using the weekly `VolumeSMA10` column. `VolumeSMA10`이 NULL이거나 0이면 `null`(1.0 치환 금지). 가격 이동평균을 거래량 기준선으로 쓰는 현행 동작을 폐기한다 (§2.8).

- 검증: AC-SAG-028

#### REQ-SAG-026 (Ubiquitous) — 거래대금

`trading_value` **shall** be sourced from daily `stock_prices.VolumeWon`. `Close × Volume` 재계산을 금지한다 (§2.7).

**O-A4 결정 (2026-08-12) — 집계 창 = 기간 토글 연동**: `trading_value(period) = Σ VolumeWon over [anchor(t, N), t]` where N = 1W→7일 / 1M→28일 / 3M→91일 (①의 `anchor()` 사용). 근거: 버블의 X축(기간 수익률)과 크기 채널(거래대금)이 **같은 창을 서술**해야 사용자가 두 채널을 함께 읽을 수 있다. 응답에 `trading_value_window_days`를 동반해 ③의 크기 범례가 어느 기간의 값인지 표기할 수 있게 한다(③ REQ-SUX-037).

- 검증: AC-SAG-029

#### REQ-SAG-027 (Ubiquitous) — RS 계열 지표 (등가중 유지)

`rs_avg = Σ RSᵢ / n_valid` (등가중). RS 행이 없는 종목은 분자·분모 모두에서 제외한다. `rs_coverage = n_valid / member_count`를 동반한다 (§2.3, 01 O-7 결정).

`rs_top_pct = count(RS >= 80) / n_valid × 100` — **분모는 `member_count`가 아니라 `n_valid`**(RS 값이 존재하는 종목 수)이며, 임계값 80은 고정 상수로 단일 위치에 정의하고 응답에 `rs_top_threshold: 80`으로 실어 UI가 명시할 수 있게 한다 (§2.4).

- 검증: AC-SAG-030

### 3.5 RRG

#### REQ-SAG-028 (Ubiquitous) — RS-Ratio의 100은 벤치마크

RS-Ratio **shall** be `RS_Ratio(t) = sector_index(t) / benchmark_index(t) × 100`, emitted **without any rolling normalization**, and the value 100 **shall** mean "벤치마크 대비 동일 성과". 횡단면 z-score 기반 산출을 폐기한다 (불변식 RRG-1).

**O-A1 결정 (2026-08-12) — 롤링 정규화 미적용**:

- 자기 시계열 롤링 정규화를 적용하면 중심 100이 "그 섹터 자신의 과거 평균"이 되어 다시 벤치마크가 아니게 된다. 표준 JdK RRG가 바로 그 방식이며, **본 프로젝트는 이를 채택하지 않는다.**
- **표준 JdK RRG와의 발산을 명시한다** — 값이 상용 RRG 도구(StockCharts 등)와 직접 비교 불가함을 응답 `warnings[]` 또는 범례 문구(③ REQ-SUX-042)로 전달한다.
- **강세장에서 다수 섹터가 Leading 사분면에 몰리는 것은 올바른 동작이다.** 100이 진짜 벤치마크이므로 시장 폭이 넓은 국면에서는 대부분 섹터가 벤치마크를 상회한다. **사분면 균등 분포를 요구하는 테스트를 두어서는 안 된다** — AC-SAG-045 R7이 이를 명시적으로 고정한다.
- 섹터별 스케일 차이는 감수하며, ③의 RRG 축 자동 대칭(VZ-8)이 흡수한다.

- 검증: AC-SAG-031 (불변식 **RRG-1**), AC-SAG-045 R7

#### REQ-SAG-029 (Ubiquitous) — 워밍업 미발행

The RRG response **shall not** emit points for the rolling warm-up window; those dates are absent from `trail[]`. 상수 100.0 패딩과 그 구간의 차분을 금지한다. `trail_start_date`와 `lookback_weeks`를 응답에 포함한다 (불변식 RRG-2).

- 검증: AC-SAG-032 (불변식 **RRG-2**)

#### REQ-SAG-030 (Ubiquitous) — 지수는 수익률 연쇄

Sector and benchmark indices **shall** be constructed as chained returns (`I(t) = I(t−1) × (1 + r(t))`), not as per-date recomputation of `Σ(close×cap)/Σcap` (불변식 RRG-3).

- 검증: AC-SAG-033 (불변식 **RRG-3**)

#### REQ-SAG-031 (Unwanted Behavior) — look-ahead 시총 금지

The index construction **shall not** apply the current `stock_meta` market-cap snapshot to past dates. 시점별 시총은 `주식수 = 현재시총 / 현재주가`로 상수 주식수를 역산한 뒤 `과거시총 = 주식수 × 과거주가`로 산출한다 (불변식 RRG-4, 고정 결정).

**O-A3 결정 (2026-08-12)**:

- **"현재주가"의 출처는 daily DB의 최신 `Close`로 고정한다.** `market_cap`이 `stock_meta`(daily)에서 오므로 `주식수 = market_cap / Close` 역산의 분자·분모가 같은 원천이어야 한다. 주봉 최신 `Close`를 쓰면 두 원천의 기준일이 어긋나 주식수가 체계적으로 틀어진다. 이 단일 지점을 코드에서 상수로 명시한다.
- **상수 주식수 가정의 한계를 응답 `warnings[]`에 상설 명시한다** — 유상증자·무상증자·액면분할·자사주 소각이 조회 구간에 있으면 과거 시총이 틀린다.
- **이벤트 감지(주가 급변 + 시총 불연속 탐지)는 구현하지 않는다 — 과설계.** 한계를 고지하는 것으로 갈음한다.

- 검증: AC-SAG-034 (불변식 **RRG-4**)

#### REQ-SAG-032 (Ubiquitous) — RRG 결측 처리

Where RS-Ratio or RS-Momentum cannot be computed, the response **shall** omit the point (100 대체 금지) and record the sector in `excluded[]` with the reason (§8.3).

- 검증: AC-SAG-035

### 3.6 응답 계약·API

#### REQ-SAG-033 (Ubiquitous) — 응답 공통 스키마

Every sector-related endpoint response **shall** include: `as_of_date`, `as_of_is_partial_week`, `market_filter`, `weight_cap`, `grid_version`, `benchmark{name, return_*, status, reconciliation_diff_pp}`, `data[]`, `excluded[]`, `warnings[]` (§9.3).

- 검증: AC-SAG-036

#### REQ-SAG-034 (Ubiquitous) — 전 엔드포인트 as_of_date 일치

For a given filter condition, all sector endpoints **shall** return the same `as_of_date` (불변식 SN-3).

- 검증: AC-SAG-037 (불변식 **SN-3**)

#### REQ-SAG-035 (Ubiquitous) — 결측 3상태 구분

Every metric field **shall** distinguish `null + reason:"missing"` / actual `0.0` / `null + reason:"insufficient"`, and additionally carry `low_confidence` and `warnings[]` where applicable (§9.1). 결측을 0 / 0.0% / 50.0으로 표현하는 것을 금지한다 (§9.2).

- 검증: AC-SAG-038

#### REQ-SAG-036 (Ubiquitous) — market 파라미터 전면 신설

The following endpoints **shall** accept a `market` query parameter (`all|kospi|kosdaq`, default `all`) applied as an aggregation-time filter: `/sectors/ranking`, `/sectors/rrg`, `/sectors/history`, `/sectors/{name}/bubble`, `/sectors/{name}/detail`, `/stage/overview` (§12.3, 규칙 UN-7).

- 검증: AC-SAG-039

#### REQ-SAG-037 (Ubiquitous) — period 파라미터

`/sectors/ranking` and `/sectors/{name}/detail` **shall** accept `period` (`1w|1m|3m`, default `1m`).

- 검증: AC-SAG-021, AC-SAG-039

#### REQ-SAG-038 (Ubiquitous) — Bump 히스토리 응답

`/sectors/history` **shall** return `dates[]`, `rankings[date][sector]`, `weeks`, `span_days`, and **shall not** substitute a bottom rank for a sector absent from ranking on a given date (선 끊김을 위해 `null` 유지) (§8.4).

- 검증: AC-SAG-040

#### REQ-SAG-039 (Ubiquitous) — 종목 목록 필드

The stock-listing response (`/stage/overview`, 종목 버블) **shall** include `weight_in_sector`, `sector_minor`, `stage`, `stage_detail`, `rs_12m`, `chg_1w/1m/3m`, `trading_value`, `volume_ratio`, `near_52w_high`, and the sector-scope aggregate `sector_aggregate` (§8.5, §8.7).

- 검증: AC-SAG-041, AC-SAG-042

#### REQ-SAG-040 (Ubiquitous) — 신규 필드의 전 구간 전파 [Lesson #4]

Every field added by this SPEC **shall** be propagated end-to-end: 집계 dataclass → 서비스 변환 → Pydantic 응답 모델 → JSON. 파생 구조(예: 상세용 축약 리스트, `by_sector` 엔트리)에도 동일 필드가 존재해야 한다.

- 검증: AC-SAG-043

#### REQ-SAG-041 (Ubiquitous) — 의미 테스트로의 대체 [테스트 1급 산출물]

`tests/test_sector_metrics.py`의 `hasattr`-only 검증(현행 `:195-215`)은 **값 단언 테스트로 대체**되어야 하며, 가중 방식·정규화 방식·벤치마크 방법론을 되돌리면 **테스트가 실패**해야 한다.

- 검증: AC-SAG-044

#### REQ-SAG-042 (Ubiquitous) — 회귀 방지: 기대되는 변화의 명문화

The regression suite **shall** assert the 8 behavior changes in `02-screen-flow.md` §12.2 as **expected**, not as defects.

- 검증: AC-SAG-045

---

## 4. Exclusions (What NOT to Build)

### Out of Scope — 기반 계층

- 정규 주간 격자 산출, 진행 중 주 판정, 유효 유니버스, stale 배제, registry dedup, weekly INSERT 마이그레이션: 전부 **① SPEC-SECTOR-GRID-001** 소관. ②는 소비만 한다.
- 과거 오염 행 처리·적재 경로 변경: ① 소관.

### Out of Scope — 화면·상태

- `AnalysisParamsContext` / `SelectionContext` / `NavIntent`, 토글 단일화, 전환 규칙, 버블 크기 매핑, 축·범례·대비, 로딩/빈 상태 UX: 전부 **③ SPEC-SECTOR-UX-001** 소관.
- 본 SPEC은 응답 필드를 **추가**할 뿐 렌더링을 규정하지 않는다.

### Out of Scope — 기능 확장

- 관심 섹터 워치리스트 / 핀 / 즐겨찾기: 범위 밖.
- 산업명(중) 161개 단위 집계(중분류 순위·RRG): §7 O-A2 미결. 본 SPEC은 종목 필드로 `sector_minor`를 노출할 뿐 중분류 집계를 만들지 않는다.
- 지수 레벨·지수 High/Low의 화면 노출: **금지**(01 O-4 결정 — 일봉 DB에 지수가 없어 교차검증 불가).
- 가중 방식 토글(등가중/시총가중 선택 UI): 도입하지 않는다. `weight_cap`은 서버 상수.
- 사전 배치 계산 테이블·외부 캐시(Redis 등): 도입하지 않는다(A2, A3).
- 신규 엔드포인트 추가: 없음. 기존 엔드포인트의 파라미터·응답 확장만.

---

## 5. Specifications (수용 기준 연결)

상세 시나리오는 `acceptance.md`, 작업 분해·리스크는 `plan.md` 참조.

### Traceability (REQ ↔ AC ↔ 불변식)

| REQ | AC | 01 부록B 불변식 |
| --- | --- | --- |
| REQ-SAG-001 | AC-SAG-001, 002 | — |
| REQ-SAG-002 | AC-SAG-003 | — |
| REQ-SAG-003 | AC-SAG-004 | — |
| REQ-SAG-004 | AC-SAG-005 | — |
| REQ-SAG-005 | AC-SAG-006 | — |
| REQ-SAG-006 | AC-SAG-007 | — |
| REQ-SAG-007 | AC-SAG-008 | **AG-6** |
| REQ-SAG-008 | AC-SAG-009 | — |
| REQ-SAG-009 | AC-SAG-010 | — |
| REQ-SAG-010 | AC-SAG-011 | — |
| REQ-SAG-011 | AC-SAG-012, 013 | **EX-1**, **EX-2** |
| REQ-SAG-012 | AC-SAG-014 | **BM-6** |
| REQ-SAG-013 | AC-SAG-015 | **BM-3** |
| REQ-SAG-014 | AC-SAG-016 | — |
| REQ-SAG-015 | AC-SAG-017 | — |
| REQ-SAG-016 | AC-SAG-018 | — |
| REQ-SAG-017 | AC-SAG-019 | **RK-1** |
| REQ-SAG-018 | AC-SAG-020 | **RK-2** |
| REQ-SAG-019 | AC-SAG-021 | — |
| REQ-SAG-020 | AC-SAG-022 | — |
| REQ-SAG-021 | AC-SAG-023 | — |
| REQ-SAG-022 | AC-SAG-024 | — |
| REQ-SAG-023 | AC-SAG-025, 026 | — |
| REQ-SAG-024 | AC-SAG-027 | **§8.6** |
| REQ-SAG-025 | AC-SAG-028 | — |
| REQ-SAG-026 | AC-SAG-029 | — |
| REQ-SAG-027 | AC-SAG-030 | — |
| REQ-SAG-028 | AC-SAG-031 | **RRG-1** |
| REQ-SAG-029 | AC-SAG-032 | **RRG-2** |
| REQ-SAG-030 | AC-SAG-033 | **RRG-3** |
| REQ-SAG-031 | AC-SAG-034 | **RRG-4** |
| REQ-SAG-032 | AC-SAG-035 | — |
| REQ-SAG-033 | AC-SAG-036 | — |
| REQ-SAG-034 | AC-SAG-037 | **SN-3** |
| REQ-SAG-035 | AC-SAG-038 | — |
| REQ-SAG-036 | AC-SAG-039 | — |
| REQ-SAG-037 | AC-SAG-021, 039 | — |
| REQ-SAG-038 | AC-SAG-040 | — |
| REQ-SAG-039 | AC-SAG-041, 042 | — |
| REQ-SAG-040 | AC-SAG-043 | — |
| REQ-SAG-041 | AC-SAG-044 | — |
| REQ-SAG-042 | AC-SAG-045 | — |

**본 SPEC이 책임지는 01 부록 B 불변식: EX-1, EX-2, RK-1, RK-2, RRG-1, RRG-2, RRG-3, RRG-4, BM-3, BM-6, SN-3, AG-6, §8.6 (13개)**

---

## 6. 의존 관계

- **선행**: `SPEC-SECTOR-GRID-001` close 필요 (격자·유니버스·`anchor()`·`as_of_date`).
- **후행**: `SPEC-SECTOR-UX-001`이 본 SPEC의 응답 필드를 소비한다. 단 ②는 추가 전용 스키마라 ③ 없이도 독립 close 가능하다(A7).

---

## 7. 미결 사항 (SPEC 레벨 open questions)

| ID | 사항 | 출처 | 결정 필요 사항 |
| --- | --- | --- | --- |
| ~~**O-A1**~~ **해결됨** | RS-Ratio 롤링 정규화와 "100 = 벤치마크"의 정합 | 신규 (설계서 내부 모순) | **결정 (2026-08-12): 선택지 (a) — 롤링 정규화를 하지 않는다.** `RS_Ratio(t) = sector_index(t) / benchmark_index(t) × 100`을 그대로 발행하며, 100은 문자 그대로 벤치마크다. 상세는 §3.5 REQ-SAG-028 및 `01 §2.11` 개정본. |
| **O-A2** | 산업명(중) 161개의 중분류 단위 집계 제공 여부 | 01 §10 O-6 = 02 §13 O-7 | 중분류 단위 순위·RRG를 제공할 것인가. 161개 중 상당수가 §5.4 최소 구성수 5에 걸릴 가능성이 크다. 제공 시 서브탭이 늘어 "현행 IA 유지" 제약과 충돌한다. |
| ~~**O-A3**~~ **해결됨** | RRG 시점별 시총 역산의 한계 | 신규 (고정 결정의 미규정 부분) | **결정 (2026-08-12): (a) `warnings[]` 명시 채택. (b) 이벤트 감지는 구현하지 않는다 — 과설계.** 상장주식수 상수 가정의 한계(유·무상증자·액면분할·자사주 소각)를 RRG 응답 `warnings[]`에 상설 기재한다. **"현재주가" 출처 = daily DB 최신 `Close`** — `market_cap`이 `stock_meta`(daily)에서 오므로 주식수 역산의 분모·분자가 같은 원천이어야 정합적이다. 검증: AC-SAG-034. |
| ~~**O-A4**~~ **해결됨** | 거래대금의 기간 정의 | 신규 (설계서 미규정) | **결정 (2026-08-12): 기간 토글과 동일한 창을 합산한다.** `trading_value(period) = Σ VolumeWon over [anchor(t, N), t]`, N = 1W→7일 / 1M→28일 / 3M→91일 (①의 `anchor()` 사용). 근거: 버블의 X축(기간 수익률)과 크기 채널(거래대금)이 **같은 창을 서술**해야 두 채널을 함께 읽을 수 있다. 검증: AC-SAG-029. `01 §2.7` · `§10 O-10` 개정 반영. |
| **O-A8** | 미완성 주 바와 기간 계산의 정합 (①에서 이관) | ①의 §7 O-G2 | **①이 등록했으나 "집계 의미는 ② 소관"으로 제외한 항목이며, ②가 인수한다.** `as_of_date`가 진행 중인 주(화요일)일 때 `latest_snapshot`(미완성 포함)과 `history_grid`(미완성 제외)가 **서로 다른 날짜**를 가리킨다. 이때 1W 수익률의 날짜 쌍을 무엇으로 잡을 것인가: (a) `as_of = latest_snapshot`, `anchor = history_grid`에서 `t−7d` 이하 → 창이 7일이 아닐 수 있다, (b) 수익률은 전부 `history_grid`만 사용하고 `latest_snapshot`은 표기 전용으로 둔다, (c) 두 값을 병기한다. **REQ-SAG-012(동일 날짜 창)와 REQ-SAG-021(`anchor(t,28)`)이 이 결정에 직접 의존한다** — 미결이면 BM-6이 무증상으로 깨질 수 있다(양쪽이 각자 다른 뷰를 쓰면서 응답에는 둘 다 실려 겉보기 일치). **M3 착수 전 결정 필수.** 검증: AC-SAG-014. |
| **O-A5** | 3M 벤치마크 정합성 이탈 (KOSDAQ 6.27%p) | 01 §10 O-5 | 격자 정규화(① ship) 후 재측정해 원인이 격자 오염인지 구성종목 변동인지 판별한다. 허용오차 **7%p는 잠정치**이며 재측정 후 조정이 필요하다. AC-SAG-015는 임계값을 상수로 분리해 조정 가능하게 둔다. |
| ~~**O-A6**~~ **해결됨** | `coverage_ratio`의 입도 | 신규 (설계서 미규정) | **결정 (2026-08-12): 지표별 + 최상위 최소값 병행.** `coverage: {rs, nh, stage, chg, trading_value}` 객체를 싣고, **동시에** 최상위 `coverage_ratio = min(그 값들)`을 유지해 기존 단일 필드 소비자(§8.1 저신뢰 판정, AG-7 임계, ③의 `⚠` 배지)를 깨지 않는다. AG-7의 0.80/0.50 임계는 **최상위 최소값**에 적용한다. 검증: AC-SAG-008. `01 §10 O-11` 개정 반영. |
| **O-A7** | 최소 구성수 5 규칙의 Bump 적용 여부 | 신규 | 01 §5.4 AG-5는 "순위·버블·RRG 대상에서 제외"라 하고 Bump를 언급하지 않는다. Bump는 순위의 시계열이므로 자동 적용되는 것으로 보이나, 특정 주에만 5 미만이 되는 섹터의 선 처리(끊김)와의 관계가 명시되지 않았다. **③의 AC-SUX-019(제외 섹터 가시성)와 AC-SUX-056 R5(KOSPI 필터 시 제외 영역 등장)가 이 항목에 의존한다** — ③은 "AG-5가 Bump에도 적용된다"를 전제로 작성되어 있으나 그것이 바로 여기서 미결이다. 결정 시 ③의 두 AC에 반영해야 한다. **③ 착수 전 해소 필요.** |
