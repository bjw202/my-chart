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
| 021 | PASS (판정 부분) | 조건 17 제거·표지 완화·"시작" 한정 모두 RED. 지침 문구(규칙 9)는 M5 |
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

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
