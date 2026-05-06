# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
