# DART 픽스처 (SPEC-AI-REPORT-005 M1)

goose DART 사전 수집 모듈(M2 `backend/services/goose_dart_prefetch.py`) 테스트용 녹화·합성 HTML이다. 테스트는 이 파일을 `httpx.MockTransport`로 돌려줄 뿐 DART에 접속하지 않는다.

## 녹화 픽스처 (`recorded/`)

- 받은 때: 2026-10-21 11:46:27.901 ~ 11:46:36.758 (KST, +09:00). 요청별 시작 시각·상태·바이트·소요 시간은 `recorded/request_log.json`.
- 명령: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/dart/capture_dart.py backend/tests/fixtures/dart/recorded` (httpx 0.28.1, 리디렉트 추적 끔, 브라우저형 User-Agent, 요청 시작 간격 1.1초 이상, 호스트 `dart.fss.or.kr`만).
- 요청 수: 성공 9회 + 중단 1회 = 10회. 11:45 KST 1차 실행에서 첫 POST가 폼 직렬화 오류(httpx가 튜플 목록을 거부)로 본문 전송 중 중단됐다(응답 없음, 파일 없음). 상한 10회에 이 1건을 포함해, 2차 실행은 9회로 줄이고 사업보고서 감사보고서 본문 구간은 받지 않았다.
- 응답은 바이트 그대로 저장했다(CRLF 포함). 합성 픽스처는 이 바이트에서 만든다.

| 파일 | 요청 | 바이트 | 내용 |
|---|---|---|---|
| `list_020150_recent.html` | `POST /dsab007/detailSearch.ax` (`textCrpNm=020150`, `publicType=A001·A002·A003`, `startDate=20231021`, `endDate=20261021`, `finalReport=recent`, `maxResults=100`, `sort=date`, `series=desc`) | 17,715 | 롯데에너지머티리얼즈 정기보고서 12행, 고유번호 전부 `00113997` |
| `main_20260814000373.html` | `GET /dsaf001/main.do?rcpNo=20260814000373` | 107,709 | 반기보고서(2026.06) 목차와 첨부 선택 목록 |
| `main_20260814000373_11527105.html` | `GET /dsaf001/main.do?rcpNo=20260814000373&dcmNo=11527105` | 40,574 | 반기연결검토보고서 목차(노드 4개) |
| `viewer_20260814000373_fs_consolidated.html` | `GET /report/viewer.do?rcpNo=20260814000373&dcmNo=11527102&eleId=19&offset=259834&length=178344&dtd=dart4.xsd` | 53,931 | `2. 연결재무제표` 구간 |
| `viewer_20260814000373_notes_consolidated.html` | `GET /report/viewer.do?rcpNo=20260814000373&dcmNo=11527102&eleId=24&offset=438182&length=1703030&dtd=dart4.xsd` | 492,989 | `3. 연결재무제표 주석` 구간 |
| `main_20260310002974.html` | `GET /dsaf001/main.do?rcpNo=20260310002974` | 116,351 | 사업보고서(2025.12) 목차와 첨부 선택 목록 |
| `viewer_20260310002974_summary.html` | `GET /report/viewer.do?rcpNo=20260310002974&dcmNo=11105315&eleId=18&offset=250218&length=25415&dtd=dart4.xsd` | 21,068 | `1. 요약재무정보` 구간(제39·38·37기) |
| `main_20260310002974_11105314.html` | `GET /dsaf001/main.do?rcpNo=20260310002974&dcmNo=11105314` | 42,309 | 연결감사보고서 목차(노드 5개) |
| `list_299030_recent.html` | `POST /dsab007/detailSearch.ax` (위와 같은 조건, `textCrpNm=299030`) | 17,271 | 하나기술 정기보고서 12행 — 정정 공시(F4) 관측용 |

출처 주소는 모두 `https://dart.fss.or.kr` + 위 경로다.

받지 않은 것(M2 테스트는 합성 본문으로 대신한다): 감사·검토보고서 본문 구간, 반기보고서 외 보고서의 재무제표 구간, 재무제표(별도) 구간.

## 합성 픽스처 (`synthetic/`)

`build_synthetic.py`가 녹화 픽스처를 문자열 단위로 고쳐 만든다(네트워크 없음, 다시 실행해도 같은 바이트). 실행: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/dart/build_synthetic.py`

| 파일 | 원본 | 바꾼 것 | 쓰는 AC |
|---|---|---|---|
| `list_020150_mixed_corp.html` | `list_020150_recent.html` | `20250814003923` 행의 고유번호만 `00999999` | AC-AIR5-005 (2) |
| `list_020150_correction.html` | `list_020150_recent.html` | `20250814003923` 행 앞에 `[기재정정] 반기보고서 (2025.06)` 행(`20250902000123`, 2025.09.02) 추가. 정정 표기 마크업은 `list_299030_recent.html`의 실제 표기를 따름 | AC-AIR5-006 (2) |
| `list_empty.html` | `list_020150_recent.html` | tbody의 행 전부 삭제. 실제 DART "결과 없음" 화면 마크업은 관측하지 않았다 | AC-AIR5-005 (3) |
| `main_20260814000373_no_consolidated.html` | `main_20260814000373.html` | `2. 연결재무제표`·`3. 연결재무제표 주석` 노드 블록(하위 노드 포함) 삭제 | AC-AIR5-007 (2) |
| `main_20260814000373_reordered.html` | `main_20260814000373.html` | `3. 연결재무제표 주석` 블록을 `2. 연결재무제표` 블록 앞으로 이동 | AC-AIR5-007 (4) |
| `main_20260814000373_polluted.html` | `main_20260814000373.html` | `2. 연결재무제표` 노드 값 `dcmNo="../1"`, `offset="1&x=y"`, `dtd="a/b"` | AC-AIR5-012 (2) |

## 색인 키 집합

`index_keys.json`이 acceptance.md §B의 `index.json` 고정 키 집합을 기계 판독용으로 담는다(AC-AIR5-009 집합 동등 검사용).

## 관측 메모 (M2 구현 참고)

- 첨부 선택 목록의 값은 `rcpNo=…&amp;dcmNo=…`처럼 HTML 엔티티로 들어 있고, 이름 앞에 `날짜&nbsp;`와 공백·개행이 붙는다.
- 사업보고서 첨부에는 `감사보고서`(별도, `11105293`)와 `연결감사보고서`(`11105314`) 외에 `감사의감사보고서`, `내부감시장치에대한감사의의견서`, `내부회계관리제도운영보고서`, `영업보고서`, `정관`이 함께 있다 — `감사보고서` 부분 일치로 고르면 `감사의감사보고서`를 잡을 수 있다.
- 사업보고서 연결감사보고서 목차는 `(첨부)연 결 재 무 제 표`, `주석` 뒤에 `외부감사 실시내용`(eleId 5) 노드가 하나 더 있다. `(첨부)` 앞 노드만 받으면 eleId 1·2다.
- 목차 노드 제목에는 글자 사이 공백이 들어간다(`감   사   보   고   서`, `(첨부)반 기 연 결 재 무 제 표`).
- 하나기술처럼 정정 사업보고서가 반기보고서와 같은 날 접수되면 목록 첫 행이 정정 사업보고서(2025.12)이고 둘째 행이 반기보고서(2026.06)다 — 목록 순서는 접수 순이지 기간 순이 아니다.
