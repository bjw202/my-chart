# SPEC-AI-REPORT-005 — 인수 기준

버전 0.3.1 · 요구사항은 `spec.md §4`(REQ-AIR5-001~016). 각 AC는 Given-When-Then, 실행 명령, 기댓값, 그리고 **이 AC가 잡아내는 틀린 구현(대조)** 과 **잡지 못하는 것** 을 적는다. 대조 항목은 run 단계에서 실제로 되돌림을 적용해 RED를 관측해야 GREEN으로 기록할 수 있다(lessons #9). 관측하지 못한 대조는 `progress.md §E.2`에 Gap으로 남긴다.

## §A 공통 실행 조건

- Python 명령은 가상환경을 활성화한 뒤 실행한다. 이 저장소의 서버용 가상환경은 코드 폴더와 다른 경로(`/Users/byunjungwon/Dev/my_chart/.venv`)에 있다. 아래 `PY`는 그 환경의 `python`이다.
- 테스트 함수 이름에 AC 번호 꼬리표(`air5_001` 등)를 넣어 `-k`로 고를 수 있게 한다.
- 프론트 테스트는 `npm --prefix frontend run test -- <필터>`로 돌린다. `--prefix`가 작업 폴더를 `frontend`로 바꾸므로 `--root frontend`를 함께 주면 `frontend/frontend`를 찾아 "No test files found"로 실패한다(plan-audit B1 관측). 이 형태는 저장소 루트의 `.claude/worktrees`를 수집하지 않는다.
- `$S`는 세션 증거 폴더 `.moai/state/verify/<session>/`다.
- 픽스처는 run 단계 M1이 research.md §6 명령으로 받은 녹화 HTML과, 그것을 손본 합성 픽스처다. 기댓값 리터럴은 research.md §3·§5의 측정값이며, M1 재수집 결과가 다르면 M1이 새 측정값으로 고친 뒤(코드 작성 전) 이 문서가 아니라 `progress.md`에 기록하고 manager-spec 재위임으로 반영한다.

## §B index.json 고정 키 집합 (AC-AIR5-009가 집합 동등으로 검사)

- 최상위: `schema_version`, `code`, `company`, `search`, `outcome`, `started_at`, `finished_at`, `request_count`, `files`
- `company`: `name`, `corp_code` (회사 확인 실패 시 `company` 값은 `null`)
- `search`: `url`, `query`, `searched_at`, `status`, `row_count`, `error`
- `files[]` 항목: `rcp_no`, `report_type`, `report_name`, `period`, `document`, `attachment_name`, `section`, `section_title`, `basis`, `viewer_url`, `fetched_at`, `html_file`, `text_file`, `sha256`, `bytes`, `status`, `error`
- `outcome` 값: `complete` | `partial` | `company_unresolved` | `failed` | `disabled`
- `files[].status` 값: `ok` | `error` | `skipped`
- `files[].section` 값(고정 키, spec.md §4.8): `financial_statements` | `notes` | `summary` | `auditor_report`. `files[].document` 값: `main` | `attachment`. `files[].basis` 값: `consolidated` | `separate`
- 시각 필드(`search.searched_at`, `started_at`, `finished_at`, `files[].fetched_at`): 시간대 포함 ISO-8601, 오프셋 `+09:00`

## §C 인수 기준

### AC-AIR5-001 — 실행 위치: 잠금 밖, 실행기 전 (REQ-AIR5-001)

- Given: 가짜 수집기(호출 시 인자를 기록하고 `asyncio.Event`를 기다림)와 가짜 실행기(호출 순서를 기록)를 주입한 작업 서비스, 임시 `runs` 폴더
- When: `start("020150", …)`를 호출하고, 수집기가 대기하는 동안 같은 종목·다른 종목 `start`를 한 번씩 더 호출한 뒤 이벤트를 풀어 준다
- Then: 첫 `start`는 수집기가 끝나기 전에 `started`를 돌려준다(대기 상한 1초 안). 대기 중 같은 종목 → `existing`, 다른 종목 → `busy`. 수집기 인자의 출력 폴더는 `<runs>/<job_id>/dart`. 기록된 호출 순서는 정확히 `["integrity", "prefetch", "integrity", "runner"]`(무결성 검사도 가짜로 주입해 기록). 별도 경우: 두 번째 무결성 검사만 실패시키면 작업은 `error`/`integrity`, 실행기 호출 수 0. 별도 경우: 수집기 없이 만든 서비스(생성자 기본값)는 순서 `["integrity", "runner"]`이고 진행 이벤트에 `dart_prefetch`가 없다
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air5_001 -q`
- 잡는 구현: (a) 수집을 `start()` 잠금 안에서 기다림 → 첫 `start`가 1초 안에 돌아오지 않음, (b) 수집을 실행기 뒤에 둠 → 순서 불일치, (c) 주입된 수집기 호출 누락 → `prefetch` 없음, (d) 출력 폴더를 `runs/<job_id>`로 둠 → 경로 불일치, (e) 실행 직전 재검사 누락 → 두 번째 `integrity` 없음·재검사 실패 경우에 실행기 호출 수 1, (f) 생성자 기본값을 실제 수집기로 둠 → 기본값 경우에 `prefetch` 등장. 이 변형은 수집기가 실패를 삼켜도(REQ-AIR5-010) 잡힌다: 순서 단언이 먼저 실패하고, 수집기가 연결을 시도한 테스트는 AC-014의 네트워크 가드가 종료 시 `network attempt in goose test`로 추가 실패시킨다
- 잡지 못하는 것: 실제 DART 응답에서의 동작(AC-005~012 담당)

### AC-AIR5-002 — 수집 중 취소 (REQ-AIR5-002)

- Given: (1) `asyncio.Event`를 영원히 기다리는 가짜 수집기(코루틴), (2) 실제 수집기 + 첫 요청에서 `asyncio.Event`를 영원히 기다리는 **비동기** `MockTransport` 처리기(동기 처리기·스레드는 쓰지 않는다 — 막힌 작업 스레드가 실행기 종료를 붙잡는다), 각각 가짜 실행기
- When: 작업 시작 후 수집 중에 `cancel(job_id)`, 그리고 별도 작업에서 `shutdown()`. 테스트 전체에 `asyncio.wait_for(..., 5)` 상한
- Then: 두 경우 모두 작업 상태 `cancelled`, 마지막 이벤트 종류 `cancelled`, 실행기 호출 수 0, 상한 안에 끝남
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py backend/tests/test_goose_dart_prefetch.py -k air5_002 -q`
- 잡는 구현(각각 되돌림으로 RED 관측): (a) 작업 서비스의 fail-open 처리가 `except BaseException`(또는 `CancelledError` 포함)으로 수집 예외를 삼키고 실행기로 진행 → 경우 (1)에서 실행기 호출 수 1, (b) 수집기 내부의 요청 반복이 `CancelledError`를 잡아 그 항목을 `error`로 적고 정상 반환 → 경우 (2)에서 실행기 호출 수 1, (c) 수집 호출을 `_run`의 `try` 밖에 둠 → 상태가 `cancelled`로 기록되지 않음
- 잡지 못하는 것: 취소 시 이미 받은 부분 파일 정리(요구하지 않음 — 작업 폴더 보존 규칙에 맡김)

### AC-AIR5-003 — 진행 단계 표시 (REQ-AIR5-003)

- Given: 가짜 수집기(호출되는 순간 `job.events`의 사본을 저장), 가짜 실행기(진행 이벤트 `goose_start` 1개 발생)
- When: 작업을 끝까지 실행하고 이벤트 목록을 읽는다; 끄기 스위치 `0`인 경우와 수집기 없는 서비스로 한 번씩 더 실행한다; 프론트 단위 테스트를 실행한다
- Then: 수집기 진입 시점의 사본에 `progress`/`dart_prefetch` 이벤트가 정확히 1개 들어 있다. 전체 이벤트에서 `dart_prefetch`는 1개이고 `goose_start`보다 앞선다. 끄기 스위치 `0`·수집기 없음 두 경우에는 `dart_prefetch` 이벤트가 0개. 프론트: `GOOSE_STAGES[0] === 'dart_prefetch'`, 진행 패널에 `공시 원문 수집`이 렌더링되고, `applyGooseStage`가 `dart_prefetch`를 `reached`에 넣는다. 갱신된 기존 테스트 2개(`gooseJob.test.ts:50`, `ProgressPanel.test.tsx:31`) 통과
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air5_003 -q`; `npm --prefix frontend run test -- gooseJob ProgressPanel`(v0.2.0 작성 시 현재 트리에서 실행: `Test Files 2 passed (2)`, `Tests 12 passed (12)`)
- 잡는 구현: (a) 백엔드만 보내고 프론트 단계 목록에 없음 → `applyGooseStage`가 무시해 `reached`에 없음, (b) 수집이 끝난 뒤에 보냄 → 진입 시점 사본에 이벤트 0개, (c) 표시 문구 누락 → 렌더 텍스트 없음, (d) 꺼진 경우에도 보냄 → 0개 단언 실패
- 잡지 못하는 것: 실제 화면 배치(라이브 AC-016 관측 때 함께 눈으로 확인, 비게이팅)

### AC-AIR5-004 — 끄기 스위치 (REQ-AIR5-004)

- Given: 실제 DART 수집기(모든 요청을 기록하는 `MockTransport` 주입)와 수집 호출 횟수를 세는 감시를 붙인 작업 서비스, 가짜 실행기, `AI_REPORT_GOOSE_DART_PREFETCH=0`. 스위치의 소유자는 작업 서비스다(REQ-AIR5-004)
- When: 작업 실행
- Then: 전송 요청 수 0, `index.json`의 `outcome == "disabled"`, `files == []`, 수집기 호출 수 0, `dart_prefetch` 진행 이벤트 0개, 실행기 호출 수 1. 같은 테스트에서 변수 미설정 시 수집기 호출 수 1·요청 수 ≥ 1(대조)
- 명령: `PY -m pytest backend/tests/test_goose_job_service.py -k air5_004 -q`
- 잡는 구현: (a) 스위치 무시 → 요청 수 ≥ 1, (a2) 스위치를 수집기 안에서만 확인 → 수집기 호출 수 1, (b) 끈 경우 색인을 쓰지 않음 → 파일 없음, (c) 끈 경우 실행기까지 건너뜀 → 호출 수 0

### AC-AIR5-005 — 회사 확인 (REQ-AIR5-005)

- Given: (1) 녹화 목록 `020150`(12행, 고유번호 전부 `00113997`), (2) 합성 목록: 같은 행에 고유번호 `00113997`과 다른 값이 섞임, (3) 행 0개 목록
- When: 수집 실행
- Then: (1) `company == {"name": "롯데에너지머티리얼즈", "corp_code": "00113997"}`, 첫 요청은 `POST https://dart.fss.or.kr/dsab007/detailSearch.ax`이고 본문에 `textCrpNm=020150`과 `publicType` 값 `A001`·`A002`·`A003`이 모두 있다. (2)·(3) `outcome == "company_unresolved"`, `company is None`, 전송 요청 수 정확히 1
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_005 -q`
- 잡는 구현: (a) 첫 행의 고유번호를 그대로 채택 → (2)에서 요청이 1개를 넘음, (b) `publicType` 누락 → 요청 본문 검사 실패, (c) 행 0개를 오류 대신 빈 성공으로 처리 → `outcome` 불일치
- 잡지 못하는 것: DART가 종목코드를 회사명 부분 일치로 해석하는 경우(관측 1건뿐, research F1)

### AC-AIR5-006 — 보고서 선택 (REQ-AIR5-006)

- Given: (1) 녹화 목록 `020150`, (2) 합성 목록: `반기보고서 (2025.06)` 원본과 그보다 늦게 접수된 `[기재정정] 반기보고서 (2025.06)`이 함께 있음
- When: 선택 실행
- Then: (1) 선택된 접수번호 목록이 순서까지 정확히 `["20260814000373","20260515000387","20260310002974","20251114002397","20250814003923","20250515002590","20250314001597","20241113000761","20240814000979"]`. (2) 2025.06 기간에는 정정본 접수번호 하나만 있고 원본은 없다, 기간 수는 9
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_006 -q`
- 잡는 구현: (a) 8개만 고름 → `20240814000979` 빠짐, (b) 오래된 순 → 순서 불일치, (c) 같은 기간 원본 유지 → (2) 실패, (d) 기간 대신 행 기준 9개 → (2)에서 기간 8개
- 잡지 못하는 것: 연결·별도 기준이 기간마다 바뀌는 회사(AC-007의 기준 기록으로만 드러남)

### AC-AIR5-007 — 구간 선택 (REQ-AIR5-007)

- Given: (1) 녹화 목차 `20260814000373`(반기), (2) 같은 목차에서 연결 노드를 지운 합성 목차, (3) 녹화 최신 사업보고서 목차, (4) (1)의 노드 순서를 바꿔 `3. 연결재무제표 주석`을 `2. 연결재무제표`보다 앞에 둔 합성 목차
- When: 구간 선택 실행
- Then: (1) 재무제표 노드 `dcmNo=11527102, eleId=19, offset=259834, length=178344, dtd=dart4.xsd`, `basis="consolidated"`; 최신 보고서 주석 노드 `eleId=24, offset=438182, length=1703030`. (2) 재무제표 노드 `eleId=58, offset=2141216`, 주석 `eleId=63`, `basis="separate"`. (3) `section == "summary"` 항목이 최신 사업보고서에만 1개이고 그 `section_title`은 `1. 요약재무정보`. (4) 재무제표 노드는 여전히 `eleId=19`. (5) 색인 항목의 `section` 값은 (1)의 재무제표 → `financial_statements`(`section_title` `2. 연결재무제표`), 주석 → `notes`(`section_title` `3. 연결재무제표 주석`), (2)의 재무제표 → `financial_statements`(`section_title` `4. 재무제표`), 주석 → `notes`(`section_title` `5. 재무제표 주석`)
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_007 -q`
- 잡는 구현: (a) 제목 부분 일치(`"연결재무제표" in title`의 첫 일치) → (4)에서 `eleId=24` 선택, (b) 연결이 있어도 별도 선택 → (1)에서 `eleId=58`, (c) 모든 보고서의 주석 수집 → 주석 항목 수 ≠ 1, (d) 요약재무정보를 반기보고서에서 가져옴 → (3) 실패, (e) `section`에 목차 제목을 그대로 씀 → (5)의 키 불일치(그리고 spec §4.8 대응표가 깨짐)
- 정직한 한계: 녹화 순서((1)·(2))에서는 부분 일치 구현도 우연히 맞는 노드를 고른다(본문이 주석보다 앞에 오므로). 부분 일치를 잡는 것은 합성 (4)뿐이다
- 잡지 못하는 것: 목차 제목 표기가 픽스처와 다른 업종(금융업 등) — 라이브 AC-016의 색인 상태로만 관측

### AC-AIR5-008 — 첨부 검토·감사보고서 (REQ-AIR5-008)

- Given: 녹화 첨부 목차 `rcpNo=20260814000373&dcmNo=11527105`(노드 4개), 녹화 본문 목차의 첨부 선택 목록(`11527104` 반기검토보고서, `11527105` 반기연결검토보고서), 녹화 최신 사업보고서 첨부 목차
- When: 첨부 수집 실행
- Then: 반기보고서 첨부는 `dcmNo=11527105`(연결)를 고르고, 받은 노드는 `eleId` 1과 2 두 개뿐(`(첨부)…`과 `주석` 제외). 최신 사업보고서의 첨부 감사보고서 항목이 `document="attachment"`로 1개 이상 있다
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_008 -q`
- 잡는 구현: (a) 목록 첫 첨부 선택 → `11527104`, (b) 첨부 노드 전부 수집 → eleId 3·4 포함, (c) 최신 보고서 첨부만 받고 사업보고서 첨부 누락 → 사업보고서 첨부 항목 0
- 잡지 못하는 것: 사업보고서 감사보고서 목차가 `(첨부)` 표기를 쓰지 않는 경우 — M1이 F8로 확인하고 픽스처에 반영

### AC-AIR5-009 — 저장과 색인 (REQ-AIR5-009)

- Given: 녹화 픽스처 전부를 경로별로 돌려주는 `MockTransport`
- When: 수집 실행 후 `index.json`을 읽는다
- Then: 키 집합이 §B와 정확히 같다(최상위·`company`·`search`·`files[]` 각각 집합 동등). `status=="ok"`인 모든 항목에서: `sha256`이 전송 계층이 돌려준 바이트의 해시와 같고, `bytes`가 그 길이와 같고, `viewer_url`의 호스트가 정확히 `dart.fss.or.kr`이며 질의 인자 6개가 선택된 목차 노드 값과 같고, `html_file`·`text_file`이 정규식 `^[a-z0-9_.-]+$`에 맞고 실제로 존재한다. 연결재무제표 텍스트 파일에 `영업이익`이 있고 `<`로 시작하는 태그 문자열이 없다. 색인 어디에도 숫자형 재무 값이 없다(`files[]` 값 중 정수는 `bytes`뿐). 모든 `files[].section`이 §B의 고정 키 4종 중 하나이고, 녹화 픽스처 전체 실행에서 나온 `section` 값 집합이 정확히 `{"financial_statements", "notes", "summary", "auditor_report"}`. 시각 필드 `search.searched_at`·`started_at`·`finished_at`·모든 `files[].fetched_at`이 `datetime.fromisoformat(v).tzinfo is not None`이고 오프셋이 `+09:00`
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_009 -q`
- 잡는 구현: (a) 텍스트만 저장 → `html_file` 없음, (b) 해시를 텍스트판으로 계산 → sha 불일치, (c) 파일 이름에 목차 제목 사용 → 정규식 실패, (d) 뷰어 주소에 offset·length 누락 → 인자 불일치, (e) 서버가 매출·영업이익을 추출해 색인에 추가 → 키 집합 불일치
- 잡지 못하는 것: 텍스트판의 표 행 보존 품질(라이브에서 goose가 수치를 읽었는지로 간접 관측)

### AC-AIR5-010 — 실패해도 진행 (REQ-AIR5-010)

- Given: 실패 행렬 `MockTransport` — (a) 목록 500, (b) 보고서 1건 목차에서 연결 오류, (c) 구간 1건 시간 초과, (d) 목차에 노드 없는 HTML; 그리고 (e) 작업 서비스에 주입한, 호출되자마자 `RuntimeError`를 던지는 가짜 수집기
- When: 각 경우 작업을 끝까지 실행(가짜 실행기는 `done` 반환)
- Then: 모든 경우 실행기 호출 수 1, 작업 상태 `done`, `error_kind is None`. (a) `outcome=="failed"`, (b)~(d) `outcome=="partial"`이고 해당 항목 `status=="error"`와 비어 있지 않은 `error`, 다른 보고서 항목은 `ok`. (e) `ERROR` 수준 로그 레코드에 작업 ID와 예외 정보(`exc_info`)가 있다(`caplog`)
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py backend/tests/test_goose_job_service.py -k air5_010 -q`
- 잡는 구현: (a) 예외 전파 → 작업 `error/exit_error`, 실행기 호출 수 0, (b) 한 보고서 실패에 전체 중단 → 다른 보고서 항목 0개, (c) 실패를 `ok`로 기록 → 상태 불일치
- 잡지 못하는 것: DART가 200과 함께 오류 안내 페이지를 주는 경우 — 목차 노드 없음(d)으로만 걸린다

### AC-AIR5-011 — 요청 예의와 예산 (REQ-AIR5-011)

- Given: 가짜 시계·가짜 대기 함수, 요청 시작 시각 기록, (1) 정상 픽스처, (2) 응답마다 가짜 시계를 30초 진행시키는 전송, (3) 9MB 본문을 주는 구간 1건
- When: 수집 실행
- Then: (1) 연속 요청 시작 간격이 모두 ≥ 1.0초, 동시 진행 요청 최대 1, 요청 수 ≤ 40, 각 요청의 시간 초과 값이 `min(20, 남은 예산)`(첫 요청 20초; 가짜 시계를 110초로 옮긴 뒤 보낸 요청은 10초 이하). (2) 누적 120초를 넘긴 뒤 새 요청 0개, 남은 항목 `status=="skipped"`, `outcome=="partial"`. (3) 그 항목 `status=="error"`, 오류 사유에 크기 초과 표기, 파일 미생성
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_011 -q`
- 잡는 구현: (a) 간격 없음 → 간격 0초, (b) `asyncio.gather` 병렬 요청 → 동시 진행 2 이상, (c) 예산 무시 → 120초 뒤에도 요청 발생, (d) 크기 상한 없음 → 파일 생성됨, (e) 요청당 시간 초과를 20초로 고정 → 110초 시점 요청의 값이 20초
- 잡지 못하는 것: 실제 DART의 제한 정책(공개 문서 없음)

### AC-AIR5-012 — 주소·입력 검증 (REQ-AIR5-012)

- Given: (1) 종목코드 `02015`·`0201500`·`02015a`, (2) 노드 값이 오염된 합성 목차(`offset="1&x=y"`, `dcmNo="../1"`, `dtd="a/b"`), (3) `https://evil.example/`로 302를 주는 응답, (4) 요청 기록
- When: 수집 실행
- Then: (1) 요청 0개, `outcome=="failed"`. (2) 오염 노드는 쓰이지 않고 그 항목 `status=="error"`, 해당 값이 들어간 요청 0개. (3) `evil.example`로의 요청 0개. (4) 기록된 모든 요청에서 `urlparse(url).scheme == "https"` 그리고 `urlparse(url).hostname == "dart.fss.or.kr"`(완전 일치 비교)
- 명령: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_012 -q`
- 잡는 구현: (a) 코드 검증 없이 전송 → 요청 1개 이상, (b) 노드 값을 그대로 질의에 붙임 → 오염 값이 든 요청 발생, (c) 리디렉트 자동 추적 → `evil.example` 요청 발생, (d) 호스트를 부분 문자열로 검사(`"dart.fss.or.kr" in url`) → 기록 단언이 `dart.fss.or.kr.evil.example` 같은 합성 리디렉트를 막지 못함(이 합성 사례를 (3)에 함께 넣는다)
- 잡지 못하는 것: DART 응답 본문 안의 지시문 — 하네스 지침 5번과 규칙 8-3b(로컬 수집 파일도 웹 자료로 취급)가 다룬다

### AC-AIR5-013 — 지침·매니페스트·권한 (REQ-AIR5-013, REQ-AIR5-014)

- Given: run 단계 M4 완료 트리
- When / Then (모두 통과해야 함):
  1. `PY -m backend.services.goose_harness > "$S/m.json" && diff "$S/m.json" backend/goose_harness_src/goose-manifest.json` → 출력 없음, 종료 0 (기준선 P7과 같은 형태)
  2. `shasum -a 256 backend/goose_harness_src/claude-settings.json` → `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3` (v0.2.0 작성 때 HEAD `7264f6c`에서 잰 고정값, research P20)
  3. `grep -c` 로 `backend/goose_harness_src/harness-instructions.md`에서 다음 문자열이 각각 1회 이상: `runs/<job_id>/dart/index.json`, `viewer_url`, `direct_read`, `read_scope`, `서버 사전 수집본으로 열람`, `"derived"`, `channel: "dart"`, `query`, `note`, `filing_coverage`, `review_or_audit`, `5번 규칙`, `서브에이전트`
  4. 서버 재시작 뒤 첫 작업이 `error`/`integrity`가 아니고, `shasum -a 256 ~/.goose-harness/CLAUDE.md`가 `shasum -a 256 backend/goose_harness_src/harness-instructions.md`와 같다
  5. 실행 중인 서버가 새 코드·새 지침을 쓰고 있다: `ps -o lstart= -p <uvicorn PID>`로 얻은 프로세스 시작 시각이 `git log -1 --format=%cI -- backend/goose_harness_src/harness-instructions.md backend/services/goose_job_service.py backend/services/goose_dart_prefetch.py`(마지막 변경 커밋 시각)과 세 파일의 `stat -f %m` 수정 시각보다 모두 늦다
- 잡는 구현: (a) 지침만 고치고 매니페스트 재생성 누락 → 1 실패(재시작하면 운영에서 모든 작업이 무결성 실패), (b) 권한 파일에 허용 규칙 추가 → 2 실패, (c) 규칙 일부 누락 → 3 실패, (d) 재시작 누락 → 4의 해시 불일치(설치는 서버 시작 때만 일어나므로) 그리고 5의 시각 역전. 재시작을 빠뜨린 서버는 무결성 오류 없이 옛 지침·옛 코드로 돈다(plan.md M4 주의) — 이 상태를 드러내는 것은 4·5뿐이다
- 잡지 못하는 것: goose가 규칙을 실제로 따르는지 — AC-016

### AC-AIR5-014 — 테스트 격리 (REQ-AIR5-015)

- Given: `backend/tests/conftest.py`(신규, plan T12)의 네트워크 가드 — 테스트 파일 이름(`Path(request.node.fspath).name`)이 `test_goose_` 또는 `test_main_goose`로 시작하는 모든 테스트에서 `socket.socket.connect`·`socket.socket.connect_ex`·`socket.create_connection`·`socket.getaddrinfo`를 대체한다. 대체 함수는 **원래 함수를 부르지 않고** 시도(대상 주소)를 목록에 기록한 뒤 예외를 던진다. 같은 conftest의 자동 픽스처가 각 테스트 종료(teardown) 때 기록이 비었는지 단언하고, 아니면 `network attempt in goose test: <기록>`으로 실패시킨다. 이 실패는 테스트 본문 밖에서 일어나므로 코드가 예외를 삼켜도(REQ-AIR5-010 fail-open, httpx의 `ExceptionGroup` 포장 포함) 사라지지 않는다. 새 수집기 테스트 모듈은 추가로 `HOME`과 `AI_REPORT_GOOSE_HARNESS_DIR`을 임시 폴더로 바꾼다. 범위를 모듈 이름(`request.module.__name__`)으로 판정하면 안 된다 — `backend/tests/__init__.py`가 있어 pytest가 모듈을 `backend.tests.test_goose_*`로 이름 붙이므로 접두어 검사가 아무 테스트에도 걸리지 않는다(plan-audit 3회차 R3-1)
- When:
  1. `before=$(ls ~/.goose-harness/runs | wc -l; stat -f %m ~/.goose-harness/runs)`
  2. `PATH=/usr/bin:/bin PY -m pytest backend/tests/test_goose_dart_prefetch.py backend/tests/test_goose_job_service.py backend/tests/test_goose_router.py backend/tests/test_goose_storage.py backend/tests/test_goose_runner.py backend/tests/test_goose_harness.py backend/tests/test_main_goose_lifespan.py -q`
  3. `after=…`(1과 같은 명령)
  4. 가드 자체 검사 `test_air5_014_guard_records_attempt`: 로컬 주소 `("127.0.0.1", 9)`로 `socket.create_connection`을 부르고 그 예외를 일부러 삼킨 뒤, 기록 목록에 `("127.0.0.1", 9)`가 정확히 1건 있음을 단언하고 기록을 비운다(그래야 종료 단언이 통과한다). 외부 호스트 이름은 쓰지 않는다
- Then: 2가 전부 통과(`PATH`에 `claude`가 없어도 통과 = 실제 `claude` 실행 없음), 종료 단언 실패 0건, `before == after`, 4 통과
- 선행 조건: 되돌림 관측 (r1)~(r4) 전에 4(가드 자체 검사)를 먼저 단독 실행해 통과를 확인한다(`PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_014_guard -q`). 4가 통과하지 않으면 가드가 꺼진 것일 수 있으므로 (r1)·(r2)를 실행하지 않는다 — 꺼진 가드 아래에서는 실제 DNS·DART 연결이 일어난다.
- 되돌림 관측(필수). 각 RED 출력 원문을 `progress.md §E.2`에 남기고 복원 후 `git status --short`로 확인한다. 가드는 원래 함수를 부르지 않으므로 되돌림 중에도 실제 연결·DNS 조회는 일어나지 않는다:
  - (r1) 수집기 테스트 하나에서 `MockTransport` 주입을 빼고 실행 → 수집기가 실패를 `error`로 기록하고 정상 반환하더라도 그 테스트가 `ERROR at teardown` + `network attempt in goose test: [...dart.fss.or.kr...]`로 RED
  - (r2) `GooseJobService` 생성자의 수집기 기본값을 실제 DART 수집기로 바꾸고 `backend/tests/test_goose_job_service.py` 실행 → 수집기 없이 서비스를 만드는 기존 테스트(`:105`·`:254` 경로)가 작업 자체는 `done`으로 끝나도 `ERROR at teardown` + `network attempt in goose test`로 RED
  - (r3) conftest의 종료 단언 픽스처만 끄고 (r1)을 다시 실행 → 해당 테스트가 통과(GREEN)해 버림을 관측. 이것이 "예외만 던지는 가드는 fail-open에 삼켜진다"(plan-audit 2회차 N1)의 실측이며, 종료 단언이 꼭 필요하다는 증거다. 이때도 기록·대체 함수는 살아 있으므로 실제 연결은 없다
  - (r4) 대체 함수가 기록을 남기지 않게 바꾸고 4 실행 → 기록 0건으로 RED
- 잡는 구현: (a) 테스트가 실제 DART에 접속하려 함 → 종료 단언 실패, (b) 생성자 기본값이 실제 수집기 → (r2)대로 기존 테스트 RED, (c) 가드가 예외만 던지고 기록하지 않음 → (r3)에서 드러나듯 fail-open이 삼켜 GREEN이 되므로 이 설계 자체가 금지됨(4가 기록을 요구), (d) 테스트가 기본 하네스 경로를 씀 → `runs` 개수·시각 변화, (e) 가짜 실행기 대신 실제 실행기 → `PATH`에 `claude`가 없어 `binary_missing`으로 실패
- 잡지 못하는 것: goose와 무관한 백엔드 테스트의 네트워크 사용(가드 범위 밖 — plan T12), 소켓을 거치지 않는 외부 접근(하위 프로세스 등 — 4의 가짜 실행기 구성과 `PATH` 제한이 맡음)

### AC-AIR5-015 — 기존 goose 회귀 (REQ-AIR5-001)

- Given: 변경 완료 트리
- When: `PY -m pytest backend/tests/test_goose_harness.py backend/tests/test_goose_job_service.py backend/tests/test_goose_runner.py backend/tests/test_goose_storage.py backend/tests/test_goose_router.py backend/tests/test_main_goose_lifespan.py -q` 그리고 `npm --prefix frontend run test`
- Then: 백엔드 실패 0, 통과 개수는 run 단계 M3 착수 전 같은 명령으로 잰 기준선 이상. 프론트는 실패 파일 집합이 기준선과 같거나 그 부분집합이고 통과 테스트 수가 기준선 이상. v0.2.0 작성 때 잰 프론트 기준선: `Test Files 1 failed | 96 passed (97)`, `Tests 840 passed`, 실패 파일은 이 SPEC과 무관한 `e2e/preset-flow.spec.ts`(research P16) — M3 착수 전에 다시 잰 값을 기준선으로 쓴다(lessons #10)
- 잡는 구현: (a) 단계 목록을 고정한 기존 테스트 2개를 갱신하지 않음 → `gooseJob.test.ts`·`ProgressPanel.test.tsx` 실패, (b) 수집기 추가로 기존 이벤트 순서 단언이 깨짐(수집기 없는 기본값이 아닌 경우) → `test_goose_job_service.py` 실패

### AC-AIR5-016 — 라이브 관측 검사 (REQ-AIR5-016)

라이브 관측 게이트다. 통과해야 SPEC을 닫는다(§F). goose(모델)의 판단에 달려 있으므로 같은 KST 날짜에 020150으로 최대 2회 실행할 수 있다. 1·2·3은 두 실행 중 하나가 모두 만족하면 되고, 4·5는 **실행한 모든 회차**에서 만족해야 한다.

- Given: M4 반영 후 서버 재시작과 AC-013 #4·#5 통과, 기준선 research.md §2(같은 종목 이전 실행에서 대상 6종 전부 발생)
- When: 앱에서 020150으로 goose 작업을 실행하고 끝까지 기다린다. 452190은 선택 관측(게이트 아님)
- Then (작업과 같은 KST 날짜에 확인):
  1. 작업 `status: done`, `delivery_status: draft`
  2. `runs/<job_id>/dart/index.json`: `outcome == "complete"`, `request_count <= 40`, `finished_at - started_at <= 120초`, `ok` 항목에 재무제표 9개·주석 1개·요약재무정보 1개·첨부 1개 이상
  3. `python3 -I ~/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input ~/.goose-harness/runs/<job_id>/draft/report-input.json --output "$S/audit.json"`의 결함 코드 집합과 `{DART_BODY, DART_NOTES, DART_REVIEW_OR_AUDIT, LATEST_SEARCH_DART, QUARTER_HISTORY, ANNUAL_HISTORY}`의 교집합이 공집합. (`REVIEW_*` 코드는 `--review`를 주지 않으면 항상 나오므로 판정에 쓰지 않는다 — `draft` 판정은 1이 맡는다)
  4. 출처 대조: 초안 입력의 `sources` 중 호스트가 `dart.fss.or.kr`이고 `verification == "direct_read"`인 것마다 (i) `url`이 색인 `ok` 항목의 `viewer_url` 집합에 있고, (ii) `read_scope`에 그 항목의 `text_file` 이름이 들어 있고, (iii) `limitations`에 `서버 사전 수집본으로 열람`이 들어 있다. 위반 0건
  5. `filing_coverage` 대조(spec.md §4.8): `body`·`notes`·`review_or_audit` 각각에서 `status == "read"`인 항목의 `source_ids`가 가리키는 출처가 모두 그 항목에 허용된 색인 구간(§4.8 표)의 `viewer_url`이다. 예: `body`의 `source_ids`에 주석·첨부 출처가 있으면 위반. 위반 0건
- 실패 시 기록: 2 실패 → 수집 결함, 2 통과·4 또는 5 위반 → 지침 미준수(사실과 다른 열람 기록), 2·4·5 통과·3 실패 → 남은 결함 코드와 해당 입력 필드를 그대로 기록. 어느 경우든 SPEC은 닫지 않고 manager-spec 재위임으로 지침·구간을 고친 뒤 다시 잰다
- 잡는 구현: 수집은 되지만 지침이 없어 goose가 파일을 안 읽음 → 3 실패, 지침이 출처 URL을 로컬 경로로 적게 함 → `read_ids(dart=True)` 실패로 3 실패, 검색 기록에 `query`·`note`가 비거나 `searched_at`이 시간대 없는 값 → `LATEST_SEARCH_DART`로 3 실패, goose가 연 적 없는 구간으로 `filing_coverage`를 채움 → 5 실패, 서버 사전 수집본 표기 누락 → 4(iii) 실패
- 잡지 못하는 것: goose가 파일을 열었다고 적고 실제로는 일부만 읽은 경우(스트림 기록을 보존하지 않으므로 기계 검증 불가 — Gap으로 명시)

## §D 경계 사례

| 사례 | 기대 동작 | 담당 AC |
|---|---|---|
| 신규 상장으로 정기보고서가 9개 미만 | 있는 것만 수집, `outcome=="complete"`, goose 쪽에서 분기 부족 결함은 남을 수 있음 | AC-006(합성 목록 1건 추가 권장), 라이브 비게이팅 |
| 같은 기간 정정 공시 | 최신 접수 하나 | AC-006 |
| 연결 재무제표 없는 회사 | 별도 기준, `basis="separate"` | AC-007 |
| 주석 구간 0.5MB 수준 | 정상 저장(상한 8MB) | AC-011 |
| DART 일시 장애 | `failed`/`partial` 후 goose 진행 | AC-010 |
| 서버 종료 중 수집 | `cancelled` | AC-002 |
| 끄기 스위치 | 요청 0, `disabled` | AC-004 |

## §E 품질 게이트

- 새 수집 모듈 줄 커버리지 85% 이상. 측정은 `coverage run --source=backend -m pytest <파일>` → `coverage report` (lessons #9의 커버리지 측정 함정)
- `ruff check` 새 경고 0(기준선 대비)
- 대조 항목은 되돌림 RED 관측 후에만 GREEN 기록(§A)
- @MX: 수집 모듈의 외부 시스템 진입점에 `@MX:ANCHOR` 또는 `@MX:WARN`(네트워크·시간 예산), 주석 언어는 `code_comments: ko`

## §F 완료 정의

- AC-AIR5-001~015 통과(명령·출력·기준선을 `progress.md §E.2`에 원문으로)
- AC-AIR5-016 통과(라이브 관측 게이트 — 실패 기록만으로는 닫지 않는다)
- 매니페스트 재생성·서버 재시작·무결성 확인 완료(AC-013 #4·#5)
- `claude-settings.json` 무변경
- 이 SPEC 이후에도 goose 결과가 `draft`임을 sync 문서에 명시(t17 연결)
