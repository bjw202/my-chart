# SPEC-AI-REPORT-006 sync 감사 보고서 (sync-auditor)

- 대상: SPEC-AI-REPORT-006 v0.3.4 (goose 후처리 감수), 브랜치 `WT-goose-review-pass`, HEAD `4042f6a`, 기준 `7abdcac`
- 감사 방식: 독립 감사자(evaluator 프로파일 `default`, 평면 가중 모드, 임계값 0.80). 구현자·오케스트레이터 자기 보고는 증거로 쓰지 않고 직접 재실행한 출력만 근거로 삼았다.
- 격리: 모든 pytest/python은 `AI_REPORT_GOOSE_HARNESS_DIR=.moai/state/verify/t18-audit-final/h`, `-B -p no:cacheprovider`. `~/.goose-harness`는 건드리지 않았다(`CLAUDE.md` 수정 시각 `Oct 21 21:36:04 2026`이 감사 전·후 동일). 추적 파일은 이 보고서 외에 바꾸지 않았고 커밋·푸시도 하지 않았다.

## 쉬운 말 요약

서버가 초안 화면을 찍고 별도 감수 세션이 그 화면을 보는 기능이 SPEC대로 만들어졌는지 다시 확인했다. 결론은 합격(PASS-WITH-DEBT, 종합 0.85)이다. 격리 환경에서 goose 테스트 565개가 통과했고(직접 실행), 네 핵심 모듈의 줄 커버리지는 96%였으며, 두 개의 높은 보안 결함(초안이 로컬 파일을 그리는 문제, 초안이 바깥으로 요청을 보내는 문제)이 실제 브라우저로 닫혀 있음을 제가 만든 추가 우회 시도 10가지까지 포함해 확인했다. 라이브 게이트(020150 실행) 증거 JSON도 AC-018이 요구한 항목과 맞았다. 부족한 점은 대부분 문서와 절차다. 특히 라이브 통과는 보안 강화(M7) 이전 빌드에서 관측됐고, 강화 뒤 재관측과 임시 완화 해제는 기록이 없는데도 SPEC 상태는 이미 `completed`다. 이 점은 문서에 한 줄로 밝혀야 한다.

## 종합

| 차원 | 가중 | 점수(0~1) | 판정 |
|---|---|---|---|
| Functionality | 40% | 0.88 | PASS |
| Security | 25% | 0.82 | PASS |
| Craft | 20% | 0.88 | PASS |
| Consistency | 15% | 0.80 | PASS |
| **종합(가중 평균)** | | **0.853** | **PASS-WITH-DEBT** |
| 참고: 조화평균(skill 기준) | | 0.844 | PASS |

Must-pass 방화벽(Functionality, Security): 둘 다 임계값을 독립적으로 넘었다. Critical/High 보안 결함은 없다(Security 루브릭 0.75~1.00 사이: Medium 1건이 문서화된 완화와 함께 열려 있음). 차단(blocking) 결함 0건, 선택(optional) 결함 아래 표.

## 직접 실행한 기계 검증 (verbatim)

| 차원 | 명령 | 출력 |
|---|---|---|
| Functionality | `pytest backend/tests -k goose -q -p no:cacheprovider` (격리) | `565 passed, 4 skipped, 214 deselected, 1 warning in 32.53s` |
| Functionality | 실제 브라우저 R1·R2·R3 (`AI_REPORT_GOOSE_REAL_BROWSER_TESTS=1 … test_goose_screenshot_live.py -v`) | `3 passed, 1 skipped, 1 warning in 3.66s`; 실행 뒤 `pgrep -fl chrome-headless-shell` 출력 없음 |
| Functionality | 매니페스트 재생성 `python -B -m backend.services.goose_harness` 뒤 `diff regen.json goose-manifest.json` | `MANIFEST_SAME` (`CLAUDE.md` 항목 `e5c3fd9b…d6e6` = `shasum -a 256 harness-instructions.md`) |
| Security | `shasum -a 256 backend/goose_harness_src/claude-settings.json` | `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3` (기준선과 동일) |
| Security | `git diff --stat 7abdcac HEAD -- backend/goose_harness_src/skills …/claude-settings.json` | 출력 없음(변경 0) |
| Security | 추가 우회 10종(`probe_extra.py`, 아래 §보안) | 마젠타 화소 전부 0, 바깥 접속 없음 |
| Craft | `coverage run --include=<4개 모듈> -m pytest … -k goose` + `coverage report` | `goose_job_service.py 372 16 96%`, `goose_review.py 294 15 95%`, `goose_runner.py 361 8 98%`, `goose_screenshot.py 305 13 96%`, `TOTAL 1332 52 96%` |
| Craft | `python3 -m ruff check <변경 9파일> --no-cache` | `All checks passed!` |
| Consistency | `grep -nE '^[0-9]+\. ' harness-instructions.md` | 규칙 번호 `1 2 3 4 5 6 7 8 9 10` 순서대로 하나씩 |
| Consistency | `git diff --stat bc56cc7 HEAD -- backend frontend pyproject.toml` | 출력 없음(보안 재검토 대상 코드 = 현재 HEAD 코드) |

## Functionality — REQ-1..20 / AC-1..22 매핑

범례: 코드 위치 / 테스트 수(`air6_NNN` 태그 이름 수, 직접 집계) / 관측 증거. "주장만"은 관측 기록이 없는 항목.

| AC | REQ | 코드 | 테스트 | 관측 증거 | 판정 |
|---|---|---|---|---|---|
| 001 | 001 | `goose_job_service.py:360-409` | 7 | 565 통과, 순서 `integrity,runner,integrity,screenshot,review`를 AC가 단언 | PASS |
| 002 | 002 | `goose_screenshot.py:520-524`, `goose_job_service.py:402-404` | 4 | 모듈·서비스·`run_review` 각각 시험 | PASS |
| 003 | 003 | `goose_job_service.py:385,393,418`, `frontend/src/utils/gooseJob.ts:55-69` | 4(+프론트) | 단계 목록이 SPEC 순서와 일치(직접 읽음) | PASS (프론트 vitest는 재실행하지 않음) |
| 004 | 004 | `goose_job_service.py:372-374` | 1 | 변이 (b) 독립 변이 불가로 미관측(progress 176에 공개) | PASS-공개 Gap |
| 005 | 005 | `goose_job_service.py:386-409` | 2 | fail-open 두 겹 변이 관측(progress 177) | PASS |
| 006 | 006 | `goose_screenshot.py:378-461` | 5 | 라이브 JSON: 데스크톱 13·모바일 19타일 | PASS |
| 007 | 007 | `goose_screenshot.py:353-527` | 6 | 라이브 index 키·`+09:00`·`preview_sha256` 일치(직접 대조) | PASS |
| 008 | 008 | `goose_screenshot.py:43-49,401,410,469,515` | 7 | 일치 | PASS |
| 009 | 009 | `goose_screenshot.py:56-66,165-231,320-339` | 16(+live 4) | 직접 재실행 R1·R2·R3 통과, 우회 10종, 변이 RED | PASS |
| 010 | 010 | `goose_screenshot.py:285-308` | 4 | 일치 | PASS |
| 011 | 011 | `goose_runner.py:135-172,627-658` | 6 | 일치 | PASS |
| 012 | 012 | `goose_review.py:173-216` | 3 | 라이브에서 감수 기록이 컨텍스트 값 해시를 정확히 복사(`AUDIT_INPUT_VERSION` 부재) | PASS |
| 013 | 013 | `harness-instructions.md:16,33-44`, 매니페스트 | 14 | 매니페스트 재생성 동일, 설정 sha 불변, 스킬 diff 0, 번호 1..10 | PASS (#5는 M7 지침본 재시작 뒤 무결성 미관측, 공개됨) |
| 014 | 014 | `goose_review.py:134-216,240-268` | 19 | 변이 RED 직접 관측(아래) | PASS (15번 기대 목록은 SPEC 문구 후속으로 공개) |
| 015 | 015 | `goose_review.py:433-452,482-530`, `goose_runner.py:565-612` | 17 | 일치 | PASS |
| 016 | 016 | `goose_review.py:290-410`, `goose_runner.py:198-221` | 18 | 조건 순서·읽기 보호 코드와 SPEC 문구를 줄 단위로 대조해 일치 | PASS |
| 017 | 017 | `conftest.py`(+4줄) | 태그 없음(횡단) | (1)(2)(3)은 직접 확인. **(4) 가드 되돌림 관측 기록 없음** | **PASS-주장만(F2)** |
| 018 | 018 | 라이브 | — | 증거 JSON 직접 대조(아래 §라이브) | PASS (M7 이전 빌드, F1) |
| 019 | 020 | M1 스파이크 | — | progress 24-59: 본문 토큰 2개 정확 인용, 6/6 `Read` 짝, 타일 해시 상이 | PASS (기록만, 재실행 불가) |
| 020 | 019 | `goose_job_service.py:316-324,458-466` | 6 | (c) 변이 미관측 공개 | PASS-공개 Gap |
| 021 | 013,016 | `goose_review.py:34,389-391` | 4 | 조건 17 제거 변이 직접 RED | PASS |
| 022 | 016,019 | 실제 `audit_report.py`·`render_report.py` 통합 | 2 | 날짜 재작성 대신 `historical` 모드로 신선도 분리(progress 182에 공개) | PASS-방식 변경 공개 |

REQ 20개는 위 AC와 1:1로 덮인다(REQ-020 ↔ AC-019, REQ-019 ↔ AC-020).

### 라이브 AC-018 증거 직접 대조 (`.moai/reports/t18/run-evidence/live-m6/`)

`check_live.py` 출력:

```
complete 2026-10-21T21:20:13+09:00 2026-10-21T21:20:16+09:00 {'name': 'HeadlessChrome', 'version': '153.0.8010.12', 'path_kind': 'playwright_cache'} 96f62e0c9d8f
desktop ok {... 'scroll_width': 1280, 'client_width': 1280, 'scroll_height': 19369, 'horizontal_overflow': False} 13
mobile ok {... 'scroll_width': 390, 'client_width': 390, 'scroll_height': 29600, 'horizontal_overflow': False} 19
tile sha vs receipt snapshot mismatches: [] snapshot files 33
expected<=read True ['visual_not_pass'] False
no_review codes ['AUDIT_INPUT_VERSION','AUDIT_MODE','AUDIT_PREVIEW_VERSION','AUDIT_TIME','REVIEW_CALCULATIONS','REVIEW_COVERAGE','REVIEW_OPINION','REVIEW_SOURCE_ACCURACY','REVIEW_VISUAL']
with_review codes ['REVIEW_SOURCE_ACCURACY','REVIEW_VISUAL','UNRESOLVED_ISSUE'] revise
{'source_accuracy': ('revise', 829), 'calculations': ('pass', 509), 'coverage': ('pass', 395), 'opinion': ('pass', 303), 'visual': ('revise', 624)} True
revise True True
```

- 항목 1 `job.json status: done, delivery_status: draft`, 이벤트 마지막 `done … delivery_status: draft`(`lead-events.sse`): 일치.
- 항목 2: 32타일, 영수증 시작 스냅샷의 33개 파일 해시(타일 32 + 색인)가 색인 타일 해시와 전부 같다. PNG 자체는 증거에 없어 리드의 "파일 존재" 주장은 이 간접 대조로만 확인.
- 항목 3: `tiles_expected` 32 ⊆ `tiles_read`, `exit_code` 0, `draft_unchanged` true, `judged_writes` [], 스냅샷 시작=종료.
- 항목 4: 형식 코드 4개와 교집합 공집합, 5개 검사 모두 존재·증거 비어 있지 않음, `visual.evidence`가 `[렌더 차이]`로 시작, 대조군(`--review` 없음)에서 형식 코드 4개가 다시 나타남.
- 항목 5: `visual_admissible false`와 `reasons ['visual_not_pass']`가 일관, `final/` 없음, 전달 `draft`.
- 감수 세션이 "정직한 revise"로 진짜 결함 2건(근거 미보관 수치, 390px 모바일 차트 잘림)을 기록한 것도 설계 의도대로다.

## Security

- **S1/S2 닫힘(직접 재확인)**: 실제 브라우저 R1(`file://` iframe/object/embed/data 중첩, 마젠타 화소 0, 초안 자체는 그려짐)·R2(루프백 수신 소켓 0건)·R3(정상 보고서 타일 형태가 격리 전 모듈과 같음) 통과. 이어서 SPEC·보안 재검토 목록에 없는 변형을 따로 돌렸다(`probe_extra.py`): `<link rel=stylesheet href=file://…css>`, CSS `@import file://`, `<img>`/SVG `<image>`/CSS `background:url()`의 `file://` png, `srcdoc` 중첩 iframe의 `file://`, `<base href=file://…/>` 뒤 상대 경로 `<img>`, `<meta refresh 0;url=view-source:file://…>`, `<meta refresh 0;url=chrome://version>`. 모두 마젠타 화소 0, 캡처 `complete`. `<meta refresh 0;url=file://…>`는 캡처가 `failed`(예산 `budget_exceeded`)로 끝나 타일이 하나도 남지 않는다(닫힌 쪽, F4).
- **변이 독립 관측**(타일은 건드리지 않고 모듈 텍스트만 바꿔 sys.modules에 올리는 플러그인 `mutplug.py`로 실행. 추적 파일 무수정): ① `tile_not_read` 조건 제거 → 7건 RED(`test_air6_016_isolated_pre_session_cases[c]`, `…[c2]`, `…014_13…` 등). ② `judged_input_write_attempt` 조건 제거 → 6건 RED. ③ `font_note_missing` 조건 제거 → 4건 RED. ④ 세션 전 `_empty_review` 호출 제거 → 7건 RED. ⑤ 요청 핸들러가 모든 URL을 `continue` → `air6_009_3_handler_contract…` 1건 RED. 다섯 변이 모두 RED이고 progress의 되돌림 관측 주장과 일치한다.
- **fail-closed `evaluate_admissibility`**: 예외를 삼켜 `(False, ["receipt_invalid"])`로 닫고(`goose_review.py:405-407`), 영수증 없음·깨짐·스키마 불일치·색인 읽기 불가·`audit-review.json` 깨짐은 해당 보호 조건 사유만 내는 것을 코드 읽기로 확인했다. 저장된 `visual_admissible`은 입력으로 쓰이지 않는다(`goose_review.py:527-529`는 출력).
- **규칙 7**: 서버는 `Read` 호출과 성공한 `tool_result` 쌍으로만 타일 열람을 인정하고(`goose_runner.py:578-597`), 영수증은 서버가 직접 쓰며 세션이 쓴 같은 이름 파일을 먼저 지운다(`goose_review.py:433-440`). 서버가 일으키지 않은 "통과"는 기록되지 않는다.
- **이월 항목(F1·F2·F3·F4·F5·F6·S4·S6~S8) 문서화 평가**: SPEC `spec.md:182-188`, `progress.md:454-485`, CHANGELOG `알려진 한계`가 근거 등급(검증됨/가설/미관측)을 붙여 대부분 정직하게 적었다. 부족한 부분: S4(Bash 허용 접두어+리다이렉트 쓰기)가 CHANGELOG·README에 한 줄도 없다(F7). F1의 "미관측 가설"은 악용 쪽에만 해당하고 권한 사실(`WebSearch`·`WebFetch`·`Agent`·`Skill` 허용)은 설정 파일로 이미 확인된 사실이다. 읽는 사람이 오해하지 않을 정도로는 쓰여 있다.

## Craft

- 테스트는 대부분 의미가 있다. 가짜 DevTools 전송으로 명령 순서·응답 방식을 단언하고(`test_air6_009_3_handler_contract…`), 판정 표는 `reasons` 목록 전체를 순서까지 단언하며, 실제 `audit_report.py`·`render_report.py`를 거치는 AC-022가 있다. 공허 단언(`assert True`, 무조건 skip)은 없다.
- 되돌림 RED 증거는 실재한다: 산출물에 `mutations*.out`이 있고 내가 임의로 고른 5개 변이도 모두 RED였다.
- 약점: ① AC-017 (4)(가드가 실제 DevTools 연결을 RED로 잡는지 되돌림 관측)는 기록이 없는데 M4 표가 PASS로 적었다(F2). ② `test_goose_harness.py:632`의 스킬 불변 시험은 기준 커밋 `9c763cb`가 없으면 조용히 건너뛴다(스쿼시 병합 뒤 공허해짐, F6). ③ 한 파일의 `@MX:ANCHOR`가 상한을 넘었다(F5).
- `ruff` 통과. `ruff format --check`는 기존 파일 때문에 적용하지 않았다고 공개됨.

## Consistency

- 코드·SPEC·지침·매니페스트 정합: 조건 1~17 순서, 읽기 보호 규칙, 사유 코드, REQ-009의 `Fetch` 허용 목록/CSP/플래그/환경 허용 목록이 SPEC 문구와 줄 단위로 일치한다. 지침 규칙 7 개정·규칙 4 "최종본:" 줄·규칙 10(10-1~10-11)과 매니페스트도 일치한다.
- `spec.md` frontmatter `status: completed`, `version 0.3.4`가 HISTORY와 일치. 나머지 5개 문서는 frontmatter가 없다(정상). 상태 전이는 draft → completed 한 번에 합쳐진 점이 `progress.md:432`에 공개돼 있다.
- 문서 대 코드 불일치는 모두 사소하다(F7).

## 결함 목록

심각도는 추정, 확신도는 괄호. `blocking`은 정확성 또는 SPEC이 명시한 요구에 영향이 있는 것만이다. 차단 결함은 없다.

| ID | 심각도 | 구분 | 위치 | 내용 | 필요한 수정 |
|---|---|---|---|---|---|
| F1 | 중간 (높음) | optional(부채, 공개 필요) | `progress.md:407`, `plan.md:83`, `CHANGELOG.md:19` | AC-018 통과는 M7 이전 빌드(main `2713402`, 지침 `64ceebda`)에서 관측됐다. M7은 캡처 경로(문서 CSP 서빙·요청 가로채기·`review/` 비우기)를 바꿨다. plan §5의 병합 뒤 필수 사후 검증 (2) 재관측과 (3) 임시 완화 `AI_REPORT_GOOSE_REVIEW=0` 해제 기록이 없다. 현재 `~/.goose-harness/CLAUDE.md`는 `64ceebda…`이고 저장소 지침은 `e5c3fd9b…`라 M7 지침은 아직 설치되지 않았다. 그런데 `spec.md`는 `completed`이고 CHANGELOG는 "라이브 게이트 1회차 통과"만 적었다. 완화 효과: M7 R3가 같은 라이브 초안에서 타일 수(13/19)를 기준선과 같게 재현했다 | `progress.md §E.4`와 CHANGELOG `알려진 한계`에 "AC-018은 M7 이전 빌드에서 관측, 재관측과 완화 해제는 대기"를 명시하거나 재관측 결과를 기록 |
| F2 | 낮음 (높음) | optional | `acceptance.md:332`, `progress.md:183` | AC-017 (4)(새 후처리 경로가 실제 DevTools 연결을 시도하면 `network attempt in goose test`로 실패하는지의 되돌림)이 관측 기록 없이 M4 표에서 PASS | 되돌림 한 번을 관측해 기록하거나 §E.2에 Gap으로 적기 |
| F3 | 낮음 (낮음, 가설) | optional | `goose_review.py:527-530`, `goose_job_service.py:395-408` | `finish_review`가 영수증 쓰기(`_write_receipt_file`) 이전에 OSError가 아닌 예외를 내면 `receipt_done=True` 때문에 대체 영수증이 쓰이지 않고, 세션이 위조해 둔 `review/receipt.json`이 디스크에 남아 `select_report`가 읽는다. 그런 예외 경로는 찾지 못했다 | `finish_review` 첫머리에서 세션이 쓴 `receipt.json`을 먼저 제거하거나 예외 시에도 실패 영수증 덮어쓰기 |
| F4 | 낮음 (높음) | optional | `goose_screenshot.py:233-248`(적재 대기), `CHANGELOG.md:20 (i)` | `<meta refresh 0;url=file://…>`가 있는 초안은 캡처가 60초 예산을 다 쓰고 `failed`로 끝난다(직접 관측, 브라우저 정리는 정상). 보안 재검토 F5에는 있으나 CHANGELOG (i)에는 없다. 닫힌 쪽 실패 | CHANGELOG (i)에 한 구절 추가 |
| F5 | 낮음 (높음) | optional | `goose_job_service.py:240,330,351,479` | 한 파일에 `@MX:ANCHOR` 4개, `mx.yaml:239`의 `anchor_per_file: 3` 초과 | 가장 호출 수가 적은 한 개를 NOTE로 강등 |
| F6 | 낮음 (높음) | optional | `test_goose_harness.py:632` | 스킬 불변 시험이 기준 커밋 `9c763cb` 부재 시 건너뛴다(스쿼시 병합 뒤 공허). 매니페스트 해시 시험이 일부를 보완 | 기준을 `7abdcac`로 바꾸거나 건너뜀 대신 매니페스트 해시로 고정 |
| F7 | 낮음 (높음) | optional | `CHANGELOG.md:16`, `README.md:231`(규칙 10~11 표기), `README.md:230`("수치 불일치"), `README.md:187,202`("약 3~6분"), `plan.md:3`("상태: draft"), CHANGELOG 한계 목록 | ① 규칙은 1~10뿐이고 10-11은 하위 항목이다. ② 라이브 감수 기록은 "근거 미보관 수치(대조 불가)"를 지적했지 불일치가 아니다. ③ 라이브 전체가 10분 7초였는데 소요 시간 표기가 그대로다. ④ plan.md 본문 상태가 draft로 남음(`progress.md:433`에 공개된 Gap). ⑤ S4·S6 이월이 CHANGELOG·README에 없다 | 문구 정정 |
| F8 | 정보 | optional | `progress.md:283-284` | 작업 시간 "21:12:09~21:22:16 (10분 7초)"와 `job.json finished_at 21:22:10`이 6초 차이(원인은 기록 안 됨; 훅/보관 시간으로 추정) | 출처 표기 |
| F9 | 정보 | optional | `progress.md:426,438` | `sync_commit_sha: pending-backfill`, `sync_auditor_score: pending`, 커밋 뒤 `moai spec lint` 재측정 미기록. 이 보고서가 점수를 채워 넣을 대상 | 이 보고서 반영 후 채우기 |

## 확인하지 못한 것

- 실제 `claude -p` 감수 세션의 동작(프롬프트 주입, 규칙 10-11 효과, `WebFetch` 유출, S4 리다이렉트 쓰기). 설정 파일 읽기와 증거 JSON만 봤다.
- 라이브 서버의 현재 실행 중 코드와 `AI_REPORT_GOOSE_REVIEW=0` 완화 여부, 서버 재시작 뒤 설치본 무결성(M7 지침 기준). `~/.goose-harness`는 읽기 전용으로 해시만 봤다.
- 라이브 타일 PNG 존재와 해시(증거에 PNG 없음. 영수증 스냅샷과의 일치로 간접 확인만).
- 감수가 지적한 390px 차트 잘림이 진짜 렌더러 결함인지(렌더 결과를 직접 보지 않음).
- 프론트 vitest·tsc·eslint 재실행, `moai spec lint`(CLI가 cwd에 상태 파일을 쓸 수 있어 실행하지 않음).
- M1 스파이크(AC-019) 재현(원본 스크립트와 캐너리 PNG는 증거에 없음, `progress.md`의 기록만).
- 다른 Chrome 빌드·Linux, 부하 상태의 대상 연결 경합, 하드링크·TOCTOU(F2/F3 보안 재검토 항목) 재현.
- 외부 모델 교차 감수(`audit_model` 설정 없음 → Claude 단독 감사).

## 권고

1. F1을 문서에서 해소한다(재관측 기록 또는 "대기" 명시). 이 감사의 PASS는 그 한 줄이 들어간다는 조건과 함께 유효하다.
2. F2 되돌림 한 번 관측, F5 MX 강등, F7 문구 정정은 후속 커밋에서 처리해도 되고, 누르지 않아도 PASS는 유지된다.
3. 후속 카드 후보(범위 밖, 기록용): `--disallowedTools`로 감수 세션 권한 좁히기(F1/S3), `--remote-debugging-pipe`(F4 보안 재검토), 하드링크·TOCTOU 단일 fd(F2/F3 보안 재검토).
