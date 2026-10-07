# SPEC-FNGUIDE-WCOMP-001 — 조사 기록 (research)

> plan 단계에서 관측한 사실과 그 관측 방법을 모은다. spec.md의 결정(D1~D9)과 acceptance.md의 기대값은 모두 이 문서의 어느 행을 근거로 한다. 교훈 #10에 따라 코드베이스에 대한 주장마다 프로브 명령을 함께 적었다.

## §R0 표본 위치와 수명 경고

조사 표본은 세션 전용 임시 디렉터리에 있다.

```
SP=/private/tmp/claude-501/-Users-byunjungwon-Dev-my-project-01-my-chart/d73171bb-e515-41a5-9d94-8b421935fe6b/scratchpad
$SP/raw/       getFin{Income,Balance,CashFlow}_<code>_<Y|Q>_<C|B|P|I>.json  (재무 JSON 원본), page_<code>.html
$SP/samples/   축소본 9개 (005930 Y C trim8, 403870 C 전체 null, 330590 반기, 105560 금융, 005935 빈 dataset, 999999 오류 HTML 등)
$SP/html/      Snapshot_{005930,403870,105560}.html, bad_005935.html(삼성전자로 둔갑), bad_999999.html(302 본문), Consensus_*.html, FinanceRatio_*.html
$SP/json/      컨센서스·스냅샷 계열 JSON (범위 밖이지만 후속 복원용 참고)
$SP/fs.html    옛 호스트가 돌려주는 1,829바이트 안내 페이지
$SP/specprobe/ plan 단계 프로브 스크립트(hdr.py, names.py, proto.py, proto2.py, tie.py, missing.py, labeltable.py, alias.txt)
```

**[위험] 이 디렉터리는 OS 임시 경로라 사라질 수 있다.** run 단계 M1은 가장 먼저 필요한 파일을 `tests/fnguide/fixtures/wcomp/`로 복사해야 한다. 이미 사라졌다면 같은 URL을 라이브로 한 번 다시 받아 캡처하고, 받은 시각을 progress.md §E.2에 적는다. 표본에 **없는** 것(001750의 Balance·CashFlow, 330590의 Q Balance·CashFlow, 001750·330590 스냅샷)은 어차피 M1에서 새로 받아야 한다.

---

## §R1 계측으로 확정한 사실

| # | 주장 | 관측 방법 (명령) | 결과 |
|---|---|---|---|
| F-01 | 기본 스위트 기준선은 101 passed / 94 deselected | `cd repo && /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide tests/test_analysis_api.py -q -p no:cacheprovider` | `101 passed, 94 deselected, 1 warning in 0.50s` (2026-10-07 plan 단계 직접 실행) |
| F-02 | 라이브·느린 테스트는 94개 | 같은 명령 + `--collect-only -m "live or slow"` | `94/195 tests collected (101 deselected)`. "라이브 실행 시 `crawler.py:187`에서 25 errors"는 오케스트레이터 조사 결과이며 **plan 단계에서 다시 돌리지 않았다** |
| F-03 | 장애 경로는 `crawler.py:187` → `parser.py:38` | 코드 열람: `crawler.py:182-187`(`requests.get` 후 `tables[0]`), `parser.py:38`(`th[0][0]`). 라이브 재현(005930·403870)은 오케스트레이터 조사 결과 | 코드상 표가 1개면 `table_parsing(tables[0])`의 `th[0]`가 `<th>` 없는 행이라 빈 목록 → `IndexError` |
| F-04 | 옛 안내 페이지는 1,829바이트, 표 1개 | `ls -la $SP/fs.html`; `grep -c "<table" $SP/fs.html` | `1829`; `1`. `<title>FnGuide,Your Best Financial Guide`, 본문에 `wcomp.fnguide.com` |
| F-05 | `df_snap`·`df_snap_ann`·`df_cons`는 소비처 없음; `backend/`는 `fnguide.analyzer`·`fnguide.crawler`를 쓰지 않음 | `grep -rnE "fnguide\.(analyzer|crawler)|get_fnguide|analyze_comp" backend; echo rc=$?` (v0.2.0 교체 — 이전 프로브는 50줄 넘게 출력해 판정이 어려웠다) | `rc=1`(0건). `get_fnguide` 호출부는 `dashboard.py:928`, `analyzer.py:159` 둘뿐이며 둘 다 위치 3·4·5를 `_`로 버림. 별개로 `rim_fnguide/rim_fnguide_ver20.py:2706`에 이름만 같은 다른 `get_fnguide(comp_name)`이 있다 — 이 SPEC의 대상이 아니다 |
| F-06 | 옛 크롤러는 `종목명`을 채운 적이 없다 | `grep -n "종목명" fnguide/crawler.py; echo rc=$?` | `rc=1`(0건). 소비처는 `dashboard.py:934 report.get("종목명", code)` |
| F-07 | `consol_typ` B = P = I | `cmp raw/getFinIncome_005930_Y_B.json raw/getFinIncome_005930_Y_P.json` (I, 403870도 같은 방식) | 4쌍 모두 차이 없음(`cmp` 출력 없음, 종료 0) |
| F-08 | 현재 요청에 타임아웃이 없다 | `grep -n "timeout" fnguide/crawler.py; echo rc=$?` | `rc=1`. `requests.get(snap_url)`(`:58`), `requests.get(fs_url)`(`:182`), `requests.get(json_url)`(`:236`) |
| F-09 | 머리글 모양 | `$SP/specprobe/hdr.py $SP/raw` (CD·YYMM·LINE 덤프) | Income Y/Q: 6열(VAL4 `YYYY/MM (최근분기)` LINE=1, VAL5 `YYYY/MM (전년동기)`, VAL6 `전년동기대비(%)`). Balance·CashFlow: 4열. 330590 Y: `2024/12, 2025/06, 2025/12, 2026/06`, 표지 없음, LINE 전부 0, VAL5 `2025/12 (전년동기)`. 330590 Q Income VAL4도 표지 없음 |
| F-10 | 레이아웃은 Income LVL0 `매출액(수익)` 유무로 갈린다 | LVL0 이름 덤프(§R3 원자료) | `매출액(수익)` 있음: 000220·002360·005670·005930·024950·025440·033340·034730·038460·064400·108380·298380·330590·403870·454910·476830·491000. 없음: 000810(`영업수익`부터)·001750·006800·029780·055550·105560. Balance LVL0은 일반이 `자산총계/부채총계/자본총계`, 금융이 `자산/부채/자본` |
| F-11 | 선택 규칙 입력값 | `getFinIncome_<code>_Y_<C|B>`의 `당기순이익` 행 덤프 | 403870 C 전부 null, B `804.32, 862.80, 726.62, 489.69`. 001750 C `351.04, 387.98, null, null`, B `347.58, 387.98, 565.71, 383.34`(C의 VAL1이 B와 다름 — 연결 실적이 실제로 있던 해). 005930 C `154871.00, 344513.51, 452068.05, 1188497.33` |
| F-12 | 330590의 VAL5는 직전 기간과 같다 | 같은 덤프의 `매출액(수익)` | Y B `656.29, 699.54, 708.80, 821.10, 708.80, 15.84` — VAL5 = VAL3. Q 합 389.34 + 431.76 = 821.10 = Y VAL4(6개월 회계기간) |
| F-13 | 없는 종목·잘못된 코드는 200 + HTML | `hdr.py` 결과의 `NOTJSON`; `cmp raw/getFinIncome_999999_Y_C.json raw/getFinIncome_12345_Y_C.json` | 999999·12345·ABCDEF·117930 모두 1,668바이트 HTML, 999999와 12345는 바이트 동일, 본문 `해당 종목이 없거나`. **본문이 `\r\n\n<!DOCTYPE`로 시작** — 선행 공백을 지운 뒤 `<`를 봐야 한다(spec REQ-WC-002 반영) |
| F-14 | 우선주·ETF는 200 + 빈 dataset | `hdr.py` | 005935·069500·빈 코드: `rows=0`, VAL1~VAL5 `YYMM` null, VAL6만 `전년동기대비(%)` |
| F-15 | 스냅샷은 우선주 요청에 삼성전자를 내준다 | `grep -o 'id="cmp_cd"[^>]*\|id="giName"[^<]*' $SP/html/bad_005935.html` | `giName">삼성전자`, `cmp_cd" value="005930"` |
| F-16 | 스냅샷 기준점 | `grep -o 'id="cmp_cd"…\|id="master_chk"…\|id="giName"…' $SP/html/Snapshot_<code>.html` | 005930: C·삼성전자·005930 / 403870: P·HPSP·403870 / 105560: C·KB금융·105560. 005930 표: 시가총액(상장예정포함) `17,748,495`, `52주베타` `1.27893`, 시가총액(보통주) `16,135,729`, 발행주식수 `5,846,278,608/ 802,371,203`, `자사주` 행 `133,670,794`(같은 페이지에 `자사주(자사주+자사주신탁)` 행이 따로 있음 — 정확히 `자사주`인 행만 쓴다), 요약 첫 문장 `동사는 1969년 설립된…` |
| F-17 | 999999 스냅샷은 302 | `head -c 400 $SP/html/bad_999999.html` | `Object moved to /Error/InvalidCompany?…` (193바이트). `requests`는 리디렉션을 따라가므로 최종 페이지에 `#cmp_cd`가 없거나 다를 것 — 추정, 미관측 |
| F-18 | `read_consensus`는 패키지 공개 이름이다 | `grep -n "read_consensus" fnguide/__init__.py` | `:31`, `:51` (`__all__`) |
| F-19 | `stk_typ`은 업종 구분에 못 쓴다 | `grep -n stk_typ $SP/html/*.html` | 삼성전자·우선주 둔갑 페이지·컨센서스 페이지 모두 `value="1"`. KB금융 페이지도 1이라는 주장은 오케스트레이터 조사 결과 |
| F-20 | 기본 실행은 라이브 테스트를 뺀다 | `grep -n "addopts" pyproject.toml` | `:59 addopts = '-m "not live and not slow"'` |
| F-21 | 손익계산서·대차대조표·현금흐름표 사이에 공유 행 이름이 손익↔현금흐름에만 있다 (이어 붙이는 순서의 동치 근거, spec D4) | 연간 세 재무제표의 정규화 이름 집합 교집합 계산(005930 C, 403870 B, 330590 B, 105560 C) | 네 종목 모두 `I∩B = []`, `B∩C = []`. 그래서 손익·대차의 상대 순서는 `.loc`·`.iloc[0]` 결과를 바꾸지 않는다. 옛 코드 순서는 변수 이름(`crawler.py:194-195`, 대차→손익→현금)과 docstring(`crawler.py:174`, 0번 표 = 연간손익)이 서로 달라 확정 불가 |
| F-22 | 프론트엔드 모달 회사명은 API `company_name`이 아니다 | `grep -rn "companyName={" frontend/src`; `grep -n "companyName" frontend/src/components/AnalysisModal.tsx`; `grep -rn "company_name" frontend/src` | `ChartCell.tsx:428,443` `companyName={stock.name}`; `AnalysisModal.tsx:765` `{companyName}` 렌더; `company_name`은 `types/analysis.ts:91` 타입 선언 1건뿐. v0.1.0의 "모달 회사명이 코드로 보였다"는 주장은 철회 |
| F-23 | 충당부채 계층 | `P_AC_CODE`와 이름에 `충당부채`가 든 행 덤프(005930 C Y Balance) | `[('131580','유동종업원급여충당부채'),('131580','단기충당부채'),('130010','비유동종업원급여충당부채'),('130010','장기충당부채')]` — run M1 V-4가 403870에도 재확인 |

---

## §R2 옛 계정명 → 코드 위치 → 필수/선택 → 새 응답 대응표

**생성 방법**: 손으로 옮기지 않고 `$SP/specprobe/labeltable.py`가 `grep -nE '(df_fs_ann|df_fs_quar)\.loc\["…"|_safe_loc\(df_fs_ann, "…"|base_series\.at\["…"'`로 코드에서 계정명을 뽑고, `raw/`의 005930 C·105560 C 응답과 대조해 만들었다.

**구분 기준**
- `hard` — 이름이 없으면 해당 계산 블록이 `KeyError`로 끝나는 위치. `analysis.py`의 `hard`가 하나라도 없으면 `dashboard.py:954-975`의 try가 Sections 2–7을 모두 `None`으로 만든다. `dashboard.py:293-295`의 `hard`가 없으면 Section 1이 `None`.
- `soft` — `_safe_loc`, `try/except KeyError`로 감싸 없어도 대체값으로 진행하는 위치.
- `hard*` — `fnguide/analyzer.py`(`analyze_comp`) 안의 필수 참조. `/api/analysis` 경로 밖(§R1 F-05)이지만 `report` 키·`account_type` 분기를 지키기 위해 함께 적는다.

**프로브의 사각지대(교훈 #10)**: 이 정규식은 문자열 리터럴로 직접 쓴 계정명만 본다. `dashboard.py:622`의 `df_fs_ann.loc[row, c]`처럼 변수로 넘기는 경우는 못 본다 — 그 호출부(`dashboard.py:645 _slope_for_df_fs("매출액")`)를 따로 읽어 `매출액` 하나뿐임을 확인했다. 또 `df_profit.loc[...]` 같은 파생 프레임 참조가 같은 줄에 걸리면 중복 줄 번호가 생겨, 스크립트에서 (파일, 줄) 단위로 중복을 지웠다.

| 옛 계정명 | 코드 위치 | 구분 | 새 응답 일반 레이아웃(005930 C) | 금융 레이아웃(105560 C) |
|---|---|---|---|---|
| `매입채무및기타유동채무` | analysis.py:65, dashboard.py:821 | hard/soft | 별칭 ← `매입채무및기타채무` | 부재 |
| `유동종업원급여충당부채` | analysis.py:66 | hard | 원명 그대로 (1행) | 부재 |
| `기타단기충당부채` | analysis.py:67 | hard | 별칭 ← `단기충당부채` | 부재 |
| `당기법인세부채` | analysis.py:68 | hard | 별칭 ← `당기법인세부채(미지급법인세)` | 부재 |
| `기타유동부채` | analysis.py:69 | hard | 원명 그대로 (1행) | 부재 |
| `장기매입채무및기타비유동채무` | analysis.py:70 | hard | 별칭 ← `장기매입채무및기타채무` | 부재 |
| `비유동종업원급여충당부채` | analysis.py:71 | hard | 원명 그대로 (1행) | 있음 |
| `기타장기충당부채` | analysis.py:72 | hard | 별칭 ← `장기충당부채` | 부재 |
| `이연법인세부채` | analysis.py:73 | hard | 원명 그대로 (1행) | 있음 |
| `장기당기법인세부채` | analysis.py:74 | hard | 별칭 ← `장기당기법인세부채(미지급법인세)` | 부재 |
| `기타비유동부채` | analysis.py:75 | hard | 원명 그대로 (1행) | 부재 |
| `단기사채` | analysis.py:79, analyzer.py:220 | hard/hard* | 원명 그대로 (1행) | 부재 |
| `단기차입금` | analysis.py:80, analyzer.py:221 | hard/hard* | 원명 그대로 (1행) | 부재 |
| `유동성장기부채` | analysis.py:81 | hard | 원명 그대로 (1행) | 부재 |
| `유동금융부채` | analysis.py:82, analyzer.py:222 | hard/hard* | 원명 그대로 (1행) | 부재 |
| `사채` | analysis.py:83, analyzer.py:223 | hard/hard* | 원명 그대로 (1행) | 부재 |
| `장기차입금` | analysis.py:84, analyzer.py:224 | hard/hard* | 원명 그대로 (1행) | 부재 |
| `비유동금융부채` | analysis.py:85 | hard | 원명 그대로 (1행) | 부재 |
| `기타포괄손익누계액` | analysis.py:89 | hard | 별칭 ← `기타포괄이익누계액` | 부재 |
| `이익잉여금(결손금)` | analysis.py:89 | hard | 별칭 ← `이익잉여금` | 있음 |
| `자본금` | analysis.py:93 | hard | 원명 그대로 (1행) | 있음 |
| `신종자본증권` | analysis.py:94 | hard | 원명 그대로 (1행) | 있음 |
| `자본잉여금` | analysis.py:95 | hard | 원명 그대로 (1행) | 있음 |
| `기타자본` | analysis.py:96 | hard | 원명 그대로 (1행) | 있음 |
| `비지배주주지분` | analysis.py:100 | soft (try 99-102) | 원명 그대로 (1행) | 있음 |
| `매각예정으로분류된처분자산집단에포함된부채` | analysis.py:105 | hard | 별칭 ← `매각예정으로분류된처분자산에포함된부채` | 부재 |
| `기타금융업부채` | analysis.py:106 | hard | 원명 그대로 (1행) | 있음 |
| `유형자산` | analysis.py:115 | hard | 원명 그대로 (1행) | 있음 |
| `무형자산` | analysis.py:116 | hard | 원명 그대로 (1행) | 있음 |
| `비유동생물자산` | analysis.py:117 | hard | 원명 그대로 (1행) | 부재 |
| `재고자산` | analysis.py:121, dashboard.py:820 | hard/soft | 원명 그대로 (1행) | 부재 |
| `유동생물자산` | analysis.py:122 | hard | 원명 그대로 (1행) | 부재 |
| `매출채권및기타유동채권` | analysis.py:123, dashboard.py:819 | hard/soft | 별칭 ← `매출채권및기타채권` | 부재 |
| `당기법인세자산` | analysis.py:124 | hard | 별칭 ← `당기법인세자산(선급법인세)` | 부재 |
| `기타유동자산` | analysis.py:125 | hard | 원명 그대로 (1행) | 부재 |
| `장기매출채권및기타비유동채권` | analysis.py:126 | hard | 별칭 ← `장기매출채권및기타채권` | 부재 |
| `이연법인세자산` | analysis.py:127 | hard | 원명 그대로 (1행) | 있음 |
| `장기당기법인세자산` | analysis.py:128 | hard | 원명 그대로 (1행) | 부재 |
| `기타비유동자산` | analysis.py:129 | hard | 원명 그대로 (1행) | 부재 |
| `투자부동산` | analysis.py:133 | hard | 원명 그대로 (1행) | 있음 |
| `장기금융자산` | analysis.py:134 | hard | 별칭 ← `투자자산` | 부재 |
| `관계기업등지분관련투자자산` | analysis.py:135 | hard | **부재 → 0 행 보충 목록**(spec D8) | 있음 |
| `현금및현금성자산` | analysis.py:139 | hard | 원명 그대로 (1행) | 부재 |
| `유동금융자산` | analysis.py:139 | hard | 별칭 ← `단기금융자산` | 부재 |
| `매각예정비유동자산및처분자산집단` | analysis.py:143 | hard | 별칭 ← `매각예정비유동자산및처분자산` | 부재 |
| `기타금융업자산` | analysis.py:144 | hard | 원명 그대로 (1행) | 있음 |
| `영업이익` | analysis.py:152, :160, dashboard.py:294, :344, :653, analyzer.py:191 | hard/hard*/soft | 원명 그대로 (1행) | 있음 |
| `이자비용` | analysis.py:154, :161 (`.iloc[0]`) | hard · **다중 행 필요** | 원명 그대로 (**3행**: 손익 202560·204800, 현금흐름 400050) | 있음 |
| `법인세비용` | analysis.py:155, :162 (`.iloc[0]`) | hard · **다중 행 필요** | 원명 그대로 (**1행** — §R4 P-2 결함) | 있음 |
| `당기순이익` | analysis.py:156, :163, dashboard.py:295, :345, analyzer.py:182, :192 | hard/hard*/soft · **단일 행 필요** | 원명 그대로 (**2행**: 손익 LVL0, 현금흐름 LVL1 — §R4 P-1 결함) | 있음 |
| `지배주주순이익` | analysis.py:166, :168, dashboard.py:298, analyzer.py:174 | soft(try 165-172)/soft/hard* | 별칭 ← `(지배주주지분)당기순이익` | 부재 |
| `비지배주주순이익` | analysis.py:167, :169 | soft (try 165-172) | 별칭 ← `(비지배주주지분)당기순이익` | 부재 |
| `매출액` | dashboard.py:293, :343, :652, :823, analyzer.py:190 (+ :622 변수 경유) | hard/hard*/soft | 별칭 ← `매출액(수익)` | 부재 |
| `영업활동으로인한현금흐름` | dashboard.py:305, :773 | soft | 원명 그대로 (1행) | 있음 |
| `매출총이익` | dashboard.py:312 | soft | 원명 그대로 (1행) | 부재 |
| `자산` | dashboard.py:678, :824 | soft | 별칭 ← `자산총계` | 있음 |
| `매출원가` | dashboard.py:822 | soft | 원명 그대로 (1행) | 부재 |
| `지배기업주주지분계산에 참여한 계정 펼치기` | analyzer.py:177 | soft (try 175-180) | 부재 — 옛 화면의 아코디언 버튼 문구가 붙은 이름. JSON에는 이 접미사가 없다 | 부재 |
| `지배기업주주지분` | analyzer.py:180 | hard* | 별칭 ← `지배주주지분` | 부재 |
| `자본` | analyzer.py:183 | hard* | 별칭 ← `자본총계` | 있음 |

요약(스크립트 출력에서 셈 — `grep -c "별칭 ←"` → 21, `grep -c "원명 그대로"` → 37, 부재 2, 합 60): 코드가 문자열로 찾는 계정 60개 중 별칭이 필요한 것 21개, 이름이 그대로인 것 37개(그중 `당기순이익`·`법인세비용` 2개는 이름은 같지만 중복 구조 보정이 필요 — §R4), 새 응답에 없는 것 2개(`관계기업등지분관련투자자산` → 0 행 보충, `…계산에 참여한 계정 펼치기` → 이미 `analyzer.py:179-180` 대체 경로). 승인 계획 별칭표는 22개인데 남는 1개 `부채총계→부채`는 분석 코드가 문자열로 찾지 않는다 — 그래도 정합성 가드(REQ-WC-011)가 `부채`를 쓰므로 별칭표에 둔다. 부재 2개는 `missing.py` 실행 결과(`005930 C missing 2 ['관계기업등지분관련투자자산', '지배기업주주지분계산에 참여한 계정 펼치기']`)와 일치하며 005930 B·403870 B·330590 B도 같은 2개였다.

**별칭 의미 재확인 필요**: `단기충당부채→기타단기충당부채`, `장기충당부채→기타장기충당부채`는 이름만 대조한 후보다. 옛 화면에 `기타단기충당부채` 외에 다른 단기충당부채 행이 있었는지는 옛 사이트가 죽어 확인할 수 없다(plan.md §B Q-E).

---

## §R3 옛 구조 대 새 구조 비교 매트릭스

| 항목 | 옛 (`comp.fnguide.com`, 2026-10 이전) | 새 (`wcomp.fnguide.com`) |
|---|---|---|
| 형식 | 서버 렌더 HTML 표 6개(`SVD_Finance.asp`), 순서 고정 | 재무제표 3종 × 연/분기 = JSON 6회 |
| 연결/별도 | 표 머리글 첫 칸(`th[0][0]`)이 `IFRS(연결)`/`IFRS(별도)` | `consol_typ` 파라미터. 판별 필드 없음 → 선택 규칙(spec D2) |
| 계정명 | 공백 들여쓰기 + 일부 행에 `계산에 참여한 계정 펼치기` 접미사 | 공백 4칸 들여쓰기, 접미사 없음, 일부 이름 변경(§R2) |
| 열 | 연간 마지막 두 열(전년동기·전년동기%)을 무조건 잘라냄(`crawler.py:212-213`) | Income만 VAL5·VAL6 존재, Balance·CashFlow는 4열 |
| 값 | 쉼표 문자열, `-`/빈칸 = 결측 | 소수 둘째 자리 문자열(쉼표 없음), JSON null = 결측 |
| 단위 | 억원 | 억원(DIGIT=0, UNIT=null) |
| 식별자 | 없음 | `AC_CODE`·`P_AC_CODE`·`LVL`. 단 `AC_CODE`는 레이아웃마다 뜻이 다름(삼성전자 200000 = 매출액(수익), KB금융 200000 = 순이자이익; 105560 `당기순이익`의 AC_CODE 202550 = 삼성전자 `금융원가`) |
| 실패 신호 | 없음(지금은 안내 페이지, 200) | 200 + HTML 또는 200 + 빈 dataset |

### 사례별 비교

| 사례 | 코드 | 새 응답 특징 | 선택 | 레이아웃 | 기대 결과 |
|---|---|---|---|---|---|
| 대형 연결 | 005930 | C·B 모두 정상, Y VAL4 `2026/06 (최근분기)` | C | 일반 | 200, 섹션 채워짐, `df_yoy_base_ann` 있음 |
| 별도 전용 | 403870 | C 전 행 null | B | 일반 | 200, 섹션 채워짐, `IFRS(별도)` |
| 별도 전용 | 476830 | C 전 행 null(Income Y만 표본) | B | 일반 | 403870과 같음(표본이 Income뿐이라 라이브 AC 대상에서 뺐다) |
| 반기 리츠 | 330590 | C 전 행 null, Y 열이 반기 단위, 표지 없음 | B | 일반 | 200, `df_yoy_base_ann` = None, `calc_weight_coeff` gap 6 → w2 = 1.0 |
| 부분 연결 | 001750 | C의 당기순이익 VAL1·VAL2만 값 | B | **금융**(증권사, `매출액(수익)` 없음) | 200, Sections 1–7 null |
| 은행·보험·증권 | 105560·055550·000810·006800 | Balance LVL0 `자산/부채/자본`, CashFlow 170~190행 | C | 금융 | 200, Sections 1–7 null |
| 우선주·ETF | 005935·069500 | `data=[]`, 머리글 null | — | — | 404 |
| 없는 코드 | 999999·12345·ABCDEF·117930 | 1,668바이트 오류 HTML | — | — | 404 |

각주 — 금융 레이아웃의 Section 8: 105560 Y C 세 재무제표를 별칭 없이 이어 붙여 `dashboard._calc_activity_ratios`를 직접 호출하면 예외 없이 모든 값이 `None`인 `ActivityRatios`를 돌려준다(Section 1은 `KeyError: '매출액'`, `fs_analysis`는 `KeyError: '매입채무및기타유동채무'`). 그래서 금융 레이아웃의 `activity_ratios`는 `null`이 아니라 "값이 모두 null인 객체"이며 acceptance.md는 이를 단언하지 않는다.

---

## §R4 중복 행 결함 — 프로토타입 실측

프로토타입 `$SP/specprobe/proto.py`·`proto2.py`는 승인 계획의 별칭표만 적용한 최소 리더로 005930 C를 읽어 **수정하지 않은** `fnguide.analysis.fs_analysis`와 `fnguide.dashboard`의 섹션 함수를 그대로 호출한다.

### P-1 — `당기순이익` 2행 (계획대로 "중복 보존"만 하면)

```
$ python proto.py ../raw 005930 C naive
당기순이익 rows 2 법인세비용 rows 1 이자비용 3
fs_analysis FAIL ValueError cannot set a row with mismatched columns
sec1 FAIL TypeError float() argument must be a string or a real number, not 'Series'
sec8 OK
```

### P-2 — `법인세비용` 1행 (현금흐름표 `당기순이익`만 개명하고 0 행 보충을 안 하면)

```
$ python proto2.py ../raw 005930 C half
당기순이익 rows 1 법인세비용 rows 1 이자비용 3
fs_analysis OK
           2023/12    2024/12    2025/12    2026/06  …  예상
법인세비용     -44808.4   -44808.4   -44808.4    13198.2  …  367217.4
지배주주순이익   144734.0   336213.6   442609.6  1496691.7  …  1292899.0
```

### 보정 후 (개명 + 0 행 보충)

```
$ python proto.py ../raw 005930 C fixed
당기순이익 rows 1 법인세비용 rows 2 이자비용 3
fs_analysis OK
법인세비용     -44808.4    30783.8    42746.7   371247.8  …  460880.7
지배주주순이익   144734.0   336213.6   442609.6  1496691.7  …  1622668.9
주주몫      3532337.8  3916876.0  4243132.6  5650647.4
sec1 OK
sec8 OK
```

해석: P-2는 예외가 없어 200 응답과 채워진 섹션을 만든다. 예상 지배주주순이익이 1,622,668.9 → 1,292,899.0으로 약 20% 줄어드는 오계산이 "정상 응답"으로 나간다. **주의(v0.2.0)**: 이 두 예상값은 접기를 하지 않은 프로토타입의 값이다. 최종 접기 정책(전부 `기타*`)을 적용한 감사자 독립 재구현에서는 보정 후 예상값이 1,622,686.97로 조금 다르다(영업자산이 접힌 금액만큼 커지므로). 그래서 AC는 예상값을 고정하지 않고, 접기와 무관하며 독립 재계산으로 확인된 `법인세비용`·`이자비용` 값만 고정한다(AC-WC-005). `주주몫` 2023/12 = 3,532,337.75는 원 응답의 `지배주주지분` 2023/12 값과 같다 — 별칭 계층이 자본 쪽을 빠짐없이 옮긴다는 교차 확인이다.

옛 사이트에서 `법인세비용`이 두 행이었는지(그래서 `.iloc[0]` 코드가 맞았는지)는 확인할 수 없다. 코드 주석(`analysis.py:153` "중복 계정이 있어 iloc[0]으로 첫 번째 행만 사용")이 유일한 근거다(plan.md §B Q-B).

---

## §R5 정합성 검산

`$SP/specprobe/tie.py`: 일반 레이아웃 Balance에서 분석 코드가 소비하는 자산·부채 계정의 합과 `자산`·`부채`의 차이를 열마다 계산한다. 접기 규칙 두 안(`other` = 전부 `기타*`, `fin` = 금융상품은 금융 계정)을 모두 돌렸다. 사용자는 `other`(승인 계획)를 택했다(plan.md §B.2 Q-G). 아래 표는 연간 표 결과다. 감사자 독립 재구현으로 최종 정책의 분기 표까지 재계산한 값: 접기 시 연간·분기 경고 0건, 접기를 빼면 005930 C에서 경고 8건(연간 `6353.93, 368.77, 257.15, 460.00`, 분기 2025/09~2026/06 `201.71, 257.15, 232.38, 460.00`, 모두 `자산 − 소비 자산 합` 부호 양수). 403870 B는 두 경우 모두 0건.

| 종목·유형 | 접힌 비영(非零) 행 | 자산 잔차 (4열) | 부채 잔차 (4열) |
|---|---|---|---|
| 005930 C | `당기손익-공정가치측정금융자산`, `상각후원가측정금융자산` | 0.0, 0.0, 0.0, 0.0 | 0.0, 0.0, 0.0, 0.0 |
| 005930 B | 없음 | 0.0 ×4 | 0.0 ×4 |
| 403870 B | 없음 | 0.0, **−0.02**, 0.01, 0.0 | −0.01, 0.0, 0.01, 0.0 |
| 330590 B | 없음 | 0.0, −0.01, 0.01, 0.01 | 0.0, −0.01, 0.0, 0.0 |
| 403870 C | 없음(전부 null) | 0.0 ×4 | 0.0 ×4 |

- 접힌 행들이 옛 사이트에 없던 **새 행인지는 관측하지 못했다**(옛 사이트 소멸) — 승인 계획의 "새로 생긴 행" 서술은 미검증 추정이다.
- 두 접기 안의 잔차가 **완전히 같다** — 정합성 가드는 귀속을 판별하지 못한다(spec D7).
- 반올림 잔차가 최대 0.02억원 → 허용오차 0.01억원은 정상 종목에서 경고를 낸다. 0.1억원으로 정했다(spec D7).
- 접기를 하지 않으면 005930 C 자산 잔차는 2023/12부터 `6353.93, 368.77, 257.15, 460.00`(= 두 금융상품 행의 합). acceptance AC-WC-007의 되돌림 관측값이다.
- 비유동자산: 하위 합 3,192,574.98 = `비유동자산` 값(승인 계획 조사). `투자자산`(AC 190310)과 `투자부동산`(AC 111330)이 별개 행이라 `금융투자 = 투자부동산 + 장기금융자산(←투자자산) + 관계기업등지분관련투자자산(0)`에 이중 계산이 없다.

---

## §R6 후속 참고 (범위 밖)

- 컨센서스 복원 후보: `$SP/json/cnsperfor_<code>_<C|P>_<Y|Q>.json`, `cnstrend_*`. 스냅샷 시계열 후보: `snpfin_<code>_<M|P|C>_<A|Q>.json`, 그리고 Snapshot HTML 안의 `snpFinancial` 인라인 JSON(VAL1~VAL8, `EP_CHK="E"`가 추정치).
- 금융 레이아웃 분석 후보: 105560 Income LVL0 `영업이익/법인세비용차감전계속사업이익/당기순이익`, Balance LVL0 `자산/부채/자본`.
