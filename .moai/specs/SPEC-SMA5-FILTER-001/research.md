# SPEC-SMA5-FILTER-001 Research — SMA5 지표 추가 및 ChartGrid 필터 노출

> 본 문서는 구현 전 코드베이스 심층 분석 결과다. 모든 변경 지점은 `경로:라인` 형식으로 검증되었다.
> 분석 일자: 2026-05-25 / 분석 대상 커밋: `chore/integrated-main-merge-2026-04-25` 브랜치 작업 트리.

---

## 1. 목표 요약

일봉 DB(`Output/stock_data_daily.db`, 테이블 `stock_prices`)에 **5일 단순이동평균(SMA5)** 값 컬럼과 **이격도 컬럼 FromSMA5(%)** (DB 컬럼명 `FromSMA5`)를 추가하고, 이를 ChartGrid 스크리닝 필터(PatternBuilder)에서 선택 가능한 지표로 노출한다.

기존 `FromEMA10 / FromEMA20 / FromSMA50 / FromSMA200` 패턴을 그대로 미러링한다.

---

## 2. 핵심 아키텍처 발견 (필수 반영)

### 2.1 스크리닝 필터는 `stock_prices`를 직접 조회하지 않는다 — `stock_meta` 스냅샷을 조회한다 [CRITICAL]

스크리닝 필터는 `stock_prices`가 아니라 denormalized 스냅샷 테이블 `stock_meta`를 대상으로 SQL을 실행한다.

- `backend/services/screen_service.py:23-33` — `_INDICATOR_COLUMN` 딕셔너리가 Pydantic Literal 지표명을 실제 `stock_meta` 컬럼명으로 매핑한다 (예: `"SMA50" -> "sma50"`).
- `backend/services/screen_service.py:118-129` — `PatternCondition`의 `col_a {op} {col_b} * ?` WHERE 절을 `_INDICATOR_COLUMN` 매핑값으로만 구성한다 (SQL injection 차단을 위해 컬럼명은 절대 사용자 입력에서 가져오지 않음).
- `backend/services/screen_service.py:171-178` — `SELECT ... FROM stock_meta WHERE {where_sql}` 실행.

**결론**: SMA5 필터가 실제로 **동작하려면** `stock_meta` 테이블에 `sma5` 컬럼이 반드시 존재해야 한다. 따라서 `backend/services/meta_service.py` 변경은 **선택이 아니라 필수(REQUIRED)** 다.

현재 `_INDICATOR_COLUMN`에 등록된 지표(9개): `Close, Open, High, Low, EMA10, EMA20, SMA50, SMA100, SMA200`. (참고: `stock_prices`에는 `SMA21`, `EMA65`가 존재하지만 스크리닝 화이트리스트에는 등록되어 있지 않다. 이는 본 SPEC 범위 밖이며 SMA5만 추가한다.)

### 2.2 `CREATE TABLE IF NOT EXISTS`는 기존 테이블을 변경하지 않는다 → 멱등 ALTER가 필수

- `my_chart/db/daily.py:54-73` — `_ensure_daily_table()`의 `CREATE TABLE IF NOT EXISTS stock_prices (...)`는 **테이블이 이미 존재하면 아무 일도 하지 않는다**. 따라서 새 컬럼을 CREATE 문에 추가하는 것만으로는 기존 30컬럼 DB에 컬럼이 추가되지 않는다.
- `my_chart/db/daily.py:81-87` — 누락 컬럼 멱등 추가 루프:
  ```python
  for col in ("SMA100", "RS_Line", "SMA150", "LOW_52W", "SMA200_20D_AGO"):
      if col not in existing_cols:
          conn.execute(f"ALTER TABLE stock_prices ADD COLUMN {col} REAL")
  ```
  여기에 `"SMA5"`, `"FromSMA5"`를 추가하지 않으면, 기존 30컬럼 DB를 상대로 32요소 `INSERT OR REPLACE INTO stock_prices VALUES (...)`가 컬럼 수 불일치로 실패한다. (전체 재생성 정상 경로의 belt-and-suspenders 방어선.)

### 2.3 위치 기반 executemany — 컬럼 순서 정합성이 깨지면 무음 데이터 오염 [HIGH RISK]

`my_chart/db/daily.py`는 `INSERT OR REPLACE INTO stock_prices VALUES (?,?,...)` (라인 272, 282) 형태의 **위치 기반(positional) executemany**를 사용한다. 컬럼명을 명시하지 않으므로 다음 3개 지점의 순서가 정확히 일치해야 한다:

1. `_DAILY_COLS` 튜플 (라인 32-42) — placeholder 개수 산출 기준 (라인 253: `placeholders = ", ".join(["?"] * len(_DAILY_COLS))`).
2. `CREATE TABLE` 컬럼 정의 (라인 56-73) — 실제 테이블 컬럼 순서.
3. `rows.append((...))` 값 튜플 (라인 182-213) — 삽입되는 값의 순서.

세 지점 중 하나라도 SMA5/FromSMA5를 다른 위치에 넣으면 **무음 컬럼 시프트 데이터 오염**이 발생한다. (예: `SMA5` 위치에 `FromSMA5` 값이 들어가도 SQLite는 오류를 내지 않는다 — 둘 다 REAL이므로.)

마찬가지로 `meta_service.py`의 SELECT(`stock_prices`에서 읽기)와 INSERT(`stock_meta`에 쓰기)도 위치 정합성을 지켜야 한다.

---

## 3. 검증된 변경 지도 (plan.md 작업 분해의 근거)

### 3.1 DB 계층 — `my_chart/db/daily.py`

| 지점 | 라인 | 현재 상태 | 변경 |
| --- | --- | --- | --- |
| `_DAILY_COLS` 튜플 | 32-42 | 30개 엔트리 | `"SMA5"`를 `EMA20`(pos 12) 뒤 / `SMA21`(pos 13) 앞에 삽입, `"FromSMA5"`를 `FromEMA20`(pos ~21) 뒤 / `FromSMA50` 앞에 삽입 → 32개 엔트리. (주기 정렬 일관성) |
| `CREATE TABLE` | 56-73 | 30컬럼 | `SMA5 REAL`, `FromSMA5 REAL`을 **동일 위치**에 추가 |
| 멱등 ALTER 루프 | 81-87 | `("SMA100","RS_Line","SMA150","LOW_52W","SMA200_20D_AGO")` | 튜플에 `"SMA5"`, `"FromSMA5"` 추가 [REQUIRED] (§2.2) |
| 지표 계산 블록 | 128-136 | 다른 rolling mean들과 나란히 | `price["SMA5"] = price["Close"].rolling(window=5).mean()` 추가 |
| 이격도 계산 블록 | 148-152 | `FromEMA10/20/SMA50/200(%)` | `price["FromSMA5(%)"] = (price["Close"] - price["SMA5"]) / price["SMA5"] * 100` 추가 |
| INSERT 값 튜플 | 182-213 | 30개 값 | `float(r["SMA5"])`, `_to_float_or_none(r["FromSMA5(%)"])` 또는 `float(r["FromSMA5(%)"])`를 일치하는 위치에 추가 → 32개 값 |

**참고 — 기존 패턴**: 다른 `From*(%)` 컬럼들은 모두 `float(r["FromEMA10(%)"])` 처럼 `float()` 직접 변환을 사용한다 (라인 203-206). 따라서 `FromSMA5(%)`도 동일하게 `float()`로 변환하는 것이 일관성에 부합한다. 단, SMA5 자체는 5일 미만 종목에서 NaN이 가능하므로 NULL 처리 검토가 필요하다 (§5 에지케이스 참조).

### 3.2 DB 재생성 진입점 (in-place 백필 없음, 전체 재생성)

- 트리거: HTTP `POST /api/db/update` (`backend/routers/db.py:20`)
  → `backend/services/db_service.py:_run_update` (라인 59-99)
  → Phase 3 `price_daily_db()` (`db_service.py:81`, `my_chart/db/daily.py`)
  → Phase 4 `rebuild_stock_meta()` (`db_service.py:89`, `meta_service.py`)
- 데이터 소스: 네이버 API `price_naver()` (`my_chart/price.py`, `daily.py:24`에서 import, `daily.py:119`에서 호출).
- 사용자 관점 재생성 절차: 기존 DB 파일 삭제 후 `POST /api/db/update` 실행 (SPEC-MINERVINI-001 v1.0.2에서 채택한 "파일 교체" 정상 경로와 동일).

### 3.3 백엔드 스키마 — `backend/schemas/screen.py`

| 지점 | 라인 | 변경 |
| --- | --- | --- |
| `IndicatorName` Literal | 12 | `"SMA5"` 추가 [REQUIRED] |
| `StockItem` 응답 모델 | 46-73 | `sma5: float | None = None` 추가는 **선택(OUT OF SCOPE)** — 그리드 표시할 때만 필요 |

### 3.4 백엔드 스크리닝 — `backend/services/screen_service.py`

| 지점 | 라인 | 변경 |
| --- | --- | --- |
| `_INDICATOR_COLUMN` 딕셔너리 | 20-33 | `"SMA5": "sma5"` 추가 [REQUIRED]. 추가 후 패턴 평가(118-129)가 SMA5를 타입 안전하게 자동 처리 |
| `screen_stocks()` SELECT | 171-178 | 응답 표시를 추가할 때만 `sma5`를 SELECT에 포함 (OUT OF SCOPE). WHERE 절은 `stock_meta.sma5`를 참조 → 그래서 `stock_meta.sma5`가 필수 |

### 3.5 백엔드 메타 — `backend/services/meta_service.py` [필터 동작에 필수]

| 지점 | 라인 | 변경 |
| --- | --- | --- |
| `_STOCK_META_DDL` | 20-49 | `sma5 REAL` 추가 (일관성을 위해 `ema20` 뒤) [REQUIRED] |
| `_rebuild` daily SELECT (stock_prices에서) | 159-174 | SMA5를 컬럼 목록에 추가. `has_minervini_price_cols` 분기 양쪽(라인 160-166 신규 경로 / 168-174 레거시 경로) 모두 고려 |
| `daily_by_name` 인덱스 매핑 | 175-177, 273-275 | 신규 컬럼 추가 시 위치 인덱스 주석/오프셋 갱신 |
| `_rebuild` INSERT 값 튜플 | 279-306 | `sma5` 값을 일치하는 위치에 추가. 위치 정합성 유지 |
| `INSERT ... VALUES (?,?,...)` placeholder | 310-311 | 현재 26개 `?` → sma5 추가 시 27개로 증가 |

**주의**: `meta_service.py`의 SELECT에 SMA5를 추가하면 `daily_by_name` 튜플의 인덱스가 시프트된다. Minervini 컬럼(`d[8]/d[9]/d[10]`)을 `len(d) > N` 가드로 읽는 코드(라인 303-305)가 있으므로, SMA5 삽입 위치에 따라 이 인덱스를 재계산해야 한다. SMA5를 SELECT 목록 **끝**(SMA200_20D_AGO 뒤)에 추가하면 기존 인덱스를 보존할 수 있어 시프트 위험이 가장 낮다 — 단 DDL/INSERT 위치와의 정합성은 별도로 맞춰야 한다. (plan.md에서 단일 일관 위치 결정.)

### 3.6 프론트엔드

| 지점 | 라인 | 변경 |
| --- | --- | --- |
| `frontend/src/types/filter.ts` `IndicatorName` union | 3-12 | `| 'SMA5'` 추가 [REQUIRED] |
| `frontend/src/components/FilterBar/PatternBuilder.tsx` `INDICATORS` 배열 | 5-8 | `'SMA5'` 추가 [REQUIRED]. 라벨은 raw 영문 렌더("SMA50" 등) → SMA5는 "SMA5"로 표시. 한글 라벨은 OUT OF SCOPE |
| `frontend/src/types/stock.ts` `StockItem` | (해당 시) | `sma5` 추가는 **선택(OUT OF SCOPE)** — 그리드 표시 전용. 현재 `filter.ts`의 StockItem(라인 40-58)에도 `sma5` 미존재 |

---

## 4. 테스트 영향 분석 (TDD 타깃)

### 4.1 기존 테스트 수정 필요

| 파일:라인 | 현재 단언 | 변경 |
| --- | --- | --- |
| `tests/test_daily.py:22-26` | `assert len(_DAILY_COLS) == 27` — **이미 실패 중** (실제 30; Minervini 컬럼 추가 후 stale) | `== 32`로 갱신 (사전 존재 불일치, 본 변경으로 32 확정) |
| `tests/test_daily.py:44-49` | `expected_indicators = ("EMA10","EMA20","SMA21","SMA50","EMA65","SMA100","SMA200")` | `"SMA5"` 추가 |
| `tests/test_screen_service.py:239-244` | `test_indicator_column_map_covers_all_whitelist_values`가 `get_args(IndicatorName)`를 순회하며 각 값이 `_INDICATOR_COLUMN`에 있는지 단언 | `IndicatorName` Literal에 `"SMA5"`만 추가하고 `_INDICATOR_COLUMN`에 매핑을 안 넣으면 **이 테스트가 실패** → 두 편집이 반드시 함께 착지해야 함 |

### 4.2 영향 없음 확인 (회귀 없음)

| 파일:라인 | 사유 |
| --- | --- |
| `frontend/.../PatternBuilder.test.tsx` (전체) | "조건 추가" 버튼 한도(5) 동작만 테스트, 옵션 개수는 단언하지 않음 → SMA5 추가 영향 없음 |
| `backend/tests/test_minervini_template.py:82-191` | 테스트가 자체 stock_meta DDL/INSERT를 정의(26컬럼). 프로덕션 `_STOCK_META_DDL`과 독립적이므로 프로덕션에 sma5 추가해도 이 테스트는 깨지지 않음 |
| `backend/tests/test_minervini_template.py:335-405` | 테스트가 자체 stock_prices DDL을 정의(SMA5 미포함). 프로덕션 daily.py CREATE TABLE과 독립적 → 영향 없음 |
| `backend/tests/test_sector_advanced.py`, `test_sector_detail_service.py` | 자체 stock_meta DDL을 정의하며 sma5 미참조 → 영향 없음 |

### 4.3 신규 테스트 (TDD RED 타깃)

1. **SMA5 계산 정확성**: `_fetch_daily_stock` 반환 행의 SMA5가 Close의 5기간 rolling mean과 일치.
2. **FromSMA5(%) 공식 정확성**: `(Close - SMA5) / SMA5 * 100`.
3. **stock_meta.sma5 존재**: rebuild 후 `PRAGMA table_info(stock_meta)`에 `sma5` 포함.
4. **SMA5 PatternCondition 동작**: `PatternCondition(indicator_a="Close", operator="gt", indicator_b="SMA5")`가 유효한 WHERE 절(`close > sma5 * ?`) 생성 / 스크리닝 결과 반환.
5. **프론트 PatternBuilder SMA5 옵션 렌더**: `INDICATORS`에 SMA5 포함, 드롭다운 옵션 "SMA5" 렌더.
6. **컬럼 정합성 게이트** (§2.3): `len(row tuple) == len(_DAILY_COLS)` (기존 `tests/test_daily.py:155-180`이 커버) + 명시적 컬럼명↔값 정렬 검사.

---

## 5. 에지케이스

- **상장 5거래일 미만 종목**: `Close.rolling(window=5).mean()`는 처음 4개 행에서 NaN을 반환. 따라서 SMA5는 NaN/NULL이 정상. 기존 `_to_float_or_none` 패턴(`daily.py:169-177`)이 NaN→None(SQLite NULL) 변환을 담당. SMA5/FromSMA5의 NULL 처리가 이 패턴과 일치하는지 검증 필요.
- **FromSMA5(%) 0 division**: SMA5가 0이거나 NaN이면 `FromSMA5(%)`도 NaN/inf. `_sanitize_ohlc`(라인 100-109)가 0 Close를 제거하므로 정상 데이터에서 SMA5=0은 발생하지 않으나, NULL 전파 검증 필요.
- **stock_meta에 sma5 누락된 레거시 DB로 SMA5 필터 실행**: 현재 `screen_service.py`는 Minervini 컬럼만 PRAGMA 선검사(`_minervini_columns_available`, 라인 60-63). SMA5에는 동일 가드가 없으므로, sma5 미존재 시 `OperationalError`가 발생할 수 있다. 전체 재생성 정상 경로에서는 항상 sma5가 존재하므로 범위 밖이나, plan.md 리스크에 기록한다.

---

## 6. 리스크 요약

| 리스크 | 심각도 | 완화 |
| --- | --- | --- |
| 컬럼 순서 정합성 깨짐 (무음 데이터 오염) | HIGH | 3개 지점(daily.py) + 2개 지점(meta_service.py)에 동일 위치 적용. `len(row)==len(_DAILY_COLS)` 단위 테스트 + 컬럼명↔값 정렬 검사 |
| 멱등 ALTER 누락 시 기존 DB INSERT 실패 | HIGH | `daily.py:81-87` 루프에 SMA5/FromSMA5 추가 (REQUIRED) |
| `IndicatorName` Literal과 `_INDICATOR_COLUMN` 비동기 착지 | MEDIUM | `test_indicator_column_map_covers_all_whitelist_values`가 강제 — 두 편집 동시 착지 |
| `meta_service.py` daily SELECT 인덱스 시프트 | MEDIUM | SMA5를 SELECT 목록 끝에 추가하거나 인덱스 주석 재계산 (plan.md에서 단일 위치 확정) |
| 전체 DB 재생성 필요(런타임) | MEDIUM (운영) | 사용자에게 "기존 DB 삭제 + POST /api/db/update" 절차 명시 |

---

## 7. 결론

- `meta_service.py` 변경은 필터 동작에 **필수**다 (스크리닝이 `stock_meta`를 조회하기 때문, §2.1).
- 컬럼 순서 정합성이 본 변경의 최대 리스크다 (§2.3).
- `tests/test_daily.py:26`의 `== 27` 단언은 본 변경과 무관하게 이미 실패 중이며, 본 변경으로 `== 32`로 확정 갱신한다.
- 전체 DB 재생성이 데이터 마이그레이션 전략이다 (별도 백필 스크립트 없음).
</content>
</invoke>
