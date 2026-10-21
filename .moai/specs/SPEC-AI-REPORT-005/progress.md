# SPEC-AI-REPORT-005 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-10-21T00:00:00+09:00
- plan_status: audit-ready (v0.3.1, plan-audit PASS)
- plan_audit:
  - 1회차 FAIL 0.77 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-1.md` (B1~B7·S1~S6·M1~M5 → v0.2.0에서 반영)
  - 2회차 FAIL 0.88 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-2.md` (N1~N5 → v0.3.0에서 반영)
  - 3회차 PASS 0.92 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-3.md` (R3-1 → v0.3.1에서 반영, R3-2·R3-3은 아래 부채)
- plan_debt (사용자 승인 2026-10-21, run 단계 처리):
  - R3-2: AC-AIR5-014 되돌림 (r3)이 대상 테스트를 지정하지 않아 결과가 비결정적이다. → run 단계는 (r1)·(r3)에 쓸 테스트 이름을 정확히 정해 `progress.md §E.2`에 적고, 수집 성공 여부와 무관한 단언(실행기 호출·작업 진행)만 가진 테스트를 고르거나 (r2)의 작업 서비스 변형으로 (r3)를 수행한다.
  - R3-3: 첨부 항목이 `section == "auditor_report"`·`document == "attachment"`를 갖는지 단언하는 AC가 없다. → run 단계는 새 AC를 만들지 말고 AC-AIR5-008 테스트 안에 eleId 1·2 항목에 대한 두 단언을 추가한다.
- R3-1 run 단계 주의: 네트워크 가드 범위는 테스트 파일 이름으로 판정하고, AC-AIR5-014 #4를 되돌림 관측보다 먼저 실행한다.
- artifacts: spec.md, plan.md, acceptance.md, research.md, progress.md
- counts: REQ 16개(REQ-AIR5-001~016), AC 16개(AC-AIR5-001~016) — Tier M 상한(각 16) 이내
- needs_clarification: 0건 (미확인 DART 사실 F4·F8은 run 단계 M1 관측 항목, research.md §3)
- baseline: 이전 실행 2건에서 대상 감사 결함 6종 모두 발생(research.md §2, P14), 매니페스트 = 원본 재생성 결과(P7)

## §F Phase 4 Mode Selection

- 입력: Tier M · 범위 약 10~12개 파일(백엔드 모듈·테스트·conftest·하네스 지침·매니페스트·프론트 3개) · 도메인 3(백엔드, 하네스, 프론트) · 코딩 중심 · 동시성 이점 낮음
- direct: 미선택 — 다중 파일 구현
- serial: **선택** — 코딩 중심 작업, 마일스톤 순서 의존(M1 픽스처 → M2 모듈 → M3 연결 → M4 지침 → M5 라이브)
- fanout: 미선택 — 연구 중심이 아님
- sweep: 미선택 — 기계적 대량 변환 아님
- Decision: serial
- 근거: 코딩 작업은 병렬화 이점이 작고 마일스톤이 앞 단계 산출물(픽스처·모듈)에 의존한다. 사용자 선택에 따라 마일스톤마다 보고 후 다음으로 진행한다(2026-10-21 Implementation Kickoff Approval). 실행자는 공용 체크아웃에서 작업하는 manager-develop 역할의 general-purpose 에이전트(SPEC-AI-REPORT-004와 같은 방식; manager-develop 정의는 자동으로 별도 작업 공간에 격리됨).

## §E.2 Run-phase Evidence

### M1 — 픽스처와 데이터 모양 확정 (2026-10-21, HEAD 9f9e09e 기준)

산출물: `backend/tests/fixtures/dart/` — `recorded/`(녹화 9개 + `request_log.json`), `synthetic/`(합성 6개), `capture_dart.py`(수집), `build_synthetic.py`(합성 생성), `index_keys.json`(색인 키 집합), `README.md`(수집 시각·명령·요청 수·출처). 운영 코드·conftest 없음(M2·M3 몫).

#### 요청 기록

- 명령: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/dart/capture_dart.py backend/tests/fixtures/dart/recorded`
- 1차(11:45 KST): 첫 POST가 httpx 폼 직렬화 오류(`TypeError: sequence item 1: expected a bytes-like object, tuple found`)로 본문 전송 중 중단 — 응답·파일 없음. 상한 계산에 1건으로 포함.
- 2차: 9회, 모두 HTTP 200, 시작 시각 `2026-10-21T11:46:27.901+09:00` ~ `11:46:36.758+09:00`, 간격 1.1초 이상, 응답 0.057~0.155초. 합계 10회(중단 1 포함).
- 상한 때문에 받지 않은 것: 사업보고서 감사보고서 본문 구간 1건(위임 범위의 9번째 항목). M2의 `auditor_report` 본문은 합성 바이트로 대신한다 — Gap G-M1-1.

#### F4·F8 관측표

| 사실 | 가정(research §3) | 관측 | 근거 | 판정 |
|---|---|---|---|---|
| F4 `finalReport=recent` 목록에서 정정 전 원본이 빠지는가 | 미확인 | 하나기술(299030) `finalReport=recent` 정기보고서 12행에 `[기재정정] 사업보고서 (2025.12)`(`20260814003680`), `[기재정정] 사업보고서 (2024.12)`(`20250814004212`), `[기재정정] 사업보고서 (2023.12)`(`20240422000338`)만 있고 같은 기간 원본 사업보고서 행은 0개. 같은 기간 행이 둘 이상인 경우 0건 | `recorded/list_299030_recent.html` (요청 9) | 가정과 일치: `recent` 조회는 기간당 최신 제출본 하나만 보여 준다. REQ-AIR5-006의 "같은 기간이면 최신 접수" 규칙은 안전장치로 유지(합성 `list_020150_correction.html`이 검사) — SPEC 변경 불필요 |
| F4 보조 | — | `finalReport` 없이 받은 목록은 관측하지 않았다(요청 상한). 원본 사업보고서들이 3년 창 안에 실제로 있다는 것은 추론(정정은 원본을 전제) | — | Gap G-M1-2 |
| F8 사업보고서 첨부 감사보고서 목차 순서 | "감사인 보고서 본문 → `(첨부)` 재무제표"인지 미확인 | 연결감사보고서(`dcmNo=11105314`) 노드: 1 `감   사   보   고   서`, 2 `독립된 감사인의 감사보고서`, 3 `(첨부)연 결 재 무 제 표`, 4 `주석`, 5 `외부감사 실시내용` | `recorded/main_20260310002974_11105314.html` (요청 8) | 가정과 일치: 감사인 보고서(1·2)가 `(첨부)` 앞에 온다. 반기 검토보고서와 달리 `주석` 뒤에 5번 노드가 더 있으나 REQ-AIR5-008("`(첨부)` 앞 텍스트만")·plan T5("`(첨부)` 앞 노드")로 자동 제외 — SPEC 변경 불필요 |
| F8 보조: 첨부 선택 | — | 사업보고서 첨부 7종: `감사보고서` 11105293, `감사의감사보고서` 11105318, `내부감시장치에대한감사의의견서` 11105320, `내부회계관리제도운영보고서` 11105321, `연결감사보고서` 11105314, `영업보고서` 11105319, `정관` 11105317 | `recorded/main_20260310002974.html` | M2 주의: `감사보고서` 부분 일치는 `감사의감사보고서`를 잡는다 |

#### research §5 기댓값 대조

- `recorded/list_020150_recent.html`: 12행, 고유번호 집합 `{'00113997'}`, 접수번호·순서가 research §5 12행과 같다(`20260814000373` … `20231114000877`). 2026.09 분기보고서 없음 → **§5 기댓값 변경 없음**, AC-AIR5-006 리터럴 그대로.
- 반기 목차 노드가 research P11과 같다: 요약재무정보 `11527102/18/233941/25639`, 연결재무제표 `19/259834/178344`, 연결재무제표 주석 `24/438182/1703030`, 재무제표 `58/2141216/124954`, 재무제표 주석 `63/2266174/1375036`. 첨부 `11527104` 반기검토보고서, `11527105` 반기연결검토보고서. 첨부 목차 노드 4개(P12와 같음). 본문 바이트 53,931·492,989(P13과 같음).
- 새 측정값(최신 사업보고서 `20260310002974`, 본문 `dcmNo=11105315`): 요약재무정보 `eleId=18 offset=250218 length=25415`(제39·38·37기 3개 회계연도), 연결재무제표 `19/275884/278976`, 연결재무제표 주석 `24/554864/2182152`, 재무제표 `65/2737020/188752`, 재무제표 주석 `70/2925776/1946506`.
- 관측(SPEC 변경 불필요, M2 참고): 목록 순서는 접수 순이다. 하나기술은 정정 사업보고서(2025.12)와 반기보고서(2026.06)가 같은 날 접수되어 정정본이 첫 행이다. 020150에는 해당 없음.

#### index.json 키 집합

`backend/tests/fixtures/dart/index_keys.json` = acceptance.md §B. 대조 명령(이번 실행): §B 줄의 백틱 토큰과 JSON을 집합 비교 → `top True 9`, `company True 2`, `search True 6`, `files_item True 17`, `outcome True`, `status True`. 각 키의 값은 녹화 데이터에서 얻을 수 있다: `company.name`·`corp_code`(목록 행 회사명·`openCorpInfoNew`), `rcp_no`·`report_name`·`period`(목록 행), `section_title`·`viewer_url` 인자 6개(목차 노드), `attachment_name`(첨부 선택 목록 이름). 변경 없음.

#### 합성 픽스처

`build_synthetic.py` 실행 후 독립 파서로 확인: `list_020150_mixed_corp.html` 12행·고유번호 `{00113997, 00999999}`; `list_020150_correction.html` 13행, `20250902000123 [기재정정] 반기보고서 (2025.06)`이 `20250814003923` 앞; `list_empty.html` 0행; `no_consolidated` 재무제표 `eleId 58`·주석 `63`만; `reordered` 순서 주석(24) → 연결재무제표(19); `polluted` 연결재무제표 노드 `dcmNo ../1, offset 1&x=y, dtd a/b`(원본과 `diff` 3줄만 다름). CRLF 보존(`mixed_corp` 17,715바이트 = 원본, `cmp` 차이 4바이트).

#### TDD 메모

M1은 픽스처만 만든다(운영 코드 없음). RED 출력(E8)은 해당 없음 — M2의 첫 테스트가 RED를 남긴다.

#### Gaps

- G-M1-1: 감사·검토보고서 본문 구간 녹화 없음(요청 상한).
- G-M1-2: `finalReport` 없는 목록 미관측 — F4의 "원본이 존재한다" 쪽은 추론.
- G-M1-3: 실제 DART "결과 없음" 목록 마크업 미관측 — `list_empty.html`은 행만 지운 합성본.

### M2 — 사전 수집 모듈 (2026-10-21, HEAD d72a1e1 기준)

산출물: `backend/services/goose_dart_prefetch.py`(신규, `DartPrefetcher`·`write_disabled_index`), `backend/tests/test_goose_dart_prefetch.py`(신규, 39개). 작업 서비스 연결·conftest 가드는 M3 몫이라 손대지 않았다. 증거 폴더 `$S/aiR5/`(`.moai/state/verify/70e95898/aiR5/`, 미추적).

#### 설계 메모

- HTML 해석: 목록·첨부 선택 목록은 `bs4`(pyproject 선언 의존성, 4.14.3), 목차는 `makeToc()` 안 `nodeN['키'] = "값"` 정규식, 텍스트판은 표준 `html.parser`. 새 의존성 없음.
- 첨부 이름은 공백 제거 후 완전 일치: 연결 `연결감사보고서`·`반기연결검토보고서`·`분기연결검토보고서` 우선, 별도 `감사보고서`·`반기검토보고서`·`분기검토보고서`. 첨부 값은 엔티티를 안정될 때까지(최대 3회) 푼다.
- 보고서 선택은 행 순서가 아니라 기간 내림차순, 같은 기간은 접수번호가 큰 것(M1 관측: 목록은 접수 순).
- 감사·검토보고서 본문은 녹화가 없어(G-M1-1) 테스트가 합성 바이트로 답한다. 녹화 없는 보고서 목차는 반기보고서 목차의 접수번호만 바꾼 합성본, 녹화 없는 재무제표 구간은 작은 합성 표.
- 끄기 색인은 작업 서비스가 부를 `write_disabled_index(out_dir, code)`로 제공(REQ-AIR5-004의 색인 모양만, 스위치 판단은 M3).

#### RED (E8) — 구현 전

1. 모듈 없음: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -q` → `E   ImportError: cannot import name 'goose_dart_prefetch' from 'backend.services'`, `1 warning, 1 error in 0.53s` (`aiR5/m2_red_1_no_module.log`)
2. 공개 이름만 있고 몸체가 `NotImplementedError`인 골격: 같은 명령 → `E       NotImplementedError` … `39 failed, 1 warning in 5.68s` (`aiR5/m2_red_2_skeleton.log`)

#### GREEN

- `PY -m pytest backend/tests/test_goose_dart_prefetch.py -q` → `39 passed, 1 warning in 1.55s`

#### 대조 되돌림 관측 (acceptance §A, lessons #9)

`aiR5/mutate.py`가 변형을 하나씩 모듈에 적용 → 해당 AC 테스트 실행 → 원본 바이트로 복원(마지막 줄 `restored sha ok: True`). 34건 모두 RED (`aiR5/m2_contrast_mutations.log`):

| AC | 잡는 구현(변형) | RED 테스트 |
|---|---|---|
| 005 | (a) 첫 행 고유번호 채택 / (b) `publicType` 누락 / (c) 행 0개를 성공 처리 | `unresolved_company…[list_file0]` / `resolves_company…` / `unresolved_company…` |
| 006 | (a) 8개 / (b) 오래된 순 / (c) 같은 기간 원본 유지 / (d) 기간 대신 행 기준 | `selects_nine…` ×2 / `same_period…` ×2 |
| 007 | (a) 제목 부분 일치 / (b) 별도 우선 / (c) 모든 보고서 주석 / (d) 요약을 최신(반기)에서 / (e) `section`에 제목 | `exact_title…reordered` / `consolidated_sections…` ×3 / `summary_only…` |
| 008 | (a) 별도(목록 첫) 첨부 / (b) 첨부 노드 전부 / (c) 사업보고서 첨부 누락 | `attachment_review_and_audit_reports` ×3 |
| 009 | (a) 텍스트만 / (b) 텍스트판 해시 / (c) 파일 이름에 목차 제목 / (d) 뷰어 주소 offset·length 누락 / (e) 색인에 재무 값 키 | `index_schema_hashes_and_files` ×5 |
| 010 | (a) 예외 전파 / (b) 한 보고서 실패로 전체 중단 / (c) 실패를 `ok`로 기록 | `list_500…` / `one_failure…` ×2 |
| 011 | (a) 간격 0 / (b) `asyncio.gather` 병렬 / (c) 총 예산 무시 / (d) 크기 상한 없음 / (e) 요청당 20초 고정 / (f) 요청 수 상한 무시 | `spacing…` ×3 / `total_budget…` / `oversized…` / `request_cap…` |
| 012 | (a) 코드 검증 없음 / (b) 노드 값 그대로 / (c) 리디렉트 추적 / (d) 호스트 부분 문자열 검사 | `invalid_code…[02015]` / `polluted…` / `redirects…` / `url_guard…` |
| 002 | (b) 수집기 요청 반복이 `CancelledError`를 잡고 정상 반환 | `cancellation_propagates_from_request` |

R3-3 반영: `test_air5_008_attachment_review_and_audit_reports`가 eleId 1·2 항목마다 `section == "auditor_report"`, `document == "attachment"`를 단언한다(새 AC 없음).

#### 품질

- 커버리지(acceptance §E 방식): `PY -m coverage run --source=backend -m pytest backend/tests/test_goose_dart_prefetch.py -q` → `39 passed`; `coverage report -m --include=backend/services/goose_dart_prefetch.py` → `440 stmts, 21 miss, 95%` (`aiR5/m2_coverage.log`)
- goose 회귀: 기준선 `PY -m pytest backend/tests -k goose -q` → `201 passed, 214 deselected` (`aiR5/m2_baseline_goose.log`); M2 후 → `240 passed, 214 deselected` (= 201 + 새 39, 실패 0) (`aiR5/m2_goose_regression.log`)

#### Gaps

- G-M2-1: `ruff check` 미실행 — 가상환경·PATH에 ruff 없음(`No module named ruff`, `ruff not found`). `py_compile`만 통과.
- G-M2-2: AC-AIR5-014 #4 가드 자체 검사(`test_air5_014_guard_records_attempt`)는 conftest 가드(M3)가 있어야 의미가 있어 M3로 넘긴다. 이 테스트 모듈은 `MockTransport`만 쓰고 `HOME`·`AI_REPORT_GOOSE_HARNESS_DIR`을 임시 폴더로 바꾼다. R3-2((r1)·(r3) 대상 테스트 지정)도 M3에서 정한다.
- G-M2-3: AC-002·004·010의 작업 서비스 쪽 단언(실행기 호출 수, 상태 `cancelled`/`done`, `caplog`)은 M3. 이번에는 수집기 쪽만(취소 전파, 실패 시 정상 반환, 끄기 색인 모양).
- G-M2-4: 실제 DART 응답에서의 목차·첨부 해석은 녹화 픽스처 3종(반기·사업·첨부 목차 2)만 관측. 금융업 등 다른 목차 표기와 `분기연결검토보고서` 이름은 미관측(라이브 AC-016).

### M3 — 작업 서비스 연결·네트워크 가드·진행 단계 (2026-10-21, HEAD 06fb05f 기준)

산출물: `backend/services/goose_job_service.py`(생성자 `prefetcher` 인자·기본값 없음, 운영 `_service`에만 `DartPrefetcher()`, `_run`에서 수집 → 무결성 재검사 → 실행기, `_prefetch`가 끄기 스위치·`dart_prefetch` 이벤트·fail-open 소유), `backend/tests/conftest.py`(신규, 네트워크 가드), `backend/tests/test_goose_job_service.py`(새 테스트 15개, `mods`에 `gdp` 추가), `backend/tests/test_goose_dart_prefetch.py`(가드 자체 검사 1개), 프론트 3개(`types/aiReport.ts`·`utils/gooseJob.ts`·`components/ProgressPanel.tsx`) + 고정 테스트 2개 갱신. 증거 `$S/aiR5/m3_*.log`.

#### 설계 메모

- 끄기 스위치(`AI_REPORT_GOOSE_DART_PREFETCH` 값을 공백 제거 후 `"0"`과 비교)는 작업 서비스만 본다. 꺼지면 `write_disabled_index`로 `outcome: disabled` 색인을 쓰고 이벤트 없이 실행기로 간다.
- 무결성 재검사는 수집기가 주입된 서비스에서만 한다(스위치 `0`이어도 수행 — 비용이 작고 수집기 없는 기본값의 동작은 그대로). 재검사 실패는 종료 훅을 `("error", "integrity")`로 부르고 `error`/`integrity`로 닫는다.
- 네트워크 가드: `goose_network_attempts`(기록 목록 + 대체 함수 설치)와 자동 픽스처 `_goose_network_guard`(종료 때 `network attempt in goose test: <기록>` 단언)를 나눴다. 범위는 `Path(str(request.node.fspath)).name`의 접두어(R3-1). pytest 9.0.2에서 `fspath`는 legacypath 플러그인이 제공(경고 없음).
- 프론트 `dart_prefetch`가 맨 앞이라, 수집 단계가 없는 작업(수집기 없음·스위치 `0`)에서는 진행 패널에 `건너뜀`으로 보인다(기존 `stageStates` 규칙).

#### RED (E8) — 구현 전

1. 가드 자체 검사: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_014_guard -q` → `E       fixture 'goose_network_attempts' not found`, `39 deselected, 1 warning, 1 error in 0.58s` (`aiR5/m3_red_1_guard.log`)
2. 작업 서비스: `PY -m pytest backend/tests/test_goose_job_service.py -k air5 -q` → `E       TypeError: GooseJobService.__init__() got an unexpected keyword argument 'prefetcher'` ×12, `13 failed, 2 passed` (통과 2개는 수집기 없는 기본값의 현재 동작을 고정하는 `default_constructor_has_no_prefetch`·`no_dart_prefetch_stage…[no_prefetcher]`) (`aiR5/m3_red_2_jobservice.log`)
3. 프론트: `npm --prefix frontend run test -- gooseJob ProgressPanel` → `Tests 4 failed | 10 passed (14)` (`aiR5/m3_red_3_frontend.log`)

#### GREEN

- 가드 자체 검사 단독(R3-1 선행 조건, 되돌림 관측 전): `… -k air5_014_guard -q` → `1 passed, 39 deselected` (`aiR5/m3_green_guard_selftest.log`, 관측 직전 재실행 `aiR5/m3_guard_selftest_preprobe.log`도 `1 passed`)
- `PY -m pytest backend/tests/test_goose_job_service.py backend/tests/test_goose_dart_prefetch.py -k air5 -q` → `55 passed, 37 deselected` (`aiR5/m3_green_air5.log`)
- 프론트 대상: `Test Files 2 passed (2)`, `Tests 14 passed (14)` (`aiR5/m3_green_frontend_targeted.log`)

#### 대조 되돌림 관측 (`aiR5/m3_mutate.py` → `aiR5/m3_contrast_mutations.log`, 마지막 줄 `restored sha ok: True`)

| AC | 잡는 구현(변형) | 결과 |
|---|---|---|
| 001 | (a) 수집을 `start()` 잠금 안에서 기다림 / (b) 실행기 뒤 / (c) 수집기 호출 누락 / (d) 출력 폴더 `runs/<job_id>` / (e) 재검사 누락 / (f) 생성자 기본값 실제 수집기 | 모두 RED — (a) `prefetch_runs_outside_lock…`(1초 상한), (f)는 `default_constructor…` FAILED + 같은 테스트 `ERROR` teardown `network attempt in goose test: [(b'dart.fss.or.kr', 443)]` |
| 002 | (a) fail-open을 `except BaseException`로 / (c) 수집 호출을 `_run`의 `try` 밖에 | 둘 다 RED (`…fake_prefetch`·`…real_prefetch_request` FAILED). (b)는 M2에서 관측 |
| 003 | (b) 수집 뒤에 이벤트 / (d) 꺼도 이벤트 | RED (`…emitted_once_before_prefetch` / `…[switch_off]`) |
| 003 프론트 | (a) `GOOSE_STAGES`에서 `dart_prefetch` 제거 / (c) 표시 문구 빈 문자열 | RED `Tests 4 failed` / `Tests 1 failed` (`aiR5/m3_frontend_contrast.log`, 복원 sha 일치) |
| 004 | (a) 스위치 무시 / (b) 끈 경우 색인 없음 / (c) 끈 경우 실행기 건너뜀 | 모두 RED. (a2) "수집기 안에서만 확인"은 작업 서비스 관점에서 (a)와 같은 변형(수집기 호출 수 1)이라 같은 단언(`calls["n"] == 0`)이 잡는다 — 별도 변형 없음 |
| 010 | (e) 수집 예외 전파 | RED (`…exception_is_logged_and_runner_continues`) |

#### AC-AIR5-014 되돌림 관측 (r1~r4, R3-2 대상 테스트 지정)

가드 자체 검사 단독 통과를 먼저 확인한 뒤 실행했다. 가드는 원래 함수를 부르지 않으므로 실제 연결·DNS 조회는 없었다(기록된 시도는 대체 함수가 막은 `getaddrinfo`).

- (r1) 대상: `backend/tests/test_goose_job_service.py::test_air5_010_prefetch_failures_still_run_goose[b_connect_error]` — 실제 `DartPrefetcher`를 쓰고 단언이 수집 성공과 무관(실행기 호출 1·`done`·색인 `outcome ∈ {failed, partial}`). `_real_prefetcher`에서 `MockTransport` 주입을 빼고 `-k "test_air5_010_prefetch_failures_still_run_goose and b_connect_error"` → `1 passed, 51 deselected, 1 error`, `ERROR …[b_connect_error]`, `E       AssertionError: network attempt in goose test: [(b'dart.fss.or.kr', 443)]` (본문은 통과, teardown에서 RED)
- (r2) 생성자 기본값을 `prefetcher or goose_dart_prefetch.DartPrefetcher()`로 바꾸고 `test_goose_job_service.py` 전체 → `12 failed, 40 passed, 25 errors`; 기존 테스트 `test_ac007_same_code_twice_returns_existing_job_without_quota`·`test_done_result_emits_done_and_clears_active`·`test_b5_concurrent_starts_*`·`test_ac011_*` 등이 `ERROR` teardown `network attempt in goose test: [(b'dart.fss.or.kr', 443)]` (`aiR5/m3_revert_probes_full.log`)
- (r3) conftest 종료 단언만 `pass`로 끄고 (r1) 재실행(같은 테스트 이름) → `1 passed, 51 deselected` GREEN — fail-open이 예외를 삼킨다는 실측(N1). 기록·대체 함수는 살아 있어 실제 연결 없음
- (r4) 대체 함수가 기록을 남기지 않게 바꾸고 가드 자체 검사 → `FAILED backend/tests/test_goose_dart_prefetch.py::test_air5_014_guard_records_attempt`, `1 failed`
- 복원: `restored sha ok: True`(4개 파일 sha256 원본과 일치), `git status --short backend/services backend/tests` → 의도한 4개 경로만

#### AC-AIR5-014 격리 실행

- `PATH=/usr/bin:/bin PY -m pytest <goose 7개 파일> -q` → `256 passed, 1 warning`, 종료 단언 실패 0건(`network attempt` 0회) (`aiR5/m3_ac014_isolation.log`)
- `~/.goose-harness/runs` 개수·수정 시각 전후 동일: `before=[4 1792505284] after=[4 1792505284]` (`aiR5/m3_ac014_runs_before_after.log`)

#### 회귀 (AC-AIR5-015)

- 백엔드 goose 전체: 기준선 `PY -m pytest backend/tests -k goose -q` → `240 passed, 214 deselected` (`aiR5/m3_baseline_backend.log`) → M3 후 `256 passed, 214 deselected` (= 240 + 새 16, 실패 0) (`aiR5/m3_goose_regression.log`)
- AC-015 명령(6개 파일, 수집기 테스트 제외) → `216 passed` (`aiR5/m3_ac015_backend.log`). 착수 전 같은 명령은 직접 재지 않았다 — 기준선 240에서 수집기 테스트 39개를 뺀 201로 산출(M2 로그 `201 passed` 기준선과 일치), M3 새 테스트 15개를 더하면 216
- 프론트 전체: 기준선 `Test Files 1 failed | 96 passed (97)`, `Tests 840 passed (840)`, 실패 파일 `e2e/preset-flow.spec.ts` (`aiR5/m3_baseline_frontend_full.log`) → M3 후 `Test Files 1 failed | 96 passed (97)`, `Tests 842 passed (842)`, 실패 파일 같음 (`aiR5/m3_frontend_full.log`)
- 타입 검사 `npm --prefix frontend run typecheck`(`tsc -b`) → 기준선·M3 후 모두 종료 0 (`aiR5/m3_baseline_typecheck.log`, `aiR5/m3_typecheck.log`)
- 커버리지 `goose_job_service.py` 98%(273 stmts, 6 miss — 333-334는 끄기 색인 쓰기 실패 분기) (`aiR5/m3_coverage.log`)

#### Gaps

- G-M3-1: `ruff check` 미실행 — 가상환경에 ruff 없음(`No module named ruff`, G-M2-1과 같음).
- G-M3-2: 끄기 색인 쓰기 실패 분기(로그만 남기고 계속) 테스트 없음.
- G-M3-3: AC-003의 실제 화면 배치는 라이브 AC-016 때 눈으로 확인(비게이팅). 서버 재시작은 M4 몫이라 하지 않았다 — 실행 중 서버는 아직 옛 코드다.
- G-M3-4: AC-010 (b)~(d)의 "다른 보고서 항목 `ok`"는 M2 수집기 테스트가 맡고, M3 작업 서비스 쪽은 실행기 호출 1·`done`·색인 `failed/partial`만 단언한다.

### M4 — 하네스 지침 규칙 8과 매니페스트 (2026-10-21, HEAD 93b5ed5 기준, 서버 재시작 제외)

산출물: `backend/goose_harness_src/harness-instructions.md`(규칙 8: 8, 8-1~8-3, 8-3a, 8-3b, 8-4~8-6 추가, 1~7 변경 없음), `backend/goose_harness_src/goose-manifest.json`(재생성 — `CLAUDE.md` 해시 한 줄만 바뀜). 증거 폴더 `aiR5/m4_*`.

#### 실제 코드와 맞춘 점 (plan.md §4 초안 대비)

- 텍스트 파일 경로: 색인 `text_file`은 폴더 없는 이름(`NN_<section>.txt`, `goose_dart_prefetch.py:526-527`)이라 `runs/<job_id>/dart/` + `text_file`로 열도록 적고, 예시를 초안의 `dart/03_fs.txt`에서 실제 형식 `dart/01_financial_statements.txt`로 바꿈.
- 끄기 스위치: 작업 서비스는 스위치 0이면 `outcome: "disabled"`, `files: []` 색인을 쓴다(`goose_job_service.py:330-335`, `write_disabled_index`). 그래서 8-5를 "`index.json`이 없거나 `files`가 비어 있으면(`disabled`·`failed`·`company_unresolved` 등) 8-1~8-4를 건너뜀"으로 넓힘.
- 8-3: 검색 기록은 `search.status == "ok"`이고 DART 출처를 하나 이상 적었을 때만 더하도록 조건을 둠(`result: "read"`가 사실이 되게). `note`의 자리표시는 실제 키 `search.row_count`·`company.corp_code`로 적음. 시각은 `_iso()`(`:408-409`)가 이미 `+09:00`을 붙이므로 그대로 옮기라고 적음.
- 8-3a: §4.8 대응표의 `notes`(`document == "main"`) 조건과 세 항목의 `read_scope` 형식을 모두 옮김(초안에는 `notes`의 `document` 조건과 `notes`·`review_or_audit` 범위 문구가 빠져 있었음).
- AC-AIR5-012 "잡지 못하는 것"(로컬 파일 속 지시문)은 8-3b가 5번 규칙을 참조해 다룬다. 5번 규칙 본문은 고치지 않음.
- goose 권한: `claude-settings.json`에 `Read(./**)` 허용이 이미 있어 `runs/<job_id>/dart/` 읽기에 권한 변경이 필요 없음(파일 무변경).

#### AC-AIR5-013 #1~#3 (`aiR5/m4_ac013.log`, `aiR5/m4_diff.log`)

- 착수 전 기준선: 재생성 출력과 커밋된 매니페스트 `diff` 결과 없음(`aiR5/m4_manifest_baseline.json`, `BASELINE_MATCH`).
- #1: `PY -m backend.services.goose_harness > aiR5/m4_ac013_1.json; diff … backend/goose_harness_src/goose-manifest.json` → `exit=0`, `diff_exit=0`, 출력 없음.
- 매니페스트 차이: `"CLAUDE.md": "8e3deb89…98"` → `"a7a9a06e43d2a2be64107a8c934446b8b3c2c787251523bc99a74fa6041554e9"` 한 줄(`git diff --stat`: 매니페스트 `2 +-`, 지침 `9 +++++++++`). 새 해시는 `shasum -a 256 harness-instructions.md`와 같다.
- #2: `shasum -a 256 backend/goose_harness_src/claude-settings.json` → `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`, `git diff --quiet` 종료 0.
- #3: `grep -cF` 13개 문자열 모두 1회 이상 — `runs/<job_id>/dart/index.json` 2, `viewer_url` 1, `direct_read` 1, `read_scope` 2, `서버 사전 수집본으로 열람` 1, `"derived"` 1, `channel: "dart"` 1, `query` 1, `note` 2, `filing_coverage` 1, `review_or_audit` 1, `5번 규칙` 1, `서브에이전트` 2.
- 설치 모의(실제 설치본 무접촉): 임시 폴더에 `_install()` 후 `verify_source` `[]`, `verify_installed` `[]`, 설치된 `CLAUDE.md` sha `a7a9a06e…54e9` (`aiR5/m4_temp_install.log`).

#### 회귀

- `PY -m pytest backend/tests -k goose -q` → `256 passed, 214 deselected` (M3 후와 같음, `aiR5/m4_pytest_goose.log`)
- `PY -m pytest backend/tests/test_goose_harness.py -q` → `32 passed` (`aiR5/m4_pytest_harness.log`). 테스트는 임시 매니페스트를 쓰므로 커밋된 매니페스트 일치는 #1 명령이 맡는다.

#### Gaps

- G-M4-1: AC-AIR5-013 #4(재시작 후 첫 작업이 `integrity`가 아님, `~/.goose-harness/CLAUDE.md` 해시 = `a7a9a06e…54e9`)와 #5(uvicorn 시작 시각 > 지침·작업 서비스·수집 모듈의 마지막 커밋 시각과 `stat -f %m`)는 서버 재시작 뒤 오케스트레이터가 확인한다. 지금 실행 중 서버는 옛 지침·옛 코드다.
- G-M4-2: goose가 규칙 8을 실제로 따르는지는 라이브 AC-AIR5-016(M5)에서만 드러난다.

### M5 — 라이브 실측 (2026-10-21, HEAD 91b904e 코드로 재시작한 서버, 증거 정리는 HEAD 4be2906 시점)

대상 작업: `~/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/`, 020150 롯데에너지머티리얼즈, 2026-10-21 13:10:00 KST 시작. 서버(pid 44028) 재시작 12:33:04 뒤 첫 작업이고 `error`/`integrity`로 끝나지 않았다. AC-016 실행 횟수 1회(상한 2회). 하네스 쪽 파일은 읽기만 했고, 감사 스크립트 출력은 실행 폴더 밖 `aiR5/m5_audit.json`에 썼다. 대조 스크립트는 세션 임시 폴더의 `m5_check.py`(실행 폴더·리포 밖)를 가상환경 python `-I`로 실행했고 출력 원문은 `aiR5/m5_check.log`.

#### AC-AIR5-013 #4·#5 (`aiR5/m5_ac013.log`, 오케스트레이터 측정과 같은 값을 이 실행에서 다시 관측)

```
$ shasum -a 256 ~/.goose-harness/CLAUDE.md
a7a9a06e43d2a2be64107a8c934446b8b3c2c787251523bc99a74fa6041554e9  /Users/byunjungwon/.goose-harness/CLAUDE.md
$ grep '"CLAUDE.md"' backend/goose_harness_src/goose-manifest.json
    "CLAUDE.md": "a7a9a06e43d2a2be64107a8c934446b8b3c2c787251523bc99a74fa6041554e9"
$ ps -o pid=,lstart=,command= -p 44028
44028 Wed Oct 21 12:33:04 2026     /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
$ git log -1 --format=%cd --date=format:%H:%M:%S 91b904e -- <파일>
backend/goose_harness_src/harness-instructions.md commit=12:30:26
backend/services/goose_job_service.py commit=12:24:49
backend/services/goose_dart_prefetch.py commit=12:09:16
```

- #4: 설치본 `CLAUDE.md` 해시 = 매니페스트 값, 재시작 뒤 첫 작업 a5becbb9가 `integrity`가 아님(`job.json` `status: done`, `error_kind: null`) → PASS
- #5: 서버 시작 12:33:04가 세 파일의 마지막 커밋 시각(12:30:26 / 12:24:49 / 12:09:16)보다 늦다 → PASS. 수정 시각도 `harness-instructions.md` 12:29:09, `goose_dart_prefetch.py` 12:07:10(이 실행에서 `stat -f %Sm`로 관측)으로 12:33:04 이전이고, `goose_job_service.py`의 작업 시점 수정 시각은 오케스트레이터 측정 12:24:49다. 지금 `goose_job_service.py`의 수정 시각이 13:25인 것은 이 작업 뒤의 커밋 4be2906(하루 실행 횟수 제한 제거, 이 SPEC 밖) 때문이다. 즉 실행 중인 서버에는 아직 4be2906이 반영되지 않았다.

#### AC-AIR5-016 판정

| # | 기준 | 관측 (원문) | 판정 |
|---|---|---|---|
| 1 | `status: done`, `delivery_status: draft` | `backend/reports/롯데에너지머티리얼즈/goose/2026-10-21/job.json`: `"status": "done"`, `"error_kind": null`, `"delivery_status": "draft"`, `"interrupted": false`, `finished_at 13:18:31+09:00` | PASS |
| 2 | 색인 `complete`, 요청 40 이하, 120초 이하, 재무제표 9·주석 1·요약 1·첨부 1 이상 | `outcome=complete request_count=27 duration_s=26.133 files=15 ok=15`; `ok by (document,section): {('main','financial_statements'): 9, ('main','notes'): 1, ('attachment','auditor_report'): 4, ('main','summary'): 1}` | PASS |
| 3 | 감사 결함 코드와 대상 6종의 교집합 = 공집합 | 직접 실행(아래) `codes= ['AUDIT_INPUT_VERSION', 'AUDIT_MODE', 'AUDIT_PREVIEW_VERSION', 'AUDIT_TIME', 'LATEST_SEARCH_NAVER', 'REVIEW_CALCULATIONS', 'REVIEW_COVERAGE', 'REVIEW_OPINION', 'REVIEW_SOURCE_ACCURACY', 'REVIEW_VISUAL']`, `intersection with target = []`. goose 자체 `delivery-audit.json`도 같은 코드 집합(`same code set (ours vs goose): True`), 교집합 `[]` | PASS |
| 4 | DART `direct_read` 출처마다 (i) `url` ∈ 색인 `ok`의 `viewer_url`, (ii) `read_scope`에 `text_file`, (iii) `limitations`에 `서버 사전 수집본으로 열람` | `dart direct_read sources: 10 of total sources 17`, 10건 모두 `(i)=True (ii)=True (iii)=True`, 추가로 `accessed_at==fetched_at=True` 10/10, `#4 violations = 0` | PASS |
| 5 | `filing_coverage`(§4.8): `read` 항목의 `source_ids`가 허용 구간의 `viewer_url`만 가리킴 | `body: status=read source_ids=['dart_h1_26_fs'] -> 01_financial_statements.txt (main/financial_statements)`, `notes: status=read ['dart_h1_26_notes'] -> 02_notes.txt (main/notes)`, `review_or_audit: status=read ['dart_h1_26_review'] -> 04_auditor_report.txt (attachment/auditor_report)`, `#5 violations = 0` | PASS |

기준선 대비: research.md §2의 이전 실행 2건에서는 대상 6종이 모두 나왔고, 이번 실행에서는 0종이다.

#3 감사 명령(AC-016 문구 그대로, 출력만 실행 폴더 밖):

```
$ cd ~/.goose-harness && /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I .claude/skills/goose/workflows/fact-check/scripts/audit_report.py \
    --input ~/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/draft/report-input.json \
    --output /Users/byunjungwon/Dev/my-project-01/my_chart/.moai/state/verify/70e95898/aiR5/m5_audit.json \
    > …/aiR5/m5_audit_stdout.log 2>&1; echo "audit_exit=$?"
audit_exit=2
```

종료 코드 2는 결함이 남아 `"decision": "revise"`인 경우다(`m5_audit.json`).

부가 관측:

- `company-input.json`과 `draft/report-input.json`은 바이트가 같다(`True`). goose가 입력을 `company-input.json`으로 쓰고 render가 `draft/`로 복사했다.
- 검색 기록(규칙 8-3): `{"channel": "dart", "searched_at": "2026-10-21T13:10:00.391+09:00", "query": "currentPage=1&…&textCrpNm=020150&…", "result": "read", "source_ids": [10개], "note": "서버 사전 수집 검색: 정기보고서 12건, 회사 고유번호 00113997"}` — `searched_at`·`query`가 색인 `search`와 같다.
- `filing_coverage.body.read_scope` = `정기보고서 본문 중 III. 재무에 관한 사항의 연결재무제표(반기보고서 (2026.06))`, `notes.read_scope` = `3. 연결재무제표 주석(반기보고서 (2026.06)) 중 주석 1~8 구간`, `review_or_audit.read_scope` = `반기연결검토보고서 감사인 보고서 본문(첨부 재무제표 사본 제외)` — §4.8 표의 범위 문구 형식과 맞다.

#### 후속 관찰 (이 SPEC의 결함 아님 — 기록만)

- O-M5-1 진행 단계: 화면에 `리포트 입력 작성 — 건너뜀`. 원인은 실행기 `StageMapper`가 `runs/{job_id}/input.json`만 compose로 인식했는데 goose가 `company-input.json`을 썼기 때문. 커밋 4be2906에서 작업 폴더 바로 아래 `*input.json`을 모두 인식하도록 고쳤다(하위 폴더 `draft/report-input.json` 제외, RED→GREEN 테스트 11건). 서버 재시작 전이라 라이브 반영은 미확인.
- O-M5-2 권한 거부: 13:10:40 Bash `cd … && grep` 1건 `permission_denied`(오케스트레이터가 서버 로그에서 관측). 규칙 4가 예상한 거부이고 goose는 계속 진행해 `done`으로 끝났다.
- O-M5-3 `LATEST_SEARCH_NAVER`: 네이버 검색이 막혀 결함이 남음 → 백로그 t19.
- O-M5-4 감수(`AUDIT_*`·`REVIEW_*`)와 화면 확인(`REVIEW_VISUAL`) 미실행으로 `draft` → 백로그 t18(spec.md §5 Out of Scope, 카드 t17 연결). 이 SPEC 이후에도 goose 결과는 `draft`다.

#### Gaps

- G-M5-1: goose가 파일을 열었다고 적은 10건을 실제로 끝까지 읽었는지는 기계 검증 불가(스트림 기록 미보존 — acceptance AC-016 "잡지 못하는 것").
- G-M5-2: 452190 선택 관측(비게이팅)은 하지 않았다.
- G-M5-3: AC-AIR5-003의 진행 패널 화면 배치(`DART 원문 수집` 단계 표시)는 이 실행에서 내가 직접 보지 않았다. O-M5-1 화면 관측은 오케스트레이터 보고에 기댄다.
- G-M5-4: `ruff check` 미실행(G-M2-1과 같은 이유).
- G-M5-5: 4be2906 이후 서버 재시작과 그 뒤 라이브 실행은 아직 없다(오케스트레이터 몫).

## §E.3 Run-phase Audit-Ready Signal

- run_status: audit-ready
- run_complete_at: 2026-10-21 (M5 라이브 실측 기록 시점)
- run_commits: d72a1e1 (M1 픽스처) · 06fb05f (M2 수집 모듈) · 93b5ed5 (M3 작업 서비스 연결) · 91b904e (M4 지침 규칙 8·매니페스트) · M5 증거 기록 커밋(이 progress.md 변경)
- 범위 밖 후속 커밋: 4be2906 `fix(ai-report)` — goose 하루 실행 횟수 제한 제거(사용자 결정 2026-10-21)와 compose 단계 인식 보정(O-M5-1). SPEC-AI-REPORT-004의 쿼터 관련 문서(README·CHANGELOG·004 design/progress)는 sync 단계가 고친다.
- AC 요약 (16개):

| AC | 판정 | 근거 위치 |
|---|---|---|
| 001 실행 위치 | PASS | M3 GREEN·되돌림 (a)~(f) |
| 002 수집 중 취소 | PASS | M2 (b), M3 (a)(c) |
| 003 진행 단계 | PASS (자동 테스트) | M3 (b)(d)·프론트 (a)(c). 화면 배치 눈 확인은 G-M5-3 |
| 004 끄기 스위치 | PASS | M3 (a)~(c) |
| 005~009, 011, 012 | PASS | M2 되돌림 34건 표 |
| 010 실패해도 진행 | PASS | M2 (a)~(c), M3 (e) |
| 013 지침·매니페스트·권한 | PASS | #1~#3 M4, #4·#5 M5 |
| 014 테스트 격리 | PASS | M3 r1~r4·격리 실행 |
| 015 기존 goose 회귀 | PASS | M3·M4 회귀(`256 passed`) |
| 016 라이브 관측 | PASS (1회차) | M5 판정표 #1~#5 |

- gaps: G-M2-1/G-M3-1/G-M5-4(ruff 미설치), G-M3-2(끄기 색인 쓰기 실패 분기 테스트 없음), G-M5-1(실제 열람 범위 기계 검증 불가), G-M5-3(진행 패널 눈 확인), G-M5-5(4be2906 라이브 미반영)
- 참고: M3 §E.2 기록의 테스트 이름 `test_ac007_same_code_twice_returns_existing_job_without_quota`는 4be2906에서 `test_ac007_same_code_twice_returns_existing_job`으로 바뀌었다(기록은 당시 이름 그대로 둔다).

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_complete_at: 2026-10-21
sync_commit_sha: pending-backfill
sync_status: audit-ready
sync_route: A (main 직접 커밋, PR 없음, push 없음)
sync_base_sha: cb6b1ff
frontmatter_status_transitions:
  spec.md: in-progress → completed (updated 2026-10-21 — 이미 같은 날짜라 값 변화 없음)
  plan.md / acceptance.md / research.md / progress.md: frontmatter 없음 — 전이 대상 아님
b12_self_test_a: "grep -c 'SPEC-AI-REPORT-005' CHANGELOG.md → 0 (추가 전)"
b12_self_test_b: "acceptance.md 고유 AC-AIR5-* 16개 = CHANGELOG 'AC-AIR5-001~016 16개'. 원시 grep 26은 본문의 축약 별칭(AC-002·AC-016 등 10개) 포함"
b12_self_test_c: "CHANGELOG 새 항목에 적은 경로 19개 ls 존재 확인 (19/19)"
changelog_entry_position: "[Unreleased] 첫 항목 — ### Added (SPEC-AI-REPORT-005 v0.3.1 …), 이어서 ### Removed (하루 횟수 제한 제거), ### Fixed (입력 작성 단계 인식)"
```

### sync 단계 산출물

- `README.md`: AI 분석 절에 DART 사전 수집 단계(수집 범위, 요청 간격·횟수·시간·크기 상한, 실패해도 진행, 재검사, 끄기 스위치)를 `Goose 동작 방식` 2번으로 넣었다. 하루 한도 행·환경 변수 2개·알려진 한계 2줄을 지우고, API 표의 429 설명을 코드(`backend/routers/ai_report.py`)와 맞췄다(fast: `already_running`·`rate_limit`, deep: `goose_busy`). 알려진 한계에 `draft` 지속(t18·t19)과 수집 범위를 적었다. SPEC 표와 하단 SPEC 목록에 005를 더했다.
- `.env.example`: 끄기 스위치 `AI_REPORT_GOOSE_DART_PREFETCH`를 주석 줄로 더했다(이전에는 없었다).
- `CHANGELOG.md`: 위 `changelog_entry_position`의 세 항목.

### MX 태그 점검 (보고만, 코드 수정 없음)

- `backend/services/goose_dart_prefetch.py`: `DartPrefetcher` `@MX:ANCHOR`(+REASON·SPEC), `_Session` `@MX:WARN`(+REASON), 예산 상수 `@MX:NOTE` 있음.
- `backend/services/goose_job_service.py`: `_prefetch` `@MX:ANCHOR`(+REASON·SPEC) 있음. `start`·`_run` 주변 기존 태그 유지.
- `backend/tests/conftest.py`: 소켓 바꿔치기 `@MX:WARN`(+REASON) 있음.
- `backend/services/ai_report_service.py`: `check_rate_limit` `@MX:ANCHOR`(라우터 + 테스트), `@MX:NOTE`가 "분당 버스트 방지만 남긴다"로 현재 동작과 맞다.
- `backend/services/goose_runner.py` `StageMapper`: compose 인식 주석이 현재 동작과 맞다. 호출자는 실행기 내부뿐이라 ANCHOR 대상 아님.
- 누락된 `@MX:ANCHOR` 없음.

### sync 단계에서 하지 않은 것

- `plan.md` 머리말 "상태: draft · 버전 0.3.1"은 본문이라 고치지 않았다.
- SPEC-AI-REPORT-004 문서(design·progress의 하루 한도 서술)는 완료된 SPEC의 역사 기록이라 고치지 않았다. §E.3이 "004 design/progress는 sync 단계가 고친다"고 적었지만, 이번 위임 범위가 완료 SPEC 본문 수정을 금지해 그대로 두었다.
- `.moai/project/product.md:48`·`.moai/project/tech.md:101`의 옛 Deep 하루 한도(`AI_REPORT_DEEP_DAILY_QUOTA`) 서술은 SPEC-AI-REPORT-004 이전부터 낡은 내용이라 이번 범위 밖으로 남겼다.
- 4be2906·cb6b1ff 반영 서버 재시작과 라이브 확인(G-M5-5)은 하지 않았다.
