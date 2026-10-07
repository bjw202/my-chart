# SPEC-FNGUIDE-WCOMP-001 — 구현 계획 (plan)

> 원천 계획: `.moai/plans/wondrous-noodling-coral.md`(승인됨). 이 문서는 그 계획을 run 단계의 실행 순서로 옮기고, plan 단계 계측에서 드러난 정정과 사용자 결정을 앞에 모은다. 시간 추정은 쓰지 않는다. v0.2.0에서 미확정 항목은 모두 사용자 결정 또는 M1 확인 과제로 해소했다.

## §A 맥락

### §A.1 위치와 산출물

| 항목 | 값 |
|---|---|
| 저장소 | `/Users/byunjungwon/Dev/my-project-01/my_chart` |
| 파이썬 | `/Users/byunjungwon/Dev/my_chart/.venv/bin/python` (cwd와 venv 경로가 다름 — 메모리 `project_server_runtime_env.md`) |
| SPEC 산출물 | `spec.md`, `plan.md`, `acceptance.md`, `research.md`, `progress.md` (이 디렉터리) |
| 수정 대상 | `fnguide/crawler.py` (재작성: `read_fs`, `read_snapshot`, `get_fnguide`) |
| 신규 | `fnguide/account_alias.py`, `tests/fnguide/test_wcomp_repro.py`, `tests/fnguide/test_wcomp_reader.py`, `tests/fnguide/test_wcomp_snapshot.py`, `tests/test_analysis_api_wcomp.py`, `tests/fnguide/fixtures/wcomp/*`(축소본 + README) |
| 다시 쓰기 | `tests/fnguide/test_crawler.py`(라이브 단언을 새 계약으로, `IFRS(별도)` 후보 `:83`, `TestReadConsensus` `:177-196` 삭제), `tests/fnguide/test_analysis.py`(`IFRS(별도)` 후보 `:234`, `test_characterize_controlling_profit_equals_net_income` `:255-268`), 필요 시 `tests/fnguide/conftest.py` |
| 손대지 않음 (PRESERVE) | `fnguide/analysis.py`, `fnguide/dashboard.py`, `fnguide/analyzer.py`, `fnguide/parser.py`, `fnguide/__init__.py`, `backend/**`, `frontend/**`, 다른 SPEC 디렉터리(ENGINE-001 포함) |

`fnguide/parser.py`의 `to_num`은 재사용만 하고 고치지 않는다. `fnguide/__init__.py`는 `read_consensus`를 계속 내보내므로 손대지 않는다(spec §6).

### §A.2 SPEC ID ↔ 화면 요소 대응 (교훈 #7)

| 화면 요소 | 이 SPEC 이후 변화 |
|---|---|
| 재무 분석 모달(`/api/analysis/{code}` 소비) | 503 오류 → 정상 표시 |
| 모달 상단 회사명 | **변화 없음.** 모달은 차트 셀의 `stock.name`을 표시한다(`ChartCell.tsx:428`, `AnalysisModal.tsx:765`). API `company_name`이 종목 코드 대신 회사명이 되는 것은 API 수준 정정이며 화면에 보이지 않는다(프론트엔드의 `company_name`은 `types/analysis.ts:91` 타입 선언뿐) |
| 금융회사(KB금융 등) 모달 | 503 → 200 + 대부분 섹션 비어 있음(옛 동작과 같은 정책) |

다른 탭·차트·스크리너에는 영향이 없다.

### §A.3 라이브 사용 가설과 되돌리기 (교훈 #7)

- 가설: 사용자는 종목을 고를 때 재무 분석 모달을 열어 S-RIM 지표를 본다. 이 SPEC 이후 모달이 다시 열리면 기능 복구로 충분하며, 새 기능 가치 재평가는 필요 없다(장애 복구 SPEC).
- 되돌리기: run 단계 커밋을 되돌리면 지금과 같은 503 상태로 돌아간다. 데이터 저장이 없으므로 되돌림에 따른 데이터 손상 위험은 없다.

---

## §B 정정, 결정, 위험

### §B.1 승인 계획 대비 정정 (계측 근거 있음)

| # | 승인 계획 | 이 SPEC | 근거 |
|---|---|---|---|
| C-1 | 001750은 200 + 섹션 채워짐 | 001750은 **금융 레이아웃**(증권사) → 200 + Sections 1–7 null | research.md §R1 F-10: 001750 Income LVL0에 `매출액(수익)` 없음 |
| C-2 | 정합성 허용오차 0.01억원 | 0.1억원, 연간·분기 두 표 모두 검사 | research.md §R5: 403870 B 정상 응답에서 반올림 잔차 −0.02억원. 분기 표는 `analyzer.py:180,183`이 대차대조표 행을 읽음 |
| C-3 | "중복 이름 보존"만 명시 | 중복 행 불변식 추가: 현금흐름표 `당기순이익` 개명 + `법인세비용`·`이자비용` 2행 이상 보장 | research.md §R4: 보존만 하면 Section 1–7 전부 실패(P-1), 개명만 하면 법인세비용이 예외 없이 틀림(P-2) |
| C-4 | 요청 2회 절감 | 요청 수는 3 → 최대 8회로 늘어남 | 옛 방식은 재무제표 페이지 1회에 표 6개였다. 새 API는 재무제표마다 1회. 5분 캐시가 흡수(spec §5) |
| C-5 | 상태 코드·`Content-Type`으로 실패 판정 | 2xx 본문 기반 판정, 2xx 밖은 503 | `Content-Type`은 plan 단계에서 관측하지 못함 → M1 V-1에서 기록 |

### §B.2 사용자 결정 (2026-10-07, 확정)

| # | 질문 | 결정 | 반영 위치 |
|---|---|---|---|
| Q-G | 새 하위 행(특히 `당기손익-공정가치측정금융자산`, `상각후원가측정금융자산` 등 금융상품 행)을 어디로 접나 | **승인 계획대로 전부 부모의 `기타*` 계정**(`기타유동자산`/`기타비유동자산`/`기타유동부채`/`기타비유동부채`) | spec D6, REQ-WC-011, AC-WC-007 |
| Q-I | 0 행 보충 범위 | **명시 목록만**(현재 `관계기업등지분관련투자자산` 하나). 그 밖의 필수 계정 부재는 경고 로그, 행을 지어내지 않음 | spec D8, REQ-WC-010, AC-WC-008 |
| Q-D | 결산 기간이 4개 미만인 신규 상장 기업 | **`ValueError`(404)**, 메시지에 기간 부족 명시, 0으로 채우지 않음 | REQ-WC-002, AC-WC-009 (d) |
| Q-F | 수집 자세와 fixture | 현행 수집 자세(요청 시 가져와 5분 캐시, 대량 저장 없음) 유지. fixture는 **테스트가 쓰는 행·열만 남긴 축소본**을 `tests/fnguide/fixtures/wcomp/`에 커밋 | REQ-WC-015, REQ-WC-016, §B.3 |
| Q-A | 옛 사이트 소멸로 수정 전후 수치 비교 불가 | **수용한 잔여 위험.** 완화: 정합성 가드(AC-WC-007), 지배주주지분 = 주주몫 교차 확인(AC-WC-002), run 완료 시 005930 핵심 지표(영업이익률·부채비율·이자보상배율)를 FnGuide 화면과 눈으로 대조해 progress.md §E.2에 기록(acceptance §E DoD) | acceptance §E |

**Q-G에서 고려한 세 안** (어느 쪽이 옛 사이트 처리와 같았는지는 옛 사이트 소멸로 **검증할 수 없다**. 이 선택에 따라 달라지는 금액은 삼성전자 2023/12 기준 6,353.93억원 = 271.12 + 6,082.81):

| 안 | 내용 | 결과 |
|---|---|---|
| 채택 — 전부 `기타*` | 금융상품 행도 부모의 `기타*`로 | 영업자산(운전자산)에 들어감. 승인 계획과 같음. 삼성전자 `기타유동자산` 2023/12 = 90,403.61 |
| 기각 — 금융상품은 금융 계정으로 | 이름에 `금융자산`·`금융부채`·`유가증권`이 든 행을 `유동금융자산` 등으로 | 비영업자산에 들어감. S-RIM 분류와 더 가깝다는 논거가 있었으나 사용자가 승인 계획을 택함 |
| 기각 — 행을 버림 | 접지 않음 | 자산 합계가 `자산`과 어긋남(삼성전자 연간 4열 + 분기 4열 = 경고 8건) |

### §B.3 알려진 위험 (수용 또는 변경하지 않는 자세)

- **선택 판정 응답의 실패 판정 범위**(REQ-WC-002, v0.2.2): 결정되지 않은 유형의 선택 응답이 비거나 머리글이 null이면 그 유형을 "값 없음"으로 보고 404를 내지 않는다. 관측한 별도 전용 종목(403870·330590·476830)의 `C` 응답은 모두 56행이 있고 값만 전부 null이었다(research.md §R1 F-09·F-11) — 빈 `data`를 돌려주는 `C`는 관측한 적이 없어 이 규칙은 관측 사례 없이 방어용으로 둔다. 두 유형이 모두 실패하면 `ValueError`(404).
- **수정 전후 수치 비교 불가**(Q-A, 수용): 위 완화 조치로 대신한다. 남는 위험은 "합계는 맞지만 분류가 옛 사이트와 다른 경우"다 — 가드는 이를 잡지 못한다(spec D7).
- **fixture 공개 범위**(Q-F): 축소 fixture라도 FnGuide 응답의 일부가 저장소에 들어간다. 원격 저장소 `github.com/bjw202/my-chart`가 공개인지 **확인하지 못했다**. 공개라면 약관(DB화 금지 문구)과의 긴장이 남는다 — 수용한 잔여 위험.
- **수집 자세**: `robots.txt` `Disallow: /`. 옛 방식과 같은 위험이며 새로 생긴 위험은 아니다. 요청 수 증가(C-4)는 사용자가 모달을 열 때만 발생하고 5분 캐시가 흡수한다.
- **이벤트 루프 차단**: 라우터가 `async def` 안에서 동기 크롤링을 호출한다. 최악 8회 × 10초. 라우터 수정 금지라 기록만 한다(spec §5).
- **표본 수명**: 조사 표본이 OS 임시 디렉터리에 있다(research.md §R0). M1의 첫 작업이 fixture 확보다.
- **추가 캡처 필요**: 001750 Balance·CashFlow를 `C`와 `B` **둘 다**, Y와 Q 모두(8개 응답 — AC-WC-003 대조 (나) "`C`에 값이 있으면 `C`" 구현이 `C` 재무제표 전체를 요청하므로 `C`도 필요), 001750 Income Q `C`·`B`, 330590 Q Balance·CashFlow(`B`), 001750·330590 스냅샷, 105560 Q Balance·CashFlow(`C`)는 표본에 없다. M1에서 라이브로 한 번 받아 축소 fixture로 고정한다.
- **베타 0 → Ke 3.5%**: 기존 동작 유지(spec §5).

---

## §C 착수 전 점검 (run 단계 M1 직전)

```bash
cd /Users/byunjungwon/Dev/my-project-01/my_chart
PY=/Users/byunjungwon/Dev/my_chart/.venv/bin/python
git rev-parse --short HEAD && git branch --show-current          # BASE 기록 (AC-WC-015)
git status --short fnguide tests backend                          # 무관한 변경이 섞여 있지 않은지
$PY -m pytest tests/fnguide tests/test_analysis_api.py -q -p no:cacheprovider | tail -1   # 기대: 101 passed, 94 deselected
ls /private/tmp/claude-501/-Users-byunjungwon-Dev-my-project-01-my-chart/d73171bb-e515-41a5-9d94-8b421935fe6b/scratchpad/raw | wc -l   # 표본 생존 확인 (plan 단계 시점 102)
grep -n "^status" .moai/specs/SPEC-DASHBOARD-002/spec.md         # depends_on 충족 확인: status: completed
```

현재 primary checkout의 `git status`에 이 SPEC과 무관한 대량 삭제·수정(`.agency/`, `.claude/agents/` 등)이 있다. run 단계는 반드시 경로를 지정해 스테이징하고(`git add -A` 금지), 가능하면 워크트리에서 작업한다.

---

## §D 제약

- `fnguide/analysis.py`, `fnguide/dashboard.py`, 라우터, 스키마, 서비스, 프론트엔드는 수정 금지(REQ-WC-015). 수정이 필요해 보이면 blocker로 보고한다.
- 기본 스위트에서 실제 HTTP 금지(acceptance §A.2). 라이브 테스트는 `@pytest.mark.live`.
- 코드 주석은 한국어(`language.yaml code_comments: ko`), 커밋 메시지는 한국어(`git_commit_messages: ko`), Conventional Commits + `🗿 MoAI <email@mo.ai.kr>` 끝줄.
- 커밋 메시지 본문에 `--no-verify` 문자열을 쓰지 않는다(pre-commit 가드 오탐 — 메모리 `feedback_precommit_guard_false_positive.md`).
- 새 워크트리에서 pre-commit 백엔드 pytest가 운영 DB 부재로 실패할 수 있다(메모리 `project_worktree_precommit_db_trap.md`).
- `account_alias.py`가 유일한 계정명 출처다(별칭표, 0 행 보충 목록, 필수 계정 목록, 재무제표 한정 개명표, 다중 행 필요 목록, 접기 부모 코드 → `기타*` 대응). `crawler.py`에 계정명 문자열을 흩뿌리지 않는다.
- fixture는 축소본만 커밋하고, `tests/fnguide/fixtures/wcomp/README.md`에 원본 URL·캡처 시각·축소 방법을 적는다.
- @MX: `read_fs`, `read_snapshot`, `get_fnguide`에 `@MX:ANCHOR`(호출부 고정 계약) + `@MX:REASON`. 중복 행 보정 지점에 `@MX:WARN`(분석 코드의 암묵 가정에 묶인 구조) + `@MX:REASON`. 주석 언어 한국어.

---

## §E 자체 검증 산출물 (run 단계가 progress.md §E.2에 남길 것)

1. AC-WC-001 ~ AC-WC-016 판정표: AC | 상태 | 명령 | 실제 출력(축자).
2. **RED 관측 기록**: AC마다 `#### RED 관측 — AC-WC-0NN` 머리글 하나. AC-WC-001은 구현 전 RED, AC-WC-002 ~ AC-WC-013은 소스 되돌림 RED. 되돌림 방법, 실패 출력 축자, 복원 후 `git status --short`. AC-WC-016이 이 머리글 집합을 대조 AC 집합과 비교한다.
3. 커버리지(acceptance §E DoD 명령).
4. 005930 캐시 미스 1회 소요 시간(기준선 기록용).
5. M1 확인 과제 V-1~V-4 결과(아래 §F.1).
6. 수용한 잔여 위험 완화 기록: 005930 영업이익률·부채비율·이자보상배율의 FnGuide 화면 값 대조, HPSP 모달 열림 확인.
7. 미검증 목록(Gaps)과 잔여 위험.

---

## §F 마일스톤

### §F.0 검토 우선순위 (바뀔 가능성이 큰 결정부터)

1. spec D4 중복 행 불변식 — 분석 코드 암묵 가정과의 계약(V-2로 첫 행 정체 확인)
2. spec D2 연결/별도 선택 규칙, D3 레이아웃 판별
3. spec D6·D7 접기와 정합성 가드(Q-G 결정 반영), D8 0 행 보충(Q-I 결정 반영)
4. REQ-WC-002·003·005 실패 분류(404 / 503 경계)
5. 스냅샷 파싱, 8-튜플 유지, 테스트 정리 — 기계적 작업

### §F.1 실행 순서

**M1 — 재현, fixture, 확인 과제 (Priority High)**
- 표본에서 축소 fixture를 만들어 `tests/fnguide/fixtures/wcomp/`에 둔다(테스트가 쓰는 행·열만). §B.3의 부족분은 라이브로 1회 캡처해 같은 방식으로 축소하고, README에 캡처 시각을 적는다.
- `test_wcomp_repro.py`(AC-WC-001) 작성 → **수정 전 RED(`IndexError`) 관측·기록**.
- BASE SHA 기록.
- 확인 과제 네 가지를 실행하고 결과를 §E.2에 기록한다. 통과 조건을 못 채우면 구현을 진행하지 말고 blocker로 보고한다.

| ID | 확인 대상 | 명령 | 통과 조건 |
|---|---|---|---|
| V-1 | 세 엔드포인트의 실제 응답 헤더(REQ-WC-002가 `Content-Type`에 기대지 않도록 기록만) | `for e in getFinIncome getFinBalance getFinCashFlow; do curl -s -D - -o /dev/null -A "Mozilla/5.0" -H "X-Requested-With: XMLHttpRequest" -H "Referer: https://wcomp.fnguide.com/" "https://wcomp.fnguide.com/CompanyInfo/$e?cmp_cd=005930&freq_typ=Y&consol_typ=C"; done > tests/fnguide/fixtures/wcomp/HEADERS_005930.txt` 와 같은 명령을 `cmp_cd=999999`(오류 HTML), `cmp_cd=005935`(빈 dataset)로도 실행 | 세 경우의 상태 줄과 `Content-Type`이 파일에 기록됨. 헤더 값이 REQ-WC-002·003의 판정과 모순되면(예: 오류가 2xx 밖) blocker |
| V-2 | `이자비용`·`법인세비용`의 첫 행 정체(구 Q-B) | `$PY -c "import json;d=json.load(open('tests/fnguide/fixtures/wcomp/<005930 Income Y C 파일>',encoding='utf-8-sig'))['dataset']['data'];print([(r['AC_CODE'],r['P_AC_CODE'],r['VAL1']) for r in d if r['NAME'].replace(' ','') in ('이자비용','법인세비용')])"` 후, 구현된 `read_fs` 결과에서 `df.loc['이자비용'].iloc[0]`, `df.loc['법인세비용'].iloc[0]`을 출력 | 이자비용 첫 행 = AC_CODE 202560(부모 202550 금융원가)의 값(2023/12 9302.53), 법인세비용 첫 행 = AC_CODE 203130의 값(2023/12 −44808.35). 이 정체가 옛 화면의 "첫 행"과 같았는지는 확인 불가로 Gaps에 남김 |
| V-3 | 12월 결산 직후 열 모양(구 Q-C) | 합성 fixture(acceptance AC-WC-006 (c))로 `read_fs` 실행: `$PY -m pytest tests/fnguide/test_wcomp_reader.py -q -p no:cacheprovider -k "ac_wc_006 and dec"` | 열 4개 `2022/12…2025/12`, `df_yoy_base_ann is None`, `calc_weight_coeff == (1.0, 2.0, 3.0, 6.0)`. 실물 확인은 다음 결산 공시 이후로 Gaps에 남김 |
| V-4 | `단기충당부채→기타단기충당부채`, `장기충당부채→기타장기충당부채` 의미 일치(구 Q-E) | `$PY -c "import json;d=json.load(open('<005930 Balance Y C fixture>',encoding='utf-8-sig'))['dataset']['data'];print([(r['P_AC_CODE'],r['NAME'].strip()) for r in d if '충당부채' in r['NAME']])"` 를 005930 C와 403870 B에 실행 | 부모 131580·130010 아래 충당부채 행이 각각 `종업원급여충당부채` 1개 + `단기충당부채`/`장기충당부채` 1개뿐(plan 단계 005930 C 관측: `[('131580','유동종업원급여충당부채'),('131580','단기충당부채'),('130010','비유동종업원급여충당부채'),('130010','장기충당부채')]`). 즉 종업원급여가 아닌 충당부채가 한 행씩이라 옛 이름 `기타…충당부채`(종업원급여 외 충당부채)와 같은 범위 |

**M2 — 계정명 단일 출처 (Priority High)**
- `fnguide/account_alias.py`: 일반 레이아웃 별칭표(승인 계획 22개), 0 행 보충 목록(`관계기업등지분관련투자자산`), 필수 계정 목록(분석 코드 계정 + `매출총이익`·`매출원가`·`영업활동으로인한현금흐름`), 재무제표 한정 개명표(현금흐름표 `당기순이익→당기순손익`), 다중 행 필요 목록(`이자비용`, `법인세비용`), 접기 부모 코드 → `기타*` 대응.

**M3 — `read_fs` 재작성 (Priority High)**
- 옛 URL 상수 `_FS_URL`·`_SNAP_URL`(`crawler.py:27-34`) 삭제. `_CONS_D_URL`·`_CONS_B_URL`은 호출되지 않는 `read_consensus`를 위해 남긴다(AC-WC-015 4번 기대 출력에 도달하는 조건).
- 코드 검증·요청(쿼리 파라미터, 헤더, 타임아웃), 상태·본문 기반 실패 분류, 연결/별도 선택, 열·기간 일치·값·이름 정규화, 이어 붙이기와 중복 행 불변식, 레이아웃 판별, 별칭·0 행·접기·정합성 가드(두 표 모두, 부재 시 경고 후 건너뜀), 전년동기 분리.
- AC-WC-002 ~ AC-WC-010 GREEN.

**M4 — `read_snapshot` 재작성 (Priority Medium)**
- 시그니처 `read_snapshot(code, account_type="IFRS(연결)")` 유지(인자는 무시), 반환은 `(report, 빈 DataFrame, 빈 DataFrame)`(REQ-WC-013).
- Snapshot HTML 1회, `#cmp_cd` 검사(부재 포함), report 키 유지, `종목명`, `자사주` 정확 일치(부재 시 0), `52주베타`.
- AC-WC-011, AC-WC-012 GREEN.

**M5 — `get_fnguide` 정리 (Priority Medium)**
- 컨센서스 호출 제거, 위치 2·3·4 빈 DataFrame, 8-튜플 유지. `_FS_URL`·`_SNAP_URL`이 M3·M4에서 지워졌는지 AC-WC-015 4번 AST 프로브로 확인(`_CONS_*` 두 상수와 `read_consensus`만 남아야 함).
- AC-WC-013, AC-WC-014 GREEN.

**M6 — 기존 테스트 정리와 게이트 (Priority Medium)**
- `test_crawler.py` 라이브 단언을 새 계약으로 다시 쓰기(옛 `df_snap`·`df_snap_ann`이 비어 있지 않다는 단언 제거. `:44`의 `자산`·`부채`·`자본` 인덱스 단언은 새 계약에서도 성립하므로 유지).
- `IFRS(별도)` 후보 목록 `["003550", "015760", "034020"]`(`test_crawler.py:83`, `test_analysis.py:234`)을 실측 별도 종목 `["403870", "330590", "476830"]`로 교체. 옛 후보는 새 선택 규칙에서 별도로 판정되지 않아 `"IFRS(별도) 종목을 찾지 못함"` skip 4건(`test_crawler.py:96, :103`, `test_analysis.py:248, :258`)을 낸다 — AC-WC-015 3번의 skip 상한 1을 넘는다.
- `test_analysis.py:255-268`(`test_characterize_controlling_profit_equals_net_income`) 다시 쓰기: 지금은 `yearly_cols[-1]`(Trailing 12M으로 덮어쓴 열)의 `지배주주순이익`과 같은 열의 `df_fs_ann["당기순이익"]`(누적 YTD)을 비교해 마지막 연간 열이 부분 연도면 항상 실패한다(403870: 857.27 대 489.69 — 오케스트레이터 확인). 후보가 늘 skip이라 지금까지 숨어 있었다. 비교 열을 Trailing 보정이 없는 완결 연도 `yearly_cols[-2]`로 바꾼다(403870 양쪽 726.62). 이것은 테스트의 결함 수정이며 `fnguide/analysis.py`는 건드리지 않는다.
- **`TestReadConsensus`(`test_crawler.py:177-196` — 데코레이터 177, 클래스 178, 마지막 단언 196; `@pytest.mark.live`) 삭제.** 이 클래스는 `read_consensus("005930")`으로 옛 호스트 `comp.fnguide.com/SVO2/json/data/01_06/…`(`crawler.py:35-36`)를 요청하고, 그 호스트는 안내 페이지만 돌려주므로 fixture 단계에서 error가 난다 — AC-WC-015 3번(라이브 error 0)이 통과할 수 없고, 컨센서스를 쓰지 않는 새 계약(REQ-WC-014)과도 맞지 않는다. skip으로 바꾸는 대안은 택하지 않는다(허용 skip 목록에 없으므로 AC-WC-015 FAIL).
- 대조 AC 13개 RED 관측, 커버리지, 라이브 HTTP 결과표(AC-WC-016), AC-WC-015 게이트(라이브 skip ≤ 1).

---

## §G 피해야 할 것

- 2xx 상태를 성공 신호로 쓰기(오류도 200이다). `Content-Type`에 기대기(관측 전).
- `AC_CODE`로 계정을 찾기(레이아웃마다 뜻이 다르다 — research.md §R3).
- "200이고 섹션이 채워졌다"만으로 통과 판정하기 — §R4 P-2처럼 숫자만 틀리는 결함을 놓친다. 숫자를 고정한 AC(AC-WC-005)가 이를 막는다.
- 접기·가드에서 `[...][0]` 같은 무조건 인덱싱 — 목적지 행이 없으면 `IndexError`가 새어 503이 된다(REQ-WC-011).
- 대조 테스트를 쓰고 GREEN만 확인한 뒤 "대조 성립"으로 기록하기(교훈 #9). 되돌림 RED를 직접 봐야 한다.
- 분석 코드나 프론트엔드를 고쳐 새 이름에 맞추기(REQ-WC-015 위반).
- 우선주 요청을 보통주로 바꿔 주기, 신규 상장 기업 기간을 0으로 채우기(범위 밖).

---

## §H 참조

- 승인 계획: `.moai/plans/wondrous-noodling-coral.md`
- 선행 SPEC: `SPEC-FNGUIDE-ENGINE-001`(본문 참조, frontmatter 없음), `SPEC-DASHBOARD-001`(본문 참조, `status: draft`), `SPEC-DASHBOARD-002`(`depends_on`, `status: completed`)
- 감사 독립 재구현: `scratchpad/auditor/indep.py`(plan 단계 산출물, 읽기 전용)
- 교훈: 메모리 `lessons.md` #9(대조 단언은 되돌림 RED 관측으로 판정), #10(산문 주장에 프로브), #7(UI 대응표·되돌리기)
- 실행환경: 메모리 `project_server_runtime_env.md`, `project_worktree_precommit_db_trap.md`, `feedback_precommit_guard_false_positive.md`
