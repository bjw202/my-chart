> **⚠️ 폐기됨 (2026-04-23)** — 이 Plan V1 은 Tavily 한 자리만 대체하는 초기 설계로,
> 측정 결과 **Perplexity 가 최종 리포트 품질에 더 큰 영향** 을 주므로 우선순위에서 밀렸고,
> 이후 사용자 최종 의사결정 (Perplexity 완전 제거, 비용 0) 에 따라 **V3 로 대체됨**.
> 현재 활성 계획: [`plan-v3-complete-codex-replacement.md`](./plan-v3-complete-codex-replacement.md).
> V1 내용은 히스토리 참조용으로만 보존.

# Codex CLI 기반 심층 리서치 소스 통합 (Tavily → Codex 대체) — 폐기됨

## Context

현재 my_chart 의 AI 분석 기능(`POST /api/ai-report/{code}?mode=deep`)은 5개 외부 API
(Perplexity, Brave, Tavily, Naver, YouTube)를 `httpx.AsyncClient` 로 병렬 호출해
스테이징 디렉터리에 저장한 뒤, Claude Code CLI 가 Read tool 로 읽어 합성 리포트를
작성하는 구조다. 그 중 Tavily 는 `search_depth: advanced` 로 20건 검색 결과를 받아오는
수준이라 "심층 리서치" 라는 이름값을 못 한다.

PC에 이미 설치돼 있는 Codex CLI (`codex-cli 0.121.0`, ChatGPT 계정 로그인 완료)는
GPT-5-Codex 모델로 웹 검색 + 추론 체인을 수행해 **자체적으로 한국어 분석 보고서**를
작성할 수 있다. 사용자의 최종 목표는 **Tavily 리서치를 Codex 심층 리서치로 대체**하는
것이며, 운영 안정성을 위해 Codex 실패 시 **Tavily 를 fallback 으로 유지**한다.

### 사용자 확정 사항 (AskUserQuestion 답변)

- Codex 역할: **심층 리서치 에이전트** (단순 검색기 아님) — 한국어 Markdown 보고서 반환
- 결과 포맷: `sources/codex_research.md`
- 타임아웃: 180초
- 실패 처리: **Codex 실패 시 Tavily fallback** (Tavily 코드/키 유지)

### 기술 배경 (사전 조사 확정 사실)

- **Codex CLI 실행 플래그 확인 완료**: `codex exec --skip-git-repo-check --sandbox read-only -o <FILE> --json --color never "<prompt>"` 형태 실행 가능 (`codex exec --help` 출력으로 검증).
- **인증**: ChatGPT 계정 로그인으로 완료되어 `OPENAI_API_KEY` 불필요. 웹 검색은 계정의 기본 tool catalog 에서 자동 장착 (기본 동작 확인은 스모크 테스트 필요 — Step 7.1).
- **기존 Claude CLI subprocess 패턴 재사용 가능**: `backend/services/claude_cli_streamer.py:110-131` 의 terminate→kill 2단계 정리, `:194-202` 의 stderr drain 패턴.
- **경로 안전 검사**: `deep_research_collector.py:857-864` 의 `_BLOCKED_ROOTS` 재사용.

---

## Recommended Approach

### 개요

```
기존:  collect_all_sources → [perplexity, brave, tavily, naver, youtube] 5개 병렬
                                         ↑ httpx POST
변경:  collect_all_sources → [perplexity, brave, codex_research, naver, youtube] 5개 병렬
                                         ↑ codex exec --output-last-message
                                         ↓ 실패 시 순차 fallback
                                         tavily (기존 코드 그대로)
```

1. 신규 어댑터 `codex_cli_runner.py` — Codex CLI subprocess 단일 호출 + 파일 산출물 검증.
2. `deep_research_collector.py` 에 `_collect_codex()` 추가, `SOURCE_NAMES` 에서 `tavily` → `codex_research` 치환. Tavily 함수는 **유지** (fallback 용).
3. `collect_all_sources()` 내부에 Codex 실패 시 Tavily 호출 fallback 분기 추가.
4. `stock_synthesis_prompt.md` 조건부 파일 명시 + `deep_research_service.py` user_prompt 갱신.
5. 프론트엔드 `types/aiReport.ts` SourceName 변경 + source_fallback 이벤트 처리.
6. 신규/확장 테스트 + 실 Codex 스모크 검증.

### 주요 설계 결정

| 항목 | 결정 | 근거 |
|---|---|---|
| Codex 결과 수집 방식 | `--output-last-message <md path>` 로 Codex 가 직접 파일 쓰기 | stdout JSONL 파싱보다 안전, 빈 파일 감지로 실패 판별 쉬움 |
| Sandbox 모드 | `-s read-only` | Codex 가 로컬 FS 를 수정하지 않도록 차단. `-o` 경로는 예외적으로 쓰기 허용됨 |
| subprocess 정리 | 신규 파일에 `_terminate_proc`/`_drain_stderr` **로직 복제** | import 경계 단순화. Claude stream-json vs Codex one-shot 은 흐름 제어가 근본적으로 달라 일반화 = 과설계 |
| Fallback 트리거 지점 | `collect_all_sources()` 내부 (gather 완료 후) | `_collect_one_source` 는 소스-불가지론 유지. fallback 로직은 상위에서 조건 분기 |
| 스테이징 디렉터리 생성 타이밍 | **collect 전 prepare_staging_directory** 로 분리 | Codex 가 수집 중 md 파일을 직접 써야 하므로 경로가 먼저 존재해야 함 |
| 타임아웃 180초 | 상수로 시작, 환경변수화는 2차 | 사용자 답변 명시. 추후 실측 후 `AI_REPORT_CODEX_TIMEOUT` 승격 예약 |

### 주요 파일 변경 (수정 범위)

#### 신규
- `backend/services/codex_cli_runner.py` — 단일 `run_codex_research()` 어댑터
- `backend/tests/test_codex_cli_runner.py` — bash wrapper 기반 fake codex 스모크

#### 수정
- `backend/services/deep_research_collector.py:580-596` — `_DEFAULT_TIMEOUTS` 에 `codex_research: 180.0`, `SOURCE_NAMES` 치환
- `backend/services/deep_research_collector.py:364-432` — `_collect_tavily` 유지 (dead code 아님, fallback 용)
- `backend/services/deep_research_collector.py:~450 (신규)` — `_collect_codex()` 추가, `staging_sources_dir` 인자 수용
- `backend/services/deep_research_collector.py:602-650` — `_collect_one_source` 에 `staging_sources_dir` 선택 인자 전달
- `backend/services/deep_research_collector.py:662-764` — `collect_all_sources()` 에 fallback 로직 추가, `_wrap_tavily_as_codex_slot()` 헬퍼 신설
- `backend/services/deep_research_collector.py:879-907` — `create_staging_directory` → `prepare_staging_directory()` + `finalize_staging_directory()` 2단계로 리팩터링. Codex 슬롯은 `data["fallback_from"]` 유무로 파일 생성 분기
- `backend/services/deep_research_service.py:328-331` — prepare/collect/finalize 3단계 호출로 재배치
- `backend/services/deep_research_service.py:265-290` — `_progress_cb` 에 `source_fallback` 이벤트 추가
- `backend/services/deep_research_service.py:150` — `_source_count` 에 `markdown_path` 분기
- `backend/services/deep_research_service.py:343-358` — user_prompt 에 `sources/codex_research.md` 2번째 파일로 추가
- `backend/prompts/stock_synthesis_prompt.md:14,33,40,100` — `tavily.json` 언급을 조건부 Codex/Tavily 설명으로 교체
- `frontend/src/types/aiReport.ts:24` — `SourceName` 유니언 `tavily` → `codex_research`, `PhaseEvent` 에 `source_fallback` variant 추가
- `frontend/src/components/.../ProgressPanel` (grep 으로 위치 확정) — 라벨 맵에 `codex_research: "Codex 심층 리서치"`, fallback 배지

#### 테스트
- `backend/tests/test_deep_research_collector.py` — `test_collect_codex_success`, `test_collect_codex_timeout`, `test_collect_all_sources_codex_fallback_to_tavily`, `test_collect_all_sources_both_codex_and_tavily_fail`, `test_staging_writes_tavily_json_on_fallback`
- `backend/tests/test_deep_research_service.py` — SSE phase 시퀀스 (`source_fallback` 이벤트 포함), user_prompt 스냅샷
- 기존 `test_collect_tavily*` **유지** (fallback 경로 커버)

### 재사용 유틸리티
- `SourceResult` dataclass (`deep_research_collector.py:34-47`) — 그대로
- `_BLOCKED_ROOTS` (`deep_research_collector.py:857-864`) — Codex output_path 검증에 재사용
- `asyncio.wait_for` 타임아웃 래핑 (`_collect_one_source:633`) — Codex 슬롯에도 동일 적용

### 재사용 불가 (중복 구현 허용)
- subprocess 실행·정리 전체 스캐폴딩 (Claude CLI 는 stream-json generator, Codex 는 one-shot 파일 쓰기라 흐름 제어가 근본적으로 다름 — 일반화는 과설계)
- `_collect_codex` 본체 (Tavily/Naver 등과 다른 입력/출력 모양 — httpx 아닌 subprocess)
- `_wrap_tavily_as_codex_slot` fallback 래퍼

---

## 단계별 실행 순서 (점진적 검증)

**Step 1 — 어댑터 단독 구축 (기존 파이프라인 무손상)**
1. `backend/services/codex_cli_runner.py` 작성 (CodexResult dataclass + run_codex_research)
2. `backend/tests/test_codex_cli_runner.py` — fake bash wrapper 6가지 케이스 (success, timeout, empty_output, binary_missing, exit_error, cancelled)
3. `pytest backend/tests/test_codex_cli_runner.py` 전부 green

**Step 2 — Staging 리팩터링 (동작 불변)**
1. `create_staging_directory` → `prepare_staging_directory` + `finalize_staging_directory` 분리
2. `deep_research_service.py:328-331` 호출부 3단계로 재배치
3. 기존 `test_deep_research_collector.py` + `test_deep_research_service.py` 전부 green — 회귀 게이트

**Step 3 — Codex 슬롯 치환 (Tavily 는 dead 경로)**
1. `_collect_codex` 추가, `SOURCE_NAMES` 치환, `_collect_one_source` 시그니처 확장
2. `_DEFAULT_TIMEOUTS["codex_research"] = 180.0` 추가
3. `test_collect_codex_success`, `test_collect_codex_timeout` 통과

**Step 4 — Fallback 로직**
1. `collect_all_sources` 내부 `if not gathered["codex_research"].success: call tavily` 분기
2. `_wrap_tavily_as_codex_slot` 헬퍼
3. `test_collect_all_sources_codex_fallback_to_tavily` 통과

**Step 5 — 합성 프롬프트 + SSE 이벤트**
1. `stock_synthesis_prompt.md` 조건부 파일 설명
2. `deep_research_service.py` user_prompt + `source_fallback` 이벤트
3. `_source_count` 에 `markdown_path` 분기

**Step 6 — 프론트엔드**
1. `types/aiReport.ts` SourceName 교체, `source_fallback` 이벤트 variant
2. 라벨 맵 수정 (ProgressPanel 위치 `grep -r "tavily" frontend/src/components` 로 확정)
3. 타입 스냅샷/컴포넌트 테스트 갱신

**Step 7 — 실 Codex 스모크 & fallback 스모크**
1. (**선결 검증**) `codex exec --json --skip-git-repo-check "오늘 2026-04-23 삼성전자(005930) 종가. 웹 검색 후 URL 포함"` — JSONL 에 `web_search` tool 호출 이벤트 확인. 없으면 Risks 1번 참조.
2. 005930 (삼성전자) 1회 end-to-end: `/api/ai-report/005930?mode=deep` → `sources/codex_research.md` 생성 확인, SSE `codex_research` phase 이벤트 확인
3. Fallback 경로: `PATH=/tmp/empty:$PATH` 로 codex 일시 숨김 → Tavily json 생성 + `source_fallback` 이벤트 확인

---

## Risks & Open Questions

1. **Codex 웹 검색 기본 활성 여부** — 최우선 선결 검증. `codex exec --json` 의 JSONL 이벤트에 `web_search` tool 호출이 없다면 `~/.codex/config.toml` 에 Brave MCP 서버 등록하는 2차 계획 필요. **Step 7.1 을 구현 착수 전에 수행**.
2. **180초 현실성** — Codex 실측 후 조정 필요. 환경변수화 예약. 초기 P95 분석 필수.
3. **ChatGPT 쿼터 차감** — API 키 과금이 아니라 구독 한도 소진. `AI_REPORT_DEEP_DAILY_QUOTA=15` 상한은 유지되지만 1회 Codex 호출이 ChatGPT 의 몇 "credit" 인지 초기 모니터링 필요.
4. **Path safety** — Codex 가 `--output-last-message` 로 /tmp 외부에 파일 쓰는 일 없도록 `prepare_staging_directory()` 에서 `_BLOCKED_ROOTS` 검사 선수행.
5. **프롬프트 인젝션** — Codex 출력 md 에 악성 Markdown 가능. Claude 는 `--allowedTools Read,Grep,Glob` 제한 (`claude_cli_streamer.py:178`)이 이미 걸려 있어 실행 위험 없음. 단 md 렌더 UI 에서 외부 링크 클릭 경고 검토 필요.
6. **Tavily 환경변수** — `TAVILY_API_KEY` 유지. Codex 가 기본 경로가 됐다고 해서 `.env.example` 에서 제거 금지.

---

## Verification

End-to-end 검증:

```bash
# 1. 단독 스모크 (웹 검색 작동 여부) — 구현 착수 전 선결
codex exec --json --skip-git-repo-check \
  "오늘 2026-04-23 삼성전자(005930) 종가를 웹에서 검색해 URL과 함께 한국어로 알려줘"
# 기대: JSONL 이벤트 중 web_search 호출 이벤트 존재, 마지막 assistant 메시지에 URL 포함

# 2. 단위 테스트
cd backend && source .venv/bin/activate
pytest tests/test_codex_cli_runner.py -v
pytest tests/test_deep_research_collector.py -v
pytest tests/test_deep_research_service.py -v

# 3. 통합 (primary path)
uvicorn backend.main:app --reload
curl -N "http://localhost:8000/api/ai-report/005930?mode=deep"
# 기대: SSE 이벤트 중 phase={"source":"codex_research", "status":"ok"} 수신,
#       /tmp/analysis_005930_*/sources/codex_research.md 생성 확인

# 4. 통합 (fallback path)
PATH=/tmp/empty:$PATH uvicorn backend.main:app --reload  # codex 바이너리 숨김
curl -N "http://localhost:8000/api/ai-report/005930?mode=deep"
# 기대: phase={"type":"source_fallback","from":"codex_research","to":"tavily"} 수신,
#       sources/tavily.json 생성, codex_research.md 부재
```

프론트엔드 UI 확인:
- `npm run dev` 로 dev server 기동
- 종목 상세 페이지에서 "AI 분석 (심층 모드)" 실행
- ProgressPanel 에 "Codex 심층 리서치" 라벨 표시, fallback 시 "Tavily (폴백)" 배지

TRUST 5 체크:
- **Tested**: 신규 6개 + 확장 5개 테스트, 기존 Tavily 테스트 유지 (커버리지 ≥ 85%)
- **Readable**: `_collect_codex`, `_wrap_tavily_as_codex_slot` 등 이름으로 의도 명시
- **Unified**: ruff check, 기존 Claude CLI runner 와 스타일 일관
- **Secured**: sandbox=read-only, Read-only 도구만, path safety 검사
- **Trackable**: 커밋은 SPEC-AI-REPORT-003 (신규 SPEC 발행) 또는 SPEC-AI-REPORT-002 v1.1 확장 — 팀에서 결정
