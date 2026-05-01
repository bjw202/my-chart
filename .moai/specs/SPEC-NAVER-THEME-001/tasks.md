# TDD Task Decomposition: SPEC-NAVER-THEME-001

**Status**: Phase 1 Planning Complete  
**Methodology**: Test-Driven Development (RED-GREEN-REFACTOR)  
**Development Mode**: TDD (from quality.yaml)  
**Coverage Target**: 85% minimum  

---

## Task Ordering & Dependencies

```
CRITICAL PATH:
config.py (provides constants)
    ↓
crawler.py (uses config constants, has Session singleton)
    ↓
parser.py (uses config constants)
    ↓
analyzer.py (uses parser functions, computes z-scores with numpy)
    ↓
service.py (composes all above, returns ThemeAnalysisResult)
    ↓
routes/themes.py (imports service.py, exposes 3 endpoints)
    ↓
tests/ (test fixtures and integration tests)
```

Each task tests something new and builds on previous code passing.

---

## Phase 1.1: config.py — Constants and Configuration

**File**: `backend/services/naver_theme/config.py`  
**Lines**: ~50  
**Dependency**: None  

### RED: Test Constants Exist

```python
# tests/services/naver_theme/test_config.py
import pytest
from backend.services.naver_theme.config import (
    NAVER_THEME_LIST_URL,
    NAVER_THEME_DETAIL_URL,
    CRAWL_DELAY,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    USER_AGENT,
    MOMENTUM_WEIGHT_1D,
    MOMENTUM_WEIGHT_3D,
    LEADER_SCORE_WEIGHTS,
    DEFAULT_TOP_N_THEMES,
    DEFAULT_LEADERS_PER_THEME,
)

@pytest.mark.unit
def test_constants_defined():
    """All configuration constants are defined and have expected types."""
    assert isinstance(NAVER_THEME_LIST_URL, str)
    assert "page={" in NAVER_THEME_LIST_URL
    assert isinstance(NAVER_THEME_DETAIL_URL, str)
    assert "no={" in NAVER_THEME_DETAIL_URL
    assert CRAWL_DELAY == 0.7
    assert REQUEST_TIMEOUT == 10
    assert MAX_RETRIES == 1
    assert isinstance(USER_AGENT, str)
    assert "1.0" in USER_AGENT
    assert MOMENTUM_WEIGHT_1D == 0.6
    assert MOMENTUM_WEIGHT_3D == 0.4
    assert LEADER_SCORE_WEIGHTS['change_pct'] == 0.40
    assert LEADER_SCORE_WEIGHTS['volume'] == 0.30
    assert LEADER_SCORE_WEIGHTS['market_cap'] == 0.20
    assert LEADER_SCORE_WEIGHTS['trade_value'] == 0.10
    assert DEFAULT_TOP_N_THEMES == 20
    assert DEFAULT_LEADERS_PER_THEME == 3
```

### GREEN: Implement config.py

Copy constants from plan.md into backend/services/naver_theme/config.py. No logic required.

### REFACTOR

None needed (pure constants).

---

## Phase 1.2: crawler.py — Session Singleton and Fetch Functions

**File**: `backend/services/naver_theme/crawler.py`  
**Lines**: ~100  
**Dependency**: config.py  

### RED: Test Session Singleton

```python
# tests/services/naver_theme/test_crawler.py
import pytest
import requests
from unittest.mock import patch, MagicMock
from backend.services.naver_theme.crawler import _get_session

@pytest.mark.unit
def test_session_singleton_creation():
    """_get_session() creates a Session on first call."""
    # Clear module state
    import backend.services.naver_theme.crawler as crawler_module
    crawler_module._session = None
    
    session = _get_session()
    assert isinstance(session, requests.Session)

@pytest.mark.unit
def test_session_singleton_reuse():
    """_get_session() reuses the same Session on subsequent calls."""
    import backend.services.naver_theme.crawler as crawler_module
    crawler_module._session = None
    
    session1 = _get_session()
    session2 = _get_session()
    assert session1 is session2  # Same object

@pytest.mark.unit
def test_session_has_retry_adapter():
    """Session has HTTPAdapter with Retry configuration mounted."""
    import backend.services.naver_theme.crawler as crawler_module
    crawler_module._session = None
    
    session = _get_session()
    https_adapter = session.get_adapter("https://")
    assert hasattr(https_adapter, 'max_retries')
    # Retry object has total=1, status_forcelist includes 429, 500, etc.
```

### RED: Test fetch_theme_list_page

```python
@pytest.mark.unit
@patch('backend.services.naver_theme.crawler.requests.Session.get')
def test_fetch_theme_list_page_returns_html(mock_get):
    """fetch_theme_list_page() returns HTML string."""
    mock_response = MagicMock()
    mock_response.text = "<html><body>Theme List</body></html>"
    mock_get.return_value = mock_response
    
    from backend.services.naver_theme.crawler import fetch_theme_list_page
    html = fetch_theme_list_page(1)
    assert isinstance(html, str)
    assert "Theme List" in html

@pytest.mark.unit
@patch('backend.services.naver_theme.crawler.requests.Session.get')
def test_fetch_theme_list_page_calls_correct_url(mock_get):
    """fetch_theme_list_page() calls the correct URL with page parameter."""
    mock_response = MagicMock()
    mock_response.text = "<html></html>"
    mock_get.return_value = mock_response
    
    from backend.services.naver_theme.crawler import fetch_theme_list_page
    fetch_theme_list_page(3)
    
    called_url = mock_get.call_args[0][0]
    assert "page=3" in called_url or "=3" in called_url

@pytest.mark.slow
def test_fetch_theme_list_page_with_real_sleep(monkeypatch):
    """fetch_theme_list_page() includes sleep(0.7) for rate limiting."""
    import time
    from backend.services.naver_theme.crawler import fetch_theme_list_page
    
    # Mock the Session.get to avoid real network calls
    mock_get = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "<html></html>"
    mock_get.return_value = mock_response
    
    monkeypatch.setattr('backend.services.naver_theme.crawler.requests.Session.get', mock_get)
    
    start = time.time()
    fetch_theme_list_page(1)
    elapsed = time.time() - start
    
    # Should include sleep, so elapsed >= 0.7 (allowing some tolerance)
    # Note: In tests with mocked network, we measure sleep() directly instead
```

### GREEN: Implement crawler.py

Implement:
1. `_get_session()` - Session singleton with Retry adapter (pattern from my_chart/price.py)
2. `fetch_theme_list_page(page: int) -> str` - Fetch one page of theme list
3. `fetch_theme_detail_page(theme_id: int) -> str` - Fetch detail page for one theme
4. Both functions use time.sleep(CRAWL_DELAY) after request

### REFACTOR

None needed initially. Session initialization is simple enough.

---

## Phase 1.3: parser.py — HTML Parsing and Number Normalization

**File**: `backend/services/naver_theme/parser.py`  
**Lines**: ~200  
**Dependency**: config.py  

### RED: Test to_num() Function

```python
# tests/services/naver_theme/test_parser.py
import pytest
from backend.services.naver_theme.parser import to_num

@pytest.mark.unit
def test_to_num_integer():
    """to_num() converts integer strings."""
    assert to_num("1234") == 1234
    assert to_num("0") == 0

@pytest.mark.unit
def test_to_num_float():
    """to_num() converts float strings."""
    assert to_num("12.34") == 12.34
    assert to_num("0.5") == 0.5

@pytest.mark.unit
def test_to_num_with_commas():
    """to_num() removes commas before converting."""
    assert to_num("1,234,567") == 1234567
    assert to_num("1,234.56") == 1234.56

@pytest.mark.unit
def test_to_num_invalid():
    """to_num() returns 0 for invalid input."""
    assert to_num("invalid") == 0
    assert to_num("") == 0
    assert to_num("NaN") == 0
```

### RED: Test normalize_money() Function

```python
@pytest.mark.unit
def test_normalize_money_won():
    """normalize_money() handles Korean currency units."""
    # "1000억" → 100,000,000,000 (100 billion won)
    assert normalize_money("1000억") == 100_000_000_000
    assert normalize_money("1조") == 1_000_000_000_000
    assert normalize_money("100만") == 100_000_000

@pytest.mark.unit
def test_normalize_money_numeric():
    """normalize_money() handles plain numbers."""
    assert normalize_money("1000") == 1000
    assert normalize_money("1000.5") == 1000.5
```

### RED: Test parse_theme_list() Function

```python
@pytest.mark.unit
def test_parse_theme_list_returns_dataframe(theme_list_html_fixture):
    """parse_theme_list() returns a DataFrame with required columns."""
    from backend.services.naver_theme.parser import parse_theme_list
    df = parse_theme_list(theme_list_html_fixture)
    
    assert isinstance(df, pd.DataFrame)
    required_cols = ['theme_id', 'theme_name', 'change_pct', 'change_pct_3d', 
                     'up_count', 'flat_count', 'down_count', 'top_stocks_preview', 'collected_at']
    assert all(col in df.columns for col in required_cols)

@pytest.mark.unit
def test_parse_theme_list_korean_characters(theme_list_html_fixture):
    """parse_theme_list() preserves Korean characters without corruption."""
    from backend.services.naver_theme.parser import parse_theme_list
    df = parse_theme_list(theme_list_html_fixture)
    
    # Should have Korean theme names
    assert any("전" in str(name) or "금" in str(name) 
               for name in df['theme_name'].head())
    assert not any("?" in str(name) for name in df['theme_name'])
```

### GREEN: Implement parser.py

Implement:
1. `to_num(x: str) -> int | float` - From fnguide/parser.py reference
2. `normalize_money(s: str) -> int | float` - Handle Korean units (억, 조, 만)
3. `parse_theme_list(html: str) -> pd.DataFrame` - BeautifulSoup parsing
4. `parse_theme_detail(html: str, theme_id: int) -> list[dict]` - Extract stocks from detail page

### REFACTOR

Extract URL selector patterns to constants if needed.

---

## Phase 1.4: analyzer.py — Z-Score Scoring and Theme Analysis

**File**: `backend/services/naver_theme/analyzer.py`  
**Lines**: ~250  
**Dependency**: config.py, parser.py  

### RED: Test build_strong_themes()

```python
@pytest.mark.unit
def test_build_strong_themes_filters_by_momentum():
    """build_strong_themes() calculates momentum_score correctly."""
    from backend.services.naver_theme.analyzer import build_strong_themes
    
    themes_df = pd.DataFrame({
        'theme_id': [1, 2, 3],
        'theme_name': ['A', 'B', 'C'],
        'change_pct': [5.0, 2.0, -1.0],
        'change_pct_3d': [10.0, 3.0, 0.0],
    })
    
    result = build_strong_themes(themes_df)
    
    # momentum_score = change_pct * 0.6 + change_pct_3d * 0.4
    # A: 5*0.6 + 10*0.4 = 3 + 4 = 7.0
    # B: 2*0.6 + 3*0.4 = 1.2 + 1.2 = 2.4
    # C: -1*0.6 + 0*0.4 = -0.6 + 0 = -0.6
    
    assert 'momentum_score' in result.columns
    assert result[result['theme_id'] == 1]['momentum_score'].iloc[0] == 7.0
```

### RED: Test build_leaders()

```python
@pytest.mark.unit
def test_build_leaders_calculates_z_score():
    """build_leaders() calculates leader_score with z-score weights."""
    from backend.services.naver_theme.analyzer import build_leaders
    import numpy as np
    
    stocks_df = pd.DataFrame({
        'stock_code': ['000001', '000002', '000003'],
        'stock_name': ['A', 'B', 'C'],
        'change_pct': [5.0, 2.0, -1.0],
        'volume': [1000000, 500000, 200000],
        'market_cap': [100000000000, 50000000000, 20000000000],
        'trade_value': [50000000000, 25000000000, 10000000000],
        'theme_id': [1, 1, 1],
    })
    
    leaders_df = build_leaders(stocks_df, 3)
    
    # leader_score = z(change_pct)*0.40 + z(volume)*0.30 + z(market_cap)*0.20 + z(trade_value)*0.10
    # Should have leader_score column with computed values
    assert 'leader_score' in leaders_df.columns
    assert len(leaders_df) <= 3  # Top 3 per theme
    assert leaders_df['leader_score'].dtype in [np.float64, np.float32, 'float64']
```

### RED: Test build_multi_theme_stocks()

```python
@pytest.mark.unit
def test_build_multi_theme_stocks_filters_count():
    """build_multi_theme_stocks() filters stocks appearing in 2+ themes."""
    from backend.services.naver_theme.analyzer import build_multi_theme_stocks
    
    stocks_df = pd.DataFrame({
        'stock_code': ['001', '001', '002', '003', '001'],
        'stock_name': ['A', 'A', 'B', 'C', 'A'],
        'theme_id': [1, 2, 1, 2, 3],
        'theme_name': ['T1', 'T2', 'T1', 'T2', 'T3'],
    })
    
    result = build_multi_theme_stocks(stocks_df)
    
    # Stock '001' appears in themes 1, 2, 3 (count=3)
    # Stock '002' appears in theme 1 (count=1, filtered out)
    # Stock '003' appears in theme 2 (count=1, filtered out)
    
    assert 'theme_count' in result.columns
    assert all(result['theme_count'] >= 2)
    assert len(result[result['stock_code'] == '001']) > 0
    assert '001' not in result[result['stock_code'] == '002']['stock_code'].values
```

### GREEN: Implement analyzer.py

Implement:
1. `build_strong_themes(themes_df) -> pd.DataFrame` - Calculate momentum_score, sort, filter
2. `build_leaders(stocks_df, top_n=3) -> pd.DataFrame` - Z-score weighted scoring
3. `build_multi_theme_stocks(stocks_df) -> pd.DataFrame` - Filter theme_count >= 2
4. Helper: `_zscore(series)` - Compute z-scores with NaN handling

### REFACTOR

- Extract z-score logic to separate `_compute_weighted_score()` for reuse

---

## Phase 1.5: service.py — Main Service Orchestration

**File**: `backend/services/naver_theme/service.py`  
**Lines**: ~250  
**Dependency**: config.py, crawler.py, parser.py, analyzer.py  

### RED: Test ThemeAnalysisResult Dataclass

```python
@pytest.mark.unit
def test_theme_analysis_result_structure():
    """ThemeAnalysisResult has required attributes."""
    from backend.services.naver_theme.service import ThemeAnalysisResult
    import pandas as pd
    
    empty_df = pd.DataFrame()
    result = ThemeAnalysisResult(
        themes_df=empty_df,
        stocks_df=empty_df,
        strong_themes_df=empty_df,
        leaders_df=empty_df,
        multi_theme_stocks_df=empty_df,
        metadata={'test': True}
    )
    
    assert hasattr(result, 'themes_df')
    assert hasattr(result, 'stocks_df')
    assert hasattr(result, 'strong_themes_df')
    assert hasattr(result, 'leaders_df')
    assert hasattr(result, 'multi_theme_stocks_df')
    assert hasattr(result, 'metadata')
```

### RED: Test collect_and_analyze() Entry Point

```python
@pytest.mark.unit
@patch('backend.services.naver_theme.crawler.fetch_theme_list_page')
@patch('backend.services.naver_theme.crawler.fetch_theme_detail_page')
@patch('backend.services.naver_theme.parser.parse_theme_list')
@patch('backend.services.naver_theme.parser.parse_theme_detail')
def test_collect_and_analyze_returns_result(mock_detail_parse, mock_list_parse, 
                                            mock_detail_fetch, mock_list_fetch):
    """collect_and_analyze() returns ThemeAnalysisResult with 5 DataFrames."""
    # Set up mocks to return minimal valid data
    mock_list_fetch.return_value = "<html></html>"
    mock_detail_fetch.return_value = "<html></html>"
    mock_list_parse.return_value = pd.DataFrame({
        'theme_id': [1],
        'theme_name': ['Test'],
        'change_pct': [1.0],
        'change_pct_3d': [1.0],
    })
    mock_detail_parse.return_value = [{
        'stock_code': '001',
        'stock_name': 'Test Stock',
        'change_pct': 1.0,
        'volume': 1000,
    }]
    
    from backend.services.naver_theme.service import collect_and_analyze
    result = collect_and_analyze(top_n_themes=5, skip_details=True)
    
    assert isinstance(result.themes_df, pd.DataFrame)
    assert isinstance(result.stocks_df, pd.DataFrame)
    assert isinstance(result.strong_themes_df, pd.DataFrame)
    assert isinstance(result.leaders_df, pd.DataFrame)
    assert isinstance(result.multi_theme_stocks_df, pd.DataFrame)
    assert isinstance(result.metadata, dict)
```

### RED: Test Metadata Recording

```python
@pytest.mark.unit
def test_collect_and_analyze_metadata():
    """Metadata contains collected_at, theme_count, stock_count, elapsed_sec, errors."""
    from backend.services.naver_theme.service import collect_and_analyze
    
    # Use mocks as above
    result = collect_and_analyze()
    
    assert 'collected_at' in result.metadata
    assert 'theme_count' in result.metadata
    assert 'stock_count' in result.metadata
    assert 'elapsed_sec' in result.metadata
    assert 'errors' in result.metadata
    assert isinstance(result.metadata['errors'], list)
```

### GREEN: Implement service.py

Implement:
1. `ThemeAnalysisResult` - Dataclass with 5 DataFrames + metadata
2. `collect_and_analyze(top_n_themes=20, leaders_per_theme=3, skip_details=False) -> ThemeAnalysisResult`
   - Fetch theme list pages (paginate until end)
   - If skip_details=False: Fetch detail for each theme
   - Parse all data
   - Compute strong themes, leaders, multi-theme stocks
   - Record metadata (collected_at, counts, elapsed_sec, errors)
   - Return ThemeAnalysisResult
3. Error handling: Catch exceptions, collect in errors list, continue

### REFACTOR

- Extract pagination logic to `_fetch_all_theme_pages()`
- Extract detail collection to `_fetch_all_theme_details()`

---

## Phase 1.6: routes/themes.py — API Endpoints

**File**: `backend/routers/themes.py`  
**Lines**: ~120  
**Dependency**: service.py  

### RED: Test /api/themes/snapshot Endpoint

```python
# tests/routers/test_themes.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.mark.unit
def test_themes_snapshot_endpoint():
    """GET /api/themes/snapshot returns list of themes."""
    response = client.get("/api/themes/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.unit
def test_themes_snapshot_with_top_n():
    """GET /api/themes/snapshot?top_n=5 returns top 5 themes."""
    response = client.get("/api/themes/snapshot?top_n=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
```

### RED: Test /api/themes/by-stock/{code} Endpoint

```python
@pytest.mark.unit
def test_themes_by_stock_endpoint():
    """GET /api/themes/by-stock/005930 returns themes for stock."""
    response = client.get("/api/themes/by-stock/005930")
    assert response.status_code in [200, 404]  # May not exist
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
```

### GREEN: Implement routes/themes.py

Implement three endpoints:
1. `GET /api/themes/snapshot` - Returns themes_df (paginated)
2. `GET /api/themes/quick` - Returns strong themes only (skip_details=True)
3. `GET /api/themes/by-stock/{code}` - Returns themes containing stock code

Register router in backend/main.py after sectors_router.

### REFACTOR

- Extract response models to Pydantic BaseModel

---

## Phase 2: Unit Tests — Coverage Completion

**Files**: `tests/services/naver_theme/test_*.py`  
**Coverage Target**: >= 85%  

Run after Phase 1 implementation:

```bash
pytest tests/services/naver_theme/ \
  --cov=backend/services/naver_theme \
  --cov-report=term-missing \
  --cov-fail-under=85 \
  -v
```

If coverage < 85%, identify gaps and write additional tests.

---

## Phase 3: Integration Tests

**Files**: `tests/integration/test_naver_theme_e2e.py`  

```python
@pytest.mark.slow
@pytest.mark.integration
def test_collect_and_analyze_with_real_data():
    """Full end-to-end test with real network calls."""
    from backend.services.naver_theme.service import collect_and_analyze
    
    result = collect_and_analyze(top_n_themes=5, skip_details=False)
    
    # Verify all DFs populated
    assert len(result.themes_df) > 0
    assert len(result.stocks_df) > 0
    # ... AC validations ...
```

---

## Risk Assessment

### Risk 1: Network Failures
**Mitigation**: Retry adapter (max_retries=1) + timeout=10s. Collect errors in metadata.

### Risk 2: Character Encoding
**Mitigation**: BeautifulSoup with lxml parser (handles UTF-8 well). Validate in AC-2 test.

### Risk 3: Z-Score Edge Cases
**Mitigation**: Handle single-value or all-zero series. Use numpy.isnan() and fillna(0).

### Risk 4: Timing Measurement
**Mitigation**: Use time.time() at start/end. Measure sleep() in slow tests with @pytest.mark.slow.

### Risk 5: Crawl Delay Accuracy
**Mitigation**: AC-6 test measures total elapsed time. Target >= 18 seconds for default call (0.7 × ~27 requests).

---

## Success Criteria (for expert-backend)

✅ All RED tests written before any GREEN implementation  
✅ All GREEN tests pass (service.py imports correctly, endpoints registered)  
✅ 85%+ code coverage achieved  
✅ AC-1 through AC-9 pass  
✅ No existing features broken (sectors, screens, charts still work)  
✅ Commit messages follow convention: `feat(naver-theme): {phase} — {what}`  

---

## Next Phases (after Phase 1)

- **Phase 2**: expert-frontend implements ThemeAnalysis.tsx components
- **Phase 3**: expert-testing writes E2E tests
- **Phase 4**: manager-quality validates TRUST 5
- **Phase 5**: manager-docs creates API documentation

---

**Ready for expert-backend to begin Phase 1.1 implementation.**
