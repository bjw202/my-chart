from fastapi import APIRouter, HTTPException

from backend.services.naver_theme import collect_and_analyze

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
