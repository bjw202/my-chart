# SPEC-SECTOR-AGGREGATION-001 Plan — 구현 계획

> 마일스톤은 **되돌리기 어려운 결정 순**으로 배열한다. 지표 의미·응답 계약 같은 고변경 결정을 앞에, 라우터 배선 같은 기계적 작업을 뒤에 둔다.

---

## 0. 착수 전 차단 항목 (BLOCKING)

| ID | 사항 | 상태 | 차단 대상 |
| --- | --- | --- | --- |
| **O-A8** | 미완성 주 바와 기간 계산의 정합 (①의 O-G2 인수) | **미결 — 차단 중** | **M3 (벤치마크·순위)** — REQ-SAG-012(동일 날짜 창)·REQ-SAG-021(`anchor(t,28)`)이 직접 의존. 미결이면 BM-6이 무증상으로 깨진다 |
| **O-A7** | 최소 구성수 5 규칙의 Bump 적용 | **미결** | M6의 `/sectors/history`, 그리고 **③의 AC-SUX-019 / AC-SUX-056 R5** |
| ~~O-A1~~ | RS-Ratio 롤링 정규화 | **해결 (2026-08-12)** — 정규화 미적용 | M4 차단 해제 |
| ~~O-A3~~ | 주식수 상수 가정 + "현재주가" 출처 | **해결** — `warnings[]` 명시 + daily 최신 `Close` | M4 차단 해제 |
| ~~O-A4~~ | 거래대금의 기간 정의 | **해결** — 기간 토글과 동일 창 | M5 차단 해제 |
| ~~O-A6~~ | `coverage_ratio` 입도 | **해결** — 지표별 + 최상위 최소값 | M1 차단 해제 |
| ①의 close | `SPEC-SECTOR-GRID-001` `status: completed` | 선행 | 전 마일스톤 |

M1·M2·M4·M5·M6은 진행 가능하다. **M3은 O-A8 결정 후에만 착수한다.** O-A7은 M6 착수 전 그리고 ③ 착수 전에 해소한다.

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

#### M1.0 — 골든 baseline 캡처 [HARD · 코드 변경 **전**에 수행]

**어떤 코드도 건드리기 전에 현행 응답을 떠 둔다.** AC-SAG-045 R4("현행 대비 상승")·R5("min-max 대비 증가")는 비교 대상이 필요한데, 본 SPEC은 기존 구현을 **교체**하고 어느 SPEC도 구 구현을 보존하지 않는다. 구현이 끝난 뒤에는 비교할 값이 존재하지 않으므로 **지금이 유일한 캡처 시점**이다.

```
tests/fixtures/golden/pre-sector-ux/
  ranking-all-1w.json      ← GET /sectors/ranking (현행 무파라미터 응답)
  ranking-all-1m.json
  ranking-all-3m.json
  stage-overview.json      ← GET /stage/overview (현행)
  MANIFEST.md              ← 캡처 시각 · git SHA · DB 스냅샷 식별자 · 캡처 명령
```

- **프로즌 DB 스냅샷 위에서 캡처한다**(acceptance.md §8). 라이브 DB로 뜨면 baseline 자체가 드리프트해 비교가 무의미해진다.
- `MANIFEST.md`는 필수다 — 나중에 "이 baseline이 무엇과 비교되는 값인가"를 판별할 수 없으면 R4/R5가 다시 실행 불가능해진다.
- **M1 완료 조건에 포함한다. baseline 미캡처 상태로 M2 착수를 금지한다.**

#### M1.1 — 응답 계약 + 결측 표현

전 응답에 파급되는 형태 결정을 먼저 고정한다.

- D6 결측 표현 형태 확정 → 전 지표 필드에 적용
- **O-A6 반영**: `coverage: {rs, nh, stage, chg, trading_value}` + 최상위 `coverage_ratio = min(...)`, `valid_counts` 동형. AG-7 임계는 최상위 최소값에 적용
- `SectorAggregate` / `BenchmarkInfo` / `ResponseEnvelope` dataclass + Pydantic 모델 정의
- RED: AC-SAG-036, AC-SAG-038, AC-SAG-043, AC-SAG-008(지표별 커버리지)
- GREEN: 스키마 정의 + 빈 값으로 채워 반환(값 로직은 M2 이후)

### M2 — 가중·집계 코어 (지표 의미 변경)

- RED: AC-SAG-001 ~ AC-SAG-010
- GREEN: `my_chart/analysis/weighting.py` + `sector_metrics.py` 집계 교체
- `sector_metrics.py:42-44` 거짓 주석 정정
- 커버리지·`effective_n`·`capped_members` 산출

### M3 — 벤치마크 + 순위/정규화 (지표 의미 변경) [**O-A8 선결**]

- **선결**: O-A8 (미완성 주 바일 때 1W 수익률의 날짜 쌍). REQ-SAG-012·REQ-SAG-021이 직접 의존하며, 미결 상태로 진행하면 BM-6이 **무증상으로** 깨진다 — 섹터와 벤치마크가 각자 다른 뷰(`latest_snapshot` vs `history_grid`)를 쓰면서 응답에는 두 날짜가 모두 실려 겉보기로는 일치한다
- RED: AC-SAG-011 ~ AC-SAG-023
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

- **프로즌 픽스처 확인** (acceptance.md §8): 게이팅 AC(002 / 013 / 024 / 030 / 045 R3·R4·R5)가 `tests/fixtures/frozen/weekly-2026-08-12/` 위에서 실행되는지 확인. `/api/db/update` 1회 실행 후 재실행해 붉어지지 않음을 검증한다
- AC-SAG-044: `hasattr`-only 블록 대체 + 되돌림 검출 3케이스 증명
- AC-SAG-045: R1·R3~R8 회귀 방지 테스트 (**R2는 삭제** — `10<=k<=24`는 29섹터의 34~83%로 아무것도 게이팅하지 않았고 AC-SAG-013의 `18±3`과 중복이었다)
- R4/R5는 M1.0에서 캡처한 골든 baseline과 비교한다
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
