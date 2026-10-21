# SPEC-TEST-HERMETIC-001 — 구현 계획 (plan.md)

## §A Context

- 발단: 칸반 카드 t12 — 프론트엔드 전용 카드의 커밋이 DB 부재 워크트리에서 백엔드 테스트 약 21건 실패로 차단됨. 워크어라운드(DB 복사, setuptools 핀)가 아니라 게이트가 의존하는 테스트 스위트 구조 자체를 고친다.
- 개발 모드: `quality.yaml` `constitution.development_mode: tdd` — 본 계획의 M1(RED 관측) → M2/M3(수정·GREEN) → M4(검증) 구조는 RED-GREEN-REFACTOR 사이클과 정합한다.
- 라우트: Route A (Tier M, main 직접 커밋·푸시, PR 없음).
- 브랜치: `main` (커밋은 명시적 pathspec 스테이징, `git add -A` 금지).

## §B Known Issues

| # | 사실 | 근거 |
|---|------|------|
| B1 | 모든 라우터가 `backend.deps`의 상수를 모듈별 복사본으로 보유 — deps만 패치하면 무효 | `backend/deps.py:10-11` + 라우터별 import (직접 재확인) |
| B2 | test_market_api.py `test_client` 픽스처가 `DAILY_DB_PATH` 미패치 → daily DB 부재 시 12건 실패 | `tests/test_market_api.py:128-137` (직접 재확인) |
| B3 | test_response_contract.py `client` 픽스처가 `stage.DAILY_DB_PATH` 미패치 → 4건 실패 | `tests/test_response_contract.py:94-102` (직접 재확인) |
| B4 | test_m6_gap_closure(4)은 DB 경로 패치형(36-39행), test_ac_sag_045(1)은 패치 문자열 없는 명시 인자형(44-46·61행) — 두 파일 모두 정적으로 실패 원인이 재현되지 않음 — **관측 전까지 결함 주장 금지** | t8b 워크트리 관측 vs 정적 분석 불일치 + 직접 재확인 |
| B5 | 게이트의 스코프 게이팅 메커니즘 부재, `.git/hooks/pre-commit`은 생성 템플릿 | 조사 결과 #5 |
| B6 | 게이트가 이 저장소에서 vitest를 실행하는지 미검증 — 루트 package.json/tsconfig 부재 | 조사 결과 #5, `frontend/package.json:9` |
| B7 | vitest 루트 미고정 시 `.claude/worktrees` 테스트 수집(약 78건 오탐 전례) | `frontend/vite.config.ts:15-20`, 2026-08-19 관측 |
| B8 | 임포트 시점에 `my_chart/config.py:40` mkdir이 실행되어 워크트리에 빈 `Output/`이 생성됨 — RED 판정은 `.db` 부재 기준으로 한다 | 직접 재확인 |

## §C Pre-flight

1. **LSP baseline 캡처** (quality.yaml plan 게이트) — 변경 전 `lsp` 상태 기록.
2. **기준선 측정 (정상 환경)** — 주 체크아웃에서 `.venv/bin/pytest tests/ -q` 전체 실행, 결과(통과/실패/스킵 수)를 `.moai/specs/SPEC-TEST-HERMETIC-001/evidence/m0-baseline.md`에 기록. AC-009의 비교 기준선이며, 개수는 절대 상수가 아니라 이 실측값을 인용한다(손전사 금지).
3. **DB-less 환경 준비** — `git worktree add`로 워크트리 생성(gitignored `Output/*.db` 부재 상태 그대로). 주 체크아웃에서 `Output/` 이동은 금지(dev 서버·타 세션 리스크).
4. **venv 재사용 규약** — 워크트리에는 .venv가 없으므로 주 저장소의 venv를 절대 경로로 호출하고 cwd만 워크트리로 둔다: `cd <워크트리> && /Users/byunjungwon/Dev/my-project-01/my_chart/.venv/bin/pytest tests/ -q`. 상대 경로·`python -c sys.path` 트랩 회피(프로젝트 교훈). 주의: 이 venv의 editable-install 파인더는 `backend`/`my_chart`를 주 체크아웃 절대 경로에 바인딩할 수 있다(plan-auditor neutral-cwd 관측). 현재 이를 막는 유일한 장치는 `tests/__init__.py` 존재가 pytest prepend 임포트 모드에서 워크트리 루트를 `sys.path[0]`에 넣는 것이며, 이는 문서화·검증되지 않은 안전장치다. 따라서 스위트 실행 전 바인딩 단언이 필수다: `cd <워크트리> && /Users/byunjungwon/Dev/my-project-01/my_chart/.venv/bin/python -c "import backend; print(backend.__file__)"` 출력이 워크트리 내부 경로여야 한다.
5. **커밋 전 동기화 점검** — 스폰/커밋 전 `git fetch origin main` + `git rev-list --count --left-right origin/main...HEAD` 및 `moai session list` 병렬 점검.

## §D Constraints

- 수정 허용 파일: `tests/conftest.py`, `tests/test_market_api.py`, `tests/test_response_contract.py`, M3 진단 결과에 따른 테스트 파일, (조건부) `frontend/vite.config.ts`, (필요 시) `pyproject.toml`, `.moai/specs/SPEC-TEST-HERMETIC-001/**`. 백엔드 프로덕션 코드는 최소 시임(seam) 예외만 허용(사유 기록 필수).
- 금지: `.claude/`, `.agency/`, `.git/hooks/`, moai-adk 바이너리, `moai update` 템플릿.
- 시간 예측 금지 — 우선순위(High/Medium/Low)와 단계 순서로만 표현.
- 코드 주석: ko. 커밋 주제: `fix(SPEC-TEST-HERMETIC-001): M<N> ...` (run-phase 첫 커밋에서 `draft → in-progress` 전이는 manager-develop 소유).

## §E Self-Verification

- 모든 RED/GREEN 주장에는 실행한 명령과 verbatim 출력을 첨부한다(verification-claim-integrity §2).
- 대용량 원문: `.moai/state/verify/<세션>/` 저장, 요약은 `.moai/specs/SPEC-TEST-HERMETIC-001/evidence/`에 기록하고 상호 참조.
- 커버리지: 본 SPEC은 테스트 인프라 변경으로 신규 프로덕션 코드가 원칙적으로 없으므로 85% 커버리지 게이트는 신규 코드 대상이 아니다. 대신 (1) DB-less 전체 GREEN, (2) 정상 환경 회귀 0이 DoD 게이트다. 측정이 필요하면 `coverage run --source=my_chart,backend -m pytest tests/` 형태를 쓴다(`pytest --cov`는 이 프로젝트에서 numpy ImportError로 실패하는 known issue).
- 되돌림 검증(대조 단언이 도입되는 경우): 구현 되돌림 → RED 관측 → `git status --short` 복원 증명까지가 1세트.

## §F Milestones

검토 집중 안내: 인간 리뷰 가치가 가장 높은 결정은 **M2의 픽스처 설계**(아래 기술 접근 참조)다. M1이 앞에 오는 것은 설계 결정이 아니라 재현 우선(프로젝트 교훈: 관측된 RED 없는 결함 주장 금지) 의무 때문이다. M3 이후는 M1·M2 관측 결과에 종속되는 순서 고정 단계다.

### M1 — RED 재현 (Reproduction-First) [Priority High]

- 목표: DB-less 환경에서 실패 세트를 실측해 증거로 고정한다. 예상 건수(약 21건)는 절대 상수로 쓰지 않고 실측값을 기록한다.
- 절차:
  1. §C-2 기준선 측정(정상 환경) 완료.
  2. DB-less 워크트리에서 `git status --short` + `ls Output/*.db`로 DB 부재 확인(B8: mkdir로 빈 Output/은 생성될 수 있음 — `.db` 부재 기준 판정).
  3. 바인딩 단언(§C-4): `cd <워크트리> && /Users/byunjungwon/Dev/my-project-01/my_chart/.venv/bin/python -c "import backend; print(backend.__file__)"` 출력이 워크트리 내부 경로임을 확인한다. 주 체크아웃 경로가 출력되면 즉시 중단한다.
  4. `.venv/bin/pytest tests/ --co -q` 수집 성공 확인.
  5. `.venv/bin/pytest tests/ -q` 전체 실행 → 실패 테스트 ID 목록 + 트레이스백 캡처.
- 파일 대상: 코드 수정 없음(증거만 산출).
- 증거 의무: `evidence/m1-red-observations.md`에 실패 ID 전수 목록, 조사 예상(16설명+5미설명)과 실측의 대조, 미설명 실패의 원문 트레이스백 참조.
- 중단 조건: 전체 실행에서 관측된 실패가 0건(예상 약 21건 대비)이면 DB-less 전제가 깨진 것이다 — 1순위 원인은 임포트가 주 체크아웃에 바인딩된 경우다. 바인딩을 고쳐 RED가 관측될 때까지 M2에 착수하지 않는다.
- 종결 조건: 관측된 실패 세트가 문서화됨. 이 산출물 없이 M2 착수 금지.

### M2 — conftest 허메틱 픽스처 [Priority High]

- 기술 접근(검토 집중점): conftest에 픽스처를 추가해 `backend.routers` 패키지를 순회하며 모든 모듈의 `WEEKLY_DB_PATH`/`DAILY_DB_PATH`를 패치한다. 형태는 (a) autouse — 테스트 작성자가 빠뜨려도 허메틱이 유지됨(기본안), (b) 명시 요청 — 기존 픽스처와의 간섭 최소. **기본안 (a)**: autouse는 "경로 대체"만 하고, DB 파일이 필요한 테스트는 기존 `daily_db`/`weekly_db` 픽스처를 계속 명시 요청한다. 기존 파일별 픽스처가 동일 속성을 재패치하더라도 monkeypatch 중첩은 안전하며(안쪽 패치가 우선), REQ-005의 갭 수선은 중복 방어로 남긴다. autouse 도입으로 기존 DB 경로 터치 테스트 파일들(M1 시점 grep 실측 목록)의 동작 변화를 M2 검증으로 확인한다.
- 파일 대상: `tests/conftest.py`(신규 픽스처), `tests/test_market_api.py`(갭 수선), `tests/test_response_contract.py`(갭 수선).
- 증거 의무: M1에서 실패한 test_market_api/test_response_contract 관련 테스트가 DB-less 환경에서 GREEN으로 전환되는 것을 verbatim 출력으로 기록. 픽스처 커버 검증(AC-003) 추가.
- RED-GREEN 대응: M1 관측이 RED, 본 마일스톤이 GREEN.

### M3 — 미설명 5건 진단·해소 [Priority High]

- M1에서 관측된 `test_m6_gap_closure.py`(4건), `test_ac_sag_045_r1_r4_r5a.py`(1건) 실패 각각에 대해: 트레이스백 관측 → 원인 기록 → 수정. 픽스처 고립으로 해소 불가한 환경 의존성으로 판명되면 원인과 처분을 기록하고 오케스트레이터에게 보고한다(REQ-006). `nongating` 재분류 원칙 금지.
- 파일 대상: 진단 결과에 따름(예상: `tests/test_m6_gap_closure.py`, `tests/test_ac_sag_045_r1_r4_r5a.py`, 또는 conftest).
- 증거 의무: `evidence/m3-unexplained-diagnosis.md` — 실패별 (트레이스백 요약 | 원인 | 처분 | 수정 전 RED/후 GREEN 출력 참조).

### M4 — 게이트 실측 + 조건부 vitest 핀 + 최종 검증 [Priority Medium]

- `moai gate` 1회 실측(가능하면 상세 모드) → 단계 이름 목록, JS/TS 트리거 여부를 `evidence/m4-gate-measurement.md`에 기록(REQ-007).
- **Where** vitest 실행 확인: `frontend/vite.config.ts` test 설정에 root/include 고정 추가 → 저장소 루트에서 vitest 수집 대상에 `.claude/worktrees`가 없음을 검증(REQ-008, AC-008). **Where** 미확인: no-op 소견 기록, 파일 변경 없음.
- 최종 검증: (1) DB-less 워크트리 전체 스위트 종료 코드 0(AC-001, AC-010), (2) 주 체크아웃 기준선 대비 신규 실패 0(AC-009), (3) `git status --short`로 의도 파일만 변경됐음을 증명.
- 파일 대상: `frontend/vite.config.ts`(조건부), 증거 문서.

## §G Anti-Patterns (금지)

1. `backend.deps`만 패치하는 오구현 — 라우터 모듈별 상수 복사 토폴로지(B1)를 무시한 수정.
2. RED 관측 없이 B4의 5건을 "아마 DB 문제"로 추정해 수정 — 관측된 트레이스백이 먼저다.
3. 예상 개수(21건 등)를 절대 상수로 SPEC/보고에 고정 — 기준선·실측 델타로만 서술.
4. 주 체크아웃에서 `Output/` 임시 이동으로 DB-less를 흉내 — 워크트리를 쓴다.
5. DB 복사 워크어라운드의 제도화 — 본 SPEC이 제거하려는 대상 자체다.
6. 손으로 옮겨 적은 테스트 개수·상수 검증 — 명세 블록 런타임 추출 또는 기준선 델타 비교.
7. grep 프로브를 필드명 등 명명 규약 축으로 수행 — 관측하려는 형태 자체를 대상으로 삼는다.

## §H Cross-References

- `SPEC-RS-REBALANCE-001` — 라이브 DB 재생성·워크트리 DB 부재 문제의 직전 사례 (v0.6.0 target, completed)
- 커밋 `5b8d8f5` — setuptools<81 근본 해소(본 SPEC과 별개로 이미 종료된 워크트리 함정의 절반)
- `SPEC-SECTOR-GRID-001` amendment — 되돌림 RED 관측 교훈(#9)의 출처
- `SPEC-THEME-DISPLAY-UNIFY-001` — 산문 계층 프로브 증거 교훈(#10)의 출처
- 프로젝트 메모리: `project_worktree_precommit_db_trap`, `feedback_vitest_root_picks_worktrees`, `feedback_cwd_trap_relative_paths`
