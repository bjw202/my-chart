# KR Stock Screener

한국 주식 시장(KOSPI/KOSDAQ) 통합 스크리닝·분석 데스크탑 도구. 차트 그리드, AI 심층 리포트, S-RIM 재무, 네이버 테마, Minervini 검증된 스크리너 — 모두 로컬에서.

## 🔒 로컬 전용 프라이버시
클라우드 미사용. SQLite 단일 source, KRX 인증/AI 키 모두 로컬 `.env`

## 🇰🇷 한국 시장 특화
KRX 세션 인증 / FnGuide S-RIM / 네이버 테마 (finance.naver.com) 직접 통합

## 🤖 2-tier AI 통합
Perplexity 빠른 분석 (~$0.05) + Claude CLI 5-소스 심층 합성 (~$0.20)

## 📈 검증된 스크리너
Mark Minervini Trend Template 8조건 strict gate (SQL WHERE 평가)

## ⚡ 2,570 종목 즉시 필터링
1일 1회 DB 업데이트 → SQL 기반 인메모리 응답

---

## 🎯 기능 한눈에 보기

### 🔍 종목 스크리닝

| SPEC | 기능 |
|------|------|
| SPEC-MINERVINI-001 | Mark Minervini Trend Template (8조건 strict gate, P1, v1.0.3) |
| SPEC-PRESET-001 | 프리셋 필터 시스템 (사용자 정의 필터 저장) |
| SPEC-SMA5-FILTER-001 | SMA5 지표 필터 추가 + ChartGrid 토글 노출 |
| 내장 필터 | 시가총액, 기간수익률(1D/1W/1M/3M), 기술적 패턴 빌더 (3조건 AND/OR), RS점수, 시장(KOSPI/KOSDAQ), 섹터 멀티셀렉트 |

### 📊 차트 시각화

| SPEC | 기능 |
|------|------|
| SPEC-RS-LINE-001 | RS Line (Relative Strength Line, IBD-style 보라색, 독립 Y축, 종가/KOSPI 비율) |
| SPEC-WEEKLY-CHART-001 | Weekly DB SMA Rename + Daily/Weekly 차트 토글 |
| SPEC-CHART-SEARCH-001 | 차트 검색 |
| SPEC-CHART-NAV-001 | Chart navigation (2026-05-09 rolled back, archive 참조) |
| 내장 기능 | TradingView Lightweight Charts (2x2/3x3), MA 오버레이, 볼륨바, 차트 헤더 (종목명·코드·섹터·등락률·RS), Top 20 라벨, 등락폭 측정 도구 (% 버튼 / M 키 / 연속 측정 / 상태머신) |

### 🏭 섹터·테마 분석

| SPEC | 기능 |
|------|------|
| SPEC-TOPDOWN-001 | Top-Down Market Analysis System |
| SPEC-TOPDOWN-002 | Advanced Sector Visualization & Analytics |
| SPEC-DASHBOARD-001 | 시장 개요 대시보드 |
| SPEC-DASHBOARD-002 | 대시보드 확장 |
| SPEC-NAVER-THEME-001 | 네이버 금융 테마 분석 V1 (desktop HTML 크롤링 MVP) |
| SPEC-NAVER-THEME-002 | V2 mobile JSON API 마이그레이션 |
| SPEC-NAVER-THEME-003 | V2 amendment 체인 (description tooltip, 종목 편입설명, localStorage 캐시) |
| SPEC-NAVER-THEME-CONSOLIDATED | 시리즈 통합 retrospective + lessons (2026-05-27) |
| SPEC-SECTOR-MINOR-COLOR-001 | StockBubbleChart 산업명(중) 색상·동적 범례 (2026-05-27 ship #9) |

### 💰 재무·기업 분석

| SPEC | 기능 |
|------|------|
| SPEC-FNGUIDE-ENGINE-001 | FnGuide 재무 분석 엔진 (S-RIM 8-섹션 대시보드) |
| SPEC-AI-REPORT-001 | AI 빠른 분석 — Perplexity `sonar-reasoning-pro` 단일 호출 (~$0.05/건) |
| SPEC-AI-REPORT-002 | AI 심층 분석 — 5-소스 병렬 + Claude CLI 합성 (~$0.20/건) |
| SPEC-AI-REPORT-003 | Perplexity → Codex 전면 대체 (Plan 완료, Step 1 승인 대기 — 2026-04-23) |

### 🛠️ 데이터 인프라

| SPEC | 기능 |
|------|------|
| SPEC-001 | Data Pipeline Validation & DB Performance Optimization |
| SPEC-WEB-001 | FastAPI + React 웹 기반 (백엔드/프론트 분리 아키텍처) |
| SPEC-KRX-AUTH-001 | KRX 세션 기반 인증 (pykrx 우회, sectormap 폴백) |

### 🎨 UI/UX

| SPEC | 기능 |
|------|------|
| SPEC-UI-001 | UI 기반 (5탭 구성, 키보드 네비게이션, virtualized list) |
| SPEC-STOCK-TOOLTIP-PRODUCT-001 | StockBubbleChart tooltip 주요제품 라인 추가 (2026-05-27 ship #9) |

---

## 🚀 빠른 시작

### 한 번에 실행 (권장)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd frontend && pnpm install && cd ..

./dev.sh   # 백엔드(8000) + 프론트엔드(5173) 동시 실행
```

### 개별 실행

**백엔드:**

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

API 문서: http://localhost:8000/docs

**프론트엔드:**

```bash
cd frontend
pnpm dev
```

개발 서버: http://localhost:5173

### KRX 세션 인증 설정 (선택사항)

pykrx 라이브러리로 KRX 데이터를 조회할 때 인증을 필요로 할 수 있습니다.

**1.** `.env` **파일 생성:**

`.env.example`을 참고하여 프로젝트 루트에 `.env` 파일을 생성합니다:

```bash
KRX_ID=your_krx_id
KRX_PW=your_krx_password
```

**2. 환경변수 설정:**

- `KRX_ID`: 한국거래소(data.krx.co.kr) 회원 ID
- `KRX_PW`: 한국거래소 회원 비밀번호

앱이 시작될 때 자동으로 다음 작업이 수행됩니다:

- pykrx webio를 인증된 세션으로 monkey-patch
- KRX에 로그인 (3단계 인증 플로우)
- 인증 실패 시 자동으로 sectormap 폴백 모드로 동작

**3. 폴백 메커니즘:**

만약 KRX 로그인이 실패하거나 환경변수가 설정되지 않으면:

1. pykrx 호출 시도 (인증 없음)
2. 실패 시 `Input/sectormap-original.xlsx`의 D-day 컬럼 사용
3. 폴백 데이터도 없으면 빈 DataFrame 반환

### 첫 실행

1. 백엔드와 프론트엔드를 시작합니다
2. "DB 업데이트" 버튼을 클릭합니다 (~2,570종목 수집, 5-30분 소요)
3. 필터를 적용하고 차트 그리드를 탐색합니다

---

## 🗂️ 5탭 워크플로우 가이드

### 1️⃣ Market Overview (시장 개요) — SPEC-DASHBOARD-001/002, SPEC-TOPDOWN-001

전체 시장의 현재 상태를 한눈에. 주가지수, 섹터별 성과, 시장 breadth를 대시보드로 제공합니다.

### 2️⃣ Sector Analysis (섹터 분석) — SPEC-TOPDOWN-002, SPEC-NAVER-THEME-001/002/003

산업별·테마별 주도주를 추적하고, 강세 섹터를 실시간으로 파악하세요. 네이버 금융 테마 데이터(V2 모바일 JSON API)와 StockBubbleChart 색상·범례로 시각화합니다.

### 3️⃣ Stock Explorer (종목 검색) — SPEC-MINERVINI-001, SPEC-PRESET-001, SPEC-SMA5-FILTER-001

내장 필터를 조합하여 맞춤 스크리닝:
- **기본 필터**: 시가총액, 기간수익률(1D/1W/1M/3M), RS점수, 시장, 섹터
- **고급 필터**: Minervini Trend Template (8조건), 기술적 패턴 빌더 (3조건 AND/OR), SMA5 지표
- **저장**: 프리셋 시스템으로 자주 쓰는 조건 저장

### 4️⃣ Chart Grid (차트 그리드) — SPEC-WEB-001, SPEC-RS-LINE-001, SPEC-WEEKLY-CHART-001

필터링된 종목들의 차트를 2x2 또는 3x3 그리드로 동시 표시. TradingView Lightweight Charts로 구현되며, MA 오버레이·RS Line·볼륨바를 지원합니다. 키보드/스크롤로 종목 리스트와 동기화되고, 등락폭 측정 도구(% 버튼, M 키)로 수익률 계산이 가능합니다.

**재무 분석 (FS 버튼)** — SPEC-FNGUIDE-ENGINE-001: FnGuide S-RIM 8섹션 대시보드 (사업실적·건전성·대차대조표·수익률분해·이익워터폴·활동성·추세신호·5개질문)

**AI 기업 분석 (AI 버튼)** — SPEC-AI-REPORT-001/002: 2모드 AI 분석
- **빠른 분석** (~40-90초, ~$0.05): Perplexity `sonar-reasoning-pro` 단일 호출
- **심층 분석** (~3-5분, ~$0.20): 5-소스 병렬 (Perplexity+Brave+Tavily+Naver+YouTube) + Claude CLI 합성

### 5️⃣ Theme Analysis (테마 분석) — SPEC-NAVER-THEME-001/002/003, SPEC-STOCK-TOOLTIP-PRODUCT-001

네이버 금융 테마 실시간 수집(V2: 모바일 JSON API) → 강세 테마 상위 N개 추출 → 종목별 편입설명 + 주요제품 tooltip 표시 → 멀티테마 종목 분석.

---

## 🤖 AI 분석 시스템

### 빠른 분석 vs 심층 분석

| 구분 | 빠른 분석 | 심층 분석 |
|------|---------|---------|
| 비유 | 한 리서처의 의견 | 5인 리서치팀 + 시니어 애널리스트 |
| 소요 시간 | 40~90초 | 3~5분 (캐시 hit 시 1초) |
| 비용 | ~$0.05/건 | ~$0.10~0.30/건 |
| 결과 | Perplexity 답변 (뉴스/테마/모멘텀) | 6컬럼 표 + 교차 검증 + 리스크/촉매 분리 |
| 적합한 상황 | "어제 왜 올랐지?" 빠른 확인 | "내일 진입할지" 의사결정 직전 검토 |

### 환경변수 설정 (필수)

```bash
# 빠른 분석 (필수)
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxx

# 심층 분석 (필수)
BRAVE_API_KEY=
TAVILY_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
YOUTUBE_API_KEY=

# 비용 제어 (선택, 기본값 사용 권장)
AI_REPORT_DAILY_QUOTA=50          # 빠른 분석 일일 한도
AI_REPORT_BURST_LIMIT=3           # 빠른 분석 분당 한도
AI_REPORT_DEEP_DAILY_QUOTA=15     # 심층 분석 일일 한도
AI_REPORT_DEEP_BURST_LIMIT=1      # 심층 분석 분당 한도
AI_REPORT_DEEP_MODEL=sonnet       # 합성 모델 (sonnet 또는 opus)
```

상세 설명은 `.moai/specs/SPEC-AI-REPORT-001/spec.md`, `.moai/specs/SPEC-AI-REPORT-002/spec.md`를 참조하세요.

---

## 🔍 Minervini Trend Template Screener

Mark Minervini의 Stage 2 상승 추세 8조건을 strict gate로 평가하는 스크리너입니다. (SPEC-MINERVINI-001 v1.0.3)

### 8조건

| 조건 | 설명 |
|------|------|
| T1 | Close > SMA150 && SMA200 |
| T2 | SMA150 > SMA200 |
| T3 | SMA200 > 20거래일 전 SMA200 |
| T4 | SMA50 > SMA150 && SMA200 |
| T5 | Close > SMA50 |
| T6 | Close ≥ 52주 저점 × 1.25 |
| T7 | 52주 고점 × 0.75 ≤ Close ≤ 52주 고점 |
| T8 | 12개월 RS ≥ 70 |

### 사용법

Stock Explorer 탭의 **"Minervini Trend Template"** 필터를 활성화하거나, 사전 설정된 프리셋을 선택하세요. 결과 집합의 모든 종목은 8조건을 모두 통과한 검증된 상승 추세주입니다.

---

## 📏 등락폭 측정 도구

TradingView의 "Price Range" 측정 도구와 유사한 기능으로, 차트 위 두 지점을 클릭하여 가격 등락률(%)을 측정합니다.

### 사용법

1. 차트 헤더의 `%` 버튼 클릭 또는 `M` 키 → 측정 모드 진입 (커서 crosshair)
2. 차트 위 첫 번째 클릭 → 시작점 고정
3. 마우스 이동 → 실시간 미리보기 (연결 영역 + 라벨)
4. 두 번째 클릭 → 측정 결과 고정 (locked)
5. 측정 결과 상태에서 클릭 → 해당 위치를 시작점으로 즉시 새 측정 시작 (연속 측정)
6. `ESC` / `%` 버튼 재클릭 / `M` 키 → 측정 해제 (idle로 복귀)

### 표시 형식

- 양수: `+20.00%` (초록)
- 음수: `-13.26%` (빨강)

### 상태 머신

```
IDLE ──[% / M]──> MEASURING ──[클릭(시작점)]──> MEASURING* ──[클릭(끝점)]──> LOCKED
IDLE <──[% / M / ESC]── MEASURING
LOCKED ──[클릭]──> MEASURING* (연속 측정: 클릭 위치가 새 시작점)
LOCKED ──[% / M / ESC]──> IDLE
```

---

## 📡 API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
| --- | --- | --- |
| POST | `/api/db/update` | DB 업데이트 시작 (백그라운드 태스크) |
| GET | `/api/db/status` | DB 업데이트 진행률 (SSE 스트림) |
| GET | `/api/db/last-updated` | 마지막 업데이트 시각 및 DB 기준 최종 데이터 날짜 |
| POST | `/api/screen` | 필터 적용, 섹터별 그룹 결과 반환 |
| GET | `/api/chart/{code}` | 종목 차트 데이터 (OHLCV + MA 오버레이 + RS Line) |
| GET | `/api/sectors` | 필터 드롭다운용 섹터 목록 |
| GET | `/api/analysis/{code}` | 종목 재무 분석 (FnGuide S-RIM 8개 섹션 대시보드) |
| POST | `/api/ai-report/{code}` | AI 종목 분석 리포트 생성 (SSE 스트리밍, mode=perplexity\|deep) |
| GET | `/api/ai-report/{code}/history` | 저장된 AI 분석 이력 목록 |
| GET | `/api/ai-report/{code}/{filename}` | 저장된 AI 분석 파일 조회 |
| GET | `/api/themes/v2/snapshot` | V2 테마 분석 스냅샷 (모바일 JSON API 기반, ~30초) |
| GET | `/api/themes/v2/quick` | V2 테마 분석 빠른 조회 (≤10초) |

---

## 🛠️ 기술 스택

- **백엔드**: Python 3.13, FastAPI, uvicorn, sse-starlette, requests, beautifulsoup4
- **프론트엔드**: React 19, TypeScript, Vite, TradingView Lightweight Charts, react-window
- **데이터베이스**: SQLite (WAL mode, read-only 모드)
- **데이터 소스**: Naver Finance API, pykrx (한국거래소), 네이버 금융 테마 페이지

---

## 📁 프로젝트 구조

```
my_chart/           # 기존 Python 데이터 라이브러리 (가격, 지표, DB)
backend/            # FastAPI API 레이어 (routers, schemas, services)
frontend/           # React + Vite + TypeScript UI
tests/              # pytest 테스트 (374개)
```

---

## 설정

### Input 디렉토리

| 파일 | 출처 | 용도 |
| --- | --- | --- |
| `sectormap-original.xlsx` | [세종데이터](https://www.sejongdata.com/) | 종목코드, 종목명, 시장(KOSPI/KOSDAQ), 섹터 분류(산업명 대/중, 주요제품) (53 컬럼) |
| `basic_data.xlsx` | [KRX 정보데이터시스템](https://data.krx.co.kr/) | 상장주식수 (시가총액 계산에 사용) |

### Output 디렉토리

DB 파일은 `Output/` 디렉토리에 저장됩니다:

- `stock_data_weekly.db` - 주간 주가 데이터
- `stock_data_daily.db` - 일일 주가 데이터
- `stock_data_rs.db` - 상대강도 점수 데이터

---

## my_chart 라이브러리

기존 `my_chart` 패키지가 백엔드 데이터 레이어를 담당합니다:

| 함수 | 모듈 | 웹 서비스 역할 |
| --- | --- | --- |
| `price_naver()` | price.py | `/api/chart/{code}` 데이터 소스 |
| `get_stock_registry()` | registry.py | `/api/sectors`, 종목 메타데이터 |
| `generate_price_db()` | db/weekly.py | `/api/db/update` 배치 작업 |
| `price_daily_db()` | db/daily.py | `/api/db/update` 일일 배치 |
| `load_price_with_rs()` | db/queries.py | 필터링 데이터 소스 |

---

## 📚 SPEC 인덱스

전체 25개 SPEC을 카테고리별로 정렬하였습니다. 각 SPEC의 상세 요구사항은 `.moai/specs/SPEC-{ID}/spec.md`를 참고하세요.

### 스크리닝 / 필터
- [SPEC-MINERVINI-001](/.moai/specs/SPEC-MINERVINI-001/spec.md) — Mark Minervini Trend Template (v1.0.3, completed)
- [SPEC-PRESET-001](/.moai/specs/SPEC-PRESET-001/spec.md) — 프리셋 필터 시스템
- [SPEC-SMA5-FILTER-001](/.moai/specs/SPEC-SMA5-FILTER-001/spec.md) — SMA5 지표 필터

### 차트 / 시각화
- [SPEC-RS-LINE-001](/.moai/specs/SPEC-RS-LINE-001/spec.md) — RS Line 차트 오버레이
- [SPEC-WEEKLY-CHART-001](/.moai/specs/SPEC-WEEKLY-CHART-001/spec.md) — Weekly DB + 차트 토글
- [SPEC-CHART-SEARCH-001](/.moai/specs/SPEC-CHART-SEARCH-001/spec.md) — 차트 검색
- [SPEC-CHART-NAV-001](/.moai/specs/SPEC-CHART-NAV-001/spec.md) — Chart navigation (rolled back 2026-05-09)

### 대시보드 / 분석
- [SPEC-TOPDOWN-001](/.moai/specs/SPEC-TOPDOWN-001/spec.md) — Top-Down Market Analysis System
- [SPEC-TOPDOWN-002](/.moai/specs/SPEC-TOPDOWN-002/spec.md) — Advanced Sector Visualization
- [SPEC-DASHBOARD-001](/.moai/specs/SPEC-DASHBOARD-001/spec.md) — 시장 개요 대시보드
- [SPEC-DASHBOARD-002](/.moai/specs/SPEC-DASHBOARD-002/spec.md) — 대시보드 확장

### 테마 분석
- [SPEC-NAVER-THEME-001](/.moai/specs/SPEC-NAVER-THEME-001/spec.md) — V1 desktop HTML (MVP)
- [SPEC-NAVER-THEME-002](/.moai/specs/SPEC-NAVER-THEME-002/spec.md) — V2 mobile JSON API
- [SPEC-NAVER-THEME-003](/.moai/specs/SPEC-NAVER-THEME-003/spec.md) — V2 amendment 체인
- [SPEC-NAVER-THEME-CONSOLIDATED](/.moai/specs/SPEC-NAVER-THEME-CONSOLIDATED/spec.md) — 시리즈 통합 (2026-05-27)
- [SPEC-SECTOR-MINOR-COLOR-001](/.moai/specs/SPEC-SECTOR-MINOR-COLOR-001/spec.md) — StockBubbleChart 색상/범례

### AI / 재무
- [SPEC-FNGUIDE-ENGINE-001](/.moai/specs/SPEC-FNGUIDE-ENGINE-001/spec.md) — FnGuide S-RIM 8섹션 대시보드
- [SPEC-AI-REPORT-001](/.moai/specs/SPEC-AI-REPORT-001/spec.md) — Perplexity 빠른 분석 (v1.1.6)
- [SPEC-AI-REPORT-002](/.moai/specs/SPEC-AI-REPORT-002/spec.md) — 5-소스 심층 분석 (v1.0.5)
- [SPEC-AI-REPORT-003](/.moai/specs/SPEC-AI-REPORT-003/spec.md) — Perplexity → Codex 전면 대체 (planning)

### 인프라 / 기초
- [SPEC-001](/.moai/specs/SPEC-001/spec.md) — Data Pipeline Validation & Optimization
- [SPEC-WEB-001](/.moai/specs/SPEC-WEB-001/spec.md) — FastAPI + React 웹 기반
- [SPEC-KRX-AUTH-001](/.moai/specs/SPEC-KRX-AUTH-001/spec.md) — KRX 세션 인증

### UI/UX
- [SPEC-UI-001](/.moai/specs/SPEC-UI-001/spec.md) — UI 기반 (5탭, 키보드 네비, virtualized list)
- [SPEC-STOCK-TOOLTIP-PRODUCT-001](/.moai/specs/SPEC-STOCK-TOOLTIP-PRODUCT-001/spec.md) — StockBubbleChart 주요제품 tooltip

---

## 🧪 테스트

```bash
pytest tests/ -q
```

---

## 🎯 이 도구가 필요한 이유

한국 주식 시장 트레이딩 도구의 부재. 대부분의 플랫폼은 **차트-필터 통합이 약하거나 클라우드 기반**입니다. 

이 프로젝트는:
- **로컬 프라이버시**: 트레이딩 데이터가 외부 서버를 거치지 않음
- **클라우드 비용 회피**: 일일 1회 업데이트 모델로 효율적 운영
- **통합 워크플로우**: 스크리닝 → 차트 → 재무 → AI → 테마 분석을 한 화면에서
- **한국 시장 특화**: KRX 인증, FnGuide 재무, 네이버 테마 (다른 도구들은 글로벌 중심)

개별 트레이더와 분석가가 로컬에서 **꽤 괜찮은 주식 모니터링 툴**을 운영할 수 있습니다.

---

## 📜 라이선스

Private - 로컬 전용.