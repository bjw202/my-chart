# SPEC-AI-REPORT-003 구현 계획

## 단계 개요

```
Step 1: Codex CLI runner 어댑터 + 단위 테스트
Step 2: Codex 프롬프트 템플릿 작성
Step 3: Deep Mode Codex 슬롯 교체 + staging 2단계 분리
Step 4: Fast Mode Codex 전환 (heartbeat)
Step 5: Perplexity 자산 완전 제거
Step 6: 합성 프롬프트 + SSE 이벤트 + 프론트엔드 라벨
Step 7: 전체 회귀 테스트
Step 8: 실 Codex 스모크 (Fast + Deep end-to-end)
```

각 Step 은 독립 커밋 가능한 단위. 이전 Step 테스트가 통과한 후에만 다음 Step 진행.

---

## Step 1 — Codex CLI runner 어댑터

### 신규 파일
- `backend/services/codex_cli_runner.py` — `run_codex_research()` 함수 + `CodexResult` dataclass
- `backend/tests/test_codex_cli_runner.py` — fake bash wrapper 기반 단위 테스트

### 핵심 함수 시그니처

```python
@dataclass(frozen=True)
class CodexResult:
    success: bool
    output_path: Path | None
    char_count: int
    error_type: str | None  # "timeout" | "exit_error" | "binary_missing" | "empty_output" | "auth" | None
    error_message: str | None
    duration_ms: int


async def run_codex_research(
    *,
    code: str,
    stock_name: str,
    output_path: Path,
    timeout: float = 600.0,
    _cmd_override: list[str] | None = None,  # 테스트 전용
) -> CodexResult
```

### 구현 포인트
- argv: `codex exec --skip-git-repo-check --sandbox read-only -C <dir> --output-last-message <path> --color never --json "<prompt>"`
- subprocess 관리: `asyncio.create_subprocess_exec` + `terminate → kill 2단계 정리` (from `claude_cli_streamer.py:110-131` 복제)
- stderr drain: 마지막 50 라인 보관 (`claude_cli_streamer.py:194-202` 패턴)
- 에러 분류 (ER-001~004)

### 테스트 케이스 (6개 이상)
- `test_run_codex_success_writes_md` — fake bash wrapper 가 `--output-last-message` 경로에 md 작성 후 exit 0
- `test_run_codex_timeout` — sleep 스크립트, timeout=1
- `test_run_codex_empty_output` — exit 0 이지만 파일 미작성
- `test_run_codex_binary_missing` — `_cmd_override=["__nonexistent__"]`
- `test_run_codex_nonzero_exit` — exit 7 + stderr 내용
- `test_run_codex_cancelled` — asyncio.Task.cancel()

### 검증
- `pytest backend/tests/test_codex_cli_runner.py -v` 전부 green
- Step 1 완료 시 기존 파이프라인 **무손상** (어댑터만 신규 추가)

---

## Step 2 — Codex 프롬프트 템플릿

### 신규/갱신 파일
- `backend/prompts/codex_prompt.md` — Codex 전용 프롬프트 (Fast/Deep 공용)
- `backend/prompts/stock_synthesis_prompt.md` — `sources/perplexity.md` → `sources/codex.md` (Step 6 에서 함께 처리)

### 프롬프트 설계
- 종목명/코드 치환 플레이스홀더 (`〈종목명〉`, `〈종목코드〉`)
- 섹션: Executive Summary / 사업 본질 / 최신 이벤트 / 시장 심리 / 실적·밸류·수급·테크니컬 / Catalyst / 리스크 / 스윙 진입·청산 관점
- 출력 규칙: [n] 형식 인용 + 참고문헌 섹션, 추상어·매매권유 금지

### 검증
- 템플릿 로드 유닛 테스트 (`test_load_codex_prompt`)
- 플레이스홀더 부재 시 `ValueError`

---

## Step 3 — Deep Mode Codex 슬롯 교체

### 수정 파일
- `backend/services/deep_research_collector.py`
  - `_collect_codex(code, stock_name, *, client=None, staging_sources_dir: Path) -> SourceResult` 신규
  - `_collect_perplexity` 제거 (Step 5 로 미룰 수도 있으나 시그니처는 Step 3 에서 치환)
  - `_normalize_perplexity` 제거
  - `SOURCE_NAMES`: `"perplexity"` → `"codex"`
  - `_DEFAULT_TIMEOUTS["codex"] = 600.0`, `"perplexity"` 키 제거
  - `create_staging_directory` → `prepare_staging_directory()` + `finalize_staging_directory()` 2단계 분리
  - 1회 재시도 로직 구현
- `backend/services/deep_research_service.py`
  - staging 3단계 호출로 재배치 (`prepare → collect → finalize`)
  - `collect_all_sources` 에 `staging_sources_dir` 전달
  - SSE phase 이벤트 name: `"perplexity"` → `"codex"`
  - `_source_count` 에 `markdown_path` / `char_count` 분기 추가

### 테스트 갱신
- `test_deep_research_collector.py`
  - `test_collect_perplexity_*` 4개 삭제
  - `test_collect_codex_success`, `test_collect_codex_timeout`, `test_collect_codex_binary_missing`, `test_collect_codex_retry_succeeds`, `test_collect_codex_retry_fails` 신규
  - `test_write_perplexity_md_think_stripped` → `test_write_codex_md_present` 로 교체 (Codex 는 think 블록 없음)
  - `test_normalize_perplexity_none` 삭제
- `test_deep_research_service.py`
  - SSE phase 이벤트 시퀀스 검증에 `"codex"` 반영
  - user_prompt 스냅샷 갱신

### 검증
- 기존 Deep Mode 통합 흐름 유지, phase 이벤트 이름만 변경
- pytest 통과

---

## Step 4 — Fast Mode Codex 전환 (Heartbeat)

### 수정 파일
- `backend/services/ai_report_service.py`
  - `stream_perplexity` 삭제
  - `stream_codex_fast(stock_name) -> AsyncGenerator[str, None]` 신규
    - Codex subprocess 를 background task 로 실행
    - 30초 단위 heartbeat 메시지 yield
    - 완료 시 markdown 을 256자 청크로 분할 yield
  - `SYSTEM_PROMPT, SEARCH_DOMAIN_FILTER, load_prompt, _load_prompt_template, _PROMPT_TEMPLATE_PATH` 삭제
  - `perplexity_cache` import 제거
- `backend/routers/ai_report.py`
  - `stream_perplexity` 호출 → `stream_codex_fast` 로 교체
  - `claude CLI` 바이너리 체크 외에 `codex` 바이너리 체크 추가
- `backend/main.py`
  - `_load_prompt_template` 호출 제거 또는 Codex 프롬프트 로더로 교체

### 테스트 갱신
- `test_ai_report_service.py`
  - `TestLoadPrompt` 제거
  - `TestStreamCodexFast` 신규 (fake codex runner 주입, heartbeat 이벤트 검증)
- `test_ai_report_router_deep_mode.py` 는 Deep 중심이라 일부 perplexity stub 만 codex stub 으로 교체

### 검증
- Fast Mode end-to-end 수동 테스트 (실 Codex 호출 생략, mocking)
- SSE heartbeat 30초 주기 확인

---

## Step 5 — Perplexity 자산 완전 제거

### 삭제 파일
- `backend/services/perplexity_cache.py`
- `backend/prompts/perplexity_prompt.md` (내용은 `codex_prompt.md` 로 이미 재설계됨)

### `.env` / `.env.example` 갱신
- `PERPLEXITY_API_KEY` 라인 제거
- 주석에 "Codex CLI 는 `codex login` 으로 인증, 별도 API 키 불필요" 명시

### 검증
- `grep -ri "perplexity" backend/ --include="*.py"` → 결과 없음
- `grep "PERPLEXITY_API_KEY" .env.example` → 결과 없음
- `ls backend/services/perplexity_cache.py backend/prompts/perplexity_prompt.md` → 둘 다 없음
- pytest 전체 통과 (perplexity 관련 import 잔재 없음)

---

## Step 6 — 합성 프롬프트·SSE·프론트엔드

### 수정 파일
- `backend/prompts/stock_synthesis_prompt.md`
  - `sources/perplexity.md` → `sources/codex.md` (전체 replace)
  - `[perplexity]` → `[codex]` (인용 표기)
- `backend/services/deep_research_service.py`
  - user_prompt 에서 파일명 언급 갱신
- `frontend/src/types/aiReport.ts`
  - `SourceName` 유니언: `"perplexity"` 제거, `"codex"` 추가
- `frontend/src/components/**` (grep 필요)
  - ProgressPanel 라벨 맵: `"codex": "Codex 심층 리서치"`
  - Fast Mode 로딩 컴포넌트: heartbeat 메시지 표시
- 프론트엔드 스냅샷/타입 테스트 갱신

### 검증
- TypeScript 컴파일 통과
- 프론트엔드 테스트 통과

---

## Step 7 — 전체 회귀 테스트

### 실행
```bash
unset VIRTUAL_ENV && source .venv/bin/activate
pytest backend/tests/ -v
```

### 기대
- 모든 새 Codex 테스트 통과
- 기존 non-perplexity 테스트 통과
- 기존 `my_chart.db` 관련 import 에러는 SPEC 범위 밖 (허용)

### 커버리지
- `pytest backend/tests/ --cov=backend/services --cov-report=term-missing`
- `codex_cli_runner.py`, `_collect_codex`, `stream_codex_fast` 85% 이상

---

## Step 8 — 실 Codex 스모크

### Fast Mode end-to-end

```bash
uvicorn backend.main:app --reload
curl -N "http://localhost:8000/api/ai-report/006400?mode=fast"
# 기대:
# - phase: codex_fast_progress 이벤트 수신 (30초 단위)
# - data: 이벤트로 markdown 청크 수신
# - done: 이벤트로 완료
```

### Deep Mode end-to-end

```bash
curl -N "http://localhost:8000/api/ai-report/006400?mode=deep"
# 기대:
# - phase: codex (수집 시작/종료)
# - /tmp/analysis_006400_<uuid>/sources/codex.md 생성
# - Claude CLI 합성 진행
# - data: 이벤트로 최종 리포트 청크 수신
```

### 1회 재시도 스모크

```bash
# codex 을 잠시 PATH 에서 제외해 첫 호출 실패 유도
PATH=/tmp/empty:$PATH (만 단일 세션)
# 기대: binary_missing 으로 즉시 실패, 재시도 없음

# Codex 를 느리게 만드는 wrapper 로 타임아웃 유도 (개발용)
# 기대: 첫 timeout 후 두 번째 재시도 시도
```

---

## 리스크 및 완화

| 리스크 | 완화 |
|---|---|
| Fast Mode UX 악화 | heartbeat 30초 + markdown 청크 스트리밍. 초기 배포 후 사용자 피드백 수집 |
| Codex 응답시간 변동 | timeout 600s + 1회 재시도. 최악 20분. 프론트엔드 대기 UI 필요 |
| ChatGPT 쿼터 소진 | `AI_REPORT_DAILY_QUOTA=50` 재정의 (쿼터 보호 용). 소진 시 HTTP 429 반환 |
| Codex 샘플링 재현성 | 초기 운영 모니터링. 과도한 분산 시 프롬프트 제약 강화 |
| import 순환 | Step 3 에서 `codex_cli_runner` 는 독립 모듈. `ai_report_service` / `deep_research_collector` 둘 다 이를 import 해도 순환 없음 |
| 스테이징 2단계 변경 회귀 | Step 3 내부에서 기존 테스트 전부 통과 확인 후 진행 |

---

## 단계별 승인 필요 체크리스트

각 Step 착수 전에 아래 사항을 사용자에게 확인:

1. 목적 (이 Step 에서 달성할 것)
2. 수정 파일 목록 (신규/수정/삭제)
3. 예상 리스크
4. 검증 방법

사용자가 명시적으로 "진행" 을 지시하기 전에는 구현 착수 금지. 이전 세션의 "계속해" 오해 재발 방지.
