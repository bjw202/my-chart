# SPEC-SECTOR-METRIC-UNIFY-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- **작성 시각**: 2026-08-18
- **원본**: `.moai/plans/rs-purring-key.md` (사용자 승인 완료) — 본 SPEC은 전사이며 재기획이 아님
- **Tier**: L (분리 후에도 유지 — M0~M5 + M5.5로 마일스톤 7개, 대상 파일 backend 5 + 프론트 3(nullable 타입·사다리·차트) ≈ 10 → 임계 "≥3 milestone AND ≥10 files" 경계 충족. `tier: L`을 frontmatter에 선언해 도구가 읽을 수 있게 함)
  - Tier L 표준 산출물 중 `research.md` / `design.md`는 **별도 작성하지 않음** — 조사·설계 판단이 승인된 원본 계획에 이미 확정돼 있고, 그 결정은 plan.md §A(핵심 결정 표)와 §B(순서 근거)로 전사됨. 중복 문서를 만들지 않는다
- **산출물**: spec.md / plan.md / acceptance.md / progress.md
- **SPEC ID 정규식 자체 검사**: 실행 완료 — `PASS`
  ```
  ID="SPEC-SECTOR-METRIC-UNIFY-001"
  [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
  → PASS
  ```
- **ID 충돌 검사**: `.moai/specs/`에 `METRIC-UNIFY` 매칭 없음 → `NO_COLLISION`
- **미변경 트리에서 실측해 AC에 리터럴로 고정한 스캔 기준선**:
  | 스캔 | 관측 출력 (2026-08-18, 미변경 트리) | AC |
  |---|---|---|
  | `grep -c 'compute_sector_bubble' backend/services/sector_advanced_service.py` | `3` | AC-SMU-012 (목표 `0`) |
  | `grep -c 'envelope_fields' backend/services/sector_advanced_service.py` | `0` | AC-SMU-010 (목표 `1` 이상) |
- **미해결 갭(고의로 미해결로 남김)**: G-1(고정 픽스처의 결측 종목 충분성), G-2(`VolumeWon` 3M 커버리지), G-3(`PERIOD_SIZE_LADDER` 재산출 필요 여부) — plan.md §E 참조. AC가 이 가정들이 성립한다고 전제하지 않는다
- ~~REQ 26건 / AC 27건~~ → 분리 후 수치는 아래 `audit_iteration_1` 참조

## §E.1.1 audit_iteration_1 — plan-auditor FAIL 0.71 → 대응 (2026-08-18)

**감사가 클리어한 판단 (재논의 금지)**: 두 정적 스캔 리터럴 독립 재현 확인, 전사 충실도 high(누락·약화·창작 0), AC-SMU-002(b) 동등 게이팅 논리, AC-SMU-018 측정 게이트 구조와 "재산출 필수" 단정에 대한 회의, AC-SMU-016 양변 출처 요건, G-1/G-2 갭 규율(E-5가 실패 분기를 명시적으로 처리), `research.md`/`design.md` 생략의 문서화된 부채 처리.

| 결함 | 등급 | 처분 |
|---|---|---|
| **D1** — AC-SMU-001/008이 비교 배열 미지정으로 실현 불가 | BLOCKING | **수정 완료.** 우변을 봉투 `data[]`의 **필드 경로**로 확정(`data[j].rs_avg.value` / `excess_returns["<p>"].value` / `trading_value["<p>"].value` / `returns["<p>"].value`). 20/29 기준선을 같은 배열 쌍 기준으로 재기술. 레거시 `sectors[]` 제외 근거 2건(모델에 `trading_value` 부재 / `excess_returns`가 정의 A라 §5 M8이 상수 차이를 설계상 잔여로 명시) 명기. 계획서 원작자도 자기 결함으로 인정 |
| **D2** — frontmatter `tags` 타입 불일치 | BLOCKING | **수정 완료.** `tags` 문자열화, `version` 인용, `related_specs` → `depends_on` |
| **D3** — REQ-SMU-020/013 무-AC | BLOCKING | **부분 수정.** REQ-SMU-013 → **AC-SMU-028 신설**(스칼라-또는-null 단언), REQ-SMU-011 프론트 타입 → **AC-SMU-029 신설**. REQ-SMU-020(색 램프)과 REQ-SMU-016(8개 호출부)은 프론트 SPEC으로 이관되어 **AC-SDU-005 / AC-SDU-001**에서 커버 |
| **D4** — `date` 출처 오진 + 진짜 결함(`if date:` 가드 누락) | SHOULD-FIX | **수정 완료.** 출처를 `sector_advanced_service.py:57`로 정정, `:131` 선례의 진리값 가드 이식을 plan.md M4에 코드 형태로 명시, **E-6 엣지 신설**(빈 date → 200 + 빈 `sectors[]`, 503 아님) |
| **D5** — "위치 인자 4건" 미검증·과소 집계 | SHOULD-FIX | **수정 완료.** 실행 스캔으로 교체, 관측 출력을 REQ-SMU-008에 리터럴 고정. `tests/test_consumer_dates.py:438` 누락 보정 → 단일 위치 인자 호출 **3곳** 확정 |
| **D6** — `tier:` frontmatter 부재 | SHOULD-FIX | **수정 완료.** `tier: L` 선언 |
| **D7** — REQ/AC 예산 초과 | — | **결정 A 반영: M6/M7을 `SPEC-SECTOR-DISPLAY-UNIFY-001`로 분리.** 본 SPEC 범위 = M0~M5 + M5.5 + M8 기록 |
| **D8** — `grep -c` 종료코드 함정 | SHOULD-FIX | **수정 완료.** acceptance.md 상단 규약에 [HARD]로 1회 기록(`|| true` + stdout 파싱, 종료코드를 판정에 쓰지 않음) |
| **D11** — `compute_rank_change=False` 누락 | MINOR | **수정 완료.** M4 호출에 명시(기본 `True`는 `anchor(t,28)` 1단 재귀 재집계를 유발하는데 버블은 `rank_change`를 소비하지 않음). 투영 원천 컨테이너를 `result.aggregates`로 명기 |
| **D9 / D10** | MINOR | **run-phase 기계 사항으로 기록.** G-6은 프론트 SPEC(G-F1)으로 이관, **G-7 신설**(순서 술어 `git merge-base --is-ancestor` + "프로덕션 파일 0개"의 경로 필터 정의) |

**분리 후 예산 (Tier L, 25/25)**

| SPEC | Tier | REQ | AC |
|---|---|---|---|
| SPEC-SECTOR-METRIC-UNIFY-001 (본 SPEC) | L | 18 | 22 |
| SPEC-SECTOR-DISPLAY-UNIFY-001 | M | 11 | 13 |

- 본 SPEC REQ: 001~015, 023, 025, 026 (016~022·024는 tombstone, 번호 재사용 금지)
- 본 SPEC AC: 001~015, 018, 022, 025~029 (016·017·019~021·023·024는 tombstone)
- **예외 잔류**: `PERIOD_SIZE_LADDER` 재산출(REQ-SMU-023 / AC-SMU-018 / M5.5)은 프론트 파일이지만 M4 완결 조건이므로 본 SPEC에 잔류. 프론트 SPEC으로 미루면 백엔드만 머지된 구간에서 모든 버블이 한쪽 끝으로 뭉친 채 배포된다

## §E.1.2 audit_iteration_2 — plan-auditor PASS-WITH-DEBT 0.85 → 델타 대응 (2026-08-18)

Δ +0.14 (0.71 → 0.85), Tier L 임계 0.85 정확히 충족. must-pass 7건 전부 통과, iter-1 결함 11건 중 9건 완전 해소.

**감사가 인정한 것 (재논의 금지)**: tombstone 방식(15개 행의 목적지 식별자가 형제 SPEC에 전부 실재 — 재번호했으면 살아남은 AC↔REQ 간선이 조용히 재지정됐을 것), D1의 `MetricValueModel` 비대칭 처리(우변만 `.value`, 좌변은 bare scalar), M5.5 사다리 예외의 4곳 배치 일치 + DoD 등재로 "행동하지 않음으로는 소진 불가능", D11 인용 검증.

| 결함 | 등급 | 처분 |
|---|---|---|
| **D-1** — AC-SMU-001 "20/29" 기준선 무귀속 | BLOCKING | **수정 완료(권장안 채택).** 리터럴을 버리고 RED 목표를 **M0가 고정한 `N`**으로 전환. AC-SMU-002와 같은 M0 조정 절 신설: `N≠20`이어도 결함 아님(20은 미상의 배열 쌍에서 나온 참고값), **`N==0`이면 즉시 blocker**(전제 붕괴 → 동어반복). DoD에 측정 항목 추가 |
| **D-2** — E-6 되돌림 반증 불가 | BLOCKING | **수정 완료.** 2분기 **측정 게이트**로 재작성(AC-SMU-018 G-3와 동형). 분기 A(즉시 예외) 구별 관측량 = HTTP status 200 vs 503, 분기 B(조용한 빈 결과) 구별 관측량 = **봉투 `excluded[]` 길이**(가드 있음 0 / 없음 전 섹터 `no_members` 등재). 갭 **G-8** 신설 + DoD 등재 |
| **D-3** — `§4.4` 중복 | BLOCKING | **수정 완료.** 두 번째를 `§4.5`로 |
| **D-4** — ThemeAnalysis 항목이 떠난 M6 참조 | BLOCKING | **수정 완료.** `SPEC-SECTOR-DISPLAY-UNIFY-001`(G-F2) 지시로 교체 — plan.md G-4와 정합 |
| **D-5** — `types/bubble.ts:6-8` (4개 필드는 `:6-9`) | BLOCKING | **수정 완료.** `:6-9`로 정정 + 왜 어긋났는지 각주. 실측 확인: `excess_return :6` / `rs_avg :7` / `trading_value :8` / `period_return :9` |
| **D-6/7/8** — 인용 3건 | optional | **수정 완료.** `if date:` `:131`→**`:136`**, `date=` `:57`→**`:58`**, 라우터 `:88`→**`:89`**(REQ-SMU-008 실측 스캔과 일치). 전부 소스 재확인 |
| **D-9** — AC 역참조 부재 | optional | **수정 완료.** AC-SMU-015 → REQ-SMU-012, AC-SMU-027 → REQ-SMU-026 |

## §E.1.3 audit_iteration_3 — plan-auditor PASS 0.92 → 잔여 2건 정리 (2026-08-18)

Δ +0.07 (0.85 → 0.92), Tier L 임계 0.85. **0.71 → 0.85 → 0.92 단조 상승, 세 iteration 내내 정체된 결함 0건.** D-1~D-9 전부 해소 확인. **감사 iteration 예산 3/3 소진 + 판정 PASS → 4회차 감사 없음.**

**감사가 소스 대조로 인정한 것 (재논의 금지)**: D-1이 닫힌 결정적 요소는 **`N == 0` 바닥**(단순 "M0에서 재라"였으면 M0가 0을 낼 때 조용히 동어반복으로 퇴화 — 실패값을 선언해 게이트로 만든 것이 차이). 원 조사의 우변 배열 기록 부재를 덮지 않고 명시한 것도 VCI §2 기준 옳은 처리. D-2 분기 B 관측량이 실제로 판별함 — `sector_metrics.py:833` `excluded.append(ExcludedSector(sector_name, "no_members", 0))` → `SectorAggregationResult.excluded`(`:248`, `:875`) → `envelope_fields(excluded=...)`(`envelope.py:247`) → `excluded_models(...)`(`:269`). 인용 수정 4건(`:136`, `:58`, `:89`, `bubble.ts:6-9`) 및 §4.4→§4.5 재번호가 고아 상호참조를 만들지 않음도 확인.

| 결함 | 처분 |
|---|---|
| **D-A** — `acceptance.md` AC-SMU-001의 "왜 항진명제가 아닌가"가 stale ("되돌림이 **기준선 20건**을 재현한다는 사실이 **실측돼 있다**") — 여섯 줄 위의 D-1 수정("20은 이 배열 쌍으로 측정된 적 없음")과 정면 충돌하며, 폐기된 미귀속 주장을 *실측이라고* 재단언 | **수정 완료.** 불릿을 **두 갈래로 분리**: (1) **구조적 근거(지금 성립)** — 양변이 서로 다른 엔드포인트·서로 다른 서비스 모듈(`sector_advanced_service.py` vs `sector_ranking_service.py`의 `agg.aggregates`)에서 오며 한쪽 헬퍼 2회 호출 형태가 아님(lessons #9), (2) **경험적 근거(M0에서 확정)** — 되돌림이 **M0 고정 `N`건**을 재현하며 `N`은 여기서 실측으로 주장하지 않고 `N==0`이면 blocker. 숫자 20은 이 불릿에서 완전히 제거 |
| **D-B** — M4 스케치가 `aggregates = []`만 초기화하고 **`excluded` 미바인딩**. M5가 `envelope_fields(..., excluded=result.excluded)`로 배선하는 순간 가드 거짓 시 `NameError` → 라우터 포괄 핸들러가 **503**으로 변환 = E-6이 막으려던 바로 그 결과. 동시에 분기 B 필수 관측량("가드된 경우 `excluded[]` 길이 0")도 성립 불가 | **수정 완료.** 스케치에 가드 밖 `excluded = []` + 가드 안 `excluded = result.excluded` 추가. "가드 밖 초기화는 스타일이 아니라 E-6의 전제"임을 [HARD]로 명시하고, 두 이름의 초기값이 곧 E-6 기대 상태를 만든다는 대응(`aggregates=[]`→빈 `sectors[]`, `excluded=[]`→봉투 `excluded[]` 길이 0)을 기록. M5 마일스톤에도 `excluded=excluded` 전달을 명시 |

---

## §E.1.4 run 단계 인계 — debt 처분표 [HARD]

> **run 세션이 읽을 유일한 인계 문서다.** 아래 항목은 전부 이미 acceptance.md DoD에 등재돼 있다.

| # | debt | 처분 시점 | 실패 시 조치 |
|---|---|---|---|
| **AC-SMU-001 `N`** | `sectors[]`↔봉투 `data[]` 쌍으로 불일치 건수 `N`을 측정해 **M0 커밋에서 리터럴 고정** | **M0** | **`N == 0`이면 SPEC 중단 + blocker 보고** — 두 경로가 갈린다는 전제가 무너진 것이고 AC가 동어반복이 된다 |
| **G-1** | 고정 픽스처 `tests/fixtures/frozen/aggregation-2026-08-11`에 결측 경로를 태울 RS 결측 종목이 충분한지 확인 | **M0 킥오프** | 부족하면 합성 DB(`backend/tests/test_sector_advanced.py:19-147` 관용)로 전환 |
| **G-2** | `daily.db`의 `VolumeWon`이 3M 창을 덮는지 확인 | **M0 킥오프** | 부족하면 합성 DB 전환 + 3M 거래대금 AC를 합성 픽스처 기준으로 재기술. E-5가 실패 분기를 이미 명시 |
| **G-8** | E-6 빈 `date` 분기(A 즉시 예외 / B 조용한 빈 결과) 확정 — **실측 1회** | **M4 착수 전** | **분기 B로 판명되면 `excluded[]` 길이 관측량 필수**(status는 양쪽 200이라 판별 불가). 관측 출력을 progress.md에 verbatim 기록 |
| **G-3** | `PERIOD_SIZE_LADDER` `vMin`/`vMax`가 M4 이후 실제 거래대금 분포를 담는지 **측정** | **M4 직후 (M5.5 게이팅)** | 벗어나면 재산출. 측정 없이 바꾸지도 그대로 두지도 않는다 |
| **G-5** | 커버리지 측정 형태 — `pytest --cov`는 이 프로젝트에서 `ImportError: numpy`. 동작 형태는 `coverage run --source=my_chart,backend -m pytest <files>` → `coverage report` | **run 시작** | — |
| **G-7** | AC-SMU-025 순서 술어 명령 확정 — `git merge-base --is-ancestor <M0_SHA> <M4_SHA>` + "프로덕션 파일 0개"의 경로 필터 정의(`tests/`·`backend/tests/` 밖 0개) | **run 시작** | — |

- audit_iteration_4: **PASS 0.95** (2026-08-18, run-gate Phase 1 delta re-audit — iteration 3 verdict 후 D-A/D-B 편집이 있어 sticky-cache 3조건의 hash-unchanged 미충족 → 계약상 재심사 1회) — D-A(AC-SMU-001 항진명제 근거 두 갈래 분리 + 숫자 20 완전 제거)·D-B(plan.md M4 excluded 가드 밖 초기화 + M5 excluded=excluded 배선) 전부 RESOLVED, 델타 회귝 CLEAN, must-pass 7/7. 단조 상승 0.71→0.85→0.92→0.95. run debts(N·G-1/G-2·G-8·G-3·G-5/G-7)는 plan 결함이 아닌 run-phase 측정 게이트로 확인.
- audit_verdict: PASS
- audit_report: .moai/reports/plan-audit/SPEC-SECTOR-METRIC-UNIFY-001-review-4.md
- audit_at: 2026-08-18

## §F Phase 4 Mode Selection

Input parameters:

| 파라미터 | 값 |
| --- | --- |
| tier | L |
| scope (files) | ≈10 — backend 5 (`sector_advanced_service.py` · `routers/sectors.py` · `schemas/sector_advanced.py` · `sector_metrics.py`(원천, 읽기) · 테스트 3종 신설) + 프론트 3 (`types/bubble.ts` · `bubbleRadius.ts` · `SectorBubbleChart.tsx` 소비 확인) |
| domain count | 2 (backend Python 집계 + frontend TS 타입·사다리) — 단 M0→M5.5 순서 강제(§B)로 상호 의존 |
| file language mix | Python + TypeScript |
| concurrency benefit | LOW — coding-heavy + 엄격한 순서 의존 (M0 선행·M4만 수치 변경) |
| Agent Teams prereqs | N/A (Mode 3 RETIRED) |

Mode evaluation:

| Mode | Selected | Rationale |
| --- | --- | --- |
| 1 trivial | no | Tier L, AC 22종 |
| 2 background | no | write-capable — 마일스톤 순서 게이팅 필요 |
| 3 agent-team | RETIRED | tombstone |
| 4 parallel | no | M0→M1→…→M5.5 순차 의존이 load-bearing(§B-1/B-2) — 팬아웃 불가 |
| 5 sub-agent | **YES** | 순차 마일스톤 실행; manager-kanban 진입 판정(≥3 milestones AND ≥10 files)은 경계 충족이나 "cross-domain fan-out" 조건 불충족 — 순서 강제 + 스폰 불안정 환경(GLM 하위 컨텍스트 사망 패턴, memory 기록)에서 단일 순차 위임이 최소 위험 |
| 6 workflow | no | semantic/new-code 작업 — 기계적 단일 변환 아님 |

Decision: sub-agent (Mode 5) — sequential manager-develop delegations per milestone (다이어트 스폰; 2회 사망 시 orchestrator-direct 폴백 질의 — 세션 검증 패턴)

Justification: M0 특성화의 단독-선행-커밋 제약(REQ-SMU-025)과 "M4만 숫자를 바꾼다"는 국소화 계약(REQ-SMU-026)이 전체를 직렬로 강제한다. Anthropic 코딩-과제 병렬성 경고가 적용되며, 이 세션의 스폰 불안정 이력(3회 autocompact 사망·회복)은 팬아웃이 아니라 순차 최소 스폰을 지시한다.

Mode 6 confirmation: N/A (Mode 5 — Implementation Kickoff Approval은 lead 세션 승인 완료)

### §F.1 G-7 술어 확정 (run 착수 시 — DoD 항목)

- **순서 술어**: `M0=$(git log --format='%H' --diff-filter=A -- backend/tests/test_bubble_characterization.py | tail -1)` → `git merge-base --is-ancestor "$M0" "$M4"; echo $?` — **exit 0**이어야 함 (`| tail -1`은 복수 커밋 방어; M0은 신설이므로 1건 예상)
- **프로덕션 파일 0개 술어 (경로 필터 정의)**: `git show --name-only --format= "$M0" | grep -v '^tests/\|^backend/tests/' || true` — **출력 0줄**이어야 함 (grep -v 후 빈 출력 = 전부 테스트 경로)
- 실행 시점: M4 커밋 확정 후 AC-SMU-025 판정에서. 관측 출력 verbatim §E.2 기록

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
