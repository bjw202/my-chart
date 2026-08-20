---
id: SPEC-THEME-DISPLAY-UNIFY-001
title: ThemeRankingTable 표시 통일 — 지역 포맷터 3종을 MetricCell 단일 출처로 흡수
version: "0.2.1"
status: in-progress
created: 2026-08-20
updated: 2026-08-20
author: manager-spec
priority: P3
phase: "v0.5.1 target"
module: theme-analysis
lifecycle: spec-anchored
tags: "theme, frontend, display, metric-cell, formatter"
tier: M
depends_on: [SPEC-SECTOR-DISPLAY-UNIFY-001, SPEC-SECTOR-UX-001]
---

# SPEC-THEME-DISPLAY-UNIFY-001 — ThemeRankingTable 표시 통일

> 선행 SPEC `SPEC-SECTOR-DISPLAY-UNIFY-001`이 **범위 밖으로 명시하고 백로그로 넘긴** 항목(G-F2)의 인수 SPEC이다. 선행 SPEC이 SectorAnalysis에서 해소한 것과 같은 결함을 ThemeAnalysis에서 해소한다.

## HISTORY

| 버전 | 날짜 | 변경 |
|---|---|---|
| 0.2.1 | 2026-08-20 | plan-audit iteration 2(PASS 0.97, 무조건) 후속. **N1**: `plan.md` A.3의 `ThemeDetailPanel.tsx:17`(`return` 행)을 `:13-18`(`function` 선언)로 교정 — §1.1이 선언한 인용 규약과 어긋나 있었다. 같은 문단의 `:81`·`ThemeAnalysis.tsx:321`은 인라인 표현식이라 감쌀 선언이 없으므로 표현식 행 인용이 유일한 형태 — 미변경. 규약 일괄 점검 중 D2 표 3행의 `ThemeRankingTable.tsx:38`(`return` 행)도 같은 위반이라 `:36`(선언)으로 함께 교정 |
| 0.2.0 | 2026-08-20 | plan-audit(PASS-WITH-CONDITIONS 0.90) 대응. **F1**: D2의 근거 전제가 거짓으로 판명 — `grep "_ratio"`(필드명)가 아니라 `grep "\* 100"`(렌더 형태)로 재계측하니 동일 변환 소비자가 **3곳**. 결론(인라인 화살표)은 유지하고 근거를 `StockTable.tsx:256` 선례 일치로 교체. 승격 조건이 이미 발화했음을 인정하고 후속 백로그 기록(C1/A1 충돌로 지금은 미이행). **F2**: AC-TDU-008의 Given 2건 × 4셀 = 8이 프로즌 `=== 4`와 모순 → Given을 1건으로 고정(AC-TDU-003과 상수 공유). **F3**: F3 게이트의 "3건"이 실제 4건 → 절대 개수를 버리고 M1 기준선 델타 비교로 전환. F4 픽스처 주입 지시, F5 `Where`→`When`, F6 행번호·인용 불일치 주석, F7 E4 분기 귀속 |
| 0.1.0 | 2026-08-20 | 신설. G-F2 백로그(리드 카드 t8) 인수. 결정 4건 확정(D1~D4) + 지시에 없던 발산 축 2건(Infinity·런타임 null)을 계측으로 추가 발견 |

---

## §1 배경 — 인수 경위와 결함

### §1.1 인수 경위 (재논의 금지)

이 SPEC은 새로 발굴한 과제가 아니라 **선행 SPEC이 스스로 그어 둔 절단면의 반대편**이다. 근거는 선행 SPEC 본문에 축자로 남아 있다.

- `SPEC-SECTOR-DISPLAY-UNIFY-001/spec.md:107-108` — `### Out of Scope — ThemeAnalysis 동일 패턴 확산`. 당시에는 동일 패턴 보유 여부가 **미확인**이었고, "발견되면 별도 백로그로 기록만" 하기로 했다.
- `.../plan.md:73` — 갭 `G-F2`로 등록.
- `.../progress.md:269` — 실제로 **발견되었고**, `ThemeRankingTable.tsx:33/:38/:43`에 `toFixed` 계열 포맷터 3종이 있음을 기록. 범위 확장은 금지하고 후속 백로그로만 남김.

> **인용 행번호 불일치 안내**: 위 인용은 선행 SPEC 원문을 **축자 그대로** 옮긴 것이라 `:33/:38/:43`으로 적혀 있으나, §1.2 표의 **선언** 행은 `:30/:36/:41`이다. 둘 다 맞다 — 선행 SPEC은 각 함수의 **`return` 행**(`:33`/`:38`/`:43`)을 가리켰고, 본 SPEC은 **`function` 선언 행**을 가리킨다. 다음 독자가 같은 대조를 다시 하지 않도록 기록한다.
- `.../progress.md:463` — 리드 백로그 **t8**로 등록 완료.

즉 선행 SPEC은 확인 → 기록 → 위임까지 마쳤다. 본 SPEC은 그 위임의 수신자다.

### §1.2 결함 — 표시 단일 출처의 우회

`frontend/src/components/common/MetricCell.tsx`는 선행 SPEC들이 세운 **표시 단일 출처**다. 그 파일의 주석(`:4-10`)이 존재 이유를 명시한다 — 화면마다 결측 표기가 `–` / `-` / `NaN`으로 갈리는 것을 구조적으로 막기 위한 D6 결정이며, "5개 화면이 이 컴포넌트만 사용한다"고 적혀 있다.

`ThemeRankingTable.tsx`는 그 5개 화면에 들지 않으며, 지역 포맷터 3종으로 같은 일을 독자 수행한다.

| 위치 | 포맷터 | 본문 |
|---|---|---|
| `:30` | `formatPct(value: number)` | `!isFinite → '-'`, 그 외 `sign + toFixed(2) + '%'` |
| `:36` | `formatBreadth(value?: number)` | `null/!isFinite → '-'`, 그 외 `(value * 100).toFixed(1) + '%'` |
| `:41` | `formatMomentum(value?: number)` | `null/!isFinite → '-'`, 그 외 `toFixed(2)` |

소비 지점 5곳: `:91`·`:99`(`formatPct`), `:101`(`formatMomentum`), `:102`(`formatBreadth`), `:104`(`top_stocks_preview ?? '-'`).

결함의 실체는 "코드가 중복됐다"가 아니라 **결측 표기 문자가 갈린다**는 것이다. 정본은 `MISSING_TEXT = '–'`(U+2013 en dash), 이 화면은 `'-'`(U+002D ASCII hyphen)를 쓴다. 선행 SPEC이 SectorAnalysis에서 없앤 바로 그 발산이 이 화면에 남아 있다.

### §1.3 계측으로 새로 드러난 발산 축 2건 (인수 지시에 없던 항목)

카드가 지목한 축(결측 글리프·×100 단위) 외에, **동등하다고 가정된 경로에서 실제로 갈리는 지점 2건**을 본 SPEC 작성 중 계측했다. 둘 다 구현 방식에 직접 제약을 건다.

**(a) `Infinity` — 마이그레이션이 유발할 수 있는 회귀.** `formatPct(Infinity)`는 `!isFinite` 가드에 걸려 `'-'`를 낸다. 그러나 `MetricCell`의 `resolveState`(`:63`)는 결측 판정에 `Number.isNaN`만 쓰므로 `Infinity`를 **정상값으로 통과**시키고, `percent2(Infinity)`가 실행된다. 실측:

```
percent2(Infinity) = "+Infinity%"
Number.isNaN(Infinity)    = false   <- resolveState가 결측으로 보지 않음
Number.isFinite(Infinity) = false   <- toMetricValue는 null로 접음
```

따라서 값을 **날것으로** `MetricCell`에 넘기면 `-` → `+Infinity%`라는 회귀가 발생한다. `toMetricValue()`로 감싸야만 `–`가 된다. 이 때문에 §3 REQ-TDU-002가 `toMetricValue` 경유를 [HARD]로 못박는다.

형제 화면 `SectorRankingTable`은 날것을 넘기지만(`:208`~`:265`), 그 화면의 원래 코드에는 `isFinite` 가드가 없었으므로 보존할 거동도 없었다 — **선례를 그대로 복사하면 안 되는 지점**이다.

**(b) 런타임 `null` — 현재 코드의 잠재 크래시.** `isFinite(null)`은 `Number(null) === 0`이므로 **`true`**다. 즉 `formatPct`의 가드는 `null`을 걸러내지 못하고 `null.toFixed(2)`에 도달한다. 실측:

```
isFinite(null)     = true
percent2(null) THROWS: TypeError - Cannot read properties of null (reading 'toFixed')
```

`change_pct`·`change_pct_3d`는 `themes.ts:9-10`에서 **필수 `number`**로 선언돼 있다. 그러나 이는 **컴파일 타임 보증일 뿐**이며 API가 런타임에 `null`을 보내는 것을 막지 못한다 — 응답은 `response.data as ThemesSnapshotResponse`로 **단언 캐스팅**될 뿐 검증되지 않는다(`themes.ts:70`·`:77`). 따라서 "필수 타입이므로 결측 가드는 도달 불가"라는 주장은 **타입 층에 대한 주장이지 런타임에 대한 주장이 아니다**. 마이그레이션은 이 크래시 경로를 `–` 렌더로 바꾸는 부수 이득을 갖는다.

---

## §2 가정

| # | 가정 | 근거 / 미충족 시 |
|---|---|---|
| A1 | `MetricCell`의 기존 5상태 로직과 기존 포맷터 4종(`percent1`/`percent2`/`rating0`/`pct0`)은 **변경하지 않는다** | 형제 화면 5곳이 의존. 변경 시 본 SPEC 범위를 벗어남 |
| A2 | Theme API 응답에는 신뢰도 봉투(`low_confidence`/`warnings`/`reason`)가 **없다** | §4 D3에서 계측으로 확정 |
| A3 | ThemeAnalysis에는 ECharts 소비자가 없다 | `grep -rn "formatter" frontend/src/components/ThemeAnalysis/` → 0매치(관측) |

---

## §3 요구사항 (GEARS)

### REQ-TDU-001 — 결측 표기 단일화
The ThemeRankingTable component shall render every missing metric value using the canonical `MISSING_TEXT` constant exported by `MetricCell.tsx`, and shall not render the ASCII hyphen `'-'` as a missing indicator in any cell.

### REQ-TDU-002 — 비유한값 접기 [HARD]
When a metric value is passed to `MetricCell`, the ThemeRankingTable component shall pass it through `toMetricValue()` so that non-finite values (`Infinity`, `-Infinity`, `NaN`) fold to the missing state.

> 근거: §1.3(a). 이 절을 생략하면 `Infinity`가 `+Infinity%`로 새어 나가 현행 거동을 회귀시킨다.

### REQ-TDU-003 — 등락률 표시 불변
While a `change_pct` or `change_pct_3d` value is finite, the ThemeRankingTable component shall render it with a leading `+` when positive and exactly two decimal places followed by `%` — that is, byte-identical to the current `formatPct` output.

### REQ-TDU-004 — 상승비율 표시 불변
While a `breadth_ratio` value is finite, the ThemeRankingTable component shall render it multiplied by 100, with exactly one decimal place, followed by `%`, and **without a leading sign** — that is, byte-identical to the current `formatBreadth` output.

> 세 축(×100 / 소수 1자리 / 무부호)이 모두 구속된다. 정본 `percent1`은 `n > 0`에서 `+`를 붙이므로(`MetricCell.tsx:35`) 이 요구를 **위반**한다 — D2 참조.

### REQ-TDU-005 — 모멘텀점수 표시 불변
While a `momentum_score` value is finite, the ThemeRankingTable component shall render it with exactly two decimal places and no unit suffix — that is, byte-identical to the current `formatMomentum` output.

### REQ-TDU-006 — 대표종목 결측 표기
When `top_stocks_preview` is absent, the ThemeRankingTable component shall render the canonical `MISSING_TEXT` constant.

### REQ-TDU-007 — 신뢰도 상태 합성 금지 [HARD]
The ThemeRankingTable component shall not synthesize `low_confidence`, `warnings`, or `reason` fields for any theme metric.

> 근거: A2/D3. 백엔드가 보내지 않는 신호를 프론트가 만들어내면 화면이 근거 없는 ⚠/❗를 표시하게 된다.

### REQ-TDU-008 — 정렬·색상 거동 보존
The ThemeRankingTable component shall preserve its existing column sort behavior and the `getChangePctColor` background shading on the two change-percentage columns.

---

## §4 결정 (D1~D4)

### D1 — 결측 글리프 변경을 승인한다

**결정**: 승인. `-`(U+002D) → `–`(U+2013).

**이유**: 이것이 본 SPEC의 목적 그 자체다. 두 문자를 공존시키는 한 "표시 단일 출처"는 이름뿐이다. 선행 SPEC이 SectorAnalysis에서 동일한 변경을 이미 적용했으므로, 이 변경은 발산을 만드는 것이 아니라 **남은 발산을 제거**한다.

**폭발 반경 (사용자 가시 변경의 전부)**: `ThemeRankingTable` 한 파일, 한 행당 최대 5개 셀.

| 셀 | 결측 시 현행 | 결측 시 변경 후 | 결측 도달 가능성 |
|---|---|---|---|
| 등락률 | `-` | `–` | 낮음(필수 타입) — §1.3(b) 런타임 경로만 |
| 3일등락률 | `-` | `–` | 낮음(동일) |
| 모멘텀점수 | `-` | `–` | **높음**(`momentum_score?`) |
| 상승비율 | `-` | `–` | **높음**(`breadth_ratio?`) |
| 대표종목 | `-` | `–` | 중간(`top_stocks_preview?`) |

**정상값 셀은 한 글자도 바뀌지 않는다** — REQ-TDU-003/004/005가 바이트 동등을 요구한다. 즉 사용자가 관측할 변경은 오직 결측 칸의 하이픈 모양 하나다.

**남는 공존(§5 참조)**: `ThemeDetailPanel`·`ThemeAnalysis` 본문은 이번에 바뀌지 않으므로, 본 SPEC 종료 시점에도 ThemeAnalysis 탭 **전체**로 보면 두 글리프가 공존한다. 이 사실을 숨기지 않고 §5에 명시한다.

### D2 — `breadth_ratio` 단위 변환은 호출부 인라인 화살표로 귀속한다

**결정**: `MetricCell.tsx`에 새 정본 포맷터를 **추가하지 않는다**. 호출부에 인라인 화살표 `(n) => `${(n * 100).toFixed(1)}%`` 를 둔다.

**리드가 지목한 축(이 변환이 Theme 전용인가, 다른 화면에도 재발할 축인가)에 대한 계측**:

```
$ grep -rn "\* 100" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v test
```

이 변환은 **Theme 전용이 아니라 이미 세 곳에서 쓰이는 형태**다.

| # | 위치 | 형태 | 값 |
|---|---|---|---|
| 1 | `StockExplorer/StockTable.tsx:256` | `<MetricCell>`에 인라인 화살표 — 템플릿 리터럴 `(n * 100).toFixed(1)` + `%` (아래 코드블록 참조) | 0..1 비율(`stage.ts:42`, 상한 `WEIGHT_CAP=0.1`) |
| 2 | `AnalysisModal.tsx:26-28` `fmtPct` | `` `${(val * 100).toFixed(1)}%` `` — docstring이 *"Convert decimal ratio (e.g. 0.143)"* 로 명시 | 0..1 비율 |
| 3 | `ThemeAnalysis/ThemeRankingTable.tsx:36` `formatBreadth` | 본 SPEC의 대상 | 0..1 비율 |

**1번이 결정적이다.** 축자 인용:

```tsx
// frontend/src/components/StockExplorer/StockTable.tsx:256
<MetricCell value={c.weight_in_sector} format={(n) => `${(n * 100).toFixed(1)}%`} />
```

`<td>` 안에서 `MetricCell`에 **바이트 동등한 인라인 화살표**(같은 ×100, 같은 소수 1자리, 같은 무부호)를 넘기는, 본 SPEC이 제안하는 것과 **정확히 같은 구성**이 이미 출시돼 있다.

> **정정 기록 (v0.2.0)**: v0.1.0은 "0..1 비율을 표 셀에 백분율로 찍는 곳은 `breadth_ratio` 단 하나"라고 적었다. **이는 거짓이다.** 당시 프로브가 `grep -rn "_ratio"`였는데, 이는 **렌더 형태**를 묻는 질문에 **필드명 접미사**로 답한 것이다. `weight_in_sector`도 `fmtPct`의 지역 변수들도 그 부분 문자열을 갖지 않아 전부 누락됐다. 올바른 프로브는 위의 `grep -rn "\* 100"`이다. 결론(인라인 화살표)은 유지되지만 **근거는 뒤집혔다** — 아래가 정정된 근거다.

**정정된 근거**: 인라인 화살표는 단일 소비자를 위한 예외가 **아니라**, 세 소비자가 이미 공유하는 **관례에 대한 일치**다. 채택 근거가 "이번만 예외"에서 "출시된 선례와 동일"로 바뀌면서 오히려 강해진다. 부호·정밀도 회귀 회피 논거(아래 표)는 프로브 오류와 무관하게 그대로 유효하다.

**세 발산 축 전부에 대한 판정**:

| 축 | 현행 | `percent1` | `pct0` | 인라인 화살표 |
|---|---|---|---|---|
| ×100 단위 변환 | 있음 | **없음** | **없음** | 있음 |
| 소수 자릿수 | 1 | 1 ✔ | **0** | 1 ✔ |
| 부호 | 없음 | **`+` 붙음** | 없음 ✔ | 없음 ✔ |

**렌더 문자열 전후 대조** (`breadth_ratio = 0.625`):

| 구현 | 렌더 결과 | 판정 |
|---|---|---|
| 현행 `formatBreadth` | `62.5%` | 기준 |
| 인라인 화살표 | `62.5%` | **동등** |
| `percent1` (×100 별도 적용 시) | `+62.5%` | 부호 회귀 |
| `pct0` (×100 별도 적용 시) | `63%` | 정밀도 회귀 |

`breadth_ratio`는 0..1 비율이므로 항상 0 이상이고, 따라서 `percent1`의 `+`는 **결측 아닌 모든 행에서** 나타난다. 산발적 회귀가 아니라 전면 회귀다.

**추가 근거(선례 일치)**: `SectorRankingTable.tsx:265`가 `composite_score`에 대해 정확히 같은 형태(`format={(n) => n.toFixed(2)}`)를 쓴다. 인라인 화살표를 `format`으로 넘기는 관례 자체가 이미 정착돼 있다.

**승격 조건은 이미 충족됐다 — 그런데도 지금은 승격하지 않는다.**

v0.1.0은 "두 번째 소비자가 생기면 승격"을 미래 조건으로 적었다. 위 계측이 보여주듯 **두 번째·세 번째 소비자는 이미 존재한다.** 따라서 정직한 기술은 "조건이 아직 오지 않았다"가 아니라 **"조건은 발화했으나 지금 이행하지 않는다"** 이며, 그 이유는 다음과 같다.

- 정본 `ratioPct1`을 추가하려면 `MetricCell.tsx`를 수정해야 하는데, 이는 **C1/A1(정본 무변경)과 정면 충돌**한다. 그 제약은 형제 화면 5곳의 회귀 위험 때문에 걸어 둔 것이다.
- 세 소비자를 한 정본으로 모으는 작업은 `StockExplorer`·`AnalysisModal`까지 건드리므로 **본 SPEC의 범위(단일 파일)를 벗어난다.**
- 즉 승격은 본 SPEC이 **할 수 없어서 미루는 것이지, 불필요해서 미루는 것이 아니다.**

**후속 백로그 항목 (기록)**: `MetricCell.tsx`에 `ratioPct1`을 `export function`으로 추가하고 세 소비자(`StockTable.tsx:256`, `AnalysisModal.tsx:26-28`, 본 SPEC이 남길 `ThemeRankingTable`의 인라인 화살표)를 이관한다. **반드시 `export function` 선언**이어야 한다 — 화살표 `const`는 `react-refresh/only-export-components`가 잡는다(`MetricCell.tsx:44-45`에 실측으로 기록됨). 이 항목은 `MetricCell` 수정 권한을 갖는 SPEC이 소유한다.

### D3 — 5상태 채택 범위: 4개 필드 모두 2상태만 도달 가능

**계측** (리드 지시대로 백엔드까지 확인):

```
$ grep -rln "low_confidence" --include="*.py" .
my_chart/analysis/aggregate_types.py
my_chart/analysis/sector_metrics.py
tests/test_response_contract.py
tests/test_sector_aggregation.py
backend/schemas/envelope.py
```

→ **sector 계열 전용**. Theme 파이프라인에는 없다. 추가 확인:

```
$ grep -n "low_confidence\|envelope" backend/services/naver_theme_v2/parser.py   → 0매치
$ grep -rn "envelope" backend/routers/ | grep -i theme                          → 0매치
$ grep -n "low_confidence\|warnings" frontend/src/api/themes.ts                 → 0매치
```

Theme 응답은 봉투를 거치지 않고 원시 숫자를 보낸다.

**필드별 판정** (블랭킷 아님):

| 필드 | `missing` | `ok` | `insufficient` | `low-confidence` | `warning` |
|---|---|---|---|---|---|
| `change_pct` | 도달(런타임 null/비유한) | 도달 | **불가** | **불가** | **불가** |
| `change_pct_3d` | 도달(동일) | 도달 | **불가** | **불가** | **불가** |
| `momentum_score` | 도달(옵셔널) | 도달 | **불가** | **불가** | **불가** |
| `breadth_ratio` | 도달(옵셔널) | 도달 | **불가** | **불가** | **불가** |

`insufficient`는 `MetricObject.reason === 'insufficient'`를 요구하고(`MetricCell.tsx:64`), `low-confidence`/`warning`은 각각 `low_confidence`/`warnings`를 요구한다(`:65-66`). Theme은 원시 숫자만 보내므로 `normalize`가 `{ value }`만 만들고 세 상태는 **구조적으로 도달 불가**하다.

**결정**: 4개 필드 모두 `missing` + `ok` 2상태만 채택한다. 나머지 3상태는 **잉여이되 비용이 0**이다 — 별도로 추가하는 코드가 아니라 이미 존재하는 `metricDisplay` 분기이며, 입력이 없으면 실행되지 않는다. 따라서 제거하지도, 사용하지도 않고 휴면 상태로 둔다. 신호를 **합성하는 것은 금지**한다(REQ-TDU-007) — 백엔드가 보내지 않는 ⚠/❗를 프론트가 만들어내면 사용자가 근거 없는 경고를 보게 된다.

### D4 — 네 번째 지점(`top_stocks_preview`)을 포함한다

**결정**: 포함. 단 `MetricCell`을 **경유하지 않는다**. `'-'` 리터럴을 `MISSING_TEXT` 상수 참조로 교체한다.

**포함 이유**: 3개 지표만 고치면 같은 행에 `–`와 `-`가 나란히 남는다. `momentum_score`와 `breadth_ratio`가 결측일 확률이 높은(옵셔널) 필드이므로, 이 공존은 이론적 가능성이 아니라 **흔한 화면 상태**다. 그러면 D1의 목적이 그 행에서 무효가 된다.

**`MetricCell`을 쓰지 않는 이유**: `MetricValue = number | null | undefined | MetricObject`이고 `format?: (n: number) => string`이다(`MetricCell.tsx:29`·`:114`). `top_stocks_preview`는 `string`이므로 넘기면 타입 오류이며, 우회하더라도 `metricDisplay`가 `String(obj.value)`로 처리해 숫자 셀 의미론을 문자열에 잘못 적용하게 된다. 지표 컴포넌트를 비지표 필드에 쓰는 것은 D1이 세우려는 경계 자체를 흐린다.

**따라서**: 통일하는 대상은 **글리프**이지 컴포넌트가 아니다. `MISSING_TEXT` 상수만 공유하면 목적은 달성되고 타입 경계는 보존된다.

---

## §5 범위 밖 (Out of Scope)

### Out of Scope — 인접 동일 패턴 3곳

카드가 지정한 범위는 `ThemeRankingTable.tsx` 한 파일이다. 작성 중 같은 디렉터리에서 동일 패턴 3곳을 관측했으나 **본 SPEC 범위를 넓히지 않는다**. 침묵으로 넘기지 않고 사유와 함께 기록한다 — 선행 SPEC이 G-F2를 다룬 방식과 동일한 규율이다.

- `ThemeDetailPanel.tsx:13-18` `formatChangePct` — 문자열이 아니라 **색상이 입혀진 JSX 엘리먼트**를 반환한다(`color: var(--positive)/var(--negative)`). `MetricCell`에는 등락 방향 색상 채널이 없다(`className` 통과만 있음). 이관하려면 "색상을 어디가 소유하는가"라는 별도 결정이 필요하며, 그 결정은 `MetricCell`의 기존 로직을 건드릴 소지가 있다 — A1 위반.
- `ThemeDetailPanel.tsx:81` `isFinite(price) ? price.toLocaleString() : '-'` — 천단위 구분 정수 포맷은 정본에 대응 포맷터가 **없다**. 추가하려면 단일 소비자를 위한 정본 확장이 되어 D2의 판단과 모순된다.
- `ThemeAnalysis.tsx:321` — 다중테마 종목 표의 인라인 등락률. 위 첫 항목과 같은 색상 결합 문제.

**귀결(숨기지 않음)**: 본 SPEC 종료 후에도 ThemeAnalysis 탭 전체로 보면 `–`(순위표)와 `-`(상세 패널·다중테마표)가 공존한다. 이는 카드가 그은 범위를 존중한 결과이며, 후속 백로그로 넘긴다. 이 SPEC이 스스로 만든 발산이 아니라 **줄이고 남긴 잔량**이다.

### Out of Scope — SectorAnalysis 및 MetricCell 기존 로직

- SectorAnalysis의 기존 `MetricCell` 채택 지점 일체.
- `MetricCell`의 5상태 판정 로직과 기존 포맷터 4종(`percent1`/`percent2`/`rating0`/`pct0`)의 거동.
- `MetricTextParity.m7.test.tsx`의 기존 단언(형제 화면 대상).

### Out of Scope — 표↔툴팁 문자열 동등 검증 (명시적 N/A)

선행 SPEC의 `MetricTextParity.m7.test.tsx`는 **표 셀 DOM ↔ ECharts 툴팁 문자열**의 동등을 실증한다. 그 검사의 전제는 "같은 값을 두 소비자가 각자 렌더한다"는 것이다.

ThemeAnalysis에는 **차트가 없다** — `grep -rn "formatter" frontend/src/components/ThemeAnalysis/` 0매치(관측). 두 번째 소비자가 존재하지 않으므로 전제가 성립하지 않는다.

Theme용 대응 검사를 억지로 만들면 `metricText(v, f)`와 `MetricCell(v, f)`를 비교하게 되는데, 후자는 내부에서 전자와 같은 함수를 호출한다(`MetricCell.tsx:120` → `metricDisplay`; `:100` → 동일 함수). 즉 **같은 헬퍼를 양변에서 호출하는 항진명제**이며, lessons #9의 항진명제 유형 2(공유 헬퍼 자기 호출)와 정확히 같은 형태다. 어떤 구현에서도 통과하므로 검사가 아니다.

**따라서 N/A로 판정하고 그 사유를 위와 같이 기록한다.** 검사를 만들지 않는 것이 이 경우의 올바른 답이다.

### Out of Scope — 구현

본 SPEC은 plan 단계 산출물이다. 코드 변경은 run 단계가 수행한다.
