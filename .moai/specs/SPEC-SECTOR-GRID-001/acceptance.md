# SPEC-SECTOR-GRID-001 Acceptance — 수용 기준

> `development_mode: tdd`. 모든 AC는 **실행 가능한 검사**(쿼리 / 테스트 단언 / 기대 출력이 있는 명령)로 기술한다.
> 산문으로만 서술되어 실패할 수 없는 기준은 두지 않는다.

---

## 1. Given/When/Then 시나리오

### AC-SGR-001 — 정규 격자: ISO 주당 바 1개 (불변식 **TG-2**)

- **Given** 라이브 주봉 DB(`Output/stock_data_weekly.db`) 또는 다중 날짜 ISO 주를 포함한 합성 DB가 있고
- **When** `canonical_weekly_grid(db_path)`가 반환한 날짜 집합을 ISO 주로 그룹핑하면
- **Then** 다음 쿼리가 **0행**을 반환한다.

```sql
SELECT iso_year, iso_week, COUNT(*) c
FROM (정규 격자 날짜)
GROUP BY iso_year, iso_week HAVING c > 1;
```

- **And** 각 ISO 주의 대표 날짜는 그 주에 존재하는 원시 날짜들의 `MAX`와 일치한다 — 실측 검증 케이스 3건을 회귀 픽스처로 고정: W32 → `2026-08-07`, W28 → `2026-07-10`, W27 → `2026-07-03`.
- **현재 상태**: 실패 (21주가 2개 이상)

### AC-SGR-002 — 인접 바 간격 6–10일 (불변식 **TG-3**)

> **이전 판의 자기모순 해소**: 이전 판은 Then에서 "**모든** 간격이 6–10일"을 요구하고 And에서 "범위 밖 간격은 격자에서 **제외하지 않는다**"를 요구했다. 예외 바를 유지하면 Then이 반드시 깨지고, Then을 지키려면 예외를 제외해야 한다 — 어떤 구현도 두 조건을 동시에 만족할 수 없었다. 설계 문서(`01-data-contract.md §3.5 TG-3`)에도 같은 모순이 있었으며 함께 개정했다.
>
> **판정 대상을 한정해 해소한다**: 불변식은 "`grid_anomalies[]`에 기록되지 **않은** 모든 인접 쌍이 6–10일"이며, 실제 게이트는 **"범위 밖인데 기록도 없는 쌍이 0건"**이다.

- **Given** 정규 격자의 `history_grid` 날짜 리스트가 오름차순으로 있고
- **When** 인접 쌍의 일수 차를 계산하면
- **Then** `grid_anomalies[]`에 등재되지 않은 **모든** 쌍이 `6 <= gap <= 10`이다.
- **And** **핵심 게이트**: `{(a,b) : gap(a,b) 범위 밖} \ {grid_anomalies에 기록된 쌍}` 이 **공집합**이다. 즉 범위를 벗어난 쌍은 하나도 빠짐없이 `{from, to, gap_days}`로 기록되어 있다(무음 통과 금지).
- **And** 범위를 벗어난 쌍의 바는 **격자에서 제외되지 않는다** — `len(history_grid)`가 예외 개수만큼 줄지 않았음을 단언한다.

**라이브 실측 예외 5건 — 회귀 픽스처로 고정** (2026-08-12 `Output/stock_data_weekly.db` 정규 격자 346바 실측):

| # | from | to | gap(일) | 원인 |
| --- | --- | --- | --- | --- |
| A1 | 2020-04-24 | 2020-04-29 | 5 | 다음 주가 부처님오신날(4/30)·근로자의날(5/1)로 수요일 종료 |
| A2 | 2020-09-25 | 2020-09-29 | 4 | 다음 주가 추석 연휴(9/30~10/2)로 화요일 종료 |
| A3 | 2021-02-05 | 2021-02-10 | 5 | 다음 주가 설 연휴(2/11~2/12)로 수요일 종료 |
| A4 | 2023-09-22 | 2023-09-27 | 5 | 다음 주가 추석 연휴(9/28~9/29)로 수요일 종료 |
| A5 | 2026-08-07 | 2026-08-11 | 4 | **진행 중인 주**(W33) |

> **A1 `gap_days` 정정 (2026-08-12)**: 이전 판은 A1을 `4`로 적었으나 `2020-04-24 → 2020-04-29`는 **5일**이다(A2=4 / A3=5 / A4=5 / A5=4는 정확). `AC-SGR-002`는 `{from, to, gap_days}` **집합 동등** 비교이므로, 잘못된 값으로 작성된 테스트는 **올바른 구현에 대해 실패한다** — 그리고 그때의 자연스러운 반응은 구현을 "고치거나" 비교를 개수 비교로 완화하는 것인데, 이 AC는 둘 다 명시적으로 금지한다. 설계 문서 `01-data-contract.md §3.5 TG-3` 표에도 같은 오류가 있어 함께 정정했다. 값을 되돌리지 말 것.

- **And** 위 5쌍을 포함한 **축소 스냅샷 픽스처**(§3 프로즌 픽스처 규약)에서 `grid_anomalies`가 정확히 A1~A5를 담는다(집합 동등 비교, 개수만 세지 않는다).
- **And** **A5는 `history_grid`에서 나타나지 않는다** — CG-2가 진행 중인 주 바를 제외하므로, `history_grid` 기준 예외는 A1~A4 4건이고 `latest_snapshot`을 포함한 전체 격자 기준으로만 5건이다. 두 뷰의 예외 개수가 다름을 각각 단언한다.
- **And** **대조 단언**: `grid_anomalies` 기록을 비활성화한 변형에서 핵심 게이트가 **실패**한다(테스트의 반증 가능성 확보).
- **And** 실측 예외는 전부 **6일 미만의 짧은 간격**이며 10일 초과는 0건이다 — "명절이면 간격이 벌어진다"는 반대 방향 가정을 테스트에 넣지 않는다.
- **현재 상태**: 실패

### AC-SGR-003 — 진행 중인 주 플래그와 두 뷰의 분리

- **Given** 최신 ISO 주의 대표 날짜가 화요일이고 그 주에 금요일 바가 없는 합성 DB에서
- **When** `latest_snapshot()`과 `history_grid()`를 각각 호출하면
- **Then** `latest_snapshot.date == 화요일 날짜`이고 `latest_snapshot.is_partial_week is True`이며 `partial_week_trading_days == 그 주의 실제 거래일 수`이다.
- **And** `history_grid`의 마지막 날짜는 **그 화요일이 아니라 직전 완결 주의 대표 날짜**다.
- **And** 최신 주에 금요일 바가 존재하는 픽스처에서는 `is_partial_week is False`이고 두 뷰의 마지막 날짜가 **동일**하다.

### AC-SGR-004 — 부분 데이터 날짜 배제 (규칙 CG-3)

- **Given** 조회 구간의 날짜별 행 수 중앙값이 2,548이고 특정 날짜의 행 수가 1인 픽스처에서 (실측 케이스: 2026-07-23=1행, 07-14=1행, 07-07=1행, 06-11=1행, 06-30=4행)
- **When** 정규 격자를 산출하면
- **Then** 해당 날짜는 격자에 포함되지 않는다.
- **And** `grid_exclusions[]`에 `{date, row_count, median}` 항목이 기록된다.
- **And** 행 수가 중앙값의 정확히 50%인 경계 날짜는 **포함**된다(`< 0.50` 배제, `>= 0.50` 포함 — 경계 방향 확정).

### AC-SGR-005 — 자체 기준일 조회의 부재 (정적 스캔)

> **이전 판의 결함**: 스캔이 `MAX(Date)` 리터럴만 찾았다. 그런데 **가장 중요한 두 지점** — `sector_metrics.py:231`(`LIMIT 1 OFFSET 3`, rank_change 기준일)과 `:346`(중앙값 가드) — 은 `ORDER BY Date DESC` / `GROUP BY Date` 관용구를 쓰므로 **한 번도 매칭되지 않았다.** 스캔이 통과해도 요구사항은 미구현일 수 있었다. 3종 관용구(§1.2.1 I1~I3)를 전부 덮도록 확장한다.

- **When** 다음 명령을 실행하면

```bash
grep -rnE "MAX\(Date\)|max\(Date\)|DISTINCT Date|GROUP BY Date" \
     backend/services/ backend/routers/ my_chart/analysis/ \
  | grep -v "_test\|tests/" \
  | grep -v "my_chart/analysis/weekly_grid\.py" \
  | grep -vE "chart_service\.py|routers/db\.py|sector_advanced\.py:.*COUNT\(DISTINCT|market_breadth\.py" \
  | grep -vE "meta_service\.py:.*MAX\(Date\) FROM stock_prices WHERE Name"
```

- **Then** 출력이 **0행**이다 — 3종 관용구 전부에 대해 모든 **주봉** 기준일 조회가 공유 헬퍼를 경유한다.
- **And** **`meta_service.py` 제외의 정밀도 단언 [HARD]**: 마지막 제외 패턴은 `FROM stock_prices`(일봉, `:135`)만 걸러내며 `FROM weekly.stock_prices`(`:196`)는 **걸러내지 않는다**. 검증: `:196`을 순진한 `MAX(Date)`로 되돌린 변형에서 이 스캔이 **1행 이상을 출력한다**. 파일 단위 제외(`grep -v meta_service\.py`)를 쓰면 이 대조가 실패하므로 금지한다 — 실제 소비자를 통째로 숨기게 된다.
- **And** **allowlist 정당성 회귀**: 제외한 5개 경로가 §1.2.2의 사유(단일 종목 시계열 / 적재 상태 / `COUNT` / O-G6 보류 / **일봉 기준 종목 최신일(O-G7)**)를 여전히 만족함을 각 1건씩 단언한다. allowlist가 조용히 비대해지는 것을 막는다.
- **And** **allowlist 상한 단언**: allowlist 항목 수가 **5개 이하**다(이전 판 4개 + `meta_service.py:135` 일봉 지점 1건 = 5). 신규 위반을 allowlist에 추가해 회피하는 경로를 봉쇄한다.
- **And** §1.2.1의 **7개 모듈 전부**가 격자 모듈을 import한다: `sector_ranking_service.py`, `stage_service.py`, `market_service.py`, `meta_service.py`, **`sector_advanced_service.py`**, `sector_advanced.py`, `sector_metrics.py`.
- **And** `sector_advanced_service.py`에 `def _get_latest_date` 정의가 **남아 있지 않다**(`grep -c` → 0). 함수를 남긴 채 호출부만 바꾸면 재도입 경로가 살아 있다.

### AC-SGR-006 — 전 엔드포인트 동일 격자 (불변식 **TG-5**)

> **이전 판의 결함 (1) — TG-5가 라이브 데이터에서 반증 불가였다.** 이전 판은 "다섯 서비스의 `as_of_date`가 서로 같다"만 단언했다. 그런데 실측(2026-08-12): 최신 ISO 주(W33)의 정규 격자 대표 바 = `2026-08-11` = 순진한 `MAX(Date)`와 **동일**하다. 따라서 다섯 서비스가 **전부 순진한 `MAX(Date)`를 그대로 써도 서로 일치하므로 이 AC는 통과한다.** 서로 같다는 것은 격자를 쓴다는 증거가 아니다. → `fixture_max_ne_canonical`로 해소(아래).
>
> **이전 판의 결함 (2) — 7-way 대조가 2개 소비자에 대해 성립하지 않았다.** 개정판은 단언 대상을 5→7 소비자로 넓혔으나, 그중 둘은 "해석한 `as_of_date` == `W-금요일`"을 **원리상 만족할 수 없다**:
>
> - `my_chart/analysis/sector_metrics.py:231`은 기준일을 해석하지 않는다 — `SELECT DISTINCT Date … WHERE Date < ? ORDER BY Date DESC LIMIT 1 OFFSET ?`로 **`t`보다 구조적으로 이른** `prev_date`(rank_change 기준일)를 뽑는다. `:346`은 `GROUP BY Date` 행 수 가드로 **날짜 리스트**를 반환하며 단일 기준일 값이 아니다. 두 지점을 `== W-금요일`로 묶으면 올바른 구현이 실패한다.
> - `backend/services/meta_service.py:135`는 **일봉 DB**를 읽는다(`_rebuild`가 daily 커넥션에서 실행되고 weekly는 `:194`에서 `ATTACH`될 뿐이다). 주봉 픽스처인 `fixture_max_ne_canonical`은 이 지점을 반증할 수 없다.
>
> **해소 — 역할별로 인벤토리를 분할한다.** §1.2.1의 7개 모듈은 두 역할로 나뉘며, 각 역할에 자기가 실제로 계산하는 것에 맞는 단언을 준다. "7개 소비자가 증명됐다"고 읽히지만 실제로는 5개만 증명하는 상태를 만들지 않는다.

#### AC-SGR-006-A — 기준일 해석자 그룹 (as-of resolvers, 6지점 / 6모듈)

주봉 `stock_prices`에서 **단일 기준일 값**을 해석하는 지점 전량. `fixture_max_ne_canonical`이 진짜로 증명하는 대상이다.

| # | 지점 | 비고 |
| --- | --- | --- |
| A-1 | `backend/services/sector_ranking_service.py:24` | |
| A-2 | `backend/services/stage_service.py:25` | |
| A-3 | `backend/services/market_service.py:37` | |
| A-4 | `backend/services/sector_advanced_service.py:40-45` `_get_latest_date()` | 5개 엔드포인트 지배 |
| A-5 | `my_chart/analysis/sector_advanced.py:98-108` `_get_dates()`, `:799` | `DISTINCT Date … DESC LIMIT` |
| A-6 | `backend/services/meta_service.py:196` | **주봉** (`FROM weekly.stock_prices`), `WHERE Name = REFERENCE_STOCK` — 아래 픽스처 조건 필수 |

- **Given** 다음 조건을 만족하는 합성 주봉 DB 픽스처 `fixture_max_ne_canonical`에서
  - 최신 ISO 주 W에 두 날짜가 존재: `W-금요일`(정상 행 수, 예: 2,000행)과 그보다 **늦은** `W+1-월요일`(행 수 3행 — 중앙값의 50% 미만)
  - 따라서 순진한 `MAX(Date)` = `W+1-월요일`, **CG-3이 부분 데이터로 배제**한 뒤의 정규 대표 바 = `W-금요일`
  - 즉 `naive_max != canonical_as_of` 가 픽스처 수준에서 성립한다(테스트가 이 전제를 먼저 단언한다)
  - **[HARD] A-6 전용 픽스처 조건**: `REFERENCE_STOCK`이 `W+1-월요일`의 **3행 중 하나로 반드시 포함**되고 `W-금요일` 바도 갖는다. 이 조건이 없으면 `SELECT MAX(Date) … WHERE Name = REFERENCE_STOCK`이 순진한 경로에서도 `W-금요일`을 내므로 **A-6의 대조 단언이 무음 통과**한다 — 되돌려도 실패하지 않는 대조는 대조가 아니다. 테스트는 이 전제(`naive_max_for_reference_stock == W+1-월요일`)를 먼저 단언한다.
- **When** 위 **6지점**이 각각 해석한 `as_of_date`를 수집하면
- **Then** **6개 값이 모두 `W-금요일`과 동일**하다 — 서로 같을 뿐 아니라 **정규 격자 값과 같다**.
- **And** **대조 단언**: 어느 한 지점을 순진한 `MAX(Date)`/`DISTINCT … DESC LIMIT 1` 경로로 되돌린 변형에서 이 AC가 **실패**한다. 지점별로 **6회** 반복해, 6개 교체가 전부 실제로 이루어졌음을 증명한다(1곳만 교체하고 나머지가 우연히 일치하는 상태를 검출).
- **And** 같은 조건으로 각 지점이 사용하는 히스토리 날짜 집합이 동일하다(집합 동등 비교).
- **And** **라이브 DB 비게이팅 스모크**: 라이브에서도 6개 값이 동일함을 확인하되, 이는 `xfail`이 아닌 **정보성 검사**로 표시한다 — 라이브에서 이 검사가 통과하는 것은 `naive_max == canonical`인 오늘의 우연이며 구현의 증거가 아님을 docstring에 명시한다.

#### AC-SGR-006-B — 격자·앵커 소비자 그룹 (2지점 / 1모듈)

기준일을 해석하지 않고 **격자 위에서 다른 것을 계산**하는 지점. `== W-금요일` 단언은 이 그룹에 원리상 적용되지 않으므로 각자의 계약으로 단언한다.

| # | 지점 | 실제로 계산하는 것 | 단언 |
| --- | --- | --- | --- |
| B-1 | `my_chart/analysis/sector_metrics.py:231` | rank_change 기준일 (`t`보다 이른 바) | 아래 B-1 단언 |
| B-2 | `my_chart/analysis/sector_metrics.py:346` | 부분 데이터 판정용 날짜별 행 수 가드 | 아래 B-2 단언 |

- **B-1 (`:231` → `anchor(t, 28)`)**
  - **Then** 반환값이 `anchor(t, 28)`과 **정확히 일치**하며 `history_grid`의 **원소**다(`assert prev_date in history_grid`).
  - **And** 반환값이 `as_of_date`보다 **엄격히 이르다**(`prev_date < t`) — 이 그룹에 `== W-금요일`을 요구하지 않는 이유를 테스트가 직접 표현한다.
  - **And** `fixture_max_ne_canonical`에서 CG-3이 배제한 `W+1-월요일`이 반환값이 **되지 않는다**.
  - **And** **대조 단언**: `LIMIT 1 OFFSET 3` 경로로 되돌린 변형에서 B-1이 **실패**한다 — 원시 날짜 집합에는 다중 날짜 주와 부분 데이터 날짜가 섞여 있어 오프셋 3이 격자 4주 전과 어긋난다. (경계값 자체는 AC-SGR-020 R2가 `28 <= (t−baseline).days <= 35`로 별도 고정한다.)
- **B-2 (`:346` → 공유 중앙값 가드)**
  - **Then** 반환 날짜 집합이 격자 모듈의 공유 가드가 산출한 집합과 **집합 동등**하다 — 자체 `GROUP BY Date` 쿼리로 독립 집합을 만들지 않는다.
  - **And** `grid_exclusions[]`에 오른 부분 데이터 날짜가 반환 집합에 **하나도 없다**.
  - **And** **대조 단언**: 자체 `GROUP BY Date … LIMIT weeks*2` 경로로 되돌린 변형에서 배제 대상 날짜가 집합에 **나타나** B-2가 실패한다.

#### 범위 밖 — `backend/services/meta_service.py:135`

**본 AC의 대상이 아니다.** 이 지점은 `stock_meta` 재구축을 위해 **일봉** `stock_prices`에서 기준 종목의 최신 거래일을 해석한다(`_rebuild`가 daily 커넥션에서 실행; weekly는 `:194`에서 `ATTACH`될 뿐이다). 본 SPEC의 정규 격자는 **주봉 전용**이므로 `fixture_max_ne_canonical`(주봉)로는 이 지점을 반증할 수 없고, 이 지점을 6-way 대조에 넣으면 **되돌려도 실패하지 않는 항목**이 생겨 그룹 A의 반증력이 희석된다.

- 처리: §1.2.2 정적 스캔 allowlist에 **사유와 함께** 등재한다(조용히 빠뜨리지 않는다). REQ-SGR-005의 금지 범위는 **주봉** `stock_prices`로 한정한다(D2).
- 일봉 측 격자(있다면)를 요구하려면 별도 REQ와 **일봉 픽스처**(`fixture_daily_max_ne_canonical`: 기준 종목의 일봉 최신 날짜가 부분 데이터 날짜인 조건)가 필요하다. 본 SPEC은 이를 **수행하지 않으며**, §7 **O-G7**로 등록한다.

- **현재 상태**: 실패 (가드가 `compute_sector_history` 1곳에만 존재)

### AC-SGR-007 — 달력 앵커링: 364일 = 52±1 바 (불변식 **TG-1**)

- **Given** 정규 격자 `history_grid`에서
- **When** `[t − 364d, t]` 구간의 바를 조회하면
- **Then** 바 개수가 `52 ± 1`이다.
- **And** `anchor(t, 7)`, `anchor(t, 28)`, `anchor(t, 91)`, `anchor(t, 182)`, `anchor(t, 364)`가 각각 `t − Nd` **이하**의 최근 격자 바를 반환하며, 반환값이 `t − Nd`를 초과하지 않는다.
- **And** `anchor(t, 28)`은 현행 `LIMIT 1 OFFSET 3`이 선택하던 2026-07-31이 **아니라** `t−28d` 이하 최근 격자 바를 반환한다.
- **현재 상태**: 실패 (최근 52행 = 139일)

### AC-SGR-008 — `weeks=N`의 의미 (불변식 **TG-4**)

- **Given** 정규 격자에서
- **When** `history(weeks=N)`을 호출하면 (N ∈ {8, 12, 26})
- **Then** 반환 날짜 개수가 정확히 N이고(가용 이력이 N주 이상일 때), 첫 날짜와 마지막 날짜의 간격이 `7×(N−1) ± 7`일이다.
- **And** N=12에서 실제 span이 36일이 아니라 **84 ± 7일**이다.
- **And** 가용 이력이 N주 미만이면 가용한 만큼만 반환하고 `requested_weeks`/`returned_weeks`를 함께 노출한다(조용한 축소 금지).
- **현재 상태**: 실패 (12주 = 36일)

### AC-SGR-009 — weekly column-name INSERT: fresh-DDL round-trip (Lesson #8)

- **Given** 새 임시 DB에 현행 `CREATE TABLE` DDL로 `stock_prices`를 생성하고
- **When** `_STOCK_PRICES_COLS`의 각 컬럼에 **서로 다른 식별 가능한 값**(컬럼명 해시 등)을 넣은 1행을 새 INSERT 경로로 기록한 뒤 `SELECT *`로 읽어오면
- **Then** 각 컬럼이 자기 값을 보유한다(시프트 0).
- **And** `relative_strength`에 대해서도 동일 round-trip이 성립한다.

### AC-SGR-010 — **legacy-ALTER 시나리오 round-trip** [HARD, Lesson #8 필수 게이트]

- **Given** `stock_prices`를 **`_STOCK_PRICES_COLS`보다 컬럼이 적은 과거 스키마**로 직접 `CREATE TABLE`하고
- **When** 멱등 `ALTER TABLE ... ADD COLUMN`으로 신규 컬럼을 **테이블 끝에 append**하여(따라서 라이브 컬럼 순서 ≠ `_STOCK_PRICES_COLS` 순서) 새 INSERT 경로를 실행한 뒤 `SELECT <각 컬럼명>`으로 읽어오면
- **Then** **각 컬럼이 자기 값을 보유한다** — `RS_Line`이 `Range` 값을 갖는 등의 시프트가 0건이다.
- **And** 동일 픽스처를 positional INSERT로 실행하면 시프트가 **발생함**을 함께 단언해, 이 테스트가 실제로 결함을 잡는 테스트임을 증명한다(테스트 자체의 반증 가능성 확보).
- **And** `relative_strength`에 대해서도 동일 시나리오를 커버한다.
- **근거**: Lesson #8 — `SPEC-SMA5-FILTER-001` v1.0.4에서 fresh-DDL만 테스트해 1.3M 행이 부패했다.

### AC-SGR-011 — positional INSERT 재도입 금지 (정적 스캔)

- **When** 다음 명령을 실행하면

```bash
grep -rn "INSERT OR REPLACE INTO [a-z_]* VALUES" my_chart/db/
```

- **Then** 출력이 **0행**이다.
- **And** `my_chart/db/weekly.py`에 `INSERT OR REPLACE INTO stock_prices (` 와 `INSERT OR REPLACE INTO relative_strength (` 리터럴이 각각 1건 존재한다.

### AC-SGR-012 — 주중 재적재 supersede (규칙 IG-1)

- **Given** ISO 주 W에 대해 월요일 바가 이미 적재된 DB에서
- **When** 같은 주 화요일 데이터로 weekly 적재를 실행하면
- **Then** 해당 ISO 주의 `(Name, Date)` 행이 종목당 **1행**(화요일)만 남는다.
- **And** ISO 주 W-1 이전의 기존 다중 날짜 행은 **삭제되지 않고 그대로 존재한다**(과거 이력 보존, A5).
- **And** supersede로 삭제된 행 수가 INFO 로그에 `{iso_week, deleted_rows}`로 기록된다.

### AC-SGR-013 — supersede 안전장치

- **Given** `--no-supersede` 플래그(또는 동등한 설정)가 활성이면
- **When** 같은 주 재적재를 실행하면
- **Then** 기존 행이 삭제되지 않고 현행과 동일하게 다중 날짜 행이 남는다(무력화 확인).
- **And** 이 경로에서도 AC-SGR-001(조회 시점 격자)은 여전히 통과한다 — 적재 보호와 조회 정규화가 **독립적으로** 성립함을 증명한다.

### AC-SGR-014 — 유니버스 단일 소스 (규칙 UN-1/UN-2)

- **Given** 유니버스 모듈이 로드되면
- **When** 각 종목의 `sector_major` / `sector_minor` / `market` 출처와 `market_cap` 출처를 조회하면
- **Then** 전자는 registry, 후자는 `stock_meta`에서만 조달된다.
- **And** 정적 스캔: `grep -rn "sector_major" backend/services/ my_chart/analysis/ | grep "stock_meta"` 결과가 유니버스 모듈 내부 조인 1곳 외에는 0행이다.

### AC-SGR-015 — 유효 유니버스 정의 (규칙 UN-3)

- **Given** registry(dedup) 2,559, `stock_meta` 2,546, 최신 정규 바 가격 존재 종목, 비-stale 종목의 4중 교집합에서
- **When** `effective_universe(as_of_date)`를 호출하면
- **Then** 반환 집합의 크기가 `<= 2,546`이고, 반환 집합의 모든 원소가 4개 조건을 **전부** 만족한다(원소별 단언).
- **And** registry에만 존재하는 종목(현행 13개)은 반환 집합에 **포함되지 않는다**.
- **And** 합성 픽스처로 "stock_meta에만 존재하는 종목"을 주입해도 교집합 결과에 포함되지 않는다(A6 — 방향 무관 교집합).

### AC-SGR-016 — registry 중복 제거 + 경고 (불변식 **UN-4**)

- **Given** registry 원본에 동일 `Code`가 2행 존재할 때 (실측: 아이톡시 052770)
- **When** registry를 로드하면
- **Then** 로드 결과에서 해당 `Code`는 **1행**이고, 전체 고유 `Code` 수 == 전체 행 수이다.
- **And** `WARNING` 레벨 로그에 `Code`와 종목명이 포함된 중복 경고가 **최소 1건** 기록된다(`caplog` 단언).
- **And** 회귀: 게임 섹터 구성 종목 수가 `/api/sectors`와 `/api/sectors/ranking`에서 **동일**하다.
- **현재 상태**: 실패

### AC-SGR-017 — stale 종목 배제 (규칙 UN-5)

> **이전 판의 결함 — REQ-SGR-014/015가 라이브에서 반증 불가였다.** 실측(2026-08-12): stale 32종목 ∩ `stock_meta` = **0**. 그런데 유효 유니버스는 이미 `∩ stock_meta`(UN-3)를 거치므로, **stale 필터를 한 줄도 구현하지 않아도** "반환 집합에 stale 0개"는 항상 참이다. 이전 판의 Then은 `∩ stock_meta`가 대신 만족시켜 주는 조건이었고, `last_updated` 금지(AC-SGR-018)와 결합하면 두 REQ의 반증 가능성이 합쳐서 0이었다.
>
> **해소**: `stock_meta`에 존재하면서 동시에 stale인 종목을 **합성 픽스처로 반드시 주입**하고, 그 종목의 배제를 단언한다. 이 조건에서만 stale 필터가 유일한 배제 사유가 된다.

- **Given** 합성 픽스처 `fixture_stale_in_meta`에서 — 다음 4종목이 **모두 `stock_meta`와 registry에 존재**하고 최신 일봉 거래일이 `T`일 때
  | 종목 | 종목별 일봉 `MAX(Date)` | `T − MAX(Date)` | 기대 |
  | --- | --- | --- | --- |
  | S-STALE | `T − 20d` | 20일 | **배제** |
  | S-EDGE14 | `T − 14d` | 14일 | **포함** (`> 14`만 배제 — 경계 방향 확정) |
  | S-EDGE15 | `T − 15d` | 15일 | **배제** |
  | S-FRESH | `T` | 0일 | 포함 |
- **When** `effective_universe(T)`를 호출하면
- **Then** 반환 집합이 `S-EDGE14`·`S-FRESH`를 **포함**하고 `S-STALE`·`S-EDGE15`를 **포함하지 않는다**(4종목 개별 단언).
- **And** **대조 단언**: stale 필터를 제거한 변형에서 `S-STALE`과 `S-EDGE15`가 반환 집합에 **나타난다** — 즉 배제가 `∩ stock_meta`가 아니라 stale 규칙에서 왔음을 증명한다. 이 대조가 없으면 AC 전체가 무의미하다.
- **And** 배제된 종목 수가 진단 필드 `stale_excluded_count`로 노출되며, 픽스처에서 정확히 `2`다.
- **And** **라이브 비게이팅 진단**: 라이브에서 `stale ∩ stock_meta`의 크기를 측정해 로그로 남긴다. 현재 값 **0**이며, 이 값이 0인 동안은 stale 규칙이 라이브 화면에 **아무 변화도 만들지 않음**을 docstring에 명시한다 — 리뷰어가 가시적 변화를 기대해서는 안 된다. 개수는 하드코딩하지 않는다(§7 O-G3 미결).

### AC-SGR-018 — `last_updated` 기반 판정 금지

> **이전 판의 결함**: 정적 스캔 단독이었고, AC-SGR-017과 마찬가지로 `∩ stock_meta`가 결과를 대신 만족시켜 **행동 단언이 없었다.** 판정 원천이 실제로 바뀌었는지 검증하지 못한다.

- **When** `grep -rn "last_updated" backend/ my_chart/ | grep -v "_test\|tests/" | grep -i "stale\|14"` 를 실행하면
- **Then** 출력이 **0행**이다.
- **And** **행동 단언 (판정 원천 검증)**: 합성 픽스처 `fixture_last_updated_divergent`에서 — `stock_meta.last_updated`가 **전 종목 동일 타임스탬프**(라이브 실태와 동일)이면서 일봉 종목별 `MAX(Date)`는 종목마다 다르게 설정한다.
  - `last_updated`로 판정하면 **아무도 stale이 아니다**(전 행 동일 타임스탬프이므로 판정력 0)
  - 일봉 `MAX(Date)`로 판정하면 `S-STALE`·`S-EDGE15`가 stale이다
  - **Then** `stale_excluded_count == 2`다 — 즉 판정이 `last_updated`가 아니라 일봉 `MAX(Date)`에서 왔음이 값으로 증명된다.
- **And** **대조 단언**: 판정을 `last_updated` 기반으로 되돌린 변형에서 `stale_excluded_count == 0`이 되어 위 단언이 **실패**한다.

### AC-SGR-019 — registry 전용 종목 진단 산출물

- **Given** `registry \ stock_meta` 차집합이 비어 있지 않을 때
- **When** 유니버스 모듈을 로드하면
- **Then** `WARNING` 로그에 차집합 크기와 종목명 목록이 기록된다.
- **And** 진단 결과가 `universe_diagnostics()` 반환값의 `registry_only[]`로 프로그램적으로도 접근 가능하다.

### AC-SGR-020 — **회귀 방지 AC**: 기대되는 변화의 명문화

아래는 전부 **올바른 결과**이며, 향후 리뷰어가 "되돌리는" 것을 막기 위해 테스트가 기대값으로 고정한다.

| # | 변화 | 단언 |
| --- | --- | --- |
| R1 | `history(weeks=12)` span이 36일 → 84±7일로 **늘어난다** | `assert 77 <= span_days <= 91` |
| R2 | rank_change 기준일이 `2026-07-31`(11일 전) → `t−28d` 이하 격자 바로 **이동한다** | `assert 28 <= (t - baseline).days <= 35` — **양쪽 경계 필수** |
| R3 | 게임 섹터 구성종목이 33 → **32**로 줄어든다 | `assert game_member_count == 32` + Code/Name dedup 분기 픽스처 (아래) |
| R4 | 정규 격자 바 개수가 원시 고유 날짜 수보다 **적다** | `assert len(grid) == 346 and len(raw_distinct_dates) == 385` (프로즌 스냅샷 기준) |
| R5 | 히스토리 차트의 x축 포인트 수가 줄어들 수 있다 | `assert len(history_grid_points) <= len(raw_row_dates)` — **단언으로 고정**. docstring 지시만으로는 검사되지 않는다 |

**R2 — 상한 경계가 없으면 규칙을 검증하지 못한다.** 이전 판은 `>= 28`만 단언했다. 그런데 `anchor(t, 364)`(=`t−364d` 이하 최근 바)도, 극단적으로 히스토리 첫 바도 `>= 28`을 만족한다 — **`anchor(t, 28)`을 `anchor(t, 364)`로 잘못 배선해도 통과한다.** 상한 `<= 35`가 "`t−28d` **이하**의 **가장 가까운** 격자 바"를 실제로 강제한다(정규 격자 간격 6–10일이므로 `t−28d` 직전 바는 최대 `t−35d` 근방이다).
- **And** **대조 단언**: `anchor(t, 91)` / `anchor(t, 364)`를 대신 쓴 변형에서 R2가 **실패**한다.

**R3 — 이전 판은 항진명제였다.** `assert game_member_count == unique_game_codes`는 dedup 구현 여부와 무관하게 좌우변이 같은 방식으로 산출되면 항상 참이다. 게다가 실측 결과 아이톡시(052770)는 **완전 중복 행**이므로 registry 원본에서 `Code` 기준 dedup과 `Name` 기준 dedup이 **둘 다 32**를 낸다(2026-08-12 실측: raw 33 / Code-dedup 32 / Name-dedup 32 / dedup ∩ `stock_meta` 32). **라이브 데이터로는 UN-4의 "Code 기준" 규칙을 검증할 수 없다.**

R3의 단언은 두 층이다:

- **(a) 라이브 값 고정**: `assert game_member_count == 32` — 실측값을 그대로 못 박는다. 좌우변이 같은 함수에서 나오지 않게 우변은 리터럴이다.
- **(b) Code-vs-Name 분기 합성 픽스처** (UN-4의 실제 게이트): 다음 두 행을 registry 픽스처에 주입한다.
  | Code | Name | 산업명(대) |
  | --- | --- | --- |
  | `X00001` | 가나전자 | 게임 |
  | `X00001` | **가나전자우** | 게임 |
  같은 `Code`, 다른 `Name`이다. **Code 기준 dedup → 1행 유지(게임 +1), Name 기준 dedup → 2행 유지(게임 +2).** 두 규칙의 결과가 갈리므로 이 픽스처에서만 UN-4가 반증 가능해진다.
  - **Then** 이 픽스처에서 게임 구성종목 수가 **base+1**이다.
  - **And** **대조 단언**: dedup 키를 `Name`으로 되돌린 변형에서 **base+2**가 되어 실패한다.
  - **And** 드롭된 행의 `Code`와 종목명이 WARNING 로그에 남는다(AC-SGR-016과 동일 경로).

각 항목은 **테스트 함수의 docstring에 "이것은 의도된 변화다"를 명시**하고, 릴리스 노트 문구를 함께 기재한다. 단 docstring은 **보조 설명일 뿐 검사 수단이 아니다** — R1~R5 전부가 실행 가능한 `assert`를 갖는다.

**프로즌 픽스처 의무**: R1~R5의 게이팅 단언은 전부 §3의 축소 스냅샷 픽스처 위에서 수행한다. 라이브 DB 실행은 비게이팅 스모크다(사유는 §3).

---

### AC-SGR-021 — 미분류 섹터 센티넬 단일화 (REQ-SGR-017) [잠재 발산 차단]

- **Given** 유니버스 모듈이 canonical sentinel 상수(예: `UNCLASSIFIED_SECTOR`)를 노출할 때
- **When** `backend/services/stage_service.py`와 `my_chart/analysis/sector_metrics.py`가 각각 미분류 기본값으로 해석하는 문자열을 수집하면
- **Then** 두 값이 **문자열 동등**하고, 둘 다 그 상수를 참조한다.
- **And** 정적 스캔: `grep -rn '"Unknown"' backend/services/stage_service.py` → **0행**. 하드코딩된 `"기타"` 기본값도 유니버스 모듈 외부에 남아 있지 않다.
- **And** **행동 단언**: `산업명(대)`가 NULL인 합성 registry 행을 주입한 픽스처에서, Stage 분포가 만든 섹터 키와 섹터 집계가 만든 섹터 키가 **일치**하고, 그 종목이 양쪽 모두에서 같은 섹터 그룹에 들어간다.
- **And** **대조 단언**: 두 경로가 다른 기본값을 쓰도록 되돌린 변형에서는 위 행동 단언이 **실패**한다(테스트의 반증 가능성 확보).
- **[중요] 가시적 변화 없음**: `stock_meta`의 NULL / 빈 문자열 / `'nan'` / `'기타'` 행이 현재 **0건**이므로 이 AC는 **합성 픽스처로만** 검증된다. 라이브 화면에는 어떤 변화도 나타나지 않는다 — 리뷰어가 가시적 변화를 기대해서는 안 된다.
- **And** 현재 0건임을 확인하는 진단 쿼리를 회귀 테스트에 남겨, 미분류 행이 처음 생기는 시점을 감지할 수 있게 한다.

## 2. 에지 케이스

| # | 상황 | 기대 동작 |
| --- | --- | --- |
| E1 | 주봉 DB가 비어 있음 | 격자 = 빈 리스트, `as_of_date = None`. 예외 없이 빈 응답 |
| E2 | ISO 주에 단 1개 날짜만 존재 | 그 날짜가 대표 바. 정상 |
| E3 | 연도 경계 ISO 주 (12/31 ↔ 01/01) | ISO 연도·주차 기준으로 그룹핑되어 동일 주로 묶인다. 테스트 픽스처 필수 |
| E4 | 최신 주가 토/일요일 바 | `is_partial_week` 판정이 요일이 아니라 **"금요일 바 부재 + 주 미종료"** 조건에 따른다 |
| E5 | 모든 날짜의 행 수가 중앙값 50% 미만 (전면 부분 데이터) | 격자를 비우지 않고 `grid_exclusions`에 전량 기록 + WARNING. 빈 격자 반환 시 상위 계층이 "데이터 없음" 처리 |
| E6 | registry에 3중 중복 | 첫 행 유지, 2건 드롭, 경고 2건 |
| E7 | `--no-supersede` + 주중 3회 실행 | 3개 날짜 행이 남고 조회는 여전히 1개만 반환 |
| E8 | ALTER로 append된 컬럼이 `_STOCK_PRICES_COLS`에 **없는** 경우 | column-name INSERT는 해당 컬럼을 건드리지 않고 NULL/기본값 유지. 예외 없음 |

---

## 3. 프로즌 픽스처 규약 [HARD — ②와 공유]

**문제**: 본 문서의 여러 AC가 라이브 DB의 값을 숫자로 못 박는다(AC-SGR-001 대표 날짜 3건, AC-SGR-002 예외 5건, AC-SGR-004 부분 데이터 날짜, AC-SGR-020 R3=32 / R4=346·385). 그런데 `/api/db/update`는 **주 1회 이상, 종종 주중에도** 실행된다(§2 A2). 즉 **게이팅 AC가 코드 변경 없이 붉어진다.** 드리프트는 이미 시작됐다 — 설계 문서는 2026-W32(08-07)를 2,548행으로 기록하지만 DB는 그 뒤로 더 늘었다.

**규약**:

0. **[HARD] 구축 시점은 `plan.md` M1.0이다 — 코드 변경보다 먼저다.** 게이팅 AC가 M1~M5에 걸쳐 있으므로 스냅샷이 마지막에 생기면 규약이 그 사이를 보호하지 못한다. **프로즌 픽스처 미구축 상태로 M1.1 착수를 금지한다**(②의 "골든 baseline 미캡처 상태로 M2 착수 금지"와 동일 강도).
1. **게이팅 AC는 프로즌 스냅샷 픽스처 위에서만 실행한다.** `tests/fixtures/frozen/weekly-2026-08-12/`에 축소 주봉/일봉 DB와 registry 축약본을 커밋한다. 위 실측값(346바 / 385날짜 / 예외 5건 / 게임 32)은 이 스냅샷의 값이며 스냅샷과 함께 고정된다.
2. **축소 기준**: 전 종목이 아니라 **재현에 필요한 최소 집합**을 담는다 — 예외 5쌍이 걸린 ISO 주 전후, 다중 날짜 주 21주 중 대표 3주, 부분 데이터 날짜 5건, 게임 섹터 33행(중복 포함), stale/경계 종목. 파일 크기를 리포에 담을 수준으로 유지한다.
3. **라이브 DB 실행은 비게이팅**이다. 동일 검사를 라이브에서도 돌리되 실패해도 CI를 막지 않으며, **불일치를 리포트로 남긴다** — 그 불일치가 "데이터가 갱신됐다"인지 "격자 규칙이 깨졌다"인지 판별하는 것이 리포트의 목적이다.
4. **스냅샷 갱신은 명시적 행위다.** 갱신 시 커밋 메시지에 사유와 새 실측값을 남기고, 변경된 기대값을 AC 본문에도 반영한다. 조용한 재생성을 금지한다.
5. `grid_version` 변경 시 스냅샷 기대값 재검토를 의무화한다.

**적용 대상 AC**: AC-SGR-001, 002, 004, 015, 017, 020 (라이브 값이 기대값에 들어가는 전량). AC-SGR-003, 009, 010, 012, 013, 016, 021은 이미 순수 합성 픽스처이므로 해당 없음.

---

## 4. 품질 게이트 (Definition of Done)

- [ ] AC-SGR-001 ~ AC-SGR-021 전부 PASS (**AC-SGR-006은 A/B 두 하위 절 모두** — 기준일 해석자 6지점 + 격자·앵커 소비자 2지점)
- [ ] **§3 프로즌 픽스처가 M1.0에서 구축됨** — 미구축 상태로 M1.1 착수 금지(§3.0 진입 게이트)
- [ ] **§3 프로즌 픽스처가 리포에 존재하고 게이팅 AC가 그 위에서 실행됨** — 라이브 DB 갱신으로 CI가 붉어지지 않음을 `/api/db/update` 1회 실행 후 재실행으로 확인
- [ ] **대조 단언 7종 PASS** — AC-SGR-002(anomalies 미기록), 005(`meta_service` 제외 정밀도 — `:196` 되돌림 시 스캔이 검출), **006-A(기준일 해석자 6지점 개별 되돌림 6회)**, **006-B(`LIMIT 1 OFFSET 3` 되돌림 · 자체 `GROUP BY Date` 되돌림)**, 010(positional INSERT), 017/018(stale 필터 제거 · `last_updated` 되돌림), 020 R2/R3(anchor 오배선 · Name dedup)
- [ ] **AC-SGR-006-A `REFERENCE_STOCK` 픽스처 조건 확인** — `fixture_max_ne_canonical`의 부분 데이터 3행에 `REFERENCE_STOCK`이 포함되어 A-6(`meta_service.py:196`) 대조가 무음 통과하지 않음을 전제 단언으로 검증
- [ ] **AC-SGR-010 (legacy-ALTER round-trip) PASS** — Lesson #8 [HARD] 게이트. 미통과 시 ship 금지
- [ ] 신규 격자·유니버스 모듈 라인 커버리지 >= 85%
- [ ] `pytest` 전체 회귀 통과 (기존 테스트 0건 실패)
- [ ] `.moai/specs/SPEC-SECTOR-GRID-001/progress.md` §E.2에 성능 baseline 실측값 기록 (§0.2)
- [ ] `grid_version = "canonical-v1"` 상수가 단일 위치에 정의되고 격자 규칙 변경 시 갱신 대상임이 주석으로 명시됨
- [ ] `@MX:ANCHOR` — weekly column-name INSERT 지점에 daily.py:267 패턴과 동일한 앵커 주석 부착
- [ ] `@MX:WARN` — supersede DELETE 지점에 `@MX:REASON` 동반 주석 부착
- [ ] ship commit에 frontmatter `status` 갱신 포함 (Lesson #6)
- [ ] 릴리스 노트에 AC-SGR-020 R1~R5의 "고장처럼 보이지만 올바른 변화" 문구 반영
- [ ] §7 미결 O-G1~O-G7이 사용자 확인 대기 상태로 progress.md에 명시 (O-G6 = `market_breadth.py:472` 격자 미적용 / **O-G7 = `meta_service.py:135` 일봉 기준일 격자 미적용** — 둘 다 AC-SGR-005 allowlist 잔류 항목)
