# SPEC-AI-REPORT-006 — 설계

버전 0.1.0 · 요구사항 `spec.md §4`, 결정 `plan.md §2`, 프로브 `research.md`. 이 문서는 구현 세부(스키마·절차·경계)를 정한다. 코드 식별자는 run 단계에서 확정하며 여기서는 역할 이름으로 적는다.

## 1. 구성요소와 경계

| 구성요소 | 위치 | 책임 | 하지 않는 일 |
|---|---|---|---|
| 캡처 모듈 | `goose_screenshot.py` | 브라우저 탐색·실행·종료, 두 뷰포트 타일 저장, `screens/index.json` | 감수·영수증·전달 판정 |
| 감수 보조 모듈 | `goose_review.py` | `review/context.json` 작성, 열람 기록 집계, 영수증 작성, 화면 확인 인정 판정 함수 | 프로세스 실행 |
| 실행기 | `goose_runner.py` | 감수 세션 `claude -p` 실행(`run_review`), 감수 프롬프트, 스트림에서 `Read` 호출·결과 수집, `select_report` | 캡처, 영수증 쓰기 |
| 작업 서비스 | `goose_job_service.py` | 후처리 순서·진행 이벤트·스위치·취소·fail-open, 영수증 쓰기 호출 | 판정 규칙 정의 |
| 하네스 지침 | `harness-instructions.md` | 1차·감수 세션 행동 규칙 | 서버 판정 |

주입 경계: 작업 서비스 생성자에 `screenshotter`, `reviewer`(둘 다 기본 없음)를 받는다. 운영 인스턴스에만 실제 구현을 붙인다(005의 `prefetcher`와 같은 패턴, P8). 캡처 모듈은 브라우저 구동을 `BrowserDriver` 인터페이스(뷰포트·URL·타일 구간을 받아 PNG 바이트와 지표를 돌려줌) 뒤에 둬서 테스트가 가짜를 꽂는다.

## 2. 후처리 순서와 실패 행렬

```
1차 세션 done + draft 존재
  → [스위치 0] 영수증 disabled, 끝
  → 무결성 재검사 ✗ → 영수증 integrity_failed, 끝 (작업은 러너 결과대로 종료)
  → emit screenshot → capture
        ✓ complete/partial    ✗ unavailable/failed/예외 (모두 index.json에 기록)
  → review/context.json 쓰기 (캡처 결과와 무관하게 쓴다; screens.outcome 포함)
  → emit review → run_review
        ✓ exit 0, audit-review.json 있음     ✗ 시작 실패/비정상 종료/시간 초과/기록 없음
  → (세션 프로세스 그룹 종료 확인)
  → 영수증 쓰기 (세션이 쓴 같은 이름 파일은 덮어쓴다)
  → 종료 훅 → select_report → 보관 → _finish
```

| 실패 지점 | 작업 상태 | 전달 상태 | 영수증 outcome | 후속 |
|---|---|---|---|---|
| 스위치 0 | done | draft | `disabled` | 후처리 없음 |
| 무결성 재검사 실패 | 러너 결과대로 | draft | `integrity_failed` | 캡처·감수 없음 |
| 브라우저 없음/실패/시간 초과 | done | draft(감수 결과와 무관하게 `final`은 인정 못 함) | 감수가 돌았으면 `reviewed` + 사유 `screens_not_complete` | 감수는 계속 실행(`visual: revise` 사유 기록) |
| 감수 세션 시작 실패/비정상 종료/기록 없음 | done | draft | `review_failed` | — |
| 감수 세션 시간 초과 | done | draft | `timeout` | 프로세스 그룹 종료 |
| 취소 | cancelled | (훅이 초안 보관, 기존 규칙) | `cancelled`(best-effort) | 그룹 종료 |
| 영수증 쓰기 실패 | done | draft(영수증 없음 = final 불가) | — | 로그 |

## 3. 화면 캡처

### 3.1 브라우저 실행

- 인자(고정 문자열 + 서버 값만): `--headless`(헤드리스 셸은 기본), `--disable-gpu`, `--hide-scrollbars`, `--remote-debugging-port=<서버가 고른 루프백 빈 포트>`, `--user-data-dir=<서버가 만든 임시 폴더>`, 시작 URL `about:blank`. 네트워크 차단 방식은 M1이 G3·G8에서 확정(`--host-resolver-rules="MAP * ~NOTFOUND"` 또는 DevTools `Network.setBlockedURLs`). `--no-sandbox` 필요 여부는 G9.
- 새 프로세스 그룹(`start_new_session=True`)으로 띄우고 종료·취소·시간 초과 때 그룹 전체를 종료한다(실행기의 `terminate_group` 패턴 재사용 가능). 임시 프로필 폴더는 `finally`에서 지운다.
- 접속: `http://127.0.0.1:<port>/json/list`에서 `page` 타입의 `webSocketDebuggerUrl`을 얻어 `websockets`로 연결(P14 관측: 시작 후 0.29초에 응답).

### 3.2 캡처 절차 (뷰포트마다)

1. `Emulation.setDeviceMetricsOverride`: 데스크톱 `1280×800, mobile=false`, 모바일 `390×844, mobile=true`, `deviceScaleFactor=1`.
2. `Emulation.setScriptExecutionDisabled(true)`(G3 확인 대상), 네트워크 차단 적용.
3. `Page.navigate(file://<resolved draft/report.html>)` 후 `Page.loadEventFired` 대기(예산 안에서). P14는 고정 3초 대기를 썼고 이벤트 대기는 M1이 확정한다.
4. `Runtime.evaluate`로 `document.documentElement`의 `scrollWidth`·`clientWidth`·`scrollHeight`를 읽는다. `horizontal_overflow = scrollWidth > clientWidth`.
5. `scrollHeight`를 1568px 단위로 나눠 타일 구간 `[y, y+h)`를 만든다(마지막 타일은 나머지). 개수가 24를 넘으면 그 뷰포트는 `too_tall`로 기록하고 타일을 만들지 않는다.
6. 타일마다 `Page.captureScreenshot{format:png, captureBeyondViewport:true, clip:{x:0,y,width,height,scale:1}}`(P14는 y=0 전체 높이만 관측, y>0 타일은 G3). 8 MiB 초과 타일은 그 뷰포트를 `error`로 기록한다.
7. 파일은 `screens/<viewport>-NN.png`로 쓰고 SHA-256·바이트 길이를 계산한다. 어떤 뷰포트가 실패해도 다른 뷰포트는 계속한다(`partial`).

전체 예산 60초는 브라우저 시작부터 정리까지의 벽시계 시간이며 초과하면 남은 구간을 `skipped`로 기록하고 그룹을 종료한다.

## 4. 스키마 (고정 키 집합)

### 4.1 `screens/index.json`

- 최상위: `schema_version`(1), `source`(`"draft/report.html"`), `preview_sha256`, `started_at`, `finished_at`, `outcome`, `browser`, `viewports`
- `browser`: `name`, `version`, `path_kind`(`env` | `path` | `known_location` | `none`). 브라우저 절대 경로는 적지 않는다(로그에만)
- `viewports[]`: `name`(`desktop` | `mobile`), `width`, `status`(`ok` | `error` | `too_tall` | `skipped`), `error`, `metrics`(`scroll_width`, `client_width`, `scroll_height`, `horizontal_overflow`), `tiles`
- `tiles[]`: `file`, `y`, `width`, `height`, `bytes`, `sha256`
- `outcome`: `complete`(두 뷰포트 `ok`) | `partial`(하나만 `ok`) | `unavailable`(브라우저 없음) | `failed`(둘 다 실패) | `disabled`
- 시각은 시간대 포함 ISO-8601, 오프셋 `+09:00`

### 4.2 `review/context.json` (서버가 감수 세션 시작 전에 씀)

- 최상위: `schema_version`(1), `job_id`, `code`, `now`, `input`(`path`, `sha256`), `preview`(`path`, `sha256`), `screens`(`index_path`, `outcome`, `tiles`: 읽어야 할 파일 상대 경로 목록), `audit_review_path`, `audit_output_path`, `final_dir`, `copy_into_review_record`(`input_sha256`, `preview_sha256`, `reviewed_at`, `mode`)
- `input.path` = `runs/<job_id>/draft/report-input.json`(P4: 입력 원본과 바이트 동일), `preview.path` = `runs/<job_id>/draft/report.html`
- `copy_into_review_record.reviewed_at` = `now`(감수 세션 시작 시각이며 감사기 요건 `cutoff ≤ reviewed_at ≤ 감사 시각`을 만족, P1 `:98-99`), `mode` = `"separate_review_pass"`
- 경로는 모두 하네스 기준 상대 경로(`runs/…`) — 하네스 규칙 4의 `..`·절대 경로 금지와 맞춘다

### 4.3 `review/receipt.json` (서버가 세션 종료 후 씀)

- 최상위: `schema_version`(1), `outcome`, `started_at`, `finished_at`, `process`(`exit_code`, `timed_out`), `hashes`(`input_start`, `input_end`, `preview_start`, `preview_end`), `draft_unchanged`, `screens`(`outcome`, `index_sha256`, `tiles_expected`, `tiles_read`), `audit_review`(`present`, `sha256`, `mode`, `visual_status`, `input_sha256`, `preview_sha256`, `reviewed_at`), `visual_admissible`, `reasons`
- `outcome`: `reviewed` | `review_failed` | `timeout` | `cancelled` | `integrity_failed` | `disabled`
- `reasons`: 미인정 사유 코드 목록(예: `screens_not_complete`, `preview_hash_mismatch`, `tile_missing`, `tile_not_read`, `mobile_overflow`, `draft_changed`, `mode_not_separate_review_pass`, `visual_not_pass`, `reviewed_before_capture`, `no_audit_review`)

## 5. 최종본 인정 판정 (`select_report`)

```
final_dir/report.html 이 정규 파일이고 final/render-validation.json 의 delivery_allowed == true   (기존 조건)
  AND receipt.json 이 있고 파싱되며 schema_version == 1
  AND receipt.visual_admissible == true
  AND sha256(draft/report.html) == receipt.hashes.preview_end        (영수증 이후 변조 확인)
→ ("final", final_dir)
그 외: draft/report.html 이 정규 파일이면 ("draft", draft_dir), 첫 미충족 조건을 로그
```

`visual_admissible`은 서버가 영수증을 쓸 때 REQ-AIR6-016의 조건을 모두 확인해 정한다. 판정 함수는 `goose_review.py`에 두고 `select_report`는 영수증 필드를 읽는다(영수증의 사실 필드 `tiles_read`·해시는 서버가 쓴 값). 세션이 영수증 이름의 파일을 써 두어도 서버가 종료 후 덮어쓴다(REQ-AIR6-015).

## 6. 열람 기록 수집

- 입력: 감수 세션의 `stream-json` 줄. 1차 세션과 같은 읽기 루프를 쓴다(`_read_stdout`)에 줄 구독자를 하나 더한다.
- 수집 규칙: `assistant` 줄의 `tool_use`(`name == "Read"`, `input.file_path`)를 `id`로 기억하고, 이후 `user` 줄의 `tool_result`(`tool_use_id` 일치)가 오류 표지(`is_error` 등, G1에서 이름 확정)가 아닐 때만 "읽음"으로 센다. 서브에이전트(`parent_tool_use_id` 있음)의 읽기도 센다.
- 경로 정규화: 절대 경로면 하네스 경로(`resolve_harness_dir()`) 아래여야 하고, 상대 경로면 하네스 기준으로 해석한 뒤 `os.path.normpath`한다. 결과가 정확히 `<harness>/runs/<이 작업 ID>/screens/<index.json에 적힌 타일 파일>` 중 하나일 때만 해당 타일로 센다. 기본 이름만 비교하거나 부분 문자열로 비교하지 않는다(다른 작업의 같은 이름 파일이 섞이지 않게).
- 메모리 상한: 기억하는 `tool_use`는 256개(기존 `_TOOL_MEMORY_LIMIT`과 같은 방식).

## 7. 하네스 지침 초안 (`harness-instructions.md`)

규칙 7 개정(1차 세션 대상):

> 7. 이 세션은 브라우저가 없으므로 화면 확인(visual) 검사를 통과로 기록하지 않는다. 이 세션은 `audit-review.json`을 쓰지 않고 `render_report.py --final`도 실행하지 않는다. 초안(`--output-dir runs/<job_id>/draft`)을 만들고 `audit_report.py`를 감수 기록 없이 한 번 실행한 뒤 끝낸다. 서버가 초안 뒤에 화면 캡처와 별도 감수 세션을 돌린다.

규칙 9 추가(프롬프트가 "감수 세션"이라고 밝힌 세션에만 적용):

> 9. 감수 세션 규칙. 이 세션은 초안을 쓴 세션이 아니다. 조사·작성을 다시 하지 않는다. (a) `runs/<job_id>/review/context.json`을 먼저 Read로 읽는다. (b) `fact-check/GUIDE.md`와 `references/delivery-audit.md`를 읽는다(규칙 7·9가 그 문서의 브라우저 관련 문장보다 우선한다). (c) `draft/`와 입력 JSON을 수정하지 않는다. 지적할 결함은 `audit-review.json`의 `issues`에 `status: "open"`으로 적는다. (d) 검사 5종(`source_accuracy`, `calculations`, `coverage`, `opinion`, `visual`)을 각각 실제 자료·수치·화면과 대조하고 `evidence`에 무엇을 어떻게 확인했는지 적는다. (e) `visual`은 `screens/index.json`의 모든 타일 파일을 Read로 하나씩 연 경우에만 `pass`로 적고, `evidence`에 연 타일 파일 이름들과 모바일 지표(`scroll_width`·`client_width`)를 적는다. 화면이 없거나 `index.json`의 `outcome`이 `complete`가 아니거나 타일을 다 열지 못했으면 `status: "revise"`와 사유를 적는다. 글꼴이 대체 글꼴로 그려졌다면 그 사실도 적는다. (f) `runs/<job_id>/audit-review.json`을 Write로 쓴다. `input_sha256`·`preview_sha256`·`reviewed_at`·`mode`는 `context.json`의 `copy_into_review_record` 값을 그대로 옮긴다(직접 계산하지 않는다). (g) `audit_report.py`를 `--input runs/<job_id>/draft/report-input.json --preview runs/<job_id>/draft/report.html --review runs/<job_id>/audit-review.json --output runs/<job_id>/review/delivery-audit.json`으로 실행한다. (h) 결정이 `pass`일 때만 `render_report.py --final --input runs/<job_id>/draft/report-input.json --preview runs/<job_id>/draft/report.html --audit-review runs/<job_id>/audit-review.json --output-dir runs/<job_id>/final`을 실행한다. 결정이 `revise`이면 `final`을 만들지 않고 끝낸다. (i) 일어나지 않은 열람·대조·화면 확인을 통과로 적지 않는다. 서버가 세션 출력에서 연 파일을 직접 확인하며, 연 적 없는 타일을 `pass` 근거로 적으면 최종본이 되지 않는다.

규칙 4의 명령 형식·`mkdir`/`cd`/절대 경로 금지는 두 세션에 동일하게 적용된다. 경로는 모두 `runs/<job_id>/…` 상대 경로다. 이 지침 개정으로 `harness-instructions.md` 해시가 바뀌므로 매니페스트를 재생성하고(`python -m backend.services.goose_harness`) 서버를 재시작해 설치본을 갱신한다.

## 8. 진행 단계 (프론트)

`GooseStage`에 `screenshot`, `review`를 더하고 `GOOSE_STAGES`를 `dart_prefetch, goose_start, plan, research_tick, fetch_start, fetch_done, compose, render_draft, audit, session_end, screenshot, review, render_final`(13개)로 바꾼다. `render_final`은 이제 감수 세션의 `--final` 실행으로만 발생하므로 `session_end`(1차 세션 종료) 뒤에 둔다. 서버는 감수 세션 스트림에서 `render_report.py`·`--final`을 보면 `render_final`을 내고, 감수 세션의 다른 도구 호출은 진행 이벤트로 내보내지 않는다(1차 세션의 `audit`·`render_draft` 등과 섞이지 않게). 라벨: `screenshot` → `화면 캡처`, `review` → `감수`. 갱신 대상: `gooseJob.test.ts:49-52`(“단계 11개” → 13개와 새 순서), `ProgressPanel.test.tsx:31`(P18).

## 9. 보안 분석

| 위협 | 대응 |
|---|---|
| 보고서 HTML(외부 자료 기반)이 브라우저에서 코드를 실행하거나 외부로 요청 | 스크립트 비활성, 외부 네트워크 차단, `file://`만. 초안에는 `<script>`가 0개(P16)라 기능 손실 없음 |
| 보고서 내용이 브라우저 인자·파일 이름으로 흘러듦 | 인자는 고정 문자열 + 서버 검증 URL·포트·임시 폴더. 파일 이름은 서버 생성(`desktop-NN.png`) |
| 심볼릭 링크로 작업 폴더 밖 파일을 열게 함 | `draft/report.html`이 심볼릭 링크이거나 resolve 결과가 작업 폴더 밖이면 거부 |
| 감수 세션이 영수증·최종 검증 파일을 위조 | 영수증은 서버가 세션 종료 후 덮어쓰며 `select_report`가 영수증과 현재 초안 해시를 다시 대조 |
| 감수 세션이 초안·입력을 변조 | 시작·종료 해시 비교 → 미인정(REQ-AIR6-014) |
| 감수 세션이 권한을 넓힘 | 설정 파일 불변, 무결성 재검사(T3·REQ-AIR6-001) |
| 감수 프롬프트로 외부 문자열 주입 | 종목명 미포함(T10), 코드·작업 ID는 기존 형식 검사 재사용 |
| 브라우저가 남아 자원 점유 | 프로세스 그룹 종료, 임시 프로필 삭제, 시간 예산 |

## 10. 테스트 이중화 지점

- 가짜 `BrowserDriver`: 호출 인자(뷰포트·모바일 여부·스크립트 비활성 호출·URL·타일 구간)를 기록하고 결정적 PNG 바이트와 지표를 돌려준다.
- 가짜 브라우저 실행 파일: 테스트 임시 폴더의 셸 스크립트(`AI_REPORT_GOOSE_BROWSER`로 지정)로 argv를 파일에 남기고 오래 잔다 — 인자 검증·프로세스 그룹 종료 시험용. 네트워크 연결 없음.
- 가짜 `claude`: `claude_bin` 인자로 임시 스크립트를 주고 합성 `stream-json`을 출력하게 한다(열람 집계·시간 초과·그룹 종료 시험).
- 가짜 `screenshotter`/`reviewer`: 작업 서비스 단위 시험에서 호출 순서·인자·`asyncio.Event` 대기를 기록한다.
- 모든 테스트 파일 이름은 `test_goose_` 접두어라 공용 네트워크 가드가 자동 적용된다(005, `conftest.py:20`).
