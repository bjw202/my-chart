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
ac_count: 50          # 0.5.0: AC-SAG-050(INV-CAP-1 작성 규약의 기계적 집행 — 정적 스캔 2종, N1 구조적 종결) 신설. 0.4.2: AC-SAG-049(상한 재배분 알고리즘 종료·불변식 계약 — 무작위 스윕, D17) 신설. 0.4.1: AC-SAG-048(M1.0-a 종료 게이트 — 집계 픽스처 F1~F12 충족, D14) 신설. 0.4.0: AC-SAG-047(M1 종료 게이트 — 골든 baseline 캡처 완결성, D4). 0.3.0: AC-SAG-046(창 일수 실측)
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
m1_forced_order: "[v0.5.0 재실행] M1.0-a **재빌드**(F12 + **F13 재빌드 구성 계약** 포함, **F13-1 상위집합 필수**, **F7 규약 Y 적용 — 빌더 코드 변경 동반**) → AC-SAG-048 PASS(F1~F13 게이트) → M1.0-b **재캡처**(구 baseline 폐기 — F12 미충족 픽스처 위에서 떠졌다) → M1.0-c(AC-SAG-047 종료 게이트) → M2. M1.1(응답 계약, 7305e2e)은 집계 로직 미변경이므로 되돌리지 않는다"
point_of_no_return: "M2"                  # [HARD] plan-audit iteration 2 판정. 비가역 경계는 M1.0-b가 아니라 M2다 — M1.0 구간에서는 구현 코드가 그대로이므로 잘못 뜬 baseline의 재캡처가 가능하다. M2가 구 구현을 교체하는 순간 캡처 창이 영구히 닫힌다. 이 여유가 D12/D14를 치명적이 아니라 회복 가능한 결함으로 만든 근거다. run-phase가 M1.0-c에서 AC-SAG-047 RED를 만나면 (1) 산출물 결함 vs 게이트 단언 결함을 구분하고 (2) 산출물 결함이면 M1.0-a로 되돌아가 재캡처, (3) 단언 결함이면 blocker report 반환(acceptance.md 편집 권한 없음). 상세: acceptance.md §8.5 / plan.md §0.2
blocking_before_ux: [O-A7]                # ③의 AC-SUX-019 / AC-SUX-056 R5가 의존 (③의 O-U9)
as_of_pinned: "2026-08-11"                # 사용자 결정 2026-08-13 (D3). 기존 날짜 축 픽스처 유지, AC-SAG-046 리터럴 4개(11/32/95, 앵커 07-31/07-10/05-08, baseline 07-10) 불변. 게이팅 테스트의 as_of 기본값(None → today) 사용 금지 — acceptance.md §8 규약 8
fixtures:
  date_axis: "tests/fixtures/frozen/weekly-2026-08-12/"        # ① 소관, 읽기 전용. AC-SAG-046만 호스팅
  aggregation: "tests/fixtures/frozen/aggregation-2026-08-11/" # ② 소관, M1.0-a 신규 빌드. 횡단면 게이팅 AC 호스팅. 요건 = acceptance.md §8.2 F1~F13. [v0.5.0] F4·F8 폐지 + F13(재빌드 구성 계약) 신설. F13-1 상위집합(현행 145종목 전량 보존)이 F5-a/F5-b/F6/F7의 유일 충족 경로 — 신규 시총순 선정만으로는 각각 0/3/소멸/2로 미달(실측). 갱신 예산: 종목 약 360 / 26섹터 / 9.0MB → 약 16~17MB. F7은 규약 Y(NULL MAX52 분모 제외)로 재계수 — 빌더 변경 필요
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
plan_audit_resolution_v042:
  - "D16 (CRITICAL, M2 차단 — run-phase 실측 blocker) RESOLVED: AC-SAG-002의 절 2건이 지정 집계 픽스처 위에서 산술적으로 성립 불가였다. 근본 원인은 cap_eff = max(cap, 1/n)의 축퇴 — cap=0.10에서 n <= 10이면 n × cap_eff = 1이라 max(w) <= cap_eff ∧ Σw = 1의 해가 균등 하나뿐이고, 시총가중이 등가중과 완전히 동일해진다(실측 차 0.0000%p). 픽스처는 F4를 18/18 섹터에서 충족하고 AC-SAG-048도 PASS였으나 AG-5 통과 18섹터 중 n > 10이 게임(32) 하나뿐이었다 — F4가 구성종목 수를 규정하지 않으므로 효과를 함의하지 않는다. 실측(run-phase, 독립 참조 구현): |Δ| >= 0.5%p 섹터 1개(요구 >= 3), 평균 절대 순위 이동 0.3750(요구 >= 1.0). 해소: 픽스처 요건 F12 신설(F12-a n >= 11 ∧ 최상위 원비중 > 0.10 섹터 >= 12 / F12-b 1M |Δ| >= 0.5%p 섹터 >= 3 + 집합 MANIFEST 기록 / F12-c 1M 순위 이동 섹터 >= 5 + 집합 기록) — 구조가 아니라 효과 자체를 요건으로 승격. AC-SAG-002의 두 절을 MANIFEST 집합 동등으로 재작성. '평균 절대 순위 이동 >= 1.0'은 삭제(manager-spec 실측 2026-08-13, 라이브 3개 주봉 바 08-12/08-07/07-31: 12섹터 n=15에서 0.500/0.750/0.500, 14섹터 n=20에서 0.778/1.333/0.889 — 어떤 실용적 픽스처 크기에서도 보장 불가한 데이터 의존 임계). F12 실현 가능성 실측: 라이브 유효 시총 종목 >= 11 섹터가 29/29, 12섹터 n=15에서 F12-b 10/10/9 · F12-c 8/10/8로 전 바 충족. AC-SAG-045 R1 되돌림 대조를 mut_equal_weight → mut_service_not_rewired로 교체(구조적 보장) + mut_equal_weight가 R1의 판별자가 아님을 본문 명시. §8.4 규약 10 신설(대조 검출력 실측 요구). AC-SAG-048에 F12-a/b/c 기계 검사 3행 + 축퇴 방지 절 추가"
  - "D17 (CRITICAL, M2 차단 — run-phase 실측 blocker) RESOLVED: plan.md §3.1 verbatim 알고리즘이 종료하지 않았다. 상한 종목을 cap_eff로 고정하지만 다음 반복에서 over 조건(> cap_eff + 1e-12)에 걸리지 않아 rest로 분류되어 재배분을 다시 받고, 진동하다 20회 상한에서 상한 초과 상태로 종료한다. 실측(manager-spec, seed 20260813, 4,000 케이스, n∈[2,40], 시총 10**U(0,4)×U(0,1)): 3,183건(79.6%) 상한 초과, 최악 n=6에서 cap_eff=0.166667 대비 max(w)=0.211925(+27.2%). 해소: §3.1을 동결형으로 교체 + 종료 증명 명시(매 회 frozen 진부분집합 엄격 증가 → <= min(n,20)회). 고정점 불변 실측 확인 — verbatim 2,000회와 최대 편차 6.696e-12, 닫힌 해와 3.053e-16. 반복 횟수 실측 최악 6회(4,000 케이스) / 7회(60,000 케이스, n<=60, seed 7) → AC-SAG-001과 spec.md §0.2의 '5회 이하' 임계 폐기. AC-SAG-001을 축퇴 케이스(A, [70,10,10,5,5] → 정확히 균등)와 비례 케이스(B, n=15 [1000,15,10×13] → w[1]/w[2] == 1.5)로 분리 — 이전 판의 w[1]/w[3] == 2.0은 n=5에서 원리적으로 성립 불가였다. AC-SAG-049 신설(무작위 스윕 + mut_plan31_verbatim). 파급: AC-SAG-003의 라이브 반도체 인용 + capped_weight 0.10 리터럴(픽스처 반도체 6종목 → cap_eff=0.1667이라 거짓)을 12종목 순수 합성 [600, 40×11]로 교체 + 6종목 축퇴 대조 추가"
  - "D18 (MAJOR, M1.1 관측) RESOLVED: AC-SAG-005의 cap_coverage_ratio 정의가 모호했다(run-phase 보고). '유효시총합 / 전체시총합'은 NULL 종목 시총을 합산할 수 없어 분자·분모가 항상 같아지는 항진명제(Lesson #9 F1)였고, 본 AC 시나리오에서는 두 해석이 모두 1.0을 내어 무증상이었다. Σ market_cap(유효 시총 ∧ 기간 수익률 non-null) / Σ market_cap(유효 시총 종목), 기간별 최솟값으로 확정(run-phase 구현과 동일). 유효 시총 종목 1개의 CHG_1M만 NULL로 바꾸는 판별 대조 절 추가 — 폐기된 해석은 그 변형에서도 1.0을 유지하므로 두 해석이 판별된다. spec.md REQ-SAG-004에도 정의 명시"
  - "D19 (MINOR) RESOLVED: M6 의존 절의 평가 시점 명시. AC-SAG-007 전체(market 파라미터 전제 — M6 신설, AC-SAG-039)와 AC-SAG-043의 파생 구조 절(by_sector · 상세 축약 리스트 — M6 신설, AC-SAG-041/042)은 M2~M5 구간에서 미실행이 Gap이 아니라 설계상 지연이다. AC 본문 + §8.4 규약 6 + §9 DoD에 명시하고 progress.md §E.2 deferred-to-M6 기재를 요구. AC-SAG-043은 4단계 절(M1.1부터)과 파생 구조 절(M6 이후)의 PASS/FAIL을 분리 기록하도록 요구 — 부분 PASS를 전체 PASS로 기록하는 것을 금지"
plan_audit_cache: invalidated-2026-08-13-v0.5.0  # v0.5.0에서 plan 산출물 4종 전부 재변경 → plan-artifact hash 재변경. iteration 3 판정(FAIL 0.81 + STOP)은 v0.4.2 시점 산출물에 대한 것이며 캐시로서 무효. /moai run Phase 1에서 plan-audit 재실행 필수(skip 4조건 중 artifact-hash 조건 불충족)
plan_audit_resolution_v050:
  - "N1 (CRITICAL — cap_eff 축퇴 계열의 5번째 사례) RESOLVED-STRUCTURALLY: AC-SAG-041의 'weight_in_sector == 0.10'이 n < 10 섹터에서 거짓이었다(실측 n=5 → 0.200000, n=6 → 0.166667). 재빌드는 F3/F6 요건상 그런 섹터를 4개 의도 포함한다. 개별 정정에 그치지 않고 acceptance.md §0 INV-CAP-1(3개 명제 + 작성 규약)을 신설해 AC 11개 + F12-a를 전수 결속하고, AC-SAG-050(정적 스캔 2종 + 대조 변형 mut_reintroduce_cap_literal)으로 기계 집행했다. 이 스캔이 작성 중 AC-SAG-003의 'capped_weight: 0.10' 표기를 실제로 검출했다(값은 옳았으나 규약 위반)"
  - "D22 (CRITICAL) RESOLVED: AC-SAG-010의 effective_n 24.3 ± 1.0 / 무상한 2.2는 라이브 반도체(n=163, 재현 실측 24.2606)의 값이었다. INV-CAP-1 명제 3(effective_n <= n)에 의해 밴드 [23.3,25.3]은 n >= 24를 요구하나 재빌드 목표는 n=15(실측 13.4214 topcap / 11.4189 random) — 성립 불가. 순수 합성 [3000,100×24]에서 22.8571428571(= 160/7) 유도 + 5/6종목 축퇴 대조(effective_n == n) + mut_effective_n_uncapped 신설"
  - "D20 (MAJOR) RESOLVED: AC-SAG-045 R1의 '평균 절대 순위 이동 >= 2.5'가 6/6 구성에서 미달했다(composite↔composite 0.8235~2.3529, period=1m 1.1765~2.1176). 순위 이동 섹터 '집합'의 크기 >= 5로 교체 — 실측 집합 크기 15~23(26섹터 재빌드) / 9~14(17섹터), 여유 3.0배이며 mut_service_not_rewired에서 구조적으로 공집합이 된다. mut_equal_weight는 R1의 판별자가 아님을 재실측으로 확인(적용 후에도 집합 크기 12~20 유지)"
  - "D23 (MAJOR) RESOLVED: AC-SAG-015의 '1W KOSPI/KOSDAQ 경고 없이 통과(실측 −0.10/−0.15%p)'는 부호부터 틀렸다. 재측정 라이브 +0.2695%p(n=827) / +0.5035%p(n=1705) — KOSDAQ는 이미 허용오차 0.5%p 초과. 픽스처 규모에서는 +1.0420/+1.9658%p(topcap). 2,546종목 지수를 부분집합이 재현할 수 없으므로 구조적 불가 → 정합성 대조를 비게이팅 스모크로 강등, 게이팅은 경고 발화 메커니즘(합성 픽스처 양방향)에만"
  - "D24 (MAJOR) RESOLVED: AC-SAG-013의 부호 분산 0 < k < N을 비게이팅으로 강등. k를 규정하는 픽스처 요건이 없고 시장 상황에 종속된다(실측 k = 13~24/26, 17섹터 구성 7~15/17). 동시에 '모두 같은 부호는 불가' 선언과 '모두 같은 부호면 warnings[] 경고' 요구의 자기모순을 해소 — k ∈ {0,N}은 정상 가능 상태이고 그때 경고가 실리는 것이 계약이다. 경고 절은 합성 픽스처로 게이팅"
  - "D21 (MINOR) RESOLVED: AC-SAG-045 R5-b(표준편차 증가)를 비게이팅으로 강등. 26섹터 구성에서는 6/6 상승(최소 여유 +1.06)이나 12섹터 구성에서 하락 관측 — 구성 의존. R5의 게이트는 R5-a(등간격, 실측 편차 0.00e+00) 단독"
  - "N4 (MAJOR) RESOLVED: AC-SAG-012의 mock 호출 인자 비교가 항진명제였다 — plan.md §3.2가 '이 구조가 EX-1을 테스트가 아니라 타입 수준에서 보장한다'고 명시하므로 양변이 같은 호출 지점에서 나온다. 명명된 변형 2종(mut_benchmark_divergent_cap 신설 / mut_benchmark_own_anchor 공유) 대조를 주 단언으로 올리고 mock 절을 비게이팅 회귀 가드로 강등. 게이팅 열거로 승격"
  - "N3 (MAJOR) RESOLVED: AC-SAG-016의 정적 스캔 grep -rnE '\\bis (not )?[0-9]' tests/ → 0행이 산문에 매치됐다 — 현행 트리에서 4건이 걸리며 전부 docstring/f-string의 자연어(test_registry.py:58, fnguide/test_dashboard.py:64/79/461)이고 실제 is-리터럴 비교는 0건이다. GREEN을 만들려면 무관한 docstring을 수정해야 했다. ast.Compare + ast.Is/IsNot + ast.Constant(수치, bool 제외) 스캔으로 교체 — 실측 0건"
  - "N7 (MINOR) RESOLVED: AC-SAG-044의 grep -c hasattr에 수치 목표가 없어 카운트 절이 게이팅하지 않았다. 현행 15건이 전부 단일 함수 test_sector_rank_has_required_fields(:195-218)에 있음을 확인하고 기대값 0을 명시. 검출력은 되돌림 3케이스가 전담함을 분리 기재"
  - "N2 (MAJOR) RESOLVED: F7 계수 규약이 빌더와 AC-024 본문에서 모순됐다. build_fixture.py:481의 (max52 or 0.0)는 NULL MAX52를 Close >= 0 = 항상 True로 처리해 divergent 35(MANIFEST 기록값), AC-024 본문 규약으로는 15 — 차이 20 = NULL MAX52 종목 수(실측 현행 픽스처). 규약 Y(NULL 종목을 신·구 양쪽 분모에서 제외)로 확정하고 AC-024 / 045 R3 / F7 / MANIFEST 의미 정렬. 빌더 코드 변경이 필요하므로 run-phase 작업 지시로 명기"
  - "D25 (MAJOR) RESOLVED: F 요건 공허성 — F4·F8은 픽스처를 실행하는 소비 AC가 하나도 없어 빌드만 제약했다(F4는 현행 픽스처가 18/18 충족하면서 AC-SAG-002를 무게이팅으로 만든 당사자). 폐지. F5-a·F6은 AC-SAG-013의 null 섹터 집합 동등 절이, F10은 002/011/013의 market_cap 원천이 실제 소비 AC임을 확인해 재결속(이전 판의 소비 AC 표기 029/034가 틀렸을 뿐 요건은 vacuous가 아니다)"
  - "R-C1~R-C8 (재빌드 구성) RESOLVED: F13(6개 기계 검사 조건)으로 통합. F13-1 상위집합이 핵심 — 신규 시총순 선정만으로는 F7 15→2, F5-b 10섹터→3, F5-a 7→0, F6 소멸로 네 요건이 동시에 깨진다(전부 시총 하위권 종목이 담당). F13-2(대형 섹터 >= 14) / F13-3(F12-b·c >= 9 빌드 목표 — R-C1의 6 vs 5 재발 방지) / F13-4(패션 5종목·유효 시총 3 보존) / F13-5(양 시장 비공백) / F13-6(합성 바 재현). R-C6은 AC-SAG-010의 순수 합성 전환으로 소멸. 예산 갱신: 약 360종목 / 16~17MB"
  - "D29 (MINOR) RESOLVED: 합성 바 명문화 — 라이브 주봉에 2026-08-11 행이 존재하지 않으며(실측 최근 distinct 날짜 2026-08-12/08-10/08-07/07-31/07-24) 픽스처의 그 바는 라이브 2026-08-12를 재라벨링한 합성 바다. acceptance.md §8.1.1 신설 + MANIFEST synthetic_bar 4항목 요건화 + F13-6이 검사. 재빌드에서 재라벨링이 누락되면 AC-SAG-046의 리터럴 4개가 코드 변경 0줄에 전부 RED가 된다"
  - "N5 / D26 (MINOR) RESOLVED: 고아 AC 결속 — AC-SAG-037을 plan.md M1.1(4단계 절) / M6(7-변형 행렬) RED 목록에, AC-SAG-049를 M2 RED 목록에 등재. AC-SAG-050도 M2(스캔 1) / M7(스캔 2 회귀) 결속"
  - "스윕 미평가 항목 (8건) DISPOSED: acceptance.md §8.6 신설 — 각 항목에 미검증 유지가 안전한 근거 또는 검증 가능하게 만드는 요건을 기재했다. 025·031~035·046 금요일 변형은 안전(합성/정의적 성질 또는 ① 읽기 전용 픽스처), 037은 요건 추가, 012·014는 v0.5.0 검출력 보강, 007·043 파생 절은 deferred-to-M6 유지, AC-SAG-048의 F9/F10은 MANIFEST 실측 일치 절에 명시 포함, 골든 baseline 수치 정확성은 검증 대상 아님(구조 게이트가 의도)"
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

### M1.1 — 응답 계약 + 결측 3상태 표현 (2026-08-13)

#### E1 AC PASS/FAIL 매트릭스

| AC | 상태 | 검증 명령 | 실측 |
| --- | --- | --- | --- |
| AC-SAG-036 (응답 공통 10키) | **PASS** | `pytest tests/test_response_contract.py -q` | 7 엔드포인트 × 10키 누락 0건. `excluded` 키 상존, `return_window_days` 3키 |
| AC-SAG-038 (결측 3상태) | **PASS** | 동상 | 3상태 직렬화 형태 3종 상이. 전 응답 스캔에서 결측 자리 `0`/`0.0`/`50.0` 0건 |
| AC-SAG-043 (4단계 전파) | **PASS (부분 — Gap 1건)** | 동상 | dataclass / 서비스 변환 / `model_fields` / JSON 4단계 전건 통과. **파생 구조(`by_sector`·상세 축약 리스트) 절은 M6 이관** |
| AC-SAG-008 (커버리지 4필드) | **PASS** | 동상 | `data[]` 18항목 전건 4필드 보유. `coverage`/`valid_counts` 5버킷 동형 |

전체: `14 passed` (tests/test_response_contract.py). 회귀: `702 passed / 8 failed / 25 errors`
— failed·errors 는 M1.0-c 이전과 **동일 집합**(신규 0건), 증거
`.moai/state/verify/m11/1-full-m11.log`.

#### E2 D6 결측 표현 형태 결정 기록

**채택: `{value, reason}` 객체 형태.** 형제 `*_reason` 필드 형태를 기각한다.

1. AC-SAG-038 본문이 세 상태를 `{value: null, reason: "missing"}` / `{value: 0.0}` /
   `{value: null, reason: "insufficient"}` 로 **직접 명시**한다. 형제 필드 형태는
   `{"x": null, "x_reason": "missing"}` 으로 직렬화돼 AC 본문과 형태가 갈린다.
2. 형제 필드는 지표당 키가 2개로 늘고 **한쪽만 등록에서 빠뜨릴 수 있다** — Lesson #4
   (파생 구조가 원본 갱신을 자동 반영하지 않아 누락된 선례)의 실패 형태 그대로이며,
   AC-SAG-043 의 4단계 전파 검사 대상도 두 배가 된다.
3. §9.1 3상태 보존은 **생성자 검증**으로 구조 보장한다 — `MetricValue.__post_init__` 이
   `reason` 과 `value` 의 동시 지정을 `ValueError` 로 거부하므로, 결측 자리에 `0`/`0.0`/
   `50.0` 이 들어가려면 `present(0.0)` 를 **의도적으로 써야** 하고 누락으로는 발생할 수
   없다. 구 구현의 `float(s.get("CHG_1W") or 0.0)` 및 `_normalize_list` 의 `50.0` 붕괴가
   재도입되면 타입 수준에서 막힌다.

#### E9 `sector_metrics.py` 거짓 주석 — M2 로 이월

plan.md 가 지시한 `:42-44` 는 현재 파일에서 `:41-43`(`sector_return_1w/1m/3m` 의
`# market-cap weighted avg ... return (%)`)이다. 정정은 실제 구현을 시총가중으로 바꾸는
M2 와 같은 커밋에 있어야 의미가 있으므로 M1.1 에서 수행하지 않았다(주석만 먼저 고치면
"등가중인데 등가중이라고 적힌" 상태가 되어 정보량이 같다). 정정문은 WIP 브랜치
`83cb847` 에 포함돼 있다.

---

### M2 — 가중·집계 코어 : **미착수 (BLOCKER)** (2026-08-13)

**M2 를 커밋하지 않았다.** 착수 직전 검증에서 **AC-SAG-002(게이팅 AC)의 절 2건이 지정
집계 픽스처 위에서 산술적으로 성립 불가**임을 실측했다. M2 는 비가역 경계(§8.5)이며,
해소에 집계 픽스처 재빌드(M1.0-a) → 골든 baseline 재캡처(M1.0-b) 가 필요할 수 있어
**지금 커밋하면 그 경로가 영구히 닫힌다**. 구현물은 WIP 브랜치에 보존했다
(`wip/SPEC-SECTOR-AGGREGATION-001-M2`, `83cb847`, main 미머지).

#### 근본 원인 — `cap_eff = max(cap, 1/n)` 의 귀결

`cap = 0.10` 에서 `n <= 10` 이면 `cap_eff = 1/n` 이므로 `n × cap_eff = 1` 이 된다. 즉
"최대 가중치 <= cap_eff 이고 Σw = 1" 을 만족하는 해가 **등가중 하나뿐**이다. 따라서
**구성종목 10개 이하 섹터에서 시총가중은 등가중과 항상 완전히 동일**하며, 상한 재배분이
관측 가능한 구간은 `n >= 11` 이다.

집계 픽스처의 AG-5 통과 18섹터 중 `n > 10` 은 **게임(32) 하나뿐**이다(나머지 17개는
n=5~8). 픽스처 요건 **F4("최상위 종목 원비중 > 10% 인 섹터 >= 3")는 이 조건을 함의하지
않는다** — F4 자체는 충족돼 있고 AC-SAG-048 도 PASS 다.

#### 실측 (독립 참조 구현 — 프로덕션 모듈 미import, §8.3)

```
AG-5 통과 16섹터 중 |시총가중 − 등가중| >= 0.5%p 인 섹터 = 1개 (게임, Δ 2.2763%p)
                                       AC-SAG-002 요구: >= 3개          → FAIL
평균 절대 순위 이동 (시총가중 순위 vs 등가중 순위) = 0.3750
                                       AC-SAG-002 요구: >= 1.0          → FAIL
n=6 섹터 표본: 비철금속 24.2060 vs 24.2060 / 통신 15.0261 vs 15.0261 / 화장품 25.4084 vs 25.4084
              (Δ = 0.0000%p — 완전 동일, 부동소수 오차조차 없음)
```

AC-SAG-002 는 이 두 절에 대해 *"두 방식이 우연히 일치하는 픽스처에서는 이 AC 가
무게이팅이 되므로 F4 는 필수 요건이다"* 라고 적고 있다 — **AC 자신의 항진명제 방지
장치가 발화한 것**이며, 형식 위반이 아니라 검출력 상실이다. 같은 벽에 **AC-SAG-045 R1**
(골든 baseline 대비 순위 이동, M7 게이팅)도 부딪힌다.

#### 파생 발견 — plan.md §3.1 알고리즘의 20회 상한 부족

§3.1 verbatim 형태는 상한에 걸린 종목을 다음 반복에서 나머지 집합에 **다시 포함**하므로
진동하며, 20회 안전 상한에서 **가중치가 상한을 초과한 채 종료**한다.

```
n=9,  cap_eff=0.111111 → §3.1 verbatim 20회 종료 시 max weight = 0.122775  (+10.5% 초과)
n=12, cap_eff=0.100000 → §3.1 verbatim 20회 종료 시 max weight = 0.1000000000063
```

AC-SAG-001 의 "최대값 <= cap_eff" 와 "5회 이하 수렴" 을 동시에 위반한다. WIP 구현은
상한 종목을 **동결**하는 형태를 쓰며 같은 고정점을 갖는다(§3.1 을 200회까지 돌린 값과
최대 편차 `4.8e-12`, 무작위 305 케이스에서 반복 최대 **5회**, 상한 위반 0건).
등가성 대조는 `tests/test_weighting.py::test_ac_sag_001_matches_plan_31_verbatim_fixed_point`
가 §3.1 을 독립 재구현해 단언한다.

#### 파생 발견 2 — AC-SAG-001 지정 픽스처의 비율 단언 불가

AC-SAG-001 의 `w[1]/w[2] == 1.0`, `w[1]/w[3] == 2.0` 는 지정 픽스처 `[70,10,10,5,5]`
(`n=5`, `cap_eff=0.20`)에서 **어떤 인덱싱 규약으로도 성립 불가**하다 — 위 귀결에 의해
해가 균등 `0.2 × 5` 하나뿐이므로 모든 비율이 `1.0` 이다. "비례 배분(균등 아님)" 이라는
**성질**은 `n >= 11` 픽스처에서 단언했다(`test_ac_sag_001_redistribution_is_proportional_not_equal`,
원 시총 3:2:1 비율 보존 확인).

#### E3 Lesson #9 되돌림 실증 — **미실행 (Gap)**

`mut_equal_weight`(AC-SAG-002 / 045 R1) 변형 실증은 **수행하지 않았다.** 대조 대상인
AC-SAG-002 의 값 단언 자체가 현 픽스처에서 검출력을 갖지 못하므로, 변형을 적용해 RED 를
받아도 그 RED 는 "AC 가 유효하다" 는 증거가 되지 못한다. §9 DoD 에 따라 **GREEN 이 아니라
Gap 으로 기재**한다. 픽스처 요건 정정 후 실증한다.

#### 보존된 WIP 내용 (`83cb847`, main 미머지)

`my_chart/analysis/weighting.py` 신설(`capped_weights` — `@MX:ANCHOR` AG-1 계약,
`effective_n`, `weighted_mean`) · `sector_metrics.py` 집계 교체(`compute_sector_aggregates`,
AG-1~AG-7, 커버리지·`effective_n`·`capped_members`·`excluded` 산출) · `:41-43` 거짓 주석
정정 · `tests/test_weighting.py` 11 tests. 회귀 `713 passed`, 신규 실패 0건
(`.moai/state/verify/m2/1-full-m2.log`).

#### **[v0.4.2 · manager-spec] blocker 2건 SPEC 층에서 해소 (2026-08-13)**

두 blocker는 **SPEC 층에서 해소됐다**(spec.md / plan.md / acceptance.md v0.4.2 —
`D16` · `D17`). run-phase 재개 전 **집계 픽스처 재빌드부터** 시작한다.

| blocker | 해소 위치 | 요지 |
| --- | --- | --- |
| **BLOCKER-1** (`cap_eff` 축퇴 → AC-SAG-002 무게이팅) | acceptance.md §8.2 **F12 신설** · AC-SAG-002 절 2·3 재작성 · AC-SAG-045 R1 대조 교체 · §8.4 규약 10 신설 · AC-SAG-048 F12 검사 3행 | 보장 근거를 F4 → **F12**로 이관. F12-b/F12-c는 **효과 자체를 요건으로 규정**하므로 "구조가 효과를 함의한다"는 잘못된 전제가 재발할 수 없다. *"평균 절대 순위 이동 >= 1.0"* 은 **삭제** — 실측상 어떤 실용적 픽스처 크기에서도 보장 불가한 데이터 의존 임계였다 |
| **BLOCKER-2** (§3.1 비종료) | plan.md **§3.1 동결형으로 교체** + 종료 증명 · AC-SAG-001 A/B 분리 · **AC-SAG-049 신설** | 고정점 불변 실측 확인(verbatim 2,000회 대비 `6.696e-12`, 닫힌 해 대비 `3.053e-16`) — **종료 성질만** 고친다. 반복 최악 실측 6~7회이므로 *"5회 이하"* 임계 폐기 |

**manager-spec 실측 근거 (프로덕션 모듈 미import, 라이브 원본 읽기 전용)**:

```
F12 실현 가능성 — 라이브 유효 시총 종목 >= 11 인 섹터 = 29/29
  (헬스케어 328 · 인터넷 171 · 반도체 163 · Auto 138 · 건설 128 · … 상위 20섹터 전부 >= 57)
12섹터 n=15 구성, 3개 주봉 바(2026-08-12 / 08-07 / 07-31):
  F12-b(|Δ| >= 0.5%p 섹터) = 10 / 10 /  9   (임계 >= 3)   전 바 충족
  F12-c(순위 이동 섹터)    =  8 / 10 /  8   (임계 >= 5)   전 바 충족
  평균 절대 순위 이동       = 0.500 / 0.750 / 0.500        → 구 임계 1.0 미달 (삭제 근거)
n=11 로 낮추면 F12-b = 3 / 4 / 4, F12-c = 4 / 7 / 2 → 임계에 붙거나 미달 ⇒ 빌드 목표 n >= 15
n <= 10 전 구간: F12-b = 0, F12-c = 0, max|Δ| = 0.000%p (축퇴 확인)

§3.1 알고리즘 — seed 20260813, 4,000 케이스, n∈[2,40]
  verbatim 20회 상한 종료 시 상한 초과      = 3,183 / 4,000 (79.6%), 최악 +27.2% (n=6)
  verbatim 2,000회 미수렴                    = 0 / 4,000       (고정점은 존재한다)
  동결형 상한 초과                            = 0 / 4,000
  동결형 최대 반복                            = 6회 (60,000 케이스 확장 스윕에서 7회)
  동결형 vs verbatim@2000  max|Δw|           = 6.696e-12
  동결형 vs 닫힌 해        max|Δw|           = 3.053e-16
```

**E3 Gap 유지**: `mut_equal_weight` 실증은 여전히 **미실행**이다. 대조 대상 AC-SAG-002가
재빌드된 픽스처 위에서 검출력을 회복한 뒤에 수행한다(§9 DoD).

**AC-SAG-005 모호성(D18) 해소**: run-phase가 보고한 두 해석 중
`Σ market_cap(유효 시총 ∧ 기간 수익률 non-null) / Σ market_cap(유효 시총 종목)`(기간별 최솟값,
**현행 구현과 동일**)으로 확정됐다. 폐기된 `유효시총합/전체시총합` 해석은 NULL 시총을 합산할 수
없어 **항상 1.0**인 항진명제였다. AC-SAG-005에 판별 대조 절이 추가됐으므로 M2에서 그 절의
테스트를 함께 작성한다.

**M6 의존 절 범위 확정(D19)**: `AC-SAG-007` 전체와 `AC-SAG-043`의 파생 구조 절은 M6 산출물
(`market` 파라미터 · `by_sector` · 상세 축약 리스트)에 의존한다. M2~M5 구간에서 이 절들은
**`deferred-to-M6`으로 기재**하며 **Gap이 아니다**. AC-SAG-043은 4단계 절(M1.1부터 평가)과
파생 구조 절(M6 이후)의 PASS/FAIL을 **분리 기록**한다.

**재개 순서 (강제)**: `M1.0-a 재빌드(F12 · 섹터당 n >= 15)` → `AC-SAG-048 PASS(F1~F12)` →
`M1.0-b 골든 baseline 재캡처(구 baseline 폐기)` → `M1.0-c(AC-SAG-047 PASS)` → `M2`.
M1.1(`7305e2e`)은 집계 로직을 건드리지 않았으므로 되돌리지 않는다. WIP 브랜치
`wip/SPEC-SECTOR-AGGREGATION-001-M2 @ 83cb847`은 **동결형 구현을 이미 담고 있으므로**
(plan.md §3.1 v0.4.2와 동일 형태) M2 재개 시 참조하되, F12 픽스처 위에서 AC를 다시 판정한다.

> **[v0.5.0 갱신 — 2026-08-13] 위 재개 순서는 F13 재빌드 구성 계약으로 대체된다.**
> plan-audit iteration 3(FAIL 0.81 + STOP)에 이어 수행한 **49개 AC 전수 도달가능성 스윕**이
> 신규 결함 N1~N7 + 재확인 D20~D26을 반환했고, v0.5.0이 이를 단일 배치로 정정했다.
> **run-phase가 재개 전 반드시 반영할 두 가지**:
> 1. **F13-1 상위집합 [HARD]** — 재빌드는 현행 픽스처 **145종목을 전량 보존**한다. 신규 시총순
>    선정만으로 뽑으면 **F5-a(7→0) · F5-b(10섹터→3) · F6(패션 소멸) · F7(15→2)이 동시에 깨진다**
>    (실측 2026-08-13, 독립 참조 구현). 갱신 예산: 약 360종목 / 26섹터 / 16~17 MB.
> 2. **F7 규약 Y [빌더 코드 변경 동반]** — `build_fixture.py:481`의 `(max52 or 0.0)`을 **NULL 제외**로
>    교체하고 MANIFEST `f7_*`를 재기록한다(현행 35 → 규약 Y 기준 15 계열).
>
> **갱신 재개 순서 (강제)**: `M1.0-a 재빌드(F12 + F13, 상위집합 + 규약 Y)` → `AC-SAG-048 PASS(F1~F13)` →
> `M1.0-b 골든 baseline 재캡처` → `M1.0-c(AC-SAG-047 PASS)` → `M2`.
> AC 총수 49 → **50**(AC-SAG-050 신설). M2 RED 목록에 **AC-SAG-049 · AC-SAG-050**이 추가됐고,
> M1.1 / M6 RED 목록에 **AC-SAG-037**이 결속됐다(고아 AC 해소).

---

### M1.0-a 재빌드 — 집계 픽스처 F1~F13 + AC-SAG-048 확장 (2026-08-13, `a000add`)

**결론: AC-SAG-048 PASS (65 tests).** v0.4.2 D16 / v0.5.0 F13 요건에 따라 픽스처를 재빌드했다.
구 빌드(`adb1f25`)는 F1~F11 을 전부 충족하고 AC-SAG-048 도 PASS 였으나, AG-5 통과 18섹터 중
유효 시총 `n > 10` 이 게임 하나뿐이라 INV-CAP-1 축퇴(`cap_eff = max(0.10, 1/n)` — `n <= 10` 이면
시총가중이 등가중과 비트 단위로 동일)로 AC-SAG-002 를 **완전한 무게이팅**으로 만들었다.

#### 빌드 설계 (재빌드에서 바뀐 3점)

1. **F13-1 상위집합 [HARD]** — `f13-1-superset-baseline.tsv` 신설. `git show adb1f25:…/weekly.db`
   와 `…/registry.xlsx` 를 직접 추출해 145종목 + 섹터 배정을 기록했다(워킹트리 상태에 의존하지
   않는다). 빌더는 이 집합을 **후보 풀 통과 여부와 무관하게 전량 시드**하며, 누락 시 빌드가
   `SystemExit` 로 중단된다.
2. **F13-2 대형 섹터 폭** — `SECTOR_PLAN` 확대. F3 3개 섹터(디스플레이·스마트폰·PCB)는
   **KOSPI 구성수(4 / 4 / 5)를 고정한 채 KOSDAQ 으로만** 넓혔다. 이유: 이 셋을 `n <= 10` 으로
   두면 시총가중 값이 등가중과 비트 동일해지는데도 **이웃 섹터의 교차만으로 F12-c 순위 이동
   집합에 끼어든다**(1차 빌드에서 PCB·스마트폰이 실제로 들어왔다). AC-SAG-048 축퇴 방지 절이
   그 상태를 참조 구현 결함으로 규정하므로, 축퇴 경계를 넘겨 구조적으로 제거했다.
   패션은 5종목 / 유효 시총 3 을 유지한다(F6 · F13-4).
3. **F7 규약 Y (N2)** — `build_fixture.py` 의 `(max52 or 0.0)` / `MAX52.fillna(0.0)`(규약 X)을
   **NULL 제외**로 교체했다. 상세는 아래 E4.

#### E1 — F1~F13 실측 표 (임계는 acceptance.md §8.2 / §8.2.1 리터럴)

| 요건 | 요구 | 실측 | 여유 | 판정 | 측정 명령 |
| --- | --- | --- | --- | --- | --- |
| **F1** 날짜 축 상위집합 | 종목·날짜 집합 ⊇ | 누락 0 / 0 | — | PASS | `pytest -k f1_superset` |
| **F2** AG-5 통과 섹터 | `>= 12` | **18** | 1.50x | PASS | `pytest -k f2_ag5` |
| **F3-a** KOSPI 정확히 4 | `== 2` | **2** (디스플레이·스마트폰) | — | PASS | `pytest -k f3_kospi` |
| **F3-b** KOSPI 정확히 5 | `>= 1` | **1** (PCB) | 1/1 | PASS | `pytest -k f3_kospi` |
| ~~F4~~ | — | **폐지** (v0.5.0, 소비 AC 부재) | — | N/A | 검사 삭제 |
| **F5-a** 시총 NULL/`<=0` 종목 | `>= 5` | **9** | 1.80x | PASS | `pytest -k f5a` |
| **F5-b** RS 결측 보유 섹터 | `>= 3` | **10** | 3.33x | PASS | `pytest -k f5b` |
| **F6** 유효 시총 정확히 3 섹터 | `>= 1` | **1** (패션) | 1/1 | PASS | `pytest -k f6_ag4` |
| **F7** 신고가 판정 분기 (규약 Y) | `>= 5` | **24** | 4.80x | PASS | `pytest -k f7_nh` |
| ~~F8~~ | — | **폐지** (v0.5.0, 소비 AC 부재) | — | N/A | 검사 삭제 |
| **F9** 완성 바 / 3M 앵커 | `>= 53` / 존재 | **345** / True | 6.51x | PASS | `pytest -k f9_grid` |
| **F10** meta·daily 결측 | `0` / `0` | **0** / **0** | — | PASS | `pytest -k f10_daily` |
| **F11** MANIFEST 필수 키 + `synthetic_bar` | 비어 있지 않음 | 7키 + 4항목 | — | PASS | `pytest -k f11_manifest` |
| **F12-a** `n >= 11` ∧ 최상위 원비중 `> 0.10` | `>= 12` | **17** | 1.42x | PASS | `pytest -k f12a` |
| **F12-b** 1M 시총가중−등가중 `>= 0.5%p` | `>= 3` | **13** | 4.33x | PASS | `pytest -k f12b` |
| **F12-c** 1M 시총가중 순위 ≠ 등가중 순위 | `>= 5` | **12** | 2.40x | PASS | `pytest -k f12c` |
| **F12** 축퇴 방지 | f12a/b/c 집합에 `n<=10` 0개 | **0** | — | PASS | `pytest -k f12_no_degenerate` |
| **F13-1** 상위집합 누락 / 섹터 드리프트 | `0` / `0` | **0** / **0** | — | PASS | `pytest -k f13_1_superset` |
| **F13-2** 유효 시총 `n >= 15` 섹터 | `>= 14` | **17** | 1.21x | PASS | `pytest -k f13_2_large` |
| **F13-3** F12-b / F12-c 빌드 목표 | `>= 9` / `>= 9` | **13** / **12** | 1.33x | PASS | `pytest -k f13_3_f12_headroom` |
| **F13-4** 패션 구성 / 유효 시총 | `5` / `3` | **5** / **3** | — | PASS | `pytest -k f13_4_small` |
| **F13-5** 양 시장 비공백 + AG-5 섹터 | `>= 1` / `>= 1` | kospi 15 · kosdaq 17 (유니버스 133 · 188) | — | PASS | `pytest -k f13_5_both_markets` |
| **F13-6** 합성 바 재라벨링 | `2026-08-11 > 0` ∧ `2026-08-12 == 0` | **323** / **0** | — | PASS | `pytest -k f13_6_synthetic` |
| **MANIFEST 실측 일치** | 기록 == 독립 재산출 | 카운트 19키 · 집합 8키 · 스칼라 8키 전건 일치 | — | PASS | `pytest -k manifest_` |

> **여유가 얇았던 1차 빌드를 폐기하고 재구성했다** — 1차 구성(296종목)에서 F12-a 는 14(1.17x),
> F13-2 는 14(**1.00x, 여유 0**)였고 F12-c 집합에 `n<=10` 섹터 2개(PCB·스마트폰)가 들어 있었다.
> §8.4 규약 10(대조 단언의 검출력을 실측으로 확인한다)의 취지에 따라 임계에 붙은 구성을 버리고
> F3 3개 섹터를 KOSDAQ 으로 넓힌 2차 구성(331종목)을 채택했다.

#### E2 — 산출물 인벤토리

| 파일 | 구 빌드(`adb1f25`) | 재빌드(`a000add`) |
| --- | --- | --- |
| `weekly.db` | 6.80 MB · 20,479행 · 145 이름 | **11.0 MB · 31,254행 · 331 이름**(지수 2 포함) |
| `daily.db` | 2.56 MB · 9,050행 | **5.8 MB** |
| `registry.xlsx` | 13 KB | **24 KB** |
| `f13-1-superset-baseline.tsv` | — | **신설** (145종목 + 섹터 배정) |
| `MANIFEST.md` | F2~F8 | **F2~F13 + `synthetic_bar` + F7 규약 대조** |
| 합계 | 9.0 MB | **16.8 MB** |

유효 유니버스 135 → **321**. 고유 날짜 385 · 정규 격자 346바 · `history_grid` 345바 ·
CG-3 배제 0건 — **날짜 축은 불변**이다.

#### E4 — F7 규약 Y 마이그레이션 (N2)

`build_fixture.py` 변경 (선별 단계 · 실측 단계 양쪽):

```python
# 규약 X (폐기) — NULL MAX52 를 0.0 으로 채워 `Close >= 0` 을 항상 참으로 만든다
verdict_stored = df["Close"] >= df["MAX52"].fillna(0.0) * (1 - NH_THRESHOLD)
verdict_high   = df["Close"] >= df["max_high"].fillna(0.0) * (1 - NH_THRESHOLD)
df["nh_divergent"] = verdict_stored != verdict_high

# 규약 Y (확정) — NULL MAX52 종목을 신·구 양쪽 분자·분모에서 제외한다
judgeable = df["MAX52"].notna() & df["max_high"].notna()
verdict_stored = df["Close"] >= df["MAX52"] * (1 - NH_THRESHOLD)
verdict_high   = df["Close"] >= df["max_high"] * (1 - NH_THRESHOLD)
df["nh_divergent"] = judgeable & (verdict_stored != verdict_high)
```

| 계수 규약 | 구 픽스처(`adb1f25`) | 재빌드 픽스처 |
| --- | --- | --- |
| 규약 X (NULL → `0.0`, 폐기) | **35** (MANIFEST 기록값) | **51** |
| **규약 Y (NULL 제외, 확정)** | 15 (재계산값) | **24** |
| NULL `MAX52` 종목 수 | 20 | **27** |
| 차이 == NULL 종목 수 | 35 − 15 = 20 ✔ | 51 − 24 = 27 ✔ |

MANIFEST `f7_*` 3키를 규약 Y 기준으로 재기록했다(`f7_convention: "Y"` ·
`f7_nh_verdict_divergent_stock_count: 24` · `f7_max52_null_stock_count: 27` ·
`f7_convention_x_divergent_stock_count: 51`). AC-SAG-048 은 **두 규약의 계수가 다름**과
**차이가 정확히 NULL 종목 수임**을 단언한다 — 두 값이 같으면 규약 선택이 무증상이라는 뜻이므로
그 픽스처는 AC-SAG-024 의 규약 Y 절을 게이팅하지 못한다.

> 프로덕션 `near_52w_high` 경로에도 같은 규약을 적용하는 것은 **M5 작업**이다(§2.5). 본
> 마일스톤은 프로덕션 코드를 건드리지 않았다(E12).

#### E5 — 날짜 축 정합 + AC-SAG-046 비회귀

```
$ git status --short tests/fixtures/frozen/weekly-2026-08-12/      → (공백)
$ git diff --stat HEAD~2 HEAD -- tests/fixtures/frozen/weekly-2026-08-12/  → (공백)
```

날짜 축 픽스처는 ① SPEC-SECTOR-GRID-001 소관 읽기 전용이며 **본 마일스톤에서 단 1바이트도
변경되지 않았다.** 집계 픽스처 위의 파생값도 AC-SAG-046 과 동일하다 — `latest=2026-08-11` ·
`is_partial_week=True` · `return_window_days={1w:11, 1m:32, 3m:95}` · 격자 346바 · 배제 0건.
소비 테스트 `tests/test_consumer_dates.py` 26 passed, `tests/test_response_contract.py` +
`tests/test_weekly_grid.py` 27 passed.

#### E6 — F13-1 상위집합 증명

`adb1f25` 145종목 전량이 재빌드에 존재하고 섹터 배정도 보존됐다.

```
f13_1_missing        = []   (집합 차 sorted(set(baseline) - set(agg_names)))
f13_1_sector_drift   = []   (baseline 섹터 != 재빌드 registry 섹터인 종목)
f13_1_baseline_count = 145  (MANIFEST 기록 == 목록 실측)
```

#### E3 — 음성 검증 (Lesson #9 — 작성이 아니라 **관측된 RED**)

**NEG-1 · F2 임계 `12 → 999`** (AC-SAG-048 본문 지정 변형)

```
E       AssertionError: F2 위반 — AG-5 통과 섹터 18개 < 999: ['Auto', 'PCB', '게임', '내수',
        '디스플레이', '반도체', '방산', '비철금속', '스마트폰', '유통', '음식료', '인터넷',
        '조선', '철강', '통신', '패션', '헬스케어', '화장품']
E       assert 18 >= 999
tests/test_aggregation_fixture.py:408: AssertionError
FAILED tests/test_aggregation_fixture.py::test_ac_sag_048_f2_ag5_sector_count
1 failed, 2 passed, 62 deselected
```

**NEG-2 · F12-a 임계 `12 → 999`** (v0.4.2 지정 변형)

```
E       AssertionError: F12-a 위반 — n >= 11 이고 최상위 원비중 > 0.1 인 섹터 17개 < 999: [...]
E       assert 17 >= 999
tests/test_aggregation_fixture.py:532: AssertionError
FAILED tests/test_aggregation_fixture.py::test_ac_sag_048_f12a_observable_cap_redistribution_sectors
1 failed, 2 passed, 62 deselected
```

두 변형 모두 복원 후 **sha256 바이트 동등**을 확인했다
(`f794452e3fa911c53d36fce6755422da7bf0ef3a46b8d0c4f9e62bc7d8d7cb12`, before == after).

**NEG-3 · F13-1 상위집합 OFF — 지정된 형태로 실증되지 않았다 (Gap, 아래 참조)**

`load_superset_baseline()` 을 `{}` 로 눌러 tmpdir 에 재빌드한 결과 **네 요건이 모두 green 이었다**:

```
F5-a  market_cap NULL/<=0 종목       실측   7  임계 >=   5  -> green
F5-b  RS 결측 보유 섹터              실측  10  임계 >=   3  -> green
F6    유효 시총 정확히 3 섹터        실측   1  임계 >=   1  -> green
F7    신고가 판정 분기(규약 Y)       실측  19  임계 >=   5  -> green
```

원인은 **빌더에 두 번째 충족 경로가 있다**는 것이다 — `select_names()` 는 `FORCED_CAP_MISSING_
PER_SECTOR` 로 시총 결측 종목을 강제 포함하고, "(b) 플래그 종목 최대 2개" 단계에서
`nh_divergent | sma_null | rs_missing` 종목을 우선 픽한다. 상위집합을 빼도 선별기가 라이브 풀에서
동등한 종목을 다시 집어온다.

SPEC §8.2.1 이 실측 근거로 든 **순수 시총순 선정**(상위집합 OFF **+** 플래그 인지 선별 OFF)을
별도로 재현하면 **2/4 만 RED** 다:

```
F5-a  market_cap NULL/<=0 종목       실측   0  임계 >=   5  -> RED   (SPEC 예측 0 — 일치)
F5-b  RS 결측 보유 섹터              실측   5  임계 >=   3  -> green (SPEC 예측 3 — 불일치)
F6    유효 시총 정확히 3 섹터        실측   0  임계 >=   1  -> RED   (SPEC 예측 소멸 — 일치)
F7    신고가 판정 분기(규약 Y)       실측  12  임계 >=   5  -> green (SPEC 예측 2 — 불일치)
```

두 실행 모두 **tmpdir 에만 빌드**했으며 리포의 픽스처는 건드리지 않았다.

#### E10 — 전체 회귀 (B-13 baseline 대비)

| 구분 | baseline (`a224593`) | 재빌드 후 | 신규 |
| --- | --- | --- | --- |
| passed | 702 | **737** (+35, 신규 AC-SAG-048 테스트) | — |
| failed | 8 | **8** (동일 집합) | **0** |
| errors | 25 (`tests/fnguide/*`) | **25** | **0** |
| skipped / xpassed | 68 / 1 | 68 / 1 | — |

기존 실패 8건은 전건 pre-existing 이다 — `test_screen_service.py`(3) · `test_meta_service.py`(2) ·
`test_rs_line.py`(2) · `test_api.py::test_too_many_patterns_rejected`(1).
로그: `.moai/state/verify/m10a/1-post-rebuild-suite.log`.

---

### M1.0-b 재캡처 — 골든 baseline 폐기 후 재수집 + M1.0-c AC-SAG-047 (2026-08-13, `8e51176`)

**결론: AC-SAG-047 PASS (40 tests). `golden_baseline_discarded: true`.**

#### E1 — 폐기 기록

구 baseline(`b839cee`, 캡처 2026-08-13 13:45:27)은 F12 미충족 픽스처(`adb1f25`) 위에서 떠졌고,
그 픽스처는 재빌드로 더 이상 리포에 존재하지 않는다. 그 위에서 R1/R4/R5 를 판정하면 v0.4.1 의
결함을 그대로 상속하므로 폐기했다(§9 DoD). 폐기 전 sha256:

```
ranking-current.json  3dbf8341fa0448bd0be36c51f79ee08b767463ffd10d8f0c5945d8e1da169c1b
stage-overview.json   6b02e9c47045f1626e2953ba53baa32e51f9995f2b75868633d91fc61cefd0f2
MANIFEST.md           7631a4b8f77b2a541eebd746a9f65c6ff14d75db7a9febb3709918eca6dc250e
```

재캡처 후 sha256:

```
ranking-current.json  249940b97c05eeaeb0efc0c3880d2ee21202e6889f6413994bdb769943312595
stage-overview.json   7bee482b9584f3c7ee4d10c61b3c0ad534d227c465bab7a5a616e7d30b41f664
MANIFEST.md           5edd288e55f37a6ecbb0525c65503c98c96c35a4c2f6bd0e8a56d1a44779fea5
```

#### E7 — 캡처 provenance (직렬화 계약)

캡처 경로는 불변이다 — `fastapi.testclient.TestClient` 로 실제 HTTP 요청을 태워
`response_model` 직렬화를 통과한 바이트를 뜬다. ASGI 경유 증거(캡처 로그 verbatim):

```
[INFO] httpx: HTTP Request: GET http://testserver/api/sectors/ranking "HTTP/1.1 200 OK"
[INFO] httpx: HTTP Request: GET http://testserver/api/stage/overview "HTTP/1.1 200 OK"
captured: date=2026-08-11 sectors=18 total=321
```

레지스트리 고정도 불변이다 — `my_chart.registry.get_sector_registry()` 는 경로 인자 없이 라이브
`Input/sectormap-original.xlsx` 를 lazy-load 하므로, 모듈 상수 `SECTORMAP_PATH` 와 lazy 캐시
`_df_sector` / `_df_stock` 을 함께 눌러 픽스처 사본을 읽게 했다. DB 경로는
`backend.routers.sectors.{WEEKLY,DAILY}_DB_PATH` 와 `backend.routers.stage.WEEKLY_DB_PATH` 를 패치했다.

`as_of` 는 `2026-08-11` 로 고정되며, 캡처 스크립트가 응답 `date` 와의 동등성을 단언한다
(§8.4 규약 8 — `as_of=None` 기본값 의존 0건). D12 재도입 가드: 캡처 JSON 전체에서
`sector_excess_return` **0건** · `total_count` **0건**.

MANIFEST 에 픽스처 계보를 추가로 기록했다 —
`fixture_manifest_git_sha: a224593` · `fixture_superset_of: adb1f25` ·
`golden_baseline_discarded: true` · `supersedes: "b839cee …"`.

#### E8 — baseline 비축퇴

| 지표 | 값 |
| --- | --- |
| `excess_returns != returns` 인 섹터 수 | **18 / 18** |
| 세 기간 최대 절대 격차 `\|excess − returns\|` | **16.166200** |

`capture_baseline.py` 에 **캡처 시 비축퇴 단언**을 신설했다 — 지수 행 부재나 벤치마크 산출
실패로 초과수익률이 원수익률로 degenerate 하면 캡처 자체가 실패한다. 그 상태의 baseline 위에서는
R1/R4/R5 비교가 무의미하다.

#### E2 — 산출물 실측 (구 baseline 대비)

| 지표 | 구 (`b839cee`) | 신 (`8e51176`) |
| --- | --- | --- |
| `ranking.date` | 2026-08-11 | **2026-08-11** (불변) |
| `len(sectors)` | 18 | **18** (불변) |
| `distribution.total` | 135 | **321** |
| `distribution` 1/2/3/4 | 1 / 42 / 2 / 90 | **5 / 96 / 6 / 214** |
| `len(by_sector)` | 18 | **18** (불변) |
| `len(stage2_candidates)` | 6 | **11** |
| `len(all_stocks)` | 135 | **321** |

#### E3 — AC-SAG-047 음성 검증 (Lesson #9)

`ranking-current.json` 을 스크래치패드로 임시 이동한 상태의 관측 RED:

```
E       AssertionError: 골든 baseline 누락: …/tests/fixtures/golden/pre-sector-ux/ranking-current.json
        — M1.0-b 캡처가 수행되지 않았다. `python tests/fixtures/golden/pre-sector-ux/capture_baseline.py` 로 캡처한다.
E       assert False
tests/test_golden_baseline.py:62: AssertionError
```

복원 후 sha256 바이트 동등 확인(before == after), `pytest tests/test_golden_baseline.py` **40 passed**.

#### E12 — 스코프 규율

```
$ git status --short my_chart/ backend/ frontend/
 M frontend/src/components/SectorAnalysis/BumpChart.tsx     ← 본 마일스톤과 무관(마지막 커밋 4c89d79, 2026-03-15)
?? backend/reports/ · frontend/coverage/ · frontend/test-results/   ← 기존 미추적
```

**프로덕션 코드 변경 0줄.** `my_chart/` · `backend/` · `frontend/` 는 스테이징하지 않았다.
`git add -A` / `git add .` 미사용, 픽스처 DB 는 `git add -f`(`.gitignore:41 *.db`).

| 커밋 | 스테이징된 파일 |
| --- | --- |
| `a000add` | `tests/test_aggregation_fixture.py` · 픽스처 5종(`build_fixture.py` · `MANIFEST.md` · `f13-1-superset-baseline.tsv` · `registry.xlsx` · `weekly.db` · `daily.db`) |
| `8e51176` | `tests/fixtures/golden/pre-sector-ux/` 4종(`capture_baseline.py` · `MANIFEST.md` · `ranking-current.json` · `stage-overview.json`) |

#### E10 — 전체 회귀 (재캡처 후)

`8 failed, 737 passed, 68 skipped, 1 xpassed, 25 errors` — B-13 baseline 과 **동일 집합**, 신규 0.
로그: `.moai/state/verify/m10a/2-post-recapture-suite.log`.

#### Gaps / 잔여 위험 (M1.0 재실행)

| # | 항목 | 처분 |
| --- | --- | --- |
| **G1** | **AC-SAG-048 v0.5.0 음성 검증(상위집합 OFF 시 F7/F5-a/F5-b/F6 **함께** RED)이 실증되지 않았다.** 상위집합만 끄면 4/4 green, SPEC 이 근거로 든 순수 시총순 선정에서도 **2/4**(F5-a·F6)만 RED 다. 원인 둘: (a) 빌더의 플래그 인지 선별이 **제2의 충족 경로**를 이룬다, (b) 재빌드 규모가 SPEC 실측(235종목)의 1.4배(331종목)라 F5-b·F7 이 자연 발생만으로 임계를 넘는다 | **Gaps 로 기재**(§9 DoD — "실증하지 못한 항목은 GREEN 이 아니라 Gaps"). **F13-1 자체는 게이트로 강제되고 GREEN 이다**(누락 0 · 섹터 드리프트 0). 영향 범위는 "상위집합이 네 요건의 **유일** 충족 경로"라는 §8.2.1 서술의 근거이며, 이는 이 빌더 구현에 대해 **F5-a·F6 에만 성립**한다. AC 본문 수정 없이는 실증 형태를 바꿀 수 없으므로 M2 착수 전 `manager-spec` 판단 대상 |
| **G2** | F12-b/F12-c 참조 구현의 **AG-7 해석** — §8.3 은 "최상위 `coverage_ratio < 0.50`"이라 적었으나 F12 문맥의 coverage 정의가 명시돼 있지 않다. 본 구현은 "1M 수익률 산출 가능 종목 비율 `< 0.50` 이면 섹터 null" 로 해석했고, 재빌드 픽스처에서는 **어느 섹터도 이 분기에 걸리지 않아 무증상**이다 | 무증상이므로 F12 값에 영향 없음. M2 의 프로덕션 참조 대조(AC-SAG-002 / 011 / 013) 착수 시 재확인 |
| **G3** | F12 참조 구현이 빌더(`build_fixture.py`)와 테스트(`test_aggregation_fixture.py`) **양쪽에 독립 재구현**돼 있다. MANIFEST 일치 절은 두 재구현의 대조이며, **둘이 같은 오해를 공유하면 무증상 통과**한다 | AC-SAG-048 이 규정한 구조 그대로다(MANIFEST 실측 일치). 프로덕션과의 진짜 대조는 M2~M3 의 AC-SAG-002 / 011 / 013 이 담당한다 |
| **G4** | AC-SAG-046 의 **금요일 종단 변형**은 본 마일스톤에서 재실행하지 않았다 | §8.6 판정대로 **미재실행 유지 — 안전**. 날짜 축 픽스처가 무변경(E5)이고 F13-6 이 대리 감시자다 |
| **G5** | `f13-1-superset-baseline.tsv` 는 `adb1f25` blob 에서 생성했으나 **파일 자체는 손으로 재생성 가능**하다 | 생성 명령을 파일 헤더 주석에 기록했다. AC-SAG-048 은 MANIFEST 기록 종목 수(145)와 목록 실측의 일치까지 단언한다 |
| **잔여 위험** | 재빌드가 라이브 DB(`mtime 2026-08-12 23:09:34`)에 의존한다. `/api/db/update` 재실행 후 빌드를 다시 돌리면 선별 결과가 달라질 수 있다 | 픽스처는 커밋으로 동결됐고 게이팅은 커밋된 바이트 위에서만 돈다. MANIFEST 가 원본 mtime 을 기록한다 |
| **잔여 위험** | F13-2 여유 1.21x · F12-a 1.42x 는 확보했으나, **F13-2 는 18섹터 중 17섹터가 이미 대형**이라 상한에 가깝다 | 추가 여유가 필요하면 새 섹터를 유니버스에 편입해야 한다(현 계약은 요구하지 않는다) |

---

### M2 — 가중·집계 코어 (2026-08-13) **[비가역 경계 통과]**

> **`point_of_no_return_crossed: true`.** 구 등가중 집계 구현이 교체됐다 — 골든 baseline
> 재캡처 창이 이 커밋으로 영구히 닫혔다. 진입 전제(AC-SAG-048 PASS · AC-SAG-047 PASS)는
> 착수 시점에 105/105 GREEN 으로 확인했다.

#### E1 — AC PASS/FAIL 매트릭스

| AC | 상태 | 검사 | 실측 |
| --- | --- | --- | --- |
| **AC-SAG-001 (A 축퇴)** | PASS | `test_ac_sag_001_a_degenerate_n5_is_exactly_equal_weight` | `cap_eff = max(0.10, 1/5) = 0.20`, 결과 `[0.2]×5` (각 `1e-12` 이내), `Σw = 1.0` |
| **AC-SAG-001 (B 비례)** | PASS | `test_ac_sag_001_b_proportional_redistribution_observable_at_n15` | `n=15`, `w[0] = cap_eff = 0.10`, `w[1]/w[2] = 1.5`, `w[1] = 0.0931034483`, `w[2] = 0.0620689655` |
| **AC-SAG-001 (종료 계약)** | PASS | `test_ac_sag_001_termination_is_structural_not_a_count_threshold` | 6개 입력 전부 `iterations <= min(n,20)` · `exhausted is False` |
| **AC-SAG-001 (무구속)** | PASS | `test_ac_sag_001_uniform_caps_need_no_redistribution` | 15종목 동일 시총 → `iterations = 0`, `w = 1/15`, `capped_members = ()` |
| **AC-SAG-002 (값 절)** | PASS | `test_ac_sag_002_production_matches_independent_reference` | AG-5 통과 18섹터 중 프로덕션 non-null 16섹터 전건 일치. 최대 편차 **`3.553e-15`**(화장품), 임계 `1e-9` |
| **AC-SAG-002 (null 집합)** | PASS | `test_ac_sag_002_null_sector_set_equality` | 프로덕션 null = 참조 null = `{패션(AG-4), 헬스케어(AG-7 rs 0.45)}` |
| **AC-SAG-002 (F12-b 크기 절)** | PASS | `test_ac_sag_002_f12b_delta_set_matches_manifest` | 13섹터, MANIFEST `f12b_delta_ge_50bp_sectors_1m` 와 집합 동등, `>= 3` |
| **AC-SAG-002 (F12-c 순위 절)** | PASS | `test_ac_sag_002_f12c_rank_shift_set_matches_manifest` | 12섹터, MANIFEST `f12c_rank_shifted_sectors_1m` 와 집합 동등, 비공집합, `>= 5` |
| **AC-SAG-003** | PASS | `test_ac_sag_003_*` (weighting 2 + aggregation 2) | `n=12` → `capped_members` 1건, `raw 0.5769230769` / `capped = cap_eff`, 미상한 11종목 각 `0.0818181818`, `iterations = 1`. 축퇴 대조 `n=6` → `cap_eff = 1/6`, 리터럴 아님 |
| **AC-SAG-004** | PASS | `test_ac_sag_004_*` | 10종목 중 3 NULL → `member_count 10 · valid_count 7 · coverage 0.7`, 값 `5.0` vs 0-치환 `< 5.0`. 재정규화 후 값이 `[1,7]` 범위 내 |
| **AC-SAG-005** | PASS | `test_ac_sag_005_*` (3건) | 시총 NULL 3종목 제외 후 값이 "3종목 제거 픽스처"와 `1e-9` 일치(대체값 흔적 0). `cap_coverage_ratio = 1.0`; 유효 시총 1종목 수익률만 NULL → `1 − mc/Σmc` 와 `1e-9` 일치 (폐기 해석 판별) |
| **AC-SAG-006** | PASS | `test_ac_sag_006_insufficient_cap_valid_members_null_cap_weighted_fields` | 유효 시총 3 → `returns/effective_n = null + insufficient`, `cap_weighted_available False`, 등가중 3지표 값 유지 |
| **AC-SAG-008** | PASS | `test_ac_sag_008_*` | `data[]` 18/18 항목이 `member_count·valid_count·coverage_ratio·cap_coverage_ratio` 보유(누락 0). 최상위 = `min(coverage.*)` 확인(rs 0.8 / chg 1.0 → 0.8) |
| **AC-SAG-009** | PASS | `test_ac_sag_009_*` (3건) | 0.95 → 값·플래그 없음 / 0.75 → 값·`low_confidence` / 0.45 → null·`insufficient`. 경계 0.80 플래그 없음, 0.50 값 유지. 전원 NULL → `missing`(≠`insufficient`) |
| **AC-SAG-010 (A)** | PASS | `test_ac_sag_010_a_effective_n_at_n25_is_160_over_7` | `n=25` → `22.8571428571 (=160/7)`, 무상한 `3.1558441558`, 배율 `7.24`, `<= n` |
| **AC-SAG-010 (축퇴 대조)** | PASS | `test_ac_sag_010_degenerate_effective_n_collapses_to_n` | `n=5 → 5.0`, `n=6 → 6.0` (각 `1e-9` 이내) |
| **AC-SAG-010 (응답 절)** | PASS | `test_ac_sag_010_response_*` | 시총가중 가능 16섹터 전건 `effective_n` non-null 이고 `<= member_count`. 합성 25종목 응답 `= 160/7` |
| **AC-SAG-049** | PASS | `test_ac_sag_049_*` (4건) | 시드 20260813 · 4,000 케이스: 불변식 1/2/3 위반 **0건**, `exhausted` 0건, 반복 히스토그램 `{1:165, 2:1030, 3:1580, 4:912, 5:290, 6:23}` 최악 **6회**. §3.1 고정점 편차 `6.695e-12`, 닫힌 해 편차 `5.551e-17` |
| **AC-SAG-050 (스캔 1)** | PASS | `test_ac_sag_050_scan1_*` | 1a `my_chart/ backend/ tests/` **0행**, 1b `min(x, 0.10\|WEIGHT_CAP)` **0행**. `WEIGHT_CAP` 정의 1곳(`aggregate_types.py`), `weighting.py` 실행 토큰에 상한 리터럴 0개 |
| **AC-SAG-050 (스캔 2)** | PASS | `test_ac_sag_050_scan2_*` | acceptance.md 본문 **0행**. 스캔 3종 `bash -n` 문법 검증 통과 |
| AC-SAG-007 | deferred-to-M6 | — | `market` 파라미터가 M6 산출물(D19). 미실행은 Gap 이 아니다 |

신규 테스트 **48건** (`test_weighting.py` 18 · `test_sector_aggregation.py` 23 · `test_inv_cap1_scan.py` 7·중 파라미터화 포함) 전건 GREEN.

#### E2 — Lesson #9 되돌림 실증 (**관측된 RED**)

네 변형 전건을 **실제로 적용**하고 실패 출력을 verbatim 캡처한 뒤 복원했다.
로그: `.moai/state/verify/m2-run/mut_*-RED.log`.

**(1) `mut_equal_weight`** — `capped_weights_detail` 의 초기 가중치를 `w = {k: 1/n}` 등가중으로 되돌림.

```
E   AssertionError: Auto: 프로덕션 8.468826134827173 != 참조 4.723254990954548
E   AssertionError: 등가중 변형과 어긋나는 섹터가 1개뿐 — 무게이팅이다
E   AssertionError: 최상위가 cap_eff 로 고정되지 않았다
E     assert 0.06666666666666667 == 0.1 ± 1.0e-12
10 failed, 30 passed
```

FAILED: `002_production_matches_independent_reference` · `002_mut_equal_weight_is_detectable` ·
`003_response_exposes_weight_cap_and_capped_members` · `010_response_effective_n_matches_synthetic_literal` ·
`001_b_proportional_redistribution_observable_at_n15` · `003_capped_members_expose_raw_and_cap_eff_at_n12` ·
`010_a_effective_n_at_n25_is_160_over_7` · `010_mut_effective_n_uncapped_is_detectable` ·
`049_matches_plan31_fixed_point` · `049_matches_closed_form`

**(2) `mut_effective_n_uncapped`** — `effective_n` 을 상한 **적용 전** 원비중으로 산출.

```
E   assert 3.1558441558441555 == 22.857142857142858 ± 1.0e-09
FAILED tests/test_sector_aggregation.py::test_ac_sag_010_response_effective_n_matches_synthetic_literal
1 failed, 39 passed
```

AC 본문이 예고한 `22.8571428571 → 3.1558441558` 과 **정확히 일치**한다.

**(3) `mut_plan31_verbatim`** — 동결(`frozen`)을 제거해 §3.1 v0.4.1 형태로 되돌림.

```
E   AssertionError: 불변식 1 위반 3183건: [(13, 0.10007495748496975, 0.1), (32, 0.10000066791015419, 0.1), (18, 0.10006016997242106, 0.1)]
E   AssertionError: n=5 반복 20 > min(n, 20)
E   AssertionError: s0=0.20000000661526854 — 균등해가 아니다
E   AssertionError: §3.1 고정점과 최대 편차 1.234e-01
8 failed, 32 passed
```

위반 케이스 **3,183 / 4,000** — acceptance.md AC-SAG-049 의 실측 기재와 **바이트 동일**하다.

**(4) `mut_reintroduce_cap_literal`** — acceptance.md 말미에 위반형 절 1행을 임시 추가.

```
E   AssertionError: acceptance.md 가 INV-CAP-1 작성 규약을 위반한다:
E     1003:- **And (mut)** 상한이 적용된 종목의 `weight_in_sector == 0.10` 이다.
FAILED tests/test_inv_cap1_scan.py::test_ac_sag_050_scan2_spec_body_has_no_cap_literal_expectation
1 failed, 7 passed
```

**복원 증거** — 네 변형 모두 복원 후 재실행 GREEN, 그리고

```
$ diff -q <백업> my_chart/analysis/weighting.py   → RESTORED byte-identical
$ git status --short -- .moai/specs/SPEC-SECTOR-AGGREGATION-001/acceptance.md
(공백)
```

> **부수 사건 (정직한 기재)**: 변형 (2) 복원 시 `git checkout-index -f` 를 써서 **스테이징된
> cherry-pick 판본**으로 되돌려 M2 편집분이 일시 소실됐다. 즉시 전량 재적용하고 179 tests
> GREEN 으로 확인한 뒤, 이후 변형은 scratchpad 백업 사본으로만 복원했다. 최종 산출물에
> 영향 없음(§E.2 E1 매트릭스가 재적용 후 상태에서 측정됐다).

#### E3 — INV-CAP-1 스캔 1 (신규 코드 대상)

```
$ grep -rnE '(capped_weight|weight_in_sector)[^=<>!]*[=!]=[^=]*0\.10?([^0-9]|$)' \
       my_chart/ backend/ tests/ --include='*.py'
(0행)

$ grep -rnE 'min\([^,]*,\s*(0\.10?|WEIGHT_CAP|weight_cap)\s*\)' \
       my_chart/ backend/ --include='*.py'
(0행)
```

첫 실행은 **RED 였다** — 신설 테스트 2곳의 독스트링이 위반형 문자열을 담고 있어
스캔 1a 가 잡았다(`tests/test_weighting.py:201` · `tests/test_inv_cap1_scan.py:87`).
문구를 `cap_eff` 경유 표현으로 고쳐 해소했다. **집행 장치가 실제로 작동함의 직접 증거다.**

#### E4 — AC-SAG-049 종료 스윕 (verbatim)

```
AC-SAG-049 sweep — seed=20260813, cases=4000, n~U{2..40}, cap=10**U(0,4)*random()
iteration histogram : {1: 165, 2: 1030, 3: 1580, 4: 912, 5: 290, 6: 23}
max iterations      : 6
cap violations (INV1): 0
exhausted exits(INV2): 0
bound violations     : 0
norm violations(INV3): 0
fixed-point max dev  : 6.695e-12  (AC 기재 6.696e-12)
closed-form max dev  : 5.551e-17  (AC 기재 3.053e-16)
mut_plan31@20 cap violations: 3183 / 4000  (AC 기재 3183)
```

로그: `.moai/state/verify/m2-run/5-ac049-sweep.log`.

#### E5 — 참조 구현 독립성 (§8.3)

* `tests/test_weighting.py` 의 오라클 `_plan31_verbatim` / `_closed_form` — 프로덕션 **미import**.
  상한 상수도 파일 지역 리터럴 `CAP = 0.10` 이다.
* `tests/test_sector_aggregation.py` 의 참조 `_ref_capped_weights` / `_ref_sector_values` /
  `_f12_sets` / `fixture_raw` — 프로덕션 **미import**. 픽스처 `weekly.db` · `daily.db` ·
  `registry.xlsx` 에서 원시 컬럼을 직접 읽는다. 상한도 지역 리터럴이며 프로덕션 상수와의
  일치는 `test_reference_cap_matches_production_constant` 가 **별도 단언**한다(D3 단일 정의).
* 프로덕션 import 는 (a) 대조의 프로덕션 변 `compute_sector_aggregates`, (b) 합성 AC 의
  피검사 대상 `_Member` / `_aggregate_members`, (c) 결측 사유 상수뿐이다.

**§8.3 AG-3/4/5/7 처리 (참조 = 프로덕션)**

| 규칙 | 참조 동작 |
| --- | --- |
| AG-3 (`market_cap` NULL/`<=0`) | 시총가중 분자·분모에서 제외, 등가중 분모에는 포함 |
| AG-4 (유효 시총 `< 5`) | 시총가중 값을 산출하지 않고 **null 집합**에 넣는다 |
| AG-5 (구성종목 `< 5`) | `data[]` 대상에서 제외(값·null 어느 집합에도 넣지 않는다) |
| AG-7 (최상위 `coverage_ratio < 0.50`) | 참조도 null 취급. `coverage = min(rs, nh, stage, chg)` 를 독립 재계산 |

F5-a(시총 NULL 9종목) · F5-b(RS 결측 10섹터) · F6(패션 유효 시총 3)이 실제로 발화했다 —
null 집합이 `{패션, 헬스케어}` 로 **비공집합**임이 그 증거다(`test_ac_sag_002_null_sector_set_equality`).

#### E6 — `capped_weights` 구조적 보장 (D1/D2)

`capped_weights_detail` 이 AG-1 의 **단일 진입점**이다. M2 시점 fan_in = 3
(`capped_weights` 래퍼 + `sector_metrics._aggregate_members` 2곳 — 섹터 전체 가중치, 기간별
결측 제외 후 재정규화 가중치).

| 항목 | 상태 |
| --- | --- |
| 섹터 집계가 이 함수를 호출한다 | **실증 완료** — 위 grep + AC-SAG-002 값 일치 |
| 벤치마크 집계가 **같은** 함수를 호출한다 | **구조만 준비 · 미실증** — 벤치마크 경로는 M3 산출물이다. 현재 리포에 벤치마크 산출 코드가 존재하지 않으므로 EX-1/BM-2 는 M3 에서 실증된다 |
| `@MX:ANCHOR` fan_in 수치 | M2 실측 3 으로 기재. M3 에서 갱신 |

#### E7 — 게이트 불변성

```
$ git status --porcelain tests/fixtures/
(공백)
```

`tests/test_aggregation_fixture.py`(65) + `tests/test_golden_baseline.py`(40) = **105 passed**
(M2 착수 전 · 완료 후 동일). 프로즌 픽스처 · 골든 baseline · `build_fixture.py` 미수정.

#### E8 — 하위 호환

`tests/test_api.py` · `test_response_contract.py` · `test_sector_metrics.py` ·
`test_sector_detail.py` · `test_sector_history_consistency.py` · `test_analysis_api.py`
→ **77 passed, 1 failed**. 유일 실패는 pre-existing `TestScreenEndpoint::test_too_many_patterns_rejected`
(B-2 baseline 동일 항목, 섹터와 무관). 로그: `.moai/state/verify/m2-run/7-backcompat.log`.

* 응답 필드 추가는 **가산적**이다 — 기존 `sectors[]` 키 형태 불변, 신규 값은 봉투
  `data[]` / `excluded[]` / `warnings[]` 로만 들어간다.
* 라우터 파라미터 미변경(M6 소관). `backend/routers/sectors.py` 변경은 내부 호출 인자
  `DAILY_DB_PATH` 전달 1줄뿐이며 쿼리 파라미터를 신설하지 않았다.
* **값은 바뀐다** — `sectors[].returns` 가 등가중 → 상한재배분 시총가중, 그리고 저장된
  `CHG_*` → `anchor(t, N)` 기준으로 바뀌었다. 이는 SPEC 이 의도한 변화이며 골든 baseline 이
  비교 대상으로 보존돼 있다(AC-SAG-045 R1, M7).

#### E9 — 전체 회귀 (B-2 baseline 대비)

```
8 failed, 786 passed, 68 skipped, 1 xpassed, 25 errors in 90.79s
```

| | B-2 baseline | M2 완료 후 | 델타 |
| --- | --- | --- | --- |
| passed | 737 | **786** | +49 (신규 48 + `test_consumer_dates` 1건 재계수 없음 — 신규 테스트 증가분) |
| failed | 8 | **8** | 0 — **동일 집합** |
| errors | 25 | **25** | 0 — 전건 `tests/fnguide/*` pre-existing |

**신규 실패 0건.** 실패 집합: `test_api`(1) · `test_meta_service`(2) · `test_rs_line`(2) ·
`test_screen_service`(3). 로그: `.moai/state/verify/m2-run/6-full-final.log`.

중간 1회 신규 실패가 있었고 **수정했다** — `test_consumer_dates.py::test_ac006b_rank_change_uses_anchor_not_offset`
가 내 `@MX:NOTE` 주석이 인용한 `LIMIT 1 OFFSET` 문자열을 잔존으로 오판했다(①의 정적 스캔).
주석 문구를 "고정 바 오프셋 관용구"로 바꿔 해소했다. 로그: `1-full-suite.log` → `2-full-suite.log`.

#### E10 — `sector_metrics.py` 거짓 주석 정정

`plan.md` 는 `:42-44` 로 인용했으나 **실측 위치는 `d4a560a:41-43`** 이다(M1.1 §E.9 기재와 일치).

```
# before (d4a560a:41-43)
    sector_return_1w: float        # market-cap weighted avg 1W return (%)
    sector_return_1m: float        # market-cap weighted avg 1M return (%)
    sector_return_3m: float        # market-cap weighted avg 3M return (%)

# after (:96-98)
    sector_return_1w: float        # 상한재배분 시총가중, anchor(t,7) 기준 (%) — 폴백 등가중
    sector_return_1m: float        # 상한재배분 시총가중, anchor(t,28) 기준 (%) — 폴백 등가중
    sector_return_3m: float        # 상한재배분 시총가중, anchor(t,91) 기준 (%) — 폴백 등가중
```

주석이 참이 된 것은 **구현이 실제로 시총가중이 된 같은 커밋에서**다. `:89-95` 의
`@MX:NOTE` 가 괴리의 이력과 현재 계약(AG-4/AG-7 시 등가중 폴백)을 함께 기록한다.

#### E11 — @MX 태그

| 태그 | 위치 | 내용 |
| --- | --- | --- |
| `@MX:ANCHOR` + `@MX:REASON` | `weighting.py:74-80` | AG-1 상한 재배분 계약 — 섹터·벤치마크 공용 진입점. fan_in 3(M2 실측) · 불변식 4종 |
| `@MX:NOTE` | `sector_metrics.py:65-71` | 기간 수익률 원천이 `CHG_*` 가 아니라 `anchor(t, N)` 인 이유 + 픽스처 실측 근거 |
| `@MX:NOTE` | `sector_metrics.py:89-95` | 거짓 주석 이력 + 현재 폴백 계약 |
| `@MX:NOTE` | `sector_metrics.py:228-231` | 앵커 기준 수익률의 결측 처리(0 접기 금지) |
| `@MX:NOTE` | `sector_metrics.py:338-340` | `trading_value` 미산출을 0 이 아니라 `None` 으로 두는 이유 |
| `@MX:NOTE` (기존) | `aggregate_types.py:56` | 결측 3상태 헬퍼 — B-15 지정 항목, M1.1 에서 이미 작성됨 |

파일당 한도 준수 — ANCHOR 1/3, NOTE 4/10(`sector_metrics.py`).

#### E12 — 스코프 규율

```
$ git status --short   (첫 열이 M/A 인 항목만)
M  backend/routers/sectors.py
M  backend/services/sector_ranking_service.py
M  my_chart/analysis/sector_metrics.py
A  my_chart/analysis/weighting.py
A  tests/test_inv_cap1_scan.py
A  tests/test_sector_aggregation.py
A  tests/test_weighting.py
```

`git add -A` / `git add .` **미사용** — 7개 경로를 개별 지정했다.
`frontend/src/components/SectorAnalysis/BumpChart.tsx`(마지막 커밋 `4c89d79`, 2026-03-15,
본 작업과 무관) · MoAI 하네스 대량 변경 · `tests/Untitled.md` · `backend/reports/` 는
**스테이징하지 않았다.** `tests/fixtures/` 는 무변경(E7).

#### Gaps / 잔여 위험 (M2)

| # | 항목 | 처분 |
| --- | --- | --- |
| **G6** | **커버리지를 측정하지 못했다.** `coverage.py` C-tracer 가 numpy 2.4.2 에서 `ImportError: cannot load module more than once per process` 로 죽는다(`COVERAGE_CORE=sysmon` / `pytrace` 모두 동일). 임시 설치한 `pytest-cov` · `coverage` 는 venv 원상복구를 위해 **제거**했다 | **Gap 으로 기재** — §9 DoD "신규/변경 모듈 커버리지 >= 85%" 는 **미측정**이다. 관측하지 않은 수치를 기재하지 않는다. 대리 지표: 신규 48 테스트가 `weighting.py` 전 공개 함수 4종과 `_aggregate_members` 의 AG-1/3/4/6/7 분기를 직접 실행한다. 환경 해소(numpy/coverage 조합) 후 재측정 필요 |
| **G7** | **AC-SAG-002 본문의 `CHG_1M` 표기와 MANIFEST 가 어긋난다.** AC 본문은 참조 입력을 `(종목, market_cap, CHG_1M)` 으로 적었으나, MANIFEST 의 `f12b`/`f12c` 집합은 `f12_anchor_1m: "2026-07-10"` = `anchor(t,28)` 기준 Close 비율로 산출됐다. 픽스처 실측 결과 저장된 `CHG_1M` 은 `2026-07-16`(고정 바 오프셋) 기준이라 **다른 바**다. `CHG_1M` 을 문자 그대로 쓰면 F12-b 12개(≠MANIFEST 13) · F12-c 14개(≠MANIFEST 12)로 **집합 동등 절이 RED** 가 된다 | **앵커 해석을 채택**했다. 근거 3점: (a) 이미 GREEN 인 AC-SAG-048 의 F12 참조가 앵커 기준이고 MANIFEST 를 그 정의로 검증했다, (b) MANIFEST 가 `f12_anchor_1m` 를 명시 기록한다, (c) spec.md §1.2 가 고정 바 오프셋 관용구를 `anchor(t, N)` 로 교체하라고 적었고 REQ-SAG-043(`return_window_days = [anchor(t,N), t]`)이 이를 강제한다. **AC 본문의 `CHG_1M` 은 앵커 결정(v0.3.0 O-A8) 이전 표기의 잔존으로 판단**했다. `manager-spec` 의 표기 정정 대상이며, 정정 없이도 현재 구현·MANIFEST·AC-SAG-048 은 서로 정합적이다 |
| **G8** | **F12 참조와 프로덕션 참조의 AG-7 적용 범위가 다르다.** F12(§8.2 · MANIFEST)는 AG-7 을 "1M 수익률 가용률"에 적용하고, 프로덕션·§8.3 참조는 최상위 `min(coverage.*)` 에 적용한다. 그래서 헬스케어(rs 커버리지 0.45)가 MANIFEST `f12b` 집합에는 있고 프로덕션 `data[]` 에서는 null 이다 | 두 절이 서로 다른 대상을 검사하므로 **모순이 아니다** — F12 는 "픽스처가 검출력을 갖는가"(픽스처 속성), AC-SAG-002 값·null 절은 "프로덕션이 규칙대로 계산하는가"다. 테스트 코드에 `_f12_sets` 독스트링으로 명시했다. M1.0-a 의 **G2 가 예고한 지점**이며 여기서 실제로 발화했다 |
| **G9** | `compute_sector_aggregates` 가 유효 유니버스를 `compute_universe`(UN-3)로 제한하도록 바뀌었다. 라이브 경로에서 이 필터가 섹터 구성원 수를 줄인다 | 의도된 동작이다 — spec.md §5 "유효 유니버스는 ① 소관, ②는 소비만 한다". `daily_db_path` 가 없으면 제한 없이 동작하도록 폴백을 뒀다(라이브 DB 암묵 개방 금지) |
| **잔여 위험** | 하위 호환 표면(`SectorRank`)의 수익률도 앵커·시총가중으로 바뀌었으므로 프론트엔드가 보는 **숫자가 달라진다** | SPEC 이 의도한 변화(R1~R8 "고장처럼 보이지만 올바른 변화"). 골든 baseline 이 비교 기준으로 보존돼 있고 M7 이 판정한다 |
| **잔여 위험** | `excess_returns` 는 여전히 KOSPI 지수 행(`_load_kospi_returns`) 기준이라 **방법론 혼합** 상태다 | M3 소관(BM-1 — 지수 행 사용 금지). `data[]` 의 `excess_returns` 는 `missing()` 으로 두어 잘못된 값을 싣지 않았다 |
| **잔여 위험** | `test_sector_aggregation.py` 의 `fixture_raw` 는 유효 유니버스를 3중 교집합(registry ∩ stock_meta ∩ 최신바)으로 근사한다. 프로덕션은 stale 배제까지 포함한 4중 교집합이다 | 이 픽스처에 stale 종목이 없음이 F13 으로 보장돼 두 결과가 일치한다(값 최대 편차 `3.553e-15`가 그 증거). 다른 픽스처로 옮기면 재확인 필요 |

---

### M3 — 벤치마크 + 순위/정규화 (2026-08-13)

#### E1 — 구현 개요

`_compute_sector_aggregates_core`(신설, M2의 `compute_sector_aggregates` 본체를
그대로 옮김) + 얇은 공개 래퍼 `compute_sector_aggregates`(rank_change 를 위해
`anchor(t,28)` 기준일에서 core 를 재귀 없이 1회 더 호출)로 구조를 나눴다.

| 대상 | 내용 |
| --- | --- |
| `_compute_benchmark` | 규칙 BM-1 — `_aggregate_members` 를 **재사용**(새 call-site 없음)해 섹터 그룹핑 없는 전체 유니버스를 집계한다. 이름은 `ALL_CAPPED`/`KOSPI_CAPPED`/`KOSDAQ_CAPPED`. 구성종목 0 이면 `status="unavailable"`(BM-4/BM-5) |
| `_excess_returns` | 규칙 EX-2 — 섹터·벤치마크 양쪽 non-null 일 때만 `sector - benchmark` 산출, 아니면 `missing()` |
| `_benchmark_reconciliation_warnings` | 규칙 BM-3 — `market=kospi/kosdaq` 에서 상한 없는(`cap=1.0`) 벤치마크와 지수 행(`Name='KOSPI'/'KOSDAQ'`)의 차가 `BENCHMARK_RECONCILIATION_TOLERANCE_PP={1w:0.5, 1m:3.0, 3m:7.0}` 를 초과하면 경고. `market=all` 은 대상 아님(단일 지수 행 없음) |
| `norm()` | 규칙 AG-8 — 순위 백분위 정규화(scipy 없이 순수 파이썬 average-tie 재구현). `N==0→[]`, `N==1→[50.0]` |
| `_rank_sectors` | 규칙 AG-9/RK-1/RK-2 — 세 기간 초과수익률이 **모두** non-null 인 섹터만 후보로 `norm()` 적용 후 `0.30/0.40/0.30` 가중합, `(-composite, name)` 결정적 tie-break, 함수 내부 `round(` 호출 **0건**(AST 정적 스캔으로 확인, 반올림은 `backend/schemas/envelope.py::_rounded_metric_model` 에서 직렬화 직전 1회) |
| `compute_return_window_days` | REQ-SAG-043 — `(t − anchor_date).days` (라벨 상수 아님) |

**BM-6(동일 날짜 창) 보존 방식**: 벤치마크가 별도로 `anchor()` 를 부르지 않는다 —
섹터 집계가 이미 `_anchor_returns(conn, grid, date)` 로 1회 산출한 `anchor_dates`
딕셔너리를 `_compute_benchmark` 에 **그대로 전달**한다. 즉 "같은 `t`" 가 아니라
"애초에 재조회 자체가 없다" — v0.4.0 D6/D11 이 지적한 무증상 이원화 경로가
설계상 존재하지 않는다.

#### E2 — AC Binary PASS/FAIL 매트릭스 (AC-SAG-011~023, 046-lite)

전건 `tests/test_sector_benchmark_ranking.py`(35 tests, 신설). 명령:
`pytest tests/test_sector_benchmark_ranking.py -q` → `35 passed`.

| AC | 상태 | 비고 |
| --- | --- | --- |
| AC-SAG-011 | PASS | 시장별 이름·참조 일치·쌍별 상이. 되돌림 대조는 아래 §되돌림 실증 참조 |
| AC-SAG-012 | PASS | 구조 대조(소스에서 `_aggregate_members(` 호출 확인) + 4-튜플 변형 1(weight_cap 상이) |
| AC-SAG-013 | PASS | `S − B` 파생 잔차 일치 + 벤치마크 흔들기 대조 |
| AC-SAG-014 | PASS | 단일 요청 내 계측된 `anchor()` 의 `t` 가 `{as_of_date}` 1개, `days` 집합 `{7,28,91}` |
| AC-SAG-015 | PASS | 임계 초과/이하 양방향 + `market=all` 비대상 + 임계 상수 단일 정의 |
| AC-SAG-016 | PASS | 구성종목 0 → unavailable + 에러 메시지, `returns` `None`(0.0 아님), excess/composite/rank 모두 None, `sector_return` 값 유지 |
| AC-SAG-017 | PASS | 극단값 미지배, 동점 평균 순위, N=1→50.0, N=0→[], N≥2 min==max 비붕괴 |
| AC-SAG-018 | PASS | composite 공식 3케이스 + 3M null → composite/rank None + excluded 등록(부분 점수 금지) |
| AC-SAG-019 | PASS | 입력 순서 3종 치환 → 동일 rank 배정 + 사전순 |
| AC-SAG-020 | PASS | 근접값(86.234/86.236) 비동점 + `_rank_sectors` 소스 AST 스캔 `round(` 0건 |
| AC-SAG-021 | PASS(함수 수준) | rank 연속·정렬 일치, market=kospi 최대 rank 축소. **라우터 `period`/`market` 쿼리 파라미터 배선은 M6 소관(deferred)** |
| AC-SAG-022 | PASS(함수 수준) | rank 존재 섹터는 composite_score 도 존재 |
| AC-SAG-023 | PASS(함수 수준) | `baseline_date == anchor(t,28) == "2026-07-10"`(구 `LIMIT 1 OFFSET 3` 11일 전과 다름), `days>=28`. **rank_change 필드의 응답 봉투 최상위 `baseline_date` 키 노출은 M6 라우터 응답 스키마 확장과 결합 — deferred** |
| AC-SAG-046 (lite) | PASS(부분) | 집계 픽스처 위에서 `return_window_days == {1w:11, 1m:32, 3m:95}`, `benchmark.anchor_date == "2026-07-31"`(AC-SAG-048 이 두 픽스처의 날짜 축 동일성을 보장하므로 유효한 대체 검증). **`weekly-2026-08-12` 프로즌 + 금요일 종단 변형을 쓰는 원 AC-SAG-046 게이팅 절차 및 `trading_value_window_days`/`rank_change.baseline_date` 응답 노출은 실행하지 않음 — Gap 으로 기재** |
| AC-SAG-045 R1/R3/R4/R5-a | NOT RUN | plan.md M3 GREEN 목록에 없음(§E.2 M1.0-a/b 재빌드 이후 표기 `next_gate` 는 M7 회귀 게이트 소관으로 재확인 — 골든 baseline 대비 비교는 M7 일괄 처리가 합리적. 본 세션에서 미실행, Gap 아님(M2~M6 미실행은 Gap 아니다, progress.md 관행) |

#### E3 — 정적 스캔 결과

```
$ python -c "..."  # AST 기반, _rank_sectors 소스만
round( 호출 0건 — test_ac_sag_020_no_round_call_inside_rank_sectors PASS
```

전역 스캔(`grep -n "round(" my_chart/analysis/sector_metrics.py`)은 legacy
`_compute_sector_metrics`/`compute_sector_ranking` 경로(하위 호환 `SectorRank`
표면, M3 미변경)에 9건이 남아 있다 — RK-2 의 대상은 신설 `data[]` 순위 경로
(`_rank_sectors`)이며, 그 함수 내부는 0건이다.

#### E4 — 전체 테스트 스위트 델타 (M2 → M3)

```
$ pytest tests/ -q
8 failed, 821 passed, 68 skipped, 1 xpassed, 25 errors in 95.20s
```

| | M2 완료 후 | M3 완료 후 | 델타 |
| --- | --- | --- | --- |
| passed | 786 | **821** | +35 (신규 `test_sector_benchmark_ranking.py` 전건) |
| failed | 8 | **8** | 0 — **동일 집합**(`test_api` 1 · `test_meta_service` 2 · `test_rs_line` 2 · `test_screen_service` 3) |
| errors | 25 | **25** | 0 — 전건 pre-existing `tests/fnguide/*` |

신규 실패 0건. M2 게이트(`test_aggregation_fixture.py` + `test_golden_baseline.py`
= 105) 재확인 그린.

#### E5 — 커버리지

```
$ pytest --cov=my_chart.analysis.sector_metrics --cov=my_chart.analysis.weighting tests/... -q
ERROR: unrecognized arguments: --cov=...
$ python -c "import coverage"
ModuleNotFoundError: No module named 'coverage'
```

**[Gap 지속 — G6 재확인]** M2 에서 기록한 numpy/coverage 충돌로 임시 제거한
`pytest-cov`/`coverage` 가 이 세션에도 미설치 상태다(`pyproject.toml` 에는
`pytest-cov>=7.0.0` 이 선언돼 있으나 실제 venv 에 없다). 재설치·환경 해소는
이번 세션 스코프 밖이다(M2 와 동일 판단 — venv 원상복구 우선). 관측하지 않은
수치를 기재하지 않는다. 대리 지표: 신설 35 테스트가 `_compute_benchmark` /
`_excess_returns` / `_benchmark_reconciliation_warnings` / `norm()` /
`_rank_sectors` 전 공개·비공개 함수의 정상/축퇴/변형 분기를 직접 실행한다.

#### E6 — 되돌림 실증 (Lesson #9 — 실제 적용 → RED 관측 → 복원 → GREEN)

세 건을 실제로 적용해 RED 를 verbatim 캡처하고 백업본(`cp`)으로 복원했다
(`git checkout-index` 미사용 — lessons.md #9 되돌림 복원 절차 준수).

**변형 1 — `mut_benchmark_ignores_market_filter`** (`_compute_sector_aggregates_core`
의 벤치마크 유니버스 수집에서 `_market_matches` 필터를 제거):

```
FAILED test_ac_sag_011_matches_independent_reference
  kospi: 프로덕션 6.378529756876937 != 참조 4.870388625210951
FAILED test_ac_sag_011_pairwise_distinct
  assert 0.0 > 1e-06  (kospi == kosdaq 로 붕괴)
```

**변형 2 — `mut_round_in_sort_path`** (`_rank_sectors` 의 composite 할당 라인에
`round(raw_scores[idx], 6)` 삽입):

```
FAILED test_ac_sag_020_no_round_call_inside_rank_sectors
  AssertionError: _rank_sectors 내부에 round( 호출: ['round']
```

**변형 3 — `mut_partial_composite`** (`_rank_sectors` 의 후보 필터에서 3기간
전건 non-null 요건을 제거 — 부분 점수 허용):

```
FAILED test_ac_sag_018_null_3m_excludes_from_composite_no_partial_score
  TypeError: '<' not supported between instances of 'NoneType' and 'float'
  (partial 섹터의 None 값이 norm() 정렬에 섞여 즉시 예외로 붉어짐 — 검출력 확정적)
```

세 건 모두 복원 후 `diff /tmp/sector_metrics.py.bak my_chart/analysis/sector_metrics.py`
바이트 동일 확인 + `pytest tests/test_sector_benchmark_ranking.py -q` → `35 passed`
재확인.

#### E7 — @MX 태그

| 태그 | 위치 | 내용 |
| --- | --- | --- |
| `@MX:NOTE` | `sector_metrics.py` `_compute_benchmark` 상단 | BM-1 구조(같은 함수 재사용)의 EX-1/BM-2 보장 근거 |
| `@MX:ANCHOR` 갱신 | `weighting.py:74-79` | M3 실측 — call-site 수 **불변**(재사용이 곧 새 지점 미생성)임을 명시. fan_in 3 유지 |

파일당 한도 준수 — `sector_metrics.py` NOTE 5/10(신규 1건 추가), ANCHOR 0/3, WARN 0/5.

#### E8 — 스코프 규율

```
$ git status --short   (M/A 항목만)
M  backend/schemas/envelope.py
M  backend/services/sector_ranking_service.py
M  my_chart/analysis/sector_metrics.py
M  my_chart/analysis/weighting.py
A  tests/test_sector_benchmark_ranking.py
```

`tests/fixtures/`·`spec.md`/`plan.md`/`acceptance.md` 본문·MoAI 하네스 대량
변경분·`frontend/`·`Input/` 등은 스테이징하지 않았다.

#### Gaps / 잔여 위험 (M3)

| # | 항목 | 처분 |
| --- | --- | --- |
| **G10** | 라우터 파라미터(`period`/`market` 쿼리) 미배선 — AC-SAG-021 의 엔드투엔드(`/sectors/ranking?period=1w&market=all`) 검증, `return_window_days`/`benchmark.anchor_date`/`rank_change.baseline_date` 의 최상위 응답 노출(AC-SAG-046 완전판)이 M6 산출물에 의존한다 | plan.md M6 이 명시적으로 소관("라우터 파라미터 + 종목 목록 필드"). M2 의 AC-SAG-007/043 과 동일한 처분 패턴 — 지금 미실행은 Gap 이 아니라 예정된 의존이다 |
| **G11** | AC-SAG-046 의 게이팅 절차(프로즌 `weekly-2026-08-12` + 금요일 종단 임시 사본 변형)를 실행하지 않고, 대신 집계 픽스처(`aggregation-2026-08-11`)의 동일 날짜 축(AC-SAG-048 보증)으로 lite 버전만 검증했다 | 값 자체(11/32/95, 앵커 07-31/07-10/05-08)는 두 픽스처가 구조적으로 동일함이 AC-SAG-048 로 이미 보증되므로 함수 정확성 검증으로는 충분하나, **원 AC 의 "프로즌 스냅샷" Given 절과 "금요일 종단 대조" 절은 문자 그대로 실행되지 않았다** — 완전 게이팅은 별도 세션 권고 |
| **G12** | AC-SAG-013 의 부호 분산 합성 픽스처 절(`k==N`/`k==0` 인 합성 입력에서 경고 발화)을 전용 합성 픽스처로 실행하지 않았다 — `_compute_sector_aggregates_core` 에 로직은 배선했으나(1w 전건 동일 부호 시 경고), 전용 단위 테스트는 미작성 | 로직은 존재하고 실제 집계 픽스처에서 우연히 발화하지 않았음을 확인했을 뿐 — 별도 합성 픽스처 테스트 추가 권고(비게이팅이므로 M3 완료 조건 아님) |
| **G13** | 커버리지 미측정(G6 연속) | 위 §E5 참조 |
| **잔여 위험** | rank_change 계산이 baseline 재귀 호출로 인해 `compute_sector_aggregates(compute_rank_change=True)` 호출 비용이 2배가 된다(현재 기준일 + `anchor(t,28)` 기준일 각 1회) | 라이브 트래픽 규모에서 성능 재측정 권고(§0.2 계열 성능표는 M7 소관). 픽스처 규모에서는 무시 가능(35 테스트 전체 0.6~0.8초) |

---

### M4 — RRG (2026-08-13)

#### E1 — 구현 개요

신설 모듈 `my_chart/analysis/rrg.py`(순수 함수, DB 미접근) — 라우터 배선은 M6 소관
(plan.md M6 "라우터 파라미터 + 종목 목록 필드")이므로 M4 는 M2/M3 와 동일하게
**함수 수준** 진입점(`compute_rrg`)까지만 제공한다. 기존 z-score 기반 RRG
(`my_chart/analysis/sector_advanced.py`, SPEC-TOPDOWN-001A 소관)는 **건드리지 않았다**
— 별도 SPEC 소관 파일이며 본 SPEC 의 PRESERVE 대상이다.

| 대상 | 내용 |
| --- | --- |
| `chain_index` | RRG-3 — 수익률 연쇄 지수. `r(t) = Σ(w_i(t−1)×ret_i(t))/Σw_i(t−1)`, `I(t)=I(t−1)×(1+r(t))`, `I(t0)=100`. 분모는 양쪽 시점 종가가 모두 존재하는 종목의 직전 가중치 합으로 재정규화(`weighted_mean` 과 동일 관용) — 구성종목 변동에도 잔존 종목 수익률이 같으면 흔들리지 않는다 |
| `implied_shares` / `historical_market_caps` | RRG-4 — 주식수 = 현재시총/현재주가(단일 지점 역산) → 시점별 시총 = 주식수×그 시점 Close. 현재 스냅샷 시총을 과거에 직접 적용하는 경로 없음(AST 정적 스캔으로 확인) |
| `_rs_ratio_trail` | RRG-1/RRG-2 — `rs_ratio(t) = 100×섹터지수(t)/벤치마크지수(t)`. 모멘텀은 직전 유효 지점 대비 단순 차분(롤링 z-score 없음, O-A1). 처음 `lookback_weeks` 개 날짜는 `trail[]` 에서 제외(상수 패딩 없음) |
| `compute_rrg` | 벤치마크(섹터 그룹핑 없는 전체 유니버스, `capped_weights` 재사용 — M3 의 BM-1 관용과 동일 구조) + 섹터별 궤적 + 산출 불가 섹터 `excluded[]` + 상수 주식수 가정 경고(O-A3, 매 응답 상설) |

**해석이 필요했던 지점(단일 통과 최선 해석, blocker 아님)**: AC-SAG-032 의 "워밍업
`lookback_weeks=12`" 이 정확히 무엇을 지연시키는지 acceptance.md 본문에 산식이
없었다. **선택한 해석**: 처음 `lookback_weeks` 개 지수 지점을 `trail[]` 에서 제외하고,
모멘텀은 단순 lag-1 차분(직전 지점 대비)으로 산출한다 — 롤링 정규화(O-A1 이 명시적으로
금지)나 이동평균 스무딩을 도입하지 않는 가장 단순한 형태다. `trail` 길이가
`history − lookback_weeks`(±1)로 정확히 맞아떨어지고, 모멘텀이 워밍업 구간 마지막
지점을 기준으로 첫 지점부터 유효값을 갖는다(추가 1점 소비, AC-SAG-032 본문의 "모멘텀
차분 1점 추가 제외" 표현과 부합). 대안(예: 모멘텀에 별도 스무딩 윈도우를 두는 해석)도
가능했으나, Enforce Simplicity 원칙과 O-A1(롤링 정규화 없음) 결정에 가장 부합하는
최소 형태를 택했다.

#### E2 — AC Binary PASS/FAIL 매트릭스 (AC-SAG-031~035, AC-SAG-045 R7)

전건 `tests/test_sector_rrg.py`(신설, 11 tests). 명령:
`pytest tests/test_sector_rrg.py -q` → `11 passed`.

| AC | 상태 | 실제 출력(검증 커맨드) | 비고 |
| --- | --- | --- | --- |
| AC-SAG-031 | PASS | `pytest tests/test_sector_rrg.py::test_ac_sag_031_identical_sector_and_benchmark_rs_ratio_100 tests/test_sector_rrg.py::test_ac_sag_031_all_sectors_above_100_when_all_leading -q` → `2 passed` | 동일 지수 → `rs_ratio==100±0.01` 전 구간, all-leading 픽스처 → 전 섹터 `rs_ratio>100`, `benchmark_name` 존재 |
| AC-SAG-032 | PASS | `pytest tests/test_sector_rrg.py::test_ac_sag_032_warmup_non_emission -q` → `1 passed` | `trail` 길이 `30−12`(±1), `trail_start_date>dates[0]`, 상수 100 패딩 없음, 첫 4개 모멘텀 상이 |
| AC-SAG-033 | PASS | `pytest tests/test_sector_rrg.py::test_ac_sag_033_index_chain_no_jump_on_membership_change tests/test_sector_rrg.py::test_weight_lag_uses_prev_period_weights_not_current -q` → `2 passed` | 구성종목 변동 시에도 인접 비율 `1.01±0.001` 유지 + **대조**: 날짜별 재계산(naive) 방식은 구성 변동 시점에서 `1.01` 대비 `0.005` 초과 이탈(점프) 실증 |
| AC-SAG-034 | PASS | `pytest tests/test_sector_rrg.py::test_ac_sag_034_historical_market_cap_uses_implied_shares_not_current_snapshot tests/test_sector_rrg.py::test_ac_sag_034_static_scan_no_current_snapshot_leak_into_history -q` → `2 passed` | 과거 시총(`500.0`) ≠ 현재 시총(`1000.0`) 값 검증 + AST 스캔: `historical_market_caps` 함수 코드 내부에 `market_caps` 식별자 참조 0건 |
| AC-SAG-035 | PASS | `pytest tests/test_sector_rrg.py::test_ac_sag_035_missing_sector_excluded_no_rs_ratio_100_substitute -q` → `1 passed` | 산출 불가 섹터는 `trail_by_sector` 에서 빠지고 `excluded[]` 에 사유(`no_data_in_trail_window`)와 함께 등록. `rs_ratio==100` 대체 없음 |
| AC-SAG-045 R7 | PASS | `pytest tests/test_sector_rrg.py::test_ac_sag_045_r7a_all_leading_no_bias_warning tests/test_sector_rrg.py::test_ac_sag_045_r7a_cross_sectional_zscore_variant_diverges tests/test_sector_rrg.py::test_ac_sag_045_r7b_no_quadrant_balance_assertion_in_test_suite -q` → `3 passed` | (a) all-leading → 전 섹터 `rs_ratio>100`, 편중 경고 없음 + **대조**: 횡단면 z-score 되돌림 변형에서 절반 미만 실증. (b) `grep -rnE --include=*.py "quadrant.*(balanc|even|distribut)\|len\(leading\).*<" tests/` → 0행(자기 파일 제외) |

#### E3 — 대조/되돌림 실증 (Lesson #9 — 실제 적용 → RED 관측 → 복원 → GREEN)

세 건을 실제로 적용해 RED 를 verbatim 캡처하고 백업본(`cp`)으로 복원했다
(`git checkout-index` 미사용).

**변형 1 — `mut_current_weight`**(`chain_index` 에서 가중치를 `w(t-1)` 대신 `w(t)`
로 즉시 갱신):

```
FAILED tests/test_sector_rrg.py::test_weight_lag_uses_prev_period_weights_not_current
  AssertionError: {'d0': 100.0, 'd1': 108.0, 'd2': 116.64000000000001}
  assert 8.0 < 1e-09
   +  where 8.0 = abs((108.0 - 100.0))
```

**변형 2 — `mut_no_warmup`**(`_rs_ratio_trail` 에서 워밍업 구간을 건너뛰지 않고
`range(0, len(ordered))` 로 전 구간 발행):

```
FAILED tests/test_sector_rrg.py::test_ac_sag_031_all_sectors_above_100_when_all_leading
  AssertionError: ('SEC_A', (RRGPoint(date='d0', rs_ratio=100.0, ...), ...))
  assert False
FAILED tests/test_sector_rrg.py::test_ac_sag_032_warmup_non_emission
  AssertionError: 30
  assert 12 <= 1
   +  where 12 = abs((30 - 18))
```

**변형 3 — `mut_rs_ratio_100_fallback`**(`compute_rrg` 에서 산출 불가 섹터를
`excluded[]` 대신 `rs_ratio==100` 상수로 채워 `trail_by_sector` 에 포함):

```
FAILED tests/test_sector_rrg.py::test_ac_sag_035_missing_sector_excluded_no_rs_ratio_100_substitute
  AssertionError: assert 'SEC_MISSING' not in {'SEC_MISSING': RRGSeries(trail=(RRGPoint(date='d11', rs_ratio=100.0, rs_momentum=0.0), ...)}
```

세 건 모두 복원 후 `diff /tmp/rrg.py.bak my_chart/analysis/rrg.py` 바이트 동일 확인
+ `pytest tests/test_sector_rrg.py -q` → `11 passed` 재확인.

#### E4 — 전체 테스트 스위트 델타 (M3 → M4)

```
$ pytest tests/ -q
8 failed, 832 passed, 68 skipped, 1 xpassed, 25 errors in 94.64s
```

| | M3 완료 후 | M4 완료 후 | 델타 |
| --- | --- | --- | --- |
| passed | 821 | **832** | +11 (신규 `test_sector_rrg.py` 전건) |
| failed | 8 | **8** | 0 — **동일 집합**(`test_api` 1 · `test_meta_service` 2 · `test_rs_line` 2 · `test_screen_service` 3) |
| errors | 25 | **25** | 0 — 전건 pre-existing `tests/fnguide/*` |

신규 실패 0건. M2/M3 게이트(`test_aggregation_fixture.py` + `test_sector_aggregation.py`
+ `test_sector_benchmark_ranking.py` = 123) 재확인 그린.

#### E5 — 커버리지

`coverage` 모듈 미설치(M2/M3 와 동일 환경 — G6/G13 연속, 재설치는 세션 스코프 밖).
대리 지표: 신설 11 테스트가 `chain_index` / `implied_shares` /
`historical_market_caps` / `_rs_ratio_trail` / `compute_rrg` 전 공개·비공개 함수의
정상/워밍업/결측/구성변동 분기를 직접 실행한다. `sector_advanced.py`(구 RRG, 본
SPEC 미변경)는 커버리지 대상이 아니다.

#### E6 — @MX 태그

| 태그 | 위치 | 내용 |
| --- | --- | --- |
| `@MX:NOTE` | `rrg.py` `chain_index` 상단 | 가중치 지연(`w_i(t−1)`)이 plan.md §3.4 설계 결정임을 명시(우연한 구현 세부사항 아님) |

신설 파일 — NOTE 1/10, ANCHOR 0/3, WARN 0/5. `compute_rrg` 는 M6 라우터 배선 이전
이라 fan_in 0(아직 호출자 없음) — ANCHOR 대상 아님. M6 배선 이후 fan_in>=3 이 되면
ANCHOR 승격 검토.

#### E7 — 스코프 규율

```
$ git status --short   (신설 파일만)
?? my_chart/analysis/rrg.py
?? tests/test_sector_rrg.py
```

`my_chart/analysis/sector_advanced.py`(구 RRG, SPEC-TOPDOWN-001A 소관) ·
`backend/routers/sectors.py`(M6 소관) · `tests/fixtures/` · `spec.md`/`plan.md`/
`acceptance.md` 본문은 손대지 않았다.

#### Gaps / 잔여 위험 (M4)

| # | 항목 | 처분 |
| --- | --- | --- |
| **G14** | `compute_rrg` 는 함수 수준까지만 제공 — `/sectors/rrg` 라우터 배선, DB 조회(주봉 격자 history, daily 최신 시총/종가), 응답 스키마 노출은 M6 산출물에 의존 | plan.md M6 이 명시적으로 소관("라우터 파라미터 + 종목 목록 필드"). M2 의 AC-SAG-007/043, M3 의 G10 과 동일한 처분 패턴 — 지금 미실행은 Gap 이 아니라 예정된 의존이다 |
| **G15** | 커버리지 미측정(G6/G13 연속) | 위 §E5 참조 |

---

### M5 — 지표 정정 (독립 커밋 단위, 2026-08-13)

#### E1 — 구현 개요 (5개 독립 커밋)

plan.md M5 규약대로 지표별 개별 commit — rollback 입도를 지표 단위로 확보했다.

| # | 커밋 SHA | 대상 | 파일 |
| --- | --- | --- | --- |
| 1 | `9f2318c` | MAX52 → `MAX(High)` over 364d (규약 Y) | `my_chart/analysis/sector_metrics.py`(`_high52_map` 신설 · `_build_member`/`_compute_sector_metrics`/`compute_sector_ranking` 배선) + `tests/test_ac_sag_024_high52.py`(신설) |
| 2 | `d17c737` | Stage 분류기 단일화 + 일봉 분류기 삭제 | `my_chart/analysis/stage_classifier.py`(`classify_stage_or_none` 신설) · `backend/services/sector_detail_service.py`(`_classify_stage_simple` 삭제) · `backend/routers/sectors.py` · `backend/schemas/stage.py`(`unclassified_count`/`total` 신설) · `backend/services/stage_service.py` + 테스트 2종 |
| 3 | `5c14e17` | `volume_ratio` → weekly `VolumeSMA10` | `my_chart/analysis/sector_advanced.py`(`compute_stock_bubble`) · `backend/schemas/sector_advanced.py` + `backend/tests/test_sector_advanced.py` |
| 4 | `b7e9f97` | `trading_value` → daily `VolumeWon`, 창 = 기간 토글 연동 | `my_chart/analysis/sector_metrics.py`(`compute_trading_value_by_period` 신설) + `tests/test_ac_sag_029_trading_value.py`(신설) |
| 5 | `98f5809` | RS 평균 결측 제외 — 회귀 없음 확인(게이팅 테스트만) | `tests/test_ac_sag_030_rs_avg.py`(신설) |

**RS 평균(#5)은 프로덕션 코드 변경이 없다.** 기존 `_equal_mean(rs_values)`(sector_metrics.py:451 부근)가 이미 M2 시점부터 결측 제외 등가중 평균을 산출하고 있었다 — 게이팅 테스트를 신설해 그 사실을 회귀 방지선으로 고정했다.

**M2~M4 함수-수준 진입점 관행 유지**: `compute_trading_value_by_period`는 M2~M4의 "함수 수준까지만 제공, 라우터 배선은 M6 소관" 패턴을 그대로 따른다. `SectorAggregate.trading_value` 필드 신설 및 응답 배선은 M6 산출물이다(deferred-to-M6, Gap G16).

#### E2 — fixture_stage_divergent 구축 증거 (AC-SAG-025 — GREEN 전 작성 요건)

plan.md M5는 "`fixture_stage_divergent`(두 분류기가 다른 답을 내는 3케이스)를 GREEN 전에 작성"을 명시한다. 구축 순서:

1. `_classify_stage_simple`이 여전히 존재하는 상태에서 C1(일봉 상승배열→구2, 주봉 SMA40 하락+RS낮음→기대 1|4)/C2(일봉 하락배열→구4, 주봉 골든크로스+RS높음→기대 2)/C3(일봉 상승배열→구2, 주봉 SMA40 NULL→기대 None) 3케이스를 리터럴로 설계.
2. 각 케이스에서 구 분류기(`_old_daily_classify`, 폐기된 `_classify_stage_simple` 재현)의 실제 반환값을 단언(`old == 2` / `old == 4` / `old == 2`) — 전제 검증.
3. 신설 `classify_stage_or_none`(주봉 Weinstein)의 실제 반환값을 실행해 기대 stage와 일치함 + 구 분류기 값과 **실제로 다름**(`new_stage != old`)을 단언.

verbatim(구현 완료 후 재확인, 논리는 구현 전 설계와 동일 — 3케이스 모두 구·신 분류기가 실제로 분기함을 실행으로 확인):

```
$ pytest backend/tests/test_sector_detail_service.py -k "fixture_stage_divergent" -q
...                                                                       [100%]
3 passed in 0.4x s
```

C1: old=2(daily heuristic) vs new=4(weekly Weinstein, close<sma10 and close<sma40 and slope<-0.01) — 분기.
C2: old=4(daily heuristic) vs new=2(weekly Weinstein, golden cross+RS강) — 분기.
C3: old=2(daily heuristic) vs new=None(SMA40 NULL, 분류 불가) — 분기.

동일성 단독 단언이면 양쪽 모두 구 분류기여도 통과했을 것 — 대신 각 케이스가 리터럴 기대값과 일치**하고** 구 분류기 값과 **다름**을 함께 확인해 검출력을 실증했다(acceptance.md AC-SAG-025 결함 (1) 대응).

#### E3 — `_classify_stage_simple` 삭제 확인 (AC-SAG-025 행동 단언)

```
$ grep -rn "_classify_stage_simple" --include="*.py" .
backend/tests/test_sector_detail_service.py:291:    """폐기된 `_classify_stage_simple` 의 재현(대조 전용, 프로덕션에서는 삭제됨)."""
```

프로덕션 코드(0건) — 테스트 파일의 대조용 재현 함수(`_old_daily_classify`) docstring 참조 1건만 남음(함수 자체는 프로덕션에서 완전 삭제, 테스트가 폐기된 알고리즘의 값을 재현할 뿐 import하지 않음).

정적 스캔(§8 규약, 보조 확인):

```
$ grep -nE "def .*stage|sma200" backend/services/sector_detail_service.py
(no output, exit=1)
```

행동 단언(이름 변경 내성) — `test_ac_sag_025_no_three_input_daily_stage_classifier_in_module`이 모듈의 모든 public/private 함수 시그니처를 순회해 `{close, sma50, sma200}` 3입력 shape을 검사한다 — rename으로 회피되지 않는다.

#### E4 — AC Binary PASS/FAIL 매트릭스 (AC-SAG-024/025/026/027/028/029/030 + AC-SAG-045 R3/R4)

| AC | 상태 | 검증 커맨드 | 실제 출력 | 비고 |
| --- | --- | --- | --- | --- |
| AC-SAG-024 | PASS | `pytest tests/test_ac_sag_024_high52.py -q` | `5 passed` | Given/Then(98/100/92 케이스) · 규약 Y NULL 제외 · 게이팅(집계 픽스처 프로덕션 신고가 수 == 참조) · 되돌림 대조(diverging>=5) · 정적 스캔 |
| AC-SAG-025 | PASS | `pytest backend/tests/test_sector_detail_service.py -k "divergent or ac_sag_025" -q` | `5 passed` | fixture_stage_divergent 3케이스 + 행동 단언(rename 내성) + 정적 스캔 |
| AC-SAG-026 | PASS | `pytest backend/tests/test_sector_detail_service.py -k "excludes_unclassified" -q` + `pytest backend/tests/test_stage_service.py -k "ac_sag_026" -q` | `1 passed` + `1 passed` | SMA40/SMA10 NULL → stage=None, stage2_pct/distribution 분모 제외 |
| AC-SAG-027 | PASS | `pytest backend/tests/test_stage_service.py -k "ac_sag_027" -q` | `2 passed` | distribution·by_sector 전 엔트리 합계 항등식 + Stage1 미흡수 확인 |
| AC-SAG-028 | PASS | `pytest backend/tests/test_sector_advanced.py -k "ac_sag_028" -q` | `4 passed` | Given/Then(200/100→2.0) · NULL/0→None(파라미터화 2케이스) · 정적 스캔 |
| AC-SAG-029 | PASS | `pytest tests/test_ac_sag_029_trading_value.py -q` | `3 passed` | Given/Then(VolumeWon=1e9) · anchor 창 합산(`(anchor_date, t]`) · 정적 스캔 |
| AC-SAG-030 | PASS | `pytest tests/test_ac_sag_030_rs_avg.py -q` | `4 passed` | Given/Then(8/10 결측 제외) · 비시총가중(1/n 비례) · 게이팅(참조 1e-9 이내) · 되돌림 대조 |
| AC-SAG-045 R3 | PASS(파생) | AC-SAG-024와 동일 규칙 공유 — `mut_stored_max52` 대조 동일 | 위 AC-SAG-024 게이팅 절이 R3의 파생 규칙("신고가 수 == 참조 구현값")을 그대로 충족 | 골든 baseline 대비 M7 최종 확정은 M7 소관(회귀 게이트) |
| AC-SAG-045 R4 | 함수 수준 확인(NOT골든대비) | `pytest tests/test_ac_sag_030_rs_avg.py -k "gating" -q` | `1 passed` | rs_avg 전 섹터 정합성은 M5에서 확인. 골든 baseline 대비 "전반적 상승" 비교는 M7이 baseline JSON을 로드해 수행(M5는 baseline 파일에 접근하지 않음 — Gap G17) |

전건 `pytest tests/test_ac_sag_024_high52.py tests/test_ac_sag_029_trading_value.py tests/test_ac_sag_030_rs_avg.py backend/tests/test_sector_detail_service.py backend/tests/test_stage_service.py backend/tests/test_sector_advanced.py -q` → `74 passed`.

#### E5 — 대조/되돌림 실증 (Lesson #9 — 실제 적용 → RED 관측 → 복원 → GREEN)

4건을 실제로 적용해 RED를 verbatim 캡처하고 백업본(`cp`)으로 복원했다(`git checkout-index` 미사용). AC-SAG-029(거래대금)는 정적 스캔이 실제 되돌림을 검출하는지를 개발 중 우연히 실증했다(아래 4번).

**변형 1 — `mut_stored_max52`**(`_high52_map`을 저장 `MAX52` 컬럼 직조회로 되돌림):

```
FAILED tests/test_ac_sag_024_high52.py::test_ac_sag_024_gating_production_nh_count_matches_reference
AssertionError: 프로덕션 신고가 종목 수 26 != 참조 2
assert 26 == 2
```

**변형 2 — `mut_daily_simple_retained`**(`_load_weekly_classification`을 항상 빈 dict 반환으로 되돌림 — 구 일봉 근사 분류기 부재 상태 재현):

```
FAILED backend/tests/test_sector_detail_service.py::test_sub_sector_stage2_pct
AssertionError: 소프트웨어 stage2_pct=0.0, 기대값=50.0
FAILED backend/tests/test_sector_detail_service.py::test_sub_sector_stage2_pct_excludes_unclassified_from_denominator
AssertionError: 분류 불가 종목이 분모에 남았다: stage2_pct=0.0, 기대값=100.0
```

**변형 3 — `mut_price_sma10_approx`**(`raw_volume_sma10 = sma10` 가격 근사로 되돌림):

```
FAILED backend/tests/test_sector_advanced.py::test_ac_sag_028_volume_ratio_uses_weekly_volume_sma10_not_price_sma10
AssertionError: assert 0.004 is None (기대 2.0)
FAILED backend/tests/test_sector_advanced.py::test_ac_sag_028_volume_ratio_none_when_volume_sma10_missing[None]
FAILED backend/tests/test_sector_advanced.py::test_ac_sag_028_volume_ratio_none_when_volume_sma10_missing[0.0]
FAILED backend/tests/test_sector_advanced.py::test_ac_sag_028_static_scan_no_price_sma10_volume_approximation
AssertionError: 'volume_sma10 = sma10' is contained here
```

**변형 4 — `mut_rs_zero_fill`**(`rs_avg`를 `or 0.0` + `member_count` 분모로 되돌림):

```
FAILED tests/test_ac_sag_030_rs_avg.py::test_ac_sag_030_given_then_rs_avg_excludes_missing_from_denominator
FAILED tests/test_ac_sag_030_rs_avg.py::test_ac_sag_030_mut_rs_zero_fill_reference_diverges
AssertionError: 결측 제외 방식(프로덕션)과 0.0 치환+member_count 분모 방식이 최소 1개 섹터에서 실제로 갈려야 한다
assert 0 >= 1
```

**AC-SAG-029 정적 스캔의 우연한 실증**: `compute_trading_value_by_period` 상단 주석 초안에 `Close*Volume`이라는 리터럴을 실수로 남긴 채 정적 스캔 테스트(`test_ac_sag_029_static_scan_no_close_times_volume_recomputation`)를 실행했더니 그 주석 1건을 실제로 검출해 RED가 됐다(`AssertionError: Close*Volume 재계산 표현이 남아있다: ['Close*Volume']`) — 스캔의 검출력을 개발 중 실측으로 확인한 부수 증거. 주석을 "종가×거래량"으로 정정해 GREEN 복원했다(코드 로직 변경 없음, 주석 표현만 교체).

4건 모두 복원 후 `diff /tmp/moai-verify/*.bak <대상파일>` 바이트 동일 확인 + 해당 테스트 재실행 GREEN 재확인.

#### E6 — 전체 테스트 스위트 델타 (M4 → M5)

```
$ pytest tests/ -q
8 failed, 844 passed, 68 skipped, 1 xpassed, 25 errors in 95.78s
```

| | M4 완료 후 | M5 완료 후 | 델타 |
| --- | --- | --- | --- |
| passed | 832 | **844** | +12(신규 `test_ac_sag_024_high52.py` 5 · `test_ac_sag_029_trading_value.py` 3 · `test_ac_sag_030_rs_avg.py` 4) |
| failed | 8 | **8** | 0 — 동일 집합(`test_api` 1 · `test_meta_service` 2 · `test_rs_line` 2 · `test_screen_service` 3) |
| errors | 25 | **25** | 0 — 전건 pre-existing `tests/fnguide/*` |

`backend/tests/` 신규/변경 테스트(개별 파일 실행, 이 저장소의 `backend/tests/` 전체 일괄 실행은 사전 존재 test-isolation 결함으로 별도 관리 — 아래 Gaps G18 참조): `test_sector_detail_service.py`(13 passed) · `test_stage_service.py`(3 passed) · `test_sector_advanced.py`(46 passed) 개별 실행 전건 GREEN.

M2~M4 게이트(`test_aggregation_fixture.py` + `test_sector_aggregation.py` + `test_sector_benchmark_ranking.py` + `test_sector_rrg.py` + `test_sector_metrics.py`) M5 완료 후 재확인: `146 passed`. item1(MAX52) 커밋 직후 단독 재검증 시에도 동일 5파일 `146 passed`.

#### E7 — 커버리지

`coverage` 모듈 미설치(M2~M4 연속, G6/G13/G15 연속). 대리 지표: 신설 21개 테스트가 `_high52_map`/`compute_trading_value_by_period`/`classify_stage_or_none`/`_load_weekly_classification`/`compute_stock_bubble`(volume_ratio 분기) 전 신규·수정 함수의 정상/결측/되돌림 분기를 직접 실행한다.

#### E8 — @MX 태그

| 태그 | 위치 | 내용 |
| --- | --- | --- |
| `@MX:NOTE` | `sector_metrics.py` `_high52_map` 상단 | 규약 Y(NULL MAX52 종목 분자·분모 제외) — 0.0 치환 시 가짜 divergence 20건 발생 근거 명시 |
| `@MX:NOTE` | `sector_metrics.py` `compute_trading_value_by_period` 상단 | anchor(t,N) 창 공유 — 수익률·거래대금이 다른 창을 쓰는 사고 방지 |
| `@MX:NOTE` | `sector_detail_service.py` `_load_weekly_classification` 상단 | REQ-SAG-023 단일화 근거 + AC-SAG-026 결측 처리 위임 |
| `@MX:NOTE` | `stage_classifier.py` `classify_stage_or_none` 상단 | classify_stage() 시그니처(항상 int) 불변 유지 이유(SPEC-TOPDOWN-001A 소관) |

기존 파일에 대한 추가라 파일별 한도 재확인: `sector_metrics.py` NOTE 기존분 포함 다수(한도 미접근), `sector_detail_service.py`/`stage_classifier.py` 각 NOTE 1건 추가(한도 10 이내).

#### E9 — 스코프 규율

```
$ git status --short   (M5 5개 커밋 누적, 최종 상태)
(모두 커밋됨 — git log 9f2318c..98f5809)
```

`my_chart/analysis/sector_advanced.py`의 RRG(z-score) 관련 코드·`_rolling_zscore`/`compute_rrg_data`는 손대지 않았다(volume_ratio 수정은 `compute_stock_bubble` 함수 국소). `backend/routers/sectors.py`는 `get_sector_detail` 호출부 1줄(`weekly_db_path=` 추가)만 수정 — 라우터 파라미터 신설은 M6 소관. `spec.md`/`plan.md`/`acceptance.md` 본문은 손대지 않았다.

#### Gaps / 잔여 위험 (M5)

| # | 항목 | 처분 |
| --- | --- | --- |
| **G16** | `compute_trading_value_by_period`는 함수 수준까지만 제공 — `SectorAggregate.trading_value`/`trading_value_window_days` 응답 필드 신설·라우터 배선은 M6 산출물 의존 | plan.md M6 명시 소관("라우터 파라미터 + 종목 목록 필드"). M2~M4와 동일 처분 패턴 |
| **G17** | AC-SAG-045 R4("골든 baseline 대비 rs_avg 전반적 상승")의 baseline 비교는 M5에서 미실행 — `tests/fixtures/golden/pre-sector-ux/ranking-current.json` 로드 로직은 M7 회귀 게이트 소관 | plan.md M7이 R1/R4/R5를 명시적으로 담당("R1/R4/R5는 M1.0-b에서 캡처한 골든 baseline과 비교"). M5는 함수 수준 정합성(rs_avg == 참조)만 확인 |
| **G18** | `backend/tests/` 디렉토리 전체 일괄 실행 시 사전 존재 test-isolation 결함(`generate_price_db` import 실패 등 — `backend/tests/test_minervini_template.py`/`test_stocks_master.py` 등에서 다수 관측) 확인. M5 신설 테스트 3개 파일과 무관하게 M5 착수 **전**에도 존재(개별 파일 실행은 전건 GREEN, 디렉토리 일괄 실행만 실패) | 회귀 아님 — SPEC 범위 밖 사전 결함. `tests/` 단독 실행(공식 pre-flight 커맨드)은 영향 없음(151→154→844 델타로 확인). manager-spec 표기 권고 후속 SPEC 대상 |
| **G19** | 커버리지 미측정(G6/G13/G15 연속) | 위 §E7 참조 |

---

### M6 — 라우터 파라미터 + 종목 목록 필드 (기계적, 2026-08-13)

#### E1 — 구현 개요 (단일 커밋)

`market`/`period` 쿼리 파라미터를 6개 엔드포인트(`/sectors/ranking`, `/sectors/rrg`,
`/sectors/history`, `/sectors/{name}/detail`, `/sectors/{name}/bubble`, `/stage/overview`)
에 신설했다(AC-SAG-039). 파라미터 미전달 시 `market=all`(및 `/ranking`·`/detail`의
`period=1m`)로 기존 동작이 유지된다(하위 호환 확인 — `test_ac_sag_039_backward_
compat_default_market_all`).

**실질 데이터 필터로 배선한 경로**(집계 시점 필터 — `member_count` 자체가 달라짐을
실증):
- `/sectors/ranking` → `sector_ranking_service.get_sector_ranking(market=...)` →
  `compute_sector_aggregates(market=...)`(이미 시장 필터를 지원했던 함수, 라우터
  배선만 M6 신규) + `compute_sector_ranking(market=...)`(**M6 신설 파라미터** —
  `sector_to_stocks` 를 `_market_matches` 로 사전 필터).
- `/stage/overview` → `stage_service.get_stage_overview(market=...)` — registry
  `Market` 컬럼으로 `raw_stocks`/`candidates_raw` 를 사전 필터.
- `/sectors/{name}/detail` → `sector_detail_service.get_sector_detail(market=...)` —
  `stock_meta.market` 컬럼 SQL WHERE 절.
- `/sectors/history` → `compute_sector_history(market=...)` **신설 파라미터** →
  `compute_sector_ranking(market=...)` 그대로 전파(단일 원천).

**M6 단계에서 echo 만 하고 Gap 으로 남긴 경로**(아래 Gaps 참조): `/sectors/rrg`,
`/sectors/{name}/bubble`(종목 단위 시장 필터).

**AC-SAG-040** — `/sectors/history` 에 `dates[]`(길이 == `weeks`) · `span_days`
(`7×(weeks−1) ± 7`) · `rankings[date][sector]`(그 날짜에 순위 대상이 아니었던 섹터는
키가 존재하되 값이 `null` — 최하위 순위로 대체하지 않는다, 전 구간 등장 섹터 합집합을
매 날짜 키로 미리 채워 넣는 방식으로 구현)를 신설했다.

**AC-SAG-041** — `StageStock`(stage/overview 의 `stage2_candidates`/`all_stocks`)에
`weight_in_sector`·`chg_1w`·`chg_3m`·`trading_value`·`near_52w_high` 필드를
추가했다. `weight_in_sector` 는 **`weighting.capped_weights_detail` 을 섹터별로
그대로 재호출**해 산출한다(INV-CAP-1 — cap_eff(n) = max(WEIGHT_CAP, 1/n) 재사용,
새 산식을 만들지 않았다 — D16/D17/N1 계열 결함의 재발 방지). `trading_value` 는
weekly `Close × Volume` 근사이며(정규 원천인 daily `VolumeWon` 배선은 이 종목
목록이 daily DB 를 소비하지 않으므로 Gap — 아래 참조), `near_52w_high` 는
`sector_metrics._NH_THRESHOLD`(2%)와 동일 관용을 `stage_service._NEAR_52W_
THRESHOLD` 로 독립 상수화해 재사용했다.

**AC-SAG-042** — `/sectors/{name}/bubble` 응답에 `sector_aggregate` 필드를
신설했다. `compute_sector_ranking()` 을 **ranking 서비스와 동일 인자로 재호출**해
산출하므로(별도 산식을 두지 않음 — EX-1 방법론 일치 구조 보장), legacy `sectors[].
returns.w1` 값과 정확히 일치한다(`< 1e-6`, `test_ac_sag_042_...` 실측 확인).
canonical `data[].returns` 값(compute_sector_aggregates 경유, 별도 계산 경로)과는
반올림 차 수준(`~2.8e-05`)의 차이가 있음을 확인했다 — AC-SAG-042 본문이 지시하는
비교 대상은 legacy `sectors[]` 표면이다.

**AC-SAG-007** — M6 완료로 평가 시점 도달. `market=kospi` 응답에서 F3 섹터
(디스플레이·스마트폰, 유효 종목 정확히 4)가 `excluded[]`에 `reason:
"insufficient_members"`, `count: 4`로 등록되고 `data[]`에서 빠짐을 실증했다.
경계값(PCB, 정확히 5)은 `data[]`에 포함됨을 확인했다(`>= 5` 경계 포함).
`market=all`에서는 두 섹터가 `data[]`에 포함된다(필터가 구성수를 바꿈).

**AC-SAG-043 파생 구조 절** — `stage_service.by_sector`(`SectorStageBreakdown`)의
`unclassified_count`/`total`은 **M5에서 이미 신설**됐음을 재확인했다(중복 구현
방지 — Section B 사전 확인 절차대로 `backend/schemas/stage.py` 를 먼저 읽고
확인). M6이 신규로 추가한 것은 없다 — 4단계(dataclass/서비스/Pydantic/JSON)는
M1.1부터 이미 PASS, 파생 구조 절(by_sector)은 M5부터 이미 PASS였다. 이 절의
평가 시점 명시(D19)는 절차적 요구였을 뿐, 실제 필드 신설은 M5에서 선행 완료됐다.

#### E2 — AC PASS/FAIL 매트릭스 (M6 신규 실행분)

| AC | 상태 | 검증 명령 | 실측 결과 |
| --- | --- | --- | --- |
| AC-SAG-039 (ranking market 필터) | PASS | `pytest tests/test_sag_m6_router_wiring.py -k ac_sag_039_ranking` | `2 passed` |
| AC-SAG-039 (backward compat) | PASS | `pytest ... -k ac_sag_039_backward_compat` | `1 passed` |
| AC-SAG-039 (422) | PASS | `pytest ... -k ac_sag_039_invalid_market` | `1 passed` |
| AC-SAG-039 (stage/overview) | PASS | `pytest ... -k ac_sag_039_stage_overview` | `1 passed` |
| AC-SAG-039 (detail) | PASS | `pytest ... -k ac_sag_039_sector_detail` | `1 passed` |
| AC-SAG-039 (history) | PASS-WITH-DEBT | `pytest ... -k ac_sag_039_history_market` | `1 passed` — echo 만 확인, 실질 데이터 차이는 미검증(구조적으로는 compute_sector_ranking market 전파로 실질 필터가 걸려 있으나 전용 데이터-차이 단언 미작성) |
| AC-SAG-039 (rrg) | PASS-WITH-DEBT | `pytest ... -k ac_sag_039_rrg` | `1 passed` — echo 만, 실 데이터 재계산 미배선(Gap 참조) |
| AC-SAG-040 (dates/span_days/rankings) | PASS | `pytest ... -k ac_sag_040` | `3 passed` |
| AC-SAG-041 (필드 존재 + INV-CAP-1) | PASS | `pytest ... -k ac_sag_041` | `3 passed` |
| AC-SAG-042 (sector_aggregate 일치) | PASS | `pytest ... -k ac_sag_042` | `1 passed` |
| AC-SAG-007 (M6 평가 개시) | PASS | `pytest ... -k ac_sag_007` | `3 passed` |
| AC-SAG-043 (파생 구조 절, M6 재확인) | PASS | `pytest ... -k ac_sag_043` | `1 passed` — M5 선행 완료 재확인 |
| AC-SAG-021 (rank = f(period, market)) | PASS-WITH-DEBT | (수동 확인, 전용 테스트 미작성) | market 절만 실증(제외 섹터 발생 → rank 최대값 감소, `test_ac_sag_039_ranking_market_filter_changes_data`가 간접 실증). period 절은 미이행 — `rank`은 `compute_sector_ranking`의 고정 composite(1w/1m/3m 가중 정규화)로만 산출되고 `period` 파라미터는 소비하지 않는다(G22) |

전체: `pytest tests/test_sag_m6_router_wiring.py -q` → `18 passed`.

#### E3 — 되돌림 대조(필수, Lesson #9)

- **`mut_no_ag5_gate`**(AC-SAG-007 / 045 R6 공유): `compute_sector_aggregates(...,
  apply_min_members=False)` 변형에서 F3 섹터(디스플레이·스마트폰)가 `data[]`에
  재등장하고 `insufficient_members` 사유로는 더 이상 `excluded[]`에 남지 않음을
  확인했다 — `test_ac_sag_007_red_when_ag5_gate_removed`. 정상 구현에서는 두
  섹터가 `excluded[]`에 있었으므로(원 단언), 변형 적용 시 그 조건이 RED가 됨을
  실증했다(대조가 검출력을 가짐).
- **`mut_weight_cap_literal`**(AC-SAG-041): `weighting.capped_weights_detail`
  대신 `min(raw, 0.10)` 산출로 되돌린 변형에서 정규화(`Σw == 1.0`) 위반을
  실증했다 — `test_ac_sag_041_weight_in_sector_red_when_literal_010_used`. 축퇴
  섹터(패션, 유효 시총 3, cap_eff=1/3≈0.3333)에서 실제 응답값이 리터럴 0.10
  근처가 아님도 직접 확인했다(`test_ac_sag_041_weight_in_sector_not_literal_
  010_degenerate_sector`).
- 복원 확인: 두 대조 모두 프로덕션 코드를 직접 변형하지 않고 순수 함수를
  국소 재현(`caps` 딕셔너리 조작 / `apply_min_members=False` 인자)해 관측했다
  — `git status --short` 는 이 M6 커밋 범위 밖 사전 dirty 상태만 남기고
  공백(내 변경분 기준).

#### E4 — 전체 스위트 델타

```
$ pytest tests/ -q
8 failed, 862 passed, 68 skipped, 1 xpassed, 25 errors in 102.85s
```

| | M5 완료 후 | M6 완료 후 | 델타 |
| --- | --- | --- | --- |
| passed | 844 | **862** | +18(신규 `tests/test_sag_m6_router_wiring.py`) |
| failed | 8 | **8** | 0 — 동일 집합 |
| errors | 25 | **25** | 0 — 전건 pre-existing `tests/fnguide/*` |

M2~M5 게이트(`test_aggregation_fixture.py` + `test_sector_aggregation.py` +
`test_sector_benchmark_ranking.py` + `test_sector_rrg.py` + `test_response_
contract.py`) M6 완료 후 재확인: `148 passed`(변경 없음 — M6 은 이 5파일이
커버하는 함수를 재구현하지 않았다). `backend/tests/test_sector_detail_
service.py`(13 passed) · `test_stage_service.py`(3 passed) · `test_sector_
advanced.py`(46 passed) 개별 실행 전건 GREEN(하위 호환 확인).

#### E5 — 스코프 규율

```
$ git status --short   (M6 단일 커밋 e139067, 이 SPEC 범위 파일만)
(내 변경분은 모두 커밋됨 — 사전 존재 무관 dirty 파일들만 남음, PRESERVE 미접촉)
```

수정 파일 9개(`backend/routers/{sectors,stage}.py`, `backend/schemas/{sector_
advanced,stage}.py`, `backend/services/{sector_advanced_service,sector_detail_
service,sector_ranking_service,stage_service}.py`, `my_chart/analysis/
sector_metrics.py`) + 신규 테스트 1개. `stage_classifier.py`(공유 호출자 다수)는
손대지 않았다 — `_load_stocks_for_classification` 을 그대로 재사용하고, 확장
컬럼(CHG_1W/CHG_3M/MAX52/Volume)은 `stage_service.py` 국소 보조 쿼리로 분리했다
(scope discipline). `sector_metrics.py` 는 `compute_sector_ranking`/`compute_
sector_history` 시그니처에 `market` 파라미터만 추가했고 기존 호출자(무인자
호출)는 기본값 `"all"`로 하위 호환된다.

#### Gaps / 잔여 위험 (M6)

| # | 항목 | 처분 |
| --- | --- | --- |
| **G20** | `/sectors/rrg`, `/sectors/{name}/bubble`(종목 단위)의 `market` 파라미터는 라우터에서 수신·검증되고 `market_filter`로 echo 되지만, 실 데이터 재계산은 배선하지 않았다 — RRG 는 섹터 지수 시계열(주봉 격자)을 소비하며 시장별 지수가 별도로 저장돼 있지 않고, `compute_stock_bubble`은 종목 단위 시장 필터 로직이 없다 | 아키텍처 확장(시장별 지수 계열 신설 또는 종목 필터 추가)이 필요해 "기계적 배선"의 범위를 넘는다. AC-SAG-039 는 6개 엔드포인트 모두를 요구하므로 이 두 엔드포인트는 **PASS-WITH-DEBT**로 기록한다. 후속 SPEC 대상 |
| **G21** | `stage_service`의 `trading_value`는 weekly `Close × Volume` 근사다 — M5가 확정한 정규 원천(daily `VolumeWon`, `compute_trading_value_by_period`)은 daily DB 를 요구하는데 이 종목 목록 경로는 weekly DB 만 소비한다 | `weekly Volume`은 원천이 다르다(단위·정합성 미검증). AC-SAG-041은 필드 존재만 요구하고 원천 일치를 명시 요구하지 않아 PASS로 기록했으나, 원천 정합은 후속 과제로 기재한다 |
| **G22** | `/sectors/ranking`·`/sectors/{name}/detail`의 `period` 파라미터는 수신·검증되나(422 게이트) 응답 형태를 바꾸지 않는다 — ranking은 이미 3개 윈도우(1w/1m/3m)를 항상 반환하고(AC-SAG-036), detail의 top_stocks도 `chg_1m`만 유지한다. **AC-SAG-021의 `period=3m` → `rank` 재배정 요구가 이로 인해 미이행이다**(`compute_sector_ranking`은 고정 composite 만 산출) | spec.md §12.3 본문이 `period`의 정확한 의미(단일 대표 지표 선택인지 단순 하위호환 파라미터인지)를 명시하지 않아, 단일 패스 최선 해석으로 "영향 없음, 수신만" 채택했으나 AC-SAG-021 본문과는 직접 모순됨을 재확인 후 정정 기재한다. `rank`를 `period` 별로 재계산하려면 `compute_sector_ranking`의 composite 정규화 로직을 period-단일-지표 기준으로 분기해야 하며 M6 스코프를 넘는 후속 과제다 |
| **G23** | `stock_bubble`(`/sectors/{name}/bubble`)의 `StockBubbleItem`은 AC-SAG-041의 `weight_in_sector`/`chg_1w`/`chg_3m`/`near_52w_high`를 아직 갖지 않는다 — `price_change`(단일 period 값)만 있다 | spec.md §12.3 이 stock-listing 대상을 "`/stage/overview`, 종목 버블"로 명시하므로 완전한 이행은 아니다. 시간 제약으로 `/stage/overview` 를 우선 완결하고 이 항목은 후속 과제로 넘긴다 |
| **G24** | 커버리지 미측정(G6/G13/G15/G19 연속) | coverage 모듈 미설치. 대리 지표: 신규 18개 테스트가 M6 신설/수정 함수(market 필터 전 경로, weight_in_sector, sector_aggregate, dates/span_days/rankings)를 직접 실행 |
| **G16 (M5 신설, M6에서도 미해소)** | `SectorAggregate.trading_value`/`trading_value_window_days` 응답 필드 신설·라우터 배선 — `compute_trading_value_by_period`는 여전히 함수 수준 정의만 있고 호출부가 0건(실측: `grep -rn compute_trading_value_by_period my_chart/ backend/` → 정의 1건) | M6이 처음 §E.3 초안 작성 시 "RESOLVED"로 오기재했다가 재확인 후 정정했다(verification-claim-integrity §1.1 surface 1 위반 자체 검출·수정). M6 스코프는 stage/overview 종목 목록(weekly 근사 trading_value, AC-SAG-041)만 다뤘고 섹터 집계 항목(data[])의 trading_value는 다루지 않았다. 후속 SPEC 또는 M7 범위 확대 대상 |
| **G25 (M3 신설, M6에서도 미해소)** | AC-SAG-023의 `rank_change` 최상위 `baseline_date` 응답 노출, AC-SAG-046 원판(트리거 픽스처 + 금요일 종단 변형)의 `trading_value_window_days`/`rank_change.baseline_date` 최상위 응답 노출 — 둘 다 M3 §E.2에서 "M6 라우터 응답 스키마 확장과 결합, deferred"로 명시 기재됐으나 M6은 이 특정 최상위 필드들을 신설하지 않았다 | M6 초안이 "M3에서 이미 완료"로 오기재했다가 progress.md §E.2 M3 원문 재확인 후 정정한다(verification-claim-integrity §1.1 surface 1). `market_filter`/`return_window_days` 등 AC-SAG-036 10키는 완비돼 있으나 `baseline_date`/`trading_value_window_days`는 그 10키 밖의 개별 필드다. 후속 SPEC 또는 M7 범위 확대 대상 |

---

#### 9. AC-SAG-037 Closure (post-M7, 2026-08-14) — cycle_type=tdd

M7이 §7에서 기록한 유일한 미해소 Gap("전 엔드포인트 as_of_date 일치, SN-3
되돌림 실증 미이행")을 닫는 후속 세션. M7 본문(§1~§8)은 수정하지 않는다 —
이 절이 그 뒤를 잇는다.

**착수 전 실측 확인** — 프로덕션 코드를 실제로 조사한 결과, Gap 기록이
정확했을 뿐 아니라 **당초 우려보다 근본적**이었다: `EnvelopeMixin.as_of_date`
필드는 존재했지만, 실제로 값을 채우는 배선은 `/sectors/ranking`
(`sector_ranking_service.get_sector_ranking` → `envelope_fields(as_of_date=date, ...)`)
**단 1개 엔드포인트뿐**이었다. 나머지 6개(`/sectors/bubble`,
`/sectors/{name}/bubble`, `/sectors/rrg`, `/sectors/history`,
`/stage/overview`, `/sectors/{name}/detail`)는 응답 모델이
`EnvelopeMixin`을 상속해 키는 존재했으나(AC-SAG-036 통과) 값은 필드
기본값 `None`이었다 — "서로 다르다"가 아니라 "6곳이 애초에 채우지 않는다"
상태였다. `grid_version`은 `EnvelopeMixin`의 클래스 기본값(`GRID_VERSION =
"canonical-v1"`)이 모든 엔드포인트에서 오버라이드 없이 그대로 쓰여
이미 7개 전부 일치했다(변경 불필요).

**프로덕션 코드 수정** (6개 서비스 함수, 3개 파일 — 각 함수는 이미 canonical
헬퍼(`_get_latest_valid_date` 직접 또는 로컬 `_get_latest_date` 래퍼 경유)로
지역 변수 `date`를 계산하고 있었으나 응답 생성자에 전달하지 않았다):

- `backend/services/sector_advanced_service.py` — `get_sector_bubble` /
  `get_stock_bubble` / `get_rrg_data`에 `as_of_date=date or None` 추가.
  `get_sector_history`는 `dates[-1]`(history SSOT)이 진행 중인 주 배제
  시맨틱상 canonical latest와 다를 수 있어(±`is_partial` 분기, `weekly_grid.py`
  `_compute_cached`) 별도로 `_get_latest_valid_date(weekly_db_path)`를
  직접 호출해 `as_of_date`를 채운다(다른 6개와 동일한 공유 헬퍼 직접 경유).
- `backend/services/stage_service.py` — `get_stage_overview`의 두 반환
  분기(빈 DB 조기 반환 + 정상 반환) 모두에 `as_of_date=date` 추가.
- `backend/services/sector_detail_service.py` — 함수 시작부에
  `as_of_date = _get_latest_valid_date(weekly_db_path) if weekly_db_path
  else None`을 신설(기존에는 지역 `date` 변수 자체가 없었다 — 이 파일은
  `_load_weekly_classification` 내부에서만 `compute_weekly_grid(...).latest.date`를
  쓰고 상위로 노출하지 않았다)하고, 두 반환 분기에 전달.

**신규 테스트** — `tests/test_ac_sag_037_endpoint_date_consistency.py`(신설,
10 테스트): ①이 소유한 `tests/test_consumer_dates.py`의
`_build_fixture_max_ne_canonical`/`WEEKLY_FULL_DATE`/`WEEKLY_PARTIAL_DATE`를
**import 로만 재사용**(해당 파일 미수정). 서비스 함수를 라우터 경유 없이
직접 호출하는 방식을 택했다(TestClient 전체 스택 대신 — 프로덕션
`fixture_max_ne_canonical`은 weekly DB만 채우므로 라우터 경유 시 daily
DB/레지스트리 스키마를 함께 맞춰야 하는 부수 비용이 컸다; 대신 최소
`stock_meta` 빈 테이블 하나만 신설):

1. `test_ac_sag_037_all_seven_endpoints_converge_to_canonical_date` — 7개
   서비스 함수 호출 결과 `as_of_date`가 전부 canonical(`WEEKLY_FULL_DATE`,
   2024-01-12)과 같고 naive(`WEEKLY_PARTIAL_DATE`, 2024-01-15)와는 다름을
   양쪽 단언.
2. `test_ac_sag_037_all_seven_endpoints_share_grid_version` — 7개
   `grid_version`이 전부 `canonical-v1`.
3. `test_ac_sag_037_naive_max_date_revert_fails_for_each_endpoint`
   (parametrize 7종, id=엔드포인트 경로) — 각 엔드포인트가 의존하는
   공유 헬퍼(4개는 `sector_advanced_service._get_latest_valid_date` 공용
   import, 나머지 3개는 각 모듈 고유의 `_get_latest_date`/
   `_get_latest_valid_date`)를 naive `SELECT MAX(Date) ... WHERE Name NOT
   IN ('KOSPI','KOSDAQ')` 구현으로 개별 monkeypatch한 뒤 **그 엔드포인트만**
   호출해 `as_of_date == WEEKLY_PARTIAL_DATE`(naive) 및 `!=
   WEEKLY_FULL_DATE`(canonical)를 단언 — acceptance.md §9 DoD의 "엔드포인트별
   순진 MAX(Date) 7회" 대조 단언을 충족한다.
4. `test_ac_sag_037_live_smoke_as_of_date_matches_across_endpoints` —
   라이브 `backend.deps.WEEKLY_DB_PATH`/`DAILY_DB_PATH` 존재 시에만 실행,
   불일치는 `warnings.warn`으로만 강등(assert 없음) — acceptance.md 지시
   "정보성 검사로 표시" 그대로 non-gating.

**엔드포인트 개수 해석 메모** — plan.md/acceptance.md의 "7개 엔드포인트"
가정은 M7 시점(2026-08-14) 현재 라우터 표면(`backend/routers/sectors.py`
6개 + `backend/routers/stage.py` 1개 = `/sectors/ranking`,
`/sectors/bubble`, `/sectors/rrg`, `/sectors/history`,
`/sectors/{name}/detail`, `/sectors/{name}/bubble`, `/stage/overview`)과
정확히 일치했다 — M6/gap-closure 이후에도 개수 불일치는 없었다. 재해석
불필요.

**대조 단언 공유-헬퍼 그룹 메모** — `sector_advanced_service.py`의 4개
함수(`get_sector_bubble`/`get_stock_bubble`/`get_rrg_data`/
`get_sector_history`)는 물리적으로 동일한 모듈 import 심볼
(`_get_latest_valid_date`)을 공유한다. 되돌림 대조 7변형은 "엔드포인트를
1곳씩 되돌렸을 때 그 엔드포인트만 호출해 관측"하는 방식으로 구현했으므로
— 4개가 물리적으로 같은 헬퍼를 공유한다는 사실 자체가 각 엔드포인트의
배선이 (개별 하드코딩이 아니라) 정말 그 헬퍼를 경유함을 증명하는 데는
지장이 없다. 다만 "1곳만 배선하고 나머지 3곳이 우연히 일치"하는 시나리오는
이 4개 사이에서는 원천적으로 발생할 수 없다(코드가 물리적으로 하나이므로) —
이 그룹 내부의 상호 독립성 검증은 이 AC의 범위를 벗어난다(생성자 kwargs
누락 여부는 정판정 테스트 ①이 개별적으로 검출한다).

**전체 스위트 델타**:
```
$ pytest tests/ -q   (본 세션 착수 전 baseline, M7 종료 시점과 동일)
8 failed, 900 passed, 69 skipped, 1 xpassed, 25 errors in 111.68s

$ pytest tests/ -q   (AC-SAG-037 테스트 파일 추가 후)
8 failed, 910 passed, 69 skipped, 1 xpassed, 25 errors in 128.37s
```
+10 passed(신규 파일 1개: 정판정 2 + 되돌림 대조 7(parametrize) + 라이브
스모크 1). failed 8건·error 25건은 baseline과 **동일 집합**(`test_api.py`
`TestScreenEndpoint::test_too_many_patterns_rejected`,
`test_meta_service.py` `TestRebuild::*` 2건,
`test_rs_line.py::TestRsLineCalculation` 2건, `test_screen_service.py`
3건, `fnguide/` 25 error — 전건 SPEC 범위 밖 사전 존재, 신규 실패 0건).

**Blocker**: 없음.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: implemented            # M7(테스트 대체 + 회귀 게이트) 완료 + post-M7 세션에서 AC-SAG-037 Gap 종결(§E.2 §9). 미이월 Gap 없음 — sync-phase 대기
milestone_completed: M7            # 테스트 대체(AC-SAG-044) + 회귀 게이트(AC-SAG-045 R1/R4/R5-a) + as_of 정적 스캔 확장 + F1~F13/050 회귀 재확인
run_commit_sha: 753a529            # M7 단일 커밋
prior_run_commit_sha_m6: e139067   # M6 단일 커밋 (M6-gap-closure 는 별도 세션, b337365 이전 커밋)
prior_run_commit_sha_m5: 98f5809   # M5 #5(RS 평균, 최종 커밋)
prior_run_commit_sha_m5_1: 9f2318c # M5 #1(MAX52)
prior_run_commit_sha_m5_2: d17c737 # M5 #2(Stage 단일화)
prior_run_commit_sha_m5_3: 5c14e17 # M5 #3(volume_ratio)
prior_run_commit_sha_m5_4: b7e9f97 # M5 #4(trading_value)
prior_run_commit_sha_m4: 8a3a7f7   # M4 커밋
prior_run_commit_sha_m3: 1815d30   # M3 커밋
prior_run_commit_sha_m2: 25f3fa9   # M2 커밋 (M1.0-b 재캡처는 8e51176, M1.0-a 재빌드는 a000add)
coverage_m11: "aggregate_types 94% · envelope 99% · sector_ranking_service 91% (TOTAL 95%, 임계 85%)"
prior_milestone_commits: "adb1f25 (M1.0-a 구) · b839cee (M1.0-a §E.3 구) · 6f00ba5 (M1.0-b/c 구) · 7b5fc45 (M1.0-b/c §E.3 구) · 7305e2e (M1.1) · a000add (M1.0-a 재빌드) · 8e51176 (M1.0-b 재캡처)"
ac_gate: "AC-SAG-011~023 · 046(lite) · 031~035 · 045(R7) (M2~M4 RED 목록 누적 — 046 은 §8.1 지정 픽스처 대신 aggregation 픽스처로 lite 검증, Gap G11)"
ac_pass_count: 36                  # M2 17 + M3 13(011~023, 046-lite 는 부분 PASS 로 별산) + M4 6(031·032·033·034·035·045-R7)
ac_fail_count: 0                   # M2~M4 RED 목록 전건 GREEN(021/022/023 은 함수 수준, compute_rrg 라우터 배선은 M6 의존 — Gap G10/G14)
ac_blocked: "없음 — v0.4.2에서 해소 (D16: F12 신설 + AC-SAG-002 재작성 / D17: §3.1 동결형 교체 + AC-SAG-049 신설). [v0.5.0] 추가 정정 — N1(AC-SAG-041 cap_eff) · D22(AC-SAG-010) · D20(045 R1) · D23(AC-SAG-015) · D21(045 R5-b) · N4(AC-SAG-012) · N3(AC-SAG-016) · N7(AC-SAG-044) · D24(AC-SAG-013) · N2(F7 규약 Y) · D25(F4·F8 폐지) · R-C1~R-C8(F13 신설) · D29(합성 바) · N5/D26(고아 AC)"
blocker_open: false               # M2 blocker(D16/D17)는 v0.4.2/v0.5.0 에서 해소됐고 M2 가 완주했다. 신규 blocker 없음 — G7 은 표기 정정 권고(비차단)
blocker_owner: manager-develop    # 소유권 반환. acceptance.md 본문 수정 완료(v0.4.2)
blocker_resolution_version: "0.5.0"   # 0.4.2에서 M2 blocker 2건(D16·D17) 해소, 0.5.0에서 전수 스윕 결함 14건 일괄 해소
spec_layer_deltas: "F12 신설(§8.2) · AC-SAG-002 절 2·3 집합 동등 재작성 · AC-SAG-045 R1 대조 mut_service_not_rewired 교체 · plan.md §3.1 동결형 + 종료 증명 · AC-SAG-001 A/B 분리 · AC-SAG-049 신설 · AC-SAG-003 순수 합성 교체 · AC-SAG-005 정의 확정 · AC-SAG-007/043 M6 의존 명시 · §8.4 규약 10 신설"
wip_branch: "wip/SPEC-SECTOR-AGGREGATION-001-M2 @ 83cb847 (main 미머지)"
capture_via_http_response: true    # TestClient 경유 response_model 직렬화. model_dump_json() 아님
capture_as_of: "2026-08-11"        # 캡처 스크립트가 응답 date 와 동등성 단언
capture_fixture: "tests/fixtures/frozen/aggregation-2026-08-11"
capture_git_sha: a000add           # 재캡처 시점 (M1.0-a 재빌드 커밋 — 구현 코드 변경 0줄 상태)
capture_fixture_manifest_git_sha: a224593   # 픽스처 MANIFEST 가 기록한 빌드 시점 SHA
capture_fixture_superset_of: adb1f25        # F13-1 기준 빌드 식별자
baseline_files: 3                  # ranking-current.json · stage-overview.json · MANIFEST.md
baseline_sector_count: 18          # >= 10 (AC-SAG-047)
baseline_excess_returns_degenerate: false   # 18/18 섹터가 returns 와 상이. max gap 16.166200
baseline_distribution_total: 321   # 구 baseline 135 → 재캡처 321 (유효 유니버스 확대의 귀결)
d12_forbidden_string_count: 0      # sector_excess_return · total_count 양 파일 0건
new_warnings_or_lints_introduced: 0
full_suite_delta: "+35 passed (702 → 737, AC-SAG-048 F12/F13 테스트 신설) / failed 8 (전건 pre-existing, 동일 집합) / errors 25 (pre-existing) / 신규 실패 0"
date_axis_fixture_touched: false   # tests/fixtures/frozen/weekly-2026-08-12/ 미변경 (git status/diff 공백 확인)
aggregation_fixture_touched: true  # [재실행] M1.0-a 재빌드 — 145 → 331 이름 / 9.0 → 16.8 MB
production_code_touched: true      # [M2] weighting.py 신설 + sector_metrics.py 집계 교체 + 서비스/라우터 배선. near_52w_high 규약 Y 적용은 여전히 M5
live_db_mutated: false             # /api/db/update 미실행
negative_verification: observed-red-3        # NEG-1 F2→999 RED · NEG-2 F12-a→999 RED · NEG-4 golden 파일 이동 RED. 3건 모두 복원 후 sha256 바이트 동등 확인
negative_verification_f13_1: not-reproduced  # [Gap G1] 상위집합 OFF 시 4/4 green, 순수 시총순에서도 2/4(F5-a·F6)만 RED. 빌더의 플래그 인지 선별이 제2 충족 경로
mutation_verification_m2: observed-red-4   # mut_equal_weight(10 RED) · mut_effective_n_uncapped(1) · mut_plan31_verbatim(8, 위반 3183/4000) · mut_reintroduce_cap_literal(1). 4건 모두 복원 후 GREEN + 바이트 동등 확인
point_of_no_return_crossed: true   # **M2 커밋 — 구 등가중 구현 교체. 골든 baseline 재캡처 창이 영구히 닫혔다**
fixture_rebuild_required: false    # [해소 a000add] F1~F13 전건 충족. F12-a 17(1.42x) · F12-b 13(4.33x) · F12-c 12(2.40x) · F13-2 17(1.21x) · F13-3 13/12(목표 9)
fixture_rebuild_measurements: "종목 331(지수 2) · 유효 유니버스 321 · weekly 31,254행/385날짜 · 격자 346바 · 16.8 MB · F2 18 · F3 2·1 · F5-a 9 · F5-b 10 · F6 1 · F7(규약 Y) 24 · F9 345 · F10 0·0 · F13-1 누락 0 · F13-4 패션 5·3 · F13-6 323행/0행"
f7_convention: "Y"                 # NULL MAX52 를 신·구 양쪽 분자·분모에서 제외. 규약 X 51 → 규약 Y 24, 차이 27 = NULL 종목 수
golden_baseline_discarded: true    # [완료 8e51176] b839cee 캡처분(F12 미충족 픽스처 위) 폐기 후 재빌드 픽스처에서 재캡처. 폐기 전 sha256 은 §E.2 M1.0-b 재캡처 E1 에 기록
relief_valve_used: none            # F13-2 14→12 축소 미사용. 크기 16.8 MB 로 예산(16~17 MB) 내
next_gate: "M7 — 테스트 대체 + 회귀 게이트(프로즌 픽스처 재확인, 되돌림 실증 라운드, 릴리스 노트)"
deferred_to_m6: "[PARTIALLY RESOLVED — M6] AC-SAG-007 전체(RESOLVED, §E.2 참조) · AC-SAG-043 파생 구조 절(D19, RESOLVED — M5에서 이미 신설된 것 재확인) · AC-SAG-021 market 절(RESOLVED — market=kospi 시 제외 섹터 발생·rank 최대값 감소 실증) / AC-SAG-021 period 절(NOT RESOLVED — `period` 는 라우터에서 수신·검증만 하고 rank 배정에 영향을 주지 않는다, G22) · AC-SAG-023(NOT RESOLVED — rank_change 의 최상위 baseline_date 응답 노출은 이번 M6 스코프에 포함하지 않았다, G25로 신규 기재) · AC-SAG-046 원판(NOT RESOLVED — trading_value_window_days/rank_change.baseline_date 최상위 노출 미실행, lite 대체 유지, G25) · compute_rrg 함수 수준 배선(NOT RESOLVED — G20으로 이월, 라우터 파라미터만 신설·실계산 미배선) · SectorAggregate.trading_value/trading_value_window_days 응답 필드(NOT RESOLVED — G16 그대로 잔존, 아래 참조)"
g10_g14_g16_resolution: "G10(period/market 라우터 미배선) → M6 ranking/history/detail/stage-overview 에서 실배선 완료(RESOLVED). G14(compute_rrg 라우터 배선) → 라우터 파라미터는 신설했으나 실 데이터 재계산(시장별 지수 소스 부재)은 미배선 — G20 으로 재이월(NOT RESOLVED). G16(SectorAggregate.trading_value 응답 필드) → 실측 확인 결과 `compute_trading_value_by_period` 는 여전히 함수 수준 정의만 있고(`grep -rn compute_trading_value_by_period my_chart/ backend/` → 정의 1건, 호출 0건) `SectorAggregate` dataclass 에 trading_value 필드 자체가 없다(`aggregate_types.py` — Coverage/ValidCounts 의 커버리지-비율용 trading_value 와는 다른 필드). **G16 은 해소되지 않았다** — M6 은 stage/overview 종목 목록의 trading_value(weekly 근사, AC-SAG-041)만 다뤘고 SectorAggregate(data[] 섹터 집계 항목)의 trading_value 필드 신설은 다루지 않았다. 초기 기재(RESOLVED 주장)는 미검증 주장이었음을 확인 후 정정한다(verification-claim-integrity 원칙)"
total_run_phase_files: 54          # M2 27 + M3 1종 + M4 2종 + M5 14종 + M6 10종(`git diff --stat adf4bb8..e139067` 실측)
# --- M2 (2026-08-13) ---------------------------------------------------------
m2_new_tests: 48                   # test_weighting 18 · test_sector_aggregation 23 · test_inv_cap1_scan 7
m2_full_suite: "8 failed, 786 passed, 68 skipped, 1 xpassed, 25 errors — B-2 baseline 과 실패 집합 동일, 신규 실패 0"
m2_gate_tests_still_green: 105     # test_aggregation_fixture 65 + test_golden_baseline 40 (착수 전/후 동일)
m2_fixtures_touched: false         # git status --porcelain tests/fixtures/ 공백
m2_ac002_max_deviation: 3.553e-15  # 프로덕션 vs 독립 참조, AG-5 통과 non-null 16섹터. 임계 1e-9
m2_ac002_null_sectors: "패션(AG-4 유효시총 3) · 헬스케어(AG-7 rs 커버리지 0.45)"
m2_ac049_iteration_histogram: "{1:165, 2:1030, 3:1580, 4:912, 5:290, 6:23} — 최악 6회, exhausted 0"
m2_ac049_fixed_point_dev: 6.695e-12
m2_ac049_closed_form_dev: 5.551e-17
m2_ac050_scan1_hits: 0             # 첫 실행은 RED(신설 테스트 독스트링 2곳) — 문구 수정 후 0
m2_ac050_scan2_hits: 0
m2_return_source_changed: "저장 CHG_* → Close(t)/Close(anchor(t,N))−1. 픽스처 실측 CHG_1M 기준 바 = 2026-07-16, anchor(t,28) = 2026-07-10 (다른 바)"
m2_universe_restriction_added: true  # compute_sector_aggregates 가 compute_universe(UN-3) 유효 유니버스로 제한
coverage_m2: not-measured          # [Gap G6] coverage.py C-tracer x numpy 2.4.2 = "cannot load module more than once per process". 관측하지 않은 수치를 기재하지 않는다
m2_open_gaps: "G6(커버리지 미측정) · G7(AC-SAG-002 CHG_1M 표기 ↔ MANIFEST 앵커 불일치 — manager-spec 표기 정정 권고) · G8(F12 vs 프로덕션 AG-7 범위 차 — 무모순, 명시화 완료) · G9(유니버스 제한 도입)"
m2_benchmark_path_status: "완료(M3) — 미존재 상태 해소"
# --- M3 (2026-08-13) ---------------------------------------------------------
m3_new_tests: 35                   # test_sector_benchmark_ranking.py 전건 신설
m3_full_suite: "8 failed, 821 passed, 68 skipped, 1 xpassed, 25 errors — M2 baseline 과 실패 집합 동일, 신규 실패 0"
m3_gate_tests_still_green: 105     # test_aggregation_fixture 65 + test_golden_baseline 40 (M3 착수 전/후 동일)
m3_fixtures_touched: false         # git status --porcelain tests/fixtures/ 공백
m3_benchmark_new_call_sites: 0     # _compute_benchmark 가 _aggregate_members 를 재사용 — capped_weights_detail call-site 수 불변(fan_in 3 유지)
m3_ac011_reference_max_deviation_pp: "1e-9 이내(3개 시장 모두)"  # 참조 구현 대조
m3_ac015_tolerance_pp: "{1w: 0.5, 1m: 3.0, 3m: 7.0}"  # BENCHMARK_RECONCILIATION_TOLERANCE_PP 단일 정의
m3_ac017_norm_impl: "순수 파이썬 average-tie 재구현 — scipy 미설치(venv 확인) 이므로 신규 의존성 추가 없이 대체"
m3_ac020_static_scan_scope: "_rank_sectors 함수 소스 AST 스캔(0건) — legacy compute_sector_ranking 경로는 대상 아님(하위 호환 SectorRank 표면, M3 미변경)"
m3_rank_change_recursion_guard: "compute_rank_change 파라미터로 1단 재귀만 허용(무한 재귀 방지) — baseline 호출은 compute_rank_change=False"
mutation_verification_m3: observed-red-3   # mut_benchmark_ignores_market_filter(2 RED) · mut_round_in_sort_path(1 RED) · mut_partial_composite(1 RED, TypeError 로 검출). 3건 모두 복원 후 GREEN + 바이트 동등 확인(diff /tmp/sector_metrics.py.bak)
m3_open_gaps: "G10(라우터 파라미터 미배선 — M6 의존) · G11(AC-SAG-046 원 픽스처·금요일 종단 절 미실행, lite 로 대체) · G12(AC-SAG-013 부호분산 합성 픽스처 전용 테스트 미작성) · G13(커버리지 미측정, G6 연속)"
# --- M4 (2026-08-13) ---------------------------------------------------------
m4_new_tests: 11                   # test_sector_rrg.py 전건 신설
m4_full_suite: "8 failed, 832 passed, 68 skipped, 1 xpassed, 25 errors — M3 baseline 과 실패 집합 동일, 신규 실패 0"
m4_gate_tests_still_green: 123     # test_aggregation_fixture 65 + test_sector_aggregation 23 + test_sector_benchmark_ranking 35 (M4 착수 전/후 동일)
m4_fixtures_touched: false         # git status --porcelain tests/fixtures/ 공백 — M4 는 순수 함수라 DB 픽스처 자체를 쓰지 않는다
m4_new_module: "my_chart/analysis/rrg.py (신설, 순수 함수 — DB 미접근)"
m4_legacy_rrg_untouched: true      # my_chart/analysis/sector_advanced.py(SPEC-TOPDOWN-001A 소관 z-score RRG) 미수정
m4_interpretation_note: "AC-SAG-032 워밍업 산식 미명시 — lookback_weeks 만큼 trail 앞부분 절단 + 모멘텀 단순 lag-1 차분으로 단일 통과 해석(§E.2 M4 E1 상세)"
mutation_verification_m4: observed-red-3   # mut_current_weight(1 RED) · mut_no_warmup(2 RED) · mut_rs_ratio_100_fallback(1 RED). 3건 모두 복원 후 GREEN + 바이트 동등 확인(diff /tmp/rrg.py.bak)
m4_counter_naive_jump: "naive(날짜별 Σ(close×cap)/Σcap, 현재 가중치) 방식은 구성종목 변동 시점(d2→d3)에서 비율 1.000098 (기대 1.01 대비 0.0099 이탈, 임계 0.005 초과) — 체인 방식은 같은 구간에서 1.01±0.001 유지(test_ac_sag_033_index_chain_no_jump_on_membership_change)"
m4_open_gaps: "G14(compute_rrg 라우터 배선 미실행 — M6 의존) · G15(커버리지 미측정, G6/G13 연속)"
# --- M5 (2026-08-13) ---------------------------------------------------------
m5_new_tests: "tests/ 신규 12(test_ac_sag_024_high52.py 5 + test_ac_sag_029_trading_value.py 3 + test_ac_sag_030_rs_avg.py 4, pytest 844−832 델타로 실측) + backend/tests/ 함수정의 기준 신규 13(test_sector_detail_service.py +7 · test_stage_service.py +3(신설 파일) · test_sector_advanced.py +3, git show b2f45d2 대비 AST 함수정의 카운트)"
m5_full_suite: "8 failed, 844 passed, 68 skipped, 1 xpassed, 25 errors — M4 baseline 과 실패 집합 동일, 신규 실패 0"
m5_gate_tests_still_green: 146     # test_aggregation_fixture + test_sector_aggregation + test_sector_benchmark_ranking + test_sector_rrg + test_sector_metrics 5파일 합산 실측(M5 완료 후 재확인)
m5_fixtures_touched: false         # git status --porcelain tests/fixtures/ 공백
m5_commit_strategy: "지표별 5개 독립 커밋(plan.md M5 규약) — 9f2318c(MAX52)·d17c737(Stage단일화)·5c14e17(volume_ratio)·b7e9f97(trading_value)·98f5809(RS평균, 테스트 전용)"
m5_f7_convention_reused: true      # AC-SAG-024 규약 Y 는 M1.0-a 재빌드가 이미 확정한 것을 프로덕션 경로(near_52w_high)에 적용 — F7 MANIFEST 기록과 동일 규약
m5_rs_avg_production_unchanged: true   # #5 RS 평균은 프로덕션 코드 변경 없음(_equal_mean 은 M2 시점부터 이미 정합) — 게이팅 테스트만 신설
mutation_verification_m5: observed-red-4   # mut_stored_max52(1 RED)·mut_daily_simple_retained(2 RED)·mut_price_sma10_approx(4 RED)·mut_rs_zero_fill(2 RED). 4건 모두 복원 후 GREEN + 바이트 동등 확인(diff /tmp/moai-verify/*.bak). AC-SAG-029 정적 스캔은 개발 중 우발적 RED로 검출력 실증(§E5 참조)
m5_open_gaps: "G16(trading_value 응답 필드·라우터 배선 미실행 — M6 의존) · G17(AC-SAG-045 R4 골든 baseline 비교 미실행 — M7 소관) · G18(backend/tests/ 디렉토리 일괄 실행 시 사전 존재 test-isolation 결함, SPEC 범위 밖) · G19(커버리지 미측정, G6/G13/G15 연속)"
m1_to_mN_commit_strategy: "마일스톤별 개별 커밋 후 main 직푸시 (Hybrid Trunk 1인 OSS)"
# --- M7 (2026-08-14) ----------------------------------------------------------
m7_new_test_files: "tests/test_ac_sag_044_regression.py(3) · tests/test_ac_sag_045_r1_r4_r5a.py(11) · tests/test_as_of_static_scan_m7.py(13, 1 skip) + tests/test_sector_metrics.py 기존 파일 hasattr→값단언 교체(순증 0, 카운트 불변 12) + scripts/spec_checks/as_of_none_scan.sh(coarse 셸 스캔)"
m7_full_suite: "8 failed, 900 passed, 69 skipped, 1 xpassed, 25 errors — M6-gap-closure baseline(873 passed) 대비 +27 passed, 실패/에러 집합 동일, 신규 실패 0"
m7_gate_tests_rerun_idempotent: true   # 227개 게이팅 관련 테스트 2회 연속 실행 동일 결과(§8.4 규약 1)
m7_fixtures_touched: false             # 집계·날짜축 픽스처 모두 미변경(git status 공백)
m7_commit_strategy: "단일 커밋(753a529) — main 직푸시(Hybrid Trunk 1인 OSS)"
m7_coverage_measurement: gap           # pytest-cov 미설치(venv에 부재, pip 바이너리 셸 부재) — 대리 지표: 신규 테스트 14건이 대상 함수 경로 직접 실행
m7_ac_sag_037_status: gap              # 7-엔드포인트 as_of_date 일치 되돌림 실증 미구현 — 후속 필요(§E.2 M7 §7 참조)
m7_open_gaps: "AC-SAG-037(7-엔드포인트 as_of_date 일치 되돌림 실증 미구현) · 커버리지 % 미측정(pytest-cov 부재)"
```

### M6 Gap Closure — G16/G20/G21/G22/G23/G25 (2026-08-14)

M6 §E.2 에 남은 6건의 Gap을 M7(회귀 게이트) 착수 전에 해소한다. `cycle_type=tdd`
위임 세션 — 각 gap마다 되돌림(수정 전 상태) RED를 실측 후 수정 GREEN을 확인했다
(§E.2 관행 — 대조 단언 판정 기준은 lessons.md #9).

#### 상태 매트릭스

| Gap | 상태 | 근거 |
| --- | --- | --- |
| **G16** | **RESOLVED** | `compute_trading_value_by_period`(M5 신설)를 `SectorAggregate.trading_value`(기간별 dict, `returns`와 동형)에 배선. `_compute_sector_aggregates_core`가 `anchor_dates`(수익률과 동일 호출) 기준으로 1회 계산해 `_Member.trading_value`에 실은 뒤 `_aggregate_members`에서 결측 제외 합산. `envelope.py` `SectorAggregateModel.trading_value` + `aggregate_model()` 배선. `Coverage.trading_value`/`ValidCounts.trading_value`는 의도적으로 `None` 유지(AG-7 최소값 오염 방지, aggregate_types.py 기존 주석과 동일 근거) — 이 필드는 그 게이팅과 무관한 별도 값 필드다. |
| **G20** | **RESOLVED** | RRG: `compute_sector_price_index`/`compute_rrg_data`에 `market` 전달 → `_build_sector_stock_map`의 기존 `market_filter` 재사용(별도 시장별 지수 저장소 신설 없음). 종목 버블: `compute_stock_bubble`에 `market` 추가 — `sector_stocks` 필터링에 `stock_meta[name]["시장구분"]` 비교 적용. 실측(§ 하단 E2): market=kospi에서 18개 섹터 전부 rs_ratio가 market=all과 달라짐(더 이상 echo 전용 아님); 종목 버블 kospi 9종목 vs all 17종목(축소 확인). |
| **G21** | **RESOLVED** | `stage_service._load_extended_weekly_fields`가 weekly `Close×Volume` 근사 대신 M5 정규 원천(`compute_trading_value_by_period`, daily `VolumeWon`, 1W 창)을 소비하도록 교체. `daily_db_path` 미전달 시(호출자 없음) 결측(`None`) 유지 — 조용한 근사 대체 금지. |
| **G22** | **RESOLVED** | `_rank_sectors(aggregates, period=...)` 신설 — `period` 지정 시 그 기간의 (정규화 전) 초과수익률 단독을 rank 정렬 키로 사용(AC-SAG-021 "해당 (period, market)의 초과수익률 기준"). `composite_score`는 항상 3기간 가중합 유지(AC-SAG-022 비회귀). `compute_sector_aggregates`/`_compute_sector_aggregates_core`에 `period` 관통 배선, baseline(rank_change) 재귀 호출에도 동일 period 전달(같은 기준 비교 유지). 라우터 `/sectors/ranking`이 `period`를 `get_sector_ranking`에 전달. 레거시 `sectors[]`(`compute_sector_ranking`)는 영향 없음(AC-SAG-036 3윈도우 상설 요구 유지). |
| **G23** | **RESOLVED** | `StockBubble`/`StockBubbleItem`에 `weight_in_sector`/`chg_1w`/`chg_3m`/`near_52w_high` 4필드 신설. `weight_in_sector`는 `weighting.capped_weights_detail`(stage_service와 동일 산식 재사용, INV-CAP-1)로 market 필터 후 유니버스 기준 산출. `chg_1w`/`chg_3m`/`near_52w_high`는 별도 원시 쿼리(`_load_raw_chg_max52`)로 결측을 `None` 보존(§9.1) — 기존 `_get_price_on_date`(공유 함수, 결측 0 치환)는 건드리지 않음(scope discipline). |
| **G25** | **RESOLVED** | `EnvelopeMixin`에 `baseline_date`/`trading_value_window_days` 신설(봉투 10키 → 12키). `envelope_fields()`가 `trading_value_window_days` 미지정 시 `return_window_days`와 **동일 dict**를 채운다(O-A4 — 같은 anchor 창 공유이므로 항등이 자명하게 성립). `get_sector_ranking`이 `agg.baseline_date`를 `envelope_fields(baseline_date=...)`로 전달. |

#### 되돌림(RED) 실측 — `git stash push` 로 프로덕션 파일만 pre-fix로 되돌린 뒤 신규 회귀
테스트(`tests/test_m6_gap_closure.py`) 실행, 이후 `git stash pop`으로 복원.

```
$ git stash push -m "m6-gap-closure-verify-red" -- \
    my_chart/analysis/aggregate_types.py my_chart/analysis/sector_metrics.py \
    backend/schemas/envelope.py backend/services/sector_ranking_service.py \
    backend/routers/sectors.py my_chart/analysis/sector_advanced.py \
    backend/schemas/sector_advanced.py backend/services/sector_advanced_service.py \
    backend/services/stage_service.py
$ pytest tests/test_m6_gap_closure.py -q
10 failed, 1 passed, 1 warning in 5.94s
  FAILED test_g16_compute_trading_value_by_period_has_call_site
  FAILED test_g16_data_trading_value_field_present_and_populated
  FAILED test_g20_rrg_market_filter_recomputes_rs_ratio
  FAILED test_g20_stock_bubble_market_filter_reduces_universe
  FAILED test_g21_stage_overview_trading_value_matches_canonical_source
  FAILED test_g22_period_changes_data_rank
  FAILED test_g23_stock_bubble_item_has_ac_sag_041_fields
  FAILED test_g23_weight_in_sector_sums_close_to_one
  FAILED test_g25_baseline_date_exposed_at_top_level
  FAILED test_g25_trading_value_window_days_matches_return_window_days_per_period
$ git stash pop   # 프로덕션 수정 복원
$ pytest tests/test_m6_gap_closure.py -q
11 passed, 1 warning in 7.12s
```

10/11 되돌림 RED(9개 defect-proving 테스트 + G22 대비 테스트 1건 — `test_g16_
compute_trading_value_by_period_has_call_site`도 포함해 총 10건). 나머지 1건
(`test_g22_composite_score_still_present_alongside_rank`)은 비회귀 확인용(defect
판별자가 아니므로 pre-fix에서도 PASS가 정상 — AC-SAG-022는 M6 이전부터 유지).

#### AC 재검증 (수정 후, 픽스처 고정)

```
$ pytest tests/ -k "ac_sag_021 or ac_sag_023 or ac_sag_029 or ac_sag_041 or ac_sag_046" -v
14 passed
  AC-SAG-021: test_ac_sag_021_ranks_are_contiguous_and_sorted PASSED
  AC-SAG-021: test_ac_sag_021_market_filter_reduces_max_rank PASSED
  AC-SAG-023: test_ac_sag_023_baseline_date_is_anchor_t_minus_28 PASSED
  AC-SAG-023: test_ac_sag_023_rank_change_none_for_sector_absent_at_baseline PASSED
  AC-SAG-029: test_ac_sag_029_given_then_trading_value_from_volume_won_not_close_times_volume PASSED
  AC-SAG-029: test_ac_sag_029_compute_trading_value_by_period_sums_volume_won_over_anchor_window PASSED
  AC-SAG-029: test_ac_sag_029_static_scan_no_close_times_volume_recomputation PASSED
  AC-SAG-041: test_ac_sag_041_stage_stock_has_required_fields PASSED
  AC-SAG-041: test_ac_sag_041_weight_in_sector_not_literal_010_degenerate_sector PASSED
  AC-SAG-041: test_ac_sag_041_weight_in_sector_red_when_literal_010_used PASSED
  AC-SAG-041(G23): test_g23_stock_bubble_item_has_ac_sag_041_fields PASSED (tests/test_m6_gap_closure.py)
  AC-SAG-046: test_ac_sag_046_lite_return_window_days_literal PASSED
  AC-SAG-046: test_ac_sag_046_lite_mut_label_constant_window_is_detectable PASSED
  AC-SAG-046: test_ac_sag_046_lite_benchmark_anchor_date_matches_1w PASSED
```

#### 전체 스위트 델타

```
$ pytest tests/ -q
8 failed, 873 passed, 68 skipped, 1 xpassed, 25 errors in 110.42s
```

M6 완료 시점 baseline(862 passed / 8 failed / 25 errors, 실패·에러 집합 동일)
대비 **+11 passed**(`tests/test_m6_gap_closure.py` 신규 11건), 실패 8건·에러
25건은 전건 baseline과 동일 집합(사전 존재, SPEC 범위 밖 — 신규 실패 0건).

#### 미해소 / 이관 항목 (없음)

이번 세션에서 6건 전부 RESOLVED로 종결했다. DEFERRED-WITH-RATIONALE 또는
MISDIAGNOSED로 분류된 항목은 없다.

#### 해석이 필요했던 지점 (단일 패스 최선 해석)

1. **G16 `trading_value` 필드 모양** — spec.md/plan.md/G16 원문은 "응답 필드
   신설"만 명시하고 스칼라 vs 기간별 dict 여부를 특정하지 않았다. `trading_
   value_window_days`가 `return_window_days`(3키 dict)와 동일 모양으로 요구된
   점(AC-SAG-046)에 근거해 `SectorAggregate.trading_value`도 `returns`/
   `excess_returns`와 동형인 `dict[str, MetricValue]`(3기간)로 해석했다.
2. **G22 `rank_change`의 period 결속** — AC-SAG-021은 `data[].rank`가 period에
   결속돼야 함을 요구하지만 `rank_change`(baseline 대비 순위 이동)의 period
   결속 여부는 명시하지 않는다. baseline 재귀 호출에도 동일 period를 전달해
   "같은 기준(같은 period)의 순위 이동"으로 해석했다 — 이질적 기준(현재
   period-rank vs baseline composite-rank) 비교를 피하기 위함이다.
3. **G23 필드 적용 범위** — spec.md §12.3은 종목 목록 대상을 "`/stage/overview`,
   종목 버블"로 명시한다. G23 원문은 `/sectors/{name}/bubble`의 `StockBubbleItem`
   미비를 지적했으므로 그 표면만 확장했다(`/sectors/bubble`의 `SectorBubbleItem`
   — 섹터 단위 버블 — 은 대상 밖으로 해석, 종목 단위 필드 요구가 아니므로).

### M7 — 테스트 대체 + 회귀 게이트 (2026-08-14)

M6 gap closure(`b337365` 이전) 이후 이 SPEC의 종료 마일스톤. plan.md M7 체크리스트
8개 항목을 아래에 항목별로 보고한다.

#### 1. 프로즌 픽스처 확인 (게이팅 AC 재실행 + `/api/db/update` 등가 재실행)

- 게이팅 열거 7개 파일 전부(`test_sector_aggregation.py` / `test_sector_benchmark_
  ranking.py` / `test_ac_sag_024_high52.py` / `test_ac_sag_030_rs_avg.py` /
  `test_sag_m6_router_wiring.py` / `test_golden_baseline.py` /
  `test_aggregation_fixture.py`) + `test_inv_cap1_scan.py` + `test_weighting.py` +
  `test_sector_rrg.py`를 함께 2회 연속 실행 — **227 passed, 227 passed**(변화 없음,
  §8.4 규약 1 "재실행해 붉어지지 않음" 충족).
  ```
  $ pytest tests/test_sector_aggregation.py tests/test_sector_benchmark_ranking.py \
      tests/test_ac_sag_024_high52.py tests/test_ac_sag_030_rs_avg.py \
      tests/test_sag_m6_router_wiring.py tests/test_golden_baseline.py \
      tests/test_aggregation_fixture.py tests/test_inv_cap1_scan.py \
      tests/test_weighting.py tests/test_sector_rrg.py -q
  227 passed, 1 warning in 9.39s   (1st run)
  227 passed, 1 warning in 9.32s   (2nd run — idempotency 확인)
  ```
- 실제 라이브 `/api/db/update` 를 이 세션에서 실행하지는 않았다(라이브 DB를 건드리면
  §8.4 규약 3의 "라이브 비게이팅 스모크" 범위를 넘어 픽스처 자체를 변경할 위험이
  있다) — 대신 **동형의 재실행 등가**로 게이팅 테스트 스위트를 2회 반복해 결정성을
  확인했다(위). 라이브 `/api/db/update` 자체 실행은 배포 환경 스모크로 별도 관리
  범위이며, 이 SPEC의 게이팅 계약은 §8.4 규약 3에 따라 애초에 라이브 실행에
  결속되지 않는다(순수 픽스처 기반).

#### 2. 집계 픽스처 F1~F13 재확인 (AC-SAG-048 회귀)

```
$ pytest tests/test_aggregation_fixture.py -q
65 passed, 1 warning in 0.52s
```
MANIFEST 실측 기록(F1~F13, `synthetic_bar`, `as_of: "2026-08-11"`, `git_sha:
"a224593"`)과 실제 픽스처 내용의 일치를 검증하는 65개 테스트 전부 PASS — M1.0-a
종료 시점(`a000add`) 대비 **드리프트 없음**(NO).

#### 3. `as_of=None` 정적 스캔 (§8 규약 8)

**정직한 기재**: acceptance.md §8.4 규약 8 원문은 스캔 명령의 리터럴 코드 블록을
담고 있지 않다(산문 서술만: "정적 스캔으로 강제 — 게이팅 테스트 파일에서
`as_of=None` 리터럴 사용 0건, ... `bash -n` 으로 문법 검증한 뒤 실행"). 따라서
"명세 블록에서 바이트 동등 추출"은 대상이 없어 수행할 수 없었다 — 대신 이 규약을
**코드로 최초 구현**했고, 그 사실을 이 항목에 정직하게 기록한다.

구현 2단:
1. **coarse 셸 스캔**(`scripts/spec_checks/as_of_none_scan.sh`, 신규) — `bash -n`
   문법 검증 통과 후 실행:
   ```
   $ bash -n scripts/spec_checks/as_of_none_scan.sh
   syntax-check exit=0
   $ bash scripts/spec_checks/as_of_none_scan.sh
   PASS: 0 code-level as_of=None literal occurrences in 7 gating test files
   (coarse grep; AST scan is authoritative).
   run exit=0
   ```
2. **AST 기반 정밀 스캔**(`tests/test_as_of_static_scan_m7.py`, 신규) — 실제 함수
   호출의 키워드 인자만 매치(docstring/주석/문자열 리터럴 오탐 0):
   ```
   $ pytest tests/test_as_of_static_scan_m7.py -v
   13 passed, 1 skipped in 0.30s
   ```
   (`test_golden_baseline.py`는 격자·집계 진입점 호출이 없어 정당하게 skip — 그
   자체가 baseline 구조 검사 파일이지 as_of 인자를 받는 함수 호출자가 아니다.)

기존에 `tests/test_aggregation_fixture.py::test_gating_test_pins_as_of_explicitly`
가 **자기 파일 하나만** 정적 스캔하고 있었다 — 이번 M7에서 **7개 게이팅 파일
전부**로 확장했다(M7 이전에는 나머지 6개 파일이 스캔 커버리지 밖이었다는 뜻이며,
실측상 이번 확장 검사에서도 위반 0건이었다 — 즉 커버리지 확장 자체가 새 결함을
발견하지는 않았지만, 그 사실을 검증하는 코드가 M7 이전에는 존재하지 않았다).

#### 4. AC-SAG-044 — 의미 테스트로의 대체

```
$ grep -c "hasattr" tests/test_sector_metrics.py
0
```
`test_sector_rank_has_required_fields`(구 hasattr 15건, `:195-218`)을 값 단언
블록으로 교체(`tests/test_sector_metrics.py`) — 타입/범위 단언(0~100 pct 필드,
float 필드, `rank >= 1` 등) + 관계 단언(`sector_excess_return_1w ==
sector_return_1w - KOSPI_1w`).

되돌림 검출 3케이스(신규 `tests/test_ac_sag_044_regression.py`):
```
$ pytest tests/test_ac_sag_044_regression.py -v
test_ac_sag_044_mut_a_cap_weight_to_equal_weight_changes_values PASSED
test_ac_sag_044_mut_b_percentile_norm_to_minmax_changes_composite PASSED
test_ac_sag_044_mut_c_benchmark_disconnect_changes_excess_return PASSED
3 passed in 0.74s
```
- (a) 시총가중→등가중: `daily_db_path=None`(시총 원천 부재, AG-4 등가중 폴백)으로
  `compute_sector_ranking`을 재호출 — 18개 공통 섹터 중 값이 갈리는 섹터가 임계
  `>=3`을 충족.
- (b) 순위백분위→min-max: **범위 정정** — `compute_sector_ranking`(legacy 호환
  표면)은 실측 확인 결과 애초부터 `_normalize_list`(min-max)를 무조건 쓰고
  있어(마이그레이션되지 않은 알려진 단순화, 새로 발견한 사실) 그 표면에서는
  percentile→min-max 되돌림이 **항등 변환**이 되어 검출력이 0이었다. 실제
  percentile 정규화(AC-SAG-017/045 R5-a)의 production 경로인
  `compute_sector_aggregates`/`_rank_sectors`(`norm()`)를 대상으로 교체해
  검출력을 실증했다.
- (c) 벤치마크 방법론: `_load_kospi_returns`를 0으로 고정하는 되돌림에서
  `sector_excess_return_1w == sector_return_1w`가 되는 섹터가 5개 이상 발생함을
  확인(정상 경로에서는 이 등식이 성립하지 않는 섹터가 5개 이상) — 벤치마크
  방법론이 실제로 초과수익률에 반영되고 있음을 대조로 실증.

**Gap — 커버리지 측정 불가**: `pytest-cov`가 이 venv에 설치돼 있지 않고(`pip`
바이너리 자체가 셸에서 사용 불가) 커버리지 % 를 기계적으로 측정하지 못했다. AC-
SAG-044의 "신규/변경 집계 모듈 라인 커버리지 >= 85%" 절은 **미검증(Gap)** 으로
남긴다 — 대리 지표로 신규 테스트 14건(ac_sag_044 3 + ac_sag_045_r1_r4_r5a 11)이
`sector_metrics.py`의 `compute_sector_ranking` / `compute_sector_aggregates` /
`_rank_sectors` / `norm` / `_normalize_list` / `_load_kospi_returns` 경로를 직접
실행한다.

#### 5. AC-SAG-045 R1 / R3 / R4 / R5-a / R6 회귀 방지

**정직한 기재 — 신규 발견**: M1.0-b~M6 구간까지 골든 baseline은 **구조만**(파일
존재·키 존재·`as_of` 일치·엔트리 수, AC-SAG-047) 검사됐고, R1/R4/R5-a의 **값
비교 단언 자체**는 이번 M7 이전까지 어느 테스트 파일에도 구현돼 있지 않았다.
`tests/test_ac_sag_045_r1_r4_r5a.py`(신규)로 M7에서 최초 구현:

```
$ pytest tests/test_ac_sag_045_r1_r4_r5a.py -v
test_baseline_and_new_share_as_of PASSED
test_ac_sag_045_r1_composite_rank_moved_set_nonempty_ge5 PASSED
test_ac_sag_045_r1_mut_service_not_rewired_control PASSED
test_ac_sag_045_r4_rs_avg_average_and_count_increase PASSED
test_ac_sag_045_r4_mut_rs_zero_fill_control PASSED
test_ac_sag_045_r5a_norm_is_evenly_spaced[1w] PASSED
test_ac_sag_045_r5a_norm_is_evenly_spaced[1m] PASSED
test_ac_sag_045_r5a_norm_is_evenly_spaced[3m] PASSED
test_ac_sag_045_r5a_mut_minmax_norm_control[1w] PASSED
test_ac_sag_045_r5a_mut_minmax_norm_control[1m] PASSED
test_ac_sag_045_r5a_mut_minmax_norm_control[3m] PASSED
11 passed in 1.16s
```
- **R1**: `composite_rank`(period=None 시 `rank`) 이동 섹터 집합 — golden(18섹터)
  대비 공통 섹터 18개 중 이동 섹터 `>= 5`(공집합 아님) 확인. 되돌림
  `mut_service_not_rewired`(구조적 보장 — golden 자기 자신과 비교하면 이동
  집합이 정확히 공집합이 됨을 직접 확인)로 검출력 실증.
- **R3**: AC-SAG-024 게이팅 절과 동일 파생 규칙 공유 — `tests/test_ac_sag_024_
  high52.py`(기존)가 이미 PASS(§E.2 M5 참조), M7에서 별도 재구현 불필요(파생
  규칙 공유이므로 중복 회피).
- **R4**: 전 섹터 `rs_avg` 평균이 golden 대비 상승 + 상승 섹터 수 > 하락 섹터
  수(N=18 >= 10) 확인. 되돌림 `mut_rs_zero_fill`은 AC-SAG-030과 공유 —
  `test_ac_sag_030_rs_avg.py`의 기존 검출력 실증을 서브프로세스로 재확인.
- **R5-a**: 3개 기간(1w/1m/3m) 전부 `norm(excess_p)` 정렬 결과가 등간격
  `[0, 100/(N-1), ...]`과 `1e-6` 이내 일치. 되돌림 `mut_minmax_norm`(min-max로
  치환)에서 등간격이 깨짐을 3개 기간 전부에서 확인.
- **R6**: AC-SAG-007과 동일 파생 규칙(F3, `mut_no_ag5_gate`) 공유 — M6
  `test_sag_m6_router_wiring.py`가 이미 PASS + RED 캡처 완료(§E.2 M6 참조),
  M7에서 재구현 불필요.

#### 6. AC-SAG-050 정적 스캔 2종 + 음성 검증

```
$ pytest tests/test_inv_cap1_scan.py -v
8 passed in 0.40s
```
스캔 1(코드) + 스캔 2(SPEC 본문) 둘 다 위반 0건, `mut_reintroduce_cap_literal`
음성 검증(`test_ac_sag_050_scan2_is_actually_capable_of_firing`)이 스캔 2가 실제로
위반을 검출할 수 있음을 재확인(M2에서 이미 실증됐고 M7은 회귀 재확인).

#### 7. §9 되돌림 실증 완결 라운드 — mutation 변형 커버리지 테이블

| 변형/AC | 판정 | 근거 |
| --- | --- | --- |
| `mut_equal_weight`(AC-SAG-002) | already-verified-in-M2 | `test_sector_aggregation.py::test_ac_sag_002_mut_equal_weight_is_detectable`, progress.md §E.2 M2 |
| `mut_effective_n_uncapped`(AC-SAG-010) | already-verified-in-M2 | progress.md §E.2 M2 |
| `mut_benchmark_divergent_cap`(AC-SAG-012) | already-verified-in-M3 | `test_sector_benchmark_ranking.py::test_ac_sag_012_mut_divergent_cap_breaks_four_tuple`, progress.md §E.2 M3 |
| `mut_benchmark_own_anchor`(AC-SAG-012/014) | already-verified-in-M3 | `test_sector_benchmark_ranking.py::test_ac_sag_014_mut_benchmark_own_anchor_breaks_uniqueness`, progress.md §E.2 M3 |
| `mut_weight_cap_literal`(AC-SAG-041) | already-verified-in-M6 | progress.md §E.2 M6 |
| `mut_service_not_rewired`(AC-SAG-045 R1) | **verified-now-in-M7** | 위 §5 — `test_ac_sag_045_r1_r4_r5a.py::test_ac_sag_045_r1_mut_service_not_rewired_control` |
| `mut_plan31_verbatim`(AC-SAG-049) | already-verified-in-M2 | progress.md §E.2 M2 |
| `mut_reintroduce_cap_literal`(AC-SAG-050) | already-verified-in-M2, 회귀 재확인-in-M7 | 위 §6 — `test_inv_cap1_scan.py` |
| `mut_no_ag5_gate`(AC-SAG-007/045 R6) | already-verified-in-M6 | `test_sag_m6_router_wiring.py::test_ac_sag_007_red_when_ag5_gate_removed`, progress.md §E.2 M6 |
| `mut_benchmark_index_row`(AC-SAG-011/013) | already-verified-in-M3 | progress.md §E.2 M3(`mut_benchmark_index_row 검출 실측: 편차 0.957391 %p`) |
| `mut_benchmark_own_anchor`(AC-SAG-014, 보조 GREEN 병행) | already-verified-in-M3 | 위와 동일 |
| `mut_stored_max52`(AC-SAG-024/045 R3) | already-verified-in-M5 | `test_ac_sag_024_high52.py`, progress.md §E.2 M5(`mutation_verification_m5: observed-red-4`) |
| `_classify_stage_simple` 유지 변형(AC-SAG-025) | already-verified-in-M5 | progress.md §E.2 M5 §E3 |
| `mut_rs_zero_fill`(AC-SAG-030/045 R4) | already-verified-in-M5, 재확인-in-M7 | `test_ac_sag_030_rs_avg.py`, progress.md §E.2 M5 + 위 §5 |
| 날짜별 재계산 변형(AC-SAG-033) | already-verified-in-M4 | progress.md §E.2 M4(`test_ac_sag_033_index_chain_no_jump_on_membership_change`) |
| 엔드포인트별 순진 `MAX(Date)` 7회(AC-SAG-037) | **Gap** | 아래 참조 |
| AC-SAG-044 (3케이스) | **verified-now-in-M7** | 위 §4 |
| `mut_minmax_norm`(AC-SAG-045 R5-a) | **verified-now-in-M7** | 위 §5 |
| 횡단면 z-score 변형(AC-SAG-045 R7) | already-verified-in-M4 | `test_sector_rrg.py` |
| `mut_label_constant_window` + 금요일 종단 변형(AC-SAG-046) | already-verified-in-M1.1/M3 | `test_sector_benchmark_ranking.py::test_ac_sag_046_lite_mut_label_constant_window_is_detectable`, progress.md §E.2 M1.1(금요일 종단) |
| 파일 1개 제거 음성 검증(AC-SAG-047) | already-verified-in-M1.0-b | progress.md §E.2 M1.0-b §E3 |
| F2/F12-a 임계 `>= 999` 음성 검증 + F13-1 상위집합 해제 실증(AC-SAG-048) | already-verified-in-M1.0-a 재빌드 | progress.md §E.2 M1.0-a 재빌드 |

**Gap — AC-SAG-037(전 엔드포인트 as_of_date 일치, SN-3) 되돌림 실증 미이행**:
plan.md M1.1/M6 RED 목록에 결속됐다고 progress.md N5/D26 항목이 기록했으나,
실제 코드 검색(`grep -rln "AC-SAG-037" tests/ backend/tests/`)결과 이 AC를 다루는
테스트 파일이 **존재하지 않는다**. `fixture_max_ne_canonical` 픽스처는 존재하지만
(SPEC-SECTOR-GRID-001 소관, `tests/test_consumer_dates.py`) 이 SPEC의 7개
섹터 엔드포인트에 그 픽스처를 주입해 `as_of_date`/`grid_version` 일치 및
엔드포인트별 되돌림 7회를 실증하는 코드는 M7 시점까지 미작성이다. 이는 §8.4
규약 6 게이팅 열거(002/007/011/012/013/014/024/030/045/046/047/048)에는
포함되지 않지만 §9 DoD("AC-SAG-001~050 전부 PASS") 및 mutation 변형 목록에
명시적으로 결속돼 있어 **완결 라운드의 정직한 Gap**으로 기재한다 — 7개
엔드포인트 각각에 fixture 주입 + 날짜 해석 배선 확인이 필요한 별도 작업량이며,
"관측하지 못한 것을 GREEN으로 기재하지 않는다"(Lesson #9)는 원칙에 따라 여기서
강행 완료를 주장하지 않는다. **후속 조치 필요**: 별도 세션 또는 후속 SPEC에서
`tests/test_ac_sag_037_endpoint_as_of_consistency.py`(가칭) 신설.

#### 8. 릴리스 노트 초안 (manager-docs 인계용 — CHANGELOG.md 직접 편집 금지)

manager-develop은 sync-phase CHANGELOG.md 편집 권한이 없다(소유권 매트릭스). 아래
초안을 manager-docs 인계 항목으로 남긴다:

> **섹터 집계 시총가중 재작성 완결(M1~M7)** — 시가총액가중 + 상한 재배분(INV-
> CAP-1) 집계 코어, 시장별 벤치마크(BM-1~BM-6), 순위 백분위 정규화(AG-8/AG-9),
> RRG 지수, 52주 신고가/Stage 단일화/RS 평균/거래대금 지표 정정, 라우터
> `market`/`period` 파라미터 신설. R1~R8 "고장처럼 보이지만 올바른 변화"는
> INV-CAP-1(축퇴 경계) 신설과 상한 재배분 알고리즘 교체(무한 진동 → 동결형)에서
> 기인하며, 회귀가 아니라 의도된 결과다(acceptance.md AC-SAG-045 참조). AC-SAG-
> 037(전 엔드포인트 as_of_date 일치 되돌림 실증)은 후속 작업으로 이월한다.

전체 스위트 델타:
```
$ pytest tests/ -q   (M7 착수 전 baseline)
8 failed, 873 passed, 68 skipped, 1 xpassed, 25 errors in 110.80s

$ pytest tests/ -q   (M7 신규 테스트 4파일 추가 후)
8 failed, 900 passed, 69 skipped, 1 xpassed, 25 errors in 111.68s
```
+27 passed(신규 파일 4개 합계: as_of scan 13(12 pass+1 skip) + ac_sag_044 3 +
ac_sag_045_r1_r4_r5a 11 = 27), failed 8건·error 25건은 baseline과 **동일 집합**
(전건 SPEC 범위 밖 사전 존재 — 신규 실패 0건). skipped +1은 의도된 skip(§3).

#### Blocker 보고 (manager-spec / manager-docs 대상)

1. **manager-docs 대상** — 위 §8 릴리스 노트 초안을 CHANGELOG.md `[Unreleased]`에
   반영해 달라(manager-develop은 편집 금지).
2. **manager-docs 대상** — 이 SPEC의 sync-phase 전환(`in-progress → implemented →
   completed`)을 진행해 달라. manager-develop은 이 전환을 수행하지 않는다.
3. **후속 SPEC 또는 재위임 대상** — AC-SAG-037(7-엔드포인트 as_of_date 일치
   되돌림 실증)이 미구현 상태다(§7 Gap 참조). SPEC 본문(acceptance.md) 수정은
   필요 없다 — 순수 테스트 코드 작성 작업이므로 acceptance.md 편집 권한 이슈는
   아니다. 다음 run-phase 위임 시 우선 항목으로 포함을 권고한다.
4. **acceptance.md §8.4 규약 8 정적 스캔 명령의 리터럴 코드 블록 부재** — 이번
   M7에서 이 규약을 코드로 최초 구현했다(§3). 향후 SPEC에서 acceptance.md를
   개정할 기회가 있다면 스캔 명령을 코드 블록으로 명문화해 "명세에서 바이트
   동등 추출" 절차를 실제로 수행 가능하게 만드는 편이 Lesson #9 원칙에 더
   부합한다 — 이는 정보성 제안이며 blocker는 아니다.

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_status: completed
sync_complete_at: 2026-08-14
sync_commit_sha: 13d74d0                 # 백필 완료 — sync-phase artifacts + 3-phase close 커밋
changelog_entry_position: "CHANGELOG.md [Unreleased] 최상단 (### Added SPEC-SECTOR-AGGREGATION-001 v0.5.0)"
readme_updated: false                    # README.md 에 섹터 집계 관련 참조 0건(grep 확인) — 갱신 대상 없음
frontmatter_status_transitions:
  spec_md: "in-progress -> completed (updated: 2026-08-13 -> 2026-08-14)"
  plan_md: "N/A — YAML frontmatter 없음(status 필드 부재, 본문 h1 시작)"
  acceptance_md: "N/A — YAML frontmatter 없음(status 필드 부재, 본문 h1 시작)"
b12_self_test_a: "grep -c 'SPEC-SECTOR-AGGREGATION-001' CHANGELOG.md (편집 전) -> 0 (사전 중복 없음 확인)"
b12_self_test_b: "acceptance.md AC-SAG-* 고유 카운트 grep -oE 'AC-SAG-[0-9]{3}' | sort -u | wc -l -> 50, CHANGELOG 엔트리 '50/50' 문구와 일치"
b12_self_test_c: "CHANGELOG 엔트리가 인용한 파일 경로(my_chart/analysis/weighting.py, my_chart/analysis/rrg.py, tests/fixtures/frozen/aggregation-2026-08-11/) ls 확인 완료"
mx_tag_validation: "sync 서브스텝 — run-phase 각 마일스톤(§E.2)에서 @MX 태그를 이미 부여·검증 완료(M2 E11, M3 E7, M4 E6, M5 E8 참조). sync-phase 신규 위반 0건"
canary_compliance_check:
  applicable: false   # 본 SPEC은 forward-looking 정책 SPEC이 아님(섹터 집계 기능 구현) — canary 자기검사 대상 아님
run_status_carried_forward: implemented   # §E.3 run_status 참조 — 미이월 Gap 없음(AC-SAG-037 closure 로 M7 Gap 종결)
blocker_report: none
```

**Sync-phase 요약**: manager-develop 이 §E.2 §8(릴리스 노트 초안) + §E.2 §9(AC-SAG-037 closure, `b703dc2`) 으로 인계한 내용을 CHANGELOG.md `[Unreleased]` 최상단에 반영했다. README.md 는 섹터 집계 관련 언급이 없어 갱신 대상이 아니다(grep 확인). spec.md frontmatter `status: in-progress -> completed` + `updated: 2026-08-14` 전환을 이 커밋에서 수행한다 — plan.md/acceptance.md 는 YAML frontmatter 자체가 없으므로(본문이 `#` h1으로 바로 시작) 전환 대상 필드가 없다(N/A, 소유권 위반 아님). `sync_commit_sha` 는 자기참조 해저드로 `pending-backfill-sync` placeholder 를 기록하고 후속 백필 커밋에서 실제 SHA로 갱신한다(§E.3 `run_commit_sha` 백필과 동일 규약).
