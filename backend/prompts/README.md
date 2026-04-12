# backend/prompts/

AI 리포트 기능(SPEC-AI-REPORT-001)이 사용하는 **시스템 자산(canonical prompt)** 보관소입니다.

## 파일

- **`perplexity_prompt.md`** — Perplexity API `user` role 메시지 템플릿
  - 런타임에 `load_prompt(stock_name)`이 읽어서 `〈종목명〉` 플레이스홀더를 치환
  - 구조: 7단계 스윙 트레이더 리포트 (Executive Summary → 사업본질 → 최신이벤트 → 심리 → 실적/밸류/수급/테크 → Catalyst → 리스크)

## 편집 시 주의사항

이 파일은 **코드가 의존하는 자산**입니다. 다음을 반드시 지키세요:

1. **`〈종목명〉` 플레이스홀더 유지 필수** — 제거 시 서버 시작 실패 (lifespan 검증)
2. **편집은 코드 리뷰 거침** — 프롬프트는 AI 응답 품질을 직접 좌우
3. **버전 변경 시 SPEC HISTORY 업데이트** — `.moai/specs/SPEC-AI-REPORT-001/spec.md`
4. **테스트 실행** — `pytest backend/tests/test_ai_report_service.py`

## docs/ 폴더와의 구분

- `docs/` = 사용자 스크래치. 참고용 문서, 비교 자료 등을 자유롭게 보관
- `backend/prompts/` = **시스템이 런타임에 실제로 사용하는 자산**. 편집 시 영향 평가 필수

이전에는 `docs/perplexity-prompt.md`를 직접 읽었으나, 구조 취약성(런타임 의존, 책임 혼동)으로 v1.1.5부터 이 위치로 이전되었습니다.

## 관련 문서

- SPEC: `.moai/specs/SPEC-AI-REPORT-001/spec.md`
- 구현: `backend/services/ai_report_service.py::load_prompt()`
- 시작 시 검증: `backend/main.py::lifespan()`
