# SPEC-SECTOR-METRIC-UNIFY-001 — 인수 조건 (백엔드 · M0~M5 + M5.5)

> **범위**: M0~M5 + M5.5(사다리 정합). 프론트 표시 통일(M6)·Table 기간 토글(M7) AC는 형제 SPEC **`SPEC-SECTOR-DISPLAY-UNIFY-001`** 소관이다. 이관 목록은 §G tombstone.

## 규약 (모든 AC에 적용)

- **[HARD] 판정 기준 (lessons.md #9)**: AC는 "테스트가 존재하고 GREEN"이 아니라 **"되돌림을 실제 적용해 RED를 관측했는가"**로만 만족된다. 실증하지 못한 항목은 GREEN이 아니라 **Gaps**로 기록한다.
- **[HARD] zsh 글롭**: 모든 grep 스캔은 `--include='*.py'`처럼 따옴표로 감싼다. 따옴표 없는 형태는 zsh가 먼저 글롭해 중단시킨다.
- **[HARD] `grep -c` 종료코드 함정**: `grep -c`는 **개수가 0일 때 종료코드 1**을 낸다. AC-SMU-012의 *목표*가 `0`이고 AC-SMU-010의 *기준선*이 `0`이므로, 두 경우 모두 **정답 경로가 exit 1**이다. `subprocess.check_output` / `set -e` / `&&` 체인은 바로 여기서 터진다 — 즉 "올바른 코드에서 통과할 수 없는 스캔"이 된다. 따라서:
  - Python: `subprocess.run(..., check=False)` + `stdout` 파싱 후 정수 단언
  - Shell: `grep -c ... || true` 로 감싸고 출력값을 비교
  - 종료코드를 통과 판정에 쓰지 않는다

---

## §A 최우선 AC (반증 증거가 명확한 3종)

### AC-SMU-001 — 두 산출 경로 지표 일치 (핵심 방어선)

**Given** 고정 픽스처 트리와 기동된 백엔드
**When** 동일 (market, period) 조합으로 두 응답을 얻어 섹터명으로 조인하면
**Then** 29개 섹터 전부에서 아래 **필드 경로 쌍**이 일치한다 — **불일치 0건**

| 지표 | 좌변 (`/api/sectors/bubble`) | 우변 (`/api/sectors/ranking` **봉투 `data[]`**) |
|---|---|---|
| RS | `sectors[i].rs_avg` | `data[j].rs_avg.value` |
| 초과수익률 | `sectors[i].excess_return` | `data[j].excess_returns["<period>"].value` |
| 거래대금 | `sectors[i].trading_value` | `data[j].trading_value["<period>"].value` |
| 기간수익률 | `sectors[i].period_return` | `data[j].returns["<period>"].value` |

```bash
curl -s "http://localhost:8000/api/sectors/bubble?market=all&period=1m"  > /tmp/b.json
curl -s "http://localhost:8000/api/sectors/ranking?market=all&period=1m" > /tmp/r.json
# 좌변: /tmp/b.json 의 sectors[]
# 우변: /tmp/r.json 의 data[]      ← sectors[] 아님
```

- **[HARD] 우변은 봉투 `data[]`이며 레거시 `sectors[]`가 아니다.** `data[]`는 `agg.aggregates`로 채워진다(`backend/services/sector_ranking_service.py:106`). 레거시 `sectors[]`(`SectorRankItem`, `backend/schemas/sector.py`)를 우변으로 쓰면 **두 번 불가능**하다: (1) 그 모델에 `trading_value` 필드가 **아예 없어** 좌변에 대응할 우변이 없고, (2) 그 `excess_returns`는 정의 A(KOSPI)라 M5 이후에도 시장·기간별 **상수만큼 다르며, spec.md §5 M8이 그 잔여를 설계상 의도된 것으로 명시**한다. `sectors[]`는 일치 검증에서 **의도적으로 제외**한다.
- **[HARD] RED 목표 건수 조정 규칙 (M0 귀속)**: 되돌림의 RED 목표는 **M0 특성화가 고정한 불일치 건수 `N`**이다. 이 SPEC은 `N`을 리터럴로 박지 않는다.
  - 조사 시점의 참고값은 "29개 중 20개 불일치"이나, 그 20은 **이번 개정에서 처음 명명한 `sectors[]`↔봉투 `data[]` 쌍으로 측정된 적이 없다**(원본 조사가 어느 배열을 우변으로 썼는지 기록이 없다). 재현 명령도 관측일도 붙일 수 없는 값을 기준선으로 박으면 귀속 없는 단언이 된다.
  - 따라서 **M0가 이 배열 쌍으로 `N`을 측정해 리터럴로 고정**하고, 본 AC는 그 `N`을 참조한다. `N ≠ 20`이어도 결함이 아니다 — 20은 다른(혹은 미상의) 배열 쌍에서 나온 참고값이다.
  - **단 `N == 0`이면 즉시 blocker로 보고한다.** 두 경로가 실제로 갈린다는 이 SPEC의 전제가 무너진 것이고, 그 경우 되돌림이 RED를 낼 수 없어 본 AC는 동어반복이 된다.
  - 이 규칙은 AC-SMU-002의 "9개 섹터 목록·방산 두 값은 M0 특성화에서 리터럴로 고정" 조항과 같은 구조다.
- **되돌림 절차**: M4 커밋을 revert(또는 `get_sector_bubble` 본문을 `compute_sector_bubble` 경로로 되돌림) → 동일 조인 실행 → **M0가 고정한 `N`건**의 불일치 재현 관측 → 트리 복원 후 `git status --short`로 복원 증명
- **왜 항진명제가 아닌가 (두 갈래)**:
  - **구조적 근거 (지금 성립)**: 단언의 양변이 **서로 다른 엔드포인트·서로 다른 서비스 모듈**에서 온다 — 좌변은 `backend/services/sector_advanced_service.py`, 우변은 `backend/services/sector_ranking_service.py`의 `agg.aggregates`. 어느 한쪽 헬퍼를 두 번 호출해 비교하는 형태가 아니다(lessons #9).
  - **경험적 근거 (M0에서 확정)**: 되돌림이 **M0가 고정한 `N`건**을 재현한다. `N`은 아직 이 배열 쌍으로 측정되지 않았으므로 여기서 실측으로 주장하지 않는다 — 위 조정 규칙대로 M0가 고정하며, `N == 0`이면 이 AC는 동어반복이 되므로 blocker다.

### AC-SMU-002 — 결측 제외 + 무결측 섹터 값 불변 (양쪽 모두 게이팅)

**Given** M4 적용 트리
**When** 섹터 `rs_avg`를 산출하면
**Then (a)** 결측이 있는 섹터의 값이 결측 제외 기준으로 바뀐다 — **방산 47.35(0-대체) → 53.27(제외)**
**And (b)** 결측 0건 섹터 **9개**(PCB·게임·금융·내수·비철금속·스마트폰·유통·지주사·철강)의 값이 **소수점까지 불변**이다

- **(b)가 진짜 방어선이다.** 결측 0건 섹터는 두 구현이 수학적으로 동일해야 하는 집합이므로, 여기서 값이 움직였다면 결측 처리가 아니라 **다른 무언가를 깨뜨린 것**이다. (a)와 동등한 게이팅 비중을 갖는다 — 각주가 아니다.
- **되돌림 (a)**: M4 revert → 방산 47.35 재현 관측
- **되돌림 (b)**: 결측 종목을 0으로 채우는 monkeypatch 주입 → 9개 섹터 값이 이동하는 것을 RED로 관측 → 트리 복원
- 9개 섹터 목록·방산 두 값은 M0 특성화에서 **리터럴로 고정**한다

### AC-SMU-003 — `rs_avg` 기간 불변 (INV-3 회귀 방어)

**Given** M4 적용 트리 **When** 동일 market으로 `period=1w`/`1m`/`3m`을 호출하면 **Then** 모든 섹터의 `rs_avg`가 세 응답에서 동일하다.
- **동반 단언**: `excess_return`·`period_return`·`trading_value` 3개는 기간별로 **서로 달라야** 한다. 그것이 없으면 "전부 상수를 반환해도 통과"하는 항진명제다
- **되돌림**: `rs_avg` 투영을 기간 의존 필드로 바꾸는 임시 편집 → 세 기간 값이 갈라지는 것을 RED로 관측

---

## §B 백엔드 AC

### AC-SMU-004 — 초과수익률 항등식
**Then** `returns[p] - benchmark.returns[p] == excess_returns[p]`가 허용오차 내 성립.
**되돌림**: 벤치마크를 KOSPI 지수로 되돌림 → 항등식 깨짐 RED.

### AC-SMU-005 — 초과수익률 기준 전환 실측치
**When** `period=1m, market=all` **Then** 기계 `22.36 → 18.70`, 금융 `-4.80 → -8.45`.
**되돌림**: M4 revert → 22.36 / -4.80 재현.

### AC-SMU-006 — 전원 결측 시 None
**Given** 전 구성 종목 RS 결측 합성 DB **Then** `rs_avg`가 `0.0`이 아니라 `None`.
**되돌림**: 반환을 `or 0.0`으로 감싸는 편집 → RED.

### AC-SMU-007 — 결측 제외 분모
**Given** 10종목 중 2종목 결측 합성 DB **Then** 분모가 **8**이며 0-대체 계산값(분모 10)과 **strict 부등**.
**되돌림**: 분모를 전체 N으로 변경 → RED.

### AC-SMU-008 — 거래대금 산식
**Then** `sectors[i].trading_value`가 `/api/sectors/ranking` 봉투 `data[j].trading_value["<period>"].value`와 일치하고, 주봉 1개 `close*volume`(약 2.5e7배 작음)과 다르다.
- **우변 필드 경로는 AC-SMU-001과 동일**하게 봉투 `data[]`다. 레거시 `sectors[]`에는 `trading_value` 필드가 존재하지 않으므로 그 배열로는 이 AC를 표현할 수 없다.
**되돌림**: M4 revert → 2.5e7배 차이 재현.

### AC-SMU-009 — `market_filter` 정직성
**When** `market=kospi`/`kosdaq`/`all` **Then** 봉투 `market_filter`가 요청값과 같다.
- **기준선**: 현재는 모든 요청에 `"all"` 고정(D4)
**되돌림**: `envelope_fields` 호출을 직접 응답 생성으로 되돌림 → `kospi` 요청에 `"all"` RED.

### AC-SMU-010 — 봉투 필드 채움
**Then** `benchmark` non-null, `data[]` 비어있지 않음, `return_window_days`가 기본값 아님.
- **정적 스캔 (미변경 트리 실행 관측값)**:
  ```bash
  grep -c 'envelope_fields' backend/services/sector_advanced_service.py || true
  ```
  **관측 출력(2026-08-18, 미변경 트리)**: `0` (종료코드 1 — 위 규약대로 종료코드를 판정에 쓰지 않는다) → **목표: `1` 이상**
**되돌림**: M5 revert → `0` 재현.

### AC-SMU-011 — 레거시 봉투 키 유지
**Then** `date`/`period`/`market`/`sectors` 4개 키 존재(`tests/test_response_contract.py:327` 통과 유지).
**되돌림**: 한 개 제거 → 기존 계약 테스트 RED.

### AC-SMU-012 — `compute_sector_bubble` 참조 제거 (정적 스캔)
```bash
grep -c 'compute_sector_bubble' backend/services/sector_advanced_service.py || true
```
- **관측 출력(2026-08-18, 미변경 트리)**: `3` — import 1(`:13`) + docstring 언급 1(`:52`) + 호출 1(`:59`)
- **목표 `0`. docstring의 언급도 함께 제거해야 도달한다** — 구현 요구사항이다
- 목표가 0이므로 정답 경로의 종료코드가 1이다 → 규약대로 `|| true` + stdout 파싱
- 스캔 범위가 단일 파일이라 본 SPEC 신설 테스트 파일을 자기 매칭하지 않는다
**되돌림**: 서비스 변경 revert → `3` 재현 RED.

### AC-SMU-013 — `compute_sector_bubble` 존치 + deprecation
**Then** `/market/overview`가 정상 동작하고, `my_chart/analysis/sector_advanced.py`의 해당 docstring이 "HTTP 엔드포인트를 다시 지원하지 말 것" 취지를 담는다.
**되돌림**: 함수 삭제 → `/market/overview` 실패 RED.

### AC-SMU-014 — `daily_db_path` 키워드 호환
**Then** 실행 스캔으로 확정한 **단일 위치 인자 호출 3곳**이 전부 통과한다: `tests/test_ac_sag_037_endpoint_date_consistency.py:87`, `:184`, **`tests/test_consumer_dates.py:438`**. **And** 라우터(`backend/routers/sectors.py:89`)가 `DAILY_DB_PATH`를 전달한다.
- 스캔 원문과 관측 출력은 spec.md REQ-SMU-008에 리터럴로 고정. 원본 계획의 "4건"은 미검증 수치였고 `test_consumer_dates.py:438`을 누락했다
**되돌림**: 위치 필수 인자로 변경 → 3곳 RED.

### AC-SMU-015 — 섹터 소실 0건 (REQ-SMU-012)
**Given** M4(`MIN_SECTOR_MEMBERS=5` 신규 적용) **Then** 섹터 **집합이** M0 특성화 고정 집합과 **동일**하다.
- 집합 등식으로 단언한다. `len(after) <= len(before)`류 부등식은 항진명제이므로 쓰지 않는다
**되돌림**: 임계값 20 주입 → 방산 소실 RED.

### AC-SMU-022 — 결측 섹터 비드롭 (M3)
**Given** `rs_avg`가 null인 섹터를 포함한 응답 **Then** 그 섹터가 응답 `sectors[]`에서 사라지지 않는다(항목 수 보존).
**되돌림**: null 필터링 추가 → 항목 수 감소 RED.

### AC-SMU-028 — `MetricValueModel` 미탑재 (파괴적 변경 가드, REQ-SMU-013)
**Given** M3 적용 트리 **When** `SectorBubbleItem`의 4개 지표 필드 타입을 검사하면 **Then** 전부 **스칼라-또는-null**(`float | None`)이며 어떤 필드도 `MetricValueModel`(객체)이 아니다.
- 검증 형태 2택: (a) `SectorBubbleItem.model_fields`를 순회해 4개 필드 어노테이션이 객체 모델이 아님을 단언, 또는 (b) 실제 응답 JSON에서 해당 4개 값이 `dict`가 아님을 단언
- **왜 필요한가**: `SectorBubbleChart.tsx:127`이 이 스칼라들을 ECharts 튜플로 펼친다. 객체가 실리면 차트가 조용히 깨진다
**되돌림**: `rs_avg`를 `MetricValueModel`로 바꾸는 편집 주입 → RED 관측.

### AC-SMU-029 — 프론트 타입 동시 확장 (REQ-SMU-011)
**Given** M3 적용 트리 **When** `frontend/src/types/bubble.ts`의 4개 지표 필드를 검사하면 **Then** 전부 `number | null`이고, `npx tsc --noEmit`이 통과한다.
- 백엔드만 nullable로 넓히고 TS를 안 넓히면 null 유입 시 타입 거짓말이 된다
**되돌림**: TS 타입을 `number`로 되돌림 → null 픽스처를 소비하는 테스트에서 `tsc` 오류 RED.

### AC-SMU-018 — 버블 크기 사다리 정합 (게이팅, M5.5)
**Given** M4 적용 백엔드의 실제 `trading_value` 분포 **When** 기간별로 `PERIOD_SIZE_LADDER[period]`의 `[vMin, vMax]`와 대조하면 **Then** 분포의 5~95 백분위가 사다리 구간 안에 들어가고, 렌더된 버블 반지름 **고유값이 3종 이상**이다.
- **[HARD] 이것은 주석이 아니라 게이트다.** 사다리를 맞추지 않으면 모든 버블이 한쪽 끝으로 뭉친다
- **파일은 프론트지만 본 SPEC 소관이다** — M4가 거래대금 단위를 바꾸는 당사자이고, 프론트 SPEC으로 미루면 백엔드만 머지된 구간에서 뭉친 채 배포된다. 경로만 보고 이관하지 말 것
- **미해결 갭 G-3**: 현행 상수(`bubbleRadius.ts:27-31` — `1w` 1e10~1e12 / `1m` 5e10~5e12 / `3m` 1e11~1e13)는 VolumeWon 스케일 기준으로 설계된 것으로 **읽히지만 미측정**이다. 재산출 필요 여부는 **M4 직후 실제 측정으로 결정**한다. 측정 없이 바꾸지도, 그대로 두지도 않는다
**되돌림**: `vMax`를 1e3으로 주입 → 반지름 고유값이 1종으로 붕괴 RED.

---

## §C 프로세스 AC

### AC-SMU-025 — M0 선행 랜딩 (커밋 순서)
**Then** `backend/tests/test_bubble_characterization.py`를 추가한 커밋이 프로덕션 변경 커밋보다 **앞서고**, 그 커밋 diff에 `tests/`·`backend/tests/` **밖 경로가 0개**다.
```bash
M0=$(git log --format='%H' --diff-filter=A -- backend/tests/test_bubble_characterization.py)
git merge-base --is-ancestor "$M0" "$M4"; echo $?      # 0 이어야 함 (순서 술어)
git show --name-only --format= "$M0" | grep -v '^tests/\|^backend/tests/' || true   # 출력 0줄
```
- 두 술어의 최종 명령 형태는 run-phase에서 확정한다(갭 G-7). "프로덕션 파일 0개"는 M0 diff가 자기 테스트 파일을 반드시 포함하므로 **경로 필터**로 정의한다
**되돌림**: 특성화를 M4 이후 커밋으로 옮긴 히스토리 → 순서 술어 RED.

### AC-SMU-026 — M4 국소성
**Then** M1·M2·M3 각 커밋 시점에서 특성화 테스트가 전부 GREEN(값 불변)이고, **M4 커밋에서만** 뒤집힌다.
**되돌림**: M2 배선 커밋에 산식 변경을 섞으면 M2 시점 특성화 RED — 그것이 관측자다.

### AC-SMU-027 — 갱신 대상 외 무회귀 (REQ-SMU-026)
**Then** plan.md §F 전 구간 명령의 실패가 plan.md §D의 의도적 갱신 대상(백엔드 2건)에 한정되고, 그 밖의 실패는 **0건**.

---

## §D 엣지 케이스

| # | 케이스 | 기대 |
|---|---|---|
| E-1 | 전 종목 RS 결측 섹터 | `rs_avg = None`, 응답에서 드롭되지 않음 |
| E-2 | `trading_value = None` | 점선 테두리(기존 `SectorBubbleChart.tsx:113` 동작 보존) |
| E-3 | `market=kosdaq`에서 섹터 0개 | 빈 배열 + 정상 봉투(`market_filter="kosdaq"`), 500 아님 |
| E-5 | 3M 창이 `VolumeWon` 데이터 범위 초과(G-2) | `trading_value = None`(0이 아님) |
| **E-6** | **`_get_latest_valid_date` 실패로 `date == ""`** | **기대**: 빈 `sectors[]` + 유효 봉투를 **200**으로 반환(503 아님). **되돌림은 아래 측정 게이트로 확정한다.** |

### E-6 측정 게이트 — [HARD] 되돌림 기술 전에 분기를 실측한다

`if date:` 가드를 제거했을 때 무슨 일이 일어나는지는 **두 분기**로 갈리며, SPEC이 지금 단정할 값이 아니다. 분기를 잘못 가정하면 되돌림이 **반증 불가능**해진다 — 특히 분기 B에서는 되돌림 결과(200 + 빈 `sectors[]`)가 곧 E-6의 **기대 상태**여서 RED가 관측되지 않는다(lesson #9 동어반복).

**M4 착수 전 실측 1회**로 분기를 확정하고, 관측된 분기에 맞춰 되돌림을 기술한다(AC-SMU-018의 G-3 게이트와 같은 구조 — 갭 G-8).

| 분기 | 무슨 일이 일어나나 | 가드 있음(기대 상태) | 가드 없음(되돌림 상태) | **구별 관측량** |
|---|---|---|---|---|
| **A — 즉시 예외** | `compute_weekly_grid(weekly_db_path, "")`(`my_chart/analysis/sector_metrics.py:794`) 또는 하위가 빈 date에 던짐 → 라우터 포괄 `except Exception`(`backend/routers/sectors.py:90-94`)이 **503**으로 변환 | HTTP **200** + 빈 `sectors[]` | HTTP **503** | **HTTP status** (200 vs 503) — 그대로 RED 관측 가능 |
| **B — 조용한 빈 결과** | `_load_weekly_snapshot(conn, "")`가 빈 스냅샷 반환 → 전 섹터 `members`가 비어 `excluded`에 `no_members`로 빠지고 `aggregates=[]`로 **정상 반환**(`:777-850`) | HTTP **200** + 빈 `sectors[]` + 봉투 `excluded[]` **길이 0**(집계를 아예 호출하지 않음) | HTTP **200** + 빈 `sectors[]` + 봉투 `excluded[]`에 **전 섹터가 `no_members` 사유로 등재**(길이 > 0) | **봉투 `excluded[]` 길이** — status는 양쪽 200이라 구별 불가하므로 이 관측량이 필수 |

- **분기 B로 판명되면** E-6의 단언은 status만으로는 성립하지 않는다. `excluded[]` 길이(가드 있음 `0` vs 가드 없음 `> 0`)를 **추가 관측량으로 반드시 넣는다.** `benchmark`/`data` 채움 여부도 같은 방향의 보조 관측량이 될 수 있으나, 1차 구별자는 `excluded[]`다.
- **분기 A로 판명되면** status 단언만으로 충분하다.
- 실측 방법: 임시 스크립트로 `compute_sector_aggregates(<fixture_weekly_db>, "", as_of="")`를 직접 호출해 **던지는지 / 빈 결과를 반환하는지** 관측하고, 출력을 progress.md에 verbatim 기록한다.

> E-6은 AC-SMU-015(유효 date 픽스처)와 E-3(빈 *kosdaq 유니버스*) 어느 쪽도 덮지 않는 경로다. 현행 `compute_sector_bubble`은 date를 받지 않아 빈 date에도 200을 내지만, M4 이후 `date`는 `compute_sector_aggregates`의 **필수 인자**가 된다.

---

## §E Definition of Done

- [ ] AC-SMU-001~015, 018, 022, 025~029 판정 완료 — 각 항목에 **되돌림 RED 관측 증거**(verbatim 실패 출력) 또는 **Gaps 기재**
- [ ] G-1·G-2가 M0 킥오프에서 확인되고 결과가 progress.md에 기록됨
- [ ] G-3(사다리 정합)이 M4 직후 **측정**으로 판정되고 결정이 기록됨
- [ ] G-7(순서 술어 명령)이 run-phase 착수 시 확정됨
- [ ] **G-8(E-6 분기)이 M4 착수 전 실측 1회로 확정**되고, 관측 출력과 선택된 되돌림 관측량이 progress.md에 기록됨
- [ ] **AC-SMU-001의 `N`(불일치 건수)이 M0에서 `sectors[]`↔`data[]` 쌍으로 측정·고정**됨. `N == 0`이면 blocker 보고
- [ ] plan.md §F 전 구간 명령 실행 + 종료코드 관측 (eslint는 파이프 없이 `; echo $?`)
- [ ] 커버리지 측정 — `coverage run --source=my_chart,backend -m pytest <files>` → `coverage report`
- [ ] M4 커밋 본문에 변경 전후 값 기록
- [ ] frontmatter `status` 갱신 (lessons #6)

---

## §G 프론트 SPEC으로 이관된 AC (tombstone — 번호 재사용 금지)

| 이관된 번호 | 내용 | 이관처 (`SPEC-SECTOR-DISPLAY-UNIFY-001`) |
|---|---|---|
| AC-SMU-016 | RS 문자열 3면 동일성 | AC-SDU-008 |
| AC-SMU-017 | 기간 토글 축 거동(Y 불변/X만 변화) | AC-SDU-009 |
| AC-SMU-019 | 기간별 순위 실반영 픽스처 | AC-SDU-006 |
| AC-SMU-020 | `data[]` 부재 폴백 캡션 | AC-SDU-007 |
| AC-SMU-021 | `null%` 버그 해소 | AC-SDU-002 |
| AC-SMU-023 | 임계값 상수 단일 출처(교차 언어 추출) | AC-SDU-003 |
| AC-SMU-024 | 라벨 정확성 | AC-SDU-004 |
