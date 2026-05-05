## Task Decomposition
SPEC: SPEC-NAVER-THEME-003 (V2 frontend 채택)

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | Backend RED: V2 metadata alias 5개 단위 테스트 추가 | REQ-NT3-005, REQ-NT3-006 | - | tests/test_naver_theme_v2_service.py | pending |
| T-002 | Backend GREEN: collect_and_analyze_v2 metadata에 V1 alias 4 필드 + _empty_result 적용 | REQ-NT3-005, REQ-NT3-006, REQ-NT3-C-003 | T-001 | backend/services/naver_theme_v2/service.py | pending |
| T-003 | Frontend RED: api/themes.ts URL swap + 타입 확장 vitest | REQ-NT3-001, REQ-NT3-002, REQ-NT3-003 | - | frontend/src/api/__tests__/themes.test.ts | pending |
| T-004 | Frontend GREEN: api/themes.ts V2 endpoint swap + theme_description? + stock_description? | REQ-NT3-001, REQ-NT3-002, REQ-NT3-003 | T-003 | frontend/src/api/themes.ts | pending |
| T-005 | Frontend RED: ThemeRankingTable theme_description tooltip vitest | REQ-NT3-004, REQ-NT3-NF-002 | T-004 | frontend/src/components/ThemeAnalysis/__tests__/ThemeRankingTable.test.tsx | pending |
| T-006 | Frontend GREEN: ThemeRankingTable theme_name 셀 title 속성 추가 | REQ-NT3-004, REQ-NT3-NF-002 | T-005 | frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx | pending |
| T-007 | Frontend RED: ThemeAnalysis 에러 메시지 + retry 버튼 vitest | REQ-NT3-007, REQ-NT3-NF-001, REQ-NT3-C-006 | T-004 | frontend/src/components/ThemeAnalysis/__tests__/ThemeAnalysis.test.tsx | pending |
| T-008 | Frontend GREEN: ThemeAnalysis error state + retry handler | REQ-NT3-007, REQ-NT3-NF-001, REQ-NT3-C-006 | T-007 | frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx | pending |
| T-009 | Frontend RED: ThemeDetailPanel D-3 V2 description 호환 vitest | REQ-NT3-008 | T-004 | frontend/src/components/ThemeAnalysis/__tests__/ThemeDetailPanel.test.tsx | pending |
| T-010 | Verification: ThemeDetailPanel.tsx 무수정 (git diff empty) | REQ-NT3-008, REQ-NT3-C-002 | T-009 | (verification only) | pending |
| T-011 | Integration verification: V1 51 + V2 24+5 + frontend vitest baseline + git diff guards | REQ-NT3-C-001~006, REQ-NT3-NF-004 | T-002, T-006, T-008, T-010 | (validation) | pending |
| T-012 | MX tag update: SPEC ID 갱신 (themes.ts, ThemeRankingTable.tsx, ThemeAnalysis.tsx) + 신규 retry 패턴 NOTE | (REQ-NT3-001~008) | T-002~T-010 | (modified files) | pending |
| T-013 | Git commit: feat(naver-theme-v2-frontend) — 본 SPEC 파일만 명시 stage (SPEC-AI-REPORT-003 미커밋 변경 분리) | (all REQ) | T-011, T-012 | (commit) | pending |

> Drift Guard baseline: 7 planned files. Threshold: drift > 30% triggers Phase 2.7 re-planning.
