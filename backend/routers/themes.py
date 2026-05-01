from fastapi import APIRouter, Query
from pydantic import BaseModel
from backend.services.naver_theme.service import collect_and_analyze

router = APIRouter()


class ThemeInfo(BaseModel):
    """테마 정보 응답 모델."""
    theme_id: int
    theme_name: str
    change_pct: float
    change_pct_3d: float
    momentum_score: float | None = None


class StockInfo(BaseModel):
    """종목 정보 응답 모델."""
    stock_code: str
    stock_name: str
    change_pct: float
    leader_score: float | None = None
    theme_count: int | None = None


@router.get("/themes/snapshot", response_model=list[ThemeInfo])
async def themes_snapshot(top_n: int = Query(20, ge=1, le=100)) -> list[ThemeInfo]:
    """테마 목록 스냅샷 반환.

    @param top_n: 조회할 테마 수 (기본값: 20)
    @return: 테마 리스트
    """
    result = collect_and_analyze(top_n_themes=top_n, skip_details=False)

    themes = [
        ThemeInfo(
            theme_id=row["theme_id"],
            theme_name=row["theme_name"],
            change_pct=row["change_pct"],
            change_pct_3d=row["change_pct_3d"],
            momentum_score=row.get("momentum_score"),
        )
        for _, row in result.strong_themes_df.iterrows()
    ]

    return themes


@router.get("/themes/quick", response_model=list[ThemeInfo])
async def themes_quick() -> list[ThemeInfo]:
    """빠른 테마 분석 (상세 없이, ~5초).

    @return: 강세 테마 리스트
    """
    result = collect_and_analyze(skip_details=True)

    themes = [
        ThemeInfo(
            theme_id=row["theme_id"],
            theme_name=row["theme_name"],
            change_pct=row["change_pct"],
            change_pct_3d=row["change_pct_3d"],
            momentum_score=row.get("momentum_score"),
        )
        for _, row in result.strong_themes_df.head(10).iterrows()
    ]

    return themes


@router.get("/themes/by-stock/{code}", response_model=list[ThemeInfo])
async def themes_by_stock(code: str) -> list[ThemeInfo]:
    """특정 종목을 포함하는 테마 반환.

    @param code: 종목 코드
    @return: 테마 리스트
    """
    result = collect_and_analyze(skip_details=False)

    if result.stocks_df.empty:
        return []

    # 해당 종목의 테마 필터링
    stock_themes = result.stocks_df[result.stocks_df["stock_code"] == code]["theme_id"].unique()

    if len(stock_themes) == 0:
        return []

    themes_list = result.strong_themes_df[result.strong_themes_df["theme_id"].isin(stock_themes)]

    return [
        ThemeInfo(
            theme_id=row["theme_id"],
            theme_name=row["theme_name"],
            change_pct=row["change_pct"],
            change_pct_3d=row["change_pct_3d"],
            momentum_score=row.get("momentum_score"),
        )
        for _, row in themes_list.iterrows()
    ]
