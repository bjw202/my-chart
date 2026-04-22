# KR Stock Screener Product Documentation

## Project Overview

**Project Name:** KR Stock Screener

**Tagline:** Web-based Korean stock screening tool with real-time chart grid and advanced technical filters

**Description:** KR Stock Screener is a local-only web application that provides comprehensive screening of KOSPI/KOSDAQ stocks (~2,570 listings). Built on the existing `my_chart` Python library for data acquisition and technical analysis, it adds a FastAPI backend and React frontend with TradingView Lightweight Charts for interactive visualization. Users can apply complex filter combinations (market cap, period returns, technical patterns, RS scores, sectors), view results in a sector-grouped stock list, and scan through candlestick chart grids with synchronized scrolling.

## Core Features

1. **Filter System** - Complex multi-condition screening with market cap ranges, period-based return thresholds (1D/1W/1M/3M), technical pattern builder (price vs MA comparisons with AND/OR logic), RS score filters, market selection (KOSPI/KOSDAQ), and sector/theme multi-select

2. **Chart Grid** - TradingView Lightweight Charts displayed in 2x2 or 3x3 grid layout with daily candlestick, moving averages (10/20/50/100/200), volume bars, and RS Line overlay (stock Close / KOSPI Close ratio, IBD-style purple line with independent hidden Y-axis). Memory-optimized with viewport-only rendering and chart instance destruction on scroll-out. Per-cell header shows stock name, code, sector group (대>중 format matching right-panel grouping), daily change%, and RS score

3. **Stock List** - Right sidebar showing filtered stocks grouped by sector (sectormap `산업명(대)` + `산업명(중)`), sorted by market cap within groups, with collapse/expand headers, keyboard navigation, and display of stock name, code, daily change, and RS score

4. **Scroll Sync** - Bidirectional synchronization between stock list and chart grid. Clicking a stock navigates to its chart page, left/right arrow keys (← →) and pagination buttons advance chart pages, and chart page changes scroll the stock list

5. **DB Update** - One-click batch update of all stock data (daily/weekly OHLCV + moving averages + RS scores + market cap) via background task with progress bar and SSE-based status push. Recommended frequency: once daily after market close

6. **Price Range Measurement** - Interactive price range measurement tool (TradingView-style). Click `%` button or press `M` to activate. First click sets start point, second click locks result showing price diff and percent change. Supports continuous measurement: clicking after a locked result immediately starts new measurement from that click point. Per-cell independent operation, no shared state.

7. **Technical Pattern Builder** - Condition builder UI for constructing custom technical patterns: `[Indicator A] [Operator] [Indicator B or Constant] [x Multiplier]`. Supports price, MA(10/20/50/100/200) as indicators with >, <, >=, <=, and proximity(%) operators. Up to 3 patterns combinable with AND/OR

8. **Financial Analysis Modal (FS Button)** - Comprehensive S-RIM financial dashboard accessible per stock via FS button. Modal header displays company name, code, sector (산업명(대)), and primary product (주요제품). 8-section analysis covering:
   - Section 1: 사업 실적 (Business Performance) — 매출/영업이익/순이익 추이, YoY 성장률, 이익률, 이익의 질
   - Section 2: 건전성 지표 (Health Indicators) — 부채비율, 유동비율, 이자보상배율 등 재무 건전성
   - Section 3: 자본 구조 (Balance Sheet) — 조달(부채/자본) vs 운용(자산) 시각화
   - Section 4: 수익률 분해 (Rate Decomposition) — ROE 분해, 가중평균 ROE, 스프레드 분석
   - Section 5: 이익 워터폴 (Profit Waterfall) — 매출 → 영업이익 → 순이익 폭포 차트
   - Section 6: 활동성 비율 (Activity Ratios) — 매출채권/재고/매입채무 회전율, CCC 타임라인 그래픽
   - Section 7: 추세 신호 (Trend Signals) — 주요 재무 추세 방향 시그널
   - Section 8: 5대 질문 (Five Questions) — 종합 투자 체크리스트 (양호/보통/주의)

10. **Minervini Trend Template Screener** - Mark Minervini 의 Stage 2 상승 추세 8조건을 **strict gate** 로 평가하는 백엔드 스크리너 (SPEC-MINERVINI-001 v1.0.3). `POST /api/screen { "minervini_trend_template": true }` 요청 시 서버사이드 SQL WHERE 에서 8조건 전체를 AND 결합으로 평가하며, 결과 집합의 모든 종목은 정의상 8조건을 모두 통과한다 (`StockItem.trend_template_score` 필드가 고정 `8` 로 반환). 8조건: (T1) close > SMA150 && SMA200, (T2) SMA150 > SMA200, (T3) SMA200 > 20 거래일 전 SMA200, (T4) SMA50 > SMA150 && SMA200, (T5) close > SMA50, (T6) close ≥ 52주 저점 × 1.25, (T7) 52주 고점 × 0.75 ≤ close ≤ 52주 고점, (T8) 12개월 RS ≥ 70. 일봉 파이프라인은 `SMA150`, `LOW_52W`, `SMA200_20D_AGO` 를 precompute 하고 `High52W` 는 250 거래일 rolling 으로 정제. 레거시 DB 에서 신규 컬럼이 누락되면 HTTP 200 + empty 응답으로 격리되어 기존 필터에는 영향이 없다 (defense-in-depth). UI (칩, 토글, 프리셋) 는 SPEC-PRESET-001 의 범위이며 본 기능은 데이터 계층과 평가 엔진까지 다룬다.

11. **AI Company Analysis (AI Button)** - 2-모드 AI 리포트 시스템. SPEC-AI-REPORT-001 (빠른 분석) + SPEC-AI-REPORT-002 (심층 분석, v1.0.5 기준). AI 버튼 클릭 → 모달 오픈 → 모드 선택 → "분석 시작" 명시적 클릭 후 SSE 스트리밍.
   - **빠른 분석 (Perplexity 단일 소스, ~40-90초, ~$0.05/건)**
     - 모델: `sonar-reasoning-pro` (DeepSeek R1 기반 Chain-of-Thought 추론)
     - 검색 품질: `search_context_size: "high"` + `search_recency_filter: "month"` + 최소 SNS 블랙리스트
     - 시스템 프롬프트: 한국 애널리스트 6원칙 (인과 분석 필수, [N] 인용 필수, 교차확인 구분, 기대 vs 팩트, DART/KRX 우선, 추상어 금지)
   - **심층 분석 (5-소스 병렬 + Claude CLI 합성, ~3-5분, ~$0.10-0.30/건)**
     - 수집 소스: Perplexity(sonar-reasoning-pro) + Brave Search + Tavily(advanced) + Naver(웹) + YouTube (asyncio 병렬, 최소 2/5 성공 게이트)
     - 스테이징: `/tmp/analysis_{code}_{ts}_{uuid8}/` 격리 디렉토리에 `summary.md` + `sources/*.json|md` 저장
     - 합성: Claude Code CLI subprocess (기본 `claude-sonnet-4-6`, `AI_REPORT_DEEP_MODEL=opus`로 스위칭 가능), `--permission-mode bypassPermissions --add-dir`로 스테이징 dir 접근
     - Rate limit: Deep 전용 독립 쿼터 (`AI_REPORT_DEEP_DAILY_QUOTA=15`, `AI_REPORT_DEEP_BURST_LIMIT=1`)
     - 캐시 재사용 (v1.0.3): 빠른 분석 후 10분 내 같은 종목 심층 분석 시 Perplexity HTTP 호출 스킵 (메모리 TTL 캐시)
   - **진행 상태 패널 (v1.0.4)**: 심층 분석 모달에 per-source 실시간 진행 UI. `event: phase` SSE 이벤트(`source_start`/`source_done`/`collecting_done`/`staging_done`/`synthesis_start`/`synthesis_first_chunk`) 기반, 5소스 아이콘(⏸/⏳/✅/❌) + duration + count + 캐시 재사용 라벨 + Claude 합성 단계(idle/waiting/streaming) 표시
   - **안정화 (v1.0.5)**: Claude CLI subprocess `StreamReader` limit 64KB → 4MB (LimitOverrunError 방지), 합성 중 미처리 예외를 `event: error`로 변환해 프론트 전달, `logging.basicConfig(INFO)`로 `.dev-server.log` 가시화
   - **UI**: 2탭 모달 (분석 결과 / 히스토리), 모드 토글 (빠른/심층), idle 상태 "분석 시작" 버튼, 마크다운 실시간 렌더링, 복사 버튼, ESC/backdrop 닫기
   - **저장**: `backend/reports/{종목명}/{YYYY-MM-DD}.md` (동일 날짜는 `_N` 시퀀스)
   - **엔드포인트**: POST `/api/ai-report/{code}?mode=perplexity|deep`, GET `/api/ai-report/{code}/history`, GET `/api/ai-report/{code}/{filename}`

## Target Users

- Korean stock market investors running a local screening tool on their machine
- Individual traders who want fast visual scanning of filtered stocks with chart grids
- Technical analysis practitioners applying custom MA and RS-based screening criteria

## Key Use Cases

**Daily Screening Workflow:** Launch app -> Update DB (if stale) -> Set filter criteria -> Browse sector-grouped results -> Scan charts via keyboard/scroll -> Identify trading candidates

**Technical Pattern Screening:** Build custom conditions (e.g., "Close <= 10-day MA x 1.05 AND 10/20/50 MA convergence <= 5%") to find stocks matching specific technical setups

**Sector Analysis:** Filter by specific sectors/themes, view all stocks in a sector with their charts side-by-side for relative comparison

**RS-Based Screening:** Filter stocks by Relative Strength score (e.g., RS >= 80) to identify outperformers vs KOSPI index

## Technology Stack

**Backend:** Python 3.11+, FastAPI, uvicorn, existing my_chart package (data acquisition, indicators, screening, DB management)

**Frontend:** React (Vite), TypeScript, TradingView Lightweight Charts, react-window (virtualized lists)

**Database:** SQLite (existing weekly_price.db, weekly_rs.db, daily_price.db schema)

**Deployment:** Local-only (localhost), no cloud infrastructure

## Data Strategy

### DB-First Approach

All filtering and screening operates on pre-computed data stored in SQLite, ensuring fast query response times. The DB update process (triggered by user) fetches data from external sources (Naver Finance, pykrx) and persists:

- **Weekly DB:** OHLCV, MA50/150/200, period returns (CHG_1W~12M), RS scores
- **Daily DB:** OHLCV, EMA/SMA(10/20/50/200), volume indicators, range indicators
- **Market Cap:** Fetched via pykrx during DB update and stored for SQL-based filtering

### Data Freshness

Data reflects the last DB update timestamp. Intended for end-of-day analysis (장 마감 후 1일 1회 업데이트).

## Reusable Existing Code

The following `my_chart` package functions serve as the backend data layer:

| Function | Module | Web Service Role |
|----------|--------|-----------------|
| `price_naver()` | price.py | `/api/chart/{code}` data source |
| `get_stock_registry()` | registry.py | `/api/sectors`, stock metadata |
| `add_sector_info()` | registry.py | Stock list sector grouping |
| `mmt_companies()` | screening/momentum.py | `/api/screen` momentum filter |
| `daily_filtering()` | screening/daily_filters.py | `/api/screen` daily filter |
| `generate_price_db()` | db/weekly.py | `/api/db/update` batch job |
| `price_daily_db()` | db/daily.py | `/api/db/update` daily batch |
| `load_price_with_rs()` | db/queries.py | Filtering data source |
| `MACD/RSI/BB` | indicators.py | Technical indicator calculation |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/db/update` | Start DB update (async background task) |
| GET | `/api/db/status` | Query update progress (SSE) |
| GET | `/api/db/last-updated` | Last update timestamp |
| POST | `/api/screen` | Apply filter conditions, return filtered stock list |
| GET | `/api/chart/{code}` | Stock chart data (OHLCV + MA) |
| GET | `/api/sectors` | Sector list for filter dropdown |
| GET | `/api/analysis/{code}` | Comprehensive financial analysis (8-section S-RIM dashboard) |
| POST | `/api/ai-report/{code}` | AI 종목 분석 리포트 생성 (Perplexity SSE 스트리밍) |
| GET | `/api/ai-report/{code}/history` | 저장된 AI 분석 이력 목록 |
| GET | `/api/ai-report/{code}/{filename}` | 저장된 AI 분석 파일 조회 |

## Market Coverage

- **KOSPI:** Korea Composite Stock Price Index (~800 stocks)
- **KOSDAQ:** Korean Securities Dealers Automated Quotations (~1,700 stocks)
- Total: ~2,570 stocks with daily/weekly OHLCV and technical indicators

## Quality Standards

- Modular architecture separating API layer from existing data library
- Pure SQL-based filtering for performance (no runtime API calls during screening)
- Memory-optimized chart rendering with viewport virtualization
- Keyboard-accessible navigation for efficient stock scanning
- Parameterized SQL queries preventing injection
