# SPEC-RS-REBALANCE-001 — 수용 기준 (acceptance)

> 요구사항은 `spec.md` §3(REQ-RSR-001~023)에 있다. 이 문서는 검증 층이며 각 기준을 Given-When-Then으로 쓴다.
> **가격 행 픽스처 규칙**: `generate_rs_db()`는 `SELECT * FROM stock_prices` 뒤 `df.dropna()`를 적용하므로(`weekly.py:425-431`, REQ-RSR-023), 픽스처의 모든 `stock_prices` 행은 약 35개 전 컬럼(`my_chart.db.weekly._STOCK_PRICES_COLS`, `weekly.py:33`)을 NULL 없이 채워야 한다 — 그렇지 않으면 행이 결측 규칙으로 빠져 다른 AC의 기대값이 엉뚱한 이유로 맞거나 틀린다. 테스트는 공용 빌더 `tests/rsr_fixtures.py`의 `price_row(name, date, **overrides)`(M1 신설: `_STOCK_PRICES_COLS` 전 컬럼에 NULL 아닌 기본값을 채우고 지정 컬럼만 덮어씀)와 `make_weekly_db(tmp_path, rows)`(테이블은 `_ensure_stock_prices_table()`로 생성)를 함께 쓴다. AC-RSR-018처럼 NULL을 의도한 경우에만 `overrides`로 `None`을 넣는다.
> **대조 단언(lessons #9)**: 모든 AC는 "어떤 잘못된 구현을 잡는가"를 명시하고, 그 되돌림을 실제로 적용했을 때 RED가 관측되어야 한다. 단언의 두 변은 같은 식에서 나오면 안 되며, 적어도 한 변은 프로덕션 경로(실제 함수·실제 SQL·실제 응답)에서 나와야 한다. 기계적으로 되돌릴 수 없는 경우 monkeypatch 주입 대상 심볼을 적는다.
> **픽스처 공통 주의**: `generate_rs_db()`는 기준 종목(`REFERENCE_STOCK = "삼성전자"`)의 날짜 목록만 처리한다(`weekly.py:416-421`). 기준 종목을 픽스처에 넣으면 그 행이 분모에 들어가 기대 순위가 바뀌므로, 테스트는 `monkeypatch.setattr("my_chart.db.weekly.REFERENCE_STOCK", <픽스처 종목명>)`으로 기준 종목을 픽스처 종목 하나로 지정한다. 기준 종목은 픽스처의 모든 처리 대상 날짜에 행을 가져야 한다.
> 테스트 DB는 `tmp_path`에 새로 만든다. 라이브 `Output/` DB는 AC-RSR-001·002·007·014·015·017의 "라이브 단계"에서만 읽고, 쓰기는 M2·M4의 정식 갱신 경로로만 한다.

## §D AC 매트릭스

| AC | REQ | 마일스톤 | 대조(되돌림) |
|---|---|---|---|
| AC-RSR-001 | REQ-RSR-001 | M1 (+M2 라이브) | (i)·(ii) 동시 제거 / (i)만 제거 |
| AC-RSR-002 | REQ-RSR-002, 004, 008 | M1 (+M2 라이브) | 분모 필터 제거 / 사후 마스킹으로 바꿔치기 |
| AC-RSR-003 | REQ-RSR-003 | M1 | 순진한 `우$` 패턴 / 끝자리 판별 제거 / `스팩` 판별 제거 |
| AC-RSR-004 | REQ-RSR-007 | M1 | `1+R ≤ 0` 가드 제거 |
| AC-RSR-005 | REQ-RSR-005 | M2 | 현행 가중치 / 차분식 / 12M 단독 |
| AC-RSR-006 | REQ-RSR-006, 009 | M1 특성화, M2 | 6M/3M/1M 산식 변형 |
| AC-RSR-007 | REQ-RSR-010 | M4 | Phase 4 복사 제거 |
| AC-RSR-008 (+008b) | REQ-RSR-011 | M4 | 튜플 중간 삽입 / ALTER 누락 / DDL 중간 배치 |
| AC-RSR-009 | REQ-RSR-012, 014 | M4 | `rs_1m`에 다른 주차·다른 컬럼 연결 |
| AC-RSR-010 | REQ-RSR-013, 014 | M4 | `rs_med`를 평균으로 / 결측을 0으로 |
| AC-RSR-011 | REQ-RSR-015, 016, 022 | M5 | `>` 경계 / 리터럴 80 / 결측을 높은 값으로 |
| AC-RSR-012 | REQ-RSR-017 | M5 | `rs_med` 열 누락·`rs_avg` 재사용 |
| AC-RSR-013 | REQ-RSR-019, 022 | M3 | 리터럴 70 잔존(코드·주석·라벨) / 거울 상수 불일치 / 80 변경 |
| AC-RSR-014 | REQ-RSR-020 | M2 (기준선·목표), M6 (기록) | 현행 산식으로 재생성 / 원시 컬럼 재계산 |
| AC-RSR-015 | REQ-RSR-018 | M3 | (a) 두 사본 60/70/80 판별력 사전 조건 + 상대 ±10%(기록만 모드 포함) / (b) ±5%p와 기록된 차이 |
| AC-RSR-016 | REQ-RSR-021 | M2 | 가중치 변경 |
| AC-RSR-017 | REQ-RSR-001, 004 | M1 (+M2 라이브) | (i)·(ii)를 짝 기준 삭제로 바꿔치기 |
| AC-RSR-018 | REQ-RSR-023 | M1 | 결측 행에 부분 산식으로 등급 부여 |
---

## AC-RSR-001 — 짝 없는 행 제거 (REQ-RSR-001)

- **Given** 기준 종목을 `S1`으로 지정한(`monkeypatch.setattr("my_chart.db.weekly.REFERENCE_STOCK", "S1")`) 임시 주간 DB에 `stock_prices`가 날짜 `d1`, `d2`의 종목 `S1`~`S5` 행을 갖고, `relative_strength`가 그 쌍들과 함께 세 종류의 짝 없는 행 — (a) `stock_prices`에 없는 날짜 `dX`의 행 3개, (b) `stock_prices`에 없는 이름 `OLD`의 `d1` 행 1개, (c) `stock_prices`에 `S2` 1행만 있는(기준 종목 `S1`은 없는) 날짜 `dP`의 다른 종목 행 2개 — 를 갖는다
- **When** `generate_rs_db()`를 실행한다
- **Then** `SELECT COUNT(*) FROM relative_strength rs LEFT JOIN stock_prices sp USING(Name, Date) WHERE sp.Name IS NULL`이 `0`이다. **라이브 단계(M2 재생성 후)**: 같은 질의를 `Output/stock_data_weekly.db`(immutable 읽기)에 실행해 `0`(변경 전 관측 `119881`, research.md R2)
- **대조**: (i)과 (ii)를 모두 제거하면 짝 없는 행 `6`개가 그대로 남는다(RED). (i)만 제거하면 (b)는 (ii)가 지우지만 (a)·(c)의 `5`개가 남는다(RED). 짝 없는 행은 (i)·(ii)에 포함되므로 별도 조항이 없다(spec.md REQ-RSR-001) — 그 포함 관계가 이 두 수치로 드러난다.
- **AC-RSR-017과의 구분**: 이 AC는 `stock_prices` 짝이 **없는** 행을, AC-RSR-017은 짝이 **있는데도** 남는 낡은 행을 다룬다. 픽스처와 잡는 오구현이 다르다(이 AC는 "재생성이 덮어쓰니 정리는 필요 없다", AC-RSR-017은 "짝 없는 행만 지우면 충분하다").
- **양변 출처**: 좌변은 프로덕션 실행 후 실제 테이블 질의, 우변은 픽스처에 심은 행 수(6, 5)라는 독립 상수.
- **as-implemented (sync 2026-10-20) 비고 — 기준 종목 날짜 0개 가드(spec.md REQ-RSR-001 주석)**: 테스트 `test_missing_reference_stock_leaves_table_untouched`(`tests/test_rsr_m1_denominator.py:102`)가 고정한다. 기준 종목을 픽스처에 없는 `ABSENT`로 지정하고 `relative_strength`에 2행(처리 날짜 `d1` 1행, 가격 행 없는 날짜 1행)을 심은 뒤 실행하면 `SELECT COUNT(*) FROM relative_strength`가 `2`로 그대로다. 대조: 가드를 `if False:`로 바꾸면 `AssertionError: assert 0 == 2`(테이블 전체 삭제) RED(progress.md §E.2 `### M1`). sync 재실행: `pytest "tests/test_rsr_m1_denominator.py::test_missing_reference_stock_leaves_table_untouched" -q` → `1 passed in 0.26s`.

## AC-RSR-002 — 지수·거래량 0 분모 제외, 유동성 비적용 (REQ-RSR-002, 004, 008)

- **Given** 임시 DB의 한 날짜에 일반 종목 4개(`S1`~`S4`, 거래량 > 0), `KOSPI`, `KOSDAQ`, 거래량 0인 `Z`, 그리고 거래대금이 50억 원에 크게 못 미치는 일반 종목 `L`이 있고, 모든 행의 원시 수익률이 결측 없이 채워져 있다. `Z`의 `RS_1M`은 일반 종목 중간값보다 크게 설정한다
- **When** `generate_rs_db()`를 실행한다
- **Then** (a) `relative_strength`에 `KOSPI`, `KOSDAQ`, `Z` 행이 없다; (b) `L`의 행은 존재한다; (c) `S1`~`S4`, `L` 다섯 종목의 `RS_1M_Rating`이 그 다섯 종목만으로 계산한 `rank(pct=True)*100` 값(테스트 안의 독립 계산)과 같다
- **대조**: 필터를 제거하면 (a)가 RED(행 3개 존재). 필터를 "전체로 순위를 매긴 뒤 행만 버리는" 사후 마스킹으로 바꾸면 (a)는 통과하지만 (c)가 RED — `Z`가 분모에 남아 다른 종목의 백분위가 달라진다. 유동성 필터를 분모에 넣으면 (b)가 RED.
- **양변 출처**: 좌변은 프로덕션 테이블 값, 우변은 테스트가 픽스처 원시값으로 직접 계산한 기대 순위(프로덕션 함수 호출 없음).
- **라이브 단계(M2 재생성 후)**: `SELECT COUNT(*) FROM relative_strength WHERE Name IN ('KOSPI','KOSDAQ')` → `0`(변경 전 `692`, 그중 짝 있는 행 600 — research.md R2·R2.1). 그리고 `SELECT COUNT(*) FROM relative_strength rs JOIN stock_prices sp USING(Name, Date) WHERE sp.Volume = 0` → `0`(변경 전 `16369`).

## AC-RSR-003 — 우선주·스팩 판별 규칙 (REQ-RSR-003)

- **Given** 임시 DB와 테스트용 등록부에 보통주 `성우`, `에코글로우`, `이오플로우`(실측 이름, 코드 끝자리 `0`, research.md R3), 합성 우선주 `가나다우`(코드 끝자리 `5`), 합성 스팩 `가나다스팩1호`(코드 끝자리 `0`)가 있고 모두 거래량 > 0, 원시 수익률 결측 없음이다. 판별 규칙은 spec.md §2.4 B-1(코드 끝자리 ≠ `0` → 우선주, 이름에 `스팩` → 스팩)이다
- **주입 지점**: `weekly.py:24`가 `from my_chart.registry import get_stock_registry`로 함수를 모듈 이름공간에 가져오므로, 테스트는 `monkeypatch.setattr("my_chart.db.weekly.get_stock_registry", lambda: <테스트 등록부 DataFrame>)`으로 등록부를 주입한다. 대안으로 지연 전역 `my_chart.registry._df_stock`(`registry.py:108-119`)을 바꿀 수 있으나, 다른 테스트로 새는 것을 막기 위해 모듈 이름공간 주입을 기본으로 한다
- **When** `generate_rs_db()`를 실행한다
- **Then** 보통주 3개는 `relative_strength` 행을 갖고, `가나다우`와 `가나다스팩1호`는 행을 갖지 않는다
- **대조**: 판별을 이름 패턴 `우$`로 바꾸면 보통주 3개의 행이 사라져 RED. 코드 끝자리 판별을 제거하면 `가나다우`가 행을 가져 RED. `스팩` 판별을 제거하면 `가나다스팩1호`가 행을 가져 RED — 이 종목은 코드 끝자리가 `0`이라 끝자리 규칙으로는 잡히지 않으므로 두 판별이 독립적으로 검증된다.
- **라이브 사실(사전 가드임을 기록)**: 현재 등록부(`get_stock_registry()`, 2,559행)에서는 이 규칙의 제외 대상이 0개다(코드 끝자리 `{'0': 2559}`, 이름 `스팩`·`SPAC` 0개 — research.md R3). 따라서 라이브 재생성 결과는 규칙 유무와 무관하게 같으며, 이 AC는 픽스처로만 효과를 검증한다.

## AC-RSR-004 — `1+R ≤ 0` 행 가드 (REQ-RSR-007)

- **Given** 임시 DB의 한 날짜에 정상 종목 4개와 `RS_6M = -1.0`인 종목 `V`가 있다(`RS_3M`, `RS_9M`, `RS_12M`은 정상값)
- **When** `generate_rs_db()`를 실행한다
- **Then** `V`의 행이 없고, 정상 종목 4개의 `RS_1M_Rating`은 그 4개만으로 계산한 백분위와 같다
- **대조**: 가드를 제거하면 `q3 = (1 + RS_9M) / (1 + RS_6M) − 1`의 분모가 0이 되어(`q2`의 분모는 `1 + RS_3M`이므로 영향 없음) `V`의 점수가 무한대가 되고, `V`가 행을 가져 RED(또는 0으로 나눔 오류로 RED). 관측 데이터에는 해당 행이 0개이므로 이 AC는 픽스처로만 검증한다(research.md R3).

## AC-RSR-005 — IBD식 산식 (REQ-RSR-005)

- **Given** 임시 DB의 한 날짜에 research.md R10의 종목 A~D(원시 수익률 고정, 거래량 > 0)가 있다
- **When** `generate_rs_db()`를 실행한다
- **Then** `RS_12M_Rating`이 A `100.0`, B `75.0`, C `25.0`, D `50.0`이다
- **대조** (각각 독립 RED):
  - 현행 가중치로 되돌리면 B `50.0`, D `75.0` → RED
  - 차분식(`RS_6M − RS_3M` 등)으로 바꾸면 A `75.0`, B `100.0` → RED
  - 12M 단독으로 바꾸면 A `75.0`, B `100.0` → RED
- **양변 출처**: 좌변은 프로덕션 테이블 값, 우변은 research.md R10에서 독립 계산해 고정한 리터럴. 테스트 안에서 IBD식을 다시 계산해 비교하는 형태(같은 식 양변)는 금지한다.

## AC-RSR-006 — 나머지 등급 산식 불변과 스키마 불변 (REQ-RSR-006, 009)

- **Given** M1 착수 직전 **변경 전 코드**로 R10 픽스처(필터에 걸리는 행 없음)를 처리해 캡처·단독 커밋한 골든값 — A `100.0/50.0/25.0`, B `25.0/25.0/50.0`, C `50.0/87.5/100.0`, D `75.0/87.5/75.0`(`RS_6M/3M/1M_Rating`, research.md R10)
- **When** 변경 후 `generate_rs_db()`를 같은 픽스처로 실행한다
- **Then** 네 종목의 `RS_6M_Rating`, `RS_3M_Rating`, `RS_1M_Rating`이 골든값과 정확히 같다(부동소수 동일). 그리고 `PRAGMA table_info(relative_strength)`의 컬럼 이름·순서가 `Name, Date, RS_12M_Rating, RS_6M_Rating, RS_3M_Rating, RS_1M_Rating`이며 `tests/test_weekly_insert.py` 12건이 수정 없이 통과한다(as-implemented (sync 2026-10-20): 원문 "10건" 정정 — 아래 비고)
- **대조**: `RS_6`에서 `rank_1m`을 빼는 등 세 산식 중 하나를 바꾸면 해당 열이 RED. 골든값은 변경 전 프로덕션 출력이므로 변경 후 프로덕션 출력과 출처가 다르다.
- **비고**: 필터에 걸리는 행이 섞인 입력에서는 분모가 달라지므로 값이 같을 수 없다. 그 경우의 정합성은 AC-RSR-002 (c)가 맡는다.
- **as-implemented (sync 2026-10-20) 비고 — `test_weekly_insert.py` 건수**: `grep -cE '^\s*(async )?def test_' tests/test_weekly_insert.py` → `10`(테스트 함수 수), `pytest tests/test_weekly_insert.py --collect-only -q` → `12 tests collected` — `:166`·`:199`의 `@pytest.mark.parametrize("drop_col", ["SMA10", "RS_1M"])`가 각각 2건으로 펼쳐진다. `pytest tests/test_weekly_insert.py -q` → `12 passed in 0.20s`. SPEC 범위 전체에서 파일 변경 없음: `git diff --stat f747ce5~1 HEAD -- tests/test_weekly_insert.py` → 출력 없음. 원문 "10건"은 함수 수를 센 값이며 "수정 없이 통과" 요구는 그대로 충족된다(sync 4차원 감사 Functionality 지적, spec.md §7.1 2번).

## AC-RSR-007 — `stock_meta.rs_1m` 복사 (REQ-RSR-010) — 계획서 AC-1b

- **Given** 임시 주간 DB의 최신 주차에 종목 3개의 `RS_1M_Rating`(서로 다른 값)과 그보다 한 주 앞선 주차의 다른 값이 있고, 임시 일봉 DB·등록부가 그 3개 종목과 RS 행이 없는 종목 1개를 갖는다
- **When** `rebuild_stock_meta(daily, weekly)`를 실행한다
- **Then** `SELECT name, rs_1m FROM stock_meta`가 3개 종목은 최신 주차 값, RS 행 없는 종목은 NULL이다
- **대조**: Phase 4 복사 코드를 제거하면 모두 NULL(RED). 앞 주차를 읽게 하면 값 불일치(RED). `RS_12M_Rating`을 잘못 연결하면 불일치(RED — 픽스처에서 두 컬럼 값을 다르게 둔다).
- **라이브 단계(M4 갱신 1회 후)**: `ATTACH` 없이 두 DB를 immutable로 읽어, 최신 주차 `RS_1M_Rating`과 `stock_meta.rs_1m`을 이름으로 맞춰 불일치 0건.

## AC-RSR-008 — 레거시 `stock_meta` 보강 (REQ-RSR-011)

- **Given** 임시 일봉 DB에 `rs_1m`이 없는 27컬럼 레거시 `stock_meta`(라이브와 같은 컬럼명 `ma50_w ma150_w ma200_w` 포함, research.md R6)가 있다
- **When** `rebuild_stock_meta()`를 실행한다
- **Then** `PRAGMA table_info(stock_meta)`의 마지막 컬럼이 `rs_1m`이고, 기존 27개 컬럼(`sma5` 포함)의 값이 픽스처 기대값과 같다(예: `rs_12m`은 `RS_12M_Rating`, `sma5`는 일봉 `SMA5`)
- **대조**: ALTER를 빼면 삽입이 컬럼 수 불일치로 실패(RED). 값을 튜플 중간(`rs_12m` 다음)에 끼우면 `ma50_w` 이후 값이 한 칸씩 밀려 RED.

### AC-RSR-008b — 새 DB의 컬럼 위치와 28번째 값 (REQ-RSR-011)

- **Given** `stock_meta`가 없는 빈 임시 일봉 DB와, 한 종목의 일봉 `SMA5` 값을 식별용 값 `5.555`, 주간 `RS_1M_Rating`을 `11.0`, `RS_12M_Rating`을 `22.0`으로 둔 주간 DB
- **When** `rebuild_stock_meta()`를 실행한다
- **Then** `PRAGMA table_info(stock_meta)`의 마지막 행이 `cid = 27`, `name = rs_1m`이고, 그 종목의 `sma5 = 5.555`, `rs_1m = 11.0`, `rs_12m = 22.0`이다
- **대조**: DDL에서 `rs_1m`을 중간(예: `rs_12m` 다음)에 두면 `cid` 단언이 RED. DDL은 끝에 두되 튜플에서 `rs_12m` 다음에 끼우면 그 뒤 값이 한 칸씩 밀려 `sma5` 컬럼은 `sma200_20d_ago`의 값을, `rs_1m` 컬럼은 `5.555`를 받으므로 `sma5 = 5.555`와 `rs_1m = 11.0` 단언이 모두 RED.

## AC-RSR-009 — 종목 응답 `rs_1m` (REQ-RSR-012, 014) — 계획서 AC-3

- **Given** 임시 DB의 최신 주차에 종목의 `RS_12M_Rating`과 `RS_1M_Rating`이 서로 다른 값으로 있다
- **When** `/stage/overview`와 `/sectors/{name}/bubble`을 테스트 클라이언트로 호출한다
- **Then** 각 종목 항목에 `rs_1m`이 있고 그 값이 같은 주차 `RS_1M_Rating`과 같으며, `rs_12m`은 이전과 같은 이름·의미(`RS_12M_Rating`)로 남는다. `RS_1M_Rating` 행이 없는 종목의 `rs_1m`은 `null`이다
- **대조**: `rs_1m`에 `RS_12M_Rating`을 연결하면 RED(두 값이 다름). 필드를 빼면 응답 스키마 검사에서 RED. `RS_1M_Rating` 컬럼 자체가 유지됨은 AC-RSR-006의 스키마 단언이 맡는다.
- **양변 출처**: HTTP 응답 값 vs 픽스처에 심은 DB 값.

## AC-RSR-010 — 섹터 `rs_med` (REQ-RSR-013, 014) — 계획서 AC-4

- **Given** 구성 종목 5개씩인 섹터 P, Q의 RS가 P = `[10, 20, 30, 90, 100]`, Q = `[45, 48, 50, 52, 55]`이다(두 섹터 평균 모두 `50.0`). 별도 섹터 R은 P의 다섯 값에 RS 결측 종목 1개를 더한 6개 종목이다
- **When** 섹터 집계를 실행하고 `/sectors/ranking`과 봉투 `data[]`를 읽는다
- **Then** P: `rs_avg = 50.0`, `rs_med = 30.0`, `rs_top_pct = 40.0`. Q: `rs_avg = 50.0`, `rs_med = 50.0`, `rs_top_pct = 0.0`. R(결측 제외 구현): `rs_med = 30.0`, `rs_avg = 50.0`
- **대조**: `rs_med`를 평균으로 계산하면 P가 `50.0`(RED). 결측을 0으로 채우면 R이 `[0, 10, 20, 30, 90, 100]`의 중앙값 `25.0`이 되어 RED. `rs_avg`의 값이 바뀌면 `tests/test_ac_sag_030_rs_avg.py` 4건이 RED.
- **양변 출처**: 응답 값 vs 손으로 계산한 리터럴.

## AC-RSR-011 — 열기 배지 술어 (REQ-RSR-015, 016) — 두 언어

- **Given** `rs_1m` 값 `79.99`, `80`, `80.01`, `null`인 종목 4개
- **When** 종목 테이블과 종목 버블 툴팁을 렌더한다
- **Then** `80`, `80.01`만 열기 배지를 갖고(열기 배지 값의 출처는 주간 `RS_1M_Rating` — 응답의 `rs_1m`, spec.md §2.4 B-2), 배지의 title에 `RS_TOP_THRESHOLD` 값이 문자열로 들어 있다(상수 유래). 그리고 `rsMetrics.test.ts`가 `sector_metrics.py`에서 추출한 `_RS_TOP_THRESHOLD`와 `RS_TOP_THRESHOLD`가 수치로 같음을 단언한다(기존 `:44-47` 유지)
- **대조**: 술어를 `>`로 쓰면 `80`이 RED. 상수 대신 리터럴 `80`을 쓰면, 테스트에서 `RS_TOP_THRESHOLD`를 85로 주입(vitest `vi.mock('../../utils/rsMetrics')`)했을 때 `80.01`이 여전히 배지를 가져 RED. 결측을 높은 기본값으로 메우는 구현(`rs_1m ?? 100` 등)은 `null` 사례에서 RED. (JavaScript에서 `null >= 80`은 `false`이므로, 결측을 아무 처리 없이 비교하는 구현은 `null` 사례를 통과한다 — 이는 정상 동작과 결과가 같아 오구현으로 보지 않는다.)
- **monkeypatch 대상 심볼**: `frontend/src/utils/rsMetrics.ts` `RS_TOP_THRESHOLD`.
- **툴팁 검사 지점**: 버블 툴팁 formatter는 내보낸 함수가 아니라 `StockBubbleChart.tsx:361`의 ECharts 옵션 안 익명 함수다. 기존 테스트와 같은 방식으로 `vi.mock('echarts-for-react', …)`(`__tests__/StockBubbleChart.test.tsx:15`)로 옵션을 붙잡고 `option.tooltip.formatter(…)`를 직접 호출해 반환 HTML을 검사한다(같은 파일 `:369`, `:377` 선례). 종목 테이블은 `StockTable` 렌더 결과의 DOM을 검사한다.

## AC-RSR-012 — 섹터 테이블 중앙값·breadth 병기 (REQ-RSR-017)

- **Given** AC-RSR-010의 P, Q 응답을 주입한 `SectorRankingTable`
- **When** 렌더한다
- **Then** 헤더에 `RS Avg`, 중앙값 열, `RS 80+ 비중`이 인접 순서로 있고, P 행의 중앙값 셀이 `30`, Q 행이 `50`을 표시한다
- **대조**: 중앙값 열이 `rs_avg`를 읽으면 P가 `50`(RED). 열을 빼면 헤더 단언 RED.

## AC-RSR-013 — 임계값 단일 정의 지점 (REQ-RSR-019) — 계획서 AC-5

- **Given** M3에서 재보정한 Stage 2 상수(B-3: 70/60만 대상, `_RS_TOP_THRESHOLD` 80 유지)
- **When** 다음 정적 스캔과 테스트를 실행한다
  - `grep -n -E 'rs_12m\s*>=\s*[0-9]|RS Strong[^"]*[0-9]' backend/services/screen_service.py frontend/src/components/StockExplorer/StockTable.tsx`
  - `rsMetrics.test.ts`
- **Then** 스캔 결과 0줄. 변경 전 관측(2026-10-20, spec 0.3.1 정정 세션에서 위 명령을 그대로 실행, 종료코드 0) — 4줄:

  ```
  backend/services/screen_service.py:61:        " AND rs_12m >= 70"                              # T8
  frontend/src/components/StockExplorer/StockTable.tsx:32:  rs: boolean    // rs_12m >= 70
  frontend/src/components/StockExplorer/StockTable.tsx:39:    rs: c.rs_12m >= 70,
  frontend/src/components/StockExplorer/StockTable.tsx:263:                  <CheckDot pass={checklist.rs} label="RS Strong (≥ 70)" checkKey="rs" />
  ```

  네 줄 모두 REQ-RSR-019의 대상이다: `:61`(T8)과 `:39`는 상수 참조로, `:32` 주석은 상수 이름(`RS_STRONG_THRESHOLD`)을 가리키도록, `:263` 라벨은 상수에서 끌어온 문자열(예: 템플릿 리터럴 안의 `${RS_STRONG_THRESHOLD}`)로 바뀐다. 이 형태들은 패턴에 걸리지 않는다 — 비교식 오른쪽이 숫자가 아니고(`rs_12m >= {상수}`·`rs_12m >= RS_STRONG_THRESHOLD`), 라벨의 `RS Strong` 뒤부터 닫는 큰따옴표 전까지 숫자가 없기 때문이다(템플릿 리터럴의 상수 이름에는 숫자가 없다). 같은 줄의 `"Vol Surge (ratio ≥ 1.5)"`(`:262`)는 `RS Strong` 접두가 없어 걸리지 않는다. 패턴 자체 검증(정정 세션 scratchpad): 위 준수 형태 4줄 + `Vol Surge` 줄로 만든 가짜 파일은 0줄(종료코드 1), `RS Strong ≥ 70`·`RS Strong (>= 70)`·`RS Strong (≥ 65)`·`// rs_12m >=70`으로 만든 위반 가짜 파일은 4줄 모두 검출(plan-audit review-5 N2 반영 후 패턴, 오케스트레이터 재측정). 라벨 쪽 패턴은 괄호·기호 형태와 무관하게 `RS Strong` 뒤의 숫자를 잡는다. `rsMetrics.test.ts`가 `RS_STRONG_THRESHOLD`·`RS_S2_STRONG_THRESHOLD`를 `stage_classifier.py`에서 추출한 `_STAGE2_ENTRY_RS_MIN`·`_STAGE2_RS_STRONG`과 수치로 비교한다(현재 `:50-54`의 리터럴 단언을 대체). 또한 `_RS_TOP_THRESHOLD == 80.0`과 `RS_TOP_THRESHOLD === 80`이 변경 후에도 유지된다(REQ-RSR-022)
- **대조**: 거울 상수 하나만 바꾸고 백엔드를 그대로 두면 교차 언어 테스트가 RED. 코드 리터럴·주석·라벨 중 하나라도 숫자로 남기면 스캔이 1줄 이상(RED) — 패턴이 숫자를 특정하지 않으므로 재보정 값(예: `65`)을 숫자로 다시 적어 넣는 구현도 잡는다. `_RS_TOP_THRESHOLD`를 80 외의 값으로 바꾸면 유지 단언이 RED.
- **grep 종료코드 규약**: 0줄이면 `grep` 종료코드는 1이다. 판정은 출력 줄 수로 한다.
- **소유권 정리(D13)**: `rsMetrics.test.ts:50-54`는 70/60을 `SPEC-SECTOR-DISPLAY-UNIFY-001` REQ-SDU-003의 프론트 소유 상수로 단언한다. 이 SPEC은 소유권을 옮기지 않고 값만 양쪽에서 함께 바꾸며, 리터럴 단언을 백엔드 추출 비교로 바꾸는 것은 값 동일성을 기계로 지키기 위한 것이다. `screen_service.py:61`(T8)은 `_STAGE2_ENTRY_RS_MIN`을 참조하도록 바뀐다(spec.md §2.4 D13).

## AC-RSR-014 — 프로덕션 경로 잔존율 (REQ-RSR-020) — 계획서 AC-2

- **Given** M2에서 `scripts/rs_eval/stock_rs_eval.py`에 추가한 프로덕션 모드와 `--db <경로>` 인자(현재 DB 경로는 `:9`에 하드코딩), 그리고 DB 사본 `Output/snapshots/weekly_before_rsr.db`(재생성 전), `Output/snapshots/weekly_after_rsr.db`(재생성 후). 프로덕션 모드는 점수만 `relative_strength.RS_12M_Rating`으로 바꾸고 유니버스 규칙 — ISO 주차 마지막 날짜(`:19-21`), `dates[52:-H]`(`:71`), 날짜당 200종목 이상(`:74`), 점수 ≥ 90을 상위 10%로(`:76`), `tv20 >= 5e9`(`:99`) — 은 그대로 쓴다. 점수는 50억 유니버스 안에서 `rank(pct=True)*100`으로 다시 매긴다
- **When** 다음 두 명령을 실행한다
  - `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db Output/snapshots/weekly_before_rsr.db`
  - `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db Output/snapshots/weekly_after_rsr.db`
- **Then** 재생성 후 사본의 `상위10_지속률`이 `60` 이상이다. 재생성 전 사본의 값은 기준선으로 기록하며, 계획서의 31%와 ±3%p 안에 들 것으로 예상한다. 벗어나면 실패로 보지 않고 값과 원인 가설을 기록한다(research.md R9.1 — 현행 산식은 분모 의존이라 프로덕션 경로 값이 스크립트 재계산 값과 다를 수 있다). 두 값과 명령은 progress.md에 기록한다
- **기계적 독립성 확인**: 프로덕션 모드의 점수 함수는 시그니처상 `relative_strength`에서 읽은 등급 열만 받는다. 그리고 `grep -cE "RS_(1|3|6|9|12)M\b" <프로덕션 모드 점수 함수 본문>`이 `0`이다(원시 수익률 컬럼으로 산식을 재계산하지 않음)
- **대조**: 재생성 전 사본(현행 산식)은 같은 명령에서 60 미만이어야 한다(기준선 자체가 대조 관측). 프로덕션 모드가 원시 컬럼으로 IBD식을 재계산하도록 바꾸면 위 grep이 1 이상이 되어 RED.
- **양변 출처**: 프로덕션 테이블에서 읽은 등급 vs 고정 임계값 60.

## AC-RSR-015 — Stage 2 상수 재보정 (REQ-RSR-018)

- **Given** DB 사본 `Output/snapshots/weekly_before_rsr.db`, `Output/snapshots/weekly_after_rsr.db`와 주차 집합 W = 두 사본에 모두 있는 기준 종목(`삼성전자`) 날짜 중 최근 12개. 측정 명령은 `scripts/rs_eval/stage2_ratio_eval.py --db <경로> --weeks 12 --mode {conditional|strong} --threshold <값>`이며, `my_chart.analysis.stage_classifier`의 상수를 인자값으로 바꾼 뒤 프로덕션 함수(`_load_stocks_for_classification`, `classify_stage`, `classify_all`)를 호출한다. 두 기준의 분모는 가격 테이블로 정해지는 종목 집합이라 두 사본에서 같다
- **When / Then — (a) 조건부 RS 통과율(`--mode conditional`)**
  - 정의: 날짜 `d`에서 RS 외 진입 조건 다섯 개(Stage 2 분류 `:265-267`, `Close > SMA10` `:278-280`, `SMA10 > SMA40` `:282-284`, 거래량 배수 `:286-288`, `CHG_1M > 0` `:294-296`)를 모두 통과한 종목 중 `RS_12M_Rating >= 임계값`인 비중의 W 평균
  - 1단계(판별력 사전 조건, 두 사본): 변경 전 사본과 변경 후 사본 **각각**에서 임계값 60·70·80의 값 `c60`, `c70`, `c80`을 측정·기록하고, 사본마다 `c60 > c70 > c80`이면서 `c60 − c80 > 0.10 × c70`인지 판정한다. **두 사본 중 하나라도** 충족하면 2단계로 간다. 둘 다 충족하지 않으면 (a)는 판별력이 없으므로 **70은 "기록만"**: 상수를 70으로 유지하고 두 사본의 `c60`·`c70`·`c80`을 기록한 뒤, `|c70(변경 후) − c70(변경 전)| <= 0.10 × c70(변경 전)`을 단언한다. 이 단언이 성립하면 이 AC의 (a)는 충족된다. 성립하지 않으면 (a)는 PASS도 FAIL도 선언하지 않고 측정값과 함께 사용자에게 에스컬레이션한다(blocker 보고, plan-audit iter-3 부채 T1)
  - **대조(1단계)**: 사전 조건을 변경 전 사본에서만 판정하는 구현은, 변경 후 사본만 충족하는 경우(아래 plan 단계 예측이 바로 그 경우다) 2단계를 건너뛰어 RED — 기록에 변경 후 사본의 판정이 없으면 이 AC는 미충족이다. "기록만" 모드에서 변경 후 c70이 상대 ±10%를 벗어났는데 70을 유지하고 PASS를 선언하면 RED(에스컬레이션 누락)
  - 2단계(사전 조건 충족 시): `|변경 후·채택 값 − 변경 전·70 값| <= 0.10 × 변경 전·70 값`
  - **대조(2단계)**: 사전 조건이 `c60 − c80 > 0.10 × c70`을 요구하므로, 채택값 대신 80(또는 60)을 넣으면 측정값이 허용오차 밖으로 나갈 수 있는 판별 폭이 확보된다. 이 경우 변경 후 사본에서 80으로 측정한 값이 허용오차 밖임을 함께 기록한다(RED 관측)
  - **plan 단계 예측**: 현재 라이브 DB 사본(변경 전 사본에 해당)에서 `c60 = 100.00`, `c70 = 99.48`, `c80 = 97.85`(research.md R15) — 단조는 성립하나 폭 2.15%p < 9.95%p로 사전 조건 미충족. plan-audit iter-3의 변경 후 사본 모의(감사 측정, 재실행하지 않음)는 `99.58 / 94.42 / 84.87`로 폭 14.71 > 9.44여서 충족 — 따라서 M3에서도 같은 결과면 (a)가 적용되어 2단계로 가며, 70 유지 시 `|94.42 − 99.48| = 5.06 <= 9.948`로 허용오차 안이다. 이 예측들은 판정이 아니며, M3의 두 사본 측정이 판정을 대신한다
- **When / Then — (b) Stage 2 강세 비중(`--mode strong`)**
  - 정의: `classify_all(db, d)` 결과 중 `stage == 2`인 종목에서 `detail == "Stage 2 Strong"`인 비중의 W 평균(분모는 Stage 판정이 RS를 쓰지 않으므로 두 사본에서 같은 집합)
  - (1) 변경 전·현행 60, (2) 변경 후·현행 60, (3) 변경 후·채택 값을 측정하고, (3)이 (1)과 ±5%p 이내다(plan-audit iter-2 실측 기준선 33.53%)
  - **대조**: 채택 값이 60과 다르면 (2)와 (3)의 차이는 0이 아니어야 한다(0이면 바꿀 근거가 없어 RED). 60을 유지하면 (2)가 (1)과 ±5%p 이내여야 한다 — (2)가 범위 밖인데 60을 유지했다면 RED
- 두 기준의 모든 측정값·명령·채택 상수는 progress.md에 기록한다. (a)는 사본마다 W의 날짜별 RS 외 조건 통과 종목 수(분모 크기)를 W 평균 옆에 함께 기록한다 — 분모가 날짜별 수십 개 수준(research.md R15: 12~54개)이라 상대 ±10%가 종목 몇 개의 차이에 해당함을 판정 독자가 볼 수 있게 하기 위해서다(plan-audit iter-3 부채 T2)

## AC-RSR-016 — 섹터 종합 점수 가중치 불변 (REQ-RSR-021) — 계획서 AC-6

- **Given** 신설 고정 테스트: `from my_chart.analysis.sector_metrics import _COMPOSITE_WEIGHTS`
- **When** 테스트와 `composite_score`를 다루는 기존 7개 파일(research.md R8)을 실행한다
- **Then** `_COMPOSITE_WEIGHTS == {"1w": 0.30, "1m": 0.40, "3m": 0.30}`이고 기존 7개 파일의 테스트가 변경 전후 모두 같은 결과로 통과한다
- **대조**: 가중치 하나를 바꾸면 신설 테스트가 RED. 기존 테스트에는 가중치 상수를 직접 고정하는 테스트가 없었으므로(`grep -rn "_COMPOSITE_WEIGHTS" tests backend/tests` → 0건) 신설이 필요하다.

---

## AC-RSR-017 — 짝이 있는 낡은 행 제거 (REQ-RSR-001, 004)

- **Given** 임시 DB에서 기준 종목을 `S1`으로 지정하고(`monkeypatch.setattr("my_chart.db.weekly.REFERENCE_STOCK", "S1")`), 날짜 `d1`, `d2`에 일반 종목 `S1`~`S4`의 가격 행이 있다. `relative_strength`에는 이전 실행이 남긴 낡은 행 세 종류를 미리 넣는다: (a) `stock_prices`에도 `d1` 행이 있는 `KOSPI`의 `d1` 행; (b) `d2`에 거래량 0으로 바뀐 종목 `Z`의 `d2` 행(`Z`의 `stock_prices` `d2` 행 `Volume = 0`); (c) `S1`에는 없지만 `S2`의 `stock_prices` 행이 있는 비기준 날짜 `dN`의 `S2` 행
- **When** `generate_rs_db()`를 실행한다
- **Then** 세 행이 모두 없다: `SELECT COUNT(*) FROM relative_strength WHERE (Name='KOSPI' AND Date=d1) OR (Name='Z' AND Date=d2) OR Date=dN` → `0`. 그리고 남은 행은 모두 이번 실행이 쓴 `(Name, Date)`다
- **대조**: (i)·(ii)를 빼고 그 자리에 짝 기준 삭제(`stock_prices` 짝이 없는 행만 삭제)를 넣으면, 세 행은 모두 짝이 있으므로 살아남아 같은 질의가 `3`(RED). 잡는 오구현: "짝 없는 행만 지우면 충분하다"는 구현.
- **양변 출처**: 프로덕션 실행 후 테이블 질의 vs 픽스처에 심은 낡은 행 수(3).
- **라이브 단계(M2 재생성 후)**: 변경 전 관측 — 짝 있는 지수 행 600, 짝 있는 거래량 0 행 16,369, 비기준 날짜의 짝 있는 행 5(research.md R2.1). 재생성 후 세 질의 모두 `0`.

## AC-RSR-018 — 결측 수익률 행 (REQ-RSR-023)

- **Given** 임시 DB의 한 날짜에 정상 종목 4개, `RS_12M`만 NULL인 신규 상장 종목 `Y`(다른 컬럼은 채워짐), `RS_*`는 모두 있고 `SMA40_Trend_4M`만 NULL인 종목 `W`가 있다
- **When** `generate_rs_db()`를 실행한다
- **Then** `Y`와 `W`의 `relative_strength` 행이 없고, 정상 종목 4개의 `RS_1M_Rating`은 4개만으로 계산한 백분위와 같다. `Y`는 `rs_1m`이 없으므로 열기 배지 대상이 아니다
- **대조**: 결측 분기를 0으로 채우거나 있는 분기만으로 IBD 점수를 계산해 `Y`에 등급을 주면 `Y`의 행이 생겨 RED. `dropna`를 `RS_*` 다섯 컬럼으로 좁히는 변경은 두 번째 픽스처 종목 `W`(`RS_*`는 모두 있고 `SMA40_Trend_4M`만 NULL — 라이브의 `명인제약`과 같은 형태, research.md R3.1)가 행을 갖게 되어 RED. 따라서 Then에 "`W`의 행도 없다"를 함께 단언한다.

## §D.1 엣지 케이스

- 분모 필터 후 한 날짜의 종목이 0개 — 현행처럼 그 날짜를 건너뛴다(`weekly.py:433`). 행을 기록하지 않는다.
- 최신 주차에 `RS_1M_Rating`이 있으나 `RS_12M_Rating` 계산이 REQ-RSR-007로 제외된 종목 — 같은 행 전체가 분모에서 빠지므로 두 값 모두 없다. `rs_1m`, `rs_12m` 모두 null/미기록.
- 섹터 구성 종목 중 유효 RS 0개 — `rs_med` 결측(봉투 `MetricValueModel`의 결측 표현).

## §D.2 품질 게이트

- 신규·수정 Python 코드 테스트 커버리지 85% 이상(`quality.yaml` `test_coverage_target: 85`)
- `ruff` 신규 경고 0, 프론트 `tsc --noEmit`·`eslint` 신규 오류 0 (변경 전 기준선과 비교)
- 프론트 테스트는 `npm --prefix frontend run test -- --root frontend` 형태로 실행한다(저장소 루트에서 실행하면 `.claude/worktrees` 테스트까지 수집됨 — 프로젝트 메모리)

## §D.3 Definition of Done

- AC-RSR-001~018(008b 포함) 전부 PASS, 각 AC의 대조 RED를 run 단계 증거(progress.md §E.2)에 명령과 출력으로 기록
- 라이브 DB 단계(AC-RSR-001·002·007·014·015·017) 관측값 기록
- plan.md §B 결정 3건(2026-10-20 해소)이 구현에 반영됨
- dev 서버 재시작 후 종목 테이블·버블·섹터 테이블 화면 확인
