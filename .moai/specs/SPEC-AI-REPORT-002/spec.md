---
id: SPEC-AI-REPORT-002
version: 1.0.0
status: Planned
created: 2026-04-16
updated: 2026-04-16
author: manager-spec
priority: High
issue_number: null
lifecycle: spec-first
---

# SPEC-AI-REPORT-002: AI 리포트 Deep-Research 합성 파이프라인

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| 1.0.0 | 2026-04-16 | 초기 SPEC 작성 — 5소스 병렬 수집 + Claude CLI 합성 파이프라인 |
| 1.0.1 | 2026-04-16 | 시간 예산 완화 (NFR-002/FR-007: 90/180s → 300/600s), 프론트 라벨 "수분 소요"로 변경. claude CLI 인자 보정 (`--cwd` → `--add-dir`+subprocess `cwd=`+`--permission-mode bypassPermissions`+`--model claude-sonnet-4-6` 명시). collector source별 timeout 분리 (perplexity 120s, tavily 90s, brave/naver/youtube 15s). |

---

## 개요

기존 SPEC-AI-REPORT-001(Perplexity 단일 소스)의 한계를 보완하기 위해, "심층 분석(Deep)" 모드를 추가한다. Python이 5개 검색 API(Perplexity/Brave/Tavily/Naver/YouTube)를 병렬 수집하여 `/tmp/<uuid>` 디렉토리에 스테이징하고, Claude Code 헤드리스 CLI(`claude -p`)를 1회 fork-exec하여 합성 리포트를 생성·SSE 스트리밍으로 프론트엔드에 전달한다.

**핵심 설계 결정 (사용자 승인 완료)**:
1. SPEC-ID: SPEC-AI-REPORT-002 (기존 SPEC-AI-REPORT-001 v1.1.6 연번)
2. 합성 모델: Sonnet 기본 + `AI_REPORT_DEEP_MODEL=opus` 환경변수로 승격 가능
3. 프론트 UX: 명시적 2단 토글 "빠른 분석(Perplexity)" / "심층 분석(Deep, ~90s)"
4. 하네스 범위: `/tmp` 격리 only — `.claude/agents`·`.claude/skills` 영구 등록 없음

---

## 요구사항

### FR-001: Deep 모드 엔드포인트 분기 (Event-Driven)

**When** the user sends `POST /api/ai-report/{code}?mode=deep`, the backend **shall** route the request to the Deep Research pipeline instead of the existing Perplexity pipeline, while preserving all existing guard checks (code format → stock existence → API key → duplicate → rate limit).

**When** `mode` is absent or `mode=perplexity`, the backend **shall** route to the existing Perplexity pipeline without any behavioral change.

### FR-002: 5-소스 병렬 수집 (Event-Driven)

**When** the Deep pipeline is triggered, the backend **shall** concurrently fetch all 5 sources using `httpx.AsyncClient` and `asyncio.gather`:
- Perplexity `sonar-reasoning-pro` (non-streaming, full response)
- Brave Search (20 results, English + Korean queries)
- Tavily (advanced depth, `include_answer=true`, 20 results)
- Naver Web/News (Korean, 10 results)
- YouTube Data API v3 (video metadata, 10 results)

**When** at least 2 of 5 sources succeed, the pipeline **shall** proceed to staging. **When** fewer than 2 sources succeed, the backend **shall** return HTTP 502 with an SSE `error` event.

### FR-003: 컨텍스트 스테이징 (Event-Driven)

**When** source collection succeeds (≥2/5), the backend **shall** create an isolated staging directory at `/tmp/analysis_<code>_<ISO8601-UTC>_<uuid8>/` containing:
- `summary.md` — stock metadata + source collection status table + synthesis instructions
- `sources/perplexity.md` — `<think>` blocks stripped
- `sources/brave.json`, `sources/tavily.json`, `sources/naver.json`, `sources/youtube.json` (present only if source succeeded)

**When** a source fails, the backend **shall** omit its file and record failure in `summary.md` without aborting the pipeline.

### FR-004: Claude CLI 헤드리스 합성 (Event-Driven)

**When** staging is complete, the backend **shall** invoke the Claude CLI as a subprocess:
```
claude -p "@summary.md 먼저 읽고, sources/ 하위 파일 전체를 교차 검증하여 한국 스윙 트레이딩 리포트 마크다운을 생성하라."
  --cwd /tmp/analysis_<code>_<uuid>
  --append-system-prompt "$(cat backend/prompts/stock_synthesis_prompt.md)"
  --allowedTools "Read,Grep,Glob"
  --output-format stream-json
  --verbose
```

**When** the `AI_REPORT_DEEP_MODEL` environment variable is set to `opus`, the backend **shall** add `--model claude-opus-4-6` to the CLI invocation.

### FR-005: stream-json → SSE 어댑터 (Event-Driven)

**When** the Claude CLI process writes `stream-json` lines to stdout, the backend **shall** parse each line and forward to the client as SSE events:
- `type=assistant` + `content[].type=text` → `data: <text chunk>`
- `type=result` → `event: done\ndata: \n\n`
- `type=system` + `subtype=error` → `event: error\ndata: <message>\n\n`
- Unknown types → silently ignored (defensive parsing)

**When** a line fails JSON parsing, the backend **shall** log the line at WARNING level and continue streaming.

### FR-006: 리포트 자동 저장 (Event-Driven)

**When** the Deep synthesis stream completes successfully, the backend **shall** save the complete markdown to `backend/reports/<stock_name>/<date>.md` using the existing `save_report()` function from `ai_report_service.py`.

### FR-007: 프로세스 타임아웃 및 좀비 방지 (State-Driven)

**While** the Claude CLI process is running, the backend **shall** enforce a 600-second (10-minute) timeout using `asyncio.wait_for`. **When** the timeout expires, the backend **shall** call `proc.terminate()`, wait up to 15 seconds, then call `proc.kill()` if still running, and emit an SSE `error` event.

> History: v1.0.0은 180s hard timeout이었으나, 실제 5-소스 + 6컬럼 표 합성이 Sonnet으로 180초 안에 완료되지 않는 사례가 다수 확인되어 v1.0.1에서 600s로 완화. Deep 분석은 의도적으로 무거운 작업으로 사용된다는 운영 결정.

**When** the client disconnects (CancelledError), the backend **shall** terminate the subprocess and clean up the staging directory in a `finally` block.

### FR-008: Deep 모드 전용 Rate Limit (State-Driven)

**While** Deep mode is active, the backend **shall** enforce a separate quota:
- Daily limit: `AI_REPORT_DEEP_DAILY_QUOTA` (default: 15)
- Burst limit: `AI_REPORT_DEEP_BURST_LIMIT` (default: 1 per minute)

The existing `check_rate_limit()` for Perplexity mode **shall** remain unchanged.

### FR-009: Claude CLI 가용성 게이트 (State-Driven)

**While** the server is starting up (lifespan), the backend **shall** call `shutil.which("claude")` and log a WARNING if the binary is not found. **When** a Deep mode request arrives and `claude` binary is absent, the backend **shall** return HTTP 503 with error `"claude_cli_missing"`.

**When** `claude` binary is absent, Perplexity mode **shall** continue to function normally without disruption.

### FR-010: 합성 전용 프롬프트 (Ubiquitous)

The system **shall** use `backend/prompts/stock_synthesis_prompt.md` as the system prompt for Claude synthesis. This file is distinct from `backend/prompts/perplexity_prompt.md` and **shall** never overwrite it.

The synthesis prompt **shall** instruct Claude to:
- Output only markdown report body (no preamble, no JSON wrapping)
- Use `[brave]`, `[tavily]`, `[naver]`, `[youtube]` citation labels
- Cross-verify Perplexity analysis against other sources
- Maintain the 6-column table format from SPEC-AI-REPORT-001

### FR-011: 프론트엔드 2단 토글 (Ubiquitous)

The AI Report Modal **shall** include an explicit mode selector with two options:
- "빠른 분석" (Perplexity, default)
- "심층 분석 (수분 소요)" (Deep)

The mode selector **shall** be displayed in the modal header area and **shall** be disabled while streaming is in progress.

### FR-012: SSE 이벤트 계약 호환성 (Ubiquitous)

The Deep mode SSE event contract **shall** be identical to the existing Perplexity mode contract:
- Default event: markdown text chunk (data only)
- `event: done`: stream complete
- `event: error`: error message

An optional `event: phase` **shall** be emitted during collection phase with progress data `{"phase":"collecting","progress":0.0-1.0}`. Frontend **shall** silently ignore unknown event types.

### FR-013: /tmp 정리 (State-Driven)

**While** the server starts up (lifespan), the backend **shall** scan `/tmp` for `analysis_*` directories older than 7 days and delete them.

**When** a Deep analysis completes (success or error), the backend **shall** optionally preserve the staging directory for 24 hours for debugging, then clean up.

---

## 비기능 요구사항

### NFR-001: 첫 토큰 응답 시간

The frontend **shall** begin rendering the first chunk within 3 seconds after Claude CLI starts generating output (collection phase not counted).

### NFR-002: 전체 소요 시간 (v1.0.1 완화)

Average end-to-end time (from request to `done` event) **shall** be ≤ 300 seconds (5 minutes). Hard timeout is 600 seconds (10 minutes).

> v1.0.0은 90초 평균 / 180초 hard timeout 이었으나, Sonnet의 5-소스 + 6컬럼 표 합성이 이 예산 안에 끝나지 않아 v1.0.1에서 완화. Deep 분석은 무거운 작업이라는 사용자 결정 반영.

### NFR-003: 프로세스 격리

Each Deep analysis request **shall** use a unique UUID-based `/tmp` directory. Cross-request interference **shall** be impossible by construction.

### NFR-004: 보안 — Claude CLI 도구 제한

The Claude CLI invocation **shall** use `--allowedTools "Read,Grep,Glob"` to prevent any writes, Bash execution, or web requests during synthesis.

API keys for search APIs **shall** be passed via environment variables, never as CLI arguments.

### NFR-005: 보안 — /tmp 경로 안전성

The staging directory name **shall** include a UUID8 suffix to prevent predictable path collisions. The backend **shall** validate that the staging path resolves under `/tmp` before use.

### NFR-006: 관찰성

The backend **shall** log the following metrics per Deep analysis request:
- Phase 1 (collection): per-source success/failure status and duration
- Phase 3 (synthesis): Claude CLI exit code and total token count (from `stream-json` result event)
- Total end-to-end duration

### NFR-007: 합성 품질 — Graceful Degradation

**When** fewer than 5 sources succeed, Claude **shall** produce a report using available sources, explicitly noting missing sources in the synthesis. A 2-source minimum (FR-002) ensures baseline quality.

### NFR-008: 배포 이식성

Deep mode **shall** be gated on `shutil.which("claude")`. Servers without Claude CLI installed **shall** serve Perplexity mode normally. Documentation **shall** specify Claude CLI as a Deep-mode-only dependency.

---

## 에러 처리 요구사항

### ER-001: 환경변수 누락 (Unwanted Behavior)

**If** any required search API key (`BRAVE_API_KEY`, `TAVILY_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `YOUTUBE_API_KEY`) is missing, **then** that source **shall** be skipped (counted as failure) and its absence noted in `summary.md`. The pipeline continues if ≥2 other sources succeed.

### ER-002: 소스 수집 실패 게이트 (Unwanted Behavior)

**If** fewer than 2 of 5 sources succeed, **then** the backend **shall** return an SSE `error` event with message `"수집 실패: {N}/5 소스만 성공하여 합성 품질을 보장할 수 없습니다."` and HTTP 502.

### ER-003: claude 바이너리 부재 (Unwanted Behavior)

**If** `shutil.which("claude")` returns None at request time, **then** the backend **shall** return HTTP 503 with `{"error": "claude_cli_missing", "detail": "서버에 Claude CLI가 설치되지 않아 심층 분석을 사용할 수 없습니다."}`.

### ER-004: CLI 타임아웃 (Unwanted Behavior)

**If** the Claude CLI process exceeds 600 seconds (v1.0.1 기준), **then** the backend **shall** terminate the process and emit `event: error` with a Korean message that includes the actual configured timeout value (currently `"합성 시간 초과 (600초). 다시 시도하거나 빠른 분석을 사용해 주세요."`). 메시지의 초 단위 값은 streamer가 동적으로 채운다.

### ER-005: 클라이언트 연결 끊김 (Unwanted Behavior)

**If** the client disconnects during streaming, **then** the backend **shall** catch `CancelledError`, terminate the Claude CLI subprocess, and clean up the staging directory.

### ER-006: 동시 Deep 분석 요청 (State-Driven)

**While** a Deep analysis for the same stock code is already in progress, the system **shall** reject additional Deep requests with HTTP 429 and message `"{stock_name}({code}) 심층 분석이 이미 진행 중입니다."`.

---

## API 설계

| Endpoint | Method | Query Param | Description | Response |
|---|---|---|---|---|
| `/api/ai-report/{code}` | POST | `mode=perplexity` (default) | 기존 Perplexity 분석 | `text/event-stream` |
| `/api/ai-report/{code}` | POST | `mode=deep` | Deep Research 합성 분석 | `text/event-stream` |
| `/api/ai-report/{code}/history` | GET | — | 분석 히스토리 (기존 유지) | `[{filename, date, created_at}]` |
| `/api/ai-report/{code}/{filename}` | GET | — | 저장된 분석 조회 (기존 유지) | `{content, filename, date}` |

### Deep 모드 SSE 이벤트 스키마

```
# 수집 진행 (선택적, 프론트가 무시해도 됨)
event: phase
data: {"phase":"collecting","source":"perplexity","progress":0.2}

# 마크다운 청크 (기존과 동일)
data: # 삼성전자 스윙 트레이딩 리포트\n\n

# 완료 (기존과 동일)
event: done
data:

# 에러 (기존과 동일)
event: error
data: 오류 메시지
```

---

## 신규 파일 목록

| 파일 | 위치 | 역할 |
|---|---|---|
| `deep_research_collector.py` | `backend/services/` | Phase 1: 5-소스 병렬 수집 + 스테이징 |
| `claude_cli_streamer.py` | `backend/services/` | Phase 3-4: CLI 호출 + stream-json 파서 + SSE 어댑터 |
| `deep_research_service.py` | `backend/services/` | Phase 1-5 오케스트레이션, SSE 제너레이터 |
| `stock_synthesis_prompt.md` | `backend/prompts/` | Claude 합성 전용 시스템 프롬프트 |
| `test_deep_research_service.py` | `backend/tests/` | Deep 파이프라인 단위/통합 테스트 |

### 수정 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `backend/routers/ai_report.py` | `mode: str = Query("perplexity")` 파라미터 추가, deep 분기 |
| `backend/main.py` | lifespan에 `shutil.which("claude")` 체크 + `stock_synthesis_prompt.md` fail-fast 검증 추가 |
| `frontend/src/components/AiReportModal.tsx` | 헤더에 2단 토글(빠른/심층) 추가 |
| `frontend/src/hooks/useAiReport.ts` | `startStream(code, mode)` 시그니처 확장 |
| `frontend/src/api/aiReport.ts` | URL에 `?mode=${mode}` 추가 |

### 보존 대상 (수정 금지)

| 파일 | 이유 |
|---|---|
| `backend/services/ai_report_service.py` | SPEC-001 기존 함수 무변경 (stream_perplexity, check_rate_limit, SYSTEM_PROMPT) |
| `backend/prompts/perplexity_prompt.md` | NFR-004 프롬프트 무결성 |
| `backend/routers/ai_report.py:32-106` 기존 로직 | 기존 generate_report 가드 체인 순서 보존 |

---

## 환경변수 설계

```
# 기존 (변경 없음)
AI_REPORT_DAILY_QUOTA=50
AI_REPORT_BURST_LIMIT=3

# 신규 — Deep 모드 전용
AI_REPORT_DEEP_DAILY_QUOTA=15
AI_REPORT_DEEP_BURST_LIMIT=1
AI_REPORT_DEEP_MODEL=sonnet          # 기본값; "opus"로 변경 시 Opus 사용

# 신규 — 검색 API 키
BRAVE_API_KEY=
TAVILY_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

---

## @MX 태그 계획

### ANCHOR 대상 (신규 함수, fan_in >= 2 예측)

| 함수 | 파일 | 이유 |
|---|---|---|
| `orchestrate_deep_analysis()` | `deep_research_service.py` | 라우터 SSE 핸들러 + 테스트에서 직접 호출 |
| `stream_claude_synthesis()` | `claude_cli_streamer.py` | 오케스트레이터 + 테스트 |
| `check_deep_rate_limit()` | `deep_research_service.py` | 라우터 + 테스트 |

### WARN 대상

| 위치 | 위험 이유 |
|---|---|
| `_active_deep_analyses: set` | 멀티워커 전역 상태 (`_active_analyses`와 동일 패턴) |
| `asyncio.create_subprocess_exec` 호출부 | subprocess 좀비, 타임아웃 경쟁 조건 |
| `/tmp` 디렉토리 쓰기 블록 | 디스크 포화, UUID 충돌(이론적) |

---

## Exclusions (What NOT to Build)

- 상주 Claude Code 세션/데몬 — 본 SPEC은 1회성 fork-exec만 다룬다
- `.claude/agents/` 또는 `.claude/skills/`에 신규 하네스 영구 등록 (PoC 범위 외)
- Perplexity 모드 스키마/프롬프트/rate limit 구조 수정
- 서버사이드 벡터 DB / RAG 구축
- Deep 모드 전용 리포트 저장 경로 분리 (기존 `backend/reports/` 통합 사용)
- 자동 폴백 (빠른 분석 실패 시 심층 자동 전환) — 명시적 사용자 선택만 허용
