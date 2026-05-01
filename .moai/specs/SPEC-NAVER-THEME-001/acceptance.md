# 인수 조건 (Acceptance Criteria): SPEC-NAVER-THEME-001 V1

**Version**: 1.0.0 | **Validation Method**: Automated + Manual | **Sign-off**: Product Owner

---

## AC 1: 5종 DataFrame + Metadata 반환

**요구사항**: `collect_and_analyze()` 호출 1회로 정확히 5종 DataFrame과 metadata dict 반환

**테스트 스크립트**:
```python
from modules.naver_theme.service import collect_and_analyze

result = collect_and_analyze(top_n_themes=20, leaders_per_theme=3, skip_details=False)

# 검증
assert isinstance(result.themes_df, pd.DataFrame)
assert isinstance(result.stocks_df, pd.DataFrame)
assert isinstance(result.strong_themes_df, pd.DataFrame)
assert isinstance(result.leaders_df, pd.DataFrame)
assert isinstance(result.multi_theme_stocks_df, pd.DataFrame)
assert isinstance(result.metadata, dict)

# 각 DataFrame의 필수 컬럼 확인
assert 'theme_id' in result.themes_df.columns
assert 'stock_code' in result.stocks_df.columns
assert 'leader_score' in result.leaders_df.columns
assert 'theme_count' in result.multi_theme_stocks_df.columns
assert 'collected_at' in result.metadata
```

**합격선**:
- 5개 DataFrame 모두 반환됨
- 각 DataFrame의 필수 컬럼 확인 완료
- metadata dict에 collected_at, theme_count, stock_count, elapsed_sec, errors 포함

---

## AC 2: 한글 깨짐 없음

**요구사항**: 테마명, 종목명 모두 UTF-8로 정확하게 인코딩되어 깨지지 않음

**테스트 스크립트**:
```python
result = collect_and_analyze()

# 테마명 샘플
sample_themes = result.themes_df['theme_name'].head()
for name in sample_themes:
    assert all(ord(c) < 0x110000 for c in name), f"Invalid character in {name}"
    assert "?" not in name, "Replacement character found"

# 종목명 샘플
sample_stocks = result.stocks_df['stock_name'].head()
for name in sample_stocks:
    assert all(ord(c) < 0x110000 for c in name), f"Invalid character in {name}"

# 실제 한글 확인
assert any("전" in str(t) or "금" in str(t) or "테" in str(t) for t in result.themes_df['theme_name']), \
    "No Korean characters found in theme names"
```

**합격선**:
- 테마명/종목명에 한글 포함됨 (샘플: "전선", "AI반도체", "삼성전자" 등)
- ? 또는 기타 깨짐 문자 없음
- UTF-8 유효성 검사 통과

---

## AC 3: 시가총액·거래대금 원 단위 통일

**요구사항**: market_cap, trade_value 모두 정수 원 단위로 저장되어 있음

**테스트 스크립트**:
```python
result = collect_and_analyze()
stocks_df = result.stocks_df

# 시가총액 단위 검증
assert stocks_df['market_cap'].dtype in [int, 'int64', 'int32'], \
    f"market_cap should be int, got {stocks_df['market_cap'].dtype}"

# 거래대금 단위 검증
assert stocks_df['trade_value'].dtype in [int, 'int64', 'int32'], \
    f"trade_value should be int, got {stocks_df['trade_value'].dtype}"

# 값 범위 검증 (합리적 범위)
assert (stocks_df['market_cap'] > 0).all() or stocks_df['market_cap'].isna().any(), \
    "market_cap should be > 0 or NaN"

# 샘플: 삼성전자 시가총액 ~ 30조 (3e13)
samsung_market_cap = stocks_df[stocks_df['stock_name'] == '삼성전자']['market_cap'].max()
assert samsung_market_cap > 1e13 if not pd.isna(samsung_market_cap), \
    "Samsung market_cap seems too small"
```

**합격선**:
- market_cap, trade_value 모두 int 타입 (또는 nullable int64)
- 모든 값이 >= 0 (또는 NaN)
- 대형주 (삼성전자) 시가총액 > 10조 확인
- "억" 또는 "백만" 문자 포함 안 됨

---

## AC 4: Leader Score 가중치 정확 (0.4 / 0.3 / 0.2 / 0.1)

**요구사항**: leader_score = z(change_pct)*0.40 + z(volume)*0.30 + z(market_cap)*0.20 + z(trade_value)*0.10

**테스트 스크립트**:
```python
result = collect_and_analyze()
leaders_df = result.leaders_df

# 첫 번째 테마의 주도주 3개에 대해 점수 재계산
first_theme_id = result.stocks_df['theme_id'].iloc[0]
theme_stocks = result.stocks_df[result.stocks_df['theme_id'] == first_theme_id]

# z-score 계산
for col in ['change_pct', 'volume', 'market_cap', 'trade_value']:
    mean = theme_stocks[col].mean()
    std = theme_stocks[col].std()
    if std == 0:
        theme_stocks[f'{col}_z'] = 0
    else:
        theme_stocks[f'{col}_z'] = (theme_stocks[col] - mean) / std

# 재계산한 점수
expected_scores = (
    theme_stocks['change_pct_z'] * 0.40 +
    theme_stocks['volume_z'] * 0.30 +
    theme_stocks['market_cap_z'] * 0.20 +
    theme_stocks['trade_value_z'] * 0.10
)

# 실제 점수와 비교 (허용 오차 ±0.01)
actual_leaders = leaders_df[leaders_df['theme_id'] == first_theme_id].sort_values('rank')
for actual, expected in zip(actual_leaders['leader_score'], expected_scores.head(3)):
    assert abs(actual - expected) < 0.01, \
        f"Score mismatch: {actual} vs {expected}"
```

**합격선**:
- leader_score의 재계산 값과 실제 값의 차이 < 0.01 (부동소수점 오차 허용)
- 4개 가중치 합 = 1.0 확인
- 음수 등락률도 그대로 반영 (음수 점수 가능)

---

## AC 5: 페이지네이션 자동 탐지

**요구사항**: 마지막 페이지를 하드코딩하지 않고 동적으로 탐지

**테스트 스크립트**:
```python
# 크롤링 로그 또는 메타데이터에서 페이지 수 확인
result = collect_and_analyze()

# themes_df의 행 수가 합리적인가? (네이버는 보통 40~50개 테마)
assert len(result.themes_df) >= 20, \
    f"Too few themes collected: {len(result.themes_df)}"

assert len(result.themes_df) <= 200, \
    f"Too many themes (likely infinite loop): {len(result.themes_df)}"

# 각 페이지에서 일정한 행 수 (약 10개/페이지)를 수집했는가?
# → 로그에서 페이지 수 확인 (강제로 검사할 수 없으므로 수동 검증)
```

**합격선**:
- themes_df 행 수: 20~100개 범위
- 페이지네이션 로직이 코드에서 "hardcoded 숫자"가 아님
- 실제 네이버 페이지 구조 변경 시 자동 대응 가능

---

## AC 6: 호출 간 Sleep ≥ 0.7초 실측

**요구사항**: 각 HTTP 요청 사이에 0.7초 이상의 대기 시간 존재

**테스트 스크립트**:
```python
import time
from unittest.mock import patch

# 실제 크롤링 시간 측정
start = time.time()
result = collect_and_analyze()
elapsed = time.time() - start

# HTTP 호출 수 추정: 테마 7페이지 + 강세 테마 20개 상세 = 27회
# 예상 시간: 27회 * 0.7초 = 18.9초 (최소값)
assert elapsed >= 18, \
    f"Total time too short ({elapsed}s), may not include sleep delays"

# 더 정확한 검증: mock으로 sleep 호출 수 추적
with patch('time.sleep') as mock_sleep:
    result = collect_and_analyze()
    
    # sleep 호출 횟수 >= 27 (또는 유사한 수)
    sleep_calls = mock_sleep.call_count
    assert sleep_calls >= 20, \
        f"Too few sleep calls: {sleep_calls}"
    
    # 각 호출의 인자가 >= 0.7초
    for call in mock_sleep.call_args_list:
        sleep_time = call[0][0]
        assert sleep_time >= 0.7, \
            f"Sleep time too short: {sleep_time}s"
```

**합격선**:
- 총 소요 시간 >= 18초 (27회 × 0.7초 기본)
- 코드에서 `time.sleep(CRAWL_DELAY)` 또는 유사 호출 확인
- mock 검증: sleep_calls >= 20, 각 호출 >= 0.7초

---

## AC 7: 부분 실패 허용 + errors 기록

**요구사항**: 일부 테마/종목 파싱 실패 시에도 진행 계속, errors에 기록

**테스트 스크립트**:
```python
# 네이버 응답 1개를 고의로 실패시키는 mock
import json
from unittest.mock import patch

def mock_fetch_fail(url):
    if "page=2" in url:
        raise requests.exceptions.HTTPError("429 Too Many Requests")
    return real_fetch(url)

with patch('backend.services.naver_theme.crawler.requests.get', side_effect=mock_fetch_fail):
    result = collect_and_analyze()
    
    # 에러 기록 확인
    assert len(result.metadata['errors']) > 0, \
        "Expected error to be recorded"
    
    # 하지만 다른 테마는 계속 반환됨
    assert len(result.themes_df) > 0, \
        "Should return partial results despite error"
    
    # 에러 형식
    error = result.metadata['errors'][0]
    assert 'stage' in error, "Error should include stage"
    assert 'reason' in error, "Error should include reason"
```

**합격선**:
- 일부 테마 크롤링 실패 시에도 정상 테마는 반환됨
- metadata['errors'] 리스트에 오류 기록됨
- 각 error는 {'stage': str, 'reason': str} 형식

---

## AC 8: skip_details=True 시 10초 이내

**요구사항**: skip_details=True로 호출 시 10초 이내에 응답 (빠른 모드)

**테스트 스크립트**:
```python
import time

start = time.time()
result = collect_and_analyze(skip_details=True)
elapsed = time.time() - start

assert elapsed <= 10, \
    f"Quick mode took too long: {elapsed}s"

# 상세 데이터는 없어야 함
assert len(result.stocks_df) == 0, \
    "stocks_df should be empty in quick mode"

assert len(result.leaders_df) == 0, \
    "leaders_df should be empty in quick mode"

# 하지만 테마 목록은 있어야 함
assert len(result.themes_df) > 0, \
    "themes_df should have data in quick mode"

assert len(result.strong_themes_df) > 0, \
    "strong_themes_df should have data in quick mode"
```

**합격선**:
- skip_details=True 호출 완료 시간 <= 10초
- stocks_df, leaders_df, multi_theme_stocks_df 모두 빈 상태
- themes_df, strong_themes_df는 데이터 포함

---

## AC 9: 단위 테스트 (Parser & Analyzer Fixture 기반)

**요구사항**: parser, analyzer 모두 fixture 기반 단위 테스트로 커버 >= 85%

**테스트 파일**: `tests/test_naver_theme_parser.py`, `tests/test_naver_theme_analyzer.py`

**예시**:
```python
@pytest.mark.unit
def test_parser_theme_list():
    """Fixture HTML에서 테마 목록 파싱."""
    with open('tests/fixtures/naver_theme/theme_list_page1.html') as f:
        html = f.read()
    
    result = parse_theme_list(html, page=1)
    
    assert len(result['themes']) > 0
    assert result['themes'][0]['theme_id'] > 0
    assert 'theme_name' in result['themes'][0]

@pytest.mark.unit
def test_analyzer_leader_score():
    """z-score 기반 leader_score 계산."""
    # 임의 테마 데이터
    stocks_data = {
        'stock_code': ['005930', '006260'],
        'stock_name': ['삼성전자', 'LS'],
        'change_pct': [1.5, 2.0],
        'volume': [1000000, 500000],
        'market_cap': [300000000000, 10000000000],
        'trade_value': [300000000000, 5000000000],
    }
    stocks_df = pd.DataFrame(stocks_data)
    
    leaders = build_leaders(stocks_df, leaders_per_theme=2)
    
    assert len(leaders) == 2
    assert 'leader_score' in leaders.columns
    assert leaders['leader_score'].notna().all()
```

**합격선**:
- `pytest tests/ -m unit --cov=backend.services.naver_theme --cov-report=term-missing`
- 커버리지 >= 85%
- 모든 단위 테스트 PASS

---

## AC 10: 외부 사용 가능 (Import 1줄)

**요구사항**: 외부에서 `from modules.naver_theme.service import collect_and_analyze` 한 줄로 사용 가능

**테스트 스크립트**:
```python
# backend/routers/themes.py 또는 테스트에서
from modules.naver_theme.service import collect_and_analyze, ThemeAnalysisResult

# 직접 호출
result = collect_and_analyze()

# 타입 힌팅
assert isinstance(result, ThemeAnalysisResult)
```

**합격선**:
- `from modules.naver_theme.service import ...` 정상 동작
- __init__.py에서 collect_and_analyze 노출됨
- 다른 모듈은 구현 세부사항이므로 import 불필요

---

## 최종 서명 기준

| AC | 테스트 방법 | 합격/불합격 |
|----|-----------|-----------|
| 1 | 자동 | ✅ |
| 2 | 자동 | ✅ |
| 3 | 자동 | ✅ |
| 4 | 자동 | ✅ |
| 5 | 자동 + 수동 | ✅ |
| 6 | 자동 | ✅ |
| 7 | 자동 | ✅ |
| 8 | 자동 | ✅ |
| 9 | 자동 (pytest) | ✅ |
| 10 | 자동 | ✅ |

**모든 AC 통과 시**: ✅ V1 Production Ready

