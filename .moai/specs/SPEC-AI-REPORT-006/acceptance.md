# SPEC-AI-REPORT-006 — 인수 기준

버전 0.3.3 · 요구사항은 `spec.md §4`(REQ-AIR6-001~020), 인수 기준 AC-AIR6-001~022. 각 AC는 Given-When-Then, 실행 명령, 기댓값, 그리고 **이 AC가 잡아내는 틀린 구현(대조)** 과 **잡지 못하는 것** 을 적는다. 대조 항목은 run 단계에서 실제로 되돌림을 적용해 RED를 관측해야 GREEN으로 기록할 수 있다(lessons #9). 관측하지 못한 대조는 `progress.md §E.2`에 Gap으로 남긴다.

## §A 공통 실행 조건

- Python 명령은 서버용 가상환경 `/Users/byunjungwon/Dev/my_chart/.venv`(코드 폴더와 다른 경로)의 `python`으로 실행한다. 아래 `PY`는 그 환경의 `python`이다.
- 테스트 함수 이름에 AC 번호 꼬리표(`air6_001` 등)를 넣어 `-k`로 고를 수 있게 한다. 테스트 파일 이름은 `test_goose_` 접두어를 지켜 공용 네트워크 가드(005)가 자동 적용되게 한다.
- 프론트 테스트는 `npm --prefix frontend run test -- <필터>`로 돌린다(`--root`를 함께 주지 않는다 — 005 기록).
- `$S`는 세션 증거 폴더 `.moai/state/verify/<session>/`다.
- 모든 테스트는 실제 브라우저·실제 `claude`·실제 네트워크를 쓰지 않는다(REQ-AIR6-017). 가짜 드라이버·가짜 실행 파일은 `design.md §10`.
- 픽스처는 run 단계 M1이 research.md §2 P13·P14 방식으로 얻은 값(라이브 초안 `a5becbb9…`의 높이 데스크톱 20160px·모바일 30683px(글꼴 로드)/30803px(네트워크 전면 차단, 캡처 모듈이 보는 값), 문서 폭 일치; 기존 초안 4개의 분포는 research P26)과 합성 값이다. 기댓값 리터럴이 M1 관측과 다르면 코드 작성 전에 `progress.md`에 기록하고 manager-spec 재위임으로 이 문서를 고친다.
- 수치 한도(60초, 30타일, 1568px, 8 MiB, 900초)는 초기값이며 M1·M6이 관측으로 확정한다. 바뀌면 테스트는 spec.md의 값이 아니라 모듈 상수를 임포트해 단언하고, spec.md는 manager-spec 재위임으로 고친다.

## §B 고정 키 집합 (AC-006·007·012·015가 집합 동등으로 검사)

- `screens/index.json` 최상위: `schema_version`, `source`, `preview_sha256`, `started_at`, `finished_at`, `outcome`, `browser`, `viewports`. `browser`: `name`, `version`, `path_kind`. `viewports[]`: `name`, `width`, `status`, `error`, `metrics`, `tiles`. `metrics`: `scroll_width`, `client_width`, `scroll_height`, `horizontal_overflow`. `tiles[]`: `file`, `y`, `width`, `height`, `bytes`, `sha256`
- `review/context.json` 최상위: `schema_version`, `job_id`, `code`, `now`, `input`, `preview`, `screens`, `audit_review_path`, `audit_output_path`, `final_dir`, `copy_into_review_record`. `screens`: `index_path`, `outcome`, `tiles`, `render_note`. `copy_into_review_record`: `input_sha256`, `preview_sha256`, `reviewed_at`, `mode`
- `review/receipt.json` 최상위: `schema_version`, `outcome`, `started_at`, `finished_at`, `process`, `hashes`, `draft_unchanged`, `screens`, `judged_writes`, `audit_review`, `visual_admissible`, `reasons`. `hashes`: `input_start`, `input_end`, `preview_start`, `preview_end`. `screens`: `outcome`, `index_sha256`, `tiles_expected`, `tiles_read`, `snapshot_start`, `snapshot_end`. `snapshot_*`: `index_sha256`, `files`
- `browser.path_kind` ∈ {env, playwright_cache, none}
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

- Given: 호출 횟수를 세는 가짜 캡처기·감수기, 가짜 실행기(`draft/report.html`과 `final/report.html` + `delivery_allowed: true`를 둘 다 만든 것으로 가정, 실제 실행기가 영수증 없이 계산하는 값 `draft`를 돌려줌), `AI_REPORT_GOOSE_REVIEW=0`
- When: 작업 실행
- Then: 캡처기·감수기 호출 0, `screenshot`·`review`·`render_final` 이벤트 0, `review/receipt.json`의 `outcome == "disabled"`, 실행기 호출 1, 전달 상태 `draft`(영수증이 인정하지 않으므로 `final/`이 있어도 `draft`). 같은 테스트에서 변수 미설정 시 캡처기 1·감수기 1 호출(대조)
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_004 -q`
- 잡는 구현: (a) 스위치 무시 → 호출 1, (b) 스위치를 감수기 안에서만 확인 → 캡처기 호출 1, (c) 끈 경우 영수증을 쓰지 않음 → 파일 없음, (d) 끈 경우 실행기까지 건너뜀 → 호출 0
- 잡지 못하는 것: 서버 재시작 없이 환경 변수를 바꾼 경우(프로세스 환경은 시작 시 고정 — 매 작업마다 읽으므로 테스트에서는 `monkeypatch`로 충분)

### AC-AIR6-005 — 후처리 실패해도 초안으로 끝남 (REQ-AIR6-005)

- Given: 실패 유형 행렬. 캡처기: 예외 발생 / `unavailable` 색인 반환. 감수기: 예외 / 비정상 종료(`review_failed`) / 시간 초과(`timeout`) / 종료 0인데 `audit-review.json` 없음(`review_failed`)
- When: 각 경우로 작업 실행
- Then: 모든 경우 작업 `done`, 전달 상태 `draft`, `error` 이벤트 0. 캡처만 실패한 경우에도 감수기는 호출되고 `review/context.json`의 `screens.outcome`이 `unavailable`/`failed`. 감수기 실패 경우 영수증 `outcome`이 각각 `review_failed`(예외·비정상 종료)/`timeout`/`review_failed`(종료 0이지만 `audit-review.json` 없음 — 이때 `reasons`에 `no_audit_review`)
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_005 -q`
- 잡는 구현: (a) 캡처 실패가 작업을 `error`로 만듦, (b) 캡처 실패 시 감수 건너뜀 → 감수기 호출 0, (c) 감수기 예외를 삼키지 않고 작업 실패 처리, (d) 시간 초과를 `done`/`final`로 처리 → 영수증 outcome 불일치, (e) 종료 0이지만 `audit-review.json` 없는 경우를 `reviewed`로 기록 → outcome 단언 실패
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

- Given: 가짜 드라이버: (1) 모바일 페이지 높이 100000px(상한 `TILE_CAP`=30타일 초과; 테스트는 상수를 임포트해 `(TILE_CAP+1)*1568`px로 경계도 시험), (2) 호출 하나가 예산을 넘겨 지연(테스트가 예산 상수를 작게 패치), (3) 9 MiB 크기 타일 반환, (4) 정상. 가짜 브라우저 실행 파일로 프로세스 그룹 확인(`AI_REPORT_GOOSE_BROWSER`)
- When: 캡처 실행(정상·실패·취소 각 경로)
- Then: (1) 모바일 `status == "too_tall"`, 모바일 타일 0개(일부만 저장하지 않음), 데스크톱은 `ok`, `outcome == "partial"`. (2) 예산 초과 뷰포트 `error`, 남은 뷰포트 `skipped`, 가짜 브라우저 그룹 종료. (3) 해당 뷰포트 `error`. 모든 경우(정상 포함) 종료 뒤 브라우저 프로세스 그룹이 없고(`killpg(…,0)` → `ProcessLookupError`) 임시 프로필 폴더가 존재하지 않는다
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_008 -q`
- 잡는 구현: (a) 타일 상한 없음 → (1)에서 타일 수 > `TILE_CAP`, (a') 상한 경계 오류 → 정확히 `TILE_CAP*1568`px 페이지는 `ok`(30타일), `TILE_CAP*1568+1`px는 `too_tall`이어야 하는데 어긋남, (b) 상한 초과 때 앞 `TILE_CAP`개만 저장 → 타일 0개 단언 실패, (c) 예산 미적용 → (2)가 끝나지 않음(`wait_for` 상한으로 RED), (d) 크기 상한 없음 → (3)에서 `ok`, (e) 임시 폴더를 성공 경로에서만 삭제 → 실패·취소 경로에서 폴더 잔존
- 잡지 못하는 것: 실제 브라우저의 메모리 사용

### AC-AIR6-009 — 격리 (REQ-AIR6-009)

- Given: 가짜 브라우저 실행 파일(받은 argv를 파일에 기록하고 잠), 가짜 드라이버, 보고서 HTML 안에 `--evil-flag`·`$(touch x)`·`</script>`가 든 제목 텍스트(보고서 내용에서 온 문자열)와 종목명 `A; rm -rf /`
- When: 캡처 실행
- Then: 기록된 argv의 모든 원소가 (고정 문자열 허용 집합) ∪ (`--remote-debugging-port=<정수>`) ∪ (`--user-data-dir=<임시 폴더 경로>`) ∪ (`about:blank` 또는 검증된 `file://` URL)에 속하고 보고서 문자열·종목명이 어느 원소에도 부분 문자열로 없다. 디버깅 포트는 루프백만(`--remote-debugging-address`가 있으면 `127.0.0.1`). 가짜 드라이버 호출 기록에 스크립트 비활성과 네트워크 차단 적용이 있고, 차단 패턴이 정확히 전부 차단(`["*"]`)이며 허용 호스트·예외 목록이 비어 있다(초안 `<link>`에서 관측한 글꼴 호스트 `cdn.jsdelivr.net`·`fonts.googleapis.com` 문자열이 드라이버 호출 인자 어디에도 없다)
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_009 -q`
- 잡는 구현: (a) 인자에 보고서·종목명 문자열 포함 → 부분 문자열 단언 실패, (b) 스크립트 비활성 호출 누락, (c) 네트워크 차단 누락, (d) 디버깅 주소 `0.0.0.0` → 루프백 단언 실패, (e) 글꼴 호스트 예외 허용(차단 패턴에서 호스트 제외 또는 허용 목록 추가) → 전부 차단 단언·호스트 문자열 부재 단언 실패(운영자 결정 2026-10-21)
- 잡지 못하는 것: 실제 브라우저가 외부로 요청하지 않는지(G3·G8 — M1 관측, 가능하면 로컬 수신 소켓으로 요청 0건 확인)

### AC-AIR6-010 — 브라우저 탐색 (REQ-AIR6-010)

- Given: 임시 폴더에 실행 권한 있는 가짜 브라우저 파일 A, 실행 권한 없는 파일 B, 임시 Playwright 캐시 루트(테스트가 모듈의 캐시 루트 목록 상수를 이 폴더로 패치)에 `chromium_headless_shell-9/…/chrome-headless-shell`과 `chromium_headless_shell-12/…/chrome-headless-shell`(둘 다 실행 가능, 서로 다른 내용), 그리고 `PATH`에 고정 이름 `chromium`·`google-chrome`의 가짜 실행 파일 D, 임시 `Google Chrome.app` 모양 폴더 E
- When: (1) `AI_REPORT_GOOSE_BROWSER=A`, (2) `=B`, (3) 변수 없음 + 캐시 루트에 위 두 빌드, (4) 변수 없음 + 캐시 루트 비어 있음(`PATH`의 D·E는 그대로)
- Then: (1) A로 실행, `browser.path_kind == "env"`. (2) 실행 시도 0, `outcome == "unavailable"`, 캐시의 빌드로 폴백하지 않음. (3) 빌드 번호 12의 실행 파일로 실행(9 아님 — 문자열 정렬이 아닌 숫자 비교), `path_kind == "playwright_cache"`. (4) 실행 시도 0(D·E를 쓰지 않음), `outcome == "unavailable"`, 사유 기록, 색인의 어느 필드에도 브라우저 절대 경로 없음
- 명령: `PY -m pytest backend/tests/test_goose_screenshot.py -k air6_010 -q`
- 잡는 구현: (a) 환경 변수 무시 → (1)에서 캐시 빌드 사용, (b) 잘못된 변수일 때 조용히 폴백 → (2)에서 캐시 빌드 실행, (c) 후보 없음일 때 예외 → `unavailable` 아님, (d) 가장 높은 빌드를 고르지 않음(첫 항목·문자열 정렬: `12` < `9`) → (3)에서 9 실행, (e) `PATH`·`Google Chrome.app`을 탐색 → (4)에서 D 또는 E 실행(운영자 결정 2026-10-21)
- 잡지 못하는 것: 이 호스트의 실제 설치 위치(M1이 관측, 문서화), Linux 캐시 구조(G12)

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
- Then: 가짜 감수기 진입 시점에 파일이 이미 있다. §B 키 집합과 동등. `input.sha256`·`preview.sha256`이 테스트가 두 파일 바이트에서 독립적으로 계산한 값과 같고 `copy_into_review_record`의 `input_sha256`·`preview_sha256`과 같다. `copy_into_review_record.mode == "separate_review_pass"`, `reviewed_at == now`이며 시간대 `+09:00`. `screens.render_note`가 비어 있지 않은 고정 문장이고 "외부 네트워크"·"웹 글꼴"·"조금 다르"를 모두 포함한다(캡처 성공·실패 모두). 모든 경로 값이 `runs/<job_id>/`로 시작하는 상대 경로이고 `..`·절대 경로 없음. `screens.outcome`이 색인과 같고, 색인이 unavailable이면 `screens.tiles`가 빈 목록
- 명령: `PY -m pytest backend/tests/test_goose_review.py -k air6_012 -q`
- 잡는 구현: (a) 감수기 호출 뒤에 컨텍스트 작성 → 진입 시점 파일 없음, (b) 입력 대신 입력 사본(`company-input.json`) 경로·해시 기록 → 경로 단언 실패, (c) 절대 경로 기록 → 상대 경로 단언 실패, (d) 캡처 실패 시 컨텍스트 미작성 → 파일 없음, (e) `render_note` 누락 → 키 집합 동등 실패
- 잡지 못하는 것: 감수 세션이 값을 정확히 옮겨 적는지(감사기 `AUDIT_INPUT_VERSION`·`AUDIT_PREVIEW_VERSION`이 AC-018에서 잡음)

### AC-AIR6-013 — 하네스 지침·매니페스트·권한 불변 (REQ-AIR6-013)

- Given: 변경 후 작업 트리
- When: 아래 명령을 실행한다
- Then:
  1. 지침 존재: `harness-instructions.md`가 (i) 규칙 7에서 1차 세션의 `audit-review.json` 작성·`--final` 실행 금지, (ii) 규칙 10(하위 `10-1`~`10-10`)에서 `review/context.json` 읽기, 모든 타일 Read, `separate_review_pass`, `copy_into_review_record` 값 그대로 옮기기, `draft/` 수정 금지, `visual`을 `pass`로 적는 조건(모든 타일 열람 + 타일 이름·모바일 지표를 `evidence`에 기재)과 `revise` 조건, 결정이 `pass`일 때만 `--final`, 일어나지 않은 일을 통과로 적지 않기(10-10), `screens/` 수정 금지, 결함을 찾은 검사는 `revise` + 구체적 증거 + `open` issue(정직한 `revise`는 허용), `visual` 증거를 리터럴 표지 `[렌더 차이]`로 시작해 "외부 네트워크와 웹 글꼴을 막고 그려 실제 화면과 조금 다르다"를 적기를 담는다. 테스트는 각 항목의 고정 문구를 파일에서 찾는다(문구 목록은 테스트가 상수로 가진다)
  2. 매니페스트: 원본 재생성 결과 == 커밋된 매니페스트(`PY -m backend.services.goose_harness`를 JSON 비교)
  3. 권한 불변: `claude-settings.json`의 SHA-256 == `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`(research P6 기준선)
  4. 벤더링 스킬 불변: `git diff --stat -- backend/goose_harness_src/skills`가 비어 있다
  5. 서버 재시작 후 설치본이 무결성 검사를 통과한다(라이브 단계, M5)
- 명령: `PY -m pytest backend/tests/test_goose_harness.py -k air6_013 -q`; `git diff --stat -- backend/goose_harness_src/skills backend/goose_harness_src/claude-settings.json`
- 잡는 구현: (a) 규칙 10의 핵심 문구(`[렌더 차이]` 표지 문구 포함) 삭제 → #1 RED, (b) 지침만 고치고 매니페스트 미재생성 → #2 RED(`verify_source`가 해시 불일치 보고), (c) 허용 목록에 명령 추가 → #3 RED, (d) 벤더링 `delivery-audit.md`를 고침 → #4 RED
- 잡지 못하는 것: 지침 문구가 실제로 모델 행동을 바꾸는지(문구 존재 검사는 약한 증거다 — 행동은 AC-018 라이브가 판정)

### AC-AIR6-014 — 감수 중 판단 대상 불변과 변조 탐지 (REQ-AIR6-014)

판단 대상은 `draft/report.html`, `draft/report-input.json`, `screens/index.json`, 모든 타일 파일, `screens/` 아래 모든 파일의 상대 경로 집합(하위 폴더 포함 재귀)이다. 감수 세션은 `Write(./runs/**)` 권한으로 이들을 모두 고칠 수 있다(research P6) — 이 AC는 그 구멍을 닫았음을 보인다(plan-audit D2).

- Given: 가짜 감수기(세션 중에 디스크를 바꾸고, 합성 스트림에 `Write`/`Edit` 호출을 남길 수 있음)가 시나리오별로
  - (1) 아무것도 바꾸지 않음
  - (2) `draft/report.html`을 바꿈
  - (3) `draft/report-input.json`을 바꿈
  - (4) `screens/index.json`을 바꿔 `outcome: complete`·`horizontal_overflow: false`·위조 타일 해시로 고쳐 쓰고 위조 타일 파일도 씀(스트림에는 위조 타일 `Read`가 성공으로 있음)
  - (5) 타일 PNG 하나만 다른 바이트로 덮어씀(색인은 그대로)
  - (6) `screens/`에 새 파일 `mobile-99.png`를 추가
  - (6b) `screens/sub/a.png`처럼 하위 폴더에 새 파일을 추가(최상위 `screens/`의 파일 이름 목록은 그대로)
  - (7) 타일 PNG를 바꿨다가 종료 전에 원래 바이트로 복원(디스크 해시는 시작·종료 동일), 스트림에는 그 타일에 대한 `Edit` 호출이 있음
  - (8) `Write` 시도가 `draft/` 안 파일을 향함(도구 결과는 오류, 디스크 불변)
  - (9) `review/` 아래 파일만 씀(`audit-review.json`, `delivery-audit.json` 등 정상 쓰기)
  - (10) `Write` 호출의 대상이 대소문자만 다른 경로(`runs/<id>/Screens/mobile-01.png`)를 향함(디스크 불변 — 대소문자를 구분하지 않는 파일시스템을 가정한 방어, research P32)
- When: 후처리 실행 후 영수증을 읽고 `select_report`를 부른다(감수 세션이 `final/`과 `delivery_allowed: true`를 만들어 둔 것으로 가정)
- Then: (1) `draft_unchanged == true`, start/end 쌍이 같고 `screens.snapshot_start == snapshot_end`, `judged_writes == []`. (2)·(3) `draft_unchanged == false`, 해당 쌍이 다름, `visual_admissible == false`, `reasons`에 `draft_changed`. (4) `snapshot_start != snapshot_end`, `reasons`에 `screens_changed`, `select_report == ("draft", …)`. (5)·(6)·(6b) 같은 결과(`screens_changed`). (7) 스냅샷은 같지만 `judged_writes`에 그 타일 경로가 있고 `reasons`에 `judged_input_write_attempt`, `select_report == ("draft", …)`. (8) `judged_writes`에 `draft/` 경로, 같은 사유. (9) `judged_writes == []`이고 위 사유가 없다(정상 쓰기를 오탐하지 않음). (10) `judged_writes`에 그 경로가 있고(비교는 대소문자를 무시), 사유 `judged_input_write_attempt`, `select_report == ("draft", …)`
- **사전 심기 케이스 (REQ-AIR6-014 첫 절, iter3 N13)** — 1차 goose 세션이 `Write(./runs/**)`로 감수 세션 시작 전에 파일을 심었고, 감수 세션이 그것을 덮어쓰지 않고 종료 코드 0으로 끝나는 경우다. 가짜 감수기는 진입 시점에 두 경로(`audit-review.json`, `final/`)의 존재를 기록한다. 영수증 작성기의 `reasons`(조건 1~17)와 `select_report`를 읽는다
  - (11) 심은 것: `audit-review.json`(`visual: pass`, 증거에 `[렌더 차이]`, 색인·초안 해시를 복사, `mode: separate_review_pass`, `reviewed_at`은 미래). 가짜 감수기: 모든 타일 `Read`를 스트림에 내고, 정상 `final/`(`delivery_allowed: true`)을 만들지만 `audit-review.json`은 쓰지 않은 채 종료 코드 0. 기대: 진입 시점에 `audit-review.json` 없음, 영수증 `outcome == "review_failed"`, 작성기 `reasons == [review_not_completed, no_audit_review]`, `select_report == ("draft", …)`
  - (12) 심은 것: `final/report.html` + `final/render-validation.json{delivery_allowed: true}`(`audit-review.json`은 없음). 가짜 감수기: 모든 타일을 읽고 context 값을 옮긴 정직한 `audit-review.json`(`visual: pass`, `[렌더 차이]` 포함)을 쓰되 `final/`은 만들지 않은 채 종료 코드 0. 기대: 진입 시점에 `final/` 없음, `outcome == "reviewed"`, 작성기 `reasons == []`, `select_report == ("draft", …)`(조건 0 `final_not_allowed`)
  - (13) 삭제 실패: (11)의 심은 `audit-review.json`과 (12)의 심은 `final/`이 모두 있고, 서비스의 삭제 단계만 실패하도록 테스트가 삭제 함수를 패치한다. 기대: 가짜 감수기 호출 0, 작업 `done`, 영수증 `outcome == "review_failed"`, 작성기 `reasons == [review_not_completed, tile_not_read]`, `select_report == ("draft", …)`, 완료 이벤트 전달 상태 `draft`. 이 목록은 서버가 삭제 실패 시점에 시작 값을 먼저 측정해 시작·종료 양쪽에 같은 값으로 쓴다는 규칙(REQ-014, iter3 델타 N17)을 전제로 한다 — 손으로 유도한 결과: 3 `review_not_completed` 미충족(outcome `review_failed`), 4·5·7·8·12 충족, 6·9는 지금 값 == 시작 값 == 종료 값이라 충족, 10은 심은 기록이 해시를 복사해 충족, 11 `tile_not_read` 미충족(감수기 미호출이라 읽은 타일 없음), 13~17은 심은 기록이 읽히고 형식이 맞아 충족. 시작 값을 비워 두면 6·9가 더해져 `[review_not_completed, screens_changed, draft_changed, tile_not_read]`가 된다(되돌림 (m))
- 명령: `PY -m pytest backend/tests/test_goose_review.py backend/tests/test_goose_job_service.py -k air6_014 -q`
- 잡는 구현(되돌림 RED): (a) 종료 해시를 다시 계산하지 않고 시작 해시를 복사 → (2)(3)에서 `true`, (b) 한쪽 파일만 비교 → 다른 쪽 변경 경우 RED, (c) **screens 스냅샷을 아예 만들지 않음(또는 세션 후에야 측정)** → (4)(5)(6)에서 `screens_changed`가 안 나고 `final`이 선택됨, (d) 파일 집합을 빼고 해시만 비교 → (6) RED, (e) `Write`/`Edit` 호출 기록 누락 → (7)(8) RED, (f) 결과가 오류인 시도는 무시 → (8) RED, (g) `review/` 쓰기까지 위반으로 셈 → (9) RED, (h) 대소문자를 구분하는 경로 비교 → (10) RED, (i) 감수 세션 시작 전 `audit-review.json` 삭제를 뺀 변형 → (11)에서 심은 파일이 남아 `outcome`이 `reviewed`, 작성기 `reasons == []`, `select_report`가 `final`이 되어 RED, (j) `final/` 삭제를 뺀 변형 → (12)에서 `select_report`가 `final`이 되어 RED, (k) 삭제 실패를 무시하고 세션을 시작하는 변형 → (13)에서 감수기 호출 1이 되어 RED, (l) 최상위 파일만 열거하는 비재귀 스냅샷 → (6b)에서 `screens_changed`가 안 나오고 `final`이 선택되어 RED, (m) 삭제 실패 때 시작 값을 측정하지 않고 비워 둔 채 `review_failed`로 가는 변형 → (13)에서 작성기 `reasons`에 `screens_changed`·`draft_changed`가 더해져 RED(결과 뒤집힘이 아니라 사유 목록 변화 — 전달 상태는 어느 쪽이든 `draft`)
- 잡지 못하는 것: 도구 호출이 아닌 경로(허용된 두 스크립트의 부작용)로 바뀌었다 복원되는 변경(Gap G11), `draft/`·`screens/` 밖 파일 변경(범위 밖). 대소문자만 다른 경로로 타일을 `Read`한 경우는 읽음으로 세지 않는다(안전 방향 — 최악의 결과는 `tile_not_read`로 `draft`). 사전 심기 삭제는 `audit-review.json`과 `final/`만 다룬다 — 판정이 읽지 않는 `review/` 아래 다른 파일(예: `review/delivery-audit.json`)을 심어도 영향이 없어 지우지 않는다. 삭제 이후 감수 세션 시작 사이에 파일을 쓰는 주체는 이 SPEC의 작업 모델에 없다(1차 세션의 프로세스 그룹은 `run_goose`가 돌아오기 전에 항상 정리됨 — research P34, 그룹 밖으로 빠져나간 프로세스는 미관측)

### AC-AIR6-015 — 영수증과 열람 집계 (REQ-AIR6-015)

- Given: 합성 `stream-json`(JSONL) 시나리오. 대상 화면 파일 목록 `{desktop-01, desktop-02, mobile-01}`
  - S1: 세 파일 모두 `Read` 호출 + 성공 `tool_result`
  - S2: `tool_use`만 있고 `tool_result` 없음
  - S3: `tool_result`가 오류 표지
  - S4: 상대 경로(`runs/<id>/screens/mobile-01.png`)와 절대 경로(`<하네스>/runs/<id>/screens/desktop-01.png`) 혼용
  - S5: 다른 작업의 같은 이름 파일(`runs/<other>/screens/mobile-01.png`), `..` 우회 경로, 기본 이름만 같은 `/tmp/mobile-01.png`
  - S6: 서브에이전트(`parent_tool_use_id` 있음)의 읽기
  - S7: 세션이 `review/receipt.json`에 `visual_admissible: true`를 직접 써 둠
  - S8: `tool_result.is_error`가 `false`인 `Read`(성공), 키가 없는 `Read`(성공), `true`인 `Read`(오류)가 한 스트림에 섞임(기존 스트림 픽스처의 실제 비율: 없음 33·`false` 4·`true` 3, research P10)
  - S9: 영수증 쓰기 실패. (a) S7처럼 세션이 쓴 `review/receipt.json`이 있는 상태에서 서버의 교체 단계만 실패(제거는 성공; 테스트가 교체 함수를 실패하도록 패치), (b) 제거와 교체가 모두 실패해 세션이 쓴 파일이 남음
- When: 영수증 작성 함수에 스트림과 상태를 넣는다
- Then: §B 키 집합과 동등. `tiles_read`: S1 세 파일 전부, S2 비어 있음, S3 비어 있음, S4 `{mobile-01, desktop-01}`, S5 비어 있음, S6 서브에이전트가 읽은 파일 포함. S7은 서버가 쓴 값으로 덮어써져 `visual_admissible`이 서버 판정을 따른다(스트림에 열람이 없으면 `false`). S8: `false`·키 없음 `Read`는 읽음, `true`는 읽음이 아님. S9(a): 쓰기가 실패해도 세션이 쓴 영수증이 남아 있지 않다(서버가 먼저 제거), `select_report == ("draft", …)`이고 첫 사유 `no_receipt`, 작업 `done`, 로그에 `receipt_write_failed` 1건, 완료 이벤트 전달 상태 `draft`. S9(b): 작업 `done`, 로그 `receipt_write_failed`, 완료 이벤트 전달 상태 `draft`(`final` 아님). S9(b)에서 보관 단계의 `select_report`가 디스크의 낡은 영수증을 다시 읽는 경로는 막지 못한다(Gap G14 — 이 시나리오는 서비스가 확정한 이벤트 값만 단언한다)
- 명령: `PY -m pytest backend/tests/test_goose_review.py -k air6_015 -q`
- 잡는 구현: (a) `tool_use`만 세기 → S2·S3 RED, (a') `is_error`가 "키 있음"이면 오류로 취급(`false`도 오류) → S8 RED, (b) 기본 이름·부분 문자열로 비교 → S5 RED, (c) 상대 경로 해석 누락 → S4 RED, (d) 서브에이전트 읽기 무시 → S6 RED, (e) 세션이 쓴 영수증을 덮어쓰지 않고 존중 → S7 RED, (f) 쓰기 실패 때 세션이 쓴 영수증을 제거하지 않고 둠(제거 없이 교체만 시도) → S9(a)에서 파일 잔존으로 RED, (g) S9(b)에서 이벤트가 영수증 판정을 건너뛰고 `final` → RED
- 잡지 못하는 것: 실제 `claude`의 이미지 `Read` 스트림 모양(G1 — M1 스파이크에서 실제 스트림 1건을 녹화해 S1 픽스처를 그것으로 교체한다), S9(b)의 보관 단계 재판정(G14)

### AC-AIR6-016 — 최종본 인정과 규칙 7 불변식 (REQ-AIR6-016)

조건 18개를 표 구동으로 시험한다. 조건 0(`final_not_allowed`)은 `select_report`가 평가하고, 조건 1~17은 단일 순수 함수 `evaluate_admissibility`가 평가한다. 영수증 작성기와 `select_report`가 같은 조건 코어를 실행하며(작성기는 코어를, `select_report`는 디스크 래퍼를 부른다) 작성기는 1~17만 평가한다. 함수는 예외를 던지지 않고 읽을 수 없는 입력은 미충족으로 본다(REQ-AIR6-016의 읽기 보호 규칙).

**되돌림 주장의 정확한 범위.** 한 조건의 검사를 제거했을 때 관측되는 변화에는 두 수준이 있다.
- **수준 A (결과가 뒤집힘)**: 그 조건 하나만 어기는 *격리 케이스*의 결과가 `draft`에서 `final`로 바뀐다. 조건 0, 2~12, 14~17의 16개가 여기에 속한다.
- **수준 B (사유 목록이 바뀜)**: 읽기 보호 조건 1(영수증 존재)과 13(`audit-review.json` 존재)은 입력을 아예 못 읽는 상황을 막는다. 그 상황에서는 다른 조건도 입력을 못 읽어 미충족이 되므로, 1이나 13을 제거해도 결과는 `draft`로 남고 보고되는 사유 목록만 달라진다(예: 1을 빼면 `no_receipt` 대신 `receipt_invalid`가 보고됨). 모든 케이스가 `reasons` 목록 전체를 **순서까지 정확히** 단언하므로 수준 B도 RED로 관측된다.

아래 "자연 흐름" 케이스는 실제 공격 경로를 재현한다. 여러 조건이 함께 걸려 어느 한 조건의 제거로는 뒤집히지 않으므로 되돌림 대상이 아니며, 공격이 막히는지를 보이는 용도다.

- Given: 작업 폴더 픽스처 빌더. 기준 픽스처 P = 모든 조건을 만족하는 상태(`final/report.html` + `final/render-validation.json{delivery_allowed: true}` + `draft/` + 색인 complete·모바일 넘침 없음·타일 파일·서버 방식으로 쓴 영수증 `outcome: reviewed`·`tiles_read` 전부·`judged_writes: []`·스냅샷 start==end·유효한 `audit-review.json`(`separate_review_pass`, `visual: pass`, 증거에 `[렌더 차이]`, `reviewed_at` ≥ 색인 `finished_at`, `preview_sha256` 일치)). 격리 케이스는 P에서 **정확히 하나의 입력만** 바꾼다. 색인·타일처럼 화면 스냅샷에 속하는 파일을 바꾸는 격리 케이스는 빌더가 영수증의 `snapshot_start`·`snapshot_end`를 바뀐 상태로 다시 측정해 맞춘다(세션 시작 전에 이미 그 상태였던 것과 같다). 그래야 스냅샷 조건 6이 함께 걸리지 않는다

**격리 케이스 (한 조건씩)**

| 케이스 | 변경 (P에서 하나만) | 기대 `reasons` (정확히) | 격리하는 조건 · 수준 |
|---|---|---|---|
| (a) | 변경 없음 | `[]` → `("final", final_dir)` | — |
| (n) | `final/render-validation.json`의 `delivery_allowed: false` | `select_report` 쪽 `[final_not_allowed]`. `evaluate_admissibility`를 직접 부르면 admissible(`[]`) | 0 · A |
| (b) | 영수증 파일 삭제 | `[no_receipt]` | 1 · B |
| (b2-i) | 영수증 `schema_version: 2` | `[receipt_invalid]` | 2 · A |
| (b2-ii) | 영수증에서 진단용 키(`reasons`) 하나 삭제 | `[receipt_invalid]` | 2 · A |
| (r) | 영수증 `outcome: timeout` | `[review_not_completed]` | 3 · A |
| (w) | 영수증 `judged_writes`에 `draft/` 경로 1건 | `[judged_input_write_attempt]` | 4 · A |
| (d) | 색인 `outcome: partial`(나머지 값은 그대로) | `[screens_not_complete]` | 5 · A |
| (s) | 영수증 작성 뒤 `index.json`의 모바일 `horizontal_overflow`를 `true`→`false`로 위조(영수증 스냅샷은 `true` 상태의 색인) | `[screens_changed]` | 6 · A |
| (x) | 영수증 작성 뒤 `screens/`에 색인에 없는 새 파일 `mobile-99.png` 추가 | `[screens_changed]` | 6 · A |
| (t7) | 타일 하나를 세션 시작 전에 삭제(색인에는 그대로 있음, 스냅샷은 삭제 상태로 일관) | `[tile_missing]` | 7 · A |
| (g2) | 타일 하나의 바이트를 세션 시작 전에 변조(스냅샷은 변조 상태로 일관, 색인 해시는 원본) | `[tile_hash_mismatch]` | 8 · A |
| (k) | 영수증 작성 뒤 `draft/report-input.json` 바이트 변경 | `[draft_changed]` | 9 · A |
| (k2) | 영수증의 `hashes.preview_end`가 디스크의 `draft/report.html` 해시와 다름 | `[draft_changed]` | 9 · A |
| (e) | 색인 `preview_sha256`이 현재 `draft/report.html` 해시와 다름(낡은 화면; 스냅샷은 그 상태로 일관) | `[preview_hash_mismatch]` | 10 · A |
| (m) | `audit-review.json`의 `preview_sha256`이 현재 `draft/report.html` 해시와 다름 | `[preview_hash_mismatch]` | 10 · A |
| (c) | 타일 하나가 `tiles_read`에 없음 | `[tile_not_read]` | 11 · A |
| (c2) | 영수증 `tiles_expected`가 색인의 타일 목록과 다름 | `[tile_not_read]` | 11 · A |
| (f) | 색인 모바일 `horizontal_overflow: true`(스냅샷은 그 상태로 일관) | `[mobile_overflow]` | 12 · A |
| (o) | `audit-review.json` 삭제(영수증 작성 뒤) | `[no_audit_review]` | 13 · B |
| (h) | `audit-review.json`의 `mode: independent_agent` | `[mode_not_separate_review_pass]` | 14 · A |
| (i) | `checks.visual.status: revise` | `[visual_not_pass]` | 15 · A |
| (j) | `reviewed_at`이 색인 `finished_at`보다 이름 | `[reviewed_before_capture]` | 16 · A |
| (p) | `checks.visual.evidence`에서 `[렌더 차이]` 표지 제거 | `[font_note_missing]` | 17 · A |

**읽기 실패 케이스 (fail-closed 시험 — 특정 조건의 되돌림 대상이 아님)**

| 케이스 | 변경 | 기대 `reasons` (정확히) |
|---|---|---|
| (b3) | 영수증이 깨진 JSON | `[receipt_invalid]` (예외 없음, 의존 조건 3·4·6·9·11은 보고하지 않음) |
| (d2) | 색인 파일이 깨진 JSON(스냅샷은 그 상태로 일관) | `[screens_not_complete]` (예외 없음, 의존 조건 7·8·11·12·16은 보고하지 않음 — 16은 색인의 `finished_at`을 읽는다, iter3 N11) |
| (o2) | `audit-review.json`이 깨진 JSON | `[no_audit_review]` (예외 없음, 의존 조건 14~17은 보고하지 않음) |

**자연 흐름 케이스 (여러 조건이 함께 걸림 — 되돌림 대상 아님)**

| 케이스 | 변경 | 기대 `reasons` (정확히) |
|---|---|---|
| (g) | 영수증 작성 뒤 타일 하나를 다른 바이트로 덮어씀(영수증의 저장된 `visual_admissible: true`·`reasons: []`는 그대로) | `[screens_changed, tile_hash_mismatch]` |
| (g3) | 영수증 작성 뒤 색인에 적힌 타일 파일 하나 삭제 | `[screens_changed, tile_missing]` |
| (kr) | 영수증 작성 뒤 `draft/report.html` 바이트 변경 | `[draft_changed, preview_hash_mismatch]` |

- When: 각 케이스에서 `evaluate_admissibility(job_dir)`와 `select_report(job_dir)`를 호출하고, `archive_job`이 같은 `delivery_status`를 쓰는지 확인한다. 영수증 작성기를 거치는 케이스는 작성기가 `reasons`를 채운 결과를 읽어 같은 시점의 `select_report` 사유와 비교한다. 작성기는 영수증이 디스크에 없는 상태에서 방금 측정한 사실을 인자로 조건 코어를 부르고(iter3 N12) 영수증을 한 번만 쓴다: 테스트는 코어 호출 시점에 `review/receipt.json`이 없음을 확인하고 그 경로에 대한 최종 교체가 정확히 1번임을 단언한다
- Then: (a)만 `("final", final_dir)`. 나머지는 모두 `("draft", draft_dir)`이고 `reasons`가 표의 기대 목록과 **순서까지 정확히 같다**. 첫 항목이 로그에 남는다. `archive_job`의 `delivery_status`도 같다. 추가로 영수증 없는 `final/`만 있고 `draft/`가 없는 폴더는 `None`(기존 규칙)
- 명령: `PY -m pytest backend/tests/test_goose_runner.py backend/tests/test_goose_review.py -k air6_016 -q`
- 잡는 구현(조건별 되돌림 RED — 해당 조건의 검사만 제거한 변형에서 아래 케이스가 RED):
  - 수준 A: 0→(n), 2→(b2-i)(b2-ii), 3→(r), 4→(w), 5→(d), 6→(s)(x), 7→(t7), 8→(g2), 9→(k)(k2), 10→(e)(m), 11→(c)(c2), 12→(f), 14→(h), 15→(i), 16→(j), 17→(p). 각 변형에서 해당 케이스가 `final`이 되어 RED
  - 수준 B: 1→(b), 13→(o). 각 변형에서 결과는 `draft`로 남지만 사유 목록이 기대와 달라져 RED
  - 읽기 실패 처리를 허용으로 바꾼 변형(fail-open) → (b)(b3)(d2)(o)(o2)가 `final`이 되어 RED. 읽기 실패에서 예외를 던지는 변형 → (b3)(d2)(o2)가 오류로 RED
  - **저장된 `visual_admissible`을 입력으로 사용하는 구현 → (g)(kr)에서 RED**(디스크가 바뀌었는데 `final`)
  - 판정 함수를 영수증 작성기와 `select_report`가 따로 구현(조건 목록 갈라짐) → 두 호출 결과 비교 단언(작성기 `reasons` == 같은 시점 `select_report` 사유) RED
  - 작성기가 디스크 래퍼를 부르는 변형(영수증이 아직 없어 `[no_receipt]`) → (a)에서 작성기 `reasons == [no_receipt]`가 되어 RED. 작성기가 판정을 위해 영수증을 먼저 쓰고 결과를 넣어 다시 쓰는 변형 → 영수증 교체 횟수 1 단언과 코어 호출 시점의 파일 부재 단언 RED
  - 읽기 보호 목록에서 16을 뺀 v0.3.0 형태의 변형 → (d2)가 `[screens_not_complete, reviewed_before_capture]`가 되어 RED
  - 되돌림 대상이 아닌 짝: 6과 8, 9와 10은 같은 공격(타일 덮어쓰기, 보고서 변경)에 함께 걸려 (g)(kr)에서는 한쪽을 빼도 다른 쪽이 막는다 — 그래서 각자의 격리 케이스로 시험한다
- 잡지 못하는 것: 영수증 조건을 모두 만족하면서 판단이 틀린 감수(범위 밖 — 영수증은 열람 사실과 판단 대상 불변만 증명), 도구 밖 경로 변조(G11), `final/` 산출물이 렌더러가 만든 것인지(조건 0은 두 파일의 존재와 `delivery_allowed`만 본다, G13), `audit-review.json`이 영수증 작성 뒤에 바뀌는 경우(G15)

### AC-AIR6-017 — 테스트 격리와 회귀 (REQ-AIR6-017)

횡단 기준이다. M2~M5 각 마일스톤 종료 때 `pytest backend/tests -k goose`로 확인하고, 최종 판정은 M5 종료 시점에 한다(plan.md §3).

- Given: 변경 후 작업 트리
- When: goose 백엔드 테스트 전체와 새 테스트를 실행하고, 격리 점검을 한다
- Then: (1) `pytest backend/tests -k goose` 실패 0이고 통과 수 ≥ 기준선 267 + 새로 추가한 테스트 수 − 의도적으로 지운 테스트 수(M4가 갱신한 기존 테스트 목록을 `progress.md §E.2`에 적는다). (2) 네트워크 가드 기록 0건(가드가 종료 시 단언). (3) 새 테스트 파일에서 실제 `claude`·브라우저 실행 파일을 이름으로 호출하는 곳이 없다: `git grep -n "chrome-headless-shell\|Google Chrome\|ms-playwright" -- backend/tests`는 테스트가 만든 가짜 경로 상수 외에 없다. (4) 가드 자체 검사: 새 후처리 경로가 주입 없이 실제 DevTools 연결(`127.0.0.1` 소켓)을 시도하게 임시로 바꾸면 테스트가 `network attempt in goose test`로 실패한다(되돌림 관측)
- 명령: `PY -m pytest backend/tests -k goose -q -p no:cacheprovider`
- 잡는 구현: 가짜 드라이버 주입 대신 실제 CDP 연결을 여는 테스트 → (2)·(4)에서 RED
- 잡지 못하는 것: 이 호스트에서만 나타나는 브라우저 설치 의존 동작(AC-018)

### AC-AIR6-018 — 라이브 관측 게이트 (REQ-AIR6-018)

라이브 관측 게이트다. 통과해야 SPEC을 닫는다(§F). 감수 세션(모델)의 판단에 달려 있으므로 같은 KST 날짜에 020150으로 최대 2회 실행할 수 있다.

**통과 규칙(명시).** 게이트는 다음 둘이 모두 참일 때 통과다: (가) 실행한 **모든 회차**가 5(안전 불변식)를 만족한다. (나) 실행한 회차 중 **적어도 한 회차**가 1~4(작업·화면·열람·기록 형식)를 모두 만족한다. 1~4를 만족하지 못한 회차는 원인을 `progress.md §E.2`에 남겨야 한다(원인 없는 실패 회차는 게이트 실패). 두 번째 회차는 첫 회차가 기록된 원인으로 1~4를 만족하지 못했을 때만 허용되는 재시도이며 추가 관문이 아니다. LLM 판단의 비결정성 때문에 한 회차 통과로 충분하되, 안전 불변식(5)은 회차를 가리지 않는다.

**`[렌더 차이]` 표지 누락의 결과는 한 가지다.** 누락은 서버 조건 17(`font_note_missing`) 미충족이므로 영수증이 화면 확인을 인정하지 않고 전달은 `draft`가 된다. 이는 설계된 안전 방향 결과이며 규칙 7 불변식 결함이 아니다. 게이트에서의 취급: 한 회차의 누락은 그 회차가 (나)군의 4를 만족하지 못하게 할 뿐 (가)군 실패가 아니다. 모든 회차에서 누락되면 (나)가 불충족이라 게이트가 실패한다.

- Given: M5 반영 후 서버 재시작과 AC-013 #5 통과, 기준선 research.md P2·P3(같은 종목 이전 실행에서 대상 8종 전부 발생), 운영 호스트에 Playwright 캐시의 `chrome-headless-shell`이 있음
- When: 앱에서 020150으로 goose 작업을 실행하고 끝까지 기다린다. 452190은 선택 관측(게이트 아님)
- Then (작업과 같은 KST 날짜에 확인, `R`은 `~/.goose-harness/runs/<job_id>`):
  1. 작업 `status: done`
  2. `R/screens/index.json`의 `outcome == "complete"`이고 두 뷰포트 `ok`, 타일 파일이 모두 존재하며 SHA-256 일치
  3. `R/review/receipt.json`: `screens.tiles_read`가 `screens.tiles_expected`를 모두 포함(감수 세션이 모든 타일을 실제로 열었다), `process.exit_code == 0`, `draft_unchanged == true`, `judged_writes == []`, `screens.snapshot_start == snapshot_end`
  4. **감수 기록의 형식이 올바르다**(정직한 부정 결과를 가로막지 않는 조건): `python3 -I ~/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input R/draft/report-input.json --preview R/draft/report.html --review R/audit-review.json --output "$S/audit.json"`의 결함 코드 집합이 `{AUDIT_INPUT_VERSION, AUDIT_PREVIEW_VERSION, AUDIT_TIME, AUDIT_MODE}`와 교집합이 공집합이고, `R/audit-review.json`의 5개 검사(`source_accuracy`, `calculations`, `coverage`, `opinion`, `visual`)가 모두 존재하며 각 `evidence`가 비어 있지 않고, `checks.visual.evidence`가 `[렌더 차이]` 표지를 **포함**한다(서버 조건 17과 같은 기준). 각 검사의 `status`가 `pass`인지 `revise`인지는 게이트 조건이 아니다 — 기록만 한다(`REVIEW_SOURCE_ACCURACY`·`REVIEW_CALCULATIONS`·`REVIEW_COVERAGE`·`REVIEW_OPINION`·`REVIEW_VISUAL`이 정당한 `revise` 때문에 남는 것은 정상이다)
  5. **안전 불변식(모든 회차)**: (i) `receipt.visual_admissible == false`이면 전달 상태(`job.json`/작업 완료 이벤트의 `delivery_status`)는 `draft`다. (ii) 전달 상태가 `final`이면 `R/final/delivery-audit.json`의 `decision == "pass"`다. (iii) 작업 완료 이벤트의 `delivery_status`가 `R`을 보관한 폴더의 `job.json`의 값과 같다(REQ-AIR6-019). (iv) 영수증 내부 정합: `visual_admissible == true`이면 `reasons`가 비어 있고 `false`이면 비어 있지 않다
- **알려진 한계(7번 결함 처리).** 020150 라이브 실행에서는 네이버 검색이 `blocked`로 기록돼(research P23) `LATEST_SEARCH_NAVER`가 남고 감사 결정이 `pass`가 되지 못하므로 `--final`이 실행되지 않는다 — 카드 t19가 해소한다. 따라서 이 AC의 5(i)·5(ii)는 라이브에서 "`draft`·최종본 없음" 쪽만 관측되고, `final` 인정 경로는 AC-AIR6-022(격리 통합 시험)와 AC-016이 담당한다
- 비게이팅(기록만): 5개 검사 각각의 `pass`/`revise` 결과와 `REVIEW_*` 코드 잔존, `checks.visual.status == "pass"`인데 `visual_admissible == false`인 회차의 수와 그 `reasons`(표지 누락·타일 미열람 등 — 지침 미준수로 분류), `visual.evidence`가 표지로 *시작*하는지 여부(지침은 시작을 요구하고 서버와 게이트는 포함만 확인한다), `LATEST_SEARCH_NAVER` 등 이 SPEC 범위 밖 결함, 최종본 도달 여부, 소요 시간·토큰(research G5), 진행 패널 화면 배치, **자정(KST)을 넘겨 후처리 감사에서 `FRESHNESS_CUTOFF`가 추가로 난 경우**(`audit_report.py:32-33`, research P31 — 게이팅 코드가 아니므로 기록만)
- 실패 시 기록: 2 실패 → 캡처 결함(브라우저·타일), 2 통과·3 실패 → 감수 세션이 이미지를 안 열었거나 영수증 수집 결함(스트림 모양 확인), 3 통과·4 실패 → 지침 미준수(표지 누락 포함) 또는 컨텍스트 결함(남은 코드와 해당 필드를 그대로 기록), 5 위반 → 규칙 7 불변식 결함(최우선; 5는 안전 불변식만 가리키며 표지 누락·미인정 `pass`는 5가 아니라 4와 비게이팅 기록의 몫이다). 어느 경우든 SPEC은 닫지 않고 manager-spec 재위임으로 고친 뒤 다시 잰다
- 대조(되돌림 관측): 같은 회차의 `R/draft`에 대해 `--review`를 주지 않은 감사 출력은 P2-A와 같이 형식 코드 4개(와 `REVIEW_*` 5개)를 모두 낸다 — 4의 판정이 이 입력에서 공집합이 될 수 있음을 보이는 기준선으로 같이 기록한다
- 잡는 구현: 캡처는 되지만 감수 세션이 지침을 따르지 않아 `audit-review.json`이 없음 → 4 실패, 감수 세션이 해시를 틀리게 옮김 → `AUDIT_INPUT_VERSION`/`AUDIT_PREVIEW_VERSION`으로 4 실패, `visual` 증거에 표지를 빠뜨림 → 조건 17로 영수증이 인정하지 않아 전달은 안전하게 `draft`(5 만족)이고 그 회차는 4 실패로 (나)군에서 탈락, 타일을 열지 않고 `visual: pass`를 적음 → 영수증이 인정하지 않아 전달은 안전하게 `draft`(5 만족)로 내려가지만 3 실패로 그 회차는 (나)군에서 탈락하고 비게이팅 기록에 "`pass`인데 미인정"으로 남는다(지침 미준수로 분류해 지침을 고친 뒤 다시 잰다). 감수 세션이 결함을 찾아 정직하게 `revise`를 적음 → 4·5 모두 만족(게이트를 막지 않는다)
- 잡지 못하는 것: 감수 세션이 열었다고 한 자료를 실제로 끝까지 읽었는지, 사실 대조의 충실도(스트림 기록으로 열람 사실만 확인, G6), `final` 인정 경로의 라이브 관측(위 한계)

### AC-AIR6-019 — M1 GO/NO-GO 게이트: 캐너리 토큰 인용 (REQ-AIR6-020)

M1은 게이트다. 실제 `claude -p`가 서버가 만든 PNG를 정말 "보는지"를 이진으로 판정한다. 성공한 `tool_result` 하나는 모델이 이미지를 인지했다는 증거가 아니다(이미지가 너무 커 축소됐거나 글자가 뭉개졌을 수 있다, G4). REQ-AIR6-020과 이 AC는 같은 GO 정의를 쓴다.

- Given: 실제 `claude`(설치본)와 설치된 하네스, 그리고 **M1 전용 스파이크 스크립트**(증거 폴더 `$S`에 보관하고 병합하지 않는다). 스크립트는 M2 캡처 모듈에 의존하지 않고, REQ-AIR6-006·009가 정한 것과 같은 DevTools 호출(뷰포트 1280/390, 모바일 에뮬레이션, 스크립트 비활성, 외부 네트워크 전면 차단, `file://`, 높이 1568px `clip` 타일)로 캐너리 페이지를 찍고, 타일은 설치된 하네스 폴더의 `~/.goose-harness/runs/<canary>/` 아래에 저장한다(하네스 권한이 `Read(./**)`만 허용하므로 폴더 밖 파일은 허용 규칙이 덮지 못한다, research P35). 캐너리 페이지는 두 뷰포트 모두 타일이 2개 이상이 되는 높이로 만든다. 뷰포트마다 임의 토큰 3개(영숫자 6자, 매번 새로 생성, 파일·프롬프트에 사전 노출 없음)를 (가) 보고서 본문 글자 크기(초안의 계산된 `font-size`를 M1이 측정해 사용) 1개, (나) 그보다 작은 두 크기 각 1개로 그린다. 본문 크기 토큰 (가)는 첫 타일 바깥, 즉 `y > 0` 타일 안에 놓는다
- When: 감수 세션과 같은 인자·설정(REQ-AIR6-011)으로 `claude -p`를 실행해 "각 타일 파일을 Read로 열고 그림 안의 토큰을 그대로 답하라"고 시킨다. 프롬프트에는 토큰도 정답도 없다. 스트림을 서버 쪽에서 기록한다
- Then (GO 조건 전부 — REQ-AIR6-020과 동일):
  1. 응답이 **두 뷰포트의 본문 크기 토큰 (가) 2개를 모두 정확히(대소문자 포함 문자열 일치) 인용**한다
  2. 스트림에 **모든 캐너리 타일**에 대한 `Read` `tool_use`와 짝이 맞는 `tool_result`가 있고 `is_error`가 `false`이거나 키가 없다
  3. `y > 0` 타일의 PNG가 `y == 0` 타일과 해시가 다르고 높이가 요청 구간과 같다(타일 `clip` 동작, G3)
- NO-GO: 위 1~3 중 하나라도 어긋나는 모든 경우(본문 크기 토큰 오인용·거부·오류 `tool_result`·시간 초과·`claude` 부재 포함). NO-GO 결과: M2~M6 코드를 병합하지 않는다, 관측 원문(명령·출력)을 `progress.md §E.2`에 기록한다, SPEC은 계획 단계로 되돌아가며 **이 문서는 바뀌지 않은 채** manager-spec 재위임과 운영자 결정(예: 타일 높이 축소 재시도 1회, 또는 "화면 확인"의 의미 변경)을 거친다. 타일 높이를 줄여 재시도해 GO가 되면 그 높이가 새 상수가 되고 AC-006의 타일 높이 리터럴은 재계산해 manager-spec 재위임으로 고친다
- GO 판정과 무관한 기록 (모두 `progress.md §E.2`에 측정값으로, 메모가 아니라 수치):
  4. **가독성 임계값**: (나) 토큰을 포함해 토큰을 맞게 인용한 가장 작은 글자 크기. (나) 토큰의 오인용은 NO-GO가 아니며 이 임계값으로만 기록한다(G4). `Read` 한 번에 걸린 시간도 적는다(G5)
  5. 기존 초안 4개의 높이·타일 분포를 재측정해 기록한다(REQ-AIR6-008, research P26)
- 조정 후 진행 (GO/NO-GO를 바꾸지 않는다, 부족하면 M2 병합 전에 이 문서를 고친다):
  - (a) 타일 상한(`TILE_CAP`)이 5에서 재측정한 최대 타일 수의 1.5배보다 작으면 상한을 올려 REQ-AIR6-008과 AC-AIR6-008을 manager-spec 재위임으로 고친 뒤에만 M2를 병합한다
  - (b) `Read` 한 번의 시간 × 33(020150 초안의 타일 수: 데스크톱 13 + 모바일 20, research P26)이 감수 시간 상한 기본값 900초(`AI_REPORT_GOOSE_REVIEW_TIMEOUT`)를 넘으면 기본값을 올려 REQ-AIR6-011과 AC-AIR6-011, research G5를 manager-spec 재위임으로 고친 뒤에만 M2를 병합한다
- 명령: M1 스파이크 스크립트(증거 폴더 `$S`에 보관)와 그 출력 원문. 자동 시험이 아니라 관측 게이트다(실제 `claude`·브라우저 사용 — REQ-AIR6-017의 격리 시험과 구분되는 유일한 예외로, M1에서만 허용)
- 잡는 구현(= 이 게이트가 막는 오판): 이미지 `Read`가 성공으로 보이지만 모델이 내용을 못 보는 환경 → 토큰 미인용으로 NO-GO. 프롬프트에 정답을 넣어 통과시키는 스크립트 오류 → 토큰이 사전 노출되지 않았음을 `claude` 입력 로그로 확인(위 Given). `y > 0` 타일이 실제로는 `y == 0` 타일과 같은 그림(`clip` 무시) → 3번으로 NO-GO
- 잡지 못하는 것: 실제 보고서 화면의 모든 시각 결함 인식(토큰 인용은 "글자를 읽을 수 있다"까지만), 감수 세션이 실제 감수에서 모든 타일을 꼼꼼히 보는지(G6)

### AC-AIR6-020 — 작업 완료 이벤트의 전달 상태 소유 (REQ-AIR6-019)

- Given: 가짜 실행기(1차 세션 직후 `RunResult.delivery_status`로 `"draft"`를 돌려줌 — 영수증이 아직 없으므로 `select_report`도 `draft`), 가짜 캡처기, 가짜 감수기(`final/`·`delivery_allowed: true`·영수증 인정 조건을 모두 만족하는 디스크 상태를 만든다), 임시 `runs`/보관 폴더. 시나리오 (1) 실제 종료 훅(`archive_job`)을 주입, (2) 훅 없음, (3) 훅이 `{}`를 돌려줌(`archive_job`이 `None`), (4) 감수기가 인정되지 않는 상태를 만든다(훅 주입), (5) 스위치 `AI_REPORT_GOOSE_REVIEW=0`(훅 없음), (6) 두 번째 무결성 검사 실패(훅 없음). (5)(6)의 가짜 실행기는 일부러 같은 디스크 상태의 `select_report` 결과(`draft`)와 **다른** 값 `"final"`을 돌려준다 — 실제 실행기에서는 나오지 않는 값이며 전달 상태 값의 출처를 가르기 위한 것이다
- When: 작업 실행 후 완료 이벤트의 `data.delivery_status`와 보관된 `job.json`의 값을 읽는다
- Then: (1) 이벤트 `delivery_status == "final"`, `job.json`도 `"final"`, 둘이 `archive_job`의 반환과 같다 — 실행기 값 `draft`와 **다른** 경우다. (2) 이벤트 `"final"`(`select_report` 재계산값). (3) 이벤트 `"final"`(재계산값, 실행기의 `draft`가 아님). (4) 이벤트 `"draft"`, `job.json` `"draft"`. (5) 후처리가 돌지 않았으므로 실행기가 계산한 값 `"final"`을 그대로 쓴다(재계산하면 `draft`가 되어 어긋난다). (6) 캡처·감수가 시작되지 않았으므로 실행기 값 `"final"`을 그대로 쓴다
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_020 -q`
- 잡는 구현: (a) 이벤트에 `result.delivery_status`를 그대로 사용(스테일) → (2)(3)에서 `draft`로 RED, (b) 훅 값이 없을 때만 재계산하고 훅 값이 `None`인 경우를 처리하지 않음 → (3) RED, (c) 이벤트와 `job.json`이 서로 다른 시점의 값 → (1)에서 불일치 RED, (d) 스위치 0일 때도 재계산 → (5)에서 `draft`가 나와 RED(실행기 값 `final`과 달라서 관측됨), (e) 무결성 재검사가 실패한 경우에도 재계산 → (6)에서 `draft`가 나와 RED
- 잡지 못하는 것: 실제 보관 폴더 구조의 모든 파일(`goose_storage` 기존 시험 담당), 영수증 쓰기 실패 때의 이벤트 값(AC-015 S9가 담당)

### AC-AIR6-021 — 글꼴 차단 증거 문구 요건 (REQ-AIR6-013, REQ-AIR6-016 조건 17)

운영자 결정(2026-10-21): 캡처는 외부 네트워크를 전부 막으므로 렌더링이 실제 화면과 다르다. 감수 기록이 그 사실을 적었는지 서버가 확인한다. 표지 누락의 결과는 한 가지다: 조건 17 미충족, 전달 `draft`(설계된 안전 방향 결과).

- Given: AC-016의 기준 픽스처 P 변형. 케이스: (1) `visual.evidence`가 `[렌더 차이]`로 시작하고 차단 사실을 적음, (2) 표지를 앞에서 뒤로 옮긴 문구(포함은 하지만 시작 아님)는 **인정**(조건은 "포함"), (3) 표지 없음, (4) 비슷한 문구(`[렌더링 차이]`, `[render diff]`)
- When: `evaluate_admissibility`와 `select_report`를 호출한다. 별도로 `context.json`의 `screens.render_note`와 하네스 지침 문구를 읽는다
- Then: (1)(2) 다른 조건이 충족되면 `final`. (3)(4) `("draft", …)`, `reasons == [font_note_missing]`. `render_note`는 AC-012의 고정 문장이고 지침(규칙 10, 10-6)에 `[렌더 차이]` 표지 문구가 있다
- 명령: `PY -m pytest backend/tests/test_goose_review.py backend/tests/test_goose_harness.py -k air6_021 -q`
- 잡는 구현(되돌림 RED): (a) 조건 17을 제거 → (3)(4)가 `final`이 되어 RED, (b) 정확히 일치하지 않는 표지도 인정(정규식 완화) → (4) RED, (c) 지침에서 표지 문구 삭제 → 지침 문구 단언 RED, (d) 컨텍스트에서 `render_note` 누락 → AC-012 RED, (e) 표지가 시작에 있을 때만 인정(조건을 "시작"으로 구현) → (2)가 `draft`가 되어 RED
- 잡지 못하는 것: 표지 문구가 실제로 차이를 이해하고 적었는지(문자열 존재만 확인 — 약한 증거), 차이가 판단에 미치는 영향. 라이브에서의 표지 누락 빈도는 AC-018의 (나)군 형식 요건과 비게이팅 기록

### AC-AIR6-022 — 최종본 인정 경로의 격리 통합 시험 (REQ-AIR6-016·019, plan-audit D7)

020150 라이브 실행은 `LATEST_SEARCH_NAVER` 때문에 `final`에 도달하지 못한다(AC-018 한계, research P23). 최종본 인정이 판정 표(AC-016)의 합성 픽스처에서만 확인되는 것을 막기 위해 실제 감사기·렌더러를 거치는 끝에서 끝까지의 시험을 둔다.

- Given: 검색 채널 규칙을 만족하는 합성 입력(라이브 초안 입력에서 `naver` 채널의 `blocked` 항목을 `no_results`로 바꾸고, 시험 시점의 날짜로 `cutoff`·`as_of`·`searched_at`을 다시 쓴 것 — research P24·P25에서 이 패치로 감사 결정 `pass`와 `final/` 생성이 관측됨), 벤더링된 실제 `audit_report.py`·`render_report.py`(`backend/goose_harness_src/skills/…`의 임시 복사본, 실제 홈·설치본 불사용), 가짜 캡처기(결정적 PNG, `complete` 색인), 가짜 `claude` 스크립트(`context.json`을 읽고 `copy_into_review_record` 값으로 감수 기록 5개 검사 `pass`·`[렌더 차이]` 증거를 쓰고, 합성 스트림으로 모든 타일 `Read`와 성공 `tool_result`를 출력하고, 임시 하네스에서 `audit_report.py`와 `render_report.py --final`을 실제 실행), 실제 종료 훅
- When: 작업을 끝까지 실행한다
- Then: 감사 출력의 `decision == "pass"`, `final/render-validation.json`의 `delivery_allowed == true`, 영수증 `visual_admissible == true`, `select_report == ("final", final_dir)`, 완료 이벤트 `delivery_status == "final"`(AC-020과 일치), `render_final` 진행 이벤트 정확히 1개. 대조로 같은 시험에서 가짜 `claude`가 타일 하나를 열지 않으면 `draft`
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air6_022 -q`
- 잡는 구현: 영수증 경로와 실제 감사기·렌더러 사이의 단절(예: 컨텍스트의 값 이름이 감수 기록이 요구하는 키와 어긋남, 영수증 시각 조건이 실제 `reviewed_at`과 어긋남, `final/` 위치 불일치) → `decision`이 `pass`가 아니거나 `select_report`가 `draft`. 각각 해당 단계의 되돌림(예: `copy_into_review_record`의 `preview_sha256`을 틀리게)으로 RED를 관측한다
- 잡지 못하는 것: 실제 `claude`의 지침 준수(AC-018 라이브), 실제 웹 검색의 결과. 시험 시점 날짜 재작성 빌더는 미관측(research G10) — 만들 수 없으면 이 AC를 Gap으로 `progress.md`에 기록하고 사유를 남긴다(그 경우 SPEC은 이 Gap을 명시한 채 닫을 수 있는지 manager-spec 재위임으로 판단)

## §D 경계 사례

| 사례 | 기대 동작 | 담당 AC |
|---|---|---|
| 브라우저가 호스트에 없음 | 색인 `unavailable`, 감수는 실행되고 `visual: revise`, 전달 `draft` | AC-005·010 |
| 페이지가 매우 길어 타일 상한 초과 | 해당 뷰포트 `too_tall`, 타일 없음, 최종본 불가 | AC-008·016 |
| 모바일 문서 폭 넘침 | `horizontal_overflow`가 참이면 최종본 불가 | AC-007·016 |
| 감수 세션이 초안을 몰래 수정 | 영수증 `draft_unchanged: false`, 최종본 불가 | AC-014·016 |
| 감수 세션이 `screens/` 색인·타일을 고치거나 추가·복원 | 스냅샷 불일치 또는 `Write`/`Edit` 기록 → 최종본 불가 | AC-014·016 |
| 감수 세션이 대소문자만 다른 경로로 `screens/`를 씀 | `judged_writes`에 기록(대소문자 무시 비교), 최종본 불가 | AC-014 |
| 감수 세션이 영수증을 위조 | 서버가 종료 후 덮어씀, 판정은 저장된 불리언을 믿지 않고 재계산 | AC-015·016 |
| 1차 세션이 `audit-review.json`·`final/`을 미리 심고 감수 세션이 덮어쓰지 않음 | 서버가 세션 시작 전에 삭제, 삭제 실패면 세션 미시작, 심은 파일은 인정 근거가 되지 못함 | AC-014 (11)~(13) |
| 서버의 영수증 쓰기가 실패 | 세션이 쓴 영수증을 먼저 제거, 남으면 이벤트 `draft`, 로그 `receipt_write_failed` | AC-015 |
| 감수 세션이 결함을 찾아 정직하게 `revise`를 기록 | 게이트를 막지 않음, 전달 `draft` | AC-018 |
| 정상 감수인데 첫 세션 값과 영수증 뒤 값이 다름 | 완료 이벤트는 영수증 뒤 값 | AC-020 |
| 글꼴 차단 증거 표지 누락 | 조건 17 미충족, 전달 `draft`(설계된 안전 방향 결과) | AC-021 (라이브: AC-018 (나)군 형식 요건) |
| 라이브 020150이 `LATEST_SEARCH_NAVER`로 `final`에 못 감 | 인정 경로는 격리 통합 시험으로 확인 | AC-022 |
| 감수 세션이 타일을 열지 않고 `pass` 선언 | `tile_not_read`로 최종본 불가 | AC-015·016 |
| 끄기 스위치 | 후처리 없음, 영수증 `disabled`, 전달 `draft` | AC-004 |
| 서버 종료 중 후처리 | `cancelled`, 프로세스 그룹 정리 | AC-002 |
| 후처리 중 무결성 재검사 실패 | 캡처·감수 없음, 영수증 `integrity_failed` | AC-001 |
| 외부 웹 글꼴 차단으로 글꼴 대체(전면 차단, 운영자 결정) | 화면은 대체 글꼴, 증거에 `[렌더 차이]` 표지 필수 | AC-009(차단 전부), AC-013(문구), AC-021(서버 확인), AC-018(관측) |
| Playwright 캐시에 `chrome-headless-shell` 없음, `PATH`에 다른 Chrome 있음 | `unavailable`, 다른 브라우저로 폴백하지 않음 | AC-010 |
| 영수증·`audit-review.json`·색인이 깨져 있거나 없음 | 예외 없이 해당 보호 조건의 사유만 보고, `draft` | AC-016 |

## §E 품질 게이트

- 새 모듈(`goose_screenshot.py`, `goose_review.py`) 줄 커버리지 85% 이상. 측정은 `coverage run --source=backend -m pytest <파일>` → `coverage report`(lessons #9의 커버리지 측정 함정)
- `ruff check` 새 경고 0(기준선 대비)
- 대조 항목은 되돌림 RED 관측 후에만 GREEN 기록(§A). 영수증 판정(AC-016)은 조건 18개(`final_not_allowed` + 17개) 각각을 AC-016에 적은 수준으로 관측한다: 수준 A 16개는 해당 격리 케이스가 `draft`에서 `final`로 뒤집히는 것을, 수준 B 2개(조건 1·13)는 사유 목록이 달라지는 것을 관측한다. 관측하지 못한 되돌림은 조건 번호와 사유를 `progress.md §E.2`에 Gap으로 적는다(위 AC-016의 "자연 흐름" 케이스는 되돌림 대상이 아니다)
- @MX: 캡처 모듈의 브라우저 프로세스 진입점과 `select_report` 영수증 확인에 `@MX:ANCHOR`·`@MX:WARN`(+REASON), 주석 언어는 `code_comments: ko`

## §F 완료 정의

- AC-AIR6-019(M1 GO/NO-GO) GO와 조정 후 진행 규칙 (a)(b)의 반영 — 이후에만 M2 이후 코드를 병합
- AC-AIR6-001~017, 020~022 통과(명령·출력·기준선을 `progress.md §E.2`에 원문으로). AC-022를 만들 수 없으면 사유와 함께 Gap으로 기록
- AC-AIR6-018 통과(라이브 관측 게이트 — 통과 규칙은 AC-018 본문. 실패 기록만으로는 닫지 않는다)
- M1 관측값(research §4 G3·G4·G5·G8·G9)이 `progress.md §E.2`에 기록됨
- 매니페스트 재생성·서버 재시작·무결성 확인 완료(AC-013 #2·#5), `claude-settings.json`·`skills/**` 무변경(#3·#4)
- README·`.env.example`에 후처리 단계와 환경 변수 `AI_REPORT_GOOSE_REVIEW`·`AI_REPORT_GOOSE_BROWSER`·`AI_REPORT_GOOSE_REVIEW_TIMEOUT`, 브라우저 요건(Playwright 캐시의 `chrome-headless-shell`만 지원, 구동이 확인된 것만 목록에), "이 SPEC 이후에도 다른 감사 결함으로 `draft`일 수 있음"이 기록됨
