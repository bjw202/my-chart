# SPEC-AI-REPORT-007 — 진행 기록

버전 0.4.0 · 변경 이력: 0.1.0~0.3.0은 `spec.md` HISTORY와 같다. 0.4.0(2026-10-21, manager-spec) — §E.1에 v0.4.0 개정 요약·계수(REQ 15·AC 15)·사실표 P6·P14 재측정과 P17~P19 추가. §E.2(run 단계 M1 기록)는 이 개정에서 고치지 않았다.

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-10-21T00:00:00+09:00
- plan_status: v0.4.0 — run 단계 M1 관측(§E.2 V1~V5) 반영 개정, 재감사 대기
- plan_audit:
  - 1회차 FAIL 0.81 — `.moai/reports/t19/plan-audit.md` (D1a·D1b·D3·D4·D5·D6 차단, D2·D7·D8·D9·D10 선택 → v0.2.0에서 전부 반영)
  - 2회차 FAIL 0.85 — `.moai/reports/t19/plan-audit-iter2.md` (N1·N4 차단, N2·N3·N5·N6·N7 선택 → v0.3.0에서 전부 반영. N6은 리드가 통합 카드에 병합 단계를 적는 방식 — plan.md §5 "수행 책임")
  - 3회차 PASS 0.88 — 커밋 `9feb1fe`의 보고서(v0.3.0 대상)
- v0.4.0 개정(M1 관측 반영, 2026-10-21): V1 그룹 펼침·모양 오류 기록(REQ-006·007·008·009·014, AC-006·007·008·014), V2 요약 본문 인정 조건(사용자 결정 — D3, REQ-010·013, AC-009·010·012), V3 엔티티 해제 순서(REQ-006, AC-006 6·7), V4 `code_validated`(D9, REQ-015·AC-015 신설), V5 나머지 키 무시·주소는 검증된 식별자로(REQ-006, AC-007 교차 확인). 근거 프로브는 아래 P6·P14·P17~P19
- card: t19 · worktree: `.claude/worktrees/t19` · branch: `WT-naver-search-block` · 1회차 기준 HEAD `c8e5c20`, 2회차 수정 기준 HEAD `5b7a22b`, v0.4.0 수정 기준 HEAD `871c105`
- artifacts: spec.md, plan.md, acceptance.md, progress.md
- counts: REQ 15개(REQ-AIR7-001~015), AC 15개(AC-AIR7-001~015) — Tier M 상한(각 16) 이내. 새 번호는 끝에 붙였고 기존 번호는 바꾸지 않았다
- needs_clarification: 0건 (G4·G5는 M1에서 관측 완료 — spec §8)
- gating_live_ac: AC-AIR7-012는 리드 몫(통합·재시작 뒤), 이 레인 밖
- overlap: SPEC-AI-REPORT-006(카드 t18, 커밋 `4663bb3`)과 `goose_job_service.py`·`harness-instructions.md`(둘 다 규칙 9 추가)·`goose-manifest.json`·`test_goose_job_service.py` 겹침 — plan.md §5 필수 병합 단계

### 미결 사항 (리드 결정)

- Q1 `phase` 값 **[해결 2026-10-21: 리드가 `"v0.6.0 target"`으로 결정, spec.md 프런트매터 반영]**. 아래는 결정 전 기록이다. spec.md 프런트매터는 `"v0.5.5 target"`이었다. 이것은 AI-REPORT 계열 순번(004 `v0.5.3`, 005 `v0.5.4`)을 이은 **미확정 가정**이며 사실로 주장하지 않는다. 저장소에는 이 값을 고정하는 원천이 없고(사실표 P15), 005 이후 완료된 SPEC-TEST-HERMETIC-001·SPEC-RS-REBALANCE-001과 카드 t18의 SPEC-AI-REPORT-006은 `"v0.6.0 target"`을 쓴다. 006과 맞추려면 `"v0.6.0 target"`, 계열 순번을 지키려면 그대로 둔다. 리드가 정하면 manager-spec이 프런트매터만 고친다.

### 계측으로 확정한 사실 (lessons #10 — 주장 | 관측 방법 | 결과)

P1~P5·P7·P8은 2026-10-21 HEAD `c8e5c20`에서, P9a·P9b·P10~P12·P15는 같은 날 HEAD `5b7a22b`에서, P13·P16은 v0.3.0 문서 기준으로, P6·P14·P17~P19는 v0.4.0 문서와 HEAD `871c105` 기준으로 같은 날 이 문서 작성자가 직접 실행했다(감사 보고서·M1 기록의 프로브를 옮겨 적지 않았다).

| # | 주장 (spec·plan·acceptance에서 쓰는 곳) | 관측 방법 | 결과 |
|---|---|---|---|
| P1 | 권한 파일은 `WebFetch`를 도메인 제한 없이 허용하고, 해시는 고정값이다 (spec §2.5, AC-011 #2) | `shasum -a 256 backend/goose_harness_src/claude-settings.json`; `grep -c '"WebFetch"' …`; `grep -c 'WebFetch(' …` | `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`; `1`; `0` (도메인 지정 형태 `WebFetch(...)`는 0회라 이 프로브는 제한이 있었다면 볼 수 있었다) |
| P2 | a5becbb9 실행의 권한 거부는 Bash 1건뿐이고 WebFetch 언급은 없다 (spec §2.5) | 주 체크아웃 `.dev-server.log`: `grep -c a5becbb9`; 그 줄 중 `grep -ci denied`; 그 줄 중 `grep -ci webfetch` | `3`; `1` — 원문 앞부분: `goose 세션 permission_denied: 도구=Bash 사유=rule 명령=cd /Users/byunjungwon/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/dart && for f in …`; `0`. 한계: 로그는 실행기가 해석한 권한 거부만 남기므로 WebFetch 도구 오류의 부재를 증명하지 않는다(spec G1) |
| P3 | 감사의 `naver` 채널 조건, `no_results` 무조건 통과, `blocked` 불인정 (spec §2.4) | `grep -n "channels.update\|read_ids(s.get('source_ids'))\|차단은 완료가 아닙니다" audit_report.py`; `grep -c "verification')!='direct_read'" audit_report.py` | 44행 `channels.update({'company_ir','naver','industry'})`, 51행 `if (s.get('result')=='read' and read_ids(s.get('source_ids'))) or s.get('result')=='no_results'`, 52행 결함 문구에 `차단은 완료가 아닙니다`; `1`. 51행에서 `no_results`는 다른 조건 없이 통과한다. `read_ids` 본문(21~28행)은 Read로 확인: `dart=True`일 때만 호스트를 검사하며 51행 호출은 `dart` 인자가 없다 |
| P4 | 작업 서비스에는 아직 네이버 관련 코드가 없고, DART 수집기는 운영 인스턴스에만 붙어 있다 (spec §4, plan T5) | `grep -c naver backend/services/goose_job_service.py`; `grep -n "prefetcher=goose_dart_prefetch" …` | `0`; `389:    prefetcher=goose_dart_prefetch.DartPrefetcher(),` |
| P5 | 새 수집 모듈 파일은 아직 없다 (spec §4 [NEW]) | `ls backend/services/goose_naver_prefetch.py` | `No such file or directory` |
| P6 | AC-009 검사 문자열의 기준선 — 네이버 규칙 전용 문자열은 모두 0이라 프로브가 부재를 볼 수 있다. 규칙 8과 겹치는 짧은 표기는 이미 1이다 (AC-009) | **v0.4.0 재측정**(HEAD `871c105`, 같은 루프): `0 API 요약본(약 150자), 원문 미확인` · `0 요약에 없는 사실은 단정하지 않는다` · `0 모바일 뉴스 API 응답의 제목·요약 본문 필드` · `0 code_validated` · `0 서버가 종목코드 유효성을 확인하지 못함` · `0 runs/<job_id>/naver/index.json` · `0 article_url` · `0 channel: "naver"` · `0 metadata_only` · `0 "no_results"` · `0 서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음` · `0 이번 세션에서 그 파일을 연 시각` · `0 original_news` · `2 runs/<job_id>/dart/index.json`. 아래는 v0.3.0 측정 기록: `for s in …; do printf '%s\t%s\n' "$(grep -cF "$s" harness-instructions.md)" "$s"; done` (HEAD `5b7a22b`) | `0 runs/<job_id>/naver/index.json` · `0 article_url` · `0 channel: "naver"` · `0 metadata_only` · `0 "no_results"` · `0 모바일 뉴스 API 응답의 제목·본문 필드` · `0 서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음` · `1 accessed_at` · `0 original_news` · `2 runs/<job_id>/dart/index.json` · `1 서버 사전 수집본으로 열람`; 대체 문자열 `grep -cF '이번 세션에서 그 파일을 연 시각'` → 지침 `0`, plan.md 초안 `1`. ~~v0.1.0 AC-009의 "규칙 9를 지우면 앞의 8개 문자열이 모두 0"~~ — 철회: `서버 사전 수집본으로 열람`은 규칙 8에도 있어 지워도 1로 남는다(1회차 감사 A4). v0.2.0은 규칙 8과 겹치지 않는 문자열만 쓴다 |
| P7 | 파일 이름이 `test_goose_`로 시작하면 기존 네트워크 가드가 적용된다 — conftest 변경 불필요 (spec §4 [EXISTING], REQ-AIR7-012) | `grep -n "_GOOSE_PREFIXES = " backend/tests/conftest.py` | `20:_GOOSE_PREFIXES = ("test_goose_", "test_main_goose")` |
| P8 | 지침 내용을 검사하는 기존 테스트는 규칙 4-1·4-2 문자열과 매니페스트 해시만 본다 — 규칙 추가는 그 단언을 깨지 않는다(매니페스트 재생성 전제) (plan §5, AC-011 #3) | `grep -n '_REAL_SOURCE / "harness-instructions.md"' backend/tests/test_goose_harness.py` → 431·468행, 466~477행 Read | 431행 매니페스트 해시 비교, 468행 이후 4-1·4-2 문자열 포함 단언 8개(추가된 규칙과 무관) |
| P9a | ~~SPEC ID가 형식에 맞고 006·007이 모두 비어 있다~~ — **철회**(1회차 감사 D2): c8e5c20(16:58:56) 시점 관측은 맞았으나 그 뒤 17:10:50에 카드 t18이 SPEC-AI-REPORT-006을 커밋했다. 006은 카드 t18이 가지고 있으므로 이 SPEC은 007을 그대로 쓴다 | `[[ "SPEC-AI-REPORT-007" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS`; `git -C <worktree> log -1 --format='%h %ci %s' 4663bb3` | `PASS`; `4663bb3 2026-10-21 17:10:50 +0900 docs(SPEC-AI-REPORT-006): plan 단계 SPEC 초안 작성 (카드 t18)` |
| P9b | SPEC-AI-REPORT-006도 규칙 9를 더하고 매니페스트를 재생성하며 작업 서비스를 바꾼다 (spec 관계 문단, plan §5) | `git -C <worktree> show 4663bb3:.moai/specs/SPEC-AI-REPORT-006/spec.md \| grep -n "^phase:\|harness-instructions\|goose_job_service\|goose-manifest"` | `10:phase: "v0.6.0 target"` · `65:… goose_job_service.py … 1차 세션 뒤 후처리(재검사 → 캡처 → 감수 → 영수증), 진행 이벤트, 끄기 스위치, 취소·fail-open` · `66:… harness-instructions.md … 규칙 7 개정, 감수 세션 규칙 9 추가` · `67:… goose-manifest.json … 지침 변경에 따른 매니페스트 재생성` · `72:… test_goose_job_service.py, test_goose_runner.py, test_goose_harness.py …` (49행 D3 결정 줄도 `harness-instructions.md`를 언급) |
| P10 | `dart_prefetch` 단계는 프론트 소스 3개와 프론트 테스트 2개에 박혀 있다 — 새 단계를 만들면 같은 범위가 바뀐다 (plan T6) | `grep -rln dart_prefetch frontend/src`; `grep -rln dart_prefetch backend/tests` | 프론트: `types/aiReport.ts`, `utils/__tests__/gooseJob.test.ts`, `utils/gooseJob.ts`, `components/ProgressPanel.tsx`, `components/__tests__/ProgressPanel.test.tsx`; 백엔드 테스트: `test_goose_dart_prefetch.py`, `test_goose_job_service.py`, `fixtures/dart/README.md` |
| P11 | 출처마다 `accessed_at`이 필수다 (spec REQ-010, plan T2) | `grep -n accessed_at …/stock-report/references/report-input.md`; `grep -n accessed_at …/stock-report/scripts/render_report.py` | `37:각 source는 다음 문자열을 모두 갖습니다: … accessed_at …` · `42:- published_at, accessed_at: ISO 날짜 또는 …` · `53: "accessed_at":"실제 읽은 날짜" …`; `117: for key in ("id", "title", "publisher", "published_at", "period", "accessed_at", "read_scope", "findings"):` |
| P12 | httpx `MockTransport`는 시간 상한을 적용하지 않고, DART 모듈은 바깥 `asyncio.wait_for`로 상한을 보장한다 (spec REQ-005, plan T4, acceptance §A·AC-005) | `PY -I -c "import httpx,inspect; print(httpx.__version__); src=inspect.getsource(httpx.MockTransport.handle_async_request); print(src); print('timeout' in src)"`; `grep -n "asyncio.wait_for" backend/services/goose_dart_prefetch.py` | `0.28.1`, 메서드 본문은 `await request.aread()` → `response = self.handler(request)` → 필요하면 `await response` → `return response`, `False`; `376:        return await asyncio.wait_for(self._send(method, url, form, timeout), timeout)` |
| P13 | AC-011 #4 규칙 번호 검사(v0.3.0 블록, 본문 `N-M` 참조 검사 추가)가 현재 트리와 plan 초안에서 통과하고, 중복 번호·남은 옛 하위 라벨·본문에 남은 옛 참조를 잡는다 (AC-011 #4, plan §5 단계 1) | v0.3.0 `acceptance.md`에서 `# AC-AIR7-011`로 시작하는 코드 블록을 정규식으로 **그대로 추출**해 `python3 -I -c` 안에서 `exec`, `open`을 메모리 안 텍스트로 바꿔 실행. 입력: 실제 지침, 실제 지침 + plan.md §4 초안(`N`을 9로), 감수 규칙 9 + 초안(`N`을 10으로), 그 변형 3종 | `real file => rules [1, 2, 3, 4, 5, 6, 7, 8] \| rule numbering ok` · `M4: real + plan draft as rule 9 => rules [1, …, 9] \| rule numbering ok` · `merge: review 9 + plan draft as 10 => rules [1, …, 10] \| rule numbering ok` · `merge: plan draft left as 9 (dup) => … \| top-level numbers not 1..K unique: [1, 2, 3, 4, 5, 6, 7, 8, 9, 9]` · `merge: draft top 10 but labels 9-* => … \| line 29: sub-item 9-* under rule 10` (29~34행 6줄) · `merge: draft as 10, prose ref left 9-2 => … \| line 31: in-text reference 9-2 inside rule 10`. 초안이 9·10 어느 번호로도 통과하므로 초안에는 다른 규칙을 가리키는 `N-M` 참조가 없다. 별도 확인(같은 판정 로직, 합성 줄): 날짜 같은 `2026-10-21`은 오탐하지 않음(`rule numbering ok`). ~~v0.2.0 P13의 3종 관측~~ — 대체: 블록이 바뀌어 다시 쟀다 |
| P14 | **v0.4.0 재측정**: 블록(50줄, `SUMMARY` 문구를 3S에서만 요구)을 문서에서 그대로 추출해 20종 실행 → `cases 20 all match: True`. 새 경우: `[run] limitations lacks summary phrase → violations 1 \| mode 3F+3S \| nv1: limitations lacks summary phrase`, `[other] failed + fallback WebFetch read (no summary phrase) → violations 0 \| mode 3F only (outcome=failed)`, `[other] no_results + fallback read outside index → violations 0 \| mode 3F only (outcome=no_results)`. 나머지 17종은 아래 v0.3.0 결과와 같은 판정(통과 입력은 두 문구를 모두 넣은 것으로 교체). 아래는 v0.3.0 기록 — AC-012 검사 3(v0.3.0 블록, 3F/3S 분리)이 성공 회차의 변형은 모두 잡고, 다른 회차의 REQ-010 허용 기록은 통과시키며, 다른 회차의 지어낸 기록은 잡는다 (AC-012, REQ-013) | v0.3.0 `acceptance.md`에서 `# AC-AIR7-012`로 시작하는 코드 블록(47줄)을 **그대로 추출**해 `exec`, `open`·`os.path.exists`를 메모리 안 JSON으로 바꿔 18종 실행(2회차 감사 P-C의 경우 전부 포함 + 지어낸 기록 2종 + 색인 없음 1종) | 18종 모두 기대와 일치. 성공 회차(`partial`): `good partial → violations 0 \| mode 3F+3S`; `no_results instead of read → violations 2`(`naver no_results while index outcome=partial`, `no naver read entry`); `url = metadata_only article_url`·`url outside index → violations 1`(`nv1: url is not an ok index article_url`); `read_scope lacks text_file`·`limitations missing → violations 1`(`nv1: read_scope/limitations mismatch`); `read + extra no_results → violations 2`; `read + extra blocked → violations 1`(`naver entries=2 (the read entry must be the only naver entry)`); `empty source_ids`·`missing source_ids key → violations 1`(`naver read entry has no source_ids`); `int source id → violations 1`(`7: source id not in sources`, 역추적 없음). 다른 회차: `failed + honest blocked`, `failed + fallback WebFetch read`, `no_results + goose no_results`, `disabled + blocked`, `index missing + blocked` → 모두 `violations 0 \| mode 3F only (outcome=…)`; `failed + fabricated no_results → violations 1`; `failed(all metadata) + read of metadata_only article → violations 1`. ~~v0.2.0 P14의 4종 관측~~ — 대체: 블록이 바뀌어 다시 쟀다 |
| P16 | 선언 길이 검사는 본문을 읽기 전에 거부하므로 "본문 조각 읽힘 수 == 0" 단언이 그 검사만 지운 변형을 잡는다 (spec REQ-005, AC-005 (ii-a)) | venv `python -I -c`로 httpx `MockTransport` + 읽힌 조각 수를 세는 `httpx.AsyncByteStream`(`content-length: 2097153` 선언) 위에 두 검사를 가진 최소 대역 수집 함수를 만들어 검사 조합 4가지 실행 | `httpx 0.28.1` · `both checks -> failed: too large (declared) body_chunks_read=0 … PASS` · `declared removed -> failed: too large (stream) body_chunks_read=2 … RED` · `stream removed -> failed: too large (declared) body_chunks_read=0 … PASS` · `both removed -> ok 3145731 bytes body_chunks_read=3 … RED`. 대역 함수라 실제 모듈의 거동은 run 단계에서 다시 관측한다 |
| P15 | `phase` 값을 고정하는 버전 원천이 없다 (spec 관계 문단, Q1) | `grep -H "^phase:"` 004·005·TEST-HERMETIC-001·RS-REBALANCE-001 spec.md; `grep -n '^version' pyproject.toml`; `git -C <worktree> tag --list` | 004 `"v0.5.3 target"`, 005 `"v0.5.4 target"`, TEST-HERMETIC-001 `"v0.6.0 target"`, RS-REBALANCE-001 `"v0.6.0 target"`; `7:version = "0.1.0"`; 태그는 `moai/SPEC-AI-REPORT-003/sync-complete`, `moai/SPEC-MINERVINI-001/sync-complete`, `moai/SPEC-RS-LINE-001/sync-complete`, `moai/SPEC-WEB-001/sync-complete`뿐(버전 태그 없음) |
| P17 | 응답은 그룹 배열이고 기사 목록은 펼친 `items`, 그룹 `total`은 기사 수가 아니다. 엔티티는 본문뿐 아니라 제목에도 있다 (spec §2.6, REQ-006·007, AC-006·007) | `python3 -I -c`로 녹화 3개 파일을 `json.load` → 최상위 타입·그룹 수·펼친 길이·`sum(total)`·그룹별 `len(items)`, 기사마다 `title`·`body`·`officeName`에서 `&[a-zA-Z#0-9]+;` 탐색, `html.unescape(태그 제거)` 결과 | `020150_p1.json top list groups 10` · `flattened 10 sum(total) 22 items/group [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]` · `entity group 1 item 0 field body ents ['&quot;']` · `entity group 4 item 0 field title ents ['&quot;']` · `body len min/max 129 154 endswith ...: 10 / 10`; `000040_p1.json … flattened 10 sum(total) 10` · `entity group 3 item 0 field body ents ['&quot;']` · `body len min/max 131 154 endswith ...: 10 / 10`; `999999_p1.json top list groups 0 flattened 0`. 해제 뒤 세 필드 모두 `&quot;` 없음·`"` 있음. 제목 엔티티는 M1 관측표(O3, 본문만 셈)에 없던 사실이다 |
| P18 | 운영 경로는 라우터가 서버 종목 목록 조회로 코드를 걸러 `start()`를 부르며, 그 조회는 네트워크 없이 고정 엑셀 표를 본다. 작업 서비스가 같은 조회를 가져와도 순환 가져오기가 없다 (spec §2.7·D9, plan T9, REQ-015) | `grep -rn "\.start(" backend \| grep -v /tests/`; `grep -n` 라우터 63·70~75·147행 읽기; `ai_report_service.py` 88~100행 Read; `registry.py` 1~160행 Read; `grep -n "^from\|^import" backend/services/ai_report_service.py`; `grep -c goose_job_service backend/services/ai_report_service.py`; `grep -n "상장\|폐지\|delist\|listing" my_chart/registry.py`; venv로 `get_stock_name` 3건 호출; `git ls-files --error-unmatch Input/sectormap-original.xlsx` | `start(` 운영 호출은 `backend/routers/ai_report.py:147: outcome = await get_goose_service().start(code, stock_name)` 하나(나머지 일치는 주석·다른 `.start()`). 라우터 63행 6자리 검사 → 422, 70~75행 `get_stock_name(code)`가 `None`이면 404. `get_stock_name`은 `my_chart.registry._name`을 불러 `"NonName"`이면 `None`. `_name`은 `get_stock_registry()`(`sectormap-original.xlsx`를 `pd.read_excel`로 한 번 읽어 둔 표)에서 `Code == x`를 찾는다. `ai_report_service` 가져오기는 표준 라이브러리 + `from my_chart.registry import _name`뿐, `goose_job_service` 언급 `0`. 상장·폐지 관련 단어 0건. `SECTORMAP_PATH … exists True` · `020150 '롯데에너지머티리얼즈'` · `000040 'KR모터스'` · `999999 None`. 엑셀 파일은 git 추적 중(`Input/sectormap-original.xlsx`) |
| P19 | AC-006·007의 V1·V3·V5 되돌림이 실제 녹화 데이터에서 RED가 된다 (AC-006 되돌림 검사, AC-007 추가 되돌림) | `python3 -I -c`로 최소 대역 해석 함수(펼침 / 첫 그룹만, 해제 / 해제 없음 / 해제 먼저)를 녹화 2개 파일과 메모리 안 문자열에 실행 | 020150: `impl flatten count: 10 \| REVERT first_group count: 1 \| REVERT sum(total): 22 \| expected (flattened len): 10`, 런타임 선택 `[(1, 'body'), (4, 'title')]`, 둘 다 `impl text has &quot;: False \| REVERT no-decode text has &quot;: True`, `article_url == mobileNewsUrl: impl 10 / 10 \| REVERT int(officeId): 0 / 10`. 000040: `REVERT first_group count: 1`, `REVERT sum(total): 10`(= 펼친 길이 — `total` 되돌림은 020150에서만 잡힌다, AC-006이 그렇게 적음), 선택 `[(3, 'body')]` 같은 판정, `REVERT int(officeId): 1 / 10`. 순서: `impl tags->decode "a'b'c & <b>리터럴</b> 태그" literal <b>리터럴</b>: True` · `REVERT decode->tags "a'b'c & 리터럴 태그" literal <b>리터럴</b>: False` · `REVERT no decode … &#39; left: True`. 대역 함수라 실제 모듈은 run 단계 M2에서 다시 관측한다 |

미관측(이 표에 없는 것): ~~네이버 모바일 API 응답의 정확한 구조와 `article_url` 형태(spec G4·G5)~~ — run 단계 M1에서 관측 완료(§E.2 O1~O7, P17). 남은 미관측은 실제 태그가 든 `body`, 그룹당 기사 2건 이상, 실제 상장 종목의 0건 응답, 호출 제한(spec §8). plan 단계 작성자는 네트워크 요청을 보내지 않았다. 엔드포인트 관측표(spec §2.3)는 리드와 `.moai/reports/t19/investigation.md`의 기록이며 이 문서 작성자가 다시 재지 않았다. P13·P14는 문서의 블록을 합성 입력에 돌린 것이며, 실제 병합 트리와 실제 라이브 입력에는 아직 돌리지 않았다. P16은 최소 대역 함수 관측이다. 응답 헤더 뒤 본문이 멈추는 경우의 시간 상한은 테스트하지 않는다(2회차 감사 (d) — REQ-005가 본문 읽기까지 상한에 넣으므로 run 단계 선택 관측).

## §E.2 Run-phase Evidence

### M1 — 픽스처와 데이터 모양 관측 (2026-10-21, 카드 t19)

실행 위치: 에이전트 격리 워크트리 `agent-a8a4aa39c4b1cb9d1`(기준 HEAD `794b9f7`). `PY` = `/Users/byunjungwon/Dev/my_chart/.venv/bin/python`. 외부 요청은 상한(`m.stock.naver.com` 3건 + `n.news.naver.com` 1건) 안에서 모두 4건: `m.stock.naver.com` 3건(020150, 000040, 999999), `n.news.naver.com` 1건. 요청 헤더는 User-Agent만 보냈다.

#### 요청 기록

| # | 명령 | 관측 원문 | 결론 |
|---|---|---|---|
| R1·R2 | `PY -I backend/tests/fixtures/naver/capture_naver.py backend/tests/fixtures/naver/recorded 020150 000040` | `200 application/json;charset=UTF-8 8094 https://m.stock.naver.com/api/news/stock/020150?pageSize=10&page=1` / `200 application/json;charset=UTF-8 8192 https://m.stock.naver.com/api/news/stock/000040?pageSize=10&page=1` | 두 종목 모두 200 JSON. 받은 시각 `2026-10-21T17:59:55.533+09:00`, `17:59:56.725+09:00` (`recorded/request_log.json`). 000040은 기사가 적을 것으로 보고 골랐으나 기사 10건이 왔다 — "기사가 적은 종목" 관측은 얻지 못했다 |
| R3 | `PY -I backend/tests/fixtures/naver/capture_naver.py backend/tests/fixtures/naver/recorded 999999` 뒤 `od -c recorded/999999_p1.json` | `200 application/json;charset=UTF-8 2 https://m.stock.naver.com/api/news/stock/999999?pageSize=10&page=1` / `0000000    [   ]` | 존재하지 않는 종목코드도 HTTP 200 + 본문 `[]`(2바이트). 받은 시각 `18:00:44.936+09:00` |
| R4 | `curl -sS -L -o /dev/null -A "<Chrome UA>" -w 'status=%{http_code} redirects=%{num_redirects} final_url=%{url_effective} content_type=%{content_type} size_download=%{size_download}\n' https://n.news.naver.com/mnews/article/015/0005344879` | `status=200 redirects=0 final_url=https://n.news.naver.com/mnews/article/015/0005344879 content_type=text/html; charset=utf-8 size_download=300749` (요청 직후 `date` → `2026-10-21T18:00:30+0900`) | 020150 첫 기사(`officeId 015`, `articleId 0005344879`)로 만든 주소가 리디렉트 없이 200 HTML. 페이지 본문은 저장하지 않았고 내용도 검사하지 않았다(아래 Gap) |

녹화 파일 해시(`shasum -a 256`): `020150_p1.json` `e6f86f39ef11f9fc4db40a04e629939203ec04f0c4866bfee77b9f7207bad7cf`, `000040_p1.json` `907cbc191d271523eb74b96783ab5b4f2cd5f82cb53732e2a13431d30c0ac72a`, `999999_p1.json` `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.

#### 관측 (G4·G5)

| # | 명령 | 관측 원문 (발췌) | 결론 |
|---|---|---|---|
| O1 (G4 경로) | `PY -I -c` — `json.load` 후 최상위 타입·길이, 그룹별 키·`total`·`len(items)` 출력 | 020150: `top type list len 10`, 그룹마다 `keys ['total', 'items']`, `items/group [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`, `totals [4, 1, 10, 1, 1, 1, 1, 1, 1, 1]`. 000040: `groups 10`, `items/group` 전부 1, `totals` 전부 1 | 최상위는 **그룹 배열**(pageSize=10 → 그룹 10개). 그룹 = `{total, items}`, 관측한 20개 그룹 모두 `items` 1건. 기사 목록 경로는 `[*].items[*]`(그룹을 펼친 목록)이다. `[0].items`만 읽으면 기사 1건만 나온다. 그룹의 `total`은 관련 기사 묶음 크기로 보이며(020150 합계 22 ≠ 기사 10) 기사 수가 아니다 |
| O2 (키) | 같은 스크립트로 기사 키 정렬 출력, 첫 기사 3건의 `{키: (타입, 값)}` | 키: `articleId, body, datetime, id, imageOriginLink, mobileNewsUrl, officeId, officeName, photoType, title, titleFull, type` (`imageOriginLink`는 일부 기사에 없음). 타입: `id`·`officeId`·`articleId`·`officeName`·`datetime`·`title`·`titleFull`·`mobileNewsUrl` 문자열, `type`·`photoType` 정수. 예: `'officeId': ('str', '015')`, `'articleId': ('str', '0005344879')`, `'mobileNewsUrl': ('str', 'https://n.news.naver.com/mnews/article/015/0005344879')` | spec이 적은 키 7개는 모두 있다. 추가 키 5개(`titleFull`, `mobileNewsUrl`, `imageOriginLink`, `photoType`, `type`). `officeId`는 앞자리 0이 있는 문자열이라 정수로 바꾸면 주소가 깨진다. `title != titleFull` 0건(두 파일) |
| O3 (body) | 기사별 `len(body)`, 태그 정규식 `<[a-zA-Z/][^>]*>`, 엔티티 정규식 `&[a-zA-Z#0-9]+;`, 개행 여부, `body.endswith('... ')`, 첫 기사 3건 `repr(body)` | 020150 `n 10 min 129 median 147.5 max 154`, 000040 `n 10 min 131 median 137.5 max 154`. 태그 `False` 20/20, 개행 `False` 20/20, 엔티티 `True` 2/20 — 종류는 두 파일 모두 `['&quot;']`. `body endswith "... ": 10 / 10`(두 파일). 예: `"삼성자산운용은 … 삼성운용 측은 개인투자자의... "` | `body`는 기사 전문이 아니라 **129~154자에서 잘린 요약 조각**(20건 모두 `... `로 끝남). HTML 태그는 없고 HTML 엔티티(`&quot;`)가 들어 있다 |
| O4 (datetime) | `re.fullmatch(r'[0-9]{12}', datetime)` 개수 | `datetime 12 digits: 10`(두 파일 각각) | 20/20이 `YYYYMMDDHHMM` 12자리. 값에 시간대 표시는 없다 |
| O5 (식별자) | `re.fullmatch(r'[0-9]{1,12}', …)` 개수, `id == officeId+articleId` 개수 | `officeId/articleId match ^[0-9]{1,12}$: 10`, `id == officeId+articleId: 10`(두 파일 각각) | REQ-AIR7-006 정규식에 녹화 기사 20건이 모두 맞는다 |
| O6 (G5 주소) | `mobileNewsUrl == 'https://n.news.naver.com/mnews/article/%s/%s' % (officeId, articleId)` 개수 + R4 | `10 / 10`(두 파일 각각), R4 `status=200 redirects=0` | 응답의 `mobileNewsUrl`이 spec의 `article_url` 형태와 20/20 일치하고, 그 형태의 주소 1건이 200으로 열린다 |
| O7 (0건) | R3 | 본문 `[]` | 0건 응답의 실제 모양은 빈 최상위 배열. 존재하지 않는 종목코드와 "기사 0건 종목"을 응답만으로는 구별할 수 없다(실제 상장 종목의 0건 응답은 관측하지 못함) |

#### SPEC 가정과의 차이 (manager-spec 재위임 대상 — 이 레인은 spec·plan·acceptance를 고치지 않음)

| # | 위치 | SPEC 가정 | 관측 | 영향 |
|---|---|---|---|---|
| V1 | spec.md:78, spec.md:145, spec.md:153, acceptance.md:109·122·307 | 응답에 `items[]` 목록 하나(78행 "`items[]`에 …"), 145행 "the response path fixed in run-phase M1", AC가 "픽스처 기사 목록 길이"를 쓴다 | 최상위 그룹 배열, 그룹마다 `items` 1건(O1). 기사 목록 = 그룹들의 `items`를 펼친 것 | REQ-006의 경로를 `[*].items[*]`(펼침, 최대 10건)로 확정해야 한다. `item_count`·"기사 목록 길이"가 펼친 길이인지, 그룹의 `total`이 아님을 명시할 필요. 그룹당 기사 2건 이상은 관측되지 않았다 |
| V2 | spec.md:103(D3), spec.md:157(REQ-010 `read_scope` 문구), acceptance.md:116 | `body`가 전문인지 요약인지 미정(G4). 116행은 "잡지 못하는 것"으로 둠 | 20/20이 129~154자 요약 조각, `... `로 끝남(O3) | `read_scope` 문구 "모바일 뉴스 API 응답의 제목·본문 필드"는 사실과 어긋나지 않지만, 읽은 것이 기사 요약 조각(약 150자)이라는 점을 드러내지 않는다. `direct_read`로 감사를 통과시키는 근거가 150자 조각이라는 점을 리드·manager-spec이 받아들일지 결정해야 한다(D3의 `limitations` 문구 보강 후보: "요약 조각") |
| V3 | spec.md:145 (REQ-006 "plain text with markup removed"), acceptance.md:106·111 | 마크업(태그)이 있을 수 있음 — 합성 `<b>강조</b>`로 검사 | 실제 응답에 태그 0건, HTML 엔티티 `&quot;` 2건(O3) | 평문 변환에 HTML 엔티티 해제가 필요하다는 점이 REQ에 명시돼 있지 않다. 태그 제거만 구현하면 `&quot;`가 텍스트 파일에 남는다. AC-006에 엔티티 해제 단언을 더할지 결정 필요 |
| V4 | spec.md:153 (REQ-009), plan.md:67(N-3 초안) | 정상 응답 + 기사 0건 → `no_results`, goose는 그때만 `no_results` | 없는 종목코드 `999999`도 200 `[]`(O7) | 6자리 숫자 형식만 맞으면 존재하지 않는 종목도 `no_results`가 되고, 하네스 규칙이 goose에게 `no_results` 기록을 허용한다. 실제 운영 호출은 상장 종목이라 위험은 낮지만, 응답만으로 구별할 수 없다는 점을 문서에 적을지 결정 필요 |
| V5 | spec.md:78 | 키 7개 나열 | 추가 키 5개, 특히 `mobileNewsUrl`(O2·O6) | 모순은 아니다. `article_url`을 검증된 숫자 식별자로 서버가 만드는 현재 방식은 그대로 유효(응답 문자열을 주소에 쓰지 않음). `mobileNewsUrl`을 쓰지 않는다는 점, 또는 일치 검사에 쓸지를 정할 수 있다 |

차이 없음으로 확인한 것: `article_url` 형태(O6, R4), `officeId`·`articleId` 정규식(O5), `datetime` 12자리 형식(O4), 키 이름 `officeId`·`articleId`·`officeName`·`datetime`·`title`·`body`(O2), 응답 크기(8 KB대, 2 MB 상한과 무관), content-type `application/json;charset=UTF-8`.

#### 픽스처

- 녹화 `backend/tests/fixtures/naver/recorded/`: `020150_p1.json`(8,094 B), `000040_p1.json`(8,192 B), `999999_p1.json`(2 B), `request_log.json`(1,302 B). 생성 스크립트 `capture_naver.py`.
- 합성 `backend/tests/fixtures/naver/synthetic/`(생성 `build_synthetic.py`, 2회 실행 후 `shasum` 비교로 같은 바이트 확인: `deterministic-ok`): `zero_articles.json`, `empty_body.json`, `bad_article_id.json`, `bad_datetime.json`, `markup_body.json`, `parse_cases.json`(AC-006 (2) 4건 묶음), `mixed_status.json`(AC-014), `all_metadata_only.json`(AC-014), `missing_items_path.json`(AC-008 경로 없음 — 처음 이름 `no_items_key.json`이 `.gitignore` 139행 `*_key.*`에 걸려 바꿈), `not_json.txt`(AC-008, `json.loads` → `JSONDecodeError Unterminated string starting at: line 1 column 44 (char 43)`). 모양 점검: 모든 합성 기사의 키 집합이 녹화본 키의 부분집합(`keys_same_as_recorded True`). 설명은 `fixtures/naver/README.md`.

#### Gap (M1에서 관측하지 않은 것)

- R4의 페이지가 그 기사인지(제목 일치)는 검사하지 않았다 — 본문을 저장하지 않는 지시에 따라 상태·최종 주소·크기만 봤다.
- `datetime`이 KST라는 점: 값에 시간대가 없다. 가장 최근 기사 `202610211352`가 받은 시각 `17:59 +09:00`보다 앞선다는 것은 KST 해석과 모순되지 않을 뿐 증명은 아니다.
- 그룹 하나에 기사가 2건 이상 오는 경우, 실제 상장 종목의 기사 0건 응답, 실제 마크업 태그가 든 `body` — 모두 관측하지 못했다.
- 호출 제한·약관(spec G3)은 여전히 미관측.

### M2 — 수집 모듈 `goose_naver_prefetch.py` (2026-10-21, 카드 t19)

실행 위치: 에이전트 격리 워크트리 `agent-a3f9bb90dca738a53`(기준 HEAD `1c49411`). `PY` = `/Users/byunjungwon/Dev/my_chart/.venv/bin/python`. 증거 폴더 `$S` = `.moai/state/verify/t19-run/`. 외부 네트워크 요청 0건(모든 요청은 `httpx.MockTransport`).

- 기준선(AC-013, M2 착수 전, 새 파일 제외): `PY -m pytest backend/tests/test_goose_dart_prefetch.py backend/tests/test_goose_job_service.py backend/tests/test_goose_router.py backend/tests/test_goose_storage.py backend/tests/test_goose_runner.py backend/tests/test_goose_harness.py backend/tests/test_main_goose_lifespan.py -q -p no:cacheprovider` → `267 passed, 1 warning in 17.17s` (`$S/baseline_goose.txt`)
- 합성 픽스처 5종 추가(`build_synthetic.py`): `top_level_object.json`, `mixed_malformed_groups.json`, `two_items_group.json`, `entity_body.json`, `all_empty_items.json`(감사 부채 D-B). 결정성: 생성 → `shasum -a 256 synthetic/*` → 재생성 → `shasum` → `cmp` → `deterministic-ok`. 기존 합성 10종은 바이트 변화 없음(`git status --short`에 수정 표시 없음)
- RED(모듈 작성 전): `PY -m pytest backend/tests/test_goose_naver_prefetch.py -q` → `E   ImportError: cannot import name 'goose_naver_prefetch' from 'backend.services'` / `1 warning, 1 error in 0.68s`
- GREEN: 같은 명령 → `41 passed, 1 warning in 0.51s` (`$S/m2_naver_tests.txt`)
- 커버리지(§E): `PY -m coverage run --source=backend -m pytest backend/tests/test_goose_naver_prefetch.py` → `coverage report --include='backend/services/goose_naver_prefetch.py' -m` → `goose_naver_prefetch.py  201  7  97%  82, 99-100, 165, 173, 175, 221`
- ruff: 설치되어 있지 않음(`No module named ruff`, `which ruff` → `ruff not found`) — §E 린트 게이트는 미관측(Gap)

#### 되돌림 관측 (lessons #9 — 변형 적용 → 실행 → RED 원문 → 복원)

변형은 Edit로 소스에 넣고 같은 Edit로 되돌렸다. 복원 확인: 모든 되돌림 뒤 `shasum -a 256 backend/services/goose_naver_prefetch.py` → `36ed1628f0aac7a60ef4f4a36b97892ab75cb3eb34d74a1b8404fb854cccaada`(변형 전 백업과 같음), 이어서 전체 41 passed. 명령은 모두 `PY -m pytest backend/tests/test_goose_naver_prefetch.py -q -k <선택>`.

| # | AC | 변형 | `-k` | RED 원문 (발췌) | 복원 뒤 |
|---|---|---|---|---|---|
| R1 | 005 입력 검증 | 종목코드 검사를 `if False:` | `air7_005_invalid` | `E       AssertionError: assert [<Request('GE...=10&page=1')>] == []` · `Left contains one more item: <Request('GET', 'https://m.stock.naver.com/api/news/stock/02015a?pageSize=10&page=1')>` · `3 failed, 38 deselected` | 41 passed |
| R2 | 005 리디렉트 | `client.send(..., follow_redirects=True)` | `air7_005_redirect` | `E       AssertionError: assert 2 == 1` · `where 2 = len([<Request('GET', 'https://m.stock.naver.com/...')>, <Request('GET', 'https://evil.example.com/x')>])` (두 번째 요청은 MockTransport가 기록 — 실제 연결 없음) | 41 passed |
| R3 | 005 선언 길이 | 선언 길이 검사만 끔 | `air7_005_declared or air7_005_streamed` | `E       assert 3 == 0` · `where 3 = <..._CountingStream ...>.read` (outcome은 스트리밍 검사로 여전히 failed — 조각 수 단언만 RED) · `1 failed, 1 passed` | 41 passed |
| R4 | 005 스트리밍 누적 | 누적 검사만 끔 | 같음 | `E       AssertionError: assert 'too large' in 'JSONDecodeError: Expecting value: line 1 column 1 (char 0)'` · `1 failed, 1 passed` — 주의: acceptance가 적은 `outcome != "failed"`가 아니다. 본문 `xxx…`가 JSON 해석에서 실패해 outcome은 `failed`로 남고, `too large` 문구 단언이 RED를 낸다 | 41 passed |
| R5 | 005 둘 다 | 두 검사 모두 끔 | 같음 | 두 테스트 모두 `E       AssertionError: assert 'too large' in 'JSONDecodeError: Expecting value: line 1 column 1 (char 0)'` · `2 failed` | 41 passed |
| R6 | 005 시간 | `asyncio.wait_for` 제거, `await _send(...)`만 | `air7_005_hanging` | `E                   TimeoutError` (바깥 2초 상한, `asyncio/timeouts.py:116`) · `1 failed ... in 2.45s` | 41 passed |
| R7 | 006 경로(V1) | `enumerate(data[:1], 1)`(첫 그룹만) | `air7_006_recorded_flattened` | `E       assert 1 == 10` · `where 1 = len([{'article_id': '0005344879', ...}])` (020150), `where 1 = len([{'article_id': '0003691095', ...}])` (000040) | 41 passed |
| R8 | 007 `item_count`(V1) | `item_count`를 그룹 `total` 합으로 | `air7_007` | `E       assert 22 == 10` (020150) · `1 failed, 1 passed` (000040은 `total` 합 = 10이라 GREEN — P19와 같음) | 41 passed |
| R9 | 006 모양 오류(V1) | 그룹 검사 없이 `group["items"]` 바로 순회 | `air7_006_malformed or e_mixed_malformed` | `E       AssertionError: assert [] == ['015/0005344...1/0003690339']` · `Right contains 2 more items` (예외가 최상위 처리로 가서 articles 비고 failed), AC-014 (e) `E       AssertionError: assert 'failed' == 'partial'` | 41 passed |
| R10 | 006 엔티티 해제(V3) | `html.unescape` 제거 | `air7_006_recorded_entities or air7_006_tags_removed` | 런타임 선택 기사 `E               AssertionError: (1, 'body', '&quot;')` · `assert '&quot;' not in '제목: 오늘의 프리미...` (020150), `(3, 'body', '&quot;')` (000040); 순서 테스트 `E       assert "a'b'c & <b>리터럴</b> 태그" in "...a&#39;b&#x27;c &amp; &lt;b&gt;리터럴&lt;/b&gt; 태그\n"` | 41 passed |
| R11 | 006 순서(V3) | 해제 먼저, 태그 제거 나중 | `air7_006_tags_removed` | `E       assert "a'b'c & <b>리터럴</b> 태그" in "...본문(...):\na'b'c & 리터럴 태그\n"` | 41 passed |
| R12 | 006 태그 제거 | 태그 제거 단계 삭제 | `air7_006_parse_cases or air7_006_tags_removed` | `E       AssertionError: assert ('강조' in '...' and '<b>' not in '...')` · `'<b>' is contained here: <b>강조</b> 19일 오후 3시 30분 기준` | 41 passed |
| R13 | 006 `metadata_only` | 빈 본문도 `ok` | `air7_006_parse_cases or air7_014` | `E       AssertionError: assert ('ok' == 'metadata_only'` · AC-014 (b) `E       AssertionError: assert 'complete' == 'failed'` | 41 passed |
| R14 | 006 `+09:00` | `datetime`에 시간대 없음 | `air7_006_parse_cases or air7_007` | `E       AssertionError: assert '2026-10-21T13:52:00' == '2026-10-21T13:52:00+09:00'` | 41 passed |
| R15 | 007 V5 교차 확인 | `article_url`에 `int(officeId)` | `air7_007` | `E           AssertionError: assert 'https://n.ne...15/0005344879' == 'https://n.ne...15/0005344879'` · `- .../article/015/0005344879` / `+ .../article/15/0005344879` (두 녹화 파일 모두 RED) | 41 passed |
| R16 | 007 키 집합 | 항목에서 `article_url` 키 제거 | `air7_007` | `E        +  where False = all(<generator object test_air7_007_index_keys_raw_response_and_urls.<locals>.<genexpr> ...>)` (두 파일) | 41 passed |
| R17 | 008 최상위 배열(V1, 감사 부채 D-A) | 최상위 배열 검사를 끔 | `air7_008` | `E       AssertionError: assert 'top-level JSON value is not an array' in '_ParseError: no group has an items array'` · `FAILED ...::test_air7_008_top_level_object_reports_top_level_error` · `1 failed, 11 passed` — D-A 확인: 일반 실패 테스트 `[top_level_object]`는 형제 검사 때문에 GREEN이고, 최상위 전용 오류 문구 단언만 RED | 41 passed |
| R18 | 008 `items` 배열 전무 | 그 판정을 끔 | `air7_008` | `E       TypeError: argument of type 'NoneType' is not iterable` (`search.error`가 None) · `FAILED ...[missing_items_path]` · `FAILED ...::test_air7_008_no_group_with_items_array_is_failed_with_error` · `2 failed, 10 passed` | 41 passed |
| R19 | 008 최상위 예외 처리 | `except Exception` → `except ZeroDivisionError` | `air7_008` | `E       RuntimeError: parser exploded` · `FAILED ...::test_air7_008_unexpected_exception_is_recorded_as_failed` (수집기 직접 실행 경로) | 41 passed |
| R20 | 008 0건 | 0건을 `failed`로 | `air7_008_zero` | `E       AssertionError: assert 'failed' == 'no_results'` (3개 변형 모두) | 41 passed |
| R21 | 014 | `all ok` 대신 `not any error`로 complete | `air7_014` | (b) `E       AssertionError: assert 'complete' == 'failed'` | 41 passed |
| R22 | 014 | `ok`가 하나라도 있으면 complete | `air7_014` | `FAILED ...test_air7_014_outcome[a_mixed_status]` · `[d_parse_cases]` · `[e_mixed_malformed]` | 41 passed |
| R23 | 014 | 모양 오류 항목을 판정에서 뺌 | `air7_014` | `E       AssertionError: assert 'complete' == 'partial'` · `FAILED ...[e_mixed_malformed]` | 41 passed |
| R24 | 013 가드 | 테스트 도우미 `run()`의 `transport`를 `None`으로 | `air7_005_valid_code` | 선행: `PY -m pytest backend/tests/test_goose_dart_prefetch.py -k air5_014_guard -q` → `1 passed`. RED: `ERROR at teardown of test_air7_005_valid_code_sends_exactly_one_get` · `E       AssertionError: network attempt in goose test: [(b'm.stock.naver.com', 443)]` (가드는 원래 함수를 부르지 않음 — 실제 연결 없음) | 41 passed |

#### M2 Gap

- AC-005 R4의 RED는 acceptance가 예상한 단언(`outcome != "failed"`)이 아니라 `too large` 문구 단언에서 나왔다. 테스트 본문이 `x` 바이트라 JSON 해석이 따로 실패하기 때문이다. 결과적으로 변형은 잡히지만, outcome만 보는 검사였다면 잡지 못했다.
- AC-002 수집기 부분(취소 전파)은 테스트가 통과하지만 "수집기가 CancelledError를 잡아 failed로 기록" 되돌림은 M3에서 작업 서비스 경로로 관측한다(AC-002 (2)).
- ruff 미설치로 린트 게이트 미관측.
- 실제 태그가 든 `body`, 그룹당 기사 2건, 실제 상장 종목 0건은 여전히 합성으로만 검사(spec G4).

### M3 — 작업 서비스 연결 (2026-10-21, 카드 t19)

변경: `goose_job_service.py` — 생성자 인자 `naver_prefetcher`·`code_check`(기본값 둘 다 `None`), `_run`에서 DART 수집 뒤·무결성 재검사 앞에 `_prefetch_naver`, 재검사 조건을 "수집기가 하나라도 주입"으로(T7), 끄기 스위치 `AI_REPORT_GOOSE_NAVER_PREFETCH`, 진행 이벤트 없음, `_code_validated`(확인 함수를 `asyncio.to_thread`로 호출, 없거나 예외면 `False`), 운영 인스턴스에 `NaverPrefetcher()`와 `_server_code_check`(지연 가져오기한 `ai_report_service.get_stock_name(code) is not None`).

- RED(연결 전): `PY -m pytest backend/tests/test_goose_job_service.py -q -k air7` → `21 failed, 1 passed, 49 deselected in 0.45s`. 원인 분포: `AttributeError: module 'backend.services.goose_job_service' has no attribute 'goose_naver_prefetch'` 13 · `TypeError: GooseJobService.__init__() got an unexpected keyword argument 'naver_prefetcher'` 6 · `'GooseJobService' object has no attribute '_naver_prefetcher'` 1 · `... '_code_check'` 1 (통과 1건은 수집기 없는 구성 (c))
- GREEN: `PY -m pytest backend/tests/test_goose_job_service.py backend/tests/test_goose_naver_prefetch.py -q` → `112 passed, 1 warning in 2.19s` (`$S/m3_tests.txt`; job_service 71 = 기존 49 + 새 22)
- AC-015 (f) 운영 확인 함수: `test_air7_015_production_code_check_uses_server_stock_list`가 `"020150"` → `True`, `"999999"` → `False`로 통과(네트워크 가드 종료 단언 통과 = 연결 시도 0)

#### 되돌림 관측

복원 확인: `shasum -a 256 backend/services/goose_job_service.py backend/services/goose_naver_prefetch.py` → `84cfe0a437e5bf5b2c3f0803beb1016d8d0a3fbed5487c148b77d23000dc1d96` / `36ed1628f0aac7a60ef4f4a36b97892ab75cb3eb34d74a1b8404fb854cccaada`(변형 전과 같음), 이어서 112 passed. 명령은 `PY -m pytest backend/tests/test_goose_job_service.py [backend/tests/test_goose_naver_prefetch.py] -q -k <선택>`.

| # | AC | 변형 | `-k` | RED 원문 (발췌) |
|---|---|---|---|---|
| M3-R1 | 001 | 네이버 수집 호출을 실행기 호출 뒤로 | `air7_001` | (a) `E       AssertionError: assert ['integrity',...ner', 'naver'] == ['integrity',...ty', 'runner']` · `At index 2 diff: 'integrity' != 'naver'`; (b) `At index 1 diff: 'integrity' != 'naver'` |
| M3-R2 | 001 | 재검사 조건을 DART 주입일 때만 | `air7_001` | (b) `E       AssertionError: assert ['integrity',...er', 'runner'] == ['integrity',...ty', 'runner']` · `At index 2 diff: 'runner' != 'integrity'`; 네이버만 주입 + 2차 무결성 실패 `E       AssertionError: assert ('done', None) == ('error', 'integrity')` |
| M3-R3 | 002 (1) | 작업 서비스 네이버 예외 처리를 `except BaseException` | `air7_002` | `E           AssertionError: cancel` · `assert ('done', None) == ('cancelled', None)` (가짜·실제 수집기 두 경우 모두 — 작업이 실행기까지 가서 done) |
| M3-R4 | 002 (2) | 수집기 `_collect`의 `except Exception` → `except BaseException`(CancelledError를 failed로 기록하고 정상 반환) | `air7_002` (두 파일) | 작업 서비스 경로 `E           AssertionError: cancel` · `assert ('done', None) == ('cancelled', None)`; 수집기 직접 `E       Failed: DID NOT RAISE <class 'asyncio.exceptions.CancelledError'>` · `2 failed, 1 passed` (가짜 수집기 경우는 수집기 코드를 거치지 않아 GREEN) |
| M3-R5 | 003 | 스위치 검사 줄을 `if False:` | `air7_003 or air7_015_disabled` | `E       AssertionError: assert ['https://m.s...ze=10&page=1'] == []` · `Left contains one more item: 'https://m.stock.naver.com/api/news/stock/020150?pageSize=10&page=1'`; `E       AssertionError: assert 'no_results' == 'disabled'` |
| M3-R6 | 004 | 네이버 수집 전에 `progress`/`naver_prefetch` 이벤트 | `air7_004` | `E       AssertionError: assert ['dart_prefet...'goose_start'] == ['dart_prefet...'goose_start']` · `At index 1 diff: 'naver_prefetch' != 'goose_start'` |
| M3-R7 | 008 | 작업 서비스 네이버 `except Exception` → `except ZeroDivisionError` | `air7_008` | `E       assert 0 == 1` · `where [] = <...FakeRunner ...>.calls` · `FAILED ...::test_air7_008_naver_prefetcher_exception_does_not_stop_goose` · `1 failed, 6 passed` (실제 수집기 6개 변형은 수집기 자체 fail-open이 막아 GREEN — acceptance AC-008 되돌림 설명과 같음) |
| M3-R8 | 013 | 생성자 기본값을 실제 `NaverPrefetcher()`로 | `air5_001_default or test_done_result_emits_done` | `ERROR at teardown of test_done_result_emits_done_and_clears_active` · `E       AssertionError: network attempt in goose test: [(b'm.stock.naver.com', 443)]` · `ERROR at teardown of test_air5_001_default_constructor_has_no_prefetch` (가드가 원래 함수를 부르지 않음 — 실제 연결 없음) |
| M3-R9 | 015 | 확인 결과 대신 `code_validated=True` | `air7_015` | (b)·(c)·(d) 각각 `E       assert True is False` |
| M3-R10 | 015 | 확인이 거짓이면 수집 건너뜀 | `air7_015` | (b)·(c)·(d) `E       FileNotFoundError: [Errno 2] No such file or directory: '.../runs/<job_id>/naver/index.json'` (수집기 호출 0 → 색인 없음) |
| M3-R11 | 015 | 확인 함수 예외를 그대로 올림 | `air7_015` | (d) `E       FileNotFoundError: ... naver/index.json` · `1 failed, 5 passed` (색인이 없다 = 수집기가 불리지 않았다. 작업 상태는 이 실패 줄보다 뒤의 단언이라 관측하지 않았다) |
| M3-R12 | 015 (f)·013 | 운영 인스턴스에 `code_check` 없음 | `air7_015_production or air7_013` | `E        +  where False = callable(None)` · `E           TypeError: 'NoneType' object is not callable` |

#### M3 Gap

- AC-002의 "서버 종료(lifespan) 중 실제 프로세스" 경로는 `svc.shutdown()` 호출로만 검사했다(실제 uvicorn 종료 미관측 — 기존 `test_main_goose_lifespan.py` 회귀로 대신).
- `_server_code_check`의 실제 운영 서버 호출(라우터 경유)은 관측하지 않았다 — 테스트 프로세스 안에서 같은 함수를 직접 불렀다.
- spec.md·plan.md·acceptance.md 프런트매터 `status`는 `draft` 그대로다. 에이전트 계약상 첫 run 커밋에서 `in-progress`로 바꾸는 전환이 있으나, 리드 지시("spec.md/plan.md/acceptance.md를 수정하지 말 것")가 우선이라 손대지 않았다 — 리드가 정할 사항.

### M4 — 하네스 규칙 9와 매니페스트 (2026-10-21, 카드 t19)

변경: `harness-instructions.md`에 규칙 9(하위 9-1~9-6)를 plan.md §4 초안대로 추가(N=9). 초안과 다른 점은 9-1에 "Read 도구로"와 예시 경로 `runs/<job_id>/naver/01_article.txt`를 더한 것뿐이다(규칙 8-1과 같은 형태). `goose-manifest.json`은 `PY -m backend.services.goose_harness > backend/goose_harness_src/goose-manifest.json`으로 재생성했다 — 차이는 `"CLAUDE.md"` 해시 한 줄(`a7a9a06e…` → `77e260e4c5a27e9f6166be2be19faec6332d421cdf0d82ba5fe3c1b6c6fb2fed`).

- AC-009 문자열 개수(`$S/air7_009.txt`, 명령은 acceptance의 한 줄 루프): `2 runs/<job_id>/naver/index.json` · `1 article_url` · `1 channel: "naver"` · `1 metadata_only` · `1 "no_results"` · `1 모바일 뉴스 API 응답의 제목·요약 본문 필드` · `1 서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음` · `1 API 요약본(약 150자), 원문 미확인` · `1 요약에 없는 사실은 단정하지 않는다` · `1 이번 세션에서 그 파일을 연 시각` · `1 original_news` · `1 code_validated` · `1 서버가 종목코드 유효성을 확인하지 못함` · `2 runs/<job_id>/dart/index.json` — 기준선 0(P6)에서 13개 모두 ≥ 1, 규칙 8 문자열은 2 그대로
- AC-009 되돌림(소스가 아니라 `$S` 사본에 적용): 규칙 9 블록을 뺀 사본 `no_rule9.md` → 13개 모두 `0`, `2 runs/<job_id>/dart/index.json`. "요약에 없는 사실은 단정하지 않는다." 문장만 뺀 사본 `no_v2.md` → 그 줄만 `0`, 나머지 12개는 그대로
- AC-011 #1: `PY -m backend.services.goose_harness > "$S/m.json" && diff "$S/m.json" backend/goose_harness_src/goose-manifest.json` → 출력 없음, `diff_exit=0`
- AC-011 #1·#3 되돌림(재생성 전 상태에서 관측): `diff` → `< "CLAUDE.md": "77e260e4…"` / `> "CLAUDE.md": "a7a9a06e…"`, `diff_exit=1`; `PY -m pytest backend/tests/test_goose_harness.py -q` → `FAILED ...::test_committed_source_matches_committed_manifest` · `FAILED ...::test_committed_manifest_covers_instructions_settings_and_whole_skill` · `2 failed, 30 passed`
- AC-011 #2: `shasum -a 256 backend/goose_harness_src/claude-settings.json` → `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`
- AC-011 #3: `PY -m pytest backend/tests/test_goose_harness.py -q` → `32 passed in 0.10s`
- AC-011 #4: 블록을 acceptance.md에서 정규식으로 그대로 추출(`$S/rulenum.py`) → `python3 -I "$S/rulenum.py" backend/goose_harness_src/harness-instructions.md` → `rules [1, 2, 3, 4, 5, 6, 7, 8, 9]` / `rule numbering ok`
- AC-011 #4 병합 상황 되돌림(`$S` 사본, 규칙 9 자리에 합성 대역 "감수 세션 규칙" 한 줄을 넣고 네이버 규칙을 뒤에 둠): 정상 재번호 `m_ok10.md` → `rules [1, …, 10]` / `rule numbering ok`; 번호 9 중복 `m_dup9.md` → `top-level numbers not 1..K unique: [1, 2, 3, 4, 5, 6, 7, 8, 9, 9]`; 상위만 10·라벨 9 `m_labels9.md` → `line 28: sub-item 9-* under rule 10` · `line 29: sub-item 9-* under rule 10` (출력을 `head -3`으로 잘라 앞 두 줄만 봤다); 라벨 10·본문 "9-2에서" 남김 `m_prose9.md` → `line 30: in-text reference 9-2 inside rule 10`. 실제 006 병합 트리에는 아직 돌리지 않았다(병합은 리드 몫)

#### M4 도중 발견해 고친 것 — 하네스 원본 안 `__pycache__`

재생성한 매니페스트에 `.claude/skills/goose/workflows/fact-check/scripts/__pycache__/audit_report.cpython-313.pyc`가 섞여 나왔다. 원인은 M2의 AC-010 테스트가 `importlib`으로 `audit_report.py`를 불러 그 폴더에 바이트코드를 쓴 것이다(파일은 `.gitignore` 대상이라 `git status`에 보이지 않았고 추적 파일은 0개 — `git ls-files backend/goose_harness_src | grep -c pycache` → `0`). 이대로 커밋하면 매니페스트에 git에 없는 파일이 들어가 다른 체크아웃에서 무결성 검사가 깨진다. 조치: (1) 테스트가 불러오는 동안 `sys.dont_write_bytecode = True`(monkeypatch), (2) 테스트가 만든 `__pycache__` 폴더 삭제, (3) AC-010 재실행 `2 passed` 뒤 폴더 목록 `audit_report.py` 하나뿐, (4) 매니페스트 재생성. `git status --short --ignored backend/goose_harness_src/skills` → 출력 없음.

#### 최종 게이트

- AC-013: 전 `ls ~/.goose-harness/runs | wc -l; stat -f %m ~/.goose-harness/runs` → `5` / `1792576328`; `PATH=/usr/bin:/bin PY -m pytest <acceptance AC-013의 8개 파일> -q` → `330 passed, 1 warning in 16.65s`(`$S/ac013_goose.txt`), `network attempt in goose test` 0건; 후 → `5` / `1792576328`(같음). 통과 수 330 = 기준선 267 + 새 41 + 새 22
- `PY -m pytest backend/tests -q -k goose` → `330 passed, 214 deselected, 1 warning in 14.81s`(`$S/k_goose.txt`)
- 전체 백엔드 `PY -m pytest backend/tests -q` → 처음 `5 failed, 481 passed, 1 warning, 58 errors`. 그중 `test_air7_015_production_code_check_uses_server_stock_list`(`E       assert False is True`)는 이 SPEC 테스트였다: `test_ai_report_service.py`가 `sys.modules["my_chart.registry"]`에 스텁을 monkeypatch 없이 영구히 심어, 같은 세션에서 뒤에 도는 이 테스트가 스텁을 봤다. 재현: `PY -m pytest backend/tests/test_ai_report_service.py backend/tests/test_goose_job_service.py -q` → `E       assert False is True` / `1 failed, 99 passed`. 조치: 이 테스트 동안만 `my_chart.registry`·`backend.services.ai_report_service`를 `sys.modules`에서 지움(monkeypatch가 복원) → 같은 명령 `100 passed`. 수정 뒤 전체 → `4 failed, 482 passed, 1 warning, 58 errors`(`$S/full_backend2.txt`): `test_bubble_characterization.py` 21 · `test_bubble_ranking_parity.py` 30 · `test_bubble_schema_nullable.py` 1 · `test_stocks_master.py` 6 (ERROR, 원인 59줄 모두 `ImportError: cannot import name 'get_sector_registry' from '<unknown module name>'` — 같은 스텁 오염), `test_bubble_empty_date_edge.py` 1 · `test_minervini_template.py` 3 (FAILED). 새 테스트를 모두 뺀 실행(`--ignore=backend/tests/test_goose_naver_prefetch.py -k "not air7"`) → `4 failed, 419 passed, 22 deselected, 1 warning, 58 errors`로 같은 실패 — 이 SPEC의 테스트에서 오지 않는다
- ruff: 미설치(`No module named ruff`) — 린트 미관측
- 보호 파일: `git diff --stat 1c49411 -- backend/goose_harness_src/claude-settings.json backend/goose_harness_src/skills backend/services/goose_dart_prefetch.py backend/services/ai_report_service.py backend/routers/ai_report.py frontend backend/tests/conftest.py backend/tests/fixtures/naver/recorded` → 출력 없음

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-10-21T00:00:00+09:00   # 날짜만 정확, 시각은 기록하지 않음
run_commit_sha: <M4 커밋 — 이 파일을 담는 커밋이라 자기 SHA를 적을 수 없음; M2 b28394c, M3 9b4443f>
run_status: run-lane-complete-pending-lead   # AC-012(라이브)·006 병합 단계는 리드 몫
ac_pass_count: 14   # AC-001~011, 013, 014, 015 (run 레인 범위)
ac_fail_count: 0
ac_not_in_lane: [AC-AIR7-012]
reversal_checks_observed: 24 (M2) + 12 (M3) + AC-009 2 + AC-011 #1·#3 1 + AC-011 #4 3
preserve_list_post_run_count: claude-settings.json sha256 e8b527cc… 동일, skills/**·audit_report.py·goose_dart_prefetch.py·ai_report_service.py·routers·frontend·conftest·recorded 픽스처 diff 없음
l44_pre_commit_fetch: not-run   # 리드 지시로 push·통합 없음
l44_post_push_fetch: not-applicable
new_warnings_or_lints_introduced: unknown — ruff 미설치
cross_platform_build: not-applicable (Python, macOS에서만 실행)
total_run_phase_files: 14   # 서로 다른 파일 수: M2 10 + M3 2(goose_job_service.py, test_goose_job_service.py) + M4 2(harness-instructions.md, goose-manifest.json); progress.md는 M2에 포함
m1_to_mN_commit_strategy: 마일스톤마다 커밋 1개(M2 b28394c, M3 9b4443f, M4 이 커밋), 명시적 pathspec
coverage_new_module: 97% (201 stmts, 7 miss)
full_backend_suite: 4 failed / 58 errors — 새 테스트를 빼도 같음(기존 my_chart.registry 스텁 오염), goose 330 passed
```

Gaps(이 레인이 관측하지 않은 것):
- AC-012 라이브 게이트(리드 몫), 006과의 실제 병합 단계 1~4(리드/통합 카드 몫 — #4 판정은 합성 사본으로만)
- ruff 린트 게이트
- 전체 백엔드의 기존 실패 4·오류 58이 이 SPEC 이전 커밋(`1c49411`)에서도 같은지는 그 커밋으로 직접 돌려 보지 않았다(브랜치 전환 금지). 근거는 새 테스트를 뺀 실행에서 같은 수가 나온 것과 원인 문구뿐이다. 그 실행에도 `goose_job_service.py` 소스 변경은 들어 있다(다만 실패 파일들은 그 모듈을 가져오지 않는다 — 가져오기 검사는 하지 않았다)
- spec·plan·acceptance `status: draft` 유지(리드 지시 우선) — `in-progress` 전환 여부는 리드 결정
- 실제 태그가 든 `body`, 그룹당 기사 2건, 실제 상장 종목 0건, 호출 제한(spec G3·G4)

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
