# Perplexity API 활용 방식 심층 분석

Perplexity를 Codex로 전환하기 위해 **현재 코드가 Perplexity를 어떻게 쓰고 있는지** 전수 조사한 결과.

## 1. Perplexity는 **두 가지 경로**로 쓰인다

### 1-A. Fast Mode — `ai_report_service.py::stream_perplexity`

SPEC-AI-REPORT-001 기반. 빠른 분석 전용. 사용자가 종목 상세 페이지에서 "AI 분석 (빠름)" 을 누르면 호출됨.

**핵심 특징**:

| 항목 | 값 | 파일:라인 |
|---|---|---|
| Model | `sonar-reasoning-pro` | `ai_report_service.py:245` |
| Streaming | True (SSE) | `:246` |
| Temperature | 0.2 | `:247` |
| Max tokens | 12,000 | `:248` |
| `search_context_size` | **`high`** | `:249-251` |
| `search_recency_filter` | `month` (30일) | `:252` |
| `search_domain_filter` | SNS 최소 블랙리스트 | `:253` (+ `:150-157`) |
| `return_related_questions` | True (multi-pass) | `:254` |
| System prompt | 8원칙 한국 애널리스트 | `:113-140` (SYSTEM_PROMPT) |
| User prompt | `perplexity_prompt.md` 템플릿 | `:217` (load_prompt) |
| `<think>` 필터 | 스트리밍 상태머신 | `:295-340` |
| Timeout | 180초 | `:276` |
| Rate limit | 일일 50 + 분당 3 | `:33-34, 45-92` |
| 캐시 | `perplexity_cache.put(code, markdown)` TTL 600초 | 완료 후 |

### 1-B. Deep Mode — `deep_research_collector.py::_collect_perplexity`

SPEC-AI-REPORT-002 기반. 심층 분석. 5개 병렬 소스 중 하나.

**핵심 특징**:

| 항목 | 값 | 파일:라인 |
|---|---|---|
| Model | `sonar-reasoning-pro` (동일) | `deep_research_collector.py:249` |
| Streaming | **False** | `:252` |
| Query | 하드코딩 단순 쿼리 | `:247` |
| `search_context_size` | **미설정** → 기본 `low` | (없음) |
| `search_recency_filter` | **미설정** | (없음) |
| `search_domain_filter` | **미설정** | (없음) |
| `return_related_questions` | **미설정** → False | (없음) |
| System prompt | **미설정** | (없음) |
| User prompt | 단순 쿼리 | `:247` |
| Timeout | 120초 | `:583` `_DEFAULT_TIMEOUTS` |
| Rate limit | 일일 15 + 분당 1 (별도) | `ai_report_service.py:33` 별개 환경변수 |
| 캐시 | **Fast Mode 캐시에서 읽기만** (시나리오 C) | `:222-235` |

## 2. 두 모드의 핵심 모순

**Fast Mode 쿼리 예시** (풍부):

```
System: (1500자 한국 애널리스트 system prompt)
User: # 한국 상장기업 삼성SDI 스윙 트레이더 리포트
      최우선: 최근 7일 주가 핵심 모멘텀 포착...
      ## 🔥 Executive Summary
      ## 📦 0단계: 사업 본질
      ## ⚙️ 1단계: 최신 이벤트
      ## 💬 2단계: 시장 심리
      ...
옵션: search_context_size=high, recency=month, domain_filter, related_questions
```

**Deep Mode 쿼리 예시** (빈약):

```
User: 삼성SDI(006400) 한국 주식 스윙 트레이딩 분석
옵션: (없음)
```

**결과 품질 차이**:
- Fast Mode: 표·섹션·출처·인과분석 풍부한 1만자 리포트
- Deep Mode: 1,451자 서술형 답변, 가격 단위 오류, 최신 이벤트 누락 (**이전 비교 테스트에서 확인**)

## 3. 시나리오 C — 비용 절감 캐시 파이프라인

`perplexity_cache.py` 의 핵심 로직:

```
사용자 Fast Mode 실행
  → stream_perplexity() 10K자 markdown 생성
  → perplexity_cache.put(code, markdown)  # TTL 600초

(10분 내) 사용자 Deep Mode 실행
  → _collect_perplexity() → perplexity_cache.get(code) HIT
  → HTTP 재호출 스킵, Fast Mode 결과를 Deep Mode 결과로 재사용
  → SourceResult(name="perplexity", success=True, cached=True)
```

즉 **캐시 hit 시 Deep Mode 단독 호출이 실행되지 않음** — 이 경우 Deep Mode의 빈약한 payload 문제는 우회된다.

**캐시 miss 시** (사용자가 Fast 없이 바로 Deep 실행, 또는 10분 경과)에만 빈약한 payload로 실제 호출 발생.

## 4. Claude 합성 프롬프트에서 Perplexity 역할

`backend/prompts/stock_synthesis_prompt.md:12` 참조:

```
- `sources/perplexity.md` — Perplexity AI 분석 (think 블록 제거됨, 인라인 인용 포함)
```

5개 소스 중 **유일한 AI 분석 결과** (나머지는 검색 결과 JSON). Claude 합성 시 "종목 식별" 기준 소스로도 명시됨 (`:33`). 즉 **Perplexity 결과 품질 = 최종 리포트 품질 상한**.

## 5. 산출물 포맷

### Fast Mode

- HTTP 스트리밍 응답 → 사용자 SSE 실시간 수신
- 완료 후 `backend/reports/...` 에 저장
- 메모리 캐시 `_perplexity_full_cache[code]` 저장

### Deep Mode (정상 호출 시)

`deep_research_collector.py:884-900`:

```
sources/perplexity.md:
# Perplexity 분석

{think 블록 제거된 content}

## 출처
- {citation_url_1}
- {citation_url_2}
...
```

JSON이 아니라 Markdown (다른 소스는 JSON). Claude 합성에 용이.

## 6. Rate Limit 이중 구조

- Fast Mode: `AI_REPORT_DAILY_QUOTA=50` + `AI_REPORT_BURST_LIMIT=3/min`
- Deep Mode: `AI_REPORT_DEEP_DAILY_QUOTA=15` + `AI_REPORT_DEEP_BURST_LIMIT=1/min`
- 각 모드 진입 시 `check_rate_limit()` 별도 게이트

## 7. Codex 전환 가능성 평가

### 7-1. 기능 매핑

| Perplexity 기능 | Codex 대응 | 난이도 |
|---|---|---|
| 실시간 SSE 스트리밍 (Fast Mode) | Codex는 non-streaming (`--output-last-message`) | ⚠️ **상** |
| `<think>` CoT 블록 | Codex는 reasoning summaries 기본 숨김 (`--json` 에서만 노출) | 하 (노출 안 됨) |
| `search_context_size: high` | Codex 기본 auto (reasoning effort high 상응) | 하 |
| `search_recency_filter: month` | 프롬프트에 "최근 30일" 명시 | 하 |
| `search_domain_filter` | 프롬프트에 도메인 선호 명시 | 중 (강제력 부족) |
| `return_related_questions` | Codex 기본 multi-pass search | 하 |
| System prompt + User prompt 분리 | Codex는 단일 prompt 인자 | 하 (프롬프트 내 역할 구분) |
| Rate limit 게이트 | Python 쪽에서 그대로 유지 | 하 |
| 10분 캐시 | 이름만 바꿔 동일 구조 | 하 |
| Citations 리스트 | Codex 본문 [n] 각주 → 파싱 후처리 필요 | 중 |
| Markdown 출력 | Codex 네이티브 | 하 |

### 7-2. 본질적 차이

| 차원 | Perplexity | Codex |
|---|---|---|
| 아키텍처 | 검색엔진 + 요약 LLM (특화) | 범용 agent + web_search tool (유연) |
| 응답 모델 | sonar-reasoning-pro | gpt-5.4 |
| Streaming | ✅ 네이티브 SSE | ❌ non-streaming (파일 산출) |
| 응답 시간 | 30-90초 (관찰) | 2-9분 (관찰) |
| 비용 투명성 | ✅ $0.013/call 명시 | ❌ ChatGPT 구독 쿼터 (불투명) |
| 재현성 | ✅ temperature 제어 | ⚠️ 일부 제어 불가 |
| 품질 상한 | 모델 성능 + 검색 품질에 제약 | 더 깊은 reasoning 가능 |

### 7-3. 전환 전략 옵션

| 옵션 | 범위 | 장점 | 단점 | 권장도 |
|---|---|---|---|---|
| **A** | Fast+Deep 전체 대체 | 일관된 아키텍처 | Fast Mode 스트리밍 UX 손실, 수 분 대기 | ❌ 비권장 |
| **B** | Deep Mode만 대체 | UX 유지, Deep 품질 개선 | Fast↔Deep 캐시 호환성 재설계 필요 | ✅ **권장** |
| **C** | Perplexity Deep payload 강화 (비-Codex) | 1줄 변경, 즉효 | Codex 수준 품질 도달 불확실 | ⭕ 선행 검증 |
| **D** | Deep Mode에 Codex 추가 (6개 소스) | 안정성 + 게이트 확률↑ | 시간·비용 최대 | ⚠️ 리소스 부담 |

### 7-4. 옵션 B (권장) 의 세부 설계 과제

1. **캐시 호환성**: Fast Mode는 Perplexity markdown을, Deep Mode는 Codex markdown을 생성 → 두 포맷이 섞이면 합성 품질 불일치. 해결: Fast Mode 캐시 hit 시 그대로 사용, miss 시 Codex 호출 — 두 소스가 같은 `sources/perplexity.md` 슬롯에 저장되지만 출처가 다른 경우가 발생. 또는 캐시 별도화.
2. **스트리밍 호환**: Fast Mode는 계속 Perplexity. Deep Mode만 Codex로 전환 → 스트리밍 UX 영향 없음.
3. **Rate limit 재설계**: Codex는 ChatGPT 구독 쿼터. 현재 환경변수 `AI_REPORT_DEEP_*` 는 Perplexity 기준. Codex용 별도 쿼터 관리 필요.
4. **타임아웃 상향**: Perplexity 120초 → Codex 300-600초 (이전 비교에서 9분 관측).
5. **citations 후처리**: Codex 본문의 `[n]` 각주 + 참고문헌 섹션을 파싱해 `citations` 배열 재구성 — 또는 markdown 그대로 사용하며 citations 배열 비워둠.

### 7-5. 옵션 C 선행 검증 가치

Deep Mode의 Perplexity payload를 Fast Mode 수준으로 강화하면 얼마나 품질이 올라오는가? 이번 A/B 테스트에서 측정. 만약 Codex와 거의 동급이면 Codex 전환 **불필요**하고 옵션 C 를 채택하는 것이 최저비용·최소변경.

## 8. 결론

1. **Deep Mode의 Perplexity 호출이 "빈약"한 건 버그가 아니라 누락된 최적화**. Fast Mode 설계자는 모든 옵션을 활성화했으나 Deep Mode 설계자는 병렬 5-소스 중 하나라는 관점에서 최소 payload만 썼다.
2. **Codex 전환은 Deep Mode 한정 (옵션 B)** 이 현실적. Fast Mode의 실시간 스트리밍 UX는 Codex로 재현 불가.
3. **옵션 C (Payload 강화) 선행 검증이 결정적**. 강화만으로 충분하면 Codex 미도입이 최선.
4. **Perplexity 캐시 시나리오 C는 반드시 보존**. 사용자가 Fast → Deep 순서로 실행하는 일반 흐름에서 비용·시간 절감 구조.

---

**다음 액션**: 옵션 C (Payload 강화) 로 Perplexity 재호출해 품질 측정 → 결과에 따라 옵션 B (Codex 전환) 필요성 판단.
