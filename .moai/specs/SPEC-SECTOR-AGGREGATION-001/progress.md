# SPEC-SECTOR-AGGREGATION-001 Progress

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-08-12
tier: L
artifacts: [spec.md, plan.md, acceptance.md, progress.md]
design_research_substitute:
  - docs/sector-ux/01-data-contract.md   # research (실측)
  - docs/sector-ux/02-screen-flow.md     # design (§12.3 서버 선행 조건)
ac_count: 48          # 0.4.1: AC-SAG-048(M1.0-a 종료 게이트 — 집계 픽스처 F1~F11 충족, D14) 신설. 0.4.0: AC-SAG-047(M1 종료 게이트 — 골든 baseline 캡처 완결성, D4). 0.3.0: AC-SAG-046(창 일수 실측)
invariants_owned: [EX-1, EX-2, RK-1, RK-2, RRG-1, RRG-2, RRG-3, RRG-4, BM-3, BM-6, SN-3, AG-6, "§8.6"]
depends_on: [SPEC-SECTOR-GRID-001]
open_questions: [O-A2, O-A5, O-A7]        # O-A5는 ① close로 착수 가능해졌으나 재측정이 run-phase M3 작업이라 미결 유지
resolved_open_questions:
  - "O-A1 (2026-08-12): RS-Ratio 롤링 정규화 미적용 — 100이 문자 그대로 벤치마크"
  - "O-A3 (2026-08-12): 상수 주식수 한계를 warnings[]에 명시 + '현재주가' = daily 최신 Close"
  - "O-A4 (2026-08-12): 거래대금 창 = 기간 토글 연동 [anchor(t,N), t]"
  - "O-A6 (2026-08-12): 지표별 coverage.* + 최상위 최소값 병행"
  - "O-A8 (2026-08-13): 선택지 (a) 미완성 주 포함 — as_of = latest, 앵커 = anchor(t,N)(완성 바). 창이 라벨보다 길어짐(실측 프로즌 11/32/95일, 라이브 12/33/96일 — 요일 의존). 파생: REQ-SAG-043 + AC-SAG-046(return_window_days) 신설, REQ-SAG-012에 BM-6 보존 조건(동일 anchor 호출) 명시"
blocking_before_run: []                   # 2026-08-13 v0.4.1: 착수 차단 항목 없음. ① status: completed(v0.3.0) + O-A8 결정 + plan-audit iteration 1 D1/D3/D5 + iteration 2 D10~D15 전부 SPEC 층에서 해소
m1_forced_order: "M1.0-a(집계 픽스처 빌드) → AC-SAG-048 PASS(F1~F11 게이트, v0.4.1 D14) → M1.0-b(골든 baseline 캡처) → M1.0-c(AC-SAG-047 종료 게이트) → M2"
point_of_no_return: "M2"                  # [HARD] plan-audit iteration 2 판정. 비가역 경계는 M1.0-b가 아니라 M2다 — M1.0 구간에서는 구현 코드가 그대로이므로 잘못 뜬 baseline의 재캡처가 가능하다. M2가 구 구현을 교체하는 순간 캡처 창이 영구히 닫힌다. 이 여유가 D12/D14를 치명적이 아니라 회복 가능한 결함으로 만든 근거다. run-phase가 M1.0-c에서 AC-SAG-047 RED를 만나면 (1) 산출물 결함 vs 게이트 단언 결함을 구분하고 (2) 산출물 결함이면 M1.0-a로 되돌아가 재캡처, (3) 단언 결함이면 blocker report 반환(acceptance.md 편집 권한 없음). 상세: acceptance.md §8.5 / plan.md §0.2
blocking_before_ux: [O-A7]                # ③의 AC-SUX-019 / AC-SUX-056 R5가 의존 (③의 O-U9)
as_of_pinned: "2026-08-11"                # 사용자 결정 2026-08-13 (D3). 기존 날짜 축 픽스처 유지, AC-SAG-046 리터럴 4개(11/32/95, 앵커 07-31/07-10/05-08, baseline 07-10) 불변. 게이팅 테스트의 as_of 기본값(None → today) 사용 금지 — acceptance.md §8 규약 8
fixtures:
  date_axis: "tests/fixtures/frozen/weekly-2026-08-12/"        # ① 소관, 읽기 전용. AC-SAG-046만 호스팅
  aggregation: "tests/fixtures/frozen/aggregation-2026-08-11/" # ② 소관, M1.0-a 신규 빌드. 횡단면 게이팅 AC 호스팅. 요건 = acceptance.md §8.2 F1~F11 (값이 아니라 구조)
plan_audit_history:
  - "iteration 1 (2026-08-13): FAIL 0.78 (L thresh 0.85). MUST-PASS 전항 통과. Clarity 0.80 / Completeness 0.82 / Testability 0.55 / Traceability 0.95. BLOCKING D1·D2·D3·D5, SHOULD-FIX D4·D6·D7, MINOR D8·D9"
  - "iteration 2 (2026-08-13): PASS-WITH-DEBT 0.845 (조화평균, L thresh 0.85 미달 / 산술평균 0.855). Δ +0.065. MUST-PASS 7항 전항 통과. Clarity 0.85 / Completeness 0.88 / Testability 0.72(+0.17) / Traceability 0.97. D2·D3·D5·D6·D7·D8·D9 RESOLVED, D1·D4 PARTIALLY-RESOLVED. 신규 D10(CRITICAL)·D11(MAJOR)·D12(CRITICAL)·D13(MAJOR)·D14(MINOR)·D15(MINOR). M1 착수 SUSTAINED — blocking_before_run: [] 유지. 보고서: .moai/reports/plan-audit/SPEC-SECTOR-AGGREGATION-001-review-2.md"
plan_audit_resolution_v040:
  - "D1 (BLOCKING) RESOLVED: 프로즌 픽스처가 게이팅 기대값 7/8을 호스팅 불가 → 픽스처 2종 분리(§8.1) + 집계 픽스처 구조 요건 F1~F11(§8.2) + 게이팅 기대값을 리터럴에서 파생 규칙으로 전환(§8.3). 라이브 결속 7값은 비게이팅 스모크로 강등(규약 3)"
  - "D2 (BLOCKING) RESOLVED: 설계결정 3 반증 → 참 조건을 '최신 대표 바가 금요일'로 정정(spec.md REQ-SAG-043), AC-SAG-046 마감 주 대조를 금요일 종단 픽스처 변형으로 재작성. 실증: 절단본에서 latest=2026-08-07/partial=False/{7,28,91}"
  - "D3 (BLOCKING) RESOLVED: as_of=2026-08-11 리터럴 명기(§8 규약 7) + as_of 기본값 사용 금지 + 정적 스캔 강제(규약 8)"
  - "D4 (SHOULD-FIX) RESOLVED: AC-SAG-047 신설(기계적 M1 종료 게이트) + 캡처 목록을 무파라미터 엔드포인트 현실에 맞춰 단일 파일로 정정"
  - "D5 (BLOCKING) RESOLVED: R1을 골든 baseline에 결속(R4/R5와 동일), R5의 최상위>=95/최하위<=5를 등간격 파생 단언(R5-a)로 대체, R4는 F2(N>=12)로 degenerate 회피"
  - "D6 (SHOULD-FIX) RESOLVED: AC-SAG-014를 출력 동등에서 anchor() 호출 계측 구조 단언으로 전환. 실증으로 출력 동등의 검출력 0 확인(latest/history 양쪽에서 앵커 동일)"
  - "D7 (SHOULD-FIX) RESOLVED: 002/007/011/013/014/024/030/045 R1·R3·R4·R5·R6/046/047에 명명된 되돌림 변형 부여 + 전 대조 단언에 대해 관측된 RED verbatim 기록을 요구하는 DoD 항목 신설(Lesson #9)"
  - "D8 (MINOR) RESOLVED: REQ-SAG-029 → Unwanted Behavior, REQ-SAG-032 → Where"
  - "D9 (MINOR) RESOLVED: AC-SAG-007을 픽스처 구조 요건(F3) 기반으로 재기술하고 순수 합성 열거 → 게이팅 열거로 이동"
plan_audit_resolution_v041:
  - "D10 (CRITICAL, M3 차단) RESOLVED: AC-SAG-013의 '초과수익률 시총가중 평균 == 0 ± 0.05%p' 파생 항등식이 올바른 구현에서 거짓이었다 — 상한 재배분이 그룹핑 계층을 넘어 합성되지 않기 때문이며, F4(원비중 10% 초과 종목 보유 섹터 >= 3)가 상한 구속을 강제하므로 요건상 반드시 실패했다. 실측(2026-08-13, plan.md §3.1을 두 계층에 그대로 구현): cap=0.10 → +1.496127 %p / 상한 없음 → -0.000000 %p / 상한 없음+AG-5 제외 2섹터 → +0.035526 %p. 세 번째 실측이 감사 제안 (a)'무상한 항등식' 대안도 배제한다(F3/F6이 제외 섹터를 강제). 해소: 주 단언을 참조 구현 대조로 교체(섹터별 S_s^ref − B^ref 일치 + ω_s^ref 가중 잔차 일치), 0 리터럴 삭제, 무상한 완전분할 0 항등식은 참조 자기검사(비게이팅)로만 잔존. mut_benchmark_index_row 검출 실측: 편차 0.957391 %p (허용 1e-9)"
  - "D11 (MAJOR, M3 차단) RESOLVED: AC-SAG-014의 anchor() 호출 횟수 == 1 단언이 plan.md D1/D2 공용 함수 구조(섹터 N회 + 벤치마크 1회 = N+1회)에서 스스로 RED가 됐다. 주 단언을 인자 t(앵커 기준일)의 유일성으로 이전하고 호출 횟수 제약 삭제. mut_benchmark_own_anchor는 t를 2026-08-07로 바꾸므로 검출력 보존. 반환 객체 아이덴티티는 두 t가 같은 GridBar를 반환하므로 비게이팅 보조로 강등"
  - "D12 (CRITICAL, M1.0-c 차단) RESOLVED: AC-SAG-047이 존재하지 않는 키를 단언했다. 실측(2026-08-13, model_dump_json): ranking-current.json = {date, sectors[]}, sectors[i].excess_returns = {w1,m1,m3}, 'sector_excess_return' 문자열 0건; stage-overview.json distribution = {stage1..stage4, total}, 'total_count' 0건. backend/schemas/sector.py:24-37 + sector_ranking_service.py:41-52 / backend/schemas/stage.py:8-15. v0.4.0의 키는 내부 dataclass sector_metrics.SectorRank 필드명이었다. 전 키 정정 + 컨테이너명(sectors) 명시 + 재도입 방지 정적 확인 추가. 파급분 AC-SAG-027 / REQ-SAG-024 / plan.md M1.0-b 주석도 정정"
  - "D13 (MAJOR, M2 차단) RESOLVED: §8.3에 참조 구현의 제외·null 처리 계약 신설 — AG-3(시총가중 분모 제외, 등가중 분모 포함) / AG-4(시총가중 미산출) / AG-5(data[] 제외이나 벤치마크 유니버스 잔존) / AG-7(null 취급) + 대조 집합을 프로덕션 non-null 섹터로 제한 + null 섹터 집합 동등 별도 단언. AC-SAG-024/030/013별 파생 규칙 명시"
  - "D14 (MINOR, M1.0-b 차단) RESOLVED: AC-SAG-048 신설 — F1~F11 기계 검증을 M1.0-a 종료 조건으로 격상. MANIFEST 기록값과 검사 산출 실측값의 정확한 일치까지 요구(F3은 섹터명 집합). 음성 검증: F2 임계 >= 999 임시 상향 시 RED. plan.md M1.0-a / M7 / acceptance.md §8.2 말미 동기화"
  - "D15 (MINOR, M3 차단) RESOLVED: AC-SAG-014 태그를 [게이팅 — 집계 픽스처 · 구조 단언]으로, Given에 as_of=2026-08-11 · market=all · period=1w 명시. AC-SAG-045 R5-a에 [게이팅 — 집계 픽스처, as_of=2026-08-11] 부여. 규약 1·8 위반 해소"
plan_audit_cache: invalidated-2026-08-13-v0.4.1  # v0.4.1에서 plan 산출물 4종 전부 재변경 → plan-artifact hash 재변경. 직전 판정 PASS-WITH-DEBT 0.845도 캐시로서는 무효. /moai run Phase 1에서 plan-audit 재실행 필수(skip 4조건 중 artifact-hash 조건 불충족)
```

Tier L이나 `design.md` / `research.md`를 신규 작성하지 않는다 — 그 역할은 이미 확정·교차검증된 `docs/sector-ux/01-data-contract.md`(연구·실측)와 `02-screen-flow.md`(설계)가 수행하며, 중복 작성은 SSOT 분기를 만든다.

## §E.2 Run-phase Evidence

### M1.0-a — 집계 프로즌 픽스처 빌드 + AC-SAG-048 게이트 (2026-08-13)

산출물: `tests/fixtures/frozen/aggregation-2026-08-11/{weekly.db, daily.db, registry.xlsx, MANIFEST.md, build_fixture.py}`
+ 게이트 테스트 `tests/test_aggregation_fixture.py` (30 tests).

빌드 명령: `python tests/fixtures/frozen/aggregation-2026-08-11/build_fixture.py`
(라이브 `Output/*.db` 는 **읽기 전용**으로만 접근했다 — `/api/db/update` 미실행.)

#### 빌드 설계 (핵심 3점)

1. **F1 상위집합** — 날짜 축 픽스처의 41 종목 · 385 날짜 주봉 행을 **verbatim 복사**한 위에
   102 종목을 최근 창(2025-07-01~)에만 얹었다. 날짜 축은 원본 41 종목이 보존하므로 격자가
   346바 그대로 재현된다.
2. **라이브 드리프트 흡수** — 라이브 주봉의 ISO W33 대표 바는 이미 `2026-08-12` 로 갱신됐고
   `2026-08-11` 행은 **라이브에 더 이상 존재하지 않는다**(실측: 라이브 `Date <= 2026-08-11`
   고유 날짜 382 vs 픽스처 385, 픽스처 전용 3일 = 06-16 / 08-05 / 08-11). 보강 종목의 W33 바를
   `2026-08-11` 로 **재라벨**해 최신 정규 바에 가격이 존재하도록 했다. 라이브의
   `Date <= 2026-08-11` 날짜 집합이 픽스처 385 날짜의 부분집합임을 실측 확인했으므로
   신규 날짜는 유입되지 않는다(`live-only dates == []`).
3. **지수 행 포함** — 날짜 축 픽스처와 달리 `KOSPI`/`KOSDAQ` 행을 포함했다.
   `sector_metrics._load_kospi_returns` 가 이 행을 읽으므로 없으면 M1.0-b 골든 baseline 의
   초과수익률이 전부 원수익률로 degenerate 한다. `weekly_grid` 는 지수 행을 날짜 카운트에서
   제외하므로(`_INDEX_NAMES`) 격자에는 영향이 없다(실측 exclusions 0건).

**케이스는 주입이 아니라 선별이다** — F5(NULL 시총) / F7(신고가 판정 분기) / F8(SMA 결측)은
라이브에 자연 존재하는 종목(각 14 / 90 / 39건)에서 골라 담았다. 값을 손으로 만들지 않았다.

#### E1 — F1~F11 실측 표 (임계는 acceptance.md §8.2 리터럴)

| 요건 | 요구 | 실측 | 판정 | 측정 명령 |
| --- | --- | --- | --- | --- |
| **F1** | 날짜 축 종목·날짜 집합 ⊆ 집계 픽스처 | 종목 누락 0 / 날짜 누락 0 (41 ⊆ 145, 385 ⊆ 385) | **PASS** | `pytest -k f1_superset_of_date_axis_fixture` |
| **F2** | AG-5 통과 섹터 >= 12 | **18** | **PASS** | `pytest -k f2_ag5_sector_count` |
| **F3** | kospi 유효 종목 정확히 4인 섹터 == 2 / 정확히 5 >= 1 | **2** (`디스플레이`, `스마트폰`) / **1** (`PCB`) | **PASS** | `pytest -k f3_kospi_member_count_shape` |
| **F4** | 최상위 원비중 > 0.10 섹터 >= 3 | **18** | **PASS** | `pytest -k f4_cap_binding_sectors` |
| **F5** | 시총 NULL/<=0 종목 >= 5 / RS 결측 보유 섹터 >= 3 | **7** / **10** | **PASS** | `pytest -k f5_missing_cap_and_rs` |
| **F6** | 유효 시총 정확히 3인 섹터 >= 1 | **1** (`패션`) | **PASS** | `pytest -k f6_ag4_insufficient_sector` |
| **F7** | `MAX52` vs `MAX(High) over 364d` 판정 분기 종목 >= 5 | **35** | **PASS** | `pytest -k f7_nh_verdict_divergence` |
| **F8** | `SMA40`/`SMA10` NULL 종목 >= 3 | **17** | **PASS** | `pytest -k f8_sma_null_stocks` |
| **F9** | 완성 바 >= 53 + 3M 앵커 `2026-05-08` | **345** / 존재 | **PASS** | `pytest -k f9_grid_depth_and_anchor` |
| **F10** | 전 종목 daily `market_cap`·`close` + 3M 창 `VolumeWon` | 결측 **0** / **0** | **PASS** | `pytest -k f10_daily_meta_and_volume_window` |
| **F11** | MANIFEST 필수 키 비어 있지 않음 + F2~F8 실측 일치 | 필수 키 7/7 + count 9/9 + 섹터명 집합 3/3 일치 | **PASS** | `pytest -k "f11 or manifest"` |

Gaps: 없음. 요건을 완화하거나 임계를 조정한 항목 없음.

#### E4 — 날짜 축 정합 (AC-SAG-046 과 동일)

```
AGGREGATION names=145 distinct_dates=385 grid_bars=346 history=345 latest=2026-08-11 partial=True exclusions=0
AGGREGATION return_window_days={'1w': 11, '1m': 32, '3m': 95} anchors={'1w': '2026-07-31', '1m': '2026-07-10', '3m': '2026-05-08'}
DATE-AXIS   names=41  distinct_dates=385 grid_bars=346 history=345 latest=2026-08-11 partial=True exclusions=0
DATE-AXIS   return_window_days={'1w': 11, '1m': 32, '3m': 95} anchors={'1w': '2026-07-31', '1m': '2026-07-10', '3m': '2026-05-08'}
```

두 픽스처가 `as_of="2026-08-11"` 에서 **완전히 동일한** 날짜 축을 산출한다(F1 상위집합 성질의 귀결).
증거: `.moai/state/verify/sag001-m10a/e4-e5-date-axis.log`.

#### E5 — AC-SAG-046 비회귀 (날짜 축 픽스처 미변경)

```
$ git status --short tests/fixtures/frozen/weekly-2026-08-12/
(출력 없음)
```

날짜 축 픽스처(① SPEC-SECTOR-GRID-001 소관, 읽기 전용)는 한 바이트도 건드리지 않았고,
AC-SAG-046 의 네 리터럴(11/32/95, 앵커 07-31 / 07-10 / 05-08)이 위 E4 로그의 `DATE-AXIS` 행에서
그대로 재현됐다.

#### E6 — 전체 회귀 (B-2 baseline 대비)

| 구분 | baseline (`ee01a6a`/`ac9f547`) | M1.0-a 이후 | 델타 |
| --- | --- | --- | --- |
| passed | 618 | **648** | **+30** (= 신규 AC-SAG-048 테스트 30건) |
| failed | 8 | **8** | 0 |
| errors | 25 | **25** | 0 |
| skipped | 68 | 68 | 0 |
| xpassed | 1 | 1 | 0 |

실패 8건은 baseline 과 **동일 집합**이며 전부 pre-existing 이다 —
`test_api.py::TestScreenEndpoint::test_too_many_patterns_rejected` (1),
`test_meta_service.py::TestRebuild` (2), `test_rs_line.py::TestRsLineCalculation` (2),
`test_screen_service.py` (3). errors 25건은 `tests/fnguide/*` 모듈 import 오류(pre-existing).
**NEW 실패 0건.** 증거: `.moai/state/verify/sag001-m10a/e6-full-suite.log`.

#### E3 — 음성 검증 (Lesson #9 — 작성이 아니라 **관측된 RED**)

M1 커밋(`adb1f25`) 직후, 추적 상태에서 두 건을 실증했다. 테스트를 작성했다는 사실은 증거가
아니며, **되돌렸을 때 RED 를 관측했는지**만이 증거다.

**(1) AC 본문이 요구한 음성 검증 — F2 임계 `>= 12` → `>= 999` 임시 상향**

```
$ sed -i '' 's/^F2_MIN_AG5_SECTORS = 12  /F2_MIN_AG5_SECTORS = 999/' tests/test_aggregation_fixture.py
$ git diff --stat tests/test_aggregation_fixture.py
 tests/test_aggregation_fixture.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
$ python -m pytest tests/test_aggregation_fixture.py -q
.....F........................                                           [100%]
=================================== FAILURES ===================================
_____________________ test_ac_sag_048_f2_ag5_sector_count ______________________
    def test_ac_sag_048_f2_ag5_sector_count(measured: dict) -> None:
        """F2 — AG-5(>= 5종목)를 통과하는 섹터 수 >= 12."""
        n = len(measured["f2_sectors"])
>       assert n >= F2_MIN_AG5_SECTORS, (
            f"F2 위반 — AG-5 통과 섹터 {n}개 < {F2_MIN_AG5_SECTORS}: {measured['f2_sectors']}")
E       AssertionError: F2 위반 — AG-5 통과 섹터 18개 < 999: ['Auto', 'PCB', '게임', '내수', '디스플레이', '반도체', '방산', '비철금속', '스마트폰', '유통', '음식료', '인터넷', '조선', '철강', '통신', '패션', '헬스케어', '화장품']
E       assert 18 >= 999
=========================== short test summary info ============================
FAILED tests/test_aggregation_fixture.py::test_ac_sag_048_f2_ag5_sector_count
1 failed, 29 passed, 1 warning in 0.49s
```

**(2) 추가 음성 검증 — MANIFEST 손조작 (AC-SAG-048 의 "MANIFEST 실측 일치" 절)**

이 절이 AC-SAG-048 의 핵심이므로(MANIFEST 가 틀리면 AC-SAG-007 / 045 R6 이 틀린 기대값 위에서
GREEN 이 된다) 별도로 검출력을 실증했다. F6 섹터명을 `패션` → `헬스케어` 로, F7 count 를
`35` → `34` 로 손으로 고친 변형:

```
$ python -m pytest tests/test_aggregation_fixture.py -q -k manifest
E       AssertionError: MANIFEST 불일치 — f7_nh_verdict_divergent_stock_count: 기록 34 vs 실측 35 (...)
E       assert 34 == 35
E       AssertionError: MANIFEST 섹터명 집합 불일치 — f6_cap_valid_exactly3_sectors: 기록 ['헬스케어'] vs 실측 ['패션']
E       assert {'헬스케어'} == {'패션'}
FAILED tests/test_aggregation_fixture.py::test_ac_sag_048_manifest_counts_match_measured[f7_nh_verdict_divergent_stock_count-f7_stocks]
FAILED tests/test_aggregation_fixture.py::test_ac_sag_048_manifest_sector_sets_match_measured[f6_cap_valid_exactly3_sectors-f6_sectors]
2 failed, 12 passed, 16 deselected, 1 warning in 0.35s
```

**복원 증명 (두 건 모두)**

```
$ git checkout -- tests/test_aggregation_fixture.py
$ git checkout -- tests/fixtures/frozen/aggregation-2026-08-11/MANIFEST.md
$ git status --short tests/fixtures/ .moai/specs/SPEC-SECTOR-AGGREGATION-001/
(출력 없음)
$ python -m pytest tests/test_aggregation_fixture.py -q
30 passed, 1 warning in 0.31s
```

**항진명제 회피 근거** — 단언의 양변이 서로 다른 원천에서 온다. 한 변은 픽스처 DB/xlsx 에서
원시 컬럼을 직접 읽어 재산출한 실측값이고(`build_fixture.py` 를 import 하지 않는다), 다른
한 변은 별도 산출물인 `MANIFEST.md` 의 기록값 또는 acceptance.md §8.2 본문 리터럴 임계다.
증거 파일: `.moai/state/verify/sag001-m10a/e3-neg-f2-999.log`,
`.moai/state/verify/sag001-m10a/e3-neg-manifest-tamper.log`.

### M1.0-b — 골든 baseline 캡처 + M1.0-c AC-SAG-047 게이트 (2026-08-13)

**구현 코드 0줄 변경.** 캡처는 구 구현의 현행 응답을 그대로 뜬 것이며, 비가역 경계인 M2 는
아직 착수하지 않았다(plan.md §0.2 — M1.0-c 까지는 재캡처 가능).

#### E1 — 캡처 경로 (직렬화 계약이 이 마일스톤의 최대 위험)

AC-SAG-047 은 **직렬화 응답**의 형태를 단언한다. 서비스 반환값의 `model_dump_json()` 을 뜨면
`response_model` 변환을 우회해 구조가 어긋나고, 게이트가 실결함과 무관하게 RED 가 된다.
따라서 `fastapi.testclient.TestClient` 로 **실제 HTTP 요청**을 태워 캡처했다.

```
$ python tests/fixtures/golden/pre-sector-ux/capture_baseline.py
httpx: HTTP Request: GET http://testserver/api/sectors/ranking "HTTP/1.1 200 OK"
httpx: HTTP Request: GET http://testserver/api/stage/overview "HTTP/1.1 200 OK"
captured: date=2026-08-11 sectors=18 total=135
```

DB 경로는 라우터 모듈 상수를 패치해 집계 프로즌 픽스처로 고정했다(라이브 DB 캡처 금지):

| 패치 대상 | 값 |
| --- | --- |
| `backend.routers.sectors.WEEKLY_DB_PATH` | `tests/fixtures/frozen/aggregation-2026-08-11/weekly.db` |
| `backend.routers.sectors.DAILY_DB_PATH` | `.../aggregation-2026-08-11/daily.db` |
| `backend.routers.stage.WEEKLY_DB_PATH` | `.../aggregation-2026-08-11/weekly.db` |
| `my_chart.registry.SECTORMAP_PATH` (+ lazy 캐시 2개) | `.../aggregation-2026-08-11/registry.xlsx` |

**registry 고정은 캡처 중 발견한 추가 위험이다.** 구 구현의 `get_sector_registry()` 는 경로
인자가 없고 라이브 `Input/sectormap-original.xlsx` 를 lazy-load 한다(`my_chart/registry.py:122`).
고정하지 않으면 baseline 이 라이브 파일에 묶여 드리프트한다. 고정 전/후 캡처를 `diff` 로
대조해 **양쪽이 바이트 동일**함을 확인했으므로(현재 라이브 registry == 픽스처 사본) 값 변화는
없고, 재현성만 확보됐다.

`as_of` 는 현행 무파라미터 엔드포인트에서 픽스처의 최신 정규 바로 결정되며, 캡처 스크립트가
응답 `date == "2026-08-11"` 을 단언해 기준일이 실제로 고정값임을 확인한다(§8 규약 7).

#### E2 — 산출물 인벤토리

| 파일 | 크기 | 최상위 키 |
| --- | --- | --- |
| `ranking-current.json` | 7,804 B | `date`, `sectors` — `len(sectors) = 18`, `date = 2026-08-11` |
| `stage-overview.json` | 54,024 B | `distribution`, `by_sector`, `stage2_candidates`, `all_stocks` |
| `MANIFEST.md` | 2,988 B | 기계 판독 YAML 블록(`as_of` / `captured_at` / `git_sha` / `fixture` / `capture_command` / `periods`) |
| `capture_baseline.py` | 8,453 B | 재캡처 스크립트(캡처 명령의 실체) |

```
sectors[0] keys: ['name','stock_count','returns','excess_returns','rs_avg',
                  'rs_top_pct','nh_pct','stage2_pct','composite_score','rank','rank_change']
distribution: {'stage1': 1, 'stage2': 42, 'stage3': 2, 'stage4': 90, 'total': 135}
len(by_sector)=18  len(stage2_candidates)=6  len(all_stocks)=135
```

기간별 3파일은 캡처하지 않았다 — 현행 `/sectors/ranking` 은 무파라미터이므로 세 번 호출해도
동일 응답 3부이며, 단일 응답이 이미 `returns.{w1,m1,m3}` / `excess_returns.{w1,m1,m3}` 로 세
기간을 전부 싣는다(plan.md v0.4.0 정정 D4).

#### E3 — AC-SAG-047 결과

```
$ python -m pytest tests/test_golden_baseline.py -q
........................................                                 [100%]
40 passed, 1 warning in 0.34s
```

#### E4 — D12 재도입 방지 (실측 문자열 카운트)

| 파일 | `sector_excess_return` | `total_count` |
| --- | --- | --- |
| `ranking-current.json` | **0건** | **0건** |
| `stage-overview.json` | **0건** | **0건** |

`all sectors have excess_returns.{w1,m1,m3}: True` / `distribution.total present: True (=135)`.
두 문자열은 각각 내부 dataclass 필드명(`SectorRank`)과 존재하지 않는 키이며, 검출되면 응답
모델을 우회해 dataclass 를 덤프했다는 신호다. v0.4.0 결함이 되돌아오면 즉시 RED 가 된다.

#### E5 — 음성 검증 (Lesson #9 — 작성이 아니라 **관측된 RED**)

`stage-overview.json` 을 임시 이동한 상태에서 관측된 RED:

```
$ mv tests/fixtures/golden/pre-sector-ux/stage-overview.json /tmp/_neg_stage.json
$ python -m pytest tests/test_golden_baseline.py -q
FAILED tests/test_golden_baseline.py::test_baseline_file_exists[stage-overview.json]
FAILED tests/test_golden_baseline.py::test_no_dataclass_field_names_leaked[sector_excess_return-stage-overview.json]
FAILED tests/test_golden_baseline.py::test_no_dataclass_field_names_leaked[total_count-stage-overview.json]
ERROR tests/test_golden_baseline.py::test_stage_top_level_container - Asserti...
(… distribution 5건 / by_sector 5건 ERROR …)
3 failed, 26 passed, 1 warning, 11 errors in 0.28s
```

복원 후:

```
$ mv /tmp/_neg_stage.json tests/fixtures/golden/pre-sector-ux/stage-overview.json
$ ls tests/fixtures/golden/pre-sector-ux/
MANIFEST.md  capture_baseline.py  ranking-current.json  stage-overview.json
$ python -m pytest tests/test_golden_baseline.py -q
40 passed
```

`git status --short` 는 이 시점에 `?? tests/fixtures/golden/pre-sector-ux/` 만 표시한다 —
디렉터리 전체가 신규(untracked)이므로 개별 파일 diff 가 뜨지 않는 정상 상태이며, 복원 증명은
위 `ls` + 재실행 GREEN 이 담당한다. 커밋 이후에는 `git status --short` 가 공백이 된다.

#### E6 — baseline 비퇴화 (index row 존재 확인)

`excess_returns` 가 `returns` 와 항등이면 벤치마크가 사실상 부재하다는 뜻이고, R4/R5 비교가
무의미해진다. 사용자 승인 사항인 KOSPI/KOSDAQ 지수 행(각 59바) 포함 결정이 실제로 작동했는지
직접 측정했다:

| 지표 | 실측 |
| --- | --- |
| 한 기간이라도 다른 섹터 | **18 / 18** |
| 다른 (섹터, 기간) 쌍 | **54 / 54** (항등 0건) |
| `max abs(returns − excess_returns)` | **16.1662** |
| 표본 (`화장품`) | `returns {w1:16.1499, m1:25.4084, m3:30.4431}` vs `excess {w1:11.0328, m1:28.95, m3:46.6092}` |

#### E7 — 구현 코드 미변경

```
$ git status --porcelain my_chart/ backend/ frontend/
 M frontend/src/components/SectorAnalysis/BumpChart.tsx      ← 본 SPEC 착수 이전부터 존재 (51+/36-)
?? backend/reports/  frontend/coverage/  frontend/test-results/  frontend/2026-03-16-…txt
```

`BumpChart.tsx` 및 untracked 항목은 **본 마일스톤 착수 시점에 이미 워킹트리에 있던 무관 변경**이며
커밋에 포함하지 않는다(경로 명시 `git add`). 프로즌 픽스처 2종도 미변경:
`git status --porcelain tests/fixtures/frozen/` → 출력 없음.

#### E8 — 전체 회귀 (M1.0-a baseline 대비)

```
$ python -m pytest -q
8 failed, 688 passed, 68 skipped, 1 xpassed, 25 errors in 79.91s
```

| 항목 | M1.0-a 직후 | 현재 | 델타 |
| --- | --- | --- | --- |
| passed | 648 | **688** | **+40** (AC-SAG-047 신규) |
| failed | 8 | **8** | 0 |
| errors | 25 | **25** | 0 |
| skipped / xpassed | 68 / 1 | 68 / 1 | 0 |

실패 8건 집합이 baseline 과 **동일**하다: `test_screen_service` 3 · `test_meta_service` 2 ·
`test_rs_line` 2 · `test_api::test_too_many_patterns_rejected` 1. errors 25 는 전건 `tests/fnguide/*`.
**NEW 실패 0건.** 로그: `.moai/state/verify/m10bc/full-suite.log`.

#### E9 — MANIFEST 기계 판독 블록 (verbatim)

```yaml
as_of: "2026-08-11"
captured_at: "2026-08-13 13:45:27"
git_sha: "b839cee"
fixture: "tests/fixtures/frozen/aggregation-2026-08-11"
capture_command: "python tests/fixtures/golden/pre-sector-ux/capture_baseline.py"
periods: ["w1", "m1", "m3"]
```

#### Gaps / 잔여 위험

- **Gap 1** — 캡처값의 **수치적 정확성**은 검증 대상이 아니다. AC-SAG-047 은 구조 게이트이며,
  이 baseline 이 "구 구현의 응답"이라는 사실만 보증한다. 값의 옳고 그름은 M7 의 R1/R4/R5 가
  구 대비 개선을 판정할 때 비로소 의미를 갖는다.
- **Gap 2** — `all_stocks` (135개) 와 `stage2_candidates` (6개) 는 AC-SAG-047 이 단언하지 않는다.
  R1/R4/R5 가 읽지 않는 필드이므로 게이트 범위 밖이나, 캡처에는 포함돼 있다.
- **잔여 위험 1** — `git_sha: b839cee` 는 **캡처 시점** SHA 이며 본 마일스톤 커밋 이전이다.
  이는 의도된 것이다 — baseline 은 "코드 변경 0줄 상태"에서 떠졌음을 기록해야 한다.
- **잔여 위험 2** — 라이브 `Input/sectormap-original.xlsx` 가 향후 변경돼도 캡처는 픽스처
  registry 를 읽으므로 재현된다(E1 에서 고정). 다만 **재캡처를 다른 커밋에서 수행하면**
  구현이 그 사이 바뀌었을 수 있으므로, M2 이후 재캡처는 불가능하다(설계상 의도).

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: in-progress            # M1.0-c 완료. M2(비가역 경계) 는 사용자 검토 게이트 ② 뒤
milestone_completed: M1.0-c
run_commit_sha: 6f00ba5                 # 본 §E.3 backfill 은 후속 커밋 (커밋은 자기 SHA 를 알 수 없다)
prior_milestone_commits: "adb1f25 (M1.0-a) · b839cee (M1.0-a §E.3 backfill)"
ac_gate: AC-SAG-047
ac_pass_count: 2                   # AC-SAG-048 (30 테스트) + AC-SAG-047 (40 테스트)
ac_fail_count: 0
capture_via_http_response: true    # TestClient 경유 response_model 직렬화. model_dump_json() 아님
capture_as_of: "2026-08-11"        # 캡처 스크립트가 응답 date 와 동등성 단언
capture_fixture: "tests/fixtures/frozen/aggregation-2026-08-11"
capture_git_sha: b839cee           # 캡처 시점 (코드 변경 0줄 상태)
baseline_files: 3                  # ranking-current.json · stage-overview.json · MANIFEST.md
baseline_sector_count: 18          # >= 10 (AC-SAG-047)
baseline_excess_returns_degenerate: false   # 54/54 (섹터,기간) 쌍이 returns 와 상이. max gap 16.1662
d12_forbidden_string_count: 0      # sector_excess_return · total_count 양 파일 0건
new_warnings_or_lints_introduced: 0
full_suite_delta: "+40 passed (648 → 688) / failed 8 (전건 pre-existing, baseline 동일 집합) / errors 25 (pre-existing)"
date_axis_fixture_touched: false   # tests/fixtures/frozen/weekly-2026-08-12/ 미변경
aggregation_fixture_touched: false # tests/fixtures/frozen/aggregation-2026-08-11/ 미변경
production_code_touched: false     # my_chart/ · backend/ · frontend/ 미변경 (BumpChart.tsx 는 착수 이전 무관 변경)
live_db_mutated: false             # /api/db/update 미실행
negative_verification: observed-red-1        # stage-overview.json 임시 이동 → 3 failed + 11 errors 관측. 복원 후 40 passed (E5)
point_of_no_return_crossed: false  # M2 미착수 — 재캡처 여전히 가능
next_gate: "M2 (구 집계 구현 교체) — 사용자 검토 게이트 ②. AC-SAG-048 + AC-SAG-047 양자 PASS 로 진입 전제 충족"
total_run_phase_files: 11          # M1.0-a 6 + baseline 3 + capture_baseline.py 1 + test_golden_baseline.py 1
m1_to_mN_commit_strategy: "마일스톤별 개별 커밋 후 main 직푸시 (Hybrid Trunk 1인 OSS)"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
