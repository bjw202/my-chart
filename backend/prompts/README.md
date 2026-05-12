# backend/prompts/

AI 리포트 기능이 사용하는 **시스템 자산(canonical prompt)** 보관소입니다.

## 파일

- **`codex_prompt.md`** — Codex CLI 호출용 프롬프트 (Fast Mode + Deep Mode 공용, SPEC-AI-REPORT-003)
  - 런타임에 `backend.services.codex_cli_runner.load_codex_prompt(code, stock_name)` 이 읽어서
    `〈종목명〉`, `〈종목코드〉` 플레이스홀더를 치환
  - 구조: 8단계 스윙 트레이더 리포트 (Executive Summary → 사업본질 → 최신이벤트 → 심리 → 실적/밸류/수급/테크 → Catalyst → 리스크 → 스윙 진입·청산)
- **`stock_synthesis_prompt.md`** — Deep Research 최종 합성 프롬프트 (Claude CLI system prompt)
  - 런타임에 `deep_research_service._load_synthesis_prompt()` 이 읽음

## 편집 시 주의사항

이 파일들은 **코드가 의존하는 자산**입니다. 다음을 반드시 지키세요:

1. **플레이스홀더 유지 필수** — `codex_prompt.md` 에서 `〈종목명〉` / `〈종목코드〉` 제거 시 서버 시작 실패 (lifespan 검증)
2. **편집은 코드 리뷰 거침** — 프롬프트는 AI 응답 품질을 직접 좌우
3. **버전 변경 시 SPEC HISTORY 업데이트** — `.moai/specs/SPEC-AI-REPORT-003/spec.md`
4. **테스트 실행** — `pytest backend/tests/test_codex_cli_runner.py`

## 관련 문서

- Codex SPEC: `.moai/specs/SPEC-AI-REPORT-003/spec.md`
- 구현: `backend/services/codex_cli_runner.py::load_codex_prompt()`
- 시작 시 검증: `backend/main.py::lifespan()`
