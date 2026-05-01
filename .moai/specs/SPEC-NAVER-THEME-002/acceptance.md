---
id: SPEC-NAVER-THEME-002
title: 모바일 stock.naver.com 기반 테마 분석 V2 — Acceptance Criteria
status: Draft
version: 1.0.1
owner: bjw2002
created: 2026-05-01
updated: 2026-05-01
depends_on: SPEC-NAVER-THEME-001
---

# Acceptance Criteria: SPEC-NAVER-THEME-002 V2

## 메타

| 항목 | 값 |
|------|-----|
| SPEC | SPEC-NAVER-THEME-002 |
| 버전 | 1.0.1 |
| 검증 방식 | 자동 (pytest) + 라이브 1회 (`@pytest.mark.live`) |
| 사인오프 | Product Owner |
| 총 AC | 14개 (전부 PASS 시 V2 완료) |

---

## HISTORY

- 2026-05-01 v1.0.1 (RUN-phase amendment): AC-5의 `V1_THEMES_COLUMNS`/`V1_STOCKS_COLUMNS`와 AC-12의 `FRONTEND_THEMES_REQUIRED`/`FRONTEND_STOCKS_REQUIRED`를 V1 실측 컬럼명으로 정정. plan phase에서 추정한 `score, rank, rising_count, unchanged_count, falling_count, change_rate, code, name`은 V1 실제 코드(`backend/services/naver_theme/parser.py` + `backend/services/naver_theme/analyzer.py`)와 불일치한 것이 RUN phase에서 발견됨. V1 실측은 `change_pct, change_pct_3d, up_count, flat_count, down_count, stock_code, stock_name`. V2 parser(`backend/services/naver_theme_v2/parser.py`)는 V1 실측 컬럼명을 정확히 사용하며 V1 호환 alias(`change_rate`, `code`, `name`)도 추가로 노출함. 본 amendment는 V2 implementation 무수정 — expectation 정정만 수행. V1 무수정 정책(REQ-NT2-C-002)은 그대로 유지되며 V1 51 단위 테스트는 회귀 0건 PASS.

- 2026-05-01 v1.0.0: 초안 작성 (manager-spec). 14 AC + AC-PoC-Resolution sentinel.

---

> 모든 V2 import 경로는 `backend.services.naver_theme_v2`. V1 모듈 (`backend.services.naver_theme`)은 무수정. analyzer/db_join/schemas는 V1을 import 재사용 (단, schemas.py 파일은 부재 — `ThemeAnalysisResult`는 `backend/services/naver_theme/service.py`에 `@dataclass`로 정의되어 `__init__.py`로 re-export됨).

---

## AC-1: 단일 진입점 노출 (REQ-NT2-001)

### Given
- `backend/services/naver_theme_v2/` 패키지가 구현되어 있다
- V1 패키지 `backend/services/naver_theme/`는 무수정으로 존재한다

### When
```python
from backend.services.naver_theme_v2 import collect_and_analyze_v2, ThemeAnalysisResult
import inspect
```

### Then
```python
assert callable(collect_and_analyze_v2)

sig = inspect.signature(collect_and_analyze_v2)
params = sig.parameters

# 시그니처는 V1 collect_and_analyze와 동일 패턴
assert "top_n_themes" in params
assert "leaders_per_theme" in params
assert "skip_details" in params
assert params["top_n_themes"].default == 20
assert params["leaders_per_theme"].default == 3
assert params["skip_details"].default is False
```

---

## AC-2: ThemeAnalysisResult 인스턴스 반환 (REQ-NT2-001, REQ-NT2-008)

### Given
- 네이버 모바일 사이트 endpoint 2종이 정상 응답하거나 (라이브) JSON fixture가 mock 처리되어 있다

### When
```python
from backend.services.naver_theme_v2 import collect_and_analyze_v2, ThemeAnalysisResult
import pandas as pd

result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)
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

# data_source는 V2임을 명시
assert result.metadata.get("data_source") == "naver_mobile_v2"
```

---

## AC-3: themes_df의 theme_description 컬럼 존재 및 nullable (REQ-NT2-004)

### Given
- AC-2 result가 가용하다
- detail endpoint 응답에서 일부 sectorDescription이 null인 경우를 fixture로 포함한다

### When
```python
result = collect_and_analyze_v2(top_n_themes=10, skip_details=False)
themes_df = result.themes_df
```

### Then
```python
import pandas as pd

# theme_description 컬럼이 존재
assert "theme_description" in themes_df.columns

# dtype은 object (nullable string)
assert themes_df["theme_description"].dtype == object

# null/NaN 허용 — 일부는 채워져 있고, 일부는 NaN일 수 있음 (강제 100% 채움 X)
# 단, 라이브 fixture 기준 적어도 1개 이상은 non-null이어야 (sectorDescription이 거의 항상 채워지므로)
non_null_count = themes_df["theme_description"].notna().sum()
assert non_null_count >= 1, "적어도 1개 이상의 theme_description이 채워져야 함"

# null인 경우 NaN (strict)
for desc in themes_df["theme_description"]:
    assert desc is None or isinstance(desc, str) or pd.isna(desc)
```

---

## AC-4: stocks_df의 stock_description 컬럼 존재 및 nullable (REQ-NT2-005)

### Given
- AC-2 result가 가용하다

### When
```python
result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)
stocks_df = result.stocks_df
```

### Then
```python
import pandas as pd

assert "stock_description" in stocks_df.columns
assert stocks_df["stock_description"].dtype == object

# 라이브 fixture 기준 적어도 1개 이상의 stock_description이 채워져 있어야 함 (PoC 결과 8/8 = 100%)
non_null_count = stocks_df["stock_description"].notna().sum()
assert non_null_count >= 1

for desc in stocks_df["stock_description"]:
    assert desc is None or isinstance(desc, str) or pd.isna(desc)
```

---

## AC-5: V1 컬럼 100% 보존 (REQ-NT2-008, REQ-NT2-C-002)

### Given
- V1 V2 호환성을 검증하기 위해 V1 `collect_and_analyze` 결과의 컬럼 set을 baseline으로 사용

### When
```python
from backend.services.naver_theme.schemas import ThemeAnalysisResult as V1Result
# V1 baseline 컬럼은 schemas.py 또는 V1 단위 테스트에서 정의된 컬럼 set

V1_THEMES_COLUMNS = {
    "theme_id", "theme_name", "change_pct", "change_pct_3d",
    "up_count", "flat_count", "down_count",
    # (V1 실측: backend/services/naver_theme/parser.py parse_theme_list 출력 기준)
}
V1_STOCKS_COLUMNS = {
    "theme_id", "theme_name", "stock_code", "stock_name",
    "inclusion_reason", "change_pct", "volume", "trade_value", "market_cap",
    # (V1 실측: backend/services/naver_theme/parser.py parse_theme_detail 출력 + enrich_market_cap 후 market_cap)
}

result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)
```

### Then
```python
# V2 themes_df는 V1 컬럼을 superset으로 가짐
assert V1_THEMES_COLUMNS.issubset(set(result.themes_df.columns)), \
    f"V1 columns missing in V2: {V1_THEMES_COLUMNS - set(result.themes_df.columns)}"

# V2 stocks_df도 동일
assert V1_STOCKS_COLUMNS.issubset(set(result.stocks_df.columns)), \
    f"V1 columns missing in V2: {V1_STOCKS_COLUMNS - set(result.stocks_df.columns)}"

# V2 신규 컬럼 추가 확인
assert "theme_description" in result.themes_df.columns
assert "stock_description" in result.stocks_df.columns
```

---

## AC-6: errors는 dict 리스트 (REQ-NT2-NF-003)

### Given
- detail endpoint 1개를 강제 실패시키는 fixture (예: 5xx mock)

### When
```python
result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)
errors = result.metadata.get("errors", [])
```

### Then
```python
assert isinstance(errors, list)
for err in errors:
    assert isinstance(err, dict)
    assert "theme_id" in err  # 값은 None 가능
    assert "stage" in err
    assert "reason" in err
    # stage는 정의된 enum 중 하나
    assert err["stage"] in {
        "list_fetch", "detail_fetch", "schema_validation",
        "content_type", "json_decode", "endpoint_drift",
    }
    assert isinstance(err["reason"], str)
```

---

## AC-7: 모바일 UA + Referer + Accept 헤더 (REQ-NT2-NF-001)

### Given
- crawler.py가 HTTP 요청을 수행한다

### When
```python
# crawler 호출 시 send된 request의 headers를 mock으로 캡처
import unittest.mock as mock
from backend.services.naver_theme_v2 import crawler

with mock.patch("backend.services.naver_theme_v2.crawler.requests.Session.get") as mocked_get:
    mocked_get.return_value.status_code = 200
    mocked_get.return_value.json.return_value = {"isSuccess": True, "result": {"sectors": []}}
    mocked_get.return_value.headers = {"Content-Type": "application/json; charset=utf-8"}
    crawler.fetch_theme_list(page=1, page_size=50)

call_args = mocked_get.call_args
sent_headers = call_args.kwargs.get("headers", {})
```

### Then
```python
assert "User-Agent" in sent_headers
assert "iPhone" in sent_headers["User-Agent"]
assert "Mobile" in sent_headers["User-Agent"]

assert "Referer" in sent_headers
assert sent_headers["Referer"] == "https://m.stock.naver.com/domestic/home/theme/daily"

assert "Accept" in sent_headers
assert "application/json" in sent_headers["Accept"]

# Cookie/Authorization 헤더 없음 (REQ-NT2-C-001)
assert "Cookie" not in sent_headers
assert "Authorization" not in sent_headers
```

---

## AC-8: sleep ≥ 0.7s 검증 (REQ-NT2-NF-001)

### Given
- crawler가 연속 요청 사이에 sleep을 수행한다

### When
```python
import time
import unittest.mock as mock
from backend.services.naver_theme_v2 import crawler

call_times = []

def fake_get(*args, **kwargs):
    call_times.append(time.monotonic())
    resp = mock.MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"isSuccess": True, "result": {"sectors": []}}
    resp.headers = {"Content-Type": "application/json"}
    return resp

with mock.patch("backend.services.naver_theme_v2.crawler.requests.Session.get", side_effect=fake_get):
    # 2번 연속 호출
    crawler.fetch_theme_list(page=1, page_size=50)
    crawler.fetch_theme_list(page=2, page_size=50)
```

### Then
```python
assert len(call_times) == 2
gap = call_times[1] - call_times[0]
assert gap >= 0.7, f"Sleep between requests must be >= 0.7s, got {gap:.3f}s"
```

---

## AC-9: V2 라우터 등록 — `/api/themes/v2/snapshot` 및 `/api/themes/v2/quick` (REQ-NT2-R-001, REQ-NT2-R-002)

### Given
- FastAPI 앱이 부팅 가능하다

### When
```python
from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
routes = [(r.path, r.methods) for r in app.routes if hasattr(r, "path")]
```

### Then
```python
# V2 snapshot 라우트 존재
assert any(
    path == "/api/themes/v2/snapshot" and "GET" in (methods or set())
    for path, methods in routes
), f"V2 snapshot route missing. routes={routes}"

# V2 quick 라우트 존재
assert any(
    path == "/api/themes/v2/quick" and "GET" in (methods or set())
    for path, methods in routes
), f"V2 quick route missing. routes={routes}"
```

---

## AC-10: V1 라우터 무수정 — 회귀 차단 (REQ-NT2-R-003, REQ-NT2-C-002)

### Given
- V1 라우터 `/api/themes/snapshot`, `/api/themes/quick`이 V1 ship 시점에 등록되어 있었다

### When
```python
from backend.main import app
routes = [(r.path, list(r.methods or set()), r.endpoint.__name__) for r in app.routes if hasattr(r, "path")]
```

### Then
```python
# V1 routes 그대로 존재
v1_snapshot = [r for r in routes if r[0] == "/api/themes/snapshot"]
v1_quick = [r for r in routes if r[0] == "/api/themes/quick"]

assert len(v1_snapshot) == 1
assert len(v1_quick) == 1

assert "GET" in v1_snapshot[0][1]
assert "GET" in v1_quick[0][1]

# V1 endpoint 함수 이름이 V1 ship 시점과 동일 (handler 함수가 갈아끼워지지 않았는지 확인)
# V1 endpoint 함수명은 V1 ship 시점의 progress.md에서 확인 가능
# (구현 단계에서 V1의 정확한 endpoint 함수 이름을 assert)
```

---

## AC-11: DB INSERT/UPDATE 미발생 — DB mtime 무변경 (REQ-NT2-C-004)

### Given
- `Output/stock_data_daily.db` 파일이 존재하고, 테스트 시작 전 mtime을 기록한다

### When
```python
import os
from pathlib import Path

DB_PATH = Path("Output/stock_data_daily.db")
mtime_before = DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0

# V2 entrypoint 호출
from backend.services.naver_theme_v2 import collect_and_analyze_v2
result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)

mtime_after = DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0
```

### Then
```python
# V2 호출 후에도 DB mtime은 변경되지 않아야 함 (read-only)
assert mtime_after == mtime_before, \
    f"DB was modified during V2 call. before={mtime_before}, after={mtime_after}"
```

---

## AC-12: frontend ThemeAnalysisResult shape 호환 (REQ-NT2-008, REQ-NT2-C-002)

### Given
- V1 frontend 컴포넌트들이 의존하는 컬럼 set이 정의되어 있다 (research.md §3.3)

### When
```python
result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)

# V1 frontend가 themes_df에서 의존하는 컬럼 (V1 실측)
FRONTEND_THEMES_REQUIRED = {"theme_id", "theme_name", "change_pct"}

# V1 frontend가 stocks_df에서 의존하는 컬럼 (V1 실측)
FRONTEND_STOCKS_REQUIRED = {
    "theme_id", "theme_name", "stock_code", "stock_name",
    "market_cap", "change_pct", "inclusion_reason",
}
```

### Then
```python
assert FRONTEND_THEMES_REQUIRED.issubset(set(result.themes_df.columns))
assert FRONTEND_STOCKS_REQUIRED.issubset(set(result.stocks_df.columns))

# theme_id는 int (V1 호환)
if len(result.themes_df) > 0:
    assert pd.api.types.is_integer_dtype(result.themes_df["theme_id"])

# market_cap은 int 단위 원 (V1 호환)
if len(result.stocks_df) > 0:
    assert pd.api.types.is_integer_dtype(result.stocks_df["market_cap"])
```

---

## AC-13: 5xx/timeout retry 동작 — 1회 retry 후 부분 실패 허용 (REQ-NT2-NF-003)

### Given
- detail endpoint 1건이 첫 호출에서 503 응답, 두 번째 호출에서 200 응답으로 mock 설정

### When
```python
import unittest.mock as mock

call_count = {"n": 0}

def fake_detail_get(url, **kwargs):
    call_count["n"] += 1
    resp = mock.MagicMock()
    if call_count["n"] == 1:
        resp.status_code = 503
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"detailCode": "service_unavailable"}
        # raise_for_status는 호출 안하고 status_code만 사용한다고 가정
    else:
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"isSuccess": True, "result": {
            "sectorCode": "178", "sectorName": "전선",
            "sectorDescription": "전선 테마 설명", "items": [],
            "changeRate": 9.2, "totalMarketCap": 0,
            "risingCount": 0, "unChangedCount": 0, "fallingCount": 0,
        }}
    return resp

# crawler.fetch_theme_detail 호출 시 1회 retry 후 성공해야 함
with mock.patch("backend.services.naver_theme_v2.crawler.requests.Session.get", side_effect=fake_detail_get):
    from backend.services.naver_theme_v2 import crawler
    parsed = crawler.fetch_theme_detail(theme_id=178)

# 또 다른 케이스: 2회 모두 5xx → errors[]에 기록되고 함수는 None 또는 빈 결과 반환 (예외 X)
call_count2 = {"n": 0}
def fake_detail_always_5xx(url, **kwargs):
    call_count2["n"] += 1
    resp = mock.MagicMock()
    resp.status_code = 503
    resp.headers = {"Content-Type": "application/json"}
    resp.json.return_value = {"detailCode": "service_unavailable"}
    return resp

with mock.patch("backend.services.naver_theme_v2.crawler.requests.Session.get", side_effect=fake_detail_always_5xx):
    # service.collect_and_analyze_v2가 5xx에서도 부분 실패 결과 반환해야 함
    result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)
```

### Then
```python
# Case A: 1회 retry 후 성공
assert call_count["n"] == 2  # 첫 호출 + 1회 retry
assert parsed is not None

# Case B: 2회 실패 → errors[]에 기록, 예외 X
errors = result.metadata.get("errors", [])
detail_fetch_errors = [e for e in errors if e["stage"] == "detail_fetch"]
assert len(detail_fetch_errors) >= 1
```

---

## AC-14: endpoint URL이 config 상수로부터 사용됨 (REQ-NT2-NF-005)

### Given
- `backend/services/naver_theme_v2/config.py`에 endpoint 상수가 정의되어 있다

### When
```python
from backend.services.naver_theme_v2 import config, crawler
import inspect
import re
```

### Then
```python
# config.py에 4개 상수 정의 확인
assert hasattr(config, "NAVER_MOBILE_BASE_URL")
assert hasattr(config, "NAVER_MOBILE_FRONT_API_PREFIX")
assert hasattr(config, "LIST_ENDPOINT_PATH")
assert hasattr(config, "DETAIL_ENDPOINT_PATH")

assert config.NAVER_MOBILE_BASE_URL == "https://m.stock.naver.com"
assert config.NAVER_MOBILE_FRONT_API_PREFIX == "/front-api"
assert config.LIST_ENDPOINT_PATH == "/stock/sectors/all"
assert config.DETAIL_ENDPOINT_PATH == "/domestic/sector/item/list"

# crawler.py 소스에 hardcoded URL inline 없음
crawler_source = inspect.getsource(crawler)

# "https://m.stock.naver.com/..." inline literal이 없어야 함 (단, config import 후 사용은 허용)
forbidden_inline = re.findall(
    r'"https?://(?:m\.stock|api\.stock|finance)\.naver\.com[^\"]*"', 
    crawler_source,
)
assert len(forbidden_inline) == 0, \
    f"crawler.py에 inline URL hardcoded 발견: {forbidden_inline} — config 상수를 import하세요"

# 동일 검증을 service.py에도
from backend.services.naver_theme_v2 import service
service_source = inspect.getsource(service)
forbidden_in_service = re.findall(
    r'"https?://(?:m\.stock|api\.stock|finance)\.naver\.com[^\"]*"',
    service_source,
)
assert len(forbidden_in_service) == 0
```

---

## AC-PoC-Resolution: PoC blocker 해결 검증 (조건부)

### 조건
이 AC는 research.md §1에서 **PoC-BLOCK-001이 raise되지 않은 경우 SKIP** 한다. PoC 결과 endpoint가 식별되었다면 (현재 상태: ENDPOINT_FOUND) 이 AC는 해당 없음.

### 만약 PoC가 차단되었다면
- research.md에 BLOCKER section이 명시되어 있어야 함
- /moai run 시작 전, 사용자가 browser DevTools로 endpoint를 캡처하여 research.md §2.1, §2.2 schema를 채워야 함
- config.py의 endpoint 상수 placeholder가 실제 URL로 교체되어야 함

### 현재 상태
**PASS (해당 없음)** — research.md §1에서 endpoint 식별 완료, schema 라이브 검증 완료. 이 AC는 단순 sentinel이며 V2 RUN phase에서는 trivially PASS 처리.

---

## 부록: 검증 자동화 매트릭스

| AC | 검증 방식 | 의존성 |
|---|---|---|
| AC-1 | unit (signature 검사) | inspect 표준 라이브러리 |
| AC-2 | unit (mock crawler) + integration (라이브 1회) | JSON fixture |
| AC-3 | unit (synthetic fixture with sectorDescription=null) | fixture 필요 |
| AC-4 | unit (synthetic fixture with description=null) | fixture 필요 |
| AC-5 | unit (V1 vs V2 컬럼 set 비교) | V1 fixture or schemas.py |
| AC-6 | unit (강제 실패 mock + errors[] 검사) | mock 필요 |
| AC-7 | unit (`mock.patch` headers 캡처) | mock 필요 |
| AC-8 | unit (`time.monotonic()` 측정) | 시간 측정 |
| AC-9 | integration (`TestClient(app)` route 검사) | FastAPI TestClient |
| AC-10 | integration (V1 route 그대로 존재) | FastAPI TestClient |
| AC-11 | integration (DB mtime 비교) | 실 DB 파일 (또는 mock) |
| AC-12 | unit (V2 result 컬럼 set 검사) | fixture |
| AC-13 | unit (mock 503 응답 + retry 카운트) | mock |
| AC-14 | unit (config 상수 + 소스 grep) | inspect.getsource |

### 라이브 통합 테스트

`@pytest.mark.live` 마커를 가진 1개 테스트:

```python
@pytest.mark.live
def test_collect_and_analyze_v2_live():
    """라이브 mobile API 호출. CI에서는 skip, 로컬에서만 실행."""
    result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)
    assert isinstance(result, ThemeAnalysisResult)
    assert len(result.themes_df) >= 1
    assert result.themes_df["theme_description"].notna().sum() >= 1
    assert result.stocks_df["stock_description"].notna().sum() >= 1
```

---

## Definition of Done

- [ ] AC-1 ~ AC-14 자동 검증 PASS (14/14)
- [ ] AC-PoC-Resolution PASS (해당 없음으로 trivially PASS)
- [ ] 단위 테스트 커버리지 ≥ 85% (`backend.services.naver_theme_v2.*`)
- [ ] 라이브 1회 검증 (`@pytest.mark.live` test_collect_and_analyze_v2_live PASS)
- [ ] V1 단위 테스트 51개 그대로 PASS (회귀 0건)
- [ ] V1 endpoint `/api/themes/snapshot`, `/api/themes/quick` smoke test PASS (변경 없음 확인)
- [ ] DB mtime 무변경 (AC-11 자동 + 수동 확인)

---

Version: 1.0.0
Status: Draft (V2 RUN phase 검증 기준)
