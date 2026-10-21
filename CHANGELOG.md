# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed (Bump 마지막 점을 진행 중인 주의 잠정 순위로 — 2026-10-22)

- **Bump 차트가 진행 중인 주의 순위를 잠정점으로 그려, 마지막 순위가 표와 같아진다** — 표(`/api/sectors/ranking`)는 진행 중인 주 바(예: 2026-10-21, `as_of_is_partial_week=true`)로 순위를 매기는데, Bump(`/api/sectors/history`)는 끝난 주(2026-10-16)까지만 그려 마지막 순위가 표와 한 주 어긋났다. 이제 최신 주가 진행 중이면 그 날짜의 순위를 Bump가 쓰는 것과 같은 집계 호출(`compute_sector_aggregates`, 같은 기간·시장, 등가중 대체 포함)로 한 번 더 계산해 마지막 점으로 덧붙인다. 최신 주가 끝났으면 잠정점은 없다 (SPEC 없음 — 사용자 결정)
  - **백엔드** (`my_chart/analysis/sector_metrics.py`, `backend/services/sector_advanced_service.py`, `backend/schemas/sector_advanced.py`): `compute_sector_history_with_provisional`을 새로 두고 `compute_sector_history`는 그 앞 두 값(`(dates, rankings)`)을 돌려주는 얇은 함수로 남겼다. 응답에 `provisional_date`(없으면 `null`)와 `sectors[].history[].provisional`(기본 `false`)을 더했다. 잠정 날짜는 `sectors[].history` 끝에만 들어가고 `dates[]`·`rankings`·`span_days`에는 넣지 않는다 — `len(dates) == weeks`(AC-SAG-040)와 "최근 N개 끝난 주"라는 기존 의미를 지키려는 선택이다. 테스트에서 기준일을 고정할 수 있도록 히스토리 함수에 `as_of` 인자를 더했다(라우터는 넘기지 않아 오늘 기준)
  - **화면** (`frontend/src/api/history.ts`, `frontend/src/components/SectorAnalysis/BumpChart.tsx`): 마지막 끝난 점 → 잠정점 구간은 점선, 잠정점은 속 빈 기호로 그린다. x축 라벨은 `2026-10-21 (잠정)`, 툴팁에 `잠정 — 주 진행 중` 줄을 더하고, 기준 캡션은 `마지막 점 2026-10-21 잠정(주 진행 중)`으로 바뀐다. Top-N 필터와 섹터명 끝 라벨은 잠정점 순위를 따른다. 점선 구간은 같은 섹터 이름의 별도 시리즈라 클릭하면 표로 이동하고, 호버 시 실선·점선 두 조각을 함께 강조하도록 이름으로 강조 동작을 다시 보낸다
  - **테스트**: `tests/test_sector_history_provisional.py`(부분 주 픽스처 — 잠정점 순위가 같은 기준일·기간·시장의 표 `data[].rank`와 전 섹터 일치, 끝난 주 계약 유지, 주가 끝나면 잠정점 없음), `frontend/src/components/SectorAnalysis/__tests__/BumpChart.provisional.test.tsx`, `frontend/src/api/__tests__/history.test.ts` 보강
  - **라이브 대조 (2026-10-22, `period=1m`, `weeks=12`)**: 라이브 서버 표(as_of 2026-10-21, 부분 주)와 잠정점 순위가 `market=all` 29/29, `market=kosdaq` 29/29 일치. `dates[]`는 12개(마지막 2026-10-16), `span_days` 77 그대로

### Added (SPEC-AI-REPORT-006 v0.3.4 — Goose 후처리 감수: 서버 화면 캡처와 별도 감수 세션, 카드 t18, 2026-10-21)

- **goose가 만든 초안을 서버가 화면으로 찍고, 별도 `claude -p` 감수 세션이 그 화면을 보고 감수 기록을 쓴다** — 전달 감사기는 감수 기록(`review`)이 없으면 `AUDIT_*`·`REVIEW_*` 결함을 내는데, goose는 브라우저가 없어 화면을 볼 수 없고 감수 기록의 해시도 스스로 만들 수 없어 라이브 실행마다 초안(`draft`)에서 멈췄다. 이제 1차 세션이 끝나면 작업 서비스가 하네스 무결성 재검사 → 서버 화면 캡처 → 감수 세션 → 서버가 쓰는 영수증 순으로 이어서 실행하고, 영수증이 화면 확인을 인정할 때만 최종본(`final`)으로 전달한다. 후처리가 실패해도 초안은 그대로 전달된다 (`d8854c1` 캡처 모듈 · `83b327f` 감수 세션·영수증 · `86e4301` 작업 서비스·프론트 · `33e3c18` 하네스 규칙 10 · `bc56cc7` 보안 강화)
  - **캡처 모듈** (`backend/services/goose_screenshot.py`): Playwright 캐시의 `chrome-headless-shell`만 지원하고, 초안 `report.html`을 데스크톱·모바일 두 크기로 찍어 타일로 잘라 `runs/<job_id>/screens/`에 `index.json`과 함께 둔다(캡처 60초, 타일 30장 상한). 스크립트 실행과 외부 네트워크를 모두 막고 찍으므로 실제 화면과 조금 다르다
  - **감수 보조·영수증** (`backend/services/goose_review.py`, `backend/services/goose_runner.py`): 감수 세션은 모든 타일을 `Read`한 뒤 `audit-review.json`을 쓴다(900초 상한). 서버가 세션 종료 뒤 영수증 `review/receipt.json`을 직접 쓰고, 전달 판정은 영수증과 같은 단일 함수 한 곳에서 한다. 세션 전에 `review/`·`audit-review.json`·`final/`을 비운다
  - **작업 서비스·프론트** (`backend/services/goose_job_service.py`): 후처리 순서·진행 이벤트·취소·실패 시 초안 유지. `AI_REPORT_GOOSE_REVIEW=0`이면 캡처·감수를 하지 않고, `AI_REPORT_GOOSE_REVIEW_TIMEOUT`(초, 기본 900)으로 감수 시간을 바꾼다. `AI_REPORT_GOOSE_BROWSER`로 브라우저 실행 파일을 지정한다
  - **하네스 지침** (`backend/goose_harness_src/harness-instructions.md`, `backend/goose_harness_src/goose-manifest.json`): 1차 세션은 최종본을 만들지 않고(규칙 7 개정), 감수 규칙(규칙 10, 하위 항목 10-1~10-11)을 더했다. `claude-settings.json`(sha256 `e8b527cc…`)은 바꾸지 않았다
  - **보안 강화 (M7)**: 첫 보안 검토가 FAIL(높음 2건, 검증됨)이었다 — 초안 안 `file://` iframe이 로컬 파일 내용을 타일에 그렸고(S1), cross-site iframe/object/embed가 루프백으로 요청을 보냈다(S2). 캡처 모듈에 층 A1(Fetch로 모든 대상의 요청을 가로채 초안 URL과 `data:`만 통과), 층 A2(프록시 우회 차단 플래그), 층 B(서버가 문서에 붙이는 CSP), 허용 목록 환경(브라우저 자식 프로세스), `review/` 비우기를 넣었다. 수정 뒤 PoC1(비밀 문구를 심은 `file://` iframe)은 타일이 빈 칸이고 PoC2(루프백 수신)는 `HITS []`였다
  - **테스트** (`backend/tests/test_goose_screenshot.py`, `backend/tests/test_goose_review.py`, `backend/tests/test_goose_screenshot_live.py` 외): 가짜 드라이버·가짜 실행 파일로 돌리고, 실제 브라우저 시험 4개는 `AI_REPORT_GOOSE_REAL_BROWSER_TESTS=1`일 때만 켜진다
- **검증**: AC-AIR6-001~022 22개. 라이브 게이트 AC-AIR6-018은 1회차 통과(작업 `0ffb8f9e…`, 020150, 5개 판정 항목 충족, 전달은 `draft`). goose 회귀 `565 passed, 4 skipped, 214 deselected`(격리 실행). 네 모듈 라인 커버리지 96%(job_service 96 · review 95 · runner 97 · screenshot 96, M7 이후 재측정). ruff 통과, tsc 0, eslint 0, vitest 702 passed(M4 시점). 매니페스트 재생성 결과 동일, 독립 보안 재검토 PASS(`.moai/reports/t18/security-rereview.md`, 해결되지 않은 높음 없음)
- **알려진 한계** (근거 등급): (a) conftest에 하네스 경로 격리가 없어 lifespan을 도는 테스트가 실제 `~/.goose-harness`를 덮어쓸 수 있음(후속 카드 후보, 리드 보고) · (b) 렌더러의 390px 모바일 차트 잘림을 라이브 감수가 찾음(제품 후속 후보) · (c) 라이브에서 `final` 인정 경로는 보지 못했다 — AC-018은 `draft`로 끝난 경로만 관측(미관측) · (d) AC-AIR6-004(b)·020(c)·022의 현재 모드 신선도 미관측 · (e) AC-AIR6-013 #5는 M6 시점에만 관측, 규칙 10-11 반영본의 재시작 뒤 무결성은 미관측 · (f) 감수 세션이 1차 세션과 같은 권한(`WebSearch`·`WebFetch`·`Agent`·`Skill`·`Write(./runs/**)`)을 갖고 규칙 10-11은 지침일 뿐 — 보안 재검토 F1 중간, 가설(`--disallowedTools` 좁히기가 후속) · (g) 하드링크·교체된 초안이 초안 검사를 통과함 — F2 낮음 검증됨, F3 낮음 가설(`ln`이 Bash 허용 밖이라 악용이 어렵고, 수정은 `O_NOFOLLOW`와 `st_nlink` 검사) · (h) DevTools 포트가 127.0.0.1에서 인증 없이 열림 — F4 낮음 검증됨(후속 `--remote-debugging-pipe`) · (i) 심은 `screens` 일반 파일이나 매우 큰 초안은 최종본 불인정으로 끝남 — F5 낮음 검증됨(안전한 쪽으로 실패) · (j) S7·S8 이월(가설) · (k) `Network.setBlockedURLs ["*"]`가 `data:` 이미지도 막아 감수자는 로고 같은 `data:` 이미지를 못 봄(검증됨, 제품 후속 후보) · (l) macOS의 `chrome-headless-shell` 153.0.8010.12 하나만 관측, Linux와 규칙 10-11이 모델 행동에 미치는 효과는 미관측 · (m) AC-AIR6-009 (6)(o)의 "이미지가 사라진다"는 (k) 때문에 관측 불가 · (n) AC-AIR6-014 (15)의 기대 목록은 심은 `audit-review.json` 유무에 따라 달라짐(SPEC 문구 후속) · (o) 브라우저 격리는 세션당 한 번 적용(SPEC의 뷰포트마다보다 엄격)
  - **sync 감사 반영 (sync-auditor 0.853 PASS-WITH-DEBT)**: (p) AC-AIR6-018 라이브 통과는 보안 강화(M7) 이전 빌드(main `2713402`)에서 관측했다. M7 반영본의 서버 재시작, 임시 완화 `AI_REPORT_GOOSE_REVIEW=0` 해제, 라이브 재관측은 리드가 병합 뒤 하며 아직 기록이 없다. 설치된 `~/.goose-harness`는 M7 이전 지침(`64ceebda…`)이고 저장소 지침은 `e5c3fd9b…`이다 · (q) `<meta refresh>`로 `file://`을 여는 초안은 캡처가 60초를 다 쓰고 `failed`로 끝난다(닫힌 쪽 실패, 재검토 F5와 같은 가용성 부류) · (r) 감수 세션의 S4(Bash 리다이렉트로 쓰기)와 S6(디버그 포트 경합)은 가설·코드 읽기 수준 이월이다
  - **근거**: `.moai/specs/SPEC-AI-REPORT-006/progress.md` §E.2~§E.4 · `.moai/reports/t18/security-rereview.md` · `.moai/reports/t18/sync-audit.md` · `.moai/reports/t18/run-evidence/live-m6/`

### Added (SPEC-AI-REPORT-007 v0.4.0 — Goose 네이버 최신 뉴스 사전 수집, 카드 t19, 2026-10-21)

- **goose 실행 전에 서버가 네이버 증권 최신 뉴스를 받아 둔다** — 전체 기업 보고서의 전달 감사는 `naver` 채널의 최근 검색 기록을 요구하는데, 라이브 실행 `a5becbb9`에서 goose가 네이버 접근을 `blocked`로 적어 `LATEST_SEARCH_NAVER` 결함이 남았다. DART 사전 수집(SPEC-AI-REPORT-005)과 같은 방식으로, 이제 작업 서비스가 goose 실행 직전에 네이버 모바일 뉴스 JSON API를 한 번 불러 `runs/<job_id>/naver/`에 기사별 텍스트 파일·원본 응답·`index.json`을 쓴다. goose 권한 파일은 바꾸지 않았다 (`871c105` 픽스처·응답 모양 관측 · `b28394c` 수집 모듈 · `9b4443f` 작업 서비스 연결 · `c16e1de` 하네스 규칙 9 · `ff9613e` 라이브 확인 기록)
  - **수집 모듈** (`backend/services/goose_naver_prefetch.py`): `https://m.stock.naver.com/api/news/stock/<code>?pageSize=10&page=1`에 작업당 `GET` 1회. 요청 전체(전송 + 본문 읽기) 10초 상한을 `asyncio.wait_for`로, 응답 2MB 상한을 선언 길이(본문 읽기 전 거부)와 스트리밍 누적으로 지킨다. 호스트는 `m.stock.naver.com`과 정확히 같아야 하고 리디렉트는 따라가지 않으며, 6자리 숫자가 아닌 종목코드는 요청 없이 거부한다. 응답은 그룹 배열이라 모든 그룹의 `items`를 펼쳐 앞 10건을 쓰고(그룹 `total`은 기사 수가 아니라 쓰지 않음), 제목·본문은 태그 제거 → HTML 엔티티 해제 → 앞뒤 공백 정리 순서로 평문화한다. 기사 주소는 검증한 `officeId`·`articleId`로 서버가 만들고(`https://n.news.naver.com/mnews/article/<officeId>/<articleId>`), 파일 이름도 서버가 만든다(`NN_article.txt`). 본문이 빈 기사는 `metadata_only`(파일 없음)
  - **색인 결과 판정** (`index.json`의 `outcome`): `disabled`(끄기 스위치) · `failed`(요청·해석 실패, 또는 항목은 있으나 `ok`가 하나도 없음) · `no_results`(펼친 기사 0건) · `complete`(모든 항목 `ok`) · `partial`(`ok`와 `metadata_only`/`error`가 섞임). 어떤 실패도 색인에 적고 정상 반환하며, 취소만 전파한다
  - **작업 서비스 연결** (`backend/services/goose_job_service.py`): DART 수집 뒤·하네스 무결성 재검사 앞에 네이버 수집을 부른다. 재검사는 수집기가 하나라도 주입되면 돈다. 수집기와 종목코드 확인 함수는 생성자 주입이며 기본값은 없음(운영 인스턴스에만 붙인다). `AI_REPORT_GOOSE_NAVER_PREFETCH=0`이면 수집하지 않고 `outcome: disabled` 색인만 쓴다. 진행 이벤트는 새로 만들지 않았다 — 화면은 기존 `공시 원문 수집` 단계 동안 이어서 수집하며 프론트 변경은 없다
  - **`code_validated`**: 존재하지 않는 종목코드도 API가 HTTP 200 + `[]`를 돌려주므로, 작업 서비스가 라우터와 같은 서버 종목 목록 조회(`get_stock_name`, 네트워크 없음) 결과를 색인에 `code_validated`로 남긴다. 확인 함수가 없거나 예외를 내면 `false`이고, 수집은 어느 경우에도 실행한다
  - **하네스 규칙 9** (`backend/goose_harness_src/harness-instructions.md`, `backend/goose_harness_src/goose-manifest.json`): goose가 `runs/<job_id>/naver/index.json`을 먼저 읽고, 실제로 연 `ok` 텍스트 파일만 `verification: direct_read` 출처로 적게 한다. 요약 본문을 출처로 인정하는 조건(사용자 결정): `read_scope`에 `모바일 뉴스 API 응답의 제목·요약 본문 필드`, `limitations`에 `서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음`과 `API 요약본(약 150자), 원문 미확인`을 함께 적고, `요약에 없는 사실은 단정하지 않는다`. `naver` 검색 기록은 `ok` 파일을 연 경우에만 `read` 한 건, 색인이 `no_results`일 때만 `no_results`(`code_validated`가 거짓이면 `서버가 종목코드 유효성을 확인하지 못함`을 `note`에 적음)로 쓰고, 그 밖에는 기존 경로로 시도한 실제 결과를 적는다 — 막힘을 `read`·`no_results`로 바꿔 적지 않는다. 매니페스트는 재생성했고 권한 파일 `claude-settings.json`은 바이트 단위로 그대로다
  - **테스트** (`backend/tests/test_goose_naver_prefetch.py`, `backend/tests/test_goose_job_service.py`, 픽스처 `backend/tests/fixtures/naver/`): 녹화 응답(020150·000040·999999)과 합성 픽스처 15종을 `httpx.MockTransport`로 돌린다. 파일 이름이 `test_goose_`로 시작해 기존 네트워크 가드가 외부 연결 시도를 RED로 드러낸다
- **검증**: AC-AIR7-001~015 15개 모두 PASS(AC-AIR7-012는 라이브 1회차, 나머지 14개는 run 레인 자동 테스트). 새 수집 모듈 라인 커버리지 97%(201문 중 7 누락). 되돌림 대조(lessons #9)로 틀린 구현을 넣어 RED를 관측한 것이 M2 24건·M3 12건. goose 회귀 `330 passed`(기준선 267 + 새 63)
  - **라이브 (2026-10-21, 롯데에너지머티리얼즈 020150, 작업 `11808900…`)**: 색인 `outcome=complete`, 요청 1회, 기사 10건 모두 `ok`, `code_validated=true`. 감사 결함에서 `LATEST_SEARCH_NAVER`가 사라졌고(기준선 `a5becbb9`에는 있었음), 기록 검사 스크립트 `violations 0`·`mode 3F+3S`. goose는 `ok` 10건 중 4건을 열었다고 적었고 모두 약 150자 요약본이라고 밝혔다
- **알려진 한계**: (a) 서버가 받는 본문은 기사 전문이 아니라 API가 주는 약 150자 요약이다. 기사 원문 페이지 수집은 범위 밖이며, 보고서가 요약에 없는 사실을 단정하는지는 기계로 검사하지 않는다 · (b) 비공식 모바일 API라 예고 없이 바뀔 수 있다 — 바뀌면 `failed`로 기록되고 goose는 기존 방법으로 돌아가며 `LATEST_SEARCH_NAVER`가 다시 남는다(조용한 통과는 없음) · (c) 라이브 회차에서 `company_ir` 채널 기록이 없어 `LATEST_SEARCH_COMPANY_IR` 결함이 새로 나왔다(기준선 `a5becbb9`에는 `company_ir` `read` 기록이 있었음). 규칙 9의 부작용인지 실행마다 달라지는 변동인지는 두 번째 실행을 하지 않아 관측하지 못했다(progress.md O-AC12-1) · (d) 결과물은 여전히 `draft`다 — 남은 `AUDIT_*`·`REVIEW_*` 결함은 카드 t18(SPEC-AI-REPORT-006) 소관 · (e) 서버 종목 목록은 고정 엑셀 표라 상장 폐지됐지만 목록에 남은 종목은 `code_validated=true`로 `no_results`가 될 수 있다 · (f) 호출 제한·약관은 관측하지 않았고, `ruff`가 이 환경에 없어 실행하지 못했다 · (g) conftest에 하네스 경로 격리가 없어 lifespan을 도는 테스트가 실제 `~/.goose-harness`를 덮어쓸 수 있음(후속 카드 후보)
  - **근거**: `.moai/specs/SPEC-AI-REPORT-007/progress.md` §E.2~§E.4 · `.moai/reports/t19/run-evidence/`

### Added (SPEC-TEST-HERMETIC-001 v0.1.0 — 백엔드 pytest 스위트 허메틱화, 2026-10-21)

- **프로덕션 DB 없는 환경에서 백엔드 테스트 전체가 통과한다** — 새 git 워크트리에는 gitignored 프로덕션 DB(`Output/stock_data_weekly.db`·`stock_data_daily.db`)가 없어 프론트엔드만 수정한 카드의 커밋도 백엔드 테스트 약 20건 실패로 차단됐다. 원인은 게이트가 아니라 스위트 자체가 비-허메틱인 것이었고, 테스트 계층만 고쳐 워크트리 DB 복사 워크어라운드 없이 pre-commit 게이트가 통과하도록 만들었다. 백엔드 프로덕션 코드 변경은 0건이다 (`eb0b6be` 코드 · `19279f9` 증거 문서)
  - **허메틱 DB 경로 패치 픽스처** (`tests/conftest.py`): autouse `hermetic_db_paths` 픽스처가 `backend.routers` 패키지 전체를 순회해 모든 라우터 모듈이 갖고 있는 `WEEKLY_DB_PATH`·`DAILY_DB_PATH` 모듈 상수(라우터별 복사본 — `backend.deps`만 패치해서는 무효)를 tmp_path 산하 경로로 대체한다. 경로 대체만 수행하고 DB 파일을 만들지 않으므로, DB 내용이 필요한 테스트는 기존 `daily_db`/`weekly_db` 픽스처를 그대로 명시 요청한다. 모듈이 추가돼도 순회로 자동 포함된다
  - **기존 픽스처 패치 갭 2곳 수선** (`tests/test_market_api.py`, `tests/test_response_contract.py`): `test_client` 픽스처의 `DAILY_DB_PATH` 미패치(market/stage daily 조회 12건+1건 실패 원인)와 `client` 픽스처의 `stage.DAILY_DB_PATH` 미패치(4건 실패 원인)를 메웠다
  - **M1 RED 실측 4건 진단·해소** (`tests/test_m6_gap_closure.py`): `stock_meta` 부재 시 `config` 파생 `DEFAULT_DB_DAILY` 폴백 경로를 패치. 정적 분석으로 미설명이던 실패는 관측된 트레이스백으로 원인을 확정한 뒤에만 수정했다(관측된 RED 없는 결함 주장 금지 원칙). `test_ac_sag_045_r1_r4_r5a.py` 1건은 DB-less 실측에서 재현되지 않았다
  - **검증 테스트 신설** (`tests/test_hermetic_db_patch.py`): 라우터 전 모듈 순회로 패치 커버를 단언하는 테스트와 config 파생 상수 커버 테스트. 되돌림 RED 실측(autouse 비활성화 → 2 failed, 종료 코드 1 → 복원 후 2 passed)으로 각 테스트가 패치 누락을 실제로 잡는지 확인했다
  - **게이트 실측 (AC-007/008)**: `moai gate` 실측 결과 이 저장소에서는 Python test 단계만 트리거되고 vitest는 실행되지 않음(루트 `package.json`/`tsconfig.json` 부재) — `frontend/vite.config.ts`는 변경 없음(no-op 분기)
- **검증**: AC-001~AC-010 10개 모두 PASS. DB-less 워크트리 전체 스위트 `1089 passed, 1 skipped, 95 deselected, 1 xpassed`, 종료 코드 0(`0 failed`); 수정 전 동일 환경 RED `20 failed`(M1 실측). 정상 환경 기준선 대비 신규 실패 0·신규 skip 0. 워크트리 실행 후 `Output/`의 `.db` 생성 0건. ff-merge 후 주 체크아웃(실 DB 존재)에서 동일 스위트 재실행도 `1089 passed, 1 skipped, 95 deselected, 1 xpassed`, 종료 코드 0으로 회귀 없음 확인. 되돌림 대조(프로젝트 교훈 #9)로 핵심 AC의 되돌림 RED를 관측했다
  - **근거**: `.moai/specs/SPEC-TEST-HERMETIC-001/progress.md` §E.2~§E.4 · `evidence/`(m0-baseline, m1-red-observations, m3-unexplained-diagnosis, m4-gate-measurement) · `.moai/state/verify/develop-hermetic/` · `.moai/state/verify/41724e22-orch/post-merge-main-suite.log`
- **알려진 한계**: conftest autouse 순회는 테스트 중 최초 임포트 시점의 모듈만 볼 수 있어, 스위트 어디서도 임포트되지 않는 신규 라우터는 미패치로 노출될 수 있다(현 스위트는 `backend.main` 경유 전수 임포트라 영향 없음 — 최종 전체 GREEN이 실측 보장). `moai gate`는 성공 시 무출력 설계라 단계 이름 목록은 설정 선언+시간 실측으로 구성했다

### Added (SPEC-AI-REPORT-005 v0.3.1 — Goose DART 원문 사전 수집, 2026-10-21)

- **goose 실행 전에 서버가 DART 정기보고서 원문을 받아 둔다** — goose의 WebFetch로는 DART 공시 원문(목록 POST 조회, 자바스크립트로 그리는 목차)을 읽지 못해 리포트가 DART 미확보 결함을 안고 초안으로 끝났다. 이제 작업 서비스의 백그라운드 태스크가 goose 실행기를 부르기 직전에 수집기를 불러 `runs/<job_id>/dart/`에 원본 HTML·텍스트판·`index.json`을 쓴다 (`d72a1e1` 픽스처 · `06fb05f` 수집 모듈 · `93b5ed5` 작업 서비스 연결 · `91b904e` 하네스 지침 · `c1076ec` 라이브 증거)
  - **수집 모듈** (`backend/services/goose_dart_prefetch.py`): 인증키 없는 DART 공개 화면에서 최근 3년 사업·반기·분기보고서를 검색해 최신 9개 기간을 고른다. 기간마다 재무제표 구간, 가장 최근 보고서의 재무제표 주석, 가장 최근 사업보고서의 요약재무정보, 이 두 보고서의 첨부 감사·검토보고서(뒤에 붙은 재무제표 사본 제외)를 받는다. 요청 시작 간격 1초 이상, 작업당 40회, 전체 120초, 응답 8MB 상한을 코드 상수로 지킨다. 검색 결과가 한 회사로 좁혀지지 않으면 더 요청하지 않는다(`company_unresolved`). 어떤 실패도 색인에 적고 정상 반환하며, 취소(`CancelledError`)만 전파한다
  - **작업 서비스 연결** (`backend/services/goose_job_service.py`): 수집은 시작 판정 잠금 밖에서 돌고, 끝나면 하네스 무결성을 다시 검사한 뒤 goose를 실행한다. 수집기는 생성자 주입이며 기본값은 없음(운영 인스턴스에만 실제 수집기를 붙인다). `AI_REPORT_GOOSE_DART_PREFETCH=0`이면 수집하지 않고 `outcome: disabled` 색인만 쓴다. 진행 이벤트 `dart_prefetch`를 수집 전에 한 번 보낸다
  - **화면** (`frontend/src/components/ProgressPanel.tsx`, `frontend/src/utils/gooseJob.ts`, `frontend/src/types/aiReport.ts`): 진행 패널 첫 단계에 `공시 원문 수집`을 더했다
  - **하네스 지침** (`backend/goose_harness_src/harness-instructions.md`, `backend/goose_harness_src/goose-manifest.json`): 규칙 8 — goose가 `runs/<job_id>/dart/index.json`을 먼저 읽고, 실제로 연 텍스트 파일만 `verification: direct_read` 출처로 적으며(`url`은 색인의 `viewer_url`, `limitations`에 "서버 사전 수집본으로 열람"), 서버 검색을 `research_window.searches`에 옮겨 적게 한다. goose 권한·프롬프트·실행 인자는 바꾸지 않았다. 매니페스트는 재생성
  - **테스트 격리** (`backend/tests/conftest.py`): goose 테스트에서 외부 소켓 연결 시도를 기록하고 테스트 종료 시 0건을 단언한다 — 수집기가 실패를 삼켜도 실제 DART 접속이 RED로 드러난다. 녹화·합성 픽스처는 `backend/tests/fixtures/dart/`
- **검증**: AC-AIR5-001~016 16개 모두 PASS(AC-AIR5-003은 자동 테스트 기준, AC-AIR5-016은 라이브 1회차). 수집 모듈 라인 커버리지 95%(440문 중 21 누락), 되돌림 대조(lessons #9)로 각 AC가 틀린 구현을 잡는지 RED를 관측했다. goose 회귀 `256 passed`(M4)
  - **라이브 (2026-10-21, 롯데에너지머티리얼즈 020150, 작업 `a5becbb9`)**: 색인 `outcome=complete`, 요청 27회, 26.1초, 파일 15/15 `ok`(재무제표 9·주석 1·요약 1·감사/검토보고서 4). goose는 `status: done`·`delivery_status: draft`로 끝났고, 이전 실행 2건에서 나오던 DART 관련 감사 결함 6종이 0종이 됐다. DART `direct_read` 출처 10건 모두 색인의 `viewer_url`·`text_file`과 일치
- **알려진 한계**: (a) 결과물은 여전히 `draft`다 — 감수(`AUDIT_*`·`REVIEW_*`)와 브라우저 화면 확인(`REVIEW_VISUAL`)이 없고(백로그 t18), 네이버 검색이 막혀 `LATEST_SEARCH_NAVER`가 남는다(t19) · (b) 정기보고서만 받는다 — 잠정실적·주요사항보고서·지분 공시·KIND·PDF 원본은 범위 밖 · (c) goose가 연 파일을 끝까지 읽었는지는 기계로 확인할 수 없다 · (d) 진행 패널 화면 배치는 직접 보지 않았다 · (e) `ruff`가 이 환경에 없어 실행하지 못했다
  - **근거**: `.moai/specs/SPEC-AI-REPORT-005/progress.md` §E.2~§E.4 · `.moai/state/verify/70e95898/aiR5/`

### Removed (AI 리포트 하루 횟수 제한 제거 — 사용자 결정, 2026-10-21)

- **Goose 하루 실행 횟수 제한 제거** (`4be2906` — `backend/services/goose_job_service.py`, `backend/routers/ai_report.py`, `frontend/src/api/aiReport.ts`, `frontend/src/components/AiReportModal.tsx`): 단일 사용자 앱이라 필요 없다. `AI_REPORT_GOOSE_DAILY_QUOTA`, 하루 한도 카운터, 429 `goose_rate_limit` 응답과 "내일 다시 시도하세요" 안내를 지웠다. 서버 전체 동시 실행 1건(다른 종목이면 429 `goose_busy`)은 그대로다. 같은 날 7번 연달아 시작해도 거부되지 않음을 서비스·라우터 테스트로 고정했다
- **빠른 분석 하루 호출 횟수 제한 제거** (`cb6b1ff` — `backend/services/ai_report_service.py`): `AI_REPORT_DAILY_QUOTA`와 "일일 쿼터 초과" 거부를 지웠다. 분당 연속 요청 제한(`AI_REPORT_BURST_LIMIT`, 기본 3회/60초 → 429 `rate_limit`)과 같은 종목 중복 분석 거부(429 `already_running`)는 그대로다. 같은 날 60번 연달아 호출해도 거부되지 않음을 서비스 테스트로 고정했다
- **설정 영향**: `.env.example`에서 두 키를 지웠다. 기존 `.env`에 남은 두 키는 이제 읽지 않는다. 백엔드 테스트 `292 passed`(두 커밋 각각, `.moai/state/verify/70e95898/aiR5/quota_pytest.log`·`fastquota_backend.log`)

### Fixed (Goose 진행 단계 "리포트 입력 작성" 인식 — 2026-10-21)

- **goose가 `company-input.json`을 써도 입력 작성 단계를 인식한다** (`4be2906` — `backend/services/goose_runner.py`): 실행기 `StageMapper`가 `runs/<job_id>/input.json`만 입력 작성(compose) 단계로 쳤는데, 라이브 실행 `a5becbb9`에서 goose가 `company-input.json`을 써서 진행 패널에 `리포트 입력 작성 — 건너뜀`으로 보였다. 이제 작업 폴더 바로 아래의 `*input.json`을 모두 인식하고, 하위 폴더(`draft/report-input.json`)와 다른 작업 폴더는 세지 않는다. 재현 테스트를 먼저 실패시킨 뒤 고쳤다. 서버 재시작 뒤 라이브 확인은 아직 하지 않았다

### Changed (Bump 순위 기준을 표와 통일 — 2026-10-21)

- **Bump 차트가 표와 같은 기간·시장 기준으로 순위를 그린다** — 표는 헤더의 기간 탭(1W/1M/3M) 초과수익률 단독으로 순위를 매기는데, Bump는 종합점수(1W 30%·1M 40%·3M 30%)와 전체 시장으로 그려 두 화면의 순위가 어긋났다. 이제 Bump가 헤더의 기간·시장 토글 값을 그대로 조회에 싣는다 (`ddbdf23`, SPEC 없음 — 사용자 결정)
  - **API** (`backend/routers/sectors.py`, `backend/services/sector_advanced_service.py`, `backend/schemas/sector_advanced.py`, `my_chart/analysis/sector_metrics.py`): `/api/sectors/history`가 `period`(`1w`|`1m`|`3m`)를 받아 `compute_sector_history` → `compute_sector_aggregates(period=...)`로 넘긴다. 생략하면 종전대로 composite 순위다. 응답에 `period` echo와 주별 `rank_basis_excess_return`(순위를 정한 기간의 초과수익률, composite면 `null`)을 더했다. 허용하지 않는 기간 값은 422
  - **화면** (`frontend/src/api/history.ts`, `frontend/src/components/SectorAnalysis/BumpChart.tsx`, `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx`): Bump 서브탭에서 기간 토글이 활성이다(AC-SUX-027의 비활성 대상에서 Bump 제외, RRG는 유지). 기간이나 시장을 바꾸면 Bump가 다시 조회한다. 툴팁은 종합점수 대신 순위 기준 기간의 초과수익률(예: `3M 초과수익률: +12.3%`)을 보여 주고, 차트 위에 `순위 기준: 1M 초과수익률 · All (표와 같은 기준 · 마지막 점 2026-10-16, 끝난 주)` 캡션을 둔다(`5583842`에서 "(표와 동일)"을 고침 — 표는 진행 중인 주까지 반영해 순위 숫자가 다를 수 있다)
  - **근거 — 355주 실측** (2020-04 ~ 2026-10, 프로덕션 집계 경로, 매주 상위 5개 섹터 기준): 향후 4주 초과수익(중앙값 대비)은 1M 단독 1.69%p, composite 1.53%p, 1W 단독 1.58%p로 표준오차(약 0.45%p) 안에서 구분되지 않았고, 표본을 반으로 나누면 1위가 바뀌었다(전반 1W, 후반 1M). 반면 한 주 10칸 이상 순위 이동 비율은 1M 12%, composite 18%, 1W 40%였다. 1W 30%를 섞는 근거가 된 기록은 없었다 — 가중치는 최초 커밋 `8b78ee4`에서 이유 없이 정해졌다
  - **라이브 확인 (2026-10-16, `period=1m`)**: `market=all`에서 Bump 순위가 표의 1M 순위와 29개 모두 같다. `market=kospi`는 Bump에만 있는 디스플레이(19위)·스마트폰(24위)(AC-SUX-019 등가중 대체) 때문에 순위 숫자는 다르지만 공통 27개 섹터의 상대 순서는 같다. `period` 생략 시 응답은 종전 composite 순위(방송미디어·음식료·운송)
- **화면 변화**: 기본 1M에서 Bump 상위가 바뀐다 — 2026-10-16 기준 1위가 방송미디어(composite)에서 PCB(1M 초과 +17.4%)로 바뀐다. 1W 탭에서는 순위가 크게 흔들린다(한 주 10칸 이상 이동 40%) — 단기 열기를 보는 탭이므로 의도된 동작이다. 표의 기준일은 진행 중인 주(예: 10-20)까지, Bump 마지막 점은 끝난 주(10-16)까지라는 차이는 그대로다
- **검증**: 재현 테스트를 먼저 작성해 실패를 확인했다(백엔드 7개 — `period` 인자 부재로 TypeError·AttributeError, 프론트엔드 9개). 변경 후 `tests/` 1087 passed, `backend/tests` 4 failed / 58 errors는 실패 노드 ID가 기준선과 같다(diff 동일). vitest 839 passed(`e2e/preset-flow.spec.ts` 수집 실패는 이전부터 있던 것), `tsc` exit 0. eslint 1건(`SectorAnalysis.tsx` `react-hooks/set-state-in-effect`)과 ruff I001 5건은 변경 전 코드에도 같은 위치에 있던 것이다
- **알려진 한계**: (a) 실측은 현재 시점의 종목 유니버스와 시가총액을 과거에도 쓴다(생존 편향·look-ahead — 프로덕션 화면과 같은 조건이라 기준 간 비교에는 공정) · (b) 거래비용은 반영하지 않았다 · (c) 섹터 29개로 IC가 0.01~0.07이라 어떤 기준이든 섹터 단위 예측력은 약하다 · (d) 브라우저 화면은 직접 보지 않았다(개발 서버가 새 모듈을 내보내는 것까지 확인)
- **독립 sync 감사**: PASS-WITH-DEBT(조화평균 0.909, 차단 0건). 지적 F1(기간 토글을 빠르게 바꾸면 늦게 온 이전 응답이 새 화면을 덮어씀 — weeks 토글에도 있던 경합)·F2(캡션 "(표와 동일)"이 기준일 차이로 화면에서 틀리게 읽힘)·F3(낡은 주석)은 `5583842`에서 고쳤다 — 요청 순번으로 최근 요청의 응답만 반영하고 재현 테스트를 더했다(고치기 전 실패 확인). 이후 vitest 840 passed, `tsc` exit 0. 남은 지적: F4(Bump 탭을 한 번 열면 숨겨진 상태에서도 토글마다 5~9초 조회가 돈다), F5(시장 필터에서 공통 섹터 상대 순서 일치는 라이브 대조 1회뿐, 자동 테스트 없음)
  - **근거**: `.moai/state/verify/e6bbafd3-bump-period/`(테스트·린트 출력, 라이브 응답·대조 `live_check.txt`, 감사 `audit.md`) · `.moai/state/verify/e6bbafd3-bump-score-eval/`(실측 스크립트·원자료·결과)

### Fixed (섹터 순위 계산 경로 통일 — SPEC-RS-REBALANCE-001 라이브 점검 후속, 2026-10-21)

- **같은 섹터의 순위가 화면마다 달랐던 문제 해소** — 섹터 표의 순위는 집계 경로(`compute_sector_aggregates`: 시총가중, 순위 백분위 정규화, 상한가중 벤치마크 `ALL_CAPPED` 기준 초과수익률)로 매겼지만, Bump 히스토리·주간 섹터 알림·표의 기본 행(`sectors[]`)·ContextBar 리더/래거드는 레거시 `compute_sector_ranking`(min-max 정규화, KOSPI 지수 행 기준 초과수익률)을 탔다. 그래서 표 한 행 안에서도 순위는 집계 경로, 초과수익률 숫자는 KOSPI 기준인 값이 섞여 있었다. 네 소비처를 모두 집계 경로(`period=None` composite)로 옮기고 레거시 함수를 지웠다 (SPEC 없음 — SPEC-RS-REBALANCE-001 라이브 점검에서 발견)
  - **Bump 히스토리** (`6ae45d7` — `my_chart/analysis/sector_metrics.py`, `backend/services/sector_advanced_service.py`): 각 히스토리 날짜의 순위를 `compute_sector_aggregates(as_of=d, period=None)`에서 가져온다. Bump만 최소 구성수 규칙(AG-5)을 적용하지 않고, 시총가중 수익률을 낼 수 없는 섹터(AG-4/AG-7)는 등가중 수익률로 대신해 모든 섹터 선을 유지한다(`2ef3644`, AC-SUX-019). 대체가 필요 없는 날짜에서는 Bump 순위가 표 종합점수 순위와 같다(라이브 8주 `market=all`·`kosdaq` 불일치 0). 날짜와 무관한 입력(정규 격자, 유효 유니버스, registry 매핑)은 `_SharedInputs`로 호출당 한 번만 계산한다. 라이브 2026-10-16: 비철금속 Bump 순위 1위 → 5위(3M +31% 극단값이 min-max 스케일을 지배하던 효과가 사라짐). 12주 응답 약 24초 → 약 4.7초(웜 캐시, 레거시 2.5초). 재현 테스트 `tests/test_sector_history_rank_alignment.py` 신설
  - **주간 섹터 전환 알림** (`2472bec` — `my_chart/analysis/sector_advanced.py`, `backend/services/market_service.py`, `backend/routers/market.py`): `/api/market/overview`의 `sector_alerts`가 같은 경로를 쓰고, 이제 일봉 DB(`DAILY_DB_PATH`)를 받아 시총가중으로 계산한다(전에는 일봉 DB 없이 호출돼 조용히 등가중으로 폴백했다). RS·Stage 2 값이 한쪽이라도 결측이면 신호를 내지 않는다(레거시는 0으로 취급했다). 라이브: 약화 알림 1건 — 에너지(15위 → 28위, Stage 2 −14.8%p, RRG Lagging). 일봉 DB 없이 호출하면 0건이었다. 재현 테스트 `tests/test_sector_transitions_rank_alignment.py` 신설
  - **순위 응답 `sectors[]`와 종목 버블 기준선** (`d99abbc` — `backend/services/sector_ranking_service.py`, `backend/services/sector_advanced_service.py`, `my_chart/analysis/sector_metrics.py`, `my_chart/analysis/aggregate_types.py`): `/api/sectors/ranking`의 레거시 `sectors[]`(섹터 표 기본 행, ContextBar 리더/래거드, MarketOverview, WeeklyHighlights가 읽음)를 집계 경로에서 만든다 — 초과수익률은 `ALL_CAPPED` 벤치마크 기준(전에는 KOSPI 지수 행), composite는 순위 백분위, 순위 제외 섹터는 생략. 응답 스키마와 키는 그대로다. 종목 버블의 `sector_aggregate`도 같은 경로에서 가져온다. 레거시 `compute_sector_ranking`·`_compute_sector_metrics`·`_normalize_list`·`_COMPOSITE_W_*`·`_load_kospi_returns`·`SectorRank`를 삭제했다(레거시 직접 테스트 12개 삭제, 4개 이관, 재현 테스트 `tests/test_sector_ranking_sectors_unify.py` 신설)
  - **라이브 전·후 비교 (2026-10-20, 1M 초과수익률 / composite 순위)**: 방송미디어 +23.8% → +15.5% / 2위 → 1위, 비철금속 +22.8% → +14.5% / 1위 → 3위, PCB +27.8% → +19.5% / 12위 → 14위. ContextBar 상위 3개 비철금속·방송미디어·음식료 → 방송미디어·음식료·비철금속. 섹터 수는 전·후 모두 29개(빠진 섹터 없음). 변경 후 `sectors[]`와 `data[]`의 순위·composite·초과수익률 불일치 0건
  - **빌드 의존성** (`5b8d8f5`·`d81aa34` — `pyproject.toml`, `uv.lock`): setuptools 요구를 `>=82.0.1` → `<81`로 되돌리고 잠금 파일을 82.0.1 → 80.10.2로 맞췄다. pykrx가 import하는 `pkg_resources`가 setuptools 82에서 제거됐기 때문이다. 운영 venv는 이미 80.10.2로 돌고 있었고, 새 워크트리 venv에서만 82가 설치돼 pre-commit 게이트가 깨졌다
- **화면 변화**:
  - 섹터 표와 ContextBar·MarketOverview·WeeklyHighlights의 초과수익률 숫자가 대체로 약 8%p 낮아진다. 기준이 KOSPI 지수에서 상한가중 전체 벤치마크로 바뀌어서다(2026-10-20 1M 기준 세 섹터 모두 −8.3%p)
  - ContextBar 리더/래거드 구성과 순서가 바뀔 수 있다. Bump 차트의 선 순서도 표 순위와 같아진다
  - 순위 제외 섹터(구성종목 5개 미만 등)는 표 기본 행에서 빠질 수 있다. Bump는 시장 필터(KOSPI/KOSDAQ)를 걸어도 모든 섹터 선을 유지한다 — `market=kospi`에서 표는 27개(디스플레이·스마트폰 제외), Bump는 29개다. 이 두 섹터는 등가중 대체 값으로 순위가 매겨져 주마다 크게 오르내릴 수 있고(스마트폰 29위→3위→1위), 같은 순위 분모를 쓰는 다른 섹터의 Bump 순위도 표와 조금 어긋날 수 있다
- **검증**: `tests/` 1077 passed(기준선 1070), Bump 복원(`2ef3644`) 후 1080 passed. `backend/tests`의 4 failed / 58 errors는 실패 노드 ID가 SPEC-RS-REBALANCE-001 sync 기준선과 같다(diff 결과 동일). vitest 832 passed, `e2e/preset-flow.spec.ts` 수집 실패는 이전부터 있던 것이다. `frontend/`에서 `tsc -b` exit 0. 이번 변경은 프런트엔드 코드를 건드리지 않았다. AC-SUX-019 관련 vitest 46개 통과(`.moai/state/verify/bump-ag5/`). 독립 sync 감사 PASS(조화평균 0.89, 차단 0건). `d99abbc`의 재현 테스트는 변경 전 코드에서 7 failed / 3 passed, 변경 후 10 passed
- **알려진 한계**: (a) F1 — 히스토리 값이 원천에서 반올림되지 않는다(화면에서만 반올림) · (b) F2 — `_SharedInputs`를 두 곳에서 손으로 조립하고, docstring은 히스토리 전용이라고 적고 있다 · (c) F3 — setuptools 핀에 하한이 없다. CVE-2025-47273 대응으로 `>=78.1.1,<81`을 권장 · (d) F4 — 알림 정렬 테스트 파일은 옛 코드에서 assertion이 아니라 `ImportError`로만 실패한다 · (e) 요청이 느려졌다 — `/api/sectors/ranking`은 기본 `period=1m`에서 집계 4회(기간 2회 + 순위 변화 기준선 2회)를 돌아 라이브 약 6.2초다(변경 전 지연은 같은 조건으로 재지 않았다) · (f) 구성종목 5개 미만 섹터는 종목 버블 기준선(`sector_aggregate`)이 `null`이다 · (g) `6ae45d7`·`2472bec`의 검증 증거는 해당 워크트리를 제거할 때 함께 사라졌다. 위 두 커밋의 라이브 수치(비철금속 Bump 1위 → 5위, 12주 응답 시간, 에너지 알림)는 보존된 증거 파일이 없다
  - **근거**: `.moai/state/verify/e6bbafd3-sync/`(`audit.md`, `summary.txt`, `backend_fail_ids.txt`·`base_fail_ids.txt`) · `.moai/state/verify/a41fe4b/`(`red.txt`, `green.txt`, `live_before.json`, `live_after.json`)

### Changed (SPEC-RS-REBALANCE-001 v0.4.0 — RS 타임라인 재조정, 2026-10-20)

- **종목 RS 등급(`RS_12M_Rating`)을 IBD식 비율 가중으로 바꿨다** — 예전 산식은 1개월 수익률 순위에 큰 비중을 둬 상위 종목 명단이 몇 주 만에 크게 바뀌었다. 이제 최근 분기(3M) 40%와 이전 세 분기 각 20%를 수익률 비율로 합친 점수의 순위를 쓴다. 1개월 신호는 등급에서 떼어 별도의 "열기" 배지로 보여 준다 (`my_chart/db/weekly.py`)
  - **효과 (같은 측정 스크립트로 변경 전·후 DB 사본을 비교, 295주)**: 상위 10% 종목이 4주 뒤에도 상위 10%에 남는 비율 29.24% → 65.17%(목표 60% 이상). 상위 10%의 향후 4주 수익 − 유니버스 평균은 −0.55 → −0.52pp로 사실상 그대로다 — 수익 예측력은 바뀌지 않았고 명단 안정성만 올랐다 (`scripts/rs_eval/stock_rs_eval.py 4 --production`)
  - **순위 분모 정리와 낡은 행 제거**: 지수(KOSPI·KOSDAQ), 거래량 0 행, 우선주(코드 끝자리 ≠ 0)·스팩, `1+R ≤ 0` 행, 결측 행을 순위 분모에서 뺀다. 재생성 때 이번 실행이 쓰지 않은 `relative_strength` 행은 모두 지운다 — 라이브 주봉 DB에서 짝 없는 행 119,881 → 0, 지수 행 692 → 0, 거래량 0 짝 행 16,369 → 0, 기준 종목 날짜가 아닌 행 5 → 0. 기준 종목 행이 0개면 아무것도 지우지 않고 경고만 남긴다
  - **새 필드 `rs_1m`** (주간 `RS_1M_Rating`): `StageStock`·`StockBubbleItem` 응답과 일봉 `stock_meta`의 마지막 컬럼(멱등 ALTER — 기존 테이블 끝에 열 추가) (`my_chart/analysis/stage_classifier.py`, `my_chart/analysis/sector_advanced.py`, `backend/services/meta_service.py`, `backend/services/stage_service.py`, `backend/services/sector_advanced_service.py`, `backend/schemas/stage.py`, `backend/schemas/sector_advanced.py`)
  - **새 필드 `rs_med`** (섹터 RS 중앙값): 섹터 랭킹 항목과 봉투 `data[]`. 결측은 0으로 채우지 않고 `null`로 둔다 (`my_chart/analysis/sector_metrics.py`, `my_chart/analysis/aggregate_types.py`, `backend/services/sector_ranking_service.py`, `backend/schemas/sector.py`, `backend/schemas/envelope.py`)
  - **화면**: Stock Explorer 종목 표와 섹터 버블 툴팁에 열기 배지(`rs_1m >= RS_TOP_THRESHOLD`, 80 — 섹터 화면의 RS 80+ 비중과 같은 상수) · 섹터 랭킹 표에 `RS Med` 열(RS Avg → RS Med → RS 80+ 비중 순서, 정렬 지원) (`frontend/src/utils/rsMetrics.ts`, `frontend/src/components/StockExplorer/StockTable.tsx`, `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx`, `frontend/src/components/SectorAnalysis/SectorRankingTable.tsx`, `frontend/src/components/SectorAnalysis/SectorAnalysis.tsx`, `frontend/src/styles/global.css`, `frontend/src/types/stage.ts`·`bubble.ts`·`market.ts`)
  - **Stage 2 임계값 70/60은 실측으로 유지**: 새 등급으로 다시 쟀다 — 70(진입 RS 하한)은 조건부 RS 통과율 99.48 → 94.42로 허용오차(9.948) 안, 60(Strong)은 Strong 비중 33.53 → 33.72%로 ±5%p 안. 상수 값은 그대로 두고, `backend/services/screen_service.py`와 `StockTable.tsx`에 흩어져 있던 리터럴 70을 상수 참조로 바꿨다. 측정 도구 `scripts/rs_eval/stage2_ratio_eval.py` 신설
  - **데이터 주의**: 컬럼 이름은 그대로지만 주봉 `RS_12M_Rating`과 일봉 `stock_meta.rs_12m`에 든 값은 이제 새 산식 값이다. 2026-10-20 라이브 주봉 DB의 RS를 재생성하고 일봉 DB의 `stock_meta`를 재구축했다. 백업: `Output/stock_data_weekly.db.bak_20261020`, `Output/stock_data_daily.db.bak_20261020_m4`. 최신 주차(2026-10-16) 등급 종목은 2,490 → 2,387(거래량 0 101 + 지수 2 제외), 그중 열기 배지 478
  - **검증**: 인수 기준 AC-RSR-001~018 + 008b 19개 중 FAIL 0, 라이브 단계까지 관측한 것 8개(001·002·007·011·012·014·015·017). sync 게이트: `tests/` 1070 passed · vitest 832 passed · `tsc -b` exit 0 · ruff 새 지적 0(변경 전 41 = 변경 후 41). `backend/tests`의 4 failed / 58 errors와 vitest `e2e/preset-flow.spec.ts` 수집 실패는 이 SPEC 이전부터 있던 것이다(실패 노드 ID가 기준선과 같음). sync 4차원 감사 PASS(조화평균 0.891)
  - **알려진 한계** (spec.md §7): (a) 버블 툴팁의 열기 배지는 라이브 화면에서 호버로 보지 않았다(단위 테스트로만 검증). ECharts 툴팁 기본값(`enterable: false`) 때문에 배지 title이 화면에서 읽히지 않을 수 있다 · (b) sync 감사 minor 12건은 기록만 했다 — `screen_service.py`가 임계값을 f-string으로 SQL에 넣는 점, 측정 스크립트의 SQLite URI 이스케이프, `_get_rs_on_date()` 튜플 반환 등 · (c) 설명 문서 `docs/rs-timeline-eli5.html`은 gitignore 대상이라 커밋되지 않았다
  - **근거**: `.moai/specs/SPEC-RS-REBALANCE-001/progress.md` §E.2~§E.4 · `.moai/state/verify/c1bf371e/`

### Changed (SPEC-AI-REPORT-004 v0.4.4 — AI 모달 심층 분석을 Goose 스킬 하네스로 교체, 2026-10-20)

- **차트 셀 AI 모달의 Deep 모드를 goose 스킬 하네스(헤드리스 `claude -p`)로 교체** — 옛 5-소스 병렬 수집 + Claude CLI 합성 파이프라인(SPEC-AI-REPORT-002)을 지우고, 전용 하네스 폴더에서 띄운 `claude -p`가 goose `company_report` 리포트를 단일 HTML로 만들도록 바꿨다. 작업은 HTTP 요청과 분리된 서버 작업 큐에서 돌아 모달을 닫거나 새로고침해도 이어진다. 모드 버튼 이름은 "심층 분석" → "Goose". 빠른 분석(Codex, SPEC-AI-REPORT-003)은 그대로다
  - **하네스 설치·무결성** (`backend/services/goose_harness.py`, 원본 `backend/goose_harness_src/` + `goose-manifest.json`): 서버 시작(lifespan) 때 원본을 매니페스트 sha256과 대조해 `~/.goose-harness`(`AI_REPORT_GOOSE_HARNESS_DIR`)에 설치하고, 작업마다 설치본을 다시 검사한다. 원본·설치본이 어긋나면 작업을 시작하지 않는다(닫힌 실패). 원본은 `.claude/`·`CLAUDE.md` 이름을 쓰지 않아 이 리포의 Claude Code 세션이 goose 스킬을 발견하지 않는다
  - **실행기** (`backend/services/goose_runner.py`): `claude -p --output-format stream-json --setting-sources project --settings <하네스>/.claude/settings.json --strict-mcp-config --permission-mode dontAsk --no-session-persistence --model <AI_REPORT_GOOSE_MODEL>`, 하네스 폴더를 cwd로 실행. 환경 변수는 허용 목록 8종만 넘기고, 시간 상한(`AI_REPORT_GOOSE_TIMEOUT`, 기본 900초) 초과 시 프로세스 그룹 전체를 종료한다. stream-json을 진행 단계로 바꾸고, 권한 거부 시 거부된 도구·명령을 로그에 남긴다
  - **작업 서비스·라우터** (`backend/services/goose_job_service.py`, `backend/routers/ai_report.py`): `POST /api/ai-report/{code}?mode=deep` → 202 `{job_id}`(같은 종목 실행 중이면 200 기존 `job_id`, 다른 종목 실행 중이면 429 `goose_busy`, 한도 소진 시 429 `goose_rate_limit`). `GET /api/ai-report/jobs/{job_id}/events`(SSE, 재생 + `Last-Event-ID`), `POST /api/ai-report/jobs/{job_id}/cancel`, `GET /api/ai-report/goose/active`. Goose 전용 하루 한도 `AI_REPORT_GOOSE_DAILY_QUOTA`(기본 5)
  - **보관·서빙** (`backend/services/goose_storage.py`): `final/report.html` + `delivery_allowed: true`일 때만 최종본, 아니면 `draft/` 초안으로 판정해 `backend/reports/<종목명>/goose/<날짜>/`에 허용 목록 파일과 `assumptions.md`·`job.json`만 복사한다. `GET /api/ai-report/{code}/goose/{run}/report.html`은 `sandbox` CSP 헤더와 함께 서빙하고, 기록 API에 `kind: goose` 항목을 더했다. 하네스 작업 폴더는 최근 `AI_REPORT_GOOSE_RUNS_KEEP`(기본 10)개만 남긴다
  - **프론트엔드** (`frontend/src/components/AiReportModal.tsx`, `GooseReportView.tsx`, `ProgressPanel.tsx`, `frontend/src/hooks/useAiReport.ts`, `useGooseActive.ts`, `frontend/src/utils/gooseJob.ts`, `frontend/src/api/aiReport.ts`, `frontend/src/components/ChartGrid/ChartCell.tsx`): 작업 구독·재구독, 진행 패널, sandbox iframe 리포트와 초안 배너, 기록 탭 Goose 항목, 실행 중 종목의 AI 버튼 표시
  - **삭제·정리**: `backend/services/deep_research_service.py`·`deep_research_collector.py`·`backend/prompts/stock_synthesis_prompt.md`와 그 시험, `frontend/e2e/ai-report-deep.spec.ts` 삭제. `backend/services/claude_cli_streamer.py`는 라인 파서·종료 함수만 남김. `.env.example`에서 검색 API 키 5종·`AI_REPORT_DEEP_*` 3종을 빼고 `AI_REPORT_GOOSE_{MODEL,TIMEOUT,DAILY_QUOTA,RUNS_KEEP}`(+ 주석 `AI_REPORT_GOOSE_HARNESS_DIR`)를 넣었다
  - **검증**: 인수 기준 AC-AIR4-001~025 25개 중 자동 23개 PASS(되돌림 RED 관측 기록 포함), 라이브 AC-AIR4-003 권한 음성 탐침 11/11 거부 PASS, 라이브 AC-AIR4-025는 부분 확인 — 2026-10-20 하나기술(299030)·한빛레이저(452190) 2건이 사람 입력 없이 `done`·`draft`로 끝났다(3분 37초, 2분 40초, `assumptions.md` 비어 있지 않음). goose 시험 6파일 `201 passed`(v0.4.4 기준)
  - **알려진 한계**: (a) Goose 하루 한도 카운터가 서버 메모리에 있어 재시작하면 초기화된다 · (b) goose의 WebFetch로는 DART 공시 원문을 읽지 못한다(목록이 POST 조회이고 목차를 자바스크립트가 들고 있음) — 그래서 리포트가 초안으로 끝난다. 서버가 DART 본문을 받아 넘기는 방식은 후속 카드 t16 · (c) AC-AIR4-025 중 두 항목은 미관측 — 한 종목의 기록 탭에 Goose 항목과 빠른 분석 항목이 함께 보이는지, 실제 goose 세션의 `final/` 생성
  - **근거**: `.moai/specs/SPEC-AI-REPORT-004/progress.md` §E.2·§E.4 · `.moai/state/verify/m7/` · `.moai/state/verify/goose-bash-denial/`

### Fixed (네이버 모바일 테마 API 스키마 변경 대응 — 테마 수집 0건 복구, 2026-10-17)

- **테마 분석 화면이 테마 0건을 받던 문제 해소** — 네이버 모바일 테마 API의 스키마가 바뀌어 수집 결과가 0건이 됐다. 목록 필드명이 `sectorCode`/`sectorName`/`unChangedCount` → `code`/`name`/`unchangedCount`로 바뀌었고, 페이지 방식이 `page` 번호에서 `cursor` 기반으로 바뀌었으며, 상세 필드가 `result.sectorInfo` 아래로 옮겨졌다. 세 변경에 맞춰 파서·크롤러·서비스를 고쳤다 (Kanban t13 선행 수정 — SPEC 없음)
  - **변경** (`4f3d3e1`, 12파일 +587/−109): `backend/services/naver_theme_v2/parser.py` · `crawler.py` · `service.py` + 라이브 응답 픽스처(`tests/fixtures/naver_theme_v2/list_live.json`·`list_live_last.json`·`detail_live.json`) 신설과 합성 픽스처 갱신 + 테스트 3종 보강
  - **관측**: 수정 후 라이브 수집 테마 264건 · 종목 574건 · errors `[]` (수정 전 0건) — 백엔드 `pytest tests -m "not live"` `1034 passed, 1 skipped, 93 deselected, 1 xpassed`
  - **남은 데이터 공급 문제 (기존 상태, 후속 카드)**: `change_pct_3d`는 모바일 API가 제공하지 않아 백엔드가 0.0 자리표시값을 채우므로 모든 행이 `0.00%`로 표시된다(t14) · `top_stocks_preview`는 채워지지 않는다(t15)

### Changed (SPEC-THEME-DISPLAY-UNIFY-001 v0.2.1 — 테마 순위표 결측 표기 `–` 통일, 2026-10-17)

- **테마 순위표의 결측 표기를 `–`(en dash)로 통일하고 표시 포맷을 `MetricCell` 단일 출처로 흡수** — `ThemeRankingTable.tsx`의 지역 포맷터 3종(`formatPct`/`formatBreadth`/`formatMomentum`)을 제거하고 등락률·3일등락률·모멘텀점수·상승비율 4개 지표 셀을 `MetricCell` + `toMetricValue` 경유로 바꿨다. 대표종목 칸은 `MetricCell`을 거치지 않고 `MISSING_TEXT` 상수만 공유한다. 선행 `SPEC-SECTOR-DISPLAY-UNIFY-001`이 백로그로 넘긴 항목(G-F2, Kanban t8)의 인수 SPEC
  - **결함 해소**: 결측 칸이 `-`(hyphen)로 찍히던 것을 섹터 화면과 같은 `–`로 통일 · `change_pct`가 `Infinity`이면 `+Infinity%`가 새던 경로와, 런타임 `null`이 `null.toFixed` TypeError로 표를 깨뜨리던 경로를 `toMetricValue`가 결측으로 접어 차단
  - **변경** (`44ce058`, PR #13): `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` 1파일 +14/−22 · 신규 테스트 `frontend/src/components/ThemeAnalysis/__tests__/ThemeRankingTable.display.test.tsx`(21 it — AC 15 + 경계 E1~E6) · `frontend/src/components/common/MetricCell.tsx` 무변경
  - **검증**: AC-TDU-001~015 **15/15 PASS** — 대조 8종 전부 되돌림 RED 실측, AC-TDU-004는 되돌림 `'-'` / 불완전 구현 `'+Infinity%'` / 완전 구현 `'–'` 세 상태 모두 실행 관측 · `tsc -b` exit 0 · eslint 델타 0 · vitest 전체 760 passed(파일 실패 2건은 기존 e2e 수집 오류)
  - **라이브 확인 (F7, 2026-10-17)**: headless Chromium으로 순위표 20행 확인 — 대표종목 열 20/20 `–`, 모든 열에서 `-`·`NaN`·`null`·`undefined`·`+Infinity%` 0건, 정상값(`+9.08%`·`0.00%`·`5.45`·`100.0%`)은 변경 전 포맷과 같다. 라이브 snapshot 20행 기준 4개 지표 null 0/20. 이 확인은 위 네이버 스키마 대응 수정(`4f3d3e1`) 이후에야 가능했다. sync 게이트: vitest ThemeAnalysis+common 8파일 80테스트 통과
  - **잔여**: ThemeAnalysis 탭 전체로는 `–`(순위표)와 `-`(ThemeDetailPanel·다중테마표)가 공존한다 — 의도된 범위 경계(spec.md §5)
  - **근거**: `.moai/specs/SPEC-THEME-DISPLAY-UNIFY-001/progress.md` §E.2~§E.4 · `.moai/state/verify/8c9ed526/`

### Changed (SectorAnalysis 기간 조인 단일 순회 통합 — 술어 중복 제거, 2026-08-19)

- **기간 순위 조인의 성공 판정이 두 곳에 중복 인코딩돼 있던 구조를 제거** — `SectorAnalysis.tsx` 의 두 useMemo 가 각각 `sectors[]`·`data[]` 를 따로 순회하며 "조인 성공 = 이름 일치 AND `d.rank != null`" 을 각자 인코딩했다. 여기서 나온 `periodRankingActive`·`partialFallbackCount` 가 `(순위 기준)` 마커·폴백 캡션·부분 고지를 결정하므로, 한쪽 정의만 바뀌면 표의 행과 그 아래 고지가 서로 다른 말을 하고 어느 쪽도 오류를 내지 않는다 (chore 카드 t7 — SPEC 없음, 운영자 승인)
  - **변경** (`bbb41cc`, 2파일 +67/−18): 단일 useMemo 가 `{ joinedSectors, periodJoinCount }` 를 한 순회(`for...of`)에서 함께 반환 — 조인 성공 판정이 한 자리에서 한 번 일어나고 행 교체와 카운팅이 같은 분기에서 나오므로 두 값이 어긋나는 상태가 **구조적으로 표현 불가능**하다. 소비 지점 3곳의 prop 계약과 `SectorRankingTable.tsx` 는 무변경 (diff 확인)
  - **성격 (F3 — 정확한 기록)**: 순수 동작 보존이 아니라 **한 방향으로 엄밀히 개선**이다. `data[]` 에 같은 이름이 두 번 오면 이전 코드는 갈릴 수 있었다 — 조인 행은 Map 이라 마지막 항목이 이기는데 카운트는 Set(`rank != null`)이라 아무 항목이든 rank 를 가지면 조인 성공으로 셌다. `[{A,rank:1},{A,rank:null}]` 에서 A 행은 composite 폴백인데 카운트는 A 를 조인 성공으로 넣는 어긋남 — 이 카드가 없애려던 바로 그 상태. 통합 후에는 `byName.get()` 한 곳만 보므로 갈라질 수 없으며, 정상 입력(유니크 섹터명)에서는 동작 불변
  - **증명 (관측)**: 부분 조인 특성화 테스트 신규 1건 — **변경 전 코드에 대고 먼저 8/8 green** 관측(선재 결함 부재 확인) 후 통합했고 통합 후에도 8/8(보존) · 판별력 실증 — 카운트만 옛 정의(이름 일치)로 되돌리면 `2 failed | 6 passed`, verbatim `TestingLibraryElementError: Unable to find an element by: [data-testid="ranking-basis-partial"]` (변이 시 카운트 3 → `partialFallbackCount = 3−3 = 0` → 부분 고지 노드 소실). 신규 테스트와 기존 F2 회귀 테스트가 같은 변이에 서로 다른 각도(행 값 vs 고지 문구)로 동시 반응 — review 가 run 보고를 신뢰하지 않고 변이를 직접 재현했다
  - **eslint 델타 0 (총량이 아닌 부모 폼 대조)**: review 가 `bbb41cc^` 의 `SectorAnalysis.tsx` 를 임시 복원해 측정 — 부모 1건 / 현재 1건(동일 규칙 `react-hooks/set-state-in-effect` @ 동일 useEffect) · 신규 테스트 파일 0건. 계기 기록: run 의 첫 통합 형태(map 콜백 내 `let` 변이)에서 23→22 를 관측했는데 줄어든 이유가 수선이 아니라 **react-hooks 컴파일러 분석이 그 컴포넌트에서 중단되며 손대지 않은 기존 진단이 사일런싱**된 것이었다 — `for...of` + 동일 스코프 `let` 으로 교체해 복귀. 컴파일러 분석 기반 규칙에서 감소는 "분석기가 코드를 못 보게 됐다"는 신호일 수 있으므로 감소가 관측되면 원인을 대게 하고 대지 못하면 실패로 본다(리드 채택 존치 소견)
  - **배터리 불변**: `npm run typecheck` exit 0 · vitest 전체 **84파일 739테스트 green**(738 + 신규 1) · eslint **5개 디렉터리 게이트 스코프** 명령(plan.md §F 축자 — `npm run lint` 전체 스코프의 50 과는 다른 명령) **23 problems 유지** · `npm run build` exit 0 — 리드·run 독립 측정 일치, sync 세션 재실행으로도 4/4 재확인 (`.moai/state/verify/sync-69061723-t7/`)
  - **리뷰 정정 이력 (F1 — 보존)**: review 초판이 "리드의 eslint 기준선 23 이 재현되지 않는다(전체 50)"며 기준선 결함을 판정했다가 **철회**했다. 원인은 범위 착오 — 23 은 5개 디렉터리 스코프 게이트 명령의 값, 50 은 `npm run lint`(전체 스코프)의 값으로 서로 다른 명령의 결과다. review 가 게이트 명령으로 재측정해 23 을 재현했고 초판 판정을 철회하며 서술을 지우지 않고 `[정정됨 2026-08-19]` 표시로 경위·자기 귀속을 남겼다(문서화된 명령이 존재하는데 실행해 보지 않고 결함을 단정한 미관측 결함 주장). t7 의 eslint 델타 0 결론은 이 정정의 영향을 받지 않는다
  - **소견 처분**: F1 — 위 정정 이력 보존 + 존치 소견 2건 채택(판정문에 게이트 스코프 명시 · 감소 방향 판정) · F2 — 기록만: 파일 단독 측정은 1건(`SectorAnalysis.tsx:151 set-state-in-effect` — 부모 폼과 동일 규칙·동일 useEffect, 델타 0). run 보고의 "진단 3건"은 게이트 스코프 내 `set-state-in-effect` **규칙 총계 3건**(SectorAnalysis 1 + RRGChart 1 + StockExplorer 1 — 각 1건씩)이며 카드가 복귀시킨 것은 SectorAnalysis 1건. 수치에 규칙·스코프 표기로 해소 — sync 감사가 리뷰 서술 "RRGChart 2 + SectorAnalysis 1"(RRGChart 의 2건은 서로 다른 규칙 2건 — 총 문제 수와 규칙 수의 우연한 수치 일치)의 귀속 혼동을 eslint.out 대조로 정정 · F3 — 위 성격 항목으로 기록("완전한 동작 보존" 서술은 부정확 → 한 방향 개선으로 정확히 기록)
  - **근거**: `.moai/state/verify/b3e680b5/t7-*.out` (리드) · `.moai/state/verify/1a086d99/t7-report.md`·`t7-*.out` (run) · `.moai/state/verify/04afee96/t7-review.md` (review 정정본) — 테스트 CI 부재(워크플로 label-sync.yml 단일)로 로컬 재현이 유일한 근거

### Fixed (frontend 테스트 tsconfig 분리 — 프로덕션 타입 경계 폐쇄, 2026-08-19)

- **프로덕션 `src` 코드에서 Node 내장 모듈과 vitest 전역이 더 이상 타입 검사를 통과하지 않는다** — `tsconfig.app.json` 이 `include: ["src"]` 하나로 프로덕션과 테스트를 한 프로젝트에 담고 있었다. 테스트가 `node:fs` 를 쓰므로 `types` 에 `"node"` 가 들어가 있었고(`d0cfe75`) `"vitest/globals"` 도 같은 구조였다 — 그 결과 **프로덕션 코드도 Node 모듈을 import 하면 타입 검사를 통과**했다. 테스트 전용 프로젝트 `tsconfig.test.json` 을 분리해 이 경계를 닫았다 (chore 카드 t4 — 운영자 승인으로 SPEC 3종 생략)
  - **변경** (`736f4d4`): `tsconfig.test.json` 신설 — extends app · `types` `["vite/client","vitest/globals","node"]` · include `__tests__/**` + `*.test.ts|tsx` + `test-setup.ts` + `src/**/*.d.ts` · tsbuildinfo 분리. `tsconfig.app.json` 은 `types` 를 `["vite/client"]` 로 축소하고 테스트 갈래를 exclude. 루트 `tsconfig.json` references 3개로 확장. `src/**/*.d.ts` 명시는 필수 — 이 줄이 없으면 `src/types/react-window.d.ts` ambient 선언이 test 프로젝트에서 보이지 않아 TS7016 4건이 재발한다(t9 백로그 참조)
  - **증명 (설정 diff 가 아니라 관측이다)**: 프로덕션 파일에 `node:fs` import 주입 → 변경 전 `tsc -b` exit 0 / 변경 후 exit 2 (TS2307) — 기준선은 리드가 구현 전에 독립 측정 · 같은 파일에 `describe/it/expect` 주입 → 변경 후 exit 2 (TS2593 ×2 + TS2304) · `.spec.ts` 파일은 F1 전 app 프로젝트로 떨어져 exit 2 / F1 후 exit 0 (`--listFilesOnly` 소속 test 1 · app 0) · test 프로젝트가 장식품이 아님 — `tsc -b --dry` 에 app·node·test 세 프로젝트가 모두 오르고, 테스트에 타입 오류 주입 시 TS2322 로 실패(리뷰 실측)
  - **배터리 불변**: `npm run typecheck` exit 0 · vitest 전체 **84파일 738테스트 green** · eslint §F.1 범위 23 problems 불변 · `npm run build` exit 0 — sync 세션 재실행으로 4/4 재확인 (`.moai/state/verify/sync-69061723-t4/`)
  - **남은 소견 (리뷰 판정 전부 비차단)**: **F1** `*.spec.ts|tsx` 갈래 누락 — 누락 파일이 생기면 경계가 조용히 열리는 게 아니라 빌드가 즉시 깨져 시끄럽게 알린다 → 후속 커밋 `c1c2d35` 로 app exclude·test include 양쪽 추가 **완료** · **F2** 공유 프로덕션 파일 오류가 test·app 두 프로젝트에서 2줄 중복 출력 — 미관 문제, 오류를 놓치는 방향 아님(기록만) · **F3** `tsc -b` 가 noEmit 프로젝트를 매번 out-of-date 로 판정해 증분 캐시가 무효 — 기존 app·node 도 같은 성질이고 절대 비용 2.4초라 조치 불요(기록만) · **중복 컴파일 실측** — 프로덕션 102파일 이중 검사, `tsc -b` 2.36s (app 단독 1.04s / test 단독 1.58s), 순증 1초 미만(기록만)
  - **근거**: 리드·run·review 증거 — `.moai/state/verify/b3e680b5/t4-*` · `.moai/state/verify/1a086d99/t4-*` · `.moai/state/verify/04afee96/t4-review.md` (이 레포에는 테스트 CI 가 없다 — 워크플로는 label-sync.yml 하나뿐이라 로컬 재현이 유일한 근거)

### Fixed (SPEC-SECTOR-DISPLAY-UNIFY-001 v0.3.0, 2026-08-19)

- **섹터 분석 화면의 RS 라벨 부정확·null% 렌더·기간 토글 무동작 해소** — 형제 백엔드 `SPEC-SECTOR-METRIC-UNIFY-001`(M0~M5)에서 분리된 프론트 SPEC(원본 계획 M6·M7). UI의 "RS"가 등급·RRG RS-Ratio·RS Line 세 가지를 지칭하던 모호함과, 같은 지표의 반올림이 제각각이던 것(`Math.round`/`toFixed(1)`/없음 혼재)을 `rating0`(등급 정수)/`pct0`(비율 정수) 단일 출처로 통일
  - **라벨 정확성 (REQ-SDU-004)**: `'RS Top %'` → **`RS 80+ 비중`** (RS 점수처럼 읽히는 혼동 해소 — 임계값 80을 이름에 명시) · `'RS 중앙'`(50 상수 표기) → **`RS 50 (유니버스 백분위 중앙)`** · 차트 셀 배지 `RS {v}` → **`RS등급 {v}`** (RS Line 버튼과 구분) · RRG 차트 측정 지표 캡션 신설 · 버블 Y축 → `RS Rating 평균 (0-100)`
  - **null% 표시 버그 (REQ-SDU-002)**: MetricCard가 결측값에 문자열 `null%`를 렌더하던 결함 해소 — 이제 결측은 `-`
  - **RS 임계값 상수화 (REQ-SDU-003)**: `frontend/src/utils/rsMetrics.ts` 신설 (`RS_TOP_THRESHOLD=80` 외 3상수). 백엔드 `my_chart/analysis/sector_metrics.py` 원문을 읽어 등식을 검증하는 교차 언어 테스트로 고정 — 임계값 드리프트 구조적 차단
  - **색 램프 분리 (REQ-SDU-005)**: RS 등급(rs_avg) 보라 ↔ RS 80+ 비중(rs_top_pct) 파랑 — 같은 수치에서 두 셀이 같은 색으로 수렴하던 것을 되돌림으로 실증
  - **기간 토글 실동작 (REQ-SDU-006~011)**: 랭킹 표 순위가 선택 기간(1W/1M/3M)으로 재산출 — 봉투 `data[]` 이름 조인으로 `rank`/`rank_change` 전환, 선택 기간 열에 `(순위 기준)` 마커, 화면 상단에 기간·시장 고지 띠. 봉투 부재·전량 rank null 시 `순위 기준: 종합점수(3기간 가중)` 캡션, 일부 폴백 시 `일부 N개 섹터는 이번 기간 순위가 없어 종합점수 순위 유지` 고지(원인 중립 문구 — 리뷰 F6). 버블 X축 벤치마크 라벨도 형제 SPEC의 정의 B 전환을 반영해 `KOSPI/KOSDAQ 상한가중`으로 정정
  - **커밋 하이라이트**: M6 `0023210` (표시 통일 — 반올림 단일출처·상수화·라벨·색램프) · M7 `45ffaad` (기간 토글 — data[] 조인·폴백 캡션·마커·X축 라벨) · 정정 `4059f44` (§F 전체 스위트로 좁힘 결함 정정 — 누락 갱신 대상 3종 등재 + AC-012/013 재판정) · 리뷰 F1~F4 `3b9398b` (배지 강조 술어를 표시 문자열 기준으로 통일·rank null 가드·단언 강도 복구·기록 정정) · F6 `739ba53` (부분 폴백 고지 원인 중립화) 외 SPEC 기록 docs 6건 — 총 11커밋
  - **신설된 회귀 가드**: 신규 관측 — `rsMetrics.test.ts`(교차 언어 등식) · `rsDisplayConsistency`(표 셀·상세 패널·버블 툴팁 3면 RS 문자열 동일성) · `sectorPeriodToggle`(신설 파일 — 조인 순서·폴백 캡션·열 마커·전량 rank null) · 색램프 분리 · rating0 반올림 · null% 렌더 + F1 경계 단언 2건(`rs_12m ∈ [79.5,80)` 배지-강조 일치) · F2 rank-null 캡션 1건. 기존 2종 테스트는 라벨 갱신
  - **검증**: AC-SDU-001~013 **13/13 PASS — 되돌림/주입 RED 실측**(AC-012/013은 리드 정정 재판정: 원 좁힘 증거 무효화 → §F 축자 전체 스위트 근거로 교체) · `npm run typecheck` exit 0 · eslint §F.1 범위 23 problems = 기준선 27 − 소실 6 + 사전 선언 예외 2, **신규 (파일,규칙) 0건 (B\A=∅)** · vitest 전체 **84파일 738테스트 all green**. 실행 방식 orchestrator-direct(manager-develop 스폰 GLM 하위 컨텍스트 한계 2회 사망 → 운영자 승인 A, 리드 경유 — §E.2.1). DoD 라이브 화면 확인은 운영자 판정으로 해소(§E.3 — provider·hook dep 변경은 dev 서버 재시작 후 확인해야 한다는 교훈 포착)
  - **Gap/잔여 (본 SPEC 미수정·기록)**: F5(AC-SDU-009 X축 변화 단언 강도 — Y 불변 절반은 주입 되돌림 RED 실증이라 판정 유지) · 참고 2건은 리드 백로그 t7(조인 성공 술어 2곳 중복 — 공용 술어 후보)·t8(`ThemeAnalysis/ThemeRankingTable.tsx` 동일 직접 포맷 패턴, G-F2) · `Number(rsDisplay)`와 `rating0` 출력 결합(포맷 확장 시 동반 검토)

### Fixed (SPEC-SECTOR-METRIC-UNIFY-001 v0.5.0, 2026-08-18)

- **섹터 버블 차트 지표가 랭킹 탭과 달랐던 결함 — 산출 원천 단일화** — 같은 RS 정의를 공유하면서도 섹터 집계 구현이 두 벌 존재해 결측 처리(0점 대체 vs 제외)·초과수익률 벤치마크(KOSPI 지수 vs 시장별 상한 시총가중 유니버스)·거래대금 산식(주봉 close×volume 1개 vs VolumeWon 기간 누적, 약 2.5e7배 차이)·유니버스가 전부 갈렸다. `/api/sectors/bubble`을 `compute_sector_aggregates` 투영으로 전환해 두 경로 지표를 일치시켰다(**불일치 N=18 → 0**, 9조합×4필드쌍 전부). RS 결측 종목은 분모에서 제외(방산 1w/all rs_avg 48.16→54.18), 전원 결측 섹터는 0.0이 아닌 `null`, 거래대금은 VolumeWon 누적(억원) 기준. 봉투 `market_filter`가 모든 요청에 `"all"`로 거짓말하던 결함(D4)도 해소 — 이제 요청 시장을 반영한다
  - **커밋 하이라이트**: M0 특성화 `6aabf81`(손대지 않은 트리 GREEN 단독 커밋 — 불일치 N=18 리터럴 고정) · M1 RED `3cb3828`(파리티 9조합 + 결측 제외) · M2 배선 `d96ade6`(동작 불변) · M3 nullable `d16cb65`(백 스키마 4필드 `float | None` + TS `number | null` 동시 확장) · **M4 전환 `8f0a0c7`(수치가 바뀐 유일 단계 — N=18→0)** · M5 봉투 정상화 `3d06d9d`(`envelope_fields` + `market_filter` 정직화) · M5.5 `d6d1083`(섹터 전용 사다리 `SECTOR_PERIOD_SIZE_LADDER` 신설 + M4가 폭로한 `0억` 표시 회귀 해소) · review 재작업 `1f0c304`(차단 5건 해소)
  - **신설된 회귀 가드**: 백엔드 테스트 5종 신설(특성화 21 · 랭킹 파리티 30 · 스키마 nullable 6 · 결측 제외 3 · 빈 date 엣지 1) — SPEC 스위트 파일별 9종 **157 passed**. AC 22종 중 21종 **되돌림 RED 실측**(주입 → RED 관측 → 복원 → 바이트 동등 증명). 관측자 결함 2건을 스스로 폭로·보강(항진명제 — 봉투 market_filter 미검사, 스칼라-only 단언의 판별력 0)
  - **결측 표시**: `sectorReturnColor`가 null을 받으면 결측 전용색 `#4B5563`으로 렌더 — 종전에는 null이 산술 비교에서 0으로 강제 변환돼 결측 섹터가 보합과 같은 중립 회색으로 렌더되던 회귀 해소(review B2). TS 이중 캐스트 4건 제거로 타입 되돌림 시 `tsc -b` 하드 오류가 나는 정직한 픽스처 복원(AC-029)
  - **검증**: AC **21/22 PASS + 1 Gap(AC-005)** · pytest 157 passed · vitest SectorAnalysis+common **290/290** · `cd frontend && npx tsc -b` SPEC 귀속 **0건**(잔여 29건 전부 무관 기존 오류 — 루트 tsconfig가 `files: []` solution-style이라 `tsc --noEmit`은 0파일 검사하는 공허 관측임을 리뷰에서 확정, 게이트 교정) · **커버리지 최초 실측**(`coverage run --source=my_chart,backend`): `schemas/sector_advanced.py` 100% · `services/sector_advanced_service.py` 88% · `sector_metrics.py` 97% · `routers/sectors.py` 78% · `analysis/sector_advanced.py` 81%
  - **Gap**: AC-005(기계·금융 섹터 실측치 — frozen 픽스처에 해당 섹터 부재로 어느 방향으로도 관측 불가, AC 문구 개정은 manager-spec 소관) · 사다리 refs 스케일의 라이브 검증 미실시(대형주 편중 fixture 기준 — 배포 후 첫 주 실측 분포 대비 재확인 권고)
  - **잔여 분류 (후속)**: F4(SPEC 문구 개정 REQ-SMU-023/AC-018 → `SECTOR_PERIOD_SIZE_LADDER` + HISTORY 행) manager-spec 소관 · F7(`SECTOR ladder` vMin/vMax 커밋 테스트 0건) 배포 전 관측자 신설 권고 · F3/F22(단위 표기 "원"→"억원" 정정 4곳)·F14~F29는 `SPEC-SECTOR-DISPLAY-UNIFY-001` 및 후속 분류 — review-report.md §권고 처리 순서 참조

### Added (SPEC-CHECKED-SECTOR-GROUP-001 v0.3.0, 2026-08-17)

- **차트 그리드 종목 목록 체크 탭 섹터 그룹핑** — `체크(N)` 탭이 평면 목록에서 섹터 헤더 + 체크 종목 행 구조로 전환. 헤더는 섹터명과 **그 섹터의 체크 수**(유니버스 `stock_count` 아님)를 표시하고 모든 행은 어떤 헤더 아래에 위치한다. 그룹 키는 백엔드 규칙의 정확한 재현(`major = sector_major || '기타'`, `minor ? `${major} > ${minor}` : major` — `backend/services/screen_service.py:221-223`), 정렬은 코드포인트 오름차순(백엔드 `sorted()` 파리티 — `localeCompare('ko')`는 ICU collation이 한글을 Latin 앞에 두어 두 탭 순서가 어긋나므로 기각, 되돌림 보조축으로 실증). 접기 상태는 체크 탭 전용 `Set`으로 분리(전체 탭 `flatItems`/`collapsedSectors` 경로 무변경)
  - **커밋 하이라이트**: M0 characterization `3acf05a`(손대지 않은 트리 GREEN 단독 커밋 — rollback 이분 탐색 기준점) · M1 `aeb249f` `sectorKey.ts` 그룹 키 헬퍼(소비자 0 신설) · M2 `06d251f` `StockList.tsx` 그룹 경로 전환 · M3 `f819deb` + lint 정합 `e8b5a74` · review 결함 수정 `e620657`(접힘 키 그룹 소멸 정리 — 그룹 재등장 시 펼침 보장) + `fe7c73a`(prune를 useEffect → 이벤트 경로 전환, `react-hooks/set-state-in-effect` 해소)
  - **신설된 회귀 가드**: 테스트 3종 신설(`sectorKey.test.ts` · `StockList.grouping.test.tsx` · `StockList.alltab.characterization.test.tsx` — StockList 스코프 `Test Files 3 / Tests 28 passed`) — AC별 되돌림 16/16 RED 실측(항진명제 0), localeCompare('ko') 보조축 게이팅 실증, 과잉정리 방지(부분 해제 시 그룹 잔존·접힘 유지)·전체 탭 접힘 경계 불변 단언 포함
  - **검증**: AC 15/15 PASS(AC-CSG-012 철회 결번, review 보강 단언 1건 포함) · 되돌림 16/16 RED · 전체 vitest `Tests 722 passed (722)`(2 e2e 파일 로드 실패 = 사전 존재 기준선 노이즈, 동일 집합) · `npx tsc --noEmit` exit 0 · eslint StockList 스코프 exit 0 · 커버리지 `sectorKey.ts` 100% / `StockList.tsx` lines 89.81%(≥85% 게이트) · 의존성 변동 0줄. sync-phase 품질 심사: 4차원(기능성 0.9/보안성 1.0/공정성 0.9/일관성 0.9, 조화평균 **0.923** ≥ 0.85) binding PASS — 결함 7건 전부 미차
  - **Gap**: §0.2 성능 사전 baseline 미포착(사후 단일 jsdom 샘플만: 탭 전환 46.08ms · uncheck 3.94ms) · `StockList.tsx` branch coverage 80.64%(lines 게이트는 충족)
  - **알려진 제약 (사용자 결정, 본 SPEC 미수정)** — 재발 보고 추적용 기록:
    - 재현: 체크 탭에서 섹터 그룹 접기 → 차트 그리드(ChartCell)에서 그 그룹의 마지막 체크 종목 해제 → 같은 종목 재체크
    - 증상: 그룹이 접힌 상태로 재등장(`aria-expanded="false"`)하여 방금 체크한 종목 행이 보이지 않음 (탭 라벨 카운트는 증가)
    - 원인: `ChartCell.tsx:358`이 `useWatchlist().toggleStock`을 StockList 컴포넌트 경계 밖에서 직접 소비 — 이벤트 래퍼 prune 경로(`pruneCollapseKeyAfterUncheck`)가 2개 진입점(체크 탭 x 버튼·전체 탭 체크박스)만 커버
    - 참고: `clearAll`은 UI 소비처 0건 — 네 번째 진입점 없음 (review grep 확인)
    - 처분: 사용자 결정으로 본 SPEC에서 수정하지 않음. 재등장-펼침 보장의 정식 AC는 ChartCell 경로를 커버하는 후속 SPEC이 3개 진입점 전체 대상으로 소유

### Fixed (Bump 차트 Top-N 필터, 2026-08-16)

- **섹터 분석 Bump 탭 Top 5 / Top 10 필터가 사실상 무력했던 결함** — 종전 구현은 `history.some(w => w.rank <= n)`("기간 중 한 번이라도 N위에 진입" 시맨틱스)이라 순위 변동이 큰 29개 섹터에서 Top 5 를 눌러도 20개 이상, Top 10 은 28개가 통과해 필터와 무관하게 라인이 그대로 다 그려졌다. 기준일(전체 history 중 가장 늦은 날짜 — 화면 상단 `기준일` 표기와 동일 기준) 순위가 N위 이내인 섹터만 남기도록 수정: Top 5 = 정확히 5개 라인, Top 10 = 10개. `latestDate` 는 필터 결과(`filteredSectors`)가 아니라 원본 `sectors` 에서 계산한다(필터 결과 의존 시 순환 발생)
  - **신설된 회귀 가드**: `__tests__/BumpChart.topfilter.test.tsx` 4건 — 전체 선택 시 7개 섹터 불변, Top 5 선택 시 기준일 1~5위 정확히 5개(A/B/D/E/F), 과거 상위 섹터 제외(직전 주 2위·기준일 9위 섹터는 Top 5 에 남지 않음 — 되돌림 방지), Top 10 선택 시 기준일 1~10위만 포함
  - **검증**: frontend vitest SectorAnalysis 스코프 **25 files / 250 tests passed**(직전 24 files / 246 tests, 신규 4) · `npx tsc --noEmit` exit 0 · 되돌림 대조 — 옛 `some()` 로직 복원 시 신규 테스트 3건 RED 실제 관측 후 복구 GREEN

### Added (SPEC-BUBBLE-ZOOM-001 v0.2.0, 2026-08-15~16)

- **종목·섹터 버블 차트 X축 줌·팬·영역 선택 줌** — 수익률 아웃라이어 종목(예: 화장품 OEMODM +350%)이 X축 스케일을 독점하면 나머지 종목이 0% 부근에 뭉쳐 구분되지 않는 문제 해소. Y축(RS 0-100)은 고정해 해석 일관성 유지 (M1~M4, `run_commit_sha` `e61d89d`)
  - **`e61d89d` — 휠 줌·드래그 팬·빈 공간 더블클릭 리셋**: ECharts `dataZoom type:'inside'` X축 전용(`yAxisIndex` 키 생략이 X축만 제어하는 관용구 — 음수 인덱스 비활성화 관용구는 존재하지 않음을 감사에서 확인), `filterMode:'none'`(줌 창 밖 버블도 클리핑 표시해 분포 맥락 유지), `minSpan:20/maxSpan:100`(퍼센트 단위 — 분율 0.2/1.0 오용 시 초기 창 클램프로 버블이 사라지는 회귀를 기존 sectorSwitch 테스트가 포착해 수정). 더블클릭 리셋은 zrender `dblclick`에서 `e.target` 부재(빈 공간)일 때만 `dispatchAction` — 버블 위 더블클릭은 기존 `onStockClick`/`onSectorClick` 반응속도 무손실(디바운스 없음)
  - **`b9c0e4f` — 줌 계약 테스트**: 기존 `echarts-for-react` 모킹 관례(option 캡처)를 ref(`getEchartsInstance`/`getZr`) 노출형으로 확장 — dataZoom 계약, 빈 공간/버블 위 더블클릭 분기, 빈 데이터 부재, `notMerge` 불변 단언
  - **`2827b5c` — 툴박스 영역 선택 줌 (REQ-BZ-007, v0.2.0)**: 수동 확인 후 "확대 후 이동" 2단계 조작 개선 요청으로 추가. 박스 드래그의 가로 범위만 X축 창에 적용(`toolbox.feature.dataZoom.yAxisIndex: false` — 공식 문서의 축 제외 방식), restore 버튼으로 전체 범위 즉시 복귀(더블클릭 리셋과 동등)
  - **`a93a21e` — 상단 마진 확보**: 최대 버블 반지름(종목 26px·섹터 34px)+상단 라벨이 `grid.top`(50/40)을 넘어 제목/toolbox 영역을 침범하던 결함 수정(종목 70·섹터 48) — 수동 확인 중 사용자 보고, RED→GREEN 마진 계약 테스트로 고정
  - **줌 중 Y축 순간 사선 현상**: ECharts가 dataZoom 창 변화 시 축 눈금/라벨도 update 애니메이션하는 부산물(공식 체인지로그에 명시된 동작)로 판명 — 최종 상태는 항상 올바르게 수렴하므로 사용자 결정으로 유지(무해)
  - **검증**: frontend vitest **690 passed**(직전 672, 신규 18) · `npx tsc --noEmit` exit 0. 선행 실패 집합 불변 — e2e 로드 실패 2파일(`e2e/ai-report-deep.spec.ts`, `e2e/preset-flow.spec.ts`, 0 tests collected)은 SPEC 범위 밖 기존 결함
  - **신설된 회귀 가드**: dataZoom 계약(inside/X축 전용/`yAxisIndex` 부재/`filterMode`/`min·maxSpan`), 빈 공간 더블클릭 `dispatchAction`·버블 위 미호출(REQ-BZ-003d), 빈 데이터 시 dataZoom·toolbox 부재, `notMerge` 불변, toolbox X축 전용 계약, 상단 마진 계약(종목 ≥70·섹터 ≥48)

### Fixed (post-release — 종목 탐색·섹터 버블 버그 수정 5건, 2026-08-14~15)

- **사용자 라이브 사용 중 발견된 SPEC 범위 밖 결함 5건** — SPEC-SECTOR-UX-001 close(`9c7096c`/`14356ac`) 이후 보고. 4건은 해당 SPEC의 선언 범위 밖(백엔드 API 계약, `StatusBar` 푸터, 스크롤 레이아웃, `bubble.ts` 전송 계층)이라 SPEC frontmatter/HISTORY 변경 없이 post-release 수정으로 처리
  - **`eb93f7a` — 푸터 종목 수가 필터 결과와 불일치**: `StatusBar`가 `useScreen()`의 전역 스크리닝 총계(`results.total`)만 읽어, 섹터 필터가 걸린 종목 탐색 화면에서 헤더·Stage 분포 바·표는 44종목을 가리키는데 푸터만 52개로 표시됐다. 필터 술어를 `frontend/src/components/StockExplorer/stockFilter.ts`(신규)로 추출해 `StockTable`·`StockExplorer`가 동일 함수를 호출하도록 하고, `ScreenContext`에 표시 중인 모집단을 게시하는 `visibleCount` 채널을 추가(`frontend/src/contexts/ScreenContext.tsx`)해 게시자가 있으면 푸터가 그 값을 따르도록 배선(`frontend/src/components/StatusBar/StatusBar.tsx`). 부수적으로 `StockExplorer`/`StockTable`이 서로 다르게 판정하던 미분류 조건(`stage == null` vs `1~4` 범위 밖)도 단일 술어로 해소
  - **`bfeeaf4` — 종목 표 세로 스크롤 부재**: `StockExplorer`의 클래스 없는 래퍼 `<div>`가 flex 컬럼의 일반 block 자식이라 콘텐츠 높이(Playwright 실측 75,239px)로 팽창, 안쪽 `.stock-table-wrapper`의 `flex:1`이 무효화되어 스크롤 컨테이너가 성립하지 않았다. `.stock-table-fill`(`flex:1; min-height:0`, `frontend/src/styles/global.css`) 부여 + `.stock-table-wrapper`에 `min-height:0` 추가로 복구(실측 client 75,239→634, scrollable false→true)
  - **`1405bb3` — 섹터 전환 시 이전 섹터 버블 잔존**: `echarts-for-react`는 `notMerge` 없이 `setOption`을 호출하면 series를 **인덱스 단위로 병합**한다. 섹터 분석 서브탭이 keep-mounted(AC-SUX-017)라 언마운트되지 않아, 기계(3계열)→스마트폰(2계열) 전환 시 인덱스 2(농기계)가 생존해 건설기계 종목(혜인·대동)이 스마트폰 버블에 표시됐다. `StockBubbleChart.tsx`·`SectorBubbleChart.tsx`에 `notMerge={true}` 추가(`RRGChart`/`BumpChart`/`TreemapHeatmap`은 이미 보유)
  - **`5629972` — `/sectors/bubble` market 파라미터 계약 불일치**: 7개 섹터 엔드포인트(`backend/routers/sectors.py`) 중 이 하나만 `^(KOSPI|KOSDAQ)$`(대문자, `all` 불가)를 요구해, 소문자로 표준화된 프론트가 KOSPI/KOSDAQ 선택 시 422를 받았다. 패턴을 형제 6개와 동일한 `^(all|kospi|kosdaq)$`로 정렬. 패턴만으로는 부족했다 — `my_chart/analysis/sector_advanced.py`의 `compute_sector_bubble`이 `_normalize_market_filter` 없이 market을 raw로 `backend/services/sector_advanced_service.py`에 넘기던 유일한 호출부라, 정규화를 배선하지 않으면 `market_filter="all"`이 (대문자 원천인) `stock_meta.시장구분`과 매칭되지 않아 **빈 섹터 목록에 HTTP 200**을 반환했을 것(실측 확인)
  - **`33b404b` — 종목 버블 뷰 시장 토글 무동작**: 원인 2건이 겹쳐 있었다 — `frontend/src/api/bubble.ts`의 `fetchStockBubble`이 `market` 파라미터를 아예 받지 않았고, stock 쿼리 키에도 `market`이 없어 `useQuery`가 재조회하지 않았다(각각 독립 변형으로 실증 — 하나만 고치면 여전히 무동작). 섹터 목록 뷰는 정상(키·인자 모두 배선됨)이었고 드릴다운 뷰만 고장. `frontend/src/components/SectorAnalysis/BubbleChart.tsx` 배선과 함께, `market='all'` → `null` 매핑·`!== 'ALL'` 대문자 비교 등 옛 규약 잔재를 제거하고 소문자 3값(`all`/`kospi`/`kosdaq`) 단일 규약으로 통일
- **검증**: frontend vitest **672 passed**(직전 661) · tsc 28건(비증가) · `TS2353` 0건 · backend pytest **917 passed**(직전 910), 회귀 0건. 선행 실패 집합 불변 — 프론트 e2e 로드 실패 2파일(`e2e/ai-report-deep.spec.ts`, `e2e/preset-flow.spec.ts`, 0 tests collected), 백엔드 8 failed(`test_screen_service`×3, `test_rs_line`×2, `test_meta_service`×2, `test_api`×1) + `tests/fnguide/` 25 errors — 전부 SPEC 범위 밖 기존 결함, 이번 5건과 무관
- **신설된 회귀 가드**: 푸터 표시 카운트(3경로), 스크롤 계약(부모 클래스 + CSS 선언), 섹터 전환 시 잔존 series(실 ECharts SVG 판독), `/sectors/bubble` market 계약(소문자 3값 수용 + 상태코드 일치 + 거래대금 분할 불변식 `kospi + kosdaq == all`), 종목 버블 market 배선(쿼리 키 + fetch 인자)
- **동작 변경 고지**: `/sectors/bubble`에 대문자 `KOSPI`/`KOSDAQ`을 보내면 이제 422다(형제 6개 엔드포인트와 동일해진 결과 — 저장소 내 대문자 호출자·테스트 없음을 grep으로 확인). `market` 파라미터 생략 시 응답 `market` 에코가 `null` → `"all"`로 변경

### Added (SPEC-SECTOR-UX-001 v0.4.0, 2026-08-14)

- **섹터 분석 화면 계층 — 상태 모델·전환 규칙·시각화 규약** (M1~M7, `run_commit_sha` `ccb9068`)
  - **상태 모델**: `AnalysisParamsContext`(market/period 사용자 제어 + `asOfDate`/`asOfIsPartialWeek`/`gridVersion` 읽기 전용)와 `SelectionContext`를 의도적으로 **분리**(D2) — period 변경이 섹터 선택 소비자를 리렌더시키지 않도록 함
  - **NavIntent 교체**: 기존 `CrossTabParams` 삭제(전역 clear 부재), `NavIntent` 3조건 소비 가드(target/id/active + `lastHandledId`)로 대체 — 전역 clear 경쟁 상태(ST-2) 해소
  - **토글 단일화**: 기간·시장 토글을 헤더 단일 인스턴스로 통합, 시장 토글이 실제로 5개 경로(Table/Bubble 섹터·종목/RRG/Bump/종목 탐색)에 반영되도록 배선(ST-4 해소)
  - **표·컨트롤 규약** (M4): rank 열 응답값 그대로 렌더, 정렬 변경 시 고지 띠, 순위변동 3상태(▲/▼/–/신규), 기준일 헤더 표기, 가중 방식 배지(ⓦ/ⓔ), 제외 섹터 하단 영역, `1W%`/`1M%`/`3M%`/섹터비중 신규 열, 순위 총수(`N/M`) 병기, Stage 분포 바 모집단 일치, 좁은 화면 열 접기(섹터비중 → Vol배 → 52W고 순, 기간 3열·Stage·RS·Name은 불변)
  - **시각화 규약** (M5): `bubbleRadius` 공용 유틸(면적 비례 + 로그 정규화, 기간별 고정 눈금 참조값)을 섹터·종목 버블 차트가 공유, 섹터 버블 발산형 5단계 색상(기준점 0%), 버블 테두리 채널 단일화(섹터=결측 거래대금 점선 / 종목=Stage 단독), RRG 사분면 의미 표기·축 자동 대칭(`half = max(5, ceil(maxDev × 1.1))`), 섹터 분석 서브탭 keep-mounted(탭 왕복 remount 0)
  - **로딩·오류·빈 상태** (M6): `DataLoadContext` 공용 조회 계층(쿼리 키 + TTL 1시간 + stale-but-showing + 2s/4s/8s 백오프 3회 후 정지 + 수동 새로고침 + 기준일 합치 검증 + `grid_version` 변경 시 전 캐시 무효화), `MetricCell` 공용 5상태 셀(`–`/`0.00%`/`계산 불가`/`42 ⚠`/`42 ❗`), 빈 상태 원인 표기(활성 필터별 해제 액션), 섹터 상세 오류 표시 + 재시도
  - **회귀 게이트** (M7): AC-SUX-056 R1~R5(기간 변경 시 로딩, 정렬 변경 시 고지 띠, 버블 크기 분포 변화, RRG 궤적 단축, KOSPI 필터 시 순위표 행 감소 + 제외 영역 — 전부 **의도된 변화**이며 회귀가 아님), §0.3 X1~X6 제거 목록 정적 스캔, §1.2 보존 10항목 회귀 0 확인, `metricText` 공용 헬퍼로 표 셀 ↔ 차트 툴팁(섹터버블/RRG/Bump)의 결측 표기 문자열 통일(D2), 캐시 적중 경로의 전역 기준일 미기록 결함(F1) 수정
  - **AG-5(Bump 최소 구성수 5) 미적용 확정** (2026-08-14 사용자 결정): `AC-SUX-019`/`AC-SUX-056 R5`의 검증 범위를 Table·섹터 Bubble·RRG로 한정(Bump 제외)하고, 제외 섹터의 선이 Bump에 남아 있어야 한다는 반대 방향 단언을 신설. `SPEC-SECTOR-AGGREGATION-001` 백엔드 변경 없음(출하 구현이 이미 미적용)
  - **AC 결과**: 60개 AC 중 **54 PASS / 6 PASS-WITH-DEBT / 0 FAIL**(AC-SUX-057은 REQ-SUX-054 철회로 결번). Debt 6건 — AC-SUX-018(RRG/Bump/StockExplorer 3경로 시장 미소구, 주 경로는 해소), AC-SUX-032(default 진입 시 기준일·진행중 배지 미구현, M6 소관), AC-SUX-042(벤치마크 절대값 백엔드 미전달), AC-SUX-046(`lookback_weeks`/`trail_start_date`/RRG `market` 파라미터 백엔드 미지원), AC-SUX-060(저커버리지 툴팁 ⚠ + 하단 요약 미구현), AC-SUX-033(**2026-08-14 사용자 결정** — `MarketProvider` 현행 유지, 부팅 시 sector fetch 1회 잔존은 후속 SPEC 항목)
  - **회귀처럼 보이지만 올바른 변화** (`acceptance.md` AC-SUX-056 R1~R5 참조): 기간 변경 시 로딩 발생, 정렬 변경 시 안내 띠 노출, 버블 크기 분포 변화(선형 매핑 대비 표준편차 증가), RRG 궤적 단축(TRAIL_WINDOW 적용), KOSPI 필터 시 순위표 행 감소 + 제외 영역 노출 — 전부 되돌림 금지
  - **검증**: `vitest run` 655 passed(run 착수 baseline 430 대비 +225), tsc 총 오류 28건(baseline 28 대비 비증가) · `TS2353` 0건(HARD 게이트 유지), eslint 45 errors(신규 error class 0 — 전부 기존 `react-refresh/only-export-components` 클래스), 기존 프론트엔드 테스트 전량 통과(회귀 0건). e2e 파일 로드 실패 2건(`e2e/ai-report-deep.spec.ts`, `e2e/preset-flow.spec.ts`)은 SPEC 범위 밖 선행 결함
  - Gap: §0.2 성능 목표 중 INP P95 / FCP / 토글 P95는 실브라우저 계측이 필요해 미측정. '종목 표 3열 추가 +20% 이내'는 비교 baseline이 M4 착수 전에 측정되지 않아 사후 판정 불가(절대 실측 500행 median 104.9ms + 3열 델타 +3.6% 대리 지표만 기록)

### Added (SPEC-SECTOR-AGGREGATION-001 v0.5.0, 2026-08-13~14)

- **섹터 집계 계층 — 시총가중·벤치마크·순위·RRG 지수·응답 공통 스키마** (M1~M7 + AC-SAG-037 closure, `run_commit_sha` `753a529`, closure `b703dc2`)
  - 신규 모듈 `my_chart/analysis/weighting.py`: 시가총액가중 집계 코어 — 섹터별 상한(`weight_cap = 0.10`) 재배분을 **동결형 알고리즘**으로 구현(상한 종목을 매 회 `frozen` 진부분집합으로 영구 제외해 `<= min(n,20)`회 내 종료를 증명). `INV-CAP-1` 불변식(`cap_eff(n) = max(0.10, 1/n)` — `n <= 10` 섹터는 시총가중이 등가중과 정확히 동일해지는 축퇴 경계) 신설·기계 집행(정적 스캔 2종)
  - 벤치마크 계산 — 섹터 집계와 동일한 집계 헬퍼를 재사용해 시장별(KOSPI/KOSDAQ/전체) 벤치마크 산출, 참조 구현 대조로 초과수익률 정합 검증
  - 순위 백분위 정규화(평균-동순위 처리, 결정적 tie-break) + `rank_change`(1단 재귀 가드)
  - 신규 모듈 `my_chart/analysis/rrg.py`: RRG(Relative Rotation Graph) 수익률 연쇄 지수 — 구성종목 변동 시점의 naive 방식 점프(비율 이탈 0.0099)를 체인 방식으로 제거
  - 지표 정정 5건(독립 커밋): 52주 신고가 판정(MAX52), Stage 분류기 단일화(레거시 일봉 분류기 삭제), `volume_ratio`(weekly VolumeSMA10 정정), `trading_value`(daily VolumeWon 원천 정정), RS 평균(등가중 + 결측 제외 게이팅 실증)
  - 라우터 `market`/`period` 쿼리 파라미터를 7개 엔드포인트(`/sectors/ranking`, `/sectors/bubble`, `/sectors/{name}/bubble`, `/sectors/rrg`, `/sectors/history`, `/sectors/{name}/detail`, `/stage/overview`)에 전면 배선(하위 호환 유지) + 응답 공통 스키마(`EnvelopeMixin.as_of_date`/`grid_version`) 전 엔드포인트 정합(AC-SAG-037, SN-3)
  - **AC-SAG-001~050 전항 PASS (50/50)** — acceptance.md §0 `INV-CAP-1`에 결속된 축퇴 계열 AC 11건 포함, 대조 단언(falsification/mutation) 전항 관측된 RED 확인 후 GREEN 복원
  - 검증: `tests/` 회귀 스위트 `900 → 910 passed`(AC-SAG-037 closure 기준), `8 failed`/`25 errors`는 SPEC 범위 밖 사전 존재 결함과 동일 집합(신규 실패 0건). 집계 프로즌 픽스처(`tests/fixtures/frozen/aggregation-2026-08-11/`) F1~F13 + AC-SAG-048/049/050 게이트 전항 PASS
  - **회귀처럼 보이지만 올바른 변화** (acceptance.md AC-SAG-045 R1~R8 참조): 순위 이동, 시총가중-등가중 괴리 등은 `INV-CAP-1` 축퇴 경계 신설과 상한 재배분 알고리즘 교체(무한 진동 → 동결형)에서 기인하며 되돌림 금지
  - Gap: 커버리지 % 미측정(pytest-cov 미설치, venv 부재) — 대리 지표로 신규 테스트가 대상 함수 경로를 직접 실행함을 확인

### Added (SPEC-SECTOR-GRID-001 v0.2.2, 2026-08-12)

- **섹터 분석 기반 계층 — 정규 주간 격자·유니버스·적재 보호** (M0~M6, `run_commit_sha` `1f62beb`)
  - 신규 모듈 `my_chart/analysis/weekly_grid.py`: `compute_weekly_grid()` — 주봉 원시 날짜(다중 날짜 주·부분 데이터 포함)를 정규화해 ISO 주당 1바 격자 산출
    - CG-1(ISO 주 그룹핑, 대표 = `MAX(Date)`), CG-2(진행 중인 주 `is_partial_week` 분리), CG-3(중앙값 50% 미만 배제 + `grid_exclusions[]`)
    - `anchor(t, days)` 달력 앵커링(1W/1M/3M/6M/12M/52W), `history(weeks=N)`, `grid_version = "canonical-v1"` 상수
    - 공유 헬퍼 `_get_latest_valid_date()` — 자체 기준일 조회 재도입 방지(REQ-SGR-005)
  - 신규 모듈 `my_chart/analysis/universe.py`: `compute_universe()` — 유효 유니버스(4중 교집합: registry ∩ stock_meta ∩ 최신바가격 ∩ 비-stale) + 진단(`registry_only`, `duplicates`, `stale_names`)
    - registry `Code` 기준 중복 제거(UN-4) + WARNING 로그, stale 판정(일봉 `MAX(Date)` 기준 14일 초과, `last_updated` 미사용, UN-5)
    - 미분류 섹터 센티널 `ETC_SECTOR = "기타"` 단일화(REQ-SGR-017)
  - `my_chart/db/weekly.py`: weekly INSERT를 positional → **column-name** 방식으로 전환(`stock_prices`, `relative_strength` 각 1건, Lesson #8 legacy-ALTER round-trip 게이트) + 주중 재적재 supersede(`--no-supersede` 안전장치 포함)
  - 7개 기준일 소비자(`sector_ranking_service.py`, `stage_service.py`, `market_service.py`, `meta_service.py`, `sector_advanced_service.py`, `sector_advanced.py`, `sector_metrics.py`)를 공유 격자 헬퍼로 수렴(TG-5)
  - **AC-SGR-001~021 전항 PASS (21/21)** — 프로즌 픽스처(`tests/fixtures/frozen/weekly-2026-08-12/`) 위에서 게이팅, 대조 단언(falsification) 7종 전부 GREEN
  - 검증: SPEC 스코프 gating 69 passed (`test_weekly_grid.py` / `test_consumer_dates.py` / `test_weekly_insert.py` / `test_weekly_supersede.py` / `test_universe.py` / `test_regression_sgr020.py`), 전체 회귀 `pytest tests/ --ignore=tests/fnguide` 475 passed / 8 failed(SPEC 범위 밖 기존 결함 — `test_api`/`test_meta_service`/`test_rs_line`/`test_screen_service`)
  - 성능: 격자 캐시 적중 0.003~0.005ms(목표 <5ms 대비 ~1000× 여유), 캐시 미적중(콜드) 635~803ms(목표 P95<50ms 미달이나 spec §0.2 처방 완화(`(db_path, mtime)` 메모이즈)가 이미 M1에 구현되어 있어 프로세스당 1회 콜드 비용으로 완화됨)
  - **회귀처럼 보이지만 올바른 변화** (`.moai/specs/SPEC-SECTOR-GRID-001/release-notes.md` 참고): rank 순위 이동, 1주 초과수익률 양수 섹터 29→18, 52주 신고가 종목 99→56, 게임 섹터 구성종목 33→32(중복 제거) 등 — 전부 AC-SGR-020 R1~R5로 기대값 고정, 되돌림 금지

### Fixed (SPEC-SECTOR-GRID-001 v0.3.0 — in-place amendment, 2026-08-12)

- **반증력(falsifiability) 복구 — 위 v0.2.2 릴리스의 테스트/AC 문서 결함 수정. 프로덕션 동작은 변경 없음.**
  - **배경**: 위 v0.2.2 종료 후 sync-auditor 독립 감사가 **PASS-WITH-DEBT 78.6/100**(Functionality 78 / Security 92 / Craft 72 / Consistency 75, BLOCKING 0 / SHOULD-FIX 6 / MINOR 6)을 반환했다. 핵심 소견: progress.md §E.2가 "대조 단언(falsification) 7종 전부 GREEN"이라 기록했으나, 실제로는 **진짜 4종 / 공허 3종**이었다 — 공허한 3종은 구현을 완전히 되돌려도 동일하게 GREEN이라 아무것도 반증하지 못했다. 사용자 승인 후 SPEC을 `completed → in-progress`로 되돌려 in-place amendment를 진행했다(`amendment_of: SPEC-SECTOR-GRID-001`, `prior_completed_sha: 95e0980`).
  - **1단계 — SPEC 본문 개정** (commit `2140cd6`, manager-spec, spec.md + acceptance.md 192+/47−): AC-SGR-005 정적 스캔 규범 명령이 유효한 bash가 아니었던 결함(줄바꿈 이음 누락 → `bash -n` exit 2)을 복구하고 잔류 집합 검증 방식을 제외 정규식 연쇄에서 **집합 동등 비교**로 전환, allowlist 실행 쿼리 상한을 6→**5**로 축소(공허했던 `chart_service.py` 항목 제거, 실측 `grep -c` → 0), AC-SGR-020 R5를 수학적 항진명제(`len(history) <= len(raw)`, 격자가 원시에서 선별되므로 어떤 구현에서도 참)에서 프로즌 리터럴 `345` 기준 엄격 부등으로 재기술, AC-SGR-004를 프로즌 적용 대상에서 **합성 픽스처 게이팅** 대상으로 재분류(라이브 실측 `exclusions == []`로 CG-3가 프로즌 픽스처 위에서 한 번도 발화하지 않음을 확인), §1.2.1 행 번호 드리프트 정정 + 판정 키를 매칭 텍스트로 전환, O-G6(`market_breadth.py:472` TG-4 오계산) 심각도 상향.
  - **2단계 — 테스트 반증력 실질화** (commit `a61c3c1` + backfill `e07ae36`, manager-develop, 4개 테스트 파일 + pyproject.toml + progress.md §E.2/§E.3, 689+/79−): F1(AC-SGR-021 센티넬 발산 차단 — 테스트 내부에서 동일 식 2회 비교하던 것을 프로덕션 코드 실호출로 교체), F2(AC-SGR-006-A 6지점 개별 되돌림 — A-4/A-6가 공유 헬퍼를 그대로 재호출해 실질 4-way였던 것을 6-way 전부로 복구), F3(AC-SGR-020 R5 항진명제 해소)을 되돌린 변형에서 실제 RED가 관측되도록 복구, F6(AC-SGR-005.2 규범 명령 실행), F7(AC-SGR-004 CG-3 재분류에 맞춘 게이팅 픽스처 전환)도 함께 실질화. **구현 코드는 한 줄도 수정하지 않았다** — `git diff --stat 2140cd6..HEAD -- my_chart/ backend/ frontend/`가 빈 diff(테스트/문서/설정 전용 변경).
  - **검증**: 게이팅 6파일 M6 69 passed → **84 passed**(+15, 전부 M7 신규 단언). 전체 회귀 `pytest tests/` baseline 569 passed / 8 failed / 25 errors → **584 passed**(+15, 정확히 신규분과 일치) / 8 failed(동일 목록, 본 SPEC 범위 밖 기존 결함) / 25 errors(동일, `tests/fnguide/`) — **회귀 0건**. 커버리지(DoD §4 게이트, `>= 85%`): `my_chart/analysis/weekly_grid.py` **100%**(94/94), `my_chart/analysis/universe.py` **100%**(56/56).
  - **미결로 남긴 것(REQ/AC 개정 소관, 본 커밋 범위 밖)**: (a) NULL `산업명(대)`가 pandas에서 `NaN`으로 승격되면 `NaN or ETC_SECTOR`가 NaN의 truthy 성질 때문에 센티넬 분기를 타지 않고 섹터 키가 `'nan'`이 된다(두 소비 경로 모두 동일값이라 AC-SGR-021의 "두 경로 일치" 게이팅 요건 자체는 성립 — 정규화 여부만 미결). (b) AC-SGR-004 본문의 "한 ISO 주 안에 두 날짜" 문구를 문자 그대로 구성하면 그 주가 통째로 격자에서 빠지는 경우가 있으며, AC 명시 `구성 예`만 게이팅 대상으로 채택함.

### Changed (SPEC-SECTOR-MINOR-COLOR-001 v1.0.1, 2026-05-27)

- **StockBubbleChart 종목 버블 차트 색상·범례 인코딩 교체** (commits `bebd3f1`, `7c5be67`)
  - 이전: Weinstein Stage 4-항목 (S1 바닥/S2 상승/S3 천장/S4 하락 + 미분류) 기반 색상 매핑 + 정적 5-항목 범례
  - 이후: sector_minor (산업명(중)) 기반 동적 색상 매핑 (Tableau 10 변형) + 동적 범례 (count desc, name asc, "기타" 마지막, palette overflow 흡수)
  - 색상 결정성 보장 (정렬 키 명시 + rerender() 2-pass round-trip 단언)
  - multi-series 변환으로 ECharts 표준 legend click toggle + hover emphasis 자동 동작
  - 모바일 viewport (<768px) fallback: 범례 하단 horizontal scroll, grid.right=60 / grid.bottom=80 (차트 영역 prominence 우선)
  - tooltip XSS hardening: escapeHtml 적용 (defensive coding, KRX 내부 DB 신뢰)
  - 신규 useMediaQuery hook (외부 라이브러리 무도입, SSR 가드 + cleanup listener)
  - Stage 정보는 tooltip `Stage: S{n} ({stage_detail})` 라인으로 보존 (REQ-SBM-008 회귀 방지)
  - 검증: pytest 39/39 PASS, vitest 85/85 PASS, coverage StockBubbleChart 90% / useMediaQuery 85.71%, tsc + ESLint 0 errors
  - evaluator-active Cycle 2 PASS (0.88/1.00): Functionality 92, Security 95, Craft 80, Consistency 90
  - 라이브 PASS: AC-4 sector_minor 색상 / AC-5 동적 범례 10그룹 (반도체 섹터) / AC-7 hover emphasis dim / AC-8 산업명(중) tooltip + Stage 보존
  - 후속: AC-12 200+ 종목 P95 baseline 측정은 라이브 measure pending (acceptance.md 명시 허용)

### Added (SPEC-STOCK-TOOLTIP-PRODUCT-001 v1.0.0, 2026-05-27)

- **StockBubbleChart tooltip 주요제품 라인 추가** (commit `b2ef257`)
  - tooltip에 `주요제품: {value or "—"}` 라인 추가 (산업명(중) 라인 다음, Stage 라인 위)
  - 데이터 소스: `Input/sectormap-original.xlsx` 산업명(대)/산업명(중)/**주요제품** 중 마지막 컬럼 → `stock_meta.product`
  - Backend: `_get_stock_meta` SELECT 7-컬럼 확장 (sector_minor + product), `StockBubble.product`, `StockBubbleItem.product`, `compute_stock_bubble`/`get_stock_bubble` 전파
  - Frontend: `bubble.ts`에 `product: string | null` 타입 미러, tooltip formatter `productLabel` (escapeHtml 적용), data 객체에 product 보존
  - NULL/빈 product → `주요제품: —` fallback 표시
  - AC-6 회귀 게이트: 직전 SPEC 산업명(중) 색상·범례·Stage tooltip 모두 보존 단언
  - 검증: pytest 42/42 PASS (+3), vitest 97/97 PASS (+12), tsc + ESLint 0 errors
  - 라이브 PASS: backend uvicorn `--reload` 재시작 후 tooltip 주요제품 라인 정상 표시 (사용자 확인)
  - 운영 lesson: uvicorn dev server reload 명시 필요 (CLAUDE.local.md 강조 점)

### Changed (chore — sectormap unification, 2026-05-12)

- **`Input/sectormap-original.xlsx` 단일 source 통합** (commit `face1ac`)
  - 이전: `Input/sectormap.xlsx`(6 컬럼 추출본, 2552 종목) + `Input/sectormap_original.xlsx`(원본, 백업) 이중 관리
  - 이후: `Input/sectormap-original.xlsx`(원본 53 컬럼, 2556 종목) 단일 source. `sectormap.xlsx` 폐기
  - `my_chart/config.py`: `SECTORMAP_PATH` → `sectormap-original.xlsx`
  - `my_chart/registry.py:_load_sectormap()`:
    - `header=8` (앞 row 0~7은 데이터 설명 주석)
    - 한글/개행 컬럼명 → 영문 rename (`종목\n코드`→`Code`, `종목명`→`Name`, `시장`→`Market`)
    - 6 컬럼만 select (53 → 6, 메모리 88% 절약)
    - downstream 코드(`get_stock_registry`, `get_sector_registry`, `meta_service`, `sector_advanced`, `stage_service`, `screen_service`) 변경 0
  - 종목 데이터: 2552 → 2556 (+13 신규 KONEX/SPAC, -9 구버전 폐지). 6 핵심 컬럼 99.5%+ 일치 (Market 1건만 시장 이동 차이)
  - 검증: pytest `tests/test_config.py` 10/10 PASS + registry load 정상 + backend `/api/stocks/master` HTTP 200
  - Follow-up (운영): backend dev server reload + `meta_service.rebuild_stock_meta()` 실행으로 stock_meta 테이블 갱신 필요

### Added (SPEC-NAVER-THEME-001)

- **네이버 금융 테마 분석 모듈** (SPEC-NAVER-THEME-001 v1.0.0)
  - 신규 5번째 탭: **테마 분석** (Theme Analysis)
  - 네이버 금융 테마 페이지(finance.naver.com/sise/theme.naver) read-only 크롤링
  - 백엔드 모듈: `backend/services/naver_theme/` (config, crawler, parser, analyzer, db_join, service, schemas)
    - 단일 진입점: `from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult`
    - EUC-KR 인코딩 강제 처리, SQLite read-only JOIN (`mode=ro`), 매너 크롤링(sleep ≥ 0.7s)
  - 신규 REST API 엔드포인트:
    - `GET /api/themes/snapshot?top_n=20&leaders_per_theme=3` — 5종 records list + metadata (~30s)
    - `GET /api/themes/quick?top_n=20` — themes + strong_themes + metadata (≤10s)
  - 테마 분석 결과 구조:
    - `themes_df`: theme_id, theme_name, change_pct, change_pct_3d, up/flat/down_count, top_stocks_preview
    - `strong_themes_df`: 위 + momentum_score, breadth_ratio
    - `stocks_df`: theme_id, stock_code/name, inclusion_reason, price, change/_pct, volume, trade_value, market_cap, per/roe(NaN)
    - `leaders_df`: 가중치 z-score(0.40/0.30/0.20/0.10) 기반 테마별 상위 K개
    - `multi_theme_stocks_df`: 2개 이상 테마 등장 종목
  - 신규 의존성 없음: 기존 requests, beautifulsoup4, lxml, pandas, numpy 활용 (REQ-NT-C-003)
  - 기존 4탭 회귀 0건 (AC-12): surgical mod 9줄 추가 (≤10줄 제한, AC-14)
  - 단위 테스트 51개, 커버리지 99%
  - V2 핸드오프 노트: `.moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md` (모바일 stock.naver.com 기반 SPEC 작성 용도)
  - **비개발자용 종합 가이드**: [docs/theme-analysis-guide.md](docs/theme-analysis-guide.md) — V1→V2 변천사, 4가지 결정(D-1~D-4) 친절 설명, FAQ, 용어집

### Added (SPEC-NAVER-THEME-002)

- **네이버 모바일 m.stock.naver.com 기반 V2 backend 모듈** (SPEC-NAVER-THEME-002 v1.0.1)
  - **V1+V2 cohabitation 정책**: V1 desktop HTML 모듈 무수정 + V2 mobile JSON API 신규 모듈
  - **신규 모듈**: `backend/services/naver_theme_v2/{__init__,service,crawler,parser,config}.py` (5 모듈)
  - **신규 REST API 엔드포인트**:
    - `GET /api/themes/v2/snapshot?top_n=20&leaders_per_theme=3` — V2 mobile JSON 기반 5종 records list + metadata (~30s, V1 shape 호환)
    - `GET /api/themes/v2/quick?top_n=20` — V2 themes only (≤10s)
  - **ThemeAnalysisResult shape**: V1과 동일 (frontend forward-compat) — `themes_df`, `strong_themes_df`, `stocks_df`, `leaders_df`, `multi_theme_stocks_df`
  - **신규 의존성 0건** (REQ-NT2-C-004): 기존 requests/pandas/numpy/pydantic/fastapi 활용
  - **bare except 0건** (REQ-NT2-C-005): RequestException, Timeout, JSONDecodeError, ValidationError 등 specific exception만 catch
  - **v1.0.1 amendment** (commit b1c24eb): V1 컬럼 호환성 검증 강화 + acceptance.md 14-AC 정정
  - **race condition fix** (ba3f20c): ThemeAnalysis.tsx useEffect cleanup 패턴 (V2와 무관, 본 SPEC과 함께 ship)
  - **단위 테스트**: 24개 pytest PASS + 라이브 1개 PASS (`@pytest.mark.live test_collect_and_analyze_v2_live`)
  - **V1 routes 정책**: V1 endpoints `/api/themes/snapshot`, `/api/themes/quick` 등록 유지 — cohabitation rollback 경로
  - **비개발자용 종합 가이드**: [docs/theme-analysis-guide.md](docs/theme-analysis-guide.md) — V1→V2 변천사, cohabitation 정책, FAQ

### Added (SPEC-NAVER-THEME-003)

- **V2 frontend 채택 + theme_description tooltip + V2 metadata V1 alias** (SPEC-NAVER-THEME-003 v1.0.0)
  - **V2 endpoint URL swap**: `frontend/src/api/themes.ts` 가 V2 endpoint 호출 (REQ-NT3-001)
  - **TypeScript 타입 확장**: `ThemeItem.theme_description?`, `ThemeStockItem.stock_description?` optional 필드 (REQ-NT3-002, REQ-NT3-003)
  - **ThemeRankingTable hover tooltip** (D-2): theme_name 셀에 native HTML title 속성 (REQ-NT3-004)
  - **null/undefined/empty 정책** (D-4): title 속성 자체 미렌더링 — 노이즈 회피 (REQ-NT3-NF-002)
  - **ThemeAnalysis 에러 메시지 + retry 버튼** (D-1): V2 503/timeout 시 사용자 친화적 메시지 + 수동 retry. retryNonce trigger + race-safe cleanup 보존 (REQ-NT3-007). V1 자동 폴백 금지 (REQ-NT3-C-006).
  - **ThemeDetailPanel 무수정** (D-3): V2 parser inclusion_reason ← item.description 정책으로 자동 호환 (REQ-NT3-008)
  - **V2 backend metadata V1 alias**: `collected_at`, `theme_count`, `stock_count`, `elapsed_sec` 4 필드 additive 추가 (REQ-NT3-005, REQ-NT3-C-003). `_empty_result` 에도 동일 적용 (REQ-NT3-006).
  - **검증**: V1 51 PASS (회귀 0, REQ-NT3-C-002) + V2 24+5=29 PASS + frontend vitest 271 PASS (baseline diff 0, ChartGrid 1 fail pre-existing)
  - **evaluator-active PASS**: Functionality 100 / Security 90 / Craft 92 / Consistency 95
  - **신규 의존성 0건** (REQ-NT3-C-004): native HTML title 사용 (Radix Tooltip 미도입)
  - **신규 단위 테스트**: backend 5 (V2 metadata alias) + frontend vitest 4 파일 15 tests
  - **비개발자용 종합 가이드**: [docs/theme-analysis-guide.md](docs/theme-analysis-guide.md), 시리즈 회고: [.moai/learnings/SPEC-NAVER-THEME-001-003-lessons.md](.moai/learnings/SPEC-NAVER-THEME-001-003-lessons.md)
  - **v1.0.1 amendment** (D-3 reverse — UX 사용성 개선):
    - hover tooltip만으로는 description이 한눈에 안 보여 네이버 모바일 UX와 어긋난다는 사용자 라이브 검증 결과 반영
    - ThemeDetailPanel 테마명 아래 `theme_description` 본문 박스로 노출 (REQ-NT3-009 신규)
    - 주도주 카드 + 종목 테이블 각 행 뒤에 `inclusion_reason` 본문으로 펼쳐 노출 (REQ-NT3-010 신규)
    - hover tooltip(`title` 속성)은 보존 (중복 노출, AC-13 호환)
    - AC-16/17 신규 추가 (총 17 AC)
    - ThemeDetailPanel.test.tsx vitest 6 cases 추가
  - **v1.0.2 amendment** (주도주 섹션 제거 + theme_description prominent 강화):
    - 사용자 후속 신고: 테마명 직후 "주도주" 섹션이 가장 위에 위치해서 네이버 모바일의 "테마 설명 우선" UX와 어긋남
    - ThemeDetailPanel 주도주(themeLeaders) 섹션 완전 제거 (REQ-NT3-011 신규)
    - theme_description 본문 박스 스타일 강화: font-size 12→13px, color text-secondary→text-primary, padding 8/12→12/14, border-radius 6→8, border-left 3px→4px (REQ-NT3-009 강화)
    - leaders prop은 호출부 호환을 위해 optional로 유지하되 컴포넌트 내부에서 미사용
    - RankBadge 함수 미사용으로 제거
    - AC-18 신규 추가 (총 18 AC)
    - ThemeDetailPanel.test.tsx vitest 7 cases (AC-13 1 + AC-16 2 + AC-17 2 + AC-18 2)
  - **v1.0.5 amendment** (탭 전환 재 fetch 해결 — frontend localStorage 캐시 + 명시적 갱신 버튼):
    - 사용자 신고: "한 번 크롤링 했는데 다른 메뉴 갔다오면 왜 다시 크롤링을 하느라 시간을 쓰지?"
    - Root cause: backend/frontend 양쪽 캐시 0건. AppContent는 CSS display:none/flex 토글로 mount 보존되지만, 사용자가 빠른/전체 조회 모드 버튼 토글 시 매번 useEffect 재실행 → 30초 재크롤링. 페이지 새로고침 시에도 자동 30초 fetch.
    - 사용자 사용 패턴 (혼자 사용 + Chart Grid DB 수동 업데이트와 동일 모델) 반영해서 자동 fetch 최소화 + 명시적 갱신 모델로 전환
    - 해결: ThemeAnalysis.tsx에 (1) `theme-analysis-cache-{quick|full}` localStorage 캐시 — mount/mode 변경 시 cache 우선 읽기 → cache hit이면 fetch skip + 즉시 표시 (REQ-NT3-015 신규), (2) 툴바에 `🔄 갱신` 버튼 추가 (data-testid="theme-refresh-button") — 클릭 시 현재 mode 캐시 무효화 + 강제 fetch + 응답을 캐시에 재쓰기 (REQ-NT3-016 신규)
    - 캐시 schema: `{cache_version: 'v1', saved_at: ISO-8601, data: ThemesSnapshotResponse}`. cache_version mismatch 시 자동 무효화 → 향후 backend schema 변경 대비
    - 자동 만료 없음 (수동 갱신 모델). 갱신 버튼만 trigger
    - AC-22/23/24 신규 (총 24 AC). ThemeAnalysis.test.tsx vitest 3 cases 추가 (mount cache hit / refresh button / mode별 cache key 분리)
    - **수정 범위**: ThemeAnalysis.tsx 1 파일 + 테스트 1 파일. backend 무수정, V1 무수정, 의존성 변경 0
    - **검증**: vitest 284/285 PASS (ChartGrid 1 fail pre-existing baseline 동일, REQ-NT3-NF-004), 회귀 0건
  - **v1.0.4 amendment** (backend strong_themes_df description 머지 누락 수정):
    - 사용자 후속 신고: v1.0.3 default 'full' 적용 후에도 화면에 description 미노출
    - 라이브 진단 결과: backend snapshot 응답의 `themes` 배열에는 description=274자 정상이지만 `strong_themes` 배열에는 description=0(empty). frontend는 `data?.strong_themes ?? data?.themes`로 strong_themes 우선 사용 → 사용자가 클릭한 테마는 description=null인 strong_themes에서 매핑됨 → ThemeDetailPanel D-4 hidden
    - Root cause: `service.py:73`에서 `strong_themes_df = build_strong_themes(themes_df, ...)`를 detail 호출 전에 빌드, line 92-95 detail 머지가 `themes_df`에만 적용됨. v1.0.0 RUN 시점부터 잠재된 버그가 v1.0.3 default 'full'로 수면 위로
    - 해결: detail loop 종료 후 `strong_themes_df["theme_description"] = strong_themes_df["theme_id"].map(themes_df.set_index("theme_id")["theme_description"].to_dict())` 1줄 추가 (REQ-NT3-014 신규)
    - backend pytest AC-21 신규 (총 21 AC)
    - frontend 변경 0, V1 backend 무수정, 의존성 변경 0
  - **v1.0.3 amendment** (default 'full' mode + 빠른 조회 advisory):
    - 사용자 후속 신고: v1.0.2까지 본문 박스가 코드에 추가됐으나 화면에 표시 안 됨
    - Root cause: backend `service.py:92-95`가 detail 호출 시에만 `theme_description`을 themes_df에 머지. 빠른 조회 모드는 detail skip → backend가 description=null 반환 → frontend D-4 hidden 정책으로 본문 박스 미표시. parser.py 주석에도 "list 응답 sectorDescription은 항상 null" 명시되어 있고 라이브 list endpoint 호출로 재검증 완료.
    - ThemeAnalysis.tsx의 default mode를 `'quick'` → `'full'`로 변경 (REQ-NT3-012 신규). 첫 진입 시 자동 snapshot 호출 → description 정상 표시 (~30초).
    - 사용자가 "빠른 조회"를 토글한 경우 ThemeRankingTable 아래에 회색 advisory 박스 노출 — "빠른 조회 모드는 테마 설명과 종목 편입설명을 포함하지 않습니다" + "전체 조회" CTA 안내 (REQ-NT3-013 신규).
    - AC-19/20 신규 추가 (총 20 AC).
    - ThemeAnalysis.test.tsx vitest 4 cases (AC-11 1 + AC-12 1 + AC-19 1 + AC-20 1).
    - backend, V1 backend, 의존성 변경 0.

### Changed (SPEC-AI-REPORT-003)

- **AI 리포트 Fast/Deep 양쪽 모드를 Perplexity API 에서 Codex CLI 로 전면 전환** (SPEC-AI-REPORT-003 v1.0.1)
  - **Fast Mode** (`POST /api/ai-report/{code}?mode=fast`, 기본): Codex CLI subprocess + 30s heartbeat SSE + 256자 청크 스트리밍. ChatGPT 구독 기반 무료 호출 (별도 API 키 불필요, `codex login` 으로 인증).
  - **Deep Mode** (`?mode=deep`): 5소스 병렬 수집 (Codex/Brave/Tavily/Naver/YouTube) + Claude CLI 합성. 기존 Perplexity 슬롯이 Codex 슬롯으로 교체.
  - **Backward compat**: `?mode=perplexity` 는 deprecated alias → Fast Mode 로 라우팅 (warning 로그). `?mode=fast` 가 권장.
  - **신규 모듈**:
    - `backend/services/codex_cli_runner.py` — `run_codex_research()` async + `CodexResult` dataclass + `load_codex_prompt()`
    - `backend/services/ai_report_service.py::stream_codex_fast()` — Fast Mode SSE 어댑터 (heartbeat + 청크)
    - `backend/services/deep_research_collector.py::_collect_codex()` — Deep Mode codex 슬롯 (1회 재시도 + 결정론적 실패 분기)
    - `backend/services/deep_research_collector.py::prepare_staging_directory()` + `finalize_staging_directory()` — staging 2단계 분리 (Codex `--output-last-message` 가 호출 시점에 경로 필요)
    - `backend/prompts/codex_prompt.md` — Codex 전용 8섹션 프롬프트 (`〈종목명〉`/`〈종목코드〉` 플레이스홀더)
  - **NFR-001 (Codex 타임아웃)**: 단일 호출 600s + 1회 재시도 600s = 최대 1200s. `_DEFAULT_TIMEOUTS["codex"] = 1200.0` 으로 외부 timeout 보장.
  - **NFR-002 (쿼터 보호)**: `AI_REPORT_DAILY_QUOTA` 와 `AI_REPORT_DEEP_DAILY_QUOTA` 가 ChatGPT 구독 일일 한도 보호 목적으로 재정의 (값 변경 없음).
  - **삭제된 자산**:
    - `backend/services/perplexity_cache.py` (TTL 10분 캐시 레이어, Codex 대체로 불필요)
    - `backend/prompts/perplexity_prompt.md` (Codex 전용 템플릿으로 교체)
    - `ai_report_service.py` 의 `stream_perplexity`, `SYSTEM_PROMPT`, `SEARCH_DOMAIN_FILTER`, `_load_prompt_template`, `load_prompt`
    - `deep_research_collector.py` 의 `_collect_perplexity`, `_normalize_perplexity`
    - `.env.example` 의 `PERPLEXITY_API_KEY`
  - **프론트엔드**:
    - `frontend/src/types/aiReport.ts::SourceName`: `"perplexity"` → `"codex"`
    - `frontend/src/types/aiReport.ts::PhaseEvent` 에 `codex_fast_start`, `codex_fast_progress`, `staging_prepared` 이벤트 추가
    - `frontend/src/api/aiReport.ts::AiReportMode`: `"perplexity"` → `"fast"`
    - `frontend/src/components/ProgressPanel.tsx`: 라벨 `"Codex 심층 리서치"`, codex char_count KB 단위 표시
    - `frontend/src/components/AiReportModal.tsx`: 기본 mode='fast', 설명 문구에 Codex CLI 특성 (2~9분, ChatGPT 구독) 반영
  - **품질 검증**: Backend 134/134 + Frontend 19/19 PASSED. 커버리지: codex_cli_runner 81%, deep_research_collector 89%, deep_research_service 84%, ai_report_service 82%.
  - **자동 스모크 (2026-04-25)**: Fast Mode 8m44s 통과 (phase 18/data 230/done 1/error 0), Deep Mode 19분 end-to-end 통과 (4/5 gate → 합성 done). `backend/reports/삼성SDI/2026-04-25{,_2}.md` 자동 저장.

### Added (SPEC-MINERVINI-001)

- **Mark Minervini Trend Template 스크리너 (데이터 계층 + 평가 엔진)** (SPEC-MINERVINI-001 v1.0.3)
  - 새 요청 플래그: `POST /api/screen { "minervini_trend_template": true }` → 8조건 strict gate
  - 8조건 (research.md §2.1 기준): close > SMA150/200, SMA150 > SMA200, SMA200 > 20일 전 SMA200, SMA50 > SMA150/200, close > SMA50, close ≥ LOW_52W × 1.25, close ≥ HIGH_52W × 0.75 && close ≤ HIGH_52W, rs_12m ≥ 70
  - 응답 필드 신규 추가: `StockItem.trend_template_score: int | None` (strict gate 통과 시 고정 `8`, 플래그 OFF 시 `None`)
  - `ScreenRequest.patterns` 제한 완화: `max_length=3` → `max_length=5` (SPEC-PRESET-001 에서 활용 예정)
  - **일봉 파이프라인 신규 컬럼** (`stock_prices`): `SMA150` (150일 SMA), `LOW_52W` (250 거래일 rolling min), `SMA200_20D_AGO` (SMA200 의 20 거래일 shift). 기존 `High52W` 는 window `252 → 250` 으로 변경 (SPEC A2).
  - **stock_meta 스냅샷 컬럼 신규 추가**: `sma150`, `low52w`, `sma200_20d_ago`. 기존 `high52w` 는 값만 갱신.
  - **멱등 ALTER**: 레거시 DB 에도 PRAGMA 기반 컬럼 존재 검사 후 누락 시에만 `ALTER TABLE ADD COLUMN` (defense-in-depth).
  - **Defense path (REQ-MIN-007)**: 신규 컬럼이 누락된 레거시 DB 에서 `minervini_trend_template=true` 요청 시 HTTP 200 + empty 응답 + WARN 로그. 기존 필터는 영향 없음.
  - 신규 모듈/함수:
    - `my_chart/db/daily.py::_compute_minervini_indicators(df)` — 4개 rolling/shift 지표 계산
    - `backend/services/meta_service.py::_ensure_meta_minervini_columns(conn)` — PRAGMA 기반 멱등 ALTER
    - `backend/services/screen_service.py::_build_minervini_where()` — 8조건 AND SQL 상수 빌더 (`@MX:NOTE`)
    - `backend/services/screen_service.py::_minervini_columns_available(conn)` — PRAGMA 가드
    - `backend/services/screen_service.py::screen_stocks()` — strict-gate invariant (`@MX:ANCHOR` + `@MX:REASON`)
  - **프론트엔드 타입**: `frontend/src/types/filter.ts` 에 `ScreenRequest.minervini_trend_template?: boolean | null`, `StockItem.trend_template_score?: number | null` 추가 (UI 변경은 SPEC-PRESET-001 에서 다룸).
  - **테스트**: 28개 pytest 통과 (Group A rolling 정확성 6 / B meta 멱등 ALTER 3 / C WHERE + strict-gate 점수 11 / D 회귀 4 / E defense path 3). 커버리지: `screen_service` ~94%, `meta_service` ~96%, `daily.py` 신규 로직 ~100%.
  - **배포 전략 (v1.0.2 Primary path)**: 기존 `daily.db` / `weekly.db` 파일 삭제 후 `db-update` 파이프라인 전체 재실행. 상세 절차는 spec.md §11.4 참조.
  - **Out of scope** (후속 SPEC): 부분 매칭 점수 (6/8 등), VCP 패턴, 거래량 돌파, 시장 환경 필터, UI 프리셋 (SPEC-PRESET-001).

### Added (SPEC-AI-REPORT-002)

- **AI 리포트 심층 분석 모드 (Deep Research Synthesis)** (SPEC-AI-REPORT-002 v1.0.3)
  - 새 엔드포인트 파라미터: `POST /api/ai-report/{code}?mode=deep`
  - 5-소스 병렬 수집: Perplexity sonar-reasoning-pro + Brave + Tavily + Naver + YouTube
  - `/tmp/analysis_<code>_<uuid>/` 격리 staging 디렉토리
  - Claude Code CLI 헤드리스 합성 (subprocess, OAuth 세션, default Sonnet)
  - SSE stream-json → SSE 어댑터 (data/done/error/phase 이벤트)
  - 자동 리포트 저장: `backend/reports/<stock_name>/<date>.md`
  - 신규 모듈:
    - `backend/services/deep_research_collector.py` — 5-소스 병렬 수집 + 스테이징
    - `backend/services/claude_cli_streamer.py` — CLI subprocess + stream-json 파서
    - `backend/services/deep_research_service.py` — 오케스트레이션 + Deep rate limit
    - `backend/services/perplexity_cache.py` — TTL 10분 메모리 캐시 (시나리오 C 비용 절감)
    - `backend/prompts/stock_synthesis_prompt.md` — 합성 시스템 프롬프트 (절대규칙 A/B/C)
- **프론트엔드 2단 모드 토글 + 명시적 시작 버튼**
  - 헤더: "빠른 분석" / "심층 분석 (수분 소요)" 토글 (ARIA tablist)
  - AI 버튼 클릭 시 idle 상태로 모달 오픈, 사용자가 모드 선택 후 "분석 시작" 버튼 클릭
  - 빠른 → 심층 시 같은 종목의 Perplexity 결과 캐시 재사용 (TTL 10분)
  - done 상태에서 "심층 분석으로 다시 시도" / "빠른 분석으로 다시 시도" 모드 라벨 버튼
  - 캐시 재사용 힌트 표시
- **신규 환경변수**:
  - `BRAVE_API_KEY`, `TAVILY_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `YOUTUBE_API_KEY`
  - `AI_REPORT_DEEP_DAILY_QUOTA` (default 15)
  - `AI_REPORT_DEEP_BURST_LIMIT` (default 1)
  - `AI_REPORT_DEEP_MODEL` (default sonnet, "opus"로 변경 가능)
- **Playwright e2e 테스트**: `frontend/e2e/ai-report-deep.spec.ts` (4 시나리오)
- **테스트 추가**: 백엔드 95개 (Phase A 20 + B 39 + C 22 + D 14), 프론트 7개 (모달 토글 + retry)

### Changed (SPEC-AI-REPORT-002)

- `backend/routers/ai_report.py`: `mode: str = Query("perplexity", pattern="^(perplexity|deep)$")` 파라미터 추가, 가드 체인 분기
- `backend/main.py` lifespan: `shutil.which("claude")` 체크 (warning) + `_load_synthesis_prompt()` fail-fast + `/tmp` 7일 초과 staging 디렉토리 정리
- `frontend/src/components/AiReportModal.tsx`: 모달 헤더 토글 + idle 상태 launcher + done 상태 retry 버튼
- `frontend/src/hooks/useAiReport.ts`: `startStream(code, mode='perplexity')` 시그니처 확장
- `frontend/src/api/aiReport.ts`: URL에 `?mode=${mode}` 추가
- `frontend/src/components/ChartGrid/ChartCell.tsx`: AI 버튼 클릭 시 즉시 시작 X → idle 상태 모달 오픈

### Fixed (SPEC-AI-REPORT-002)

- v1.0.1: Claude CLI timeout 180s → 600s (10분) — Sonnet 5-소스 합성에 180s 부족 (FR-007/NFR-002 완화)
- v1.0.1: Claude CLI 인자 보정 — `--cwd` 옵션은 CLI 2.1.110에 없음. `--add-dir` + subprocess `cwd=` kwarg + `--permission-mode bypassPermissions` + `--model claude-sonnet-4-6` 명시
- v1.0.1: collector source별 timeout — perplexity 120s, tavily 90s, brave/naver/youtube 15s (이전 일괄 10s는 Perplexity가 항상 timeout)
- v1.0.2: Naver/YouTube query에 종목 코드 포함 (예: "우리로" → "우리은행/우리금융" 결과 섞임 방지)
- v1.0.2: 학습 데이터 면책 차단 — synthesis prompt 절대 규칙 A/B/C (사전 학습 지식 사용 금지, "보고서 작성 불가" 면책 금지, 종목 코드 신뢰)
- v1.0.3: 시나리오 C 비용 절감 — Perplexity 캐시 재사용 (HTTP 호출 0)
- v1.0.5: 합성 단계 LimitOverrunError 방어 — `asyncio.create_subprocess_exec(limit=4MB)`로
  StreamReader 버퍼 상향 (기본 64KB로는 긴 stream-json 라인에서 터짐). 미처리 예외도
  `event: error`로 변환해 프론트에 전달 (이전엔 연결만 끊겨 "대기중" 상태로 보임).
  `logging.basicConfig(level=INFO)`로 애플리케이션 로그 가시화.
- v1.0.4: 심층 분석 진행 상태 패널 (Progress Panel) — per-source 실시간 SSE `event: phase`
  - 백엔드 `collect_all_sources`에 `progress_callback` 추가 + `asyncio.wait(FIRST_COMPLETED)`로 소스 완료 순 이벤트 emit
  - 신규 phase 이벤트: `source_start` / `source_done` (success, duration_ms, count, cached, error) / `collecting_done` / `staging_done` / `synthesis_start` / `synthesis_first_chunk`
  - `SourceResult.cached` 필드 — Perplexity 캐시 재사용 여부 표시
  - 프론트: `<ProgressPanel>` 컴포넌트 (5소스 + 합성 상태 + 캐시 재사용 라벨)
  - `useAiReport` 훅에 `progress` state 추가, `createAiReportStream`에 optional `onPhase` 콜백 추가
  - 테스트 +13: ProgressPanel 11, AiReportModal 렌더 조건 2
- e2e UX 버그: AiReportModal done 상태에서 retry 버튼 누락 → done && markdown 분기에 추가

### Notes (SPEC-AI-REPORT-002)

- 검증 종목: **대한광통신 (010170)** — 풀 합성 3분 9초, 11.8KB 리포트 정상 생성
- 검증 종목: **우리로 (046970)** — 동명이인 모호 케이스, 면책 차단 후 14.7KB 리포트 정상 생성
- 회귀: SPEC-001 30 테스트 모두 통과 (AC-017 byte-identical contract preserved)
- 알려진 이슈: `test_sector_advanced.py` 5건 — 다른 테스트 파일의 SimpleNamespace 스텁이 my_chart.registry를 덮어쓸 때 발생, SPEC-002 코드와 무관

### Fixed (SPEC-MARKET-BREADTH-001 v0.1.1, 2026-08-13)

- **시장 개요 breadth 히스토리 — 정규 주간 격자 적용으로 구간 절단 결함 수정** (M1~M6, `run_commit_sha` `dbcbab2`)
  - **결함**: `my_chart/analysis/market_breadth.py:472` `compute_breadth_history()`가 주봉 DB에서 최근 N개 **원시 distinct 날짜**를 직접 뽑아 썼다. 이 DB는 다중 날짜 ISO 주를 포함하므로, 실서비스 호출 `compute_breadth_history(weekly_db_path, "KOSPI", weeks=52)`(`backend/services/market_service.py:132`)가 반환한 52바는 실제로는 겨우 **21개 ISO 주(139일)**만 덮었다(기대: 52주/358일). 이제 `SPEC-SECTOR-GRID-001`의 정규 주간 격자(`compute_weekly_grid` → `history()`)를 단일 원천으로 소비한다.
  - **중요 — 사용자 확인 필요**: **차트의 포인트 개수는 그대로 52개다.** "점이 줄어든 것 아니냐"는 신고가 있다면 이번 변경 때문이 아니다 — 바뀐 것은 포인트 **개수**가 아니라 차트가 덮는 **구간(span)**이다. 프로즌 실측: `span_days` 139일 → **358일**, 고유 ISO 주 21개 → **52개**, 마지막 점이 진행 중인 주(`2026-08-11`)에서 직전 완료 주(`2026-08-07`)로 이동. 차트 제목도 `12-week`(호출부 `weeks=52`와 불일치하던 표기)에서 `Market Breadth (1-year)`로 정정했다(`frontend/src/components/MarketOverview/BreadthChart.tsx:156`).
  - 하류 소비자 `detect_choppy()`의 판정 입력 창도 함께 확대된다. 프로즌 스냅샷 기준으로는 판정 결과(`False`) 자체는 변하지 않았으나, 조건식 입력값(최근 4주 `pct_above_sma50`)은 `[42.42, 57.58, 57.58, 72.73]` → `[20.59, 18.18, 24.24, 57.58]`로 실질 이동했다 — 이 스냅샷에서 뒤집히지 않았다는 것이 임계값이 항상 안전하다는 뜻은 아니며, 임계값 자체는 재튜닝하지 않았다.
  - 검증: `pytest tests/test_market_breadth_grid.py tests/test_market_breadth.py -q` 신규 34 passed + 기존 20 passed(무회귀), 전체 스위트 baseline 584 passed/8 failed/68 skipped/25 errors → **618 passed**(+34)/8 failed(무변화)/68 skipped/**1 xpassed**(AC-MBR-004, 비게이팅)/25 errors(무변화, `tests/fnguide/` 범위 밖). 선행 SPEC-SECTOR-GRID-001 게이팅 스위트 84 passed 유지(allowlist 5행 동기화 포함). 프론트엔드 `npx vitest run src/components/MarketOverview` 5 files/50 passed.
  - AC-MBR-001~010 전항 PASS (AC-MBR-004는 XPASS·비게이팅으로 문서화된 한계).
  - **미결(사용자 확인 대기)**: `compute_breadth`의 `market` 인자가 종목을 필터하지 않아 KOSPI/KOSDAQ이 동일 모집단 위에서 계산된다 — 다만 `breadth.kosdaq`는 스키마 선언만 있고 실사용·렌더 0건이라 사용자 비가시적 잠재 결함이다(의도/미구현 여부 확인 필요). `detect_choppy` 임계값 재튜닝 여부도 별도 확인 필요.

## [1.1.0] - 2026-03-08

### Added

- **RS Line (상대강도선) 차트 오버레이** (SPEC-RS-LINE-001)
  - `my_chart/db/daily.py`: RS_Line 컬럼 추가 및 계산 로직
    - KOSPI 지수 데이터 자동 조회
    - 매일 RS_Line = 종목 종가 / KOSPI 종가 계산
    - NULL 값에 대한 폴백 처리
  - `backend/schemas/chart.py`: ChartResponse에 `rs_line` 필드 추가
  - `backend/services/chart_service.py`: 일일/주간 차트 API에 RS_Line 데이터 포함
  - `frontend/src/types/chart.ts`: ChartResponse 인터페이스에 `rs_line` 추가
  - `frontend/src/components/ChartGrid/ChartCell.tsx`: RS Line 시각화
    - IBD 스타일 숨겨진 Y축 표시
    - 반투명 자주색(rgba(108, 92, 231, 0.5)) 렌더링
    - 토글 버튼으로 표시/숨기기 (세션 기간만 유지)
  - 주간 차트에도 동일하게 적용되는 일관된 스타일

## [1.0.0] - 2026-03-04

### Added

- **KRX 세션 기반 인증** (SPEC-KRX-AUTH-001)
  - `my_chart/krx_session.py`: KRX 세션 관리 모듈
    - `patch_pykrx_session()`: pykrx webio를 인증된 세션으로 monkey-patch
    - `login_krx(id, pw)`: 3단계 KRX 인증 (JSESSIONID 획득 → JSP 세션 초기화 → 실제 로그인)
    - `init_session()`: KRX_ID/KRX_PW 환경변수에서 자동 초기화
    - `get_market_cap_safe(date)`: 3단계 폴백 (pykrx → sectormap Excel → 빈 DataFrame)
  - `.env.example`: 인증 정보 템플릿
  - `python-dotenv` 의존성 추가

- **설정 개선**
  - `my_chart/config.py`: dotenv 로드 및 자동 세션 초기화
  - 7개 파일에서 `stock.get_market_cap()` → `get_market_cap_safe()` 교체

### Changed

- Type hints 및 Pyright 호환성 개선
  - `my_chart/krx_session.py`: 타입 안전성 강화 (monkey-patch 함수의 Any 타입 적절한 처리)

### Fixed

- Pyright 타입 오류 수정
  - `my_chart/krx_session.py`: pandas 타입 힌트 개선, type: ignore 주석 추가
