> **⚠️ 폐기됨 (2026-04-23)** — V2 는 Deep Mode 한정 대체 + Perplexity Enhanced fallback 을 전제했으나,
> 사용자 최종 의사결정에 따라 **Fast + Deep 전체 완전 대체 + Perplexity 완전 제거** 방향으로 승격됨.
> 현재 활성 계획: [`plan-v3-complete-codex-replacement.md`](./plan-v3-complete-codex-replacement.md).
> V2 내용은 히스토리 참조용으로만 보존.

# Plan V2 — Perplexity → Codex 전환 (Deep Mode 한정) — 폐기됨

기존 `plan.md` 는 Tavily → Codex 대체였으나, 비교 측정 결과 **Perplexity가 최종 리포트 품질에 더 큰 영향**을 준다는 것이 확인됨 (`comparison-samsungsdi-2026-04-23.md` 참조). Plan V2는 Perplexity 대체 전략이다.

> V1 (plan.md) 과의 관계: V1 을 **폐기하지 않고 보류**. Perplexity 개선이 실패하거나 Codex 도입이 결정되면 V2 가 V1 을 대체. Perplexity Payload 강화(옵션 C)만으로 충분하면 V1/V2 둘 다 불필요.

## Context

`perplexity-usage-analysis.md` 에서 상세히 분석한 바 대로:

- Perplexity 는 Fast Mode (풍부한 payload, 스트리밍 UX) + Deep Mode (빈약한 payload, 병렬 수집) 두 경로로 쓰인다.
- Fast Mode 는 `search_context_size: high` + system prompt + recency filter + domain filter + related_questions 모두 활성화.
- Deep Mode 는 이 중 **아무것도 안 씀** — 단순 쿼리 `"{stock_name}({code}) 한국 주식 스윙 트레이딩 분석"` 만 전송.
- 시나리오 C 캐시 덕분에 Fast → Deep 순서의 정상 흐름에서는 빈약 호출이 스킵됨. 그러나 캐시 miss 시 (Fast 없이 Deep 직행, 10분 경과) 빈약 호출로 품질 저하.

본 Plan V2 의 목적은 **Deep Mode 의 Perplexity 슬롯을 Codex 로 대체**하는 것. Fast Mode 는 건드리지 않는다.

## 결정 요약

| 항목 | 결정 |
|---|---|
| 대체 범위 | **Deep Mode 의 `_collect_perplexity` 만** — Fast Mode 는 유지 |
| 파일 포맷 | `sources/perplexity.md` → `sources/codex_research.md` 로 **이름 변경** |
| Fast→Deep 시나리오 C 캐시 | **별도 관리** — Perplexity 캐시는 기존대로 유지, Codex 결과는 별도 캐시 |
| 타임아웃 | **600초** (이전 비교 실측 9분 관측) |
| Fallback | **Perplexity Deep (빈약) 그대로 유지** — Codex 실패 시 폴백 |
| Rate Limit | Codex 전용 카운터 추가 (`AI_REPORT_CODEX_DAILY_QUOTA=15`, `AI_REPORT_CODEX_BURST_LIMIT=1`) |
| SPEC 번호 | `SPEC-AI-REPORT-003` 신규 발행 (V1 과 별개 SPEC) |

## 선결 검증 (옵션 C 우선 시도)

본 Plan V2 착수 전에 **옵션 C (Perplexity Deep payload 강화)** 가 목표 품질에 도달하는지 먼저 검증한다. 방법:

```
deep_research_collector.py::_collect_perplexity 의 payload 를
ai_report_service.py::stream_perplexity 와 동일하게 변경하되 stream=False:
  - "web_search_options": {"search_context_size": "high"}
  - "search_recency_filter": "month"
  - "search_domain_filter": SEARCH_DOMAIN_FILTER
  - "return_related_questions": True
  - "temperature": 0.2
  - "max_tokens": 12000
  - "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": load_prompt(stock_name)}]
```

**합격 기준 (옵션 C)**:
- 현재가 정확도 ≥ 실제 ±5%
- 최근 7일 주요 이벤트 (±5% 이상 등락) 80% 이상 포착
- 1차 공식 소스 ≥ 50% (DART/KRX/주요 일간지)
- 스윙 매매 구간이 실제 현재가와 정합

합격하면 옵션 C 채택, Plan V2 폐기. 불합격하면 Plan V2 진행.

## Recommended Approach (옵션 B 상세)

### 아키텍처

```
Deep Mode 병렬 수집:
  기존: [perplexity_빈약, brave, tavily, naver, youtube]
  변경: [codex_research, brave, tavily, naver, youtube]
                 ↑ 실패 시 순차 fallback
                 perplexity_enhanced (옵션 C payload)
```

### 핵심 차이 (plan.md V1 대비)

| 항목 | V1 (Tavily→Codex) | V2 (Perplexity→Codex) |
|---|---|---|
| 제거 대상 | Tavily | Perplexity Deep Mode |
| 유지 대상 | Perplexity (그대로) | Tavily (그대로) |
| Fallback | Tavily 유지 (실패 시 복귀) | Perplexity Enhanced (강화 payload) |
| Fast Mode 영향 | 없음 | 없음 (명시적으로 분리) |
| 시나리오 C 캐시 | 영향 없음 | **구조 변경** — 아래 §시나리오 C 재설계 |
| 합성 프롬프트 영향 | tavily.json → codex_research.md | perplexity.md → codex_research.md (더 큰 영향) |

### 주요 파일 변경 (수정 범위)

#### 신규 (V1 과 공용)
- `backend/services/codex_cli_runner.py` — 단일 `run_codex_research()` 어댑터 (V1 스펙 그대로)
- `backend/tests/test_codex_cli_runner.py`
- `backend/services/codex_cache.py` — Codex 결과 별도 캐시 (Perplexity 캐시와 독립)

#### 수정
- `backend/services/deep_research_collector.py`
  - `_collect_codex()` 신설 (V1 과 같음)
  - `_collect_perplexity()` 를 `_collect_perplexity_enhanced()` 로 이름 바꾸고 payload 강화 — **fallback 전용**
  - `SOURCE_NAMES`: `"perplexity"` → `"codex_research"`
  - `_DEFAULT_TIMEOUTS`: `"codex_research": 600.0` 추가, `"perplexity": 120.0` 유지 (fallback 용)
  - `collect_all_sources()`: Codex 실패 시 Perplexity Enhanced 호출로 폴백
  - `create_staging_directory()` → `prepare_staging_directory()` + `finalize_staging_directory()` 분리 (V1 과 같음)
- `backend/services/deep_research_service.py`
  - user_prompt 파일 명시 변경
  - SSE phase 이벤트 (`perplexity` → `codex_research`)
  - `source_fallback` 이벤트 추가
- `backend/prompts/stock_synthesis_prompt.md`
  - `sources/perplexity.md` → `sources/codex_research.md` (조건부: 둘 다 존재 시 codex 우선)
- `frontend/src/types/aiReport.ts`
  - `SourceName` 유니언 업데이트
- `backend/services/ai_report_service.py` (Fast Mode)
  - **변경 없음** (명시적으로 분리)
- `backend/services/perplexity_cache.py`
  - **변경 없음** — Fast Mode 의 캐시 구조 그대로

#### 테스트
- V1 의 `test_codex_cli_runner.py` 재사용
- `test_deep_research_collector.py`:
  - 기존 `test_collect_perplexity*` → `test_collect_perplexity_enhanced*` 로 이름 변경 (fallback 경로 커버)
  - `test_collect_codex_success`, `test_collect_codex_fallback_to_perplexity_enhanced` 신규
  - `test_fast_mode_cache_unaffected` — Fast Mode 캐시가 Deep Mode 전환 영향 없음을 검증

### 시나리오 C 캐시 재설계

**문제**: 기존 시나리오 C 는 Fast Mode Perplexity markdown 을 Deep Mode Perplexity 슬롯에 재사용. 이제 Deep Mode 슬롯은 Codex. 서로 다른 포맷·출처의 결과가 같은 슬롯을 공유하면 Claude 합성 시 혼란.

**해결안 1 (권장)**: Fast Mode 캐시는 Perplexity 전용으로 유지. Codex 는 자체 캐시 사용. Deep Mode 진입 시 분기:

```python
async def collect_all_sources(...):
    # Codex 호출 전 Codex 캐시 확인
    codex_cached = codex_cache.get(code)
    if codex_cached:
        codex_result = SourceResult(name="codex_research", success=True, cached=True, data=codex_cached)
    else:
        codex_result = await _collect_codex(...)
        if codex_result.success:
            codex_cache.put(code, codex_result.data)
    
    # Fallback 시: Perplexity Fast Mode 캐시 확인
    if not codex_result.success:
        perp_cached = perplexity_cache.get(code)
        if perp_cached:
            codex_result = _wrap_perplexity_as_codex_slot(perp_cached)
        else:
            perp_enhanced = await _collect_perplexity_enhanced(...)
            codex_result = _wrap_perplexity_as_codex_slot(perp_enhanced)
```

**시사점**:
- Fast → Deep 직후 (10분 내): Perplexity 캐시가 있으므로 Codex 실패 시 즉시 Perplexity 캐시로 대체 (HTTP 호출 없음)
- Codex 성공 시: 자체 캐시 TTL 600초 → 같은 종목 반복 호출 시 비용 절감
- Fast 없이 Deep 직행: Codex 1회 호출 또는 Perplexity Enhanced 1회 호출

**해결안 2**: Fast Mode 도 Codex 로 이전 (옵션 A) — 비권장 (UX 손실).

### Codex Rate Limit

`ai_report_service.py::check_rate_limit()` 패턴을 복제해 `codex_rate_limiter.py` 신규 모듈:

```python
AI_REPORT_CODEX_DAILY_QUOTA = int(os.environ.get("AI_REPORT_CODEX_DAILY_QUOTA", "10"))
AI_REPORT_CODEX_BURST_LIMIT = int(os.environ.get("AI_REPORT_CODEX_BURST_LIMIT", "1"))
```

Codex 는 ChatGPT 구독 쿼터 차감이라 비용 측정 불가 → 더 보수적 한도. 초기 배포 시 10/day.

### 구현 단계 (Step 1 ~ 8)

1. **Step 1 — Codex 어댑터 단독 구축** (V1 과 같음)
2. **Step 2 — Codex 캐시 모듈** (`codex_cache.py` 신규)
3. **Step 3 — Perplexity Enhanced Fallback 구현** (`_collect_perplexity_enhanced`)
4. **Step 4 — Staging 2단계 리팩터링** (V1 과 같음)
5. **Step 5 — 소스 슬롯 교체 + Fallback 로직**
6. **Step 6 — 합성 프롬프트 + SSE 이벤트**
7. **Step 7 — 프론트엔드 라벨 변경**
8. **Step 8 — End-to-end 스모크**
   - Codex 정상 경로
   - Codex 실패 + Perplexity Enhanced 성공
   - Codex 실패 + Perplexity Enhanced 실패 (게이트 차단 확인)

### Risks & Open Questions

1. **ChatGPT 쿼터 차감 불투명성** (가장 큰 리스크) — 초기 10/day 로 시작, 1주일 모니터링 후 상향/하향.
2. **Codex 응답 시간 변동성** — 9분까지 관측. 600초 타임아웃으로도 부족할 경우 800초 상향 가능성.
3. **Fast Mode 캐시 호환성** — Fallback 시 Perplexity markdown 을 `codex_research.md` 파일명으로 저장. Claude 합성 프롬프트가 "내용 포맷"에 의존하지 않는다면 OK. 의존 시 통합 스키마 정의 필요.
4. **Perplexity Enhanced 의 실제 품질** — 선결 검증 결과 (§ 선결 검증) 에 따라 Plan 자체가 폐기될 수 있음.

### Verification (Plan V2 승인 후)

```bash
# 선결 검증 (옵션 C 품질 측정) — 먼저 수행
cd /tmp && mkdir -p perp_enhanced_smoke && cd perp_enhanced_smoke
# Perplexity Enhanced payload 로 호출
python3 call_perp_enhanced.py 006400 삼성SDI > perp_enhanced.json
# 품질 기준 (위 §선결 검증 '합격 기준') 충족 여부 평가

# 합격 시: Plan V2 폐기, 옵션 C 만 적용
# 불합격 시: 아래 Plan V2 착수

# Plan V2 실 통합 스모크
curl -N "http://localhost:8000/api/ai-report/006400?mode=deep"
# SSE 이벤트에서 codex_research phase 확인
# 성공 시 sources/codex_research.md 생성 확인

# Fallback 스모크
PATH=/tmp/empty:$PATH uvicorn backend.main:app --reload
curl -N "http://localhost:8000/api/ai-report/006400?mode=deep"
# source_fallback 이벤트 + Perplexity Enhanced 호출 확인
```

---

## 결정 플로우 차트

```
[시작]
  │
  ▼
[Perplexity Deep 가 품질 문제?] ── NO → [현상 유지, 두 Plan 모두 폐기]
  │ YES
  ▼
[옵션 C Payload 강화로 충분?] ── YES → [옵션 C 채택, Plan V1/V2 폐기]
  │ NO
  ▼
[Tavily 품질 문제가 Perplexity 보다 큰가?] ── YES → [Plan V1 착수]
  │ NO
  ▼
[Plan V2 착수]
```

## 비교 재실시 결과 반영 예정

`comparison-samsungsdi-2026-04-23.md` 갱신 시 3-way 비교 결과 포함:
- Perplexity Deep (현재, 빈약 payload) — 이미 측정됨 (품질 낮음)
- Perplexity Enhanced (옵션 C 적용) — 본 문서 작성 시점 측정 중
- Codex Deep (plan V1 구조화 프롬프트) — 이미 측정됨 (품질 높음)

3-way 결과가 나와야 최종 옵션 선택 가능.
