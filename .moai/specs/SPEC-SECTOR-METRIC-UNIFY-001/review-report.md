# SPEC-SECTOR-METRIC-UNIFY-001 — 코드 리뷰 보고서

- 리뷰어: `review-tjvce8` (칸반 review 컬럼)
- 일자: 2026-08-18
- 범위: `777f044..eef55e0` — 9커밋 / 19파일 / +2108 −45 (main 직접, origin과 `0 0`)
- 모드: `/moai review --deep` — 4 헌트 렌즈 → 3인 적대적 패널(2-of-3 quorum) → 종합
- 증거: `.moai/state/verify/review-tjvce8-smu001/`

## 판정

**차단 — sync 진행 불가.**

구현 설계는 대체로 건전하고 M4 지표 통일(불일치 N=18→0)이라는 본 목적은 달성됐다.
차단 사유는 두 가지다: main에 **적색 테스트 1건**과 **라이브 타입 오류 1건**이 병합돼
있고, 그 둘이 각각 AC-028·AC-029의 판정 근거를 무효화한다. `progress.md` §E.3의
**21/22 PASS 집계는 액면 그대로 성립하지 않는다**.

검증 강도 구분: 아래 B1·B2 및 F3/F4/F5/F12/F13/F23은 리뷰어가 명령을 직접 실행해
출력을 관측했다. 그 외는 3인 패널의 2-of-3 quorum 통과 항목이며 리뷰어 재현은 없다.

---

## 차단 사유

### B1 — `test_bubble_schema_nullable.py`가 main에서 실패 상태 (리뷰어 재현)

`backend/tests/test_bubble_schema_nullable.py:103`

```
FAILED test_bubble_schema_nullable.py::test_live_response_fields_are_scalars
E  AssertionError: 패션.period_return: float 관찰값과 다르다: None
   assert False = isinstance(None, float)
1 failed, 5 passed
```

M4가 유입시킨 `None`을 `isinstance(value, float)`가 거부한다. 이 파일 docstring이
"M4 이후 null 유입이 시작되면 완화된다"고 예고했으나 완화가 적용되지 않았다.
경로상 in-range 커밋은 M3 `d16cb65` 1건뿐이다.

**파급**: `progress.md` §E.2가 AC-SMU-028의 되돌림 증거로 이 파일의 `1 failed`를
인용한다. 주입 전에 이미 `1 failed`이므로 그 증거의 판별력은 0이다 — lessons #9
(동어반복) 계열. §E.3의 M4/M5 게이트 집계(33+22+21+46=122)에 이 파일 6건이
빠져 있어 감지되지 않았다.

**권고**: 두 번째 단언을 "스칼라 또는 None"으로 완화하되 필드별 허용 집합을 픽스처
관측치에 고정하고, AC-028 되돌림 증거를 별도 관측자로 재수립.

### B2 — `SectorBubbleChart.tsx:124` 라이브 타입 오류 + AC-029 증거 공허 (리뷰어 재현)

```
src/components/SectorAnalysis/SectorBubbleChart.tsx(124,77):
error TS2345: Argument of type 'number | null' is not assignable to parameter of type 'number'
```

M3이 `period_return`을 nullable로 넓혔으나 소비처 `sectorReturnColor(v: number)`가
갱신되지 않았다.

**런타임 결과가 조용하다**: `sectorReturnColor(null)` → 밴드 `v > -3 && v < 3`에서
`null`이 0으로 강제 변환돼 참 → 결측 섹터가 **정상 보합과 동일한 중립 회색**(#9CA3AF)
으로 렌더된다. `missing` 점선 테두리는 `trading_value` 기준이라 이 경우를 덮지 않는다.
픽스처 실데이터의 패션·헬스케어가 해당한다.

**왜 안 잡혔나**: 루트 `frontend/tsconfig.json`이 `files: []` + project references라
`tsc --noEmit`이 **0개 파일을 컴파일**한다(`--listFiles` 실측 0줄). §E.3의 `tsc: exit 0`은
공허한 관측이고, AC-029의 "`npx tsc --noEmit`이 통과한다" 요구도 공허하게 충족됐다.

**심각도 범위 정정**: `tsc -b`(= `npm run build` 경로)는 exit 2이나, 오류 30건 중
**본 SPEC 귀속은 정확히 1건**이고 29건은 무관 pre-existing(`stage.test.ts`,
`ChartGrid` 계열)이다. "이 SPEC이 빌드를 깼다"가 아니라 "이미 깨진 빌드가 이 오류를
가렸다"가 정확한 기술이다.

**권고**: `sectorReturnColor`와 x축 accessor에 null 분기 명시(결측을 별도 시각 채널로
분리), CI 타입체크를 `tsc --noEmit -p tsconfig.app.json` 또는 `tsc -b`로 교체.

---

## 미해결 3건 처분 의견

### ① AC-029 되돌림 관측자 부재 — Gap 유지 부당, 즉시 닫을 수 있음

두 원인이 겹쳐 있고 둘 다 수정 가능하다.

1. B2의 공허한 tsc 설정 (루트 tsconfig가 0개 컴파일)
2. **관측자여야 할 테스트가 타입을 스스로 무력화 중**:
   - `SectorBubbleChart.m5.test.tsx:65` — `trading_value: null as unknown as number`
   - `MetricTextParity.m7.test.tsx:93-94` — `excess_return`·`rs_avg`·`period_return` 4필드 동일 이중 캐스트

이 5개 캐스트는 타입이 좁던 시절의 잔재다. `tsconfig.app.json`은 `include: ["src"]`이고
테스트가 `src/` 아래이므로 검사 범위 안이다. 캐스트를 제거하면 `types/bubble.ts`를
`number`로 되돌렸을 때 하드 tsc 오류가 발생한다 — 관측자가 복원된다.

§E.2의 "타입 증명 파일 시도 후 철회"는 불필요한 우회였다. 기존 픽스처를 정직하게
만드는 것이 정답이다. M3이 타입만 넓히고 캐스트를 정리하지 않은 **미완 마이그레이션**이
근본 원인이다.

### ② 커버리지 미측정 — sync 보측 타당, 단 B1 선행

`coverage` 미설치는 환경 문제이며 SPEC 로직과 무관하므로 sync 보측이 타당하다.
다만 현재 B1로 인해 커버리지 명령이 실패하거나 부분 결과를 낸다.
**순서: B1 수정 → 커버리지 측정 → DoD 체크박스 정리.**

### ③ 사다리 refs 라이브 미검증 — 배포 차단 사유 아님

리뷰어가 픽스처에서 직접 재계산했다. `return_window_days = {1w:11, 1m:32, 3m:95}`
(anchor(t,N) 관용 · O-A8)이며, 섹터합/시장 비율 1.47 / 1.16 / 1.05가 각각
11÷7 / 32÷28 / 95÷91과 일치한다 — **이중 계상도 창 불일치도 없다.** 데이터는 정확하고
사다리가 어긋나도 시각 스케일만 나빠진다. 잔여 불확실성("대형주 편중 픽스처로 보정")은
§E.3에 이미 공시된 갭이다.

**단, 별건으로 F7은 배포 전 처리 권고** — `SECTOR_PERIOD_SIZE_LADDER`의 vMin/vMax를
읽는 커밋된 테스트가 0건이라 라이브 재보정 시 회귀를 잡을 장치가 없다.

---

## 중점 검토 3건 판정

### ① 파티션 계약 재기술 — 의미 변화는 반영, 그러나 정확 등식 가용 지점에서 약화 (리뷰어 실측)

재기술 자체는 시장별 AG-5라는 새 의미를 담고 `all ⊇ kospi ∪ kosdaq` 방향도 맞다.
두 가지가 문제다.

**(가) 최강 경계 사례가 무단언으로 통과한다.** (b)절의 이중 `if name in side` 가드
때문에 양 시장 모두에서 빠진 섹터는 루프 본문에 진입하지 않는다. 실측:

```
섹터수 all=18 kospi=15 kosdaq=17 both=15
  디스플레이: kosdaq에만 3.4405e+03 < all 5.7643e+03   → (b) 통과
  스마트폰  : kosdaq에만 3.6497e+03 < all 1.3597e+04   → (b) 통과
  패션      : 양쪽 응답 모두 부재                        → 단언 0건 실행
             (kospi excluded count=1, kosdaq excluded count=4)
```

하필 AG-5 재기술이 겨냥한 사례가 패션이다.

**(나) 정확 등식이 무비용으로 가능한데 부등식에 그쳤다.** M5가 봉투에 실은
`excluded[].count` + `member_count`로 세 경계 섹터 전부 엄격 등식이 성립한다:

```
디스플레이 18 == 4 + 14   OK
스마트폰   17 == 4 + 13   OK
패션        5 == 1 +  4   OK
```

docstring의 "완화가 아니다"는 성립하지 않는다.

**정상 참작**: `test_bubble_characterization_snapshot`이 9조합의 정확 집합을 별도
고정하므로 레포 전체로는 집합 회귀 방어선이 남는다. 따라서 심각한 구멍이 아니라
**재기술이 자기 주제를 스스로 검사하지 않는 결함**이며 medium이 적정선이다.

**권고**: (b)절을 `excluded[]` 기반 정확 단언으로 교체 — "한쪽에만 존재하는 섹터는
누락된 시장의 `excluded[]`에 `insufficient_members`, `count < 5`로 등재".

### ② 섹터 전용 사다리 분리 — 새 불일치를 만들었고 이미 착지했다

방향은 옳다(두 차트 단위가 실제로 다르다). 방식이 문제다.

- `SizeLadder` 타입에 단위 판별자가 없어 두 상수가 **구조적으로 완전 교환 가능**하다.
- `sizeLegendRefs(period, rMin, rMax, ladder?)`의 기본값이 하필 원 스케일
  `PERIOD_SIZE_LADDER`다. **가정이 아니라 이미 오배선 중이다** —
  `bubbleRadius.test.ts:103`이 섹터 반지름(`SECTOR_BUBBLE_R_*`)을 넘기면서 사다리를
  생략해 stock 사다리를 검증하고 있다(F11).
- 새 상수의 vMin/vMax를 읽는 커밋된 테스트가 0건이다(F7). m5 테스트는 refs 파생
  문자열만 단언한다.
- **`spec.md:133` REQ-SMU-023이 여전히 `PERIOD_SIZE_LADDER`를 지목하며 "경로만 보고
  SPEC-SECTOR-DISPLAY-UNIFY-001로 옮기지 말 것"이라고 못박고 있다**(F4). 구현은 그
  상수를 그대로 두고 새 상수를 만들었는데 `spec.md`·`acceptance.md` 어느 쪽도
  개정되지 않았다(HISTORY 최신 0.5.0, 범위 내 두 파일 커밋 없음).

결과적으로 **후속 개발자가 요구를 성실히 따를수록 종목 버블을 깨뜨리는 구조**다.
AC-SMU-018을 문자 그대로 평가하면 FAIL이다 — 실측 1w 분포 `[2.2e3, 9.4e5]`는
`PERIOD_SIZE_LADDER['1w'] = [1e10, 1e12]` 안에 없다. §E.3의 AC-018 PASS는 **개정된
의도**에 대한 판정이지 **기술된 AC**에 대한 판정이 아니다.

**권고**: REQ-SMU-023 / AC-SMU-018을 `SECTOR_PERIOD_SIZE_LADDER`로 개정 + HISTORY 행
추가. `ladder`를 필수 인자로 승격하거나 `SizeLadder`에 `unit: 'krw' | 'eok'` 브랜드
필드를 추가해 타입 수준에서 분리.

### ③ 원 복원 래퍼 — 같은 함정을 남겼고 발견 가능성이 역전돼 있다

현재 섹터 렌더 경로(범례·툴팁)는 전부 래퍼를 타므로 **활성 버그는 없다.** 구조가 문제다.

- 올바른 `formatSectorTradingValue`는 `SectorBubbleChart.tsx` 안의 **비-export 모듈
  상수**인 반면, 틀린 `formatTradingValueEok`은 **export돼 있고 docstring이
  "거래대금(원) → 억원 표기 … 범례·툴팁 공용"이라 주장**한다. 억원 데이터를 만나는
  다음 개발자가 import 목록에서 발견할 수 있는 유일한 포맷터가 틀린 쪽이다.
- 후보 함정이 이미 존재한다: `StageStock.trading_value`가 같은
  `compute_trading_value_by_period` 출처의 억원 값을 단위 표기 없이 노출하고,
  소비자 측 변환이 레포 어디에도 없다.
- 단위 표기가 네 곳에서 일관되게 **틀려 있다**(F3, 리뷰어 확인):
  `backend/schemas/envelope.py:92`, `my_chart/analysis/sector_metrics.py:234`,
  `frontend/src/types/bubble.ts:9`, `docs/sector-ux/01-data-contract.md:176`
  — 전부 "원"인데 실제 값은 억원(`my_chart/db/daily.py:152`
  `VolumeWon = HLC * Volume / 1_0000_0000`).

즉 **문서를 신뢰한 개발자가 M4→M5.5에서 한 번 출하된 0억 회귀를 그대로 재현한다.**

**권고**: `formatSectorTradingValue`를 `bubbleRadius.ts`의 `SECTOR_PERIOD_SIZE_LADDER`
옆으로 옮겨 export하고 `formatTradingValueEok` docstring 정정. 네 곳 단위 표기를
"억원(1e8 KRW)"으로 정정. **올바른 선택지를 발견 가능한 쪽으로 만드는 것**이 핵심이다.

---

## 추가 확인 — backend 컬렉션 오류 2건

**결론(무관·pre-existing)은 맞고, 진단은 부정확하다.** (리뷰어 재현, 상세:
`.moai/state/verify/review-tjvce8-smu001/collection-error-rootcause.md`)

- 두 파일 단독 수집은 정상(3건 / 16건). 전체 디렉토리에서만 깨진다 → 정적 import
  결함이 아니라 **수집 순서 의존**이다.
- 심볼은 실제로 존재한다(`my_chart/db/weekly.py:301 generate_price_db`, `:388 generate_rs_db`).
- 근본 원인: `backend/tests/test_ai_report_router_deep_mode.py:64-70`이 import 시점에
  `types.ModuleType("my_chart")` 스텁을 `sys.modules`에 심는 전역 변조.
  `types.ModuleType`은 `__file__`/`__spec__`이 없어 이후 수집 모듈의
  `from my_chart.db.weekly import ...`가 `(unknown location)`으로 실패한다.
  스텁은 `my_chart` 미import 시에만 등록되므로 순서 의존이다.
- **본 SPEC 무관 확인**: 범위가 `db_service.py` / `services/__init__.py` /
  `db/weekly.py` / `test_ai_report_router_deep_mode.py` 중 어느 것도 건드리지 않았다.

**파생 주의**: `pytest backend/tests` 디렉토리 일괄 실행은 수집 단계에서 중단되어
**0건 실행**으로 끝난다. 디렉토리 스위프 근거의 "통과" 주장은 귀속 불가.
§E.3의 백엔드 증거는 파일 단위 호출이므로 이 함정에 걸리지 않는다(확인함).

---

## 확정 결함 목록 (패널 2-of-3 quorum 통과, 29건)

`[R]` = 리뷰어 직접 재현 · 그 외는 패널 검증.

### 봉투 파리티 파손

| ID | 심각도 | 위치 | 요지 |
|---|---|---|---|
| F5 `[R]` | high | `sector_advanced_service.py:128` | `as_of_is_partial_week`가 버블 `True` / 랭킹 `False` — 같은 트리·같은 요청에서 상반. 버블은 `as_of=<최신 봉 날짜>`, 랭킹은 `as_of=None`(오늘)로 각각 그리드 생성 |
| F15 | medium | `sector_advanced_service.py:98` | `compute_rank_change=False`로 버블 `data[].rank_change`·`baseline_date`가 구조적 null (랭킹은 실값). 어떤 테스트도 `bubble["data"]`를 읽지 않음 |
| F6 | high | `test_bubble_ranking_parity.py:72` | 파리티 테스트가 랭킹 라우터가 선언하지 않는 `as_of` 쿼리를 전송 → FastAPI가 무시 → 날짜 고정이 존재하지 않음 (F5의 발생 기제) |
| F27 | medium | `test_bubble_ranking_parity.py:105` | AC-010이 버블 봉투를 규율하는데 `benchmark`·`data[]` 단언이 **랭킹 응답**에서만 수행 (AC-009에서 고친 항진 결함과 동형) |

### 단위 계약 잔재

| ID | 심각도 | 위치 | 요지 |
|---|---|---|---|
| F3 `[R]` | high | envelope.py:92 / sector_metrics.py:234 / bubble.ts:9 / 01-data-contract.md:176 | 실제 억원인데 네 곳 전부 "원" 표기. 0억 회귀의 재발 벡터 |
| F22 | low | stage_service.py:88 / 02-screen-flow.md:736 / bubbleRadius.ts:108 외 | Stage 스키마 단위 미표기 · 설계문서 VZ-2 표가 구 원 스케일 · 포맷터 docstring 오기 |
| F14 | medium | `sector_advanced.py:25`, `bubble.ts:7` | `excess_return` 주석이 "KOSPI 대비"이나 M4가 기준을 시장별 상한 시총가중 유니버스로 변경 |

### 관측자 부재 / 약화

| ID | 심각도 | 위치 | 요지 |
|---|---|---|---|
| F7 | high | `bubbleRadius.ts:38` | `SECTOR_PERIOD_SIZE_LADDER` vMin/vMax를 읽는 커밋 테스트 0건 — AC-018 게이트가 run을 넘겨 생존 못 함 |
| F9 | medium | `SectorBubbleChart.tsx:247` | 툴팁 측 0억 수정에 관측자 없음. 형제 `StockBubbleChart.m5.test.tsx:38`은 tooltip formatter를 실제 호출하는 패턴 보유 |
| F8 | medium | `SectorBubbleChart.m5.test.tsx:19` | 픽스처가 구 원 단위(5e11~1e14)라 SECTOR 사다리 vMax=1e6에서 전부 rMax 클램프 → 사이징 판별력 0 |
| F11 | medium | `bubbleRadius.test.ts:103` | AC-SUX-039 섹터 범례 테스트가 섹터 반지름 + stock 사다리 조합을 검증 중 |
| F12 `[R]` | medium | `test_sectors_bubble_market_contract.py:143` | 양 시장 모두 부재 섹터(패션) 무단언 통과 |
| F13 `[R]` | medium | 〃`:148` | 부등식 그침 — `excluded[]`로 정확 단언 가능 |
| F29 | low | 파리티/특성화/m5 다수 | 죽은 skip 분기 · 결측 판별을 `value[7]` 대신 지름 14로 · 단언식/진단식 불일치 등 묶음 |

### SPEC 장부 정합

| ID | 심각도 | 위치 | 요지 |
|---|---|---|---|
| F4 `[R]` | high | `spec.md:133` | REQ-SMU-023 / AC-SMU-018이 `PERIOD_SIZE_LADDER` 지목, 구현은 미수정 + 신규 상수. 양 문서 미개정 |
| F23 `[R]` | medium | `progress.md:247` | §E.2 되돌림 표에 **004·005·008 행 부재**인데 §E.3은 "AC-001~011 전부 되돌림 RED 관측" 선언. 실집계는 최소 18/22 + 4 Gaps |
| F26 | medium | `acceptance.md:129` | AC-015가 집합 등식을 요구하고 부등식류를 명시 금지했으나, 시장별 AG-5로 kospi 15/18·kosdaq 17/18. 관측자는 되더 후 등식 단언 |
| F24 | medium | `acceptance.md:75` | AC-005가 픽스처에 없는 섹터(기계·금융)만으로 기술 — 되돌림 RED 관측 불가 |
| F25 | medium | `acceptance.md:54` | AC-002(b) "진짜 방어선" 되돌림 미실시 + 명명 섹터 2건 픽스처 부재 + 특성화 EXPECTED가 post-M4로 재생성돼 M4 경계 불변성 증명 소실 |
| F28 | low | plan.md:141 외 | M5.5 결정이 "기존 테스트 갱신 원장"에만 기록 · AC-027 문자 그대로 FAIL · AC-001 29섹터 vs 검증 18섹터 · DoD 10칸 전 미체크 |

### 성능 / 견고성

| ID | 심각도 | 위치 | 요지 |
|---|---|---|---|
| F17 | medium | `sector_advanced_service.py:90` | 요청마다 `sectormap-original.xlsx` 재파싱(비캐시 경로, 실측 0.29s). 구 경로는 SQLite만 접근 |
| F18 | medium | 〃`:133` | 소비자 없는 봉투 `data[]` 추가로 페이로드 28,707B 중 28,611B — 프론트 타입에 `data` 필드 자체가 없음 |
| F16 | medium | 〃`:77` | docstring의 "등가중 폴백" 약속이 실제로 없음 — `daily_db_path=None`이면 전 지표 null로 퇴화 |
| F19 | medium | `sector_metrics.py:522` | 멤버 1명만 VolumeWon을 가져도 합계가 present. coverage/valid_counts는 하드코딩 None |
| F20 | low | `sector_advanced_service.py:60` | `excluded[]`에 `insufficient_members`(sectors[]에서 빠짐)와 `excess_return_missing`(남음)이 혼재 |
| F21 | low | `routers/sectors.py:90` | catch-all이 xlsx 파싱 실패까지 `weekly_db_not_ready` 503으로 보고 |

---

## 반증된 후보 (quorum 미달 — 기록 보존)

- **거래대금 이중 계상 의심 (리뷰어 자체 가설)** — 반증. 창이 11/32/95일이라 비율이
  정확히 설명됨. 반도체 1w 941,379가 멤버 VolumeWon 합과 정확 일치, (Name,Date) 중복 0건.
- **`trading_value_window_days` 누락 의심 (리뷰어 자체 가설)** — 반증. 랭킹도 동일하게
  생략하고 같은 문서화된 기본값(= `return_window_days`)을 쓴다. 불일치 아님.
- `market` vs `market_filter` 대소문자 불일치 — 라우터 `pattern` 검증으로 HTTP 경로에선
  불가능. docstring "대소문자 무관" 문구만 정정 대상.
- nullable 확장에 API 버전 신호 부재 — 외부 소비자 증거 없음, 내부 2소비자는 동일 커밋 갱신.
- 빈 date 엣지 테스트가 봉투 상태 미단언 — 분기 A 확정이므로 status 단언으로 충분(§D E-6 규정).
- RS 결측 합성 테스트의 AG-5·시장 축 부재 — AG-5는 시험 대상 기제가 아님, 되돌림 RED 입증됨.
- 랭킹 null 섹터 픽스처 고정이 취약 — 특성화 스위트의 의도된 계약.
- REQ-SMU-026 "M4 외 수치 불변" 위반 — `산출 수치`는 백엔드 값을 지칭, M5.5는 프론트만 변경.

---

## 권고 처리 순서

1. **B1** — `test_bubble_schema_nullable.py` 단언 완화 + AC-028 되돌림 증거 재수립
2. **B2** — `sectorReturnColor` null 분기 + CI 타입체크를 `-p tsconfig.app.json`으로 교체
3. **AC-029 캐스트 5개 제거**(m5.test:65, MetricTextParity.m7.test:93-94) → 관측자 복원
4. **SPEC 개정** — REQ-SMU-023/AC-018 → `SECTOR_PERIOD_SIZE_LADDER`, AC-015 → 시장별
   집합 등식, §E.3 집계에 004/005/008 Gaps 반영, HISTORY 행 추가
5. **F7 관측자 신설**(사다리 vMin/vMax) — 배포 전 권고
6. F3/F22 단위 표기 정정 + `formatSectorTradingValue` export 이동
7. 나머지(F14~F29)는 sync 또는 SPEC-SECTOR-DISPLAY-UNIFY-001로 분류

## 리뷰 방법론 공시

- 4 헌트 렌즈(backend correctness / unit contract / test strength / traceability)를
  read-only 병렬 실행 → 3인 적대적 패널(OCCURRENCE / IMPACT / DEFENSES, REFUTE 편향)이
  후보 전량에 투표 → 2-of-3 quorum 통과분만 확정 결함으로 승격.
- **패널 독립성 한계 공시**: 투표자가 후보를 개별이 아니라 묶음으로 받았으므로,
  건별 3인 패널 대비 건별 독립성이 다소 약하다. quorum 규칙 자체는 보존됐다.
- 비만장일치(2/3) 항목은 확신도를 medium으로 상한 처리했다.
- `--patch` 미사용 — 패치 초안을 작성하지 않았다. 리뷰는 읽기 전용이다.
