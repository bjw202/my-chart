# SPEC-RS-REBALANCE-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- **작성 시각**: 2026-10-20
- **원본**: `docs/rs-rebalance-plan-brief.md` 2판(사용자 승인) — 본 SPEC은 전사이며 재기획이 아님. Q1~Q4는 이번 plan 세션에서 사용자가 답함
- **Tier**: L (마일스톤 6개, 운영 코드 대상 파일 23개 — plan.md §D: 기존 22 + M3 신설 `scripts/rs_eval/stage2_ratio_eval.py` 1)
- **산출물**: spec.md / plan.md / acceptance.md / research.md / progress.md. `design.md`는 만들지 않음(설계 결정이 spec.md §2와 plan.md §A~§C에 고정되어 중복 문서가 됨)
- **SPEC ID 정규식 자체 검사**: 실행 완료 — `PASS`
  ```
  ID="SPEC-RS-REBALANCE-001"
  [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
  → PASS
  ```
- **ID 충돌 검사**: `ls -d .moai/specs/SPEC-RS-REBALANCE-001` → 생성 전 `No such file or directory`
- **REQ 23건 / AC 18건(+ AC-RSR-008b)** (Tier L 상한 각 25 이내)
- **조사 결정 3건 해소 (2026-10-20, 사용자 결정)**: B-1 → (a) 코드 끝자리 ≠ `0` 우선주 + 이름 `스팩` 스팩(현재 제외 대상 0개, 사전 가드), B-2 → (a) `stock_meta.rs_1m`은 Phase 4 채우기·API 노출까지(일봉 배지 연결은 후속), B-3 → (a) M3 재보정은 Stage 2 상수 70/60과 거울만, `_RS_TOP_THRESHOLD` 80 유지. 결정 본문은 spec.md §2.4, plan.md §B. 남은 미해소 표식 0건
- plan_audit_final: PASS-WITH-DEBT 0.90 (iter-3, Tier L 기준 0.85) — 부채 T1~T3는 §E.1.3
- plan_complete_at: 2026-10-20T13:05:35+09:00
- plan_status: audit-ready

## §E.1.1 audit_iteration_1 — plan-auditor FAIL 0.74 → 대응 (2026-10-20, spec.md 0.2.0)

| 결함 | 등급 | 처분 |
|---|---|---|
| D1 짝 있는 낡은 행 잔존 | BLOCKING | REQ-RSR-001을 "이번 실행이 쓰지 않은 행 삭제"(선행 + 날짜별 집합 차, 같은 트랜잭션)로 재작성, 전체 삭제는 기각 기록, AC-RSR-017 신설, §1.3 정정, research.md R2.1 |
| D2 M3 종료 조건 측정 불가 | BLOCKING | REQ-RSR-018·AC-RSR-015를 진입 비율(70)·강세 비중(60) 두 기준으로 분리, W = 최근 12개 공통 기준 날짜, 명령 `scripts/rs_eval/stage2_ratio_eval.py`, 사본 `Output/snapshots/weekly_{before,after}_rsr.db` 고정 |
| D3 계측 명령 미고정 | SHOULD-FIX | `--production --db <경로>` 명령 고정, 유니버스 규칙 줄 번호 인용(`:19-21`, `:71`, `:74`, `:76`, `:99`), 원시 컬럼 grep 0 기계 검사 |
| D4 결측 행 규칙 | SHOULD-FIX | REQ-RSR-023·AC-RSR-018 신설, 현행 `dropna` 유지와 45행 내역(R3.1) |
| D5 테스트 목록 누락 | SHOULD-FIX | plan.md §G에 49개 전체 목록·세는 명령·파일별 판정, 근거 없던 문장 삭제 |
| D6 컬럼 위치 | SHOULD-FIX | REQ-RSR-011에 DDL 마지막 컬럼·28번째 값 명시, AC-RSR-008b 신설 |
| D7 AC-004 문구 | MINOR | 실패 불가 조항 삭제, `q3` 분모 설명 정정 |
| D8 AC-010 방향 | SHOULD-FIX | 결측 제외 30.0 / 0 채움 25.0 고정 |
| D9 주입 지점 | SHOULD-FIX | `my_chart.db.weekly.get_stock_registry`, 툴팁 `StockBubbleChart.tsx:361` + `echarts-for-react` 목 선례 |
| D10 마일스톤 정렬 | MINOR | plan.md §F 종료 조건과 AC 매트릭스 일치, 머리말 범위 001~023 |
| D11 REQ-011 패턴 | MINOR | `While … when`으로 변경 |
| D12 등록부 수치 | MINOR | 등록부 프로브 2,559행으로 인용 |
| D13 소유권·T8 | SHOULD-FIX | spec.md §2.4 D13 결정 행, AC-RSR-013 소유권 정리 |
| D14 파일 수 재현 | MINOR | plan.md §D에 세는 명령과 관측 출력 인라인 |

## §E.1.2 audit_iteration_2 — plan-auditor FAIL 0.83 → 대응 (2026-10-20, spec.md 0.3.0)

iter-1 결함 D1~D14는 감사가 모두 해소로 확인했다.

| 결함 | 등급 | 처분 |
|---|---|---|
| N1 70 기준 무의미(진입 비율이 임계값에 거의 무반응) | BLOCKING | 사용자 결정: 조건부 RS 통과율로 교체, 상대 ±10%, 판별력 사전 조건(60/70/80 엄격 단조 + 폭 > 0.10 × c70), 미충족 시 70은 "기록만". plan 단계 실측 100.00/99.48/97.85(R15) — 미충족 예고 |
| N2 AC-RSR-001 대조 수치 도달 불가 | BLOCKING | REQ-RSR-001에서 짝 없는 행 조항 삭제(포함 관계 산문 명시), AC-RSR-001 대조를 "(i)·(ii) 제거 → 6, (i)만 제거 → 5"로, AC-RSR-017과 구분 명시(병합 불필요), plan §E 1행 갱신 |
| N3 측정 분모가 사본 의존 | SHOULD-FIX | (a) 분모 = RS 외 다섯 조건 통과 집합, (b) 분모 = Stage 2 종목 — 모두 가격 테이블로 결정됨을 REQ-RSR-018·AC-RSR-015에 명시 |
| N4 REQ-RSR-023 shall 절 | MINOR | "`stock_prices` 행의 어느 컬럼이든 NULL"을 shall 절에 넣음 |
| N5 픽스처 전 컬럼 | MINOR | acceptance.md 머리말에 전 컬럼 채움 규칙과 공용 빌더 `tests/rsr_fixtures.py`(`price_row`, `make_weekly_db`) 명시, plan M1에 신설 |
| AC-RSR-008b 문구 | MINOR | 중간 삽입 시 `sma5` ← `sma200_20d_ago` 값, `rs_1m` ← `5.555`로 정정 |

## §E.1.3 audit_iteration_3 — plan-auditor PASS-WITH-DEBT 0.90 (2026-10-20, spec.md 0.3.0)

iter-2 결함 N1~N5는 감사가 모두 해소로 확인했다(파일 대조 + 프로브 재실행). 차단 결함 0건. 차원 점수: 명확성 0.90 / 완전성 0.90 / 검증가능성 0.85 / 추적성 0.95.

| 부채 | 등급 | 내용 | run 단계 처리 |
|---|---|---|---|
| T1 | SHOULD-FIX | REQ-RSR-018 (a) 판별력 사전 조건을 변경 전 사본에서만 측정. 감사의 변경 후 사본 모의: c60/c70/c80 = 99.58/94.42/84.87(폭 14.71 > 기준 9.44 → 통과로 뒤집힘). 결론(70 유지)은 동일 | 사전 조건을 두 사본 모두에서 평가하고 하나라도 판별되면 (a) 적용. "기록만" 모드에서도 c70 after가 before 대비 상대 ±10% 안인지 단언, 벗어나면 사용자 에스컬레이션 |
| T2 | MINOR | (a) 분모가 날짜별 12~54개로 작아 상대 ±10%가 종목 1~5개 수준 | 날짜별 비RS 조건 통과 개수를 평균 옆에 기록 |
| T3 | MINOR | (b) 거래량 0 종목의 낡은 등급이 before 사본에만 있어 Strong 비율이 33.53→33.72로 미세 이동 | 알려진 소폭 효과로 기록 |
| — | 참고 | `design.md` 미작성(Tier L), 사유 plan.md §D | 유지 |

## §E.1.4 Run-phase Plan Audit Gate (2026-10-20, review-4)

- audit_verdict: PASS-WITH-DEBT 0.88 (Tier L 기준 0.85) — 명확성 0.90 / 완전성 0.85 / 검증가능성 0.85 / 추적성 0.95
- audit_report: .moai/reports/plan-audit/SPEC-RS-REBALANCE-001-review-4.md
- audit_at: 2026-10-20T07:20:10Z
- auditor_version: plan-auditor (Claude-only, 교차 모델 미사용)
- audit_cache_hit: false (이 SPEC의 이전 보고서 파일 부재)
- f747ce5 이후 표류: 없음 — 인용 경로 전체 `git diff --quiet f747ce5 HEAD` 종료 0, DB 수치 재측정 일치
- 신규 결함: SHOULD-FIX 3(D1 `aggregate_types.py` 누락, D2 AC-RSR-013 grep 기준 3줄, D3 T1 부채가 REQ/AC에 미반영) / MINOR 5(D4~D8)
- 오케스트레이터 확인: D1(`envelope.py:209-210`이 `SectorAggregate`에서 읽음), D2(`StockTable.tsx:32` 주석이 grep에 걸림) 직접 관측. 추가 관측: `StockTable.tsx:263` 라벨 `"RS Strong (≥ 70)"` 리터럴

- 결함 처리(사용자 결정: 착수 전 수정): manager-spec이 D1~D8 수정(spec.md 0.3.1, 추가로 REQ-RSR-006 `weekly.py:450-456` 정정) → 차등 재감사 review-5 **PASS 0.92** (명확성 0.92 / 완전성 0.92 / 검증가능성 0.90 / 추적성 0.95, D1~D8 전부 해소, 2026-10-20T07:47:20Z)
- review-5 신규 MINOR 2건은 오케스트레이터가 직접 수정: N1 plan.md M3·§D 18행에 `:32` 주석·`:263` 라벨 추가, N2 AC-RSR-013 라벨 패턴을 `RS Strong[^"]*[0-9]`로 넓힘 — 현재 코드 4줄, 준수 형태 0줄, 위반 형태 4/4 검출(scratchpad 재측정)
- 이 SPEC의 run 진입 기준 판정: PASS 0.92 (report .moai/reports/plan-audit/SPEC-RS-REBALANCE-001-review-5.md)

## Phase 1 SKIP Rationale

건너뛰지 않음(not skipped). 이 SPEC은 기존 코드(`weekly.py`, `meta_service.py`, 섹터 집계, 프론트 세 화면)를 고치므로 코드베이스 조사가 필수였다. 실제로 조사에서 계획서 주장 세 건이 관측과 달랐다(고아 행 합계, 우선주 패턴 오탐, `stock_meta` 비재생성 — 아래 표). 조사를 건너뛰었다면 세 건 모두 run 단계에서 결함으로 드러났을 것이다.

## 계측으로 확정한 사실

DB 질의는 모두 `sqlite3 "file:$PWD/Output/<db>?immutable=1"`(읽기 전용)로 실행했다. 상세 출력은 `research.md`의 해당 절에 있다.

| 주장 | 관측 방법 | 결과 |
|---|---|---|
| 현행 `RS_12M_Rating` 산식은 1M 가중 1.0의 순위합 (orchestrator pre-probe) | `sed -n 395,470p my_chart/db/weekly.py` | 확인 — `weekly.py:441-448`; `RS_6/3/1`은 `:450-455` |
| 저장은 `INSERT OR REPLACE` (pre-probe) | 같은 파일 `:180-195` | 확인 — `weekly.py:188` |
| 지수 행이 `stock_prices`에 일반 행으로 들어감 (pre-probe) | `sed -n 325,350p my_chart/db/weekly.py` | 확인 — `:335-343` |
| 고아 행 "42개 날짜 10만 4천 행 + 옛 이름 21개" (계획서) | `LEFT JOIN stock_prices USING(Name, Date) WHERE sp.Name IS NULL` + 원인별 분해 | **정정** — 합계 `119881`행: 42개 날짜 `104411` + 21개 이름 `5507` + 쌍 불일치 `9963`(4개 날짜) |
| `relative_strength`의 지수 행 | `… WHERE Name IN ('KOSPI','KOSDAQ') GROUP BY Name` | `KOSDAQ 346`, `KOSPI 346` |
| 기준 종목 날짜 수 355 | `… WHERE Name='삼성전자'` | `355` (2020-01-03~2026-10-16). `stock_prices` 전체 날짜는 `368`, 그중 100행 미만 날짜 `13` |
| 우선주·스팩을 이름 패턴으로 판별 (계획서) | `LIKE '%우'`, `'%우B'`, `'%우C'`, `'%스팩%'`, `'%SPAC%'` 최신 주차·전 기간 | **정정** — 실제 우선주·스팩 0개, `%우`는 보통주 3개(`성우 에코글로우 이오플로우`)만 일치 |
| 코드 끝자리로 우선주 식별 가능성 | `SELECT substr(code,6,1), COUNT(*) FROM stock_meta GROUP BY 1` (일봉 DB) | `0|2533` — 끝자리 0 아닌 코드 없음 |
| 거래량 0 행 존재 | `… WHERE Date='2026-10-16' AND (Volume=0 OR Volume IS NULL)` | `101`행 (전 기간 `Volume=0` `19496`행) |
| 원시 수익률은 소수 비율이고 `1+R > 0` | 최신 주차 값 조회, 지수 제외 전 기간 `MIN`, `RS_kM <= -1` 개수 | 소수 비율 확인, 최솟값 `-0.99887…`, `<= -1` 행 `0` |
| `stock_meta`는 재구축 테이블이라 DDL만 바꾸면 됨 (계획서) | `sed -n 20,130p backend/services/meta_service.py`, `grep -n "DELETE FROM stock_meta\|DROP"`, 라이브 `PRAGMA table_info(stock_meta)` | **정정** — `CREATE IF NOT EXISTS` + `DELETE`(`:341`), `DROP` 없음, 위치 기반 27열 삽입, 라이브 컬럼명이 DDL과 다름(`ma50_w ma150_w ma200_w`). 멱등 ALTER 선례 `_MINERVINI_META_COLS`(`:59`, `:112-124`) |
| 주간 소비처 목록 (계획서 §4.1) | `grep -rn "RS_12M_Rating" my_chart backend frontend/src …` (테스트 제외) | **보강** — `my_chart/analysis/sector_advanced.py:240-249` `_get_rs_on_date()` 누락. 나머지 일치 |
| 일봉 소비처 목록 (계획서 §4.1) | `grep -rln "rs_12m" …` | 일치 — `screen_service.py:61`(리터럴 70), `sector_detail_service.py`, `sector_advanced_service.py`, `stage_service.py` |
| 상수 없이 반복된 임계값 리터럴 | `grep -rn -E "rs[_a-zA-Z0-9]*\s*(>=|>|<=|<)\s*[0-9]+…"` | `backend/services/screen_service.py:61`, `frontend/src/components/StockExplorer/StockTable.tsx:39` |
| DB 갱신 파이프라인 4단계 순서 | `grep -n … backend/services/db_service.py`, `grep -rn "db/update" frontend/src` | 일치 — `_run_update()` `:64`, Phase 1~4 `:67/:76/:84/:92`, 프론트 `api/db.ts:5` |
| 종목 테이블·버블의 RS 공급원 | `sed -n 180,195p stage_classifier.py`, `sed -n 238,250p sector_advanced.py` | 둘 다 주간 `relative_strength` — `stock_meta`를 읽지 않음 |
| 섹터 테이블 렌더 지점 | `grep -rn "rs_avg\|rs_top_pct" frontend/src/components/SectorAnalysis/*.tsx` | `SectorRankingTable.tsx:50,52,158,232-244`; 랭킹 항목 생성 `backend/services/sector_ranking_service.py:69-83` |
| 영향 테스트 개수 | `grep -cE '^\s*(async )?def test_'` / `^\s*(it|test)\(` | `test_weekly_insert.py 10`, `test_stage_classifier.py 14`, `test_stage_service.py 3`, `test_meta_service.py 15`, `test_db_service.py 18`, `test_sector_metrics.py 12`, `test_sector_aggregation.py 21`, `test_ac_sag_030_rs_avg.py 4`, `test_screen_service.py 32`, `rsMetrics.test.ts 2` |
| 교차 언어 등식 테스트 존재 | `grep -nE "readFileSync|THRESHOLD" frontend/src/utils/__tests__/rsMetrics.test.ts` | 있음 — `_RS_TOP_THRESHOLD`만 수치 비교, 70/60은 리터럴 단언(`:50-54`) |
| D1 가중치 고정 테스트 존재 | `grep -rn "_COMPOSITE_WEIGHTS" tests backend/tests` | 없음(0건) — 신설 필요 |
| 계측 스크립트는 프로덕션 테이블을 읽음 | `sed -n 1,101p scripts/rs_eval/stock_rs_eval.py` | **아님** — 원시 컬럼에서 산식을 스크립트 안에서 재계산. 미추적(`?? scripts/rs_eval/`) |
| 잔존율 31/57/65/75% | `head -40 scripts/rs_eval/rs_final_h4.out` | `30.88 / 57.46 / 65.28 / 74.78` (298주) |
| IBD 픽스처 기대값 | scratchpad `ibd.py`, `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I` | A 100 / B 75 / C 25 / D 50 (research.md R10) |
| 고정 픽스처의 지수 행 | `… tests/fixtures/frozen/aggregation-2026-08-11/weekly.db` 질의 | `27419`행/`93`날짜, 지수 행 `186` |
| 의존 SPEC 상태 | `grep -m3 -E "^(id|status|title):" …/spec.md` | 두 SPEC 모두 `status: completed` |
| 운영 코드 대상 파일 수 | plan.md §D의 존재 확인 루프 | `new: scripts/rs_eval/stage2_ratio_eval.py`, `existing=22` → 23 |
| 짝 있는 낡은 행 (D1) | `relative_strength rs JOIN stock_prices sp USING(Name, Date)` 조건별 | 지수 `KOSPI 300`·`KOSDAQ 300`, 거래량 0 `16369`(최신 주차 `101`), 비기준 날짜 `5|4` |
| 등록부 우선주·스팩 (D12) | venv python `get_stock_registry()` 집계 | `2559 {'0': 2559} 0 0` |
| 최신 주차 등급 누락 내역 (D4) | `RS_*` NULL 집계 + 누락 이름의 NULL 컬럼 조회 | 가격 `2535` → RS `2490`: `RS_*` 결측 `44` + `명인제약`(`SMA40_Trend_4M` NULL) `1` |
| 조건부 RS 통과율 60/70/80 (N1) | 라이브 DB 사본 + `stage_classifier` 함수 호출 스크립트(research.md R15) | `100.0` / `99.48` / `97.85`, W = 2026-07-31~2026-10-16, RS 외 통과 종목 수 12~54 |
| 80 이상 몫 (B-3) | `AVG(RS_12M_Rating>=80)`, `AVG(RS_1M_Rating>=80)` | iter-1 프로브 `20.08`/`20.04`, 재측정 `20.02`/`20.01` |
| 변경 기호 참조 테스트 (D5) | plan.md §G의 grep | `49`(Python 25, 프론트 24), 축약 DDL 13개 |

## §F Phase 4 Mode Selection

Input parameters:

| 파라미터 | 값 |
| --- | --- |
| tier | L |
| scope (files) | 23 운영 코드(Python 13, 프론트 7, 스크립트 2, 문서 1) + 테스트(변경 후보 16개 — plan.md §G 판정 열이 '변경 없음'이 아닌 행) |
| milestone count | 6 (M1→M2 순서 강제, M3는 M2 결과에 의존) |
| domain count | 3 (주간 DB 생성, 백엔드 API, 프론트 표시) |
| file language mix | Python + TypeScript/TSX + HTML 문서 |
| concurrency benefit | LOW — 코딩 중심이며 M1→M2→M3 순서가 데이터 의존(재생성 전 기준선 측정, 재생성 후 재보정) |
| 라이브 DB 쓰기 | M2(재생성), M4(메타 재구축) — 동시 쓰기 금지 |

| 모드 | 평가 |
| --- | --- |
| serial | 채택 — 마일스톤 단위로 `manager-develop`(tdd) 단독 스폰, 순차 |
| fanout | 기각 — 연구는 plan 단계에서 끝남, 남은 일은 코딩 중심 |
| agent-team | 기각 — 명시 요청 없음(실험 기능), 라이브 DB 쓰기 경합 위험 |
| sweep | 기각 — 균일 기계 변환 아님, 파일 간 의존·데이터 순서 의존 |

Decision: serial (files: 24, domains: 3, milestones: 6)

Justification: M1→M2→M3이 데이터 순서로 묶이고(재생성 전 기준선, 재생성 후 재보정), M2·M4가 라이브 `Output/` DB에 쓰므로 쓰기 가능한 에이전트를 동시에 둘 수 없다. 코딩 중심 작업이라 병렬 이득도 낮다.

## §F.1 Implementation Kickoff Approval (2026-10-20, 사용자 결정)

- 착수: 승인 — 단, 감사 review-4의 SHOULD-FIX 3건(D1~D3)과 MINOR 5건(D4~D8)을 manager-spec이 먼저 고친 뒤 M1 시작
- 진행 방식: 반자율 — 마일스톤마다 오케스트레이터가 증거를 읽고 사용자 확인 후 다음 마일스톤
- 라이브 DB(M2 재생성, M4 메타 재구축): `.bak_<날짜>` 백업 + 변경 전 기준선 측정 후, 덮어쓰기 직전에 사용자 확인
- `/moai goal` 미설정(반자율 선택)

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
