# SPEC-THEME-DISPLAY-UNIFY-001 — 구현 계획

> 배치 원칙: **되돌리기 어려운 결정을 위로, 기계적 작업을 아래로.** §A~§C가 사람의 판단이 필요한 부분이고, §F 마일스톤은 그 판단이 확정된 뒤의 실행 순서다. 검토 시간을 §A~§C에 쓰라.

---

## §A 사용자 가시 결정 — 가장 먼저 뒤집힐 수 있는 항목

### A.1 결측 글리프 `-` → `–` (D1)

이 SPEC에서 **사용자가 실제로 보게 되는 변경은 이것 하나뿐이다.** 정상값 칸은 한 글자도 바뀌지 않는다(REQ-TDU-003/004/005가 바이트 동등 요구).

되돌리기 난이도는 낮다(글리프 한 종류) 그러나 **판단 자체는 되돌리면 SPEC의 목적이 사라진다** — 통일하지 않기로 하는 것과 같다. 따라서 진행 전에 확인할 것은 "이 변경을 승인하는가"가 아니라 다음 한 가지다:

> 순위표(`–`)와 상세 패널(`-`)에 서로 다른 글리프가 남는 중간 상태를 감수할 것인가?

감수하지 않겠다면 §A.3의 인접 3곳을 범위에 넣어야 하며, 그 경우 본 SPEC은 Tier M을 넘어간다. 카드가 그은 범위(`ThemeRankingTable.tsx` 단일 파일)를 따르면 중간 상태가 남는다 — **이 사실을 알고 진행한다.**

### A.2 `breadth_ratio` 귀속 (D2) — 인라인 화살표

같은 ×100·1자리·무부호 변환이 이미 **세 곳**에서 쓰인다 — `StockTable.tsx:256`(`<td>` 안 `MetricCell`에 **바이트 동등한 인라인 화살표**), `AnalysisModal.tsx:26-28` `fmtPct`, 그리고 본 SPEC의 대상. 따라서 인라인 화살표는 예외가 아니라 **출시된 선례와의 일치**다. `SectorRankingTable.tsx:265`도 `format`에 인라인 화살표를 넘기는 같은 관례를 쓴다.

> v0.1.0은 이 자리에서 "`breadth_ratio` 단 하나"라고 적었다. 거짓이었고 v0.2.0에서 철회했다 — 원인과 교훈은 progress.md § 철회된 주장 참조.

**뒤집힐 조건**: 정본 `ratioPct1` 승격이 **더 나은 선택이며, 조건은 이미 충족돼 있다.** 본 SPEC이 하지 않는 이유는 불필요해서가 아니라 C1/A1(`MetricCell` 무변경)과 충돌하고 세 소비자 이관이 단일 파일 범위를 벗어나기 때문이다(spec.md D2에 후속 백로그로 기록). `MetricCell` 수정 권한을 갖는 SPEC이 이 항목을 가져가면 그때 승격한다 — `export function` 선언 필수(화살표 `const`는 `react-refresh/only-export-components` 위반, `MetricCell.tsx:44-45` 실측).

### A.3 인접 3곳 제외 (범위 결정)

`ThemeDetailPanel.tsx:13-18`·`:81`, `ThemeAnalysis.tsx:321`은 제외한다(spec.md §5에 사유 기록). 핵심 사유는 예산이 아니라 **결합**이다 — 앞의 둘은 등락 방향 **색상**이 포맷터에 얽혀 있고, `MetricCell`에는 색상 채널이 없다. 이관하려면 "색상을 어디가 소유하는가"를 결정해야 하고, 그 결정은 `MetricCell` 자체를 건드릴 소지가 있어 A1(정본 무변경)과 충돌한다.

**이 결정이 뒤집히면** 본 SPEC이 아니라 `MetricCell`의 색상 채널을 다루는 별도 SPEC이 필요하다 — 범위 확장이 아니라 선행 SPEC 신설이다.

---

## §B 알려진 갭

| # | 갭 | 처리 |
|---|---|---|
| G1 | 본 SPEC 종료 후에도 ThemeAnalysis 탭 전체에는 `–`/`-`가 공존 | A.3의 의도된 귀결. 후속 백로그로 기록(spec.md §5) |
| G2 | 기존 테스트가 표시 문자열을 단언하지 않는다는 관측은 **작성 시점 grep** 결과 | run 단계가 F3에서 실행으로 재확인. 메모를 신뢰하지 않음 |
| G3 | Theme API의 런타임 `null` 유입 빈도는 미측정 | AC-TDU-005는 가능성에 대한 내성 확보이지 빈도 주장이 아님 |
| G4 | `momentum_score`·`breadth_ratio`의 실제 결측 발생률 미측정 | D1 폭발 반경 표의 "높음/낮음"은 **타입 옵셔널 여부에 근거한 추정**이며 실측이 아님 |

G4는 명시적으로 남긴다 — 폭발 반경 표를 실측으로 오해하지 않게 하기 위함이다.

---

## §C 제약

| # | 제약 | 근거 |
|---|---|---|
| C1 | `MetricCell.tsx` 무변경 [HARD] | A1. 형제 화면 5곳 의존 |
| C2 | 4개 지표 전부 `toMetricValue()` 경유 [HARD] | REQ-TDU-002. 누락 시 `Infinity` → `+Infinity%` 회귀(spec.md §1.3a 실측) |
| C3 | 신뢰도 신호 합성 금지 [HARD] | REQ-TDU-007 |
| C4 | `top_stocks_preview`는 `MetricCell` 경유 금지 | D4. `MetricValue`에 `string` 없음 |
| C5 | 대조 단언에서 `MISSING_TEXT` import 비교 금지 | acceptance.md §A.1 규칙 3 |

---

## §D 기술 접근

### D.1 변경 형태 (예상 diff)

```
- import type { ThemeItem } from '../../api/themes'
+ import type { ThemeItem } from '../../api/themes'
+ import { MetricCell, percent2, toMetricValue, MISSING_TEXT } from '../common/MetricCell'

- function formatPct(...)      // :30-34  제거
- function formatBreadth(...)  // :36-39  제거
- function formatMomentum(...) // :41-44  제거

  <td ...><MetricCell value={toMetricValue(theme.change_pct)}    format={percent2} /></td>
  <td ...><MetricCell value={toMetricValue(theme.change_pct_3d)} format={percent2} /></td>
  <td ...><MetricCell value={toMetricValue(theme.momentum_score)} format={(n) => n.toFixed(2)} /></td>
  <td ...><MetricCell value={toMetricValue(theme.breadth_ratio)}  format={(n) => `${(n * 100).toFixed(1)}%`} /></td>
  <td ...>{theme.top_stocks_preview ?? MISSING_TEXT}</td>
```

`getChangePctColor(theme.change_pct)`는 **`<td>` 쪽에 그대로 둔다** — `MetricCell`은 `<span>`을 렌더하므로 배경은 부모 `<td>`가 계속 소유한다(REQ-TDU-008).

### D.2 `percent2` 재사용 근거

`formatPct`의 유한값 경로 `` `${sign}${value.toFixed(2)}%` `` 와 `percent2`(`MetricCell.tsx:38-40`)의 `` `${n > 0 ? '+' : ''}${n.toFixed(2)}%` `` 는 **동일 식**이다. 결측 처리만 `MetricCell`로 이관되고 유한값 표시는 바뀌지 않는다 — AC-TDU-009/010/011이 이를 고정한다.

### D.3 `momentum_score` 인라인 화살표

정본에 무단위 2자리 포맷터가 없다. `SectorRankingTable.tsx:265`의 `composite_score`가 정확히 같은 형태를 쓰므로 선례 일치.

---

## §E 위험

| # | 위험 | 완화 |
|---|---|---|
| R1 | `toMetricValue` 누락 → `Infinity`가 `+Infinity%`로 노출 | AC-TDU-004가 기계적으로 차단(이중 판별) |
| R2 | `percent1` 오채택 → 상승비율에 `+` 전면 부착 | AC-TDU-012가 전체 등식으로 차단 |
| R3 | 5개 지점 중 일부만 이행 | AC-TDU-007(잔여 집합 동등) + AC-TDU-003(`=== 4`)이 차단 |
| R4 | 되돌림 실증 없이 GREEN 보고 (lessons #9 재발) | F2를 [HARD] 게이트로 두고 축자 출력 요구 |
| R5 | `MetricCell` 무단 수정 | `git diff --stat`으로 DoD 확인 |
| R6 | Fast Refresh로 라이브 확인이 미반영으로 보임 | F7에 dev 서버 재시작 명시 |

---

## §F 마일스톤 (기계적 실행 — 위 결정 확정 후)

우선순위 순. 시간 추정 없음.

### M1 — 기준선 고정 (Priority High)
변경 **전에** 실행해 축자 저장: 프론트 테스트 전체 결과, `tsc` 결과, 변경 대상 디렉터리 lint 결과. F4·F5·F6의 델타 비교 기준이 된다. 이 단계를 건너뛰면 이후 게이트가 절대 개수 단언으로 퇴화한다.

### M2 — 테스트 선행 작성 (Priority High)
`ThemeRankingTable.display.test.tsx` 신설, AC-TDU-001~015 구현. **구현 전에 작성한다** — 이 시점에 §B 대조 단언은 전부 RED여야 하며, 그 RED가 F2 실증의 절반이다(나머지 절반은 M4의 되돌림 재현).

### M3 — 구현 (Priority High)
§D.1 형태로 `ThemeRankingTable.tsx` 변경. 지역 포맷터 3종 제거, 5개 소비 지점 교체. `MetricCell.tsx`는 건드리지 않는다(C1).

### M4 — 되돌림 실증 (Priority High) [HARD]
`ThemeRankingTable.tsx`를 M3 이전 상태로 되돌린 사본에서 테스트 실행 → §B 8종 RED 축자 캡처 → 트리 복원 → `git status --short`로 복원 증명. 결과를 progress.md §E.2에 기록.

**실증하지 못한 항목은 GREEN이 아니라 Gaps로 적는다.** 이것이 이 SPEC의 중심 게이트다.

### M5 — 게이트 통과 (Priority Medium)
F1·F3·F4·F5·F6 실행, M1 기준선과 델타 비교.

### M6 — 라이브 확인 (Priority Medium)
dev 서버 **재시작 후** 테마 분석 탭에서 결측 칸 `–` 및 정상값 칸 무변경 육안 확인(F7).

---

## §G 안티패턴 (하지 말 것)

- `MetricCell.tsx`에 `breadth` 전용 포맷터를 "겸사겸사" 추가 — D2 판정 위반이자 C1 위반 위험.
- `top_stocks_preview`를 `MetricCell`에 통과시키기 위한 타입 우회 — D4 판정 위반.
- 대조 단언을 `toContain`으로 작성 — `'62.5%' ⊂ '+62.5%'` 함정(acceptance.md §A.1 규칙 4).
- AC-TDU-008을 동반 개수 단언 없이 GREEN 기록 — 공허 참(#9 유형 3).
- §C 불변 단언을 "대조 단언"으로 보고 — acceptance.md §A.2 위반.
- 인접 3곳을 "김에 같이" 수정 — 범위 확장. spec.md §5가 명시적으로 제외.

---

## §H 교차 참조

- `.moai/specs/SPEC-SECTOR-DISPLAY-UNIFY-001/` — 선행 SPEC. G-F2가 본 SPEC의 출처
- `frontend/src/components/common/MetricCell.tsx` — 정본(무변경 대상)
- `frontend/src/components/SectorAnalysis/SectorRankingTable.tsx:265` — 인라인 화살표 선례
- `frontend/src/components/common/__tests__/MetricTextParity.m7.test.tsx:122` — 앵커 일치 선례
- `lessons.md #9` — 대조 단언 판정 기준(본 SPEC AC 설계의 구속 근거)
- `lessons.md #1·#2` — 프론트 표시/발견성 결정은 라이브 확인 후 잠근다(F7 근거)
