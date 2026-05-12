# DB Enhance Design Plan

작성 범위: 기존 코드 분석 + additive 확장 설계 + 단계별 구현 계획.  
제약: 현재 단계에서는 코드 작성 없이 설계와 실행 계획만 정리한다.

## 1) Executive Summary

- 현재 구조는 `weekly stock_prices -> weekly relative_strength -> daily stock_prices -> daily stock_meta`의 4단계 배치로 동작하며, 조회/스크리닝 목적에는 충분히 잘 정리돼 있다.
- 가장 큰 부족점은 `point-in-time 학습용 feature snapshot 부재`, `event table 부재`, `forward label 부재`, `market regime 미저장`, `universe/survivorship 구조 부재`다.
- 추천 확장 방향 한 줄 요약:
  기존 `daily/weekly/meta`는 그대로 유지하고, 별도의 `research DB`를 추가해 `market_regime + universe_snapshot + feature_snapshot + setup_events + forward_labels`를 materialized table 중심으로 적층한다.

## 2) Current Code / Data Flow Analysis

### 관련 파일 / 함수

- `backend/routers/db.py`
  - `/api/db/update`, `/api/db/status`, `/api/db/last-updated` 제공
  - 웹 기준 DB 업데이트 공식 진입점
- `backend/services/db_service.py`
  - `start_update()`, `_run_update()`
  - 실제 배치 오케스트레이션 담당
- `my_chart/db/weekly.py`
  - `generate_price_db()`: 주간 `stock_prices`
  - `generate_rs_db()`: 주간 `relative_strength`
- `my_chart/db/daily.py`
  - `price_daily_db()`: 일간 `stock_prices`
- `backend/services/meta_service.py`
  - `rebuild_stock_meta()`, `_rebuild()`
  - daily + weekly + sectormap + `basic_data.xlsx`를 합쳐 `stock_meta` 재구축
- `my_chart/price.py`
  - `price_naver()`, `price_naver_rs()`
  - Naver Finance API fetcher
- `my_chart/registry.py`
  - `get_stock_registry()`, `get_sector_registry()`
  - 종목/섹터 registry 로딩
- `backend/deps.py`
  - daily/weekly DB 경로 및 SQLite connection 제공
- `my_chart/analysis/market_breadth.py`
  - breadth / cycle 계산 로직 존재
  - `market_regime` 확장 시 재사용 가능한 가장 가까운 기존 분석 모듈

### 현재 파이프라인 요약

현재 `_run_update()`의 순서는 아래와 같다.

1. Phase 1: `my_chart/db/weekly.py::generate_price_db()`
   - `Output/stock_data_weekly.db`
   - `stock_prices` 생성/업데이트
   - KOSPI/KOSDAQ 포함
   - WAL, `INSERT OR REPLACE`, 50종목 단위 batch commit
2. Phase 2: `my_chart/db/weekly.py::generate_rs_db()`
   - weekly `relative_strength` 생성
   - `stock_prices`를 날짜별 읽어 percentile 산출
3. Phase 3: `my_chart/db/daily.py::price_daily_db()`
   - `Output/stock_data_daily.db`
   - daily `stock_prices` 생성/업데이트
   - 2년치 일봉 + EMA/SMA/ADR/RS_Line 계산
4. Phase 4: `backend/services/meta_service.py::rebuild_stock_meta()`
   - daily 최신일 snapshot + weekly 최신일 + sectormap + `Input/basic_data.xlsx`
   - `stock_meta` 전체 삭제 후 재적재

### 현재 스키마/동작 특성

- daily/weekly 모두 `PRIMARY KEY (Name, Date)` 기반이다.
- 생성 전략은 대부분 `CREATE TABLE IF NOT EXISTS` + 일부 `ALTER TABLE` 또는 구스키마 감지 후 재생성이다.
- 병렬 fetch는 `ThreadPoolExecutor` 기반이며, 실제 write는 단일 SQLite connection에서 batch insert 한다.
- `stock_meta`는 point-in-time table이 아니라 최신 스냅샷 테이블이다.
- 기존 조회 기능들은 `stock_meta` 또는 `stock_prices + relative_strength`를 직접 읽는다.

### 확장 시 재사용 가능한 부분

- 오케스트레이션
  - `backend/services/db_service.py`의 phase 구조와 progress callback 패턴
- 원천 데이터
  - daily/weekly `stock_prices`
  - weekly `relative_strength`
- 메타/분류 정보
  - `my_chart/registry.py`의 sectormap 로딩
  - `backend/services/meta_service.py`의 market cap 계산 방식
- 시장 상태 계산 후보
  - `my_chart/analysis/market_breadth.py`의 breadth/cycle 계산식

### 가장 안전한 확장 포인트

- 1순위: 기존 4단계 뒤에 research build phase를 추가
  - 이유: 기존 API가 기대하는 DB와 테이블을 건드리지 않는다.
  - 실패 시에도 `stock_meta`까지는 현행 기능 유지가 가능하다.
- 2순위: 별도 `research DB` 파일 추가
  - 권장 파일명: `Output/stock_research.db`
  - 이유: 현행 daily/weekly DB read path와 lock/contention을 분리할 수 있다.
- 비권장: `stock_meta`를 학습용 snapshot으로 직접 확장
  - 이유: 최신 스냅샷 성격이 강하고 누수 위험이 크다.

## 3) Gap Analysis

### 학습/검증 관점의 부족점

- `feature snapshot` 부재
  - 현재는 원천 지표는 있으나 학습 샘플 단위 row가 없다.
- `setup_events` 부재
  - breakout, contraction, pullback 같은 의미 있는 날짜를 구조화하지 못한다.
- `forward_labels` 부재
  - `ret_5d`, `mfe_10d`, `mae_10d`, `success_flag`를 저장하지 않는다.
- `market_regime` 부재
  - 시장 국면을 feature 또는 stratified validation에 쓰기 어렵다.
- `tradable universe` 부재
  - 상장/거래정지/유동성 기준을 특정 날짜 기준으로 재현하기 어렵다.

### point-in-time / leakage 리스크

- `stock_meta`는 최신 snapshot이므로 학습용 입력으로 직접 사용하면 누수 가능성이 높다.
- weekly `relative_strength`는 날짜 단위로 저장돼 있어 PIT 사용은 가능하지만, 이를 latest-only 형태로 소비하는 코드 경로와 혼용되면 위험하다.
- label 계산 로직이 아직 없으므로, 이후 구현 시 feature 생성과 label 생성을 같은 step에서 섞으면 누수가 생길 가능성이 높다.
- `market_breadth.py`는 계산 함수는 있으나 DB materialization이 없고, 현재 `market` 인자를 실제 universe 필터에 반영하지 않는다. 그대로 regime source로 쓰면 KOSPI/KOSDAQ 분리 정합성이 약하다.

### 성능/유지보수 이슈

- 주간 RS 생성은 날짜별 `SELECT *` 후 pandas rank 계산이라 단순하지만, research 파생 테이블이 늘어나면 한 DB에 계속 적층하는 구조는 write time과 file size가 커질 수 있다.
- `stock_meta`는 전체 `DELETE` 후 재적재한다. 최신 snapshot이라 문제는 작지만, research history table까지 같은 패턴을 적용하면 rebuild 비용이 급증한다.
- daily/weekly 생성은 `Name` 기준 natural key를 사용한다.
  - 종목명 변경 시 historical consistency가 깨질 수 있으므로 research layer에서는 `code` 중심 key가 더 안전하다.
- registry는 lazy singleton DataFrame이며 thread-safe initialization을 앱 lifespan에서 보완하고 있다. research builder도 이 전제에 맞춰 same-process build를 유지하는 편이 안전하다.

### 스키마/인덱스 개선 포인트

- research layer는 `PRIMARY KEY(code, date[, setup_type])` 중심으로 설계해야 한다.
- 학습 쿼리용 인덱스가 추가로 필요하다.
  - `(date)`
  - `(setup_type, date)`
  - `(label_horizon, date)`
  - `(market, date)` 또는 `(market_regime, date)`
- lineage 추적용 `build_runs` 또는 `asof_date`, `source_daily_date`, `source_weekly_date`가 필요하다.

## 4) Proposed Research DB Architecture

### 권장 배치 방식

- 기존 유지
  - `stock_data_daily.db`
  - `stock_data_weekly.db`
- 신규 추가
  - `stock_research.db`

이 선택의 장점은 아래와 같다.

- 기존 API/화면/테스트 영향 최소화
- research 전용 rebuild를 실패시켜도 기존 서비스 DB는 손상되지 않음
- 대용량 파생 테이블, 인덱스를 별도 파일로 관리 가능
- build 단계에서 daily/weekly를 `ATTACH DATABASE`로 읽기만 하면 됨

### 신규 구조 제안

#### A. `market_regime`

목적:
- 날짜별 시장 상태 저장
- feature 입력, validation split, 성과 stratification에 사용

권장 key:
- `date`, `market`, `frequency`

핵심 컬럼:
- `date`
- `market` (`KOSPI`, `KOSDAQ`, `ALL`)
- `frequency` (`daily`, `weekly`)
- `index_close`
- `index_sma10_w`, `index_sma20_w`, `index_sma40_w`
- `pct_above_sma50_proxy`
- `pct_above_sma200_proxy`
- `nh_nl_ratio`
- `ad_ratio`
- `breadth_score`
- `cycle_phase` (`bull`, `sideways`, `bear`)
- `choppy_flag`
- `regime_score`
- `source_weekly_date`

생성 로직:
- weekly DB 기준으로 계산
- 초기 버전은 `my_chart/analysis/market_breadth.py` 로직 재사용
- 단, KOSPI/KOSDAQ별 universe 필터를 먼저 보강한 뒤 materialize

#### B. `universe_snapshot`

목적:
- 특정 날짜 기준 tradable universe와 exclusion reason 저장
- survivorship bias 완화의 최소 기반

권장 key:
- `code`, `date`

핵심 컬럼:
- `code`, `name`, `date`
- `market`
- `is_in_registry`
- `has_daily_price`
- `has_weekly_price`
- `close`
- `volume_won`
- `market_cap`
- `eligible_basic`
- `eligible_liquidity`
- `eligible_price`
- `eligible_final`
- `exclude_reason`

생성 로직:
- daily latest row per code/date를 기반으로 universe rule 계산
- 초기에는 거래정지/상폐 이력이 없어도 `data available + min liquidity + min price` 수준으로 시작
- 이후 phase에서 상태 이력 컬럼 확장

#### C. `feature_snapshot`

목적:
- 특정 날짜 기준 학습 입력값 저장
- label과 완전 분리

권장 key:
- `code`, `date`

핵심 컬럼:
- 식별
  - `code`, `name`, `date`, `market`
- 가격/위치
  - `close`
  - `close_to_high52w`
  - `close_to_low52w`
  - `close_vs_ema10`
  - `close_vs_ema20`
  - `close_vs_sma50`
  - `close_vs_sma200`
- 변동성/수축
  - `adr20`
  - `daily_range_pct`
  - `range_pct`
  - `adr20_pct_rank_optional`
  - `vol_contract_5d`
- 거래량/유동성
  - `volume`
  - `volume20ma`
  - `volume_ratio_1d`
  - `volume_won`
- 리더십
  - `rs_line`
  - `rs_12m_rating`
  - `rs_6m_rating`
  - `rs_3m_rating`
  - `rs_line_slope_20d`
- 주봉 구조
  - `weekly_chg_1w`
  - `weekly_chg_1m`
  - `weekly_chg_3m`
  - `weekly_sma10`
  - `weekly_sma20`
  - `weekly_sma40`
  - `weekly_trend_aligned_flag`
- 메타
  - `market_cap`
  - `market_cap_bucket`
  - `sector_major`
  - `sector_minor`
- 시장 상태 join 결과
  - `regime_score`
  - `cycle_phase`
  - `choppy_flag`
- lineage
  - `source_daily_date`
  - `source_weekly_date`

생성 로직:
- daily `stock_prices` + nearest/동일 week의 weekly `stock_prices` + weekly `relative_strength` + `market_regime` + sector registry를 조합
- feature는 반드시 해당 `date` 이전/당일에 관측 가능한 값만 사용
- `stock_meta`를 source로 사용하지 않고, raw tables에서 다시 조립

#### D. `setup_events`

목적:
- 의미 있는 셋업 발생일만 별도 저장
- event-driven 학습/랭킹 기준 제공

권장 key:
- `code`, `date`, `setup_type`

핵심 컬럼:
- `code`, `name`, `date`
- `setup_type`
  - `breakout`
  - `contraction`
  - `ema10_pullback`
  - `ema20_pullback`
  - `rs_leader_near_high`
- `setup_score`
- `trigger_price`
- `pivot_price`
- `stop_reference_price`
- `is_valid_setup`
- `setup_rule_version`

생성 로직:
- `feature_snapshot` 기반 규칙 판정
- 초기 버전은 deterministic rules로 materialize
- 이후 모델 score가 생기면 별도 scoring table로 분리

#### E. `forward_labels`

목적:
- 미래 성과를 strict label layer로 저장

권장 key:
- `code`, `event_date`, `label_horizon`, `label_type`

핵심 컬럼:
- `code`
- `event_date`
- `entry_price_basis` (`close`, `next_open`, `pivot_break`)
- `label_horizon` (`5d`, `10d`, `20d`)
- `ret`
- `mfe`
- `mae`
- `hit_plus_8pct`
- `hit_minus_4pct`
- `breakout_success_flag`
- `first_hit_up_day`
- `first_hit_down_day`
- `label_cutoff_date`

생성 로직:
- daily future bars만 사용
- event row 또는 feature row와 물리적으로 분리 저장
- 초기 구현은 `setup_events` 기준 label 생성
- 확장 시 full `feature_snapshot` 기준의 dense label도 선택 가능

#### F. `build_runs` (선택이지만 권장)

목적:
- 빌드 재현성과 디버깅

핵심 컬럼:
- `run_id`
- `started_at`, `finished_at`
- `daily_db_path`, `weekly_db_path`, `research_db_path`
- `latest_daily_date`, `latest_weekly_date`
- `status`
- `rows_feature_snapshot`
- `rows_setup_events`
- `rows_forward_labels`
- `rule_version`

### 권장 뷰

- `v_event_training_samples`
  - `setup_events` + `feature_snapshot` + `forward_labels` + `market_regime`
- `v_latest_setup_candidates`
  - 가장 최근 date 기준 actionable event 모음
- `v_feature_snapshot_latest`
  - 최신 snapshot 탐색용

## 5) Recommended Build Flow

권장 최종 배치 순서:

1. weekly `stock_prices`
2. weekly `relative_strength`
3. daily `stock_prices`
4. daily `stock_meta`
5. research `market_regime`
6. research `universe_snapshot`
7. research `feature_snapshot`
8. research `setup_events`
9. research `forward_labels`
10. research `build_runs` finalize

이 순서를 권장하는 이유:

- 기존 운영 경로(1~4)는 그대로 둔다.
- research 단계는 원천 DB를 읽기만 하므로 독립적이다.
- `feature_snapshot -> setup_events -> forward_labels`가 의존 순서상 자연스럽다.

## 6) Phase-by-Phase Implementation Plan

### Phase 1: `market_regime` + `forward_labels`

구현 난이도:
- 중

기대 효과:
- 시장 상태와 미래 성과가 분리 저장되며, 가장 먼저 학습/검증 골격이 생긴다.

범위:
- 신규 `stock_research.db`
- `market_regime`
- `forward_labels`
- 기초 `build_runs`

변경 범위:
- `my_chart/config.py`: research DB path 상수 추가
- `backend/services/db_service.py`: research phase hook 추가
- 신규 research builder 모듈

리스크:
- label 정의가 전략 철학과 직접 연결되므로 스펙 조율 필요
- `market_breadth.py`의 market filtering을 먼저 보강해야 regime 품질 확보 가능

우선순위:
- 최고

### Phase 2: `feature_snapshot` + `setup_events`

구현 난이도:
- 중상

기대 효과:
- event-driven 학습 데이터셋이 완성된다.
- 규칙 기반 후보군 생성 + ML 기반 점수화의 실제 입력 구조가 생긴다.

범위:
- `feature_snapshot`
- `setup_events`
- `v_event_training_samples`

변경 범위:
- 신규 feature/event 생성 모듈
- possibly `market_regime` join 규칙 고정

리스크:
- feature 수가 빠르게 늘어나며 관리가 어려워질 수 있다.
- weekly 값을 daily date에 매핑하는 규칙(같은 주/직전 주)을 명확히 고정해야 한다.

우선순위:
- 높음

### Phase 3: `universe_snapshot` + survivorship/backtest 보강

구현 난이도:
- 상

기대 효과:
- validation/backtest 신뢰도가 올라간다.
- 실전 매매 연결성 강화

범위:
- `universe_snapshot`
- 거래 가능성 / 제외 사유 기록
- 향후 거래정지/상폐/관리종목 이력 수용 구조

변경 범위:
- 외부 입력 데이터 소스 추가 검토 가능
- universe builder 및 테스트 확대

리스크:
- 현재 코드베이스에는 status history 원천이 없다.
- 외부 데이터 품질/갱신 정책이 없으면 반쪽 구조가 될 수 있다.

우선순위:
- 중

## 7) Migration Strategy

### 핵심 원칙

- 기존 `stock_data_daily.db`, `stock_data_weekly.db`, `stock_meta`는 호환성 유지
- research layer는 additive하게 구축
- 기존 `/api/db/update`를 유지하되 내부 배치만 확장

### 권장 방식

- 새 DB 파일 `stock_research.db` 생성
- research builder에서
  - `ATTACH DATABASE daily`
  - `ATTACH DATABASE weekly`
  - 필요 시 자기 자신(research) write
- 생성 대상은 full rebuild 또는 date-based incremental rebuild

### SQLite 현실화 전략

- WAL 사용
- `executemany` batch insert 유지
- wide table은 materialized table로 저장하고, 최종 소비용 join은 view로 얇게 제공
- 핵심 PK/보조 index만 우선 생성
- 초기에 너무 많은 secondary index를 만들지 말고, 실제 학습 쿼리 후 병목 기준으로 추가

### 업데이트 시간 45초 훼손 최소화 전략

- 기존 1~4단계는 건드리지 않는다.
- research phase는 원천 DB fetch가 아니라 local SQLite read/derive만 수행한다.
- 초기 full rebuild 허용, 이후 incremental 전환
  - `market_regime`: 새 weekly date만 append
  - `feature_snapshot`: 새 daily date만 append
  - `setup_events`: 새 daily date만 append
  - `forward_labels`: horizon이 닫힌 날짜까지만 append/update
- 장기적으로는 `build watermark` 테이블을 두고 마지막 처리 date를 관리

## 8) File-Level Change Plan

### 기존 파일 수정 예상

- `backend/services/db_service.py`
  - research build phase 추가
- `my_chart/config.py`
  - `DEFAULT_DB_RESEARCH` 추가
- `backend/routers/db.py`
  - 필요 시 `/db/last-updated` 응답에 research build timestamp 추가 검토
  - 초기 단계에서는 필수 아님

### 신규 모듈 제안

- `my_chart/research/__init__.py`
- `my_chart/research/schema.py`
  - research DB DDL 관리
- `my_chart/research/build.py`
  - 전체 research build orchestration
- `my_chart/research/market_regime.py`
- `my_chart/research/universe.py`
- `my_chart/research/features.py`
- `my_chart/research/events.py`
- `my_chart/research/labels.py`
- `backend/services/research_db_service.py`
  - 선택 사항
  - `db_service.py`를 얇게 유지하려면 분리 권장

### 테스트 파일 제안

- `tests/test_research_schema.py`
- `tests/test_research_market_regime.py`
- `tests/test_research_features.py`
- `tests/test_research_events.py`
- `tests/test_research_labels.py`
- `tests/test_research_build.py`

## 9) SQL / DDL Draft (초안 수준)

### `market_regime`

```sql
CREATE TABLE IF NOT EXISTS market_regime (
    date TEXT NOT NULL,
    market TEXT NOT NULL,
    frequency TEXT NOT NULL,
    index_close REAL,
    pct_above_sma50_proxy REAL,
    pct_above_sma200_proxy REAL,
    nh_nl_ratio REAL,
    ad_ratio REAL,
    breadth_score REAL,
    cycle_phase TEXT,
    choppy_flag INTEGER,
    regime_score REAL,
    source_weekly_date TEXT,
    PRIMARY KEY (date, market, frequency)
);
```

### `feature_snapshot`

```sql
CREATE TABLE IF NOT EXISTS feature_snapshot (
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    market TEXT,
    close REAL,
    close_to_high52w REAL,
    close_vs_ema10 REAL,
    close_vs_ema20 REAL,
    close_vs_sma50 REAL,
    close_vs_sma200 REAL,
    adr20 REAL,
    volume_ratio_1d REAL,
    volume_won REAL,
    rs_12m_rating REAL,
    rs_6m_rating REAL,
    rs_3m_rating REAL,
    weekly_trend_aligned_flag INTEGER,
    market_cap REAL,
    market_cap_bucket TEXT,
    sector_major TEXT,
    sector_minor TEXT,
    regime_score REAL,
    cycle_phase TEXT,
    choppy_flag INTEGER,
    source_daily_date TEXT,
    source_weekly_date TEXT,
    PRIMARY KEY (code, date)
);
```

### `setup_events`

```sql
CREATE TABLE IF NOT EXISTS setup_events (
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    setup_type TEXT NOT NULL,
    setup_score REAL,
    trigger_price REAL,
    pivot_price REAL,
    stop_reference_price REAL,
    is_valid_setup INTEGER,
    setup_rule_version TEXT NOT NULL,
    PRIMARY KEY (code, date, setup_type)
);
```

### `forward_labels`

```sql
CREATE TABLE IF NOT EXISTS forward_labels (
    code TEXT NOT NULL,
    event_date TEXT NOT NULL,
    label_horizon TEXT NOT NULL,
    label_type TEXT NOT NULL,
    entry_price_basis TEXT NOT NULL,
    ret REAL,
    mfe REAL,
    mae REAL,
    hit_plus_8pct INTEGER,
    hit_minus_4pct INTEGER,
    breakout_success_flag INTEGER,
    label_cutoff_date TEXT,
    PRIMARY KEY (code, event_date, label_horizon, label_type, entry_price_basis)
);
```

## 10) Validation / Test Plan

### 기능 검증 포인트

- 기존 `/api/db/update`가 여전히 정상 완료되는지
- 기존 `/api/screen`, `/api/chart`, `/api/sectors`가 영향 없이 동작하는지
- research build 실패 시 기존 daily/weekly/meta는 usable 상태인지

### 데이터 정합성 검증 포인트

- `feature_snapshot.date` 기준으로 future-derived 값이 없는지
- `forward_labels`가 오직 `event_date` 이후 bar만 사용하는지
- weekly feature를 daily date에 붙일 때 look-ahead가 없는지
- `code/date` row count가 예상 universe와 일치하는지

### 성능 검증 포인트

- 기존 4단계 소요 시간 변화
- research build 추가 후 전체 소요 시간
- DB file size 증가량
- 학습용 주요 query latency

### 회귀 테스트 우선순위

- `tests/test_db_service.py`
- `tests/test_meta_service.py`
- `tests/test_market_breadth.py`
- 신규 research builder tests

## 11) Recommended Decisions Before Coding

코드 작성 전에 아래 항목은 먼저 고정하는 것이 좋다.

1. research layer를 `별도 DB`로 갈지, daily DB 내 추가 테이블로 갈지
   - 본 계획은 `별도 DB`를 권장
2. event 정의의 최소 버전
   - `breakout`, `contraction`, `ema10_pullback`, `rs_leader_near_high`
3. label 기준 가격
   - `당일 종가`, `익일 시가`, `pivot breakout price` 중 무엇을 정답 기준으로 삼을지
4. weekly 값을 daily에 매핑하는 규칙
   - `해당 일자가 속한 최신 확정 주봉`으로 고정 권장
5. universe 최소 필터
   - 가격, 거래대금, 데이터 보유 기간 기준

## 12) Final Recommendation

- 구현은 `기존 4단계 유지 + research DB 추가`로 가는 것이 가장 안전하다.
- 첫 구현은 `market_regime`, `forward_labels`, `build_runs`로 시작해 label/validation 기반을 먼저 만들고,
- 다음 단계에서 `feature_snapshot`, `setup_events`를 추가해 event-driven 학습 구조를 완성하는 순서가 가장 현실적이다.
- `stock_meta`는 계속 조회용 최신 스냅샷으로 남기고, 학습용 구조는 raw daily/weekly 기준으로 별도 materialization 해야 한다.
