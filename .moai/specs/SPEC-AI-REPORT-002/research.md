# Research: SPEC-AI-REPORT-002 — AI 리포트 Deep-Research 합성 모드

문서 유형: Plan 단계 리서치 아티팩트
생성일: 2026-04-16
작성 주체: Agent Teams (researcher / analyst / architect — moai-plan-ai-report-002)
원본 설계: `docs/ai-report-deep-research-design.md` (422라인, Draft)
기존 SPEC 연번: SPEC-AI-REPORT-001 (v1.1.6, Perplexity 단일 소스)

---

## 0. 사용자 확정 결정 4건

| # | 결정 | 값 |
|---|------|----|
| 1 | SPEC ID | `SPEC-AI-REPORT-002` (기존 001과 별도 연번) |
| 2 | 합성 모델 기본값 | Sonnet (env `AI_REPORT_DEEP_MODEL=sonnet` 기본) + 요청 시 `?model=opus` 승격 |
| 3 | 프론트 UX | 명시적 2단 토글 "빠른 분석(Perplexity)" / "심층 분석(Deep, ~90s)", 자동 폴백 배제 |
| 4 | 하네스 범위 | `/tmp` 격리 only, `.claude/agents`·`.claude/skills` 영구 등록 없음 |

---

## 1. 설계 문서 요약 (researcher)

- **하이브리드 파이프라인**: Python은 5개 소스(Perplexity / Brave / Tavily / Naver / YouTube) 병렬 수집 + `/tmp/<uuid>` 스테이징만 담당하고, 합성은 `claude -p` 헤드리스 CLI 1회 fork-exec로 위임
- **모드 분기**: `POST /api/ai-report/{code}?mode=deep` 쿼리 파라미터로 기존 Perplexity 경로와 Deep 경로를 분리. SSE 이벤트 계약(청크 / done / error)은 프론트 변경 없이 동일 유지
- **보안 3중 방어**: `--cwd /tmp/<uuid>` 격리 + `--allowedTools "Read,Grep,Glob"` 화이트리스트 + 환경변수 기반 API 키 전달 (CLI 인자 금지)
- **비용 통제 분리**: 기존 Perplexity 쿼터(50/일, 3/분) 불변, Deep 전용 쿼터(15/일, 1/분) 별도 추가
- **점진 도입 5단계**: A(PoC) → B(수집기) → C(합성) → D(라우터/UX) → E(운영화). 각 단계 독립 검증 가능

---

## 2. 기존 자산 인벤토리 (researcher)

| 파일 | 역할 | SPEC-002 관련성 | 변경 영향 |
|------|------|----------------|----------|
| `backend/routers/ai_report.py` | POST 엔드포인트, 가드 체인 | `?mode=deep` 분기 진입점 | **수정** — `mode`/`model` 쿼리 파라미터 추가, Deep 분기 |
| `backend/services/ai_report_service.py` | Perplexity 스트리밍, rate limit, 파일 저장 | `check_rate_limit()`·`_sanitize_name()`·`save_report()` 재사용 | **부분 수정** — `check_deep_rate_limit()` 신규 추가, 기존 함수 보존 |
| `backend/prompts/perplexity_prompt.md` | Perplexity 1차 분석 프롬프트 | 보존 대상 | **무변경** (G4) |
| `backend/schemas/ai_report.py` | Pydantic 응답 모델 | 필요 시 Deep 응답 타입 확장 | 보존 또는 소폭 확장 |
| `backend/main.py:27-51` | lifespan fail-fast 프롬프트 검증 | 동일 패턴으로 `stock_synthesis_prompt.md` + `shutil.which("claude")` 검증 추가 | **수정** |
| `backend/tests/test_ai_report_service.py` | 30개 회귀 테스트 (sanitize/rate limit/prompt) | 신규 테스트 참조 기준 | **확장** — 신규 테스트 파일 추가 |
| `docs/deep-research/skill.md` | 5-parallel bash 수집 스킬 원본 | API 스키마·파라미터 참조 | 읽기 전용 |
| `docs/deep-research/scripts/merge_results.py` | 소스별 파싱·병합 로직 | `summary.md`/`sources/` 쓰기 참조 | 읽기 전용 |
| `frontend/src/components/AiReportModal.tsx` | 5-state UI 상태 머신 | 2단 토글 삽입 지점 | **수정** |
| `frontend/src/hooks/useAiReport.ts:34` | SSE 스트리밍 훅 | `startStream(code, mode)` 시그니처 확장 | **수정** |
| `frontend/src/api/aiReport.ts:29` | `createAiReportStream()` | URL에 `?mode=${mode}` 추가 | **수정** |

---

## 3. 재사용 가능 패턴 (researcher)

### 3.1 `stream_perplexity()` (ai_report_service.py:223)
Deep 모드는 Perplexity 1차 분석본을 **파일로 저장**해야 하므로, 기존 스트리밍 제너레이터를 그대로 재사용하는 것은 부적합. collector 내부에 비스트리밍 단순 POST 헬퍼를 신규 작성(기존 함수는 불변 유지).

### 3.2 `check_rate_limit()` 분리 (ai_report_service.py:45, `@MX:ANCHOR`)
전역 카운터 + 환경변수 기반 설계가 이미 확립. Deep 전용 `_deep_daily_call_count`·`_deep_recent_timestamps`와 `check_deep_rate_limit()` 함수를 같은 파일에 **병렬 추가**하면 기존 불변.

### 3.3 startup lifespan 검증 패턴 (main.py:40-49)
`_load_prompt_template()` fail-fast 검증과 동일 패턴으로, `stock_synthesis_prompt.md` 로드 + `shutil.which("claude")` 체크 추가. CLI 부재 시 `raise` 대신 `logger.warning`으로만 처리하여 Perplexity 모드는 정상 운영(설계 NFR-008 배포 이식성 게이팅).

---

## 4. 통합 지점 (researcher)

- **Router 분기점**: `backend/routers/ai_report.py:32` `generate_report(code)` 시그니처에 `mode: str = Query("perplexity")` 추가 후 `if mode == "deep":` 분기. 가드 체인 순서 유지 필수
- **Rate limit 모듈 확장**: `backend/services/ai_report_service.py:33-34` 전역 변수 블록에 Deep 전용 변수 3개 + 함수 1개 추가
- **Frontend 토글 지점**: `AiReportModal.tsx:122-130` 헤더 또는 `148-160` 탭 영역 위에 "빠른 분석 | 심층 분석(~90s)" 세그먼트 토글 추가

---

## 5. 기존 테스트 패턴 (researcher)

`backend/tests/test_ai_report_service.py`(284라인, 30개) 패턴:
- `importlib.util.spec_from_file_location`로 서비스 모듈 격리 로드
- `monkeypatch.setattr`로 `_REPORTS_BASE` → `tmp_path` 교체
- `my_chart.registry` 스텁을 `sys.modules` 주입
- pytest `tmp_path` fixture로 파일시스템 격리

신규 테스트(`test_deep_research_*.py`)에도 동일 fixture 적용. `httpx_mock` 또는 `unittest.mock.patch`로 5소스 실패 시나리오 처리. subprocess 관련은 mock으로 격리, E2E만 실제 `claude` 바이너리 사용.

---

## 6. 의존성 현황 (researcher)

| 항목 | 버전 | 상태 |
|------|------|------|
| Python | ≥ 3.13 | 기존 |
| httpx | ≥ 0.27 (dev: 0.28.1) | 기존 — `AsyncClient` 사용 가능 |
| sse-starlette | ≥ 2.0 | 기존 |
| fastapi | ≥ 0.115 | 기존 |
| pytest-asyncio | ≥ 0.23, `asyncio_mode="auto"` | 기존 |
| **claude CLI 바이너리** | 런타임 의존 (권장: v2.1.x 이상) | **신규** |
| **BRAVE_API_KEY / TAVILY_API_KEY / NAVER_CLIENT_ID/SECRET / YOUTUBE_API_KEY** | 환경변수 | **신규** |

신규 Python 패키지 추가 불필요.

---

## 7. EARS 요구사항 초안 (analyst)

### 기능 (FR)
1. Deep 모드 분기 엔드포인트 (Event-Driven) — `?mode=deep`
2. 모델 선택 파라미터 (Optional Feature) — env + query override
3. 2단 모드 토글 UI (Event-Driven)
4. 5-parallel 소스 수집 + `/tmp` 스테이징 (Event-Driven)
5. 최소 소스 게이트 `2/5` (Event-Driven)
6. Claude CLI 헤드리스 합성 + stream-json → SSE 릴레이 (Event-Driven)
7. 리포트 자동 저장 — SPEC-001 경로 규약 재사용 (Event-Driven)
8. (선택) `event: phase` 진행 신호 (Optional Feature)

### 비기능 (NFR)
1. 첫 델타 응답 시간 ≤ 3s (수집 완료 후)
2. 전체 파이프라인 상한 180s (subprocess timeout 일치)
3. 프로세스 격리 — 요청당 `/tmp/<uuid>`
4. Deep 전용 쿼터 (15/일, 1/분) — Perplexity 쿼터 불변
5. SSE 계약 안정성 — 프론트 무수정 이중 모드 지원
6. 프롬프트 자산 무결성 — `perplexity_prompt.md`·`SYSTEM_PROMPT` 불변
7. 관찰성 로깅 — 소스별 latency, Claude 토큰 수, 전체 duration
8. 배포 이식성 게이팅 — CLI 부재 시 Deep 비활성화, Perplexity 정상

### 보안 (SR)
1. Claude CLI 도구 화이트리스트 `Read,Grep,Glob`
2. `/tmp` 디렉토리 격리 (cwd로 프로젝트 CLAUDE.md 자동 로드 차단)
3. 환경변수 키 전달 (CLI 인자 금지)

### 에러 처리 (ER)
1. Claude CLI 바이너리 부재 → 503
2. 환경변수 누락 → 503 (어떤 키가 없는지 명시)
3. 전체 소스 <2개 성공 → 502 + `event: error`
4. subprocess 타임아웃 → terminate(15s) → kill + error
5. 클라이언트 연결 끊김 → terminate + /tmp 정리
6. stream-json 파싱 오류 → 해당 라인 무시, 스트림 계속
7. Deep 쿼터 초과 → 429 (Perplexity 카운터 불변)
8. `/tmp` 7일 TTL 청소

### 수락 기준 (AC) 요약
- AC-001 정상 완료 (5/5 성공, 첫 델타 ≤3s, done 이벤트, 파일 저장)
- AC-002 부분 실패 복원력 (3/5 성공, summary.md에 명시, 정상 완료)
- AC-003 게이트 실패 (1/5, 502 + error, subprocess 미실행)
- AC-004 CLI 바이너리 부재 (503, Perplexity 모드 무영향)
- AC-005 Deep 쿼터 초과 (429, Perplexity 카운터 불변)
- AC-006 클라이언트 연결 끊김 (≤1s terminate, ≤16s 좀비 제거, /tmp 삭제)

### Exclusions (설계 N1~N5 + 추가 2건)
- 상주 Claude Code 세션·데몬 금지
- Perplexity 모드 스키마·프롬프트·쿼터 수정 금지
- 서버사이드 벡터 DB·RAG 금지
- 리포트 DB 영구 저장 구조 변경 금지
- `.claude/agents`·`.claude/skills` 영구 등록 금지
- 자동 폴백(Perplexity → Deep) 금지 — 2단 토글 확정
- Opus 강제 승격 금지 — 사용자 옵션만

---

## 8. 아키텍처 설계 요약 (architect)

### 8.1 신규/수정 파일 요약

| 구분 | 파일 | 역할 |
|------|------|------|
| 신규 | `backend/services/deep_research_collector.py` | 5-parallel 수집 + `/tmp` 스테이징 |
| 신규 | `backend/services/claude_cli_streamer.py` | subprocess + stream-json 파서 → SSE |
| 신규 | `backend/services/deep_research_service.py` | Phase 1~5 오케스트레이션 |
| 신규 | `backend/prompts/stock_synthesis_prompt.md` | 합성 전용 시스템 프롬프트 |
| 수정 | `backend/routers/ai_report.py` | `?mode=deep`·`?model=` 분기 |
| 수정 | `backend/services/ai_report_service.py` | `check_deep_rate_limit()` 추가 |
| 수정 | `backend/main.py` | lifespan: CLI·신규 프롬프트 검증 |
| 수정 | `frontend/src/components/AiReportModal.tsx`, `hooks/useAiReport.ts`, `api/aiReport.ts` | 2단 토글 + mode/model 전달 |

### 8.2 공개 인터페이스 계약

```python
# deep_research_collector.py
@dataclass
class CollectionResult:
    staging_dir: Path
    sources_ok: list[str]
    sources_failed: list[tuple[str, str]]
    gate_passed: bool  # len(sources_ok) >= 2

async def collect(code: str, stock_name: str, staging_dir: Path) -> CollectionResult: ...

# claude_cli_streamer.py
async def stream_synthesis(
    staging_dir: Path,
    prompt_path: Path,
    model: str,  # "sonnet" | "opus"
) -> AsyncGenerator[str, None]: ...

# deep_research_service.py
async def stream_deep_report(
    code: str,
    stock_name: str,
    model: str,
) -> AsyncGenerator[str, None]: ...
```

### 8.3 Claude CLI 실행 인자 (고정 계약)

```
claude -p "<instruction>" \
  --cwd /tmp/analysis_<code>_<ISO8601>_<uuid8> \
  --append-system-prompt "<content of stock_synthesis_prompt.md>" \
  --allowedTools "Read,Grep,Glob" \
  --output-format stream-json \
  --verbose \
  --model <sonnet|opus>
```

### 8.4 stream-json 파서 방어 규칙

- `type == "assistant"` → `message.content[*].text`를 SSE data 청크로 yield
- `type == "result"` → break (SSE `event: done`)
- `type == "system"` + `subtype == "error"` → SSE `event: error`
- 미지의 type → 무시 (방어적)
- `json.JSONDecodeError` → 해당 라인 로그 후 계속

### 8.5 Rate Limit 분리 설계

```python
# 신규 — 기존 check_rate_limit()과 완전 분리
AI_REPORT_DEEP_DAILY_QUOTA = int(os.environ.get("AI_REPORT_DEEP_DAILY_QUOTA", "15"))
AI_REPORT_DEEP_BURST_LIMIT = int(os.environ.get("AI_REPORT_DEEP_BURST_LIMIT", "1"))
# @MX:ANCHOR: fan_in >= 2 (router + tests)
def check_deep_rate_limit() -> None: ...
```

### 8.6 @MX 태그 계획

| 위치 | 태그 | 이유 |
|------|------|------|
| `deep_research_service::stream_deep_report` | `@MX:ANCHOR` | 공개 엔트리, fan_in ≥ 2 |
| `claude_cli_streamer::_parse_stream_json` | `@MX:WARN` | subprocess stdout 포맷 신뢰성·버전 변동 |
| `deep_research_collector::_stage_sources` | `@MX:NOTE` | `/tmp` 네이밍 규약 |
| `_active_analyses` Deep 경로 재사용 | `@MX:WARN` | 전역 가변 상태 (SPEC-001 기존 경고 연속) |
| `lifespan()의 shutil.which("claude")` | `@MX:ANCHOR` | startup invariant |
| `check_deep_rate_limit` | `@MX:ANCHOR` | 비용 폭주 방지, fan_in ≥ 2 |

### 8.7 리스크 완화 매핑

| 리스크 | 완화 | 위치 |
|-------|------|------|
| CLAUDE.md 자동 로드 오염 | `/tmp` cwd + allowedTools | claude_cli_streamer |
| stream-json 포맷 변동 | 방어적 파서 (unknown skip) | `_parse_stream_json` |
| 비용 폭주 | Deep 전용 쿼터 | `check_deep_rate_limit` |
| CLI 미설치 | startup `shutil.which` | `main.py lifespan()` |
| 좀비 프로세스 | finally의 terminate→kill | `claude_cli_streamer` |
| `/tmp` 포화 | startup task 7일 TTL 청소 | `deep_research_service` |
| 전체 소스 실패 | 2/5 게이트 | `deep_research_service` |

### 8.8 기존 코드 재사용 확정

| 자산 | 재사용 |
|------|-------|
| `_sanitize_name()` | Deep 리포트 파일명 안전화 |
| `save_report()` | Deep 최종 저장 (동일 경로) |
| `get_stock_name()` | 라우터 종목 검증 |
| `_active_analyses` | Deep 중복 요청 방지 (동일 set 공유) |
| `docs/deep-research/skill.md` API 스키마 | 각 엔드포인트 URL/파라미터 확정값 |
| `merge_results.py::parse_*` | 소스별 파서 로직 참고 (httpx 포팅) |

---

## 9. 위험·제약 요약

1. **claude CLI 런타임 의존**: 배포 환경에 `claude` 바이너리 필요. Docker 이미지 포함 or 로컬 전용 기능으로 게이팅
2. **멀티워커 비호환**: `_active_analyses` 전역 상태는 단일 프로세스 uvicorn 전제 (기존 `@MX:WARN` 연속)
3. **stream-json 포맷 변동**: Claude Code 버전 업 시 이벤트 구조 변경 가능 → 방어적 파서 + 버전 핀닝
4. **`/tmp` 포화**: 7일 TTL 정리 startup task 필수
5. **`testpaths` 불일치**: `pyproject.toml:55`에 `tests` 설정됨. 실제 테스트는 `backend/tests/`. SPEC-002 테스트도 동일 위치 → 통합 테스트 실행 검증 필요

---

## 10. architect 에스컬레이션 — 사용자 확인 필요 3건

1. **Perplexity 수집 방식** — 비스트리밍 헬퍼 신규 작성 vs 기존 `stream_perplexity()` 버퍼 축적 재사용
2. **리포트 저장 경로** — `backend/reports/{종목명}/` 통합 vs `backend/reports/deep/{종목명}/` 분리
3. **관찰성 수준** — 로그 only vs 선택적 Prometheus 메트릭

이 3건은 `plan.md` Open Questions로 이관되어 annotation cycle에서 확정합니다.
