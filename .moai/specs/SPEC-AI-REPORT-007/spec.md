---
id: SPEC-AI-REPORT-007
title: "goose 네이버 최신 뉴스 사전 수집 (서버가 goose 실행 전에 네이버 모바일 뉴스 JSON을 받아 둔다)"
version: "0.3.0"
status: draft
created: 2026-10-21
updated: 2026-10-21
author: manager-spec
priority: High
phase: "v0.6.0 target"
module: "backend/services"
lifecycle: spec-anchored
tags: "ai-report, goose, naver, prefetch, fail-open, harness"
tier: M
related_specs: [SPEC-AI-REPORT-005, SPEC-AI-REPORT-004, SPEC-AI-REPORT-006, SPEC-TEST-HERMETIC-001]
---

# SPEC-AI-REPORT-007: goose 네이버 최신 뉴스 사전 수집

## HISTORY

| 버전 | 일자 | 작성 | 내용 |
|---|---|---|---|
| 0.1.0 | 2026-10-21 | manager-spec | 초안. 칸반 카드 t19. 리드 승인 방향(서버가 네이버 모바일 뉴스 JSON을 사전 수집 → 색인 → 하네스 규칙으로 goose가 `naver` 검색 기록을 남김) 반영. 근거는 `.moai/reports/t19/` |
| 0.2.0 | 2026-10-21 | manager-spec | plan-audit 1회차(FAIL 0.81, `.moai/reports/t19/plan-audit.md`) 반영: 라이브 게이트에서 goose가 지어낸 `no_results`를 막음(D1a), REQ-013·AC-012의 출처 규칙을 "색인 `ok` 항목만"으로 통일하고 세 검사를 같은 회차에 요구(D1b), SPEC-AI-REPORT-006(카드 t18)과의 규칙 번호·매니페스트·`_run` 충돌을 필수 병합 단계로 명시(D3), 요청 시간 상한을 전송 계층과 무관한 `asyncio.wait_for`로 규정(D4), `outcome` 판정 규칙을 REQ-AIR7-014로 신설(D5), 실패할 수 없던 "blocked 없음" 조항 삭제(D7), 규칙의 `accessed_at` 값 지정(D8), `phase` 값을 미확정 가정으로 표기(D9). REQ 14·AC 14 |
| 0.3.0 | 2026-10-21 | manager-spec | plan-audit 2회차(FAIL 0.85, `.moai/reports/t19/plan-audit-iter2.md`) 반영, REQ 14·AC 14 유지: REQ-013의 "다른 회차" 검사를 색인 `outcome`에 따라 성공 형태(`complete`·`partial`)와 지어냄 형태(그 밖)로 나눠 REQ-010이 허용하는 대체 기록을 위반으로 보지 않게 함(N1), 성공 형태에 "`naver` 항목은 정확히 한 건, `source_ids` 비어 있지 않음"을 더함(N2), REQ-005의 선언 길이 검사를 "본문을 읽기 전에 거부"로 규정(N4 근거), REQ-014를 번호 순서 자리(§5.7)로 옮김(N7) |

관계: SPEC-AI-REPORT-005(DART 원문 사전 수집, completed)와 같은 구조를 네이버 채널에 적용한다. 005의 수집기·색인·하네스 규칙 8은 수정하지 않고, 작업 서비스에 두 번째 수집기 하나를 끼운다. 004·005 문서는 수정하지 않는다. 같은 시기에 카드 t18이 SPEC-AI-REPORT-006(goose 최종본 경로, 커밋 `4663bb3`, draft)을 진행하며, 그 SPEC도 `harness-instructions.md`에 규칙 9를 더하고 매니페스트를 재생성하며 `goose_job_service.py`의 `_run`을 바꾼다(006 spec.md 65~67행). 두 SPEC의 병합 절차는 `plan.md §5`에 필수 단계로 둔다.

`phase` 값은 리드가 `"v0.6.0 target"`으로 정했다(2026-10-21, 근거 `progress.md` P15: TEST-HERMETIC-001·RS-REBALANCE-001·006이 모두 `v0.6.0 target`). 저장소에는 이 값을 고정하는 버전 원천이 없다(`pyproject.toml` `version = "0.1.0"`, 버전 태그 없음). 처음 적은 `"v0.5.5 target"`은 계열 순번을 이은 가정이었고 폐기했다.

---

## 1. 개요

전체 기업 보고서(`deep_report`)의 전달 감사는 `naver` 채널의 최근 검색 기록을 요구한다. 라이브 실행 a5becbb9(020150, 2026-10-21)에서 goose는 `naver` 채널을 `result: "blocked"`로 적었고, 감사 스크립트는 `blocked`를 통과 수단으로 인정하지 않으므로 `LATEST_SEARCH_NAVER` 결함이 남았다.

이 SPEC은 DART 사전 수집(SPEC-AI-REPORT-005)과 같은 방식으로 문제를 푼다. 백엔드 서버가 goose 실행 직전에 네이버 증권 모바일 뉴스 JSON을 한 번 받아 작업 폴더 `runs/<job_id>/naver/`에 기사별 텍스트 파일과 `index.json`으로 저장하고, 하네스 지침에 "이 파일을 실제로 열었을 때만 읽었다고 적고, 색인의 검색 정보를 `naver` 검색 기록으로 옮겨라"는 규칙을 더한다. goose 권한은 넓히지 않는다.

이 SPEC이 끝나도 goose 결과물은 **초안(`draft`)** 이다. 이 SPEC의 성공은 "정상 상장사에 대해 `LATEST_SEARCH_NAVER` 결함이 더 이상 나오지 않고, 그 근거가 된 열람 기록이 서버 수집본과 일치하는 것"이다.

## 2. 근거 (관측 기록)

### 2.1 막힘 기록 원문

출처: `.moai/reports/t19/a5becbb9-research-window.json` (goose의 `company-input.json`과 `draft/report-input.json`에 같은 항목이 있다).

```json
{
  "channel": "naver",
  "searched_at": "2026-10-21T13:13:00+09:00",
  "query": "finance.naver.com/item/main.naver?code=020150 및 뉴스·모바일 API",
  "result": "blocked",
  "source_ids": [
    "naver_blocked"
  ],
  "note": "검색 시각은 근사(±1분)입니다. 도구가 finance.naver.com, m.stock.naver.com, polling.finance.naver.com 접근을 차단했습니다. 차단은 결과 없음이 아니며 네이버 채널은 미완료입니다."
}
```

이 `note`는 goose(모델)가 쓴 주장이다. 무엇이 실제로 막았는지는 관측되지 않았다(§8 Gap G1).

### 2.2 증거 경로

| 경로 | 내용 |
|---|---|
| `.moai/reports/t19/investigation.md` | 감사 규칙 읽기, 네이버 엔드포인트 curl 관측표, 가설, Gap |
| `.moai/reports/t19/a5becbb9-research-window.json` | a5becbb9 실행의 `research_window` 원문(위 2.1) |
| `.moai/reports/t19/plan-audit.md` | plan-audit 1회차 보고서와 프로브 기록 |
| `.dev-server.log` (주 체크아웃) | a5becbb9 실행 중 권한 거부 기록 |

### 2.3 네이버 엔드포인트 관측 (리드, 개발 머신 curl, 2026-10-21)

| 주소 | 관측 |
|---|---|
| `finance.naver.com/item/news_news.naver?code=020150` | HTTP 410 |
| `finance.naver.com/item/news_notice.naver?code=020150` | HTTP 410 |
| `m.stock.naver.com/api/news/stock/020150?pageSize=5&page=1` | HTTP 200 JSON, `items[]`에 `id`, `officeId`, `articleId`, `officeName`, `datetime`(예: `202610211352`), `title`, `body` |
| `search.naver.com` 뉴스 검색 | HTTP 200 HTML |

### 2.4 감사 규칙 (코드 읽기)

`backend/goose_harness_src/skills/goose/workflows/fact-check/scripts/audit_report.py` 44·50·51·52행(프로브는 `progress.md §E.1` 사실표 P3):

- `deep_report`면 검사 채널에 `naver`가 들어간다(44행).
- 통과 조건: `searches` 항목 중 `channel == "naver"`, `searched_at`이 cutoff 전 24시간 이내, `query`·`note`가 비어 있지 않음, 그리고 `result == "read"`이면서 `read_ids(source_ids)`가 참이거나 `result == "no_results"`(50·51행).
- `read_ids`는 각 출처가 `verification == "direct_read"`이고 `read_scope`가 비어 있지 않을 것을 요구한다. `naver` 채널 호출은 `dart=False`라 출처 호스트는 검사하지 않는다(21~28·51행).
- `result == "no_results"`는 출처나 다른 조건 없이 통과한다(51행). 따라서 감사만으로는 goose가 지어낸 `no_results`를 막을 수 없다 — 이 SPEC의 라이브 게이트(REQ-AIR7-013)가 그 경우를 막는다.
- `blocked`는 어떤 경우에도 통과하지 못한다. 결함 문구에 "차단은 완료가 아닙니다"가 들어 있다(52행).

### 2.5 서버 사전 수집을 택한 이유 (지침만 고치는 대안을 버린 이유)

- goose 권한 파일 `backend/goose_harness_src/claude-settings.json`은 `WebFetch`를 도메인 제한 없이 허용한다(`"WebFetch"` 1회, `WebFetch(` 0회 — 사실표 P1).
- `.dev-server.log`에서 a5becbb9가 나온 줄 중 권한 거부는 1건이고 도구는 Bash다. 같은 줄들에 `WebFetch`는 0회 나온다(사실표 P2).
- 따라서 권한 설정은 "막힘"을 설명하지 못한다. 막힘의 실제 원인이 관측되지 않았으므로, "모바일 API로 가라"는 지침만 더하는 방식은 효과를 예측할 수 없다. 서버가 직접 받아 두면 goose 쪽 도구 거동과 무관하게 열 수 있는 로컬 파일이 생긴다. 이 판단은 SPEC-AI-REPORT-005가 DART에 대해 내린 결정 D2와 같은 형태다.

## 3. 확정 결정

| ID | 결정 | 출처 |
|---|---|---|
| D1 | 서버가 goose 실행 전에 네이버 증권 모바일 뉴스 JSON을 받아 `runs/<job_id>/naver/`에 쓴다. goose 권한 파일은 바이트 단위로 그대로 둔다 | 리드 승인 2026-10-21 |
| D2 | "읽었다"는 기록은 사실이어야 한다: 이번 실행에 서버가 받은 기사 텍스트 파일을 goose가 이번 세션에서 실제로 연 경우만 `direct_read`. 서버는 열람 기록을 만들지 않는다 — 색인은 무엇을 받았는지만 적는다 | SPEC-AI-REPORT-005 D3·규칙 8-2와 같은 원칙 |
| D3 | 서버가 받은 것은 "모바일 뉴스 API 응답의 기사 제목·본문 필드"다. 기사 원문 페이지와 대조하지 않았으므로 `read_scope`와 `limitations`에 그 범위를 그대로 적는다. 본문 필드가 비어 있는 기사는 메타데이터뿐이라 읽은 출처로 쓸 수 없다(`metadata_only`) | 이 SPEC 결정 |
| D4 | 사전 수집의 어떤 실패도 작업을 막지 않는다(fail-open). 실패하면 goose는 기존 방법으로 시도하고 결과를 그대로 적는다. `blocked`를 `read`나 `no_results`로 바꿔 적지 않는다 | 카드 t19 지시 |
| D5 | 진행 단계(`progress` 이벤트)를 새로 만들지 않는다. 프론트는 바꾸지 않는다. 네이버 수집은 기존 `dart_prefetch` 단계 표시 동안 이어서 실행된다 | 이 SPEC 결정, 근거 plan.md §2 T6 |
| D6 | 작업 간 캐시 없음. 수집본은 작업 폴더와 함께 기존 보존 규칙(최근 10개)으로 정리된다 | SPEC-AI-REPORT-005 D7과 같음 |
| D7 | 서버 수집본에 `ok` 파일이 있으면 `naver` 채널 기록은 그 파일로 만든 한 건만 둔다. goose가 다른 경로로 읽은 네이버 계열 기사는 `original_news` 채널에 적는다. 라이브 게이트는 `naver` 채널의 모든 `read` 출처가 색인 `ok` 항목이어야 통과한다 | 이 SPEC 결정(plan-audit D1b) — 근거: 게이트의 목적은 "사전 수집이 통과를 만들었다"를 보이는 것이다. 다른 출처를 허용하면 서버 수집이 실패하고 대체 경로로 통과한 경우와 구분할 수 없다 |
| D8 | 하네스 규칙의 번호는 고정하지 않는다. SPEC-AI-REPORT-006과 둘 중 나중에 병합되는 쪽이 다음 빈 번호를 쓰고, 그 규칙의 하위 항목 번호를 같이 바꾼다. 인수 기준은 번호에 기대지 않는 문자열로 검사한다 | 이 SPEC 결정(plan-audit D3) |

기술 결정 T1~T8은 `plan.md §2`에 둔다.

## 4. 변경 범위 [DELTA]

| 표기 | 대상 | 내용 |
|---|---|---|
| [NEW] | `backend/services/goose_naver_prefetch.py` | 요청 1회 → 응답 해석 → 기사별 텍스트 파일·원본 응답·`index.json` 저장 |
| [MODIFY] | `backend/services/goose_job_service.py` | 네이버 수집기 생성자 주입(기본값 없음), DART 수집 뒤·무결성 재검사 전 호출, 끄기 스위치, 운영 인스턴스 연결 |
| [MODIFY] | `backend/goose_harness_src/harness-instructions.md` | 네이버 사전 수집본 사용 규칙 추가(번호는 D8) |
| [MODIFY] | `backend/goose_harness_src/goose-manifest.json` | 지침 변경에 따른 재생성 |
| [NEW] | `backend/tests/test_goose_naver_prefetch.py`, `backend/tests/fixtures/naver/` | 녹화·합성 JSON 픽스처와 수집기 테스트 |
| [MODIFY] | `backend/tests/test_goose_job_service.py` | 연결·순서·취소·스위치 테스트 추가 |
| [EXISTING] | `backend/tests/conftest.py` | 변경 없음 — 파일 이름이 `test_goose_`로 시작하면 네트워크 가드가 이미 적용된다 |
| [EXISTING] | `backend/goose_harness_src/claude-settings.json` | 변경 없음(D1) |
| [EXISTING] | `backend/goose_harness_src/skills/**` (감사 스크립트 포함) | 변경 없음 |
| [EXISTING] | `backend/services/goose_dart_prefetch.py`, `frontend/**` | 변경 없음 |

## 5. 요구사항 (GEARS)

### 5.1 실행 위치와 수명

**REQ-AIR7-001** — Where a Naver prefetcher has been injected into the job service (the production service instance injects it; the constructor default is no Naver prefetcher, which keeps the pre-SPEC behavior), when a goose job's background task begins, the job service shall run the Naver prefetch for that job's stock code after the DART prefetch (when one is injected) and before the pre-run harness integrity re-check and the goose runner, writing under `runs/<job_id>/naver/`; the pre-run integrity re-check shall run whenever at least one prefetcher is injected.

**REQ-AIR7-002** — When a job is cancelled (user cancel or server shutdown) while the Naver prefetch is in progress, the job service shall end the job in the `cancelled` state through the existing cancellation path and shall not launch the goose runner for that job.

**REQ-AIR7-003** — Where a Naver prefetcher is injected and the environment variable `AI_REPORT_GOOSE_NAVER_PREFETCH` is set to `0`, the job service (the sole owner of this switch) shall not invoke the Naver prefetcher, shall write a Naver index whose outcome is `disabled`, and shall proceed to the goose runner.

**REQ-AIR7-004** — The job service shall emit no progress event for the Naver prefetch, so that the sequence of progress events of a job with a Naver prefetcher injected equals that of the same job without one.

### 5.2 요청

**REQ-AIR7-005** — The Naver prefetcher shall send at most one HTTP request per job: a `GET` to `https://m.stock.naver.com/api/news/stock/<code>?pageSize=10&page=1`, bounded as a whole (send plus body read) by a 10-second timeout enforced with `asyncio.wait_for` around the send coroutine independently of the HTTP transport — the same form as `goose_dart_prefetch.py` line 376 — and by a maximum accepted response size of 2 MB, rejecting a declared `content-length` above the limit before reading any of the body and otherwise checking the accumulated size while streaming the body; it shall send requests only to `https` URLs whose parsed hostname is exactly `m.stock.naver.com`, shall not follow redirects, and shall reject a stock code that is not six ASCII digits without sending any request.

### 5.3 응답 해석과 저장

**REQ-AIR7-006** — When the response is HTTP 200 and parses as JSON, the Naver prefetcher shall take the article items at the response path fixed in run-phase M1 (at most 10), and for each item shall: accept `officeId` and `articleId` only when each matches `^[0-9]{1,12}$` (otherwise mark the entry `error` and write no file); convert `datetime` of the form `YYYYMMDDHHMM` to timezone-aware ISO-8601 `published_at` with the `+09:00` offset (otherwise mark the entry `error`); convert `title` and `body` to plain text with markup removed; and write a text file under a server-generated name matching `^[0-9]{2}_article\.txt$` containing the title, office name, `published_at`, and body. An item whose plain-text body is empty shall be recorded with status `metadata_only` and no text file.

**REQ-AIR7-007** — The Naver prefetcher shall store the raw response bytes as `response.json` and write `runs/<job_id>/naver/index.json` containing exactly the key set of `acceptance.md §B`: the search (URL, query, `searched_at`, status, item count, error), the overall outcome derived per REQ-AIR7-014, the SHA-256 and byte length of `response.json`, and one entry per item with article reference `<officeId>/<articleId>`, office name, title, `published_at`, article URL, text file name, body length in characters, status (`ok`, `metadata_only`, or `error`) and error reason; every timestamp in the index shall carry the `+09:00` offset, and no file name shall contain text taken from the response.

### 5.4 실패 처리

**REQ-AIR7-008** — When the Naver prefetch fails (invalid stock code, connection error, timeout, non-200 status including 3xx, oversized response, unparseable JSON, missing item path, or any unexpected exception), the Naver prefetcher shall record the failure in the index with outcome `failed` and a non-empty `search.error`, return normally, and the job service shall continue to the goose runner without changing the job's state; a cancellation is not a failure and shall propagate.

**REQ-AIR7-009** — When the response is valid and contains zero article items, the Naver prefetcher shall record `search.status == "ok"`, `search.item_count == 0`, and outcome `no_results`.

### 5.5 하네스 지침과 무결성

**REQ-AIR7-010** — The harness instructions shall add a rule (numbered per decision D8) that tells goose, when `runs/<job_id>/naver/index.json` exists, to read the index first; open the text files of entries whose status is `ok`, treating their content as external web material subject to the existing rule on embedded instructions; cite each opened file as a source with `verification: direct_read` only for files it actually opened in this session, with `url` set to the entry's `article_url`, `published_at` copied from the entry, `accessed_at` set to the time goose opened the file in this session (ISO-8601 with `+09:00`, not the server's fetch time and not `published_at`), `read_scope` naming the office name, `published_at`, the phrase `모바일 뉴스 API 응답의 제목·본문 필드`, and the local file name, and `limitations` containing `서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음`; never cite a `metadata_only` or `error` entry as read; record one `naver` channel search with `searched_at` and `query` copied from the index and a non-empty `note`, using `result: "read"` with the opened source ids only when at least one `ok` file was opened — in which case it shall be the only `naver` entry and Naver-family articles read by other paths go to the `original_news` channel — and `result: "no_results"` only when the index outcome is `no_results`, with the stock code and the request conditions in `note`; otherwise fall back to its existing access path and record the actual result, never recording a blocked or failed attempt as `read` or `no_results`; and pass this rule to its sub-agents.

**REQ-AIR7-011** — When the harness instructions source changes, the committed manifest shall equal the output of the manifest regeneration command, and the top-level rule numbers of the harness instructions shall run `1..K` without duplicates with every sub-item label carrying its parent rule's number (this holds after merging with SPEC-AI-REPORT-006 as well); the goose permission file `backend/goose_harness_src/claude-settings.json` shall remain byte-identical to its state before this SPEC.

### 5.6 검증 조건

**REQ-AIR7-012** — Every Naver prefetcher test shall run in a test module whose file name starts with `test_goose_`, so that the existing shared network guard records and fails any connection or name-resolution attempt; tests shall answer requests through an injected `httpx.MockTransport` serving recorded or synthetic JSON fixtures, any test that waits on a request shall carry an outer `asyncio.wait_for` bound, and existing job-service tests that construct the service without a Naver prefetcher shall issue zero Naver requests.

**REQ-AIR7-013** — When a goose job runs on stock code 020150 on the deployed server after integration and the restart that installs the new harness (up to two runs on the same KST day), one and the same run shall satisfy all of: (1) the Naver index outcome is `complete` or `partial`; (2) the delivery audit on goose's draft input does not emit `LATEST_SEARCH_NAVER`; (3) the success form of the record check holds — the draft input has exactly one `naver` entry, that entry has `result: "read"` and a non-empty `source_ids` list, and every source it cites has a `url` equal to the `article_url` of an index entry with status `ok`, a `read_scope` containing that entry's text file name, and `limitations` containing `서버 사전 수집본으로 열람`. In every other run executed that day, the record check shall hold in the form that run's index outcome selects: the success form above when the outcome is `complete` or `partial`; otherwise only the fabrication form — no `naver` entry with `result: "no_results"` unless the index outcome is `no_results`, and no `naver` `read` source whose `url` equals an index `article_url` unless that index entry has status `ok` and matches `read_scope` and `limitations` as above — so that the fallback records REQ-AIR7-010 allows for a `failed`, `disabled`, missing, or `no_results` index (an honest `blocked`, a `read` of sources outside the index, or `no_results` for a `no_results` index) are not violations. This is a gating observed-verification requirement owned by the lead after integration; the SPEC does not close while it is unmet, and it is not part of the run-phase lane.

### 5.7 색인 결과 판정 (REQ-AIR7-007이 참조)

**REQ-AIR7-014** — The Naver prefetcher shall derive the index `outcome` as follows, in this order: `disabled` only when written by the job service for the off switch; `failed` when the request or response handling failed (REQ-AIR7-008); `no_results` when the response was valid and held zero article items; `complete` when every item entry has status `ok`; `partial` when at least one entry is `ok` and at least one is `metadata_only` or `error`; and `failed` when items were present but no entry is `ok`.

## 6. 하네스 규칙이 할 수 있는 것과 없는 것

| 질문 | 답 |
|---|---|
| 서버가 받은 기사로 `naver` 채널을 `read`로 통과시킬 수 있나 | goose가 `ok` 항목의 텍스트 파일을 실제로 열면 그렇다. 감사는 출처 호스트를 보지 않고 `direct_read`와 `read_scope`만 본다(§2.4). 열지 않으면 `read`로 적지 않는다 |
| `metadata_only` 항목(제목·시각만 있음)으로 통과시킬 수 있나 | 없다. 읽을 본문이 없으므로 출처로 쓰지 않는다 |
| 검색은 됐는데 기사가 0건이면 | 색인 `outcome == "no_results"`일 때만 `result: "no_results"`를 쓰고, `note`에 종목코드·`pageSize`·`page`·`searched_at`을 적는다 |
| 색인에 `ok` 기사가 있는데 `no_results`를 쓸 수 있나 | 없다. 감사는 이를 막지 못하지만(§2.4) 라이브 게이트 검사 3이 위반으로 잡는다 |
| 수집이 실패한 회차에 goose가 `blocked`를 적거나 기존 경로로 읽으면 라이브 게이트 위반인가 | 아니다. 그런 회차는 통과 회차가 될 수 없을 뿐이고, 검사 3은 지어낸 기록(색인이 `no_results`가 아닌데 `no_results`, 색인의 `ok`가 아닌 기사를 읽었다는 주장)만 잡는다(REQ-AIR7-013) |
| 수집이 실패했으면 | 기존 방법(WebFetch 등)으로 시도하고 실제 결과를 적는다. 그래도 못 읽으면 `blocked` 그대로 두며 감사 결함은 남는다 — 조용한 통과는 없다 |
| 열람 범위를 기사 원문 페이지라고 적을 수 있나 | 없다. 받은 것은 API 응답의 제목·본문 필드다(D3) |
| `accessed_at`에는 무엇을 적나 | goose가 이번 세션에서 그 파일을 연 시각. 서버 수집 시각은 goose의 열람이 아니다 |

## 7. 제외 범위 (Out of Scope)

### Out of Scope — 다른 카드의 작업

- 카드 t18(SPEC-AI-REPORT-006)의 항목: goose 최종본 경로, 별도 감수(review pass), 화면 캡처(screenshots).
- 카드 t14·t15의 테마 표 작업, `backend/services/naver_theme_v2/` 수정.
- 메인 브랜치 통합(merge), 라이브 goose 실행 — 리드 몫(REQ-AIR7-013).

### Out of Scope — 감사와 권한

- 감사 규칙(`audit_report.py`) 변경. `blocked`·`no_results` 처리 방식은 그대로 둔다.
- goose 권한(`claude-settings.json`)·실행 인자·프롬프트 변경.
- `LATEST_SEARCH_NAVER` 외 감사 결함 해소.

### Out of Scope — 수집 범위

- 기사 원문 페이지(`n.news.naver.com` 등) 본문 수집, `search.naver.com` HTML 파싱, 공식 검색 API(인증키 필요).
- 2페이지 이상 수집, 재시도 큐, 작업 간 캐시(D6).
- 네이버 수집 전용 진행 단계·프론트 표시(D5).
- 기사 내용 요약·해석·감성 분석 — 서버는 받은 텍스트만 공급한다.

## 8. Gaps (관측하지 않은 것)

- G1: a5becbb9에서 `naver` 채널을 실제로 막은 원인. 기록된 "차단"은 모델이 쓴 주장이며 도구 오류 원문은 보존되지 않았다. 서버 로그는 실행기가 해석한 권한 거부만 남기므로, 로그에 WebFetch가 없다는 사실이 WebFetch 오류가 없었다는 증거는 아니다.
- G2: goose 샌드박스 안에서의 WebFetch 거동(이 머신의 curl과 다를 수 있다).
- G3: 모바일 API의 호출 제한·이용 약관. 관측은 소수 회 호출뿐이다.
- G4: 모바일 API의 안정성과 정확한 응답 구조(최상위가 객체인지 배열인지, `items` 경로, `body`가 전문인지 요약인지, 마크업 포함 여부) — run 단계 M1에서 녹화 픽스처로 확정한다.
- G5: `article_url` 형태(`https://n.news.naver.com/mnews/article/<officeId>/<articleId>`)가 실제로 기사를 가리키는지 — M1에서 GET 1회로 관측한다. 관측이 다르면 M1이 형태를 바꾸고 manager-spec 재위임으로 반영한다.

## 9. 잔여 위험

- 비공식 모바일 API라 예고 없이 바뀔 수 있다. 같은 계열(`naver_theme_v2`)이 카드 t14에서 스키마 변경을 겪었다. 바뀌면 이 수집은 `failed`로 기록되고 goose는 기존 방법으로 돌아가며, `LATEST_SEARCH_NAVER`는 다시 남는다(조용한 통과는 없다).
- 라이브 통과(REQ-AIR7-013)는 goose(모델)가 규칙을 따르는지에 달려 있다. goose가 파일을 열었다고 적고 실제로는 일부만 읽은 경우는 스트림 기록을 보존하지 않으므로 기계로 검증할 수 없다.
- 감사는 `naver` 출처의 호스트를 검사하지 않고 `no_results`를 조건 없이 받으므로, 규칙을 어긴 기록도 감사를 통과할 수 있다. 이를 드러내는 것은 REQ-AIR7-013 검사 3뿐이며, 그 검사는 라이브 회차에만 적용된다. 라이브 게이트 뒤의 일상 실행에서는 같은 위반이 감사 통과로 보일 수 있다.
- SPEC-AI-REPORT-006과의 병합에서 규칙 번호·매니페스트를 손으로 합치면 무결성 실패나 하위 항목 번호 불일치가 생긴다. `plan.md §5`의 필수 병합 단계와 AC-AIR7-011 #4가 이를 잡는다.
