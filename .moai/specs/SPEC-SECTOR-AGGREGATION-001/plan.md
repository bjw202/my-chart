# SPEC-SECTOR-AGGREGATION-001 Plan — 구현 계획

> 마일스톤은 **되돌리기 어려운 결정 순**으로 배열한다. 지표 의미·응답 계약 같은 고변경 결정을 앞에, 라우터 배선 같은 기계적 작업을 뒤에 둔다.

---

## 0. 착수 전 차단 항목 (BLOCKING)

| ID | 사항 | 상태 | 차단 대상 |
| --- | --- | --- | --- |
| ~~**O-A8**~~ | 미완성 주 바와 기간 계산의 정합 (①의 O-G2 인수) | **해결 (2026-08-13)** — 미완성 주 **포함**(`as_of = latest`), 앵커는 `anchor(t,N)` = 완성 바. 창이 라벨보다 길어짐(+4~+5일, 요일 의존) | **M3 차단 해제.** 파생: REQ-SAG-043 / AC-SAG-046 신설 |
| **O-A7** | 최소 구성수 5 규칙의 Bump 적용 | **미결** | M6의 `/sectors/history`, 그리고 **③의 AC-SUX-019 / AC-SUX-056 R5** |
| ~~O-A1~~ | RS-Ratio 롤링 정규화 | **해결 (2026-08-12)** — 정규화 미적용 | M4 차단 해제 |
| ~~O-A3~~ | 주식수 상수 가정 + "현재주가" 출처 | **해결** — `warnings[]` 명시 + daily 최신 `Close` | M4 차단 해제 |
| ~~O-A4~~ | 거래대금의 기간 정의 | **해결** — 기간 토글과 동일 창 | M5 차단 해제 |
| ~~O-A6~~ | `coverage_ratio` 입도 | **해결** — 지표별 + 최상위 최소값 | M1 차단 해제 |
| ~~①의 close~~ | `SPEC-SECTOR-GRID-001` `status: completed` | **충족 (v0.3.0 `completed`)** | 전 마일스톤 차단 해제 |

**2026-08-13 기준 — run 착수 차단 항목이 전부 해소됐다.** ① close + O-A8 결정 두 조건이 모두 충족되어 **M1~M6 전부 착수 가능**하다. O-A7만 남으며 이는 M6 착수 전 그리고 ③ 착수 전에 해소한다.

### 0.1 v0.4.0 — plan-audit iteration 1 결함 해소 (2026-08-13)

plan-audit iteration 1은 **FAIL 0.78**(Tier L 임계 0.85)이었다. MUST-PASS는 전항 통과했고 실패 동인은 **Testability 0.55** — 게이팅 구조 3건이 지정 산출물 위에서 **실행 불가**였다. 착수 전 반드시 반영해야 하는 것은 다음 3건이다.

| 결함 | 요지 | 착수 전 영향 |
| --- | --- | --- |
| **D1** | 지정 프로즌 픽스처가 게이팅 기대값 8개 중 **7개를 호스팅할 수 없다**(적격 섹터 1개, 헬스케어·방산·디스플레이 부재) | **M1.0에 집계 픽스처 빌드가 추가된다**(아래 M1.0-a). 이 픽스처 없이 캡처하면 R1/R4/R5가 증명 불가 상태로 고정된다 |
| **D3** | `as_of` 리터럴 미기재 | **결정 완료 — `as_of = 2026-08-11`**(사용자 결정). 기존 날짜 축 픽스처 유지, AC-SAG-046 리터럴 4개 불변 |
| **D5** | R1이 보존되지 않는 "등가중 순위"를 비교 대상으로 삼고 있었고 R5는 `N==1`에서 구조적으로 실패했다 | R1을 골든 baseline에 결속, R5를 등간격 파생 단언으로 대체 |

**핵심 설계 변경 — 게이팅 기대값을 리터럴에서 파생 규칙으로 전환한다**(acceptance.md §8.3). 리터럴을 유지했다면 M1.0에서 픽스처를 빌드한 뒤 **acceptance.md 본문의 숫자를 채워 넣어야** 했고, 이는 `manager-develop`이 수행할 수 없는 편집이므로(SPEC 본문 소유권은 `manager-spec`) **run 중단 → blocker → 재위임**이 불가피했다. 파생 규칙에서는 테스트가 픽스처에서 기대값을 독립 산출하므로 픽스처가 어떻게 빌드되든 AC 본문을 고칠 일이 없다.

> **plan-auditor 재실행 안내**: v0.4.0에서 plan 산출물 4종이 전부 변경됐으므로 **plan-artifact hash가 바뀌었고 캐시된 감사 판정(FAIL 0.78)은 무효**다. `/moai run` Phase 1에서 plan-audit이 재실행된다.

### 0.2 v0.4.1 — plan-audit iteration 2 부채 해소 (2026-08-13)

plan-audit iteration 2는 **PASS-WITH-DEBT 0.845**(L 임계 0.85, 조화평균 기준 미달)였다. MUST-PASS 7항 전항 통과, Testability **+0.17**로 단일 이터레이션 최대 상승. iteration 1의 D2/D3/D5/D6/D7/D8/D9는 RESOLVED, D1/D4는 PARTIALLY-RESOLVED. 사용자 결정에 따라 **신규 결함 D10~D15를 M1 착수 전 단일 배치로 해소**했다(집계 설계 재검토는 하지 않는다 — 두 계층 상한 재배분 구조는 그대로 두고 **수용 기준만 고친다**).

| 결함 | 심각도 | 요지 | 해소 |
| --- | --- | --- | --- |
| **D10** | CRITICAL (M3 차단) | AC-SAG-013의 "가중평균 초과수익률 == 0" 파생 항등식이 **올바른 구현에서 거짓**. 상한 재배분은 그룹핑 계층을 넘어 합성되지 않으며, **F4가 상한 구속을 강제**하므로 요건상 반드시 실패했다. 실측 `+1.496127 %p` vs 허용 `±0.05` | 주 단언을 **참조 구현 대조**로 교체(섹터별 `S_s^ref − B^ref` + `ω_s^ref` 가중 잔차). `0` 리터럴 삭제. 무상한 완전분할 `0` 항등식은 **참조 자기검사(비게이팅)** 로만 잔존 |
| **D11** | MAJOR (M3 차단) | AC-SAG-014의 `anchor()` 호출 `== 1` 단언이 **D1/D2 공용 함수 구조(`N+1`회)에서 스스로 RED** | 주 단언을 **인자 `t`의 유일성**으로 이전, 호출 횟수 제약 삭제. `mut_benchmark_own_anchor` 검출력 보존 |
| **D12** | CRITICAL (M1.0-c 차단) | AC-SAG-047이 **존재하지 않는 응답 키**를 단언(`sector_excess_return_1w/1m/3m`, `total_count`) — 정상 캡처에서 게이트가 RED | 실측 직렬화 키로 전면 정정(`sectors[i].excess_returns.{w1,m1,m3}`, `distribution.total`). AC-SAG-027 / REQ-SAG-024 / M1.0-b 주석 파급분도 정정 |
| **D13** | MAJOR (M2 차단) | 참조 구현 계약이 AG-3/AG-4/AG-7에 미규정 — F5/F6이 그 케이스를 주입하므로 참조 동작이 갈릴 수 있었다 | §8.3에 **제외·null 처리 계약** 신설(허용 동작 1개 + 대조 집합 제한 + null 섹터 집합 동등 단언) |
| **D14** | MINOR (M1.0-b 차단) | F1~F11 검증이 **캡처 뒤**에 있어 degenerate 픽스처 위에서 baseline이 떠질 수 있었다 | **AC-SAG-048 신설** — M1.0-a **종료 조건**. MANIFEST 기록값과 검사 산출 실측값의 일치까지 요구 |
| **D15** | MINOR (M3 차단) | AC-SAG-014 / 045 R5-a에 픽스처 지정·`as_of` 고정 누락(규약 1·8 위반) | 태그를 `[게이팅 — 집계 픽스처 · …]`로, Given에 `as_of="2026-08-11"` 명시 |

> **[HARD] 비가역 경계는 M1.0-b가 아니라 M2다** (감사 판정 기록, acceptance.md §8.5). M1.0-a~M1.0-c 구간에서는 **구현 코드가 그대로**이므로 잘못 뜬 baseline은 **재캡처할 수 있다.** 구 구현이 교체되는 **M2에서 캡처 창이 영구히 닫힌다.** run-phase 에이전트가 **M1.0-c에서 AC-SAG-047 RED**를 만나면 (1) 산출물 결함인지 게이트 단언 결함인지 먼저 구분하고, (2) 산출물 결함이면 M1.0-a로 되돌아가 **재캡처**하고, (3) 단언 결함이면 acceptance.md 편집 권한이 없으므로 **blocker report를 반환**한다. **강제 순서: `M1.0-a` → `AC-SAG-048 PASS` → `M1.0-b` → `M1.0-c(AC-SAG-047 PASS)` → `M2`.**

> **plan-auditor 캐시 무효화 (v0.4.1)**: spec.md / plan.md / acceptance.md / progress.md가 다시 변경됐으므로 plan-artifact hash가 바뀌었고 **iteration 2 판정(PASS-WITH-DEBT 0.845)도 캐시로서는 무효**다.

---

## 1. [HARD] 결정 사항

| # | 결정 | 선택 | 근거 |
| --- | --- | --- | --- |
| D1 | 가중치 산출 위치 | `my_chart/analysis/weighting.py` 신규 (섹터·벤치마크 **공용**) | BM-2 방법론 일치를 **구조로 보장** — 같은 함수를 호출하면 어긋날 수 없다 |
| D2 | 벤치마크 산출 | 섹터 집계 함수에 "유니버스 = 전체"를 넣어 호출 | 별도 구현을 두면 EX-1이 다시 깨진다 |
| D3 | `weight_cap` | 상수 `0.10`, 단일 정의 위치. 설정 파일화하지 않음 | 0.3 재평가 시 한 곳만 바꾸면 됨. 사용자 토글은 범위 밖 |
| D4 | 응답 스키마 확장 방식 | **추가 전용 optional 필드** + 라우터 파라미터 **optional + 기본값** | ② 단독 ship 안전 (A7, rollback 단순화) |
| D5 | 캐시 | `(as_of_date, market, period, grid_version)` 키 프로세스 내 메모이즈 | 01 §7.2 SN-5. 외부 캐시 미도입(A3) |
| D6 | 결측 표현 | 값 필드 + 형제 `*_reason` 필드 (또는 `{value, reason}` 객체) — **M1에서 형태 확정** | §9.1 3상태. 형태가 전 응답에 파급되므로 가장 먼저 고정 |
| D7 | 일봉 근사 Stage 분류기 | **삭제**(주석 처리 아님) | 같은 종목이 화면마다 다른 Stage로 보이는 문제의 근본 제거 |
| D8 | 지수 행 사용 | 정합성 검증 전용. 초과수익률 기준으로 사용 금지, 화면 노출 금지 | 01 O-4 결정 |

---

## 2. 마일스톤 (되돌리기 어려운 순)

### M1 — 골든 baseline 캡처 + 응답 계약 + 결측 표현 확정 (가장 되돌리기 어려움)

#### M1.0-a — 집계 프로즌 픽스처 빌드 [HARD · v0.4.0 신설 (D1) · **캡처보다 먼저**]

**골든 baseline은 이 픽스처 위에서 떠야 한다.** 기존 `tests/fixtures/frozen/weekly-2026-08-12/`는 ①이 **날짜 축** 재현용으로 만든 41종목 스냅샷이라 AG-5를 통과하는 섹터가 **게임 하나뿐**이다(실측: `stock_meta` 33행 = 게임 32 / 반도체 1). 그 위에서 baseline을 캡처하면 `data[]`가 1섹터가 되어 R1(순위 이동)·R4(상승/하락 섹터 수)·R5(분포)가 **전부 degenerate**해지고, 캡처 창은 이미 닫힌 뒤다. **순서가 곧 안전장치다 — 픽스처 먼저, 캡처는 그 다음.**

```
tests/fixtures/frozen/aggregation-2026-08-11/
  weekly.db        ← 날짜 축 픽스처 41종목 전량 + 횡단면 보강 종목
  daily.db         ← stock_meta(시총·현재가) + 3M 창 stock_prices(VolumeWon)
  registry.xlsx    ← 보강된 섹터 매핑
  MANIFEST.md      ← as_of: 2026-08-11 · git SHA · 원본 DB mtime · 빌드 명령 · F2~F8 실측 충족값
```

- **요건은 acceptance.md §8.2 F1~F11**이며 **값이 아니라 구조**다. 어느 섹터를 몇 개 넣을지는 빌드 재량이고, 충족 여부만 MANIFEST에 실측으로 기록한다.
- **F1(상위집합)이 날짜 축 정합의 근거다** — 원래 41종목이 385날짜 전부에 행을 갖고 있으므로, 보강 종목이 최근 창에만 존재해도 격자·`as_of=2026-08-11`·`is_partial_week=True`가 그대로 재현된다. 신규 종목은 F9의 53 완성 바 창에만 행을 채우면 되므로 픽스처 크기가 폭증하지 않는다.
- **날짜 축 픽스처(`weekly-2026-08-12/`)는 ① 소관이며 읽기 전용이다** — 수정하지 않는다. 집계 픽스처는 별도 디렉터리다.
- **[v0.4.1 (D14)] 요건 충족 검사는 M1.0-a의 종료 조건이다 — `AC-SAG-048 PASS`.** v0.4.0은 이를 "M1 종료 시"로 적어 캡처(M1.0-b) **뒤**에 두었는데, 그 순서에서는 요건 미충족 픽스처 위에서 baseline이 떠진다(iteration 1 D1 실패 모드의 한 단계 이동). AC-SAG-048은 F1~F11을 각각 독립 단언하고, **MANIFEST에 기록된 값과 검사가 산출한 실측값의 정확한 일치**까지 요구한다(F3은 섹터명 집합까지) — AC-SAG-007 / 045 R6이 섹터명을 MANIFEST에서 읽으므로 MANIFEST가 틀리면 그 두 AC가 틀린 기대값 위에서 GREEN이 된다.
- **AC-SAG-048이 RED인 상태로 M1.0-b(캡처) 착수를 금지한다.**
- 음성 검증 1회: F2 임계를 `>= 12`에서 `>= 999`로 임시 상향한 상태에서 AC-SAG-048이 RED가 됨을 실증하고, 복원 후 `git status --short` 공백을 기록한다.

#### M1.0-b — 골든 baseline 캡처 [HARD · 코드 변경 **전**에 수행]

**어떤 코드도 건드리기 전에 현행 응답을 떠 둔다.** AC-SAG-045 R1("등가중 순위 대비")·R4("현행 대비 상승")·R5("min-max 대비 증가")는 비교 대상이 필요한데, 본 SPEC은 기존 구현을 **교체**하고 어느 SPEC도 구 구현을 보존하지 않는다. 구현이 끝난 뒤에는 비교할 값이 존재하지 않으므로 **지금이 유일한 캡처 시점**이다.

```
tests/fixtures/golden/pre-sector-ux/
  ranking-current.json     ← GET /sectors/ranking (현행 무파라미터 — 1W/1M/3M 전부 포함)
  stage-overview.json      ← GET /stage/overview (현행)
  MANIFEST.md              ← as_of: 2026-08-11 · 캡처 시각 · git SHA · 픽스처 식별자 · 캡처 명령 · 포함 기간 목록
```

- **[v0.4.0 정정 (D4)] 기간별 3파일은 캡처할 수 없다.** `/sectors/ranking`은 현행 **무파라미터**(`backend/routers/sectors.py:44` — `async def sector_ranking()`)이므로 세 번 호출해도 동일 응답 3부다. `period` 파라미터는 M6 신설이다. 다만 현행 응답이 세 기간의 원수익률·초과수익률을 **모두** 싣고 있어 **단일 파일에 세 기간이 전부 담긴다** — 기능 손실 없이 파일만 1개로 줄인다. **[v0.4.1 정정 (D12)] 응답의 실제 키는 `sectors[i].returns.{w1,m1,m3}` / `sectors[i].excess_returns.{w1,m1,m3}`이다**(`backend/schemas/sector.py:24-37`, `sector_ranking_service.py:41-52`). v0.4.0이 인용한 `sector_return_1w` / `sector_excess_return_1w` 계열은 내부 dataclass `sector_metrics.SectorRank`의 필드명이며 **직렬화되지 않는다**(실측: 캡처 JSON에 해당 문자열 0건).
- **M1.0-a의 집계 픽스처 위에서 `as_of="2026-08-11"`로 캡처한다**(acceptance.md §8 규약 2). 라이브 DB로 뜨면 baseline 자체가 드리프트해 비교가 무의미해진다.
- `MANIFEST.md`는 필수다 — 나중에 "이 baseline이 무엇과 비교되는 값인가"를 판별할 수 없으면 R1/R4/R5가 다시 실행 불가능해진다.
- **`as_of` 기준일은 결정 완료다 (2026-08-13, 사용자 결정): `2026-08-11`.** 기존 날짜 축 픽스처를 유지하며 재캡처하지 않는다 — AC-SAG-046의 리터럴 4개(11/32/95, 앵커 07-31 / 07-10 / 05-08, baseline 07-10)가 plan-auditor 독립 실행으로 검증됐고, 재캡처하면 요일이 바뀌어 네 리터럴 전부가 갱신 대상이 되며 그 갱신은 run-phase의 acceptance.md 편집(소유권 위반)을 요구한다. 상세: acceptance.md §8 규약 7.

#### M1.0-c — M1 종료 게이트 [HARD · v0.4.0 신설 (D4)]

- **AC-SAG-047 PASS가 M1 완료 조건이다.** baseline 3파일 존재 + MANIFEST 필수 키 비어 있지 않음 + `as_of == 2026-08-11` + JSON이 `sectors[]` 컨테이너와 `rs_avg`·`composite_score`·`rank`·`excess_returns.{w1,m1,m3}`를 담음 + `sectors[]` 엔트리 수 `>= 10`을 **기계적으로** 검사한다. **[v0.4.1 (D12)] 키 이름은 실측 직렬화 결과로 정정됐다** — v0.4.0의 `sector_excess_return_1w/1m/3m`·`total_count`는 응답에 존재하지 않아 **정상 캡처에서 이 게이트가 RED가 되는 상태**였다.
- **RED를 만났을 때**: 비가역 경계는 M1.0-b가 아니라 **M2**다(§0.2, acceptance.md §8.5). 여기서 RED가 나면 (1) 산출물 결함인지 게이트 단언 결함인지 구분하고, (2) 산출물 결함이면 **재캡처가 가능하다**(코드는 아직 그대로다) — M1.0-a로 되돌아간다. (3) 단언 결함이면 acceptance.md 편집 권한이 없으므로 **blocker report를 반환**한다.
- **왜 필요한가**: 이전 판에서 "미캡처 상태로 M2 착수 금지"의 집행 수단은 산문과 DoD 체크박스뿐이었고, 유일한 기계적 검출기인 R1/R4/R5는 **M7에서야 발화**한다 — 캡처 창(M2가 구 구현을 교체하는 시점)이 닫히고 한참 뒤다. `tests/fixtures/golden/`은 현재 존재하지 않는다(실측 2026-08-13).
- 음성 검증 1회: 세 파일 중 하나를 임시 이동한 상태에서 AC-SAG-047이 RED가 됨을 실증하고 복원 후 `git status --short` 공백을 기록한다.

#### M1.1 — 응답 계약 + 결측 표현

전 응답에 파급되는 형태 결정을 먼저 고정한다.

- D6 결측 표현 형태 확정 → 전 지표 필드에 적용
- **O-A6 반영**: `coverage: {rs, nh, stage, chg, trading_value}` + 최상위 `coverage_ratio = min(...)`, `valid_counts` 동형. AG-7 임계는 최상위 최소값에 적용
- **O-A8 반영**: 봉투에 `return_window_days: {"1w", "1m", "3m"}` 키를 신설한다(REQ-SAG-043). 키 존재·모양은 M1.1 소관(AC-SAG-036), **값의 실측 일치는 앵커가 붙는 M3 소관**(AC-SAG-046)
- `SectorAggregate` / `BenchmarkInfo` / `ResponseEnvelope` dataclass + Pydantic 모델 정의
- RED: AC-SAG-036, AC-SAG-038, AC-SAG-043, AC-SAG-008(지표별 커버리지)
- GREEN: 스키마 정의 + 빈 값으로 채워 반환(값 로직은 M2 이후)

### M2 — 가중·집계 코어 (지표 의미 변경) [**비가역 경계 — 캡처 창이 여기서 닫힌다**]

> **[HARD · v0.4.1] 이 마일스톤이 point of no return이다.** M2가 구 집계 구현을 교체하는 순간 골든 baseline의 재캡처가 불가능해진다. **진입 전제**: `AC-SAG-048 PASS`(집계 픽스처 F1~F11) **및** `AC-SAG-047 PASS`(골든 baseline 캡처 완결성). 둘 중 하나라도 RED면 M2에 진입하지 않는다 — M1.0 구간에서는 아직 되돌릴 수 있다.

- RED: AC-SAG-001 ~ AC-SAG-010
- GREEN: `my_chart/analysis/weighting.py` + `sector_metrics.py` 집계 교체
- `sector_metrics.py:42-44` 거짓 주석 정정
- 커버리지·`effective_n`·`capped_members` 산출

### M3 — 벤치마크 + 순위/정규화 (지표 의미 변경) [O-A8 해결 완료 — 착수 가능]

- **O-A8 결정 (2026-08-13) 반영**: `as_of = latest`(미완성 주 포함), 앵커 = `anchor(t, N)`(완성 바). **BM-6 보존의 유일 조건은 섹터·벤치마크가 같은 `anchor(t, N)` 호출을 쓰는 것**이며, D1/D2(공용 함수)로 구조적으로 보장한다. 각자 다른 뷰(`latest` vs `history_grid`)에서 앵커를 구하면 응답에는 두 날짜가 모두 실려 겉보기 일치하면서 BM-6이 **무증상으로** 깨진다 — 이것이 원래의 위험이었고, 동일 호출 강제가 그 방어다
- **창 길이는 라벨과 다르다** — 실측 11 / 32 / 95일(프로즌, `as_of=2026-08-11`). 이것은 오류가 아니며, `return_window_days`로 응답에 노출한다(REQ-SAG-043). `rank_change`의 `anchor(t,28)`도 같은 이유로 실제 32일이다(AC-SAG-023의 `>= 28`이 이미 수용)
- **[v0.4.0 (D2)] 설계결정 3 정정 반영**: `as_of_is_partial_week == false`는 `창 == N`을 **함의하지 않는다**(실측 `as_of=2026-08-17` → partial `False`인데 창 11/32/95). `as_of`는 날짜 축을 자르지 않고 미완성 주 판정에만 쓰이기 때문이다(`weekly_grid.py:144`). 참 조건은 **최신 대표 바가 금요일**일 때이며, AC-SAG-046의 마감 주 대조는 `as_of` override가 아니라 **금요일 종단 픽스처 변형**(`Date <= '2026-08-07'` 런타임 절단 사본)으로 검증한다 — 실증에서 `latest=2026-08-07 / partial=False / {7,28,91}`이 `as_of` 값과 무관하게 재현됐다
- **[v0.4.0 (D6)] BM-6 게이팅은 구조 단언이다**: 출력 동등(두 앵커 날짜 문자열 비교)은 검출력이 **0**임이 실증됐다 — `latest=2026-08-11`에서 구하든 `history` 마지막 `2026-08-07`에서 구하든 `anchor(·, 7/28/91)`이 **동일하게** 07-31 / 07-10 / 05-08을 반환한다. AC-SAG-014는 `anchor()` 호출 계측으로 `(t, days)` 조합당 **정확히 1회** 호출 + 양쪽 경로가 **같은 반환 객체**를 소비함을 단언한다
- RED: AC-SAG-011 ~ AC-SAG-023, **AC-SAG-046**
- GREEN: 벤치마크를 M2 집계 함수 재사용으로 구현(D2), 조용한 0.0 제거, 순위 백분위 정규화, tie-break, 반올림 1회화, `rank = f(period, market)`, `rank_change` 기준일(①의 `anchor(t,28)`)
- 정적 스캔: 정렬 경로 내 `round(` 0건

### M4 — RRG (O-A1 / O-A3 해결 완료 — 착수 가능)

- RED: AC-SAG-031 ~ AC-SAG-035, AC-SAG-045 R7
- GREEN: 수익률 연쇄 지수, 시점별 시총 역산(**"현재주가" = daily 최신 `Close` 단일 지점**), 벤치마크 기준 RS-Ratio(**롤링 정규화 없음**), 워밍업 미발행, `warnings[]`에 상수 주식수 가정 한계 상설 기재
- 대조 테스트 필수: 구 방식으로 계산 시 점프/패딩이 **발생함**을 단언
- **R7 편중 검사 2종**: `fixture_all_leading`에서 전 섹터 `rs_ratio > 100` + 경고 미발생 / 사분면 균등성 요구 단언 부재 grep. 횡단면 z-score 되돌림 변형에서 실패함을 대조 단언

### M5 — 지표 정정 (독립 커밋 단위)

지표별로 개별 commit — rollback 입도를 지표 단위로 확보한다.

- MAX52 → `MAX(High) over 364d` (AC-SAG-024)
- Stage 단일화 + 일봉 분류기 삭제 (AC-SAG-025, 026, 027) — **`fixture_stage_divergent`(두 분류기가 다른 답을 내는 3케이스)를 GREEN 전에 작성**. 동일성 단독 단언은 양쪽이 모두 구 분류기여도 통과하므로 검출력이 없다. `_classify_stage_simple` 호출부 `:115`·`:143` 교체 + 함수 삭제
- `volume_ratio` → weekly `VolumeSMA10` (AC-SAG-028)
- `trading_value` → daily `VolumeWon`, **집계 창 = 기간 토글 연동**(`[anchor(t,N), t]`) + `trading_value_window_days` 동반 (AC-SAG-029, O-A4 결정 반영)
- RS 평균 결측 제외 (AC-SAG-030)

### M6 — 라우터 파라미터 + 종목 목록 필드 (기계적)

- RED: AC-SAG-039 ~ AC-SAG-042
- GREEN: `backend/routers/sectors.py` 6개 엔드포인트 파라미터 신설, `stage_service` `unclassified_count`·`by_sector` 확장, 종목 목록 3열(1W/1M/3M) + `weight_in_sector` + `sector_aggregate`
- 하위 호환 확인: 파라미터 미전달 시 기존 동작

### M7 — 테스트 대체 + 회귀 게이트

- **프로즌 픽스처 확인** (acceptance.md §8): 게이팅 AC가 **각각 지정된** 픽스처 위에서 실행되는지 확인한다. v0.4.1 게이팅 열거 = **002 / 007 / 011 / 013 / 014 / 024 / 030 / 045(R1·R3·R4·R5·R6) / 046 / 047 / 048** (007은 D9로 순수 합성 열거에서 이동, 014는 D6으로 승격 후 D15로 픽스처·`as_of` 지정, 047은 D4로 신설, **048은 v0.4.1 D14로 신설**). 픽스처 배정: **046만 날짜 축 픽스처**(`weekly-2026-08-12/`), 나머지 횡단면 AC는 **집계 픽스처**(`aggregation-2026-08-11/`). 이 열거는 acceptance.md §8 규약 6과 바이트 단위로 일치해야 한다. `/api/db/update` 1회 실행 후 재실행해 붉어지지 않음을 검증한다
- **집계 픽스처 F1~F11 충족 재확인** (acceptance.md §8.2 · **AC-SAG-048**) — MANIFEST 실측 기록과 실제 픽스처 내용의 일치를 확인한다. 이 검사의 **최초 실행 지점은 M1.0-a 종료**이며(v0.4.1 D14), M7에서는 회귀 확인이다
- **`as_of` 명시 고정 정적 스캔** (§8 규약 8): 게이팅 테스트에서 `as_of=None` 의존 0건. 스캔 명령은 `bash -n` 문법 검증 후 실행하고 명세 블록에서 런타임 추출해 바이트 동등을 단언한다(Lesson #9)
- AC-SAG-044: `hasattr`-only 블록 대체 + 되돌림 검출 3케이스 증명
- AC-SAG-045: R1·R3~R8 회귀 방지 테스트 (**R2는 삭제** — `10<=k<=24`는 29섹터의 34~83%로 아무것도 게이팅하지 않았고 AC-SAG-013과 중복이었다)
- **R1/R4/R5는 M1.0-b에서 캡처한 골든 baseline과 비교한다** (v0.4.0 — R1이 D5로 추가 결속됨). R5는 `최상위>=95 / 최하위<=5` 대신 **등간격 파생 단언**(R5-a) + baseline 대비 표준편차 증가(R5-b)를 쓴다
- **[HARD · Lesson #9] 되돌림 실증 라운드**: acceptance.md §9의 되돌림 실증 DoD 항목에 열거된 **모든** 변형을 실제 적용하고 RED 출력을 verbatim 캡처해 `progress.md §E.2`에 기록한다. 복원 후 `git status --short` 공백 확인. 실증 실패 항목은 GREEN이 아니라 **Gaps**로 기재한다 — 선행 ①에서 "대조 단언 7종 전부 GREEN"으로 close한 뒤 3종이 항진명제로 적발된 전례가 있다
- §0.2 성능 측정 → progress.md §E.2
- 릴리스 노트 작성

---

## 3. 기술 노트

### 3.1 상한 재배분 알고리즘

```python
def capped_weights(caps: dict[str, float], cap: float = 0.10) -> dict[str, float]:
    n = len(caps)
    cap_eff = max(cap, 1.0 / n)
    total = sum(caps.values())
    w = {k: v / total for k, v in caps.items()}
    for _ in range(20):                      # 실측 5회 이내 수렴, 20은 안전 상한
        over = {k for k, v in w.items() if v > cap_eff + 1e-12}
        if not over:
            break
        excess = sum(w[k] - cap_eff for k in over)
        rest = {k: v for k, v in w.items() if k not in over}
        rest_total = sum(rest.values())
        for k in over:
            w[k] = cap_eff
        if rest_total > 0:
            for k in rest:
                w[k] += excess * (w[k] / rest_total)
    return w
```

`rest_total == 0`(전 종목이 상한에 걸림)은 `cap_eff = 1/n`일 때만 발생하며 이때 이미 균등이다.

### 3.2 벤치마크 = 섹터 집계의 특수 케이스

```
benchmark_return(period, market) = aggregate_return(
    universe = effective_universe(as_of_date, market),   # 섹터 그룹핑 없음
    period   = period,
    cap      = WEIGHT_CAP,
)
```
이 구조가 EX-1(방법론 일치)을 **테스트가 아니라 타입 수준에서** 보장한다.

### 3.3 순위 백분위 정규화

```python
from scipy.stats import rankdata      # 또는 pandas Series.rank(method="average")
def norm(values: list[float]) -> list[float]:
    n = len(values)
    if n == 0: return []
    if n == 1: return [50.0]
    r = rankdata(values, method="average")     # ties → 평균 순위
    return [(x - 1) / (n - 1) * 100 for x in r]
```

### 3.4 RRG 지수 연쇄

```
r(t) = Σ(w_i(t−1) × ret_i(t)) / Σ w_i(t−1)      # 가중치는 직전 시점 기준
I(t) = I(t−1) × (1 + r(t)),  I(t0) = 100
```
가중치를 직전 시점 기준으로 잡아야 "구성종목 변동이 수익률로 오인되는" 현상이 사라진다. 시점별 시총은 `주식수 × 그 시점 Close`(RRG-4 역산).

### 3.5 52주 High

`MAX(High)` over `[t−364d, t]`를 **weekly DB**에서 산출한다(daily `stock_meta.high52w`는 갱신 시점 의존). 어느 원천을 쓰든 **단일 원천으로 고정**하고 상수화한다.

---

## 4. 리스크 분석

| 리스크 | 심각도 | 완화 |
| --- | --- | --- |
| **O-A1 미해결 상태로 RRG 구현 강행** | HIGH | M4를 차단 항목으로 지정(§0). 결정 전 착수 금지 |
| 사용자가 순위 변동을 결함으로 신고 | HIGH | AC-SAG-045 R1 + 릴리스 노트 + ③의 헤더 가중 표기(ⓦ/ⓔ) |
| 기간 토글마다 서버 재조회 → 체감 지연 | HIGH | §0.2 목표. D5 메모이즈. 초과 시 ③에 stale-but-showing(LD-C)이 완충 |
| 신규 필드가 파생 구조에 전파 누락 | MEDIUM | AC-SAG-043 4단계 단언 (Lesson #4) |
| 벤치마크 정합성 허용오차 7%p가 잠정치 | MEDIUM | O-A5. 임계값 상수 분리로 조정 용이 |
| 주식수 상수 가정 오류(증자·분할) | MEDIUM | O-A3 결정. 최소한 `warnings[]` 명시 |
| 일봉 Stage 분류기 삭제로 상세 응답 깨짐 | MEDIUM | AC-SAG-025 동일성 단언 + 상세 엔드포인트 회귀 |
| **집계 픽스처 빌드가 F1~F11을 부분 충족한 채 진행** | **HIGH** | M1.0-a → M1.0-b 순서 강제 + MANIFEST에 요건별 실측 기록 + M1 종료 구조 검사. 미충족 요건에 걸린 AC는 GREEN이 아니라 **Gaps**로 기재 |
| **참조 구현(파생 규칙)이 프로덕션과 같은 오해를 공유** | **MEDIUM** | 참조 구현은 프로덕션 모듈을 import하지 않고 원시 컬럼에서 가장 단순한 형태로 재구현. 각 게이팅 AC의 **명명된 되돌림 변형에서 RED 관측**을 GREEN 기록의 전제 조건으로 둔다(§9 DoD) |
| **되돌림 실증 없이 대조 단언을 GREEN으로 기록** | **HIGH** | Lesson #9 — 선행 ①에서 7종 중 3종이 항진명제로 적발된 전례. §9 DoD의 verbatim RED 캡처 항목이 게이트 |
| composite null 전파로 순위표가 비는 상황 | LOW | E4 처리 — 원수익률은 유지 |

---

## 5. mx_plan

| 위치 | 태그 | 내용 |
| --- | --- | --- |
| `weighting.py` `capped_weights` | `@MX:ANCHOR` | AG-1 계약. 섹터·벤치마크 공용 (fan_in >= 4) |
| 벤치마크 산출부 | `@MX:ANCHOR` | BM-2 방법론 일치 — 섹터 집계 함수 재사용이 계약 |
| `norm()` 정규화 | `@MX:ANCHOR` | AG-8. composite·rank 의존 |
| RRG 지수 연쇄 | `@MX:ANCHOR` + `@MX:WARN` | RRG-3/RRG-4. look-ahead 재도입 위험 지대 |
| 결측 3상태 헬퍼 | `@MX:NOTE` | §9.1. 0/50.0 치환 금지 사유 |
| 삭제된 일봉 Stage 분류기 자리 | `@MX:NOTE` | 폐기 사유 + 주봉 분류기로의 포인터 |

---

## 6. 검증 순서

1. ① close 확인
2. `pytest tests/ -k "aggregation or benchmark or rrg or stage"`
3. `pytest tests/` 전체 회귀
4. 되돌림 검출 3케이스 (AC-SAG-044)
5. 7개 엔드포인트 계약 스캔 (AC-SAG-036, 037)
6. 하위 호환 확인 — 기존 프론트엔드로 스모크
7. 성능 측정 (§0.2)
