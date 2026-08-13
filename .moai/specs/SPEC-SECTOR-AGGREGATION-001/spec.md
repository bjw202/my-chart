---
id: SPEC-SECTOR-AGGREGATION-001
title: "섹터 집계 계층 — 시총가중·벤치마크·순위·RRG 지수·응답 공통 스키마"
version: "0.5.0"
status: in-progress
created: 2026-08-12
updated: 2026-08-13
author: manager-spec
priority: P0
phase: "sector-ux v1"
module: "my_chart/analysis, backend/services, backend/schemas, backend/routers"
lifecycle: spec-anchored
tags: "sector, aggregation, benchmark, rrg, ranking, api-contract"
depends_on: [SPEC-SECTOR-GRID-001]
related_specs: [SPEC-SECTOR-GRID-001, SPEC-SECTOR-UX-001]
tier: L
---

# SPEC-SECTOR-AGGREGATION-001: 섹터 집계 계층 — 시총가중·벤치마크·순위·RRG 지수·응답 공통 스키마

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 0.1.0 | 2026-08-12 | manager-spec | 초기 SPEC. `docs/sector-ux/01-data-contract.md` §2(지표 사전)·§5(집계)·§6(벤치마크)·§8(화면별 계약)·§9(결측 정책)을 구현 계약으로 전환. `02-screen-flow.md` §12.3 서버 선행 조건 전부 포함. Lesson #3/#4/#5/#7 반영. |
| 0.2.0 | 2026-08-12 | manager-spec | plan-audit 0.83 FAIL(L, thresh 0.85) 결함 델타 반영. **사용자 결정 4건 수용**: O-A1(RS-Ratio **롤링 정규화 미적용** — 100이 문자 그대로 벤치마크. 표준 JdK RRG와의 발산 및 강세장 사분면 편중이 정상임을 명시), O-A3(상수 주식수 가정 한계를 `warnings[]`에 명시 + **"현재주가" = daily 최신 `Close`**. 이벤트 감지는 과설계로 미구현), O-A4(**거래대금 창 = 기간 토글 연동** `[anchor(t,N), t]` + `trading_value_window_days` 동반), O-A6(**지표별 `coverage.*` + 최상위 최소값** 병행 — AG-7 임계는 최소값에 적용). **AC 반증 가능성 복구**: AC-SAG-037(라이브 `naive MAX == canonical`이라 SN-3 반증 불가 → `fixture_max_ne_canonical` + 엔드포인트별 되돌림 7회), AC-SAG-025(동일성 단독 단언은 양쪽이 모두 구 분류기여도 통과 → 주봉 Weinstein 기대 stage 리터럴 3케이스 + `_classify_stage_simple` 대조 + rename 내성 행동 단언), AC-SAG-016(`is not 0.0` float 아이덴티티 비교 삭제 — 결함 미검출 + `SyntaxWarning`), AC-SAG-045(R2 `10<=k<=24`는 29섹터의 34~83%로 무게이팅 + AC-SAG-013 중복 → **삭제**; R4/R5는 비교 대상 미보존으로 실행 불가였으므로 **골든 baseline 캡처를 plan.md M1.0 선행 작업으로 신설**; R7 "그런 테스트가 없음을 확인"을 행동 단언 + grep 2종으로 재작성). **§8 프로즌 픽스처 규약 신설** — 주 1회+ `/api/db/update`로 게이팅 AC가 코드 변경 없이 붉어지는 문제. **O-A8 신설** — ①의 O-G2(미완성 주 바와 기간 계산의 정합)를 인수, M3 차단 항목. **O-A7에 ③ 의존 교차 링크** 추가. |
| 0.2.1 | 2026-08-12 | manager-spec | plan-audit iteration 2 **PASS 0.88**(L, thresh 0.85; MUST-PASS 전항 통과, 단조 개선) 이후 잔여 결함 정리. **(D5) `AC-SAG-011`이 §8 프로즌 픽스처 규약 밖에 있었다** — 1W 벤치마크 실측값(KOSPI +1.03% / KOSDAQ +7.54% / All +1.88%, ±0.5%p)을 게이팅 기대값으로 못 박으면서 §8의 게이팅 표에도, §8.5 "순수 합성 · 해당 없음" 열거에도 없었다. `/api/db/update` 1회로 코드 변경 없이 붉어지는, §8이 막으려는 바로 그 형태다. **게이팅 표에 등재**하고 AC 본문에 프로즌 한정을 명시했다. `AC-SAG-044`(정적 스캔 + mutation 대조, 라이브 값 없음)도 어느 열거에도 없었으므로 **N/A로 명시 등재**했다 — 무해하지만 같은 누락 경로다. **§8.6 열거 완결성 규칙 신설**: `AC-SAG-001`~`045` 전부가 (게이팅 표) 또는 (순수 합성 열거) 중 정확히 한 곳에 나타나야 하며, 신규 AC는 반드시 한쪽에 등재한다 — 어느 쪽에도 없는 AC가 규약 밖에 방치되는 것이 011/044의 누락 경로였다. **(D6) 골든 baseline 캡처 문구의 잘못된 절 참조 정정** — `acceptance.md:416`이 프로즌 규약을 **§9**로 가리켰으나 §9는 품질 게이트이고 프로즌 규약은 **§8**이다(`plan.md:55`는 이미 §8로 정확했다). |
| 0.3.0 | 2026-08-13 | manager-spec | **O-A8 해소 — 선택지 (a) 채택(미완성 주 포함)** + 그 귀결인 **창 일수 응답 계약 신설**. (1) `as_of` = `latest`(미완성 주 포함, `_get_latest_valid_date()` 현행 동작), 앵커 = `history_grid`(완성 바만). 근거: 사용자가 이 화면을 실시간으로 보므로 진행 중인 주의 움직임이 반영되어야 한다. (2) 그 결과 **창은 라벨보다 짧아지는 게 아니라 길어진다** — 실측 프로즌(as_of 2026-08-11 화) 1W=11일/1M=32일/3M=95일(+4), 라이브(as_of 2026-08-12 수) 12/33/96일(+5). 초과분은 요일 의존이며 세 기간에 **동일**하다(7·28·91이 모두 7의 배수). (3) **REQ-SAG-043 신설 + AC-SAG-046 신설** — `return_window_days: {1w,1m,3m}`를 응답에 실어 ③이 "1W (11일치)"로 표기할 수 있게 한다(O-A4의 `trading_value_window_days` 선례를 수익률에 확장). (4) REQ-SAG-012에 **BM-6 보존 조건 명시** — 섹터·벤치마크가 **같은 `anchor(t, N)` 호출**에서 앵커를 얻어야 하며, 창 길이 ≠ N은 오류가 아니라 기대되는 상태다. (5) REQ-SAG-021에 미완성 주 시 baseline 간격이 28일 초과임을 명시(AC-SAG-023의 `>= 28`이 이미 수용). AC 45 → 46. |
| 0.4.0 | 2026-08-13 | manager-spec | **plan-audit iteration 1 FAIL 0.78**(L, thresh 0.85; MUST-PASS 전항 통과, Testability 0.55가 원인) 결함 D1~D9 해소. **(D1 BLOCKING) 프로즌 픽스처가 게이팅 기대값 8개 중 7개를 호스팅할 수 없었다** — `weekly-2026-08-12`는 ①이 **날짜 축** 재현용으로 만든 41종목 스냅샷이라 AG-5(최소 5종목)를 통과하는 섹터가 **게임 하나뿐**이고 헬스케어·방산·디스플레이는 아예 없다(실측: `stock_meta` 33행 = 게임 32 / 반도체 1, registry 41행 / 8섹터). 해소: **횡단면 집계용 제2 프로즌 픽스처를 신설 명세**(§8.2 F1~F11 — 값이 아니라 **구조** 요건)하고, 그 위의 게이팅 AC를 **리터럴이 아니라 파생 규칙**으로 재작성했다(§8.3). 파생 규칙은 픽스처 재빌드 시 acceptance.md 본문 수정이 불필요하므로 run-phase 소유권 위반(manager-develop의 acceptance.md 편집 금지)을 구조적으로 제거한다. **(D2 BLOCKING) 설계결정 3이 실증적으로 거짓이었다** — `as_of_is_partial_week == false ⇒ 창 == N`은 성립하지 않는다(실측 `as_of=2026-08-17` → partial `False`인데 창은 11/32/95). `as_of`는 날짜 축을 자르지 않기 때문이다. 참 조건은 **"최신 대표 바가 금요일(완성 주 대표 바)"**이며, 이에 맞춰 설계결정 3을 정정하고 AC-SAG-046의 마감 주 대조를 `as_of` override가 아닌 **금요일 종단 픽스처 변형**으로 재작성했다(실증: `Date <= '2026-08-07'` 절단본에서 partial `False` + 창 정확히 7/28/91). **(D3 BLOCKING) `as_of` 리터럴 미기재** — 사용자 결정으로 **`as_of = 2026-08-11` 고정**(기존 프로즌 유지, AC-SAG-046의 검증된 리터럴 4개 불변). 게이팅 테스트의 `as_of` 기본값(`None` → today) 사용을 금지하고 정적 스캔으로 강제한다(§8 규약 8). **(D5 BLOCKING) R1/R4/R5** — R1을 R4/R5와 동일하게 골든 baseline에 결속, R5의 `최상위>=95 / 최하위<=5`를 **등간격 파생 단언**(순위 백분위의 정의적 성질, min-max에서 불성립)으로 대체해 N 의존 우연을 제거. **(D4) AC-SAG-047 신설** — 골든 baseline 캡처 완결성의 **기계적 M1 종료 게이트**. 캡처 목록도 정정했다(`/sectors/ranking`은 무파라미터이나 응답이 1W/1M/3M을 **모두** 싣고 있으므로 기간별 3파일이 아니라 **단일 파일**로 캡처한다). **(D6) AC-SAG-014**를 출력 동등에서 **구조 단언**(공유 `anchor()` 호출 횟수·인자)으로 전환 — 실증으로 출력 동등의 검출력이 0임을 확인했다(`latest=2026-08-11`·`history 마지막=2026-08-07` 양쪽에서 `anchor(·,7/28/91)`이 **동일하게** 07-31/07-10/05-08). **(D7) 되돌림 변형 신설** — 002/011/013/014/045 R3·R4·R5·R6에 명명된 변형 추가 + **관측된 RED 증거를 요구하는 DoD 항목** 신설(Lesson #9: 작성 여부가 아니라 되돌림 RED 관측이 판정 기준). **(D8) GEARS 라벨 정정** REQ-SAG-029 → Unwanted Behavior, REQ-SAG-032 → Where. **(D9) AC-SAG-007** 라이브 구성수 인용을 픽스처 구조 요건(F3)으로 재기술하고 게이팅 표로 이동. AC 46 → **47**. |
| 0.4.1 | 2026-08-13 | manager-spec | **plan-audit iteration 2 PASS-WITH-DEBT 0.845**(L, thresh 0.85; MUST-PASS 전항 통과, Testability +0.17). iteration 1 결함 D2/D3/D5/D6/D7/D8/D9 RESOLVED, D1/D4 PARTIALLY-RESOLVED. **신규 결함 D10~D15를 단일 배치로 해소한다.** **(D10 CRITICAL) AC-SAG-013의 파생 항등식이 올바른 구현에서 거짓이었다** — v0.4.0은 초과수익률의 시총가중 평균이 `0.0 ± 0.05%p`이며 *"정의상"* 성립한다고 적었으나, **상한 재배분은 그룹핑 계층을 넘어 합성되지 않는다**(섹터는 섹터 내부에, 벤치마크는 유니버스 전체에 상한을 적용한다). 실측(2026-08-13, plan.md §3.1을 두 계층에 그대로 구현): `cap=0.10`에서 가중평균 `+1.496127 %p`(허용오차의 30배) / 상한 없음에서 `-0.000000 %p`. 게다가 픽스처 요건 **F4가 상한 구속을 강제**하므로 이 단언은 **요건상 반드시 실패**했다. 추가 실측으로 **감사가 제시한 (a)"무상한 항등식" 대안도 채택 불가**임을 확인했다 — AG-5/AG-4 제외 섹터가 있으면 상한을 꺼도 0이 아니다(제외 2섹터에서 `+0.035526 %p`)이며 F3/F6이 그 제외를 강제한다. 해소: 주 단언을 **참조 구현 대조**(섹터별 `S_s^ref − B^ref` 일치 + `ω_s^ref` 가중 잔차 일치)로 교체하고 **`0` 리터럴을 삭제**했다. 상한을 끈 완전 분할에서의 `0` 항등식은 **참조 측 자기검사(비게이팅)** 로만 남겼다. `mut_benchmark_index_row`에서 편차 `0.957391 %p`(허용 `1e-9`)로 RED 검출 실측 확인. **(D12 CRITICAL) AC-SAG-047이 존재하지 않는 응답 키를 단언했다** — `sector_excess_return_1w/1m/3m`는 내부 dataclass `sector_metrics.SectorRank`의 필드명이며 **직렬화되지 않고**(실측: 캡처 JSON에 해당 문자열 0건), 실제 키는 `sectors[i].excess_returns.{w1,m1,m3}`이다(`backend/schemas/sector.py:24-37`). `total_count`도 존재하지 않으며 실제 키는 `distribution.total`이다(`backend/schemas/stage.py:8-15`). 정상 캡처에서 게이트가 RED가 되는 상태였다. 실측 직렬화 결과로 전 키를 정정하고 컨테이너명(`sectors`)을 명시했으며, **동일 결함 재도입 방지용 정적 확인**(`sector_excess_return` 문자열 0건)을 추가했다. 같은 결함이 파급된 **AC-SAG-027 · REQ-SAG-024 · plan.md M1.0-b 주석**도 함께 정정했다. **(D11 MAJOR) AC-SAG-014의 `anchor()` 호출 횟수 `== 1` 단언이 SPEC이 지시한 구조에서 스스로 RED가 됐다** — plan.md D1/D2의 공용 함수 구조에서는 섹터 N회 + 벤치마크 1회로 `N+1`회가 정상이며, 어느 REQ도 앵커 호이스팅을 요구하지 않는다. 주 단언을 **인자 `t`(앵커 기준일)의 유일성**으로 옮기고 호출 횟수 제약을 삭제했다 — `mut_benchmark_own_anchor`는 `t`를 `2026-08-07`로 바꾸므로 검출력이 보존된다. 반환 객체 아이덴티티는 두 `t`가 같은 `GridBar`를 반환하므로 **비게이팅 보조**로 강등했다. **(D13 MAJOR) 참조 구현 계약이 AG-3/AG-4/AG-7에 대해 미규정이었다** — 같은 픽스처가 F5/F6으로 그 케이스를 의도적으로 주입하므로 두 가지 defensible한 참조 동작이 갈릴 수 있었다. §8.3에 **제외·null 처리 계약**(AG-3/AG-4/AG-5/AG-7 + 대조 집합 제한 + null 섹터 집합 동등 단언)을 신설해 허용 동작을 하나로 못 박았다. **(D14 MINOR) F1~F11 검증이 캡처 뒤에 있었다** — **AC-SAG-048 신설**로 M1.0-a **종료 조건**으로 끌어올렸다(MANIFEST 기록값과 검사 산출 실측값의 일치까지 요구). **(D15 MINOR) AC-SAG-014·045 R5-a에 픽스처 지정과 `as_of` 고정 누락**(규약 1·8 위반) — 태그와 Given을 정정했다. **감사 판정 기록 — 비가역 경계는 M1.0-b가 아니라 M2다**(§8.5 신설): M1.0-c까지는 코드가 그대로이므로 재캡처 경로가 남아 있고, 이것이 D12/D14를 회복 가능한 결함으로 만든 근거다. 강제 순서 `M1.0-a → AC-SAG-048 → M1.0-b → M1.0-c(AC-SAG-047) → M2`. AC 47 → **48**. |
| 0.4.2 | 2026-08-13 | manager-spec | **run-phase M2 blocker 2건 해소 (D16 · D17) + 파생 3건 (D18 · D19 · AC-SAG-049 신설).** run-phase가 M1.0-a~M1.1을 완료하고 **M2 착수 직전에 커밋 없이 blocker를 반환**했으며(`point_of_no_return_crossed: false`), 비가역 경계가 M2라는 §8.5 판정 덕분에 픽스처 재빌드·baseline 재캡처 경로가 살아 있었다. **(D16 CRITICAL) AC-SAG-002의 절 2건이 지정 픽스처 위에서 산술적으로 성립 불가였다** — `cap = 0.10`에서 `n <= 10`이면 `cap_eff = 1/n`이라 `n × cap_eff = 1`이 되어 `max(w) <= cap_eff ∧ Σw = 1`의 해가 **균등 하나뿐**이다. 즉 **구성종목 10개 이하 섹터에서 시총가중은 등가중과 완전히 동일**하다(실측 차 `0.0000%p`, 부동소수 오차조차 0). 픽스처는 F4(최상위 원비중 > 10% 섹터 >= 3)를 **18/18 섹터에서 충족**하고 AC-SAG-048도 PASS였으나 AG-5 통과 18섹터 중 `n > 10`이 게임(32) 하나뿐이라, `|시총가중 − 등가중| >= 0.5%p` 섹터 = **1개**(요구 >= 3) / 평균 절대 순위 이동 = **0.3750**(요구 >= 1.0)으로 게이팅 AC가 **완전한 무게이팅**이 됐다. **F4가 구성종목 수를 규정하지 않으므로 이 효과를 함의하지 않는다** — "구조 요건이 검출력을 함의한다"는 전제가 거짓임이 드러난 사례다. 해소: **픽스처 요건 F12 신설**(F12-a 유효 시총 `n >= 11` ∧ 최상위 원비중 > 0.10인 섹터 >= 12개 / F12-b 1M `|Δ| >= 0.5%p` 섹터 >= 3개 + 섹터명 집합 MANIFEST 기록 / F12-c 1M 순위 이동 섹터 >= 5개 + 집합 기록) — **효과 자체를 요건으로 승격**해 같은 실패가 재발할 수 없게 했다. AC-SAG-002의 두 절을 **MANIFEST 집합 동등**으로 재작성하고, *"평균 절대 순위 이동 >= 1.0"* 은 **삭제**했다(실측: 3개 주봉 바 × 12섹터 `n=15`에서 0.500/0.750/0.500, 14섹터 `n=20`에서도 0.778/1.333/0.889로 임계를 가로질러 **어떤 실용적 픽스처 크기에서도 보장 불가**한 데이터 의존 임계였다). AC-SAG-045 R1의 되돌림 대조를 `mut_equal_weight` → **`mut_service_not_rewired`** 로 교체하고, `mut_equal_weight`가 R1의 판별자가 **아님**을 본문에 명시했다(가중 전환 단독 기여 0.500~1.333 < 임계 2.5). **§8.4 규약 10 신설** — 대조 단언의 검출력을 실측으로 확인한다. **(D17 CRITICAL) plan.md §3.1의 verbatim 알고리즘이 종료하지 않았다** — 상한에 걸린 종목을 `cap_eff`로 고정하지만 다음 반복에서 `over` 조건(`> cap_eff + 1e-12`)에 걸리지 않아 `rest`로 분류되어 **재배분을 다시 받고**, 진동하다 20회 상한에서 **상한 초과 상태로 종료**한다. 실측(seed 20260813, 4,000 케이스): **3,183건(79.6%)이 상한 초과**, 최악 `n=6`에서 `cap_eff=0.166667` 대비 `max(w)=0.211925`(**+27.2%**). AC-SAG-001의 "최대값 <= cap_eff"와 "5회 이하 수렴"을 **동시에** 위반했다. 해소: §3.1을 **동결형**(상한 종목을 재배분 집합에서 영구 제외)으로 교체하고 **종료 증명**(매 회 `frozen`이 진부분집합으로 엄격 증가 → `<= min(n, 20)`회 종료)을 명시했다. 고정점은 불변임을 실측 확인 — verbatim 2,000회 결과와 최대 편차 `6.696e-12`, 닫힌 해와 `3.053e-16`. 반복 횟수 실측 최악은 **6회**(4,000 케이스) / **7회**(60,000 케이스, `n <= 60`)이므로 *"섹터당 <= 5회"* 임계는 **폐기**하고 구조적 종료 계약으로 대체했다. AC-SAG-001의 비례 배분 절(`w[1]/w[3] == 2.0`)은 지정 입력 `[70,10,10,5,5]`에서 **어떤 인덱싱 규약으로도 성립 불가**였으므로(해가 균등뿐 → 모든 비율 1.0), 축퇴 케이스(A)와 `n >= 11` 비례 케이스(B, `[1000,15,10×13]` → `w[1]/w[2] == 1.5`)로 분리했다. **AC-SAG-049 신설** — 시드 고정 무작위 스윕으로 상한·종료·정규화 불변식 + §3.1 고정점 등가 + 닫힌 해 대조를 검증한다(대조 변형 `mut_plan31_verbatim`). **(D17 파생) AC-SAG-003**이 라이브 반도체(삼성전자)를 인용하며 `capped_weight: 0.10`을 적었으나 픽스처 반도체는 6종목이라 `cap_eff = 0.1667`로 **거짓**이었고 §8.4 규약 5의 "순수 합성" 분류와도 어긋났다 — 12종목 순수 합성 입력(`[600, 40×11]`)으로 교체하고 6종목 축퇴 대조를 추가했다. **(D18) AC-SAG-005의 `cap_coverage_ratio` 정의가 모호했다** — `유효시총합 / 전체시총합`은 NULL 종목의 시총을 합산할 수 없어 분자와 분모가 항상 같아지는 **항진명제**였고, 본 AC 시나리오에서는 두 해석이 모두 1.0을 내어 모호성이 **무증상**이었다. `Σ market_cap(유효 시총 ∧ 기간 수익률 non-null) / Σ market_cap(유효 시총 종목)`(기간별 최솟값)으로 확정하고, 유효 시총 종목 1개의 수익률만 NULL로 바꾸는 **판별 대조 절**을 추가했다. **(D19) M6 의존 절의 평가 시점 명시** — AC-SAG-007 전체(`market` 파라미터 전제)와 AC-SAG-043의 파생 구조 절(`by_sector` · 상세 축약 리스트)은 M6 산출물에 의존하므로 M2~M5 구간의 미실행이 Gap이 아니라 **설계상 지연**임을 본문·DoD·§8.4 규약 6에 명시하고 `deferred-to-M6` 기재를 요구했다. AC 48 → **49**. |

| 0.5.0 | 2026-08-13 | manager-spec | **AC 도달가능성 전수 스윕 결과의 일괄 정정 — `cap_eff` 축퇴 결함 계열의 구조적 종결.** plan-audit iteration 3이 **FAIL 0.81 + STOP 신호**(iteration 2의 0.845 대비 회귀 — 감사 심도 증가에 기인)를 반환했고, 사용자 결정에 따라 4차 감사 대신 **49개 AC 전수 도달가능성 스윕 후 단일 배치 정정**을 수행했다. 스윕과 본 정정의 실측은 전부 **독립 참조 구현**(프로덕션 모듈 미import)으로 재빌드 구성을 2개 선정 전략 × 3개 주봉 바로 시뮬레이션해 산출했다. **(1) `cap_eff` 축퇴 계열의 구조적 종결 [N1 · 최우선]** — 같은 뿌리의 결함이 AC-SAG-002(D16, run-phase M2 차단) / 003(D17) / 010(D22) / 041(N1) **네 곳에서 따로** 적발됐고 매번 개별 AC만 고쳐 왔다. **acceptance.md §0 `INV-CAP-1` 신설** — 세 명제(① 상한 적용 종목의 가중치는 `cap_eff(n) = max(0.10, 1/n)`이지 `weight_cap`이 아니다 ② `n <= 10`이면 해가 균등 하나뿐이라 시총가중 ≡ 등가중 ③ `effective_n <= n`이며 축퇴 구간에서 `== n`)와 **작성 규약**을 한 곳에 못 박고 관련 AC 11개 + F12-a를 전수 결속했다. **AC-SAG-050 신설** — 규약 위반을 코드·SPEC 본문 양쪽에서 **정적 스캔으로 기계 집행**한다(대조 변형 `mut_reintroduce_cap_literal`). 다섯 번째 사례가 작성되면 CI에서 즉시 붉어진다. 이 스캔이 작성 중 실제로 1건을 검출했다(AC-SAG-003의 `capped_weight: 0.10` — 값은 옳았으나 규약 위반). **(2) 도달 불가 임계 5건 정정** — **AC-SAG-041**(N1) `weight_in_sector == 0.10` → `== cap_eff(n)` + 소형 섹터 축퇴 대조(실측 `n=5` → `0.200000`, `n=6` → `0.166667`. 재빌드는 F3/F6 요건상 그런 섹터를 **4개 의도 포함**한다). **AC-SAG-010**(D22) 라이브 반도체 `effective_n 24.3 ± 1.0` → 순수 합성 `[3000,100×24]`에서 `22.8571428571` 유도 + 5/6종목 축퇴 대조(밴드 `[23.3,25.3]`은 `n >= 24`를 요구하나 재빌드 목표는 `n=15`, 실측 `13.4214`). **AC-SAG-045 R1**(D20) 평균 절대 순위 이동 `>= 2.5` → **순위 이동 섹터 집합의 크기 `>= 5`**(실측 평균 이동은 6/6 구성에서 `0.82~2.35`로 전부 미달. 집합 크기는 `15~23`으로 여유 3.0배이며 `mut_service_not_rewired`에서 **구조적으로 공집합**이 된다). **AC-SAG-015**(D23) 정합성 대조를 비게이팅 스모크로 강등 — 인용 리터럴 `−0.10/−0.15%p`는 **부호부터 틀렸고**(재측정 `+0.2695/+0.5035%p`, KOSDAQ는 라이브에서 이미 허용오차 초과), 2,546종목 지수를 부분집합이 재현할 수 없으므로 "경고 없이 통과"는 구조적 불가다. **AC-SAG-045 R5-b**(D21) 표준편차 증가 부등식을 비게이팅으로 강등(26섹터 구성에서는 6/6 상승이나 12섹터 구성에서 하락 관측 — 구성 의존). **(3) 검출력 없는 단언 3건 보강** — **AC-SAG-012**(N4)는 plan.md §3.2가 *"타입 수준에서 보장한다"* 고 명시한 성질을 mock 인자 비교로 단언해 **항진명제**였다. 변형 2종(`mut_benchmark_divergent_cap` / `mut_benchmark_own_anchor`) 대조를 주 단언으로 올리고 mock 절을 비게이팅 가드로 강등, 게이팅으로 **승격**했다. **AC-SAG-016**(N3) 정적 스캔이 **산문에 매치**돼 현행 트리에서 4건(전부 docstring/f-string)이 걸렸다 — GREEN을 만들려면 무관한 docstring을 고쳐야 했다. **AST 스캔**으로 교체(실측 0건). **AC-SAG-044**(N7) `grep -c hasattr`에 수치 목표가 없어 게이팅하지 않았다 — 현행 15건이 **전부 단일 함수**(`:195-218`)에 있으므로 기대값 **0**을 명시했다. **AC-SAG-013**(D24) 부호 분산 `0 < k < N`을 비게이팅으로 강등하고(실측 `k`는 시장 상황에 종속되며 어느 요건도 규정하지 않는다) *"모두 같은 부호는 불가"* 선언과 *"모두 같은 부호면 경고"* 요구의 **자기모순을 해소**했다. **(4) F7 계수 규약 확정 [N2]** — 빌더(`build_fixture.py:481` `(max52 or 0.0)`)와 AC-024 본문이 **모순되는 NULL `MAX52` 규약**을 써서 같은 픽스처에서 F7이 **35 vs 15**로 갈렸다(차이 20 = NULL `MAX52` 종목 수). **규약 Y**(NULL 종목을 신·구 양쪽 분모에서 제외)로 확정하고 AC-024 / 045 R3 / F7 / MANIFEST 의미를 정렬했다. **빌더 변경이 필요하므로 run-phase 작업 지시로 명기**했다. **(5) F 요건 공허성 해소** — 소비 AC가 없어 빌드만 제약하던 **F4 · F8을 폐지**하고(F4는 현행 픽스처가 18/18 충족하면서도 AC-SAG-002를 무게이팅으로 만든 당사자다), **F5-a / F6 / F10의 소비 AC를 재결속**했다(F5-a·F6 → AC-SAG-013의 null 섹터 집합 동등 절 / F10 → 002·011·013의 `market_cap` 원천). **(6) F13 재빌드 구성 계약 신설** — 스윕의 **R-C1~R-C8을 6개 기계 검사 조건으로 통합**했다. 핵심은 **F13-1 상위집합**이다: 신규 시총순 선정만으로 재빌드하면 F7 divergent 15 → **2**, F5-b 10섹터 → **3**, F5-a 7 → **0**, F6 소멸로 **네 요건이 동시에 깨진다**(전부 시총 하위권 종목이 담당하기 때문). 현행 픽스처 145종목의 **전량 보존**이 유일한 충족 경로다. F13-2(대형 섹터 `>= 14`) / F13-3(F12-b·c 빌드 목표 `>= 9` — R-C1의 `6 vs 5` 재발 방지) / F13-4(패션 5종목·유효 시총 3 보존, R-C5) / F13-5(양 시장 비공백, R-C7) / F13-6(합성 바 재현) 포함. 크기 예산을 **약 360종목 / 16~17 MB**로 갱신했다(v0.4.2의 13 MB는 상위집합 미고려 값). **(7) 합성 바 명문화 [§8.1.1]** — 라이브 주봉에 `2026-08-11` 행이 **존재하지 않으며**(실측 최근 바 `2026-08-12`), 픽스처의 그 바는 빌더가 라이브 `2026-08-12`를 **재라벨링**한 **합성 바**다. 어느 절도 이를 기록하지 않아 재빌드 시 누락되면 AC-SAG-046의 리터럴 4개가 코드 변경 0줄에 전부 RED가 된다. MANIFEST `synthetic_bar` 기록을 요건화하고 F13-6이 검사한다. **(8) 고아 AC 결속** — AC-SAG-037(N5) · AC-SAG-049(D26)를 plan.md 마일스톤 RED 목록에 등재했다. **(9) §8.6 신설** — 스윕이 평가하지 못한 8개 항목 각각에 **미검증 유지가 안전한 근거** 또는 **검증 가능하게 만드는 요건**을 기재했다. AC 49 → **50**. |

---

## 0. BRIEF (Lesson #7 [HARD] 의무 항목)

### 0.1 라이브 사용 가설 + 재평가 체크포인트

| 항목 | 내용 |
| --- | --- |
| 가설 | 사용자는 섹터 순위표를 "어느 섹터에 돈이 들어오고 있는가"의 1차 판단에 쓴다. 시총가중 전환 후, 사용자는 **대형주가 지배하는 섹터의 순위 하락을 납득**하고, 초과수익률 부호가 양방향으로 갈리는 것을 "시장 폭 신호"로 읽을 수 있어야 한다. |
| 기대 행동 | ship 후 1~2주 사용 시점에 (a) 상위 섹터 → 종목 탐색 진입 동선이 유지되는가, (b) "순위가 이상하다"는 신고가 발생하지 않는가, (c) RRG 사분면 편중을 사용자가 시장 방향으로 해석하는가. |
| 정량 지표 | 1W 초과수익률 양수 섹터 29/29 → **18/29**. 신고가 종목 99 → **56**. 순위 평균 이동 3.5계단. RRG 워밍업 12점 제거. |
| 재평가 시점 | ③ UI ship 이후 **라이브 사용 7일 시점**에 사용자에게 "시총가중 순위가 직관과 맞는가 / 상한 10%가 적절한가"를 확인한다. 상한값(10%)은 재평가 대상이며, 변경 시 `weight_cap` 단일 상수만 조정한다. |
| 폐기 조건 | 사용자가 시총가중 순위를 신뢰하지 않아 등가중으로 되돌리기를 원하면, `weight_cap` 대신 가중 모드 토글을 추가하는 후속 SPEC으로 대응한다. 본 SPEC 전체 폐기는 상정하지 않는다(격자·벤치마크 정합성은 가중 방식과 독립적으로 옳다). |

### 0.2 성능 baseline + 목표값

| 측정 지점 | baseline (측정 의무) | 목표 |
| --- | --- | --- |
| `GET /sectors/ranking` P50 / P95 | 현행 무파라미터 응답 실측 | (period, market) 조합별 P95 < baseline × 1.5 |
| `GET /sectors/rrg` P95 | 현행 실측 | 지수 연쇄 + 시총 역산 추가로 baseline × 2.0 이내 |
| `GET /sectors/history` P95 | 현행 실측 | baseline × 1.5 이내 |
| 상한 재배분 반복(AG-1) 수렴 횟수 | 신규 | **[v0.4.2 정정 — D17]** `<= min(n, 20)`회 (동결형 구조적 종료 계약). 이전 판의 *"섹터당 <= 5회"* 는 실측과 어긋나 폐기 — 최악 6회(4,000 케이스) / 7회(60,000 케이스, `n <= 60`) |
| 전 섹터 집계 1회 (29 섹터 × 2,546 종목) | 신규 | < 300ms |

**③ UI가 기간 토글마다 서버 재조회를 유발**하므로(CT-4 trade-off) 응답 지연이 곧 사용자 체감이다. baseline 미측정 상태에서 M 착수를 금지한다.

### 0.3 SPEC ID ↔ UI 요소 매핑 표

본 SPEC이 **값을 공급**하는 UI 요소 (렌더링은 ③ 소관):

| UI 요소 | 공급 필드 | 신규/변경 |
| --- | --- | --- |
| 순위표 `Rank` 열 | `rank` (period, market 함수) | 의미 변경 |
| 순위표 `복합점수` 열 | `composite_score` | 신규 열(값은 기존, 정규화 방식 변경) |
| 순위표 `Δ순위` 열 헤더의 기준일 | `baseline_date` | 신규 필드 |
| 헤더 벤치마크 표기 `전체 상한가중(10%) +1.88%` | `benchmark.name`, `benchmark.return_*`, `weight_cap` | 신규 |
| 기준일 배지 / 진행 중 배지 | `as_of_date`, `as_of_is_partial_week` | 신규 (값 출처는 ①) |
| 표 하단 `순위 대상 제외 (2)` 영역 | `excluded[]` | 신규 |
| 저신뢰 `⚠` 배지 | `coverage_ratio`, `low_confidence` | 신규 |
| 상세 패널 `가중치 상한 적용 3종목` | `capped_members[]` | 신규 |
| 상세 패널 `유효N` | `effective_n` | 신규 |
| 종목 표 `섹터비중` 열 | `weight_in_sector` | 신규 |
| Stage 분포 바 `미분류` 세그먼트 | `unclassified_count` | 신규 |
| 종목 버블 X 기준선 값 | `sector_aggregate` | 신규 |
| RRG 사분면 라벨의 벤치마크 이름 | `benchmark_name` | 신규 |
| RRG 궤적 시작 표기 | `trail_start_date`, `lookback_weeks` | 신규 |
| Bump 축 하단 `12주 (84일)` | `weeks`, `span_days` | 신규 |

**본 SPEC 단독으로는 화면에 아무 변화가 없다** — 필드를 추가할 뿐 렌더링은 ③이 한다. 사용자가 "이 SPEC의 결과"로 인식할 화면은 ③의 것이다.

### 0.4 rollback 시나리오

| 단계 | 안전 commit 경계 | rollback |
| --- | --- | --- |
| M1 (집계 코어) | 신규 함수 추가 + 기존 경로 미변경 | 파일 단위 revert |
| M2 (벤치마크) | 단일 commit | revert 시 초과수익률이 현행 편향 상태로 복귀 |
| M3 (순위/정규화) | 단일 commit | revert 시 min-max + 비대칭 반올림 복귀 |
| M4 (RRG) | 단일 commit | revert 시 횡단면 z-score 복귀. **③의 RRG 범례 변경과 짝** — ③ 배포 후 ②만 revert하면 라벨과 값이 어긋난다 |
| M5 (지표 정정: MAX52/Stage/volume) | 지표별 개별 commit | 지표 단위 revert 가능 |
| M6 (응답 스키마 + 라우터 파라미터) | 단일 commit | **추가 전용 필드 + optional 파라미터**라 기존 프론트와 하위 호환 → 단독 revert 안전 |

**설계 원칙**: M6의 응답 필드는 전부 **추가**이고, 라우터 파라미터는 전부 **optional + 기본값**이다. 따라서 ② 단독 ship이 안전하고 ③은 나중에 붙일 수 있다(Lesson #7 rollback 단순화).

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **선행 설계 (Tier L 산출물 대체)**: 본 SPEC은 Tier L이나 `design.md` / `research.md`를 새로 작성하지 않는다. 그 역할은 이미 확정·교차검증된 다음 두 문서가 수행한다.
  - 연구/실측: `docs/sector-ux/01-data-contract.md` (855줄, 전 수치가 read-only 쿼리 실측)
  - 설계: `docs/sector-ux/02-screen-flow.md` §12.3 (서버 선행 조건)
  - 중복 작성은 SSOT 분기를 만들므로 금지한다. 두 문서를 **인용**한다.
- **선행 SPEC**: `SPEC-SECTOR-GRID-001` (격자·유효 유니버스·`as_of_date`·`anchor(t,days)` 공급). **본 SPEC은 ①이 close된 뒤에 run 착수한다.**
- **변경 성격**: BROWNFIELD — 기존 엔드포인트의 의미가 바뀐다.
- **개발 방법론**: TDD.

### 1.2 기존 코드 현황 (01 부록 A 인용)

| 경로 | 현행 결함 | 본 SPEC의 조치 |
| --- | --- | --- |
| `sector_metrics.py:173-175` | `sum/n` 등가중 | 시총가중 + 상한 |
| `sector_metrics.py:42-44` 주석 | 시총가중이라 **거짓 기재** | 주석 정정 |
| `sector_metrics.py:151-154, 176, 179-184` | RS `or 0.0` + 분모 잔존 | 결측 제외 |
| `my_chart/price.py:148` | `MAX 52W = Close.rolling(52).max()` | 사용 중단, `MAX(High) over 364d`로 판정 |
| `sector_metrics.py:164` | `Close >= MAX52 × 0.98` | 실제 High 기준으로 판정 |
| `backend/services/sector_detail_service.py:23-47` | 일봉 근사 Stage 분류기 | **폐기** |
| `my_chart/analysis/stage_classifier.py:classify_stage` | 주봉 Weinstein | **단일 채택** |
| `sector_advanced.py:608, 705` | `volume_sma10 = sma10` (가격 SMA) | weekly `VolumeSMA10` 사용 |
| `sector_advanced.py:608, 705` | 거래대금 산출 | daily `VolumeWon` 사용 |
| `sector_metrics.py:285, 311` | 비결정 tie-break | `(−composite, sector_name)` |
| `sector_metrics.py:230-237` | `LIMIT 1 OFFSET 3` | ①의 `anchor(t, 28)` |
| `sector_metrics.py:275-280, 305-309` | 반올림 비대칭 | 반올림 전 값으로 비교 |
| `sector_metrics.py:109-117` | min-max 정규화 (`:115-116` 붕괴 시 50.0) | 순위 백분위 정규화 |
| `sector_metrics.py:94-106` | `_load_kospi_returns` 조용한 0.0 | 명시적 오류 상태 |
| `sector_advanced.py:145-178` | `_get_benchmark_return` KOSPI 고정, RRG 미사용 | 시장별 전환 + RRG 경로 연결 |
| `sector_advanced.py:285-304` | 날짜별 지수 재계산 | 수익률 연쇄 |
| `sector_advanced.py:328-331` | `_rolling_zscore` 상수 100 패딩 | 워밍업 미발행 |
| `sector_advanced.py:437-453` | RS-Ratio 횡단면 z-score | 벤치마크 기준 |
| `sector_advanced.py:537` | 혼합 방법론 초과수익률 | 방법론 일치 |
| `backend/routers/sectors.py:43-58` | `sector_ranking()` 무파라미터 | `period`·`market` 신설 |
| `backend/routers/sectors.py:82-83` | `sector_rrg()` 무파라미터 | `market` 신설 |
| `backend/routers/sectors.py:100-102` | `weeks`만 | `market` 신설 |
| `backend/routers/sectors.py:134-137` | 종목 버블 `period`만 | `market` 신설 |
| `backend/services/stage_service.py:81-91` | `by_sector` 이미 존재 | `unclassified_count` 추가 |
| `tests/test_sector_metrics.py:195-215` | 8개 `hasattr` 호출 — 값 단언 없음 | **의미 테스트로 대체** |

### 1.3 테스트 현황 (실측)

`tests/test_sector_metrics.py:195-215`는 `hasattr` 8회만 호출하고 값을 검증하지 않는다. 가중 방식을 등가중 ↔ 시총가중으로 바꿔도 **어떤 테스트도 실패하지 않는다.** 본 SPEC은 신규 의미 테스트를 **1급 산출물**로 취급한다(§4 Exclusions 아님).

---

## 2. Assumptions (가정, Lesson #5)

- **A1**: ①이 제공하는 `effective_universe(as_of_date, market)`가 집계의 유일한 모집단이다. ②는 유니버스를 직접 산출하지 않는다.
- **A2 (사용 패턴)**: 단일 사용자, 주 1회~수시 수동 갱신, 실시간 요구 없음. 따라서 집계는 **요청 시 계산**하고 사전 배치 계산 테이블을 만들지 않는다.
- **A3 (캐시 모델)**: 서버 캐시는 `(as_of_date, market_filter, period, grid_version)` 키의 **프로세스 내 메모이즈**만 둔다(01 §7.2 SN-5). Redis 등 외부 캐시는 도입하지 않는다 — `MarketContext` 수동 갱신 패턴(프로젝트 기존 모델)과 일관.
- **A4**: `stock_meta.market_cap`은 **현재 시점 스냅샷**이며 시점별 시총 이력 테이블은 존재하지 않는다(01 §10 O-3). RRG는 역산에 의존한다.
- **A5**: `VolumeWon`은 daily DB에 존재하며 최신일 NULL 0건(실측). 재계산하지 않는다.
- **A6 (dataframe 전파, Lesson #4)**: `sector_advanced.py`는 dict/dataclass 파이프라인이며 pandas derived dataframe 복사 의미 문제가 있는 경로는 `sector_metrics.py`의 집계 중간 구조다. 신규 필드(coverage/weight/capped)는 **dataclass → Pydantic → JSON 전 구간에서 명시 전파**되어야 하며 이를 AC로 검증한다.
- **A7**: 프론트엔드는 본 SPEC이 추가한 필드를 **무시해도 동작**한다(추가 전용). 따라서 ② 단독 ship이 안전하다.
- **A8**: 지수 행(`Name='KOSPI'`/`'KOSDAQ'`)은 **정합성 검증용**으로만 읽고 초과수익률 기준으로 쓰지 않는다. 지수 레벨·지수 High/Low는 **화면에 노출하지 않는다**(01 O-4 결정).

---

## 3. Requirements (요구사항, GEARS)

### 3.1 가중·집계

#### REQ-SAG-001 (Ubiquitous) — 시총가중 + 반복 상한 재배분

The aggregation module **shall** compute sector returns as `Σ(wᵢ×rᵢ)/Σwᵢ` where `wᵢ` is derived by the iterative capping algorithm: `wᵢ = capᵢ/Σcap`, `cap_eff = max(0.10, 1/N)`, then iteratively clip over-cap weights and redistribute the excess proportionally **among the not-yet-capped constituents only**, with `Σwᵢ = 1` (규칙 AG-1).

The capping loop **shall not** return a weight vector whose maximum exceeds `cap_eff`. A constituent clipped to `cap_eff` **shall** be excluded from every subsequent redistribution set (동결), so that the frozen set grows strictly monotonically and the loop terminates within `min(N, 20)` iterations.

- **[v0.4.2 신설 — D17]** 재배분 대상에서 상한 종목을 제외하지 않는 형태는 진동하며 **상한을 초과한 채 반복 상한에서 종료**한다(실측 4,000 케이스 중 3,183건, 최악 +27.2%). 동결형은 그 형태의 **고정점을 바꾸지 않는다**(수렴까지 돌린 값과 최대 편차 `6.696e-12`, 닫힌 해와 `3.053e-16`) — 종료 성질만 고친다. 알고리즘 본문은 plan.md §3.1.
- **[v0.4.2 신설 — D16] 축퇴 경계**: `cap = 0.10`에서 `N <= 10`이면 `cap_eff = 1/N`이므로 `N × cap_eff = 1`이 되어 해가 **균등 하나뿐**이다 — 시총가중이 등가중과 **완전히 동일**해지며, 상한 재배분이 관측 가능한 하한은 `N >= 11`이다. 이 경계가 acceptance.md §8.2 F12의 근거다.
- **[v0.5.0 — 불변식 정본 이관]** 위 두 성질과 `effective_n <= N`은 **acceptance.md §0 `INV-CAP-1`**에 3개 명제로 통합 기술됐다. 같은 뿌리의 결함이 AC-SAG-002(D16) / 003(D17) / 010(D22) / 041(N1) **네 곳에서 따로** 적발됐기 때문에, 불변식을 한 곳에 못 박고 관련 AC 전수를 그곳에 결속했다. **새 AC가 위반형(`상한 후 가중치 == 0.10`)으로 작성되면 AC-SAG-050의 정적 스캔이 즉시 RED로 만든다.**

- 검증: AC-SAG-001, AC-SAG-002, **AC-SAG-049**, **AC-SAG-050** (INV-CAP-1 작성 규약의 기계적 집행)

#### REQ-SAG-002 (Ubiquitous) — 상한 적용 사실의 노출

Every sector aggregation response **shall** include `weight_cap` and `capped_members[]` (종목명 + 원비중 + 적용 후 비중) (규칙 AG-2).

- 검증: AC-SAG-003

#### REQ-SAG-003 (When) — 결측 종목의 완전 제외

When a constituent's period return (`CHG_*`) is NULL, the aggregation **shall** exclude it from numerator, denominator, and weight renormalization alike. 0 치환을 금지한다 (§2.0 분모 규칙).

- 검증: AC-SAG-004

#### REQ-SAG-004 (When) — NULL market_cap 처리

When a constituent's `market_cap` is NULL or `<= 0`, the aggregation **shall** exclude it from cap-weighted metrics while **including** it in equal-weighted metrics (RS 평균, Stage 비율, 신고가 비율, 종목 수), and **shall** report `cap_coverage_ratio` (규칙 UN-6, AG-3). 대체값(1.0·중앙값) 부여를 금지한다.

- **[v0.4.2 확정 — D18] `cap_coverage_ratio`의 정의는 정확히 하나다**: `Σ market_cap(유효 시총 ∧ 해당 기간 수익률 non-null 종목) / Σ market_cap(유효 시총 종목)`, 기간이 여럿이면 **기간별 최솟값**. 즉 `coverage_ratio`(종목 수 공간)의 **시총 공간** 짝이다. 이전 판 표현 `유효시총합 / 전체시총합`은 NULL 종목의 시총을 합산할 수 없어 **항상 1.0이 되는 항진명제**였으므로 폐기한다.

- 검증: AC-SAG-005

#### REQ-SAG-005 (Where) — 유효 시총 종목 부족 시

Where a sector's valid-market-cap constituent count falls below the §5.4 minimum, the cap-weighted metrics **shall** be `null` and only equal-weighted metrics are provided, with the methodology difference flagged in the response (규칙 AG-4).

- 검증: AC-SAG-006

#### REQ-SAG-006 (Where) — 최소 구성종목 수

Where a sector's post-filter effective constituent count is below 5, the sector **shall** be excluded from ranking / bubble / RRG output and listed in `excluded[]` with `reason: "insufficient_members"` and `count` (규칙 AG-5). 목록에서 숨기는 것을 금지한다.

- 검증: AC-SAG-007

#### REQ-SAG-007 (Ubiquitous) — 커버리지 필드 동반

Every sector aggregation entry **shall** carry `member_count`, `valid_count`, `coverage_ratio`, `cap_coverage_ratio` (규칙 AG-6).

**O-A6 결정 (2026-08-12) — 지표별 커버리지 + 최상위 최소값 병행**:

- `coverage: {rs, nh, stage, chg, trading_value}` 객체를 추가로 싣는다. `01 §5.5`의 `valid_count` 정의가 이미 지표별이므로 단일 필드로는 "어느 지표가 비었는가"를 알 수 없다.
- **동시에 최상위 `coverage_ratio = min(coverage.*)`을 유지한다** — 기존 단일 필드 소비자(§8.1 저신뢰 판정, REQ-SAG-008의 AG-7 임계, ③의 `⚠` 배지)를 깨지 않기 위한 하위 호환 장치다.
- **AG-7의 0.80 / 0.50 임계는 최상위 최소값에 적용한다.** 지표별 값에 개별 임계를 걸지 않는다 — 한 지표만 비어도 행 전체가 저신뢰로 표시되는 것이 보수적으로 옳다.
- `valid_count`도 동일하게 `valid_counts: {rs, nh, stage, chg, trading_value}` + 최상위 최소값 형태를 취한다.

- 검증: AC-SAG-008 (불변식 **AG-6**)

#### REQ-SAG-008 (Where) — 커버리지 하한

Where `coverage_ratio < 0.80`, the entry **shall** carry `low_confidence: true`. Where `coverage_ratio < 0.50`, the metric value **shall** be `null` with `reason: "insufficient"` (규칙 AG-7).

- 검증: AC-SAG-009

#### REQ-SAG-009 (Ubiquitous) — 유효 종목수 노출

The sector detail response **shall** include `effective_n = 1/Σwᵢ²` (상한 적용 후) (01 §5.1).

- **[v0.5.0 신설 — D22]** `effective_n <= N`이 **항등적으로** 성립하며(INV-CAP-1 명제 3), 축퇴 구간(`N <= 10`)에서는 `effective_n == N`으로 정확히 붕괴한다. 따라서 `effective_n` 기대값을 라이브 대형 섹터의 실측값으로 못 박는 AC는 작성 금지다 — 픽스처의 `N`이 그보다 작으면 산술적으로 성립 불가다(AC-SAG-010의 이전 판이 라이브 반도체 `N=163`의 `24.3`을 `N=6` 픽스처에 요구했다).

- 검증: AC-SAG-010 (순수 합성 유도 + 축퇴 대조)

### 3.2 벤치마크

#### REQ-SAG-010 (Ubiquitous) — 시장별 벤치마크

The benchmark **shall** be the cap-applied market-cap-weighted aggregate of the filtered universe: KOSPI 필터 → KOSPI 구성종목, KOSDAQ → KOSDAQ, All → 전체 (규칙 BM-1).

- 검증: AC-SAG-011

#### REQ-SAG-011 (Ubiquitous) — 방법론 일치

The benchmark **shall** be computed with the same effective universe, the same 10% cap, the same canonical grid dates, and the same missing-value handling as the sector aggregates (규칙 BM-2).

- 검증: AC-SAG-012 (불변식 **EX-1**), AC-SAG-013 (불변식 **EX-2**)

#### REQ-SAG-012 (Ubiquitous) — 동일 날짜 창

Sector return and benchmark return **shall** use the same as-of date and the same past anchor date, and both dates **shall** appear in the response (불변식 BM-6).

**O-A8 결정 (2026-08-13) 반영 — BM-6 보존 조건의 명시**: `as_of`가 미완성 주 바이므로 창 길이가 라벨 N과 다를 수 있다(§7 O-A8). 이 상태에서 BM-6을 지키는 조건은 하나다 — **섹터 쪽과 벤치마크 쪽이 같은 `anchor(t, N)` 호출에서 앵커를 얻어야 한다.** 양쪽이 동일 앵커를 공유하는 한 창이 몇 일이든 초과수익률(`sector − benchmark`) 비교는 정합적이며, **창 길이 ≠ N은 오류가 아니라 기대되는 상태**다. 반대로 한쪽이 `history_grid` 마지막 바를, 다른 쪽이 `latest`를 기준으로 각자 앵커를 구하면 두 날짜가 어긋나고 BM-6이 **무증상으로** 깨진다. 구현은 D1/D2(공용 함수 재사용)로 이 동일성을 **구조로** 보장한다. `anchor()`는 정의상 `history_grid`(완성 바)만 반환하므로 앵커 쪽에는 미완성 바가 절대 섞이지 않는다.

**v0.4.0 정정 (D6) — 출력 동등 단언은 이 불변식을 게이팅하지 못한다**: 이전 판은 "두 앵커 날짜의 **문자열 동등**"을 AC-SAG-014의 단언으로 삼았다. 실증(2026-08-13, 프로즌 스냅샷 `as_of=2026-08-11`)에서 이 단언은 검출력이 **0**이다 — 벤치마크가 `latest`(`2026-08-11`)에서 앵커를 구하든 `history` 마지막 완성 바(`2026-08-07`)에서 구하든 `anchor(·, 7/28/91)`이 **동일하게** `2026-07-31 / 2026-07-10 / 2026-05-08`을 반환한다. 즉 "각자 따로 구한" 오구현이 출력 동등을 그대로 통과한다(D6이 지적한 무증상 통과). 따라서 BM-6의 게이팅 단언은 **구조 단언**이어야 한다 — 한 요청 처리 중 `(as_of, N)` 조합당 `anchor()` 호출이 **정확히 1회**이고 섹터 경로와 벤치마크 경로가 그 **같은 반환값**을 소비함을 호출 계측으로 확인한다. 출력 동등은 보조 단언으로만 남긴다.

- 검증: AC-SAG-014 (불변식 **BM-6**) — 구조 단언(공유 `anchor()` 단일 호출) 주 + 출력 동등 보조.

#### REQ-SAG-013 (When) — 지수 행 정합성 검증

When the difference between the uncapped pure cap-weighted constituent aggregate and the index row (`Name='KOSPI'`/`'KOSDAQ'`) exceeds the tolerance (1W <= 0.5%p, 1M <= 3%p, 3M <= 7%p), the response **shall** carry `benchmark_reconciliation_warning` with the measured difference (불변식 BM-3).

- 검증: AC-SAG-015 (불변식 **BM-3**)

#### REQ-SAG-014 (Unwanted Behavior) — 조용한 0.0 금지

The benchmark loader **shall not** return `0.0` when benchmark data is unavailable. It **shall** set `benchmark_return = null`, `benchmark_status = "unavailable"`, `benchmark_error = <사유>`, `excess_return = null`, `composite_score = null` (규칙 BM-4, BM-5).

- 검증: AC-SAG-016

### 3.3 순위·정규화

#### REQ-SAG-015 (Ubiquitous) — 순위 백분위 정규화

Normalization **shall** be `norm(v) = (rank_ascending(v) − 1)/(N − 1) × 100` with ties assigned the average rank; `N == 1` → 50.0; `N == 0` → 빈 결과. min-max 정규화를 폐기한다 (규칙 AG-8).

- 검증: AC-SAG-017

#### REQ-SAG-016 (Ubiquitous) — composite_score

`composite_score = 0.30×norm(excess_1w) + 0.40×norm(excess_1m) + 0.30×norm(excess_3m)`. 어느 기간이라도 `null`이면 composite는 `null`이며 순위 대상에서 제외한다(부분 점수 금지) (규칙 AG-9).

- 검증: AC-SAG-018

#### REQ-SAG-017 (Ubiquitous) — 결정적 tie-break

The ranking sort key **shall** be `(−composite_score_unrounded, sector_name)`. 레지스트리 삽입 순서 의존을 금지한다 (불변식 RK-1).

- 검증: AC-SAG-019 (불변식 **RK-1**)

#### REQ-SAG-018 (Ubiquitous) — 반올림 시점

Rounding **shall** occur exactly once, immediately before response serialization. 정렬·순위 비교·현재/과거 composite 대조는 모두 반올림 전 값으로 수행한다 (불변식 RK-2, 규칙 AG-10).

- 검증: AC-SAG-020 (불변식 **RK-2**)

#### REQ-SAG-019 (Ubiquitous) — rank = f(period, market)

`GET /sectors/ranking` **shall** accept `period` (`1w|1m|3m`) and `market` (`all|kospi|kosdaq`) and **shall** return `rank` computed for that (period, market) pair, so that ascending `rank` order and the returned row order agree (규칙 CT-4).

- 검증: AC-SAG-021

#### REQ-SAG-020 (Ubiquitous) — composite는 별도 열로 보존

The ranking response **shall** additionally return `composite_score` and `composite_rank` as independent fields, so the multi-period view survives the period-scoped ranking (규칙 CT-5).

- 검증: AC-SAG-022

#### REQ-SAG-021 (Ubiquitous) — rank_change 기준일

`rank_change = rank(baseline_date) − rank(as_of_date)` where `baseline_date = anchor(as_of_date, 28)` from SPEC-SECTOR-GRID-001. The response **shall** include `baseline_date`. 비교 기준일이 없거나 당시 순위 대상이 아니었으면 `rank_change = null`(0 아님) (§2.10).

**O-A8 결정 (2026-08-13) 반영 — 실제 간격은 28일보다 길다**: `as_of`가 미완성 주 바일 때 `anchor(t, 28)`은 28일 전이 아니라 그보다 이른 완성 바를 가리킨다(실측: 프로즌 `as_of=2026-08-11` → `baseline_date=2026-07-10`, 간격 **32일**). 요구사항 문구는 그대로 유효하다 — 정의가 "28일"이 아니라 `anchor(t, 28)`이기 때문이다. **별도 필드를 신설하지 않는다**: `anchor(t, 28)`은 1M 수익률 앵커와 **동일한 호출**이므로, 소비자는 `baseline_date`(날짜)와 REQ-SAG-043의 `return_window_days["1m"]`(일수)만으로 기준 구간을 완전히 복원할 수 있다. `rank_change_baseline_window_days` 같은 네 번째 필드는 같은 값의 중복이므로 만들지 않는다.

- 검증: AC-SAG-023 — 기존 단언 `(as_of_date − baseline_date).days >= 28`은 이 결정을 **이미 수용**한다(`== 28` 이 아니라 `>= 28`). 32일도, 주가 마감된 금요일의 28일도 모두 통과하며, `현행 LIMIT 1 OFFSET 3`(11일 전)과 다름을 요구하는 절이 검출력을 유지한다.

### 3.4 지표 정정

#### REQ-SAG-022 (Ubiquitous) — 52주 신고가 판정

`nh_pct` **shall** be `count(Close >= high_52w × 0.98) / n_valid × 100` where `high_52w = MAX(High)` over the 364-day window. 저장된 `MAX52`(Close 기반)를 판정에 사용하지 않는다. 52주 최고가 산출 불가 종목은 분모에서 제외한다 (§2.5).

- 검증: AC-SAG-024

#### REQ-SAG-023 (Ubiquitous) — Stage 분류기 단일화

Stage classification **shall** use `my_chart/analysis/stage_classifier.py:classify_stage` (주봉) exclusively. `backend/services/sector_detail_service.py:23-47`의 일봉 근사 분류기를 **폐기(코드 삭제)** 한다. `SMA40` 또는 `SMA10`이 NULL인 종목은 **분류 불가**로 분모에서 제외한다 (§2.6).

- 검증: AC-SAG-025, AC-SAG-026

#### REQ-SAG-024 (Ubiquitous) — Stage 합계 항등식

`stage1 + stage2 + stage3 + stage4 + unclassified_count == total` **shall** hold for every stage distribution response, including the `by_sector` entries. 분류 불가를 Stage 1에 흡수시키는 것을 금지한다 (§8.6).

> **[v0.4.1 정정 (D12 파급)] 키 이름을 실제 직렬화 형태에 맞췄다.** 이전 판은 `stage1_count + … == total_count`로 적었으나 현행 응답에 그런 키는 없다. 실측(2026-08-13, `StageOverviewResponse.model_dump_json()`): `distribution` = `{stage1, stage2, stage3, stage4, total}`, `by_sector[i]` = `{sector, stage1, stage2, stage3, stage4}`(합계 키 없음) — `backend/schemas/stage.py:8-15, 18-25`. 기존 키 `stage1`~`stage4`·`total`을 그대로 쓰고, 본 REQ가 **신설**하는 필드는 `unclassified_count`(`distribution`·`by_sector` 양쪽)와 `by_sector[i].total`이다.

- 검증: AC-SAG-027 (불변식 **§8.6**)

#### REQ-SAG-025 (Ubiquitous) — volume_ratio

`volume_ratio = Volume / VolumeSMA10` using the weekly `VolumeSMA10` column. `VolumeSMA10`이 NULL이거나 0이면 `null`(1.0 치환 금지). 가격 이동평균을 거래량 기준선으로 쓰는 현행 동작을 폐기한다 (§2.8).

- 검증: AC-SAG-028

#### REQ-SAG-026 (Ubiquitous) — 거래대금

`trading_value` **shall** be sourced from daily `stock_prices.VolumeWon`. `Close × Volume` 재계산을 금지한다 (§2.7).

**O-A4 결정 (2026-08-12) — 집계 창 = 기간 토글 연동**: `trading_value(period) = Σ VolumeWon over [anchor(t, N), t]` where N = 1W→7일 / 1M→28일 / 3M→91일 (①의 `anchor()` 사용). 근거: 버블의 X축(기간 수익률)과 크기 채널(거래대금)이 **같은 창을 서술**해야 사용자가 두 채널을 함께 읽을 수 있다. 응답에 `trading_value_window_days`를 동반해 ③의 크기 범례가 어느 기간의 값인지 표기할 수 있게 한다(③ REQ-SUX-037).

- 검증: AC-SAG-029

#### REQ-SAG-027 (Ubiquitous) — RS 계열 지표 (등가중 유지)

`rs_avg = Σ RSᵢ / n_valid` (등가중). RS 행이 없는 종목은 분자·분모 모두에서 제외한다. `rs_coverage = n_valid / member_count`를 동반한다 (§2.3, 01 O-7 결정).

`rs_top_pct = count(RS >= 80) / n_valid × 100` — **분모는 `member_count`가 아니라 `n_valid`**(RS 값이 존재하는 종목 수)이며, 임계값 80은 고정 상수로 단일 위치에 정의하고 응답에 `rs_top_threshold: 80`으로 실어 UI가 명시할 수 있게 한다 (§2.4).

- 검증: AC-SAG-030

### 3.5 RRG

#### REQ-SAG-028 (Ubiquitous) — RS-Ratio의 100은 벤치마크

RS-Ratio **shall** be `RS_Ratio(t) = sector_index(t) / benchmark_index(t) × 100`, emitted **without any rolling normalization**, and the value 100 **shall** mean "벤치마크 대비 동일 성과". 횡단면 z-score 기반 산출을 폐기한다 (불변식 RRG-1).

**O-A1 결정 (2026-08-12) — 롤링 정규화 미적용**:

- 자기 시계열 롤링 정규화를 적용하면 중심 100이 "그 섹터 자신의 과거 평균"이 되어 다시 벤치마크가 아니게 된다. 표준 JdK RRG가 바로 그 방식이며, **본 프로젝트는 이를 채택하지 않는다.**
- **표준 JdK RRG와의 발산을 명시한다** — 값이 상용 RRG 도구(StockCharts 등)와 직접 비교 불가함을 응답 `warnings[]` 또는 범례 문구(③ REQ-SUX-042)로 전달한다.
- **강세장에서 다수 섹터가 Leading 사분면에 몰리는 것은 올바른 동작이다.** 100이 진짜 벤치마크이므로 시장 폭이 넓은 국면에서는 대부분 섹터가 벤치마크를 상회한다. **사분면 균등 분포를 요구하는 테스트를 두어서는 안 된다** — AC-SAG-045 R7이 이를 명시적으로 고정한다.
- 섹터별 스케일 차이는 감수하며, ③의 RRG 축 자동 대칭(VZ-8)이 흡수한다.

- 검증: AC-SAG-031 (불변식 **RRG-1**), AC-SAG-045 R7

#### REQ-SAG-029 (Unwanted Behavior) — 워밍업 미발행

The RRG response **shall not** emit points for the rolling warm-up window; those dates are absent from `trail[]`. 상수 100.0 패딩과 그 구간의 차분을 금지한다. `trail_start_date`와 `lookback_weeks`를 응답에 포함한다 (불변식 RRG-2).

- 검증: AC-SAG-032 (불변식 **RRG-2**)

#### REQ-SAG-030 (Ubiquitous) — 지수는 수익률 연쇄

Sector and benchmark indices **shall** be constructed as chained returns (`I(t) = I(t−1) × (1 + r(t))`), not as per-date recomputation of `Σ(close×cap)/Σcap` (불변식 RRG-3).

- 검증: AC-SAG-033 (불변식 **RRG-3**)

#### REQ-SAG-031 (Unwanted Behavior) — look-ahead 시총 금지

The index construction **shall not** apply the current `stock_meta` market-cap snapshot to past dates. 시점별 시총은 `주식수 = 현재시총 / 현재주가`로 상수 주식수를 역산한 뒤 `과거시총 = 주식수 × 과거주가`로 산출한다 (불변식 RRG-4, 고정 결정).

**O-A3 결정 (2026-08-12)**:

- **"현재주가"의 출처는 daily DB의 최신 `Close`로 고정한다.** `market_cap`이 `stock_meta`(daily)에서 오므로 `주식수 = market_cap / Close` 역산의 분자·분모가 같은 원천이어야 한다. 주봉 최신 `Close`를 쓰면 두 원천의 기준일이 어긋나 주식수가 체계적으로 틀어진다. 이 단일 지점을 코드에서 상수로 명시한다.
- **상수 주식수 가정의 한계를 응답 `warnings[]`에 상설 명시한다** — 유상증자·무상증자·액면분할·자사주 소각이 조회 구간에 있으면 과거 시총이 틀린다.
- **이벤트 감지(주가 급변 + 시총 불연속 탐지)는 구현하지 않는다 — 과설계.** 한계를 고지하는 것으로 갈음한다.

- 검증: AC-SAG-034 (불변식 **RRG-4**)

#### REQ-SAG-032 (Where) — RRG 결측 처리

Where RS-Ratio or RS-Momentum cannot be computed, the response **shall** omit the point (100 대체 금지) and record the sector in `excluded[]` with the reason (§8.3).

- 검증: AC-SAG-035

### 3.6 응답 계약·API

#### REQ-SAG-033 (Ubiquitous) — 응답 공통 스키마

Every sector-related endpoint response **shall** include: `as_of_date`, `as_of_is_partial_week`, `return_window_days`, `market_filter`, `weight_cap`, `grid_version`, `benchmark{name, return_*, status, reconciliation_diff_pp}`, `data[]`, `excluded[]`, `warnings[]` (§9.3).

`return_window_days`는 REQ-SAG-043이 정의한다(O-A8 결정의 귀결).

- 검증: AC-SAG-036, AC-SAG-046

#### REQ-SAG-034 (Ubiquitous) — 전 엔드포인트 as_of_date 일치

For a given filter condition, all sector endpoints **shall** return the same `as_of_date` (불변식 SN-3).

- 검증: AC-SAG-037 (불변식 **SN-3**)

#### REQ-SAG-035 (Ubiquitous) — 결측 3상태 구분

Every metric field **shall** distinguish `null + reason:"missing"` / actual `0.0` / `null + reason:"insufficient"`, and additionally carry `low_confidence` and `warnings[]` where applicable (§9.1). 결측을 0 / 0.0% / 50.0으로 표현하는 것을 금지한다 (§9.2).

- 검증: AC-SAG-038

#### REQ-SAG-036 (Ubiquitous) — market 파라미터 전면 신설

The following endpoints **shall** accept a `market` query parameter (`all|kospi|kosdaq`, default `all`) applied as an aggregation-time filter: `/sectors/ranking`, `/sectors/rrg`, `/sectors/history`, `/sectors/{name}/bubble`, `/sectors/{name}/detail`, `/stage/overview` (§12.3, 규칙 UN-7).

- 검증: AC-SAG-039

#### REQ-SAG-037 (Ubiquitous) — period 파라미터

`/sectors/ranking` and `/sectors/{name}/detail` **shall** accept `period` (`1w|1m|3m`, default `1m`).

- 검증: AC-SAG-021, AC-SAG-039

#### REQ-SAG-038 (Ubiquitous) — Bump 히스토리 응답

`/sectors/history` **shall** return `dates[]`, `rankings[date][sector]`, `weeks`, `span_days`, and **shall not** substitute a bottom rank for a sector absent from ranking on a given date (선 끊김을 위해 `null` 유지) (§8.4).

- 검증: AC-SAG-040

#### REQ-SAG-039 (Ubiquitous) — 종목 목록 필드

The stock-listing response (`/stage/overview`, 종목 버블) **shall** include `weight_in_sector`, `sector_minor`, `stage`, `stage_detail`, `rs_12m`, `chg_1w/1m/3m`, `trading_value`, `volume_ratio`, `near_52w_high`, and the sector-scope aggregate `sector_aggregate` (§8.5, §8.7).

- 검증: AC-SAG-041, AC-SAG-042

#### REQ-SAG-040 (Ubiquitous) — 신규 필드의 전 구간 전파 [Lesson #4]

Every field added by this SPEC **shall** be propagated end-to-end: 집계 dataclass → 서비스 변환 → Pydantic 응답 모델 → JSON. 파생 구조(예: 상세용 축약 리스트, `by_sector` 엔트리)에도 동일 필드가 존재해야 한다.

- 검증: AC-SAG-043

#### REQ-SAG-041 (Ubiquitous) — 의미 테스트로의 대체 [테스트 1급 산출물]

`tests/test_sector_metrics.py`의 `hasattr`-only 검증(현행 `:195-215`)은 **값 단언 테스트로 대체**되어야 하며, 가중 방식·정규화 방식·벤치마크 방법론을 되돌리면 **테스트가 실패**해야 한다.

- 검증: AC-SAG-044

#### REQ-SAG-042 (Ubiquitous) — 회귀 방지: 기대되는 변화의 명문화

The regression suite **shall** assert the 8 behavior changes in `02-screen-flow.md` §12.2 as **expected**, not as defects.

- 검증: AC-SAG-045, AC-SAG-047(골든 baseline 캡처 완결성 — M1 종료 게이트), AC-SAG-048(집계 픽스처 F1~F11 충족 — **M1.0-a 종료 게이트**, v0.4.1 D14). 두 게이트는 R1/R4/R5의 비교 기반이 유효하게 성립하기 위한 선행 조건이다.

#### REQ-SAG-043 (Ubiquitous) — 실제 창 일수의 응답 노출 [O-A8 귀결]

Every sector-related endpoint response **shall** include `return_window_days`, an object carrying **all three** period keys — `{"1w": int, "1m": int, "3m": int}` — where each value is the **실측** day count `(as_of_date − anchor(as_of_date, N)).days`, N = 1W→7 / 1M→28 / 3M→91. The values **shall not** be the nominal N when the two differ.

**동기**: O-A8 결정 (a)에 따라 `as_of`가 미완성 주 바이므로 실제 창이 라벨보다 길다 — 실측으로 프로즌 `as_of=2026-08-11`(화)에서 1W가 **11일**, 라이브 `as_of=2026-08-12`(수)에서 **12일**이다. 라벨만 `1W`로 표기하면 HTS·네이버와 값이 어긋나는데 화면에 그 이유가 없다. ③은 이 필드로 `1W (11일치)`를 렌더링한다(`00-overview.md` §4 "진행 중 (N일치)" 배지의 값 출처).

**설계 결정 3건**:

1. **세 키를 항상 전부 싣는다** — `period` 파라미터가 있는 엔드포인트(`/sectors/ranking`, `/sectors/{name}/detail`)에서도 활성 기간만 싣지 않는다. 필드 모양을 엔드포인트마다 다르게 하면 ③이 분기해야 하고, `rank_change`의 `anchor(t,28)` 기준 구간(= `1m` 키)이 `period=1w` 조회에서 사라진다.
2. **`trading_value_window_days`(O-A4)와의 관계**: O-A4의 거래대금 창은 `[anchor(t, N), t]`로 수익률 창과 **같은 구간**이므로, 활성 기간 P에 대해 `trading_value_window_days == return_window_days[P]`가 성립해야 한다. 두 필드는 같은 `anchor()` 호출에서 파생한다.
3. **창이 라벨 N과 같아지는 조건은 "최신 대표 바가 금요일(= 완성 주 대표 바)"이다** — `as_of_is_partial_week == false`가 **아니다**.

   **v0.4.0 정정 (D2) — 이전 판의 이 항목은 실증적으로 거짓이었다.** 이전 판은 *"`as_of_is_partial_week == false`이면 초과분은 0이다"*라고 적었다. 실측(2026-08-13, 프로즌 스냅샷):

   ```
   as_of=2026-08-11  → latest=2026-08-11  partial=True   {1w:11, 1m:32, 3m:95}
   as_of=None(today) → latest=2026-08-11  partial=True   {1w:11, 1m:32, 3m:95}
   as_of=2026-08-17  → latest=2026-08-11  partial=False  {1w:11, 1m:32, 3m:95}   ← 등가 관계 반증
   ```

   원인: **`as_of`는 날짜 축을 자르지 않는다.** `compute_weekly_grid`는 `kept`(격자 바 집합)를 **데이터에서** 도출하고, `as_of`는 오직 미완성 주 판정 `is_partial = (not has_friday) and as_of_d <= week_sunday`(`my_chart/analysis/weekly_grid.py:144`)에만 쓰인다. ISO 주 W33이 금요일 바 없이 마감되면(`as_of`가 그 주의 일요일을 지나면) `partial`은 `False`로 뒤집히지만 **최신 바는 여전히 화요일(`2026-08-11`)**이므로 창은 11/32/95로 남는다. 즉 `partial == false`와 `창 == N`은 등가가 아니다.

   **참 조건 (실증)**: 최신 대표 바 자체가 금요일이어야 한다. 프로즌 `weekly.db`를 `Date <= '2026-08-07'`로 절단한 변형에서 최신 대표 바 = `2026-08-07`(금), `as_of_is_partial_week is False`, `return_window_days == {"1w":7, "1m":28, "3m":91}`, 앵커 `2026-07-31 / 2026-07-10 / 2026-05-08`이 정확히 재현된다. 이 결과는 `as_of`를 `2026-08-11` / `None` / `2026-08-07` 어느 값으로 주어도 **동일**하다 — 조건이 `as_of`가 아니라 **데이터의 최신 바 요일**에 달려 있음을 직접 보인다.

   검증은 이 **금요일 종단 픽스처 변형**으로 수행한다(AC-SAG-046). `as_of` override로는 재현되지 않으므로 `as_of`를 조작하는 형태의 대조는 쓰지 않는다.

**초과분의 성질 (실측)**: 초과분은 최신 대표 바의 요일에만 의존하며 **세 기간에 동일**하다 — 7·28·91이 모두 7의 배수라 `t − N`의 요일이 `t`와 같고, 앵커는 그 요일 직전의 금요일(완성 바)로 밀리기 때문이다. 실측 3회: 화요일 최신 바 → +4(11/32/95), 수요일 최신 바(라이브) → +5(12/33/96), **금요일 최신 바 → 0(7/28/91, 금요일 종단 변형에서 직접 측정)**. 월 +3 / 목 +6은 여전히 **미측정 파생값**이므로 AC 리터럴로 쓰지 않는다.

- 검증: AC-SAG-046

---

## 4. Exclusions (What NOT to Build)

### Out of Scope — 기반 계층

- 정규 주간 격자 산출, 진행 중 주 판정, 유효 유니버스, stale 배제, registry dedup, weekly INSERT 마이그레이션: 전부 **① SPEC-SECTOR-GRID-001** 소관. ②는 소비만 한다.
- 과거 오염 행 처리·적재 경로 변경: ① 소관.

### Out of Scope — 화면·상태

- `AnalysisParamsContext` / `SelectionContext` / `NavIntent`, 토글 단일화, 전환 규칙, 버블 크기 매핑, 축·범례·대비, 로딩/빈 상태 UX: 전부 **③ SPEC-SECTOR-UX-001** 소관.
- 본 SPEC은 응답 필드를 **추가**할 뿐 렌더링을 규정하지 않는다.

### Out of Scope — 기능 확장

- 관심 섹터 워치리스트 / 핀 / 즐겨찾기: 범위 밖.
- 산업명(중) 161개 단위 집계(중분류 순위·RRG): §7 O-A2 미결. 본 SPEC은 종목 필드로 `sector_minor`를 노출할 뿐 중분류 집계를 만들지 않는다.
- 지수 레벨·지수 High/Low의 화면 노출: **금지**(01 O-4 결정 — 일봉 DB에 지수가 없어 교차검증 불가).
- 가중 방식 토글(등가중/시총가중 선택 UI): 도입하지 않는다. `weight_cap`은 서버 상수.
- 사전 배치 계산 테이블·외부 캐시(Redis 등): 도입하지 않는다(A2, A3).
- 신규 엔드포인트 추가: 없음. 기존 엔드포인트의 파라미터·응답 확장만.

---

## 5. Specifications (수용 기준 연결)

상세 시나리오는 `acceptance.md`, 작업 분해·리스크는 `plan.md` 참조.

### Traceability (REQ ↔ AC ↔ 불변식)

| REQ | AC | 01 부록B 불변식 |
| --- | --- | --- |
| REQ-SAG-001 | AC-SAG-001, 002, **049** | — |
| REQ-SAG-002 | AC-SAG-003 | — |
| REQ-SAG-003 | AC-SAG-004 | — |
| REQ-SAG-004 | AC-SAG-005 | — |
| REQ-SAG-005 | AC-SAG-006 | — |
| REQ-SAG-006 | AC-SAG-007 | — |
| REQ-SAG-007 | AC-SAG-008 | **AG-6** |
| REQ-SAG-008 | AC-SAG-009 | — |
| REQ-SAG-009 | AC-SAG-010 | — |
| REQ-SAG-010 | AC-SAG-011 | — |
| REQ-SAG-011 | AC-SAG-012, 013 | **EX-1**, **EX-2** |
| REQ-SAG-012 | AC-SAG-014 | **BM-6** |
| REQ-SAG-013 | AC-SAG-015 | **BM-3** |
| REQ-SAG-014 | AC-SAG-016 | — |
| REQ-SAG-015 | AC-SAG-017 | — |
| REQ-SAG-016 | AC-SAG-018 | — |
| REQ-SAG-017 | AC-SAG-019 | **RK-1** |
| REQ-SAG-018 | AC-SAG-020 | **RK-2** |
| REQ-SAG-019 | AC-SAG-021 | — |
| REQ-SAG-020 | AC-SAG-022 | — |
| REQ-SAG-021 | AC-SAG-023 | — |
| REQ-SAG-022 | AC-SAG-024 | — |
| REQ-SAG-023 | AC-SAG-025, 026 | — |
| REQ-SAG-024 | AC-SAG-027 | **§8.6** |
| REQ-SAG-025 | AC-SAG-028 | — |
| REQ-SAG-026 | AC-SAG-029 | — |
| REQ-SAG-027 | AC-SAG-030 | — |
| REQ-SAG-028 | AC-SAG-031 | **RRG-1** |
| REQ-SAG-029 | AC-SAG-032 | **RRG-2** |
| REQ-SAG-030 | AC-SAG-033 | **RRG-3** |
| REQ-SAG-031 | AC-SAG-034 | **RRG-4** |
| REQ-SAG-032 | AC-SAG-035 | — |
| REQ-SAG-033 | AC-SAG-036, 046 | — |
| REQ-SAG-034 | AC-SAG-037 | **SN-3** |
| REQ-SAG-035 | AC-SAG-038 | — |
| REQ-SAG-036 | AC-SAG-039 | — |
| REQ-SAG-037 | AC-SAG-021, 039 | — |
| REQ-SAG-038 | AC-SAG-040 | — |
| REQ-SAG-039 | AC-SAG-041, 042 | — |
| REQ-SAG-040 | AC-SAG-043 | — |
| REQ-SAG-041 | AC-SAG-044 | — |
| REQ-SAG-042 | AC-SAG-045, 047, 048 | — |
| REQ-SAG-043 | AC-SAG-046 | **BM-6** (창 길이 노출) |

**본 SPEC이 책임지는 01 부록 B 불변식: EX-1, EX-2, RK-1, RK-2, RRG-1, RRG-2, RRG-3, RRG-4, BM-3, BM-6, SN-3, AG-6, §8.6 (13개)**

---

## 6. 의존 관계

- **선행**: `SPEC-SECTOR-GRID-001` close 필요 (격자·유니버스·`anchor()`·`as_of_date`).
- **후행**: `SPEC-SECTOR-UX-001`이 본 SPEC의 응답 필드를 소비한다. 단 ②는 추가 전용 스키마라 ③ 없이도 독립 close 가능하다(A7).

---

## 7. 미결 사항 (SPEC 레벨 open questions)

| ID | 사항 | 출처 | 결정 필요 사항 |
| --- | --- | --- | --- |
| ~~**O-A1**~~ **해결됨** | RS-Ratio 롤링 정규화와 "100 = 벤치마크"의 정합 | 신규 (설계서 내부 모순) | **결정 (2026-08-12): 선택지 (a) — 롤링 정규화를 하지 않는다.** `RS_Ratio(t) = sector_index(t) / benchmark_index(t) × 100`을 그대로 발행하며, 100은 문자 그대로 벤치마크다. 상세는 §3.5 REQ-SAG-028 및 `01 §2.11` 개정본. |
| **O-A2** | 산업명(중) 161개의 중분류 단위 집계 제공 여부 | 01 §10 O-6 = 02 §13 O-7 | 중분류 단위 순위·RRG를 제공할 것인가. 161개 중 상당수가 §5.4 최소 구성수 5에 걸릴 가능성이 크다. 제공 시 서브탭이 늘어 "현행 IA 유지" 제약과 충돌한다. |
| ~~**O-A3**~~ **해결됨** | RRG 시점별 시총 역산의 한계 | 신규 (고정 결정의 미규정 부분) | **결정 (2026-08-12): (a) `warnings[]` 명시 채택. (b) 이벤트 감지는 구현하지 않는다 — 과설계.** 상장주식수 상수 가정의 한계(유·무상증자·액면분할·자사주 소각)를 RRG 응답 `warnings[]`에 상설 기재한다. **"현재주가" 출처 = daily DB 최신 `Close`** — `market_cap`이 `stock_meta`(daily)에서 오므로 주식수 역산의 분모·분자가 같은 원천이어야 정합적이다. 검증: AC-SAG-034. |
| ~~**O-A4**~~ **해결됨** | 거래대금의 기간 정의 | 신규 (설계서 미규정) | **결정 (2026-08-12): 기간 토글과 동일한 창을 합산한다.** `trading_value(period) = Σ VolumeWon over [anchor(t, N), t]`, N = 1W→7일 / 1M→28일 / 3M→91일 (①의 `anchor()` 사용). 근거: 버블의 X축(기간 수익률)과 크기 채널(거래대금)이 **같은 창을 서술**해야 두 채널을 함께 읽을 수 있다. 검증: AC-SAG-029. `01 §2.7` · `§10 O-10` 개정 반영. |
| ~~**O-A8**~~ **해결됨** | 미완성 주 바와 기간 계산의 정합 (①에서 이관) | ①의 §7 O-G2 | **결정 (2026-08-13): 선택지 (a) — 미완성 주를 포함한다.** `as_of = latest`(진행 중인 주 포함), 앵커 = `anchor(t, N)`(정의상 `history_grid` = 완성 바만). **근거(사용자)**: 이 화면을 실시간으로 보므로 진행 중인 주의 움직임이 반영되어야 한다. 그로 인한 부정확은 수용 가능하다고 판단했다. (b)안(수익률은 완성 바만 사용)은 화면이 최대 4~6일 낡아 보이므로, (c)안(병기)은 같은 지표에 두 값을 실어 ③이 어느 쪽을 순위에 쓸지 다시 미결이 되므로 각각 기각. **귀결 — 창은 짧아지는 게 아니라 길어진다**: 실측 프로즌(`as_of=2026-08-11` 화) 1W **11일** / 1M **32일** / 3M **95일**(라벨 대비 +4), 라이브(`as_of=2026-08-12` 수) 12 / 33 / 96일(+5). 초과분은 `as_of` 요일 의존이며 세 기간에 동일하다(7·28·91이 모두 7의 배수). **현행 구현이 이미 이 동작이다** — `_get_latest_valid_date()`(`weekly_grid.py:184`)가 `grid.latest.date`를 반환하고 ①의 M5가 7개 소비자를 이 헬퍼로 수렴시켰으므로, `as_of` 쪽은 새로 만들 것이 없다. **BM-6은 깨지지 않는다** — 섹터·벤치마크가 같은 `anchor(t, N)` 호출을 공유하는 한(REQ-SAG-012 개정 참조) 창 길이가 몇 일이든 초과수익률 비교는 정합적이다. **파생 요구사항**: 라벨과 실제 창의 괴리를 화면이 설명할 수 있도록 **REQ-SAG-043**(`return_window_days`)을 신설했다. 검증: AC-SAG-014(BM-6 보존), **AC-SAG-046**(창 일수 실측값). **v0.4.0 후속 (2026-08-13)**: (i) `as_of`를 **`2026-08-11`로 고정**한다(사용자 결정 — 기존 프로즌 유지, AC-SAG-046의 검증된 리터럴 4개 불변. 게이팅 테스트의 `as_of` 기본값 사용 금지 — acceptance.md §8 규약 8). (ii) 설계결정 3의 "`partial == false` ⇒ 창 == N"은 **실증 반증되어 정정**됐다 — 참 조건은 "최신 대표 바가 금요일"이며 검증은 금요일 종단 픽스처 변형으로 한다(REQ-SAG-043 참조). |
| **O-A5** | 3M 벤치마크 정합성 이탈 (KOSDAQ 6.27%p) | 01 §10 O-5 | **미결이나 2026-08-13부로 착수 가능해졌다** — 선결 조건이던 ① `SPEC-SECTOR-GRID-001`이 `status: completed`(v0.3.0)에 도달했다. 다만 해소에는 재측정이 필요하고 재측정은 run-phase **M3**의 작업이므로, 여기서 답을 적지 않는다. 격자 정규화(① ship) 후 재측정해 원인이 격자 오염인지 구성종목 변동인지 판별한다. 허용오차 **7%p는 잠정치**이며 재측정 후 조정이 필요하다. AC-SAG-015는 임계값을 상수로 분리해 조정 가능하게 둔다. |
| ~~**O-A6**~~ **해결됨** | `coverage_ratio`의 입도 | 신규 (설계서 미규정) | **결정 (2026-08-12): 지표별 + 최상위 최소값 병행.** `coverage: {rs, nh, stage, chg, trading_value}` 객체를 싣고, **동시에** 최상위 `coverage_ratio = min(그 값들)`을 유지해 기존 단일 필드 소비자(§8.1 저신뢰 판정, AG-7 임계, ③의 `⚠` 배지)를 깨지 않는다. AG-7의 0.80/0.50 임계는 **최상위 최소값**에 적용한다. 검증: AC-SAG-008. `01 §10 O-11` 개정 반영. |
| **O-A7** | 최소 구성수 5 규칙의 Bump 적용 여부 | 신규 | 01 §5.4 AG-5는 "순위·버블·RRG 대상에서 제외"라 하고 Bump를 언급하지 않는다. Bump는 순위의 시계열이므로 자동 적용되는 것으로 보이나, 특정 주에만 5 미만이 되는 섹터의 선 처리(끊김)와의 관계가 명시되지 않았다. **③의 AC-SUX-019(제외 섹터 가시성)와 AC-SUX-056 R5(KOSPI 필터 시 제외 영역 등장)가 이 항목에 의존한다** — ③은 "AG-5가 Bump에도 적용된다"를 전제로 작성되어 있으나 그것이 바로 여기서 미결이다. 결정 시 ③의 두 AC에 반영해야 한다. **③ 착수 전 해소 필요.** |
