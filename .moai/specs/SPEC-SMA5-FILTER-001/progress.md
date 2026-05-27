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

### Follow-up #2 — 2026-05-27 라이브 검증 2차 (컬럼 시프트 회귀)
- 사용자 보고: /api/db/update 후 차트 자주색 RS선이 비정상(400K~900K wild 변동) — 4종목 동일 패턴
- 진단: 라이브 stock_prices에 ALTER ADD COLUMN으로 SMA5/FromSMA5가 끝(idx 30, 31)에 append되어 코드 _DAILY_COLS(SMA5 idx 13)와 어긋남 → positional INSERT가 idx 13~31 전체를 한 칸씩 시프트. RS_Line 컬럼에 Range 값, SMA5 컬럼에 LOW_52W 값이 저장. 1.3M 행 부패.
- 수정: daily.py INSERT를 column-name 기반(`INSERT OR REPLACE INTO stock_prices (col1, col2, ...) VALUES (?, ?, ...)`)으로 변경 → 라이브 컬럼 순서와 무관하게 안전 매핑
- 신규 reproduction test: `test_legacy_db_with_altered_columns_inserts_to_correct_columns` (legacy-ALTER 시나리오, AC-9의 fresh-DDL 한정 사각지대 보완)
- SPEC v1.0.3 → v1.0.4, Lesson #8 등록
- 회귀 0 (586 passed, pre-existing 8건 변동 없음)
- 사용자 액션: /api/db/update 재실행 → 2년치 가격 재fetch → 부패 행이 정상 컬럼으로 덮어쓰여짐
