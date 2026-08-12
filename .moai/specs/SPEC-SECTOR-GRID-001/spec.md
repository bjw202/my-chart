---
id: SPEC-SECTOR-GRID-001
title: "섹터 분석 기반 계층 — 정규 주간 격자·유니버스·적재 보호"
version: "0.3.0"
status: completed
created: 2026-08-12
updated: 2026-08-12
amendment_of: SPEC-SECTOR-GRID-001
author: manager-spec
priority: P0
phase: "sector-ux v1"
module: "my_chart/db, my_chart/registry.py, my_chart/analysis, backend/services"
lifecycle: spec-anchored
tags: "sector, weekly-grid, universe, data-integrity, brownfield, sqlite"
depends_on: []
related_specs: [SPEC-SECTOR-AGGREGATION-001, SPEC-SECTOR-UX-001]
tier: M
---

# SPEC-SECTOR-GRID-001: 섹터 분석 기반 계층 — 정규 주간 격자·유니버스·적재 보호

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 0.1.0 | 2026-08-12 | manager-spec | 초기 SPEC. `docs/sector-ux/01-data-contract.md` §3(시간 축)·§4(유니버스)·§7(스냅샷) 확정안을 구현 계약으로 전환. Lesson #8 [HARD] 반영 — `my_chart/db/weekly.py:148,295` positional INSERT를 column-name으로 마이그레이션하고 legacy-ALTER 시나리오 round-trip AC 포함. Lesson #5/#7 반영 — 사용 패턴 가정·라이브 가설·rollback 시나리오·UI 매핑 명시. |
| 0.2.0 | 2026-08-12 | manager-spec | plan-audit 0.81 PASS-WITH-DEBT 결함 델타 반영 (Completeness/Testability). **핵심 문제: AC가 통과해도 요구사항이 미구현일 수 있는 지점 4곳을 반증 가능하게 재작성.** (1) §1.2.1 신설 — 기준일 소비자를 6개→**7개**로 정정, 누락된 `backend/services/sector_advanced_service.py:40-45` `_get_latest_date()` 추가(5개 엔드포인트 지배). `sector_advanced.py:503`은 호출부이고 실제 쿼리는 `:100`·`:799`임을 정정. `sector_detail_service.py`는 기준일 쿼리 0건으로 대상 아님을 명시. §1.2.2 정적 스캔 allowlist 신설. (2) REQ-SGR-005 — 금지 대상을 `MAX(Date)` 리터럴에서 **3종 관용구**(I1 `MAX(Date)` / I2 `DISTINCT Date … ORDER BY Date DESC` / I3 `GROUP BY Date … DESC`)로 확장. (3) AC-SGR-002 — Then/And 자기모순 해소(판정 대상을 `grid_anomalies` 미기록 쌍으로 한정), 라이브 실측 예외 5건 픽스처 고정. (4) AC-SGR-005 — 스캔을 3종 관용구 통합 + allowlist 상한 4개로 확장. (5) AC-SGR-006 — 라이브에서 `naive MAX == canonical`이라 TG-5가 반증 불가였던 문제를 `fixture_max_ne_canonical` + 소비자별 되돌림 7회 대조 단언으로 해소. (6) AC-SGR-017/018 — `stale ∩ stock_meta = 0`이라 필터 미구현으로도 통과하던 문제를 `fixture_stale_in_meta`(14/15일 경계 포함) + `fixture_last_updated_divergent` + 대조 단언으로 해소. (7) AC-SGR-020 — R2 단측(`>=28`)을 양측(`28~35`)으로, R3 항진명제를 실측 리터럴 32 + Code/Name dedup 분기 픽스처로, R5를 docstring 지시에서 `assert`로 전환. (8) **§3 프로즌 픽스처 규약 신설** — 주 1회+ `/api/db/update`로 게이팅 AC가 코드 변경 없이 붉어지는 문제. (9) §7 O-G6 신설(`market_breadth.py:472` 격자 미적용). 설계 문서 `01 §3.5 TG-3` 동일 모순 함께 개정. |
| 0.2.1 | 2026-08-12 | manager-spec | plan-audit iteration 2 **PASS 0.86**(M, thresh 0.80; MUST-PASS 전항 통과, 단조 개선) 이후 잔여 결함 정리. **(D3) 고정 예외 A1의 `gap_days` 오류 정정 (4 → 5)** — `2020-04-24 → 2020-04-29`는 5일이다(A2=4/A3=5/A4=5/A5=4는 정확). `AC-SGR-002`가 `{from, to, gap_days}` **집합 동등** 비교이므로 이 표로 작성된 테스트는 **올바른 구현에 대해 실패**하며, 그때의 자연스러운 반응(구현을 고치거나 개수 비교로 완화)은 AC가 명시적으로 금지한 두 가지다. `docs/sector-ux/01-data-contract.md:376` 동일 오류 함께 정정. **(D1) `AC-SGR-006`의 7-way 대조를 역할별로 분할** — 확장된 7개 소비자 중 둘이 "해석한 `as_of_date` == W-금요일"을 원리상 만족할 수 없었다: `sector_metrics.py:231`은 `t`보다 **구조적으로 이른** rank_change 기준일(`LIMIT 1 OFFSET 3`)을, `:346`은 날짜 **리스트**를 반환한다. `AC-SGR-006-A`(기준일 해석자 6지점 — 개별 되돌림 6회) / `AC-SGR-006-B`(격자·앵커 소비자 2지점 — `anchor(t,28)` 일치 + 공유 중앙값 가드 집합 동등)로 분리해 각자가 실제로 계산하는 것에 맞는 단언을 준다. **`meta_service.py:196`의 무음 통과 차단**: `WHERE Name = REFERENCE_STOCK` 때문에 `REFERENCE_STOCK`이 부분 데이터 3행에 없으면 순진한 경로로 되돌려도 `W-금요일`이 나와 대조가 통과한다 — 픽스처 조건을 [HARD]로 명문화. **(D2) `REQ-SGR-005`의 주봉/일봉 중의성 제거** — 두 DB 모두 `stock_prices`를 가지므로 한정어 없는 금지는 `meta_service.py:135`(일봉, `stock_meta` 재구축용)를 위반으로 잡는다. 금지 범위를 **주봉 전용**으로 한정(`REQ-SGR-014`의 "daily" 한정과 동형)하고, `:135`를 §1.2.2 allowlist에 사유와 함께 등재(상한 4 → 5). `meta_service` 제외는 **파일 단위가 아니라 지점 단위**이며, `:196` 되돌림 시 스캔이 검출함을 정밀도 대조로 단언한다. **§7 O-G7 신설**(일봉 기준일 격자 필요 여부 — 답을 발명하지 않는다). **(D4) 프로즌 픽스처를 M6 → M1.0으로 이동** — `plan.md`가 "다른 회귀 작업보다 먼저"라고 지시하면서 **최종 마일스톤**에 배치해 지시와 순서가 모순됐다. 그 픽스처가 보호하는 AC는 M1~M5를 게이팅한다. ②의 M1.0 `[HARD · 코드 변경 전]`과 동일 형태로 이동하고 **"미구축 상태로 M1.1 착수 금지"** 진입 게이트를 부여했다. |
| 0.2.2 | 2026-08-12 | manager-spec | M5 run-phase 발견 보완 — AC-SGR-005 allowlist에 `my_chart/analysis/universe.py:106`(일봉 stale 판정, REQ-SGR-014/UN-5) 추가, 상한 5→6. `universe.py:106`은 M2에서 도입된 일봉 `stock_prices` 종목별 `MAX(Date)` 조회(`SELECT Name, MAX(Date) FROM stock_prices GROUP BY Name`)로 allowlist 작성 시점(0.2.0)에 누락됐다. `meta_service.py:135`과 동일 "일봉" 범주(주봉 격자 계약 REQ-SGR-005 주봉 한정 밖)이며 stale는 일봉 개념이므로 주봉 격자를 쓰지 않는다. **코드/요구사항 변경 없음(문서 보완 only)** — REQ-SGR-005/REQ-SGR-014 및 어떤 AC 의미도 변경하지 않는다. acceptance.md AC-SGR-005 grep 제외 + 상한 단언(5→6) 동기화. |
| 0.3.0 | 2026-08-12 | manager-spec | **in-place amendment — 반증력 복구.** sync-auditor 독립 감사 PASS-WITH-DEBT 78.6/100 후속. 0.2.0~0.2.1이 **plan 단계**에서 잡아 고친 "통과해도 미구현일 수 있는 AC" 실패 양식이 **테스트 작성 단계**에서 재발했다 — progress.md §E.2는 "대조 단언 7종 전부 GREEN"이라 적었으나 실제로는 4종만 진짜고 3종은 구현을 전부 되돌려도 동일하게 통과한다. 본 개정은 그 3종의 발생지가 테스트가 아니라 **acceptance.md 본문**임을 확인하고 본문을 고친다. (1) **AC-SGR-005 스캔 명령이 유효한 bash가 아니었다** — 0.2.2에서 추가한 `universe.py` 제외 행 직전 줄에 줄바꿈 이음(`\`)이 빠져 `bash -n` 이 exit 2(syntax error)로 거부한다. 규범 명령이 실행 불가였고, 테스트는 이를 침묵으로 우회했다(`--include="*.py"` 무단 추가 + `universe.py` 를 파이프라인이 아닌 Python 쪽에서 필터). 명령을 복구하고 **결과 집합을 바꾸는 `--include="*.py"` 를 규범에 명문화**하며, 취약한 제외 정규식 연쇄를 **잔류 집합 동등 비교**로 전환한다(허용목록 증감이 자동 검출된다). (2) **§1.2.2 `chart_service.py` 항목이 공허했다** — 실측 `grep -c` → **0건**. 잡히지도 않는 경로가 상한 6개를 잠식했다. 제거하고 상한을 **실행 쿼리 지점 5개**로 재정의한다. (3) **AC-SGR-020 R5가 수학적 항진명제였다** — `len(grid.history) <= COUNT(DISTINCT Date)`는 격자 바가 원시 날짜에서 **선별**되므로 어떤 구현에서도(순진한 구현 포함) 참이다. R4가 이미 `grid` 를 프로즌 리터럴로 고정하지만 **`history_grid`(CG-2 진행 중인 주 배제)를 고정하는 단언은 R-계열에 하나도 없었다** — R5를 프로즌 리터럴 `345` 기준 엄격 부등으로 재기술해 그 공백을 메운다. (4) **AC-SGR-004의 프로즌 적용 주장이 사실과 달랐다** — `MANIFEST.md` 실측 `CG-3 배제된 대표 바 = 0건`, `exclusions == []`. 부분 데이터 날짜 5건은 픽스처에 있으나 어느 것도 ISO 주 대표 바가 아니어서 **CG-3이 한 번도 발화하지 않는다**(CG-1이 대신 배제). AC-004는 프로즌 적용 대상이 아니라 **합성 픽스처 게이팅**임을 명문화하고 필요한 픽스처 성질을 규정한다. (5) **§1.2.1/§1.2.2 행 번호 드리프트** — `stage_service.py:25`·`market_service.py:37`은 현재 빈 줄, `meta_service.py:135`→`:136`, `sector_advanced.py:386`→`:388`. 값을 갱신하되, 재발을 막기 위해 **행 번호를 정보성으로 강등**하고 기계적 키를 `(경로, 매칭 텍스트)`로 전환한다. (6) **§7 O-G6의 라이브 영향 명시** — `market_breadth.py:472`는 가정이 아니라 **현재 출하 중인 사용자 가시 오계산**이다. (7) 미검증 "And" 절 6건을 각각 **필수(테스트화)** 또는 **비게이팅(명시)** 으로 판정한다 — 조용히 버리지 않는다. **어떤 수용 기준도 완화하지 않는다 — 전부 강화 방향이다.** |

---

## Amendments

### 0.3.0 — 반증력 복구 (in-place amendment)

| 항목 | 값 |
| --- | --- |
| 직전 completed 버전 | `0.2.2` |
| `prior_completed_sha` | `95e0980` (sync commit — `in-progress → implemented → completed` 전이 및 3-phase close 담당) |
| 개정 성격 | **in-place amendment** (`amendment_of: SPEC-SECTOR-GRID-001` 자기참조). 후속 SPEC 분리가 아니다 — 결함의 발생지가 본 SPEC의 acceptance.md 본문이므로 본문을 고치는 것이 정확한 귀속이다 |
| 상태 전이 | `completed → in-progress` (신규 enum 없음. `.claude/rules/moai/development/spec-frontmatter-schema.md` § Status Transition Ownership Matrix `completed → in-progress (amendment)` 행) |

**개정 사유**: sync-auditor 독립 감사가 **PASS-WITH-DEBT 78.6/100** (Functionality 78 / Security 92 / Craft 72 / Consistency 75, BLOCKING 0 / SHOULD-FIX 6 / MINOR 6)을 반환했다. 중심 소견은 다음과 같다 — 본 SPEC의 HISTORY 0.2.0~0.2.1은 "AC가 통과해도 요구사항이 미구현일 수 있는 지점"을 **plan 단계에서** 네 곳 찾아 반증 가능하게 재작성한 기록이다. 그런데 **동일한 실패 양식이 한 계층 아래(테스트 작성 단계)에서 재발했다.** progress.md §E.2는 "대조 단언(falsification) 7종 — 전부 GREEN"이라고 기록했으나, 정확한 진술은 **진짜 4종 / 공허 3종**이다. 공허한 3종은 구현을 완전히 되돌려도 동일하게 통과한다.

결정적으로, 그 3종 중 최소 2종은 **테스트의 결함이 아니라 acceptance.md 본문의 결함**이다: R5는 본문 자체가 항진명제이고, AC-005 스캔 명령은 본문 자체가 유효한 bash가 아니다(`bash -n` → exit 2). 테스트를 고치는 것만으로는 다음 작성자가 같은 본문을 읽고 같은 공허한 단언을 다시 만든다. 따라서 본문을 고치는 in-place amendment가 필요하다.

**개정 범위 (영향받는 §B REQ / AC)**:

| 대상 | 개정 내용 | 방향 |
| --- | --- | --- |
| `REQ-SGR-005` / `AC-SGR-005` | 스캔 명령 bash 문법 복구 + `--include="*.py"` 규범화 + 제외 정규식 연쇄 → 잔류 **집합 동등** 전환 + 허용목록 상한 기계 단언 + 7개 모듈 import 단언 명시 열거 | **강화** |
| `REQ-SGR-018` / `AC-SGR-020 R5` | 항진명제 → 프로즌 리터럴(`history_grid == 345`) 기준 엄격 부등 | **강화** |
| `REQ-SGR-003` / `AC-SGR-004` | 프로즌 적용 대상 → **합성 픽스처 게이팅**으로 정정 + 필요 픽스처 성질 규정 | **강화** (지금까지 아무것도 검증하지 않던 AC가 검증을 시작한다) |
| `§1.2.1` 소비자 인벤토리 | 행 번호 갱신 + 정보성 강등, 기계적 키를 `(경로, 매칭 텍스트)`로 전환 | 정확도 복구 |
| `§1.2.2` 정적 스캔 allowlist | 공허한 `chart_service.py` 항목 제거, 상한 6 → **실행 쿼리 지점 5** | **강화** (상한 축소) |
| `§7 O-G6` | 가설이 아니라 **출하 중인 사용자 가시 오계산**임을 명시 | 정확도 복구 |
| `AC-SGR-006-A` / `AC-SGR-017` 라이브 절 | **비게이팅**임을 명시적으로 표기(미충족 기준으로 읽히지 않게) | 명확화 |

**요구사항 의미 변경 없음**: 어떤 REQ의 금지 범위·경계값·기대 동작도 완화하지 않는다. 본 개정은 전부 "통과하기 쉽게" 가 아니라 "되돌리면 실패하도록" 방향이다.

---

## 0. BRIEF (Lesson #7 [HARD] 의무 항목)

### 0.1 라이브 사용 가설 + 재평가 체크포인트

| 항목 | 내용 |
| --- | --- |
| 가설 | 사용자는 이 SPEC의 산출물을 **직접 보지 않는다.** 본 SPEC은 화면 변화가 거의 없는 기반 계층이며, 가치는 "② 집계 / ③ UI가 올바른 숫자를 계산할 수 있는 토대"로만 발현된다. |
| 기대 행동 | 라이브에서 사용자가 체감하는 유일한 변화는 (a) Bump/RRG의 x축 날짜 간격이 균일해지고, (b) 히스토리 구간이 "12주 = 84일"로 늘어나며, (c) 주중 갱신 후에도 중복 바가 쌓이지 않는 것이다. |
| 정량 지표 | 정규 격자 조회 시 최근 364일 = 52±1 바 (현행 실측 52행 = 139일). 다중 날짜 ISO 주 21주 → 조회 결과 0주. |
| 재평가 시점 | ② 집계 SPEC ship 이후 **주중 갱신 1회 + 주말 갱신 1회를 실제로 돌린 뒤**(최소 1개 ISO 주 경과) 사용자에게 "Bump 날짜 축이 균일해 보이는가"를 확인한다. 이 시점 전에는 본 SPEC의 가치를 판정하지 않는다. |
| 폐기 조건 | 격자 정규화로 인해 히스토리 포인트 수가 사용자 기대보다 크게 줄어(중복 바 제거) 차트가 빈약해 보인다고 판단되면, ①의 조회 필터는 유지하되 `weeks` 기본값을 늘리는 조정으로 대응한다(SPEC 폐기 대상 아님). |

### 0.2 성능 baseline + 목표값

| 측정 지점 | baseline (측정 의무) | 목표 |
| --- | --- | --- |
| `/api/db/update` weekly 적재 전체 소요 | 현행 값 측정 후 기록 | +10% 이내 (ISO 주 supersede DELETE 1회 추가분) |
| 정규 격자 산출 함수 1회 호출 | 신규 | P95 < 50ms (단일 SELECT + 그룹핑, 2,548행 × 346주) |
| `/sectors/ranking` 응답 P50/P95 | 현행 값 측정 후 기록 | 격자 필터 추가로 인한 증가 +15% 이내 |
| 격자 결과 캐시 적중 시 | 신규 | < 5ms |

baseline은 run 단계 착수 시 **먼저 측정해 progress.md §E.2에 기록**한다. 목표 미달 시 격자 산출 결과를 프로세스 내 메모이즈(`(db_path, mtime)` 키)한다.

### 0.3 SPEC ID ↔ UI 요소 매핑 표

| UI 요소 | 변화 | 소유 SPEC |
| --- | --- | --- |
| (없음 — 신규 UI 요소 0개) | — | SPEC-SECTOR-GRID-001 |
| Bump 축 하단 `12주 (84일) · 정규 격자 canonical-v1` 문구 | 값이 정확해짐 (표기 자체는 ③이 추가) | ③ SPEC-SECTOR-UX-001 |
| 기준일 배지 `2026-08-11 🟡진행 중인 주` | 값 공급원이 본 SPEC (`as_of_date`/`as_of_is_partial_week`) | 표기는 ③, 값은 ① |

**본 SPEC은 사용자에게 보이는 UI 요소를 추가하지 않는다.** 사용자가 "이 SPEC의 결과"라고 인식할 화면 요소는 없다 — 명명 혼동 방지를 위해 명시한다.

### 0.4 rollback 시나리오

| 단계 | 안전 commit 경계 | rollback 방법 |
| --- | --- | --- |
| M1 (격자 헬퍼 신규) | 신규 모듈 추가만, 기존 호출부 미변경 | 파일 삭제로 무해 복귀 |
| M2 (weekly INSERT column-name) | 단일 commit | revert 후 **DB 재적재 불필요**(column-name INSERT는 값 위치를 바꾸지 않음). 단 revert 시 lesson #8 위험이 복원됨 |
| M3 (엔드포인트 격자 적용) | 서비스별 개별 commit | 서비스 단위 revert 가능 |
| M4 (적재 supersede) | 단일 commit + `--no-supersede` 플래그 | 플래그로 런타임 무력화 → 코드 revert 없이 즉시 정지 |
| M5 (유니버스 규약) | 단일 commit | revert 시 게임 섹터 종목수 32 → 33 복귀 |

**전면 rollback 경계**: M1 직전 commit. 이후 ②/③이 본 SPEC의 헬퍼에 의존하므로, ② ship 이후에는 ①만 단독 rollback할 수 없다.

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + SQLite), localhost 전용
- **선행 설계**: `docs/sector-ux/01-data-contract.md` (855줄, 확정안) — 본 SPEC은 §3 시간 축 / §4 유니버스 / §7 스냅샷 유효성을 구현 계약으로 전환한다
- **변경 성격**: BROWNFIELD — 라이브 DB(주봉 346 ISO주 × 2,548종목, 일봉 1.3M+행)를 보유한 운영 중 시스템
- **개발 방법론**: TDD (`.moai/config/sections/quality.yaml` `development_mode: tdd`)
- **계층 위치**: 3단 분할의 **①번(기반)**. ② 집계와 ③ UI가 본 SPEC에 단방향 의존한다

### 1.2 기존 코드 현황 (실측 확인)

| 경로 | 현행 | 본 SPEC에서의 역할 |
| --- | --- | --- |
| `my_chart/db/weekly.py:32` `_STOCK_PRICES_COLS` | 컬럼 튜플 | 변경 없음 (순서 유지) |
| `my_chart/db/weekly.py:146-148` | `placeholders` + `INSERT OR REPLACE INTO stock_prices VALUES (...)` — **positional** | **column-name INSERT로 마이그레이션 \[HARD, Lesson #8\]** |
| `my_chart/db/weekly.py:295` | `INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?, ?, ?, ?)` — positional | **column-name INSERT로 마이그레이션 \[HARD\]** |
| `my_chart/db/daily.py:267-276` | 이미 column-name INSERT (`@MX:ANCHOR` 보유) | **참조 구현**. 동일 패턴을 weekly에 적용 |
| `my_chart/registry.py` + `Input/sectormap-original.xlsx` | 2,560행 / 고유 `Code` 2,559 | 중복 제거 + 경고 로그 |

#### 1.2.1 기준일 조회 소비자 전량 (7개 모듈, 2026-08-12 재실측)

이전 판은 소비자를 6개로 셌고 `MAX(Date)` 리터럴만 추적했다. **재조사 결과 소비자는 7개 모듈이며, 기준일 조회 관용구는 3종이다.** 관용구가 3종이라는 사실이 AC-SGR-005의 정적 스캔 형태를 결정한다(단일 리터럴 스캔은 절반을 놓친다).

> **[HARD] 행 번호는 정보성이며 기계적 식별자가 아니다 (v0.3.0)**. 이전 판은 아래 행 번호를 allowlist 정밀도의 **지점 단위 식별자**로 취급했다. 그러나 행 번호는 무관한 편집만으로도 어긋난다 — 2026-08-12 재실측 결과 `stage_service.py:25`·`market_service.py:37`은 이미 **빈 줄**이고, `meta_service.py:135`는 `:136`, `sector_advanced.py:386`은 `:388`로 밀렸다. 스캔이나 단언이 행 번호에 의존하면 **코드 변경 없이 붉어지거나(false positive), 조용히 다른 줄을 가리킨다(false negative)**. 따라서 본 개정 이후 **기계적 키는 `(경로, 매칭된 관용구 텍스트)`** 이며, 행 번호는 사람이 찾아가기 위한 참고값으로만 유지한다. AC-SGR-005의 잔류 집합 동등 비교도 이 키를 쓴다.
>
> **"개정 전 지점"과 "현행 지점"을 함께 적는다**: 아래 1~5번의 개정 전 쿼리는 M3/M5에서 **삭제**되었으므로(그것이 본 REQ의 목적이다) 그 행 번호는 현재 코드에 존재하지 않는다. 개정 전 값을 지우면 "무엇이 교체되었는가"의 근거가 사라지고, 현행 값만 적으면 "왜 이 파일이 인벤토리에 있는가"가 사라진다.

| # | 경로 | 개정 전 지점 (교체 대상, 현재는 부재) | 관용구 | 현행 지점 (2026-08-12 실측) |
| --- | --- | --- | --- | --- |
| 1 | `backend/services/sector_ranking_service.py` | `:24` | `SELECT MAX(Date)` | `:8` import, `:21` `_get_latest_valid_date(db_path)` |
| 2 | `backend/services/stage_service.py` | `:25` | `SELECT MAX(Date)` | `:10` import, `:24` 헬퍼 호출 |
| 3 | `backend/services/market_service.py` | `:37` | `SELECT MAX(Date)` | `:16` import, `:35` 헬퍼 호출 |
| 4 | `backend/services/meta_service.py` | `:196` | `SELECT MAX(Date) FROM weekly.stock_prices` (`WHERE Name = REFERENCE_STOCK`) | `:14` import, `:199` 헬퍼 호출. **같은 파일의 일봉 지점(개정 전 `:135` → 현행 `:136`)은 대상이 아니다** — §1.2.2 allowlist + §7 O-G7 |
| 5 | **`backend/services/sector_advanced_service.py`** | `:40-45` `_get_latest_date()` | `SELECT MAX(Date)` | `:17` import, `:56`·`:97`·`:137`·`:246` 헬퍼 호출 4곳. `def _get_latest_date` 정의는 **제거됨**(재도입 경로 차단 — AC-SGR-005) |
| 6 | `my_chart/analysis/sector_advanced.py` | `:98-108` `_get_dates()`, `:799` | `SELECT DISTINCT Date … ORDER BY Date DESC LIMIT ?` | `:14` import, `:104`·`:799` `compute_weekly_grid(db_path)`. 이전 판은 이 파일을 `:503`으로 지목했으나 `:503`은 `_get_dates(conn, 1)` **호출부**였고 실제 쿼리는 두 곳이었다 |
| 7 | `my_chart/analysis/sector_metrics.py` | `:231`(`LIMIT 1 OFFSET 3`), `:346`(중앙값 가드) | `SELECT DISTINCT Date … ORDER BY Date DESC` / `GROUP BY Date … ORDER BY Date DESC` | `:17` import, `:231-232` `anchor(grid, date, 28)`, `:335` `compute_weekly_grid` (개정 전 `:346`에서 이동) |

**소비자의 두 역할 (AC-SGR-006 단언 형태를 결정한다)**: 위 7개 모듈은 하는 일이 같지 않다. **기준일 해석자**(#1·#2·#3·#4·#5·#6 — 주봉에서 단일 기준일 값을 뽑는다)와 **격자·앵커 소비자**(#7 — `:231`은 `t`보다 구조적으로 이른 rank_change 기준일을, `:346`은 날짜별 행 수 가드를 계산한다)로 나뉜다. 후자에 "해석한 `as_of_date` == 정규 대표 바"를 요구하면 **올바른 구현이 실패한다** — `:231`은 정의상 `t`보다 이르고 `:346`은 단일 값이 아니라 리스트를 반환하기 때문이다. 두 역할은 `acceptance.md` AC-SGR-006-A / AC-SGR-006-B로 분리해 각자의 계약으로 단언한다. **교체 대상은 7개 전부**이며(REQ-SGR-005·M5), 분할되는 것은 **검증 형태**다.

**#5의 파급이 가장 크다** — `_get_latest_date`는 5개 호출부(`:71`, `:112`, `:152`, `:261`)를 거쳐 **5개 엔드포인트**를 실질 지배한다:

| 엔드포인트 | 라우터 | 경유 |
| --- | --- | --- |
| `GET /sectors/bubble` | `backend/routers/sectors.py:61-71` | `get_sector_bubble` → `:71` |
| `GET /sectors/rrg` | `backend/routers/sectors.py:82-89` | `get_rrg_data` → `:112` |
| `GET /sectors/history` | `backend/routers/sectors.py:100-108` | `get_sector_history` → `:152` |
| `GET /sectors/{name}/bubble` | `backend/routers/sectors.py:134-143` | `get_stock_bubble` |
| `GET /market/treemap` | `backend/routers/market.py:33-46` | `get_treemap_data` → `:261` |

**누락 원인 (재발 방지용 기록)**: `backend/services/sector_advanced_service.py`(서비스 계층)와 `my_chart/analysis/sector_advanced.py`(분석 계층)는 이름이 거의 같고 둘 다 "sector_advanced"다. 이전 판은 후자만 인벤토리에 올려 전자를 같은 파일로 오인했다. **두 파일은 별개이며 각각 자체 기준일 조회를 갖는다.**

**`backend/services/sector_detail_service.py` 재확인 결과**: `Date` 관련 쿼리가 **0건**이다(`grep -n "Date" ` → 0행). 이 파일은 기준일 소비자가 **아니다** — daily `sma50`/`sma200`을 읽는 일봉 근사 Stage 분류기(`:23-47` `_classify_stage_simple`)를 갖고 있으며 그것은 **② 소관**(REQ-SAG-023)이다. 본 SPEC의 교체 대상이 아님을 명시해 ②와의 경계를 고정한다.

#### 1.2.2 정적 스캔 allowlist (AC-SGR-005 근거)

위 3종 관용구를 통합 스캔하면 본 SPEC의 **범위 밖 실행 쿼리 지점**이 함께 잡힌다. 이들은 기준일 격자와 무관하므로 allowlist로 명시 제외한다 — allowlist를 문서화하지 않으면 스캔이 항상 실패하거나, 반대로 스캔 범위를 좁히다 진짜 소비자를 놓친다.

> **[HARD] `chart_service.py` 항목 제거 (v0.3.0)**. 이전 판은 `backend/services/chart_service.py:39, 51, 143, 155`를 allowlist에 올렸다. 그러나 2026-08-12 실측 `grep -c "MAX(Date)\|DISTINCT Date\|GROUP BY Date" backend/services/chart_service.py` → **0**. 이 파일은 3종 관용구를 **하나도 갖고 있지 않으며**, 따라서 제외할 대상 자체가 없었다. 공허한 항목은 두 가지 해를 끼쳤다: (a) 상한 6개 중 1칸을 잠식해 **실질 상한을 부풀렸고**, (b) "allowlist에 있으니 검토됐다"는 인상을 주어 정당성 회귀 단언이 무엇을 검사하는지 흐렸다. 제거하고 상한을 **실행 쿼리 지점 5개**로 재정의한다 — 상한 축소는 완화가 아니라 **강화**다.

**기계적 키는 `(경로, 매칭된 관용구 텍스트)`이며 행 번호가 아니다** (§1.2.1 상단 [HARD] 참조). 행 번호는 아래 표에서 참고값으로만 유지한다.

| # | 경로 | 매칭 텍스트 (기계적 키) | 행(참고) | 왜 격자 소비자가 아닌가 |
| --- | --- | --- | --- | --- |
| L1 | `backend/routers/db.py` | `SELECT MAX(Date) FROM stock_prices` | `:75` | `/api/db/status`의 적재 상태 표시용. 집계 기준일이 아니다 |
| L2 | `my_chart/analysis/sector_advanced.py` | `SELECT COUNT(DISTINCT Date) FROM stock_prices …` | `:388` | `COUNT(DISTINCT Date)` — 날짜가 아니라 **개수**를 센다 |
| L3 | **`backend/services/meta_service.py`** | `SELECT MAX(Date) FROM stock_prices WHERE Name = ?` | `:136` | **일봉** `stock_prices`에서 기준 종목(`REFERENCE_STOCK`)의 최신 거래일을 해석한다 — `_rebuild`가 daily 커넥션에서 실행되며 주봉은 `ATTACH`될 뿐이다. 본 SPEC의 정규 격자는 주봉 전용이므로 이 지점은 계약 밖이다(REQ-SGR-005 주봉 한정). **같은 파일의 주봉 지점(`FROM weekly.stock_prices`)은 allowlist 대상이 아니라 교체 대상이다** — 파일 단위가 아니라 지점 단위로 제외한다. 일봉 격자 필요 여부는 §7 **O-G7** |
| L4 | **`my_chart/analysis/universe.py`** | `SELECT Name, MAX(Date) FROM stock_prices GROUP BY Name` | `:106` | **일봉** `stock_prices`에서 종목별 `MAX(Date)`를 구해 REQ-SGR-014/UN-5 stale 판정에 사용(`daily_db_path` 커넥션). stale는 일봉 개념이며 주봉 격자(REQ-SGR-005 주봉 한정) 밖이다 — L3과 동일 "일봉" 범주. M2(`universe.py`)에서 도입되어 allowlist 작성 시점(0.2.0)에 누락됐고 0.2.2에서 보완했다. 일봉 격자 필요 여부는 §7 **O-G7** |
| L5 | `my_chart/analysis/market_breadth.py` | `SELECT DISTINCT Date FROM stock_prices …` | `:472` | **판단 보류 항목** — §7 **O-G6**. 격자 오염의 TG-4 왜곡을 동일하게 받으며 **현재 출하 중인 오계산이다**(가설이 아니다). 다만 breadth는 섹터 화면이 아니라 시장 개요 소관이라 본 3-계층 SPEC 범위 밖이므로 이번 범위에서는 allowlist에 넣되 조용히 빠뜨리지 않는다 |

**실행 쿼리 지점 상한 = 5** (L1~L5). 신규 **주봉** 소비자 관용구를 allowlist에 추가해 회피하는 경로는 여전히 위반이다 — 항목마다 사유가 명시되고, 일봉 범주(L3·L4) 확장은 §7 O-G7 미결과 별도로 정당화된다.

**비실행 산문 행(주석·docstring)의 처리**: `universe.py`는 일봉 stale 규칙을 설명하는 주석·docstring에서 `MAX(Date)`를 **문자열로 언급**한다(2026-08-12 실측 `:14`, `:35`, `:55`, `:99`, `:111` — 총 5행). 이들은 SQL이 아니므로 격자 계약 위반이 아니지만, 스캔은 텍스트 매칭이므로 함께 잡힌다. 이전 판의 대응(제외 정규식을 계속 덧붙이기)은 **스캔을 조용히 눈멀게 만드는 방향**이었다 — 정규식이 넓어질수록 진짜 위반도 함께 숨는다. 본 개정은 반대로 간다: **스캔을 넓게 유지하고 잔류 전량을 집합 동등으로 비교한다**(AC-SGR-005). 산문 행도 명시적 allowlist 원소가 되며, 추가·삭제가 자동 검출된다.

### 1.3 실측 근거 (01-data-contract.md §3.1~§3.2, §4.1)

- 전체 346 ISO주 중 **행 날짜가 2개 이상인 주 21주**, 금요일 바 없는 주 21주
- 최근 12행 = 36일(의도 대비 43%), 최근 52행 = 139일(38%)
- registry 2,560행 중 완전 중복 1건(아이톡시 052770) → `/api/sectors` 게임=32 vs `/api/sectors/ranking` 게임=33
- registry 전용 종목 13개, `stock_meta` 전용 0개 → `stock_meta ⊂ registry`
- 일봉 고유 종목 2,580개 중 최근 14일 신규 바 없음 **32개** (팀리드 전달 "34종목"과 불일치 → §7 O-G3)

---

## 2. Assumptions (가정, Lesson #5)

- **A1 (사용 패턴)**: 단일 사용자(jw), localhost 단독. 팀 동시 접근 없음.
- **A2 (갱신 빈도)**: 주봉 DB는 **주 1회 이상, 종종 주중에도** `/api/db/update`로 갱신된다. 주중 갱신이 §3 오염의 직접 원인이다.
- **A3 (freshness 기대치)**: 사용자는 "최신 주가 진행 중이어도 최신 값을 보고 싶다"고 확정했다(01 O-2 해결). 따라서 진행 중인 주를 숨기지 않는다.
- **A4 (캐시 모델)**: 격자 산출 결과는 **프로세스 내 메모이즈**만 도입하고 TTL 캐시·디스크 캐시는 도입하지 않는다. 근거: A2에서 갱신은 사용자가 명시적으로 트리거하므로 `MarketContext`의 수동 갱신 패턴(프로젝트 기존 모델, Lesson #5)과 일관된다. 프론트 TTL 캐시는 ③ 소관.
- **A5**: 과거 오염 행은 **물리 삭제하지 않는다**(고정 결정). 조회 시점 필터 CG-1이 처리한다.
- **A6**: `stock_meta`(일봉 DB)는 `registry`의 부분집합이라는 실측 포함 관계가 향후에도 유지된다고 가정하지 않는다 — UN-3의 교집합 연산이 방향과 무관하게 성립하도록 구현한다.
- **A7**: `SMA10`/`SMA40`/`MAX52`/`CHG_*`는 수집 시점 원천 주봉 시계열에서 계산되어 저장되므로 격자 오염의 직접 영향을 받지 않는다(01 §2.6·§3.2 실측). 본 SPEC은 이들 컬럼의 **재계산을 수행하지 않는다**.
- **A8**: `Input/sectormap-original.xlsx`는 수기 관리 파일이며, 중복 제거는 **로드 시점 메모리 상**에서 수행한다. 원본 xlsx는 수정하지 않는다.

---

## 3. Requirements (요구사항, GEARS)

### REQ-SGR-001 (Ubiquitous) — 정규 주간 격자 단일 함수

The 격자 모듈 **shall** expose a single function that, given a weekly DB path and an optional as-of bound, returns the canonical weekly grid: for each ISO (year, week) present in `stock_prices`, exactly one representative date = `MAX(Date)` within that ISO week (규칙 CG-1).

- 검증: AC-SGR-001, AC-SGR-002

### REQ-SGR-002 (Where) — 진행 중인 주 플래그

Where the latest ISO week in the grid has no Friday bar and that ISO week has not yet ended relative to the representative date, the 격자 모듈 **shall** mark that bar with `is_partial_week = true` and expose `partial_week_trading_days` (해당 주에 존재하는 거래일 수) (규칙 CG-2).

- 검증: AC-SGR-003

### REQ-SGR-003 (When) — 부분 데이터 날짜 배제

When a candidate representative date's row count is below 50% of the median row count over the queried span, the 격자 모듈 **shall** exclude that date from the grid and record an exclusion entry naming the date and its row count (규칙 CG-3).

- 검증: AC-SGR-004

### REQ-SGR-004 (Ubiquitous) — 히스토리·롤링에서 미완성 바 제외

The 격자 모듈 **shall** provide two distinct views: `latest_snapshot` (미완성 바 포함 가능) and `history_grid` (미완성 바 제외). 히스토리·롤링 계산·기준일 비교는 `history_grid`만 사용한다 (규칙 CG-2 후단).

- 검증: AC-SGR-003, AC-SGR-007

### REQ-SGR-005 (Ubiquitous) — 공유 최신 기준일 헬퍼

The backend **shall** resolve `as_of_date` exclusively through a shared `_get_latest_valid_date()` helper backed by REQ-SGR-001. The following **7 modules shall not** resolve a trading-date set from the **weekly** `stock_prices` (`Output/stock_data_weekly.db`, including its `weekly.` ATTACH alias) on their own: `sector_ranking_service`, `stage_service`, `market_service`, `meta_service`, **`sector_advanced_service`**, `sector_advanced`, `sector_metrics` (규칙 CG-4, SN-1). 전량 인벤토리는 §1.2.1.

**[HARD] 주봉/일봉 중의성 제거**: 두 DB **모두** `stock_prices` 테이블을 갖는다. 한정어 없이 "`stock_prices`에서 거래일 집합을 만들지 않는다"고 쓰면 일봉 측 조회까지 금지 대상으로 읽히고, `AC-SGR-005`의 스캔이 `meta_service`의 일봉 기준 종목 최신일 조회(`stock_meta` 재구축용)를 위반으로 표시한다. 그 지점은 본 SPEC의 주간 격자 계약 밖이다.

- 본 REQ의 금지 범위는 **주봉 전용**이다. `REQ-SGR-014`가 이미 stale 판정을 "**daily** `stock_prices`"로 한정한 것과 같은 한정 방식이다.
- `meta_service.py`는 **두 지점을 갖는다**: 일봉 지점 `SELECT MAX(Date) FROM stock_prices WHERE Name = ?`(범위 **밖** — §1.2.2 L3) / 주봉 지점 `FROM weekly.stock_prices`(범위 **안** — 교체 대상). 모듈 단위가 아니라 **지점 단위**로 판정하며, 판정 키는 행 번호가 아니라 **매칭된 관용구 텍스트**다(§1.2.1 상단 [HARD]).
- 일봉 측 기준일 정규화는 본 SPEC이 **요구하지 않는다** — 필요 여부는 §7 **O-G7** 미결이다. 답을 발명하지 않는다.

The prohibition **shall** cover all three latest-date idioms in use, not the `MAX(Date)` literal alone:

| # | 관용구 | 현행 사용처 |
| --- | --- | --- |
| I1 | `SELECT MAX(Date) FROM stock_prices …` | 소비자 1~5 |
| I2 | `SELECT DISTINCT Date … ORDER BY Date DESC LIMIT ?` | 소비자 6, 7 |
| I3 | `SELECT Date, COUNT(*) … GROUP BY Date ORDER BY Date DESC` | 소비자 7 (중앙값 가드) |

I2·I3를 금지 대상에서 빼면 **가장 중요한 두 지점**(`sector_metrics.py:231` `LIMIT 1 OFFSET 3` 기준일, `:346` 중앙값 가드)이 규칙을 우회한 채 통과한다.

- 검증: AC-SGR-005, AC-SGR-006

### REQ-SGR-006 (Ubiquitous) — 달력 앵커링 기간 정의

The 격자 모듈 **shall** expose `anchor(t, days)` returning the most recent `history_grid` bar at or before `t − days`, and the period table **shall** be 1W=7d, 1M=28d, 3M=91d, 6M=182d, 12M/52W=364d (규칙 CP-1).

- 검증: AC-SGR-007

### REQ-SGR-007 (Ubiquitous) — "N주" 파라미터의 의미 재정의

The 격자 모듈 **shall** interpret every `weeks=N` parameter as N canonical weekly bars (주 수), never N DB rows (규칙 CP-2). `compute_sector_history(weeks=N)` returns exactly N `history_grid` dates when available.

- 검증: AC-SGR-008 (TG-4)

### REQ-SGR-008 (Ubiquitous) — weekly INSERT의 column-name 마이그레이션 [HARD, Lesson #8]

`my_chart/db/weekly.py` **shall** write `stock_prices` and `relative_strength` using column-name INSERT of the form `INSERT OR REPLACE INTO <t> (col1, ..., colN) VALUES (?, ..., ?)`, mirroring the shipped pattern at `my_chart/db/daily.py:267-276`. Positional `VALUES ({placeholders})` INSERT **shall not** remain in this module.

- 검증: AC-SGR-009, **AC-SGR-010 (legacy-ALTER 시나리오)**

### REQ-SGR-009 (Unwanted Behavior) — positional INSERT 재도입 금지

`my_chart/db/` 하위 모듈 **shall not** contain a positional `INSERT ... VALUES (` form built from a column-count placeholder string. 정적 스캔으로 검출한다.

- 검증: AC-SGR-011

### REQ-SGR-010 (When) — 주중 재적재 시 동일 ISO 주 supersede

When the weekly ingest writes a bar for ISO week W, the ingest **shall** remove rows of the same `(Name, ISO week W)` whose `Date` is earlier than the newly written bar, so that at most one row per `(Name, ISO week)` is created **going forward**. 과거(이번 실행이 기록하지 않은) ISO 주의 행은 삭제하지 않는다.

- 검증: AC-SGR-012, AC-SGR-013
- 안전장치: `--no-supersede` 플래그로 런타임 무력화 가능해야 한다.

### REQ-SGR-011 (Ubiquitous) — 유니버스 단일 소스

The universe module **shall** treat `Input/sectormap-original.xlsx` (registry) as the sole source of 섹터 소속·산업명(대)·산업명(중)·시장 구분, and `stock_meta` as the sole source of `market_cap` (규칙 UN-1, UN-2).

- 검증: AC-SGR-014

### REQ-SGR-012 (Ubiquitous) — 유효 유니버스 정의

The universe module **shall** compute `유효 유니버스 = registry(dedup) ∩ stock_meta ∩ {최신 정규 바에 가격 존재} ∩ {비-stale}` and expose it as the single input to every sector aggregation (규칙 UN-3).

- 검증: AC-SGR-015

### REQ-SGR-013 (When) — registry 중복 제거 + 경고 로그

When registry loading encounters more than one row for the same `Code`, the loader **shall** keep the first occurrence, drop the rest, and emit a WARNING log naming the code and 종목명. 조용한 무시를 금지한다 (규칙 UN-4).

- 검증: AC-SGR-016 (UN-4)

### REQ-SGR-014 (Ubiquitous) — stale 종목 배제

The universe module **shall** exclude from all denominators any 종목 whose per-name `MAX(Date)` in the **daily** `stock_prices` is more than 14 days older than the latest daily trading date (규칙 UN-5).

- 검증: AC-SGR-017

### REQ-SGR-015 (Unwanted Behavior) — `stock_meta.last_updated` 기반 stale 판정 금지

The universe module **shall not** use `stock_meta.last_updated` for staleness determination — 전 행이 동일 타임스탬프로 갱신되어 판정력이 없다.

- 검증: AC-SGR-018

### REQ-SGR-016 (Ubiquitous) — registry 전용 종목 진단 산출물

The universe module **shall** emit, at load time, the list of `registry \ stock_meta` 종목 (현행 실측 13개) as a WARNING-level diagnostic with count, so that "수집 누락인가 정당한 제외인가"를 사후에 판별할 수 있다. 본 SPEC은 원인 판정 자체를 수행하지 않는다 (§7 O-G1).

- 검증: AC-SGR-019

### REQ-SGR-017 (Ubiquitous) — 미분류 섹터 센티넬 단일화 [잠재 발산 차단]

The universe module **shall** define exactly one canonical unclassified-sector sentinel string and expose it as a shared constant; every path that defaults a missing `산업명(대)` **shall** use that constant. 경로마다 서로 다른 기본값을 쓰는 것을 금지한다.

현행 실측 (2026-08-12 소스 확인):

| 경로 | 현행 기본값 |
| --- | --- |
| `backend/services/stage_service.py:57` | `"Unknown"` |
| `backend/services/stage_service.py:67` | `"Unknown"` |
| `my_chart/analysis/sector_metrics.py:250` | `"기타"` |

한 경로가 만든 섹터 칩은 다른 경로의 행과 **영원히 매칭되지 않는다**. UN-3(단일 소속 원천)만으로는 두 기본값이 일치하도록 강제되지 않으므로 별도 규칙이 필요하다.

- 검증: AC-SGR-021
- **[중요] 잠재 발산 차단이지 라이브 버그 수정이 아니다**: `stock_meta`에 현재 NULL / 빈 문자열 / `'nan'` / `'기타'` 행이 **0건**이므로 오늘은 어떤 행도 센티넬 경로를 타지 않는다. 따라서 **이 변경으로 화면에 보이는 변화는 없다** — 리뷰어가 가시적 변화를 기대해서는 안 된다. 이 규칙은 registry에 미분류 행이 처음 생기는 날 발생할 발산을 사전에 차단한다.
- 설계 문서 근거 없음: `grep -n "Unknown" docs/sector-ux/*.md` → 0행. 두 설계서 모두 이 사안을 다루지 않으며, 결함 인벤토리 대조에서 발견되었다.
- 센티넬 문자열 선택은 §7 O-G5 (`"기타"` 채택이 기본안 — 사용자 노출 문자열이고 종목 버블 `ETC_LABEL`과 일치).

### REQ-SGR-018 (Ubiquitous) — 회귀 방지: 기대되는 변화의 명문화

The regression suite **shall** assert the following as **expected outcomes**, not defects: (a) `compute_sector_history(weeks=12)` 구간이 36일 → 84일로 늘어남, (b) rank_change 기준일이 2026-07-31 → `t−28d` 이하 정규 바로 이동, (c) 게임 섹터 구성종목이 33 → 32로 줄어듦, (d) 정규 격자 조회 결과의 바 개수가 원시 행 수보다 적어짐.

- 검증: AC-SGR-020

---

## 4. Exclusions (What NOT to Build)

### Out of Scope — 집계·지표 의미

- 시총가중·10% 상한·커버리지·composite·정규화: 전부 **② SPEC-SECTOR-AGGREGATION-001** 소관. 본 SPEC은 유효 유니버스와 격자 날짜만 공급한다.
- 벤치마크 선정·정합성·RRG 지수 구성: ② 소관.
- `MAX52` 정의 오류(Close vs High) 수정: 시간축이 아니라 정의 문제 → ② 소관.
- `volume_ratio`의 `VolumeSMA10` 교체: ② 소관.

### Out of Scope — 화면·상태

- `AnalysisParamsContext` / `SelectionContext` / `NavIntent` 도입: **③ SPEC-SECTOR-UX-001** 소관.
- 기준일 배지·진행 중 배지의 렌더링: ③ 소관 (본 SPEC은 값만 공급).
- 응답 스키마에 `as_of_date` 등 공통 필드를 **싣는 작업**: ② 소관 (본 SPEC은 값 산출까지).

### Out of Scope — 데이터 마이그레이션

- 과거 오염 행의 물리 삭제 / 일괄 마이그레이션: 수행하지 않는다(A5, 고정 결정).
- `SMA10`/`SMA40`/`MAX52`/`CHG_*` 컬럼의 재계산·재적재: 수행하지 않는다(A7).
- `INSERT OR REPLACE` 자체의 교체(UPSERT 전략 변경): 수행하지 않는다. supersede로 대응한다.

### Out of Scope — 기타

- 관심 섹터 워치리스트 / 핀 / 즐겨찾기: 전 SPEC 공통 범위 밖.
- 신규 API 엔드포인트 추가: 없음. 기존 엔드포인트의 내부 배선만 바꾼다.
- 산업명(중) 단위 집계 제공: ② §7 O-A2 미결.

---

## 5. Specifications (수용 기준 연결)

상세 Given/When/Then, 에지케이스, 품질 게이트는 `acceptance.md` 참조. 작업 분해·리스크·mx_plan은 `plan.md` 참조.

### Traceability (REQ ↔ AC)

| REQ | 매핑 AC | 01 부록B 불변식 |
| --- | --- | --- |
| REQ-SGR-001 | AC-SGR-001, AC-SGR-002 | **TG-2**, **TG-3** |
| REQ-SGR-002 | AC-SGR-003 | — |
| REQ-SGR-003 | AC-SGR-004 | — |
| REQ-SGR-004 | AC-SGR-003, AC-SGR-007 | — |
| REQ-SGR-005 | AC-SGR-005, **AC-SGR-006-A** (기준일 해석자 6지점), **AC-SGR-006-B** (격자·앵커 소비자 2지점) | **TG-5** |
| REQ-SGR-006 | AC-SGR-007 | **TG-1** |
| REQ-SGR-007 | AC-SGR-008 | **TG-4** |
| REQ-SGR-008 | AC-SGR-009, **AC-SGR-010** | — (Lesson #8) |
| REQ-SGR-009 | AC-SGR-011 | — |
| REQ-SGR-010 | AC-SGR-012, AC-SGR-013 | — |
| REQ-SGR-011 | AC-SGR-014 | — |
| REQ-SGR-012 | AC-SGR-015 | — |
| REQ-SGR-013 | AC-SGR-016 | **UN-4** |
| REQ-SGR-014 | AC-SGR-017 | — |
| REQ-SGR-015 | AC-SGR-018 | — |
| REQ-SGR-016 | AC-SGR-019 | — |
| REQ-SGR-017 | AC-SGR-021 | — |
| REQ-SGR-018 | AC-SGR-020 | — |

**본 SPEC이 책임지는 01 부록 B 불변식: TG-1, TG-2, TG-3, TG-4, TG-5, UN-4 (6개)**

---

## 6. 의존 관계

```
SPEC-SECTOR-GRID-001 (①, 본 SPEC)
        │  격자 날짜 · 유효 유니버스 · as_of_date · anchor(t,days)
        ▼
SPEC-SECTOR-AGGREGATION-001 (②)
        │  응답 공통 스키마 · rank=f(period,market) · 벤치마크
        ▼
SPEC-SECTOR-UX-001 (③)
```

②/③은 ①의 산출물을 소비하지만, ①은 ②/③을 참조하지 않는다. ①은 자체 회귀 게이트(AC-SGR-001~020)만으로 독립 close 가능하다.

---

## 7. 미결 사항 (SPEC 레벨 open questions — 답을 발명하지 않는다)

| ID | 사항 | 출처 | 결정 필요 사항 |
| --- | --- | --- | --- |
| **O-G1** | registry 전용 13종목(NPX, 노블엠앤비, 더존비즈온, 더테크놀로지, 바이온, 스타코링크, 신세계푸드, 아이엠, 아크솔루션스, 에코마케팅, 일정실업, 프로브잇, 현대홈쇼핑)이 `stock_meta`에 없는 이유 | 01 §10 O-8 | 수집 누락인가, 정당한 제외인가. 수집 누락이면 유니버스 규약이 아니라 수집 파이프라인 결함이며 별도 SPEC이 필요하다. 본 SPEC은 REQ-SGR-016으로 **진단 로그만** 남긴다. |
| **O-G2** | 미완성 주 바와 기간 계산의 정합 | 신규 (설계서 미규정) | `as_of_date`가 진행 중인 주(화요일)일 때, `CHG_1W`는 수집 시점 원천 시계열 기준이라 "화요일 대비 전주 화요일"이 아닐 수 있다. `latest_snapshot`(미완성 포함)과 `history_grid`(미완성 제외)가 **서로 다른 날짜를 가리키는 상태**에서 1W 수익률의 기준을 무엇으로 볼 것인가. 설계서 §3.3 CG-2는 "최신 스냅샷으로는 사용"만 규정하고 이 경계를 다루지 않는다. |
| **O-G3** | stale 종목 수 불일치 | 실측 32 vs 팀 전달 34 | 01 §4.2 UN-5는 32개, 작업 지시는 "갱신 정지 34종목"이다. 측정 시점 차이인지 판정 기준 차이인지 확인이 필요하다. 본 SPEC은 **규칙(14일)** 을 고정하고 개수는 측정값으로 둔다(AC-SGR-017은 개수를 하드코딩하지 않는다). |
| **O-G4** | supersede의 되돌림 불가능성 | 신규 | REQ-SGR-010은 이번 실행이 기록한 ISO 주 안에서 더 이른 날짜 행을 물리 삭제한다. "존재하는 행은 보존"이라는 고정 결정과의 경계(과거 이력 보존 / 당주 중복 정리)를 사용자가 승인해야 한다. `--no-supersede`가 안전장치다. |
| **O-G6** | `market_breadth.py:472`의 격자 미적용 — **현재 출하 중인 사용자 가시 오계산** | 신규 (§1.2.1 재실측), v0.3.0에서 영향 등급 정정 | **[중요] 이것은 가설이 아니라 지금 라이브에서 잘못된 숫자를 내는 결함이다.** `compute_breadth_history(db_path, …)`는 **주봉 DB**를 받아(`:461` docstring "Path to weekly SQLite database file") `:472`에서 `SELECT DISTINCT Date FROM stock_prices … ORDER BY Date DESC LIMIT ?`로 **원시 날짜 행**을 가져온다. 따라서 `weeks=12`는 12개 원시 행 = 실측 기준 **약 36일**을 반환하며, 사용자가 "12주"라고 읽는 구간은 실제로 약 6주다. 이는 본 SPEC이 `REQ-SGR-007`(TG-4)로 **다른 곳에서는 이미 고친 바로 그 결함**이며, 시장 개요(breadth) 화면에는 **미수정 상태로 출하되어 있다**. §1.2.2 L5의 allowlist 등재는 "무해하다"는 판정이 아니라 **"이번 SPEC의 3-계층 범위 밖이므로 이번에 고치지 않는다"는 범위 판정**이다 — 두 가지를 혼동해서는 안 된다. 결정 필요: (a) 본 SPEC 범위를 확장해 8번째 소비자로 교체할 것인가, (b) 별도 SPEC으로 분리할 것인가, (c) 오계산을 알면서 감수할 것인가. **(c)를 선택하는 경우에도 "알려진 출하 결함"으로 명시 기록해야 하며, 조용한 잔류는 선택지가 아니다. 결정 전에는 AC-SGR-005 allowlist에 남는다.** |
| **O-G7** | 일봉 기준일의 격자 정규화 필요 여부 | 신규 (AC-SGR-006 역할 분할) | `backend/services/meta_service.py:135`가 **일봉** `stock_prices`에서 기준 종목의 최신 거래일을 해석해 `stock_meta`를 재구축한다. 일봉에도 부분 데이터 날짜가 존재한다면 같은 종류의 오염을 받지만, 본 SPEC의 정규 격자는 **주봉 전용**이고 주봉 픽스처로는 반증할 수 없다. (a) 일봉 격자를 별도 REQ + `fixture_daily_max_ne_canonical`로 본 SPEC에 편입할 것인가, (b) 별도 SPEC으로 분리할 것인가, (c) 감수할 것인가. **결정 전에는 AC-SGR-005 allowlist에 남는다.** 선행 확인: 일봉 DB에 부분 데이터 날짜가 실제로 존재하는지 미측정 — 존재하지 않으면 (c)가 자명하다. |
| **O-G5** | 미분류 섹터 센티넬 문자열의 값 | 신규 (REQ-SGR-017) | 두 경로가 `"Unknown"`과 `"기타"`로 갈려 있다. 기본안은 **`"기타"`** — 사용자에게 노출되는 한국어 문자열이고 종목 버블의 `ETC_LABEL = '기타'`(`StockBubbleChart.tsx:26`)와 이미 일치하므로 화면 어휘가 통일된다. 다만 `"기타"`는 registry에 실재하는 정상 섹터명일 가능성이 있어(현재 0건) "미분류 센티넬"과 "실제 기타 섹터"가 충돌할 여지가 있다. 별도 문자열(예: `"미분류"`)을 쓸 것인지 확인이 필요하다. |
