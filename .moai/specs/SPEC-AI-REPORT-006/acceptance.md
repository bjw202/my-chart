# SPEC-AI-REPORT-006 — 인수 기준

버전 0.1.0 · 요구사항은 `spec.md §4`(REQ-AIR6-001~018). 각 AC는 Given-When-Then, 실행 명령, 기댓값, 그리고 **이 AC가 잡아내는 틀린 구현(대조)** 과 **잡지 못하는 것** 을 적는다. 대조 항목은 run 단계에서 실제로 되돌림을 적용해 RED를 관측해야 GREEN으로 기록할 수 있다(lessons #9). 관측하지 못한 대조는 `progress.md §E.2`에 Gap으로 남긴다.

## §A 공통 실행 조건

- Python 명령은 서버용 가상환경 `/Users/byunjungwon/Dev/my_chart/.venv`(코드 폴더와 다른 경로)의 `python`으로 실행한다. 아래 `PY`는 그 환경의 `python`이다.
- 테스트 함수 이름에 AC 번호 꼬리표(`air6_001` 등)를 넣어 `-k`로 고를 수 있게 한다. 테스트 파일 이름은 `test_goose_` 접두어를 지켜 공용 네트워크 가드(005)가 자동 적용되게 한다.
- 프론트 테스트는 `npm --prefix frontend run test -- <필터>`로 돌린다(`--root`를 함께 주지 않는다 — 005 기록).
- `$S`는 세션 증거 폴더 `.moai/state/verify/<session>/`다.
- 모든 테스트는 실제 브라우저·실제 `claude`·실제 네트워크를 쓰지 않는다(REQ-AIR6-017). 가짜 드라이버·가짜 실행 파일은 `design.md §10`.
- 픽스처는 run 단계 M1이 research.md §2 P13·P14 방식으로 얻은 값(라이브 초안 `a5becbb9…`의 높이 데스크톱 20160px·모바일 30683px, 문서 폭 일치)과 합성 값이다. 기댓값 리터럴이 M1 관측과 다르면 코드 작성 전에 `progress.md`에 기록하고 manager-spec 재위임으로 이 문서를 고친다.
- 수치 한도(60초, 24타일, 1568px, 8 MiB, 900초)는 초기값이며 M1·M6이 관측으로 확정한다. 바뀌면 테스트는 spec.md의 값이 아니라 모듈 상수를 임포트해 단언하고, spec.md는 manager-spec 재위임으로 고친다.

## §B 고정 키 집합 (AC-006·007·012·015가 집합 동등으로 검사)

- `screens/index.json` 최상위: `schema_version`, `source`, `preview_sha256`, `started_at`, `finished_at`, `outcome`, `browser`, `viewports`. `browser`: `name`, `version`, `path_kind`. `viewports[]`: `name`, `width`, `status`, `error`, `metrics`, `tiles`. `metrics`: `scroll_width`, `client_width`, `scroll_height`, `horizontal_overflow`. `tiles[]`: `file`, `y`, `width`, `height`, `bytes`, `sha256`
- `review/context.json` 최상위: `schema_version`, `job_id`, `code`, `now`, `input`, `preview`, `screens`, `audit_review_path`, `audit_output_path`, `final_dir`, `copy_into_review_record`. `copy_into_review_record`: `input_sha256`, `preview_sha256`, `reviewed_at`, `mode`
- `review/receipt.json` 최상위: `schema_version`, `outcome`, `started_at`, `finished_at`, `process`, `hashes`, `draft_unchanged`, `screens`, `audit_review`, `visual_admissible`, `reasons`. `hashes`: `input_start`, `input_end`, `preview_start`, `preview_end`. `screens`: `outcome`, `index_sha256`, `tiles_expected`, `tiles_read`
- 값 집합: `index.outcome` ∈ {complete, partial, unavailable, failed, disabled}; `viewport.status` ∈ {ok, error, too_tall, skipped}; `receipt.outcome` ∈ {reviewed, review_failed, timeout, cancelled, integrity_failed, disabled}
- 시각 필드(`started_at`, `finished_at`, `now`): 시간대 포함 ISO-8601, 오프셋 `+09:00`

## §C 인수 기준

### AC-AIR6-001 — 후처리 위치와 순서 (REQ-AIR6-001)

- Given: 가짜 실행기(호출 기록, `draft/report.html`을 만들고 `done`/`draft` 반환), 가짜 무결성 검사(호출 기록, 두 번째 호출만 실패시킬 수 있음), 가짜 캡처기·가짜 감수기(호출 기록, 캡처기는 `asyncio.Event`를 기다릴 수 있음), 임시 `runs` 폴더
- When: (1) `start("020150", …)` 후 캡처기가 대기하는 동안 같은 종목·다른 종목 `start`를 각 1번 더 부르고 이벤트를 푼다. (2) 두 번째 무결성 검사를 실패시킨다. (3) 실행기가 `draft/report.html`을 만들지 않고 `done`을 반환한다. (4) 캡처기·감수기 없이 만든 서비스(생성자 기본값)
- Then: (1) 첫 `start`는 캡처기가 끝나기 전에 `started`를 돌려준다(1초 안). 대기 중 같은 종목 → `existing`, 다른 종목 → `busy`. 호출 기록 순서가 정확히 `["integrity","runner","integrity","screenshot","review"]`이고 마지막에 작업은 `done`. (2) 호출 기록 `["integrity","runner","integrity"]`, 캡처기·감수기 호출 0, `review/receipt.json`의 `outcome == "integrity_failed"`. (3) 캡처기·감수기 호출 0. (4) 기록 `["integrity","runner"]`, `screenshot`·`review` 진행 이벤트 0, 영수증 파일 없음
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_001 -q`
- 잡는 구현: (a) 후처리를 `start()` 잠금 안에서 기다림 → 첫 `start`가 1초 안에 안 돌아옴, (b) 감수를 캡처 앞에 둠 → 순서 불일치, (c) 재검사 누락 → 두 번째 `integrity` 없음, (d) 재검사 실패 때 그대로 진행 → (2)에서 호출 0 단언 실패, (e) 생성자 기본값을 실제 구현으로 둠 → (4)에서 `screenshot` 등장, (f) draft 존재 확인 누락 → (3)에서 호출 발생
- 잡지 못하는 것: 실제 브라우저·실제 `claude`에서의 동작(AC-006~011 담당, 라이브는 AC-018)

### AC-AIR6-002 — 후처리 중 취소 (REQ-AIR6-002)

- Given: (1) `asyncio.Event`를 영원히 기다리는 가짜 캡처기, (2) 같은 방식의 가짜 감수기, (3) 실제 캡처 모듈 + 테스트 임시 폴더의 가짜 브라우저 실행 파일(`AI_REPORT_GOOSE_BROWSER`, 오래 자는 셸 스크립트), (4) 실제 `run_review` + 오래 자는 가짜 `claude` 스크립트. 각각 가짜 실행기
- When: 후처리 중 `cancel(job_id)`, 별도 작업에서 `shutdown()`. 테스트 전체에 `asyncio.wait_for(..., 5)` 상한
- Then: 모든 경우 작업 상태 `cancelled`, 마지막 이벤트 종류 `cancelled`, 상한 안에 끝남, `receipt.outcome`이 있으면 `cancelled`, `select_report`가 `final`을 내지 않음. (3)·(4)는 가짜 프로세스의 프로세스 그룹에 `os.killpg(pgid, 0)`을 보내 `ProcessLookupError`(남은 프로세스 0)
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py backend/tests/test_goose_screenshot.py backend/tests/test_goose_review.py -k air6_002 -q`
- 잡는 구현: (a) 서비스의 fail-open 처리가 `except BaseException`으로 취소를 삼키고 다음 단계로 진행 → (1)에서 감수기 호출 1, (b) 브라우저 프로세스 하나만 죽이고 그룹은 안 죽임 → (3)에서 `killpg`가 성공(남은 프로세스 있음), (c) 감수 프로세스 그룹 정리 누락 → (4) 동일, (d) 후처리 호출을 `_run`의 `try` 밖에 둠 → 상태가 `cancelled`로 기록되지 않음
- 잡지 못하는 것: 취소 시 이미 저장된 화면 파일 정리(요구하지 않음 — 작업 폴더 보존 규칙에 맡김)

### AC-AIR6-003 — 진행 단계와 프론트 표시 (REQ-AIR6-003)

- Given: 가짜 캡처기·감수기(호출되는 순간 `job.events` 사본 저장), 가짜 감수기는 스트림 줄로 `render_report.py … --final …` `Bash` 호출을 흘려 보낸 것처럼 `render_final` 신호를 낸다
- When: 작업을 끝까지 실행해 이벤트를 읽는다; 스위치 `0`인 경우와 캡처기·감수기 없는 서비스로 한 번씩 더 실행한다; 프론트 단위 테스트를 실행한다
- Then: 캡처기 진입 시점 사본에 `progress/screenshot`이 정확히 1개(그 시점에 `review`는 0개), 감수기 진입 시점 사본에 `review`가 정확히 1개. 전체 이벤트에서 `screenshot`·`review`·`render_final`은 각각 1개이고 순서가 `screenshot` < `review` < `render_final`, 모두 `goose_start`보다 뒤. 스위치 `0`·미주입 경우에는 세 단계 이벤트 0개. 프론트: `GOOSE_STAGES`가 정확히 `[dart_prefetch, goose_start, plan, research_tick, fetch_start, fetch_done, compose, render_draft, audit, session_end, screenshot, review, render_final]`, 진행 패널에 `화면 캡처`·`감수`가 렌더링되고 `applyGooseStage`가 두 단계를 `reached`에 넣음. 갱신된 기존 테스트 2개(`gooseJob.test.ts`, `ProgressPanel.test.tsx`) 통과
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_003 -q`; `npm --prefix frontend run test -- gooseJob ProgressPanel`
- 잡는 구현: (a) 백엔드만 보내고 프론트 목록에 없음 → `reached`에 없음, (b) 단계를 시작 후에 보냄 → 진입 시점 사본에 0개, (c) 단계를 두 번 보냄 → 개수 단언 실패, (d) 꺼진 경우에도 보냄 → 0개 단언 실패, (e) `render_final`을 `session_end` 앞에 둠 → 고정 목록 단언 실패, (f) 감수 세션의 모든 도구 호출을 진행 이벤트로 중계 → `audit`·`render_draft`가 감수 단계에서 다시 나와 개수 단언 실패
- 잡지 못하는 것: 실제 화면 배치(라이브 AC-018 관측 때 함께 눈으로 확인, 비게이팅)

### AC-AIR6-004 — 끄기 스위치 (REQ-AIR6-004)

- Given: 호출 횟수를 세는 가짜 캡처기·감수기, 가짜 실행기(`draft/report.html`과 `final/report.html` + `delivery_allowed: true`를 둘 다 만든 것으로 가정), `AI_REPORT_GOOSE_REVIEW=0`
- When: 작업 실행
- Then: 캡처기·감수기 호출 0, `screenshot`·`review`·`render_final` 이벤트 0, `review/receipt.json`의 `outcome == "disabled"`, 실행기 호출 1, 전달 상태 `draft`(영수증이 인정하지 않으므로 `final/`이 있어도 `draft`). 같은 테스트에서 변수 미설정 시 캡처기 1·감수기 1 호출(대조)
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_004 -q`
- 잡는 구현: (a) 스위치 무시 → 호출 1, (b) 스위치를 감수기 안에서만 확인 → 캡처기 호출 1, (c) 끈 경우 영수증을 쓰지 않음 → 파일 없음, (d) 끈 경우 실행기까지 건너뜀 → 호출 0
- 잡지 못하는 것: 서버 재시작 없이 환경 변수를 바꾼 경우(프로세스 환경은 시작 시 고정 — 매 작업마다 읽으므로 테스트에서는 `monkeypatch`로 충분)

### AC-AIR6-005 — 후처리 실패해도 초안으로 끝남 (REQ-AIR6-005)

- Given: 실패 유형 행렬. 캡처기: 예외 발생 / `unavailable` 색인 반환. 감수기: 예외 / 비정상 종료(`review_failed`) / 시간 초과(`timeout`) / 종료 0인데 `audit-review.json` 없음
- When: 각 경우로 작업 실행
- Then: 모든 경우 작업 `done`, 전달 상태 `draft`, `error` 이벤트 0. 캡처만 실패한 경우에도 감수기는 호출되고 `review/context.json`의 `screens.outcome`이 `unavailable`/`failed`. 감수기 실패 경우 영수증 `outcome`이 각각 `review_failed`/`timeout`
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_005 -q`
- 잡는 구현: (a) 캡처 실패가 작업을 `error`로 만듦, (b) 캡처 실패 시 감수 건너뜀 → 감수기 호출 0, (c) 감수기 예외를 삼키지 않고 작업 실패 처리, (d) 시간 초과를 `done`/`final`로 처리 → 영수증 outcome 불일치
- 잡지 못하는 것: 취소(AC-002 담당)

### AC-AIR6-006 — 캡처 대상·뷰포트·타일 (REQ-AIR6-006)

- Given: 가짜 `BrowserDriver`(호출 인자 기록, 페이지 높이 데스크톱 3200px·모바일 4000px, 결정적 PNG 바이트 반환), 임시 작업 폴더에 `draft/report.html`
- When: 캡처 실행; 별도로 `draft/report.html`을 심볼릭 링크(작업 폴더 밖 파일을 가리킴)로 바꿔 실행
- Then: 드라이버 호출 기록의 URL이 `file://`로 시작하고 값이 `resolve()`한 `draft/report.html` 경로와 정확히 같다. 데스크톱 호출은 폭 1280·`mobile=false`, 모바일 호출은 폭 390·`mobile=true`. 스크립트 비활성 호출이 첫 `navigate`보다 앞선다. 타일 높이 목록이 데스크톱 `[1568, 1568, 64]`, 모바일 `[1568, 1568, 864]`이고 `y` 오프셋이 `0, 1568, 3136`. 파일 이름이 정확히 `desktop-01.png`~`desktop-03.png`, `mobile-01.png`~`mobile-03.png`이며 `screens/` 안의 파일 집합이 이 6개 + `index.json`. 심볼릭 링크 경우: 드라이버 호출 0, 해당 색인 `outcome`이 `failed`(또는 `unavailable`이 아닌 오류 사유 기록)
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_006 -q`
- 잡는 구현: (a) 타일 없이 한 장 전체 저장 → 타일 목록 불일치, (b) 두 뷰포트가 같은 폭 → 폭 단언 실패, (c) 모바일 에뮬레이션 누락 → `mobile` 단언 실패, (d) 스크립트 비활성이 `navigate` 뒤 → 순서 단언 실패, (e) 보고서 내용에서 뽑은 문자열로 파일 이름 생성 → 이름 집합 불일치, (f) 심볼릭 링크를 따라감 → 드라이버 호출 발생
- 잡지 못하는 것: 실제 브라우저의 `clip` 동작(M1 관측 G3), 타일 이미지의 가독성(G4)

### AC-AIR6-007 — `screens/index.json` (REQ-AIR6-007)

- Given: AC-006과 같은 가짜 드라이버; 시나리오 (1) 두 뷰포트 성공, (2) 모바일만 드라이버 오류, (3) 둘 다 오류, (4) 브라우저 없음
- When: 캡처 실행 후 `index.json`을 읽는다
- Then: §B 키 집합과 정확히 동등(`set(keys) == 기대 집합`, 추가·누락 키 모두 실패). `preview_sha256`이 테스트가 `draft/report.html` 바이트에서 독립적으로 계산한 SHA-256과 같다. 각 타일 `sha256`·`bytes`가 실제 파일에서 계산한 값과 같다. 시각 필드는 `+09:00` 시간대 포함. `outcome`: (1) `complete`, (2) `partial`, (3) `failed`, (4) `unavailable`. 지표 4개 키가 각 뷰포트에 있고 가짜 드라이버가 준 값과 일치. `horizontal_overflow`는 `scroll_width > client_width`일 때만 참(경계값 `390/390` 거짓, `391/390` 참을 가짜 값으로 시험)
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_007 -q`
- 잡는 구현: (a) 키 이름 변경·누락 → 집합 동등 실패, (b) 시간대 없는 시각 → 형식 단언 실패, (c) 입력 JSON 해시를 `preview_sha256`에 기록 → 값 불일치, (d) 타일 해시를 디스크 파일이 아닌 메모리 바이트 사본에서 계산하되 쓴 뒤 달라진 경우 → 불일치(쓰기 후 읽어 확인), (e) `>=` 비교로 넘침 판정 → `390/390`에서 거짓이어야 하는데 참
- 잡지 못하는 것: 실제 페이지에서의 지표 정확도(M1 P14 관측 1건)

### AC-AIR6-008 — 한도와 정리 (REQ-AIR6-008)

- Given: 가짜 드라이버: (1) 모바일 페이지 높이 100000px(상한 24타일 초과), (2) 호출 하나가 예산을 넘겨 지연(테스트가 예산 상수를 작게 패치), (3) 9 MiB 크기 타일 반환, (4) 정상. 가짜 브라우저 실행 파일로 프로세스 그룹 확인(`AI_REPORT_GOOSE_BROWSER`)
- When: 캡처 실행(정상·실패·취소 각 경로)
- Then: (1) 모바일 `status == "too_tall"`, 모바일 타일 0개(일부만 저장하지 않음), 데스크톱은 `ok`, `outcome == "partial"`. (2) 예산 초과 뷰포트 `error`, 남은 뷰포트 `skipped`, 가짜 브라우저 그룹 종료. (3) 해당 뷰포트 `error`. 모든 경우(정상 포함) 종료 뒤 브라우저 프로세스 그룹이 없고(`killpg(…,0)` → `ProcessLookupError`) 임시 프로필 폴더가 존재하지 않는다
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_008 -q`
- 잡는 구현: (a) 타일 상한 없음 → (1)에서 타일 수 > 24, (b) 상한 초과 때 앞 24개만 저장 → 타일 0개 단언 실패, (c) 예산 미적용 → (2)가 끝나지 않음(`wait_for` 상한으로 RED), (d) 크기 상한 없음 → (3)에서 `ok`, (e) 임시 폴더를 성공 경로에서만 삭제 → 실패·취소 경로에서 폴더 잔존
- 잡지 못하는 것: 실제 브라우저의 메모리 사용

### AC-AIR6-009 — 격리 (REQ-AIR6-009)

- Given: 가짜 브라우저 실행 파일(받은 argv를 파일에 기록하고 잠), 가짜 드라이버, 보고서 HTML 안에 `--evil-flag`·`$(touch x)`·`</script>`가 든 제목 텍스트(보고서 내용에서 온 문자열)와 종목명 `A; rm -rf /`
- When: 캡처 실행
- Then: 기록된 argv의 모든 원소가 (고정 문자열 허용 집합) ∪ (`--remote-debugging-port=<정수>`) ∪ (`--user-data-dir=<임시 폴더 경로>`) ∪ (`about:blank` 또는 검증된 `file://` URL)에 속하고 보고서 문자열·종목명이 어느 원소에도 부분 문자열로 없다. 디버깅 포트는 루프백만(`--remote-debugging-address`가 있으면 `127.0.0.1`). 가짜 드라이버 호출 기록에 스크립트 비활성과 네트워크 차단 적용이 있다
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_009 -q`
- 잡는 구현: (a) 인자에 보고서·종목명 문자열 포함 → 부분 문자열 단언 실패, (b) 스크립트 비활성 호출 누락, (c) 네트워크 차단 누락, (d) 디버깅 주소 `0.0.0.0` → 루프백 단언 실패
- 잡지 못하는 것: 실제 브라우저가 외부로 요청하지 않는지(G3·G8 — M1 관측, 가능하면 로컬 수신 소켓으로 요청 0건 확인)

### AC-AIR6-010 — 브라우저 탐색 (REQ-AIR6-010)

- Given: 임시 폴더에 실행 권한 있는 가짜 브라우저 파일 A, 실행 권한 없는 파일 B, `PATH`에 고정 이름의 가짜 실행 파일 C
- When: (1) `AI_REPORT_GOOSE_BROWSER=A`, (2) `=B`, (3) 변수 없음 + `PATH`에 C, (4) 변수 없음 + 후보 전무
- Then: (1) A로 실행, `browser.path_kind == "env"`. (2) 실행 시도 0, `outcome == "unavailable"`, C가 있어도 C로 폴백하지 않음. (3) C로 실행, `path_kind == "path"`. (4) 실행 시도 0, `outcome == "unavailable"`, 사유 기록, 색인의 어느 필드에도 브라우저 절대 경로 없음
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_010 -q`
- 잡는 구현: (a) 환경 변수 무시 → (1)에서 C 사용, (b) 잘못된 변수일 때 조용히 폴백 → (2)에서 C 실행, (c) 후보 없음일 때 예외 → `unavailable` 아님
- 잡지 못하는 것: 이 호스트의 실제 설치 위치(M1이 관측, 문서화)

### AC-AIR6-011 — 감수 세션 호출 (REQ-AIR6-011)

- Given: `claude_bin`으로 지정한 가짜 `claude` 스크립트(argv·환경·cwd를 파일에 기록하고 합성 `stream-json`을 출력), 임시 하네스 경로(`AI_REPORT_GOOSE_HARNESS_DIR`), 부모 환경에 허용 목록 밖 변수(예: `OPENAI_API_KEY=canary`)
- When: `run_review(job_id, code, …)` 실행. 별도: `AI_REPORT_GOOSE_REVIEW_TIMEOUT=1`과 오래 자는 가짜 `claude`; 종료 0 정상
- Then: argv에 `--setting-sources project`, `--settings <하네스>/.claude/settings.json`, `--strict-mcp-config`, `--permission-mode dontAsk`, `--no-session-persistence`가 모두 있고 `--dangerously-skip-permissions`·`bypassPermissions` 문자열이 없다. 프롬프트에 작업 ID·6자리 코드·`감수 세션`이 있고 종목명(테스트가 준 `홍길동전자`)은 없다. cwd는 하네스 경로. 자식 환경에 `canary` 변수 없음. 시간 초과 경우 `timed_out == true`이고 그룹에 남은 프로세스 0. 정상 경우 `timed_out == false`
- 명령: `PY -m pytest backend/tests/test_goose_review.py -k air6_011 -q`
- 잡는 구현: (a) `--strict-mcp-config` 누락, (b) 권한 우회 플래그 추가, (c) 프롬프트에 종목명 포함, (d) 환경 전체 전달 → canary 노출, (e) 시간 상한 무시 → 가짜가 끝날 때까지 안 돌아옴(`wait_for` 상한으로 RED), (f) 그룹 정리 누락 → 남은 프로세스 있음
- 잡지 못하는 것: 실제 `claude`의 동작(AC-018)

### AC-AIR6-012 — 감수 컨텍스트 (REQ-AIR6-012)

- Given: 임시 작업 폴더의 `draft/report-input.json`·`draft/report.html`(알려진 바이트), `screens/index.json`(complete 또는 unavailable), 가짜 감수기(진입 시점에 `review/context.json` 존재 여부와 내용을 읽어 기록)
- When: 후처리 실행
- Then: 가짜 감수기 진입 시점에 파일이 이미 있다. §B 키 집합과 동등. `input.sha256`·`preview.sha256`이 테스트가 두 파일 바이트에서 독립적으로 계산한 값과 같고 `copy_into_review_record`의 `input_sha256`·`preview_sha256`과 같다. `copy_into_review_record.mode == "separate_review_pass"`, `reviewed_at == now`이며 시간대 `+09:00`. 모든 경로 값이 `runs/<job_id>/`로 시작하는 상대 경로이고 `..`·절대 경로 없음. `screens.outcome`이 색인과 같고, 색인이 unavailable이면 `screens.tiles`가 빈 목록
- 명령: `PY -m pytest backend/tests/test_goose_review.py -k air6_012 -q`
- 잡는 구현: (a) 감수기 호출 뒤에 컨텍스트 작성 → 진입 시점 파일 없음, (b) 입력 대신 입력 사본(`company-input.json`) 경로·해시 기록 → 경로 단언 실패, (c) 절대 경로 기록 → 상대 경로 단언 실패, (d) 캡처 실패 시 컨텍스트 미작성 → 파일 없음
- 잡지 못하는 것: 감수 세션이 값을 정확히 옮겨 적는지(감사기 `AUDIT_INPUT_VERSION`·`AUDIT_PREVIEW_VERSION`이 AC-018에서 잡음)

### AC-AIR6-013 — 하네스 지침·매니페스트·권한 불변 (REQ-AIR6-013)

- Given: 변경 후 작업 트리
- When: 아래 명령을 실행한다
- Then:
  1. 지침 존재: `harness-instructions.md`가 (i) 규칙 7에서 1차 세션의 `audit-review.json` 작성·`--final` 실행 금지, (ii) 규칙 9에서 `review/context.json` 읽기, 모든 타일 Read, `separate_review_pass`, `copy_into_review_record` 값 그대로 옮기기, `draft/` 수정 금지, `visual`을 `pass`로 적는 조건(모든 타일 열람 + 타일 이름·모바일 지표를 `evidence`에 기재)과 `revise` 조건, 결정이 `pass`일 때만 `--final`, 일어나지 않은 일을 통과로 적지 않기(i)를 담는다. 테스트는 각 항목의 고정 문구를 파일에서 찾는다(문구 목록은 테스트가 상수로 가진다)
  2. 매니페스트: 원본 재생성 결과 == 커밋된 매니페스트(`PY -m backend.services.goose_harness`를 JSON 비교)
  3. 권한 불변: `claude-settings.json`의 SHA-256 == `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`(research P6 기준선)
  4. 벤더링 스킬 불변: `git diff --stat -- backend/goose_harness_src/skills`가 비어 있다
  5. 서버 재시작 후 설치본이 무결성 검사를 통과한다(라이브 단계, M5)
- 명령: `PY -m pytest backend/tests/test_goose_harness.py -k air6_013 -q`; `git diff --stat -- backend/goose_harness_src/skills backend/goose_harness_src/claude-settings.json`
- 잡는 구현: (a) 규칙 9의 핵심 문구 삭제 → #1 RED, (b) 지침만 고치고 매니페스트 미재생성 → #2 RED(`verify_source`가 해시 불일치 보고), (c) 허용 목록에 명령 추가 → #3 RED, (d) 벤더링 `delivery-audit.md`를 고침 → #4 RED
- 잡지 못하는 것: 지침 문구가 실제로 모델 행동을 바꾸는지(문구 존재 검사는 약한 증거다 — 행동은 AC-018 라이브가 판정)

### AC-AIR6-014 — 감수 중 초안 불변 (REQ-AIR6-014)

- Given: 가짜 감수기가 (1) 아무것도 바꾸지 않음, (2) `draft/report.html`을 바꿈, (3) `draft/report-input.json`을 바꿈
- When: 후처리 실행 후 영수증을 읽는다
- Then: (1) `draft_unchanged == true`, `hashes`의 start/end 쌍이 같음. (2)·(3) `draft_unchanged == false`, 해당 쌍이 다름, `visual_admissible == false`, `reasons`에 `draft_changed`
- 명령: `PY -m pytest backend/tests/test_goose_review.py -k air6_014 -q`
- 잡는 구현: (a) 종료 해시를 다시 계산하지 않고 시작 해시를 복사 → (2)(3)에서 `true`, (b) 한쪽 파일만 비교 → 다른 쪽 변경 경우 RED
- 잡지 못하는 것: `draft/` 밖 파일 변경(범위 밖)

### AC-AIR6-015 — 영수증과 열람 집계 (REQ-AIR6-015)

- Given: 합성 `stream-json`(JSONL) 시나리오. 대상 화면 파일 목록 `{desktop-01, desktop-02, mobile-01}`
  - S1: 세 파일 모두 `Read` 호출 + 성공 `tool_result`
  - S2: `tool_use`만 있고 `tool_result` 없음
  - S3: `tool_result`가 오류 표지
  - S4: 상대 경로(`runs/<id>/screens/mobile-01.png`)와 절대 경로(`<하네스>/runs/<id>/screens/desktop-01.png`) 혼용
  - S5: 다른 작업의 같은 이름 파일(`runs/<other>/screens/mobile-01.png`), `..` 우회 경로, 기본 이름만 같은 `/tmp/mobile-01.png`
  - S6: 서브에이전트(`parent_tool_use_id` 있음)의 읽기
  - S7: 세션이 `review/receipt.json`에 `visual_admissible: true`를 직접 써 둠
- When: 영수증 작성 함수에 스트림과 상태를 넣는다
- Then: §B 키 집합과 동등. `tiles_read`: S1 세 파일 전부, S2 비어 있음, S3 비어 있음, S4 `{mobile-01, desktop-01}`, S5 비어 있음, S6 서브에이전트가 읽은 파일 포함. S7은 서버가 쓴 값으로 덮어써져 `visual_admissible`이 서버 판정을 따른다(스트림에 열람이 없으면 `false`)
- 명령: `PY -m pytest backend/tests/test_goose_review.py -k air6_015 -q`
- 잡는 구현: (a) `tool_use`만 세기 → S2·S3 RED, (b) 기본 이름·부분 문자열로 비교 → S5 RED, (c) 상대 경로 해석 누락 → S4 RED, (d) 서브에이전트 읽기 무시 → S6 RED, (e) 세션이 쓴 영수증을 덮어쓰지 않고 존중 → S7 RED
- 잡지 못하는 것: 실제 `claude`의 이미지 `Read` 스트림 모양(G1 — M1 스파이크에서 실제 스트림 1건을 녹화해 S1 픽스처를 그것으로 교체한다)

### AC-AIR6-016 — 최종본 인정과 규칙 7 불변식 (REQ-AIR6-016)

- Given: `select_report`를 부르는 작업 폴더 픽스처. 공통: `final/report.html` + `final/render-validation.json{delivery_allowed: true}` + `draft/report.html`. 케이스별 영수증·색인·화면 파일:
  - (a) 인정되는 전부 충족 영수증
  - (b) 영수증 없음
  - (c) 타일 하나가 `tiles_read`에 없음
  - (d) 색인 `outcome == "unavailable"`인데 `audit-review.json`은 `visual: pass`
  - (e) 색인 `preview_sha256`이 현재 `draft/report.html` 해시와 다름(낡은 화면)
  - (f) 모바일 `horizontal_overflow == true`
  - (g) 타일 파일을 캡처 뒤에 수정해 SHA-256이 색인과 다름
  - (h) `audit-review.json`의 `mode == "independent_agent"`
  - (i) `audit-review.json`의 `visual.status == "revise"`
  - (j) `reviewed_at`이 색인 `finished_at`보다 이름
  - (k) 영수증은 (a)와 같으나 영수증 작성 뒤 `draft/report.html`이 바뀜
- When: `select_report(job_dir)` 호출(그리고 `archive_job`이 같은 결과를 쓰는지 확인)
- Then: (a) `("final", final_dir)`. (b)~(k) 모두 `("draft", draft_dir)`이고 첫 미충족 조건이 로그에 남는다. `archive_job`의 `delivery_status`도 같다. 추가로 영수증 없는 `final/`만 있는 폴더(draft 없음)는 `None`(기존 규칙: draft가 없으면 보고서 없음)
- 명령: `PY -m pytest backend/tests/test_goose_runner.py backend/tests/test_goose_review.py -k air6_016 -q`
- 잡는 구현(각각 되돌림으로 RED 관측): (a) 영수증 확인 전체 제거 → (b)~(k) 전부 `final`이 되어 RED, (b') 영수증 없음을 허용 → (b) RED, (c') 열람 조건 제거 → (c) RED, (d') `audit-review`의 `visual: pass`만 믿고 색인 `outcome` 무시 → (d) RED, (e') 낡은 화면 허용 → (e) RED, (f') 넘침 무시 → (f) RED, (g') 타일 해시 재검증 누락 → (g) RED, (h') 모드 무시 → (h) RED, (i') `visual` 상태 무시 → (i) RED, (j') 시각 순서 무시 → (j) RED, (k') 영수증 이후 해시 재대조 누락 → (k) RED
- 잡지 못하는 것: 영수증 조건을 모두 만족하면서 판단이 틀린 감수(범위 밖 — 영수증은 열람 사실만 증명)

### AC-AIR6-017 — 테스트 격리와 회귀 (REQ-AIR6-017)

- Given: 변경 후 작업 트리
- When: goose 백엔드 테스트 전체와 새 테스트를 실행하고, 격리 점검을 한다
- Then: (1) `pytest backend/tests -k goose` 실패 0이고 통과 수 ≥ 기준선 267 + 새로 추가한 테스트 수 − 의도적으로 지운 테스트 수(M4가 갱신한 기존 테스트 목록을 `progress.md §E.2`에 적는다). (2) 네트워크 가드 기록 0건(가드가 종료 시 단언). (3) 새 테스트 파일에서 실제 `claude`·브라우저 실행 파일을 이름으로 호출하는 곳이 없다: `git grep -n "chrome-headless-shell\|Google Chrome\|ms-playwright" -- backend/tests`는 테스트가 만든 가짜 경로 상수 외에 없다. (4) 가드 자체 검사: 새 후처리 경로가 주입 없이 실제 DevTools 연결(`127.0.0.1` 소켓)을 시도하게 임시로 바꾸면 테스트가 `network attempt in goose test`로 실패한다(되돌림 관측)
- 명령: `PY -m pytest backend/tests -k goose -q -p no:cacheprovider`
- 잡는 구현: 가짜 드라이버 주입 대신 실제 CDP 연결을 여는 테스트 → (2)·(4)에서 RED
- 잡지 못하는 것: 이 호스트에서만 나타나는 브라우저 설치 의존 동작(AC-018)

### AC-AIR6-018 — 라이브 관측 게이트 (REQ-AIR6-018)

라이브 관측 게이트다. 통과해야 SPEC을 닫는다(§F). 감수 세션(모델)의 판단에 달려 있으므로 같은 KST 날짜에 020150으로 최대 2회 실행할 수 있다. 1~5는 **실행한 모든 회차**에서 만족해야 한다.

- Given: M5 반영 후 서버 재시작과 AC-013 #5 통과, 기준선 research.md P2·P3(같은 종목 이전 실행에서 대상 8종 전부 발생)
- When: 앱에서 020150으로 goose 작업을 실행하고 끝까지 기다린다. 452190은 선택 관측(게이트 아님)
- Then (작업과 같은 KST 날짜에 확인, `R`은 `~/.goose-harness/runs/<job_id>`):
  1. 작업 `status: done`
  2. `R/screens/index.json`의 `outcome == "complete"`이고 두 뷰포트 `ok`, 타일 파일이 모두 존재하며 SHA-256 일치
  3. `R/review/receipt.json`: `screens.tiles_read`가 `screens.tiles_expected`를 모두 포함(감수 세션이 모든 타일을 실제로 열었다), `process.exit_code == 0`, `draft_unchanged == true`
  4. `python3 -I ~/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input R/draft/report-input.json --preview R/draft/report.html --review R/audit-review.json --output "$S/audit.json"`의 결함 코드 집합과 `{AUDIT_INPUT_VERSION, AUDIT_PREVIEW_VERSION, AUDIT_TIME, AUDIT_MODE, REVIEW_SOURCE_ACCURACY, REVIEW_CALCULATIONS, REVIEW_COVERAGE, REVIEW_OPINION}`의 교집합이 공집합
  5. 규칙 7 정합: (i) `audit-review.json`의 `checks.visual.status == "pass"`이면 `receipt.visual_admissible == true`이고 `reasons`가 비어 있다. (ii) `receipt.visual_admissible == false`이면 전달 상태(`job.json`/작업 완료 이벤트의 `delivery_status`)는 `draft`다. (iii) 전달 상태가 `final`이면 `R/final/delivery-audit.json`의 `decision == "pass"`다. (iv) `visual.evidence`가 연 타일 파일 이름을 하나 이상 적는다
- 비게이팅(기록만): `REVIEW_VISUAL`이 남는지(감수가 정당하게 `revise`를 낼 수 있다), `LATEST_SEARCH_NAVER` 등 이 SPEC 범위 밖 결함, 최종본 도달 여부, 소요 시간·토큰(research G5), 진행 패널 화면 배치
- 실패 시 기록: 2 실패 → 캡처 결함(브라우저·타일), 2 통과·3 실패 → 감수 세션이 이미지를 안 열었거나 영수증 수집 결함(스트림 모양 확인), 3 통과·4 실패 → 지침 미준수 또는 컨텍스트 결함(남은 코드와 해당 필드를 그대로 기록), 5 위반 → 규칙 7 불변식 결함(최우선). 어느 경우든 SPEC은 닫지 않고 manager-spec 재위임으로 고친 뒤 다시 잰다
- 대조(되돌림 관측): 같은 회차의 `R/draft`에 대해 `--review`를 주지 않은 감사 출력은 P2-A와 같이 8개 코드를 모두 낸다 — 4의 판정이 이 입력에서 공집합이 될 수 있음을 보이는 기준선으로 같이 기록한다
- 잡는 구현: 캡처는 되지만 감수 세션이 지침을 따르지 않아 `audit-review.json`이 없음 → 4 실패(`AUDIT_*` 8개 발생), 감수 세션이 해시를 틀리게 옮김 → `AUDIT_INPUT_VERSION`/`AUDIT_PREVIEW_VERSION`으로 4 실패, 타일을 열지 않고 `visual: pass`를 적음 → 영수증이 인정하지 않아 전달은 안전하게 `draft`로 내려가지만(5(ii) 만족) `pass`와 `visual_admissible: false`가 어긋나 5(i)가 위반으로 기록된다 — 지침 미준수로 분류해 지침을 고친 뒤 다시 잰다
- 잡지 못하는 것: 감수 세션이 열었다고 한 자료를 실제로 끝까지 읽었는지, 사실 대조의 충실도(스트림 기록으로 열람 사실만 확인, G6)

## §D 경계 사례

| 사례 | 기대 동작 | 담당 AC |
|---|---|---|
| 브라우저가 호스트에 없음 | 색인 `unavailable`, 감수는 실행되고 `visual: revise`, 전달 `draft` | AC-005·010 |
| 페이지가 매우 길어 타일 상한 초과 | 해당 뷰포트 `too_tall`, 타일 없음, 최종본 불가 | AC-008·016 |
| 모바일 문서 폭 넘침 | `horizontal_overflow`가 참이면 최종본 불가 | AC-007·016 |
| 감수 세션이 초안을 몰래 수정 | 영수증 `draft_unchanged: false`, 최종본 불가 | AC-014·016 |
| 감수 세션이 영수증을 위조 | 서버가 종료 후 덮어씀 | AC-015 |
| 감수 세션이 타일을 열지 않고 `pass` 선언 | `tile_not_read`로 최종본 불가 | AC-015·016 |
| 끄기 스위치 | 후처리 없음, 영수증 `disabled`, 전달 `draft` | AC-004 |
| 서버 종료 중 후처리 | `cancelled`, 프로세스 그룹 정리 | AC-002 |
| 후처리 중 무결성 재검사 실패 | 캡처·감수 없음, 영수증 `integrity_failed` | AC-001 |
| 외부 웹 글꼴 차단으로 글꼴 대체 | 화면은 대체 글꼴, 감수 지침이 증거에 적도록 함 | AC-013(문구), AC-018(관측) |

## §E 품질 게이트

- 새 모듈(`goose_screenshot.py`, `goose_review.py`) 줄 커버리지 85% 이상. 측정은 `coverage run --source=backend -m pytest <파일>` → `coverage report`(lessons #9의 커버리지 측정 함정)
- `ruff check` 새 경고 0(기준선 대비)
- 대조 항목은 되돌림 RED 관측 후에만 GREEN 기록(§A). 영수증 판정(AC-016)은 조건 11개 각각의 되돌림을 개별로 관측한다
- @MX: 캡처 모듈의 브라우저 프로세스 진입점과 `select_report` 영수증 확인에 `@MX:ANCHOR`·`@MX:WARN`(+REASON), 주석 언어는 `code_comments: ko`

## §F 완료 정의

- AC-AIR6-001~017 통과(명령·출력·기준선을 `progress.md §E.2`에 원문으로)
- AC-AIR6-018 통과(라이브 관측 게이트 — 실패 기록만으로는 닫지 않는다)
- M1 GO/NO-GO 결과(특히 G1)와 M1 관측값(research §4 G2·G3·G4·G8·G9)이 `progress.md §E.2`에 기록됨
- 매니페스트 재생성·서버 재시작·무결성 확인 완료(AC-013 #2·#5), `claude-settings.json`·`skills/**` 무변경(#3·#4)
- README·`.env.example`에 후처리 단계와 환경 변수 `AI_REPORT_GOOSE_REVIEW`·`AI_REPORT_GOOSE_BROWSER`·`AI_REPORT_GOOSE_REVIEW_TIMEOUT`, 브라우저 요건, "이 SPEC 이후에도 다른 감사 결함으로 `draft`일 수 있음"이 기록됨
