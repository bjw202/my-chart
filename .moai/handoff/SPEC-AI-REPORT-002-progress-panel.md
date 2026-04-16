# SPEC-AI-REPORT-002 다음 세션 인계 — 진행 상태 패널 (Progress Panel)

**작성일**: 2026-04-16
**작성 시점 commit**: `f119302` (v1.0.3)
**다음 세션이 이어갈 작업**: 심층 분석 진행 중 5-소스 + 합성 단계의 실시간 상태를 사용자에게 시각화

---

## 0. 빠른 컨텍스트 복원

### 현재 SPEC-AI-REPORT-002 상태 (v1.0.3까지 완료)

| 버전 | commit | 핵심 변경 |
|---|---|---|
| 1.0.0 (Phase A-E) | `55f0b7c` ~ `4714c8d` | 5-소스 병렬 수집 + Claude CLI 헤드리스 합성 + 프론트 토글 |
| 1.0.1 | `293ba55` | Claude CLI timeout 180s → 600s |
| 1.0.2 | `da15772` | Naver/YouTube query에 종목 코드 추가, 학습 데이터 면책 차단 |
| 1.0.3 | `f119302` | AI 버튼 즉시 시작 X → idle 상태 모달 + "분석 시작" 버튼, Perplexity 캐시 재사용 (시나리오 C) |

### 검증된 흐름 (실측)

- **빠른 분석** (Perplexity 단일): 47-90초, 22.9KB 마크다운, done 정상
- **심층 분석** (5소스 + Claude CLI): 3분-4분, 10-15KB 마크다운, done 정상
- **시나리오 C** (빠른 → 심층): cache hit 시 Perplexity HTTP 호출 0초 (코드 통과 + 회귀 OK, 실측 INFO 로그 가시화는 다음 단계)
- **회귀**: backend 125 + frontend 203 = 328 tests 모두 통과

---

## 1. 다음 세션 미션

**사용자 인용**:
> "심층분석할 때, 단순히 기다리는 것이 아니라 각 서치가 진행중인지 완료되었는지, 어떤 단계에 있는지 보여주는게 가능한가? claude code를 호출할 때는 아마 스트리밍이 안 될텐데 상관없다."

→ **심층 분석 SSE에 per-source phase 이벤트를 세분화하고 프론트에 진행 상태 패널을 추가한다.**

**핵심 사실 (사용자가 별도 질문해서 확인됨)**:
- 5개 검색 API는 `asyncio.gather`로 **완전 병렬** 진행 중
- 가장 느린 Perplexity(약 14초)가 전체 collecting 단계의 critical path
- Brave/Naver/YouTube는 1초 미만, Tavily는 1초 미만~수초
- `asyncio.gather`는 모든 task가 끝나야 다음으로 진행

---

## 2. 설계 (이미 사용자에게 제시 + 구두 동의 단계)

### Backend (deep_research_service + collector)

현재 phase 이벤트(3단계: collecting/staging/synthesizing)를 **소스별 + 합성 세분화**로 확장:

```jsonc
// 5개 동시 시작
event: phase
data: {"phase":"source_start", "source":"perplexity"}
event: phase
data: {"phase":"source_start", "source":"brave"}
... (5개 모두)

// 완료 순서대로 (빠른 것부터: Brave → Naver → YouTube → Tavily → Perplexity)
event: phase
data: {"phase":"source_done", "source":"brave", "success":true, "duration_ms":519, "count":18}
... (5개)

// 캐시 hit 케이스 (시나리오 C)
event: phase
data: {"phase":"source_done", "source":"perplexity", "success":true, "duration_ms":0, "count":1345, "cached":true}

// 전체 수집 완료
event: phase
data: {"phase":"collecting_done", "successful":5, "total":5}

// 스테이징
event: phase
data: {"phase":"staging_done"}

// 합성 시작
event: phase
data: {"phase":"synthesis_start", "model":"sonnet"}

// Claude 첫 청크 도착 (스트리밍 시작 시점 표시)
event: phase
data: {"phase":"synthesis_first_chunk"}

// 마크다운 청크 (기존)
data: <청크>
data: <청크>
...

// 완료
event: done
data: 
```

### Frontend (AiReportModal)

`status === 'streaming'`일 때 본문 위에 진행 상태 패널:

```
┌─ 🔄 분석 진행 상황 ───────────────┐
│ ✅ Perplexity   519ms / 1.3KB    │
│ ⏳ Brave        진행 중...        │
│ ✅ Tavily       910ms / 13.7KB   │
│ ✅ Naver        339ms / 10건     │
│ ⏳ YouTube      진행 중...        │
│ ─────────────────────────────────│
│ 🤖 Claude 합성 (Sonnet)          │
│   ⏳ 5개 소스 분석 중...          │
└──────────────────────────────────┘

[합성 본문이 도착하면 패널 유지 + 본문은 패널 아래 표시]
```

캐시 hit 시: `✅ Perplexity (캐시 재사용, 0ms)`

---

## 3. 구현 영향 파일 (예상)

| 파일 | 변경 내용 |
|---|---|
| `backend/services/deep_research_collector.py` | `_collect_one_source(name, code, stock_name, *, client, timeout)` helper 추출 — name 인자로 source 분기 + cache 처리 통합 |
| `backend/services/deep_research_service.py` | `asyncio.gather` → `asyncio.as_completed` 패턴 변경. 각 source 시작/완료마다 phase event yield. 합성 첫 청크 도착 시 synthesis_first_chunk yield |
| `frontend/src/api/aiReport.ts` | `createAiReportStream`에 `onPhase(phaseData: object) => void` 콜백 옵션 추가 (기존 콜백과 호환). SSE `event: phase` 라인 파싱 후 콜백 호출 |
| `frontend/src/hooks/useAiReport.ts` | progress state 추가: `progress: { sources: {[name]: SourceProgress}, synthesis: SynthesisProgress }` |
| `frontend/src/components/AiReportModal.tsx` | streaming 상태에서 진행 상태 패널 렌더 (`<ProgressPanel progress={progress} />`) |
| `frontend/src/components/ProgressPanel.tsx` (신규) | 5소스 + 합성 단계 시각화 컴포넌트 |
| `frontend/src/styles/global.css` | `.ai-report-progress-panel`, `.ai-report-progress-source`, `.ai-report-progress-source--done`, `.ai-report-progress-source--running` 등 |
| `frontend/src/components/__tests__/AiReportModal.test.tsx` | progress 패널 렌더 + phase event 처리 테스트 추가 |

---

## 4. 구현 시나리오 단계별 절차

### Step 1: Backend per-source phase events (~30분)

1. `_collect_one_source(source_name, code, stock_name, *, client, timeout)` 함수를 collector.py에 추가
   - source_name 으로 dispatch ("perplexity"/"brave"/"tavily"/"naver"/"youtube")
   - 기존 `_collect_<source>` 함수들을 내부 호출
   - cache check도 이 함수 안에서 (perplexity만)
2. `stream_deep_analysis`를 `asyncio.as_completed`로 재작성
   - 5개 task 생성, source_start phase event yield
   - `as_completed`로 완료 순서대로 받아서 source_done phase event yield (success/duration_ms/count/cached)
   - 모두 끝나면 collecting_done yield
3. staging_done, synthesis_start, synthesis_first_chunk phase event 추가
4. 회귀: `pytest backend/tests/test_deep_research_service.py -v`

### Step 2: Frontend SSE phase 파싱 (~15분)

1. `createAiReportStream`에 `onPhase` 콜백 옵션 추가
2. EventSource 또는 fetch streaming의 `event: phase` 라인 파싱 (지금은 silent ignore)
3. `data:` 의 JSON 파싱 후 `onPhase(parsedData)` 호출

### Step 3: useAiReport progress state (~15분)

1. `progress` state 추가: 5소스 dict + synthesis 객체
2. `onPhase` 콜백에서 phase 종류별로 state 갱신
3. `progress`를 return value에 추가

### Step 4: ProgressPanel 컴포넌트 (~20분)

1. `<ProgressPanel sources={...} synthesis={...} />` 신규 컴포넌트
2. 각 소스: 아이콘 (✅/⏳/❌) + 이름 + duration + count
3. 합성: 모델 + 첫 청크 도착 여부
4. 캐시 hit 표시

### Step 5: AiReportModal 통합 (~10분)

1. `streaming` 상태에서 `<ProgressPanel>` 렌더 (본문 위)
2. `done` 상태에서도 패널 유지 (참고용)

### Step 6: vitest 테스트 추가 (~15분)

- ProgressPanel 단위 테스트 (5소스 모두 OK / 일부 FAIL / 캐시 hit 시나리오)
- useAiReport phase 처리 테스트

### Step 7: 실제 검증 + commit (~15분)

- 백엔드 재시작 + curl로 우리로(046970) deep mode 호출
- SSE 라인에 `event: phase data: {"phase":"source_..."}` 모두 포함 확인
- Playwright e2e (선택)
- v1.0.4로 commit

**총 예상 시간**: 2시간 (테스트 포함)

---

## 5. 주의사항 및 함정

### 5.1 `asyncio.as_completed`의 함정

- `as_completed`가 yield하는 future 결과는 **실제 task가 완료된 시점의 결과**
- 그러나 `as_completed`는 yield 순서가 완료 순서이지만, **task 자체는 이미 완료된 상태로 받음**
- 이 task 결과를 SSE phase event로 변환해야 함

### 5.2 SourceResult duration_ms 값 활용

- 기존 `SourceResult.duration_ms` 필드가 이미 측정됨
- phase event에 그대로 사용 가능 (`source_done`의 `duration_ms` 필드)

### 5.3 캐시 hit 표시 (사용자가 기대하는 핵심 가치)

- `_collect_perplexity`에서 cache hit 시 `data` 안에 `cached: True` 플래그 추가
- 또는 SourceResult에 새 필드 `cached: bool = False` 추가
- phase event의 `cached` 필드로 전달 → 프론트에서 "캐시 재사용" 표시

### 5.4 동시 시작 vs 순차 표시

- 기술적으로 5개 source는 동시 시작이지만, SSE는 순차 yield
- `source_start`를 5개 한꺼번에 yield 후 `as_completed`로 완료 순서대로 yield
- 이 순서가 SSE에 그대로 반영됨

### 5.5 `event: phase`의 SSE 호환성

- 기존 코드 (이전 v1.0.0~v1.0.3)는 phase 이벤트를 silent ignore
- 새 frontend code는 phase 이벤트를 적극 처리
- 백엔드만 업그레이드하면 기존 frontend는 그냥 무시 → 호환성 OK

### 5.6 합성 단계 진행 표시 한계

- Claude CLI stream-json은 `type=assistant` 청크만 옴 (도구 사용 정보는 일부 있지만 "5개 파일 중 3번째 읽는 중" 같은 세부 정보 없음)
- 따라서 합성 단계는 "synthesis_start" + "synthesis_first_chunk" + (이후 청크 갯수 카운트 또는 elapsed time) 정도가 한계
- 사용자는 "claude code를 호출할 때는 아마 스트리밍이 안 될텐데 상관없다"고 명시 → 단순 spinner + 경과 시간으로 OK

### 5.7 backend INFO 로그 가시화 (별도 sub-task)

- 현재 `logger.info`가 uvicorn root logger에서 안 보임
- `backend/main.py`에 1줄 추가:
  ```python
  logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
  ```
- 이걸 추가하면 perplexity_cache HIT/MISS, source 수집 duration 등 모든 진단 로그 가시화

---

## 6. 사용자 미답변 옵션 (다음 세션에서 다시 묻기)

마지막에 사용자에게 옵션 4개를 제시했으나 사용자는 "검색이 병렬인가?"만 묻고 옵션 선택 안 함:

| 옵션 | 설명 | 추천도 |
|---|---|---|
| 1. **풀 패널 + 백엔드 + 프론트 동시** (~30-40분) | 5소스 상태 표 + 합성 단계 아이콘 + cache hit 표시 | ★★★★★ |
| 2. **백엔드만 먼저** (~20분) | phase event만 세분화, 프론트 패널은 다음 턴 | ★★★ |
| 3. **간소화: 한 줄 자동 업데이트 타이핑** (~15분) | "Brave 완료 · Tavily 진행 중 · Perplexity 대기..." | ★★ |
| 4. **다른 우선 이슈** | 진행 상태 패널 보류 | ★ |

→ 다음 세션에서 사용자에게 다시 옵션 1-3 중 선택을 받아 진행 권장.

---

## 7. 검증 방법

### Backend 단독 검증

```bash
# 회귀
source .venv/bin/activate && pytest backend/tests -v --ignore=backend/tests/test_sector_detail_service.py --tb=line -q

# Deep mode SSE 호출 (phase 이벤트 시퀀스 확인)
curl -sS -m 700 -N -X POST "http://127.0.0.1:8000/api/ai-report/010170?mode=deep" | grep "^event: phase\|^data: {.*phase"
```

기대 출력:
```
event: phase
data: {"phase":"source_start","source":"perplexity"}
event: phase
data: {"phase":"source_start","source":"brave"}
... (5개)
event: phase
data: {"phase":"source_done","source":"brave","success":true,"duration_ms":519,"count":18}
... (5개)
event: phase
data: {"phase":"collecting_done","successful":5,"total":5}
event: phase
data: {"phase":"staging_done"}
event: phase
data: {"phase":"synthesis_start","model":"sonnet"}
event: phase
data: {"phase":"synthesis_first_chunk"}
data: # 우리로(010170) 딥 리서치 ...
... (마크다운 청크)
event: done
```

### 시나리오 C 검증

1. 같은 종목으로 빠른분석 1회 → 캐시 저장
2. 즉시 (10분 내) 같은 종목 deep 호출
3. SSE에서 `source_done` perplexity의 `cached: true` + `duration_ms: 0` 확인

### 프론트 검증

- 브라우저에서 `:5173` 접속 → 검색 → AI 버튼 → 심층 분석 시작
- 모달 본문 위에 5소스 상태 패널 표시 확인
- Brave/Naver/YouTube가 ✅로 빠르게 전환되고 Perplexity가 마지막에 ✅
- 합성 단계 아이콘 → 첫 청크 도착 시 본문 표시

### Playwright e2e (선택)

- 기존 `frontend/e2e/ai-report-deep.spec.ts`에 새 케이스 추가
- ProgressPanel locator 검증 + phase 이벤트 시퀀스 처리 검증

---

## 8. 관련 파일 (다음 세션 빠른 진입용)

### 핵심 코드
- `backend/services/deep_research_collector.py` (5-소스 수집, 800줄)
- `backend/services/deep_research_service.py` (오케스트레이션, 320줄)
- `backend/services/perplexity_cache.py` (TTL 캐시, 70줄, v1.0.3 신규)
- `backend/services/claude_cli_streamer.py` (CLI subprocess, 230줄)
- `backend/routers/ai_report.py` (라우터 + cache.put, 250줄)
- `frontend/src/components/AiReportModal.tsx` (모달, 280줄)
- `frontend/src/hooks/useAiReport.ts` (SSE 훅, 125줄)
- `frontend/src/api/aiReport.ts` (SSE 클라이언트)
- `frontend/src/components/ChartGrid/ChartCell.tsx` (AI 버튼 트리거, ~440줄)

### SPEC 문서
- `.moai/specs/SPEC-AI-REPORT-002/spec.md` (v1.0.1 반영)
- `.moai/specs/SPEC-AI-REPORT-002/plan.md` (Phase A-E 원본 계획)
- `.moai/specs/SPEC-AI-REPORT-002/acceptance.md` (18개 AC)
- `.moai/specs/SPEC-AI-REPORT-002/progress.md` (run-phase 기록)

### 인계 문서 (이 파일)
- `.moai/handoff/SPEC-AI-REPORT-002-progress-panel.md` ← **이 문서**

---

## 9. 부록: 사용자가 별도로 평가한 리포트 품질 보고

리포트 `backend/reports/대한광통신/2026-04-16_5.md` (14.7KB) 평가:
- **종합 95/100 (A)** — 매우 우수
- 강점: 도메인 깊이, 교차 검증 라벨, 비판적 시각, 한계 인식
- 약점: Executive Summary 표 변형(spec은 서술형 200-300자), 거래량 5/7건 미공개

### 프롬프트 업그레이드 8개 제안 (다음 세션에서 별도 진행 가능)

1. Executive Summary: 표 + 서술 200-300자 둘 다 강제
2. 데이터 추출 강제 규칙 (거래량/가격 grep 시도)
3. Bull/Base/Bear 시나리오 표 강제
4. 신규 섹션: "7. 트레이더 액션 가이드 (정보성)"
5. 소스 간 불일치 처리 규칙 (이미 자체 도입한 것을 spec에 명시)
6. 검증 불가 클레임에 "대체 소스 제안" 컬럼 추가
7. 테크니컬 지표 fallback 추출 강제
8. Perplexity 인용 정책 명확화 (단일출처 표기 시 명시 OK)

ROI 큰 3개: #1, #2, #4

---

## 10. 진행 상태 패널 외 미해결 항목

1. **백엔드 INFO 로그 가시화** — `logging.basicConfig(level=logging.INFO)` 1줄 추가
2. **e2e spec 업데이트** — `frontend/e2e/ai-report-deep.spec.ts`가 자동 시작 흐름을 가정 (v1.0.3에서 명시 시작 버튼으로 변경)
3. **vitest 테스트 추가** — idle 분기 + onStart + 시작 버튼 검증
4. **프롬프트 업그레이드 (위 섹션 9)** — 별도 commit 가능
5. **Tavily payload 정렬** (search.sh 참고) — `include_raw_content: true` 등으로 데이터 풍부도 향상 가능 (선택)

---

## 11. 다음 세션 첫 발화 예시

```
이전 세션에서 SPEC-AI-REPORT-002 v1.0.3까지 완료하고 진행 상태 패널 작업을 인계 문서로 남겼습니다.
.moai/handoff/SPEC-AI-REPORT-002-progress-panel.md 를 읽어 현재 상태를 복원하고,
사용자가 미선택한 옵션 1-3 중 어떤 패치 범위로 진행할지 확인 후 시작하세요.
```

---

**End of Handoff Document**
