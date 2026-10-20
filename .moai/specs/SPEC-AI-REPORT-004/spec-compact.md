# SPEC-AI-REPORT-004 (압축본)

> 원문: `spec.md` v0.4.1, `acceptance.md`. 요구사항·인수 기준·변경 파일·제외 사항만 담는다.

## 요구사항

- REQ-AIR4-001 — When the server starts, the job service shall verify the tracked harness source against the manifest committed in the repository and, only when every listed file matches and no unlisted source file exists (the manifest file `goose-manifest.json` itself and `.DS_Store` files are excluded from this check and are never installed), shall install it into the harness directory (`AI_REPORT_GOOSE_HARNESS_DIR`, default `~/.goose-harness`) by replacing the installed `CLAUDE.md` and `.claude/` directory and leaving `runs/` untouched; when the source verification fails, it shall not install and shall record a startup integrity failure that holds until the next server start. When a goose job is about to start and either a startup integrity failure is recorded (even if a previously installed harness matches the committed manifest) or the installed harness fails the integrity check against that committed manifest (a listed file is missing or its sha256 differs, or an unlisted file exists under the harness `.claude/` directory), the job service shall record the job as `error` with error kind `integrity`, shall not launch `claude`, shall not register the job as the running job, and shall not consume daily quota, and the router shall return 202 with that job's `job_id`.
- REQ-AIR4-002 — The goose runner shall launch `claude -p` with the harness directory as working directory, `--setting-sources project`, `--settings <harness directory>/.claude/settings.json`, `--strict-mcp-config`, `--output-format stream-json`, `--permission-mode dontAsk`, and `--model` set to `AI_REPORT_GOOSE_MODEL` (default `sonnet`), and shall not pass `bypassPermissions` or `--dangerously-skip-permissions`. The harness settings file shall set `disableAllHooks: true`, `autoMemoryEnabled: false`, `claudeMdExcludes` containing `**/.claude/CLAUDE.md`, and an `env.PATH` naming the system binary directories.
- REQ-AIR4-003 — The harness permission policy shall deny, without prompting, every tool call outside the allowlist: WebSearch, WebFetch, Read/Glob/Grep inside the harness, writes inside the job workspace only, Agent, Skill, and Bash limited to the exact script paths of `render_report.py` and `audit_report.py`; the policy shall also deny read-only Bash commands that read a path outside the harness directory, whether the path is written as an absolute path or with `~` or `$HOME`, and whether the command stands alone or is chained after an allowed command, because Claude Code auto-approves some read-only Bash commands in `dontAsk` mode.
- REQ-AIR4-004 — The goose runner shall pass the subprocess only allowlisted environment variables, so that backend secrets are not inherited.
- REQ-AIR4-005 — The headless goose session shall not ask the user questions; it shall proceed with the defaults stated in the prompt and harness instructions and shall write every assumption it made to `assumptions.md` in the job workspace (stating "가정 없음" when there are none).
- REQ-AIR4-006 — When a job exceeds `AI_REPORT_GOOSE_TIMEOUT`, is cancelled, or the server shuts down, the goose runner shall terminate the whole subprocess group (SIGTERM, then SIGKILL after a configurable grace period).
- REQ-AIR4-007 — When a job ends other than by exit 0 with a report selectable under REQ-AIR4-014, the job service shall set exactly one terminal state according to its cause: cancel request or server shutdown → state `cancelled` (no error kind); integrity mismatch → `error`/`integrity`; executable missing → `error`/`binary_missing`; authentication failure in stderr → `error`/`auth`; timeout → `error`/`timeout`; exit 0 with no report → `error`/`empty_output`; any other non-zero exit → `error`/`exit_error`.
- REQ-AIR4-008 — When `POST /ai-report/{code}?mode=deep` is received, the router shall decide in this order and stop at the first match: invalid code format → 422; unknown stock → 404; `claude` executable missing → 503; a goose job for the same code is running → 200 with that `job_id`, consuming no quota; a goose job for a different code is running → 429 with error `goose_busy` naming the running stock; daily quota `AI_REPORT_GOOSE_DAILY_QUOTA` (default 5) exhausted → 429 with error `goose_rate_limit`; the integrity check of REQ-AIR4-001 fails (including a recorded startup integrity failure) → 202 with the `job_id` of a job recorded as `error`/`integrity`, consuming no quota and not registering it as running (REQ-AIR4-001); otherwise start a background job, consume one quota unit, and return 202 with a new `job_id`.
- REQ-AIR4-009 — When a client subscribes to `GET /ai-report/jobs/{job_id}/events`, the job service shall replay every past event in sequence order and then stream live events; when `Last-Event-ID` is supplied, it shall send only events after that id; for an unknown `job_id` it shall return 404.
- REQ-AIR4-010 — While a job is running, the job shall continue when every event subscriber disconnects.
- REQ-AIR4-011 — When `POST /ai-report/jobs/{job_id}/cancel` is received for a running job, the job service shall stop the job and emit a terminal `cancelled` event; for a finished job it shall return the current state unchanged; for an unknown `job_id` it shall return 404.
- REQ-AIR4-012 — When the runner observes a stream-json event listed in the progress mapping table, the job service shall emit the corresponding phase event; unknown events shall be ignored without raising.
- REQ-AIR4-013 — When `GET /ai-report/goose/active` is received, the router shall return the running goose job as `{job_id, code, stock_name, status}`, or `null` when no goose job is running.
- REQ-AIR4-014 — When a job's session ends, the job service shall locate the report itself under the job workspace without following model-printed paths, shall select `final` only when `final/report.html` exists and `final/render-validation.json` has `delivery_allowed: true`, otherwise shall select `draft` when `draft/report.html` exists, and shall copy only allowlisted artifact files of the selected source (plus `assumptions.md` when present; its absence is not an error) to `backend/reports/<sanitized name>/goose/YYYY-MM-DD[_N]/` with the delivery status recorded. When a job ends by timeout, non-zero exit, cancellation, or server shutdown (best-effort for shutdown) and a report is selectable under this rule, the job service shall keep the terminal state and error kind classified by REQ-AIR4-007, and shall still archive that report the same way, keeping the delivery status selected by this rule (`final` or `draft`) and recording `interrupted: true`.
- REQ-AIR4-015 — The goose report endpoint shall serve `report.html` with a `Content-Security-Policy` header containing `sandbox` and without `allow-scripts` or `allow-same-origin`.
- REQ-AIR4-016 — When the run identifier fails the pattern `^\d{4}-\d{2}-\d{2}(_\d+)?$` or the resolved path falls outside the reports root, the goose report endpoint shall return 404.
- REQ-AIR4-017 — The history response shall list existing markdown reports with `kind: "markdown"` and goose runs with `kind: "goose"` plus their delivery status (`final` / `draft`) and `interrupted` flag (default `false`).
- REQ-AIR4-018 — The AI report modal shall label the deep mode "Goose" and shall display a goose report only inside an iframe whose `sandbox` attribute excludes `allow-scripts` and `allow-same-origin`.
- REQ-AIR4-019 — When the displayed goose report has delivery status `draft`, the modal shall show a visible banner reading "최종 감사 미통과 초안" above the iframe, and when the run is marked `interrupted`, the modal shall show a notice that the analysis was interrupted regardless of its delivery status.
- REQ-AIR4-020 — When the modal is reopened for a code whose goose job was started earlier in the same browser tab and is still running, the hook shall resubscribe to that job's events without starting a new job; closing the modal shall not cancel the job.
- REQ-AIR4-021 — While a goose job for the cell's code that was started earlier in the same browser tab is running, the chart cell AI button shall show its active state, including after the modal is closed and after the page is reloaded in the same tab, and shall clear it once the job is no longer running.
- REQ-AIR4-022 — The tracked backend sources shall not contain the deep research service, its collector, the synthesis prompt, or any reference to them or to the Brave/Tavily/Naver/YouTube keys, shall not contain any directory named `.claude` or file named `CLAUDE.md`, and the server shall start without them.
- REQ-AIR4-023 — The Fast (codex) mode shall keep its current request contract and behavior.

## 인수 기준

| AC | REQ | 요지 |
|---|---|---|
| 001 | 001 | 서버 시작 시 원본 대조 후 설치(`runs/` 보존, 매니페스트·`.DS_Store` 제외), 원본 변조·목록 밖 원본 파일 시 설치 안 함 / 원본 대조 실패 기록 시 기존 정상 설치본이 있어도 → 202, `integrity`, 실행 0회 / 설치본 1바이트 변조·목록 밖 파일 → 202, `integrity`, 실행 0회, active `null`, 쿼터 0 / 재시작 시 복구 |
| 002 | 002 | argv 리터럴(`--settings <H>/.claude/settings.json`, `--strict-mcp-config` 포함), 모델 기본 `sonnet`, 우회 플래그·`--restricted` 없음, cwd 기본 `~/.goose-harness`(리포 밖), 설정 키 4개(`claudeMdExcludes`에 `**/.claude/CLAUDE.md` 포함) |
| 003 | 003 | [라이브] 음성 탐침 11건 거부(하네스 밖 읽기 전용 Bash 6형태: `cat`·`head`·`grep` 절대 경로, `~`·`$HOME` 경로, 허용 스크립트 뒤 복합 명령), 파일 변화 0, 카나리 미노출 |
| 004 | 004 | env 키 ⊆ 허용 목록 8개, canary 비밀 환경 변수 3개 미전달 |
| 005 | 006 | 유예 0.5초 주입, 3초 안에 자식·손자 종료, `timeout` |
| 006 | 007 | 오류 종류 4종 분류 |
| 007 | 008 | 같은 종목 2회 → 202 J1, 200 J1, 실행 1회, 쿼터 1 |
| 008 | 008 | 판정 순서 7행 표(쿼터 vs 422/404/503, 같은 종목+쿼터 소진 200, 다른 종목 `goose_busy`) |
| 009 | 009 | 재생 1~5, `Last-Event-ID: 3` → 4,5, 404 |
| 010 | 010 | 구독 끊김 후 `done` |
| 011 | 011, 006, 007 | 순차 전제(J1 취소 후 J3): 취소 → 상태 `cancelled`·오류 종류 없음·그룹 소멸, 완료 작업 불변, 404, lifespan 종료 → `cancelled` |
| 012 | 012 | 녹화 픽스처(196줄) → design §3.5 측정 표 기준 단계 순서 리터럴, 역할 단계 없음, 예외 없음 |
| 013 | 014 | 허용 파일 + `assumptions.md` + `job.json`만 복사, 모델 경로 무시 |
| 014 | 014 | final 우선 / draft만 / final 있으나 `delivery_allowed: false` → draft / 없음 → `empty_output` / (e) 시간 초과+초안 → `error/timeout` 유지·초안 보관·`draft`+`interrupted` / (f) 취소+초안 → `cancelled`·동일 보관 / (g) 시간 초과+final 조건 충족 → `final`+`interrupted` |
| 015 | 015 | CSP 헤더 |
| 016 | 016 | 경로 탈출 5종 404 |
| 017 | 017 | 기록 5항목 kind·전달 상태, 중단 항목만 `interrupted: true` |
| 018 | 018 | “Goose” 라벨, iframe sandbox 값 리터럴 |
| 019 | 019 | draft에서만 배너 1개, `interrupted`면 전달 상태와 상관없이 중단 안내(기록에서 열어도) |
| 020 | 020 | 재구독 1회, 시작·취소 POST 0회 |
| 021 | 013 | `/goose/active` 실행 중 객체 / `null`, 422 아님 |
| 022 | 021 | 셀 폴링: 닫은 뒤 활성, `null`이면 해제·중지, 새로고침 후 복원, 저장값 없는 셀 폴링 0, 새 작업 시작 시 재개 |
| 023 | 022 | `git grep -nI` 0줄 + `git ls-files backend`에 `.claude`·`CLAUDE.md` 0줄 + `import backend.main` 성공 |
| 024 | 023 | Fast 테스트 무수정 통과 |
| 025 | 005, 014, 017, 018, 019, 020 | [라이브] 299030 전 과정, `assumptions.md` 존재·비어 있지 않음, 실행 시간·`final/` 여부 기록 |

## 변경 파일

- 신규(추적 원본): `backend/goose_harness_src/{harness-instructions.md, claude-settings.json, goose-manifest.json, skills/goose/**}` — 서버 시작 시 `~/.goose-harness/{CLAUDE.md, .claude/settings.json, .claude/skills/goose/**}`로 설치(리포 밖, 커밋 안 함)
- 삭제(미추적): M1 임시 `backend/goose_harness/`
- 신규: `backend/services/goose_runner.py`, `backend/services/goose_job_service.py`, `frontend/src/hooks/useGooseActive.ts`, 테스트 `test_goose_runner.py`, `test_goose_job_service.py`, `test_ai_report_router_goose.py`, 픽스처 `goose_stream_299030.jsonl`, `useAiReport.goose.test.ts`, `useGooseActive.test.ts`
- 수정: `backend/routers/ai_report.py`, `backend/services/ai_report_service.py`, `backend/schemas/ai_report.py`, `backend/main.py`, `backend/prompts/__init__.py`, `backend/prompts/README.md`, `.env.example`, `frontend/src/components/{AiReportModal.tsx, ProgressPanel.tsx, ChartGrid/ChartCell.tsx}`, `frontend/src/hooks/useAiReport.ts`, `frontend/src/api/aiReport.ts`, `frontend/src/types/aiReport.ts`, 테스트 `AiReportModal.test.tsx`, `ProgressPanel.test.tsx`
- 축소: `backend/services/claude_cli_streamer.py`, `backend/tests/test_claude_cli_streamer.py`
- 삭제: `backend/services/deep_research_service.py`, `deep_research_collector.py`, `backend/prompts/stock_synthesis_prompt.md`, `backend/tests/test_deep_research_service.py`, `test_deep_research_collector.py`, `test_ai_report_router_deep_mode.py`(교체)

## 제외 사항

- goose의 다른 흐름과 유형 선택 UI
- Agent SDK, MCP·금융 API
- 다중 워커, 작업 상태 영속화, 서버 재시작 후 작업 복구
- 리포트 내용의 사실 정확성 검증, 주입에 의한 문장 왜곡 탐지, `assumptions.md` 내용의 타당성 판단
- goose 스킬 수정·자동 업데이트, Fast 모드 변경, 기존 markdown 파일 삭제·이동, SPEC-AI-REPORT-002 본문 수정
