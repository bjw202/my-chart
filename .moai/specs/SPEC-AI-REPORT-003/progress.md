# SPEC-AI-REPORT-003 진행 상황

구현 시작 전 빈 체크리스트. 각 Step 완료 시 체크 표시하고 검증 결과 기록.

---

## Step 1 — Codex CLI runner 어댑터

- [x] `backend/services/codex_cli_runner.py` 작성
- [x] `backend/tests/test_codex_cli_runner.py` 작성 (6개 케이스 이상)
- [x] `pytest backend/tests/test_codex_cli_runner.py` 통과
- [x] 기존 파이프라인 무손상 확인

**검증 결과** (2026-04-23, 브랜치 `feature/SPEC-AI-REPORT-003-codex-replacement`):
- 신규 테스트: `backend/tests/test_codex_cli_runner.py` 6/6 PASSED (1.39s)
  - test_run_codex_success_writes_md: output_path 에 markdown 기록 + success=True 계약
  - test_run_codex_timeout: 1초 타임아웃에 10초 sleep → error_type='timeout', 파일 미생성
  - test_run_codex_empty_output: exit 0 + 파일 미작성 → error_type='empty_output'
  - test_run_codex_binary_missing: FileNotFoundError → error_type='binary_missing'
  - test_run_codex_nonzero_exit: stderr + exit=7 → error_type='exit_error', stderr tail 포함
  - test_run_codex_cancelled: asyncio.Task.cancel() → CancelledError re-raise + 프로세스 정리
- 회귀 스모크 (기존 파이프라인 무손상):
  - `pytest backend/tests/test_claude_cli_streamer.py test_deep_research_collector.py test_ai_report_service.py` → 89/89 PASSED (34.99s)
- 코드 설계 포인트:
  - `_PROC_GRACE_PERIOD_SEC=15.0` + terminate→kill 2단계 정리 (claude_cli_streamer 패턴 복제)
  - stderr 마지막 50 라인 tail buffer 보관 (진단용)
  - 에러 분류: binary_missing / auth / timeout / empty_output / exit_error
  - @MX:ANCHOR + @MX:WARN 태그 추가 (fan_in Step 3/4 완료 후 ≥3 도달 예정)
- 격리 테스트 로드: `importlib.util.spec_from_file_location` 로 `backend/services/__init__.py` cascade import 회피
- 미완료 사항: 없음. Step 2 (Codex 프롬프트 템플릿) 착수 대기 중.

---

## Step 2 — Codex 프롬프트 템플릿

- [x] `backend/prompts/codex_prompt.md` 작성
- [x] 플레이스홀더 검증 로직 추가
- [x] `test_load_codex_prompt` 통과

**검증 결과** (2026-04-23):
- 신규 파일: `backend/prompts/codex_prompt.md`
  - 플레이스홀더: `〈종목명〉`, `〈종목코드〉`
  - 섹션: Executive Summary → 사업 본질 → 최신 이벤트 → 시장 심리 → 실적·밸류·수급·테크니컬 → Catalyst → 리스크 → 스윙 진입·청산 관점 → 출력 규칙
  - 출력 규칙: `[n]` 인용 + 참고문헌 섹션, 추상어·매매권유 금지
- `codex_cli_runner.py` 확장:
  - `_PROMPT_TEMPLATE_PATH`, `_REQUIRED_PLACEHOLDERS` 상수 추가
  - `load_codex_prompt(code, stock_name) -> str` 함수 추가 (fail-fast 검증 3단계: 파일 존재 → 템플릿 플레이스홀더 포함 → 치환 후 잔존 없음)
- 신규 테스트 3개 (`test_codex_cli_runner.py` 에 추가):
  - `test_load_codex_prompt_substitutes_placeholders` — 정상 치환
  - `test_load_codex_prompt_missing_file_raises` — 템플릿 미존재 → FileNotFoundError
  - `test_load_codex_prompt_missing_placeholder_raises` — 템플릿 malformed → ValueError
- Step 2 테스트 결과: 9/9 PASSED (1.40s)
- 회귀 스모크: 89/89 PASSED (유지)
- 미완료 사항: 없음. Step 3 (Deep Mode Codex 슬롯 교체 + staging 2단계) 착수 대기 중.

---

## Step 3 — Deep Mode Codex 슬롯 교체

- [x] `_collect_codex` 함수 신규
- [x] `SOURCE_NAMES` 갱신 (`perplexity` → `codex`)
- [x] `_DEFAULT_TIMEOUTS["codex"] = 600.0`
- [x] 1회 재시도 로직 (timeout/exit_error/empty_output 재시도, binary_missing/auth 재시도 금지)
- [x] `create_staging_directory` → `prepare_staging_directory` + `finalize_staging_directory` 2단계 분리
- [x] `deep_research_service.py` 3단계 호출 재배치 (prepare → collect → finalize)
- [x] SSE phase 이벤트 이름 변경 (`perplexity` → `codex`, staging 2-phase 이벤트 추가)
- [x] 관련 테스트 갱신 (perplexity 전용 테스트 삭제 + codex 시나리오 추가)
- [x] `pytest backend/tests/test_deep_research_collector.py` 통과
- [x] `pytest backend/tests/test_deep_research_service.py` 통과

**검증 결과** (2026-04-23, atomic 커밋 3a → 3b → 3c+3d 순차 진행):

### 3a: staging 2단계 분리
- `prepare_staging_directory(code, base_dir)` + `finalize_staging_directory(staging_dir, code, stock_name, result)` 추가
- `create_staging_directory` 는 두 함수의 thin wrapper 로 유지 (기존 시그니처 보존)
- 3a 단독 검증: 70/70 PASSED

### 3b: _collect_codex 추가 (perplexity 공존)
- 신규: `_collect_codex(code, stock_name, *, staging_sources_dir)` with 1회 재시도 로직
- Lazy import + fail-fast 에러 분류 (missing_staging_dir / import_error / prompt_error)
- 테스트 6개 추가: success / timeout_retry_fails / binary_missing / retry_succeeds / auth_no_retry / without_staging_dir
- 3b 단독 검증: 76/76 PASSED

### 3c+3d: Perplexity → Codex 전면 cutover (3c/3d 통합 커밋)
- 제거: `_PERPLEXITY_URL`, `_collect_perplexity`, `_normalize_perplexity`, 관련 테스트 6개
- 갱신: `SOURCE_NAMES` = ("codex", "brave", "tavily", "naver", "youtube")
- 갱신: `_DEFAULT_TIMEOUTS` (codex: 600.0, perplexity 제거)
- 갱신: `_collect_one_source` — codex 전용 `staging_sources_dir` kwarg 전달
- 갱신: `collect_all_sources` — `staging_sources_dir` 파라미터 추가
- 갱신: `_build_summary_md` + `finalize_staging_directory` — perplexity 분기 삭제, 소스명 표 갱신
- 갱신: `deep_research_service.py` — prepare → collect → finalize 3단계, user_prompt 의 `perplexity.md` → `codex.md`, `_source_count` 의 codex 분기 (data["char_count"])
- 갱신: 4개 테스트 (`test_minimum_2_sources_gate_*`, `test_all_sources_succeed`, `test_collect_all_sources_no_client`) 를 codex mocks 로 전환
- 신규: `test_finalize_skips_codex_md_write` (subprocess 경로와의 충돌 방지 검증)
- 3c+3d 최종 검증: deep_research_* 70/70 + codex_cli_runner 9/9 = 79/79 PASSED (2.00s)
- 광역 회귀: claude_cli_streamer + ai_report_service + ai_report_router_deep_mode 64/64 PASSED

### 미완료 사항
없음. Step 4 (Fast Mode Codex 전환 + heartbeat) 착수 대기 중.

---

## Step 4 — Fast Mode Codex 전환

- [x] `stream_codex_fast` 함수 신규 (4a)
- [x] 30초 단위 heartbeat 구현 (`_CODEX_FAST_HEARTBEAT_SEC = 30.0`, 5개 메시지 rotation)
- [x] markdown 청크 분할 스트리밍 (`_CODEX_FAST_CHUNK_SIZE = 256`)
- [x] `stream_perplexity` 제거 (4b)
- [x] `SYSTEM_PROMPT`, `SEARCH_DOMAIN_FILTER`, `load_prompt`, `_load_prompt_template`, `_PROMPT_TEMPLATE_PATH` 제거
- [x] 라우터에서 `codex` 바이너리 체크 추가 (PERPLEXITY_API_KEY 체크 제거)
- [x] `mode=fast` 신설 (default), `mode=perplexity` 는 deprecated alias → fast 로 라우팅
- [x] `main.py` lifespan 에서 `_load_prompt_template` 호출 제거 → `load_codex_prompt` 검증으로 교체
- [x] `test_ai_report_service.py` 갱신 (`TestLoadPrompt` 제거, `TestStreamCodexFast` 5개 추가)
- [x] `test_ai_report_router_deep_mode.py` Codex stub 교체 (`TestFastModePathPreservation` + `test_fast_rate_limit_unaffected_by_deep_quota`)
- [x] 모든 테스트 통과

**검증 결과** (2026-04-23, atomic 커밋 4a → 4b):

### 4a: stream_codex_fast 신규
- `stream_codex_fast(stock_name, code) -> AsyncGenerator[dict, None]` 추가
- 30초 주기 heartbeat phase 이벤트 (`codex_fast_progress`, 5가지 메시지 rotation)
- 완료 시 markdown 을 256자 청크로 분할 yield, save_report 로 영속화
- `asyncio.shield` 로 heartbeat timeout 시 codex subprocess 보호, CancelledError re-raise
- 에러 경로: prompt_error / codex_failure / empty_output → error 이벤트
- 테스트 5개: yields_chunks_and_done / emits_error / heartbeat / save_report / prompt_error
- 4a 단독 검증: 35/35 PASSED (stream_perplexity 는 아직 공존)

### 4b: 라우터·main·테스트 스위치 + stream_perplexity 제거
- 라우터 `generate_report`: mode 파라미터 `"fast"`(기본)/`"deep"`/`"perplexity"`(deprecated alias) 수용
- `_handle_perplexity_mode` → `_handle_fast_mode` 로 대체 (codex CLI 체크 + rate limit + 중복 방지 유지)
- `main.py` lifespan: `_load_prompt_template` → `load_codex_prompt` 검증, `codex` 바이너리 부재 시 warning
- `ai_report_service.py` 에서 제거: `stream_perplexity`, `SYSTEM_PROMPT`, `SEARCH_DOMAIN_FILTER`, `_PROMPT_TEMPLATE_PATH`, `_load_prompt_template`, `load_prompt`, `import httpx`, `import json`, `lru_cache`
- 테스트 갱신: `TestLoadPrompt` 제거, `TestPerplexityPathPreservation` → `TestFastModePathPreservation` (3 케이스), rate limit isolation 테스트 갱신
- stub pollution 수정: `_load_codex_runner_into_sys_modules` 가 stub (run_codex_research 누락) 을 감지하면 실 모듈 재로드
- 4b 최종 검증: 134/134 PASSED (ai_report_service + ai_report_router_deep_mode + codex_cli_runner + deep_research_collector + deep_research_service + claude_cli_streamer)

### 미완료 사항
없음. Step 5 (Perplexity 잔여 자산 — perplexity_cache.py, perplexity_prompt.md, .env.example) 착수 대기 중.

---

## Step 5 — Perplexity 자산 완전 제거

- [x] `deep_research_collector.py` 내 `_collect_perplexity`, `_normalize_perplexity`, `_PERPLEXITY_URL` 제거 (Step 3 에서 처리됨)
- [ ] `backend/services/perplexity_cache.py` 삭제
- [ ] `backend/prompts/perplexity_prompt.md` 삭제
- [ ] `ai_report_service.py` 의 `SYSTEM_PROMPT`, `SEARCH_DOMAIN_FILTER`, `load_prompt`, `_load_prompt_template` 제거 (Step 4 와 연동)
- [ ] `.env` / `.env.example` 에서 `PERPLEXITY_API_KEY` 제거
- [ ] `grep -ri "perplexity" backend/ --include="*.py"` 결과 없음
- [ ] pytest 전체 통과

**검증 결과**: Step 4 (Fast Mode 전환) 완료 후 Step 5 본격 진행. Step 3 cutover 로 collector 쪽 perplexity 자산은 이미 제거됨.

---

## Step 6 — 합성 프롬프트·SSE·프론트엔드

- [ ] `stock_synthesis_prompt.md` 의 `sources/perplexity.md` → `sources/codex.md`
- [ ] `aiReport.ts::SourceName` 갱신
- [ ] ProgressPanel 라벨 맵 갱신
- [ ] Fast Mode 로딩 컴포넌트 heartbeat 메시지
- [ ] TypeScript 컴파일 통과
- [ ] 프론트엔드 테스트 통과

**검증 결과**: (Step 완료 시 기재)

---

## Step 7 — 전체 회귀 테스트

- [ ] `pytest backend/tests/ -v` 전부 통과 (my_chart.db 관련 사전 존재 이슈 제외)
- [ ] 커버리지: `codex_cli_runner`, `_collect_codex`, `stream_codex_fast` ≥ 85%
- [ ] ruff / lint 통과
- [ ] @MX 태그 갱신 (Perplexity 관련 tag 정리, Codex 관련 tag 추가)

**검증 결과**: (Step 완료 시 기재)

---

## Step 8 — 실 Codex 스모크

- [ ] Fast Mode end-to-end (`/api/ai-report/006400?mode=fast`) 정상 동작
- [ ] Deep Mode end-to-end (`/api/ai-report/006400?mode=deep`) 정상 동작
- [ ] `sources/codex.md` 생성 확인
- [ ] 1회 재시도 경로 수동 검증
- [ ] SSE heartbeat UX 사용자 체감 확인

**검증 결과**: (Step 완료 시 기재)

---

## 최종 Acceptance 검증

AC-001 ~ AC-012 각 시나리오 검증:

- [ ] AC-001: Fast Mode Codex 전환
- [ ] AC-002: Deep Mode Codex 슬롯
- [ ] AC-003: 1회 재시도 동작
- [ ] AC-004: Fast Mode heartbeat UX
- [ ] AC-005: Perplexity 완전 제거 (grep 결과)
- [ ] AC-006: 스테이징 2단계 생성
- [ ] AC-007: 합성 프롬프트 갱신
- [ ] AC-008: 타임아웃 동작
- [ ] AC-009: 2개 이상 성공 게이트
- [ ] AC-010: 프론트엔드 SourceName 갱신
- [ ] AC-011: 경로 안전
- [ ] AC-012: 전체 테스트 스위트 통과

---

## 로그 (반복 진행 기록)

| 이터레이션 | 날짜 | 완료 AC | 실패 AC | 에러 delta | 비고 |
|---|---|---|---|---|---|
| (빈 상태) | | | | | |
