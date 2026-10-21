---
id: SPEC-AI-REPORT-006
title: "goose 후처리 감수 (서버가 초안 화면을 찍고, 별도 감수 세션이 audit-review.json을 쓴다)"
version: "0.1.0"
status: draft
created: 2026-10-21
updated: 2026-10-21
author: manager-spec
priority: High
phase: "v0.6.0 target"
module: "backend/services"
lifecycle: spec-anchored
tags: "ai-report, goose, review-pass, screenshot, headless-browser, audit-review, delivery-gate, harness"
tier: L
related_specs: [SPEC-AI-REPORT-004, SPEC-AI-REPORT-005]
---

# SPEC-AI-REPORT-006: goose 후처리 감수

## HISTORY

| 버전 | 일자 | 작성 | 내용 |
|---|---|---|---|
| 0.1.0 | 2026-10-21 | manager-spec | 초안. 칸반 카드 t18. 결함 두 건(감수 단계 부재, 화면 확인 불가)을 하나의 후처리 단계로 해결. 근거·프로브는 `research.md`, 구조는 `design.md`, 계획은 `plan.md` |

관계: SPEC-AI-REPORT-004(goose 하네스)·005(DART 사전 수집)의 후속이다. 두 SPEC의 작업 서비스·실행기·하네스 설치 구조를 그대로 쓰고, goose 1차 세션이 끝난 뒤에 "화면 캡처 → 별도 감수 세션" 두 단계를 붙인다. 004·005 문서는 수정하지 않는다.

---

## 1. 개요

goose가 만든 보고서는 "최종본"이 되려면 감사 스크립트(`audit_report.py`)의 감수 기록 요건을 모두 채워야 한다. 지금은 두 가지가 막고 있다.

1. **감수 단계가 없다.** goose는 초안을 쓰고 감사 스크립트를 한 번 돌린 뒤 끝낸다. 감수 기록 `audit-review.json`이 만들어지지 않으므로 `AUDIT_INPUT_VERSION`, `AUDIT_PREVIEW_VERSION`, `AUDIT_TIME`, `AUDIT_MODE`, `REVIEW_SOURCE_ACCURACY`, `REVIEW_CALCULATIONS`, `REVIEW_COVERAGE`, `REVIEW_OPINION` 결함이 항상 나온다. 2026-10-21 020150 라이브 실행(작업 `a5becbb9…`)의 `delivery-audit.json`에서 이 8개가 모두 관측됐고, 합성 기록으로 감사기를 돌려 보면 형식을 갖춘 감수 기록 하나로 8개가 모두 사라진다(`research.md` P2·P3).
2. **화면을 볼 방법이 없다.** 감사기는 `visual` 검사 통과 기록을 요구하지만(`audit_report.py:95-103`) goose가 쓸 수 있는 브라우저가 없고, 하네스 규칙 7은 일어나지 않은 통과를 기록하지 못하게 막는다(`research.md` P1·P5). 그래서 `REVIEW_VISUAL`은 영원히 남는다.

이 SPEC은 goose 권한을 넓히지 않고 두 결함을 함께 푼다. goose 1차 세션은 지금처럼 초안까지만 만든다. 그 뒤 **서버가** 초안 HTML을 헤드리스 브라우저로 열어 데스크톱·모바일 화면을 `runs/<job_id>/screens/`에 저장하고, **별도 `claude -p` 세션(감수 세션)** 이 초안·원장·화면 이미지를 읽고 `audit-review.json`을 쓴 뒤 감사 스크립트를 다시 돌린다. 감수 세션은 새 대화라서 초안을 쓴 대화와 섞이지 않으므로 감사기의 `mode=separate_review_pass`(작성 후 별도 감수 단계)에 해당한다.

**불변식(규칙 7 보존).** 화면 확인 "통과"는 일어난 일일 때만 최종본을 열 수 있다. 서버는 감수 세션이 끝난 뒤, 세션의 출력 스트림에서 화면 이미지를 실제로 열었다는 기록과 파일 해시 정합성을 직접 확인해 **영수증(`review/receipt.json`)** 을 쓴다. 영수증이 화면 확인을 인정하지 않으면 감수 세션이 `final/`을 만들었더라도 전달 상태는 `draft`다. 감수 기록의 선언만으로는 최종본이 되지 않는다.

이 SPEC이 끝나도 최종본이 항상 나오는 것은 아니다. 감사기의 다른 결함(예: 020150 라이브 실행에서 관측된 `LATEST_SEARCH_NAVER`, 네이버 금융 접근 차단)은 조사 품질 문제라 범위 밖이다. 이 SPEC의 성공은 "감수 기록 관련 결함 8종이 사라지고, 화면 확인이 서버가 확인한 사실에만 근거하는 것"이다.

## 2. 확정 결정

| ID | 결정 | 출처 |
|---|---|---|
| D1 | 두 결함을 하나의 후처리로 푼다. 1차 goose 세션은 초안까지(변경 없음), 후처리 = 서버 화면 캡처 + 별도 감수 세션 | 카드 t18 방향, 근거 plan.md T1 |
| D2 | 감수 방식은 `separate_review_pass`(별도 `claude -p` 세션)다. `independent_agent`(독립 에이전트)는 주장하지 않는다 | 이 SPEC 결정, 근거 plan.md T2 |
| D3 | goose 권한 파일(`claude-settings.json`)과 벤더링 스킬(`skills/**`)·감사 스크립트는 바이트 단위로 그대로 둔다. 바뀌는 하네스 파일은 `harness-instructions.md`와 매니페스트뿐이다 | 이 SPEC 결정, 근거 plan.md T3 |
| D4 | 감수 세션은 읽기 전용이다. 초안·입력 JSON을 고치지 않는다. 지적 사항은 `issues`에 `open`으로 남기고 수정·재감수 반복은 범위 밖이다 | 이 SPEC 결정, 근거 plan.md T4 |
| D5 | 화면 확인 통과의 인정 근거는 서버가 직접 확인한 사실(영수증)뿐이다. 감수 기록의 선언은 근거가 아니다 | 카드 t18 규칙 7 보존 요구, 근거 plan.md T6 |
| D6 | 후처리의 어떤 실패도 작업을 `error`로 만들지 않는다(fail-open). 결과는 1차 세션이 만든 초안으로 남는다 | 005 D6와 같은 원칙, 근거 plan.md T7 |
| D7 | 화면 캡처는 서버 호스트의 헤드리스 Chrome 계열 브라우저를 DevTools 프로토콜로 구동한다. 스크립트 비활성·외부 네트워크 차단. 새 직접 의존성은 `websockets`뿐(이미 설치돼 있음, P11) | 이 SPEC 결정, 근거 plan.md T8 |
| D8 | 끄기 스위치 `AI_REPORT_GOOSE_REVIEW=0`. 끄면 후처리 전체를 건너뛰고 전달 상태는 항상 `draft`다(현재 동작과 같다) | 005 D6 선례, 근거 plan.md T7 |

기술 결정 T1~T12는 `plan.md §2`에 둔다.

## 3. 변경 범위 [DELTA]

| 표기 | 대상 | 내용 |
|---|---|---|
| [NEW] | `backend/services/goose_screenshot.py` | 브라우저 탐색·실행, 화면 캡처(타일), `screens/index.json` 저장 |
| [NEW] | `backend/services/goose_review.py` | 감수 컨텍스트(`review/context.json`)·영수증(`review/receipt.json`) 작성, 열람 기록 집계, 화면 확인 인정 판정 |
| [MODIFY] | `backend/services/goose_runner.py` | 감수 세션 실행(`run_review`), 감수 프롬프트, Read 기록 수집, `select_report`에 영수증 확인 추가 |
| [MODIFY] | `backend/services/goose_job_service.py` | 1차 세션 뒤 후처리(재검사 → 캡처 → 감수 → 영수증), 진행 이벤트, 끄기 스위치, 취소·fail-open |
| [MODIFY] | `backend/goose_harness_src/harness-instructions.md` | 규칙 7 개정, 감수 세션 규칙 9 추가 |
| [MODIFY] | `backend/goose_harness_src/goose-manifest.json` | 지침 변경에 따른 매니페스트 재생성 |
| [MODIFY] | `pyproject.toml` | `websockets` 직접 의존성 선언 |
| [MODIFY] | `frontend/src/types/aiReport.ts`, `frontend/src/utils/gooseJob.ts`, `frontend/src/components/ProgressPanel.tsx` | 진행 단계 `screenshot`·`review` 추가와 `render_final` 위치 조정, 표시 문구 |
| [MODIFY] | `frontend/src/utils/__tests__/gooseJob.test.ts`, `frontend/src/components/__tests__/ProgressPanel.test.tsx` | 단계 목록 고정 단언 갱신 |
| [NEW] | `backend/tests/test_goose_screenshot.py`, `backend/tests/test_goose_review.py` | 가짜 브라우저·가짜 claude로 도는 테스트 |
| [MODIFY] | `backend/tests/test_goose_job_service.py`, `test_goose_runner.py`, `test_goose_harness.py` | 후처리 순서·영수증 확인·지침·매니페스트 테스트, 영수증 없는 `final` 선택 테스트 갱신 |
| [MODIFY] | `README.md`, `.env.example` | 후처리 단계, 환경 변수 3개, 브라우저 요건 |
| [EXISTING] | `backend/goose_harness_src/claude-settings.json` | 변경 없음(D3) |
| [EXISTING] | `backend/goose_harness_src/skills/**` | 변경 없음(D3). `audit_report.py`·`delivery-audit.md` 포함 |
| [EXISTING] | `backend/services/goose_storage.py` | 보관 허용 파일 목록 변경 없음. 화면·영수증은 보관하지 않는다 |

## 4. 요구사항 (GEARS)

### 4.1 후처리 위치와 수명

**REQ-AIR6-001** — Where a screenshotter and a reviewer have been injected into the job service (the production service instance injects both; the constructor default is neither, which keeps the pre-SPEC behavior byte-for-byte) and the review switch (REQ-AIR6-004) is not `0`, when the goose runner returns `done` and `runs/<job_id>/draft/report.html` is a regular file, the job service shall, inside the job's background task, without holding the start lock, and while the job remains the registered active job, re-run the harness integrity check, then run the screen capture (REQ-AIR6-006), then the review session (REQ-AIR6-011), then write the receipt (REQ-AIR6-015), in that order, and only then end the job; when the integrity re-check fails it shall launch neither the capture nor the review session, shall write a receipt whose outcome is `integrity_failed`, and shall end the job in the state the runner result dictates.

**REQ-AIR6-002** — When a job is cancelled (user cancel or server shutdown) while the screen capture or the review session is running, the job service shall stop it, terminate the browser or review process group so that no process of that group survives, end the job `cancelled` through the existing cancellation path, and shall not select a `final` report for that job.

**REQ-AIR6-003** — When the job service is about to start the screen capture it shall emit exactly one progress event with stage `screenshot`, and when it is about to launch the review session exactly one with stage `review`, each before the step begins; when the review session's output shows `render_report.py` invoked with `--final` it shall emit a `render_final` progress event; it shall emit none of these when no screenshotter or reviewer is injected or the switch is `0`. The frontend shall list the stages in the order `dart_prefetch, goose_start, plan, research_tick, fetch_start, fetch_done, compose, render_draft, audit, session_end, screenshot, review, render_final` and display `screenshot` as `화면 캡처` and `review` as `감수`.

**REQ-AIR6-004** — Where the environment variable `AI_REPORT_GOOSE_REVIEW` is set to `0`, the job service (the sole owner of this switch) shall invoke neither the screenshotter nor the reviewer, shall emit none of the REQ-AIR6-003 events, shall write a receipt whose outcome is `disabled`, and shall end the job exactly as it did before this SPEC, with delivery status `draft`.

**REQ-AIR6-005** — When any post-processing step fails (browser missing or failing to launch, capture timeout or protocol error, review process failing to start, exiting non-zero, timing out, or leaving no `audit-review.json`, or any unexpected exception), the job service shall record the failure in the receipt, shall still run the review session when only the capture failed, and shall end the job `done` with delivery status `draft` instead of `error`; a cancellation is not a failure and shall propagate.

### 4.2 화면 캡처

**REQ-AIR6-006** — The screenshotter shall open only the server-resolved file `runs/<job_id>/draft/report.html` (a regular file, not a symlink, whose resolved path lies inside the job directory) as a `file://` URL, shall render it at a desktop viewport of 1280 px width and a mobile viewport of 390 px width with mobile emulation, and for each viewport shall save the full page as PNG tiles of at most 1568 px height under `runs/<job_id>/screens/` using server-generated names `desktop-NN.png` and `mobile-NN.png` (two-digit sequence from 01) that never contain text taken from the report.

**REQ-AIR6-007** — The screenshotter shall write `runs/<job_id>/screens/index.json` recording the overall outcome (`complete`, `partial`, `unavailable`, `failed`, or `disabled`), the browser name and version, the SHA-256 of the exact `draft/report.html` bytes that were rendered, timezone-aware ISO-8601 `+09:00` `started_at`/`finished_at`, and per viewport its status (`ok`, `error`, `too_tall`, or `skipped`), error reason, page metrics (`scroll_width`, `client_width`, `scroll_height`, `horizontal_overflow`), and per tile the file name, vertical offset, width, height, byte length, and SHA-256; the outcome is `complete` only when both viewports are `ok`.

**REQ-AIR6-008** — The screenshotter shall bound the whole capture, including browser start-up, to a wall-clock budget of 60 seconds, shall produce at most 24 tiles per viewport (a page that would need more is recorded `too_tall` with no tiles for that viewport), shall reject any tile larger than 8 MiB, shall terminate the browser process group on completion, failure, timeout, and cancellation, and shall delete its temporary browser profile directory in every one of those cases.

**REQ-AIR6-009** — The screenshotter shall launch the browser with an argument list built only from fixed strings, the server-validated file URL, a loopback debugging port, and a server-created temporary profile directory (never text taken from the report, the stock name, or any DART or web material), shall disable script execution in the page, and shall block every network request the page makes, so that rendering an untrusted report cannot run page code or contact an external host.

**REQ-AIR6-010** — The screenshotter shall locate the browser from the environment variable `AI_REPORT_GOOSE_BROWSER` when it is set (and record `unavailable` without falling back when that path is not an executable file), otherwise from a fixed list of executable names on `PATH`, otherwise from a fixed list of known install locations; when none is found it shall record outcome `unavailable` with the reason and make no browser launch.

### 4.3 감수 세션

**REQ-AIR6-011** — The review launcher shall start the review session as a new `claude -p` process built with the same security argument set as the goose session (`--setting-sources project`, the installed harness `--settings`, `--strict-mcp-config`, `--permission-mode dontAsk`, `--no-session-persistence`, never a permission-bypass flag), in the harness directory, with the same environment allow-list and process-group handling, with a prompt that names only the job directory, the six-digit stock code, and the review-session role (never the stock name), and with a time limit taken from `AI_REPORT_GOOSE_REVIEW_TIMEOUT` seconds (default 900).

**REQ-AIR6-012** — Before launching the review session the service shall write `runs/<job_id>/review/context.json` recording the current time, the path and SHA-256 of `runs/<job_id>/draft/report-input.json`, the path and SHA-256 of `runs/<job_id>/draft/report.html`, the screens index path with its outcome, the audit-review and audit-output paths, and the exact values the review record must copy (`input_sha256`, `preview_sha256`, `reviewed_at`, `mode`), so that the review session never has to compute a hash.

**REQ-AIR6-013** — The harness instructions shall (a) restrict the goose first session to producing the draft and running the audit once without a review record, forbidding it from writing `audit-review.json` or running `render_report.py --final`; (b) define the review session rules: read `review/context.json`; open every tile listed in `screens/index.json`; check each of `source_accuracy`, `calculations`, `coverage`, `opinion`, `visual` against real material and record concrete evidence; write `runs/<job_id>/audit-review.json` copying the four context values with `mode: separate_review_pass`; never modify `draft/` or the input; record any defect as an `open` issue; record `visual` as `pass` only when every tile was opened and the evidence names the tiles and cites the page metrics, and as `revise` with the reason when the screens are missing or incomplete; run the audit with the review record, and run `render_report.py --final` only when the audit decision is `pass`; and (c) state that a pass is never recorded for work that did not happen; and the committed manifest shall equal the output of the manifest regeneration command, `claude-settings.json` and every file under `skills/` shall be byte-identical to their state before this SPEC.

**REQ-AIR6-014** — When the review session ends, the service shall compare the SHA-256 of `draft/report.html` and `draft/report-input.json` with the values recorded before the launch and shall record the comparison in the receipt; a difference makes the screen verification not admissible (REQ-AIR6-016).

### 4.4 영수증과 최종본 인정 (규칙 7)

**REQ-AIR6-015** — After the review process group has ended, the service shall write `runs/<job_id>/review/receipt.json` itself, overwriting any file of that name the session may have written, recording the outcome (`reviewed`, `review_failed`, `timeout`, `cancelled`, `integrity_failed`, `disabled`), the process exit information, the draft and input hashes at start and end, the screens outcome and the SHA-256 of the screens index, the list of expected tile files, the list of tile files the session actually read, the summary of `audit-review.json` (present, SHA-256, `mode`, `checks.visual.status`, `input_sha256`, `preview_sha256`, `reviewed_at`), and the admissibility verdict with its reasons; a tile counts as read only when the session's output stream contains a `Read` tool call whose path resolves to that tile of this job's `screens/` directory and a matching tool result that is not flagged as an error.

**REQ-AIR6-016** — The goose runner's report selection shall classify a report as `final` only when the existing condition holds (`final/report.html` is a regular file and `final/render-validation.json` carries `delivery_allowed: true`) and the receipt admits the screen verification, that is, all of the following: the screens outcome is `complete`; the screens index hash of `draft/report.html` equals the current `draft/report.html` hash and the `preview_sha256` in `audit-review.json`; every listed tile file exists with the recorded SHA-256; every listed tile was read (REQ-AIR6-015); the mobile page metrics show no horizontal overflow; the draft and input hashes did not change during the review (REQ-AIR6-014); `audit-review.json` has `mode: separate_review_pass`, `checks.visual.status: pass`, and a `reviewed_at` not earlier than the capture's `finished_at`; otherwise it shall classify the report as `draft` and log the first unmet condition. Without a receipt no report is `final`.

### 4.5 검증 조건

**REQ-AIR6-017** — Every new and changed goose backend test shall run under the existing shared network guard without recording a connection attempt, shall inject a fake browser driver and a fake or script-stub `claude` instead of a real browser or the real `claude`, shall not read or write the real home directory or the installed harness, and the existing goose tests shall keep passing (baseline `267 passed` for `pytest backend/tests -k goose`, research P17, changed only by the tests this SPEC deliberately updates).

**REQ-AIR6-018** — When a goose job runs on stock code 020150 on the deployed server after the restart required by the manifest change (up to two runs on the same KST day), then in every run the job shall end `done`, the screens index outcome shall be `complete`, the receipt shall list every expected tile as read, the delivery audit run on the review session's `audit-review.json` with that run's draft input and preview shall emit none of `AUDIT_INPUT_VERSION`, `AUDIT_PREVIEW_VERSION`, `AUDIT_TIME`, `AUDIT_MODE`, `REVIEW_SOURCE_ACCURACY`, `REVIEW_CALCULATIONS`, `REVIEW_COVERAGE`, and `REVIEW_OPINION`, and the rule-7 consistency conditions of REQ-AIR6-016 shall hold between the receipt, the review record, and the delivery status. This is a gating observed-verification requirement: the SPEC does not close while it is unmet.

## 5. 제외 범위 (Out of Scope)

### Out of Scope — 감수 결과의 수정 반복

- 감수 세션이 찾은 결함을 입력 JSON에 반영해 초안을 다시 만들고 재감수하는 반복(`delivery-audit.md`의 수정→재감수 3회 반복). 이 SPEC은 한 번 감수하고 `issues`에 남기는 데까지다(D4). 수정·재캡처·재감수 루프는 후속 SPEC 후보다.
- 감수 세션이 사실 대조를 얼마나 충실히 했는지의 기계 검증. 감사기 스스로 "사실의 진실성 증명이 아니다"라고 밝히며(`audit_report.py:106`), 이 SPEC의 영수증은 "화면 이미지를 열었다"까지만 증명한다.

### Out of Scope — 다른 감사 결함과 조사 품질

- `LATEST_SEARCH_*`(예: 네이버 금융 접근 차단), `DART_*`, `QUARTER_HISTORY`, `CHART_*`, `UNRESOLVED_ISSUE` 해소. 이 SPEC 뒤에도 이런 결함으로 전달 상태가 `draft`일 수 있다.
- goose 1차 세션의 조사·작성 품질 개선.

### Out of Scope — 권한·구조·표시

- goose 권한(`claude-settings.json`)·실행 인자·벤더링 스킬·감사 스크립트 변경(D3).
- 화면 이미지를 사용자 화면(프론트)에 보여 주는 기능, 화면·영수증의 보관 폴더 복사(`goose_storage` 허용 목록), 전달 상태가 `draft`인 사유를 사용자에게 알리는 배너.
- 브라우저 자동 설치·다운로드. 호스트에 브라우저를 두는 것은 운영 요건으로 README에 적는다.
- 외부 웹 글꼴(CDN)을 불러온 화면의 재현. 캡처는 외부 네트워크를 막으므로 대체 글꼴로 그려진다(D7, plan.md `[NEEDS CLARIFICATION]`).
- `independent_agent` 방식(서브에이전트 감수)과 다중 감수자.
