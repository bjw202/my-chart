---
id: SPEC-FNGUIDE-WCOMP-001
title: "FnGuide 신사이트(wcomp) 이전 대응 — 재무제표·스냅샷 수집층 재작성, 분석 로직 불변"
version: "0.2.2"
status: draft
created: 2026-10-07
updated: 2026-10-07
author: manager-spec
priority: P1
phase: "v0.5.2 target"
module: fnguide
lifecycle: spec-anchored
tags: "fnguide, wcomp, crawler, financial-analysis, s-rim, regression, account-alias"
tier: M
depends_on: [SPEC-DASHBOARD-002]
---

# SPEC-FNGUIDE-WCOMP-001 — FnGuide 신사이트 이전 대응

> 승인된 계획 `.moai/plans/wondrous-noodling-coral.md`를 구현 계약으로 옮긴 SPEC이다. 분석 로직(`fnguide/analysis.py`, `fnguide/dashboard.py`)은 한 줄도 바꾸지 않고, 데이터를 가져오는 계층(`fnguide/crawler.py`)만 새 사이트의 JSON API로 갈아 끼운다. 새 계정명을 옛 계정명으로 바꿔 주는 변환층을 두어 S-RIM 재분류·건전성 지표 등 분석 철학을 그대로 보존한다.

## HISTORY

| 버전 | 날짜 | 변경 |
|---|---|---|
| 0.2.2 | 2026-10-07 | plan-audit iteration 3(FAIL 0.83 strict, 마지막 감사 — 차단 1건 수정 시 PASS-WITH-DEBT 권고) 대응. **D-I3-1**: 라이브 게이트가 통과할 수 있도록 M6에 `test_analysis.py:255-268` 비교 열 수정(`yearly_cols[-2]`)과 별도 후보 교체(`403870, 330590, 476830`)를 명시하고 AC-WC-015 3번 근거에 반영. **S1**: AC-WC-015 4번 AST 프로브를 문자열 상수 노드 기준(docstring 제외, `AnnAssign`·`from … import` 추적)으로 교체, M3·M5에 `_FS_URL`·`_SNAP_URL` 삭제. **S2**: `read_snapshot` 시그니처·반환 형태 고정(REQ-WC-013). **M1~M8**: `TestReadConsensus` 줄 범위 177-196, skip 실제 호출 36, `자산총계` 단언 문구 삭제, progress.md 오래된 서술 갱신, AC-WC-003 (d) VAL4 모두 null 사례, git diff 게이트에 `analyzer.py`·`parser.py`·`__init__.py` 추가, 요청 상한 8을 REQ-WC-004로 올림, 선택 판정 응답의 실패 판정 범위 명시(REQ-WC-002) |
| 0.2.1 | 2026-10-07 | plan-audit iteration 2(FAIL 0.80) 대응. **D-N1**: AC-WC-003 요청 구분 규칙을 "(getFinIncome, Y) 외 다섯 쌍은 결정 유형, (getFinIncome, Y)는 {C, B} 안에서 결정 유형 포함, 데이터 출처는 반환 값으로 증명"으로 교체, 요청 예산(연간 Income C·B 2 + 재무 5 + 스냅샷 1 = 8)을 §5·AC-WC-013에 일치. **D-N2**: REQ-WC-001의 옛 호스트 금지 범위를 `read_fs`·`read_snapshot`·`get_fnguide`와 보조 함수로 한정(`read_consensus`는 남기되 호출하지 않음), AC-WC-015 4번을 AST 판정으로 교체, M6에 `TestReadConsensus` 삭제 추가. **D-N3**: 응답별 검사(REQ-WC-002)가 정렬 검사(REQ-WC-005 (b))보다 먼저, 정렬 비교는 정규화된 `YYYY/MM` 값으로. **D-N4**: `df_yoy_base_ann` 행 라벨도 정규화·별칭. **D-N5~N12**: skip 개수 프로브 교체(재실행 37), 자사주 판별 사례 명시, AC-WC-009 대조를 `read_fs` 수준으로, 경고 토큰 고정, REQ-WC-005·011 하위 조항 (a)(b)(c), 001750 C·B 캡처 목록, `read_fs` 반환 순서 고정, iteration-1 D19 처분 기록 |
| 0.2.0 | 2026-10-07 | plan-audit iteration 1(FAIL 0.78) 대응과 사용자 결정 반영. **사용자 결정**: Q-G 접기는 승인 계획대로 전부 `기타*`(D6·REQ-WC-011에서 금융 계정 분기 삭제), Q-I 명시 목록 유지, Q-D 결산 기간 4개 미만은 `ValueError`(404), Q-F 축소 fixture 커밋, Q-A 수치 전후 비교 불가는 수용한 잔여 위험. **감사 결함**: D2 실패 판정을 본문 기준으로(Content-Type 미관측), D3 접기·정합성 가드를 연간·분기 두 표에 적용하고 차이를 `자산 − 소비 계정 합`으로 정의, D4 접기 목적지·합계 행 부재 시 경고 후 건너뜀, D5 2xx 밖 상태는 `ConnectionError`(503), D6 `depends_on`을 completed인 SPEC-DASHBOARD-002만 남김, D7 "모달 회사명이 코드로 보였다" 주장 삭제, D8 세 재무제표 기간 불일치는 `RuntimeError` 계열(503), D10 옛 이어 붙이기 순서 서술 정정, D16 종목별 데이터 성질은 `While`/`When`, D18 선택 규칙의 "값" 정의, D19b 대시보드 전용 계정까지 부재 경고, D20 종목 코드 ASCII 검증과 쿼리 파라미터 전달. REQ 16 / AC 16 유지 |
| 0.1.0 | 2026-10-07 | 신설. 승인 계획 이식 + plan 단계 계측으로 계획에 없던 결함 2건(D4 중복 행 불변식)과 계획 정정 3건(001750 레이아웃, 정합성 허용오차, 0 행 보충 범위)을 추가 반영. Tier M 예산(REQ 16 / AC 16)에 맞춰 요구사항을 묶음 |

---

## §1 배경

### §1.1 증상

`GET /api/analysis/{code}`가 **모든 종목**에서 503 `list index out of range`를 반환한다(2026-10-07, 005930·403870 재현 — 오케스트레이터 조사). 코드상 호출 경로는 `analysis_service.get_dashboard` → `dashboard.py:928 analyze_dashboard` → `crawler.py:283 get_fnguide` → `crawler.py:187 table_parsing(tables[0])` → `parser.py:38 th[0][0]`이며, 마지막 줄에서 `IndexError`가 난다. 이 예외는 `routers/analysis.py:159-163`의 포괄 `except Exception` 분기에서 503 `internal_error`로 바뀐다.

### §1.2 원인

옛 호스트 `comp.fnguide.com`의 세 URL(`crawler.py:27-36`의 `SVD_Main.asp`, `SVD_Finance.asp`, `json/data/01_06/*.json`)이 모두 HTTP 200과 함께 1,829바이트짜리 "페이지가 없습니다, 새 버전 `https://wcomp.fnguide.com`으로 이동" 안내 페이지를 돌려준다. 이 페이지에는 표가 1개뿐이라 옛 크롤러의 "표 6개를 순서대로 읽는" 방식이 첫 줄에서 무너진다. 상태 코드가 200이므로 상태 코드로는 이 고장을 감지할 수 없다.

### §1.3 실제 소비 범위

`/api/analysis` 응답을 만드는 데 실제로 쓰이는 입력은 `read_fs`의 결과(`df_fs_ann`, `df_fs_quar`, `df_yoy_base_ann`, `account_type`)와 `report`의 키 3개(`Summary`, `베타(1년)`, `종목명`)뿐이다. `df_snap`, `df_snap_ann`, `df_cons`는 받아 놓기만 하고 아무도 쓰지 않는다 — 두 호출부 `dashboard.py:928`과 `analyzer.py:159`가 모두 해당 위치를 `_`로 버린다. `fnguide/analyzer.py`의 `analyze_comp`는 `/api/analysis` 경로에 없다(`backend/`에서 `fnguide.analyzer`·`fnguide.crawler`·`get_fnguide`·`analyze_comp` 참조 0건). 근거 프로브는 `research.md` §R1.

### §1.4 범위를 정한 원칙

- **분석 계층은 고치지 않는다.** 결함은 수집 계층에 있고, 분석 철학(SPEC-DASHBOARD-001의 S-RIM 재분류, SPEC-DASHBOARD-002의 활동성 비율)은 옛 계정명 위에 서 있다. 새 이름을 옛 이름으로 번역하는 쪽이 분석 코드 60곳의 계정명 참조를 고치는 쪽보다 되돌리기 쉽고 영향 반경이 작다.
- **분석 코드가 실제로 의존하는 DataFrame 성질을 계약으로 삼는다.** 옛 크롤러의 출력을 그대로 복제한다고 주장하지 않는다 — 옛 사이트가 죽어 옛 출력은 관측할 수 없다. 대신 분석 코드가 읽는 성질(4열 `YYYY/MM`, 계정별 행 개수, 결측 0)을 계약으로 고정한다. 이 성질 중 일부는 코드에 암묵적으로만 박혀 있어(§3 D4) 이번 plan 단계에서 계측으로 처음 드러났다.

---

## §2 선행 SPEC과의 관계

### §2.1 SPEC-FNGUIDE-ENGINE-001 — 부분 대체 (본문 참조, `depends_on` 아님)

ENGINE-001은 YAML frontmatter가 없고, 본문 메타데이터 표의 상태 칸에 `Completed`가 적혀 있다(기계 판독 가능한 `status:` 필드 없음). run 단계 의존성 사전 점검이 이 SPEC을 미충족으로 오판하지 않도록 `depends_on`에 넣지 않고 본문에서만 참조한다. ENGINE-001 §3.2의 크롤러 요구사항은 옛 호스트를 전제로 쓰였으며, 이 SPEC이 다음과 같이 대체·수정한다.

**대체 관계의 정본 위치**: 이 표(spec.md §2.1)다. ENGINE-001 파일은 어느 단계에서도 수정하지 않는다. sync 단계 manager-docs는 이 SPEC의 `progress.md` §E.4에 "SPEC-FNGUIDE-ENGINE-001 REQ-C-001~006, A-8 부분 대체 — 정본 spec.md §2.1" 한 줄을 남긴다.

| ENGINE-001 항목 | 처분 | 이 SPEC의 대응 |
|---|---|---|
| REQ-C-001 재무제표(연결) — 4열 이상, `자산총계`·`부채총계`·`자본총계` 인덱스 존재 | **수정** | 열은 "4개 이상"이 아니라 **정확히 4개**(REQ-WC-005). 대차대조표 합계는 옛 분석 코드가 실제로 찾는 이름인 `자산`·`부채`·`자본`으로 노출(REQ-WC-009). ENGINE-001이 적은 `자산총계`는 옛 코드의 소비 이름과 애초에 달랐다 — `dashboard.py:678`·`analyzer.py:183`이 찾는 이름은 `자산`·`자본` |
| REQ-C-002 재무제표(별도) | **수정** | `account_type` 판정 근거가 옛 표의 머리글에서 연결/별도 선택 규칙(REQ-WC-004)으로 바뀐다 |
| REQ-C-003 스냅샷 — `df_snap`·`df_snap_ann` 비어 있지 않음 | **대체** | 두 DataFrame은 빈 값으로 반환(REQ-WC-014). `report` 키 계약은 유지하고 `종목명`을 추가(REQ-WC-013) |
| REQ-C-004 컨센서스 | **폐지(이번 회차)** | `get_fnguide`가 더 이상 컨센서스를 요청하지 않는다(REQ-WC-014). 복원은 범위 밖(§6) |
| REQ-C-005 통합 함수 — 7-튜플 | **정정** | 실제 코드는 이미 8-튜플(`crawler.py:257-291`). 8-튜플의 순서와 시그니처를 불변으로 고정(REQ-WC-014) |
| REQ-C-006 잘못된 종목 코드 | **강화** | 판정 기준을 응답 본문으로 고정(REQ-WC-002)하고, 라우터 매핑(404/503)까지 계약에 넣는다 |
| A-8 "모든 크롤링 테스트는 라이브 HTTP, mock 없음" | **수정** | 실응답을 축소한 fixture로 도는 **오프라인 테스트를 기본 스위트에 추가**한다(REQ-WC-016). 라이브 테스트는 `@pytest.mark.live`로 남기되 새 계약에 맞게 다시 쓴다. 근거: 기본 스위트가 101 passed인 상태에서 서비스가 전면 장애였다 — 라이브 전용 테스트는 기본 실행에서 제외되므로(`pyproject.toml:59 addopts`) 이 회귀를 잡을 수 없었다 |

### §2.2 SPEC-DASHBOARD-001 / 002 — 철학 보존

두 SPEC의 산식·섹션 구성·임계값은 그대로다. 이 SPEC은 두 SPEC이 전제한 입력 성질(옛 계정명, 4열, Trailing 12M = 최근 4분기 합)을 새 데이터 원천에서 다시 만들어 낼 뿐이다. `depends_on`에는 `status: completed`인 SPEC-DASHBOARD-002만 둔다. SPEC-DASHBOARD-001은 frontmatter가 `status: draft`라 의존성 사전 점검을 막으므로 본문 참조로만 둔다.

---

## §3 확정 결정

모든 결정의 계측 근거는 `research.md`에 프로브 명령과 함께 있다.

### D1 — 데이터 원천: wcomp JSON API + 변환층
재무제표는 `https://wcomp.fnguide.com/CompanyInfo/getFinIncome|getFinBalance|getFinCashFlow`(쿼리 파라미터 `cmp_cd`, `freq_typ=Y|Q`, `consol_typ=C|B`)에서, 스냅샷은 `https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=`의 서버 렌더 HTML 1회 요청으로 얻는다. 종목 코드는 요청 전에 ASCII `^[0-9]{6}$`로 검사하고 쿼리 파라미터로만 전달한다(URL 문자열 조립 금지). 새 계정명→옛 계정명 번역표, 0 행 보충 목록, 필수 계정 목록은 신규 모듈 `fnguide/account_alias.py` 한 곳에만 둔다(단일 출처).

### D2 — 연결/별도 선택은 종목당 한 번, 여섯 호출에 같은 값
`consol_typ=B`, `P`, `I`는 바이트 단위로 같은 응답이다(`research.md` §R1 F-07). 별도 전용 종목(403870·476830·330590)은 `C`가 전 행 null이고, 001750은 `C`가 앞 두 해만 값이 있다. 규칙: 연간 Income을 `C`와 `B`로 받아, 각 유형의 LVL0 `당기순이익` 행을 본다. 두 행 중 어느 쪽에든 값이 있는 가장 최근 열(VAL4→VAL1 순으로 탐색)에서 `C`의 값이 null이 아니면 `C`, 아니면 `B`다. 선택은 연간·분기 × 세 재무제표 여섯 호출 모두에 똑같이 적용한다(섞지 않음). `account_type`은 `C`이면 `"IFRS(연결)"`, `B`이면 `"IFRS(별도)"`로 합성해 기존 분기 코드(`analyzer.py:173-183`)가 그대로 동작하게 한다. 스냅샷의 hidden `#master_chk`는 `account_type`의 근거로 쓰지 않는다.

### D3 — 레이아웃 판별: Income LVL0에 `매출액(수익)`이 있으면 일반, 없으면 금융
새 사이트에는 금융업 여부를 알려 주는 기계 판독 필드가 없다(`stk_typ`은 관측한 모든 표본에서 1). 표본 Income 응답에서 LVL0 행 이름이 정확히 두 갈래로 나뉜다 — 일반 레이아웃은 `매출액(수익)`으로 시작하고, 은행·보험·증권·카드(105560·055550·000810·006800·001750·029780)는 `매출액(수익)`이 없다(`research.md` §R1 F-10). **001750(한양증권)은 증권사라 금융 레이아웃이다** — 승인 계획은 001750을 "섹션이 채워지는" 쪽에 두었으나 계측과 어긋나므로 이 SPEC은 계측을 따른다(plan.md §B.1 C-1).

### D4 — 중복 행 불변식 [HARD] (계획에 없던 발견)
옛 분석 코드는 계정명 중복에 대해 **두 가지 상반된 가정**을 암묵적으로 한다.

- **단일 행 가정**: `dashboard.py:295`의 `float(df_fs_ann.loc["당기순이익", c])`, `analysis.py:156`의 `df_profit.loc["당기순이익"] = df_fs_ann.loc["당기순이익"]`은 이름이 한 행일 때만 동작한다. 새 응답은 `당기순이익`이 손익계산서(LVL0)와 현금흐름표(LVL1) **두 곳**에 있다. 그대로 이어 붙이면 Section 1은 `TypeError`, Sections 2–7은 `ValueError`로 전부 `None`이 된다(`research.md` §R4 P-1, 프로토타입 실측).
- **다중 행 가정**: `analysis.py:154-155, 161-162`의 `.loc["이자비용"].iloc[0]`, `.loc["법인세비용"].iloc[0]`은 이름이 **두 행 이상**이어서 `.loc`가 DataFrame을 돌려줄 때만 "첫 행"을 뜻한다. 이름이 한 행이면 `.loc`가 Series를 돌려주고 `.iloc[0]`은 **첫 열 값 하나**가 되어 네 해 전체에 복사된다. 새 응답은 `법인세비용`이 손익계산서에만 **한 행**이다. 이 경우 예외 없이 숫자만 틀린다 — 삼성전자 2024/12 법인세비용이 30,783.83이 아니라 −44,808.35로, Trailing 12M이 371,247.80이 아니라 13,198.16으로 계산된다(감사자 독립 재계산으로 확인). 예상 지배주주순이익도 약 20% 줄어든다(접기 없는 프로토타입 기준 수치 — research.md §R4 P-2; 최종 접기 정책에서는 값이 조금 다르므로 AC에 고정하지 않는다). 200 응답과 채워진 섹션만 확인하는 검사는 이 결함을 통과시킨다.

결정: 리더는 (a) 현금흐름표의 `당기순이익`을 `당기순손익`으로 바꿔(재무제표 한정 개명) 단일 행 가정을 지키고, (b) `이자비용`·`법인세비용`이 각각 두 행 이상이며 **첫 행이 손익계산서 값**이도록 보장한다. 두 행에 못 미치면 현금흐름표 뒤에 0 행을 덧붙인다. 이 불변식은 레이아웃과 무관하게 적용한다(의미 번역이 아니라 구조 보정이므로). `당기순손익`이라는 새 이름은 분석 코드가 읽는 어떤 이름과도 겹치지 않는다는 것이 요점이며, 옛 화면의 행 이름을 재현했다고 주장하지 않는다.

**이어 붙이는 순서**: 새 리더는 손익계산서 → 대차대조표 → 현금흐름표 순으로 붙인다. 옛 코드의 순서는 확정할 수 없다 — `crawler.py:194-195`의 변수 이름은 대차대조표 → 손익계산서 → 현금흐름표를 가리키지만, 같은 함수의 docstring(`crawler.py:174`)은 0번 표를 연간손익이라 적는다. 어느 쪽이든 결과는 같다: 표본 4종목(005930 C, 403870 B, 330590 B, 105560 C)에서 손익계산서와 대차대조표가 공유하는 행 이름이 0개이고, 대차대조표와 현금흐름표도 0개다(`research.md` §R1 F-21). 그래서 두 표의 상대 순서는 `.loc`·`.iloc[0]` 결과를 바꾸지 않으며, 의미 있는 조건은 "현금흐름표가 손익계산서 뒤"뿐이다 — 이는 두 순서 모두에서 성립한다.

### D5 — 전년동기 기준 데이터는 사이트의 `(최근분기)` 표지로 결정
연간 Income의 VAL4 머리글에 `(최근분기)`가 붙어 있으면(최근 열이 누적 YTD) VAL5(`전년동기`)를 1열 DataFrame `df_yoy_base_ann`으로 반환하고, 없으면 `None`을 반환한다. 반기 결산 리츠 330590은 머리글이 `2024/12, 2025/06, 2025/12, 2026/06`이고 `(최근분기)`가 없으며, VAL5가 직전 기간(2025/12)과 같은 값이다 — 이때 `None`을 반환해도 `dashboard.py:340-350`이 직전 기간 대비로 같은 숫자를 낸다(`research.md` §R1 F-12).

### D6 — 새 하위 행 접기: 전부 `기타*` (사용자 결정 Q-G)
일반 레이아웃에서 별칭 원천도 필수 계정도 아닌 LVL2 행(`계약자산`, `반품(환불)자산`, `배출권`, `당기손익-공정가치측정금융자산`, `상각후원가측정금융자산` 등)은 `P_AC_CODE` 부모(유동자산 112830 / 비유동자산 110010 / 유동부채 131580 / 비유동부채 130010)를 따라 각각 `기타유동자산`/`기타비유동자산`/`기타유동부채`/`기타비유동부채`에 합산한다. 이름에 `금융`이 들어간 행도 예외 없이 같은 규칙을 따른다. 고려했던 세 안(전부 `기타*` / 금융상품은 금융 계정으로 / 행을 버림)과 선택 근거는 plan.md §B.2에 있다. 이 선택이 움직이는 금액은 삼성전자 2023/12 기준 6,353.93억원이다. 이 행들이 **옛 사이트에 없던 새 행인지는 관측하지 못했다**(옛 사이트 소멸) — 옛 코드가 이 행들을 어떻게 처리했는지도 알 수 없다. 접기는 대차대조표 행이므로 **연간 표와 분기 표 모두**에 적용한다(`analyzer.py:180,183`이 분기 표의 대차대조표 행을 읽는다).

### D7 — 정합성 가드는 경고만, 허용오차 0.1억원
분석 코드가 소비하는 자산 계정의 합과 `자산`, 부채 계정의 합과 `부채`의 차이(`자산 − 소비 자산 계정 합`, `부채 − 소비 부채 계정 합`)를 **연간·분기 두 표의 모든 열**에서 검사하고, 절댓값이 0.1억원을 넘으면 경고 로그만 남긴다(분석은 계속). 승인 계획의 0.01억원은 소수 둘째 자리 반올림 잔차만으로 정상 종목에서 경고를 낸다 — 403870 B의 2024/12 자산 잔차가 −0.02억원으로 관측됐다(`research.md` §R5). 이 가드는 합계를 볼 뿐 어느 계정으로 접었는지는 구별하지 못한다 — 행 누락을 잡는 장치이지 분류 정확성을 보증하지 않는다. 접기 목적지 행이나 `자산`·`부채` 행 자체가 없으면 예외를 내지 않고 경고를 남긴 뒤 해당 접기·검사를 건너뛴다(예외가 새면 지금과 같은 503이 되므로).

### D8 — 0 행 보충은 명시 목록만 (사용자 결정 Q-I)
일반 레이아웃에서 분석 코드가 필수로 찾는데 새 응답에 대응이 없는 계정은 **`account_alias.py`의 명시 목록에 든 것만** 0 행으로 보충한다. 현재 목록은 `관계기업등지분관련투자자산` 하나다 — 그 값은 별칭 `투자자산→장기금융자산`이 이미 담고 있어 0으로 두면 합이 보존된다(`research.md` §R5). 목록 밖의 필수 계정(분석 코드 계정과 대시보드 전용 계정 `매출총이익`·`매출원가`·`영업활동으로인한현금흐름` 포함)이 사라지면 0을 지어내지 않고 경고 로그를 남긴 채 그대로 둔다 — 그래야 해당 섹션이 `None`으로 드러난다.

### D9 — 스냅샷: 같은 키 이름, 둔갑 방지
`report` dict는 옛 키 이름을 유지해 `dashboard.py:551-558, 934, 986`과 `analyzer.py:165-170, 229, 257-261`을 건드리지 않는다. 응답의 hidden `#cmp_cd`가 없거나 요청 코드와 다르면 `ValueError`를 낸다 — 우선주 005935를 요청하면 사이트가 삼성전자(005930) 페이지를 그대로 내주는 함정이 실측됐다(`research.md` §R1 F-15). `#giName`으로 `종목명`을 새로 채운다. 옛 크롤러는 `종목명`을 채운 적이 없어(`crawler.py`에 `종목명` 0건) API의 `company_name`이 늘 종목 코드였다. 다만 **화면에는 변화가 없다** — 재무 분석 모달은 API의 `company_name`이 아니라 차트 셀이 넘기는 `stock.name`을 표시한다(`ChartCell.tsx:428` `companyName={stock.name}`, `AnalysisModal.tsx:765`; 프론트엔드에서 `company_name`은 `types/analysis.ts:91` 타입 선언에만 나온다). 이 개선은 API 수준의 정정이다.

---

## §4 요구사항 (GEARS)

### A. 수집과 실패 판정

#### REQ-WC-001 — 데이터 원천과 요청 위생
The crawler shall validate the code against the ASCII pattern `^[0-9]{6}$` before any request and raise `ValueError` otherwise, shall obtain income, balance and cash-flow statements only from the wcomp JSON endpoints `getFinIncome`, `getFinBalance` and `getFinCashFlow` (for both `freq_typ=Y` and `freq_typ=Q`) and the snapshot only from `https://wcomp.fnguide.com/CompanyInfo/Snapshot` in a single request, passing the code only as a query parameter, shall send every HTTP request with a timeout of at most 10 seconds and with `User-Agent`, `X-Requested-With: XMLHttpRequest` and `Referer` headers, and shall not request any URL on the host `comp.fnguide.com` from `read_fs`, `read_snapshot`, `get_fnguide` or any helper they call (the legacy `read_consensus` and its URL constants are retained but never called, per §6 and `fnguide/__init__.py:31, 51`).

#### REQ-WC-002 — 본문 기반 실패 판정 [HARD]
When a 2xx statement response that the reader uses as data (the six responses of the decided consolidation type, REQ-WC-004), checked per response before any cross-statement comparison of REQ-WC-005 (b), fails to decode as JSON or begins with `<` after leading whitespace is stripped, or its `dataset.data` is empty, or any of its `VAL1`..`VAL4` header periods is null (including a company with fewer than four reported periods), the financial-statement reader shall raise `ValueError` whose message contains the requested code (and, for missing periods, states that the reported periods are insufficient), shall not treat a 2xx status as the success signal, and shall not zero-pad missing periods; when only the selection response of the type that is not decided fails these checks, the reader shall treat that type as having no value and shall not raise, and when the selection responses of both types fail them, it shall raise `ValueError`.

> 근거: 없는 종목·잘못된 코드는 HTTP 200 + 1.6KB 오류 HTML(본문이 `\r\n\n<!DOCTYPE`로 시작), 우선주·ETF는 HTTP 200 + `data=[]` + `YYMM` null 머리글(`research.md` §R1 F-13·F-14). `Content-Type` 헤더는 관측하지 못했으므로 판정 근거로 쓰지 않는다 — 실제 헤더는 run 단계 M1이 기록한다(plan.md §F.1). `ValueError`는 `routers/analysis.py:149-153`에서 404가 된다.

#### REQ-WC-003 — 전송 실패
When a request fails at the transport level (connection error or timeout) or returns an HTTP status outside 2xx, the crawler shall raise `ConnectionError` or an `OSError` subclass so that the router maps it to 503 (`routers/analysis.py:154-158`).

### B. 연결/별도, 열, 값

#### REQ-WC-004 — 연결/별도 선택 [HARD]
The financial-statement reader shall decide the consolidation type once per code by examining the LVL0 `당기순이익` row of the annual income statement of both `C` and `B`, using `C` if and only if the `C` row is non-null in the most recent period column (searched from `VAL4` down to `VAL1`) in which either row is non-null, and `B` otherwise; it shall apply that type to all six statement requests without combining `C` and `B` data, shall reuse the decided type's annual-income selection response as its annual-income data so that one `get_fnguide` call issues at most eight requests (two annual-income selection requests, five further statement requests and one snapshot request), and shall return `account_type` equal to `"IFRS(연결)"` for `C` and `"IFRS(별도)"` for `B`.

#### REQ-WC-005 — 열 모양과 기간 일치
The financial-statement reader shall satisfy the following clauses.

- (a) The reader shall return `df_fs_ann` and `df_fs_quar` with exactly four columns each, taken from `VAL1`..`VAL4` of the annual and quarterly responses and labelled with the leading `YYYY/MM` of each header period with any suffix such as `(최근분기)` removed.
- (b) When, after every response has passed the per-response checks of REQ-WC-002, the normalized `YYYY/MM` values of `VAL1`..`VAL4` differ among the three statements of one frequency, the reader shall raise a `RuntimeError`-class exception (not `ValueError` and not `OSError`, so the router maps it to 503); raw header strings shall not be compared, because the quarterly income `VAL4` reads `2026/06 (최근분기)` while the quarterly balance `VAL4` reads `2026/06`.
- (c) When the normalized fourth quarterly period differs from the normalized fourth annual period, the reader shall log a warning and continue.

#### REQ-WC-006 — 전년동기 열 분리
The financial-statement reader shall exclude `VAL5` and `VAL6` from `df_fs_ann` and `df_fs_quar`; while the annual income header `VAL4` carries the `(최근분기)` marker, it shall return `df_yoy_base_ann` as a one-column DataFrame built from the annual income `VAL5` whose column label contains `전년동기` and whose row labels are normalized per REQ-WC-007 and, while the general layout applies, aliased per REQ-WC-009 (so that `dashboard.py:342` finds `매출액`), and while the marker is absent, it shall return `None`.

#### REQ-WC-007 — 값 변환과 이름 정규화
The financial-statement reader shall convert each `VAL1`..`VAL5` cell to `float`, mapping JSON null and any non-numeric string to `0.0`, and shall derive each row label from `NAME` by removing every space and non-breaking space (`\xa0`) character, without using `AC_CODE` as a cross-layout identifier.

### C. 행 구조

#### REQ-WC-008 — 이어 붙이기와 중복 행 불변식 [HARD]
The financial-statement reader shall concatenate statements in the order income, balance, cash flow for both `df_fs_ann` and `df_fs_quar`, preserving duplicate labels in that order; it shall relabel the cash-flow row `당기순이익` as `당기순손익`, and shall ensure that `이자비용` and `법인세비용` each occupy at least two rows of each frame with the first such row carrying the income-statement value, appending zero-valued rows after the cash-flow rows where fewer than two exist.

#### REQ-WC-009 — 레이아웃 판별과 별칭
While the annual income statement of a code contains a LVL0 row named `매출액(수익)` (general layout), the financial-statement reader shall rename rows of both frames using the alias table defined solely in `fnguide/account_alias.py`; while it does not (financial layout), the reader shall not apply that alias table.

#### REQ-WC-010 — 0 행 보충은 명시 목록만
While the general layout applies, the financial-statement reader shall add a zero-valued row to both frames for each label in the explicit zero-row list of `fnguide/account_alias.py` that is absent after aliasing; when any other label in that module's required-label list (the labels referenced by `fnguide/analysis.py` plus the dashboard-only labels `매출총이익`, `매출원가` and `영업활동으로인한현금흐름`) is absent after aliasing, it shall log a warning naming the code and that label and shall not fabricate a row for it.

#### REQ-WC-011 — 새 하위 행 접기와 정합성 가드
While the general layout applies, the financial-statement reader shall satisfy the following clauses in both `df_fs_ann` and `df_fs_quar`.

- (a) The reader shall add the values of every LVL2 row under the current-asset, non-current-asset, current-liability and non-current-liability subtotals that is neither an alias source nor a required label into that parent's `기타유동자산`, `기타비유동자산`, `기타유동부채` or `기타비유동부채` row respectively.
- (b) When a fold destination row or the `자산` or `부채` row is absent, the reader shall log a warning containing the code, the row name and the fixed token `행 없음`, and shall skip that fold or check without raising.
- (c) When, for any column of either frame, `자산` minus the sum of the consumed asset labels or `부채` minus the sum of the consumed liability labels exceeds 0.1 (억원) in absolute value, the reader shall log one warning per mismatch containing the code, the frame, the column and the signed difference, and shall not raise.

### D. 스냅샷

#### REQ-WC-012 — 둔갑 방지 [HARD]
When the hidden `#cmp_cd` value in the snapshot response is absent or differs from the requested code, the snapshot reader shall raise `ValueError` whose message contains the requested code.

#### REQ-WC-013 — report 키, 종목명, 자기주식
The snapshot reader shall keep the signature `read_snapshot(code, account_type="IFRS(연결)")` (the `account_type` argument is accepted and ignored, so the existing call at `crawler.py:286` stays valid) and return the three-element tuple `(report, empty DataFrame, empty DataFrame)`, with `report` containing the keys `시가총액(상장예정포함,억원)`, `발행주식수(보통주)`, `발행주식수(우선주)`, `자기주식`, `베타(1년)`, `PER`, `12M PER`, `업종 PER`, `PBR`, `배당수익률`, `Summary` and `종목명`, taking `베타(1년)` from the row labelled `52주베타`, `종목명` from the text of `#giName`, and `자기주식` from the shareholder-table row labelled exactly `자사주` (or `0` when absent), and shall map an unparseable numeric field to `0` exactly as the existing `to_num` helper (`parser.py:89-101`) does.

### E. 통합과 불변

#### REQ-WC-014 — 8-튜플 계약과 금융 레이아웃 [HARD]
The `get_fnguide` function shall keep its single parameter `code` and its eight-element return order `(df_fs_ann, df_fs_quar, df_snap, df_snap_ann, df_cons, report, account_type, df_yoy_base_ann)`, shall return empty DataFrames in the `df_snap`, `df_snap_ann` and `df_cons` positions without requesting consensus data, shall keep `read_fs(code)` returning the four-element tuple `(account_type, df_fs_ann, df_fs_quar, df_yoy_base_ann)` in that order (`crawler.py:215`; `test_crawler.py:87` reads `result[0]`), and while the financial layout applies shall return without raising so that `GET /api/analysis/{code}` responds 200 with the sections the unchanged dashboard cannot compute set to null.

#### REQ-WC-015 — 분석 계층과 저장 자세 불변
The implementation shall not modify `fnguide/analysis.py`, `fnguide/dashboard.py`, `backend/routers/analysis.py`, `backend/schemas/analysis.py`, `backend/services/analysis_service.py` or any file under `frontend/`, and the crawler shall not persist fetched FnGuide content anywhere other than the existing in-process five-minute TTL cache (`analysis_service.py:17-18`).

#### REQ-WC-016 — 오프라인 회귀 테스트와 축소 fixture
The test suite shall verify REQ-WC-001..REQ-WC-014 in the default (non-live) run against trimmed wcomp fixtures committed under `tests/fnguide/fixtures/wcomp/` that keep only the rows and columns the tests need (sources and capture times listed in that directory's README), shall include a reproduction test that feeds the 1,829-byte legacy stub page to the reader, and shall keep network-dependent tests under the `live` marker.

---

## §5 비기능 제약

- **요청 수**: 캐시 미스 한 번에 옛 방식 3회(재무 1 + 스냅샷 1 + 컨센서스 1)에서 최대 8회로 늘어난다 — 선택 판정용 연간 Income `C`·`B` 2회(결정된 유형의 응답은 데이터로 재사용) + 나머지 재무 5회 + 스냅샷 1회. 조사 시 초당 약 10회 × 20회 연속에서 차단이 없었다. 기존 5분 TTL 캐시(`analysis_service.py:17-18`)가 반복 요청을 흡수한다.
- **응답 시간**: 요청당 타임아웃 10초 상한(REQ-WC-001). 이번 회차는 성능 목표를 새로 잡지 않는다 — 옛 경로가 전면 장애라 비교할 기준선이 없다. run 단계에서 005930 캐시 미스 1회의 소요 시간을 기록만 한다(plan.md §E).
- **이벤트 루프 차단(기존 구조, 변경 금지)**: `routers/analysis.py`의 `async def analysis`가 동기 크롤링을 그대로 호출한다. 최악의 경우 요청 8회 × 10초 = 80초 동안 이벤트 루프가 막힐 수 있다. 라우터 수정 금지(REQ-WC-015)이므로 이번에는 기록만 한다.
- **로그**: 경고 로그(REQ-WC-005, 010, 011)는 `logging.getLogger(__name__)`으로 남기고 종목 코드를 포함한다.
- **알려진 기존 결함(변경 금지)**: 베타를 못 읽으면 `to_num`이 0을 돌려주고(`parser.py:100-101`), `dashboard.py:549-558`이 이를 그대로 써 자기자본비용 Ke = 3.5%(무위험수익률만)가 된다. 옛 크롤러와 같은 동작이며 이번에 바꾸지 않는다.

---

## §6 범위 밖 (Out of Scope)

### Out of Scope — 금융회사 분석
- 은행·보험·증권·카드 레이아웃(D3)의 분석 지원. 옛 크롤러와 마찬가지로 Sections 1–7은 `None`이 되고 응답은 200이다(REQ-WC-014). `영업수익`·`순이자이익`을 `매출액`으로 별칭하지 않는다.

### Out of Scope — 컨센서스·스냅샷 시계열 복원
- `df_snap`, `df_snap_ann`, `df_cons`의 내용 복원. 소비처가 없어 빈 DataFrame으로 둔다. 필요해지면 후속 SPEC에서 wcomp 컨센서스 JSON(조사 표본 `json/cnsperfor_*.json`)으로 복원한다.
- `read_consensus` 함수 자체의 재작성. `fnguide/__init__.py:31, 51`이 이 이름을 내보내므로 함수는 남기되 호출하지 않는다.

### Out of Scope — 저장과 수집 정책
- DB 저장, 대량·주기 수집, 캐시 TTL 변경. `robots.txt`가 전체 `Disallow`이고 페이지 하단에 DB화 금지 문구가 있다. 요청 시에만 가져오는 현행 자세를 유지한다.

### Out of Scope — 프론트엔드, 라우터, 분석 계층
- `frontend/` 변경(모달 회사명 표시 원천을 API로 바꾸는 일 포함), 응답 스키마 변경, `analysis.py`·`dashboard.py`의 산식·임계값·섹션 변경.
- 라우터의 동기 크롤링 호출 구조(§5) 수정, 베타 파싱 실패 시 Ke = 3.5%가 되는 기존 동작 수정.

### Out of Scope — 우선주·ETF·신규 상장 처리
- 005935 같은 우선주 코드를 보통주로 바꿔 분석하는 기능. 404로 끝낸다.
- 결산 기간이 4개 미만인 신규 상장 기업의 분석. 404로 끝낸다(사용자 결정 Q-D, REQ-WC-002).

---

## §7 추적성

| REQ | AC (acceptance.md) | 성격 |
|---|---|---|
| REQ-WC-001 | AC-WC-009, AC-WC-010, AC-WC-013 | 대조 |
| REQ-WC-002 | AC-WC-001, AC-WC-009 | 대조 |
| REQ-WC-003 | AC-WC-010 | 대조 |
| REQ-WC-004 | AC-WC-003 | 대조 |
| REQ-WC-005 | AC-WC-006 | 대조 |
| REQ-WC-006 | AC-WC-006 | 대조 |
| REQ-WC-007 | AC-WC-002 | 대조 |
| REQ-WC-008 | AC-WC-004, AC-WC-005 | 대조 |
| REQ-WC-009 | AC-WC-002, AC-WC-014 | 대조/불변 |
| REQ-WC-010 | AC-WC-008 | 대조 |
| REQ-WC-011 | AC-WC-007 | 대조 |
| REQ-WC-012 | AC-WC-011 | 대조 |
| REQ-WC-013 | AC-WC-012 | 대조 |
| REQ-WC-014 | AC-WC-013, AC-WC-014 | 대조/불변 |
| REQ-WC-015 | AC-WC-015 | 게이트 |
| REQ-WC-016 | AC-WC-001, AC-WC-015, AC-WC-016 | 게이트 |
