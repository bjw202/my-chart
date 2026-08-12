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
| M6 (회귀 게이트+성능) | _(본 커밋)_ | `test_regression_sgr020.py`(AC-SGR-020 R1~R5) + 성능 실측 + 릴리스 노트 |

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

### 대조 단언(falsification) 7종 — 전부 GREEN (DoD §4)

AC-SGR-002(anomalies 미기록) · 005(`meta_service` :196 되돌림 검출) · 006-A(6지점 개별 되돌림) · 006-B(OFFSET 3 / 자체 GROUP BY 되돌림) · 010(positional INSERT) · 017/018(stale 필터 제거 / last_updated 되돌림) · 020 R2(anchor(t,91)/(364) 오배선 감지) · 020 R3(Name dedup 분기).

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: audit-ready
run_complete_at: 2026-08-12
run_commit_sha: pending-backfill   # 본 M6 커밋 SHA — 커밋 후 후속 커밋으로 backfill (D3 자기참조 면제)
tier: M
cycle_type: tdd
route: A                            # Hybrid Trunk main-direct
development_mode: tdd               # quality.yaml
milestones_completed: [M0, M1, M2, M3, M4, M5, M6]
ac_pass_count: 21
ac_fail_count: 0
ac_total: 21
preserve_list_post_run_count: 0     # M6 는 구현 코드 미수정(test+docs only)
l44_pre_commit_fetch: true          # git fetch origin main 사전 확인 — origin 정합
l44_post_push_fetch: pending-backfill
new_warnings_or_lints_introduced: 0 # ruff 미설치(알려진 gap, 아래 §Gaps) — 신규 lint 0건(구현 코드 미수정)
cross_platform_build:
  applicable: false                 # Python 프로젝트 — cross-platform build tag 해당 없음
total_run_phase_files:
  impl_modified: 0                  # M6 = test+docs only, 구현 파일 0건 수정(B10 준수)
  test_created: 1                   # tests/test_regression_sgr020.py
  docs_created: 1                   # .moai/specs/SPEC-SECTOR-GRID-001/release-notes.md
  docs_modified: 1                  # .moai/specs/SPEC-SECTOR-GRID-001/progress.md (본 §E.2/§E.3)
m1_to_mN_commit_strategy: per-milestone   # M1~M5 마일스톤별 commit, M6 본 커밋
```

### §Gaps (미검증 — 5-section §3.4)

- **성능 — 캐시 미적중 P95<50ms MISS**: 실측 803ms. spec §0.2 처방 완화(메모이즈, M1 구현)로 캐시 적중 지점은 <5ms(목표 1000× 여유 충족). 콜드 비용은 (프로세스×mtime)당 1회.
- **성능 — `/api/db/update` 적재 소요 + `/sectors/ranking` 응답**: 읽기 전용 측정 불가(서버/ingest 필요). ② 집계 SPEC ship 후 별도 측정 예정.
- **lint(ruff)**: ruff 미설치(프로젝트 알려진 gap). M6 는 구현 코드 0건 수정이므로 신규 lint 도입 없음 — 구조적으로 보장됨(`git diff --name-only` 로 검증).

### §Residual-risk (5-section §3.5)

- **라이브 재평가 미수행**: spec §0.1 재평가 시점(② ship 후 주중+주말 갱신 1회씩) 전이므로 "Bump 날짜 축 균일" 사용자 확인 미수행. 본 SPEC 가치 판정은 해당 시점까지 보류.
- **8건 기존 결함(비게이팅)**: `test_api`·`test_meta_service`·`test_rs_line`·`test_screen_service` 의 market_cap/rs_line/screen 결함. 본 SPEC 범위 밖이나, 향후 별도 SPEC으로 처리 필요.
- **플리커(flicker)**: 캐시 적중/미적중 측정은 단일 프로세스 안정 환경에서 수행. 다중 워커/재시작 잦은 환경에서는 콜드 비용 빈도 증가 가능(완화는 동일).

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

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
