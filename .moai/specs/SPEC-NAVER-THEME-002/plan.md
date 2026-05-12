---
id: SPEC-NAVER-THEME-002
title: 모바일 stock.naver.com 기반 테마 분석 V2 — Implementation Plan
status: Draft
version: 1.0.0
owner: bjw2002
created: 2026-05-01
updated: 2026-05-01
depends_on: SPEC-NAVER-THEME-001
---

# Implementation Plan: SPEC-NAVER-THEME-002 V2

## 메타

| 항목 | 값 |
|------|-----|
| SPEC | SPEC-NAVER-THEME-002 |
| 버전 | 1.0.0 |
| 상태 | Draft (Pending User Approval) |
| 우선순위 | High |
| 의존성 | SPEC-NAVER-THEME-001 V1 (read-only import 재사용) |
| 위험 등급 | Medium (비공식 endpoint 의존) |

---

## 1. Phase 분해 (RUN Phase 실행 순서)

| Phase | 담당 | 우선순위 | 선행 의존성 |
|-------|------|----------|-------------|
| Phase 1 — V2 백엔드 모듈 신규 작성 | expert-backend | High | 없음 |
| Phase 2 — FastAPI 라우터 V2 추가 | expert-backend | High | Phase 1 |
| Phase 3 — V1 회귀 검증 (smoke test) | expert-testing | High | Phase 2 |
| Phase 4 — V2 단위 테스트 + fixture | expert-testing | High | Phase 1 (parser, service 함수 존재) |
| Phase 5 — 라이브 통합 검증 | expert-testing | High | Phase 4 |
| Phase 6 — 통합 검증 + AC-1~14 PASS | manager-quality | High | Phase 1~5 |

> 시간 추정 사용 금지 (`.claude/rules/moai/core/agent-common-protocol.md` "Time Estimation" 준수). 우선순위 라벨 + Phase 순서로 진행 관리.

---

## 2. Phase 1 — V2 백엔드 모듈 신규 작성

### 2.1 디렉토리 구조 (신규 생성)

```
backend/services/naver_theme_v2/
├── __init__.py        # collect_and_analyze_v2, ThemeAnalysisResult 노출
├── service.py         # 단일 진입점 (오케스트레이션, V1 analyzer 재사용)
├── crawler.py         # HTTP 호출 (requests + JSON), 단일 thread, sleep 정책
├── parser.py          # JSON dict → 정규화 dict/list (필드명 access only)
├── config.py          # endpoint URL, 모바일 UA, sleep 등 상수
└── (analyzer.py, db_join.py, schemas.py는 V1에서 import — 파일 생성 X)
```

V1 `backend/services/naver_theme/`는 변경 없음.

### 2.2 모듈별 변경 규모 (V1 → V2 매트릭스)

| 모듈 | V1 path | V2 path | 변경 규모 | 비고 |
|---|---|---|---|---|
| `__init__.py` | `naver_theme/__init__.py` | `naver_theme_v2/__init__.py` | 신규 (소) | `collect_and_analyze_v2`, `ThemeAnalysisResult` re-export |
| `config.py` | `naver_theme/config.py` | `naver_theme_v2/config.py` | 신규 (소) | mobile endpoint, UA, headers; **EUC-KR 상수 없음** |
| `crawler.py` | `naver_theme/crawler.py` | `naver_theme_v2/crawler.py` | 신규 (중) | requests + JSON; specific exception only (REQ-NT2-C-005) |
| `parser.py` | `naver_theme/parser.py` | `naver_theme_v2/parser.py` | 신규 (중) | JSON dict access only; bs4/lxml 없음 |
| `analyzer.py` | `naver_theme/analyzer.py` | (재사용 via import) | 변경 없음 | DO NOT copy; import V1 모듈 — z-score 로직 single-source |
| `service.py` | `naver_theme/service.py` | `naver_theme_v2/service.py` | 신규 (중) | V2 crawler/parser 오케스트레이션 + V1 analyzer 호출 |
| `db_join.py` | `naver_theme/db_join.py` | (재사용 via import) | 변경 없음 | optional fallback only (marketValue 누락 시) |
| `schemas.py` | `naver_theme/schemas.py` | (재사용 via import) | 변경 없음 | `ThemeAnalysisResult` import 재사용 |
| `routers/themes.py` | `backend/routers/themes.py` | EDIT (add v2 routes) | 소 (+ ~30 LOC) | 2 GET routes 추가; **V1 routes 무수정** |
| `tests/test_naver_theme_v2_*` | — | 신규 | 대 | JSON fixture (live blend + synthetic) |

### 2.3 `config.py` 신규 작성

```python
# backend/services/naver_theme_v2/config.py
"""V2 모바일 endpoint 상수. URL 변경 시 이 파일만 수정 (REQ-NT2-NF-005)."""

NAVER_MOBILE_BASE_URL = "https://m.stock.naver.com"
NAVER_MOBILE_FRONT_API_PREFIX = "/front-api"
LIST_ENDPOINT_PATH = "/stock/sectors/all"
DETAIL_ENDPOINT_PATH = "/domestic/sector/item/list"

# 라이브 PoC 검증 헤더 (research.md §1.3)
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DEFAULT_REFERER = "https://m.stock.naver.com/domestic/home/theme/daily"
ACCEPT_HEADER = "application/json"

# 매너 호출 정책 (REQ-NT2-NF-001)
REQUEST_SLEEP_SECONDS = 0.7
REQUEST_TIMEOUT_SECONDS = 10
RETRY_BACKOFF_SECONDS = 1.0  # 5xx 후 retry 전 대기

# 페이지네이션 (research.md §1.2 — 서버 검증 max=50)
LIST_PAGE_SIZE = 50
DETAIL_PAGE_SIZE = 50
LIST_MAX_PAGES = 10  # 약 264 themes / 50 = 6 pages (안전 마진 4 페이지 추가)

# 응답 시간 목표 (REQ-NT2-NF-004)
SNAPSHOT_TIMEOUT_BUDGET = 30
QUICK_TIMEOUT_BUDGET = 10

# data_source label (metadata)
DATA_SOURCE = "naver_mobile_v2"
```

### 2.4 `crawler.py` 신규 작성 — 핵심 로직 sketch

```python
# backend/services/naver_theme_v2/crawler.py
"""HTTP 호출 — JSON 응답, 단일 thread, specific exception."""

import json
import time
from typing import Optional

import requests
from pydantic import ValidationError

from . import config

_SESSION: Optional[requests.Session] = None
_LAST_REQUEST_TIME = 0.0


def _get_session() -> requests.Session:
    """Session 싱글톤. 헤더는 매 요청마다 명시 (mock 캡처 가능)."""
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
    return _SESSION


def _enforce_sleep_policy() -> None:
    """REQ-NT2-NF-001 — sleep ≥ 0.7s between requests."""
    global _LAST_REQUEST_TIME
    elapsed = time.monotonic() - _LAST_REQUEST_TIME
    if elapsed < config.REQUEST_SLEEP_SECONDS:
        time.sleep(config.REQUEST_SLEEP_SECONDS - elapsed)


def _build_headers() -> dict:
    """REQ-NT2-NF-001, REQ-NT2-C-001 — anonymous, mobile UA."""
    return {
        "User-Agent": config.MOBILE_USER_AGENT,
        "Referer": config.DEFAULT_REFERER,
        "Accept": config.ACCEPT_HEADER,
    }


def _verify_content_type(response: requests.Response) -> None:
    """REQ-NT2-NF-002 — Content-Type 검증."""
    ct = response.headers.get("Content-Type", "")
    if "application/json" not in ct:
        raise ValueError(f"Unexpected Content-Type: {ct!r}")


def fetch_theme_list(page: int, page_size: int = config.LIST_PAGE_SIZE) -> dict:
    """List endpoint 호출. 5xx/timeout → 1회 retry. 영속 실패 시 raise."""
    url = f"{config.NAVER_MOBILE_BASE_URL}{config.NAVER_MOBILE_FRONT_API_PREFIX}{config.LIST_ENDPOINT_PATH}"
    params = {
        "sectorType": "theme",
        "businessDayCategory": "daily",
        "sectorSortType": "CHANGE_RATE",
        "nationType": "domestic",
        "page": page,
        "pageSize": page_size,
    }

    _enforce_sleep_policy()
    session = _get_session()

    last_exc: Optional[Exception] = None
    for attempt in (0, 1):  # 첫 시도 + 1회 retry
        try:
            response = session.get(url, params=params, headers=_build_headers(), timeout=config.REQUEST_TIMEOUT_SECONDS)
            global _LAST_REQUEST_TIME
            _LAST_REQUEST_TIME = time.monotonic()

            if response.status_code >= 500:
                last_exc = requests.HTTPError(f"5xx: {response.status_code}")
                time.sleep(config.RETRY_BACKOFF_SECONDS)
                continue

            _verify_content_type(response)
            return response.json()
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            last_exc = e
            if attempt == 0:
                time.sleep(config.RETRY_BACKOFF_SECONDS)
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("unreachable")


def fetch_theme_detail(theme_id: int, page_size: int = config.DETAIL_PAGE_SIZE) -> dict:
    """Detail endpoint 호출. 동일한 retry 정책."""
    url = f"{config.NAVER_MOBILE_BASE_URL}{config.NAVER_MOBILE_FRONT_API_PREFIX}{config.DETAIL_ENDPOINT_PATH}"
    params = {
        "sectorType": "theme",
        "sectorCode": str(theme_id),
        "sectorSortType": "CHANGE_RATE",
        "page": 1,
        "pageSize": page_size,
    }
    # ... (동일 패턴)
```

**§13-4 교훈 인코딩:** specific exception (`requests.RequestException`, `json.JSONDecodeError`, `ValueError`)만 catch. `bare except` 사용 금지.

### 2.5 `parser.py` 신규 작성 — 핵심 로직 sketch

```python
# backend/services/naver_theme_v2/parser.py
"""JSON dict → 정규화된 list/dict. 필드명 access only (§13-1 교훈)."""

from typing import Optional


def parse_theme_list(response_json: dict) -> list[dict]:
    """list endpoint 응답을 V1 형식의 dict 리스트로 변환.
    
    필드명 access only — positional indexing 금지 (§13-1).
    """
    if not response_json.get("isSuccess"):
        return []

    sectors = response_json.get("result", {}).get("sectors", [])
    parsed = []
    for sec in sectors:
        # KeyError 가 raise되면 service.py가 catch하여 errors[]에 기록
        theme_id = int(sec["sectorCode"])  # string-of-int → int (V1 호환)
        parsed.append({
            "theme_id": theme_id,
            "theme_name": sec["sectorName"],
            "change_rate": float(sec["changeRate"]),
            "rising_count": int(sec["risingCount"]),
            "unchanged_count": int(sec["unChangedCount"]),
            "falling_count": int(sec["fallingCount"]),
            # NOTE: list 응답의 sectorDescription은 항상 null (research.md §2.1)
            "theme_description": None,
            # list 응답의 totalMarketCap은 백만원 단위 → V2에서 사용 X (§2.3 단위 매트릭스)
        })
    return parsed


def parse_theme_detail(response_json: dict, theme_id: int) -> Optional[dict]:
    """Detail endpoint 응답을 V1 stocks_df row dict 리스트로 변환."""
    if not response_json.get("isSuccess"):
        return None

    result = response_json.get("result", {})
    theme_description: Optional[str] = result.get("sectorDescription")  # nullable
    theme_name = result.get("sectorName", "")

    items_parsed = []
    for item in result.get("items", []):
        items_parsed.append({
            "theme_id": theme_id,
            "theme_name": theme_name,
            "code": item["itemCode"],
            "name": item["name"],
            "market_cap": int(item["marketValue"]) if item.get("marketValue") is not None else None,  # 원 단위 (§2.3)
            "change_rate": float(item["fluctuationsRatio"]) if item.get("fluctuationsRatio") else 0.0,
            "inclusion_reason": item.get("description"),  # V1 컬럼 호환성 — V1의 inclusion_reason 자리에 V2 description 매핑
            "stock_description": item.get("description"),  # V2 신규 컬럼 (REQ-NT2-005)
        })

    return {
        "theme_id": theme_id,
        "theme_description": theme_description,
        "items": items_parsed,
    }
```

**§13-1, §13-2 교훈 인코딩:** 
- `sec["sectorCode"]` 등 필드명 access (positional indexing 없음)
- `Content-Type: application/json` 검증은 crawler.py에서 수행 (encoding 명시)

### 2.6 `service.py` 신규 작성 — 오케스트레이션

```python
# backend/services/naver_theme_v2/service.py
"""단일 진입점 + V1 analyzer/db_join 재사용."""

import json
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests
from pydantic import ValidationError

# V1 모듈 재사용 (import만, 파일 수정 X)
from backend.services.naver_theme.schemas import ThemeAnalysisResult
from backend.services.naver_theme.analyzer import (
    compute_strong_themes,
    compute_leaders,
    compute_multi_theme_stocks,
    # ... V1 analyzer functions (실 함수명은 V1 코드 참조)
)
from backend.services.naver_theme.db_join import join_market_cap  # optional fallback

from . import config, crawler, parser


def collect_and_analyze_v2(
    top_n_themes: int = 20,
    leaders_per_theme: int = 3,
    skip_details: bool = False,
) -> ThemeAnalysisResult:
    """V2 단일 진입점 (REQ-NT2-001).

    Args:
        top_n_themes: 강세 테마 상위 N개 (default 20, V1과 동일)
        leaders_per_theme: 테마별 주도주 N개
        skip_details: True면 list endpoint만 호출 (10초 이내 빠른 모드)

    Returns:
        ThemeAnalysisResult (V1 schema 동일, themes_df + stocks_df에 신규 컬럼 추가)
    """
    errors: list[dict] = []

    # ── Phase A: list endpoint 페이지네이션 ───────────────────────
    all_themes = []
    for page in range(1, config.LIST_MAX_PAGES + 1):
        try:
            list_resp = crawler.fetch_theme_list(page=page, page_size=config.LIST_PAGE_SIZE)
            page_themes = parser.parse_theme_list(list_resp)
            if not page_themes:
                break  # 마지막 페이지
            all_themes.extend(page_themes)
            if len(page_themes) < config.LIST_PAGE_SIZE:
                break
        except (requests.RequestException, json.JSONDecodeError, KeyError, ValidationError, ValueError) as e:
            errors.append({
                "theme_id": None,
                "stage": "list_fetch",
                "reason": f"page={page}: {type(e).__name__}: {e}",
            })
            # 부분 실패 허용 (REQ-NT2-NF-003)
            break

    themes_df = pd.DataFrame(all_themes)
    if len(themes_df) == 0:
        # 모든 list 호출 실패 — 빈 결과 반환
        return _empty_result(errors)

    # ── Phase B: top-N 결정 (V1 analyzer 재사용) ─────────────────
    strong_themes_df = compute_strong_themes(themes_df, top_n=top_n_themes)
    top_theme_ids = strong_themes_df["theme_id"].tolist()

    # ── Phase C: detail endpoint (skip_details=False일 때만) ──────
    all_stocks = []
    if not skip_details:
        for theme_id in top_theme_ids:
            try:
                detail_resp = crawler.fetch_theme_detail(theme_id=theme_id)
                detail_parsed = parser.parse_theme_detail(detail_resp, theme_id=theme_id)
                if detail_parsed is None:
                    errors.append({
                        "theme_id": theme_id,
                        "stage": "endpoint_drift",
                        "reason": "isSuccess=false",
                    })
                    continue
                # theme_description을 themes_df에 머지
                themes_df.loc[themes_df["theme_id"] == theme_id, "theme_description"] = detail_parsed["theme_description"]
                all_stocks.extend(detail_parsed["items"])
            except (requests.RequestException, json.JSONDecodeError, KeyError, ValidationError, ValueError) as e:
                errors.append({
                    "theme_id": theme_id,
                    "stage": "detail_fetch",
                    "reason": f"{type(e).__name__}: {e}",
                })
                continue

    stocks_df = pd.DataFrame(all_stocks) if all_stocks else _empty_stocks_df()

    # ── Phase D: market_cap fallback (REQ-NT2-006) ─────────────────
    # marketValue가 누락된 종목에 대해 db_join 사용 (optional)
    if "market_cap" in stocks_df.columns:
        missing_mask = stocks_df["market_cap"].isna()
        if missing_mask.any():
            stocks_df.loc[missing_mask, "market_cap"] = stocks_df.loc[missing_mask, "code"].apply(
                lambda c: join_market_cap(c) or 0  # mode=ro URI (V1 보존)
            )

    # ── Phase E: V1 analyzer 재사용 ──────────────────────────────
    leaders_df = compute_leaders(stocks_df, leaders_per_theme=leaders_per_theme)
    multi_theme_stocks_df = compute_multi_theme_stocks(stocks_df)

    return ThemeAnalysisResult(
        themes_df=themes_df,
        stocks_df=stocks_df,
        strong_themes_df=strong_themes_df,
        leaders_df=leaders_df,
        multi_theme_stocks_df=multi_theme_stocks_df,
        metadata={
            "data_source": config.DATA_SOURCE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_themes_seen": len(themes_df),
            "errors": errors,
        },
    )


def _empty_result(errors: list[dict]) -> ThemeAnalysisResult:
    """모든 list 호출이 실패한 경우 빈 결과 반환 (예외 X — REQ-NT2-NF-003)."""
    empty_themes = pd.DataFrame(columns=["theme_id", "theme_name", "change_rate", "score", "rank", "rising_count", "unchanged_count", "falling_count", "theme_description"])
    empty_stocks = pd.DataFrame(columns=["theme_id", "theme_name", "code", "name", "market_cap", "change_rate", "inclusion_reason", "stock_description"])
    return ThemeAnalysisResult(
        themes_df=empty_themes,
        stocks_df=empty_stocks,
        strong_themes_df=empty_themes.copy(),
        leaders_df=empty_stocks.copy(),
        multi_theme_stocks_df=empty_stocks.copy(),
        metadata={
            "data_source": config.DATA_SOURCE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_themes_seen": 0,
            "errors": errors,
        },
    )
```

**§13-3, §13-4, §13-5 교훈 인코딩:**
- §13-3: `db_join.py` 사용 시 V1의 `mode=ro` URI 패턴 보존 (V1 코드 자체 무수정)
- §13-4: `except (requests.RequestException, json.JSONDecodeError, KeyError, ValidationError, ValueError)` — bare except 없음
- §13-5: `errors.append({"theme_id": ..., "stage": ..., "reason": ...})` — dict 리스트

### 2.7 `__init__.py` 신규 작성

```python
# backend/services/naver_theme_v2/__init__.py
"""V2 모바일 테마 분석 모듈. V1 schema 재사용."""

from backend.services.naver_theme.schemas import ThemeAnalysisResult
from .service import collect_and_analyze_v2

__all__ = ["collect_and_analyze_v2", "ThemeAnalysisResult"]
```

---

## 3. Phase 2 — FastAPI 라우터 V2 추가

### 3.1 `backend/routers/themes.py` EDIT (V1 routes 무수정)

V1 시점의 `themes.py` 구조는 다음과 같음 (V1 plan.md §3에서 확인):

```python
# 기존 (V1 ship 시점)
from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult

router = APIRouter(prefix="/api/themes", tags=["themes"])

@router.get("/snapshot", response_model=ThemeSnapshotResponse)
def get_themes_snapshot():
    return collect_and_analyze(skip_details=False)

@router.get("/quick", response_model=ThemeSnapshotResponse)
def get_themes_quick():
    return collect_and_analyze(skip_details=True)
```

V2 추가 (insert만, V1 함수는 손대지 않음):

```python
# V2 추가 import
from backend.services.naver_theme_v2 import collect_and_analyze_v2

# V2 라우트 (REQ-NT2-R-001, REQ-NT2-R-002)
@router.get("/v2/snapshot", response_model=ThemeSnapshotResponse)
def get_themes_v2_snapshot():
    """V2: 모바일 stock.naver.com 기반 테마 분석. theme_description, stock_description 포함."""
    return collect_and_analyze_v2(skip_details=False)


@router.get("/v2/quick", response_model=ThemeSnapshotResponse)
def get_themes_v2_quick():
    """V2 quick 모드: list endpoint만 호출, 10초 이내."""
    return collect_and_analyze_v2(skip_details=True)
```

### 3.2 변경 라인 수 제한

- `backend/routers/themes.py`: +30 LOC 이내 (import 1 + 함수 2개)
- 기타 백엔드 파일: 0 변경
- 프론트엔드 파일: 0 변경 (V2 채택은 별도 SPEC)

### 3.3 V1 routes 회귀 검증

- V1의 `get_themes_snapshot`, `get_themes_quick` 함수 본문은 byte-identical (단, line number만 변동 가능)
- V1 import (`from backend.services.naver_theme import collect_and_analyze`)는 그대로 유지
- V2 import는 V1 import 다음 줄에 추가 (하단으로 이동시키지 않음)

---

## 4. Phase 3 — V1 회귀 검증

### 4.1 V1 단위 테스트 그대로 PASS

V1 ship 시점 (commit 12d81b1)의 단위 테스트 51개가 V2 구현 후에도 그대로 PASS해야 한다.

```bash
source .venv/bin/activate
pytest tests/test_naver_theme_parser.py tests/test_naver_theme_analyzer.py -v
# Expected: 51 passed
```

### 4.2 V1 endpoint smoke test

```bash
# 백엔드 로컬 부팅 후
curl -s http://127.0.0.1:8000/api/themes/snapshot | jq '.themes_df | length'  # > 0
curl -s http://127.0.0.1:8000/api/themes/quick | jq '.themes_df | length'  # > 0
```

V1 응답 shape이 변하지 않았는지 확인 (key set 비교).

---

## 5. Phase 4 — V2 단위 테스트 + fixture

### 5.1 fixture 디렉토리 (§13-7 교훈)

```
tests/fixtures/naver_theme_v2/
├── list_p1_real.json          # 라이브 fetch 결과 (research.md PoC에서 보존)
├── detail_178_real.json       # 라이브 fetch 결과 (전선 테마)
├── list_synthetic.json        # 합성: corner case (sectors=[], single sector, etc.)
├── detail_synthetic.json      # 합성: sectorDescription=null, items=[]
├── detail_no_market_value.json  # 합성: marketValue=null (db_join fallback 검증)
└── error_5xx_response.json    # 합성: isSuccess=false
```

### 5.2 단위 테스트 파일 구조

```
tests/test_naver_theme_v2_parser.py
tests/test_naver_theme_v2_crawler.py
tests/test_naver_theme_v2_service.py
tests/test_naver_theme_v2_routes.py
```

### 5.3 테스트 케이스 매핑 (AC → test)

| AC | test 함수 | 파일 |
|---|---|---|
| AC-1 | `test_collect_and_analyze_v2_signature` | service |
| AC-2 | `test_collect_and_analyze_v2_returns_result` | service |
| AC-3 | `test_themes_df_theme_description_column` | service |
| AC-4 | `test_stocks_df_stock_description_column` | service |
| AC-5 | `test_v1_columns_preserved` | service |
| AC-6 | `test_errors_dict_shape` | service |
| AC-7 | `test_crawler_headers` | crawler |
| AC-8 | `test_crawler_sleep_policy` | crawler |
| AC-9 | `test_v2_routes_registered` | routes |
| AC-10 | `test_v1_routes_unchanged` | routes |
| AC-11 | `test_db_mtime_unchanged` | service |
| AC-12 | `test_frontend_columns_compatibility` | service |
| AC-13 | `test_5xx_retry_then_partial_failure` | crawler + service |
| AC-14 | `test_endpoint_url_from_config_only` | crawler + service |

### 5.4 라이브 marker

```python
# tests/test_naver_theme_v2_service.py

@pytest.mark.live
def test_collect_and_analyze_v2_live():
    """라이브 mobile API 호출. CI에서는 skip, 로컬에서만 실행 (§13-6)."""
    result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)
    assert isinstance(result, ThemeAnalysisResult)
    assert len(result.themes_df) >= 1
    assert result.themes_df["theme_description"].notna().sum() >= 1
    assert result.stocks_df["stock_description"].notna().sum() >= 1
```

`pytest.ini`에 marker 등록 (V1과 동일 패턴):

```ini
markers =
    live: requires live network access to Naver API
```

실행 명령:
```bash
# 평소 (CI): live skip
pytest -v -m "not live"

# 로컬 라이브 검증
pytest -v -m live
```

### 5.5 커버리지 목표

```bash
pytest --cov=backend.services.naver_theme_v2 --cov-report=term --cov-fail-under=85 \
       tests/test_naver_theme_v2_*.py
```

목표: `backend.services.naver_theme_v2.*` 모듈 ≥ 85% (V1은 99%, V2도 동일 수준 권장).

---

## 6. Phase 5 — 라이브 통합 검증

V1 §13-6 교훈을 RUN phase에서 처음부터 적용:

1. `pytest -v -m live tests/test_naver_theme_v2_service.py::test_collect_and_analyze_v2_live` 실행
2. 라이브 응답에서 다음 4가지를 자동 검증:
   - `themes_df["theme_description"]` non-null count ≥ 1
   - `stocks_df["stock_description"]` non-null count ≥ 1
   - `errors` 리스트가 dict 형식 (REQ-NT2-NF-003)
   - `metadata["data_source"] == "naver_mobile_v2"`

3. 라이브 호출 결과 fixture로 보존:
   - `tests/fixtures/naver_theme_v2/list_p1_real.json`
   - `tests/fixtures/naver_theme_v2/detail_<top_id>_real.json`

4. 응답시간 측정 (REQ-NT2-NF-004):
   - snapshot ≤ 30s
   - quick ≤ 10s

---

## 7. Phase 6 — 통합 검증 (manager-quality)

### 7.1 AC 14건 PASS 확인

```bash
pytest -v -m "not live" tests/test_naver_theme_v2_*.py
# Expected: 14 AC × N test = all pass
```

### 7.2 V1 회귀 PASS

```bash
pytest -v tests/test_naver_theme_parser.py tests/test_naver_theme_analyzer.py
# Expected: 51 tests passed (V1 baseline)
```

### 7.3 DB mtime check

```bash
stat -f "%m" Output/stock_data_daily.db  # before
pytest -v -m "not live" tests/test_naver_theme_v2_*.py
stat -f "%m" Output/stock_data_daily.db  # after — must equal before
```

### 7.4 frontend 회귀 (vitest)

```bash
cd frontend
npm run test
# Expected: V1 시점 그대로 PASS (V2는 frontend 변경 X)
```

---

## 8. 위험 mitigation 매핑 (research.md §5 → plan.md 적용)

| 위험 ID | 위험 | mitigation |
|---|---|---|
| R-1 | endpoint URL 변경 (sentry release 활발) | `config.py` 격리 (REQ-NT2-NF-005, AC-14). URL 한 곳만 수정 |
| R-2 | pageSize 상한 50 변경 | `config.LIST_PAGE_SIZE` config 상수 + 서버 검증 메시지 catch (`detailCode: too_big`) → errors[] |
| R-3 | rate limit 도입 | `REQUEST_SLEEP_SECONDS=0.7` + 5xx 1회 retry (AC-8, AC-13) |
| R-4 | sectorDescription null | nullable column (AC-3) |
| R-5 | description null (per stock) | nullable column (AC-4) |
| R-6 | sectorCode string vs V1 int | parser.py `int(sectorCode)` 정규화 |
| R-7 | marketValue/marketCap 단위 혼동 | research.md §2.3 단위 매트릭스 — detail의 marketValue (원)만 사용 |
| R-8 | theme ID 체계 변경 | 호환성 unit test (AC-12) |
| R-9 | 인증 도입 | schema 검증 → ValidationError catch (REQ-NT2-NF-003) |
| R-10 | analyzer.py 호환성 | V1 columns superset 유지 (REQ-NT2-008, AC-5, AC-12) |

---

## 9. V1 RUN phase 교훈 인코딩 매핑 (§13 → plan.md 위치)

V2 핸드오프 §13의 7개 교훈을 plan의 어느 섹션에서 인코딩하는지 명시:

| §13 항목 | 교훈 | plan.md 인코딩 위치 |
|---|---|---|
| §13-1 | 컬럼 인덱스 의존 금지 → 필드명 access | §2.5 `parser.py` (sec["sectorCode"] 등 dict access) |
| §13-2 | 인코딩 강제 누락 금지 → Content-Type 검증 | §2.4 `crawler.py` `_verify_content_type()` |
| §13-3 | DB 연결 read-only URI | §2.6 `service.py` Phase D — V1 `db_join.join_market_cap` 호출 (V1 자체 보존) |
| §13-4 | bare except 금지 → specific exception | §2.4, §2.6 — `except (requests.RequestException, json.JSONDecodeError, KeyError, ValidationError, ValueError)` (REQ-NT2-C-005) |
| §13-5 | errors는 dict 형식 | §2.6 `errors.append({"theme_id": ..., "stage": ..., "reason": ...})` (REQ-NT2-NF-003, AC-6) |
| §13-6 | 라이브 검증 1회 필수 | §6 Phase 5 — `@pytest.mark.live` 자동 검증 |
| §13-7 | fixture는 라이브 + synthetic 혼합 | §5.1 fixture 디렉토리 — `*_real.json` + `*_synthetic.json` |

---

## 10. 검증 도구 매트릭스

| 도구 | 용도 | 임계값 |
|---|---|---|
| pytest | 단위 + 통합 테스트 | 14 AC PASS |
| pytest --cov | 커버리지 | ≥ 85% |
| pytest -m live | 라이브 통합 | 1회 PASS |
| pytest -m "not live" | CI mode | V1 51 + V2 14 모두 PASS |
| ruff/mypy (이미 V1에서 사용) | 린팅 | 0 새 warning |
| vitest (frontend) | frontend 회귀 | V1 시점과 동일 PASS |

---

## 11. Definition of Done (RUN phase 종료 조건)

- [ ] AC-1 ~ AC-14 자동 검증 PASS (14/14)
- [ ] AC-PoC-Resolution PASS (해당 없음으로 trivially PASS)
- [ ] V1 단위 테스트 51개 그대로 PASS (회귀 0)
- [ ] V1 endpoint `/api/themes/snapshot`, `/api/themes/quick` 응답 변경 없음 (smoke test PASS)
- [ ] frontend vitest 신규 회귀 0건
- [ ] DB mtime 무변경
- [ ] 라이브 통합 테스트 1회 PASS (`@pytest.mark.live`)
- [ ] 커버리지 ≥ 85% (`backend.services.naver_theme_v2.*`)
- [ ] `bare except` 0건 (`grep -rE 'except\s*:|except\s+Exception\s*:' backend/services/naver_theme_v2/`)
- [ ] `inline URL` 0건 (`grep -rE '"https?://m?\.?stock\.naver\.com' backend/services/naver_theme_v2/crawler.py backend/services/naver_theme_v2/service.py`)

---

## 12. RUN phase 시작 명령 (next session)

V2 SPEC plan 승인 후 사용자가 실행할 명령:

```
/clear
/moai run SPEC-NAVER-THEME-002
```

---

Version: 1.0.0
Status: Draft (Pending User Approval)
Next phase: User annotation cycle → approval → `/clear` → `/moai run SPEC-NAVER-THEME-002`
