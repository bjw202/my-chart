# SPEC-SECTOR-DISPLAY-UNIFY-001 — 구현 계획

> 원본: `.moai/plans/rs-purring-key.md` M6·M7. 형제 백엔드 SPEC `SPEC-SECTOR-METRIC-UNIFY-001`에서 분리.

## §A 핵심 결정

| # | 결정 | 대안 | 왜 이것인가 |
|---|---|---|---|
| DEC-F1 | M6을 백엔드 머지와 **무관하게 선행** | 백엔드 완료 후 일괄 | 원본 계획 M6 헤더가 "백엔드 독립, 먼저 배포 가능"이라고 명시. 전부 기존 응답 필드의 표시 방식 변경이라 값 의존이 없다 |
| DEC-F2 | M7만 형제 SPEC M5 완료에 의존 | 전체를 의존으로 취급 | M7은 봉투 `data[]`를 읽는다. `depends_on`을 건 이유는 M7·X축 라벨이지 M6이 아니다 |
| DEC-F3 | 임계값을 `frontend/src/utils/rsMetrics.ts`에 신설 | 컴포넌트 로컬 상수 | `utils/`는 순수 모듈 + `__tests__/` 관례(`sort.ts`/`hangul.ts` 선례). 교차 언어 등식 테스트를 붙이려면 순수 모듈이어야 한다 |
| DEC-F4 | 세 수익률 열 전부 유지, 선택 기간에 `(순위 기준)` 표시만 추가 | 선택 기간 열만 표시 | 기간 간 비교가 이 표의 존재 이유 |
| DEC-F5 | `types/market.ts`에 `data?: SectorAggregateItem[]` **최소 형태**만 추가 | 봉투 전체 타입 이식 | 필요한 필드만 읽는다. 봉투 스키마 전체를 프론트로 복제하면 백엔드 변경마다 드리프트한다 |
| DEC-F6 | 사다리 재산출은 **형제 SPEC에 잔류** | 프론트 파일이니 여기로 | M4가 거래대금 단위를 바꾸는 당사자. 여기로 미루면 백엔드만 머지된 구간에서 버블이 뭉친 채 배포된다 |

---

## §B 마일스톤 순서의 근거 — 의존성이지 되돌림 난이도가 아니다 [HARD]

형제 SPEC §B가 M0 선행 근거를 명시한 것과 **같은 수준으로** 여기서도 명시한다.

- **M6 먼저**: 백엔드 의존이 **없다**. 값이 아니라 표시 방식만 바꾸므로 형제 SPEC이 머지되기 전에도 완결·배포 가능하다. 뒤로 미룰 이유가 없고, 미루면 독립 배포 가능한 개선이 불필요하게 지연된다.
- **M7 나중**: 봉투 `data[]`를 읽으므로 형제 SPEC **M5(봉투 정상화) 완료에 의존**한다. `data[]`가 비어 있는 동안 M7을 랜딩하면 폴백 경로만 계속 타서 실동작 여부를 검증할 수 없다.
- **버블 X축 라벨 변경도 M5 의존**: 초과수익률 벤치마크가 정의 B로 바뀐 뒤라야 라벨이 참이 된다. M6 묶음에 넣지 말고 M7과 함께 처리한다.

즉 순서 근거는 "쉬운 것 먼저"가 아니라 **의존 그래프**다. 순서를 바꾸면 M7이 검증 불가 상태로 랜딩된다.

---

## §C 마일스톤

### M6 — 프론트 표시 통일 (백엔드 독립, 먼저 배포 가능) · Priority Medium

- **반올림 규약**: `MetricCell.tsx`(`@MX:ANCHOR metricDisplay` 단일 출처)에 `rating0`/`pct0` 추가 후 호출부 전환. 호출부 개수는 **실행 스캔으로 확정**한다(원본 계획의 "8개"는 미검증 수치 — §E G-F3). `MetricCard`(`SectorDetailPanel.tsx:18-30`)를 `MetricValue` 수용으로 바꿔 `null%` 버그 해소
- **임계값 상수화**: `frontend/src/utils/rsMetrics.ts` 신설. `RS_TOP_THRESHOLD=80` / `RS_STRONG_THRESHOLD=70` / `RS_S2_STRONG_THRESHOLD=60` / `RS_UNIVERSE_MIDPOINT=50`. 라벨 없던 두 술어(`StockTable.tsx:59`, `ChartCell.tsx:299`)에 상수 유래 `title` 추가
- **라벨 정확성**: `'RS Top %'` → `'RS 80+ 비중'` / `'RS 중앙'` → `'RS 50 (유니버스 백분위 중앙)'` / `ChartCell` 배지 `RS등급`으로 RS Line 버튼과 구분 / RRG 패널에 "순위표 RS Rating과 다른 지표" 캡션
  - 버블 Y축 `'RS Rating 평균 (0-100)'`은 값 의존이 없으므로 M6에서 함께 처리. **X축 라벨만 M7로 미룬다**(벤치마크 정의 전환 의존)
- **색 램프 분리**: `SectorRankingTable.tsx:54-64`의 파란 램프를 등급과 비중이 공유 중 → 등급용 채널 분리

### M7 — Table 기간 토글 실동작 (형제 SPEC M5 의존, 가장 넓은 영향) · Priority Medium

- `api/market.ts`에 `period` 인자 추가 → `MarketContext`에 `periodRef`(기존 `marketRef` 관용 확장) → `types/market.ts`에 `data?: SectorAggregateItem[]` 최소 형태 추가 → `SectorAnalysis.tsx:93-110`에서 이름으로 조인해 `rank`/`rank_change` 덮어쓰기
- `data[]` 부재 시 composite로 폴백하고 **캡션이 그 사실을 말하게 한다**(`순위 기준: 종합점수(3기간 가중)`)
- `SectorRankingTable`에 `activePeriod` prop 추가 — 선택 기간 열 헤더에 `(순위 기준)` 표시. 세 수익률 열은 전부 유지
- `SectorAnalysis.tsx:218`의 원시 상태값(`기간 1m`) 출력을 표시 라벨(`:30`)로 교체
- 버블 X축 라벨을 정의 B(상한 시총가중 유니버스 벤치마크) 서술로 정렬

---

## §D 의도적으로 갱신해야 하는 기존 테스트

| 파일:라인 | 갱신 사유 |
|---|---|
| `SectorAnalysis.market-delivery.test.tsx:56,64,81` | `api/market.ts` 인자 1개 → 2개 (M7). **실측 확인** — `toHaveBeenLastCalledWith('all'/'kospi'/'kosdaq')` 세 곳. 원본 계획의 `:60,68,79`는 미검증 수치였다. 같은 파일 `:55`/`:77`의 인자 없는 `toHaveBeenCalled()`는 arity 변경 영향 없음 |
| `SectorRankingTable.test.tsx:70` | 라벨 문자열 변경 (M6) |
| `SectorDetailPanel.test.tsx:65-67` | 라벨 문자열 변경 (M6) |

이 목록 밖의 기존 테스트가 깨지면 **의도치 않은 회귀**로 취급한다.

---

## §E 리스크 / 미검증 갭 — AC가 이것들이 성립한다고 가정하지 않는다

| # | 갭 | 처분 |
|---|---|---|
| G-F1 | **교차 언어 상수 추출 기법 미확정.** **(D6 기록)** 이 테스트는 `frontend/` → 레포 루트 경계를 넘으므로 **vite import로는 해결되지 않는다**(vite 모듈 그래프 밖이며 `.py`는 로더 대상도 아니다). Node `fs`로 읽되 경로는 CWD가 아니라 **`import.meta.url` 기준으로 해석**해야 한다 — vitest 실행 CWD 가정은 깨지기 쉽다. 백엔드 심볼은 **비공개이며 float**(`_RS_TOP_THRESHOLD = 80.0`, `my_chart/analysis/sector_metrics.py:58`)이고 TS 상수는 `80`이 된다. import가 불가하므로 vitest가 상대경로로 `.py`를 읽어 `parseFloat`로 추출한 뒤 **수치** 등식을 단언하는 형태가 된다(문자열 등식이 아니다 — `80.0` ≠ `80`) | run-phase 착수 시 위 형태로 확정. 손으로 옮겨 적은 상수 비교로 대체하지 않는다(lessons #9) |
| G-F2 | `ThemeAnalysis/ThemeRankingTable.tsx`가 동일 표시 패턴을 갖는지 미확인 | 범위 밖(spec.md §4). 발견되면 백로그 기록만 |
| G-F3 | 원본 계획의 "8개 호출부"는 **미검증 수치**다 | M6 착수 시 실행 스캔으로 개수를 확정하고 관측 출력을 AC-SDU-001에 리터럴로 고정 |
| G-F4 | 형제 SPEC M5 미머지 상태에서 M7 테스트를 돌리면 폴백 경로만 탄다 | M7 착수 전 형제 SPEC M5 머지 여부를 확인. 미머지면 M6까지만 랜딩 |
| **G-F5** | **REQ-SDU-001 구현이 lint 기준선을 +2 늘린다 — 기계적으로 확실하고 크기가 정확하다.** 소스 대조: 기준선의 `react-refresh/only-export-components` **5건**(`MetricCell.tsx:34, 38, 70, 86, 93`)이 이 파일의 `export function` 선언 5개(`percent1`, `percent2`, `metricDisplay`, `metricText`, `toMetricValue`)와 **정확히 일치**하고, 반면 exported `const`/`type`/`interface` **7개**(`:12, 13, 19, 21, 29, 63, 99`)는 **한 건도 내지 않는다**. REQ-SDU-001은 이 파일에 `rating0`/`pct0` 함수 2개를 더 export하라고 하므로 **+2가 확정적**이며, **G-F5가 미해결인 동안 AC-SDU-012/013의 "신규 0건"은 구성상 통과 불가**다 | **[HARD] 소진 경계 = M6 첫 커밋 이전.** (b)안은 M6 첫 커밋의 내용 자체를 바꾸므로 코드가 착지한 뒤의 결정은 결정이 아니라 사후 합리화다. 후보는 § G-F5 결정 후보 참조. **(a)안이 추정 정답**이며, 확정 lint 1회를 M6 킥오프에 둔다 |

---

## §F 자기 검증 명령

```bash
cd frontend && npm run typecheck   # = tsc -b. 루트 tsconfig가 files:[] solution-style이라 tsc --noEmit은 0파일 검사(공허 관측)
# [HARD] eslint 범위는 M6/M7이 실제로 건드리는 디렉터리를 전부 포함한다 (아래 범위 근거)
cd frontend && npx eslint src/components/SectorAnalysis src/components/common src/components/ChartGrid src/components/StockExplorer src/utils --max-warnings=0 > /tmp/lint.out 2>&1; echo $?   # 파이프 금지(종료코드 은폐)
cd frontend && npx vitest run --exclude "e2e/**"
```

**범위 근거**: 원본 계획의 `src/components/SectorAnalysis src/utils`는 M6이 수정하는 디렉터리 3곳을 보지 못한다 — `common/MetricCell.tsx`(REQ-SDU-001의 `rating0`/`pct0`), `ChartGrid/ChartCell.tsx`(REQ-SDU-003 `:299` title, REQ-SDU-004 `:326` 배지), `StockExplorer/StockTable.tsx`(REQ-SDU-003 `:59` title). `tsc`·`vitest`가 덮긴 하지만, "§D 밖 무회귀"를 주장하는 명령이 정작 변경 파일 3개를 못 보는 상태였다.

> **[HARD] zsh 주의**: grep 스캔은 반드시 `--include='*.tsx'`처럼 따옴표로 감싼다. 따옴표 없는 형태는 zsh가 grep보다 먼저 글롭하고 중단시킨다. `bash -n`은 잡지 못한다.
> **[HARD] `grep -c` 종료코드 억제 관례는 eslint에 적용하지 않는다.** `grep -c`의 exit 1은 "개수 0"이라는 부수 신호라 `|| true`로 억제하지만, **eslint의 exit 1은 의미 있는 신호**다. 억제 대상이 아니라 **비교 대상**이며, 판정은 종료코드가 아니라 아래 기준선과의 **델타**로 한다.

---

## §F.1 eslint 기준선 — 축자 고정 [HARD]

**넓힌 범위는 미변경 트리에서 이미 실패한다.** 따라서 "eslint 통과"를 절대 조건으로 쓰면 M6 커밋이 0개인 트리에서도 RED가 나오고, 그 RED는 *"M6에 숨은 값 의존이 있다"* 와 *"레포에 기존 lint 기준선이 있다"* 를 구분하지 못한다 — 구분이야말로 AC-SDU-012의 존재 이유다. 그래서 절대 통과가 아니라 **기준선 대비 델타**로 판정한다.

**실측 (2026-08-18, 미변경 트리 `main`)**

```
$ cd frontend && npx eslint src/components/SectorAnalysis src/components/common \
    src/components/ChartGrid src/components/StockExplorer src/utils --max-warnings=0
EXIT=1
✖ 27 problems (27 errors, 0 warnings)
```

| 파일 | 건수 | 규칙 |
|---|---|---|
| `ChartGrid/ChartCell.tsx` | 6 | `no-explicit-any` ×2 (`232:33`, `233:29`), `react-hooks/refs` ×4 (`392:20` ×3, `394:20`) |
| `ChartGrid/__tests__/ChartGrid.integration.test.tsx` | 3 | `no-unused-vars` (`12:27`, `61:7`, `611:13`) |
| `ChartGrid/__tests__/ChartGrid.perf.test.tsx` | 1 | `no-unused-vars` (`14:17`) |
| `ChartGrid/__tests__/StockSearchBox.test.tsx` | 1 | `no-unused-vars` (`13:42`) |
| `SectorAnalysis/RRGChart.tsx` | 2 | `react-refresh/only-export-components` (`39:17`), `react-hooks/set-state-in-effect` (`150:5`) |
| `SectorAnalysis/SectorAnalysis.tsx` | 1 | `react-hooks/set-state-in-effect` (`115:5`) |
| `SectorAnalysis/SectorBubbleChart.tsx` | 1 | `react-refresh/only-export-components` (`39:17`) |
| `SectorAnalysis/__tests__/SectorBubbleChart.zoom.test.tsx` | 2 | `react-hooks/immutability` (`33:7`, `34:7`) |
| `SectorAnalysis/__tests__/SectorDetailPanel.test.tsx` | 1 | `no-unused-vars` (`307:11`) |
| `SectorAnalysis/__tests__/StockBubbleChart.zoom.test.tsx` | 2 | `react-hooks/immutability` (`36:7`, `37:7`) |
| `StockExplorer/StockExplorer.tsx` | 2 | `react-refresh/only-export-components` (`19:14`), `react-hooks/set-state-in-effect` (`74:5`) |
| `common/MetricCell.tsx` | 5 | `react-refresh/only-export-components` (`34:17`, `38:17`, `70:17`, `86:17`, `93:17`) |
| **합계** | **27** | |

**[HARD] 이 기준선은 고치는 대상이 아니다.** 27건 중 M6이 건드리는 파일에 있는 것들을 "겸사겸사" 고치면 범위 침식이다. 본 SPEC의 의무는 **신규 0건**이지 기준선 해소가 아니다.

**A는 집합이 아니라 다중집합이다 (D12).** 위 표의 `×3`(`ChartCell.tsx:392:20` `react-hooks/refs`)이 다중도를 기록한다. 엄격한 집합 의미에서는 이 3건이 원소 하나로 붕괴하므로 셋 중 하나가 사라져도 `B \ A == ∅`가 검출하지 못한다. **의도된 결과다** — AC의 목적은 **신규 검출**이고, 기준선 오류가 *고쳐지는* 것은 회귀가 아니다. 즉 **`A \ B`(소실)는 의도적으로 확인하지 않는다.** 판정 시 A는 이 표의 다중도를 포함한 다중집합으로 읽되, 비교는 `B \ A` 한 방향만 한다.

---

## §F.2 G-F5 결정 후보 — M6 첫 커밋 이전에 확정

| 안 | 내용 | 평가 |
|---|---|---|
| **(a) 예외 사전 선언 — 추정 정답** | `MetricCell.tsx`의 `react-refresh/only-export-components` **+2건**을 기준선 블록에 **사전 선언된 예외로 명시 추가**한 뒤 판정 | **근거**: 이 파일은 이미 같은 계열 포매터 `percent1`/`percent2`를 export하고 있고 `rating0`/`pct0`는 **정확히 같은 계열**이다. 파일의 성격을 바꾸지 않고, REQ-SDU-001의 "단일 출처" 전제도 유지된다 |
| (b) 비컴포넌트 모듈로 분리 | 포매터를 별도 모듈로 이동 | **기각 방향.** 둘만 옮기면 포매터 계열이 두 모듈로 쪼개져 넷 중 둘만 앵커 파일에 남는다 — 피하려던 lint 지적보다 나쁘다. 다섯 함수를 통째로 옮기면 `@MX:ANCHOR metricDisplay` 파일 자체를 리팩터링하게 되어 **REQ-SDU-001 범위를 한참 넘는다** |
| (c) `export const rating0 = (n) => …` 화살표 형태 | 함수 선언 대신 const 바인딩 | **거의 죽은 것으로 보이나 미측정 — 가설로 기록.** `frontend/eslint.config.js:16`이 `reactRefresh.configs.vite` 프리셋을 쓰고, 이 프리셋은 `allowConstantExport: true`라 **상수 리터럴 export만** 면제한다. 그래서 `MISSING_TEXT`/`INSUFFICIENT_TEXT`(`:12`/`:13`, 문자열 리터럴)는 안 걸리고 함수 export는 걸린다. 화살표 함수 const는 상수 리터럴이 아니므로 **면제되지 않을 가능성이 높다** → (c) 기각 시 (a)가 강화된다. **직접 측정하지 않았으므로 가설이다** — M6 킥오프에서 lint 1회로 확정한다. 확정 전까지 **(a)가 추정 정답** |

---

## §G 안티패턴 (lessons.md 유래)

- **#9** 대조 단언은 되돌림 RED 관측으로만 판정한다. 단언 양변이 같은 함수/표현식에서 오면 무효 — 최소 한 변은 검증 대상 프로덕션 경로에서 와야 한다.
- **#9** 명세의 스캔 명령은 실제 실행해 관측 출력을 리터럴로 고정한다(G-F3가 그 대상).
- **#1/#2** 표시·발견성 결정은 라이브 확인 후 잠근다. 라벨 문자열은 사용자가 보는 것이므로 M6 랜딩 후 실화면 확인을 남긴다.
- **#6** ship 커밋 또는 직후 sync 커밋에서 frontmatter `status`를 갱신한다.

## §H 교차 참조

- spec.md §2 의존 비대칭 / §4 범위 밖
- acceptance.md — AC 전량 + 되돌림 절차
- 형제 SPEC `SPEC-SECTOR-METRIC-UNIFY-001` (tombstone 매핑표 포함)
