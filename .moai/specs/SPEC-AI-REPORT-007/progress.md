# SPEC-AI-REPORT-007 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-10-21T00:00:00+09:00
- plan_status: audit-ready 대기 (v0.1.0, plan-audit 미실시)
- card: t19 · worktree: `.claude/worktrees/t19` · branch: `WT-naver-search-block` · base HEAD: `c8e5c20`
- artifacts: spec.md, plan.md, acceptance.md, progress.md
- counts: REQ 13개(REQ-AIR7-001~013), AC 13개(AC-AIR7-001~013) — Tier M 상한(각 16) 이내
- needs_clarification: 0건 (응답 구조·`article_url` 형태는 run 단계 M1 관측 항목, spec G4·G5)
- gating_live_ac: AC-AIR7-012는 리드 몫(통합·재시작 뒤), 이 레인 밖
- overlap: 카드 t18(레인 1)과 `goose_job_service.py`·`harness-instructions.md`·`goose-manifest.json` 겹침 — plan.md §5 병합 순서 메모

### 계측으로 확정한 사실 (lessons #10 — 주장 | 관측 방법 | 결과)

모든 명령은 2026-10-21, 워크트리 HEAD `c8e5c20`에서 실행했다.

| # | 주장 (spec·plan·acceptance에서 쓰는 곳) | 관측 방법 | 결과 |
|---|---|---|---|
| P1 | 권한 파일은 `WebFetch`를 도메인 제한 없이 허용하고, 해시는 고정값이다 (spec §2.5, AC-011 #2) | `shasum -a 256 backend/goose_harness_src/claude-settings.json`; `grep -c '"WebFetch"' …`; `grep -c 'WebFetch(' …` | `e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3`; `1`; `0` (도메인 지정 형태 `WebFetch(...)`는 0회라 이 프로브는 제한이 있었다면 볼 수 있었다) |
| P2 | a5becbb9 실행의 권한 거부는 Bash 1건뿐이고 WebFetch 언급은 없다 (spec §2.5) | 주 체크아웃 `.dev-server.log`: `grep -c a5becbb9`; 그 줄 중 `grep -ci denied`; 그 줄 중 `grep -ci webfetch` | `3`; `1` — 원문 앞부분: `goose 세션 permission_denied: 도구=Bash 사유=rule 명령=cd /Users/byunjungwon/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/dart && for f in …`; `0`. 한계: 로그는 실행기가 해석한 권한 거부만 남기므로 WebFetch 도구 오류의 부재를 증명하지 않는다(spec G1) |
| P3 | 감사의 `naver` 채널 조건과 `blocked` 불인정 (spec §2.4) | `grep -n "channels.update\|read_ids(s.get('source_ids'))\|차단은 완료가 아닙니다" audit_report.py`; `grep -c "verification')!='direct_read'" audit_report.py` | 44행 `channels.update({'company_ir','naver','industry'})`, 51행 `if (s.get('result')=='read' and read_ids(s.get('source_ids'))) or s.get('result')=='no_results'`, 52행 결함 문구에 `차단은 완료가 아닙니다`; `1`. `read_ids` 본문(21~28행)은 Read로 확인: `dart=True`일 때만 호스트를 검사하며 51행 호출은 `dart` 인자가 없다 |
| P4 | 작업 서비스에는 아직 네이버 관련 코드가 없고, DART 수집기는 운영 인스턴스에만 붙어 있다 (spec §4, plan T5) | `grep -c naver backend/services/goose_job_service.py`; `grep -n "prefetcher=goose_dart_prefetch" …` | `0`; `389:    prefetcher=goose_dart_prefetch.DartPrefetcher(),` |
| P5 | 새 수집 모듈 파일은 아직 없다 (spec §4 [NEW]) | `ls backend/services/goose_naver_prefetch.py` | `No such file or directory` |
| P6 | 하네스 지침에 네이버 색인 문자열은 없고 DART 색인 문자열은 있다 — AC-009 프로브가 부재를 볼 수 있다 | `grep -cF 'runs/<job_id>/naver/index.json' harness-instructions.md`; `grep -cF 'runs/<job_id>/dart/index.json' …` | `0`; `2` |
| P7 | 파일 이름이 `test_goose_`로 시작하면 기존 네트워크 가드가 적용된다 — conftest 변경 불필요 (spec §4 [EXISTING], REQ-AIR7-012) | `grep -n "_GOOSE_PREFIXES = " backend/tests/conftest.py` | `20:_GOOSE_PREFIXES = ("test_goose_", "test_main_goose")` |
| P8 | 지침 내용을 검사하는 기존 테스트는 규칙 4-1·4-2 문자열과 매니페스트 해시만 본다 — 규칙 9 추가는 그 단언을 깨지 않는다(매니페스트 재생성 전제) (plan §5, AC-011 #3) | `grep -n '_REAL_SOURCE / "harness-instructions.md"' backend/tests/test_goose_harness.py` → 431·468행, 466~477행 Read | 431행 매니페스트 해시 비교, 468행 이후 4-1·4-2 문자열 포함 단언 8개(추가된 규칙과 무관) |
| P9 | SPEC ID가 형식에 맞고 중복이 없다 | `[[ "SPEC-AI-REPORT-007" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS`; 주 체크아웃·모든 워크트리의 `.moai/specs/SPEC-AI-REPORT-00*` 목록; `git log --all --oneline \| grep -c "AI-REPORT-00[67]"` | `PASS`; 001~005만 존재(006·007 없음); `0` |

미관측(이 표에 없는 것): 네이버 모바일 API 응답의 정확한 구조와 `article_url` 형태(spec G4·G5) — 이 plan 단계에서는 네트워크 요청을 보내지 않았다. 엔드포인트 관측표(spec §2.3)는 리드와 `.moai/reports/t19/investigation.md`의 기록이며 이 문서 작성자가 다시 재지 않았다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
