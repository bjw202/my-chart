# SPEC-AI-REPORT-004 구현 계획 — Deep 모드를 goose 하네스로 교체

> 상태: **in-progress**(run 단계, M1 완료) · 버전 0.4.1 · 작성 2026-10-19 · 작성 manager-spec · Tier L(사용자 확정)
> 승인된 기획: `.moai/plans/ai-refactored-snowglobe.md`
> 관련 문서: `spec.md`(요구사항), `acceptance.md`(인수 기준), `design.md`(구조·보안 경계), `research.md`(조사), `spec-compact.md`(압축본)
> 감사 이력: plan-audit 1회차 FAIL 0.78 → v0.3.0 반영, 2회차 FAIL 0.90 → v0.3.1 반영, 3회차 FAIL 0.91 → 사용자 부채 수용 → v0.3.2 반영, 4회차(run 단계 Phase 1) PASS 0.93 → 선택 결함 일부를 M1 관측과 함께 v0.4.0에서 반영(§2.3, §2.4), 5회차(v0.4.0 delta) FAIL 0.83(점수 하락 → STOP, 단일 수정) → v0.4.1 반영(§2.4). 감사 결함 ID는 회차 접두어(`R1-`~`R5-`)를 붙여 결정 ID(D1~D10, T1~T11)와 구분한다.

---

## 1. 목표

차트 셀 AI 모달의 Deep 모드를 goose 스킬의 `company_report` 전체 리포트로 바꾼다. 실행은 전용 하네스 폴더에서 띄운 헤드리스 `claude -p`가 맡고, 작업이 HTTP 요청과 분리돼 모달을 닫거나 새로고침해도 이어진다. 결과는 goose가 만든 단일 HTML을 sandbox iframe으로 보여준다. Fast(codex) 모드는 그대로 둔다.

## 2. 확정 결정

### 2.1 승인 기획에서 고정된 결정

1. 범위: goose `company_report` 전체 리포트만. 유형 선택 UI 없음.
2. UI: `AiReportModal`의 Deep 자리를 Goose가 대체. Fast 유지.
3. 실행: 하네스 폴더 + `claude -p`, cwd = 하네스, `--setting-sources project`. Agent SDK 미사용. `bypassPermissions` 금지.
4. 요청과 분리된 작업: 시작 → `job_id`, SSE 재생·재접속, 취소, 인메모리 상태(단일 uvicorn).
5. 출력: `report.html`을 CSP `sandbox`로 서빙, sandbox iframe 표시, 기록 탭에 goose 실행 목록.
6. 기존 Deep 파이프라인과 Brave/Tavily/Naver/YouTube 키 의존 삭제.

### 2.2 사용자 결정 (2026-10-19, 계획 검토)

| ID | 질문 | 결정 | 반영 위치 |
|---|---|---|---|
| D7 | 최종 감사 미통과 초안의 표시 정책 | 초안을 sandbox iframe에 표시하고 “최종 감사 미통과 초안” 배너. 기록에는 `draft` | REQ-014, 017, 019 / AC-014, 017, 019 |
| D8 | 기존 markdown 리포트(61개)의 기록 탭 노출 | `kind: "markdown"`으로 계속 표시, `kind: "goose"`와 함께 나열 | REQ-017 / AC-017 |
| D9 | goose 기본 모델 | `AI_REPORT_GOOSE_MODEL` 기본값 `sonnet` | REQ-002 / AC-002 |
| D10 | goose 작업 전체 동시 실행 개수 | 서버 전체 1개. 다른 종목은 429, 같은 종목은 기존 `job_id` | REQ-008 / AC-007, 008 |

### 2.3 기술 결정 (plan-audit 1~3회차와 M1 관측 반영, manager-spec 권한)

| ID | 결정 | 해결한 감사 결함 | 반영 위치 |
|---|---|---|---|
| T1 | 시작 판정 순서를 REQ-008 하나에 고정: 422 → 404 → 503 → 같은 종목 실행 중(200, 쿼터 차감 없음) → 다른 종목 실행 중(429 `goose_busy`) → 쿼터 소진(429 `goose_rate_limit`) → 무결성 실패(202, 쿼터 미차감) → 시작(202) | R1-D1 | REQ-008, AC-008, design §4.3 |
| T2 | 같은 종목 재요청은 HTTP **200**, 새 시작은 **202** | R1-D10 | REQ-008, AC-007 |
| T3 | 셀 활성 표시는 `GET /ai-report/goose/active` 조회 + 셀 폴링. 저장된 `job_id`가 있는 셀만 폴링하고, 응답이 `null`이거나 다른 작업이면 중지. SSE는 모달 전용으로 유지. 이 경로는 `/{code}/{filename}`보다 먼저 등록 | R1-D2 | REQ-013, 021, AC-021, 022, design §4.5, §7.2 |
| T4 | 프로세스 종료(REQ-006)와 종료 상태 기록(REQ-007)을 분리하고 사유→상태/오류 종류 표를 둔다. **`cancelled`는 종료 상태이며 오류 종류가 아니다.** 서버 종료도 `cancelled` | R1-D4 | REQ-006, 007, AC-005, 006, 011, design §4.1 |
| T5 | 가정은 작업 디렉터리의 `assumptions.md`에 기록(없으면 “가정 없음”), 보관 폴더로 복사, 라이브 AC-025에서 존재·비어 있지 않음 확인 | R1-D5 | REQ-005, 014, AC-013, 025, design §2.1 |
| T6 | 쿼터는 실제로 프로세스를 띄우기로 확정될 때 1회 차감. 무결성 실패는 차감하지 않고 실행 중 작업으로 등록하지 않음. 취소·오류로 끝나도 환급하지 않음 | R1-D11 | REQ-001, 008, AC-001, design §4.3 |
| T7 | `final` 판정 단일 규칙: `final/report.html` 존재 **그리고** `final/render-validation.json`의 `delivery_allowed: true`. 아니면 `draft/` | R1-D6 | REQ-014, AC-014, design §5.2 |
| T8 | 프로세스 종료 유예 시간은 실행기 인자(기본 15초), 테스트는 0.5초 주입 | R1-D9 | REQ-006, AC-005, design §3.4 |
| T9 | 모달을 다시 열면 새 `EventSource`가 헤더 없이 전체 재생을 받는다. `Last-Event-ID`는 같은 객체의 자동 재접속에만 쓰인다(설계 설명 정정) | R1-D8 | design §4.4, §8 |
| T10 | 시간 초과·비정상 종료·취소·서버 종료(best-effort)로 끝났지만 선택 가능한 리포트(대개 `draft/report.html`)가 있으면, 종료 상태·오류 종류는 분류대로(`error/timeout`, `error/exit_error`, `cancelled`) 두고 리포트는 허용 목록 방식으로 보관하며 `interrupted: true`를 기록한다. 전달 상태는 선택 규칙 결과 그대로(`final` 조건이 맞으면 `final`, 아니면 `draft`, 사용자 결정 R3-M2). 화면은 `draft`면 초안 배너, `interrupted`면 상태와 상관없이 중단 안내. 기록 항목에 `interrupted: true`. 근거: 결정 D7(비용이 든 초안을 버리지 않는다) | R2-N4 | REQ-007, 014, 017, 019, AC-014(e)(f)(g), 017, 019, design §4.1, §4.4, §4.6, §5.2, §5.3, §7.1 |
| T11 | **하네스는 리포 밖에서 실행하고, 리포에는 추적 원본만 둔다.** 원본 `backend/goose_harness_src/`는 `.claude`·`CLAUDE.md`라는 이름을 쓰지 않고(`harness-instructions.md`, `claude-settings.json`, `skills/goose/`), 리포의 `goose-manifest.json`이 설치본 경로 기준 sha256을 고정한다. 서버 시작 시 원본을 매니페스트로 대조해 맞을 때만 `~/.goose-harness`(`AI_REPORT_GOOSE_HARNESS_DIR`)에 설치하고(`runs/` 보존), 작업 시작마다 설치본을 같은 매니페스트로 검사한다(목록 밖 `.claude/` 파일도 실패). 원본 대조가 실패하면 그 서버 실행 동안 모든 작업이 `integrity`로 끝난다(기존 설치본이 맞아도 — 닫힌 실패, v0.4.1 사용자 결정). 매니페스트 범위는 `CLAUDE.md`·`settings.json`·스킬 전체. **근거**: (1) 리포 안 실행은 오염된다(M1 P2: 캐시 생성 115,950 대 13,028, MoAI 스킬·에이전트 17개·MCP 서버·리포 메모리 누수). (2) 리포 안에 `.claude/skills`가 있으면 이 리포의 MoAI 세션이 goose 스킬을 발견한다(M1 부수 관측). 이름을 바꾼 원본은 발견 대상이 아니다. (3) 원본을 리포에 두어 벤더링 내역이 버전 관리되고, 매니페스트가 설치본 밖(리포)에 있어 설치본을 바꾼 쪽이 기준값까지 바꿀 수 없으므로 REQ-001 검사가 의미를 가진다. **기각한 대안**: (a) 리포에 사본 없이 수동 배치 — 벤더링 이력과 설정 파일 원본이 추적되지 않고 새 환경에서 재현할 수 없다. (b) 원본을 `.claude/` 이름 그대로 리포에 두고 복사 — (2)의 발견 문제가 남는다. (c) `--restricted` — goose 스킬도 사라진다(M1 P2b) | M1 판정(조건부 GO), 사용자 결정 2026-10-19 | REQ-001, 002, 022, AC-001, 002, 023, design §2, §2.3, §3.1, §6 |

### 2.4 감사 결함 처리 내역

| 결함 | 분류 | 처리 |
|---|---|---|
| R1-D1 시작 판정 우선순위 모순 | blocking | 반영 — T1, AC-008 5·6행 추가 |
| R1-D2 모달 닫은 뒤 셀 활성 표시 불가 | blocking | 반영 — T3 |
| R1-D3 AC-023 충족 불가(`backend/prompts/__init__.py`, `README.md`, `__pycache__`) | blocking | 반영 — 두 파일 [MODIFY] 추가, AC-023을 `git grep -nI`로 변경 |
| R1-D4 REQ-006 범위 불일치, `cancelled` 정의 충돌 | blocking | 반영 — T4 |
| R1-D5 가정 기록 검증 불가 | blocking | 반영 — T5 |
| R1-D6 `final` 규칙 불일치 | blocking | 반영 — T7, AC-014(c) 추가 |
| R1-D7 503 우선순위 미검증 | optional | 반영 — AC-008 4행 |
| R1-D8 `Last-Event-ID` 설명 오류 | optional | 반영 — T9 |
| R1-D9 유예 시간 모호 | optional | 반영 — T8 |
| R1-D10 같은 종목 재요청 상태 코드 | optional | 반영 — T2 |
| R1-D11 쿼터 차감 규칙 | optional | 반영 — T6 |
| R1-D12 AC-015→REQ-020 간접 추적 | optional | 반영 — 현 AC-014에서 배너 REQ 추적을 빼고 “전제 데이터” 비고로 표시 |
| R1-D13 REQ의 sessionStorage 구현 누출 | optional | 반영 — REQ-020을 “같은 브라우저 탭에서 이전에 시작한 작업”으로 표현, 저장 수단은 design §7.1 |
| R1-D14 `module` 경로 형태 | optional | 반영 — `module: "backend/services"` |

거절한 결함: 없음.

2회차(`.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-2.md`, FAIL 0.90) — 재번호 없이 반영

| 결함 | 분류 | 처리 |
|---|---|---|
| R2-N1 REQ-008 순서에 무결성 단계 없음 | blocking | 반영 — REQ-008에 무결성 실패 단계(202, 쿼터 미차감, 미등록) 삽입, REQ-001에 응답 202 명시, AC-001 Then에 202 |
| R2-N2 REQ-021 범위가 설계보다 넓음 | blocking | 반영 — “같은 브라우저 탭에서 이전에 시작한 작업”으로 한정 |
| R2-N3 AC-011 전제가 D10과 충돌 | blocking | 반영 — J1 취소 후 J3 시작하는 순차 전제 |
| R2-N4 중단 종료와 리포트 선택 우선순위 | blocking | 반영 — T10, REQ-007 조건절 정정, AC-014 (e)(f) |
| R2-N5 폴링 재시작 미검증 | optional | 반영 — AC-022 (6), design §7.2 앱 내부 신호 |
| R2-N6 AC-025 추적 불일치 | optional | 반영 — AC-025 머리줄에 REQ-017 |
| R2-N7 결정 ID와 결함 ID 충돌 | optional | 반영 — 감사 결함에 `R1-`/`R2-` 접두어, AC의 “D7/D8 위반”을 “결정 D7/D8 위반”으로 |
| R2-N8 스크립트 출력 점검 주장 과장 | optional | 반영 — design §6.1을 “매니페스트 대상 파일 변경만 걸린다”로 축소 |
| R2-N9 `assumptions.md` 부재 시 동작 | optional | 반영 — REQ-014 “when present; its absence is not an error” |

거절한 결함: 없음.

3회차(`.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-3.md`, FAIL 0.91) — 사용자가 부채 수용을 선택(4회차 감사 없음), v0.3.2에서 수정

| 결함 | 분류 | 처리 |
|---|---|---|
| R3-M1 기록 탭에 `interrupted` 경로 없음 | blocking | 반영 — `HistoryItem.interrupted`(기본 `false`), REQ-017, design §5.3·§7.1, AC-017 중단 항목 추가 |
| R3-M2 중단 시 `final`/`draft` 충돌 | blocking | 반영(사용자 결정) — 선택된 전달 상태 유지, 중단 안내는 상태와 상관없이 표시. REQ-014·019, design §4.4·§5.2, T10, AC-014 (g), AC-019 |
| R3-M3 서버 종료 시 보관 여부 | optional | 반영 — REQ-014 계기에 서버 종료(best-effort), design §4.6 |
| R3-M4 design §4.1 그림·표 첫 행 | optional | 반영 — “exit 0 + 리포트 선택됨” |
| R3-M5 T1 요약에 무결성 단계 누락 | optional | 반영 — T1에 무결성 실패 단계 |

거절한 결함: 없음.

4회차(`.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-4.md`, PASS 0.93, run 단계 Phase 1) — M1 관측 반영과 함께 v0.4.0에서 처리, 재번호 없음

| 결함 | 분류 | 처리 |
|---|---|---|
| R4-1 AC-014 “픽스처 4종” | SHOULD-FIX | 반영 — “픽스처 7종 (a)~(g)” |
| R4-2 REQ-014 “(in practice `draft/report.html`)” | MINOR | 반영 — 괄호 삭제(spec.md, spec-compact.md) |
| R4-3 M5 항목·추적표 017행에 `interrupted` 없음 | SHOULD-FIX | 반영 — M5 “(+`delivery_status`, `run`, `interrupted`)”, 추적표 017행 |
| R4-4 추적표 008행에 무결성 단계 없음 | MINOR | 반영 — “…→쿼터 429→무결성 실패 202(쿼터 미차감)→202” |
| R4-5 머리말 감사 이력·`R3-` 접두어·§2.3 제목 | MINOR | 반영 — 머리말, §2.3 제목 |
| R4-6 서버 종료 보관 best-effort 판정 불가 | MINOR | 보류 — 이번 위임 범위 밖(R4-1·3·7 필수, 2·4·8 선택) |
| R4-7 design §8 라우터가 4~6단계 판정 | SHOULD-FIX | 반영 — design §8을 “router 1~3단계 → service.start()가 잠금 안에서 4~8단계” |
| R4-8 progress.md §G “verification pending” | MINOR | 반영 — 해당 줄을 “검증 완료, 독립 재감사는 review-4”로 갱신 |
| R4-9 AC-014에 exit 7 + 초안 경우 없음 | MINOR | 보류 — R4-6과 같은 이유. M4·M5 위임 프롬프트에서 명시 권장 |

5회차(`.moai/reports/plan-audit/SPEC-AI-REPORT-004-review-5.md`, FAIL 0.83, v0.4.0 delta) — 점수 하락에 따른 STOP 신호로 한 번만 수정, v0.4.1, 재번호 없음. 보고서의 결함 번호 D1~D10을 `R5-1`~`R5-10`으로 적는다

| 결함 | 분류 | 처리 |
|---|---|---|
| R5-1 원본 대조 실패 + 기존 설치본이 있을 때 동작 미정 | blocking | 반영 — 사용자 결정(2026-10-19): 닫힌 실패. 시작 시 실패를 기록하고 이후 작업은 기존 설치본이 맞아도 `error`/`integrity`. REQ-001·008, design §2.3·§4.1·§4.3, AC-001 (2b) |
| R5-2 원본 쪽 목록 밖 파일 규칙이 매니페스트 파일 자체와 충돌, REQ에 없음 | blocking | 반영 — 제외 목록(`goose-manifest.json`, `.DS_Store`)을 REQ-001·design §2.3에 명시, AC-001 (1) 제외 파일 조건과 (2c) 목록 밖 원본 파일 |
| R5-3 AC-003 (6)이 `cat` 한 형태만 시험 | blocking | 반영 — (6a)~(6f): `cat`·`head`·`grep` 절대 경로, `~`·`$HOME` 경로, 허용 스크립트 뒤 복합 명령. 거부 11건. REQ-003 둘째 절과 design §2.2 표를 맞춤 |
| R5-4 "M1이 변경 감지를 확인" 과장 | blocking | 반영 — design §6.1·§9 행을 "오탐 없음 관측, 감지는 AC-001 (3)(4)"로. progress.md 관측 기록은 그대로 두고 아래에 정정 줄 추가 |
| R5-5 design §2.2 표 제목이 미실행 규칙까지 덮음 | optional | 반영 — 제목 변경, `audit_report.py` 허용·`CLAUDE.md` 거부에 [미관측] |
| R5-6 리포 아래 `<H>` 거부가 REQ·AC에 없음 | optional | 보류 — M2 위임 프롬프트에서 결과(설치 안 함 → R5-1 규칙에 따라 작업은 `integrity`)를 명시 권장 |
| R5-7 research.md 낡은 cwd 설명 | optional | 반영 — §2.5·§5.3 두 곳에 T11 대체 표시 |
| R5-8 AC-012 기대 순서 리터럴 미고정 | optional | 보류 — M3 위임 프롬프트에서 녹화 기준 리터럴을 테스트에 직접 적도록 명시 권장 |
| R5-9 acceptance 머리말 변경 목록에 AC-025 누락 | optional | 반영 |
| R5-10 설치본 최상위 기타 파일(`CLAUDE.local.md` 등) 미검사 | optional | 보류 — M2 재관측 때 `CLAUDE.local.md` 로드 여부를 함께 확인 권장 |

### 2.5 Tier

Tier L(사용자 확정). 산출물 5종 + `spec-compact.md` + `progress.md`. 요구사항 23개, 인수 기준 25개(각 상한 25). plan-auditor 통과 기준 0.85.

## 3. 파일 목록

| 구분 | 파일 |
|---|---|
| 신규(추적 원본, T11) | `backend/goose_harness_src/harness-instructions.md`(→ 설치본 `CLAUDE.md`), `backend/goose_harness_src/claude-settings.json`(→ `.claude/settings.json`), `backend/goose_harness_src/goose-manifest.json`(설치본 경로 기준), `backend/goose_harness_src/skills/goose/**`(벤더링, 작성 아님. 로컬 수정 1건 — `workflows/stock-report/references/report-input.md` 8-9행 실행 예시를 상대 경로 형식으로, v0.4.4, design §2. 다시 벤더링하면 재적용) |
| 런타임(리포 밖, 커밋 안 함) | `~/.goose-harness/{CLAUDE.md, .claude/settings.json, .claude/skills/goose/**, runs/}` — 서버 시작 시 설치 |
| 삭제(미추적) | `backend/goose_harness/` — M1 임시 하네스. 리포 안 `.claude/skills`라 MoAI 세션에 발견됨. M2에서 원본으로 옮긴 뒤 삭제 |
| 신규 | `backend/services/goose_runner.py`, `backend/services/goose_job_service.py` |
| 신규 테스트 | `backend/tests/test_goose_runner.py`, `backend/tests/test_goose_job_service.py`, `backend/tests/test_ai_report_router_goose.py`, `backend/tests/fixtures/goose_stream_299030.jsonl`(M1 녹화), `frontend/src/hooks/__tests__/useAiReport.goose.test.ts`, `frontend/src/hooks/__tests__/useGooseActive.test.ts` |
| 수정 | `backend/routers/ai_report.py`, `backend/services/ai_report_service.py`(기록 `kind`), `backend/schemas/ai_report.py`, **`backend/main.py`**(`:34-36` import, `:76` 프롬프트 로드, `:84` 스테이징 정리 제거 + lifespan 종료 시 작업 정리), **`backend/prompts/__init__.py`**(`:9` 언급 제거), **`backend/prompts/README.md`**(`:11-12` 언급 제거), `.env.example`(`.gitignore`는 작업 디렉터리가 리포 밖이라 변경 없음) |
| 수정 | `frontend/src/components/AiReportModal.tsx`, `frontend/src/components/ProgressPanel.tsx`(5소스 → goose 단계로 교체), `frontend/src/components/ChartGrid/ChartCell.tsx`(활성 표시 + `handleCloseAiReport` `:92-96`), `frontend/src/hooks/useAiReport.ts`, `frontend/src/api/aiReport.ts`, `frontend/src/types/aiReport.ts` |
| 신규(프론트) | `frontend/src/hooks/useGooseActive.ts`(셀 폴링 훅, 이름은 구현 단계에서 확정) |
| 수정 테스트 | `frontend/src/components/__tests__/AiReportModal.test.tsx`, `frontend/src/components/__tests__/ProgressPanel.test.tsx` |
| 축소/정리 | `backend/services/claude_cli_streamer.py`(라인 파서·종료 함수만 남기거나 실행기로 이동, `stream_claude_synthesis` 삭제), `backend/tests/test_claude_cli_streamer.py`(남는 부분만) |
| 삭제 | `backend/services/deep_research_service.py`, `backend/services/deep_research_collector.py`, `backend/prompts/stock_synthesis_prompt.md` |
| 삭제/교체 테스트 | `backend/tests/test_deep_research_service.py`, `backend/tests/test_deep_research_collector.py`(삭제), `backend/tests/test_ai_report_router_deep_mode.py`(→ `test_ai_report_router_goose.py`로 교체) |
| 변경 없음(회귀 확인) | `backend/services/codex_cli_runner.py`, `stream_codex_fast`, `backend/tests/test_ai_report_service.py`, `backend/tests/test_codex_cli_runner.py` |

## 4. 마일스톤 (결정이 바뀔 가능성이 큰 순서)

우선순위 표기만 쓰고 소요 시간은 적지 않는다. M1의 관측값이 이후 값(시간 상한, 진행 단계 대응표, 하네스 위치, 결과 파일 위치, 권한 규칙 문법)을 확정한다. design.md §9의 잠정 목록은 M1 직후 manager-spec 재위임으로 갱신했다(v0.4.0, design §9 측정 완료 표와 §9.1 미관측 목록).

### M1 — 스파이크: 헤드리스 goose 실행 가능성 확인 (Priority High, go/no-go) — **완료: 조건부 GO (2026-10-19)**

결과: 리포 밖 하네스 + `--settings` + `--strict-mcp-config` + 설정 `env.PATH`·`autoMemoryEnabled:false` 조합에서만 통과. 측정값과 미관측 항목은 `progress.md §E.2 ### M1 스파이크 관측`과 design §9·§9.1. 아래 준비·탐침 설명은 실행 당시 계획 기록으로 남긴다(“최종 위치 `backend/goose_harness/`”는 T11로 폐기).

목적: research.md §8의 증거 공백 G1~G9를 관측으로 닫는다. 서비스 코드는 바꾸지 않는다.

준비
- 하네스를 **최종 위치** `backend/goose_harness/`에 임시로 꾸린다(상위 CLAUDE.md 탐색은 위치에 좌우되므로). 커밋은 M2에서.
- 비교용으로 같은 하네스를 세션 스크래치 디렉터리(상위에 CLAUDE.md 없음)에도 복사한다.
- 벤더링 전 `DISTRIBUTION.json` sha256 대조 결과를 기록한다.

탐침 — 명령과 관측 출력을 그대로 `progress.md §E.2`에 기록

| 탐침 | 닫는 공백 | 내용 |
|---|---|---|
| P0 | G1 | 하네스 cwd에서 `claude -p "ok라고만 답하세요" --setting-sources project --output-format stream-json --verbose --permission-mode dontAsk --no-session-persistence --model sonnet` → `result.is_error` |
| P1 | G3 | 같은 실행의 `system/init`에서 스킬·슬래시 명령·도구·에이전트 목록 — `goose` 있음, MoAI 스킬 없음 |
| P2 | G2 | 리포 내 위치와 스크래치 위치에서 P0를 각각 실행해 `result.usage` 입력 토큰(캐시 생성·읽기 포함) 비교 |
| P3 | G6 | 음성 탐침 4종(AC-003과 동일) → `permission_denials` 4건, 파일 변화 0 |
| P4 | G4, G5, G7, G8, G9 | 실제 분석 1회: 하나기술(299030), 모델 `sonnet`. stream-json 전체를 파일로 저장(→ 픽스처 원본). `assumptions.md` 작성 여부 확인 |
| P5 | G4 | P4 기록의 Agent `tool_use` 개수·역할 설명, 서브에이전트 쪽 거부 기록 |
| P6 | G7 | 작업 디렉터리의 `draft/`·`final/` 존재, `render-validation.json`의 `delivery_allowed`·`delivery_status`, `delivery-audit.json`의 `decision` |
| P7 | G9 | 이벤트 타입·도구 이름 빈도표 → 진행 단계 대응표 확정 |

통과(GO) 조건
- P0 인증 성공, P1에서 `goose` 발견.
- P3 4종 모두 거부 + 파일 변화 0.
- P4가 사람 입력 없이 끝나고 작업 디렉터리에 `report.html`(초안 또는 최종) 생성. 초안만 나와도 D7에 따라 GO.
- P2에서 오염이 확인되면 조건부 GO: 하네스를 리포 밖(`AI_REPORT_GOOSE_HARNESS_DIR`)으로 옮기거나 `--restricted --tools …`를 재탐침해 통과해야 GO.

대체 경로(NO-GO 시)
- 스킬 미발견 → `--plugin-dir` 또는 `--append-system-prompt-file`로 재시도.
- Agent 도구 없음/미사용 → goose 순차 역할 수행 허용(실행 시간만 증가).
- 인터뷰로 멈춤 또는 `assumptions.md` 미작성 → 하네스 CLAUDE.md·프롬프트 보강 후 재시도, 두 번 실패하면 사용자 보고.
- 음성 탐침 하나라도 통과 → 권한 규칙 재작성 후 재탐침. 해결 전 M2 진입 금지.
- 인증 실패 → 사용자 보고(`--bare`는 API 키 전용이라 대안 아님).

M1 산출값: `AI_REPORT_GOOSE_TIMEOUT` 기본값(P4 측정값×2, 5분 단위 올림), 진행 단계 대응표, 결과 파일 탐색 위치, 하네스 위치, 권한 규칙 문법, 인증용 환경 변수, 녹화 픽스처.

### M2 — 하네스 원본·설치·재탐침 (Priority High)

- 추적 원본 `backend/goose_harness_src/` 작성(T11, design §2): goose 벤더링(`.DS_Store` 제외) → `skills/goose/`, `harness-instructions.md`(design §2.1, 가정 기록 규칙 포함), `claude-settings.json`(design §2.2: 권한 + `env.PATH` + `autoMemoryEnabled: false` + `disableAllHooks: true`), `goose-manifest.json`(설치본 경로 기준, `CLAUDE.md`·`.claude/settings.json`·`.claude/skills/goose/**` 전체).
- 원본 대조·설치 함수(서버 시작 시, `runs/` 보존, 리포 아래 경로 거부, `goose-manifest.json`·`.DS_Store` 제외, 대조 실패 시 실패 기록 → 이후 작업은 기존 설치본과 상관없이 `integrity`)와 설치본 무결성 검사 함수(목록 밖 `.claude/` 파일 포함) — design §2.3, AC-001.
- M1 임시 `backend/goose_harness/`(미추적) 삭제. `git ls-files backend`에 `.claude`·`CLAUDE.md` 없음 확인(AC-023 일부).
- 최종 위치 `~/.goose-harness`에서 재관측: P0·P1(`goose` 발견, MoAI 항목 없음, `mcp_servers []`, `~/.claude/CLAUDE.md` 로드 여부 확인 시도), AC-003 음성 탐침 (1)~(5)와 (6a)~(6f). (6a)~(6f) 중 하나라도 하네스 밖 읽기 전용 Bash가 거부되지 않으면 거부 규칙을 보강해 재탐침하고, 막을 수 없으면 차단 보고(M3 진입 금지).

### M3 — 실행기 `goose_runner.py` (Priority High)

- argv(design §3.1: `--settings <H>/.claude/settings.json`, `--strict-mcp-config` 포함, cwd = `AI_REPORT_GOOSE_HARNESS_DIR` 기본 `~/.goose-harness`), 프롬프트(§3.2), 환경 변수 허용 목록(§3.3, 부모에 있는 8개 중 해당 변수만), 새 프로세스 그룹 + 그룹 단위 종료 + 유예 시간 인자(§3.4), 시간 상한 기본 900초, 종료 사유 분류(§4.1 표), stream-json 해석과 진행 단계 대응(§3.5 측정 표, 녹화 픽스처 `goose_stream_299030.jsonl`).
- AC-002, 004, 005, 006, 012.

### M4 — 작업 서비스와 라우터 (Priority High)

- `goose_job_service.py`: 상태 기계(design.md §4.1), 시작 판정 순서(§4.3, T1·T2·T6), 이벤트 재생(§4.4), 취소, 실행 중 작업 조회(§4.5), lifespan 종료 정리(§4.6).
- 레이트 리밋: `deep_research_service.check_deep_rate_limit`(`:96-145`)을 goose 전용으로 옮겨 `AI_REPORT_GOOSE_DAILY_QUOTA`(기본 5)로 읽는다. Fast 카운터와 분리.
- 라우터: `mode=deep` → 작업 시작, `GET /ai-report/jobs/{job_id}/events`, `POST /ai-report/jobs/{job_id}/cancel`, `GET /ai-report/goose/active`(기존 `/{code}/{filename}`보다 먼저 등록).
- AC-001, 007~011, 021.

### M5 — 저장과 서빙 (Priority Medium)

- `final` 판정(T7)과 허용 파일 + `assumptions.md` 복사, `job.json`(design.md §5.1-5.2).
- `GET /ai-report/{code}/goose/{run}/report.html` + CSP(§5.4), 경로 검증.
- 기록 API: `kind: markdown` + `kind: goose`(+`delivery_status`, `run`, `interrupted`), 스키마 확장(§5.3).
- AC-013~017.

### M6 — 프론트엔드 (Priority Medium)

- `AiReportModal.tsx`: “Goose” 라벨, 진행 패널 + 취소 버튼, iframe(sandbox 값 고정), 초안 배너 “최종 감사 미통과 초안”, 기록 탭 kind별 표시, 429 `goose_busy`/`goose_rate_limit` 안내.
- `ProgressPanel.tsx`: 5소스 전용 → goose 단계(design §3.5 측정 표: `goose_start`, `plan`, `research_tick`, `fetch_start`, `fetch_done`, `compose`, `render_draft`, `audit`, `render_final`, `session_end`).
- `useAiReport.ts` / `api/aiReport.ts` / `types/aiReport.ts`: 작업 시작 → `EventSource` 구독, sessionStorage `goose_job:{code}`, 닫기는 구독만 종료.
- 셀 폴링 훅 + `ChartCell.tsx`: `--active`에 Goose 작업 상태 반영(design §7.2), `handleCloseAiReport` 수정.
- AC-018~020, 022.

### M7 — 기존 Deep 파이프라인 정리 (Priority Low, 기계적 작업)

- §3 파일 목록의 삭제·축소 대상 처리, `main.py`·`backend/prompts/__init__.py`·`README.md` 수정, `.env.example`(옛 키·`AI_REPORT_DEEP_*` 제거, `AI_REPORT_GOOSE_MODEL=sonnet`, `AI_REPORT_GOOSE_TIMEOUT=900`, `AI_REPORT_GOOSE_DAILY_QUOTA=5`, `AI_REPORT_GOOSE_HARNESS_DIR`(주석으로 기본 `~/.goose-harness`) 추가).
- AC-023, 024. 라이브 AC-025는 M7 이후 dev 서버 재시작 상태에서.
- SPEC-AI-REPORT-002의 대체 표기는 sync 단계에서.

## 5. 환경 변수

| 변수 | 기본값 | 근거 |
|---|---|---|
| `AI_REPORT_GOOSE_MODEL` | `sonnet` | D9 |
| `AI_REPORT_GOOSE_TIMEOUT` | 900(초) | M1 P4 352.8초 × 2, 5분 단위 올림. 표본 1회·초안 종료 실행이라 AC-025에서 재측정 |
| `AI_REPORT_GOOSE_DAILY_QUOTA` | 5 | 승인 기획 |
| `AI_REPORT_GOOSE_HARNESS_DIR` | `~/.goose-harness` (리포 밖) | M1 P2 오염 확인, T11. 리포 아래 경로는 거부 |

하위 프로세스에는 `PATH`·`HOME`·`USER`·`LANG`·`LC_ALL`·`TZ`·`TMPDIR`·`SHELL` 중 부모에 있는 것만 넘긴다. 인증용 추가 변수는 없다(M1 P0: 6개로 구독 인증 성공).

## 6. 위험과 대응

research.md §7을 따른다. 특히:

1. **결과가 늘 초안일 가능성** — goose 감사기는 브라우저 화면 검수 `pass`를 요구한다. D7로 초안 표시가 확정돼 기능은 동작하지만, 사용자는 대부분 배너를 보게 될 수 있다. M1 P6이 실제 비율을 보여준다.
2. **권한 규칙 우회** — 접두어 Bash 규칙은 `..`로 우회된다. 정확한 경로 고정 + 거부 규칙 + M1 음성 탐침.
3. **삭제 범위 누락** — `main.py`와 `backend/prompts/__init__.py`·`README.md`가 Deep 자산을 언급한다. M7과 AC-023(`git grep`)이 함께 다룬다.
4. **라우트 가림** — `/ai-report/goose/active`가 `/{code}/{filename}`에 가려질 수 있다. 등록 순서를 지키고 AC-021이 422 여부로 잡는다.
5. **하네스 밖 읽기 전용 Bash** (M1 관측) — `dontAsk`에서도 읽기 전용 Bash가 자동 허용됐다. 하네스 밖 비밀 파일을 `cat`으로 읽고 WebFetch로 내보내는 주입 경로가 남을 수 있다. M2 재탐침(AC-003 (6))에서 막지 못하면 run 단계를 멈추고 다시 계획한다.
6. **서브에이전트 권한 상속 미확인** (M1 미관측) — 서브에이전트 쪽 음성 탐침이 없다. 서브에이전트가 메인 권한 규칙을 따르지 않으면 허용 목록 밖 도구를 쓸 수 있다. acceptance.md §H에 남은 위험으로 둔다.
7. **사용자 전역 `~/.claude/CLAUDE.md` 로드 미확인** (M1 미관측) — 로드되면 사용자 개인 지시가 하네스 세션에 섞인다. M2 재관측에서 확인을 시도한다.
8. **`-p` Bash `PATH` 원인 미상** (M1 미관측) — `env.PATH` 설정으로 우회했다. `claude` 버전이 바뀌면 동작이 달라질 수 있어 AC-025 라이브 실행이 회귀를 잡는다.
9. **시간 상한 대표성** — 900초는 초안에서 멈춘 실행 1회 기준이다. 감사·`--final`까지 가면 넘을 수 있어 AC-025에서 다시 잰다.

## 7. 요구사항·인수 기준 추적

| REQ | 요지 | AC |
|---|---|---|
| 001 | 서버 시작 시 원본 대조 후 설치(`runs/` 보존, 매니페스트·`.DS_Store` 제외) / 무결성 실패(목록 밖 파일, 시작 시 원본 대조 실패 기록 포함) → `error/integrity`, 미실행·미등록·쿼터 미차감 | 001 |
| 002 | argv(`--settings`·`--strict-mcp-config` 포함)·cwd `~/.goose-harness`·모델 기본 `sonnet`·우회 플래그 금지·설정 키 3개 | 002 |
| 003 | 허용 목록 밖 거부 + 하네스 밖 읽기 전용 Bash 거부 | 003 |
| 004 | 환경 변수 허용 목록 | 004 |
| 005 | 질문 금지 + `assumptions.md` 기록 | 025 |
| 006 | 프로세스 그룹 종료(유예 주입) | 005, 011 |
| 007 | 사유→종료 상태/오류 종류 1개, `cancelled`는 상태, 중단돼도 분류 유지(T10) | 006, 011, 014 |
| 008 | 시작 판정 순서(422→404→503→같은 종목 200→다른 종목 429→쿼터 429→무결성 실패 202(쿼터 미차감)→202) | 007, 008 |
| 009 | 재생·`Last-Event-ID`·404 | 009 |
| 010 | 구독 끊겨도 계속 | 010 |
| 011 | 취소 | 011 |
| 012 | 진행 단계 대응 | 012 |
| 013 | 실행 중 작업 조회 | 021 |
| 014 | 산출물 탐색·`final` 규칙·허용 복사·`assumptions.md`(있을 때)·중단 시 초안 보관(T10) | 013, 014, 025 |
| 015 | CSP sandbox | 015 |
| 016 | 경로 검증 404 | 016 |
| 017 | 기록 kind markdown + goose(`delivery_status`, `interrupted`) | 017, 025 |
| 018 | Goose 라벨·iframe sandbox | 018, 025 |
| 019 | 초안 배너 + 중단 안내 | 019, 025 |
| 020 | 재구독·닫기는 취소 아님 | 020, 025 |
| 021 | 같은 탭에서 시작한 작업의 셀 활성 표시(닫은 뒤·새로고침 후·재시작 포함) | 022 |
| 022 | Deep 자산 제거 + 추적 backend에 `.claude`·`CLAUDE.md` 없음 | 023 |
| 023 | Fast 회귀 없음 | 024 |

## 8. mx_plan (Phase 14 — @MX 태그 계획)

`code_comments: ko`이므로 태그 설명은 한국어로 쓴다. 에이전트가 붙이는 태그는 `[AUTO]` 접두어.

| 태그 | 대상 | 이유 |
|---|---|---|
| @MX:WARN + @MX:REASON | `goose_runner`의 하위 프로세스 생성 함수 | 새 프로세스 그룹으로 띄우지 않거나 그룹 종료를 빠뜨리면 `claude`·python 손자 프로세스가 고아로 남아 구독 사용량을 계속 소모 |
| @MX:WARN + @MX:REASON | `goose_runner`의 프로세스 그룹 종료 함수 | SIGTERM → 유예 → SIGKILL 순서와 `ProcessLookupError` 처리가 깨지면 종료 보장이 사라짐 |
| @MX:WARN + @MX:REASON | `goose_job_service`의 모듈 전역 작업 저장소와 `active_job_id` | 단일 uvicorn 전제, 다중 워커에서 D10이 깨짐. 판정-후-등록은 잠금 안에서만 |
| @MX:ANCHOR + @MX:REASON | `goose_job_service`의 공개 API(`start`, `subscribe`, `cancel`, `active`, `shutdown`) | 라우터·lifespan·테스트가 호출하는 계약. 시작 판정 순서(T1)와 종료 상태 불변(T4)을 바꾸면 REQ-007·008이 깨짐 |
| @MX:ANCHOR + @MX:REASON | goose 리포트 경로 검증 함수(run 정규식 + `resolve()` 이탈 차단) | 외부 입력이 파일 경로가 되는 유일한 관문. 기존 `get_report_content`와 같은 2중 방어 |
| @MX:ANCHOR + @MX:REASON | 산출물 선택·허용 복사 함수 | `final` 단일 규칙(T7)과 모델 출력 경로를 따르지 않는다는 보안 불변 |
| @MX:NOTE | 라우터의 `/ai-report/goose/active` 등록 위치 | `/{code}/{filename}`보다 먼저 등록해야 하는 이유 |
| @MX:NOTE | CSP 헤더 상수 | `sandbox`에 `allow-scripts`·`allow-same-origin`을 넣으면 안 되는 이유와 폰트 출처 목록 근거 |
| @MX:NOTE | 하위 프로세스 환경 변수 허용 목록 상수 | 백엔드 비밀이 상속되지 않게 하는 목록, 추가 시 검토 필요 |
| @MX:NOTE | 실행기의 하네스 권한 대응 주석 | 스크립트 정확한 경로 고정과 `..` 거부 규칙의 이유 |
| @MX:NOTE | stream-json 진행 단계 대응표 | M1 녹화 기반, 알 수 없는 이벤트 무시 불변 |
| @MX:NOTE | `AiReportModal`의 iframe `sandbox` 값, 셀 폴링 훅의 중지 조건 | 허용 토큰 3개 고정 근거, 저장값 있는 셀만 폴링하는 이유 |
| @MX:NOTE | 하네스 설치·무결성 검사 함수 | 매니페스트를 리포에서 읽는 이유(설치본이 기준값을 바꾸지 못하게), 원본에 `.claude` 이름을 쓰지 않는 이유(T11) |
| @MX:TODO | 시간 상한 기본 900초 상수 | M1 표본 1회·초안 종료 실행 기준. AC-025 라이브 재측정 후 확정되면 제거 |

기존 태그 정리: `deep_research_service.py`·`claude_cli_streamer.stream_claude_synthesis`의 ANCHOR/WARN은 파일·함수 삭제와 함께 사라진다. 남는 `parse_stream_json_line`의 ANCHOR는 호출자가 실행기로 바뀌므로 fan_in을 다시 센다.

## 9. 범위 밖

spec.md §6 Exclusions를 따른다.

## 10. 재사용 코드 (Reference)

- `backend/services/codex_cli_runner.py:72-94` — `CodexResult` 오류 분류
- `backend/services/codex_cli_runner.py:52`, `:57-63`, `:147` — stderr 꼬리, 인증 실패 판정
- `backend/services/claude_cli_streamer.py:62-102` — stream-json 라인 파서(불변 조건 유지, `tool_use` 해석 추가)
- `backend/services/claude_cli_streamer.py:110-131` — terminate→kill 종료(프로세스 그룹으로 확장)
- `backend/services/claude_cli_streamer.py:211-217` — 4MB 라인 버퍼
- `backend/services/db_service.py:26-49` — 배타 시작 패턴
- `backend/services/progress_store.py:23-53` — 잠금 보호 진행 상태
- `backend/routers/db.py:20-60` — 202 시작 + SSE 상태 스트림
- `backend/services/ai_report_service.py:297-343` — `_sanitize_name`
- `backend/services/ai_report_service.py:419-448` — 파일명 정규식 + `resolve()` 이탈 차단
- `backend/services/deep_research_service.py:96-145` — 레이트 리밋(삭제 전 goose 전용으로 이동)
- `backend/routers/ai_report.py:39-86` — 검사 순서(422 → 404 → 모드별)
- `frontend/src/api/aiReport.ts:41-157` — Fast용 SSE 파서(유지)
- `frontend/src/components/ChartGrid/ChartCell.tsx:92-96` — 현재 모달 닫기 핸들러(수정 대상)
