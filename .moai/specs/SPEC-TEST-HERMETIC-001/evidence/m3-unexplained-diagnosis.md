# M3 — 미설명 실패 진단 (REQ-006 / AC-006)

## 0. 스코프 — 관측된 실패만 진단 대상

M1 DB-less 실측(전체 20건) 중 정적 분석으로 설명되지 않았던 세트는
`tests/test_m6_gap_closure.py` 4건이 관측됐고, `tests/test_ac_sag_045_r1_r4_r5a.py`
1건은 **재현되지 않았다**(아래 §4). 관측되지 않은 실패에 대한 결함 주장은 하지
않는다(프로젝트 교훈 #9).

## 1. 진단 대상 4건 (관측 RED)

| # | 실패 ID | 관측 단언 (m1-red-full-run.log 발췌) |
|---|---------|--------------------------------------|
| 1 | `test_g20_rrg_market_filter_recomputes_rs_ratio` | `AssertionError: market=all/kospi 공통 섹터가 없다 — 비교 불가` |
| 2 | `test_g20_stock_bubble_market_filter_reduces_universe` | `AssertionError: market=kospi 종목 수(0)가 market=all(0) 과 같거나 많다` |
| 3 | `test_g23_stock_bubble_item_has_ac_sag_041_fields` | `AssertionError: stocks[] 가 비어 있다` |
| 4 | `test_g23_weight_in_sector_sums_close_to_one` | `AssertionError: weight_in_sector 가 전부 결측이다` |

공통 배경 로그(같은 로그의 Captured log 섹션):
`WARNING my_chart.analysis.universe:universe.py:145 registry 전용 종목(registry \ stock_meta) 2238종`
— stock_meta 조회가 사실상 비어 있었음을 시사했다.

## 2. 원인 (트레이스백 → 소스 대조로 확정)

4건 모두 같은 단일 원인으로 수렴한다:

- 버블/RRG 계산부 `my_chart/analysis/sector_advanced.py`의 `_get_stock_meta(db_path)`(154행)는
  주어진 DB(라우터 패치가 가리키는 프로즌 weekly.db — stock_meta 테이블 부재, sqlite_master
  실측: `('stock_prices',), ('relative_strength',)`만 존재)에서 `stock_meta` 조회가
  `sqlite3.OperationalError`로 실패하면 **config 파생 폴백 경로**로 재시도한다.
- 그 폴백은 166행 `daily_fallback = f"{DEFAULT_DB_DAILY}.db"` — `my_chart.config`의
  `DEFAULT_DB_DAILY`(=`Output/stock_data_daily`, 확장자 없음)가 **모듈 임포트 시
  `from my_chart.config import DEFAULT_DB_DAILY`로 sector_advanced 네임스페이스에
  복사**된 값이다. 이 이름은 라우터 레벨 패치(`backend.routers.*`) 밖에 있어서,
  DB-less 환경에서는 존재하지 않는 `Output/stock_data_daily.db`를 가리킨다.
- 결과: `stock_meta = {}` → 섹터별 종목 매핑 공집합 → bubble `stocks[]`/RRG `sectors[]`
  빈 응답 → 4건의 구조 단언 실패.
- 정상 환경(M0 기준선)에서 이 테스트들이 통과했던 이유: 같은 폴백이 **실제
  `Output/stock_data_daily.db`의 stock_meta(수천 행)** 를 읽어 환경 차이가 은닉됐다.
  즉 이 4건은 "프로즌 픽스처만으로 자급"하지 않고 프로덕션 DB에 의존하고 있었다.

보조 실측(디버깅 과정): 폴백 상수를 프로즌 daily.db **파일명**으로 패치하면 코드가
다시 `.db`를 붙여 `daily.db.db`가 되어 실패한다(`f"{DEFAULT_DB_DAILY}.db"` 구조).
→ 패치값은 확장자 없는 형태여야 한다. 이 실측이 최종 패치값
(`str(DAILY_DB.with_suffix(""))`)의 근거다.

## 3. 처분 및 수정

**처분: 테스트 계층 해소** — 프로덕션 코드 변경 없음(plan §D 원칙).

`tests/test_m6_gap_closure.py`의 모듈 스코프 `client` 픽스처에 1줄 패치 추가:

```python
patch("my_chart.analysis.sector_advanced.DEFAULT_DB_DAILY",
      str(DAILY_DB.with_suffix(""))),
```

- RED→GREEN: 수정 전 4건 RED(m1-red-full-run.log) → 수정 후
  `pytest tests/test_m6_gap_closure.py -q` → `11 passed, 1 warning in 13.45s`,
  종료 코드 0(직접 실행 확인). 전체 스위트도 DB-less GREEN
  (final-dbless-full-run.log: `1089 passed, 1 skipped, 95 deselected, 1 xpassed`).

**부산물 — AC-003 검증 테스트 신설**: 이 진단 과정에서 패치 커버의 회귀를 막는
검증 테스트가 요구됐다(AC-003). 본 진단이 산출 파일로서 신규 테스트 파일
`tests/test_hermetic_db_patch.py`(pkgutil 순회 기반 전 모듈 커버 검증 +
config 계층 커버 검증)를 명명한다 — 이것이 허용 파일 목상 "M3 진단이 이름 붙인
테스트 파일"의 근거다. 되돌림 RED 실측: conftest의 autouse 픽스처를
`autouse=False`로 일시 전환하면 본 테스트 2건이 모두 실패한다 —
verbatim 로그 `.moai/state/verify/develop-hermetic/ac003-revert-red.log`
(`2 failed` / 종료 코드 1), 복원 후 `2 passed`(종료 코드 0) 재확인.

## 4. 미재현 항목 — test_ac_sag_045_r1_r4_r5a.py

- 조사가 "미설명 5건"에 넣었으나 M1 DB-less 실측에서 **실패 0건**(1067 passed에 포함).
- 이 파일은 DB 경로를 패치 문자열 없이 `compute_sector_aggregates`에 명시 인자로
  전달하므로(조사 결과 #3), 라우터 상수 토폴로지의 영향을 받지 않는다. t8b 워크트리
  관측과의 불일치는 본 환경에서 재현되지 않았으며, 결함 주장·수정 모두 하지 않는다.
- REQ-006의 "관측된 각 실패" 진단 의무는 §1의 4건으로 완결된다.

## 5. 증거 파일 대장

| 증거 | 경로 |
|------|------|
| RED 원문(20건 전체) | `.moai/state/verify/develop-hermetic/m1-red-full-run.log` |
| 최종 GREEN 원문 | `.moai/state/verify/develop-hermetic/final-dbless-full-run.log` |
| AC-003 되돌림 RED 원문 | `.moai/state/verify/develop-hermetic/ac003-revert-red.log` |
| 소스 근거 | `my_chart/analysis/sector_advanced.py:154-193`(`_get_stock_meta`), `:166`(폴백) |
