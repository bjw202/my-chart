# SPEC-SECTOR-AGGREGATION-001 Acceptance — 수용 기준

> `development_mode: tdd`. 모든 AC는 **실행 가능한 검사**로 기술한다.
> 현행 `tests/test_sector_metrics.py:195-215`는 `hasattr` 8회만 호출해 가중 방식을 바꿔도 실패하지 않는다. 아래 AC는 **되돌리면 반드시 실패하는** 형태로 작성한다.

---

## 1. 가중·집계

### AC-SAG-001 — 시총가중 + 상한 재배분 (규칙 AG-1)

- **Given** 시총이 `[70, 10, 10, 5, 5]`(합 100)인 5종목 섹터 픽스처에서
- **When** `compute_weights(caps, cap=0.10)`을 호출하면
- **Then** `cap_eff == max(0.10, 1/5) == 0.20`이고, 결과 가중치의 최대값이 `0.20` 이하이며 `abs(Σw − 1.0) < 1e-9`이다.
- **And** 상한 초과분은 **나머지 종목의 현재 비중에 비례**해 배분된다(균등 배분이 아님) — `w[1]/w[2] == 1.0`, `w[1]/w[3] == 2.0`.
- **And** 반복 횟수가 5회 이하로 수렴한다.
- **And** 상한이 구속하지 않는 균등 시총 픽스처에서는 결과가 등가중과 일치한다.

### AC-SAG-002 — 시총가중 실측 회귀 (되돌리면 실패)

- **Given** 라이브 DB 기준일에서
- **When** 1M 섹터 수익률을 산출하면
- **Then** 반도체가 **음수**이고 헬스케어가 **양수**이며, 반도체 순위 > 헬스케어 순위(숫자가 큼 = 하위)이다.
- **And** 등가중으로 되돌리면 이 단언이 실패한다(테스트 docstring에 명시).
- **참조 실측**: 헬스케어 등가중 +9.23% → 시총가중 +17.07%, 반도체 +2.49% → −6.59%.

### AC-SAG-003 — 상한 적용 사실의 노출 (규칙 AG-2)

- **Given** 반도체 섹터(삼성전자 원비중 55.1%)에서
- **When** 상세 응답을 조회하면
- **Then** `weight_cap == 0.10`이고 `capped_members[]`에 `{name:"삼성전자", raw_weight:~0.551, capped_weight:0.10}` 형태 항목이 존재한다.
- **And** `capped_members[]`의 모든 항목의 `capped_weight == cap_eff`이다.

### AC-SAG-004 — 결측 종목 완전 제외 (분모 규칙)

- **Given** 10종목 중 3종목의 `CHG_1M`이 NULL인 픽스처에서
- **When** 1M 섹터 수익률을 산출하면
- **Then** 결과가 "NULL을 0으로 치환한 값"과 **다르다**(구체적 기대값 단언).
- **And** `valid_count == 7`, `member_count == 10`, `coverage_ratio == 0.7`.
- **And** 남은 7종목의 가중치가 재정규화되어 `Σw == 1.0`이다.

### AC-SAG-005 — NULL market_cap 처리 (규칙 UN-6/AG-3)

- **Given** 20종목 중 3종목의 `market_cap`이 NULL 또는 0인 픽스처에서
- **When** 집계하면
- **Then** 시총가중 수익률 계산에 그 3종목이 **포함되지 않는다**.
- **And** `rs_avg` / `stage2_pct` / `nh_pct` / `member_count`에는 **포함된다**(등가중 지표).
- **And** `cap_coverage_ratio == 유효시총합 / 전체시총합`이 응답에 존재한다.
- **And** 대체값(1.0 / 중앙값) 부여 흔적이 없다 — 3종목을 제거한 픽스처와 시총가중 결과가 **일치**한다.

### AC-SAG-006 — 유효 시총 종목 부족 (규칙 AG-4)

- **Given** 유효 시총 종목이 3개(최소 5 미만)인 섹터에서
- **When** 집계하면
- **Then** 시총가중 필드는 `null` + `reason:"insufficient"`이고, 등가중 필드(`rs_avg` 등)는 값을 갖는다.
- **And** 응답에 방법론 차이 플래그(`cap_weighted_available: false`)가 존재한다.

### AC-SAG-007 — 최소 구성종목 수 (규칙 AG-5)

- **Given** `market=kospi` 필터에서 디스플레이(4종목)·스마트폰(4종목)일 때
- **When** `/sectors/ranking?market=kospi`를 호출하면
- **Then** 두 섹터가 `data[]`에 없고 `excluded[]`에 `{sector, reason:"insufficient_members", count:4}`로 존재한다.
- **And** PCB(5종목)·게임(6종목)은 `data[]`에 **포함**된다(경계 `>= 5` 포함).
- **And** `market=all`에서는 두 섹터가 `data[]`에 포함된다.

### AC-SAG-008 — 커버리지 필드 동반 (불변식 **AG-6**)

- **When** 모든 섹터 집계 엔드포인트를 호출하면
- **Then** `data[]`의 **모든** 항목이 `member_count`, `valid_count`, `coverage_ratio`, `cap_coverage_ratio` 4개 필드를 갖는다(누락 0건).
- **현재 상태**: 실패 (필드 없음)

### AC-SAG-009 — 커버리지 하한 (규칙 AG-7)

- **Given** `coverage_ratio`가 각각 0.95 / 0.75 / 0.45인 3개 섹터 픽스처에서
- **Then** 0.95 → 값 + `low_confidence` 없음, 0.75 → 값 + `low_confidence: true`, 0.45 → `null` + `reason:"insufficient"`.
- **And** 경계 0.80 정확히 → `low_confidence` 없음. 0.50 정확히 → 값 유지(`< 0.50`만 null).

### AC-SAG-010 — 유효 종목수 `effective_n`

- **Given** 반도체 섹터(상한 10%)에서
- **When** 상세를 조회하면
- **Then** `effective_n == 1/Σwᵢ²`이고, 상한 없는 경우(2.2)보다 **크다**(실측 24.3 근방, 오차 ±1.0).

---

## 2. 벤치마크

### AC-SAG-011 — 시장별 벤치마크 전환 (규칙 BM-1)

- **When** `market=all|kospi|kosdaq`로 각각 조회하면
- **Then** `benchmark.name`이 각각 `ALL_CAPPED` / `KOSPI_CAPPED` / `KOSDAQ_CAPPED`이고 세 값이 서로 **다르다**.
- **And** 실측 근사 확인(±0.5%p): 1W KOSPI +1.03%, KOSDAQ +7.54%, All +1.88%. **이 세 값은 라이브 실측이므로 §8 프로즌 픽스처 위에서만 게이팅한다** — 라이브 DB 실행은 비게이팅 스모크다.
- **And** 세 이름이 서로 다르다는 단언은 값과 무관하므로 스냅샷 갱신에 영향받지 않는다(값 단언만 프로즌 대상).

### AC-SAG-012 — 방법론 일치 (불변식 **EX-1**)

- **Given** 동일 필터 조건에서
- **When** 섹터 집계와 벤치마크 집계의 (유니버스 크기, `weight_cap`, 격자 날짜 쌍, 결측 처리 규칙)을 각각 수집하면
- **Then** 네 항목이 **모두 동일**하다(구조적 단언 — 벤치마크가 섹터와 같은 함수를 호출함을 mock 호출 인자 비교로 검증).
- **현재 상태**: 실패

### AC-SAG-013 — 초과수익률 부호 분산 (불변식 **EX-2**)

- **Given** 단일 시장·단일 기간 기준으로
- **When** 전 섹터의 초과수익률을 수집하면
- **Then** 부호가 **모두 같지 않다**(양수 섹터 수가 `0 < k < N`).
- **And** 모두 같은 부호이면 `warnings[]`에 벤치마크 정합성 경고가 기록된다.
- **And** 라이브 회귀: 1W 양수 섹터 수가 29가 아니라 **18 ± 3** 범위다.
- **현재 상태**: 실패 (1W 29/29 양수)

### AC-SAG-014 — 동일 날짜 창 (불변식 **BM-6**)

- **When** 임의 기간·시장으로 조회하면
- **Then** 응답에 `as_of_date`와 `benchmark.anchor_date`가 모두 존재하고, 섹터 수익률 계산에 쓰인 앵커 날짜와 벤치마크 앵커 날짜가 **문자열 동등**하다.
- **현재 상태**: 미검증

### AC-SAG-015 — 지수 행 정합성 경고 (불변식 **BM-3**)

- **Given** 허용오차 상수 `{1w: 0.5, 1m: 3.0, 3m: 7.0}` (%p, 단일 위치 정의)
- **When** 상한 없는 순수 시총가중 집계와 지수 행 수익률의 차를 계산하면
- **Then** 초과 시 `benchmark_reconciliation_warning`에 `{period, market, diff_pp}`가 실린다.
- **And** 1W KOSPI/KOSDAQ는 경고 없이 통과한다(실측 −0.10%p / −0.15%p).
- **And** 임계값은 상수로 분리되어 O-A5 재측정 후 조정 가능하다.

### AC-SAG-016 — 벤치마크 부재 시 명시적 오류 (규칙 BM-4/BM-5)

- **Given** 벤치마크 산출이 불가능한 픽스처(구성종목 0 / 지수 행 없음)에서
- **When** 조회하면
- **Then** `benchmark.status == "unavailable"`, `benchmark.return_* is None`, `benchmark_error`가 비어 있지 않다.
- **And** 모든 섹터의 `excess_return is None`, `composite_score is None`이며 `rank is None`이다.
- **And** `sector_return`(원수익률)은 **값을 유지**한다.
- **And** `0.0`이 반환되지 않는다 — `assert benchmark.return_1w is None` **단독**으로 단언한다.

> **이전 판의 결함 제거**: 이전 판은 `assert benchmark.return_1w is not 0.0`을 함께 요구했다. 이는 **float 객체 아이덴티티 비교**로, CPython에서 `0.0`은 인터닝되지 않으므로 값이 실제로 `0.0`이어도 거의 항상 참이 된다 — 즉 **결함을 잡지 못하면서 통과한다.** 게다가 Python 3.8+에서 `SyntaxWarning: "is not" with a literal`을 발생시킨다. `is None` 단언 하나로 의도가 완전히 표현되므로 **삭제**한다.
- **And** **정적 스캔**: 테스트 스위트 전체에서 리터럴 대상 `is` / `is not` 사용이 0건이다 — `grep -rnE "\bis (not )?[0-9]" tests/` → 0행. 동일 안티패턴의 재도입을 막는다.

---

## 3. 순위·정규화

### AC-SAG-017 — 순위 백분위 정규화 (규칙 AG-8)

- **Given** 값 배열 `[1, 2, 3, 1000]`에서
- **When** `norm()`을 적용하면
- **Then** 결과가 `[0, 33.33, 66.67, 100]` 근방이다 — **극단값 1000이 스케일을 지배하지 않는다**(min-max였다면 `[0, 0.1, 0.2, 100]`).
- **And** 동일 값 `[5, 5, 5]` → 세 값 모두 평균 순위 기반 동일 값.
- **And** `N == 1` → `50.0`. `N == 0` → 빈 결과(예외 없음, 50.0 반환 금지).
- **And** `max == min`인 배열에서 전 섹터가 50.0으로 붕괴하지 않는다.

### AC-SAG-018 — composite_score (규칙 AG-9)

- **Given** `norm(excess_1w)=100, norm(excess_1m)=50, norm(excess_3m)=0`인 섹터에서
- **Then** `composite_score == 0.30×100 + 0.40×50 + 0.30×0 == 50.0`.
- **And** `excess_3m`이 `null`인 섹터는 `composite_score is None`이고 `rank is None`이며 `excluded[]`에 등록된다(부분 점수 산출 금지).

### AC-SAG-019 — 결정적 tie-break (불변식 **RK-1**)

- **Given** composite가 완전히 동일한 3섹터(`가나다`, `나다라`, `다라마`) 픽스처에서
- **When** 순위를 **입력 순서를 바꿔 가며 3회** 산출하면
- **Then** 세 결과의 `rank` 배정이 **동일**하고, 섹터명 사전순으로 정렬된다.
- **현재 상태**: 실패

### AC-SAG-020 — 반올림 대칭 (불변식 **RK-2**)

- **Given** composite가 `86.234`와 `86.236`인 두 섹터에서
- **When** 현재/과거 순위를 산출하면
- **Then** 두 순위가 **다르고**(반올림했다면 동점), `rank_change`에 허수 ±1이 발생하지 않는다.
- **And** 반올림은 직렬화 직전 1회만 수행됨을 코드 경로로 확인(정렬 함수 내부에 `round(` 호출 0건 — 정적 스캔).
- **현재 상태**: 실패

### AC-SAG-021 — rank = f(period, market) (규칙 CT-4)

- **When** `/sectors/ranking?period=1w&market=all`을 호출하면
- **Then** `data[]`의 `rank` 값이 `1, 2, 3, ...` 연속이고, `data[]` 배열 순서와 `rank` 오름차순이 **일치**한다.
- **And** `period=3m`으로 바꾸면 `rank` 배정이 **달라진다**(동일하면 파라미터 미반영).
- **And** `market=kospi`로 바꾸면 제외 섹터가 생겨 `rank` 최대값이 줄어든다.
- **And** `rank`는 해당 (period, market)의 초과수익률 기준이며, 순위 대상 제외 섹터는 `rank is None`이다.

### AC-SAG-022 — composite 별도 열 (규칙 CT-5)

- **When** `/sectors/ranking?period=1w`을 호출하면
- **Then** `composite_score`와 `composite_rank`가 함께 반환되고, `composite_rank`는 `period`와 무관하게 **동일**하다(1w/1m/3m 3회 호출 결과 비교).

### AC-SAG-023 — rank_change 기준일 (§2.10)

- **When** 순위 응답을 조회하면
- **Then** `baseline_date`가 존재하고 `(as_of_date − baseline_date).days >= 28`이다.
- **And** `baseline_date`가 현행 `LIMIT 1 OFFSET 3` 결과(11일 전)와 **다르다**.
- **And** 기준일에 순위 대상이 아니었던 섹터는 `rank_change is None`(0이 아님)이다.
- **And** `rank_change == 0`인 섹터와 `rank_change is None`인 섹터가 응답에서 구분된다.

---

## 4. 지표 정정

### AC-SAG-024 — 52주 신고가 판정 (§2.5)

- **Given** 종가 98, 52주 `MAX(High)` 100, 저장된 `MAX52`(Close 기반) 92인 종목에서
- **When** `near_52w_high`를 판정하면
- **Then** `98 >= 100×0.98` → **True**이며, `MAX52` 기준(`98 >= 92×0.98` → True)과 구분되는 케이스(종가 95)에서 신 판정은 **False**, 구 판정은 True로 갈린다.
- **And** 52주 최고가 산출 불가 종목(상장 1년 미만)은 분모에서 제외된다.
- **And** 라이브 회귀: 신고가 종목 수가 99가 아니라 **56 ± 8**이다.
- **And** `MAX52` NULL 48행이 분모에 남지 않는다.

### AC-SAG-025 — Stage 분류기 단일화 (§2.6)

> **이전 판의 결함 두 가지.**
> **(1) 동일성만으로는 어느 분류기인지 결정되지 않는다.** "두 경로의 stage가 같다"는 **양쪽이 모두 폐기 대상인 일봉 근사 분류기를 쓰는 상태에서도 참**이다. 요구사항은 "같다"가 아니라 "**둘 다 주봉 Weinstein 분류기를 쓴다**"이다.
> **(2) `grep "def .*stage"`는 이름 변경으로 회피된다.** `_classify_stage_simple`을 `_derive_phase`로 rename하면 스캔이 0행이 되면서 코드는 그대로 남는다. 정적 스캔에만 의존해서는 안 된다.
>
> 실측(2026-08-12): `backend/services/sector_detail_service.py:23` `_classify_stage_simple`이 `close` / `sma50` / `sma200`(일봉) 3입력으로 분류하며, `:115`·`:143` 두 곳에서 호출된다. 주봉 Weinstein 분류기(`my_chart/analysis/stage_classifier.py:classify_stage`)는 `Close`/`SMA10`/`SMA40`/`SMA40_Trend_4M`/`RS_12M_Rating`/`Volume`/`VolumeSMA10` **7입력**의 완전히 다른 알고리즘이다. 두 분류기는 같은 종목에 다른 답을 낼 수 있고, 그것이 바로 이 REQ가 존재하는 이유다.

- **Given** 두 분류기가 **서로 다른 답을 내도록 설계된** 합성 픽스처 `fixture_stage_divergent` — 각 케이스는 주봉 Weinstein 기대 stage를 리터럴로 못 박는다.

| 케이스 | 일봉 입력 (`close`/`sma50`/`sma200`) | 주봉 입력 (`Close`/`SMA10`/`SMA40`/`SMA40_Trend_4M`/`RS`) | `_classify_stage_simple` | **주봉 Weinstein (기대)** |
| --- | --- | --- | --- | --- |
| C1 | 상승 배열 (close>sma50>sma200) | `SMA40` 하락 추세 + RS 낮음 | 2 | **1 또는 4** (≠2) |
| C2 | 하락 배열 (close<sma50<sma200) | `SMA40` 상승 추세 + `Close>SMA10>SMA40` + RS 높음 | 4 | **2** |
| C3 | 상승 배열 | `SMA40` NULL | 2 | **`None` + `reason:"insufficient"`** |

- **When** 섹터 상세 경로와 Stage 분포 경로에서 각각 stage를 조회하면
- **Then** 두 경로의 값이 동일**하고**, 그 값이 위 표의 **주봉 Weinstein 기대값과 일치**한다(케이스별 리터럴 단언). 동일성 단독 단언을 쓰지 않는다.
- **And** **대조 단언**: `_classify_stage_simple`을 그대로 사용하는 변형에서 C1·C2가 **실패**한다 — 즉 이 테스트가 실제로 분류기 교체를 검출함을 증명한다.
- **And** **행동 단언(이름 변경 내성)**: `sector_detail_service` 모듈에 `close`/`sma50`/`sma200` 3입력만으로 stage를 산출하는 호출 가능 객체가 **존재하지 않는다** — 모듈의 public/private 심볼을 순회해 시그니처로 검사한다. rename으로 회피되지 않는다.
- **And** 정적 스캔(보조): `grep -nE "def .*stage|sma200" backend/services/sector_detail_service.py` → 0행. **이 스캔은 단독 근거가 아니며** 위 행동 단언의 보조 확인이다.
- **And** `_classify_stage_simple`의 두 호출부(`:115`, `:143`)가 주봉 분류기 경로로 교체되었음을 확인한다.

### AC-SAG-026 — Stage 분류 불가 처리

- **Given** `SMA40` 또는 `SMA10`이 NULL인 종목에서
- **Then** `stage is None` + `reason:"insufficient"`이고 `stage2_pct` 분모에서 제외된다(0 치환 금지).

### AC-SAG-027 — Stage 합계 항등식 (불변식 **§8.6**)

- **When** `/stage/overview`(전체) 및 `by_sector`의 **모든** 엔트리에서
- **Then** `s1+s2+s3+s4+unclassified == total_count`가 성립한다(전 엔트리 루프 단언).
- **And** `unclassified_count` 필드가 존재한다.
- **And** 분류 불가 종목이 Stage 1 카운트에 흡수되지 않는다(합성 픽스처로 확인).
- **현재 상태**: 미검증

### AC-SAG-028 — volume_ratio (§2.8)

- **Given** `Volume=200`, `VolumeSMA10=100`, 가격 `SMA10=50000`인 종목에서
- **Then** `volume_ratio == 2.0`이다 (현행 로직이면 `200/50000 == 0.004`).
- **And** `VolumeSMA10`이 NULL 또는 0이면 `volume_ratio is None`(1.0 치환 금지).
- **And** 정적 스캔: `grep -n "volume_sma10 = sma10" my_chart/analysis/sector_advanced.py` → 0행.

### AC-SAG-029 — 거래대금 출처 (§2.7)

- **Given** daily `VolumeWon = 1_000_000_000`, `Close × Volume = 999_000_000`인 종목에서
- **Then** `trading_value == 1_000_000_000`이다.
- **And** 정적 스캔: 집계 경로에 `Close * Volume` / `close * volume` 재계산 표현이 0건.

### AC-SAG-030 — RS 평균 등가중 + 결측 제외 (§2.3)

- **Given** 10종목 중 2종목에 RS 행이 없는 픽스처에서
- **Then** `rs_avg == Σ(8종목 RS)/8`이고, `0.0` 치환 후 10으로 나눈 값과 **다르다**.
- **And** `rs_coverage == 0.8`.
- **And** 시총가중이 아님을 확인 — 대형주 RS를 크게 바꿔도 `rs_avg` 변화가 `1/n` 비례다.
- **And** 라이브 회귀: 방산 RS 평균이 45.64가 아니라 **51 ± 2**로 **상승**한다.
- **And (rs_top_pct, §2.4)**: 같은 픽스처(10종목 중 2종목 RS 부재, 나머지 8종목 중 3종목이 RS >= 80)에서 `rs_top_pct == 3/8 × 100 == 37.5`이며, `member_count`(10)를 분모로 쓴 값(30.0)과 **다르다**.
- **And** 임계값 80이 단일 상수로 정의되고 응답에 `rs_top_threshold == 80`으로 실린다.
- **And** 경계값 정확히 RS == 80인 종목은 **포함**된다(`>= 80`).

---

## 5. RRG

### AC-SAG-031 — RS-Ratio 100 = 벤치마크 (불변식 **RRG-1**)

- **Given** 섹터 지수와 벤치마크 지수가 **완전히 동일한** 합성 픽스처에서
- **When** RS-Ratio를 산출하면
- **Then** 전 구간에서 `rs_ratio == 100.0 ± 0.01`이다.
- **And** 전 섹터가 벤치마크를 상회하는 픽스처에서 **모든** 섹터의 `rs_ratio > 100`이다 — 횡단면 z-score였다면 절반이 100 미만이 된다.
- **And** `benchmark_name`이 응답에 존재한다.
- **현재 상태**: 실패 (횡단면 평균)
- **선결**: §7 O-A1 결정 필요. 결정 전에는 이 AC를 통과시킬 수 없다.

### AC-SAG-032 — 워밍업 미발행 (불변식 **RRG-2**)

- **Given** `lookback_weeks=12`이고 히스토리 30주인 픽스처에서
- **When** RRG를 조회하면
- **Then** `trail[]`의 길이가 `30 − 12`(± 1, 모멘텀 차분 1점 추가 제외) 이하이고, `trail_start_date`가 히스토리 첫 날짜보다 **늦다**.
- **And** `trail[]`의 어떤 점도 `rs_ratio == 100.0` 상수 패딩이 아니다.
- **And** 최초 12개 모멘텀 값이 0으로 눌려 있지 않다 — `trail[0..3]`의 `rs_momentum`이 서로 다르다.
- **현재 상태**: 실패

### AC-SAG-033 — 지수 = 수익률 연쇄 (불변식 **RRG-3**)

- **Given** 구성종목 수가 도중에 바뀌는 픽스처(각 종목 수익률은 매주 +1%)에서
- **When** 섹터 지수를 산출하면
- **Then** 인접 지수 비율이 전 구간 `1.01 ± 0.001`이다 — 구성종목 변동에 따른 **레벨 점프가 없다**.
- **And** 날짜별 `Σ(close×cap)/Σcap` 재계산 방식으로 같은 픽스처를 계산하면 점프가 **발생함**을 대조 단언한다.
- **현재 상태**: 실패 (전자제품 ±14% 계단 실측)

### AC-SAG-034 — look-ahead 시총 금지 (불변식 **RRG-4**)

- **Given** 주가가 과거에 절반이었던 종목 픽스처에서
- **When** 과거 날짜의 지수 가중치를 산출하면
- **Then** 그 시점 시총이 `주식수 × 과거주가`이며 현재 시총과 **다르다**.
- **And** `주식수 == 현재시총 / 현재주가`로 산출되고, 산출에 쓰인 "현재주가"의 출처가 코드에서 단일 지점으로 명시된다.
- **And** 현재 스냅샷 시총을 과거에 적용하는 경로가 코드에 남아 있지 않다(정적 스캔 + 대조 테스트).
- **현재 상태**: 실패
- **선결**: §7 O-A3 (주식수 상수 가정의 경고 처리) 결정.

### AC-SAG-035 — RRG 결측 처리

- **Given** RS-Ratio 산출 불가 섹터가 있을 때
- **Then** 해당 섹터의 점이 `trail[]`에서 **누락**되고 `excluded[]`에 사유와 함께 기록된다.
- **And** `rs_ratio == 100` 대체가 발생하지 않는다.

---

## 6. 응답 계약·API

### AC-SAG-036 — 응답 공통 스키마 (§9.3)

- **When** `/sectors/ranking`, `/sectors/bubble`, `/sectors/rrg`, `/sectors/history`, `/stage/overview`, `/sectors/{name}/detail`, `/sectors/{name}/bubble` 7개를 각각 호출하면
- **Then** **모든** 응답이 `as_of_date`, `as_of_is_partial_week`, `return_window_days`, `market_filter`, `weight_cap`, `grid_version`, `benchmark`, `data`, `excluded`, `warnings` 10개 키를 갖는다(엔드포인트별 루프 단언).
- **And** `excluded`는 빈 배열일 수 있으나 **키 자체는 항상 존재**한다.
- **And** `return_window_days`는 `period` 파라미터와 무관하게 항상 `{"1w", "1m", "3m"}` 세 키를 갖는다(값 단언은 AC-SAG-046 소관).

### AC-SAG-037 — 전 엔드포인트 as_of_date 일치 (불변식 **SN-3**)

> **이전 판의 결함 — 라이브 데이터에서 반증 불가.** ①의 AC-SGR-006과 정확히 같은 함정이다. 실측(2026-08-12): 최신 ISO 주(W33) 정규 대표 바 = `2026-08-11` = 순진한 `MAX(Date)`. 따라서 7개 엔드포인트가 **전부 순진한 `MAX(Date)`를 그대로 써도 서로 일치하므로 이 AC는 통과한다.** "서로 같다"는 "격자를 쓴다"의 증거가 아니다.

- **Given** ①의 `fixture_max_ne_canonical`(순진한 `MAX(Date)` ≠ 정규 대표 바가 되도록 설계된 합성 주봉 DB — ① acceptance.md AC-SGR-006 참조)를 주입하고 동일 `market` 필터로
- **When** 7개 엔드포인트를 연속 호출하면
- **Then** 7개 `as_of_date`가 모두 동일할 뿐 아니라 **정규 대표 바 값(`W-금요일`)과 같다** — `naive_max` 값과는 **다르다**(양쪽 모두 단언).
- **And** 7개 `grid_version`이 동일하고 `"canonical-v1"`이다.
- **And** **대조 단언**: 엔드포인트를 하나씩 순진한 `MAX(Date)` 경로로 되돌린 7개 변형에서 각각 이 AC가 **실패**한다. 7회 반복해 7개 배선이 전부 실제로 이루어졌음을 증명한다 — 1곳만 교체하고 나머지가 우연히 일치하는 상태를 검출한다.
- **And** **라이브 비게이팅 스모크**: 라이브에서도 7개 값이 동일함을 확인하되 **정보성 검사**로 표시하고, 라이브 통과가 오늘 `naive_max == canonical`인 우연 때문임을 docstring에 명시한다.
- **현재 상태**: 실패

### AC-SAG-038 — 결측 3상태 구분 (§9.1/§9.2)

- **Given** (a) 원천 값 없음, (b) 실제 0, (c) 산출 조건 미달 3케이스 픽스처에서
- **Then** 각각 `{value: null, reason: "missing"}`, `{value: 0.0}`, `{value: null, reason: "insufficient"}`로 구분된다.
- **And** 응답 JSON 전체에서 결측 자리에 `0` / `0.0` / `50.0`이 나타나지 않는다(전 필드 스캔 단언).

### AC-SAG-039 — market/period 파라미터 신설 (§12.3)

- **When** 6개 엔드포인트(`/sectors/ranking`, `/sectors/rrg`, `/sectors/history`, `/sectors/{name}/bubble`, `/sectors/{name}/detail`, `/stage/overview`)에 `market=kospi`를 전달하면
- **Then** 각 응답의 `market_filter == "kospi"`이고, `market=all` 응답과 **데이터가 다르다**(동일하면 필터 미반영).
- **And** 파라미터 미전달 시 기본값 `all`(및 `/ranking`·`/detail`의 `period=1m`)로 동작해 기존 호출과 **하위 호환**된다.
- **And** 잘못된 값(`market=nyse`)은 422를 반환한다.
- **And** 필터는 **집계 시점**에 적용된다 — `market=kospi` 응답의 `member_count`가 `all`보다 작다.

### AC-SAG-040 — Bump 히스토리 응답 (§8.4)

- **When** `/sectors/history?weeks=12&market=all`을 호출하면
- **Then** `dates[]` 길이 == `weeks`, `span_days`가 `7×(weeks−1) ± 7`이다(①의 TG-4 소비).
- **And** 특정 날짜에 순위 대상이 아니었던 섹터의 `rankings[date][sector]`가 `null`이며, 최하위 순위값으로 대체되지 않는다.

### AC-SAG-041 — 종목 목록 필드 (§8.5)

- **When** 종목 목록 응답을 조회하면
- **Then** 각 종목이 `weight_in_sector`, `sector_minor`, `stage`, `stage_detail`, `rs_12m`, `chg_1w`, `chg_1m`, `chg_3m`, `trading_value`, `volume_ratio`, `near_52w_high` 필드를 갖는다.
- **And** `chg_1w`/`chg_1m`/`chg_3m` **3개 모두** 반환된다 — 기간 토글과 무관하게 항상(③의 3열 상설 요구).
- **And** 상한이 적용된 종목의 `weight_in_sector == 0.10`이고 `weight_capped: true`가 동반된다.
- **And** 섹터 상세에서 진입한 종목 목록의 유니버스가 순위표와 **동일**하다(종목 수 일치 단언).

### AC-SAG-042 — 종목 버블 섹터 기준선 (§8.7)

- **When** `/sectors/{name}/bubble`을 조회하면
- **Then** `sector_aggregate` 필드에 해당 섹터의 기간 집계 수익률이 실린다.
- **And** 값이 `/sectors/ranking`의 동일 섹터·동일 기간 `sector_return`과 **일치**한다.

### AC-SAG-043 — 신규 필드 전 구간 전파 [Lesson #4]

- **Given** 본 SPEC이 추가한 필드 목록을 상수로 정의하고
- **When** 집계 dataclass / 서비스 변환 결과 / Pydantic 모델 `model_fields` / 실제 JSON 응답 4단계에서 각각 필드 존재를 확인하면
- **Then** **4단계 모두**에서 존재한다(단계별 루프 단언).
- **And** 파생 구조(`by_sector` 엔트리, 상세용 축약 리스트)에도 동일 필드가 존재한다.
- **근거**: Lesson #4 — 파생 구조가 원본 갱신을 자동 반영하지 않아 머지가 누락된 선례.

### AC-SAG-044 — 의미 테스트로의 대체 (테스트 1급 산출물)

- **When** `grep -c "hasattr" tests/test_sector_metrics.py`를 실행하면
- **Then** 기존 `hasattr`-only 블록(`:195-215`)이 값 단언 테스트로 대체되어 있다.
- **And** **되돌림 검출 증명**: 다음 3가지를 각각 되돌린 변형에서 최소 1개 테스트가 실패한다 — (a) 시총가중 → 등가중, (b) 순위 백분위 → min-max, (c) 벤치마크 방법론 일치 → KOSPI 지수 고정. 각 케이스를 mutation 스타일 테스트 또는 명시적 대조 픽스처로 증명한다.
- **And** 신규/변경 집계 모듈 라인 커버리지 >= 85%.

### AC-SAG-045 — **회귀 방지 AC**: 기대되는 변화 8종 (02 §12.2)

전부 **올바른 결과**다. 테스트가 기대값으로 고정하고 docstring에 "의도된 변화"를 명시한다.

| # | 변화 | 단언 |
| --- | --- | --- |
| R1 | 섹터 순위가 크게 뒤바뀐다 (평균 3.5계단, 최대 10계단) | 등가중 순위 대비 평균 절대 이동 `>= 2.5` |
| R2 | 1W 초과수익률 양수 섹터 29/29 → 18/29 | **삭제** — 아래 사유 |
| R3 | 52주 신고가 종목 99 → 56 | `40 <= nh_count <= 70` (프로즌 픽스처 기준) |
| R4 | RS 평균이 전반적으로 상승 | **골든 baseline 대비** 전 섹터 `rs_avg` 평균 상승 (아래 캡처 절차) |
| R5 | 복합점수 절대값이 바뀌고 분포가 균등해짐 | **골든 baseline 대비** 표준편차 증가 + 최상위 ≈100 / 최하위 ≈0 |
| R6 | KOSPI 필터에서 일부 섹터가 순위표에서 빠짐 | `excluded[]` 길이 >= 2 (디스플레이·스마트폰) |
| R7 | RRG에서 대부분 섹터가 한 사분면에 몰릴 수 있다 | 아래 실행 가능 형태로 재작성 |
| R8 | RRG 궤적이 짧아진다 (워밍업 제거) | `len(trail) < len(history_dates)` |

#### R2 삭제 사유

`10 <= positive_count <= 24`는 29개 섹터의 **34%~83%** 구간이다. 이 폭은 사실상 어떤 구현도 통과시키며 아무것도 게이팅하지 않는다. 같은 사안의 **실제 게이트는 AC-SAG-013의 `18 ± 3`**(15~21)이며, R2는 그것을 느슨하게 복제한 중복 항목이었다. **중복 + 무게이팅이므로 삭제한다** — 느슨한 범위를 남겨 두면 "회귀 테이블에 항목이 있다"는 인상만 주고 검출력은 0이다. AC-SAG-013이 이 변화를 계속 책임진다.

#### R4 / R5 — 골든 baseline 캡처 (plan.md M1 선행 작업)

R4("현행 대비 상승")와 R5("min-max 대비 증가")는 **비교 대상인 "현행"이 어디에도 보존되어 있지 않다.** 본 SPEC은 기존 구현을 교체하며 어느 SPEC도 구 구현을 남기지 않으므로, 구현이 끝난 시점에는 비교할 값이 존재하지 않는다 — 이전 판의 두 단언은 **실행 불가능**했다.

**해소 — plan.md M1의 선행 작업으로 골든 baseline을 캡처한다** (코드 변경 착수 **전**에 수행):

```
tests/fixtures/golden/pre-sector-ux/
  ranking-all-1w.json      ← GET /sectors/ranking (현행, 무파라미터)
  ranking-all-1m.json
  ranking-all-3m.json
  stage-overview.json      ← GET /stage/overview (현행)
  MANIFEST.md              ← 캡처 시각, git SHA, DB mtime, 캡처 명령
```

- 캡처는 **현행 코드 · 프로즌 DB 스냅샷**(§8 — 프로즌 픽스처 규약. §9는 품질 게이트다) 위에서 수행한다. 라이브 DB로 캡처하면 baseline 자체가 드리프트한다.
- `MANIFEST.md`에 캡처 시점의 git SHA와 DB 스냅샷 식별자를 남긴다 — 나중에 "이 baseline이 무엇과 비교되는 값인가"를 판별할 수 있어야 한다.
- **R4 단언**: 신 구현의 전 섹터 `rs_avg` 평균 > `ranking-all-*.json`에서 계산한 평균. 섹터별로도 `rs_avg` 상승 섹터 수가 하락 섹터 수보다 많음을 단언한다.
- **R5 단언**: 신 구현 `composite_score`의 표준편차 > baseline 표준편차. 최상위 `>= 95`, 최하위 `<= 5`.
- **M1 완료 조건에 포함한다** — baseline 미캡처 상태로 M2 착수를 금지한다. 한 번 코드를 바꾸면 되돌려 캡처하기 어렵다.

#### R7 재작성 — "그런 테스트가 없음을 확인한다"는 실행 가능한 검사가 아니다

이전 판은 "사분면 균등 분포를 요구하지 않음을 명시. 편중을 실패로 판정하는 테스트가 없음을 확인"이라고 적었다. **부재를 확인하는 절차가 없어 실행할 수 없다.** 두 개의 실행 가능한 검사로 대체한다:

- **(a) 행동 단언**: 전 섹터가 벤치마크를 상회하는 합성 픽스처(`fixture_all_leading`)에서 RRG를 산출하면 **모든 섹터의 `rs_ratio > 100`**이고, 전 섹터가 Leading/Improving 사분면에 몰려도 **응답이 정상이며 `warnings[]`에 편중 관련 경고가 실리지 않는다**. 편중은 정상 상태다.
  - **대조 단언**: 횡단면 z-score 방식으로 되돌린 변형에서는 같은 픽스처에서 약 절반이 `rs_ratio < 100`이 되어 위 단언이 **실패**한다.
- **(b) 정적 스캔**: 테스트 스위트에 사분면 분포 균등성을 요구하는 단언이 없다 — `grep -rnE "quadrant.*(balanc|even|distribut)|len\(leading\).*<" tests/` → **0행**. 부재 확인을 grep 명령으로 실행 가능하게 만든다.

이 두 검사는 REQ-SAG-028의 O-A1 결정(롤링 정규화 미적용 → 강세장 편중은 올바른 동작)과 직접 짝을 이룬다.

### AC-SAG-046 — 실제 창 일수 (REQ-SAG-043, O-A8 귀결) [게이팅 — 프로즌 한정]

> **이 AC가 잡으려는 잘못된 구현**: `return_window_days`를 **라벨값 그대로**(`{"1w": 7, "1m": 28, "3m": 91}` 상수) 채워 넣는 것. 이것이 가장 자연스러운 오구현이며 — 필드를 추가하라는 요구만 읽으면 상수를 넣는 게 제일 쉽다 — "필드가 존재한다" 또는 "값이 N과 같다" 류의 단언으로는 **전혀 검출되지 않는다**. 따라서 이 AC는 **프로즌 스냅샷에서 실측한 리터럴**로 값을 못 박는다. 되돌림(상수 N 반환)은 이 리터럴에서 즉시 붉어진다.

- **Given** 프로즌 스냅샷 `tests/fixtures/frozen/weekly-2026-08-12/weekly.db`, **`as_of`를 명시적으로 고정**한다 — 이 스냅샷의 정규 최신 바는 `2026-08-11`(**화요일**, ISO W33 진행 중)이고 `history_grid` 마지막 완성 바는 `2026-08-07`(금)이다. 아래 리터럴은 **이 `as_of` 요일에 종속**되므로 스냅샷을 다른 요일에 재캡처하면 함께 갱신한다(§8 규약 4).
- **When** 임의의 섹터 엔드포인트를 호출하면
- **Then** `as_of_date == "2026-08-11"`이고 `as_of_is_partial_week is True`이다.
- **And** `return_window_days == {"1w": 11, "1m": 32, "3m": 95}` — **정확히 이 세 값**이다. (참고: 라벨 N은 7 / 28 / 91이므로 셋 다 다르다.)
- **And** `period=1w` 조회에서 `benchmark.anchor_date == "2026-07-31"`이고 `(as_of_date − benchmark.anchor_date).days == return_window_days["1w"]` — 보고된 일수가 **실제로 쓰인 앵커**에서 나온 값임을 묶는다(AC-SAG-014의 섹터·벤치마크 앵커 동등 단언과 연쇄해, 리터럴 11이 곧 섹터 수익률 구간임을 함의한다).
- **And** `trading_value_window_days == return_window_days[period]`를 세 기간 각각에서 확인한다(O-A4 창과 동일 구간, REQ-SAG-043 설계결정 2).
- **And** `rank_change`의 `baseline_date == "2026-07-10"`이고 `(as_of_date − baseline_date).days == return_window_days["1m"] == 32` — `anchor(t,28)`이 1M 앵커와 같은 호출임을 확인한다(REQ-SAG-021).
- **And** **되돌림 대조 (필수)**: `return_window_days`를 라벨 상수 `{7, 28, 91}`로 바꾼 변형에서 이 AC가 **실패**한다. 실패하지 않으면 단언이 무게이팅이라는 뜻이므로 AC를 다시 쓴다.
- **And** **마감 주 대조**: `as_of`를 완성 주 금요일(`2026-08-07`)로 강제한 변형에서는 `as_of_is_partial_week is False`이고 `return_window_days == {"1w": 7, "1m": 28, "3m": 91}`이다 — 초과분이 미완성 주에서만 발생함을 보인다. 이 절이 있어 "항상 N보다 크다"는 반대 방향의 오구현(무조건 +4 가산)도 검출된다.
- **현재 상태**: 미검증 (신규 필드)

**반증 가능성 근거 (실측 2회)**: `as_of=2026-08-11`(화)에서 창 11 / 32 / 95일, `as_of=2026-08-12`(수, 라이브 DB)에서 12 / 33 / 96일을 직접 측정했다. 두 측정 모두 라벨(7 / 28 / 91)과 다르므로, 라벨 상수를 반환하는 구현은 어느 쪽 스냅샷에서도 이 AC를 통과할 수 없다. 초과분이 세 기간에 동일한 것은 7·28·91이 모두 7의 배수이기 때문이며(파생), 요일별 예상치 월 +3 / 목 +6 / 금 0은 **미측정 파생값**이므로 AC 리터럴로 쓰지 않는다.

---

## 7. 에지 케이스

| # | 상황 | 기대 |
| --- | --- | --- |
| E1 | 섹터 구성종목 전원 `CHG` NULL | `sector_return is None` + `coverage_ratio == 0` + `excluded[]` 등록 |
| E2 | 시총이 1종목에 100% 집중 (N=1) | `cap_eff = max(0.10, 1/1) = 1.0` → 상한 무구속. 단 §5.4에서 이미 제외 대상 |
| E3 | `market=kosdaq`에서 구성종목 0인 섹터 | `excluded[]`에 `count: 0`으로 등록. 예외 없음 |
| E4 | 전 섹터 composite가 null (벤치마크 부재) | `data[]`는 원수익률과 함께 반환, 전 `rank is None`, `excluded[]`에 전 섹터 |
| E5 | 히스토리가 lookback보다 짧음 | `trail[]` 빈 배열 + `trail_start_date is None` + `warnings[]`에 사유 |
| E6 | 과거 주가가 0 또는 NULL (역산 불가) | 그 날짜의 해당 종목을 지수에서 제외하고 가중치 재정규화 |
| E7 | `period=3m`인데 3M 앵커 바가 없음 (이력 부족) | `sector_return_3m is None` + `reason:"missing"` → composite null |
| E8 | 동일 종목이 두 섹터에 소속 | ①의 registry dedup 이후 발생 불가. 발생 시 WARNING + 첫 소속 채택 |

---

## 8. 프로즌 픽스처 규약 [HARD — ①과 공유]

**문제**: 아래 AC들이 라이브 DB 값을 게이팅 기대값으로 못 박는다.

| AC | 못 박은 라이브 값 |
| --- | --- |
| AC-SAG-002 | 헬스케어 +17.07% / 반도체 −6.59% (시총가중 1M), 순위 대소 |
| **AC-SAG-011** | **1W 벤치마크 KOSPI +1.03% / KOSDAQ +7.54% / All +1.88% (±0.5%p)** — 이전 판은 이 AC를 게이팅 표에도 §8.5 순수 합성 열거에도 넣지 않아 규약 밖에 있었다. `/api/db/update` 1회로 붉어지는 전형적 형태다 |
| AC-SAG-013 | 1W 양수 섹터 `18 ± 3` |
| AC-SAG-024 | 신고가 종목 `56 ± 8` |
| AC-SAG-030 | 방산 RS 평균 `51 ± 2` |
| AC-SAG-045 R3 / R4 / R5 | 신고가 40~70, RS 평균 상승, composite 분포 |
| **AC-SAG-046** | **`as_of_date=2026-08-11`, `return_window_days={1w:11, 1m:32, 3m:95}`, `benchmark.anchor_date=2026-07-31`, `baseline_date=2026-07-10`** — 스냅샷의 `as_of` **요일**(화)에 종속된 값이다. 재캡처 요일이 바뀌면 네 리터럴이 전부 바뀐다(규약 4 적용 대상) |
| AC-SGR-020 (① 소관, ②가 소비) | 게임 32 / 격자 346바 |

그런데 `/api/db/update`는 **주 1회 이상, 종종 주중에도** 실행된다(spec.md §2 A2). **게이팅 AC가 코드 변경 없이 붉어진다.** 드리프트는 이미 시작됐다 — `01-data-contract.md`는 2026-W32(08-07)를 2,548행으로 기록하지만 현재 DB는 그 이후로 갱신되었다.

**규약** (①의 acceptance.md §3과 동일한 스냅샷을 공유한다):

1. **게이팅 AC는 `tests/fixtures/frozen/weekly-2026-08-12/` 축소 스냅샷 위에서만 실행한다.** 위 표의 기대값은 전부 이 스냅샷의 값이며 스냅샷과 함께 고정된다.
2. **골든 baseline**(`tests/fixtures/golden/pre-sector-ux/`, AC-SAG-045 R4/R5)도 **같은 프로즌 스냅샷 위에서** 캡처한다. 라이브로 캡처하면 baseline과 비교값의 기준이 어긋난다.
3. **라이브 DB 실행은 비게이팅 스모크**다. 실패해도 CI를 막지 않으며 **불일치를 리포트로 남긴다** — "데이터가 갱신됐다"인지 "집계 규칙이 깨졌다"인지 판별하는 것이 리포트의 목적이다.
4. **스냅샷 갱신은 명시적 행위다.** 커밋 메시지에 사유와 새 실측값을 남기고 AC 본문 기대값도 함께 갱신한다. 조용한 재생성을 금지한다.
5. 순수 합성 픽스처 AC(001, 003~010, 012, 014~023, 025~029, 031~043, **044**)는 해당 없음. **AC-SAG-044**는 정적 스캔(`grep -c "hasattr"`) + mutation 대조로만 구성되어 라이브 값을 기대값에 넣지 않으므로 스냅샷 드리프트의 영향을 받지 않는다 — 무해하지만 이전 판에서 어느 열거에도 없었으므로 완결성을 위해 명시한다.
6. **열거 완결성 규칙**: `AC-SAG-001`~`046` 전부가 (게이팅 표) 또는 (§8.5 순수 합성 열거) 중 **정확히 한 곳**에 나타난다. 새 AC를 추가하면 둘 중 하나에 반드시 등재한다 — 어느 쪽에도 없는 AC는 규약 밖에 방치되며, 그것이 AC-SAG-011/044가 누락된 경로였다. `AC-SAG-046`(2026-08-13 신설)은 게이팅 표에 등재했다.

7. **드리프트가 진행 중이다 — M1.0 캡처 전에 `as_of` 기준일을 먼저 정한다** (2026-08-13 기록). 프로즌 스냅샷의 정규 최신 바는 `2026-08-11`(화)이나 라이브 주봉 DB는 이미 `2026-08-12`(수)까지 갱신됐다(실측). 본 SPEC의 M1.0 골든 baseline은 **아직 캡처되지 않았으므로**, 캡처 담당자는 착수 시 **baseline이 어느 `as_of`에 고정되는지 먼저 결정하고 `MANIFEST.md`에 적어야 한다.** 기존 프로즌(08-11)을 그대로 쓸지, 새 스냅샷을 뜰지의 선택이며, **새로 뜨면 AC-SAG-046의 네 리터럴이 전부 바뀐다**(요일 종속).
   - **왜 이것이 명시적 결정이어야 하는가**: `SPEC-MARKET-BREADTH-001`에서 `date.today()`에 매달린 프로즌 리터럴이 ISO 주가 마감되는 것만으로 **코드 변경 0줄에** 붉어지는 사례가 관측됐다. O-A8 결정으로 본 SPEC의 `as_of`는 **미완성 주 바**에 놓이므로 정확히 같은 노출을 갖는다 — 미완성 주는 요일마다 값이 변하고 금요일에 마감되면 초과분이 0이 된다. 따라서 미완성 `as_of`에서 유도한 **모든** AC 리터럴은 `as_of` 명시 고정을 동반해야 하며, 이는 AC-SAG-046 본문의 **Given** 절에 이미 반영돼 있다.

---

## 9. 품질 게이트 (Definition of Done)

- [ ] AC-SAG-001 ~ AC-SAG-046 전부 PASS
- [ ] **선결 미결 해소 — 구현 착수 전 사용자 결정 필요**: ~~**O-A8**~~ **해결 (2026-08-13)** — M3 차단 해제. **O-A7**(최소 구성수 5의 Bump 적용 — ③의 AC-SUX-019 / AC-SUX-056 R5가 의존, **③ 착수 전 필요**)만 남는다
- [ ] **해결 완료 확인**: O-A1(롤링 정규화 미적용), O-A3(warnings[] + daily 최신 Close), O-A4(기간 연동 창), O-A6(지표별 coverage + 최상위 최소값), **O-A8(미완성 주 포함 + `return_window_days`)** 5건이 REQ 본문에 반영됨
- [ ] **M1.0 baseline의 `as_of` 기준일이 `MANIFEST.md`에 명시됨** (§8 규약 7) — 미완성 주 `as_of`에서 유도한 AC 리터럴은 as-of 고정 없이는 코드 변경 0줄에 붉어진다
- [ ] **§8 프로즌 픽스처가 리포에 존재하고 게이팅 AC가 그 위에서 실행됨** — `/api/db/update` 1회 실행 후 재실행으로 확인
- [ ] **골든 baseline이 M1에서 캡처됨** (`tests/fixtures/golden/pre-sector-ux/` + `MANIFEST.md`) — 미캡처 상태로 M2 착수 금지
- [ ] `SPEC-SECTOR-GRID-001` close 확인 (`status: completed`)
- [ ] AC-SAG-044 되돌림 검출 3케이스 증명 완료
- [ ] 신규/변경 모듈 커버리지 >= 85%
- [ ] `pytest` 전체 회귀 통과
- [ ] §0.2 성능 baseline/목표 실측 기록 (progress.md §E.2)
- [ ] 응답 필드 추가가 **하위 호환**임을 확인 — 기존 프론트엔드 빌드/런타임 무오류
- [ ] `@MX:ANCHOR` — 가중치 산출, 벤치마크 산출, 정규화, RRG 지수 4개 지점
- [ ] ship commit에 frontmatter `status` 갱신 포함 (Lesson #6)
- [ ] 릴리스 노트에 R1~R8 "고장처럼 보이지만 올바른 변화" 반영
