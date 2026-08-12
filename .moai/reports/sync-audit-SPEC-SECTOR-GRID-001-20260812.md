# sync-auditor 감사 기록 — SPEC-SECTOR-GRID-001

- **감사 시점**: 2026-08-12, 대상 HEAD `fca134c` (v0.2.2 `completed` 직후)
- **판정**: **PASS-WITH-DEBT 78.6/100** (조화평균) — BLOCKING 0건 / SHOULD-FIX 6건 / MINOR 6건
- **차원별**: 기능성 78 (40%) · 보안 92 (25%) · 장인정신 72 (20%) · 일관성 75 (15%)
- **처리**: 사용자 승인 후 in-place amendment (v0.3.0). 커밋 `2140cd6`(SPEC 본문) → `a61c3c1`+`e07ae36`(테스트) → `5931a14`+`212d70c`(재close)

> 이 파일은 감사 결과의 영구 기록이다. 감사 당시 리포트가 파일로 저장되지 않아 세션 대화에만 존재했고, manager-docs가 §E.4에 "미기록"으로 정직하게 남긴 항목들을 여기에 복원한다.

---

## 귀무가설 검정 — 기각됨

감사자가 "이 SPEC의 변경이 실제로 무언가를 고쳤는가"를 반증 시도했으나 **변경은 진짜**로 확인됐다.

- `history(weeks=12)`가 프로즌 스냅샷(385 날짜)에서 77~91일 구간 반환 — 구 `LIMIT 36` 경로는 36
- `_get_latest_valid_date`가 `fixture_max_ne_canonical`에서 `2024-01-12` 반환, 순진한 `MAX(Date)`는 `2024-01-15`
- allowlist를 벗겨낸 원시 3종 관용구 스캔에서 주봉 소비자 7곳 전부 0건 — 배선 전환은 실제로 일어났다
- `test_stock_prices_legacy_alter_positional_shifts_ac010`은 구 positional 경로를 같은 픽스처에 실행해 시프트 발생을 단언하는 진짜 mutation test

**회귀 가설도 기각**: 감사자의 1차 비교가 회귀(7→8)를 시사했으나 worktree에 untracked 파일이 없어 생긴 artifact였다. 실제 원인은 `meta_service.py:239`가 untracked `Input/basic_data.xlsx`를 읽는 것이며, 무관 커밋 `908f03c`에서 유래한다. `git diff --stat HEAD -- backend/ my_chart/ tests/` 공백 확인.

---

## 결함 목록 및 처리 상태

| ID | 심각도 | 요지 | 처리 |
|---|---|---|---|
| F1 | SHOULD-FIX | `test_universe.py` AC-SGR-021 행동 단언이 항진명제. `stage_key`/`metrics_key`가 바이트 동일 표현식, 프로덕션 코드 미호출. docstring의 반증 주장은 거짓 | **수정** (`a61c3c1`) — 두 프로덕션 경로 실호출 + 되돌림 RED 실증 |
| F2 | SHOULD-FIX | `test_consumer_dates.py` AC-006-A가 6-way 대조를 표방하나 A-4/A-6이 공유 헬퍼 자기 호출 → 실제 4-way. `sector_advanced_service`·`meta_service` 완전 되돌림에도 통과 | **수정** — A-4 → `get_sector_bubble`, A-6 → `rebuild_stock_meta` 관측. REFERENCE_STOCK 전제 명시 단언 추가 |
| F3 | SHOULD-FIX | `test_regression_sgr020.py` R5 `len(history) <= COUNT(DISTINCT Date)`가 수학적 항진명제. 결함 원천은 acceptance.md R5 자체 | **수정** — 프로즌 리터럴 345/346/385 + strict 3-way + 대조 단언 |
| F4 | SHOULD-FIX | AC "And" 절 6건 미구현: (a) allowlist 근거 회귀 (b) **allowlist 상한 단언 — 어디에도 없음** (c) 7모듈 import 중 2개만 검사 (d) AC-006-A 라이브 스모크 (e) AC-017 라이브 진단 (f) AC-020 R3(b) WARNING 로그 | **부분 수정** — (b) 상한 5 기계 단언 추가, (c) 7개 AST 단언, (d)(e) 비게이팅 명시. (a)(f) **미해결** |
| F5 | SHOULD-FIX | DoD `신규 격자·유니버스 모듈 커버리지 >= 85%`가 측정도 §Gaps 기재도 없음 (`grep -i coverage progress.md` → 0건). 감사자 3회 측정 시도 전부 실패 | **해결** — `coverage run --source=my_chart,backend -m pytest` 로 측정 성공. weekly_grid 100%(94/94), universe 100%(56/56), db/weekly 47%(95/202). 게이트 충족 |
| F6 | SHOULD-FIX | acceptance.md AC-005 스캔 명령이 유효하지 않은 bash (`\` 누락으로 universe.py 제외줄 고아화, `bash -n` exit 2). 테스트 `_AC005_GREP`은 그 제외를 생략하고 `--include="*.py"`를 무단 추가 | **수정** — 명령 복구 + 배제 체인 → 잔여 집합 동등, 테스트 상수를 acceptance.md에서 런타임 추출해 바이트 동등 단언 |
| F7 | MINOR | AC-SGR-004의 라이브 근거가 프로즌 픽스처에서 재현 불가. `MANIFEST.md`: `CG-3 배제된 대표 바 0건` → 프로즌 경로가 아무것도 검사 안 함. §3은 frozen-applicable로 표기 | **수정** — CG-3이 실제 발화하는 합성 픽스처로 재게이팅 + 제거 대조 |
| F8 | MINOR | spec.md §1.2.2 allowlist의 `chart_service.py` 항목이 무의미 (해당 파일 3종 관용구 0건). 상한(6)을 잠식 | **수정** — 항목 제거, 상한 6→5 축소 |
| F9 | MINOR | `test_consumer_dates.py:159-163` docstring이 "BLOCKER … allowlist가 누락 … manager-spec이 보완해야" 로 남아 있으나 spec v0.2.2가 이미 추가함 | **미확인** — amendment 중 해당 테스트가 대폭 재작성돼 잔존 여부 불명 |
| F10 | MINOR | §1.2.1 소비자 인벤토리 행 번호 드리프트 (`stage_service.py:25`·`market_service.py:37`은 현재 빈 줄, `meta_service.py:135`→`:136`). SPEC이 이를 지점 식별자로 사용하므로 정밀도 손실 | **수정** (`2140cd6`) — 재도출 갱신 |
| F11 | MINOR | `test_weekly_grid.py:129`가 테스트 내 재구현과의 비교를 대조 단언으로 오표기. 실제 반증은 line 120의 하드코딩 리터럴 | **미확인** — 동일 사유 |
| F12 | MINOR | O-G6(`market_breadth.py:472`)가 주봉 DB에 I2 관용구 사용 → `weeks=12`가 ~36일. 라이브 사용자 노출 오계산인데 §7 열린 질문으로만 기재, §Residual-risk 부재 | **기록** — §Residual-risk 등재 + §7 심각도 문구 상향. **수정은 별도 SPEC 필요** |

---

## 감사자의 기록 정정 요구

> progress.md §E.2가 `대조 단언(falsification) 7종 — 전부 GREEN`이라 서술했으나, 그중 3종은 구현 존재/부재를 구분하지 못한다. 정확한 서술은 **4건 유효 / 3건 무효**.

amendment에서 §E.2를 정정했다(덮어쓰지 않고 당시 부정확성을 남긴 채 기록). 감사자 지적대로 이 패턴 자체가 교훈 대상이다 — spec.md HISTORY 0.2.0~0.2.1이 AC 층에서 같은 결함 4건을 잡아 고쳤음에도 테스트 작성 층에서 3건이 재발했다. 교훈은 auto-memory `lessons.md` #9에 기록.

---

## amendment 후 검증 (orchestrator 직접 실행)

| 항목 | 결과 |
|---|---|
| 되돌림 RED 실증 | 6/6 관측 (F1·F2 A-4·F2 A-6·F3·F6·F7) |
| 게이팅 스위트 | 69 → **84 passed** |
| 전체 스위트 | 569 → **584 passed**, 실패 8건·error 25건 baseline과 동일 → 회귀 0 |
| 구현 파일 diff | `git diff --stat 1ccf918..HEAD -- my_chart/ backend/ frontend/` **공백** |
| origin 정합 | `0 0` |

---

## 남은 열린 항목

1. **O-G6 수정 SPEC** — 라이브 오계산, `canonical_weekly_grid` 재사용으로 해결 가능 (Tier S 예상)
2. **NaN 진리값** — 진짜 NULL `산업명(대)`가 `'기타'`가 아닌 `'nan'`으로 귀결. 두 경로 일치라 AC는 충족하나 요구사항 미결
3. **AC-SGR-004 문구 충돌** — "한 ISO 주 두 날짜"는 문자 그대로 구현 불가 (주 전체 탈락, 이른 날 폴백 없음)
4. **F4 (a)(f)**, **F9/F11 미확인**, **`db/weekly.py` 47% 해석**
5. **기존 결함 8건 + fnguide 25건** — 본 SPEC 범위 밖

---

기록일: 2026-08-13 · 기록자: orchestrator (sync-auditor 판정 + 직접 검증 결과 통합)
