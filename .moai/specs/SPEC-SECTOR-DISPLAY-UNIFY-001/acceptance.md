# SPEC-SECTOR-DISPLAY-UNIFY-001 — 인수 조건

## 규약 (모든 AC에 적용)

- **[HARD] 판정 기준 (lessons.md #9)**: AC는 "테스트가 존재하고 GREEN"이 아니라 **"되돌림을 실제 적용해 RED를 관측했는가"**로만 만족된다. 실증하지 못한 항목은 GREEN이 아니라 **Gaps**로 기록한다.
- **[HARD] zsh 글롭**: grep 스캔은 `--include='*.tsx'`처럼 따옴표로 감싼다.
- **[HARD] `grep -c` 종료코드**: 개수 0이면 종료코드 1이다. 목표가 0인 스캔은 `|| true` + stdout 파싱으로 판정하고, 종료코드를 통과 판정에 쓰지 않는다.
- **[HARD] 의존 게이트**: §B(M7) AC는 형제 SPEC `SPEC-SECTOR-METRIC-UNIFY-001` **M5 머지 이후**에만 판정 가능하다. 미머지 상태의 GREEN은 폴백 경로를 측정한 것이므로 무효다(갭 G-F4).
- **[HARD] eslint 판정은 델타다**: 절대 통과가 아니라 `plan.md §F.1` 기준선(**27건**) 대비 **신규 0건**으로 판정한다. `grep -c`의 exit 1을 `|| true`로 억제하는 관례는 **eslint에 적용하지 않는다** — eslint의 exit 1은 의미 있는 신호이므로 억제 대상이 아니라 비교 대상이다.

---

## §0 REQ ↔ AC 매핑 (명시) — [HARD] 암묵 항등 관례에 의존하지 않는다

001~008은 번호가 우연히 일치하지만 **009~011은 어긋난다.** 재번호 대신 이 표를 정본으로 둔다.

| REQ | AC | 내용 |
|---|---|---|
| REQ-SDU-001 | AC-SDU-001 | 반올림 규약 단일 출처 |
| REQ-SDU-002 | AC-SDU-002 | `null%` 해소 |
| REQ-SDU-003 | AC-SDU-003 | 임계값 상수 단일 출처 |
| REQ-SDU-004 | AC-SDU-004 | 라벨 정확성 |
| REQ-SDU-005 | AC-SDU-005 | 색 램프 분리 |
| REQ-SDU-006 | AC-SDU-006 | 기간별 순위 실반영 |
| REQ-SDU-007 | AC-SDU-007 | `data[]` 부재 폴백 캡션 |
| REQ-SDU-008 | AC-SDU-008 | RS 문자열 3면 동일성 |
| **REQ-SDU-009** (`activePeriod` 헤더 + 세 열 유지) | **AC-SDU-010** | ← 번호 어긋남 |
| **REQ-SDU-010** (안내 문구 표시 라벨) | **AC-SDU-011** | ← 번호 어긋남 |
| **REQ-SDU-011** (기간 토글 축 거동) | **AC-SDU-009** | ← 번호 어긋남 |
| (프로세스 — REQ 없음) | AC-SDU-012 | 의존 비대칭 증명 |
| (프로세스 — REQ 없음) | AC-SDU-013 | 무회귀 |

> 양방향 고아는 0건이다(커버리지 온전). 이 표가 없으면 run 단계가 "AC-SDU-009 PASS"를 시험하지도 않은 REQ-SDU-009에 대해 보고하게 된다.

---

## §A M6 AC — 백엔드 독립, 선행 판정 가능

### AC-SDU-001 — 반올림 규약 단일 출처
**Given** M6 적용 트리 **When** `MetricCell.tsx` 밖에서 RS/비율 값을 직접 포맷하는 호출부를 스캔하면 **Then** 잔여가 **0**이고, 전환된 호출부 개수가 M6 착수 시 확정한 관측값과 같다.
- **[HARD] 개수는 착수 시 실행 스캔으로 확정한다.** 원본 계획의 "8개"는 미검증 수치이므로 그대로 단언하지 않는다(갭 G-F3). 착수 스캔의 **관측 출력을 이 AC에 리터럴로 고정**한 뒤 판정한다.
- **착수 스캔 확정 (2026-08-18, M6 첫 커밋 이전 — G-F3 소진).** 아래 명령의 관측 출력 **14줄**을 리터럴로 고정한다. 판정 시 동일 명령의 잔여가 **0**이고 전환 개수가 **14 (rating0 7 + pct0 7)** 과 같아야 한다:
  ```bash
  cd frontend && grep -rn --include='*.tsx' -E 'String\(Math\.round\(n\)\)|Math\.round\(stock\.rs_12m\)|n => n\.toFixed\(1\)|value=\{sector\.rs_avg\} />|label="RS Avg" value=\{sector\.rs_avg\} />|\$\{Math\.round\(n\)\}%|\(n\) => `\$\{n\}%`|\$\{sector\.(rs_top_pct|nh_pct|stage2_pct)\}%' src/components/SectorAnalysis src/components/ChartGrid src/components/StockExplorer | grep -v __tests__
  ```
  > 패턴 정정 (M6 커밋 이전, 2026-08-19): 최초 핀의 `label="RS Avg" value={sector.rs_avg}` 은 전환된 형태(`format={rating0}` 부착)까지 부분 매칭해 잔여 0 판정을 오염시켰다. 종결자 ` />` 를 붙여 **미전환 형태만** 매칭한다. 킥오프 관측 출력 14줄은 변하지 않는다(원 라인이 모두 `} />` 또는 위 패턴들로 종결).
  관측 출력 (14줄, 전부 변환 대상):
  ```
  src/components/SectorAnalysis/SectorBubbleChart.tsx:249:          const rsAvg = metricText(toMetricValue(d[1]), n => n.toFixed(1))
  src/components/SectorAnalysis/SectorDetailPanel.tsx:99:        <MetricCard label="RS Avg" value={sector.rs_avg} />
  src/components/SectorAnalysis/SectorDetailPanel.tsx:100:        <MetricCard label="RS Top %" value={`${sector.rs_top_pct}%`} />
  src/components/SectorAnalysis/SectorDetailPanel.tsx:101:        <MetricCard label="52W High %" value={`${sector.nh_pct}%`} />
  src/components/SectorAnalysis/SectorDetailPanel.tsx:102:        <MetricCard label="Stage 2 %" value={`${sector.stage2_pct}%`} />
  src/components/SectorAnalysis/SectorDetailPanel.tsx:139:                        <MetricCell value={sub.rs_avg} format={(n) => String(Math.round(n))} />
  src/components/SectorAnalysis/SectorDetailPanel.tsx:142:                        <MetricCell value={sub.stage2_pct} format={(n) => `${Math.round(n)}%`} />
  src/components/SectorAnalysis/SectorDetailPanel.tsx:181:                          <MetricCell value={stock.rs_12m} format={(n) => String(Math.round(n))} />
  src/components/SectorAnalysis/SectorRankingTable.tsx:188:                <MetricCell value={sector.rs_avg} />
  src/components/SectorAnalysis/SectorRankingTable.tsx:197:                <MetricCell value={sector.rs_top_pct} format={(n) => `${n}%`} />
  src/components/SectorAnalysis/SectorRankingTable.tsx:206:                <MetricCell value={sector.nh_pct} format={(n) => `${n}%`} />
  src/components/SectorAnalysis/SectorRankingTable.tsx:215:                <MetricCell value={sector.stage2_pct} format={(n) => `${n}%`} />
  src/components/ChartGrid/ChartCell.tsx:297:  const rsValue = stock.rs_12m === null ? null : Math.round(stock.rs_12m)
  src/components/StockExplorer/StockTable.tsx:229:                <td data-col-key="rs_12m"><MetricCell value={c.rs_12m} format={(n) => String(Math.round(n))} /></td>
  ```
  할당 — **rating0 (7)**: BubbleChart `:249`, Panel `:99`·`:139`·`:181`, RankingTable `:188`, ChartCell `:297`, StockTable `:229` / **pct0 (7)**: Panel `:100`·`:101`·`:102`·`:142`, RankingTable `:197`·`:206`·`:215`.
- **되돌림**: 전환된 호출부 하나를 `toFixed(1)` 직접 호출로 되돌림 → 잔여 스캔이 1을 반환하는 것을 RED로 관측

### AC-SDU-002 — `null%` 버그 해소
**Given** 결측 지표를 가진 섹터 **When** `MetricCard`(`SectorDetailPanel.tsx:18-30`)를 렌더하면 **Then** 렌더 문자열에 `null`이 포함되지 않고 `–`가 표시된다.
- **(D7 기록)** 인용 `SectorDetailPanel.tsx:18-30` 중 `MetricCard`는 실제로 **`:22-30`**이며, `null%`의 **생산 지점은 호출부 `:100`**(`` value={`${sector.rs_top_pct}%`} ``)이다. 본 AC는 **렌더 출력**을 관측하므로 그대로 유효하지만, `MetricCard` 내부만 고치고 호출부 보간을 남겨 두면 통과하지 못한다
- **되돌림**: `MetricValue` 수용 이전 형태로 되돌림 → `null%` 문자열 재현 RED

### AC-SDU-003 — 임계값 상수 단일 출처 (교차 언어 등식)
**Given** M6 적용 트리 **When** `rsMetrics.ts`의 `RS_TOP_THRESHOLD`와 백엔드 `my_chart/analysis/sector_metrics.py:58`의 `_RS_TOP_THRESHOLD`를 대조하면 **Then** **수치가 같다**.
- **[HARD] 백엔드 값을 손으로 옮겨 적어 비교하지 않는다.** 심볼이 **비공개(`_` 접두)이며 float(`80.0`)**이고 TS 상수는 `80`이므로: 테스트가 상대경로로 `.py`를 읽어 정규식으로 `_RS_TOP_THRESHOLD` 대입값을 추출 → `parseFloat` → **수치 등식**(문자열 등식 아님)을 단언한다. 최종 형태는 run-phase에서 확정(갭 G-F1)
- **And** `StockTable.tsx:59`, `ChartCell.tsx:299`의 두 술어가 상수 유래 `title`을 갖는다
- **[HARD] 되돌림 안전 규약 — 이 AC는 `frontend/` 밖으로 나가는 본 SPEC의 유일한 지점이다.** 되돌림이 **형제 SPEC 소유 파일**(`my_chart/analysis/sector_metrics.py`)을 변형하며, 공유 체크아웃에서 그 SPEC의 run 작업이 동시에 진행될 수 있다. 따라서:
  1. **사전 조건**: 편집 **전에** `git status --short`가 **깨끗해야** 한다. 미커밋 변경이 있으면 실행하지 않는다 — 복원이 남의 작업을 되돌릴 수 있다
  2. **금지 창**: 형제 SPEC의 run 작업이 미커밋 상태인 동안에는 **실행하지 않는다**
  3. **단일 스텝**: 편집 → 테스트 실행 → 복원을 **중단 없는 한 스텝** 안에서 끝낸다. 편집한 채로 다른 작업을 하지 않는다
  4. **사후 조건**: 복원 후 `git status --short`가 다시 깨끗함을 확인해 증명한다
- **되돌림**: 위 규약 아래에서 백엔드 상수를 `85.0`으로 바꾸는 임시 편집 → 등식 RED 관측 → 복원

### AC-SDU-004 — 라벨 정확성
**Given** M6 적용 트리 **When** 각 라벨을 읽으면 **Then** `'RS 80+ 비중'` / `'RS 50 (유니버스 백분위 중앙)'` / 버블 Y축 `'RS Rating 평균 (0-100)'` / `ChartCell` 배지 `RS등급` / RRG 패널 "순위표 RS Rating과 다른 지표" 캡션이 존재하고, 구 문자열(`'RS Top %'`, `'RS 중앙'`)은 **잔여 0건**이다.
- 신규 문자열 존재 단언만 두면 구 문자열이 남아 공존해도 통과한다 → **잔여 0건 단언을 함께 둔다**
- **되돌림**: 각 문자열을 이전 값으로 되돌림 → 해당 단언 RED

### AC-SDU-005 — 색 램프 분리
**Given** M6 적용 트리 **When** 동일한 수치값에 대해 **등급 셀**(`SectorRankingTable.tsx:185`, `sector.rs_avg`)과 **비중 셀**(`:194`, `sector.rs_top_pct`)이 렌더한 배경색을 각각 읽으면 **Then** 두 색이 **다르다**.
- **[HARD] 반동어반복 가드 정정**: 현재 램프는 **단일 헬퍼 `getCellColor(value, type)`**(`:54`, `type: 'return' | 'percentage'`) 하나뿐이며 `:185`/`:194` 둘 다 `'percentage'`를 넘긴다. "서로 다른 헬퍼 둘"이라는 전제는 트리에 존재하지 않았다. 자연스러운 수정은 **세 번째 `type`(예: `'rating'`) 추가**이고, 단언은 **두 프로덕션 호출부(`:185` / `:194`)의 렌더 출력**을 비교한다 — 헬퍼를 테스트가 직접 두 번 호출해 비교하면 여전히 무효다(lessons #9)
- **되돌림**: `:185`를 다시 `'percentage'`로 되돌림 → 두 색이 같아지는 것을 RED로 관측

### AC-SDU-008 — RS 문자열 3면 동일성
**Given** 동일 섹터 픽스처 **When** Table / Bubble 툴팁 / 상세 패널을 각각 렌더해 RS 표시를 읽으면 **Then** 세 곳의 **최종 문자열이 동일**하다(숫자값이 아니라 렌더 출력).
- 비교 양변은 **서로 다른 컴포넌트의 렌더 출력**에서 온다. 같은 헬퍼를 세 번 호출해 비교하면 무효다
- **되돌림**: 세 호출부 중 하나를 `toFixed(1)`로 되돌림 → 문자열 불일치 RED

---

## §B M7 AC — 형제 SPEC M5 머지 이후에만 판정

### AC-SDU-006 — 기간별 순위 실반영
**Given** `sectors[]`가 `[1,2,3]`, 봉투 `data[]`가 `[3,1,2]` 순위를 담은 픽스처 **When** 해당 기간으로 Table을 렌더하면 **Then** 화면이 **`3,1,2`**를 표시한다.
- 두 배열이 **서로 다른 순서**여야 한다. 같은 순서 픽스처는 어느 구현으로도 통과하는 항진명제다
- **되돌림**: `data[]` 조인을 제거해 `sectors[]`만 읽게 되돌림 → `1,2,3` 표시 RED

### AC-SDU-007 — `data[]` 부재 폴백 캡션
**Given** `data[]`가 없는 응답 픽스처 **When** Table을 렌더하면 **Then** composite 순위를 쓰고 캡션에 `순위 기준: 종합점수(3기간 가중)`가 보인다.
- **되돌림**: 캡션 분기를 제거 → 캡션 부재 RED

### AC-SDU-009 — 기간 토글 축 거동
**Given** M7 적용 프론트 **When** 기간 토글을 1W→1M→3M으로 전환하면 **Then** 버블 **Y축 값(RS)은 불변**이고 **X축(초과수익률)만** 변한다.
- Y 불변과 X 변화를 **둘 다** 단언한다. Y 불변만 두면 응답 전체가 상수여도 통과한다
- **되돌림**: `rs_avg`를 기간 의존 필드로 읽게 하는 편집 주입 → Y 이동 RED

### AC-SDU-010 — `activePeriod` 열 헤더 + 세 열 유지
**Given** M7 적용 프론트 **When** `activePeriod='1m'`로 렌더하면 **Then** 1M 열 헤더에 `(순위 기준)`이 붙고, **세 수익률 열이 모두 존재**한다.
- 열 개수 단언을 함께 둔다 — 선택 열만 남기는 구현을 막는 것이 이 AC의 절반이다
- **되돌림**: 비선택 열을 제거 → 열 개수 RED

### AC-SDU-011 — 안내 문구 표시 라벨
**Given** M7 적용 프론트 **When** `SectorAnalysis.tsx:218` 안내 문구를 읽으면 **Then** 원시 상태값(`기간 1m`)이 아니라 표시 라벨(`:30` 유래)이 렌더된다.
- **되돌림**: 원시 상태값 출력으로 되돌림 → `기간 1m` 문자열 재현 RED

---

## §C 프로세스 AC

### AC-SDU-012 — M6 독립 배포 가능성 (의존 비대칭 증명)

**Given** 형제 SPEC이 **머지되지 않은** 베이스(현재 `main` — 형제 SPEC이 `draft`이므로 `main`이 정확히 요구되는 베이스다)
**When** M6 커밋만 적용해 plan.md §F 전 구간 명령을 실행하면
**Then** 아래 셋이 모두 성립한다:
1. `npm run typecheck` (= `tsc -b`) **통과**
2. `vitest` 실패가 plan.md §D의 M6 대상 2건(`SectorRankingTable.test.tsx`, `SectorDetailPanel.test.tsx` 라벨)에 한정
3. **eslint 신규 0건** — `plan.md §F.1`의 27건 기준선에 없는 오류가 하나도 추가되지 않는다

- **[HARD] 절대 통과가 아니라 델타다.** 넓힌 eslint 범위는 **미변경 트리에서 이미 27건 실패**하므로, "전부 통과"로 쓰면 M6 커밋이 0개인 트리에서도 RED가 나온다. 그 RED는 *"M6에 숨은 값 의존이 있다"* 와 *"레포에 기존 lint 기준선이 있다"* 를 **구분하지 못하며, 구분이야말로 이 AC의 존재 이유**다
- 판정 방법: 기준선 블록의 `(파일, 행:열, 규칙)` 집합을 A, 이번 실행 결과 집합을 B라 할 때 **`B \ A == ∅`**. `|B| > |A|`만 보는 개수 비교로는 한 건이 사라지고 다른 한 건이 생긴 경우를 놓친다
- **G-F5 주의**: REQ-SDU-001이 `MetricCell.tsx`에 export를 2개 더 추가하면 `react-refresh/only-export-components`가 +2건 날 가능성이 높다. M6 착수 시 결정된 처리(예외 사전 선언 또는 모듈 분리)를 기준선 블록에 반영한 뒤 판정한다 — **판정 시점에 즉흥적으로 예외를 만들지 않는다**
- **되돌림**: M6 커밋에 `data[]` 소비 코드를 섞으면 `tsc` 또는 `vitest`가 RED — 그것이 관측자다. 기준선 대비 델타 방식이라 기존 27건이 이 관측자를 가리지 않는다

### AC-SDU-013 — 갱신 대상 외 무회귀
**Given** 전 마일스톤 완료 트리 **When** plan.md §F 전 구간 명령을 실행하면 **Then**:
- `vitest` 실패가 plan.md §D의 의도적 갱신 대상 **3건**에 한정되고 그 밖의 실패는 **0건**
- `npm run typecheck` (= `tsc -b`) 통과
- **eslint 신규 0건** (기준선 27건 대비 델타 — AC-SDU-012와 동일 판정 방식)

> 개정 전 문구("그 밖의 실패는 0건")는 eslint 27건 때문에 **거짓**이었고, 27건 중 3건이 M6이 건드리는 파일에 있어 run 단계를 무관한 lint 수정으로 떠밀었다(범위 침식). 기준선 27건은 **본 SPEC의 수선 대상이 아니다.**

---

## §D 엣지 케이스

| # | 케이스 | 기대 |
|---|---|---|
| EF-1 | 지표 4개 전부 null인 섹터 | 각 셀이 `–`, 행은 사라지지 않음 |
| EF-2 | `data[]`는 있으나 섹터명 조인 실패 | 조인 실패 섹터는 composite 순위 유지, 캡션 폴백 표기 |
| EF-3 | `data[]`가 빈 배열(`[]`) | 부재와 동일하게 폴백 + 캡션(널 아님과 길이 0을 구분하지 않는다) |
| EF-4 | 기간 토글 값이 알 수 없는 값 | 표시 라벨 조회 실패 시 원시값 노출 대신 기본 라벨 |

---

## §E Definition of Done

- [ ] AC-SDU-001~013 판정 완료 — 각 항목에 **되돌림 RED 관측 증거**(verbatim 실패 출력) 또는 **Gaps 기재**
- [ ] G-F3(호출부 개수)가 M6 착수 스캔으로 확정되고 관측 출력이 AC-SDU-001에 고정됨
- [ ] G-F1(교차 언어 추출 형태)이 run-phase 착수 시 확정됨
- [ ] G-F4 확인 — M7 AC 판정 시점에 형제 SPEC M5가 머지돼 있음을 근거와 함께 기록
- [ ] **G-F5 결정** — `MetricCell.tsx`의 `react-refresh/only-export-components` 증가 처리(예외 사전 선언 / 모듈 분리)를 M6 착수 시 결정하고 기준선 블록에 반영
- [ ] **M6 단독 착지 시** `depends_on` override 근거가 `.moai/logs/depends-on-override.log`에 기록됨 (spec.md §2.1)
- [ ] plan.md §F 전 구간 명령 실행 + 종료코드 관측 (eslint는 파이프 없이 `; echo $?`)
- [ ] M6 랜딩 후 실화면 확인 기록 (lessons #1/#2 — 표시 결정은 라이브 확인 후 잠근다)
- [ ] frontmatter `status` 갱신 (lessons #6)
