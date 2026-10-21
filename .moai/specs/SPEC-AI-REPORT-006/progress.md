# SPEC-AI-REPORT-006 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_revised_at: 2026-10-21 (v0.3.2, 3차 델타 검사 N17·N18 반영 — 소형 텍스트 패치. 앞서 v0.3.1은 3차 감사 PASS-WITH-DEBT 조건 N11~N16 반영)
- plan_status: draft (v0.3.2). 3차 델타 검사 보고서 `.moai/reports/t18/plan-audit-iter3-delta.md`(N17·N18). 3차 감사 보고서 `.moai/reports/t18/plan-audit-iter3.md`(결함 N11~N16). 감사 보고서: 1차 `.moai/reports/t18/plan-audit.md`(결함 D1~D14), 2차 `.moai/reports/t18/plan-audit-iter2.md`(결함 N1~N10)
- artifacts: spec.md, plan.md, acceptance.md, design.md, research.md, progress.md (Tier L)
- counts: REQ 20개(REQ-AIR6-001~020), AC 22개(AC-AIR6-001~022). v0.3.0·v0.3.1·v0.3.2에서 개수 변동 없음(재계산 출력: `.moai/state/verify/t18-plan3/trace.py`)
- tier_rationale: Tier L — 새 서브시스템(브라우저 캡처) + 두 번째 `claude -p` 세션 + 전달 판정 변경 + 하네스 지침 + 프론트, 마일스톤 6개, 변경·신규 파일 약 20개
- needs_clarification: 0건. 구 2건은 운영자 결정(2026-10-21)으로 해소 — spec.md D7, plan.md T9에 결정으로 기록 (지원 브라우저 = Playwright 캐시의 chrome-headless-shell만, 외부 네트워크 전면 차단)
- probe_evidence: `.moai/state/verify/t18-plan/`(v0.1.0), `.moai/state/verify/t18-plan2/`(v0.2.0), `.moai/state/verify/t18-plan3/`(v0.3.0: `trace.py`와 그 출력) — 모두 git 무시 경로. v0.3.0에서 추가한 코드베이스·환경 주장은 research P32(대소문자 비구분 경로)·P33(`render_report.py --final`의 출력 파일)
- baseline: goose 백엔드 테스트 `267 passed, 214 deselected` (research P17, v0.1.0 측정; v0.2.0·v0.3.0에서 재실행하지 않음, 2차 감사자가 같은 값을 재관측); 라이브 실행 `a5becbb9…`의 감사 결함 10개 중 대상 8개 발생(research P2·P3)
- gaps: research §4 G1·G3~G15 (G1이 M1 GO/NO-GO 조건, G2는 범위 밖으로 종결). v0.3.0 신규: G13(`final/` 출처 미검증), G14(영수증 제거·교체 이중 실패), G15(`audit-review.json` 사후 변경 미탐지)
- lint: v0.1.0에서 `moai spec lint --strict --json`은 SPEC-AI-REPORT-006 대상 0건이었다. v0.2.0·v0.3.0 개정본에 대해서는 **재실행하지 않았다**(미검증)
- id_check: `[[ "SPEC-AI-REPORT-006" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` → `PASS`(v0.1.0 기록; ID 불변)
- 2차 감사 결함 처리 요약(v0.3.0): N1·N2·N3 수정(필수), N4 Gap(G13), N5·N6·N7·N8·N9 수정, N10 (a)(c)(e) 수정·(b) 안내 문구로 완화·(d) 기각(G15). 위치는 HISTORY 0.3.0 행과 반환 보고
- 3차 감사 조건 처리 요약(v0.3.1): N11 수정(읽기 보호 목록에 16 추가), N12 수정(영수증 사실을 인자로 받는 조건 코어 + 디스크 래퍼), N13 수정(세션 전 `audit-review.json`·`final/` 삭제, AC-014 (11)~(13)), N14 수정(스냅샷 재귀·상대 경로, AC-014 (6b)), N15 수정(REQ-020·AC-019), N16 2단계 확장(plan.md 병합 의무 행). 신규 프로브: research P34(1차 세션 그룹 정리), P35(`Read(./**)` 허용·`Read(../**)` 거부). 읽기 보호 목록 모델 출력: `.moai/state/verify/t18-plan3/guard_model.py`(구현이 아니라 가드 문구의 문자적 모델)
- 알려진 불일치: SPEC-AI-REPORT-005 spec.md §5는 화면 확인을 "카드 t17"이 다룬다고 적었다. 이 카드는 t18이며 내용은 005가 예고한 범위와 같다. 005 문서는 수정하지 않았다

## §E.2 Run-phase Evidence

### M1 스파이크·픽스처 (GO/NO-GO) — 2026-10-21

**판정: GO** (시도 1회째에 통과, 시도 3회 한도 중 1회 사용). 증거 폴더: `.moai/state/verify/t18-m1/` (git 무시 경로). 파이썬은 `../../../.venv/bin/python -I`(서버 가상환경과 같은 3.13.11, `websockets 16.0`)로 실행했고 모든 명령 종료 코드 0이다. 스파이크는 M2 모듈이 아니라 M1 전용 스크립트(`cdp.py`, `spike_canary.py`)이며 기존 `goose_runner.build_invocation`/`build_env`로 하네스 인자를 만들었다(argv: `attempt1/attempt1-argv.json`, `--setting-sources project --settings ~/.goose-harness/.claude/settings.json --strict-mcp-config --permission-mode dontAsk --no-session-persistence --model sonnet`).

| 조건 | 결과 | 근거 |
|---|---|---|
| (a) 두 뷰포트 본문 크기(17px) 토큰 정확 인용, `y>0` 타일에 배치 | PASS | 기대 `desktop FJMP2E` / `mobile WR9EA3`. 응답 JSON `desktop-02.png: ["FJMP2E","CKNYYU","UWKUMU"]`, `mobile-02.png: ["WR9EA3","A9NVX6","NWHGUV"]` — 본문 토큰 2개 모두 문자열 일치. 두 토큰 모두 타일 02(y=1568) 안 |
| (b) 모든 캐너리 타일에 `Read` tool_use↔tool_result 짝, `is_error` false 또는 키 없음 | PASS | 6/6 타일 짝 확인, 전부 `is_error` 키 없음(`ABSENT`), 결과 content 종류 `['image']` (`attempt1.out`) |
| (c) `y>0` 타일 해시가 `y=0`과 다르고 높이가 clip과 같음 | PASS | 아래 표 |

(b) Read 짝 원문(`attempt1.out`): `desktop-01..03.png`, `mobile-01..03.png` 각 1쌍, tool_use→tool_result 간격 0.02~0.06초.

(c) clip 원문: `desktop-02 y=1568 h=1568 → png h 1568 sha 7c9477095…  ≠ y0 38fc1d611…` / `desktop-03 y=3136 h=1064 → 1064 sha 9a7ada66c…` / `mobile-02 y=1568 h=1568 → 1568 sha a1c26dafc…  ≠ y0 45fb400e8…` / `mobile-03 y=3136 h=1064 → 1064 sha 1cd355c23…`. 캐너리 페이지 높이 4200px → 타일 3개(1568+1568+1064).

토큰 사전 노출 없음: 프롬프트·argv에 6개 토큰 중 어느 것도 없음(`tokens_exposed_in_input: []`, `attempt1/record.json`). 토큰 문자 집합은 혼동 글자(0/O, 1/I, 소문자 등)를 뺀 대문자·숫자 `ACDEFGHJKLMNPRTUVWXYZ2345679`(글꼴 혼동으로 인한 오판 방지, 가독성 임계값과 별개). 캐너리 폴더 `~/.goose-harness/runs/t18-m1-canary-<ts>/`는 증거를 복사한 뒤 삭제했고 `ls ~/.goose-harness/runs`는 기존 5개 폴더뿐이다. 라이브 초안 해시 `480b6f772b308ecf…` 불변.

**기록 값 (GO와 무관)**
- 가독성 임계값(G4): 본문 17px, 12px, 9px 토큰이 두 뷰포트 모두 정확 인용됨. 시험한 가장 작은 크기 9px에서도 오인용이 없어 임계값은 "≤ 9px"(하한 미확정, 응답이 "작은 글씨는 해상도가 낮아 읽기 어려웠지만 보이는 대로 옮겼다"고 언급).
- 타일 1568px 높이 유지 가능(재시도 불필요).
- 이미지 `Read` 스트림 모양(G1): `assistant`의 `tool_use{name:"Read", input.file_path=절대 경로}`(모델이 상대 경로를 하네스 절대 경로로 확장), 이어 `user`의 `tool_result{is_error 키 없음, content:[{type:"image"}]}`.
- `Read` 시간(G5/N10e): 보조 세션으로 라이브 초안 실제 타일 33장(데스크톱 13+모바일 20)을 한 세션에서 열게 함 → `Read 33/33 짝, is_error 전부 ABSENT, 세션 벽시계 28.81초, tool_use→result 평균 0.02초(최대 0.04), 첫 Read~마지막 결과 12.09초` (`timing_and_write_probe.out`). 900초 상한 대비 여유 충분, 조정 규칙 (b) 해당 없음. 단 응답 품질은 "제목 한 줄"만 요구한 낮은 부하이며 실제 감수(사실 대조·감수 기록 쓰기 포함)의 시간은 M6 실측.

**타일 상한 확정 (P26, AC-008)**: 네트워크 전면 차단·스크립트 비활성으로 재측정(`probe_geometry.out`): `1d261a37` 9807→7타일/15047→10, `5695985a` 9053→6/14169→10, `a5becbb9` 20160→13/30803→20, `d0a64dfc` 12066→8/18797→12. 모두 `sw == cw`. 최대 데스크톱 13·모바일 20, 1.5배 = 20·30. 값이 SPEC(research P26)과 같고 `TILE_CAP=30`은 충분하다 → **조정 없음**, 조정 규칙 (a) 해당 없음.

**Gap 관측**
- G2: 환경 변수 없이 Playwright 캐시 탐색(빌드 번호 숫자 비교)이 `chromium_headless_shell-1243/…/chrome-headless-shell`(`Google Chrome for Testing 153.0.8010.12`)을 선택.
- G3: 이 스파이크 경로로 `y>0` clip 동작(위 (c)와 라이브 초안 `desktop y=1568 sha 5aad3e94…`, `mobile y=1568 sha a9ef4622…`, 마지막 타일 `y=18816 h=1344`/`y=29792 h=1011`이 clip 높이와 일치), `Emulation.setScriptExecutionDisabled`·`Network.setBlockedURLs ["*"]` 모두 `ok`. 격리 관측: 로컬 수신 소켓에 `<link>`·`<img>`·`<script src>`·`fetch`를 심은 파일 — 대조군(차단 없음·스크립트 허용)은 수신 `['/a.css','/b.png','/c','/d.js']`·`div text = SCRIPT-RAN`, SPEC 설정(차단+스크립트 비활성)은 수신 `[]`·`div text = static`.
- G8: 같은 라이브 초안에서 차단 대비 비차단은 모바일 높이 30683 대 30803(−120px, P27과 같음), 데스크톱 20160 동일, 타일 y=0 해시는 두 뷰포트 모두 다름. 눈으로 비교한 모바일 y=1568 타일(`live-mobile-{blocked,unblocked}-y1568.png`)은 본문 글꼴이 같고 차이는 제목(명조 계열 대체 글꼴) 모양과 줄 위치 약간.
- G9: `--no-sandbox` 없이 구동 성공(`no --no-sandbox in argv: True`, 엔드포인트 응답 0.26초). 이 호스트에서는 불필요, 다른 호스트는 미관측.
- 관측값이 SPEC 기록과 다른 항목 없음(P26, P27, P28 일치).

**주의할 새 관측 (SPEC 수정 요구 아님, 판단은 오케스트레이터)**: 모든 `claude -p` 세션 stderr에 `Ignoring 9 permissions.allow entries from .claude/settings.json: this workspace has not been trusted ...`가 출력된다(`~/.claude.json`에 하네스 폴더 `projects` 항목 없음, `grep goose` 출력 없음). 그럼에도 `Read`(타일)와 `./runs/<폴더>/`에 대한 `Write`·`Edit`·`Read`는 성공했다(`writeprobe`: Write/Edit/Read 모두 `is_error` ABSENT, 파일 내용 `world`). 즉 이 환경에서 허용 목록이 무시돼도 이 도구들은 동작했고, 허용 목록이 실제 제한 수단인지(예: `runs/` 밖 쓰기 거부)는 시험하지 않았다(미관측). 영수증의 위조 방지 가정(T3·T13)과 관련되므로 M3 전에 확인을 권한다.

**미관측/한계**: 실제 감수 세션의 사실 대조·`audit-review.json` 쓰기·`render_report.py --final` 실행은 M1 범위 밖. 토큰 인용은 글자를 읽을 수 있다는 증거까지만. 시도 1회라 재현성(반복 시 동일 결과)은 미관측.

**픽스처**: SPEC 파일 표에 픽스처 경로 지정 없음 → 요청대로 `.moai/state/verify/t18-m1/`에 보관: 라이브 초안 타일(`live-*.png`, 차단·비차단), 캐너리 HTML·타일(`attempt1/`), 격리 시험 HTML(`isolation_fixture.html`). 라이브 초안 HTML 자체는 복사하지 않고 읽기 전용으로 직접 참조했다(M2 이후 합성 HTML 픽스처 제작은 미착수).

**증거 경로**: `probe_geometry.out`, `attempt1.out`, `attempt1/{record.json,tokens.json,prompt.txt,attempt1-stream.jsonl,attempt1-argv.json,attempt1-stderr.txt}`, `timing_and_write_probe.out`, `timing-stream.jsonl`(19.9 MB), `writeprobe-stream.jsonl`.

### M2 캡처 모듈 — 2026-10-21

**산출**: `backend/services/goose_screenshot.py`(신규), `backend/tests/test_goose_screenshot.py`(신규, 34개). 증거 폴더 `.moai/state/verify/t18-m2/`(git 무시 경로): `red_stub.out`, `mutations.out`, `mutate.py`(되돌림 하네스), `real_capture.py`·`real_capture.out`(실제 브라우저 수동 실행). 파이썬 `../../../.venv/bin/python`(3.13.11), 린트 `python3 -m ruff`(시스템 0.14.11 — 서버 venv에는 ruff 없음).

**기준선·결과 (직접 실행)**
- 전: `../../../.venv/bin/python -m pytest backend/tests -k goose -q` → `267 passed, 214 deselected, 1 warning in 16.66s`
- 후: 같은 명령 → `301 passed, 214 deselected, 1 warning in 22.31s` (267 + 신규 34, 실패 0, 기존 테스트 수정 0)
- 신규 파일만: `34 passed`. 커버리지 `coverage run --include='*/goose_screenshot.py' -m pytest backend/tests/test_goose_screenshot.py` → `backend/services/goose_screenshot.py 242 13 95% 97-109, 207, 308` (97-109는 `/json/list` 탐색 루프 — 아래 수동 실행이 대신 관측)
- 린트: `python3 -m ruff check backend/services/goose_screenshot.py backend/tests/test_goose_screenshot.py` → `All checks passed!` (`ruff format --check`는 기존 `goose_runner.py`도 재포맷 대상이라 적용하지 않음)

**RED 관측 순서**: 구현을 먼저 초안으로 쓴 뒤 시험을 썼으므로(TDD 순서 위반) 구현을 스크래치로 치우고 상수·빈 `capture`만 있는 스텁으로 바꿔 `red_stub.out`을 얻었다 → `34 failed` (전부 `NotImplementedError`/속성 없음). 이어 구현을 복원해 `34 passed`. 그 뒤 AC별 되돌림 RED는 `mutate.py`가 보호 동작을 하나씩 임시로 되돌리고 시험을 돌린 뒤 복원했다. 마지막 줄 `restored-sha-match: True`(원본 해시와 일치).

| AC | 상태 | 시험 | 되돌림 변이 → 관측한 RED (`mutations.out` 원문 요약) |
|---|---|---|---|
| 006 | PASS | `test_air6_006_*` 5개(드라이버 2 포함) | (a) 타일 없이 한 장 → 5건 실패 · (b) 같은 폭 → 1건 · (c) 모바일 에뮬레이션 누락 → 8건 · (d) 스크립트 비활성이 navigate 뒤 → 2건 · (e) 보고서 내용으로 파일 이름 → 1건 · (f) 심볼릭 링크 검사 전부 제거 → 2건 · (g) 폴더 링크(해석 경로) 검사 제거 → 1건 |
| 007 | PASS | `test_air6_007_*` 8개 | (a) 키 이름 변경 → 5건 · (b) 시간대 없음 → 4건 · (c) 입력 JSON 해시 → 2건 · (d) 메모리 사본 해시 → 1건 · (e) `>=` 넘침 → 3건 |
| 008 | PASS | `test_air6_008_*` 12개 | (a) 상한 없음 → 2건 · (a') 상한 경계 `>=` → 1건 · (b) 앞 30개만 저장 → 2건 · (c) 예산 미적용 → 2건 · (d) 크기 상한 없음 → 1건 · (d') 크기 경계 `>=` → 1건 · (e) 임시 프로필을 성공 경로에서만 삭제 → 4건 · (f) 실패 뷰포트 부분 타일 미정리 → 1건 |
| 009 | PASS | `test_air6_009_*` 4개(CdpDriver 호출 형태 1 포함) | (a) 비허용 인자 추가 → 1건 · (b) 스크립트 비활성 누락 → 2건 · (c) 네트워크 차단 누락 → 1건 · (d) 디버깅 주소 0.0.0.0 → 1건 · (e) 글꼴 호스트 예외 → 1건 |
| 010 | PASS | `test_air6_010_*` 4개 | (a) 환경 변수 무시 → 24건 · (b) 잘못된 변수에서 폴백 → 1건 · (c) 후보 없음에서 예외 → 2건 · (d) 빌드 번호 문자열 비교 → 1건 · (d') 첫 후보 선택 → 1건 · (e) PATH 탐색 → 1건 |
| 002(모듈 몫) | PASS | `test_air6_002_cancel_kills_browser_group_and_profile` | (b) 직계 프로세스만 종료 → 7건 · 취소 때 정리 생략 → 7건 |

변이 33개 모두 RED 관측(적용 실패·미관측 0). `Google Chrome.app`(E)은 PATH 후보 폴더에 같은 이름 실행 파일(`Google Chrome`)로 흉내 냈고 앱 번들 구조 자체는 만들지 않았다 — 모듈에 그런 경로 탐색 코드가 없어 변이도 PATH 탐색(e) 하나로 대표했다.

**실제 브라우저 수동 실행** (`real_capture.out`, pytest 밖): 합성 페이지(높이 4200px, 외부 `<link>` + `<script>`)에 `gs.capture` 1회 → `outcome: complete`, `browser {HeadlessChrome, 153.0.8010.12, playwright_cache}`(환경 변수 없이 캐시 탐색), 데스크톱 `[1568,1568,1064]`·모바일 같은 분할, 파일 `desktop-01..03.png`, `mobile-01..03.png`, `index.json`, 종료 후 `goose-shot-*` 프로필 폴더·브라우저 프로세스 잔존 0(`pgrep` 출력 없음). 모바일 `scroll_width` 980은 합성 페이지에 `<meta viewport>`가 없어서이며 모듈 문제가 아니다(M1 라이브 초안은 390=390).

**SPEC 대비 차이·결정 (모두 SPEC 문구 수정은 요구하지 않음)**
- 실제 브라우저 시험은 pytest에 두지 않았다: 공용 네트워크 가드(`conftest.py`)가 루프백 `socket.connect`까지 막아 `/json/list`·WebSocket이 불가능하다. 대신 수동 실행으로 대체.
- `index.json` 스키마에 실패 사유 필드가 없어 사유 코드는 뷰포트의 `error`에 둔다. `unavailable`은 두 뷰포트 `status: skipped` + `error: browser_not_found | browser_env_not_executable`. 시작 실패는 `browser_start_failed:<예외 이름>`, 예산 초과 `budget_exceeded`, 취소 `cancelled`, 심볼릭/비정규 초안 `draft_not_regular_file`·`draft_outside_job_dir`. 예외 메시지는 경로가 샐 수 있어 클래스 이름만 적는다.
- 실패한 뷰포트의 `metrics`는 4개 키를 모두 `null`로 둔다(스키마 키 집합 유지). `AI_REPORT_GOOSE_BROWSER`가 빈 문자열이면 미설정으로 본다.
- `screens/`는 서버 소유 폴더라 캡처 시작 때 비우고 다시 만든다. 색인은 임시 파일 + 원자적 교체로 쓴다.
- 프로세스 종료는 `terminate_group`(SIGTERM→유예→SIGKILL) 대신 `killpg(SIGKILL)` + `wait()`로 했다: 프로필을 어차피 지우므로 정상 종료가 필요 없고, 취소 중에도 동기로 끝나며, 좀비를 회수해야 `killpg(pgid, 0)`이 `ProcessLookupError`가 된다.
- `websockets`는 `pyproject.toml`에 아직 선언돼 있지 않다(M5 소관, plan M5 행). 서버 venv에는 16.0이 설치돼 있어 import는 통과.

**미관측/한계**: 실제 `file://` 로드의 로드 이벤트 대기 시간 분포(1회 관측, 즉시 완료), Linux 캐시 구조(G12), 외부 요청 0건을 로컬 소켓으로 확인하는 일은 M1에서 수행했고 이 모듈 경로로는 재측정하지 않았다(`Network.setBlockedURLs ["*"]` 호출 형태만 시험). 예산 60초 안에서 33장 캡처가 실제로 몇 초 걸리는지는 M6 라이브에서 측정.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
