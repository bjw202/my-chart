# SPEC-SECTOR-GRID-001 Progress

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-08-12
tier: M
artifacts: [spec.md, plan.md, acceptance.md, progress.md]
ac_count: 21
invariants_owned: [TG-1, TG-2, TG-3, TG-4, TG-5, UN-4]
latent_divergence_guards: [REQ-SGR-017]   # 미분류 센티넬 — 가시적 변화 없음
open_questions: [O-G1, O-G2, O-G3, O-G4, O-G5, O-G6, O-G7]
blocking_before_run: [O-G5]               # 미분류 센티넬 문자열 값 — M2 착수 전 필요
```

미결 O-G1~O-G7은 전부 사용자 확인 대기 상태다. 착수 전 확인이 필요한 순서:

- **O-G5**(미분류 센티넬 문자열 값) — **M2 차단** (`plan.md` M2가 "O-G5 선결 필요"로 명시)
- **O-G4**(supersede 물리 삭제 승인) — **M4 차단**
- **O-G6**(`market_breadth.py:472`) / **O-G7**(`meta_service.py:135` 일봉 기준일) — 차단 아님. 결정 전까지 AC-SGR-005 allowlist에 잔류하며, allowlist 상한 5의 근거다
- O-G1(registry 전용 13종목 원인) / O-G2(미완성 주 바와 기간 계산 — ②가 O-A8로 인수) / O-G3(stale 32 vs 34) — 차단 아님. 진단·측정으로 처리

## §E.2 Run-phase Evidence

### 마일스톤 커밋 맵 (M0~M6)

| 마일스톤 | SHA | 요약 |
| --- | --- | --- |
| M0 (WIP 보존) | `97e90d3` | 기존 inline WIP(sector_metrics/sector_advanced_service/test) 보존 |
| M1 (격자 계약) | `b51c460` | `weekly_grid.py` 신규 + 프로즌 픽스처(`tests/fixtures/frozen/weekly-2026-08-12/`) |
| M2 (유니버스 규약) | `1fa894b` | `universe.py` + registry Code-dedup + 미분류 센티널 단일화 |
| M3 (INSERT column-name) | `c311cc4` | `weekly.py` positional → column-name INSERT (Lesson #8) |
| M4 (적재 supersede) | `a0b591e` | 주중 재적재 supersede + `--no-supersede` 안전장치 |
| M5 (7 소비자 배선) | `128cdd8`·`23de261`·`c1e2d42`·`7179f8d`·`9617292`·`b715e0e`·`facf34d`·`71063c0`·`62e4edd`·`74d2619`·`b764f75`·`9d5aeec` | 공유 헬퍼 `_get_latest_valid_date` + 7 소비자 격자 수렴 + `test_consumer_dates.py` |
| M6 (회귀 게이트+성능) | `1f62beb`·`1ccf918` | `test_regression_sgr020.py`(AC-SGR-020 R1~R5) + 성능 실측 + 릴리스 노트 |
| M7 (반증력 복구, v0.3.0) | _(본 커밋)_ | 공허했던 대조 단언 3종(F1/F2/F3) 실질화 + AC-005 규범 명령 바이트 동등(F6) + AC-004 재분류(F7) + `nongating` 마커 등록 |

### 테스트 결과 (M6 종료 시점, venv=`/Users/byunjungwon/Dev/my_chart/.venv`)

```
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest \
    tests/test_weekly_grid.py tests/test_universe.py tests/test_weekly_insert.py \
    tests/test_weekly_supersede.py tests/test_consumer_dates.py \
    tests/test_sector_history_consistency.py tests/test_regression_sgr020.py -v
======================== 72 passed, 1 warning in 0.59s =========================
```

- **SPEC-SECTOR-GRID-001 스코프**: 72 passed / 0 failed
- **AC-SGR-001~021 게이팅 전부 PASS** (프로즌 픽스처 위에서 안정)
- **AC-SGR-020 R1~R5**: `test_regression_sgr020.py` 6 passed (R3 = 2 함수: 라이브값 32 + Code/Name 분기)
- **전체 회귀 (`pytest tests/ --ignore=tests/fnguide`)**: 475 passed / 8 failed — **8건은 SPEC-SECTOR-GRID-001 범위 밖**의 기존 결함(`test_api`·`test_meta_service`·`test_rs_line`·`test_screen_service` 의 market_cap/rs_line/screen, grep 교차검증: 본 SPEC 파일 0건 히트). M1~M5 가 도입한 회귀 아님.

### 테스트 결과 (M7 반증력 복구 종료 시점)

```
$ python -m pytest tests/test_weekly_grid.py tests/test_consumer_dates.py \
    tests/test_weekly_insert.py tests/test_weekly_supersede.py \
    tests/test_universe.py tests/test_regression_sgr020.py -q
84 passed, 1 warning in 0.65s        # M6 69 → M7 84 (+15, 신규 단언·케이스)

$ python -m pytest -q                 # 전체 스위트
8 failed, 584 passed, 68 skipped, 25 errors in 81.60s
```

- **게이팅 6파일**: M6 69 passed → M7 **84 passed** (증가분 15건 전부 본 M7 신규 단언).
- **전체 회귀 baseline 대조**: 569 → **584 passed (+15 = M7 추가분과 정확히 일치)**, **8 failed 동일**, **25 errors 동일**. 실패 목록도 baseline 과 완전 일치(`test_screen_service` ×3 · `test_rs_line` ×2 · `test_meta_service` ×2 · `test_api` ×1). **M7 이 도입한 회귀 0건.**
- **커버리지 (신규 격자·유니버스 모듈, DoD §4 게이트)**: `my_chart/analysis/weekly_grid.py` **100%** (94/94) · `my_chart/analysis/universe.py` **100%** (56/56) → **>= 85% 충족**. 측정: `coverage run --source=my_chart,backend -m pytest`(pytest-cov 경로는 numpy ImportError 로 실패 — §Gaps 참조).

### 성능 실측 (§0.2, 라이브 DB `Output/stock_data_weekly.db` 읽기 전용)

라이브 DB 규모: **885,623 행 / 2,582 종목 × 385 날짜**(spec §0.2 추정 2,548×346=881,608 와 일치).
쿼리: `SELECT Date, COUNT(*) FROM stock_prices WHERE Name NOT IN (...) GROUP BY Date` → `SCAN stock_prices USING INDEX idx_stock_prices_date`(전표 스캔 + 그룹핑).

| 지점 | 목표 | 실측(N=20, p50/p95) | 판정 |
| --- | --- | --- | --- |
| 격자 산출 캐시 적중(2nd call, lru_cache) | < 5ms | **0.003 / 0.005 ms** | PASS (~1000× 여유) |
| 격자 산출 캐시 미적중(1st call / mtime 변동 후) | P95 < 50ms | **635 / 803 ms** | MISS(아래 근거) |

**캐시 미적중 목표 미달 — 근거 + 완화(spec §0.2 준거)**:
- spec §0.2 가 "목표 미달 시 격자 산출 결과를 프로세스 내 메모이즈(`(db_path, mtime)` 키)한다"고 처방한 **완화가 이미 M1 에 구현**됨(`weekly_grid._compute_cached`, `@lru_cache`, mtime 변화 시 자동 무효화).
- 캐시 적중 지점은 목표를 ~1000× 여유로 충족 → 서버 프로세스 내에서 **1회 콜드 비용 후 모든 후속 요청은 <5ms**. 콜드 비용은 (프로세스 × DB mtime) 당 1회(` /api/db/update` 직후 1회).
- 50ms 목표는 단일 SELECT+그룹핑 추정이었으나, 885K 행 전표 스캔은 SQLite 인덱스로도 회피 불가. 추가 최적화(예: Date 인덱스 커버링 스캔 / 증분 캐시)는 **범위 밖** — 본 SPEC의 완화(메모이즈)가 유효하므로 추후 SPEC으로 연기.

**지연(DEFERRED) 지점 — 읽기 전용으로 측정 불가 (§0.2)**:

| 지점 | 지연 사유 |
| --- | --- |
| `/api/db/update` weekly 적재 전체 소요 | 라이브 ingest 필요(네트워크 + DB 쓰기). M6 는 읽기 전용 측정만 허용 |
| `/sectors/ranking` 응답 P50/P95 | 서버 기동 필요. M6 는 서버 기동 금지 |

두 지점은 ② 집계 SPEC ship 후 라이브 서버/ingest 환경에서 별도 측정한다.

### AC PASS 집계 (21/21)

| AC | 상태 | 게이트 위치 |
| --- | --- | --- |
| AC-SGR-001 (ISO 주당 1바) | PASS | `test_weekly_grid.py` |
| AC-SGR-002 (간격 6~10일 + anomalies) | PASS | `test_weekly_grid.py` |
| AC-SGR-003 (진행 중인 주 분리) | PASS | `test_weekly_grid.py` |
| AC-SGR-004 (부분 데이터 배제) | PASS | `test_weekly_grid.py` |
| AC-SGR-005 (자체 기준일 조회 부재) | PASS | `test_consumer_dates.py` |
| AC-SGR-006-A (기준일 해석자 6지점) | PASS | `test_consumer_dates.py` |
| AC-SGR-006-B (격자·앵커 소비자 2지점) | PASS | `test_consumer_dates.py` |
| AC-SGR-007 (364일=52±1바 + anchor) | PASS | `test_weekly_grid.py` |
| AC-SGR-008 (weeks=N 의미) | PASS | `test_weekly_grid.py` |
| AC-SGR-009 (fresh-DDL round-trip) | PASS | `test_weekly_insert.py` |
| AC-SGR-010 (legacy-ALTER round-trip) | PASS | `test_weekly_insert.py` |
| AC-SGR-011 (positional INSERT 금지) | PASS | `test_weekly_insert.py` |
| AC-SGR-012 (주중 재적재 supersede) | PASS | `test_weekly_supersede.py` |
| AC-SGR-013 (supersede 안전장치) | PASS | `test_weekly_supersede.py` |
| AC-SGR-014 (유니버스 단일 소스) | PASS | `test_universe.py` |
| AC-SGR-015 (유효 유니버스 4중 교집합) | PASS | `test_universe.py` |
| AC-SGR-016 (registry dedup + 경고) | PASS | `test_universe.py` |
| AC-SGR-017 (stale 배제, 경계 14/15) | PASS | `test_universe.py` |
| AC-SGR-018 (last_updated 판정 금지) | PASS | `test_universe.py` |
| AC-SGR-019 (registry 전용 진단) | PASS | `test_universe.py` |
| AC-SGR-020 (회귀 방지 R1~R5) | PASS | `test_regression_sgr020.py` |
| AC-SGR-021 (미분류 센티널 단일화) | PASS | `test_universe.py` |

**AC PASS = 21/21** (AC-SGR-006 은 A/B 두 하위절 모두 PASS).

### 대조 단언(falsification) — M6 기록 정정 + M7 복구 (DoD §4)

**[정정] M6 종료 시점의 기록은 부정확했다.** M6 는 "대조 단언 7종 — 전부 GREEN"으로 보고했으나, sync-auditor 감사(PASS-WITH-DEBT 78.6/100) 결과 **7종 중 3종은 구현을 전부 되돌려도 GREEN**이었다 — 즉 아무것도 반증하지 못했다. DoD §4 는 대조 단언을 "작성했다"가 아니라 **"되돌린 변형에서 RED 가 관측됐다"**로만 PASS 처리하도록 요구하는데, M6 는 전자로 판정했다. 이 오판정 자체가 0.2.x 실패 양식의 재발이며, 기록에서 지우지 않고 남긴다.

**M6 실제 상태 — 진성 4종 / 공허 3종**

| # | 대조 단언 | M6 실제 | 원인 |
| --- | --- | --- | --- |
| 1 | AC-SGR-002 anomalies 미기록 | **진성** | — |
| 2 | AC-SGR-006-B OFFSET 3 / 자체 GROUP BY 되돌림 | **진성** | — |
| 3 | AC-SGR-010 positional INSERT | **진성** | — |
| 4 | AC-SGR-017/018 stale 필터 제거 / last_updated 되돌림 | **진성** | — |
| 5 | AC-SGR-020 R2 anchor 오배선 | **진성** | — |
| 6 | AC-SGR-020 R3 Name dedup 분기 | **진성** | — |
| F1 | AC-SGR-021 센티넬 발산 차단 | **공허** | 테스트 파일 안에서 동일 식을 2회 복사해 비교 — 프로덕션 코드 미실행, 무조건 통과 |
| F2 | AC-SGR-006-A 6지점 개별 되돌림 | **공허(부분)** | A-4·A-6 이 공유 헬퍼를 그대로 재호출 — 실질 4-way. 두 소비자를 전부 되돌려도 통과 |
| F3 | AC-SGR-020 R5 | **공허** | `len(history_grid) <= len(raw)` 는 선별 관계상 **수학적 항진명제** (385<=385 로도 통과) |

**M7 복구 후 — 반증 실증 매트릭스 (전부 되돌린 변형에서 RED 관측)**

| 수리 | 되돌린 변형 | revert 시 | revert 없이 |
| --- | --- | --- | --- |
| F1 AC-021 | `stage_service.ETC_SECTOR` → `"Unknown"` | **FAIL** (`기타 != Unknown`) | PASS |
| F2 A-4 | `sector_advanced_service._get_latest_valid_date` → 순진 `MAX(Date)` | **FAIL** (`2024-01-15 != 2024-01-12`) | PASS |
| F2 A-6 | `meta_service._get_latest_valid_date` → 순진 `MAX(Date) WHERE Name=REFERENCE_STOCK` | **FAIL** (`chg_1w 0.9999 != 0.1111`) | PASS |
| F3 R5 | `history_grid` → `grid`(진행 중인 주 포함) | **FAIL** (`346 != 345`) | PASS |
| F6 AC-005.2 | `sector_ranking_service` 에 순진 `MAX(Date)` 재도입 | **FAIL** (잔류 집합 초과 1건) | PASS |
| F7 AC-004 | CG-3 행 수 판정 제거(중앙값 0) | **FAIL**(대조 테스트가 복귀를 단언) | PASS |

**M7 반증 강도 판정**: F1/F2(A-4·A-6)/F3/F6/F7 **전부 이전보다 엄격히 통과하기 어렵다** — 공허한 3종은 프로덕션 경로 실호출·프로즌 리터럴·집합 동등으로 대체됐고, 완화된 단언은 없다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: audit-ready
run_complete_at: 2026-08-12
run_commit_sha: a61c3c1               # M7 커밋 SHA (D3 자기참조 면제 — 본 후속 커밋으로 backfill 완료)
prior_run_commit_sha: 1f62beb         # M6 커밋 SHA (1ccf918 로 backfill 완료)
tier: M
cycle_type: tdd
route: A                            # Hybrid Trunk main-direct
development_mode: tdd               # quality.yaml
milestones_completed: [M0, M1, M2, M3, M4, M5, M6, M7]
ac_pass_count: 21
ac_fail_count: 0
ac_total: 21
falsification_genuine_count: 9      # M7 복구 후 진성 대조 단언 (M6 진성 6 + F1/F2/F3 복구 3)
falsification_vacuous_count: 0      # M6 시점 3건 → M7 에서 전부 실질화
preserve_list_post_run_count: 0     # M7 도 구현 코드 미수정(test+config only)
l44_pre_commit_fetch: true          # git fetch origin main 사전 확인 — origin 정합
l44_post_push_fetch: true           # push 후 origin/main == HEAD 정합 확인
new_warnings_or_lints_introduced: 0 # ruff 미설치(알려진 gap, 아래 §Gaps) — 구현 코드 미수정
coverage_new_grid_universe_modules: # DoD §4 ">= 85%" 게이트
  weekly_grid_py: "100% (94/94)"
  universe_py: "100% (56/56)"
  db_weekly_py: "47% (95/202)"      # SPEC 수정 대상이나 '신규 격자·유니버스 모듈' 범주 밖 — §Gaps
  method: "coverage run --source=my_chart,backend -m pytest"
cross_platform_build:
  applicable: false                 # Python 프로젝트 — cross-platform build tag 해당 없음
total_run_phase_files:
  impl_modified: 0                  # M7 = test+config only, 구현 파일 0건 수정(B10 준수)
  test_modified: 4                  # test_universe / test_consumer_dates / test_regression_sgr020 / test_weekly_grid
  config_modified: 1                # pyproject.toml (nongating 마커 등록)
  docs_modified: 1                  # progress.md (본 §E.2/§E.3 — §E.4 는 manager-docs 소유, 미수정)
m1_to_mN_commit_strategy: per-milestone   # M1~M5 마일스톤별 commit, M6·M7 각 1커밋
```

### §Gaps (미검증 — 5-section §3.4)

- **성능 — 캐시 미적중 P95<50ms MISS**: 실측 803ms. spec §0.2 처방 완화(메모이즈, M1 구현)로 캐시 적중 지점은 <5ms(목표 1000× 여유 충족). 콜드 비용은 (프로세스×mtime)당 1회.
- **성능 — `/api/db/update` 적재 소요 + `/sectors/ranking` 응답**: 읽기 전용 측정 불가(서버/ingest 필요). ② 집계 SPEC ship 후 별도 측정 예정.
- **lint(ruff)**: ruff 미설치(프로젝트 알려진 gap). M6·M7 모두 구현 코드 0건 수정이므로 신규 lint 도입 없음 — 구조적으로 보장됨(`git diff --name-only` 로 검증).
- **커버리지 — M6 시점 미측정·미공시 (M7 에서 해소)**: DoD §4 "신규 격자·유니버스 모듈 라인 커버리지 >= 85%"는 **명시적 게이트인데도 M6 progress.md 에 측정값도 미측정 사유도 없었다**(`grep -i "coverage\|커버리지"` → 0건). 게이트를 조용히 비운 것이며, sync-auditor 가 이를 지적했다. M7 에서 측정 완료: `weekly_grid.py` **100%**, `universe.py` **100%** → 게이트 충족.
  - **측정 경로 주의**: `pytest --cov`(pytest-cov)는 이 환경에서 `ImportError: Unable to import required dependency numpy`로 실패한다(`COVERAGE_CORE=ctrace` 로도 동일). numpy 자체는 정상(`import numpy` → 2.4.2). **동작하는 경로는 `coverage run --source=my_chart,backend -m pytest` + `coverage report`** 이며, `--source` 를 패키지명으로 주는 것이 핵심이다(모듈 dotted-path 로 주면 "never imported"). 후속 측정 시 이 경로를 쓸 것.
  - **`my_chart/db/weekly.py` = 47%(95/202)**: 본 SPEC 이 수정한 INSERT 경로(M3 column-name 마이그레이션)는 `test_weekly_insert.py`·`test_weekly_supersede.py` 가 덮지만, 미커버 107 statements 는 **네트워크 의존 crawl/ingest 경로**로 기존 코드다. DoD 문구의 "신규 격자·유니버스 모듈" 범주 밖으로 판단해 게이트 판정에서 제외했다 — 이 해석 자체를 명시적으로 남긴다(조용히 빼지 않는다).
- **AC-SGR-021 — 진짜 NULL(NaN) 산업명(대) 는 canonical 센티넬로 수렴하지 않는다 (M7 발견)**: pandas 가 registry 의 NULL 을 `NaN` 으로 승격하면 `NaN or ETC_SECTOR` 는 **NaN 이 truthy 이므로** 센티넬 분기를 타지 않고 `str(NaN) == 'nan'` 이 섹터 키가 된다(실측: 두 경로 모두 `'nan'`). AC-SGR-021 의 게이팅 요건(**두 경로 일치**)은 성립하므로 "발산 차단"은 유지되나, 빈 문자열과 달리 NULL 은 `기타` 로 정규화되지 않는다. 라이브 `stock_meta` 의 NULL/빈문자열/`'nan'`/`'기타'` 행이 **현재 0건**이라 가시적 영향은 없다. `test_ac_sgr_021_true_null_sector_paths_still_agree` 가 일치 요건만 게이팅하며, 정규화 여부는 REQ 개정이 필요하므로 미결로 남긴다(AC 본문 수정은 manager-spec 소관).
- **AC-SGR-004 — ISO 주 내부(intra-week) 차선 날짜 대체는 일어나지 않는다 (M7 발견)**: AC-004 본문의 "어떤 ISO 주 W 안에 두 날짜가 있고" 문구를 문자 그대로 구성하면(한 주에 Mon+Fri, 늦은 Fri 가 부분 데이터) CG-1 이 Fri 를 대표로 뽑고 CG-3 이 배제한 뒤 **같은 주의 Mon 으로 되돌아가지 않아 그 주가 통째로 격자에서 빠진다**(실측 확인). 반면 AC 가 명시한 `구성 예`(= `fixture_max_ne_canonical` 형태: W-금요일 + 더 늦은 W+1-월요일)에서는 대표 바가 W-금요일로 정상 대체된다. M7 은 AC 가 지정한 `구성 예`를 게이팅 픽스처로 채택했다. 두 문구의 불일치와 intra-week 미대체 동작은 REQ/AC 개정 사안이므로 미결로 남긴다.

### §Residual-risk (5-section §3.5)

- **라이브 재평가 미수행**: spec §0.1 재평가 시점(② ship 후 주중+주말 갱신 1회씩) 전이므로 "Bump 날짜 축 균일" 사용자 확인 미수행. 본 SPEC 가치 판정은 해당 시점까지 보류.
- **8건 기존 결함(비게이팅)**: `test_api`·`test_meta_service`·`test_rs_line`·`test_screen_service` 의 market_cap/rs_line/screen 결함. 본 SPEC 범위 밖이나, 향후 별도 SPEC으로 처리 필요.
- **플리커(flicker)**: 캐시 적중/미적중 측정은 단일 프로세스 안정 환경에서 수행. 다중 워커/재시작 잦은 환경에서는 콜드 비용 빈도 증가 가능(완화는 동일).
- **O-G6 — `market_breadth.py:472` 는 현재 출하 중인 TG-4 오계산이다 (미결이 아니라 잔여 위험)**: `SELECT DISTINCT Date FROM stock_prices … ORDER BY Date DESC LIMIT ?` 로 주봉 DB 를 조회하므로, 다중 날짜 주 오염을 그대로 받아 **`weeks=12` 가 약 36일치만 반환한다**(본 SPEC 이 R1 에서 84±7일로 고친 것과 동일한 결함). 이는 가설이 아니라 **사용자에게 이미 보이고 있는 오계산**이다. breadth 는 섹터 화면이 아니라 시장 개요 소관이라 본 3-계층 SPEC 범위 밖이며 AC-SGR-005 allowlist(L5)에 잔류시켰으나, spec §7 O-G6 "미결 질문"으로만 기록되어 있어 **잔여 위험 목록에서 누락**되어 있었다. 여기에 명시적으로 등재한다 — 별도 SPEC 으로 격자 적용이 필요하며, 그때까지 시장 개요의 breadth 기간 표기는 신뢰할 수 없다.
- **M6 자기보고 오판정의 재발 가능성**: M6 는 대조 단언을 "작성 여부"로 판정해 공허한 3종을 GREEN 으로 보고했다(위 §E.2 정정 참조). M7 은 6종 전부에 대해 되돌린 변형을 실제 실행해 RED 를 관측했으나, **이 실증 절차 자체는 자동화되어 있지 않다** — 향후 대조 단언이 추가될 때 같은 오판정이 재발할 수 있다. DoD §4 의 "되돌린 변형에서 RED 관측" 요건을 CI 로 강제하는 장치(예: mutation testing)는 본 SPEC 범위 밖이다.

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_status: audit-ready
sync_complete_at: 2026-08-12
sync_commit_sha: 95e0980            # M6 sync 커밋 SHA (D3 backfill — 자기참조 면제, 후속 커밋으로 완료)
tier: M
route: A                             # Hybrid Trunk main-direct
changelog_entry_position: "[Unreleased] > Added (SPEC-SECTOR-GRID-001 v0.2.2, 2026-08-12)"
frontmatter_status_transitions:
  spec_md: "in-progress -> completed"
  plan_md: "N/A (frontmatter 없음 — 본문 전용 문서)"
  acceptance_md: "N/A (frontmatter 없음 — 본문 전용 문서)"
b12_self_test_a: "grep -c 'SECTOR-GRID' CHANGELOG.md (edit 전) = 0 — 중복 없음 확인"
b12_self_test_b: "acceptance.md SSOT AC 21건(AC-SGR-001~021, 006은 A/B 하위절 포함 1건) == CHANGELOG/progress.md ac_count 21 일치"
b12_self_test_c: "CHANGELOG 명시 파일 경로(weekly_grid.py/universe.py/weekly.py) ls 검증 완료"
```

README.md는 수정하지 않았다 — 본 SPEC은 데이터/격자 내부 계약(REQ-SGR-*) 변경으로, README에 문서화된 사용자 대면 기능·설치·실행 절차가 변경되지 않았다(라이브 화면 재계산 결과는 CHANGELOG + release-notes.md로 안내).

## §F Phase 4 Mode Selection

**Phase 1 (Plan Audit Gate)**: BYPASSED-with-recent-PASS — 금일 plan-phase PASS 0.86(iter-2, MUST-PASS 전항 통과) 인정, 산출물 미변경. 사용자 결정(Implementation Kickoff Approval 2026-08-12, 착수 게이트 = "최근 PASS 인정 후 M1.0 착수"). skip 자격(score≥0.90)은 아니나 동일 산물·동일 PASS로 재감사 무의미하여 사용자 판단으로 생략.

Input parameters:
- tier: M
- scope: 9 파일(SPEC-scope 소비자 7 + weekly.py + registry.py) + 신규 모듈 2(weekly_grid.py, universe.py)
- domain count: 2(데이터/격자 계약 + 적재 보호) — 단일 도메인 밀집
- file language mix: Python 100%
- concurrency benefit: LOW(coding-heavy, Anthropic coding-task parallelism caveat)

Mode evaluation: Mode 1 trivial N · Mode 2 background N(write/blocking) · Mode 3 agent-team RETIRED · Mode 4 parallel N(coding-heavy 단일 도메인) · **Mode 5 sub-agent SELECTED** · Mode 6 workflow N(신규 코드 + inter-file 의존, mechanical-uniform 아님)

Decision: sub-agent (Mode 5)
Justification: Anthropic coding-task parallelism caveat — 코딩 작업은 병렬화 가능 태스크가 적음. M1→M6 순차 의존(① 격자가 ②/③ 기반). manager-develop 단일 순차 위임, 마일스톤마다 보고.

Route: A(Hybrid Trunk main-direct) — Tier M 기본, manager-develop main 직접 commit/push.
Development: cycle_type=tdd(quality.yaml), 보고 주기 = 마일스톤마다.

Run-phase 사용자 결정 (Implementation Kickoff Approval 2026-08-12):
- **WIP 처리**: 기존 inline WIP(sector_metrics.py + sector_advanced_service.py + test_sector_history_consistency.py) 보존 커밋 후 M1 canonical(weekly_grid.py)로 재작업. M5에서 inline → grid 호출로 교체.
- **O-G5 해결**: 미분류 센티넬 = `"기타"`(ETC_LABEL 일치, 현재 registry 0건 충돌 없음). REQ-SGR-017 canonical 상수값.
- **O-G4 해결**: supersede 승인(M4 구현, `--no-supersede` 안전장치, 삭제 범위 = 이번 실행 ISO 주 한정, run 전 DB 백업 권고).
- **O-G6/O-G7**: 비차단, AC-SGR-005 allowlist 잔류(market_breadth.py:472 / meta_service.py:135 일봉).
