# SPEC-AI-REPORT-003 사전 조사

## 조사 요약

Perplexity → Codex 전환 타당성 검증 자료. 2026-04-23 수행.

### 1. Perplexity 활용 방식 (전수 조사)

`codex-transform-plan/perplexity-usage-analysis.md` 의 결론:

**Fast Mode (SPEC-AI-REPORT-001)**:
- `ai_report_service.py::stream_perplexity` — 풍부한 payload
- `search_context_size: high`, `search_recency_filter: month`, `search_domain_filter`, `SYSTEM_PROMPT` 활용
- 실시간 SSE 스트리밍, `<think>` 블록 필터 상태머신
- `perplexity_cache.put()` 으로 TTL 600초 캐시

**Deep Mode (SPEC-AI-REPORT-002)**:
- `deep_research_collector.py::_collect_perplexity` — **빈약한 payload**
- 단순 쿼리 `"{name}({code}) 한국 주식 스윙 트레이딩 분석"` 만 전송
- `search_context_size` 미설정 → 기본 `low`
- 시나리오 C: Fast 캐시 hit 시 HTTP 호출 스킵

**역설**: Fast Mode 가 "빠른 분석" 이면서 실제로는 Deep Mode 보다 풍부한 payload. Deep Mode 는 5-소스 병렬 중 하나라는 관점에서 최소 payload 로 설계됨.

### 2. 품질 측정 (삼성SDI 006400, 2026-04-23 KST)

`codex-transform-plan/comparison-samsungsdi-2026-04-23.md` 의 3-way 결과:

| 변형 | 팩트 포착률 | 응답 크기 | 응답 시간 | 비용 |
|---|---|---|---|---|
| Perplexity Deep (현재) | 8% (1/12) | 1.4 KB | 30s | $0.013/call |
| Perplexity Enhanced (옵션) | 58% (7/12) | 14 KB | 212s | $0.061/call |
| **Codex Deep** | **83% (10/12)** | 5.8 KB | 260s | **$0 (구독)** |

**핵심 오류 (Perplexity Deep)**:
- 현재가 329,000원 보고 (실제 625,000원)
- 매수 25만~26만원 제안 (실제 대비 60% 할인 — 실전 매매 불가)
- 최근 1주일 주요 이벤트 (벤츠 배터리 계약, NH 목표가 상향) 완전 누락
- 원인: `search_context_size: low` 기본값 + 4개월 전 리포트가 주 출처

**Codex 의 강점**:
- 장중 실시간 가격 포착 (시각까지 명시)
- 기술 지표 구체 수치 (RSI 58.098, MACD +27272, MA5~MA200 전체)
- 1차 공식 소스 (삼성SDI IR, 연합뉴스, 파이낸셜뉴스)
- 38회 웹 검색 교차 검증

**Perplexity Enhanced 가 역전하는 영역**:
- NH투자증권 목표가 상향 (+80%) 단독 이벤트 포착 (Codex 누락)
- 구조화된 표 형식 (system prompt 덕분)

### 3. Codex CLI 환경 검증

**설치 확인**:
```
$ which codex
/Users/byunjungwon/.nvm/versions/node/v24.12.0/bin/codex

$ codex --version
codex-cli 0.121.0

$ codex login status
Logged in using ChatGPT
```

**웹 검색 기본 활성**: `codex exec` 호출 시 설정 없이 자동으로 `web_search` 도구 활성화됨. 38회 호출 관측 (2026-04-23 스모크).

**핵심 플래그**:
- `--skip-git-repo-check` — /tmp 스테이징은 git repo 아님
- `--sandbox read-only` — 로컬 FS 수정 차단 (단 `--output-last-message` 경로는 예외)
- `-C <dir>` — cwd 고정
- `-o, --output-last-message <FILE>` — Codex 마지막 답변을 파일에 저장
- `--json` — JSONL 이벤트 (진단용, stderr 로그)
- `--color never` — ANSI 이스케이프 제거

### 4. 기존 인프라 재사용 가능성

`backend/services/claude_cli_streamer.py` 가 이미 Claude CLI 를 subprocess 로 호출하는 완성된 인프라. Codex 에 재사용 가능:

- `asyncio.create_subprocess_exec` 패턴
- `terminate → kill 2단계 정리` (L.110-131)
- `stderr drain` 마지막 N 라인 (L.194-202)
- `asyncio.timeout` 래핑

단, Claude 는 stream-json generator 이고 Codex 는 one-shot 파일 쓰기라 **흐름 제어 구조가 근본적으로 다름**. 일반화된 모듈로 추상화는 과설계. `codex_cli_runner.py` 로 별도 구현 권장.

### 5. 테스트 격리 제약

`test_deep_research_collector.py` 의 `_load_collector_module` 은 `importlib.util.spec_from_file_location` 으로 격리 로드. 이유: `backend/__init__.py` → `chart_service` → `my_chart` 연쇄 import 를 회피.

Codex runner 의 import 경로 설계 시 주의:
- `backend/services/codex_cli_runner.py` 는 `my_chart` 나 `backend.services.*` 에 의존하지 말 것
- `backend/prompts/codex_prompt.md` 로더도 순환 없이 독립적

### 6. 비용·쿼터 모델 차이

| 항목 | Perplexity | Codex |
|---|---|---|
| 과금 모델 | per-call ($0.01~0.06) | ChatGPT 정기구독 무료 |
| 쿼터 | API 결제 한도 | ChatGPT 구독 쿼터 (일 N회 불투명) |
| 통제 방법 | 환경변수 `AI_REPORT_DAILY_QUOTA` | 동일 변수 재정의 (쿼터 보호) |

### 7. 선결 리스크 해소 상태

| 리스크 | 상태 |
|---|---|
| Codex 웹 검색 기본 활성 여부 | ✅ 해소 — 자동 호출 확인 |
| Codex 타임아웃 180s 적정성 | ✅ 해소 — 부족 판명, 600s 로 상향 결정 |
| Codex 인증 상태 | ✅ 해소 — ChatGPT 로그인 완료 |
| 테스트 격리 호환성 | ✅ 해소 — `codex_cli_runner` 독립 모듈로 배치 |
| Perplexity 제거 후 품질 | ✅ 해소 — Codex 팩트 포착률 83% 로 우세 |

### 8. 미해결 리스크 (구현 후 모니터링)

- Codex 샘플링 재현성 (temperature 제어 불가)
- Fast Mode UX 손실 체감 (heartbeat 로 완화)
- ChatGPT 쿼터 소진 이벤트
- Codex 응답 시간 변동성 (2~9분)

---

## 참고 문서

- Plan 상세: `codex-transform-plan/plan-v3-complete-codex-replacement.md`
- Codex CLI 호출 스펙: `codex-transform-plan/codex-cli-reference.md`
- 품질 비교 보고서: `codex-transform-plan/comparison-samsungsdi-2026-04-23.md`
- Perplexity 분석: `codex-transform-plan/perplexity-usage-analysis.md`
- 실측 샘플: `codex-transform-plan/samples/`
