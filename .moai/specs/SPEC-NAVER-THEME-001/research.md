# 기술 리서치 (Reference): SPEC-NAVER-THEME-001

**버전**: 1.0.0 | **출처**: theme-analysis-plan/research.md | **참고용 문서**

이 파일은 SPEC 작성 시 참고한 코드베이스 조사 결과입니다. 구현 단계에서 이 정보를 활용하세요.

---

## 1. 마스터 DB 시가총액 정보

### DB 위치 및 테이블
```
파일: /Users/byunjungwon/Dev/my-project-01/my_chart/Output/stock_data_daily.db
테이블: stock_meta
컬럼: market_cap (INTEGER, 원 단위)
```

### 시가총액 단위 근거
```
backend/services/screen_service.py:78
  int(req.market_cap_min) * 100_000_000
  → 프론트엔드 입력(억원) × 100,000,000 = 원 단위
```

### DB 읽기 쿼리 (JOIN 템플릿)
```sql
SELECT code, market_cap FROM stock_meta WHERE code IN (?, ?, ...)
-- 결과: (stock_code: str, market_cap: int)
```

### KRX 코드 커버리지
- ✅ 005930 (삼성전자)
- ✅ 006260 (LS)
- ✅ 010100 (가온전선)
- 신규 상장 코드: market_cap = NaN → z-score = 0 처리

---

## 2. 기존 크롤러 패턴 분석

### 2.1 Session 싱글톤 + Retry 어댑터
**파일**: `my_chart/price.py:18-36`

```python
_session: requests.Session | None = None

def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session
```

**우리 적용**: 동일한 구조로 naver_theme/crawler.py 작성

### 2.2 숫자 변환 함수 to_num()
**파일**: `fnguide/parser.py:89-101`

```python
def to_num(x: str) -> int | float:
    """콤마 포맷 문자열을 int 또는 float으로 변환."""
    num = x.replace(",", "")
    try:
        if "." in num:
            return float(num)
        return int(num)
    except ValueError:
        return 0
```

**우리 확장**: normalize_money() 추가 (억, 조, 백만 단위 처리)

### 2.3 크롤딩 지연 상수
**파일**: `fnguide/crawler.py:38`

```python
_CRAWL_DELAY = 0.1  # 초
```

**우리 설정**: `_CRAWL_DELAY = 0.7` (네이버 권고)

### 2.4 BeautifulSoup 사용 패턴
**파일**: `fnguide/crawler.py:1-24`

```python
from bs4 import BeautifulSoup
from lxml import html

soup = BeautifulSoup(snap_page.text, "html.parser")
# 또는 "lxml"
```

---

## 3. FastAPI 라우터 패턴

### 3.1 라우터 등록 위치
**파일**: `backend/main.py:107-114`

```python
app.include_router(ai_report_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
# ...
app.include_router(sectors_router, prefix="/api")
app.include_router(stage_router, prefix="/api")
# ← 여기에 themes_router 추가 (114줄 이후)
```

### 3.2 라우터 구조 모델
**파일**: `backend/routers/sectors.py:1-80`

```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.deps import DAILY_DB_PATH
from backend.services.sector_service import get_sectors

router = APIRouter()

@router.get("/sectors", response_model=list[SectorInfo])
async def sectors() -> list[SectorInfo]:
    raw = get_sectors(DAILY_DB_PATH)
    return [SectorInfo(...) for r in raw]
```

**우리 적용**: 동일한 패턴으로 themes.py 작성

### 3.3 DB 의존성
**파일**: `backend/deps.py`

```python
from my_chart.config import DEFAULT_DB_DAILY, DEFAULT_DB_WEEKLY

DAILY_DB_PATH: str = f"{DEFAULT_DB_DAILY}.db"

def get_db_conn(path: str) -> sqlite3.Connection:
    return sqlite3.connect(path, check_same_thread=False)
```

**우리 사용**: `from backend.deps import get_db_conn, DAILY_DB_PATH`

---

## 4. 프론트엔드 컴포넌트 구조

### 4.1 탭 네비게이션
**파일**: `frontend/src/components/TabNavigation/TabNavigation.tsx:10-15`

```typescript
const TABS: TabConfig[] = [
  { id: 'market-overview', label: 'Market Overview' },
  { id: 'sector-analysis', label: 'Sector Analysis' },
  // ← 여기에 추가: { id: 'theme-analysis', label: 'Theme Analysis' }
  { id: 'stock-explorer', label: 'Stock Explorer' },
  { id: 'chart-grid', label: 'Chart Grid' },
]
```

### 4.2 탭 렌더링 패턴
**파일**: `frontend/src/AppContent.tsx:19-61`

```typescript
export function AppContent(): ReactElement {
  const { activeTab, crossTabParams, clearCrossTabParams } = useTab()
  
  return (
    <div className="app">
      <div style={{ display: activeTab === 'theme-analysis' ? 'flex' : 'none' }}>
        <ThemeAnalysis />
      </div>
    </div>
  )
}
```

### 4.3 CrossTabParams 확장
**파일**: `frontend/src/contexts/TabContext.tsx:1-43`

```typescript
interface CrossTabParams {
  stockCodes?: string[]     // 기존
  themeId?: number          // ← 신규 추가
  themeName?: string        // ← 신규 추가
}
```

### 4.4 컴포넌트 패턴 모델

#### SectorRankingTable.tsx (162줄)
- Props: sectors[], sortField, sortDirection, onSort, onSectorClick, selectedSector
- 렌더링: 정렬 가능 테이블 + 색상 기반 셀 배경
- 클릭: 행 클릭 시 onSectorClick 트리거

**우리 적용**: ThemeRankingTable
- 동일한 구조, change_pct/change_pct_3d 컬럼 표시

#### SectorDetailPanel.tsx (204줄)
- Props: sector
- useEffect: fetchSectorDetail() API 호출
- 렌더링: 메트릭 카드 + 기간별 return bar + 2열 테이블 (sub-sector + top 5 stocks)

**우리 적용**: ThemeDetailPanel
- 동일한 구조, momentum_score/breadth_ratio 메트릭
- 주도주 카드 3개 + 편입사유 툴팁

---

## 5. API 클라이언트 패턴

### 파일: `frontend/src/api/sectors.ts`

```typescript
import client from './client'
import type { SectorInfo } from '../types/stock'
import type { SectorDetailResponse } from '../types/sector'

export async function fetchSectors(): Promise<SectorInfo[]> {
  const response = await client.get<SectorInfo[]>('/sectors')
  return response.data
}

export async function fetchSectorDetail(sectorName: string): Promise<SectorDetailResponse> {
  const encoded = encodeURIComponent(sectorName)
  const response = await client.get<SectorDetailResponse>(`/sectors/${encoded}/detail`)
  return response.data
}
```

**우리 적용**: themes.ts
```typescript
export async function fetchThemesSnapshot(topN?: number) {
  return client.get('/themes/snapshot', { params: { top_n: topN } })
}

export async function fetchThemesByStock(code: string) {
  return client.get(`/themes/by-stock/${code}`)
}
```

---

## 6. 테스트 컨벤션

### Pytest 마커
**파일**: `pyproject.toml:54-60`

```toml
[tool.pytest.ini_options]
markers = [
    "live: 라이브 HTTP 요청이 필요한 테스트",
    "slow: 실행 시간이 긴 테스트 (크롤링 포함)",
]
```

**우리 사용**:
```python
@pytest.mark.unit
def test_parse_theme_list(): ...

@pytest.mark.slow
def test_naver_crawl_live(): ...  # live mark 사용
```

### Fixture 디렉토리
```
tests/fixtures/naver_theme/
├── theme_list_page1.html
├── theme_detail_178.html
└── ...
```

---

## 7. 라이브러리 의존성 (이미 설치됨)

**파일**: `pyproject.toml:10-34`

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| requests | >=2.28 | HTTP + Retry |
| beautifulsoup4 | >=4.12 | HTML 파싱 |
| lxml | >=4.9 | 파서 |
| pandas | >=2.0 | DataFrame |
| numpy | >=1.24 | z-score |
| fastapi | >=0.115.0 | 라우터 |

**결론**: pyproject.toml 수정 불필요 ✅

---

## 8. 안전성 검증 항목

### DB READ-ONLY
- SELECT market_cap만 (INSERT/UPDATE 금지)
- 기존 서비스와 독립적 (screen_service, chart_service와 무관)
- ✅ 안전

### API 라우팅
- `/api/themes/*` 신규 (기존 `/api/theme` 없음)
- ✅ 충돌 없음

### 타입 시스템
- TabId 확장: 'theme-analysis' 추가
- CrossTabParams 확장: themeId, themeName 필드 추가
- ✅ 기존 코드 영향 없음

### 네이버 ToS
- User-Agent: 식별 가능한 문자열 ✅
- Sleep: 0.7초 (0.5초 권고 상한보다 안전) ✅
- 단일 스레드, 동시 요청 금지 ✅

---

## 9. 참고 자료

- **theme-request.md**: 원본 요구사항 (R1-R7, AC 10개)
- **theme-strategy.md**: 투자자 관점 전략 & 확정 입력값 11개
- **research.md**: 코드베이스 깊이 탐사 (650줄)

