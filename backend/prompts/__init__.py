"""AI 리포트 프롬프트 패키지.

이 패키지는 SPEC-AI-REPORT-003 의 Codex CLI 시스템 자산을 보관합니다.

파일 목록:
- codex_prompt.md: Codex CLI 호출용 사용자 프롬프트 (Fast Mode + Deep Mode 공용)
  - `〈종목명〉` / `〈종목코드〉` 플레이스홀더 필수
  - `codex_cli_runner.load_codex_prompt()` 가 런타임에 치환
- stock_synthesis_prompt.md: Deep Research 최종 합성 시스템 프롬프트 (Claude CLI)

canonical 경로이며 변경 시 코드 리뷰 필수.
"""
