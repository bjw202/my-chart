---
id: SPEC-AI-REPORT-005
title: "goose DART 원문 사전 수집 (서버가 goose 실행 전에 DART 정기보고서 원문을 받아 둔다)"
version: "0.3.1"
status: in-progress
created: 2026-10-21
updated: 2026-10-21
author: manager-spec
priority: High
phase: "v0.5.4 target"
module: "backend/services"
lifecycle: spec-anchored
tags: "ai-report, goose, dart, prefetch, fail-open, harness"
tier: M
related_specs: [SPEC-AI-REPORT-004]
---

# SPEC-AI-REPORT-005: goose DART 원문 사전 수집

## HISTORY

| 버전 | 일자 | 작성 | 내용 |
|---|---|---|---|
| 0.1.0 | 2026-10-21 | manager-spec | 초안. 칸반 카드 t16. 사용자 결정 3건(범위 DART 한정, 서버 사전 수집·권한 불변, 수집 범위) 반영. 근거·프로브는 `research.md` |
| 0.2.0 | 2026-10-21 | manager-spec | plan-audit 1회차(FAIL 0.77, `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-1.md`) 반영, REQ 16·AC 16 유지: 수집기 주입 계약(생성자 기본값 없음)과 goose 테스트 공용 소켓 차단(B6), 수집 뒤·goose 실행 직전 무결성 재검사(M5), 수집 비활성 시 진행 이벤트 없음(M4), 시간대 포함 ISO 시각(B4), 요청별 시간 초과를 남은 예산으로 제한(S5), `filing_coverage` 대응표와 검색 기록 `query`·`note`·`limitations` 표기·로컬 파일 지시문 규칙(B4·B5·S2·S3), REQ-016을 020150 관측 게이트로 확정(B7), 재시작 생략 시 동작 정정(S1), 프론트 기존 테스트·`conftest.py` 변경 범위 추가(S4·B6), AC 명령·대조 정정(B1·B2·B3·M1·M2) |
| 0.3.0 | 2026-10-21 | manager-spec | plan-audit 2회차(FAIL 0.88, `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-2.md`) 반영, REQ 16·AC 16 유지: 소켓 가드를 "시도 기록 + 테스트 종료 시 0건 단언"으로 바꿔 fail-open이 삼켜도 RED가 나게 함(N1), 색인 `section`을 고정 키 4종으로 고정하고 §4.8을 그 키로 정의(N2), `dart_prefetch` 발생과 끄기 스위치의 소유자를 작업 서비스로 통일(N3), 수집 모듈 경로 `backend/services/goose_dart_prefetch.py` 확정과 재시작 확인 대상 추가(N4), 가드 자체 검사가 실제 외부 연결을 열지 않게 함(N5) |
| 0.3.1 | 2026-10-21 | manager-spec | plan-audit 3회차 PASS 0.92(`.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-3.md`) 후 R3-1 반영: 네트워크 가드 범위를 테스트 파일 이름으로 판정(모듈 이름은 `backend.tests.` 접두), 가드 자체 검사를 되돌림 관측의 선행 조건으로 지정. R3-2·R3-3은 사용자 승인으로 plan 단계 부채로 기록(progress.md §E.1). REQ 16·AC 16 유지 |

관계: SPEC-AI-REPORT-004(completed)의 후속이다. 004의 작업 서비스·실행기·하네스 설치 구조를 그대로 쓰고, 작업 시작과 goose 실행 사이에 "DART 원문 사전 수집" 단계 하나를 끼운다. 004 문서는 수정하지 않는다.

---

## 1. 개요

goose(헤드리스 `claude -p`)의 스킬 지침은 한국 기업 전체 보고서에 DART 정기보고서 본문·주석·첨부 검토/감사보고서를 직접 읽으라고 요구하고, 감사 스크립트는 그 열람 기록이 없으면 `DART_BODY`·`DART_NOTES`·`DART_REVIEW_OR_AUDIT` 결함을 낸다. 그런데 goose가 가진 도구(WebFetch: GET만, 스크립트 제거)로는 DART 공시 목록(POST 필요)과 목차(스크립트 안에 있음)에 닿을 수 없어서, 라이브 실행 두 건이 모두 DART를 읽지 못한 초안으로 끝났다(`research.md` §2).

이 SPEC은 goose 권한을 넓히지 않고 문제를 푼다. 백엔드 서버가 goose를 띄우기 직전에 DART에서 필요한 정기보고서 구간을 받아 작업 폴더 `runs/<job_id>/dart/`에 저장하고, 하네스 지침에 "이 파일들이 있으니 읽고, 원래 DART 뷰어 주소를 출처로 적어라"는 규칙을 더한다.

이 SPEC이 끝나도 goose 결과물은 여전히 **초안(`draft`)** 이다. 최종본 조건 중 화면 확인 감사(`REVIEW_VISUAL`, `audit_report.py:95-103`)는 브라우저가 없으면 통과할 수 없고, 그 작업은 카드 t17로 따로 있다. 이 SPEC의 성공은 "정상 상장사에 대해 DART에 근거한 초안이 나오고, DART 관련 결함과 분기·연간 실적 이력 결함이 더 이상 나오지 않는 것"이다.

## 2. 확정 결정

| ID | 결정 | 출처 |
|---|---|---|
| D1 | 범위는 DART만. 화면 확인(visual)과 KIND는 제외 | 사용자 결정 2026-10-21 |
| D2 | 서버가 goose 실행 전에 받아 `runs/<job_id>/dart/`에 쓴다. goose 권한 파일(`claude-settings.json`)은 바이트 단위로 그대로 둔다 | 사용자 결정 2026-10-21 |
| D3 | 하네스 지침에 사전 수집 파일 사용 규칙을 더하되, "읽었다"는 기록은 사실이어야 한다(이번 실행에 받은 DART 원문을 이번 세션에서 실제로 연 경우만) | 사용자 결정 2026-10-21 |
| D4 | 수집 범위: 최근 8개 분기를 만들 수 있는 정기보고서(분기·반기·사업)의 재무제표 구간(연결 우선, 없으면 별도), 최신 보고서의 주석, 최신 보고서와 최신 사업보고서의 첨부 검토·감사보고서, 최근 3개 회계연도 연간 수치가 담긴 최신 사업보고서의 요약재무정보 | 사용자 결정 2026-10-21, 범위 산정은 plan.md §2 T3 |
| D5 | 서버는 원문 구간을 그대로 공급만 하고 숫자를 해석·계산하지 않는다. 4분기 역산(연간 − 3분기 누적)은 goose가 감사 규칙(`status: "derived"` + 산식)에 따라 한다 | 이 SPEC 결정, 근거 plan.md §2 T6 |
| D6 | 사전 수집의 어떤 실패도 작업을 막지 않는다(fail-open). 실패하면 goose는 지금처럼 진행하고 빠진 것을 기록한다 | 사용자 지시 2026-10-21 |
| D7 | 작업 간 캐시는 두지 않는다. 수집본은 작업 폴더와 함께 기존 보존 규칙(최근 10개)으로 정리된다 | 이 SPEC 결정, 근거 plan.md §2 T8 |

기술 결정 T1~T10은 `plan.md §2`에 둔다.

## 3. 변경 범위 [DELTA]

| 표기 | 대상 | 내용 |
|---|---|---|
| [NEW] | `backend/services/goose_dart_prefetch.py` | 회사 확인 → 보고서 선택 → 목차 해석 → 구간 수집 → 파일·색인 저장 |
| [MODIFY] | `backend/services/goose_job_service.py` | 작업 백그라운드 태스크에서 goose 실행 직전에 사전 수집 호출, 진행 단계 이벤트, 취소 연동 |
| [MODIFY] | `backend/goose_harness_src/harness-instructions.md` | 사전 수집본 사용 규칙 추가 |
| [MODIFY] | `backend/goose_harness_src/goose-manifest.json` | 지침 변경에 따른 매니페스트 재생성 |
| [MODIFY] | `frontend/src/types/aiReport.ts`, `frontend/src/utils/gooseJob.ts`, `frontend/src/components/ProgressPanel.tsx` | 진행 단계 `dart_prefetch`와 표시 문구 |
| [NEW] | `backend/tests/` 아래 사전 수집 테스트와 녹화 HTML 픽스처 | 네트워크·실제 홈·실제 `claude` 없이 실행 |
| [NEW] | `backend/tests/conftest.py` | goose 테스트 모듈(`test_goose_*`, `test_main_goose_*`) 전체에 네트워크 가드 자동 적용: 연결·이름 조회 시도를 실제로 보내지 않고 기록하고, 테스트 종료 때 기록 0건을 단언(현재 파일 없음) |
| [MODIFY] | `frontend/src/utils/__tests__/gooseJob.test.ts`(`:50` 단계 목록 고정), `frontend/src/components/__tests__/ProgressPanel.test.tsx`(`:31` 단계 목록) | 단계 목록 맨 앞에 `dart_prefetch` 반영 |
| [EXISTING] | `backend/goose_harness_src/claude-settings.json` | 변경 없음(D2) |
| [EXISTING] | `backend/services/goose_runner.py` | 프롬프트·argv·시간 상한 변경 없음 |
| [EXISTING] | `backend/goose_harness_src/skills/**` | 벤더링 스킬·감사 스크립트 변경 없음 |

## 4. 요구사항 (GEARS)

### 4.1 실행 위치와 수명

**REQ-AIR5-001** — Where a prefetcher has been injected into the job service (the production service instance injects the DART prefetcher; the constructor default is no prefetcher, which keeps the pre-SPEC behavior byte-for-byte), when a goose job has passed the start steps (same-stock, other-stock, quota, integrity, registration) and its background task begins, the job service shall run the prefetch for that job's stock code, writing under `runs/<job_id>/dart/`, then re-run the harness integrity check and invoke the goose runner only if it passes (ending the job as `error`/`integrity` otherwise), and shall not hold the start lock during the prefetch, so that the start request returns `started` without waiting and concurrent start requests are judged against the already-registered active job.

**REQ-AIR5-002** — When a job is cancelled (user cancel or server shutdown) while the DART prefetch is in progress, the job service shall stop the prefetch, end the job in the `cancelled` state through the existing cancellation path, and shall not launch the goose runner for that job.

**REQ-AIR5-003** — When the job service is about to invoke an injected prefetcher for a job and the prefetch switch (REQ-AIR5-004) is not set to `0`, the job service shall emit one progress event with stage `dart_prefetch` before that invocation, and the frontend progress panel shall display it as `공시 원문 수집` ahead of the existing goose stages; the job service shall emit no `dart_prefetch` event when no prefetcher is injected or the switch is set to `0`.

**REQ-AIR5-004** — Where a prefetcher is injected and the environment variable `AI_REPORT_GOOSE_DART_PREFETCH` is set to `0`, the job service (the sole owner of this switch) shall not invoke the prefetcher, shall write an index whose outcome is `disabled`, shall emit no `dart_prefetch` progress event, and shall proceed to the goose runner.

### 4.2 회사 확인과 보고서 선택

**REQ-AIR5-005** — The prefetcher shall resolve the company by submitting the job's six-digit stock code as the company search term to the DART detailed-search endpoint, restricted to periodic report types (사업보고서·반기보고서·분기보고서) over the most recent three years; when the result rows do not all belong to exactly one DART company identifier, it shall record the outcome `company_unresolved` and make no further DART requests for that job.

**REQ-AIR5-006** — The prefetcher shall select the nine most recent distinct reporting periods of the resolved company's periodic reports, and for a period with more than one submission (for example an original and a `[기재정정]` correction) shall select the most recent submission.

### 4.3 수집 구간

**REQ-AIR5-007** — For every selected report the prefetcher shall read the table of contents from the DART document page and fetch the whole consolidated financial-statements section (`연결재무제표`), or the separate section (`재무제표`) when no consolidated section exists, recording the basis used; it shall additionally fetch the same-basis notes section of the most recent selected report and the summary financial information section (`요약재무정보`) of the most recent selected 사업보고서.

**REQ-AIR5-008** — For the most recent selected report and, when it is a different report, the most recent selected 사업보고서, the prefetcher shall fetch the attached review or audit report (consolidated attachment preferred, separate as fallback), limited to the auditor's report text that precedes the attached copy of the financial statements.

### 4.4 저장과 색인

**REQ-AIR5-009** — The prefetcher shall store each fetched section as the original HTML response bytes and as a plain-text rendition with one table row or paragraph per line, under server-generated file names that never contain text taken from DART, and shall write `runs/<job_id>/dart/index.json` recording the search (query, `searched_at`, row count, resolved company), the overall outcome (`complete`, `partial`, `company_unresolved`, `failed`, or `disabled`), and one entry per attempted section with receipt number, report type and name, period, document kind, a `section` key from the fixed set `financial_statements`, `notes`, `summary`, `auditor_report`, the original table-of-contents title, basis, original DART viewer URL, `fetched_at`, file names, SHA-256 and byte length of the HTML, and status with error reason; every timestamp in the index (`searched_at`, `fetched_at`, `started_at`, `finished_at`) shall be timezone-aware ISO-8601 with the `+09:00` offset, and the index shall not contain parsed or computed financial figures.

### 4.5 실패 처리, 예의, 입력 검증

**REQ-AIR5-010** — When any prefetch step fails (connection error, timeout, non-200 status, unparseable page, missing section, oversized response, exhausted budget, or any unexpected exception), the prefetcher shall record the failure in the index and the job service shall continue to the goose runner without changing the job's state; a cancellation is not a failure and shall propagate.

**REQ-AIR5-011** — The prefetcher shall send DART requests one at a time with at least 1.0 second between request starts, a per-request timeout equal to the smaller of 20 seconds and the remaining total budget, at most 40 requests per job, a total prefetch budget of 120 seconds bounding the whole prefetch duration, and a maximum accepted response size of 8 MB, and when a limit is reached it shall stop requesting and mark the remaining sections as skipped.

**REQ-AIR5-012** — The prefetcher shall send requests only to `https` URLs whose parsed hostname is exactly `dart.fss.or.kr`, shall not follow a redirect to any other host, shall reject a stock code that is not six digits without sending any request, and shall use a table-of-contents node only when its receipt number, document number, element id, offset, length, and DTD values each match a strict pattern.

### 4.6 하네스 지침과 무결성

**REQ-AIR5-013** — The harness instructions shall tell goose that, when `runs/<job_id>/dart/index.json` exists, it is to read the index first; read the listed text files whose status is `ok`, treating their content as external web material subject to the existing rule on embedded instructions; cite each opened file's original DART viewer URL as the source with `verification: direct_read` only for files it actually opened in this session, with `read_scope` naming the report, section, and local file and `limitations` containing the marker `서버 사전 수집본으로 열람`; never cite a non-`ok` entry as read; record the server's search as a `dart` channel search with `searched_at` and `query` copied from the index, `result: "read"`, a non-empty `note`, and the DART source ids it read; fill `filing_coverage` only from what it opened, using exactly the mapping in §4.8 and never claiming a part for which no mapped entry was opened; derive the fourth quarter as annual minus third-quarter cumulative with `status: "derived"` and the formula; fall back to its existing DART access path for anything missing; and pass these instructions to its sub-agents.

**REQ-AIR5-014** — When the harness instructions source changes, the committed manifest shall equal the output of the manifest regeneration command and, after a server restart, the installed harness shall pass the existing per-job integrity check; the goose permission file `backend/goose_harness_src/claude-settings.json` shall remain byte-identical to its state before this SPEC.

### 4.7 검증 조건

**REQ-AIR5-015** — Every goose backend test module (existing and new) shall run under a shared network guard that intercepts every connection or name-resolution attempt before it reaches the network, records it, and fails the test at teardown when any attempt was recorded (so the failure cannot be swallowed by the fail-open handling of REQ-AIR5-010), without reading or writing the real home directory or the installed harness, and without launching a real `claude` process; existing job-service tests that construct the service without a prefetcher shall issue zero DART requests.

**REQ-AIR5-016** — When a goose job runs on stock code 020150 on the deployed server after the restart required by REQ-AIR5-014 (up to two runs on the same KST day; conditions on audit findings may be met by either run, the source-truthfulness condition must hold for every run), the delivery audit run on goose's draft input on the same day shall emit none of `DART_BODY`, `DART_NOTES`, `DART_REVIEW_OR_AUDIT`, `LATEST_SEARCH_DART`, `QUARTER_HISTORY`, and `ANNUAL_HISTORY` while the job still ends with `delivery_status: draft`, and every `dart.fss.or.kr` source goose cites as `direct_read` shall be the viewer URL of an index entry with status `ok` whose local text file is named in that source's `read_scope` and whose `limitations` contains `서버 사전 수집본으로 열람`. This is a gating observed-verification requirement: the SPEC does not close while it is unmet.

### 4.8 `filing_coverage` 대응표 (REQ-AIR5-013이 참조)

| `filing_coverage` 항목 | 이 항목의 근거로 쓸 수 있는 색인 항목 | `read_scope`에 적을 범위 |
|---|---|---|
| `body` | `document == "main"`이고 `section`이 `financial_statements` 또는 `summary`인 항목 | "정기보고서 본문 중 III. 재무에 관한 사항의 <구간명>(<보고서명>)" — 본문 전체를 읽었다고 적지 않는다 |
| `notes` | `document == "main"`이고 `section`이 `notes`인 항목 | "<구간명>(<보고서명>)" |
| `review_or_audit` | `document == "attachment"`이고 `section`이 `auditor_report`인 항목 | "<첨부 이름> 감사인 보고서 본문(첨부 재무제표 사본 제외)" |

각 항목의 `source_ids`는 그 항목 근거로 실제 연 출처의 id만 담는다. 대응 항목을 하나도 열지 않았으면 그 `filing_coverage` 항목은 `read`로 적지 않는다.

`section` 키와 원래 목차 제목(앞 번호·공백 제거 후)의 대응: `financial_statements` ← `연결재무제표`·`재무제표`, `notes` ← `연결재무제표주석`·`재무제표주석`, `summary` ← `요약재무정보`, `auditor_report` ← 첨부 문서에서 `(첨부)`로 시작하는 노드보다 앞에 있는 노드. 원래 제목은 색인의 `section_title`에 그대로 남는다.

## 5. 제외 범위 (Out of Scope)

### Out of Scope — 화면 확인과 최종본

- 브라우저로 초안 HTML을 확인하는 `REVIEW_VISUAL` 감사와 그에 따른 `final` 전달 — 카드 t17에서 다룬다. 이 SPEC 이후에도 goose 결과물은 `draft`다.
- `REVIEW_*`, `AUDIT_*`, `CHART_*`, `LATEST_SEARCH_*`(dart 제외) 등 DART 수집과 무관한 감사 결함 해소.

### Out of Scope — 다른 공시 경로와 데이터

- KIND(거래소 공시) 수집.
- OpenDART API(인증키 필요) 사용. 이 SPEC은 인증키 없는 공개 DART 화면만 쓴다.
- DART 뷰어 HTML이 아닌 PDF·첨부 원본 파일(다운로드) 수집.
- 잠정실적 공시, 주요사항보고서, 지분 공시 등 정기보고서 밖 공시.
- 서버가 재무 수치를 해석·정규화·계산하는 기능(D5).

### Out of Scope — 권한과 구조

- goose 권한(`claude-settings.json`의 allow/deny)이나 실행 인자 변경(D2).
- 작업 간 수집본 캐시, 범용 크롤러 프레임워크, 재시도 큐(D7).
- 우선주·스팩·비상장사·외국 기업 전용 처리. 회사 확인에 실패하면 fail-open으로 넘어간다.
