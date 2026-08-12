---
id: SPEC-MARKET-BREADTH-001
title: "시장 개요 breadth 히스토리 — 정규 주간 격자 적용 및 기간 표기 일치"
version: "0.1.0"
status: draft
created: 2026-08-13
updated: 2026-08-13
author: manager-spec
priority: P1
phase: "market-overview v1"
module: "my_chart/analysis/market_breadth.py, backend/services/market_service.py, backend/routers/market.py, frontend/src/components/MarketOverview"
lifecycle: spec-anchored
tags: "market-overview, breadth, weekly-grid, shipping-defect, brownfield, sqlite"
tier: S
depends_on: [SPEC-SECTOR-GRID-001]
related_specs: [SPEC-SECTOR-GRID-001]
---

# SPEC-MARKET-BREADTH-001: 시장 개요 breadth 히스토리 — 정규 주간 격자 적용 및 기간 표기 일치

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 0.1.0 | 2026-08-13 | manager-spec | 초기 SPEC. `SPEC-SECTOR-GRID-001` v0.3.0 §7 **O-G6**(현재 출하 중인 사용자 가시 오계산)을 별도 SPEC으로 분리한다. 선행 SPEC이 7개 소비자에서 이미 고친 결함이 `market_breadth.py:472`에만 미수정 상태로 남아 있다. **선행 기록의 수치 정정 포함** — 이전까지 "`weeks=12` → 약 36일"로 기록됐으나 이는 함수 기본값 기준이며, 실제 호출부는 `market_service.py:132`의 `weeks=52` 하나뿐이다(§1.3). 범위는 O-G6 + `weeks` 기간 표기 3중 불일치이며, **O-G7(일봉 기준일)은 범위 밖**(§3.9). |

---

## 1. 문제

### 1.1 배경 — 선행 SPEC이 남긴 단 하나의 미수정 소비자

`SPEC-SECTOR-GRID-001`(v0.3.0, `completed`)은 `my_chart/analysis/weekly_grid.py`에 정규 주간 격자를 세우고 기준일 소비자 7곳을 그 격자로 수렴시켰다. 그 SPEC은 `market_breadth.py`를 **의도적으로 범위 밖**에 두었다 — breadth는 섹터 화면이 아니라 시장 개요 소관이기 때문이다. 그 판정은 "무해하다"가 아니라 "이번에 고치지 않는다"는 **범위 판정**이었으며, 선행 SPEC은 이를 다음 세 곳에 명시적으로 남겼다.

| 위치 | 기록 내용 |
| --- | --- |
| `SPEC-SECTOR-GRID-001/spec.md` §7 **O-G6** | "가설이 아니라 지금 라이브에서 잘못된 숫자를 내는 결함" |
| 동 `progress.md` §Residual-risk | 잔여 위험으로 등재, "별도 SPEC으로 격자 적용이 필요" |
| 동 `acceptance.md` AC-SGR-005 allowlist **L5** | `market_breadth.py` / `SELECT DISTINCT Date FROM stock_prices` / "실행 쿼리 (O-G6 보류)" |

본 SPEC이 그 "별도 SPEC"이다.

### 1.2 결함 표면 — 정확히 한 개의 쿼리

`market_breadth.py`는 492행이며, 기준일 관용구가 걸리는 지점은 두 곳뿐이다. 그중 **한 곳만** 본 SPEC의 대상이다.

| 행 | 쿼리 | 대상 여부 | 사유 |
| --- | --- | --- | --- |
| `:85` | `... WHERE Date = ?` (`_query_stocks_at_date`) | **아니다** | 날짜를 **호출자가 공급**한다. 격자 정합성은 호출자 책임이며, 이 함수는 주어진 날짜의 스냅샷을 계산할 뿐이다. |
| `:472` | `SELECT DISTINCT Date FROM stock_prices WHERE Name NOT IN ('KOSPI','KOSDAQ') ORDER BY Date DESC LIMIT ?` | **그렇다** | **O-G6**. 선행 SPEC `REQ-SGR-005`가 금지한 3종 관용구 중 **I2**(`DISTINCT Date … ORDER BY Date DESC`)에 정확히 해당한다. |

결함 함수는 `compute_breadth_history(db_path, market, weeks=12)` (`:453-492`)이다. 최근 `weeks`개의 **원시 고유 날짜**를 가져온 뒤 각 날짜마다 `compute_breadth`를 호출한다. 주봉 DB에는 다중 날짜 ISO 주가 섞여 있으므로(프로즌 스냅샷 실측 **385 원시 날짜 / 346 ISO 주 / 다중 날짜 주 21개**), N개 원시 행은 N주보다 **짧은** 구간을 덮는다.

### 1.3 실측 — 선행 기록의 수치를 정정한다

선행 SPEC의 O-G6 기술과 그에 파생된 `docs/sector-ux/00-overview.md` §4 범위 밖 행은 이 결함을 **"`weeks=12` → 약 36일"** 로 기록한다. 이 숫자는 함수의 **기본값** 기준이며 **실제 호출부의 값이 아니다.** 유일한 프로덕션 호출부는 다음 한 곳이다.

```
backend/services/market_service.py:131-132
    # Compute breadth history (52 weeks = 1 year)
    history = compute_breadth_history(weekly_db_path, "KOSPI", weeks=52)
```

`weeks=12`는 어떤 프로덕션 경로에서도 사용되지 않는다(테스트 3건만 사용). **따라서 라이브 영향은 12주 차트가 아니라 52주(1년) 차트에 있다.** 본 SPEC은 이 정정된 수치를 아래에 기록해 잘못된 수치의 전파를 끊는다.

프로즌 스냅샷(`tests/fixtures/frozen/weekly-2026-08-12/weekly.db`, `as_of=2026-08-12`)과 라이브(`Output/stock_data_weekly.db`) 실측:

| 구현 | 반환 개수 | 첫 날짜 | 마지막 날짜 | span(일) | 고유 ISO 주 |
| --- | ---: | --- | --- | ---: | ---: |
| **현행(출하 중), 프로즌** | 52 | 2026-03-25 | 2026-08-11 | **139** | **21** |
| 현행(출하 중), 라이브 | 52 | 2026-03-18 | 2026-08-12 | 147 | 22 |
| **올바른 구현, 프로즌** | 52 | 2025-08-14 | 2026-08-07 | **358** | **52** |
| 올바른 구현, 라이브 | 52 | 2025-08-14 | 2026-08-07 | 358 | 52 |

즉 **사용자는 "1년"이라고 이해하는 차트에서 실제로는 약 20주(139일)만 보고 있으며**, 그 52개 점은 균등한 주간 간격이 아니라 다중 날짜 주가 중복 표시된 불균등 축이다.

### 1.4 개수는 판별자가 아니다 [설계상 핵심]

위 표에서 **반환 개수는 현행과 올바른 구현 모두 52로 동일하다.** 이는 본 SPEC의 수용 기준 설계를 지배하는 사실이다 — "포인트 개수가 바뀐다"는 형태의 단언은 **어떤 방향으로도 참이 아니며**, 그런 단언을 쓰면 결함을 전혀 잡지 못한다. 판별자는 **날짜 집합(첫 날짜 / 마지막 날짜 / span / 고유 ISO 주 수)** 이다(§3.1).

### 1.5 같은 파일이 절반만 전환되어 있다

`market_service.py`는 이미 격자를 **일부** 쓴다.

```
:16   from my_chart.analysis.weekly_grid import _get_latest_valid_date
:35   return _get_latest_valid_date(db_path)     # ← 선행 SPEC M5에서 전환됨
:132  history = compute_breadth_history(..., weeks=52)   # ← 원시 행 기반, 미전환
```

한 모듈이 **기준일은 정규 격자에서 해석하면서 히스토리는 원시 행에서 유도한다.** 두 축이 서로 다른 시간 규약을 쓰는 내부 모순이며, 본 SPEC이 이를 해소한다.

### 1.6 기간 표기 3중 불일치

`weeks`의 값과 사용자에게 보이는 기간 문구가 세 곳에서 서로 다르다.

| # | 위치 | 현재 문구/값 | 사용자 가시성 |
| --- | --- | --- | --- |
| P1 | `backend/routers/market.py:20` docstring | `"... and 12-week history."` | 간접(OpenAPI 스키마 설명) |
| P2 | `frontend/src/components/MarketOverview/BreadthChart.tsx:156` | `Market Breadth (12-week)` | **직접 — 차트 제목** |
| P3 | `backend/services/market_service.py:131-132` | 주석 `52 weeks = 1 year` + `weeks=52` | 없음(코드) |

**판정: P3(=52)이 정본이고 P1·P2가 낡았다.** 근거는 두 가지다 — (a) P3의 주석 `52 weeks = 1 year`는 값과 의도가 함께 적힌 **의도적 기술**인 반면 P1·P2는 값 없이 문구만 남아 있고, (b) 52 → 12로 되돌리면 이미 출하된 정보량이 축소된다(회귀). 따라서 **P1·P2를 52주(1년)로 맞춘다**(REQ-MBR-005). 되돌림 경로는 §5에 기록한다.

---

## 2. 요구사항 (GEARS)

### REQ-MBR-001 — 히스토리 날짜의 출처를 정규 격자로 [핵심]

**When** `compute_breadth_history(db_path, market, weeks=N)`이 호출되면, **함수는** 대상 날짜 집합을 `my_chart.analysis.weekly_grid`의 정규 주간 격자 히스토리 뷰에서 유도해야 한다(`shall`).

- 기존 자산을 **재사용한다**: `compute_weekly_grid(weekly_db_path, as_of=None)` → `history(grid, weeks)`. 새 날짜 해석 헬퍼를 만들지 않는다.
- **The function shall not** `stock_prices`에 대해 자체 `SELECT DISTINCT Date … ORDER BY Date DESC LIMIT ?` 쿼리를 수행한다(선행 `REQ-SGR-005` 금지 관용구 I2).
- `:85` `_query_stocks_at_date`의 `WHERE Date = ?`는 **변경 대상이 아니다**(§1.2).

### REQ-MBR-002 — `weeks=N`의 의미 (선행 `AC-SGR-008` 상속)

**When** `weeks=N`으로 호출되면, **함수는** 서로 다른 N개 ISO 주의 대표 바를 반환해야 한다(`shall`); 첫 날짜와 마지막 날짜의 간격은 `7×(N−1) ± 7`일이어야 한다.

- 이 정의는 선행 SPEC `AC-SGR-008`(불변식 TG-4)에서 **상속**한다. 병행 정의를 새로 만들지 않는다.
- N=52 적용 시: 기대 span = `7×51 ± 7` = **357 ± 7일**(350–364). 프로즌 실측 **358일**이 이 구간 안에 든다.
- 선행 SPEC은 `AC-SGR-007`에서 `364일 = 52±1 바`를 별도 앵커 불변식(TG-1)으로 고정한다. 본 SPEC은 그 앵커 계약을 **재정의하지 않으며**, `history(weeks=52)`가 `(t−364d, t]` 창과 일치함을 §3.4에서 참조 확인만 한다(프로즌 실측: 창 내 바 52개, 2025-08-14 ~ 2026-08-07 — `history(52)`와 동일).

### REQ-MBR-003 — 진행 중인 주 배제 (CG-2 상속)

**While** 최신 ISO 주가 진행 중이면(`WeeklyGrid.latest.is_partial_week == True`), **함수는** 그 주의 바를 반환 집합에서 제외해야 한다(`shall`).

- 근거: breadth 히스토리는 **추세 판독용**이며, 현재 주의 breadth는 같은 화면에서 단일 값 지표로 이미 별도 표시된다. 미완성 주가 히스토리 끝에 섞이면 마지막 점이 체계적으로 낮은 거래일 수 위에서 계산돼 추세를 왜곡한다.
- 구현상 이는 `grid.history`(=`history()`의 원천)를 쓰면 자동으로 성립한다. **`grid.dates`를 쓰면 성립하지 않는다** — 이 구분이 §3.2의 판별 대상이다.
- 진행 중인 주를 포함하는 배지/토글 변형은 만들지 않는다.

### REQ-MBR-004 — 이력 부족의 비침묵 공개

**When** 가용 격자 이력이 N주 미만이면, **함수는** 가용한 만큼만 반환하되 요청값 N과 실제 반환 개수를 함께 담은 `WARNING` 로그를 남겨야 한다(`shall`).

- 선행 `AC-SGR-008` 3항("조용한 축소 금지")의 상속이다. 선행은 `HistorySlice.requested_weeks/returned_weeks`로 이를 노출했으나, `compute_breadth_history`의 반환 타입은 `list[BreadthResult]`이며 **이 타입은 소비자 계약이므로 바꾸지 않는다**(§4). 따라서 공개 채널은 로그다.
- **The function shall not** 요청보다 적게 반환하면서 아무 신호도 남기지 않는다.

### REQ-MBR-005 — 기간 표기 일치

**The system shall** 사용자에게 보이는 breadth 히스토리 기간 문구를 실제 호출부의 `weeks` 인자와 일치시킨다.

- §1.6 판정에 따라 P1(`routers/market.py:20` docstring)과 P2(`BreadthChart.tsx:156` 차트 제목)를 **52주(1년)** 기준으로 정정한다.
- P3(`market_service.py` 호출부 `weeks=52`)는 **변경하지 않는다** — 정본이다.
- **The system shall not** 세 표면 중 어느 하나만 갱신한 상태로 남긴다.

### REQ-MBR-006 — 금지 관용구 재도입 차단 및 선행 allowlist 정리

**Where** 정적 스캔이 수행되면, **`market_breadth.py`는** 선행 `REQ-SGR-005` 금지 관용구 I1/I2/I3 중 어느 것도 포함하지 않아야 한다(`shall`).

- 결과적으로 선행 SPEC `AC-SGR-005` allowlist의 **L5 항목이 공허해지고 상한 5가 4로 축소된다.** 이는 완료된 SPEC의 `acceptance.md` 본문 변경(in-place amendment)을 요구하는 **교차 SPEC 결합**이며, run 단계에서 별도 취급한다(plan.md M5, 위험 R2).
- 본 plan 단계에서는 선행 SPEC의 어떤 산출물도 수정하지 않는다.

---

## 3. 수용 기준 (Tier S — 인라인)

### 3.0 반증력 규약 [HARD — 본 SPEC의 최우선 품질 기준]

선행 SPEC은 plan 단계에서 항진명제 AC 4건을 잡아 고쳤고, 그럼에도 **테스트 작성 단계에서 같은 실패 양식이 3건 재발**했다(`sync-audit-SPEC-SECTOR-GRID-001-20260812.md`, spec.md v0.3.0). 본 SPEC은 그 실패 양식을 아래와 같이 명시적으로 금지한다.

**금지 형태 (아래에 해당하는 단언은 수용 기준으로 인정하지 않는다)**

| 코드 | 금지 형태 | 왜 공허한가 |
| --- | --- | --- |
| F1 | 테스트 안에서 **바이트 동일한 두 표현**을 비교 | 좌우변이 같은 계산에서 나오므로 항상 참 |
| F2 | 구현이 호출하는 **같은 헬퍼를 테스트가 호출해 자기 자신과 비교** | 구현을 통째로 되돌려도 좌우변이 함께 움직여 통과. 본 SPEC에서는 `history(compute_weekly_grid(db), 52)`와 `compute_breadth_history(db, ..., 52)`의 날짜 비교가 정확히 이 형태다 — **주 단언으로 금지**하며, 프로즌 리터럴을 쓴다 |
| F3 | **부분집합 크기 부등식**(`len(subset) <= len(superset)`) | 선별 관계에서 구조적으로 참. 기존 테스트 `test_history_length_matches_weeks_param`(`assert len(results) <= 4`)이 이 형태다 |
| F4 | **개수만** 단언 | §1.4 — 현행/올바른/CG-2 누락 세 구현 모두 52를 반환한다 |

**각 AC는 (a) 실행 가능한 검사, (b) 기대값, (c) 이 AC가 실패시키는 구체적 잘못된 구현을 모두 명시한다.** "코드가 틀리면 실패한다" 수준의 대조 진술은 인정하지 않는다.

**판별 대상 변형 (프로즌 실측 리터럴 — 전부 실제로 측정한 값이다)**

| 변형 | 설명 | n | 첫 날짜 | 마지막 날짜 | span |
| --- | --- | ---: | --- | --- | ---: |
| **V★** | **올바른 구현** — `history(grid, 52)` | 52 | 2025-08-14 | 2026-08-07 | **358** |
| V0 | 현행 출하 구현 — 원시 `DISTINCT Date LIMIT 52` | 52 | 2026-03-25 | 2026-08-11 | 139 |
| V1 | CG-1은 적용, **CG-2 누락** — `grid.dates[-52:]` | 52 | 2025-08-22 | **2026-08-11** | 354 |
| V2 | 마지막 바를 한 번 더 잘라내는 off-by-one | 51 | 2025-08-14 | 2026-07-31 | 351 |
| V3 | `history(grid, 51)` 오배선 | 51 | 2025-08-22 | 2026-08-07 | 350 |

### AC-MBR-001 — 히스토리 날짜 경계 (프로즌 리터럴 3중 고정) [핵심 게이트]

- **Given** 프로즌 스냅샷 `tests/fixtures/frozen/weekly-2026-08-12/weekly.db` (`as_of='2026-08-12'`)에서
- **When** `compute_breadth_history(frozen_weekly_db, "KOSPI", weeks=52)`를 호출하면
- **Then** 반환된 `BreadthResult.date` 리스트에 대해 **세 리터럴이 동시에** 성립한다:
  - `dates[0] == "2025-08-14"`
  - `dates[-1] == "2026-08-07"`
  - `(date(dates[-1]) - date(dates[0])).days == 358`
- **And** 세 값은 **프로즌 리터럴**이며 어떤 헬퍼 호출 결과와도 비교하지 않는다(F2 금지).
- **잡는 잘못된 구현**: V0(139일·2026-03-25 시작), V1(2026-08-11 종료·354일), V2(351일), V3(350일). **네 변형 모두 세 리터럴 중 최소 둘을 위반한다.**
- **항진명제가 아닌 근거**: 우변이 전부 정수/문자열 리터럴이므로 좌변이 어떤 함수에서 나오든 좌우변이 함께 움직일 수 없다.

### AC-MBR-002 — 진행 중인 주 배제 (CG-2, V1 전용 판별) [HARD]

- **Given** 동일 프로즌 스냅샷에서 (진행 중인 주 = **W33 = 2026-08-11**, `is_partial_week=True`, 거래일 2일 — `MANIFEST.md` 실측)
- **When** 위와 동일 호출을 하면
- **Then** `"2026-08-11" not in dates`이다.
- **And** 반환된 마지막 날짜의 ISO 주가 `(2026, 33)`이 **아니다**.
- **잡는 잘못된 구현**: **V1 전용.** V1은 CG-1(ISO 주당 1바)을 올바로 적용하므로 AC-MBR-003의 "고유 ISO 주 52"를 **통과한다.** V1을 실패시키는 것은 이 AC의 마지막-날짜 단언뿐이다.
- **항진명제가 아닌 근거**: `2026-08-11`은 프로즌 DB에 **실재하는 원시 날짜**이며(33행 보유), 격자 규칙을 적용하지 않으면 반드시 반환 집합에 들어온다. 존재하지 않는 날짜의 부재를 단언하는 것이 아니다.

### AC-MBR-003 — ISO 주 고유성 (V0 전용 판별)

- **Given** 동일 프로즌 스냅샷에서
- **When** 위와 동일 호출을 하면
- **Then** `len({isocalendar(d)[:2] for d in dates}) == 52`이고 `len(dates) == 52`이다 — **즉 날짜 하나당 ISO 주 하나로 1:1이다.**
- **잡는 잘못된 구현**: **V0 전용.** V0은 52개 날짜를 반환하지만 고유 ISO 주는 **21개**다(다중 날짜 주 중복). 개수 단언만으로는 V0을 잡지 못하므로(§1.4, F4) 고유 주 수가 실제 판별자다.
- **항진명제가 아닌 근거**: 두 값이 같아지는 것은 "다중 날짜 주가 중복 반환되지 않는다"는 실질적 성질이며, 프로즌 DB에 다중 날짜 주가 **21개 실재**하므로 반증 가능하다.

### AC-MBR-004 — 앵커 창 정합 참조 (선행 TG-1 재확인, 비게이팅)

- **Given** 프로즌 스냅샷에서 `t = dates[-1]`일 때
- **When** `(t − 364d, t]` 구간의 `grid.history` 바를 세면
- **Then** 그 집합이 AC-MBR-001의 반환 날짜 집합과 **동등**하다(프로즌 실측: 52개, 2025-08-14 ~ 2026-08-07).
- **비게이팅 [명시]**: 이 절은 선행 `AC-SGR-007`(TG-1)이 이미 소유한 계약의 **재확인**이며, 본 SPEC이 새로 강제하는 요구사항이 아니다. 실패 시 선행 SPEC의 회귀를 의미하므로 리포트로 남기되 본 SPEC의 CI를 막지 않는다. **미충족 기준으로 읽지 않는다.**

### AC-MBR-005 — 이력 부족의 비침묵 공개 (REQ-MBR-004)

- **Given** ISO 주 **10개**만 담은 합성 픽스처(주당 1날짜, 진행 중인 주 없음 — `as_of`를 마지막 주 다음 주 월요일로 고정)에서
- **When** `compute_breadth_history(fixture, "KOSPI", weeks=52)`를 호출하면
- **Then** `len(results) == 10`이다.
- **And** `caplog.at_level(logging.WARNING)`으로 캡처한 레코드 중 **`"52"`와 `"10"`을 모두 포함하는 레코드가 최소 1건** 존재한다 — `assert any("52" in r.message and "10" in r.message for r in caplog.records)`.
- **잡는 잘못된 구현**: 요청보다 적게 반환하면서 **아무 로그도 남기지 않는 조용한 축소**. 레벨만 확인하거나 레코드 개수만 세는 검사는 금지한다(어느 값이 부족했는지 식별 불가하면 진단 가치가 없다).
- **항진명제가 아닌 근거**: 현행 구현은 이 로그를 **전혀 남기지 않으므로** 이 단언은 현재 반드시 실패한다(RED 확인 가능).

### AC-MBR-006 — 금지 관용구 부재 (정적 스캔, REQ-MBR-006)

- **Given** 저장소 루트에서
- **When** 다음 스캔을 실행하면

  ```bash
  grep -nE 'MAX\(Date\)|DISTINCT[[:space:]]+Date|GROUP[[:space:]]+BY[[:space:]]+Date' \
    my_chart/analysis/market_breadth.py
  ```

- **Then** 매칭이 **0건**이다(exit 1).
- **And** **대조 단언**: `:472`를 원시 `SELECT DISTINCT Date … ORDER BY Date DESC LIMIT ?`로 되돌린 변형에서 이 스캔이 **1건 이상 매칭**한다(exit 0). 되돌림 변형은 임시 파일 사본에 적용해 검사하며, 원본을 수정하지 않는다.
- **And** `market_breadth.py`가 `my_chart.analysis.weekly_grid`를 import한다.
- **잡는 잘못된 구현**: 격자를 쓰는 새 코드 경로를 추가하면서 낡은 쿼리를 **삭제하지 않고 남겨둔** 상태(사용되지 않더라도 재도입 경로가 된다).
- **항진명제가 아닌 근거**: 대조 단언이 스캔 자체의 검출력을 증명한다 — 스캔이 아무것도 잡지 못하도록 잘못 작성되면 대조 단언이 실패한다.

### AC-MBR-007 — 기간 표기 3중 일치 (REQ-MBR-005)

- **Given** §1.6의 세 표면에서
- **When** 각 표면의 기간 문구를 조회하면
- **Then** 세 조건이 모두 성립한다:
  - `backend/routers/market.py`에 문자열 `12-week`이 **없다**
  - `frontend/src/components/MarketOverview/BreadthChart.tsx`에 문자열 `12-week`이 **없다**
  - `backend/services/market_service.py`의 `compute_breadth_history(...)` 호출 인자가 여전히 `weeks=52`다
- **And** 위 두 표면이 각각 52주/1년을 뜻하는 문구를 보유한다(문구 리터럴은 run 단계에서 확정하고 테스트 상수와 바이트 동등으로 고정한다).
- **잡는 잘못된 구현**: (a) 백엔드 docstring만 고치고 사용자가 실제로 보는 차트 제목(P2)을 방치, (b) 반대로 프론트만 고침, (c) 라벨 대신 **호출부를 12로 낮춰** 이미 출하된 정보량을 축소(§1.6 판정 위반).
- **항진명제가 아닌 근거**: 세 조건 중 셋째가 나머지 둘과 **반대 방향**이다 — 라벨을 맞추는 가장 쉬운 방법(호출부를 12로 내리기)을 셋째 조건이 명시적으로 차단한다.

### AC-MBR-008 — PRESERVE: 단일 날짜 breadth 불변 (회귀 방지)

- **Given** 프로즌 스냅샷에서 고정 날짜 `d = "2026-07-31"`에 대해
- **When** `compute_breadth(frozen_weekly_db, "KOSPI", d)`를 호출하면
- **Then** 반환 `BreadthResult`의 모든 수치 필드가 본 SPEC 착수 **전에 캡처한 baseline 리터럴과 동등**하다(M1에서 캡처해 테스트 상수로 고정).
- **And** `compute_breadth_composite(result)`도 동일하게 baseline 리터럴과 동등하다.
- **잡는 잘못된 구현**: `:472` 수정 과정에서 `_query_stocks_at_date`(`:85`)나 지표 계산을 함께 건드리는 범위 이탈. 히스토리 날짜 집합이 바뀌어도 **개별 날짜의 breadth 값은 바뀌면 안 된다.**
- **항진명제가 아닌 근거**: 우변이 M1에서 **코드 변경 전에** 캡처된 리터럴이므로, 구현 변경이 값을 움직이면 좌우변이 갈라진다.

### AC-MBR-009 — 기존 테스트 20건 전량 통과 + 공허한 단언 승격

- **Given** `tests/test_market_breadth.py`(526행, 20 테스트)에서
- **When** 전체 테스트를 실행하면
- **Then** 20건 전부 통과한다.
- **And** `test_history_length_matches_weeks_param`의 `assert len(results) <= 4`(금지 형태 **F3**)를 `assert len(results) == 4`로 승격한다 — 해당 픽스처(`weekly_db_12weeks`)는 12개 ISO 주를 정확히 1주 간격으로 담으므로 올바른 구현에서 정확히 4를 반환한다.
- **잡는 잘못된 구현**: `weeks=N`을 상한이 아니라 "가능하면 N 근처"로 해석하는 느슨한 구현.
- **항진명제가 아닌 근거 / 한계 명시**: `weekly_db_12weeks` 픽스처는 **주당 정확히 1날짜**이므로 **다중 날짜 주 오염이 존재하지 않는다** — 이 픽스처 위에서는 V0(현행)과 V★(올바른 구현)이 **동일한 결과를 낸다.** 따라서 이 세 기존 테스트는 본 SPEC의 핵심 결함을 **잡지 못하며**, 잡을 것을 기대해서도 안 된다. 핵심 판별은 전적으로 AC-MBR-001/002/003의 프로즌 스냅샷이 담당한다. 이 한계를 여기에 명문화해 "기존 테스트가 통과하므로 괜찮다"는 오독을 차단한다.

### AC-MBR-010 — 하류 소비자 `detect_choppy` 창의 실질 변화

- **Given** `market_service.py:139`의 `weekly_returns` 프록시가 `history[-8:]`를 쓰고, `detect_choppy(history, ...)`가 히스토리 전체를 받는 상태에서
- **When** 프로즌 스냅샷으로 `weeks=52` 히스토리를 만들고 마지막 8개 날짜의 span을 재면
- **Then** span이 **49–56일**(8 ISO 주)이다.
- **잡는 잘못된 구현**: 격자를 히스토리 **일부에만** 적용하거나, `history[-8:]`가 여전히 원시 행 8개(현행 프로즌 실측 마지막 8 원시 날짜 = 약 21일)를 가리키는 상태.
- **항진명제가 아닌 근거**: 현행 구현에서 이 값은 49 미만이므로 지금 반드시 실패한다(RED 확인 가능). 상·하한 **양쪽 경계**를 두어, 창을 과도하게 넓히는 오배선(예: `history[-8:]`를 `history[:8]`로)도 잡는다.

---

## 4. 회귀 보호 — 바뀌어도 되는 것과 안 되는 것

| 대상 | 판정 | 근거 |
| --- | --- | --- |
| `compute_breadth_history`가 반환하는 **날짜 집합과 span** | **바뀐다(의도)** | 본 SPEC의 목적. §5 |
| `compute_breadth_history`의 **반환 타입** `list[BreadthResult]` | **불변** | `market_service`가 순회·슬라이싱·`detect_choppy` 전달에 의존. 타입 변경은 하류 파급이 크다(REQ-MBR-004가 로그를 채널로 택한 이유) |
| `compute_breadth_history`의 **정렬 순서**(오래된 것 우선) | **불변** | 차트가 이 순서에 의존. 기존 테스트 `test_history_ordered_by_date`가 보호 |
| `compute_breadth`(`:85`) **시그니처·쿼리·의미** | **불변** | AC-MBR-008 |
| `BreadthResult` **필드 구성** | **불변** | `backend/schemas/market.py` 및 프론트 `types/market.ts`가 의존 |
| `compute_breadth_composite`(breadth_score) 산식 | **불변** | AC-MBR-008 |
| `weeks` **기본값 12** | **불변** | 프로덕션 미사용이나 기존 테스트 3건이 사용. 기본값 변경은 본 SPEC 범위 밖의 별개 결정 |
| `market_service.py:132`의 `weeks=52` | **불변** | §1.6 정본 |
| 기존 테스트 20건 | **전량 통과 유지**(1건 단언 승격 — AC-MBR-009) | |

---

## 5. 기대되는 "고장처럼 보이지만 올바른" 변화

릴리스 노트에 아래를 그대로 반영한다. 전부 **의도된 변화**이며 되돌림 대상이 아니다.

| # | 변화 | 프로즌 실측 |
| --- | --- | --- |
| C1 | 시장 개요 breadth 차트의 **구간이 크게 늘어난다** | span 139일 → **358일**(약 20주 → 52주) |
| C2 | **포인트 개수는 그대로 52다** — "점이 줄었다"는 신고는 이 변경 때문이 아니다 | 52 → 52 (§1.4) |
| C3 | x축 간격이 **균등해진다**(다중 날짜 주 중복 소멸) | 고유 ISO 주 21 → **52** |
| C4 | 차트의 **마지막 점이 현재 주가 아니라 직전 완료 주**가 된다 | 2026-08-11(진행 중) → **2026-08-07** |
| C5 | 차트 **제목이 "12-week"에서 1년 기준 문구로 바뀐다** | §1.6 P2 |
| C6 | `detect_choppy`의 판정이 **바뀔 수 있다** — 입력 창이 약 21일에서 49–56일로 넓어지므로 동일 시점에 다른 phase/choppy 결과가 나올 수 있다 | AC-MBR-010 |

**되돌림 경로(폐기 조건)**: 사용자가 1년 구간을 과하다고 판단하면 `market_service.py:132`의 `weeks` 값만 조정하고 라벨을 함께 맞춘다. **격자 적용(REQ-MBR-001~003) 자체는 되돌림 대상이 아니다** — 기간 선호와 격자 정합성은 독립 축이다.

---

## 6. 픽스처 전략

**결정: 선행 SPEC의 프로즌 스냅샷 `tests/fixtures/frozen/weekly-2026-08-12/weekly.db`를 재사용한다. 새 프로즌 스냅샷을 만들지 않는다.**

**적합성 확인 (실측 — 선행 SPEC이 `CG-3 배제 0건`으로 AC-SGR-004를 무효화했던 종류의 불일치를 사전에 검사했다)**

| 본 SPEC AC가 요구하는 픽스처 성질 | 프로즌 스냅샷 실측 | 판정 |
| --- | --- | --- |
| 다중 날짜 ISO 주가 실재할 것 (AC-MBR-003의 반증 가능성) | **21개** | 충족 |
| 진행 중인 주가 실재할 것 (AC-MBR-002) | W33 = 2026-08-11, `is_partial_week=True` | 충족 |
| 52 ISO 주 이상의 이력 (AC-MBR-001) | `history_grid` **345바** | 충족 |
| `compute_breadth_history`가 실제로 동작할 것 | 실행 확인: 52건 반환, 0.04초 | 충족 |
| 지수(KOSPI/KOSDAQ) 행 불요 | 스냅샷에 지수 행 **0건**이나 `compute_breadth`는 지수를 배제하므로 무관 | 충족 |
| 날짜당 충분한 행 수 | 최근 날짜 기준 **33행/날짜**(41 종목) | 충족 |

**합성 픽스처가 추가로 필요한 곳 — AC-MBR-005 뿐이다.** 프로즌 스냅샷은 이력이 345바이므로 "가용 이력 < 요청"을 재현할 수 없다. 10 ISO 주짜리 소형 합성 픽스처를 새로 만든다.

**§3 프로즌 규약 준수**: 선행 SPEC `acceptance.md` §3 규약 3에 따라 라이브 DB 실행은 **비게이팅 스모크**다. 본 SPEC의 게이팅 AC(001/002/003/008/010)는 전부 프로즌 위에서만 실행한다. 스냅샷 갱신 시 본 SPEC의 리터럴(358 / 2025-08-14 / 2026-08-07 / 52)도 함께 재검토 대상이다(규약 4·5).

---

## 7. 범위 제외

### 7.1 Out of Scope — O-G7 일봉 기준일

- `backend/services/meta_service.py:136`의 일봉 기준일 격자 미적용(선행 SPEC §7 **O-G7**)은 본 SPEC 범위 밖이다.
- 사유: O-G7은 결함이 아니라 **미해결 요구사항 질문**("일봉 축에 격자가 필요한가?")이다. 선행 SPEC이 그 답을 발명하지 않기로 명시적으로 결정했으며, 본 SPEC에서 답을 발명하면 선행 SPEC HISTORY가 기록한 실패 양식을 반복한다.
- 선행 `AC-SGR-005` allowlist에 잔류한다.

### 7.2 Out of Scope — `market` 인자의 미사용 필터

- `compute_breadth(db_path, market, date)`의 `market` 인자는 `BreadthResult.market`에 실릴 뿐 종목 필터로 **사용되지 않는다**(`_query_stocks_at_date`는 지수만 배제하고 시장 구분을 하지 않는다). 따라서 `"KOSPI"`와 `"KOSDAQ"`은 동일한 종목 모집단 위에서 계산된다.
- 본 SPEC은 이 동작을 **변경하지 않는다.** 시장별 분리는 별개의 요구사항 결정이며 §8 O-M1로 남긴다.

### 7.3 Out of Scope — 격자 규약 자체의 개정

- CG-1(ISO 주당 1바) / CG-2(진행 중인 주 배제) / CG-3(부분 데이터 배제)의 정의, `weekly_grid.py` API, `grid_version`은 선행 SPEC 소유이며 본 SPEC은 **소비만 한다.**
- 새 날짜 해석 헬퍼를 만들지 않는다(REQ-MBR-001).

### 7.4 Out of Scope — `weeks` 기본값 및 사용자 선택 기간

- 함수 기본값 `weeks=12`의 변경, 프론트에서 기간을 선택하는 UI 추가는 범위 밖이다.

### 7.5 Out of Scope — 선행 SPEC 산출물의 plan 단계 수정

- 본 plan 단계에서는 `SPEC-SECTOR-GRID-001`의 어떤 파일도 수정하지 않는다. `AC-SGR-005` allowlist L5 정리는 run 단계 작업이다(REQ-MBR-006, plan.md M5).

---

## 8. 미결 질문

답을 발명하지 않고 기록만 한다.

| # | 질문 | 왜 지금 답할 수 없는가 |
| --- | --- | --- |
| **O-M1** | `compute_breadth`의 `market` 인자가 종목을 필터하지 않는 것은 의도인가, 미구현인가? (§7.2) | 코드에도 설계 문서(`docs/sector-ux/*`)에도 근거가 없다. `BreadthResult.market`에 값을 싣는 것으로 보아 분리 의도가 있었을 수 있으나, 프론트는 `breadth.kospi`/`breadth.kosdaq`를 별도 표시하므로 **현재 두 값이 동일할 가능성**이 있다. 이는 별개의 출하 결함일 수 있으며 사용자 확인이 필요하다. |
| **O-M2** | `detect_choppy`의 입력 창이 넓어질 때(C6) phase/choppy 판정이 실제로 어떻게 달라지는가, 그리고 그 변화가 바람직한가? | 판정 변화 여부는 run 단계에서 프로즌 스냅샷으로 측정 가능하나, **"바람직한가"는 요구사항 질문**이다. `detect_choppy`의 임계값들은 원시 행 창(약 21일)을 전제로 튜닝됐을 수 있다. 본 SPEC은 창을 올바르게 만들 뿐 임계값을 재튜닝하지 않는다. run 단계에서 실측 후 사용자 확인 대상으로 승격한다. |
| **O-M3** | P2 차트 제목의 최종 문구(`Market Breadth (1-year)` / `Market Breadth (52주)` / 한글 병기)는 무엇인가? | 표기 언어·형식은 UI 문안 결정이며 근거 문서가 없다. AC-MBR-007은 "`12-week`가 없을 것 + 52주/1년을 뜻할 것"까지만 고정하고 리터럴은 run 단계 확정 + 테스트 상수 바이트 동등으로 처리한다. |

---

## 9. 품질 게이트 (Definition of Done)

- [ ] AC-MBR-001 ~ AC-MBR-010 전부 PASS (AC-MBR-004는 비게이팅 리포트)
- [ ] §3.0 금지 형태 F1~F4에 해당하는 단언이 신규 테스트에 **0건** — 리뷰 시 각 AC의 "잡는 잘못된 구현" 열을 대조한다
- [ ] 변형 되돌림 대조 5회 실행: V0 / V1 / V2 / V3 / AC-MBR-006 스캔 되돌림 — 각각 지정된 AC가 **실패함**을 확인
- [ ] 기존 `tests/test_market_breadth.py` 20건 전량 통과
- [ ] §5 C1~C6이 릴리스 노트에 반영
- [ ] REQ-MBR-006의 선행 SPEC allowlist 정리(L5 제거·상한 5→4)가 수행되었거나, 미수행 시 사유가 progress.md에 명시
- [ ] §8 O-M1 ~ O-M3이 사용자 확인 대기 상태로 progress.md에 등재
