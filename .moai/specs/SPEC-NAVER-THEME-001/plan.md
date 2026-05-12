# Implementation Plan: SPEC-NAVER-THEME-001 V1

## 메타

| 항목 | 값 |
|------|-----|
| SPEC | SPEC-NAVER-THEME-001 |
| 버전 | 1.0.0 |
| 상태 | Draft (Pending User Approval) |
| 우선순위 | High |
| 의존성 | 없음 (기존 코드는 모두 read-only로 참조) |

---

## 1. Phase 분해 (RUN Phase 실행 순서)

| Phase | 담당 | 우선순위 | 선행 의존성 |
|-------|------|----------|-------------|
| Phase 1 — 백엔드 모듈 구현 | expert-backend | High | 없음 |
| Phase 2 — FastAPI 라우터 추가 | expert-backend | High | Phase 1 |
| Phase 3 — 프론트엔드 컴포넌트 | expert-frontend | High | Phase 2 (API 경로 확정) |
| Phase 4 — 단위 테스트 작성 | expert-testing | High | Phase 1 (parser, analyzer 함수 존재) |
| Phase 5 — 통합 검증 + 회귀 검증 | manager-quality | High | Phase 1~4 |

> 시간 추정 사용 금지 (`.claude/rules/moai/core/agent-common-protocol.md` "Time Estimation" 준수). 우선순위 라벨 + Phase 순서로 진행 관리.

---

## 2. Phase 1 — 백엔드 모듈 구현

### 2.1 디렉토리 구조 (신규 생성)

```
backend/services/naver_theme/
├── __init__.py        # collect_and_analyze, ThemeAnalysisResult 노출
├── service.py         # 진입점 (오케스트레이션)
├── crawler.py         # HTTP 호출, Session 싱글톤, EUC-KR 강제
├── parser.py          # HTML 파싱 (테마 목록, 상세, 편입사유)
├── analyzer.py        # 강세 테마, 주도주, 멀티테마 계산
├── db_join.py         # market_cap read-only JOIN
├── schemas.py         # Pydantic 모델
└── config.py          # URL, 헤더, sleep, 가중치 상수
```

### 2.2 `config.py` (의사코드)

```python
NAVER_THEME_LIST_URL = "https://finance.naver.com/sise/theme.naver?&page={n}"
NAVER_THEME_DETAIL_URL = "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}"

CRAWL_DELAY = 0.7
REQUEST_TIMEOUT = 10
MAX_RETRIES = 1
USER_AGENT = "KR-Stock-Screener/1.0 (naver_theme_analysis)"
RESPONSE_ENCODING = "euc-kr"  # REQ-NT-NF-002

# 가중치
MOMENTUM_WEIGHT_1D = 0.6
MOMENTUM_WEIGHT_3D = 0.4
LEADER_SCORE_WEIGHTS = {
    "change_pct": 0.40,
    "volume": 0.30,
    "market_cap": 0.20,
    "trade_value": 0.10,
}

DEFAULT_TOP_N_THEMES = 20
DEFAULT_LEADERS_PER_THEME = 3
```

### 2.3 `__init__.py` (단일 진입점 노출)

```python
from .service import collect_and_analyze, ThemeAnalysisResult

__all__ = ["collect_and_analyze", "ThemeAnalysisResult"]
```

> 외부 사용은 `from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult` 한 줄로 충족 (REQ-NT-001, AC-10).

### 2.4 `crawler.py` (의사코드)

핵심 포인트:

- Session 싱글톤 (`my_chart/price.py` 패턴 모방) + `urllib3.util.Retry` 어댑터
- `Response.encoding = 'euc-kr'` **강제 설정** (REQ-NT-NF-002, A-3)
- 호출 간 `time.sleep(0.7)` (REQ-NT-NF-001)

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import (
    CRAWL_DELAY, REQUEST_TIMEOUT, MAX_RETRIES,
    USER_AGENT, RESPONSE_ENCODING,
    NAVER_THEME_LIST_URL, NAVER_THEME_DETAIL_URL,
)

_session: requests.Session | None = None

def _get_session() -> requests.Session:
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

def _fetch(url: str) -> str:
    """EUC-KR 강제 디코딩 후 HTML 텍스트 반환."""
    sess = _get_session()
    resp = sess.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = RESPONSE_ENCODING  # ← 한글 깨짐 방지
    text = resp.text
    time.sleep(CRAWL_DELAY)
    return text

def fetch_theme_list_page(page: int) -> str:
    return _fetch(NAVER_THEME_LIST_URL.format(n=page))

def fetch_theme_detail_page(theme_id: int) -> str:
    return _fetch(NAVER_THEME_DETAIL_URL.format(theme_id=theme_id))
```

### 2.5 `parser.py` (의사코드, 실 페이지 구조 반영)

#### 2.5.1 숫자 변환 헬퍼

```python
import re
import math

def to_num(x: str) -> float:
    """콤마/공백 제거 후 float. 변환 실패 시 NaN."""
    s = (x or "").replace(",", "").strip().replace("%", "")
    if s in ("", "-", "N/A"):
        return math.nan
    try:
        return float(s)
    except ValueError:
        return math.nan

_KOREAN_UNIT = {"조": 1_000_000_000_000, "억": 100_000_000, "천만": 10_000_000, "백만": 1_000_000, "만": 10_000}
_KOREAN_NUMBER_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(조|억|천만|백만|만)?")

def _parse_korean_number(text: str) -> float:
    """'1,289조 1,044억', '524억', '1.2조', '500만', '500,000' 등을 원 단위 float으로 변환.

    멀티 토큰 표기를 누적 합산한다.
    """
    if not text:
        return math.nan
    total = 0.0
    matched = False
    for raw, unit in _KOREAN_NUMBER_RE.findall(text):
        if not raw:
            continue
        val = float(raw.replace(",", ""))
        total += val * _KOREAN_UNIT.get(unit, 1)
        matched = True
    return total if matched else math.nan

def normalize_money(value_str: str) -> int:
    """원 단위 정수로 정규화 (NaN이면 0이 아닌 NaN 유지를 위해 호출자에서 사후 처리)."""
    n = _parse_korean_number(value_str)
    return int(n) if not math.isnan(n) else 0
```

#### 2.5.2 테마 목록 파서 (theme_id는 anchor href에서 추출)

```python
import re
from bs4 import BeautifulSoup

_THEME_NO_RE = re.compile(r"no=(\d+)")

def parse_theme_list(html: str) -> dict:
    """Returns {'themes': [...], 'last_page': int}."""
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.type_1 tr")
    themes: list[dict] = []
    for row in rows:
        anchor = row.select_one("td.col_type1 a")
        if not anchor:
            continue
        href = anchor.get("href", "")
        m = _THEME_NO_RE.search(href)
        if not m:
            continue
        theme_id = int(m.group(1))
        cells = row.find_all("td")
        if len(cells) < 7:
            continue
        themes.append({
            "theme_id": theme_id,
            "theme_name": anchor.get_text(strip=True),
            "change_pct": to_num(cells[1].get_text()),
            "change_pct_3d": to_num(cells[2].get_text()),
            # up/flat/down: 네이버는 '상승/보합/하락'을 별도 td로 나누거나 합쳐 노출
            # 실제 셀 구조에 맞춰 매핑 (fixture 기반 검증 필요)
            "up_count": to_num(cells[3].get_text()),
            "flat_count": to_num(cells[4].get_text()),
            "down_count": to_num(cells[5].get_text()),
            "top_stocks_preview": cells[6].get_text(" ", strip=True) if len(cells) > 6 else "",
        })

    # 마지막 페이지 탐지 (페이지네이션 영역의 숫자 앵커 중 최댓값)
    last_page = 1
    for a in soup.select("table.Nnavi a, td.pgRR a"):
        txt = a.get_text(strip=True)
        if txt.isdigit():
            last_page = max(last_page, int(txt))
    return {"themes": themes, "last_page": last_page}
```

#### 2.5.3 테마 상세 파서 (실 컬럼 구조 반영)

```python
_STOCK_CODE_RE = re.compile(r"code=(\d{6})")

def parse_theme_detail(html: str, theme_id: int, theme_name: str) -> list[dict]:
    """
    네이버 테마 상세 페이지 실측 컬럼 매핑 (Assumptions A-6):
        td[0] 종목명 (a.tltle), code는 href="...?code=DDDDDD"에서 정규식
        td[1] 편입사유 텍스트     ← REQ-NT-008
        td[2] 현재가
        td[3] 전일비
        td[4] 등락률
        td[5] 매수호가
        td[6] 매도호가
        td[7] 거래량
        td[8] 거래대금            ← _parse_korean_number
        td[9] 전일거래량
    PER/ROE는 페이지에 없음 → NaN 고정 (A-5).
    """
    soup = BeautifulSoup(html, "lxml")
    stocks: list[dict] = []
    for row in soup.select("table.type_5 tr"):
        anchor = row.select_one("td a.tltle")
        if not anchor:
            continue
        href = anchor.get("href", "")
        m = _STOCK_CODE_RE.search(href)
        if not m:
            continue
        cells = row.find_all("td")
        if len(cells) < 9:
            continue
        stocks.append({
            "theme_id": theme_id,
            "theme_name": theme_name,
            "stock_code": m.group(1),
            "stock_name": anchor.get_text(strip=True),
            "inclusion_reason": cells[1].get_text(" ", strip=True),
            "price": to_num(cells[2].get_text()),
            "change": to_num(cells[3].get_text()),
            "change_pct": to_num(cells[4].get_text()),
            "volume": int(_parse_korean_number(cells[7].get_text())) if cells[7].get_text(strip=True) else 0,
            "trade_value": int(_parse_korean_number(cells[8].get_text())) if cells[8].get_text(strip=True) else 0,
            "per": math.nan,  # 상세 페이지 미노출
            "roe": math.nan,  # 상세 페이지 미노출
        })
    return stocks
```

### 2.6 `analyzer.py` (의사코드)

```python
import pandas as pd
import numpy as np
from .config import LEADER_SCORE_WEIGHTS, MOMENTUM_WEIGHT_1D, MOMENTUM_WEIGHT_3D

def build_strong_themes(themes_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    df = themes_df.copy()
    df["momentum_score"] = df["change_pct"] * MOMENTUM_WEIGHT_1D + df["change_pct_3d"] * MOMENTUM_WEIGHT_3D
    denom = df["up_count"] + df["flat_count"] + df["down_count"]
    df["breadth_ratio"] = (df["up_count"] / denom).fillna(0)
    return df.sort_values("change_pct", ascending=False).head(top_n).reset_index(drop=True)

def _zscore(s: pd.Series) -> pd.Series:
    std = s.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - s.mean()) / std

def build_leaders(stocks_df: pd.DataFrame, leaders_per_theme: int) -> pd.DataFrame:
    out = []
    for theme_id, group in stocks_df.groupby("theme_id"):
        g = group.copy()
        for col in ("change_pct", "volume", "market_cap", "trade_value"):
            # market_cap NaN은 0으로 fillna 후 z-score 계산 (REQ-NT-009)
            series = g[col].astype(float).fillna(0)
            g[f"z_{col}"] = _zscore(series)
        g["leader_score"] = sum(g[f"z_{c}"] * w for c, w in LEADER_SCORE_WEIGHTS.items())
        top = g.nlargest(leaders_per_theme, "leader_score").reset_index(drop=True)
        top["rank"] = top.index + 1
        out.append(top[["theme_id", "theme_name", "rank", "stock_code", "stock_name",
                        "leader_score", "change_pct", "volume", "market_cap", "trade_value"]])
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()

def build_multi_theme_stocks(stocks_df: pd.DataFrame) -> pd.DataFrame:
    if stocks_df.empty:
        return pd.DataFrame()
    grouped = stocks_df.groupby("stock_code").agg(
        stock_name=("stock_name", "first"),
        theme_names=("theme_name", lambda x: sorted(set(x))),
        theme_count=("theme_name", "nunique"),
        avg_change_pct=("change_pct", "mean"),
    ).reset_index()
    return grouped[grouped["theme_count"] >= 2].sort_values(
        "theme_count", ascending=False
    ).reset_index(drop=True)
```

### 2.7 `db_join.py` (read-only DB JOIN)

```python
import sqlite3
import pandas as pd
from backend.deps import DAILY_DB_PATH

def enrich_market_cap(stocks_df: pd.DataFrame, db_path: str = DAILY_DB_PATH) -> pd.DataFrame:
    """stock_meta.market_cap을 read-only로 JOIN (REQ-NT-007, REQ-NT-C-001)."""
    if stocks_df.empty:
        stocks_df["market_cap"] = pd.Series(dtype="float64")
        return stocks_df
    codes = stocks_df["stock_code"].astype(str).unique().tolist()
    placeholders = ",".join("?" * len(codes))
    # 강제 read-only URI (INSERT/UPDATE 시도 시 SQLite가 거부)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            f"SELECT code, market_cap FROM stock_meta WHERE code IN ({placeholders})",
            codes,
        ).fetchall()
    finally:
        conn.close()
    cap_map = {code: cap for code, cap in rows}
    stocks_df = stocks_df.copy()
    stocks_df["market_cap"] = stocks_df["stock_code"].map(cap_map).astype("float64")
    return stocks_df
```

### 2.8 `service.py` (오케스트레이션)

```python
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import pandas as pd

from .crawler import fetch_theme_list_page, fetch_theme_detail_page
from .parser import parse_theme_list, parse_theme_detail
from .analyzer import build_strong_themes, build_leaders, build_multi_theme_stocks
from .db_join import enrich_market_cap
from .config import DEFAULT_TOP_N_THEMES, DEFAULT_LEADERS_PER_THEME

KST = timezone(timedelta(hours=9))
logger = logging.getLogger("naver_theme")

@dataclass
class ThemeAnalysisResult:
    themes_df: pd.DataFrame
    stocks_df: pd.DataFrame
    strong_themes_df: pd.DataFrame
    leaders_df: pd.DataFrame
    multi_theme_stocks_df: pd.DataFrame
    metadata: dict

def _now_kst() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")

def _collect_theme_list(errors: list[dict]) -> pd.DataFrame:
    """첫 페이지를 fetch → last_page 추출 → 후속 페이지 순회 (REQ-NT-003)."""
    themes: list[dict] = []
    try:
        first_html = fetch_theme_list_page(1)
        first = parse_theme_list(first_html)
        themes.extend(first["themes"])
        last_page = max(1, int(first.get("last_page", 1)))
    except Exception as e:
        errors.append({"theme_id": None, "stage": "list", "reason": f"page=1: {e}"})
        return pd.DataFrame()

    for page in range(2, last_page + 1):
        try:
            html = fetch_theme_list_page(page)
            themes.extend(parse_theme_list(html)["themes"])
        except Exception as e:
            errors.append({"theme_id": None, "stage": "list", "reason": f"page={page}: {e}"})

    df = pd.DataFrame(themes)
    if not df.empty:
        df["collected_at"] = _now_kst()
    return df

def _collect_theme_details(strong_df: pd.DataFrame, errors: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for _, theme in strong_df.iterrows():
        theme_id = int(theme["theme_id"])
        try:
            html = fetch_theme_detail_page(theme_id)
            rows.extend(parse_theme_detail(html, theme_id, theme["theme_name"]))
        except Exception as e:
            errors.append({"theme_id": theme_id, "stage": "detail", "reason": str(e)})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["collected_at"] = _now_kst()
    return df

def collect_and_analyze(
    top_n_themes: int = DEFAULT_TOP_N_THEMES,
    leaders_per_theme: int = DEFAULT_LEADERS_PER_THEME,
    skip_details: bool = False,
    theme_filter: list[str] | None = None,
) -> ThemeAnalysisResult:
    start = time.time()
    errors: list[dict] = []

    themes_df = _collect_theme_list(errors)
    if theme_filter and not themes_df.empty:
        themes_df = themes_df[themes_df["theme_name"].isin(theme_filter)].reset_index(drop=True)

    strong_df = build_strong_themes(themes_df, top_n_themes) if not themes_df.empty else pd.DataFrame()

    if skip_details or strong_df.empty:
        stocks_df = pd.DataFrame()
        leaders_df = pd.DataFrame()
        multi_df = pd.DataFrame()
    else:
        stocks_df = _collect_theme_details(strong_df, errors)
        if not stocks_df.empty:
            stocks_df = enrich_market_cap(stocks_df)
            leaders_df = build_leaders(stocks_df, leaders_per_theme)
            multi_df = build_multi_theme_stocks(stocks_df)
        else:
            leaders_df = pd.DataFrame()
            multi_df = pd.DataFrame()

    elapsed = round(time.time() - start, 2)
    return ThemeAnalysisResult(
        themes_df=themes_df,
        stocks_df=stocks_df,
        strong_themes_df=strong_df,
        leaders_df=leaders_df,
        multi_theme_stocks_df=multi_df,
        metadata={
            "collected_at": _now_kst(),
            "theme_count": int(len(themes_df)),
            "stock_count": int(len(stocks_df)),
            "elapsed_sec": elapsed,
            "errors": errors,
        },
    )
```

---

## 3. Phase 2 — FastAPI 라우터 추가

### 3.1 신규 파일: `backend/routers/themes.py`

```python
from fastapi import APIRouter, HTTPException
from backend.services.naver_theme import collect_and_analyze

router = APIRouter()

def _records(df) -> list:
    return df.to_dict(orient="records") if not df.empty else []

@router.get("/themes/snapshot")
async def themes_snapshot(top_n: int = 20, leaders_per_theme: int = 3) -> dict:
    """REQ-NT-R-001: 5종 DataFrame + metadata."""
    try:
        r = collect_and_analyze(top_n_themes=top_n, leaders_per_theme=leaders_per_theme, skip_details=False)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "themes": _records(r.themes_df),
        "stocks": _records(r.stocks_df),
        "strong_themes": _records(r.strong_themes_df),
        "leaders": _records(r.leaders_df),
        "multi_theme_stocks": _records(r.multi_theme_stocks_df),
        "metadata": r.metadata,
    }

@router.get("/themes/quick")
async def themes_quick(top_n: int = 20) -> dict:
    """REQ-NT-R-002: 빠른 모드 (skip_details=True, 10초 이내)."""
    try:
        r = collect_and_analyze(top_n_themes=top_n, skip_details=True)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "themes": _records(r.themes_df),
        "strong_themes": _records(r.strong_themes_df),
        "metadata": r.metadata,
    }
```

> V1 범위에서는 `/themes/by-stock/{code}` 엔드포인트를 **추가하지 않는다** (Out-of-scope §6.1).

### 3.2 `backend/main.py` 수정 (총 2줄 추가)

```python
# 기존 import 블록 끝에 1줄 추가
from backend.routers.themes import router as themes_router

# 기존 include_router 블록 끝에 1줄 추가
app.include_router(themes_router, prefix="/api")
```

> 합계 2줄. 기존 라우터 등록 순서 변경 금지 (기존 4탭 회귀 방지, REQ-NT-C-002).

---

## 4. Phase 3 — 프론트엔드 컴포넌트

### 4.1 신규 파일

```
frontend/src/components/ThemeAnalysis/
├── ThemeAnalysis.tsx          # 컨테이너 (좌우 2열 + 하단 멀티테마 위젯)
├── ThemeRankingTable.tsx      # SectorRankingTable 패턴 미러링
└── ThemeDetailPanel.tsx       # SectorDetailPanel 패턴 미러링
frontend/src/api/themes.ts     # API 클라이언트
```

### 4.2 API 클라이언트 (`frontend/src/api/themes.ts`)

```typescript
import client from './client'

export async function fetchThemesSnapshot(topN?: number, leadersPerTheme?: number) {
  const response = await client.get('/themes/snapshot', {
    params: { top_n: topN, leaders_per_theme: leadersPerTheme },
  })
  return response.data
}

export async function fetchThemesQuick(topN?: number) {
  const response = await client.get('/themes/quick', { params: { top_n: topN } })
  return response.data
}
```

> `fetchThemesByStock`는 V1.5 범위 — 본 SPEC에서 **추가하지 않는다**.

### 4.3 기존 파일 surgical 수정 (REQ-NT-C-002, AC-14)

| 파일 | 변경 | 줄 수 |
|------|------|-------|
| `frontend/src/types/market.ts` | TabId union에 `'theme-analysis'` 추가 | +1 |
| `frontend/src/components/TabNavigation/TabNavigation.tsx` | TABS 배열에 1행 추가 | +1 |
| `frontend/src/AppContent.tsx` | activeTab 분기에 `'theme-analysis'` case 1개 + 마운트 1줄 | +1 ~ +2 |
| `backend/main.py` | import 1 + include_router 1 | +2 |

합계 ≤ 10줄. `TabContext.tsx`의 `CrossTabParams.themeId/themeName`은 V1.5에서 추가 (Out-of-scope §6.1).

---

## 5. Phase 4 — 단위 테스트

### 5.1 디렉토리

```
tests/
├── fixtures/naver_theme/
│   ├── theme_list_page1.html
│   └── theme_detail_178.html
├── test_naver_theme_parser.py
└── test_naver_theme_analyzer.py
```

### 5.2 단위 테스트 시나리오 (parser)

- `test_parse_theme_list_extracts_theme_id_from_anchor_href`: `td.col_type1 a` href의 `?no=178` → `theme_id=178`
- `test_parse_theme_list_detects_last_page`: 페이지네이션 영역의 최대 숫자 앵커 추출
- `test_parse_theme_detail_captures_inclusion_reason`: `td[1]`이 `inclusion_reason` 컬럼으로 보존됨 (AC-13)
- `test_parse_theme_detail_columns_match_real_layout`: 가격은 `td[2]`, 거래대금은 `td[8]` 매핑 검증
- `test_parse_korean_number_multi_token`: `'1,289조 1,044억'` 누적 합산 검증
- `test_to_num_handles_dash_and_empty`: `'-'` → NaN

### 5.3 단위 테스트 시나리오 (analyzer)

- `test_build_strong_themes_sorts_by_change_pct`
- `test_build_strong_themes_breadth_ratio_zero_division_safe`
- `test_build_leaders_weights_sum_to_one_and_apply_correctly`
- `test_build_leaders_zero_std_yields_zero_z`
- `test_build_multi_theme_stocks_dedups_duplicate_rows`: 동일 종목·동일 테마 중복 시 `theme_count`가 nunique로 집계됨

### 5.4 마커

```python
@pytest.mark.unit  # parser, analyzer
@pytest.mark.live  # 실제 네이버 호출 통합 테스트 (선택)
```

---

## 6. Phase 5 — 통합 검증 + 회귀 검증

### 6.1 신규 기능 검증

- `pytest tests/test_naver_theme_*.py -m unit --cov=backend.services.naver_theme --cov-report=term-missing` → 커버리지 ≥ 85% (AC-9)
- `acceptance.md`의 14개 AC 모두 PASS

### 6.2 기존 기능 회귀 검증 (REQ-NT-C-002, AC-12)

- 기존 백엔드 테스트: `pytest backend/tests/ -m "not live"` 변화 없이 통과
- 기존 프론트엔드 테스트: `npm test` (Vitest) 변화 없이 통과
- 수동 스모크 테스트: Market Overview / Sector Analysis / Stock Explorer / Chart Grid 4탭의 핵심 화면이 정상 렌더링되는지 확인

### 6.3 DB 무수정 검증 (REQ-NT-C-001, AC-11)

- AC-11 자동 테스트: `os.path.getmtime()` 비교
- read-only URI 모드(`mode=ro`) 사용 검증 (`db_join.py` 코드 리뷰)

---

## 7. 의존성 및 병렬화

| 노드 | 선행 |
|------|------|
| Phase 1.1 (config/__init__) | — |
| Phase 1.2 (crawler) | Phase 1.1 |
| Phase 1.3 (parser) | Phase 1.1 |
| Phase 1.4 (analyzer) | Phase 1.1 |
| Phase 1.5 (db_join) | Phase 1.1 |
| Phase 1.6 (service) | Phase 1.2 ~ 1.5 |
| Phase 2 (router) | Phase 1.6 |
| Phase 3 (frontend) | Phase 2 |
| Phase 4 (tests) | Phase 1.3 + 1.4 (parser/analyzer 함수 존재) |
| Phase 5 (integration) | Phase 1 ~ 4 |

병렬 가능: Phase 1.2/1.3/1.4/1.5 (서로 독립). Phase 4는 Phase 1.3, 1.4 완료 즉시 시작 가능.

---

## 8. 위험 및 완화

| 위험 | 완화 |
|------|------|
| 네이버 페이지 구조 변경 | fixture 기반 단위 테스트 + `@pytest.mark.live` 회귀 테스트 |
| EUC-KR 인코딩 누락 → 한글 깨짐 | `Response.encoding = 'euc-kr'` 강제 + AC-2 검증 |
| `theme_id` 추출 실패 (anchor href 형식 변경) | 정규식 `?no=(\d+)` 매칭 실패 시 행 skip + errors 기록 |
| 페이지 루프 1회 도는 버그 | 첫 페이지 fetch → `last_page` 추출 → `range(2, last+1)` 패턴 강제 |
| `multi_theme_stocks` 중복 행 집계 오류 | `nunique()` + `sorted(set(x))` 사용 |
| DB JOIN 시 INSERT/UPDATE 실수 | `mode=ro` URI 강제 + AC-11 mtime 검증 |
| 기존 4탭 회귀 | Phase 5.2 회귀 테스트 + AC-12, AC-14 surgical mod 경계 검증 |
| 429 Rate Limit | Retry 어댑터 + 0.7초 sleep + 부분 실패 허용 |
| `market_cap=NaN` 종목 | z-score 계산 시 0으로 fillna (REQ-NT-009) |

---

## 9. 성공 기준 (Definition of Done)

- 14개 AC 전체 통과 (`acceptance.md`)
- 단위 테스트 커버리지 ≥ 85%
- 라이브 크롤링 1회 성공 (선택, `@pytest.mark.live`)
- 기존 4탭 회귀 없음 (수동 + 자동)
- 기존 파일 수정 줄 수 합계 ≤ 10줄 (surgical mod)
- DB mtime 무변경 (READ-ONLY 검증)
- 코드 리뷰 승인 (manager-quality)
