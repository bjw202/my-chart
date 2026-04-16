# SPEC-AI-REPORT-002 Compact (Quick Reference)

**ID**: SPEC-AI-REPORT-002 | **Status**: Planned | **Created**: 2026-04-16

## 한 줄 요약

Perplexity 단일 소스 한계를 5-소스 병렬 수집 + Claude CLI 헤드리스 합성으로 보완하는 "심층 분석(Deep)" 모드 추가.

## 핵심 설계 결정

| 항목 | 결정 |
|---|---|
| 모드 분기 | `?mode=deep` 쿼리 파라미터 (기본: `perplexity`) |
| 합성 모델 | Sonnet 기본, `AI_REPORT_DEEP_MODEL=opus`로 승격 |
| 프론트 UX | 명시적 2단 토글 ("빠른 분석" / "심층 분석 ~90초") |
| 하네스 | `/tmp` 격리 only — `.claude/` 영구 등록 없음 |
| SSE 계약 | 기존과 동일 (프론트 코드 최소 변경) |
| 비용 통제 | Deep 전용 쿼터 (일일 15, 분당 1) 분리 |

## 신규 파일

```
backend/services/
  deep_research_collector.py   # Phase 1: 5-소스 병렬 수집 + 스테이징
  claude_cli_streamer.py       # Phase 3-4: CLI 호출 + stream-json 파싱
  deep_research_service.py     # Phase 1-5 오케스트레이션 + rate limit

backend/prompts/
  stock_synthesis_prompt.md    # Claude 합성 전용 시스템 프롬프트

backend/tests/
  test_deep_research_service.py
```

## 수정 파일

```
backend/routers/ai_report.py       # mode 파라미터 분기 추가
backend/main.py                    # shutil.which + synthesis prompt 검증
frontend/src/components/AiReportModal.tsx  # 2단 토글 UI
frontend/src/hooks/useAiReport.ts  # startStream(code, mode) 시그니처
frontend/src/api/aiReport.ts       # ?mode=${mode} URL 추가
```

## 보존 대상 (절대 수정 금지)

```
backend/services/ai_report_service.py   # SPEC-001 Perplexity 로직 전체
backend/prompts/perplexity_prompt.md    # NFR-004 프롬프트 무결성
```

## 파이프라인 흐름

```
POST ?mode=deep
  → 가드 체인 (코드/종목/키/claude 바이너리/중복/rate limit)
  → Phase 1: asyncio.gather 5-소스 수집 (≥2/5 게이트)
  → Phase 2: /tmp/analysis_<code>_<uuid>/ 스테이징
  → Phase 3: claude -p --cwd /tmp/<uuid> --allowedTools "Read,Grep,Glob"
             --output-format stream-json --verbose
  → Phase 4: stream-json 라인 파싱 → SSE data/done/error
  → Phase 5: save_report() + /tmp 정리
```

## 핵심 인수 기준 (요약)

| AC | 조건 | 기대 결과 |
|---|---|---|
| AC-001 | mode 파라미터 없음 | 기존 Perplexity 동작 무변경 |
| AC-004 | 1/5 소스 성공 | SSE error + 파이프라인 중단 |
| AC-007 | unknown type JSON | 무시, 스트리밍 계속 |
| AC-009 | 180초 초과 | proc.terminate → proc.kill + SSE error |
| AC-011 | 16번째 Deep 요청 | HTTP 429, Perplexity 쿼터 무영향 |
| AC-012 | claude 바이너리 없음 | HTTP 503, Perplexity 모드 정상 |
| AC-017 | SPEC-001 기존 테스트 | 30개 전부 통과 |

## @MX 태그 계획

**ANCHOR** (신규, fan_in >= 2):
- `deep_research_service.py::stream_deep_analysis()` — 라우터+테스트
- `deep_research_service.py::check_deep_rate_limit()` — 라우터+테스트
- `claude_cli_streamer.py::stream_claude_synthesis()` — 오케스트레이터+테스트

**WARN** (신규):
- `_active_deep_analyses: set` — 멀티워커 전역 상태
- `asyncio.create_subprocess_exec` 호출부 — subprocess 좀비 위험

## 환경변수 (신규)

```bash
AI_REPORT_DEEP_DAILY_QUOTA=15
AI_REPORT_DEEP_BURST_LIMIT=1
AI_REPORT_DEEP_MODEL=sonnet     # opus 로 변경 시 Opus 승격
BRAVE_API_KEY=
TAVILY_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

## 위험 상위 3개

1. **claude CLI 미설치** — `shutil.which` + 503 게이팅으로 완화
2. **stream-json 포맷 변동** — 방어적 파싱 (unknown type 무시)
3. **/tmp 디스크 포화** — 7일 초과 자동 정리 + 요청 후 즉시 정리

## 구현 단계

A (CLI PoC) → B (수집기) → C (합성 통합) → D (라우터/UX) → E (운영화)
