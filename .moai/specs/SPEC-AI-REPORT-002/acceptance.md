# SPEC-AI-REPORT-002 인수 기준 (Acceptance Criteria)

EARS 형식 기반 인수 시나리오. 모든 시나리오는 Given/When/Then 구조로 검증 가능해야 한다.

---

## AC-001: mode 파라미터 기본값 (FR-001)

**Given** an existing Perplexity mode request with no `mode` query parameter  
**When** `POST /api/ai-report/005930` is received  
**Then** the backend routes to the Perplexity pipeline (unchanged behavior), and the response SSE events are identical to pre-SPEC-002 behavior

**Given** `POST /api/ai-report/005930?mode=perplexity`  
**When** processed by the router  
**Then** the Perplexity pipeline is invoked (same as no `mode` parameter)

---

## AC-002: Deep 모드 분기 진입 (FR-001)

**Given** a valid 6-digit stock code with `mode=deep`  
**When** `POST /api/ai-report/005930?mode=deep` is received  
**Then** the router executes the guard chain (code format → stock existence → API key → claude binary → duplicate → rate limit) and delegates to `stream_deep_analysis()`

**Given** an invalid mode value `mode=invalid`  
**When** the request is processed  
**Then** the backend returns HTTP 422 with `invalid_mode` error

---

## AC-003: 5-소스 병렬 수집 성공 (FR-002)

**Given** all 5 API keys are configured and all APIs respond within timeout  
**When** `collect_all_sources("005930", "삼성전자")` is called  
**Then** all 5 source files are present in the staging directory, and `summary.md` shows 5/5 success

**Given** 2 of 5 sources succeed (minimum gate)  
**When** collection completes  
**Then** the pipeline proceeds to staging with available sources, and `summary.md` records partial success

---

## AC-004: 최소 소스 수 미달 (FR-002, ER-002)

**Given** only 1 of 5 sources succeeds  
**When** collection completes  
**Then** an SSE `event: error` is emitted with message containing "수집 실패: 1/5", and no Claude CLI subprocess is spawned

**Given** all 5 sources fail (e.g., all API keys missing)  
**When** collection completes  
**Then** HTTP 502 response with SSE `event: error` is returned

---

## AC-005: 스테이징 디렉토리 구조 (FR-003)

**Given** collection succeeds with 4 of 5 sources (YouTube fails)  
**When** `create_staging_directory()` completes  
**Then**:
- `/tmp/analysis_005930_<ISO8601>_<uuid8>/summary.md` exists and contains "YouTube ❌ 실패"
- `/tmp/analysis_005930_<ISO8601>_<uuid8>/sources/perplexity.md` exists with no `<think>` blocks
- `/tmp/analysis_005930_<ISO8601>_<uuid8>/sources/youtube.json` does NOT exist
- Each UUID8 is unique across concurrent requests

---

## AC-006: Claude CLI 호출 보안 제약 (FR-004)

**Given** staging directory is ready  
**When** the CLI is invoked  
**Then** the subprocess command includes `--allowedTools "Read,Grep,Glob"` and `--cwd /tmp/analysis_<uuid>`

**Given** `AI_REPORT_DEEP_MODEL=opus` environment variable is set  
**When** the CLI is invoked  
**Then** `--model claude-opus-4-6` is appended to the command

**Given** `AI_REPORT_DEEP_MODEL` is not set  
**When** the CLI is invoked  
**Then** no `--model` flag is added (default Sonnet behavior)

---

## AC-007: stream-json 파싱 및 SSE 전달 (FR-005)

**Given** Claude CLI outputs `{"type":"assistant","message":{"content":[{"type":"text","text":"# 삼성전자"}]}}`  
**When** the line is parsed  
**Then** SSE `data: # 삼성전자` is emitted to the client

**Given** Claude CLI outputs `{"type":"result","subtype":"success"}`  
**When** parsed  
**Then** SSE `event: done\ndata: \n\n` is emitted and subprocess cleanup begins

**Given** Claude CLI outputs `{"type":"unknown_future_type","data":{}}`  
**When** parsed  
**Then** the line is silently ignored and streaming continues

**Given** Claude CLI outputs malformed JSON `{not valid`  
**When** parsing is attempted  
**Then** `json.JSONDecodeError` is caught, line is logged at WARNING level, streaming continues

---

## AC-008: 리포트 자동 저장 (FR-006)

**Given** Deep synthesis stream completes successfully  
**When** the `done` event is emitted  
**Then** `backend/reports/<stock_name>/<date>.md` exists with the complete synthesized markdown content

**Given** the same stock has an existing report for today  
**When** a new Deep analysis completes  
**Then** the file is saved with sequence number (e.g., `2026-04-16_2.md`) using existing `save_report()` logic

---

## AC-009: 타임아웃 처리 (FR-007)

**Given** the Claude CLI process runs longer than 180 seconds  
**When** `asyncio.wait_for` timeout fires  
**Then**:
- `proc.terminate()` is called
- After 15-second grace period, `proc.kill()` is called if still running
- SSE `event: error` with timeout message is emitted
- Staging directory is cleaned up in `finally` block

---

## AC-010: 클라이언트 연결 끊김 (FR-007, ER-005)

**Given** a Deep analysis is streaming to the client  
**When** the client disconnects (browser tab closed, EventSource abort)  
**Then**:
- `CancelledError` is caught in the SSE generator
- Claude CLI subprocess is terminated
- Staging directory is deleted
- No zombie process remains after 20 seconds

---

## AC-011: Deep 전용 Rate Limit (FR-008)

**Given** `AI_REPORT_DEEP_DAILY_QUOTA=15` is configured  
**When** the 16th Deep analysis request arrives on the same calendar day  
**Then** HTTP 429 is returned with message containing "일일 쿼터 초과"

**Given** `AI_REPORT_DEEP_BURST_LIMIT=1` is configured  
**When** a second Deep analysis request arrives within 60 seconds of the first  
**Then** HTTP 429 is returned with burst limit message

**Given** a Deep mode request exceeds its rate limit  
**When** processed  
**Then** the Perplexity mode quota (`AI_REPORT_DAILY_QUOTA`) is NOT decremented

---

## AC-012: Claude CLI 부재 처리 (FR-009, ER-003)

**Given** `shutil.which("claude")` returns None (Claude CLI not installed)  
**When** `POST /api/ai-report/{code}?mode=deep` is received  
**Then** HTTP 503 is returned with `{"error": "claude_cli_missing"}` and the Perplexity mode endpoint remains fully functional

**Given** the server starts with Claude CLI absent  
**When** lifespan startup completes  
**Then** a WARNING log line containing "claude CLI 미설치" is emitted and server starts successfully (no crash)

---

## AC-013: 합성 프롬프트 분리 (FR-010)

**Given** `backend/prompts/stock_synthesis_prompt.md` exists  
**When** the Deep pipeline initializes  
**Then** `stock_synthesis_prompt.md` is loaded as the `--append-system-prompt` content

**Given** `backend/prompts/perplexity_prompt.md` exists  
**When** any Deep analysis runs  
**Then** `perplexity_prompt.md` is NOT modified and remains byte-identical to its pre-SPEC-002 state

---

## AC-014: 프론트엔드 2단 토글 (FR-011)

**Given** the AI Report Modal is open  
**When** the user views the header area  
**Then** two mode buttons "빠른 분석" and "심층 분석 (~90초)" are visible

**Given** streaming is in progress  
**When** the user attempts to click the mode toggle  
**Then** both mode buttons are disabled (no mode switching during active stream)

**Given** the user selects "심층 분석"  
**When** the analysis button is clicked  
**Then** `POST /api/ai-report/{code}?mode=deep` is sent (not `mode=perplexity`)

**Given** the user selects "빠른 분석" (default)  
**When** the analysis button is clicked  
**Then** `POST /api/ai-report/{code}?mode=perplexity` or `POST /api/ai-report/{code}` is sent

---

## AC-015: SSE 이벤트 계약 호환성 (FR-012)

**Given** the frontend EventSource handler for Perplexity mode  
**When** it receives a Deep mode stream  
**Then** markdown chunks, `done` event, and `error` event are processed identically without frontend code changes

**Given** the frontend receives an `event: phase` event  
**When** processed  
**Then** the unknown event type is silently ignored (no console error, no UI disruption)

---

## AC-016: /tmp 정리 (FR-013)

**Given** `/tmp/analysis_005930_2026-04-09_abc12345/` exists and is 8 days old  
**When** the server starts up (lifespan)  
**Then** the directory is deleted by `_cleanup_stale_staging_dirs()`

**Given** `/tmp/analysis_005930_2026-04-16_xyz67890/` exists and is 1 hour old  
**When** the server starts up  
**Then** the directory is preserved (not deleted)

---

## AC-017: 기존 SPEC-001 회귀 없음

**Given** SPEC-AI-REPORT-001 v1.1.6 test suite (30 tests in `test_ai_report_service.py`)  
**When** run after SPEC-002 implementation  
**Then** all 30 tests pass without modification

**Given** `POST /api/ai-report/005930` (no mode parameter)  
**When** processed after SPEC-002 implementation  
**Then** behavior is identical to pre-SPEC-002 (Perplexity pipeline, same SSE events, same rate limits)

---

## AC-018: @MX 태그 배치

**Given** SPEC-002 implementation is complete  
**When** reviewing new source files  
**Then**:
- `deep_research_service.py::stream_deep_analysis()` has `@MX:ANCHOR` with fan_in >= 2 justification
- `deep_research_service.py::check_deep_rate_limit()` has `@MX:ANCHOR`
- `claude_cli_streamer.py::stream_claude_synthesis()` has `@MX:ANCHOR`
- `_active_deep_analyses` global set has `@MX:WARN` with multiworker incompatibility reason
- `asyncio.create_subprocess_exec` call site has `@MX:WARN` with zombie process reason
