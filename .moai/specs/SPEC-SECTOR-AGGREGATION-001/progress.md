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

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: blocked                # M1.1 완료. M2 는 AC-SAG-002 blocker 로 미착수
milestone_completed: M1.1
run_commit_sha: 7305e2e            # M1.1 구현 커밋 (§E.2 증거 커밋은 633d6b4)
coverage_m11: "aggregate_types 94% · envelope 99% · sector_ranking_service 91% (TOTAL 95%, 임계 85%)"
prior_milestone_commits: "adb1f25 (M1.0-a) · b839cee (M1.0-a §E.3) · 6f00ba5 (M1.0-b/c) · 7b5fc45 (M1.0-b/c §E.3) · 7305e2e (M1.1)"
ac_gate: AC-SAG-047
ac_pass_count: 6                   # 048 + 047 + 036 + 038 + 043(부분) + 008
ac_fail_count: 0                   # M2 는 착수 자체를 하지 않았다(FAIL 이 아니라 미실행)
ac_blocked: "없음 — v0.4.2에서 해소 (D16: F12 신설 + AC-SAG-002 재작성 / D17: §3.1 동결형 교체 + AC-SAG-049 신설). [v0.5.0] 추가 정정 — N1(AC-SAG-041 cap_eff) · D22(AC-SAG-010) · D20(045 R1) · D23(AC-SAG-015) · D21(045 R5-b) · N4(AC-SAG-012) · N3(AC-SAG-016) · N7(AC-SAG-044) · D24(AC-SAG-013) · N2(F7 규약 Y) · D25(F4·F8 폐지) · R-C1~R-C8(F13 신설) · D29(합성 바) · N5/D26(고아 AC)"
blocker_open: false               # [v0.4.2 2026-08-13] manager-spec 재위임 완료. SPEC 층 해소 — 다음 행동은 M1.0-a 재빌드
blocker_owner: manager-develop    # 소유권 반환. acceptance.md 본문 수정 완료(v0.4.2)
blocker_resolution_version: "0.5.0"   # 0.4.2에서 M2 blocker 2건(D16·D17) 해소, 0.5.0에서 전수 스윕 결함 14건 일괄 해소
spec_layer_deltas: "F12 신설(§8.2) · AC-SAG-002 절 2·3 집합 동등 재작성 · AC-SAG-045 R1 대조 mut_service_not_rewired 교체 · plan.md §3.1 동결형 + 종료 증명 · AC-SAG-001 A/B 분리 · AC-SAG-049 신설 · AC-SAG-003 순수 합성 교체 · AC-SAG-005 정의 확정 · AC-SAG-007/043 M6 의존 명시 · §8.4 규약 10 신설"
wip_branch: "wip/SPEC-SECTOR-AGGREGATION-001-M2 @ 83cb847 (main 미머지)"
capture_via_http_response: true    # TestClient 경유 response_model 직렬화. model_dump_json() 아님
capture_as_of: "2026-08-11"        # 캡처 스크립트가 응답 date 와 동등성 단언
capture_fixture: "tests/fixtures/frozen/aggregation-2026-08-11"
capture_git_sha: b839cee           # 캡처 시점 (코드 변경 0줄 상태)
baseline_files: 3                  # ranking-current.json · stage-overview.json · MANIFEST.md
baseline_sector_count: 18          # >= 10 (AC-SAG-047)
baseline_excess_returns_degenerate: false   # 54/54 (섹터,기간) 쌍이 returns 와 상이. max gap 16.1662
d12_forbidden_string_count: 0      # sector_excess_return · total_count 양 파일 0건
new_warnings_or_lints_introduced: 0
full_suite_delta: "+14 passed (688 → 702, M1.1) / failed 8 (전건 pre-existing, 동일 집합) / errors 25 (pre-existing)"
date_axis_fixture_touched: false   # tests/fixtures/frozen/weekly-2026-08-12/ 미변경
aggregation_fixture_touched: false # tests/fixtures/frozen/aggregation-2026-08-11/ 미변경
production_code_touched: true      # M1.1 — 응답 스키마 추가 전용 확장 + 서비스 봉투 배선. 집계 로직 미변경
live_db_mutated: false             # /api/db/update 미실행
negative_verification: observed-red-1        # stage-overview.json 임시 이동 → 3 failed + 11 errors 관측. 복원 후 40 passed (E5)
mutation_verification_m2: not-run  # mut_equal_weight 미실증 — 재빌드된 F12 픽스처 위에서 AC-SAG-002 가 검출력을 회복한 뒤 수행(Gap 유지)
point_of_no_return_crossed: false  # **M2 미커밋 — 재캡처 경로 여전히 열려 있다**
fixture_rebuild_required: true     # [v0.4.2 D16 · v0.5.0 F13 확장] 현 픽스처는 F12 미충족(AG-5 통과 18섹터 중 n>10 이 게임 1개). 재빌드 목표 = **현행 145종목 상위집합**(F13-1 [HARD]) + 유효 시총 n >= 15 섹터 14개 이상(F13-2) + F12-b·c >= 9 빌드 목표(F13-3) + 패션 5종목/유효 시총 3 보존(F13-4) + 양 시장 비공백(F13-5) + 합성 바 재라벨링 재현(F13-6). F7은 규약 Y로 재계수(빌더 변경)
golden_baseline_discarded: true    # [v0.4.2 D16] b839cee 캡처분은 F12 미충족 픽스처 위에서 떠졌으므로 폐기 — M1.0-b 재수행
next_gate: "M1.0-a 재빌드(F12 + F13 · 상위집합 + F7 규약 Y) → AC-SAG-048 PASS(F1~F13) → M1.0-b 재캡처 → M1.0-c(AC-SAG-047 PASS) → M2"
deferred_to_m6: "AC-SAG-007 전체 · AC-SAG-043 파생 구조 절 — M6 산출물 의존(D19). M2~M5 미실행은 Gap 이 아니다"
total_run_phase_files: 18          # 기존 11 + M1.1 7 (신설 3 · 수정 4)
m1_to_mN_commit_strategy: "마일스톤별 개별 커밋 후 main 직푸시 (Hybrid Trunk 1인 OSS)"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
