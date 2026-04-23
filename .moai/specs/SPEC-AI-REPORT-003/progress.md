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

- [ ] `backend/prompts/codex_prompt.md` 작성
- [ ] 플레이스홀더 검증 로직 추가
- [ ] `test_load_codex_prompt` 통과

**검증 결과**: (Step 완료 시 기재)

---

## Step 3 — Deep Mode Codex 슬롯 교체

- [ ] `_collect_codex` 함수 신규
- [ ] `SOURCE_NAMES` 갱신 (`perplexity` → `codex`)
- [ ] `_DEFAULT_TIMEOUTS["codex"] = 600.0`
- [ ] 1회 재시도 로직
- [ ] `create_staging_directory` → `prepare` + `finalize` 2단계 분리
- [ ] `deep_research_service.py` 3단계 호출 재배치
- [ ] SSE phase 이벤트 이름 변경
- [ ] 관련 테스트 갱신
- [ ] `pytest backend/tests/test_deep_research_collector.py` 통과
- [ ] `pytest backend/tests/test_deep_research_service.py` 통과

**검증 결과**: (Step 완료 시 기재)

---

## Step 4 — Fast Mode Codex 전환

- [ ] `stream_codex_fast` 함수 신규
- [ ] 30초 단위 heartbeat 구현
- [ ] markdown 청크 분할 스트리밍
- [ ] `stream_perplexity` 제거
- [ ] 라우터에서 `codex` 바이너리 체크 추가
- [ ] `test_ai_report_service.py` 갱신
- [ ] `test_ai_report_router_deep_mode.py` Codex stub 교체
- [ ] 모든 테스트 통과

**검증 결과**: (Step 완료 시 기재)

---

## Step 5 — Perplexity 자산 완전 제거

- [ ] `backend/services/perplexity_cache.py` 삭제
- [ ] `backend/prompts/perplexity_prompt.md` 삭제
- [ ] `ai_report_service.py` 의 `SYSTEM_PROMPT`, `SEARCH_DOMAIN_FILTER`, `load_prompt`, `_load_prompt_template` 제거
- [ ] `.env` / `.env.example` 에서 `PERPLEXITY_API_KEY` 제거
- [ ] `grep -ri "perplexity" backend/ --include="*.py"` 결과 없음
- [ ] pytest 전체 통과

**검증 결과**: (Step 완료 시 기재)

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
