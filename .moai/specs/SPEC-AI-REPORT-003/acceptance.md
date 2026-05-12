# SPEC-AI-REPORT-003 인수 기준 (Acceptance Criteria)

EARS 형식 기반 인수 시나리오. 모든 시나리오는 Given/When/Then 구조로 검증 가능해야 한다.

---

## AC-001: Fast Mode Codex 전환 (FR-001)

**Given** Codex CLI 가 PATH 에 설치되어 있고 `codex login` 인증 완료된 상태
**When** 사용자가 `POST /api/ai-report/005930?mode=fast` 를 호출
**Then** 백엔드가 `stream_codex_fast` 를 실행하고, 30초 간격 heartbeat SSE 이벤트 + 완료 시 markdown 청크 스트리밍이 반환됨

**Given** `mode` 쿼리 파라미터 생략
**When** `POST /api/ai-report/005930` 을 호출
**Then** Fast Mode Codex 파이프라인으로 라우팅됨 (하위 호환성 유지)

---

## AC-002: Deep Mode Codex 슬롯 대체 (FR-002)

**Given** 5개 API 키(BRAVE/TAVILY/NAVER/YOUTUBE) 설정됨, Codex CLI 인증 완료
**When** `POST /api/ai-report/005930?mode=deep` 수신
**Then** `collect_all_sources` 가 `["codex", "brave", "tavily", "naver", "youtube"]` 5개 소스를 병렬 수집, `_collect_codex` 가 Codex subprocess 를 호출

**Given** Deep Mode 수집 완료
**When** 스테이징 디렉터리 검사
**Then** `/tmp/analysis_005930_<uuid>/sources/codex.md` 파일 존재 (`sources/perplexity.md` 부재)

---

## AC-003: 1회 재시도 동작 (FR-003)

**Given** Codex 첫 호출이 `timeout` 실패
**When** `_collect_codex` 가 재시도 분기 진입
**Then** 동일한 프롬프트로 두 번째 Codex subprocess 호출, 성공 시 정상 `SourceResult` 반환

**Given** Codex 두 번째 호출도 실패
**When** 두 번째 시도 완료
**Then** `SourceResult(success=False, error_type=...)` 반환, 추가 재시도 없음

**Given** 첫 호출이 `binary_missing` 실패
**When** 에러 분기 평가
**Then** 재시도하지 않고 즉시 실패 반환 (결정론적 실패)

---

## AC-004: Fast Mode Heartbeat UX (FR-004)

**Given** Fast Mode Codex subprocess 실행 중 (60초 경과)
**When** 사용자 브라우저가 SSE 스트림 수신
**Then** 최소 2개의 `phase` 이벤트 수신됨 (30초 단위, 예: "웹 검색 진행 중", "자료 교차 검증 중")

**Given** Fast Mode Codex 완료
**When** markdown 을 청크로 분할 전송
**Then** 사용자는 완성된 markdown 을 순차 청크로 수신, 완료 시 `done` 이벤트 수신

---

## AC-005: Perplexity 완전 제거 검증 (FR-005, NFR-004)

**Given** 구현 완료 상태
**When** `grep -ri "perplexity" backend/ --include="*.py"` 실행
**Then** 결과 없음 (완전 제거)

**Given** `.env.example` 파일
**When** `grep "PERPLEXITY_API_KEY" .env.example`
**Then** 결과 없음

**Given** 파일 시스템 검사
**When** `ls backend/services/perplexity_cache.py backend/prompts/perplexity_prompt.md`
**Then** 두 파일 모두 존재하지 않음 (완전 삭제)

---

## AC-006: 스테이징 2단계 생성 (FR-006)

**Given** Deep Mode 실행 중
**When** `prepare_staging_directory` 실행 시점
**Then** `/tmp/analysis_<code>_<uuid>/sources/` 디렉터리 존재, `summary.md` 미생성

**Given** 수집 완료 후
**When** `finalize_staging_directory` 실행
**Then** `summary.md` + 성공한 소스 파일(`codex.md`, `brave.json` 등) 모두 생성

---

## AC-007: 합성 프롬프트 갱신 (FR-007)

**Given** 갱신된 `stock_synthesis_prompt.md`
**When** `grep "sources/codex.md" backend/prompts/stock_synthesis_prompt.md`
**Then** 매치 존재 (`sources/perplexity.md` 언급은 없음)

**Given** Deep Mode 실행 완료
**When** Claude CLI 가 합성 수행
**Then** `sources/codex.md` 를 읽고 참조 (로그 또는 최종 리포트에서 [codex] 출처 인용 관찰 가능)

---

## AC-008: 타임아웃 동작 (NFR-001, ER-003)

**Given** Codex subprocess 가 601초 이상 소요
**When** 타임아웃 발생
**Then** `asyncio.TimeoutError` → terminate → kill 순으로 정리, `error_type="timeout"` 반환, 재시도 시작

**Given** 재시도도 600초 초과
**When** 두 번째 타임아웃 발생
**Then** 최종 실패 `SourceResult` 반환, 나머지 4개 소스 성공 여부로 게이트 판정

---

## AC-009: 2개 이상 성공 게이트 (FR-002 from SPEC-002)

**Given** Deep Mode 5 소스 중 Codex 실패 + 나머지 4개 중 2개 이상 성공
**When** `CollectionResult.build()` 실행
**Then** `gate_passed=True`, 리포트 생성 계속 진행

**Given** Codex 만 성공, 나머지 4개 전부 실패
**When** 게이트 판정
**Then** `gate_passed=False`, SSE `error` 이벤트 emit, 합성 중단

---

## AC-010: 프론트엔드 SourceName 갱신 (FR-009)

**Given** 갱신된 `aiReport.ts`
**When** TypeScript 타입 검사 실행
**Then** `SourceName` 유니언에 `"codex"` 포함, `"perplexity"` 미포함

**Given** ProgressPanel 컴포넌트
**When** Deep Mode 진행 중 렌더링
**Then** "Codex 심층 리서치" 라벨 표시 (구 "Perplexity" 표시 없음)

---

## AC-011: 경로 안전 (NFR-003)

**Given** `prepare_staging_directory` 호출
**When** 계산된 경로가 `/tmp/analysis_*` 외부를 가리킴 (예: 심볼릭 링크 등)
**Then** `_BLOCKED_ROOTS` 검사에 걸려 예외 발생

**Given** Codex `--output-last-message` 인자
**When** Codex subprocess 실행
**Then** 경로가 스테이징 디렉터리 내부, `--sandbox read-only` 적용됨

---

## AC-012: 전체 테스트 스위트 통과 (FR-005, NFR-005)

**Given** 모든 변경 적용 완료
**When** `pytest backend/tests/ -v` 실행
**Then** 모든 테스트 통과. 단 아래는 허용:
- 기존 Perplexity 관련 테스트는 Codex 테스트로 교체됨 (삭제 + 신규)
- 기존 my_chart.db 관련 import 에러 2건은 이 SPEC 범위 밖 (사전 존재)

**Given** 신규 Codex 테스트
**When** `test_collect_codex_*`, `test_codex_cli_runner_*` 실행
**Then** Codex runner 어댑터, 1회 재시도, 타임아웃, 빈 출력, 바이너리 미설치 케이스 전부 커버
