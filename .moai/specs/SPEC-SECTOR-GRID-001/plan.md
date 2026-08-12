# SPEC-SECTOR-GRID-001 Plan — 구현 계획

> 마일스톤은 **되돌리기 어려운 결정 순**으로 배열한다. 데이터 모델·인터페이스·적재 경로처럼 변경 가능성이 높은 결정을 먼저 두고, 기계적 치환(호출부 교체)을 뒤에 둔다.

---

## 1. [HARD] 결정 사항 (먼저 검토할 것)

| # | 결정 | 선택 | 근거 |
| --- | --- | --- | --- |
| D1 | 격자 산출 위치 | `my_chart/analysis/`에 신규 모듈 (예: `weekly_grid.py`). backend/services가 아니라 my_chart 계층 | 서비스 5곳 + analysis 2곳이 공유해야 하므로 하위 계층에 둔다 |
| D2 | 격자 반환 형태 | dataclass `WeeklyGrid { dates: list[str], latest: GridBar, history: list[GridBar], exclusions: [], anomalies: [], grid_version: str }` | 날짜 리스트만 반환하면 `is_partial_week`·제외 사유를 상위가 알 수 없다 |
| D3 | 미완성 바 노출 방식 | `latest_snapshot`(포함) / `history_grid`(제외) **두 뷰 분리** | 01 §3.3 CG-2가 "스냅샷엔 쓰되 히스토리엔 제외"를 요구 → 단일 리스트로는 표현 불가 |
| D4 | weekly INSERT 마이그레이션 방식 | **column-name INSERT** (Lesson #8 권장 default). `_STOCK_PRICES_COLS` 순서는 **변경하지 않는다** | `daily.py:267-276` 선례. 컬럼 순서 변경까지 겹치면 rollback 판정이 어려워진다 |
| D5 | 적재 보호 방식 | 동일 ISO 주 **supersede DELETE** (이번 실행이 기록한 주에 한정) + `--no-supersede` 플래그 | 고정 결정 "ingest prevention + 기존 행 보존". 과거 주는 건드리지 않는다 |
| D6 | 유니버스 모듈 위치 | `my_chart/analysis/universe.py` 신규. `registry.py`는 로더로 유지하고 dedup만 추가 | registry는 xlsx I/O 책임, universe는 교집합·stale 책임 — 분리 |
| D7 | 캐시 | 프로세스 내 `functools.lru_cache` 수준 메모이즈만. 키 = `(weekly_db_path, db_mtime)` | Lesson #5 — 사용 패턴(단일 사용자·수동 갱신)에서 TTL 캐시는 과설계 |
| D8 | `grid_version` | 문자열 상수 `"canonical-v1"`, 단일 정의 위치 | 01 §7.2 SN-5 캐시 무효화 키 |

---

## 2. 마일스톤 (되돌리기 어려운 순, 시간 추정 없음)

### M1 — 격자·유니버스 계약 정의 (되돌리기 가장 어려움: 데이터 모델)

#### M1.0 — 프로즌 스냅샷 픽스처 구축 [HARD · 코드 변경 **전**에 수행]

**게이팅 AC가 의존하는 기반이므로 그 AC들보다 먼저 존재해야 한다.** 이전 판은 이 작업을 "다른 회귀 작업보다 **먼저** 한다"고 적어 두고 **최종 마일스톤 M6에 배치**해, 지시와 순서가 서로 모순됐다 — M1~M5의 AC(001/002/004/015/017/020)가 라이브 값을 기대값으로 쓰는데 그 값을 고정할 스냅샷이 마지막에야 생기므로, 그 사이의 `/api/db/update` 한 번으로 CI가 코드 변경 없이 붉어진다. ②(`SPEC-SECTOR-AGGREGATION-001`)는 같은 작업을 **M1.0 `[HARD · 코드 변경 전]`**에 두었다. 동일한 배치로 맞춘다.

```
tests/fixtures/frozen/weekly-2026-08-12/
  weekly.db        ← 축소 주봉
  daily.db         ← 축소 일봉 (stale·경계 종목)
  registry.xlsx    ← registry 축약본 (게임 섹터 33행, 중복 포함)
  MANIFEST.md      ← 캡처 시각 · git SHA · 원본 DB mtime · 축소 기준 · 실측값 목록
```

- **축소 기준**: 예외 5쌍이 걸린 ISO 주 전후, 다중 날짜 주 21주 중 대표 3주, 부분 데이터 날짜 5건, 게임 섹터 33행(중복 포함), stale/경계 종목(`S-STALE`/`S-EDGE14`/`S-EDGE15`/`S-FRESH`). 리포에 담을 수 있는 크기를 유지한다.
- **고정되는 실측값**: 격자 346바 / 원시 고유 날짜 385 / 예외 5건(A1 `gap=5`, A2 4, A3 5, A4 5, A5 4) / 게임 32. `MANIFEST.md`에 함께 적어 "이 값이 무엇의 값인가"를 나중에 판별할 수 있게 한다.
- **[HARD] 진입 게이트: 프로즌 픽스처 미구축 상태로 M1.1 착수를 금지한다.** ②의 "baseline 미캡처 상태로 M2 착수 금지"와 동일한 강도다.
- 라이브 DB 동일 검사는 **비게이팅 스모크 + 불일치 리포트**로 병행한다(acceptance.md §3.3).

#### M1.1 — 격자 계약

- `WeeklyGrid` / `GridBar` / `UniverseSnapshot` dataclass 확정 (D2)
- RED: AC-SGR-001 ~ AC-SGR-004, AC-SGR-007, AC-SGR-008 테스트 작성 (합성 DB 픽스처)
- GREEN: `my_chart/analysis/weekly_grid.py` 구현
- 픽스처: 다중 날짜 주(2·3·4개), 금요일 부재 주, ISO 연도 경계, 부분 데이터 날짜(1행)

### M2 — 유니버스 규약 (되돌리기 어려움: 집계 모집단 정의)

- RED: AC-SGR-014 ~ AC-SGR-019, AC-SGR-021
- GREEN: `my_chart/analysis/universe.py` + `registry.py` dedup + 경고 로그
- stale 판정은 **일봉 DB** 종목별 `MAX(Date)` 사용 (`last_updated` 금지)
- **반증 가능성 확보 픽스처를 GREEN보다 먼저 만든다** — 라이브 데이터가 UN-4/UN-5를 반증하지 못하기 때문이다(실측: stale ∩ `stock_meta` = 0, Code-dedup과 Name-dedup이 둘 다 게임 32)
  - `fixture_stale_in_meta`: `stock_meta`에 있으면서 stale인 종목 + 14/15일 경계 종목 (AC-SGR-017)
  - `fixture_last_updated_divergent`: `last_updated` 전 행 동일 + 일봉 `MAX(Date)` 종목별 상이 (AC-SGR-018)
  - Code/Name dedup 분기 registry 픽스처: 같은 `Code` · 다른 `Name` 2행 (AC-SGR-020 R3)
- **미분류 센티넬 단일화 (REQ-SGR-017)**: canonical 상수 정의 후 `stage_service.py:57,67`의 `"Unknown"`과 `sector_metrics.py:250`의 `"기타"`를 그 상수로 교체. **O-G5(문자열 값) 선결** 필요. 가시적 변화 없음 — 합성 픽스처로만 검증

### M3 — weekly INSERT column-name 마이그레이션 [HARD, Lesson #8]

- RED: **AC-SGR-010 (legacy-ALTER round-trip)** 먼저 작성 — positional 경로에서 시프트가 **발생함**을 단언하는 대조 테스트 포함
- RED: AC-SGR-009 (fresh-DDL round-trip)
- GREEN: `my_chart/db/weekly.py:146-148`, `:295` column-name 변환
- `@MX:ANCHOR` 주석 부착 (daily.py:267 패턴 인용)
- 정적 스캔 AC-SGR-011 통과 확인

### M4 — 적재 supersede (되돌리기 어려움: 물리 삭제)

- RED: AC-SGR-012, AC-SGR-013
- GREEN: 적재 후 동일 ISO 주 이전 날짜 행 DELETE + INFO 로그 + `--no-supersede` 플래그
- `@MX:WARN` + `@MX:REASON` 주석 필수 (삭제 경로)
- **사용자 승인 대기 항목**: §7 O-G4

### M5 — 엔드포인트 배선 교체 (기계적)

**7개** 소비자 모듈을 공유 헬퍼로 교체한다(spec.md §1.2.1 인벤토리 — 이전 판의 6개는 `sector_advanced_service.py` 누락분이 빠진 수치였다):

| # | 대상 | 관용구 |
| --- | --- | --- |
| 1 | `backend/services/sector_ranking_service.py:24` | `MAX(Date)` |
| 2 | `backend/services/stage_service.py:25` | `MAX(Date)` |
| 3 | `backend/services/market_service.py:37` | `MAX(Date)` |
| 4 | `backend/services/meta_service.py:196` | `MAX(Date) FROM weekly.stock_prices` — **`:135`은 일봉이라 대상 아님**(§1.2.2 allowlist / O-G7) |
| 5 | **`backend/services/sector_advanced_service.py:40-45`** `_get_latest_date()` | `MAX(Date)` — **5개 엔드포인트 지배**, 파급 최대 |
| 6 | `my_chart/analysis/sector_advanced.py:98-108` `_get_dates()`, `:799` | `DISTINCT Date … ORDER BY Date DESC` |
| 7 | `my_chart/analysis/sector_metrics.py:231`, `:346` | `DISTINCT Date … DESC` / `GROUP BY Date … DESC` |

- **#5를 먼저 처리한다** — 단일 함수 교체로 `/sectors/bubble`·`/sectors/rrg`·`/sectors/history`·`/sectors/{name}/bubble`·`/market/treemap` 5개가 동시에 정상화되므로 위험 대비 효과가 가장 크다. 교체 후 `def _get_latest_date` 정의 자체를 **삭제**한다(남기면 재도입 경로가 산다).
- **#7의 `:231`은 단순 교체가 아니다** — `LIMIT 1 OFFSET 3`을 `anchor(t, 28)`로 바꾸는 **의미 변경**이며 AC-SGR-020 R2의 대상이다. 기계적 치환 항목과 분리해 별도 commit으로 둔다.
- RED: AC-SGR-005(3종 관용구 통합 스캔 + allowlist 상한 5 + `meta_service` 제외 정밀도 대조), **AC-SGR-006-A**(`fixture_max_ne_canonical` + 기준일 해석자 6지점 개별 되돌림 6회 — `REFERENCE_STOCK`을 부분 데이터 3행에 포함시키는 픽스처 조건 필수), **AC-SGR-006-B**(`:231`→`anchor(t,28)` / `:346`→공유 가드, 각자의 계약으로 단언)
- **교체는 7개 모듈 전부**이고, 검증 형태만 A/B 두 역할로 나뉜다(spec.md §1.2.1 역할 표) — "7개 소비자가 증명됐다"고 읽히지만 실제로는 5개만 증명하는 AC를 만들지 않기 위한 분할이다
- 서비스 단위 개별 commit (rollback 입도 확보)
- **`backend/services/sector_detail_service.py`는 대상이 아니다** — 기준일 쿼리 0건. 이 파일의 일봉 Stage 분류기는 ② 소관이다

### M6 — 회귀 게이트 + 성능 측정

- **프로즌 픽스처는 M1.0에서 이미 구축돼 있다** — 여기서는 게이팅 AC(001/002/004/015/017/020)가 실제로 그 위에서 실행되는지 **확인**한다. `/api/db/update` 1회 실행 후 재실행해 붉어지지 않음을 검증한다(②의 plan.md 최종 확인 항목과 동일 형태)
- AC-SGR-020 (R1~R5) 회귀 방지 테스트 — R5는 docstring이 아니라 `assert`로 고정
- §0.2 성능 baseline/목표 실측 → progress.md §E.2 기록
- 릴리스 노트 문구 작성

---

## 3. 기술 노트

### 3.1 ISO 주 그룹핑

SQLite에는 ISO week 함수가 없다. 두 가지 경로:

- (권장) Python 측에서 `datetime.date.fromisoformat(d).isocalendar()[:2]`로 그룹핑 — 날짜 목록만 가져오면 되므로 부하가 작다 (`SELECT DISTINCT Date FROM stock_prices` = 346행 수준)
- SQL `strftime('%W')`는 ISO 주와 규칙이 달라(연초 처리) **사용 금지**

### 3.2 부분 데이터 판정용 행 수

`SELECT Date, COUNT(*) FROM stock_prices GROUP BY Date` 1회로 날짜별 행 수를 얻는다. 중앙값은 조회 구간 기준(전체가 아님)이므로 함수 인자로 구간을 받는다.

### 3.3 column-name INSERT 변환 형태

```python
column_list = ", ".join(_STOCK_PRICES_COLS)
placeholders = ", ".join(["?"] * len(_STOCK_PRICES_COLS))
sql = f"INSERT OR REPLACE INTO stock_prices ({column_list}) VALUES ({placeholders})"
```

값 튜플 생성 순서는 `_STOCK_PRICES_COLS`와 동일하게 유지한다(현행 로직 변경 없음). 이 변환은 값 위치를 바꾸지 않으므로 **기존 데이터 재적재가 불필요**하다.

### 3.4 supersede 쿼리

```sql
DELETE FROM stock_prices
WHERE Date IN (:same_iso_week_dates_excluding_new)
```
대상 날짜 집합은 Python에서 ISO 주 계산으로 산출한다(§3.1). 이번 실행이 기록한 ISO 주 외의 날짜는 집합에 포함하지 않는다.

---

## 4. 리스크 분석

| 리스크 | 심각도 | 완화 |
| --- | --- | --- |
| **supersede가 의도치 않은 행을 삭제** | HIGH | 삭제 전 대상 날짜를 INFO 로그로 출력. `--no-supersede` 기본 OFF 여부를 사용자 승인(O-G4). 삭제 대상은 "이번 실행이 기록한 ISO 주"로 한정. run 전 DB 백업 권고 |
| **column-name 변환 시 컬럼명 오타** | HIGH | `_STOCK_PRICES_COLS`를 그대로 join하므로 수기 나열 금지. AC-SGR-009/010이 round-trip으로 검출 |
| 격자 도입으로 히스토리 포인트 감소 → 사용자 "데이터 잘림" 오인 | MEDIUM | AC-SGR-020 R1/R4 + 릴리스 노트 명시 |
| 6개 서비스 동시 교체 중 일부 누락 | MEDIUM | AC-SGR-005 정적 스캔 + AC-SGR-006 동등성 테스트 |
| ISO 연도 경계 버그 | MEDIUM | E3 픽스처 필수 |
| 격자 산출이 매 요청마다 전체 스캔 → 지연 | LOW | D7 메모이즈. §0.2 목표 미달 시 적용 |
| registry dedup으로 종목 수가 줄어 ②/③ 기대값이 흔들림 | LOW | AC-SGR-020 R3에 기대값 고정 |

---

## 5. mx_plan (MX 태그 계획)

| 위치 | 태그 | 내용 |
| --- | --- | --- |
| `weekly.py` column-name INSERT | `@MX:ANCHOR` | `_STOCK_PRICES_COLS` 순서가 라이브 컬럼 순서와 달라도 안전함을 명시. daily.py:267 선례 인용 |
| supersede DELETE | `@MX:WARN` + `@MX:REASON` | 물리 삭제 경로. 대상 한정 조건 명시 |
| `weekly_grid.py` 대표 바 선택 | `@MX:ANCHOR` | CG-1 계약 (ISO 주당 1바, MAX(Date)). fan_in >= 6 |
| `universe.py` 유효 유니버스 | `@MX:ANCHOR` | UN-3 4중 교집합. fan_in >= 3 |
| `grid_version` 상수 | `@MX:NOTE` | 격자 규칙 변경 시 갱신 의무 |

---

## 6. 검증 순서

1. `pytest tests/ -k "grid or universe"` (신규)
2. `pytest tests/` 전체 회귀
3. 정적 스캔 3종 (AC-SGR-005 / 011 / 018)
4. 라이브 DB 대상 read-only 스모크: TG-1/TG-2/TG-3 실측 재확인
5. 성능 측정 (§0.2)
