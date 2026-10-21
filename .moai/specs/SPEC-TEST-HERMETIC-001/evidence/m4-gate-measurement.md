# M4 — 게이트 실측 (REQ-007 / AC-007, AC-008)

## 1. 실측 조건

- 실행 위치: run 워크트리(cwd = `/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a54a6df6c5c4a1636`)
- `CLAUDE_PROJECT_DIR`를 unset한 상태로 실행(게이트의 프로젝트 디렉터리 결정 우선순위 1위가 이 변수라, 설정 상태로는 주 체크아웃을 잠조할 수 있어서다 — 커밋 시 훅은 셸 cwd 기준으로 실행되므로 워크트리 측정이 본 실측의 대상이다)
- 상세 모드: `moai gate --help` 실측 결과 플래그는 `-h --help`뿐 — **상세 모드 없음**(REQ-007의 "가능하면" 조건 불성립, 기록함)

## 2. 실행 결과 (verbatim)

명령: `unset CLAUDE_PROJECT_DIR && moai gate > <증거로그> 2>&1`

- 종료 코드: **0**
- stdout+stderr 출력: **0바이트** (성공 시 무출력 설계로 실측됨 — `moai gate silent exit 0 is ambiguous` 프로젝트 교훈 상황)
- 소요: 시작 1792566511 → 종료 1792566605 = **94초** (`date +%s` 전후 실측)

증거 로그: `.moai/state/verify/develop-hermetic/m4-gate-run3.log` (0바이트 그대로 보존 — 무출력 자체가 관측 결과다)

## 3. 관측된 단계 이름 목록 (AC-007)

게이트가 무출력이므로 단계 이름은 출력으로 관측되지 않고, 아래 2개의 실측으로
구성한다:

1. **설정 선언 단계**(`.moai/config/sections/gate.yaml` 실측): `gate.enabled: true`,
   `skip_tests: false`, timeouts `{vet: 30, lint: 60, test: 240}`,
   `ast_grep_gate.enabled: true`. `disabled_steps` 키 없음(전역 노브만 존재 —
   SPEC §2 조사 #5와 일치).
2. **실실행 추정(시간 실측)**: 94초는 워크트리에서의 pytest 전체 스위트 단독
   실행 시간(99.23s/98.42s, M1·최종 실행 실측)과 동일 상태다. Go vet/lint(이
   저장소에 Go 소스 없음)·JS/TS 스테이지가 돌았다면 시간이 유의하게 증가하거나
   실패했을 것이다.

**판정: Python test 단계가 트리거되어 통과(exit 0)**, 그 외 언어 단계는
트리거 근거가 관측되지 않았다. 94초 무출력 exit 0이 본 저장소에서의 게이트
정상 신호다.

## 4. JS/TS(vitest) 트리거 여부 (AC-008 분기 조건)

**판정: 미실행(no-op)** — 근거 3건:

1. 시간 실측: 94초 ≈ pytest 단독(§3-2). vitest 프론트 슈트 실행 시간이 가산됐을 리 없다.
2. 구조 실측: 저장소 루트에 `package.json`, `tsconfig.json`, 루트 `vitest.config.*` 모두
   부재(`ls` 실측 — No such file or directory 3건). JS/TS 마커는 `frontend/` 하위에만
   존재한다. 게이트의 언어 감지가 프로젝트 루트 마커 기반임을 고려하면 TS 감지가
   이루어지지 않는 것이 관측과 정합한다.
3. exit 0: 2026-08-19 전례(루트 실행 시 `.claude/worktrees` 수집 약 78건 오탐)가
   실제로 발생했다면 게이트는 실패(exit 1)했어야 한다.

→ **REQ-008의 Where 미실행 분기 적용: `frontend/vite.config.ts` 변경 없음(no-op)**.
루트 직접 실행 시의 수집 위험 자체는 여전히 존재하지만(전례 실측), 그것을 게이트가
실행하지 않는다는 것이 본 실측의 결론이며, 핀 추가는 후속 SPEC 후보로
`acceptance.md` §8 Forward-looking Checks 성격으로 남긴다.

## 5. 커밋 경로에서의 부합 확인

pre-commit 훅(`.git/hooks/pre-commit` 전문 실측 완료)은 (1) 스테이지드 Go 파일
있을 때만 gofmt+go vet — 본 SPEC은 Go 스테이징 없음 → 생략, (2) `moai gate` —
위 실측과 동일 경로. 즉 본 SPEC의 커밋은 DB-less 워크트리에서 허메틱 스위트의
GREEN(exit 0)으로 통과해야 하며, 이것이 본 SPEC의 종결 게이트(AC-001)와 정확히
일치한다.
