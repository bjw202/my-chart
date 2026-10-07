# SPEC-FNGUIDE-WCOMP-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

**작성자**: manager-spec (plan 단계)
**일자**: 2026-10-07
**Tier**: M (spec.md + plan.md + acceptance.md, 보조로 research.md + 본 파일)

### 산출물

| 파일 | 상태 |
|---|---|
| `spec.md` | v0.2.2 — 결정 D1~D9, REQ-WC-001~016(16개, Tier M 상한 16), Out of Scope 5개 소절 |
| `plan.md` | v0.2.2 — 계획 정정 C-1~C-5, 사용자 결정 5건(Q-G, Q-I, Q-D, Q-F, Q-A), M1 확인 과제 V-1~V-4, 마일스톤 M1~M6(M6에 라이브 게이트 선행 과제 3건), 미확정 표지 0건 |
| `acceptance.md` | v0.2.2 — AC-WC-001~016(16개, Tier M 상한 16): 대조 13 / 불변 1 / 게이트 2 |
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

### v0.2.2 자체 점검

| 항목 | 결과 |
|---|---|
| REQ / AC 개수 | 16 / 16 (새 사례는 기존 AC에 병합) |
| 미확정 표지 | 다섯 파일 모두 0건 |
| lint | `moai spec lint` 무결 |
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

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
