---

id: SPEC-MINERVINI-001 title: Mark Minervini Trend Template Screener (Data Layer & Evaluation Engine) version: 1.0.3 status: completed created: 2026-04-21 updated: 2026-04-21 author: jw priority: P1 tags: \[screener, minervini, trend-template, sqlite, fastapi, pydantic, tdd\] related:

- SPEC-RS-LINE-001
- SPEC-DASHBOARD-002
- SPEC-PRESET-001 (downstream, UI presets)

---

# SPEC-MINERVINI-001: Mark Minervini Trend Template 스크리너 (데이터 계층 + 평가 엔진)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 1.0.0 | 2026-04-21 | jw | 초기 SPEC 작성 (research.md 2026-03-08 기반) |
| 1.0.1 | 2026-04-21 | jw | SMA200 shift 값 20일 확정 (컬럼명 `SMA200_20D_AGO`), score 엄격 모드 확정 (strict gate, 통과 행은 항상 `trend_template_score=8`) |
| 1.0.2 | 2026-04-21 | jw | 전체 DB 재생성 전략 확정 (ALTER 마이그레이션 → 파일 교체). 기존 daily/weekly DB 파일 삭제 후 db-update 파이프라인 전체 재실행을 정상 경로로 채택. ALTER 경로는 방어적 백업으로 유지. |
| 1.0.3 | 2026-04-21 | MoAI | `/moai run` + `/moai sync` 완료. Implementation Notes 섹션 추가, status: planned → completed. 28/28 TDD 테스트 통과, Simplify 패스 적용 (commit `79de6a8` + `cd72fcb`). |

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + SQLite)
- **선행 리서치**: `.moai/specs/SPEC-MINERVINI-001/research.md` (2026-03-08)
- **목표**: Minervini Trend Template 8조건을 백엔드 스크리너에서 서버사이드 SQL 평가로 수행
- **범위**: 이 SPEC 은 **데이터 계층 + 평가 엔진**만 다룬다. UI (프리셋 칩, 버튼) 는 SPEC-PRESET-001 에서 다룬다.
- **배포 환경**: localhost 전용, 클라우드 미사용

### 1.2 기술 스택

- **Backend**: Python 3.13+, FastAPI, Pydantic v2 (`model_validate`, `ConfigDict`), SQLite (WAL)
- **Frontend**: React 18+, TypeScript (본 SPEC 에서는 타입 추가만)
- **Testing**: pytest + pytest-asyncio (커버리지 85% 이상, TDD RED-GREEN-REFACTOR)
- **개발 방법론**: TDD (`.moai/config/sections/quality.yaml` 의 `development_mode: tdd`)

### 1.3 기존 코드 현황 (2026-04-21 기준)

| 경로 | 역할 | 본 SPEC 에서의 역할 |
| --- | --- | --- |
| `my_chart/db/daily/price_daily_db.py` | 일봉 DB 생성 (OHLCV + EMA10/20 + SMA50/100/200 + RS_Line) | 신규 컬럼 계산 추가 |
| `backend/services/db_service.py` | 4단계 DB 업데이트 오케스트레이션 | 변경 없음 |
| `backend/services/meta_service.py` | `stock_meta` 스냅샷 재빌드 | 스냅샷 컬럼 확장 + 멱등 ALTER |
| `backend/schemas/screen.py` | `ScreenRequest`, `StockItem`, `ScreenResponse` | 요청/응답 모델 확장 |
| `backend/services/screen_service.py` | WHERE 빌더 + stock_meta SELECT | `_build_minervini_where()` 추가, 점수 SELECT 확장 |
| `backend/services/chart_service.py` | `stock_prices` 스키마 참조 (Date, Open, High, Low, Close, VolumeWon, EMA10, EMA20, SMA50, SMA100, SMA200, RS_Line) | 신규 컬럼 후방 호환 확인 |
| `frontend/src/types/filter.ts` | `ScreenRequest` TypeScript 미러 | 타입 필드 추가만 |

### 1.4 현재 DB 스키마 갭 (research.md §4.2 요약)

Trend Template 8조건 중 DB 에 **없는** 데이터:

- **SMA150** (일봉 기준 150일 단순이평) — T1, T2, T4 에 필요
- **52주 최저가 (LOW_52W)** — T6 에 필요 (기존 `high52w` 는 있으나 `min52w` 는 없음)
- **20영업일 전 SMA200 (SMA200_20D_AGO)** — T3 의 "1개월 상승 추세" 판정에 필요

SMA50, SMA100, SMA200, Close, rs_12m, HIGH_52W 는 이미 존재한다.

---

## 2. Assumptions (가정)

- A1: Trend Template 8조건은 research.md §2.1 의 정의를 그대로 따른다. 특히 T6 의 배율은 **1.25** (25% 이상) 를 사용한다. (1.30 을 쓰는 자료도 있으나 본 프로젝트는 research.md 기준을 채택.)
- A2: 52주 최고/최저는 **250 영업일 rolling window** 로 정의한다. 주말·공휴일을 제외한 순수 거래일 기준.
- A3: "20영업일 전 SMA200" 은 **정확히 20 trading-day shift** 로 계산한다. 즉 `SMA200_20D_AGO[t] = SMA200[t - 20]`. 컬럼명과 shift 값은 **v1.0.1 (2026-04-21) 결정**으로 확정되었으며, research.md §2.1 의 "20 trading days ago" 표현과 일치한다. (이전 초안에서 혼용되던 "\~1 calendar month ≈ 22 days" 해석은 폐기.)
- A4: 상장 후 거래일이 250일 미만인 종목은 T6, T7 에서 NULL 을 반환하므로 WHERE 조건에서 자연스럽게 탈락한다.
- A5: 모든 컬럼 추가는 **멱등**이어야 한다. 파이프라인을 두 번 실행해도 오류가 발생하거나 컬럼이 중복되지 않는다.
- A6: 신규 컬럼이 아직 마이그레이션되지 않은 환경에서도 `/api/screen` 는 **HTTP 200** 을 반환해야 한다 (empty list + warning log). 기존 필터는 영향을 받지 않는다.
- A7: **점수 노출은 엄격 모드 (strict gate)** 이다. **v1.0.1 (2026-04-21) 결정**에 따라 WHERE 절이 8조건 전체를 AND 결합하는 strict gate 로 고정된다. 결과 집합에 남는 행은 **반드시** 8조건을 모두 통과하며, `trend_template_score` 는 스키마 안정성을 위해 필드로 유지되나 반환되는 모든 행에서 고정 정수 `8` 을 가진다. **부분 매칭 (예: 6/8 통과 행) 노출은 현재 범위 밖이며 향후 SPEC 에서도 별도 기능으로 분리된다.**
- A8: 본 SPEC 은 VCP, 거래량 돌파, 시장 환경 필터를 포함하지 않는다. 이는 별도 SPEC 의 책임이다.
- A9: **배포 전략 — 전체 DB 재생성 (v1.0.2 2026-04-21 결정)**. 본 SPEC 의 배포 시점에 기존 `daily.db` 및 `weekly.db` 파일을 **삭제**하고 `db-update` 파이프라인을 **전체 재실행**하여 새 DB 를 생성한다. SMA150, HIGH_52W, LOW_52W, SMA200_20D_AGO 는 새 DB 생성 시점부터 **모든 행에 자연스럽게 채워진다** (파이프라인이 해당 컬럼을 INSERT 하므로 별도 백필 불필요). 점진적 ALTER TABLE 마이그레이션 경로는 **방어적 백업으로만 유지**되며 (REQ-MIN-008 의 idempotent PRAGMA + ALTER, §6.2 참조), 운영 실수 (일부 컬럼만 누락된 DB 와 신규 코드의 조합) 를 대비하기 위한 것이지 정상 배포 경로가 아니다.

---

## 3. Requirements (요구사항, EARS 포맷)

### Module 1: Daily Price Pipeline (my_chart/db/daily/)

**REQ-MIN-001 — SMA150 계산 및 저장**

시스템은 **항상** 각 종목의 일봉 데이터 처리 시 150일 단순이동평균을 계산하여 `stock_prices.SMA150` (REAL) 컬럼에 저장해야 한다.

- 산식: `SMA150[t] = mean(Close[t-149 .. t])`
- 거래일이 150일 미만인 초기 행은 NULL 로 저장한다 (pandas `rolling(150, min_periods=150)`).
- 기존 SMA50/100/200 과 동일한 pandas rolling 방식을 사용하여 일관성을 유지한다.

**REQ-MIN-002 — 52주 최고/최저 계산 및 저장**

시스템은 **항상** 각 종목의 일봉 데이터 처리 시 250 거래일 rolling 최고/최저가를 계산하여 `stock_prices.HIGH_52W`, `stock_prices.LOW_52W` (REAL) 에 저장해야 한다.

- 산식: `HIGH_52W[t] = max(High[t-249 .. t])`, `LOW_52W[t] = min(Low[t-249 .. t])`
- 거래일이 250일 미만인 초기 행은 NULL 로 저장한다.
- **WHEN** 거래일이 250일 미만인 종목이 `minervini_trend_template=true` 로 필터링되면 **THEN** T6/T7 이 NULL 비교로 탈락하여 결과에서 제외된다 (자연 필터, Assumption A4 참조).

**REQ-MIN-003 — 20영업일 전 SMA200 저장**

시스템은 **항상** 각 종목의 일봉 데이터 처리 시 20 거래일 전의 SMA200 값을 `stock_prices.SMA200_20D_AGO` (REAL) 컬럼에 저장해야 한다.

- 산식: `SMA200_20D_AGO[t] = SMA200[t - 20]`
- SMA200 이 NULL 이거나 t &lt; 20 인 행은 NULL 로 저장한다.
- 런타임 스크리닝 쿼리에서 재계산을 피하기 위해 **precompute** 한다 (Assumption A3, 의사결정 #1).

### Module 2: stock_meta Snapshot Rebuild

**REQ-MIN-004 — stock_meta 스냅샷 컬럼 확장**

시스템은 **항상** `meta_service.rebuild_stock_meta` 실행 시 각 종목 최신 행의 `SMA150, HIGH_52W, LOW_52W, SMA200_20D_AGO` 값을 `stock_meta.sma150, stock_meta.high52w, stock_meta.low52w, stock_meta.sma200_20d_ago` 컬럼으로 복사해야 한다.

- `high52w` 는 기존 컬럼이므로 **값만 갱신**한다 (재정의 없음).
- `sma150, low52w, sma200_20d_ago` 는 **신규 컬럼**으로 추가한다.
- 스냅샷 컬럼은 스크리닝 쿼리의 성능을 위해 비정규화된 최신값을 의미한다 (기존 `sma50, sma200, rs_12m` 과 동일한 패턴).

**REQ-MIN-008 — 멱등 컬럼 추가**

시스템은 **항상** 신규 컬럼을 추가하기 전에 `PRAGMA table_info(<table>)` 을 조회하여 컬럼 존재 여부를 확인한 후 누락된 경우에만 `ALTER TABLE ADD COLUMN` 을 수행해야 한다.

- 대상 테이블: `stock_prices` (daily), `stock_meta`.
- 대상 컬럼: `SMA150`, `HIGH_52W`, `LOW_52W`, `SMA200_20D_AGO` (stock_prices), `sma150`, `low52w`, `sma200_20d_ago` (stock_meta).
- `rebuild_stock_meta` 가 호출되기 전에 동일 함수가 idempotent ALTER 를 수행해야 한다.
- **WHEN** 동일한 DB 에 대해 `db_service.update_all` 이 반복 실행되면 **THEN** 에러가 발생하지 않아야 한다 (duplicate column 방지).

### Module 3: Screen Request Schema

**REQ-MIN-005 — Minervini 필터 플래그**

시스템은 **항상** `ScreenRequest` 에 `minervini_trend_template: bool | None = None` 필드를 노출해야 한다.

- **WHEN** `minervini_trend_template=true` 이면 **THEN** 백엔드는 Trend Template 8조건을 WHERE 절에서 **모두 AND 결합**하여 평가해야 한다.
- **WHEN** `minervini_trend_template` 이 `false` 또는 `None` 이면 **THEN** Trend Template 조건은 적용하지 않는다 (기존 동작 유지).
- 조건은 **하드코딩**된 전용 WHERE 빌더 (`_build_minervini_where()`) 로 구성한다. 이 SPEC 에서는 `PatternCondition` 으로 표현하지 않는다 (의사결정 #2).
- 기존 `patterns: list[PatternCondition]` 의 `max_length` 는 3 에서 **5** 로 확장한다. (이 확장은 SPEC-PRESET-001 에서 소비되며, 본 SPEC 은 Pydantic 제약 변경만 수행한다.)

Trend Template 8조건 WHERE 식 (stock_meta 컬럼 기준):

```
(close > sma150 AND close > sma200)                           -- T1
AND (sma150 > sma200)                                         -- T2
AND (sma200 > sma200_20d_ago)                                 -- T3
AND (sma50 > sma150 AND sma50 > sma200)                       -- T4
AND (close > sma50)                                           -- T5
AND (close >= low52w * 1.25)                                  -- T6
AND (close <= high52w * 1.0 AND close >= high52w * 0.75)      -- T7
AND (rs_12m >= 70)                                            -- T8
```

**REQ-MIN-006 — Trend Template 점수 노출 (엄격 모드)**

**WHEN** `minervini_trend_template=true` 이고 **WHERE 절을 통과한 행**이 있으면 **THEN** 시스템은 각 `StockItem` 에 `trend_template_score: int` 필드로 **고정값** `8` 을 포함해야 한다.

- **v1.0.1 (2026-04-21) 결정 — 엄격 모드 (strict gate) 확정**: WHERE 절이 8조건 전체를 AND 결합하는 strict gate 이므로 결과 집합에 반환되는 모든 행은 정의상 8조건을 모두 통과한다. 따라서 `trend_template_score` 는 반환되는 모든 행에서 **항상 정확히** `8` 이다.
- 필드는 **API 스키마 안정성**을 위해 유지된다. 향후 부분 매칭 모드가 별도 SPEC 으로 도입되더라도 본 필드의 타입과 위치는 변경되지 않는다.
- SQL 은 `SUM(CASE WHEN T_i THEN 1 ELSE 0 END)` 형태로 계산하지만 strict gate 특성상 결과는 항상 8 이다. 구현 단순화를 위해 `CASE WHEN :minervini_on = 1 THEN 8 END AS trend_template_score` 로 축약해도 무방하다 (구현 재량).
- \[HARD\] **부분 매칭 (예: 6/8 통과 행) 은 본 SPEC 에서 반환하지 않는다.** WHERE 을 HAVING + CASE SUM 으로 리팩터하여 부분 매칭을 노출하는 접근은 **명시적으로 out of scope** 이다 (§10 참조).
- **WHEN** `minervini_trend_template` 이 꺼져 있거나 요청에 해당 필드가 없으면 **THEN** `trend_template_score` 는 `None` 으로 반환한다.
- `StockItem` 스키마 필드: `trend_template_score: int | None = None`.

### Module 4: Backward Compatibility & Degraded Mode

**REQ-MIN-007 — 마이그레이션 미적용 환경에서의 안전 동작 (방어적 기본값, defense-in-depth)**

> **스코프 변경 (v1.0.2, 2026-04-21)**: 전체 DB 재생성이 정상 경로이다 (Assumption A9 참조). 본 요구사항은 **운영 실수** (예: 신규 코드 배포는 완료되었으나 DB 재생성을 잊은 경우, 일부 컬럼만 누락된 채 시작된 경우) 에 대비한 **defense-in-depth fallback** 이며, 테스트는 WARN 로그와 HTTP 200 empty 응답만 검증한다.

**IF** 요청 시점에 `stock_meta.sma150`, `stock_meta.low52w`, `stock_meta.sma200_20d_ago` 중 **하나라도 누락**되어 있고 `minervini_trend_template=true` 이면 **THEN** 시스템은 다음과 같이 동작해야 한다:

1. `sqlite3.OperationalError (no such column)` 을 **내부적으로** 감지한다.
2. HTTP **200 OK** 를 반환한다 (500 또는 503 금지).
3. `ScreenResponse(total=0, sectors=[])` 를 반환한다.
4. WARN 레벨 로그 1회 기록: `"[minervini] required columns missing; delete DB files and re-run db-update pipeline"`
5. 기존 필터 (market_cap, chg\_\*, patterns, rs_min, sectors, markets, codes) 는 **Minervini 플래그와 무관하게** 정상 작동해야 한다.

컬럼 존재 검사는 `_build_minervini_where()` 호출 직전에 `PRAGMA table_info(stock_meta)` 1회 조회로 수행하여 불필요한 예외 왕복을 회피할 수도 있다 (구현 재량).

---

## 4. Specifications (세부 사양)

### 4.1 데이터 흐름

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 (0) 배포 단계 — Primary path (정상 경로, v1.0.2 결정)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      [기존 daily.db / weekly.db 파일 백업 후 삭제]
        $ mv daily.db daily.db.bak
        $ mv weekly.db weekly.db.bak
        $ rm daily.db weekly.db
                 ↓
      [파이프라인 전체 재실행]
        $ POST /api/refresh     (or equivalent CLI)
                 ↓
      [모든 컬럼이 처음부터 채워진 새 DB 생성]
        stock_prices: SMA150, HIGH_52W, LOW_52W, SMA200_20D_AGO 포함
        stock_meta:   sma150,  high52w,  low52w,  sma200_20d_ago  포함
                 ↓
      [별도 백필 불필요 — 250 거래일+ 종목 100% 채움]


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 (1) 파이프라인 내부 흐름 (`db-update` 실행 시마다 동일)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    /api/refresh 호출
      ↓
    db_service.update_all()
      ↓
    [Phase 3] price_daily_db.py
      - Close/Open/High/Low/Volume 수집
      - EMA10, EMA20 계산 (기존)
      - SMA50, SMA100, SMA200 계산 (기존)
      - [NEW] SMA150 계산                ← REQ-MIN-001
      - [NEW] HIGH_52W, LOW_52W 계산     ← REQ-MIN-002
      - [NEW] SMA200_20D_AGO shift        ← REQ-MIN-003
      - RS_Line 계산 (기존)
      - stock_prices 에 저장 (신규 DB: 컬럼이 생성 시점부터 존재)
      ↓
    [Phase 4] meta_service.rebuild_stock_meta()
      - [Defense 백업] PRAGMA 컬럼 검사 + 누락 컬럼 ALTER   ← REQ-MIN-008
        (Primary path 에서는 새 DB 이므로 ALTER 는 실행되지 않는다 —
         PRAGMA 검사 결과 컬럼이 이미 존재함)
      - 각 종목 최신 행의 sma150/high52w/low52w/sma200_20d_ago 를
        stock_meta 로 복사                                    ← REQ-MIN-004

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 (2) 런타임 — POST /api/screen { minervini_trend_template: true }
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    screen_service.screen_stocks(req)
      ↓
    _build_where(req)
      - 기존 조건 (market_cap, chg_*, rs_min, markets, sectors, codes, patterns)
      - [NEW] if req.minervini_trend_template:
                call _build_minervini_where()                  ← REQ-MIN-005
      ↓
    SELECT ... , (CASE WHEN :minervini_on = 1 THEN 8 END)
                 AS trend_template_score
    FROM stock_meta
    WHERE <조합된 WHERE + 8조건 strict gate>
      ↓
    StockItem 에 trend_template_score 매핑 (strict: 항상 8)    ← REQ-MIN-006
      ↓
    SectorGroup 집계
      ↓
    ScreenResponse 반환

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 (3) Defense path (점선 분기) — 운영 실수 방어용 (v1.0.2 defense-in-depth)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      기존 DB 를 삭제하지 않은 채 신규 코드만 배포된 경우
    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

      rebuild_stock_meta() 진입 시 PRAGMA 검사
                 ↓
      누락된 컬럼만 멱등 ALTER TABLE ADD COLUMN 으로 추가
      (단, 값은 NULL. 다음 사이클에서 Phase 3/4 재실행 시 채워짐)
                 ↓
      /api/screen 호출 시 컬럼이 아직 NULL 이면
      sqlite3.OperationalError 또는 NULL 비교로
      HTTP 200 OK + empty list + WARN log                     ← REQ-MIN-007
                 ↓
      운영자: 완전 복구 원한다면 (0) Primary path 로 복귀하여
             DB 삭제 후 전체 재실행
```

### 4.2 스키마 변경 요약

#### stock_prices (daily)

| 컬럼 | 타입 | 설명 | 생성 시점 |
| --- | --- | --- | --- |
| `SMA150` | REAL | 150일 단순이평 | price_daily_db.py |
| `HIGH_52W` | REAL | 250 거래일 rolling max(High) | price_daily_db.py |
| `LOW_52W` | REAL | 250 거래일 rolling min(Low) | price_daily_db.py |
| `SMA200_20D_AGO` | REAL | SMA200 의 20 거래일 shift | price_daily_db.py |

#### stock_meta (스냅샷)

| 컬럼 | 타입 | 설명 | 생성 시점 |
| --- | --- | --- | --- |
| `sma150` | REAL | 신규. 해당 종목 최신 SMA150 | rebuild_stock_meta |
| `low52w` | REAL | 신규. 해당 종목 최신 LOW_52W | rebuild_stock_meta |
| `sma200_20d_ago` | REAL | 신규. 해당 종목 최신 SMA200_20D_AGO | rebuild_stock_meta |
| `high52w` | REAL | 기존. 값만 `HIGH_52W` 로 갱신 | rebuild_stock_meta |

### 4.3 Pydantic 모델 변경

```python
# backend/schemas/screen.py

class ScreenRequest(BaseModel):
    # ... 기존 필드 ...
    patterns: list[PatternCondition] = Field(default_factory=list, max_length=5)  # 3 → 5
    minervini_trend_template: bool | None = Field(
        default=None,
        description="Minervini Trend Template 8조건 전체를 AND 결합으로 적용",
    )

class StockItem(BaseModel):
    # ... 기존 필드 ...
    trend_template_score: int | None = Field(
        default=None,
        ge=0,
        le=8,
        description=(
            "엄격 모드에서 반환되는 모든 행의 Trend Template 통과 조건 개수. "
            "strict gate 특성상 반환되는 행은 항상 정확히 8. "
            "플래그가 꺼져 있거나 요청에 없으면 None. "
            "ge/le 경계는 API 스키마 안정성을 위해 유지되며 향후 부분 매칭 SPEC 과의 호환을 보장한다."
        ),
    )
```

### 4.4 TypeScript 타입 변경 (최소)

```ts
// frontend/src/types/filter.ts
export interface ScreenRequest {
  // ... 기존 ...
  minervini_trend_template?: boolean | null;
}

export interface StockItem {
  // ... 기존 ...
  trend_template_score?: number | null;
}
```

프런트엔드의 실제 UI 반영 (칩, 토글, 프리셋) 은 본 SPEC 의 범위 밖이며 SPEC-PRESET-001 에서 다룬다.

### 4.5 수정 파일 목록

| 파일 | 변경 사항 | SPEC 레퍼런스 |
| --- | --- | --- |
| `my_chart/db/daily/price_daily_db.py` | SMA150, HIGH_52W, LOW_52W, SMA200_20D_AGO 계산 추가 | REQ-MIN-001/002/003 |
| `backend/services/meta_service.py` | 멱등 ALTER + 스냅샷 4개 컬럼 복사 | REQ-MIN-004, REQ-MIN-008 |
| `backend/schemas/screen.py` | `minervini_trend_template`, `trend_template_score` 추가, `patterns.max_length=5` | REQ-MIN-005, REQ-MIN-006 |
| `backend/services/screen_service.py` | `_build_minervini_where()` 추가, SELECT 에 점수 계산, 컬럼 누락 가드 | REQ-MIN-005, REQ-MIN-006, REQ-MIN-007 |
| `frontend/src/types/filter.ts` | TypeScript 타입 추가 (UI 변경 없음) | REQ-MIN-005, REQ-MIN-006 |
| `backend/tests/test_minervini_template.py` | 신규 테스트 파일 (RED-first) | 전체 |

### 4.6 신규 파일

- `backend/tests/test_minervini_template.py` — 단위 + 통합 + 회귀 + 후방 호환 테스트

### 4.7 Traceability

| 요구사항 | 구현 파일 | 테스트 |
| --- | --- | --- |
| REQ-MIN-001 | my_chart/db/daily/price_daily_db.py | test_sma150_rolling_correctness, test_sma150_insufficient_history_null |
| REQ-MIN-002 | my_chart/db/daily/price_daily_db.py | test_52w_rolling_max_min, test_52w_ipo_under_250days_null |
| REQ-MIN-003 | my_chart/db/daily/price_daily_db.py | test_sma200_20d_ago_shift, test_sma200_20d_ago_null_for_short_history |
| REQ-MIN-004 | backend/services/meta_service.py | test_meta_snapshot_contains_new_columns, test_meta_latest_value_copied |
| REQ-MIN-005 | backend/schemas/screen.py, backend/services/screen_service.py | test_minervini_where_all_8_conditions, test_minervini_boundary_cases |
| REQ-MIN-006 | backend/services/screen_service.py | test_trend_template_score_is_8_for_all_returned_rows, test_trend_template_score_none_when_flag_off |
| REQ-MIN-007 | backend/services/screen_service.py | test_backward_compat_missing_columns_returns_200_empty |
| REQ-MIN-008 | backend/services/meta_service.py | test_rebuild_idempotent_no_duplicate_columns |

---

## 5. Acceptance Criteria (수용 기준)

각 항목은 Given / When / Then 시나리오로 정의된다. 모든 항목이 통과해야 `run` phase 가 완료된다.

### AC-1: SMA150 rolling 계산 정확성 (단위)

- **Given** `Close = [100, 101, ..., 249]` (150개 값, 선형 증가)
- **When** `compute_sma150(df)` 를 호출한다
- **Then** `SMA150[149] == 174.5` (149번째 인덱스 = 첫 유효값), `SMA150[0..148]` 은 모두 NULL

### AC-2: 52주 rolling 최고/최저 정확성 (단위)

- **Given** 300일치 일봉 데이터가 있는 종목
- **When** `compute_52w_high_low(df)` 를 호출한다
- **Then**:
  - `HIGH_52W[249]` = `max(High[0..249])`
  - `LOW_52W[299]` = `min(Low[50..299])`
  - `HIGH_52W[0..248], LOW_52W[0..248]` 는 NULL (min_periods=250)

### AC-3: SMA200_20D_AGO shift (단위, edge case)

- **Given** SMA200 이 220일부터 계산되어 있는 종목
- **When** `compute_sma200_20d_ago(df)` 를 호출한다
- **Then** `SMA200_20D_AGO[t]` 은 `t >= 220+20=240` 일 때부터 유효값을 가지며, 그 전은 NULL

### AC-4: 통합 — 8조건 경계 케이스 픽스처 (strict gate)

- **Given** 아래 10개 종목으로 구성된 fixture DB:
  - S1 \~ S8: 각각 T1 \~ T8 조건 하나만 실패 (다른 7개는 통과)
  - S9: 8조건 모두 통과 (예상 통과)
  - S10: 8조건 모두 실패
- **When** `POST /api/screen { minervini_trend_template: true }` 를 호출한다
- **Then**
  - 결과 집합은 **정확히** `{S9}` **단 하나**만 포함한다 (strict gate 로 S1\~S8 은 각각 단 하나의 조건 실패로도 탈락)
  - `S9.trend_template_score == 8` (정확한 동등 비교)
  - S1\~S8 의 부분 매칭 점수 (예: 7) 는 **노출되지 않는다**

### AC-5: 통합 — trend_template_score 엄격 모드 노출

- **Given** fixture DB 의 S9 와 `minervini_trend_template=true`
- **When** 스크리닝을 수행한다
- **Then**
  - 응답의 모든 `StockItem` 에서 `trend_template_score == 8` 이다 (strict gate 이므로 반환되는 모든 행에 대해 `== 8` assert)
  - 0, 1, ..., 7 값을 가진 행은 **결과 집합에 존재하지 않는다** (별도 assert)
- **And When** `minervini_trend_template` 를 제거하고 동일 종목이 다른 필터로 포함되면
- **Then** 해당 종목의 `trend_template_score` 는 `None`

### AC-6: 회귀 — 기존 필터 영향 없음

- **Given** fixture DB 와 `minervini_trend_template` 이 false/None 인 기존 요청들 (market_cap_min, chg_1w_min, chg_1m_min, chg_3m_min, rs_min, patterns\[2개\], markets, sectors, codes)
- **When** 각 요청을 전송한다
- **Then** SPEC-MINERVINI-001 적용 전과 동일한 결과 집합과 정렬이 반환된다
- **And** Pydantic 의 `patterns.max_length=5` 확장이 기존 3개 이하 요청을 거부하지 않는다

### AC-7: 마이그레이션 멱등성

- **Given** 완전히 비어 있는 daily DB
- **When** `meta_service.rebuild_stock_meta()` 를 **두 번 연속** 호출한다
- **Then**:
  - 두 호출 모두 예외 없이 완료된다
  - `PRAGMA table_info(stock_meta)` 결과에서 `sma150, low52w, sma200_20d_ago` 는 각 1회씩만 나타난다
  - 두 번째 호출 후에도 스냅샷 값은 최신 상태로 유지된다

### AC-8: 후방 호환 — 컬럼 미존재 시 200 OK

- **Given** stock_meta 에 신규 컬럼 3개가 모두 없는 레거시 DB
- **When** `POST /api/screen { minervini_trend_template: true }` 를 호출한다
- **Then**:
  - 응답: HTTP 200, `{ "total": 0, "sectors": [] }`
  - 로그: WARN 1회 (`[minervini] required columns missing`)
  - 5xx 응답 없음, 예외 전파 없음
- **And When** 동일 DB 에서 `minervini_trend_template=false` 로 다른 필터를 호출하면
- **Then** 정상 결과가 반환된다 (fallback 이 기존 필터에 영향 주지 않음)

### AC-9: IPO 종목 (거래일 &lt; 250일) 자연 탈락

- **Given** 상장 후 거래일 150일인 종목 (HIGH_52W, LOW_52W 가 NULL)
- **When** `minervini_trend_template=true` 로 스크리닝한다
- **Then** 해당 종목은 T6/T7 NULL 비교로 인해 결과 집합에서 제외된다

### Definition of Done

- [ ] 모든 REQ-MIN-001 \~ 008 의 코드 변경 완료

- [ ] pytest 커버리지 ≥ 85% (`backend/services/screen_service.py`, `backend/services/meta_service.py`)

- [ ] AC-1 \~ AC-9 전부 통과

- [ ] ruff lint 경고 0

- [ ] 실제 KRX DB (KOSPI 100 종목 샘플) 에서 수동 검증: `minervini_trend_template=true` 결과가 research.md §2.1 의 8조건과 일치

- [ ] @MX:NOTE 태그 추가 (`_build_minervini_where()`), @MX:ANCHOR 태그 (`screen_stocks()` — fan_in ≥ 3)

- [ ] Frontend 타입 변경은 타입체크만 통과 (UI 변경 없음)

---

## 6. Technical Approach (기술 접근)

### 6.1 일봉 파이프라인 변경 전략

`price_daily_db.py` 는 pandas DataFrame 에서 기술 지표를 계산한 후 SQLite 에 저장하는 구조이다. 기존 SMA50/100/200 계산 이후에 다음 3줄을 추가한다 (의사 코드):

```python
df["SMA150"]          = df["Close"].rolling(150, min_periods=150).mean()
df["HIGH_52W"]        = df["High"].rolling(250, min_periods=250).max()
df["LOW_52W"]         = df["Low"].rolling(250, min_periods=250).min()
df["SMA200_20D_AGO"]  = df["SMA200"].shift(20)
```

종목별로 DataFrame 을 별도로 처리하는 기존 루프에 삽입하면 종목 간 데이터 누수가 발생하지 않는다.

### 6.2 배포 전략 — 전체 DB 재생성 (Primary) + 멱등 ALTER (Defense)

**Primary path (정상 경로, v1.0.2 결정)**: 배포 시점에 기존 DB 파일을 **완전 교체**한다.

1. 기존 DB 파일 백업 (운영 안전): `mv daily.db daily.db.bak`, `mv weekly.db weekly.db.bak`
2. 기존 DB 파일 삭제 (또는 교체): `rm daily.db weekly.db`
3. `db-update` 파이프라인 **전체 재실행**: `backend/services/db_service.update_all()` 호출
4. 결과: 새로 생성된 `daily.db` 의 `stock_prices` 테이블과 `stock_meta` 테이블에 **SMA150, HIGH_52W, LOW_52W, SMA200_20D_AGO 컬럼이 처음부터 존재**하며, 250 거래일 이상의 히스토리를 가진 모든 종목에 대해 값이 **100% 채워진 상태**로 생성된다. 별도 백필 절차는 불필요하다.

**Order of operations (파이프라인 내부 순서)**: `db_service.update_all()` 은 기존 4-단계 오케스트레이션을 그대로 유지한다. 본 SPEC 에 유의미한 순서는:

- Phase 3 (daily prices): `price_daily_db.py` 가 SMA150 / HIGH_52W / LOW_52W / SMA200_20D_AGO 를 포함한 `stock_prices` 테이블을 신규 생성한다 (REQ-MIN-001/002/003).
- Phase 4 (meta rebuild): `meta_service.rebuild_stock_meta()` 가 Phase 3 에서 갓 채워진 `stock_prices` 를 소스로 읽어 `stock_meta` 스냅샷을 생성한다 (REQ-MIN-004).

Phase 3 이 선행되어 `stock_prices` 에 신규 컬럼이 채워진 상태여야 Phase 4 의 snapshot 복사가 NULL 이 아닌 유효값을 가진다.

**Defense path (방어적 경로, defense-in-depth)**: 운영 실수로 기존 DB 를 그대로 둔 채 신규 코드만 배포된 경우를 대비하여 `meta_service.rebuild_stock_meta` 는 다음과 같이 동작한다:

1. `PRAGMA table_info(stock_meta)` 로 현재 컬럼 목록을 조회한다.
2. 기대 컬럼 집합 `{sma150, low52w, sma200_20d_ago}` 중 누락된 것만 `ALTER TABLE stock_meta ADD COLUMN <col> REAL` 로 추가한다 (REQ-MIN-008).
3. 그 다음 기존 재빌드 로직이 각 종목 최신 행을 읽을 때 SELECT 에 신규 컬럼을 포함시킨다.
4. INSERT/REPLACE 시 신규 컬럼 값을 저장한다.

이 경로는 **정상 배포가 아니지만** 운영 실수의 폭발 반경을 줄이고 `/api/screen` 이 500 을 반환하지 않도록 보장한다. 테스트는 유지하되 (AC-7, Group B 테스트), 부하·성능 최적화 대상은 아니다.

### 6.3 `_build_minervini_where()` 설계

```python
def _build_minervini_where() -> str:
    return (
        "("
        "close > sma150 AND close > sma200"                             # T1
        " AND sma150 > sma200"                                          # T2
        " AND sma200 > sma200_20d_ago"                                  # T3
        " AND sma50 > sma150 AND sma50 > sma200"                        # T4
        " AND close > sma50"                                            # T5
        " AND close >= low52w * 1.25"                                   # T6
        " AND close >= high52w * 0.75 AND close <= high52w"             # T7
        " AND rs_12m >= 70"                                             # T8
        ")"
    )
```

- 파라미터 바인딩이 필요 없는 **순수 상수 식**이므로 SQL injection 표면은 증가하지 않는다.
- 조건 순서는 **가장 탈락률이 높은 조건을 먼저** 배치할 수 있으나, SQLite 의 쿼리 플래너가 통계 기반으로 재배치하므로 가독성 순서를 우선한다.

### 6.4 점수 SELECT 확장 (strict gate, v1.0.1)

Strict gate 가 WHERE 절에서 이미 8조건 전체를 통과한 행만 남기므로, 반환되는 모든 행의 점수는 정의상 8 이다. 따라서 SELECT 는 다음과 같이 단순화된다:

```sql
SELECT code, name, ... , sma150, low52w, sma200_20d_ago,
  CASE WHEN :minervini_on = 1 THEN 8 ELSE NULL END AS trend_template_score
FROM stock_meta
WHERE ...
  AND (... 8조건 AND 결합 ...)   -- _build_minervini_where() 반환값
```

대안 (동등한 결과):

```sql
SELECT code, name, ... ,
  CASE WHEN :minervini_on = 1 THEN
    (CASE WHEN close > sma150 AND close > sma200        THEN 1 ELSE 0 END) +
    (CASE WHEN sma150 > sma200                           THEN 1 ELSE 0 END) +
    ... (8조건)
  END AS trend_template_score
FROM stock_meta
WHERE ...
```

두 방식 모두 **strict gate 에서 결과가 항상 8** 이다. 첫 번째 방식이 SQL 이 더 짧고 의도가 명확하다. 구현 재량으로 선택한다.

`minervini_trend_template` 이 false/None 이면 `trend_template_score` 는 NULL 로 반환되어 `StockItem.trend_template_score = None` 으로 직렬화된다.

\[HARD\] WHERE 을 느슨하게 풀고 HAVING + CASE SUM 으로 부분 매칭을 노출하는 리팩터는 **본 SPEC 에서 금지**한다. 부분 매칭은 §10 에 out of scope 로 명시된다.

### 6.5 컬럼 누락 가드 전략

옵션 A (선호): `_build_minervini_where()` 호출 직전에 `PRAGMA table_info(stock_meta)` 를 한 번 조회하여 컬럼 존재를 확인한다. 누락 시 WARN 로그 + 빈 응답을 즉시 반환한다.

옵션 B: `sqlite3.OperationalError` 를 try/except 로 잡는다.

옵션 A 는 예외 경로를 회피하여 성능 이점이 있고, 옵션 B 는 race condition 에서도 안전하다. **구현 시 옵션 A 를 우선 적용**하되, 예외 백업을 병행한다.

### 6.6 MX 태그 계획

| 태그 | 위치 | 이유 |
| --- | --- | --- |
| `# @MX:NOTE` | `_build_minervini_where()` 위 | 8조건 식이 research.md §2.1 에 대응된다는 맥락 전달 |
| `# @MX:ANCHOR` | `screen_stocks()` | fan_in ≥ 3 (router + 테스트 + 추후 preset service). `@MX:REASON: 사용자-facing 스크리닝 엔트리 포인트` |
| `# @MX:TODO` | `_build_minervini_where()` 초안 | RED 단계에서 추가, GREEN 에서 제거 |

`code_comments: ko` 설정에 따라 태그 설명은 한국어로 작성한다.

---

## 7. Dependencies (의존성)

### 7.1 Upstream 의존성 (본 SPEC 이 필요로 하는 선행 요소)

- **SPEC-RS-LINE-001**: `rs_12m` 컬럼이 이미 stock_meta 에 존재한다는 전제. 본 SPEC 은 이 값을 읽기만 한다.
- **기존 daily 파이프라인**: SMA200, Close, High, Low, Volume 계산이 동작 중이어야 한다.

### 7.2 Downstream 의존성 (본 SPEC 을 사용하는 후속 요소)

- **SPEC-PRESET-001 (예정)**: 프리셋 UI 가 `ScreenRequest.minervini_trend_template=true` 를 토글하는 칩을 제공한다. 또한 `patterns.max_length=5` 확장을 활용하여 사용자 정의 프리셋을 구성한다.
- **SPEC-VCP-XXX (미착수)**: VCP 패턴 감지가 본 SPEC 의 Minervini 통과 종목 집합을 후보로 사용할 가능성이 있다.
- **SPEC-VOLUME-BREAKOUT-XXX (미착수)**: 거래량 150% 돌파 감지가 Minervini 통과 종목에만 적용될 수 있다.

### 7.3 외부 라이브러리 의존성

신규 라이브러리 도입 없음. pandas, sqlite3, Pydantic v2, FastAPI 만 사용.

---

## 8. Risk Register (리스크와 완화)

| ID | 리스크 | 영향 | 발생 가능성 | 완화책 |
| --- | --- | --- | --- | --- |
| R1 | 배포 시 DB 재생성 실패 (Phase 3 또는 Phase 4 중단) 로 부분적으로 채워진 DB 가 남음 | 중 | 낮음 | **v1.0.2 전략 변경으로 blast radius 축소**: DB 파일 교체 방식이므로 부분 실패 시 `mv daily.db.bak daily.db` 로 즉시 복구 가능. **완화책**: 배포 스크립트에 `mv daily.db daily.db.bak && mv weekly.db weekly.db.bak` 단계 필수 포함. 파이프라인 실패 시 (1) 로그 확인 → (2) 백업 파일 복구 → (3) 재실행. 기존 `stock_meta` ALTER 동시 잠금 리스크는 새 DB 생성 플로우에서는 해당 없음 (defense path 에서만 유효하며 WAL 모드가 짧게 잠근다). |
| R2 | 일봉 파이프라인 실행 시간 증가 (rolling 250 윈도우) | 저 | 중 | pandas rolling 은 벡터화되어 종목당 수 ms 증가에 그친다. KOSPI+KOSDAQ 2,500 종목 기준 수 초 이내. 실측은 R&D 단계에서 확인. |
| R3 | 신규 컬럼 NULL 이 기존 필터 (PatternCondition) 와 상호작용하여 결과가 달라짐 | 중 | 낮음 | 기존 PatternCondition 의 indicator 매핑은 SMA50/100/200 에 한정되므로 SMA150 등 신규 컬럼과 교차하지 않는다. 회귀 테스트 (AC-6) 로 방어. |
| R4 | 250 거래일 rolling 이 메모리를 증가시킴 | 저 | 매우 낮음 | 종목별 DataFrame 은 2\~3천 행 수준이므로 영향 없음. |
| R5 | 레거시 DB 사용자 (마이그레이션 누락) 가 `/api/screen` 500 에러를 받음 | 고 | 중 | REQ-MIN-007 로 200 OK + empty + WARN log 를 보장. AC-8 로 회귀 방어. |
| R6 | `patterns.max_length` 3→5 확장이 Pydantic 검증에서 기존 클라이언트를 거부 | 고 | 매우 낮음 | 기존 클라이언트는 항상 3개 이하를 보내므로 확장은 완화 방향 (relaxation). 회귀 테스트로 확인. |
| R7 | Trend Template 8조건 해석 차이 (T6 배율 1.25 vs 1.30) | 중 | 낮음 | research.md §2.1 이 1.25 를 채택. Assumption A1 에 명시. 필요 시 설정화는 후속 SPEC. |
| R8 | `rs_12m` 업데이트 지연으로 T8 이 과거 값을 기준으로 평가됨 | 저 | 중 | 기존 파이프라인의 RS 계산 단계가 stock_meta 재빌드 이전에 수행되므로 snapshot 시점에는 최신값이다. |
| R9 | IPO 종목이 LOW_52W NULL 로 자동 탈락하는 것이 사용자 의도와 다를 수 있음 | 저 | 낮음 | Assumption A4 로 명시. 제품 결정 사항이며, 후속 SPEC 에서 완화 옵션을 제공할 수 있다. |
| R10 | strict gate 로 결과가 매우 희소할 때 (예: 0건) 사용자가 부분 매칭을 기대할 수 있음 | 중 | 중 | **not required; strict gate per user decision (2026-04-21)**. v1.0.1 에서 엄격 모드가 확정되었으며 WHERE → HAVING + CASE SUM 리팩터는 본 SPEC 범위 밖. §10 #10 참조. 향후 별도 SPEC 에서 UX 를 평가한다. |

---

## 9. Test Plan (TDD 접근)

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 이다 (`development_mode: tdd`).

### 9.1 RED Phase — 실패 테스트 선작성

신규 파일 `backend/tests/test_minervini_template.py` 에 다음 순서로 테스트를 먼저 작성하고 **모두 실패함을 확인**한다.

**Group A — 단위: rolling 계산 + Greenfield 파이프라인 (모듈** `my_chart/db/daily/`**)**

- `test_sma150_rolling_correctness` — 150일 선형 Close 입력 → `SMA150[149] == 174.5`
- `test_sma150_insufficient_history_null` — 100일 데이터 → 모든 SMA150 값이 NULL
- `test_52w_rolling_high_low_correctness` — 300일 High/Low 입력 → rolling 250 max/min 검증
- `test_52w_ipo_under_250days_null` — 150일 데이터 → HIGH_52W, LOW_52W 전부 NULL
- `test_sma200_20d_ago_shift` — SMA200 배열을 shift(20) 과 동일하게 생성
- `test_sma200_20d_ago_null_for_short_history` — 215일 데이터 → `SMA200_20D_AGO` 전부 NULL (SMA200 이 200일 이후 유효 + 20일 shift → 220일 이후부터 유효)
- `test_greenfield_db_all_columns_present_after_pipeline` — Primary path 검증 (v1.0.2). 빈 디렉토리에서 시작하여 `stock_prices` 와 `stock_meta` 가 존재하지 않는 상태로 `db_service.update_all()` 을 **1회** 실행한 후:
  - `PRAGMA table_info(stock_prices)` 결과에 `SMA150, HIGH_52W, LOW_52W, SMA200_20D_AGO` 가 포함된다
  - `PRAGMA table_info(stock_meta)` 결과에 `sma150, high52w, low52w, sma200_20d_ago` 가 포함된다
  - 250 거래일 이상의 히스토리를 가진 fixture 종목들에 대해 위 4개 컬럼의 **NULL 비율 ≤ 5%** (거의 모든 행이 채워짐)
  - 운영 환경에서는 실제로 별도 ALTER 호출이 트리거되지 않았음을 확인 (PRAGMA 검사 후 누락 없음 → ALTER skip)

**Group B — 단위: meta_service 멱등 ALTER**

- `test_meta_alter_adds_missing_columns` — 빈 stock_meta → rebuild 후 sma150/low52w/sma200_20d_ago 존재
- `test_meta_alter_idempotent` — rebuild 두 번 호출 → 컬럼 중복 없음 (PRAGMA table_info 카운트)
- `test_meta_latest_value_copied` — 최신 일봉 행의 SMA150 값이 stock_meta.sma150 과 일치

**Group C — 통합: screen_service WHERE + 점수 (strict gate)**

- `test_minervini_where_all_conditions_met` — fixture S9 (모든 조건 통과) → 결과 포함 + score=8
- `test_minervini_where_each_boundary_case` — S1\~S8 각각 조건 하나씩 실패 → 결과에서 제외 (parametrize). 부분 점수 (7) 는 노출되지 않음을 확인
- `test_trend_template_score_is_8_for_all_returned_rows` — strict gate 검증. 응답의 모든 `StockItem` 에 대해 `trend_template_score == 8` (전수 assert). 0\~7 값은 결과에 존재하지 않음
- `test_trend_template_score_none_when_flag_off` — `minervini_trend_template=false` 또는 None → score=None
- `test_minervini_with_existing_filters_combined` — market_cap_min + minervini 플래그 AND 결합 동작

**Group D — 회귀: 기존 필터 불변성**

- `test_existing_chg_filters_unchanged` — chg_1w/1m/3m 기존 응답과 byte-level 동일
- `test_existing_patterns_unchanged` — patterns\[0..3개\] 기존 응답과 동일
- `test_patterns_max_length_5_accepts_4_or_5` — Pydantic 이 4개, 5개 pattern 을 허용 (기존 3개는 물론 허용)
- `test_patterns_max_length_5_rejects_6` — Pydantic 이 6개는 거부

**Group E — Defense path (운영 실수 대비, defense-in-depth; v1.0.2 reframing)**

> 본 그룹은 Primary path (전체 DB 재생성) 가 아닌 **운영 실수 시나리오** 를 검증한다. 기존 DB 파일을 삭제하지 않은 채 신규 코드만 배포된 경우를 모사한다.

- `test_defense_missing_columns_returns_200_empty` — 레거시 stock_meta (신규 컬럼 없음) + `minervini=true` → 200 OK, total=0, sectors=\[\]
- `test_defense_warn_log_emitted_once` — 동일 요청에서 caplog 로 WARN 1회 확인 (로그 문구: `"[minervini] required columns missing; delete DB files and re-run db-update pipeline"`)
- `test_defense_other_filters_still_work` — 같은 레거시 DB + `minervini=false` + market_cap_min → 정상 결과 (defense path 가 기존 필터에 영향 없음)

### 9.2 GREEN Phase — 최소 구현

위 테스트가 모두 통과하도록 최소 구현을 작성한다. 이 SPEC 은 코드를 포함하지 않으며, 구현은 `/moai run SPEC-MINERVINI-001` 단계에서 수행한다.

### 9.3 REFACTOR Phase

- `_build_minervini_where()` 의 조건 식을 SQL 상수 문자열에서 enum 기반 상수로 승격 (선택)
- fixture 공통화 (10종목 경계 케이스 → pytest fixture)
- @MX 태그 추가 (NOTE, ANCHOR)

### 9.4 커버리지 목표

- `backend/services/screen_service.py`: 90% 이상
- `backend/services/meta_service.py`: 85% 이상
- 신규 로직 (rolling 계산 함수): 95% 이상

### 9.5 수동 검증 (Post-Automation)

- 실제 KRX 일봉 DB (최근 250 거래일 이상) 로 `/api/refresh` 실행
- `POST /api/screen { minervini_trend_template: true }` 를 KOSPI 우량주 표본 100 종목에 적용
- 결과 종목들이 차트에서 Stage 2 상승 추세로 확인되는지 샘플링 검토 (3\~5 종목)

---

## 10. Out of Scope (범위 밖 — 명시)

본 SPEC 은 다음을 **다루지 않는다**. 각 항목은 별도 SPEC 으로 분리된다.

 1. **프리셋 칩 UI / 프리셋 버튼 / 프리셋 상태 관리** → SPEC-PRESET-001
 2. **VCP (Volatility Contraction Pattern) 자동 감지 알고리즘** → 향후 SPEC (research.md §5.2 P3)
 3. **거래량 돌파 감지 (150%+)** → 향후 SPEC
 4. **시장 환경 필터 (KOSPI/KOSDAQ 추세 기반)** → 향후 SPEC
 5. **주봉 SMA30 추가** → research.md §5.2 P1 에 언급되나 본 SPEC 은 일봉만 다룸. 주봉 확장은 필요 시 별도 SPEC
 6. **프런트엔드 UI 변경** (칩, 토글 위젯, 점수 시각화) → SPEC-PRESET-001 및 후속 UI SPEC
 7. `patterns.max_length` **확장의 실제 활용** (5개 pattern 조합 UI) → SPEC-PRESET-001 에서 소비. 본 SPEC 은 Pydantic 제약 완화만 수행
 8. **손절/익절/포지션 사이징 로직** — 이는 screener 의 범위가 아니며, 별도 트레이딩 모듈의 책임
 9. **설정화된 임계값 (Configurable RS threshold 포함)** — T6 의 1.25, T8 의 `rs_12m >= 70` 등을 `.env` / config 로 외부화하여 사용자가 조정할 수 있게 하는 기능은 **본 SPEC 에서 다루지 않는다**. 현재는 research.md §2.1 의 하드코딩 기준값을 유지한다. 필요성 확인 후 별도 SPEC 으로 분리한다.
10. **부분 매칭 점수 (Partial-Match Score Exposure)** — 6/8, 7/8 등 일부 조건만 통과한 종목을 점수와 함께 노출하는 기능은 **명시적으로 out of scope** 이다 (v1.0.1 2026-04-21 결정). 본 SPEC 은 **strict gate** 로만 동작하며, 반환되는 모든 행은 8조건을 모두 통과한다 (score 는 항상 정확히 8). WHERE 를 HAVING + CASE SUM 으로 바꿔 부분 매칭을 허용하는 리팩터 또한 **금지**된다. 향후 사용자 UX 연구 후 별도 SPEC 으로 평가한다.
11. **점진적 ALTER 마이그레이션 (파일 교체가 정상 경로)** — 기존 DB 를 유지한 채 새 컬럼만 백필하는 점진적 마이그레이션 전략은 **본 SPEC 의 정상 경로가 아니다** (v1.0.2 2026-04-21 결정, Assumption A9 참조). 배포 시 기존 `daily.db` / `weekly.db` 파일을 삭제하고 `db-update` 파이프라인을 전체 재실행하여 새 DB 를 생성하는 **파일 교체 전략**이 Primary path 이다. REQ-MIN-008 의 idempotent PRAGMA + ALTER 로직과 REQ-MIN-007 의 누락 컬럼 fallback 은 **defense-in-depth 백업**으로만 유지되며, 성능 튜닝 / 프로덕션 규모 백필 / 다운타임 최소화 마이그레이션 플레이북은 본 SPEC 범위 밖이다. 필요 시 운영 런북에서 별도로 다룬다.

---

문서 버전: 1.0.3 작성일: 2026-04-21 (v1.0.0 초안), 2026-04-21 (v1.0.1 shift 값/strict 결정 반영), 2026-04-21 (v1.0.2 DB 파일 교체 전략 반영), 2026-04-21 (v1.0.3 구현 완료 및 Implementation Notes) 작성자: MoAI (manager-spec) 기반 리서치: `.moai/specs/SPEC-MINERVINI-001/research.md` v1.1.0 (2026-03-08)

---

## 11. Implementation Notes (v1.0.3 — 2026-04-21)

본 섹션은 `/moai run` + `/moai sync` 완료 시점의 **실제 구현 상태**를 기록한다. SPEC 의 원본 요구사항과 실제 산출물 사이의 divergence 및 의사결정을 보존하여 이후 유지보수에 활용한다.

### 11.1 Divergence from Original SPEC

| 항목 | SPEC 기재 | 실제 구현 | 사유 |
| --- | --- | --- | --- |
| 파이프라인 파일 경로 | `my_chart/db/daily/price_daily_db.py` | `my_chart/db/daily.py` (함수 `price_daily_db()` 포함) | 기존 모듈 구조가 SPEC 표기와 달랐음. 실제 구조를 따름. |
| `HIGH_52W` 컬럼 생성 | "신규 컬럼 추가" (§4.2 스키마 표) | 기존 `stock_prices.High52W` 컬럼 **재사용**, rolling window만 252 → **250** 으로 변경 | SQLite는 컬럼명 대소문자 무시. 기존 컬럼의 정의만 250 거래일(SPEC A2)에 맞춰 조정. 신규 컬럼은 `SMA150`, `LOW_52W`, `SMA200_20D_AGO` 3개만 추가. 사용자 승인 (2026-04-21). |
| SPEC 원본의 `High52W` 값 | window=252 결과 | window=250 결과 | SPEC A2 요구사항과 일치. 영향 범위: 기존 `High52W` 를 읽는 모든 코드 (스크리너 7번 조건, 차트 상단 표식 등). Minervini T7은 이 값을 사용한다. |

### 11.2 구현 산출물

**Git 이력 (2 commits on** `main`**):**

- `79de6a8` — `feat(minervini): SPEC-MINERVINI-001 — Mark Minervini Trend Template 스크리너 구현`
  - `my_chart/db/daily.py` (+77/-0 이후 cd72fcb 로 조정) — `_compute_minervini_indicators()` 추가
  - `backend/services/meta_service.py` (+73/-0) — 멱등 ALTER + 스냅샷 4개 컬럼 복사
  - `backend/schemas/screen.py` (+16/-1) — `minervini_trend_template`, `trend_template_score`, `patterns max_length=5`
  - `backend/services/screen_service.py` (+99/-0 이후 cd72fcb 로 조정) — `_build_minervini_where()` + 가드 + strict gate
  - `backend/tests/test_minervini_template.py` (+790/-0) — 신규 28개 테스트 (Group A-E)
  - `frontend/src/types/filter.ts` (+24/-0) — TypeScript 타입 미러
- `cd72fcb` — `refactor(minervini): SPEC-MINERVINI-001 Simplify 패스 개선`
  - `CASE WHEN 1=1 THEN 8 ELSE NULL END` 타우톨로지 → 상수 `"8"`
  - `_MINERVINI_META_COLS` 를 `meta_service` 에서 공유 import (상수 중복 제거)
  - `@MX:REASON` 을 strict-gate invariant contract 로 재작성 (caller 열거 대신 계약 명시)
  - `except sqlite3.OperationalError` fallback 의 misleading WARN 메시지 수정
  - `_compute_minervini_indicators` docstring/주석 bloat 축약

**@MX 태그:**

| 위치 | 태그 | 내용 |
| --- | --- | --- |
| `screen_service.py:_build_minervini_where` | `@MX:NOTE` | 순수 상수 SQL — SQL injection 표면 없음 |
| `screen_service.py:screen_stocks` | `@MX:ANCHOR` + `@MX:REASON` | strict-gate invariant — `minervini_trend_template=True` 로 반환되는 모든 행은 8조건 통과 + `trend_template_score=8` 보증 |

### 11.3 품질 검증 결과

- **테스트**: `pytest backend/tests/test_minervini_template.py -v` → **28 passed**, 1 warning (pykrx pkg_resources deprecation, 무관)
- **회귀**: 기존 `backend/tests/` 스위트 141 passed (pre-existing `test_sector_advanced.py` 5 실패는 SPEC-MINERVINI-001 과 무관)
- **커버리지 추정**: `screen_service.py` (신규 코드) \~94% / `meta_service.py` (신규 코드) \~96% / `my_chart/db/daily.py:_compute_minervini_indicators` \~100%
- **ruff lint**: 신규 코드 경고 0. 기존 `meta_service.py:7, :222` 의 I001 (import ordering) 2건은 pre-existing 이며 SPEC 범위 밖 (Scope discipline).

### 11.4 배포 단계 체크리스트 (운영자 용)

v1.0.2 Primary path 에 따라 운영자는 배포 시 다음을 수행해야 한다:

```bash
# 1. 기존 DB 파일 백업 및 삭제
mv daily.db daily.db.bak
mv weekly.db weekly.db.bak

# 2. db-update 파이프라인 전체 재실행 (FastAPI 서버 기동 후)
curl -X POST http://localhost:8000/api/refresh
# 또는 동등한 CLI 엔트리

# 3. 검증: stock_meta 에 신규 컬럼 확인
sqlite3 daily.db "PRAGMA table_info(stock_meta)" | grep -E "sma150|low52w|sma200_20d_ago"
```

코드 배포만 완료하고 DB 재생성이 누락된 경우는 **defense path** (REQ-MIN-007)가 작동하여 `minervini_trend_template=true` 요청은 HTTP 200 + empty 응답을 반환하고 WARN log 를 남긴다. 운영자는 로그를 확인한 후 위 절차를 실행한다.

### 11.5 후속 SPEC

- **SPEC-PRESET-001** (미구현, 예정): 본 SPEC 이 노출한 `ScreenRequest.minervini_trend_template` 플래그와 `patterns.max_length=5` 확장을 실제 UI (칩, 토글, 프리셋) 로 활용한다. 본 SPEC 완료가 선행 조건이었다.
- VCP 패턴, 거래량 돌파, 시장 환경 필터는 별도 SPEC 으로 분리 유지 (§10 참조).