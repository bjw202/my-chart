# SPEC-AI-REPORT-006 — 설계

버전 0.3.1 · 요구사항 `spec.md §4`, 결정 `plan.md §2`, 프로브 `research.md`. 이 문서는 구현 세부(스키마·절차·경계)를 정한다. 코드 식별자는 run 단계에서 확정하며 여기서는 역할 이름으로 적는다.

## 1. 구성요소와 경계

| 구성요소 | 위치 | 책임 | 하지 않는 일 |
|---|---|---|---|
| 캡처 모듈 | `goose_screenshot.py` | 브라우저 탐색·실행·종료, 두 뷰포트 타일 저장, `screens/index.json` | 감수·영수증·전달 판정 |
| 감수 보조 모듈 | `goose_review.py` | `review/context.json` 작성, 세션 전 스냅샷, 열람·쓰기 시도 기록 집계, 영수증 작성, **단일 판정 함수 `evaluate_admissibility`**(영수증 작성기와 `select_report`가 함께 호출) | 프로세스 실행 |
| 실행기 | `goose_runner.py` | 감수 세션 `claude -p` 실행(`run_review`), 감수 프롬프트, 스트림에서 `Read`·`Write`·`Edit` 호출·결과 수집, `select_report`(판정 함수 호출) | 캡처, 영수증 쓰기 |
| 작업 서비스 | `goose_job_service.py` | 후처리 순서·진행 이벤트·스위치·취소·fail-open, 영수증 쓰기 호출, 영수증 뒤 전달 상태 재계산 | 판정 규칙 정의 |
| 하네스 지침 | `harness-instructions.md` | 1차·감수 세션 행동 규칙 | 서버 판정 |

주입 경계: 작업 서비스 생성자에 `screenshotter`, `reviewer`(둘 다 기본 없음)를 받는다. 운영 인스턴스에만 실제 구현을 붙인다(005의 `prefetcher`와 같은 패턴, P8). 캡처 모듈은 브라우저 구동을 `BrowserDriver` 인터페이스(뷰포트·URL·타일 구간을 받아 PNG 바이트와 지표를 돌려줌) 뒤에 둬서 테스트가 가짜를 꽂는다.

## 2. 후처리 순서와 실패 행렬

```
1차 세션 done + draft 존재
  → [스위치 0] 영수증 disabled, 끝
  → 무결성 재검사 ✗ → 영수증 integrity_failed, 끝 (작업은 러너 결과대로 종료)
  → emit screenshot → capture
        ✓ complete/partial    ✗ unavailable/failed/예외 (모두 index.json에 기록)
  → 세션 전 정리: 기존 audit-review.json과 final/ 삭제 (1차 세션이 심은 것 제거, REQ-AIR6-014)
        ✗ 삭제 실패 → 감수 세션을 시작하지 않고 review_failed로 간다
  → 세션 전 스냅샷(초안·입력·screens 색인·타일 해시, screens 상대 경로 집합) + review/context.json 쓰기
      (캡처 결과와 무관하게 쓴다; screens.outcome·render_note 포함)
  → emit review → run_review
        ✓ exit 0, audit-review.json 있음     ✗ 시작 실패/비정상 종료/시간 초과/기록 없음(`review_failed`)
  → (세션 프로세스 그룹 종료 확인)
  → 종료 스냅샷 + 영수증 쓰기 (세션이 쓴 같은 이름 파일을 먼저 제거한 뒤 임시 파일 + 원자적 교체로 쓴다)
  → 종료 훅(select_report 호출 → archive) → 전달 상태 확정(훅 값, 없거나 None이면 select_report 재계산) → _finish
```

| 실패 지점 | 작업 상태 | 전달 상태 | 영수증 outcome | 후속 |
|---|---|---|---|---|
| 스위치 0 | done | draft | `disabled` | 후처리 없음 |
| 무결성 재검사 실패 | 러너 결과대로 | draft | `integrity_failed` | 캡처·감수 없음 |
| 브라우저 없음/실패/시간 초과 | done | draft(감수 결과와 무관하게 `final`은 인정 못 함) | 감수가 돌았으면 `reviewed` + 사유 `screens_not_complete` | 감수는 계속 실행(`visual: revise` 사유 기록) |
| 감수 세션 시작 실패/비정상 종료/종료 코드 0이지만 `audit-review.json` 없음 | done | draft | `review_failed`(마지막 경우 reasons에 `no_audit_review`) | — |
| 세션 전 정리 실패(기존 `audit-review.json`·`final/` 삭제 불가) | done | draft | `review_failed` | 감수 세션 시작 안 함. 남은 파일이 있어도 `outcome`이 `reviewed`가 아니라 조건 3이 막는다 |
| 감수 세션 시간 초과 | done | draft | `timeout` | 프로세스 그룹 종료 |
| 취소 | cancelled | (훅이 초안 보관, 기존 규칙) | `cancelled`(best-effort) | 그룹 종료 |
| 영수증 쓰기 실패 | done | draft. 서버는 쓰기 전에 기존 파일(세션이 쓴 것일 수 있음)을 먼저 제거하고 임시 파일 + 원자적 교체로 쓰므로, 쓰기가 실패해도 세션이 쓴 영수증이 남지 않는다(= final 불가). 제거마저 실패해 파일이 남으면 완료 이벤트의 전달 상태를 `draft`로 확정한다(보관 단계의 재판정은 Gap G14) | — | 제거 재시도, `receipt_write_failed` 로그 |

## 3. 화면 캡처

### 3.1 브라우저 실행

- 인자(고정 문자열 + 서버 값만): `--headless`(헤드리스 셸은 기본), `--disable-gpu`, `--hide-scrollbars`, `--remote-debugging-port=<서버가 고른 루프백 빈 포트>`, `--user-data-dir=<서버가 만든 임시 폴더>`, 시작 URL `about:blank`. 네트워크는 **전부** 차단한다(글꼴 호스트 예외 없음, 운영자 결정 2026-10-21). 방식은 DevTools `Network.setBlockedURLs ["*"]`이며 `file://` 로드를 막지 않음이 관측됐다(P28, 감사자 관측). 허용 호스트 목록은 존재하지 않는다. `--no-sandbox`는 이 호스트에서 필요 없었다(P28, 다른 호스트는 미관측 G9).
- 브라우저 탐색: `AI_REPORT_GOOSE_BROWSER`(있으면 우선, 실행 불가면 폴백 없이 `unavailable`) → 고정된 Playwright 캐시 루트 목록(macOS `~/Library/Caches/ms-playwright`, Linux `~/.cache/ms-playwright`; Linux는 미관측)의 `chromium_headless_shell-<빌드번호>/…/chrome-headless-shell` 중 빌드 번호가 가장 큰 것. `PATH`·`Google Chrome.app`은 탐색하지 않는다. `path_kind`는 `env` | `playwright_cache` | `none`.
- 새 프로세스 그룹(`start_new_session=True`)으로 띄우고 종료·취소·시간 초과 때 그룹 전체를 종료한다(실행기의 `terminate_group` 패턴 재사용 가능). 임시 프로필 폴더는 `finally`에서 지운다.
- 접속: `http://127.0.0.1:<port>/json/list`에서 `page` 타입의 `webSocketDebuggerUrl`을 얻어 `websockets`로 연결(P14 관측: 시작 후 0.29초에 응답).

### 3.2 캡처 절차 (뷰포트마다)

1. `Emulation.setDeviceMetricsOverride`: 데스크톱 `1280×800, mobile=false`, 모바일 `390×844, mobile=true`, `deviceScaleFactor=1`.
2. `Emulation.setScriptExecutionDisabled(true)`(G3 확인 대상), 네트워크 차단 적용.
3. `Page.navigate(file://<resolved draft/report.html>)` 후 `Page.loadEventFired` 대기(예산 안에서). P14는 고정 3초 대기를 썼고 이벤트 대기는 M1이 확정한다.
4. `Runtime.evaluate`로 `document.documentElement`의 `scrollWidth`·`clientWidth`·`scrollHeight`를 읽는다. `horizontal_overflow = scrollWidth > clientWidth`.
5. `scrollHeight`를 1568px 단위로 나눠 타일 구간 `[y, y+h)`를 만든다(마지막 타일은 나머지). 개수가 30(`TILE_CAP`, REQ-AIR6-008)을 넘으면 그 뷰포트는 `too_tall`로 기록하고 타일을 만들지 않는다.
6. 타일마다 `Page.captureScreenshot{format:png, captureBeyondViewport:true, clip:{x:0,y,width,height,scale:1}}`(P14는 y=0 전체 높이만 관측, y>0 타일은 G3). 8 MiB 초과 타일은 그 뷰포트를 `error`로 기록한다.
7. 파일은 `screens/<viewport>-NN.png`로 쓰고 SHA-256·바이트 길이를 계산한다. 어떤 뷰포트가 실패해도 다른 뷰포트는 계속한다(`partial`).

전체 예산 60초는 브라우저 시작부터 정리까지의 벽시계 시간이며 초과하면 남은 구간을 `skipped`로 기록하고 그룹을 종료한다.

## 4. 스키마 (고정 키 집합)

### 4.1 `screens/index.json`

- 최상위: `schema_version`(1), `source`(`"draft/report.html"`), `preview_sha256`, `started_at`, `finished_at`, `outcome`, `browser`, `viewports`
- `browser`: `name`, `version`, `path_kind`(`env` | `playwright_cache` | `none`). 브라우저 절대 경로는 적지 않는다(로그에만)
- `viewports[]`: `name`(`desktop` | `mobile`), `width`, `status`(`ok` | `error` | `too_tall` | `skipped`), `error`, `metrics`(`scroll_width`, `client_width`, `scroll_height`, `horizontal_overflow`), `tiles`
- `tiles[]`: `file`, `y`, `width`, `height`, `bytes`, `sha256`
- `outcome`: `complete`(두 뷰포트 `ok`) | `partial`(하나만 `ok`) | `unavailable`(브라우저 없음) | `failed`(둘 다 실패) | `disabled`
- 시각은 시간대 포함 ISO-8601, 오프셋 `+09:00`

### 4.2 `review/context.json` (서버가 감수 세션 시작 전에 씀)

- 최상위: `schema_version`(1), `job_id`, `code`, `now`, `input`(`path`, `sha256`), `preview`(`path`, `sha256`), `screens`(`index_path`, `outcome`, `tiles`: 읽어야 할 파일 상대 경로 목록, `render_note`: "외부 네트워크와 웹 글꼴을 막고 그려 실제 화면과 조금 다르다"는 고정 문장), `audit_review_path`, `audit_output_path`, `final_dir`, `copy_into_review_record`(`input_sha256`, `preview_sha256`, `reviewed_at`, `mode`)
- `input.path` = `runs/<job_id>/draft/report-input.json`(P4: 입력 원본과 바이트 동일), `preview.path` = `runs/<job_id>/draft/report.html`
- `copy_into_review_record.reviewed_at` = `now`(감수 세션 시작 시각이며 감사기 요건 `cutoff ≤ reviewed_at ≤ 감사 시각`을 만족, P1 `:98-99`), `mode` = `"separate_review_pass"`
- 경로는 모두 하네스 기준 상대 경로(`runs/…`) — 하네스 규칙 4의 `..`·절대 경로 금지와 맞춘다

### 4.3 `review/receipt.json` (서버가 세션 종료 후 씀)

- 최상위: `schema_version`(1), `outcome`, `started_at`, `finished_at`, `process`(`exit_code`, `timed_out`), `hashes`(`input_start`, `input_end`, `preview_start`, `preview_end`), `draft_unchanged`, `screens`(`outcome`, `index_sha256`, `tiles_expected`, `tiles_read`, `snapshot_start`, `snapshot_end`), `judged_writes`, `audit_review`(`present`, `sha256`, `mode`, `visual_status`, `input_sha256`, `preview_sha256`, `reviewed_at`), `visual_admissible`, `reasons`
- `screens.snapshot_start`·`snapshot_end`: `{index_sha256, files: {<screens/ 기준 상대 경로>: <sha256>}}`. `screens/` 아래를 하위 폴더까지 재귀로 훑어 모든 파일을 상대 경로(예: `mobile-01.png`, `sub/a.png`)로 적는다. 세션 시작 전(context.json을 쓰는 같은 단계)과 종료 뒤에 서버가 측정한다. 파일 집합은 `files`의 키 집합이다
- `judged_writes`: 스트림에서 본 `Write`/`Edit` 호출 중 대상이 이 작업의 `draft/` 또는 `screens/`로 풀리는 경로 목록(정규화된 상대 경로)
- `outcome`: `reviewed` | `review_failed` | `timeout` | `cancelled` | `integrity_failed` | `disabled`
- `reasons`: 판정 함수가 계산한 미인정 사유 코드 목록(진단용 — 판정의 입력이 아니다). 코드 집합과 순서는 §5의 17개 + `final_not_allowed`
- 필수 키 집합은 `receipt_invalid` 판정(§5 조건 2)이 쓴다

## 5. 최종본 인정 판정 (단일 함수)

`evaluate_admissibility(job_dir) -> (admissible, reasons)`는 `goose_review.py`의 순수 함수이며 **영수증 작성기와 `select_report`가 같은 조건 코어를 실행한다**(REQ-AIR6-016, plan-audit D3). 호출 형태는 둘이다(iter3 N12): 조건 코어는 영수증 사실을 **인자**로 받고, 디스크 래퍼 `evaluate_admissibility(job_dir)`는 `review/receipt.json`을 디스크에서 읽어 코어를 부른다(파일이 없으면 "없음", JSON 객체로 파싱되지 않으면 "파싱 불가"로 코어에 넘겨 조건 1·2가 각각 판정한다). 영수증 작성기는 영수증이 아직 디스크에 없으므로 방금 측정한 사실을 인자로 코어를 부른 뒤 영수증을 **한 번만** 원자적으로 쓴다(두 번 쓰지 않는다 — 두 번째 쓰기는 두 번째 실패 지점이다). 이때 진단용 키 `visual_admissible`·`reasons`는 입력이 아니므로 자리표시 값으로 넘긴다. `select_report`와 재평가는 래퍼를 부른다. 함수는 아래 표의 조건 1~17을 구현한다. 조건 0(`final_not_allowed`)은 `select_report`가 먼저 평가하고, 통과하면 이 함수를 부른다. 영수증 작성기는 1~17만 평가한다(iter2 N7). 함수는 예외를 던지지 않으며 읽을 수 없는 입력은 미충족으로 본다. 입력은 (가) 디스크의 현재 파일들, (나) 영수증에 서버가 쓴 사실 필드(`outcome`, `tiles_read`, `snapshot_start`·`snapshot_end`, `hashes`, `judged_writes`)이다. 영수증의 `visual_admissible`·`reasons` 필드는 진단용 출력이며 입력으로 읽지 않는다 — 읽으면 영수증 작성 뒤 디스크가 바뀌어도 `true`가 남는다.

평가 순서(고정, 모든 미충족을 모으고 첫 항목을 로그):

| # | 사유 코드 | 조건 | 근거 REQ |
|---|---|---|---|
| 0 | `final_not_allowed` | `final/report.html` 정규 파일 + `final/render-validation.json`의 `delivery_allowed == true` (기존 조건, `select_report` 쪽) | 016 |
| 1 | `no_receipt` | `review/receipt.json` 존재 | 015·016 |
| 2 | `receipt_invalid` | (조건 1이 충족일 때만 평가) JSON 객체로 파싱, `schema_version == 1`, 고정 키 집합 모두 존재 | 015·016 |
| 3 | `review_not_completed` | `outcome == "reviewed"` | 005·016 |
| 4 | `judged_input_write_attempt` | `judged_writes`가 빈 목록 | 014 |
| 5 | `screens_not_complete` | 지금 읽은 `screens/index.json`이 파싱되고 `outcome == "complete"`(읽을 수 없으면 미충족) | 007 |
| 6 | `screens_changed` | 지금 측정한 screens 스냅샷(색인·타일 해시·파일 집합) == `snapshot_start` == `snapshot_end` | 014 (D2) |
| 7 | `tile_missing` | 색인에 적힌 타일 파일이 모두 정규 파일로 존재 | 016 |
| 8 | `tile_hash_mismatch` | 존재하는 각 타일의 현재 SHA-256 == 색인 값(없는 타일은 조건 7의 몫) | 007·016 |
| 9 | `draft_changed` | `draft/report.html`·`draft/report-input.json`의 현재 해시 == 영수증의 start == end | 014 |
| 10 | `preview_hash_mismatch` | 색인 `preview_sha256` == `audit-review.json`의 `preview_sha256` == 현재 `draft/report.html` 해시 | 016 |
| 11 | `tile_not_read` | 색인의 타일 목록(영수증 `tiles_expected`와 같아야 함) ⊆ `tiles_read` | 015 |
| 12 | `mobile_overflow` | 모바일 뷰포트 `horizontal_overflow == false` | 007 |
| 13 | `no_audit_review` | `audit-review.json` 존재·파싱 | 016 |
| 14 | `mode_not_separate_review_pass` | `mode == "separate_review_pass"` | 016 |
| 15 | `visual_not_pass` | `checks.visual.status == "pass"` | 016 |
| 16 | `reviewed_before_capture` | `reviewed_at >= index.finished_at` | 016 |
| 17 | `font_note_missing` | `checks.visual.evidence`에 표지 `[렌더 차이]` 포함 | 013·016 |

결과: 0~17이 모두 충족이면 `("final", final_dir)`, 아니면 `draft/report.html`이 정규 파일일 때 `("draft", draft_dir)`, draft도 없으면 `None`(기존 규칙). 영수증 작성기는 같은 함수를 1~17에 대해 호출해 `reasons`를 채운다(0은 `final/`이 생기기 전일 수 있어 작성 시점에는 평가하지 않는다).

**읽기 보호와 조건의 독립성 (iter2 N3).** 조건 대부분은 서로 다른 입력을 읽어 독립적으로 평가된다. 입력을 아예 읽지 못하는 경우만 보호 조건이 맡는다.

| 보호 조건 | 읽지 못하는 입력 | 평가·보고하지 않는 의존 조건 |
|---|---|---|
| 1·2 (영수증) | 영수증 파일 | 3, 4, 6, 9, 11 (영수증 사실에 의존). 2는 1이 충족일 때만 평가 |
| 5 (색인) | 색인이 파싱되지 않음 | 7, 8, 11, 12, 16과 10의 색인 쪽 (16은 색인의 `finished_at`을 읽는다) |
| 13 (감수 기록) | `audit-review.json` | 14, 15, 16, 17과 10의 감수 기록 쪽 |

의존 조건을 건너뛰는 것은 허용이 아니다 — 보호 조건의 사유가 보고되므로 `admissible == false`다. 이 규칙 덕분에 케이스당 사유 목록이 짧고 정확하며(예: 영수증이 없으면 `[no_receipt]`), 조건 1·13을 빼면 다른 조건이 같은 상황을 대신 막기 때문에 결과가 아니라 사유 목록만 바뀐다(수준 B). 나머지 조건은 격리 케이스에서 해당 검사를 빼면 결과가 `final`로 뒤집힌다(수준 A). 조건별 격리 케이스와 수준은 `acceptance.md` AC-016.

**표지 누락의 결과.** `[렌더 차이]` 표지가 없으면 조건 17이 미충족이라 영수증이 화면 확인을 인정하지 않고 전달은 `draft`다. 설계된 안전 방향 결과이며 규칙 7 불변식 위반이 아니다. 지침은 표지로 *시작*하라고 요구하지만 서버(조건 17)와 라이브 게이트는 *포함*만 확인한다.

**`final/` 출처 (iter2 N4, Gap G13).** 조건 0은 `final/report.html`과 `final/render-validation.json`의 `delivery_allowed`만 본다. 이 두 파일은 `render_report.py --final`이 쓰지만(research P33) 감수 세션도 `Write(./runs/**)`로 같은 이름 파일을 쓸 수 있다. 1~17은 화면 확인에 대한 조건이라, 지침을 어기고 `revise` 기록 뒤 `final/`을 손으로 쓰는 경우를 막지 못한다. 규칙 7(화면 확인 통과는 일어난 일일 때만)은 영향받지 않는다. 비용 대비 효과가 작아 Gap으로 두고 후속 후보를 research G13에 적는다.

**닫는 구멍.** 감수 세션은 `Write(./runs/**)`·`Edit(./runs/**)` 권한으로(P6) `screens/index.json`·타일도 고칠 수 있다. 세션 전 스냅샷(조건 6)과 `Write`/`Edit` 호출 기록(조건 4)이 이를 막고, 조건 7·8은 세션 시작 전에 이미 어긋난 파일(캡처 직후 변조)을 막는다. 잔여 위험: 도구가 아닌 경로(허용된 두 스크립트의 부작용)로 `screens/`가 바뀌었다가 복원되는 경우는 증명하지 못한다(Gaps).

세션이 영수증 이름의 파일을 써 두어도 서버가 종료 후 덮어쓴다(REQ-AIR6-015).

## 6. 열람 기록 수집

- 입력: 감수 세션의 `stream-json` 줄. 1차 세션과 같은 읽기 루프를 쓴다(`_read_stdout`)에 줄 구독자를 하나 더한다.
- 수집 규칙: `assistant` 줄의 `tool_use`(`name == "Read"`, `input.file_path`)를 `id`로 기억하고, 이후 `user` 줄의 `tool_result`(`tool_use_id` 일치)가 오류 표지(`is_error == true`)가 아닐 때만 "읽음"으로 센다. 서브에이전트(`parent_tool_use_id` 있음)의 읽기도 센다. 오류 표지는 `tool_result.is_error`이며 기존 스트림 픽스처에서 `true` 3건, `false` 4건, 키 없음 33건이 관측됐다(P10) — `false`와 키 없음은 모두 성공이고 `true`만 오류다.
- `Write`/`Edit` 호출(`tool_use`, `input.file_path`; 픽스처에서 `Write` 2건·`Edit` 1건 모두 `file_path` 키 관측)도 같은 규칙으로 경로를 정규화해, 이 작업의 `draft/`·`screens/` 아래로 풀리면 결과와 무관하게(시도만으로) `judged_writes`에 적는다. 쓰기 시도의 경로 비교는 대소문자를 구분하지 않는다: macOS 기본 파일시스템은 `/Users`와 `/users`를 같은 경로로 풀므로(research P32) `Screens/`처럼 대소문자만 바꾼 경로가 `os.path.normpath` 비교를 빠져나갈 수 있다(iter2 N10c). 읽기는 정확한 대소문자 경로만 읽음으로 센다 — 변형 경로 읽기를 세지 않으면 최악의 결과가 `tile_not_read`(`draft`)라 안전 방향이다.
- 경로 정규화: 절대 경로면 하네스 경로(`resolve_harness_dir()`) 아래여야 하고, 상대 경로면 하네스 기준으로 해석한 뒤 `os.path.normpath`한다. 결과가 정확히 `<harness>/runs/<이 작업 ID>/screens/<index.json에 적힌 타일 파일>` 중 하나일 때만 해당 타일로 센다. 기본 이름만 비교하거나 부분 문자열로 비교하지 않는다(다른 작업의 같은 이름 파일이 섞이지 않게).
- 메모리 상한: 기억하는 `tool_use`는 256개(기존 `_TOOL_MEMORY_LIMIT`과 같은 방식).

## 7. 하네스 지침 초안 (`harness-instructions.md`)

규칙 7 개정(1차 세션 대상):

> 7. 이 세션은 브라우저가 없으므로 화면 확인(visual) 검사를 통과로 기록하지 않는다. 이 세션은 `audit-review.json`을 쓰지 않고 `render_report.py --final`도 실행하지 않는다. 초안(`--output-dir runs/<job_id>/draft`)을 만들고 `audit_report.py`를 감수 기록 없이 한 번 실행한 뒤 끝낸다. 서버가 초안 뒤에 화면 캡처와 별도 감수 세션을 돌린다.

규칙 9 추가(프롬프트가 "감수 세션"이라고 밝힌 세션에만 적용):

> 9. 감수 세션 규칙. 이 세션은 초안을 쓴 세션이 아니다. 조사·작성을 다시 하지 않는다. (a) `runs/<job_id>/review/context.json`을 먼저 Read로 읽는다. (b) `fact-check/GUIDE.md`와 `references/delivery-audit.md`를 읽는다(규칙 7·9가 그 문서의 브라우저 관련 문장보다 우선한다). (c) `draft/`, `screens/`, 입력 JSON을 수정하지 않는다(서버가 세션 전후 해시와 `Write`/`Edit` 호출을 기록해 바뀌었으면 최종본을 만들지 않는다). 지적할 결함은 `audit-review.json`의 `issues`에 `status: "open"`으로 적는다. (d) 검사 5종(`source_accuracy`, `calculations`, `coverage`, `opinion`, `visual`)을 각각 실제 자료·수치·화면과 대조하고 `evidence`에 무엇을 어떻게 확인했는지 적는다. 대조에서 결함을 찾은 검사는 `status: "revise"`로 적고 `evidence`에 구체적 결함을, `issues`에 `open` 항목을 남긴다. 결함을 찾지 못한 검사만 `pass`로 적는다(정직한 `revise`는 허용되며 막히지 않는다). (e) `visual`은 `screens/index.json`의 모든 타일 파일을 Read로 하나씩 연 경우에만 `pass`로 적고, `evidence`에 연 타일 파일 이름들과 모바일 지표(`scroll_width`·`client_width`)를 적는다. 화면이 없거나 `index.json`의 `outcome`이 `complete`가 아니거나 타일을 다 열지 못했으면 `status: "revise"`와 사유를 적는다. `visual`의 `evidence`는 리터럴 표지 `[렌더 차이]`로 시작하고, 외부 네트워크와 웹 글꼴을 막고 그렸으므로 실제 화면과 조금 다르다는 사실(`context.json`의 `screens.render_note`)을 적는다. (f) `runs/<job_id>/audit-review.json`을 Write로 쓴다. `input_sha256`·`preview_sha256`·`reviewed_at`·`mode`는 `context.json`의 `copy_into_review_record` 값을 그대로 옮긴다(직접 계산하지 않는다). (g) `audit_report.py`를 `--input runs/<job_id>/draft/report-input.json --preview runs/<job_id>/draft/report.html --review runs/<job_id>/audit-review.json --output runs/<job_id>/review/delivery-audit.json`으로 실행한다. (h) 결정이 `pass`일 때만 `render_report.py --final --input runs/<job_id>/draft/report-input.json --preview runs/<job_id>/draft/report.html --audit-review runs/<job_id>/audit-review.json --output-dir runs/<job_id>/final`을 실행한다. 결정이 `revise`이면 `final`을 만들지 않고 끝낸다. (i) 일어나지 않은 열람·대조·화면 확인을 통과로 적지 않는다. 서버가 세션 출력에서 연 파일을 직접 확인하며, 연 적 없는 타일을 `pass` 근거로 적으면 최종본이 되지 않는다.

규칙 4의 명령 형식·`mkdir`/`cd`/절대 경로 금지는 두 세션에 동일하게 적용된다. 경로는 모두 `runs/<job_id>/…` 상대 경로다. 이 지침 개정으로 `harness-instructions.md` 해시가 바뀌므로 매니페스트를 재생성하고(`python -m backend.services.goose_harness`) 서버를 재시작해 설치본을 갱신한다.

## 8. 진행 단계 (프론트)

`GooseStage`에 `screenshot`, `review`를 더하고 `GOOSE_STAGES`를 `dart_prefetch, goose_start, plan, research_tick, fetch_start, fetch_done, compose, render_draft, audit, session_end, screenshot, review, render_final`(13개)로 바꾼다. `render_final`은 이제 감수 세션의 `--final` 실행으로만 발생하므로 `session_end`(1차 세션 종료) 뒤에 둔다. 서버는 감수 세션 스트림에서 `render_report.py`·`--final`을 보면 `render_final`을 내고, 감수 세션의 다른 도구 호출은 진행 이벤트로 내보내지 않는다(1차 세션의 `audit`·`render_draft` 등과 섞이지 않게). 라벨: `screenshot` → `화면 캡처`, `review` → `감수`. 갱신 대상: `gooseJob.test.ts:49-52`(“단계 11개” → 13개와 새 순서), `ProgressPanel.test.tsx:31`(P18).

## 9. 보안 분석

| 위협 | 대응 |
|---|---|
| 보고서 HTML(외부 자료 기반)이 브라우저에서 코드를 실행하거나 외부로 요청 | 스크립트 비활성, 외부 네트워크 **전면** 차단(예외 호스트 없음), `file://`만. 렌더러 소스에 `<script` 리터럴 0개, 관측한 초안 4개 모두 0개(P16·P29)라 기능 손실 없음(렌더러가 읽는 외부 템플릿 파일은 조사하지 않음 — 렌더러 디렉터리 전체에서 `<script` 리터럴 0개는 관측) |
| 보고서 내용이 브라우저 인자·파일 이름으로 흘러듦 | 인자는 고정 문자열 + 서버 검증 URL·포트·임시 폴더. 파일 이름은 서버 생성(`desktop-NN.png`) |
| 심볼릭 링크로 작업 폴더 밖 파일을 열게 함 | `draft/report.html`이 심볼릭 링크이거나 resolve 결과가 작업 폴더 밖이면 거부 |
| 감수 세션이 영수증·최종 검증 파일을 위조 | 영수증은 서버가 세션 종료 후 덮어쓰며 `select_report`는 저장된 불리언을 믿지 않고 §5 함수로 디스크를 다시 계산 |
| 감수 세션이 초안·입력·화면 색인·타일을 변조(`Write(./runs/**)` 권한, P6) | 세션 전 스냅샷과 종료 후 대조 + `Write`/`Edit` 호출 기록 → 미인정(REQ-AIR6-014, §5 조건 4·6) |
| 1차 세션이 `Write(./runs/**)`로 `audit-review.json`(`visual: pass`, 복사한 해시, 미래 `reviewed_at`)이나 `final/`을 미리 심고, 감수 세션이 덮어쓰지 않은 채 종료 코드 0으로 끝남(iter3 N13) | 서버가 감수 세션 시작 전에 기존 `audit-review.json`·`final/`을 삭제한다(REQ-AIR6-014). 삭제 실패면 세션을 시작하지 않는다. 삭제는 `screens/` 스냅샷보다 먼저이고 `review/context.json`을 쓰기 전이다. 심은 파일이 사라지므로 종료 코드 0인데 기록이 없으면 `review_failed`(조건 3·13) |
| 감수 세션이 권한을 넓힘 | 설정 파일 불변, 무결성 재검사(T3·REQ-AIR6-001) |
| 감수 프롬프트로 외부 문자열 주입 | 종목명 미포함(T10), 코드·작업 ID는 기존 형식 검사 재사용 |
| 브라우저가 남아 자원 점유 | 프로세스 그룹 종료, 임시 프로필 삭제, 시간 예산 |

## 10. 테스트 이중화 지점

- 가짜 `BrowserDriver`: 호출 인자(뷰포트·모바일 여부·스크립트 비활성 호출·URL·타일 구간)를 기록하고 결정적 PNG 바이트와 지표를 돌려준다.
- 가짜 브라우저 실행 파일: 테스트 임시 폴더의 셸 스크립트(`AI_REPORT_GOOSE_BROWSER`로 지정)로 argv를 파일에 남기고 오래 잔다 — 인자 검증·프로세스 그룹 종료 시험용. 네트워크 연결 없음.
- 가짜 `claude`: `claude_bin` 인자로 임시 스크립트를 주고 합성 `stream-json`을 출력하게 한다(열람 집계·시간 초과·그룹 종료 시험).
- 격리 통합 시험(AC-AIR6-022): 가짜 `claude` 스크립트가 `context.json`을 읽어 감수 기록을 쓰고 **벤더링된 실제** `audit_report.py`·`render_report.py --final`(`backend/goose_harness_src/skills/…`의 임시 복사본)을 돌린다. 입력은 검색 채널 규칙을 만족하는 합성 입력.
- 가짜 `screenshotter`/`reviewer`: 작업 서비스 단위 시험에서 호출 순서·인자·`asyncio.Event` 대기를 기록한다.
- 모든 테스트 파일 이름은 `test_goose_` 접두어라 공용 네트워크 가드가 자동 적용된다(005, `conftest.py:20`).
