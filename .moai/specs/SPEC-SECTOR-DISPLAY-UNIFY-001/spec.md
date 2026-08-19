---
id: SPEC-SECTOR-DISPLAY-UNIFY-001
title: Sector Analysis 프론트 표시 통일 및 기간 토글 실동작
version: "0.3.0"
status: completed
created: 2026-08-18
updated: 2026-08-19
author: manager-spec
priority: P2
phase: "v0.5.0 target"
module: sector-analysis
lifecycle: spec-anchored
tags: "sector, frontend, display, labels, period-toggle"
tier: M
depends_on: [SPEC-SECTOR-METRIC-UNIFY-001, SPEC-SECTOR-UX-001]
---

# SPEC-SECTOR-DISPLAY-UNIFY-001 — Sector Analysis 프론트 표시 통일 및 기간 토글 실동작

> 승인된 원본 계획: `.moai/plans/rs-purring-key.md` M6·M7. 형제 백엔드 SPEC `SPEC-SECTOR-METRIC-UNIFY-001`(M0~M5)에서 분리된 SPEC이다.

## HISTORY

| 버전 | 날짜 | 변경 |
|---|---|---|
| 0.3.0 | 2026-08-18 | plan-audit iteration 2 (PASS-WITH-DEBT 0.875) 잔여 4건. D11: G-F5 소진 경계를 **M6 첫 커밋 이전**으로 명시(+2가 기계적으로 확정임을 소스 대조로 근거화), `plan.md §F.2` 결정 후보표 신설 — (a) 예외 사전 선언을 **추정 정답**, (b) 모듈 분리 기각 방향, (c) 화살표 const는 `allowConstantExport` 가설로 기록(미측정). D12: A가 **다중집합**이며 `A \ B`(소실)는 의도적 미확인임을 명시. D6: G-F1에 `frontend/`→루트 경계 + Node `fs`/`import.meta.url` 위험 기록. D7: REQ-SDU-002·AC-SDU-002에 `MetricCard`는 `:22-30`, `null%` 생산 지점은 호출부 `:100` 기록(수정 아님) |
| 0.2.0 | 2026-08-18 | plan-audit iteration 1 (FAIL 0.70) 대응. D1+D4: eslint 범위를 M6 변경 디렉터리 3곳까지 넓혀 **기준선 27건 축자 고정**, AC-SDU-012/013을 절대 통과 → **기준선 대비 신규 0건** 델타 단언으로 재작성. D2: 명시적 REQ↔AC 매핑표 신설(009/010/011 어긋남 해소). D3: `depends_on` 미충족 시 run 단계 분기 지시(§2.1) 신설. D5: 형제 파일 되돌림 안전 규약. D8: REQ-SDU-007 `(While)` / REQ-SDU-011 `(When)` |
| 0.1.0 | 2026-08-18 | `SPEC-SECTOR-METRIC-UNIFY-001`에서 M6/M7 분리 신설 (D7 결정 A) |

---

## §1 배경 — 왜 별도 SPEC인가 (재논의 금지)

절단면은 감사가 새로 그은 것이 아니라 **승인된 원본 계획서 자신이 이미 그어 둔 것**이다 — `.moai/plans/rs-purring-key.md`의 M6 헤더가 *"프론트 표시 통일 (백엔드 독립, 먼저 배포 가능)"*이라고 명시한다. 예산을 맞추려 자른 것이 아니라 원래 둘이던 것을 하나로 묶어 뒀던 것이며, 배포 순서(백엔드 선행 → 프론트 후행)와도 일치한다.

본 SPEC이 해소하는 결함은 원본 계획의 **D6(라벨·표시 부정확)**과 **D5(Table 기간 토글 무동작)**이다.

### §1.1 D6 — 라벨·표시 부정확
`'RS 중앙'`이 계산된 중앙값이 아닌 50 상수(`SectorBubbleChart.tsx:217`) / `'RS Top %'`가 RS 점수처럼 보이나 실제로는 "RS≥80 비율"(임계값 미표기) / UI에서 "RS"가 세 가지를 지칭(등급·RRG RS-Ratio·RS Line, `ChartCell.tsx:326`과 `:352`가 한 셀에 공존) / 같은 지표 반올림 제각각(`Math.round` / `toFixed(1)` / 반올림 없음) / `MetricCard`가 null에 `null%` 문자열 렌더(ER-2 위반).

### §1.2 D5 — Table 기간 토글 무동작
`frontend/src/api/market.ts:12-19`가 `period`를 안 보낸다. **`period`만 추가해도 화면은 안 바뀐다** — 기간별 `rank` 재배정은 봉투 `data[]`에만 있고(`my_chart/analysis/sector_metrics.py:695-706`), 프론트가 읽는 `sectors[]`는 `compute_sector_ranking`이 `period`를 받지 않아 항상 composite 기준이다. **`data[]`를 읽어야 실제로 동작한다.**

---

## §2 의존 관계 — 비대칭이며, 이것이 내부 순서의 근거다 [HARD]

두 마일스톤의 의존성이 다르다. 내부 순서(M6 먼저, M7 나중)의 근거는 "되돌리기 쉬움"이 아니라 **의존성**이다.

| 마일스톤 | 백엔드 의존 | 근거 |
|---|---|---|
| **M6** (반올림 규약 · 임계값 상수화 · 라벨 정확성 · 색 램프 분리) | **없음 — 선행 가능** | 전부 기존 응답 필드의 표시 방식만 바꾼다. 백엔드 머지를 기다릴 이유가 없고 단독 배포 가능하다 |
| **M7** (Table 기간 토글) | **`SPEC-SECTOR-METRIC-UNIFY-001` M5 완료에 의존** | 봉투 `data[]`를 읽는데, bubble/ranking 봉투 정상화(M5)와 기간 인자 배선이 백엔드 쪽에서 선행돼야 한다 |
| 버블 X축 라벨 변경 | **동일하게 M5 의존** | 초과수익률 벤치마크가 정의 B로 바뀐 뒤라야 라벨이 참이 된다 |

> **[HARD] 따라서 M6은 백엔드 머지를 기다리지 않는다.** 이 SPEC 전체를 백엔드 뒤로 미루면 독립 배포 가능한 개선이 불필요하게 지연된다. 형제 SPEC에 `depends_on`을 건 것은 M7·X축 라벨 때문이지 M6 때문이 아니다.

### §2.1 `depends_on` 미충족 시 run 단계 분기 지시 — [HARD]

`depends_on`의 충족 판정은 엄격히 `status: completed`이며 **마일스톤 단위 세분이 없다.** 따라서 `SPEC-SECTOR-METRIC-UNIFY-001`이 `draft`인 한 `/moai run`은 pre-flight에서 `wait / override / abort` 선택으로 막힌다 — 그리고 그 기계적 귀결은 §2의 [HARD] 지시("M6은 기다리지 않는다")와 정면으로 충돌한다.

**선언은 지우지 않는다.** `depends_on`을 빼면 M7의 실제 의존이 문서에서 사라져 더 나빠진다. 대신 어느 분기를 탈지 여기서 지시한다.

| 착지 대상 | 올바른 분기 | 조치 |
|---|---|---|
| **M6 단독 착지** | **`override`** | `--ignore-deps` 경로로 진행하고, **미충족 의존 ID와 본 §2의 비대칭 근거**를 `.moai/logs/depends-on-override.log`에 남긴다. M6은 값 의존이 없으므로 이 override는 근거 있는 것이며, AC-SDU-012가 그 근거를 기계적으로 검증한다 |
| **M7 착지** | **`wait`** | 형제 SPEC이 M5를 포함해 `completed`가 될 때까지 기다린다. `wait`가 옳은 유일한 경우다 |
| 판단 불가 | `abort` | 어느 마일스톤을 착지시키는지 불명확하면 중단하고 확인한다 |

> override는 의존을 부정하는 것이 아니라 **마일스톤 단위 세분이 없는 도구 한계를 우회**하는 것이다. 로그가 그 구분을 남긴다.

---

## §3 요구사항 (GEARS)

### §3.1 M6 — 백엔드 독립

- **REQ-SDU-001** (Ubiquitous) — 반올림 규약은 `MetricCell.tsx`(`@MX:ANCHOR metricDisplay`) 단일 출처를 통해야 한다. `rating0`/`pct0`를 추가하고 호출부를 전환한다.
- **REQ-SDU-002** (When) — `MetricCard`(`SectorDetailPanel.tsx:18-30`)가 결측값을 받을 때 `null%` 문자열이 아니라 `MetricValue` 규약의 `–`를 렌더해야 한다.
  > **(D7 기록 — 수정 아님, 구현 시 참고)** 인용 `:18-30`은 두 가지가 부정확하다. `MetricCard` 자체는 **`:22-30`**이고, `null%` 문자열이 **실제로 만들어지는 지점은 컴포넌트가 아니라 호출부 `:100`**(`` value={`${sector.rs_top_pct}%`} ``)이다 — 결측값이 템플릿 리터럴에 보간되면서 `null%`가 된다. 즉 요구사항이 수정 범위를 실제보다 좁게 잡고 있다. AC-SDU-002는 **렌더 출력**을 관측하므로 충족 가능성 자체는 유지되지만, 구현이 `MetricCard` 내부만 고치고 호출부 보간을 그대로 두면 통과하지 못한다.
- **REQ-SDU-003** (Ubiquitous) — RS 임계값은 `frontend/src/utils/rsMetrics.ts`에 상수로 존재해야 한다: `RS_TOP_THRESHOLD=80`(백엔드 `my_chart/analysis/sector_metrics.py:58` `_RS_TOP_THRESHOLD`의 거울) / `RS_STRONG_THRESHOLD=70` / `RS_S2_STRONG_THRESHOLD=60` / `RS_UNIVERSE_MIDPOINT=50`. 라벨 없던 두 술어(`StockTable.tsx:59`, `ChartCell.tsx:299`)에 상수 유래 `title`을 붙인다.
- **REQ-SDU-004** (Ubiquitous) — 라벨은 지시 대상을 정확히 서술해야 한다: `'RS Top %'` → `'RS 80+ 비중'`(+임계값 title) / `'RS 중앙'` → `'RS 50 (유니버스 백분위 중앙)'` / 버블 Y축 `'RS Rating 평균 (0-100)'`로 드릴다운(`'RS Rating (0-100)'`)과 정렬 / `ChartCell` 배지 `RS등급` / RRG 패널에 "순위표 RS Rating과 다른 지표" 캡션.
- **REQ-SDU-005** (Ubiquitous) — `SectorRankingTable.tsx:54-64`의 등급용 색 램프와 비중용 색 램프는 **서로 구분되는 채널**이어야 한다(현재 파란 램프를 공유).
- **REQ-SDU-008** (Ubiquitous) — 같은 섹터의 RS는 Table ↔ Bubble ↔ 상세 패널에서 **동일 문자열**로 표시되어야 한다.

### §3.2 M7 — 백엔드 M5 의존

- **REQ-SDU-006** (When) — 사용자가 Table 기간 토글을 전환할 때, 화면은 봉투 `data[]`의 기간별 `rank`/`rank_change`를 반영해야 한다.
- **REQ-SDU-007** (While) — 응답에 `data[]`가 없는 동안, 화면은 composite로 폴백하고 **캡션이 그 사실을 말해야** 한다(`순위 기준: 종합점수(3기간 가중)`).
- **REQ-SDU-009** (Ubiquitous) — `SectorRankingTable`은 `activePeriod` prop을 받아 선택 기간 열 헤더에 `(순위 기준)`을 표시해야 한다. **세 수익률 열은 모두 유지**한다(비교가 이 표의 존재 이유).
- **REQ-SDU-010** (Ubiquitous) — `SectorAnalysis.tsx:218`의 안내 문구는 원시 상태값(`기간 1m`)이 아니라 표시 라벨(`:30`)을 써야 한다.
- **REQ-SDU-011** (When) — 사용자가 기간 토글을 전환할 때, 버블 **Y축(RS) 값은 불변**이고 **X축(초과수익률)만** 변해야 한다(백엔드 INV-3의 화면 측 회귀 방어).

---

## §4 범위 밖 (exclusions)

### Out of Scope — 백엔드 산출 통일 (M0~M5)
- 단일 원천 전환·결측 제외·벤치마크 정의 B·거래대금 산식·봉투 정상화는 형제 SPEC **`SPEC-SECTOR-METRIC-UNIFY-001`** 소관이다. 본 SPEC은 응답 값을 바꾸지 않는다.

### Out of Scope — 버블 크기 사다리 재산출
- `PERIOD_SIZE_LADDER`(`bubbleRadius.ts`) `vMin`/`vMax` 재산출은 프론트 파일이지만 **백엔드 SPEC에 잔류**한다. 거래대금 단위를 바꾸는 당사자가 그쪽 M4이고, 이 SPEC으로 미루면 백엔드만 머지된 구간에서 모든 버블이 한쪽 끝으로 뭉친 채 배포된다. **경로만 보고 여기로 옮기지 말 것.**

### Out of Scope — RS 정의·축 배치·RRG 지표
- 형제 SPEC §2의 불변 조건 INV-1~INV-4를 그대로 승계한다. 본 SPEC은 **라벨 구분만** 개선하며 지표를 바꾸지 않는다.

### Out of Scope — ThemeAnalysis 동일 패턴 확산
- `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx`가 같은 표시 패턴을 갖는지 **미확인**이다. M6 작업 중 발견되면 별도 백로그로 기록만 하고 본 SPEC 범위를 넓히지 않는다.

---

## §5 참조

- 승인된 원본 계획: `.moai/plans/rs-purring-key.md` M6·M7
- 형제 SPEC: `SPEC-SECTOR-METRIC-UNIFY-001` (백엔드 M0~M5, 이관 tombstone 포함)
- 선행 SPEC: SPEC-SECTOR-UX-001 (`MetricCell` 규약 ER-1/ER-2, 버블 사다리)
- 프로젝트 교훈: `lessons.md` #9(대조 단언은 되돌림 RED 관측으로만 판정), #1/#2(표시·발견성 결정)
