# SPEC-SMA5-FILTER-001 (Compact)

**SMA5 지표 추가 및 ChartGrid 필터 노출** — status: draft / priority: medium / mode: tdd / brownfield / issue: 0

## REQ 목록

- **REQ-SMA5-001** (Ubiquitous): `stock_prices`의 모든 일봉 행에 SMA5 / FromSMA5 저장.
- **REQ-SMA5-002** (Event-Driven): 일봉 DB 재생성 시 SMA5(Close 5기간 rolling mean)와 FromSMA5(%)=(Close-SMA5)/SMA5*100 계산·영속화.
- **REQ-SMA5-003** (Ubiquitous): `stock_meta`에 `sma5` 포함 [필터 동작 필수].
- **REQ-SMA5-004** (Event-Driven): SMA5 PatternCondition을 `stock_meta.sma5` 대상 파라미터 WHERE로 서버사이드 평가.
- **REQ-SMA5-005** (Ubiquitous): PatternBuilder 드롭다운에 raw "SMA5" 노출.
- **REQ-SMA5-006** (Unwanted): 5거래일 미만 종목은 SMA5/FromSMA5를 NULL로 안전 저장 (예외 없음).

## Acceptance (요약)

- AC-1 SMA5 = Close 5기간 평균 정확성 / AC-2 FromSMA5(%) 공식 / AC-3 stock_prices 컬럼+튜플 길이 32 / AC-4 stock_meta.sma5 존재+값복사 / AC-5 SMA5 패턴 → `(close > sma5 * ?)` (외곽 괄호 포함) 결과 반환 / AC-6 IndicatorName↔_INDICATOR_COLUMN 동기 / AC-7 PatternBuilder "SMA5" 옵션 / AC-8 5거래일 미만 NULL / **AC-9 컬럼명↔값 정렬 round-trip 게이트 (HIGH-risk swap 오염 검출)**.
- 품질 게이트: 컬럼 정합성(길이 `==32` + **AC-9 정렬 round-trip**) + Literal 동기 + 85% 커버리지.

## Files to Modify (체크리스트)

- [ ] `my_chart/db/daily.py` — 삽입 위치 [HARD, plan.md §1(A)]: SMA5 = EMA20 뒤/SMA21 앞, FromSMA5 = FromEMA20 뒤/FromSMA50 앞 (3개 지점 동일). `_DAILY_COLS`(32-42), CREATE TABLE(56-73), 멱등 ALTER 루프(81-87)[필수], 지표 계산(128-136), 이격도 계산(148-152), INSERT 튜플(182-213). 30→32 컬럼.
- [ ] `backend/services/meta_service.py` [필수] — 삽입 위치 [HARD, plan.md §1(B)]: sma5를 **끝에 append** (Minervini `d[8/9/10]` 인덱스 보존). `_STOCK_META_DDL`(20-49) 끝 sma5, stock_prices SELECT(159-174) 끝, daily_by_name 인덱스(175-177/273-275) → sma5=d[11], INSERT 튜플(279-306) 끝, placeholder(310-311) 26→27.
- [ ] `backend/schemas/screen.py:12` — `IndicatorName` Literal에 "SMA5".
- [ ] `backend/services/screen_service.py:20-33` — `_INDICATOR_COLUMN`에 `"SMA5": "sma5"`. (schema와 동시 착지 [HARD])
- [ ] `frontend/src/types/filter.ts:3-12` — `IndicatorName`에 `'SMA5'`.
- [ ] `frontend/src/components/FilterBar/PatternBuilder.tsx:5-8` — `INDICATORS`에 `'SMA5'`.
- [ ] `tests/test_daily.py:26` — `== 27` → `== 32` (사전 실패 중). `:44-49` expected_indicators에 "SMA5".
- [ ] `tests/test_screen_service.py` — SMA5 패턴 WHERE/스크리닝 테스트 추가.
- [ ] 신규 테스트: SMA5 계산, FromSMA5 공식, stock_meta.sma5, SMA5 PatternCondition, PatternBuilder SMA5 옵션, NULL 안전, **AC-9 컬럼명↔값 정렬 round-trip(daily 행 read-back + stock_meta.sma5==stock_prices.SMA5)**.

## 변경 없음 (EXISTING)

`backend/services/db_service.py`(59-99), `backend/routers/db.py:20`, `my_chart/price.py`, 주봉 전 파일.

## Exclusions

- 주봉 DB / 5주선.
- ChartGrid 결과 그리드에 SMA5 값 표시 (`StockItem.sma5`, `stock.ts`).
- 한글 라벨("5일선").
- 가격 차트 SMA5 오버레이 (`my_chart/charting/single.py`).
- 별도 in-place 백필 스크립트 (전체 재생성만).
- `stock_meta.sma5` 누락 전용 PRAGMA 가드.
</content>
