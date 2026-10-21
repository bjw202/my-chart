# SPEC-AI-REPORT-005 — 조사 기록

작성: manager-spec, 2026-10-21. 이 문서의 모든 코드베이스·DART 사실 주장은 아래 프로브 표에 명령과 결과를 함께 둔다(lessons #10). "관측"은 이번 세션에서 명령을 실행해 본 것, "추론"은 관측에서 끌어낸 것으로 run 단계 M1에서 확인해야 하는 것이다.

## 1. 문제의 뿌리

goose 스킬은 한국 기업 전체 보고서에 DART 원문 열람을 요구한다.

- `research-contract.md:11` — "회사 실적 발표·정기 공시·회계 주석·첨부 검토/감사보고서 … DART 본문 확인과 첨부 검토보고서 확인을 구별합니다."
- `delivery-audit.md:9` — "한국 기업의 전체 보고서는 DART 정기보고서 본문, 관련 주석, 첨부 검토·감사보고서를 직접 읽습니다. … 끝내 접근하지 못하면 초안으로 남깁니다."
- `audit_report.py:20-27` `read_ids(ids, dart=True)` — 출처가 `verification == "direct_read"`, `read_scope` 비어 있지 않음, URL 호스트가 `dart.fss.or.kr`(또는 그 하위 도메인)이어야 통과.
- `audit_report.py:52-57` — `filing_coverage`의 `body`·`notes`·`review_or_audit` 각각에 대해 위 조건이 안 되면 `DART_BODY`/`DART_NOTES`/`DART_REVIEW_OR_AUDIT`.
- `audit_report.py:40-50` — 한국 기업 전체 보고서는 `dart` 채널 최신 검색 기록(조사 마감 전 24시간 이내, `result: read` + 직접 열람 출처)이 없으면 `LATEST_SEARCH_DART`.
- `audit_report.py:62-79` — 분기 원장은 6개 이상 연속, DART 직접 열람 출처, `status` `filed`/`derived`여야 하며 아니면 `QUARTER_HISTORY`. 연간은 최근 3개 연속 연도(조사 연도 미만, 최신이 조사 연도−2 이상)여야 하며 아니면 `ANNUAL_HISTORY`(연간 쪽 `read_ids`는 DART 호스트를 요구하지 않음).
- `audit_report.py:95-103` — `visual` 감수 기록이 `pass`가 아니면 `REVIEW_VISUAL`. 브라우저 없는 하네스는 지침 7번에 따라 이것을 통과로 기록하지 않는다 → 이 SPEC 이후에도 `draft`.

goose의 도구는 `WebSearch`, `WebFetch`, `Agent`, `Skill`, 하네스 안 `Read`, `runs/` 아래 `Write`/`Edit`, 스크립트 2개만 허용된 `Bash`다(`claude-settings.json`). WebFetch는 GET만 하고 스크립트를 걷어 낸 본문을 돌려준다. DART 공시 목록은 POST이고, 보고서 목차의 구간 인자는 `main.do` 안 자바스크립트에 있으므로 goose 혼자서는 본문 URL을 만들 수 없다.

## 2. 기준선 — 지금은 6개 결함이 모두 난다

이전 라이브 실행 두 건의 초안 입력에 감사 스크립트를 다시 돌렸다(설치본 스크립트, 원본과 sha256 동일).

| 작업 | 종목 | DART 출처 | 분기/연간 행 | 감사 결함 중 이 SPEC 대상 6종 |
|---|---|---|---|---|
| `d0a64dfc…` | 020150 | `blocked` 1건 (`dsab007/main.do`) | 0 / 0 | `DART_BODY`, `DART_NOTES`, `DART_REVIEW_OR_AUDIT`, `LATEST_SEARCH_DART`, `QUARTER_HISTORY`, `ANNUAL_HISTORY` 전부 |
| `1d261a37…` | 452190 | `blocked` 1건 (`dart.fss.or.kr/`) | 0 / 0 | 위와 같음 |

두 작업 모두 `audit_report.py`를 실행하지 않고 끝났다(초안 폴더에 감사 JSON 없음). goose가 남긴 가정 기록: "페이지가 스크립트로 렌더링되어 목록이 비어 있었습니다"(d0a64 `assumptions.md:9`), "접수번호를 확보하지 못해 직접 읽지 못했습니다"(1d261 `assumptions.md:6`).

주의: `FRESHNESS_CUTOFF`와 `LATEST_SEARCH_*`는 감사 실행 시각과 조사 마감일을 비교하므로 다른 날 다시 돌리면 결과가 달라진다. 라이브 검증(AC-AIR5-016)은 작업과 같은 날(KST) 감사를 돌린다.

## 3. DART 접근 사실

| # | 사실 | 구분 | 근거 |
|---|---|---|---|
| F1 | 상세검색 POST `dsab007/detailSearch.ax`에 `textCrpNm=<6자리 종목코드>`와 `publicType=A001/A002/A003`을 주면 그 회사의 정기보고서만 최신순으로 온다 | 관측 2026-10-21 | P10: 020150 → 12행, 전부 롯데에너지머티리얼즈의 분기·반기·사업보고서(2023.09~2026.06), HTTP 200, 17,715 bytes |
| F2 | 결과 행마다 회사 고유번호가 `openCorpInfoNew('<8자리>', …)`로 들어 있다 | 관측 | P10: `00113997` |
| F3 | 행의 보고서명에 기간이 괄호로 있다(`반기보고서 (2026.06)`). 정정은 `[기재정정]` 접두로 표시된다 | 관측(출처 두 곳, 서로 다른 조회) | 기간 괄호 표기: P10(020150, 이번 세션 조회). 정정 접두: P10이 아니라 2026-10-20 증거 `list.html`(하나기술, 조회 조건 미기록, 정기보고서 외 공시도 섞인 목록) 4행 `[기재정정] 사업보고서 (2025.12)` |
| F4 | `finalReport=recent`를 준 조회에서 정정 전 원본이 목록에서 빠지는지 | 추론(미확인) | P10(020150, `finalReport=recent`)에는 정정 행이 0개였다. F3의 정정 행은 다른 회사·다른 조회 조건에서 나왔으므로 둘은 모순이 아니라 서로 다른 관측이다. 020150이 이 기간에 정정 공시를 낸 적이 있는지는 확인하지 않았다 → 선택 규칙은 "같은 기간이면 최신 접수"로 정해 두고, M1에서 정정 이력이 있는 회사의 목록을 `finalReport=recent` 유무로 각각 받아 확인한다. AC-AIR5-006의 접수번호 리터럴은 P10만으로 정해지며 F3·F4에 기대지 않는다 |
| F5 | `dsaf001/main.do?rcpNo=…`의 목차 노드(`text`, `rcpNo`, `dcmNo`, `eleId`, `offset`, `length`, `dtd`)가 `makeToc()` 자바스크립트에 문자열로 있다 | 관측 | P11: 020150 반기보고서 노드, 증거 `viewer.html` |
| F6 | 같은 보고서의 첨부(검토·감사보고서)는 `main.do` 첨부 선택 목록에 `rcpNo=…&dcmNo=…` 값으로 있고, 본문과 다른 `dcmNo`다 | 관측 | P11: `11527104` 반기검토보고서, `11527105` 반기연결검토보고서(본문 `11527102`) |
| F7 | 첨부 문서의 목차는 `main.do?rcpNo=…&dcmNo=<첨부>`로 열면 같은 형식으로 나온다. 검토보고서 노드는 `검토보고서` 본문 2개 뒤에 `(첨부)반기연결재무제표`, `주석`이 온다 | 관측 | P12: 노드 4개 |
| F8 | 사업보고서 첨부 감사보고서의 목차도 "감사인 보고서 본문 → `(첨부)` 재무제표" 순서인지 | 추론(미확인) | 반기 검토보고서 1건만 관측 → M1에서 최신 사업보고서 첨부로 확인 |
| F9 | `report/viewer.do?rcpNo&dcmNo&eleId&offset&length&dtd`는 스크립트 없는 HTML이고 숫자가 본문에 그대로 있다 | 관측 | P13: 연결재무제표 구간 53,931 bytes, `<script` 없음, `영업이익(손실) (16,896,328,507) (21,876,790,670) …` |
| F10 | 연결재무제표 주석 구간은 크다 | 관측 | P13: 492,989 bytes, 태그 제거 텍스트 약 4.9만 자 |
| F11 | 반기·3분기 보고서 손익계산서에는 3개월과 누적 열이 함께 있다 | 관측 | P13: 매출액 `194,197,979,593`(3개월) `354,046,661,102`(누적) |
| F12 | 응답 시간은 요청당 0.1~0.25초 | 관측 | P11·P13 `time_total` |
| F13 | 반기보고서 요약재무정보에 3개 시점(2026.6, 2025.12, 2024.12)이 있다 | 관측 | 증거 `summary.html` |
| F14 | 상장사 목록 화면은 목차에 `2-2. 연결 포괄손익계산서` 같은 하위 노드를 두기도 하고 두지 않기도 한다 | 관측 | 증거 `toc.txt`(하나기술: 하위 노드 있음), P11(롯데에너지머티리얼즈: 정규식이 하위 노드를 잡지 못함) → 하위 노드 대신 상위 `연결재무제표` 구간 전체를 받는다(T4) |

이번 세션 라이브 요청은 모두 6회다(공개 페이지, 읽기 전용, 사람 속도). 캡처는 세션 임시 폴더에만 있고 이 SPEC 폴더 밖 쓰기 금지 때문에 리포에 남기지 않았다. run 단계 M1이 §5 명령으로 픽스처를 다시 받는다.

## 4. 코드베이스 프로브 (주장 | 관측 방법 | 결과)

| # | 주장 | 관측 방법 | 결과 |
|---|---|---|---|
| P1 | 작업 시작 판정 4~8단계는 단일 잠금 안에 있고, 8단계가 작업 폴더 생성 → active 등록 → 쿼터 차감 → 백그라운드 태스크 생성 순 | `Read backend/services/goose_job_service.py` | `:235-260` `async with self._lock:` 안에서 `mkdir` → `_prune_runs` → `_active_job_id` → `consume()` → `create_task(self._run(job))` |
| P2 | `_run`은 실행기 호출만 `try`로 감싸고 `CancelledError`를 `cancelled`로 닫은 뒤 다시 던진다 | 같은 파일 | `:275-302` |
| P3 | 취소는 태스크 `cancel()` 후 `gather`로 기다린다, 서버 종료도 같은 경로 | 같은 파일 | `:372-387` |
| P4 | goose 권한 파일은 WebFetch·WebSearch와 스크립트 2개 Bash만 허용 | `cat backend/goose_harness_src/claude-settings.json` | allow 9개, deny 11개 |
| P5 | 하네스 지침은 현재 7개 규칙 | `Read backend/goose_harness_src/harness-instructions.md` | 17줄, 규칙 1~7 |
| P6 | 무결성 검사는 매니페스트 파일과 `.claude/` 아래만 본다 → `runs/<job_id>/dart/`는 검사 대상 밖 | `sed -n 173,196p backend/services/goose_harness.py` | `verify_installed`가 매니페스트 항목과 `harness_dir/.claude` 트리만 순회 |
| P7 | 현재 매니페스트는 원본 재생성 결과와 같다(기준선) | `python -m backend.services.goose_harness > tmp; diff -q tmp backend/goose_harness_src/goose-manifest.json` | 차이 없음(`MANIFEST_MATCHES_SOURCE`) |
| P8 | HTTP 클라이언트: `httpx`는 런타임 의존성으로 이미 있고(0.28.1 설치), 앱 코드는 아직 import하지 않는다. `requests`(동기)는 크롤러들이 쓴다. `bs4`·`lxml` 설치됨 | `grep -n httpx pyproject.toml`; `grep -rlnE "^\s*(import httpx|from httpx)" backend my_chart`(0건, tests 제외); `python -c "import httpx,requests,bs4,lxml"` | `pyproject.toml:33 "httpx>=0.27.0"`, 버전 `0.28.1 2.32.5 4.14.3`, `lxml ok`; requests 사용처 `backend/services/naver_theme*/…`, `my_chart/krx_session.py` 등 |
| P9 | 프론트는 알 수 없는 진행 단계를 무시한다 → 백엔드가 먼저 배포돼도 깨지지 않는다 | `sed -n 50,100p frontend/src/utils/gooseJob.ts` | `applyGooseStage`: `if (!isGooseStage(stage)) return prev`; 단계 목록 `GOOSE_STAGES` 10개, 표시 문구 `ProgressPanel.tsx:15-25` |
| P10 | (DART) 종목코드 검색 | `curl -X POST https://dart.fss.or.kr/dsab007/detailSearch.ax --data-urlencode textCrpNm=020150 -d "currentPage=1&maxResults=100&maxLinks=10&sort=date&series=desc&startDate=20231021&endDate=20261021&publicType=A001&publicType=A002&publicType=A003&finalReport=recent"` | `200 17715`, 12행(§5에 접수번호) |
| P11 | (DART) 목차·첨부 | `curl "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260814000373"` | `200 107709 0.19s`; 첨부 `dcmNo=11527104`(반기검토보고서), `11527105`(반기연결검토보고서); 노드 `1. 요약재무정보 11527102/18/233941/25639`, `2. 연결재무제표 …/19/259834/178344`, `3. 연결재무제표 주석 …/24/438182/1703030`, `4. 재무제표 …/58/2141216/124954`, `5. 재무제표 주석 …/63/2266174/1375036`, dtd 모두 `dart4.xsd` |
| P12 | (DART) 첨부 목차 | `curl "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260814000373&dcmNo=11527105"` | `200 40574`; 노드 `검  토  보  고  서 /1`, `반기연결재무제표 검토보고서 /2`, `(첨부)반 기 연 결 재 무 제 표 /3`, `주석 /4` |
| P13 | (DART) 본문 구간 | `curl ".../report/viewer.do?rcpNo=20260814000373&dcmNo=11527102&eleId=19&offset=259834&length=178344&dtd=dart4.xsd"` 및 `eleId=24` 주석 | 재무제표 `200 53931 0.11s text/html; charset=utf-8`, 주석 `200 492989 0.23s` |
| P14 | 이전 실행의 DART 상태와 감사 결함(§2) | `python3 -I ~/.goose-harness/.claude/skills/goose/workflows/fact-check/scripts/audit_report.py --input ~/.goose-harness/runs/<id>/draft/report-input.json --output <scratch>/audit.json` | 두 작업 모두 대상 6종 발생, 종료 코드 2 |
| P15 | 설치본 감사 스크립트 = 리포 원본 | `shasum -a 256` 두 파일 | 둘 다 `4297d90e…a3f95` |
| P16 | (v0.2.0) 프론트 goose 테스트 명령이 테스트를 찾는다 | `npm --prefix frontend run test -- gooseJob ProgressPanel` | `Test Files 2 passed (2)`, `Tests 12 passed (12)`. 전체 `npm --prefix frontend run test`는 `Test Files 1 failed | 96 passed (97)`, `Tests 840 passed` — 실패 파일은 이 SPEC과 무관한 `e2e/preset-flow.spec.ts`(기존 기준선) |
| P17 | (v0.2.0) 무결성 검사는 원본을 다시 읽지 않는다 | `sed -n 296,307p backend/services/goose_harness.py` | `check_job_integrity()`는 시작 때 기록한 `_baseline_manifest`와 설치본만 `verify_installed`로 비교 |
| P18 | (v0.2.0) 기존 테스트가 수집기 없이 서비스를 만든다, 공용 conftest 없음 | `grep -n "GooseJobService(" backend/tests/*.py`; `ls backend/tests/conftest.py` | test_goose_job_service.py:105·254·492·526·553, test_goose_router.py:102·387, test_goose_storage.py:91; conftest 없음 |
| P19 | (v0.2.0) 단계 목록을 고정한 기존 프론트 테스트 | `grep -rn "goose_start" frontend/src` | `utils/__tests__/gooseJob.test.ts:50` `expect(GOOSE_STAGES).toEqual([...])`, `components/__tests__/ProgressPanel.test.tsx:31` |
| P20 | (v0.2.0) 권한 파일 기준 해시 | `shasum -a 256 backend/goose_harness_src/claude-settings.json`; `git diff --quiet HEAD -- …` | `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`, HEAD(`7264f6c`)와 차이 없음 |

## 5. 보고서 선택 계산 (020150, 2026-10-21 기준)

P10의 12행(최신순): `20260814000373` 반기(2026.06), `20260515000387` 분기(2026.03), `20260310002974` 사업(2025.12), `20251114002397` 분기(2025.09), `20250814003923` 반기(2025.06), `20250515002590` 분기(2025.03), `20250314001597` 사업(2024.12), `20241113000761` 분기(2024.09), `20240814000979` 반기(2024.06), `20240514001418` 분기(2024.03), `20240315000794` 사업(2023.12), `20231114000877` 분기(2023.09).

최신 9개 기간을 고르면 앞의 9행이다. 이것으로 만들 수 있는 분기: 2026-Q2, Q1, 2025-Q4(사업 2025 − 3분기 2025 누적), Q3, Q2, Q1, 2024-Q4(사업 2024 − 3분기 2024 누적), Q3, Q2 = 9개 연속. 8개만 고르면 창의 가장 오래된 보고서가 사업보고서일 때 그 해 3분기 누적이 없어 4분기를 못 만드는 경우가 생긴다(창 끝이 `20250314001597`이면 7개) — 9개로 정한 이유(plan T3).

연간: 사업보고서 2025·2024의 손익계산서가 각각 당기·전기를 담고, 최신 사업보고서 요약재무정보가 3개 회계연도를 담는다 → 2023·2024·2025 세 해. 감사의 연간 조건(조사 연도 2026 미만, 최신 ≥ 2024, 3개 연속)을 만족할 원문이 공급된다.

예상 요청 수: 목록 1 + 목차 9 + 재무제표 9 + 주석 1 + 요약재무정보 1 + 첨부 목차 2 + 첨부 본문 약 4 = 약 27회. 1초 간격이면 약 30~35초.

## 6. 픽스처 재수집 명령 (run 단계 M1)

§4 P10~P13의 명령 4종에 더해 최신 사업보고서(`20260310002974`)의 `main.do`, 그 첨부 감사보고서 `main.do`(F8 확인), 그 첨부 본문 1구간을 받는다. 요청 사이 1초 이상, 합계 10회 이하. 저장 위치는 테스트 픽스처 폴더이고, 받은 날짜와 명령을 픽스처 옆 README에 남긴다. 받은 목록이 §5와 다르면(예: 2026.09 분기보고서 접수) §5의 기댓값을 새 측정값으로 바꿔 `progress.md`에 기록한 뒤 선택 코드를 쓴다.

## 7. 위험

| 위험 | 영향 | 대응 |
|---|---|---|
| goose가 지침을 따르지 않거나 서브에이전트가 지침을 못 받음 | 수집본이 있어도 DART 결함이 남음 | 지침에 서브에이전트 전달 규칙(REQ-AIR5-013), 라이브 검증 AC-AIR5-016에서 실측 |
| DART 화면 구조 변경 | 목차 해석 실패 | fail-open(REQ-AIR5-010), 색인에 실패 사유가 남아 원인 확인이 쉬움 |
| DART가 서버 IP를 차단·제한 | 수집 실패 | 요청 간격·상한(REQ-AIR5-011), fail-open |
| 큰 주석 구간이 goose 문맥을 많이 씀 | 토큰 증가 | 텍스트판 제공(약 4.9만 자, F10), goose는 필요한 부분만 읽음 |
| 정정 공시 처리(F4) | 오래된 수치 사용 | 같은 기간 최신 접수 선택(REQ-AIR5-006), M1 확인 |
| 작업 시간 증가 | 최대 120초 추가 | 예산 상한(REQ-AIR5-011), goose 시간 상한 900초와 별개 |
