---
id: SPEC-AI-REPORT-004
title: "AI 모달 Deep 모드를 goose 스킬 하네스(헤드리스 claude -p)로 교체"
version: "0.4.2"
status: in-progress
created: 2026-10-19
updated: 2026-10-20
author: manager-spec
priority: High
phase: "v0.5.3 target"
module: "backend/services"
lifecycle: spec-anchored
tags: "ai-report, goose, claude-cli, headless, job-queue, sse, security, sandbox"
---

# SPEC-AI-REPORT-004: AI 모달 Deep 모드를 goose 스킬 하네스로 교체

## HISTORY

| 버전 | 일자 | 작성 | 내용 |
|---|---|---|---|
| 0.1.0 | 2026-10-19 | manager-spec | research.md + plan.md 초안, `[NEEDS CLARIFICATION]` 4건 |
| 0.2.0 | 2026-10-19 | manager-spec | 사용자 결정 4건 반영(초안 표시·기존 markdown 기록·기본 모델 sonnet·서버 전체 동시 실행 1개), Tier L 산출물 일체 작성 |
| 0.3.0 | 2026-10-19 | manager-spec | plan-audit 1회차(FAIL 0.78) 반영: 시작 판정 순서를 요구사항 하나로 고정(R1-D1), 실행 중 작업 조회 엔드포인트와 셀 폴링 추가(R1-D2), 정리 범위에 `backend/prompts/__init__.py`·`README.md` 추가와 grep 대상 정정(R1-D3), 프로세스 종료와 종료 상태 기록 분리 + `cancelled`를 종료 상태로 통일(R1-D4), 가정 기록 위치를 `assumptions.md`로 지정(R1-D5), `final` 판정 규칙 단일화(R1-D6), 선택 결함 R1-D7~D14 반영. 요구사항을 1~23으로 다시 번호 매김 |
| 0.3.1 | 2026-10-19 | manager-spec | plan-audit 2회차(FAIL 0.90) 반영, 재번호 없음: REQ-008 판정 순서에 무결성 실패 단계 추가와 REQ-001 응답 202 명시(R2-N1), REQ-021을 같은 탭에서 시작한 작업으로 한정(R2-N2), AC-011 전제를 순차로(R2-N3), 중단된 작업의 초안 보관 규칙(REQ-014·019, 결정 T10, R2-N4), REQ-007 조건절을 REQ-014 선택 규칙에 맞춤, 선택 결함 R2-N5~N9 반영(감사 결함 ID에 회차 접두어 `R1-`/`R2-`를 붙여 결정 ID D1~D10과 구분) |
| 0.3.2 | 2026-10-19 | manager-spec | plan-audit 3회차(FAIL 0.91) 후 사용자가 부채 수용(PASS-WITH-DEBT)을 선택, 재감사 없이 수정, 재번호 없음: `HistoryItem`에 `interrupted` 추가(REQ-017, R3-M1), 중단된 작업은 선택된 전달 상태를 그대로 유지하고 중단 안내는 상태와 상관없이 표시(REQ-014·019, 사용자 결정 R3-M2), 서버 종료 시 보관을 best-effort로 명시(R3-M3), design §4.1·plan T1 문구 정정(R3-M4·M5) |
| 0.4.0 | 2026-10-19 | manager-spec | run 단계 M1 스파이크(조건부 GO) 관측 반영, 재번호 없음(REQ 23·AC 25 유지): 하네스를 리포 밖 `~/.goose-harness`로 옮기고 리포에는 `.claude`·`CLAUDE.md` 이름이 없는 추적 원본만 두어 서버 시작 시 매니페스트 대조 후 설치(결정 T11, REQ-001·022), argv에 `--strict-mcp-config`·`--settings <하네스>/.claude/settings.json` 추가와 설정 키 `disableAllHooks`·`autoMemoryEnabled`·`env.PATH`(REQ-002), 읽기 전용 Bash 자동 허용 관측에 따라 하네스 밖 읽기 거부를 명시(REQ-003), 시간 상한 기본 900초(표본 1회), 진행 단계 대응표·산출물 위치·환경 변수 목록을 측정값으로 확정(design §9). plan-audit 4회차 결함 R4-1·R4-2·R4-3·R4-4·R4-5·R4-7·R4-8 수정 |
| 0.4.1 | 2026-10-19 | manager-spec | plan-audit 5회차(FAIL 0.83, 점수 하락 → 단일 수정) 반영, 재번호 없음(REQ 23·AC 25 유지): 서버 시작 원본 대조가 실패하면 실패를 기록하고 이후 모든 goose 작업을 `error`/`integrity`로 끝냄 — 기존 설치본이 매니페스트와 맞아도 마찬가지(사용자 결정 2026-10-19, 닫힌 실패, R5-1, REQ-001·008, AC-001 (2b)), 원본 쪽 목록 밖 파일 규칙과 제외 목록(`goose-manifest.json`, `.DS_Store`)을 요구사항으로 올림(R5-2, AC-001 (1)(2c)), 하네스 밖 읽기 전용 Bash 탐침을 `cat`·`head`·`grep`·`~`·`$HOME`·허용 스크립트 뒤 복합 명령으로 넓힘(R5-3, REQ-003, AC-003 (6a)~(6f)), M1 해시 비교를 "오탐 없음 관측"으로 정정(R5-4). 선택 결함 R5-5·R5-7·R5-9 반영, R5-6·R5-8·R5-10 보류. 감사 보고서의 결함 번호 D1~D10을 결정 ID와 구분하려고 `R5-1`~`R5-10`으로 적는다 |
| 0.4.2 | 2026-10-20 | manager-spec | run 단계 M3 차단 보고(B2) 반영, 재번호 없음(REQ 23·AC 25 유지): 사용자 전역 `~/.claude/CLAUDE.md`가 하네스 세션에 로드되는 관측에 따라 하네스 설정 키에 `claudeMdExcludes: ["**/.claude/CLAUDE.md"]`를 추가(사용자 결정 2026-10-20, REQ-002, AC-002, design §2.2·§9.1). 근거: M3 탐침 4회 — 설정 키는 전역 지침만 빼고 하네스 `CLAUDE.md`는 남김, 인증 유지(`progress.md §E.2 ### M3 실행기 goose_runner` E4). 설치본 경로 재탐침은 M4 진입 확인 항목 |

관계: 이 SPEC은 **SPEC-AI-REPORT-002**(Deep 5소스 수집 + claude 합성)를 대체한다(supersedes). 002 문서 자체는 수정하지 않으며, 상태 정리는 sync 단계에서 한다. SPEC-AI-REPORT-003(Fast/Codex)은 유지된다.

---

## 1. 개요

차트 셀 AI 모달의 Deep 모드를 제3자 스킬 goose(“모두의 주식” v0.1.0)의 `company_report` 전체 리포트로 바꾼다. 실행은 전용 하네스 폴더에서 띄운 헤드리스 `claude -p`가 맡는다. 수십 분 걸리는 작업은 HTTP 요청과 분리된 작업(job)으로 돌고, 사용자는 모달을 닫았다 열어도 진행을 이어 본다. 결과는 goose가 만든 단일 HTML이며 sandbox iframe으로만 표시한다. Fast(codex) 모드는 그대로 둔다.

배경과 근거: `research.md`. 구조와 보안 경계: `design.md`. 구현 순서와 결정 기록: `plan.md`.

## 2. 확정 결정

| ID | 결정 | 출처 |
|---|---|---|
| D1 | 범위는 goose `company_report` 전체 리포트 하나. 유형 선택 UI 없음 | 승인 기획 |
| D2 | 모달의 Deep 자리를 “Goose”가 대체. Fast 유지 | 승인 기획 |
| D3 | 하네스 폴더 + 헤드리스 `claude -p`, `--setting-sources project`, `bypassPermissions` 금지, Agent SDK 미사용 | 승인 기획 |
| D4 | 요청과 분리된 작업, SSE 재생·재접속, 취소, 인메모리 상태(단일 uvicorn) | 승인 기획 |
| D5 | goose `report.html`을 CSP `sandbox`로 서빙, sandbox iframe 표시, 기록 탭에 goose 실행 목록 | 승인 기획 |
| D6 | 기존 Deep 파이프라인과 Brave/Tavily/Naver/YouTube 키 의존 삭제 | 승인 기획 |
| D7 | goose가 초안(최종 감사 미통과)으로 끝나면 초안을 iframe에 표시하고 “최종 감사 미통과 초안” 배너를 보인다. 기록에는 전달 상태 `draft` | 사용자 결정 2026-10-19 |
| D8 | 기존 markdown 리포트는 기록에 `kind: "markdown"`으로 계속 표시하고 `kind: "goose"` 항목과 함께 나열 | 사용자 결정 2026-10-19 |
| D9 | `AI_REPORT_GOOSE_MODEL` 기본값 `sonnet` | 사용자 결정 2026-10-19 |
| D10 | goose 작업은 서버 전체에서 동시에 1개. 다른 종목 시작 요청은 429, 같은 종목은 기존 `job_id` | 사용자 결정 2026-10-19 |

기술 결정 T1~T11(감사·M1 반영)은 `plan.md §2.3`에 기록한다. D3의 “하네스 폴더”는 M1 이후 리포 밖 설치본을 뜻한다(T11).

## 3. 변경 범위 [DELTA]

| 표기 | 대상 | 내용 |
|---|---|---|
| [NEW] | `backend/goose_harness_src/` | 하네스 추적 원본(작업 디렉터리로 쓰지 않음). 벤더링 스킬, 권한·설정 파일, 헤드리스 규칙, 무결성 매니페스트. `.claude`·`CLAUDE.md`라는 이름을 쓰지 않는다(T11) |
| [NEW] | `~/.goose-harness/` (리포 밖, `AI_REPORT_GOOSE_HARNESS_DIR`) | 서버 시작 시 설치되는 실행용 하네스(`CLAUDE.md`, `.claude/settings.json`, `.claude/skills/goose/`)와 작업 디렉터리 `runs/` |
| [NEW] | `backend/services/goose_runner.py` | `claude -p` 실행, 프로세스 그룹 관리, stream-json → 진행 단계 |
| [NEW] | `backend/services/goose_job_service.py` | 하네스 설치·무결성 검사, 작업 상태·이벤트 로그·시작 판정·산출물 복사 |
| [MODIFY] | `backend/routers/ai_report.py` | `mode=deep`을 작업 시작으로, 이벤트·취소·실행 중 작업 조회·HTML 서빙 경로 추가 |
| [MODIFY] | `backend/services/ai_report_service.py` | 기록에 `kind`·전달 상태 포함 |
| [MODIFY] | `backend/schemas/ai_report.py` | `HistoryItem`에 `kind`, `delivery_status`, `run`, `interrupted`(기본 `false`) |
| [MODIFY] | `backend/main.py` | Deep 전용 import·시작 시 호출 제거(`:34-36`, `:76`, `:84`), 종료 시 작업 정리 |
| [MODIFY] | `backend/prompts/__init__.py`, `backend/prompts/README.md` | `stock_synthesis_prompt.md`·`_load_synthesis_prompt` 언급 제거(`__init__.py:9`, `README.md:11-12`) |
| [MODIFY] | `.env.example` | goose 변수 추가, 옛 키 제거 (작업 디렉터리가 리포 밖이라 `.gitignore` 변경 없음) |
| [REMOVE] | `backend/goose_harness/` (M1 임시 하네스, 미추적) | 리포 안에서 `.claude/skills`가 MoAI 세션에 발견되므로 M2에서 삭제(T11) |
| [MODIFY] | `frontend/src/components/AiReportModal.tsx`, `ProgressPanel.tsx`, `ChartGrid/ChartCell.tsx`, `hooks/useAiReport.ts`, `api/aiReport.ts`, `types/aiReport.ts` | Goose 라벨, 작업 구독, iframe, 초안 배너, 취소, 진행 단계, 셀 활성 표시 |
| [EXISTING] | `backend/services/codex_cli_runner.py`, `stream_codex_fast` | Fast 경로 — 변경 없음, 오류 분류 체계만 참조 |
| [EXISTING] | `ai_report_service._sanitize_name`, `get_report_content` | 경로 검증 방식 재사용 |
| [REMOVE] | `backend/services/deep_research_service.py`, `deep_research_collector.py`, `backend/prompts/stock_synthesis_prompt.md` | 기존 Deep 파이프라인 |
| [REMOVE] | `backend/tests/test_deep_research_service.py`, `test_deep_research_collector.py`, `test_ai_report_router_deep_mode.py`(Goose 라우터 테스트로 교체), `test_claude_cli_streamer.py`(재사용 부분 테스트로 축소) | Deep 전용 테스트 |
| [MODIFY/REMOVE] | `backend/services/claude_cli_streamer.py` | 재사용 부분(라인 파서·종료 함수)만 남기거나 실행기로 이동, `bypassPermissions`를 쓰는 `stream_claude_synthesis` 삭제 |

## 4. 요구사항 (GEARS)

### 4.1 하네스와 실행

**REQ-AIR4-001** — When the server starts, the job service shall verify the tracked harness source against the manifest committed in the repository and, only when every listed file matches and no unlisted source file exists (the manifest file `goose-manifest.json` itself and `.DS_Store` files are excluded from this check and are never installed), shall install it into the harness directory (`AI_REPORT_GOOSE_HARNESS_DIR`, default `~/.goose-harness`) by replacing the installed `CLAUDE.md` and `.claude/` directory and leaving `runs/` untouched; when the source verification fails, it shall not install and shall record a startup integrity failure that holds until the next server start. When a goose job is about to start and either a startup integrity failure is recorded (even if a previously installed harness matches the committed manifest) or the installed harness fails the integrity check against that committed manifest (a listed file is missing or its sha256 differs, or an unlisted file exists under the harness `.claude/` directory), the job service shall record the job as `error` with error kind `integrity`, shall not launch `claude`, shall not register the job as the running job, and shall not consume daily quota, and the router shall return 202 with that job's `job_id`.

**REQ-AIR4-002** — The goose runner shall launch `claude -p` with the harness directory as working directory, `--setting-sources project`, `--settings <harness directory>/.claude/settings.json`, `--strict-mcp-config`, `--output-format stream-json`, `--permission-mode dontAsk`, and `--model` set to `AI_REPORT_GOOSE_MODEL` (default `sonnet`), and shall not pass `bypassPermissions` or `--dangerously-skip-permissions`. The harness settings file shall set `disableAllHooks: true`, `autoMemoryEnabled: false`, `claudeMdExcludes` containing `**/.claude/CLAUDE.md`, and an `env.PATH` naming the system binary directories.

**REQ-AIR4-003** — The harness permission policy shall deny, without prompting, every tool call outside the allowlist: WebSearch, WebFetch, Read/Glob/Grep inside the harness, writes inside the job workspace only, Agent, Skill, and Bash limited to the exact script paths of `render_report.py` and `audit_report.py`; the policy shall also deny read-only Bash commands that read a path outside the harness directory, whether the path is written as an absolute path or with `~` or `$HOME`, and whether the command stands alone or is chained after an allowed command, because Claude Code auto-approves some read-only Bash commands in `dontAsk` mode.

**REQ-AIR4-004** — The goose runner shall pass the subprocess only allowlisted environment variables, so that backend secrets are not inherited.

**REQ-AIR4-005** — The headless goose session shall not ask the user questions; it shall proceed with the defaults stated in the prompt and harness instructions and shall write every assumption it made to `assumptions.md` in the job workspace (stating "가정 없음" when there are none).

**REQ-AIR4-006** — When a job exceeds `AI_REPORT_GOOSE_TIMEOUT`, is cancelled, or the server shuts down, the goose runner shall terminate the whole subprocess group (SIGTERM, then SIGKILL after a configurable grace period).

**REQ-AIR4-007** — When a job ends other than by exit 0 with a report selectable under REQ-AIR4-014, the job service shall set exactly one terminal state according to its cause: cancel request or server shutdown → state `cancelled` (no error kind); integrity mismatch → `error`/`integrity`; executable missing → `error`/`binary_missing`; authentication failure in stderr → `error`/`auth`; timeout → `error`/`timeout`; exit 0 with no report → `error`/`empty_output`; any other non-zero exit → `error`/`exit_error`.

### 4.2 작업 API

**REQ-AIR4-008** — When `POST /ai-report/{code}?mode=deep` is received, the router shall decide in this order and stop at the first match: invalid code format → 422; unknown stock → 404; `claude` executable missing → 503; a goose job for the same code is running → 200 with that `job_id`, consuming no quota; a goose job for a different code is running → 429 with error `goose_busy` naming the running stock; daily quota `AI_REPORT_GOOSE_DAILY_QUOTA` (default 5) exhausted → 429 with error `goose_rate_limit`; the integrity check of REQ-AIR4-001 fails (including a recorded startup integrity failure) → 202 with the `job_id` of a job recorded as `error`/`integrity`, consuming no quota and not registering it as running (REQ-AIR4-001); otherwise start a background job, consume one quota unit, and return 202 with a new `job_id`.

**REQ-AIR4-009** — When a client subscribes to `GET /ai-report/jobs/{job_id}/events`, the job service shall replay every past event in sequence order and then stream live events; when `Last-Event-ID` is supplied, it shall send only events after that id; for an unknown `job_id` it shall return 404.

**REQ-AIR4-010** — While a job is running, the job shall continue when every event subscriber disconnects.

**REQ-AIR4-011** — When `POST /ai-report/jobs/{job_id}/cancel` is received for a running job, the job service shall stop the job and emit a terminal `cancelled` event; for a finished job it shall return the current state unchanged; for an unknown `job_id` it shall return 404.

**REQ-AIR4-012** — When the runner observes a stream-json event listed in the progress mapping table, the job service shall emit the corresponding phase event; unknown events shall be ignored without raising.

**REQ-AIR4-013** — When `GET /ai-report/goose/active` is received, the router shall return the running goose job as `{job_id, code, stock_name, status}`, or `null` when no goose job is running.

### 4.3 저장과 서빙

**REQ-AIR4-014** — When a job's session ends, the job service shall locate the report itself under the job workspace without following model-printed paths, shall select `final` only when `final/report.html` exists and `final/render-validation.json` has `delivery_allowed: true`, otherwise shall select `draft` when `draft/report.html` exists, and shall copy only allowlisted artifact files of the selected source (plus `assumptions.md` when present; its absence is not an error) to `backend/reports/<sanitized name>/goose/YYYY-MM-DD[_N]/` with the delivery status recorded. When a job ends by timeout, non-zero exit, cancellation, or server shutdown (best-effort for shutdown) and a report is selectable under this rule, the job service shall keep the terminal state and error kind classified by REQ-AIR4-007, and shall still archive that report the same way, keeping the delivery status selected by this rule (`final` or `draft`) and recording `interrupted: true`.

**REQ-AIR4-015** — The goose report endpoint shall serve `report.html` with a `Content-Security-Policy` header containing `sandbox` and without `allow-scripts` or `allow-same-origin`.

**REQ-AIR4-016** — When the run identifier fails the pattern `^\d{4}-\d{2}-\d{2}(_\d+)?$` or the resolved path falls outside the reports root, the goose report endpoint shall return 404.

**REQ-AIR4-017** — The history response shall list existing markdown reports with `kind: "markdown"` and goose runs with `kind: "goose"` plus their delivery status (`final` / `draft`) and `interrupted` flag (default `false`).

### 4.4 프론트엔드

**REQ-AIR4-018** — The AI report modal shall label the deep mode "Goose" and shall display a goose report only inside an iframe whose `sandbox` attribute excludes `allow-scripts` and `allow-same-origin`.

**REQ-AIR4-019** — When the displayed goose report has delivery status `draft`, the modal shall show a visible banner reading "최종 감사 미통과 초안" above the iframe, and when the run is marked `interrupted`, the modal shall show a notice that the analysis was interrupted regardless of its delivery status.

**REQ-AIR4-020** — When the modal is reopened for a code whose goose job was started earlier in the same browser tab and is still running, the hook shall resubscribe to that job's events without starting a new job; closing the modal shall not cancel the job.

**REQ-AIR4-021** — While a goose job for the cell's code that was started earlier in the same browser tab is running, the chart cell AI button shall show its active state, including after the modal is closed and after the page is reloaded in the same tab, and shall clear it once the job is no longer running.

### 4.5 정리와 회귀

**REQ-AIR4-022** — The tracked backend sources shall not contain the deep research service, its collector, the synthesis prompt, or any reference to them or to the Brave/Tavily/Naver/YouTube keys, shall not contain any directory named `.claude` or file named `CLAUDE.md`, and the server shall start without them.

**REQ-AIR4-023** — The Fast (codex) mode shall keep its current request contract and behavior.

## 5. 비기능 제약

- 단일 uvicorn 워커 전제(기존 `@MX:WARN` 범위와 같음).
- `AI_REPORT_GOOSE_TIMEOUT` 기본값 900초(M1 P4 실행 352.8초 × 2를 5분 단위로 올림). 표본 1회이고 초안에서 멈춘 실행이라 감사·`--final` 경로 시간이 들어 있지 않다. 라이브 AC-025에서 다시 재고, 더 길면 갱신한다.
- 하네스 위치는 리포 밖이다. 기본 `~/.goose-harness`, `AI_REPORT_GOOSE_HARNESS_DIR`로 바꿀 수 있다. 리포 안 위치는 M1에서 오염이 확인돼 쓰지 않는다(캐시 생성 토큰 115,950 대 13,028, MoAI 스킬·에이전트·MCP 서버가 세션에 섞임).
- 인증은 구독(OAuth)이며 추가 환경 변수가 필요 없다(M1 P0, `apiKeySource: none`).
- 인수 기준: `acceptance.md`. 압축본: `spec-compact.md`.

## 6. 제외 사항 (Exclusions)

이 SPEC에서 만들지 않는 것은 아래와 같다(out of scope).

### Out of Scope — 분석 유형

- goose의 다른 흐름(동종 비교, 실적 해설, 사건 영향, 관심종목 재점검, 보유자산 상담, 증시 마감)과 유형 선택 UI.

### Out of Scope — 실행 기반

- Agent SDK 전환, MCP·금융 API 연결.
- 다중 워커 지원, 작업 상태의 디스크·DB·Redis 영속화, 서버 재시작 후 진행 중 작업 복구.

### Out of Scope — 내용 품질 보증

- 리포트 내용의 사실 정확성 검증. 시스템은 goose 자체 팩트체크·감사 결과를 표시만 하며 내용이 맞는지 보증하지 않는다.
- 프롬프트 주입이 리포트 문장을 왜곡했는지의 자동 탐지.
- `assumptions.md` 내용의 타당성 판단(존재와 비어 있지 않음만 확인).

### Out of Scope — 기존 자산

- goose 스킬 내용 수정과 자동 업데이트(업데이트는 수동 벤더링).
- Fast(codex) 모드 변경.
- 기존 markdown 리포트 파일의 삭제·이동·변환.
- SPEC-AI-REPORT-002 문서 본문 수정.
