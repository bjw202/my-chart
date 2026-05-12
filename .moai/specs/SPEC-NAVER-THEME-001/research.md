# 기술 리서치: SPEC-NAVER-THEME-001

| 항목 | 값 |
|------|-----|
| 버전 | 1.1.0 |
| 출처 | `theme-analysis-plan/research.md` (650줄) |
| 보강 | EUC-KR 인코딩 강조, 실 페이지 컬럼 표, 편입사유 위치, V1 범위 정리 |
| 모드 | read-only (파일 수정 없음) |

이 문서는 SPEC 작성 시 참고한 코드베이스/외부 페이지 조사 결과 요약본이다. 실제 구현 시 이 정보를 활용한다.

---

## 0. 핵심 요약 (TL;DR)

- 모듈 경로: `backend/services/naver_theme/` (사용자 결정 — `modules/` 아님)
- 진입점: `from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult`
- **인코딩**: 네이버 금융 페이지는 **EUC-KR**. `Response.encoding = 'euc-kr'`을 강제 설정해야 한글 깨짐 없음 (실측 확인)
- 외부 호출: 기본 모드 약 27회 (목록 N페이지 + 강세 테마 20개 상세), 빠른 모드 약 7회
- 시가총액: `Output/stock_data_daily.db.stock_meta.market_cap`을 **read-only**로 JOIN
- 신규 의존성: 없음 (`requests`, `bs4`, `lxml`, `pandas`, `numpy`, `fastapi` 모두 기설치)
- 기존 4탭 무회귀: 변경 파일 4개로 한정, 총 줄 수 ≤ 10

---

## 1. 마스터 DB 시가총액 컬럼 (CRITICAL — leader_score JOIN 기초)

### 1.1 DB 위치 및 테이블 구조

| 항목 | 값 |
|------|-----|
| DB 파일 | `/Users/byunjungwon/Dev/my-project-01/my_chart/Output/stock_data_daily.db` |
| 테이블 | `stock_meta` |
| 키 컬럼 | `code (TEXT, PRIMARY KEY)`, `market_cap (INTEGER, 원 단위)` |
| 갱신 메커니즘 | `my_chart/db/daily.py` + `backend/routers/db.py POST /api/db/update` |

### 1.2 단위 근거

`backend/services/screen_service.py:78`: `int(req.market_cap_min) * 100_000_000`
→ 프론트 입력 (억원) × 1억 = DB는 원 단위 저장.

### 1.3 read-only JOIN 템플릿 (REQ-NT-007)

```python
import sqlite3
conn = sqlite3.connect(f"file:{DAILY_DB_PATH}?mode=ro", uri=True)
try:
    rows = conn.execute(
        "SELECT code, market_cap FROM stock_meta WHERE code IN (?, ?, ...)",
        codes,
    ).fetchall()
finally:
    conn.close()
```

`mode=ro` URI 모드 시 SQLite가 INSERT/UPDATE/DELETE를 자체 거부한다. AC-11에서 이 동작을 회귀 테스트로 검증한다.

### 1.4 KRX 코드 커버리지

확인된 보유 종목: `005930` (삼성전자), `005935` (삼성전자우), `006260` (LS), `010100` (가온전선) 등. 신규 상장 코드는 `market_cap = NaN` 폴백 (z-score = 0 처리).

---

## 2. 인코딩 — EUC-KR 강제 설정 (CRITICAL)

### 2.1 실측 결과

네이버 금융 페이지는 **EUC-KR**로 응답한다. Content-Type 헤더에 charset이 명시되지 않을 수 있어, requests는 ISO-8859-1로 추정해버려 한글이 깨진다. 다음 패턴이 필수다:

```python
resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
resp.raise_for_status()
resp.encoding = "euc-kr"   # ← 강제 설정. 누락 시 한글 깨짐 발생
text = resp.text
```

### 2.2 검증 포인트

- AC-2: 테마명 / 종목명 / 편입사유 모두 한글 정상 표시
- 빈 character ``, replacement character `?` 미발생
- `re.compile(r"[가-힣]").search(text)` 매칭

### 2.3 대비 (FnGuide와 차이)

`fnguide/crawler.py`는 UTF-8 응답 페이지를 다루므로 명시적 encoding 강제가 없다. 본 모듈에서 그 패턴을 그대로 복사하면 안 된다.

---

## 3. 네이버 페이지 구조 (실측)

### 3.1 테마 목록 페이지

**URL**: `https://finance.naver.com/sise/theme.naver?&page={n}`

**추출 포인트**:
- `theme_id`: 행의 `td.col_type1 a` 앵커의 `href` 속성에서 `?no=(\d+)` 정규식
- `theme_name`: 같은 앵커의 텍스트
- `change_pct`, `change_pct_3d`, `up/flat/down_count`: 후속 td 셀
- 페이지네이션: `table.Nnavi` 또는 `td.pgRR` 영역의 숫자 앵커 중 최댓값

> **주의 — anchor href에서 theme_id 추출**: 행의 첫 번째 td 텍스트는 테마명일 뿐, theme_id가 아니다. theme_id는 anchor의 href 쿼리 파라미터에서만 얻을 수 있다.

### 3.2 테마 상세 페이지

**URL**: `https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}`

#### 실측 컬럼 순서 (반드시 이 매핑을 따를 것)

| td 인덱스 | 의미 | 비고 |
|----------|------|------|
| `td[0]` | 종목명 (`a.tltle` 앵커) | `stock_code`는 `href="...?code=DDDDDD"`에서 정규식 추출 |
| **`td[1]`** | **편입사유 텍스트 (`inclusion_reason` 컬럼)** | **REQ-NT-008. UX 차별화 포인트** |
| `td[2]` | 현재가 | |
| `td[3]` | 전일비 | |
| `td[4]` | 등락률 | |
| `td[5]` | 매수호가 | 미사용 |
| `td[6]` | 매도호가 | 미사용 (이전 SPEC에서 거래대금으로 잘못 매핑한 사례 — 정정) |
| `td[7]` | 거래량 | |
| `td[8]` | 거래대금 | `_parse_korean_number`로 원 단위 정규화 |
| `td[9]` | 전일거래량 | 미사용 |

#### 페이지에 **노출되지 않는** 컬럼

- PER (없음 → NaN 고정)
- ROE (없음 → NaN 고정)
- 시가총액 (없음 → DB JOIN으로 보강)

> **주의**: PER이 td[7]이라는 가정은 잘못된 것이다. td[7]은 거래량이다. PER/ROE는 페이지 자체에 없다.

### 3.3 한국 단위 숫자 파싱

거래대금/시가총액 같은 표기는 `'1,289조 1,044억'`, `'524억'`, `'1.2조'`, `'500만'` 등 멀티 토큰 형태가 가능하다. 단순 `replace("억", "")` 방식으로는 처리 못한다. 정규식 누적 합산 헬퍼 필요:

```python
import re
_KOREAN_UNIT = {"조": 1e12, "억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4}
_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(조|억|천만|백만|만)?")

def _parse_korean_number(text: str) -> float:
    if not text:
        return float("nan")
    total = 0.0
    matched = False
    for raw, unit in _RE.findall(text):
        if not raw:
            continue
        total += float(raw.replace(",", "")) * _KOREAN_UNIT.get(unit, 1)
        matched = True
    return total if matched else float("nan")
```

---

## 4. 기존 크롤러/서비스 패턴 (미러링 대상)

### 4.1 Session 싱글톤 + Retry (`my_chart/price.py:18-36`)

`requests.Session()` + `urllib3.util.Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])` + `HTTPAdapter` 패턴을 그대로 채택. 본 SPEC의 `MAX_RETRIES = 1`로 조정.

### 4.2 숫자 변환 (`fnguide/parser.py:89-101`)

`to_num()`은 콤마 제거 후 int/float 판정. 본 SPEC에서는 `'-'`, `''`, `'N/A'` → NaN 반환으로 확장.

### 4.3 크롤링 지연

FnGuide: 0.1초. 본 SPEC: **0.7초** (네이버 권고 + 안전 마진). config 상수.

### 4.4 BeautifulSoup + lxml

`BeautifulSoup(html, "lxml")` 사용. lxml은 pyproject.toml에 이미 포함.

---

## 5. FastAPI 등록 패턴

### 5.1 라우터 등록 위치 (`backend/main.py:107-114`)

기존 라우터 등록 블록:
```python
app.include_router(ai_report_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
# ...
app.include_router(stage_router, prefix="/api")
# ← 여기 다음 라인에 themes_router 추가
```

수정량: import 1줄 + include_router 1줄 = **총 2줄** (이전 SPEC 초안의 "3줄" 표기는 정정 대상이었다).

### 5.2 라우터 모델 (`backend/routers/sectors.py`)

```python
from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.get("/sectors", response_model=list[SectorInfo])
async def sectors() -> list[SectorInfo]: ...
```

본 SPEC: `backend/routers/themes.py` 신규 작성, 동일 구조.

### 5.3 DB 의존성 (`backend/deps.py`)

```python
from my_chart.config import DEFAULT_DB_DAILY
DAILY_DB_PATH: str = f"{DEFAULT_DB_DAILY}.db"
```

본 SPEC의 `db_join.py`는 `from backend.deps import DAILY_DB_PATH`로 경로만 가져오고, 연결은 자체적으로 `mode=ro` URI로 연다.

---

## 6. 프론트엔드 통합 지점

### 6.1 TabId 확장 (`frontend/src/types/market.ts`)

```typescript
// 기존
export type TabId = 'market-overview' | 'sector-analysis' | 'stock-explorer' | 'chart-grid'

// 본 SPEC 적용 후 (1줄 변경)
export type TabId = 'market-overview' | 'sector-analysis' | 'theme-analysis' | 'stock-explorer' | 'chart-grid'
```

### 6.2 TabNavigation TABS 배열 (`frontend/src/components/TabNavigation/TabNavigation.tsx`)

기존 4행 + `'theme-analysis'` 행 1개 추가 (Sector Analysis 우측에 배치).

### 6.3 AppContent 분기 (`frontend/src/AppContent.tsx`)

기존 패턴:
```typescript
<div style={{ display: activeTab === 'sector-analysis' ? 'flex' : 'none' }}>
  <SectorAnalysis />
</div>
```

신규 분기 1개 추가:
```typescript
<div style={{ display: activeTab === 'theme-analysis' ? 'flex' : 'none' }}>
  <ThemeAnalysis />
</div>
```

### 6.4 본 SPEC에서 **변경하지 않는** 기존 파일

- `frontend/src/contexts/TabContext.tsx` (`CrossTabParams.themeId/themeName`은 V1.5)
- `frontend/src/components/MarketOverview/*` (`HotThemesStrip`은 V1.5)
- `frontend/src/components/StockList/*` (`ThemeChips`은 V1.5)
- `frontend/src/components/SectorAnalysis/*` (참조만, 미수정)

### 6.5 신규 컴포넌트 (Sector 패턴 미러링)

| Sector (참조) | Theme (신규) | 패턴 |
|--------------|-------------|------|
| `SectorRankingTable.tsx` (162 lines) | `ThemeRankingTable.tsx` | 정렬 가능 테이블 + 색상 셀 + 행 클릭 |
| `SectorDetailPanel.tsx` (204 lines) | `ThemeDetailPanel.tsx` | 메트릭 카드 + 주도주 카드 3개 + 편입사유 툴팁 |

---

## 7. 테스트 컨벤션

### 7.1 pytest 마커 (`pyproject.toml:54-60`)

```toml
[tool.pytest.ini_options]
markers = [
    "live: 라이브 HTTP 요청이 필요한 테스트",
    "slow: 실행 시간이 긴 테스트 (크롤링 포함)",
]
```

본 SPEC 추가 마커:
```python
@pytest.mark.unit  # parser, analyzer (네트워크 없음)
@pytest.mark.live  # 실제 네이버 호출 (선택)
```

### 7.2 fixture 디렉토리

```
tests/fixtures/naver_theme/
├── theme_list_page1.html      # 테마 목록 페이지 (페이지네이션 포함)
└── theme_detail_178.html      # 테마 상세 페이지 (편입사유 포함, AC-13)
```

fixture는 EUC-KR로 저장. 테스트 시 `Path(...).read_text(encoding="euc-kr")` 사용.

---

## 8. 안전성 체크리스트

| 항목 | 상태 | 근거 |
|------|------|------|
| DB READ-ONLY | ✅ | `mode=ro` URI + AC-11 mtime/size 검증 |
| 라우터 충돌 없음 | ✅ | `/api/themes/*` 신규, 기존 라우팅과 무충돌 |
| 타입 시스템 확장 | ✅ | TabId union 확장은 backward-compatible |
| 신규 라이브러리 0건 | ✅ | pyproject.toml 무수정 |
| 네이버 ToS 준수 | ✅ | 0.7초 sleep + 식별 가능한 UA + 단일 스레드 |
| EUC-KR 인코딩 명시 | ✅ | `Response.encoding = 'euc-kr'` 강제 |
| 기존 4탭 회귀 없음 | ✅ | 변경 파일 4개, 총 ≤ 10줄, AC-12/14 검증 |
| KRX 코드 커버리지 | ✅ | 보유 종목 + 신규 코드 NaN 폴백 |

---

## 9. V1 범위 명시

### 9.1 V1에서 구현

- 백엔드 모듈 (`service`, `crawler`, `parser`, `analyzer`, `db_join`, `schemas`, `config`)
- FastAPI 라우터: `GET /api/themes/snapshot`, `GET /api/themes/quick`
- 프론트엔드 신규 탭 + `ThemeRankingTable` + `ThemeDetailPanel`
- 단위 테스트 (parser, analyzer, fixture 기반)

### 9.2 V1.5로 분류 (본 SPEC 범위 **외**)

- `GET /api/themes/by-stock/{code}` 엔드포인트
- `HotThemesStrip` (Market Overview 침투 위젯)
- `ThemeChips` (Stock Explorer / Chart Grid 침투 위젯)
- `CrossTabParams.themeId/themeName` 필드

### 9.3 V2 이후

- 시계열 누적, `ThemeBumpChart`, `ThemeBubbleChart`, "어제 대비 부상한 테마" Banner

### 9.4 V3

- AI 코멘트 자동 생성 (기존 `ai_report_service` 활용)

---

## 10. 참고 파일 맵

| 항목 | 파일 경로 | 라인 | 용도 |
|------|---------|------|------|
| Master DB | `Output/stock_data_daily.db` | — | `stock_meta.market_cap` JOIN |
| Session 패턴 | `my_chart/price.py` | 18-36 | Session 싱글톤 + Retry 모델 |
| 파서 함수 | `fnguide/parser.py` | 89-101 | `to_num()` 함수 |
| 라우터 등록 | `backend/main.py` | 107-114 | `include_router` 위치 (2줄 추가) |
| 라우터 모델 | `backend/routers/sectors.py` | 1-80 | 라우터 구조 모델 |
| DB 의존성 | `backend/deps.py` | 1-22 | `DAILY_DB_PATH` 상수 |
| 탭 정의 | `frontend/src/components/TabNavigation/TabNavigation.tsx` | 10-15 | TABS 배열 |
| TabId 타입 | `frontend/src/types/market.ts` | 1-5 | union 확장 1줄 |
| 탭 렌더링 | `frontend/src/AppContent.tsx` | 19-61 | 조건부 마운트 |
| 섹터 테이블 | `frontend/src/components/SectorAnalysis/SectorRankingTable.tsx` | 1-162 | 패턴 모델 |
| 섹터 패널 | `frontend/src/components/SectorAnalysis/SectorDetailPanel.tsx` | 1-204 | 패턴 모델 |
| 테스트 설정 | `pyproject.toml` | 54-60 | pytest 마커 |
| 라이브러리 | `pyproject.toml` | 10-34 | 의존성 (모두 기설치) |

---

## 11. 핵심 SQL 스니펫

```sql
-- 시가총액 read-only JOIN (REQ-NT-007)
-- 연결: sqlite3.connect(f"file:{DAILY_DB_PATH}?mode=ro", uri=True)
SELECT code, market_cap
FROM stock_meta
WHERE code IN ('005930', '006260', '010100', ...);

-- 결과 예
-- 005930 | 309700000000   (약 30조 원)
-- 006260 |   9800000000   (약 1조 원)
```

---

## 12. 결론

본 모듈은 **읽기 전용 애드온**으로 안전하게 통합 가능하다.

- 기존 DB는 `mode=ro` URI로 SELECT만 수행
- 기존 4탭은 무회귀 (변경 파일 4개, ≤ 10줄)
- 네이버 페이지는 EUC-KR — 명시적 인코딩 강제 필수
- 실 페이지 컬럼 매핑: `td[0]` 종목명, `td[1]` 편입사유(`inclusion_reason`), `td[2]` 가격, `td[8]` 거래대금
- 신규 의존성 0건, V1 범위만 구현 (V1.5 이후는 후속 SPEC)
