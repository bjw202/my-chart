# SPEC-RS-REBALANCE-001 — 코드베이스 조사 (research)

> 작성: 2026-10-20, manager-spec. 모든 주장 옆에 그것을 관측한 명령을 둔다(lessons #10).
> 작업 디렉터리: `/Users/byunjungwon/Dev/my-project-01/my_chart`. DB 프로브는 실행 중인 서버와 충돌하지 않도록 `sqlite3 "file:$PWD/Output/<db>?immutable=1"` 형태의 읽기 전용 URI로 실행했다. 일반 `-readonly` 열기는 WAL 모드 때문에 `unable to open database file (14)`로 실패했다.
> "orchestrator pre-probe"로 표시한 항목은 오케스트레이터가 먼저 관측했고 이 세션에서 같은 명령으로 다시 확인한 것이다.

## R1. 현행 RS 산식과 재생성 경로 (`my_chart/db/weekly.py`)

명령: `sed -n 395,470p my_chart/db/weekly.py`, `grep -n "def generate_rs_db" my_chart/db/*.py`

- `generate_rs_db()`는 `weekly.py:390`에 정의된다.
- 처리 날짜는 기준 종목(`REFERENCE_STOCK = "삼성전자"`, `my_chart/config.py:32`)의 `stock_prices` 날짜 목록이다(`weekly.py:416-421`).
- 날짜마다 `SELECT * FROM stock_prices WHERE Date = ?` 후 `df.dropna()`를 적용하고(`weekly.py:425-430`), 그 행 집합 전체가 순위 분모가 된다. 지수 행(`KOSPI`, `KOSDAQ`)도 결측이 없으면 분모에 들어간다.
- 산식(`weekly.py:436-456`, orchestrator pre-probe 재확인):
  - `RS_12 = rank_1m + 0.8*rank_3m + 0.6*rank_6m + 0.4*rank_9m + 0.2*rank_12m`, `RS_12M_Rating = RS_12.rank(pct=True)*100`
  - `RS_6 = rank_1m + rank_3m + rank_6m`, `RS_3 = rank_1m + rank_3m`, `RS_1M_Rating = rank_1m`
- 저장은 `_batch_insert_rs()`의 `INSERT OR REPLACE INTO relative_strength` (`weekly.py:188`). 기존 행을 지우는 단계가 없다.
- 지수 행 출처: `generate_price_db()`가 `price_naver_rs("KOSPI"/"KOSDAQ")`를 받아 `stock_prices`에 일반 행으로 삽입한다(`weekly.py:335-343`).

## R2. `relative_strength` 고아 행 (D7 근거) — 실측

명령(모두 `Output/stock_data_weekly.db`, immutable 읽기):

| 질의 | 결과 |
|---|---|
| `SELECT COUNT(*), COUNT(DISTINCT Date), COUNT(DISTINCT Name), MIN(Date), MAX(Date) FROM relative_strength;` | `794818\|346\|2537\|2021-01-22\|2026-10-16` |
| `SELECT COUNT(*), COUNT(DISTINCT rs.Date), COUNT(DISTINCT rs.Name) FROM relative_strength rs LEFT JOIN stock_prices sp USING(Name, Date) WHERE sp.Name IS NULL;` | `119881\|327\|2535` |
| 고아 행 중 `stock_prices`에 아예 없는 날짜에 속한 행 | `104411` (해당 날짜 `42`개) |
| 고아 행 중 유효 날짜에 있으나 `stock_prices`에 아예 없는 이름의 행 | `5507` (해당 이름 `21`개) |
| 나머지(이름·날짜는 각각 존재하나 쌍이 없음) | `9963` 행, 날짜 `4`개 |

나머지 4개 날짜의 정체(명령: 날짜별 `COUNT(*)` 비교):

```
2026-06-29 sp=2 rs=2495
2026-07-06 sp=1 rs=2490
2026-08-10 sp=1 rs=2491
2026-09-02 sp=1 rs=2492
```

`stock_prices`에는 한두 종목만 남은 주중 날짜인데 `relative_strength`에는 전 종목 행이 남아 있다. 계획서가 말한 "주중 날짜 42개 10만 4천 행, 옛 종목명 21개"는 실측(104,411행/42일, 21개 이름)과 일치하며, **그 밖에 쌍 불일치 9,963행이 더 있어 합계는 119,881행이다.** `(Name, Date)` 쌍 기준 삭제는 세 원인을 모두 덮는다.

지수 행: `SELECT Name, COUNT(*) FROM relative_strength WHERE Name IN ('KOSPI','KOSDAQ') GROUP BY Name;` → `KOSDAQ|346`, `KOSPI|346`.

`stock_prices` 날짜 밀도: `SELECT COUNT(DISTINCT Date) ... FROM stock_prices` → `368` 날짜. 기준 종목 날짜 수 `355`(2020-01-03~2026-10-16). 행 수 100 미만인 날짜 `13`개, 100 이상 `355`개. 즉 `stock_prices` 자체에도 1~2행짜리 주중 날짜 13개가 있다. RS 루프는 기준 종목 날짜만 돌기 때문에 이 13개 날짜는 처리되지 않는다(본 SPEC 범위 밖, plan.md §E 위험에 기록).

### R2.1 짝이 있는데도 남는 낡은 행 (plan-audit iter-1 D1, 이 세션 재측정)

`(Name, Date)` 짝 기준 삭제로는 지워지지 않고, 이번 실행이 같은 쌍을 다시 쓰지 않으므로 `INSERT OR REPLACE`로도 덮이지 않는 행이다.

| 질의 (`relative_strength rs JOIN stock_prices sp USING(Name, Date)`) | 결과 |
|---|---|
| `WHERE rs.Name IN ('KOSPI','KOSDAQ') GROUP BY rs.Name` | `KOSDAQ\|300`, `KOSPI\|300` (지수 행 692개 중 짝 없는 고아는 92개뿐) |
| `WHERE sp.Volume = 0` | `16369` |
| `WHERE sp.Volume = 0 AND rs.Date = '2026-10-16'` | `101` |
| `WHERE rs.Date NOT IN (SELECT Date FROM stock_prices WHERE Name='삼성전자')` → `COUNT(*), COUNT(DISTINCT rs.Date)` | `5\|4` |

최신 주차의 거래량 0 행 101개는 `stock_meta.rs_12m`, 섹터 `rs_avg`, Stage 분류로 흘러간다. 따라서 REQ-RSR-001은 "이번 실행이 쓰지 않은 행은 모두 지운다"로 정했다(spec.md §3.1).

전체 삭제를 택하지 않는 근거: `sed -n 1,10p my_chart/db/weekly.py` → `:7` `- INSERT OR REPLACE (UPSERT) instead of DROP TABLE` — 의도된 설계로 기록되어 있다.

## R3. 순위 분모 정리 후보 (D5) — 실측

명령: 최신 주차 `2026-10-16` 기준 `stock_prices` 질의.

| 패턴 | 이름 수 |
|---|---|
| `Name LIKE '%우'` | `3` — `성우 에코글로우 이오플로우` |
| `Name LIKE '%우B'`, `'%우C'`, `'%우(전환)'` | `0`, `0`, `0` |
| `Name LIKE '%스팩%'`, `'%SPAC%'` | `0`, `0` |
| 전체 기간 합집합(`%우`, `%우B`, `%우C`, `%스팩%`, `%SPAC%`) | `성우 에코글로우 이오플로우` 3개뿐 |

종목 코드 끝자리(우선주 코드는 통상 끝자리가 0이 아니다): `sqlite3 "file:.../stock_data_daily.db?immutable=1" "SELECT substr(code,6,1) d, COUNT(*) FROM stock_meta GROUP BY d;"` → `0|2533`. 끝자리가 0이 아닌 코드는 하나도 없다.

등록부 자체 프로브(plan-audit iter-1 D12 정정 — 위 2,533은 `stock_meta` 기준이었다): `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -c "…from my_chart.registry import get_stock_registry as g; d=g(); c=d.Code.astype(str).str.zfill(6); print(len(d), c.str[-1].value_counts().to_dict(), d.Name.str.contains('스팩').sum(), d.Name.str.contains('SPAC').sum())"` → `2559 {'0': 2559} 0 0` (로그 한 줄: 중복 Code `052770` 1행 제거). `generate_rs_db()`가 쓰는 등록부(`weekly.py:24`, `:331`)에서 코드 끝자리는 모두 `0`, 이름에 `스팩`·`SPAC`이 든 종목은 0개다.

**해석**: 종목 등록부(`my_chart/registry.py:108` `get_stock_registry()`, 출처 `sectormap-original.xlsx`)는 현재 우선주·스팩을 담고 있지 않다. 계획서의 이름 패턴(`…우`, `…우B`, `…스팩`)을 그대로 쓰면 **실제 우선주 0개를 제외하고 보통주 3개(성우, 에코글로우, 이오플로우)를 잘못 제외한다.** 이 판별 규칙은 2026-10-20 사용자 결정으로 코드 끝자리 ≠ `0`(우선주) + 이름에 `스팩`(스팩) 규칙으로 정했다(spec.md §2.4 B-1). 현재 등록부에서 이 규칙의 제외 대상은 0개다.

거래량 0: 최신 주차 `Volume=0 OR Volume IS NULL` → `101`행. 전 기간 `Volume=0` → `19496`행.

원시 수익률 단위: 최신 주차 `삼성전자` `RS_3M = -0.1302…`, `RS_12M = 1.2165…` — 소수 비율(백분율 아님). 지수 제외 전 기간 최솟값: `MIN(RS_3M), MIN(RS_6M), MIN(RS_9M), MIN(RS_12M)` = 모두 `-0.99887…`, `RS_kM <= -1`인 행 수 `0`. 따라서 비율 기반 분기 수익률의 분모 `1+R`은 관측 데이터에서 항상 양수다.

### R3.1 결측 수익률 행 (plan-audit iter-1 D4, 이 세션 재측정)

`weekly.py:425-430`은 `SELECT * FROM stock_prices WHERE Date = ?` 뒤 `df.dropna()`를 적용하므로, 약 35개 컬럼 중 하나라도 NULL이면 그 행은 등급을 받지 못한다.

질의(최신 주차 `2026-10-16`): `SELECT COUNT(*), SUM(RS_12M IS NULL), SUM(RS_1M IS NULL OR RS_3M IS NULL OR RS_6M IS NULL OR RS_9M IS NULL OR RS_12M IS NULL) FROM stock_prices WHERE Date='2026-10-16'` → `2535|44|44`. 같은 날짜 `relative_strength` 행 수 → `2490`. 차이 45행의 내역: `RS_*` 결측 44행, 그리고 `RS_*`는 모두 있으나 `SMA40_Trend_4M`이 NULL인 `명인제약` 1행(질의: 가격 행 중 RS 행이 없고 `RS_1M`~`RS_12M`이 모두 NOT NULL인 이름 → `명인제약`; 그 행의 NULL 컬럼 → `['SMA40_Trend_4M']`). 즉 현행 `dropna`는 `RS_*` 결측보다 넓게 행을 뺀다. REQ-RSR-023은 이 현행 동작(전 컬럼 `dropna`)을 넓히지도 좁히지도 않고 그대로 고정한다.

## R4. 소비처 — `RS_12M_Rating`(주간) / `stock_meta.rs_12m`(일봉)

명령: `grep -rn "RS_12M_Rating" my_chart backend frontend/src --include='*.py' --include='*.ts' --include='*.tsx' | grep -v -E '/tests?/|test_|\.test\.'` 및 `grep -rln "rs_12m" …`

주간(`relative_strength.RS_12M_Rating`) 직접 소비 — 계획서 목록 대비:

| 파일 | 형태 | 계획서 목록 |
|---|---|---|
| `my_chart/analysis/stage_classifier.py:19,25,79,187,272` | `_STAGE2_ENTRY_RS_MIN = 70.0`, `_STAGE2_RS_STRONG = 60.0`, 주간 조인 질의 | 있음 |
| `my_chart/analysis/sector_metrics.py:58,124,403,530` | `_RS_TOP_THRESHOLD = 80.0`, 집계 | 있음 |
| `my_chart/analysis/sector_advanced.py:240-249` `_get_rs_on_date()` | 종목 버블·트리맵의 RS 공급원 | **누락** |
| `my_chart/db/queries.py:51,91` | `RS_12M_Rating > 80` | 있음 |
| `my_chart/screening/momentum.py:109,299,322` | `{rs_col} > 80`, 기본 `rs_rating=90` | 있음 |
| `my_chart/charting/single.py:142`, `bulk.py:329,353` | 차트 선(값만 변함) | 있음 |
| `backend/services/meta_service.py:217` | 최신 주차 → `stock_meta.rs_12m` 복사 | 있음 |
| `backend/services/stage_service.py:285` | `stock["RS_12M_Rating"]` | 있음 |
| `backend/schemas/screen.py:36` | `rs_min` 설명 문자열 | 없음(설명만) |

일봉(`stock_meta.rs_12m`) 소비 — `screen_service.py:61`(`rs_12m >= 70` 리터럴), `:106`, `:179`; `sector_detail_service.py:78-178`(소그룹 평균·정렬); `sector_advanced_service.py:176,388`(값 전달). 계획서 목록과 일치.

프론트 임계값 리터럴(명령: `grep -rn -E "rs[_a-zA-Z0-9]*\s*(>=|>|<=|<)\s*[0-9]+|…" …`):

- `frontend/src/components/StockExplorer/StockTable.tsx:39` — `rs: c.rs_12m >= 70` **상수 미사용 리터럴**
- `frontend/src/components/StockExplorer/StockTable.tsx:62` — `RS_S2_STRONG_THRESHOLD` 사용
- `frontend/src/components/ChartGrid/ChartCell.tsx:307,338` — `RS_TOP_THRESHOLD` 사용 + 상수 유래 title
- `frontend/src/components/SectorAnalysis/SectorRankingTable.tsx:158` — `RS_TOP_THRESHOLD` 유래 title
- `frontend/src/utils/rsMetrics.ts:10,13,16` — `RS_TOP_THRESHOLD = 80`, `RS_STRONG_THRESHOLD = 70`, `RS_S2_STRONG_THRESHOLD = 60`

백엔드 리터럴: `backend/services/screen_service.py:61` `" AND rs_12m >= 70"`(T8) — `_STAGE2_ENTRY_RS_MIN`을 참조하지 않는 중복 리터럴.

## R5. DB 갱신 파이프라인 (계획서 §4.1 확인)

명령: `grep -n "def _run_update\|Phase\|generate_rs_db\|rebuild_stock_meta\|price_daily_db\|generate_price_db" backend/services/db_service.py`, `grep -rn "db/update" frontend/src`

- 프론트: `frontend/src/components/FilterBar/DbUpdateButton.tsx` → `hooks/useDbUpdate` → `frontend/src/api/db.ts:5` `client.post('/db/update')`
- 라우터: `backend/routers/db.py:20-27` `@router.post("/db/update")` → `start_update(DAILY_DB_PATH, WEEKLY_DB_PATH)`
- 서비스: `backend/services/db_service.py:64` `_run_update()`
  - Phase 1 `:67-70` `generate_price_db()` (`weekly_prices`)
  - Phase 2 `:76-79` `generate_rs_db()` (`weekly_rs`)
  - Phase 3 `:84-87` `price_daily_db()` (`daily_prices`)
  - Phase 4 `:92-95` `rebuild_stock_meta()` (`rebuilding_meta`)

계획서의 순서·함수명과 일치한다.

## R6. `stock_meta`의 성격 — 계획서 주장 정정

계획서 §4: "`stock_meta`는 재구축 테이블이라 마이그레이션 없이 DDL만 바꾸면 됨". 관측은 이와 다르다.

명령: `sed -n 20,130p backend/services/meta_service.py`, `grep -n "DELETE FROM stock_meta\|DROP" backend/services/meta_service.py`, 라이브 DB `PRAGMA table_info(stock_meta)`

- DDL은 `CREATE TABLE IF NOT EXISTS`(`meta_service.py:23`)이고, 재구축은 `DELETE FROM stock_meta`(`:341`) 후 재삽입이다. **`DROP`은 없다.** 기존 테이블은 새 컬럼을 자동으로 얻지 못한다.
- 이를 위해 이미 멱등 ALTER 경로가 있다: `_MINERVINI_META_COLS = ("sma150", "low52w", "sma200_20d_ago", "sma5")`와 `_ensure_meta_minervini_columns()`(`:112-124`, `_rebuild` `:134`에서 호출).
- 삽입은 위치 기반 `VALUES (?,…)` 27개(`:342-344`)이며, 행 튜플 순서가 물리 컬럼 순서에 의존한다(`rs_12m`은 `:330`).
- 라이브 일봉 DB의 실제 컬럼: `… chg_3m rs_12m ma50_w ma150_w ma200_w last_updated sma150 low52w sma200_20d_ago sma5` — DDL의 `sma10_w sma20_w sma40_w`와 **이름이 다르다**. 레거시 테이블이 그대로 살아 있고 위치 삽입이라 동작하고 있을 뿐이다.

결론: `rs_1m` 추가는 (1) 멱등 ALTER로 **테이블 끝에** 덧붙이고 (2) 행 튜플의 **맨 끝**에 값을 덧붙여야 한다. DDL만 바꾸면 라이브 DB에는 컬럼이 생기지 않고, 튜플 중간에 끼우면 위치 시프트로 값이 엇갈린다.

## R7. 프론트 표시 지점

명령: `ls frontend/src/components/SectorAnalysis/`, `grep -rn "rs_avg\|rs_top_pct" frontend/src/components/SectorAnalysis/*.tsx …`, `grep -n "rs_12m" …StockBubbleChart.tsx …StockTable.tsx`

- 섹터 테이블: `SectorRankingTable.tsx:50`(`RS Avg` 열), `:52`(`RS 80+ 비중` 열 — breadth는 이미 표시 중), `:158`(상수 유래 title), `:232-244`(셀 렌더). 데이터: `/sectors/ranking` → `backend/schemas/sector.py:26` `SectorRankItem`(`rs_avg :33`, `rs_top_pct :34`), 타입 `frontend/src/types/market.ts:95`.
- 봉투 `data[]`: `backend/schemas/envelope.py:95-96,209-210` (`rs_avg`, `rs_top_pct`).
- 섹터 상세 패널: `SectorDetailPanel.tsx:105-106`(카드), `:145`(소그룹 평균).
- 종목 버블: `StockBubbleChart.tsx:175`(`s.rs_12m`), 타입 `frontend/src/types/bubble.ts:27`, 스키마 `backend/schemas/sector_advanced.py:48` `StockBubbleItem`(`rs_12m :53`), 데이터 `my_chart/analysis/sector_advanced.py:240` `_get_rs_on_date()`(주간 `relative_strength`).
- 종목 테이블: `StockExplorer/StockTable.tsx:236`(`rs_12m` 셀), 데이터 `/stage/overview` → `backend/schemas/stage.py:36` `StageStock`(`rs_12m :46`), 원천 `stage_classifier.py:183-193` 주간 조인 질의(`rs.RS_12M_Rating`만 선택).

**관측**: 계획서가 지목한 두 종목 표시면(종목 테이블·버블)은 모두 **주간 `relative_strength`**를 읽고, `stock_meta`를 읽지 않는다. 따라서 `stock_meta.rs_1m`(D3의 "일봉 쪽 공급원")에는 이 두 화면 안에 소비처가 없다. 일봉 쪽 소비처 후보는 `stock_meta.rs_12m`을 이미 읽는 `screen_service.py` 경유 화면(`ChartGrid/ChartCell.tsx` RS 배지 등)이다. 2026-10-20 사용자 결정(B-2): `stock_meta.rs_1m`은 채우기와 API 노출까지만 하고 일봉 화면 연결은 후속 과제로 미룬다. 두 종목 화면의 배지는 주간 `RS_1M_Rating`에서 공급한다(spec.md §2.4).

## R8. 영향받는 기존 테스트 — 개수

명령: `grep -cE '^\s*(async )?def test_' <file>` (프론트는 `^\s*(it|test)\(`)

| 파일 | 테스트 수 | 영향 |
|---|---|---|
| `tests/test_weekly_insert.py` | 10 | `_batch_insert_rs` DDL 왕복 — 스키마 불변이므로 변경 없이 통과해야 함 |
| `tests/test_stage_classifier.py` | 14 | M3에서 임계값이 바뀌면 경계값 기대 재검토 |
| `backend/tests/test_stage_service.py` | 3 | 동일 |
| `tests/test_meta_service.py` | 15 | `rs_1m` 컬럼·ALTER 경로 추가 |
| `tests/test_db_service.py` | 18 | `generate_rs_db`를 참조(파이프라인 순서) — 순서 불변 확인 |
| `tests/test_sector_metrics.py` | 12 | `rs_med` 추가 |
| `tests/test_sector_aggregation.py` | 21 | 봉투 `data[]` 필드 추가 |
| `tests/test_ac_sag_030_rs_avg.py` | 4 | `rs_avg` 의미 불변 확인 |
| `tests/test_screen_service.py` | 32 | M3에서 T8(`rs_12m >= 70`)이 바뀌면 영향 |
| `frontend/src/utils/__tests__/rsMetrics.test.ts` | 2 | 교차 언어 등식 테스트 — AC 확장 대상 |

변경 기호(`RS_12M_Rating`, `rs_12m`, `RS_1M_Rating`, `generate_rs_db`)를 참조하는 테스트 파일 전체 목록과 파일별 판정은 plan.md §G에 있다(49개: Python 25, 프론트 24 — 세는 명령도 그곳에 있음). 이 중 13개 Python 파일은 `RS_1M_Rating` 없는 축약 `relative_strength` DDL을 만들므로 M4의 질의 변경에 반응할 수 있다. (0.1.0의 "Python 22개·프론트 28개"와 "대부분 반응하지 않는다"는 문장은 세는 명령이 달랐고 판정 근거가 없어 삭제했다.)

교차 언어 등식 테스트: `frontend/src/utils/__tests__/rsMetrics.test.ts:10,37,44-47`이 `node:fs`로 `sector_metrics.py`를 읽어 `_RS_TOP_THRESHOLD`를 수치로 추출해 `RS_TOP_THRESHOLD`와 비교한다. `:50-54`는 `RS_STRONG_THRESHOLD === 70`, `RS_S2_STRONG_THRESHOLD === 60`을 **리터럴로** 단언한다(백엔드 `_STAGE2_ENTRY_RS_MIN`/`_STAGE2_RS_STRONG`와는 비교하지 않음).

D1 가중치 고정 테스트: `grep -rn "_COMPOSITE_WEIGHTS" tests backend/tests` → 0건. 가중치 상수 자체를 고정하는 테스트는 **없다**. `composite_score`를 다루는 테스트 파일은 7개(`test_market_breadth.py`, `test_sector_metrics.py`, `test_ac_sag_044_regression.py`, `test_sector_benchmark_ranking.py`, `test_golden_baseline.py`, `test_market_api.py`, `test_m6_gap_closure.py`). 계획서 AC-6의 "가중치 테스트"는 신설이 필요하다.

고정 픽스처: `tests/fixtures/frozen/aggregation-2026-08-11/weekly.db` — `relative_strength` `27419`행/`93`날짜, 지수 행 `186`행. 이 픽스처는 재생성되지 않는 고정 자료이므로 본 SPEC의 산식 변경이 값을 바꾸지 않는다. 다만 지수 행을 포함한 채 남는다(plan.md §E 위험).

## R9. 회귀 계측 도구 `scripts/rs_eval/stock_rs_eval.py`

명령: `sed -n 1,101p scripts/rs_eval/stock_rs_eval.py`, `git status --short scripts/rs_eval` → `?? scripts/rs_eval/`(미추적)

- CLI: `python -I scripts/rs_eval/stock_rs_eval.py <H>`, `H`=향후 주 수(기본 4). DB 경로와 `sys.path`가 절대 경로로 하드코딩돼 있다(`:6`, `:8`).
- 유니버스: `stock_prices`에서 `KOSPI`/`KOSDAQ` 제외(`:14`), ISO 주차별 마지막 날짜만 남김(`:19-21` — 주중 고아 날짜를 자연히 배제), 20주 평균 주간거래대금 `tv20 >= 5e9`(`:99`), 날짜당 200종목 미만이면 건너뜀(`:74`), 처음 52주와 마지막 H주는 제외(`dates[52:-H]`, `:71`), 점수 ≥ 90을 상위 10%로(`:76`).
- **중요**: 이 스크립트는 `relative_strength` 테이블을 읽지 않는다. 각 후보 산식을 `stock_prices`의 원시 컬럼에서 **스크립트 안에서 다시 계산**하고, 순위도 50억 유니버스 안에서 매긴다. 따라서 "새 산식 재생성 후 이 스크립트를 다시 돌리는 것"은 프로덕션 코드를 검증하지 못한다. AC의 프로덕션 측 계측을 위해 `relative_strength.RS_12M_Rating`을 읽는 경로가 필요하다(plan.md M2).
- IBD식 정의(`:36-38`): `q1=RS_3M; q2=(1+RS_6M)/(1+RS_3M)-1; q3=(1+RS_9M)/(1+RS_6M)-1; q4=(1+RS_12M)/(1+RS_9M)-1; pr(2*q1+q2+q3+q4)` — 비율 기반, 원시 수익률에 가중합 후 순위. `2:1:1:1`은 `0.4:0.2:0.2:0.2`와 순위가 같다(양의 상수배).
- 기존 출력 `scripts/rs_eval/rs_final_h4.out`(4주, 50억 필터, 298주): `현행(1M 33%가중) 상위10_지속률 30.88`, `현행에서 1M 제거 57.46`, `IBD식(최근분기 40%) 65.28`, `12M 단독 74.78`. 계획서 §2의 31%/57%/65%/75%와 일치한다.

### R9.1 프로덕션 경로 계측이 원 수치와 비교 가능한 이유

IBD식 종합 점수는 각 종목의 원시 수익률만으로 정해지며 **분모 집합에 의존하지 않는다**. 따라서 프로덕션이 전체 분모(D5 필터 후)에서 매긴 `RS_12M_Rating`을 50억 유니버스 안에서 다시 순위 매기면, 스크립트가 50억 유니버스 안에서 IBD 점수로 매긴 순위와 (동점 처리 차이를 빼면) 같다. 반면 현행 산식은 백분위 순위의 합이라 분모에 의존하므로, 프로덕션 경로로 잰 현행 기준선은 31%에서 다소 벗어날 수 있다. 그래서 기준선은 "가정한 31%"가 아니라 **변경 전 DB에서 같은 프로덕션 경로로 잰 값**이어야 한다(acceptance.md AC-RSR-014).

## R10. IBD 픽스처 기대값 (계산 실측)

명령: scratchpad의 `ibd.py`를 `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I`로 실행(pandas `rank(pct=True)*100`, 프로덕션과 같은 순위 함수).

| 종목 | RS_1M | RS_3M | RS_6M | RS_9M | RS_12M | IBD 비율식 | IBD 차분식 | 현행식 | 12M 단독 |
|---|---|---|---|---|---|---|---|---|---|
| A | -0.10 | 1.00 | 1.00 | 1.00 | 1.000 | 100.0 | 75.0 | 100.0 | 75.0 |
| B | 0.00 | 0.00 | 0.50 | 1.25 | 2.375 | 75.0 | 100.0 | 50.0 | 100.0 |
| C | 0.50 | 0.10 | 0.10 | 0.10 | 0.100 | 25.0 | 25.0 | 25.0 | 25.0 |
| D | 0.05 | 0.20 | 0.30 | 0.40 | 0.500 | 50.0 | 50.0 | 75.0 | 50.0 |

같은 입력의 현행 `RS_6M/3M/1M_Rating`: A `100.0/50.0/25.0`, B `25.0/25.0/50.0`, C `50.0/87.5/100.0`, D `75.0/87.5/75.0`.

비율식과 다른 세 산식은 각각 최소 두 종목에서 값이 다르다. 이 표가 acceptance.md AC-RSR-005·AC-RSR-006의 고정 기대값이다.

## R13. 80 이상 몫 (B-3 근거)

plan-audit iter-1 프로브(라이브 주간 DB): `AVG(RS_12M_Rating>=80)` = 20.08%, `AVG(RS_1M_Rating>=80)` = 20.04%. 이 세션 재측정: `SELECT ROUND(100.0*AVG(RS_12M_Rating>=80),2), ROUND(100.0*AVG(RS_1M_Rating>=80),2) FROM relative_strength;` → `20.02|20.01`(전 행, 지수·고아 포함). 두 측정 모두 약 20%로, 백분위 순위의 성질이 실데이터에서 확인되었다. 감사 수치와의 소수점 차이는 대상 행 집합 차이로 보이며 결론에 영향이 없다.

## R14. 테스트 주입 지점 (plan-audit iter-1 D9)

- 등록부: `weekly.py:24` `from my_chart.registry import get_stock_registry` → 테스트는 `my_chart.db.weekly.get_stock_registry`를 바꾼다. 대안은 지연 전역 `my_chart.registry._df_stock`(`registry.py:108-119`).
- 버블 툴팁: 내보낸 formatter 함수는 없다. `StockBubbleChart.tsx:361`의 ECharts 옵션 안 익명 `formatter`이며, 기존 테스트는 `vi.mock('echarts-for-react', …)`(`__tests__/StockBubbleChart.test.tsx:15`)로 옵션을 붙잡아 `tooltip.formatter(…)`를 직접 호출한다(`:369`, `:377`).
- Stage 측정 함수: `classify_all(db_path, date)`(`stage_classifier.py:218`), `screen_stage2_entry(db_path, date)`(`:237`). `_STAGE2_RS_STRONG`은 `:105`에서 Strong/Weak 라벨에만, `_STAGE2_ENTRY_RS_MIN`은 `:291`에서 진입 선별에만 쓰인다.

## R15. 조건부 RS 통과율 — 판별력 사전 측정 (plan-audit iter-2 N1)

명령: 라이브 주간 DB를 scratchpad로 복사(`cp Output/stock_data_weekly.db <scratchpad>/weekly_copy.db` — `Output/`에 `-wal` 파일 없음 확인)한 뒤, `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I <scratchpad>/cond.py <scratchpad>/weekly_copy.db`. 스크립트는 `stage_classifier._load_stocks_for_classification()`과 `classify_stage()`를 그대로 호출하고, `screen_stage2_entry()`의 RS 외 조건(`:265-267`, `:278-288`, `:294-296`)을 같은 식으로 적용한 뒤, 통과 종목 중 `RS_12M_Rating >= t`인 비중을 날짜별로 구해 평균한다. W = `삼성전자` 최근 12개 날짜(2026-07-31 ~ 2026-10-16).

관측 출력:

```
non-RS pass counts [54, 16, 35, 12, 26, 28, 26, 24, 16, 45, 23, 16]
60 100.0 n_dates 12
70 99.48 n_dates 12
80 97.85 n_dates 12
```

해석: RS 외 다섯 조건(이평 정배열·거래량 급증·1개월 상승)을 통과한 종목은 이미 RS가 높다. 60/70/80의 폭은 2.15%p로, 상대 ±10% 허용오차(0.10 × 99.48 = 9.95%p)보다 작다. 따라서 이 사본이 M3의 변경 전 사본과 같다면 AC-RSR-015 (a)의 판별력 사전 조건은 성립하지 않고 70은 "기록만"이 된다. 참고로 plan-audit iter-2가 같은 W에서 잰 비조건부 진입 비율은 임계값 70 → 1.070%, 60 → 1.074%, 50 → 1.074%, 80 → 1.057%였다(감사 측정, 이 세션에서 재실행하지 않음).

## R11. 의존 SPEC 상태

명령: `grep -m3 -E "^(id|status|title):" .moai/specs/SPEC-SECTOR-DISPLAY-UNIFY-001/spec.md` → `status: completed`. `SPEC-SECTOR-METRIC-UNIFY-001` → `status: completed`(spec.md 머리말). 두 SPEC 모두 완료 상태이므로 `depends_on` 사전 점검은 통과한다.

## R12. SPEC ID

명령: `ID="SPEC-RS-REBALANCE-001"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` → `PASS`. `ls -d .moai/specs/SPEC-RS-REBALANCE-001` → 생성 전 부재 확인(`No such file or directory`).
