# SPEC-AI-REPORT-006 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_revised_at: 2026-10-21 (v0.3.4, sync 단계 보안 검토 S1~S9 반영 — 아래 §E.2 "Sync-phase security review". 앞서 v0.3.3, t19 병합 뒤 감수 규칙 번호 9 → 10 반영 — 문구 패치. 앞서 v0.3.2는 3차 델타 검사 N17·N18 반영 소형 텍스트 패치, v0.3.1은 3차 감사 PASS-WITH-DEBT 조건 N11~N16 반영)
- plan_status: draft (v0.3.4). 3차 델타 검사 보고서 `.moai/reports/t18/plan-audit-iter3-delta.md`(N17·N18). 3차 감사 보고서 `.moai/reports/t18/plan-audit-iter3.md`(결함 N11~N16). 감사 보고서: 1차 `.moai/reports/t18/plan-audit.md`(결함 D1~D14), 2차 `.moai/reports/t18/plan-audit-iter2.md`(결함 N1~N10)
- artifacts: spec.md, plan.md, acceptance.md, design.md, research.md, progress.md (Tier L)
- counts: REQ 20개(REQ-AIR6-001~020), AC 22개(AC-AIR6-001~022). v0.3.0·v0.3.1·v0.3.2·v0.3.3·v0.3.4에서 개수 변동 없음(재계산 출력: `.moai/state/verify/t18-plan3/trace.py`, v0.3.4는 `.moai/state/verify/t18-sync/trace_amend.py`)
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

### M3 감수 세션·영수증 — 2026-10-21

**산출**: `backend/services/goose_review.py`(신규), `backend/tests/test_goose_review.py`(신규, 97개), `backend/services/goose_runner.py`(추가: `build_review_prompt`, `resolve_review_timeout`, `ReviewTracker`, `ReviewRunResult`, `run_review`, 공용 `_run_session` 추출·`_seconds_from`). 증거 폴더 `.moai/state/verify/t18-m3/`(git 무시): `step0_write_probe.py`, `step0-attempt1.out`·`-stream.jsonl`·`-stderr.txt`·`-argv.json`, `step0-harness-{before,after-probe,after-cleanup}.txt`, `step0-find6-after.txt`, `mutate.py`, `mutations.out`, `pytest-after.out`.

**Step 0 — 쓰기 허용·거부 관측 (운영 argv, 시도 1회, 종료 코드 0)** `build_invocation`/`build_env`로 만든 argv(`--setting-sources project --settings ~/.goose-harness/.claude/settings.json --strict-mcp-config --permission-mode dontAsk --no-session-persistence`), cwd=`~/.goose-harness`. stderr 원문: `Ignoring 9 permissions.allow entries from .claude/settings.json: this workspace has not been trusted. Run Claude Code interactively here once and accept the trust dialog, or set projects["/Users/byunjungwon/.goose-harness"].hasTrustDialogAccepted: true in /Users/byunjungwon/.claude.json.`

| # | 호출 | 기대 | 관측 | is_error | tool_result 원문 |
|---|---|---|---|---|---|
| 1 | Write `runs/t18-m3-probe/ok.txt` | 허용 | 허용 | 키 없음 | `File created successfully at: /Users/byunjungwon/.goose-harness/runs/t18-m3-probe/ok.txt (file state is current in your context — no need to Read it back)` |
| 2 | Edit 같은 파일 | 허용 | 허용 | 키 없음 | `The file …/runs/t18-m3-probe/ok.txt has been updated successfully. (file state is current in your context — no need to Read it back)` (디스크 내용 `world` 확인) |
| 3 | Write `./t18-m3-outside.txt` | 거부 | 거부 | True | `Permission to use Write has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt …` (+ 스트림에 `system/permission_denied`, `decision_reason_type: "mode"`) |
| 4 | Write `./.claude/t18-m3-deny.txt` | 거부 | 거부 | True | `<tool_use_error>File is in a directory that is denied by your permission settings.</tool_use_error>` |
| 5 | Edit 존재하지 않는 `./.claude/t18-m3-nonexistent.txt` | 거부 | 거부 | True | `<tool_use_error>File is in a directory that is denied by your permission settings.</tool_use_error>` |

해석: 허용 목록 경고에도 `runs/` 쓰기는 되고 `runs/` 밖·`.claude/` 쓰기는 거부된다(후자는 `deny` 규칙이 신뢰 경고와 무관하게 적용됨을 시사). 3의 거부는 허용 목록 부재 + dontAsk 모드 때문이므로 허용 목록이 무시되는 환경에서는 `runs/` 쓰기 허용이 허용 목록 때문인지 다른 규칙 때문인지는 이 관측만으로 구분하지 못한다(미관측). 기대와 어긋난 결과 없음.

정리·검증 (프로브 직후, 리드 보류 지시 도착 전에 완료): `rm -r ~/.goose-harness/runs/t18-m3-probe` 후 `find ~/.goose-harness -maxdepth 3 -not -path '*/skills/*' | sort`를 시작 전 스냅샷과 `diff` → `IDENTICAL_TO_BEFORE`. `settings.json` sha256 `e8b527cc…15df3`, `CLAUDE.md` `a7a9a06e…554e9` 전후 동일(그때 설치본). 보류 해제 뒤 읽기 전용 재검증(쓰기 없음, `python -B -I`): `find ~/.goose-harness \( -name '__pycache__' -o -name '*.pyc' \) | wc -l` → `0`; `-not -path '*/runs/*' -not -path '*/.claude/skills/*'` 목록 = `.claude`, `.claude/settings.json`, `.claude/skills`, `CLAUDE.md`, `runs` 뿐; `*t18*` 파일 0개; 스냅샷 diff는 리드의 t19 라이브 작업 폴더 `runs/11808900a8834252814d1872da5e0ca5`(내가 만든 것이 아님)만 추가. 매니페스트: 이 워크트리의 낡은 매니페스트로는 `verify_installed` → `['installed sha256 mismatch: CLAUDE.md']`(리드가 19:36 서버 재시작으로 t19 지침을 재설치했고 설치본 `CLAUDE.md`는 `77e260e4…2fed`), 메인 체크아웃 매니페스트(33개)로는 `verify_installed mismatches: []`. 따라서 설치본 33개 해시 일치는 메인 매니페스트 기준이며 내 프로브가 만든 변경이 아니다.

**기준선·결과 (직접 실행)**
- 전: `../../../.venv/bin/python -m pytest backend/tests -k goose -q` → `301 passed, 214 deselected` (M2 기록·시작 기준선)
- 후: 같은 명령 → `398 passed, 214 deselected, 1 warning in 27.44s` (301 + 신규 97, 실패 0, 기존 테스트 수정 0; `test_goose_runner.py` 65개 통과로 `_run_session` 추출의 동작 보존 확인)
- 커버리지: `coverage run --include='*/goose_review.py' -m pytest backend/tests/test_goose_review.py` → `goose_review.py 274 17 94%`
- 린트: `python3 -m ruff check` 새·변경 3파일 → `All checks passed!`

**RED 관측**: 구현을 먼저 초안으로 쓴 뒤 시험을 썼다(TDD 순서 위반, M2와 같음 — 시험이 구현을 먼저 보고 쓰였다는 한계). 대신 모든 보호 동작을 `mutate.py`로 하나씩 되돌려 RED를 관측했다(`mutations.out`, 변이 52개 전부 RED, 미적용·STILL-GREEN 0, 마지막 줄 `restored-sha-match: True`).

| AC | 상태 | 되돌림 변이 → RED |
|---|---|---|
| 016 수준 A 15개(조건 2~12, 14~17) | PASS | 각 조건의 사유 추가를 제거한 변이마다 해당 격리 케이스 RED (예: 조건 14 → `[h]`만, 15 → `[i]`만, 16 → `[j]`만) |
| 016 수준 B(조건 1, 13) | PASS | 1을 `receipt_invalid`로 바꿈(SPEC 모델) → `[b]`·S9(a) RED; 제거 → 같음. 13 제거 → `[o]`·`[o2]` RED (이 구현에서는 결과가 뒤집힘 — 조건 13 미충족이면 14~17을 평가하지 않기 때문) |
| 016 조건 0 | M4 | `select_report` 연결은 M4. 여기서는 `evaluate_admissibility`가 `delivery_allowed:false`에 무관함만 시험((n) 절반) |
| 016 기타 | PASS | 저장된 `visual_admissible` 입력 사용 → 19건 RED; 읽기 실패 허용 → 6건; 작성기가 디스크 래퍼 호출 → 30건; 영수증 이중 쓰기 → 3건; 읽기 보호에서 16 제외 → 2건 |
| 021 | PASS (판정 부분) | 조건 17 제거·표지 완화·"시작" 한정 모두 RED. 지침 문구(규칙 10)는 M5 |
| 014 (a)~(m) | PASS | 13개 변이 모두 RED ((e)(f)는 추적기 시험으로 RED) |
| 015 (a)(a')(b)(c)(d)(e)(f) | PASS | 7개 모두 RED; (g)는 M4 |
| 011 (a)~(f) + 기본 시간 상한 | PASS | 7개 모두 RED |
| 002 (감수 프로세스 그룹 몫) | PASS | 그룹 정리 제거 → RED |

**SPEC 대비 차이·결정**
- `finish_review`는 `harness_dir`을 명시 인자로 받는다(경로 정규화용). 취소는 `outcome="cancelled"` 인자로 강제한다. `integrity_failed`·`disabled` 영수증 작성기는 M4가 추가한다(이 모듈은 아직 없음).
- 사유 코드 밖의 안전망: `evaluate_admissibility`가 예기치 않은 예외를 만나면 `(False, ["receipt_invalid"])`로 미인정 처리한다(설계상 도달하지 않음).
- `ReviewTracker`는 `Write`/`Edit`만 쓰기 시도로 센다(`MultiEdit`·`NotebookEdit`은 세지 않음 — 하네스 허용 목록에 그 도구가 있는지는 확인하지 않았다).
- 세션 전 정리가 `final/`까지 지우므로 시험의 기준 픽스처 P는 `final/`을 감수 세션이 만든 것으로 모델링한다.
- 삭제 실패 시(AC-014 (13)) `context.json`은 쓰지 않는다.
- 실행기: `run_goose`의 세션 실행부를 `_run_session`으로 추출(동작 동일, 기존 65개 통과). 추적기는 `StageMapper`와 같은 `.feed(line)` 계약이라 `_read_stdout`을 그대로 쓴다.

**미관측/한계**: 이미지 `Read` 실제 스트림 모양은 M1 기록(`tool_result.content=[{type:image}]`, `is_error` 키 없음)을 합성 픽스처로 모사했을 뿐 실제 녹화로 교체하지 않았다. 별칭 경로(`/private/var` ↔ `/var`) 대응 분기와 일부 방어 분기(커버리지 미적용 17줄)는 시험하지 않았다. `select_report`·작업 서비스·완료 이벤트(AC-014 (11)~(13)의 `select_report` 절반, AC-015 S9의 이벤트 값, AC-016의 `archive_job` 비교)는 M4.

**오케스트레이터 독립 확인 (2026-10-21 19:39~19:44, 병합 83b327f 뒤, 증거 `.moai/state/verify/t18-m3-orch/`)**
- `pytest backend/tests -k goose -q -p no:cacheprovider` → `398 passed, 214 deselected, 1 warning in 25.16s` (`pytest_goose.out`, exit 0).
- 하네스 목록(`find ~/.goose-harness -maxdepth 2 -not -path "*/runs/*"`): `.claude/settings.json`, `.claude/skills`, `CLAUDE.md`, `runs`만 있고, `__pycache__`·`*.pyc`·`*t18*`는 0개. `runs/`에는 기존 5개 폴더와 t19 라이브 작업 `11808900a8834252814d1872da5e0ca5`뿐이다.
- 무결성(`verify_harness.py`, `python -B -I`, 주 체크아웃 `backend/goose_harness_src` 매니페스트): 19:43:48 `entries 33 | verify_installed vs primary manifest: []`.
- **일시적 불일치 관측**: 19:40경 같은 확인이 `['installed sha256 mismatch: CLAUDE.md']`를 냈다. 당시 설치본 `CLAUDE.md` 앞 16자리는 `a7a9a06e43d2a2be`(= t18 작업공간 매니페스트의 항목), 주 체크아웃 매니페스트는 `77e260e4c5a27e9f`였다. 19:42:16에 `CLAUDE.md`와 `settings.json`의 수정 시각이 갱신됐고 19:42:19에 다시 `77e260e4…`로 바뀐 뒤 불일치는 사라졌다. 그 시각대에 t19 작업공간 파이썬(pid 69801, 19:41:46 시작)이 돌고 있었다.
- **원인 정정 (2026-10-21 20:30, 근거는 시각 일치뿐이며 훅 내부는 열어 보지 않았다).** `a7a9a06e…`는 t18 고유 버전이 아니라 기준 커밋 `7abdcac`의 값이다(리드가 `git show 7abdcac:…`로 확인) — 규칙 9가 들어오기 전 소스를 가진 모든 작업공간이 같은 값을 설치한다. 덮어쓰기 시각은 t18 커밋 시각의 35~45초 뒤와 3건 모두 맞는다: `83b327f` 19:38:52 → 하네스 19:39:36, `5a9a09b` 19:44:24 → 19:44:59, `86e4301` 20:27:18 → 20:28:03(`git log --format='%h %cd' --date=format:%H:%M:%S`와 `stat`). `.git/hooks/pre-commit` 65행이 `moai gate`(lint+테스트)를 돌리고, 앱 lifespan을 띄우는 테스트가 그 체크아웃의 하네스 소스를 `AI_REPORT_GOOSE_HARNESS_DIR` 미지정 시 실제 `~/.goose-harness`에 설치하는 경로(`backend/main.py` lifespan → `install_at_startup`)가 있다. 앞 문단의 "제 `pytest`일 가능성"은 이 3건으로는 지지되지 않는다. 대응: t18의 이후 커밋은 `AI_REPORT_GOOSE_HARNESS_DIR`를 임시 경로로 지정하고 한다(훅이 환경을 상속한다는 가정은 다음 커밋에서 수정 시각 불변으로 확인).

### M4 작업 서비스 연결·최종본 인정·프론트 — 2026-10-21

**산출**: `backend/services/goose_job_service.py`(후처리 `_post_process`·스위치·취소·fail-open·전달 상태 재계산, 생성자 `screenshotter`/`reviewer`, 운영 인스턴스에 `goose_screenshot.capture`·`goose_runner.run_review` 주입), `backend/services/goose_review.py`(`write_outcome_receipt`: integrity_failed·disabled·cancelled 영수증 작성기), `backend/services/goose_runner.py`(`select_report`가 조건 0 통과 뒤 `goose_review.evaluate_admissibility` 호출), 프론트 3파일(`types/aiReport.ts`, `utils/gooseJob.ts`, `components/ProgressPanel.tsx`), 시험(`test_goose_job_service.py`·`test_goose_review.py` 추가, `test_goose_runner.py`·`test_goose_storage.py` 갱신 + 프론트 시험 2파일), 합성 입력 픽스처 `backend/tests/fixtures/goose_review/live-draft-input.json`(라이브 020150 초안 입력 원본 68430바이트, 시험에서 네이버 채널 패치). 증거 폴더 `.moai/state/verify/t18-m4/`(git 무시): `baseline.out`, `red_select.out`, `red_service.out`, `vitest_red.out`, `mutations.out`, `mutations2.out`, `mutate.py`, `py.sh`·`node.sh`(격리 실행 래퍼), `final_goose.out`, `vitest_final.out`, `tsc.out`, `eslint.out`, `harness-before.txt`, `harness-after.txt`.

**격리**: 모든 pytest·python 실행은 `py.sh`(임시 `HOME=.moai/state/verify/t18-m4/home`, `AI_REPORT_GOOSE_HARNESS_DIR=…/home/.goose-harness`, `python -B`, `PYTHONDONTWRITEBYTECODE=1`)로, 프론트 도구는 `node.sh`(같은 HOME/하네스 환경)로 실행했다. **예외 1건(프론트, 하네스와 무관)**: 20:17경 `vitest run`(RED 관측용) 1회가 `node.sh` 도입 전에 격리 환경 변수 없이 `frontend/node_modules/.bin/vitest`로 실행됐다(출력 `vitest_red.out`). 그 시점 실제 홈의 `~/.goose-harness`에 쓰는 코드 경로는 프론트 시험에 없지만 환경 변수로 막지 않았다는 사실을 그대로 기록한다. 격리 이전에 돌린 pytest·python은 없다(첫 pytest는 `py.sh` 경유 `baseline.out`).

**하네스 전후** (`harness-before.txt` 19:47 / `harness-after.txt` 20:26, 읽기 전용 `shasum -a 256`·`stat`):
- 전: `CLAUDE.md` `a7a9a06e43d2a2be…554e9`(mtime 19:44:59), `settings.json` `e8b527cc…15df3`(19:44:59)
- 후: `CLAUDE.md` `77e260e4c5a27e9f6166be2be19faec6332d421cdf0d82ba5fe3c1b6c6fb2fed`(mtime **20:01:07**), `settings.json` 해시 동일 `e8b527cc…15df3`, mtime 20:01:07
- 해석: 바뀌었다. 내 첫 pytest/python 실행은 20:06경(`baseline.out` 20:06:48)이라 변경(20:01:07)은 내 실행보다 앞선다. 19:47~20:06 사이 내가 한 일은 읽기(cat·sed·grep·ls)뿐이었다. 새 해시 `77e260e4…`는 M3 기록의 주 체크아웃 매니페스트 값(= t19 지침 설치본)과 같다. 변경 주체는 확인하지 못했다(설치 행위를 직접 보지 못함).

**기준선·결과 (직접 실행)**
- 전: `py.sh -m pytest backend/tests -k goose -q -p no:cacheprovider` → `398 passed, 214 deselected, 1 warning in 36.26s`
- 후: 같은 명령 → `470 passed, 214 deselected, 1 warning in 28.26s` (398 + 신규 72, 실패 0). 신규 72 = `test_goose_review.py` 35(select_report 몫 + 종료 영수증 작성기) + `test_goose_storage.py` 매개변수 2(`a-no-receipt`, `g-no-receipt`) + `test_goose_job_service.py` 35(AC-001~005·014 서비스 몫·015 S9·020·022)
- **갱신한 기존 테스트 3개**(398 기준선 대비): `test_goose_runner.py::test_select_report_rules`(영수증 없는 `final/`은 draft라는 새 기대 + `evaluate_admissibility`를 인정으로 고정한 `final` 기대), `test_goose_storage.py::test_ac014_final_judgement_fixtures[a]`·`[g]`(`final/` 보관 복사 경로를 계속 시험하려고 판정 함수만 인정으로 고정; 영수증 없음 기대는 `a-no-receipt`·`g-no-receipt`로 추가). 다른 기존 테스트 수정 0.
- 프론트: `node.sh vitest run --root …/frontend src/utils src/components` → `Test Files 77 passed (77) / Tests 702 passed (702)`, exit 0(`vitest_final.out`). 전체 `vitest run` 1회(`vitest_green.out`): `Tests 845 passed (845)`, `Test Files 1 failed | 96 passed (97)` — 실패 1건은 `e2e/preset-flow.spec.ts`(`Playwright Test did not expect test.describe() to be called here`), 이 변경과 무관한 Playwright 스펙이 vitest에 수집된 것(기준선에서 별도 재측정하지 않음 — 미검증). `tsc -p tsconfig.app.json --noEmit` exit 0, `eslint`(변경 5파일) exit 0. 워크트리에 `frontend/node_modules`가 없어 주 체크아웃 것을 `cp -cR`(복제)로 워크트리 안에 두고 썼다(주 체크아웃 쓰기 없음, gitignore 대상).
- 린트: `python3 -m ruff check`(변경 7파일) → `All checks passed!`

**RED 관측**: 이번 마일스톤은 시험을 먼저 썼다. (1) select_report·종료 영수증 시험: 구현 전 `33 failed, 2 passed`(`red_select.out`, `-k "select_report or planted_cases or outcome_receipt"`; 통과 2건은 구현 전에도 맞던 기준 상태 확인) → 구현 후 `35 passed`. (2) 서비스 시험: 구현 전 `31 failed, 1 passed`(`red_service.out`) → 구현 후 전부 통과. (3) 프론트: `5 failed | 12 passed`(`vitest_red.out`) → 구현 후 통과. 그 뒤 모든 AC의 되돌림 변이는 `mutate.py`(`mutations.out` 64개 + 재구성 3개 `mutations2.out`)로 보호 동작을 하나씩 되돌려 RED를 관측하고 복원했다. 마지막 줄 `restored-sha-match: True` 두 번.

| AC | 상태 | 되돌림 변이 → 관측 |
|---|---|---|
| 001 (a)~(f) | PASS | (a) 후처리를 잠금 안에서 실행 · (b) 감수를 캡처 자리에서 실행 · (c) 재검사 생략 · (d) 재검사 실패 때 진행 · (e) 생성자 기본값에 실제 구현 · (f) draft 확인 제거 → 모두 RED |
| 002 | PASS | (a) 캡처 단계가 취소를 삼킴(`BaseException`) · 취소 영수증 쓰기 제거 · (c) 감수 프로세스 그룹 정리 제거(실제 `run_review` + 잠자는 가짜 claude) → RED. 브라우저 프로세스 그룹 몫 (b)(3)은 M2 `test_air6_002_cancel_kills_browser_group_and_profile`가 담당(이 마일스톤에서 서비스 수준으로 중복하지 않음) |
| 003 | PASS | (a) 프론트 단계 목록 누락 · (b) 단계를 시작 후 발행 · (c) 두 번 발행 · (d) 꺼진 경우에도 발행 · (e) 프론트 `render_final`을 `session_end` 앞에 · (f) 감수 세션 모든 호출 중계 · `render_final` 중복 제거 해제 · 라벨 누락 → 모두 RED |
| 004 | PASS | (a) 스위치 무시 · (c) disabled 영수증 미작성 · (d) 스위치 0이면 실행기도 건너뜀 → RED. (b) "스위치를 감수기 안에서만 확인"은 구조상 별도 변이를 만들지 않았다(스위치는 후처리 진입에서 한 번 읽는다) — 미관측 |
| 005 | PASS | (a) 캡처 예외가 작업 실패로 전파 · (b) 캡처 실패 시 감수 건너뜀 · (c) 감수 예외 전파(안쪽·바깥쪽 fail-open 두 겹을 함께 제거해야 RED, 첫 시도에서 안쪽만 제거한 변이는 STILL-GREEN이었음 — 바깥 보호가 받아내서) · (d) 시간 초과를 기록하지 않음 · (e) 종료 0·기록 없음을 `reviewed`로 기록 → RED |
| 014 서비스 몫 | PASS | (i) 사전 심은 `audit-review.json` 삭제 제거 · (j) `final/` 삭제 제거 · (k) 삭제 실패를 무시하고 세션 시작(`launch=True`; 첫 변이 `if False: return start`는 STILL-GREEN이라 의도대로 `launch`를 바꾼 변이로 재구성) · (m) 삭제 실패 때 시작 값 비워 둠 · select_report 인정 건너뜀 → RED. (11)(12)(13)의 select_report 절반은 `test_air6_014_select_report_planted_cases` |
| 015 S9 | PASS | S9(a)(b)는 세션이 서버와 똑같은 **인정 영수증**을 위조해 두는 시험(처음엔 키가 부족한 위조 파일이라 우연히 draft가 되어 변이가 STILL-GREEN일 뻔했고, 완전한 위조로 고침). (f) 제거 없이 교체만(제거 두 곳을 함께 빼야 RED) · (g) 영수증 잔존 시 이벤트를 draft로 확정하는 분기 제거 → RED |
| 016 select_report 몫 | PASS | 조건 0 제거 · 판정 함수 호출 제거 · 조건 1~17 각각의 사유 추가를 제거(`reasons.append("…")`→`pass`) → 17개 모두 RED. 수준 A/B 구분 없이 select 시험(`air6_016_select_report_*`)이 모든 조건에서 RED. 조건별 격리 사유 목록 단언은 M3 시험이 담당 |
| 020 (1)~(6) | PASS (c 제외) | (a) 실행기 값 그대로 사용 · (b) 재계산 대신 고정값 · (d) 스위치 0에서도 재계산 · (e) 재검사 실패에서도 재계산 → RED. (c) "이벤트와 `job.json`이 다른 시점 값"은 훅과 재계산이 같은 `select_report`를 읽어 서로 갈라지는 상태를 만들 수 없어 독립 변이를 만들지 못했다 — 미관측(대신 (1)이 이벤트·`job.json`·`archive_job` 반환의 동치를 단언) |
| 022 | PASS | 실제 `audit_report.py`·`render_report.py --final`을 가짜 claude 스크립트가 실행. 합성 입력은 라이브 초안 입력에서 네이버 `blocked`→`no_results` 패치 + `research_window.mode: historical`·`user_requested_as_of: true`(날짜 신선도 검사를 시험 시점과 분리 — G10을 날짜 재작성 대신 이 방식으로 해소; 분기·연도 상대 검사도 고정). 감사 `decision == pass`·`findings == []`, `final/render-validation.json` `delivery_allowed: true`, 영수증 `reviewed`·`visual_admissible: true`·`reasons: []`, `select_report == final`, 완료 이벤트와 `job.json` `final`, `render_final` 이벤트 1개. 대조(타일 하나 미열람)는 감사기·렌더러는 통과시키나 사유 `[tile_not_read]`, `draft`. 되돌림: 컨텍스트의 `preview_sha256`·`input_sha256`·`reviewed_at`·`mode` 오염, 조건 11 제거, `render_final` 중계 제거 → 모두 RED |
| 017 (M4 종료 시 회귀) | PASS | 위 `470 passed`, 실패 0, 네트워크 가드 teardown 단언 통과(가드 기록 0) |

**SPEC 대비 차이·결정**
- 주입 계약: `screenshotter(job_dir)`는 `goose_screenshot.capture`(위치 인자 1개), `reviewer(job_id=, code=, on_event=)`는 `goose_runner.run_review`와 같은 키워드 시그니처. 둘 중 하나라도 없으면 후처리를 하지 않고 영수증도 쓰지 않는다. 하네스 경로는 `runs_root().parent`로 얻는다.
- `disabled`·`integrity_failed` 영수증은 "주입됨 + 1차 `done` + `draft/report.html` 정규 파일"일 때만 쓴다(REQ-AIR6-004는 주입 조건을 적지 않지만 REQ-001의 "생성자 기본값은 기존 흐름 그대로"와 맞추려고 주입이 없으면 쓰지 않는다).
- 후처리 중 취소는 best-effort `cancelled` 영수증을 쓴다. 감수 세션 시작 전이면 `write_outcome_receipt`, 시작 뒤면 `finish_review(outcome="cancelled")`.
- `render_final` 진행 이벤트는 감수 세션 단위로 한 번만 낸다(같은 세션이 `--final`을 여러 번 실행해도).
- 1차 세션 `StageMapper`의 `render_final`(1차 세션이 규칙을 어기고 `--final`을 실행한 경우)은 건드리지 않았다(T11). 이 경우 `render_final`이 `session_end` 앞에 도착할 수 있고 프론트는 그대로 `reached`에 넣는다.
- 영수증 쓰기 실패 + 파일 잔존 시 완료 이벤트는 `draft`(REQ-019), 보관 훅의 `job.json`은 G14 그대로(디스크 재판정).
- 전달 상태 재계산에서 `select_report`가 `None`(draft도 사라짐)이면 이벤트 값은 `None`이다.

**Gap·미관측**
- 004 (b), 020 (c): 위 표 사유로 독립 변이 미관측.
- 002 (3)의 실제 브라우저 프로세스 그룹은 서비스 수준에서 다시 시험하지 않았다(M2 시험이 모듈 수준에서 RED 관측 완료).
- 합성 입력 시험은 `historical` 모드를 쓰므로 실제 현재 모드(`current`)의 `FRESHNESS_CUTOFF`·`AS_OF_MISMATCH` 경로는 AC-022가 확인하지 않는다.
- 프론트 전체 `vitest run`의 `e2e/preset-flow.spec.ts` 실패는 기준선에서 재측정하지 않았다.
- 커버리지는 이 마일스톤에서 재측정하지 않았다(`goose_job_service` 후처리 신규 줄은 위 시험들이 지나가나 수치 미측정).
- `ruff format --check`는 기존 파일 재포맷 대상이라 적용하지 않았다.

### Merge main (SPEC-AI-REPORT-007, 카드 t19) — 2026-10-21

main(89db7a2)을 `WT-goose-review-pass` 줄(0ee4593)에 병합했다. 병합만 했고 harness-instructions.md·매니페스트·pyproject·README·`.env.example`은 건드리지 않았다(다음 단계 M5).

충돌은 2개 파일, 10개 구간이었다.

| 파일 | 구간 | 해결 | 이유 |
|---|---|---|---|
| goose_job_service.py | 모듈 문서 문자열 | 양쪽 유지(006, 007 순) | 서로 다른 SPEC 설명 |
| 〃 | import | `goose_naver_prefetch`를 더한 한 목록 | 둘 다 필요 |
| 〃 | `ENV_REVIEW` / `ENV_NAVER_PREFETCH` | 둘 다 | 서로 다른 끄기 스위치 |
| 〃 | 타입 별칭 | 둘 다 | Screenshotter·Reviewer·`_PostResult` + NaverPrefetcher·CodeCheck |
| 〃 | 생성자 인자 | 둘 다(screenshotter, reviewer, naver_prefetcher, code_check) | 모두 기본값 None |
| 〃 | 생성자 대입 | 둘 다 | 위와 동일 |
| 〃 | 메서드 블록(HEAD 116줄 / main 29줄) | 둘 다(006 후처리 메서드들 뒤에 007 `_code_validated`·`_prefetch_naver`) | 서로 독립된 메서드 |
| 〃 | 운영 인스턴스 `_service(...)` | 인자 4개 모두 | 둘 다 운영에 연결 |
| test_goose_job_service.py | 양쪽 모두 파일 끝에 추가한 구간 | 합집합: 기준 + 006 추가분(718줄) + 007 추가분(338줄) | 두 구간이 줄 단위로 얽혀 있어 조각 병합 대신 ours 전체 + main 추가분을 그대로 붙임. 최상위 이름 충돌 없음(AST로 확인) |

`_run` 본문은 git이 충돌 없이 합쳤고 순서가 맞다: DART 수집 → 네이버 수집 → (수집기 하나라도 있으면) 무결성 재검사 → 1차 세션 → `_post_process`(재검사 → 캡처 → 감수 → 영수증) → 전달 상태 → 종료. 진행 이벤트에는 네이버 단계가 없다.

병합 통합 시험 1개를 추가했다(`test_merge_007_006_run_order_and_identical_event_lists`): 두 SPEC 주입을 모두 켠 구성에서 호출 순서와, 네이버 주입 유무에 따른 진행 이벤트 목록 동일을 확인한다.

시험(격리: `AI_REPORT_GOOSE_HARNESS_DIR=.moai/state/verify/t18-merge/home/.goose-harness`, `-B -p no:cacheprovider`):
- `pytest backend/tests -k goose -q` → `534 passed, 214 deselected` (통합 시험 추가 전 533). 출력 `.moai/state/verify/t18-merge/goose_all_final.txt`.
- 작업 서비스 시험 파일: 기준 49, 006쪽 84(+35), main쪽 71(+22), 병합 106 = 49+35+22 (+ 통합 1 = 107).
- AC-AIR7-001·004, AC-AIR6-001·003·004·005·020 선택 실행 28개 통과.

하네스 전후: `~/.goose-harness/CLAUDE.md`의 해시와 수정 시각이 전후 동일(`.moai/state/verify/t18-merge/harness-{before,after}.txt`).

### M5 하네스 지침·매니페스트·문서 — 2026-10-21 (카드 t18)

기준: 브랜치 `WT-goose-review-pass` 9c763cb(M1~M4 + main 병합). 작업은 자동 격리 워크트리(`worktree-agent-a9205c52de2a1df0e`)에서 했고 시작 시 `git rev-parse --short HEAD` → `9c763cb`. 격리: 모든 pytest/python은 `AI_REPORT_GOOSE_HARNESS_DIR=.moai/state/verify/t18-m5/home/.goose-harness`, `python -B`, `pytest -p no:cacheprovider`. 증거 파일은 `.moai/state/verify/t18-m5/`(git 미추적).

**번호 결정(SPEC 문서와 다른 점).** SPEC 문서는 감수 규칙을 "규칙 9"라 적었지만 t19가 규칙 9(네이버)를 먼저 들여왔으므로 감수 규칙은 **규칙 10**이다. 하위 항목은 설계의 (a)~(i)를 `10-1`~`10-10`으로 바꿨고(규칙 4·8·9와 같은 형식, 마지막 `10-10`은 설계의 (i)), 본문 자기 참조는 `10-3`(10-5 안)이다. 규칙 7은 번호 그대로 개정했고 규칙 4의 "최종본:" 줄에 "(감수 세션만 실행한다 — 규칙 7·10)"을 덧붙였다. 코드·테스트에서 규칙 번호를 이름으로 부르는 곳은 없었다(`grep -rnE "규칙 ?9|rule 9|규칙 ?7|\b9-[0-9]" backend --include='*.py'` → `goose_runner.py:194`·`goose_review.py:4`의 "규칙 7 불변식" 주석 2건뿐, 번호 9 없음). `build_review_prompt`는 "하네스 지침의 감수 세션 규칙"으로만 가리켜 수정하지 않았다.

**병합 필수 4단계 (007 `plan.md §5`)**

1. 규칙 번호: `python3 -I .moai/state/verify/t18-m5/rulenum.py backend/goose_harness_src/harness-instructions.md`(007 AC-AIR7-011 #4 블록을 그대로 추출) →
   ```
   rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
   rule numbering ok
   ```
   감사 부채 N9(정상 교차 참조 오탐)는 발생하지 않았다. `grep -n '9번 규칙' backend/goose_harness_src/harness-instructions.md` → 출력 없음(종료 1).
2. 지침 문자열 AC 재실행: 006 `pytest backend/tests/test_goose_harness.py backend/tests/test_goose_review.py -k "air6_013 or air6_021" -q` → `20 passed, 158 deselected`. 007 AC-AIR7-009의 grep 루프(`air7_009.txt`): `naver/index.json` 2, `article_url` 1, `channel: "naver"` 1, `metadata_only` 1, `"no_results"` 1, `모바일 뉴스 API 응답의 제목·요약 본문 필드` 1, `서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음` 1, `API 요약본(약 150자), 원문 미확인` 1, `요약에 없는 사실은 단정하지 않는다` 1, `이번 세션에서 그 파일을 연 시각` 1, `original_news` 1, `code_validated` 1, `서버가 종목코드 유효성을 확인하지 못함` 1, `runs/<job_id>/dart/index.json` 2 — 14개 모두 기대(≥1, 마지막 2) 충족. (`runs/<job_id>/naver/index.json`이 2인 것은 규칙 9 도입부와 9-6, ≥1 기대.)
3. 매니페스트 재생성: `../../../.venv/bin/python -B -m backend.services.goose_harness > backend/goose_harness_src/goose-manifest.json`(종료 0; stderr의 `pkg_resources` 경고만 있었고 stdout은 JSON뿐). 변경은 `CLAUDE.md` 해시 한 줄(`77e260e4…` → `64ceebda7075b70a65abfd5402bb1dfd13ba72856dc567a8c7be2702b2c1b35e`)뿐이다. AC-AIR7-011 #1: 다시 생성해 `diff m.json goose-manifest.json` → 출력 없음, 종료 0. #2: `claude-settings.json` sha256 `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`. #3: `pytest backend/tests/test_goose_harness.py -q` → `46 passed`(실패 0).
4. `_run` 순서·이벤트: `pytest backend/tests/test_goose_job_service.py -k "air7_001 or air7_004" -v` → `5 passed, 102 deselected`(`test_air7_001_order_with_dart_and_naver`·`…naver_only`·`…without_prefetchers`·`…second_integrity_failure_with_naver_only`·`test_air7_004_naver_prefetch_adds_no_progress_event` 모두 PASSED).

**AC-AIR6-013 / 021 (TDD)**

- RED(지침 수정 전, 시험 추가 직후): `10 failed, 538 passed, 214 deselected`(`pytest-before.out`, `red-initial.out`): 실패는 새 시험 10개(`KeyError: 10` 등). 기준선 534 + 새 시험 중 처음부터 통과하는 4개(매니페스트=재생성은 아직 일치, 설정 해시, 스킬 불변, 전체 변형 시험 1개) = 538.
- GREEN: `pytest backend/tests -k goose -q` → `548 passed, 214 deselected`(534 + 새 시험 14개, 실패 0).
- 새 시험 14개(`test_goose_harness.py`): `air6_013` 규칙 7 문구·규칙 10(번호·하위 라벨·고정 문구 13개)·적용 범위·매니페스트=재생성·설정 해시·스킬 불변(기준 9c763cb 대비 `git diff --stat` 비어 있음), 텍스트 변형 시험 6개, `air6_021` 표지 요건·D7 결과 문구.
- 되돌림 RED(`mutations.out`, 실제 `harness-instructions.md`에 변형을 적용하고 시험 후 복원 — 복원 뒤 `git diff --stat`이 변형 전과 같음):
  - (a) 표지 `[렌더 차이]` 문장 삭제 → `test_air6_021_instructions_carry_render_difference_marker_requirement`·`test_air6_021_d7_…` RED
  - (b) 규칙 7의 "audit-review.json을 쓰지 않고" 삭제 → `test_air6_013_rule7_forbids_first_session_review_record_and_final` RED
  - (c) 번호 충돌(`10.` → `9.`) → `test_air6_013_review_rule_is_rule_10_after_naver_rule_9`·`…rule10_applies_only…` 등 RED
  - (d) 옛 하위 라벨 `9-2` → 규칙 번호 시험 RED
  - (e) 본문 자기 참조 `10-3` → `9-3` → 규칙 번호 시험 RED
  - (f) 모든 타일 Read 조건 문구 삭제 → 규칙 10 고정 문구 시험 RED
  - (g) `--final`을 결정 `pass` 조건 없이 실행하도록 변경 → 규칙 10 고정 문구 시험 RED
  - (h) 지침만 고치고 매니페스트 미재생성 → `test_committed_source_matches_committed_manifest`·`…covers_instructions…`·`test_air6_013_manifest_equals_regeneration` RED(`mut-b-manifest-stale.out`, 재생성 전에 실제로 관측)
  - 모든 변형에서 매니페스트 시험도 같이 RED가 된다(지침 해시가 달라지므로). 변형별 판별 RED는 위 지정 시험이다.
- 잡지 못하는 것: 문구가 모델 행동을 바꾸는지(약한 증거 — AC-018 라이브). AC-013 #5(서버 재시작 후 설치본 무결성)는 라이브 단계라 이 레인에서 관측하지 않았다(Gap).

**기타 변경.** `pyproject.toml`에 `websockets>=16.0`(서버 venv 설치 16.0)을 더했고 `uv.lock`의 프로젝트 `dependencies`·`requires-dist`에 같은 항목을 더했다(`uv lock --check --offline` → `Resolved 78 packages`, 종료 0). `.env.example`에 `AI_REPORT_GOOSE_REVIEW`·`AI_REPORT_GOOSE_REVIEW_TIMEOUT`·`AI_REPORT_GOOSE_BROWSER`를, README의 Goose 동작 방식 5항 아래에 캡처·감수·브라우저 지원 범위(chrome-headless-shell 153.0.8010.12, macOS 구동 확인)·끄기를 적었다. 캡처 60초·타일 30장은 코드 상수라 환경 변수가 없다(`AI_REPORT_GOOSE_REVIEW_TIMEOUT`만 설정 가능). README 알려진 한계의 "감수·화면 확인 단계가 없다" 문장은 M6 라이브 확인과 병합 뒤에 고칠 대상이라 남겨 두었다.

**하네스 전후** (`harness-before.txt`/`harness-after.txt`): 시작 시 `~/.goose-harness/CLAUDE.md` sha256 `77e260e4c5a27e9f6166be2be19faec6332d421cdf0d82ba5fe3c1b6c6fb2fed`, 수정 시각 `20:32:20`. 커밋 뒤 값은 아래 보고에 이어 적는다.

**SPEC 본문에 남은 "규칙 9" 표기 (manager-spec 후속, 이 레인에서는 고치지 않음)**: plan.md:48(M5 행), plan.md:68(병합 순서 위험 행의 설명), design.md:158(제목 줄)·160(규칙 본문 안 `규칙 7·9`), acceptance.md:139(AC-013 #1)·145(잡는 구현 (a))·333(AC-021 Then), spec.md:72(§3 변경 범위 표), research.md:78(G13 `규칙 9 (h)`), progress.md:128(AC-021 행). progress.md:149는 t19 규칙 9를 가리키는 정당한 표기다. (위 목록은 커밋 `c5632a6`(v0.3.3)에서 규칙 10으로 정정됐다. 남은 "규칙 9"는 의도된 설명이거나 t19의 실제 규칙 9다.)

**오케스트레이터 독립 확인 (2026-10-21 20:50~21:05, 병합 `33e3c18`·`c5632a6` 뒤, 증거 `.moai/reports/t18/run-evidence/orch-m5/`)**
- 규칙 번호 검사(007 acceptance.md의 AC-AIR7-011 #4 블록을 그대로 추출해 `python3 -B -I`): `rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` / `rule numbering ok`. 감수 표지 문구 `[렌더 차이]`는 `harness-instructions.md`에 1건, 한자 표기 0건.
- 매니페스트: `python -B -m backend.services.goose_harness`로 새로 재생성한 출력과 커밋된 `goose-manifest.json`의 `diff`가 비었다(종료 0). `claude-settings.json` sha256 앞 16자리 `e8b527ccaf017853` 그대로, `backend/goose_harness_src`의 `.pyc`·`__pycache__` 0개.
- `pytest backend/tests -k goose -q -p no:cacheprovider`(`AI_REPORT_GOOSE_HARNESS_DIR`를 저장소 안 임시 경로로 지정): `548 passed, 214 deselected, 1 warning in 28.24s`, 종료 0. 실행 전후 실제 `~/.goose-harness/CLAUDE.md`는 `77e260e4c5a27e9f`, 수정 시각 `20:32:20`으로 같다.
- 프런트 `e2e/preset-flow.spec.ts`를 vitest로 돌리면 기준 상태(주 체크아웃)에서도 `Playwright Test did not expect test.describe() to be called here.`, `Test Files 1 failed (1)`, `Tests no tests`로 실패한다(`vitest_e2e_baseline.out`). 이 SPEC의 변경과 무관한 이미 있던 실패다(Playwright 명세가 vitest에 수집됨). 에이전트가 본 전체 vitest 1파일 실패와 같은 파일이다.
- **커밋 게이트 격리 확인**: 환경 변수 `AI_REPORT_GOOSE_HARNESS_DIR`를 붙인 커밋 5건(`0ee4593`, `9c763cb`, `33e3c18`, `c5632a6`, `28e896e`)에서 실제 하네스 `CLAUDE.md` 수정 시각은 `20:32:20`에서 변하지 않았다. 각 커밋 뒤 75~150초를 두고 읽었다(이전 3건은 커밋 +35~45초에 덮어쓰기). 훅 안에서 테스트가 격리 경로로 도는 것을 직접 보지는 못했다.
- 사본 증거에서 1MB를 넘는 3개는 제외했고(`EXCLUDED-over-1MB.txt`) 비밀 문자열 검색은 필드 이름 `apiKeySource` 3건 외에 일치가 없었다(`run-evidence/README.md`).
- **미검증**: AC-013 #5(서버 재시작 뒤 설치본 무결성 통과)와 M6 라이브 전부. 현재 설치된 하네스(`77e260e4…`)는 새 매니페스트(`CLAUDE.md` 항목 `64ceebda…`)와 달라 main 병합 뒤 서버 재시작 때 맞춰진다. (아래 M6에서 리드가 재시작 뒤 33개 파일 일치와 규칙 10 설치를 확인했다.)

### M6 라이브 관측 게이트 (AC-AIR6-018) — 2026-10-21 (리드 실행·판정, 증거 사본 `.moai/reports/t18/run-evidence/live-m6/`)

**판정: 통과 (1회차).** 리드가 main `2713402`에서 서버를 재시작(21:12, pid 8701)한 뒤 020150에 대해 1회 실행했다. job `0ffb8f9e490d40779b9b3d7c5224c1b3`, KST 21:12:09~21:22:16(10분 7초). AC가 허용한 ≤2회 중 한 회차로 충분해 두 번째는 쓰지 않았다. 판정과 `ac018_check.py`는 리드가 실행했고, 아래 표의 영수증·색인·감수 기록 필드는 내가 런 원본 JSON을 읽기 전용으로 다시 읽어 일치를 확인했다(`.moai/state/verify/t18-m6-orch/summarize_live.out`).

| AC-018 판정 항목 | 관측 | 확인 |
|---|---|---|
| 1 작업 완료 | `job.json` `status: done`, `delivery_status: draft`, `interrupted: false` (`live-m6/job.json`) | 리드·나(사본 읽음) |
| 2 캡처 | `screens/index.json` `outcome: complete`, 데스크톱 13·모바일 19 타일, 파일 존재·sha256 불일치 0 | 타일 수는 나, 불일치 0은 리드 |
| 3 영수증 | `outcome: reviewed`, `tiles_expected` 32 = `tiles_read` 32, `exit_code` 0, `timed_out` false, `draft_unchanged` true, `judged_writes` [], `snapshot_start == snapshot_end` | 나(JSON 직접 읽음) |
| 4 감수 기록 형식 | `audit_report.py --preview --review` 결함 코드 `[REVIEW_SOURCE_ACCURACY, REVIEW_VISUAL, UNRESOLVED_ISSUE]`, 형식 코드 4개(`AUDIT_INPUT_VERSION`, `AUDIT_PREVIEW_VERSION`, `AUDIT_TIME`, `AUDIT_MODE`)와 교집합 공집합, 5개 검사 모두 존재·`evidence` 비어 있지 않음. 대조군(`--review` 없음)은 형식 코드 4개 + `REVIEW_*` 5개가 다시 나타남 | 리드(`lead-audit018_*.json`, `lead-ac018.txt`), 5개 검사 존재·evidence 길이는 나 |
| 5 안전 불변식 | `visual_admissible: false`, `reasons: ['visual_not_pass']`, 전달 `draft`, `final/` 폴더 없음, 완료 이벤트 `delivery_status: draft` == `job.json` | 나(영수증·`final/` 부재·이벤트 읽음) |

**비게이팅 기록.** 5개 검사 상태: `source_accuracy` revise, `calculations` pass, `coverage` pass, `opinion` pass, `visual` revise. `visual.evidence`는 `[렌더 차이]`로 시작한다. 감수 세션이 실제 결함 2건(기사 출처라 한 수치의 불일치, 390px 모바일 차트 잘림)을 찾아 `UNRESOLVED_ISSUE`가 남았고 그래서 `final`에 도달하지 못했다 — 정직한 `revise`가 게이트를 막지 않는다는 설계(REQ-018)대로다. 이번 회차의 `research_window`는 `dart`·`naver`·`original_news`·`company_ir`·`industry` 모두 `read`라 `LATEST_SEARCH_*` 결함이 없었고 `FRESHNESS_CUTOFF`도 없었다(자정 전 종료). 소요 시간 외 토큰 실측은 없다.

**관측하지 못한 것.** 라이브에서 `final` 인정 경로는 보지 못했다(감수가 결함을 찾아 `draft`로 끝났으므로) — 이 경로는 AC-AIR6-022 격리 시험이 담당한다. 감수가 찾은 두 결함이 진짜 결함인지(차트 잘림·수치 불일치)는 내가 렌더 결과를 보고 확인하지 않았다(리드 보고만).

**제품 후속 후보 (이 SPEC 범위 밖).** 렌더러의 390px 모바일 차트 잘림.

### Sync-phase security review (2026-10-21) — 보안 검토 `--security --deep` 결과의 SPEC 반영 (v0.3.4)

이 절은 plan 단계 담당(manager-spec)이 보안 검토 결과를 SPEC에 반영한 기록이다. 구현·수정 코드는 아직 없다(M7이 한다). 증거는 `.moai/state/verify/t18-sync/sec/`(git 무시 경로). 아래 "상태"는 SPEC 개정에서의 처리이며 수정이 반영·검증됐다는 뜻이 아니다. 판정(PASS/FAIL)은 하지 않는다.

| ID | 심각도 | 내용 | SPEC 처리 | 관측한 근거 |
|---|---|---|---|---|
| S1 | 높음 | `file://` 하위 자원(iframe)이 열려 로컬 파일 내용이 타일에 그려짐 | 이번 개정에서 수정 요건화(REQ-009 강화, design §3.3 층 A1·B, AC-009 (3)(5)(6) R1). 코드 수정은 M7 | research P36: `job1/screens/desktop-01.png`를 직접 열어 비밀 표지와 `/etc/hosts` 내용 확인(PoC 재실행은 리드) |
| S2 | 높음 | 페이지 대상 밖의 cross-site iframe/object/embed가 외부로 요청 | 이번 개정에서 수정 요건화(REQ-009, design §3.3 층 A1·A2·B, AC-009 (3)(5)(6) R2). 코드 수정은 M7 | research P37: `poc2.py`를 내가 재실행 → `poc2_amend.out`, HITS 6건(`/iframe`·`/embed`·`/object` × 2뷰포트) |
| S3 | 중간 | 감수 세션이 웹 자료 속 지시를 따르고 `WebFetch`/`WebSearch`/`Agent`/`Skill`을 호출할 수 있음 | 이번 개정에서 지침 수준만 완화(규칙 10-11, REQ-013, AC-013 #1·#6·(e)). 권한 봉쇄는 D3 때문에 이월(G16) | 보안 검토 보고. 지침 문구의 행동 효과는 미관측 |
| S4 | 가설 | `Bash` 허용 접두어 + 셸 리다이렉트로 쓰기 거부 목록 밖에 쓸 수 있는지 | 이월(G16), 수정 안 함. 시험하지 않았다 | 미관측 |
| S5 | 낮음 | 브라우저 자식 프로세스가 서버 환경 전체를 상속 | 이번 개정에서 수정 요건화(REQ-009 허용 목록 환경, AC-009 (2)). 코드 수정은 M7 | research P40: 코드 읽기(`Popen`에 `env` 없음) |
| S6 | 낮음 | `_free_port`와 브라우저 바인드 사이 TOCTOU | 이월(G17), 수정 안 함. 코드 읽기로만 확인 | research P42 |
| S7 | 가설 | 스트림 줄 읽기 한도 4 MiB 대 타일 8 MiB 불일치 | 이월(G18), 수정 안 함. 닫힌 쪽(가용성)으로만 어긋남 | 미관측 |
| S8 | 가설 | 완료 경로와 취소 경로의 영수증 임시 파일 이름 충돌 | 이월(G19), 수정 안 함 | 미관측 |
| S9 | 정보·낮음 | 1차 세션이 심은 `review/delivery-audit.json`이 세션 전 정리에서 지워지지 않음 | 이번 개정에서 수정 요건화(REQ-014 `review/` 비우기, AC-014 (14)(15)). 단 "보관됨" 전제는 코드 읽기로 성립하지 않음 — research P41, 리드에게 정정 보고. 코드 수정은 M7 | research P41 |
| S10 | — | 이번 지시에 내용이 없어 기록하지 못했다 | 미확인. 리드가 알려 주면 추가한다 | — |

수용·유지: G11, G13, G14, G15, D13(변경 없음). 신규 Gap: G20(수정 메커니즘의 미관측 동작).

**미검증:** 이번 개정은 문서 변경뿐이다. 새 SPEC 요건이 구현 가능한지(특히 층 B의 `Fetch.fulfillRequest` 서빙, 프록시 플래그와 브라우저 기동, `data:`·`about:blank` 일시 정지)는 G20으로 열려 있다. 이전 §E.1의 `moai spec lint` 미재실행 상태도 그대로다.

### M7 security hardening (v0.3.4, 카드 t18) — 2026-10-21

기준 커밋 `f0926e2`(브랜치 `WT-goose-review-pass`)에서 `manager-develop`(cycle_type=tdd)가 구현. 증거 원문은 `.moai/state/verify/t18-m7/`(git 무시 경로). 모든 pytest·python 실행은 `AI_REPORT_GOOSE_HARNESS_DIR=.moai/state/verify/t18-m7/home/.goose-harness`와 `-B -p no:cacheprovider`로 돌렸고 `HOME`은 건드리지 않았다. 서버·goose 작업은 만지지 않았다.

**1. G20 관측 (구현 전, 프로브 `probe/probe.py`).** 라이브 초안 사본(`live-draft-copy.html`)을 헤드리스 셸 1243(Playwright 캐시 최고 빌드)에 먹였다.
- 세 프록시 플래그를 켜도 브라우저가 뜨고 `/json/list`가 응답한다. 허용 목록 환경(`PATH HOME USER LANG LC_ALL TZ TMPDIR SHELL`)만으로도 기동한다.
- 층 B 가능: `file://` 주 문서 요청이 `Fetch.requestPaused`(resourceType `Document`)로 오고 `Fetch.fulfillRequest`(디스크 바이트 + `Content-Security-Policy`)가 동작한다. 렌더 결과는 `scrollHeight` 19369(기록값 P39와 같음). 외부 글꼴 `<link>` 2개는 CSP `style-src`가 먼저 막아 일시 정지로 오지 않는다. 따라서 "B 불가 → 계획 단계로 되돌림" 조건은 해당 없음.
- `about:blank`·`about:srcdoc` 일시 정지는 내가 요청 URL을 기록한 두 관측(라이브 초안 프로브, 자식 대상 프로브)에서 오지 않았다. R1~R3 실행은 일시 정지 URL을 기록하지 않았으므로 거기서는 미관측이다. 정상 보고서 캡처가 달라지지 않았으므로(R3 일치) `about:blank` 예외를 두지 않았다.
- 자동 연결 대상은 방어가 전부 작동하는 구성에서는 **한 번도 붙지 않는다**(`attach-count.out`: R1 0, R2 0 — 자식 문서가 로드되지 않으므로). 실제 브라우저에서 이 경로를 보려고 A2·CSP를 끄고 A1이 모두 `continue`하게 한 프로브(`attach-probe.out`)를 돌렸다: cross-site iframe 문서를 통과시키면 `Target.attachedToTarget`이 뷰포트마다 한 번 오고, `Fetch.enable → Target.setAutoAttach → Runtime.runIfWaitingForDebugger` 순서를 Chrome이 오류 없이 받으며, 자식 문서의 하위 요청(`/childimg`)이 **자식 세션**의 `Fetch.requestPaused`로 온다(페이지 세션이 아니다). 즉 자식 대상 방어는 실제로 필요하고 동작한다.

**2. 구현 요약.**
- `goose_screenshot.py`: `ISOLATION_FLAGS`(층 A2, `_launch` argv), `DOCUMENT_CSP`(층 B, design §3.3의 문자열 그대로 — 조정 불필요), `BrowserDriver.isolate(url, body)`(첫 `Page.navigate` 전에 `Target.setAutoAttach` + `Fetch.enable{*}`; `body`는 `_run`이 해시한 바로 그 바이트), 이벤트 펌프(`_pump`: 응답은 보관, `Target.attachedToTarget`은 `Fetch.enable → setAutoAttach → runIfWaitingForDebugger`, `Fetch.requestPaused`는 초안 URL 정확 일치 → `fulfillRequest`, `data:` → `continueRequest`, 나머지 → `failRequest`), `Popen(env=build_env(environ))`(허용 목록 = 실행기 `ENV_ALLOWLIST` 재사용). `setBlockedURLs ["*"]`·스크립트 비활성은 그대로.
- fail closed: 이벤트 처리 중 예외(모양이 틀린 이벤트, 자식 대상 `Fetch.enable` 오류)는 `_broken`을 세워 이후 `open()`이 `isolation_failed`로 끝난다(두 번째 뷰포트도 열지 않는다). 페이지 세션의 `isolate` 오류는 기존 시작 실패 경로(`browser_start_failed:cdp_error:Fetch.enable`, 두 뷰포트 error, `Page.navigate` 없음).
- `goose_review.py`: `_remove_entry`·`_empty_review` 추가, `_delete_planted`가 **`review/`를 먼저** 비운다(링크는 `unlink`만, `review` 자체가 링크·파일이면 그것만 지움). 비우기 실패 → 기존 삭제 실패 경로(`launch=False`).
- `harness-instructions.md` 규칙 10-11, 매니페스트 재생성. @MX: `_post_process`·`capture`에 `@MX:WARN`, `finish_review`에 `@MX:ANCHOR`(그 밖의 태그 없음).

**3. 층 행렬 (AC-009 (6)) — 관측** (`matrix.out`, `observe.py matrix`; R1 = 마젠타 화소 수, R2 = 루프백 수신 소켓 기록 수; 각 변형은 코드를 임시로 토글, 커밋하지 않음).

| 켜 둔 층 | R1 file iframe | R1 object/embed | R1 data: 중첩 | R2 | 예측과 비교 |
|---|---|---|---|---|---|
| 없음 | RED (마젠타 391376) | RED (392176) | 0 | RED (6건: `/iframe /embed /object` × 2) | 예측 일치. **차이:** `data:` 중첩 iframe은 층이 없어도 `file://`을 못 연다(0) — 이 변형은 이 브라우저에서 RED가 되지 않는 회귀 방지용이다 |
| A1만 | GREEN (0) | GREEN | 0 | GREEN (0건) | 일치 |
| A2만 | RED (391376) | RED | 0 | GREEN (0건) | 일치 |
| B만 | GREEN | GREEN | 0 | GREEN | 일치 |
| A1+B | GREEN | GREEN | 0 | GREEN | (추가) |
| A1+A2 | GREEN | GREEN | 0 | GREEN | (추가) |
| A2+B | GREEN | GREEN | 0 | GREEN | (추가) |
| A1+A2+B | GREEN (0) | GREEN (0) | 0 | GREEN (0건) | 일치. 두 뷰포트 모두 `complete`, 파란 박스 20000화소(= 초안 자체는 그려짐) |

추가 관측: (가) 자식 대상 보호만 뺀 A1(`a1-page-only.out`, 플래그·CSP도 끔)도 R1·R2 GREEN이다 — 이 PoC들은 자식 문서 자체가 로드되지 않아 자식 세션 방어를 시험하지 못한다(그 계약은 가짜 전송 시험과 위 프로브가 맡는다). (나) 채택 구성에서 한 층·한 처리기 변형만으로는 실제 브라우저 회귀(R1·R2)가 RED가 되지 않는다(층이 겹치는 설계 의도). 실제 브라우저 R1이 RED가 되는 것은 `isolate()` 자체를 뺄 때(A1과 B 동시 제거)뿐이다(`mutations-live.out`: `009-r` RED 1, 나머지 16개 변형 RED 0).

**4. 되돌림 RED 관측 (코드를 임시 변형 → 시험 → 바이트 단위 복원, `mutate.py`)**. 전부 변형마다 RED가 관측됐고 복원 후 같은 시험이 GREEN이다. 원문: `mutations-009.out`, `mutations-014-013.out`, `mutations-live.out`, 구현 전 초기 RED는 `red-initial-*.out`(리뷰·하네스 9건, 캡처 9건, 라이브 R1·R2).

| 변형 | RED가 된 시험(요약) |
|---|---|
| 009-f 프록시·우회 목록·호스트 해석 플래그 각각 제거 | `argv_only_fixed_strings…` |
| 009-g `Popen`에 `env` 미전달 | `child_env_is_an_allowlist…` |
| 009-h 자식 대상 `Fetch.enable` 제거 / 009-i `runIfWaitingForDebugger`를 먼저 | `(3) handler_contract…`, `(4) …attached_target…` |
| 009-j 모든 요청 `continueRequest` / 009-k `file://` 통과 | `(3) handler_contract…` |
| 009-l 초안 비교를 접두어·대소문자 무시·부분 문자열로 | `(3) handler_contract…`(`#x`·`?x=1`·대소문자·`.bak` 행) |
| 009-m CSP 헤더 없음 / `frame-src` 누락 / `object-src` 누락 | `(3) handler_contract…`(첫 행) |
| 009-n 서빙 본문이 디스크 바이트와 다름 | `(3) handler_contract…`(첫 행) |
| 009-o `data:`도 실패시킴 | `(3) handler_contract…`(`data:` 행) |
| 009-p 핸들러 오류 삼킴 | `(4) …malformed…`, `(4) …attached_target…` |
| 009-q `Fetch.enable` 오류 무시(페이지 세션 / 자식 대상 각각) | `(4) …page_session…` / `(4) …attached_target…` |
| 009-r `isolate()` 호출 제거 | 5건(`isolation_is_applied…`, `isolation_failure…`, `(3)×2`, `(4) page_session`) + 라이브 R1 |
| 014-n `review/` 비우기 제거 | (14)(15)(서비스 포함) 7건 |
| 014-o 심볼릭 링크를 따라가 대상 삭제 | `(14) review_dir_is_emptied_without_following_links`, 서비스 (14) |
| 014-p `review/` 삭제 실패 무시 | (15) 3건(감수기가 호출됨) |
| 014-q `context.json`을 쓰지 않음 | (14) 계열 + 기존 `…11/12/…normal_review_directory_writes…` 등 8건 |
| 014-x(추가) `review` 자체가 링크일 때 따라감 | `(14) review_that_is_itself_a_symlink…` |
| 013-e 규칙 10-11 삭제 | `rule10_11_…`, `mutation_dropping_rule10_11…`, 그리고 매니페스트 해시 시험 3건 |
| 013-b 지침만 고치고 매니페스트 미재생성 | 매니페스트 시험 3건 |

**5. R1·R2·R3 (PoC 전후).** 손 실행 `PYTHONPATH=. <venv>/python -B .moai/state/verify/t18-m7/poc.py baseline|new` (`poc-baseline.out`, `poc-new.out`)와 pytest(`AI_REPORT_GOOSE_REAL_BROWSER_TESTS=1 … -m pytest backend/tests/test_goose_screenshot_live.py -q`, 라이브 초안 사본까지 돌리려면 `AI_REPORT_GOOSE_R3_DRAFT=<사본>` 추가).
- PoC1(글자 비밀 + `/etc/hosts`): 기준선 `desktop-01.png`에 `TOP-SECRET-LOCAL-FILE-CONTENT-12345`와 `/etc/hosts` 전체가 보인다(눈으로 확인). 새 모듈은 프레임 둘 다 빈 칸이다. 마젠타 판정 R1 세 변형: 기준선 391376 / 392176 / 0(`data:` 중첩은 원래 안 새는 것으로 관측), 새 모듈 0 / 0 / 0, 세 변형 모두 `complete`.
- PoC2(루프백 수신 소켓): 기준선 HITS 6건(`GET /iframe /embed /object` × 2뷰포트, 감사자 재현과 동일), 새 모듈 HITS `[]`, `complete`.
- R3 합성 보고서(`r3-synthetic.out`): 기준선(= `f0926e2`의 모듈, git에서 읽어 임시 모듈로 로드) 두 뷰포트 3타일 `[1568, 1568, 377]` / scroll_height 3513, 새 모듈 동일. 라이브 초안 사본 `0ffb8f9e…`(`r3-live-draft.out`): 기준선·새 모듈 모두 데스크톱 13타일(마지막 553)·scroll_height 19369, 모바일 19타일(마지막 1376)·29600 — 기록값(P39)과 같고 두 모듈이 서로 같다. 한글 본문 + `<meta charset>` 없음 초안의 타일 SHA-256도 기준선과 새 모듈이 같다(`charset-probe.out`: `Content-Type: text/html`에 charset을 붙이지 않은 서빙이 `file://` 로드와 같은 해석).
- 기본 `pytest backend/tests -k goose`에서 라이브 시험 4개는 `skipped`로 집계된다(`default-run-live-skipped.out`; 환경 변수 없음 3개 + R3 라이브 초안 경로 없음 1개).

**6. AC-013 #6 (같은 커밋 묶음의 세 기록).**
- (가) 규칙 번호 검사(007 AC-AIR7-011 #4 블록을 `sed`로 `rulenum.py`에 그대로 추출해 `python3 -B -I rulenum.py backend/goose_harness_src/harness-instructions.md`): 출력 `rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` / `rule numbering ok` (`rulenum.out`).
- (나) `python -B -m backend.services.goose_harness`로 재생성한 매니페스트를 커밋 파일과 `diff`: 출력 없음, 종료 0(`manifest-diff.out`). 매니페스트의 변경은 `CLAUDE.md` 해시 한 줄(`64ceebda… → e5c3fd9b…`, 지침 파일의 새 SHA-256)뿐이다. 매니페스트는 손으로 고치지 않고 위 명령의 출력으로 덮어썼다.
- (다) `shasum -a 256 backend/goose_harness_src/claude-settings.json` = `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3` 불변(`settings-sha.out`). 벤더링 스킬은 건드리지 않았다.
- 라이브 하네스(읽기 전용 관찰): `~/.goose-harness/CLAUDE.md` sha256 `64ceebda…`(= 이전 매니페스트 값)·수정 시각 21:36:04가 작업 시작 전(`harness-before.txt`)과 커밋 직전에 같다. 커밋 직후 값은 반환 보고에 적는다. 설치본은 서버 재시작 때 새 지침으로 바뀌므로 이 작업이 만든 변경이 아니다.

**7. 시험 집계.** `pytest backend/tests -k goose -q` 기준선 `548 passed, 214 deselected` → 변경 후 `565 passed, 4 skipped, 214 deselected`(새 시험 17개: 캡처 8, 리뷰 5, 서비스 2, 하네스 2 + 기존 argv 시험 확장). 네트워크 가드 기록 0건(가드 teardown 단언 통과). `ruff check`(시스템 `python3 -m ruff`) 변경 파일 전부 통과.

**8. conftest 변경 (AC-009 (5) 가드 회피 결정).** `backend/tests/conftest.py`의 `_is_goose_test`가 `goose_real_browser` 표지(`request.node.get_closest_marker`)가 있으면 False를 돌려준다 — 한 줄 조건과 주석뿐이다. 표지는 `pyproject.toml`의 markers에 등록했다. 표지는 새 파일 `test_goose_screenshot_live.py`의 `pytestmark`에만 있고, 같은 `pytestmark`의 `skipif`가 `AI_REPORT_GOOSE_REAL_BROWSER_TESTS=1`과 브라우저 존재를 요구하므로 기본 실행에서 가드는 바뀌지 않는다. 다른 시험의 가드는 약화하지 않았다.

**9. SPEC과 어긋나거나 정밀하지 않은 점 (manager-spec 재위임 대상).**
1. **AC-014 (15)의 기대 목록.** `[review_not_completed, tile_not_read]`는 심은 `audit-review.json`이 있을 때만 성립한다. 심은 기록이 없으면 조건 13이 더해져 `[review_not_completed, tile_not_read, no_audit_review]`다(서비스의 기존 삭제 실패 시험과 같은 이유). (15)는 "(14)의 심은 항목 중 하나"라고만 적어 심은 기록·`final/`의 유무를 정하지 않았다. 구현은 `review/`를 **먼저** 비워서, 비우기 실패 시 `audit-review.json`·`final/`을 지우기 전에 멈춘다 — 그러면 (13)과 같은 목록이 나오고, 두 경우를 모두 시험했다.
2. **`data:` 이미지는 이미 렌더되지 않는다.** `Network.setBlockedURLs ["*"]`가 이 브라우저에서 `data:` 이미지도 막는다(`data-image-finding.out`: 크기 속성 없는 300×200 `data:image/png` — 차단 켠 상태 초록 화소 0·마지막 타일 377px, 차단을 끄면 60000화소·558px). 기준선(`f0926e2`)도 똑같다. design §3.3·P38은 "정상 보고서가 `data:image/png`를 쓴다"를 전제로 `data:` 예외와 `img-src data:`를 정했지만, 현재 캡처에서는 그 이미지가 타일에 나타나지 않는다. 결과: (o) `data:`도 실패시킴 변형은 R3에서 RED가 되지 않고(AC-009 (6)(o)의 "이미지가 사라진다"는 관측 불가) 핸들러 계약 시험의 `data:` 행만 잡는다. 제품 후속 후보: 감수자는 로고 같은 `data:` 이미지를 화면에서 못 본다.
3. **`data:` 중첩 iframe 변형은 이 브라우저에서 원래 새지 않는다**(층 없음 행 마젠타 0). R1의 세 번째 변형은 회귀 방지용이며 `data:` 예외가 우회로가 되지 않음을 *증명*하지는 못한다.
4. **격리 적용 횟수.** design §3.2 단계 2는 "뷰포트마다" 격리를 적용한다고 읽히지만 `Fetch.enable`·`setAutoAttach`는 세션에 지속되므로 브라우저 시작 직후 **한 번** 적용한다(AC (3)-1의 "한 번씩"과 맞다). 격리 실패는 두 뷰포트 모두 `error`다(`browser_start_failed:…`). 이벤트 처리 실패 뒤에는 `_broken`으로 두 번째 뷰포트도 열지 않는다(SPEC은 "해당 뷰포트"만 error라 적음 — 더 엄격).
5. **(3)-2 해석.** 대상이 붙으면 `Runtime.runIfWaitingForDebugger`는 `waitingForDebugger` 값과 무관하게 항상 보낸다(false여도 무해). AC (4)(나) 시험은 자식 대상 설정 중 끼어드는 페이지 세션 요청 응답이 정당하므로 attach 이벤트만 주입했다(AC 문구 "어느 경우에도 통과시키지 않음"은 끼어드는 이벤트가 없을 때의 보장이다).
6. **응답 비대기.** `Fetch.fulfill/continue/failRequest`의 오류 응답은 기다리지 않는다(이미 사라진 요청의 오류가 방어를 깨뜨리지 않으며, 대기하면 큐가 쌓인 요청마다 재귀가 깊어진다). SPEC은 이 응답 처리를 정하지 않았다.

**10. 미검증(Gaps).** (i) 이 호스트의 `chrome-headless-shell` 1243(HeadlessChrome 153.0.8010.12) 하나만 관측했다 — 다른 빌드·Linux는 미관측. (ii) R1·R2는 한 번씩의 관측이다(대상 연결 경합이 부하에서 드러나는지는 못 봤다). (iii) R2는 캡처 뒤 0.5초만 더 기다렸다. `<meta http-equiv=refresh content="3;…">`의 이동이 캡처 종료 뒤에 일어났다면 관측하지 못한 것이다(그 경로는 A1·`setBlockedURLs`가 막도록 설계됨). (iv) `Fetch`가 일시 정지하지 않는 요청 종류는 PoC 벡터에 걸리지 않았다는 사실만 안다. (v) 규칙 10-11이 모델 행동을 바꾸는지는 미관측(문구 존재 시험뿐, 권한은 D3으로 그대로). (vi) 실제 `claude` 감수 세션·서버 재시작·AC-018 재관측은 하지 않았다(리드의 필수 사후 검증). (vii) 독립 보안 재검토(PoC 재실행 포함)는 이 레인의 일이 아니다. (viii) 벤더링 스킬 불변은 `git status`에 `backend/goose_harness_src/skills`가 없다는 것과 기존 시험(`vendored_skills_are_unchanged`)의 GREEN으로만 확인했다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-10-21   # 날짜만 기록, 시각은 기록하지 않음
run_commit_sha: "M7 bc56cc7 (보안 강화). 이전 마일스톤: M4 86e4301, M5 33e3c18, M6 증거 9a7b9af"
run_status: run-complete-security-hardened   # 1차 보안 검토 FAIL(S1·S2 높음) → M7 수정 → 독립 재검토 PASS
ac_total: 22   # AC-AIR6-001~022 (acceptance.md 고유 AC-AIR6-* 재계산: 22)
ac_live_gate: "AC-AIR6-018 통과(M6, 1회차, 리드 판정)"
test_goose_isolated: "565 passed, 4 skipped, 214 deselected"   # 오케스트레이터 직접 실행. skipped 4개 = 실제 브라우저 시험(AI_REPORT_GOOSE_REAL_BROWSER_TESTS 환경 변수로만 켜짐)
coverage_four_modules_pre_m7: "96% (job_service 96, review 94, runner 98, screenshot 95) — M7 이전 측정"
lint_and_types: "ruff 통과, tsc 0 오류, eslint 0 오류"   # 오케스트레이터 직접 실행
frontend_tests: "vitest 702 passed (M4 시점 측정, M7 이후 재실행하지 않음)"
security_poc_after_m7: "PoC1(file:// iframe + 심은 비밀) 타일 빈 칸 · PoC2(루프백 수신) HITS []"
manifest: "재생성 결과가 커밋 파일과 동일(diff 없음)"
claude_settings_sha256: "e8b527cc… 불변"
live_harness: "~/.goose-harness 손대지 않음"
security_review: "1차 FAIL(S1·S2 높음, 검증됨) → M7(bc56cc7) → 독립 재검토 PASS (.moai/reports/t18/security-rereview.md)"
reversal_checks: "M7 되돌림 RED 관측 §E.2 M7 4절 (변형마다 RED 관측 후 바이트 단위 복원)"
```

Gaps(이 단계가 관측하지 않은 것): §E.2 M7 10절과 아래 §E.4 "알려진 한계"에 모았다.

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_complete_at: 2026-10-21
sync_commit_sha: pending-backfill   # 이 파일을 담는 커밋이라 자기 SHA를 적을 수 없음
sync_status: audit-ready
sync_route: 카드 워크트리 `.claude/worktrees/t18`(브랜치 WT-goose-review-pass) 커밋, push·PR 없음
sync_base_sha: bc56cc7
sync_auditor_score: "0.853 PASS-WITH-DEBT (가중 평균, 조화평균 0.844; Functionality 0.88 · Security 0.82 · Craft 0.88 · Consistency 0.80; 차단 결함 0건). 보고서 .moai/reports/t18/sync-audit.md. 지적 F1(AC-018이 M7 이전 빌드에서 관측됨 — 재관측·완화 해제 대기, CHANGELOG (p)에 명시)·F4(CHANGELOG (q))·F7(문구 정정)·F9(이 필드)는 후속 문서 커밋에서 반영. 미반영 이월: F2(AC-017 (4) 되돌림 RED 관측 기록 없음), F3(가설, finish_review 예외 시 위조 영수증 잔존), F5(@MX:ANCHOR 4개 > 상한 3), F6(스킬 불변 시험이 기준 커밋 없으면 건너뜀), F8(작업 시간 6초 어긋남, 원인 미기록)"
frontmatter_status_transitions:
  spec.md: "draft → completed (updated: 2026-10-21 유지). 3단계 닫기(draft → in-progress → implemented → completed)를 이 sync 커밋 하나에 합침"
  plan.md / acceptance.md / design.md / research.md / progress.md: "YAML frontmatter가 없다. plan.md 3행 본문 '상태: draft'는 본문이라 이 단계가 고치지 않았다(Gap)"
b12_self_test_a: "grep -c 'SPEC-AI-REPORT-006' CHANGELOG.md → 1 (추가 전). 그 1건은 007 항목 안의 '알려진 한계 (c)'가 006을 가리키는 교차 참조이고 006 자체 항목 제목은 없었다 → 중복 아님, 진행"
b12_self_test_b: "acceptance.md 고유 AC-AIR6-* 22개 = CHANGELOG 'AC-AIR6-001~022 22개'. 앵커 grep 원시 고유 수 41은 본문의 축약 별칭 포함"
b12_self_test_c: "CHANGELOG 새 항목에 적은 경로·커밋은 ls 및 git log로 존재 확인 (아래 증거 절)"
changelog_entry_position: "[Unreleased] 첫 항목 — ### Added (SPEC-AI-REPORT-006 v0.3.4 …), 기존 첫 항목 SPEC-AI-REPORT-007 앞"
moai_spec_lint: "WARNING StatusGitConsistency — 이 커밋 전 측정: frontmatter 'draft' vs git 추정 'in-progress'. 0 error(s), 1 warning(s), exit 0. 커밋 후 재측정값은 반환 보고에 적는다"
```

### sync 단계 산출물

- `.moai/specs/SPEC-AI-REPORT-006/spec.md`: frontmatter `status`만 `completed`로 바꿨다(`updated`는 이미 2026-10-21). 본문은 손대지 않았다.
- `.moai/specs/SPEC-AI-REPORT-006/progress.md`: §E.3·§E.4를 채웠다.
- `CHANGELOG.md`: `[Unreleased]` 첫 항목으로 SPEC-AI-REPORT-006을 더했다. 형식은 007 항목(`### Added (SPEC-… vX — 제목, 카드, 날짜)` + 굵은 글씨 하위 항목 + 검증 + 알려진 한계 + 근거)을 따랐다.
- `README.md`: SPEC 표·하단 SPEC 목록에 006 행을 더하고, 알려진 한계에서 "감수 단계가 없다"는 낡은 문장을 현재 상태로 고쳤다.

### 증거 (이 sync 실행에서 직접 실행, 격리: `AI_REPORT_GOOSE_HARNESS_DIR=.moai/state/verify/t18-docs/h`, `-B -p no:cacheprovider`, `HOME` 불변)

- 시험: `coverage run … -m pytest -p no:cacheprovider backend/tests -k goose -q` → `565 passed, 4 skipped, 214 deselected, 1 warning in 35.46s`
- 커버리지 재측정(M7 이후, `--include`로 네 모듈만, `--cov=` 미사용): `goose_job_service.py` 372문 16누락 **96%** · `goose_review.py` 294문 15누락 **95%** · `goose_runner.py` 361문 10누락 **97%** · `goose_screenshot.py` 305문 13누락 **96%** · 합계 1332문 54누락 **96%**
- 라이브 하네스: `stat -f %Sm ~/.goose-harness/CLAUDE.md` → `Oct 21 21:36:04 2026` (시험 실행 뒤, 커밋 뒤 값은 반환 보고)

### 독립 보안 재검토 결과 (`.moai/reports/t18/security-rereview.md`, 기준 HEAD bc56cc7, 판정 **PASS**)

검토자는 새 PoC를 `.moai/state/verify/t18-resec/`에서 실행했고 모든 벡터를 실제 문서 CSP(층 B)와 CSP를 `default-src *`로 푼 상태(층 A1·A2만) 두 번씩 돌렸다. 바깥으로 나가는 요청도 `file://` 내용도 타일에서 확인되지 않았다. 층 A1(모든 대상의 Fetch 가로채기)은 CSP 없이도 혼자 막았다. 이전 높음 2건(S1 file:// iframe, S2 루프백·네트워크 요청)은 닫혔다. 해결되지 않은 높음·치명 없음.

| ID | 심각도 | 근거 등급 | 내용 |
|---|---|---|---|
| F1 | 중간 | 가설(HYPOTHESIS: 코드·설정 읽기, 실제 `claude`에 돌리지 않음) | 감수 세션이 1차 세션과 같은 `claude-settings.json` 권한을 쓴다(`WebSearch`·`WebFetch`·`Agent`·`Skill`·`Read(./**)`·`Write(./runs/**)` 허용). 규칙 10-11은 문구일 뿐이다 |
| F2 | 낮음 | 검증됨(VERIFIED) | 외부 파일에 대한 하드링크 초안이 `_check_draft`를 통과해 HTML로 렌더됨. 지금은 `ln`이 Bash 허용 밖이라 악용이 어렵다 |
| F3 | 낮음 | 가설(재현 안 함) | `_check_draft`와 `read_bytes()` 사이의 TOCTOU. 수정은 F2와 같다(파일 기술자 하나) |
| F4 | 낮음 | 검증됨 | DevTools 포트(127.0.0.1)가 인증 없이 열려 있음. 같은 호스트의 다른 사용자가 `PUT /json/new`로 `file://` 대상을 열 수 있음 |
| F5 | 낮음 | 검증됨(가용성, 안전한 쪽으로 실패) | 심은 `screens` 일반 파일이나 매우 큰 초안은 최종본 불인정으로 끝난다. 예산(60초)과 프로세스 정리는 매번 지켜졌다 |
| F6 | 정보 | 검증됨 + 코드 읽기 | 브라우저 자식 환경은 HOME·LANG·PATH·SHELL·TMPDIR·USER만(S5 검증). 화면 밖에 둔 내용은 타일에 없다(감수 범위 공백). `review/` 비우기(S9)는 코드 읽기만 |

검토자가 시험하지 않은 것: 실제 `claude -p` 감수 세션(프롬프트 주입, F1 악용, WebFetch 유출), `_empty_review`·`_delete_planted`의 실제 심은 파일 실행, F3 경합, 다른 Chrome 빌드·Linux, 적대적 초안으로 작업 서비스 끝에서 끝까지.

### 알려진 한계 (근거 등급 표기)

- (a) **conftest에 하네스 경로 격리가 없다** — lifespan을 도는 테스트가 실제 `~/.goose-harness`를 덮어쓸 수 있음(후속 카드 후보). 리드가 이 사고를 보고했다(원인: `AI_REPORT_GOOSE_HARNESS_DIR` 미격리 + `TestClient(app)` lifespan의 `install_at_startup()`). 007 sync와 같은 문제이며 이 카드 이전부터 있었다. [리드 보고 — 007 sync 기록에서 가져옴]
- (b) **렌더러의 390px 모바일 차트 잘림** — M6 라이브 감수가 찾았다. 제품 후속 후보(이 SPEC 범위 밖). 잘림이 진짜 결함인지는 이 기록 작성자가 렌더 결과를 보고 확인하지 않았다. [리드 보고, 라이브 관측]
- (c) **라이브 `final` 경로 미관측** — AC-AIR6-018은 `draft`/`visual_not_pass`로 끝나는 경로만 봤다. `final` 인정은 AC-AIR6-022 격리 시험이 담당한다. [미관측]
- (d) **AC-AIR6-004(b)·AC-AIR6-020(c)·AC-AIR6-022의 현재 모드 신선도 미관측** [미관측]
- (e) **AC-AIR6-013 #5(서버 재시작 뒤 설치본 무결성)** — M6에서 리드가 재시작 뒤 33개 파일 일치와 규칙 10 설치를 관측했다. 그러나 M7이 지침을 다시 바꿔(규칙 10-11, `CLAUDE.md` 해시 `64ceebda… → e5c3fd9b…`) 설치본(`64ceebda…`)은 다음 서버 재시작 때 맞춰진다. M7 지침본에 대한 재시작 뒤 무결성은 미관측. [리드 관측(M6 시점) + 미관측(M7 시점)]
- (f) **S3 잔여 / F1 중간** — 감수 세션이 1차 세션과 같은 권한을 갖는다. 규칙 10-11은 지침 수준일 뿐이다. 후속: `--disallowedTools` 좁히기. [가설]
- (g) **F2·F3 낮음** — 하드링크나 교체된 `draft/report.html`이 `_check_draft`를 통과한다. 악용에는 `ln`이 필요하고 Bash 허용 목록에 없다. 수정: `O_NOFOLLOW`와 `st_nlink` 검사를 파일 기술자 하나로. [F2 검증됨 / F3 가설]
- (h) **F4 낮음** — CDP 디버그 포트가 127.0.0.1에서 인증 없이 열림. 후속: `--remote-debugging-pipe`. [검증됨]
- (i) **F5 낮음(가용성)** — 심은 `screens` 일반 파일이나 매우 큰 초안은 최종본 불인정(안전한 쪽으로 실패)으로 끝난다. [검증됨]
- (j) **S7·S8 이월** — 스트림 줄 한도 4 MiB 대 타일 8 MiB 불일치(S7), 완료·취소 경로의 영수증 임시 파일 이름 충돌(S8). [가설, 시험하지 않음]
- (k) **`data:` 이미지가 이미 렌더되지 않는다** — `Network.setBlockedURLs ["*"]`가 막는다. 감수자는 `data:` 이미지(로고 등)를 화면에서 못 본다. 제품 후속 후보. [검증됨(§E.2 M7 9절 2번)]
- (l) **관측 범위**: macOS의 `chrome-headless-shell` 153.0.8010.12 하나만 관측했다. Linux는 미관측. 규칙 10-11이 모델 행동을 바꾸는지도 미관측. [미관측]
- (m) **AC-AIR6-009 (6)(o)의 "이미지가 사라진다"는 R3로 관측할 수 없다** — (k) 때문이다. 핸들러 계약 시험의 `data:` 행만 잡는다. [검증됨]
- (n) **AC-AIR6-014 (15)의 기대 목록**은 심은 `audit-review.json`이 있는지에 따라 달라진다. SPEC 문구 후속 — manager-spec 재위임 대상. [검증됨(§E.2 M7 9절 1번)]
- (o) **격리는 브라우저 세션당 한 번 적용한다** — SPEC 오류 문구의 "뷰포트마다"보다 엄격하다. 격리 실패는 두 뷰포트 모두 `error`다. [검증됨(§E.2 M7 9절 4번)]

### sync 단계에서 하지 않은 것

- spec.md의 `status` 외 필드, plan.md·acceptance.md·design.md·research.md 본문, `.moai/reports/t18/security-rereview.md`, 코드·테스트·하네스 파일은 고치지 않았다.
- push·PR은 하지 않았다. sync-auditor는 이 커밋 뒤에 돈다(점수 칸은 비움).
- MX 태그 호출자 수 계산, 문서 링크 검사기, 마크다운 린터는 실행하지 않았다.
