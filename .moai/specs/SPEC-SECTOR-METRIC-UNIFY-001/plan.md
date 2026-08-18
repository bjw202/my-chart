# SPEC-SECTOR-METRIC-UNIFY-001 — 구현 계획

> 원본: `.moai/plans/rs-purring-key.md` (사용자 승인 완료). 본 문서는 그 계획의 SPEC 형식 전사이며 재기획이 아니다.

## §A 핵심 결정 (되돌리기 어려운 순)

| # | 결정 | 대안 | 왜 이것인가 |
|---|---|---|---|
| DEC-1 | 단일 원천 = `compute_sector_aggregates` | `compute_sector_ranking` | 레거시 `SectorRank`에 거래대금 필드 없음 / `sector_metrics.py:993-996`이 `or 0.0`으로 동일 0-대체 결함 재현 / 초과수익률이 KOSPI 기준 |
| DEC-2 | 초과수익률 벤치마크 = 정의 B(상한 시총가중 유니버스) | A(KOSPI 지수), C(KOSPI·등가중) | 섹터도 상한재배분 시총가중 → 같은 구성 기준끼리 비교 / All 시장에서 KOSPI만 잣대로 쓰는 A의 결함 없음 / Bubble X축 라벨이 이미 B를 서술 |
| DEC-3 | 결측 섹터를 드롭하지 않고 nullable로 통과 | 필터링 제거 | `MetricCell.tsx:4-11` ER-1/ER-2가 "이유 없이 사라짐"을 명시적으로 금지. null Y는 점이 안 찍혀 0으로 바닥에 찍히는 현행보다 낫다 |
| DEC-4 | 결측 사유는 봉투 `data[]`로 전달, 아이템에는 스칼라만 | `MetricValueModel`을 아이템에 탑재 | `SectorBubbleChart.tsx:127`이 스칼라를 ECharts 튜플로 펼침 → 파괴적 변경 |
| DEC-5 | `compute_sector_bubble` 존치 + deprecation | 삭제 | `detect_sector_transitions`(`sector_advanced.py:951`)가 `/market/overview`(`market_service.py:158-161`)로 소비 |
| DEC-6 | `daily_db_path`는 키워드 기본값 인자 | 위치 필수 인자 | 실행 스캔으로 확정한 단일 위치 인자 호출 **3곳**(`tests/test_ac_sag_037_endpoint_date_consistency.py:87`·`:184`, `tests/test_consumer_dates.py:438`)이 깨짐. 스캔 출력은 spec.md REQ-SMU-008에 리터럴로 고정 |
| DEC-8 | `date`는 기존 지역 변수 `_get_latest_valid_date(...) or ""`(`:58`)를 그대로 쓰되, `if date:` 진리값 가드를 **함께 이식** | 가드 없이 그대로 전달 | 같은 파일의 종목버블 선례(`:136`)가 이미 가드를 갖는다. 가드 없이 빈 문자열이 `compute_sector_aggregates`의 필수 `date`로 들어가면 라우터의 포괄 `except Exception`(`routers/sectors.py:90-94`)이 **503**으로 바꾸거나, 성공하더라도 섹터 0개를 조용히 반환한다 |
| DEC-7 | M8(레거시 `sectors[]` 이관)은 **본 SPEC 밖** | 함께 처리 | 잔여가 시장·기간별 **상수**여서 순서 불변·x=0 선만 이동. 별도 판단 대상 |

## §B 마일스톤 순서의 근거 — [HARD] 재논의 금지

두 순서가 load-bearing이며 구현 중 임의로 바꾸지 않는다.

### B-1. M0(특성화)이 반드시 먼저 랜딩된다

변경 **후에** 쓴 특성화 테스트는 변경 전 동작이 아니라 **변경이 만들어낸 값을 고정**한다. 그러면 diff를 증명할 기준선이 사라진다. M0은 손대지 않은 트리에서 GREEN을 관측하고 **단독 커밋**으로 먼저 들어간다. 이후 모든 diff가 이 파일로 증명된다.

> 이 순서 결함은 **본 프로젝트 직전 SPEC의 plan-audit에서 실제로 적발된 항목**이다. 기록해 두어 재논의되지 않게 한다.

### B-2. M4만 숫자를 바꾼다 — blast radius 국소화

- M1 = 테스트만 (프로덕션 무수정)
- M2 = 배선만 (동작 불변)
- M3 = nullable 스키마 확장 (값 불변)
- **M4 = 전환 — 수치가 바뀌는 유일한 단계**
- M5 = 봉투 필드 채움 (섹터 값 불변)
- M5.5 = 사다리 정합 측정 (백엔드 값 불변, 표시 스케일만)

따라서 **M4 밖에서 숫자가 움직이면 그건 다른 것이 깨진 신호**다. 이 성질이 회귀 진단 비용을 크게 낮춘다.

---

## §C 마일스톤 (원본 순서 그대로)

### M0 — 특성화 테스트 (선행, 단독 커밋) · Priority High

- `backend/tests/test_bubble_characterization.py` 신설: 고정 픽스처(`tests/fixtures/frozen/aggregation-2026-08-11`, `AS_OF="2026-08-11"`)로 9개 (period, market) 조합의 **현재** bubble 산출값을 리터럴로 고정
- 두 엔드포인트의 현재 **불일치**를 명시적으로 기록하는 테스트 — 수정 후 이 단언은 뒤집힌다
- 기존 패턴 참고: `tests/test_ac_sag_030_rs_avg.py`(변이-발산 테스트 `:145` 포함), `tests/test_sectors_bubble_market_contract.py:33-48`(TestClient + patch 관용)
- **킥오프 시 G-1/G-2(§E) 먼저 확인** — 픽스처가 결측 경로를 못 태우면 합성 DB(`backend/tests/test_sector_advanced.py:19-147` 관용)로 전환

### M1 — RED · Priority High

- `tests/test_bubble_ranking_parity.py` + `tests/test_bubble_rs_missing_exclusion.py` 신설. **프로덕션 코드는 손대지 않는다.** 실패 건수와 섹터별 델타가 M0 기준선과 일치하는지 확인
- parity 테스트(`@parametrize` period × market 9조합): `rs_avg`/`excess_return`/`period_return`/`trading_value`가 `data[]`와 일치, 섹터 집합 일치, `market_filter`가 요청 반영, 봉투에 `benchmark`·`data` 존재
- **`rs_avg` 기간 불변** 테스트 추가 (INV-3 회귀 방어)
- exclusion 테스트: 10종목 중 2종목이 `relative_strength` 행 없는 합성 DB — 분모가 8인지, 0-대체 값(분모 10)과 다른지, 전원 결측 시 `0.0`이 아니라 `None`인지

### M2 — 배선만 (동작 불변) · Priority High

- `get_sector_bubble`에 `daily_db_path: str | None = None` **키워드 기본값** 추가 (`backend/services/sector_advanced_service.py:41-45`)
- `backend/routers/sectors.py:89`에서 `DAILY_DB_PATH` 전달 — 이미 import돼 있고(`:13`) ranking·history·detail·종목버블은 전부 넘기는데 bubble만 빠져 있다

### M3 — 스키마 nullable 확장 · Priority High

- `SectorBubbleItem`의 4개 수치 필드를 `float | None`으로 (`backend/schemas/sector_advanced.py:23-26`)
- `frontend/src/types/bubble.ts:6-8`을 `number | null`로 동시 확장
- 결측 섹터를 **드롭하지 않는다**(DEC-3). 프론트는 이미 null 내성이 있다(`SectorBubbleChart.tsx:113`이 `trading_value == null`을 점선 테두리로 처리)
- `MetricValueModel`을 아이템에 싣지 **않는다**(DEC-4)

### M4 — 전환 (숫자가 바뀌는 유일한 단계) · Priority High

`get_sector_bubble` 본문을 `compute_sector_aggregates(...)` 호출 + 투영으로 교체.

**`date` 해석 (DEC-8) — 새로 만들지 않는다.** 교체 대상 함수가 이미 `date = _get_latest_valid_date(weekly_db_path) or ""`(`backend/services/sector_advanced_service.py:58`)를 갖고 있고, 같은 파일의 종목버블 선례가 이 지역 변수를 `if date:` 가드 아래에서 소비한다(`:136`). **그 가드를 함께 이식한다.**

```python
date = _get_latest_valid_date(weekly_db_path) or ""
aggregates = []
excluded = []                               # ← M5가 봉투로 넘길 값. 가드 밖에서 반드시 초기화한다
if date:                                    # ← :136 선례의 진리값 가드
    result = compute_sector_aggregates(
        weekly_db_path, date,
        daily_db_path=daily_db_path,
        market=market, as_of=date, period=period,
        compute_rank_change=False,          # D11 — 아래 근거
    )
    aggregates = result.aggregates          # 투영 원천 컨테이너
    excluded = result.excluded               # E-6 분기 B의 구별 관측량 원천
```

- **[HARD] `excluded`를 가드 밖에서 초기화하는 것은 스타일이 아니라 E-6의 전제다.** M5가 `envelope_fields(..., excluded=excluded)`로 배선하는데 이 이름이 가드 안에서만 바인딩되면, 가드가 거짓일 때 `NameError`가 나고 라우터 포괄 `except Exception`이 그걸 **503**으로 바꾼다 — E-6이 막으려던 바로 그 결과다. 동시에 분기 B의 필수 관측량("가드된 경우 봉투 `excluded[]` 길이 0")도 성립하지 않는다.
- 두 이름의 가드 밖 초기값이 곧 E-6의 기대 상태를 만든다: `aggregates = []` → 빈 `sectors[]`, `excluded = []` → 봉투 `excluded[]` 길이 0.

- **`compute_rank_change=False` 필수(D11)**: 기본값이 `True`(`sector_metrics.py:889`)라 `anchor(t, 28)` 기준일로 1단 재귀 재집계(`:906-908`)가 돌지만, 버블 투영은 `rank_change`를 **소비하지 않는다**. 기본값을 두면 폐기될 필드를 위해 요청당 집계가 2배가 된다.
- 가드가 없으면 빈 `date`가 필수 인자로 들어가 라우터 포괄 `except Exception`(`backend/routers/sectors.py:90-94`)에 의해 **503**이 되거나, 성공하더라도 섹터 0개를 조용히 반환한다. AC-SMU-015는 유효 date 픽스처로 돌고 E-3은 빈 *kosdaq 유니버스*를 다루므로 이 경로는 어느 쪽도 덮지 않는다 → **E-6 신설**.

| `SectorBubbleItem` | 원천 (`result.aggregates[i]`, 이하 `a`) | 산출 위치 |
|---|---|---|
| `period_return` | `a.returns[p].value` | `sector_metrics.py:502-521` (결측 제외 후 가중 재정규화) |
| `excess_return` | `a.excess_returns[p].value` | `:843-844`, `_excess_returns :596-609` |
| `rs_avg` | `a.rs_avg.value` | `:529` — **기간 무관** (INV-3 충족) |
| `trading_value` | `a.trading_value[p].value` | `:523-527` (VolumeWon 기간 누적) |

- 기간 키 `"1w"|"1m"|"3m"`이 라우터 쿼리값과 동일해 변환표 불필요(종목버블 `:138-139` 매핑표와 대비)
- `compute_sector_bubble` 존치(DEC-5) + deprecation docstring + 정적 스캔 테스트
- **M0 특성화는 이 커밋에서 뒤집거나 삭제하고, 변경 전후 값을 커밋 본문에 기록한다**
- `MIN_SECTOR_MEMBERS=5` 필터가 새로 적용되지만 현재 최소 섹터가 방산 N=18이라 **사라지는 섹터 0개**(실측 확인)

### M5 — 봉투 정상화 · Priority High

- `envelope_fields(...)`로 응답 구성 (D4). **`excluded=excluded`를 반드시 함께 넘긴다** — M4 스케치가 가드 밖에서 초기화해 둔 그 이름이며, E-6 분기 B의 구별 관측량이 여기서 나온다
- 레거시 `date`/`period`/`market`/`sectors` 키 유지 — `tests/test_response_contract.py:327`이 이 4개를 고정

### M5.5 — 사다리 정합 확인 (M4 완결 조건) · Priority High

`PERIOD_SIZE_LADDER`(`frontend/src/components/SectorAnalysis/bubbleRadius.ts`)의 `vMin`/`vMax`가 M4 이후 실제 거래대금 분포를 담는지 **측정**하고, 벗어나면 재산출한다(AC-SMU-018 / 갭 G-3).

> 프론트 파일이지만 본 SPEC에 잔류한다. 거래대금 단위를 바꾸는 당사자가 M4이고, 이걸 프론트 SPEC으로 미루면 **백엔드만 머지된 구간에서 모든 버블이 한쪽 끝으로 뭉친 채 배포된다.** 표시 개선이 아니라 M4의 완결 조건이다.

### M6 / M7 — 형제 SPEC으로 이관

프론트 표시 통일(M6)과 Table 기간 토글 실동작(M7)은 **`SPEC-SECTOR-DISPLAY-UNIFY-001`** 소관이다.

**절단 근거 (재논의 금지)**: 절단면은 승인된 원본 계획서 자신이 이미 그어 둔 것이다 — `.moai/plans/rs-purring-key.md`의 M6 헤더가 *"백엔드 독립, 먼저 배포 가능"*이라고 명시한다. 예산을 맞추려 자른 것이 아니라 원래 둘이던 것을 하나로 묶어 뒀던 것이며, 배포 순서(백엔드 선행 → 프론트 후행)와도 일치한다.

### M8 — 잔여 (별도 판단) — **본 SPEC에서 구현하지 않음**

M5 이후에도 레거시 `sectors[]`는 KOSPI 기준이라 Table과 Bubble이 **시장·기간별 상수**(`상한가중 벤치마크 − KOSPI 지수`)만큼 차이 난다. 모든 섹터에 동일하게 적용되므로 **순서는 같고 x=0 선만 이동**한다. 오늘의 섹터별 제각각 불일치보다 훨씬 작은 잔여. `sectors[]`를 `data[]`로 이관할지는 별도 결정 사항으로 이월한다(spec.md §5 참조).

---

## §D 의도적으로 갱신해야 하는 기존 테스트

| 파일:라인 | 갱신 사유 |
|---|---|
| ~~`SectorAnalysis.market-delivery.test.tsx:60,68,79`~~ | M7 → `SPEC-SECTOR-DISPLAY-UNIFY-001`로 이관 |
| ~~`SectorRankingTable.test.tsx:70`~~ | M6 → `SPEC-SECTOR-DISPLAY-UNIFY-001`로 이관 |
| ~~`SectorDetailPanel.test.tsx:65-67`~~ | M6 → `SPEC-SECTOR-DISPLAY-UNIFY-001`로 이관 |
| `backend/tests/test_sector_advanced.py:277-334` | 주석으로 "이 함수는 더 이상 `/api/sectors/bubble`를 지원하지 않음" 명시 (M4) |
| `backend/tests/test_bubble_characterization.py` (M0 신설) | M4 커밋에서 뒤집거나 삭제 |
| `tests/test_sectors_bubble_market_contract.py::test_bubble_market_partition_is_exact` | **M4 런타임 등재 (2026-08-18, 사용자 승인 — 계획 누락 보완)**: 기존 "kospi+kosdaq == all" 분할 등식은 AG-5 미적용 시에만 참인 계약. M4가 버블에 봉투와 동일한 AG-5(시장별 멤버쉽 기준, AC-SMU-015/REQ-SMU-012)를 적용하면서 디스플레이·패션(단일 시장 유니버스 미달)이 시장별 응답에서 제외되어 등식이 구조적으로 깨짐 — M0의 bubble-only 관측(kospi {디스플레이,스마트폰,패션})이 이미 예측한 귀결. 재기술: 양쪽 존재 섹터는 엄격 등식 유지 + 한쪽만 존재 섹터는 존재 쪽 < all 엄격 부등식 + (a) 집합 최소 1개 단언 (완화 아닌 AG-5 의미론 반영) |
| `frontend/src/components/SectorAnalysis/__tests__/SectorBubbleChart.m5.test.tsx` (AC-SUX-039 범례 3종) | **M5.5 런타임 등재 (2026-08-18, 사용자 승인 — 사다리 분리의 귀결)**: 참조 리터럴이 구 사다리(원 단위 기준) 값이었으나 M5.5가 섹터 전용 사다리 SECTOR_PERIOD_SIZE_LADDER(억원 VolumeWon 기준 재산출)를 신설하면서 갱신. 함께 M4가 만든 표시 회귀(억원 trading_value를 원 단위 가정 포맷터에 통과해 범례·툴팁이 0억으로 렌더)를 섹터 차트 호출부 원 복원으로 해소 |

이 목록 밖의 기존 테스트가 깨지면 **의도치 않은 회귀**로 취급한다.

---

## §E 리스크 / 미검증 갭 — [HARD] AC가 이것들이 성립한다고 가정하지 않는다

| # | 갭 | 처분 |
|---|---|---|
| G-1 | 고정 픽스처 `tests/fixtures/frozen/aggregation-2026-08-11`에 **RS 결측 종목이 결측 경로를 태울 만큼 들어있는지 미확인** | M0 킥오프에서 확인. 부족하면 합성 DB(`backend/tests/test_sector_advanced.py:19-147` 관용)로 전환 |
| G-2 | `daily.db`의 `VolumeWon`이 **3M 창을 덮을 만큼 과거까지 채워져 있는지 미확인** | M0 킥오프에서 확인. 부족하면 합성 DB로 전환하고 3M 거래대금 AC를 합성 픽스처 기준으로 재기술 |
| G-3 | `PERIOD_SIZE_LADDER` 상수(`bubbleRadius.ts:27-31`, `1w` 1e10~1e12 / `1m` 5e10~5e12 / `3m` 1e11~1e13)는 SPEC-SECTOR-UX-001에서 **VolumeWon 스케일 기준으로 설계된 것으로 읽힌다**. 그렇다면 M4 이후 값이 이미 사다리 안에 들어오고 원본 계획이 요구한 "재산출"이 불필요할 수 있다. **양쪽 다 미측정** | M4 직후 실제 분포를 측정한 뒤 결정(AC-SMU-018이 측정을 게이트로 요구). 측정 없이 상수를 손대지도, 그대로 두지도 않는다 |
| G-4 | `ThemeAnalysis/ThemeRankingTable.tsx` 동일 표시 패턴 여부 — **`SPEC-SECTOR-DISPLAY-UNIFY-001`로 이관** | 본 SPEC 소관 아님 |
| G-6 | 교차 언어 상수 추출(백엔드 `_RS_TOP_THRESHOLD = 80.0` ↔ TS `80`) — **`SPEC-SECTOR-DISPLAY-UNIFY-001`로 이관** | 본 SPEC 소관 아님 |
| G-8 | **E-6의 빈 `date` 분기 미확정.** 가드 제거 시 (A) 즉시 예외 → 라우터 포괄 핸들러가 503, (B) `_load_weekly_snapshot(conn, "")`가 빈 스냅샷 → 전 섹터 `no_members` → `aggregates=[]` 정상 반환 중 어느 쪽인지 미측정. `compute_weekly_grid(weekly_db_path, "")`(`sector_metrics.py:794`)가 먼저 던질 가능성이 남아 있다. **분기 B면 되돌림 결과가 곧 기대 상태여서 RED가 안 나온다**(동어반복) | **M4 착수 전 실측 1회**로 확정하고 관측된 분기에 맞춰 되돌림 기술. 분기별 구별 관측량은 acceptance.md § E-6 측정 게이트에 사전 기재됨 |
| G-7 | **AC-SMU-025의 순서 단언 명령 미확정**(run-phase 기계 사항). 기재된 두 명령은 M0 SHA 확정과 stat 출력까지만 하고 **위치를 비교하지 않는다** → `git merge-base --is-ancestor <M0_SHA> <M4_SHA>`가 필요. 또 "프로덕션 파일 0개"는 M0 diff가 자기 테스트 파일을 반드시 포함하므로 그대로는 술어가 아니다 → **경로 필터**(`tests/`·`backend/tests/` 밖 경로 0개)로 정의해야 한다 | run-phase 착수 시 두 술어를 명령으로 확정 |
| G-5 | 백엔드 커버리지 측정은 이 프로젝트에서 `pytest --cov`가 `ImportError: numpy`로 실패한다. 동작 형태는 `coverage run --source=my_chart,backend -m pytest <files>` → `coverage report` (lessons #9 부수 발견) | DoD 커버리지 측정 시 이 형태를 쓴다 |

---

## §F 자기 검증 명령

```bash
# 백엔드
cd backend && pytest tests/ -k "bubble or ranking or sector" -v
# 프로젝트 루트 테스트
pytest tests/ -k "bubble or ranking or sector or aggregation" -v
# 프론트
cd frontend && npx tsc --noEmit
cd frontend && npx eslint src/components/SectorAnalysis src/utils --max-warnings=0 > /tmp/lint.out 2>&1; echo $?   # 파이프 금지(종료코드 은폐)
cd frontend && npx vitest run --exclude "e2e/**"
```

> **[HARD] zsh 주의**: grep 스캔은 반드시 `--include='*.py'`처럼 **따옴표로 감싼다**. 따옴표 없는 `--include=*.py`는 zsh가 grep보다 먼저 글롭하고 중단시킨다. `bash -n`은 이것을 잡지 못한다.

---

## §G 안티패턴 (lessons.md 유래)

- **#9** 대조 단언은 "테스트를 썼는가"가 아니라 **"되돌렸을 때 RED를 관측했는가"**로만 판정한다. 단언의 양변이 같은 함수/표현식에서 오면 무효다. 최소 한 변은 검증 대상 프로덕션 경로에서 와야 한다.
- **#9** 부분집합 크기 부등식(`<=`)은 대개 항진명제다 → 프로즌 리터럴 등식 + strict 부등식으로 대체.
- **#9** 명세의 스캔 명령은 실제로 실행해 **관측된 출력을 리터럴로 고정**한다. 손으로 옮겨 적으면 드리프트한다.
- **#6** ship 커밋 또는 직후 sync 커밋에서 frontmatter `status`를 갱신한다.

## §H 교차 참조

- spec.md §2 불변 조건 / §5 범위 밖
- acceptance.md — AC 전량 + 되돌림 절차
- `.moai/plans/rs-purring-key.md` — 승인된 원본
