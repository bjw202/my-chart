---
id: SPEC-SECTOR-UX-001
title: "섹터 분석 화면 계층 — 상태 모델·전환 규칙·시각화 규약"
version: "0.4.0"
status: draft
created: 2026-08-12
updated: 2026-08-14
author: manager-spec
priority: P1
phase: "sector-ux v1"
module: "frontend/src/contexts, frontend/src/components/SectorAnalysis, frontend/src/components/StockExplorer"
lifecycle: spec-anchored
tags: "sector, frontend, state-model, visualization, react, echarts"
depends_on: [SPEC-SECTOR-AGGREGATION-001]
related_specs: [SPEC-SECTOR-GRID-001, SPEC-SECTOR-AGGREGATION-001, SPEC-SECTOR-MINOR-COLOR-001]
tier: L
---

# SPEC-SECTOR-UX-001: 섹터 분석 화면 계층 — 상태 모델·전환 규칙·시각화 규약

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 0.1.0 | 2026-08-12 | manager-spec | 초기 SPEC. `docs/sector-ux/02-screen-flow.md` §3(상태 모델)·§5(전환)·§6~§7(컨트롤)·§8(로딩)·§9(시각화)·§10(오류·빈 상태)을 구현 계약으로 전환. Lesson #1/#2/#3/#5/#7 반영. `SPEC-SECTOR-MINOR-COLOR-001`의 색상 채널 계약과 `StockBubbleChart.tsx:28` `@MX:ANCHOR`를 보존 대상으로 명시. |
| 0.2.0 | 2026-08-12 | manager-spec | plan-audit 0.84 FAIL(L, thresh 0.85) 결함 델타 반영. **(1) tsc 게이트 달성 불가 해소** — 실측 총 33건 오류 중 `TS2353`은 1건(③ 소관)이고 32건은 선행 결함이며 상당수가 ③ 모듈 범위 안이다. AC-SUX-004를 (a) HARD `TS2353 == 0` / (b) 총량 `<= N` + ③ 수정 파일 NEW 0건으로 **2분할**. (b)가 (a)를 약화시키지 않음을 명시. **(2) 실행 불가 단언 3건 재작성** — AC-SUX-045 탈출구 `(또는 명세된 반올림 규칙)` 삭제 후 VZ-8 공식 리터럴 고정, AC-SUX-021 "정적 스캔: rank 재부여 코드 없음"을 실행 명령 + 행동 단언으로, AC-SUX-056 R1/R2 "그런 테스트가 없음을 확인"을 긍정 단언 + grep 부재 확인으로. **(3) 설계서 미수용 요구 3건 수용** — REQ-SUX-055(`01 §2.9` 순위 총수 `7/29` 병기), REQ-SUX-056(`02 §9.1` 섹터 버블 색상 = 기간 수익률 발산형 5단계), REQ-SUX-057(테두리 채널 VZ-0 충돌 단일화 — 섹터 버블=결측 거래대금 / 종목 버블=Stage). **(4) traceability를 REQ 그룹→REQ 단위**로 전개하고, 철회분을 §3.7 묘비 절로 분리 + 신규 REQ를 주제별 도메인 절에 배치(REQ-SUX-055 → §3.3 컨트롤 / REQ-SUX-056·057 → §3.5 시각화). **§3의 REQ 번호는 오름차순이 아니며 의도적으로 그렇다** — 배치 기준은 번호가 아니라 주제다. **(5) §0.1 "탭 전환 4회 이하"** 측정 절차 부재로 삭제 → 자동 검증 3항목으로 대체. **(6) REQ-SUX-054(산업명(중) 필터) 철회** — 사용자 결정으로 미구현, `01 §8.5` 계약을 구현에 맞춰 축소. U36·AC-SUX-057 삭제(결번). **사용자 결정 수용**: O-U1(비활성+툴팁, 잠정) · O-U4(기간별 고정 눈금) · O-U6(스크롤·하이라이트 or 추가, 교체 금지) · O-U7(섹터비중→Vol배→52W고 접기). **O-U8/O-U9 신설**(저커버리지 시각 인코딩 / ②의 O-A7 전파). |
| 0.3.0 | 2026-08-12 | manager-spec | plan-audit iteration 2 **PASS 0.87**(L, thresh 0.85; MUST-PASS 전항 통과, 단조 개선) 이후 잔여 결함 정리. **(D7) `AC-SUX-061` 고아 해소** — AC는 정의(`acceptance.md`)·E7·DoD·`plan.md` M4·§7 O-U7 해결 행에 모두 존재했으나 **어떤 REQ도 매핑되지 않아** §5 traceability 표에 행이 없었다(정의 60 / 추적 60이지만 **집합이 달랐다**). 열 접기 계약을 소유하는 **`REQ-SUX-058` 신설**(§3.3 컨트롤, `REQ-SUX-029` 기간 3열 상설의 폭 조건 확장) + traceability 행 추가. REQ 부재 상태에서는 구현 중 이 AC가 잘려도 §3의 어떤 항목도 반대하지 않았고, 그것은 Lesson #3(신규 열이 default 진입에서 안 보여 그림자 결함이 된 선례) 게이트를 재현하는 경로였다. **(D8) HISTORY 항목 (4)의 미검증 주장 정정** — "§3 번호 순서 정상화"는 실제로 일어나지 않았다(`REQ-SUX-055`는 `030`↔`031` 사이, `056/057`은 `048`↔`049` 사이에 그대로 있다). 주제별 배치가 **의도된 설계**임을 명시하는 문장으로 재작성하고 §3.7 서문에도 같은 취지를 못 박았다 — 재배열은 하지 않는다. **(D9) `progress.md` 갱신** — `open_questions`에 남아 있던 O-U1/O-U4/O-U6/O-U7(전부 v0.2.0에서 해결)과 `blocking_before_run`의 동일 4건을 정리하고 `resolved_open_questions`로 이력 보존. **`SPEC-SECTOR-AGGREGATION-001 completed`와 O-U9는 실제 차단 항목이므로 유지한다.** `ac_count` 57 → **60** 정정(v0.1.0 값 잔류분). |
| 0.4.0 | 2026-08-14 | manager-spec | **O-U9 해결 — 착수 차단 항목 전부 해소.** 사용자 결정(2026-08-14): **AG-5(최소 구성수 5)를 Bump에 적용하지 않는다.** ② `SPEC-SECTOR-AGGREGATION-001`은 v0.5.0 `completed`(main `65dfe2d`)로 종료됐고, 그 출하 구현이 이미 미적용이라는 것을 실물 대조로 확인했다 — `/sectors/history` → `compute_sector_history` → `compute_sector_ranking` → `_compute_sector_metrics`(`sector_metrics.py:947-948`이 *"AG-5 제외는 여기에 적용하지 않는다 — 규칙 AG-5는 `data[]`가 소유한다"* 를 명시), `get_sector_history`(`sector_advanced_service.py:218`)는 `SectorHistoryResponse` 생성 3곳 전부에서 `excluded=`를 전달하지 않아 봉투가 항상 빈 배열이다. 따라서 **②의 백엔드 변경은 없으며 amendment도 불필요하다**(② `completed` 유지). ③ 조치 3건: **(1)** `AC-SUX-019` · `AC-SUX-056 R5`의 검증 범위를 **Table · 섹터 Bubble · RRG로 한정**(Bump 제외)하고 §7 O-U9 · plan.md §0 차단 표 · DoD를 해결로 갱신. **(2)** 범위에서 빼기만 하지 않고 **Bump 반대 방향 단언을 신설** — 제외 섹터의 선이 Bump에 남아 있어야 하며, 되돌림 변형 `mut_bump_applies_ag5`(Bump 시계열을 `data[]` 섹터 집합과 교집합)에서 **RED 관측이 필수**다(Lesson #9). 단언 없는 범위 제외는 이후 누군가 Bump에 AG-5를 넣어도 어떤 AC도 반대하지 않는 상태를 만들며, 그것이 Lesson #3의 재현 경로다. **(3)** `REQ-SUX-017`(제외 섹터 가시성)에 적용 범위를 명문화 — Bump에 제외 영역을 렌더하는 구현은 충족이 아니라 **위반**이다. **도입하지 않은 것**: `connectNulls:false` 선 끊김 단언은 "Bump에도 적용" 분기 전용이었으므로 신설하지 않는다(해당 옵션 자체는 §1.2 보존 항목으로 불변). **의도된 귀결(회귀 아님)**: Bump는 전 섹터, Table `data[]`는 AG-5 통과 섹터라는 서로 다른 모집단 위에서 순위를 매기므로 같은 섹터의 rank가 두 화면에서 다를 수 있다. `CT-4`(AC-SUX-021)의 rank 일치는 순위표 내부(rank 열 ↔ 행 순서) 한정이며 Table↔Bump 교차 일치로 확대하지 않는다. `ac_count` 60 불변(신규 AC 없음 — 기존 AC 2건의 범위 한정 + 단언 추가). **plan-audit 캐시 무효화**: 본 개정으로 plan-artifact hash가 바뀌므로 v0.3.0의 PASS 0.87은 skip 근거로 쓸 수 없다 — `/moai run` Phase 1에서 plan-audit **재실행 필수**. |

---

## 0. BRIEF (Lesson #7 [HARD] 의무 항목)

### 0.1 라이브 사용 가설 + 재평가 체크포인트

| 항목 | 내용 |
| --- | --- |
| 가설 | 사용자는 W1(섹터 → 종목 발굴)을 주 동선으로 쓴다. 이 SPEC 이후 "시장 개요 → 섹터 분석 Table → 상세 패널 → 종목 탐색 → 차트 그리드" 5단계가 **컨텍스트 손실 없이** 이어지고, 되돌아와도 하던 자리가 유지되어야 한다. |
| 기대 행동 | ship 후 7일 사용 시점에 (a) `[이 섹터 종목 보기 →]` 버튼이 실제로 눌리는가, (b) 기간/시장 토글을 실제로 조작하는가(현행 시장 토글은 무동작이라 사용 이력이 없다), (c) Stage 분포 바 세그먼트 필터를 쓰는가, (d) 섹터 칩 `×`(스코프 해제)가 쓰이는가. |
| 정량 지표 | **(a) 측정 가능** — Rank 열과 행 순서 불일치 발생 **0건** (AC-SUX-021이 자동 검증). 패널 간 기준일 불일치 경고 노출 **0건**(정상 상태, AC-SUX-037이 자동 검증). 되돌아가기 전용 UI 컴포넌트 **0개** (AC-SUX-010 렌더 트리 단언).<br>**(b) 정성 지표로 재기술** — W1 5단계 완주 동선이 "되돌아가기 전용 UI 없이 이어지는가". **이전 판의 "탭 전환 4회 이하"는 삭제한다** — 아래 사유. |

> **"탭 전환 4회 이하" 삭제 사유**: 측정 방법이 없었다. 무엇을 1회로 세는지(상단 탭만인가 서브탭도인가, `[이 섹터 종목 보기 →]` 같은 프로그램 전환도 세는가), 누가 어떤 조건에서 재는지가 규정되지 않았다. 계측 코드도 없고 §0.1 재평가 시점에 이 숫자를 산출할 절차도 없다. **측정 절차 없는 정량 목표는 재평가 시점에 "달성했다"고 자평하게 만든다** — 이 SPEC이 제거하려는 바로 그 종류의 검증 불가 주장이다.
>
> 정량으로 남기려면 세션 계측(탭 전환 이벤트 로깅)이 필요하나, A1(단일 사용자·localhost·분석 도구 미도입)과 §4 Exclusions에 비추어 계측 도입은 과설계다. 따라서 **정성 지표로 낮추고, 대신 자동 검증 가능한 (a) 3항목을 정량 지표로 삼는다.** 재평가는 사용자 확인(§0.1 재평가 시점 ①~④)으로 수행한다.
| **재평가 시점** | ship 후 **7일**에 사용자에게 다음을 확인한다 — ① `sectorScopeFollow`(칩 ×) 개념이 이해되는가, ② CT-6 정렬 고지 띠가 유용한가 잔소리인가(02 O-3과 함께), ③ RRG/Bump의 비활성 기간 토글이 정보인가 소음인가, ④ 크기 범례가 실제로 읽히는가. |
| **폐기 조건** | `sectorScopeFollow` 이중 상태가 사용자에게 혼란만 준다면 SM-6를 폐기하고 "칩 × = 전역 선택 해제"로 단순화한다(SM-5만 유지). 이 경우 W1 복귀 경로가 약해지므로 **후속 amendment**로 처리하고 SPEC 전체를 폐기하지 않는다. |

### 0.2 성능 baseline + 목표값 [Lesson #7 필수 — 컨텍스트·리페치 추가]

본 SPEC은 **전역 Context 2개를 신설**하고 **재조회 트리거를 추가**한다. 리렌더 확산과 fetch 증가가 직접적 위험이다.

| 측정 지점 | baseline (측정 의무) | 목표 |
| --- | --- | --- |
| 앱 부팅 → 첫 상호작용 가능 (FCP / INP) | 현행 실측 | 회귀 없음 (INP P95 +10% 이내) |
| 부팅 시 발생하는 fetch 수 | 현행 실측 (전 탭 동시 마운트, LD-1) | **감소** — 활성 탭 데이터만 |
| 기간 토글 1회 → 표 갱신 완료 | 신규(현행은 클라이언트 재정렬이라 즉시) | P95 < 1.5s. 재조회 중 **기존 데이터 유지**(LD-C)로 체감 지연 완화 |
| 시장 토글 1회 → 전 패널 갱신 | 신규 | P95 < 2.0s |
| `selectedSector` 변경 시 리렌더되는 컴포넌트 수 | 신규 | Context 분리로 무관 컴포넌트 리렌더 0 — React DevTools Profiler로 측정 |
| 종목 표 500행 렌더 | 현행 실측 | 3열(1W/1M/3M) 추가 후 +20% 이내 |

**측정 의무**: run 착수 시 baseline을 먼저 측정해 progress.md §E.2에 기록한다. `AnalysisParamsContext`와 `SelectionContext`를 **하나로 합치지 않는** 이유가 이 지표다(기간 변경이 섹터 선택 소비자를 리렌더시키면 안 된다).

### 0.3 SPEC ID ↔ UI 요소 매핑 표 [Lesson #7 필수]

본 SPEC으로 **추가/변경되는 UI 요소 전량**:

| # | UI 요소 | 라벨/텍스트 | 위치 | 신규/변경 |
| --- | --- | --- | --- | --- |
| U1 | 기준일 배지 | `기준일 2026-08-11` | 섹터 분석 공통 헤더 | 신규 |
| U2 | 진행 중인 주 배지 | `🟡 진행 중인 주 (2일치)` | U1 옆 | 신규 |
| U3 | 격자 버전 표기 | `격자 canonical-v1` | 헤더 우측 | 신규 |
| U4 | 수동 새로고침 버튼 | `⟳ 새로고침` | 헤더 우측 | 신규 |
| U5 | 기간 토글 (단일 인스턴스) | `1W / 1M / 3M` | 섹터 분석 헤더 + 종목 탐색 헤더 | **통합**(현행 2벌) |
| U6 | 시장 토글 (단일 인스턴스) | `전체 / KOSPI / KOSDAQ` | 상동 | **통합 + 실동작화** |
| U7 | 벤치마크 표기 | `벤치마크 전체 상한가중(10%) +1.88%` | 헤더 | 신규 |
| U8 | 가중 방식 배지 | `ⓦ` / `ⓔ` + 표 하단 범례 1줄 | 순위표 컬럼 헤더 | 신규 |
| U9 | Δ순위 열 헤더의 기준일 | `Δ순위 (4주 전 2026-07-14 대비)` | 순위표 헤더 | 변경 |
| U10 | 복합점수 열 | `복합점수` | 순위표 | 신규 열 |
| U11 | 저신뢰 배지 | `⚠` + 툴팁 | 순위표 셀 | 신규 |
| U12 | 정합성 경고 배지 | `❗` + 툴팁 | 순위표 셀 | 신규 |
| U13 | 정렬 고지 띠 | `ℹ 정렬: RS 평균 ↓ · Rank 열은 …` + `[순위순으로]` | 순위표 상단 | 신규 |
| U14 | 제외 섹터 영역 | `순위 대상 제외 (2)` + 사유·종목수 | 순위표 하단 | 신규 |
| U15 | 상세 패널 진입 버튼 | `[이 섹터 종목 보기 →]` | 상세 패널 우상단 | **신규 (핵심 동선)** |
| U16 | 상세 패널 버블 진입 버튼 | `[버블에서 보기]` | 상동 | 신규 |
| U17 | 상한 적용 표기 | `가중치 상한(10%) 적용 3종목 삼성전자 55.1%→10% …` | 상세 패널 | 신규 |
| U18 | 유효N 표기 | `유효N 24.3` | 상세 패널 헤더 | 신규 |
| U19 | 크기 범례 | `크기 = 거래대금(로그) ○ 120억 ◯ 3,400억 ◯ 8.2조` | 버블 차트 우하단 | 신규 |
| U20 | 섹터 버블 X 기준선 라벨 | `벤치마크: 전체 상한가중 +1.88%` | 섹터 버블 | 신규 |
| U21 | 종목 버블 X 기준선 | `반도체 섹터 평균 −6.59%` | 종목 버블 | 신규 |
| U22 | 미표시 버블 사유 목록 | `미표시 (2) 디스플레이 — 표본 부족(4) …` | 버블 하단 | 신규 |
| U23 | RRG 사분면 라벨 | `Leading (전체 상한가중 대비 강함·개선)` | RRG | 변경 |
| U24 | RRG 기준선 설명 | `기준선 100 = 벤치마크(전체 상한가중)와 동일 성과` | RRG 범례 | 신규 |
| U25 | RRG 궤적 시작 표기 | `벤치마크 (12주 lookback · 궤적 시작 2026-05-16)` | RRG 스파크라인 헤더 | 신규 |
| U26 | Bump 구간 토글 | `구간 8주 / 12주 / 26주` | Bump 툴바 | 신규 |
| U27 | Bump 축 하단 표기 | `12주 (84일) · 정규 격자 canonical-v1` | Bump | 신규 |
| U28 | Stage 분포 바 헤더 | `Stage 분포 — 반도체 164종목` | 종목 탐색 | 변경 |
| U29 | Stage 미분류 세그먼트 | `미5` + 범례 `○ 미분류(SMA40 부족)` | Stage 분포 바 | 신규 |
| U30 | 종목 표 섹터비중 열 | `섹터비중` + `⊤`(상한 적용) | 종목 표 | 신규 열 |
| U31 | 종목 표 기간 3열 | `1W% / 1M% / 3M%` | 종목 표 | **신규 2열** (현행 1M만) |
| U32 | 종목 버블 Stage 테두리 | 흰 실선/없음/회색/점선 + 범례 `테두리 = Stage` | 종목 버블 | 신규 |
| U33 | 빈 상태 안내 | `활성 필터: … [Stage 필터 해제] [시장 전체로] [섹터 스코프 해제]` | 종목 탐색 | 신규 |
| U34 | 기준일 불일치 경고 띠 | `⚠ 패널 간 기준일 불일치 — …` | 화면 상단 | 신규 |
| U35 | 갱신 실패 경고 띠 | `갱신 실패 — 표시 중인 데이터는 {날짜} 기준입니다 [다시 시도]` | 화면 상단 | 신규 |
| ~~U36~~ | ~~산업명(중) 필터~~ | — | — | **삭제** — 구현하지 않는다 (REQ-SUX-054 철회, 2026-08-12 사용자 결정) |
| U37 | 순위 총수 병기 | `7 / 29` (Rank 열 셀 또는 표 헤더) | 순위표 | 신규 (REQ-SUX-055) |
| U38 | 섹터 버블 색상 + 범례 | 기간 수익률 발산형 5단계 + 색상 범례 | 섹터 버블 | 신규 (REQ-SUX-056) |

**제거/숨김되는 요소** (Lesson #2):

| # | 요소 | 조치 |
| --- | --- | --- |
| X1 | Table 툴바의 별도 기간 토글 (`SectorAnalysis.tsx:57`) | 헤더 단일 인스턴스로 **흡수** |
| X2 | Bubble 툴바의 별도 기간·시장 토글 (`BubbleChart.tsx:28-29`) | 상동 **흡수** |
| X3 | 섹터 버블의 `axisPointer` 값 라벨 상자 (`SectorBubbleChart.tsx:71-72`) | **삭제** (VZ-4) |
| X4 | 상세 패널의 `Sub-sector breakdown available in future update` 안내 (`SectorDetailPanel.tsx:197-201`) | **삭제** — 사실과 다름 |
| X5 | `crossTabParams` / `CrossTabParams` 타입 (`types/market.ts:5-8`) | **삭제** → `NavIntent`로 대체 |
| X6 | RRG 축 하드코딩 `min:75, max:125` (`RRGChart.tsx:238,246`) | **삭제** → 자동 대칭 |

**시각 우선순위 (위 → 아래)** (Lesson #2):

```
섹터 분석 탭:
  1. 기준일 + 진행중 배지 + 새로고침        ← 모든 숫자의 전제
  2. 기간·시장 토글 + 벤치마크 값            ← 조회 조건
  3. 서브탭 (Table / Bubble / RRG / Bump)
  4. 본문 (표 / 차트)
  5. 제외 섹터 영역 / 범례                   ← 보조

종목 탐색 탭:
  1. 기준일 + 기간·시장 토글 + 새로고침
  2. 섹터 칩 + 종목 수 + 선택 개수 + View Charts
  3. Stage 분포 바 (섹터 스코프 반영)
  4. 종목 표
```

### 0.4 rollback 시나리오

| 단계 | 안전 commit 경계 | rollback |
| --- | --- | --- |
| M1 (Context 신설, 소비자 0) | 신규 파일만 | 삭제로 무해 |
| M2 (토글 단일화) | 단일 commit | revert 시 2벌 토글 복귀 |
| M3 (NavIntent 교체) | 단일 commit | **`crossTabParams` 삭제와 동일 commit** — 부분 revert 불가. 이 커밋이 전면 rollback 경계다 |
| M4 (전환 규칙) | 화면별 개별 commit | 화면 단위 revert |
| M5 (시각화) | 차트별 개별 commit | 차트 단위 revert |
| M6 (로딩·오류 UX) | 단일 commit | revert 안전 |

**전면 rollback 경계**: M3 직전 commit. `SPEC-CHART-NAV-001`의 선례대로, 라이브 사용 후 폐기 결정이 나면 `feat/SPEC-SECTOR-UX-001` 브랜치를 archive 보존하고 M1 직전으로 checkout한다. **② 백엔드는 rollback 대상이 아니다**(추가 전용 스키마).

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **선행 설계 (Tier L 산출물 대체)**: `docs/sector-ux/02-screen-flow.md`(1,185줄, 설계 확정안 — 상태 소유권 표 §3.3이 계약 본체)와 `01-data-contract.md`(연구·실측). 신규 `design.md`/`research.md`를 작성하지 않는다(SSOT 분기 방지).
- **선행 SPEC**: `SPEC-SECTOR-AGGREGATION-001` — 본 SPEC이 렌더하는 필드 전부를 공급한다. **② close 후 run 착수.**
- **IA 제약**: 5개 상단 탭 + 4개 서브탭 + Stock Explorer 레이아웃을 **그대로 유지**한다. 바뀌는 것은 배선·상태 소유권·컨트롤 의미뿐이다.
- **개발 방법론**: TDD (Vitest + React Testing Library).

### 1.2 보존 대상 [HARD — 되돌리면 회귀]

`02-screen-flow.md` 부록 B "현행 코드에서 이미 올바른 것 (변경 금지)":

| 항목 | 위치 | 이유 |
| --- | --- | --- |
| Bump `connectNulls: false` | `BumpChart.tsx:119` | 순위 제외 주를 선 끊김으로 표현 — 이미 옳다 |
| Bump 날짜 합집합 축 | `BumpChart.tsx:67-73` | 섹터별 길이가 달라도 축 일관 |
| **종목 버블 색상 = 산업명(중)** | `StockBubbleChart.tsx:32-61` | `SPEC-SECTOR-MINOR-COLOR-001`(커밋 `4139ebc`) 출하 계약. `StockBubbleChart.tsx:28` `@MX:ANCHOR`가 결정성 매핑(정렬 키 `count desc, name asc` → `itemStyle.color` + `legend.data` + `tooltip` 3축)을 고정. **색상을 Stage로 재배정 금지** |
| 종목 버블 `기타` 범례 처리 | `StockBubbleChart.tsx:25-26, 54-58, 177-181` | 오버플로·null 흡수 + 범례 생성 — 이미 옳다 |
| RRG/Bump `focus: 'series'` | `RRGChart.tsx:221`, `BumpChart.tsx:99-108` | 선 차트에서 궤적 추적 목적에 적합 |
| `MarketContext` TTL + `refresh()` | `MarketContext.tsx:6, 34, 86-88` | **본 SPEC이 전 엔드포인트로 확산시키는 원본 패턴** |
| `Promise.allSettled` 독립 실패 | `MarketContext.tsx:45-64` | 한 엔드포인트 실패가 다른 패널을 막지 않음 |
| 지수 백오프 (2/4/8초) | `StockExplorer.tsx:10`, `MarketContext.tsx:8` | 본 SPEC이 채택 |
| Stage 세그먼트 토글 해제 | `StageDistributionBar.tsx:34-41` | TR-11이 그대로 유지 |
| tooltip XSS 이스케이프 | `StockBubbleChart.tsx:83-85` | 방어적 코딩 |

### 1.3 현행 결함 (02 §3.1 실측)

ST-1(수신자 없는 브로드캐스트) / ST-2(clear 경쟁) / ST-3(이동 없이 남의 탭 필터 변경) / ST-4(무동작 시장 토글) / ST-5(분포 바 ↔ 표 모집단 불일치) / ST-6(자가 복구 불가) / **ST-7(`stockName` 실제 타입 에러)** / ST-8(종목 버블 클릭 미배선) / FL-1~3(컨트롤 2벌·표기 불일치) / LD-1~7(로딩 결함).

---

## 2. Assumptions (가정, Lesson #5)

- **A1 (사용 패턴)**: 단일 사용자(jw), localhost, 데스크탑 브라우저 주 사용. 팀 공유·링크 공유 요구 없음 → **URL 동기화 미도입**(02 §13 O-4 미결로 유지).
- **A2 (갱신 빈도·freshness)**: 주봉 데이터는 주 1회~수시 수동 갱신. 사용자는 "지금 보고 있는 화면이 어느 날짜 기준인지"를 알고 싶어하며, 자동 폴링은 원하지 않는다.
- **A3 (캐시 모델 — 프로젝트 기존 패턴 인용)**: **TTL 1시간 + 수동 새로고침 버튼**. `MarketContext.tsx:6`의 기존 값을 채택해 전 엔드포인트로 일관화한다. 새로운 캐시 모델을 발명하지 않는다(Lesson #5 — 학습 비용 0). 주봉 데이터는 주 1회 갱신이므로 1시간 TTL은 보수적이고 안전하다.
- **A4**: "세션"은 페이지 새로고침 전까지다. localStorage / URL 영속을 도입하지 않는다 → 새로고침 시 §3.3 초기값으로 복귀.
- **A5 (모바일, Lesson #1)**: 주 사용 환경은 데스크탑이다. hover 기반 정보(툴팁·강조)는 모바일(<768px)에서 **탭(touch)으로 대체**되며, hover-only로만 존재하는 정보를 두지 않는다 — 배지·라벨은 본문에 상설한다.
- **A6**: ②가 추가한 필드는 `null`일 수 있다. 프론트는 모든 신규 필드에 대해 `null` 경로를 렌더할 수 있어야 한다.
- **A7 (default 진입, Lesson #3)**: 종목 탐색의 기본 모드에서 신규 열(1W/3M/섹터비중)과 신규 배지(기준일/진행중)가 **추가 조작 없이 보여야** 한다. lazy-fill이나 별도 모드 뒤에 숨기지 않는다.

---

## 3. Requirements (요구사항, GEARS)

### 3.1 상태 모델

#### REQ-SUX-001 (Ubiquitous) — 분석 파라미터 컨텍스트

The frontend **shall** provide `AnalysisParamsContext` owning `market`, `period`, `asOfDate`(읽기 전용), `asOfIsPartialWeek`(읽기 전용), `gridVersion`(읽기 전용). 초기값 `market='all'`, `period='1m'`. 세션 지속 (규칙 §3.3).

- 검증: AC-SUX-001

#### REQ-SUX-002 (Ubiquitous) — 선택 컨텍스트

The frontend **shall** provide `SelectionContext` owning `selectedSector`(초기 `null`, 사용자 명시 해제 시에만 소멸) and `sectorScopeFollow`(초기 `true`).

- 검증: AC-SUX-002

#### REQ-SUX-003 (Ubiquitous) — 주소 지정 내비게이션 의도

`crossTabParams` **shall** be replaced by `NavIntent = { target: TabId, id: number(단조 증가), payload: { subTab?, stockCodes?, focusStock? } }`. 소비자는 `target === 자기 탭 ID` **and** `id !== lastHandledId` **and** `activeTab === target` 3조건을 모두 만족할 때만 처리한다 (규칙 SM-1, SM-2).

- 검증: AC-SUX-003, AC-SUX-004

#### REQ-SUX-004 (Unwanted Behavior) — 전역 clear 금지

Consumers **shall not** call a global `clearCrossTabParams()`. 소비자는 자신의 `lastHandledId`만 갱신한다 (규칙 SM-3).

- 검증: AC-SUX-005

#### REQ-SUX-005 (Unwanted Behavior) — 섹터명은 의도 페이로드가 아니다

`NavIntent.payload` **shall not** carry `sectorName`. 섹터 선택은 `SelectionContext`에 직접 쓴다 (규칙 SM-4).

- 검증: AC-SUX-006

#### REQ-SUX-006 (Ubiquitous) — 단일 선택 + 스코프 추종

`selectedSector` **shall** be a single app-wide slot (마지막 쓰기 우선). 종목 탐색의 섹터 칩 `×`는 `sectorScopeFollow`만 `false`로 만들고 `selectedSector`는 **유지**한다 (규칙 SM-5, SM-6).

- 검증: AC-SUX-007

#### REQ-SUX-007 (Ubiquitous) — 컨트롤 단일 인스턴스

기간·시장 토글 **shall** exist as a single shared state instance. 화면별 독립 인스턴스를 금지한다. 기간 값 표기는 `'1w' | '1m' | '3m'`으로 단일화한다 (규칙 SM-7, CT-12).

- 검증: AC-SUX-008, AC-SUX-009

#### REQ-SUX-008 (Ubiquitous) — 복귀 시 컨텍스트 보존

When the user returns to a previously visited tab, the app **shall** preserve `selectedSector`, `period`, `market`, `subTab`, `sortField`, `sectorScopeFollow`, `stageFilter`, `selectedStocks`, `visibleSectors`, `windowEnd`, `topFilter` per the §3.3 ownership table (규칙 SM-8). 뒤로 가기 전용 UI를 만들지 않는다.

- 검증: AC-SUX-010

### 3.2 전환 규칙

#### REQ-SUX-009 (When) — 행 클릭은 필터 전용

When the user clicks a ranking table row, the app **shall** set `selectedSector` and expand the detail panel **without** calling `navigate()` (규칙 TR-3). 선택된 행 재클릭 시 `selectedSector = null` + 패널 닫힘 (TR-3b).

- 검증: AC-SUX-011

#### REQ-SUX-010 (When) — 상세 패널의 종목 탐색 진입 [신규 동선]

When the user clicks `[이 섹터 종목 보기 →]`, the app **shall** set `sectorScopeFollow = true`, emit a `NavIntent` targeting `stock-explorer`, and reset `selectedStocks` (규칙 TR-4).

- 검증: AC-SUX-012

#### REQ-SUX-011 (When) — 종목 버블 클릭 배선 [ST-8 해소]

When the user clicks a stock bubble, the app **shall** navigate to 종목 탐색 with `NavIntent.payload.focusStock` and `sectorScopeFollow = true`, resetting `selectedStocks` (규칙 TR-9). 현행은 prop 미연결로 무동작이다.

- 검증: AC-SUX-013

#### REQ-SUX-012 (Ubiquitous) — 트리맵 종목 클릭 타입 에러 수정 [ST-7 해소]

`focusStock` **shall** be a formally typed field of `NavIntent.payload`, and 차트 그리드 **shall** have a consumer for it. `MarketOverview.tsx:46`의 `stockName` 타입 에러(`TS2353`)를 제거한다 (규칙 TR-2).

- 검증: AC-SUX-014

#### REQ-SUX-013 (When) — 종목 체크 초기화 규칙

When the population changes (TR-4, TR-9, TR-12, `selectedSector` 변경), `selectedStocks` **shall** be reset. Stage 필터 변경(TR-10/11)에서는 **초기화하지 않는다** (규칙 TR-16).

- 검증: AC-SUX-015

#### REQ-SUX-014 (When) — 버블 뒤로가기 시 선택 유지

When the user clicks `← 섹터 목록` in the stock bubble view, `selectedSector` **shall** be preserved (현행은 `null`로 지운다) (규칙 TR-6).

- 검증: AC-SUX-016

#### REQ-SUX-015 (When) — RRG/Bump 요소 클릭

When the user clicks an RRG trail or a Bump line, the app **shall** set `selectedSector` and switch `subTab` to `table`, preserving RRG/Bump local state (`visibleSectors`, `windowEnd`, `topFilter`) (규칙 TR-7, TR-8).

- 검증: AC-SUX-017

### 3.3 컨트롤

#### REQ-SUX-016 (Ubiquitous) — 시장 토글의 실동작화

The market toggle **shall** trigger a server refetch changing 집계 유니버스·벤치마크·순위·제외 섹터 목록, applied to Table, Bubble(섹터·종목), RRG, Bump, 종목 탐색 **전부** (규칙 CT-1). 현행은 버튼 활성 CSS만 바꾼다(ST-4).

- 검증: AC-SUX-018

#### REQ-SUX-017 (Where) — 제외 섹터의 가시성

Where a sector is excluded for insufficient sample, the ranking table **shall** show it in a bottom `순위 대상 제외 (N)` area with reason and count. 목록에서 숨기는 것을 금지한다 (규칙 CT-2).

**적용 범위 — 순위표 · 섹터 Bubble · RRG 한정.** Bump는 이 요구의 대상이 **아니다**: AG-5는 Bump에 적용되지 않으므로(O-U9 확정, §7) Bump에는 제외 섹터라는 개념 자체가 없고 전 섹터의 선이 그대로 그려진다. Bump에 제외 영역을 렌더하는 구현은 이 요구의 충족이 아니라 **위반**이다.

- 검증: AC-SUX-019 (Bump 반대 방향 단언 + `mut_bump_applies_ag5` 대조 포함)

#### REQ-SUX-018 (When) — 선택 섹터가 제외 대상이 될 때

When a market-toggle change makes the current `selectedSector` excluded, the app **shall** keep the selection and render `이 시장 필터에서는 표본 부족(n=k)으로 순위 대상에서 제외되었습니다` in the detail panel slot. 조용한 선택 해제를 금지한다 (규칙 CT-3).

- 검증: AC-SUX-020

#### REQ-SUX-019 (Ubiquitous) — Rank 열과 행 순서의 일치

On entry and after any period/market change, the default sort **shall** be `rank` ascending so the Rank column and row order agree (규칙 CT-4). 클라이언트 재정렬로 rank를 재계산하지 않는다.

- 검증: AC-SUX-021

#### REQ-SUX-020 (When) — 다른 열 정렬 시 고지

When the user sorts by a column other than `rank`, the table **shall** render an inline notice stating the Rank column basis and offering a one-click `[순위순으로]` return (규칙 CT-6).

- 검증: AC-SUX-022

#### REQ-SUX-021 (When) — 정렬 리셋

When `period` or `market` changes, `sortField`/`sortDirection` **shall** reset to `rank`/`asc` (규칙 CT-7).

- 검증: AC-SUX-023

#### REQ-SUX-022 (Ubiquitous) — 정렬 시 null 처리

The sort comparator **shall** place `null` values **last** regardless of sort direction. 현행 `getSortValue`(`SectorAnalysis.tsx:32-45`)의 `NaN` 비교를 제거한다.

- 검증: AC-SUX-024

#### REQ-SUX-023 (Ubiquitous) — 순위변동 3상태 구분

`rank_change` **shall** render as `▲n` (>0) / `▼n` (<0) / `–` (==0, muted) / `신규` (null, muted + 툴팁). 열 헤더에 `baseline_date`를 표기한다 (규칙 CT-8, CT-9).

- 검증: AC-SUX-025

#### REQ-SUX-024 (Ubiquitous) — 가중 방식 배지

Return-family columns **shall** carry `ⓦ` and RS-family columns `ⓔ`, with a one-line legend under the table and per-column tooltips (규칙 CT-14). 배지는 **본문 상설**이며 hover-only가 아니다 (A5).

- 검증: AC-SUX-026

#### REQ-SUX-025 (Where) — RRG/Bump에서 기간 토글

Where the active sub-tab is RRG or Bump, the period toggle **shall** render disabled with a tooltip explaining the sub-tab's own time parameter. 숨기지 않는다 (규칙 CT-13).

- 검증: AC-SUX-027
- **주의**: 비활성 vs 숨김은 02 §13 O-3 미결 — §7 O-U1.

#### REQ-SUX-026 (Ubiquitous) — Bump 구간 컨트롤

Bump **shall** expose a `weeks` control with options 8 / 12 / 26 (기본 12) triggering a server refetch, and **shall** display the response's `weeks` and `span_days` under the axis (규칙 §7.2).

- 검증: AC-SUX-028

#### REQ-SUX-027 (Where) — Stage 분포 바의 모집단 일치

Where `sectorScopeFollow === true`, the Stage distribution bar **shall** render the `by_sector[selectedSector]` distribution and its header **shall** name that sector and its count; the segment sum **shall** equal the stock table row count (규칙 CT-10). 서버는 이미 `by_sector`를 내려주며 현행은 소비자가 없을 뿐이다.

- 검증: AC-SUX-029

#### REQ-SUX-028 (Ubiquitous) — 미분류 세그먼트

The Stage distribution bar **shall** render an `미분류` segment so that segment widths sum to 100%, and clicking it **shall** set `stageFilter = 'unclassified'` (규칙 CT-11).

- 검증: AC-SUX-030

#### REQ-SUX-029 (Ubiquitous) — 종목 표 기간 3열 상설

The stock table **shall** always render `1W%`, `1M%`, `3M%` as three permanent columns; the period toggle **shall** change only the default sort key, not the column set (02 §13 O-8 결정).

- 검증: AC-SUX-031, AC-SUX-032 (default 진입 가시성, Lesson #3)

#### REQ-SUX-030 (Ubiquitous) — 종목 표 섹터비중 열

The stock table **shall** render `weight_in_sector` with a `⊤` marker for cap-applied constituents (02 §4.3).

- 검증: AC-SUX-031

#### REQ-SUX-055 (Ubiquitous) — 순위의 총 섹터 수 병기 [설계서 미수용분 해소]

The ranking table **shall** display each sector's `rank` together with the total ranked-sector count in the form `7 / 29`, satisfying `01-data-contract.md §2.9` ("정수. 총 섹터 수 동반 표기(\"7 / 29\")").

`01 §2.9`가 표시 규칙으로 명시했으나 **어느 SPEC도 수용하지 않았다** — ①은 격자 계층이라 무관하고, ②는 값만 공급하며(`rank` 필드는 이미 있다), ③의 이전 판은 U-항목을 만들지 않았다. 순수 표시 요구이므로 ③ 소관이다.

- 분모는 **순위 대상 섹터 수**(`excluded[]` 제외 후)이며 전체 29가 아니다. 시장 필터로 제외가 생기면 분모가 줄어든다 — `29`를 상수로 하드코딩하는 것을 금지한다.
- 분모 값은 응답에서 도출한다(`data[]` 중 `rank is not null`인 개수). 프론트가 별도로 세지 않는다.
- 검증: AC-SUX-058

#### REQ-SUX-058 (When) — 종목 표 열 접기 우선순위 [O-U7 결정의 REQ 수용]

When the stock table's 12 columns exceed the available viewport width, the table **shall** hide columns in the fixed order `섹터비중 → Vol배 → 52W고` (3단계), and **shall not** hide `1W%` / `1M%` / `3M%` / `Stage` / `RS` / `Name` at any width (§7 O-U7 결정).

`O-U7`은 §7에서 해결됐고 `AC-SUX-061`이 그 결정을 검사하지만, **그 계약을 소유하는 REQ가 없었다.** REQ가 없으면 §5 traceability 표에 행이 서지 않고, 구현 중 이 AC가 잘려도 §3의 어떤 항목도 반대하지 않는다 — Lesson #3 게이트(기간 3열이 default 진입에서 보이지 않아 그림자 결함이 된 선례)를 정면으로 재현하는 경로다. 열 접기는 순수 표시 규약이므로 §3.3 컨트롤 소관이며, 표 열 구성을 정의하는 REQ-SUX-029(기간 3열 상설) / REQ-SUX-030(섹터비중 열)과 같은 절에 둔다.

- **접지 않는 6열은 REQ-SUX-029의 연장이다** — "기간 3열을 상설한다"는 요구는 좁은 폭에서 그 3열이 사라지면 무효가 된다. 폭 조건까지 포함해야 REQ-SUX-029가 완결된다.
- 숨겨진 열의 값은 **행 확장 또는 툴팁으로 접근 가능**해야 한다(정보 소실 금지, A5 모바일).
- 3열을 전부 숨긴 뒤에도 넘치면 **가로 스크롤**로 처리하고 추가로 열을 숨기지 않는다.
- 접기 순서는 **단일 위치의 상수 배열**로 정의한다 — 컴포넌트마다 순서를 다시 적으면 발산한다.
- 검증: AC-SUX-061

### 3.4 로딩·갱신

#### REQ-SUX-031 (Ubiquitous) — 쿼리 키와 조회 시점

All sector queries **shall** be keyed by `(endpoint, market, period, asOfDate?, 화면별 파라미터)`. 비활성 탭은 fetch하지 않으며, 탭/서브탭 활성화 시 캐시 미스 또는 TTL 만료면 fetch한다 (규칙 LD-A).

- 검증: AC-SUX-033

#### REQ-SUX-032 (Ubiquitous) — TTL

Cache TTL **shall** be 1 hour for all endpoints, adopting `MarketContext.tsx:6`'s existing value (규칙 LD-B, A3).

- 검증: AC-SUX-034

#### REQ-SUX-033 (While) — 재조회 중 기존 데이터 유지

While a refetch is in flight and previous data exists, the screen **shall** keep rendering the previous data with a spinner next to the 기준일 배지. 화면을 비우거나 차트를 언마운트하는 것을 금지한다 (규칙 LD-C).

- 검증: AC-SUX-035

#### REQ-SUX-034 (When) — 재시도와 수동 새로고침

Automatic retry **shall** use exponential backoff (2/4/8s) uniformly, stop after 3 failures, and expose a manual `[다시 시도]`. A `⟳ 새로고침` button **shall** be permanently available next to the 기준일 배지 (규칙 LD-D).

- 검증: AC-SUX-036

#### REQ-SUX-035 (When) — 기준일 합치 검증 [프론트가 검증자]

When simultaneously visible panels report differing `as_of_date`, the app **shall** display a top warning band naming each panel's date with a `[새로고침]` action. When `grid_version` differs from the cached value, the app **shall** invalidate all caches and refetch. 기준일 배지는 항상 **서버 응답 값**을 표시하며 프론트가 날짜를 계산하지 않는다 (규칙 LD-E1~E4).

The 기준일 배지 **shall** be permanently visible at the top of every 섹터 관련 화면 (섹터 분석 4개 서브탭 + 종목 탐색), and where `as_of_is_partial_week` is true it **shall** render the 진행 중 표기 alongside it (`01-data-contract.md §7.1 SN-4`). 배지를 접거나 hover 뒤에 숨기지 않는다 (A5).

- 검증: AC-SUX-037 (불변식 **SN-3** 클라이언트 검증)

### 3.5 시각화

#### REQ-SUX-036 (Ubiquitous) — 버블 크기 면적 비례 + 로그 정규화

Bubble size **shall** be computed as `u = (ln(v+1) − ln(v_min+1))/(ln(v_max+1) − ln(v_min+1))`, `r = sqrt(r_min² + u×(r_max² − r_min²))`, `symbolSize = 2r`. 섹터 버블 `r_min=7, r_max=34`; 종목 버블 `r_min=5, r_max=26`. `v_max == v_min`이면 `u = 0.5` (규칙 VZ-1).

- 검증: AC-SUX-038

#### REQ-SUX-037 (Ubiquitous) — 크기 범례 의무

Where the size channel uses log scaling, the chart **shall** render a size legend with three reference bubbles (최소·중앙값·최대) and their actual values. 범례 없이 크기 채널을 발행하는 것을 금지한다 (규칙 VZ-2).

- 검증: AC-SUX-039

#### REQ-SUX-038 (When) — 결측 거래대금

When `trading_value` is null, the bubble **shall** render at minimum size with a dashed border and a tooltip stating `거래대금 데이터 없음`. 0 치환을 금지한다 (규칙 VZ-3).

- 검증: AC-SUX-040

#### REQ-SUX-039 (Unwanted Behavior) — 떠도는 값 라벨 제거

`SectorBubbleChart`의 `xAxis.axisPointer` 블록 **shall** be deleted. 참조선은 기존 `markLine`이 담당한다 (규칙 VZ-4).

- 검증: AC-SUX-041

#### REQ-SUX-040 (Ubiquitous) — 기준선의 의미 표기

섹터 버블 X=0 markLine **shall** carry the benchmark label with its actual value; 종목 버블 X 기준선 **shall** be the sector aggregate return with a label, with the 0 line kept as a fainter auxiliary line (규칙 VZ-5).

- 검증: AC-SUX-042

#### REQ-SUX-041 (Ubiquitous) — 축 범위

Axis ranges **shall** auto-fit the data while always including 0 (또는 기준선). X축 라벨은 부호 표기(`+1.5%`), Y축(RS)은 0–100 고정 (규칙 VZ-6).

- 검증: AC-SUX-043

#### REQ-SUX-042 (Ubiquitous) — RRG 사분면 의미 표기

Quadrant labels **shall** include the benchmark-relative meaning, and the legend area **shall** carry the permanent line `기준선 100 = 벤치마크(전체 상한가중)와 동일 성과` (규칙 VZ-7).

- 검증: AC-SUX-044

#### REQ-SUX-043 (Ubiquitous) — RRG 축 자동 대칭

RRG axis range **shall** be `half = max(5, ceil(max(|v − 100|)) × 1.1)`, `min = 100 − half`, `max = 100 + half`. `min:75, max:125` 하드코딩을 삭제한다 (규칙 VZ-8).

- 검증: AC-SUX-045

#### REQ-SUX-044 (Ubiquitous) — RRG 궤적 시작·벤치마크 추종

The sparkline header **shall** display `trail_start_date` and `lookback_weeks`, and the sparkline series and label **shall** follow the market filter (All → 전체 상한가중, KOSPI → KOSPI, KOSDAQ → KOSDAQ). KOSPI 고정을 제거한다 (규칙 VZ-9, VZ-10).

- 검증: AC-SUX-046

#### REQ-SUX-045 (Ubiquitous) — 종목 버블 Stage 테두리 채널

Stage **shall** be encoded on the border channel: Stage 2 = 흰색 2px 실선, Stage 1/3 = 없음, Stage 4 = 어두운 회색 1px, 분류 불가 = 회색 1px 점선. **색상 채널은 산업명(중)을 유지**한다 (규칙 VZ-0).

- 검증: AC-SUX-047, AC-SUX-048 (색상 채널 회귀 금지)

#### REQ-SUX-046 (Ubiquitous) — 다크 배경 대비

The stock-bubble categorical palette **shall** satisfy a luminance contrast ratio >= 3:1 against `#1a1a2e`, verified by measurement (규칙 VZ-11).

- 검증: AC-SUX-049

#### REQ-SUX-047 (Ubiquitous) — 기타 범례 개수 병기

The `기타` legend item **shall** display its constituent industry count (`기타 (7개 산업)`) (규칙 VZ-12 신규분).

- 검증: AC-SUX-050

#### REQ-SUX-048 (When) — hover 강조 범위 완화

When hovering an individual stock bubble, only that bubble **shall** be emphasized (`focus: 'none'`); when hovering a legend item, that group **shall** be emphasized with the rest blurred (`focus: 'series'`). RRG/Bump의 `focus: 'series'`는 **유지**한다 (규칙 VZ-13).

- 검증: AC-SUX-051

#### REQ-SUX-056 (Ubiquitous) — 섹터 버블 색상 채널 [설계서 미수용분 해소]

The sector bubble **shall** encode 기간 수익률 on the color channel as a diverging 5-step scale, with a color legend, per `02-screen-flow.md §9.1`.

`02 §9.1`의 시각 채널 표가 섹터 버블의 색을 "기간 수익률 (발산형 5단계)"로 배정했으나 **①·②·③ 어디에도 언급이 없었다.** 종목 버블의 색상 채널(산업명(중))만 계약으로 다뤄지면서 섹터 버블 쪽이 누락됐다.

- 발산 기준점은 **0%**(수익률 부호)이며 벤치마크 값이 아니다 — X축이 이미 초과수익률(벤치마크 기준)이므로 색까지 벤치마크 기준이면 두 채널이 같은 변수를 인코딩한다(VZ-0 위반).
- 5단계 경계값은 상수로 단일 위치에 정의하고 **범례에 실제 구간 값을 표기**한다. 크기 범례(REQ-SUX-037)와 같은 이유다 — 범례 없는 연속 채널은 읽을 수 없다.
- **종목 버블의 색상 채널(산업명(중))에는 어떤 영향도 주지 않는다** — 별개 차트이며 §4 Exclusions의 보존 계약과 무관하다.
- 검증: AC-SUX-059

#### REQ-SUX-057 (Ubiquitous) — 버블 테두리 채널 단일화 [VZ-0 충돌 해소]

Border channel usage **shall** be exactly one variable per chart, per the amended `02-screen-flow.md §9.1` 테두리 채널 단일화:

| 차트 | 테두리 채널 소유자 | 결측 거래대금 표현 | 저커버리지 표현 |
| --- | --- | --- | --- |
| 섹터 버블 | **결측 거래대금**(점선) | 최소 크기 + 점선 테두리 | 툴팁 `⚠` + 하단 저신뢰 요약 (테두리 미사용) |
| 종목 버블 | **Stage** | 최소 크기 + 툴팁 문구만 (**테두리 불변**) | 툴팁 `⚠` + 하단 저신뢰 요약 (테두리 미사용) |

설계 문서 내부에 **네 주장자**가 있었다: `02 §9.1`(섹터 버블 = 표본부족/저커버리지), `02 §9.2 VZ-3` + `01 §8.2`(결측 거래대금 = 점선), `02 §10.2`(커버리지 미달 = 점선), `02 §9.1` + `01 §8.7`(종목 버블 = Stage). VZ-0(채널 중복 금지)을 설계서가 스스로 위반하고 있었으며, 두 설계 문서를 개정해 해소했다.

- **종목 버블에서 Stage가 테두리를 독점한다** — `SPEC-SECTOR-MINOR-COLOR-001` 출하 계약과 짝을 이루는 `01 §8.7` 확정이며, 결측 거래대금이 테두리를 점선으로 바꾸면 `stage === null`(회색 1px 점선, REQ-SUX-045)과 **구분 불가**해진다. 이것이 종목 버블에서 결측 거래대금의 점선을 포기하는 결정적 이유다.
- 저커버리지의 버블 위 시각 인코딩은 **미결**(`02 §13 O-11`, §7 O-U8) — 투명도는 RRG 궤적 진행도가 이미 쓰고 있어 전 차트 일관 배정이 어렵다.
- 검증: AC-SUX-040(개정), AC-SUX-047, AC-SUX-060

### 3.6 오류·빈 상태

#### REQ-SUX-049 (Ubiquitous) — 셀 수준 5상태 표현

Cells **shall** render: 데이터 없음 → `–` (muted), 실제 0 → `0.00%`, 계산 불가 → `계산 불가` (muted italic + 사유 툴팁), 저신뢰 → 값 + `⚠`, 정합성 경고 → 값 + `❗`. 전 화면에서 동일 표현을 쓴다 (규칙 ER-1).

- 검증: AC-SUX-052

#### REQ-SUX-050 (Unwanted Behavior) — 결측의 0/50.0 렌더 금지

Formatters **shall not** render `0` / `0.0%` / `50.0` / `NaN%` for missing values. `SectorRankingTable.tsx:39-42`의 무조건 `toFixed(1)` 앞에 상태 분기를 둔다 (규칙 ER-2).

- 검증: AC-SUX-053

#### REQ-SUX-051 (Ubiquitous) — 빈 상태는 원인을 말한다

Empty states **shall** display the active filters and offer one-click release actions (규칙 ER-3).

- 검증: AC-SUX-054

#### REQ-SUX-052 (Ubiquitous) — 섹터 상세 오류 표시

`SectorDetailPanel` **shall** surface fetch errors instead of swallowing them (`.catch(() => {})`), and the false `Sub-sector breakdown available in future update` notice **shall** be removed (규칙 §10.2, LD-7).

- 검증: AC-SUX-055

#### REQ-SUX-053 (Ubiquitous) — 회귀 방지: 기대되는 변화

The regression suite **shall** assert as expected: (a) 기간 변경 시 로딩 인디케이터가 나타남, (b) 비-rank 정렬 시 고지 띠가 나타남, (c) 버블 크기 분포가 바뀜, (d) RRG 궤적이 짧아짐, (e) KOSPI 필터 시 제외 섹터 영역이 나타남.

- 검증: AC-SUX-056

---

### 3.7 철회된 요구사항 (묘비)

> 번호를 재사용하지 않고 철회 사실을 남긴다. 이전 판은 철회된 `REQ-SUX-054`가 `REQ-SUX-030` 바로 뒤(§3.3 컨트롤)에 그대로 끼어 있었다. 철회분은 이 절에 모으고, 신규 요구사항(REQ-SUX-055/056/057/058)은 각자 도메인 절(§3.3 컨트롤 / §3.5 시각화)에 배치했다.
>
> **§3의 REQ 번호는 오름차순이 아니다 — 의도된 상태다.** `REQ-SUX-055`·`058`은 §3.3에서 `030`과 `031` 사이에, `056`·`057`은 §3.5에서 `048`과 `049` 사이에 놓인다. **배치 기준은 번호가 아니라 주제**이며, 번호순 재배열은 하지 않는다 — 주제 응집을 깨뜨리는 대가로 얻는 것이 정렬뿐이다. 번호는 발행 순서(이력)를, 절은 도메인을 나타내며 둘은 독립이다. 누락 검출은 §5 traceability 표(REQ 단위 전개)가 담당한다.

#### ~~REQ-SUX-054~~ — 종목 목록의 산업명(중) 필터 **[철회 — 구현하지 않는다]**

**결정 (2026-08-12, 사용자): 필터를 구현하지 않고 계약을 구현에 맞춰 좁힌다.** 이전 판은 반대 방향(계약에 맞춰 필터를 구현)을 택했으나 뒤집혔다.

- **조치**: `01-data-contract.md §8.5`의 전송 필터 목록에서 **`sector_minor`를 제거**해 문서가 구현과 일치하게 한다(개정 완료). `frontend/src/components/StockExplorer/StockTable.tsx:86`의 `sector_major`-only 술어는 **그대로 둔다** — 결함이 아니라 계약의 현재 상태다.
- **중분류 드릴다운은 종목 버블에 이미 존재한다** — 색상 채널 + 범례(`SPEC-SECTOR-MINOR-COLOR-001`, `StockBubbleChart.tsx:32-61`). 종목 표의 중분류 필터는 그것의 필수 대응물이 아니다.
- **후속 과제로 유보**: `01 §10 O-9`로 등록. 도입하려면 "161개 중 현재 섹터 스코프 내부로 선택지를 좁히는" UI 규약이 필요하며 그 설계는 본 SPEC 범위 밖이다.
- **`sector_minor` 필드 자체는 계속 소비한다** — ②의 REQ-SAG-039가 응답에 싣고 ③은 종목 버블 색상 매핑·툴팁에 쓴다. **필터 술어로만 쓰지 않는다.**
- **중분류 단위 집계**(중분류 순위·RRG·전용 서브탭)는 변함없이 범위 밖이다 — `01 §10 O-6` = `02 §13 O-7` = ②의 `O-A2`로 미결 유지.
- **철회에 따라 함께 삭제되는 산출물**: U36(§0.3), AC-SUX-057(결번), plan.md M4의 `StockTable.tsx:86` 필터 술어 수정 + 툴바 컨트롤 항목.

---

## 4. Exclusions (What NOT to Build)

### Out of Scope — 백엔드

- 격자·유니버스·집계·벤치마크·순위·RRG 지수·응답 스키마: 전부 **①/②** 소관. ③은 소비만 한다.
- 신규 API 엔드포인트 요청: 없음. ②가 제공하는 필드만 렌더한다.

### Out of Scope — IA·기능 확장

- **관심 섹터 워치리스트 / 핀 / 즐겨찾기**: 섹터 단위 핀 어포던스를 설계하지 않는다. `SelectionContext`에 핀 필드를 추가하지 않는다. (종목 단위 `WatchlistContext`는 기존대로 유지 — 키 공간 비충돌.)
- **URL 동기화**: 도입하지 않는다 (A1, 02 §13 O-4 → §7 O-U2).
- **localStorage 영속**: 도입하지 않는다.
- **신규 화면·신규 탭·신규 서브탭**: 없음. 5탭 + 4서브탭 유지.
- **섹터 2개 동시 비교(분할 뷰)**: 지원하지 않는다 (02 §13 O-5 → §7 O-U3).
- **중분류 단위 집계 (순위/RRG/전용 서브탭)**: 없음 — `01 §10 O-6` = `02 §13 O-7` = ②의 `O-A2`로 미결 유지.
- **종목 목록의 `sector_minor` 필터**: **범위 밖**(REQ-SUX-054 철회, §3.7). `01 §8.5`의 전송 필터에서 `sector_minor`를 제거해 계약을 구현에 맞췄다. 중분류 드릴다운은 종목 버블에만 존재한다. 후속 과제는 `01 §10 O-9`.
- **Chart Grid / Theme Analysis 내부 동작**: 진입 계약(`focusStock`, `stockCodes` 소비)만 규정하고 내부는 건드리지 않는다.

### Out of Scope — 시각 채널

- **종목 버블 색상 채널의 Stage 재배정**: **금지**. `SPEC-SECTOR-MINOR-COLOR-001` 되돌림이자 `StockBubbleChart.tsx:28` `@MX:ANCHOR` 위반이다.
- 색상 팔레트의 사용자 커스터마이즈 / 라이트 테마: 없음.
- 지수 레벨·지수 High/Low 표시: **금지**(01 O-4 결정 — 교차검증 불가).

### Out of Scope — 상태 라이브러리

- 외부 상태 라이브러리(Redux, Zustand, Jotai 등) 도입: 하지 않는다. React Context + `useState`로 §3.3 소유권 표를 만족한다.

---

## 5. Specifications (수용 기준 연결)

### Traceability (REQ ↔ AC) — **REQ 단위**

> 이전 판은 REQ **그룹** 단위(`SUX-036 ~ 048` → `AC-SUX-038 ~ 051`)로만 매핑해, 특정 REQ에 대응 AC가 없어도 표에서 드러나지 않았다. REQ 단위로 전개한다.

| REQ | AC | 비고 |
| --- | --- | --- |
| REQ-SUX-001 | AC-SUX-001 | |
| REQ-SUX-002 | AC-SUX-002 | |
| REQ-SUX-003 | AC-SUX-003, AC-SUX-004 | |
| REQ-SUX-004 | AC-SUX-005 | |
| REQ-SUX-005 | AC-SUX-006 | |
| REQ-SUX-006 | AC-SUX-007 | |
| REQ-SUX-007 | AC-SUX-008, AC-SUX-009 | |
| REQ-SUX-008 | AC-SUX-010 | |
| REQ-SUX-009 | AC-SUX-011 | |
| REQ-SUX-010 | AC-SUX-012 | |
| REQ-SUX-011 | AC-SUX-013 | |
| REQ-SUX-012 | AC-SUX-014 | AC-SUX-004 (a) HARD 게이트와 동일 대상 |
| REQ-SUX-013 | AC-SUX-015 | |
| REQ-SUX-014 | AC-SUX-016 | |
| REQ-SUX-015 | AC-SUX-017 | |
| REQ-SUX-016 | AC-SUX-018 | |
| REQ-SUX-017 | AC-SUX-019 | 범위 = Table·섹터 Bubble·RRG (**Bump 제외** — O-U9 확정) + Bump 반대 방향 단언 |
| REQ-SUX-018 | AC-SUX-020 | |
| REQ-SUX-019 | AC-SUX-021 | |
| REQ-SUX-020 | AC-SUX-022 | |
| REQ-SUX-021 | AC-SUX-023 | |
| REQ-SUX-022 | AC-SUX-024 | |
| REQ-SUX-023 | AC-SUX-025 | |
| REQ-SUX-024 | AC-SUX-026 | |
| REQ-SUX-025 | AC-SUX-027 | §7 O-U1 (해결됨 — 비활성 채택) |
| REQ-SUX-026 | AC-SUX-028 | |
| REQ-SUX-027 | AC-SUX-029 | |
| REQ-SUX-028 | AC-SUX-030 | |
| REQ-SUX-029 | AC-SUX-031, AC-SUX-032 | |
| REQ-SUX-030 | AC-SUX-031 | |
| REQ-SUX-031 | AC-SUX-033 | |
| REQ-SUX-032 | AC-SUX-034 | |
| REQ-SUX-033 | AC-SUX-035 | |
| REQ-SUX-034 | AC-SUX-036 | |
| REQ-SUX-035 | AC-SUX-037 | |
| REQ-SUX-036 | AC-SUX-038 | |
| REQ-SUX-037 | AC-SUX-039 | §7 O-U4 (해결됨 — 기간별 고정 눈금) |
| REQ-SUX-038 | AC-SUX-040 | REQ-SUX-057로 차트별 분기 |
| REQ-SUX-039 | AC-SUX-041 | |
| REQ-SUX-040 | AC-SUX-042 | |
| REQ-SUX-041 | AC-SUX-043 | |
| REQ-SUX-042 | AC-SUX-044 | ②의 O-A1 결정(JdK 발산 고지) 반영 |
| REQ-SUX-043 | AC-SUX-045 | |
| REQ-SUX-044 | AC-SUX-046 | |
| REQ-SUX-045 | AC-SUX-047, AC-SUX-048 | |
| REQ-SUX-046 | AC-SUX-049 | |
| REQ-SUX-047 | AC-SUX-050 | |
| REQ-SUX-048 | AC-SUX-051 | |
| REQ-SUX-049 | AC-SUX-052 | |
| REQ-SUX-050 | AC-SUX-053 | |
| REQ-SUX-051 | AC-SUX-054 | |
| REQ-SUX-052 | AC-SUX-055 | |
| REQ-SUX-053 | AC-SUX-056 | R5 범위 = Table·섹터 Bubble·RRG (**Bump 제외** — O-U9 확정) |
| ~~REQ-SUX-054~~ | ~~AC-SUX-057~~ | **삭제** — 산업명(중) 필터 미구현 결정 |
| REQ-SUX-055 | AC-SUX-058 | 신규 — `01 §2.9` 총수 병기 |
| REQ-SUX-056 | AC-SUX-059 | 신규 — `02 §9.1` 섹터 버블 색상 |
| REQ-SUX-057 | AC-SUX-040(개정), AC-SUX-047, AC-SUX-060 | 신규 — 테두리 채널 단일화 |
| REQ-SUX-058 | AC-SUX-061 | 신규 — `O-U7` 열 접기 우선순위. **이전 판에서 AC-SUX-061이 고아였다** (정의·E7·DoD·plan.md에는 있으나 소유 REQ 부재) |

**AC 번호 공백**: AC-SUX-057은 REQ-SUX-054 철회로 **결번**이다. 재사용하지 않는다 — 번호를 돌려쓰면 이력 추적이 끊긴다.

**01 부록 B 불변식과의 관계**: ③이 직접 소유하는 불변식은 없다. 다만 **SN-3**(전 패널 `as_of_date` 일치)은 프론트가 검증자이며 AC-SUX-037이 클라이언트 측 검출을 담당하고, **§8.6**(Stage 합계 항등식)은 AC-SUX-029/030이 렌더 측에서 미러 검증한다.

---

## 6. 의존 관계

- **선행**: `SPEC-SECTOR-AGGREGATION-001` close 필요. ②의 필드 없이 U1~U35 대부분이 렌더 불가다.
- **병행 불가 구간**: M4(RRG 범례·축)는 ②의 M4(RRG 지수) ship 이후에만 의미가 있다 — ② RRG를 revert하면 ③ 라벨이 거짓말을 한다(§0.4 rollback 주의).

---

## 7. 미결 사항 (SPEC 레벨 open questions)

| ID | 사항 | 출처 | 결정 필요 사항 |
| --- | --- | --- | --- |
| ~~**O-U1**~~ **해결됨 (잠정)** | RRG/Bump에서 기간 토글을 **비활성으로 남길지 숨길지** | 02 §13 O-3 | **결정 (2026-08-12): 비활성 + 툴팁으로 구현한다** (CT-13 제안 채택). 숨기면 서브탭을 오갈 때 컨트롤이 나타났다 사라져 헤더 레이아웃이 흔들리고, 사용자가 "기간 설정이 사라졌다"고 오인한다. **§0.1 재평가 시점 ③에서 "정보인가 소음인가"를 사용자에게 확인하고, 소음이면 숨김으로 전환하는 amendment로 처리한다** — 잠정 결정이며 구현을 막지 않는다. 검증: AC-SUX-027. |
| **O-U2** | 상태의 URL 동기화 | 02 §13 O-4 | `(tab, subTab, sector, period, market)`을 URL에 반영하면 새로고침 복원·링크 공유·브라우저 뒤로가기가 생긴다. 본 SPEC은 도입하지 않기로 했다. **별도 SPEC으로 다룰 것인가.** |
| **O-U3** | 섹터 선택의 단일성 (SM-5) | 02 §13 O-5 | 사용자가 두 섹터를 나란히 비교하고 싶어할 가능성. 지원하려면 분할 뷰 IA 변경이 필요해 "현행 구조 유지" 제약과 충돌한다. |
| ~~**O-U4**~~ **해결됨** | 크기 범례의 값 산출 | 02 §13 O-9 | **결정 (2026-08-12): 기간별 고정 눈금(per-period fixed ladder).** 데이터 적응형은 필터마다 눈금이 움직여 크기를 기억할 수 없고, 전 기간 공통 단일 눈금은 ②의 O-A4 결정(거래대금 창 = 기간 연동)과 충돌한다 — 3M 누적은 1W보다 자릿수가 커서 대부분 최대 눈금에 클램프된다. 사다리: **1W = 100억 / 1,000억 / 1조**, **1M = 500억 / 5,000억 / 5조**, **3M = 1,000억 / 1조 / 10조**. 범위 밖 값은 최소·최대로 클램프하고 툴팁에 실제 값을 표기한다. 상세 규약은 `02 §9.2 VZ-2` 개정본. 검증: AC-SUX-039. |
| **O-U8** | 버블의 저커버리지 시각 인코딩 | 신규 (REQ-SUX-057 채널 단일화 결과) | 테두리 채널이 차트별로 결측 거래대금(섹터 버블) / Stage(종목 버블)에 배정되면서, 저커버리지는 툴팁 `⚠` + 하단 저신뢰 요약으로만 남았다. 버블 위에 별도 시각 채널을 둘 것인가. 투명도는 RRG 궤적 진행도가 이미 쓰고 있어 전 차트 일관 배정이 어렵다. **후속 과제로 유보** — `02 §13 O-11`과 동일 사안. |
| ~~**O-U9**~~ | ②의 O-A7(최소 구성수 5의 Bump 적용) | **해결 (2026-08-14 사용자 결정)** | **AG-5를 Bump에 적용하지 않는다.** `01 §5.4 AG-5`가 "순위·버블·RRG"만 열거하고 Bump를 뺀 것이 곧 계약이며, ②의 출하 구현도 이미 그렇게 동작한다 — `/sectors/history` → `compute_sector_history` → `compute_sector_ranking` → `_compute_sector_metrics`(`my_chart/analysis/sector_metrics.py:947-948`: *"AG-5 제외는 여기에 적용하지 않는다"*), `get_sector_history`는 `excluded=`를 전달하지 않아 봉투가 항상 빈 배열이다. 따라서 **②의 백엔드 변경 없음**(② `completed` 유지, amendment 불필요). ③ 조치: **AC-SUX-019 / AC-SUX-056 R5의 검증 범위를 Table·섹터 Bubble·RRG로 한정**하고, Bump에는 제외 섹터의 선이 **남아 있어야 한다**는 반대 방향 단언 + `mut_bump_applies_ag5` 대조를 신설(범위에서 빼기만 하면 이후 Bump에 AG-5가 들어와도 어떤 AC도 반대하지 않는다 — Lesson #3 재현 경로). **의도된 귀결**: Bump(전 섹터)와 Table(`data[]`, AG-5 통과분)은 모집단이 달라 같은 섹터의 rank가 두 화면에서 다를 수 있다 — 회귀가 아니다. |
| **O-U5** | 향후 섹터 워치리스트와 `SelectionContext`의 접점 | 02 §13 O-10 | 섹터 워치리스트 도입 시 `SelectionContext`를 확장할 것인가 별도 컨텍스트로 둘 것인가. 지금 결정하면 §3.3 소유권 표가 흔들리므로 **의도적으로 미결**로 둔다. |
| ~~**O-U6**~~ **해결됨** | `focusStock`을 받은 차트 그리드의 구체 동작 | 신규 (설계서 미규정) | **결정 (2026-08-12): (c)+(a) 조합 — 이미 있으면 스크롤·하이라이트, 없으면 추가한다.** **(b) 교체는 채택하지 않는다** — 사용자가 구성해 둔 그리드를 파괴하는 동작이며, 되돌릴 방법이 없다. 상세: 그리드에 `focusStock`이 이미 존재하면 해당 셀로 스크롤 + 일시 하이라이트하고 **중복 추가하지 않는다**; 없으면 그리드 끝에 추가한 뒤 스크롤·하이라이트한다. 그리드가 정원(용량 상한)에 도달했으면 추가하지 않고 안내를 표시한다 — 조용히 다른 종목을 밀어내지 않는다. 검증: AC-SUX-014 확장 + E8. |
| ~~**O-U7**~~ **해결됨** | 와이어프레임과 3열 결정의 불일치 | 신규 (설계서 내부 불일치) | **결정 (2026-08-12): 좁은 화면에서 우선순위 역순으로 접는다 — 섹터비중 → Vol배 → 52W고 순.** 12열(체크박스·Name·Market·섹터비중·Stage·RS·1W·1M·3M·Vol배·52W고·Check)이 좁은 폭에서 넘칠 때 이 순서로 숨긴다. **기간 3열(1W/1M/3M)·Stage·RS·Name은 접지 않는다** — Lesson #3(신규 컬럼이 default 모드에서 안 보여 그림자 결함이 된 선례)의 직접 대상이다. `02 §11.7` 와이어프레임이 `1W%` 한 열만 그린 것은 폭 100자 제약에 따른 축약이며 결정과 충돌하지 않는다. 검증: AC-SUX-061. |
