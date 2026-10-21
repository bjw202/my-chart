# SPEC-AI-REPORT-007 — 인수 기준

버전 0.1.0 · 요구사항은 `spec.md §5`(REQ-AIR7-001~013). 각 AC는 Given-When-Then, 실행 명령, 기대 관측 출력, **되돌림 검사**(이 한 가지 변경을 되돌리면 검사가 RED가 된다)와 **잡지 못하는 것**을 적는다. 되돌림 검사는 run 단계에서 실제로 적용해 RED 출력을 원문으로 남겨야 GREEN으로 기록할 수 있다(lessons #9). 관측하지 못한 되돌림은 `progress.md §E.2`에 Gap으로 남긴다.

## §A 공통 실행 조건

- Python 명령은 가상환경을 활성화한 뒤 실행한다. 서버용 가상환경은 코드 폴더와 다른 경로(`/Users/byunjungwon/Dev/my_chart/.venv`)에 있다. 아래 `PY`는 그 환경의 `python`이다.
- 테스트 함수 이름에 AC 꼬리표(`air7_001` 등)를 넣어 `-k`로 고른다.
- 모든 새 테스트는 파일 이름이 `test_goose_`로 시작하는 모듈에 둔다. 그래야 `backend/tests/conftest.py`의 네트워크 가드(시도 기록 + 종료 시 0건 단언)가 적용된다(SPEC-TEST-HERMETIC-001, SPEC-AI-REPORT-005 AC-014). 테스트에 실제 네트워크는 없다 — 요청은 `httpx.MockTransport`가 답한다.
- 기대값 중 기사 수·제목·본문은 손으로 옮겨 적지 않고 녹화 픽스처에서 테스트 실행 중에 추출한다(lessons #10). 여기 적힌 리터럴은 형식 규칙과 합성 픽스처 값뿐이다.
- `$S`는 세션 증거 폴더 `.moai/state/verify/<session>/`다.
- 되돌림 관측 절차: 변형 적용(임시 소스 편집 또는 monkeypatch) → 해당 명령 실행 → 실패 출력 원문 캡처 → 복원 → `git status --short`로 복원 확인.

## §B index.json 고정 키 집합 (AC-AIR7-007이 집합 동등으로 검사)

- 최상위: `schema_version`, `code`, `channel`, `search`, `outcome`, `started_at`, `finished_at`, `request_count`, `response_file`, `response_sha256`, `response_bytes`, `articles`
- `channel` 값: `"naver"`
- `search`: `url`, `query`, `searched_at`, `status`, `item_count`, `error`
- `articles[]` 항목: `article_ref`, `office_id`, `article_id`, `office_name`, `title`, `published_at`, `article_url`, `text_file`, `body_chars`, `status`, `error`
- `outcome` 값: `complete` | `partial` | `no_results` | `failed` | `disabled`
- `articles[].status` 값: `ok` | `metadata_only` | `error`
- 시각 필드(`search.searched_at`, `started_at`, `finished_at`, `articles[].published_at`): 시간대 포함 ISO-8601, 오프셋 `+09:00`
- `outcome` 판정: `ok`가 1개 이상이고 전부 `ok`면 `complete`, `ok`가 1개 이상이고 다른 상태가 섞이면 `partial`, 기사 0건이면 `no_results`, 그 밖(요청 실패, 기사는 있으나 `ok` 0개)은 `failed`
- 이 키 이름·경로는 run 단계 M1 관측(spec G4·G5)으로 바뀔 수 있다. 바뀌면 코드 작성 전에 manager-spec 재위임으로 이 절을 고친다.

## §C 인수 기준

### AC-AIR7-001 — 실행 순서 (REQ-AIR7-001)

- Given: 가짜 DART 수집기, 가짜 네이버 수집기, 가짜 무결성 검사, 가짜 실행기 — 각자 호출 이름을 같은 목록에 기록한다. 임시 `runs` 폴더
- When: 세 구성으로 작업을 끝까지 실행한다: (a) 두 수집기 모두 주입, (b) 네이버 수집기만 주입, (c) 둘 다 없음(생성자 기본값)
- Then: 기록 목록이 정확히 (a) `["integrity", "dart", "naver", "integrity", "runner"]`, (b) `["integrity", "naver", "integrity", "runner"]`, (c) `["integrity", "runner"]`. 네이버 수집기 인자의 출력 폴더는 `<runs>/<job_id>/naver`
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air7_001 -q`
- 기대 관측: `3 passed`(구성 a·b·c를 각 테스트로 두는 경우)
- 되돌림 검사: `_run`에서 네이버 수집 호출을 실행기 호출 뒤로 옮긴다 → (a)의 순서 단언이 `["integrity", "dart", "integrity", "runner", "naver"]`로 RED
- 추가 되돌림: 무결성 재검사 조건을 DART 수집기 주입일 때만으로 되돌린다 → (b)에서 두 번째 `integrity`가 빠져 RED
- 잡지 못하는 것: 실제 네이버 응답에서의 동작(AC-005~008 담당)

### AC-AIR7-002 — 수집 중 취소 (REQ-AIR7-002)

- Given: (1) `asyncio.Event`를 영원히 기다리는 가짜 네이버 수집기, (2) 실제 네이버 수집기 + 요청을 받으면 `asyncio.Event`를 영원히 기다리는 **비동기** `MockTransport` 처리기, 각각 가짜 실행기. 테스트 전체에 `asyncio.wait_for(..., 5)` 상한
- When: 수집 중에 `cancel(job_id)`, 별도 작업에서 `shutdown()`
- Then: 모든 경우 작업 상태 `cancelled`, 마지막 이벤트 `cancelled`, 실행기 호출 수 0, 상한 안에 끝남
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py backend/tests/test_goose_naver_prefetch.py -k air7_002 -q`
- 기대 관측: 실패 0, 각 경우 통과
- 되돌림 검사: 작업 서비스의 네이버 수집 예외 처리를 `except BaseException`으로 넓힌다 → 경우 (1)에서 실행기 호출 수 1로 RED
- 추가 되돌림: 수집기 내부에서 `CancelledError`를 잡아 `failed`로 기록하고 정상 반환하게 한다 → 경우 (2)에서 실행기 호출 수 1로 RED
- 잡지 못하는 것: 취소 시 받다 만 파일 정리(요구하지 않음 — 작업 폴더 보존 규칙에 맡김)

### AC-AIR7-003 — 끄기 스위치 (REQ-AIR7-003)

- Given: 실제 네이버 수집기(모든 요청을 기록하는 `MockTransport` 주입)와 수집기 호출 횟수를 세는 감시, 가짜 실행기
- When: `AI_REPORT_GOOSE_NAVER_PREFETCH=0`으로 실행, 같은 테스트에서 변수 미설정으로 한 번 더 실행
- Then: `0`일 때 전송 요청 수 0, 수집기 호출 수 0, `runs/<job_id>/naver/index.json`의 `outcome == "disabled"`·`articles == []`, 실행기 호출 수 1. 미설정일 때 수집기 호출 수 1, 요청 수 1
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air7_003 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 스위치 검사 줄을 지운다 → `0`인 경우 요청 수 1로 RED
- 잡지 못하는 것: 운영 서버의 환경 변수 실제 값(배포 설정 몫)

### AC-AIR7-004 — 진행 이벤트 없음 (REQ-AIR7-004)

- Given: 가짜 실행기(진행 이벤트 `goose_start` 1개 발생), 가짜 DART 수집기
- When: 같은 작업을 네이버 수집기 주입/미주입으로 한 번씩 실행하고 각 작업의 `progress` 이벤트 `stage` 목록을 뽑는다
- Then: 두 목록이 같다(예: `["dart_prefetch", "goose_start"]`). `stage`에 `naver`가 들어간 이벤트 0개
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air7_004 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 네이버 수집 전에 `progress`/`naver_prefetch` 이벤트를 보내게 한다 → 두 목록 불일치로 RED
- 잡지 못하는 것: 화면 표시 문구(프론트 무변경 — plan T6의 알려진 한계)

### AC-AIR7-005 — 요청 모양과 입력 검증 (REQ-AIR7-005)

- Given: 요청을 기록하는 `MockTransport`, 녹화 픽스처 응답. 합성 처리기: (i) 다른 호스트로 가는 `302` 응답, (ii) `content-length`가 2MB를 넘는 응답, (iii) 응답 없이 기다리는 처리기(요청 시간 상한 상수를 테스트에서 0.05초로 낮춤)
- When: 수집 실행 — 정상 코드 `020150`, 잘못된 코드 `02015a`·`０２０１５０`(전각)·`0201500`, 그리고 (i)~(iii)
- Then:
  1. 정상: 요청 수 정확히 1, 메서드 `GET`, URL이 정확히 `https://m.stock.naver.com/api/news/stock/020150?pageSize=10&page=1`
  2. 잘못된 코드 3종: 요청 수 0, `search.status == "error"`, `outcome == "failed"`
  3. (i): 요청 수 1(리디렉트 대상으로 두 번째 요청 없음), `search.error`에 `HTTP 302`
  4. (ii): `outcome == "failed"`, `search.error`에 `too large`
  5. (iii): `outcome == "failed"`, 상한 안에 반환
  6. `https://m.stock.naver.com.evil.example/…`·`http://m.stock.naver.com/…`를 주소 검사 함수에 넣으면 요청 전에 거부
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_005 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 종목코드 검사를 지운다 → 잘못된 코드 경우 요청 수 1로 RED
- 추가 되돌림: 클라이언트를 `follow_redirects=True`로 바꾼다 → (i)에서 요청 수 2로 RED(두 번째 요청은 `MockTransport`가 기록하므로 실제 연결 없음)
- 잡지 못하는 것: 네이버 쪽 호출 제한(spec G3)

### AC-AIR7-006 — 응답 해석과 기사 파일 (REQ-AIR7-006)

- Given: (1) M1 녹화 픽스처 `fixtures/naver/recorded/020150_p1.json`, (2) 합성 픽스처: `body`가 빈 기사 1건, `articleId == "../x"`인 기사 1건, `datetime == "2026102113"`(10자리)인 기사 1건, 정상 기사 1건(`datetime == "202610211352"`, `body`에 `<b>강조</b>` 포함)
- When: 수집 실행
- Then:
  1. (1): 색인 기사 수 = 픽스처 기사 목록 길이와 10 중 작은 값(테스트가 픽스처에서 추출). 각 `ok` 항목의 텍스트 파일 내용에 그 기사 픽스처의 제목과 본문 평문이 들어 있다(픽스처에서 추출해 비교)
  2. 모든 `text_file` 값이 `^[0-9]{2}_article\.txt$`에 맞고, 폴더의 파일 이름 집합이 `{"index.json", "response.json"} ∪ {ok 항목의 text_file}`과 같다
  3. (2): 빈 `body` 기사 → `status == "metadata_only"`, `text_file is None`. `../x` 기사 → `status == "error"`, 파일 없음, 폴더 밖에 파일 없음. 10자리 `datetime` 기사 → `status == "error"`. 정상 기사 → `published_at == "2026-10-21T13:52:00+09:00"`, 텍스트 파일에 `강조`는 있고 `<b>`는 없다
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_006 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 텍스트 파일 이름을 기사 제목으로 만들게 바꾼다 → 2의 정규식 단언 RED
- 추가 되돌림: 빈 본문도 `ok`로 기록하게 바꾼다 → 3의 `metadata_only` 단언 RED. `datetime`을 시간대 없이 변환하게 바꾼다 → `+09:00` 단언 RED. 마크업 제거를 지운다 → `<b>` 부재 단언 RED
- 잡지 못하는 것: `body` 필드가 기사 전문인지 요약인지(spec G4 — 규칙 9가 `read_scope`에 범위를 적게 하는 것으로 대응)

### AC-AIR7-007 — 색인 키 집합과 원본 보존 (REQ-AIR7-007)

- Given: AC-006 (1) 실행 결과
- When: `index.json`을 읽는다
- Then: 최상위·`search`·`articles[]` 키 집합이 §B와 **집합 동등**. `channel == "naver"`, `search.status == "ok"`, `search.item_count`가 픽스처 기사 목록 길이와 같음, `response_sha256 == sha256(response.json 바이트)`, `response_bytes == len(response.json 바이트)`, `response.json` 바이트 = `MockTransport`가 보낸 바이트. 시각 필드 4종이 모두 `+09:00`으로 끝난다. `article_ref == f"{office_id}/{article_id}"`
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_007 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 색인에서 `article_url` 키를 뺀다 → 집합 동등 단언 RED(부분집합 검사가 아니라 동등이므로 키 추가도 RED)
- 잡지 못하는 것: `article_url`이 실제 기사를 가리키는지(spec G5 — M1 관측)

### AC-AIR7-008 — 실패해도 진행, 0건은 0건 (REQ-AIR7-008, REQ-AIR7-009)

- Given: 처리기 변형: 연결 오류(`httpx.ConnectError`), HTTP 410, HTTP 500, JSON이 아닌 본문, 기사 목록 경로가 없는 JSON, 기사 0건 JSON. 작업 서비스 경로에는 가짜 실행기
- When: 수집기를 직접 실행, 그리고 각 변형을 주입한 작업 서비스로 작업 실행
- Then: 실패 변형 5종은 수집기가 예외 없이 반환하고 `outcome == "failed"`, `search.error`가 비어 있지 않음, 작업 서비스 경로에서 실행기 호출 수 1·작업 상태는 실행기 결과대로(`done`). 0건 변형은 `outcome == "no_results"`, `search.status == "ok"`, `search.item_count == 0`, `articles == []`
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py backend/tests/test_goose_job_service.py -k air7_008 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 수집기의 최상위 예외 처리를 지워 예외를 다시 던지게 한다 → 작업 서비스 경로는 작업 서비스 fail-open이 삼키므로 통과하고, **수집기 직접 실행 경로**에서 예외로 RED. 같은 변형에서 작업 서비스 쪽 `except Exception`까지 지우면 작업이 `error`/`exit_error`, 실행기 호출 0으로 RED
- 추가 되돌림: 기사 0건을 `failed`로 기록하게 바꾼다 → `outcome == "no_results"` 단언 RED
- 잡지 못하는 것: 네이버가 200과 함께 오래된 기사만 주는 경우(신선도 판정은 감사의 24시간 규칙과 goose 몫)

### AC-AIR7-009 — 하네스 규칙 9 문구 (REQ-AIR7-010)

- Given: M4 완료 트리
- When: 아래 문자열마다 `grep -cF '<문자열>' backend/goose_harness_src/harness-instructions.md`
- Then: 각각 1 이상: `runs/<job_id>/naver/index.json`, `article_url`, `channel: "naver"`, `metadata_only`, `"no_results"`, `서버 사전 수집본으로 열람`, `모바일 뉴스 API 응답의 제목·본문 필드`, `9-6`. 그리고 기존 규칙 8 문자열 `runs/<job_id>/dart/index.json`이 여전히 1 이상(규칙 8을 덮어쓰지 않음)
- 명령: 위 grep 9회(한 줄 루프로 실행해 문자열별 개수를 `$S/air7_009.txt`에 남긴다)
- 기대 관측: 9개 줄 모두 개수 ≥ 1
- 되돌림 검사: 규칙 9 블록을 지운다 → 앞의 8개 문자열 개수가 0으로 RED, 규칙 8 문자열만 1. (이 프로브는 문자열 부재를 볼 수 있다 — 현재 트리에서 `runs/<job_id>/naver/index.json`의 개수는 0이다: `progress.md §E.1` 사실표 P6)
- 잡지 못하는 것: 문구가 있다는 것은 goose가 따른다는 뜻이 아니다 — AC-012

### AC-AIR7-010 — 규칙 9의 기록 형태가 감사를 통과하는가 (REQ-AIR7-010)

- Given: AC-006 (1)의 색인으로 규칙 9-2·9-3이 정한 대로 만든 합성 `report-input.json` 조각(`document_type: "deep_report"`, `research_window.cutoff`는 색인 `search.searched_at`보다 10분 뒤, `sources`에는 `ok` 항목 하나를 규칙 9-2 형태로)
- When: 감사 함수(`audit_report.py`의 `audit`, 변경 없음)를 직접 불러 결함 코드 집합을 얻는다. 같은 입력에서 한 가지씩 바꾼 변형 4개도 실행: (v1) `result: "blocked"`, (v2) 출처 `verification: "server_prefetch"`, (v3) `read_scope: ""`, (v4) `searched_at`을 cutoff보다 25시간 앞으로
- Then: 원래 입력의 결함 코드에 `LATEST_SEARCH_NAVER`가 없다. (v1)~(v4) 각각의 결함 코드에 `LATEST_SEARCH_NAVER`가 있다. 색인 `outcome == "no_results"`로 만든 입력(`result: "no_results"`, `note`에 종목코드·`pageSize`·`page`)도 `LATEST_SEARCH_NAVER`가 없다
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_010 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 변형 (v1)~(v4)가 이 AC의 되돌림이다 — 규칙이 정한 기록 형태에서 한 요소를 되돌리면 감사가 RED를 낸다. 이 테스트는 감사 함수(프로덕션 코드)를 부르므로 양변이 같은 식에서 나오는 자기 비교가 아니다
- 정직한 한계: 이 AC는 "규칙대로 적으면 감사를 통과하고, 막힘을 적으면 통과하지 못한다"는 계약만 확인한다. goose가 규칙대로 적는지는 AC-012만 본다
- 잡지 못하는 것: 감사 스크립트가 바뀌는 경우(이 SPEC 범위 밖 — 매니페스트 해시가 변경을 드러낸다)

### AC-AIR7-011 — 매니페스트와 권한 파일 (REQ-AIR7-011)

- Given: M4 완료 트리
- When / Then:
  1. `PY -m backend.services.goose_harness > "$S/m.json" && diff "$S/m.json" backend/goose_harness_src/goose-manifest.json` → 출력 없음, 종료 0
  2. `shasum -a 256 backend/goose_harness_src/claude-settings.json` → `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3` (plan 작성 때 HEAD `c8e5c20`에서 잰 값 — 사실표 P1)
  3. `PY -m pytest backend/tests/test_goose_harness.py -q` → 실패 0 (매니페스트와 실제 원본 해시 비교 테스트 포함)
- 되돌림 검사: 지침만 고치고 매니페스트 재생성을 빠뜨린다 → 1에서 `CLAUDE.md` 해시 줄 차이 출력, 3에서 원본 해시 비교 테스트 RED
- 잡지 못하는 것: 서버 재시작 누락(설치는 서버 시작 때만 일어난다 — 리드가 AC-012 전에 확인)

### AC-AIR7-012 — 라이브 관측 검사 (REQ-AIR7-013, 리드 몫·이 레인 밖)

통합과 서버 재시작 뒤 리드가 실행하는 라이브 게이트다. 이 레인은 실행하지 않는다. 통과해야 SPEC을 닫는다(§F). 같은 KST 날짜에 020150으로 최대 2회 실행할 수 있고, 1·2는 두 실행 중 하나가 만족하면 되고, 3은 실행한 모든 회차에서 만족해야 한다.

- Given: 통합된 서버 재시작 완료, `shasum -a 256 ~/.goose-harness/CLAUDE.md`가 `shasum -a 256 backend/goose_harness_src/harness-instructions.md`와 같음, 기준선은 a5becbb9(`naver`가 `blocked`, `LATEST_SEARCH_NAVER` 발생 — spec §2.1)
- When: 앱에서 020150으로 goose 작업을 실행하고 끝까지 기다린다
- Then (작업과 같은 KST 날짜에 확인):
  1. `runs/<job_id>/naver/index.json`의 `outcome`이 `complete` 또는 `partial`, `request_count <= 1`
  2. `python3 -I ~/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input ~/.goose-harness/runs/<job_id>/draft/report-input.json --output "$S/audit.json"`의 결함 코드에 `LATEST_SEARCH_NAVER`가 없다
  3. 출처 대조: 초안 입력의 `research_window.searches` 중 `channel == "naver"`이고 `result == "read"`인 항목의 `source_ids`가 가리키는 출처마다 (i) `url`이 색인 `ok` 항목의 `article_url` 집합에 있거나 goose가 기존 방법으로 직접 연 다른 출처이고, (ii) 색인 출처라면 `read_scope`에 그 항목의 `text_file` 이름이 들어 있고 `limitations`에 `서버 사전 수집본으로 열람`이 들어 있다. `metadata_only`·`error` 항목의 `article_url`을 가리키는 출처 0건. 위반 0건
- 실패 시 기록: 1 실패 → 수집 결함(API 변경 의심, spec §9), 1 통과·3 위반 → 지침 미준수(사실과 다른 열람 기록), 1·3 통과·2 실패 → 남은 조건(`searched_at` 범위, `note` 공백 등)을 입력 필드와 함께 기록. 어느 경우든 SPEC은 닫지 않고 원인에 맞게 재위임한다
- 잡지 못하는 것: goose가 파일을 열었다고 적고 실제로는 일부만 읽은 경우(스트림 기록 미보존 — Gap)

### AC-AIR7-013 — 테스트 밀폐와 기존 goose 회귀 (REQ-AIR7-012)

- Given: 변경 완료 트리
- When:
  1. `before=$(ls ~/.goose-harness/runs | wc -l; stat -f %m ~/.goose-harness/runs)`
  2. `PATH=/usr/bin:/bin PY -m pytest backend/tests/test_goose_naver_prefetch.py backend/tests/test_goose_dart_prefetch.py backend/tests/test_goose_job_service.py backend/tests/test_goose_router.py backend/tests/test_goose_storage.py backend/tests/test_goose_runner.py backend/tests/test_goose_harness.py backend/tests/test_main_goose_lifespan.py -q`
  3. `after=…`(1과 같은 명령)
- Then: 2의 실패 0, 종료 단언(`network attempt in goose test`) 0건, 통과 개수는 run 단계 M2 착수 전에 같은 명령(새 파일 제외)으로 잰 기준선 + 새 테스트 수 이상, `before == after`
- 되돌림 검사: 수집기 테스트 하나에서 `MockTransport` 주입을 뺀다 → 수집기가 실패를 `failed`로 적고 정상 반환해도 그 테스트가 `ERROR at teardown` + `network attempt in goose test: [...m.stock.naver.com...]`로 RED(가드는 원래 함수를 부르지 않으므로 실제 연결 없음). 선행 조건: 되돌림 전에 `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_014_guard -q`로 가드 자체 검사가 통과하는지 먼저 확인한다
- 추가 되돌림: `GooseJobService` 생성자의 네이버 수집기 기본값을 실제 수집기로 바꾼다 → 수집기 없이 서비스를 만드는 기존 테스트가 `ERROR at teardown` + `network attempt in goose test`로 RED
- 잡지 못하는 것: goose와 무관한 백엔드 테스트의 네트워크 사용(가드 범위 밖)

## §D 경계 사례

| 사례 | 기대 동작 | 담당 AC |
|---|---|---|
| 기사 0건 | `no_results`, goose는 조건을 적고 `no_results` | AC-008, AC-010 |
| 본문 없는 기사만 있음 | 전부 `metadata_only`, `outcome == "failed"`, goose는 기존 방법으로 시도 | AC-006, §B 판정 |
| 네이버 API 장애·구조 변경 | `failed` 후 goose 진행, 감사 결함은 다시 보임 | AC-008 |
| 다른 호스트로 리디렉트 | 따라가지 않음, `failed` | AC-005 |
| 끄기 스위치 | 요청 0, `disabled` | AC-003 |
| 서버 종료 중 수집 | `cancelled`, 실행기 미호출 | AC-002 |
| 기사 본문에 지시문 포함 | goose는 5번 규칙대로 자료로만 취급(규칙 9-4) | AC-009 문구, 라이브 비게이팅 |

## §E 품질 게이트

- 새 수집 모듈 줄 커버리지 85% 이상. 측정: `coverage run --source=backend -m pytest backend/tests/test_goose_naver_prefetch.py` → `coverage report --include='backend/services/goose_naver_prefetch.py'`(lessons #9의 커버리지 측정 함정)
- `ruff check` 새 경고 0(기준선 대비)
- 되돌림 검사는 RED 관측 후에만 GREEN으로 기록(§A)
- @MX: 수집 모듈의 외부 시스템 진입점에 `@MX:WARN`(네트워크·시간 상한·호스트 검사), 공개 진입점에 `@MX:ANCHOR`(호출 계약), 주석 언어는 `code_comments: ko`

## §F 완료 정의

- run 레인: AC-AIR7-001~011, 013 통과(명령·출력·기준선·되돌림 RED 원문을 `progress.md §E.2`에)
- `claude-settings.json`·감사 스크립트·`goose_dart_prefetch.py`·프론트 무변경
- 리드: 통합·서버 재시작 뒤 AC-AIR7-012 통과(라이브 관측 게이트 — 실패 기록만으로는 닫지 않는다)
- 이 SPEC 이후에도 goose 결과가 `draft`임을 sync 문서에 명시
