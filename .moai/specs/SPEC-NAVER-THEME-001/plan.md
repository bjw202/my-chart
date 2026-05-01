# 구현 계획: SPEC-NAVER-THEME-001 V1

**Version**: 1.0.0 | **Status**: Ready for Execution | **Estimated Duration**: 3-4 days

---

## 1. Phase 분해 (RUN Phase)

### Phase 1: 백엔드 모듈 구현

**담당**: expert-backend
**예상 시간**: 2일
**블로킹**: 없음 (기존 코드에 의존하지만 모두 READ-ONLY)

#### 1.1 기본 구조 및 Config (0.5일)

**파일**: `backend/services/naver_theme/config.py`

```python
# 상수
NAVER_THEME_LIST_URL = "https://finance.naver.com/sise/theme.naver?&page={n}"
NAVER_THEME_DETAIL_URL = "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}"

CRAWL_DELAY = 0.7  # 초 (설정 가능)
REQUEST_TIMEOUT = 10
MAX_RETRIES = 1
USER_AGENT = "KR-Stock-Screener/1.0 (naver_theme_analysis)"

# 가중치
MOMENTUM_WEIGHT_1D = 0.6
MOMENTUM_WEIGHT_3D = 0.4

LEADER_SCORE_WEIGHTS = {
    'change_pct': 0.40,
    'volume': 0.30,
    'market_cap': 0.20,
    'trade_value': 0.10,
}

# 기본값
DEFAULT_TOP_N_THEMES = 20
DEFAULT_LEADERS_PER_THEME = 3
```

#### 1.2 Crawler 구현 (0.5일)

**파일**: `backend/services/naver_theme/crawler.py`

**패턴**: price.py (Session 싱글톤) + fnguide/crawler.py 모방

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

_session: requests.Session | None = None

def _get_session() -> requests.Session:
    """Session 싱글톤 with Retry adapter."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session

def fetch_theme_list_page(page: int) -> str:
    """네이버 테마 목록 페이지 HTML 반환."""
    session = _get_session()
    url = NAVER_THEME_LIST_URL.format(n=page)
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    time.sleep(CRAWL_DELAY)
    return resp.text

def fetch_theme_detail_page(theme_id: int) -> str:
    """테마 상세 페이지 HTML 반환."""
    session = _get_session()
    url = NAVER_THEME_DETAIL_URL.format(theme_id=theme_id)
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    time.sleep(CRAWL_DELAY)
    return resp.text
```

#### 1.3 Parser 구현 (0.5일)

**파일**: `backend/services/naver_theme/parser.py`

**패턴**: fnguide/parser.py::to_num() 모방

```python
from bs4 import BeautifulSoup
import pandas as pd
from typing import Any

def to_num(x: str) -> int | float:
    """콤마 포맷 문자열을 int 또는 float으로 변환."""
    num = x.replace(",", "").strip()
    try:
        if "." in num:
            return float(num)
        return int(num)
    except ValueError:
        return 0

def normalize_money(value_str: str) -> int:
    """
    "524억", "1.2조", "500만" 등을 원 단위로 정규화.
    
    Examples:
        "524억" → 52400000000
        "1.2조" → 1200000000000
        "500만" → 5000000
    """
    value_str = value_str.strip()
    if "조" in value_str:
        base = float(value_str.replace("조", ""))
        return int(base * 1_000_000_000_000)
    elif "억" in value_str:
        base = float(value_str.replace("억", ""))
        return int(base * 100_000_000)
    elif "백만" in value_str:
        base = float(value_str.replace("백만", ""))
        return int(base * 1_000_000)
    else:
        return to_num(value_str)

def parse_theme_list(html: str, page: int) -> dict[str, Any]:
    """
    테마 목록 페이지 HTML을 파싱하여 테마 데이터 딕셔너리 반환.
    
    Returns:
        {
            'themes': [
                {'theme_id': int, 'theme_name': str, 'change_pct': float, ...},
                ...
            ],
            'last_page': int (페이지네이션 마지막 페이지)
        }
    """
    soup = BeautifulSoup(html, 'html.parser')
    themes = []
    
    # BeautifulSoup 선택자로 테이블 행 찾기
    # (네이버 HTML 구조에 맞게 수정 필요)
    rows = soup.select("table tbody tr")
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue
        
        theme_id = to_num(cells[0].text)
        theme_name = cells[1].text.strip()
        change_pct = to_num(cells[2].text)
        change_pct_3d = to_num(cells[3].text)
        up_count = to_num(cells[4].text)
        flat_count = to_num(cells[5].text)
        down_count = to_num(cells[6].text)
        
        themes.append({
            'theme_id': theme_id,
            'theme_name': theme_name,
            'change_pct': change_pct,
            'change_pct_3d': change_pct_3d,
            'up_count': up_count,
            'flat_count': flat_count,
            'down_count': down_count,
        })
    
    # 마지막 페이지 탐지
    last_page = page  # 기본값
    pagination = soup.select("a.page")
    if pagination:
        last_page = max(
            int(a.text) for a in pagination 
            if a.text.isdigit()
        )
    
    return {'themes': themes, 'last_page': last_page}

def parse_theme_detail(html: str, theme_id: int, theme_name: str) -> list[dict]:
    """테마 상세 페이지에서 종목 리스트 파싱."""
    soup = BeautifulSoup(html, 'html.parser')
    stocks = []
    
    rows = soup.select("table tbody tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 8:
            continue
        
        stock = {
            'theme_id': theme_id,
            'theme_name': theme_name,
            'stock_code': cells[0].text.strip(),
            'stock_name': cells[1].text.strip(),
            'price': to_num(cells[2].text),
            'change': to_num(cells[3].text),
            'change_pct': to_num(cells[4].text),
            'volume': to_num(cells[5].text),
            'trade_value': normalize_money(cells[6].text),
            'per': to_num(cells[7].text) if len(cells) > 7 else float('nan'),
        }
        stocks.append(stock)
    
    return stocks
```

#### 1.4 Analyzer 구현 (0.5일)

**파일**: `backend/services/naver_theme/analyzer.py`

```python
import pandas as pd
import numpy as np
from datetime import datetime

def build_strong_themes(themes_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """강세 테마 추출 및 점수 계산."""
    df = themes_df.copy().head(top_n)
    
    df['momentum_score'] = (
        df['change_pct'] * 0.6 + 
        df['change_pct_3d'] * 0.4
    )
    
    df['breadth_ratio'] = (
        df['up_count'] / 
        (df['up_count'] + df['flat_count'] + df['down_count'])
    ).fillna(0)
    
    return df.sort_values('change_pct', ascending=False)

def build_leaders(stocks_df: pd.DataFrame, leaders_per_theme: int = 3) -> pd.DataFrame:
    """주도주 산출 (z-score 기반 점수)."""
    leaders = []
    
    for theme_id, group in stocks_df.groupby('theme_id'):
        theme_name = group['theme_name'].iloc[0]
        
        # z-score 계산
        for col in ['change_pct', 'volume', 'market_cap', 'trade_value']:
            mean = group[col].mean()
            std = group[col].std()
            if std == 0:
                group[f'{col}_z'] = 0
            else:
                group[f'{col}_z'] = (group[col] - mean) / std
        
        # leader_score 계산
        group['leader_score'] = (
            group['change_pct_z'] * 0.40 +
            group['volume_z'] * 0.30 +
            group['market_cap_z'] * 0.20 +
            group['trade_value_z'] * 0.10
        )
        
        # 상위 K개
        top_k = group.nlargest(leaders_per_theme, 'leader_score')
        for rank, (_, row) in enumerate(top_k.iterrows(), 1):
            leaders.append({
                'theme_id': theme_id,
                'theme_name': theme_name,
                'rank': rank,
                'stock_code': row['stock_code'],
                'stock_name': row['stock_name'],
                'leader_score': row['leader_score'],
                'change_pct': row['change_pct'],
                'volume': row['volume'],
                'market_cap': row['market_cap'],
                'trade_value': row['trade_value'],
            })
    
    return pd.DataFrame(leaders)

def build_multi_theme_stocks(stocks_df: pd.DataFrame) -> pd.DataFrame:
    """멀티테마 종목 추출."""
    grouped = stocks_df.groupby('stock_code').agg({
        'stock_name': 'first',
        'theme_name': lambda x: x.tolist(),
        'theme_id': 'count',
        'change_pct': 'mean',
    }).reset_index()
    
    grouped.columns = ['stock_code', 'stock_name', 'theme_names', 'theme_count', 'avg_change_pct']
    
    return grouped[grouped['theme_count'] >= 2].sort_values('theme_count', ascending=False)
```

#### 1.5 Service 진입점 (0.5일)

**파일**: `backend/services/naver_theme/service.py`

```python
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from .crawler import fetch_theme_list_page, fetch_theme_detail_page
from .parser import parse_theme_list, parse_theme_detail
from .analyzer import build_strong_themes, build_leaders, build_multi_theme_stocks
from backend.deps import get_db_conn, DAILY_DB_PATH

@dataclass
class ThemeAnalysisResult:
    themes_df: pd.DataFrame
    stocks_df: pd.DataFrame
    strong_themes_df: pd.DataFrame
    leaders_df: pd.DataFrame
    multi_theme_stocks_df: pd.DataFrame
    metadata: dict

def collect_and_analyze(
    top_n_themes: int = 20,
    leaders_per_theme: int = 3,
    skip_details: bool = False,
    theme_filter: list[str] | None = None,
) -> ThemeAnalysisResult:
    """
    네이버 테마 데이터 수집 및 분석 (메인 진입점).
    """
    start_time = time.time()
    errors = []
    
    try:
        # Step 1: 테마 목록 수집
        themes_list = []
        page = 1
        last_page = 1
        
        while page <= last_page:
            try:
                html = fetch_theme_list_page(page)
                result = parse_theme_list(html, page)
                themes_list.extend(result['themes'])
                last_page = result['last_page']
                page += 1
            except Exception as e:
                errors.append({
                    'stage': 'list',
                    'page': page,
                    'reason': str(e),
                })
                page += 1
        
        themes_df = pd.DataFrame(themes_list)
        themes_df['collected_at'] = datetime.now(timezone.utc).isoformat()
        
        # Step 2: 강세 테마 추출
        strong_themes_df = build_strong_themes(themes_df, top_n_themes)
        
        # Step 3: 종목 상세 수집 (skip_details=True면 생략)
        stocks_list = []
        if not skip_details:
            for _, theme in strong_themes_df.iterrows():
                try:
                    html = fetch_theme_detail_page(int(theme['theme_id']))
                    stocks = parse_theme_detail(html, int(theme['theme_id']), theme['theme_name'])
                    stocks_list.extend(stocks)
                except Exception as e:
                    errors.append({
                        'theme_id': int(theme['theme_id']),
                        'stage': 'detail',
                        'reason': str(e),
                    })
            
            stocks_df = pd.DataFrame(stocks_list)
            
            # Step 4: 시가총액 보강 (DB JOIN)
            if len(stocks_df) > 0:
                stocks_df = _enrich_market_cap(stocks_df)
            
            # Step 5: 주도주 및 멀티테마 계산
            leaders_df = build_leaders(stocks_df, leaders_per_theme)
            multi_theme_stocks_df = build_multi_theme_stocks(stocks_df)
        else:
            stocks_df = pd.DataFrame()
            leaders_df = pd.DataFrame()
            multi_theme_stocks_df = pd.DataFrame()
        
        stocks_df['collected_at'] = datetime.now(timezone.utc).isoformat()
        
    except Exception as e:
        logger.error(f"collect_and_analyze failed: {e}")
        raise
    
    elapsed = time.time() - start_time
    
    return ThemeAnalysisResult(
        themes_df=themes_df,
        stocks_df=stocks_df,
        strong_themes_df=strong_themes_df,
        leaders_df=leaders_df,
        multi_theme_stocks_df=multi_theme_stocks_df,
        metadata={
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'theme_count': len(themes_df),
            'stock_count': len(stocks_df),
            'elapsed_sec': elapsed,
            'errors': errors,
        }
    )

def _enrich_market_cap(stocks_df: pd.DataFrame) -> pd.DataFrame:
    """DB에서 시가총액 조회 및 join."""
    conn = get_db_conn(DAILY_DB_PATH)
    try:
        codes = stocks_df['stock_code'].unique().tolist()
        placeholders = ",".join("?" * len(codes))
        query = f"SELECT code, market_cap FROM stock_meta WHERE code IN ({placeholders})"
        rows = conn.execute(query, codes).fetchall()
        
        market_cap_dict = {row[0]: row[1] for row in rows}
        stocks_df['market_cap'] = stocks_df['stock_code'].map(
            lambda code: market_cap_dict.get(code, None)
        )
        return stocks_df
    finally:
        conn.close()
```

### Phase 2: FastAPI 라우터 추가 (0.5일)

**담당**: expert-backend

**파일**: `backend/routers/themes.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.naver_theme.service import collect_and_analyze

router = APIRouter()

@router.get("/themes/snapshot")
async def themes_snapshot(
    top_n: int = 20,
    leaders_per_theme: int = 3,
) -> dict:
    """5종 DataFrame JSON 반환."""
    try:
        result = collect_and_analyze(
            top_n_themes=top_n,
            leaders_per_theme=leaders_per_theme,
            skip_details=False,
        )
        return {
            'themes': result.themes_df.to_dict(orient='records'),
            'stocks': result.stocks_df.to_dict(orient='records'),
            'strong_themes': result.strong_themes_df.to_dict(orient='records'),
            'leaders': result.leaders_df.to_dict(orient='records'),
            'multi_theme_stocks': result.multi_theme_stocks_df.to_dict(orient='records'),
            'metadata': result.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/themes/quick")
async def themes_quick(top_n: int = 20) -> dict:
    """빠른 모드 (테마 목록만, 10초 이내)."""
    try:
        result = collect_and_analyze(
            top_n_themes=top_n,
            skip_details=True,
        )
        return {
            'themes': result.themes_df.to_dict(orient='records'),
            'strong_themes': result.strong_themes_df.to_dict(orient='records'),
            'metadata': result.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/themes/by-stock/{code}")
async def themes_by_stock(code: str) -> list:
    """종목이 속한 테마 목록."""
    # 서버측 캐시에서 조회 (별도 구현)
    # 또는 모든 stock_df를 메모리에서 필터링
    ...
```

**backend/main.py 수정** (3줄 추가):

```python
# line ~24
from backend.routers.themes import router as themes_router

# line ~114
app.include_router(themes_router, prefix="/api")
```

### Phase 3: 프론트엔드 컴포넌트 (1일)

**담당**: expert-frontend

**파일**: `frontend/src/components/ThemeAnalysis/`

- ThemeAnalysis.tsx (컨테이너, 좌우 2열)
- ThemeRankingTable.tsx (테이블, SectorRankingTable 패턴)
- ThemeDetailPanel.tsx (상세 패널, SectorDetailPanel 패턴)

**파일**: `frontend/src/api/themes.ts`

```typescript
export async function fetchThemesSnapshot(
  topN?: number,
  leadersPerTheme?: number,
): Promise<ThemeAnalysisResponse> { ... }

export async function fetchThemesQuick(topN?: number): Promise<...> { ... }

export async function fetchThemesByStock(code: string): Promise<ThemeInfo[]> { ... }
```

**파일**: 타입 & 컨텍스트 수정

- `frontend/src/types/market.ts`: TabId에 'theme-analysis' 추가
- `frontend/src/contexts/TabContext.tsx`: CrossTabParams에 themeId, themeName 추가
- `frontend/src/components/TabNavigation/TabNavigation.tsx`: TABS 배열에 항목 추가
- `frontend/src/AppContent.tsx`: 조건부 렌더링 추가

### Phase 4: 테스트 작성 (0.5일)

**담당**: expert-testing

**파일**: `tests/test_naver_theme_parser.py`, `tests/test_naver_theme_analyzer.py`

- Fixture 기반 단위 테스트 (parser, analyzer)
- @pytest.mark.slow, @pytest.mark.live 마커

### Phase 5: 통합 & 배포 (0.5일)

**담당**: manager-quality + expert-backend

- API 통합 테스트 (라우터)
- 엔드투엔드 테스트 (프론트 ↔ 백)
- 라이브 크롤링 테스트 (선택)
- 문서 정리

---

## 2. 담당 역할 분담

| 역할 | 담당자 | 작업 | 예상 시간 |
|------|--------|------|---------|
| expert-backend | — | crawler + parser + analyzer + service + router | 2일 |
| expert-frontend | — | components + API client + types | 1일 |
| expert-testing | — | fixtures + unit tests | 0.5일 |
| manager-quality | — | 통합 + AC 검증 | 0.5일 |

---

## 3. 의존성 및 병렬화

**병렬 가능**:
- Phase 2 (라우터) ← Phase 1 (모듈) 완료 후 (1개 부분 병렬 불가, 순차)
- Phase 3 (프론트) ← Phase 2 (API) 완료 후

**순차 필수**:
1. Phase 1 → Phase 2 (라우터는 service.py 의존)
2. Phase 2 → Phase 3 (프론트는 API 경로 확정 필요)
3. Phase 4 (테스트는 병렬 가능)
4. Phase 5 (최종 검증)

---

## 4. 위험 & 완화 전략

| 위험 | 완화 |
|------|------|
| 네이버 페이지 구조 변경 | fixture 기반 테스트 + live mark로 구분 |
| 시가총액 DB 미발견 | NaN → z-score=0 폴백 |
| 429 Too Many Requests | Retry 어댑터 + 0.7초 sleep |
| 한글 인코딩 | BeautifulSoup UTF-8 자동 디코딩 |
| 프론트 탭 충돌 | TabId 타입 확장으로 안전성 확보 |

---

## 5. 성공 기준

- ✅ 모든 AC (10개) 통과
- ✅ 단위 테스트 커버리지 >= 85%
- ✅ 라이브 크롤링 테스트 1회 성공
- ✅ 프론트엔드 E2E 테스트 통과
- ✅ 코드 리뷰 승인

