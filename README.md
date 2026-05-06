# KR Stock Screener

한국 주식시장(KOSPI/KOSDAQ) \~2,570종목을 스크리닝하는 웹 애플리케이션입니다. 기존 `my_chart` Python 라이브러리 위에 FastAPI 백엔드와 React 프론트엔드를 구축했습니다.

## 아키텍처

```
React (Vite+TS)  ->  FastAPI (Python)  ->  my_chart package  ->  SQLite
                                       ->  stock_meta table   ->  (denormalized)
```

## 빠른 시작

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

pykrx 라이브러리로 KRX 데이터를 조회할 때 인증을 필요로 할 수 있습니다. 다음과 같이 설정하면 자동으로 인증됩니다:

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
2. 실패 시 `Input/sectormap.xlsx`의 D-day 컬럼 사용
3. 폴백 데이터도 없으면 빈 DataFrame 반환

### 첫 실행

1. 백엔드와 프론트엔드를 시작합니다
2. "DB 업데이트" 버튼을 클릭합니다 (\~2,570종목 수집, 5-30분 소요)
3. 필터를 적용하고 차트 그리드를 탐색합니다

## 주요 기능 (5탭 구성)

### 1. Market Overview (시장 개요)
- 주가지수, 섹터별 성과 개요

### 2. Sector Analysis (섹터 분석)
- 섹터 성과 트래킹, 섹터별 주도주

### 3. Stock Explorer (종목 검색)
- **필터 시스템**: 시가총액, 기간수익률(1D/1W/1M/3M), 기술적 패턴 빌더, RS점수, 시장, 섹터 필터

### 4. Chart Grid (차트 그리드)
- **차트**: TradingView Lightweight Charts (2x2 / 3x3), MA 오버레이, 볼륨바, RS 값 표시, RS Line (상대강도선, 종가/KOSPI 비율), 마지막 캔들 5봉 여백
- **차트 헤더**: 종목명 · 종목코드 · 섹터그룹(대&gt;중) · 등락률 · RS 점수 한눈에 표시
- **등락폭 측정**: 차트 위 두 지점 클릭으로 가격 등락률(%) 표시, 연속 측정 지원 (측정 완료 후 클릭만으로 즉시 새 측정 시작), 셀별 독립 동작 (아래 상세 설명 참고)
- **종목 리스트**: 섹터 그룹별 가상화 리스트, 키보드 네비게이션
- **스크롤 동기화**: 차트 그리드와 종목 리스트 간 양방향 동기화 (← → 방향키 및 버튼 클릭으로 페이지 이동, 자동 스크롤 연동)
- **관심종목**: 체크 버튼으로 관심 등록/해제, 관심 탭에서 모아보기, TradingView 내보내기
- **DB 업데이트**: SSE 기반 진행률 스트리밍, 백그라운드 일괄 업데이트, DB 기준 최종 날짜 표시
- **재무 분석 (FS 버튼)**: FnGuide 크롤링 기반 S-RIM 8섹션 재무 대시보드 (사업실적·건전성·대차대조표·수익률분해·이익워터폴·활동성·추세신호·5개질문)
- **AI 기업 분석 (AI 버튼)**: Perplexity API 기반 실시간 AI 스윙 트레이더 리포트. 공간(Spaces) 수준의 깊이 있는 분석 (SSE 스트리밍 + 자동 저장 + 히스토리 관리)

### 5. Theme Analysis (테마 분석) — SPEC-NAVER-THEME-001/002/003 V1+V2

**V1 (desktop HTML 크롤링, SPEC-NAVER-THEME-001)** — cohabitation 보존, 즉시 rollback 경로
**V2 (mobile JSON API, SPEC-NAVER-THEME-002+003)** — 현재 frontend 호출 대상

- **테마 목록**: 네이버 금융 테마 실시간 수집(V1: 데스크탑 HTML, V2: 모바일 m.stock.naver.com JSON), 강세 테마 상위 N개 추출
- **테마 설명 tooltip**: V2 응답의 `theme_description`이 theme_name 셀 hover 시 native HTML title로 노출 (D-2, SPEC-003 REQ-NT3-004)
- **테마 설명 본문 (prominent)**: 선택된 테마의 `theme_description`을 우측 상세 패널 상단에 큰 글씨 + 좌측 색 띠로 prominent하게 표시 (v1.0.2 amendment, REQ-NT3-009 강화)
- **종목 테이블 + 편입설명**: 종목별 편입설명을 종목 행 다음에 본문 텍스트로 노출 + hover tooltip 동시 (v1.0.1 amendment, REQ-NT3-010)
- **주도주 섹션 제거**: v1.0.2 amendment에서 별도 "주도주" 섹션 제거. 주도주 정보는 종목 테이블의 모든 종목으로 통합 (REQ-NT3-011)
- **기본 모드 '전체 조회'**: v1.0.3 amendment에서 기본 진입 모드를 '빠른 조회'에서 '전체 조회'로 변경 (REQ-NT3-012). description은 V2 detail endpoint에서만 채워지므로 default를 full로 하여 사용자가 처음부터 description 노출. "빠른 조회" 토글 시 description이 표시되지 않음을 advisory 박스로 안내 (REQ-NT3-013).
- **멀티테마 종목**: 2개 이상 테마에 동시 편입된 종목 분석
- **에러 처리 (V2)**: V2 endpoint 503/timeout 시 사용자 친화적 에러 메시지 + 다시 시도 버튼 (V1 자동 폴백 X — D-1, SPEC-003 REQ-NT3-007)
- **빠른 조회**: V2 `/api/themes/v2/quick` (≤10초) / 상세 조회: V2 `/api/themes/v2/snapshot` (~30초)
- **rollback 경로**: V1 endpoints `/api/themes/snapshot`, `/api/themes/quick`은 등록 유지 — frontend `themes.ts` URL을 V1으로 되돌리면 즉시 복귀
- **비개발자용 가이드**: 작업 배경, V1→V2 변천사, 4가지 결정(D-1~D-4) 친절 설명 → [docs/theme-analysis-guide.md](docs/theme-analysis-guide.md), 시리즈 회고/교훈 → [.moai/learnings/SPEC-NAVER-THEME-001-003-lessons.md](.moai/learnings/SPEC-NAVER-THEME-001-003-lessons.md)

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
| --- | --- | --- |
| POST | `/api/db/update` | DB 업데이트 시작 (백그라운드 태스크) |
| GET | `/api/db/status` | DB 업데이트 진행률 (SSE 스트림) |
| GET | `/api/db/last-updated` | 마지막 업데이트 시각 및 DB 기준 최종 데이터 날짜 |
| POST | `/api/screen` | 필터 적용, 섹터별 그룹 결과 반환 |
| GET | `/api/chart/{code}` | 종목 차트 데이터 (OHLCV + MA 오버레이 + RS Line) |
| GET | `/api/sectors` | 필터 드롭다운용 섹터 목록 |
| GET | `/api/analysis/{code}` | 종목 재무 분석 (FnGuide S-RIM 8개 섹션 대시보드) |
| POST | `/api/ai-report/{code}` | AI 종목 분석 리포트 생성 (Perplexity SSE 스트리밍) |
| GET | `/api/ai-report/{code}/history` | 저장된 AI 분석 이력 목록 |
| GET | `/api/ai-report/{code}/{filename}` | 저장된 AI 분석 파일 조회 |
| GET | `/api/themes/snapshot` | V1 테마 분석 (데스크탑 HTML, cohabitation rollback 경로) |
| GET | `/api/themes/quick` | V1 테마 분석 빠른 조회 (데스크탑 HTML, cohabitation rollback 경로) |
| GET | `/api/themes/v2/snapshot` | V2 테마 분석 스냅샷 (모바일 JSON API 기반, 5종 DataFrame + V1-호환 metadata, ~30초) |
| GET | `/api/themes/v2/quick` | V2 테마 분석 빠른 조회 (모바일 JSON API 기반, ≤10초) |

## 필터 유형

- **시가총액**: 최소 기준 (억원)
- **기간수익률**: CHG_1D, CHG_1W, CHG_1M, CHG_3M 최소 %
- **기술적 패턴**: 최대 3개 조건, AND/OR (`Close <= EMA10 x 1.05`)
- **RS점수**: 최소 RS_12M_Rating
- **시장**: KOSPI / KOSDAQ 체크박스
- **섹터**: 산업명(대) 멀티셀렉트

## 기술 스택

- **백엔드**: Python 3.13, FastAPI, uvicorn, sse-starlette, requests, beautifulsoup4 (테마 크롤링)
- **프론트엔드**: React 19, TypeScript, Vite, TradingView Lightweight Charts, react-window
- **데이터베이스**: SQLite (WAL mode, read-only 모드)
- **데이터 소스**: Naver Finance API, pykrx (한국거래소), 네이버 금융 테마 페이지 (finance.naver.com/sise/theme.naver)

## 프로젝트 구조

```
my_chart/           # 기존 Python 데이터 라이브러리 (가격, 지표, DB)
backend/            # FastAPI API 레이어 (routers, schemas, services)
frontend/           # React + Vite + TypeScript UI
tests/              # pytest 테스트 (374개)
```

## 테스트

```bash
pytest tests/ -q
```

## my_chart 라이브러리

기존 `my_chart` 패키지가 백엔드 데이터 레이어를 담당합니다:

| 함수 | 모듈 | 웹 서비스 역할 |
| --- | --- | --- |
| `price_naver()` | price.py | `/api/chart/{code}` 데이터 소스 |
| `get_stock_registry()` | registry.py | `/api/sectors`, 종목 메타데이터 |
| `generate_price_db()` | db/weekly.py | `/api/db/update` 배치 작업 |
| `price_daily_db()` | db/daily.py | `/api/db/update` 일일 배치 |
| `load_price_with_rs()` | db/queries.py | 필터링 데이터 소스 |

## 설정

### Input 디렉토리

| 파일 | 출처 | 용도 |
| --- | --- | --- |
| `sectormap.xlsx` | [세종데이터](https://www.sejongdata.com/) | 종목코드, 종목명, 시장(KOSPI/KOSDAQ), 섹터 분류(산업명 대/중, 주요제품) |
| `basic_data.xlsx` | [KRX 정보데이터시스템](https://data.krx.co.kr/) | 상장주식수 (시가총액 계산에 사용: 종가 x 상장주식수) |
| `sectormap_original.xlsx` | 세종데이터 (원본) | 백업용 원본 파일 (코드에서 직접 사용하지 않음) |

- KOSPI 주식 (\~833개)
- KOSDAQ 주식 (\~1,719개)
- 섹터 분류 정보

### Output 디렉토리

DB 파일은 `Output/` 디렉토리에 저장됩니다:

- `stock_data_weekly.db` - 주간 주가 데이터
- `stock_data_daily.db` - 일일 주가 데이터
- `stock_data_rs.db` - 상대강도 점수 데이터

## 등락폭 측정 도구

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

### 기술 구현

- `usePriceRangeMeasure` hook: 상태 머신 + lightweight-charts 이벤트 구독
- `PriceRangeOverlay` 컴포넌트: HTML div 기반 오버레이 (pointer-events: none)
- 데이터 좌표(price, time)로 저장, 매 렌더 시 픽셀 좌표로 변환
- 각 차트 셀이 독립적으로 동작 (Context API 불필요)

## 개발 참고

- 단일 프로세스 uvicorn (1 worker) - SQLite 스레드 안전성
- Registry lifespan event에서 사전 초기화
- 인덱싱된 `stock_meta` 테이블에서 파라미터화 SQL 필터링
- 차트 인스턴스 페이지 변경 시 destroy (메모리 누수 방지)

## AI 기업 분석 (Perplexity 통합)

차트 셀 오른쪽 툴바의 **AI 버튼**을 클릭하면 Perplexity API를 통해 실시간 AI 스윙 트레이더 리포트를 생성합니다.

- **SPEC**: [`SPEC-AI-REPORT-001`](.moai/specs/SPEC-AI-REPORT-001/spec.md) (현재 v1.1.6)
- **서비스 구현**: [`backend/services/ai_report_service.py`](backend/services/ai_report_service.py)
- **라우터**: [`backend/routers/ai_report.py`](backend/routers/ai_report.py)
- **프롬프트 템플릿(canonical)**: [`backend/prompts/perplexity_prompt.md`](backend/prompts/perplexity_prompt.md)

### 1. Perplexity API 호출 파라미터 (v1.1.6)

엔드포인트: `POST https://api.perplexity.ai/chat/completions` (SSE 스트리밍)

| 파라미터 | 값 | 역할 |
|---------|---|-----|
| `model` | `sonar-reasoning-pro` | DeepSeek R1 기반 Chain-of-Thought 추론 모델 |
| `stream` | `true` | SSE 실시간 스트리밍 (event-stream) |
| `temperature` | `0.2` | 재현성 확보 (낮은 랜덤성) |
| `max_tokens` | `12000` | 내부 `<think>` 추론 블록 + 최종 리포트 동시 생성 공간 |
| `web_search_options.search_context_size` | `"high"` | 공간(Spaces) 수준의 검색 컨텍스트 확보 (품질 1차 레버) |
| `search_recency_filter` | `"month"` | 최근 30일 소스 우선 |
| `search_domain_filter` | `["-instagram.com", "-x.com", "-twitter.com", "-facebook.com", "-reddit.com"]` | SNS만 제외, 블로그/유튜브/공시/일간지 모두 허용 (공간 전략 일치) |
| `return_related_questions` | `true` | 다중 패스 리서치 활성화 |
| `messages` | `[{role: system, ...}, {role: user, ...}]` | system = 애널리스트 페르소나, user = 7단계 리포트 구조 요청 |

**HTTP 타임아웃**: 180초 (high context는 응답 시간이 길어질 수 있음)

### 2. 시스템 프롬프트 (system role, v1.1.6 전문)

`backend/services/ai_report_service.py`의 `SYSTEM_PROMPT` 상수:

```markdown
당신은 한국 주식시장 전문 스윙 트레이딩 애널리스트입니다.

# 검색 전략 (필수 준수)

대형주(시가총액 상위, 통신/금융/화학/자동차 등 전통 산업군)는 정보가
여러 소스에 분산되어 있습니다. 데이터가 부족하다고 느껴지면 다음 순서로
**추가 검색 관점을 능동적으로 동원**하세요:

1. 재무 데이터: DART 정기공시, 증권사 리포트(SK증권/미래에셋/하나/NH/메리츠 등),
   wisereport, fnguide, buffettlab
2. 배당/주주환원: 배당 정책 기사, 주주총회 공시, 배당수익률 비교 리포트
3. 수급 데이터: GSIFN IR, 외국인/기관 순매수 보도, 공매도 잔고(KRX),
   투자 블로그의 일일 집계
4. 테크니컬: 알파스퀘어, 네이버 증권, 다음 금융, Investing.com의 실시간 차트
5. 최신 이벤트: 장중 기사(news.nate, hankyung, mk, biz.chosun), 52주 신고가/저가,
   VI 발동
6. 산업 동향: 경쟁사 비교(동종 업종), 테마 관련 기사, 증권사 업종 리포트

→ "검색 결과 부재" 단독 결론은 금지. 단일 소스라도 유용하면 인용하되
   [루머]/[단일출처]로 명시.

# 작성 원칙

1. 각 표 뒤에는 반드시 1-2문단의 서술형 인과 분석을 추가하세요.
2. 모든 수치·주장에는 [1], [2] 형식의 출처 인용을 반드시 부여하세요.
3. 톱티어 2건 이상 교차 확인된 뉴스만 '확정'으로 분류하고,
   단일 출처는 [루머] 또는 [단일출처]로 명시하세요.
4. 기대(내러티브) vs 팩트(실적/공시) 패턴을 명시적으로 구분하세요.
5. 출처 우선순위: DART/KRX 공시 > 주요 일간지 > 증권사 리포트 >
   IR·분석 플랫폼 > 투자 블로그.
6. 금지: 추상어("좋은/나쁜/강한" 단독 사용), 매매권유, 출처 없는 수치,
   근거 없는 전망.
7. 데이터 부족 시에도 찾아낸 범위에서 최대한 구체적 수치를 제시하고,
   누락된 항목은 표 안에서 "미공개" 같은 짧은 라벨로만 표시하세요.
   절대 "데이터 부재" 같은 안내 문구로 섹션 전체를 대체하지 마세요.
8. 표 컬럼은 항상 6개 유지: 날짜(KST), 유형, 헤드라인, 출처,
   주가반응/영향, 교차확인.
```

### 3. 사용자 프롬프트 (user role, canonical 템플릿)

`backend/prompts/perplexity_prompt.md`의 7단계 구조 (`〈종목명〉` 플레이스홀더만 런타임 치환):

```markdown
# 한국 상장기업 〈종목명〉 스윙 트레이더 리포트

최우선: 최근 7일 주가 핵심 모멘텀 포착. KOSPI/KOSDAQ/KRX/KST 기준.
수치 중심, 한국어 작성.

## 🔥 Executive Summary
[상승/하락/횡보] | 핵심테마 | 주목이유 Top3 | 7일주가(%) | 핵심리스크
(200-300자, 수치중심, 추상어 금지)

## 📦 0단계: 사업 본질
- 주력제품/매출구성/주요고객/밸류체인/시장지위 표
- 기술차별점·진입장벽 | 산업연계 인과관계(예: HBM↑→수주+30%)
- 영업이익률·현금흐름

## ⚙️ 1단계: 최신 이벤트
최근 7일(72h 집중) ±5% 이상 이슈표:
  날짜(KST)/유형/헤드라인/출처/URL/주가반응/교차확인
톱티어2건+=확정, 단일출처=[루머], "관계자"언급=[루머]

## 💬 2단계: 시장 심리
최근 25일 키워드빈도표(급등/수주/실적/호재/악재/공매도)
긍부정비율 | 기대vs팩트 패턴

## 📈 3단계: 실적·밸류·수급·테크니컬
- 실적: 분기매출/영업익/이익률/컨센서스/일회성
- 밸류: PER업종비교+경쟁사
- 수급: 5일외국인/거래대금/공매도잔고
- 기술: MA정배열/RSI/ATR/VWAP

## 📅 5단계: Catalyst
이벤트캘린더(날짜/이벤트/유형/영향도/시급성)
전주 대비 변화(추가/소멸/수급/기술/심리)

## ⚠️ 6단계: 리스크
리스크표(유형/확률/영향범위/모니터링지표)
금지: 추상어·근거없는전망·매매권유

## 🧠 출력 규칙
Markdown+표+소제목 | 수치구간표현 | 인과관계명확 | 출처[1][2]표기
금지: 추상어·근거없는전망·출처없는수치·매매권유
```

**프롬프트 무결성 (NFR-004)**: `backend/prompts/perplexity_prompt.md`는 시스템 자산입니다. 변경 시 코드 리뷰 필수. 서버 시작 시 `〈종목명〉` 플레이스홀더 존재를 fail-fast로 검증합니다 (`backend/main.py::lifespan()`).

### 4. 환경 변수 설정

`.env` 파일에 다음을 설정합니다 (프로젝트 루트):

```bash
# 필수
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 선택 (비용 폭주 방지, 기본값 사용 권장)
AI_REPORT_DAILY_QUOTA=50   # 하루 최대 분석 횟수 (기본 50)
AI_REPORT_BURST_LIMIT=3    # 분당 최대 요청 수 (기본 3)
```

- API 키는 [Perplexity API 대시보드](https://www.perplexity.ai/settings/api)에서 발급
- 쿼터 초과 시 HTTP 429 반환 (자정 기준 KST 리셋)

### 5. 스트리밍 응답 처리

**백엔드** (`ai_report_service.py::stream_perplexity()`):
1. Perplexity SSE 응답을 라인 단위로 파싱
2. `sonar-reasoning-pro`의 `<think>...</think>` 블록은 버퍼 기반 상태머신으로 필터링 (사용자 노출 차단)
3. 최종 리포트 마크다운만 클라이언트에 yield
4. 스트림 완료 시 전체 내용을 파일로 자동 저장

**프론트엔드** (`frontend/src/api/aiReport.ts::createAiReportStream()`):
1. `fetch()` + `ReadableStream`으로 SSE 수신 (POST 지원)
2. CRLF/LF 혼합 대응 (`split(/\r\n|\r|\n/)`)
3. 빈 줄 = 이벤트 경계, 여러 `data:` 라인은 `\n`으로 조인 (SSE 스펙)
4. `event: done` 수신 시 완료, `event: error` 수신 시 에러 핸들러 호출
5. `AbortController`로 모달 close 시 즉시 중단 가능

### 6. 리포트 자동 저장

분석 완료 시 마크다운 파일로 자동 저장:

```
backend/reports/{종목명}/{YYYY-MM-DD}.md
backend/reports/{종목명}/{YYYY-MM-DD}_2.md  # 같은 날 재분석
backend/reports/{종목명}/{YYYY-MM-DD}_3.md
```

**저장 경로 안전성** (v1.1.4 CRITICAL 보안 대응):

- `_sanitize_name()`: 종목명을 파일시스템 안전 문자열로 변환
  - NFKC 유니코드 정규화
  - 금지 문자(`/\:*?"<>|`) + 제어 문자(`\x00-\x1f`) 제거
  - 경로 조작 시퀀스(`..`) → `_` 치환
  - Windows 예약명(CON, NUL, COM1-9, LPT1-9) `_` 접두사
  - 길이 100자 제한, 빈 문자열은 "report" 폴백
- `get_report_content()`: filename을 `^\d{4}-\d{2}-\d{2}(_\d+)?\.md$` 정규식으로 엄격 검증 + `resolve()` 후 보관 디렉토리 이탈 체크 (이중 방어)

`backend/reports/`는 `.gitignore` 처리되어 사용자 데이터로 분류.

### 7. 모델 계층 및 도달도

v1.1.6 기준 실측 품질 (공간(Spaces) 대비 %):

| 종목 유형 | 예시 | 도달도 | 비고 |
|----------|------|-------|------|
| 중소형 테마주 | 대한광통신 (010170) | **~75%** | 뉴스 집중, 단일 검색 충분 |
| 대형주 (일반) | 현대차 (005380) | **~65%** | 글로벌 이슈 양호 |
| 대형 전통산업 | SK텔레콤 (017670) | **~60-65%** | v1.1.5에서 v1.1.6으로 2배 개선 |

공간(Spaces) 대비 100% 도달은 내부적으로 `sonar-deep-research`(비동기 멀티패스) 필요 → Stage 3 옵션 (별도 SPEC 분리 대상, 비용 3-5배 증가).

### 8. 호출 비용

Perplexity API `sonar-reasoning-pro` 기준 (2025-2026 요율):

| 항목 | 단가 |
|------|------|
| 입력 토큰 | $2 / 1M |
| 출력 토큰 | $8 / 1M |
| 검색 요청 (high context) | ~$14 / 1K |
| **1회 분석 예상 비용** | **약 $0.05 (₩70)** |

하루 20건 분석 시 월 약 $30 (₩42,000) 수준. `AI_REPORT_DAILY_QUOTA` 환경변수로 일일 한도 설정 가능.

### 9. 응답 시간

- 첫 청크 도달: ~3-5초
- 전체 완료: ~40-60초 (대형주 품질 강화로 v1.1.6부터 약간 증가)
- 타임아웃: 180초

### 10. 에러 처리

| 상황 | HTTP | 동작 |
|------|------|------|
| API 키 미설정 | 503 | "AI 분석 서비스를 사용할 수 없습니다" |
| 잘못된 종목코드 | 404 | "종목을 찾을 수 없습니다" |
| 동시 분석 요청 (같은 종목) | 429 | "이미 분석이 진행 중입니다" |
| **일일 쿼터 초과** | 429 | "일일 쿼터 초과. 내일 다시 시도해 주세요." |
| **분당 버스트 초과** | 429 | "분당 요청 한도 초과. N초 후 다시 시도해 주세요." |
| Perplexity 장애 | SSE error | 재시도 버튼 표시 |
| 서버 시작 시 프롬프트 파일 이상 | — | **서버 시작 중단** (fail-fast) |

### 11. SPEC 버전 히스토리

`SPEC-AI-REPORT-001` 주요 변경:

| 버전 | 핵심 변경 |
|------|---------|
| 1.0.0 | 초기 SPEC: sonar-pro 모델, 기본 설정, 2탭 모달, 파일 저장 |
| 1.1.0 | 품질 개선: `search_context_size: high`, 도메인 필터, 시스템 프롬프트 강화 |
| 1.1.1 | 버그 수정: `search_domain_filter` 최대 20개 제한 준수 |
| 1.1.2 | 도메인 전략 반전: whitelist 폐기 → 최소 SNS 블랙리스트만 (공간 전략 일치) |
| 1.1.3 | 모델 전환: `sonar-pro` → `sonar-reasoning-pro`, `<think>` 블록 스트리밍 필터 |
| 1.1.4 | CRITICAL 보안: 경로 조작 방지, rate limiting(50/일+3/분), 회귀 테스트 26건 |
| 1.1.5 | 프롬프트 자산 이전: `docs/` → `backend/prompts/`, `@lru_cache`, fail-fast 검증 |
| 1.1.6 | 대형주 품질 격차: SYSTEM_PROMPT에 "검색 전략" 6관점 추가, SK텔레콤 도달도 30%→60-65% |

### 12. FS vs AI 버튼 역할 구분

| 구분 | FS (FnGuide) | AI (Perplexity) |
|------|-------------|-----------------|
| 데이터 출처 | FnGuide 웹 크롤링 (정형 재무) | Perplexity API 웹 검색 (뉴스·공시·분석) |
| 분석 방식 | S-RIM 정량 재무 계산 | 정성 분석 + 최신 이벤트 |
| 비용 | 무료 | ~$0.05/건 |
| 응답 시간 | 1-3초 (캐시 hit 시 즉시) | 40-60초 |
| 용도 | 펀더멘털 검증 | 모멘텀·테마·촉매 파악 |

두 기능은 상호 보완적입니다. FS로 정량 재무를 확인하고, AI로 최신 시장 심리와 촉매를 파악합니다.

### 13. 엔드포인트 요약

| 메서드 | 엔드포인트 | 설명 | 응답 |
|-------|----------|------|------|
| POST | `/api/ai-report/{code}` | AI 리포트 생성 (SSE 스트리밍) | `text/event-stream` |
| GET | `/api/ai-report/{code}/history` | 저장된 분석 이력 목록 | `{items: HistoryItem[]}` |
| GET | `/api/ai-report/{code}/{filename}` | 저장된 분석 파일 조회 | `{content, filename, date}` |

### 14. 테스트

```bash
# 회귀 테스트 (30건)
pytest backend/tests/test_ai_report_service.py -v

# 라이브 테스트 스크립트
python3 scripts/test_v113_service.py       # 서비스 직접 호출
python3 scripts/test_v116_sktelecom.py     # SK텔레콤 품질 검증
python3 scripts/test_perplexity.py v11 120 # API 파라미터 튜닝
```

## AI 기업 분석 v2: Deep Research (SPEC-AI-REPORT-002)

기존 Perplexity 단일 소스의 한계를 보완하기 위해 **Deep Research** 모드를 추가했습니다. 5개 검색 API를 병렬로 수집하고 Claude Code CLI로 합성한 정보 공간(Spaces) 수준의 심층 리포트를 제공합니다.

### 쉬운 설명: "AI가 무슨 일을 하는가?"

종목 차트 위에 있는 **🤖 AI 버튼**을 누르면 모달 창이 열리고, 두 가지 분석 모드 중 하나를 고를 수 있습니다.

| | 빠른 분석 | 심층 분석 |
|---|---|---|
| 비유하자면 | 한 명의 리서치 애널리스트에게 물어보기 | 5명의 리서처 + 1명의 시니어 애널리스트 팀에게 맡기기 |
| 동작 | Perplexity API 1회 호출 → 마크다운 | 웹 검색 5곳 병렬 수집 → Claude가 모두 읽고 교차 검증 → 합성 리포트 |
| 소요 시간 | 40~90초 | 3~5분 (Perplexity 캐시 hit 시 합성만 ~2분) |
| 비용 | ~$0.05/건 | ~$0.10~0.30/건 |
| 결과물 | Perplexity 답변(뉴스/테마/모멘텀) | 서술형 + 6컬럼 표 + 출처 교차 검증 + 리스크/촉매 분리 |
| 적합한 상황 | "어제 왜 올랐지?"처럼 빠른 확인 | "내일 진입할지 말지" 의사결정 직전의 꼼꼼한 검토 |

**중요 UX 원칙**: AI 버튼을 누르자마자 분석이 시작되지 않습니다. 모달이 열리고 사용자가 "빠른" 또는 "심층"을 선택한 뒤 **"분석 시작"** 버튼을 눌러야 과금이 발생합니다. (v1.0.3부터 명시적 시작 UX)

### 심층 분석 내부 흐름 (5단계)

```
 1. 사용자: "심층 분석 시작" 클릭
 2. 백엔드: 5개 검색 API에 병렬로 같은 종목 질의
      ├─ Perplexity  (sonar-reasoning-pro, AI 분석)
      ├─ Brave       (웹 검색 결과)
      ├─ Tavily      (심층 검색 + AI 요약)
      ├─ Naver       (한국어 뉴스/웹)
      └─ YouTube     (관련 영상)
 3. 백엔드: 5개 결과를 /tmp의 격리 폴더에 저장
      └─ summary.md + sources/{perplexity.md, brave.json, tavily.json, naver.json, youtube.json}
 4. Claude Code CLI: 위 폴더를 작업 디렉토리로 실행
      └─ 5개 파일을 모두 Read tool로 열고 교차 검증 → 마크다운 리포트
 5. 스트리밍: 각 단계를 SSE로 실시간 전송
      └─ 프론트 진행 상태 패널이 소스별 상태를 표시
```

### 진행 상태 패널 (v1.0.4부터)

심층 분석은 3~5분이 걸리므로 "정말 돌고 있는지" 알 수 없으면 답답합니다. v1.0.4부터는 모달 상단에 **진행 상태 패널**이 나타나 다음을 실시간으로 보여줍니다.

- 5개 소스의 상태 아이콘: ⏸ 대기 / ⏳ 진행 중 / ✅ 완료 / ❌ 실패
- 완료된 소스의 응답 시간 (예: `519ms`)과 수집 건수 (예: `18건`, Perplexity는 `5.4KB`)
- Perplexity가 캐시에서 재사용된 경우 **"캐시 재사용"** 라벨 (v1.0.3 시나리오 C)
- Claude 합성 단계 상태: `수집 대기 → 5개 소스 분석 중 → 생성 중`

동시 시작 → 완료되는 순서대로 하나씩 ✅로 전환 → 가장 느린 Perplexity(약 14초)가 수집의 critical path → 모든 소스가 ✅가 되면 🤖 Claude 합성 시작 → 첫 청크 도착하면 본문이 아래로 흐르기 시작.

### 캐시 재사용 시나리오 (같은 종목을 "빠른→심층"으로 연속 분석할 때)

1. 빠른 분석 완료 → Perplexity 전문(full markdown)을 **메모리 10분 TTL 캐시**에 저장
2. 10분 안에 같은 종목으로 심층 분석 시작
3. 심층 분석의 Perplexity 수집이 캐시 hit → HTTP 호출 0회, duration 0ms
4. 진행 상태 패널에 Perplexity 옆에 "캐시 재사용" 라벨 (cyan 강조)
5. 나머지 4개 소스만 새로 수집 + Claude 합성 → 비용/시간 절약

### 실패와 복구 (v1.0.5 안정화)

- **Perplexity 결제/쿼터 문제로 401·402·429 응답**: 해당 소스만 ❌ 표시 + `http_error` 라벨. 나머지 4개로 합성 계속 (최소 2/5 성공 게이트).
- **Claude CLI가 긴 stream-json을 내보내서 subprocess 버퍼 초과**: v1.0.5에서 subprocess limit을 64KB → 4MB로 상향. 이전엔 `LimitOverrunError`로 연결만 끊겨 "대기 중"에 멈춰 보였음.
- **합성 중 미처리 예외**: v1.0.5부터 모두 `event: error`로 감싸 프론트에 전달 → 에러 메시지 + "다시 시도" 버튼.
- **파일 기반 로그 가시화** (v1.0.5): `.dev-server.log`에 `backend.services.deep_research_service`의 per-source 수집/합성 타이밍이 INFO로 남아 운영 중 진단 가능.

### 개요

- **5-소스 병렬 수집**: Perplexity sonar-reasoning-pro + Brave Search + Tavily + Naver + YouTube
- **Claude CLI 헤드리스 합성**: `/tmp` 격리 환경에서 subprocess 실행 (기본 Sonnet, `AI_REPORT_DEEP_MODEL=opus` 가능)
- **SSE 스트리밍**: stream-json 파서를 통한 실시간 프론트엔드 전달
- **2단 모드 토글**: 모달에서 "빠른 분석(Perplexity)" / "심층 분석(Deep, 수분 소요)" 선택
- **Perplexity 캐시 재사용**: 빠른 모드 후 심층 모드 시 HTTP 호출 0 (비용 절감)

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  프론트엔드                                                  │
│  - AI 버튼 클릭                                              │
│  - 모달에서 "빠른" / "심층" 토글                             │
│  - "분석 시작" 버튼 (명시적)                               │
└────────────────┬────────────────────────────────────────────┘
                 │ POST /api/ai-report/{code}?mode=deep
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  라우터 (backend/routers/ai_report.py)                      │
│  - mode 파라미터 분기                                       │
│  - guard 체인 (코드 형식 → 종목 존재 → API key → 중복 → rate limit)
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  deep_research_collector.py                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐  ┌────────┐ │
│  │ Perplexity  │  │    Brave    │  │ Tavily │  │ Naver  │ │
│  │  (120s)     │  │   (15s)     │  │ (90s)  │  │ (15s)  │ │
│  └────────┬────┘  └──────┬──────┘  └───┬────┘  └───┬────┘ │
│           │               │              │           │      │
│  ┌────────┴───────────────┴──────────────┴───────────┴────┐ │
│  │         asyncio.gather (병렬 수집)                     │ │
│  │         ≥2/5 sources 필터링                           │ │
│  └───────────────────────┬──────────────────────────────┘ │
│                          │                                 │
│  /tmp/analysis_<code>_<uuid>/  스테이징 디렉토리         │
│  ├─ summary.md (stock metadata + collection status)       │
│  └─ sources/                                             │
│      ├─ perplexity.md                                    │
│      ├─ brave.json                                       │
│      ├─ tavily.json                                      │
│      ├─ naver.json                                       │
│      └─ youtube.json                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  claude_cli_streamer.py (subprocess)                        │
│                                                             │
│  claude -p "@summary.md" ... --output-format stream-json   │
│  ├─ synthesis prompt로 6컬럼 표 + 교차검증 마크다운        │
│  └─ stream-json 라인 → SSE 이벤트 어댑터                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  SSE 스트림 → 프론트엔드                                    │
│  ├─ data: <markdown chunk>                                │
│  ├─ event: done                                           │
│  └─ event: error (if any)                                 │
└─────────────────────────────────────────────────────────────┘
```

### 사용 흐름 (사용자 관점)

1. **AI 버튼 클릭** → 모달 오픈 (idle 상태, "분석 시작" 버튼 비활성)
2. **모드 선택**:
   - "빠른 분석" (기본): Perplexity 단일 API 사용 (~40-60초)
   - "심층 분석 (수분 소요)": 5-소스 병렬 + Claude 합성 (~3-5분)
3. **"분석 시작" 버튼 클릭** → 스트리밍 시작
4. **시나리오 C (캐시 재사용)**:
   - "빠른 분석" 완료 → Perplexity 결과 TTL 10분 메모리 캐시
   - 같은 종목의 "심층 분석" 선택 → "캐시된 결과 재사용" 힌트 표시
   - Perplexity HTTP 호출 0, 비용 절감

### 엔드포인트 업데이트

| 메서드 | 엔드포인트 | 쿼리 파라미터 | 설명 | 응답 |
|--------|-----------|--------------|------|------|
| POST | `/api/ai-report/{code}` | `mode=perplexity` (기본) | 빠른 분석 (Perplexity 단일 API) | `text/event-stream` |
| POST | `/api/ai-report/{code}` | `mode=deep` | 심층 분석 (5-소스 병렬 + Claude 합성) | `text/event-stream` |
| GET | `/api/ai-report/{code}/history` | — | 분석 히스토리 (기존 유지) | `[{filename, date, created_at}]` |
| GET | `/api/ai-report/{code}/{filename}` | — | 저장된 분석 조회 (기존 유지) | `{content, filename, date}` |

### 신규 환경변수 (Deep 모드)

```bash
# Deep 모드 검색 API 키 (필수)
BRAVE_API_KEY=
TAVILY_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
YOUTUBE_API_KEY=

# Deep 모드 운영 옵션 (선택, 기본값 사용 가능)
AI_REPORT_DEEP_DAILY_QUOTA=15        # 하루 최대 Deep 분석 횟수
AI_REPORT_DEEP_BURST_LIMIT=1         # 분당 최대 Deep 요청 수
AI_REPORT_DEEP_MODEL=sonnet          # 합성 모델 (sonnet 또는 opus)
```

기존 환경변수 (`PERPLEXITY_API_KEY`, `AI_REPORT_DAILY_QUOTA`, `AI_REPORT_BURST_LIMIT`)는 변경 없음.

### 의존성

**Deep 모드 활성화 필수**:
- Claude Code CLI 설치: `pip install --upgrade claude-code`
  - 없으면 Deep 모드는 HTTP 503 `claude_cli_missing` 반환
  - Perplexity 모드는 정상 작동

**dev 의존성 추가**:
- `pytest-asyncio` — async 테스트 지원

### 에러 처리

| 상황 | HTTP | 응답 |
|------|------|------|
| API 키 미설정 (Perplexity/검색 API) | 503 | "AI 분석 서비스를 사용할 수 없습니다" |
| 잘못된 종목코드 | 404 | "종목을 찾을 수 없습니다" |
| 동시 분석 요청 (같은 종목, 같은 모드) | 429 | "이미 분석이 진행 중입니다" |
| **Deep 일일 쿼터 초과** | 429 | "심층 분석 일일 쿼터 초과. 내일 다시 시도해 주세요." |
| **Deep 분당 burst 초과** | 429 | "심층 분석 분당 한도 초과. N초 후 다시 시도해 주세요." |
| Deep 모드: Claude CLI 미설치 | 503 | "서버에 Claude CLI가 설치되지 않아 심층 분석을 사용할 수 없습니다" |
| Deep 모드: 소스 수집 실패 (0-1/5) | 502 | "수집 실패: {N}/5 소스만 성공하여 합성 품질을 보장할 수 없습니다" |
| Deep 모드: Claude CLI 타임아웃 (10분) | 504 | "합성 시간 초과 (600초). 다시 시도하거나 빠른 분석을 사용해 주세요." |
| Perplexity/검색 API 장애 | SSE error | 재시도 버튼 표시 |

### FS vs AI 버튼 역할 구분

| 구분 | FS (FnGuide) | AI 빠른 | AI 심층 |
|------|-------------|--------|--------|
| 데이터 출처 | FnGuide 크롤링 | Perplexity API | 5-소스 병렬 (Perplexity+Brave+Tavily+Naver+YouTube) |
| 분석 방식 | S-RIM 정량 | Perplexity AI | Claude CLI 합성 (Sonnet/Opus) |
| 비용 | 무료 | ~$0.05/건 | ~$0.10-0.30/건 (5 API + Claude) |
| 응답 시간 | 1-3초 | 40-90초 | 3-5분 (캐시 hit 시 1초) |
| 용도 | 펀더멘털 검증 | 모멘텀·테마·촉매 | 6컬럼 표 + 교차 검증 + 리스크 분석 |

### 테스트

```bash
# SPEC-001 회귀 테스트 (기존 유지)
pytest backend/tests/test_ai_report_service.py -v

# SPEC-002 Deep 파이프라인 테스트
pytest backend/tests/test_claude_cli_streamer.py -v
pytest backend/tests/test_deep_research_collector.py -v
pytest backend/tests/test_deep_research_service.py -v
pytest backend/tests/test_ai_report_router_deep_mode.py -v

# 프론트엔드
cd frontend && npm test -- --run

# Playwright e2e (Deep 모드 시나리오)
cd frontend && npx playwright test e2e/ai-report-deep.spec.ts
```

### SPEC 버전 히스토리

| 버전 | 핵심 변경 |
|------|---------|
| 1.0.0 | 초기 SPEC: 5-소스 병렬 + Claude CLI 합성 + 2단 토글 |
| 1.0.1 | Claude CLI timeout 600s, 인자 보정 (--cwd→--add-dir), source별 timeout, sonnet 명시 |
| 1.0.2 | Naver/YouTube에 종목 코드, synthesis prompt 절대규칙 (학습 데이터/면책 차단) |
| 1.0.3 | 명시적 모드 선택 UX, Perplexity 캐시 재사용 (시나리오 C) |
| 1.0.4 | 심층 분석 진행 상태 패널 (per-source SSE `event: phase`, 5소스 + 합성 단계 실시간 시각화, 캐시 재사용 라벨) |
| 1.0.5 | 합성 단계 LimitOverrunError 방어 (subprocess limit 4MB), 미처리 예외 `event: error` 변환, INFO 로그 가시화 |

---

## 라이선스

Private - 로컬 전용.