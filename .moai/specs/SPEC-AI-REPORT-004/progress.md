# SPEC-AI-REPORT-004 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-10-19T00:00:00+09:00
- plan_status: audit-ready
- plan_audit: iteration 3 FAIL 0.91 → PASS-WITH-DEBT (사용자 승인), 부채 R3-M1·R3-M2는 v0.3.2에서 해소, 오케스트레이터 검증 완료(§G 끝 "오케스트레이터 검증" 참조)

## §E.2 Run-phase Evidence

### Phase 1 Plan Audit Gate (run 진입, 2026-10-19)

- audit_verdict: PASS
- audit_score: 0.93 (Tier L 기준 0.85)
- audit_report: .moai/reports/plan-audit/SPEC-AI-REPORT-004-review-4.md
- audit_at: 2026-10-19
- blocking 결함 0건, 선택 결함 R4-1~R4-9(SHOULD-FIX 3: R4-1·R4-3·R4-7). M1 차단 결함 없음.
- M1 이후 재감사: review-5 FAIL 0.83(v0.4.0, M2 차단 4건) → 1회 수정(v0.4.1, 3271d38) → review-6 PASS 0.90 (`.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-6.md`). 남은 선택 결함 N1(설치본 `.DS_Store`)·N2(AC-003 탐침 명령 문자열 일치)·N3(리포 내 하네스 경로 거부 시 처리)는 M2 위임 지시에서 해소.

### M1 스파이크 관측

- 일시: 2026-10-19 (KST), manager-develop. 기준: 이 실행, 이 트리, HEAD `11f3e16`(branch `main`). 모든 관측은 아래 명령을 이번에 직접 실행한 출력이다.
- `claude --version` → `2.1.303 (Claude Code)` (research.md는 2.1.302 기준). `--help`에서 `--setting-sources`, `--permission-mode`, `--output-format`, `--no-session-persistence`, `--plugin-dir`, `--append-system-prompt`, `--restricted`, `--tools`, `--strict-mcp-config`, `--settings` 확인. 2.1.303의 `--restricted`는 "user, project, local 설정 파일을 무시"하고 프로젝트 스킬도 빠진다(아래 P2 보조 탐침).
- 실행기: 스크래치의 `run_goose.py`(design §3.1 argv + 환경 변수 허용 목록 + `start_new_session=True` + 시간 상한 후 `killpg`). 넘긴 환경 변수: `["HOME","LANG","PATH","SHELL","TMPDIR","USER"]`(`LC_ALL`·`TZ`는 부모 셸에 없음).
- 하네스: `backend/goose_harness/`(리포 위치, 커밋 안 함)와 상위에 CLAUDE.md가 없는 스크래치 복사본 `<scratch>/p2/harness`(이하 "리포 밖 위치"). 부모 경로 스캔 `ls <dir>/CLAUDE.md <dir>/CLAUDE.local.md <dir>/.claude/CLAUDE.md`(루트까지) → 출력 없음. 단 `~/.claude/CLAUDE.md`(사용자 전역)는 존재한다.

#### 사전 점검 — goose 배포물 sha256

```
$ python3 -I shacheck.py ~/Downloads/goose        # DISTRIBUTION.json files[] 30개 대조
listed=30 mismatch_or_missing=0 unlisted_extra=['.DS_Store', 'workflows/.DS_Store']
$ python3 -I shacheck.py backend/goose_harness/.claude/skills/goose   # rsync --exclude .DS_Store 후 재대조
listed=30 mismatch_or_missing=0 unlisted_extra=[]
```

불일치 0건. 목록 밖 파일은 `.DS_Store` 2개뿐이며 벤더링에서 제외했다.

#### P0 (G1) — 인증

명령: 하네스 cwd에서 `claude -p "ok라고만 답하세요" --setting-sources project --output-format stream-json --verbose --permission-mode dontAsk --no-session-persistence --model sonnet` (허용 목록 환경 변수만 전달).

```
리포 위치:   is_error False subtype success turns 1 dur_ms 2496  apiKeySource none  model claude-sonnet-5-5
리포 밖 위치: is_error False subtype success turns 1 dur_ms 2959  apiKeySource none
```

`result.is_error=false`. 구독(OAuth) 인증이 위 6개 환경 변수만으로 동작했다(`apiKeySource: none`, API 키 불필요).

#### P1 (G3) — `system/init` 목록

- 두 위치 모두 `skills`에 `goose`가 있고 `slash_commands`에 `goose`가 있다. 내장 스킬(`deep-research`, `design`, `dataviz`, `code-review`, `loop`, `schedule` 등)은 위치와 무관하게 항상 있다.
- **리포 위치에서 누수 확인**: `skills`에 `agency`, `moai`, `moai-domain-design-dna`, `moai-domain-html-report`, `moai-domain-svg-infographic`, `codemaps-extract`, `plan-research-fanout`, `sync-audit-4dim`; `slash_commands`에 `moai:*` 16개; `agents`에 MoAI 에이전트 17개(`manager-*`, `plan-auditor`, `builder`, `copywriter` 등); `mcp_servers`에 리포 `.mcp.json`의 `context7`·`moai`·`sequential-thinking`; `memory_paths.auto`가 리포 메모리(`…-my-chart/memory/`).
- 리포 밖 위치: `agents ['claude','Explore','general-purpose','Plan','statusline-setup','web-fetch']`, MoAI 스킬·에이전트 없음. 사용자 전역 플러그인(moai-business 등)은 두 위치 모두 없음(`--setting-sources project` 효과).
- 두 위치 모두 **claude.ai 계정 커넥터 MCP**(Gmail·Google Drive·Calendar·Notion·Slack·Claude Docs, 쓰기 도구 포함)가 붙었다. `--strict-mcp-config`를 주면 `mcp_servers []`가 된다(P2c).
- 도구 목록에 `Agent`(표기 `Task`), `Bash`, `Read`, `Write`, `Edit`, `Skill`, `WebSearch`는 있으나 **`WebFetch`·`Glob`·`Grep`는 메인 도구 목록에 없다**. WebFetch는 내장 `web-fetch` 서브에이전트 안에서 쓰였다(P5).

#### P2 (G2) — 입력 토큰 비교

```
p0_repo           cache_create 115950  cache_read 11227  cost 0.4650
p0_scratch        cache_create  13028  cache_read 11228  cost 0.0533
p2b_repo  (--restricted --strict-mcp-config --settings <harness>)  cache_create 6160  → skills에 goose 없음
p2c_scratch (--strict-mcp-config, autoMemoryEnabled:false)          cache_create 6851  → goose 있음, mcp_servers [], memory_paths None
```

- 리포 위치는 같은 프롬프트에서 캐시 생성 토큰이 약 8.9배(115,950 vs 13,028)다. P1의 누수 목록과 합쳐 **오염 확인**.
- `--restricted`는 오염을 없애지만 goose 스킬도 사라져 대안이 되지 않는다.
- 결정: **하네스를 리포 밖에 둔다**(`AI_REPORT_GOOSE_HARNESS_DIR`). 추가로 `--strict-mcp-config`, 설정 `autoMemoryEnabled: false`.
- 부수 관측: 리포 안에 하네스를 두면 MoAI 세션 자신도 `backend/goose_harness/.claude/skills`의 `goose` 스킬을 새로 발견한다(이 세션에 "New skills discovered" 알림 수신). 리포 밖 이전의 근거가 하나 더 있다.

#### P3 (G6) — 음성 탐침 (리포 밖 위치, 허용 규칙 활성 상태)

1차(P3, 허용 규칙이 무시된 상태)와 2차(P3b, `--settings <harness>/.claude/settings.json`로 허용 규칙 활성)를 모두 실행했다. 판정은 2차 기준이다. `../../.env`는 리포 밖 위치에서 스크래치의 카나리 파일(`CANARY_ONLY=m1-p3-not-a-secret`)로 해석되도록 배치했고, 실제 프로젝트 파일은 대상이 아니다.

```
USE Bash  python3 .claude/skills/goose/workflows/../../../runs/x.py
RES err=True Permission to use Bash with command python3 .claude/skills/goose/workflows/../../../runs/x.py has been denied.
USE Write <H>/probe-outside-runs.txt
RES err=True Permission to use Write has been denied because Claude Code is running in don't ask mode. …
USE Edit  <H>/.claude/skills/goose/SKILL.md
RES err=True <tool_use_error>File is in a directory that is denied by your permission settings.</tool_use_error>
USE Read  <scratch>/.env            (모델이 ../../.env를 절대 경로로 바꿔 호출)
RES err=True Permission to use Read has been denied because Claude Code is running in don't ask mode. …
USE Bash  python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --output-dir ../../probe-out   (추가 탐침 5)
RES err=True Permission to use Bash with command … --output-dir ../../probe-out has been denied.
RESULT permission_denials: 5건 (Bash, Write, Edit, Read, Bash)
```

파일 증거:

```
$ python3 -I treehash.py <H> <scratch>/.env > p3b_before.json; (탐침 실행); … > p3b_after.json
$ cmp p3b_before.json p3b_after.json && echo HASH_IDENTICAL
HASH_IDENTICAL
$ find <scratch> -newer p3b_marker -not -path "<scratch>/logs*"
(출력 없음)
$ ls <H>/probe-outside-runs.txt <scratch>/probe-out → No such file or directory
```

AC-003 요구 4종 + 추가 1종 모두 거부, 파일 변화 0. 양성 대조(같은 설정): `Write runs/pos/ok.txt` 성공, `WebSearch` 성공.

#### P4 (G4·G5·G7·G8·G9) — 실제 분석 1회 (하나기술 299030, sonnet)

- 1차 실행(`p4_run1`): 24.7초에 끝남, 보고서 없음. 원인 = stderr `Ignoring 11 permissions.allow entries from .claude/settings.json: this workspace has not been trusted.` 리포 밖 디렉터리는 신뢰(trust) 대화상자를 거치지 않아 프로젝트 설정의 **allow 항목이 무시**되고 deny만 적용된다(WebSearch·Write·Bash 거부 3건). 하네스 원인이므로 계획의 대체 경로에 따라 1회 재시도했다.
- 수정: `--settings <harness>/.claude/settings.json`을 argv에 추가(같은 경고는 계속 나오지만 플래그 설정의 allow는 적용됨, 양성 대조로 확인). 또 `-p` 세션의 Bash 도구가 부모 `PATH`를 쓰지 않아 `python3`를 찾지 못했다(`(eval):1: command not found: python3`, `command -v sh` → exit 1, 환경 변수 59개를 넘겨도 동일, 리포 위치도 동일). 설정 `"env": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}`로 해결(`command -v sh` → `/bin/sh`, `python3 --version` → `Python 3.9.6`).
- 2차 실행(`p4_run2`, 최종 관측): 프롬프트는 design §3.2 형식, 기준일 `2026-10-19T16:25:56+09:00`, 작업 디렉터리 `runs/m1p4`.

```
run_goose.py meta: {"rc": 0, "timed_out": false, "wall_s": 354.0, "env_names_passed": ["HOME","LANG","PATH","SHELL","TMPDIR","USER"]}
RESULT is_error False success turns 23 dur_ms 352808 cost 0.7648 term completed
USAGE {"input_tokens": 28, "output_tokens": 30106, "cache_creation_input_tokens": 76978, "cache_read_input_tokens": 791837}
ASK(AskUserQuestion tool_use) 0
```

- 사람 입력 없이 종료: 예(exit 0, 질문 도구 호출 0건, 결과는 질문이 아니라 요약).
- `runs/m1p4/assumptions.md`: 있음, 1,842바이트, 비어 있지 않음(대상 식별·기준일·범위·순차 수행·DART 미열람·집계사 수치 사용 등 11개 항목).
- 시간 상한 안에서 끝남(352.8초).

#### P5 (G4) — Agent 사용

```
AGENT_CALLS 3
   ('web-fetch', 'DART 하나기술 공시 열람', main)
   ('web-fetch', '하나기술 실적·IR·뉴스 열람', main)
   ('web-fetch', 'DART rcpNo 및 본문 접근 재시도', main)
SUBAGENT_STATS {"spawned": 3, "max_depth": 1, "completed": 3, "failed": 0, "by_type": {"web-fetch": 3}}
SUB_TOOLS {'WebFetch': 18}
서브에이전트 쪽 거부: 0건 (parent_tool_use_id가 있는 거부 결과 없음)
```

goose는 finance/news/industry/review 역할을 서브에이전트로 나누지 않았다. 역할은 메인 대화에서 순차 수행했고("역할 분업은 같은 대화에서 순차 수행", assumptions.md에도 기록), 서브에이전트는 원문 열람용 내장 `web-fetch` 3회뿐이다. 메인 쪽 거부 1건: `curl -s -m 20 "https://dart.fss.or.kr/…" | grep …`(허용 목록 밖, 정상 거부).

#### P6 (G7) — 산출물

```
$ find <H>/runs -type f
runs/m1p4/input.json                      40402
runs/m1p4/assumptions.md                  1842
runs/m1p4/draft/report.html               961688
runs/m1p4/draft/report-input.json         40402
runs/m1p4/draft/source-ledger.json        8651
runs/m1p4/draft/render-validation.json    7718
$ python3 -c "…json.load(render-validation.json)…"
{'delivery_allowed': False, 'delivery_status': 'draft_pending_audit'}
```

- `draft/` 있음, `final/` 없음, `delivery-audit.json` 없음(`audit_report.py`와 `--final`을 실행하지 않음 → `decision` 값 관측 불가).
- 미완 사유(세션 결과 문구): DART 뷰어가 JS 렌더링이라 본문을 못 읽음, 브라우저가 없어 visual을 통과로 기록하지 않음.
- 하네스 무결성(design §6.1): `treehash.py <H>/.claude <H>/CLAUDE.md`를 실행 전후 비교 → `HARNESS_HASH_IDENTICAL`.

#### P7 (G9) — 이벤트·도구 빈도 (`p4_run2`, 196줄)

| 이벤트 타입 | 개수 | 도구(메인) | 개수 | 도구(서브에이전트) | 개수 |
|---|---|---|---|---|---|
| system/thinking_tokens | 64 | Read | 6 | WebFetch | 18 |
| assistant | 55 | Bash | 5 | | |
| user | 43 | WebSearch | 4 | | |
| system/task_progress | 18 | Agent | 3 | | |
| system/task_started | 3 | Write | 2 | | |
| system/task_updated | 3 | ToolSearch | 1 | | |
| system/task_notification | 3 | Edit | 1 | | |
| rate_limit_event | 2 | | | | |
| tool_progress | 2 | | | | |
| system/init · system/permission_denied · result/success | 1 · 1 · 1 | | | | |

메인 순서: `init` → GUIDE·references Read 6회 → WebSearch 3회 → Agent(web-fetch) 2회 → WebSearch → Agent 1회 → (거부된 curl) → `render_report.py --help` → Write `assumptions.md` → Write `input.json` → `render_report.py --input … --output-dir runs/m1p4/draft` → Edit `input.json` → 렌더 재실행 → `result`.

부수 관측: 허용 목록에 없는 읽기 전용 Bash(`ls runs …`, `render_report.py --help 2>&1 | head -30; wc -l …`)는 거부되지 않았다. dontAsk에서도 읽기 전용 명령은 자동 허용되는 것으로 보인다. design §2.2의 "그 외 전부 거부"는 쓰기·실행 명령에 한해 성립한다.

#### 판정: 조건부 GO

| GO 조건 (plan M1) | 관측 | 충족 |
|---|---|---|
| P0 인증 성공, P1 `goose` 발견 | `is_error=false`, `skills`에 `goose` | 예 |
| P3 4종 거부 + 파일 변화 0 | 허용 규칙 활성 상태에서 5/5 거부, `HASH_IDENTICAL` | 예 |
| P4 사람 입력 없이 종료 + `report.html` 생성 | exit 0, 질문 0, `draft/report.html` (D7에 따라 초안도 GO) | 예 |
| P2 오염 시 리포 밖 이전 또는 `--restricted` 재탐침 | 리포 위치 오염 확인 → 리포 밖 위치에서 P3·P4 통과. `--restricted`는 goose를 잃어 탈락 | 조건 충족(리포 밖) |

조건부인 이유: 위 통과는 **리포 밖 하네스 + `--settings <harness>/.claude/settings.json` + `--strict-mcp-config` + 설정 `env.PATH`·`autoMemoryEnabled:false`** 조합에서만 관측했다. design §2·§3.1의 기본안(리포 안, 플래그 없음)으로는 통과하지 않는다. 이 조합을 design에 반영하기 전에는 M2에 들어가지 않는다.

#### M1 산출값

| 항목 | 값 |
|---|---|
| `AI_REPORT_GOOSE_TIMEOUT` 기본값 | 352.8초 × 2 = 705.6초 → 5분 단위 올림 **900초**. 단 표본 1회이고, DART 본문을 못 읽어 초안에서 멈춘 실행이다(감사·`--final` 미실행). 전체 경로는 더 길 수 있다. |
| 결과 파일 위치 (작업 디렉터리 기준) | `draft/report.html`, `draft/report-input.json`, `draft/source-ledger.json`, `draft/render-validation.json`, 최상위 `assumptions.md`, 최상위 `input.json`(모델이 쓴 렌더 입력, 복사 허용 목록 밖). `final/`·`delivery-audit.json`은 관측 못 함 |
| 하네스 위치 | 리포 밖(`AI_REPORT_GOOSE_HARNESS_DIR` 필수). 리포 안 기본값 폐기 |
| 동작한 권한 규칙 문법 | `"Read(./**)"`, `"Write(./runs/**)"`, `"Edit(./runs/**)"`, `"Bash(python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py:*)"`, deny `"Bash(*..*)"`, `"Edit(./.claude/**)"`, `"Read(../**)"`, `"Read(**/.env)"`. 리포 밖에서는 `--settings <harness>/.claude/settings.json`로 넣어야 allow가 적용됨 |
| 추가 argv | `--strict-mcp-config`, `--settings <harness>/.claude/settings.json` |
| 추가 설정 키 | `"env": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}`, `"autoMemoryEnabled": false`, `"disableAllHooks": true` |
| 인증용 환경 변수 | 추가 변수 없음. `HOME`, `USER`, `PATH`, `SHELL`, `TMPDIR`, `LANG`만으로 `apiKeySource: none` 인증 성공 |
| 녹화 픽스처 | `backend/tests/fixtures/goose_stream_299030.jsonl` (196줄, 스크럽: 하네스 경로 32곳 → `/HARNESS`, `/Users/<계정>` 9곳 → `/HOME`, 계정명 9곳 → `user`, 기사 본문의 기자 이메일 3건 → `redacted@example.invalid`, 비밀 패턴 0건. `grep -c byunjungwon` → 0. `api[_-]?key|token…` 패턴 1건은 `"apiKeySource":"none"` 필드명) |

진행 단계 대응표 (관측 기반, design §3.5 대체안)

| 관측 이벤트 | 진행 단계 |
|---|---|
| `system/init` | `goose_start` |
| 메인 `Read` `.claude/skills/goose/workflows/**` | `plan`(지침 읽기) |
| 메인 `WebSearch` | `research_tick` |
| `Agent`(subagent_type `web-fetch`) 또는 `system/task_started` | `fetch_start`(description 표시) |
| 서브에이전트 `WebFetch` (`parent_tool_use_id` 있음) | `research_tick` |
| `system/task_notification` | `fetch_done` |
| `Write runs/{job}/input.json` | `compose` |
| `Bash render_report.py` (`--final` 없음, `--help` 제외) | `render_draft` |
| `Bash audit_report.py` | `audit` (미관측) |
| `Bash render_report.py --final` | `render_final` (미관측) |
| `system/permission_denied` | 단계 변화 없음(경고 로그) |
| `result` | `session_end` |

역할별(finance/news/industry/review) 단계는 관측되지 않았다. goose가 역할을 메인에서 순차 수행했기 때문이다.

#### design.md §9 변경 필요 목록 (manager-spec 재위임용)

| 항목 | 잠정값 | 측정값 |
|---|---|---|
| 하네스 위치 | `backend/goose_harness` | 리포 밖 필수(오염: cache_create 115,950 vs 13,028, MoAI 스킬·에이전트·MCP 누수). `AI_REPORT_GOOSE_HARNESS_DIR` 기본값을 리포 밖 경로로 |
| 권한 규칙 문법 | §2.2 | §2.2 문법 그대로 동작. 단 리포 밖에서는 신뢰 대화상자가 없어 프로젝트 allow가 무시되므로 `--settings`로 같은 파일을 넘김. 읽기 전용 Bash는 자동 허용됨을 §2.2에 명시. `WebFetch`·`Glob`·`Grep`는 메인 도구 목록에 없음 |
| argv (§3.1) | `-p … --setting-sources project --permission-mode dontAsk --no-session-persistence --model` | 위에 `--strict-mcp-config`, `--settings <harness>/.claude/settings.json` 추가 |
| 설정 파일 키 | 권한, hooks 없음 | `env.PATH`, `autoMemoryEnabled: false`, `disableAllHooks: true` 추가 |
| 인증 관련 환경 변수 (§3.3) | 미정 | 추가 변수 불필요(`HOME`·`USER` 포함 기본 목록으로 충분) |
| 시간 상한 기본값 | 3600초(임시) | 900초(352.8초×2, 5분 올림). 표본 1회·초안 종료 실행이라는 한계 기록 필요 |
| 진행 단계 대응표 (§3.5) | Agent 설명의 역할 키워드 | 위 관측 기반 표로 교체(역할 단계 없음, web-fetch 시작/완료와 compose 추가) |
| 작업 디렉터리 하위 폴더·산출물 위치 (§5.2) | `draft/`, `final/` | `draft/` 확인, `final/` 미관측. `input.json`은 작업 디렉터리 최상위 |
| 근거 파일 허용 목록 (§5.2) | report·report-input·source-ledger·render-validation·delivery-audit | draft에서 앞의 4개 확인. `delivery-audit.json` 미관측 |
| `assumptions.md` 작성 여부 | §2.1 규칙 | 작성됨(1,842바이트). 규칙 유지 |
| 스크립트 출력 점검 방식 (§6.1) | 미정 | 실행 전후 `.claude/**`+`CLAUDE.md` sha256 트리 비교로 충분히 감지(P3b·P4 모두 동일) |
| `--no-session-persistence`의 범위 (§3.2 표 의미) | 디스크 저장 안 함 | 서브에이전트 메타 파일 3개(각 223~230바이트, `~/.claude/projects/<하네스 경로>/<세션>/subagents/*.meta.json`)는 남음. 대화 본문은 남지 않음 |
| claude.ai 커넥터 MCP | 언급 없음 | 계정 커넥터(Gmail 전송 등)가 기본으로 붙음 → `--strict-mcp-config`로 제거(§6 보안 경계에 추가) |

> 정정 (v0.4.1, plan-audit 5회차 R5-4, manager-spec): 위 표 "스크립트 출력 점검 방식" 행의 "충분히 감지"는 관측을 넘어선 표현이다. M1이 관측한 것은 변경이 없을 때 실행 전후 해시가 같았다는 것, 즉 오탐이 없었다는 것뿐이다. 변경을 일으켜 잡히는지는 관측하지 않았으며 AC-001 (3)(4)가 검증한다. 위 관측 기록 자체는 고치지 않는다.

#### 관측하지 못한 것 (Gaps)

- `final/`, `delivery-audit.json`, `audit_report.py`·`render_report.py --final` 실행 경로: 이번 실행이 초안에서 멈춰 관측하지 못했다.
- 서브에이전트가 같은 권한 규칙을 따르는지: 서브에이전트는 허용된 WebFetch만 써서 거부 사례가 없었다. 서브에이전트 쪽 음성 탐침은 하지 않았다.
- `~/.claude/CLAUDE.md`(사용자 전역 메모리)가 로드되는지: 두 위치에 똑같이 영향을 주므로 P2 비교로는 구분되지 않는다.
- 리포 위치 실행(P0·P2b·diag)에서 리포 hooks가 실행됐는지: `.moai/state`에 다른 세션 흔적은 보이지 않았으나 직접 확인하지 않았다.
- `USER` 등 개별 환경 변수를 뺐을 때의 인증 결과, `-p` Bash가 부모 `PATH`를 무시하는 원인.
- 최종 하네스 위치(리포 밖 영구 경로)에서의 재관측: 이번 리포 밖 위치는 세션 스크래치였다.
- 시간 상한 값의 대표성: 표본 1회.

### M2 하네스 벤더링·설치·무결성

- 일시: 2026-10-19~20 (KST), manager-develop(cycle_type=tdd). 시작 HEAD `9535370`(branch `main`, 로컬 전용·push 안 함). 커밋: `d16b4b6`(원본·매니페스트), `1029017`(설치·무결성 모듈·테스트·lifespan). 실행: venv `/Users/byunjungwon/Dev/my_chart/.venv/bin/python`, cwd 리포 루트. `claude --version` → `2.1.303 (Claude Code)`.
- 산출물: `backend/goose_harness_src/{harness-instructions.md, claude-settings.json, goose-manifest.json, skills/goose/**}`(34개), `backend/services/goose_harness.py`, `backend/tests/test_goose_harness.py`(30건), `backend/tests/test_main_goose_lifespan.py`(1건), `backend/main.py` lifespan 4줄. M1 임시 `backend/goose_harness/`(미추적) 삭제 — 삭제 전 `git ls-files backend/tests/fixtures/goose_stream_299030.jsonl` → 추적 중, `runs/` 파일 0개, `CLAUDE.md`와 `harness-instructions.md` `diff` 동일 확인.
- M4가 쓸 API(모듈 docstring에 기록): `install_at_startup()`(lifespan 1회, 예외 없음), `check_job_integrity()` → `IntegrityResult(ok, reason, error_kind)`(실패 시 `error_kind == "integrity"`), `resolve_harness_dir()`, `build_manifest()`(`python -m backend.services.goose_harness`로 매니페스트 재생성). 시작 설치가 이 프로세스에서 실행되지 않았으면 작업 검사도 실패한다(닫힌 실패 쪽으로 해석).

#### 사전 점검 — goose 배포물 sha256 재대조

```
$ python3 -I shacheck.py ~/Downloads/goose
listed=30 mismatch_or_missing=0 [] unlisted_extra=['.DS_Store', 'workflows/.DS_Store']
$ rsync -a --exclude .DS_Store ~/Downloads/goose/ backend/goose_harness_src/skills/goose/ ; python3 -I shacheck.py backend/goose_harness_src/skills/goose
listed=30 mismatch_or_missing=0 [] unlisted_extra=[]
```

#### E1 — 인수 기준 행렬

AC-001은 M2가 하네스 쪽 판정(설치·대조·작업 검사 함수)을 직접 단위 시험한다. 라우터 응답(202, `job_id` 작업 상태, `GET /goose/active` → `null`, 쿼터 0, 가짜 명령 호출 0회)은 M4 범위라 여기서는 "M4 위임"으로 표시한다.

| AC | 판정 | 근거(테스트 이름 또는 명령) | 관측 |
|---|---|---|---|
| AC-001 (1) | PASS(하네스 쪽) | `test_matching_source_installs_listed_files_and_preserves_runs`, `test_job_integrity_passes_after_clean_install` | 설치본 sha256 = 매니페스트 = 테스트가 hashlib로 계산한 값, `runs/keep.txt` 그대로, `<H>` 아래 `goose-manifest.json`·`.DS_Store` 없음, 최상위 항목 `[.claude, CLAUDE.md, runs]` |
| AC-001 (2) | PASS | `test_one_byte_change_in_source_blocks_install` | `<H>/.claude`·`CLAUDE.md` 생성 안 됨, 작업 검사 `integrity` |
| AC-001 (2b) | PASS(하네스 쪽), 라우터 부분 M4 위임 | `test_startup_source_failure_keeps_old_install_but_fails_every_job` | 재시작 후 원본 1바이트 변경 → 설치본 해시 불변, `verify_installed(옛 설치본) == []`인데도 `check_job_integrity()` 두 번 모두 `ok=False`, `error_kind="integrity"` |
| AC-001 (2c) | PASS | `test_unlisted_source_file_blocks_install` (+ `test_source_file_outside_known_layout_blocks_install`, `test_nested_manifest_named_file_is_not_excluded`) | `extra.md` 추가 → 설치 안 함, 사유에 `extra.md` |
| AC-001 (3) | PASS(하네스 쪽), 라우터 부분 M4 위임 | `test_modified_installed_file_fails_job_integrity`, `test_modified_installed_claude_md_fails_job_integrity`, `test_missing_installed_file_fails_job_integrity` | 설치본 1바이트 변경 → `ok=False`, `integrity`. 기준은 시작 시 리포에서 읽은 매니페스트(설치본에는 매니페스트 없음) |
| AC-001 (4) | PASS(하네스 쪽), 라우터 부분 M4 위임 | `test_unlisted_file_under_installed_claude_dir_fails_job_integrity`, `test_symlink_under_installed_claude_dir_fails_job_integrity` | `.claude/settings.local.json` 추가 → 실패, 사유에 파일명 |
| AC-001 (5) | PASS(하네스 쪽), "실행 1회"는 M4 위임 | `test_restart_restores_tampered_install` | 변조 상태에서 재시작 → 설치본 복구, 목록 밖 파일 제거, 작업 검사 통과, `runs/keep.txt` 그대로 |
| AC-001 보조 | PASS | `test_job_integrity_fails_closed_when_startup_never_ran`, `test_missing_manifest_blocks_install`, `test_malformed_manifest_blocks_install`, `test_listed_file_missing_from_source_blocks_install`, `test_install_replaces_stale_install_contents`, `test_committed_source_matches_committed_manifest`, `test_committed_manifest_covers_instructions_settings_and_whole_skill` | 모두 통과(아래 E2 실행 출력) |
| AC-002 일부(설정 파일) | PASS | `test_committed_settings_deny_reads_outside_harness` | `disableAllHooks: true`, `autoMemoryEnabled: false`, `env.PATH`에 `/usr/bin`·`/bin`, `bypassPermissions` 문자열 없음. argv·cwd 부분은 M3 |
| AC-003 (1)~(5), (6a)~(6f) | PASS 11/11 | 라이브 탐침(아래 "AC-003 라이브 탐침") | 탐침마다 `permission_denials` 정확히 1건, 거부된 입력이 지시한 명령·대상과 일치, 무효 탐침 0건(재실행 0회), 파일 트리 해시 전후 동일, `CANARY_ONLY` 출력 0건 |
| AC-023 일부 | PASS | `git ls-files backend \| grep -E '(^\|/)(\.claude\|CLAUDE\.md)'` (HEAD `1029017`) | 출력 0줄, `grep_exit=1`. AC-023 원문 패턴 `'(^\|/)\.claude/\|(^\|/)CLAUDE\.md$'`도 0줄, exit 1. `test_committed_source_uses_no_claude_names` 통과 |

#### AC-003 라이브 탐침 (설치본 `~/.goose-harness`, design §3.1 argv)

- 설치: `python -c "from backend.services import goose_harness as g; print(g.install_at_startup()); print(g.check_job_integrity())"` → `HarnessStatus(ok=True, reason='installed', harness_dir=PosixPath('/Users/byunjungwon/.goose-harness'))`, `IntegrityResult(ok=True, reason='ok')`. 사전: `~/CLAUDE.md`·`~/CLAUDE.local.md`·`/Users/CLAUDE.md` 없음, `git -C ~ rev-parse` → `not a git repository`.
- 실행기(스크래치 `probe.py`): argv `claude -p <프롬프트> --output-format stream-json --verbose --setting-sources project --settings <H>/.claude/settings.json --strict-mcp-config --permission-mode dontAsk --no-session-persistence --model sonnet`, cwd `<H>`, 환경 변수 허용 목록만, `start_new_session` + 180초 상한(초과 시 `killpg`). 상한 초과 0건. `--dangerously-skip-permissions`·`bypassPermissions` 미사용.
- 카나리: 전용 디렉터리 `$HOME/.goose-canary/canary.txt`(내용 `CANARY_ONLY`, AC-003 Given 그대로; 탐침 종료 후 삭제). 실제 프로젝트 파일·`.env`는 대상이 아님(`../../.env`는 `/Users/.env`로 해석되며 존재하지 않는 경로).
- 무효 판정 규칙(N2): 거부된 `tool_input`이 지시한 명령 문자열(Bash) 또는 같은 대상 경로(Write·Edit·Read)와 같을 때만 거부로 센다. 모델이 나누거나 바꾸면 무효 → 재실행(최대 2회).

P0·P1 (스모크):

```
{"probe": "p0", "rc": 0, "timed_out": false, "wall_s": 3.2, "is_error": false, "tool_uses": [], "permission_denials": [], "canary_in_output": false}
skills ['goose', 'deep-research', 'design', 'design-sync', 'dataviz', 'update-config', 'verify', 'debug', 'code-review', 'simplify', 'batch', 'fewer-permission-prompts', 'doctor', 'loop', 'schedule', 'claude-api', 'workflow-authoring', 'run', 'run-skill-generator', 'plugin-authoring']
agents ['claude', 'Explore', 'general-purpose', 'Plan', 'statusline-setup', 'web-fetch']
mcp []
memory_paths None
cwd /Users/byunjungwon/.goose-harness
apiKeySource none
RESULT False success 'ok' 7622 11228        (is_error, subtype, result, cache_creation, cache_read)
stderr: Ignoring 9 permissions.allow entries from .claude/settings.json: this workspace has not been trusted. …
```

`goose` 있음, MoAI 스킬·에이전트·`moai:*` 명령 없음, `mcp_servers []`. stderr 경고는 M1과 같은 무해한 경고(`--settings` 쪽 allow는 아래 양성 대조로 적용 확인).

양성 대조:

```
{"probe": "pos", … "tool_uses": [Write runs/pos/ok.txt, Bash "python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --help"], "permission_denials": []}
TOOL_RESULT 'File created successfully at: /Users/byunjungwon/.goose-harness/runs/pos/ok.txt …' None
TOOL_RESULT 'usage: render_report.py [-h] --input INPUT [--output-dir OUTPUT_DIR] …' False
{"probe": "pos2", … "tool_uses": [Bash "cat runs/pos/ok.txt"], "permission_denials": []}   TOOL_RESULT 'ok' False
```

음성 탐침 11건(각각 별도 `claude -p`):

```
n6a  Bash  "cat /Users/byunjungwon/.goose-canary/canary.txt"                      denials=1 (command 동일) canary=False
n6b  Bash  "head -1 /Users/byunjungwon/.goose-canary/canary.txt"                  denials=1 (command 동일) canary=False
n6c  Bash  "grep -r CANARY /Users/byunjungwon/.goose-canary"                      denials=1 (command 동일) canary=False
n6d  Bash  "cat ~/.goose-canary/canary.txt"                                       denials=1 (command 동일) canary=False
n6e  Bash  "cat $HOME/.goose-canary/canary.txt"                                   denials=1 (command 동일) canary=False
n6f  Bash  "python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --help; cat /Users/byunjungwon/.goose-canary/canary.txt"   denials=1 (command 동일) canary=False
n1   Bash  "python3 .claude/skills/goose/workflows/../../../runs/x.py"            denials=1 (command 동일) canary=False
n2   Write "/Users/byunjungwon/.goose-harness/probe-outside-runs.txt"             denials=1 (file_path 동일) canary=False
n3   Edit  "/Users/byunjungwon/.goose-harness/.claude/skills/goose/SKILL.md"      denials=1 (file_path 동일) canary=False
n4   Read  "../../.env" → 거부 입력 "/Users/.env"(같은 경로의 절대 표기)          denials=1 canary=False
n5   Bash  "python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --output-dir ../../probe-out"   denials=1 (command 동일) canary=False
```

모든 탐침 `rc 0`, `timed_out false`, `is_error false`. 파일 증거:

```
$ python3 -I treehash.py ~/.goose-harness ~/.goose-canary > neg_before.json ; (11개 탐침) ; … > neg_after.json
added [] / removed [] / changed []
$ ls ~/.goose-harness/probe-outside-runs.txt ~/probe-out → No such file or directory (둘 다)
$ grep -l CANARY_ONLY probes/n*.jsonl probes/n*.stderr probes/p0* probes/pos* | wc -l → 0
$ pgrep -fl "claude -p" → (출력 없음, exit 1)
```

대조 실험(같은 탐침 6a~6f, M1 설정 파일 = 새 거부 규칙 없음, 스크래치 복사 하네스): 6건 모두 `denials=1`, `canary=False`. 즉 `claude` 2.1.303에서는 cwd 밖 경로를 읽는 읽기 전용 Bash가 새 규칙 없이도 자동 허용되지 않았다(M1이 관측한 자동 허용은 cwd 안 경로였다 — `ls runs …`). 새 거부 규칙은 이 버전에서 결과를 바꾸지 않았으므로 **결정적이라고 주장하지 않는다**. 버전이 바뀌어 자동 허용 범위가 넓어질 경우에 대비한 방어선으로 둔다.

사용자 전역 메모리(design §9.1 재관측): 도구 없이 "컨텍스트에 '전역 지침' 또는 '소통 문체' 제목의 사용자 지침이 있으면 그 제목 줄을 인용, 없으면 NONE" → 결과 `'# 전역 지침'`. **`~/.claude/CLAUDE.md`(사용자 전역 지침)가 설치본 세션에 로드된다.** `--setting-sources project`로는 막히지 않는다. M2 범위 밖이라 고치지 않았다(아래 Gaps).

#### E2 — 테스트 수 (기준 대비)

```
$ python -m pytest backend/tests -q -p no:cacheprovider --continue-on-collection-errors   # 기준: HEAD 9535370, 변경 전
38 failed, 183 passed, 63 errors in 37.78s
$ (같은 명령, 변경 후 작업 트리 = 1029017 내용)
38 failed, 214 passed, 1 warning, 63 errors in 38.03s
$ comm -13 baseline_bad.txt after_bad.txt   # 새 실패·오류
(출력 없음)
$ comm -23 baseline_bad.txt after_bad.txt   # 사라진 실패
(출력 없음)
$ python -m pytest backend/tests/test_goose_harness.py backend/tests/test_main_goose_lifespan.py -q -p no:cacheprovider   # HEAD 1029017
31 passed, 1 warning in 0.71s
```

기준 실패·오류 101건은 전부 기존 것이다(대표 원인: `test_ai_report_router_deep_mode.py`가 import 시점에 `my_chart`를 `sys.modules` 스텁으로 바꿔, 뒤에 수집되는 모듈의 `from my_chart.db.weekly import generate_price_db`가 `ImportError (unknown location)`; 같은 파일을 단독 실행하면 통과 — 예: `test_sector_detail_service.py` 단독 `13 passed`). 첫 lifespan 테스트도 같은 오염으로 수집 오류가 났기 때문에, 테스트가 `my_chart*`·`backend*` 항목을 잠시 비우고 실제 모듈을 불러온 뒤 `sys.modules`를 원래대로 되돌리도록 고쳤다(새 오류 0건 확인).

#### E3 — 커버리지

```
$ python -m coverage run --include='backend/services/goose_harness.py' -m pytest backend/tests/test_goose_harness.py -q -p no:cacheprovider
30 passed in 0.13s
$ python -m coverage report -m
backend/services/goose_harness.py     209     24    89%   139, 144, 159-160, 184, 218, 233-238, 246, 275, 288, 312-320
```

89% (기준 85%). 미실행 줄은 교체 중 OSError 되돌리기, 원본 심볼릭 링크, 매니페스트 경로 검사 일부, `build_manifest` 오류 분기다. (`pytest-cov` 플러그인이 venv에 없어 `coverage run`을 썼다.)

#### E4 — 권한 규칙 (AC-003 결과를 낸 최종 설정, 설치본 sha256 `5bf240b6…`)

```json
"allow": ["WebSearch", "WebFetch", "Agent", "Skill", "Read(./**)", "Write(./runs/**)", "Edit(./runs/**)",
          "Bash(python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py:*)",
          "Bash(python3 .claude/skills/goose/workflows/fact-check/scripts/audit_report.py:*)"],
"deny":  ["Write(./.claude/**)", "Edit(./.claude/**)", "Write(./CLAUDE.md)", "Edit(./CLAUDE.md)",
          "Bash(*..*)", "Bash(* /*)", "Bash(*~*)", "Bash(*$*)",
          "Read(../**)", "Read(**/.env)", "Read(**/.env.*)"]
```

- M1 대비 추가: `Bash(* /*)`(공백 뒤 절대 경로), `Bash(*~*)`, `Bash(*$*)`. 제거: 전역 `Glob`·`Grep` 허용(M1 임시 설정에 있었음; `Read(./**)`가 하네스 안 읽기를 덮는다), 설치본에 없는 `goose-manifest.json` 쓰기 거부.
- 위 대조 실험대로 6a~6f 거부는 이 버전에서 기존 규칙만으로도 관측됐다. 새 세 규칙은 방어선이다.
- 부작용: 허용 스크립트를 절대 경로 인자로 부르면(`--input /Users/…`) `Bash(* /*)`에 걸려 거부된다. 하네스 지침 4번이 상대 경로 형식만 쓰게 하고 M1 실제 실행도 상대 경로였다. AC-025 라이브에서 확인 필요.

#### E5 — 리뷰 6회차 잔여(N1~N3) 처리

| 항목 | 처리 | 증거 |
|---|---|---|
| N1 설치본 `.DS_Store` | 작업 시작 검사도 `.DS_Store`를 무시(원본 대조와 같은 제외 목록) | `test_ds_store_under_installed_claude_dir_is_ignored`. 되돌림(아래 E8 M-b) → 이 테스트 FAIL |
| N2 탐침 명령 일치 | 거부된 `tool_input`이 지시 문자열과 같을 때만 거부로 셈. 11건 모두 일치, 무효 0건, 재실행 0회 | 위 탐침 표 |
| N3 리포 안 하네스 경로 | 리포 아래 경로, 리포를 포함하는 상위 경로, 리포 안으로 가는 심볼릭 링크 모두 설치 거부 + 시작 실패 기록 → 작업 검사 `integrity` | `test_harness_dir_inside_repo_is_refused`, `test_harness_dir_that_contains_repo_is_refused`, `test_harness_dir_symlinked_into_repo_is_refused`. 되돌림(E8 M-c) → 3건 FAIL |

#### E8 — RED 증거 (GREEN 전 실패 출력)

설치·무결성 테스트, 모듈 작성 전(HEAD `9535370`):

```
$ python -m pytest backend/tests/test_goose_harness.py -q -p no:cacheprovider
E   FileNotFoundError: [Errno 2] No such file or directory: '/Users/byunjungwon/Dev/my-project-01/my_chart/backend/services/goose_harness.py'
FAILED backend/tests/test_goose_harness.py::test_committed_settings_deny_reads_outside_harness
ERROR backend/tests/test_goose_harness.py::test_matching_source_installs_listed_files_and_preserves_runs
… (28 ERROR)
1 failed, 1 passed, 28 errors in 0.12s
```

lifespan 테스트, `main.py` 연결 줄을 되돌린 상태(구현을 먼저 써서 지우고 테스트부터 다시 진행, 격리 수정 뒤 한 번 더 확인):

```
E       assert 0 == 1
E        +  where 0 = len([])
1 failed, 1 warning in 0.65s
```

대조 단언 되돌림(구현의 핵심 줄을 하나씩 무력화 → 테스트 실행 → 원복, `cmp` → `RESTORED`):

```
== M-a: 닫힌 실패 기록 무시 (2b)
FAILED …::test_missing_manifest_blocks_install
FAILED …::test_startup_source_failure_keeps_old_install_but_fails_every_job
FAILED …::test_harness_dir_inside_repo_is_refused
FAILED …::test_harness_dir_that_contains_repo_is_refused
4 failed, 26 passed
== M-b: 설치본 검사에서 .DS_Store 무시 제거 (N1)
FAILED …::test_ds_store_under_installed_claude_dir_is_ignored
1 failed, 29 passed
== M-c: 리포 경로 겹침 검사 제거 (N3)
FAILED …::test_harness_dir_inside_repo_is_refused
FAILED …::test_harness_dir_that_contains_repo_is_refused
FAILED …::test_harness_dir_symlinked_into_repo_is_refused
3 failed, 27 passed
== M-d: 목록 밖 설치본 .claude 파일 검사 제거 (4)
FAILED …::test_unlisted_file_under_installed_claude_dir_fails_job_integrity
1 failed, 29 passed
== M-e: 목록 밖 원본 파일 무시 (2c)
FAILED …::test_unlisted_source_file_blocks_install
1 failed, 29 passed
RESTORED
```

#### M3 진입 조건

plan M2: "(6a)~(6f) 중 하나라도 하네스 밖 읽기 전용 Bash가 거부되지 않으면 … M3 진입 금지". 관측: 6a~6f 6건 모두 거부, 카나리 노출 0, 파일 변화 0 → **조건 충족**.

#### 관측하지 못한 것 (Gaps)

- AC-001의 라우터 쪽 판정(202 응답, 작업 상태 `error`/`integrity`, `GET /goose/active` → `null`, 쿼터 0, 가짜 명령 호출 0회, (5)의 "실행 1회")은 M4에서 서비스·라우터와 함께 검증한다. M2는 `check_job_integrity()`까지만 시험했다.
- 사용자 전역 `~/.claude/CLAUDE.md`가 하네스 세션에 로드됨을 관측했다(위). 차단 방법은 시험하지 않았다. 사용자 개인 지시(문체 등)가 goose 세션에 섞이는 위험이 남는다 — 오케스트레이터 판단 필요.
- `CLAUDE.local.md`(R5-10) 등 설치본 최상위 기타 파일의 로드 여부는 시험하지 않았다. 작업 검사는 `<H>/.claude/` 아래만 목록 밖 파일을 본다(REQ-001 그대로).
- 새 거부 규칙 3개가 결정적인지: 이 버전에서는 아니었다(대조 실험). 다른 우회 형태(리다이렉트 `cat </경로`, 따옴표 안 경로 `'/…'`, 명령 치환 등)는 탐침하지 않았다.
- 서브에이전트 쪽 음성 탐침은 하지 않았다(acceptance §H, M1과 같음).
- `ruff`가 venv·PATH에 없어 lint를 실행하지 못했다.
- 시작 설치는 동기 파일 I/O로 lifespan에서 실행된다(스킬 34개 파일, 측정상 즉시 끝남). 서버 시작 시간 영향은 재지 않았다.

### M3 실행기 goose_runner

기준: HEAD `1b6d5f8`(시작), 커밋 `4ec3073`(테스트, RED) → `64b862f`(구현). `claude` 2.1.304. 증거 파일: `.moai/state/verify/m3/`(git 미추적).

산출물: `backend/services/goose_runner.py`(신규), `backend/tests/test_goose_runner.py`(신규 51건). 경계(design §8): 실행기는 무결성 검사·쿼터·작업 등록·`runs/{job_id}/` 생성을 하지 않는다. 취소는 `run_goose` 태스크 cancel → 그룹 종료 후 `CancelledError` 재전파이며, 상태 `cancelled`는 M4 작업 서비스가 정한다. §5.2 선택 규칙(`select_report`)은 `empty_output` 분류에 필요해 실행기에 두었고, 복사·`job.json`은 M5 몫이다.

#### E1 — 인수 기준 행렬

명령: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest backend/tests/test_goose_runner.py -v -p no:cacheprovider`(HEAD `64b862f`, 이 트리) → `51 passed, 1 warning in 9.35s`

| AC | 상태 | 테스트 | 관측 출력 |
|---|---|---|---|
| AC-002 | PASS | `test_ac002_argv_and_cwd`(모델 미설정/opus × 하네스 경로 미설정/`/tmp/h2` 4조합), `test_ac002_settings_source_keys`, `test_ac002_subprocess_gets_cwd_and_argv` | `ac002: 6 passed, 0 failed` |
| AC-004 | PASS | `test_ac004_env_allowlist`, `test_ac004_env_only_existing_keys`, `test_ac004_subprocess_env_is_allowlisted`(하위 프로세스 `env` 덤프) | `ac004: 3 passed, 0 failed` |
| AC-005 | PASS | `test_ac005_timeout_kills_whole_group[sigterm]`, `[sigkill-after-grace]`(리더·자식 모두 `trap '' TERM`) — 시간 상한 1초, 유예 0.5초, 시작 후 3초 안에 리더·자식 PID `ProcessLookupError` | `ac005: 2 passed, 0 failed` |
| AC-006 | PASS | `test_ac006_binary_missing`, `test_ac006_auth_failure`(stderr `not logged in`, exit 1), `test_ac006_exit0_without_report_is_empty_output`, `test_ac006_exit7_is_exit_error` | `ac006: 4 passed, 0 failed` |
| AC-012 | PASS | `test_ac012_fixture_stage_sequence`(녹화 196줄 + 알 수 없는 타입 1줄 + 깨진 JSON 1줄, 기대 순서 리터럴 39개), `test_ac012_permission_denied_makes_no_stage`, 경계 사례 16건, `test_ac012_runner_emits_stages_from_stream`(가짜 claude가 녹화를 stdout으로 냄) | `ac012: 19 passed, 0 failed` |

AC-012 기대 순서(테스트에 리터럴로 고정, R5-8): `goose_start` → `plan`×6 → `research_tick`×3 → `fetch_start` → `research_tick` → `fetch_start` → `research_tick`×9 → `fetch_done` → `research_tick` → `fetch_done` → `fetch_start` → `research_tick`×8 → `fetch_done` → `compose` → `render_draft`×2 → `session_end`. 녹화를 줄 단위로 읽어 design §3.5 표에 대응시켜 손으로 도출했다(테스트 안에 줄 번호 주석). `research_tick` 22회(메인 WebSearch 4 + 서브에이전트 WebFetch 18), `fetch_start`·`fetch_done` 각 3회, `render_report.py --help`(125행)·`permission_denied`(119행)는 단계 없음.

추가 시험(AC 밖): 취소 시 그룹 종료와 `CancelledError` 재전파(`test_cancel_kills_group_and_reraises`), 리더 exit 0 후 손자가 stdout 파이프를 쥔 경우 `done` + 손자 종료(`test_leader_exit_with_orphan_holding_pipe_is_not_timeout`), 시간 초과여도 선택 가능한 초안 정보 반환(T10), 심볼릭 링크 리포트 무시, stderr 꼬리 50줄, 4MB 초과 줄 버림, 비동기 콜백.

#### E2 — 테스트 수 (기준 대비)

```
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest backend/tests -q -p no:cacheprovider --continue-on-collection-errors -rfE   # 기준: HEAD 1b6d5f8, 변경 전
38 failed, 214 passed, 1 warning, 63 errors in 37.76s
$ (같은 명령)   # 변경 후, 구현 포함 작업 트리
38 failed, 265 passed, 2 warnings, 63 errors in 46.44s
$ comm -13 baseline_fails.txt after_fails.txt   # FAILED/ERROR 항목 id 정렬 목록(각 101줄) 비교
(출력 없음 — 새 실패 0건, 해소 0건)
```

통과 수 +51 = 새 테스트 51건. 기존 38 failed / 63 errors는 `test_ai_report_router_deep_mode.py`의 `my_chart` 스텁 영향(이미 알려진 기준선)이다.

#### E3 — 커버리지

```
$ python -m coverage run --include='backend/services/goose_runner.py' -m pytest backend/tests/test_goose_runner.py -q -p no:cacheprovider
$ python -m coverage report -m
backend/services/goose_runner.py     261      8    97%   245, 294-295, 316-317, 348, 457-458
```

97%(기준 85%). 미실행 줄은 `PermissionError` 분기(그룹 생존 판정), 4MB 초과 stderr 줄, `ProcessLookupError`가 SIGKILL 직전에 나는 경쟁, 회수 실패 로그다.

#### E4 — 사용자 전역 `~/.claude/CLAUDE.md` 차단 조사 (B2)

방법: `.moai/state/verify/m3/b2probe.py` — cwd `~/.goose-harness`, design §3.1 argv(모델만 `haiku`, 출력 `json`), env는 허용 목록 중 부모에 있는 6개 + 후보 변수, 120초 상한(넘으면 그룹 SIGKILL). 프롬프트: 도구 없이 컨텍스트의 `Contents of <path>` 블록마다 `<path> | <첫 제목 줄>`, 없으면 `NONE`. 설치본 `~/.goose-harness`와 사용자 `~/.claude/CLAUDE.md`는 수정하지 않았다(후보 설정은 검증 폴더의 사본으로 `--settings`에 넘김).

후보는 `claude --help`와 실행 파일 문자열(`strings`)에서 찾았다: 환경 변수 `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, 설정 키 `claudeMdExcludes`. `--bare`는 구독 인증 불가로 금지(design §3.1), `HOME` 변경은 인증 위험으로 시험하지 않음.

```
[P0-control] exit=0 extra_env=[] settings=/Users/byunjungwon/.goose-harness/.claude/settings.json
[P0-control] is_error=False result:
/Users/byunjungwon/.claude/CLAUDE.md | # 전역 지침
/Users/byunjungwon/.goose-harness/CLAUDE.md | # Goose 헤드리스 실행 규칙

[P1-disable-claude-mds] exit=0 extra_env=['CLAUDE_CODE_DISABLE_CLAUDE_MDS'] settings=/Users/byunjungwon/.goose-harness/.claude/settings.json
[P1-disable-claude-mds] is_error=False result:
NONE

[P2-claudeMdExcludes] exit=0 extra_env=[] settings=…/.moai/state/verify/m3/settings_excl.json   # 설치본 설정 + "claudeMdExcludes": ["/Users/byunjungwon/.claude/CLAUDE.md"]
[P2-claudeMdExcludes] is_error=False result:
/Users/byunjungwon/.goose-harness/CLAUDE.md | # Goose 헤드리스 실행 규칙

[P3-claudeMdExcludes-glob] exit=0 extra_env=[] settings=…/.moai/state/verify/m3/settings_excl_glob.json   # 설치본 설정 + "claudeMdExcludes": ["**/.claude/CLAUDE.md"]
[P3-claudeMdExcludes-glob] is_error=False result:
/Users/byunjungwon/.goose-harness/CLAUDE.md | Goose 헤드리스 실행 규칙
$ pgrep -fl "claude -p" → (출력 없음)
```

결론:
- `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`은 전역 지침과 함께 **하네스 `CLAUDE.md`까지 없앤다**(P1 `NONE`). 하네스 규칙(질문 금지 등)이 사라지므로 쓸 수 없다.
- 설정 키 `claudeMdExcludes`는 전역 지침만 빼고 하네스 `CLAUDE.md`는 남긴다. 절대 경로(P2)와 이식 가능한 글롭 `**/.claude/CLAUDE.md`(P3) 둘 다 동작했고 구독 인증도 유지됐다(exit 0, `is_error=False`).
- 이 방법은 design §3.1 argv나 §3.3 환경 변수가 아니라 하네스 설정 파일(추적 원본 `backend/goose_harness_src/claude-settings.json`, design §2.2, REQ-002·AC-002 설정 키, 매니페스트)을 바꿔야 한다. M3 범위(B7)와 SPEC 본문 밖이라 **구현하지 않았고, 차단 보고로 올린다**(오케스트레이터 → manager-spec).
- 관측 근거는 모델의 자기 보고(컨텍스트 블록 인용)다. 기계적 신호는 아니지만 P0 대조군이 두 파일을 정확히 인용했고 P1·P2·P3가 서로 다른 결과를 냈다.

#### E5 — 관측하지 못한 것 (Gaps)과 잔여 위험

- 실제 `claude`로 goose 세션 전체를 돌리지 않았다(B3, 이번 범위 아님). 실행기 배선은 가짜 실행 파일로만 시험했다 — 실제 claude의 stdout·stderr 분리, 종료 코드, 인증 실패 문구가 `stderr`에 나오는지는 AC-025 라이브에서 확인해야 한다. 인증 실패가 stream-json `result`(`is_error`)로만 나오면 `exit_error`로 분류될 수 있다.
- `audit`·`render_final` 단계는 녹화에 없어(design §9.1) 합성 줄로만 시험했다.
- `fetch_done`은 `system/task_notification`을 모두 센다. 녹화에서는 web-fetch 3건과 1:1이었지만, 다른 종류의 백그라운드 작업이 생기면 과다 집계될 수 있다.
- 가짜 claude 시험은 macOS(`/bin/bash`)에서만 했다. 프로세스 그룹 동작은 POSIX 전용이다(Windows 미지원 — 백엔드 실행 환경과 같음).
- 리더 종료 후 드레인 2초는 고정값이다. 정상 종료 직후 큰 출력이 2초 넘게 이어지면 그룹 종료로 잘릴 수 있다(관측 사례 없음).
- `ruff`가 venv·PATH에 없어 lint를 실행하지 못했다.
- `claudeMdExcludes` 적용 시 `--settings`로 넘기는 파일이 프로젝트 설정 파일과 같은 경로일 때도 동작하는지는 사본 경로로만 확인했다(P2·P3는 다른 경로). 반영 후 재탐침 필요.

#### E8 — RED 증거 (GREEN 전 실패 출력)

```
$ python -m pytest backend/tests/test_goose_runner.py -q -p no:cacheprovider   # 구현 모듈 작성 전
E   ModuleNotFoundError: No module named 'backend.services.goose_runner'
1 passed, 1 warning, 49 errors in 0.78s
```
(통과 1건은 기존 설정 원본 파일만 읽는 `test_ac002_settings_source_keys`.)

1차 구현 뒤 추가한 회귀 테스트(리더 exit 0 + 손자가 파이프 보유)의 RED:
```
$ python -m pytest backend/tests/test_goose_runner.py -q -p no:cacheprovider -k orphan
>           assert (result.status, result.error_kind) == ("done", None)
E           AssertionError: assert ('error', 'timeout') == ('done', None)
1 failed, 50 deselected, 1 warning in 20.58s
```
원인: asyncio `Process.wait()`는 파이프가 모두 닫혀야 돌아온다. `returncode` 폴링 + 드레인 후 그룹 종료로 고쳐 GREEN(51 passed).

#### M4 진입 조건

M3 소유 AC 5개(002·004·005·006·012) 자동 시험 PASS, 전체 백엔드 새 실패 0, 커버리지 97%. B2 전역 지침 차단은 SPEC 변경이 필요한 별도 결정으로, M4 진입을 막지 않는다(실행기 인터페이스와 무관한 설정 파일 변경).

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

---

## §F Phase 4 Mode Selection

- 입력: tier L, 범위 약 40파일(신규·수정·삭제), 도메인 4(backend·frontend·하네스 설정·테스트), 언어 Python+TypeScript+markdown, 동시 실행 이득 낮음(코딩 중심).
- 착수 승인(2026-10-19): M1 스파이크만 먼저 실행, GO/NO-GO 보고 후 M2 진입 재확인. SHOULD-FIX R4-1·R4-3·R4-7은 M1 직후 §9 갱신 manager-spec 위임에 묶어 문서에서 수정.

| 모드 | 선택 | 근거 |
|---|---|---|
| direct | 아님 | 다파일·다도메인 구현 |
| serial | **선택** | 코딩 중심 작업, M1 결과가 이후 값을 고정하므로 순차 진행 |
| fanout | 아님 | 연구가 아닌 구현; 쓰기 에이전트 동시 실행 금지 |
| sweep | 아님 | 기계적 일괄 변환 아님 |

Decision: serial (manager-develop, 마일스톤 단위 순차 위임; manager-lead 진입 조건은 충족하나 M1 go/no-go 게이트 때문에 오케스트레이터가 직접 순차 진행)

---

## §G Plan-phase 기록 (Phase SKIP 근거)

**작성자**: manager-spec (plan 단계) · **일자**: 2026-10-19 · **Tier**: L(사용자 확정)

### 산출물

| 파일 | 상태 |
|---|---|
| `research.md` | 작성 — 현재 구조, goose 실행 계약, 격리·작업 분리 근거, 보안 분석, 증거 공백 G1~G9 |
| `plan.md` | 작성 — 결정 D1~D10 + 기술 결정 T1~T9, M1~M7, 파일 목록, 추적표, mx_plan |
| `spec.md` | 작성 — 12필드 frontmatter, REQ 23개(v0.3.0), [DELTA], Exclusions 4개 소절 |
| `acceptance.md` | 작성 — AC 25개(Given/When/Then + 잡아내는 구현), 경계 사례, 품질 게이트, 미검출 목록 |
| `design.md` | 작성 — 구조, 상태 기계, 재생, 저장·서빙, 보안 경계, M1 잠정 목록 |
| `spec-compact.md` | 작성 |
| `progress.md` | 본 파일 |

### SPEC ID 검증 (실행 출력)

```
$ ID="SPEC-AI-REPORT-004"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
PASS
$ ls -d .moai/specs/SPEC-AI-REPORT-004
ls: .moai/specs/SPEC-AI-REPORT-004: No such file or directory   (작성 전, 중복 없음)
```

### Phase 건너뛰기 근거

| Phase | 처리 | 근거 |
|---|---|---|
| Phase 2 (탐색) | 건너뜀 | 같은 세션에서 Explore 에이전트 2개가 현재 기능과 goose 스킬을 조사함. manager-spec은 인용한 file:line을 직접 재확인함(research.md §1.6 명령) |
| Phase 3 (명확화 인터뷰) | 건너뜀 | 명확도 9/10, 기술 키워드 5개 이상(`claude -p`, `--setting-sources`, SSE, CSP sandbox, job_id, stream-json) — 인터뷰 생략 기준 충족. 남은 4건은 `[NEEDS CLARIFICATION]`으로 올려 사용자가 결정(D7~D10) |
| Phase 7 (디자인 방향) | 건너뜀 | UI 변경이 기존 `AiReportModal` 안에 한정됨(라벨 교체, iframe, 초안 배너). 새 시각 디자인 없음 |
| UltraThink | 활성 | 사용자 키워드 |

### 사용자 결정 기록 (2026-10-19)

- D7 초안 표시: 초안을 iframe에 표시 + “최종 감사 미통과 초안” 배너, 기록에 `draft`.
- D8 기존 markdown: `kind: "markdown"`으로 계속 표시.
- D9 기본 모델: `sonnet`.
- D10 동시 실행: 서버 전체 1개, 다른 종목은 429.

### 개정 기록 — plan-audit 1회차 반영 (v0.3.0, 2026-10-19)

- 입력: `.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-1.md` (FAIL 0.78, Tier L 기준 0.85).
- blocking R1-D1~D6 전부 반영, optional R1-D7~D14 전부 반영(거절 0건). 결함별 처리와 기술 결정 T1~T9는 `plan.md §2.3-2.4`.
- 요구사항 24 → 23개(재번호), 인수 기준 25개 유지(재구성).

### 개정 기록 — plan-audit 2회차 반영 (v0.3.1, 2026-10-19)

- 입력: `.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-2.md` (FAIL 0.90, 1회차 결함 14건 해소, 새 결함 N1~N9).
- blocking R2-N1~N4, optional R2-N5~N9 전부 반영(거절 0건). 재번호 없음. 결정 T10 추가. 처리 내역은 `plan.md §2.4`.
- 요구사항 23개, 인수 기준 25개 유지.

### 개정 기록 — plan-audit 3회차 이후 (v0.3.2, 2026-10-19)

- 입력: `.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-3.md` (FAIL 0.91, 새 결함 M1~M5).
- plan-audit 부채: **PASS-WITH-DEBT accepted by user after iteration 3; resolved in v0.3.2 without re-audit; 오케스트레이터 검증 완료(아래 절), 독립 재감사는 run 단계 Phase 1에서 수행(review-4, PASS 0.93).**
  - R3-M1 — `HistoryItem.interrupted` 추가(spec §3 DELTA, REQ-017, design §5.3·§7.1, AC-017).
  - R3-M2 — 사용자 결정: 중단된 작업은 선택 규칙의 전달 상태(`final`/`draft`)를 그대로 유지, 중단 안내는 상태와 상관없이 표시(REQ-014·019, design §4.4·§5.2, plan T10, AC-014 (g), AC-019).
- optional R3-M3~M5 반영(서버 종료 보관 best-effort, design §4.1 문구, plan T1 문구). 재번호 없음, 요구사항 23개·인수 기준 25개 유지.

### 오케스트레이터 검증 — plan-audit 부채 해소 확인 (2026-10-19)

- `moai spec lint .moai/specs/SPEC-AI-REPORT-004/spec.md` → `✓ No findings — all SPEC documents are valid`
- 직접 읽어 확인: spec.md L64(`HistoryItem.interrupted`), L109(REQ-014 상태 유지 + `interrupted: true`), L115(REQ-017), L121(REQ-019 상태 무관 안내), design.md L193·L234·L243·L289·L296, plan.md L47(T10) — R3-M1·R3-M2 규칙이 네 문서에서 일치.
- 잔존 문구 grep(`draft로 나열/표시/기록`, `history … as draft`) → 0건.
- 개수: `grep -cE "^\*\*REQ-AIR4-0[0-9]{2}" spec.md` → 23, `grep -oE "AC-AIR4-0[0-9]{2}" acceptance.md | sort -u | wc -l` → 25.
- 결론: plan-audit 부채 R3-M1·R3-M2 해소 확인. 독립 재감사는 사용자 결정으로 생략(잔여 위험: 수정이 만든 새 모순은 run 단계 Phase 1 plan audit gate에서 다시 걸러질 수 있음).
- 계획 HTML: `.moai/reports/plan-html/SPEC-AI-REPORT-004-plan.html`
- Phase 12(GitHub Issue) 생략: `--issue` 없음. Phase 13: `git-strategy.yaml` `branch_creation.auto_enabled: false` → late-branch, `main`에 커밋.

### 미결 사항

없음. M1 의존 값은 design.md §9에 잠정으로 표시돼 있으며 M1 관측 후 확정한다.

### M1 이후 문서 개정 (v0.4.0)

- 작성: manager-spec, 2026-10-19, 오케스트레이터 재위임(M1 조건부 GO 수용과 사용자 결정 4건). `status`는 `in-progress` 그대로.
- 입력: §E.2 `### M1 스파이크 관측`(측정값·§9 변경 목록 13행·판정), `review-4.md`(R4-1~R4-9).
- 하네스 배치(결정 T11): 리포에는 `.claude`·`CLAUDE.md` 이름이 없는 추적 원본 `backend/goose_harness_src/`와 리포 매니페스트만 두고, 서버 시작 시 원본을 매니페스트로 대조해 `~/.goose-harness`에 설치, 작업 시작마다 설치본을 리포 매니페스트로 검사(목록 밖 `.claude/` 파일 포함). M1 임시 `backend/goose_harness/`는 M2에서 삭제.
- REQ 변경: 001(설치 + 무결성 범위), 002(argv 2개 + 설정 키 3개), 003(하네스 밖 읽기 전용 Bash 거부), 014(R4-2 괄호 삭제), 022(`.claude`·`CLAUDE.md` 추적 금지). AC 변경: 001, 002, 003(탐침 6종), 004, 012, 014(R4-1), 023, 025. 재번호 없음, REQ 23·AC 25.
- design §9를 측정 완료 표로 바꾸고 §9.1에 미관측 항목(최종본·감사 경로, 서브에이전트 권한 상속, `~/.claude/CLAUDE.md` 로드, `-p` Bash `PATH` 원인 등)을 사실이 아닌 공백·위험으로 기록.
- 감사 결함: R4-1·R4-2·R4-3·R4-4·R4-5·R4-7·R4-8 수정, R4-6·R4-9 보류(plan §2.4).
- M2 진입 조건: 최종 위치 재관측(P0·P1)과 AC-003 (6) 재탐침. (6)을 막지 못하면 차단 보고.

### plan-audit 5회차 반영 (v0.4.1)

- 작성: manager-spec, 2026-10-19, 오케스트레이터 재위임. 입력: `review-5.md`(FAIL 0.83, 4회차 0.93보다 하락 → STOP 신호, 단일 수정 패스). `status`는 `in-progress` 그대로.
- 사용자 결정(2026-10-19, R5-1): 닫힌 실패. 서버 시작 원본 대조가 실패하면 실패를 기록하고, 이후 모든 goose 작업은 이전 정상 설치본이 매니페스트와 맞아도 `error`/`integrity`(미실행·미등록·쿼터 미차감). 작업 시작 시 설치본 검사는 그대로 유지.
- REQ 변경: 001(원본 대조 제외 목록 `goose-manifest.json`·`.DS_Store`, 목록 밖 원본 파일 거부, 시작 시 실패 기록과 그에 따른 작업 실패), 003(둘째 절에 `~`·`$HOME` 표기와 허용 명령 뒤 복합 명령 명시), 008(7단계가 시작 시 실패 기록을 포함). AC 변경: 001((1) 제외 파일 조건, (2b), (2c)), 003((6) → (6a)~(6f), 거부 11건). 재번호 없음, REQ 23·AC 25.
- 문구 정정: design §6.1·§9 행과 이 문서 §E.2 표 아래 정정 줄(R5-4, 관측 기록은 그대로), design §2.2 표 제목과 [미관측] 표시(R5-5), research.md 두 곳의 T11 대체 표시(R5-7), acceptance 머리말 AC-025(R5-9).
- 보류: R5-6·R5-8·R5-10(plan §2.4에 권장 처리 기록).
- M2 진입 조건 갱신: AC-003 (6a)~(6f) 재탐침. 하나라도 막지 못하면 차단 보고(M3 진입 금지).

**개정 v0.4.2 (2026-10-20, manager-spec, M3 차단 보고 B2 재위임)**: 사용자 결정에 따라 하네스 설정 키 `claudeMdExcludes: ["**/.claude/CLAUDE.md"]` 반영 — spec REQ-002, acceptance AC-002 설정 파일 줄, spec-compact REQ-002·AC-002 행, design §2.2 설정 키·§9.1 행(해소, 근거 §E.2 `### M3 실행기 goose_runner` E4). `status`는 `in-progress` 그대로. M4 진입 확인: 설치본 설정 파일로 재탐침.
