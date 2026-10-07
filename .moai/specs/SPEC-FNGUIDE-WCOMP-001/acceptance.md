# SPEC-FNGUIDE-WCOMP-001 — 인수 기준 (acceptance)

> 이 파일은 검증 층이다. 요구사항(GEARS)은 `spec.md` §4에 있고, 여기서는 각 요구사항을 이진 판정 가능한 Given-When-Then 시나리오와 정확한 명령·기대 출력으로 옮긴다. Tier M 예산에 맞춰 AC는 16개다(v0.2.0에서 새 규칙은 기존 AC에 사례로 병합).

## §A 공통 규약 [HARD]

### §A.1 실행 환경

모든 명령은 저장소 루트에서, 지정된 가상환경 파이썬으로 실행한다(`CLAUDE.local.md`: pip·pytest를 직접 부르지 않음).

```bash
cd /Users/byunjungwon/Dev/my-project-01/my_chart
PY=/Users/byunjungwon/Dev/my_chart/.venv/bin/python
```

### §A.2 테스트 이름 규약 (AC ↔ 테스트 연결)

각 AC를 검증하는 테스트 함수 이름에는 소문자 AC 식별자(`ac_wc_001` … `ac_wc_014`)가 들어간다. 대조 단언용 테스트는 이름에 `_contrast`가 추가로 들어간다. 그래서 `-k ac_wc_00N`으로 해당 AC의 테스트만 골라 돌릴 수 있다. 신규 테스트 파일은 다음 넷이다(run 단계가 만든다).

| 파일 | 담당 |
|---|---|
| `tests/fnguide/test_wcomp_repro.py` | AC-WC-001 |
| `tests/fnguide/test_wcomp_reader.py` | AC-WC-002 ~ AC-WC-010 |
| `tests/fnguide/test_wcomp_snapshot.py` | AC-WC-011 ~ AC-WC-013 |
| `tests/test_analysis_api_wcomp.py` | 라우터 경유 200/404/503 사례(AC-WC-006, 009, 010, 014) |

fixture는 `tests/fnguide/fixtures/wcomp/`에 **축소본**으로 둔다 — 테스트가 쓰는 행·열만 남긴다(REQ-WC-016). "조작본"·"합성본"은 축소 fixture를 테스트 안에서 복사해 고친 것이다(파일로 따로 커밋해도 된다). 네트워크는 `requests.get`(또는 리더가 쓰는 세션의 `get`)을 fixture 응답으로 대체해 차단한다 — 기본 스위트에서 실제 HTTP가 한 건이라도 나가면 규약 위반이다.

### §A.3 기대 출력의 판정 방식

"기대 출력: `N passed`"는 pytest 마지막 요약 줄이 `N passed`로 시작하고 `failed`·`error`라는 낱말을 포함하지 않는다는 뜻이다(deselected·warning은 허용). N은 **하한**이다 — run 단계가 같은 AC에 테스트를 더 붙여도 된다.

### §A.4 대조(contrast)와 불변(invariance)의 구분 — 교훈 #9

- **[대조]** AC는 "틀린 구현을 넣으면 실패한다"를 증명해야 한다. 두 겹으로 증명한다.
  1. **스위트 내 대조 테스트**(`_contrast`): monkeypatch로 **검증 대상 단위 하나만** 순진한 구현으로 바꾼 뒤 **프로덕션 경로**(`read_fs`, `read_snapshot`, `get_fnguide`, `fs_analysis`, `analyze_dashboard`, 라우터)를 그대로 호출하고, 각 AC에 적힌 "되돌림 시 관측값"이 나오는지 단언한다. 단언의 양변이 같은 함수·같은 식에서 나오면 무효다.
  2. **소스 되돌림 관측 1회**: run 단계가 해당 구현을 실제로 되돌린 상태에서 긍정 테스트를 돌려 RED를 보고, 실패 출력을 **그대로** `progress.md` §E.2에 `#### RED 관측 — AC-WC-0NN` 머리글 아래 남긴 뒤 트리를 복원하고 `git status --short`로 복원을 증명한다. 관측하지 못한 AC는 PASS가 아니라 §E.2 Gaps에 미검증으로 적는다.
- **[불변]** AC는 되돌려도 GREEN일 수 있는 회귀 방지 검사다. 대조로 주장하지 않는다.
- **고정값의 출처**: 아래 숫자는 원 응답 값이거나, 감사자 독립 재구현(`scratchpad/auditor/indep.py`, plan 단계 산출물)과 저자 계산이 일치한 값만 쓴다.

---

## §B 대조 단언 (되돌림 시 RED — 실증 의무)

### AC-WC-001 — 옛 안내 페이지 재현 [대조 · Reproduction-First]
**Given** `requests.get`이 어떤 URL에도 1,829바이트 옛 안내 페이지(`legacy_stub_1829.html`, 표 1개)를 HTTP 200으로 돌려준다
**When** `read_fs("005930")`을 호출한다
**Then** `ValueError`가 발생하고 메시지에 `005930`이 들어 있다.
**되돌림 시 관측값**: 현재 코드(수정 전)에서는 `IndexError: list index out of range`(`parser.py:38`) — run 단계 M1이 이 RED를 **구현 전에** 관측해 §E.2에 남긴다.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_repro.py -q -p no:cacheprovider -k ac_wc_001`
**기대 출력**: `1 passed` (수정 후). 수정 전 실행 시 `1 failed`이고 출력에 `IndexError`가 보인다.

### AC-WC-002 — 별칭 계층과 값·이름 정규화 [대조]
**Given** 005930 `C` 여섯 응답 fixture(Income/Balance/CashFlow × Y/Q)
**When** `read_fs("005930")` 결과로 `fs_analysis(df_fs_ann, df_fs_quar)`를 호출한다
**Then** 예외가 없고 `df_anal.loc["주주몫", "2023/12"]`이 `3532337.75`(허용오차 0.01)이며, 이는 원 응답의 `지배주주지분` 2023/12 값과 같다. `df_fs_ann` 인덱스에 `매출액`, `자산`, `유동금융자산`, `이익잉여금(결손금)`이 있고 `매출액(수익)`, `자산총계`가 없다.
추가 사례(REQ-WC-007): 조작본에서 한 행의 `NAME`을 `"\xa0\xa0  재고자산"`, 그 행의 VAL2를 문자열 `"N/A"`로 바꾸면 그 행의 라벨은 `재고자산`, 2024/12 값은 `0.0`이다.
**되돌림 시 관측값**: 별칭표를 빈 dict로 바꾸면(접기는 그대로 동작하는 구현에서) `fs_analysis`가 `KeyError: '매입채무및기타유동채무'`를 낸다 — 감사자 독립 재구현에서 별칭만 비우고 접기를 켠 채 재관측한 결과다. 같은 상태에서 `analyze_dashboard`는 `health_indicators`가 `None`이다.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k ac_wc_002`
**기대 출력**: `3 passed` (긍정 1 + 정규화 1 + `_contrast` 1)

### AC-WC-003 — 연결/별도 선택 규칙 세 경우 [대조]
**Given** (a) 403870: `C` 전 행 null, `B` 정상 (b) 001750: `C`의 `당기순이익`이 VAL1·VAL2만 값, VAL3·VAL4 null (c) 005930: `C`·`B` 모두 정상 (d) 005930 합성본: getFinIncome Y `C`·`B` 두 응답 모두에서 LVL0 `당기순이익` 행의 VAL4만 null로 바꿈(VAL3 이하는 원본 — "VAL4부터 아래로 찾기" 규칙과 "`C`의 VAL4가 있을 때만 `C`" 규칙을 가르는 사례)
**When** 각 코드로 `read_fs`를 호출하고 요청을 기록한다
**Then**
| 코드 | `account_type` | 단언 값 |
|---|---|---|
| 403870 | `IFRS(별도)` | `df_fs_ann.loc["매출액", "2025/12"] == 1729.65` |
| 001750 | `IFRS(별도)` | `df_fs_ann.loc["당기순이익", "2025/12"] == 565.71` |
| 005930 | `IFRS(연결)` | `df_fs_ann.loc["지배주주순이익", "2025/12"] == 442609.56` |
| 005930 합성 (d) | `IFRS(연결)` | VAL3(2025/12)에서 `C` 값 `452068.05`가 있으므로 `C` — `df_fs_ann.loc["지배주주순이익", "2025/12"] == 442609.56` |

**요청 구분** (v0.2.1 교체): 기록된 요청을 `(엔드포인트, freq_typ, consol_typ)`로 식별한다. (1) `(getFinIncome, Y)`를 **제외한** 다섯 `(엔드포인트, freq_typ)` 쌍의 기록된 요청은 **모두** 결정된 `consol_typ`을 가진다. (2) `(getFinIncome, Y)` 요청들의 `consol_typ`은 모두 `{C, B}` 안에 있고, 그중에 결정된 유형이 하나 이상 있다(REQ-WC-004가 두 유형을 모두 살펴보게 하고, 요청 상한 8건 때문에 결정된 유형의 판정 응답이 데이터로 재사용되므로 요청 순서로 데이터 요청을 가려낼 수 없다). (3) 어느 유형의 데이터가 쓰였는지는 위 표의 반환 값이 증명한다 — 세 경우 모두 결정된 유형에서만 나오는 값이다(403870 `C`는 전부 null → `0.0`, 001750 `C` 2025/12는 null → `0.0`, 005930 `B`의 `지배주주순이익` 2025/12는 `336866.01`로 `C`의 `442609.56`과 다름 — plan 단계에서 두 원 응답을 직접 대조).
**되돌림 시 관측값**: (가) "항상 `C`" → 403870이 `IFRS(연결)`·`0.0` (나) "`C`에 값이 하나라도 있으면 `C`" → 001750이 `IFRS(연결)`·`0.0` (다) "항상 `B`" → 005930이 `IFRS(별도)`. (라) "`C`의 VAL4가 null이 아니면 `C`, 아니면 `B`" → (d)가 `IFRS(별도)`.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k ac_wc_003`
**기대 출력**: `8 passed` (네 경우 각각 긍정 1 + `_contrast` 1)

### AC-WC-004 — `당기순이익` 단일 행 불변식 [대조]
**Given** 005930 `C` fixture
**When** `read_fs` 결과로 `dashboard._calc_business_performance(df_fs_ann, df_yoy_base_ann)`를 호출한다
**Then** 예외 없이 결과가 나오고 당기순이익 시계열의 2025/12 값이 `452068.05`이며, `df_fs_ann` 안에서 `당기순이익`은 정확히 1행, `당기순손익`은 1행이다.
**되돌림 시 관측값**: 현금흐름표 행 개명을 빼면 `TypeError: float() argument must be a string or a real number, not 'Series'`.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k ac_wc_004`
**기대 출력**: `2 passed`

### AC-WC-005 — `법인세비용`·`이자비용` 다중 행 불변식 (조용한 오계산 차단) [대조]
**Given** 005930 `C` fixture
**When** `read_fs` 결과로 `fs_analysis`를 호출한다
**Then** `df_anal`이 다음을 만족한다(허용오차 0.01; 감사자 독립 재계산과 일치).
| 행 | 2024/12 | 2026/06 (Trailing 12M) |
|---|---|---|
| `법인세비용` | `30783.83` | `371247.80` (= 13198.16 + 13864.58 + 116031.62 + 228153.44) |
| `이자비용` | `9039.18` | `7558.38` (= 1159.24 + 1652.42 + 2776.69 + 1970.03) |

그리고 `df_fs_ann`, `df_fs_quar` 각각에서 두 이름이 2행 이상이며 첫 행이 손익계산서 값이다.
**되돌림 시 관측값**: 0 행 보충을 빼면 **예외 없이** `법인세비용` 2024/12 = `-44808.35`, 2026/06 = `13198.16`. 현금흐름표를 손익계산서보다 먼저 붙이면 `이자비용` 2024/12 = `0.0`.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k ac_wc_005`
**기대 출력**: `3 passed` (긍정 1 + `_contrast` 2)

### AC-WC-006 — 열 모양, 기간 일치, 전년동기 기준 데이터 [대조]
**Given** (a) 005930 `C` fixture(연간 VAL4 `2026/06 (최근분기)`) (b) 330590 `B` fixture(연간 `2024/12, 2025/06, 2025/12, 2026/06`, 표지 없음) (c) 12월 결산 직후 형태의 합성본: 005930 연간 세 재무제표(getFinIncome Y·getFinBalance Y·getFinCashFlow Y)의 머리글을 `2022/12, 2023/12, 2024/12, 2025/12`(표지 없음, LINE 0)로 바꾼 것 (d) 005930 조작본: getFinBalance Y 응답 하나의 머리글 VAL2 `YYMM`만 `2024/09`로 바꿈(null 아님 — REQ-WC-002의 응답별 검사는 통과하고 REQ-WC-005 (b)의 정렬 검사에서만 걸린다). 나머지 다섯 응답은 원본. 참고: 원본 getFinIncome Q의 VAL4는 `2026/06 (최근분기)`, getFinBalance Q의 VAL4는 `2026/06`이므로 원본 (a)가 통과하려면 정렬 비교가 정규화된 `YYYY/MM` 값으로 이뤄져야 한다 (e) 005930 조작본: 분기 세 재무제표의 머리글 VAL1~VAL4를 한 분기씩 앞당겨 `2025/06, 2025/09, 2025/12, 2026/03`으로 바꾼 것(세 재무제표끼리는 일치, 연간 네 번째 기간 `2026/06`과만 다름)
**When** 각각 `read_fs`를 호출하고, (d)는 라우터로도 호출한다
**Then**
- (a) `list(df_fs_ann.columns) == ["2023/12","2024/12","2025/12","2026/06"]`, `list(df_fs_quar.columns) == ["2025/09","2025/12","2026/03","2026/06"]`, `df_yoy_base_ann`은 1열이고 열 이름에 `전년동기`가 있으며 `매출액` 값이 `1537068.20`. 이를 넣은 `_calc_business_performance`의 마지막 매출 YoY가 `0.98672`(허용오차 1e-4).
- (b) `list(df_fs_ann.columns) == ["2024/12","2025/06","2025/12","2026/06"]`, `df_yoy_base_ann is None`.
- (c) 열 4개 `["2022/12","2023/12","2024/12","2025/12"]`, `df_yoy_base_ann is None`, `analysis.calc_weight_coeff(df_fs_ann.columns) == (1.0, 2.0, 3.0, 6.0)`.
- (d) `ValueError`도 `OSError`도 아닌 `RuntimeError` 계열 예외. 라우터 응답 `503`.
- (e) 예외 없이 반환되고, 연간·분기 네 번째 기간 불일치 경고가 정확히 1건(코드 `005930` 포함).
**되돌림 시 관측값**: `df_yoy_base_ann`을 늘 `None`으로 두면 (a)의 마지막 매출 YoY가 `-0.08463`. 표지와 무관하게 늘 VAL5로 만들면 (b)·(c)의 `df_yoy_base_ann`이 `None`이 아니다. 기간 일치 검사를 빼면 (d)가 예외 없이 반환된다. `df_yoy_base_ann`의 행 라벨에 별칭을 적용하지 않으면(REQ-WC-006) `dashboard.py:343`의 `base_series.at["매출액"]`이 `KeyError`를 내고 `dashboard.py:349-351`이 이를 삼켜, (a)의 마지막 매출 YoY가 **예외 없이** `-0.08463`이 된다.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py tests/test_analysis_api_wcomp.py -q -p no:cacheprovider -k ac_wc_006`
**기대 출력**: `9 passed` (긍정 (a)~(e) 5 + 라우터 (d) 1 + `_contrast` 3)

### AC-WC-007 — 새 하위 행 접기와 정합성 가드 (두 표 모두) [대조]
**Given** 005930 `C` fixture. 유동자산 아래 접힘 대상 비영(非零) 행: `당기손익-공정가치측정금융자산`(2023/12 271.12), `상각후원가측정금융자산`(2023/12 6082.81)
**When** `read_fs`를 호출하며 `caplog`로 경고를 수집한다
**Then**
- 정합성 경고 0건(연간·분기 모두).
- `df_fs_ann.loc["기타유동자산"]`이 `[90403.61, 94464.41, 106174.16, 137745.49]`(허용오차 0.01; = 원 `기타유동자산` + 접힌 행; 감사자 독립 재구현 값), `df_fs_ann.loc["유동금융자산", "2023/12"] == 226909.24`(접기 대상 아님).
- 조작본 1: Balance 연간 `기타유동자산` 2024/12에 +1.0 → 경고 **정확히 1건**, 메시지에 `005930`, `2024/12`, `-1.0`(차이 = `자산 − 소비 자산 계정 합`).
- 조작본 2: Balance 연간·분기에서 `기타유동자산` 행 삭제 → 예외 없이 반환, 경고 메시지 중 하나에 `005930`과 `기타유동자산`이 함께 있음.
- 조작본 3: Balance 연간에서 `자산총계` 행 삭제 → 예외 없이 반환, 경고 메시지 중 하나가 `005930`을 포함하고 정규식 `(^|[^가-힣A-Za-z0-9_])자산([^가-힣A-Za-z0-9_]|$)`(낱말 단위 `자산`)과 행 부재 문구 `행 없음`을 함께 포함한다. 조작본 2의 경고 문구도 같은 `행 없음`을 쓴다(구현은 이 문구를 행 부재 경고의 고정 토큰으로 쓴다).
**되돌림 시 관측값**: 접기를 빼면 경고 **8건** — 연간 `2023/12 6353.93`, `2024/12 368.77`, `2025/12 257.15`, `2026/06 460.00`, 분기 `2025/09 201.71`, `2025/12 257.15`, `2026/03 232.38`, `2026/06 460.00`(모두 `자산` 쪽, 감사자 독립 재구현 값). 가드를 빼면 조작본 1에서 경고 0건. 목적지·합계 부재 처리를 빼면 조작본 2·3에서 `IndexError`/`KeyError`가 `read_fs` 밖으로 샌다.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k ac_wc_007`
**기대 출력**: `7 passed` (긍정 4 + `_contrast` 3)

### AC-WC-008 — 0 행 보충은 명시 목록만 [대조]
**Given** (a) 005930 `C` fixture (b) 조작본: Balance의 `재고자산` 행 `NAME`만 `재고`로 바꿈(FnGuide가 이름을 또 바꾼 상황의 모의 — 레이아웃 표지 `매출액(수익)`은 건드리지 않음) (c) 조작본: Income의 `매출원가` 행 삭제(대시보드 전용 계정)
**When** 각각 `read_fs`를 호출한다
**Then** (a) `관계기업등지분관련투자자산` 행이 연간·분기 두 표에 있고 모든 값이 `0.0`. (b) `재고자산` 행이 **없고**, 경고에 `005930`과 `재고자산`이 함께 있다. (c) `매출원가` 행이 없고, 경고에 `005930`과 `매출원가`가 함께 있다.
**되돌림 시 관측값**: "부재한 필수 계정은 모두 0으로 보충"으로 바꾸면 (b)에서 `재고자산` 행이 생기고 값이 `0.0`.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k ac_wc_008`
**기대 출력**: `4 passed`

### AC-WC-009 — 본문 기반 실패 판정과 코드 검증 [대조]
**Given** (a) 999999: HTTP 200 + 1,668바이트 오류 HTML(본문이 `\r\n\n<!DOCTYPE`로 시작) (b) 005935: HTTP 200 + `data=[]`, 머리글 `YYMM` null (c) 조작본: 005930 `C`의 getFinCashFlow Y 응답 하나에서 VAL3 머리글 `YYMM`만 null(나머지 다섯 응답은 원본 — REQ-WC-002의 응답별 검사가 REQ-WC-005 (b) 정렬 검사보다 먼저 돌아 `ValueError`가 나야 하며 `RuntimeError`이면 FAIL) (d) 신규 상장 모의: 403870 `B`의 연간 세 응답(getFinIncome Y·getFinBalance Y·getFinCashFlow Y) 모두에서 머리글 VAL1 `YYMM`을 null로, VAL1 값을 모두 null로 바꾼 것(결산 기간 3개) (e) 코드 `"00593a"`, `"０05930"`(전각 숫자), `"5930"`
**When** `read_fs`를 호출하고, (a)(b)는 라우터 `GET /api/analysis/{code}`로도 호출한다(`get_dashboard` 캐시는 테스트마다 비움)
**Then** (a)~(d) 모두 `ValueError`이고 메시지에 요청 코드가 있다. (d)의 메시지는 결산 기간이 부족하다는 뜻을 담는다(`기간` 문자열 포함). (e)는 `ValueError`이고 **요청이 0건** 기록된다. 라우터 응답은 (a)(b) 모두 `404`.
**되돌림 시 관측값**: 빈 `data`·null 머리글 검사를 빼면 `read_fs("005935")`가 **`ValueError`를 내지 않는다**(다른 예외로 새거나 예외 없이 반환). 대조 단언은 라우터가 아니라 `read_fs` 수준에서 "`ValueError`가 아님"을 본다 — 라우터 경로는 `read_snapshot("005935")`의 `#cmp_cd` 검사가 따로 `ValueError`(404)를 내므로 리더 검사가 빠져도 GREEN일 수 있어 대조로 쓰지 않는다.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py tests/test_analysis_api_wcomp.py -q -p no:cacheprovider -k ac_wc_009`
**기대 출력**: `8 passed` (read_fs (a)~(e) 5 + 라우터 2 + `_contrast` 1)

### AC-WC-010 — 요청 위생과 전송 실패 [대조]
**Given** `requests.get`을 기록기로 감싸 fixture를 돌려주게 한다
**When** `get_fnguide("005930")`를 호출한다
**Then** 기록된 모든 호출에 `timeout` 키워드가 있고 값이 `0 < timeout <= 10`이며, 헤더에 `User-Agent`, `X-Requested-With`, `Referer`가 있고, 종목 코드는 `params`로 전달된다(URL 경로·쿼리 문자열에 직접 조립되지 않음). 별도로 (가) `requests.get`이 `requests.exceptions.ConnectTimeout`을 내면 `get_fnguide`가 `ConnectionError` 또는 `OSError` 하위 예외를 내고 라우터는 `503` (나) 재무 엔드포인트가 HTTP 500(본문은 정상 JSON)을 돌려주면 `ConnectionError` 또는 `OSError` 하위 예외, 라우터는 `503`.
**되돌림 시 관측값**: `timeout` 인자를 빼면 첫 기록 호출에서 단언 실패(`timeout` 키 없음).
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py tests/test_analysis_api_wcomp.py -q -p no:cacheprovider -k ac_wc_010`
**기대 출력**: `4 passed`

### AC-WC-011 — 스냅샷 둔갑 방지 [대조]
**Given** (a) `Snapshot?cmp_cd=005935` 요청에 사이트가 실제로 돌려준 HTML(`#cmp_cd` = `005930`, `#giName` = `삼성전자`, fixture `snapshot_005935_served_as_005930.html`) (b) `#cmp_cd`가 없는 HTML(999999 요청의 `Object moved` 본문 fixture)
**When** `read_snapshot("005935")`, `read_snapshot("999999")`를 호출한다
**Then** 둘 다 `ValueError`이고 메시지에 각 요청 코드가 있다.
**되돌림 시 관측값**: `#cmp_cd` 검사를 빼면 (a)가 예외 없이 `report["종목명"] == "삼성전자"`를 반환한다.
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_snapshot.py -q -p no:cacheprovider -k ac_wc_011`
**기대 출력**: `3 passed`

### AC-WC-012 — report 키·값, 종목명, 자기주식 [대조]
**Given** `Snapshot_005930.html`, `Snapshot_403870.html` 축소 fixture, 그리고 005930 스냅샷에서 `자사주` 행을 지운 조작본
**When** `read_snapshot`을 호출하고, 005930은 재무 fixture와 함께 `analyze_dashboard("005930")`까지 호출한다
**Then** 005930 `report`가 다음과 같다.
| 키 | 값 |
|---|---|
| `시가총액(상장예정포함,억원)` | `17748495` |
| `발행주식수(보통주)` | `5846278608` |
| `발행주식수(우선주)` | `802371203` |
| `자기주식` | `133670794` (정확히 `자사주`인 행의 주식수 칸) |
| `베타(1년)` | `1.27893` |
| `종목명` | `삼성전자` |
| `Summary` | `1969년`을 포함 |

`PER`, `12M PER`, `업종 PER`, `PBR`, `배당수익률` 키가 존재한다. 403870 `report["종목명"] == "HPSP"`. `analyze_dashboard("005930").company_name == "삼성전자"`(API 수준 — 화면 표시는 `stock.name`을 쓰므로 바뀌지 않음, spec D9). 조작본(정확히 `자사주`인 행만 삭제, `자사주(자사주+자사주신탁)` 행은 남김)의 `report["자기주식"] == 0`. **판별력은 이 조작본이 맡는다**: 관측한 세 스냅샷(005930·403870·105560) 모두에서 두 행의 주식수가 같아(005930 133,670,794 / 403870 881,247 / 105560 3,581,623 — `자사주(자사주+자사주신탁)` 행은 첫 칸이 보유자 수 `1`이고 둘째 칸이 주식수) 원본만으로는 "정확한 행"을 구별할 수 없다. 접두어 일치 구현은 조작본에서 `0`이 아닌 `133670794` 또는 `1`을 낸다.
**되돌림 시 관측값**: `종목명`을 채우지 않으면 `company_name == "005930"`(`dashboard.py:934`의 코드 대체값 — 현재 API 동작).
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_snapshot.py -q -p no:cacheprovider -k ac_wc_012`
**기대 출력**: `5 passed`

### AC-WC-013 — 8-튜플 계약과 컨센서스 미요청 [대조]
**Given** 005930 전체 fixture와 요청 기록기
**When** `inspect.signature(get_fnguide)`를 보고 `get_fnguide("005930")`을 호출한다
**Then** 매개변수 이름 목록이 `["code"]`, 반환 길이 8, 위치 2·3·4가 `pd.DataFrame`이면서 `.empty`, 위치 6이 `"IFRS(연결)"`, 위치 7이 `pd.DataFrame`. 기록된 URL 중 `urllib.parse.urlparse(url).hostname == "comp.fnguide.com"`인 것이 0건, `01_06`을 포함한 것이 0건이며, 기록된 모든 URL의 `urlparse(url).hostname`이 `"wcomp.fnguide.com"`이고, 총 요청 수가 8건 이하(연간 Income `C`·`B` 판정 2회 — 결정된 유형의 응답은 데이터로 재사용 — + 나머지 재무 5회 + 스냅샷 1회 = 8).
호스트 판정은 부분 문자열이 아니라 **파싱한 호스트 이름의 정확 비교**다 — 새 호스트 `wcomp.fnguide.com`은 문자열 `comp.fnguide.com`을 품고 있으므로 `"comp.fnguide.com" in url`로 쓰면 정상 요청 전부가 위반이 된다(plan-audit iteration 4 D2; 판정식 실행 결과는 progress.md v0.2.3 자체 점검).
**되돌림 시 관측값**: `read_consensus` 호출을 되살리면 기록된 URL에 `comp.fnguide.com/SVO2/json/data/01_06/`이 나타난다(호스트 이름 `comp.fnguide.com`, `01_06` 포함 — 두 단언 모두 실패).
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_snapshot.py -q -p no:cacheprovider -k ac_wc_013`
**기대 출력**: `2 passed`

---

## §C 불변 단언 (회귀 방지 — 대조 아님)

### AC-WC-014 — 금융 레이아웃은 200, 503 아님 [불변]
**Given** 105560 fixture(Income LVL0에 `매출액(수익)` 없음)와 001750 fixture(`B` 선택, 증권사)
**When** `read_fs`를 호출하고, 라우터 `GET /api/analysis/{code}`로도 호출한다
**Then** `read_fs`가 예외 없이 4-튜플을 반환하고 `df_fs_ann` 인덱스에 `매출액`이 없다(별칭 미적용). 라우터 응답은 `200`이며 `business_performance`, `health_indicators`, `balance_sheet`, `rate_decomposition`, `profit_waterfall`, `trend_signals`, `five_questions`가 모두 `null`이다. 105560의 `company_name`은 `KB금융`, 001750의 `company_name`은 비어 있지 않고 `001750`과 다르다(001750 스냅샷은 plan 단계에서 캡처하지 않아 회사명 문자열을 고정하지 않는다).
**명령**: `$PY -m pytest tests/fnguide/test_wcomp_reader.py tests/test_analysis_api_wcomp.py -q -p no:cacheprovider -k ac_wc_014`
**기대 출력**: `4 passed`
**비고**: `activity_ratios`는 현행 `_calc_activity_ratios`가 금융 레이아웃에서도 값이 모두 `null`인 객체를 돌려주므로(research.md §R3 각주) 단언하지 않는다.

---

## §D 게이트

### AC-WC-015 — 범위 불변과 스위트 무결성 [게이트]
**Given** run 단계 착수 시점의 기준 커밋 `BASE`(run 착수 직전 `git rev-parse HEAD`, progress.md §E.2에 기록)
**When** 다음 여섯을 실행한다(넷째 명령은 참고용이며, 그 판정은 아래 4번 항목의 AST 프로브가 맡는다)
```bash
git diff --stat "$BASE" -- fnguide/analysis.py fnguide/dashboard.py fnguide/analyzer.py fnguide/parser.py fnguide/__init__.py backend/routers/analysis.py backend/schemas/analysis.py backend/services/analysis_service.py frontend/
$PY -m pytest tests/fnguide tests/test_analysis_api.py tests/test_analysis_api_wcomp.py -q -p no:cacheprovider
$PY -m pytest tests/fnguide tests/test_analysis_api.py -q -p no:cacheprovider -m "live or slow" -rs
grep -nE "//comp\.fnguide\.com" fnguide/crawler.py
F=tests/fnguide/fixtures/wcomp/README.md; test -s "$F" && grep -qE 'https://wcomp\.fnguide\.com/' "$F" && grep -qE '20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$F" && echo README_OK
grep -nE "open\([^)]*['\"](w|a|x)b?\+?['\"]|\.to_(csv|pickle|parquet|json|excel|feather|hdf|sql)\(|\.write_(text|bytes)\(|(json|pickle)\.dump\(|shelve\.|sqlite3\." fnguide/crawler.py fnguide/account_alias.py; echo "exit=$?"
```
**Then**
1. 첫 명령의 출력이 비어 있다.
2. 둘째 명령: `failed`·`error` 0건, passed 수 ≥ 101 + (§B·§C 기대 출력 하한의 합 1+3+8+2+3+9+7+4+8+4+3+5+2+4 = 63) = **164**. run 단계는 이 합을 손으로 옮기지 말고 §B·§C의 "기대 출력" 줄에서 다시 더해 확인한다(교훈 #10). 기준선 101 passed / 94 deselected는 2026-10-07 plan 단계 실측이다(research.md §R1 F-01).
3. 셋째 명령(라이브, 네트워크 필요): `error` 0건, `failed` 0건, **skipped ≤ 1**. 허용되는 skip 사유는 하나뿐이다 — `tests/fnguide/test_analysis.py:167`의 `"연도 컬럼이 3개 미만"`(데이터 의존). `-rs`가 출력하는 skip 사유가 이 하나가 아니면 FAIL이다. 이 상한이 성립하려면 M6의 세 과제가 모두 끝나야 한다: (i) `TestReadConsensus`(`test_crawler.py:177-196`, 데코레이터 177·클래스 178~196) **삭제** — 남기면 옛 호스트 요청이 error를 내고, skip으로 바꾸면 허용 목록 밖이라 FAIL. (ii) `IFRS(별도)` 후보 목록 `["003550", "015760", "034020"]`(`test_crawler.py:83`, `test_analysis.py:234`)을 실측 별도 종목 `["403870", "330590", "476830"]`(첫 성공 종목 사용)으로 교체 — 옛 후보는 새 선택 규칙에서 별도로 판정되지 않아 `"IFRS(별도) 종목을 찾지 못함"` skip 4건(`test_crawler.py:96, :103`, `test_analysis.py:248, :258`)을 낸다. (iii) `test_analysis.py:255-268`(`test_characterize_controlling_profit_equals_net_income`) 다시 쓰기 — 지금은 `yearly_cols[-1]`(Trailing 12M으로 덮어쓴 열, 403870에서 857.27)과 `df_fs_ann["당기순이익"]`의 같은 열(누적 YTD, 489.69)을 비교하므로 마지막 연간 열이 부분 연도면 항상 실패한다. 이전에는 별도 후보가 늘 skip이라 드러나지 않았다. 비교 열을 Trailing 보정이 없는 완결 연도 `yearly_cols[-2]`로 바꾼다(403870에서 양쪽 모두 726.62 — 오케스트레이터·감사자 확인). 근거: 현행 테스트의 `pytest.skip(` 실제 호출은 36곳이다(`command grep -rnE --include='*.py' "^\s*pytest\.skip\(" tests/fnguide | wc -l` → `36`, 2026-10-07 재실행. 줄 시작에 앵커하지 않은 이전 프로브의 37에는 `conftest.py:9` docstring 언급 1건이 섞여 있었다). 이 테스트들이 예외를 `pytest.skip`으로 삼키므로 skip 상한이 없으면 장애가 "skipped"로 숨는다. 수정 전 기준선은 `crawler.py:187`에서 25 errors였다(오케스트레이터 조사).
4. 넷째 명령은 판정에 쓰지 않고 참고로만 남긴다(`read_consensus`가 남아 있으므로 그 상수 줄이 나온다. 패턴 앞의 `//` 때문에 새 호스트 `wcomp.fnguide.com` 줄은 나오지 않는다). 판정은 다음 AST 프로브로 한다. 검사 대상은 **문자열 상수 노드**뿐이다 — docstring은 제외하고(주석은 AST에 없으므로 자동 제외), 모듈 최상위의 일반 대입·주석 달린 대입(`AnnAssign`)·다른 모듈에서 가져온 이름(`from … import`)을 따라간다. **docstring이나 주석에서 옛 호스트를 언급하는 것은 허용된다.** 옛 호스트 판정은 부분 문자열이 아니라 **파싱한 호스트 이름의 정확 비교**(`urllib.parse.urlparse(…).hostname == "comp.fnguide.com"`, 스킴이 없는 문자열은 `//`를 붙여 파싱)이며, 문자열 상수 분기와 `from … import` 분기가 같은 판정 함수 `old`를 쓴다. 그래서 **새 호스트 `wcomp.fnguide.com`은 옛 호스트로 잡히지 않는다** — v0.2.2까지의 부분 문자열 판정(`H in value`)은 `wcomp.fnguide.com`을 쓰는 올바른 구현도 위반으로 판정했다(plan-audit iteration 4 D1). 출력은 (옛 호스트 문자열을 담은 모듈 이름 목록, 그런 문자열이나 이름을 쓰는 최상위 함수 목록)이다. 판정 대상 파일은 첫 인자로 바꿀 수 있고, 인자가 없으면 `fnguide/crawler.py`다.
```bash
$PY - <<'EOF'
import ast, importlib, sys
from urllib.parse import urlparse
H = "comp.fnguide.com"
p = sys.argv[1] if len(sys.argv) > 1 else "fnguide/crawler.py"
def old(v):
    if not isinstance(v, str): return False
    v = v.strip()
    try: return urlparse(v if "://" in v else "//" + v).hostname == H
    except ValueError: return False
s = open(p, encoding="utf-8").read(); t = ast.parse(s)
docs = {id(n.body[0].value) for n in ast.walk(t)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
hc = lambda node: any(isinstance(n, ast.Constant) and old(n.value) and id(n) not in docs for n in ast.walk(node))
tainted = set()
for n in t.body:
    if isinstance(n, ast.Assign) and hc(n):
        tainted |= {x.id for x in n.targets if isinstance(x, ast.Name)}
    elif isinstance(n, ast.AnnAssign) and hc(n) and isinstance(n.target, ast.Name):
        tainted.add(n.target.id)
    elif isinstance(n, ast.ImportFrom):
        try: mod = importlib.import_module(("fnguide." if n.level else "") + (n.module or ""))
        except Exception: continue
        tainted |= {a.asname or a.name for a in n.names if old(getattr(mod, a.name, None))}
print(sorted(tainted), sorted(n.name for n in t.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
      and (hc(n) or any(isinstance(x, ast.Name) and x.id in tainted for x in ast.walk(n)))))
EOF
```
   기대 출력(구현 후): `['_CONS_B_URL', '_CONS_D_URL'] ['read_consensus']` — 옛 호스트는 호출되지 않는 `read_consensus`와 그 두 상수에만 남고, `read_fs`·`read_snapshot`·`get_fnguide`와 보조 함수에는 없다(REQ-WC-001 범위와 일치). 이 출력에 도달하려면 M3·M5가 `_FS_URL`·`_SNAP_URL`을 삭제해야 한다. plan 단계 실측(progress.md v0.2.3 자체 점검에 축자 기록): (가) 현행 코드 → `['_CONS_B_URL', '_CONS_D_URL', '_FS_URL', '_SNAP_URL'] ['read_consensus', 'read_fs', 'read_snapshot']`(수정 전이므로 불일치가 정상, v0.2.2 프로브와 같은 출력) (나) `wcomp.fnguide.com`만 쓰고 `_CONS_D_URL`·`_CONS_B_URL`·`read_consensus`를 남긴 준수 가짜 크롤러 → 기대 출력과 정확히 같음 (다) `read_fs`가 옛 호스트 URL을 직접 쓰는 위반 가짜 크롤러 → `['_CONS_B_URL', '_CONS_D_URL'] ['read_consensus', 'read_fs']`(옛 호스트 사용을 여전히 잡음).
5. 다섯째 명령의 출력이 정확히 `README_OK`다(REQ-WC-016 "출처와 캡처 시각은 그 디렉터리의 README에"): README가 비어 있지 않고, 원본 URL(`https://wcomp.fnguide.com/…`)과 `YYYY-MM-DD` 형식의 캡처 날짜를 각각 한 번 이상 담는다. 출력이 비면 FAIL이다. plan 단계에서는 README가 아직 없어 출력이 비는 것이 정상이며, 판정 방식은 출처·날짜를 담은 표본에서 `README_OK`, 제목만 있는 표본에서 빈 출력으로 확인했다(progress.md v0.2.3 자체 점검).
6. 여섯째 명령의 출력이 정확히 `exit=1` 한 줄이다(REQ-WC-015 "TTL 캐시 밖에 저장하지 않음"의 정적 판정): `fnguide/crawler.py`·`fnguide/account_alias.py` 어디에도 쓰기 모드 `open(…, "w"|"a"|"x"…)`, `DataFrame.to_csv`·`to_pickle` 등 `to_*` 내보내기, `write_text`·`write_bytes`, `json.dump`·`pickle.dump`, `shelve`, `sqlite3`가 없다. 일치하는 줄이 나오거나 `exit=2`(파일 없음 — `account_alias.py`는 M2가 만든다)이면 FAIL이다. 이는 정적 검사라 동적으로 조립한 쓰기 경로까지 증명하지는 못한다(잔여 위험). plan 단계 실측: 명령을 그대로 실행하면 `account_alias.py`가 아직 없어 `exit=2`(M2 전이므로 정상), 현행 `crawler.py`만 넣으면 일치 0건(`exit=1`), 네 가지 쓰기 형태를 담은 대조 파일은 네 줄 모두 일치(`exit=0`).

### AC-WC-016 — 라이브 HTTP 결과표와 되돌림 관측 기록 [게이트 · 라이브]
**Given** 백엔드를 올바른 실행환경으로 재시작한다(메모리 `project_server_runtime_env.md`: cwd와 venv가 다름)
```bash
cd /Users/byunjungwon/Dev/my-project-01/my_chart && \
/Users/byunjungwon/Dev/my_chart/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```
**When** 다른 터미널에서 다음을 실행한다
```bash
for c in 403870 005930 330590 001750 105560 005935 999999; do
  printf "%s " "$c"
  curl -s -o /tmp/wc_$c.json -w '%{http_code} ' "http://localhost:8000/api/analysis/$c"
  jq -c '[.company_name, (.business_performance|type), (.health_indicators|type), (.five_questions|type)]' /tmp/wc_$c.json 2>/dev/null || echo
done
```
**Then** 출력이 다음과 일치한다(`type`은 jq의 `"object"`/`"null"`).

| 코드 | 상태 | company_name | business_performance | health_indicators | five_questions |
|---|---|---|---|---|---|
| 403870 | `200` | `HPSP` | `object` | `object` | `object` |
| 005930 | `200` | `삼성전자` | `object` | `object` | `object` |
| 330590 | `200` | (비어 있지 않음, 코드와 다름) | `object` | `object` | `object` |
| 001750 | `200` | (비어 있지 않음, 코드와 다름) | `null` | `null` | `null` |
| 105560 | `200` | `KB금융` | `null` | `null` | `null` |
| 005935 | `404` | — | — | — | — |
| 999999 | `404` | — | — | — | — |

그리고 되돌림 관측 기록이 대조 AC 집합과 **정확히 같다**.
```bash
diff <(grep -oE '^#### RED 관측 — AC-WC-[0-9]{3}' .moai/specs/SPEC-FNGUIDE-WCOMP-001/progress.md | grep -oE 'AC-WC-[0-9]{3}' | sort -u) \
     <(printf 'AC-WC-%03d\n' $(seq 1 13))
```
기대 출력: 없음(종료 코드 0). 대조 AC는 AC-WC-001(수정 전 RED)과 AC-WC-002~013(소스 되돌림 RED)의 13개다. 관측하지 못한 AC는 머리글을 만들지 말고 §E.2 Gaps에 미검증으로 적는다 — 이 경우 이 AC는 FAIL이며 sync 진입 전 사용자 판단이 필요하다.
**비고**: 승인 계획은 001750을 "섹션 채워짐"으로 예상했으나 계측상 금융 레이아웃이다(spec.md D3, plan.md §B.1 C-1). 라이브 결과가 이 표와 다르면 run 단계는 수정하지 말고 blocker로 보고한다.

---

## §E Definition of Done

- [ ] AC-WC-001 ~ AC-WC-016 전부 PASS, 기대 출력이 progress.md §E.2에 축자로 기록됨
- [ ] 대조 AC 13개의 RED 관측이 §E.2에 축자 기록(AC-WC-016의 집합 비교 통과), 복원 후 `git status --short` 출력 첨부
- [ ] 커버리지: `coverage run --source=fnguide -m pytest tests/fnguide -q -p no:cacheprovider` → `coverage report --include='fnguide/crawler.py,fnguide/account_alias.py'`에서 두 파일 각 85% 이상(교훈 #9의 측정 함정: `--source`에는 패키지명을 준다). 85% 미만이면 미달 줄을 §E.2에 적는다
- [ ] plan.md §F.1 M1 확인 과제(V-1 응답 헤더, V-2 첫 행 정체, V-3 결산 직후 열 모양, V-4 충당부채 별칭) 결과가 §E.2에 기록됨
- [ ] 수용한 잔여 위험(수정 전후 수치 비교 불가)의 완화 조치 기록: 정합성 가드 경고 0건(AC-WC-007), 지배주주지분 = 주주몫 교차 확인(AC-WC-002), 그리고 **005930 핵심 지표(영업이익률, 부채비율, 이자보상배율)를 FnGuide 화면 값과 눈으로 대조한 수치**를 run 완료 시 progress.md §E.2에 기록(기계 판정 아님)
- [ ] 수동 확인(기록만): 브라우저에서 HPSP(403870) 재무 분석 모달이 오류 없이 열림
- [ ] 005930 캐시 미스 1회 소요 시간 기록(성능 목표 없음, 기준선 확보용)
