# SPEC-AI-REPORT-001: Implementation Plan

## v1.1.0 Enhancement Plan

Perplexity API 품질 개선 (Stage 1: API 파라미터 튜닝 + 시스템 프롬프트 강화)

### Scope

- **수정 대상**: `backend/services/ai_report_service.py` (단일 파일)
- **변경 없음**: Frontend, API routes, 스키마, `docs/perplexity-prompt.md`

### 변경 내역

- **신규 상수 정의**:
  - `SYSTEM_PROMPT`: v1.1.0 시스템 프롬프트 규격 (spec.md 참조)
  - `SEARCH_DOMAIN_FILTER`: 도메인 whitelist 배열 (DART/KRX/일간지/금융포털)
- **Payload 확장 (7개 필드)**:
  - `web_search_options.search_context_size: "high"`
  - `search_recency_filter: "month"`
  - `search_domain_filter: [whitelist]`
  - `return_related_questions: true`
  - `temperature: 0.2`
  - `max_tokens: 8000`
  - system message 추가 (SYSTEM_PROMPT)
- **Timeout 조정**: 120s → 180s (search_context_size=high로 응답 지연 증가 대응)

### 기대 품질

Perplexity Spaces 대비 70-80% 수준 (출처 15개 이상, 서술 문단 풍부, 최신성 월 단위 확보).

### Risk Mitigation

| 리스크 | 완화 방안 |
|-------|----------|
| 도메인 필터가 너무 엄격하여 응답 빈약 | 모니터링 후 v1.1.1에서 whitelist 확장 |
| 응답 시간 증가 (high context size) | Timeout 180s, 프론트엔드 진행 상태 강화 |
| max_tokens 8000 비용 증가 | 단건 호출 제한 (ER-006) 유지로 통제 |

### 마일스톤

**Priority High**: `ai_report_service.py` 상수 추가, payload 확장, timeout 조정, 로컬 테스트 (삼성전자로 출처 15+ 확인).

---

## 기술 접근 방식

### 아키텍처 개요

```
ChartCell [AI Button] → Frontend Hook → POST /api/ai-report/{code}
                                              ↓
                                        Backend Router
                                              ↓
                                    Perplexity API (sonar-pro, stream: true)
                                              ↓
                                    SSE EventSourceResponse → Frontend Modal
                                              ↓ (on complete)
                                    File Save: backend/reports/{종목명}/{날짜}.md
```

### 백엔드 구현

- **Router**: `backend/routers/ai_report.py` - 3개 엔드포인트 정의
- **Service**: `backend/services/ai_report_service.py` - Perplexity API 호출, 파일 저장 로직
- **Schema**: `backend/schemas/ai_report.py` - 응답 모델 정의
- **SSE**: `sse-starlette` 패키지 활용 (이미 프로젝트 의존성에 포함)
- **종목명 조회**: `my_chart.registry` 활용하여 종목코드 → 종목명 변환
- **프롬프트 로드**: `docs/perplexity-prompt.md` 파일 읽기, `〈종목명〉` 치환
- **HTTP Client**: `httpx` (async) 또는 `requests` (sync) 사용하여 Perplexity API 호출

### 프론트엔드 구현

- **Component**: `frontend/src/components/AiReportModal.tsx` - 포탈 기반 풀스크린 모달 (AnalysisModal 패턴 참조)
- **Hook**: `frontend/src/hooks/useAiReport.ts` - SSE 연결, 상태 관리, 히스토리 조회
- **API Client**: `frontend/src/api/aiReport.ts` - API 함수 정의
- **Types**: `frontend/src/types/aiReport.ts` - TypeScript 인터페이스
- **Button**: `ChartCell.tsx`에 AI 버튼 추가 (TR 버튼 뒤)
- **Markdown 렌더링**: `react-markdown` 라이브러리 사용

### 의존성 추가

- Backend: `httpx` (async HTTP client for Perplexity streaming)
- Frontend: `react-markdown` + `remark-gfm` (마크다운 렌더링, 테이블 지원)

## 마일스톤

### Milestone 1: 백엔드 API (Priority High)

- Perplexity API 연동 서비스 구현
- SSE 스트리밍 라우터 구현
- 파일 저장 로직 (경로 생성, 시퀀스 번호 처리)
- 에러 핸들링 (API 키 누락, 종목 코드 무효, 동시 요청 차단)
- 히스토리 조회 / 파일 조회 엔드포인트

### Milestone 2: 프론트엔드 모달 UI (Priority High)

- AiReportModal 컴포넌트 (포탈 기반)
- 탭 UI ("분석 결과" / "히스토리")
- 마크다운 실시간 스트리밍 렌더링
- 로딩 상태 (타이핑 애니메이션)
- 복사 버튼

### Milestone 3: ChartCell 통합 (Priority High)

- AI 버튼 추가 및 스타일링
- 버튼 클릭 → 모달 열기 플로우 연결
- SSE 연결 관리 (모달 닫기 시 abort)

### Milestone 4: 히스토리 기능 (Priority Medium)

- 히스토리 목록 표시
- 저장된 분석 파일 조회 및 렌더링
- 날짜별 정렬

## 리스크

| 리스크 | 영향도 | 완화 방안 |
|--------|--------|-----------|
| Perplexity API 응답 지연 (30초+) | Medium | 타임아웃 설정 (60초), 사용자에게 진행 상태 표시 |
| SSE 연결 중단 | Medium | 프론트엔드에서 에러 감지 및 재시도 버튼 제공 |
| 한글 종목명 파일 경로 이슈 | Low | 파일 시스템 안전 문자 치환 함수 구현 |
| Perplexity API 비용 | Low | 동일 종목 동시 요청 차단 (HTTP 429) |
| 대용량 응답 (10K+ 토큰) | Low | 스트리밍 방식이므로 메모리 이슈 없음 |
| `httpx` 미설치 환경 | Low | `requirements.txt`에 추가, 설치 가이드 문서화 |

## 파일 변경 범위

### 신규 파일

| 파일 | 설명 |
|------|------|
| `backend/routers/ai_report.py` | AI 리포트 API 라우터 |
| `backend/services/ai_report_service.py` | Perplexity API 호출 및 파일 저장 서비스 |
| `backend/schemas/ai_report.py` | 응답 스키마 |
| `frontend/src/components/AiReportModal.tsx` | AI 리포트 모달 컴포넌트 |
| `frontend/src/hooks/useAiReport.ts` | SSE 및 히스토리 훅 |
| `frontend/src/api/aiReport.ts` | API 클라이언트 함수 |
| `frontend/src/types/aiReport.ts` | TypeScript 타입 정의 |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/components/ChartGrid/ChartCell.tsx` | AI 버튼 추가 |
| `frontend/src/styles/global.css` | AI 버튼 및 모달 스타일 |
| `backend/main.py` | ai_report 라우터 등록 |
| `requirements.txt` | `httpx` 추가 |
| `frontend/package.json` | `react-markdown`, `remark-gfm` 추가 |
