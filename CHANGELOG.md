# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (SPEC-SECTOR-GRID-001 v0.2.2, 2026-08-12)

- **섹터 분석 기반 계층 — 정규 주간 격자·유니버스·적재 보호** (M0~M6, `run_commit_sha` `1f62beb`)
  - 신규 모듈 `my_chart/analysis/weekly_grid.py`: `compute_weekly_grid()` — 주봉 원시 날짜(다중 날짜 주·부분 데이터 포함)를 정규화해 ISO 주당 1바 격자 산출
    - CG-1(ISO 주 그룹핑, 대표 = `MAX(Date)`), CG-2(진행 중인 주 `is_partial_week` 분리), CG-3(중앙값 50% 미만 배제 + `grid_exclusions[]`)
    - `anchor(t, days)` 달력 앵커링(1W/1M/3M/6M/12M/52W), `history(weeks=N)`, `grid_version = "canonical-v1"` 상수
    - 공유 헬퍼 `_get_latest_valid_date()` — 자체 기준일 조회 재도입 방지(REQ-SGR-005)
  - 신규 모듈 `my_chart/analysis/universe.py`: `compute_universe()` — 유효 유니버스(4중 교집합: registry ∩ stock_meta ∩ 최신바가격 ∩ 비-stale) + 진단(`registry_only`, `duplicates`, `stale_names`)
    - registry `Code` 기준 중복 제거(UN-4) + WARNING 로그, stale 판정(일봉 `MAX(Date)` 기준 14일 초과, `last_updated` 미사용, UN-5)
    - 미분류 섹터 센티널 `ETC_SECTOR = "기타"` 단일화(REQ-SGR-017)
  - `my_chart/db/weekly.py`: weekly INSERT를 positional → **column-name** 방식으로 전환(`stock_prices`, `relative_strength` 각 1건, Lesson #8 legacy-ALTER round-trip 게이트) + 주중 재적재 supersede(`--no-supersede` 안전장치 포함)
  - 7개 기준일 소비자(`sector_ranking_service.py`, `stage_service.py`, `market_service.py`, `meta_service.py`, `sector_advanced_service.py`, `sector_advanced.py`, `sector_metrics.py`)를 공유 격자 헬퍼로 수렴(TG-5)
  - **AC-SGR-001~021 전항 PASS (21/21)** — 프로즌 픽스처(`tests/fixtures/frozen/weekly-2026-08-12/`) 위에서 게이팅, 대조 단언(falsification) 7종 전부 GREEN
  - 검증: SPEC 스코프 gating 69 passed (`test_weekly_grid.py` / `test_consumer_dates.py` / `test_weekly_insert.py` / `test_weekly_supersede.py` / `test_universe.py` / `test_regression_sgr020.py`), 전체 회귀 `pytest tests/ --ignore=tests/fnguide` 475 passed / 8 failed(SPEC 범위 밖 기존 결함 — `test_api`/`test_meta_service`/`test_rs_line`/`test_screen_service`)
  - 성능: 격자 캐시 적중 0.003~0.005ms(목표 <5ms 대비 ~1000× 여유), 캐시 미적중(콜드) 635~803ms(목표 P95<50ms 미달이나 spec §0.2 처방 완화(`(db_path, mtime)` 메모이즈)가 이미 M1에 구현되어 있어 프로세스당 1회 콜드 비용으로 완화됨)
  - **회귀처럼 보이지만 올바른 변화** (`.moai/specs/SPEC-SECTOR-GRID-001/release-notes.md` 참고): rank 순위 이동, 1주 초과수익률 양수 섹터 29→18, 52주 신고가 종목 99→56, 게임 섹터 구성종목 33→32(중복 제거) 등 — 전부 AC-SGR-020 R1~R5로 기대값 고정, 되돌림 금지

### Fixed (SPEC-SECTOR-GRID-001 v0.3.0 — in-place amendment, 2026-08-12)

- **반증력(falsifiability) 복구 — 위 v0.2.2 릴리스의 테스트/AC 문서 결함 수정. 프로덕션 동작은 변경 없음.**
  - **배경**: 위 v0.2.2 종료 후 sync-auditor 독립 감사가 **PASS-WITH-DEBT 78.6/100**(Functionality 78 / Security 92 / Craft 72 / Consistency 75, BLOCKING 0 / SHOULD-FIX 6 / MINOR 6)을 반환했다. 핵심 소견: progress.md §E.2가 "대조 단언(falsification) 7종 전부 GREEN"이라 기록했으나, 실제로는 **진짜 4종 / 공허 3종**이었다 — 공허한 3종은 구현을 완전히 되돌려도 동일하게 GREEN이라 아무것도 반증하지 못했다. 사용자 승인 후 SPEC을 `completed → in-progress`로 되돌려 in-place amendment를 진행했다(`amendment_of: SPEC-SECTOR-GRID-001`, `prior_completed_sha: 95e0980`).
  - **1단계 — SPEC 본문 개정** (commit `2140cd6`, manager-spec, spec.md + acceptance.md 192+/47−): AC-SGR-005 정적 스캔 규범 명령이 유효한 bash가 아니었던 결함(줄바꿈 이음 누락 → `bash -n` exit 2)을 복구하고 잔류 집합 검증 방식을 제외 정규식 연쇄에서 **집합 동등 비교**로 전환, allowlist 실행 쿼리 상한을 6→**5**로 축소(공허했던 `chart_service.py` 항목 제거, 실측 `grep -c` → 0), AC-SGR-020 R5를 수학적 항진명제(`len(history) <= len(raw)`, 격자가 원시에서 선별되므로 어떤 구현에서도 참)에서 프로즌 리터럴 `345` 기준 엄격 부등으로 재기술, AC-SGR-004를 프로즌 적용 대상에서 **합성 픽스처 게이팅** 대상으로 재분류(라이브 실측 `exclusions == []`로 CG-3가 프로즌 픽스처 위에서 한 번도 발화하지 않음을 확인), §1.2.1 행 번호 드리프트 정정 + 판정 키를 매칭 텍스트로 전환, O-G6(`market_breadth.py:472` TG-4 오계산) 심각도 상향.
  - **2단계 — 테스트 반증력 실질화** (commit `a61c3c1` + backfill `e07ae36`, manager-develop, 4개 테스트 파일 + pyproject.toml + progress.md §E.2/§E.3, 689+/79−): F1(AC-SGR-021 센티넬 발산 차단 — 테스트 내부에서 동일 식 2회 비교하던 것을 프로덕션 코드 실호출로 교체), F2(AC-SGR-006-A 6지점 개별 되돌림 — A-4/A-6가 공유 헬퍼를 그대로 재호출해 실질 4-way였던 것을 6-way 전부로 복구), F3(AC-SGR-020 R5 항진명제 해소)을 되돌린 변형에서 실제 RED가 관측되도록 복구, F6(AC-SGR-005.2 규범 명령 실행), F7(AC-SGR-004 CG-3 재분류에 맞춘 게이팅 픽스처 전환)도 함께 실질화. **구현 코드는 한 줄도 수정하지 않았다** — `git diff --stat 2140cd6..HEAD -- my_chart/ backend/ frontend/`가 빈 diff(테스트/문서/설정 전용 변경).
  - **검증**: 게이팅 6파일 M6 69 passed → **84 passed**(+15, 전부 M7 신규 단언). 전체 회귀 `pytest tests/` baseline 569 passed / 8 failed / 25 errors → **584 passed**(+15, 정확히 신규분과 일치) / 8 failed(동일 목록, 본 SPEC 범위 밖 기존 결함) / 25 errors(동일, `tests/fnguide/`) — **회귀 0건**. 커버리지(DoD §4 게이트, `>= 85%`): `my_chart/analysis/weekly_grid.py` **100%**(94/94), `my_chart/analysis/universe.py` **100%**(56/56).
  - **미결로 남긴 것(REQ/AC 개정 소관, 본 커밋 범위 밖)**: (a) NULL `산업명(대)`가 pandas에서 `NaN`으로 승격되면 `NaN or ETC_SECTOR`가 NaN의 truthy 성질 때문에 센티넬 분기를 타지 않고 섹터 키가 `'nan'`이 된다(두 소비 경로 모두 동일값이라 AC-SGR-021의 "두 경로 일치" 게이팅 요건 자체는 성립 — 정규화 여부만 미결). (b) AC-SGR-004 본문의 "한 ISO 주 안에 두 날짜" 문구를 문자 그대로 구성하면 그 주가 통째로 격자에서 빠지는 경우가 있으며, AC 명시 `구성 예`만 게이팅 대상으로 채택함.

### Changed (SPEC-SECTOR-MINOR-COLOR-001 v1.0.1, 2026-05-27)

- **StockBubbleChart 종목 버블 차트 색상·범례 인코딩 교체** (commits `bebd3f1`, `7c5be67`)
  - 이전: Weinstein Stage 4-항목 (S1 바닥/S2 상승/S3 천장/S4 하락 + 미분류) 기반 색상 매핑 + 정적 5-항목 범례
  - 이후: sector_minor (산업명(중)) 기반 동적 색상 매핑 (Tableau 10 변형) + 동적 범례 (count desc, name asc, "기타" 마지막, palette overflow 흡수)
  - 색상 결정성 보장 (정렬 키 명시 + rerender() 2-pass round-trip 단언)
  - multi-series 변환으로 ECharts 표준 legend click toggle + hover emphasis 자동 동작
  - 모바일 viewport (<768px) fallback: 범례 하단 horizontal scroll, grid.right=60 / grid.bottom=80 (차트 영역 prominence 우선)
  - tooltip XSS hardening: escapeHtml 적용 (defensive coding, KRX 내부 DB 신뢰)
  - 신규 useMediaQuery hook (외부 라이브러리 무도입, SSR 가드 + cleanup listener)
  - Stage 정보는 tooltip `Stage: S{n} ({stage_detail})` 라인으로 보존 (REQ-SBM-008 회귀 방지)
  - 검증: pytest 39/39 PASS, vitest 85/85 PASS, coverage StockBubbleChart 90% / useMediaQuery 85.71%, tsc + ESLint 0 errors
  - evaluator-active Cycle 2 PASS (0.88/1.00): Functionality 92, Security 95, Craft 80, Consistency 90
  - 라이브 PASS: AC-4 sector_minor 색상 / AC-5 동적 범례 10그룹 (반도체 섹터) / AC-7 hover emphasis dim / AC-8 산업명(중) tooltip + Stage 보존
  - 후속: AC-12 200+ 종목 P95 baseline 측정은 라이브 measure pending (acceptance.md 명시 허용)

### Added (SPEC-STOCK-TOOLTIP-PRODUCT-001 v1.0.0, 2026-05-27)

- **StockBubbleChart tooltip 주요제품 라인 추가** (commit `b2ef257`)
  - tooltip에 `주요제품: {value or "—"}` 라인 추가 (산업명(중) 라인 다음, Stage 라인 위)
  - 데이터 소스: `Input/sectormap-original.xlsx` 산업명(대)/산업명(중)/**주요제품** 중 마지막 컬럼 → `stock_meta.product`
  - Backend: `_get_stock_meta` SELECT 7-컬럼 확장 (sector_minor + product), `StockBubble.product`, `StockBubbleItem.product`, `compute_stock_bubble`/`get_stock_bubble` 전파
  - Frontend: `bubble.ts`에 `product: string | null` 타입 미러, tooltip formatter `productLabel` (escapeHtml 적용), data 객체에 product 보존
  - NULL/빈 product → `주요제품: —` fallback 표시
  - AC-6 회귀 게이트: 직전 SPEC 산업명(중) 색상·범례·Stage tooltip 모두 보존 단언
  - 검증: pytest 42/42 PASS (+3), vitest 97/97 PASS (+12), tsc + ESLint 0 errors
  - 라이브 PASS: backend uvicorn `--reload` 재시작 후 tooltip 주요제품 라인 정상 표시 (사용자 확인)
  - 운영 lesson: uvicorn dev server reload 명시 필요 (CLAUDE.local.md 강조 점)

### Changed (chore — sectormap unification, 2026-05-12)

- **`Input/sectormap-original.xlsx` 단일 source 통합** (commit `face1ac`)
  - 이전: `Input/sectormap.xlsx`(6 컬럼 추출본, 2552 종목) + `Input/sectormap_original.xlsx`(원본, 백업) 이중 관리
  - 이후: `Input/sectormap-original.xlsx`(원본 53 컬럼, 2556 종목) 단일 source. `sectormap.xlsx` 폐기
  - `my_chart/config.py`: `SECTORMAP_PATH` → `sectormap-original.xlsx`
  - `my_chart/registry.py:_load_sectormap()`:
    - `header=8` (앞 row 0~7은 데이터 설명 주석)
    - 한글/개행 컬럼명 → 영문 rename (`종목\n코드`→`Code`, `종목명`→`Name`, `시장`→`Market`)
    - 6 컬럼만 select (53 → 6, 메모리 88% 절약)
    - downstream 코드(`get_stock_registry`, `get_sector_registry`, `meta_service`, `sector_advanced`, `stage_service`, `screen_service`) 변경 0
  - 종목 데이터: 2552 → 2556 (+13 신규 KONEX/SPAC, -9 구버전 폐지). 6 핵심 컬럼 99.5%+ 일치 (Market 1건만 시장 이동 차이)
  - 검증: pytest `tests/test_config.py` 10/10 PASS + registry load 정상 + backend `/api/stocks/master` HTTP 200
  - Follow-up (운영): backend dev server reload + `meta_service.rebuild_stock_meta()` 실행으로 stock_meta 테이블 갱신 필요

### Added (SPEC-NAVER-THEME-001)

- **네이버 금융 테마 분석 모듈** (SPEC-NAVER-THEME-001 v1.0.0)
  - 신규 5번째 탭: **테마 분석** (Theme Analysis)
  - 네이버 금융 테마 페이지(finance.naver.com/sise/theme.naver) read-only 크롤링
  - 백엔드 모듈: `backend/services/naver_theme/` (config, crawler, parser, analyzer, db_join, service, schemas)
    - 단일 진입점: `from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult`
    - EUC-KR 인코딩 강제 처리, SQLite read-only JOIN (`mode=ro`), 매너 크롤링(sleep ≥ 0.7s)
  - 신규 REST API 엔드포인트:
    - `GET /api/themes/snapshot?top_n=20&leaders_per_theme=3` — 5종 records list + metadata (~30s)
    - `GET /api/themes/quick?top_n=20` — themes + strong_themes + metadata (≤10s)
  - 테마 분석 결과 구조:
    - `themes_df`: theme_id, theme_name, change_pct, change_pct_3d, up/flat/down_count, top_stocks_preview
    - `strong_themes_df`: 위 + momentum_score, breadth_ratio
    - `stocks_df`: theme_id, stock_code/name, inclusion_reason, price, change/_pct, volume, trade_value, market_cap, per/roe(NaN)
    - `leaders_df`: 가중치 z-score(0.40/0.30/0.20/0.10) 기반 테마별 상위 K개
    - `multi_theme_stocks_df`: 2개 이상 테마 등장 종목
  - 신규 의존성 없음: 기존 requests, beautifulsoup4, lxml, pandas, numpy 활용 (REQ-NT-C-003)
  - 기존 4탭 회귀 0건 (AC-12): surgical mod 9줄 추가 (≤10줄 제한, AC-14)
  - 단위 테스트 51개, 커버리지 99%
  - V2 핸드오프 노트: `.moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md` (모바일 stock.naver.com 기반 SPEC 작성 용도)
  - **비개발자용 종합 가이드**: [docs/theme-analysis-guide.md](docs/theme-analysis-guide.md) — V1→V2 변천사, 4가지 결정(D-1~D-4) 친절 설명, FAQ, 용어집

### Added (SPEC-NAVER-THEME-002)

- **네이버 모바일 m.stock.naver.com 기반 V2 backend 모듈** (SPEC-NAVER-THEME-002 v1.0.1)
  - **V1+V2 cohabitation 정책**: V1 desktop HTML 모듈 무수정 + V2 mobile JSON API 신규 모듈
  - **신규 모듈**: `backend/services/naver_theme_v2/{__init__,service,crawler,parser,config}.py` (5 모듈)
  - **신규 REST API 엔드포인트**:
    - `GET /api/themes/v2/snapshot?top_n=20&leaders_per_theme=3` — V2 mobile JSON 기반 5종 records list + metadata (~30s, V1 shape 호환)
    - `GET /api/themes/v2/quick?top_n=20` — V2 themes only (≤10s)
  - **ThemeAnalysisResult shape**: V1과 동일 (frontend forward-compat) — `themes_df`, `strong_themes_df`, `stocks_df`, `leaders_df`, `multi_theme_stocks_df`
  - **신규 의존성 0건** (REQ-NT2-C-004): 기존 requests/pandas/numpy/pydantic/fastapi 활용
  - **bare except 0건** (REQ-NT2-C-005): RequestException, Timeout, JSONDecodeError, ValidationError 등 specific exception만 catch
  - **v1.0.1 amendment** (commit b1c24eb): V1 컬럼 호환성 검증 강화 + acceptance.md 14-AC 정정
  - **race condition fix** (ba3f20c): ThemeAnalysis.tsx useEffect cleanup 패턴 (V2와 무관, 본 SPEC과 함께 ship)
  - **단위 테스트**: 24개 pytest PASS + 라이브 1개 PASS (`@pytest.mark.live test_collect_and_analyze_v2_live`)
  - **V1 routes 정책**: V1 endpoints `/api/themes/snapshot`, `/api/themes/quick` 등록 유지 — cohabitation rollback 경로
  - **비개발자용 종합 가이드**: [docs/theme-analysis-guide.md](docs/theme-analysis-guide.md) — V1→V2 변천사, cohabitation 정책, FAQ

### Added (SPEC-NAVER-THEME-003)

- **V2 frontend 채택 + theme_description tooltip + V2 metadata V1 alias** (SPEC-NAVER-THEME-003 v1.0.0)
  - **V2 endpoint URL swap**: `frontend/src/api/themes.ts` 가 V2 endpoint 호출 (REQ-NT3-001)
  - **TypeScript 타입 확장**: `ThemeItem.theme_description?`, `ThemeStockItem.stock_description?` optional 필드 (REQ-NT3-002, REQ-NT3-003)
  - **ThemeRankingTable hover tooltip** (D-2): theme_name 셀에 native HTML title 속성 (REQ-NT3-004)
  - **null/undefined/empty 정책** (D-4): title 속성 자체 미렌더링 — 노이즈 회피 (REQ-NT3-NF-002)
  - **ThemeAnalysis 에러 메시지 + retry 버튼** (D-1): V2 503/timeout 시 사용자 친화적 메시지 + 수동 retry. retryNonce trigger + race-safe cleanup 보존 (REQ-NT3-007). V1 자동 폴백 금지 (REQ-NT3-C-006).
  - **ThemeDetailPanel 무수정** (D-3): V2 parser inclusion_reason ← item.description 정책으로 자동 호환 (REQ-NT3-008)
  - **V2 backend metadata V1 alias**: `collected_at`, `theme_count`, `stock_count`, `elapsed_sec` 4 필드 additive 추가 (REQ-NT3-005, REQ-NT3-C-003). `_empty_result` 에도 동일 적용 (REQ-NT3-006).
  - **검증**: V1 51 PASS (회귀 0, REQ-NT3-C-002) + V2 24+5=29 PASS + frontend vitest 271 PASS (baseline diff 0, ChartGrid 1 fail pre-existing)
  - **evaluator-active PASS**: Functionality 100 / Security 90 / Craft 92 / Consistency 95
  - **신규 의존성 0건** (REQ-NT3-C-004): native HTML title 사용 (Radix Tooltip 미도입)
  - **신규 단위 테스트**: backend 5 (V2 metadata alias) + frontend vitest 4 파일 15 tests
  - **비개발자용 종합 가이드**: [docs/theme-analysis-guide.md](docs/theme-analysis-guide.md), 시리즈 회고: [.moai/learnings/SPEC-NAVER-THEME-001-003-lessons.md](.moai/learnings/SPEC-NAVER-THEME-001-003-lessons.md)
  - **v1.0.1 amendment** (D-3 reverse — UX 사용성 개선):
    - hover tooltip만으로는 description이 한눈에 안 보여 네이버 모바일 UX와 어긋난다는 사용자 라이브 검증 결과 반영
    - ThemeDetailPanel 테마명 아래 `theme_description` 본문 박스로 노출 (REQ-NT3-009 신규)
    - 주도주 카드 + 종목 테이블 각 행 뒤에 `inclusion_reason` 본문으로 펼쳐 노출 (REQ-NT3-010 신규)
    - hover tooltip(`title` 속성)은 보존 (중복 노출, AC-13 호환)
    - AC-16/17 신규 추가 (총 17 AC)
    - ThemeDetailPanel.test.tsx vitest 6 cases 추가
  - **v1.0.2 amendment** (주도주 섹션 제거 + theme_description prominent 강화):
    - 사용자 후속 신고: 테마명 직후 "주도주" 섹션이 가장 위에 위치해서 네이버 모바일의 "테마 설명 우선" UX와 어긋남
    - ThemeDetailPanel 주도주(themeLeaders) 섹션 완전 제거 (REQ-NT3-011 신규)
    - theme_description 본문 박스 스타일 강화: font-size 12→13px, color text-secondary→text-primary, padding 8/12→12/14, border-radius 6→8, border-left 3px→4px (REQ-NT3-009 강화)
    - leaders prop은 호출부 호환을 위해 optional로 유지하되 컴포넌트 내부에서 미사용
    - RankBadge 함수 미사용으로 제거
    - AC-18 신규 추가 (총 18 AC)
    - ThemeDetailPanel.test.tsx vitest 7 cases (AC-13 1 + AC-16 2 + AC-17 2 + AC-18 2)
  - **v1.0.5 amendment** (탭 전환 재 fetch 해결 — frontend localStorage 캐시 + 명시적 갱신 버튼):
    - 사용자 신고: "한 번 크롤링 했는데 다른 메뉴 갔다오면 왜 다시 크롤링을 하느라 시간을 쓰지?"
    - Root cause: backend/frontend 양쪽 캐시 0건. AppContent는 CSS display:none/flex 토글로 mount 보존되지만, 사용자가 빠른/전체 조회 모드 버튼 토글 시 매번 useEffect 재실행 → 30초 재크롤링. 페이지 새로고침 시에도 자동 30초 fetch.
    - 사용자 사용 패턴 (혼자 사용 + Chart Grid DB 수동 업데이트와 동일 모델) 반영해서 자동 fetch 최소화 + 명시적 갱신 모델로 전환
    - 해결: ThemeAnalysis.tsx에 (1) `theme-analysis-cache-{quick|full}` localStorage 캐시 — mount/mode 변경 시 cache 우선 읽기 → cache hit이면 fetch skip + 즉시 표시 (REQ-NT3-015 신규), (2) 툴바에 `🔄 갱신` 버튼 추가 (data-testid="theme-refresh-button") — 클릭 시 현재 mode 캐시 무효화 + 강제 fetch + 응답을 캐시에 재쓰기 (REQ-NT3-016 신규)
    - 캐시 schema: `{cache_version: 'v1', saved_at: ISO-8601, data: ThemesSnapshotResponse}`. cache_version mismatch 시 자동 무효화 → 향후 backend schema 변경 대비
    - 자동 만료 없음 (수동 갱신 모델). 갱신 버튼만 trigger
    - AC-22/23/24 신규 (총 24 AC). ThemeAnalysis.test.tsx vitest 3 cases 추가 (mount cache hit / refresh button / mode별 cache key 분리)
    - **수정 범위**: ThemeAnalysis.tsx 1 파일 + 테스트 1 파일. backend 무수정, V1 무수정, 의존성 변경 0
    - **검증**: vitest 284/285 PASS (ChartGrid 1 fail pre-existing baseline 동일, REQ-NT3-NF-004), 회귀 0건
  - **v1.0.4 amendment** (backend strong_themes_df description 머지 누락 수정):
    - 사용자 후속 신고: v1.0.3 default 'full' 적용 후에도 화면에 description 미노출
    - 라이브 진단 결과: backend snapshot 응답의 `themes` 배열에는 description=274자 정상이지만 `strong_themes` 배열에는 description=0(empty). frontend는 `data?.strong_themes ?? data?.themes`로 strong_themes 우선 사용 → 사용자가 클릭한 테마는 description=null인 strong_themes에서 매핑됨 → ThemeDetailPanel D-4 hidden
    - Root cause: `service.py:73`에서 `strong_themes_df = build_strong_themes(themes_df, ...)`를 detail 호출 전에 빌드, line 92-95 detail 머지가 `themes_df`에만 적용됨. v1.0.0 RUN 시점부터 잠재된 버그가 v1.0.3 default 'full'로 수면 위로
    - 해결: detail loop 종료 후 `strong_themes_df["theme_description"] = strong_themes_df["theme_id"].map(themes_df.set_index("theme_id")["theme_description"].to_dict())` 1줄 추가 (REQ-NT3-014 신규)
    - backend pytest AC-21 신규 (총 21 AC)
    - frontend 변경 0, V1 backend 무수정, 의존성 변경 0
  - **v1.0.3 amendment** (default 'full' mode + 빠른 조회 advisory):
    - 사용자 후속 신고: v1.0.2까지 본문 박스가 코드에 추가됐으나 화면에 표시 안 됨
    - Root cause: backend `service.py:92-95`가 detail 호출 시에만 `theme_description`을 themes_df에 머지. 빠른 조회 모드는 detail skip → backend가 description=null 반환 → frontend D-4 hidden 정책으로 본문 박스 미표시. parser.py 주석에도 "list 응답 sectorDescription은 항상 null" 명시되어 있고 라이브 list endpoint 호출로 재검증 완료.
    - ThemeAnalysis.tsx의 default mode를 `'quick'` → `'full'`로 변경 (REQ-NT3-012 신규). 첫 진입 시 자동 snapshot 호출 → description 정상 표시 (~30초).
    - 사용자가 "빠른 조회"를 토글한 경우 ThemeRankingTable 아래에 회색 advisory 박스 노출 — "빠른 조회 모드는 테마 설명과 종목 편입설명을 포함하지 않습니다" + "전체 조회" CTA 안내 (REQ-NT3-013 신규).
    - AC-19/20 신규 추가 (총 20 AC).
    - ThemeAnalysis.test.tsx vitest 4 cases (AC-11 1 + AC-12 1 + AC-19 1 + AC-20 1).
    - backend, V1 backend, 의존성 변경 0.

### Changed (SPEC-AI-REPORT-003)

- **AI 리포트 Fast/Deep 양쪽 모드를 Perplexity API 에서 Codex CLI 로 전면 전환** (SPEC-AI-REPORT-003 v1.0.1)
  - **Fast Mode** (`POST /api/ai-report/{code}?mode=fast`, 기본): Codex CLI subprocess + 30s heartbeat SSE + 256자 청크 스트리밍. ChatGPT 구독 기반 무료 호출 (별도 API 키 불필요, `codex login` 으로 인증).
  - **Deep Mode** (`?mode=deep`): 5소스 병렬 수집 (Codex/Brave/Tavily/Naver/YouTube) + Claude CLI 합성. 기존 Perplexity 슬롯이 Codex 슬롯으로 교체.
  - **Backward compat**: `?mode=perplexity` 는 deprecated alias → Fast Mode 로 라우팅 (warning 로그). `?mode=fast` 가 권장.
  - **신규 모듈**:
    - `backend/services/codex_cli_runner.py` — `run_codex_research()` async + `CodexResult` dataclass + `load_codex_prompt()`
    - `backend/services/ai_report_service.py::stream_codex_fast()` — Fast Mode SSE 어댑터 (heartbeat + 청크)
    - `backend/services/deep_research_collector.py::_collect_codex()` — Deep Mode codex 슬롯 (1회 재시도 + 결정론적 실패 분기)
    - `backend/services/deep_research_collector.py::prepare_staging_directory()` + `finalize_staging_directory()` — staging 2단계 분리 (Codex `--output-last-message` 가 호출 시점에 경로 필요)
    - `backend/prompts/codex_prompt.md` — Codex 전용 8섹션 프롬프트 (`〈종목명〉`/`〈종목코드〉` 플레이스홀더)
  - **NFR-001 (Codex 타임아웃)**: 단일 호출 600s + 1회 재시도 600s = 최대 1200s. `_DEFAULT_TIMEOUTS["codex"] = 1200.0` 으로 외부 timeout 보장.
  - **NFR-002 (쿼터 보호)**: `AI_REPORT_DAILY_QUOTA` 와 `AI_REPORT_DEEP_DAILY_QUOTA` 가 ChatGPT 구독 일일 한도 보호 목적으로 재정의 (값 변경 없음).
  - **삭제된 자산**:
    - `backend/services/perplexity_cache.py` (TTL 10분 캐시 레이어, Codex 대체로 불필요)
    - `backend/prompts/perplexity_prompt.md` (Codex 전용 템플릿으로 교체)
    - `ai_report_service.py` 의 `stream_perplexity`, `SYSTEM_PROMPT`, `SEARCH_DOMAIN_FILTER`, `_load_prompt_template`, `load_prompt`
    - `deep_research_collector.py` 의 `_collect_perplexity`, `_normalize_perplexity`
    - `.env.example` 의 `PERPLEXITY_API_KEY`
  - **프론트엔드**:
    - `frontend/src/types/aiReport.ts::SourceName`: `"perplexity"` → `"codex"`
    - `frontend/src/types/aiReport.ts::PhaseEvent` 에 `codex_fast_start`, `codex_fast_progress`, `staging_prepared` 이벤트 추가
    - `frontend/src/api/aiReport.ts::AiReportMode`: `"perplexity"` → `"fast"`
    - `frontend/src/components/ProgressPanel.tsx`: 라벨 `"Codex 심층 리서치"`, codex char_count KB 단위 표시
    - `frontend/src/components/AiReportModal.tsx`: 기본 mode='fast', 설명 문구에 Codex CLI 특성 (2~9분, ChatGPT 구독) 반영
  - **품질 검증**: Backend 134/134 + Frontend 19/19 PASSED. 커버리지: codex_cli_runner 81%, deep_research_collector 89%, deep_research_service 84%, ai_report_service 82%.
  - **자동 스모크 (2026-04-25)**: Fast Mode 8m44s 통과 (phase 18/data 230/done 1/error 0), Deep Mode 19분 end-to-end 통과 (4/5 gate → 합성 done). `backend/reports/삼성SDI/2026-04-25{,_2}.md` 자동 저장.

### Added (SPEC-MINERVINI-001)

- **Mark Minervini Trend Template 스크리너 (데이터 계층 + 평가 엔진)** (SPEC-MINERVINI-001 v1.0.3)
  - 새 요청 플래그: `POST /api/screen { "minervini_trend_template": true }` → 8조건 strict gate
  - 8조건 (research.md §2.1 기준): close > SMA150/200, SMA150 > SMA200, SMA200 > 20일 전 SMA200, SMA50 > SMA150/200, close > SMA50, close ≥ LOW_52W × 1.25, close ≥ HIGH_52W × 0.75 && close ≤ HIGH_52W, rs_12m ≥ 70
  - 응답 필드 신규 추가: `StockItem.trend_template_score: int | None` (strict gate 통과 시 고정 `8`, 플래그 OFF 시 `None`)
  - `ScreenRequest.patterns` 제한 완화: `max_length=3` → `max_length=5` (SPEC-PRESET-001 에서 활용 예정)
  - **일봉 파이프라인 신규 컬럼** (`stock_prices`): `SMA150` (150일 SMA), `LOW_52W` (250 거래일 rolling min), `SMA200_20D_AGO` (SMA200 의 20 거래일 shift). 기존 `High52W` 는 window `252 → 250` 으로 변경 (SPEC A2).
  - **stock_meta 스냅샷 컬럼 신규 추가**: `sma150`, `low52w`, `sma200_20d_ago`. 기존 `high52w` 는 값만 갱신.
  - **멱등 ALTER**: 레거시 DB 에도 PRAGMA 기반 컬럼 존재 검사 후 누락 시에만 `ALTER TABLE ADD COLUMN` (defense-in-depth).
  - **Defense path (REQ-MIN-007)**: 신규 컬럼이 누락된 레거시 DB 에서 `minervini_trend_template=true` 요청 시 HTTP 200 + empty 응답 + WARN 로그. 기존 필터는 영향 없음.
  - 신규 모듈/함수:
    - `my_chart/db/daily.py::_compute_minervini_indicators(df)` — 4개 rolling/shift 지표 계산
    - `backend/services/meta_service.py::_ensure_meta_minervini_columns(conn)` — PRAGMA 기반 멱등 ALTER
    - `backend/services/screen_service.py::_build_minervini_where()` — 8조건 AND SQL 상수 빌더 (`@MX:NOTE`)
    - `backend/services/screen_service.py::_minervini_columns_available(conn)` — PRAGMA 가드
    - `backend/services/screen_service.py::screen_stocks()` — strict-gate invariant (`@MX:ANCHOR` + `@MX:REASON`)
  - **프론트엔드 타입**: `frontend/src/types/filter.ts` 에 `ScreenRequest.minervini_trend_template?: boolean | null`, `StockItem.trend_template_score?: number | null` 추가 (UI 변경은 SPEC-PRESET-001 에서 다룸).
  - **테스트**: 28개 pytest 통과 (Group A rolling 정확성 6 / B meta 멱등 ALTER 3 / C WHERE + strict-gate 점수 11 / D 회귀 4 / E defense path 3). 커버리지: `screen_service` ~94%, `meta_service` ~96%, `daily.py` 신규 로직 ~100%.
  - **배포 전략 (v1.0.2 Primary path)**: 기존 `daily.db` / `weekly.db` 파일 삭제 후 `db-update` 파이프라인 전체 재실행. 상세 절차는 spec.md §11.4 참조.
  - **Out of scope** (후속 SPEC): 부분 매칭 점수 (6/8 등), VCP 패턴, 거래량 돌파, 시장 환경 필터, UI 프리셋 (SPEC-PRESET-001).

### Added (SPEC-AI-REPORT-002)

- **AI 리포트 심층 분석 모드 (Deep Research Synthesis)** (SPEC-AI-REPORT-002 v1.0.3)
  - 새 엔드포인트 파라미터: `POST /api/ai-report/{code}?mode=deep`
  - 5-소스 병렬 수집: Perplexity sonar-reasoning-pro + Brave + Tavily + Naver + YouTube
  - `/tmp/analysis_<code>_<uuid>/` 격리 staging 디렉토리
  - Claude Code CLI 헤드리스 합성 (subprocess, OAuth 세션, default Sonnet)
  - SSE stream-json → SSE 어댑터 (data/done/error/phase 이벤트)
  - 자동 리포트 저장: `backend/reports/<stock_name>/<date>.md`
  - 신규 모듈:
    - `backend/services/deep_research_collector.py` — 5-소스 병렬 수집 + 스테이징
    - `backend/services/claude_cli_streamer.py` — CLI subprocess + stream-json 파서
    - `backend/services/deep_research_service.py` — 오케스트레이션 + Deep rate limit
    - `backend/services/perplexity_cache.py` — TTL 10분 메모리 캐시 (시나리오 C 비용 절감)
    - `backend/prompts/stock_synthesis_prompt.md` — 합성 시스템 프롬프트 (절대규칙 A/B/C)
- **프론트엔드 2단 모드 토글 + 명시적 시작 버튼**
  - 헤더: "빠른 분석" / "심층 분석 (수분 소요)" 토글 (ARIA tablist)
  - AI 버튼 클릭 시 idle 상태로 모달 오픈, 사용자가 모드 선택 후 "분석 시작" 버튼 클릭
  - 빠른 → 심층 시 같은 종목의 Perplexity 결과 캐시 재사용 (TTL 10분)
  - done 상태에서 "심층 분석으로 다시 시도" / "빠른 분석으로 다시 시도" 모드 라벨 버튼
  - 캐시 재사용 힌트 표시
- **신규 환경변수**:
  - `BRAVE_API_KEY`, `TAVILY_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `YOUTUBE_API_KEY`
  - `AI_REPORT_DEEP_DAILY_QUOTA` (default 15)
  - `AI_REPORT_DEEP_BURST_LIMIT` (default 1)
  - `AI_REPORT_DEEP_MODEL` (default sonnet, "opus"로 변경 가능)
- **Playwright e2e 테스트**: `frontend/e2e/ai-report-deep.spec.ts` (4 시나리오)
- **테스트 추가**: 백엔드 95개 (Phase A 20 + B 39 + C 22 + D 14), 프론트 7개 (모달 토글 + retry)

### Changed (SPEC-AI-REPORT-002)

- `backend/routers/ai_report.py`: `mode: str = Query("perplexity", pattern="^(perplexity|deep)$")` 파라미터 추가, 가드 체인 분기
- `backend/main.py` lifespan: `shutil.which("claude")` 체크 (warning) + `_load_synthesis_prompt()` fail-fast + `/tmp` 7일 초과 staging 디렉토리 정리
- `frontend/src/components/AiReportModal.tsx`: 모달 헤더 토글 + idle 상태 launcher + done 상태 retry 버튼
- `frontend/src/hooks/useAiReport.ts`: `startStream(code, mode='perplexity')` 시그니처 확장
- `frontend/src/api/aiReport.ts`: URL에 `?mode=${mode}` 추가
- `frontend/src/components/ChartGrid/ChartCell.tsx`: AI 버튼 클릭 시 즉시 시작 X → idle 상태 모달 오픈

### Fixed (SPEC-AI-REPORT-002)

- v1.0.1: Claude CLI timeout 180s → 600s (10분) — Sonnet 5-소스 합성에 180s 부족 (FR-007/NFR-002 완화)
- v1.0.1: Claude CLI 인자 보정 — `--cwd` 옵션은 CLI 2.1.110에 없음. `--add-dir` + subprocess `cwd=` kwarg + `--permission-mode bypassPermissions` + `--model claude-sonnet-4-6` 명시
- v1.0.1: collector source별 timeout — perplexity 120s, tavily 90s, brave/naver/youtube 15s (이전 일괄 10s는 Perplexity가 항상 timeout)
- v1.0.2: Naver/YouTube query에 종목 코드 포함 (예: "우리로" → "우리은행/우리금융" 결과 섞임 방지)
- v1.0.2: 학습 데이터 면책 차단 — synthesis prompt 절대 규칙 A/B/C (사전 학습 지식 사용 금지, "보고서 작성 불가" 면책 금지, 종목 코드 신뢰)
- v1.0.3: 시나리오 C 비용 절감 — Perplexity 캐시 재사용 (HTTP 호출 0)
- v1.0.5: 합성 단계 LimitOverrunError 방어 — `asyncio.create_subprocess_exec(limit=4MB)`로
  StreamReader 버퍼 상향 (기본 64KB로는 긴 stream-json 라인에서 터짐). 미처리 예외도
  `event: error`로 변환해 프론트에 전달 (이전엔 연결만 끊겨 "대기중" 상태로 보임).
  `logging.basicConfig(level=INFO)`로 애플리케이션 로그 가시화.
- v1.0.4: 심층 분석 진행 상태 패널 (Progress Panel) — per-source 실시간 SSE `event: phase`
  - 백엔드 `collect_all_sources`에 `progress_callback` 추가 + `asyncio.wait(FIRST_COMPLETED)`로 소스 완료 순 이벤트 emit
  - 신규 phase 이벤트: `source_start` / `source_done` (success, duration_ms, count, cached, error) / `collecting_done` / `staging_done` / `synthesis_start` / `synthesis_first_chunk`
  - `SourceResult.cached` 필드 — Perplexity 캐시 재사용 여부 표시
  - 프론트: `<ProgressPanel>` 컴포넌트 (5소스 + 합성 상태 + 캐시 재사용 라벨)
  - `useAiReport` 훅에 `progress` state 추가, `createAiReportStream`에 optional `onPhase` 콜백 추가
  - 테스트 +13: ProgressPanel 11, AiReportModal 렌더 조건 2
- e2e UX 버그: AiReportModal done 상태에서 retry 버튼 누락 → done && markdown 분기에 추가

### Notes (SPEC-AI-REPORT-002)

- 검증 종목: **대한광통신 (010170)** — 풀 합성 3분 9초, 11.8KB 리포트 정상 생성
- 검증 종목: **우리로 (046970)** — 동명이인 모호 케이스, 면책 차단 후 14.7KB 리포트 정상 생성
- 회귀: SPEC-001 30 테스트 모두 통과 (AC-017 byte-identical contract preserved)
- 알려진 이슈: `test_sector_advanced.py` 5건 — 다른 테스트 파일의 SimpleNamespace 스텁이 my_chart.registry를 덮어쓸 때 발생, SPEC-002 코드와 무관

## [1.1.0] - 2026-03-08

### Added

- **RS Line (상대강도선) 차트 오버레이** (SPEC-RS-LINE-001)
  - `my_chart/db/daily.py`: RS_Line 컬럼 추가 및 계산 로직
    - KOSPI 지수 데이터 자동 조회
    - 매일 RS_Line = 종목 종가 / KOSPI 종가 계산
    - NULL 값에 대한 폴백 처리
  - `backend/schemas/chart.py`: ChartResponse에 `rs_line` 필드 추가
  - `backend/services/chart_service.py`: 일일/주간 차트 API에 RS_Line 데이터 포함
  - `frontend/src/types/chart.ts`: ChartResponse 인터페이스에 `rs_line` 추가
  - `frontend/src/components/ChartGrid/ChartCell.tsx`: RS Line 시각화
    - IBD 스타일 숨겨진 Y축 표시
    - 반투명 자주색(rgba(108, 92, 231, 0.5)) 렌더링
    - 토글 버튼으로 표시/숨기기 (세션 기간만 유지)
  - 주간 차트에도 동일하게 적용되는 일관된 스타일

## [1.0.0] - 2026-03-04

### Added

- **KRX 세션 기반 인증** (SPEC-KRX-AUTH-001)
  - `my_chart/krx_session.py`: KRX 세션 관리 모듈
    - `patch_pykrx_session()`: pykrx webio를 인증된 세션으로 monkey-patch
    - `login_krx(id, pw)`: 3단계 KRX 인증 (JSESSIONID 획득 → JSP 세션 초기화 → 실제 로그인)
    - `init_session()`: KRX_ID/KRX_PW 환경변수에서 자동 초기화
    - `get_market_cap_safe(date)`: 3단계 폴백 (pykrx → sectormap Excel → 빈 DataFrame)
  - `.env.example`: 인증 정보 템플릿
  - `python-dotenv` 의존성 추가

- **설정 개선**
  - `my_chart/config.py`: dotenv 로드 및 자동 세션 초기화
  - 7개 파일에서 `stock.get_market_cap()` → `get_market_cap_safe()` 교체

### Changed

- Type hints 및 Pyright 호환성 개선
  - `my_chart/krx_session.py`: 타입 안전성 강화 (monkey-patch 함수의 Any 타입 적절한 처리)

### Fixed

- Pyright 타입 오류 수정
  - `my_chart/krx_session.py`: pandas 타입 힌트 개선, type: ignore 주석 추가
