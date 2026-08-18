# SPEC-SECTOR-DISPLAY-UNIFY-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- **작성 시각**: 2026-08-18
- **출처**: `SPEC-SECTOR-METRIC-UNIFY-001` v0.3.0에서 M6/M7 분리 (plan-audit iteration 1의 D7, 결정 A)
- **분리 근거 (재논의 금지)**: 절단면은 승인된 원본 계획서 `.moai/plans/rs-purring-key.md`의 M6 헤더 *"백엔드 독립, 먼저 배포 가능"*이 이미 그어 둔 것. 예산 맞추기가 아니라 원래 둘이던 것의 복원이며, 배포 순서(백엔드 선행 → 프론트 후행)와 일치
- **SPEC ID 정규식 자체 검사**: 실행 완료 — `PASS`
  ```
  ID="SPEC-SECTOR-DISPLAY-UNIFY-001"
  [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
  → PASS
  ```
- **ID 충돌 검사**: `.moai/specs/`에 `DISPLAY` 매칭 없음 → `NO_COLLISION`
- **Tier**: M — 마일스톤 2개(M6·M7), 대상 파일 ~8개. Tier L 임계("≥3 milestone AND ≥10 files") **양쪽 다 미달**
- **예산**: REQ 11건 / AC 13건 (Tier M 예산 이내)
- **의존 비대칭 (lead 특별 요청 사항, spec.md §2 + plan.md §B에 기록)**:
  - M6 = 백엔드 의존 **없음**, 선행·단독 배포 가능
  - M7 + 버블 X축 라벨 = 형제 SPEC M5 완료 **의존**
  - 내부 순서 근거는 "되돌리기 쉬움"이 아니라 **의존 그래프**이며, AC-SDU-012가 그 비대칭을 기계적으로 증명한다
- **잔류 예외 (본 SPEC 소관 아님)**: `PERIOD_SIZE_LADDER` 재산출은 프론트 파일이지만 형제 SPEC의 M4 완결 조건이므로 그쪽에 잔류. 경로만 보고 이관 금지 — spec.md §4에 명시
- **미해결 갭**: G-F1(교차 언어 상수 추출 형태) / G-F2(ThemeAnalysis 동일 패턴) / G-F3(원본의 "8개 호출부"는 미검증 수치) / G-F4(M5 미머지 시 M7 GREEN 무효)

## §E.1.1 audit_iteration_1 — plan-auditor FAIL 0.70 → 대응 (2026-08-18)

Tier M 임계 0.80. must-pass 7건 전부 통과.

**감사가 인정한 것 (재논의 금지)**: 계획서 M6/M7 전사 충실(누락·밀반입 0건), **사다리 제외 기록이 계획서를 교정**(계획서의 `SectorBubbleChart.tsx:95`는 소비처, 정의부는 `bubbleRadius.ts:26`), 3면 문자열 캐비어트 전송 생존, 순위 픽스처 되돌림·`null%` 렌더 관측·색 램프 AC의 반증 가능성, 갭 4종이 갭으로 남았고 이를 가정하는 AC 없음, Tier M 적정(11 REQ ≤ 16 / 13 AC ≤ 16), `tags` 문자열형 정상.

| 결함 | 등급 | 처분 |
|---|---|---|
| **D1 + D4** — 의존 비대칭 증명이 판별력 없음(고정 명령이 미변경 트리에서 이미 실패) + eslint 범위가 M6 변경 디렉터리 3곳 누락 | BLOCKING | **함께 수정 완료.** 범위를 `SectorAnalysis + common + ChartGrid + StockExplorer + utils`로 확대 후 **재측정 → 27건**(기존 9건 범위에서 18건 증가). `plan.md §F.1`에 파일·행:열·규칙까지 축자 고정. AC-SDU-012/013을 절대 통과 → **`B \ A == ∅`(신규 0건)** 델타 단언으로 재작성. 개수 비교(`\|B\|>\|A\|`)로는 한 건 소실+한 건 신규를 놓치므로 **집합 차**로 판정. eslint exit 1은 `grep -c` 억제 관례 비적용(억제가 아니라 비교 대상)임을 §F·acceptance 규약 양쪽에 명시. 기준선 27건은 **본 SPEC 수선 대상 아님**을 [HARD]로 못박아 범위 침식 차단 |
| **D2** — AC 009/010/011이 REQ와 한 칸씩 어긋남 | BLOCKING | **수정 완료(재번호 아님).** `acceptance.md §0`에 **명시적 REQ↔AC 매핑표** 신설 — REQ-009→AC-010, REQ-010→AC-011, REQ-011→AC-009를 표에 못박고 001~008의 항등이 우연임을 표기. 암묵 관례 의존도 함께 해소 |
| **D3** — `depends_on` 선언과 §2 [HARD]의 기계적 충돌 | BLOCKING | **수정 완료(선언 유지).** `spec.md §2.1` 신설 — 착지 대상별 분기표: **M6 단독 = `override`**(`--ignore-deps` + 미충족 의존 ID·§2 근거를 `.moai/logs/depends-on-override.log`에 기록), **M7 = `wait`**(유일하게 옳은 경우), 불명확 = `abort`. override는 의존 부정이 아니라 마일스톤 단위 세분 부재라는 도구 한계 우회임을 명시. DoD에 로그 기록 항목 추가 |
| **D5** — 되돌림이 형제 SPEC 소유 백엔드 파일 변형 | BLOCKING | **수정 완료.** AC-SDU-003에 4항 안전 규약: 편집 **전** `git status --short` 청결 필수 / 형제 run 작업 미커밋 중 **실행 금지** / **중단 없는 단일 스텝** 수행·복원 / 복원 후 재확인. 이 AC가 `frontend/` 밖으로 나가는 유일 지점임을 명시 |
| **D8** | optional (take) | **수정 완료.** REQ-SDU-007 `(When)`→`(While)`, REQ-SDU-011 `(Ubiquitous)`→`(When)` |
| **D10** | optional (take) | **수정 완료 + 감사 수치도 정정.** 실측: `toHaveBeenLastCalledWith`는 **`:56`, `:64`, `:81`**. 계획서의 `:60,68,79`도, 감사의 `:79`도 아니다. `:55`/`:77`의 인자 없는 `toHaveBeenCalled()`는 arity 변경 무관임을 함께 기록 |
| **D9** | optional (take) | **수정 완료.** AC-SDU-005의 "서로 다른 프로덕션 헬퍼 둘" 전제가 트리에 없음을 확인 — 실제로는 단일 `getCellColor(value, type)`(`:54`)이고 `:185`/`:194` 둘 다 `'percentage'`. 가드를 **두 프로덕션 호출부(`:185`/`:194`)의 렌더 출력 비교**로 재작성하고 세 번째 `type` 추가를 자연스러운 수정으로 명시 |
| **D6 / D7** | optional | **미조치(재량).** 감사 지시대로 긴 선택 목록을 근거로 범위를 넓히지 않음. G-F1(`fs.readFileSync` + `import.meta.url`)은 이미 run-phase 갭으로 등재돼 있고, D7(`null%`의 실제 생산지가 호출부 `SectorDetailPanel.tsx:100`이라 REQ-SDU-002 문구가 문자 그대로는 부정확)은 AC-SDU-002의 관측량(렌더 문자열에 `null` 미포함)이 생산지와 무관하게 유효하므로 판정에 영향 없음 |

### 신규 갭 (감사 지적 아님 — 기준선 재측정 중 발견)

- **G-F5**: `common/MetricCell.tsx`가 기준선에 `react-refresh/only-export-components` **5건**을 이미 갖고 있고, REQ-SDU-001이 그 파일에 `rating0`/`pct0` **2개를 더 export**하라고 한다 → 같은 규칙 **+2건**이 날 가능성이 높고, 그러면 AC-SDU-012/013의 "신규 0건"이 **구성상** 실패한다. 후보 2택(예외 사전 선언 / 비컴포넌트 모듈 분리)을 적어 두되 **지금 결정하지 않는다** — (b)는 `MetricCell.tsx`가 `@MX:ANCHOR metricDisplay` 단일 출처라는 REQ-SDU-001의 전제와 충돌할 수 있다. M6 착수 시 결정 + 근거 기록, DoD 등재

## §E.1.2 audit_iteration_2 — plan-auditor PASS-WITH-DEBT 0.875 → 잔여 4건 정리 (2026-08-18)

Δ +0.175 (0.70 → 0.875), Tier M 임계 0.80. must-pass 7건 전부 통과, iter-1 구조적 결함 2건(D1/D2) 실제 수리 확인. **4회차 감사 없음.**

**감사가 트리에서 직접 재현하고 인정한 것 (재논의 금지)**: 기준선 27건이 `(파일, 줄:열, 규칙)` 단위로 전부 일치 — 요약 개수가 아닌 진짜 귀속 기준선(`ChartCell.tsx:392:20` 동일 위치 3건, `MetricCell.tsx` 5건 위치까지 행 단위 일치). 집합 차 판정 실행 가능 + `|B|>|A|` 대신 쓴 이유(한 건 소실 + 한 건 신규가 개수를 그대로 둔다) 확인. §0 매핑표 3행 정확 — **001~008 항등을 "우연"이라 표기한 것**이 미래 편집자의 "일관성 복원" 재번호를 막아 표를 오래가게 만든다고 평가. D9는 요구 이상(결과만 고치지 않고 "서로 다른 헬퍼 둘" 전제가 트리에 존재한 적 없다는 사실 자체를 기록). D10은 감사가 자기 값 `:79`가 잘린 창을 읽고 재측정하지 않은 결과임을 인정하고 `:56`/`:64`/`:81`이 맞다고 확인.

| 결함 | 처분 |
|---|---|
| **D11** — G-F5 소진 경계 모호(`M6 착수 시 결정`) | **수정 완료 3항.** (1) 경계를 **`M6 첫 커밋 이전`**으로 명시 — (b)안은 첫 커밋 내용 자체를 바꾸므로 착지 후 결정은 사후 합리화. (2) `plan.md §F.2` 결정 후보표 신설, **(a) 예외 사전 선언을 추정 정답**으로 근거와 함께 명시(같은 계열 포매터 `percent1`/`percent2`가 이미 export 중, 파일 성격·단일 출처 전제 유지). (b)는 기각 방향(둘만 옮기면 계열이 쪼개져 넷 중 둘만 앵커에 남음 = 피하려던 지적보다 나쁨 / 다섯 다 옮기면 `@MX:ANCHOR metricDisplay` 파일 리팩터링 = REQ-SDU-001 범위 초과). (3) **(c) 화살표 const 안은 가설로 기록** — `eslint.config.js:16`의 `reactRefresh.configs.vite`가 `allowConstantExport: true`라 **상수 리터럴만** 면제되고(그래서 `:12`/`:13` 문자열 리터럴은 무사, 함수 export는 걸림) 화살표 함수 const는 리터럴이 아니라 면제 안 될 가능성이 높음 → (a) 강화. **미측정이므로 가설**이며 M6 킥오프 lint 1회로 확정. **소스 대조로 +2 확정성 근거화**: 5건(`:34,38,70,86,93`)이 `export function` 5개(`percent1`/`percent2`/`metricDisplay`/`metricText`/`toMetricValue`)와 정확히 일치, exported `const`/`type`/`interface` 7개(`:12,13,19,21,29,63,99`)는 0건 |
| **D12** — "집합" 차인데 기준선에 중복 삼중항(`ChartCell.tsx:392:20` ×3) | **수정 완료.** `plan.md §F.1`에 한 절 추가: **A는 다중집합**이며 `§F.1` 표의 `×3`이 다중도를 기록한다. 엄격 집합에서는 3건이 원소 하나로 붕괴해 셋 중 하나 소실을 검출 못 하지만 **의도된 결과** — AC 목적은 신규 검출이고 기준선 오류가 고쳐지는 것은 회귀가 아니다. **`A \ B`(소실)는 의도적으로 확인하지 않으며 비교는 `B \ A` 한 방향**임을 명시 |
| **D6** — 미조치이면서 기록조차 안 됨 | **기록만 완료(수정 아님).** G-F1에 추가: 교차 언어 테스트가 `frontend/` → 레포 루트 경계를 넘으므로 **vite import로 해결되지 않으며**(모듈 그래프 밖 + `.py`는 로더 대상 아님), Node `fs`로 읽되 경로를 **CWD가 아닌 `import.meta.url` 기준**으로 해석해야 한다(vitest 실행 CWD 가정은 깨지기 쉽다) |
| **D7** — 동일 | **기록만 완료(수정 아님).** REQ-SDU-002(spec.md)와 AC-SDU-002(acceptance.md) 양쪽에: `MetricCard`는 `:18-30`이 아니라 **`:22-30`**, `null%`의 **생산 지점은 컴포넌트가 아니라 호출부 `:100`**(`` value={`${sector.rs_top_pct}%`} `` — 결측값이 템플릿 리터럴에 보간). AC가 렌더 출력을 관측하므로 충족 가능성은 유지되지만 **요구사항이 수정 범위를 실제보다 좁게 잡고 있으며**, `MetricCard` 내부만 고치고 호출부 보간을 남기면 통과 못 함 |

---

## §E.1.3 run 단계 인계 — debt 처분표 [HARD]

> **run 세션이 읽을 유일한 인계 문서다.** 형식은 백엔드 `SPEC-SECTOR-METRIC-UNIFY-001/progress.md §E.1.4`와 동일.

> ### [HARD] 먼저 처리할 것 — G-F5
> **G-F5가 미해결인 동안 AC-SDU-012 / AC-SDU-013은 통과할 수 없다.** REQ-SDU-001 구현이 `MetricCell.tsx`에 `react-refresh/only-export-components` **+2건**을 확정적으로 추가하므로 두 AC의 "신규 0건"이 **구성상** 실패한다. **M6 첫 커밋을 쓰기 전에** 이 결정부터 소진하라.

| # | debt | 소진 시점 | 실패 시 조치 |
|---|---|---|---|
| **G-F5 / D11** | `MetricCell.tsx` `only-export-components` **+2** 처리 결정 — (a) 예외 사전 선언(추정 정답) / (b) 모듈 분리(기각 방향) / (c) 화살표 const(가설, `allowConstantExport` 미측정) | **M6 첫 커밋 이전** | 확정 lint 1회로 (c) 생사 판정. (c)가 죽으면 **(a) 채택**하고 +2를 기준선 블록에 **사전 선언된 예외로 명시 추가**. 커밋이 착지한 뒤의 결정은 사후 합리화이므로 인정하지 않는다. 결정과 근거를 progress.md에 기록 |
| **G-F3** | 반올림 규약 전환 대상 **호출부 개수** 확정 (원본 계획의 "8개"는 미검증 수치) | **M6 첫 커밋 이전 — 스캔 실측** | 실행 스캔의 **관측 출력을 AC-SDU-001에 리터럴로 고정**한 뒤 판정. 손으로 옮겨 적지 않는다(lessons #9) |
| **D12** | A를 다중집합으로 읽고 `B \ A` 한 방향만 비교 (`A \ B` 소실은 의도적 미확인) | **AC-SDU-012 판정 전** | 판정 시점에 즉흥적으로 예외를 만들지 않는다. 기준선 27건은 **본 SPEC 수선 대상 아님** |
| **G-F1 / D6** | 교차 언어 상수 추출 형태 확정 — Node `fs` + **`import.meta.url` 기준 경로 해석**, `parseFloat`로 **수치 등식**(백엔드 `_RS_TOP_THRESHOLD = 80.0` ↔ TS `80`, 문자열 등식 아님) | **AC-SDU-003 테스트 작성 전** | vite import 시도 금지(`frontend/`→루트 경계, `.py`는 로더 대상 아님). vitest 실행 CWD 가정 금지. 손으로 옮겨 적은 상수 비교로 대체하지 않는다 |
| **D7** | `null%` 수정 범위 — 생산 지점은 `MetricCard`(`:22-30`) 내부가 아니라 **호출부 `:100`의 템플릿 리터럴 보간** | **REQ-SDU-002 구현 전** | 컴포넌트 내부만 고치고 호출부 보간을 남기면 **AC-SDU-002가 RED**. 요구사항 인용이 범위를 좁게 잡고 있으니 호출부까지 포함해 수정 |
| **G-F4** | 형제 SPEC `SPEC-SECTOR-METRIC-UNIFY-001` **M5 머지 여부 확인** | **§B(M7) AC 판정 전** | 미머지 상태의 GREEN은 폴백 경로를 측정한 것이므로 **무효**. 미머지면 M6까지만 랜딩 |
| **`depends_on` override** | M6 단독 착지 시 `--ignore-deps` 사용 + **미충족 의존 ID·spec.md §2 비대칭 근거**를 `.moai/logs/depends-on-override.log`에 기록 | **M6 run 진입 시** | M7 착지라면 override가 아니라 **`wait`**가 옳다. 착지 대상이 불명확하면 `abort`. 분기표는 spec.md §2.1 |
| **G-F2** | `ThemeAnalysis/ThemeRankingTable.tsx` 동일 표시 패턴 여부 | 범위 밖 | 발견되면 **백로그 기록만**. 본 SPEC 범위를 넓히지 않는다 |

## §F Phase 4 Mode Selection

- **작성 시각**: 2026-08-18 (run 진입, 카드 t2 — kanban lead 디스패치, 운영자 승인 완료)
- **입력 파라미터**: tier M · 대상 파일 ~11개(MetricCell, rsMetrics+테스트, SectorRankingTable, SectorDetailPanel, SectorBubbleChart, ChartCell, StockTable, SectorAnalysis, api/market, MarketContext, types/market + 기존 테스트 3종) · 도메인 수 1(프론트엔드 React/TS 단일) · 언어 구성 TS/TSX 100% · 동시성 편익 LOW(코딩 집약 — Anthropic coding-task 병렬성 경고) · Agent Teams 폐기(모드 3 tombstone)
- **모드 평가**: trivial ✗(다파일 의미 변경) / background ✗(쓰기 작업) / agent-team ✗(RETIRED) / parallel ✗(코딩 집약 — Mode 5 우선 원칙) / workflow ✗(~30파일 기계 변환 아님, 의미적 변경 다수) / **sub-agent ✓**
- **Decision: sub-agent (Mode 5)** — 마일스톤별 순차 manager-develop 위임(M6 → M7). 다이어트 스폰(아티팩트는 디스크 참조, 인라인 복사 최소화)으로 운용하며, **동일 사망 2회 관측 시 orchestrator-direct 전환을 리드에게 블로커 보고**한다(본 세션 환경의 확립 패턴 — memory `glm-subagent-context-death`; 형제 SPEC run에서 4회 사망 선례).
- **근거**: 코딩 집약 작업은 순차 서브에이전트가 안전한 기본(Anthropic 코딩 과제 병렬성 경고). 병렬 편익이 없어 Mode 4/6의 조정 오버헤드가 이득을 상회한다.

## §E.2 Run-phase Evidence

### §E.2.0 Run 킥오프 — 의존 게이트·G-F5·G-F3 소전 (2026-08-18, M6 첫 커밋 이전)

**의존 pre-flight (G-F4 해소 근거)** — `depends_on` 2건 전부 `status: completed` 관측:
```
$ head -5 .moai/specs/SPEC-SECTOR-METRIC-UNIFY-001/spec.md → status: completed
$ head -5 .moai/specs/SPEC-SECTOR-UX-001/spec.md            → status: completed
```
`--ignore-deps` override도 `wait`도 불필요 (spec.md §2.1 분기표 어디에도 해당하지 않는 정상 경로). M5 착지는 리드가 커밋 수준으로 확인해 디스패치에 명시했다: `3d06d9d` "M5 봉투 정상화 — envelope_fields 구성" + 배선 실재(`backend/schemas/envelope.py:238` → `backend/services/sector_advanced_service.py:126`, `backend/services/sector_ranking_service.py:14`). 본 세션도 소스에서 재확인: `envelope.py` `envelope_fields(...)`가 `data: list[SectorAggregate] | None`를 받고 `sector_ranking_service.py:106`이 `data=agg.aggregates`로 전달하며, `my_chart/analysis/sector_metrics.py:695-706`이 `period` 지정 시 해당 기간 초과수익률 기준으로 `data[].rank`를 재배정한다. **§B(M7) AC는 폴백이 아닌 실경로를 측정한다.**

**동기화 pre-flight**: `git fetch origin main` → `git rev-list --count --left-right origin/main...HEAD` = `0 0` (동기화). HEAD `f11730d` (main). `frontend/` 추적 파일 청결 (미추적 `coverage/`·`test-results/` 등은 스테이징 배제 대상). 활성 세션 1건(SPEC 미부속 — 리드 세션으로 추정, 카드 디스패치 당사자).

**Phase 1 Plan Audit Gate — 스킵 근거 (3조건)**: (1) 판정 PASS-WITH-DEBT — moai.md §8 Plan Audit 규약의 PASS 계열이며 부채 4건은 §E.1.3 인계표로 전량 처분됨 (2) 점수 0.875 ≥ Tier M 임계 0.80 (3) 아티팩트 해시 — 판정 기록 커밋(`21f370a`) 이후 spec/plan/acceptance 무변경 (단, 본 킥오프에서 plan.md §F.1 예외 등재 + acceptance.md AC-SDU-001 리터럴 고정을 §E.1.3가 사전 승인한 기계적 수정으로 수행 — 아래 참조). 감사 캐시 `compute_hash` = `7b0400fd…`, lookup hit 없음(캐시 미생성 — 진행열 세션이 gate 프로세스를 거치지 않았음) → 기록 기반 판정.

**G-F5 소진 (M6 첫 커밋 이전 — §E.1.3 [HARD]) — (c) 사망 실측 → (a) 채택**:
```
[실험] MetricCell.tsx에 export const rating0/pct0 (화살표) 임시 추가 후:
$ cd frontend && npx eslint src/components/common/MetricCell.tsx
→ ✖ 7 problems (7 errors, 0 warnings)
  기존 5건(34:17, 38:17, 74:17, 90:17, 97:17 — +4행 삽입으로 이동) 외
  신규 2건: 43:14, 44:14 react-refresh/only-export-components   ← (c)안 사망 관측
[복원 증명]
$ git status --short -- frontend/src   → 출력 없음 (청결)
$ npx eslint src/components/common/MetricCell.tsx → ✖ 5 problems (기준선 복귀)
```
`allowConstantExport: true`는 상수 리터럴만 면제 — 화살표 함수 const는 면제하지 않음이 확정. **결정: (a) 예외 사전 선언** — `rating0`/`pct0`를 `export function` 선언으로 구현, 증가분 최대 2건(파일·규칙·원인 한정)을 `plan.md §F.1` 기준선의 사전 선언 예외로 등재 완료(본 커밋 세트에 포함).

**G-F3 소진 (M6 첫 커밋 이전)** — 반올림 규약 전환 대상 호출부 실행 스캔: **14개 관측** (rating0 7 + pct0 7). 명령·출력 14줄을 `acceptance.md` AC-SDU-001에 리터럴로 고정 완료. 원본 계획의 "8개"는 실측과 불일치(미검증 수치였음이 확인됨). 스캔은 `frontend/` cwd에서 `grep -rn --include='*.tsx'` (따옴표 글롭) + `__tests__` 제외로 실행.

**문서 수정 근거**: 위 두 편집(plan.md §F.1 / acceptance.md AC-SDU-001)은 §E.1.3 인계표가 run 세션에 명시적으로 지시한 사전 승인 수정이며 M6 첫 커밋 이전에 수행됨(사후 합리화 아님). manager-develop 소유가 아닌 orchestrator가 기계적 등록만 수행.

### §E.2.1 M6 구현

**실행 방식**: orchestrator-direct (운영자 승인 A — 리드 경유, 2026-08-19). 근거: manager-develop 스폰 2회 사망(#1 "Prompt is too long" 진입 직후·전체 Section A-E 프롬프트 / #2 "Autocompact is thrashing" — 다이어트 스폰, 정찰 후 사망). 두 사망 모두 부작위(커밋 0·구현 쓰기 0 — worktree·main 상태 리드 실물 대조 4/4 확인). memory `glm-subagent-context-death` 확립 패턴 + 형제 SPEC run 선례(스폰 4회 사망 → direct 마무리). 3회째 재스폰 금지 지시.

**구현 내역** (REQ-SDU-001~005, 008):
- `common/MetricCell.tsx`: `rating0`/`pct0` `export function` 추가(G-F5 (a)안 — 화살표 아님) + 계열 주석
- `utils/rsMetrics.ts` 신설: 4 상수(RS_TOP_THRESHOLD=80 외 3) + `utils/__tests__/rsMetrics.test.ts`(교차 언어)
- 14개 핀 호출부 전환: `SectorRankingTable`(188→rating0·197/206/215→pct0), `SectorDetailPanel`(99·139·181→rating0, 100-102·142→pct0 — MetricCard MetricValue 수용·보간 제거), `SectorBubbleChart`(249→rating0), `ChartCell`(297 Math.round 제거→rating0+상수), `StockTable`(229→rating0)
- 라벨: 'RS Top %'→'RS 80+ 비중'(열+카드+임계값 title), Y축→'RS Rating 평균 (0-100)', markLine→'RS 50 (유니버스 백분위 중앙)'(50→RS_UNIVERSE_MIDPOINT), ChartCell 배지→'RS등급', RRG 캡션 신설(rrg-metric-caption)
- 색 램프: `getCellColor` 제3 type `'rating'`(보라 rgba(139,92,246)) — rs_avg 셀 전환, rs_top_pct는 기존 파란 채널
- 테스트: 기존 2종 라벨 갱신 + 신규(색램프 분리·rating0 반올림·null%·3면 동일성)

**검증 (커밋 전, HEAD f11730d 트리에 적용 후)**:
```
$ cd frontend && npm run typecheck            → exit 0
$ <AC-SDU-001 핀 스캔 — 정정 패턴>             → 출력 0줄, exit 1 (잔여 0)
$ npx vitest run <M6 4파일>                    → 4 suites passed, 38 tests passed
    (SectorRankingTable 21 · SectorDetailPanel 15 · rsMetrics 2 · rsDisplayConsistency 1 — 최초 실행에서
     rsMetrics만 "TypeError: The URL must be of scheme file" 로 적색 → import.meta.url 의 vitest(jsdom)
     /@fs/ 형태 처리 추가 후 재실행 2 passed. CWD 가정 없이 모듈 URL 기준 유지)
$ npx eslint <§F.1 범위> --max-warnings=0      → exit 1, ✖ 23 problems (23 errors, 0 warnings)
```

**eslint 델타 (AC-SDU-012 차원) — B \ A == ∅ PASS**: (파일,규칙) 다중집합 대조. B: ChartCell any×2·refs×4(행이동 392/394→401/403), MetricCell only-export×7(=A 5+선언 예외 2 — 정확히 일치), RRGChart×2, SectorAnalysis×1, SectorBubbleChart×1, zoom 테스트 immutability×4, StockExplorer×2. **신규 (파일,규칙) 쌍 0건.** 소실 5건(ChartGrid/__tests__ no-unused-vars ×3+×1+×1)은 내가 미변경 파일 — t5 커밋 f11730d의 테스트 갱신 소관이며 D12대로 의도적 미확인 대상. 기준선 §F.1 실측일(2026-08-18)이 f11730d 이전 트리였던 것으로 추정.

**스캔 패턴 정정 (M6 커밋 이전)**: 최초 핀의 `label="RS Avg" value={sector.rs_avg}` 패턴이 전환된 형태(`format={rating0}` 부착)를 부분 매칭해 잔여 1 오탐. 종결자 ` />` 추가로 미전환 형태만 매칭. 킥오프 14줄 관측 출력은 불변(원 라인이 모두 `} />` 종결). acceptance.md 동시 갱신.

**RED 사양 확인 (신규 테스트가 구현 전 상태를 실패시킬 수 있었는지)**: 되돌림 판정(§E.2.3)에서 관측한다 — 각 AC의 되돌림이 해당 테스트를 RED로 만드는지가 판정 기준이므로 사전 RED 캡처는 판정 요건이 아님(acceptance 규약). 신규 테스트 전부 구현 후 GREEN 관측 완료.

### §E.2.2 M7 구현

_<pending>_

### §E.2.3 AC 판정 (되돌림 RED 관측)

_<pending>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
