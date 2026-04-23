---
id: SPEC-AI-REPORT-003
version: 1.0.0
status: Planned
created: 2026-04-23
updated: 2026-04-23
author: MoAI (orchestrator)
priority: High
issue_number: null
lifecycle: spec-first
---

# SPEC-AI-REPORT-003: Perplexity → Codex CLI 전면 전환

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| 1.0.0 | 2026-04-23 | 초기 SPEC — Fast+Deep 양쪽 Perplexity API 완전 제거, Codex CLI 전면 대체 |

---

## 개요

SPEC-AI-REPORT-001(Fast 모드, Perplexity 스트리밍) 및 SPEC-AI-REPORT-002(Deep 모드, 5-소스 병렬 + Perplexity 포함) 의 핵심 소스인 **Perplexity API 를 완전 제거** 하고, ChatGPT 정기구독 기반으로 무료 호출 가능한 **Codex CLI** 로 전면 대체한다.

사전 3-way 품질 비교(`codex-transform-plan/comparison-samsungsdi-2026-04-23.md`) 결과 Codex 가 팩트 포착률 83% 로 Perplexity Deep(8%) / Enhanced(58%) 대비 우세했다. 사용자의 최우선 기준은 품질이며 비용은 무관(Codex 는 구독 내 무료).

**핵심 설계 결정 (사용자 확정)**:
1. 대체 범위: Fast Mode + Deep Mode 양쪽 (Perplexity 관련 자산 완전 제거)
2. Fallback: 없음 + 1회 재시도만
3. Fast Mode UX: Codex non-streaming 한계를 heartbeat SSE 메시지로 보완
4. SPEC 번호: SPEC-AI-REPORT-003 신규 (001/002 별개)
5. Codex CLI 인증: ChatGPT 로그인 (API 키 불필요)

---

## Functional Requirements (EARS)

### FR-001: Fast Mode Codex 전환 (Event-Driven)

**When** the user sends `POST /api/ai-report/{code}?mode=fast` (or default without `mode`), the backend **shall** invoke Codex CLI via subprocess (`codex exec`) instead of the Perplexity API, while preserving the SSE response contract.

**When** `mode` is omitted, the backend **shall** route to the Codex-based Fast Mode pipeline (backward compatible URL, new implementation).

### FR-002: Deep Mode Codex 슬롯 교체 (Event-Driven)

**When** the Deep pipeline runs `collect_all_sources`, the backend **shall** invoke `_collect_codex` in place of `_collect_perplexity` as one of the 5 parallel sources.

**When** Codex succeeds, the source result **shall** include the markdown file path written by Codex (`--output-last-message`), consistent with the existing `SourceResult` dataclass.

### FR-003: 1회 재시도 Fallback (Unwanted Behavior)

**When** a Codex CLI invocation fails with a transient error (`timeout`, `http_error`, non-zero exit except `binary_missing`), the backend **shall** retry exactly once with identical input and a fresh subprocess before marking the source as failed.

**When** the first attempt fails with `error_type="binary_missing"`, the backend **shall not** retry (deterministic failure).

### FR-004: Fast Mode Heartbeat UX (State-Driven)

**While** a Fast Mode Codex subprocess is running, the backend **shall** emit SSE phase events every 30 seconds with rotating status messages (예: "웹 검색 진행 중", "자료 교차 검증 중", "리포트 작성 중") to maintain user engagement.

**When** the Codex subprocess completes successfully in Fast Mode, the backend **shall** split the resulting markdown into chunks (recommended 256-character boundaries) and emit each chunk as an SSE `data` event.

### FR-005: Perplexity 자산 완전 제거 (Functional)

The system **shall** remove all Perplexity-related assets, including but not limited to:
- `backend/services/perplexity_cache.py` (전체 삭제)
- `ai_report_service.py::stream_perplexity()` 함수 (삭제)
- `ai_report_service.py::SYSTEM_PROMPT, SEARCH_DOMAIN_FILTER, load_prompt, _load_prompt_template, _PROMPT_TEMPLATE_PATH` (삭제 또는 Codex 전용 재설계)
- `backend/prompts/perplexity_prompt.md` (삭제 또는 `codex_prompt.md` 로 재활용)
- `deep_research_collector.py::_collect_perplexity()` 함수 (삭제)
- `deep_research_collector.py::_normalize_perplexity()` 함수 (삭제)
- `.env` / `.env.example` 의 `PERPLEXITY_API_KEY` (제거)
- 관련 테스트 (`test_collect_perplexity_*`, `test_normalize_perplexity_*`, `TestLoadPrompt` 등) — Codex 테스트로 대체

### FR-006: 스테이징 디렉토리 2단계 생성 (Event-Driven)

**When** Deep Mode 가 시작되면, `prepare_staging_directory()` 가 source 수집 **전** 에 실행되어 `/tmp/analysis_<code>_<uuid>/sources/` 디렉터리를 사전 생성해야 한다. Codex CLI 의 `--output-last-message` 가 이 경로에 직접 파일을 쓰기 때문이다.

**When** 수집이 완료되면 `finalize_staging_directory()` 가 실행되어 `summary.md` + 성공한 나머지 소스 파일 (`brave.json` 등) 을 기록한다.

### FR-007: 합성 프롬프트 파일 갱신 (Functional)

The `backend/prompts/stock_synthesis_prompt.md` **shall** reference `sources/codex.md` instead of `sources/perplexity.md`.

### FR-008: SSE phase 이벤트 이름 변경 (Event-Driven)

**When** Deep Mode 진행 중 source별 phase 이벤트를 emit 할 때, 이름 `"perplexity"` **shall** be replaced with `"codex"`.

**When** Fast Mode heartbeat 이 emit 될 때, phase 이름은 `"codex_fast_progress"` (또는 합의된 명칭) 이어야 한다.

### FR-009: 프론트엔드 SourceName 갱신 (Functional)

`frontend/src/types/aiReport.ts` 의 `SourceName` 유니언 타입에서 `"perplexity"` **shall** be replaced with `"codex"`. 관련 라벨 (ProgressPanel 등) 은 "Codex 심층 리서치" 로 변경.

---

## Non-Functional Requirements

### NFR-001: 타임아웃 (Performance)

- Codex 단일 호출 타임아웃: **600초** (관측된 2~9분 변동 커버)
- 1회 재시도 포함 최대 소요: 1200초
- `_DEFAULT_TIMEOUTS["codex"] = 600.0`

### NFR-002: 쿼터 보호 (Resource)

- Codex 는 ChatGPT 구독 무료 호출이나 **일일 사용 한도 내** 에서만 동작
- 기존 `AI_REPORT_DAILY_QUOTA=50` 환경변수는 "과금 방지" 가 아니라 "구독 쿼터 보호" 목적으로 재정의 (값 유지)
- `AI_REPORT_DEEP_DAILY_QUOTA=15`, `AI_REPORT_DEEP_BURST_LIMIT=1` 도 Codex 기준으로 재정의 (값 유지)

### NFR-003: 경로 안전 (Security)

- Codex `--output-last-message` 경로는 반드시 `/tmp/analysis_<code>_<uuid>/sources/` 내부여야 함
- `prepare_staging_directory()` 에서 `_BLOCKED_ROOTS` 검사 선수행
- Codex subprocess 는 `--sandbox read-only` 로 실행해 로컬 파일시스템 수정 방지 (output-last-message 경로는 예외 허용됨)

### NFR-004: 완전 제거 검증 (Maintainability)

- 구현 완료 후 `grep -r "perplexity" backend/` 결과는 빈 상태여야 함 (대소문자 무관)
- `.env.example` 에 `PERPLEXITY_API_KEY` 존재하지 않아야 함
- `import` 구문에 `perplexity` 키워드 없어야 함

### NFR-005: 인터페이스 보존 (Compatibility)

- `SourceResult` dataclass 시그니처 유지 (name 값만 `"perplexity"` → `"codex"` 로)
- `collect_all_sources` 함수 시그니처 유지
- SSE 응답 구조 (event type, data format) 기존과 호환
- 라우터 엔드포인트 URL (`/api/ai-report/{code}?mode=...`) 변경 없음

### NFR-006: 재현성 모니터링 (Quality)

- Codex 는 gpt-5.4 샘플링 기반이라 `temperature=0.2` 를 강제한 Perplexity 대비 결과 재현성이 낮을 수 있음
- 같은 종목 연속 호출 시 가격·이벤트 일관성을 운영 중 모니터링
- 샘플링 분산이 과도할 경우 `codex exec -c model_reasoning_effort=...` 또는 프롬프트 추가 제약 고려

---

## Error Handling

### ER-001: Codex 바이너리 미설치

**When** the `codex` binary is not in `PATH`, the backend **shall** return `SourceResult(success=False, error_type="binary_missing")` without retry. 프론트엔드에는 "Codex CLI 가 설치되어 있지 않습니다" 메시지 표시.

### ER-002: Codex 인증 실패

**When** Codex stderr 에 `"not logged in"` 또는 유사한 인증 오류가 포함된 경우, `error_type="auth"` 로 분류. 재시도 수행하지 않음.

### ER-003: Codex 타임아웃

**When** 600초 초과 시 `asyncio.timeout` 발생 → terminate → kill 2단계 subprocess 정리 후 `error_type="timeout"` 반환. 1회 재시도 수행.

### ER-004: 빈 출력

**When** Codex 가 exit code 0 으로 종료되었으나 `--output-last-message` 파일이 비어있거나 생성되지 않은 경우, `error_type="empty_output"` 반환. 1회 재시도 수행.

---

## 종속성 및 전제조건

- **Codex CLI**: `codex-cli 0.121.0` 이상, `PATH` 에 위치
- **Codex 인증**: `codex login` 을 통한 ChatGPT 계정 로그인 완료 (API 키 불필요)
- **Python**: 3.13+, `asyncio.subprocess` 지원
- **기존 인프라 재사용**: `claude_cli_streamer.py` 의 subprocess 관리 패턴 (terminate → kill 2단계)

---

## 범위 외 (Out of Scope)

- Codex 결과 캐싱 (선택 구현, v1.1.x 에서 고려 가능)
- Fast Mode 실시간 토큰 스트리밍 (Codex 지원 안 함, heartbeat 로 대체)
- Perplexity API 키 재사용 (완전 제거)
- SPEC-AI-REPORT-001/002 의 Perplexity 관련 테스트 유지 (Codex 테스트로 교체)

---

## 참고 문서

- Plan 상세: `codex-transform-plan/plan-v3-complete-codex-replacement.md`
- Codex CLI 호출 스펙: `codex-transform-plan/codex-cli-reference.md`
- 품질 비교 실측: `codex-transform-plan/comparison-samsungsdi-2026-04-23.md`
- Perplexity 활용 분석: `codex-transform-plan/perplexity-usage-analysis.md`
