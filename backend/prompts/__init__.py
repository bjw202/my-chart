"""AI 리포트 프롬프트 패키지.

이 패키지는 SPEC-AI-REPORT-003 의 Codex CLI 시스템 자산을 보관합니다.

파일 목록:
- codex_prompt.md: Codex CLI 호출용 사용자 프롬프트 (Fast Mode)
  - `〈종목명〉` / `〈종목코드〉` 플레이스홀더 필수
  - `codex_cli_runner.load_codex_prompt()` 가 런타임에 치환

Goose 모드(SPEC-AI-REPORT-004)는 이 패키지가 아니라 `backend/goose_harness_src/` 하네스 원본을 쓴다.

canonical 경로이며 변경 시 코드 리뷰 필수.
"""
