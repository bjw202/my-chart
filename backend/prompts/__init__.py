"""AI 리포트 프롬프트 패키지.

이 패키지는 SPEC-AI-REPORT-001의 Perplexity API 시스템 자산을 보관합니다.

파일 목록:
- perplexity_prompt.md: 사용자 프롬프트 템플릿 (system 아님, user role 메시지)
  - `〈종목명〉` 플레이스홀더 필수
  - load_prompt() 함수가 런타임에 치환

이 위치는 SPEC-AI-REPORT-001 NFR-004(프롬프트 무결성)의 canonical 경로입니다.
변경 시 코드 리뷰 필수.
"""
