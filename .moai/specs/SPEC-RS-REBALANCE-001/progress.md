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

### M1 — 분모 정리와 낡은 행 제거 (manager-develop, cycle_type=tdd, 2026-10-20)

**작업 위치.** 오케스트레이터 지시는 공용 체크아웃 `main`이었으나 이 실행은 런타임이 만든 L1 워크트리(`.claude/worktrees/agent-a6c66422cb17cb479`, 브랜치 `worktree-agent-a6c66422cb17cb479`) 안에 격리되어 있었다. 워크트리 기준점이 낡아(`fd5f11f`, SPEC 디렉터리 없음) `git merge --ff-only main`으로 `0b1dfc3`까지 빨리 감기한 뒤 작업했다. 커밋은 이 워크트리 브랜치에 있으며 `main`에는 아직 없다.

**커밋.**

| 순서 | SHA | 내용 | `git show --stat` |
|---|---|---|---|
| 1 | `f3b7066` | 특성화 골든값 + 공용 픽스처 빌더(운영 코드 변경 없음, 단독 커밋) | `tests/rsr_fixtures.py` +111, `tests/test_rsr_characterization.py` +72 |
| 2 | `cec038b` | 운영 변경 + AC 테스트 + `spec.md` status `draft → in-progress` | `spec.md` 2 ±1, `my_chart/db/weekly.py` +83 −1, `tests/test_rsr_m1_denominator.py` +279 |

**특성화가 변경 전 코드에서 통과했다는 근거.** 커밋 1 직전 `git diff --stat HEAD -- my_chart` → 출력 없음(운영 코드 무변경). 같은 트리에서 `pytest tests/test_rsr_characterization.py -q` → `2 passed in 2.13s`. 골든 테스트의 판별력: `RS_6`에서 `rank_1m`을 임시로 뺐을 때 `AssertionError: B / assert np.float64(50.0) == 25.0` → `1 failed, 1 passed`, 이후 `git checkout -- my_chart/db/weekly.py`로 복구, `git status --short`에 `weekly.py` 없음.

**RED (구현 전, `0b1dfc3`+커밋 1 트리).** `pytest tests/test_rsr_m1_denominator.py -q` → `9 failed, 2 passed in 0.39s`(증거: `.moai/state/verify/rsr-m1/red.log`). 실패 요지(원문):

```
E       AssertionError: assert 6 == 0                      # AC-001
E       AssertionError: assert 2 == 0                      # 필터 후 0행 날짜
E       AssertionError: assert not ({'KOSDAQ', 'KOSPI', 'Z'} & {'KOSDAQ', 'KOSPI', 'L', 'S1', 'S2', 'S3', ...})   # AC-002
E         Extra items in the left set: '가나다스팩1호' '가나다우'   # AC-003
E         Left contains 1 more item: {'V': 100.0}           # AC-004
E       assert 3 == 0                                       # AC-017
E       AttributeError: ... has no attribute '_delete_unprocessed_dates'   # 대조 테스트 3건
```

RED 단계에서 통과한 2건은 현행 동작을 고정하는 테스트다: AC-018(현행 `dropna`가 이미 결측 행을 뺀다, REQ-RSR-023 "현행 유지")과 "등록부에 없는 이름은 우선주가 아니다"(현행 코드는 등록부를 보지 않는다). 둘 다 아래 대조(C8·C9, 그리고 C4가 보여 주는 이름 패턴 오탐)로 판별력을 따로 확인했다. 기준 종목 부재 가드는 구현 후 추가한 분기라, 가드를 임시로 `if False:`로 바꿔 `AssertionError: assert 0 == 2`(테이블 전체 삭제) RED를 본 뒤 복구해 GREEN(`1 passed`)을 확인했다.

**GREEN (`cec038b`).** `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/test_rsr_characterization.py tests/test_rsr_m1_denominator.py -v -p no:warnings` → `14 passed in 0.36s`(증거: `.moai/state/verify/rsr-m1/final_m1.log`).

| AC | 상태 | 테스트 | 출력 |
|---|---|---|---|
| AC-RSR-001 | PASS | `test_ac_rsr_001_unpaired_rows_removed` (+ 필터 후 0행 날짜 전체 삭제 `test_ac_rsr_001_date_with_no_rows_after_filter_is_cleared`) | `PASSED` ×2 |
| AC-RSR-002 | PASS | `test_ac_rsr_002_index_and_zero_volume_excluded_before_ranking` | `PASSED` |
| AC-RSR-003 | PASS | `test_ac_rsr_003_preferred_and_spac_excluded_common_kept`, `test_ac_rsr_003_name_absent_from_registry_is_not_preferred` | `PASSED` ×2 |
| AC-RSR-004 | PASS | `test_ac_rsr_004_non_positive_one_plus_return_row_excluded` | `PASSED` |
| AC-RSR-017 | PASS | `test_ac_rsr_017_paired_stale_rows_removed` | `PASSED` |
| AC-RSR-018 | PASS | `test_ac_rsr_018_rows_with_any_null_column_get_no_rating` | `PASSED` |
| AC-RSR-006 기준(골든) | PASS (M1 후에도 불변) | `test_characterize_generate_rs_db_r10_6m_3m_1m_golden`, `test_characterize_relative_strength_schema_unchanged` | `PASSED` ×2 |

라이브 단계(AC-RSR-001·002·017의 `Output/` 질의)는 M2 재생성 후 몫이며 이번에 실행하지 않았다.

**대조 RED (lessons #9).** 실행기 `.moai/state/verify/rsr-m1/contrasts.py`가 `cec038b` 트리의 `weekly.py`에 회귀를 하나씩 문자열 치환으로 넣고 대상 테스트를 돌린 뒤 원본 바이트로 복구했다. 12건 모두 `exit=1`. 원문 로그: `.moai/state/verify/rsr-m1/contrasts.log`.

| # | 넣은 회귀 | 대상 AC | 관측(원문 발췌) |
|---|---|---|---|
| C1 | 지수·거래량 0 필터 제거 | 002 (a) | `assert not ({'KOSDAQ', 'KOSPI', 'Z'} & {'KOSDAQ', 'KOSPI', 'L', ...})` |
| C2 | 전체로 순위 → 행만 사후 마스킹 | 002 (c) | `{'S2': 37.5} != {'S2': 60.0}`, `{'S4': 87.5} != {'S4': 100.0}` — (a)는 통과, (c)에서 RED |
| C3 | 분모에 거래대금 필터(`Close*Volume >= 1e6`) | 002 (b) | `assert 'L' in {'S1': 25.0, 'S2': 50.0, 'S3': 75.0, 'S4': 100.0}` |
| C4 | 우선주 판별을 이름 패턴 `우$`로 | 003 | `assert set() == {'성우', '에코글로우', '이오플로우'}` |
| C5 | 코드 끝자리 판별 제거 | 003 | `Extra items in the left set: '가나다우'` |
| C6 | `스팩` 판별 제거 | 003 | `Extra items in the left set: '가나다스팩1호'` |
| C7 | `1+R <= 0` 가드 제거 | 004 | `{'S1': 20.0} != {'S1': 25.0}` (V가 분모에 들어옴) |
| C8 | `dropna`를 `RS_*` 다섯 컬럼으로 좁힘 | 018 | `{'S1': 20.0} != {'S1': 25.0}` (W가 분모에 들어옴) |
| C9 | 결측을 0으로 채움 | 018 | `{'S2': 33.33333333333333} != {'S2': 50.0}` (Y·W가 분모에 들어옴) |
| C10 | (i)·(ii) 모두 제거 | 001 | `AssertionError: assert 6 == 0` |
| C11 | (i)만 제거 | 001 | `AssertionError: assert 5 == 0` |
| C12 | (i)·(ii)를 짝 기준 삭제로 바꿔치기 | 017 | `assert 3 == 0` |

복구 증명: 실행 직후 `git status --short` → `?? .moai/logs/`(작업 전부터 있던 미추적 디렉터리)뿐, `git diff --stat HEAD` → 출력 없음. C10~C12와 같은 회귀는 monkeypatch 대조 테스트(`..._contrast_both_steps_disabled_leaves_6`, `..._contrast_step_i_disabled_leaves_5`, `..._contrast_pair_based_delete_leaves_3`)로도 상시 고정했다. 단언의 우변(6·5·3, 순위 상수 20/40/60/80/100·25/50/75/100)은 픽스처에 심은 행 수와 손으로 정한 값이며 프로덕션 함수에서 끌어오지 않았다.

**구현 위치(프로브: `grep -n "def _registry_preferred_names\|def _filter_rs_universe\|if total_dates == 0\|_delete_unprocessed_dates(conn)$\|_delete_stale_rows_for_date(conn, str" my_chart/db/weekly.py`).** 출력: `398:def _registry_preferred_names`, `409:def _filter_rs_universe`, `496:    if total_dates == 0:`, `503:    _delete_unprocessed_dates(conn)`, `512:        _delete_stale_rows_for_date(conn, str(date), set(df["Name"].astype(str)))`. (ii)의 삭제와 삽입은 기존 커밋 주기(20개 날짜마다 + 마지막) 안에서 커밋 전에 일어나므로 같은 트랜잭션이다. `RS_12M_Rating` 산식은 바꾸지 않았다(M2 몫).

**영향 범위 회귀.** `pytest tests/test_weekly_insert.py tests/test_db_service.py tests/test_universe.py tests/test_weekly_supersede.py tests/test_weekly_grid.py tests/test_consumer_dates.py tests/test_stage_classifier.py tests/test_sector_metrics.py tests/test_market_breadth.py -q` → `142 passed in 0.98s`(`cec038b`, 증거: `.moai/state/verify/rsr-m1/final_lane.log`). 전체 스위트는 두 커밋 모두 pre-commit 게이트(`moai gate`)가 돌려 통과했다.

**린트.** `uvx ruff check my_chart/db/weekly.py tests/rsr_fixtures.py tests/test_rsr_characterization.py tests/test_rsr_m1_denominator.py` → `F402 Import date from line 18 shadowed by loop variable` 1건. 같은 명령을 `git show HEAD:my_chart/db/weekly.py`(`0b1dfc3`)에 돌려도 같은 1건 → 기존 기준선이며 새 경고 0.

**커버리지.** `.venv/bin/python -m coverage run --include='my_chart/db/weekly.py' -m pytest tests/test_rsr_characterization.py tests/test_rsr_m1_denominator.py` (`cec038b`, 14 tests) → `my_chart/db/weekly.py 229 119 48%`, 미커버 `89-92, 122-131, 140-149, 155, 179, 204-208, 239-300, 326-387, 548, 551-552`. M1이 새로 쓴 기준 종목 부재 분기(`496-500`)와 함수(`_registry_preferred_names`, `_filter_rs_universe`, `_delete_unprocessed_dates`, `_delete_stale_rows_for_date`)는 미커버 목록에 없다. 나머지 미커버 줄은 M1 범위 밖인 가격 DB 수집 경로와 기존 진행 콜백(`548`)·20개 단위 커밋(`551-552`)이다.

**환경 조치(코드 아님).** 첫 커밋 시도에서 게이트가 21건 실패했다 — 워크트리에 gitignore된 운영 DB가 없어서다(프로젝트 메모리 `project_worktree_precommit_db_trap`). 공용 체크아웃의 `Output/stock_data_weekly.db`·`stock_data_daily.db`를 이 워크트리 `Output/`에 **복사**했고(원본은 읽기만), 워크트리 `.venv`에 `setuptools<81`을 설치했다(`setuptools==82.0.1 → 80.10.2`, `pkg_resources` 복구). 이후 게이트가 한 번 4분 상한을 넘겼다(`quality gate timed out: pytest exceeded 4m0s`, 실측 4:04.8, 부하 평균 5.3). 부하가 3.8로 내려간 뒤 재시도에서 통과했다. 우회 플래그는 쓰지 않았다.

**미검증 (Gaps).**
- 라이브 DB 단계(AC-RSR-001·002·017의 `Output/stock_data_weekly.db` 질의 → 0): M2 재생성 후 수행 예정. 이번에는 실행하지 않았다.
- `backend/tests` 스위트는 돌리지 않았다(M1이 건드리는 경로 아님). 지시에 적힌 기존 수집 오류(`cannot import name 'generate_price_db'`)는 관측하지 않았다.
- 실제 등록부(`sectormap-original.xlsx`)로 `_registry_preferred_names()`를 돌린 결과는 측정하지 않았다. research.md R3의 기록(코드 끝자리 전부 `0`)에 따르면 제외 대상은 0개일 것이다.

**잔여 위험.**
- 기준 종목 부재 가드는 REQ-RSR-001 문구에 없는 안전장치다: 기준 종목 행이 0개면 (i)이 테이블 전체를 지우게 되므로 아무것도 바꾸지 않고 경고만 남긴다. SPEC 본문과 다르다고 판단되면 manager-spec 확인이 필요하다.
- 스팩 판별은 등록부가 아니라 그 날짜 가격 행의 종목명에 적용한다(등록부 종목명과 같은 이름이므로 등록부 기준의 상위 집합). 등록부에 없는 이름도 `스팩`이 들어 있으면 제외된다.
- 커밋은 워크트리 브랜치에만 있다. `main` 반영(빨리 감기)은 오케스트레이터 몫이다.

### M2 (pre-regeneration) — IBD식과 계측 도구, 기준선 (manager-develop, cycle_type=tdd, 2026-10-20)

**범위.** 이번 실행은 라이브 DB 재생성 **직전까지**다. `Output/stock_data_weekly.db`(공용 체크아웃)에는 쓰지 않았고 `weekly_after_rsr.db`도 만들지 않았다. 따라서 AC-RSR-014의 목표(≥ 60)와 AC-RSR-001·002·017의 라이브 단계 질의는 아직 열려 있다.

**작업 위치.** 런타임 L1 워크트리 `.claude/worktrees/agent-a902f867f6e063330`(브랜치 `worktree-agent-a902f867f6e063330`). 기준점이 `fd5f11f`라 `git merge --ff-only main`으로 `f07b520`까지 빨리 감기한 뒤 작업했다. 커밋은 이 워크트리 브랜치에만 있다.

**커밋.**

| SHA | 내용 | `git show --stat` |
|---|---|---|
| `366206a` | 운영 변경(IBD식) + 계측 도구 `--production`·`--db` + AC 테스트 | `my_chart/db/weekly.py` 28 (+19 −9), `scripts/rs_eval/stock_rs_eval.py` 29 (+25 −4), `tests/test_rsr_m2_eval_production.py` +107, `tests/test_rsr_m2_ibd.py` +52 |

**기준선 (AC-RSR-014 첫 명령, 재생성 전).** 사본 확인: `shasum -a 256 …/Output/snapshots/weekly_before_rsr.db | cut -c1-16` → `949f29639a86da86`(오케스트레이터 기록과 같음). 명령(워크트리 cwd, `366206a`의 스크립트와 같은 내용):

```
/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db /Users/byunjungwon/Dev/my-project-01/my_chart/Output/snapshots/weekly_before_rsr.db
exit=0
registry 중복 Code 감지 — 첫 행 유지, 이 행 drop: Code=052770 종목명=아이톡시

=== 필터: 20주 평균 주간거래대금 >= 50억 | 향후 4주 ===
                      주수  상위10_초과pp  상하위스프레드pp  상위10_vs평균pp  지연진입_vs평균pp  IC양수비율  상위10_지속률
공식
프로덕션(RS_12M_Rating)  295       1.62      -0.47        -0.55        -0.58   32.88     29.24
```

증거: `.moai/state/verify/rsr-m2/baseline.log`(워크트리). **기준선 `상위10_지속률` = 29.24** — 계획서 31%와 ±3%p(28~34) 안이다. 측정 뒤 `ls -la …/Output/snapshots/`에는 `weekly_before_rsr.db` 한 파일뿐이었다(`--db`는 `mode=ro&immutable=1`로 열어 `-wal`/`-shm`을 만들지 않음).

- 같은 사본에서 원시 산식 모드(`… stock_rs_eval.py 4 --db <같은 경로>`, 증거 `baseline_rawmode.log`)는 `현행(1M 33%가중) 30.88`, `IBD식(최근분기 40%) 65.28`, `12M 단독 74.78`, `주수 298` — `scripts/rs_eval/rs_final_h4.out`과 같은 값이다. 스크립트 수정이 기존 모드를 바꾸지 않았다는 회귀 근거이기도 하다.
- **주수 295 대 298의 원인(프로브).** 프로덕션 모드는 `RS_12M_Rating`이 없는 행을 더 뺀다. 루프 날짜(`dates[52:-4]`, 299개) 중 `relative_strength`에 날짜 자체가 없는 것이 정확히 3개다: `2020-12-30`, `2021-01-08`, `2021-01-15`(immutable 읽기 파이썬 프로브 출력 `loop 299 loop_missing_in_rs ['2020-12-30', '2021-01-08', '2021-01-15']`). 298 − 3 = 295. 지속률 차이(29.24 대 30.88)는 이 3주와 research.md R9.1의 분모 의존(프로덕션 등급은 전체 분모에서 매긴 순위합)으로 설명되는 범위로 본다 — 가설이며 분리 측정은 하지 않았다.

**RED (구현 전).**
- 계측 도구(`f07b520` 트리, 테스트만 추가): `pytest tests/test_rsr_m2_eval_production.py -q` → `2 failed in 1.09s`. 원문: `ValueError: invalid literal for int() with base 10: '--production'`(증거 `red_eval.log`). 테스트가 인자를 `--production --db <tmp> 4` 순서로 넘기므로, 옛 스크립트는 DB를 열기 전에 실패한다 — 라이브 DB를 건드리지 않는 RED다.
- IBD식: `pytest tests/test_rsr_m2_ibd.py -q` → `1 failed, 1 passed in 0.29s`. 원문: `Differing items: {'B': 50.0} != {'B': 75.0}`, `{'D': 75.0} != {'D': 50.0}`(증거 `red_ibd.log`) — acceptance.md의 "현행 가중치로 되돌리면 B 50, D 75"와 같은 값. 통과한 1건은 AC-RSR-016 상수 고정 테스트로, 현행 값을 고정하는 테스트라 RED 단계에서 통과하는 것이 정상이다. 판별력은 대조 K8로 따로 확인했다.

**GREEN (`366206a`).** `pytest tests/test_rsr_m2_ibd.py tests/test_rsr_m2_eval_production.py tests/test_rsr_characterization.py tests/test_rsr_m1_denominator.py -v` → `18 passed in 2.23s`(증거 `green.log`).

| AC | 상태 | 테스트 / 명령 | 출력 |
|---|---|---|---|
| AC-RSR-005 | PASS | `test_ac_rsr_005_rs_12m_rating_is_ratio_based_ibd_percentile` — 기대값 A 100 / B 75 / C 25 / D 50은 research.md R10 리터럴 | `PASSED` |
| AC-RSR-006 | PASS | `test_characterize_generate_rs_db_r10_6m_3m_1m_golden`, `test_characterize_relative_strength_schema_unchanged`(M1 골든, 수정 없음) + `tests/test_weekly_insert.py`(수정 없음) | `PASSED` ×2, 영향 범위 실행에서 `test_weekly_insert.py` 포함 통과 |
| AC-RSR-016 | PASS | `test_ac_rsr_016_sector_composite_weights_unchanged` + 기존 7개 파일 `pytest tests/test_market_breadth.py tests/test_sector_metrics.py tests/test_ac_sag_044_regression.py tests/test_sector_benchmark_ranking.py tests/test_golden_baseline.py tests/test_market_api.py tests/test_m6_gap_closure.py -q` | `PASSED`; 7개 파일 `140 passed in 16.12s`(증거 `ac016_composite.log`) |
| AC-RSR-014 (도구) | PASS | `test_ac_rsr_014_production_mode_reads_rs_12m_rating_only`(고정 등급 → 지속률 `100.0`), `test_ac_rsr_014_db_flag_without_production_keeps_raw_formula_mode`(같은 픽스처의 원시 IBD식 `13.64` < 50) | `PASSED` ×2 |
| AC-RSR-014 (기계적 독립성) | PASS | `grep -n "def score_production" scripts/rs_eval/stock_rs_eval.py` → `81:def score_production(d): return pr(d.RS_12M_Rating)`; 같은 줄에 `grep -cE "RS_(1|3|6|9|12)M\b"` → `0` | — |
| AC-RSR-014 (기준선) | 측정 완료 | 위 기준선 명령 | `29.24` (< 60, 기준선 자체가 대조 관측) |
| AC-RSR-014 (목표 ≥ 60) | **열림** | 재생성 후 `weekly_after_rsr.db`에서 같은 명령 | 재생성 전이라 미측정 |

**대조 RED (lessons #9).** 실행기 `.moai/state/verify/rsr-m2/contrasts.py`가 회귀를 문자열 치환으로 하나씩 넣고 대상 테스트를 돌린 뒤 원본 바이트로 복구했다. 9건 모두 `exit=1`, 끝줄 `ALL_RED`(원문 `contrasts.log`).

| # | 넣은 회귀 | 대상 | 관측(원문 발췌) |
|---|---|---|---|
| K1 | 현행 1M 가중 순위합으로 되돌림 | 005 | `{'B': 50.0} != {'B': 75.0}`, `{'D': 75.0} != {'D': 50.0}` |
| K2 | 분기 수익률을 차분식으로 | 005 | `{'B': 100.0} != {'B': 75.0}`, `{'A': 75.0} != {'A': 100.0}` |
| K3 | 12M 단독 | 005 | `{'A': 75.0} != {'A': 100.0}`, `{'B': 100.0} != {'B': 75.0}` |
| K4 | 분기 가중치 0.25 균등 | 005 | `{'A': 75.0} != {'A': 100.0}`, `{'B': 100.0} != {'B': 75.0}` |
| K5 | `RS_6`에서 `rank_1m` 제거 | 006 골든 | `AssertionError: B / assert np.float64(50.0) == 25.0` |
| K6 | `RS_3`에서 `rank_1m` 제거 | 006 골든 | `AssertionError: A / assert np.float64(100.0) == 50.0` |
| K7 | `RS_1M_Rating`을 `rank_3m`으로 | 006 골든 | `AssertionError: A / assert np.float64(100.0) == 25.0` |
| K8 | 섹터 가중치 `1w` 0.30 → 0.35 | 016 | `{'1w': 0.35} != {'1w': 0.3}` |
| K9 | 프로덕션 점수를 원시 `RS_12M`에서 계산 | 014 | `assert 12.12 == 100.0` |

복구 증명: 실행 직후 `git status --short` → `M my_chart/db/weekly.py`, `M scripts/rs_eval/stock_rs_eval.py`, `?? .moai/logs/`, `?? tests/test_rsr_m2_eval_production.py`, `?? tests/test_rsr_m2_ibd.py`(대조 전과 같은 목록), `git diff --stat` → `weekly.py | 28`, `stock_rs_eval.py | 29`(대조 전과 같음). 그 뒤 영향 범위 실행이 전부 통과했다(아래).

**함정 기록(대조 실행기).** 첫 대조 실행 직후 영향 범위 테스트에서 4건이 실패했다(`RS_1M_Rating`이 모두 62.5). 원인은 K7이 같은 길이(`rank_1m` → `rank_3m`)로 바꿔 같은 초 안에 복구되어, 파이썬이 크기·mtime이 같은 낡은 `.pyc`를 재사용한 것이다. 소스는 정상이었다(`grep -n 'df\["RS_1M_Rating"\] = ' my_chart/db/weekly.py` → `547:        df["RS_1M_Rating"] = rank_1m`). `.pyc`를 지우고, 실행기가 대조마다 새 `PYTHONPYCACHEPREFIX`를 쓰게 고친 뒤 대조 9건을 다시 돌려 모두 RED, 영향 범위를 다시 돌려 모두 통과했다. 같은 길이 치환을 쓰는 대조 실행기는 바이트코드 캐시를 격리해야 한다.

**영향 범위 회귀.** `pytest tests/test_rsr_m2_ibd.py tests/test_rsr_m2_eval_production.py tests/test_rsr_characterization.py tests/test_rsr_m1_denominator.py tests/test_weekly_insert.py tests/test_db_service.py tests/test_universe.py tests/test_stage_classifier.py tests/test_sector_metrics.py tests/test_market_breadth.py tests/test_consumer_dates.py -q` → `134 passed in 2.66s`(증거 `lane.log`). 작업 전 같은 목록(신규 2개 파일 제외)은 `130 passed in 1.29s`. 커밋 시 pre-commit 게이트(`moai gate`) 통과(exit 0). 첫 시도는 게이트가 새로 만든 워크트리 `.venv`의 `setuptools 82.0.1`에 `pkg_resources`가 없어 `test_ac_sag_045_r4_mut_rs_zero_fill_control` 1건이 실패했고(`ModuleNotFoundError: No module named 'pkg_resources'`), `setuptools<81`(→ 80.10.2)을 설치한 뒤 통과했다. 우회 플래그는 쓰지 않았다.

**린트.** `uvx ruff check --output-format concise my_chart/db/weekly.py scripts/rs_eval/stock_rs_eval.py tests/test_rsr_m2_ibd.py tests/test_rsr_m2_eval_production.py` → 16건(`weekly.py` F402 1, `stock_rs_eval.py` E401 2·E402 1·E701 1·E702 10·I001 1). 변경 전 두 파일(`git show HEAD:…`, 같은 디렉터리에 임시 복사해 같은 설정 적용) → 같은 16건. 새 경고 0, 신규 테스트 파일 0건.

**커버리지.** `coverage run --include='my_chart/db/weekly.py' -m pytest tests/test_rsr_m2_ibd.py tests/test_rsr_characterization.py tests/test_rsr_m1_denominator.py` → `my_chart/db/weekly.py 233 119 49%`, 미커버 `89-92, 122-131, 140-149, 155, 179, 204-208, 239-300, 326-387, 558, 561-562`. 새 함수 `_ibd_composite_score`(`430-445`)는 미커버 목록에 없다. 나머지는 M1과 같은 범위 밖 경로다.

**코드베이스 주장과 프로브 (lessons #10).**
- `generate_rs_db()`의 기본 경로는 cwd 상대가 아니라 **모듈 위치 기준 절대 경로**다: `my_chart/config.py:36` `OUTPUT_DIR = Path(__file__).parent.parent / "Output"`, `:43` `DEFAULT_DB_WEEKLY = str(OUTPUT_DIR / "stock_data_weekly")`. 프로브: 워크트리 cwd에서 `python -c "import my_chart.config as c; print(c.DEFAULT_DB_WEEKLY)"` → `…/agent-a902f867f6e063330/Output/stock_data_weekly`. `db_path = f"{db_name}.db"`가 cwd 상대가 되는 것은 상대 경로를 넘길 때뿐이다.
- `-I`로 실행하면 `my_chart`가 **다른 디렉터리**에서 import된다: `python -I -c "import importlib.util as u; print(u.find_spec('my_chart').origin)"` → `/Users/byunjungwon/Dev/my_chart/my_chart/__init__.py`. `-I` 없이 cwd에서 실행하면 cwd의 패키지가 잡힌다(`…/agent-a902f867f6e063330/my_chart/__init__.py`). 재생성 명령은 `-I`를 쓰면 안 된다.
- `backend/services/db_service.py:79-82` Phase 2는 `generate_rs_db(db_name=weekly_db_path.removesuffix(".db"), progress_callback=…)`이고, `weekly_db_path`는 `backend/deps.py:11` `WEEKLY_DB_PATH = f"{DEFAULT_DB_WEEKLY}.db"`에서 온다.
- `backend/services/meta_service.py:217`의 `rebuild_stock_meta()`가 `weekly.relative_strength`의 `RS_12M_Rating`을 `stock_meta.rs_12m`으로 복사한다. 따라서 RS만 재생성하면 `stock_meta.rs_12m`은 다음 Phase 4까지 옛 산식 값으로 남는다.

**미검증 (Gaps).**
- 라이브 재생성, `weekly_after_rsr.db` 생성, AC-RSR-014 목표(≥ 60), AC-RSR-001·002·017 라이브 단계 질의: 모두 이번 범위 밖이며 실행하지 않았다.
- `--db`가 실제로 무시되지 않음을 "라이브 경로를 읽는 회귀"로 주입해 RED를 보는 대조는 하지 않았다 — 그 회귀는 라이브 DB를 열기 때문이다. 대신 테스트 픽스처(210종목, 고정 등급)가 라이브 DB에서는 나올 수 없는 출력(`주수 7`, 지속률 `100.0`)을 내는 것으로 간접 확인했다.
- 기준선 29.24와 원시 모드 30.88의 차이를 3주 결측과 분모 의존으로 나눠 재지는 않았다(가설).
- `backend/tests` 스위트는 돌리지 않았다(게이트가 돌린 범위만).

**잔여 위험.**
- `stock_rs_eval.py`의 `sys.path`(`:6`)는 여전히 공용 체크아웃 절대 경로다. 스크립트가 거기서 가져오는 것은 `get_sector_registry`뿐이라 측정값에는 영향이 없지만, 워크트리에서 돌려도 등록부는 공용 체크아웃 코드로 읽는다.
- 재생성은 20개 날짜마다 커밋하므로, 서버가 실행 중이면 재생성 도중 일부 날짜만 새 산식인 상태를 읽을 수 있다.

### M2 (live regeneration, orchestrator-run, 2026-10-20)

- 사용자 확인 후 실행(§F.1). 백업 `Output/stock_data_weekly.db.bak_20261020`·변경 전 사본 `Output/snapshots/weekly_before_rsr.db` — 원본과 크기 390672384, sha256 앞 16자리 `949f29639a86da86`, `PRAGMA quick_check` ok, RS 794818행 동일 확인 후 진행
- 명령: 코드 cwd에서 `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -W ignore -c "import my_chart, my_chart.db.weekly as w; assert my_chart.__file__ == '…/my-project-01/my_chart/my_chart/__init__.py'; assert hasattr(w, '_ibd_composite_score'); w.generate_rs_db(db_name='…/Output/stock_data_weekly')"` → `[RS] Done: 355 dates processed`, `exit=0` (17:5x~18:13:58, 로그 `.moai/state/verify/c1bf371e/m2_regen.log`)
- 변경 후 사본 `Output/snapshots/weekly_after_rsr.db` (`quick_check` ok)
- 라이브 질의(immutable 읽기, `.moai/state/verify/c1bf371e/m2_live_queries.log`):

| AC | 질의 | 변경 전 | 변경 후 |
|---|---|---|---|
| AC-RSR-001 | 짝 없는 행 `LEFT JOIN stock_prices … WHERE sp.Name IS NULL` | 119881 | **0** |
| AC-RSR-002 | 지수 행 `Name IN ('KOSPI','KOSDAQ')` | 692 | **0** |
| AC-RSR-002 | 거래량 0 짝 행 `JOIN … WHERE sp.Volume = 0` | 16369 | **0** |
| AC-RSR-017 | 기준 종목 날짜가 아닌 날짜의 행 | 5 | **0** |

- 테이블 전체: 657965행 / 300개 날짜 / 최신 2026-10-16. 사라진 날짜 46개 = 가격 테이블에 없는 날짜 42 + 비기준 날짜 4, 기준 날짜 0 (research.md R2 예측과 일치)
- 최신 주차 등급 종목: 2490 → 2387 (거래량 0 101 + 지수 2 제외, 2490−103=2387)
- `RS_12M_Rating` 범위 0.0417~100.0, 80 이상 몫 20.03% (B-3 근거 ≈20% 유지)
- **AC-RSR-014 목표**: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db Output/snapshots/weekly_after_rsr.db` → 상위10_지속률 **65.17** (기준선 29.24, 목표 ≥ 60) — **PASS**. 같은 줄: 주수 295, 상위10_초과pp 1.66, 상하위스프레드pp −0.25, IC양수비율 30.85 (`.moai/state/verify/c1bf371e/m2_after_eval.log`)
- 미반영: `stock_meta.rs_12m`(일봉)은 M4 메타 재구축 전까지 옛 산식 값

### M3 — Stage 2 상수 재보정 (manager-develop, cycle_type=tdd, 2026-10-20)

**작업 위치.** 런타임 L1 워크트리 `.claude/worktrees/agent-ab2bce17db19aa63c`(브랜치 `worktree-agent-ab2bce17db19aa63c`). 기준점 `fd5f11f`에서 `git merge --ff-only main`으로 `305cdcb`까지 빨리 감기한 뒤 작업했다. 커밋은 이 워크트리 브랜치에만 있다. 공용 체크아웃의 `Output/stock_data_{weekly,daily}.db`를 워크트리 `Output/`에 복사했고(게이트용, 원본은 읽기만), 워크트리 `.venv`에 `setuptools<81`을 설치했다(`82.0.1 → 80.10.2`). 이 설치 전 첫 커밋 시도는 게이트에서 `test_ac_sag_045_r4_mut_rs_zero_fill_control` 1건(`ModuleNotFoundError: No module named 'pkg_resources'`)으로 막혔다 — 프로젝트 메모리 `project_worktree_precommit_db_trap`과 같은 원인이다. 우회 플래그는 쓰지 않았다. 프론트 도구는 공용 체크아웃 `frontend/node_modules`를 심볼릭 링크로 연결해 썼다(gitignore 대상).

**커밋.**

| SHA | 내용 | `git show --stat` |
|---|---|---|
| `6b09f06` | 측정 도구 + 단일 정의 지점 + 교차 언어 등식 + 테스트 | `backend/services/screen_service.py` 5 (+4 −1), `frontend/src/components/StockExplorer/StockTable.tsx` 9, `frontend/src/utils/__tests__/rsMetrics.test.ts` 34, `frontend/src/utils/rsMetrics.ts` 4, `scripts/rs_eval/stage2_ratio_eval.py` +101, `tests/test_rsr_m3_stage2_ratio_eval.py` +149, `tests/test_rsr_m3_threshold_single_source.py` +43 |

**측정 (AC-RSR-015).** 사본은 측정 전후 모두 `shasum -a 256 … | cut -c1-16` → before `949f29639a86da86`, after `abecc43e98dc47b0`로 같았고, `ls -la Output/snapshots/`에는 두 `.db` 파일뿐이었다(스크립트는 `mode=ro&immutable=1`로만 연다). 명령 형식(워크트리 cwd, `S=/Users/byunjungwon/Dev/my-project-01/my_chart/Output/snapshots`):

```
/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stage2_ratio_eval.py --db $S/weekly_<copy>_rsr.db --weeks 12 --mode <conditional|strong> --threshold <t> --ref-db $S/weekly_<other>_rsr.db
```

`--ref-db`는 W를 두 사본 공통 기준 종목 날짜로 제한한다. 8회 실행 모두 `exit=0`, 출력의 W 줄이 같았다(`grep -h '^W=' … | sort | uniq -c` → `8 W=2026-07-31,2026-08-07,2026-08-14,2026-08-21,2026-08-28,2026-09-04,2026-09-11,2026-09-18,2026-09-23,2026-10-02,2026-10-08,2026-10-16 (n=12)`). 원문 로그: 워크트리 `.moai/state/verify/rsr-m3/cond_{before,after}_{60,70,80}.log`, `strong_{before,after}_60.log`.

(a) 조건부 RS 통과율 — W 평균(마지막 줄 `mean=… n_dates=12` 원문):

| 사본 | c60 | c70 | c80 | 엄격 단조 | c60 − c80 | 0.10 × c70 | 사전 조건 |
|---|---|---|---|---|---|---|---|
| 변경 전 | 100.00 | 99.48 | 97.85 | 성립 | 2.15 | 9.948 | **미충족** |
| 변경 후 | 99.58 | 94.42 | 84.87 | 성립 | 14.71 | 9.442 | **충족** |

날짜별 분모(RS 외 조건 다섯 개 통과 종목 수, T2)와 분자(`num`) — 두 사본의 분모는 날짜마다 같다:

| 날짜 | 분모 | 전·60 | 전·70 | 전·80 | 후·60 | 후·70 | 후·80 |
|---|---|---|---|---|---|---|---|
| 2026-07-31 | 16 | 16 | 16 | 15 | 16 | 16 | 14 |
| 2026-08-07 | 23 | 23 | 23 | 23 | 23 | 23 | 21 |
| 2026-08-14 | 45 | 45 | 45 | 45 | 44 | 43 | 40 |
| 2026-08-21 | 16 | 16 | 16 | 16 | 16 | 16 | 16 |
| 2026-08-28 | 24 | 24 | 24 | 23 | 24 | 23 | 20 |
| 2026-09-04 | 26 | 26 | 26 | 26 | 26 | 26 | 25 |
| 2026-09-11 | 28 | 28 | 28 | 28 | 28 | 28 | 26 |
| 2026-09-18 | 26 | 26 | 26 | 26 | 26 | 25 | 21 |
| 2026-09-23 | 12 | 12 | 12 | 12 | 12 | 9 | 8 |
| 2026-10-02 | 35 | 35 | 35 | 34 | 34 | 31 | 28 |
| 2026-10-08 | 16 | 16 | 15 | 14 | 16 | 14 | 12 |
| 2026-10-16 | 54 | 54 | 54 | 54 | 54 | 51 | 41 |

변경 전 사본 값은 research.md R15(`60 100.0 / 70 99.48 / 80 97.85`, 분모 `[54, 16, 35, 12, 26, 28, 26, 24, 16, 45, 23, 16]`)와, 변경 후 사본 값은 plan-audit iter-3 모의(`99.58 / 94.42 / 84.87`)와 같다.

(b) Stage 2 강세 비중 — 60 기준:

| 측정 | 사본·상수 | W 평균 |
|---|---|---|
| (1) | 변경 전·현행 60 | 33.53 |
| (2) | 변경 후·현행 60 | 33.72 |
| (3) | 변경 후·채택 60 | 33.72 (= (2), 채택값이 현행값) |

날짜별 분모(Stage 2 종목 수)는 두 사본에서 같다: `250, 361, 467, 370, 458, 446, 461, 486, 469, 563, 556, 390`. Strong 분자 — 변경 전 `75, 126, 173, 112, 158, 162, 165, 165, 176, 173, 167, 122`, 변경 후 `75, 127, 176, 112, 157, 163, 166, 166, 179, 177, 165, 122`. (1) 33.53은 plan-audit iter-2 기준선, (2) 33.72는 iter-3 부채 T3의 예측값과 같다.

**판정.**

- **70 (`_STAGE2_ENTRY_RS_MIN`)**: 사전 조건은 변경 후 사본에서 충족 → REQ-RSR-018 (a) 적용(두 사본 중 하나라도 충족, T1). 2단계 허용오차 `0.10 × 99.48 = 9.948`. 현행 70의 변경 후 값 `|94.42 − 99.48| = 5.06 <= 9.948` → 허용오차 안이므로 **70 유지**(현행값이 자격을 갖추면 유지). 대조(2단계): 같은 사본의 80은 `|84.87 − 99.48| = 14.61 > 9.948`로 허용오차 밖 — 판별 폭이 실제로 있음을 관측했다. "기록만" 모드는 해당 없음(에스컬레이션 조건 미발생).
- **60 (`_STAGE2_RS_STRONG`)**: (2) − (1) = 33.72 − 33.53 = 0.19%p `<= 5`%p → **60 유지**. (3) = (2)이고 (3)이 (1)의 ±5%p 안이다. AC 대조 조건 "60을 유지하면 (2)가 (1)과 ±5%p 이내" 충족.
- **80 (`_RS_TOP_THRESHOLD`/`RS_TOP_THRESHOLD`)**: B-3에 따라 측정 대상 아님, 변경 없음.
- 결과적으로 `stage_classifier.py`와 `rsMetrics.ts`의 상수 **값은 바뀌지 않았다**. 따라서 plan.md §G의 "M3 — 70/60 값이 바뀌면 경계 기대 재검토" 4개 파일은 기대값을 고칠 근거가 없어 수정하지 않았다.

**RED (구현 전).**
- 측정 도구: `python -m pytest tests/test_rsr_m3_stage2_ratio_eval.py -q` → `6 failed in 0.55s`, 원문 `can't open file '…/scripts/rs_eval/stage2_ratio_eval.py': [Errno 2] No such file or directory`(증거 `red_eval.log`).
- T8 단일 정의 지점: `python -m pytest tests/test_rsr_m3_threshold_single_source.py -q` → `1 failed, 1 passed in 0.37s`, 원문 `E       assert not True` / `E        +  where True = _passes_minervini()`(증거 `red_t8.log`) — 상수를 80으로 바꿔도 리터럴 70인 T8이 `rs_12m = 75`를 통과시킨다. 통과한 1건은 현행 상수(70)에서 75가 통과하는지 보는 기준 테스트다.
- AC-RSR-013 스캔(변경 전): 4줄, acceptance.md의 변경 전 관측과 같다(`StockTable.tsx:32`, `:39`, `:263`, `screen_service.py:61`).

**GREEN (`6b09f06`).**

| AC | 상태 | 명령 | 출력 |
|---|---|---|---|
| AC-RSR-013 (스캔) | PASS | `grep -n -E 'rs_12m\s*>=\s*[0-9]\|RS Strong[^"]*[0-9]' backend/services/screen_service.py frontend/src/components/StockExplorer/StockTable.tsx` | 0줄, `exit=1` |
| AC-RSR-013 (교차 언어·80 유지) | PASS | `npm --prefix frontend exec vitest -- run --root frontend src/utils/__tests__/rsMetrics.test.ts src/components/StockExplorer` | `Test Files 10 passed (10)`, `Tests 74 passed (74)`(증거 `green_fe.log`) |
| AC-RSR-013 (T8 공유 상수) | PASS | `python -m pytest tests/test_rsr_m3_threshold_single_source.py -q` | `2 passed in 0.30s` |
| AC-RSR-015 (도구) | PASS | `python -m pytest tests/test_rsr_m3_stage2_ratio_eval.py -v` | `6 passed in 3.46s`(증거 `green_eval.log`) |
| AC-RSR-015 (측정·판정) | PASS | 위 8회 측정 | 70: (a) 2단계 5.06 <= 9.948, 60: 0.19%p <= 5%p |

**대조 RED (lessons #9).** 실행기 `.moai/state/verify/rsr-m3/contrasts.py`가 회귀를 하나씩 문자열 치환으로 넣고 가드를 돌린 뒤 원본 바이트로 복구했다(대조마다 새 `PYTHONPYCACHEPREFIX`, M2 함정 기록 반영). 15건 모두 RED, 끝줄 `ALL_RED`(원문 `contrasts.log`).

| # | 넣은 회귀 | 가드 | 관측(원문 발췌) |
|---|---|---|---|
| A1 | `:263` 라벨을 리터럴 `"RS Strong (≥ 70)"`로 | AC-013 스캔 | `grep lines=1: …StockTable.tsx:264: … label="RS Strong (≥ 70)"` |
| A2 | 라벨을 재보정 숫자 `"RS Strong (≥ 65)"`로 | AC-013 스캔 | `grep lines=1: … label="RS Strong (≥ 65)"` |
| A3 | `:39` 술어를 `c.rs_12m >= 70`으로 | AC-013 스캔 | `grep lines=1: …StockTable.tsx:40:    rs: c.rs_12m >= 70,` |
| A4 | `:32` 주석을 `// rs_12m >= 70`으로 | AC-013 스캔 | `grep lines=1: …StockTable.tsx:33:  rs: boolean    // rs_12m >= 70` |
| A5 | T8을 리터럴 `" AND rs_12m >= 70"`으로 | AC-013 스캔 | `grep lines=1: backend/services/screen_service.py:64: " AND rs_12m >= 70"  # T8` |
| A6 | 같은 T8 리터럴 | T8 동작 테스트 | `E       assert not True`, `1 failed, 1 passed` |
| B1 | 백엔드 `_STAGE2_ENTRY_RS_MIN` 70→65, 거울 그대로 | 교차 언어 | `AssertionError: expected 70 to be 65` |
| B2 | 백엔드 `_STAGE2_RS_STRONG` 60→65, 거울 그대로 | 교차 언어 | `AssertionError: expected 60 to be 65` |
| B3 | 거울 `RS_STRONG_THRESHOLD` 70→65, 백엔드 그대로 | 교차 언어 | `AssertionError: expected 65 to be 70` |
| B4 | 백엔드 `_RS_TOP_THRESHOLD` 80→85 | 등식 + 80 유지 | `2 failed`, `expected 80 to be 85` |
| B5 | `_RS_TOP_THRESHOLD`·`RS_TOP_THRESHOLD` 함께 80→85 | 80 유지 | `1 failed`, `상위 임계값 80 은 재보정 대상이 아니다 … expected 85 to be 80` |
| E1 | conditional 분모를 Stage 2 전체로 | 도구 테스트 | `assert {…'2026-01-09': (9, 2)} == {…'2026-01-09': (5, 2)}`, `assert 38.89 == 70.0` |
| E2 | strong 분자를 `rs_12m >= t`로(경계 포함, detail 무시) | 도구 테스트 | `assert {'2026-01-02': (5, 4)} == {'2026-01-02': (5, 2)}` |
| E3 | `--ref-db` 교집합 무시 | 도구 테스트 | `assert ['2026-01-16', '2026-01-23'] == ['2026-01-09', '2026-01-16']` |
| E4 | strong에서 상수 치환 누락 | 도구 테스트 | `assert 40.0 == 20.0` |

추가 대조 — 옛 리터럴 단언의 판별력 부재: `git show HEAD:frontend/src/utils/__tests__/rsMetrics.test.ts`(`305cdcb`판)를 임시 파일로 두고 백엔드 `_STAGE2_ENTRY_RS_MIN`을 65로 바꿔 두 파일을 함께 돌리면 `Tests 1 failed | 6 passed (7)` — 실패는 새 파일의 `RS_STRONG_THRESHOLD === 백엔드 _STAGE2_ENTRY_RS_MIN` 1건뿐이고 옛 판 2건은 통과했다(증거 `contrast_head_literal.log`). 즉 옛 단언은 백엔드 값이 갈라져도 잡지 못했다. 임시 파일은 삭제, `stage_classifier.py`는 사본에서 복구했다.

복구 증명: 대조 직후 `git status --short` → `M` 4개 파일 + `??` 신규 3개 + `?? .moai/logs/`(대조 전과 같은 목록), `git diff --stat` → `4 files changed, 38 insertions(+), 14 deletions(-)`(대조 전과 같음).

**§G "M3" 4개 파일 재실행.**
- `python -m pytest backend/tests/test_minervini_template.py tests/test_market_breadth.py tests/test_stage_classifier.py -q` → `3 failed, 59 passed`(변경 전 `305cdcb`에서도 같은 3건 `3 failed, 59 passed`, 증거 `baseline_py.log`·`after_py_g.log`). 실패 3건은 `TestGroupC_ScreenService`의 `test_minervini_where_all_conditions_met`·`test_trend_template_score_is_8_for_all_returned_rows`·`test_minervini_with_existing_filters_combined`로, 캡처 로그가 두 실행 모두 `[minervini] required columns missing`(각 3회)이다. 원인 프로브: `_MINERVINI_META_COLS = ("sma150", "low52w", "sma200_20d_ago", "sma5")`(`backend/services/meta_service.py:59`)인데 `grep -cw sma5 backend/tests/test_minervini_template.py` → `0`(픽스처에 `sma5` 컬럼 없음). `sma5`는 `b1dfe17`(`fix(screening): 레거시 stock_meta 자가치유 — SMA5 패턴 0건 반환 해결`)에서 필수 컬럼에 들어갔다. M3와 무관한 기존 결함이며 임계값 변경이 원인이 아니므로 고치지 않았다.
- `StockTable.test.tsx`: 위 vitest 실행에 포함, 통과(기대값 수정 없음).

**영향 범위 회귀.** `python -m pytest tests/test_rsr_m3_stage2_ratio_eval.py tests/test_rsr_m3_threshold_single_source.py tests/test_rsr_m2_ibd.py tests/test_rsr_m2_eval_production.py tests/test_rsr_characterization.py tests/test_rsr_m1_denominator.py tests/test_screen_service.py tests/test_screen_codes_filter.py tests/test_stage_classifier.py tests/test_market_breadth.py tests/test_sector_metrics.py tests/test_universe.py tests/test_consumer_dates.py tests/test_api.py -q` → `177 passed in 5.74s`(증거 `lane.log`). 타입 검사 `npm --prefix frontend exec tsc -- -b frontend/tsconfig.json` → `exit=0`, 출력 없음. 커밋 시 pre-commit 게이트(`moai gate`, 전체 `tests/`)가 통과해 `6b09f06`이 생성됐다(게이트 실패 시 커밋이 막힌다는 것은 첫 시도에서 관측).

**린트.** `uvx ruff check --output-format concise scripts/rs_eval/stage2_ratio_eval.py tests/test_rsr_m3_stage2_ratio_eval.py tests/test_rsr_m3_threshold_single_source.py backend/services/screen_service.py` → `All checks passed!`. `npm --prefix frontend exec eslint -- --config frontend/eslint.config.js <변경된 TS 3개>` → `exit=0`, 출력 없음.

**커버리지.** `coverage run --include='scripts/rs_eval/stage2_ratio_eval.py'`로 스크립트를 변경 후 사본에서 conditional(`--ref-db` 포함)·strong 각 1회 실행 → `scripts/rs_eval/stage2_ratio_eval.py 55 0 100%`. 도구 테스트 6건은 `-I` 서브프로세스로 스크립트를 실행하므로 pytest 커버리지에는 잡히지 않는다. `screen_service.py`의 바뀐 T8 줄은 T8 테스트 2건이 실제 SQLite에서 실행한다.

**코드베이스 주장과 프로브 (lessons #10).**
- 측정 스크립트는 `-I`로 실행해도 이 저장소의 `my_chart`를 쓴다: 스크립트가 `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))`를 먼저 한다. M2 프로브(`-I`면 `/Users/byunjungwon/Dev/my_chart/my_chart`가 잡힘)와 다른 동작이며, 도구 테스트가 이 경로로 워크트리 코드를 실행해 통과한 것이 근거다(E1~E4 대조가 워크트리 스크립트 수정을 감지).
- conditional 분모는 `screen_stage2_entry()`를 `_STAGE2_ENTRY_RS_MIN = -inf`로 불러 얻는다 — 조건 5(`if rs < _STAGE2_ENTRY_RS_MIN`, `stage_classifier.py:291`)만 무력화되고 조건 1·2·3·4·6은 프로덕션 코드 그대로다. strong은 `classify_all()`(`:218-234`)을 그대로 부른다. 두 함수의 `sqlite3.connect`는 스크립트가 모듈 속성 `stage_classifier.sqlite3`를 읽기 전용 래퍼로 바꿔 사본을 `mode=ro&immutable=1`로 연다.
- 등급 행이 없는 종목은 `_load_stocks_for_classification()`의 `LEFT JOIN`과 `float(… or 0.0)`(`:272`)로 RS 0 취급되어 conditional 분모에는 들고 분자에서는 빠진다 — 도구 테스트 픽스처 `P5`가 이 경로를 고정한다.

**미검증 (Gaps).**
- `backend/tests/test_minervini_template.py`의 Minervini 경로 3건은 기존 픽스처 결함(`sma5` 부재)으로 빈 결과를 내므로, 이 파일로는 T8 동작을 확인하지 못했다. T8은 새 테스트 `tests/test_rsr_m3_threshold_single_source.py`가 대신 고정한다.
- `backend/tests` 전체 스위트는 돌리지 않았다(게이트는 `tests/`만 수집한다 — 게이트 로그의 `testpaths: tests`).
- dev 서버 재시작 후 화면 확인은 하지 않았다. 라벨 문자열은 상수가 70인 동안 `RS Strong (≥ 70)`으로 같으며, StockTable 테스트가 통과했다는 것 외의 화면 관측은 없다.
- `stage2_ratio_eval.py`의 분모 0 날짜 처리(평균에서 제외) 분기는 실데이터·테스트 모두에서 발생하지 않아 관측하지 않았다.

**잔여 위험.**
- (a)의 분모가 날짜별 12~54개라 상대 ±10%(9.948%p)는 날짜에 따라 종목 1~5개 차이에 해당한다(T2). 70 유지 판정의 여유는 4.89%p(9.948 − 5.06)다.
- 측정 스크립트는 `stage_classifier`의 모듈 전역(`sqlite3`, 두 상수)을 프로세스 안에서 덮어쓴다. 별도 프로세스로만 실행되므로 서버에는 영향이 없지만, 이 스크립트를 다른 코드에서 import해 `main()`을 부르면 그 프로세스의 상수가 바뀐다.

### M4 (pre-rebuild) — 백엔드 필드 (manager-develop, cycle_type=tdd, 2026-10-20)

**범위.** 라이브 `stock_meta` 재구축(Phase 4) **직전까지**. 라이브 DB에는 쓰지 않았다. 작업 위치는 L1 워크트리 `.claude/worktrees/agent-a078264dfa8653ed3`(브랜치 `worktree-agent-a078264dfa8653ed3`)이며, 시작 시 `git merge --ff-only main`으로 `97831f4`까지 빨리 감았다(`git rev-parse --short HEAD` → `97831f4`). 증거 파일은 전부 `.moai/state/verify/c1bf371e/m4/`에 있다.

**커밋.** `15ba7b6` — 운영 12개 + 축약 DDL 테스트 8개 + 신규 테스트 3개, `git show --stat` → `23 files changed, 644 insertions(+), 42 deletions(-)`. 첫 커밋 시도는 pre-commit 게이트가 막았다(`tests/test_ac_sag_045_r1_r4_r5a.py`의 하위 프로세스가 `ModuleNotFoundError: No module named 'pkg_resources'` — 게이트가 새로 만든 워크트리 `.venv`에 setuptools 82.0.1이 깔린 환경 문제, M4 코드와 무관). `uv pip install --python .venv/bin/python "setuptools<81"`(→ `80.10.2`) 후 재시도에서 게이트 통과로 커밋이 생성됐다.

**RED (구현 전, `97831f4` 트리 + 신규 테스트만).**
- `pytest tests/test_rsr_m4_stock_meta_rs1m.py -q` → `3 failed in 0.38s` (`red_meta.log`): `sqlite3.OperationalError: no such column: rs_1m` ×2, AC-008은 `AssertionError: 컬럼 순서=[… 'sma5']` / `Right contains one more item: 'rs_1m'`.
- `pytest tests/test_rsr_m4_rs1m_responses.py -q` → `2 failed in 1.38s` (`red_resp.log`): `AssertionError: /stage/overview all_stocks: BGF리테일 항목에 rs_1m 필드가 없다`, `/sectors/Auto/bubble: DN오토모티브 항목에 rs_1m 필드가 없다`.
- `pytest tests/test_rsr_m4_rs_med.py -q` → `7 failed in 0.39s` (`red_med.log`): `AttributeError: 'SectorRankItem' object has no attribute 'rs_med'`, `'SectorAggregateModel' …`, `'SectorAggregate' …`.

**AC 판정 (GREEN, `15ba7b6` 트리).** `pytest tests/test_rsr_m4_stock_meta_rs1m.py tests/test_rsr_m4_rs1m_responses.py tests/test_rsr_m4_rs_med.py -v` → `12 passed in 1.68s` (`green_ac.log`).

| AC | Status | 테스트 | 양변 출처 |
|---|---|---|---|
| AC-RSR-007 (픽스처 단계) | PASS | `test_ac_rsr_007_rs_1m_copied_from_latest_week` | `stock_meta.rs_1m` 읽기 vs 리터럴(최신 주차 1M 값; 앞 주차·12M 값은 모두 다르게 심음; RS 행 없는 `라종목` → NULL) |
| AC-RSR-007 (라이브 단계) | 미실행 | — | 라이브 재구축 후 오케스트레이터 몫 |
| AC-RSR-008 | PASS | `test_ac_rsr_008_legacy_stock_meta_gets_rs_1m_appended` | 라이브 컬럼명(`ma50_w ma150_w ma200_w`) 27컬럼 레거시 테이블 → `PRAGMA table_info` 끝이 `rs_1m`, 기존 27개 값 = 픽스처 기대값, 2회 실행(멱등) |
| AC-RSR-008b | PASS | `test_ac_rsr_008b_new_db_rs_1m_is_last_column_and_28th_value` | 마지막 행 `(27, 'rs_1m')`, `sma5 = 5.555`, `rs_1m = 11.0`, `rs_12m = 22.0` |
| AC-RSR-009 | PASS | `test_ac_rsr_009_stage_overview_rs_1m`, `test_ac_rsr_009_stock_bubble_rs_1m` | TestClient 응답 vs 고정 픽스처 `aggregation-2026-08-11/weekly.db` 독립 SQL(immutable 읽기). `all_stocks`·`stage2_candidates`·RS 결측 종목이 있는 섹터 전부의 버블 |
| AC-RSR-010 | PASS | `test_ac_rsr_010_*` 7건 | `get_sector_ranking()`의 `sectors[]`와 봉투 `data[]` vs 리터럴(P 30.0 / Q 50.0 / R 30.0, `rs_avg` 50.0, `rs_top_pct` 40.0·0.0) + 유효 RS 0개 섹터의 `rs_med` = `missing` |

AC-RSR-010의 하위 호환(REQ-RSR-014): `tests/test_ac_sag_030_rs_avg.py`는 아래 전체 스위트 실행에서 통과(`tests/` 1070 passed 안에 포함).

**대조 (lessons #9).** `contrast.py`가 운영 파일에 회귀를 주입 → 대상 테스트 실행 → 원래 바이트로 원복 → sha256 앞 16자리 비교 → 재실행. 원문 `contrast.log`·`contrast_c10.log`.

| # | 주입 | 관측 RED(원문) | 원복 |
|---|---|---|---|
| C1 | 튜플에서 `rs_1m`을 `rs_12m` 다음으로(중간 삽입) | AC-008b `AssertionError: sma5=1011.0`(= `sma200_20d_ago` 값), AC-007 `rs_1m={'가종목': 1004.0, …}`, AC-008 실패 → `3 failed` | sha `626c4932201475a6` 일치, `3 passed` |
| C2 | DDL에서 `rs_1m`을 `rs_12m` 다음으로 | `AssertionError: 마지막 컬럼=(27, 'sma5', 'REAL', 0, None, 0)` | 일치, `1 passed` |
| C3 | ALTER 목록에서 `_RS_META_COLS` 제거 | `sqlite3.OperationalError: table stock_meta has 27 columns but 28 values were supplied` | 일치, `1 passed` |
| C4 | Phase 4 복사 제거(`None`) | `stock_meta.rs_1m={'가종목': None, '나종목': None, '다종목': None, '라종목': None}` | 일치, `1 passed` |
| C5 | `rs_1m`에 `RS_12M_Rating` 연결 | `stock_meta.rs_1m={'가종목': 91.0, '나종목': 42.0, '다종목': 12.0, '라종목': None}` | 일치, `1 passed` |
| C10 | RS 질의를 앞 주차로 | `stock_meta.rs_1m={'가종목': 61.0, '나종목': 33.0, '다종목': 44.0, '라종목': None}` | 일치, `1 passed` |
| C6a | 종목 응답 `RS_1M_Rating`에 12M 열(`r[8]`) | `BGF리테일 rs_1m=96.18 != RS_1M_Rating=80.28112449799197` | sha `9e1783948e087797` 일치, `1 passed` |
| C6b | 버블 `rs_1m` dict를 12M 열에서 | `DN오토모티브 rs_1m=97.27 != RS_1M_Rating=80.56224899598394` | sha `0d2b32a5d89e2446` 일치, `1 passed` |
| C7 | `RS_1M_Rating`을 SELECT에서 빼고 `None` | `BGF리테일 rs_1m=None != RS_1M_Rating=80.28112449799197` | sha `9e1783948e087797` 일치, `1 passed` |
| C8 | `rs_med = rs_avg`(평균) | `섹터P rs_med=MetricValueModel(value=50.0, …)`, `섹터R rs_med=50.0` → `4 failed, 3 passed` | sha `bb4b55b5ccc5090a` 일치, `7 passed` |
| C9 | 결측을 0으로 채운 중앙값 | `섹터R rs_med=25.0`, `assert 0.0 is None` → `3 failed, 4 passed` | 일치, `7 passed` |

대조 전후 `git diff --stat` → 둘 다 `20 files changed, 110 insertions(+), 42 deletions(-)`(커밋 전 작업 트리, 같은 값).

**축약 DDL RED 판정 (plan.md §G "M4 조건부").** 2단계(주간 질의 변경) 직후, 테스트 DDL을 고치기 전에 두 스위트를 돌렸다.
- `pytest tests -q` → `22 failed, 1048 passed, 1 skipped, 95 deselected, 1 xpassed` (`post_step2_tests.log`)
- `pytest backend/tests -q` → `38 failed, 319 passed, 1 warning, 58 errors` (`post_step2_backend.log`)
- 실패 파일만 모아 `--tb=line`으로 재실행 → `59 failed, 114 passed` (`red_classify.log`). 원인 줄 집계: `no such column: RS_1M_Rating` 64줄, `no such column: rs.RS_1M_Rating` 36줄, `test_market_api.py`는 503 응답 본문 `'detail': 'no such column: rs.RS_1M_Rating'`. 나머지 실패 4건(`test_minervini_template.py` GroupC 3건 `S9가 결과에 없음` 등, `test_bubble_empty_date_edge.py` 1건)은 기준선에도 있던 실패다.

| 파일 | RED 건수 | 경로 | 조치 |
|---|---|---|---|
| `tests/test_consumer_dates.py` | 1 (+ `tests/test_ac_sag_037_endpoint_date_consistency.py` 5건 — 이 파일의 `_build_fixture_max_ne_canonical`을 import) | `meta_service`·`stage_classifier`·`sector_advanced` | DDL 1줄 + INSERT 열 목록 |
| `tests/test_market_api.py` | 6 | `stage_classifier` | DDL + INSERT 1곳 |
| `tests/test_stage_classifier.py` | 7 | `stage_classifier` | DDL + INSERT 6곳 |
| `tests/test_universe.py` | 3 | `stage_classifier` | DDL + INSERT |
| `backend/tests/test_minervini_template.py` | 3 (GroupB) | `meta_service` | 주간 `_create_weekly_db` DDL만 — 일봉 DDL 2곳은 RS 질의를 타지 않아 손대지 않음 |
| `backend/tests/test_sector_advanced.py` | 25 | `sector_advanced._get_rs_on_date` | DDL 9곳 중 RED 경로 6곳(`_create_test_db`, sector_minor·product 4건, `_make_volume_ratio_db`) + 해당 INSERT 7곳. 빈 DB·RRG·빈 알림 DDL 3곳은 변경 없이 통과 |
| `backend/tests/test_sector_detail_service.py` | 3 | `stage_classifier` | DDL + INSERT |
| `backend/tests/test_stage_service.py` | 3 | `stage_classifier` | DDL + INSERT |

RED가 나지 않아 손대지 않은 §G "M4 조건부" 파일: `tests/conftest.py`, `tests/test_market_breadth.py`, `tests/test_sector_history_consistency.py`, `tests/test_sector_metrics.py`(섹터 집계 질의 `_load_weekly_snapshot`은 `RS_1M_Rating`을 읽지 않음), `backend/tests/test_bubble_rs_missing_exclusion.py`. INSERT를 열 목록 형태(`INSERT INTO relative_strength (Name, Date, RS_12M_Rating) VALUES (…)`)로 바꾼 것은 위치 삽입이 4번째 컬럼 때문에 `table has 4 columns but 3 values`로 깨지기 때문이다. 운영 코드에는 컬럼 부재 허용 분기를 넣지 않았다(REQ-RSR-009).

**스위트 개수 (실행 확인).**

| 시점 | `pytest tests -q` | `pytest backend/tests -q` |
|---|---|---|
| 기준선 `97831f4` | `1058 passed, 1 skipped, 95 deselected, 1 xpassed` (exit 0) | `4 failed, 353 passed, 1 warning, 58 errors` |
| 2단계 직후(DDL 수정 전) | `22 failed, 1048 passed, …` | `38 failed, 319 passed, 1 warning, 58 errors` |
| 최종 `15ba7b6` | `1070 passed, 1 skipped, 95 deselected, 1 xpassed` (exit 0, +12 = M4 신규) | `4 failed, 353 passed, 1 warning, 58 errors` |

`backend/tests`의 실패·오류 노드 ID 62개는 기준선과 최종이 `diff` 결과 동일(`IDENTICAL`, `b.ids`/`a.ids`). 58 errors는 스위트 순서 오염(`ImportError: cannot import name 'get_sector_registry' from '<unknown module name>'`)이다. 이 오류 4개 파일(`test_bubble_characterization`·`test_bubble_ranking_parity`·`test_bubble_schema_nullable`·`test_stocks_master`)을 단독 실행하면 `97831f4`의 `git archive` 사본(scratchpad)과 최종 트리 모두 `11 failed, 54 passed`이고 실패 ID가 동일하다(`base_iso_4files.log`/`after_iso_4files.log`, `diff` → `IDENTICAL`). 실패 원인은 라이브 데이터 사본 기준 섹터 집합·거래대금 고정값 불일치로, M4 필드와 무관하다.

**린트.** `uvx ruff check --output-format concise <변경 운영 12개 + 신규 테스트 3개>` → `I001` 9건(import 정렬). 같은 명령을 `97831f4` 사본에서 운영 12개에 돌리면 같은 9건(줄 번호만 이동) — 새 린트 0건. 신규 테스트 3개 단독 → `All checks passed!` (`ruff_after.log`).

**커버리지.** `coverage run --include=<변경 서비스·분석 모듈 7개> -m pytest <M4 테스트 3개 + test_meta_service·test_stage_classifier·test_sector_metrics·test_sector_advanced·test_stage_service>` → `102 passed`, `TOTAL 1406 216 85%`(`meta_service.py` 91%, `stage_classifier.py` 100%, `sector_metrics.py` 90%). 변경 줄만 따로: `git diff -U0` 추가 줄 ∩ 미실행 줄 = 7개 파일 모두 `미실행 0` (`changed_cov.log`).

**리허설(라이브 아님).** 워크트리 `Output/` 사본(주 원본에서 읽기 전용 복사)을 다시 `.moai/state/verify/c1bf371e/m4/rehearsal/daily_copy.db`로 복사해 `rebuild_stock_meta()`를 실행 → exit 0. 검증(`rehearsal/check.log`): 컬럼 28개, 마지막 `(27, 'rs_1m')`; 최신 주차 `2026-10-16`, 행 2527개, `rs_1m` 비NULL 2387개; 주간 `RS_1M_Rating`과 불일치 0건, `rs_12m`과 `RS_12M_Rating` 불일치 0건; 재구축 전 사본과 비교한 22개 컬럼에서 다른 칸 52개는 전부 `market`(예: `KOSDAQ` → `KOSDAQ GLOBAL`) — 워크트리 등록부(`Input/sectormap-original.xlsx`)와 주 체크아웃 등록부의 차이이며 위치 시프트는 0. 워크트리에는 `Input/basic_data.xlsx`가 없어 시가총액은 NULL로 들어갔다(라이브에서는 원본 파일을 읽는다).

**코드베이스 주장과 프로브 (lessons #10).**
- 라이브 `stock_meta`는 아직 `rs_1m`이 없다: 주 체크아웃 일봉 DB를 `mode=ro&immutable=1`로 열어 `PRAGMA table_info(stock_meta)` → `27 ['ma200_w', 'last_updated', 'sma150', 'low52w', 'sma200_20d_ago', 'sma5']`, `count(*), max(last_updated)` → `(2533, '2026-10-16T23:15:38.190921')`.
- 라이브 재구축이 쓰는 파일은 `backend.deps.DAILY_DB_PATH = f"{DEFAULT_DB_DAILY}.db"`이고 `DEFAULT_DB_DAILY = str(OUTPUT_DIR / "stock_data_daily")`, `OUTPUT_DIR = Path(__file__).parent.parent / "Output"`(`my_chart/config.py:36`) — 즉 import된 `my_chart` 패키지 기준 `Output/`이다.
- 스크립트 파일을 `python <경로>`로 실행하면 `sys.path[0]`이 스크립트 디렉터리가 되어 다른 `my_chart`(`/Users/byunjungwon/Dev/my_chart`, import 시 KRX 로그인 시도)가 잡힌다 — 리허설 검증 첫 시도에서 `ModuleNotFoundError: No module named 'my_chart.analysis.weekly_grid'`로 관측. `-c`로 실행하면 cwd가 먼저 잡혀 이 저장소 패키지가 쓰인다(`print(my_chart.__file__)` 확인).
- `screen_stage2_entry()` 반환 dict에 `rs_1m` 키가 늘었다. 이를 소비하는 `scripts/rs_eval/stage2_ratio_eval.py`의 도구 테스트 6건은 최종 스위트에서 통과했다.

**미검증 (Gaps).**
- AC-RSR-007 라이브 단계(재구축 후 라이브 두 DB 대조)는 이번 실행 범위 밖이다.
- 프론트 타입·화면(M5)과 dev 서버 재시작 후 응답 확인은 하지 않았다. 새 필드는 모두 선택 필드라 기존 프론트 타입은 그대로 컴파일된다고 보지만, `tsc`는 돌리지 않았다.
- `backend/tests`의 기존 실패(4 failed / 58 errors, 단독 실행 시 11 failed)는 원인을 고치지 않았다.
- `/sectors/bubble`(섹터 버블)·트리맵 경로는 `_get_rs_on_date` 반환형 변경 후 기존 테스트로만 확인했고 새 단언은 없다(두 경로는 `rs_1m`을 쓰지 않음).

**잔여 위험.**
- 라이브 재구축은 `stock_meta` 전체를 `DELETE` 후 다시 넣는다. 서버가 같은 파일을 읽는 중이면 짧은 쓰기 잠금 경합이 생길 수 있다.
- 재구축은 `rs_1m`만이 아니라 `rs_12m`(M2 새 산식 값), `market_cap`, 등록부 기반 `market`·섹터, `last_updated`도 함께 갱신한다 — 일봉 화면의 `rs_12m` 기반 값(스크리닝 T8 등)이 이 시점에 새 산식으로 바뀐다.

### M4 (live stock_meta rebuild, orchestrator-run, 2026-10-20)

- 사용자 확인 후 실행(§F.1). 백업 `Output/stock_data_daily.db.bak_20261020_m4` — 원본과 크기 509251584, sha256 앞 16자리 `7182aa1a394ff69c`, `quick_check` ok, `stock_meta` 2533행 동일 확인 (`.moai/state/verify/c1bf371e/m4_backup.log`)
- 명령: 코드 cwd에서 `…/.venv/bin/python -W ignore -c "…assert my_chart.__file__/meta_service.__file__/_RS_META_COLS==('rs_1m',)/DAILY_DB_PATH/WEEKLY_DB_PATH…; m.rebuild_stock_meta(d.DAILY_DB_PATH, d.WEEKLY_DB_PATH)"` → `done`, `exit=0`, 종료 19:18:32 (`m4_rebuild.log`)
- **AC-RSR-007 라이브 단계 PASS** (두 DB immutable 읽기, ATTACH 없음, `m4_live_ac007.log`): 최신 주차 2026-10-16, 주간 등급 종목 2387 / `stock_meta` 2533행·28컬럼·마지막 컬럼 `rs_1m`, 이름 일치 2387, `rs_1m` 불일치 **0**, `rs_12m` 불일치 **0**(M2 새 산식 반영), 이번 주 미등급 146종목은 `rs_1m` NULL(비NULL 0)
- 이 시점부터 일봉 `stock_meta.rs_12m`도 IBD식 값

### M5 — 프론트 표시 (manager-develop, cycle_type=tdd, 2026-10-20)

**범위.** 열기 배지(REQ-RSR-015·016·022)와 섹터 순위 테이블 `rs_med` 열(REQ-RSR-017). 서버 재시작·라이브 화면 확인은 하지 않았다(오케스트레이터 몫). 작업 위치는 L1 워크트리 `.claude/worktrees/agent-af84ec440e38a9e6c`(브랜치 `worktree-agent-af84ec440e38a9e6c`), 시작 시 `git merge --ff-only main` → `git rev-parse --short HEAD` = `1516c25`. 증거 파일은 전부 `.moai/state/verify/rsr-m5/`에 있다. 프론트 명령은 모두 `npm --prefix frontend exec vitest -- run --root frontend …` 형태(저장소 루트에서 `--root` 없이 돌리면 `.claude/worktrees` 테스트가 섞인다).

**커밋.** `b7ff135` — `git commit` 출력 `17 files changed, 415 insertions(+), 10 deletions(-)`. pre-commit 게이트(`moai gate`, Python pytest만 실행)는 첫 시험 실행에서 `ModuleNotFoundError: No module named 'pkg_resources'`로 실패(`gate1.txt`: `1 failed, 1069 passed` — 새 워크트리 `.venv`의 setuptools 82.0.1 문제, M4와 같은 환경 원인). `uv pip install --python .venv/bin/python "setuptools<81"`(→ `80.10.2`) 후 커밋 시 게이트 통과로 커밋이 생성됐다. 게이트용 `Output/stock_data_{weekly,daily}.db`는 주 체크아웃에서 워크트리로 복사(원본 읽기만).

**설계 결정 1건.** 술어 `isRsHeat(rs1m, threshold)`는 임계값을 인자로 받고, 두 호출부가 `RS_TOP_THRESHOLD`를 넘긴다. 술어가 `rsMetrics.ts` 내부 바인딩의 상수를 직접 읽으면 AC-RSR-011이 지정한 `vi.mock('../../utils/rsMetrics')` 상수 주입(85)이 술어에 닿지 않아(ESM 모듈 내부 참조는 목 교체 대상이 아님), "리터럴 80" 대조를 구현과 구분할 수 없다. 대조 C2a·C2b로 두 위치의 리터럴 모두 RED가 됨을 확인했다.

**RED (구현 전, `1516c25` 트리 + 신규 테스트 5파일만).** `vitest run --root frontend <신규 5파일>` → `Test Files 5 failed (5)`, `Tests 12 failed | 1 passed (13)` (`red.txt`). 통과 1건은 `RS_TOP_THRESHOLD === 80` 유지 단언(REQ-RSR-022, 현행 그대로가 정답). 실패 원문 발췌:
- `TypeError: isRsHeat is not a function` ×2, `TypeError: rsHeatTitle is not a function`
- StockTable `AssertionError: expected null not to be null`, `expected '' to contain '80'`
- 버블 `expected '<b>종목B</b><br/>산업명(중): 반도체<br/>주요제품: …' to contain 'rs-heat-badge'`
- 주입 테스트 `expected null not to be null`, `expected '<b>종목E</b>…' to contain 'rs-heat-badge'`
- 섹터 `AssertionError: expected 'RS 80+ 비중' to be 'RS Med'`, `TypeError: Cannot read properties of undefined (reading 'textContent')` ×2

**AC 판정 (GREEN, 구현 트리).** `vitest run --root frontend src/utils/__tests__/rsHeat.test.ts src/utils/__tests__/rsHeat.injected.test.tsx src/utils/__tests__/rsMetrics.test.ts src/components/StockExplorer/__tests__/StockTable.rsHeat.test.tsx src/components/SectorAnalysis/__tests__/StockBubbleChart.rsHeat.test.tsx src/components/SectorAnalysis/__tests__/SectorRankingTable.rsMed.test.tsx` → `Test Files 6 passed (6)`, `Tests 18 passed (18)` (`restored.txt`, 대조 원복 후 재실행).

| AC | Status | 테스트 | 양변 출처 |
|---|---|---|---|
| AC-RSR-011 (종목 테이블) | PASS | `StockTable.rsHeat.test.tsx` 2건 | `StockTable` 렌더 DOM의 `[data-testid="rs-heat-badge"]` 유무 vs 리터럴 사례(`79.99`·`80`·`80.01`·`null` → 없음·있음·있음·없음), title ⊇ `String(RS_TOP_THRESHOLD)` |
| AC-RSR-011 (버블 툴팁) | PASS | `StockBubbleChart.rsHeat.test.tsx` 2건 | `echarts-for-react` 목으로 붙잡은 `option.tooltip.formatter` 반환 HTML vs 같은 4사례, `class="rs-heat-badge"` 요소의 title ⊇ 상수 문자열 |
| AC-RSR-011 (상수 유래) | PASS | `rsHeat.injected.test.tsx` 2건 | `vi.mock('../rsMetrics')`로 `RS_TOP_THRESHOLD`=85 주입 → 두 화면 모두 `80.01` 배지 없음, `85` 배지 있음 + title ⊇ `85` |
| AC-RSR-011 (교차 언어 등식) | PASS | `rsMetrics.test.ts` 기존 단언(변경 없음) | `sector_metrics.py` 원문에서 추출한 `_RS_TOP_THRESHOLD` vs `RS_TOP_THRESHOLD` 수치 등식 |
| AC-RSR-012 | PASS | `SectorRankingTable.rsMed.test.tsx` 3건 | 헤더 라벨 순서 `RS Avg`→`RS Med`→`RS 80+ 비중`(인접), P 행 `30`·Q 행 `50`(둘 다 `rs_avg` 50), `rs_med: null` → `0`도 빈칸도 아님 |
| REQ-RSR-022 | PASS | `rsHeat.test.ts` 첫 단언 | `RS_TOP_THRESHOLD` === `80` (RED 단계에서도 통과 — 값 미변경의 증거) |

**대조 (lessons #9).** 운영 파일 사본을 세션 스크래치에 떠 두고 `sed`로 주입 → 대상 테스트 실행 → 사본으로 원복 → `cmp`로 바이트 동일 확인(`restored-identical` 출력) → 위 AC 명령 재실행 `18 passed`. 원문은 `contrast-*.txt`.

| # | 주입 | 관측 RED(원문) |
|---|---|---|
| C1 | 술어 `>=` → `>` | `rsHeat.test` `expected false to be true`, StockTable `expected null not to be null`, 버블 `… to contain 'rs-heat-badge'` → `Tests 5 failed \| 3 passed (8)` |
| C2a | 술어가 인자 무시하고 리터럴 `rs1m >= 80` | 주입(85) 테스트 StockTable `expected <span class="rs-heat-badge" …(2)></span> to be null`, 버블 `expected '<b>종목C</b>…' not to contain 'rs-heat-badge'` → `Tests 2 failed (2)` |
| C2b | 호출부 두 곳이 `isRsHeat(…, 80)` 리터럴 | C2a와 같은 두 실패 → `Tests 2 failed (2)` |
| C3 | 결측을 높은 값으로 `(rs1m ?? 100) >= threshold` | `rsHeat.test` `expected true to be false`, 버블 `expected '<b>종목D</b>…' not to contain 'rs-heat-badge'`, StockTable `expected <span …> to be null` → `Tests 3 failed \| 5 passed (8)` |
| C3b | 결측을 0으로 `(rs1m ?? 0) >= threshold` | **RED 아님** — `Tests 8 passed (8)`. acceptance.md AC-RSR-011이 명시한 대로 결과가 정상 동작과 같아 오구현으로 보지 않는다(0 < 80) |
| C4 | 중앙값 셀이 `sector.rs_avg`를 읽음 | `expected '50' to be '30'` → `Tests 1 failed \| 2 passed (3)` |
| C5 | 중앙값 결측을 0으로 `sector.rs_med ?? 0` | `expected '0' not to be '0'` → `Tests 1 failed \| 2 passed (3)` |
| (열 누락) | 구현 전 트리 = 열 없음 | RED 단계 `expected 'RS 80+ 비중' to be 'RS Med'` |

**기존 테스트 단언 3곳 갱신 (열 추가의 기계적 결과).** RS Med 열이 `RS Avg`와 `RS 80+ 비중` 사이에 들어가 위치·개수를 단언하던 기존 테스트가 깨졌다. 변경 전 관측(`after-vitest.txt` 1차 실행, 갱신 전): `er2-screens.test.tsx` `AssertionError: expected 8 to be 7`, `SectorRankingTable.m4.test.tsx` `Found multiple elements with the text: –`(픽스처에 `rs_med`가 없어 결측 `–` 셀이 순위변동 `–`와 겹침)·`expected 5 to be 4`(ⓔ 배지 수).
- `er2-screens.test.tsx`: 결측 픽스처에 `rs_med: null` 명시, 결측 셀 수 7 → 8. **plan.md §G 10번은 이 파일을 "변경 없음"으로 분류했다** — §G는 `rs_12m` 등 문자열 신호로 기계적으로 판정했고(§G 본문 "판정은 이 신호에서 기계적으로 정했으며"), 이 파일이 `SectorRankingTable`의 결측 셀 전수를 센다는 점은 신호에 잡히지 않았다. 단언의 의도(결측은 `–`, 실제 0은 `0.0%`, 둘이 섞이지 않음)는 그대로다.
- `SectorRankingTable.m4.test.tsx`(§G 목록 밖): `makeSector` 기본값에 `rs_med: 50`, ⓔ 4 → 5(RS Med는 구성 종목 중앙값 = 등가중 계열).
- `SectorRankingTable.test.tsx`(§G 목록 밖): 색 채널 분리 단언의 비중 셀 인덱스 6 → 7. 이 파일은 갱신 전에도 통과했지만, 인덱스 6이 RS Med 결측 셀(`transparent`)을 가리켜 "등급 색 ≠ 비중 색" 단언이 공허해진 상태였다.

**전체 스위트 (§G "변경 없음" 프론트 테스트 포함).**
- 변경 전 기준선(`1516c25`, 신규 파일 없음): `vitest run --root frontend` → `Test Files 1 failed | 90 passed (91)`, `Tests 819 passed (819)`, exit 1 (`baseline-vitest.txt`). 실패 파일 1개는 `e2e/preset-flow.spec.ts` — `Playwright Test did not expect test.describe() to be called here.`(Playwright 스펙이 vitest에 수집되는 기존 문제, M5 무관)
- 변경 후: 같은 명령 → `Test Files 1 failed | 95 passed (96)`, `Tests 832 passed (832)`, exit 1 (`after-vitest.txt`). 실패 파일은 같은 `e2e/preset-flow.spec.ts` 하나. 증가분 +5파일·+13테스트 = 신규 테스트 5파일의 13건

**타입 검사·린트.**
- `npm --prefix frontend run typecheck`(`tsc -b`) → 변경 전 `exit=0`(`baseline-tsc.txt`), 변경 후 `exit=0`(`after-tsc.txt`)
- `npm --prefix frontend run lint`(`eslint .`) → 변경 전 `✖ 47 problems (45 errors, 2 warnings)`, exit 1 / 변경 후 `✖ 47 problems (45 errors, 2 warnings)`, exit 1. 행 번호를 지운 두 출력의 `diff`는 `SectorAnalysis.tsx`의 기존 `react-hooks/set-state-in-effect` 오류가 151 → 153행으로 밀린 것뿐(이번에 `getSortValue`에 2줄 추가). 새 린트 문제 0건

**범위 밖 파일 2개 (L46 귀속).** plan.md §D 목록에 없는 파일을 REQ-RSR-015·017의 직접 결과로 수정했다.
- `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx`: `getSortValue`에 `case 'rs_med'` 2줄. 없으면 RS Med 헤더 클릭이 `default`(composite)로 조용히 정렬된다
- `frontend/src/styles/global.css`: `.rs-heat-badge` 1규칙(`stage-badge`와 같은 기하, 주황 채널 — S3 호박색·S2 적색과 구분)

**미검증(Gaps).** 라이브 dev 서버 화면 확인 미실행(오케스트레이터 몫). 툴팁 배지의 title은 ECharts 툴팁이 기본적으로 마우스 진입을 받지 않아(`enterable: false`) 화면에서 호버로 읽히지 않을 수 있다 — 표시 문구 `열기`는 보인다. 커버리지 수치 미측정.

### M5 (live dev-server check, orchestrator-run, 2026-10-20)

- main `6a68ba8`로 빨리감기 후 백엔드(:8000, venv `/Users/byunjungwon/Dev/my_chart/.venv`, cwd 코드 루트)·vite(:5173) 재시작. 첫 백엔드 재시작은 이전 vite 실행 스크립트의 "Stopping all servers..."에 함께 종료되어(SIGTERM, `.dev-server.log`) 한 번 더 시작함
- 오케스트레이터 재검증: vitest 전체 `832 passed`, 파일 `95 passed | 1 failed`(사전 존재 `e2e/preset-flow.spec.ts` Playwright 수집 문제), `npm --prefix frontend run typecheck` exit 0 (`m5_vitest_full.log`, `m5_tsc.log`)
- API(`m5_api_check.log`): `/api/stage/overview` `all_stocks` 2515 중 `rs_1m` 비NULL 2387, `rs_1m>=80` 478 / `/api/sectors/ranking` `sectors` 29개 모두 `rs_med` 존재, 봉투 `data[0].rs_med` = `{"value":47.03,"reason":null}`, 중앙값<평균 섹터 14 / `/api/sectors/방송미디어/bubble` `rs_1m` 57종목
- 화면(headless Playwright, scratchpad 스크린샷): Stock Explorer `.rs-heat-badge` **478개** 렌더(API 478과 일치), 텍스트 `열기`, title `최근 1개월 RS 80 이상 — 단기 강세(열기)` — AC-RSR-011 라이브 / Sector Analysis → Table 헤더 `… RS Avgⓔ, RS Medⓔ, RS 80+ 비중ⓔ …`, 첫 행 [섹터, RS Avg, RS Med] = PCB 62/74, 방송미디어 28/16, 패션 45/43, 배터리 53/60, 음식료 40/41 — AC-RSR-012 라이브
- 미확인: 버블 툴팁 배지의 실제 호버 표시(단위 테스트로만 검증)
- 계획 밖 변경(M5 에이전트 보고, sync에서 SPEC 반영 대상): `er2-screens.test.tsx` 결측 셀 7→8, `SectorRankingTable.m4/.test.tsx` 픽스처·인덱스, `SectorAnalysis.tsx` `rs_med` 정렬 case, `global.css` 배지 규칙 1개

### M6 — 회귀 실측 기록과 문서 (manager-develop, 2026-10-20)

**작업 위치.** L1 워크트리 `.claude/worktrees/agent-a6de872dcbdaa9ca3`(브랜치 `worktree-agent-a6de872dcbdaa9ca3`). 기준점 `fd5f11f`에서 `git merge --ff-only main`으로 빨리 감은 뒤 `git rev-parse --short HEAD` → `c2fe4ac`(= `main`). `git diff --stat main -- scripts/rs_eval/stock_rs_eval.py` → 출력 없음(측정 스크립트는 M2 `366206a`판 그대로). 운영 코드 변경 없음, 라이브 DB 쓰기 없음, 서버 재시작 없음. 증거 파일은 전부 워크트리 `.moai/state/verify/c1bf371e/m6/`에 있다.

**사본 무결성.** 측정 전후 `shasum -a 256 …/Output/snapshots/weekly_{before,after}_rsr.db`를 `sha_pre.txt`·`sha_post.txt`에 남기고 `diff` → `SHA_IDENTICAL`. 값은 before `949f29639a86da86…`, after `abecc43e98dc47b0…`로 M2·M3 기록과 같다. 측정 뒤 `ls Output/snapshots/` → `weekly_after_rsr.db`, `weekly_before_rsr.db` 두 파일뿐(`-wal`/`-shm` 없음).

**REQ-RSR-020 / AC-RSR-014 재측정 (원문).** 두 명령 모두 워크트리 cwd, `S=/Users/byunjungwon/Dev/my-project-01/my_chart/Output/snapshots`.

```
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db $S/weekly_before_rsr.db
registry 중복 Code 감지 — 첫 행 유지, 이 행 drop: Code=052770 종목명=아이톡시

=== 필터: 20주 평균 주간거래대금 >= 50억 | 향후 4주 ===
                      주수  상위10_초과pp  상하위스프레드pp  상위10_vs평균pp  지연진입_vs평균pp  IC양수비율  상위10_지속률
공식                                                                                        
프로덕션(RS_12M_Rating)  295       1.62      -0.47        -0.55        -0.58   32.88     29.24
exit=0
```

```
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I scripts/rs_eval/stock_rs_eval.py 4 --production --db $S/weekly_after_rsr.db
registry 중복 Code 감지 — 첫 행 유지, 이 행 drop: Code=052770 종목명=아이톡시

=== 필터: 20주 평균 주간거래대금 >= 50억 | 향후 4주 ===
                      주수  상위10_초과pp  상하위스프레드pp  상위10_vs평균pp  지연진입_vs평균pp  IC양수비율  상위10_지속률
공식                                                                                        
프로덕션(RS_12M_Rating)  295       1.66      -0.25        -0.52        -0.55   30.85     65.17
exit=0
```

증거: `eval_before.log`, `eval_after.log`.

**before/after 표 (REQ-RSR-020).** 열 이름은 스크립트 출력 그대로다. 열의 뜻(`stock_rs_eval.py` `evaluate()` 본문): `상위10_초과pp` = 상위 10% 향후 4주 수익 평균 − 그날 중앙값, `상하위스프레드pp` = 상위 10% − 하위 10%, `상위10_vs평균pp` = 상위 10% − 그날 평균, `지연진입_vs평균pp` = 1주 늦게 진입했을 때의 같은 차이, `IC양수비율` = 점수와 향후 4주 수익의 스피어만 상관이 양수인 주의 비율, `상위10_지속률` = 4주 전 상위 10% 중 지금도 상위 10%인 비율.

| 사본 | 주수 | 상위10_초과pp | 상하위스프레드pp | 상위10_vs평균pp | 지연진입_vs평균pp | IC양수비율 | 상위10_지속률 |
|---|---|---|---|---|---|---|---|
| 변경 전 `weekly_before_rsr.db` (예전 산식) | 295 | 1.62 | −0.47 | −0.55 | −0.58 | 32.88 | **29.24** |
| 변경 후 `weekly_after_rsr.db` (IBD식) | 295 | 1.66 | −0.25 | −0.52 | −0.55 | 30.85 | **65.17** |
| 차이 (후 − 전) | 0 | +0.04 | +0.22 | +0.03 | +0.03 | −2.03 | **+35.93** |

판정: 변경 후 `상위10_지속률` 65.17 ≥ 60 → AC-RSR-014 목표 충족. 변경 전 29.24는 60 미만(대조 관측)이고 계획서 31%의 ±3%p(28~34) 안이다.

**초과수익 재측정 (plan.md §F M6).** 계획서 §2의 "상위 10% 종목의 향후 4주 수익 − 유니버스 평균은 모든 창에서 0 이하" 주장을 프로덕션 등급으로 다시 쟀다. `상위10_vs평균pp`는 −0.55 → −0.52, `지연진입_vs평균pp`는 −0.58 → −0.55로 변경 후에도 0 이하다. 같은 열의 원시 산식 모드 값(`scripts/rs_eval/rs_final_h4.out`): `현행(1M 33%가중)` −0.60·−0.59, `IBD식(최근분기 40%)` −0.58·−0.62. 해석: 이번 변경은 수익 예측력을 바꾸지 않았고(초과수익 차이 +0.03~+0.04pp, IC양수비율 −2.03%p), 명단 안정성(지속률 +35.93%p)만 크게 올렸다. 계획서 §2의 "종목 RS는 필터" 해석과 같은 방향이다. 이 해석은 단일 구간(2022~2026)·겹치는 4주 수익 표본이라는 spec.md §1.2의 한계를 그대로 진다.

**§E.2 기존 수치와의 대조.** 겹치는 값은 모두 같다.
- 변경 전 7개 열: `### M2 (pre-regeneration)` 기준선 블록(`295 1.62 -0.47 -0.55 -0.58 32.88 29.24`)과 한 자리도 다르지 않다.
- 변경 후: `### M2 (live regeneration)`의 AC-RSR-014 줄(주수 295, 상위10_초과pp 1.66, 상하위스프레드pp −0.25, IC양수비율 30.85, 지속률 65.17)과 같다.
- 새로 기록하는 값: 변경 후 `상위10_vs평균pp` −0.52와 `지연진입_vs평균pp` −0.55. M2 라이브 기록에는 이 두 열이 없었다.
- 불일치: 없음.

**문서 갱신 — `docs/rs-timeline-eli5.html`.**
- **추적 상태(프로브):** `git check-ignore -v docs/rs-timeline-eli5.html docs/rs-rebalance-plan-brief.md` → 두 파일 모두 `.gitignore:251:docs/`. `git log --all --oneline -- docs/rs-timeline-eli5.html` → 출력 없음. 두 파일은 공용 체크아웃 `/Users/byunjungwon/Dev/my-project-01/my_chart/docs/`에만 있고 이 워크트리에는 없다. 그래서 공용 체크아웃의 그 파일을 직접 고쳤다. **커밋 대상이 아니다.**
- **백업:** 수정 전 사본을 세션 스크래치패드 `rs-timeline-eli5.before-m6.html`에 두었다. sha256 `4f448b98…5c`는 원본과 같다. 수정 후 sha256은 `2a2eae9d…6a00`, 326줄 → 368줄.
- **편집 방식:** `m6_edit_html.py`가 앵커 문자열마다 정확히 1회 일치를 단언하고 치환했다(`applied 34 edits`). 이어 `m6_edit_table.py`가 12번 카드의 비교 블록을 HTML 표로 바꿨다. 한글이 섞인 고정폭 블록은 열이 어긋났기 때문이다(렌더 확인에서 관측).
- **구조 확인:** 파이썬 `html.parser` 태그 짝 검사 → `unclosed []`, `mismatch []`. `<section` 12개, `</section>` 12개.
- **렌더 확인:** 헤드리스 Chromium(`shot.mjs`) → `cards 12`, 가로 넘침 블록 `[]`. 스크린샷은 `card5/8/10/11/12.png`.

| 카드 | 편집 | 숫자 출처 |
|---|---|---|
| 머리말 | eyebrow에 "같은 날 반영", 리드에 12번 안내 한 문장 | — |
| 1 | 제목 2,490명 → 2,387명, 정리 전 2,490명 주석 | `### M2 (live regeneration)` "최신 주차 등급 종목: 2490 → 2387" |
| 2·3·4·6·9 | "현행/지금" → "예전/바꾸기 전"(본문·SVG 라벨·aria-label). 4번 범위 "−0.1 ~ −1.1%p" → "공식 12개 모두 −0.04 ~ −1.40%p"로 정정, 원시 재계산 값이라는 주석 추가 | `rs_final_h4.out` `상위10_vs평균pp` 열: 최대 −0.04(12-1 모멘텀), 최소 −1.40(3M 단독). 기존 "−1.1"은 3M 단독(−1.40)을 빠뜨린 값이었다 |
| 5 | "권고 A/B" → "채택한 공식(IBD식)". 비율식 유도식, `S = 0.4·Q1 + 0.2·Q2 + 0.2·Q3 + 0.2·Q4`, 나누기 예시, 버린 안 A(57%)·B(75%)와 B의 기각 사유. 임계값 재측정 결과(70·60 유지, 80 대상 아님) | spec.md §2.3(유도식·예시 `RS_3M = 1.0`, `RS_6M = 1.2` → `q2 = 0.10`, 차분식 0.20), §2.2 Q1(기각 사유), `rs_final_h4.out`(57.46·74.78), `### M3` 판정(99.48 → 94.42, 허용 9.948; 33.53 → 33.72), `### M2 (live regeneration)` "80 이상 몫 20.03%" |
| 8 | 식 블록을 "그대로 둠 / 새로 추가 / 이미 있던 열"로 바꾸고, 섹터 테이블의 RS Avg → RS Med → RS 80+ 비중 배치와 반영 당일 관측 문단 추가 | `### M5 (live dev-server check)`: PCB 62/74, 방송미디어 28/16, 섹터 29개, 중앙값<평균 14 |
| 9 | 정리 블록 "열기 배지 (RS_1M_Rating ≥ 80)", 배지 동작 문단(80은 섹터 화면과 같은 상수, 478/2,387, 상장 12개월 미만은 배지 없음) | spec.md Q4·REQ-RSR-015·REQ-RSR-023, `### M5 (live dev-server check)` `rs_1m` 비NULL 2387, 배지 478 |
| 10 | 분모 정의를 실제 필터 다섯 가지(지수, 거래량 0, 우선주 코드 끝자리 ≠ 0·스팩, `1+R ≤ 0`, 결측 행)로 교체하고 ETF/ETN·거래대금 50억 줄 삭제. 우선주·스팩 현재 0개, 50억은 분모 비적용, 옛 행 119,881개 정리 문단 추가 | spec.md REQ-RSR-002·003·007·008·023, §2.4 B-1, §2.2 Q3, `### M2 (live regeneration)` AC-RSR-001 119881 → 0, "거래량 0 101 + 지수 2" |
| 11 | "바꿀 것 넷, 둘 것 하나" → "바꾼 것 넷, 그대로 둔 것 둘". 항목별 반영 결과로 교체, 임계값 항목은 유지(`=`) 표시. 한계 주석에 progress.md 경로 추가 | 위 행들과 같음 |
| 12 (신설) | "바꾼 뒤 다시 쟀다" — 29.24% → 65.17% 막대(목표 60% 선), 7행 비교 표, 수익 지표 불변 해석, 29.24 대 31% 차이 가설(분리 측정 안 함 명시), 측정 조건 | 이 절의 재측정 원문 |

표기 원칙: 페이지의 숫자는 모두 위 출처에서 옮겼고, 새로 만든 숫자는 없다. 문체는 기존 페이지의 합니다체를 유지했고, 카드 구조·CSS 변수·SVG 양식도 기존 것을 그대로 썼다. CSS에는 `.tbl` 규칙 5줄만 더했다.

**미검증 (Gaps).**
- `docs/rs-timeline-eli5.html`은 gitignore 대상이라 커밋되지 않는다. 변경은 공용 체크아웃 작업 트리에만 있고 git 이력으로 되돌릴 수 없다. 되돌릴 때는 스크래치패드 백업을 쓴다. 이 파일을 추적할지는 이 SPEC 범위 밖이며 sync 단계 판단에 맡긴다.
- 렌더 확인은 라이트 테마 데스크톱 폭(900px) 한 가지뿐이다. 다크 테마와 모바일 폭은 보지 않았다.
- M6은 코드를 바꾸지 않아 테스트 스위트를 따로 돌리지 않았다. 커밋 시 pre-commit 게이트가 도는 것이 전부다.
- 12번 카드의 "29.24 대 31%" 차이 원인은 `### M2 (pre-regeneration)`의 가설(결측 3주 + 분모 의존)을 그대로 옮긴 것이며 분리 측정하지 않았다.

**잔여 위험.**
- 측정 스크립트의 `sys.path`(`:6`)가 공용 체크아웃 절대 경로라, 등록부는 공용 체크아웃 코드로 읽힌다(`### M2 (pre-regeneration)` 잔여 위험과 같음). 출력 첫 줄의 등록부 중복 코드 경고(`052770 아이톡시`)는 두 사본 측정에 똑같이 나온다.

## §E.3 Run-phase Audit-Ready Signal

**마일스톤 커밋 (프로브).** `git log --oneline -20`(`c2fe4ac` 트리) 출력에서 SPEC 커밋만 옮겼다(원문 순서는 최신이 위).

| 마일스톤 | 커밋 (오래된 순) | `git log --oneline` 제목 |
|---|---|---|
| M1 | `f3b7066` `cec038b` `f07b520` | `test(…): M1 특성화 — 변경 전 generate_rs_db() RS_6M/3M/1M 골든값 캡처` / `feat(…): M1 RS 순위 분모 정리와 낡은 행 제거` / `docs(…): M1 run-phase 증거 기록 (progress.md §E.2)` |
| M2 | `366206a` `42a405d` `305cdcb` | `feat(…): M2 RS_12M_Rating IBD식 재가중 + 회귀 계측 프로덕션 모드` / `docs(…): M2 재생성 전 증거 기록 (progress.md §E.2)` / `docs(…): M2 라이브 재생성 결과 기록` |
| M3 | `6b09f06` `97831f4` | `feat(…): M3 Stage 2 임계값 재보정 측정 도구와 단일 정의 지점` / `docs(…): M3 재보정 측정·판정 기록` |
| M4 | `15ba7b6` `73b02e8` `1516c25` | `feat(…): M4 백엔드 필드 — stock_meta.rs_1m·종목 rs_1m·섹터 rs_med` / `docs(…): M4 백엔드 필드 증거 기록 (라이브 재구축 전)` / `docs(…): M4 라이브 stock_meta 재구축 결과 기록` |
| M5 | `b7ff135` `6a68ba8` `c2fe4ac` | `feat(frontend): 열기 배지와 섹터 RS 중앙값 열 표시 (SPEC-RS-REBALANCE-001 M5)` / `docs(…): M5 프론트 표시 실행 증거 기록` / `docs(…): M5 라이브 화면 확인 기록` |
| M6 | `7a77769` | `docs(…): M6 회귀 실측 기록과 run-phase 완료 신호(§E.3)` — SHA는 sync 단계에서 채움 |

**AC 최종 상태.** PASS = 픽스처·단위 테스트 단계 통과. PASS-live = 그에 더해 라이브 DB·API·화면 단계도 관측함. Gap = 관측하지 못한 부분.

| AC | 최종 | 근거 (§E.2 위치) |
|---|---|---|
| AC-RSR-001 | PASS-live | `### M1` AC 표(`test_ac_rsr_001_*` ×2) + 대조 C10·C11; `### M2 (live regeneration)` 짝 없는 행 119881 → 0 |
| AC-RSR-002 | PASS-live | `### M1` AC 표 + 대조 C1·C2·C3; `### M2 (live regeneration)` 지수 행 692 → 0, 거래량 0 짝 행 16369 → 0 |
| AC-RSR-003 | PASS | `### M1` AC 표(`test_ac_rsr_003_*` ×2) + 대조 C4·C5·C6 |
| AC-RSR-004 | PASS | `### M1` AC 표 + 대조 C7 |
| AC-RSR-005 | PASS | `### M2 (pre-regeneration)` GREEN 표 + 대조 K1~K4 |
| AC-RSR-006 | PASS | `### M1` 특성화 골든(단독 커밋 `f3b7066`); `### M2 (pre-regeneration)` GREEN 표 + 대조 K5~K7 |
| AC-RSR-007 | PASS-live | `### M4 (pre-rebuild)` AC 표 + 대조 C4·C5·C10; `### M4 (live stock_meta rebuild)` `rs_1m` 불일치 0, `rs_12m` 불일치 0 |
| AC-RSR-008 | PASS | `### M4 (pre-rebuild)` AC 표(레거시 27컬럼 → 끝에 `rs_1m`, 멱등) + 대조 C3 |
| AC-RSR-008b | PASS | `### M4 (pre-rebuild)` AC 표 + 대조 C1·C2; 라이브 `stock_meta` 28컬럼·마지막 `rs_1m`(`### M4 (live stock_meta rebuild)`) |
| AC-RSR-009 | PASS | `### M4 (pre-rebuild)` AC 표 + 대조 C6a·C6b·C7. 보강 관측: `### M5 (live dev-server check)` `/api/stage/overview` `rs_1m` 비NULL 2387, `/api/sectors/방송미디어/bubble` `rs_1m` 57종목 |
| AC-RSR-010 | PASS | `### M4 (pre-rebuild)` AC 표(7건) + 대조 C8·C9. 보강 관측: `### M5 (live dev-server check)` 섹터 29개 모두 `rs_med`, 봉투 `data[0].rs_med` 존재 |
| AC-RSR-011 | PASS-live (종목 테이블) / Gap (버블 툴팁 라이브) | `### M5` AC 표 + 대조 C1·C2a·C2b·C3; `### M5 (live dev-server check)` 배지 478개 = API 478. 버블 툴팁 배지의 실제 호버 표시는 라이브로 확인하지 않았다(단위 테스트만) |
| AC-RSR-012 | PASS-live | `### M5` AC 표 + 대조 C4·C5; `### M5 (live dev-server check)` 헤더 `RS Avg → RS Med → RS 80+ 비중`, PCB 62/74 등 |
| AC-RSR-013 | PASS | `### M3` GREEN 표(스캔 0줄, 교차 언어 74 passed, T8 2 passed) + 대조 A1~A6·B1~B5 |
| AC-RSR-014 | PASS-live | `### M2 (pre-regeneration)` 도구·기계적 독립성(`grep -cE` → 0)·기준선 29.24 + 대조 K9; `### M2 (live regeneration)` 65.17; `### M6` 재측정 29.24 / 65.17 일치 |
| AC-RSR-015 | PASS-live | `### M3` 두 사본 8회 측정: (a) 변경 후 사본 사전 조건 충족 → 70 유지(5.06 ≤ 9.948), 대조 80은 14.61 > 9.948; (b) 33.53 → 33.72, 60 유지 |
| AC-RSR-016 | PASS | `### M2 (pre-regeneration)` GREEN 표(상수 고정 + 기존 7개 파일 140 passed) + 대조 K8 |
| AC-RSR-017 | PASS-live | `### M1` AC 표 + 대조 C12; `### M2 (live regeneration)` 비기준 날짜 행 5 → 0 |
| AC-RSR-018 | PASS | `### M1` AC 표 + 대조 C8·C9 |

집계: AC 19개(001~018 + 008b) 중 FAIL 0. PASS-live 8개(001·002·007·011·012·014·015·017; 011은 종목 테이블만 라이브, 버블 툴팁은 Gap 병기), PASS 11개(003·004·005·006·008·008b·009·010·013·016·018).

**sync로 넘길 이탈 사항.**
1. **M1 기준 종목 부재 가드** — REQ-RSR-001 문구에 없는 안전장치다. 기준 종목 행이 0개면 아무것도 지우지 않고 경고만 남긴다. 근거: `### M1` 잔여 위험. SPEC 본문 반영 여부는 manager-spec 판단 대상이다.
2. **스팩 판별 범위** — `스팩` 판별을 등록부가 아니라 그날 가격 행의 종목명에 적용한다(등록부 기준의 상위 집합). 근거: `### M1` 잔여 위험.
3. **M5 계획 밖 변경** — `er2-screens.test.tsx` 결측 셀 7 → 8(plan.md §G 10번은 "변경 없음"으로 분류), `SectorRankingTable.m4.test.tsx`·`SectorRankingTable.test.tsx` 픽스처·인덱스, `SectorAnalysis.tsx` `rs_med` 정렬 case, `global.css` 배지 규칙 1개. 근거: `### M5` "기존 테스트 단언 3곳 갱신"·"범위 밖 파일 2개", `### M5 (live dev-server check)` 마지막 줄.
4. **기존 실패(이 SPEC 원인 아님)**
   - `backend/tests/test_minervini_template.py` 3건: 픽스처에 `sma5` 컬럼이 없음. 근거: `### M3` "§G M3 4개 파일 재실행", `305cdcb`에서도 같은 3건.
   - `backend/tests` 전체 `4 failed … 58 errors`: 기준선 `97831f4`와 최종 `15ba7b6`의 노드 ID 62개가 같음(`IDENTICAL`). 근거: `### M4 (pre-rebuild)` 스위트 개수 표.
   - vitest `e2e/preset-flow.spec.ts` 수집 실패: Playwright 스펙이 vitest에 수집되는 문제. 근거: `### M5` 전체 스위트, `### M5 (live dev-server check)`.
5. **설명 문서는 커밋되지 않음** — `docs/rs-timeline-eli5.html`은 `.gitignore:251:docs/` 대상이라 공용 체크아웃 작업 트리에서만 갱신됐다. 근거: `### M6` 문서 갱신.

**Gaps.**
- AC-RSR-011 버블 툴팁 배지의 라이브 호버 표시(위 표).
- `docs/rs-timeline-eli5.html` 다크 테마·모바일 렌더(`### M6` Gaps).

```yaml
run_complete_at: 2026-10-20
run_commit_sha: 7a77769   # M6 기록 커밋 — sync 단계에서 채움(git log 확인)
run_status: audit-ready
ac_pass_count: 19          # FAIL 0; PASS-live 8 (011은 테이블만 live, 버블 툴팁 Gap 병기) + PASS 11
ac_fail_count: 0
ac_gap_items:
  - "AC-RSR-011: 버블 툴팁 열기 배지 라이브 호버 미확인 (단위 테스트로만 검증)"
milestone_commits:
  M1: [f3b7066, cec038b, f07b520]
  M2: [366206a, 42a405d, 305cdcb]
  M3: [6b09f06, 97831f4]
  M4: [15ba7b6, 73b02e8, 1516c25]
  M5: [b7ff135, 6a68ba8, c2fe4ac]
  M6: [7a77769]
req_rsr_020_persistence: {before: 29.24, after: 65.17, target: ">= 60", source: "### M6 재측정 원문"}
pre_existing_failures:
  - "backend/tests/test_minervini_template.py 3 failed (sma5 픽스처 부재)"
  - "backend/tests 4 failed / 58 errors (기준선과 노드 ID 동일)"
  - "vitest e2e/preset-flow.spec.ts 수집 실패"
known_deviations_for_sync: 5   # 위 '이탈 사항' 1~5
new_warnings_or_lints_introduced: 0   # M1~M5 각 절의 린트 비교; M6은 코드 변경 없음
spec_status_unchanged: in-progress    # sync가 이후 전이를 소유
```

## §E.4 Sync-phase Audit-Ready Signal

**범위.** 사용자 승인 gate-sync-2 — 문서만 다루고 코드는 바꾸지 않는다. 공용 체크아웃 `main`(시작 HEAD `7a77769`)에서 진행했다. SPEC 본문의 as-implemented 반영(spec v0.4.0, §7 알려진 부채, plan.md §B·§D·§G.1, acceptance.md AC-RSR-001 비고·AC-RSR-006 건수)은 manager-spec이 했고, 이 절은 manager-docs가 썼다. 두 쪽 변경은 sync 커밋 하나에 함께 들어간다.

**sync 품질 게이트 (오케스트레이터 실행, 증거 `.moai/state/verify/c1bf371e/`).**

| 항목 | 명령 결과 (로그 끝줄 원문) | 판정 | 증거 |
|---|---|---|---|
| 루트 `tests/` | `1070 passed, 1 skipped, 95 deselected, 1 xpassed in 66.51s` | PASS | `sync_tests.log` |
| `backend/tests` | `4 failed, 353 passed, 58 errors in 30.96s` | 기존 실패 — 실패·오류 노드 ID가 SPEC 이전 기준선과 같음(spec.md §7.2) | `sync_backend.log` |
| vitest 전체 | `Test Files 1 failed \| 95 passed (96)` / `Tests 832 passed (832)` | PASS — 실패 파일 1개는 기존 `e2e/preset-flow.spec.ts` Playwright 수집 문제(§7.2) | `sync_vitest.log` |
| `tsc -b` | 로그에 오류 출력 없음(`> tsc -b` 뒤 빈 줄), 오케스트레이터 기록 exit 0 | PASS | `sync_tsc.log` |
| ruff 새 지적 | `diff sync_ruff_head_norm.txt sync_ruff_base_norm.txt` → 차이 없음, 두 파일 41줄 = 41줄(기준 `f747ce5`), 새 파일 11개 지적 0 | PASS | `sync_ruff_head_norm.txt`, `sync_ruff_base_norm.txt` |

**4차원 감사 판정.** `sync_4dim_result.json`: `verdict` PASS, `harmonic_mean` 0.8912721049629209(임계 0.85, Tier L) — Functionality 0.93 / Security 0.90 / Craft 0.84 / Consistency 0.90. 지적 12건 모두 minor, `evidence_gaps` 17건. **판정이 구속력을 갖는 근거**: 4차원 모두 임계 이상이고 must-pass 실패가 없는 정상 경로이므로 sync-auditor를 따로 띄우지 않고 이 판정을 그대로 쓴다(오케스트레이터 결정). minor 12건은 고치지 않고 spec.md §7.1에 기록했다.

**run에서 넘어온 이탈 5건의 처리 (spec v0.4.0).**

| # | 이탈 (§E.3) | 처리 |
|---|---|---|
| 1 | 기준 종목 부재 가드 | spec.md REQ-RSR-001에 as-implemented 주석 |
| 2 | 스팩 판별 범위(가격 행 종목명) | spec.md REQ-RSR-003·§2.4 B-1에 주석 |
| 3 | M5 계획 밖 변경 | plan.md §D 파일 24 → 26개(`SectorAnalysis.tsx`, `global.css`), §G.1 계획 밖 테스트 변경 |
| 4 | 기존 실패 3종 | spec.md §7.2 |
| 5 | `docs/rs-timeline-eli5.html` 미커밋 | plan.md §D 22번 주석(`.gitignore:251:docs/`). 이 파일의 추적 여부는 이번 sync에서도 바꾸지 않는다 |

**갱신한 문서.**
- `CHANGELOG.md` — `[Unreleased]` 첫 항목 `### Changed (SPEC-RS-REBALANCE-001 v0.4.0 — RS 타임라인 재조정, 2026-10-20)`
- `README.md` — 기능 표 2행 추가(종목 스크리닝: IBD식 재가중·열기 배지, 섹터·테마 분석: RS Med 열). 구조 변경 없음
- `.moai/project/product.md` — 기능 목록 12번 "RS Rating Rebalance & Heat Badge" 추가
- 바꾸지 않음: `.moai/project/structure.md`, `.moai/project/tech.md`, codemaps — 새 디렉터리·의존성이 없다(신규 운영 파일은 기존 `scripts/rs_eval/` 안의 `stage2_ratio_eval.py` 하나)

**상태 전이.** spec.md 머리말 `status: in-progress → completed`(3단계 마감 관례상 implemented를 거쳐 sync 커밋 하나에서 completed로), `updated: 2026-10-20`(이미 같은 날짜). plan.md·acceptance.md·research.md·progress.md에는 머리말 status 필드가 없어 전이 대상이 아니다. spec.md HISTORY 표는 본문이라 manager-docs가 행을 더하지 않았다 — 전이 기록은 이 절이 담는다.

**Gaps.** (1) `tsc -b` exit 0은 로그에 종료 코드 줄이 없어 오케스트레이터 기록에 의존한다. (2) AC-RSR-011 버블 툴팁 배지 라이브 호버, `docs/rs-timeline-eli5.html` 다크 테마·모바일 렌더는 여전히 미관측(spec.md §7.3). (3) sync 커밋 SHA는 커밋이 자기 SHA를 담을 수 없어 아래에 적지 못한다 — `git log --oneline -1 -- .moai/specs/SPEC-RS-REBALANCE-001/progress.md`로 확인한다.

```yaml
sync_complete_at: 2026-10-20
sync_commit_sha: self   # 이 절을 담은 sync 커밋 — 커밋은 자기 SHA를 담을 수 없음, git log로 확인
sync_status: completed
sync_route: A (main 직접 커밋, PR 없음, push 없음)
sync_scope: docs-only (gate-sync-2, 코드 변경 없음)
sync_4dim: {verdict: PASS, harmonic_mean: 0.891, threshold: 0.85, functionality: 0.93, security: 0.90, craft: 0.84, consistency: 0.90, findings: "12 minor (spec.md §7.1)", binding: "happy path — sync-auditor 미기동"}
frontmatter_status_transitions:
  spec.md: in-progress → implemented → completed (sync 커밋 하나에서, updated 2026-10-20)
  plan.md / acceptance.md / research.md / progress.md: 머리말 status 없음 — 전이 대상 아님
b12_self_test_a: "grep -c 'SPEC-RS-REBALANCE-001' CHANGELOG.md → 0 (추가 전)"
b12_self_test_b: "acceptance.md 고유 AC-RSR-* 19개(001~018 + 008b) = CHANGELOG 'AC-RSR-001~018 + 008b 19개'. 원시 정규식 sort -u 24는 본문의 축약 별칭 AC-1b·AC-2~6 포함, 008b는 정규식이 008로 자름"
b12_self_test_c: "CHANGELOG에 적은 경로 30개 [ -e ] 존재 확인(30/30)"
changelog_entry_position: "[Unreleased] 첫 항목 — ### Changed (SPEC-RS-REBALANCE-001 v0.4.0 …)"
run_commit_sha_backfill: "§E.3 run_commit_sha·M6 → 7a77769"
docs_unchanged: [structure.md, tech.md, codemaps]
```
