# SPEC-AI-REPORT-007 — 인수 기준

버전 0.4.0 · 요구사항은 `spec.md §5`(REQ-AIR7-001~015). 각 AC는 Given-When-Then, 실행 명령, 기대 관측 출력, **되돌림 검사**(이 한 가지 변경을 되돌리면 검사가 RED가 된다)와 **잡지 못하는 것**을 적는다. 되돌림 검사는 run 단계에서 실제로 적용해 RED 출력을 원문으로 남겨야 GREEN으로 기록할 수 있다(lessons #9). 관측하지 못한 되돌림은 `progress.md §E.2`에 Gap으로 남긴다.

변경 이력: 0.1.0~0.3.0은 `spec.md` HISTORY와 같다. 0.4.0(2026-10-21) — run 단계 M1 관측 반영: §B에 `code_validated`·펼친 길이 `item_count`·모양 오류 항목·판정표 갱신(V1·V4), AC-006에 그룹 펼침·모양 오류·엔티티 해제·순서 단언과 되돌림(V1·V3), AC-007에 `total` 되돌림과 `mobileNewsUrl` 교차 확인(V1·V5), AC-008에 최상위 객체·녹화 0건 응답(V1), AC-009에 요약본·종목코드 문구 5개(V2·V4), AC-012 검사 3의 성공 형태에 요약본 문구(V2), AC-014 픽스처를 실제 파일로 맞추고 모양 오류 경우 추가, AC-015 신설(V4).

## §A 공통 실행 조건

- Python 명령은 가상환경을 활성화한 뒤 실행한다. 서버용 가상환경은 코드 폴더와 다른 경로(`/Users/byunjungwon/Dev/my_chart/.venv`)에 있다. 아래 `PY`는 그 환경의 `python`이다.
- 테스트 함수 이름에 AC 꼬리표(`air7_001` 등)를 넣어 `-k`로 고른다.
- 모든 새 테스트는 파일 이름이 `test_goose_`로 시작하는 모듈에 둔다. 그래야 `backend/tests/conftest.py`의 네트워크 가드(시도 기록 + 종료 시 0건 단언)가 적용된다(SPEC-TEST-HERMETIC-001, SPEC-AI-REPORT-005 AC-014). 테스트에 실제 네트워크는 없다 — 요청은 `httpx.MockTransport`가 답한다.
- `httpx.MockTransport`는 `httpx.Timeout`을 적용하지 않는다(httpx 0.28.1, `progress.md` 사실표 P12). 그래서 요청이 끝나지 않을 수 있는 테스트는 모두 바깥 `asyncio.wait_for(…, 2)`(취소 테스트는 5) 상한 안에서 돌린다 — 구현이 틀려도 테스트는 멈추지 않고 `TimeoutError`로 RED가 된다.
- 기대값 중 기사 수·제목·본문은 손으로 옮겨 적지 않고 녹화 픽스처에서 테스트 실행 중에 추출한다(lessons #10). 기사 수는 **펼친 목록 길이** `len([it for g in data for it in g["items"]])`이며 그룹의 `total`을 쓰지 않는다(spec §2.6). 평문 기대값은 `html.unescape(<태그 제거한 원문>).strip()`으로 테스트가 만든다. 여기 적힌 리터럴은 형식 규칙과 합성 픽스처 값뿐이다.
- 녹화 픽스처는 `backend/tests/fixtures/naver/recorded/`(020150·000040·999999, `progress.md §E.2`), 합성 픽스처는 `backend/tests/fixtures/naver/synthetic/`(M1이 만든 10종 + M2가 더하는 5종, plan.md §3 M2)다.
- 이 문서의 코드 블록(AC-011 #4, AC-012 검사 3)은 손으로 옮기지 않고 블록 내용을 그대로 추출해 `$S/`에 저장한 뒤 `python3 -I`로 실행한다.
- `$S`는 세션 증거 폴더 `.moai/state/verify/<session>/`다.
- 되돌림 관측 절차: 변형 적용(임시 소스 편집 또는 monkeypatch) → 해당 명령 실행 → 실패 출력 원문 캡처 → 복원 → `git status --short`로 복원 확인.

## §B index.json 고정 키 집합 (AC-AIR7-007이 집합 동등으로 검사)

- 최상위: `schema_version`, `code`, `code_validated`, `channel`, `search`, `outcome`, `started_at`, `finished_at`, `request_count`, `response_file`, `response_sha256`, `response_bytes`, `articles`
- `channel` 값: `"naver"`. `code_validated` 값: `true` | `false`(REQ-AIR7-015)
- `search`: `url`, `query`, `searched_at`, `status`, `item_count`, `error`. `item_count`는 10건 상한을 적용하기 전 펼친 기사 목록의 길이다(그룹 `total` 아님)
- `articles[]` 항목: `article_ref`, `office_id`, `article_id`, `office_name`, `title`, `published_at`, `article_url`, `text_file`, `body_chars`, `status`, `error`. 모양이 깨진 그룹·객체가 아닌 기사의 항목은 기사 필드가 `null`이고 `status == "error"`, `error`에 그룹 번호와 사유(`items missing`, `items not a list`, `group not an object`, `article not an object`)
- `outcome` 값: `complete` | `partial` | `no_results` | `failed` | `disabled` — 판정 규칙은 REQ-AIR7-014(AC-AIR7-014가 검사):

  | 조건 (위에서부터 처음 맞는 것) | `outcome` |
  |---|---|
  | 작업 서비스가 끄기 스위치로 쓴 색인 | `disabled` |
  | 요청·응답 처리 실패(REQ-AIR7-008 — 최상위가 배열 아님, 비어 있지 않은 배열인데 `items` 배열을 가진 그룹이 없음 포함) | `failed` |
  | 펼친 기사 0건이고 모양이 깨진 그룹도 없음(빈 배열 `[]` 포함) | `no_results` |
  | 모든 항목이 `ok` | `complete` |
  | `ok`가 1개 이상이고 `metadata_only`·`error`(모양 오류 항목 포함)가 1개 이상 | `partial` |
  | 항목은 있으나 `ok`가 0개 | `failed` |

- `articles[].status` 값: `ok` | `metadata_only` | `error`
- 시각 필드(`search.searched_at`, `started_at`, `finished_at`, `articles[].published_at`): 시간대 포함 ISO-8601, 오프셋 `+09:00`
- 응답 경로와 키 이름은 run 단계 M1 관측(`progress.md §E.2` O1~O7)으로 확정했다(v0.4.0). 이후 응답이 바뀌면 코드보다 먼저 이 절을 manager-spec 재위임으로 고친다.

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

- Given: 요청을 기록하는 `MockTransport`, 녹화 픽스처 응답. 합성 처리기: (i) 다른 호스트로 가는 `302` 응답, (ii) 2MB를 넘는 응답 두 가지 — (ii-a) `content-length: 2097153`을 선언하고 본문은 읽힌 조각 수를 세는 `httpx.AsyncByteStream`으로 주는 것, (ii-b) `content-length` 없이 2MB + 1바이트를 조각으로 흘려보내는 것, (iii) 응답하지 않고 `asyncio.Event`를 영원히 기다리는 비동기 처리기(요청 시간 상한 모듈 상수를 테스트에서 0.05초로 낮춤)
- When: 수집 실행 — 정상 코드 `020150`, 잘못된 코드 `02015a`·`０２０１５０`(전각)·`0201500`, 그리고 (i)~(iii). (iii)은 테스트 안에서 `asyncio.wait_for(prefetcher(...), 2)`로 감싼다
- Then:
  1. 정상: 요청 수 정확히 1, 메서드 `GET`, URL이 정확히 `https://m.stock.naver.com/api/news/stock/020150?pageSize=10&page=1`
  2. 잘못된 코드 3종: 요청 수 0, `search.status == "error"`, `outcome == "failed"`
  3. (i): 요청 수 1(리디렉트 대상으로 두 번째 요청 없음), `search.error`에 `HTTP 302`
  4. (ii-a): `outcome == "failed"`, `search.error`에 `too large`, **본문 조각 읽힘 수 == 0**(선언 길이만 보고 본문을 읽기 전에 거부). (ii-b): `outcome == "failed"`, `search.error`에 `too large`
  5. (iii): 바깥 2초 상한에 걸리지 않고 반환, `outcome == "failed"`, `search.error`에 `Timeout`
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_005 -q`
- 기대 관측: 실패 0
- 되돌림 검사(입력 검증): 종목코드 검사를 지운다 → 잘못된 코드 경우 요청 수 1로 RED
- 되돌림 검사(리디렉트): 클라이언트를 `follow_redirects=True`로 바꾼다 → (i)에서 요청 수 2로 RED(두 번째 요청은 `MockTransport`가 기록하므로 실제 연결 없음)
- 되돌림 검사(선언 길이): 선언 길이 검사만 지운다 → 스트리밍 누적 검사가 대신 거부하므로 `outcome`은 여전히 `failed`지만, 본문을 읽은 뒤라 (ii-a)의 "조각 읽힘 수 == 0" 단언이 RED(plan 단계 모의 관측: `body_chunks_read=2` — `progress.md` 사실표 P16)
- 되돌림 검사(스트리밍 누적): 스트리밍 누적 검사만 지운다 → (ii-b)는 선언 길이가 없어 통과해 버려 `outcome != "failed"`로 RED. (ii-a)는 선언 길이 검사가 그대로 잡으므로 GREEN — 두 경우를 따로 둔 이유다
- 되돌림 검사(둘 다): 두 검사를 모두 지운다 → (ii-a)·(ii-b) 모두 RED(모의 관측: `ok 3145731 bytes`, `body_chunks_read=3`)
- 되돌림 검사(시간): 전송 코루틴을 감싼 `asyncio.wait_for`를 지우고 httpx 시간 상한만 남긴다 → (iii)이 바깥 2초 상한에 걸려 `TimeoutError`로 RED(`MockTransport`가 httpx 시간 상한을 적용하지 않으므로)
- 범위 메모: 호스트 검사 함수에 손으로 만든 주소를 넣는 단위 검사는 두지 않는다. 요청 주소는 모듈 상수로 만들어지므로 그런 검사는 상수를 상수와 비교하는 자기 비교에 가깝다(lessons #9 형태 2). 다른 호스트로 실제 요청이 나가지 않는다는 성질은 (i)의 리디렉트 경우가 요청 경로를 통해 확인한다
- 잡지 못하는 것: 네이버 쪽 호출 제한(spec G3), 운영 전송 계층에서의 httpx 시간 상한 거동(바깥 `wait_for`가 상한을 보장하므로 판정에 쓰지 않음)

### AC-AIR7-006 — 응답 해석과 기사 파일 (REQ-AIR7-006)

- Given: (1) 녹화 픽스처 `recorded/020150_p1.json`과 `recorded/000040_p1.json`(그룹 배열, `progress.md §E.2` O1), (2) 합성 `synthetic/parse_cases.json`(빈 `body` / `articleId "../x"` / `datetime "2026102113"` / 정상 기사 `datetime "202610211352"` + `body` 앞 `<b>강조</b>`), (3) 합성 `synthetic/two_items_group.json`(그룹 하나에 기사 2건 — 실제로는 관측하지 못한 모양, spec G4), (4) 합성 `synthetic/mixed_malformed_groups.json`(정상 그룹 2개 + `items` 없는 그룹 1개 + `items`가 문자열인 그룹 1개 + 객체가 아닌 그룹 1개 + `items` 안에 객체가 아닌 기사 1개), (5) 합성 `synthetic/entity_body.json`(`body`에 `&#39;`·`&#x27;`·`&amp;`·`&lt;b&gt;리터럴&lt;/b&gt;`·`<i>태그</i>`)
- When: 각 픽스처로 수집 실행
- Then:
  1. (1) 기사 경로: 색인 기사 항목 수 = `min(10, 펼친 목록 길이)`, 항목 순서 = 펼친 목록 순서(`article_ref`를 테스트가 픽스처에서 `officeId/articleId`로 만들어 비교). 각 `ok` 항목의 텍스트 파일에 그 기사의 제목 평문과 본문 평문이 들어 있다 — 평문 기대값은 테스트가 `html.unescape(re.sub(r"<[^>]+>", "", 원문)).strip()`으로 픽스처에서 만든다
  2. 모든 `text_file` 값이 `^[0-9]{2}_article\.txt$`에 맞고, 폴더의 파일 이름 집합이 `{"index.json", "response.json"} ∪ {ok 항목의 text_file}`과 같다
  3. (2): 빈 `body` 기사 → `status == "metadata_only"`, `text_file is None`. `../x` 기사 → `status == "error"`, 파일 없음, 폴더 밖에 파일 없음. 10자리 `datetime` 기사 → `status == "error"`. 정상 기사 → `published_at == "2026-10-21T13:52:00+09:00"`, 텍스트 파일에 `강조`는 있고 `<b>`는 없다
  4. (3): 기사 항목 수 = 펼친 목록 길이(그룹 수보다 1 많다), 두 기사 모두 항목이 있다
  5. (4): 수집기가 예외 없이 반환. 정상 그룹의 기사는 `ok`, 깨진 그룹·객체가 아닌 기사마다 `status == "error"`, 기사 필드 `null`, `error`에 그룹 번호와 사유(`items missing` / `items not a list` / `group not an object` / `article not an object`) 항목이 하나씩, 파일 없음
  6. 엔티티 해제(V3) — 녹화 근거: (1)의 두 녹화 파일에서 제목 또는 본문 원문에 `&[a-zA-Z#0-9]+;`가 있는 기사를 테스트가 **런타임에 골라**(plan 단계 관측: 020150 그룹 1 본문·그룹 4 제목, 000040 그룹 3 본문 — 사실표 P17) 그 텍스트 파일에 `&quot;`가 없고, 1의 평문 기대값(해제된 `"` 포함)이 들어 있다. 고른 기사가 0건이면 테스트는 통과가 아니라 실패한다(픽스처가 바뀌어 검사가 비는 것을 막음)
  7. 순서(V3) — (5): 텍스트 파일에 `'`(두 참조 모두 해제), `&`, 리터럴 `<b>리터럴</b>`이 있고, `<i>`·`&#39;`·`&amp;`는 없으며 `태그`는 있다
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_006 -q`
- 기대 관측: 실패 0
- 되돌림 검사(경로, V1): 기사 목록을 첫 그룹의 `items`만으로 만들게 바꾼다(`data[0]["items"]`) → (1)에서 항목 수 1로 RED. 그룹 `total`의 합으로 개수를 세게 바꾼다 → (1)의 020150에서 항목 수 단언 RED(`total` 합계 22 ≠ 펼친 길이 10, P17)
- 되돌림 검사(모양 오류, V1): 그룹 모양 검사를 지운다(`g["items"]`를 바로 순회) → (4)에서 `KeyError`/`TypeError`가 수집기 최상위 예외 처리로 가서 `outcome == "failed"`가 되거나 테스트가 예외로 끝나, 5의 "정상 그룹 기사는 `ok`" 단언이 RED
- 되돌림 검사(엔티티 해제, V3): 엔티티 해제 단계를 지운다 → 6에서 녹화 기사의 텍스트 파일에 `&quot;`가 남아 RED, 7에서 `&#39;`가 남아 RED
- 되돌림 검사(순서, V3): 해제를 태그 제거보다 먼저 하게 바꾼다 → 7에서 `&lt;b&gt;리터럴&lt;/b&gt;`가 `<b>리터럴</b>`로 바뀐 뒤 지워져 리터럴 `<b>리터럴</b>` 단언이 RED
- 추가 되돌림: 텍스트 파일 이름을 기사 제목으로 만든다 → 2 RED. 빈 본문도 `ok`로 기록한다 → 3의 `metadata_only` 단언 RED. `datetime`을 시간대 없이 변환한다 → `+09:00` 단언 RED. 태그 제거를 지운다 → 3의 `<b>` 부재 단언과 7의 `<i>` 부재 단언 RED
- 잡지 못하는 것: 실제 응답에 태그가 든 `body`, 실제 응답의 그룹당 기사 2건 이상(둘 다 미관측 — 합성으로만 검사, spec G4). 요약 본문이 사실과 맞는지(서버는 받은 텍스트만 공급). `outcome` 값은 AC-014가 검사한다

### AC-AIR7-007 — 색인 키 집합과 원본 보존 (REQ-AIR7-007)

- Given: AC-006 (1) 실행 결과
- When: `index.json`을 읽는다
- Then: 최상위·`search`·`articles[]` 키 집합이 §B와 **집합 동등**. `channel == "naver"`, `search.status == "ok"`, `search.item_count`가 픽스처의 **펼친 기사 목록 길이**와 같음(그룹 `total` 합이 아님), `response_sha256 == sha256(response.json 바이트)`, `response_bytes == len(response.json 바이트)`, `response.json` 바이트 = `MockTransport`가 보낸 바이트. 시각 필드 4종이 모두 `+09:00`으로 끝난다. `article_ref == f"{office_id}/{article_id}"`. 교차 확인(V5): 각 `ok` 항목의 `article_url`이 같은 기사의 응답 `mobileNewsUrl`과 같다(관측 사실 O6을 테스트가 응답에서 읽어 확인 — 주소는 응답 문자열로 만들지 않는다)
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_007 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 색인에서 `article_url` 키를 뺀다 → 집합 동등 단언 RED(부분집합 검사가 아니라 동등이므로 키 추가도 RED)
- 추가 되돌림: `item_count`를 그룹 `total`의 합으로 쓰게 바꾼다 → 020150에서 22 ≠ 10으로 RED. `article_url`을 `officeId`를 정수로 바꿔 만들게 한다(앞자리 0 소실) → `mobileNewsUrl` 교차 확인 RED
- 잡지 못하는 것: 열린 기사 페이지가 그 기사인지(제목 대조 안 함 — spec G5 남은 미관측)

### AC-AIR7-008 — 실패해도 진행, 0건은 0건 (REQ-AIR7-008, REQ-AIR7-009)

- Given: 처리기 변형: 연결 오류(`httpx.ConnectError`), HTTP 410, HTTP 500, JSON이 아닌 본문(`synthetic/not_json.txt`), 모든 그룹에 `items`가 없는 배열(`synthetic/missing_items_path.json`), 최상위가 객체인 JSON(`synthetic/top_level_object.json`), 기사 0건 — 녹화 `recorded/999999_p1.json`(`[]`, 실제 관측한 0건 모양)과 합성 `synthetic/zero_articles.json`. 작업 서비스 경로에는 가짜 실행기
- When: 수집기를 직접 실행, 그리고 각 변형을 주입한 작업 서비스로 작업 실행
- Then: 실패 변형 6종은 수집기가 예외 없이 반환하고 `outcome == "failed"`, `search.error`가 비어 있지 않음, 작업 서비스 경로에서 실행기 호출 수 1·작업 상태는 실행기 결과대로(`done`). 0건 변형 2종은 `outcome == "no_results"`, `search.status == "ok"`, `search.item_count == 0`, `articles == []`
- 추가 되돌림(V1): 최상위 배열 검사를 지운다 → 최상위 객체 변형에서 순회가 키 문자열을 그룹으로 다루어 `outcome != "failed"`이거나 예외로 RED. "`items` 배열을 가진 그룹이 하나도 없음 → 실패" 판정을 지운다 → `missing_items_path.json`이 그룹별 `error` 항목만 남기고 `search.error`가 비어 RED
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py backend/tests/test_goose_job_service.py -k air7_008 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 수집기의 최상위 예외 처리를 지워 예외를 다시 던지게 한다 → 작업 서비스 경로는 작업 서비스 fail-open이 삼키므로 통과하고, **수집기 직접 실행 경로**에서 예외로 RED. 같은 변형에서 작업 서비스 쪽 `except Exception`까지 지우면 작업이 `error`/`exit_error`, 실행기 호출 0으로 RED
- 추가 되돌림: 기사 0건을 `failed`로 기록하게 바꾼다 → `outcome == "no_results"` 단언 RED
- 잡지 못하는 것: 네이버가 200과 함께 오래된 기사만 주는 경우(신선도 판정은 감사의 24시간 규칙과 goose 몫)

### AC-AIR7-009 — 하네스 네이버 규칙 문구 (REQ-AIR7-010)

- Given: M4 완료 트리
- When: 아래 문자열마다 `grep -cF '<문자열>' backend/goose_harness_src/harness-instructions.md`(한 줄 루프로 실행해 `개수<TAB>문자열`을 `$S/air7_009.txt`에 남긴다)
- 검사 문자열(모두 규칙 번호와 무관 — 006과의 병합으로 번호가 9에서 10으로 바뀌어도 그대로 쓴다):

  | 문자열 | plan 단계 기준선(HEAD `871c105`, 사실표 P6) | M4 뒤 기대 |
  |---|---|---|
  | `runs/<job_id>/naver/index.json` | 0 | ≥ 1 |
  | `article_url` | 0 | ≥ 1 |
  | `channel: "naver"` | 0 | ≥ 1 |
  | `metadata_only` | 0 | ≥ 1 |
  | `"no_results"` | 0 | ≥ 1 |
  | `모바일 뉴스 API 응답의 제목·요약 본문 필드` (v0.4.0, V2 (b)) | 0 | ≥ 1 |
  | `서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음` | 0 | ≥ 1 |
  | `API 요약본(약 150자), 원문 미확인` (V2 (a)) | 0 | ≥ 1 |
  | `요약에 없는 사실은 단정하지 않는다` (V2 (c)) | 0 | ≥ 1 |
  | `이번 세션에서 그 파일을 연 시각` (`accessed_at` 규정 — `accessed_at` 자체는 규칙 8-2에 이미 1회 있어 쓰지 않는다) | 0 | ≥ 1 |
  | `original_news` | 0 | ≥ 1 |
  | `code_validated` (V4) | 0 | ≥ 1 |
  | `서버가 종목코드 유효성을 확인하지 못함` (V4) | 0 | ≥ 1 |
  | `runs/<job_id>/dart/index.json` (규칙 8 보존 확인) | 2 | 2 |

- Then: 표의 "M4 뒤 기대"를 모두 만족
- 되돌림 검사: 네이버 규칙 블록을 지운다 → 위 13개 문자열의 개수가 모두 0으로 RED, 규칙 8 문자열만 2. V2 문구만 따로: 규칙에서 "요약에 없는 사실은 단정하지 않는다" 문장을 지운다 → 그 줄 하나만 0으로 RED(다른 12개는 그대로) — 기준선이 0이라 지우면 0으로 돌아간다는 것을 plan 단계에서 관측했다(사실표 P6). (규칙 8에도 있는 짧은 표기 `서버 사전 수집본으로 열람`과 `accessed_at`은 기준선이 이미 1이라 지워도 0이 되지 않으므로 검사 문자열로 쓰지 않는다 — 대신 네이버 규칙에만 있는 표기를 쓴다. 기준선 전체는 사실표 P6)
- 잡지 못하는 것: 문구가 있다는 것은 goose가 따른다는 뜻이 아니다 — AC-012

### AC-AIR7-010 — 규칙의 기록 형태가 감사를 통과하는가 (REQ-AIR7-010)

- Given: AC-006 (1)의 색인으로 네이버 규칙 N-2·N-3이 정한 대로 만든 합성 `report-input.json` 조각(`document_type: "deep_report"`, `research_window.cutoff`는 색인 `search.searched_at`보다 10분 뒤, `sources`에는 `ok` 항목 하나를 N-2 형태로 — `read_scope`에 `모바일 뉴스 API 응답의 제목·요약 본문 필드`, `limitations`에 두 문구)
- When: 감사 함수(`audit_report.py`의 `audit`, 변경 없음)를 직접 불러 결함 코드 집합을 얻는다. 같은 입력에서 한 가지씩 바꾼 변형 4개도 실행: (v1) `result: "blocked"`, (v2) 출처 `verification: "server_prefetch"`, (v3) `read_scope: ""`, (v4) `searched_at`을 cutoff보다 25시간 앞으로
- Then: 원래 입력의 결함 코드에 `LATEST_SEARCH_NAVER`가 없다. (v1)~(v4) 각각의 결함 코드에 `LATEST_SEARCH_NAVER`가 있다. 색인 `outcome == "no_results"`로 만든 입력(`result: "no_results"`, `note`에 종목코드·`pageSize`·`page`)도 `LATEST_SEARCH_NAVER`가 없다
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_010 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 변형 (v1)~(v4)가 이 AC의 되돌림이다 — 규칙이 정한 기록 형태에서 한 요소를 되돌리면 감사가 RED를 낸다. 이 테스트는 감사 함수(프로덕션 코드)를 부르므로 양변이 같은 식에서 나오는 자기 비교가 아니다
- 정직한 한계: 이 AC는 "규칙대로 적으면 감사를 통과하고, 막힘을 적으면 통과하지 못한다"는 계약만 확인한다. 감사는 `limitations`를 읽지 않으므로 요약본 문구(V2 (a))가 빠져도 감사는 통과한다 — 그 문구는 AC-012 검사 3의 성공 형태가 검사한다. 감사는 `no_results`를 조건 없이 받으므로(spec §2.4) 지어낸 `no_results`는 여기서 잡히지 않는다 — AC-012 검사 3이 잡는다. goose가 규칙대로 적는지는 AC-012만 본다
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
        cur = int(m.group(1)); tops.append(cur); body = line[m.end():]
    else:
        s = re.match(r"^\s+- (\d+)-\d+[a-z]?\. ", line)
        if s and int(s.group(1)) != cur:
            errs.append("line %d: sub-item %s-* under rule %s" % (n, s.group(1), cur))
        body = line[s.end():] if s else line
    # 본문 안 `N-M` 참조는 자기 규칙 번호만 가리켜야 한다(다시 매긴 뒤 남은 옛 참조를 잡는다)
    for r in re.finditer(r"(?<![\d.\-])(\d{1,2})-\d{1,2}[a-z]?(?![\d\-])", body):
        if cur is not None and int(r.group(1)) != cur:
            errs.append("line %d: in-text reference %s inside rule %s" % (n, r.group(0), cur))
if tops != list(range(1, len(tops) + 1)):
    errs.append("top-level numbers not 1..K unique: %s" % tops)
print("rules", tops)
print("rule numbering ok" if not errs else "\n".join(errs))
```

- 기대 관측(#4): plan 단계 현재 트리에서 `rules [1, 2, 3, 4, 5, 6, 7, 8]` / `rule numbering ok`(사실표 P13). M4 뒤 `rules [1, …, 9]`, 006 병합 뒤 `rules [1, …, 10]`, 마지막 줄은 항상 `rule numbering ok`
- 되돌림 검사(#1·#3): 지침만 고치고 매니페스트 재생성을 빠뜨린다 → #1에서 `CLAUDE.md` 해시 줄 차이 출력, #3에서 원본 해시 비교 테스트 RED
- 되돌림 검사(#4): 006 병합 트리에서 나중 쪽 규칙 번호를 9로 둔다 → `top-level numbers not 1..K unique: [1, …, 9, 9]`로 RED. 상위 번호만 10으로 바꾸고 하위 라벨을 `9-6`으로 남긴다 → `line <n>: sub-item 9-* under rule 10`으로 RED. 라벨은 10으로 바꾸고 본문 참조 "9-2에서"를 남긴다 → `line <n>: in-text reference 9-2 inside rule 10`으로 RED(세 경우 모두 plan 단계에서 이 블록과 같은 판정 로직으로 관측 — 사실표 P13)
- 정직한 한계(#4): 본문 참조 검사는 `N-M` 형태만 본다. "5번 규칙"처럼 다른 규칙을 이름으로 가리키는 산문은 검사하지 않는다(규칙 번호가 바뀌는 것은 나중 쪽 규칙 하나뿐이고, 기존 규칙 1~8은 번호가 그대로다). 또한 한 규칙 본문이 다른 규칙의 하위 항목을 `N-M`으로 가리키는 것도 위반으로 잡으므로, 네이버 규칙 초안은 다른 규칙의 하위 항목을 `N-M`으로 가리키지 않는다(plan.md §4)
- 잡지 못하는 것: 서버 재시작 누락(설치는 서버 시작 때만 일어난다 — 리드가 AC-012 전에 확인)

### AC-AIR7-012 — 라이브 관측 검사 (REQ-AIR7-013, 리드 몫·이 레인 밖)

통합과 서버 재시작 뒤 리드가 실행하는 라이브 게이트다. 이 레인은 실행하지 않는다. 통과해야 SPEC을 닫는다(§F). 같은 KST 날짜에 020150으로 최대 2회 실행할 수 있다. **검사 1·2·3은 같은 한 회차에서 모두 만족해야 하고**(회차 A의 수집 성공과 회차 B의 감사 통과를 합쳐 통과로 보지 않는다), 그날 실행한 다른 회차에도 검사 3 스크립트를 돌려 `violations 0`이어야 한다. 검사 3은 두 부분으로 나뉘며, 스크립트가 색인 `outcome`을 보고 적용할 부분을 고른다:

- **3F 지어냄 검사 — 모든 회차**: (F1) `naver`의 `no_results` 항목은 색인 `outcome == "no_results"`일 때만 허용(REQ-AIR7-010 "only when the index outcome is `no_results`"), (F2) `read` 항목의 출처 `url`이 색인의 어떤 `article_url`과 같으면 그 항목은 `ok`이고 `read_scope`에 그 `text_file`, `limitations`에 `서버 사전 수집본으로 열람`이 있어야 함(색인 파일을 읽었다는 주장은 사실이어야 함)
- **3S 성공 검사 — 색인 `outcome`이 `complete`·`partial`인 회차에만**: (S1) `naver`의 `read` 항목 1건 이상, (S2) 그 `read` 항목의 `source_ids`가 비어 있지 않은 목록, (S3) 그 출처가 **모두** 색인 `ok` 항목(아래 출처 규칙)이고, 각 출처의 `limitations`에 `API 요약본(약 150자), 원문 미확인`도 있음(v0.4.0, spec D3 — 요약본을 출처로 인정하는 조건), (S4) `read` 항목이 유일한 `naver` 항목(REQ-AIR7-010 "the only `naver` entry" — 같은 회차에 `blocked`·`no_results` 등 다른 `naver` 항목이 있으면 위반)

색인 `outcome`별로 REQ-AIR7-010이 허용하는 goose 기록과 적용 검사:

| 색인 `outcome` | REQ-AIR7-010이 허용하는 `naver` 기록 | 적용 검사 |
|---|---|---|
| `complete`·`partial` | 연 `ok` 파일을 인용한 `read` 한 건만 | 3F + 3S |
| `no_results` | 조건을 `note`에 적은 `no_results`. 기존 경로로 다시 찾아 실제로 읽었다면 그 결과의 `read` | 3F만 |
| `failed`·`disabled`·색인 없음(`missing`) | 기존 경로 대체 시도의 실제 결과 — 읽었으면 `read`(색인 밖 출처 허용), 막혔으면 `blocked`. `no_results`는 허용하지 않음 | 3F만 |

`no_results`·`failed`·`disabled` 회차는 검사 1에서 이미 통과 회차가 될 수 없으므로, 그런 회차에서 goose가 규칙대로 `blocked`를 적거나 대체 경로로 읽은 것은 위반이 아니다. 그런 회차에서 잡는 것은 지어낸 기록(색인이 `failed`인데 `no_results`, 색인 `metadata_only` 기사를 읽었다는 주장)뿐이다.

출처 규칙(REQ-AIR7-013과 같은 규칙, spec D7): `naver` 채널의 `result == "read"` 항목이 인용한 출처는 **모두** 색인 `ok` 항목이어야 한다. goose가 다른 경로로 연 출처는 `naver` 채널에 허용하지 않는다(그런 기사는 `original_news` 채널에 적는다 — 규칙 N-3). 이유: 게이트의 목적은 사전 수집이 통과를 만들었음을 보이는 것이고, 다른 출처를 허용하면 수집이 실패하고 대체 경로로 통과한 경우와 구분할 수 없다.

- Given: 통합된 서버 재시작 완료, `shasum -a 256 ~/.goose-harness/CLAUDE.md`가 `shasum -a 256 backend/goose_harness_src/harness-instructions.md`와 같음, 기준선은 a5becbb9(`naver`가 `blocked`, `LATEST_SEARCH_NAVER` 발생 — spec §2.1)
- When: 앱에서 020150으로 goose 작업을 실행하고 끝까지 기다린다. `IDX=~/.goose-harness/runs/<job_id>/naver/index.json`, `INP=~/.goose-harness/runs/<job_id>/draft/report-input.json`
- Then (작업과 같은 KST 날짜에, 같은 `<job_id>`로 확인):
  1. `$IDX`의 `outcome`이 `complete` 또는 `partial`, `request_count <= 1`
  2. `python3 -I ~/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input "$INP" --output "$S/audit.json"`의 결함 코드에 `LATEST_SEARCH_NAVER`가 없다
  3. 아래 블록을 `$S/air7_check3.py`로 추출해 `python3 -I "$S/air7_check3.py" "$IDX" "$INP"` → 첫 줄이 정확히 `violations 0`, 둘째 줄이 `mode 3F+3S`(통과 회차는 검사 1 때문에 반드시 이 모드다). 그날의 다른 회차도 같은 명령으로 첫 줄 `violations 0`(모드는 그 회차의 색인 `outcome`이 정한다)

```python
# AC-AIR7-012 검사 3 — naver 기록과 서버 색인 대조
# 3F(지어냄 검사)는 모든 회차, 3S(성공 검사)는 색인 outcome이 complete·partial인 회차에만 적용한다
import json, os, sys
MARK = "서버 사전 수집본으로 열람"
SUMMARY = "API 요약본(약 150자), 원문 미확인"  # 3S에서만 요구(spec D3)
idx = json.load(open(sys.argv[1], encoding="utf-8")) if os.path.exists(sys.argv[1]) else {"outcome": "missing", "articles": []}
d = json.load(open(sys.argv[2], encoding="utf-8"))
outcome = str(idx.get("outcome"))
arts = [a for a in (idx.get("articles") or []) if isinstance(a, dict)]
ok = {a.get("article_url"): a for a in arts if a.get("status") == "ok"}
indexed = {a.get("article_url") for a in arts}
src = {str(s.get("id")): s for s in d.get("sources", []) if isinstance(s, dict)}
nav = [s for s in d.get("research_window", {}).get("searches", []) if isinstance(s, dict) and s.get("channel") == "naver"]
reads = [s for s in nav if s.get("result") == "read"]
success = outcome in ("complete", "partial")
v = []

def source_findings(sid, strict):
    x = src.get(str(sid))
    if x is None:
        return [str(sid) + ": source id not in sources"] if strict else []
    a = ok.get(x.get("url"))
    if a is None:
        return [str(sid) + ": url is not an ok index article_url"] if strict or x.get("url") in indexed else []
    if str(a.get("text_file") or "\0") not in str(x.get("read_scope", "")) or MARK not in str(x.get("limitations", "")):
        return [str(sid) + ": read_scope/limitations mismatch"]
    if strict and SUMMARY not in str(x.get("limitations", "")):
        return [str(sid) + ": limitations lacks summary phrase"]
    return []

for s in nav:  # 3F-F1
    if s.get("result") == "no_results" and outcome != "no_results":
        v.append("naver no_results while index outcome=" + outcome)
if success:  # 3S-S1, S4
    if not reads:
        v.append("no naver read entry")
    if len(nav) > 1:
        v.append("naver entries=%d (the read entry must be the only naver entry)" % len(nav))
for s in reads:  # 3F-F2 (모든 회차) / 3S-S2, S3 (성공 회차)
    ids = s.get("source_ids")
    if not isinstance(ids, list) or not ids:
        if success:
            v.append("naver read entry has no source_ids")
        continue
    for i in ids:
        v += source_findings(i, success)
print("violations", len(v))
print("mode", "3F+3S" if success else "3F only (outcome=" + outcome + ")")
for line in v:
    print(" ", line)
```

- 되돌림 검사(검사 3, 리드가 게이트 실행 때 통과 회차의 `$INP` 사본으로 함께 관측): `naver` 항목의 `result`를 `no_results`로 바꾼다 → RED(`naver no_results while index outcome=…`, `no naver read entry`). 출처 `url`을 `metadata_only` 항목의 `article_url`이나 색인 밖 주소로 바꾼다 → `<id>: url is not an ok index article_url`로 RED. `source_ids`를 `[]`로 바꾼다 → `naver read entry has no source_ids`로 RED. `blocked` `naver` 항목을 하나 더 넣는다 → `naver entries=2 …`로 RED. 출처 `limitations`에서 `API 요약본(약 150자), 원문 미확인`을 뺀다 → `<id>: limitations lacks summary phrase`로 RED. 이 블록(v0.4.0)은 plan 단계에서 문서에서 그대로 추출해 합성 입력 20종으로 실행했다(사실표 P14 — 성공 회차 12종 중 통과 입력 1종 `violations 0`·변형 11종 RED(정수 출처 id는 역추적 없이 위반 한 줄, 요약본 문구 누락 포함), 다른 회차의 규칙 준수 기록 6종 `violations 0`(요약본 문구 없는 대체 경로 `read` 포함 — 3F는 그 문구를 요구하지 않는다), 다른 회차의 지어낸 기록 2종 RED)
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

- Given: 픽스처 5종(M1이 만든 것과 M2가 더하는 것, acceptance §A): (a) `synthetic/mixed_status.json`(정상 1 + 빈 `body` 1 + `articleId "../x"` 1), (b) `synthetic/all_metadata_only.json`(모든 `body`가 빈 값), (c) 녹화 `recorded/020150_p1.json`(실제 응답 — 모든 기사가 정상), (d) `synthetic/parse_cases.json`(정상 1 + `metadata_only` 1 + `error` 2), (e) `synthetic/mixed_malformed_groups.json`(정상 그룹 + 깨진 그룹)
- When: 각 픽스처로 수집 실행
- Then: `outcome`이 정확히 (a) `"partial"`, (b) `"failed"`, (c) `"complete"`, (d) `"partial"`, (e) `"partial"`. (a)~(d)는 `search.status == "ok"`, `search.item_count`가 픽스처의 펼친 기사 목록 길이와 같음(테스트가 픽스처에서 계산). (0건 → `no_results`와 요청 실패 → `failed`는 AC-008이 검사한다)
- 명령: `PY -m pytest backend/tests/test_goose_naver_prefetch.py -k air7_014 -q`
- 기대 관측: `5 passed`(경우마다 테스트 하나)
- 되돌림 검사: "항목은 있으나 `ok` 0개"를 `complete`로 판정하게 바꾼다(예: `all(s == "ok" …)` 대신 `not any(s == "error" …)`) → (b)에서 `"complete" != "failed"`로 RED
- 추가 되돌림: 혼합을 `complete`로 판정하게 바꾼다(`ok`가 하나라도 있으면 `complete`) → (a)·(d)·(e)에서 RED. `metadata_only`를 판정에서 빼고 `error`만 센다 → (b)가 `"complete"`가 되어 RED. 모양 오류 항목을 판정에서 뺀다 → (e)가 `"complete"`가 되어 RED
- 왜 필요한가: AC-012 검사 1과 규칙 N-5가 이 값에 기대므로, 판정이 틀리면 수집 실패가 게이트 통과처럼 보이거나 goose가 대체 경로를 건너뛴다
- 잡지 못하는 것: 라이브 응답의 기사 구성(라이브 회차의 색인으로만 관측)

### AC-AIR7-015 — 종목코드 확인 기록 (REQ-AIR7-015, V4)

- Given: 실제 네이버 수집기 + 녹화 `recorded/999999_p1.json`(존재하지 않는 종목코드의 실제 응답 `[]`, `progress.md §E.2` R3)을 돌려주는 `MockTransport`, 가짜 실행기. 작업 서비스 구성 4가지: (a) `code_check=lambda c: True`, (b) `code_check=lambda c: False`, (c) `code_check` 없음(생성자 기본값), (d) 예외를 던지는 `code_check`. 별도로 (e) (a) 구성 + `AI_REPORT_GOOSE_NAVER_PREFETCH=0`. 그리고 (f) 운영 인스턴스 `_service`의 `code_check`를 그대로 불러 `"020150"`과 `"999999"`를 확인(서버 종목 목록 조회 — 네트워크 없음, 가드가 확인)
- When: 각 구성으로 작업 실행 후 `runs/<job_id>/naver/index.json`을 읽는다
- Then:
  1. (a)~(d) 모두 수집기 호출 수 1, 요청 수 1, `outcome == "no_results"`, `search.item_count == 0`(빈 응답은 확인 결과와 무관하게 `no_results`로 정직하게 기록)
  2. `code_validated`가 정확히 (a) `true`, (b) `false`, (c) `false`, (d) `false`. (d)는 작업이 실행기까지 진행(호출 수 1)
  3. (e): `outcome == "disabled"`, `code_validated == true`, 요청 수 0
  4. (f): `"020150"` → `True`, `"999999"` → `False`(라우터가 404를 내는 조회와 같은 결과 — spec §2.7)
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py backend/tests/test_goose_naver_prefetch.py -k air7_015 -q`
- 기대 관측: 실패 0
- 되돌림 검사: 작업 서비스가 확인 결과 대신 `True`를 넘기게 바꾼다 → (b)·(c)·(d)에서 `code_validated == false` 단언 RED
- 추가 되돌림: 확인이 거짓이면 수집을 건너뛰게 바꾼다 → (b)·(c)에서 수집기 호출 수 0으로 RED(D9 — 거짓이어도 수집은 실행). 확인 함수의 예외를 그대로 올리게 바꾼다 → (d)에서 작업이 `error`가 되거나 수집기 호출 0으로 RED. 운영 인스턴스에 `code_check`를 붙이지 않는다 → (f)가 `None`을 부를 수 없어 RED
- 잡지 못하는 것: 서버 종목 목록에 남아 있는 상장 폐지 종목(목록이 고정된 엑셀 표라 `true`로 기록된다 — spec §9). 실제 상장 종목의 기사 0건 응답(미관측, spec G4)

## §D 경계 사례

| 사례 | 기대 동작 | 담당 AC |
|---|---|---|
| 기사 0건 | `no_results`, goose는 조건을 적고 `no_results` | AC-008, AC-010 |
| 존재하지 않는 종목코드(200 `[]`) | `no_results` + `code_validated`가 확인 결과를 기록, goose 메모는 그 값에 따라 달라짐 | AC-015, AC-009 문구 |
| 그룹 배열 펼침·그룹당 기사 2건 | 모든 그룹의 `items`를 순서대로 펼침, `total` 무시 | AC-006 (1)·(3), AC-007 |
| 깨진 그룹·최상위 객체 | 깨진 그룹은 `error` 항목, 최상위 객체·`items` 배열 전무는 `failed` | AC-006 (4), AC-008 |
| 제목·본문의 HTML 엔티티 | 태그 제거 뒤 해제, 텍스트 파일에 엔티티 없음 | AC-006 6·7 |
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

- run 레인: AC-AIR7-001~011, 013, 014, 015 통과(명령·출력·기준선·되돌림 RED 원문을 `progress.md §E.2`에)
- `claude-settings.json`·감사 스크립트·`goose_dart_prefetch.py`·프론트 무변경
- 006과 병합하는 쪽: plan.md §5 필수 병합 단계 1~4의 관측 결과를 기록
- 리드: 통합·서버 재시작 뒤 AC-AIR7-012 통과(라이브 관측 게이트 — 실패 기록만으로는 닫지 않는다)
- 이 SPEC 이후에도 goose 결과가 `draft`임을 sync 문서에 명시
