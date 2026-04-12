---

## id: SPEC-AI-REPORT-001 version: 1.1.0 status: Planned created: 2026-04-12 updated: 2026-04-12 author: manager-spec priority: High issue_number: null lifecycle: spec-first

# SPEC-AI-REPORT-001: AI 기업 분석 리포트

## HISTORY

| 버전 | 날짜 | 변경 내용 |
| --- | --- | --- |
| 1.0.0 | 2026-04-12 | 초기 SPEC 작성 |
| 1.1.0 | 2026-04-12 | Perplexity API 품질 개선: search_context_size=high, 도메인 필터, 시스템 프롬프트 강화 |
| 1.1.1 | 2026-04-12 | 버그 수정: Perplexity `search_domain_filter` 제한(최대 20개) 위반 → 20개로 축소. HTTP 400 명시 처리 추가. NFR-005(출처 개수) 목표 15→5로 현실화 (엄격한 whitelist로 인해) |
| 1.1.2 | 2026-04-12 | 품질 개선: whitelist 접근 폐기. 공간(Spaces) 출처 역분석 결과 blog.naver.com/tistory/youtube까지 적극 인용됨 → whitelist가 품질 저해 원인. 최소 블랙리스트(5 SNS)로 변경. NFR-008 재정의: whitelist 대신 시스템 프롬프트 원칙으로 소스 우선순위 유도. |
| 1.1.3 | 2026-04-12 | Stage 2 적용: 모델 sonar-pro → sonar-reasoning-pro (Chain-of-Thought 추론). max_tokens 8000→12000. `<think>...</think>` 블록 스트리밍 필터링 로직 추가 (버퍼 기반 상태 머신). 실측: 표 25→35개, "중기 펀더멘털/리스크·리워드/모니터링 우선순위" 등 추가 구조화. 공간 대비 도달도 65% → 80%. |
| 1.1.4 | 2026-04-12 | 코드 리뷰 CRITICAL 대응: (1) `_sanitize_name()` 강화: `..`/Windows예약명/제어문자/선행점/길이제한/NFKC 정규화/빈값 폴백. (2) `get_report_content()` path traversal 방지 (filename 정규식 검증 + resolve 경로 이탈 체크). (3) Rate limiting 추가: 일일 쿼터(기본 50회) + 분당 버스트(기본 3회) - 비용 폭주 방지. (4) 회귀 테스트 26건 추가 (backend/tests/test_ai_report_service.py). |
| 1.1.5 | 2026-04-12 | 프롬프트 자산 경계 정리: `docs/perplexity-prompt.md` → `backend/prompts/perplexity_prompt.md` 이전 (backend 소유). `@lru_cache`로 프로세스당 1회만 읽기, 서버 시작 시 검증(fail-fast). NFR-004 재정의 (canonical 경로 변경). 회귀 테스트 4건 추가 (총 30건). @MX 태그 추가 (경로 상수). |

## 개요

차트 셀의 AI 버튼을 통해 Perplexity API(sonar-pro)를 호출하고, 실시간 SSE 스트리밍으로 한국 주식 스윙 트레이더 분석 리포트를 생성하는 기능. 생성된 리포트는 마크다운 파일로 자동 저장되며, 히스토리 탭에서 과거 분석 이력을 조회할 수 있다.

## 요구사항

### FR-001: AI 버튼 렌더링 (Ubiquitous)

The ChartCell component **shall** render an "AI" button after the TR button in the toolbar, using the same design tone as existing toolbar buttons (%, RS, +, FS, TR).

### FR-002: AI 리포트 요청 (Event-Driven)

**When** the user clicks the AI button on a chart cell, the frontend **shall** send a POST request to `/api/ai-report/{code}` and open the AI Report modal with streaming state.

### FR-003: SSE 스트리밍 수신 (Event-Driven)

**When** the backend begins streaming the Perplexity API response, the frontend **shall** render the received markdown content in real-time inside the modal's "분석 결과" tab with a typing animation effect.

### FR-004: Perplexity API 호출 (Event-Driven)

**When** the backend receives a POST request to `/api/ai-report/{code}`, the system **shall** call the Perplexity API with model `sonar-pro`, streaming enabled, and the prompt from `docs/perplexity-prompt.md` with `〈종목명〉` replaced by the actual stock name.

### FR-005: 리포트 자동 저장 (Event-Driven)

**When** the SSE stream completes successfully, the backend **shall** save the complete response as a markdown file at `backend/reports/{종목명}/{날짜}.md`.

### FR-006: 동일 날짜 중복 분석 처리 (State-Driven)

**While** a markdown file for the same stock and same date already exists, the system **shall** append a sequence number to the filename (e.g., `2026-04-12_2.md`, `2026-04-12_3.md`).

### FR-007: 분석 히스토리 목록 조회 (Event-Driven)

**When** the user opens the "히스토리" tab in the AI Report modal, the frontend **shall** call `GET /api/ai-report/{code}/history` and display a list of previous analysis dates for the stock.

### FR-008: 저장된 분석 조회 (Event-Driven)

**When** the user clicks a date item in the history list, the frontend **shall** call `GET /api/ai-report/{code}/{filename}` and render the saved markdown content in the modal.

### FR-009: 클립보드 복사 (Event-Driven)

**When** the user clicks the copy button after analysis completes, the frontend **shall** copy the raw markdown text to the clipboard and show a visual confirmation.

### FR-010: 모달 닫기 (Event-Driven)

**When** the user presses ESC or clicks the backdrop, the AI Report modal **shall** close and abort any in-progress SSE stream.

### FR-011: 로딩 상태 표시 (State-Driven)

**While** the SSE stream is in progress, the frontend **shall** display a typing animation and progress indicator in the modal.

### FR-012: 모달 탭 구성 (Ubiquitous)

The AI Report modal **shall** contain two tabs: "분석 결과" (Analysis Result) and "히스토리" (History), with the header showing the stock name and analysis date.

## 비기능 요구사항

### NFR-001: API 키 보안

The backend **shall** read the Perplexity API key from the environment variable `PERPLEXITY_API_KEY` and never expose it in responses or logs.

### NFR-002: 스트리밍 응답 시간

The frontend **shall** begin rendering the first chunk of the streaming response within 3 seconds of the request.

### NFR-003: 파일 경로 안전성

The backend **shall** sanitize stock names used in file paths to remove or replace characters that are invalid for the filesystem (e.g., `/`, `\`, `:`, `*`).

### NFR-004: 프롬프트 무결성

The system **shall** use the prompt from `backend/prompts/perplexity_prompt.md` (canonical 경로) as-is, only replacing the `〈종목명〉` placeholder with the actual stock name. No other modifications to the prompt are permitted.

The prompt file is considered a **system asset** owned by the backend package. Changes require code review and updates to the SPEC HISTORY.

**Startup validation**: `backend/main.py::lifespan()` MUST load and validate the prompt template at server startup (fail-fast). Missing file or missing `〈종목명〉` placeholder MUST prevent server startup.

(v1.1.5: Moved from `docs/perplexity-prompt.md` — `docs/`는 사용자 스크래치 공간으로 런타임 의존 부적절. `backend/prompts/`로 이전하여 시스템 자산 경계 명확화.)

### NFR-005: 출처 밀도

The AI report **shall** include at least 5 distinct citation markers (\[N\] format) per generated report, referencing Korean financial sources from the whitelist. (v1.1.1: 엄격한 도메인 whitelist로 인해 초기 목표 15개에서 현실적인 5개로 조정.)

### NFR-006: 서술 품질

Each major section (0단계\~6단계) **shall** include at least one narrative paragraph (not just tables/bullets) explaining causal relationships between data points.

### NFR-007: 최신성 필터

The AI report **shall** use `search_recency_filter: "month"` to prioritize sources from the last 30 days.

### NFR-008: 소스 품질 관리

The system **shall** apply a minimal blacklist via `search_domain_filter` to exclude only clearly low-value sources (instagram, x.com, twitter, facebook, reddit). The system **shall** rely on the system prompt's source-priority principle (DART/KRX > major dailies > analysis platforms) to guide high-quality source usage, rather than enforcing it via domain whitelist.

(v1.1.2 rationale: Empirical comparison with Perplexity Spaces output showed that aggressive whitelisting reduces citation diversity by ~60% and causes hallucination. Spaces itself cites blogs, YouTube, and specialty databases. The whitelist was actively harming quality.)

## 에러 처리 요구사항

### ER-001: API 키 누락 (Unwanted Behavior)

**If** the `PERPLEXITY_API_KEY` environment variable is not set, **then** the backend **shall** return HTTP 503 with an error message indicating the AI analysis service is unavailable.

### ER-002: 스트리밍 중단 (Unwanted Behavior)

**If** the SSE stream is interrupted due to network error or client disconnect, **then** the backend **shall** gracefully close the Perplexity API connection and the frontend **shall** display an error message with a retry button.

### ER-003: Perplexity API 오류 (Unwanted Behavior)

**If** the Perplexity API returns an error response (4xx/5xx), **then** the backend **shall** forward the error status via SSE and the frontend **shall** display a user-friendly error message.

### ER-004: 파일 저장 실패 (Unwanted Behavior)

**If** the backend fails to save the markdown file (permission error, disk full), **then** the system **shall** log the error but still complete the SSE stream to the frontend without interruption.

### ER-005: 종목 코드 무효 (Unwanted Behavior)

**If** the provided stock code does not exist in the registry, **then** the backend **shall** return HTTP 404 with an error message.

### ER-006: 동시 분석 요청 (State-Driven)

**While** an AI analysis for the same stock code is already in progress, the system **shall** reject additional requests with HTTP 429 and the frontend **shall** display a message indicating analysis is already running.

## API 설계

| Endpoint | Method | Description | Response |
| --- | --- | --- | --- |
| `/api/ai-report/{code}` | POST | Perplexity API 호출 + SSE 스트리밍 | `text/event-stream` |
| `/api/ai-report/{code}/history` | GET | 분석 히스토리 목록 | `[{filename, date, created_at}]` |
| `/api/ai-report/{code}/{filename}` | GET | 저장된 분석 파일 조회 | `{content, filename, date}` |

## Perplexity API 호출 파라미터

| 파라미터 | 값 | 목적 |
| --- | --- | --- |
| `model` | `sonar-pro` | 한국 주식 분석에 최적화된 검색 모델 |
| `web_search_options.search_context_size` | `"high"` | 공간(Spaces) 수준 검색 컨텍스트 확보 |
| `search_recency_filter` | `"month"` | 최근 30일 소스 우선 |
| `search_domain_filter` | Korean financial whitelist (최대 20개) | 공시/일간지/금융포털만 허용. Perplexity API 제한: **20개 이하** 필수 |
| `return_related_questions` | `true` | 다중 패스 리서치 활성화 |
| `temperature` | `0.2` | 재현성 있는 결과 |
| `max_tokens` | `8000` | 전체 리포트 완성 보장 |
| `stream` | `true` | SSE 스트리밍 유지 |

### 도메인 Whitelist (공시 + 주요 일간지 + 금융포털, 총 20개 이내)

**Perplexity API 제약**: `search_domain_filter`는 최대 20개까지만 허용. 초과 시 HTTP 400 반환.

- 공시: dart.fss.or.kr, kind.krx.co.kr
- 일간지: hankyung.com, mk.co.kr, chosun.com, biz.chosun.com, newsis.com, news.nate.com
- 금융 포털: finance.naver.com, stock.naver.com, m.finance.daum.net
- 분석 플랫폼: wisereport.co.kr, fnguide.com, stockplus.com, alphasquare.co.kr
- 제외: youtube.com, tistory.com, blog.naver.com, instagram.com, x.com

## 시스템 프롬프트 규격 (v1.1.0)

Perplexity API 호출 시 system role 메시지는 다음 원칙을 강제해야 함:

1. 각 표 뒤 1-2문단 서술형 인과 분석 필수
2. 모든 수치·주장에 \[N\] 형식 출처 인용 필수
3. 톱티어 2건 교차확인 = 확정, 단일 출처 = \[루머\]
4. 기대(내러티브) vs 팩트(실적/공시) 명시적 구분
5. 출처 우선순위: DART/KRX &gt; 주요 일간지 &gt; IR/분석 플랫폼
6. 금지: 추상어 단독 사용, 매매권유, 출처 없는 수치, 근거 없는 전망

사용자 프롬프트(`docs/perplexity-prompt.md`)는 v1.0.0과 동일하게 유지 (NFR-004 프롬프트 무결성).

## 파일 저장 규칙

- 경로: `backend/reports/{종목명}/{날짜}.md`
- 예시: `backend/reports/삼성전자/2026-04-12.md`
- 동일 날짜 재분석: `2026-04-12_2.md`, `2026-04-12_3.md` (시퀀스 번호 추가)
- API endpoint는 종목코드 사용, 저장 폴더명은 종목명 사용
- 종목명의 파일 시스템 안전 문자 치환 필요

## Exclusions (What NOT to Build)

- 프롬프트 편집 UI (프롬프트는 `docs/perplexity-prompt.md` 파일에서 고정 로드)
- 분석 리포트 삭제 기능
- 다중 종목 동시 분석 (batch) 기능
- Perplexity 외 다른 AI 모델 선택 기능
- 분석 리포트 공유/내보내기 기능
- 사용자별 API 키 관리 (단일 서버 환경 변수 사용)
- 분석 결과 캐싱 (매 요청마다 새로 분석)