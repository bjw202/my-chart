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
