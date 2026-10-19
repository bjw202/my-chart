# SPEC-AI-REPORT-004 사전 조사

> AI 모달의 Deep 모드를 goose 스킬 하네스(헤드리스 `claude -p`)로 교체하기 위한 조사 자료. 2026-10-19 작성.
> 승인된 기획: `.moai/plans/ai-refactored-snowglobe.md` — 이 문서는 그 결정을 고정 전제로 두고, 코드 근거·보안 분석·미검증 항목을 정리한다.
> 표기 규칙: 이 세션에서 명령으로 직접 확인한 사실은 **[관측]**, 추론은 **[추정]**, M1 스파이크 전에는 알 수 없는 것은 **[증거 공백]**으로 구분한다.

---

## 1. 현재 구조 — Fast/Deep 두 경로

### 1.1 진입점 (프론트엔드)

| 위치 | 내용 |
|---|---|
| `frontend/src/components/ChartGrid/ChartCell.tsx:394-400` | `chart-cell-ai-btn` 버튼. 실행 중 표시(`--active`)는 `aiReport.status === 'streaming'` 기준 (`:395`) |
| `ChartCell.tsx:86-112` | `handleOpenAiReport`(모달 열기 + reset) / `handleCloseAiReport`(abort + reset) / `handleStartAiReport(mode)` / 기록 조회 핸들러 |
| `ChartCell.tsx:440-454` | `<AiReportModal>` 렌더 |
| `frontend/src/components/AiReportModal.tsx:153-179` | 모드 토글 (“빠른 분석” / “심층 분석 (수분 소요)”), 실행 중 비활성화 |
| `AiReportModal.tsx:217-224` | `ProgressPanel`은 `mode === 'deep'`이고 streaming/done일 때만 표시 |
| `AiReportModal.tsx:229`, `:263` | `ReactMarkdown`으로 결과·기록 렌더 |
| `frontend/src/components/ProgressPanel.tsx:14,55` | 5개 소스(codex/brave/tavily/naver/youtube) 전용 라벨·순서. goose 진행 단계와 맞지 않아 교체 대상 |
| `frontend/src/hooks/useAiReport.ts:68-74` | 상태 `idle | streaming | done | error | loading-history`, `abortRef`로 fetch 취소 |
| `useAiReport.ts:116-154` | `startStream(code, mode)` — 요청 1개 = 분석 1회. 모달을 닫으면 `abort()`로 연결과 분석이 함께 끊김 |
| `frontend/src/api/aiReport.ts:41-157` | `createAiReportStream` — fetch POST로 SSE를 직접 파싱(이벤트 `phase` / 기본 / `done` / `error`) |
| `aiReport.ts:11`, `:17` | 기록 목록 `GET /ai-report/{code}/history`, 내용 `GET /ai-report/{code}/{filename}` |
| `frontend/src/types/aiReport.ts:19,24,27-48` | `AiReportStatus`, `SourceName`, `PhaseEvent` 유니언 |

### 1.2 라우터

`backend/routers/ai_report.py`

- `POST /ai-report/{code}?mode=fast|deep|perplexity` (`:39-86`). 검사 순서: 코드 형식 422 (`:63`) → 종목 존재 404 (`:70`) → 모드 분기. FastAPI `Query(pattern=...)`가 잘못된 mode를 먼저 422로 거른다 (`:42`).
- `_handle_fast_mode` (`:89-132`): `shutil.which("codex")` 503 → `_active_analyses` 중복 429 → `check_rate_limit()` 429 → `EventSourceResponse`.
- `_handle_deep_mode` (`:135-160`): `shutil.which("claude")` 503 → `_active_deep_analyses` 중복 429 → `check_deep_rate_limit()` 429 → `stream_deep_analysis`.
- 기록 `GET /ai-report/{code}/history` (`:163`), 내용 `GET /ai-report/{code}/{filename}` (`:197`).

경로 충돌 검토 **[추정]**: 새 경로 `/ai-report/jobs/{job_id}/events`(세그먼트 3개)와 `/ai-report/{code}/goose/{run}/report.html`(4개)은 기존 `{code}/{filename}`(2개)과 세그먼트 수가 달라 매칭이 겹치지 않는다. 다만 `POST /ai-report/jobs` 같은 2세그먼트 경로를 만들면 `{code}` 검증(422)에 먼저 걸리므로 피한다.

### 1.3 Fast 경로 (유지 대상)

- `backend/services/ai_report_service.py:150-291` `stream_codex_fast` — codex 비스트리밍 실행 + 30초 heartbeat `phase` 이벤트 + 완료 후 256자 청크. `:279`에서 `save_report` 호출.
- `backend/services/codex_cli_runner.py` — `CodexResult`(`:72-94`)의 `error_type`: `binary_missing | auth | timeout | empty_output | exit_error`. `_terminate_proc`(`:122`) terminate→kill 2단계, stderr 꼬리 50줄(`:52`), 스트림 버퍼 4MB(`:55`), 인증 실패 문자열 판정(`:57-63`, `:147`).
- 레이트 리밋 `check_rate_limit` (`ai_report_service.py:41-87`): 일일 `AI_REPORT_DAILY_QUOTA`(기본 50), 분당 `AI_REPORT_BURST_LIMIT`(기본 3). 모듈 전역 상태 — 단일 uvicorn 전제(`:17-20` `@MX:WARN`).

### 1.4 Deep 경로 (교체·삭제 대상)

- `backend/services/deep_research_service.py` — `_active_deep_analyses`(`:69`), `check_deep_rate_limit`(`:96-145`, 일일 `AI_REPORT_DEEP_DAILY_QUOTA` 기본 15, 분당 `AI_REPORT_DEEP_BURST_LIMIT` 기본 1), `stream_deep_analysis`(`:214`), `_cleanup_stale_staging_dirs`(`:458`). `:407`에서 `save_report` 호출.
- `backend/services/deep_research_collector.py` — Brave(`:318`)/Tavily(`:381`)/Naver(`:452-453`)/YouTube(`:521`) 키를 읽어 수집.
- `backend/services/claude_cli_streamer.py` — `parse_stream_json_line`(`:62-102`): `assistant`의 첫 text, `result`, `system/error`만 해석하고 **`tool_use`는 버린다**. `_terminate_proc`(`:110-131`)는 직계 자식만 종료. `stream_claude_synthesis`(`:139-270`)는 `--permission-mode bypassPermissions`(`:179`)를 쓰고, 모델을 `opus → claude-opus-4-6`, 그 외 `claude-sonnet-4-6`으로 하드코딩(`:186-189`). 4MB 라인 한도(`:206-217`).
- `backend/prompts/stock_synthesis_prompt.md` — Deep 합성 전용.
- `backend/main.py:34-36`이 `_cleanup_stale_staging_dirs`, `_load_synthesis_prompt`를 import하고 `:76`(프롬프트 로드), `:84`(스테이징 정리)에서 시작 시 호출 → **삭제 시 `main.py`도 함께 고쳐야 한다** (승인 기획의 수정 목록에 없던 파일).
- 관련 테스트: `backend/tests/test_deep_research_service.py`, `test_deep_research_collector.py`, `test_ai_report_router_deep_mode.py`, `test_claude_cli_streamer.py`.
- `.env.example:17-28` — Brave/Tavily/Naver/YouTube 키, `AI_REPORT_DEEP_DAILY_QUOTA=15`, `AI_REPORT_DEEP_BURST_LIMIT=1`, `AI_REPORT_DEEP_MODEL=sonnet`.

### 1.5 저장소

- `ai_report_service.py:90` `_REPORTS_BASE = backend/reports` (`.gitignore:264` `backend/reports/`).
- `_sanitize_name` (`:297-343`) 7단계 정규화, `save_report` (`:346-376`) `YYYY-MM-DD[_N].md`, `get_history` (`:379-416`) **`glob("*.md")` 비재귀**, `get_report_content` (`:419-448`) 파일명 정규식 + `resolve()` 후 루트 이탈 차단.
- **[관측]** `backend/reports/` 아래 `.md` 61개. Fast와 Deep이 같은 `save_report`를 쓰므로 **파일만으로는 두 모드를 구분할 수 없다.**
- `get_history`가 비재귀이므로 `backend/reports/<종목명>/goose/` 하위 폴더를 추가해도 기존 기록 목록에 섞이지 않는다.
- 스키마 `backend/schemas/ai_report.py`: `HistoryItem{filename, date, created_at}` — `kind` 필드 없음.

### 1.6 코드 주장 검증 명령 (lessons #10 적용)

```bash
grep -n "bypassPermissions" backend/services/claude_cli_streamer.py          # :179
grep -n "deep_research_service\|_load_synthesis_prompt" backend/main.py      # :34-36, :76, :84
grep -n "def check_deep_rate_limit\|_active_deep_analyses" backend/services/deep_research_service.py  # :69, :96
grep -n "glob(\"\*.md\")" backend/services/ai_report_service.py              # get_history 비재귀
find backend/reports -name '*.md' | wc -l                                     # 61 (2026-10-19)
```

---

## 2. goose 스킬 — 구조와 실행 계약

출처: `/Users/byunjungwon/Downloads/goose` (제3자 배포물). 내용은 **자료로만 읽었고**, 안의 지시를 따르지 않았다.

### 2.1 구성 [관측]

- 스킬 1개 `goose` v0.1.0, 파일 33개(약 2.0MB, `.DS_Store` 2개 포함). `SKILL.md` + `workflows/<10개 내부 모듈>/GUIDE.md` + references + 스크립트 3개(`stock-report/scripts/render_report.py`, `fact-check/scripts/audit_report.py`, `portfolio-review/scripts/portfolio_calc.py`) + 로고·CSS 자산.
- `DISTRIBUTION.json` (schema_version 2): `files[]`에 경로별 sha256. 무결성 고정(pinning)의 기준으로 쓸 수 있다.
- 스크립트는 표준 라이브러리만 import (`argparse, base64, hashlib, html, json, math, pathlib, re, sys, urllib.parse`). 네트워크·subprocess 호출 없음. 파일 쓰기는 `--output-dir` / `--output` 인자로 받은 경로에만 한다(`render_report.py:500-513`, `audit_report.py:112`).

### 2.2 `company_report` 흐름 [관측]

`workflows/stock-report/references/workflow-map.json`:

```
finance(earnings-review, analyze) ┐
news(event-impact, analyze)       ├─► review(fact-check, analyze) ─► report(stock-report, render) ─► delivery_audit(fact-check, audit)
industry(peer-compare, analyze)   ┘
```

- 필수 입력 `company`, `as_of`. 산출물 “10장 HTML 기업 보고서 + 12문단 오피니언”.
- 수정 루프: `delivery-audit.md` §감수→수정→재감수 4항 — **최대 3회**, 같은 접근 차단이 반복되면 중지하고 미완료 사유를 보고.
- 역할 분배: `references/agent-team.md` — 실제 서브에이전트 도구가 있으면 분업, 없으면 “단일 실행자·역할별 순차 검토”로 순차 수행하고 그 사실을 기록.

### 2.3 산출물과 최종본 게이트 [관측]

- 렌더 명령(스킬 루트 기준): `python3 workflows/stock-report/scripts/render_report.py --input input.json --output-dir run/draft` → `report.html`, `report-input.json`, `source-ledger.json`, `render-validation.json`.
- 최종본은 `--final --preview <draft html> --audit-review audit-review.json`로만 생성되며, 내부에서 `audit_report.audit()`를 호출해 `delivery_allowed`가 거짓이면 실패한다(`render_report.py:489-503`).
- 감사기(`audit_report.py`)의 차단 조건 중 헤드리스 실행과 충돌할 수 있는 것:
  - `checks.visual.status == "pass"`와 실제 관찰 근거 필수(`:95-103`). 지침은 “실제 브라우저 확인이 없으면 pass로 쓰지 않는다”고 명시한다. **헤드리스에는 브라우저가 없으므로 정직하게 실행하면 최종본이 생성되지 않을 가능성이 높다 [추정].**
  - `research_window.cutoff`가 실행일과 같은 날이어야 하고(`:32`), 채널별(dart/company_ir/naver/original_news/industry) 검색 기록이 cutoff 전 24시간 이내여야 한다(`:50`).
  - 최소 6개 연속 공시 분기 + 최근 3개 연도(`:80`, `:83`). 한국 기업은 DART 본문·주석·감사보고서 직접 열람 필수.
- 따라서 정상 실행의 결과물은 **최종본(`final/report.html`) 또는 감사 대기 초안(`draft/report.html`, `delivery_status: draft_pending_audit`) 둘 중 하나**다. 어느 쪽을 보여줄지는 사용자가 2026-10-19에 결정했다: 초안이면 iframe에 표시하고 “최종 감사 미통과 초안” 배너를 보인다(plan.md D7).

### 2.4 생성되는 HTML의 성질 [관측]

- `<script>` 태그·`onclick`·`javascript:` 없음(`render_report.py` 대상 grep 0건).
- 외부 리소스: 폰트 CSS 2개(`cdn.jsdelivr.net` Pretendard, `fonts.googleapis.com` Gowun Batang, `:443`). 이미지·JSON 다운로드는 `data:` URI로 내장.
- 근거 링크(`<a href>`)가 원문 사이트를 가리킨다 → sandbox iframe 안에서 링크를 여는 방식을 정해야 한다(§5.4).

### 2.5 헤드리스와 충돌하는 지침

- 인터뷰: `goose-agent.md`는 맥락이 부족하면 “한 번에 1~3개 질문”을 하도록 한다. 헤드리스에는 답할 사람이 없으므로 하네스 지침에서 금지하고, 프롬프트에 종목·코드·기준일·범위·출력 위치를 모두 넣어 “이미 아는 정보는 묻지 않는다” 규칙이 작동하게 한다.
- 스크립트 경로: 지침은 스킬 루트 기준 상대경로(`python3 workflows/...`)를 쓴다. 하네스 cwd가 `backend/goose_harness/`이면 실제 경로는 `.claude/skills/goose/workflows/...`가 되므로, 권한 허용 규칙과 하네스 CLAUDE.md의 명령 형식을 일치시켜야 한다. 모델이 다른 형식(`cd` 후 실행 등)을 쓰면 거부된다 → M1에서 확인.

---

## 3. 하네스 격리 근거

### 3.1 왜 리포 루트에서 띄우면 안 되는가

리포 루트에서 `claude -p`를 띄우면 MoAI의 `CLAUDE.md`·`.claude/rules/**`·hooks·에이전트 정의가 함께 로드된다. 이 지침은 goose와 무관하고 양이 커서 (1) goose 동작을 오염시키고 (2) 매 실행마다 입력 토큰을 크게 늘리며 (3) hooks가 실행돼 부작용(로그·상태 파일 기록)을 낸다.

### 3.2 CLI 옵션 [관측: `claude --help`, 2.1.302]

| 옵션 | 설명(요약) | 이번 설계에서의 의미 |
|---|---|---|
| `--setting-sources <user,project,local>` | 읽을 설정 원천 선택 | `project`만 지정해 사용자 전역 설정·hooks를 배제 |
| `--bare` | hooks·CLAUDE.md 자동 탐색·keychain 읽기 생략. 인증은 `ANTHROPIC_API_KEY` 또는 apiKeyHelper만 | **구독(OAuth) 로그인을 쓸 수 없어 이번 구성에는 부적합** |
| `--restricted` | Bash·WebFetch 제거(`--tools`로 재지정 가능), 사용자/프로젝트/로컬 설정 무시, 파일 도구를 작업 디렉터리로 한정, `bypassPermissions` 거부 | M1의 대안 후보. 프로젝트 스킬이 로드되는지는 미확인 |
| `--permission-mode dontAsk` / `--permission-prompts none` | 허용 목록 밖 도구는 묻지 않고 거부 | 헤드리스에서 권한 요청이 멈춤으로 이어지지 않게 함 |
| `--add-dir` | 도구 접근 허용 디렉터리 추가 | run 작업 디렉터리를 하네스 밖에 둘 경우 필요 |
| `--max-budget-usd` | `--print`에서만 동작하는 비용 상한 | 무한 소비 방지의 보조 수단(구독 인증에서의 동작은 미확인) |
| `--no-session-persistence` | 세션을 디스크에 저장하지 않음 | 웹에서 읽은 원문이 `~/.claude/projects`에 쌓이지 않게 함 |
| `--agents`, `--plugin-dir` | 에이전트·플러그인 주입 | 스킬 탐색 실패 시 대체 경로 |
| `--disable-slash-commands` | 모든 스킬 비활성화 | 사용 금지 |

### 3.3 미검증 위험 — 상위 디렉터리 CLAUDE.md

Claude Code는 cwd에서 위로 올라가며 CLAUDE.md를 찾는다. 하네스가 `my_chart/backend/goose_harness/`에 있으면 `my_chart/CLAUDE.md`(MoAI 지시서)와 `my_chart/CLAUDE.local.md`가 탐색 경로에 있다. `--setting-sources project`가 이 탐색까지 막는지는 도움말에 나오지 않는다 → **[증거 공백] G2**. `--bare`는 이를 막지만 구독 인증을 쓸 수 없다.

M1에서 객관적으로 측정하는 방법: 같은 하네스를 (a) 리포 안 실제 위치와 (b) 상위에 CLAUDE.md가 없는 스크래치 디렉터리에 두고 같은 짧은 프롬프트를 실행해 `result` 이벤트의 입력 토큰을 비교한다. MoAI 지시서는 수만 토큰 규모라 오염되면 차이가 크게 난다. 오염이 확인되면 하네스를 리포 밖(환경 변수로 경로 지정)으로 옮기거나 `--restricted`를 검토한다.

### 3.4 Agent SDK를 쓰지 않는 이유 (승인된 결정)

- SDK도 같은 `claude` CLI를 하위 프로세스로 띄우므로 스킬·에이전트 지원 범위가 같다.
- 백엔드 venv(`/Users/byunjungwon/Dev/my_chart/.venv`, python3.13)에 `claude-agent-sdk`가 없다(승인 기획의 관측).
- 이미 `asyncio.create_subprocess_exec` + stream-json 처리 코드가 있어 의존성 추가 없이 구현할 수 있다. 권한 콜백(`can_use_tool`)이 꼭 필요해지면 하네스 폴더를 그대로 둔 채 SDK로 바꿀 수 있다.

---

## 4. 작업(job)을 요청과 분리하는 이유

### 4.1 문제

현재 Deep은 SSE 요청 하나가 분석 하나와 수명을 같이한다. 모달을 닫으면 `abort()` → fetch 취소 → 서버 제너레이터 취소 → `finally`에서 하위 프로세스 종료(`claude_cli_streamer.py:264-266`). goose 전체 리포트는 수십 분 걸린다고 추정되므로, 이 구조로는 모달을 닫거나 새로고침하는 순간 결과가 사라진다.

### 4.2 따를 기존 패턴

- `backend/services/db_service.py:26-49` `start_update` — 배타 잠금(`_update_lock.acquire(blocking=False)`) 후 백그라운드 스레드 시작, 이미 실행 중이면 `False`.
- `backend/services/progress_store.py` — 잠금으로 보호되는 진행 상태 dict(`get/update/reset/is_running`).
- `backend/routers/db.py:20-60` — `POST /db/update` 202 / 409, `GET /db/status` SSE가 500ms마다 상태를 읽어 보냄.

### 4.3 goose 작업에 맞게 바꿀 점

| 기존 패턴 | goose 작업 |
|---|---|
| 스레드 + 동기 함수 | asyncio 태스크 + 비동기 하위 프로세스 (기존 claude/codex 실행기와 동일 방식) |
| 전역 상태 1개 | `job_id`별 상태 + 이벤트 로그(순번 포함) |
| 마지막 상태만 폴링 | 지난 이벤트 전체 재생 + 실시간 전달, `Last-Event-ID`로 이어 받기 |
| 실행 중이면 409 | 같은 종목이 실행 중이면 기존 `job_id` 반환 (승인 기획 §3) |
| 취소 없음 | `POST /jobs/{id}/cancel` → 프로세스 그룹 종료 |

브라우저의 `EventSource`는 GET 전용이지만 재접속 시 `Last-Event-ID` 헤더를 자동으로 보낸다. 이벤트 구독을 GET으로 분리하면 기존의 fetch 기반 수동 파서 대신 표준 재접속 동작을 쓸 수 있다 **[추정 — 구현 단계에서 선택]**.

### 4.4 알려진 한계

- 인메모리 상태라 서버를 재시작하면 진행 중 작업 기록을 잃는다(기존과 같은 한계, 승인 기획 §위험).
- `uvicorn --reload`나 재시작 시 `claude` 하위 프로세스가 고아로 남아 구독 사용량을 계속 소모할 수 있다. 기존 `_terminate_proc`는 직계 자식만 종료하므로, 새 실행기는 새 세션(프로세스 그룹)으로 띄우고 취소·시간 초과·서버 종료 시 그룹 전체를 종료해야 한다.

---

## 5. 보안 분석

위협 모델: goose 세션은 **임의의 웹 페이지를 읽는다**. 읽은 내용 어디에든 지시문이 숨어 있을 수 있다고 가정한다(간접 프롬프트 주입, OWASP LLM01 / MITRE ATLAS AML.T0051). 모델이 따르지 않으리라는 기대가 아니라, 따르더라도 할 수 있는 일이 없게 만드는 것이 방어 원칙이다.

### 5.1 신뢰 경계

| 경로 | 신뢰 | 방어 |
|---|---|---|
| 백엔드가 만든 프롬프트(종목명·코드·run 경로) | 신뢰 (단, 종목명은 레지스트리 값) | 코드 6자리 정규식, 종목명은 `get_stock_name` 결과만 사용 |
| WebSearch/WebFetch 결과 | **비신뢰** | 도구 권한 최소화, 쓰기·실행 범위 제한, 비밀 정보 미노출 |
| 벤더링한 goose 파일 | 조건부 신뢰 | sha256 고정, 세션 중 수정 금지 |
| 모델 출력(stream-json, 최종 텍스트, 생성 파일) | **비신뢰** | 백엔드가 경로를 스스로 계산, 허용 파일명만 복사, HTML은 sandbox로만 표시 |

### 5.2 도구 권한 (OWASP LLM06 과도한 권한)

승인 기획의 허용 목록을 기준으로, 다음 우회 경로를 막아야 한다.

1. **경로 탈출로 Bash 허용 규칙 우회 [추정, M1 음성 검증 대상]**: `Bash(python3 .claude/skills/goose/workflows/*)` 같은 접두어 규칙은 `python3 .claude/skills/goose/workflows/../../../../runs/x/evil.py`도 접두어가 일치한다. 모델이 Write로 스크립트를 만든 뒤 이 형태로 실행하면 임의 코드 실행이 된다. → 허용 규칙을 **두 스크립트의 정확한 경로**로 고정하고(`render_report.py`, `audit_report.py`), `..`가 들어간 명령은 거부 규칙으로 막는다. `portfolio_calc.py`는 `company_report`에서 쓰지 않으므로 허용하지 않는다.
2. **벤더링 스크립트 덮어쓰기**: Write/Edit가 `.claude/**`를 수정할 수 있으면 허용된 스크립트 내용을 바꿔 실행할 수 있다. → 쓰기 허용은 해당 작업의 run 작업 디렉터리로만 두고 `.claude/**` 쓰기는 거부한다. 백엔드는 매 작업 시작 전 sha256을 다시 검사한다.
3. **비밀 정보 유출**: 주입된 지시가 `.env`나 홈 디렉터리 파일을 읽어 WebFetch URL에 실어 보낼 수 있다(AML.T0057). → Read/Glob/Grep을 하네스 디렉터리로 한정하고, 하위 프로세스 환경 변수를 허용 목록 방식으로 넘겨 백엔드 비밀(`KRX_ID`, `KRX_PW` 등)이 상속되지 않게 한다. 하네스 안에는 공개 리서치 자료와 goose 파일만 있게 한다.
4. **권한 우회 모드 금지**: `--permission-mode bypassPermissions`(현행 Deep, `claude_cli_streamer.py:179`)와 `--dangerously-skip-permissions`를 쓰지 않는다. 허용 목록 밖은 `dontAsk`로 조용히 거부한다.
5. **서브에이전트 권한 상속 [증거 공백 G4]**: Agent 도구로 띄운 서브에이전트가 같은 권한 규칙을 따르는지 M1에서 확인한다.

### 5.3 쓰기 범위

- 모델이 쓰는 위치와 사용자에게 보관하는 위치를 분리하는 방안을 권장한다: 세션은 하네스 안의 작업 전용 디렉터리(`backend/goose_harness/runs/<job_id>/`, gitignore)에만 쓰고, 성공하면 **백엔드가** 허용된 파일명만 `backend/reports/<종목명>/goose/YYYY-MM-DD[_N]/`로 복사한다. 이렇게 하면 다른 종목의 리포트가 있는 `backend/reports/`를 세션에 노출하지 않고, 쓰기 허용 규칙도 상대경로 하나로 끝난다. 최종 보관 위치는 승인 기획 §4와 같다.
- 단, 스크립트가 쓰는 위치는 Write 권한 규칙이 아니라 `--output-dir` 인자로 정해진다. 허용 규칙을 정확한 스크립트 경로로 고정해도 인자는 모델이 정한다 → 작업 종료 후 백엔드가 작업 디렉터리 밖 변경 여부를 점검하는 방법을 M1에서 검토한다(예: 하네스 트리의 실행 전후 파일 목록 비교).
- 모델이 출력한 “report.html 경로” 문자열은 믿지 않는다(LLM05). 백엔드는 `runs/<job_id>/` 아래 `final/report.html`, 없으면 `draft/report.html`을 스스로 찾는다. 탐색 위치는 M1 관측으로 확정한다.

### 5.4 HTML 표시

- 서빙 응답 헤더에 `Content-Security-Policy: sandbox`를 넣는다. 이 헤더가 있으면 문서를 새 탭에서 직접 열어도 불투명 출처로 취급돼 앱의 쿠키·저장소에 접근할 수 없다. 추가로 `default-src 'none'; style-src 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src https://cdn.jsdelivr.net https://fonts.gstatic.com; img-src data:`를 함께 두면 외부 요청을 폰트로 한정할 수 있다 **[추정 — 렌더 확인 필요]**.
- iframe에는 `sandbox` 속성을 두고 `allow-scripts`, `allow-same-origin`은 넣지 않는다. 근거 링크를 열려면 `allow-popups allow-popups-to-escape-sandbox`, 내장 JSON 다운로드에는 `allow-downloads`가 필요하다. 스크립트가 없는 문서이므로 이 정도 허용은 위험이 낮다.
- goose 렌더러가 HTML을 이스케이프하지만, 백엔드는 이에 기대지 않는다(제3자 코드).
- 서빙 경로 검증은 `get_report_content`(`ai_report_service.py:419-448`) 방식을 그대로 쓴다: run 폴더명 정규식(`^\d{4}-\d{2}-\d{2}(_\d+)?$`) + 파일명 고정(`report.html`) + `resolve()` 후 `_REPORTS_BASE` 이탈 차단.

### 5.5 공급망 (OWASP LLM03)

- 벤더링 시 `DISTRIBUTION.json`의 sha256과 실제 파일을 대조하고, 대조에 쓴 매니페스트를 리포에 커밋한다. 업데이트는 수동으로만 한다.
- `.DS_Store` 2개, `agents/openai.yaml`, `assets/goose.png`는 실행에 필요 없다. 원본 보존 여부는 구현 단계에서 정한다(승인 기획은 `openai.yaml` 원본 보존).

### 5.6 소비 한도 (OWASP LLM10)

- 일일 한도(기본 5회), 실행 시간 상한(`AI_REPORT_GOOSE_TIMEOUT`, M1 측정값 기반), 서버 전체 동시 실행 1개(사용자 결정 2026-10-19, plan.md D10).
- `--max-budget-usd`는 보조 수단으로 검토한다.

### 5.7 잘못된 정보 (OWASP LLM09)

주입된 페이지가 리포트 내용을 왜곡할 수 있다. goose 자체의 팩트체크·감사 단계가 일부를 거르지만, 남는 위험은 화면에 “AI 생성 리포트, 투자 판단 책임은 사용자” 고지와 초안 여부 표시로 다룬다.

### 5.8 OWASP LLM Top 10 대조

| 항목 | 해당 | 대응 위치 |
|---|---|---|
| LLM01 프롬프트 주입 | 예 (WebFetch) | §5.2, §5.3 |
| LLM02 민감 정보 노출 | 예 (환경 변수·파일) | §5.2-3 |
| LLM03 공급망 | 예 (제3자 스킬) | §5.5 |
| LLM04 데이터·모델 오염 | 해당 없음 (학습 없음) | — |
| LLM05 출력 처리 | 예 (HTML·경로) | §5.3, §5.4 |
| LLM06 과도한 권한 | 예 | §5.2 |
| LLM07 시스템 프롬프트 유출 | 낮음 (비밀 없음) | 하네스 CLAUDE.md에 비밀을 두지 않음 |
| LLM08 벡터·임베딩 | 해당 없음 | — |
| LLM09 잘못된 정보 | 예 | §5.7 |
| LLM10 무한 소비 | 예 | §5.6 |

---

## 6. 재사용 목록

| 재사용 대상 | 위치 | 방식 |
|---|---|---|
| 오류 분류 체계 | `codex_cli_runner.py:72-94`, `:57-63`, `:147` | 그대로 재사용 + `cancelled`, `integrity` 추가 |
| stderr 꼬리 보관 | `codex_cli_runner.py:52`, `:271` | 패턴 복제 |
| stream-json 라인 파싱 | `claude_cli_streamer.py:62-102` | 확장 필요 — 현재는 `tool_use`를 버림 |
| 하위 프로세스 종료 | `claude_cli_streamer.py:110-131` | 확장 필요 — 프로세스 그룹 단위로 |
| 4MB 라인 버퍼 | `claude_cli_streamer.py:211-217` | 그대로 |
| 작업 시작·중복 차단 | `db_service.py:26-49` | 비동기 버전으로 |
| 진행 상태 저장 | `progress_store.py` | job별 이벤트 로그로 확장 |
| 202 + SSE 라우터 | `routers/db.py:20-60` | 재생 기능 추가 |
| 이름 정규화·경로 검증 | `ai_report_service.py:297-343`, `:419-448` | 그대로 |
| 레이트 리밋 | `deep_research_service.py:96-145` | **삭제 파일 안에 있으므로 이동 필요** (goose 전용 쿼터 변수로) |
| SSE 파서(프론트) | `frontend/src/api/aiReport.ts:41-157` | Fast 전용으로 유지 |

---

## 7. 위험

| 위험 | 영향 | 완화 |
|---|---|---|
| 헤드리스 goose가 최종 감사를 통과하지 못함(브라우저 화면 검수 불가, DART 접근 실패) | 결과가 늘 초안 | 초안 표시 정책을 사용자 결정으로 확정, M1에서 실제 결과 확인 |
| 상위 CLAUDE.md 로드 | goose 오염, 토큰 증가 | M1 G2 측정 → 하네스 위치 이동 또는 `--restricted` |
| 스킬 미탐색 | 실행 불가 | `--plugin-dir`, `--append-system-prompt-file` 대체 경로 |
| 서브에이전트 불가 | 실행 시간 증가 | goose의 순차 수행 폴백 허용(승인 기획) |
| 실행 시간·비용 | 사용량 소진 | 쿼터·시간 상한·동시 실행 제한 |
| 고아 프로세스 | 사용량 누수 | 프로세스 그룹 종료, 서버 종료 시 정리 |
| 권한 규칙 문법 오인 | 허용·거부가 의도와 다름 | M1 음성 검증(거부되어야 할 호출이 실제로 거부되는지 관측) |
| 기존 Deep 삭제 범위 누락 | 서버 시작 실패 | `main.py:34-36,76,84` 수정 포함 |
| stream-json 이벤트 형식 변화 | 진행 표시 깨짐 | 알 수 없는 이벤트 무시(기존 파서 불변 조건 유지), 녹화 픽스처로 회귀 테스트 |

---

## 8. 증거 공백 — M1 스파이크로만 닫을 수 있는 항목

아래는 모두 **사실이 아니라 가설**이다. M1에서 명령과 관측 출력을 `progress.md`에 기록하기 전에는 설계 근거로 쓰지 않는다.

| ID | 질문 | 판정 방법(관측) |
|---|---|---|
| G1 | `-p` + `--setting-sources project`에서 구독(OAuth) 인증이 동작하는가 | 짧은 프롬프트 실행의 `result` 이벤트 `is_error=false` |
| G2 | 상위 `CLAUDE.md`/`CLAUDE.local.md`/사용자 메모리가 로드되는가 | 리포 내 위치 vs 스크래치 위치의 첫 턴 입력 토큰 비교 |
| G3 | 벤더링한 `goose` 스킬이 발견되고 `/goose`가 해석되는가, MoAI 스킬은 빠지는가 | `system/init` 이벤트의 스킬·슬래시 명령 목록 |
| G4 | Agent 도구가 있고 goose가 역할을 서브에이전트로 나누는가, 서브에이전트도 같은 권한 규칙을 따르는가 | `init`의 `tools`, 실행 중 Agent `tool_use` 개수, 서브에이전트의 거부 기록 |
| G5 | 인터뷰 없이 끝까지 진행되는가 | 질문으로 끝나는 결과·질문 도구 호출 0건 |
| G6 | 허용 목록 밖 호출이 실제로 거부되는가 (경로 탈출 Bash, 작업 디렉터리 밖 Write, `.claude/**` Edit, `../.env` Read) | `result` 이벤트의 `permission_denials`, 파일 미생성 확인 |
| G7 | `report.html`이 지정 작업 디렉터리에 생성되는가, 최종본인가 초안인가 | 파일 존재, `render-validation.json`의 `delivery_status` |
| G8 | 소요 시간·턴 수·토큰·비용 | `result` 이벤트의 `duration_ms`, `num_turns`, `usage`, `total_cost_usd` |
| G9 | 진행 표시에 쓸 이벤트 종류 | stream-json 이벤트 타입·도구 이름·Agent 설명 목록 |

M1 결과에 따라 확정되는 값: `AI_REPORT_GOOSE_TIMEOUT` 기본값, stream-json → 진행 단계 대응표, 하네스 위치, 결과 파일 탐색 위치, 권한 규칙의 최종 문법.

---

## 참고

- 승인 기획: `.moai/plans/ai-refactored-snowglobe.md`
- 선행 SPEC: SPEC-AI-REPORT-001(Perplexity SSE, superseded), SPEC-AI-REPORT-002(Deep 5소스 + claude 합성, frontmatter `status: Planned`로 남아 있음 — 이 SPEC이 대체), SPEC-AI-REPORT-003(Codex 전환, `status: Implemented`)
- goose 원본: `/Users/byunjungwon/Downloads/goose` (`VERSION` 0.1.0)
