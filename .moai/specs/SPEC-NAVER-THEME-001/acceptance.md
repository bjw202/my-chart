# Acceptance Criteria: SPEC-NAVER-THEME-001 V1

## 메타

| 항목 | 값 |
|------|-----|
| SPEC | SPEC-NAVER-THEME-001 |
| 버전 | 1.0.0 |
| 검증 방식 | 자동 (pytest) + 수동 회귀 |
| 사인오프 | Product Owner |
| 총 AC | 14개 (전부 PASS 시 V1 완료) |

> 모든 import 경로는 `backend.services.naver_theme`로 통일. 인코딩은 **EUC-KR**.

---

## AC-1: 5종 DataFrame + metadata 반환 (REQ-NT-001, REQ-NT-011)

### Given
- `backend/services/naver_theme/` 모듈이 구현되어 있다
- 네이버 금융 테마 페이지가 정상 응답한다

### When
```python
from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult
import pandas as pd

result = collect_and_analyze(top_n_themes=20, leaders_per_theme=3, skip_details=False)
```

### Then
```python
assert isinstance(result, ThemeAnalysisResult)
assert isinstance(result.themes_df, pd.DataFrame)
assert isinstance(result.stocks_df, pd.DataFrame)
assert isinstance(result.strong_themes_df, pd.DataFrame)
assert isinstance(result.leaders_df, pd.DataFrame)
assert isinstance(result.multi_theme_stocks_df, pd.DataFrame)
assert isinstance(result.metadata, dict)

# 필수 컬럼
assert {"theme_id", "theme_name", "change_pct", "change_pct_3d"} <= set(result.themes_df.columns)
assert {"stock_code", "stock_name", "inclusion_reason"} <= set(result.stocks_df.columns)
assert {"theme_id", "rank", "leader_score"} <= set(result.leaders_df.columns)
assert {"stock_code", "theme_count", "theme_names"} <= set(result.multi_theme_stocks_df.columns)

# metadata 키
for key in ("collected_at", "theme_count", "stock_count", "elapsed_sec", "errors"):
    assert key in result.metadata
```

---

## AC-2: EUC-KR 인코딩 정상 처리 (REQ-NT-NF-002, REQ-NT-NF-005)

### Given
- 네이버 금융 페이지는 EUC-KR로 응답한다
- 크롤러가 `Response.encoding = 'euc-kr'`을 강제 설정한다

### When
```python
result = collect_and_analyze()
```

### Then
```python
sample_themes = result.themes_df["theme_name"].head(10).tolist()
sample_stocks = result.stocks_df["stock_name"].head(10).tolist() if not result.stocks_df.empty else []

# 한글 깨짐 문자(  Replacement Character) 없음
for name in sample_themes + sample_stocks:
    assert "" not in name, f"Replacement character in: {name!r}"
    assert "?" not in name or name.endswith("?") is False, f"Suspicious '?' in: {name!r}"

# 실제 한글 포함 검증 (테마명에 최소 1개의 한글 음절)
import re
HANGUL = re.compile(r"[가-힣]")
assert any(HANGUL.search(name) for name in sample_themes), \
    "No Hangul characters found in theme names — encoding likely broken"
```

> 추가 검증: `crawler._fetch()` 코드에 `resp.encoding = 'euc-kr'` 라인이 존재하는지 코드 리뷰로 확인.

---

## AC-3: 시가총액·거래대금 원 단위 통일 (REQ-NT-006, REQ-NT-007)

### Given
- `enrich_market_cap`이 read-only DB JOIN을 수행한다
- `_parse_korean_number`가 거래대금 문자열을 원 단위로 정규화한다

### When
```python
result = collect_and_analyze()
stocks_df = result.stocks_df
```

### Then
```python
# 타입: int64 또는 float64 허용 (NaN 포함 가능 → float64)
assert stocks_df["market_cap"].dtype in ("int64", "Int64", "float64"), \
    f"market_cap dtype unexpected: {stocks_df['market_cap'].dtype}"
assert stocks_df["trade_value"].dtype in ("int64", "Int64", "float64"), \
    f"trade_value dtype unexpected: {stocks_df['trade_value'].dtype}"

# 값 범위 (NaN 허용)
assert ((stocks_df["market_cap"] >= 0) | stocks_df["market_cap"].isna()).all()
assert ((stocks_df["trade_value"] >= 0) | stocks_df["trade_value"].isna()).all()

# 단위 검증: 삼성전자(005930)가 결과에 있다면 시총 > 1e13 (10조 이상)
sec = stocks_df[stocks_df["stock_code"] == "005930"]
if not sec.empty:
    cap = sec["market_cap"].iloc[0]
    if not pd.isna(cap):
        assert cap > 1e13, f"Samsung market_cap suspiciously small: {cap}"

# "억", "백만", "조" 같은 단위 문자가 컬럼 값에 남아있지 않음
for col in ("market_cap", "trade_value"):
    sample = stocks_df[col].dropna().astype(str).head(20)
    for v in sample:
        for unit in ("억", "백만", "조", "만"):
            assert unit not in v, f"Raw unit '{unit}' in {col}: {v!r}"
```

---

## AC-4: leader_score 가중치 정확 (REQ-NT-009)

### Given
- 가중치: `change_pct=0.40`, `volume=0.30`, `market_cap=0.20`, `trade_value=0.10`

### When
```python
result = collect_and_analyze()
leaders_df = result.leaders_df
stocks_df = result.stocks_df
```

### Then
```python
# 가중치 합 = 1.0
weights = {"change_pct": 0.40, "volume": 0.30, "market_cap": 0.20, "trade_value": 0.10}
assert abs(sum(weights.values()) - 1.0) < 1e-9

# 첫 테마의 z-score 재계산 검증
import numpy as np
first_theme_id = leaders_df["theme_id"].iloc[0]
group = stocks_df[stocks_df["theme_id"] == first_theme_id].copy()

for col in weights:
    s = group[col].astype(float).fillna(0)
    std = s.std(ddof=0)
    group[f"z_{col}"] = 0.0 if std == 0 or pd.isna(std) else (s - s.mean()) / std

expected = sum(group[f"z_{c}"] * w for c, w in weights.items())

actual = leaders_df[leaders_df["theme_id"] == first_theme_id].sort_values("rank")
# 상위 K개의 leader_score가 재계산값과 일치 (±0.01 부동소수점 오차 허용)
top_expected = group.assign(leader_score=expected).nlargest(len(actual), "leader_score")
for a, e in zip(actual["leader_score"].tolist(), top_expected["leader_score"].tolist()):
    assert abs(a - e) < 0.01, f"leader_score mismatch: actual={a}, expected={e}"
```

---

## AC-5: 페이지네이션 자동 탐지 (REQ-NT-003)

### Given
- 첫 페이지 fetch → `last_page` 추출 → `range(2, last_page+1)` 순회 패턴

### When
```python
result = collect_and_analyze()
```

### Then
```python
# themes_df 행 수가 합리적 범위 (네이버는 보통 40~100 테마)
n = len(result.themes_df)
assert 20 <= n <= 200, f"Suspicious themes_df row count: {n}"
```

### Code review 검증
- `_collect_theme_list` 함수에 `last_page = 1`을 그대로 사용한 while 루프가 없는지 확인
- 첫 페이지 fetch → last_page 추출 → `range(2, last_page + 1)` 패턴이 사용되는지 확인

---

## AC-6: 호출 간 sleep ≥ 0.7초 실측 (REQ-NT-NF-001)

### Given
- `config.CRAWL_DELAY = 0.7`

### When (Mock 검증)
```python
from unittest.mock import patch

with patch("backend.services.naver_theme.crawler.time.sleep") as mock_sleep:
    result = collect_and_analyze(top_n_themes=3, leaders_per_theme=2)
```

### Then
```python
# sleep 호출 횟수 >= HTTP 호출 횟수
assert mock_sleep.call_count >= 3, f"Too few sleep calls: {mock_sleep.call_count}"
# 모든 호출이 >= 0.7초
for call in mock_sleep.call_args_list:
    assert call.args[0] >= 0.7, f"Sleep < 0.7s: {call.args[0]}"
```

### When (실측, 선택, @pytest.mark.live)
```python
import time
start = time.time()
result = collect_and_analyze(top_n_themes=3, leaders_per_theme=2, skip_details=False)
elapsed = time.time() - start
# 최소 sleep 합 = (1 page list + 3 details) * 0.7 = 2.8초
assert elapsed >= 2.5, f"Total elapsed too short: {elapsed}s"
```

---

## AC-7: 부분 실패 허용 + errors 기록 (REQ-NT-NF-003)

### Given
- 일부 테마/페이지 fetch가 실패할 수 있다

### When (Mock 강제 실패)
```python
from unittest.mock import patch
import requests

real_fetch = ...  # 원본 fetch_theme_list_page 참조

def mock_fetch(page):
    if page == 2:
        raise requests.exceptions.HTTPError("429 Too Many Requests")
    return real_fetch(page)

with patch("backend.services.naver_theme.service.fetch_theme_list_page", side_effect=mock_fetch):
    result = collect_and_analyze(top_n_themes=5, skip_details=True)
```

### Then
```python
# 부분 결과 반환됨
assert len(result.themes_df) > 0, "Should return partial results"

# errors 기록
assert len(result.metadata["errors"]) >= 1
err = result.metadata["errors"][0]
assert "stage" in err and err["stage"] in ("list", "detail")
assert "reason" in err
```

---

## AC-8: skip_details=True 시 10초 이내 (REQ-NT-004)

### Given
- 빠른 모드 (`skip_details=True`)에서는 테마 상세 크롤링을 생략한다

### When
```python
import time
start = time.time()
result = collect_and_analyze(skip_details=True)
elapsed = time.time() - start
```

### Then
```python
assert elapsed <= 10, f"Quick mode too slow: {elapsed}s"
assert len(result.stocks_df) == 0
assert len(result.leaders_df) == 0
assert len(result.multi_theme_stocks_df) == 0
assert len(result.themes_df) > 0
assert len(result.strong_themes_df) > 0
```

---

## AC-9: 단위 테스트 + 커버리지 ≥ 85% (REQ-NT-001 ~ REQ-NT-010)

### Given
- `tests/fixtures/naver_theme/theme_list_page1.html`, `theme_detail_178.html` fixture 존재

### When
```bash
pytest tests/test_naver_theme_parser.py tests/test_naver_theme_analyzer.py \
       -m unit \
       --cov=backend.services.naver_theme \
       --cov-report=term-missing
```

### Then
- 모든 단위 테스트 PASS
- 커버리지 ≥ 85%
- 다음 테스트가 포함되어야 한다:
  - `test_parse_theme_list_extracts_theme_id_from_anchor_href`
  - `test_parse_theme_list_detects_last_page`
  - `test_parse_theme_detail_captures_inclusion_reason` (AC-13과 연동)
  - `test_parse_korean_number_multi_token`
  - `test_build_leaders_zero_std_yields_zero_z`
  - `test_build_multi_theme_stocks_dedups_duplicate_rows`

---

## AC-10: 외부 import 1줄 (REQ-NT-001)

### Given
- `backend/services/naver_theme/__init__.py`가 진입점을 노출한다

### When
```python
from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult
result = collect_and_analyze()
```

### Then
```python
assert isinstance(result, ThemeAnalysisResult)
# Crawler/Parser/Analyzer 같은 내부 구현은 import 불필요
```

### Code review 검증
- `__init__.py`에 `from .service import collect_and_analyze, ThemeAnalysisResult`와 `__all__` 정의 존재
- 구버전 경로(`modules/` 아래)로 import하는 코드가 프로젝트 어디에도 없음. 검증 명령:
  ```bash
  ! grep -rn -- "modules\\.naver_theme" backend frontend tests
  ```
  결과는 0건이어야 한다 (모든 import는 `backend.services.naver_theme` 경로 사용).

---

## AC-11: DB 무수정 (REQ-NT-C-001)

### Given
- 본 모듈은 `Output/stock_data_daily.db`를 read-only로만 사용한다
- `db_join.py`는 `mode=ro` URI 모드로 SQLite 연결을 연다

### When
```python
import os
from backend.deps import DAILY_DB_PATH
from backend.services.naver_theme import collect_and_analyze

mtime_before = os.path.getmtime(DAILY_DB_PATH)
size_before = os.path.getsize(DAILY_DB_PATH)

result = collect_and_analyze(top_n_themes=3, leaders_per_theme=2)

mtime_after = os.path.getmtime(DAILY_DB_PATH)
size_after = os.path.getsize(DAILY_DB_PATH)
```

### Then
```python
assert mtime_before == mtime_after, f"DB mtime changed (DB modified): {mtime_before} -> {mtime_after}"
assert size_before == size_after, "DB size changed (DB modified)"
```

### Additional read-only 검증
```python
# read-only 연결이 INSERT를 거부하는지 확인 (회귀 테스트)
import sqlite3, pytest
conn = sqlite3.connect(f"file:{DAILY_DB_PATH}?mode=ro", uri=True)
with pytest.raises(sqlite3.OperationalError):
    conn.execute("INSERT INTO stock_meta (code, name) VALUES ('TEST00', 'test')")
conn.close()
```

### Code review 검증
- `backend/services/naver_theme/db_join.py`에 `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` 패턴 존재
- 본 모듈 어디에도 INSERT/UPDATE/DELETE/CREATE/DROP/ALTER 키워드가 등장하지 않음

---

## AC-12: 기존 4탭 회귀 없음 (REQ-NT-C-002)

### Given
- 변경 대상 기존 파일은 다음 4개로 한정 (AC-14 참조)
  - `backend/main.py`, `frontend/src/types/market.ts`, `frontend/src/components/TabNavigation/TabNavigation.tsx`, `frontend/src/AppContent.tsx`
- Market Overview / Sector Analysis / Stock Explorer / Chart Grid 4탭의 기존 동작은 변경되지 않는다

### When
```bash
# 백엔드 자동 회귀 테스트
pytest backend/tests/ -m "not live" --tb=short

# 프론트엔드 자동 회귀 테스트
cd frontend && npm test -- --run
```

### Then
- 모든 기존 백엔드 테스트 PASS (실패/오류 0건)
- 모든 기존 프론트엔드 Vitest suite PASS
- 기존 4탭의 핵심 시나리오 (수동 스모크 테스트):
  - Market Overview: treemap + breadth + weekly highlights 정상 렌더링
  - Sector Analysis: SectorRankingTable + SectorDetailPanel 정상 렌더링
  - Stock Explorer: 스크리닝 결과 정상 표시
  - Chart Grid: 종목 선택 후 차트 정상 렌더링
- 새 탭(Theme Analysis) 추가 후에도 위 4탭의 라우팅 / API / 컴포넌트가 영향을 받지 않음

---

## AC-13: inclusion_reason 컬럼 fixture 검증 (REQ-NT-008)

### Given
- `tests/fixtures/naver_theme/theme_detail_178.html`에 편입사유 텍스트가 포함된 종목 행이 존재한다 (`td[1]`)

### When
```python
import pathlib
from backend.services.naver_theme.parser import parse_theme_detail

html = pathlib.Path("tests/fixtures/naver_theme/theme_detail_178.html").read_text(encoding="euc-kr")
stocks = parse_theme_detail(html, theme_id=178, theme_name="전선")
```

### Then
```python
assert len(stocks) > 0
# 모든 종목이 inclusion_reason 키 보유
assert all("inclusion_reason" in s for s in stocks)
# 적어도 1개 종목은 비어있지 않은 편입사유 텍스트 보유
non_empty = [s for s in stocks if s["inclusion_reason"].strip()]
assert len(non_empty) >= 1, "No inclusion_reason captured from fixture"
# 한글 텍스트 포함 검증
import re
HANGUL = re.compile(r"[가-힣]")
assert any(HANGUL.search(s["inclusion_reason"]) for s in non_empty), \
    "inclusion_reason has no Korean characters — column mapping likely wrong"
```

> 추가: `parse_theme_detail`이 `td[1]`을 `inclusion_reason`으로 매핑하는지 코드 리뷰로 확인 (REQ-NT-008, A-6).

---

## AC-14: 기존 파일 surgical mod 경계 (REQ-NT-C-002)

### Given
- 본 SPEC은 애드온 형태이며, 기존 파일 변경 줄 수 합계는 ≤ 10줄로 제한된다

### When
```bash
# 변경된 파일 목록 확인
git diff --stat HEAD~..HEAD -- \
  backend/main.py \
  frontend/src/types/market.ts \
  frontend/src/components/TabNavigation/TabNavigation.tsx \
  frontend/src/AppContent.tsx
```

### Then
- 변경 대상은 위 4개 파일로 한정
- 각 파일별 변경량:
  | 파일 | 변경 줄 수 | 변경 내용 |
  |------|----------|----------|
  | `backend/main.py` | 2 | import 1줄 + `app.include_router(themes_router, prefix="/api")` 1줄 |
  | `frontend/src/types/market.ts` | 1 | TabId union에 `'theme-analysis'` 추가 |
  | `frontend/src/components/TabNavigation/TabNavigation.tsx` | 1 | TABS 배열에 1행 추가 |
  | `frontend/src/AppContent.tsx` | 1~2 | `'theme-analysis'` 분기 + 마운트 |
- 합계 ≤ 10줄
- 위 4개 외의 기존 파일은 무수정 (예: `TabContext.tsx`의 `CrossTabParams`는 V1.5에서 추가, 본 SPEC에서 손대지 않음)

### Verification
```bash
# 합계 줄 수가 임계 초과 시 PR 거부
total_lines_added=$(git diff --numstat HEAD~..HEAD -- \
  backend/main.py \
  frontend/src/types/market.ts \
  frontend/src/components/TabNavigation/TabNavigation.tsx \
  frontend/src/AppContent.tsx | awk '{s+=$1} END {print s}')

[ "$total_lines_added" -le 10 ] || { echo "Surgical mod boundary exceeded: $total_lines_added > 10"; exit 1; }
```

---

## 최종 사인오프 표

| AC | 요구사항 매핑 | 검증 방식 | 상태 |
|----|--------------|----------|------|
| AC-1 | REQ-NT-001, 011 | 자동 (pytest) | ☐ |
| AC-2 | REQ-NT-NF-002, 005 | 자동 + 코드 리뷰 | ☐ |
| AC-3 | REQ-NT-006, 007 | 자동 | ☐ |
| AC-4 | REQ-NT-009 | 자동 | ☐ |
| AC-5 | REQ-NT-003 | 자동 + 코드 리뷰 | ☐ |
| AC-6 | REQ-NT-NF-001 | 자동 (mock + live) | ☐ |
| AC-7 | REQ-NT-NF-003 | 자동 (mock) | ☐ |
| AC-8 | REQ-NT-004 | 자동 | ☐ |
| AC-9 | REQ-NT-001~010 | 자동 (커버리지) | ☐ |
| AC-10 | REQ-NT-001 | 자동 + grep | ☐ |
| AC-11 | REQ-NT-C-001 | 자동 (mtime/size + ro 연결) | ☐ |
| AC-12 | REQ-NT-C-002 | 자동 + 수동 스모크 | ☐ |
| AC-13 | REQ-NT-008 | 자동 (fixture) | ☐ |
| AC-14 | REQ-NT-C-002 | 자동 (git diff numstat) | ☐ |

**14개 AC 모두 PASS 시 V1 Production Ready.**
