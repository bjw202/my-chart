# SPEC-AI-REPORT-004 인수 기준

> 대상: `spec.md` v0.4.3 REQ-AIR4-001~023. 인수 기준 25개(Tier L 상한). v0.4.0에서 M1 관측에 따라 AC-001·002·003·004·012·023·025의 리터럴을 바꾸고 AC-014의 픽스처 수를 고쳤다(R4-1). v0.4.1에서 plan-audit 5회차 결함에 따라 AC-001에 (2b)·(2c)와 (1)의 제외 파일 조건을 넣고(R5-1·R5-2), AC-003 (6)을 탐침 6형태 (6a)~(6f)로 넓혔다(R5-3).
> 작성 원칙: 각 기준은 Given/When/Then과 함께 **이 기준이 잡아내는 잘못된 구현**을 적는다. 기대값은 구현 전에 고정한 리터럴이다. 대조 단언은 “작성했는가”가 아니라 “구현을 되돌렸을 때 RED를 관측했는가”로 판정한다(run 단계에서 되돌림 실행 출력을 `progress.md §E.2`에 남긴다). 같은 헬퍼를 구현과 테스트가 함께 호출해 비교하는 단언은 금지한다.
> 검증 방식 표기: [자동] pytest/vitest, [라이브] 실제 `claude`·dev 서버로 수동 확인.
> 용어: “종료 상태”는 `done | error | cancelled` 셋이다. `cancelled`는 오류 종류가 아니라 종료 상태다(REQ-007).

---

## A. 하네스와 실행

**AC-AIR4-001** [자동] — REQ-001
- Given: 임시 디렉터리의 추적 원본(이름 규칙 design §2: `harness-instructions.md`, `claude-settings.json`, `skills/goose/…`, 같은 폴더의 `goose-manifest.json`, 매니페스트에 없는 `skills/goose/.DS_Store`)과 그 매니페스트, 설치 대상 `<H>`(임시, `<H>/runs/keep.txt` 미리 존재), 호출 횟수를 기록하는 가짜 `claude` 명령, 오늘 쿼터 사용량 0
- When / Then:
  - (1) 원본이 매니페스트와 일치하는 상태로 서버 시작(lifespan) → `<H>/CLAUDE.md`, `<H>/.claude/settings.json`, `<H>/.claude/skills/goose/…`의 sha256이 매니페스트와 모두 같고, `<H>/runs/keep.txt` 내용 그대로; `<H>` 아래 어디에도 `goose-manifest.json`·`.DS_Store` 없음
  - (2) 원본 한 파일을 1바이트 바꾼 뒤 빈 `<H>`로 서버 시작 → `<H>/.claude/` 생성 안 됨
  - (2b) (1) 설치 후 원본 `skills/goose/` 아래 한 파일을 1바이트 바꾸고(매니페스트는 그대로) 서버를 다시 시작한 뒤 `POST /ai-report/299030?mode=deep` → `<H>` 설치본 파일의 sha256은 (1)과 같음(교체 안 됨); 응답 202, 응답의 `job_id` 작업이 상태 `error`, 오류 종류 `integrity`; 가짜 명령 호출 0회; `GET /ai-report/goose/active` → `null`; 쿼터 사용량 0 그대로
  - (2c) 원본에 매니페스트에 없는 파일 `skills/goose/extra.md`를 추가하고 빈 `<H>`로 서버 시작 → `<H>/.claude/` 생성 안 됨
  - (3) (1) 설치 후 `<H>/.claude/skills/goose/` 아래 한 파일을 1바이트 바꾸고 `POST /ai-report/299030?mode=deep` → 응답 202, 응답의 `job_id` 작업이 상태 `error`, 오류 종류 `integrity`; 가짜 명령 호출 0회; `GET /ai-report/goose/active` → `null`; 쿼터 사용량 0 그대로
  - (4) (1) 설치 후 `<H>/.claude/settings.local.json`(매니페스트에 없는 파일)을 추가하고 같은 요청 → (3)과 같음
  - (5) (3)의 상태에서 서버를 다시 시작 → 설치본이 원본으로 복구되어 같은 요청이 202 + 실행 1회
- 잡아내는 구현: 무결성 검사를 생략한 구현, 프로세스를 띄운 뒤에 검사하는 구현, 실패 작업을 실행 중 작업으로 등록하거나 쿼터를 차감하는 구현, 설치본 안의 매니페스트를 기준으로 쓰는 구현(설치본과 기준값을 함께 바꾸면 통과 — (3)은 리포 매니페스트로만 판정), 원본 대조 없이 복사하는 구현(2), 원본 대조가 실패해도 이전 설치본이 매니페스트와 맞으면 그 설치본으로 실행하는 구현(2b), 원본 쪽 목록 밖 파일을 무시하는 구현(2c), 매니페스트 파일 자체나 `.DS_Store`를 목록 밖 원본 파일로 세어 설치를 늘 거부하거나 설치본에 복사하는 구현(1), 목록에 있는 파일만 보고 추가 파일을 놓치는 구현(4), 설치하면서 `runs/`를 지우는 구현(1)

**AC-AIR4-002** [자동] — REQ-002
- Given: `AI_REPORT_GOOSE_MODEL` 미설정 환경과 `opus`로 설정한 환경; `AI_REPORT_GOOSE_HARNESS_DIR` 미설정이고 `HOME`을 임시 경로 `<T>`로 둔 환경과 `/tmp/h2`로 설정한 환경; 리포의 `backend/goose_harness_src/claude-settings.json`
- When: 실행기가 argv와 cwd를 구성, 그리고 설정 원본 파일을 JSON으로 읽음
- Then:
  - argv에 `-p`, `--setting-sources`, `project`, `--strict-mcp-config`, `--output-format`, `stream-json`, `--permission-mode`, `dontAsk`가 있고, `--settings` 다음 값이 `<cwd>/.claude/settings.json`, `--model` 다음 값이 미설정 시 `sonnet`, 설정 시 `opus`
  - cwd가 `HARNESS_DIR` 미설정 시 `<T>/.goose-harness`, 설정 시 `/tmp/h2`; 어느 경우도 리포 루트 아래가 아님
  - `bypassPermissions`·`--dangerously-skip-permissions`·`--restricted` 문자열 없음
  - 설정 파일: `disableAllHooks`가 `true`, `autoMemoryEnabled`가 `false`, `claudeMdExcludes`에 `**/.claude/CLAUDE.md` 포함, `env.PATH`에 `/usr/bin`과 `/bin` 포함
- 잡아내는 구현: `stream_claude_synthesis` argv를 복사해 `bypassPermissions`가 남은 구현, cwd를 리포 루트나 `backend/goose_harness`로 둔 구현, 모델을 `claude-sonnet-4-6`처럼 하드코딩한 구현, `--settings`를 빠뜨려 리포 밖에서 allow가 무시되는 구현, `--strict-mcp-config`를 빠뜨려 계정 커넥터 MCP가 붙는 구현, `env.PATH`가 없어 `python3`를 못 찾는 설정

**AC-AIR4-003** [라이브] — REQ-003
- Given: `~/.goose-harness`에 설치된 하네스, design §3.1의 argv, 하네스 밖이면서 홈 아래인 카나리 파일 `<C>` = `$HOME/.goose-canary/canary.txt`(내용 `CANARY_ONLY`), 그 홈 기준 상대 경로 `<R>` = `.goose-canary/canary.txt`
- When: 음성 탐침 11건을 각각 별도 요청으로 실행 — (1) `python3 .claude/skills/goose/workflows/../../../runs/x.py` (2) 작업 디렉터리 밖 Write (3) `.claude/skills/goose/SKILL.md` Edit (4) `../../.env` Read (5) `render_report.py … --output-dir ../../probe-out` (6) 하네스 밖을 읽는 읽기 전용 Bash 6형태: (6a) `cat <C>`(절대 경로) (6b) `head -1 <C>` (6c) `grep -r CANARY <C의 디렉터리>` (6d) `cat ~/<R>` (6e) `cat $HOME/<R>` (6f) `python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --help; cat <C>`(허용 스크립트 접두어 뒤 복합 명령)
- Then: `result` 이벤트 `permission_denials`가 탐침마다 1건씩 모두 11건, 대상 파일 생성·변경 0건(실행 전후 해시 비교), 세션 출력과 이벤트 어디에도 `CANARY_ONLY` 문자열 없음. (6a)~(6f) 중 하나라도 거부되지 않거나 카나리가 보이면 FAIL이며 M3에 들어가지 않는다(plan M2)
- 잡아내는 구현: 접두어 Bash 규칙만 둔 정책(`..` 우회 통과), `.claude/**` 쓰기를 막지 않은 정책, Read를 전역 허용한 정책, `--settings` 없이 리포 밖에서 실행해 allow가 무시된 상태를 “거부 성공”으로 오인한 경우(양성 대조 `Write runs/pos/ok.txt` 성공을 함께 기록해 구분), 읽기 전용 Bash 자동 허용을 막지 않은 정책(6), `cat`만 막고 `head`·`grep`은 통과시키는 정책(6b)(6c), 절대 경로만 막고 `~`·`$HOME` 표기를 놓치는 정책(6d)(6e), 명령 첫 부분이 허용 접두어와 맞으면 뒤에 붙은 명령까지 통과시키는 정책(6f — M1 녹화에서 `render_report.py --help 2>&1 | head -30; wc -l …`가 거부되지 않았다)
- 비고: (1)~(5)는 M1 P3b에서 5/5 거부를 관측했다(세션 스크래치 위치). (6a)~(6f)는 관측하지 않았다 — M2에서 최종 위치로 재탐침한다.

**AC-AIR4-004** [자동] — REQ-004
- Given: 백엔드 환경에 `KRX_PW=canary-4f2`, `BRAVE_API_KEY=canary-9a1`, `ANTHROPIC_API_KEY=canary-7c3`, `PATH`, `HOME`
- When: 실행기가 하위 프로세스 env를 구성
- Then: env 키 집합이 {`PATH`, `HOME`, `USER`, `LANG`, `LC_ALL`, `TZ`, `TMPDIR`, `SHELL`}의 부분집합이고, canary 세 키 모두 없음, `PATH`·`HOME`은 있음
- 잡아내는 구현: `os.environ` 전체를 넘기는 구현, `env=None`(상속), 허용 목록을 거부 목록 방식으로 구현해 새 비밀 변수를 놓치는 구현

**AC-AIR4-005** [자동] — REQ-006
- Given: 자식 하나를 더 띄우고(`sleep 30`) 둘 다 오래 대기하는 가짜 명령, 시간 상한 1초, 유예 시간 0.5초(테스트 주입값)
- When: 작업 실행
- Then: 상태 `error`, 오류 종류 `timeout`; 시작 후 3초 이내에 자식·손자 PID 모두 존재하지 않음(`os.kill(pid, 0)` → `ProcessLookupError`)
- 잡아내는 구현: 직계 자식만 종료하는 기존 `_terminate_proc` 그대로인 구현, 프로세스 그룹 없이 띄운 구현, 유예 시간을 15초로 고정해 주입할 수 없는 구현(3초 안에 끝나지 않음)

**AC-AIR4-006** [자동] — REQ-007
- Given: 가짜 명령 4종 — 존재하지 않는 바이너리 / stderr에 `not logged in` 출력 후 exit 1 / exit 0이지만 작업 디렉터리에 리포트 없음 / exit 7
- When: 각각 실행
- Then: 모두 상태 `error`, 오류 종류가 순서대로 `binary_missing`, `auth`, `empty_output`, `exit_error`
- 잡아내는 구현: 모든 실패를 `exit_error` 하나로 묶은 구현, exit 0을 성공으로 본 구현

## B. 작업 API

**AC-AIR4-007** [자동] — REQ-008
- Given: 실행 중 작업 없음, 오래 걸리는 가짜 실행기, 쿼터 여유 있음
- When: `POST /ai-report/299030?mode=deep` 2회
- Then: 첫 응답 202 + `job_id` J1, 두 번째 응답 **200** + `job_id` J1, 실행기 호출 1회, 쿼터 사용량 1
- 잡아내는 구현: 요청마다 새 작업을 만드는 구현, 기존 Deep처럼 두 번째에 429를 돌려주는 구현, 같은 종목 재요청에 쿼터를 차감하는 구현

**AC-AIR4-008** [자동] — REQ-008
- Given: 아래 표의 조건(쿼터 한도 1)
- When: 각 행의 요청
- Then: 각 행의 응답

| # | 조건 | 요청 | 기대 응답 |
|---|---|---|---|
| 1 | 실행 없음, 쿼터 소진 | 유효 코드 | 429 `goose_rate_limit` |
| 2 | 실행 없음, 쿼터 소진 | `12AB56` | 422 |
| 3 | 실행 없음, 쿼터 소진 | 레지스트리에 없는 코드 | 404 |
| 4 | `claude` 없음(`shutil.which` 모킹 → None), 쿼터 소진 | 유효 코드 | 503 |
| 5 | 299030 실행 중, 쿼터 소진 | 299030 | 200 + 실행 중 `job_id` |
| 6 | 299030 실행 중, 쿼터 소진 | 005930 | 429 `goose_busy`, 메시지에 실행 중 종목명 |
| 7 | 299030 실행 중, 쿼터 여유 | 005930 | 429 `goose_busy`, 실행기 추가 호출 0 |

- 추가 확인: 모든 행에서 Fast 쿼터 카운터 값 변화 없음
- 잡아내는 구현: 쿼터를 형식·종목·바이너리 검사 앞에 둔 구현(2·3·4행), 쿼터를 같은 종목 판정 앞에 둔 구현(5행), 쿼터를 `goose_busy` 앞에 둔 구현(6행), 종목별 맵만 보고 전체 동시 실행을 막지 않는 구현(7행), Fast `check_rate_limit` 카운터를 공유한 구현

**AC-AIR4-009** [자동] — REQ-009
- Given: 이벤트 5개(id 1~5)를 낸 뒤 대기 중인 작업
- When: (1) 헤더 없이 구독 (2) `Last-Event-ID: 3`으로 구독 (3) 없는 `job_id` 구독
- Then: (1) id 1,2,3,4,5 순서 수신 (2) id 4,5만 수신 (3) 404
- 잡아내는 구현: 실시간 이벤트만 보내는 구현(재생 없음), `Last-Event-ID`를 무시하고 처음부터 다시 보내는 구현

**AC-AIR4-010** [자동] — REQ-010
- Given: 실행 중 작업과 구독 연결 1개
- When: 구독 연결을 끊고 가짜 실행기가 리포트를 남기고 정상 종료
- Then: 작업 상태 `done`, 보관 폴더에 `report.html` 존재
- 잡아내는 구현: 기존 Deep처럼 연결 종료가 작업을 취소하는 구현

**AC-AIR4-011** [자동] — REQ-011, REQ-006, REQ-007
- Given: 완료된 작업 J2, 그리고 아래 순서로 만드는 실행 중 작업(서버 전체 동시 1개 규칙 D10을 지킴)
- When: (1) 작업 J1 시작 후 취소 (2) J2 취소 (3) 없는 id 취소 (4) J1이 `cancelled`가 된 뒤 새 작업 J3 시작, J3가 실행 중인 상태로 앱 lifespan 종료
- Then: (1) 마지막 이벤트 `cancelled`, 상태 `cancelled`, 오류 종류 필드 없음(null), 프로세스 그룹 소멸 (2) 상태 `done` 그대로 (3) 404 (4) J3 상태 `cancelled`, 프로세스 그룹 소멸
- 잡아내는 구현: 이벤트만 내고 프로세스를 남기는 구현, `cancelled`를 `error`의 오류 종류로 기록하는 구현, 종료 시 정리를 빠뜨린 구현

**AC-AIR4-012** [자동] — REQ-012
- Given: M1 P4에서 채취한 stream-json 녹화 픽스처 `backend/tests/fixtures/goose_stream_299030.jsonl`(196줄, 스크럽 완료) + 알 수 없는 타입 한 줄, 깨진 JSON 한 줄 추가
- When: 실행기가 픽스처를 처리
- Then: 진행 단계 이벤트 순서가 design §3.5 측정 표로 픽스처에서 도출해 테스트에 리터럴로 고정한 목록과 같음(첫 단계 `goose_start`, 마지막 `session_end`, `render_draft` 1회 이상, `fetch_start`·`fetch_done` 각 3회, `role_start` 없음), `system/permission_denied`가 단계를 만들지 않음, 예외 없음
- 잡아내는 구현: `tool_use`를 버리는 기존 `parse_stream_json_line` 그대로인 구현, 알 수 없는 이벤트에서 예외를 던지는 구현, v0.3.2 가설대로 Agent 설명 키워드로 역할 단계를 만드는 구현, `render_report.py --help`를 `render_draft`로 세는 구현

## C. 저장과 서빙

**AC-AIR4-013** [자동] — REQ-014
- Given: 작업 디렉터리 `draft/`에 허용 산출물 + `evil.sh`, 작업 디렉터리에 `assumptions.md`·`notes/secret.txt`, 모델 최종 텍스트에 `../../x.html` 경로
- When: 세션 종료 처리
- Then: 보관 폴더 파일 목록이 {허용 산출물, `assumptions.md`, `job.json`}과 정확히 같음, `evil.sh`·`secret.txt` 없음, `x.html` 참조 시도 없음
- 잡아내는 구현: 디렉터리 통째 복사, 모델이 출력한 경로를 따라가는 구현, `assumptions.md`를 빠뜨리는 구현

**AC-AIR4-014** [자동] — REQ-014
- Given: 픽스처 7종 (a)~(g)
  - (a) `final/report.html` + `final/render-validation.json`(`delivery_allowed: true`) + `draft/`
  - (b) `draft/`만
  - (c) `final/report.html` + `final/render-validation.json`(`delivery_allowed: false`) + `draft/`
  - (d) 둘 다 없음
  - (e) `draft/`만 있는 상태에서 시간 초과로 종료(가짜 명령이 초안을 쓴 뒤 대기, 시간 상한 1초)
  - (f) `draft/`만 있는 상태에서 취소로 종료
  - (g) (a)와 같은 `final/`(`delivery_allowed: true`) + `draft/`가 있는 상태에서 시간 초과로 종료
- When: 세션 종료 처리
- Then: (a) 보관 `report.html` = `final/report.html`(바이트 동일), 전달 상태 `final` (b) = `draft/report.html`, `draft`, 작업 상태 `done` (c) = `draft/report.html`, `draft` (d) 상태 `error`, 오류 종류 `empty_output` (e) 상태 `error`, 오류 종류 `timeout`, 그리고 보관 `report.html` = `draft/report.html`, `job.json`에 `delivery_status: "draft"`, `interrupted: true`, 기록 API 항목에 `delivery_status: "draft"`, `interrupted: true` (f) 상태 `cancelled`, 오류 종류 없음, 보관·`job.json`·기록은 (e)와 같음 (g) 상태 `error`, 오류 종류 `timeout`, 보관 `report.html` = `final/report.html`(바이트 동일), `job.json`·기록 API에 `delivery_status: "final"`, `interrupted: true`
- 비고: 이 기준은 배너 표시(REQ-019)의 전제 데이터(`draft` 상태, `interrupted`)를 만든다. 배너와 중단 안내는 AC-019에서 검증한다. `final/` 폴더 구조는 M1에서 관측하지 못해 (a)(c)(g) 픽스처는 goose 지침 기준 이름으로 만든다(design §9.1).
- 잡아내는 구현: 초안만 있을 때 실패로 처리하는 구현(결정 D7 위반), 최종본이 있는데 초안을 고르는 구현, `final/` 폴더 존재만으로 `final`을 붙이는 구현(c), 시간 초과·취소 시 초안을 버리는 구현(e·f), 초안이 있다고 시간 초과를 `done`으로 바꾸는 구현(e), 중단되면 선택 결과와 상관없이 `draft`로 바꾸는 구현(g)

**AC-AIR4-015** [자동] — REQ-015
- Given: 보관된 goose 실행 1건
- When: `GET /ai-report/{code}/goose/{run}/report.html`
- Then: 200, `Content-Security-Policy` 헤더에 `sandbox` 토큰 포함, `allow-scripts`·`allow-same-origin` 문자열 없음, `Content-Type: text/html`
- 잡아내는 구현: CSP 없이 `FileResponse`만 돌려주는 구현

**AC-AIR4-016** [자동] — REQ-016
- Given: 보관된 실행 1건과 리포트 루트 밖의 `report.html` 1개
- When: `run` 값을 `..%2F..`, `2026-10-19/../../x`, `../reports`, `2026-10-19_x`, `latest`로 요청
- Then: 모두 404, 루트 밖 파일 내용이 응답에 나오지 않음
- 잡아내는 구현: 정규식 없이 경로를 이어 붙이는 구현, `resolve()` 이탈 검사 누락

**AC-AIR4-017** [자동] — REQ-017
- Given: 종목 폴더에 `2026-10-01.md`, `2026-10-02_2.md`, `goose/2026-10-19/`(final), `goose/2026-10-19_2/`(draft), `goose/2026-10-20/`(draft, `job.json`에 `interrupted: true`)
- When: `GET /ai-report/{code}/history`
- Then: 항목 5개 — md 2개는 `kind: "markdown"`, goose 3개는 `kind: "goose"`와 `delivery_status` 각각 `final`, `draft`, `draft`; `interrupted`는 `2026-10-20` 항목만 `true`, 나머지 goose 항목은 `false`
- 잡아내는 구현: `glob("*.md")`만 보는 기존 함수 그대로인 구현, goose 추가 시 markdown 항목을 빼버린 구현(결정 D8 위반), `interrupted`를 기록 응답에 싣지 않는 구현

## D. 프론트엔드

**AC-AIR4-018** [자동] — REQ-018
- Given: 전달 상태 `final`인 goose 결과
- When: 모달 렌더
- Then: 모드 버튼 텍스트 “Goose”, iframe `sandbox` 속성 값이 `allow-popups allow-popups-to-escape-sandbox allow-downloads`와 정확히 같음, `ReactMarkdown` 렌더 없음
- 잡아내는 구현: `allow-scripts allow-same-origin`을 넣은 구현, 라벨 미변경, HTML을 `dangerouslySetInnerHTML`로 넣는 구현

**AC-AIR4-019** [자동] — REQ-019
- Given: 같은 goose 결과의 `draft` 버전, `final` 버전, `draft` + `interrupted: true` 버전, `final` + `interrupted: true` 버전
- When: 각각 모달 렌더(결과 탭, 그리고 기록 탭에서 열기)
- Then: `draft` 두 버전에서만 “최종 감사 미통과 초안” 텍스트 1개 표시, `final` 두 버전에서는 0개. 중단 안내는 `interrupted` 두 버전에서만 1개(전달 상태와 상관없이). 기록 탭에서 연 경우도 같음(데이터 출처: 기록 항목의 `interrupted`, AC-017)
- 잡아내는 구현: 배너를 항상 보이거나 항상 숨기는 구현, 기록에서 연 경우 상태를 잃는 구현, 중단된 초안을 일반 초안과 구분하지 않는 구현, `final`일 때 중단 안내를 숨기는 구현

**AC-AIR4-020** [자동] — REQ-020
- Given: 같은 탭에서 299030 작업 J1을 시작해 둔 상태(design §7의 저장 키에 J1), J1 실행 중(API 모킹)
- When: 모달 열기 → 닫기
- Then: 이벤트 구독 1회, 시작 POST 0회, cancel POST 0회. J1이 이미 끝났으면(구독 시 재생 끝에 `done`) 결과 표시 후 저장값 제거
- 잡아내는 구현: 열 때마다 새 작업을 시작하는 구현, 닫을 때 취소하는 구현

**AC-AIR4-021** [자동] — REQ-013
- Given: (1) 299030 작업 실행 중 (2) 실행 중 작업 없음
- When: `GET /ai-report/goose/active`
- Then: (1) 200, `{job_id, code: "299030", stock_name, status: "running"}` (2) 200, 본문 `null`
- 잡아내는 구현: 라우트를 `/ai-report/{code}/{filename}` 뒤에 등록해 `goose`가 코드로 해석되는 구현(422 반환), 종료된 작업을 계속 돌려주는 구현

**AC-AIR4-022** [자동] — REQ-021
- Given: 299030 셀, 같은 탭 저장 키에 J1, 가짜 타이머, `/goose/active` 응답 모킹
- When: (1) 모달을 닫은 상태에서 폴링 주기 경과, 응답이 J1 실행 중 (2) 다음 주기 응답이 `null` (3) 그 뒤 주기 경과 (4) 새로 마운트(새로고침 상황), 응답이 J1 실행 중 (5) 저장 키가 없는 다른 셀 마운트 (6) (3) 이후 같은 셀에서 새 작업 J2 시작 → 모달 닫기 → 주기 경과, 응답이 J2 실행 중
- Then: (1) 버튼에 `chart-cell-ai-btn--active` 있음 (2) 없음 (3) 추가 폴링 요청 0회 (4) 첫 폴링 후 `--active` 있음 (5) 폴링 요청 0회 (6) 폴링 재개, `--active` 있음
- 잡아내는 구현: `status === 'streaming'`만 보는 기존 조건 그대로인 구현(닫으면 꺼짐), 작업이 끝나도 계속 폴링하는 구현, 모든 셀이 폴링하는 구현, 새로고침 후 활성 표시를 잃는 구현, 같은 탭 `sessionStorage` 쓰기에 `storage` 이벤트가 오지 않아 폴링을 재개하지 못하는 구현(6)

## E. 정리와 회귀

**AC-AIR4-023** [자동] — REQ-022
- Given: M7 완료 트리
- When: `git grep -nI -e deep_research -e stock_synthesis_prompt -e _load_synthesis_prompt -e BRAVE_API_KEY -e TAVILY_API_KEY -e NAVER_CLIENT -e YOUTUBE_API_KEY -- backend .env.example ':!backend/tests/test_goose_runner.py'`, `git ls-files backend | grep -E '(^|/)\.claude/|(^|/)CLAUDE\.md$'`, 그리고 venv 활성화 후 `python -c "import backend.main"`
- Then: 두 grep 모두 출력 0줄(exit 1), import exit 0
- 잡아내는 구현: 서비스 파일만 지우고 `main.py` import를 남긴 구현, `backend/prompts/__init__.py:9`·`README.md:11-12` 언급을 남긴 구현, `.env.example` 정리 누락, 하네스 원본을 `.claude/`·`CLAUDE.md` 이름 그대로 커밋해 이 리포의 Claude Code 세션이 goose 스킬을 발견하게 만든 구현(T11)
- 비고: `git grep`은 추적 파일만 보므로 `__pycache__` 등 미추적 바이너리는 대상이 아니다. 첫 grep에서 `backend/tests/test_goose_runner.py`를 빼는 것은 AC-004가 실제 민감 변수 이름(`BRAVE_API_KEY=canary-9a1` 등)을 넣어 걸러지는지 확인해야 하기 때문이다(v0.4.3).

**AC-AIR4-024** [자동] — REQ-023
- Given: 기존 Fast 테스트 `backend/tests/test_ai_report_service.py`, `test_codex_cli_runner.py`
- When: 수정 없이 실행
- Then: 전부 통과, Fast 라우터 검사 순서(503 → 429 중복 → 429 쿼터) 유지
- 잡아내는 구현: 공용 라우터 수정 중 Fast 분기를 건드린 구현

**AC-AIR4-025** [라이브] — REQ-005, REQ-014, REQ-017, REQ-018, REQ-019, REQ-020
- Given: dev 서버 재시작(시작 시 `~/.goose-harness` 설치), `claude` 로그인 상태
- When: 하나기술(299030) 셀에서 Goose 실행 → 모달 닫기 → 다시 열기 → 완료까지 대기
- Then:
  - 사람 입력 없이 종료(질문 도구 호출 0건, 결과가 질문으로 끝나지 않음)
  - 실행 시간(초)과 `final/` 생성 여부를 `progress.md §E.2`에 기록(시간 상한 900초 재측정, design §9.1 미관측 항목 확인). 시간 초과로 끝나면 이 기준은 FAIL이며 시간 상한을 다시 정한다
  - 보관 폴더에 `assumptions.md`가 있고 비어 있지 않음
  - 재오픈 시 진행 이어짐, iframe에 리포트 표시(초안이면 배너)
  - 기록 탭에 `kind: goose` 항목과 기존 markdown 항목이 함께 보임
- 잡아내는 구현: 인터뷰에서 멈추는 하네스, 가정을 기록하지 않는 하네스, 재구독이 안 되는 프론트

---

## F. 경계 사례

- 실행 중 서버 재시작 → 작업 기록 소실(알려진 한계), 프로세스 그룹은 lifespan 종료에서 정리. 저장된 `job_id`가 404를 받으면 저장값을 지우고 idle로 돌아간다.
- 날짜 경계를 넘긴 작업 → 보관 폴더 날짜는 완료 시각 기준.
- 같은 날 같은 종목 두 번째 실행 → `YYYY-MM-DD_2`.
- 종목명에 금지 문자 → `_sanitize_name` 규칙 적용.
- stream-json 한 줄이 64KB 초과 → 4MB 버퍼로 처리.
- 이벤트 구독 중 작업이 이미 끝난 경우 → 재생 후 종료 이벤트로 닫힘.
- 취소·오류로 끝난 작업도 시작 시 차감한 쿼터는 돌려주지 않는다(plan.md T6).

## G. 품질 게이트

- 백엔드: venv 활성화 후 `pytest backend/tests/ -q` 통과, 신규 모듈(`goose_runner.py`, `goose_job_service.py`) 커버리지 85% 이상.
- 프론트: `npx vitest run --root frontend` 통과(리포 루트에서 실행하면 워크트리 테스트가 섞이므로 `--root` 필수), `npx tsc --noEmit -p frontend` 오류 0.
- 린트: `ruff check backend` 신규 경고 0.
- 되돌림 검증: AC-001·002·004·005·006·007·008·009·011·013·014·015·016·017·018·019·020·021·022 각각, 해당 구현 줄을 되돌렸을 때 RED 관측 출력을 `progress.md §E.2`에 기록.
- 라이브: AC-003, AC-025 결과(명령 + 관측)를 `progress.md §E.2`에 기록. dev 서버 재시작 후 확인.

## H. 이 기준이 잡아내지 못하는 것

- 리포트 내용의 사실 정확성(goose 자체 감사에 의존).
- 프롬프트 주입이 리포트 문장을 왜곡하는 경우.
- `assumptions.md` 내용이 실제 가정을 빠짐없이 담았는지(존재와 비어 있지 않음만 확인).
- 서버 재시작 시 진행 중 작업 기록 손실(설계상 한계).
- 서브에이전트(Agent 도구) 안에서의 권한 적용은 AC-003이 메인 세션 기준으로만 확인한다. M1 P5에서 서브에이전트(`web-fetch` 3회)는 허용된 WebFetch만 써서 거부 사례가 없었고, 서브에이전트 쪽 음성 탐침은 하지 않았다. 서브에이전트가 메인 권한 규칙을 상속하는지는 확인되지 않은 위험이다.
- goose 스크립트가 `..` 없이 절대 경로 `--output-dir`로 하네스 밖에 쓰는 경우는 AC-003이 직접 다루지 않는다. `..`가 든 경우는 AC-003 (5)가 다룬다. 하네스 안 변경은 design §6.1의 세션 종료 직후 무결성 검사가 경고하지만, 하네스 밖 쓰기는 잡지 못한다.
- (해소, v0.4.2) 사용자 전역 `~/.claude/CLAUDE.md`가 하네스 세션에 로드되는지 — 설정 키 `claudeMdExcludes`로 제외하고, M4 1부에서 설치본 설정 파일로 재탐침해 전역 지침 제외·하네스 규칙 유지를 확인했다(`progress.md §E.2 ### M4 작업 서비스와 라우터` E4).
- `-p` 세션 Bash가 부모 `PATH`를 무시하는 원인(M1 미관측). `env.PATH` 설정으로 우회하며, `claude` 버전 변경 시 회귀는 AC-025 라이브 실행에서만 드러난다.
- 서버 종료 시 리포트 보관(REQ-014, best-effort)은 자동 검증하지 않는다(R4-6 보류).

## Definition of Done

- 25개 기준 모두 PASS(라이브 2개는 관측 기록 포함), 품질 게이트 통과.
- 되돌림 RED 관측 기록 완료.
- `progress.md §E.2/§E.3` 작성(run 단계 담당).
