# M1 — DB-less RED 재현 실측 (plan §F M1 / AC-002)

## 1. DB-less 전제 확인 (수정 전, 실측)

- 워크트리: `/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a54a6df6c5c4a1636` (HEAD 318ab2f, main에서 컷)
- `git status --short`: `.moai/logs/` 1건(untracked, 런타임 관리 대상 — 커밋 안 함) 외 깨끗함
- DB 부재 확인: 실행 전 `find Output -name '*.db' | wc -l` → `0` (B8대로 임포트 mkdir의 빈 `Output/`도 아직 없었음)
- 바인딩 단언(plan §C-4): `cd <워크트리> && /Users/byunjungwon/Dev/my-project-01/my_chart/.venv/bin/python -c "import backend; print(backend.__file__)"`
  - 출력 (verbatim): `/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a54a6df6c5c4a1636/backend/__init__.py`
  - 워크트리 내부 경로 → `VENV-BINDING-LEAK` 없음 확인

## 2. 수집 완결성

명령: `.venv/bin/pytest tests/ --co -q` (워크트리 cwd)

출력 말미 (verbatim):

```
1089/1184 tests collected (95 deselected) in 1.20s
```

종료 코드 0 → REQ-001의 수집 축은 수정 전에도 충족 (실패는 실행 축).

## 3. 전체 실행 — RED 관측 (verbatim)

명령: `.venv/bin/pytest tests/ -q` (워크트리 cwd, timeout 600s)

원문 로그: `.moai/state/verify/develop-hermetic/m1-red-full-run.log` (주 체크아웃 gitignored 증거 저장소)

출력 요약행 (verbatim):

```
20 failed, 1067 passed, 1 skipped, 95 deselected, 1 xpassed in 87.24s (0:01:27)
```

종료 코드: **1** (RED 관측 — M1 종결 조건 충족: 관측된 실패 > 0)

## 4. 실패 테스트 ID 전수 목록 (실측 20건 — 로그 FAILED 행 전수 인용)

**tests/test_market_api.py (12건)** — 조사 예상 12건과 일치:

```
FAILED tests/test_market_api.py::TestStageOverviewEndpoint::test_endpoint_returns_200
FAILED tests/test_market_api.py::TestStageOverviewEndpoint::test_response_has_distribution
FAILED tests/test_market_api.py::TestStageOverviewEndpoint::test_distribution_sums_correctly
FAILED tests/test_market_api.py::TestStageOverviewEndpoint::test_response_has_by_sector
FAILED tests/test_market_api.py::TestStageOverviewEndpoint::test_response_has_stage2_candidates
FAILED tests/test_market_api.py::TestStageOverviewEndpoint::test_stage2_candidates_have_required_fields
FAILED tests/test_market_api.py::TestSectorRankingEndpoint::test_endpoint_returns_200
FAILED tests/test_market_api.py::TestSectorRankingEndpoint::test_response_has_sectors_list
FAILED tests/test_market_api.py::TestSectorRankingEndpoint::test_response_has_date
FAILED tests/test_market_api.py::TestSectorRankingEndpoint::test_sector_items_have_required_fields
FAILED tests/test_market_api.py::TestSectorRankingEndpoint::test_sectors_ordered_by_rank
FAILED tests/test_market_api.py::TestSectorRankingEndpoint::test_sector_returns_are_percentages
```

**tests/test_response_contract.py (4건)** — 조사 예상 4건과 일치:

```
FAILED tests/test_response_contract.py::test_ac_sag_036_all_endpoints_carry_envelope_keys
FAILED tests/test_response_contract.py::test_ac_sag_036_excluded_key_always_present_even_when_empty
FAILED tests/test_response_contract.py::test_ac_sag_036_return_window_days_shape
FAILED tests/test_response_contract.py::test_backward_compatible_legacy_keys_preserved
```

**tests/test_m6_gap_closure.py (4건)** — 정적으로 미설명이던 세트 중 4건 관측:

```
FAILED tests/test_m6_gap_closure.py::test_g20_rrg_market_filter_recomputes_rs_ratio
FAILED tests/test_m6_gap_closure.py::test_g20_stock_bubble_market_filter_reduces_universe
FAILED tests/test_m6_gap_closure.py::test_g23_stock_bubble_item_has_ac_sag_041_fields
FAILED tests/test_m6_gap_closure.py::test_g23_weight_in_sector_sums_close_to_one
```

**tests/test_ac_sag_045_r1_r4_r5a.py (0건)** — 조사가 "미설명 5건"에 넣었던 나머지 1건은 **본 실측에서 재현되지 않았다**. 결함 주장 없음(프로젝트 교훈 #9: 관측 없는 결함 주장 금지). 해당 파일 전체는 DB-less 실행에서 통과(1067 passed에 포함).

## 5. 조사 예상 vs 실측 대조 (AC-002 요건)

| 구분 | 조사 예상 (SPEC §2) | M1 실측 | 판정 |
|------|--------------------|---------|------|
| test_market_api.py | 12건 (`test_client` DAILY 미패치) | 12건 | 일치 — 단, 실패 위치는 daily에 임계적으로 의존하는 stage·sectors 엔드포인트(market overview는 try/except 폴백으로 생존) |
| test_response_contract.py | 4건 (`client`의 stage.DAILY 미패치) | 4건 | 일치 |
| test_m6_gap_closure.py | 4건 (미설명) | 4건 | 관측됨 — 원인은 M3 진단으로 닫음(§6, m3-unexplained-diagnosis.md) |
| test_ac_sag_045_r1_r4_r5a.py | 1건 (미설명) | **0건** | 미재현 — 결함 주장 없음, 통과 실측으로 기록 |
| 합계 | 약 21건 (16+5) | **20건** (16+4) | 예상은 절대 상수가 아니며 본 실측값이 기준(plan §G-3) |

## 6. 핵심 트레이스백 발췌 (원문은 m1-red-full-run.log 참조)

### 6.1 test_market_api / test_response_contract — 503 weekly_db_not_ready

```
E           AssertionError: /api/stage/overview → 503: {"detail":{"error":"weekly_db_not_ready","detail":"no such table: stock_prices"}}
E           assert 503 == 200
```

- 503 래퍼가 "weekly_db_not_ready"로 표시하지만 m6 파일(양쪽 라우터 WEEK+DAILY 모두 패치)의 stage 테스트가 통과한 것과 대조하면, 미패치 `DAILY_DB_PATH`(→ 주 체크아웃 `Output/stock_data_daily.db` 파생 경로) 조회가 원인. B2/B3 예상과 부합.

### 6.2 test_m6_gap_closure — 빈 응답 (M3 진단 대상)

```
E       AssertionError: market=all/kospi 공통 섹터가 없다 — 비교 불가        (test_g20_rrg)
E       AssertionError: market=kospi 종목 수(0)가 market=all(0) 과 같거나 많다 (test_g20_stock_bubble)
E       AssertionError: stocks[] 가 비어 있다                                  (test_g23_fields)
E       AssertionError: weight_in_sector 가 전부 결측이다                      (test_g23_weight)
```

- 공통 배경 로그: `WARNING my_chart.analysis.universe:universe.py:145 registry 전용 종목(registry \ stock_meta) 2238종` — stock_meta 조회가 비어 있음을 시사.
- 진단 결과: `my_chart/analysis/sector_advanced.py:166`의 `_get_stock_meta`가 `DEFAULT_DB_DAILY`(config 파생 `Output/stock_data_daily.db`)로 폴백하는데, 이 이름은 라우터 레벨 패치 밖에 있다. 상세는 `m3-unexplained-diagnosis.md`.

## 7. RED 실행의 부작용 관측 (REQ-004 생성 축의 실증)

수정 전 RED 실행 직후 워크트리 `Output/`에 `stock_data_daily.db` 1건이 **생성**되어 있었다 (`find Output -name '*.db' | wc -l` → `1`). 미패치 상수 경로에 대한 `sqlite3.connect`가 빈 파일을 만든 것으로, REQ-004(프로덕션 경로 비접촉) 위반의 실측 증거다. DB-less 전제 복원을 위해 이 빈 파일을 삭제했고(`wc -l` → `0` 재확인), 최종 AC-010 검사는 수정 후 실행 기준으로 다시 수행한다.
