# Codex Transform Plan — Handoff

Perplexity API 를 Codex CLI 로 **완전 대체** 하는 프로젝트. SPEC-AI-REPORT-003 신규 발행 예정. 구현 미시작.

## 사용자 확정 제약 (2026-04-23)

| 제약 | 값 |
| --- | --- |
| **최우선** | 품질 (비용은 무관 — Codex 는 ChatGPT 정기구독 기반 무료) |
| 대체 범위 | **Fast + Deep 양쪽** — Perplexity 완전 제거 |
| Fallback | 없음 + 1회 재시도 |
| SPEC | SPEC-AI-REPORT-003 신규 |
| 작업 방식 | 각 Step 전에 **명시적 승인** 받으며 진행 |

## 현재 상태

- [x] 사용자 의도 재확인 (Socratic interview 2 round)

- [x] Perplexity 통합 구조 심층 분석 → `perplexity-usage-analysis.md`

- [x] Codex CLI 설치 및 플래그 검증 (`codex-cli 0.121.0`)

- [x] 품질 측정 — 3-way 비교 (Perplexity Deep / Enhanced / Codex) → `comparison-samsungsdi-2026-04-23.md`

- [x] Codex 웹 검색 기본 활성 확인

- [x] **Plan V3 확정** → `plan-v3-complete-codex-replacement.md`

- [ ] **Step 1 대기**: SPEC-AI-REPORT-003 문서 작성 (승인 후 manager-spec 위임 또는 직접)

- [ ] **Step 2\~8 대기**: 실 구현 (각 Step 승인 필요)

## 파일 구성

### 활성 문서

- `plan-v3-complete-codex-replacement.md` — **활성 계획** (Perplexity 완전 제거)
- `perplexity-usage-analysis.md` — Perplexity 활용 방식 전수 조사
- `comparison-samsungsdi-2026-04-23.md` — 3-way 품질 비교 실측
- `codex-cli-reference.md` — Codex CLI 호출 스펙·프롬프트·에러 매트릭스

### 보존 문서 (폐기, 히스토리용)

- `plan.md` — **폐기** (V1 Tavily→Codex, 부분 대체 설계)
- `plan-v2-perplexity-migration.md` — **폐기** (V2 Deep 한정 대체, Enhanced fallback 전제)

### 측정 증거

- `samples/codex_sample_006400.md` — Codex 실 출력 (팩트 포착 83%)
- `samples/perplexity_sample_006400.json` — Perplexity Deep 샘플 (팩트 포착 8%, 가격 단위 오류)
- `samples/perplexity_enhanced_sample_006400.md` — Perplexity Enhanced 샘플 (팩트 포착 58%, 참조용 — 비용 역행으로 채택 불가)
- `samples/perplexity_enhanced_citations_006400.json` — Enhanced 메타

## 결정 플로우

```
[Perplexity 를 유지할 이유가 있는가?]
  사용자 결정: NO (비용 + Codex 구독 무료 활용)
       │
       ▼
[Plan V3 — 완전 대체 (Fast + Deep)]
       │
       ▼
[Step 1: SPEC-AI-REPORT-003 문서] ← 현재 승인 대기
```

## 다음 세션 (Step 1) 시작 방법

1. 사용자에게 SPEC-AI-REPORT-003 문서 작성 착수 재승인 요청
2. manager-spec 에이전트 위임 여부 결정 (에이전트가 EARS 형식에 익숙)
3. SPEC 위치 결정: `.moai/specs/SPEC-AI-REPORT-003/` 하위
4. SPEC 내용:
   - EARS 형식 requirements (The system shall...)
   - Acceptance criteria (GIVEN/WHEN/THEN)
   - 전환 범위 (Fast + Deep 양쪽)
   - 제거 대상 명시 (Perplexity 전체)
   - Fallback 전략 (없음 + 1회 재시도)
   - Fast Mode UX 전환 (SSE heartbeat 패턴)
5. 문서 완료 후 Step 2 (Codex CLI runner 어댑터) 승인 요청

## 각 Step 승인 체크리스트 (템플릿)

각 Step 전에 아래 4가지 명시 후 사용자 승인 기다림:

1. **목적**: 이 Step 에서 뭘 달성하는가
2. **수정 파일**: 어떤 파일 몇 개 변경/삭제/신규
3. **리스크**: 회귀 가능성, 외부 영향
4. **검증 방법**: 어떤 테스트로 완료 확인

## 운영 상 주의

### 품질 추적

- Codex 샘플링 재현성 체크 — 동일 종목 2-3회 호출해 가격·이벤트 일관성 확인
- 기술 지표 구체 수치 포착 여부 (Codex 의 강점이 유지되는지)

### 쿼터 모니터링

- Codex 는 무료지만 ChatGPT 구독 일일 한도 내에서. 쿼터 소진 이벤트 로깅 필요.
- `AI_REPORT_DAILY_QUOTA=50` 환경변수는 **쿼터 보호** 목적으로 재정의 (기존 비용 통제 → 쿼터 통제)

### Codex 응답 시간 변동

- 실측 2\~9분. 1회 재시도 포함 시 최악 20분.
- 타임아웃 600초 / 재시도 타임아웃 추가 600초
- Fast Mode SSE heartbeat 패턴으로 UX 보완

## 조사 환경

- 조사 날짜: 2026-04-23
- 현재 브랜치: `feature/SPEC-PRESET-001` (구현 착수 시 새 브랜치 `feature/SPEC-AI-REPORT-003-codex-replacement` 권장)
- Codex CLI: 0.121.0 (ChatGPT 로그인 완료)
- Python: 3.13