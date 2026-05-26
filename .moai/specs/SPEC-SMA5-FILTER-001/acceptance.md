# SPEC-SMA5-FILTER-001 Acceptance — 수용 기준

> development_mode: tdd. 각 시나리오는 RED 테스트로 작성 가능한 구체·검증 가능 기준이다.
> 시나리오 ID는 REQ-SMA5-NNN과 매핑된다.

---

## 1. Given/When/Then 시나리오

### AC-1 — SMA5 계산 정확성 (REQ-SMA5-002)

- **Given** 종가(Close)가 `[100, 102, 104, 106, 108]`인 5거래일 OHLCV DataFrame이 `price_naver`로 주어지고
- **When** `_fetch_daily_stock`이 지표를 계산하면
- **Then** 5번째 행의 SMA5 값은 `(100+102+104+106+108)/5 = 104.0`과 일치한다 (부동소수 허용오차 내).

### AC-2 — FromSMA5(%) 공식 정확성 (REQ-SMA5-002)

- **Given** 5번째 행에서 `Close=108`, `SMA5=104.0`이고
- **When** 이격도가 계산되면
- **Then** `FromSMA5(%)` 값은 `(108 - 104.0) / 104.0 * 100 = 3.846...`과 일치한다.

### AC-3 — stock_prices 컬럼 존재 및 정합 (REQ-SMA5-001)

- **Given** 일봉 DB 재생성이 완료되고
- **When** `PRAGMA table_info(stock_prices)`를 조회하면
- **Then** 컬럼 목록에 `SMA5`, `FromSMA5`가 존재하고, 각 일봉 행 튜플 길이는 `len(_DAILY_COLS) == 32`와 같다.

### AC-4 — stock_meta.sma5 존재 및 값 복사 (REQ-SMA5-003) [필터 동작 필수]

- **Given** SMA5가 포함된 일봉 `stock_prices`와
- **When** `rebuild_stock_meta()`가 실행되면
- **Then** `PRAGMA table_info(stock_meta)`에 `sma5`가 존재하고, 최신 일봉 날짜의 SMA5 값이 해당 종목의 `stock_meta.sma5`로 복사된다.

### AC-5 — SMA5 PatternCondition 서버사이드 평가 (REQ-SMA5-004)

- **Given** `stock_meta`에 `sma5` 컬럼과 데이터(예: 종목 A `close=110, sma5=100`)가 있고
- **When** `ScreenRequest`에 `PatternCondition(indicator_a="Close", operator="gt", indicator_b="SMA5", multiplier=1.0)`를 담아 `screen_stocks()`를 호출하면
- **Then** 생성된 WHERE 절은 `_build_where`가 패턴 절을 괄호로 감싸므로 정확히 `(close > sma5 * ?)` (params=[1.0]) 형태이고, `close > sma5`를 만족하는 종목 A가 결과에 포함된다. (단언은 정확 문자열 `(close > sma5 * ?)` 또는 정규화·부분문자열 비교로 수행. `screen_service.py:124,127-129` 참조 — 단일 패턴도 `({joiner.join(...)})`로 항상 외곽 괄호가 붙는다.)

### AC-6 — IndicatorName ↔ _INDICATOR_COLUMN 동기 (REQ-SMA5-004)

- **Given** `IndicatorName` Literal에 `"SMA5"`가 추가되고
- **When** `test_indicator_column_map_covers_all_whitelist_values`가 `get_args(IndicatorName)`를 순회하면
- **Then** 모든 값(SMA5 포함)이 `_INDICATOR_COLUMN`에 매핑되어 있어 단언이 통과한다.

### AC-7 — 프론트엔드 PatternBuilder SMA5 옵션 렌더 (REQ-SMA5-005)

- **Given** `INDICATORS` 배열에 `'SMA5'`가 추가되고
- **When** `PatternBuilder`가 렌더되면
- **Then** indicator_a / indicator_b 드롭다운에 raw 라벨 "SMA5" 옵션이 존재한다.

### AC-8 — 5거래일 미만 NULL 안전 (REQ-SMA5-006)

- **Given** 종가가 4행만 있는 OHLCV DataFrame이 주어지고
- **When** `_fetch_daily_stock`이 SMA5를 계산하면
- **Then** 모든 행의 SMA5는 NaN이고, 영속화 시 예외 없이 SQLite `NULL`(`_to_float_or_none`로 None 변환)로 저장된다.

### AC-9 — 컬럼명↔값 정렬 round-trip 게이트 (REQ-SMA5-001/002) [HARD, HIGH-risk 무음 오염 검출]

길이 단언(AC-3의 `len(row)==32`)만으로는 SMA5와 FromSMA5 값이 서로 swap된 위치에 들어가도 통과한다(둘 다 REAL). 따라서 **각 컬럼이 자기 값을 갖는지**를 명시 검증한다.

- **Given** SMA5 / FromSMA5 / SMA21 / SMA50 / FromSMA50 의 기대값이 모두 **서로 다르게(distinct)** 나오도록 설계된 소형 합성 price frame (예: 단조 증가하는 distinct Close 시퀀스로, 5일선·21일선·50일선과 각 이격도가 서로 다른 수치가 되게 함)이 daily insert 경로(`_fetch_daily_stock` → executemany)를 타고
- **When** 영속화된 `stock_prices` 행을 다시 `SELECT SMA5, FromSMA5, SMA21, SMA50, FromSMA50`으로 read-back 하면
- **Then** 각 컬럼은 **자신의 기대값**을 정확히 보유한다 (SMA5 == Close 5기간 평균, FromSMA5 == 이격도 공식값, SMA21/SMA50/FromSMA50 == 각자 기대값). 즉 어느 컬럼에도 다른 컬럼의 값이 침범하지 않았음 — 위치 swap이 없음을 증명한다.
- **And (stock_meta 정렬 검사)** `rebuild_stock_meta()` 실행 후 `stock_meta.sma5`는 최신 일자 `stock_prices.SMA5`와 **동일 값**이다 (meta_service.py SELECT/INSERT 위치 정합성 증명).

> 이 AC는 plan.md §1 확정 위치 (A)daily.py / (B)meta_service.py 의 정합성을 binary로 검출하는 유일한 테스트다. 구현은 plan.md Task 6 참조.

---

## 2. 에지케이스

| 케이스 | 기대 동작 |
| --- | --- |
| 상장 5거래일 미만 종목 | SMA5 = NaN → NULL. 예외 없음 (AC-8). |
| 정확히 5거래일 종목 | 5번째 행만 SMA5 유효, 1~4행은 NULL. |
| `_sanitize_ohlc`로 0 Close 제거된 종목 | 잔여 행 기준 rolling(5) 계산. SMA5=0 발생 안 함 (FromSMA5 inf/NaN 방지). |
| SMA5가 NULL인 행에 SMA5 패턴 적용 | SQLite NULL 비교는 결과에서 제외(NULL > x = NULL = false). 정상 동작. |
| 레거시 stock_meta(sma5 누락)로 SMA5 필터 | 전체 재생성 정상 경로 전제이므로 범위 밖. (research.md §5에 OperationalError 가능성 기록) |
| FromSMA5 컬럼만 추가하고 SMA5 누락 | 길이 게이트(AC-3, 컬럼 수)가 차단. |
| SMA5와 FromSMA5 값이 swap된 위치에 삽입 | 길이 게이트는 통과(32==32)하나 **AC-9 정렬 게이트가 차단** (각 컬럼이 자기 값을 보유하지 않음). |

---

## 3. 품질 게이트 (Quality Gates)

- **컬럼 정합성 게이트 [HARD]**: 2단계로 구성한다.
  1. 길이 검사: `len(row tuple) == len(_DAILY_COLS) == 32` (기존 `tests/test_daily.py:155-180`). 누락/초과를 검출하나 swap은 못 잡는다.
  2. **정렬 검사 (AC-9) [HARD]**: distinct 값 round-trip으로 각 컬럼이 자기 값을 보유하는지 단언 + `stock_meta.sma5 == stock_prices.SMA5`(최신일자) 단언. **이것이 무음 swap 오염을 검출하는 핵심 게이트다.** SMA5/FromSMA5 위치는 plan.md §1 확정 위치 (A)/(B)를 따른다.
- **Literal 동기 게이트 [HARD]**: `test_indicator_column_map_covers_all_whitelist_values` 통과 (AC-6).
- **테스트 커버리지**: 변경 모듈 85% 이상.
- **TRUST 5**: Tested(신규 6개 시나리오 RED→GREEN), Readable(한국어 주석/MX 태그), Unified(ruff/black), Secured(컬럼명은 화이트리스트 전용 — SQL injection 표면 없음), Trackable(conventional commit + SPEC-SMA5-FILTER-001 참조).
- **기존 테스트 회귀 없음**: `PatternBuilder.test.tsx`, `test_minervini_template.py`, `test_sector_*` 영향 없음 확인 (research.md §4.2).

---

## 4. Definition of Done

- [ ] REQ-SMA5-001~006 전부 구현 및 검증.
- [ ] `tests/test_daily.py:26` 단언 `== 32`로 갱신, 통과.
- [ ] `tests/test_daily.py:44-49` `expected_indicators`에 "SMA5" 추가, 통과.
- [ ] AC-1~AC-9 전 시나리오 테스트 통과.
- [ ] `stock_prices`에 SMA5/FromSMA5, `stock_meta`에 sma5 존재 (PRAGMA 확인).
- [ ] SMA5 PatternCondition으로 실제 스크리닝 결과 반환 (AC-5, 생성 WHERE = `(close > sma5 * ?)`).
- [ ] PatternBuilder 드롭다운에 "SMA5" 노출 (AC-7).
- [ ] 컬럼 정합성 게이트(길이 + **AC-9 정렬 round-trip**) + Literal 동기 게이트 통과.
- [ ] Exclusions 항목 미구현 확인 (주봉/그리드 표시/한글 라벨/차트 오버레이/백필 스크립트).
- [ ] 전체 DB 재생성 절차 문서화 (기존 DB 삭제 + POST /api/db/update).
</content>
