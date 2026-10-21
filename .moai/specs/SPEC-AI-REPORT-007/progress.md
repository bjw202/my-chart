# SPEC-AI-REPORT-007 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-10-21T00:00:00+09:00
- plan_status: plan-audit 2회차 대기 (v0.2.0)
- plan_audit:
  - 1회차 FAIL 0.81 — `.moai/reports/t19/plan-audit.md` (D1a·D1b·D3·D4·D5·D6 차단, D2·D7·D8·D9·D10 선택 → v0.2.0에서 전부 반영)
- card: t19 · worktree: `.claude/worktrees/t19` · branch: `WT-naver-search-block` · 1회차 기준 HEAD `c8e5c20`, 2회차 수정 기준 HEAD `5b7a22b`
- artifacts: spec.md, plan.md, acceptance.md, progress.md
- counts: REQ 14개(REQ-AIR7-001~014), AC 14개(AC-AIR7-001~014) — Tier M 상한(각 16) 이내
- needs_clarification: 0건 (응답 구조·`article_url` 형태는 run 단계 M1 관측 항목, spec G4·G5)
- gating_live_ac: AC-AIR7-012는 리드 몫(통합·재시작 뒤), 이 레인 밖
- overlap: SPEC-AI-REPORT-006(카드 t18, 커밋 `4663bb3`)과 `goose_job_service.py`·`harness-instructions.md`(둘 다 규칙 9 추가)·`goose-manifest.json`·`test_goose_job_service.py` 겹침 — plan.md §5 필수 병합 단계

### 미결 사항 (리드 결정)

- Q1 `phase` 값: spec.md 프런트매터는 `"v0.5.5 target"`이다. 이것은 AI-REPORT 계열 순번(004 `v0.5.3`, 005 `v0.5.4`)을 이은 **미확정 가정**이며 사실로 주장하지 않는다. 저장소에는 이 값을 고정하는 원천이 없고(사실표 P15), 005 이후 완료된 SPEC-TEST-HERMETIC-001·SPEC-RS-REBALANCE-001과 카드 t18의 SPEC-AI-REPORT-006은 `"v0.6.0 target"`을 쓴다. 006과 맞추려면 `"v0.6.0 target"`, 계열 순번을 지키려면 그대로 둔다. 리드가 정하면 manager-spec이 프런트매터만 고친다.

### 계측으로 확정한 사실 (lessons #10 — 주장 | 관측 방법 | 결과)

P1~P5·P7·P8은 2026-10-21 HEAD `c8e5c20`에서, P6·P9a·P9b·P10~P15는 같은 날 HEAD `5b7a22b`에서 이 문서 작성자가 직접 실행했다(1회차 감사의 프로브 기록을 옮겨 적지 않았다).

| # | 주장 (spec·plan·acceptance에서 쓰는 곳) | 관측 방법 | 결과 |
|---|---|---|---|
| P1 | 권한 파일은 `WebFetch`를 도메인 제한 없이 허용하고, 해시는 고정값이다 (spec §2.5, AC-011 #2) | `shasum -a 256 backend/goose_harness_src/claude-settings.json`; `grep -c '"WebFetch"' …`; `grep -c 'WebFetch(' …` | `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`; `1`; `0` (도메인 지정 형태 `WebFetch(...)`는 0회라 이 프로브는 제한이 있었다면 볼 수 있었다) |
| P2 | a5becbb9 실행의 권한 거부는 Bash 1건뿐이고 WebFetch 언급은 없다 (spec §2.5) | 주 체크아웃 `.dev-server.log`: `grep -c a5becbb9`; 그 줄 중 `grep -ci denied`; 그 줄 중 `grep -ci webfetch` | `3`; `1` — 원문 앞부분: `goose 세션 permission_denied: 도구=Bash 사유=rule 명령=cd /Users/byunjungwon/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/dart && for f in …`; `0`. 한계: 로그는 실행기가 해석한 권한 거부만 남기므로 WebFetch 도구 오류의 부재를 증명하지 않는다(spec G1) |
| P3 | 감사의 `naver` 채널 조건, `no_results` 무조건 통과, `blocked` 불인정 (spec §2.4) | `grep -n "channels.update\|read_ids(s.get('source_ids'))\|차단은 완료가 아닙니다" audit_report.py`; `grep -c "verification')!='direct_read'" audit_report.py` | 44행 `channels.update({'company_ir','naver','industry'})`, 51행 `if (s.get('result')=='read' and read_ids(s.get('source_ids'))) or s.get('result')=='no_results'`, 52행 결함 문구에 `차단은 완료가 아닙니다`; `1`. 51행에서 `no_results`는 다른 조건 없이 통과한다. `read_ids` 본문(21~28행)은 Read로 확인: `dart=True`일 때만 호스트를 검사하며 51행 호출은 `dart` 인자가 없다 |
| P4 | 작업 서비스에는 아직 네이버 관련 코드가 없고, DART 수집기는 운영 인스턴스에만 붙어 있다 (spec §4, plan T5) | `grep -c naver backend/services/goose_job_service.py`; `grep -n "prefetcher=goose_dart_prefetch" …` | `0`; `389:    prefetcher=goose_dart_prefetch.DartPrefetcher(),` |
| P5 | 새 수집 모듈 파일은 아직 없다 (spec §4 [NEW]) | `ls backend/services/goose_naver_prefetch.py` | `No such file or directory` |
| P6 | AC-009 검사 문자열의 기준선 — 네이버 규칙 전용 문자열은 모두 0이라 프로브가 부재를 볼 수 있다. 규칙 8과 겹치는 짧은 표기는 이미 1이다 (AC-009) | `for s in …; do printf '%s\t%s\n' "$(grep -cF "$s" harness-instructions.md)" "$s"; done` (HEAD `5b7a22b`) | `0 runs/<job_id>/naver/index.json` · `0 article_url` · `0 channel: "naver"` · `0 metadata_only` · `0 "no_results"` · `0 모바일 뉴스 API 응답의 제목·본문 필드` · `0 서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음` · `1 accessed_at` · `0 original_news` · `2 runs/<job_id>/dart/index.json` · `1 서버 사전 수집본으로 열람`; 대체 문자열 `grep -cF '이번 세션에서 그 파일을 연 시각'` → 지침 `0`, plan.md 초안 `1`. ~~v0.1.0 AC-009의 "규칙 9를 지우면 앞의 8개 문자열이 모두 0"~~ — 철회: `서버 사전 수집본으로 열람`은 규칙 8에도 있어 지워도 1로 남는다(1회차 감사 A4). v0.2.0은 규칙 8과 겹치지 않는 문자열만 쓴다 |
| P7 | 파일 이름이 `test_goose_`로 시작하면 기존 네트워크 가드가 적용된다 — conftest 변경 불필요 (spec §4 [EXISTING], REQ-AIR7-012) | `grep -n "_GOOSE_PREFIXES = " backend/tests/conftest.py` | `20:_GOOSE_PREFIXES = ("test_goose_", "test_main_goose")` |
| P8 | 지침 내용을 검사하는 기존 테스트는 규칙 4-1·4-2 문자열과 매니페스트 해시만 본다 — 규칙 추가는 그 단언을 깨지 않는다(매니페스트 재생성 전제) (plan §5, AC-011 #3) | `grep -n '_REAL_SOURCE / "harness-instructions.md"' backend/tests/test_goose_harness.py` → 431·468행, 466~477행 Read | 431행 매니페스트 해시 비교, 468행 이후 4-1·4-2 문자열 포함 단언 8개(추가된 규칙과 무관) |
| P9a | ~~SPEC ID가 형식에 맞고 006·007이 모두 비어 있다~~ — **철회**(1회차 감사 D2): c8e5c20(16:58:56) 시점 관측은 맞았으나 그 뒤 17:10:50에 카드 t18이 SPEC-AI-REPORT-006을 커밋했다. 006은 카드 t18이 가지고 있으므로 이 SPEC은 007을 그대로 쓴다 | `[[ "SPEC-AI-REPORT-007" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS`; `git -C <worktree> log -1 --format='%h %ci %s' 4663bb3` | `PASS`; `4663bb3 2026-10-21 17:10:50 +0900 docs(SPEC-AI-REPORT-006): plan 단계 SPEC 초안 작성 (카드 t18)` |
| P9b | SPEC-AI-REPORT-006도 규칙 9를 더하고 매니페스트를 재생성하며 작업 서비스를 바꾼다 (spec 관계 문단, plan §5) | `git -C <worktree> show 4663bb3:.moai/specs/SPEC-AI-REPORT-006/spec.md \| grep -n "^phase:\|harness-instructions\|goose_job_service\|goose-manifest"` | `10:phase: "v0.6.0 target"` · `65:… goose_job_service.py … 1차 세션 뒤 후처리(재검사 → 캡처 → 감수 → 영수증), 진행 이벤트, 끄기 스위치, 취소·fail-open` · `66:… harness-instructions.md … 규칙 7 개정, 감수 세션 규칙 9 추가` · `67:… goose-manifest.json … 지침 변경에 따른 매니페스트 재생성` · `72:… test_goose_job_service.py, test_goose_runner.py, test_goose_harness.py …` (49행 D3 결정 줄도 `harness-instructions.md`를 언급) |
| P10 | `dart_prefetch` 단계는 프론트 소스 3개와 프론트 테스트 2개에 박혀 있다 — 새 단계를 만들면 같은 범위가 바뀐다 (plan T6) | `grep -rln dart_prefetch frontend/src`; `grep -rln dart_prefetch backend/tests` | 프론트: `types/aiReport.ts`, `utils/__tests__/gooseJob.test.ts`, `utils/gooseJob.ts`, `components/ProgressPanel.tsx`, `components/__tests__/ProgressPanel.test.tsx`; 백엔드 테스트: `test_goose_dart_prefetch.py`, `test_goose_job_service.py`, `fixtures/dart/README.md` |
| P11 | 출처마다 `accessed_at`이 필수다 (spec REQ-010, plan T2) | `grep -n accessed_at …/stock-report/references/report-input.md`; `grep -n accessed_at …/stock-report/scripts/render_report.py` | `37:각 source는 다음 문자열을 모두 갖습니다: … accessed_at …` · `42:- published_at, accessed_at: ISO 날짜 또는 …` · `53: "accessed_at":"실제 읽은 날짜" …`; `117: for key in ("id", "title", "publisher", "published_at", "period", "accessed_at", "read_scope", "findings"):` |
| P12 | httpx `MockTransport`는 시간 상한을 적용하지 않고, DART 모듈은 바깥 `asyncio.wait_for`로 상한을 보장한다 (spec REQ-005, plan T4, acceptance §A·AC-005) | `PY -I -c "import httpx,inspect; print(httpx.__version__); src=inspect.getsource(httpx.MockTransport.handle_async_request); print(src); print('timeout' in src)"`; `grep -n "asyncio.wait_for" backend/services/goose_dart_prefetch.py` | `0.28.1`, 메서드 본문은 `await request.aread()` → `response = self.handler(request)` → 필요하면 `await response` → `return response`, `False`; `376:        return await asyncio.wait_for(self._send(method, url, form, timeout), timeout)` |
| P13 | AC-011 #4 규칙 번호 검사가 현재 트리에서 통과하고, 중복 번호와 남은 옛 하위 라벨을 잡는다 | 블록과 같은 판정 로직을 `python3 -I -c`로 (1) 현재 `harness-instructions.md`, (2) 메모리 안 합성 줄 목록 3종에 실행 | (1) `rules [1, 2, 3, 4, 5, 6, 7, 8]` / `rule numbering ok`; (2) 규칙 9 두 개 → `top-level numbers not 1..K unique: [1, 2, 3, 4, 5, 6, 7, 8, 9, 9]`, 9·10으로 다시 매김 → `rule numbering ok`, 상위 10·하위 `9-6` → `line 12: sub-item 9-* under rule 10` |
| P14 | AC-012 검사 3이 통과 입력은 통과시키고 지어낸 `no_results`·`metadata_only` 주소·색인 밖 주소를 잡는다 | 블록과 같은 판정 로직을 `python3 -I -c`로 메모리 안 합성 색인(`outcome: partial`, `ok` 1건·`metadata_only` 1건)과 입력 4종에 실행 | `good violations 0 []` · `no_results violations 2 ['naver no_results while index outcome=partial', 'no naver read entry']` · `metadata_only_url violations 1 ['nv1: url is not an ok index article_url']` · `non_index_url violations 1 ['nv1: url is not an ok index article_url']` |
| P15 | `phase` 값을 고정하는 버전 원천이 없다 (spec 관계 문단, Q1) | `grep -H "^phase:"` 004·005·TEST-HERMETIC-001·RS-REBALANCE-001 spec.md; `grep -n '^version' pyproject.toml`; `git -C <worktree> tag --list` | 004 `"v0.5.3 target"`, 005 `"v0.5.4 target"`, TEST-HERMETIC-001 `"v0.6.0 target"`, RS-REBALANCE-001 `"v0.6.0 target"`; `7:version = "0.1.0"`; 태그는 `moai/SPEC-AI-REPORT-003/sync-complete`, `moai/SPEC-MINERVINI-001/sync-complete`, `moai/SPEC-RS-LINE-001/sync-complete`, `moai/SPEC-WEB-001/sync-complete`뿐(버전 태그 없음) |

미관측(이 표에 없는 것): 네이버 모바일 API 응답의 정확한 구조와 `article_url` 형태(spec G4·G5) — plan 단계에서는 네트워크 요청을 보내지 않았다. 엔드포인트 관측표(spec §2.3)는 리드와 `.moai/reports/t19/investigation.md`의 기록이며 이 문서 작성자가 다시 재지 않았다. P13·P14는 판정 로직을 합성 입력에 돌린 것이며, 실제 병합 트리와 실제 라이브 입력에는 아직 돌리지 않았다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
