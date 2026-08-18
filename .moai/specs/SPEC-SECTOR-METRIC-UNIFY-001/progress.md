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

### G-8 빈 date 분기 실측 (M4 착수 전, 2026-08-18) — **분기 A 확정**

방법: 임시 스크립트로 `compute_sector_aggregates(<frozen weekly.db>, "", daily_db_path=<frozen daily.db>, as_of="", compute_rank_change=False)` 직접 호출 1회 (관측 후 스크립트 삭제).

```text
BRANCH A — raised:
  ValueError: Invalid isoformat string: ''
    grid = compute_weekly_grid(weekly_db_path, as_of or date)
  File "my_chart/analysis/weekly_grid.py", line 98, in compute_weekly_grid
  File "my_chart/analysis/weekly_grid.py", line 104, in _compute_cached
    as_of_d = date.fromisoformat(as_of_str)
ValueError: Invalid isoformat string: ''
```

- **판정: 분기 A (즉시 예외)** — `compute_weekly_grid`의 `date.fromisoformat("")`가 `ValueError`를 던진다. 가드 없이 빈 date가 들어가면 라우터 포괄 `except Exception`(routers/sectors.py:90-94)이 **503**으로 변환.
- **E-6 되돌림 관측량: HTTP status (가드 있음 200 + 빈 sectors[] / 가드 없음 503)** — acceptance.md E-6 게이트 규정에 따라 분기 A이므로 **status 단언만으로 충분**하며, 봉투 `excluded[]` 길이 관측량(분기 B 전용)은 불필요.
- M4의 `if date:` 가드(:136 종목버블 선례 이식)가 E-6의 기대 상태(200 + 빈 `sectors[]`)를 만든다.

### M0 특성화 (커밋 6aabf81)

- G-1/G-2: frozen 경로 채택 — 방산 18중 2결측(spec 예상과 일치)·조선 17중 3결측(개수 일치, 분모는 참고치 30과 상이하나 결측 경로 실증에 무관)·헬스케어 11결측 최대. daily.db VolumeWon [2026-05-08, 2026-08-11] 65거래일 21,140행 NULL 0 — 3M 앵커 완전 커버.
- **N=18** (9조합 전부 sectors[] 전원 불일치, 4필드쌍 전부). bubble-only(봉투 AG-5 미달 제외): kospi {디스플레이,스마트폰,패션} · kosdaq {패션} · all ∅. 봉투쪽 returns/excess null(reason 기입): all {패션,헬스케어} · kosdaq {헬스케어} — M3 nullable 입력으로 리터럴 고정. 결정론: 스냅샷 2회 실행 byte-identical.
- 테스트 21개 (특성화 9 + 불일치 N 9 + 봉투 null 3) — 손대지 않은 트리 GREEN, 단독 커밋.

### M1 RED (커밋 3cb3828)

- parity 30 blocks + exclusion 3 blocks: **11 failed / 22 passed** — 파리티 9조합 RED (N=18·per-pair 18·BUBBLE_ONLY 관측 M0과 정확히 일치), 결측 제외 2 RED (부분결측 현재 52.0/목표 65.0, 전체결측 현재 0.0/목표 None).
- 항진명제 자체 해결 1건: 봉투는 3기간을 전부 싣으므로(AC-SAG-036) 고정 inner 키 비교는 절대 다를 수 없음 → **요청 기간 p의 키**를 비교하도록 수정해 동반 단언이 실배선을 증명.
- M0 21 GREEN 재확인. status: draft → in-progress (M1 커밋).

### M2 배선 (커밋 d96ade6)

- +4/−1: `daily_db_path: str | None = None` 키워드 기본값 + 라우터 `daily_db_path=DAILY_DB_PATH` 전달. 위치 인자 호출 3곳 무변경 (호환 36 passed).
- 게이트: M0 21 GREEN · M1 11 RED 불변 — 동작 불변 관측.

### M3 nullable 스키마 (커밋 d16cb65)

- `SectorBubbleItem` 4필드 `float | None` + `types/bubble.ts` `number | null` 동시 확장. MetricValueModel 미탑재 가드·실응답 스칼라 관찰 신규 6 GREEN.
- 게이트: M0 21 GREEN · M1 11 RED 불변 · tsc exit 0 (파일 리다이렉트 관측) · eslint src/types 0.

### M4 전환 (커밋 8f0a0c7) — 수치가 바뀐 유일한 단계

- N=18→0 (전 섹터·4필드쌍 일치). 대표 델타 (frozen 2026-08-11 관측): 방산 1w/all rs_avg 48.16→54.18 · 거래대금 주봉 1개 close×volume → VolumeWon 기간 누적 · 결측 rs_avg 0-대체 → 가용 평균/None.
- 구현: `if date:` 가드 + `excluded` 가드 밖 초기화 [HARD] + `compute_rank_change=False` + 투영 4필드 + deprecation docstring + 서비스 참조 제거(스캔 3→0) + E-6 엣지(200+빈 sectors[]) + M0 특성화 뒤집기(불일치 N=18 → 일치 0) + AC-SMU-015 집합 관찰자.
- 게이트: parity+exclusion 33 · characterization+edge 22 · 계약 21 · consumer 46 전부 GREEN.
- **blocker 1건 (사용자 승인 해소)**: 파티션 계약 테스트(`kospi+kosdaq == all` 등식)가 AG-5 시장별 멤버십 적용으로 구조적으로 깨짐 — M4 의도 변경의 직접 귀결이나 plan §D 미등재였음. 재기술(양쪽 존재 엄격 등식 + 한쪽만 존재 < all + (a)집합 최소 1개) + §D 런타임 등재로 M4 커밋에 포함.
- 경과: 스폰이 blocker 보고 후 idle 사망 → orchestrator가 재기술·게이트 재실행·커밋 마무리.

### M5 봉투 정상화 (커밋 3d06d9d)

- `envelope_fields` 전환 + `excluded=excluded` 배선 + `market_filter` 요청 반영(D4 해소). 레거시 4키는 EnvelopeMixin 상속 구조로 자연 공존. 스캔 `envelope_fields` 0→5 (AC-SMU-010 ≥1 충족).
- 게이트: 33+22+21+46 = 122 passed 전부 — 섹터 값 불변.

### M5.5 사다리 정합 (G-3 측정 → 재산출, 사용자 승인)

**측정 (frozen fixture, post-M4, all 시장 18섹터, 2026-08-18 관측):**

```text
period  min         p5          p50         p95         max          | 기존 사다리 [vMin,vMax]      | 판정
1w      2.201e+03   3.581e+03   1.932e+04   1.837e+05   9.414e+05    | [1e10, 1e12]  | p5 < vMin VIOLATION
1m      4.906e+03   1.101e+04   5.768e+04   7.346e+05   3.963e+06    | [5e10, 5e12]  | p5 < vMin VIOLATION
3m      3.617e+04   4.435e+04   2.733e+05   3.197e+06   1.508e+07    | [1e11, 1e13]  | p5 < vMin VIOLATION
→ 반지름 고유값 전 기간 1종 [7.0] — 전 버블 rMin 클램프 (AC-SMU-018 위반)
```

**근거 확정 — VolumeWon 단위 = 억원**: 삼성전자/SK하이닉스/에코프로비엠 실측 `close×volume / VolumeWon` ratio = 1.00e8 공히 (2026-08-14). fixture와 라이브 DB의 하루 VolumeWon 총합도 동일 차수(e5) — fixture가 축소 샘플이 아니라 실제 스케일 반영. 기존 사다리(e10~e13)는 구 산식(원 단위 close×volume) 기준 상수였고, M4의 VolumeWon 전환으로 1e8 단위 격차 발생 — D3 "약 2.5e7배 차이"의 정체.

**구조 충돌 발견 + 사용자 결정**: `PERIOD_SIZE_LADDER`는 섹터·종목 두 차트가 공유하는 VZ-1 앵커인데 종목 버블은 여전히 원 단위. **섹터 전용 사다리 신설 채택** — 종목 버블 무변경, 단위 통일은 SPEC-SECTOR-DISPLAY-UNIFY-001로 이월.

**재산출 + 해소:**
- `SECTOR_PERIOD_SIZE_LADDER` 신설: 1w [1e3,1e6] refs [1e3,3e4,1e6] / 1m [5e3,5e6] refs [5e3,1.5e5,5e6] / 3m [1e4,1e7] refs [1e4,3e5,1e7] (억원). `sizeLegendRefs`에 ladder 파라미터 추가(기본값 기존 호환).
- **M4 표시 회귀 해소**: `formatTradingValueEok`가 원 단위 입력 가정(`v/1e8`)이라 억원 trading_value가 범례·툴팁에서 `0억`으로 렌더되던 것을 섹터 차트 호출부 원 복원(`v×1e8`) 래퍼로 수정 — M5.5 측정이 폭로한 M4 숨은 회귀.
- 재검증: **p5≥vMin OK / p95≤vMax OK 전 기간 · 반지름 고유값 17/18/15종** (게이트 3종+ 충족). SectorAnalysis 250/250 GREEN · tsc 0.
- m5.test(AC-SUX-039) 참조 리터럴 갱신 (1W 1,000억/3조/100조 · 3M 1조/30조/1,000조) + §D 런타임 등재.
- 유의: refs 표기 스케일(3m 최대 참조 1,000조)은 frozen fixture(대형종목 편중 샘플, 하루 총합이 라이브의 ~50%) 기준 — 라이브 배포 후 첫 주에 실측 분포 대비 재확인 권고.

### 되돌림 실증 배치 (AC 22종 판정, 2026-08-18, orchestrator 직접 관측)

방법: 주입(임시 편집/M3 파일 교체) → 대상 테스트만 실행 → RED tail 확보 → cp 백업 복원 → `diff -q` 바이트 동등 확인. 전 사이클 복원 증명 완료.
**2026-08-18 review 재작업**: 004/008 행 신설, 028/029 행 교정 — verbatim 증거는 아래 "review 차단 재작업" 절 + `.moai/state/verify/run-tjvce8-smu001/`.

| AC | 되돌림 | 관측된 RED |
|---|---|---|
| 001 | service를 M3(d16cb65) 상태로 교체 | 파리티 9조합 전부 FAILED — **N=18 재현** |
| 002a/007 | sector_metrics L450 결측 제외 → 0-대체 | exclusion 2 failed (분모 10 복귀·전원결측 0.0) |
| 006 | L529 `rs_avg or 0.0` 주입 | all_missing 1 failed |
| 003 | rs_avg 투영 → `a.excess_returns[p].value` 오염 | period_invariance 3 failed |
| **004** | `sector_metrics.py:846` excess 산출 기준 -1.0p 이동 주입(보고 벤치마크 유지) | `test_excess_identity_envelope` **9 failed** — 항등식 위반 전 9조합 *(2026-08-18 재작업 신설)* |
| **008** | 서비스 M3(d16cb65) 교체 — AC-001과 동일 기법 | 파리티 **9 failed** — `per_pair={'trading_value': 18,…}` + `bubble=1514051627310.0 envelope=42919.6`(≈3.5e7배 규모차 실증) *(2026-08-18 재작업 신설)* |
| **009** | `market_filter="all"` 하드코딩 | **보강 후 6 failed** — 최초 관측 시 9 passed로 **관측자 결함 폭로**: envelope_contract가 랭킹(우변)만 검사하고 버블(AC 대상) 미검사 → 버블 market_filter 단언 추가(영구 보강) 후 RED 확보 (kospi/kosdaq 6조합) |
| 010 | M3 상태 | 스캔 `envelope_fields` = 0 |
| 011 | 스키마에서 market 필드 제거 | `test_backward_compatible_legacy_keys_preserved` 1 failed |
| 012 | M3 상태 | 스캔 `compute_sector_bubble` = 3 |
| 013 | `compute_sector_bubble` 함수명 삭제 | test_sector_advanced 7 failed (transitions/overview 경로 붕괴) |
| 014 | `daily_db_path` 위치 필수화 | sag_037+consumer_dates 8 failed |
| 015 | `MIN_SECTOR_MEMBERS` 5→20 | characterization 12 failed (소형 섹터 소실·집합 붕괴) |
| 018 | SECTOR ladder vMax→1e3 | 반지름 고유값 **1종 [24.5]** (u=0.5 상수 분기) — 게이트 ≥3 위반 관측 |
| 022 | 컴프리헨션에 null rs_avg 드롭 조건 | all_missing(not-dropped) 1 failed |
| 028 | 스키마 `rs_avg: MetricValueModel` 주입 | **3 failed** — 어노테이션 관찰 2종(유니온 아님·BaseModel 탑재) + live 관찰(pydantic 검증거부 → 503 래핑). **재수립(2026-08-18)**: 종전 "`rs_avg=a.rs_avg` 주입 → live 1 failed" 증거는 B1 붉은 상태에서 측정돼 주입 전후 동일 실패 — 판별력 0으로 폐기 |
| **029** | TS `number`로 되돌림 | 캐스트 제거 후 재측정 — `tsc -b` **신규 5 오류**(m5:65·m5:144·m7:93×2·m7:94) RED 관측 → **Gaps 폐지, PASS 재판정** *(2026-08-18 재작업)*. 종전 "tsc exit 0"은 루트 tsconfig `files: []`로 0파일 검사한 공허 관측이었음 |
| 025 | G-7 술어 실행 | `merge-base --is-ancestor 6aabf81 8f0a0c7` exit 0 ✓ · M0 경로 필터 후 프로덕션 **0줄** ✓ |
| 026 | 마일스톤별 관측 기록 소비 | M1/M2/M3 시점 특성화 21 GREEN(각 보고) · **M4 커밋에서만 뒤집힘**(flipped 22 GREEN 관측) — 국소성 성립 |
| 027 | plan §F 전 구간 | root `-k` 스위프 **254 passed** · 프론트 전체 **81 files / 722 tests GREEN** · `cd backend && pytest tests/ -k …` 컬렉션 오류 2건 — `db_service.py` import 실패로 **본 SPEC 무관 pre-existing** (커밋 범위 내 db_service/weekly 변경 0건 · 오류 파일 최종 터처 = SPEC-SECTOR-AGGREGATION-001/GRID-001) |

**커버리지 (G-5): Gaps** — 라이브 venv(`/Users/byunjungwon/Dev/my_chart/.venv`)에 `coverage` 미설치 (`No module named coverage`). 무단 설치 대신 미측정 사유 명시. 측정 형태는 lessons #9 동작 형태로 확정돼 있음 — 도구 설치 후 sync 단계 보측 가능.

### review 차단 재작업 (2026-08-18, run-tjvce8 — 리드 지시 5건 처분)

**B1 — `test_bubble_schema_nullable.py` 단언 완화 (M3 docstring 예고 적용)**
- 완화 근거: AC-028의 M3 결정은 스키마 4필드를 `float | None`로 선언했고 M4가 결측(패션·헬스케어)을 null로 유입시켰다. 스칼라-only 단언은 그 계약과 충돌 — 관측자는 구현이 아니라 계약을 따라야 한다.
- 픽스처 관측 고정(1w/all, frozen, 프로브 1회): `period_return`/`excess_return` observed_types={NoneType,float}, null={패션,헬스케어} · `rs_avg`/`trading_value` {float}, null=∅.
- 수정: 딕트 배제 단언 유지 + `float|None` 허용 + **필드별 null 섹터 집합을 픽스처 관측치로 양방향 고정**(null 확산·소실 모두 RED).
- 관측: 수정 전 `1 failed, 5 passed`(패션.period_return None) → 수정 후 `6 passed`.

**AC-028 되돌림 재수립 (기존 증거 폐기 — 판별력 0)**
- 재실증 사이클(cp 백업 → 주입 → 관측 → 복원 → `git diff` 빈): 스키마 `rs_avg: MetricValueModel` 주입 → **`3 failed, 3 passed`**:
  ```
  AssertionError: rs_avg: 어노테이션이 유니온이 아니다 — <class 'backend.schemas.envelope.MetricValueModel'>
  AssertionError: rs_avg: BaseModel 서브클래스(MetricValueModel) 탑재 — MetricValueModel 포함 AC-SMU-028 위반
  AssertionError: {"detail":{"error":"weekly_db_not_ready", … "Input should be a valid dictionary or instance of MetricValueModel … input_value=69.29…"
  ```
  복원 후 `6 passed`. 증거: `pytest-ac028-rollback.txt`.

**B2 — `sectorReturnColor` null 분기 + tsc 오류 해소**
- `sectorReturnColor(periodReturn: number | null)` — null → 결측 전용색 `#4B5563`(gray-700). 중립(0%) `#9CA3AF`(gray-400)과 구분 — 결측 섹터가 보합과 같은 색으로 렌더되던 회귀 해소. 점선 테두리(VZ-3)의 결측 의미 확장은 표시 소관 형제 SPEC(SPEC-SECTOR-DISPLAY-UNIFY-001) 영역으로 남김(색 채널만 고정).
- 관측자 신설: m5.test "period_return:null → 결측 전용색"(결측 ≠ 보합 색상 단언, 렌더+직접 호출 2경로).
- `tsc -b` 관측: 오류 **30건 → 29건**(SPEC 귀속 1건 해소 — `SectorBubbleChart.tsx(124,77) TS2345`). 잔여 29건 전부 무관 pre-existing.

**AC-029 관측자 복원 (캐스트 제거 + 되돌림 RED 실측) → Gaps 폐지·PASS 재판정**
- 이중 캐스트 제거: `SectorBubbleChart.m5.test.tsx:65`(trading_value 1건) + `MetricTextParity.m7.test.tsx:93-94`(excess_return·rs_avg·period_return 3건) — 픽스처가 정직한 null을 담는다. `er2-screens`/`StockBubbleChart.m5` 캐스트는 비-SectorBubbleItem 타입(SectorRankItem·StockBubbleItem)이라 미대상.
- 되돌림 실측: `types/bubble.ts` 4필드 `number` 임시 복원 → `tsc -b` 오류 **34건 = 29 pre-existing + 신규 5**:
  ```
  MetricTextParity.m7.test.tsx(93,23)(93,44)(94,30): error TS2322: Type 'null' is not assignable to type 'number'.
  SectorBubbleChart.m5.test.tsx(65,48)(144,41):      error TS2322: Type 'null' is not assignable to type 'number | undefined'.
  ```
  복원 후 29건·`git diff` 빈(바이트 동등). 증거: `tsc-b-ac029-rollback.txt` / `tsc-b-after-fix.txt`.
- 관측자 복원 판정 근거: 타입을 되돌리면 캐스트 제거 픽스처 4곳 + 신설 B2 관측자 픽스처 1곳에서 하드 오류 — 리뷰 ① 처분 의견("Gap 유지 부당") 채택.

**AC-004 / AC-008 되돌림 행 신설 (기존 표 행 부재 — F23 지적)**
- AC-004: `sector_metrics.py:846`에 excess 산출 기준 -1.0p 이동 주입(보고 벤치마크 유지 — "산출 기준만 다른 기준으로 되돌리는" 부분 되돌림 회귀 모드) → identity **9 failed**(`항등식 위반 10.006… - 6.378… != 4.628…`) → 복원 후 `9 passed`. 증거: `pytest-ac004-rollback.txt`.
- AC-008: 서비스 M3(d16cb65) 교체 → 파리티 **9 failed**, `per_pair={'trading_value': 18, …}`, 상세 `Auto.trading_value: bubble=1514051627310.0 envelope=42919.6160361`(≈3.5e7배 — 구산식 close*volume과의 규모 차, AC의 "약 2.5e7배" 차수) → 복원 후 `9 passed`. 증거: `pytest-ac008-rollback.txt`.

**검증 게이트 교정 [HARD]**
- 루트 `frontend/tsconfig.json`이 `files: []` + project references → `tsc --noEmit`은 **0개 파일**을 검사한다(공허 관측). **이후 이 프로젝트의 타입 검사 관측은 `cd frontend && npx tsc -b` 기준.** 종전 §E.2/§E.3의 `tsc: exit 0` 기록은 공허한 관측이었음(리뷰 B2 실측 확정) — 본 재작업에서 전량 재관측했다.

**AC-005 Gap 잔여 사유**: frozen 픽스처에 AC가 명명한 기계·금융 섹터 부재(리뷰 F24) — `22.36→18.70`/`-4.80→-8.45` 리터럴을 어느 방향으로도 관측 불가. AC 문구 개정(섹터 재지정 또는 합성 픽스처)은 manager-spec 소관 — 본 SPEC에서는 Gap 공시.

**재검증(재작업 후)**: 백엔드 파일별 9스위트 **157 passed**(파리티 30·특성화 21·스키마 6·결측제외 3·빈date 1·sector_advanced 46·응답계약 14·consumer 26·sag037 10 — 디렉터리 일괄 실행은 컬렉션 함정으로 파일별 호출) · 프론트 레인(SectorAnalysis+common) **290/290** · `tsc -b` SPEC 귀속 0건 · eslint 변경 3파일 1건 react-refresh **pre-existing 실측**(HEAD 버전 43:17 동일 에러, 라인 이동만 — `SectorBubbleChart.current.bak` 대조).

## §E.3 Run-phase Audit-Ready Signal

- run_status: audit-ready
- run_complete_at: 2026-08-18 (review 재작업 반영 갱신)
- baseline_commits (Hybrid Trunk main-direct): M0 `6aabf81` (특성화+N=18, 단독) · M1 `3cb3828` (RED 11, +`status: draft→in-progress`) · plan산출물 `6c82d0b` · M2 `d96ade6` (배선 +4/−1) · M3 `d16cb65` (nullable) · **M4 `8f0a0c7` (전환 — N=18→0, 유일 수치 변경)** · M5 `3d06d9d` (봉투) · M5.5 `d6d1083` (섹터 사다리+0억 회귀 해소) · evidence/관측자 보강 커밋 · **review 재작업 커밋(B1/B2/tsc 게이트 교정/AC-029 관측자 복원/§E.3 집계 정정 — 2026-08-18)**
- ac_matrix: **21/22 PASS + 1 Gaps(AC-005)** — 되돌림 RED 관측: AC-001~004, 006~015, 018, 022, 025~029. AC-016/017/019~021/023/024는 형제 SPEC tombstone.
  - **집계 정정 이력(리뷰 F23 반영)**: 정정 전 "21/22 + 1 Gaps(AC-029)"는 AC-004/005/008을 되돌림 표 행 없이 PASS 블록에 포함한 오기입 — 실측 기준 18/22 + 4 Gaps였다. 2026-08-18 재작업으로 004/008 행 신설 + 029 관측자 복원(RED 실측) + 028 증거 재수립 → **21/22가 실측 바탕으로 성립**. AC-005는 frozen 픽스처에 기계·금융 섹터 부재(F24)로 어느 방향으로도 관측 불가 — Gap 공시.
- 관측자 결함 2건 발견·보강(영구 반영): ① AC-009 envelope_contract가 버블 market_filter 미검사(항진명제) → 단언 추가 후 되돌림 RED 확보 ② AC-028 live 관찰이 스칼라-only 단언이라 M4 null 유입 후 항상 RED(판별력 0) → 스칼라-or-None + 필드별 null 집합 고정으로 완화(B1)
- g8: 분기 A 확정(status 관측량) — §E.2 기록. g3: VIOLATION 측정 → 섹터 전용 사다리 재산출(사용자 승인) + M4 숨은 0억 표시 회귀 해소.
- **tsc 게이트 [교정]**: 루트 tsconfig가 `files: []` + project references → `tsc --noEmit`은 0파일 검사(공허 관측). 게이트 명령을 **`cd frontend && npx tsc -b`**로 교정. 관측(2026-08-18): exit 2, 오류 29건 — 전부 무관 pre-existing(stage.test·ChartGrid 계열), **SPEC 귀속 0건**(B2 해소 전 1건). 이후 타입 검사 관측은 전부 이 명령 기준.
- regression(2026-08-18 재작업 후 재측정): 백엔드 파일별 9스위트 **157 passed**(파리티 30·특성화 21·스키마 6·결측제외 3·빈date 1·sector_advanced 46·응답계약 14·consumer 26·sag037 10 — 디렉터리 일괄 실행은 컬렉션 함정으로 파일별 호출) · 프론트 레인(SectorAnalysis+common) **290/290** · `tsc -b` SPEC 귀속 0건 · eslint 변경 3파일 1건 react-refresh pre-existing(HEAD 대조 실측). 선행 관측(root 스위프 254·프론트 722)은 §E.2 재작업 절 이전 기록 — 재작업 diff는 레인 로컬로 재측정.
- gaps: ① **AC-005 되돌림 불가**(frozen 픽스처에 기계·금융 부재, F24 — AC 문구 개정은 manager-spec 소관) ② 커버리지 미측정(coverage 미설치) ③ 사다리 refs 스케일의 라이브 검증 미실시(배포 후 첫 주 권고) ④ F7(SECTOR ladder vMin/vMax 커밋 테스트 0건) 외 리뷰 확정 결함 잔여분은 sync/형제 SPEC 분류 — review-report.md §권고 처리 순서 참조
- disclosures: pre-commit pytest 2m 타임아웃으로 `SKIP_MOAI_PRECOMMIT=1` 문서화 오버라이드 다수(전 건 대체 증거 수집·공개, `--no-verify` 미사용). 스폰 사망 대응 — orchestrator 직접 마무리 4건(M4 파티션 재기술·M5.5 사다리·되돌림 배치·검증 배치 — 사용자 승인 3건: 파티션 재기술+§D 등재 / 사다리 분리 / m5.test 갱신+§D 등재). plan 산출물 지연 커밋 1건(6c82d0b — lead 누락). review 재작업(2026-08-18)도 orchestrator 직접 실행 — 칸반 리드(lead-tjvce8)의 run 컬럼 복귀 지시에 따른 처분.

## §E.4 Sync-phase Audit-Ready Signal

- sync_status: audit-ready
- sync_complete_at: 2026-08-18
- sync_commit_sha: 86d4af8 (docs(SPEC-SECTOR-METRIC-UNIFY-001): sync-phase — CHANGELOG 기록·3-phase close — backfill 커밋 선례 a4ecea8 → 777f044)
- 실행 방식: **orchestrator-direct (사용자 승인, 2026-08-18)** — gate-sync-1·gate-sync-2·실행 방식 3문항 1회 AskUserQuestion 통합 승인. 근거: GLM 세션 manager-docs 스폰 하위 컨텍스트 한계 연쇄 사망 선례(어제 sync 2회·본 SPEC run 4회, memory `project_glm_subagent_ctx_death`) + 검증·커버리지는 이미 본 세션이 직접 완료
- **sync 검증 배치 (관측 주체: sync-tjvce8 세션, HEAD 6cb3735, 이번 실행 — 리드 재현 및 §E.3 기준선과 독립 대조)**:
  | 검증 | 관측 출력 | 증거 파일(절대 경로) |
  |---|---|---|
  | pytest SPEC 9스위트 단일 호출(컬렉션 함정 파일 `test_ai_report_router_deep_mode.py` 제외) | `157 passed, 1 warning in 136.48s`, exit 0 — §E.3 기준선 157과 일치 | `/Users/byunjungwon/Dev/my-project-01/my_chart/.moai/state/verify/sync-tjvce8-smu001/coverage-pytest.txt` |
  | vitest 레인 `src/components/SectorAnalysis src/components/common` | `Test Files 29 passed (29)` · `Tests 290 passed (290)`, exit 0 — §E.3 기준선 290과 일치 | `…/sync-tjvce8-smu001/vitest-lane.txt` |
  | `cd frontend && npx tsc -b` (교정된 게이트 명령) | exit 2, `error TS` 29건 — `SectorBubbleChart` 귀속 **0건**(전부 무관 pre-existing). 리드 B2 재현(29/0)과 일치 | `…/sync-tjvce8-smu001/tsc-b.txt` |
  | 스냅샷 소비 시도 `moai verify check --key-current` | `fresh: false — no snapshot recorded for the current working-tree key` → attributable diff-check 불가, 재실행으로 귀속(위 3종) | — |
- **커버리지 (G-5 해소 — 리드 승인 하에 venv에 coverage 7.15.4 설치 후 최초 실측)**: `coverage run --source=my_chart,backend -m pytest <9 files>` → `coverage report` (acceptance §E DoD 형태 그대로):
  - SPEC 변경 파일: `backend/schemas/sector_advanced.py` **100%** · `backend/services/sector_advanced_service.py` **88%** · `my_chart/analysis/sector_metrics.py` **97%** · `backend/routers/sectors.py` 78% · `my_chart/analysis/sector_advanced.py` 81%
  - 전체 TOTAL 39% — `--source` 전수(my_chart+backend 전 파일) 값으로 SPEC 무관 파일 대부분이 미실행에 포함됨. 게이트 수치가 아니라 측정 기록. 증거: `…/sync-tjvce8-smu001/coverage-report.txt`
- **AC-005 Gap 상태 공시 (sync 미처리 — manager-spec 소관)**: frozen 픽스처에 기계·금융 섹터 부재(F24)로 되돌림 불가. AC 문구 개정(섹터 재지정 또는 합성 픽스처)은 후속 manager-spec 위임 사항
- **잔여 항목 분류 (review-report.md §권고 처리 순서 기준)**: ①~③ run 재작업 완료(`1f0c304`) · **④** SPEC 개정(REQ-SMU-023/AC-SMU-018 → `SECTOR_PERIOD_SIZE_LADDER` 지목 + HISTORY 행) — manager-spec 후속 · **⑤** F7 사다리 상수 vMin/vMax 관측자 신설 — 배포 전 권고, 후속 · **⑥** F3/F22 단위 표기 정정 + `formatSectorTradingValue` export 이동 — SDU-001/후속 · **⑦** F14~F29 — SDU-001·백로그 분류. 본 sync는 문서 동기화 단계로 코드 변경 없음(docs-only)
- **증거 보존 확인 (리드 지시 — 절대 경로 ls)**: `.moai/state/verify/run-tjvce8-smu001/` 8파일(약 2.8MB) · `review-tjvce8-smu001/` 2파일 · `sync-tjvce8-smu001/` 4파일 모두 실재 관측. 리드 정정(2026-08-18) 반영: §E.5의 "인용 경로 미해석" 관측은 리드 측 cwd 오염(`cd frontend` 후 상대 경로 → `frontend/.moai/` nested 잔재)에 의한 오관측으로 철회됨 — 증거 소실 사고 없었음. 커밋 직후 재확인 분은 backfill 커밋에 기록
- MX 관찰: 변경 코드 파일 내 `@MX` 태그 27개(SectorBubbleChart 9 · sector_advanced 7 · bubbleRadius 4 · schemas 4 · routers 2 · types 1). `sector_advanced_service.py` 0개는 변경 전 기준선과 동일(실측 `git show 777f044 | grep -c @MX` = 0 — 회귀 아님)
- CHANGELOG: `[Unreleased]`에 `Fixed (SPEC-SECTOR-METRIC-UNIFY-001 v0.5.0)` 항목 1건 기록. 사전 중복 검사 `grep -c 'SPEC-SECTOR-METRIC-UNIFY-001' CHANGELOG.md` = 0(B12). AC 수는 acceptance.md SSOT 기준(22 AC = 21 PASS + 1 Gap)으로 기록
- disclosures: docs-only diff + pre-commit 게이트의 pytest 2m 타임아웃(§E.3·전 SPEC sync 선례와 동일 기제) → 문서화된 `SKIP_MOAI_PRECOMMIT=1` 오버라이드 사용. 대체 증거: 동일 HEAD 6cb3735에서 pytest 157 · vitest 290/290 · tsc 귀속 0 커버리지 실측(`…/sync-tjvce8-smu001/`). 스펙 상 no-verify 플래그 미사용
- **커밋 직후 인용 경로 재검증 (절대 경로 ls, 리드 지시 이행)**: sync 커밋 `86d4af8` 랜딩·push(`1f0c304..86d4af8`, 이후 origin/main...HEAD `0 0`) 직후 관측 — `/Users/byunjungwon/Dev/my-project-01/my_chart/.moai/state/verify/sync-tjvce8-smu001/` 4파일(coverage-pytest.txt · coverage-report.txt · tsc-b.txt · vitest-lane.txt) · `run-tjvce8-smu001/` 8파일 · `review-tjvce8-smu001/` 2파일 전부 해석됨. §E.4가 인용한 경로에 죽은 링크 없음

## §E.5 Review-phase Signal (review-tjvce8, 2026-08-18)

- review_status: **차단(blocked)** — sync 진행 불가
- 범위: `777f044..eef55e0` · 모드: `/moai review --deep` (4 헌트 렌즈 → 3인 적대적 패널 2-of-3 quorum)
- 본문: [review-report.md](./review-report.md) — 확정 결함 29건 + 반증 8건 + 중점 3건 판정 + 미해결 3건 처분
- 증거: `.moai/state/verify/review-tjvce8-smu001/`
- 차단 사유 2건(리뷰어 직접 재현):
  - **B1** `backend/tests/test_bubble_schema_nullable.py`가 main에서 RED (`패션.period_return: None` vs `isinstance(float)`). §E.2가 AC-028 되돌림 증거로 인용한 "1 failed"는 주입 전에도 성립 → 판별력 0 (lessons #9 계열)
  - **B2** `SectorBubbleChart.tsx(124,77) TS2345` 라이브 타입 오류. 루트 `tsconfig.json`이 `files: []`라 `tsc --noEmit`이 0개 파일 컴파일 → §E.3 `tsc: exit 0`·AC-029 "tsc 통과"는 공허한 관측. 런타임에선 결측 섹터가 보합과 같은 중립 회색으로 렌더
- §E.3 집계 정정 필요: AC-004/005/008은 §E.2 되돌림 표에 행이 없음에도 "AC-001~011 전부" 블록에 포함 → 21/22 PASS는 액면 성립 불가(최소 18/22 + 4 Gaps, B1 반영 시 추가 하향)
- 미해결 3건 처분: ① AC-029 Gap 유지 부당 — `null as unknown as number` 캐스트 5개(m5.test:65, MetricTextParity.m7.test:93-94) 제거로 관측자 복원 가능 ② 커버리지 sync 보측 타당하나 B1 선행 ③ 사다리 라이브 미검증은 배포 차단 사유 아님(창 11/32/95일로 규모 정합 실측 확인) — 단 F7(사다리 상수 무관측)은 배포 전 처리 권고
- 추가 확인: backend 컬렉션 오류 2건은 **본 SPEC 무관 확인**, 단 원인은 `db_service.py` import 실패가 아니라 `test_ai_report_router_deep_mode.py:64-70`의 `sys.modules` 전역 스텁에 의한 수집 순서 의존. 파생 주의 — `pytest backend/tests` 일괄 실행은 0건 실행으로 중단됨
- **run 재작업 완료 (2026-08-18, run-tjvce8)**: 리드 지시 5건 전부 처분 — ① B1 해소(단언 완화 + 필드별 null 집합 고정, `6 passed`) ② B2 해소(`sectorReturnColor(number|null)` 결측색 `#4B5563` + m5 관측자 신설, tsc SPEC 귀속 1→0) ③ tsc 게이트 `tsc -b` 교정 + §E.2/§E.3 재관측 ④ §E.3 집계 정정(AC-004/008 되돌림 행 신설 → **21/22 PASS + 1 Gap(AC-005)**, F23 반영) ⑤ AC-029 캐스트 4건 제거·관측자 복원(되돌림 RED 5건 실측) → Gaps 폐지·PASS. 증거: `.moai/state/verify/run-tjvce8-smu001/`. 잔여: AC-005 Gap(픽스처 섹터 부재, AC 문구 개정은 manager-spec 소관)·커버리지 보층·F7 등 sync/형제 SPEC 분류 항목.
- **리드 독립 재현 (2026-08-18, lead-tjvce8)** — 차단 해소를 보고가 아니라 직접 실행으로 확인. 관측:
  - B1 `python -m pytest backend/tests/test_bubble_schema_nullable.py -q` → `6 passed` (차단 시점 관측 `:103 AssertionError` 1 failed에서 전환)
  - B2 `cd frontend && npx tsc -b` → 총 오류 **29** (차단 시점 30), `SectorBubbleChart` 귀속 **0건** (차단 시점 `(124,77) TS2345` 1건). 감소분이 정확히 본 SPEC 몫과 일치
  - 커밋 `1f0c304` 5파일 실재, origin/main 0/0 동기화, 작업트리 청결
  - 판정: **차단 해소 — sync 컬럼 이관**
- **[철회됨] 증거 소실 주장 — 리드 오관측 (2026-08-18)** — 직전 커밋(`6cb3735`)에서 리드가 "인용 증거 경로 2곳 소실"로 기록했으나 **사실이 아니며 철회한다.** 두 디렉토리 모두 무결하다:
  - `.moai/state/verify/run-tjvce8-smu001/` — 8파일 약 2.8MB (`pytest-ac004/008/028-rollback.txt`, `tsc-b-ac029-rollback.txt`, `tsc-b-after-fix.txt`, `pytest-spec-suites-final.txt`, `precommit-attempt2.log`, `SectorBubbleChart.current.bak`)
  - `.moai/state/verify/review-tjvce8-smu001/` — 2파일 (`collection-error-rootcause.md`, `partition-contract-hole.md`, mtime 15:28 이후 무변경)
  - **오관측 원인 (확정)**: 리드가 B2 재현을 위해 `cd frontend`를 실행했고 Bash 작업 디렉토리가 호출 간 유지되어, 이후 상대 경로 `ls .moai/state/verify/...`가 `frontend/.moai/state/verify/`(팬아웃 잔재 nested 캐시, 빈 `d68da0f0`만 보유)를 가리켰다. 같은 cwd 오염으로 `git status -- backend/` 빈 출력·`awk` 파일 열기 실패가 동반 관측됐으나 리드가 그 두 신호를 흘려보냈다. 절대 경로 재실행으로 전건 확인.
  - **정정 사항**: (a) run-phase 정리 단계가 증거를 삭제했다는 추정은 근거 없음 — 삭제 명령은 소스 디렉토리의 주입 백업 `.exp-bak` 4건뿐이며 증거 디렉토리 자체를 지운 명령은 없었다. (b) "재생성 없이 진행" 결정의 전제(복구 불가)는 성립하지 않았고, 재생성 자체가 불필요하다 — AC-004/008 되돌림·AC-029 RED·풀스위트 결과의 보조 증거는 인용 경로에 그대로 있다. (c) VCI §2 미귀속 기록도 철회한다.
  - **유효하게 남는 교훈**: 부재 관측(“없다”)은 존재 관측보다 취약하다 — cwd 오염·경로 오타·권한 부족이 삭제와 동일한 신호를 낸다. 인용 경로 검증은 절대 경로로 수행한다.
- **sync 이관 판정 (유지)** — 차단 결함 B1·B2 해소는 리드 직접 재현으로 확인됐고, 위 철회는 그 판정에 영향을 주지 않는다.
