# SPEC-AI-REPORT-003 Compact (Quick Reference)

**ID**: SPEC-AI-REPORT-003 | **Status**: Planned | **Created**: 2026-04-23

## 한 줄 요약

Perplexity API 를 Fast/Deep 양쪽 모두에서 완전 제거하고 Codex CLI (ChatGPT 구독 기반 무료) 로 전면 대체한다. 품질 최우선, 비용 0.

## 핵심 설계 결정

| 항목 | 결정 |
|---|---|
| 대체 범위 | Fast Mode + Deep Mode 양쪽 완전 대체 |
| Fallback | 없음 + 1회 재시도만 |
| Fast UX | Codex non-streaming → 30초 단위 heartbeat SSE + 완료 시 청크 분할 |
| 타임아웃 | 600초 (실측 2~9분 커버) |
| 인증 | Codex 는 `codex login` (ChatGPT 계정), API 키 불필요 |
| SSE 계약 | 기존과 동일 (프론트 코드 최소 변경) |

## 신규 파일

```
backend/services/codex_cli_runner.py  # subprocess 호출 어댑터
backend/prompts/codex_prompt.md       # Codex 전용 프롬프트 템플릿
backend/tests/test_codex_cli_runner.py
```

## 수정 파일

```
backend/services/ai_report_service.py       # stream_perplexity 제거, stream_codex_fast 추가
backend/services/deep_research_collector.py # _collect_codex 추가, _collect_perplexity 제거
backend/services/deep_research_service.py   # staging 3단계, SSE phase 이름
backend/prompts/stock_synthesis_prompt.md   # sources/perplexity.md → sources/codex.md
backend/routers/ai_report.py                # codex 바이너리 체크
backend/main.py                             # _load_prompt_template 호출 제거
frontend/src/types/aiReport.ts              # SourceName 갱신
frontend/src/components/**                  # ProgressPanel 라벨, Fast Mode 로딩 UI
.env.example                                # PERPLEXITY_API_KEY 제거
```

## 삭제 파일

```
backend/services/perplexity_cache.py
backend/prompts/perplexity_prompt.md
```

## 파이프라인 흐름 (변경 후)

```
POST ?mode=fast
  → 가드 체인 (코드/종목/codex 바이너리/중복/rate limit)
  → stream_codex_fast (codex exec subprocess)
  → 30초 heartbeat SSE + 완료 시 markdown 청크 분할
  → save_report

POST ?mode=deep
  → 가드 체인
  → prepare_staging_directory  # /tmp/analysis_<code>_<uuid>/sources/ 사전 생성
  → collect_all_sources  # codex 포함 5-소스 병렬 (Codex 는 --output-last-message 로 직접 md 작성)
     → 실패 시 1회 재시도 (codex 만)
  → finalize_staging_directory  # summary.md + 기타 소스 파일 기록
  → claude CLI 합성 (sources/codex.md 참조)
  → SSE data/done/error
```

## 핵심 인수 기준 (요약)

| AC | 조건 | 기대 결과 |
|---|---|---|
| AC-001 | mode=fast | heartbeat + markdown 청크 SSE |
| AC-002 | mode=deep | codex 포함 5-소스, sources/codex.md 생성 |
| AC-003 | Codex 첫 호출 실패 | 1회 재시도 |
| AC-005 | 구현 완료 후 | grep perplexity 결과 없음 |
| AC-009 | Codex 실패 + 2/4 성공 | 게이트 통과 |
| AC-012 | pytest | 전부 통과 |

## @MX 태그 계획

**ANCHOR (신규)**:
- `codex_cli_runner.py::run_codex_research()` — fan_in >= 2 (fast + deep)
- `deep_research_collector.py::_collect_codex()` — 교체됨

**WARN (신규)**:
- `codex exec subprocess` — 좀비 프로세스 위험, terminate→kill 2단계 정리 필수
- Codex 샘플링 재현성 — temperature 제어 불가

**제거 (Perplexity 관련)**:
- `stream_perplexity::@MX:ANCHOR` — 함수 삭제와 함께 제거
- `_collect_perplexity::@MX:ANCHOR` — 삭제

## 환경변수 (변경)

**제거**:
```bash
PERPLEXITY_API_KEY=   # 완전 삭제
```

**재정의 (값 유지, 의미만 쿼터 보호로)**:
```bash
AI_REPORT_DAILY_QUOTA=50       # ChatGPT 구독 쿼터 보호
AI_REPORT_BURST_LIMIT=3
AI_REPORT_DEEP_DAILY_QUOTA=15
AI_REPORT_DEEP_BURST_LIMIT=1
```

**불변 (Deep Mode 다른 소스)**:
```bash
BRAVE_API_KEY=
TAVILY_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

## 위험 상위 3개

1. **Fast Mode 실시간 스트리밍 UX 손실** — heartbeat 30s + 청크 분할로 완화. 사용자 피드백 수집 필요.
2. **Codex 응답시간 2~9분 변동** — 600s 타임아웃 + 1회 재시도. 최악 20분 대기.
3. **ChatGPT 쿼터 소진** — `AI_REPORT_DAILY_QUOTA=50` 재정의 (쿼터 보호). 소진 시 HTTP 429.

## 구현 단계

Step 1 (runner) → Step 2 (프롬프트) → Step 3 (Deep slot) → Step 4 (Fast) → Step 5 (cleanup) → Step 6 (synthesis + FE) → Step 7 (회귀) → Step 8 (실 스모크)

각 Step 착수 전 **명시적 사용자 승인 필수** — "계속해" 를 묵시적 승인으로 해석하지 않음.
