# SPEC-AI-REPORT-002 구현 계획

## 전략 개요

기존 SPEC-001 자산을 최대한 보존하면서 5단계 점진적 구현. 각 단계는 독립적으로 검증 가능하며, 이전 단계 실패 시 롤백해도 기존 Perplexity 모드에 영향 없음.

개발 방식: TDD (RED-GREEN-REFACTOR) 대상 커버리지: 85% 이상 (신규 파일 기준)

---

## 소스 활용 전략 (기존 자산 재사용 경계)

Run 단계에서 **백엔드 Python 코드가 런타임에 각 API를 직접 호출**한다. Claude Code(AI 에이전트)가 검색을 수행하지 않는다. `docs/deep-research/` 하위 기존 자산은 아래 3가지 방식으로 재사용한다.

### S1. `docs/deep-research/skill.md` — 레퍼런스 only (실행 X)

- 용도: 각 API의 **curl 명령 · URL · 헤더 · 파라미터 스키마**를 검증된 API 계약서로 참조
- 포팅 대상:

  | skill.md 항목 | 포팅 결과 |
  | --- | --- |
  | `curl "https://api.search.brave.com/res/v1/web/search?q=${Q}&count=20" -H "X-Subscription-Token: $BRAVE_API_KEY"` | `deep_research_collector.py::_collect_brave` — `httpx.AsyncClient().get()` |
  | `curl -X POST "https://api.tavily.com/search" -d '{"query":"...","search_depth":"advanced","max_results":20,"include_answer":"advanced"}'` | `_collect_tavily` — `httpx.AsyncClient().post()` |
  | `curl -X POST "https://api.perplexity.ai/chat/completions" -d '{"model":"sonar-reasoning-pro",...}'` | `_collect_perplexity` — 비스트리밍 POST + `<think>` 블록 제거 |
  | `curl "https://openapi.naver.com/v1/search/webkr.json?query=${KQ}&display=10" -H "X-Naver-Client-Id:..."` | `_collect_naver` — `httpx.AsyncClient().get()` |
  | `curl "https://www.googleapis.com/youtube/v3/search?part=snippet&q=${Q}&type=video&maxResults=10&key=..."` | `_collect_youtube` — `httpx.AsyncClient().get()` |
- skill.md 자체는 실행하지 않으며, `.claude/skills/`에 등록하지도 않는다 (Exclusions 준수).

### S2. `docs/deep-research/scripts/merge_results.py` — 파서 5개 어댑트

- 용도: 각 소스 JSON 응답을 정규화하는 **파서 함수 재활용**
- 어댑트 대상 (함수 단위 복사 + 비동기 context에 맞춤):

  | 원본 함수 (merge_results.py) | 어댑트 결과 (deep_research_collector.py) | 변경 |
  | --- | --- | --- |
  | `parse_brave(data)` | `_normalize_brave(data)` | 동일 로직, 시그니처 유지 |
  | `parse_tavily(data)` | `_normalize_tavily(data)` | 동일 |
  | `parse_perplexity(data)` | `_normalize_perplexity(data)` | `<think>` 블록 제거 로직 추가 |
  | `parse_naver(data)` | `_normalize_naver(data)` | HTML 태그 제거 로직 유지 |
  | `parse_youtube(data)` | `_normalize_youtube(data)` | `videoId` → URL 변환 로직 유지 |
  | `deduplicate_results(results)` | `_deduplicate_by_url(results)` | 동일 |
- Attribution 규칙: 파서 함수 상단에 `# Adapted from docs/deep-research/scripts/merge_results.py::parse_<source>` 주석 필수
- merge_results.py의 CLI 진입점(`main()`, argparse)·파일 입출력(`load_json_safe()`)·보고서 포맷(`format_report()`)은 **사용하지 않는다** (우리는 파일이 아닌 메모리 객체를 다룸)

### S3. 신규 작성 영역 (기존 자산에 없는 부분)

- `httpx.AsyncClient` 인스턴스 생성·수명 관리 (context manager)
- `asyncio.gather(*tasks, return_exceptions=True)` 5-parallel 래퍼
- 각 소스 개별 타임아웃 (`asyncio.wait_for(task, timeout=10)`)
- `CollectionResult` dataclass와 게이트 판정 (`gate_passed: bool`)
- `/tmp/analysis_<uuid>/` 스테이징 디렉토리 생성
- `summary.md` 마크다운 생성 (한국어 스윙트레이딩 도메인 용어 + 소스 상태 테이블 + 합성 지시)
- `sources/*.json` 쓰기 + `sources/perplexity.md` 저장 (think 블록 제거 후)
- 소스별 실패 분류 (timeout / HTTP error / parse error / quota exceeded)

### 경계 요약

| 영역 | 출처 | 라이선스 / 출처 주석 |
| --- | --- | --- |
| HTTP 호출 로직 | **신규** | 내부 코드 |
| JSON 파서 | docs/deep-research/scripts/merge_results.py 어댑트 | 함수 상단에 Attribution 주석 |
| curl 명령 구조 | docs/deep-research/skill.md 레퍼런스 | 주석에 `# skill.md §2 참조` |
| 비동기 래퍼·스테이징·summary.md | **신규** | 내부 코드 |
| 로컬 사용자 스킬 재사용 | S1/S2만, 실행·등록 X | Exclusions 준수 |

이 경계는 Phase B의 작업 분해(B1-B3)에 이미 반영되어 있으며, 본 섹션은 암묵적 전략을 명시화한 것이다.

---

## Phase A — Claude CLI PoC

**목표**: `asyncio.create_subprocess_exec`로 `claude -p` 스트리밍 파싱 검증

### 작업 목록

**A1. stream-json 파서 핵심 로직 구현**

RED: `test_claude_cli_streamer.py` 작성

- `test_parse_assistant_event()` — `type=assistant` delta 텍스트 추출
- `test_parse_result_event()` — `type=result` → done 신호
- `test_parse_error_event()` — `type=system, subtype=error` → error 신호
- `test_ignore_unknown_type()` — 알 수 없는 type 무시
- `test_malformed_json_skipped()` — JSONDecodeError 복구

GREEN: `backend/services/claude_cli_streamer.py` 최소 구현

- `parse_stream_json_line(line: str) -> StreamEvent | None`
- `StreamEvent = TextDelta | DoneSignal | ErrorSignal`

REFACTOR: 타입 안전성, 방어적 파싱 검증

**A2. subprocess 실행 + stdout 파이프 검증**

RED:

- `test_subprocess_timeout()` — 180초 초과 시 terminate
- `test_subprocess_zombie_cleanup()` — CancelledError 시 kill

GREEN:

- `stream_claude_synthesis(cwd, prompt, system_prompt, model) -> AsyncGenerator[StreamEvent]`
- `asyncio.wait_for(timeout=180)` + `finally: proc.terminate() → proc.kill()`

**A3. @MX:ANCHOR 태그 추가**

- `stream_claude_synthesis()` — subprocess 좀비 방지 finally 블록 invariant
- `parse_stream_json_line()` — 파서 계약 명시

---

## Phase B — 수집기 구현

**목표**: 5개 API httpx 병렬 수집 + `/tmp` 스테이징

### 작업 목록

**B1. 소스별 수집 함수 구현** (`backend/services/deep_research_collector.py`)

RED: `test_deep_research_collector.py`

- `test_collect_perplexity_nonstreaming()` — stream=False, think 블록 제거
- `test_collect_brave()` — 20결과, 영문+한국어 쿼리
- `test_collect_tavily()` — advanced depth, include_answer
- `test_collect_naver()` — 웹/뉴스 10건
- `test_collect_youtube()` — 비디오 메타데이터 10건
- `test_source_timeout_counted_as_failure()` — httpx.TimeoutException → 실패
- `test_minimum_2_sources_gate()` — 1개 성공 시 ValueError

GREEN:

- `collect_all_sources(code, stock_name) -> CollectionResult`
- `asyncio.gather(*tasks, return_exceptions=True)` 패턴
- 각 소스 개별 10초 타임아웃

**B2. 스테이징 디렉토리 생성**

RED:

- `test_create_staging_dir()` — UUID8 포함 경로
- `test_write_summary_md()` — 소스 성공/실패 현황 테이블
- `test_write_perplexity_md_think_stripped()` — `<think>` 블록 제거
- `test_staging_path_under_tmp()` — /tmp 외 경로 방지

GREEN:

- `create_staging_directory(code, result: CollectionResult) -> Path`
- `summary.md` 생성 (주어진 스키마 준수)
- `sources/*.json` / `sources/perplexity.md` 쓰기

**B3. @MX 태그 추가**

- `collect_all_sources()` — @MX:ANCHOR (라우터 + 테스트 fan_in)
- `_active_deep_analyses` 전역 set — @MX:WARN (멀티워커 비호환)

---

## Phase C — 합성 경로 통합

**목표**: Collector + CLI Streamer 오케스트레이션, SSE 어댑터

### 작업 목록

**C1. 합성 전용 프롬프트 작성** (`backend/prompts/stock_synthesis_prompt.md`)

- 기존 `SYSTEM_PROMPT` 작성 원칙 포팅
- "파일로 주어진 원본 데이터를 교차 검증" 전제 명시
- 출처 인용 규칙: `[brave]`, `[tavily]`, `[naver]`, `[youtube]`
- 6컬럼 표 규칙 유지
- "마크다운 본문만 출력, 선행 인사 금지" 명시

**C2. 오케스트레이터 구현** (`backend/services/deep_research_service.py`)

RED: `test_deep_research_service.py`

- `test_orchestrate_success_path()` — 5/5 성공 시 SSE done까지 완료
- `test_orchestrate_partial_sources()` — 3/5 성공 시 계속 진행
- `test_orchestrate_below_minimum()` — 1/5 성공 시 SSE error
- `test_orchestrate_cli_timeout()` — 180초 초과 시 SSE error
- `test_orchestrate_client_disconnect()` — CancelledError 시 cleanup
- `test_report_saved_on_success()` — 완료 후 save_report 호출

GREEN:

- `stream_deep_analysis(code, stock_name, model) -> AsyncGenerator[dict, None]`
  - Phase 1: `collect_all_sources()`
  - Phase 2: `create_staging_directory()`
  - Phase 3-4: `stream_claude_synthesis()` → SSE 이벤트 변환
  - Phase 5: `save_report()` + `/tmp` 정리
- `finally` 블록: proc 종료 + staging dir 삭제 보장

**C3. @MX:ANCHOR 태그 추가**

- `stream_deep_analysis()` — 전체 파이프라인 진입점, fan_in &gt;= 2

---

## Phase D — 라우터/UX 통합

**목표**: 기존 라우터에 `?mode=deep` 분기 추가 + 프론트엔드 2단 토글

### 작업 목록

**D1. 라우터 분기** (`backend/routers/ai_report.py`)

기존 `generate_report(code: str)` 시그니처 변경:

```python
@router.post("/ai-report/{code}")
async def generate_report(
    code: str,
    mode: str = Query("perplexity", pattern="^(perplexity|deep)$"),
) -> EventSourceResponse:
```

가드 체인 유지 후 분기:

```python
if mode == "deep":
    # claude CLI 체크 → deep rate limit → _active_deep_analyses → stream_deep_analysis
else:
    # 기존 Perplexity 경로 (변경 없음)
```

**D2. Deep rate limit 추가** (`backend/services/deep_research_service.py`)

- `_deep_daily_call_count`, `_deep_recent_timestamps` 전역 상태
- `check_deep_rate_limit()` 함수 (기존 `check_rate_limit()` 패턴 복사)
- 환경변수: `AI_REPORT_DEEP_DAILY_QUOTA=15`, `AI_REPORT_DEEP_BURST_LIMIT=1`

**D3. main.py lifespan 업데이트** (`backend/main.py`)

```python
# shutil.which("claude") 체크 (warning only)
import shutil
if not shutil.which("claude"):
    logger.warning("claude CLI 미설치: Deep 분석 모드 비활성화. Perplexity 모드는 정상 운영.")

# stock_synthesis_prompt.md fail-fast (기존 패턴 동일)
try:
    from backend.services.deep_research_service import _load_synthesis_prompt
    _load_synthesis_prompt()
    logger.info("Deep Research 합성 프롬프트 로드 완료")
except (FileNotFoundError, ValueError) as e:
    logger.error("합성 프롬프트 검증 실패: %s", e)
    raise

# /tmp 7일 초과 analysis_* 디렉토리 정리
_cleanup_stale_staging_dirs()
```

**D4. 프론트엔드 토글** (`frontend/src/components/AiReportModal.tsx`)

헤더 영역(`:122-130`)에 모드 선택 세그먼트 추가:

```tsx
<div className="ai-report-mode-selector">
  <button
    className={`ai-report-mode-btn${mode === 'perplexity' ? ' active' : ''}`}
    onClick={() => setMode('perplexity')}
    disabled={status === 'streaming'}
  >
    빠른 분석
  </button>
  <button
    className={`ai-report-mode-btn${mode === 'deep' ? ' active' : ''}`}
    onClick={() => setMode('deep')}
    disabled={status === 'streaming'}
  >
    심층 분석 (~90초)
  </button>
</div>
```

**D5. useAiReport 시그니처 확장** (`frontend/src/hooks/useAiReport.ts:41`)

- `startStream(code: string, mode: 'perplexity' | 'deep' = 'perplexity')`
- `mode` state 추가

**D6. API 클라이언트 URL 업데이트** (`frontend/src/api/aiReport.ts:39`)

- `/api/ai-report/${code}` → `/api/ai-report/${code}?mode=${mode}`

---

## Phase E — 운영화

**목표**: 관찰성, 빌드 문서, 클린업 로직

### 작업 목록

**E1. Phase별 로깅 강화**

- 수집 단계: 소스별 소요시간 + 성공/실패 상태
- 합성 단계: Claude CLI exit code + 토큰 수 (stream-json `result` 이벤트)
- 전체: end-to-end 소요시간

**E2. /tmp 정리 함수**

- `_cleanup_stale_staging_dirs(max_age_days=7)` 구현
- glob `/tmp/analysis_*` → mtime 7일 초과 → `shutil.rmtree`
- lifespan에서 startup 시 1회 실행

**E3. 빌드/배포 문서**

- README에 Claude CLI 의존성 명시
- 환경변수 목록 업데이트 (`AI_REPORT_DEEP_*`, 검색 API 키 5종)
- "Claude CLI 미설치 시 Deep 모드 비활성화" 동작 명시

---

## 파일 의존성 그래프

```
deep_research_service.py (오케스트레이터)
  ├── deep_research_collector.py (소스 수집 + 스테이징)
  │     └── ai_report_service.py (Perplexity 비스트리밍 래퍼, save_report)
  └── claude_cli_streamer.py (CLI 호출 + stream-json 파서)

backend/routers/ai_report.py
  ├── ai_report_service (기존, Perplexity 경로)
  └── deep_research_service (신규, Deep 경로)

backend/main.py
  ├── ai_report_service._load_prompt_template (기존)
  └── deep_research_service._load_synthesis_prompt (신규)
```

---

## 위험 완화 전략

| 위험 | 완화 |
| --- | --- |
| Claude CLI 없는 환경 | shutil.which + 503 게이팅, Perplexity 모드 무영향 |
| stream-json 포맷 변동 | 방어적 파싱(unknown type 무시), 버전 핀닝 |
| /tmp 디스크 포화 | 7일 초과 자동 정리 + 성공/실패 후 즉시 정리 |
| subprocess 좀비 | finally + terminate/kill 이중 보장 |
| 기존 SPEC-001 회귀 | 기존 파일 무변경 원칙 + 30개 기존 테스트 통과 유지 |
| pytest testpaths 불일치 | `pyproject.toml` testpaths를 `["backend/tests", "tests"]`로 수정 |

---

## 구현 완료 기준

- [ ] 신규 파일 3개 (`deep_research_collector.py`, `claude_cli_streamer.py`, `deep_research_service.py`) 구현 완료

- [ ] `backend/prompts/stock_synthesis_prompt.md` 작성 완료

- [ ] `test_deep_research_service.py` — 신규 테스트 85% 커버리지 달성

- [ ] 기존 30개 테스트 (`test_ai_report_service.py`) 모두 통과

- [ ] `backend/routers/ai_report.py` `mode` 파라미터 분기 동작

- [ ] 프론트엔드 2단 토글 렌더링 + 모드별 요청 전송

- [ ] lifespan에 `shutil.which("claude")` 체크 + synthesis 프롬프트 검증 추가

- [ ] `/tmp` 7일 초과 정리 함수 동작

- [ ] `@MX:ANCHOR` 3개, `@MX:WARN` 3개 태그 추가