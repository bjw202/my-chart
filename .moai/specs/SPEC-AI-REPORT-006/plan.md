# SPEC-AI-REPORT-006 — 구현 계획

상태: draft · 버전 0.1.0 · Tier L · 개발 방식은 `quality.yaml`의 `development_mode: tdd`(관측: `grep -n development_mode .moai/config/sections/quality.yaml` → `17:    development_mode: tdd`). 근거와 프로브는 `research.md`, 구조·스키마는 `design.md`, 요구사항은 `spec.md §4`, 인수 기준은 `acceptance.md`.

## 1. 접근 요약

goose 1차 세션이 초안을 만들고 끝나면, 작업 서비스의 백그라운드 태스크(`_run`)가 이어서 (1) 하네스 무결성 재검사, (2) 서버 화면 캡처, (3) 별도 `claude -p` 감수 세션, (4) 서버가 쓰는 영수증을 차례로 실행한다. 감수 세션은 `review/context.json`과 `screens/` 이미지를 읽고 `audit-review.json`을 쓰며 감사기를 다시 돌린다. 전달 상태 판정(`select_report`)은 영수증이 화면 확인을 인정할 때만 `final`을 낸다.

```
_run(job) [잠금 밖, active 유지]
  ├─ (기존) runner(goose 1차) → done + draft/report.html
  ├─ 후처리 [주입됨 && AI_REPORT_GOOSE_REVIEW != 0 && draft 존재]
  │    ├─ 무결성 재검사 ── 실패 → 영수증 integrity_failed, 후처리 중단
  │    ├─ emit screenshot → capture(draft) → screens/ + index.json   (실패해도 계속)
  │    ├─ review/context.json 쓰기
  │    ├─ emit review → run_review(claude -p, 감수 세션) → audit-review.json, [final/]
  │    └─ 영수증 쓰기(세션 종료 후, 서버가 직접)
  └─ (기존) 종료 훅 → select_report(영수증 확인 포함) → archive → _finish(done)
```

## 2. 기술 결정 (변경 가능성이 큰 것부터)

| ID | 결정 | 이유 |
|---|---|---|
| T1 | 두 결함을 하나의 후처리로 푼다 — 1차 세션은 그대로, 뒤에 캡처+감수를 붙인다 | 화면 캡처는 초안이 있어야 가능하므로 같은 세션 안에서 이미지를 줄 수 없다. 감수만 1차 세션 안에서 하게 하면 결함 1은 풀리지만 결함 2를 위해 어차피 두 번째 단계가 필요해진다. 감수를 두 번째 단계에 합치면 구조가 하나다(research §3-1) |
| T2 | 감수는 새 `claude -p` 세션(`separate_review_pass`). 서브에이전트(`independent_agent`)는 쓰지 않는다 | 새 세션은 초안을 쓴 대화의 기억이 없어 별도 감수라는 말이 사실이다. 서브에이전트는 1차 세션 대화에 묶여 이미지 전달이 안 된다. 감수 방식 선언의 진위는 감사기도 증명하지 못하므로 사실인 쪽을 고른다 |
| T3 | `claude-settings.json`·벤더링 스킬·감사 스크립트는 바이트 불변, 바뀌는 하네스 파일은 `harness-instructions.md`(+매니페스트)뿐 | 감수 세션이 필요한 권한(`Read(./**)`, `Write(./runs/**)`, 렌더·감사 Bash)은 이미 허용돼 있다(P6). 권한을 넓히지 않으니 005 D2의 "권한 불변" 안전 속성이 그대로 유지된다. 벤더링 파일을 고치면 재벤더링 때 사라진다 |
| T4 | 감수 세션은 읽기 전용 — 수정·재감수 루프는 범위 밖(D4) | 초안이 바뀌면 화면 이미지와 미리보기 해시가 낡아져 캡처부터 다시 해야 한다. 루프는 별도 설계가 필요한 후속 작업이다. 읽기 전용으로 두면 영수증의 해시 비교(REQ-AIR6-014)가 단순해진다 |
| T5 | 서버가 `review/context.json`에 해시·시각·모드를 미리 적는다 | 감수 세션은 해시를 계산할 수단이 없다(P6). 옮겨 적기 오류는 `AUDIT_INPUT_VERSION`·`AUDIT_PREVIEW_VERSION`으로 감사기가 잡지만(P2 D·E) 서버가 적어 주면 그 실패 경로 자체가 줄어든다 |
| T6 | 최종본 인정은 서버가 세션 종료 후 쓰는 영수증으로 한다. `select_report`가 영수증 없이는 `final`을 내지 않는다 | 세션은 `runs/` 아래에 무엇이든 쓸 수 있어(P6) `render-validation.json`의 `delivery_allowed`도 영수증 파일도 꾸밀 수 있다. 세션이 끝난 뒤 서버가 쓰는 파일만 세션이 위조할 수 없다. 단, 영수증은 "화면 이미지를 열었다"를 증명할 뿐 판단의 옳음을 증명하지 않는다(범위 밖 명시) |
| T7 | fail-open + 끄기 스위치 `AI_REPORT_GOOSE_REVIEW=0` | 후처리가 실패해도 1차 세션이 만든 초안은 지금처럼 전달돼야 한다. 스위치는 배포 직후 문제가 생길 때 현재 동작으로 즉시 되돌리는 수단이다. 스위치의 소유자는 작업 서비스(005 T와 같은 위치) |
| T8 | 브라우저는 호스트의 헤드리스 Chrome 계열을 DevTools 프로토콜(`websockets`)로 구동하고 타일은 `clip`으로 자른다. Playwright·Pillow는 쓰지 않는다 | Playwright는 이 환경에 없다(P11). 명령행 `--screenshot`은 전체 높이를 모르고 넘침 수치를 못 얻는다(P13). DevTools 프로토콜은 전체 높이·넘침·전체 캡처를 모두 얻었고(P14) `websockets`는 이미 설치돼 있다. 새 설치 의존성이 없다 |
| T9 | 브라우저 탐색은 환경 변수 → `PATH` 이름 → 알려진 설치 위치 순. 환경 변수가 잘못되면 폴백 없이 `unavailable` | 운영자가 명시한 값을 조용히 다른 브라우저로 바꾸면 "무엇으로 찍었는지"를 잃는다. 이 호스트의 후보는 P12 |
| T10 | 감수 프롬프트에는 종목명을 넣지 않는다 | 종목명은 외부 입력이 흐르는 자유 문자열이고(1차 프롬프트는 이미 사용 중) 감수 세션은 코드와 작업 ID만으로 충분하다. 주입 표면을 줄인다 |
| T11 | 1차 세션 프롬프트·`build_prompt`·1차 argv는 바꾸지 않는다. 1차 세션이 `--final`을 하지 않게 하는 것은 하네스 규칙 7 개정으로 한다 | 실행기의 1차 경로를 건드리지 않아 회귀 범위를 줄인다. 1차 세션이 규칙을 어겨 `final/`을 만들어도 영수증 확인(T6)이 `draft`로 내린다 |
| T12 | 영수증 확인 위치는 `select_report` 안 | 호출처가 `run_goose`·`archive_job` 둘이고 `@MX:ANCHOR`로 표시된 단일 규칙이다(P9). 두 곳이 같은 판정을 쓰게 하려면 규칙 정의 안에 두는 것이 가장 단순하다. 기존 "final이 있으면 final" 테스트는 영수증 픽스처를 더하도록 갱신한다(범위는 M4가 기준선 델타로 측정) |

### [NEEDS CLARIFICATION]

- [NEEDS CLARIFICATION: 서버 호스트에서 지원할 브라우저를 정해 달라 — 현재 후보는 Playwright 캐시의 `chrome-headless-shell`(관측: 버전 153.0.8010.12, 동작 확인)과 `Google Chrome.app`(존재만 확인, 구동 미관측). 기본값: 환경 변수 `AI_REPORT_GOOSE_BROWSER` → 알려진 위치 순 탐색, 지원 브라우저는 M1에서 구동이 확인된 것만 README에 적는다.]
- [NEEDS CLARIFICATION: 캡처 시 외부 네트워크를 완전히 차단해 웹 글꼴(Pretendard·Google Fonts) 없이 대체 글꼴로 그릴지, 두 글꼴 호스트만 허용할지. 기본값: 완전 차단(안전·결정적), 실제 사용자 화면과 글자 모양이 조금 다를 수 있음을 감수 지침이 증거에 적게 한다. 두 호스트만 허용하면 화면이 실제에 가깝지만 외부 접속 허용 경로가 하나 생긴다.]

## 3. 마일스톤 (실행 순서 = 의존 순서, 서열 = 변경 가능성이 큰 결정부터 검증)

| 마일스톤 | 우선순위 | 산출 | 선행 | 핵심 검증 |
|---|---|---|---|---|
| M1 스파이크·픽스처 (GO/NO-GO) | High | 브라우저 실구동 기록(G2·G3·G4·G8·G9), 라이브 초안에서 뽑은 합성·녹화 HTML 픽스처, **실제 `claude -p`가 하네스에서 PNG를 `Read`하는지와 스트림 모양(G1)**, 스키마(§design 4) 값 확정 | 없음 | G1이 NO-GO면 중단하고 manager-spec에 되돌려 보낸다. 나머지 Gap은 관측값으로 `progress.md`에 기록하고 값이 다르면 코드 작성 전에 manager-spec 재위임으로 반영 |
| M2 캡처 모듈 | High | `goose_screenshot.py` + `test_goose_screenshot.py` (AC-006~010) | M1 | 가짜 브라우저 드라이버로 타일·색인·한도·격리·탐색, 되돌림 RED |
| M3 감수 세션·영수증 | High | `goose_runner.run_review`·`build_review_prompt`·열람 기록 수집, `goose_review.py`(컨텍스트·영수증·인정 판정), `test_goose_review.py` (AC-011·012·014·015) | M2 | 가짜 `claude` 스크립트, 합성 스트림 픽스처로 열람 집계, 되돌림 RED |
| M4 작업 서비스 연결·최종본 인정·프론트 | High | `goose_job_service` 후처리·이벤트·스위치·취소·fail-open, `select_report` 영수증 확인(+기존 테스트 갱신), 프론트 단계 (AC-001~005·016) | M3 | 순서·취소·fail-open·인정 표(AC-016) 전부 되돌림 RED, 프론트 단위 테스트 |
| M5 하네스 지침·매니페스트·문서 | Medium | `harness-instructions.md` 규칙 7 개정·규칙 9, 매니페스트 재생성, `pyproject.toml`, README·`.env.example` (AC-013) | M4 | 매니페스트 = 재생성, 설정·스킬 불변, 서버 재시작 후 무결성 통과 |
| M6 라이브 관측 게이트 | High | 020150 라이브 실행 ≤2회와 판정표 (AC-018), 시간·토큰 실측(G5) | M5 | `progress.md §E.2`에 명령·출력 원문. 미충족이면 SPEC을 닫지 않는다 |

실행 방식 제안: **serial**(마일스톤 순서 의존, 코딩 중심). Tier L 기준(마일스톤 ≥3, 파일 ≥10)에 해당하므로 `manager-lead` 대상이 될 수 있으나 병렬화 이점이 작아 마일스톤마다 보고하는 직렬 진행을 권한다. 쓰기 에이전트는 동시에 하나만 돌린다. 최종 선택은 plan→run 경계의 승인 게이트가 한다.

## 4. 위험과 대응

| 위험 | 가능성 | 대응 |
|---|---|---|
| 헤드리스 세션이 이미지를 읽지 못한다(G1) | 중 | M1 GO/NO-GO. NO-GO면 설계 재검토(예: 이미지 대신 서버가 만든 텍스트 DOM 요약 — 이 경우 "화면 확인"의 의미가 바뀌므로 manager-spec 재위임과 사용자 결정이 필요) |
| 감수 세션이 이미지를 열지 않고 pass를 선언 | 중 | 영수증이 `tiles_read`로 거른다 → `draft`(AC-016 c). 실패해도 지금과 같은 결과다 |
| 감수 세션이 초안·입력을 몰래 수정 | 낮음 | 해시 비교(AC-014)로 인정 거부 |
| 후처리 시간으로 작업 전체가 길어짐 | 중 | 캡처 60초·감수 900초 상한, 끄기 스위치. 실측은 M6 |
| 새 테스트가 실제 브라우저·`claude`·네트워크를 건드림 | 중 | 가짜 드라이버 주입, 기존 네트워크 가드(005 AC-014)로 종료 시 0건 단언 |
| 기존 `final` 선택 테스트 대량 갱신 | 중 | M4가 영향 개수를 기준선 대비로 먼저 측정하고 `progress.md`에 기록 |
| 영수증 판정이 너무 엄격해 정상 최종본도 `draft`가 된다 | 중 | 조건 하나하나가 `reasons`로 남아 원인이 보인다. 미인정 사유는 로그와 영수증에 기록 |

## 5. 품질 게이트와 완료 정의

- 새 모듈(`goose_screenshot.py`, `goose_review.py`) 줄 커버리지 85% 이상. 측정은 `coverage run --source=backend -m pytest <파일>` → `coverage report`(lessons #9 커버리지 함정)
- `ruff check` 새 경고 0(기준선 대비). 005 기록에 ruff 미설치로 미실행이 있었으므로(005 progress G-M2-1) 실행 가능 여부를 M2에서 먼저 관측한다
- 모든 대조 항목은 되돌림 RED 관측 후에만 GREEN으로 기록(lessons #9). 관측하지 못한 대조는 `progress.md §E.2`에 Gap으로 남긴다
- `pytest backend/tests -k goose` 기준선 267 대비 실패 0(갱신하는 테스트는 목록으로 명시), 프론트 `npm --prefix frontend run test -- gooseJob ProgressPanel` 통과
- @MX: 캡처 모듈의 브라우저 프로세스 진입점과 `select_report`의 영수증 확인에 `@MX:ANCHOR`/`@MX:WARN`(+REASON), 주석 언어는 `code_comments: ko`
- 완료 정의는 `acceptance.md §F`
