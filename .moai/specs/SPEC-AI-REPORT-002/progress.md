## SPEC-AI-REPORT-002 Progress

- Started: 2026-04-16 (session start)
- Development mode: TDD (RED-GREEN-REFACTOR)
- Harness level: standard (Phase 2.8a evaluator-active in final-pass mode)
- Execution mode: solo (user overrode --team to sub-agent mode at Decision Point 1)
- Language detected: python (backend/pyproject.toml) + typescript (frontend/package.json)
- Team composition: backend-dev + frontend-dev + tester + quality (read-only)

### Phase Log

- Phase 0.9 complete: detected_language_skills = [python, typescript]
- Phase 0.95 complete: Full Pipeline / Team Mode (files=10, domains=3, user --team)
- Phase 1 streamlined (plan.md already present, user approved solo-mode execution at Decision Point 1)
- Phase A complete: 20 tests passed, 95% coverage on claude_cli_streamer.py, SPEC-001 30 regression tests all green
  - Files: backend/services/claude_cli_streamer.py (222 lines), backend/tests/test_claude_cli_streamer.py (455 lines)
  - MX tags: @MX:ANCHOR parse_stream_json_line, @MX:ANCHOR stream_claude_synthesis, @MX:WARN asyncio.create_subprocess_exec
  - Merged to main: 55f0b7c
- Phase B cherry-picked to main: a8451bf (base was pre-Phase-A; used cherry-pick)
- Phase C complete: 22 tests, 97% coverage on deep_research_service.py. Full SPEC 001+002 regression: 111 passed
  - Files: backend/services/deep_research_service.py, backend/prompts/stock_synthesis_prompt.md, backend/tests/test_deep_research_service.py
  - MX tags: @MX:WARN module state, @MX:ANCHOR check_deep_rate_limit, @MX:ANCHOR stream_deep_analysis
  - pytest-asyncio added to pyproject.toml dev deps. respx still needs to be added in Phase E.
  - Merged to main: 9b185d4
- Phase D complete (parallel sub-agents):
  - Backend (manager-tdd, commit 4714c8d): router mode=Query 분기, lifespan 3-block (claude-which/synthesis-prompt fail-fast/cleanup), 14 new tests
  - Frontend (expert-frontend, commit 5e82019): AiReportModal 2단 토글, ARIA tablist, 7 new tests, all 203 frontend tests passing
- test 인프라 fix (commit c1a3137): test_deep_research_service + test_ai_report_router_deep_mode의 my_chart sys.modules 오염 완화 (35 fail → 5 fail)
- Phase E1 complete (commit f665bc3): NFR-006 observability — stream_deep_analysis end-to-end 시작/종료 로그 (code/outcome/duration/chars)
- Phase E2 complete: _cleanup_stale_staging_dirs (Phase C 구현, Phase D lifespan에서 호출)
- Phase E3 deferred: README/CHANGELOG 업데이트는 /moai sync 단계로 이관

### Coverage Summary (per-agent reports)

| File | Coverage | Tests |
|---|---|---|
| backend/services/claude_cli_streamer.py | 95% | 20 |
| backend/services/deep_research_collector.py | 91% | 39 |
| backend/services/deep_research_service.py | 97% | 22 |
| backend/routers/ai_report.py + main.py | (router 14 새 테스트) | 14 |
| frontend AiReportModal + hook + api | (vitest 24 files / 203 tests) | 7 new |

### Final Test Status

- SPEC-001 (test_ai_report_service.py): 30/30 PASS (no regression)
- SPEC-002 Phase A: 20/20 PASS
- SPEC-002 Phase B: 39/39 PASS
- SPEC-002 Phase C: 22/22 PASS
- SPEC-002 Phase D backend: 14/14 PASS
- SPEC-002 Phase D frontend: 7/7 PASS (전체 vitest: 203 PASS)
- SPEC-001+002 합계: 125 backend PASS + 203 frontend PASS
- 사전-존재 알려진 이슈: test_sector_advanced.py 5건 — 다른 테스트 파일의 SimpleNamespace 스텁이 my_chart.registry를 덮어쓸 때 발생. SPEC-002 코드와 무관. conftest.py 도입으로 추후 해결 가능.

### Commits on main

```
f665bc3 feat(deep-research): SPEC-AI-REPORT-002 Phase E1 observability 로깅 강화
c1a3137 fix(tests): SPEC-AI-REPORT-002 sys.modules 오염 완화
5e82019 feat(deep-research): SPEC-AI-REPORT-002 Phase D4-D6 frontend 2-mode toggle
4714c8d feat(deep-research): SPEC-AI-REPORT-002 Phase D1+D3 router deep-mode branch + main lifespan
9b185d4 feat(deep-research): SPEC-AI-REPORT-002 Phase C orchestration + synthesis prompt
a8451bf feat(deep-research): SPEC-AI-REPORT-002 Phase B 5-source collector
55f0b7c feat(deep-research): SPEC-AI-REPORT-002 Phase A Claude CLI streamer
```

### Status: READY FOR /moai sync

### Post-release Patches (v1.0.1 ~ v1.0.5)

Phase 초기 release 이후 실사용 중 발견된 이슈 대응 및 UX/진단 개선이 누적되었다. 각 패치는 별도 commit + 회귀 검증을 수반했다.

| 버전 | commit | 주제 | 핵심 변경 |
|---|---|---|---|
| 1.0.1 | `293ba55` | Claude CLI 안정화 | timeout 180s → 600s (Sonnet 5-소스 합성용), `--cwd` → `--add-dir` + subprocess `cwd=`, `--permission-mode bypassPermissions`, `--model claude-sonnet-4-6` 명시. source별 timeout 세분화 (perplexity 120s / tavily 90s / 나머지 15s) |
| 1.0.2 | `da15772` | 종목 식별 모호성 | Naver/YouTube 검색 query에 `{stock_name} {6자리 코드}` 포함해 동명이인 회사 결과 배제. synthesis prompt 절대규칙 A/B/C 추가 (사전 학습 지식 사용 금지, "보고서 작성 불가" 면책 금지, 종목 코드 신뢰) |
| 1.0.3 | `f119302` | 명시적 모드 선택 UX + 캐시 | AI 버튼 즉시 시작 제거 → idle 모달 + "분석 시작" 버튼. `perplexity_cache.py` (메모리 TTL 10분 캐시) — 빠른 분석 → 같은 종목 심층 분석 시 Perplexity HTTP 호출 0 (시나리오 C 비용 절감) |
| 1.0.4 | `a7c8ad6` | 진행 상태 패널 | `collect_all_sources`에 `progress_callback` 추가, `asyncio.wait(FIRST_COMPLETED)`로 완료 순 이벤트 emit. 신규 phase 이벤트(`source_start`/`source_done`/`collecting_done`/`staging_done`/`synthesis_start`/`synthesis_first_chunk`), `SourceResult.cached` 필드, `<ProgressPanel>` 컴포넌트. 테스트 +13 (ProgressPanel 11 + AiReportModal 렌더 조건 2) |
| 1.0.5 | `6c12c8f` | 안정화 + 진단성 | Claude CLI `create_subprocess_exec(limit=4MB)` (기본 64KB로는 긴 stream-json에서 `LimitOverrunError`). `stream_deep_analysis`에 broad `except Exception`으로 미처리 예외를 `event: error`로 변환 (이전엔 연결 끊김 → "대기 중" 고착). `logging.basicConfig(INFO)`로 애플리케이션 로그를 `.dev-server.log`에 노출 |

### Post-release Commits

```
6c12c8f fix(deep-research): SPEC-AI-REPORT-002 v1.0.5 — 합성 단계 LimitOverrunError + 예외 방어
a7c8ad6 feat(progress-panel): SPEC-AI-REPORT-002 v1.0.4 — 심층 분석 진행 상태 패널
cd79885 docs(spec): SPEC-AI-REPORT-002 미추적 SPEC 산출물 + 다음 세션 인계 문서 추가
425cf57 docs(spec): SPEC-AI-REPORT-002 sync — README/CHANGELOG/.env.example 동기화
f119302 feat(deep-research): SPEC-AI-REPORT-002 v1.0.3 — 명시적 모드 선택 + Perplexity 재사용
da15772 fix(deep-research): SPEC-AI-REPORT-002 v1.0.2 — 종목 식별 모호성 + 학습데이터 면책 차단
c06d716 feat(e2e): SPEC-AI-REPORT-002 Playwright e2e + done 상태 retry 버튼 추가
293ba55 fix(deep-research): SPEC-AI-REPORT-002 v1.0.1 — Claude CLI timeout 600s 확장
```

### Regression Summary (v1.0.5 기준)

- Backend deep-research + claude_cli_streamer: **81/81 PASS**
- Frontend: **216/216 PASS** (신규 13개 ProgressPanel/AiReportModal 포함, 기존 203 + 13)
- 알려진 이슈: `test_sector_advanced.py` 5건 — sector 모듈 sys.modules 오염 (SPEC-AI-REPORT-002와 무관)

### Status: POST-RELEASE PATCHES MERGED TO MAIN
