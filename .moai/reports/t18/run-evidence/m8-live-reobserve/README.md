# M8 라이브 재관측 (AC-018, 보안 강화 이후 빌드)

- 빌드: main b6caa69 (M7 보안 강화 포함), 서버 재시작 23:43, 검토 스위치 AI_REPORT_GOOSE_REVIEW 해제
- 작업: job 4ce68a7e961546178091c01660a385e3, 종목 020150, 2026-10-21 23:43:45 시작, 검토 세션 23:51:01~23:53:42
- 결과: 이벤트 done, delivery_status=draft (감수가 source_accuracy=revise 로 판정, 실제 서술 오류 지적)
- 영수증: outcome=reviewed, exit_code 0, draft_unchanged=true, 타일 읽음 30 = 기대 30 (desktop 12 + mobile 18), 입력·미리보기 해시 시작=끝
- 하네스 CLAUDE.md 해시 e5c3fd9b 불변 (실행 전후)
- 미관측: file:// 서브리소스·iframe 차단이 이 실행에서 실제로 작동했는지는 정상 보고서로는 확인 불가 (PoC 시험은 security-rereview.md 참조)
- 큰 파일(PNG, report.html)은 추적하지 않음: 원본은 ~/.goose-harness/runs/<job>/ (최근 10개 유지)
