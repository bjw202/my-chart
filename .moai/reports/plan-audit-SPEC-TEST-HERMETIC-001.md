# SPEC Plan-Audit Report — SPEC-TEST-HERMETIC-001

- Iteration: 1/3 (델타 재감사 Iteration 2는 §9-§12에 추가 — 최종 판정은 §12)
- 일자: 2026-10-21
- 감사자: plan-auditor (독립 감사, M1 Context Isolation 적용 — 작성자 추론 맥락 없이 산출물만 검사)
- 대상: `.moai/specs/SPEC-TEST-HERMETIC-001/` (spec.md, plan.md, acceptance.md, progress.md) — Tier M
- 기원: 칸반 카드 t12

## 1. 최종 판정

| 항목 | 값 |
|------|-----|
| **Verdict** | Iteration 1: **PASS-WITH-DEBT** → Iteration 2 (델타): **PASS** (§12) |
| 조화평균 점수 | 1차 **0.81** → 2차 **0.86** (Tier M 기준 0.80 이상) |
| 1차 근거 | must-pass 전 항목 통과(MP-1~MP-7), 4차원 조화평균 0.809. 단 SHOULD-FIX 3건·MINOR 3건의 부채. |
| 2차 근거 | 6건 수정 전부 결함 범위 내 적용 확인, 신규 결함 없음 — 승격 (§9-§11). |

## 2. Must-Pass 결과

- **[PASS] MP-1 REQ 번호 일관성**: REQ-001~REQ-010 순차, 중복·결번 없음 (spec.md:52-90).
- **[PASS] MP-2 GEARS 형식 (요구 레이어 기준)**: 10개 REQ 전체가 5 패턴 중 하나와 일치 — Ubiquitous(REQ-001/003/007/010), Event(REQ-002/005/006: spec.md:58,70,74), Unwanted(REQ-004: :66 "shall not"), Capability gate(REQ-008 이중 Where: :82), State(REQ-009: :86). AC 레이어의 Given-When-Then은 검증 레이어의 올바른 형식이므로 감점 대상 아님(M3 §Scope).
- **[PASS] MP-3 YAML 프론트매터**: 12개 필수 필드 전원 존재·타입 적합 (spec.md:2-14). `status: draft`, `priority: P1`, `phase: "v0.6.0 target"`(릴리스 라벨 — 금지 스테이지명 아님), `lifecycle: spec-anchored`, `tier: M`(선택 필드). snake_case 별칭 없음.
- **[N/A] MP-4 언어 중립성**: 프로젝트 단일 스코프(Python pytest + JS vitest) SPEC — 다국어 도구열거 의무 없음. 자동 통과.
- **[PASS] MP-5 D7 cross-SPEC**: spec.md 본문 외부 SPEC 참조 없음. plan.md §H의 3건(SPEC-RS-REBALANCE-001 / SPEC-SECTOR-GRID-001 / SPEC-THEME-DISPLAY-UNIFY-001) 모두 `.moai/specs/`에 존재하며 `status: completed` 실측 — retired/superseded/archived 없음, 화해 조항 불요.
- **[PASS] MP-6 D8 cross-platform**: `syscall` 문자열 3개 산출물 모두 0검출 → D8-4 자동 통과.
- **[PASS] MP-7 clarification 게이트**: `[NEEDS CLARIFICATION]` 마커 SPEC 디렉터리 전체 0검출.

## 3. 카테고리 점수 (1차 기준, 0-10)

| 차원 | 점수 | 산술 근거 |
|------|------|-----------|
| Clarity | 8.0 | GEARS 전 건 매칭. 감점: REQ-003의 autouse 픽스처 의미론 두 해석 가능(D5), REQ-004 이중 부정(D6) |
| Completeness | 7.5 | 21건(12+4+5) 커버 완결, M1→M2 게이트 경질, vitest 불실행 시 no-op 경로 정의. 감점: D1 바인딩 방어선 부재, D2 skip 탈출 검출 공백, D3 전제 오류 |
| Testability | 8.0 | AC-001(종료코드+출력), AC-004/005(종료코드), AC-010(find 정밀 설계), AC-003 되돌림 RED 명시(레슨 #9 준수). 감점: AC-002 검사절 누락, AC-008 프루브 hedge |
| Traceability | 9.0 | REQ↔AC 매트릭스 완결, 카드 t12 링크, 증거 경로 선언. 감점: AC-001 오구현 (ii)의 거짓 상호참조(D2) |

**1차 조화평균 8.09/10 → 0.81**

## 4. 결함 목록 (Iteration 1)

### D1 — 워크트리 pytest 실행의 import 바인딩 무검증 (SHOULD-FIX)

- **위치**: plan.md:28(§C-4), plan.md:49-59(M1), acceptance.md:14-16(AC-001 Given)
- **내용**: venv에 `__editable__.kr_stock_screener-0.1.0.pth` 편집 설치가 있고, 파인더가 `backend`/`my_chart`를 **메인 체크아웃 절대 경로**에 바인딩함을 실측(중립 cwd /tmp에서 import 귀속 관측). 메인 Output DB 실재(487MiB/373MiB). 바인딩이 어긋나면 DB-less 워크트리에서조차 메인의 DB를 읽어 **수정 없이 위양성 GREEN**이 되고 AC-001·AC-010은 모두 통과하며 REQ-004 위반은 어떤 검출기에도 걸리지 않는다.
- **완화 사유**: `tests/__init__.py` 존재(실측)로 pytest prepend가 워크트리 루트를 sys.path[0]에 삽입 → 현재는 안전. 단 3중 암묵 조건 위에 서 있고 plan/SPEC 어디에도 명시·검증되지 않음.
- **필수 수정**: §C-4 바인딩 단언 1줄 + M1에 "예상 대비 0건 관측 시 중단" 조항.

### D2 — skip 탈출(게이밍) 검출기 부재 (SHOULD-FIX)

- **위치**: acceptance.md:18(AC-001 오구현 ii), :76-82(AC-009)
- **내용**: AC-001이 "skip 급증 시 AC-009·AC-006에서 적발"이라 주장하나 기계적으로 거짓 — AC-009는 실패 델타만, AC-006은 5건 한정. SPEC §1.3 자체 규정 위반.
- **필수 수정**: AC-009에 skip 델타 0 요구 추가 또는 AC-001 검사 확장.

### D3 — 조사#3의 test_ac_sag_045 서술 부정확 (SHOULD-FIX)

- **위치**: spec.md:39(조사#3), plan.md:17(B4)
- **내용**: "sag 파일이 frozen 픽스처를 패치하고 있다" — 실측: 패치 문자열 0건, frozen 경로를 `compute_sector_aggregates(...)` 명시 인자로 전달하는 별개 메커니즘. M3 진단 전제 정정 필요.

### D4 — "DB 경로 터치 테스트 파일 12개" vs 실측 11개 (MINOR)

- **위치**: spec.md:40, plan.md:63
- **내용**: grep 실측 11개(fixtures 헬퍼 포함). SPEC 자체 §G-3(개수 상수 고정 금지) 및 lesson #10과 모순.

### D5 — REQ-003 autouse 픽스처 의미론 이중 해석 (MINOR)

- **위치**: spec.md:62 vs plan.md:63
- **내용**: autouse가 DB를 생성하는지 경로만 대체하는지 두 해석 가능.

### D6 — REQ-004 이중 부정 (MINOR)

- **위치**: spec.md:66
- **내용**: "shall not … 읽거나 생성하지 않는다" 중첩 부정.

### 선택급 관찰 (결함 아님)

- `frontend/package.json` test 스크립트 인용 :9 → 실제 :12 (내용 정확).
- "gate.yaml의 유일한 노브는 disabled_steps" — `gate.skip_tests`도 존재하나 결론(스코프 게이팅 부재) 불변.
- AC-008 프루브 형태 hedge — M4 실측이 흡수.
- DB-less 준비 확인이 `Output/*.db`만 점검 — `Input/`, `.cache/` 미열거. M1 관측·AC-001 0실패 바가 흡수.

## 5. SPEC 산문 주장의 프로브 검증 대조 (lesson #10 준수도)

| SPEC 주장 | 프로브 결과 |
|-----------|------------|
| `backend/deps.py:10-11` 모듈 상수 복사 토폴로지 | ✅ 정확 |
| `my_chart/config.py:36,40,43-44` + 임포트 시점 mkdir | ✅ 줄 단위까지 정확 |
| test_market_api `test_client` DAILY 미패치, `:194` 동일 파일 메서드 | ✅ 정확 (:127-137, :194-200) |
| test_response_contract `stage.DAILY_DB_PATH` 누락 | ✅ 정확 (:94-101) |
| conftest `daily_db`/`weekly_db`(209-283)·`mock_sectormap`(48-62) | ✅ 정확 |
| `pyproject.toml` testpaths / 마커 필터 `not live and not slow` | ✅ 정확 (:56, :59) |
| `nongating` 마커 실재 | ✅ pyproject.toml:64 |
| `frontend/vite.config.ts:15-20` root/include 미고정 | ✅ 정확 |
| frozen 픽스처 git 추적 | ✅ daily.db/weekly.db/registry.xlsx 전부 추적 |
| 조사#3 sag 파일 "패치하고 있어" | ❌ D3 — 인자 전달 방식, 패치 아님 |
| "DB 경로 터치 파일 12개" | ❌ D4 — 실측 11개 |

11/13 정확. 오류 2건 모두 결론(스코프·처리 방침)은 유지되면서 전제 서술만 어긋난 유형.

## 6. 증거와 한계 (검증-청구 무결성)

- **관측한 것**: 위 표의 13개 프로브, 편집 설치 파인더 바인딩 경로(/tmp 중립 cwd에서 import 실측), tests/__init__.py 존재, 메인 Output DB 실재, D7 3건 status, MP-6/MP-7 grep.
- **관측하지 않은 것(한계)**: 실제 워크트리를 만들어 pytest를 돌려보지 않았다 — D1의 "현재는 안전" 판정은 /tmp 실측 + `tests/__init__.py` 메커니즘 분석에 근거한 추정이며, M1의 바인딩 단언 + RED 관측이 런타임에 확증한다. `moai gate` 실측도 run-phase(M4) 몫.

## 7. 오케스트레이터 전달 상위 3건 (Kickoff 전 사용자 보고용)

1. **D1 — DB-less 검증의 암묵 전제**: 워크트리 테스트가 메인 체크아웃 코드·DB로 새는 것을 지금은 `tests/__init__.py`가 막고 있는데, 이 방어선이 plan 어디에도 명시돼 있지 않았다.
2. **D2 — skip 탈출 검출 공백**: AC-001이 "skip 급증은 AC-009/006이 잡는다"고 주장했지만 실제로 잡는 AC가 없었다.
3. **D3+D4 — 조사 사실 정정 2건**: sag 파일은 frozen 픽스처를 패치가 아니라 함수 인자로 전달하며, DB 경로 터치 파일은 12개가 아니라 11개다.

## 8. 1차 권고 (Iteration 1 시점)

PASS-WITH-DEBT. D1~D3 소폭 수정 후 결함 델타 범위 재감사로 PASS 승격 권고. D4~D6 재량.

---

# Delta Re-Audit — Iteration 2 (2026-10-21)

범위: 1차 감사 결함 D1~D6의 수정 델타만 (전면 재감사 아님 — Retry Loop Contract 델타 스코프). 위 §1의 1차 판정은 이 섹션 §12가 **대체**한다.

## 9. 수정별 검증 결과

| 결함 | 검증 결과 | 근거 |
|------|-----------|------|
| D1 | **RESOLVED** | plan.md:28 §C-4에 편집 설치 파인더 바인딩 리스크 + `tests/__init__.py` → sys.path[0] 안전장치의 무문서 상태 + 바인딩 단언 명령(출력이 워크트리 내부 경로여야 하고, 주 체크아웃 경로면 즉시 중단) 기록. plan.md:55 M1 절차에 단언 삽입(수집·실행에 선행). plan.md:60 중단 조건 신설 — "관측 실패 0건(예상 ≈21건 대비)이면 DB-less 전제 붕괴, 1순위 원인 임포트 바인딩, 수정될 때까지 M2 착수 금지" — 위양성 GREEN을 스스로 발화시키는 요구 조항. acceptance.md:14 AC-001 Given에 단언 통과 선결조건 추가 |
| D2 | **RESOLVED** | acceptance.md:80-82 AC-009 Then이 "skip 수 델타 0"까지 요구, 검사절이 실패 델타 + skip 델타 모두 비교, 오구현 (ii)에 skip 전환 변형 명시. acceptance.md:18의 거짓 상호참조가 "skip 수 델타 0을 요구하는 AC-009"로 정확히 수선됨 — SPEC §1.3 자기규정과의 모순 해소 |
| D3 | **RESOLVED** | spec.md:39·plan.md:17(B4)이 m6(패치형, 36-39행)과 sag(명시 인자형, 패치는 registry 3건뿐)를 분리 서술. sag 파일 원본 대조 결과 manager-spec의 인용(44-46·61행)이 정확 — `_fixed_registry()`의 3개 patch() 호출이 44-46행, `sm.compute_sector_aggregates(` 호출 개시가 61행. 1차 감사의 내 인용(30-34행)은 상수 정의 블록(AGG_DIR/WEEKLY_DB/DAILY_DB/REGISTRY/AS_OF)을 가리킨 채 부정확했으므로 **본 감사 측 인용을 정정**하며 fix는 채택 |
| D4 | **RESOLVED** | spec.md:40 고정 개수 삭제 → "다수 존재(직접 grep 확인 — 고정 개수 대신 M1 시점에 실측 목록을 evidence로 남긴다)". plan.md:65 M2도 "(M1 시점 grep 실측 목록)"으로 동기화. §G-3 규정과의 모순 해소 |
| D5 | **RESOLVED** | spec.md:62 REQ-003에 "이 픽스처는 경로 상수 대체만 수행하며 DB 파일을 생성하지 않는다 — DB 파일 자체가 필요한 테스트는 기존 daily_db/weekly_db 픽스처를 계속 명시 요청한다" 추가 → 단일 해석 고정, plan.md:63 M2 서술과 일치 |
| D6 | **RESOLVED** | spec.md:66 REQ-004가 "shall not … 읽거나 생성한다"로 수선 — 이중 부정 해소, Unwanted 패턴 유지 |

**새 결함 도입 여부**: 수정 창(spec.md:39-40·62·66, plan.md:17·28·55-60·65, acceptance.md:14·18·80-82) 외 본문은 1차 판독 상태와 동일 — 스코프 확산 없음, 신규 결함 없음.

**lint 재실행 독립 확인**: `mcp__moai__spec_audit` 재실행 결과 error/warning 0건 — 유일한 finding은 `EraAutoDetected V3R5 (H-3: §E.2 present, sync_commit_sha missing)` INFO 1건으로, sync 미종료 in-flight SPEC의 정상 상태다. manager-spec의 "0 findings" 주장과 정합.

**좌표 정정(비결함)**: 조정자 전문은 바인딩 단언을 "M1 step 1"로 전달했으나 실제로는 M1 절차 step 3이다(1: 기준선 완료, 2: DB 부재 확인, 3: 바인딩 단언, 4: 수집, 5: 전체 실행). 순서 자체는 올바르다(단언이 수집·실행에 선행) — SPEC 결함 아님, 전달 요약의 서술 오류만.

## 10. 잔여 관찰 (optional-class — 게이트 비대상)

1. **DB-less 전용 조건부 skip 코너**: 정상 환경에서만 통과되고 DB-less에서 skipif로 건너뛰는 테스트는 AC-009의 정상환경 skip-델타로는 검출되지 않는다. M1 실패 ID 전수 목록 + REQ-006 재분류 금지가 증거 체인으로 막지만, 후속 강화 후보로 "최종 GREEN 실행의 통과 집합 vs M1 실패 ID 목록 대조"를 남긴다.
2. **1차 감사의 선택급 관찰 불변**: AC-002 검사절의 참조-경로-실존 확인 누락, AC-008 프루브 형태 hedge(M4 실측이 흡수), `Input/`·`.cache/` 미열거(§C-3) — 모두 optional로 유지.
3. **문서 표기 미세 항목**: `frontend/package.json:9` → 실제 :12 (내용 정확).

## 11. 승격 점수

| 차원 | 1차 | 2차 | 변동 근거 |
|------|-----|-----|-----------|
| Clarity | 8.0 | 8.5 | D5 단일 해석, D6 수선 |
| Completeness | 7.5 | 8.5 | D1 방어선+중단조건, D2 검출기, D3 전제 수선 |
| Testability | 8.0 | 8.0 | AC-001 Given 강화됐으나 AC-002·AC-008 미세 항목 불변 |
| Traceability | 9.0 | 9.5 | 거짓 상호참조(AC-001:18→AC-009) 수선 |

**조화평균: 4 / (1/8.5 + 1/8.5 + 1/8.0 + 1/9.5) = 8.59/10 → 0.86**

## 12. 최종 Verdict

- **Verdict: PASS** (Tier M 기준 0.80 이상 — 0.86)
- Must-Pass MP-1~MP-7: 유지 PASS (델타가 프론트매터·REQ 번호·GEARS 구조를 침범하지 않음 재확인)
- 잔여 결함: BLOCKING/SHOULD-FIX 0건, optional-class 관찰 3건(§10)
- 검증 한계(불변): 실제 워크트리 pytest 실행은 여전히 미실시 — D1의 안전성은 /tmp import 실측 + `tests/__init__.py` 메커니즘에 근거하며, M1 step 3의 바인딩 단언과 이어지는 RED 관측이 런타임에 확증한다.

**Kickoff 게이트 상태: PASS — Implementation Kickoff Approval 진행 가능.**
