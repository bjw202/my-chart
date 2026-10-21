---
id: SPEC-AI-REPORT-007
title: "goose 네이버 최신 뉴스 사전 수집 (서버가 goose 실행 전에 네이버 모바일 뉴스 JSON을 받아 둔다)"
version: "0.1.0"
status: draft
created: 2026-10-21
updated: 2026-10-21
author: manager-spec
priority: High
phase: "v0.5.5 target"
module: "backend/services"
lifecycle: spec-anchored
tags: "ai-report, goose, naver, prefetch, fail-open, harness"
tier: M
related_specs: [SPEC-AI-REPORT-005, SPEC-AI-REPORT-004, SPEC-TEST-HERMETIC-001]
---

# SPEC-AI-REPORT-007: goose 네이버 최신 뉴스 사전 수집

## HISTORY

| 버전 | 일자 | 작성 | 내용 |
|---|---|---|---|
| 0.1.0 | 2026-10-21 | manager-spec | 초안. 칸반 카드 t19. 리드 승인 방향(서버가 네이버 모바일 뉴스 JSON을 사전 수집 → 색인 → 하네스 규칙으로 goose가 `naver` 검색 기록을 남김) 반영. 근거는 `.moai/reports/t19/` |

관계: SPEC-AI-REPORT-005(DART 원문 사전 수집, completed)와 같은 구조를 네이버 채널에 적용한다. 005의 수집기·색인·하네스 규칙 8은 수정하지 않고, 작업 서비스에 두 번째 수집기 하나를 끼운다. 004·005 문서는 수정하지 않는다.

---

## 1. 개요

전체 기업 보고서(`deep_report`)의 전달 감사는 `naver` 채널의 최근 검색 기록을 요구한다. 라이브 실행 a5becbb9(020150, 2026-10-21)에서 goose는 `naver` 채널을 `result: "blocked"`로 적었고, 감사 스크립트는 `blocked`를 통과 수단으로 인정하지 않으므로 `LATEST_SEARCH_NAVER` 결함이 남았다.

이 SPEC은 DART 사전 수집(SPEC-AI-REPORT-005)과 같은 방식으로 문제를 푼다. 백엔드 서버가 goose 실행 직전에 네이버 증권 모바일 뉴스 JSON을 한 번 받아 작업 폴더 `runs/<job_id>/naver/`에 기사별 텍스트 파일과 `index.json`으로 저장하고, 하네스 지침에 "이 파일을 실제로 열었을 때만 읽었다고 적고, 색인의 검색 정보를 `naver` 검색 기록으로 옮겨라"는 규칙을 더한다. goose 권한은 넓히지 않는다.

이 SPEC이 끝나도 goose 결과물은 **초안(`draft`)** 이다. 이 SPEC의 성공은 "정상 상장사에 대해 `LATEST_SEARCH_NAVER` 결함이 더 이상 나오지 않고, 그 근거가 된 열람 기록이 사실과 일치하는 것"이다.

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

기술 결정 T1~T8은 `plan.md §2`에 둔다.

## 4. 변경 범위 [DELTA]

| 표기 | 대상 | 내용 |
|---|---|---|
| [NEW] | `backend/services/goose_naver_prefetch.py` | 요청 1회 → 응답 해석 → 기사별 텍스트 파일·원본 응답·`index.json` 저장 |
| [MODIFY] | `backend/services/goose_job_service.py` | 네이버 수집기 생성자 주입(기본값 없음), DART 수집 뒤·무결성 재검사 전 호출, 끄기 스위치, 운영 인스턴스 연결 |
| [MODIFY] | `backend/goose_harness_src/harness-instructions.md` | 규칙 9(네이버 사전 수집본 사용) 추가 |
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

**REQ-AIR7-005** — The Naver prefetcher shall send at most one HTTP request per job: a `GET` to `https://m.stock.naver.com/api/news/stock/<code>?pageSize=10&page=1`, with a per-request timeout of 10 seconds and a maximum accepted response size of 2 MB; it shall send requests only to `https` URLs whose parsed hostname is exactly `m.stock.naver.com`, shall not follow redirects, and shall reject a stock code that is not six ASCII digits without sending any request.

### 5.3 응답 해석과 저장

**REQ-AIR7-006** — When the response is HTTP 200 and parses as JSON, the Naver prefetcher shall take the article items at the response path fixed in run-phase M1 (at most 10), and for each item shall: accept `officeId` and `articleId` only when each matches `^[0-9]{1,12}$` (otherwise mark the entry `error` and write no file); convert `datetime` of the form `YYYYMMDDHHMM` to timezone-aware ISO-8601 `published_at` with the `+09:00` offset; convert `title` and `body` to plain text with markup removed; and write a text file under a server-generated name matching `^[0-9]{2}_article\.txt$` containing the title, office name, `published_at`, and body. An item whose plain-text body is empty shall be recorded with status `metadata_only` and no text file.

**REQ-AIR7-007** — The Naver prefetcher shall store the raw response bytes as `response.json` and write `runs/<job_id>/naver/index.json` containing exactly the key set of `acceptance.md §B`: the search (URL, query, `searched_at`, status, item count, error), the overall outcome (`complete`, `partial`, `no_results`, `failed`, or `disabled`), the SHA-256 and byte length of `response.json`, and one entry per item with article reference `<officeId>/<articleId>`, office name, title, `published_at`, article URL, text file name, body length in characters, status (`ok`, `metadata_only`, or `error`) and error reason; every timestamp in the index shall carry the `+09:00` offset, and no file name shall contain text taken from the response.

### 5.4 실패 처리

**REQ-AIR7-008** — When the Naver prefetch fails (invalid stock code, connection error, timeout, non-200 status including 3xx, oversized response, unparseable JSON, missing item path, or any unexpected exception), the Naver prefetcher shall record the failure in the index with outcome `failed` and a non-empty `search.error`, return normally, and the job service shall continue to the goose runner without changing the job's state; a cancellation is not a failure and shall propagate.

**REQ-AIR7-009** — When the response is valid and contains zero article items, the Naver prefetcher shall record `search.status == "ok"`, `search.item_count == 0`, and outcome `no_results`.

### 5.5 하네스 지침과 무결성

**REQ-AIR7-010** — The harness instructions shall add a rule that tells goose, when `runs/<job_id>/naver/index.json` exists, to read the index first; open the text files of entries whose status is `ok`, treating their content as external web material subject to the existing rule on embedded instructions; cite each opened file as a source with `verification: direct_read` only for files it actually opened in this session, with `url` set to the entry's `article_url`, `published_at` copied from the entry, `read_scope` naming the office name, `published_at`, the phrase `모바일 뉴스 API 응답의 제목·본문 필드`, and the local file name, and `limitations` containing the marker `서버 사전 수집본으로 열람`; never cite a `metadata_only` or `error` entry as read; record one `naver` channel search with `searched_at` and `query` copied from the index and a non-empty `note`, using `result: "read"` with the opened source ids only when at least one `ok` file was opened, and `result: "no_results"` only when the index outcome is `no_results`, with the stock code and the request conditions in `note`; otherwise fall back to its existing access path and record the actual result, never recording a blocked or failed attempt as `read` or `no_results`; and pass this rule to its sub-agents.

**REQ-AIR7-011** — When the harness instructions source changes, the committed manifest shall equal the output of the manifest regeneration command; the goose permission file `backend/goose_harness_src/claude-settings.json` shall remain byte-identical to its state before this SPEC.

### 5.6 검증 조건

**REQ-AIR7-012** — Every Naver prefetcher test shall run in a test module whose file name starts with `test_goose_`, so that the existing shared network guard records and fails any connection or name-resolution attempt; tests shall answer requests through an injected `httpx.MockTransport` serving recorded or synthetic JSON fixtures, and existing job-service tests that construct the service without a Naver prefetcher shall issue zero Naver requests.

**REQ-AIR7-013** — When a goose job runs on stock code 020150 on the deployed server after integration and the restart that installs the new harness (up to two runs on the same KST day), the Naver index outcome shall be `complete` or `partial`, the delivery audit on goose's draft input shall not emit `LATEST_SEARCH_NAVER`, no `naver` search entry used for that pass shall have `result: "blocked"`, and every source cited by that `naver` entry shall map to an index entry with status `ok` whose text file name appears in the source's `read_scope` and whose `limitations` contains `서버 사전 수집본으로 열람`. This is a gating observed-verification requirement owned by the lead after integration; the SPEC does not close while it is unmet, and it is not part of the run-phase lane.

## 6. 하네스 규칙 9가 할 수 있는 것과 없는 것

| 질문 | 답 |
|---|---|
| 서버가 받은 기사로 `naver` 채널을 `read`로 통과시킬 수 있나 | goose가 `ok` 항목의 텍스트 파일을 실제로 열면 그렇다. 감사는 출처 호스트를 보지 않고 `direct_read`와 `read_scope`만 본다(§2.4). 열지 않으면 `read`로 적지 않는다 |
| `metadata_only` 항목(제목·시각만 있음)으로 통과시킬 수 있나 | 없다. 읽을 본문이 없으므로 출처로 쓰지 않는다 |
| 검색은 됐는데 기사가 0건이면 | 색인 `outcome == "no_results"`일 때만 `result: "no_results"`를 쓰고, `note`에 종목코드·`pageSize`·`page`·`searched_at`을 적는다 |
| 수집이 실패했으면 | 기존 방법(WebFetch 등)으로 시도하고 실제 결과를 적는다. 그래도 못 읽으면 `blocked` 그대로 두며 감사 결함은 남는다 — 조용한 통과는 없다 |
| 열람 범위를 기사 원문 페이지라고 적을 수 있나 | 없다. 받은 것은 API 응답의 제목·본문 필드다(D3) |

## 7. 제외 범위 (Out of Scope)

### Out of Scope — 다른 카드의 작업

- 카드 t18의 항목: goose 최종본 경로, 별도 감수(review pass), 화면 캡처(screenshots).
- 카드 t14·t15의 테마 표 작업, `backend/services/naver_theme_v2/` 수정.
- 메인 브랜치 통합(merge), 라이브 goose 실행 — 리드 몫(REQ-AIR7-013).

### Out of Scope — 감사와 권한

- 감사 규칙(`audit_report.py`) 변경. `blocked` 처리 방식은 그대로 둔다.
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
- 감사는 `naver` 출처의 호스트를 검사하지 않으므로, 규칙을 어긴 기록(열지 않은 파일을 `direct_read`로 적음)도 감사를 통과할 수 있다. 이를 드러내는 것은 REQ-AIR7-013의 출처 대조뿐이다.
