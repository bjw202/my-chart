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

**eslint 델타 (AC-SDU-012 차원) — B \ A == ∅ PASS**: (파일,규칙) 다중집합 대조. B: ChartCell any×2·refs×4(행이동 392/394→401/403), MetricCell only-export×7(=A 5+선언 예외 2 — 정확히 일치), RRGChart×2, SectorAnalysis×1, SectorBubbleChart×1, zoom 테스트 immutability×4, StockExplorer×2. **신규 (파일,규칙) 쌍 0건.** 소실은 총 **6건**(리뷰 F4 정정 — 최초 5건 기록에서 1건 누락): ChartGrid/__tests__ no-unused-vars 5건(×3+×1+×1, t5 커밋 f11730d 소관) + `SectorAnalysis/__tests__/SectorDetailPanel.test.tsx:307` no-unused-vars 1건(본 SPEC 이 M6 에 수정한 파일 — 라벨 갱신 편집 중 미사용 심볼이 해소됨). D12대로 `A \ B`는 판정 대상이 아니며 산술 27 − 6 + 2 = 23 이 성립한다.

**스캔 패턴 정정 (M6 커밋 이전)**: 최초 핀의 `label="RS Avg" value={sector.rs_avg}` 패턴이 전환된 형태(`format={rating0}` 부착)를 부분 매칭해 잔여 1 오탐. 종결자 ` />` 추가로 미전환 형태만 매칭. 킥오프 14줄 관측 출력은 불변(원 라인이 모두 `} />` 종결). acceptance.md 동시 갱신.

**RED 사양 확인 (신규 테스트가 구현 전 상태를 실패시킬 수 있었는지)**: 되돌림 판정(§E.2.3)에서 관측한다 — 각 AC의 되돌림이 해당 테스트를 RED로 만드는지가 판정 기준이므로 사전 RED 캡처는 판정 요건이 아님(acceptance 규약). 신규 테스트 전부 구현 후 GREEN 관측 완료.

### §E.2.2 M7 구현

**구현 내역** (REQ-SDU-006~011, M6 커밋 0023210 위에 중첩):
- `api/market.ts`: `fetchSectorRanking(market?, period?)` — period 전송 시 봉투 `data[]` 의 기간 순위 수신(백엔드 `routers/sectors.py:46` Query `period` ^(1w|1m|3m)$ 확인)
- `MarketContext.tsx`: `periodRef`(marketRef 관용 확장) + effect dep `[market, period]` — 기간 토글 시 재조회. overview 도 재조회되나 값은 period 무관(무해, 주석 명시)
- `types/market.ts`: `SectorAggregateItem { name, rank: number|null, rank_change: number|null }` 최소형 + `data?` 필드(DEC-F5)
- `SectorAnalysis.tsx`: `joinedSectors` useMemo — 이름 조인으로 rank/rank_change 덮어쓰기(EF-2 조인 실패·EF-3 빈 배열·rank null 은 composite 유지), `periodRankingActive`/`partialFallbackCount` 산출, 정렬 소스를 joinedSectors 로 전환, `:218` 고지 띠 표시 라벨(PERIOD_LABELS/MARKET_LABELS)
- `SectorRankingTable.tsx`: `activePeriod`(선택 기간 열 `(순위 기준)` 마커 — 기간 랭킹 활성 시에만), `compositeFallback`(캡션 `순위 기준: 종합점수(3기간 가중)`), `partialFallbackCount`(부분 조인 실패 고지). 세 수익률 열 유지(DEC-F4)
- `SectorBubbleChart.tsx`: `MARKET_BENCHMARK_LABEL` kospi/kosdaq → 'KOSPI 상한가중'/'KOSDAQ 상한가중' — X축 라벨이 정의 B(상한 시쟁가중 유니버스)를 시장 무관 서술

**검증 (커밋 전)**:
```
$ npm run typecheck                              → exit 0
$ npx vitest run src/components/SectorAnalysis/__tests__ → 27 files / 261 tests passed
$ npx eslint <§F.1 범위> --max-warnings=0        → exit 1, ✖ 23 problems — (파일,규칙) 다중집합이
  M6 측정과 동일(행이동만: SectorAnalysis.tsx set-state 115→144). B \ A == ∅, 신규 0건
```

**§D 목록 정정 (투명 기록)**: `SectorAnalysis.m4.test.tsx` 고지 띠 단언(`:66-67`, `toContain('1m')`/`toContain('all')`)이 REQ-SDU-010 이 정확히 교체하는 원시 상태값을 단언해 적색화 — 계획 §D 가 놓친 **의도적 갱신 대상**으로 판정, `toContain('1M')`/`toContain('All')` 로 갱신. §D 의 delivery 라인번호도 실측으로 정정됐던 전례와 동일 계열이며, 갱신 근거는 커밋 diff로 감사 가능. **AC-SDU-013 판정 시 이 1건은 "의도적 갱신"으로 계상한다.**

**구 라벨 잔여 최종 측정 (AC-SDU-004 보조)**: 소스(테스트 제외)에서 `'RS Top %'`·`'RS 중앙'`·`'RS 평균 (0-100)'` 스캔 → **잔여 0** (주석 2건은 변경 서술 문자열로 라벨 아님). 테스트 파일에도 잔여 0.

> ⚠️ **위 검증 블록의 범위 한계 (리드 정정으로 밝혀짐 — §E.2.4 참조)**: 위 `npx vitest run src/components/SectorAnalysis/__tests__` 는 §F 가 지정한 전체 스위트를 **디렉터리로 좁힌 실행**이었다. §F.1 범위 각주가 명시한 ChartGrid/·common/ 을 보지 못해 3건의 §D 누락 갱신 대상 실패를 놓쳤다. 축자 전체 실행 결과와 재판정은 §E.2.4.

### §E.2.3 AC 판정 (되돌림 RED 관측)

**M6 판정 (2026-08-19, 커밋 0023210 트리 — 각 되돌림 후 복원, 최종 4스위트 38 tests passed + `git status --short -- frontend/src my_chart/` 출력 없음으로 트리 무결 증명)**

| AC | 판정 | 되돌림 → RED 관측 (verbatim 요지) |
|---|---|---|
| AC-SDU-001 | **PASS** | RankingTable RS Avg 셀을 `format={(n) => String(Math.round(n))}` 로 되돌림 → 핀 스캔 정확히 **1줄** 반환(`SectorRankingTable.tsx:200 …`) → 복원 후 0줄·exit 1 |
| AC-SDU-002 | **PASS** | MetricCard를 구형(string\|number + 원시 렌더)·호출부를 `` value={`${sector.rs_top_pct}%`} `` 로 되돌림 → `AssertionError: expected 'RS AvgRS 80+ 비중null%52W High %…' not to contain 'null'` (null% 문자 재현) → 복원 |
| AC-SDU-003 | **PASS** | 안전 규약 하 `my_chart/analysis/sector_metrics.py:58` 을 85.0으로 임시 편집 → `AssertionError: expected 80 to be 85 // Object.is equality` → 복원 80.0 + `git status --short -- my_chart/` 출력 없음. **And 조항**: StockTable:62 `rs_12m > RS_S2_STRONG_THRESHOLD`(+렌더 title), ChartCell:303 `>= RS_TOP_THRESHOLD`(+title) grep 관측. **공개**: 복원 sed가 cwd 함정(frontend/ 상대경로)으로 1회 실패 — 절대경로로 즉시 복원, 최종 청결은 git 무출력으로 증명. 단일 스텝이 순간적으로 깨졌으나 부작용 없이 종결 |
| AC-SDU-004 | **PASS** | 열 라벨을 'RS Top %'로 되돌림 → `TestingLibraryElementError: Unable to find an element with the text: RS 80+ 비중` → 복원. 나머지 라벨(Y축·markLine·RS등급·RRG 캡션)도 동일 계열 변경으로 header/렌더 단언이 커버 — 구 문자열 잔여는 아래 Grep 확인 |
| AC-SDU-005 | **PASS** | rs_avg 셀을 `'percentage'`로 되돌림 → `AssertionError: expected 'rgba(59, 130, 246, 0.3)' not to be 'rgba(59, 130, 246, 0.3)'` (두 셀 동일 파랑 수렴) → 복원 `'rating'` |
| AC-SDU-008 | **PASS** | 버블 툴팁을 `n => n.toFixed(1)`로 되돌림 → `AssertionError: expected '<b>Alpha</b><br/>초과수익률: 1.20%<br/>RS …' to contain 'RS 평균: 63'` (62.6 발산) → 복원 rating0 |
| AC-SDU-012 | **PASS — §E.2.4 정정 재판정** | ~~원 판정(레인 로컬 좁힘 증거)~~ 무효 — §F 축자 전체 실행 기준으로 §E.2.4 재판정: 리드 재현 실패 3건 = §D 누락 갱신 대상(회귀 아님), §D 7종 등재 후 축자 실행 typecheck 0 · vitest 735/735 · eslint B\A==∅ |

**AC-SDU-004 보조 grep (구 문자열 잔여 0)**: `'RS Top %'`·`'RS 중앙'`·`'RS 평균 (0-100)'` 각각 스캔에서 소스 잔여 0 — M7 종료 시 재측정해 §E.2.4에 기록.

**Gaps (M6)**: 없음 — 단 AC-SDU-004의 라이브 화면 확인(lessons #1/#2)은 DoD 항목으로 M7 랜딩 후 남음.

**M7 판정 (2026-08-19, M7 커밋 전 트리 — 각 주입·되돌림 후 복원, 최종 typecheck exit 0 + 27파일 261테스트 green + `git status --short -- frontend/src`가 M7 변경분만)**

| AC | 판정 | 되돌림/주입 → RED 관측 (verbatim 요지) |
|---|---|---|
| AC-SDU-006 | **PASS** | `joinedSectors` 조인 제거(sectors[] 만 반환) → `AssertionError: expected [ 'A', 'B', 'C' ] to deeply equal [ 'B', 'C', 'A' ]` → 복원 |
| AC-SDU-007 | **PASS** | `compositeFallback` 캡션 분기 무력화(`{false && …}`) → `TestingLibraryElementError: Unable to find an element by: [data-testid="ranking-basis-caption"]` → 복원 |
| AC-SDU-009 | **PASS** | 버블 series Y에 기간 오프셋 주입(`s.rs_avg + (period==='1w' ? 5 : …)`) → `AssertionError: expected 65 to be 60 // Object.is equality` (Y 이동) → 복원. X 변화 단언은 정상 구현에서 w.x≠m.x≠q.x 관측 |
| AC-SDU-010 | **PASS** | 선택 기간 열만 남기는 filter 주입 → `TestingLibraryElementError: Unable to find an element with the text: 1W` (열 소실) → 복원. 마커는 1M 헤더에만 존재(1W 헤더 not.toContain 대조) |
| AC-SDU-011 | **PASS** | 고지 띠를 원시 상태값 출력으로 되돌림 → `AssertionError: expected 'excess_w1 ↓ 기준 정렬 · 기간 1m · 시장 all — …' to contain '기간 1M'` → 복원 |
| AC-SDU-013 | **PASS — §E.2.4 정정 재판정** | ~~원 판정(디렉터리 좁힘 증거)~~ 무효 — §F 축자 전체 실행으로 교체: 갱신 대상 7종(§D) 반영 후 전체 스위트 실패 0건(84파일 735테스트)·typecheck exit 0·eslint B\A==∅ |

**Gaps (M7)**: 없음. EF-1(전 지표 null 섹터)은 M6 null% 테스트 + MetricCard MetricValue 수용이 구조적으로 커버(각 카드 '–', 행 소실 없음 — SectorRankItem 행 렌더는 값과 무관). EF-4(알 수 없는 기간값)는 PERIOD_LABELS 가 Record<Period,string> 타입으로 미지 키를 컴파일 타임 차단 — 런타임 미지값 경로 없음.

### §E.2.5 리뷰 소견 반영 — F1·F2·F3·F4 (2026-08-19, 카드 run 복귀 후)

**F1 — ChartCell 강조 술어 반올림값 통일 (운영자 결정)**: 표시는 `rating0`(반올림)·강조는 원시값이어서 `rs_12m ∈ [79.5, 80)` 에서 배지가 'RS등급 80'을 보이며 강조가 사라지던 경계 이동(변경 전 양쪽 반올림 일치의 회귀). 수선: 술어가 **표시 문자열을 그대로 읽는다** — `Number(rsDisplay) >= RS_TOP_THRESHOLD`. `Math.round` 직접 호출 미부활(REQ-SDU-001 위반 호출부)·`MetricCell` export 미증가(§F.1 예외 +2 산술 보존). 표시↔강조 일치가 우연이 아니라 구조가 됐다.
**되돌림 RED 관측 (F1)**: 술어를 원시값 기준(`stock.rs_12m >= …`)으로 되돌림 → `AssertionError: expected null to be truthy` (`ChartCellRsBadge.test.tsx` 79.5 경계 케이스 — 강조 소실 재현) → 복원. 신규 경계 단언 2건(79.5 강조 있음 + 표시 80 / 79.4 강조 없음 + 표시 79) 상시 관측.

**F2 — periodRankingActive rank null 가드**: 조인 성공의 정의를 '이름 일치'에서 **'기간 rank 존재'**로 좁히고(`data.filter(d => d.rank != null)`), `joinedSectors` 도 `d.rank != null`일 때만 rank·rank_change 를 함께 덮어쓴다(혼합 행 방지). 판정 근거: rank null 항목은 rank 가 composite 폴백인데 `periodRankingActive=true` 로 `(순위 기준)` 마커가 붙고 `compositeFallback`·`partialFallbackCount` 모두 0이라 아무 고지가 없던 것이 REQ-SDU-007 금지의 조용한 폴백. 도달성(sectors[] 교차)은 리드 소스 추론(비후보 aggregate `a.rank=None` → `data[]` 전량)로 확인됐으나 런타임 미관측 — 도달 여부와 무관하게 틀린 구조라 가드로 수선했다. 신규 테스트: data[] 전량 rank null → composite 캡션 + 마커 부재 단언.

**F3 — MetricTextParity 단언 강도 복구**: `toContain('RS 평균: 60')` 은 구 포맷 '60.0'에도 부분 매치되어 toFixed(1) 되돌림 미검출(공허 단언). `toContain('RS 평균: 60<br/>')` 정확 일치(줄 종결 앵커)로 복구 + 테스트 제목에 RS 라인 rating0 예외 명시.
**되돌림 RED 관측 (F3)**: 툴팁을 `n => n.toFixed(1)` 로 되돌림 → `AssertionError: expected '…RS 평균…' to contain 'RS 평균: 60<br/>'` — 검출 복구 확인(구 단언이었다면 통과했을 것) → 복원.

**F4 — 기록 정정**: §E.2.1 "소실 5건" → **6건** (누락 1건: `SectorDetailPanel.test.tsx:307` no-unused-vars — 본 SPEC 수정 파일에서 라벨 갱신 편집 중 해소). 27 − 6 + 2 = 23 산술 정합. 판정 불변(D12: `A \ B` 미확인 대상).

**§F 축자 재실행 (F1·F2·F3 적용 후, 2026-08-19)**:
```
$ cd frontend && npm run typecheck                          → exit 0
$ npx eslint <§F.1 범위> --max-warnings=0; echo $?          → 1, ✖ 23 problems — (파일,규칙) 다중집합
  직전 측정과 동일(Number() 추가는 export 미증가 → 예외 +2 산술 보존, B \ A == ∅)
$ npx vitest run --exclude "e2e/**"                         → 84 files / 738 tests all green
  (735 + 신규 3: F1 경계 2 + F2 rank-null 캡션 1)
```

### §E.2.4 리드 정정 — §F 전체 스위트 정정 판정 (2026-08-19)

**결함 공개**: §E.2.1/§E.2.2 에 기록한 vitest 증거는 §F 지정 명령(`npx vitest run --exclude "e2e/**"`)을 `src/components/SectorAnalysis/__tests__` 로 좁힌 실행이었다. §F.1 범위 각주가 M6 이 ChartGrid/·common/ 를 수정한다고 명시했으므로 좁힘은 근거 결함이다. 리드의 축자 재현에서 **3건 실패** 관측(증거: `.moai/state/verify/b3e680b5/vitest.out`):

| 실패 | 원인 REQ/AC | 처분 |
|---|---|---|
| `ChartGrid/__tests__/ChartCellRsBadge.test.tsx:82` (`/RS 76/`) | REQ-SDU-004/AC-SDU-004 — 배지 `RS {v}` → `RS등급 {v}` | `/RS등급 76/` 로 갱신 + §D 등재 |
| `ChartGrid/__tests__/ChartCellRsBadge.test.tsx:123` (`/RS -/`) | 동일 | `/RS등급 -/` 로 갱신 + §D 등재 |
| `common/__tests__/MetricTextParity.m7.test.tsx:119` (`'RS 평균: 60.0'`) | REQ-SDU-008/AC-SDU-008 — RS 툴팁 toFixed(1) → rating0 | `'RS 평균: 60'` 로 갱신 + §D 등재 |

세 건 모두 **회귀가 아니라 §D "의도적 갱신" 목록의 계획 시점 누락**(m4.test 정정과 동일 계열). 갱신 대상은 4종 → **7종**(§D 표에 근거 한 줄씩 등재 완료).

**완료 SPEC 단언 갱신 근거 (MetricTextParity — 리드 판단 동의)**: 이 파일은 SPEC-SECTOR-UX-001 D2 가 세우고 SPEC-SECTOR-METRIC-UNIFY-001 review 가 손댄 것이다. D2 의 실질 불변식은 **표 셀 ↔ 차트 툴팁 문자열 동등**(파일 헤더 명시)이며 `'60.0'` 은 당시의 부수 리터럴이다. REQ-SDU-008 은 RS 포맷을 3면 동시에 rating0 로 바꾸며 동등성을 유지한다(AC-SDU-008 3면 동일성 테스트가 동등 불변식을 실증) — D2 계약 생존, 부수 리터럴만 갱신. 블로커 회신 사유 없음(판단에 동의).

**§F 축자 재실행 (갱신 후, 전체 스위트 — 축자 명령)**:
```
$ cd frontend && npm run typecheck
  → exit 0
$ cd frontend && npx eslint src/components/SectorAnalysis src/components/common \
    src/components/ChartGrid src/components/StockExplorer src/utils --max-warnings=0 > /tmp/lint.out 2>&1; echo $?
  → 1   ✖ 23 problems (23 errors, 0 warnings) — (파일,규칙) 다중집합 §E.2.2 측정과 동일, B \ A == ∅
$ cd frontend && npx vitest run --exclude "e2e/**"
  → Test Files  84 passed (84) │ Tests  735 passed (735) │ Duration 29.32s
```

**AC-SDU-012 / AC-SDU-013 재판정 (§E.2.3 해당 행 정정)**:
- **AC-SDU-012 — 원 PASS 무효 → §D 정정 후 PASS.** 원 판정의 증거는 좁힌 실행이므로 "vitest 실패가 §D M6 대상에 한정" 근거로서 무효. 정정 근거: 리드 축자 실행(정정 전 트리)의 실패 3건이 전부 §D 누락 갱신 대상(회귀 아님 — `git diff` 상 두 테스트 파일 변경 0, 원인은 본 SPEC 소스 변경)이었고 §D 등재 후 축자 전체 실행 735/735. M6 단독 트리 조건은 §D 정정본 기준으로 성립.
- **AC-SDU-013 — 원 PASS 무효 → 정정 후 PASS.** 같은 이유로 근거 교체: 갱신 대상 7종 반영 후 전체 스위트 실패 0건·typecheck exit 0·eslint B \ A == ∅ (축자 증거 위).

**AC-SDU-004 보조 재측정**: 구 라벨 잔여 0 (§E.2.2 측정 유지 — 전체 스위트 green이 재확인).

**cwd 오염 노트 (frontend/.moai/ 재생성)**: `frontend/.moai/state/config-cache.json` 생성 시각(2026-08-19 00:11:05)이 본 세션의 `cd frontend && …` 배치 실행과 일치 — Bash cwd 가 frontend/ 인 순간 moai 훅이 프로젝트 루트를 CWD 로 오인해 캐시를 기록(B7 계열: CWD 폴백 누출). 미추적 상태 유지·커밋 미포함. 완화: 세션 내 Bash 는 절대경로 기준 `cd /…/my_chart && …` 로 시작하는 한 상관없음 — `cd frontend` 중첩 후 훅이 도는 것이 발생 조건.

## §E.3 Run-phase Audit-Ready Signal

- **run_status**: audit-ready
- **run_complete_at**: 2026-08-19
- **run_commit_sha**: 4059f44 — §E.3 이 주장하는 감사준비 상태(§F 축자 735/735 + AC-012/013 재판정)가 성립하는 트리는 정정 커밋 시점이다. 45ffaad 트리는 전체 스위트 기준 green 이 아니었으므로 유지 근거 없음
- **커밋**: M6 `0023210` (16파일, +448/−40) · M7 `45ffaad` (10파일, +381/−20 — api/market·MarketContext·types·SectorAnalysis·SectorRankingTable·SectorBubbleChart·테스트 3종 갱신 + sectorPeriodToggle 신설) · 정정 `4059f44` (§D 7종 등재 + 3단언 갱신 + §E.2.4)
- **AC 요약 (§E.2.4 정정본)**: AC-SDU-001~011 **PASS — 되돌림/주입 RED verbatim 관측**(§E.2.3) · AC-SDU-012/013 **PASS — §E.2.4 정정 재판정**(원 좁힘 증거 무효화 → §F 축자 전체 스위트 근거로 교체: typecheck 0 · vitest 84파일 735테스트 green · eslint B\A==∅. 갱신 대상 7종 §D 등재). 판정 경위(좁힘 결함→리드 독립 재현→정정)는 이력 보존
- **Gaps**: 0건 — 잔여는 DoD 의 라이브 화면 확인(lessons #1/#2)뿐
- **실행 방식**: orchestrator-direct(운영자 승인 A, 리드 경유) — 스폰 2회 사망 경위·부작위 관측은 §E.2.0/§E.2.1
- **미푸시 상태**: 본 SPEC 6커밋(0023210·45ffaad·ae2b8af·a2c1550·4059f44 + 본 §E.3 정리 커밋) — 본 커밋 착지 후 `git rev-list --count --left-right origin/main...HEAD` = `0 6`. t3·t5·t6 계열은 런 착수 전 pre-flight에서 이미 동기화(`0 0`)였다. push 시점은 리드/운영자 판단에 위임(전체 스위트는 push 후 CI)
- **G-F2 백로그 (범위 밖 기록 — spec.md §4)**: `ThemeAnalysis/ThemeRankingTable.tsx:33/:38/:43`이 같은 직접 포맷 패턴(`toFixed` 계열 percent 포매터 3종)을 가진다. 본 SPEC 범위 확장 금지 — 후속 백로그로만 남긴다.
- **라이브 확인 상태 (lessons #1/#2) — 해소 (2026-08-19, 운영자 판정)**: 색 채널 구분 양호(RS 등급 열 ↔ RS 80+ 비중 열)·차트 셀 배지 `RS등급 {v}` 가독성 문제없음(RS Line 버튼과 구분)·기간 토글 실동작 확인·나머지 라벨 이의 없음.
  **경위 기록 (재발 패턴)**: 최초 확인 시 기간 토글이 Table·Bubble 양쪽에서 무반응이었다 — 코드 결함이 아니라 **낡은 dev 서버**였다. M7 이 MarketContext.tsx 의 provider effect dep 를 `[fetchAll, market]` → `[fetchAll, market, period]` 로 넓혔는데, React Fast Refresh 가 이미 마운트된 provider 의 예전 effect 를 보존해 period 변경이 재조회를 트리거하지 못했다. 기간 버튼은 눌렸지만 숫자가 안 움직여 "선택 불가"로 보였다(버블은 `PERIOD_DISABLED_SUBTABS = ['rrg','bump']` 외라 원래 활성 — 첫 관찰의 "버블 선택 불가"도 같은 원인). 근거: 현 vite 프로세스 시작 01:00:00 > 마지막 커밋 a544c36 00:47:59, 그 사이 코드 변경 0(리드 명령은 전부 읽기 전용). 서버 재시작 후 동일 UI 정상 동작. **교훈: provider·hook dep·모듈 싱글턴을 건드린 변경의 라이브 확인은 dev 서버 재시작 후에 한다 — 안 하면 낡은 번들을 검사하고 미구현으로 오판한다.** (본 §E.3 이전 기술의 "Vite HMR — 변경 자동 반영" 주장도 이 함정의 일부였다: HMR 은 컴포넌트는 갱신하지만 마운트된 provider 의 effect 보존으로 dep 변경이 반영되지 않을 수 있다.)
- **ef 종결**: EF-1~EF-4 처분은 §E.2.3 M7 Gaps 노트 참조 (전부 구조적 커버 또는 타입 레벨 차단).

## §R 리뷰 (review 컬럼 — 카드 t2, 2026-08-19)

- **리뷰어**: review-tjvce8 세션 (칸반 리드 디스패치, `/moai review --deep`, 렌즈 `--deep` 단독)
- **대상**: `f11730d..8c94ab7` (25파일 +876/−61), main 체크아웃, `origin/main...HEAD` = `0 0`
- **증거 경로**: `.moai/state/verify/08214523/{tsc.out,eslint.out,vitest.out}`
- **판정**: **조건부 통과 — 차단 사유 0건.** run 되돌림으로 되돌릴 결함 없음. 후속 처리 항목 2건(F1·F2)과 기록 정확성 3건(F3~F5)을 아래에 남긴다.

### R.1 §F 축자 재현 (독립 실행 — 좁힘 없음)

```
$ cd frontend && npm run typecheck
  → exit 0
$ cd frontend && npx eslint src/components/SectorAnalysis src/components/common \
    src/components/ChartGrid src/components/StockExplorer src/utils --max-warnings=0 ; echo $?
  → 1   ✖ 23 problems (23 errors, 0 warnings)
$ cd frontend && npx vitest run --exclude "e2e/**"
  → Test Files 84 passed (84) │ Tests 735 passed (735) │ exit 0
```

**eslint 델타 독립 재구성 (B \ A 한 방향, A는 §F.1 다중집합 + 사전 선언 예외)** — 출력을 (파일,규칙) 다중집합으로 직접 파싱:

| 파일 | 규칙 | B | A | B\A |
|---|---|---|---|---|
| ChartGrid/ChartCell.tsx | no-explicit-any | 2 | 2 | 0 |
| ChartGrid/ChartCell.tsx | react-hooks/refs | 4 | 4 | 0 |
| SectorAnalysis/RRGChart.tsx | only-export / set-state-in-effect | 1/1 | 1/1 | 0 |
| SectorAnalysis/SectorAnalysis.tsx | set-state-in-effect | 1 | 1 | 0 |
| SectorAnalysis/SectorBubbleChart.tsx | only-export | 1 | 1 | 0 |
| SectorAnalysis/__tests__/SectorBubbleChart.zoom | immutability | 2 | 2 | 0 |
| SectorAnalysis/__tests__/StockBubbleChart.zoom | immutability | 2 | 2 | 0 |
| StockExplorer/StockExplorer.tsx | only-export / set-state-in-effect | 1/1 | 1/1 | 0 |
| common/MetricCell.tsx | only-export | 7 | 5 + **사전 선언 예외 2** | 0 |

**`B \ A == ∅` 독립 확인.** 산술도 맞는다: 27 − 소실 6 + 예외 2 = 23. 행 이동(392/394→401/403, 115→144)은 (파일,규칙) 다중집합 판정에 무영향.

### R.2 지적 4지점 적대 검토

**① 자기 판정 구조(orchestrator-direct — 쓴 자가 판정)**. §E.2.3 되돌림 표에서 lessons #9 위반(양변이 같은 함수/표현식) 후보를 전수 확인했다. 무효 항목 **0건**:

- **AC-SDU-003** — `rsMetrics.test.ts`가 `import.meta.url` 기준 경로로 `sector_metrics.py` **원문을 읽어** 정규식 추출 + `parseFloat`. 한 변이 손으로 옮겨 적은 상수가 아니다. 유효.
- **AC-SDU-005** — 픽스처 `rs_avg = rs_top_pct = 55`로 **같은 수치**를 넣고 두 프로덕션 `<td>`의 `style.background`를 비교. 헬퍼 직접 2회 호출이 아니다. 되돌림 시 양쪽 `rgba(59,130,246,0.3)`(둘 다 알파 클램프)로 수렴하는 관측과 일치. 유효.
- **AC-SDU-008** — 세 변이 각각 Table 렌더 / Panel 렌더 / Bubble **프로덕션 tooltip.formatter** 출력. `62.6 → '63'`이라 `toFixed(1)`('62.6') 되돌림을 실제로 검출한다. 유효.
- **AC-SDU-001 / AC-SDU-004** — 잔여 스캔을 직접 재현: 핀 스캔 **0줄**, 구 라벨(`'RS Top %'`·`'RS 중앙'`) 소스 잔여 **0**(매치 4건 전부 변경 서술 주석).
- **AC-SDU-006** — 픽스처 `sectors[1,2,3]` vs `data[3,1,2]` 순서 상이 확인(항진명제 아님).

**② 범위 좁힘 재발** — R.1대로 축자 전체 실행. 재발 없음. §E.2.4의 735/735 주장은 본 세션에서 **독립 재현**됐다.

**③ 교차 SPEC 계약(MetricTextParity)** — **판단에 동의한다.** 파일 헤더가 D2의 불변식을 "표 셀 텍스트 ↔ 차트 툴팁 텍스트 **문자열 동등**"으로 명시하고, 그 불변식을 지탱하는 단언(4소비자의 `MISSING_TEXT` 동등, `NaN` 누출 0)은 **한 줄도 건드려지지 않았다**. 갱신된 `:119`는 "값이 있으면 종전 포맷 유지" 테스트 안의 부수 리터럴이고, RS 포맷 변경은 3면 동시 적용이라 동등성은 보존된다(AC-SDU-008이 실증). 완료 SPEC 계약을 뒤집은 것이 아니다. 단 갱신 **값 선택**에 결함이 있다 → F3.

**④ M7 조인 로직** — `joinedSectors`(SectorAnalysis.tsx:94-104) 경로별 확인:
- 조인 전량 실패 → `periodJoinCount 0` → `compositeFallback` 캡션. AC-SDU-007 커버.
- `data` 부재/빈 배열 → `base` 그대로. EF-3(널 아님과 길이 0 무구분) 코드상 성립.
- 부분 실패 → `partialFallbackCount` 고지 띠. EF-2 커버. (순위 기준이 행마다 섞이는 것 자체는 EF-2가 승인한 설계이며 고지로 처리된다.)
- **`d.rank === null` 경로는 미가드** → F2.

### R.3 소견

| # | 등급 | 소견 |
|---|---|---|
| **F1** | **후속 처리 필요 (차단 아님)** | **ChartCell RS 강조 술어 경계 이동 — 표시와 술어의 반올림 기준 불일치.** `ChartCell.tsx:297-302`가 `rsValue = Math.round(rs_12m)` 제거 후 표시는 `rating0(rs_12m)`(반올림), 강조는 `stock.rs_12m >= RS_TOP_THRESHOLD`(**원시값**)로 갈렸다. 변경 전에는 양쪽 다 반올림값 기준이라 일치했다. 실행 확인: `rs_12m ∈ [79.5, 80)` 에서 배지는 `RS등급 80` 을 표시하면서 강조가 **사라진다**(79.5 → before `true` / after `false`). 기존 코드가 `Math.round` 를 쓰고 있었다는 사실 자체가 소수값 도달 가능성의 근거다. 어떤 AC도 이 술어를 관측하지 않고(`ChartCellRsBadge.test.tsx` 는 76 과 `-` 만) 되돌림 대상도 아니었다. REQ-SDU-001 의 "표시 반올림 단일 출처" 취지와 상충한다. **선택은 결정 사항이다**(표시-술어 일관성 우선 = `Math.round` 기준으로 통일 / 임계값 엄밀성 우선 = 표시도 절사 규약 재검토) — 리뷰어가 임의로 고르지 않는다. |
| **F2** | **후속 처리 필요 (도달성 미검증)** | **`periodRankingActive` 술어가 rank 존재가 아니라 이름 조인 성공만 본다 + `rank_change` 무가드 덮어쓰기.** `joinedSectors` 는 `rank: d.rank ?? s.rank` 로 null 을 방어하지만 `rank_change: d.rank_change` 는 가드가 없다. 한편 `periodJoinCount`(:107-113)는 **이름 일치만** 센다. 따라서 조인된 `d.rank === null` 인 섹터는 (a) rank 는 composite 폴백인데 (b) `periodRankingActive = true` 라 `(순위 기준)` 마커가 붙고 (c) `compositeFallback` 도 `partialFallbackCount` 도 0 이라 **아무 고지도 뜨지 않는다** — REQ-SDU-007 이 금지한 "조용한 폴백"의 잔여 구멍이며, 동시에 rank(composite)/rank_change(period) 혼합 행이 된다. **소스로 확인한 것**: 봉투 `data` 는 `agg.aggregates` 전량이고(`sector_ranking_service.py:106`) 비후보 섹터는 `a.rank = None` 으로 남는다(`sector_metrics.py:679`); `sectors[]` 는 `compute_sector_ranking`, `data[]` 는 `compute_sector_aggregates` 로 **산출 경로가 서로 다르다**. **미검증 갭**: rank=None 인 이름이 실제로 `sectors[]` 에도 나타나는지는 관측하지 못했다 — 도달성 미확인이므로 결함 확정이 아니라 **가드 부재**로 보고한다. 최소 수선안은 `periodJoinCount` 를 `d.rank != null` 조건으로 좁히고 `rank_change` 에도 동일 가드를 두는 것. |
| **F3** | 기록/테스트 강도 | **`MetricTextParity.m7.test.tsx:119` 갱신이 가드를 공허하게 만들었다.** `toContain('RS 평균: 60')` 은 구 포맷 문자열 `'RS 평균: 60.0'` 에도 **매치된다**(부분문자열). 즉 이 단언은 `toFixed(1)` 되돌림을 더는 검출하지 못한다. 계약 판단(③)은 옳지만 갱신 값 선택이 아쉽다 — 정확 일치나 소수부가 살아 있는 픽스처였다면 강도가 유지됐다. 실질 검출은 AC-SDU-008(`62.6 → '63'`)이 담당하므로 **커버리지 공백은 아니다**. 부수로, 그 테스트의 제목 "값이 있으면 종전 포맷을 그대로 유지한다(결측 경로만 바뀌었다)" 는 이제 RS 라인에 대해 참이 아니다(본문 주석은 경위를 설명하고 있다). |
| **F4** | 기록 정확성 | §E.2.1 의 "소실 5건(ChartGrid/__tests__ …)" 은 실제 **6건**이다. 누락된 1건은 `SectorAnalysis/__tests__/SectorDetailPanel.test.tsx:307 no-unused-vars` — 본 SPEC 이 실제로 수정한 파일이다. D12 대로 `A \ B` 는 판정 대상이 아니므로 **판정에는 영향 없다**(27 − 6 + 2 = 23 으로 산술이 맞아떨어진다). 기록만 정정 대상. |
| **F5** | 기록 정확성 | AC-SDU-009 의 X축 변화 단언은 판별력이 약하다. 픽스처가 기간마다 다른 `excess_return`(1.0/2.0/3.0)을 **직접 주입**하므로 `w.x ≠ m.x ≠ q.x` 는 `excess_return` 을 X 로 플롯하는 어떤 구현에서도 성립한다. 다만 AC 가 요구한 핵심 절반(Y 불변)은 주입 되돌림으로 RED 를 실제 관측했고 `w.y === RS` 상수 단언도 있어 "응답 전체가 상수여도 통과" 함정은 닫혀 있다. **판정 유지**, 강도만 기록. |

### R.4 확인했으나 이상 없던 것

- `MetricCell.tsx` 의 `rating0`/`pct0` 가 `export function` 선언(화살표 아님) — G-F5 (a)안 이행 확인, lint 예외 +2 와 정확히 대응.
- `StockTable.tsx` 의 `rs_12m > RS_S2_STRONG_THRESHOLD` 는 변경 전후 모두 원시값 기준이라 F1 같은 경계 이동이 없다.
- `MarketContext` 의 `periodRef` + `[market, period]` dep — `fetchAll` 안정성(`[]`) 유지, overview 동시 재조회는 주석대로 무해.
- `types/market.ts` 의 `SectorAggregateItem` 최소형 — 백엔드 스키마 복제 회피(DEC-F5) 타당.
- `totalRanked = sectors.filter(s => s.rank != null)` — 조인 후 rank 가 null 이려면 양쪽 다 null 이어야 하므로 AC-SUX-058 분모 의미 보존.
- 리뷰 중 트리 변경 0(읽기 전용). 훅 cwd 폴백으로 생긴 미추적 `.moai/` 잔여 3곳(§E.2.4 B7 계열 재발)은 정리했다.

### R.5 리드에게

- **카드 이동 가능**(차단 사유 없음). F1·F2 는 **본 SPEC 되돌림이 아니라 후속 결정 항목**으로 본다 — 둘 다 AC 가 관측하지 않는 지점이고, F1 은 표시 규약 결정을, F2 는 도달성 확인을 각각 필요로 한다. sync 로 넘길지 백로그로 남길지는 리드/운영자 판단.
- 본 절은 **커밋하지 않았다**(작업 트리에 하네스 잔여 684 경로 — 스윕 오염 회피). 필요 시 명시 pathspec 으로 스테이징하라: `git add .moai/specs/SPEC-SECTOR-DISPLAY-UNIFY-001/progress.md`


---

### §R.6 재확인 (범위 한정 — 커밋 `3b9398b`, 2026-08-19)

- **리뷰어**: review-tjvce8 세션 (칸반 리드 2차 디스패치, 범위 한정 — 전면 재리뷰 아님)
- **대상**: `8c94ab7..3b9398b` (7파일 +83/−13, 소스 2 / 테스트 3 / 문서 2), `origin/main...HEAD` = `0 0`
- **증거 경로**: `.moai/state/verify/08214523-r2/{tsc.out,eslint.out,vitest.out}`
- **판정**: **이관 가능 — 차단 사유 0건.** F1·F2·F3 수정이 각각 지적한 구멍을 실제로 닫았다. 신규 소견 **1건(F6, 문구 정확성 · 차단 아님)** + 참고 2건.
- **§R.1~§R.4 결론은 유효**하며 재수립하지 않았다.

#### R.6.1 §F 축자 재실행 (좁힘 없음)

```
$ cd frontend && npm run typecheck                                   → exit 0
$ cd frontend && npx eslint <§F.1 범위> --max-warnings=0 ; echo $?   → 1, ✖ 23 problems
$ cd frontend && npx vitest run --exclude "e2e/**"                   → 84파일 738테스트 all green, exit 0
```

**eslint 대조는 기계적으로 했다.** r1(수정 전) 출력과 r2(수정 후) 출력에서 모든 숫자를 치환한 뒤 `diff` 한 결과 **텍스트 차이 0** — 즉 (파일, 규칙, 개수)가 완전히 동일하고 유일한 변화는 행번호 이동(`ChartCell.tsx` `react-hooks/refs` 401:20→403:20, 403:20→405:20)뿐이다. D12 판정 기준상 `B \ A == ∅` 유지. 리드 주장과 일치하며 반증 없음. 테스트 총계도 735 + 신규 3 = **738**로 정확히 맞는다.

#### R.6.2 재확인 요청 5건

**① F1 이 경계 이동을 닫았는가 — 닫았다.** `rsHighlight = stock.rs_12m !== null && Number(rsDisplay) >= RS_TOP_THRESHOLD`. 술어가 표시 문자열을 그대로 읽으므로 표시-술어 불일치가 **구조적으로 불가능**하다. 실행 확인:

```
rs=79.4  display="79"  highlight=false  | 표시-술어 일치=true
rs=79.5  display="80"  highlight=true   | 표시-술어 일치=true   ← §R.3 F1 이 지적한 구멍
rs=79.9  display="80"  highlight=true   | 표시-술어 일치=true
rs=80    display="80"  highlight=true   | 표시-술어 일치=true
rs=null  display="-"   highlight=false  | null 가드로 Number("-")=NaN 미도달
```

`Number('-')` = `NaN` 경로는 **`stock.rs_12m !== null` 이 `&&` 좌변에서 단락**시키므로 도달하지 않는다. 타입도 확인했다 — `types/stock.ts:13 rs_12m: number | null` 로 `undefined` 가 없어 `=== null` 가드와 `!== null` 가드가 같은 집합을 막는다(두 가드가 어긋나는 제3 상태 없음). `rs=0` 도 정상(`Number('0') >= 80` false).

**회귀 무발생 확인**: AC-SDU-001 핀 스캔 잔여 여전히 **0**, 소스에서 RS 표시용 `Math.round` 직접 호출 부활 **없음**(남은 `Math.round` 는 거래대금·가격 포매터 등 무관 기존 코드와 `rating0`/`pct0` 정의부뿐). `MetricCell` export 불변 → eslint `only-export-components` 7건 유지로 §F.1 +2 산술 보존 확인.

**② F2 가드가 구멍을 닫았는가 — 닫았다.** 두 지점이 함께 좁혀졌다:
- `joinedSectors`: `d && d.rank != null` 일 때만 `rank`·`rank_change` 를 **함께** 덮어쓴다 → §R.3 F2 가 지적한 rank(composite)/rank_change(period) **혼합 행이 생성 불가**.
- `periodJoinCount`: `data.filter(d => d.rank != null)` 이름 집합과 교집합 → rank null 항목이 `periodRankingActive` 를 밀지 못한다.

**분기 일관성 확인** (`SectorAnalysis.tsx:115-118` 미변경, 새 정의와 대조):

| data[] 상태 | periodJoinCount | periodRankingActive | (순위 기준) 마커 | composite 캡션 | 부분 고지 | 판정 |
|---|---|---|---|---|---|---|
| 전량 rank 존재 | N | true | 표시(참) | 없음 | 0 | 일관 |
| 일부만 rank 존재 | 0<k<N | true | 표시(참 — 실제 k행이 기간 순위) | 없음 | N−k | 일관 |
| **전량 rank null** | **0** | **false** | **없음** | **표시** | **0** | **구멍 닫힘** |
| 부재 / 빈 배열 | 0 | false | 없음 | 표시 | 0 | 일관 |

`partialFallbackCount = 활성 ? sectors.length − periodJoinCount : 0` 는 새 정의에서 **오히려 더 정확해졌다** — 이제 "composite 로 남은 행 수"를 빠짐없이 센다(이름 미일치 + 이름 일치·rank null 양쪽). 이중 고지(캡션+부분 고지 동시 표시)도 발생하지 않는다(활성일 때만 부분 고지). 다만 그 **문구**가 어긋난다 → F6.

**③ F3 단언이 되돌림을 검출하는가 — 검출한다.** 툴팁은 `[...].join('<br/>')` 이고 `RS 평균` 은 마지막 요소가 아니므로 `<br/>` 종결 앵커가 항상 성립한다(`SectorBubbleChart.tsx:255-267`). 실행 확인:

```
신(rating0)  'RS 평균: 60<br/>' ⊂ 'RS 평균: 60<br/>기간…'   = true   ← 통과
구(toFixed1) 'RS 평균: 60<br/>' ⊂ 'RS 평균: 60.0<br/>기간…' = false  ← 되돌림 검출
(참고) 이전 앵커 'RS 평균: 60' 은 구 문자열에도 매치        = true   ← §R.3 F3 이 지적한 공허 상태
```

공허 단언 해소 확인. 제목도 `RS 라인은 rating0 예외` 로 정정돼 본문과 어긋나지 않는다.

**④ 신규 테스트 3건의 lessons #9 — 3건 모두 만족.**

| 테스트 | 양변 출처 | 판별력(구 코드에서 RED 인가) |
|---|---|---|
| `ChartCellRsBadge` 79.5 | **프로덕션 `<ChartCell>` 렌더** 의 텍스트 + `container.querySelector('.chart-cell-rs--high')` ↔ 리터럴 기대값 | **RED.** 구 술어(원시 `79.5 >= 80`)에서 클래스가 안 붙어 `toBeTruthy()` 실패 — 이 테스트의 존재 이유가 정확히 그 경계다 |
| `ChartCellRsBadge` 79.4 | 동일 | 대조군(구·신 모두 GREEN). 79.5 와 짝을 이뤄 "항상 강조" 구현을 배제 |
| `sectorPeriodToggle` 전량 rank null | **프로덕션 `<SectorAnalysis>` 렌더** 의 `ranking-basis-caption` textContent + `.rank-basis-marker` 부재 ↔ 리터럴 | **RED.** 구 정의(이름 일치)에서 `periodRankingActive` 가 true 라 캡션이 안 뜨고 마커가 붙어 양쪽 단언 모두 실패 |
| `MetricTextParity` `<br/>` 앵커 | **프로덕션 tooltip formatter 출력** ↔ 리터럴 | ③에서 실행 확인 |

단언 양변이 같은 표현식에서 오는 항목 **0건**. F1 경계 테스트가 프로덕션 렌더 결과(텍스트 + 클래스)를 본다는 요청 사항도 충족.

**⑤ 이 수정이 만든 새 문제 — 1건(문구), 차단 아님.**

| # | 등급 | 소견 |
|---|---|---|
| **F6** | **소견 (차단 아님 · 사용자 노출 문구)** | **부분 폴백 고지 문구가 새 정의와 어긋난다.** `SectorRankingTable.tsx:144` 는 `일부 {n}개 섹터는 **이름 조인 실패**로 종합점수 순위 유지` 라고 말하고 prop 주석(`:28`)도 같은 서술인데, F2 이후 `partialFallbackCount` 는 **이름 조인은 성공했으나 기간 rank 가 null 인 섹터도 포함**한다. 즉 문구가 원인을 단정하는데 실제 원인은 둘이다. 이 SPEC 이 REQ-SDU-004 로 "라벨이 실제를 정확히 서술할 것"을 요구한 것과 같은 계열의 부정확이다. 최소 수선은 `이름 조인 실패` → `기간 순위 없음` 류의 원인 중립 서술(주석 포함). **차단하지 않는 이유**: 오표기 조건이 rank null 항목이 실려야 발생하고(§R.3 F2 에서 도달성 미검증으로 남긴 그 조건), 잘못 표시돼도 행 수와 "종합점수 순위 유지" 라는 결론 자체는 참이다. |
| 참고 1 | INFO | **조인 성공 정의가 두 곳에 중복**된다 — `joinedSectors` 의 `d && d.rank != null` 과 `periodJoinCount` 의 `data.filter(d => d.rank != null)`. 현재는 일치하나 한쪽만 고치면 조용히 어긋나는 구조다(고지/마커와 실제 행이 불일치). 공용 술어로 뽑을 여지. |
| 참고 2 | INFO | `Number(rsDisplay)` 는 표시 문자열 → 수치 역파싱이라 `rating0` 의 출력 형식에 결합된다. RS 가 0-100 정수라 현재는 안전하지만, 훗날 `rating0` 이 천단위 구분자·접미사를 붙이면 술어가 조용히 `false` 로 죽는다(`Number('1,000')` = NaN). 표시-술어 일치를 얻은 대가로 받아들일 만한 결합이나 `rating0` 변경 시 동반 검토 대상이다. |

**F5 유지 확인**: 미수정 결정에 동의한다. AC-SDU-009 의 Y 불변 절반은 주입 되돌림 RED 로 실증됐고 `w.y === RS` 상수 단언이 "전체 상수" 함정을 닫고 있다.

#### R.6.3 리드에게

- **카드 이관 가능**(차단 0건). F6 은 사용자 노출 문구 한 줄 + 주석 한 줄로, 이번 카드에서 닫을지 백로그로 남길지는 리드/운영자 판단이다 — 리뷰어는 고르지 않는다.
- 리뷰 중 추적 파일 변경 0(읽기 전용 — 본 절 기록 외). 1차 때 정리했던 중첩 `.moai/` 재생성은 없었다. `frontend/.moai/`·`coverage/`·`test-results/` 미추적 잔여는 본 세션 이전부터 있던 것으로 §E.2.4 기록 범위다.
- 본 절은 **커밋하지 않았다**. 명시 pathspec: `git add .moai/specs/SPEC-SECTOR-DISPLAY-UNIFY-001/progress.md`

---

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
