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

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
