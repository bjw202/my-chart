---
id: SPEC-TEST-HERMETIC-001
title: "백엔드 pytest 스위트 허메틱화 — Output DB 부재 환경에서 pre-commit 게이트 통과"
version: "0.1.0"
status: draft
created: 2026-10-21
updated: 2026-10-21
author: manager-spec
priority: P1
phase: "v0.6.0 target"
module: "tests, backend/routers"
lifecycle: spec-anchored
tier: M
tags: "testing, hermetic, pytest, conftest, pre-commit-gate, worktree, vitest"
---

# SPEC-TEST-HERMETIC-001 — 백엔드 pytest 스위트 허메틱화

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2026-10-21 | 최초 작성 (칸반 카드 t12, plan-phase, Tier M) |

## 1. 배경 및 문제 정의

MoAI pre-commit 게이트(`.git/hooks/pre-commit` → `moai gate`)는 변경 범위와 무관하게 백엔드 pytest 전체 스위트를 실행한다. 새 git 워크트리에는 gitignored 프로덕션 DB(`Output/stock_data_weekly.db`, `Output/stock_data_daily.db`, 2026-10-21 실측 각 약 373MiB·487MiB)가 존재하지 않으므로, 프론트엔드만 수정한 카드의 커밋도 백엔드 테스트 약 21건 실패로 차단된다.

이 문제의 근본 원인은 게이트가 아니라 **테스트 스위트 자체가 비-허메틱**이라는 점이다. 워크트리 DB 복사(기존 워크어라운드)는 증상 은닉일 뿐이며, 본 SPEC은 스위트를 프로덕션 산출물과 무관하게 만드는 것을 목표로 한다.

참고: 워크트리 pre-commit 실패의 다른 축이었던 setuptools 문제는 이미 근본 해소되었다(`pyproject.toml` `setuptools<81` 핀, 커밋 `5b8d8f5`). 본 SPEC은 이를 재처리하지 않는다.

## 2. 조사 결과 (검증된 사실)

읽기 전용 조사 에이전트의 발견이며, plan 단계에서 아래 표기된 항목은 본 에이전트가 파일을 직접 읽어 재확인했다.

1. **의존성 토폴로지** — `my_chart/config.py:36,40,43-44`가 `OUTPUT_DIR`과 `DEFAULT_DB_WEEKLY/DAILY`를 정의하고, 40행의 `mkdir`은 임포트 시점에 실행된다(직접 재확인). `backend/deps.py:10-11`가 `DAILY_DB_PATH`/`WEEKLY_DB_PATH`를 파생하며(직접 재확인), 모든 라우터가 `from backend.deps import ...`로 각자 모듈 상수 복사본을 보유한다 — `backend.deps`만 패치해서는 무효하고, 라우터 모듈별 패치가 필요하다.
2. **21건 중 16건 설명됨** — `tests/test_market_api.py`(12건 실패): `test_client` 픽스처(128-137행)가 market/stage/sectors의 `WEEKLY_DB_PATH`만 패치하고 `DAILY_DB_PATH`는 패치하지 않아 daily DB 부재 시 실패(직접 재확인). 동일 갭이 194행의 `test_response_time_under_500ms` 메서드(별도 파일이 아닌 동일 파일 내 메서드 — 직접 확인)에도 적용된다. `tests/test_response_contract.py`(4건 실패): `client` 픽스처(94-102행)가 sectors WEEKLY+DAILY, stage WEEKLY는 패치하지만 `stage.DAILY_DB_PATH`는 누락(직접 재확인). 프로즌 픽스처 디렉터리(`tests/fixtures/frozen/aggregation-2026-08-11`)는 git 추적 대상이라 문제가 아니다.
3. **5건은 정적 분석으로 미설명** — `tests/test_m6_gap_closure.py`(4건)은 sectors/stage의 WEEKLY+DAILY를 git 추적 프로즌 픽스처 경로로 패치하고(36-39행, 직접 재확인), `tests/test_ac_sag_045_r1_r4_r5a.py`(1건)은 패치 문자열 없이 `compute_sector_aggregates`에 픽스처 경로를 명시 인자로 전달한다(패치는 registry 3건뿐 — 44-46·61행 직접 재확인). 두 파일 모두 t8b 워크트리에서의 실패 양상이 정적으로 재현되지 않았다. 본 SPEC은 관측된 RED 없이 이 5건에 대한 결함 주장을 하지 않으며, M1 재현 마일스톤이 실측으로 원인을 닫는다(프로젝트 교훈: 결함 주장에는 관측된 RED 증거가 필요).
4. **기존 픽스처 재료** — `tests/conftest.py`(283행)에 이미 tmp_path 기반 `daily_db`/`daily_db_no_meta`/`weekly_db` 픽스처(209-283행, 경로 문자열 반환)와 로드 함수 경계를 패치하는 `mock_sectormap` 선례(48-62행)가 있다(직접 재확인). 모듈 상수 패치 선례: `tests/test_rsr_m4_rs1m_responses.py:58`. DB 경로 상수를 건드리는 테스트 파일이 다수 존재한다(직접 grep 확인 — 고정 개수 대신 M1 시점에 실측 목록을 evidence로 남긴다).
5. **스코프 게이팅(option B)은 저장소 내 메커니즘이 없다** — `moai gate`에는 경로 스코프 인식이 없고, `gate.yaml`의 유일한 노브는 전역 `gate.disabled_steps`이며, 훅 스크립트의 스테이지드 파일 로직은 Go 전용이다. `.git/hooks/pre-commit`은 생성 템플릿이라 버전 관리 밖이다. 이 저장소에는 루트 `package.json`/`tsconfig.json`이 없어(frontend/만 존재) 게이트의 언어 감지가 TypeScript를 건너뛰는지 여부는 미검증이다.
6. **vitest 루트 위험(조건부)** — `frontend/vite.config.ts:15-20`의 test 설정에 root/include 고정이 없고(직접 재확인), `frontend/package.json`의 `test` 스크립트는 `vitest run`이다. 저장소 루트에서 vitest를 실행하면 `.claude/worktrees/*/frontend` 테스트를 수집한다(2026-08-19 관측, 약 78건 오탐). pytest는 `testpaths=["tests"]`(`pyproject.toml:54-59`)로 형제 워크트리 수집이 이미 차단되어 있다(직접 재확인).

## 3. 설계 방향 (오케스트레이터 결정 기록)

- **1차(option A)**: 백엔드 pytest 스위트를 허메틱하게 만든다. 수집된 어떤 테스트도 `Output/*.db`를 요구하지 않는다. conftest 수준 DB 경로 패치 픽스처 + 2곳의 알려진 패치 갭 수선. 재현 우선: 수정 전에 DB-less 환경에서 RED를 관측한다(M1), 수정 후 GREEN을 관측한다.
- **2차(option B)는 본 SPEC 범위 밖**: 변경 스코프 게이팅은 저장소 내 메커니즘이 없고 게이트 바이너리가 외부 요소이므로 구현하지 않는다. 대신 `moai gate`를 1회 실측해 실제 단계 이름과 JS/TS 트리거 여부를 기록하는 검증 단계만 둔다(M4). 게이트가 저장소 루트에서 vitest를 실행하는 것으로 확인되면 vitest root/include 핀(`frontend/vite.config.ts`)을 본 SPEC의 소형 마일스톤으로 흡수하고, 아니면 no-op 소견으로 기록한다.
- **5건 미설명 실패**: RED 관측 중 진단한다. 환경 의존적이라 픽스처 고립으로 해소할 수 없는 경우(예: 다른 gitignored 리소스를 읽는 경우)에도 최종 수용 기준은 DB-less 환경 0 실패를 요구하며, 진단 마일스톤이 그 갭을 닫는다.

## 4. 요구사항 (GEARS)

### REQ-001 — 수집·실행 완결성 (Ubiquitous)

백엔드 pytest 스위트(`tests/` 전체, 기본 마커 필터 `not live and not slow` 적용)는 `Output/` 산출 DB(stock_data_weekly.db, stock_data_daily.db)가 전혀 없는 환경에서도 오류 없이 수집(collect)되고 끝까지 실행되어야 한다.

### REQ-002 — DB-less 종료 코드 (Event-driven)

**When** `Output/` 아래에 .db 파일이 없는 환경에서 `.venv/bin/pytest tests/`가 실행되면, the suite shall 실패 0·오류 0으로 종료 코드 0을 반환해야 한다.

### REQ-003 — 라우터 DB 경로 패치 픽스처 (Ubiquitous)

`tests/conftest.py`는 각 테스트 실행 동안 `backend.routers` 패키지의 모든 모듈이 보유한 `WEEKLY_DB_PATH`·`DAILY_DB_PATH` 모듈 상수를, 픽스처가 만든 DB 경로(기존 `daily_db`/`weekly_db` 계열 산출물과 동일 계열)로 대체하는 단일 픽스처를 제공해야 한다. 패치 대상은 모듈 추가 시에도 자동으로 포함되도록 패키지 순회로 결정한다. 이 픽스처는 경로 상수 대체만 수행하며 DB 파일을 생성하지 않는다 — DB 파일 자체가 필요한 테스트는 기존 `daily_db`/`weekly_db` 픽스처를 계속 명시 요청한다.

### REQ-004 — 프로덕션 DB 비접촉 (Unwanted)

**While** 임의의 테스트가 실행 중일 때, the suite shall not `Output/` 아래의 프로덕션 .db 파일을 읽거나 생성한다.

### REQ-005 — 기존 픽스처 갭 수선 (Event-driven)

**When** `tests/test_market_api.py`의 `test_client` 픽스처 또는 `tests/test_response_contract.py`의 `client` 픽스처가 DB 경로를 패치할 때, the fixtures shall 해당 테스트가 실제로 임포트하는 라우터 모듈의 `WEEKLY_DB_PATH`와 `DAILY_DB_PATH`를 모두 커버해야 한다.

### REQ-006 — 미설명 실패의 관측 기반 진단 (Event-driven)

**When** DB-less RED 실행이 정적 분석으로 설명되지 않는 실패(`test_m6_gap_closure.py`, `test_ac_sag_045_r1_r4_r5a.py` 계열)를 노출하면, the run phase shall 실패 트레이스백을 관측하여 원인을 기록한 뒤에만 수정에 착수해야 한다. `nongating` 마커 재분류는 원칙적으로 금지하며, 부득의한 경우 사유와 함께 오케스트레이터에게 보고한다.

### REQ-007 — 게이트 실측 (Ubiquitous)

구현 과정에서 `moai gate`를 최소 1회 실측하여, the run phase shall 실제 단계 이름 목록과 JS/TS(vitest) 트리거 여부를 SPEC 진행 기록에 남겨야 한다.

### REQ-008 — 조건부 vitest 루트 고정 (Capability gate)

**Where** 게이트 실측이 이 저장소의 게이트 실행에 vitest가 포함됨을 확인하면, `frontend/vite.config.ts`의 test 설정 shall root/include를 frontend 디렉터리로 고정하여 저장소 루트 실행 시 상위 디렉터리(예: `.claude/worktrees/`)의 테스트를 수집하지 않게 해야 한다. **Where** 게이트 실측이 vitest 미실행을 확인하면, the run phase shall 이를 no-op 소견으로 기록하고 `vite.config.ts`를 변경하지 않아야 한다.

### REQ-009 — 정상 환경 회귀 없음 (State-driven)

**While** `Output/` DB가 존재하는 정상 개발 환경에서, the suite shall M1 이전 기준선(수정 전 동일 환경 전체 실행 결과) 대비 신규 실패 없이 통과해야 한다.

### REQ-010 — 증거 기반 달성 선언 (Ubiquitous)

허메틱 달성 선언(DB-less GREEN)은 `Output` 부재 환경에서 실측한 verbatim pytest 출력에만 근거해야 하며, the run phase shall 실패 ID·원인·처분 요약을 SPEC 디렉터리 증거 문서에 기록해야 한다. 대용량 원문 출력은 `.moai/state/verify/<세션>/`에 저장하고 요약에서 참조한다.

## 5. 제약 조건

- 하니스 표면 파일(`.claude/`, `.agency/`)은 수정 금지 — 타 작업의 미커밋 변경 약 684건이 존재한다.
- `.git/hooks/pre-commit`, moai-adk 바이너리, `moai update` 템플릿은 수정 금지(Out of Scope 참조).
- 백엔드 라우터/서비스 프로덕션 코드는 원칙적으로 변경하지 않는다(테스트 계층 해결 원칙). 단, M1 진단 결과 임포트 시점 부작용(`my_chart/config.py:40` mkdir 등)이 차단 원인으로 밝혀지는 경우에 한해 최소 시임(seam)을 허용하며 사유를 기록한다.
- `pyproject.toml`은 필요한 경우에만(예: pytest 설정 보강) 변경한다.
- 코드 주석 언어: ko (language.yaml `code_comments`). 커밋은 명시적 pathspec 스테이징으로 수행한다.
- DB-less RED 측정은 주 체크아웃에서 `Output/`을 임시 이동하는 방식을 금지하고, 별도 git 워크트리에서 수행한다(§7 안티패턴 참조).

## Out of Scope

### Out of Scope — 게이트 구조 변경

- moai-adk 바이너리 및 `moai gate` 단계 정의의 변경
- `.git/hooks/pre-commit` 훅 스크립트 수정(생성 템플릿으로 버전 관리 밖이며 `moai update`가 덮어씀)
- `moai update` 템플릿 변경
- 변경 범위 기반 스코프 게이팅(option B) 기능 구현 — 저장소 내 메커니즘이 없어 본 SPEC에서 제외하며, M4 실측 기록만 수행한다

### Out of Scope — 프로덕션 데이터·환경

- `Output/*.db` 복사·생성 자동화(워크트리 DB 복사 워크어라운드의 제도화)
- setuptools<81 핀 재처리(커밋 `5b8d8f5`로 이미 근본 해소)
- 프로덕션 DB 스키마·시드 데이터 변경

## 6. 수용 기준

Tier M SPEC이므로 상세 수용 기준은 `acceptance.md`가 소유한다. 핵심 종결 게이트는 다음 두 가지다: (1) DB-less 환경에서 `.venv/bin/pytest tests/` 종료 코드 0, (2) 정상 환경 기준선 대비 신규 실패 0.
