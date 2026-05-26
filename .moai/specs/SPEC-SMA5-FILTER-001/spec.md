---
id: SPEC-SMA5-FILTER-001
version: 1.0.3
status: Implemented
created: 2026-05-25
updated: 2026-05-26
author: jw
priority: medium
issue_number: 0
---

# SPEC-SMA5-FILTER-001: SMA5 지표 추가 및 ChartGrid 필터 노출

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 1.0.0 | 2026-05-25 | jw | 초기 SPEC 작성. research.md(2026-05-25) 기반. 일봉 DB에 SMA5/FromSMA5 추가 + stock_meta.sma5 확장 + ChartGrid PatternBuilder 노출. development_mode: tdd. issue_number: 0 (GitHub integration OFF). |
| 1.0.1 | 2026-05-25 | jw | plan-audit (review-1) 반영: 컬럼명↔값 정렬 AC 추가(D2), plan.md 테스트 경로 정정(D3), 삽입 위치 \[HARD\] 확정(D4), REQ 본문 구현 세부 제거(D5), AC-5 WHERE 문자열 괄호 보정(D6). 감사의 frontmatter 지적(D1: `created_at`/`labels`)은 프로젝트 house-style(8필드 표준: id/version/status/created/updated/author/priority/issue_number — 형제 SPEC 전부 `created` 사용·`labels` 미사용)에 따라 의도적으로 미적용 — known false-positive. |
| 1.0.2 | 2026-05-26 | jw | TDD 구현 완료 (manager-tdd): AC-1\~AC-9 전부 GREEN, 회귀 0 (baseline 9→8, stale `==27` 정정 + 신규 +10 통과). daily.py SMA5(idx 13)/FromSMA5(idx 23) 3개 정합지점 + meta_service.py 끝-append(Minervini d\[8..10\] 보존) + screen.py/screen_service.py 화이트리스트 + 프론트엔드 드롭다운. status: Implemented. commit 060640f. |
| 1.0.3 | 2026-05-26 | jw | 라이브 검증 후속 수정: 레거시 stock_meta(sma5 컬럼 누락)로 'SMA5 &gt; EMA20' 패턴이 0건 반환되는 이슈 발견. `_STOCK_META_DDL`은 `CREATE TABLE IF NOT EXISTS` 라 기존 26-col 테이블에 sma5가 자동 추가되지 않는 사각지대. `_MINERVINI_META_COLS`에 'sma5' 추가하여 daily.py SMA5 ALTER 패턴과 대칭하는 self-healing 회복. reproduction test 1건 추가 (585 passed, 회귀 0). 라이브 DB는 사용자가 `POST /api/db/update`로 SMA5 재계산 트리거 필요. |

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + SQLite)
- **선행 리서치**: `.moai/specs/SPEC-SMA5-FILTER-001/research.md` (2026-05-25)
- **목표**: 5일 단순이동평균(SMA5)과 이격도(FromSMA5(%))를 일봉 DB에 저장하고, ChartGrid 스크리닝 필터에서 선택 가능한 지표로 노출
- **배포 환경**: localhost 전용, 클라우드 미사용
- **개발 방법론**: TDD (`.moai/config/sections/quality.yaml`의 `development_mode: tdd`) — acceptance 기준은 구체적·검증 가능해야 하며 RED 테스트를 유도한다
- **변경 성격**: BROWNFIELD (기존 코드 확장)

### 1.2 기술 스택

- **Backend**: Python 3.13+, pandas (rolling mean), sqlite3 (positional executemany, WAL), FastAPI, Pydantic v2 (`Literal` 화이트리스트)
- **Frontend**: React 18+, TypeScript (타입 union + 옵션 배열 확장)
- **Testing**: pytest (백엔드), Vitest + React Testing Library (프론트), 커버리지 85% 이상

### 1.3 기존 코드 현황 (research.md §3 요약)

| 경로 | 역할 | 본 SPEC에서의 역할 |
| --- | --- | --- |
| `my_chart/db/daily.py` | 일봉 `stock_prices` 생성 (positional executemany) | SMA5/FromSMA5 컬럼 + 계산 추가 |
| `backend/services/db_service.py` | 4단계 DB 업데이트 오케스트레이션 | 변경 없음 (진입점만 문서화) |
| `backend/services/meta_service.py` | `stock_meta` 스냅샷 재빌드 | sma5 컬럼 + SELECT/INSERT 확장 \[필수\] |
| `backend/schemas/screen.py` | `IndicatorName` Literal 화이트리스트 | "SMA5" 추가 |
| `backend/services/screen_service.py` | WHERE 빌더 + stock_meta SELECT | `_INDICATOR_COLUMN`에 `"SMA5": "sma5"` 추가 |
| `frontend/src/types/filter.ts` | `IndicatorName` TS 미러 | `'SMA5'` 추가 |
| `frontend/src/components/FilterBar/PatternBuilder.tsx` | 지표 드롭다운 | `INDICATORS`에 `'SMA5'` 추가 |

### 1.4 핵심 제약 (research.md §2)

- 스크리닝 필터는 `stock_prices`가 아닌 `stock_meta`를 조회한다. SMA5 필터가 동작하려면 `stock_meta.sma5`가 반드시 존재해야 한다 (§2.1).
- `CREATE TABLE IF NOT EXISTS`는 기존 테이블을 변경하지 않으므로 멱등 ALTER 루프에 SMA5/FromSMA5 추가가 필수다 (§2.2).
- `my_chart/db/daily.py`는 위치 기반 executemany를 사용하므로 컬럼 순서 정합성이 무음 데이터 오염을 막는 핵심이다 (§2.3).

---

## 2. Assumptions (가정)

- A1. 데이터 마이그레이션 전략은 **전체 DB 재생성**이다. 기존 DB 파일 삭제 후 `POST /api/db/update` 전체 재실행. 별도 in-place 백필 스크립트는 만들지 않는다.
- A2. 적용 대상은 **일봉 DB(**`stock_data_daily.db`**,** `stock_prices`**)뿐**이다. 주봉 DB는 범위 밖이다.
- A3. SMA5는 5일 단순이동평균(`Close.rolling(window=5).mean()`)으로 정의한다.
- A4. 이격도 컬럼 DB명은 `FromSMA5`, 계산 표현식은 `FromSMA5(%) = (Close - SMA5) / SMA5 * 100`이다 (기존 `FromEMA10/FromEMA20/FromSMA50/FromSMA200` 패턴 미러링).
- A5. 지표 드롭다운 라벨은 raw 영문 "SMA5"로 표시한다 (한글 라벨 미적용).
- A6. 5거래일 미만 종목은 SMA5가 NaN → SQLite NULL이 정상 동작이다 (`_to_float_or_none` 패턴).

---

## 3. Requirements (요구사항, EARS)

### REQ-SMA5-001 (Ubiquitous) — 일봉 저장

The system **shall** store `SMA5` and `FromSMA5` values in the `stock_prices` table for every daily row of the daily database.

- 검증: `PRAGMA table_info(stock_prices)`에 `SMA5`, `FromSMA5` 존재. 정상 데이터 행에 값 존재.

### REQ-SMA5-002 (Event-Driven) — 재생성 시 계산·영속화

**When** the daily DB rebuild runs, the system **shall** compute the 5-period simple moving average of the closing price (SMA5) and its deviation percentage (FromSMA5), and persist both into the daily price table.

- 정의: SMA5 = `Close`의 5기간 단순이동평균. FromSMA5(%) = `(Close - SMA5) / SMA5 * 100`.
- 구현 위치(HOW, plan.md 참조): 재생성 진입점 `POST /api/db/update` → `price_daily_db()`. 값은 위치 기반 컬럼 슬롯에 영속화.
- 검증: 재생성 후 임의 종목의 SMA5가 직전 5거래일 Close 평균과 일치. FromSMA5가 공식과 일치. 행 튜플 길이 == `len(_DAILY_COLS)`.

### REQ-SMA5-003 (Ubiquitous) — stock_meta 확장 \[필수\]

The `stock_meta` snapshot table **shall** include the `sma5` column so that the screening filter can evaluate conditions against it.

- 검증: `rebuild_stock_meta()` 실행 후 `PRAGMA table_info(stock_meta)`에 `sma5` 존재. 최신 일봉 SMA5 값이 stock_meta로 복사됨.

### REQ-SMA5-004 (Event-Driven) — 서버사이드 필터 평가

**When** a user adds a pattern condition referencing SMA5 in the ChartGrid filter, the system **shall** evaluate it server-side as a parameterized query against the screening snapshot, using only server-side whitelisted column names (no user-supplied SQL identifiers).

- 구현 위치(HOW, plan.md 참조): 스크리닝 스냅샷 = `stock_meta`. 컬럼명은 `_INDICATOR_COLUMN` 화이트리스트(`"SMA5" -> "sma5"`) 전용. 생성 WHERE 예: `(close > sma5 * ?)`.
- 검증: `_INDICATOR_COLUMN["SMA5"] == "sma5"`. `get_args(IndicatorName)`의 모든 값이 `_INDICATOR_COLUMN`에 매핑됨. SMA5 패턴이 유효한 WHERE 절을 생성하고 스크리닝 결과를 반환.

### REQ-SMA5-005 (Ubiquitous) — 프론트엔드 선택지 노출

The ChartGrid filter **shall** list SMA5 as a selectable indicator in the indicator dropdowns, rendered as the raw label "SMA5".

- 구현 위치(HOW, plan.md 참조): 지표 드롭다운 컴포넌트 `PatternBuilder`의 `INDICATORS` 배열 + `frontend/src/types/filter.ts`의 `IndicatorName` union.
- 검증: `IndicatorName`에 `'SMA5'` 포함. `INDICATORS` 배열에 `'SMA5'` 포함. 드롭다운에 "SMA5" 옵션 렌더.

### REQ-SMA5-006 (Unwanted Behavior) — 5거래일 미만 NULL 안전

**If** a stock has fewer than 5 trading days (SMA5 is NaN), **then** the system **shall** persist `SMA5`/`FromSMA5` as SQLite `NULL` without raising, consistent with the existing `_to_float_or_none` NaN→None pattern.

- 검증: 4행 OHLCV 입력 시 SMA5 행 값이 None(NULL)이고 예외가 발생하지 않음.

---

## 4. Exclusions (What NOT to Build)

본 SPEC은 다음을 **구현하지 않는다**:

- **주봉 DB**: `stock_data_weekly.db`에 SMA5 / 5주선 미추가.
- **그리드 결과 표시**: ChartGrid 결과 테이블에 SMA5 값을 컬럼으로 표시하지 않음 (`StockItem.sma5`, `frontend/src/types/stock.ts`, `screen.py` `StockItem`, `screen_stocks()` SELECT의 sma5 표시 — 모두 범위 밖).
- **한글 라벨**: 지표 드롭다운에 "5일선" 등 한글 라벨 미적용. raw "SMA5" 유지.
- **차트 오버레이**: 가격 차트(`my_chart/charting/single.py`)에 SMA5 선 미표시.
- **별도 in-place 마이그레이션 스크립트**: 전체 재생성 외 별도 백필 스크립트 미작성.
- **SMA5 전용 PRAGMA 가드**: `stock_meta.sma5` 누락에 대한 별도 컬럼 존재 선검사 미추가 (전체 재생성 정상 경로 전제, research.md §5 참조).

---

## 5. Specifications (수용 기준 연결)

상세 Given/When/Then 시나리오, 에지케이스, 품질 게이트는 `acceptance.md` 참조. 구현 작업 분해, 기술 노트, 리스크는 `plan.md` 참조. &lt;/content&gt;