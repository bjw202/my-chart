# SPEC-AI-REPORT-006 — 구현 계획

상태: draft · 버전 0.3.2 · Tier L · 개발 방식은 `quality.yaml`의 `development_mode: tdd`(관측: `grep -n development_mode .moai/config/sections/quality.yaml` → `17:    development_mode: tdd`). 근거와 프로브는 `research.md`, 구조·스키마는 `design.md`, 요구사항은 `spec.md §4`, 인수 기준은 `acceptance.md`.

## 1. 접근 요약

goose 1차 세션이 초안을 만들고 끝나면, 작업 서비스의 백그라운드 태스크(`_run`)가 이어서 (1) 하네스 무결성 재검사, (2) 서버 화면 캡처, (3) 별도 `claude -p` 감수 세션, (4) 서버가 쓰는 영수증을 차례로 실행한다. 감수 세션은 `review/context.json`과 `screens/` 이미지를 읽고 `audit-review.json`을 쓰며 감사기를 다시 돌린다. 전달 상태 판정(`select_report`)은 영수증이 화면 확인을 인정할 때만 `final`을 낸다.

```
_run(job) [잠금 밖, active 유지]
  ├─ (기존) runner(goose 1차) → done + draft/report.html
  ├─ 후처리 [주입됨 && AI_REPORT_GOOSE_REVIEW != 0 && draft 존재]
  │    ├─ 무결성 재검사 ── 실패 → 영수증 integrity_failed, 후처리 중단
  │    ├─ emit screenshot → capture(draft) → screens/ + index.json   (실패해도 계속)
  │    ├─ 세션 전 스냅샷(초안·입력·screens) + review/context.json 쓰기
  │    ├─ emit review → run_review(claude -p, 감수 세션) → audit-review.json, [final/]
  │    └─ 종료 스냅샷 + 영수증 쓰기(세션 종료 후, 서버가 직접)
  └─ (기존) 종료 훅 → select_report(단일 판정 함수) → archive → 전달 상태 확정(훅 값, 없으면 재계산) → _finish(done)
```

## 2. 기술 결정 (변경 가능성이 큰 것부터)

| ID | 결정 | 이유 |
|---|---|---|
| T1 | 두 결함을 하나의 후처리로 푼다 — 1차 세션은 그대로, 뒤에 캡처+감수를 붙인다 | 화면 캡처는 초안이 있어야 가능하므로 같은 세션 안에서 이미지를 줄 수 없다. 감수만 1차 세션 안에서 하게 하면 결함 1은 풀리지만 결함 2를 위해 어차피 두 번째 단계가 필요해진다. 감수를 두 번째 단계에 합치면 구조가 하나다(research §3-1) |
| T2 | 감수는 새 `claude -p` 세션(`separate_review_pass`). 서브에이전트(`independent_agent`)는 쓰지 않는다 | 새 세션은 초안을 쓴 대화의 기억이 없어 별도 감수라는 말이 사실이다. 서브에이전트는 1차 세션 대화에 묶여 이미지 전달이 안 된다. 감수 방식 선언의 진위는 감사기도 증명하지 못하므로 사실인 쪽을 고른다 |
| T3 | `claude-settings.json`·벤더링 스킬·감사 스크립트는 바이트 불변, 바뀌는 하네스 파일은 `harness-instructions.md`(+매니페스트)뿐 | 감수 세션이 필요한 권한(`Read(./**)`, `Write(./runs/**)`, 렌더·감사 Bash)은 이미 허용돼 있다(P6). 권한을 넓히지 않으니 005 D2의 "권한 불변" 안전 속성이 그대로 유지된다. 벤더링 파일을 고치면 재벤더링 때 사라진다 |
| T4 | 감수 세션은 판단 대상을 고치지 않는 읽기 중심 세션 — 수정·재감수 루프는 범위 밖(D4) | 초안이 바뀌면 화면 이미지와 미리보기 해시가 낡아져 캡처부터 다시 해야 한다. 루프는 별도 설계가 필요한 후속 작업이다. 다만 권한 파일을 바꾸지 않으므로(T3) 세션은 `Write(./runs/**)`로 판단 대상도 쓸 수 있다 — 막는 수단은 권한이 아니라 탐지(T13)다 |
| T5 | 서버가 `review/context.json`에 해시·시각·모드를 미리 적는다 | 감수 세션은 해시를 계산할 수단이 없다(P6). 옮겨 적기 오류는 `AUDIT_INPUT_VERSION`·`AUDIT_PREVIEW_VERSION`으로 감사기가 잡지만(P2 D·E) 서버가 적어 주면 그 실패 경로 자체가 줄어든다 |
| T6 | 최종본 인정은 서버가 세션 종료 후 쓰는 영수증으로 한다. `select_report`가 영수증 없이는 `final`을 내지 않는다 | 세션은 `runs/` 아래에 무엇이든 쓸 수 있어(P6) `render-validation.json`의 `delivery_allowed`도 영수증 파일도 꾸밀 수 있다. 세션이 끝난 뒤 서버가 쓰는 파일만 세션이 위조할 수 없다. 단, 영수증은 "화면 이미지를 열었다"를 증명할 뿐 판단의 옳음을 증명하지 않는다(범위 밖 명시) |
| T7 | fail-open + 끄기 스위치 `AI_REPORT_GOOSE_REVIEW=0` | 후처리가 실패해도 1차 세션이 만든 초안은 지금처럼 전달돼야 한다. 스위치는 배포 직후 문제가 생길 때 현재 동작으로 즉시 되돌리는 수단이다. 스위치의 소유자는 작업 서비스(005 T와 같은 위치) |
| T8 | 브라우저는 호스트의 헤드리스 셸을 DevTools 프로토콜(`websockets`)로 구동하고 타일은 `clip`으로 자른다. Playwright·Pillow는 쓰지 않는다 | Playwright는 이 환경에 없다(P11). 명령행 `--screenshot`은 전체 높이를 모르고 넘침 수치를 못 얻는다(P13). DevTools 프로토콜은 전체 높이·넘침·전체 캡처를 모두 얻었고(P14) `websockets`는 이미 설치돼 있다. 새 설치 의존성이 없다 |
| T9 | **운영자 결정 2026-10-21 (미결정 확인 요청 2건 해소).** (1) 지원 브라우저는 Playwright 캐시의 `chrome-headless-shell`뿐이다. 탐색 순서는 `AI_REPORT_GOOSE_BROWSER`(있으면 우선, 실행 불가면 폴백 없이 `unavailable`) → Playwright 캐시의 최고 빌드 번호. `Google Chrome.app`은 범위 밖이며 `PATH` 탐색도 하지 않는다. README 지원 목록에는 M1에서 구동이 확인된 것만 적는다. (2) 캡처 중 외부 네트워크를 전부 차단한다. 글꼴 호스트(Pretendard·Google Fonts)도 허용하지 않는다. 감수 지침은 `visual` 증거를 표지 `[렌더 차이]`로 시작해 "렌더링이 실제 화면과 조금 다르다"를 적게 하고, 서버가 그 표지를 확인한다(판정 조건 17) | 운영자가 명시한 값을 조용히 다른 브라우저로 바꾸면 "무엇으로 찍었는지"를 잃는다. 전면 차단은 결정적이고 외부 접속 경로를 만들지 않는다. 대가: 글꼴이 대체돼 모바일 높이가 30683 → 30803 px로 달라진다(P14·P27, 같은 초안) |
| T10 | 감수 프롬프트에는 종목명을 넣지 않는다 | 종목명은 외부 입력이 흐르는 자유 문자열이고(1차 프롬프트는 이미 사용 중) 감수 세션은 코드와 작업 ID만으로 충분하다. 주입 표면을 줄인다 |
| T11 | 1차 세션 프롬프트·`build_prompt`·1차 argv는 바꾸지 않는다. 1차 세션이 `--final`을 하지 않게 하는 것은 하네스 규칙 7 개정으로 한다 | 실행기의 1차 경로를 건드리지 않아 회귀 범위를 줄인다. 1차 세션이 규칙을 어겨 `final/`을 만들어도 영수증 확인(T6)이 `draft`로 내린다 |
| T12 | 영수증 확인 위치는 `select_report` 안 | 호출처가 `run_goose`·`archive_job` 둘이고 `@MX:ANCHOR`로 표시된 단일 규칙이다(P9). 두 곳이 같은 판정을 쓰게 하려면 규칙 정의 안에 두는 것이 가장 단순하다. 기존 "final이 있으면 final" 테스트는 영수증 픽스처를 더하도록 갱신한다(범위는 M4가 기준선 델타로 측정). **단일 함수 호출은 T13이 정의한다** |
| T13 | 최종본 인정은 단일 순수 함수 `evaluate_admissibility`가 디스크 현재 상태 + 영수증의 서버 기록 사실로 매번 다시 계산한다. 영수증의 판정 불리언은 입력이 아니다. 세션 전 스냅샷·종료 후 대조·`Write`/`Edit` 호출 기록으로 판단 대상 변조를 탐지한다 | 감수 세션은 `Write(./runs/**)` 권한으로(P6) `screens/index.json`·타일도 고칠 수 있고, 권한 파일은 바꾸지 않기로 했다(T3). 저장된 불리언을 믿으면 영수증 작성 뒤 변조를 못 잡고, 조건 목록이 두 곳(요구사항·설계)에 갈라지면 AC가 한쪽만 시험한다(plan-audit D2·D3) |
| T14 | 작업 완료 이벤트·`job.json`의 전달 상태는 영수증을 쓴 뒤 확정한다: 종료 훅이 값을 돌려주면 그 값, 아니면(`None`·훅 없음) `select_report`를 다시 계산한 값. 후처리가 돌지 않은 작업은 실행기 값 그대로 | 실행기는 1차 세션 직후 영수증이 없는 상태로 계산하므로 후처리가 돈 작업에서는 항상 `draft`다. 그대로 쓰면 최종본이 인정돼도 이벤트가 `draft`를 알린다(plan-audit D8, `goose_job_service.py:270`) |

## 3. 마일스톤 (실행 순서 = 의존 순서, 서열 = 변경 가능성이 큰 결정부터 검증)

| 마일스톤 | 우선순위 | 산출 | 선행 | 핵심 검증 |
|---|---|---|---|---|
| M1 스파이크·픽스처 (GO/NO-GO) | High | 브라우저 실구동 기록(G3·G4·G8·G9), 캐너리 타일 실험(AC-019 — M1 전용 스파이크 스크립트로 찍으며 M2 캡처 모듈에 의존하지 않는다), 라이브 초안에서 뽑은 합성·녹화 HTML 픽스처, 기존 초안 4개의 높이·타일 분포 재측정(P26)과 타일 상한 확정, 스키마(§design 4) 값 확정 | 없음 | **GO = AC-AIR6-019 통과(REQ-AIR6-020): 두 뷰포트의 본문 크기 토큰 인용 + 모든 캐너리 타일의 `Read` 짝 + `y > 0` 타일 `clip` 확인.** 타일 상한·`Read` 시간이 부족하면 GO/NO-GO는 그대로 두고 조정 후 진행(상한·시간 상한을 올려 manager-spec 재위임으로 반영한 뒤에만 M2 병합). NO-GO면 M2~M6 코드를 병합하지 않고 `progress.md`에 관측을 적은 뒤 SPEC을 계획 단계로 되돌린다(manager-spec 재위임 + 운영자 결정, "화면 확인"의 의미가 바뀔 수 있음). 나머지 Gap은 관측값을 `progress.md`에 기록하고 값이 다르면 코드 작성 전에 manager-spec 재위임으로 반영 |
| M2 캡처 모듈 | High | `goose_screenshot.py` + `test_goose_screenshot.py` (AC-006~010) | M1 | 가짜 브라우저 드라이버로 타일·색인·한도·격리·탐색, 되돌림 RED |
| M3 감수 세션·영수증 | High | `goose_runner.run_review`·`build_review_prompt`·열람·쓰기 시도 기록 수집, `goose_review.py`(컨텍스트·스냅샷·영수증·`evaluate_admissibility`), `test_goose_review.py` (AC-011·012·014·015·021) | M2 | 가짜 `claude` 스크립트, 합성 스트림 픽스처로 열람·쓰기 집계, 되돌림 RED |
| M4 작업 서비스 연결·최종본 인정·프론트 | High | `goose_job_service` 후처리·이벤트·스위치·취소·fail-open·전달 상태 재계산, `select_report`가 판정 함수 호출(+기존 테스트 갱신), 프론트 단계, 격리 통합 시험 (AC-001~005·016·020·022) | M3 | 순서·취소·fail-open·인정 표(AC-016) 전부 되돌림 RED, 프론트 단위 테스트. AC-022를 만들 수 없으면 Gap으로 `progress.md`에 기록 |
| M5 하네스 지침·매니페스트·문서 | Medium | `harness-instructions.md` 규칙 7 개정·규칙 9, 매니페스트 재생성, `pyproject.toml`, README·`.env.example` (AC-013) | M4 | 매니페스트 = 재생성, 설정·스킬 불변, 서버 재시작 후 무결성 통과 |
| M6 라이브 관측 게이트 | High | 020150 라이브 실행 ≤2회와 판정표 (AC-018), 시간·토큰 실측(G5). 라이브 실행은 `LATEST_SEARCH_NAVER`가 남아 `final`에 도달하지 못한다(카드 t19 소관) — 최종본 인정 경로는 AC-022가 대신 확인 | M5 | `progress.md §E.2`에 명령·출력 원문. 미충족이면 SPEC을 닫지 않는다 |

AC-AIR6-017(격리·회귀)은 횡단 기준이라 마일스톤에 한 번 배정하지 않는다. M2~M5 각 종료 때 `pytest backend/tests -k goose`로 확인하고 최종 판정은 M5 종료 시점에 한다(iter2 N10a).

실행 방식 제안: **serial**(마일스톤 순서 의존, 코딩 중심). Tier L 기준(마일스톤 ≥3, 파일 ≥10)에 해당하므로 `manager-lead` 대상이 될 수 있으나 병렬화 이점이 작아 마일스톤마다 보고하는 직렬 진행을 권한다. 쓰기 에이전트는 동시에 하나만 돌린다. 최종 선택은 plan→run 경계의 승인 게이트가 한다.

## 4. 위험과 대응

| 위험 | 가능성 | 대응 |
|---|---|---|
| 헤드리스 세션이 이미지를 읽지 못하거나 읽고도 내용을 인식하지 못한다(G1·G4) | 중 | M1 GO/NO-GO를 캐너리 토큰 인용으로 판정(AC-019). NO-GO면 설계 재검토(예: 이미지 대신 서버가 만든 텍스트 DOM 요약 — "화면 확인"의 의미가 바뀌므로 manager-spec 재위임과 운영자 결정 필요) |
| 감수 세션이 이미지를 열지 않고 pass를 선언 | 중 | 영수증이 `tiles_read`로 거른다 → `draft`(AC-016 `tile_not_read`). 실패해도 지금과 같은 결과다 |
| 감수 세션이 초안·입력·화면 색인·타일을 몰래 수정(`Write(./runs/**)` 권한) | 낮음 | 세션 전 스냅샷 대조 + `Write`/`Edit` 호출 기록으로 인정 거부(AC-014·016). 도구 밖 경로의 변경 후 복원은 증명 못함(Gap). 1차 세션이 미리 심은 `audit-review.json`·`final/`은 세션 시작 전에 삭제한다(AC-014 (11)~(13)) |
| 감수 세션이 `[렌더 차이]` 표지를 빠뜨려 정상 최종본이 `draft`가 된다 | 중 | 표지 누락은 조건 17 미충족, 전달 `draft`로 가는 설계된 안전 방향 결과이며 사유 `font_note_missing`이 남는다(규칙 7 불변식 위반 아님). 지침이 표지 문구를 고정한다(AC-013). 라이브에서는 모든 회차가 누락이면 AC-018 (나)군 불충족으로 게이트 실패, 일부 회차만 누락이면 빈도를 기록한다 |
| 타일 상한 30에서도 긴 보고서가 `too_tall`이 된다 | 낮음 | 상한은 관측된 최대(모바일 20타일)의 1.5배(P26). M1이 재측정해 조정. 타일 33~60장을 900초 안에 읽는 시간은 미측정(G5) — M6에서 실측 |
| 자정(KST)을 넘겨 후처리가 끝나면 감사기가 `FRESHNESS_CUTOFF`를 낸다(`audit_report.py:32-33`) | 낮음 | 게이팅 코드가 아니므로 기록만 한다(AC-018) |
| 후처리 시간으로 작업 전체가 길어짐 | 중 | 캡처 60초·감수 900초 상한, 끄기 스위치. 실측은 M6 |
| 새 테스트가 실제 브라우저·`claude`·네트워크를 건드림 | 중 | 가짜 드라이버 주입, 기존 네트워크 가드(005 AC-014)로 종료 시 0건 단언 |
| 기존 `final` 선택 테스트 대량 갱신 | 중 | M4가 영향 개수를 기준선 대비로 먼저 측정하고 `progress.md`에 기록 |
| 병합 순서 변경(리드 결정 2026-10-21): SPEC-AI-REPORT-007(카드 t19)이 먼저, 이 SPEC이 나중에 병합돼 겹치는 파일(`goose_job_service.py`·`harness-instructions.md`·`goose-manifest.json`·`test_goose_job_service.py`)에서 충돌한다 | 높음 | 이 SPEC이 나중 쪽이므로 007 `plan.md` §5 "필수 병합 단계" 4단계를 수행한다 — (1) 이 SPEC의 감수 규칙 9를 10으로 다시 매기고 하위 라벨·자기 참조도 바꾼다(007의 AC-AIR7-011 #4가 정상 교차 참조도 표시할 수 있다는 007 감사 부채 N9에 유의), (2) 규칙 9 번호를 쓰는 이 SPEC의 모든 산출물을 새 번호로 고친다 — acceptance.md(AC-013 #1과 잡는 구현 (a), AC-021 Then), design.md(§7의 `규칙 9 추가` 제목 줄과 규칙 본문의 `규칙 7·9`), spec.md(§3 변경 범위 표), plan.md(M5 행), research.md(G13의 `규칙 9 (h)`), 그리고 progress.md에 있다면 그 항목. 고친 뒤 `grep -n '규칙 9\|규칙 7·9\|rule 9' .moai/specs/SPEC-AI-REPORT-006/*.md`를 실행해 이 행의 설명을 뺀 옛 번호 잔존이 0임을 출력 원문으로 남긴다, (3) 매니페스트는 손으로 합치지 않고 재생성한다, (4) `_run` 순서와 진행 이벤트를 병합 트리에서 재확인한다. 단계별 관측 결과는 이 SPEC의 `progress.md`에 원문으로 남기고, 그 뒤에만 병합 완료로 본다. 007 문서는 수정하지 않는다. 007의 `plan.md §5`와 감사 부채 N9 인용은 이 워크트리에 007이 없어 확인하지 못했다(`ls .moai/specs \| grep 007` 출력 없음, 2026-10-21) — 병합 시점에 007의 커밋 id로 다시 인용한다 |
| 영수증 판정이 너무 엄격해 정상 최종본도 `draft`가 된다 | 중 | 조건 하나하나가 `reasons`로 남아 원인이 보인다. 미인정 사유는 로그와 영수증에 기록 |

## 5. 품질 게이트와 완료 정의

- 새 모듈(`goose_screenshot.py`, `goose_review.py`) 줄 커버리지 85% 이상. 측정은 `coverage run --source=backend -m pytest <파일>` → `coverage report`(lessons #9 커버리지 함정)
- `ruff check` 새 경고 0(기준선 대비). 005 기록에 ruff 미설치로 미실행이 있었으므로(005 progress G-M2-1) 실행 가능 여부를 M2에서 먼저 관측한다
- 모든 대조 항목은 되돌림 RED 관측 후에만 GREEN으로 기록(lessons #9). 관측하지 못한 대조는 `progress.md §E.2`에 Gap으로 남긴다
- `pytest backend/tests -k goose` 기준선 267 대비 실패 0(갱신하는 테스트는 목록으로 명시), 프론트 `npm --prefix frontend run test -- gooseJob ProgressPanel` 통과
- @MX: 캡처 모듈의 브라우저 프로세스 진입점과 `select_report`의 영수증 확인에 `@MX:ANCHOR`/`@MX:WARN`(+REASON), 주석 언어는 `code_comments: ko`
- 완료 정의는 `acceptance.md §F`
