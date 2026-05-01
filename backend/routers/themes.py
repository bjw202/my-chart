import requests
from fastapi import APIRouter, HTTPException

from backend.services.naver_theme import collect_and_analyze
from backend.services.naver_theme_v2 import collect_and_analyze_v2

router = APIRouter()


def _records(df) -> list:
    # 빈 DataFrame 안전 처리
    return df.to_dict(orient="records") if not df.empty else []


@router.get("/themes/snapshot")
async def themes_snapshot(top_n: int = 20, leaders_per_theme: int = 3) -> dict:
    # REQ-NT-R-001: 5종 DataFrame + metadata를 records list 형식으로 반환
    try:
        r = collect_and_analyze(
            top_n_themes=top_n,
            leaders_per_theme=leaders_per_theme,
            skip_details=False,
        )
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
    # REQ-NT-R-002: skip_details=True로 10초 이내 응답 (themes + strong_themes + metadata만)
    try:
        r = collect_and_analyze(top_n_themes=top_n, skip_details=True)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "themes": _records(r.themes_df),
        "strong_themes": _records(r.strong_themes_df),
        "metadata": r.metadata,
    }


@router.get("/themes/v2/snapshot")
async def themes_v2_snapshot(top_n: int = 20, leaders_per_theme: int = 3) -> dict:
    """V2: 모바일 stock.naver.com 기반 테마 분석. theme_description, stock_description 포함."""
    try:
        r = collect_and_analyze_v2(
            top_n_themes=top_n,
            leaders_per_theme=leaders_per_theme,
            skip_details=False,
        )
    except (requests.RequestException, ValueError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "themes": _records(r.themes_df),
        "stocks": _records(r.stocks_df),
        "strong_themes": _records(r.strong_themes_df),
        "leaders": _records(r.leaders_df),
        "multi_theme_stocks": _records(r.multi_theme_stocks_df),
        "metadata": r.metadata,
    }


@router.get("/themes/v2/quick")
async def themes_v2_quick(top_n: int = 20) -> dict:
    """V2 quick 모드: list endpoint만 호출, 10초 이내."""
    try:
        r = collect_and_analyze_v2(top_n_themes=top_n, skip_details=True)
    except (requests.RequestException, ValueError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "themes": _records(r.themes_df),
        "strong_themes": _records(r.strong_themes_df),
        "metadata": r.metadata,
    }
