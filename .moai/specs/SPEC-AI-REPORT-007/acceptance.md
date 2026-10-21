# SPEC-AI-REPORT-007 — 인수 기준

버전 0.2.0 · 요구사항은 `spec.md §5`(REQ-AIR7-001~014). 각 AC는 Given-When-Then, 실행 명령, 기대 관측 출력, **되돌림 검사**(이 한 가지 변경을 되돌리면 검사가 RED가 된다)와 **잡지 못하는 것**을 적는다. 되돌림 검사는 run 단계에서 실제로 적용해 RED 출력을 원문으로 남겨야 GREEN으로 기록할 수 있다(lessons #9). 관측하지 못한 되돌림은 `progress.md §E.2`에 Gap으로 남긴다.

## §A 공통 실행 조건

- Python 명령은 가상환경을 활성화한 뒤 실행한다. 서버용 가상환경은 코드 폴더와 다른 경로(`/Users/byunjungwon/Dev/my_chart/.venv`)에 있다. 아래 `PY`는 그 환경의 `python`이다.
- 테스트 함수 이름에 AC 꼬리표(`air7_001` 등)를 넣어 `-k`로 고른다.
- 모든 새 테스트는 파일 이름이 `test_goose_`로 시작하는 모듈에 둔다. 그래야 `backend/tests/conftest.py`의 네트워크 가드(시도 기록 + 종료 시 0건 단언)가 적용된다(SPEC-TEST-HERMETIC-001, SPEC-AI-REPORT-005 AC-014). 테스트에 실제 네트워크는 없다 — 요청은 `httpx.MockTransport`가 답한다.
- `httpx.MockTransport`는 `httpx.Timeout`을 적용하지 않는다(httpx 0.28.1, `progress.md` 사실표 P12). 그래서 요청이 끝나지 않을 수 있는 테스트는 모두 바깥 `asyncio.wait_for(…, 2)`(취소 테스트는 5) 상한 안에서 돌린다 — 구현이 틀려도 테스트는 멈추지 않고 `TimeoutError`로 RED가 된다.
- 기대값 중 기사 수·제목·본문은 손으로 옮겨 적지 않고 녹화 픽스처에서 테스트 실행 중에 추출한다(lessons #10). 여기 적힌 리터럴은 형식 규칙과 합성 픽스처 값뿐이다.
- 이 문서의 코드 블록(AC-011 #4, AC-012 검사 3)은 손으로 옮기지 않고 블록 내용을 그대로 추출해 `$S/`에 저장한 뒤 `python3 -I`로 실행한다.
- `$S`는 세션 증거 폴더 `.moai/state/verify/<session>/`다.
- 되돌림 관측 절차: 변형 적용(임시 소스 편집 또는 monkeypatch) → 해당 명령 실행 → 실패 출력 원문 캡처 → 복원 → `git status --short`로 복원 확인.

## §B index.json 고정 키 집합 (AC-AIR7-007이 집합 동등으로 검사)

- 최상위: `schema_version`, `code`, `channel`, `search`, `outcome`, `started_at`, `finished_at`, `request_count`, `response_file`, `response_sha256`, `response_bytes`, `articles`
- `channel` 값: `"naver"`
- `search`: `url`, `query`, `searched_at`, `status`, `item_count`, `error`
- `articles[]` 항목: `article_ref`, `office_id`, `article_id`, `office_name`, `title`, `published_at`, `article_url`, `text_file`, `body_chars`, `status`, `error`
- `outcome` 값: `complete` | `partial` | `no_results` | `failed` | `disabled` — 판정 규칙은 REQ-AIR7-014(AC-AIR7-014가 검사):

  | 조건 (위에서부터 처음 맞는 것) | `outcome` |
  |---|---|
  | 작업 서비스가 끄기 스위치로 쓴 색인 | `disabled` |
  | 요청·응답 처리 실패(REQ-AIR7-008) | `failed` |
  | 응답은 정상이고 기사 0건 | `no_results` |
  | 모든 기사 항목이 `ok` | `complete` |
  | `ok`가 1개 이상이고 `metadata_only`·`error`가 1개 이상 | `partial` |
  | 기사는 있으나 `ok`가 0개 | `failed` |

- `articles[].status` 값: `ok` | `metadata_only` | `error`
- 시각 필드(`search.searched_at`, `started_at`, `finished_at`, `articles[].published_at`): 시간대 포함 ISO-8601, 오프셋 `+09:00`
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
- SPEC-AI-REPORT-006과 병합한 뒤 다시 실행한다(plan.md §5 필수 단계 4). 006의 후처리는 실행기 뒤에 붙으므로, 006이 기록 이름을 더하면 기대 목록의 `runner` 뒤에만 덧붙인다
- 잡지 못하는 것: 실제 네이버 응답에서의 동작(AC-005~008, 014 담당)

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
- SPEC-AI-REPORT-006과 병합한 뒤 다시 실행한다(plan.md §5 필수 단계 4)
- 잡지 못하는 것: 화면 표시 문구(프론트 무변경 — plan T6의 알려진 한계)

### AC-AIR7-005 — 요청 모양, 입력 검증, 크기·시간 상한 (REQ-AIR7-005)

- Given: 요청을 기록하는 `MockTransport`, 녹화 픽스처 응답. 합성 처리기: (i) 다른 호스트로 가는 `302` 응답, (ii) 본문이 2MB + 1바이트인 응답 두 가지 — `content-length`를 선언한 것과 선언하지 않고 조각으로 흘려보내는 것, (iii) 응답하지 않고 `asyncio.Event`를 영원히 기다리는 비동기 처리기(요청 시간 상한 모듈 상수를 테스트에서 0.05초로 낮춤)
- When: 수집 실행 — 정상 코드 `020150`, 잘못된 코드 `02015a`·`０２０１５０`(전각)·`0201500`, 그리고 (i)~(iii). (iii)은 테스트 안에서 `asyncio.wait_for(prefetcher(...), 2)`로 감싼다
- Then:
  1. 정상: 요청 수 정확히 1, 메서드 `GET`, URL이 정확히 `https://m.stock.naver.com/api/news/stock/020150?pageSize=10&page=1`
  2. 잘못된 코드 3종: 요청 수 0, `search.status == "error"`, `outcome == "failed"`
  3. (i): 요청 수 1(리디렉트 대상으로 두 번째 요청 없음), `search.error`에 `HTTP 302`
  4. (ii) 두 가지 모두: `outcome == "failed"`, `search.error`에 `too large`
  5. (iii): 바깥 2초 상한에 걸리지 않고 반환, `outcome == "failed"`, `search.error`에 `Timeout`
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_005 -q`
- 기대 관측: 실패 0
- 되돌림 검사(입력 검증): 종목코드 검사를 지운다 → 잘못된 코드 경우 요청 수 1로 RED
- 되돌림 검사(리디렉트): 클라이언트를 `follow_redirects=True`로 바꾼다 → (i)에서 요청 수 2로 RED(두 번째 요청은 `MockTransport`가 기록하므로 실제 연결 없음)
- 되돌림 검사(크기): 선언 길이 검사와 스트리밍 누적 검사를 함께 지운다 → (ii)에서 `outcome != "failed"`로 RED. 하나만 지우면 그 하나에 해당하는 경우만 RED가 된다(두 경우를 따로 둔 이유)
- 되돌림 검사(시간): 전송 코루틴을 감싼 `asyncio.wait_for`를 지우고 httpx 시간 상한만 남긴다 → (iii)이 바깥 2초 상한에 걸려 `TimeoutError`로 RED(`MockTransport`가 httpx 시간 상한을 적용하지 않으므로)
- 범위 메모: 호스트 검사 함수에 손으로 만든 주소를 넣는 단위 검사는 두지 않는다. 요청 주소는 모듈 상수로 만들어지므로 그런 검사는 상수를 상수와 비교하는 자기 비교에 가깝다(lessons #9 형태 2). 다른 호스트로 실제 요청이 나가지 않는다는 성질은 (i)의 리디렉트 경우가 요청 경로를 통해 확인한다
- 잡지 못하는 것: 네이버 쪽 호출 제한(spec G3), 운영 전송 계층에서의 httpx 시간 상한 거동(바깥 `wait_for`가 상한을 보장하므로 판정에 쓰지 않음)

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
- 잡지 못하는 것: `body` 필드가 기사 전문인지 요약인지(spec G4 — 규칙이 `read_scope`에 범위를 적게 하는 것으로 대응). `outcome` 값은 AC-014가 검사한다

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

### AC-AIR7-009 — 하네스 네이버 규칙 문구 (REQ-AIR7-010)

- Given: M4 완료 트리
- When: 아래 문자열마다 `grep -cF '<문자열>' backend/goose_harness_src/harness-instructions.md`(한 줄 루프로 실행해 `개수<TAB>문자열`을 `$S/air7_009.txt`에 남긴다)
- 검사 문자열(모두 규칙 번호와 무관 — 006과의 병합으로 번호가 9에서 10으로 바뀌어도 그대로 쓴다):

  | 문자열 | plan 단계 기준선(HEAD `5b7a22b`, 사실표 P6) | M4 뒤 기대 |
  |---|---|---|
  | `runs/<job_id>/naver/index.json` | 0 | ≥ 1 |
  | `article_url` | 0 | ≥ 1 |
  | `channel: "naver"` | 0 | ≥ 1 |
  | `metadata_only` | 0 | ≥ 1 |
  | `"no_results"` | 0 | ≥ 1 |
  | `모바일 뉴스 API 응답의 제목·본문 필드` | 0 | ≥ 1 |
  | `서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음` | 0 | ≥ 1 |
  | `이번 세션에서 그 파일을 연 시각` (`accessed_at` 규정 — `accessed_at` 자체는 규칙 8-2에 이미 1회 있어 쓰지 않는다) | 0 | ≥ 1 |
  | `original_news` | 0 | ≥ 1 |
  | `runs/<job_id>/dart/index.json` (규칙 8 보존 확인) | 2 | 2 |

- Then: 표의 "M4 뒤 기대"를 모두 만족
- 되돌림 검사: 네이버 규칙 블록을 지운다 → 위 9개 문자열의 개수가 모두 0으로 RED, 규칙 8 문자열만 2. (규칙 8에도 있는 짧은 표기 `서버 사전 수집본으로 열람`과 `accessed_at`은 기준선이 이미 1이라 지워도 0이 되지 않으므로 검사 문자열로 쓰지 않는다 — 대신 네이버 규칙에만 있는 표기를 쓴다. 기준선 전체는 사실표 P6)
- 잡지 못하는 것: 문구가 있다는 것은 goose가 따른다는 뜻이 아니다 — AC-012

### AC-AIR7-010 — 규칙의 기록 형태가 감사를 통과하는가 (REQ-AIR7-010)

- Given: AC-006 (1)의 색인으로 네이버 규칙 N-2·N-3이 정한 대로 만든 합성 `report-input.json` 조각(`document_type: "deep_report"`, `research_window.cutoff`는 색인 `search.searched_at`보다 10분 뒤, `sources`에는 `ok` 항목 하나를 N-2 형태로)
- When: 감사 함수(`audit_report.py`의 `audit`, 변경 없음)를 직접 불러 결함 코드 집합을 얻는다. 같은 입력에서 한 가지씩 바꾼 변형 4개도 실행: (v1) `result: "blocked"`, (v2) 출처 `verification: "server_prefetch"`, (v3) `read_scope: ""`, (v4) `searched_at`을 cutoff보다 25시간 앞으로
- Then: 원래 입력의 결함 코드에 `LATEST_SEARCH_NAVER`가 없다. (v1)~(v4) 각각의 결함 코드에 `LATEST_SEARCH_NAVER`가 있다. 색인 `outcome == "no_results"`로 만든 입력(`result: "no_results"`, `note`에 종목코드·`pageSize`·`page`)도 `LATEST_SEARCH_NAVER`가 없다
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_010 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 변형 (v1)~(v4)가 이 AC의 되돌림이다 — 규칙이 정한 기록 형태에서 한 요소를 되돌리면 감사가 RED를 낸다. 이 테스트는 감사 함수(프로덕션 코드)를 부르므로 양변이 같은 식에서 나오는 자기 비교가 아니다
- 정직한 한계: 이 AC는 "규칙대로 적으면 감사를 통과하고, 막힘을 적으면 통과하지 못한다"는 계약만 확인한다. 감사는 `no_results`를 조건 없이 받으므로(spec §2.4) 지어낸 `no_results`는 여기서 잡히지 않는다 — AC-012 검사 3이 잡는다. goose가 규칙대로 적는지는 AC-012만 본다
- 잡지 못하는 것: 감사 스크립트가 바뀌는 경우(이 SPEC 범위 밖 — 매니페스트 해시가 변경을 드러낸다)

### AC-AIR7-011 — 매니페스트, 권한 파일, 규칙 번호 (REQ-AIR7-011)

- Given: M4 완료 트리, 그리고 SPEC-AI-REPORT-006과 병합한 트리(plan.md §5 필수 단계 1·3)
- When / Then:
  1. `PY -m backend.services.goose_harness > "$S/m.json" && diff "$S/m.json" backend/goose_harness_src/goose-manifest.json` → 출력 없음, 종료 0
  2. `shasum -a 256 backend/goose_harness_src/claude-settings.json` → `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3` (사실표 P1)
  3. `PY -m pytest backend/tests/test_goose_harness.py -q` → 실패 0 (매니페스트와 실제 원본 해시 비교 테스트 포함)
  4. 아래 블록을 `$S/rulenum.py`로 추출해 `python3 -I "$S/rulenum.py" backend/goose_harness_src/harness-instructions.md` → 마지막 줄이 정확히 `rule numbering ok`

```python
# AC-AIR7-011 #4 — harness-instructions.md 규칙 번호 검사
import re, sys
cur = None; tops = []; errs = []
for n, line in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
    m = re.match(r"^(\d+)\. ", line)
    if m:
        cur = int(m.group(1)); tops.append(cur); continue
    s = re.match(r"^\s+- (\d+)-\d+[a-z]?\. ", line)
    if s and int(s.group(1)) != cur:
        errs.append("line %d: sub-item %s-* under rule %s" % (n, s.group(1), cur))
if tops != list(range(1, len(tops) + 1)):
    errs.append("top-level numbers not 1..K unique: %s" % tops)
print("rules", tops)
print("rule numbering ok" if not errs else "\n".join(errs))
```

- 기대 관측(#4): plan 단계 현재 트리에서 `rules [1, 2, 3, 4, 5, 6, 7, 8]` / `rule numbering ok`(사실표 P13). M4 뒤 `rules [1, …, 9]`, 006 병합 뒤 `rules [1, …, 10]`, 마지막 줄은 항상 `rule numbering ok`
- 되돌림 검사(#1·#3): 지침만 고치고 매니페스트 재생성을 빠뜨린다 → #1에서 `CLAUDE.md` 해시 줄 차이 출력, #3에서 원본 해시 비교 테스트 RED
- 되돌림 검사(#4): 006 병합 트리에서 나중 쪽 규칙 번호를 9로 둔다 → `top-level numbers not 1..K unique: [1, …, 9, 9]`로 RED. 상위 번호만 10으로 바꾸고 하위 라벨을 `9-6`으로 남긴다 → `line <n>: sub-item 9-* under rule 10`으로 RED(두 경우 모두 plan 단계에서 같은 판정 로직으로 관측 — 사실표 P13)
- 잡지 못하는 것: 서버 재시작 누락(설치는 서버 시작 때만 일어난다 — 리드가 AC-012 전에 확인)

### AC-AIR7-012 — 라이브 관측 검사 (REQ-AIR7-013, 리드 몫·이 레인 밖)

통합과 서버 재시작 뒤 리드가 실행하는 라이브 게이트다. 이 레인은 실행하지 않는다. 통과해야 SPEC을 닫는다(§F). 같은 KST 날짜에 020150으로 최대 2회 실행할 수 있다. **검사 1·2·3은 같은 한 회차에서 모두 만족해야 하고**, 검사 3은 그날 실행한 다른 회차에서도 만족해야 한다(회차 A의 수집 성공과 회차 B의 감사 통과를 합쳐 통과로 보지 않는다).

출처 규칙(REQ-AIR7-013과 같은 규칙, spec D7): `naver` 채널의 `result == "read"` 항목이 인용한 출처는 **모두** 색인 `ok` 항목이어야 한다. goose가 다른 경로로 연 출처는 `naver` 채널에 허용하지 않는다(그런 기사는 `original_news` 채널에 적는다 — 규칙 N-3). 이유: 게이트의 목적은 사전 수집이 통과를 만들었음을 보이는 것이고, 다른 출처를 허용하면 수집이 실패하고 대체 경로로 통과한 경우와 구분할 수 없다.

- Given: 통합된 서버 재시작 완료, `shasum -a 256 ~/.goose-harness/CLAUDE.md`가 `shasum -a 256 backend/goose_harness_src/harness-instructions.md`와 같음, 기준선은 a5becbb9(`naver`가 `blocked`, `LATEST_SEARCH_NAVER` 발생 — spec §2.1)
- When: 앱에서 020150으로 goose 작업을 실행하고 끝까지 기다린다. `IDX=~/.goose-harness/runs/<job_id>/naver/index.json`, `INP=~/.goose-harness/runs/<job_id>/draft/report-input.json`
- Then (작업과 같은 KST 날짜에, 같은 `<job_id>`로 확인):
  1. `$IDX`의 `outcome`이 `complete` 또는 `partial`, `request_count <= 1`
  2. `python3 -I ~/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input "$INP" --output "$S/audit.json"`의 결함 코드에 `LATEST_SEARCH_NAVER`가 없다
  3. 아래 블록을 `$S/air7_check3.py`로 추출해 `python3 -I "$S/air7_check3.py" "$IDX" "$INP"` → 첫 줄이 정확히 `violations 0`. 이 검사는 (a) `naver`의 `read` 항목이 1건 이상, (b) 색인 `outcome`이 `complete`·`partial`인데 `naver`의 `no_results` 항목이 있으면 위반(검사 1이 그 두 값을 요구하므로 통과 회차에서는 `no_results` 0건), (c) `read` 항목의 출처마다 `url`이 색인 `ok` 항목의 `article_url`이고 `read_scope`에 그 항목의 `text_file`, `limitations`에 `서버 사전 수집본으로 열람`이 있어야 함을 본다

```python
# AC-AIR7-012 검사 3 — naver 기록과 서버 색인 대조
import json, sys
idx = json.load(open(sys.argv[1], encoding="utf-8"))
d = json.load(open(sys.argv[2], encoding="utf-8"))
ok = {a["article_url"]: a for a in idx["articles"] if a["status"] == "ok"}
src = {s.get("id"): s for s in d.get("sources", [])}
nav = [s for s in d["research_window"]["searches"] if s.get("channel") == "naver"]
v = []
if idx["outcome"] in ("complete", "partial"):
    v += ["naver no_results while index outcome=" + idx["outcome"] for s in nav if s.get("result") == "no_results"]
reads = [s for s in nav if s.get("result") == "read"]
if not reads:
    v.append("no naver read entry")
for s in reads:
    for i in s.get("source_ids", []):
        x = src.get(i, {})
        a = ok.get(x.get("url"))
        if a is None:
            v.append(i + ": url is not an ok index article_url")
        elif a["text_file"] not in str(x.get("read_scope", "")) or "서버 사전 수집본으로 열람" not in str(x.get("limitations", "")):
            v.append(i + ": read_scope/limitations mismatch")
print("violations", len(v))
for line in v:
    print(" ", line)
```

- 되돌림 검사(검사 3, 리드가 게이트 실행 때 함께 관측): `$INP`의 사본에서 `naver` 항목의 `result`를 `no_results`로 바꿔 검사 3을 돌린다 → `violations 2`(`naver no_results while index outcome=…`, `no naver read entry`)로 RED. 사본에서 출처 `url`을 `metadata_only` 항목의 `article_url`이나 색인 밖 주소로 바꾼다 → `<id>: url is not an ok index article_url`로 RED. 같은 판정 로직은 plan 단계에서 합성 입력으로 관측했다(사실표 P14) — 통과 입력 `violations 0`, 위 세 변형 각각 RED
- 실패 시 기록: 1 실패 → 수집 결함(API 변경 의심, spec §9), 1 통과·3 위반 → 지침 미준수(지어낸 `no_results`나 사실과 다른 열람 기록), 1·3 통과·2 실패 → 남은 조건(`searched_at` 범위, `note` 공백 등)을 입력 필드와 함께 기록. 어느 경우든 SPEC은 닫지 않고 원인에 맞게 재위임한다
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

### AC-AIR7-014 — `outcome` 판정 (REQ-AIR7-014)

- Given: 합성 픽스처 4종: (a) 정상 기사 2건 + `body` 빈 기사 1건 + `articleId == "../x"` 기사 1건(혼합), (b) `body` 빈 기사 3건(전부 `metadata_only`), (c) 정상 기사 3건(전부 `ok`), (d) 정상 기사 1건 + 10자리 `datetime` 기사 1건(`ok` + `error`)
- When: 각 픽스처로 수집 실행
- Then: `outcome`이 정확히 (a) `"partial"`, (b) `"failed"`, (c) `"complete"`, (d) `"partial"`. 각 경우 `search.status == "ok"`, `search.item_count`가 픽스처 기사 수와 같음. (0건 → `no_results`와 요청 실패 → `failed`는 AC-008이 검사한다)
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_014 -q`
- 기대 관측: `4 passed`(경우마다 테스트 하나)
- 되돌림 검사: "기사는 있으나 `ok` 0개"를 `complete`로 판정하게 바꾼다(예: `all(s == "ok" …)` 대신 `not any(s == "error" …)`) → (b)에서 `"complete" != "failed"`로 RED
- 추가 되돌림: 혼합을 `complete`로 판정하게 바꾼다(`ok`가 하나라도 있으면 `complete`) → (a)·(d)에서 RED. `metadata_only`를 판정에서 빼고 `error`만 센다 → (b)가 `"complete"`가 되어 RED
- 왜 필요한가: AC-012 검사 1과 규칙 N-5가 이 값에 기대므로, 판정이 틀리면 수집 실패가 게이트 통과처럼 보이거나 goose가 대체 경로를 건너뛴다
- 잡지 못하는 것: 라이브 응답의 기사 구성(라이브 회차의 색인으로만 관측)

## §D 경계 사례

| 사례 | 기대 동작 | 담당 AC |
|---|---|---|
| 기사 0건 | `no_results`, goose는 조건을 적고 `no_results` | AC-008, AC-010 |
| 본문 없는 기사만 있음 | 전부 `metadata_only`, `outcome == "failed"`, goose는 기존 방법으로 시도 | AC-014 (b) |
| `ok`와 `metadata_only`·`error` 혼합 | `outcome == "partial"`, goose는 `ok` 파일만 인용 | AC-014 (a)·(d) |
| 색인에 `ok`가 있는데 goose가 `no_results`를 씀 | 감사는 통과시키지만 라이브 게이트 검사 3이 위반으로 잡음 | AC-012 |
| 네이버 API 장애·구조 변경 | `failed` 후 goose 진행, 감사 결함은 다시 보임 | AC-008 |
| 다른 호스트로 리디렉트 | 따라가지 않음, `failed` | AC-005 |
| 응답이 오지 않음 | 10초(테스트에서는 낮춘 상수) 뒤 `failed` | AC-005 (iii) |
| 끄기 스위치 | 요청 0, `disabled` | AC-003 |
| 서버 종료 중 수집 | `cancelled`, 실행기 미호출 | AC-002 |
| 기사 본문에 지시문 포함 | goose는 5번 규칙대로 자료로만 취급(규칙 N-4) | AC-009 문구, 라이브 비게이팅 |
| 006과 병합 | 나중 쪽 규칙이 10번, 하위 라벨 일치, 매니페스트 재생성 | AC-011 #1·#3·#4, AC-001·004 재실행 |

## §E 품질 게이트

- 새 수집 모듈 줄 커버리지 85% 이상. 측정: `coverage run --source=backend -m pytest backend/tests/test_goose_naver_prefetch.py` → `coverage report --include='backend/services/goose_naver_prefetch.py'`(lessons #9의 커버리지 측정 함정)
- `ruff check` 새 경고 0(기준선 대비)
- 되돌림 검사는 RED 관측 후에만 GREEN으로 기록(§A)
- @MX: 수집 모듈의 외부 시스템 진입점에 `@MX:WARN`(네트워크·시간 상한·호스트 검사), 공개 진입점에 `@MX:ANCHOR`(호출 계약), 주석 언어는 `code_comments: ko`

## §F 완료 정의

- run 레인: AC-AIR7-001~011, 013, 014 통과(명령·출력·기준선·되돌림 RED 원문을 `progress.md §E.2`에)
- `claude-settings.json`·감사 스크립트·`goose_dart_prefetch.py`·프론트 무변경
- 006과 병합하는 쪽: plan.md §5 필수 병합 단계 1~4의 관측 결과를 기록
- 리드: 통합·서버 재시작 뒤 AC-AIR7-012 통과(라이브 관측 게이트 — 실패 기록만으로는 닫지 않는다)
- 이 SPEC 이후에도 goose 결과가 `draft`임을 sync 문서에 명시
