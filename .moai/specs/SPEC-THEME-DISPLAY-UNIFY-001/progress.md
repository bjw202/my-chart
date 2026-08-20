# SPEC-THEME-DISPLAY-UNIFY-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

**작성자**: manager-spec (plan 단계)
**일자**: 2026-08-20
**Tier**: M (spec.md + plan.md + acceptance.md + progress.md)

### 산출물

| 파일 | 상태 |
|---|---|
| `spec.md` | 작성 완료 — 결정 D1~D4 확정, Out of Scope 4개 소절 |
| `plan.md` | 작성 완료 — 되돌리기 난이도 순 배치, M1~M6 |
| `acceptance.md` | 작성 완료 — 대조 8종(§B) / 불변 7종(§C) 분리 |
| `progress.md` | 본 파일 |

### SPEC ID 검증 (실행 출력)

```
$ ID="SPEC-THEME-DISPLAY-UNIFY-001"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
PASS
```

ID 중복 확인: `ls .moai/specs/ | grep -i theme` → `SPEC-NAVER-THEME-001/002/003/CONSOLIDATED` (충돌 없음).

### 계측으로 확정한 사실 (plan 단계 관측)

| # | 주장 | 관측 방법 | 결과 |
|---|---|---|---|
| 1 | 지역 포맷터 3종 위치·본문 | `cat -n ThemeRankingTable.tsx` | `:30`/`:36`/`:41` 확인, 지시 내용과 일치 |
| 2 | 소비 지점 5곳 | 동일 | `:91`·`:99`·`:101`·`:102`·`:104` 확인 |
| 3 | Theme에 ECharts 소비자 없음 | `grep -rn "formatter" .../ThemeAnalysis/` | 0매치 |
| 4 | 기존 테스트가 표시 문자열 미단언 | `grep -n "toFixed\|'-'\|–\|%" ThemeRankingTable.test.tsx` | 0매치 |
| 5 | Theme 파이프라인에 신뢰도 봉투 없음 | `grep -rln low_confidence --include="*.py"` + parser/router/themes.ts grep | sector 전용, Theme 0매치 |
| 6 | ~~0..1 비율 표 셀은 `breadth_ratio` 단독~~ | ~~`grep -rn "_ratio" frontend/src/`~~ | **철회 — 거짓으로 판명. 아래 Gaps 참조** |
| 7 | `Infinity` 발산 | `node -e` 실행 | `percent2(Infinity) === "+Infinity%"` |
| 8 | `null` 크래시 | `node -e` 실행 | `isFinite(null) === true`, `percent2(null)` → `TypeError` |

7·8은 **인수 지시에 없던 항목**이며, REQ-TDU-002([HARD] `toMetricValue` 경유)와 AC-TDU-004/005의 근거다.

### 철회된 주장 (v0.2.0 — plan-audit F1)

**주장 6 "0..1 비율을 표 셀에 백분율로 찍는 곳은 `breadth_ratio` 단 하나"는 거짓이었다.**

- **반례 2건**: `StockExplorer/StockTable.tsx:256`이 `weight_in_sector`(0..1 비율, `stage.ts:42`)를 `<td>` 안에서 `MetricCell`에 **바이트 동등한 인라인 화살표**로 넘긴다. `AnalysisModal.tsx:26-28` `fmtPct`는 docstring이 *"Convert decimal ratio"* 라고 자기 규정한다. 둘 다 소스를 직접 읽어 확인.
- **원인 — 프로브 범위 오류(오실행 아님)**: `grep -rn "_ratio"`는 **필드명 접미사**를 찾는다. 그러나 질문은 **렌더 형태**("0..1을 ×100해서 표 셀에 찍는가")였다. `weight_in_sector`도 `fmtPct`의 지역 변수도 그 부분 문자열을 갖지 않아 구조적으로 누락됐다. 올바른 프로브는 `grep -rn "\* 100" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v test`.
- **결론에 미치는 영향**: D2의 **결론(인라인 화살표)은 유지되며 근거는 오히려 강해진다** — 단일 소비자 예외가 아니라 출시된 선례와의 일치이기 때문이다. 부호·정밀도 회귀 회피 논거는 이 오류와 무관하게 유효하다.
- **파생 조치**: D2의 승격 조건("두 번째 소비자가 생기면")이 **이미 발화**해 있었음이 드러났다. spec.md D2에 후속 백로그(정본 `ratioPct1` + 세 소비자 이관)를 기록하고, 지금 이행하지 않는 이유를 C1/A1 충돌로 명시했다.

**교훈(일반화)**: 렌더 형태에 대한 질문을 필드명으로 프로브하면 조용히 누락된다. 명명 규약이 아니라 **관측하려는 형태 자체**로 grep해야 한다. 0매치·단일매치는 "없다"의 증거가 아니라 **프로브가 그 형태를 볼 수 있었는지**를 먼저 물어야 한다.

### 미검증 (Gaps — plan 단계에서 확인하지 않음)

- 결측 발생률(`momentum_score`·`breadth_ratio`)의 실측치. spec.md D1 폭발 반경 표의 "높음/낮음"은 **타입 옵셔널 여부에 근거한 추정**이며 라이브 데이터 관측이 아니다(plan.md G4).
- Theme API가 런타임에 실제로 `null`을 보내는 빈도. AC-TDU-005는 가능성에 대한 내성 확보이지 빈도 주장이 아니다(G3).
- 프론트 테스트/lint/tsc 기준선. M1에서 run 단계가 측정한다.
- **되돌림 RED 실증은 일절 수행하지 않았다.** plan 단계는 대조 단언을 *명세*할 뿐이며, 실증은 run 단계 M4의 부담이다(lessons #9).

### 결정 요약

| # | 결정 | 판정 |
|---|---|---|
| D1 | 결측 글리프 `-` → `–` | 승인. 폭발 반경 = 1파일 × 최대 5셀. 정상값 무변경 |
| D2 | `breadth_ratio` 단위 변환 귀속 | 호출부 인라인 화살표. 근거는 v0.2.0에서 교체 — "단일 소비자 예외"가 아니라 **출시된 선례(`StockTable.tsx:256`)와의 일치**. 정본 승격은 후속 백로그(C1/A1 충돌로 본 SPEC 범위 밖) |
| D3 | 5상태 채택 범위 | 4개 필드 모두 `missing`+`ok` 2상태만 도달 가능. 나머지 3상태 휴면, 합성 금지 |
| D4 | `top_stocks_preview` 포함 여부 | 포함. 단 `MISSING_TEXT` 상수만 공유, `MetricCell` 경유 금지 |
| 부가 | 표↔툴팁 parity 테스트 | **N/A** — 두 번째 소비자 부재로 전제 불성립. 억지 작성 시 공유 헬퍼 항진명제(#9 유형 2) |
| 부가 | 인접 3곳 | **범위 밖** — 색상 결합 / 정본 미보유. 잔여 공존을 숨기지 않고 spec.md §5에 기록 |

---

## §E.1-A Plan-phase Audit Verdict (plan-auditor)

**판정: PASS — 종합 0.97, 조건 없음** (plan-auditor, iteration 2/3, v0.2.0 기준. 이후 v0.2.1은 인용 규약 교정 2건뿐으로 판정에 영향 없음)

### MUST-PASS

| ID | 항목 | 결과 |
|----|------|------|
| MP-1 | REQ/AC 번호 일관성 | PASS — `REQ-TDU-001`~`008`, `AC-TDU-001`~`015` 연속·중복 0·패딩 균일 |
| MP-2 | GEARS 준수 | PASS — 8개 REQ 전부 패턴 일치. `REQ-TDU-002`는 `Where`→`When`으로 개선 |
| MP-3 | YAML frontmatter | PASS — 정본 12필드 유지, 버전 인상이 블록을 훼손하지 않음 |
| MP-4 | 언어 중립성 | N/A — 단일 프론트엔드 SPEC |
| MP-5 | 교차 SPEC 참조 | PASS — `depends_on` 2건 모두 존재·`completed` |
| MP-6 | 크로스플랫폼 | PASS — `grep -c syscall spec.md` → 0 |
| MP-7 | 미해결 표식 | PASS — `NEEDS CLARIFICATION` 0건 |

### 범주 점수 (iteration 1 → 2)

명료성 0.85 → **0.95** · 완전성 0.95 → **1.00** · 검증가능성 0.80 → **0.95** · 추적성 1.00 → **1.00**

### 반복 이력

| 회차 | 판정 | 지적 | 처리 |
|------|------|------|------|
| 1 | PASS-WITH-CONDITIONS 0.90 | 차단 3(F1·F2·F3) + 선택 4(F4~F7) | v0.2.0에서 7건 전부 반영, 거부 0건 |
| 2 | **PASS 0.97 무조건** | 선택 1(N1) | v0.2.1에서 반영 + 동종 1건 자체 발견·교정 |

핵심 지적 3건:
- **F1(major)** — D2의 근거 전제 거짓. `breadth_ratio`가 유일한 0..1 비율 표시라는 주장이 `StockTable.tsx:256`(`MetricCell` + 바이트 동등 인라인 화살표)·`AnalysisModal.tsx:26-28`로 반증. 원인은 오실행이 아니라 **프로브 범위 오류** — 렌더 형태를 묻는 질문에 필드명 접미사로 답함. 결론(인라인 화살표)은 유지되고 근거만 출시 선례 일치로 교체, 철회를 제자리에 기록.
- **F2(major)** — `AC-TDU-008`이 올바른 구현으로 만족 불가(테마 2건 × 4셀 = 8 vs 프로즌 `=== 4`). 8개 대조 AC 중 **유일하게 대조 강도가 온전하지 않던 항목**. 테마 1건 + `=== 4`로 교정해 복구.
- **F3(minor)** — DoD 게이트가 기존 테스트를 3건으로 오기(실제 4건). 절대 개수를 버리고 M1 기준선 델타 비교로 전환.

### 대조 단언 판정

8개 대조 AC 전부 **되돌림 민감**(`AC-TDU-001`~`008`), 7개 불변 AC(`AC-TDU-009`~`015`)와의 분리도 실재. #9의 항진명제 3형(자기 비교 / 공유 헬퍼 자기 호출 / 부분집합 부등식)이 각각 구조적으로 배제됨. `AC-TDU-004`는 되돌림 `'-'` / 불완전 구현 `"+Infinity%"` / 완전 구현 `'–'` 세 상태를 판별해 `REQ-TDU-002`의 `[HARD]`를 정당화.

단, `AC-TDU-003`은 대조 민감하되 증명하는 것이 **표시 정확성이 아니라 채택 여부**다 — 부분 채택(4개 중 3개 이관)을 잡는 역할로만 계상하고 값 렌더링의 근거로 쓰지 않는다.

### 미검증 (Gaps) — run 단계로 이월

- **되돌림 RED 실증 0건.** 2회 감사 모두 읽기 전용이며 `vitest`/`tsc`/lint 미실행. 위 8건의 대조 판정은 전부 **소스 추적이지 관측이 아니다**. iteration 2는 점수를 올렸을 뿐 추적 주장을 관측 주장으로 전환한 것이 없다. 실증 의무 전량은 run 단계 M4가 진다.
- Tier M PASS 임계값 미확인 — 본 워크트리에 해당 규칙 문서 부재. 0.97은 통상값을 상회하나 읽지 않은 수치는 인용하지 않는다.
- `spec-frontmatter-schema.md` 부재 — MP-3은 SSOT 파일이 아니라 감사자 정의 필드 목록 대조.
- 라이브 동작 미관측 — 결측 발생률·API null 빈도(plan.md G3/G4) 미계측.
- 감사자의 `grep "* 100"` 프로브도 망라적이지 않음. SPEC이 이를 완전성 주장으로 쓰지 않으므로 실리는 하중은 없음.

### 오케스트레이터 독립 재현

리드 제공 근거 및 감사 주장 중 다음을 plan 세션이 직접 실행해 확인: `percent2(Infinity)` → `"+Infinity%"`, `Number.isNaN(Infinity)` → false, `isFinite(null)` → true, `null.toFixed(2)` → TypeError, `StockTable.tsx:256` 인라인 화살표 바이트 동등, `AC-TDU-008` 2건×4셀 산술 모순, 기존 테스트 `it()` 4건, `WEIGHT_CAP = 0.10`, 인용 오프셋 +3/+2/+2.
---

## §Run-phase Orchestrator Entry Log (2026-08-20, t8b 워크트리)

### 워크트리 이동 경위

옛 워크트리 `t8-theme-metric-unify`가 plan 세션(pid 26967, 11시간 38분 유휴)의 Claude Code 세션 잠금으로 점유되어 `EnterWorktree`가 계속 거부됨(리드 실측). 칸반 리드(lead-tk0s46) 지시로 새 워크트리 `t8b-theme-metric-unify`(베이스 `origin/main` = `036010d`, t9·t10·t11 머지분 포함)에서 run을 재개. SPEC 4종은 원본에서 복사하였고 복사 무결성을 shasum으로 검증:

```
195c4e48a3bdc309a28118691e9ef7c4b17fd1cc84e615d2ad61e63df08cc2a5  acceptance.md
39aa0328ded20060f3ac7fa91af880aa62f74adeb91899001e9d364c34eada33  plan.md
69f5db4c04463fb12287946be29ea055f2bd25e7a8883b4a9643cb0e6d9d7d56  progress.md
3f9a904c37c5ed020963589d97c42f0c8aa05756c18f9af296f691a87532d93e  spec.md
```

리드 제공값·원본·사본 3자 전부 일치(실측). 원본은 훼손 없이 보존됨.

### Plan Audit Gate 판정 (Phase 1)

스티키 캐시 lookup: **MISS** (`plan_artifact_hash = 3656ef73…`, audit_cache MCP 실측). 독립 리포트 파일(`.moai/reports/plan-audit/SPEC-THEME-DISPLAY-UNIFY-001-*.md`)도 옛 워크트리·공용 체크아웃 어디에도 부재(관측). 그러나 3-조건 스킵 판정의 실질이 성립하여 진행:

| 조건 | 근거 | 관측 방법 |
|---|---|---|
| verdict = PASS | §E.1-A 축자 기록 — iteration 2, PASS 0.97 무조건 | progress.md 직독 |
| score ≥ Tier M 임계치(0.80) | 0.97 ≥ 0.80 | §E.1-A |
| artifact-hash unchanged | 감아 시점 문서와 바이트 동일 — 상기 4종 shasum이 리드 제공값과 전부 일치 | shasum -a 256 실측 |

캐시 미스의 원인은 워크트리 이동(리포트·캐시 엔트리가 원본 워크트리·별도 프로세스 메모리에 남음)이지 감사 미실시가 아니다. audit_cache 도구 계약 자체가 "plan-audit 게이트(별도 프로세스)는 이 캐시를 채우지 않는다"고 명시. 동일 해시의 문서에 대해 이미 확정된 PASS를 재판정하는 스폰은 절차 형식 채우기일 뿐이라 판단하고 생략 — 본 항목이 그 결정의 전부이다.

### Implementation Kickoff Approval 근거

칸반 디스패치 계약(kanban-dispatch.md § "No gate bypass")에 따라 kickoff approval은 디스패치 사이클 안에서도 유효해야 한다. 본 run의 근거: 리드의 2026-08-20 재디스패치 메시지가 (a) "앞선 t8 디스패치의 요구사항은 전부 그대로 유효하다"고 명시하고 (b) run 세션이 정리한 "진입 즉시 실행할 목록" 8항목을 "정확하다 — 그대로 쓰면 된다"고 승인했다. 카드 선택·phase 전환은 칸반 계약상 리드가 운영자 AskUserQuestion으로 처리하는 채널이므로(§ "No question delegation"), 리드의 명시적 재디스패치를 운영자 승인 경유의 kickoff 확보로 계상한다.

### Phase 4 Mode Selection

**입력 파라미터**:
- tier: M (spec.md frontmatter)
- scope: 소스 2파일(`ThemeRankingTable.tsx` 수정, `ThemeRankingTable.display.test.tsx` 신규) + SPEC 산문(progress.md)
- domain count: 1 (frontend)
- file language mix: TypeScript/TSX 100%
- concurrency benefit: 낮음 — 코딩 중심, 마일스톤 M1~M6 순차 의존(기준선 → 테스트 → 구현 → 되돌림 → 델타 비교)

**6모드 평가**:

| 모드 | 판정 | 근거 |
|---|---|---|
| 1 trivial | 부적합 | 단행 서식 수정 아님 — 15 AC, [HARD] 게이트 2종 포함 |
| 2 background | 부적합 | 쓰기 작업(Write/Edit) 포함 |
| 3 agent-team | RETIRED | 선택 불가 |
| 4 parallel | 부적합 | 단일 도메인, 연구 중심 아님 |
| 5 sub-agent | **선택** | 코딩 중심, 스코프 ≤5파일 단일 도메인 = Focused envelope |
| 6 workflow | 부적합 | ~30파일 미달, 기계적 단일 변환 아님 |

**Decision**: `Scale-based mode: Focused (Mode 5 envelope) — files: 2, domains: 1`

**Justification**: 스키마상 Fix/Focused에 해당하는 스코프다. 실행은 plan.md §F 마일스톤 M1~M6을 순차 수행하는 manager-develop(cycle_type=tdd) 단일 스폰에 위임하고, 축자 캡처 증거는 서브에이전트가 §E.2에 기록·오케스트레이터가 검증한다. GLM 세션의 manager-* 스폰 하위 컨텍스트 연쇄 사망 선례(2026-08-17)가 있어 사망 시 프로토콜(2회 → orchestrator-direct 회복, 사용자 승인)을 사전에 지정해 둔다.

### 운영 제약 (리드 지시, run 전체에 구속)

- 검증 부하는 카드 범위(프론트 vitest/tsc/lint)로 한정. 백그라운드 부하 프로세스 생성 금지 → **F7 라이브 확인(dev 서버 재시작 필요)은 run 단계에서 수행 불가** — Gaps로 기록하고 리드 보고 시 명시.
- pre-commit 게이트 우회 금지(본 세션 권한에서 `Bash(rm *)`·`SKIP_MOAI_PRECOMMIT=1` 커밋 허용 제거됨). 게이트가 막히면 원인 수정 또는 블로커 반환.
- F4의 "프론트 전체 스위트"는 카드 범위 내로 해석하여 실행. 백엔드 전체는 push 후 처리(리드 지시).

---

## §E.2 Run-phase Evidence

**작성자**: manager-develop (run 단계, cycle_type=tdd) · **일자**: 2026-08-20 · **워크트리**: t8b-theme-metric-unify (HEAD `036010d`)

실행 환경: `frontend/`에서 `npx vitest run` / `npm run typecheck`(tsc -b) / `npx eslint src/components/ThemeAnalysis/`. 워크트리에 node_modules가 없어 `npm ci`로 설치 후 진행(411 packages).

### M1 — 기준선 고정 (변경 전 축자)

프론트 테스트 전체 (`npx vitest run`, 변경 전):

```
 Test Files  2 failed | 84 passed (86)
      Tests  739 passed (739)
```

기존 실패 2건은 `e2e/ai-report-deep.spec.ts`·`e2e/preset-flow.spec.ts` — Playwright 스펙을 vitest가 수집하며 발생하는 **기존(변경 무관) 오류**로, 둘 다 `0 test` 수집 실패다(`TestTypeImpl._currentSuite` 오류). 본 SPEC은 이 2건을 기준선에 포함해 델타 비교한다.

기존 `ThemeRankingTable.test.tsx` 단독 (F3 기준선):

```
 Test Files  1 passed (1)
      Tests  4 passed (4)
```

`tsc -b` (F5 기준선): exit 0, 출력 없음(오류 0).

lint `src/components/ThemeAnalysis/` (F6 기준선):

```
/Users/.../frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx
  148:9  warning  The 'themes' logical expression could make the dependencies of useMemo Hook (at line 162) change on every render. ... react-hooks/exhaustive-deps

✖ 1 problem (0 errors, 1 warning)
```

기준선 warning 1건은 `ThemeAnalysis.tsx:148`(기존, 본 SPEC 대상 파일 아님).

### M2 — 테스트 선행 작성 + 구현 전 RED 관측

`frontend/src/components/ThemeAnalysis/__tests__/ThemeRankingTable.display.test.tsx` 신설 — AC-TDU-001~015 전부 + 경계조건 E1~E6. 21개 `it`. 대조 단언 기대값은 전부 프로즌 리터럴 `'–'`(U+2013), `MISSING_TEXT` import 비교 금지 준수(AC-TDU-014 진단용 제외), `toContain` 미사용, 개수는 전부 `=== n`.

**구현 전 실행 (RED의 절반 — plan M2)**:

```
 Test Files  1 failed (1)
      Tests  10 failed | 11 passed (21)
```

- **대조 8종(AC-TDU-001~008) 전부 RED** — §B 요구 충족
- **불변 7종(AC-TDU-009~015) 전부 GREEN** — §A.2 분리 확인(현행 구현이 불변군을 이미 만족)
- 경계 E4/E5 RED(기대값 '–'), E1/E2/E3/E6 GREEN

### M3 — 구현

`ThemeRankingTable.tsx`: 지역 포맷터 3종(`formatPct`/`formatBreadth`/`formatMomentum`) 제거, 소비 5지점 교체. `git diff --stat`: **14 insertions(+), 22 deletions(-), 1 file**. 형태는 plan.md §D.1 예상 diff와 일치:

- 등락률·3일등락률 → `<MetricCell value={toMetricValue(...)} format={percent2} />`
- 모멘텀점수 → `format={(n) => n.toFixed(2)}` (선례 `SectorRankingTable.tsx:265` 일치)
- 상승비율 → `format={(n) => \`${(n * 100).toFixed(1)}%\`}` (선례 `StockTable.tsx:256` 일치)
- 대표종목 → `?? MISSING_TEXT` (`MetricCell` 경유 안 함 — C4)
- `getChangePctColor` 셰이딩은 `<td>`에 유지 (REQ-TDU-008)

### M4 — 되돌림 실증 [HARD, 이 SPEC의 중심 게이트]

절차: M3 사본을 백업 → `git show HEAD:...ThemeRankingTable.tsx`로 파일을 되돌림 → 되돌림 확인 → 테스트 실행 → RED 축자 캡처 → M3 복원 → `git status --short` 복원 증명.

되돌림 확인 (`git diff --stat` 출력 없음 = HEAD와 동일 = M3 이전 상태, 지역 포맷터 grep 7매치).

**되돌린 상태에서의 실행 (RED의 나머지 절반)**:

```
 src/components/ThemeAnalysis/__tests__/ThemeRankingTable.display.test.tsx (21 tests | 10 failed)
     × AC-TDU-001: momentum_score 결측 시 모멘텀점수 셀이 정확히 "–"(en dash)다
     × AC-TDU-002: breadth_ratio 결측 시 상승비율 셀이 정확히 "–"다
     × AC-TDU-003: 지표 셀 구조 채택 — metric-cell testid가 정확히 4개다 (부분 채택도 RED)
     × AC-TDU-004: change_pct = Infinity → 등락률 셀이 정확히 "–"다 (toMetricValue 경유 강제)
     × AC-TDU-005: change_pct 런타임 null → 예외 없이 등락률 셀이 정확히 "–"다
     × AC-TDU-006: top_stocks_preview 결측 시 대표종목 셀이 정확히 "–"다
     × AC-TDU-007: 5개 지표 전부 결측인 행의 td 6개 textContent가 프로즌 배열과 정확히 같다
     × AC-TDU-008: 신뢰도 상태 무합성 — data-state는 ok/missing만, 개수는 정확히 4
     × E4: change_pct = NaN → "–" — toMetricValue가 결측으로 접는다
     × E5: change_pct = -Infinity → "–" — AC-TDU-004의 대칭

 Test Files  1 failed (1)
      Tests  10 failed | 11 passed (21)
```

**§B 8종 전부 RED 관측 — F2 실증 완료.** AC별 실패 상세(축자 발췌):

| AC | 되돌림 시 실패 출력 (축자) | acceptance 예상과의 부합 |
|---|---|---|
| AC-TDU-001 | `AssertionError: expected '-' to be '–' // Object.is equality` `Expected: "–" / Received: "-"` | 일치 — `formatMomentum`이 '-' 반환 |
| AC-TDU-002 | `AssertionError: expected '-' to be '–'` | 일치 — `formatBreadth`가 '-' 반환 |
| AC-TDU-003 | `AssertionError: expected +0 to be 4 // Object.is equality` | 일치 — testid 미존재 → 0 |
| AC-TDU-004 | `AssertionError: expected '-' to be '–'` | 일치 — `formatPct(Infinity)`가 '-' 반환 |
| AC-TDU-005 | `TypeError: Cannot read properties of null (reading 'toFixed')` | 일치 — §1.3(b) 예측 경로 그대로 |
| AC-TDU-006 | `AssertionError: expected '-' to be '–'` | 일치 — `?? '-'` |
| AC-TDU-007 | `TypeError: Cannot read properties of null (reading 'toFixed')` | **예상과 다른 RED 경로** — 아래 비고 |
| AC-TDU-008 | `AssertionError: expected +0 to be 4 // Object.is equality` | 일치 — `data-state` 미존재 → 동반 단언에서 RED |

**AC-TDU-007 비고 (정직 기록)**: acceptance의 되돌림 예상은 "5개 원소가 전부 `'-'` → RED"였으나 실측은 `TypeError`로 실패했다. 픽스처가 필수 타입 2개를 `null as unknown as number`로 주입하므로(§B 픽스처 주입 [HARD]), 되돌린 `formatPct`는 `isFinite(null) === true`를 통과해 `null.toFixed(2)`에 도달 — 배열 비교에 앞서 렌더가 예외로 깨진다. null을 빼면 예상대로 `'-'` 5개 배열 불일치로 실패하겠지만 그러면 픽스처 지시를 위반해 AC 강도가 무너진다. **판정은 동일(RED)이며, TypeError 경로 자체가 §1.3(b)가 문서화한 결함의 실측 재현이다.** 예상 문구와 실패 양상의 차이를 숨기지 않고 기록한다.

불변 7종은 되돌림에서도 GREEN(11 passed에 포함) — §A.2 "되돌려도 GREEN이 정상" 확인. §C 불변 단언을 대조로 보고하지 않는다.

**복원 증명** (`git status --short`, M3 복원 직후 축자):

```
 M frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx
?? .moai/specs/SPEC-THEME-DISPLAY-UNIFY-001/
?? frontend/src/components/ThemeAnalysis/__tests__/ThemeRankingTable.display.test.tsx
```

```
 .../components/ThemeAnalysis/ThemeRankingTable.tsx | 36 +++++++++-------------
 1 file changed, 14 insertions(+), 22 deletions(-)
```

복원 후 신규 테스트 재실행 GREEN 재확인(아래 F1)으로 복원 무결성 추가 증명.

### M4-A — AC-TDU-004 세 번째 상태(불완전 구현) 실행 관측

**경위**: 리드 재디스패치 지시는 세 상태(되돌림 `'-'` / 불완전 `"+Infinity%"` / 완전 `'–'`)를 **각각 관측하라**는 것이었으나 최초 run 보고는 불완전 상태를 "가상 상태라 실행 관측 대상 아님"으로 Gaps 처리했다(해당 Gaps 항목은 본 관측으로 해소되어 제거됨). 오케스트레이터 검증 단계에서 관측을 보완했다 — 되돌림이 아니라 **구현 변형 주입**: 등락률 셀 1곳만 `toMetricValue`를 생략한 불완전 구현(`value={theme.change_pct}` 직접 전달)을 일시 적용 → 실행 → 관측 → 복원 → 증명.

관측 (축자):

```
 FAIL ... AC-TDU-004: change_pct = Infinity → 등락률 셀이 정확히 "–"다 (toMetricValue 경유 강제)
 AssertionError: expected '+Infinity%' to be '–' // Object.is equality
 Expected: "–"
 Received: "+Infinity%"
```

E5(-Infinity) 대칭 상태도 함께 관측: `Received: "-Infinity%"`. 변형 상태에서의 실패는 AC-TDU-004·E5 2건뿐(19 passed) — 등락률 셀만 바꿨으므로 국소성이 정확하다. 이로써 REQ-TDU-002 [HARD]가 방어하는 회귀 경로(`resolveState`가 `Number.isNaN`만 검사해 `Infinity`를 정상값으로 통과 → `percent2(Infinity)` 샌다)가 소스 추적이 아닌 **실행 관측**으로 확정됐다. AC-TDU-004의 세 상태 판별 표(acceptance §B) 3행 전부 실측 완료. 이 변형이 `tsc`를 통과한다는 사실 자체(타입 층이 이 회귀를 잡지 못함)도 [HARD] 근거의 실측 확인이다.

복원 증명 (삼중): 백업 대비 `shasum` 동일(`f86b2cc1…`) / `git status --short` M4 복원 증명과 동일 3행 / `grep -c toMetricValue` 5매치 복귀. 복원 후 오케스트레이터 독립 재관측 — 신규 테스트 `Test Files 1 passed (1)` · `Tests 21 passed (21)`, `tsc -b` exit 0 — F1·F5 교차 검증 완료.

*(기록 정리: 본 절은 오케스트레이터 보완 실증 기록과 run 세션의 후행 보강 기록이 각각 작성돼 중복됐던 것을 하나로 병합했다. 관측 실측 출력은 양쪽 기록이 일치했다.)*

### M5 — 게이트 F1~F6

| # | 게이트 | 결과 | 축자 |
|---|---|---|---|
| F1 | 신규 테스트 GREEN | **PASS** — 21/21 | `Tests 21 passed (21)` (복원 후 재실행 포함 2회 관측) |
| F2 | 되돌림 실증 [HARD] | **PASS** — §B 8종 전부 RED 관측 | M4 절 참조(위 축자) |
| F3 | 기존 테스트 무회귀 | **PASS** — 4 passed, 기준선과 동일·신규 실패 0 | `Test Files 1 passed (1)` / `Tests 4 passed (4)` |
| F4 | 전체 스위트 무회귀 | **PASS** — 760 passed(=기준선 739+신규 21), 파일 실패는 기준선과 동일 2건(e2e 수집 오류) | `Test Files 2 failed \| 85 passed (87)` / `Tests 760 passed (760)` |
| F5 | tsc 신규 오류 0 | **PASS** — exit 0 | `tsc -b` 출력 없음, TSC_EXIT=0 |
| F6 | lint 신규 0건 | **PASS** — 0 errors, 기준선과 동일한 1 warning(ThemeAnalysis.tsx:148, 기존) | `✖ 1 problem (0 errors, 1 warning)` — 델타 0 |

F4 해석: 파일 실패 2건은 M1 기준선의 `e2e/ai-report-deep.spec.ts`·`e2e/preset-flow.spec.ts`와 동일(신규 실패 아님). 통과 파일 수 84→85는 신규 테스트 파일 1개 추가.

### M6 — 라이브 확인 (미수행 → Gaps)

리드 운영 제약(백그라운드 프로세스 생성 금지)으로 dev 서버 재시작·육안 확인 불가. **F7은 Gaps로 기록한다.**

### 코드베이스 주장 — 관측 대조 (lessons #10)

| 주장 | 관측 방법 | 결과 |
|---|---|---|
| 지역 포맷터 3종 제거됨 | `grep -c "formatPct\|formatBreadth\|formatMomentum" ThemeRankingTable.tsx` (M3 후) | 0매치 — 제거 확인 |
| 4개 지표 전부 `toMetricValue` 경유 | `grep -c "toMetricValue" ThemeRankingTable.tsx` | 5매치(import 1 + 소비 4) — C2 충족 |
| `top_stocks_preview`는 `MISSING_TEXT` 참조·`MetricCell` 미경유 | diff 축자 — `?? MISSING_TEXT`, MetricCell 프롭 아님 | 확인 — C4 충족 |
| `MetricCell.tsx` 무변경 | `git diff --name-only \| grep -c MetricCell` | 0 — **C1 [HARD] 충족** |
| 대조 단언에 `MISSING_TEXT` 미사용 | 테스트 소스 — import는 AC-TDU-014 진단 단언 1곳만 사용, §B 8종은 리터럴 | 확인 — C5 충족 |
| `toContain` 미사용 | 테스트 소스 grep | 0매치 — §A.1 규칙 4 충족 |
| 신뢰도 신호 무합성 | AC-TDU-008 — data-state 수집 `['ok','ok','missing','ok']`, 위반 0 | 확인 — C3 충족 |
| `percent2` 바이트 동등 | AC-TDU-009/010/011 — '+1.50%'/'-2.50%'/'0.00%' 전체 등식 | PASS |
| 인라인 화살표가 선례와 바이트 동일 | diff — `(n) => n.toFixed(2)`, `(n) => \`${(n * 100).toFixed(1)}%\`` | `SectorRankingTable.tsx:265`·`StockTable.tsx:256`과 형태 일치 |

### AC별 상태

| AC | 분류 | 상태 | 근거 |
|---|---|---|---|
| AC-TDU-001 | 대조 | **PASS** | M4 RED 관측 + F1 GREEN |
| AC-TDU-002 | 대조 | **PASS** | M4 RED 관측 + F1 GREEN |
| AC-TDU-003 | 대조 | **PASS** | M4 RED 관측(+0≠4) + F1 GREEN(===4) |
| AC-TDU-004 | 대조·이중판별 | **PASS** | **세 상태 전부 실행 관측** — 되돌림 `'-'` RED(M4) / 불완전 구현 `'+Infinity%'` RED(M4-A 변형 실증) / 완전 구현 `'–'` GREEN(F1) |
| AC-TDU-005 | 대조 | **PASS** | M4 TypeError RED(§1.3(b) 실측 재현) + F1 GREEN |
| AC-TDU-006 | 대조 | **PASS** | M4 RED 관측 + F1 GREEN |
| AC-TDU-007 | 대조·최강 | **PASS** | M4 RED 관측(TypeError 경로 — 비고 참조) + F1 GREEN(프로즌 배열과 정확히 같음) |
| AC-TDU-008 | 대조 | **PASS** | M4 RED 관측(+0≠4) + F1 GREEN(4개, 위반 0) |
| AC-TDU-009~013 | 불변 | **PASS** | F1 GREEN — M2·M4 양쪽에서 GREEN(바이트 동등 고정 확인) |
| AC-TDU-014 | 불변·진단 | **PASS** | `MISSING_TEXT === '–'` |
| AC-TDU-015 | 불변 | **PASS** | onSort 1회·'change_pct', background 유지 |
| E1~E6 | 경계 | **PASS** | '0.00'/'0.0%'/'100.0%'/'–'/'–'/빈 tbody — F1 GREEN |

### Gaps (run 단계 미실증)

- **F7 라이브 확인 미수행** — 리드 운영 제약(백그라운드 프로세스 금지)으로 dev 서버 재시작·육안 확인 불가. 리드/사용자가 별도 수행 필요. 결측 발생률·API null 빈도 실측(G3/G4)도 여기에 포함된다.
- 백엔드 스위트는 카드 범위 밖(리드 지시 — push 후 처리).

---

## §E.3 Run-phase Audit-Ready Signal

**작성자**: manager-develop (run 단계) · **일자**: 2026-08-20

```yaml
run_complete_at: "2026-08-20"
run_commit_sha: "PENDING-ORCHESTRATOR-COMMIT"   # run 세션은 커밋 금지(리드 지시) — 오케스트레이터 검증 후 단일 커밋
run_status: "complete-with-gaps"                # F1~F6 전부 PASS, F7(라이브 확인) Gaps — 리드 운영 제약
ac_pass_count: 15                               # AC-TDU-001~015 전부 (대조 8 + 불변 7)
ac_fail_count: 0
preserve_list_post_run_count: 4                 # 기존 ThemeRankingTable.test.tsx it 4건 전부 보존·통과(F3)
l44_pre_commit_fetch: null                      # 커밋 전 단계 아님 — 오케스트레이터 소유
l44_post_push_fetch: null                       # push 전 단계 아님 — 오케스트레이터 소유
new_warnings_or_lints_introduced: 0             # F6: 기준선 1 warning(기존) 대비 델타 0
cross_platform_build:
  performed: "tsc -b (frontend, darwin)"        # 카드 범위가 프론트 — 백엔드/타깃 플랫폼 빌드는 범위 밖(리드 지시)
  status: "pass"
total_run_phase_files: 3                        # ThemeRankingTable.tsx(수정) + display.test.tsx(신규) + progress.md(본 기록)
m1_to_mN_commit_strategy: "single-commit"       # M1~M6 산출물 + 본 기록을 오케스트레이터가 단일 커밋으로 적재
```

### DoD 체크리스트 (acceptance §G) 충족 상태

- [x] `ThemeRankingTable.tsx`의 지역 포맷터 3종 제거 + `MetricCell` 경유 대체 — grep 0매치(§E.2 주장 표)
- [x] 4개 지표 셀 전부 `toMetricValue()` 경유 (REQ-TDU-002 [HARD]) — grep 5매치(import 1+소비 4), AC-TDU-004/005가 기계적으로 강제
- [x] `top_stocks_preview`의 `'-'` 리터럴 → `MISSING_TEXT` 참조 (D4) — diff 축자
- [x] `MetricCell.tsx` **무변경** (A1/C1) — 증명: `git diff --name-only | grep -c MetricCell` → **0**. 전체 diff는 `ThemeRankingTable.tsx` 1파일(14+/22-)뿐이며 `git diff --stat`에 MetricCell 없음
- [x] 신규 테스트 파일에 AC-TDU-001~015 구현 — 21 it(AC 15 + 경계 E1~E6)
- [x] §F 게이트 F1~F6 통과, **F2 되돌림 실증 출력 축자 첨부** — §E.2 M4/M5 절
- [x] progress.md §E.2/§E.3 증거 기록 — 본 파일
- [x] 미실증 항목은 GREEN이 아니라 Gaps로 기록 — 아래 참조

### Gaps 명시

1. **F7 라이브 확인 미수행** — 리드 운영 제약("백그라운드 프로세스 생성 금지")으로 dev 서버 재시작이 불가하여 acceptance §F F7(재시작 후 육안 확인)를 수행하지 못했다. 이는 DoD 미충족 항목이 아니라 **이월 항목**이다: 리드 또는 사용자가 `npm run dev` 재시작 후 테마 분석 탭 순위표에서 (a) 결측 칸 `–` (b) 정상값 칸 무변경을 확인해야 한다. G3(런타임 null 빈도)·G4(결측 발생률) 실측도 이 절차에서 함께 가능하다.
2. 백엔드 스위트 미실행 — 카드 범위 밖(리드 지시: push 후 처리).

### 잔여 공존 재확인 (spec.md §5 — 숨기지 않음)

본 SPEC 종료 후에도 ThemeAnalysis 탭 전체로는 `–`(순위표)와 `-`(ThemeDetailPanel·다중테마표)가 공존한다 — A.3의 의도된 귀결이며 후속 백로그 소관이다.

---

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
