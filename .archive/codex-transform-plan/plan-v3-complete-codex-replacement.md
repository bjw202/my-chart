# Plan V3 — Perplexity 완전 제거 + Codex 전면 대체

**SPEC**: SPEC-AI-REPORT-003 (신규 발행)
**선행 Plan**: V1/V2 폐기 (보존됨, 참조용)

## 사용자 확정 제약

| 제약 | 값 |
|---|---|
| **최우선 기준** | 품질 (비용 무관 — Codex 는 ChatGPT 정기구독으로 무료) |
| 대체 범위 | **Fast + Deep 양쪽 완전 대체** — Perplexity API 완전 제거 |
| Fallback | 없음 + 1회 재시도만 (transient 실패 대응) |
| SPEC 번호 | SPEC-AI-REPORT-003 신규 |

## Context

`perplexity-usage-analysis.md` 전수 조사 결과, Perplexity 는 두 경로에서 쓰인다:

- **Fast Mode**: `ai_report_service.py::stream_perplexity` — 사용자 SSE 스트리밍
- **Deep Mode**: `deep_research_collector.py::_collect_perplexity` — 5-소스 병렬 중 하나

V3 는 두 경로 모두 Codex CLI 로 대체. Perplexity 관련 모든 자산 (함수, 캐시, 프롬프트, 환경변수) 을 완전 제거한다.

`comparison-samsungsdi-2026-04-23.md` 3-way 측정 결과 Codex 의 팩트 포착률이 83% (Perplexity Deep 8%, Enhanced 58% 대비) 로 우세했고, 사용자의 "품질 최우선" 기준에 부합.

## 아키텍처

### Before (현재)

```
POST /api/ai-report/{code}?mode=fast
  └→ stream_perplexity (Perplexity SSE streaming)
  └→ perplexity_cache.put()  [TTL 600s]

POST /api/ai-report/{code}?mode=deep
  └→ deep_research_service.stream_deep_analysis
       └→ collect_all_sources (5개 병렬)
            ├→ _collect_perplexity  ← 캐시 hit 시 HTTP skip
            ├→ _collect_brave
            ├→ _collect_tavily
            ├→ _collect_naver
            └→ _collect_youtube
       └→ Claude CLI 합성 (sources/*.md, *.json 읽음)
```

### After (V3)

```
POST /api/ai-report/{code}?mode=fast
  └→ stream_codex_fast (Codex exec, SSE protocol 유지)
       └→ 진행 이벤트 + 완료 시 전체 결과 전송 (non-streaming 내부)

POST /api/ai-report/{code}?mode=deep
  └→ deep_research_service.stream_deep_analysis
       └→ collect_all_sources (5개 병렬)
            ├→ _collect_codex  ← 신규, 1회 재시도
            ├→ _collect_brave
            ├→ _collect_tavily
            ├→ _collect_naver
            └→ _collect_youtube
       └→ Claude CLI 합성 (sources/codex.md + *.json)
```

## 제거 대상

### 파일 완전 삭제
- `backend/services/perplexity_cache.py`
- `backend/tests/test_perplexity_cache.py` (존재 시)
- `backend/prompts/perplexity_prompt.md` (Codex 프롬프트로 재활용 가능성 검토 후 결정 — 일단 별도 `codex_prompt.md` 신설 권장)

### 함수/상수 제거
- `ai_report_service.py::stream_perplexity()` → `stream_codex_fast()` 로 교체
- `ai_report_service.py::SYSTEM_PROMPT` → Perplexity 전용이었으므로 Codex 프롬프트로 재설계
- `ai_report_service.py::SEARCH_DOMAIN_FILTER` — Codex 는 자체 웹 검색 도구 사용, 불필요
- `ai_report_service.py::load_prompt`, `_load_prompt_template`, `_PROMPT_TEMPLATE_PATH` — Codex 프롬프트 로더로 대체
- `deep_research_collector.py::_collect_perplexity()` → `_collect_codex()` 로 교체
- `deep_research_collector.py::_normalize_perplexity()` — 삭제 (Codex 는 Markdown 직접 출력)
- `SOURCE_NAMES`: `"perplexity"` → `"codex"`

### 환경변수 제거
- `PERPLEXITY_API_KEY` — `.env`, `.env.example`, 모든 문서에서 제거

### 설정 정리
- `AI_REPORT_BURST_LIMIT`, `AI_REPORT_DAILY_QUOTA` 등 rate limit 은 Codex 전용으로 의미 재정의 (또는 "무료지만 ChatGPT 쿼터 보호" 차원으로 보수적 유지)

## 신규 추가

### 파일
- `backend/services/codex_cli_runner.py` — subprocess 호출 어댑터 (`run_codex_research`)
- `backend/prompts/codex_prompt.md` — Codex 전용 프롬프트 템플릿 (Fast/Deep 공용 or 분리)
- `backend/tests/test_codex_cli_runner.py` — fake bash wrapper 기반 단위 테스트
- `.moai/specs/SPEC-AI-REPORT-003/` — SPEC 문서 (EARS 형식)

### 함수
- `run_codex_research(stock_name, code, *, timeout=600, retry=1) -> CodexResult`
- `_collect_codex(code, stock_name, *, client=None) -> SourceResult`
- `stream_codex_fast(stock_name) -> AsyncGenerator[str, None]`
  - Codex 를 한 번에 호출하되, 내부적으로 "분석 중" 진행 메시지를 주기적으로 yield 하고 완료 시 full markdown 을 분할 yield
  - SSE 계약 유지 (프론트엔드 변경 최소화)

## Fast Mode UX 전환 전략

Codex 는 non-streaming 이므로 실시간 토큰 스트리밍 불가. 사용자 경험 보완:

```
이벤트 시퀀스:
  t=0s    : "Codex 분석 시작..." (phase 이벤트)
  t=30s   : "웹 검색 진행 중... (N회)" (heartbeat)
  t=60s   : "자료 교차 검증 중..."
  t=90s   : "리포트 작성 중..."
  t=~180s : 완료 시 full markdown 을 청크 단위로 분할 yield (100자 단위 등)
  t=end   : "완료" 이벤트
```

heartbeat 는 실제 Codex 상태를 반영하기 어렵다면 일정 간격 타이머 기반 안내 메시지로 대체. 사용자는 "생각 중" 로딩 바와 주기적 메시지로 대기 체감을 완화한다.

프론트엔드는 기존 SSE 청크 수신 로직 그대로 재사용 — 내용만 Codex 기반.

## Deep Mode 슬롯 교체

`_collect_codex` 구현:

```python
async def _collect_codex(code, stock_name, *, client=None) -> SourceResult:
    # Rate limit 게이트
    # (client 는 httpx 관례 유지용. Codex 는 subprocess 라 client 미사용)
    
    for attempt in range(2):  # 1회 재시도
        result = await run_codex_research(
            stock_name=stock_name, 
            code=code,
            timeout=600.0,
        )
        if result.success:
            return SourceResult(
                name="codex",
                success=True,
                data={"markdown_path": str(result.output_path), "char_count": result.char_count},
                duration_ms=result.duration_ms,
            )
        if result.error_type == "binary_missing":
            # 재시도 무의미
            break
    
    return SourceResult(
        name="codex",
        success=False,
        data=None,
        error_type=result.error_type,
        error_message=result.error_message,
        duration_ms=result.duration_ms,
    )
```

`_DEFAULT_TIMEOUTS["codex"] = 600.0` (기존 perplexity 키 제거).

## 스테이징 디렉토리 재설계

현재 `create_staging_directory()` 는 성공 소스 후처리로 `sources/*.md, *.json` 작성. Codex 는 이미 `--output-last-message` 로 파일에 직접 쓰므로 스테이징 디렉토리 생성이 **수집 전에** 이뤄져야 함.

→ `create_staging_directory()` 를 `prepare_staging_directory()` + `finalize_staging_directory()` 2 단계로 분리 (V1/V2 와 동일 접근).

## 합성 프롬프트 갱신

`backend/prompts/stock_synthesis_prompt.md` 의 "sources/perplexity.md" 언급을 "sources/codex.md" 로 교체. 내용 형식은 동일 (Markdown + 인용).

## 프론트엔드 변경

- `frontend/src/types/aiReport.ts::SourceName`: `"perplexity"` → `"codex"`
- 진행 상태 패널 라벨: "Codex 심층 리서치"
- Fast Mode 로딩 UI: "Codex 가 분석 중..." + heartbeat 메시지

## 구현 단계

**Step 1**: SPEC-AI-REPORT-003 문서 작성 (manager-spec, EARS 형식)
**Step 2**: Codex CLI runner 어댑터 + 테스트 (manager-tdd, RED-GREEN-REFACTOR)
**Step 3**: Codex 프롬프트 템플릿 작성 (Fast/Deep 공용)
**Step 4**: Deep Mode 슬롯 교체 (`_collect_codex` + `SOURCE_NAMES` 갱신 + staging 2단계 분리)
**Step 5**: Fast Mode 전환 (`stream_codex_fast` + 라우터 갱신)
**Step 6**: Perplexity 자산 완전 제거 (파일·함수·상수·환경변수)
**Step 7**: 합성 프롬프트·SSE 이벤트·프론트엔드 라벨 갱신
**Step 8**: 전체 회귀 테스트 + 실 Codex 스모크

각 Step 착수 전에 **Approach 제시 + 사용자 승인** 필수 (이번에는 "계속" 을 묵시적 승인으로 해석하지 않음 — 매번 명시적 확인).

## Risks

1. **Fast Mode UX 손실 체감** — 실시간 스트리밍이 사라져 사용자가 수 분간 로딩만 보게 됨. heartbeat 메시지로 완화하지만 본질적 차이. 초기 배포 후 사용자 피드백 모니터링 필요.
2. **Codex 응답 시간 변동** — 2~9분 관측. 600초 타임아웃으로 대응하나 더 길어질 가능성. 1회 재시도까지 포함하면 최악 20분.
3. **ChatGPT 쿼터 한도** — 무료지만 ChatGPT 구독의 사용 한도 내에서. 일일 호출 많으면 쿼터 소진 가능. `AI_REPORT_DAILY_QUOTA` (현재 50) 는 과금 방지가 아닌 쿼터 보호 차원으로 재정의.
4. **재현성** — Codex 는 gpt-5.4 샘플링으로 결과 재현성이 Perplexity (temperature=0.2) 보다 낮음. 품질 일관성 모니터링 필요.
5. **Perplexity 캐시 시나리오 C 소멸** — 기존엔 Fast Mode 결과를 Deep Mode 에서 재사용. V3 에서는 별도 Codex 캐시 신설 여부 결정 필요 (사용자가 Fast 직후 Deep 실행 시 Codex 2회 호출).

## Codex 캐시 (선택 사항)

기존 `perplexity_cache.py` 패턴을 `codex_cache.py` 로 복제해 Fast → Deep 비용 (쿼터) 절감 유지 가능. 단 **Fast Mode 의 Codex 결과 포맷이 Deep Mode 에서 같은 슬롯을 채울 수 있어야** 함. 구현 Step 4 설계 시 결정.

## 합격 기준

- 전체 테스트 (현재 105건) 통과
- 실 Codex 호출로 Fast/Deep 양쪽 end-to-end 작동 확인
- `grep -r "perplexity" backend/` 결과가 빈 상태 (완전 제거 검증)
- `.env.example` 에 `PERPLEXITY_API_KEY` 부재
- SPEC-AI-REPORT-003 문서 EARS 형식 완비
