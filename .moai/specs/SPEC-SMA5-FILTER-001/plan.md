# SPEC-SMA5-FILTER-001 Plan — 구현 계획

> [DELTA] 마커 범례: `[EXISTING]` 변경 없는 기존 코드 / `[MODIFY]` 기존 파일 수정 / `[NEW]` 신규 추가.
> 본 SPEC은 BROWNFIELD 변경이며 development_mode: tdd (RED → GREEN → REFACTOR).

---

## 1. 기술 노트

- **DB 계층 (`my_chart/db/daily.py`)**: pandas `rolling(window=5).mean()`로 SMA5 계산. sqlite3 **위치 기반 executemany** 사용 → `_DAILY_COLS` / `CREATE TABLE` / 값 튜플 3개 지점 순서 정합성이 핵심 (research.md §2.3).
- **메타 계층 (`backend/services/meta_service.py`)**: `stock_meta`는 denormalized 스냅샷. 스크리닝이 직접 조회하는 테이블이므로 `sma5` 추가는 필수. DDL + stock_prices SELECT + INSERT 튜플 3개 지점 정합성.
- **스키마 (`backend/schemas/screen.py`)**: Pydantic v2 `Literal` 화이트리스트 — SQL injection 방어선. `IndicatorName`에 "SMA5" 추가.
- **스크리닝 (`backend/services/screen_service.py`)**: `_INDICATOR_COLUMN` 딕셔너리만 컬럼명을 제공. `"SMA5": "sma5"` 추가 시 패턴 평가가 자동 처리.
- **프론트엔드 (React/TS)**: `IndicatorName` union + `INDICATORS` 배열 동기 확장. 백엔드 Literal과 1:1 미러.
- **삽입 위치 확정 [HARD]**: 아래 위치는 권고가 아니라 **확정 결정**이다. 모든 정합 지점에서 정확히 이 위치를 사용한다. 두 파일의 위치가 **의도적으로 다름**에 주의한다 (사유는 각 항목에 명시).

  **(A) `my_chart/db/daily.py` — 주기 정렬 위치 (3개 지점 동일)**
  - `SMA5`: `EMA20` **바로 뒤**, `SMA21` **바로 앞** (`_DAILY_COLS`에서 index 13 — 기존 `EMA20`(idx 12)과 `SMA21`(현 idx 13 → 신규 idx 14) 사이).
  - `FromSMA5`: `FromEMA20` **바로 뒤**, `FromSMA50` **바로 앞**.
  - 동일 위치를 `_DAILY_COLS`(32-42) / `CREATE TABLE`(56-73) / INSERT 값 튜플(182-213) **3개 지점에 동일하게** 적용한다.
  - 사유: daily.py는 신규 테이블이므로 주기 오름차순 정렬이 가독성에 유리하고, 인덱스 시프트에 의존하는 다운스트림 가드가 없다.

  **(B) `backend/services/meta_service.py` — 끝에 append (의도적으로 daily.py와 다름)**
  - stock_prices daily SELECT(159-174 양쪽 분기): `sma5`를 SELECT 목록 **맨 끝**(`SMA200_20D_AGO` 뒤)에 추가한다. 따라서 `daily_by_name` 튜플에서 `sma5`는 **index 11** (기존 `d[8]=sma150 / d[9]=low52w / d[10]=sma200_20d_ago` 다음).
  - stock_meta DDL(20-49): `sma5 REAL`을 **테이블 정의 맨 끝**(`sma200_20d_ago` 뒤)에 추가한다.
  - stock_meta INSERT 값 튜플(279-306): `sma5` 값을 **튜플 맨 끝**에 추가한다. placeholder `?`(310-311) 26 → 27.
  - 사유 [HARD]: Minervini 가드가 `d[8]/d[9]/d[10]`을 위치로 읽으므로(meta_service.py:303-305), sma5를 SELECT 중간에 끼우면 이 인덱스가 시프트되어 무음 오염이 발생한다. 끝에 append하면 기존 인덱스가 보존된다. **이 위치는 변경 금지.**

---

## 2. 작업 분해 (파일별, [DELTA] 마커)

### Task 1 — [MODIFY] `tests/test_daily.py` (RED, DB 계층 테스트 선행)

- `tests/test_daily.py:22-26` — `assert len(_DAILY_COLS) == 27` → `== 32`로 갱신. (사전 존재 불일치: 실제 30, 본 변경으로 32 확정. research.md §4.1)
- `tests/test_daily.py:44-49` — `expected_indicators` 튜플에 `"SMA5"` 추가.
- [NEW] SMA5 계산 정확성 테스트: `_fetch_daily_stock` 반환 행의 SMA5 == Close 5기간 rolling mean.
- [NEW] FromSMA5(%) 공식 정확성 테스트.
- [NEW] 5거래일 미만 NULL 안전 테스트 (4행 입력 → SMA5 None) (REQ-SMA5-006).
- [EXISTING] `test_row_tuple_length_matches_daily_cols` (라인 155-180) — 자동으로 32 정합 검증. 변경 불필요.

### Task 2 — [MODIFY] `my_chart/db/daily.py` (GREEN, DB 계층 구현)

- `_DAILY_COLS` (라인 32-42): SMA5/FromSMA5 삽입 → 32 엔트리.
- `CREATE TABLE` (라인 56-73): `SMA5 REAL`, `FromSMA5 REAL`을 동일 위치에 추가.
- 멱등 ALTER 루프 (라인 81-87): 튜플에 `"SMA5"`, `"FromSMA5"` 추가 [REQUIRED, research.md §2.2].
- 지표 계산 (라인 128-136): `price["SMA5"] = price["Close"].rolling(window=5).mean()`.
- 이격도 계산 (라인 148-152): `price["FromSMA5(%)"] = (price["Close"] - price["SMA5"]) / price["SMA5"] * 100`.
- INSERT 값 튜플 (라인 182-213): `float(r["SMA5"])` 또는 NaN 가능성을 고려해 `_to_float_or_none(r["SMA5"])`, `float(r["FromSMA5(%)"])`를 일치 위치에 추가 → 32 값. (기존 `From*` 컬럼은 `float()` 직접 변환을 사용하나, SMA5는 5일 미만 NaN 가능 → `_to_float_or_none` 권장. plan.md GREEN 단계에서 REQ-SMA5-006 테스트로 결정.)

### Task 3 — [MODIFY] `tests/test_screen_service.py` + `backend/schemas/screen.py` + `backend/services/screen_service.py` (RED→GREEN, 함께 착지 [HARD])

- [RED] `tests/test_screen_service.py:239-244`의 `test_indicator_column_map_covers_all_whitelist_values`가 Literal과 매핑 동기화를 강제. SMA5 패턴 WHERE 생성/스크리닝 결과 테스트 추가 (REQ-SMA5-004).
- [MODIFY] `backend/schemas/screen.py:12` — `IndicatorName` Literal에 `"SMA5"` 추가.
- [MODIFY] `backend/services/screen_service.py:20-33` — `_INDICATOR_COLUMN`에 `"SMA5": "sma5"` 추가.
- [HARD] 두 편집을 함께 착지: Literal에만 추가하면 위 테스트가 실패 (research.md §4.1).
- [HARD] 테스트 경로 주의: 스크리닝 테스트는 **`tests/test_screen_service.py`**에 작성한다. 본 저장소에는 `tests/`와 `backend/tests/`가 **둘 다 존재**하지만 `test_screen_service.py`는 `tests/`에만 있다 (`backend/tests/test_screen_service.py`는 미존재). 잘못된 디렉터리에 신규 테스트를 만들지 말 것.

### Task 4 — [MODIFY] `backend/tests/test_minervini_template.py`(또는 신규) + `backend/services/meta_service.py` (RED→GREEN, 필터 동작 필수)

- [RED] [NEW] rebuild 후 `stock_meta`에 `sma5` 컬럼 존재 + 최신 일봉 SMA5 값 복사 테스트 (REQ-SMA5-003).
- [MODIFY] `backend/services/meta_service.py:20-49` — `_STOCK_META_DDL`에 `sma5 REAL` 추가.
- [MODIFY] `backend/services/meta_service.py:159-174` — stock_prices SELECT 양쪽 분기에 SMA5 추가.
- [MODIFY] `backend/services/meta_service.py:175-177, 273-275, 279-306` — `daily_by_name` 인덱스 주석 재계산 + INSERT 값 튜플에 sma5 추가.
- [MODIFY] `backend/services/meta_service.py:310-311` — placeholder `?` 개수 26 → 27.

### Task 5 — [MODIFY] 프론트엔드 (RED→GREEN)

- [RED] [NEW] PatternBuilder 드롭다운에 "SMA5" 옵션 렌더 테스트 (REQ-SMA5-005).
- [MODIFY] `frontend/src/types/filter.ts:3-12` — `IndicatorName` union에 `| 'SMA5'` 추가.
- [MODIFY] `frontend/src/components/FilterBar/PatternBuilder.tsx:5-8` — `INDICATORS` 배열에 `'SMA5'` 추가.

### Task 6 — [MODIFY] REFACTOR + 컬럼 정합성 게이트

- [NEW] [RED] **AC-9 컬럼명↔값 정렬 round-trip 테스트 (HIGH-risk 오염 검출, acceptance.md AC-9):**
  - daily.py: SMA5 ≠ FromSMA5 ≠ SMA21 ≠ SMA50 ≠ FromSMA50이 되도록 **서로 다른 distinct Close**를 가진 소형 합성 price frame을 만들어 daily insert 경로를 태운 뒤, 행을 read-back해 SMA5/FromSMA5/SMA21/SMA50/FromSMA50가 각자의 **기대값**을 갖는지(= 위치 swap이 없는지) 단언한다. 길이 검사만으로는 못 잡는 swap 오염을 검출한다.
  - meta_service.py: rebuild 후 `stock_meta.sma5`가 최신 일자 `stock_prices.SMA5`와 **동일 값**인지 read-back 단언한다.
- 전체 변경 diff 검토: §1 확정 위치 (A) daily.py 3개 지점 + (B) meta_service.py 3개 지점 일치 확인.
- 전체 재생성 사용자 절차 문서 확인 (기존 DB 삭제 + `POST /api/db/update`).

### [EXISTING] 변경 없음

- `backend/services/db_service.py` (라인 59-99): `price_daily_db()` + `rebuild_stock_meta()` 호출만, 진입점은 변경 불필요.
- `backend/routers/db.py:20`: `POST /api/db/update` 라우터 변경 불필요.
- `my_chart/price.py`: `price_naver()` 데이터 소스 변경 없음.
- 주봉 관련 전 파일: 범위 밖.

---

## 3. 마일스톤 (우선순위 기반, 시간 추정 없음)

1. **Priority High — DB 계층 (Task 1, 2)**: SMA5/FromSMA5 계산·저장. 다른 모든 작업의 선행. 컬럼 순서 정합성 확정.
2. **Priority High — 메타 계층 (Task 4)**: `stock_meta.sma5`. 필터 동작의 필수 전제. Task 2 완료 후.
3. **Priority High — 백엔드 스크리닝 (Task 3)**: Literal + `_INDICATOR_COLUMN` 동기 착지.
4. **Priority Medium — 프론트엔드 (Task 5)**: 드롭다운 노출. 백엔드 화이트리스트 미러.
5. **Priority Medium — REFACTOR + 게이트 (Task 6)**: 정합성 검증, 사용자 재생성 절차 확인.

순서: DB 계층 완료 → 메타 계층 → 백엔드 스크리닝 → 프론트엔드 → 게이트.

---

## 4. 리스크 분석

| 리스크 | 심각도 | 완화 |
| --- | --- | --- |
| **컬럼 순서 정합성 깨짐 (무음 데이터 오염)** | HIGH | daily.py 3개 지점 + meta_service.py 3개 지점에 §1 확정 위치(A)/(B) 적용. **완화의 핵심은 acceptance.md AC-9 (round-trip 컬럼명↔값 정렬 게이트)** — 길이만 보는 `test_row_tuple_length_matches_daily_cols`(기존, 32==32만 검증)으로는 swap 오염을 못 잡으므로, SMA5≠FromSMA5인 distinct 값으로 INSERT→SELECT 왕복 후 각 컬럼이 자기 값을 갖는지 단언한다. stock_meta.sma5 == stock_prices SMA5(최신일자) 정렬 검사도 AC-9에 포함. SMA5는 SQLite REAL이라 위치가 틀려도 오류가 안 나므로 이 round-trip 단언으로만 검출 가능 |
| **멱등 ALTER 누락 → 기존 DB INSERT 실패** | HIGH | `daily.py:81-87` 루프에 SMA5/FromSMA5 추가 (REQUIRED). 전체 재생성 시에도 belt-and-suspenders |
| **Literal/`_INDICATOR_COLUMN` 비동기 착지** | MEDIUM | `test_indicator_column_map_covers_all_whitelist_values`가 강제 — Task 3에서 두 편집 동시 착지 |
| **meta_service.py daily SELECT 인덱스 시프트** | MEDIUM | sma5를 SELECT 끝에 추가하거나 `daily_by_name` 인덱스 주석 재계산. Minervini `d[8]/d[9]/d[10]` 가드 보존 |
| **전체 DB 재생성 운영 부담** | MEDIUM | 사용자에게 "기존 DB 삭제 + POST /api/db/update" 절차 명시. in-place 백필 없음 (A1) |
| **레거시 stock_meta(sma5 누락)로 SMA5 필터 실행 시 OperationalError** | LOW | 전체 재생성 정상 경로 전제. SMA5 전용 가드는 범위 밖 (Exclusions). research.md §5 기록 |

---

## 5. mx_plan (MX 태그 계획)

`code_comments: ko` 설정에 따라 MX 태그 설명은 한국어로 작성.

| 대상 | 태그 | 사유 |
| --- | --- | --- |
| `my_chart/db/daily.py` `_DAILY_COLS` / INSERT 튜플 | `@MX:WARN` (+ `@MX:REASON`) | 위치 기반 executemany — SMA5/FromSMA5 순서 불일치 시 무음 컬럼 시프트 오염. 정합 지점 3곳 명시 |
| `my_chart/db/daily.py` 멱등 ALTER 루프 (81-87) | `@MX:NOTE` | `CREATE TABLE IF NOT EXISTS`가 기존 테이블 미변경 → ALTER 필수 의도 전달 |
| `backend/services/meta_service.py` SELECT/INSERT 정합 지점 | `@MX:WARN` (+ `@MX:REASON`) | stock_prices SELECT ↔ stock_meta INSERT 위치 정합성. sma5 인덱스 시프트 위험 |
| `backend/services/screen_service.py` `_INDICATOR_COLUMN` | `@MX:ANCHOR` (+ `@MX:REASON`) | 스크리닝 화이트리스트 — Literal과 1:1 불변 계약. fan_in 高 (패턴 평가가 의존) |
| 신규 SMA5 테스트 (RED 단계) | `@MX:TODO` | GREEN 단계에서 통과 시 제거 |

REFACTOR/GREEN 단계에서 통과한 `@MX:TODO`는 제거, 신규 복잡 로직에는 `@MX:NOTE` 추가.
</content>
