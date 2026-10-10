# SPEC-FNGUIDE-WCOMP-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

**작성자**: manager-spec (plan 단계)
**일자**: 2026-10-07
**Tier**: M (spec.md + plan.md + acceptance.md, 보조로 research.md + 본 파일)

### 산출물

| 파일 | 상태 |
|---|---|
| `spec.md` | v0.2.3 — 결정 D1~D9(D7에 정합성 합산 대상 39개 계정 열거), REQ-WC-001~016(16개, Tier M 상한 16), Out of Scope 5개 소절 |
| `plan.md` | v0.2.3 — HISTORY 신설, 계획 정정 C-1~C-5, 사용자 결정 5건(Q-G, Q-I, Q-D, Q-F, Q-A), M1 확인 과제 V-1~V-4, 마일스톤 M1~M6(M6에 라이브 게이트 선행 과제 3건), 미확정 표지 0건 |
| `acceptance.md` | v0.2.3 — AC-WC-001~016(16개, Tier M 상한 16): 대조 13 / 불변 1 / 게이트 2. AC-WC-015는 판정 6항목(호스트 이름 정확 비교 AST 프로브, fixture README, 저장 금지 정적 판정 포함) |
| `research.md` | 작성 완료 — 계측 사실 F-01~F-23, 계정 대응표 60행(스크립트 생성), 구조 비교, 중복 행 결함 실측, 정합성 검산 |
| `progress.md` | 본 파일 |

### SPEC ID 검증 (실행 출력)

```
$ ID="SPEC-FNGUIDE-WCOMP-001"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
PASS
```

ID 중복 확인: `ls .moai/specs | grep -c "SPEC-FNGUIDE-WCOMP"` → `0`(작성 전). 같은 영역 SPEC은 `SPEC-FNGUIDE-ENGINE-001`, `SPEC-DASHBOARD-001`, `SPEC-DASHBOARD-002`이다. `depends_on`에는 `status: completed`인 **SPEC-DASHBOARD-002만** 둔다(v0.2.0부터). ENGINE-001(frontmatter 없음)과 DASHBOARD-001(`status: draft`)은 run 단계 의존성 점검을 막지 않도록 본문 참조로만 둔다(spec.md §2.1·§2.2).

### plan 단계에서 새로 발견한 것 (승인 계획에 없던 것)

1. **조용한 오계산**: 새 응답에서 `법인세비용`이 한 행뿐이라 `analysis.py:155,162`의 `.iloc[0]`이 첫 열 값을 네 해에 복사한다. 예외 없이 예상 지배주주순이익이 약 20% 줄어든다(research.md §R4 P-2). → spec D4, REQ-WC-008, AC-WC-005.
2. **`당기순이익` 중복으로 전 섹션 실패**: 계획대로 중복을 보존만 하면 Section 1–7이 모두 `None`(§R4 P-1). → 같은 결정.
3. **001750은 금융 레이아웃**(계획 정정 C-1), **허용오차 0.01 → 0.1**(C-2), **오류 HTML 본문이 공백으로 시작**(research.md §R1 F-13, REQ-WC-002 반영).

### 자체 완결성 점검

| 항목 | 결과 |
|---|---|
| frontmatter 12개 필드 + `tier`·`depends_on` | 있음 (`phase: "v0.5.2 target"`, 단계 이름 아님) |
| GEARS 표기 | REQ 16개 모두 `The …`/`When …`/`Where …`/`While …` 형식, `IF/THEN` 없음 |
| `### Out of Scope —` H3 + `-` 항목 | 5개 소절 |
| REQ ↔ AC 추적 | spec.md §7 표, 모든 REQ가 AC 1개 이상에 연결 |
| AC 기계 판정 | AC-WC-001~016 모두 명령 + 기대 출력 명시. 수동 확인은 DoD 항목으로만 둠 |
| 대조 AC의 되돌림 관측값 | AC-WC-001~013 각각 "되돌림 시 관측값" 명시 |
| 미확정 표지 위치 (v0.1.0 시점) | plan.md에만 있었음 — v0.2.0에서 0건으로 해소 |
| 코드베이스 주장의 프로브 | research.md §R1 표와 §R2 생성 방법에 명령 기재 |

### 계측하지 못한 것 (Gaps)

- 라이브 테스트 25 errors(오케스트레이터 조사 결과)를 plan 단계에서 다시 돌리지 않았다 — 수집 개수(94)만 확인.
- 응답 `Content-Type` 헤더를 직접 보지 않았다 — 본문 첫 글자로 판정 근거를 보강함(F-13).
- 999999 스냅샷이 리디렉션 후 어떤 페이지가 되는지 보지 못했다(F-17, 추정).
- 001750·330590 스냅샷, 001750 Balance·CashFlow, 330590·105560 Q Balance·CashFlow 표본 없음 — run 단계 M1에서 캡처.
- 옛 사이트의 계정 구조(특히 `법인세비용` 중복 여부, 현금흐름표 순이익 행 이름)는 사이트가 죽어 확인 불가.

### plan-audit 반복 기록

| 반복 | 판정 | 대응 |
|---|---|---|
| iter1 | FAIL 0.78 (Tier M 통과선 0.80) | v0.2.0으로 개정 — 아래 처분표 |
| iter2 | FAIL 0.80 (새 차단 결함 2건 D-N1·D-N2, iteration-1 개정이 유입) | v0.2.1로 개정 — 아래 iter2 처분표 |
| iter3 | FAIL 0.83 (strict, 마지막 허용 감사) — 차단 1건(D-I3-1) 수정 시 PASS-WITH-DEBT 권고, 네 번째 감사 없음 | v0.2.2로 개정 — 아래 iter3 처분표 |
| iter4 | FAIL 0.84 (Tier M 통과선 0.80 이상이나 차단 결함 1건, 근원 1개 = D1·D2) — 3회 상한을 넘긴 추가 감사(사용자가 상한 초과 진행을 명시 승인). 보고서 `.moai/reports/plan-audit/SPEC-FNGUIDE-WCOMP-001-review-4.md` | v0.2.3으로 개정 — 아래 iter4 처분표. 재감사 범위는 감사 권고대로 D1·D2 차분 |

### iter1 결함·결정 처분표 (v0.2.0)

| 항목 | 처분 | 변경 위치 |
|---|---|---|
| Q-G 접기 정책 | 사용자 결정 반영(전부 `기타*`), 금융 계정 분기 삭제, 세 안 기록 | spec.md D6·REQ-WC-011; acceptance.md AC-WC-007; plan.md §B.2 |
| Q-I 0 행 범위 | 사용자 결정 반영(명시 목록만), 해소 | spec.md D8·REQ-WC-010; plan.md §B.2 |
| Q-D 신규 상장 | 사용자 결정 반영(`ValueError`/404, 0 패딩 없음) | spec.md REQ-WC-002·§6; acceptance.md AC-WC-009 (d) |
| Q-F fixture·자세 | 사용자 결정 반영(축소 fixture 커밋), 저장소 공개 여부 미확인을 잔여 위험으로 | spec.md REQ-WC-016; plan.md §B.2·§B.3·§D |
| Q-A 전후 비교 불가 | 수용한 잔여 위험 + 완화 3종 | plan.md §B.2·§B.3; acceptance.md §E |
| Q-B / Q-C / Q-E | M1 확인 과제 V-2 / V-3 / V-4로 전환(명령·통과 조건) | plan.md §F.1 |
| D2 | 수정 — 본문 기반 판정, 헤더는 M1 V-1에서 기록 | spec.md REQ-WC-002; plan.md §B.1 C-5·§F.1 V-1 |
| D3 | 수정 — 접기·가드 두 표 모두, 차이 = `자산 − 소비 합`, 경고 8건 재계산 | spec.md D6·D7·REQ-WC-011; acceptance.md AC-WC-007; research.md §R5 |
| D4 | 수정 — 목적지·합계 부재 시 경고 후 건너뜀; AC-WC-002 예측을 접기 구현 기준으로 재관측(`KeyError: '매입채무및기타유동채무'` 유지 확인) | spec.md D7·REQ-WC-011; acceptance.md AC-WC-002·AC-WC-007 |
| D5 | 수정 — 2xx 밖 → 503, 2xx 본문 이상 → 404 | spec.md REQ-WC-002·003; acceptance.md AC-WC-010 (나) |
| D6·D21 | 수정 — `depends_on: [SPEC-DASHBOARD-002]`만, ENGINE-001 상태 서술 정정, 교차 참조는 이 SPEC §2.1 정본 + sync 시 §E.4 한 줄 | spec.md frontmatter·§2.1·§2.2 |
| D7 | 수정 — 모달 회사명 주장 철회, API 수준 개선으로 한정 | spec.md D9; plan.md §A.2; research.md F-22 |
| D8 | 수정 — 기간 불일치 `RuntimeError` 계열(503), 분기·연간 4번째 기간 차이는 경고 | spec.md REQ-WC-005; acceptance.md AC-WC-006 (d)(e) |
| D9 | 수정 — "새 행" 주장 미검증 표기, 세 안 기록 | spec.md D6; research.md §R5; plan.md §B.2 |
| D10 | 수정 — 옛 순서 확정 불가 인정, 공유 이름 0개로 동치 설명 | spec.md D4; research.md F-21 |
| D11 | 수정 — F-05 프로브 교체, `rim_fnguide` 동명 함수 기록 | research.md F-05 |
| D12 | 수정 — `dashboard.py:643` → `:645` | research.md §R2 |
| D13 | 수정 — 1,622,669 계열은 접기 없는 프로토타입 값으로 표기, AC 고정 제외 | spec.md D4; research.md §R4 |
| D14 | 수정 — 라이브 skip ≤ 1, 허용 사유 1개 명시 | acceptance.md AC-WC-015 3. |
| D15 | 수정 — RED 관측 머리글 집합 = AC-WC-001~013 정확 비교 | acceptance.md AC-WC-016; plan.md §E |
| D16 | 수정 — 종목별 성질은 `While`/`When` | spec.md REQ-WC-006·009·010·011 |
| D17 | 수정 — 정규화(`\xa0`, 비숫자→0.0), `#cmp_cd` 부재, `자사주` 부재 사례 추가 | acceptance.md AC-WC-002·011·012 |
| D18 | 수정 — "값" 정의, 선택 요청과 데이터 요청 구분법 | spec.md REQ-WC-004·D2; acceptance.md AC-WC-003 |
| D19 | 해당 없음(별도 항목 아님) — iteration-1 지시문에는 D19가 선택 항목 D19b로만 실려 있었고 그 밖의 D19 본문은 전달되지 않았다. 처분은 D19b 행이 전부다. iteration-2에서 누락 지적을 받아 이 행을 추가 | progress.md 본 행 |
| D19b | 수정 — 대시보드 전용 계정까지 부재 경고 | spec.md D8·REQ-WC-010; acceptance.md AC-WC-008 (c) |
| D20 | 수정 — ASCII 코드 검증·쿼리 파라미터; `async def` 동기 호출은 기록만 | spec.md REQ-WC-001·§5; acceptance.md AC-WC-009 (e)·AC-WC-010 |

### iter2 결함 처분표 (v0.2.1)

| 항목 | 처분 | 변경 위치 |
|---|---|---|
| D-N1 (차단) | 수정 — 요청 구분 규칙 교체: `(getFinIncome, Y)` 외 다섯 쌍은 결정 유형만, `(getFinIncome, Y)`는 {C, B} 안에서 결정 유형 포함, 데이터 출처는 반환 값으로 증명(005930 `B` 2025/12 지배주주순이익 336866.01 ≠ `C` 442609.56 원 응답 대조). 요청 예산 2 + 5 + 1 = 8을 AC-WC-013·spec §5에 일치 | acceptance.md:72, :179; spec.md:191 |
| D-N2 (차단) | 수정 — (a) M6에 `TestReadConsensus` 삭제 과제, skip 대안 기각 명시, AC-WC-015 3번에 삭제 전제 기록 (b) REQ-WC-001 금지 범위를 `read_fs`·`read_snapshot`·`get_fnguide`·보조 함수로 한정, AC-WC-015 4번을 AST 판정으로 교체(현행 코드 실행 결과 `['_CONS_B_URL', '_CONS_D_URL', '_FS_URL', '_SNAP_URL'] ['read_consensus']` — 구현 후 기대값은 앞 목록에서 `_FS_URL`·`_SNAP_URL`이 빠진 것) | plan.md:163; acceptance.md:212, :215; spec.md:122 |
| D-N3 | 수정 — 응답별 검사가 정렬 검사보다 먼저, 정렬은 정규화 `YYYY/MM` 비교, 조작본 (c)(d)가 바꾸는 재무제표를 명시 | spec.md:125, :141; acceptance.md:100, :134 |
| D-N4 | 수정 — `df_yoy_base_ann` 행 라벨 정규화·별칭, AC-WC-006 (a)에 별칭 누락 시 `-0.08463` 대조 추가(`dashboard.py:348-350`이 `KeyError`를 삼킴) | spec.md:145; acceptance.md:108 |
| D-N5 | 수정 — 프로브를 `command grep -rn --include='*.py'`로, 재실행 출력 `37` 인용 | acceptance.md:212 |
| D-N6 | 수정 — 세 스냅샷 모두 두 행 주식수가 같음을 명시, 판별은 행 삭제 조작본이 맡음(다른 값을 가진 fixture는 관측 표본 중 없음) | acceptance.md:171 |
| D-N7 | 수정 — AC-WC-009 대조를 `read_fs("005935")` 수준 "`ValueError` 아님"으로, 라우터 경로를 대조에서 제외한 이유 기록 | acceptance.md:137 |
| D-N8 | 수정 — 경고 토큰 고정: 낱말 단위 `자산` 정규식 + `행 없음` 고정 문구(REQ-WC-011 (b)에 같은 토큰) | acceptance.md:120; spec.md:165 |
| D-N9 | 수정 — REQ-WC-005·011을 하위 조항 (a)(b)(c)로 분리(REQ ID 유지) | spec.md:140-142, :164-166 |
| D-N10 | 수정 — 001750 Balance·CashFlow `C`·`B` × Y·Q 캡처 목록 | plan.md:75 |
| D-N11 | 수정 — `read_fs` 반환 순서 `(account_type, df_fs_ann, df_fs_quar, df_yoy_base_ann)` 고정(REQ-WC-014에 병합) | spec.md:179 |
| D-N12 | 수정 — iteration-1 D19 행 추가 | progress.md 처분표 D19 행 |

### iter3 결함 처분표 (v0.2.2)

| 항목 | 처분 | 변경 위치 |
|---|---|---|
| D-I3-1 (차단) | 수정 — M6에 `test_analysis.py:255-268` 비교 열을 `yearly_cols[-2]`로 바꾸는 과제, 별도 후보 `["003550","015760","034020"]` → `["403870","330590","476830"]` 교체(대체되는 skip 4건 `test_crawler.py:96, :103`, `test_analysis.py:248, :258` 명시), §A.1 다시 쓰기 목록에 `:234`·`:255-268` 추가, AC-WC-015 3번 근거에 (i)(ii)(iii) 선행 과제로 반영. 허용 skip은 여전히 1건(`"연도 컬럼이 3개 미만"`) | plan.md:16, M6; acceptance.md AC-WC-015 3. |
| S1 | 수정 — AST 프로브를 문자열 상수 노드 기준으로(docstring 제외, `AnnAssign`·`from … import` 추적, docstring·주석 언급 허용 명시). 프로브는 줄 앞 공백 없이 실어 그대로 실행 가능. M3에 `_FS_URL`·`_SNAP_URL` 삭제, M5에 AST 확인 추가 | acceptance.md AC-WC-015 4.; plan.md M3·M5 |
| S2 | 수정 — `read_snapshot(code, account_type="IFRS(연결)")` 유지(인자 무시), 반환 `(report, 빈 DataFrame, 빈 DataFrame)`; AC-WC-011·012는 그대로 `report[...]`를 읽음 | spec.md REQ-WC-013; plan.md M4 |
| M1 | 수정 — `TestReadConsensus` 범위 `test_crawler.py:177-196`(데코레이터 177, 클래스 178, 마지막 단언 196; 197~ 빈 줄 후 `:199` 다음 구역 주석) | plan.md M6·§A.1; acceptance.md AC-WC-015 3. |
| M2 | 수정 — skip 실제 호출 36(`^\s*pytest\.skip\(` 앵커 프로브), 이전 37은 `conftest.py:9` docstring 포함 | acceptance.md AC-WC-015 3. |
| M3 | 수정 — `자산총계` 인덱스 단언 문구 삭제(`:44`는 `자산`·`부채`·`자본` 단언이며 유지) | plan.md M6 |
| M4 | 수정 — 산출물 표 버전(v0.2.2), research F-01~F-23, `depends_on` 서술(DASHBOARD-002만) 갱신 | progress.md 산출물 표·ID 중복 확인 문단 |
| M5 | 수정 — AC-WC-003에 사례 (d)(C·B 모두 VAL4 null, VAL3에서 C 값 있음 → `IFRS(연결)`)와 대조 (라) 추가, 기대 출력 6 → 8, 게이트 합계 61 → 63(162 → 164) | acceptance.md AC-WC-003, AC-WC-015 2. |
| M6 | 수정 — git diff 불변 게이트에 `fnguide/analyzer.py`·`fnguide/parser.py`·`fnguide/__init__.py` 추가 | acceptance.md AC-WC-015 첫 명령 |
| M7 | 수정 — 선택 응답 재사용과 요청 상한 8을 REQ-WC-004로 올림 | spec.md REQ-WC-004 |
| M8 | 수정 — REQ-WC-002 검사 대상을 결정 유형의 데이터 응답 여섯으로 한정, 비결정 유형 선택 응답 실패는 "값 없음"으로 처리(두 유형 모두 실패 시 `ValueError`). 관측한 별도 종목 `C` 응답은 모두 56행(값 전부 null)이라 빈 `C`는 미관측 — plan §B.3에 기록 | spec.md REQ-WC-002; plan.md §B.3 |

### iter4 결함 처분표 (v0.2.3)

| 항목 | 처분 | 변경 위치 |
|---|---|---|
| D1 (차단) | 수정 — AC-WC-015 4번 AST 프로브의 옛 호스트 판정을 부분 문자열(`H in n.value`, `H in str(getattr(...))`)에서 파싱한 호스트 이름 정확 비교(`urlparse(v).hostname == "comp.fnguide.com"`, 스킴 없는 문자열은 `//`를 붙여 파싱)로 교체. 문자열 상수 분기와 `from … import` 분기가 같은 판정 함수 `old`를 씀. `wcomp.fnguide.com`은 잡히지 않는다는 문장 추가, 판정 대상 파일을 첫 인자로 받게 함(기본 `fnguide/crawler.py`). 참고용 grep을 `//comp\.fnguide\.com`으로. 현행 코드·준수 가짜·위반 가짜 세 경우의 출력을 아래 v0.2.3 자체 점검에 축자 기록. plan.md M5에 같은 판정 기준과 "부분 문자열 판정을 다시 만들지 않는다" 명시 | acceptance.md AC-WC-015 When·4.; plan.md M5·HISTORY |
| D2 (차단) | 수정 — AC-WC-013 Then의 "URL에 `comp.fnguide.com` 포함 0건"을 "`urlparse(url).hostname == "comp.fnguide.com"`인 것 0건, `01_06` 포함 0건, 모든 URL의 호스트가 `wcomp.fnguide.com`"으로 교체하고 부분 문자열을 쓰면 안 되는 이유를 한 문장으로 남김. 되돌림 관측값(`read_consensus` 부활 시 실패)은 유지 | acceptance.md AC-WC-013 |
| D3 | 수정 — 프로브로 확인 후 `dashboard.py:342` → `:343`(`base_revenue = float(base_series.at["매출액"])`), `:348-350` → `:349-351`(`except (KeyError, IndexError, ValueError):` ~ `pass`) | spec.md REQ-WC-006; acceptance.md AC-WC-006 되돌림 관측값 |
| D4 | 수정 — spec D7에 "합산 대상" 단락 신설: 소비 자산 19개(`df_invest` 다섯 행), 소비 부채 20개(`df_financing`의 신용조달·외부차입·기타, 자본 쪽 행 제외)를 소스 순서로 열거, 두 목록은 `account_alias.py`에 이름 붙은 목록으로, 목록에 있으나 표에 없는 계정은 합에 0. REQ-WC-011 (c)가 이 목록을 가리킴. plan.md M2·§D 단일 출처 목록에 추가. research.md는 이번 개정 범위 밖이라 손대지 않고 spec D7을 정본으로 둠 | spec.md D7·REQ-WC-011 (c); plan.md M2·§D |
| D5 | 수정 — AC-WC-015에 5번(fixture README에 비어 있지 않음 + `https://wcomp.fnguide.com/` URL + `YYYY-MM-DD` 날짜 → `README_OK`)과 6번(`crawler.py`·`account_alias.py`에 쓰기 모드 `open`·`to_*` 내보내기·`write_text/bytes`·`json/pickle.dump`·`shelve`·`sqlite3` 0건 → `exit=1`)을 병합. 새 AC 없음(AC 16 유지), REQ 문구는 그대로 | acceptance.md AC-WC-015 When·5.·6.; plan.md M6·§D |
| D6 | 수정 — REQ-WC-013의 `crawler.py:286`을 "`get_fnguide` 안의 `read_snapshot(code, account_type)` 호출"로, REQ-WC-014의 `crawler.py:215`·`test_crawler.py:87`을 "현행 `read_fs`가 돌려주는 순서, 라이브 크롤러 테스트가 `result[0]`을 `account_type`으로 읽음"으로 바꿈. 줄 번호는 각 REQ 아래 `> 근거` 주석으로 옮기고 재작성 후 무효임을 적음. REQ 본문(영문 GEARS 줄)에 `crawler.py:` 0건(프로브 아래) | spec.md REQ-WC-013·014 |
| D7 | 수정 — v0.2.2 자체 점검의 "lint 무결" 행을 정정 표기로 바꾸고, 실제 출력은 아래 v0.2.3 자체 점검에 축자 기록. frontmatter `status: draft`는 그대로(실제로 draft — 감사 판단과 같음) | progress.md 본 절 |

### v0.2.3 자체 점검

모든 명령은 저장소 루트에서 2026-10-07에 실행했다. `$D`는 이번 세션의 scratchpad(`/private/tmp/claude-501/-Users-byunjungwon-Dev-my-project-01-my-chart/e0b7b6de-2a3d-487d-923f-28f6082e8044/scratchpad`, 저장소 밖)다. 가짜 크롤러 두 개와 대조용 쓰기 파일·README 표본은 확인 후 삭제했다(아래 마지막 행).

| 항목 | 결과 |
|---|---|
| REQ / AC 개수 | 16 / 16 — `grep -cE '^#### REQ-WC-[0-9]{3}' spec.md` → `16`, `grep -cE '^### AC-WC-[0-9]{3}' acceptance.md` → `16` |
| frontmatter | 12개 필드 → `12`, `version: "0.2.3"`, `updated: 2026-10-07`, `tier: M`, `depends_on: [SPEC-DASHBOARD-002]` |
| 미확정 표지 | `grep -rn '\[NEEDS CLARIFICATION' spec.md plan.md acceptance.md research.md progress.md` → 출력 없음, rc=1 |
| D1 프로브 동일성 | acceptance.md에서 `$PY - <<'EOF'` ~ `EOF`를 추출한 파일과 시험한 프로브 파일을 `diff` → `identical` |
| D1 프로브 (1) 현행 `fnguide/crawler.py` | `$PY - < probe_from_doc.py` → `['_CONS_B_URL', '_CONS_D_URL', '_FS_URL', '_SNAP_URL'] ['read_consensus', 'read_fs', 'read_snapshot']` (수정 전이므로 기대값과 불일치가 정상, v0.2.2 프로브 출력과 같음) |
| D1 프로브 (2) 준수 가짜 크롤러 | `$D/fake_crawler_ok.py`: `_WCOMP_BASE = "https://wcomp.fnguide.com/CompanyInfo/"`, `_SNAPSHOT_URL: str = "https://wcomp.fnguide.com/CompanyInfo/Snapshot"`(`AnnAssign`), `Referer: https://wcomp.fnguide.com/` 헤더, `from .parser import to_num`, docstring의 `comp.fnguide.com` 언급, `_CONS_D_URL`·`_CONS_B_URL`·`read_consensus`를 둠. `$PY - $D/fake_crawler_ok.py < probe_from_doc.py` → `['_CONS_B_URL', '_CONS_D_URL'] ['read_consensus']` (기대 출력과 정확히 같음) |
| D1 프로브 (3) 위반 가짜 크롤러 (대조) | `$D/fake_crawler_bad.py`(`read_fs`가 `http://comp.fnguide.com/SVO2/asp/SVD_Finance.asp`를 직접 요청) → `['_CONS_B_URL', '_CONS_D_URL'] ['read_consensus', 'read_fs']` (옛 호스트 사용을 여전히 잡음) |
| D1 결함 재현 (v0.2.2 프로브) | 같은 준수 가짜에 v0.2.2 프로브(파일 경로만 인자로 바꿈) → `['_CONS_B_URL', '_CONS_D_URL', '_HEADERS', '_SNAPSHOT_URL', '_WCOMP_BASE'] ['_get', 'read_consensus', 'read_fs', 'read_snapshot']` — 감사 보고 D1과 같은 오판 |
| D1 참고용 grep | `grep -nE "//comp\.fnguide\.com" $D/fake_crawler_ok.py` → `11:_CONS_D_URL = …01_06/01_A{code}_A_D.json"`, `12:_CONS_B_URL = …01_06/01_A{code}_A_B.json"` 두 줄뿐(같은 파일의 `wcomp.fnguide.com` 줄 3개는 나오지 않음) |
| D2 판정식 | `$PY -c '…'`로 네 URL 평가. `https://wcomp.fnguide.com/CompanyInfo/getFinIncome \| substring: True \| hostname==: False \| 01_06: False` / `https://wcomp.fnguide.com/CompanyInfo/Snapshot \| substring: True \| hostname==: False \| 01_06: False` / `http://comp.fnguide.com/SVO2/json/data/01_06/01_A005930_A_D.json \| substring: True \| hostname==: True \| 01_06: True` / `https://comp.fnguide.com/SVO2/asp/SVD_Main.asp \| substring: True \| hostname==: True \| 01_06: False` — 부분 문자열은 wcomp에서도 `True`(결함), 호스트 이름 비교는 wcomp `False`·comp `True` |
| D3 프로브 | `grep -n 'base_series.at\["매출액"\]' fnguide/dashboard.py` → `343:            base_revenue = float(base_series.at["매출액"])`; `sed -n '338,353p'`로 `except (KeyError, IndexError, ValueError):`가 349, 주석 350, `pass` 351임을 확인 |
| D4 목록 출처 | `fs_analysis` 본문을 AST로 읽어 `df_invest`(설비투자·운전자산·금융투자·여유자금·기타)와 `df_financing`(신용조달·외부차입·기타)이 더하는 `df_fs_ann.loc[...]` 이름을 소스 순서로 추출 → `assets 19 same_order True same_set True`, `liabs 20 same_order True same_set True` (비교 대상: 감사자 독립 재구현 `scratchpad/auditor/indep.py`의 `ASSETS`·`LIABS` — AC-WC-007 고정값을 만든 목록) |
| D5 README 판정 | acceptance.md 다섯째 명령을 그대로 실행 → 출력 없음, rc=1(README 미작성, plan 단계 정상). 출처 URL·`2026-10-07` 날짜를 담은 표본 → `README_OK`, 제목만 있는 표본 → 출력 없음 |
| D5 저장 금지 판정 | acceptance.md 여섯째 명령을 그대로 실행 → `grep: fnguide/account_alias.py: No such file or directory` / `exit=2`(M2 전, 정상). `fnguide/crawler.py`만 → 출력 없음, `exit=1`. 네 쓰기 형태 대조 파일(`df.to_csv(p)`, `open(p, "w", …)`, `open(p, mode="wb")` + `pickle.dump`, `json.dump(d, open(p, "a"))`) → 3·4·5·6번 줄 모두 일치, `exit=0` |
| D6 | `grep -nE '^(The\|When\|While\|Where\|- \()' spec.md \| grep -c 'crawler\.py:'` → `0` |
| D7 lint | `moai spec lint .moai/specs/SPEC-FNGUIDE-WCOMP-001/spec.md` → 아래 블록. 경고 원인은 감사 보고의 진단대로 plan 커밋 제목이 정본 형식(`feat(SPEC-{ID}): plan-phase artifacts (…)`)이 아니기 때문으로 본다 — `git log --format='%h %s' -- …/spec.md` → `e0ee022 feat(SPEC-FNGUIDE-WCOMP-001): plan 산출물 5종 추가 (Tier M, PASS-WITH-DEBT)`. 판정 엔진 내부는 직접 보지 않았다. `status: draft`는 실제 상태이므로 frontmatter는 바꾸지 않는다 |
| 임시 파일 정리 | `rm` 후 `ls $D` → 이번 개정에서 만든 파일(`probe_*.py`, `fake_crawler_ok.py`, `fake_crawler_bad.py`, `fake_writer.py`, `README_ok.md`, `README_bad.md`) 없음. 기존에 있던 다른 세션 파일(`ast_probe.py`, `ast_probe_fake.py`, `fake_crawler.py`, `p000660`)은 손대지 않음 |

```
$ moai spec lint .moai/specs/SPEC-FNGUIDE-WCOMP-001/spec.md
SEVERITY  CODE                  FILE                                        LINE  MESSAGE
--------  ----                  ----                                        ----  -------
WARNING   StatusGitConsistency  .moai/specs/SPEC-FNGUIDE-WCOMP-001/spec.md  1     SPEC SPEC-FNGUIDE-WCOMP-001 frontmatter status 'draft' disagrees with git-implied status 'implemented'

0 error(s), 1 warning(s)
```

### v0.2.2 자체 점검

| 항목 | 결과 |
|---|---|
| REQ / AC 개수 | 16 / 16 (새 사례는 기존 AC에 병합) |
| 미확정 표지 | 다섯 파일 모두 0건 |
| lint | (v0.2.3 정정) 당시 "`moai spec lint` 무결"로 적었으나 plan 커밋 `e0ee022` 이후 실측은 0 errors, 1 warning(`StatusGitConsistency`) — 축자 출력은 v0.2.3 자체 점검 참조(plan-audit iteration 4 D7) |
| AC-WC-015 4번 프로브 | acceptance.md에서 추출해 그대로 실행 — 현행 코드 출력 `['_CONS_B_URL', '_CONS_D_URL', '_FS_URL', '_SNAP_URL'] ['read_consensus', 'read_fs', 'read_snapshot']`(수정 전이므로 기대값과 불일치가 정상) |
| 라이브 skip 상한 일관성 | 허용 1건, 옛 별도 후보 skip 4건과 `TestReadConsensus` error는 M6 과제로 제거 |

### v0.2.1 자체 점검

| 항목 | 결과 |
|---|---|
| REQ / AC 개수 | 16 / 16 (새 규칙은 기존 항목에 병합) |
| 미확정 표지 | 다섯 파일 모두 0건 |
| lint | `moai spec lint` 무결 |
| 요청 예산 일관성 | REQ-WC-004(두 유형 검토) · AC-WC-003(요청 구분) · AC-WC-013(≤ 8) · spec §5(2 + 5 + 1)가 같은 숫자 |

### v0.2.0 자체 점검

| 항목 | 결과 |
|---|---|
| REQ / AC 개수 | 16 / 16 (Tier M 상한 이내, 새 규칙은 기존 항목에 병합) |
| 미확정 표지 | spec.md·acceptance.md·plan.md 모두 0건 (문자열 검색 결과 각 0) |
| `depends_on` 충족 | SPEC-DASHBOARD-002 `status: completed` |
| AC 고정값 출처 | 원 응답 값 또는 감사자 독립 재구현과 일치한 값만 |

plan_complete_at: 2026-10-07
plan_status: audit-ready

## §E.2 Run-phase Evidence

### M1 — 재현, fixture, 확인 과제 (2026-10-07)

#### BASE

- BASE SHA: `d6ed32e` (`git rev-parse --short HEAD`, 첫 run 단계 커밋 직전). AC-WC-015 1번의 `git diff --stat "$BASE"` 기준점이다.
- 작업 위치: 에이전트 격리 워크트리(`.claude/worktrees/agent-a20b6e0f16e957192`, 브랜치 `worktree-agent-a20b6e0f16e957192`). 워크트리는 `fd5f11f`에서 만들어져 있어 `git merge --ff-only d6ed32e`로 main 끝까지 빨리 감기한 뒤 작업했다. 커밋은 이 브랜치에 쌓이며 main 반영은 오케스트레이터 몫이다.

#### 착수 전 점검 (plan.md §C, 실행 출력)

```text
$ git rev-parse --short HEAD && git branch --show-current
d6ed32e
worktree-agent-a20b6e0f16e957192
$ git status --short fnguide tests backend
(출력 없음)
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide tests/test_analysis_api.py -q -p no:cacheprovider | tail -1
101 passed, 94 deselected, 1 warning in 0.54s
$ ls <plan 표본>/raw | wc -l
     102
```

#### fixture 확보

- 표본 디렉터리가 살아 있어(102개) 가장 먼저 세션 scratchpad로 통째로 복사한 뒤 축소본을 만들었다.
- 축소본은 `tests/fnguide/fixtures/wcomp/`에 54개 파일(재무제표 JSON 40, 원본 그대로 4, 스냅샷 6, 헤더 4) + `README.md`. 축소 방법·원본 URL·캡처 시각은 README에 있다.
- 라이브 요청: 표본에 없던 응답 16건(001750 Income Q `C`·`B`, Balance·CashFlow Y·Q `C`·`B` 8건, 330590 Q Balance·CashFlow `B`, 105560 Q Balance·CashFlow `C`, 001750·330590 스냅샷) — 모두 HTTP 200, 2026-10-07T23:15:50~58+09:00. V-1 헤더 9건 + 리디렉션 추종 3건. 합계 28건, 순차 요청.
- AC-WC-015 5번 판정: `F=tests/fnguide/fixtures/wcomp/README.md; test -s "$F" && grep -qE 'https://wcomp\.fnguide\.com/' "$F" && grep -qE '20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$F" && echo README_OK` → `README_OK`

#### RED 관측 — AC-WC-001

프로덕션 코드를 바꾸기 전(`git diff --stat -- fnguide` 출력 없음)에 새 테스트만 추가한 상태에서 실행했다.

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_repro.py -q -p no:cacheprovider -k ac_wc_001 --tb=short -W ignore::UserWarning; echo "exit=$?"
F                                                                        [100%]
=================================== FAILURES ===================================
___________ test_ac_wc_001_legacy_stub_raises_value_error_with_code ____________
tests/fnguide/test_wcomp_repro.py:59: in test_ac_wc_001_legacy_stub_raises_value_error_with_code
    read_fs("005930")
fnguide/crawler.py:187: in read_fs
    account_type, df_bs_ann = table_parsing(tables[0])
                              ^^^^^^^^^^^^^^^^^^^^^^^^
fnguide/parser.py:38: in table_parsing
    account_type: str = th[0][0]
                        ^^^^^^^^
E   IndexError: list index out of range
=========================== short test summary info ============================
FAILED tests/fnguide/test_wcomp_repro.py::test_ac_wc_001_legacy_stub_raises_value_error_with_code
1 failed, 1 deselected in 0.31s
exit=1
$ git status --short
?? .moai/logs/
?? tests/fnguide/fixtures/
?? tests/fnguide/test_wcomp_repro.py
```

기대(acceptance AC-WC-001 "수정 전 실행 시 `1 failed`이고 출력에 `IndexError`")와 일치한다. 실패 위치는 spec §1.1의 장애 경로(`crawler.py:187` → `parser.py:38`)와 같다. `.moai/logs/`는 착수 전부터 있던 미추적 디렉터리이며 이 SPEC과 무관하다. GREEN은 M3(`read_fs` 재작성) 몫이다.

RED를 관측한 뒤, 실패하는 테스트가 pre-commit 게이트(`moai gate`)와 기본 스위트를 깨지 않도록 `@pytest.mark.xfail(raises=IndexError, strict=True)`를 붙여 커밋했다. `raises=IndexError`라 다른 실패는 그대로 실패로 드러나고, `strict=True`라 M3에서 `read_fs`가 고쳐져 통과하면 XPASS가 실패가 되어 표지를 지우게 된다(M3 작업 항목: 이 표지 제거 → `1 passed` 확인). 표지를 붙인 뒤의 출력:

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_repro.py -q -p no:cacheprovider -rx -W ignore::UserWarning
.x                                                                       [100%]
=========================== short test summary info ============================
XFAIL tests/fnguide/test_wcomp_repro.py::test_ac_wc_001_legacy_stub_raises_value_error_with_code - M1 RED 고정: read_fs 재작성(M3) 전까지 옛 안내 페이지에서 IndexError
1 passed, 1 xfailed in 0.22s
```

#### M1 확인 과제 V-1 ~ V-4

| ID | 상태 | 결과 |
|---|---|---|
| V-1 | 완료 — 모순 없음(주의 1건) | 아래 표. 파일 `tests/fnguide/fixtures/wcomp/HEADERS_{005930,005935,999999}.txt`, `HEADERS_999999_follow.txt` |
| V-2 | M3로 이월 | 통과 조건이 "구현된 `read_fs` 결과의 `df.loc['이자비용'].iloc[0]`"이라 `read_fs` 재작성(M3) 전에는 판정할 수 없다. fixture 쪽 절반만 미리 실행: `[('202560', '202550', '9302.53'), ('204800', '201830', None), ('203130', None, '-44808.35')]` — 이자비용 첫 행 AC_CODE 202560(부모 202550) 9302.53, 법인세비용 203130 −44808.35로 plan 기대와 같다 |
| V-3 | M3로 이월 | 명령이 `tests/fnguide/test_wcomp_reader.py -k "ac_wc_006 and dec"`인데 이 파일과 합성 fixture 테스트는 M3에서 만든다 |
| V-4 | 완료 — 통과 | 아래 출력 |

V-1 응답 헤더(plan.md §F.1 명령 그대로 실행, 2026-10-07T23:16:20+09:00):

| 경우 | 엔드포인트 | 상태 줄 | Content-Type | content-length |
|---|---|---|---|---|
| 005930 (정상) | getFinIncome / getFinBalance / getFinCashFlow | `HTTP/2 200` ×3 | `application/json; charset=utf-8` ×3 | 11981 / 15232 / 18494 |
| 005935 (빈 dataset) | 같음 | `HTTP/2 200` ×3 | `application/json; charset=utf-8` ×3 | 263 / 174 / 174 |
| 999999 (없는 종목) | 같음 | `HTTP/2 302` ×3, `location: /Error/InvalidCompany?errorPath=…` | `text/html; charset=utf-8` ×3 | 197 / 198 / 199 |
| 999999, 리디렉션 추종(`curl -sL`) | 같음 | `302` → `HTTP/2 200` ×3, `FINAL 200 1668 1` ×3 | `text/html; charset=utf-8` | 1668 ×3 |

판정: REQ-WC-002·003과 모순되지 않는다. 오류 응답의 첫 홉은 302지만 `requests.get`은 기본으로 리디렉션을 따라가므로 리더가 받는 최종 응답은 HTTP 200 + 1,668바이트 HTML이고(research.md F-13과 같음), REQ-WC-002의 본문 판정(`<` 시작)이 `ValueError`(404)를 낸다. **주의(M3 입력)**: 리더가 `allow_redirects=False`로 요청하면 302가 REQ-WC-003의 "2xx 밖 상태"에 걸려 503이 되므로, 리더는 리디렉션 추종 기본값을 유지해야 한다. `Content-Type`은 정상·빈 dataset이 JSON, 오류가 HTML로 갈리지만 REQ-WC-002는 이를 판정에 쓰지 않는다(기록만).

V-4 출력:

```text
$ for f in tests/fnguide/fixtures/wcomp/getFinBalance_005930_Y_C.json tests/fnguide/fixtures/wcomp/getFinBalance_403870_Y_B.json; do echo "$f"; /Users/byunjungwon/Dev/my_chart/.venv/bin/python -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8-sig'))['dataset']['data'];print([(r['P_AC_CODE'],r['NAME'].strip()) for r in d if '충당부채' in r['NAME']])" "$f"; done
tests/fnguide/fixtures/wcomp/getFinBalance_005930_Y_C.json
[('131580', '유동종업원급여충당부채'), ('131580', '단기충당부채'), ('130010', '비유동종업원급여충당부채'), ('130010', '장기충당부채')]
tests/fnguide/fixtures/wcomp/getFinBalance_403870_Y_B.json
[('131580', '유동종업원급여충당부채'), ('131580', '단기충당부채'), ('130010', '비유동종업원급여충당부채'), ('130010', '장기충당부채')]
```

두 종목 모두 부모 131580·130010 아래 충당부채가 `종업원급여충당부채` 1행 + `단기충당부채`/`장기충당부채` 1행뿐이다. 별칭 `단기충당부채→기타단기충당부채`, `장기충당부채→기타장기충당부채`의 범위가 옛 이름(종업원급여 외 충당부채)과 같다는 plan 단계 관측을 403870에서도 재확인했다.

#### 005930 캐시 미스 소요 시간

측정하지 않음. 새 `get_fnguide`가 아직 없어(M3~M5) 같은 요청 묶음(최대 8건)을 재현하지 않았다. 참고로 M1 라이브 요청 16건의 시각 기록은 23:15:50~23:15:58(요청 사이 0.5초 대기 포함)이었다 — 기준선이 아니다.

#### M1 후 기본 스위트

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide tests/test_analysis_api.py -q -p no:cacheprovider | tail -1
102 passed, 94 deselected, 1 xfailed, 1 warning in 0.39s
```

기준선 101 passed에 fixture 무결성 테스트 1건이 더해졌고, AC-WC-001은 xfail(RED 고정)이다.

#### M1 미검증(Gaps)

- 첫 커밋 시도에서 pre-commit `moai gate`가 워크트리에 새 `.venv`를 만들고 전체 pytest를 돌려 `21 failed, 907 passed, 1 skipped, 97 deselected, 1 xfailed, 1 xpassed`로 거부했다. 실패 21건은 모두 이 SPEC 밖(`test_market_api` 12, `test_m6_gap_closure` 4, `test_response_contract` 4, `test_ac_sag_045_r1_r4_r5a` 1)이며, 메모리 `project_worktree_precommit_db_trap.md`의 워크트리 환경 문제(운영 DB 부재, setuptools 82)와 파일 구성이 같다. 그 해소법대로 워크트리 `.venv`에 `setuptools<81`(80.10.2)을 넣고 공용 체크아웃의 `Output/stock_data_{daily,weekly}.db`를 워크트리 `Output/`에 복사한 뒤(둘 다 gitignore 대상) 다시 커밋했다. 게이트 우회는 하지 않았다.
- 이 환경에 `ruff`가 없어(`which ruff` → `ruff not found`, venv에도 없음) 새 테스트 파일의 린트를 돌리지 못했다.

- 001750·330590·105560의 일부 재무제표는 plan 표본(00시대)과 M1 라이브(23시대)가 섞였다. 기간 머리글 일치는 확인했으나 그 사이 수치 정정 여부는 확인하지 않았다.
- `legacy_stub_1829.html`의 원본 URL은 표본 이름(`fs.html`)으로 추정한 것이다.
- 005935·999999는 `consol_typ=C` 응답만 있다. 리더가 `B`도 요청하므로 M3 테스트는 같은 응답을 `B` 요청에도 돌려줘야 한다(사이트가 `B`에서 같은 본문을 주는지는 관측하지 않음).
- V-2·V-3은 M3로 이월.

### M2 — 계정명 단일 출처 (2026-10-08)

#### M2 증거

착수 기준: HEAD `3bfddcf`(M1 커밋), 같은 워크트리.

산출물: `fnguide/account_alias.py`(상수만, 클래스·함수 없음)와 구조 테스트 `tests/fnguide/test_wcomp_alias.py`(18건). 모듈이 담는 것: 일반 레이아웃 별칭표 `ALIASES` 22개, 0 행 보충 `ZERO_ROW_LABELS`(1개), 필수 계정 `REQUIRED_LABELS`(analysis.py 52개 + 대시보드 전용 3개 = 55개), 현금흐름표 한정 개명 `CASHFLOW_RENAMES`, 다중 행 필요 `MULTI_ROW_LABELS`·`MULTI_ROW_MIN`, 접기 `FOLD_PARENT_TO_OTHER`(4개), 가드용 `CONSUMED_ASSET_LABELS`(19)·`CONSUMED_LIABILITY_LABELS`(20)·`ASSET_TOTAL_LABEL`·`LIABILITY_TOTAL_LABEL`, 그리고 M3 리더가 계정명을 직접 쓰지 않도록 레이아웃 표지 `GENERAL_LAYOUT_MARKER`(`매출액(수익)`)와 선택 판정 행 `CONSOL_SELECTION_LABEL`(`당기순이익`).

테스트의 비교 기준은 손으로 옮기지 않고 실행 시점에 뽑는다: 필수 목록은 `analysis.py`의 `df_fs_(ann|quar).loc["…"]` 문자열, 19/20 목록은 spec.md D7 줄의 "소스 순서:" 뒤 계정명(순서까지 비교), 별칭 원천·접기 부모 코드는 실응답 fixture(005930 C, 403870 B, 330590 B), 별칭표 중복 키는 모듈 소스의 dict 리터럴 AST.

RED(모듈이 없는 상태에서 테스트만 추가):

```text
$ ls fnguide/account_alias.py; /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_alias.py -q -p no:cacheprovider --tb=short -W ignore::UserWarning; echo "exit=$?"
ls: fnguide/account_alias.py: No such file or directory
...
tests/fnguide/test_wcomp_alias.py:18: in <module>
    from fnguide import account_alias as aa
E   ImportError: cannot import name 'account_alias' from 'fnguide' (/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/fnguide/__init__.py)
=========================== short test summary info ============================
ERROR tests/fnguide/test_wcomp_alias.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.06s
exit=2
```

GREEN:

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_alias.py -q -p no:cacheprovider --tb=short -W ignore::UserWarning; echo "exit=$?"
..................                                                       [100%]
18 passed in 0.29s
exit=0
```

판별력 확인(교훈 #9): 모듈 RED는 "모듈 없음"만 증명하므로, GREEN 뒤에 표를 메모리에서만 하나씩 틀리게 바꾸고 해당 테스트 함수를 직접 호출했다(파일 변경 없음, 마지막에 원복 확인). 11가지 변형 모두 실패했다.

```text
RED | asset list order swapped | AssertionError
RED | liability label dropped | AssertionError
RED | required missing 재고자산 | AssertionError
RED | alias 투자자산 removed -> no source | AssertionError
RED | alias source typo | AssertionError
RED | zero-row widened | AssertionError
RED | fold target to 유동금융자산 | AssertionError
RED | cashflow rename to 지배주주순이익 | AssertionError
RED | multi-row missing 법인세비용 | AssertionError
RED | alias chain | AssertionError
restored True
23 22
RED | duplicate literal key detected
```

마지막 두 줄은 모듈 소스 문자열에 `"자산총계": "자산"` 줄을 하나 더 넣은 사본을 AST 판정 함수에 먹인 결과다(키 23개, 고유 22개 → 실패).

기본 스위트:

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide tests/test_analysis_api.py -q -p no:cacheprovider | tail -1
120 passed, 94 deselected, 1 xfailed, 1 warning in 0.46s
```

M1 102 passed + 신규 18 = 120. `crawler.py`·PRESERVE 경로는 바꾸지 않았다(`git diff --stat 3bfddcf -- fnguide` 출력 없음, 신규 파일만 미추적 상태).

#### M2 미검증(Gaps)

- 필수 목록은 REQ-WC-010 문구대로 "analysis.py가 찾는 계정 + 대시보드 전용 3개"다. 대시보드·analyzer가 찾는 `매출액`·`자산`·`자본`·`지배기업주주지분`은 이 목록에 없다 — `매출액`은 레이아웃 표지와 짝인 별칭이라 일반 레이아웃에서 늘 생기고, `자산`·`부채` 부재는 REQ-WC-011 (b)가 따로 경고한다. 나머지 둘의 부재 경고는 SPEC 범위에 없다.
- 필수 계정마다 출처가 있다는 검사는 일반 레이아웃 세 종목(005930 C, 403870 B, 330590 B)의 연간 응답에서만 했다. 분기 응답과 다른 종목은 보지 않았다.
- 충당부채 별칭의 의미 일치는 M1 V-4(두 종목)의 계층 관측에 기댄다. 옛 사이트 화면과의 대조는 불가능하다(plan.md Q-E).

### M3 — `read_fs` 재작성 (2026-10-09)

#### M3 증거

착수 기준: HEAD `9f5b03d`(M2), 같은 워크트리. GREEN 커밋 `2adc99f`.

- `fnguide/crawler.py`: 옛 상수 `_FS_URL`·`_SNAP_URL`의 정의를 지우고 `read_fs`를 wcomp JSON 리더로 바꿨다. 보조 함수는 `_fetch`, `_check_dataset`, `_parse`, `_norm`, `_to_float`, `_period`, `_choose_consol`, `_frame`, `_check_alignment`, `_first_row`, `_fold`, `_ensure_multi_rows`, `_supplement`, `_check_balance`, `_yoy_base`(클래스 없음). `read_snapshot`·`get_fnguide`·`read_consensus` 본문과 `_CONS_D_URL`·`_CONS_B_URL`은 그대로다.
- 계정명은 모두 `account_alias`에서 참조한다. `account_alias.py`는 M3에서 바꾸지 않았다.
- 테스트: `tests/fnguide/test_wcomp_reader.py` 50건(AC-WC-002~010, 대조 포함, 리디렉션 추종 오류 HTML 1건과 형식 오류 JSON 1건 포함). 대조 테스트용으로 plan 표본의 403870 `C`·005930 `B` 나머지 응답 10건을 fixture에 추가했다(라이브 요청 없음, README 갱신).
- 라우터 경유 사례(`tests/test_analysis_api_wcomp.py`: AC-WC-006 (d)·009 (a)(b)·010 (가)(나)의 503/404, AC-WC-014)는 `get_fnguide`가 M5 전까지 옛 `read_snapshot`·`read_consensus`를 부르므로 M3에서 만들지 않았다. AC-WC-010의 `get_fnguide` 수준 기록도 M5 몫이다 — M3 테스트는 같은 단언을 `read_fs` 수준에서 한다.

RED(구현 전, 테스트만 추가 — `git diff --stat -- fnguide` 출력 없음):

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider --tb=line -W ignore::UserWarning
(259줄 중 실패 원인 집계 — `grep -E "^E  " … | sort | uniq -c`)
  27 E   AssertionError: fixture 없음: SVD_Finance.asp?pGB=1&cID=&MenuYn=Y&ReportGB=&NewMenuID=103&stkGb=701&gicode=A005930_None_None_None.json
   4 E   AttributeError: <module 'fnguide.crawler' …> has no attribute '_choose_consol'
   2 E   AssertionError: fixture 없음: SVD_Finance.asp?…&gicode=A403870_None_None_None.json
   1 E   IndexError: list index out of range
   1 E   AttributeError: … has no attribute '_yoy_base'
   1 E   AttributeError: … has no attribute '_TIMEOUT'
   1 E   AttributeError: … has no attribute '_STATEMENT_ORDER'
   1 E   AttributeError: … has no attribute '_RECENT_MARK'
   1 E   AttributeError: … has no attribute '_first_row'
   1 E   AttributeError: … has no attribute '_check_dataset'
   1 E   AttributeError: … has no attribute '_check_balance'
(마지막 줄)
49 failed in 0.32s
```

옛 `read_fs`가 옛 호스트 URL(`SVD_Finance.asp`)을 요청해 가짜 사이트에 fixture가 없다는 실패가 대부분이다. 형식 오류 JSON 테스트(50번째)는 GREEN 뒤 커버리지 확인에서 추가했다(아래 커버리지 참조).

GREEN:

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider --tb=short -W ignore::UserWarning
.................................................                        [100%]
49 passed in 0.57s
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_reader.py tests/fnguide/test_wcomp_repro.py -q -p no:cacheprovider -W ignore::UserWarning | tail -1
51 passed in 0.40s
```

AC-WC-001: `test_wcomp_repro.py`의 `xfail(raises=IndexError, strict=True)` 표지를 지웠다.

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_repro.py -q -p no:cacheprovider -k ac_wc_001 -W ignore::UserWarning
.                                                                        [100%]
1 passed, 1 deselected in 0.19s
```

#### 되돌림 관측 방법 (AC-WC-002 ~ 010 공통)

GREEN 커밋(`2adc99f`) 뒤 `fnguide/crawler.py`·`fnguide/account_alias.py`를 세션 scratchpad에 복사해 두고, AC의 "되돌림 시 관측값"이 지목한 한 곳만 Edit로 고친 뒤 그 AC의 **긍정** 테스트를 돌리고, 복사본을 덮어써 복원했다. 매번 복원 직후 `git status --short` 출력은 `?? .moai/logs/` 한 줄(착수 전부터 있던 무관한 미추적 디렉터리)이었고, 마지막 복원 뒤 `git diff --stat`은 출력이 없었다. 출력은 `--tb=line`(일부 `--tb=short`) 실행에서 `E`·경로·요약 줄만 골라 옮겼다.

#### RED 관측 — AC-WC-002

되돌림: `account_alias.py`의 `ALIASES`를 `{}`로(접기는 그대로). 명령 `pytest tests/fnguide/test_wcomp_reader.py -k "ac_wc_002 and not contrast" --tb=line`.

```text
WARNING  fnguide.crawler:crawler.py:345 005930 정합성 검사 건너뜀: 분기 표에 '자산' 행 없음
WARNING  fnguide.crawler:crawler.py:345 005930 정합성 검사 건너뜀: 분기 표에 '부채' 행 없음
/Users/byunjungwon/Dev/my_chart/.venv/lib/python3.13/site-packages/pandas/core/indexes/base.py:3648: KeyError: '매입채무및기타유동채무'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_002_alias_layer_and_shareholder_equity
1 failed, 1 passed, 47 deselected in 0.29s
$ git status --short
?? .moai/logs/
```

예측(`KeyError: '매입채무및기타유동채무'`)과 일치. 예측의 둘째 문장(`analyze_dashboard`의 `health_indicators`가 `None`)은 `analyze_dashboard`가 M5 전 `get_fnguide`를 거쳐 옛 `read_snapshot`을 부르므로 관측하지 못했다(Gaps).

#### RED 관측 — AC-WC-003

되돌림: `_choose_consol`의 규칙 루프 앞에 순진한 `return`을 하나씩 넣었다. 명령 `-k ac_wc_003_consolidation_selection --tb=line`.

```text
(가) return "C"
E   AssertionError: assert 'IFRS(연결)' == 'IFRS(별도)'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_003_consolidation_selection[a]
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_003_consolidation_selection[b]
2 failed, 2 passed, 45 deselected in 0.21s
(나) return "C" if any(c.get(f"VAL{i}") is not None for i in range(1, 5)) else "B"
.../test_wcomp_reader.py:201: AssertionError: assert 'IFRS(연결)' == 'IFRS(별도)'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_003_consolidation_selection[b]
1 failed, 3 passed, 45 deselected in 0.22s
(다) return "B"
.../test_wcomp_reader.py:201: AssertionError: assert 'IFRS(별도)' == 'IFRS(연결)'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_003_consolidation_selection[c]
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_003_consolidation_selection[d]
2 failed, 2 passed, 45 deselected in 0.21s
(라) return "C" if c.get("VAL4") is not None else "B"
.../test_wcomp_reader.py:201: AssertionError: assert 'IFRS(별도)' == 'IFRS(연결)'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_003_consolidation_selection[d]
1 failed, 3 passed, 45 deselected in 0.21s
$ git status --short
?? .moai/logs/
```

예측 (가) 403870 `IFRS(연결)`, (나) 001750 `IFRS(연결)`, (다) 005930 `IFRS(별도)`, (라) (d) `IFRS(별도)`와 모두 일치. (가)는 001750도 함께 깨고, (다)는 (d)도 함께 깬다(예측 밖이지만 모순 아님). 값 쪽 예측(`0.0`, `336866.01`)은 스위트 안 `_contrast` 테스트 4건이 단언한다.

#### RED 관측 — AC-WC-004

되돌림: `account_alias.py`의 `CASHFLOW_RENAMES`를 `{}`로. 명령 `-k "ac_wc_004 and not contrast" --tb=line`.

```text
E   TypeError: float() argument must be a string or a real number, not 'Series'
/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/fnguide/dashboard.py:295: TypeError: float() argument must be a string or a real number, not 'Series'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_004_net_income_single_row
1 failed, 48 deselected in 0.22s
$ git status --short
?? .moai/logs/
```

예측과 일치.

#### RED 관측 — AC-WC-005

되돌림 1: `_ensure_multi_rows`의 조건을 `if False and …`로(0 행 보충 제거). 되돌림 2: `_STATEMENT_ORDER`를 현금흐름 → 대차 → 손익으로. 명령 `-k "ac_wc_005 and not contrast" --tb=line`.

```text
(되돌림 1)
E   assert np.float64(-44808.35) == 30783.83 ± 0.01
.../test_wcomp_reader.py:273: assert np.float64(-44808.35) == 30783.83 ± 0.01
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_005_tax_and_interest_multi_row
1 failed, 48 deselected in 0.22s
(되돌림 2)
E   assert np.float64(0.0) == 9039.18 ± 0.01
.../test_wcomp_reader.py:275: assert np.float64(0.0) == 9039.18 ± 0.01
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_005_tax_and_interest_multi_row
1 failed, 48 deselected in 0.28s
$ git status --short
?? .moai/logs/
```

예측 `법인세비용` 2024/12 = `-44808.35`(예외 없음), `이자비용` 2024/12 = `0.0`과 일치. 2026/06 = `13198.16`은 긍정 테스트가 앞 단언에서 멈춰 이 실행에서는 보이지 않으며, 스위트의 `test_ac_wc_005_contrast_no_zero_row_padding`이 단언한다.

#### RED 관측 — AC-WC-006

되돌림 1: `_yoy_base` 첫 줄에 `return None`. 되돌림 2: 표지 검사를 `if False and …`로(늘 VAL5). 되돌림 3: `_check_alignment` 호출을 `pass`로. 되돌림 4: `_yoy_base`의 별칭 적용을 빼고 `return df`.

```text
(되돌림 1) -k ac_wc_006_a
E   assert (None is not None)
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_006_a_columns_and_yoy_base
1 failed, 48 deselected in 0.19s
probe yoy is None: True last yoy_revenue: -0.08463
(되돌림 2) -k "(ac_wc_006_b or ac_wc_006_c) and not contrast"
E   assert                            2025/12 (전년동기)\n매출액                                708.80\n…총포괄이익                              196.27 is None
E   assert                            2025/06 (전년동기)\n매출액                            1537068.20\n…총포괄이익                            59812.46 is None
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_006_b_semiannual_reit
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_006_c_dec_close_columns
2 failed, 47 deselected in 0.30s
(되돌림 3) -k ac_wc_006_d
E   Failed: DID NOT RAISE <class 'RuntimeError'>
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_006_d_period_misalignment_is_runtime_error
1 failed, 48 deselected in 0.35s
(되돌림 4) -k ac_wc_006_a
E   KeyError: '매출액'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_006_a_columns_and_yoy_base
1 failed, 48 deselected in 2.94s
probe yoy is None: False | 매출액 in yoy: False | last yoy_revenue: -0.08463
$ git status --short
?? .moai/logs/
```

`probe` 줄은 같은 되돌림 상태에서 fixture를 먹인 `read_fs("005930")` → `_calc_business_performance`의 마지막 매출 YoY를 직접 출력한 것이다. 네 예측 모두 일치: 늘 `None`이면 `-0.08463`, 표지 무시면 (b)·(c)가 `None` 아님, 기간 검사 제거면 (d) 예외 없음, 별칭 제거면 대시보드가 `KeyError`를 삼켜 예외 없이 `-0.08463`(긍정 테스트는 `yoy["매출액"]`을 직접 읽어 `KeyError`로 실패).

#### RED 관측 — AC-WC-007

되돌림 1: `account_alias.py`의 `FOLD_PARENT_TO_OTHER`를 `{}`로. 되돌림 2: `read_fs`의 `_check_balance` 호출을 `pass`로. 되돌림 3: `_first_row`의 부재 처리를 빼고 `return int(hits[0])`.

```text
(되돌림 1) -k ac_wc_007_fold_keeps --tb=short
E   AssertionError: assert ['005930 정합성 ...+257.15', ...] == []
E     Left contains 8 more items, first extra item: '005930 정합성 불일치: 연간 표 2023/12 열 자산 차이 +6353.93'
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 연간 표 2023/12 열 자산 차이 +6353.93
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 연간 표 2024/12 열 자산 차이 +368.77
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 연간 표 2025/12 열 자산 차이 +257.15
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 연간 표 2026/06 열 자산 차이 +460.00
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 분기 표 2025/09 열 자산 차이 +201.71
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 분기 표 2025/12 열 자산 차이 +257.15
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 분기 표 2026/03 열 자산 차이 +232.38
WARNING  fnguide.crawler:crawler.py:352 005930 정합성 불일치: 분기 표 2026/06 열 자산 차이 +460.00
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_007_fold_keeps_balance_guard_silent
1 failed, 48 deselected in 0.32s
(되돌림 2) -k ac_wc_007_manipulated
E   assert 0 == 1
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_007_manipulated_other_asset_warns_once
1 failed, 48 deselected in 0.20s
(되돌림 3) -k ac_wc_007_missing
E   IndexError: index 0 is out of bounds for axis 0 with size 0
.../fnguide/crawler.py:286: IndexError: index 0 is out of bounds for axis 0 with size 0
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_007_missing_fold_destination_warns
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_007_missing_asset_total_warns
2 failed, 47 deselected in 0.20s
$ git status --short
?? .moai/logs/
```

예측과 일치: 접기 제거 시 경고 8건과 금액 8개가 acceptance의 값(연간 `6353.93, 368.77, 257.15, 460.00`, 분기 `201.71, 257.15, 232.38, 460.00`)과 같다. 가드 제거 시 조작본 1 경고 0건, 부재 처리 제거 시 조작본 2·3에서 `IndexError`가 `read_fs` 밖으로 샌다.

#### RED 관측 — AC-WC-008

되돌림: `_supplement`의 보충 대상을 `aa.ZERO_ROW_LABELS`에서 `aa.REQUIRED_LABELS`로(부재한 필수 계정 모두 0 보충). 명령 `-k "ac_wc_008 and not contrast" --tb=line`.

```text
E   AssertionError: assert '재고자산' not in Index(['매출액', '매출원가', '매출총이익', …, '법인세비용', '재고자산',\n       '관계기업등지분관련투자자산'],\n      dtype='str', length=200)
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_008_b_unlisted_required_label_warns_without_row
E   AssertionError: assert '매출원가' not in Index(['매출액', '매출총이익', …, '관계기업등지분관련투자자산',\n       '매출원가'],\n      dtype='str', length=200)
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_008_c_dashboard_only_label_warns
2 failed, 1 passed, 46 deselected in 0.22s
$ git status --short
?? .moai/logs/
```

예측((b)에서 `재고자산` 행이 생김)과 일치하고, (c)의 `매출원가`도 같은 이유로 생겼다. 값 `0.0`은 `test_ac_wc_008_contrast_zero_fill_all_required`가 단언한다.

#### RED 관측 — AC-WC-009

되돌림: `_check_dataset` 첫 줄에 `return`(빈 data·null 머리글 검사 제거). 명령 `-k "ac_wc_009 and not contrast" --tb=line`.

```text
E   TypeError: expected string or bytes-like object, got 'NoneType'
/Users/byunjungwon/.local/share/uv/python/cpython-3.13.11-macos-aarch64-none/lib/python3.13/re/__init__.py:167: TypeError: expected string or bytes-like object, got 'NoneType'
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_b_empty_dataset - T...
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_c_null_header_checked_before_alignment
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_d_fewer_than_four_periods
3 failed, 5 passed, 41 deselected in 0.21s
$ git status --short
?? .moai/logs/
```

예측("`read_fs("005935")`가 `ValueError`를 내지 않는다 — 다른 예외로 샘")과 일치: null 기간이 `_period`의 정규식에서 `TypeError`로 샌다(라우터는 503이 된다). (a) HTML·(e) 코드 검증·리디렉션 사례는 이 검사와 무관해 통과했다.

**2026-10-11 재관측(감사 보강 F10 뒤, 커밋 `7ba072a` 위).** 스위트의 대조 `test_ac_wc_009_contrast_no_dataset_check`가 이제 `pytest.raises(TypeError)`만 인정한다(전에는 `ValueError`가 아닌 모든 예외를 통과시켰다). 되돌림: `_parse`의 `_check_dataset(...)` 호출을 `pass`로. 명령 `pytest tests/fnguide/test_wcomp_reader.py tests/test_analysis_api_wcomp.py -k ac_wc_009 -rA --tb=line`.

```text
E   TypeError: expected string or bytes-like object, got 'NoneType'   (3회)
<py>/re/__init__.py:167: TypeError: expected string or bytes-like object, got 'NoneType'
E   assert 503 == 404
tests/test_analysis_api_wcomp.py:123: assert 503 == 404
PASSED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_a_error_html
PASSED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_e_code_validation_no_request[00593a]
PASSED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_e_code_validation_no_request[０05930]
PASSED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_e_code_validation_no_request[5930]
PASSED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_redirect_followed_error_html_is_value_error
PASSED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_malformed_json_body_is_value_error
PASSED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_contrast_no_dataset_check
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_009_router_error_page_and_empty_dataset_are_404[999999]
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_b_empty_dataset - T...
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_c_null_header_checked_before_alignment
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_009_d_fewer_than_four_periods
FAILED tests/test_analysis_api_wcomp.py::test_ac_wc_009_router_error_page_and_empty_dataset_are_404[005935]
4 failed, 8 passed, 50 deselected in 0.75s
(복원 후)
$ git status --short
?? .moai/logs/
?? .moai/reports/sync-audit/
$ git diff --stat
(출력 없음)
```

긍정 테스트 3건이 M3 기록과 같은 `TypeError`로 실패했고, M5에서 생긴 라우터 사례(005935)도 404 대신 503으로 실패했다(실패 4건 — M3 시점에는 라우터 테스트가 없었다). 고친 대조는 통과했다.

#### RED 관측 — AC-WC-010

되돌림: `_fetch`의 `requests.get`에서 `timeout=_TIMEOUT` 인자를 지움. 명령 `-k "ac_wc_010 and not contrast" --tb=line`.

```text
E   AssertionError: assert [('timeout', ...', None), ...] == []
/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/tests/fnguide/test_wcomp_reader.py:611: AssertionError: assert [('timeout', ...', None), ...] == []
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_010_request_hygiene - A...
1 failed, 2 passed, 46 deselected in 0.20s
$ git status --short
?? .moai/logs/
$ git diff --stat
(출력 없음)
```

예측("첫 기록 호출에서 `timeout` 키 없음")과 일치.

#### M3 확인 과제 V-2 · V-3

V-2 — 통과. fixture 쪽(plan.md 명령 그대로)과 구현된 `read_fs` 결과:

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -c "import json;d=json.load(open('tests/fnguide/fixtures/wcomp/getFinIncome_005930_Y_C.json',encoding='utf-8-sig'))['dataset']['data'];print([(r['AC_CODE'],r['P_AC_CODE'],r['VAL1']) for r in d if r['NAME'].replace(' ','') in ('이자비용','법인세비용')])"
[('202560', '202550', '9302.53'), ('204800', '201830', None), ('203130', None, '-44808.35')]
(가짜 사이트로 read_fs("005930") 후 df.loc['이자비용'].iloc[0], df.loc['법인세비용'].iloc[0])
이자비용 first row: {'2023/12': 9302.53, '2024/12': 9039.18, '2025/12': 6057.83, '2026/06': 4746.72}
법인세비용 first row: {'2023/12': -44808.35, '2024/12': 30783.83, '2025/12': 42746.66, '2026/06': 344185.06}
rows: 3 2
```

이자비용 첫 행 = AC_CODE 202560(부모 202550) 2023/12 `9302.53`, 법인세비용 첫 행 = 203130 2023/12 `-44808.35`. 이 정체가 옛 화면의 "첫 행"과 같았는지는 확인 불가(Gaps).

V-3 — 통과(테스트가 열 4개 `2022/12…2025/12`, `df_yoy_base_ann is None`, `calc_weight_coeff == (1.0, 2.0, 3.0, 6.0)`을 단언).

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k "ac_wc_006 and dec" -W ignore::UserWarning
.                                                                        [100%]
1 passed, 48 deselected in 0.20s
```

#### 커버리지

공용 venv에는 `coverage`가 없어(설치하지 않음) M1에서 pre-commit 게이트가 만든 워크트리 전용 `.venv`(coverage 7.13.4)로 acceptance §E DoD 명령을 돌렸다.

```text
$ .venv/bin/python -m coverage run --data-file=<scratchpad>/.coverage --source=fnguide -m pytest tests/fnguide -q -p no:cacheprovider | tail -1
157 passed, 94 deselected, 1 warning in 1.08s
$ .venv/bin/python -m coverage report --data-file=<scratchpad>/.coverage --include='fnguide/crawler.py,fnguide/account_alias.py' -m
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
fnguide/account_alias.py      13      0   100%
fnguide/crawler.py           281    103    63%   68-169, 174-177, 467-490, 518-527
--------------------------------------------------------
TOTAL                        294    103    65%
```

`crawler.py` 미달 줄은 모두 M3가 손대지 않은 함수다: 68-169 `read_snapshot`(M4), 174-177 `_extract_snap_table`(M4), 467-490 `read_consensus`(호출되지 않음), 518-527 `get_fnguide`(M5). 새 리더 코드(180-452행)의 미달 줄은 0이다. 직전 실행에서 남았던 220-221(형식 오류 JSON 분기)은 `test_ac_wc_009_malformed_json_body_is_value_error`를 더해 덮었다. 파일 전체 85% 기준은 M4·M5 뒤에 다시 잰다.

#### 005930 캐시 미스 소요 시간

측정하지 않음. `get_fnguide`가 M5 전까지 옛 `read_snapshot`을 부르고, M3에서는 새 라이브 요청을 하지 않았다.

#### M3 발견 사항

- `_SNAP_URL` 정의를 지웠으므로 손대지 말라는 `read_snapshot` 본문(68행 `snap_url = _SNAP_URL.format(code=code)`)이 이제 정의되지 않은 이름을 참조한다. 호출하면 `NameError`다 — 옛 호스트가 안내 페이지만 돌려주므로 이미 동작하지 않던 함수이고, M4가 본문을 바꿀 때 사라진다. 기본 스위트에는 이 경로를 부르는 테스트가 없다(170 passed).
- AC-WC-015 4번 AST 프로브는 이미 최종 기대 출력 `['_CONS_B_URL', '_CONS_D_URL'] ['read_consensus']`를 낸다. `_SNAP_URL`이 더는 최상위 대입이 아니라서 `read_snapshot`이 옛 호스트 사용 함수로 잡히지 않기 때문이다(옛 호스트 문자열 자체가 사라짐).
- 다중 행 보정은 이름이 **한 행 이상 있을 때만** 0 행을 채운다(0행이면 채우지 않음). REQ-WC-008 문구는 "두 행 이상 보장"이지만, 이름이 아예 없으면 첫 행이 손익계산서 값이라는 조건을 만족시킬 수 없고 REQ-WC-010이 필수 계정 부재를 경고만 하라고 하므로 그쪽을 따랐다. 관측한 표본은 모두 두 이름이 손익계산서에 있다.
- 접힌 하위 행은 `기타*`에 더한 뒤 표에서 지운다. SPEC은 지울지 정하지 않았다. 005930에서 `계약자산`·`당기손익-공정가치측정금융부채` 등이 유동·비유동 양쪽에 같은 이름으로 있어, 남기면 중복 이름 행이 늘어난다.

#### M3 미검증(Gaps)

- AC-WC-002 예측의 `analyze_dashboard().health_indicators is None`, AC-WC-006 (d)·009 (a)(b)·010의 라우터 응답 코드(503/404), AC-WC-010의 `get_fnguide` 수준 단언은 M5 이후로 미뤘다.
- 이자비용·법인세비용 "첫 행"이 옛 화면의 첫 행과 같았는지, 12월 결산 직후 실제 응답 모양은 확인할 수 없다(V-2·V-3 통과 조건이 명시한 Gaps).
- 005935·999999는 Income Y `C` 응답 하나를 모든 요청에 돌려줬다(README).
- `ruff`가 없어 새 코드 린트를 돌리지 못했다.

### M4 — `read_snapshot` 재작성 (2026-10-10)

#### M4 증거

착수 기준: HEAD `3041d46`(M3), 같은 워크트리. GREEN 커밋 `9cb4b7c`.

- `fnguide/crawler.py`: `read_snapshot(code, account_type="IFRS(연결)")`를 Snapshot HTML 1회 요청 리더로 바꿨다. 요청은 M3의 `_fetch`를 그대로 쓴다(재무제표 전용이던 `freq`·`consol` 인자를 선택 인자로 바꿈 — 타임아웃·헤더·상태 판정·리디렉션 기본값이 공용). 보조 함수는 `_label`, `_row_value`, `_check_snapshot_code`. 표 머리글은 숨은 설명 `<dl>`을 뺀 보이는 글자를 공백 없이 정확히 비교한다. 반환은 `(report, 빈 DataFrame, 빈 DataFrame)`이고 `account_type`은 받기만 한다.
- `report` 키는 REQ-WC-013의 12개다(분석 코드가 읽는 키도 이 12개뿐 — `grep -n 'report\[\|report.get' fnguide/*.py backend -r | grep -v crawler.py` 결과 analyzer.py 165-169·229·257-261, dashboard.py 552·934·986). 옛 report에만 있던 `52주.최고가`·`거래대금(억원)`·`시가총액(보통주,억원)`·`액면가`·`유통주식수`·`유통주식비율`은 소비처가 없어 만들지 않는다. 페이지 라벨(`자사주`·`52주베타` 등)은 crawler.py 상단 상수로 두었고 `account_alias.py`는 바꾸지 않았다.
- 옛 스냅샷 파서 전용이던 `_extract_snap_table`과 그 때문에만 쓰이던 `StringIO`·`lxml.html` import를 지웠다(`grep -rn -E "_extract_snap_table|read_snapshot|StringIO|BeautifulSoup|html\.fromstring|lxml" fnguide backend tests` 결과 `_extract_snap_table`·`StringIO`·`lxml`의 사용처는 옛 `read_snapshot` 본문뿐이었다).
- 테스트: `tests/fnguide/test_wcomp_snapshot.py` 13건(AC-WC-011 3, AC-WC-012 9, 코드 형식 검증 1).
- `analyze_dashboard("005930").company_name` 단언은 `get_fnguide`가 M5 전까지 옛 호스트 `read_consensus`를 부르므로, 그 두 테스트에서만 `crawler.read_consensus`를 빈 DataFrame을 돌려주는 함수로 바꿨다(소비처 없음 — spec §1.3). M5에서 호출이 사라지면 이 대체를 지운다.

RED(구현 전, 테스트만 추가 — `git diff --stat -- fnguide` 출력 없음):

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_snapshot.py -q -p no:cacheprovider --tb=line -W ignore::UserWarning | grep -E "^E |^/|FAILED|passed|failed" | sort | uniq -c | sort -rn
   9 E   NameError: name '_SNAP_URL' is not defined
   9 /Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/fnguide/crawler.py:68: NameError: name '_SNAP_URL' is not defined
   1 E   AttributeError: <module 'fnguide.crawler' …> has no attribute '_row_value'
   1 E   AttributeError: <module 'fnguide.crawler' …> has no attribute '_NAME_ID'
   1 E   AttributeError: <module 'fnguide.crawler' …> has no attribute '_check_snapshot_code'
   (FAILED 줄 12개 생략 — 테스트 12건 모두)
   1 12 failed in 0.58s
```

GREEN:

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_snapshot.py -q -p no:cacheprovider --tb=short -W ignore::UserWarning
............                                                             [100%]
12 passed in 1.13s
$ … -k ac_wc_011 | tail -1
3 passed, 9 deselected in 0.23s
$ … -k ac_wc_012 | tail -1
9 passed, 3 deselected in 1.15s
```

(코드 형식 검증 테스트는 GREEN 뒤 커버리지에서 `read_snapshot`의 검증 줄이 비어 추가했다 — 13건.)

fixture로 `read_fs` + `read_snapshot`을 이어 부른 요청 기록(AC-WC-013 예산 8의 사전 확인, `get_fnguide` 수준 단언은 M5):

```text
read_snapshot ok: 삼성전자 1.27893 True True
requests: 8 [('getFinIncome', 'Y', 'C'), ('getFinIncome', 'Y', 'B'), ('getFinIncome', 'Q', 'C'), ('getFinBalance', 'Y', 'C'), ('getFinBalance', 'Q', 'C'), ('getFinCashFlow', 'Y', 'C'), ('getFinCashFlow', 'Q', 'C'), ('Snapshot', None, None)]
PER '42.05'
12M PER '4.34'
업종 PER '33.64'
PBR '4.31'
배당수익률 '0.60 %'
```

#### RED 관측 — AC-WC-011

되돌림: `read_snapshot`의 `_check_snapshot_code(soup, code)` 호출을 `pass`로. 명령 `pytest tests/fnguide/test_wcomp_snapshot.py -k "ac_wc_011 and not contrast" --tb=line`, 이어서 같은 상태에서 005935 fixture로 직접 호출.

```text
E   Failed: DID NOT RAISE <class 'ValueError'>
/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/tests/fnguide/test_wcomp_snapshot.py:87: Failed: DID NOT RAISE <class 'ValueError'>
E   Failed: DID NOT RAISE <class 'ValueError'>
/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/tests/fnguide/test_wcomp_snapshot.py:92: Failed: DID NOT RAISE <class 'ValueError'>
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_011_served_as_other_company_raises
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_011_missing_cmp_cd_raises
2 failed, 10 deselected in 0.21s
probe read_snapshot("005935") 종목명 = 삼성전자
$ git status --short
?? .moai/logs/
```

예측("`#cmp_cd` 검사를 빼면 (a)가 예외 없이 `report["종목명"] == "삼성전자"`")과 일치. 999999(`#cmp_cd` 없는 302 본문)도 예외 없이 반환된다(반환된 report 내용은 출력하지 않았다).

#### RED 관측 — AC-WC-012

되돌림 1: `종목명` 대입을 `if False and …`로(채우지 않음). 되돌림 2(판별력 확인): `_row_value`의 정확 일치를 `startswith`로. 명령 `-k "ac_wc_012 and not contrast" --tb=line`, `-k ac_wc_012_treasury --tb=line`.

```text
(되돌림 1)
E   AssertionError: assert {'12M PER', '...식수(우선주)', ...} >= {'12M PER', '...식수(우선주)', ...}
E   KeyError: '종목명'   (company_name 4종목 각각)
E   AssertionError: assert '005930' == '삼성전자'
/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/tests/fnguide/test_wcomp_snapshot.py:143: AssertionError: assert '005930' == '삼성전자'
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_report_values_005930
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_company_name[403870-HPSP]
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_company_name[105560-KB금융]
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_company_name[001750-한양증권]
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_company_name[330590-롯데리츠]
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_analyze_dashboard_company_name
6 failed, 1 passed, 5 deselected in 0.69s
(되돌림 2)
E   assert 1 == 0
/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/tests/fnguide/test_wcomp_snapshot.py:134: assert 1 == 0
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_treasury_exact_row_only
1 failed, 11 deselected in 0.22s
$ git status --short
?? .moai/logs/
$ git diff --stat
(출력 없음)
```

예측("`종목명`을 채우지 않으면 `company_name == "005930"`")과 일치. 판별력 근거로 적힌 "접두어 일치 구현은 조작본에서 `133670794` 또는 `1`"도 `1`(정확 `자사주` 행을 지운 뒤 `자사주(자사주+자사주신탁)` 행의 첫 칸 보유자 수)로 관측했다.

#### 커버리지

```text
$ .venv/bin/python -m coverage run --data-file=<scratchpad>/.coverage --source=fnguide -m pytest tests/fnguide -q -p no:cacheprovider | tail -1
170 passed, 94 deselected, 1 warning in 1.99s
$ .venv/bin/python -m coverage report --data-file=<scratchpad>/.coverage --include='fnguide/crawler.py,fnguide/account_alias.py' -m
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
fnguide/account_alias.py      13      0   100%
fnguide/crawler.py           246     16    93%   438-461
--------------------------------------------------------
TOTAL                        259     16    94%
```

미달 438-461은 호출되지 않는 `read_consensus` 본문이다. 두 파일 모두 85% 이상.

#### M4 발견 사항

- `배당수익률` 값은 페이지 글자 그대로 `'0.60 %'`(퍼센트 기호 포함)다. 옛 값의 형태는 관측할 수 없고 analyzer는 `str(...)`로만 쓴다. `PER` 등도 문자열이다(옛 코드도 문자열).
- 999999 스냅샷 fixture는 리디렉션을 따라가지 않은 302 본문이다. 실제 `requests`는 302를 따라가므로 운영에서 받는 최종 본문은 관측하지 않았다(research.md F-17 "추정, 미관측"). 어느 쪽이든 `#cmp_cd`가 요청 코드와 같을 수 없다는 가정에 기댄다.

#### M4 미검증(Gaps)

- `ruff` 없음(린트 미실행).
- 001750·330590·105560 스냅샷은 회사명과 키 존재만 단언했고 수치는 고정하지 않았다(acceptance가 고정하지 않음).

### M5 — `get_fnguide` 정리 (2026-10-10)

#### M5 증거

착수 기준: HEAD `ae69a93`(M4), 같은 워크트리. GREEN 커밋 `b4bf7ba`.

- `fnguide/crawler.py`: `get_fnguide`가 `read_fs` → `read_snapshot`만 부르고 위치 4(`df_cons`)를 빈 DataFrame으로 반환한다(위치 2·3은 `read_snapshot`이 돌려주는 빈 DataFrame). 시그니처·8-튜플 순서는 그대로이고 `@MX:ANCHOR`를 달았다. `read_consensus`와 두 상수는 정의만 남아 있다(`fnguide/__init__.py` 무수정).
- M4가 `test_wcomp_snapshot.py`의 `analyze_dashboard` 테스트 두 곳에 넣은 `read_consensus` 임시 대체를 지웠다. 두 테스트는 대체 없이 통과한다(`-k "analyze_dashboard or no_company_name"` → `2 passed, 13 deselected`).
- 새 테스트: `tests/test_analysis_api_wcomp.py` 9건(라우터·`get_fnguide` 수준, 실제 `get_dashboard` → `analyze_dashboard` → `get_fnguide` 경로, 맨 아래 `requests.Session.request`만 fixture로 대체, 테스트마다 서비스 5분 캐시 비움), `test_wcomp_snapshot.py`에 AC-WC-013 2건, `test_wcomp_reader.py`에 AC-WC-014 `read_fs` 2건.

RED(구현 전, 테스트만 추가·대체 제거 — `git diff --stat -- fnguide` 출력 없음):

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/test_analysis_api_wcomp.py tests/fnguide/test_wcomp_snapshot.py tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider --tb=line -W ignore::UserWarning
(실패 원인 집계)
   4 E   json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
   3 E   assert 503 == 200
   1 E   AssertionError: fixture 없음: 01_A005930_A_D.json_None_None_None.json
FAILED tests/test_analysis_api_wcomp.py::test_ac_wc_010_get_fnguide_request_hygiene
FAILED tests/test_analysis_api_wcomp.py::test_ac_wc_014_router_financial_layout_is_200_with_null_sections[105560]
FAILED tests/test_analysis_api_wcomp.py::test_ac_wc_014_router_financial_layout_is_200_with_null_sections[001750]
FAILED tests/test_analysis_api_wcomp.py::test_general_layout_005930_router_returns_filled_sections
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_analyze_dashboard_company_name
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_012_contrast_no_company_name
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_013_eight_tuple_and_no_consensus_request
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_013_contrast_consensus_request_is_caught
8 failed, 68 passed in 4.38s
```

`get_fnguide`가 옛 호스트 컨센서스를 요청해 안내 페이지를 JSON으로 파싱하다 실패하고, 라우터는 그 예외를 503으로 바꾼다. 수정 전에도 통과한 라우터 사례(AC-WC-006 (d) 503, 009 (a)(b) 404, 010 (가)(나) 503)는 `read_fs` 단계에서 이미 끝나 컨센서스에 닿지 않는 경우다 — 이 사례들은 M3의 `read_fs` 수정이 만든 동작이며 M5의 대조가 아니다. AC-WC-014의 `read_fs` 2건도 M3 코드로 이미 통과한다(불변 AC).

GREEN:

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/test_analysis_api_wcomp.py tests/fnguide/test_wcomp_snapshot.py tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider --tb=short -W ignore::UserWarning
........................................................................ [ 94%]
....                                                                     [100%]
76 passed in 3.37s
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/test_analysis_api_wcomp.py -q -p no:cacheprovider -rA -W ignore::UserWarning | grep -E "^PASSED|passed|failed"
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_006_d_router_period_misalignment_is_503
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_009_router_error_page_and_empty_dataset_are_404[999999]
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_009_router_error_page_and_empty_dataset_are_404[005935]
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_010_get_fnguide_request_hygiene
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_010_router_transport_timeout_is_503
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_010_router_http_500_is_503
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_014_router_financial_layout_is_200_with_null_sections[105560]
PASSED tests/test_analysis_api_wcomp.py::test_ac_wc_014_router_financial_layout_is_200_with_null_sections[001750]
PASSED tests/test_analysis_api_wcomp.py::test_general_layout_005930_router_returns_filled_sections
9 passed in 1.94s
$ … tests/fnguide/test_wcomp_reader.py tests/fnguide/test_wcomp_snapshot.py tests/test_analysis_api_wcomp.py -k ac_wc_013 | tail -1
2 passed, 74 deselected in 0.80s
$ … -k ac_wc_014 | tail -1
4 passed, 72 deselected in 0.87s
```

AC-WC-014(불변): `read_fs` 2건(105560 `IFRS(연결)`, 001750 `IFRS(별도)`, 둘 다 `매출액` 행 없음)과 라우터 2건(200, Sections 1–7 `null`, 105560 `company_name == "KB금융"`, 001750은 비어 있지 않고 코드와 다름)이 통과 — `4 passed`. 불변 AC라 되돌림 관측 머리글을 두지 않는다.

끝까지 이어 본 결과(fixture 가짜 사이트, 실제 `analyze_dashboard` → `get_fnguide`):

```text
005930 삼성전자 requests 8 {'business_performance': 'filled', 'health_indicators': 'filled', 'balance_sheet': 'filled', 'rate_decomposition': 'filled', 'profit_waterfall': 'filled', 'trend_signals': 'filled', 'five_questions': 'filled', 'activity_ratios': 'filled'}
001750 한양증권 requests 8 {'business_performance': 'None', 'health_indicators': 'None', 'balance_sheet': 'None', 'rate_decomposition': 'None', 'profit_waterfall': 'None', 'trend_signals': 'None', 'five_questions': 'None', 'activity_ratios': 'filled'}
403870 HPSP requests 8 {… 8개 섹션 모두 'filled'}
330590 롯데리츠 requests 8 {… 8개 섹션 모두 'filled'}
105560 KB금융 requests 8 {… Sections 1–7 'None', 'activity_ratios': 'filled'}
005930 health: [('외부차입/자기자본', 0.0397), ('부채비율', 0.3188), ('차입금의존도', 0.0295), ('순차입금의존도', -0.2206), ('이자보상배율', 236.7768)]
005930 opm last: 0.4805 periods ['2023/12', '2024/12', '2025/12', '2026/06']
```

금융 레이아웃의 `activity_ratios`가 값이 모두 null인 객체로 채워지는 것은 research.md §R3 각주와 같다(acceptance가 단언하지 않음). 위 005930 지표 값은 기록용이며, FnGuide 화면과의 눈대조(acceptance §E DoD)는 아직 하지 않았다.

#### RED 관측 — AC-WC-013

(M6에서 다시 관측해 이 절의 내용을 바꿨다.) M5 첫 관측에서는 되살린 `read_consensus`가 옛 호스트 안내 페이지를 JSON으로 파싱하다 `JSONDecodeError`를 내 URL 단언에 닿지 못했다. M6에서 테스트를 고쳐(커밋 `0219614`) `get_fnguide`의 예외를 잡아 두고 요청 URL 판정을 먼저 한 뒤 예외를 다시 던지게 했다. 가짜 컨센서스 JSON fixture는 만들지 않았다.

되돌림: `get_fnguide`의 `df_cons = pd.DataFrame()`을 원래의 `time.sleep(_CRAWL_DELAY)` + `df_cons = read_consensus(code, account_type)`로 되살림(M6, HEAD `5d021cb`에 고친 테스트를 아직 커밋하지 않은 상태 — 고친 테스트는 직후 `0219614`로 커밋). 명령 `pytest tests/fnguide/test_wcomp_snapshot.py -k "ac_wc_013 and not contrast" --tb=short`.

```text
F                                                                        [100%]
=================================== FAILURES ===================================
_____________ test_ac_wc_013_eight_tuple_and_no_consensus_request ______________
tests/fnguide/test_wcomp_snapshot.py:205: in test_ac_wc_013_eight_tuple_and_no_consensus_request
    assert _host_violations(site["calls"]) == {"old_host": [], "01_06": [], "not_new_host": []}
E   AssertionError: assert {'01_06': ['h...30_A_D.json']} == {'01_06': [],...old_host': []}
E     
E     Differing items:
E     {'not_new_host': ['http://comp.fnguide.com/SVO2/json/data/01_06/01_A005930_A_D.json']} != {'not_new_host': []}
E     {'old_host': ['http://comp.fnguide.com/SVO2/json/data/01_06/01_A005930_A_D.json']} != {'old_host': []}
E     {'01_06': ['http://comp.fnguide.com/SVO2/json/data/01_06/01_A005930_A_D.json']} != {'01_06': []}
E     Use -v to get more diff
=========================== short test summary info ============================
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_013_eight_tuple_and_no_consensus_request
1 failed, 14 deselected in 0.56s
(복원 후)
$ git status --short
 M tests/fnguide/test_analysis.py
 M tests/fnguide/test_crawler.py
 M tests/fnguide/test_wcomp_snapshot.py
?? .moai/logs/
$ git diff --stat -- fnguide
(출력 없음)
```

예측("기록된 URL에 `comp.fnguide.com/SVO2/json/data/01_06/`이 나타난다 — 호스트 이름 `comp.fnguide.com`, `01_06` 포함, 두 단언 모두 실패")과 일치: 옛 호스트 판정(`old_host`)과 `01_06` 판정이 같은 URL 하나로 함께 실패했고, 새 호스트 밖 요청 판정(`not_new_host`)도 실패했다. 복원 직후 `git status`의 테스트 세 파일 수정은 이 관측 당시 아직 커밋 전이던 M6 테스트 정리이며(곧 `0219614`로 커밋), `fnguide/`의 변경은 없었다.

**2026-10-11 재관측(감사 보강 F9 뒤, 커밋 `7ba072a` 위).** 스위트의 대조 `test_ac_wc_013_contrast_consensus_request_is_caught`가 이제 `read_consensus`를 따로 부르지 않고, `get_fnguide`가 부르는 `crawler.read_snapshot`을 감싸 실제 `get_fnguide` 경로에서 컨센서스 요청이 나가게 한 뒤 판정한다. 되돌림: `get_fnguide`의 `df_cons = pd.DataFrame()`을 `time.sleep(_CRAWL_DELAY)` + `df_cons = read_consensus(code, account_type)`로. 명령 `pytest tests/fnguide/test_wcomp_snapshot.py -k ac_wc_013 -rA --tb=line`.

```text
E   AssertionError: assert {'01_06': ['h...30_A_D.json']} == {'01_06': [],...old_host': []}
tests/fnguide/test_wcomp_snapshot.py:205: AssertionError: assert {'01_06': ['h...30_A_D.json']} == {'01_06': [],...old_host': []}
PASSED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_013_contrast_consensus_request_is_caught
FAILED tests/fnguide/test_wcomp_snapshot.py::test_ac_wc_013_eight_tuple_and_no_consensus_request
1 failed, 1 passed, 13 deselected in 0.91s
(복원 후)
$ git status --short
?? .moai/logs/
?? .moai/reports/sync-audit/
$ git diff --stat
(출력 없음)
```

긍정 테스트는 앞의 기록과 같이 URL 판정에서 실패했고, 고친 대조는 통과했다.

#### M5 미검증(Gaps)

- AC-WC-013 되돌림 관측은 M5에서 예외가 URL 단언보다 먼저 났다 — M6에서 테스트 순서를 고쳐 다시 관측했다(위).
- 라이브 결과표(AC-WC-016)와 005930 핵심 지표의 FnGuide 화면 눈대조는 M6 몫이다.
- `ruff` 없음(린트 미실행).

### M6 — 기존 테스트 정리, 게이트, 라이브 확인 (2026-10-11)

#### M6 증거 — 테스트 정리

착수 기준: HEAD `5d021cb`(M5). 테스트 정리 커밋 `0219614`. 줄 번호는 편집 전 `cat -n`·`grep -n`으로 다시 확인했다(test_crawler.py 83행 후보, 162-169행 스냅샷 단언, 172-197행 `TestReadConsensus`; test_analysis.py 234행 후보, 255-268행 비교 테스트 — plan의 인용과 같았다).

- `tests/fnguide/test_crawler.py`: 별도 후보 `["003550", "015760", "034020"]` → `["403870", "330590", "476830"]`. `df_snap`·`df_snap_ann`이 비어 있지 않다는 단언을 "둘 다 빈 DataFrame, `report["종목명"] == "삼성전자"`"로 바꿨다. `자산`·`부채`·`자본` 인덱스 단언(44행)은 그대로. `TestReadConsensus`(섹션 머리글·데코레이터·클래스 전체)를 삭제했다(skip으로 바꾸지 않음).
- `tests/fnguide/test_analysis.py`: 별도 후보 교체, `test_characterize_controlling_profit_equals_net_income`의 비교 열을 `yearly_cols[-1]` → `yearly_cols[-2]`(완결 연도). `fnguide/analysis.py`는 무수정.
- `tests/fnguide/test_wcomp_snapshot.py`: AC-WC-013 긍정 테스트가 `get_fnguide`의 예외를 잡아 두고 요청 URL 판정을 먼저 한 뒤 다시 던지게 순서를 바꿨다(위 `#### RED 관측 — AC-WC-013` 재관측).

#### AC-WC-015 게이트 (이번 실행, 이 트리, HEAD `0219614` — 라이브 확인 뒤 코드 변경 없음)

```text
$ git diff --stat d6ed32e -- fnguide/analysis.py fnguide/dashboard.py fnguide/analyzer.py fnguide/parser.py fnguide/__init__.py backend/routers/analysis.py backend/schemas/analysis.py backend/services/analysis_service.py frontend/
(출력 없음)                                                     ← 1번 통과
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide tests/test_analysis_api.py tests/test_analysis_api_wcomp.py -q -p no:cacheprovider | tail -1
197 passed, 92 deselected, 1 warning in 3.48s                   ← 2번: 197 ≥ 164, failed·error 0
(3번 라이브 — 아래 절)
$ grep -nE "//comp\.fnguide\.com" fnguide/crawler.py             ← 4번 참고용
60:_CONS_D_URL = "http://comp.fnguide.com/SVO2/json/data/01_06/01_A{code}_A_D.json"
61:_CONS_B_URL = "http://comp.fnguide.com/SVO2/json/data/01_06/01_A{code}_A_B.json"
$ <acceptance.md AC-WC-015 4번 AST 프로브 그대로>
['_CONS_B_URL', '_CONS_D_URL'] ['read_consensus']               ← 4번 통과(기대 출력과 정확히 같음)
$ F=tests/fnguide/fixtures/wcomp/README.md; test -s "$F" && grep -qE 'https://wcomp\.fnguide\.com/' "$F" && grep -qE '20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$F" && echo README_OK
README_OK                                                       ← 5번 통과
$ grep -nE "open\([^)]*['\"](w|a|x)b?\+?['\"]|…|sqlite3\." fnguide/crawler.py fnguide/account_alias.py; echo "exit=$?"
exit=1                                                          ← 6번 통과
```

2번 하한 164는 §B·§C 기대 출력 줄의 합 1+3+8+2+3+9+7+4+8+4+3+5+2+4 = 63을 acceptance.md에서 다시 더해 확인했다. deselected가 94 → 92로 준 것은 `TestReadConsensus` 라이브 테스트 2건을 지웠기 때문이다.

#### AC-WC-015 3번 — 라이브 스위트 (사용자 승인, 1회 실행)

실행: 2026-10-11T00:35:58+09:00 ~ 00:36:08+09:00, 순차(병렬 워커 없음), 재실행 없음. acceptance 명령과 같은 pytest 인자를 요청 계수기로 감싼 실행기(`Output/m6_scripts/live_suite.py`, gitignore 경로, 커밋하지 않음)로 돌렸다. 계수기는 `requests.Session.request`를 감싸 요청마다 URL·상태·리디렉션을 기록하고, 403·429가 나오거나 400건을 넘으면 즉시 멈추도록 했다(발동하지 않음). 타임아웃·캐시는 그대로다.

```text
$ python Output/m6_scripts/live_suite.py <로그> -- tests/fnguide tests/test_analysis_api.py -q -p no:cacheprovider -m "live or slow" -rs
........................................................................ [ 78%]
....................                                                     [100%]
=============================== warnings summary ===============================
tests/fnguide/test_analysis.py::TestFsAnalysisStructure::test_characterize_pandas3_compatibility
  …/pykrx/__init__.py:4: UserWarning: pkg_resources is deprecated as an API. …
92 passed, 188 deselected, 1 warning in 8.67s
REQUESTS_TOTAL 80
exit=0
(요청 기록 집계)
n 80
status Counter({200: 80})
history Counter({(): 78, (302,): 2})
hosts Counter({'wcomp.fnguide.com': 80})
codes Counter({'005930': 48, '000660': 16, '403870': 14, '999999': 2})
endpoints Counter({'getFinIncome': 32, 'getFinBalance': 20, 'getFinCashFlow': 20, 'Snapshot': 8})
max sec 0.108 sum sec 6.01
```

판정: error 0, failed 0, skipped 0(허용 상한 1, `-rs` 출력에 skip 사유 없음) — 통과. 실제 요청 수는 80건(오케스트레이터 상한 추정 약 750건). 302 두 건은 999999 요청이 오류 페이지로 리디렉션된 것으로 M1 V-1 관측과 같다.

#### AC-WC-016 — 라이브 HTTP 결과표

백엔드를 이 워크트리 코드로 띄웠다. acceptance의 명령은 공용 체크아웃(`cd /Users/byunjungwon/Dev/my-project-01/my_chart`)에서 8000 포트를 쓰지만, 8000에는 사용자가 띄워 둔 공용 체크아웃 개발 서버(옛 코드, PID 42977)가 떠 있어 건드리지 않고, 워크트리에서 같은 venv 파이썬으로 8001 포트에 띄웠다(`Output/m6_scripts/live_server.py` — 작업 디렉터리를 `sys.path` 맨 앞에 넣고 `uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, workers=1)`, 요청 계수기 포함). 측정 뒤 이 서버만 종료했다(8000 서버는 그대로).

```text
$ for c in 403870 005930 330590 001750 105560 005935 999999; do printf "%s " "$c"; curl -s -o …/wc_$c.json -w '%{http_code} %{time_total}s ' "http://127.0.0.1:8001/api/analysis/$c"; jq -c '[.company_name, (.business_performance|type), (.health_indicators|type), (.five_questions|type)]' …/wc_$c.json 2>/dev/null || echo; done
403870 200 0.835063s ["HPSP","object","object","object"]
005930 200 0.995425s ["삼성전자","object","object","object"]
330590 200 0.924373s ["롯데리츠","object","object","object"]
001750 200 0.975311s ["한양증권","null","null","null"]
105560 200 0.914744s ["KB금융","null","null","null"]
005935 404 0.249999s [null,"null","null","null"]
999999 404 0.227742s [null,"null","null","null"]
```

| 코드 | 상태 | company_name | business_performance | health_indicators | five_questions | 기대와 일치 |
|---|---|---|---|---|---|---|
| 403870 | `200` | `HPSP` | `object` | `object` | `object` | 예 |
| 005930 | `200` | `삼성전자` | `object` | `object` | `object` | 예 |
| 330590 | `200` | `롯데리츠`(비어 있지 않음, 코드와 다름) | `object` | `object` | `object` | 예 |
| 001750 | `200` | `한양증권`(비어 있지 않음, 코드와 다름) | `null` | `null` | `null` | 예 |
| 105560 | `200` | `KB금융` | `null` | `null` | `null` | 예 |
| 005935 | `404` | — | — | — | — | 예 |
| 999999 | `404` | — | — | — | — | 예 |

서버 요청 기록: 45건 — wcomp 44건(모두 HTTP 200, 리디렉션 302 두 건은 999999), 종목별 403870·005930·330590·001750·105560 각 8건, 005935·999999 각 2건. 나머지 1건은 앱 시작 시 `data.krx.co.kr` 요청으로 이 SPEC과 무관하다. 서버 로그에 `WARNING`·`ERROR`·`Traceback` 0줄(접기·필수 계정·정합성 경고 없음). 표의 세 섹션 외에도, 응답 JSON에서 001750·105560은 Sections 1–7 전부 `null`, 005930은 Sections 1–7 전부 `object`임을 확인했다.

되돌림 관측 기록의 집합 비교:

```text
$ diff <(grep -oE '^#### RED 관측 — AC-WC-[0-9]{3}' .moai/specs/SPEC-FNGUIDE-WCOMP-001/progress.md | grep -oE 'AC-WC-[0-9]{3}' | sort -u) <(printf 'AC-WC-%03d\n' $(seq 1 13)); echo "diff-rc=$?"
diff-rc=0
$ grep -cE '^#### RED 관측' .moai/specs/SPEC-FNGUIDE-WCOMP-001/progress.md
13
```

#### 005930 캐시 미스 소요 시간

새로 띄운 서버 프로세스에서 005930의 첫 요청(캐시 미스): `curl` 총 소요 `0.995425s`, 그 안의 FnGuide 요청 8건이 0.826초 구간에 걸쳤다(요청별 소요 합 0.688초, `get_fnguide`의 0.1초 대기 2회 포함 전 구간). 기준선 기록용이며 성능 목표는 없다(spec §5).

#### 커버리지 (acceptance §E DoD 명령, 워크트리 `.venv`)

```text
$ .venv/bin/python -m coverage run --source=fnguide -m pytest tests/fnguide -q -p no:cacheprovider | tail -1
174 passed, 92 deselected, 1 warning in 2.35s
$ .venv/bin/python -m coverage report --include='fnguide/crawler.py,fnguide/account_alias.py'
Name                       Stmts   Miss  Cover
----------------------------------------------
fnguide/account_alias.py      13      0   100%
fnguide/crawler.py           245     11    96%
----------------------------------------------
TOTAL                        258     11    96%
```

두 파일 모두 85% 이상. 남은 11줄은 호출되지 않는 `read_consensus` 본문이다(M4 측정의 438-461 범위).

#### 수용한 잔여 위험의 완화 기록 (acceptance §E DoD)

- 정합성 가드 경고 0건: 오프라인 AC-WC-007(`test_ac_wc_007_fold_keeps_balance_guard_silent`), 라이브 서버 로그의 crawler 경고 0줄.
- 지배주주지분 = 주주몫 교차 확인: AC-WC-002 `3532337.75`.
- **005930 핵심 지표 — 사용자 눈대조 대기(pending user comparison).** 아래는 라이브 서버 응답(`GET /api/analysis/005930`)에서 읽은 값이며, FnGuide 화면과의 비교는 하지 않았다(사용자만 할 수 있음).
  - 영업이익률(`business_performance.opm`, 기간 `2023/12, 2024/12, 2025/12, 2026/06`): `0.02536, 0.10877, 0.13070, 0.48048`(마지막 열은 2026/06 누적 YTD)
  - 부채비율(`health_indicators` 「부채비율」): `0.31885`
  - 이자보상배율(`health_indicators` 「이자보상배율」): `236.78`
  - 비교할 FnGuide 페이지: `https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=005930`(이번 SPEC이 요청한 주소). 재무비율 메뉴의 정확한 주소는 확인하지 않았다.
- HPSP(403870): `GET /api/analysis/403870`이 라이브에서 `200`, 표의 세 열(Sections 1·2·7) `object`. 오프라인에서도 fixture 기반 `analyze_dashboard("403870")`이 8개 섹션 모두 채워졌다(M5 증거). **브라우저에서 재무 분석 모달이 열리는지는 확인하지 않았다(사용자 확인 대기).**

#### AC-WC-001 ~ 016 판정표 (이번 실행, 이 트리, HEAD `0219614`)

| AC | 상태 | 명령 | 실제 출력 |
|---|---|---|---|
| 001 | PASS | `pytest tests/fnguide/test_wcomp_repro.py -k ac_wc_001` | `1 passed, 1 deselected` |
| 002 | PASS | `pytest tests/fnguide/test_wcomp_reader.py -k ac_wc_002` | `3 passed, 49 deselected` |
| 003 | PASS | 같은 파일 `-k ac_wc_003` | `8 passed, 44 deselected` |
| 004 | PASS | `-k ac_wc_004` | `2 passed, 50 deselected` |
| 005 | PASS | `-k ac_wc_005` | `3 passed, 49 deselected` |
| 006 | PASS | `pytest tests/fnguide/test_wcomp_reader.py tests/test_analysis_api_wcomp.py -k ac_wc_006` | `9 passed, 52 deselected` |
| 007 | PASS | `pytest tests/fnguide/test_wcomp_reader.py -k ac_wc_007` | `8 passed, 44 deselected` (하한 7) |
| 008 | PASS | `-k ac_wc_008` | `4 passed, 48 deselected` |
| 009 | PASS | 두 파일 `-k ac_wc_009` | `12 passed, 49 deselected` (하한 8) |
| 010 | PASS | 두 파일 `-k ac_wc_010` | `7 passed, 54 deselected` (하한 4) |
| 011 | PASS | `pytest tests/fnguide/test_wcomp_snapshot.py -k ac_wc_011` | `3 passed, 12 deselected` |
| 012 | PASS | 같은 파일 `-k ac_wc_012` | `9 passed, 6 deselected` (하한 5) |
| 013 | PASS | 같은 파일 `-k ac_wc_013` | `2 passed, 13 deselected` |
| 014 | PASS | 두 파일 `-k ac_wc_014` | `4 passed, 57 deselected` |
| 015 | PASS | 위 「AC-WC-015 게이트」 여섯 항목 | 1 빈 출력 / 2 `197 passed` / 3 `92 passed`, skip 0 / 4 기대 출력 일치 / 5 `README_OK` / 6 `exit=1` |
| 016 | PASS | 위 「AC-WC-016」 명령 + 집합 비교 | 표 7행 모두 기대와 일치, `diff-rc=0` |

대조 AC 13개(001~013)의 RED 관측은 모두 이 절 위쪽의 `#### RED 관측 — AC-WC-0NN` 머리글 아래에 있다. AC-WC-014는 불변 AC라 머리글이 없다(M5 증거).

#### M1 확인 과제 V-1 ~ V-4 결과 요약

- V-1(응답 헤더): M1 완료 — 모순 없음. 오류 응답의 첫 홉은 302이고 리디렉션을 따라가면 200 HTML. 라이브 스위트·서버에서도 999999의 302 → 200이 같게 관측됐다.
- V-2(이자비용·법인세비용 첫 행): M3 통과 — 202560 `9302.53`, 203130 `-44808.35`.
- V-3(12월 결산 직후 열 모양): M3 통과(합성 fixture). 실물은 다음 결산 공시 이후 확인 가능(Gaps).
- V-4(충당부채 별칭 범위): M1 통과 — 005930 C, 403870 B 모두 종업원급여 외 충당부채가 한 행씩.

#### M6 미검증(Gaps)과 잔여 위험

- 005930 지표의 FnGuide 화면 눈대조, HPSP 모달 브라우저 확인: 사용자 확인 대기.
- AC-WC-016은 8000이 아닌 8001 포트의 워크트리 서버로 측정했다(명령의 포트·작업 디렉터리만 다름). main에 통합된 뒤 8000 개발 서버를 재시작하면 같은 결과가 나와야 하지만 관측하지 않았다.
- 라이브 값은 2026-10-07 캡처 fixture와 같았다(005930 부채비율 `0.3188`·이자보상배율 `236.7768`이 M5 오프라인 결과와 일치) — 그 사이 수치 정정은 없었던 것으로 보이나 전 계정을 대조하지는 않았다.
- 476830은 라이브 별도 후보 목록에만 있고 첫 후보 403870이 성공해 실제로 요청되지 않았다(요청 기록의 코드 집계에 없음).
- 이자비용·법인세비용 "첫 행"이 옛 화면과 같았는지, 접기 분류가 옛 사이트와 같았는지는 옛 사이트 소멸로 확인할 수 없다(spec Q-A 수용 위험).
- 라우터의 동기 크롤링(최악 8회 × 10초)과 `robots.txt` `Disallow: /`는 바꾸지 않은 기존 자세다(spec §5, plan §B.3).
- `ruff`가 없어 린트를 돌리지 못했다.

#### 독립 감사 결과와 부채

- 감사: sync-auditor, 대상 HEAD `8dfc739`(기준 `d6ed32e`). 판정 **PASS-WITH-DEBT**, 차단 결함 없음.
- 점수: Functionality 92, Security 88, Craft 86, Consistency 92 — 가중 89.8, 조화 평균 89.4. TRUST 5 종합 WARNING(Unified만 WARNING — `ruff` 부재).
- 보고서: `.moai/reports/sync-audit/SPEC-FNGUIDE-WCOMP-001-run-review-1.md` — 워크트리의 로컬 미추적 산출물이며 커밋하지 않는다.
- 아래 보강 커밋(`7ba072a` 이후)은 감사 대상 HEAD 뒤에 나왔다. 감사는 이 보강을 보지 않았다.

| ID | 등급 | 내용(요약) | 처분 |
|---|---|---|---|
| F1 | suggestion | `_fetch`가 다른 호스트로의 리디렉션 끝 응답을 믿는다 | **이번에 수정**(`7ba072a`) — 최종 URL 호스트를 `wcomp.fnguide.com`과 정확히 비교, 다르면 `ConnectionError` |
| F2 | suggestion | 응답 본문 크기 상한 없음 | 수용한 부채 — 요청 시에만 받는 응답(관측 최대: 재무제표 약 40KB, 스냅샷 약 160KB), 감사도 "지금은 불필요" |
| F3 | suggestion | 경고 로그에 응답 유래 행 이름이 그대로 들어가 줄바꿈 삽입 가능 | 수용한 부채 — 상류 침해가 전제, 로그 형식 변경은 이번 범위 밖 |
| F4 | suggestion | 예외 메시지에 상류 예외 글자가 들어가고 라우터가 그대로 내보냄 | 수용한 부채 — 내보내는 쪽은 라우터이며 REQ-WC-015가 라우터 수정을 금지, 비밀 노출 없음 |
| F5 | suggestion | `_to_float`가 `NaN`·`inf`·`1_000`을 받아들임 | 수용한 부채 — 관측한 셀 19,685개가 모두 숫자 문자열 또는 null(감사 집계), 추측성 |
| F6 | suggestion | 다중 행 보정이 0행일 때는 채우지 않음(REQ-WC-008 문구와 차이) | 수용한 부채 — M3 발견 사항에 기록한 의도된 선택(D8과 정합), 문구 정정은 sync 때 manager-spec 판단 |
| F7 | suggestion | `#giName`이 없으면 `종목명` 키를 빼서 REQ-WC-013 문구와 차이 | 수용한 부채 — `dashboard.py:934`의 코드 대체값이 키 부재에 기대므로 현재 동작이 낫다(감사 동의) |
| F8 | suggestion | 테스트 세 파일의 가짜 사이트 헬퍼 중복 | 수용한 부채 — 테스트 구조 정리는 이번 보강 범위 밖 |
| F9 | warning | AC-WC-013 대조가 운영 경로를 되돌리지 않음 | **이번에 수정**(`7ba072a`) — `get_fnguide`가 부르는 `read_snapshot`을 감싸 실제 경로에서 컨센서스 요청 |
| F10 | suggestion | AC-WC-009 대조가 모든 예외를 삼킴 | **이번에 수정**(`7ba072a`) — `pytest.raises(TypeError)`만 인정 |
| F11 | suggestion | 별칭 테스트가 상수를 다시 적고 spec.md를 실행 시 읽음(SPEC 이동 시 깨짐) | 수용한 부채 — spec.md D7과의 일치가 이 테스트의 목적, SPEC 보관 시 다시 판단 |
| F12 | warning | `ruff` 미설치로 린트·포맷 미실행 | 수용한 부채 — 이 환경에 ruff가 없고 공용 venv에 설치하지 않는다는 원칙 |

감사의 Gaps(감사자가 관측하지 않은 것): 라이브 게이트(AC-WC-015 3번, AC-WC-016)는 네트워크 금지로 재현하지 않고 기록만 읽음. 사용자 몫 수동 확인 2건(005930 지표 화면 대조, HPSP 모달). 대조 AC의 소스 되돌림은 AC-WC-001·005·007·009 네 건만 독립 재현(나머지는 스위트 `_contrast`와 이 기록에 기댐). 린트·포맷 미실행. 교차 모델 의견 없음. 2026-10-07 캡처 밖의 실사이트 동작(다른 호스트 리디렉션 포함)과 12월 결산 직후 실물 열 모양.

#### 감사 보강 증거

착수 기준: HEAD `8dfc739`. 보강 커밋 `7ba072a`. 라이브 요청 없음.

F1 RED(호스트 검사 추가 전, 테스트만 추가 — `git diff --stat -- fnguide` 출력 없음). 가짜 전송층이 wcomp 요청에 `https://example.com/…`로 302를 주고, 그 호스트가 정상 JSON fixture를 돌려준다. `requests`의 실제 리디렉션 처리를 거친다.

```text
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k redirect_to_other_host --tb=line -p no:logging -W ignore::UserWarning | tail -5
005930 정합성 검사 건너뜀: 분기 표에 '부채' 행 없음
/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-a20b6e0f16e957192/tests/fnguide/test_wcomp_reader.py:596: Failed: DID NOT RAISE <class 'ConnectionError'>
=========================== short test summary info ============================
FAILED tests/fnguide/test_wcomp_reader.py::test_ac_wc_010_redirect_to_other_host_is_connection_error
1 failed, 52 deselected in 0.22s
```

다른 호스트의 본문이 데이터로 받아들여져 예외 없이 반환됐다(경고는 모든 요청이 같은 연간 손익 본문을 받아 생긴 것).

F1 GREEN(`_fetch`에 최종 URL 호스트 정확 비교 추가 — 8줄):

```text
$ … -k redirect | tail -2
..                                                                       [100%]
2 passed, 51 deselected in 0.22s
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m pytest tests/fnguide tests/test_analysis_api.py tests/test_analysis_api_wcomp.py -q -p no:cacheprovider | tail -1
198 passed, 92 deselected, 1 warning in 3.48s
```

기존 999999 리디렉션 테스트(같은 호스트의 `/Error/InvalidCompany` → 200 HTML → `ValueError`)도 함께 통과했다. F9·F10 뒤 문서화된 명령: `-k ac_wc_013` → `2 passed, 13 deselected`, AC-WC-009 두 파일 `-k ac_wc_009` → `12 passed, 50 deselected`(테스트 수 변화 없음), AC-WC-010 두 파일 → `8 passed, 54 deselected`(F1 테스트 1건 추가로 7 → 8).

커버리지(워크트리 `.venv`): `fnguide/account_alias.py 13 0 100%`, `fnguide/crawler.py 249 11 96%`(남은 11줄은 호출되지 않는 `read_consensus`).

미검증: F1은 오프라인에서만 확인했다. 실사이트에 대고 다시 확인하지 않았다(이번 회차는 라이브 요청 금지). M6 라이브 실행의 302 두 건은 모두 같은 호스트 안의 리디렉션이었다.

## §E.3 Run-phase Audit-Ready Signal

**작성자**: manager-develop (run 단계)
**일자**: 2026-10-11

```yaml
run_complete_at: 2026-10-11
run_status: audit-ready
run_base_sha: d6ed32e
run_commit_sha: pending-backfill   # 감사 보강 기록을 담은 마지막 progress.md 커밋(후속 커밋에서 채움)
run_branch: worktree-agent-a20b6e0f16e957192   # main 통합·push 전
m1_to_mN_commit_strategy: milestone별 커밋, main 직접 커밋 대신 격리 워크트리 브랜치(통합은 마지막에 사용자 결정)
run_commits:
  - 3bfddcf  # M1 재현 테스트·축소 fixture
  - 9f5b03d  # M2 account_alias.py
  - 2adc99f  # M3 read_fs 재작성
  - 3041d46  # M3 되돌림 관측
  - 9cb4b7c  # M4 read_snapshot 재작성
  - ae69a93  # M4 되돌림 관측
  - b4bf7ba  # M5 get_fnguide 정리
  - 5d021cb  # M5 증거
  - 0219614  # M6 테스트 정리·AC-WC-013 보강
  - 3cb5168  # M6 게이트·라이브 결과
  - 8dfc739  # M6 run_commit_sha 채움 (감사 대상 HEAD)
  - 7ba072a  # 감사 보강 F1·F9·F10
ac_pass_count: 16
ac_fail_count: 0
red_observation_headings: 13   # AC-WC-001~013
offline_suite: "198 passed, 92 deselected"
audit_verdict: PASS-WITH-DEBT   # sync-auditor, HEAD 8dfc739, 가중 89.8
audit_report: .moai/reports/sync-audit/SPEC-FNGUIDE-WCOMP-001-run-review-1.md (local, untracked)
audit_debt_accepted: [F2, F3, F4, F5, F6, F7, F8, F11, F12]
live_suite: "92 passed, 188 deselected, skipped 0, 요청 80건"
coverage: {crawler.py: 96%, account_alias.py: 100%}
new_warnings_or_lints_introduced: unknown   # ruff 미설치로 미측정
manual_pending: [005930 지표 FnGuide 화면 대조, HPSP 모달 브라우저 확인]
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
