# SPEC-TEST-HERMETIC-001 — 수용 기준 (acceptance.md)

## §1 검증 원칙

1. 모든 AC는 실행 가능한 검사 명령과 기대값을 가진다(기계 검증 우선).
2. RED/GREEN 주장은 verbatim 출력으로만 한다. "통과할 것으로 보임"은 증거가 아니다.
3. 각 AC는 **자신이 잡아내는 오구현**을 명명한다. 오구현을 열거해 어떤 AC에도 걸리지 않는다면 그 AC는 결함이다(되돌림 실측으로 확인).
4. 개수·상수는 손으로 고정하지 않고 M1 기준선/실측값 인용 또는 델타 비교로 서술한다.

## §2 AC Matrix

### AC-001 — DB-less 전체 스위트 GREEN [게이트 블로킹]

- **Given** `Output/*.db`가 존재하지 않는 git 워크트리이고, 실행 전 바인딩 단언(`python -c "import backend; print(backend.__file__)"` 출력이 워크트리 내부 경로)을 통과한 환경 — venv editable-install 파인더가 `backend`를 주 체크아웃에 바인딩하면 DB-less 전제 자체가 깨진다
- **When** `cd <워크트리> && /Users/byunjungwon/Dev/my-project-01/my_chart/.venv/bin/pytest tests/ -q` 실행
- **Then** 종료 코드 0이고 출력에 `0 failed`, `0 error`가 포함된다
- **검사**: 명령 종료 코드 + 출력 확인 (verbatim 저장)
- **잡아내는 오구현**: (i) 현재 상태 그대로 — 프로덕션 DB 경로를 읽는 테스트가 M1 관측 세트로 잔존해 실패, (ii) 일부 파일만 고치고 나머지를 skip 처리한 수정 — skip 수 델타 0을 요구하는 AC-009에서 적발된다

### AC-002 — RED 증거 선보관 [증거/블로킹]

- **Given** M1 실행 완료
- **When** `.moai/specs/SPEC-TEST-HERMETIC-001/evidence/m1-red-observations.md`를 읽음
- **Then** DB-less 환경 실측 실패 테스트 ID 전수 목록과 원문 트레이스백 참조 경로가 존재하고, 조사 예상(16설명+5미설명)과 실측의 대조가 기록되어 있다
- **검사**: 파일 존재 + 실패 ID 목록의 비-empty + 예상-실측 대조 절 존재
- **잡아내는 오구현**: RED 관측 없이 M2를 착수해 "예상"만 기록한 경우 — 실측 명령 출력 참조가 없으면 FAIL

### AC-003 — 패치 픽스처의 전 모듈 커버 [블로킹]

- **Given** conftest 허메틱 픽스처가 적용된 테스트 컨텍스트
- **When** `backend.routers` 패키지의 모든 모듈을 순회해 각 모듈의 `WEEKLY_DB_PATH`·`DAILY_DB_PATH` 속성값을 조회하는 검증 테스트를 실행
- **Then** 모든 모듈의 두 상수가 픽스처 DB 경로(tmp_path 산하)를 가리킨다
- **검사**: 신규 검증 테스트(`pkgutil` 순회 기반)가 통과 — 단, 되돌림 RED 필수: 패치 픽스처를 제거(되돌림)하면 이 테스트는 반드시 실패해야 하며 그 실패 출력을 기록
- **잡아내는 오구현**: (i) `backend.deps`만 패치한 수정 — 라우터 모듈 상수는 원본 Output/ 경로 잔존으로 FAIL, (ii) market/stage/sectors 등 일부 모듈만 이름 나열해 패치한 수정 — 이후 추가/누락된 모듈(예: `stocks.py`)이 FAIL 유발

### AC-004 — test_market_api 계열 회복 [게이트 블로킹]

- **Given** DB-less 워크트리
- **When** `.venv/bin/pytest tests/test_market_api.py -q` 실행
- **Then** 종료 코드 0
- **검사**: 명령 종료 코드
- **잡아내는 오구현**: `test_client` 픽스처가 `DAILY_DB_PATH`를 여전히 패치하지 않는 수정 — market/stage 라우터의 daily DB 접근이 M1 관측과 동일하게 실패

### AC-005 — test_response_contract 회복 [게이트 블로킹]

- **Given** DB-less 워크트리
- **When** `.venv/bin/pytest tests/test_response_contract.py -q` 실행
- **Then** 종료 코드 0
- **검사**: 명령 종료 코드
- **잡아내는 오구현**: `client` 픽스처가 `stage.DAILY_DB_PATH`를 여전히 누락한 수정 — stage 라우터 daily 경로 접근 실패 잔존

### AC-006 — 미설명 5건 진단 기록 [증거/블로킹]

- **Given** M1에서 `test_m6_gap_closure.py`(4건)·`test_ac_sag_045_r1_r4_r5a.py`(1건) 실패가 관측됨
- **When** `evidence/m3-unexplained-diagnosis.md`를 읽음
- **Then** 관측된 각 실패에 대해 (트레이스백 요약 | 원인 | 처분) 항목이 존재하고, 수정된 경우 수정 전 RED/후 GREEN 출력 참조가 있다
- **검사**: 파일 존재 + 관측 실패 ID별 진단 항목 존재
- **잡아내는 오구현**: 트레이스백 없이 "환경 문제로 추정" 서술만 한 경우 — 원인 근거 출력 참조 부재로 FAIL

### AC-007 — 게이트 실측 기록 [증거/블로킹]

- **Given** M4에서 `moai gate` 실측 실행
- **When** `evidence/m4-gate-measurement.md`를 읽음
- **Then** 관측된 단계 이름 목록과 JS/TS(vitest) 트리거 여부 판정(실행/미실행 + 근거 출력)이 기록되어 있다
- **검사**: 파일 존재 + 단계 목록 및 판정 절 존재
- **잡아내는 오구현**: 실측 없이 gate.yaml/문서 추론만으로 게이트 동작을 서술한 경우 — 실행 출력 참조 부재로 FAIL

### AC-008 — 조건부 vitest 루트 고정 [조건부]

- **Given** AC-007의 실측 판정
- **Where** 게이트가 vitest를 실행함으로 판정된 경우: `frontend/vite.config.ts` test 설정에 root/include 고정이 존재하고, 저장소 루트에서 vitest 수집 대상 목록에 `.claude/worktrees` 경로가 0건이다
- **Where** 미실행으로 판정된 경우: 본 AC는 N/A로 처리하고 그 근거가 AC-007 문서에 기록되어 있으면 PASS
- **검사**: (실행 판정 시) `npx vitest list`(또는 동일 수집 형태) 출력에 worktree 경로 부재 + `git diff frontend/vite.config.ts`에 root/include 추가 확인; (미실행 판정 시) AC-007 문서의 no-op 기록
- **잡아내는 오구현**: root/include 미고정 상태 — 루트 실행 시 `.claude/worktrees/*/frontend` 수집(2026-08-19 관측 약 78건 오탐 재현)이 목록에 나타나 FAIL

### AC-009 — 정상 환경 회귀 0 [게이트 블로킹]

- **Given** M1 이전 기준선(`evidence/m0-baseline.md`, 정상 환경 전체 실행 실측)
- **When** 수정 완료 후 주 체크아웃(Output/ DB 존재)에서 `.venv/bin/pytest tests/ -q` 실행
- **Then** 기준선 대비 신규 실패 0(신규 실패 = 기준선 통과였으나 수정 후 실패한 테스트)이고, skip 수 델타도 0이다(기준선 대비 신규 skip 없음)
- **검사**: 기준선-사후 결과 집합 비교 — 실패 집합 델타와 skip 수 델타 모두 (델타 서술, 절대 상수 아님)
- **잡아내는 오구현**: (i) autouse 픽스처가 기존 테스트의 픽스처 DB 내용 의존을 깨는 회귀 — 기존 통과 테스트가 신규 실패로 전환되면 FAIL, (ii) 테스트를 skip으로 전환해 통과처럼 보이게 하는 수정 — skip 델타 0 요구로 FAIL

### AC-010 — 프로덕션 DB 비생성 [블로킹]

- **Given** AC-001의 DB-less 전체 실행 직후
- **When** 워크트리의 `Output/`을 검사
- **Then** `.db` 파일이 0건이다
- **검사**: `find <워크트리>/Output -name '*.db' 2>/dev/null | wc -l` 결과가 `0`
- **잡아내는 오구현**: 어떤 테스트(또는 임포트 부작용)가 기본 경로에 DB 파일을 생성하는 경우 — 임포트 타임 mkdir(빈 디렉터리)은 허용하되 .db 생성은 FAIL

## §3 심각도 분류

- **게이트 블로킹(핵심)**: AC-001, AC-004, AC-005, AC-009
- **증거/블로킹**: AC-002, AC-003, AC-006, AC-007, AC-010
- **조건부**: AC-008 (판정 결과에 따라 N/A 허용 — 유일하게)

## §4 비게이팅 절

본 SPEC의 AC 전체가 게이팅 대상이다. `nongating` 마커로 재분류되는 항목은 없다(REQ-006: 원칙 금지). M3 진단에서 환경 의존성이 확인되어 처분이 갈리는 경우에도 "재분류"가 아니라 "해소" 또는 "오케스트레이터 보고"로 처리한다.

## §5 추적성 (REQ ↔ AC)

| REQ | AC | 비고 |
|-----|----|------|
| REQ-001, REQ-002 | AC-001 | DB-less 수집·실행 완결 |
| REQ-010 | AC-002, AC-006, AC-007 | 증거 문서화 |
| REQ-003 | AC-003 | 전 모듈 패치 커버 (되돌림 RED 동반) |
| REQ-005 | AC-004, AC-005 | 알려진 갭 2곳 수선 |
| REQ-006 | AC-006 | 관측 기반 진단 |
| REQ-007 | AC-007 | 게이트 실측 |
| REQ-008 | AC-008 | 조건부 vitest 핀 |
| REQ-009 | AC-009 | 정상 환경 회귀 0 |
| REQ-004 | AC-001 + AC-010 | 읽기 부재(DB-less 실패 소멸) + 생성 부재(.db 0건)로 효과 검증 |

## §6 간접 검증

- AC-001의 DB-less GREEN은 "어떤 테스트도 프로덕션 DB를 읽지 않는다"(REQ-004 읽기 축)의 간접 전체 검증이다 — 파일이 없는데 성공한다는 사실이 곧 비접촉 증명.
- AC-010은 생성 축을 직접 검증한다. 두 AC가 함께 REQ-004의 양 축을 닫는다.
- AC-009는 "허메틱화가 정상 환경을 깨지 않았다"의 간접 검증으로, conftest 전역 변경의 부작용을 커버한다.

## §7 종결 게이트 (Definition of Done)

1. AC-001~AC-010 전부 PASS (AC-008은 조건부 N/A 허용).
2. 모든 RED/GREEN 판정에 verbatim 명령 출력 증거 존재 (`.moai/state/verify/<세션>/` + `evidence/`).
3. `git status --short`로 의도된 파일만 변경됐음을 확인.
4. 정상 환경 회귀 0 (AC-009) + DB-less GREEN (AC-001) 동시 충족.

## §8 Forward-looking Checks (본 SPEC 밖 후속 후보)

- `moai gate`의 변경 스코프 인식(게이트 바이너리 측 개선) — M4 실측 기록이 후속 SPEC의 입력이 된다.
- `gate.yaml` `disabled_steps` 단계명 노출/문서화.
- 임포트 시점 부작용(`my_chart/config.py:40` mkdir, `CACHE_DIR` mkdir)의 지연화 — M1/M3 진단에서 차단 원인으로 밝혀지지 않는 한 본 SPEC에서 다루지 않는다.
