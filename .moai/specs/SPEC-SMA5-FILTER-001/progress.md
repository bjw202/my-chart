## SPEC-SMA5-FILTER-001 Progress

- Started: 2026-05-26
- Branch: feature/SPEC-SMA5-FILTER-001 (from chore/integrated-main-merge-2026-04-25 HEAD)
- Development mode: tdd (RED-GREEN-REFACTOR)
- Harness level: standard (multi-domain feature, ~10 files; evaluator-active final-pass)
- Languages: python (backend) + typescript (frontend)
- plan-audit review-1: FAIL(0.74) — MP-3 frontmatter house-style false-positive; D2~D6 resolved in v1.0.1
- User approval (2026-05-26): proceed with manager-tdd + create feature branch

### Phase log
- Phase 1: plan.md reused as execution plan (manager-strategy re-analysis skipped — audit-verified plan exists)
- Phase 2 (manager-tdd): pending

### Follow-up — 2026-05-26 라이브 검증
- 사용자 보고: `SMA5 > EMA20` 패턴 0건 반환
- 진단: 레거시 stock_meta(26-col, sma5 누락) — `_STOCK_META_DDL`이 `CREATE TABLE IF NOT EXISTS`라 기존 테이블에 sma5 자동 추가 안 됨
- 수정: meta_service.py `_MINERVINI_META_COLS`에 `"sma5"` 추가 (1라인) — daily.py 멱등 ALTER 패턴과 대칭
- 검증: reproduction test 1건 추가 통과, 회귀 0 (584→585 passed)
- 사용자 액션: 서버 재시작 후 `POST /api/db/update`로 SMA5 재계산 트리거 필요
