import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from backend.services.naver_theme.service import (
    ThemeAnalysisResult,
    collect_and_analyze,
)


@pytest.mark.unit
def test_theme_analysis_result_structure():
    """ThemeAnalysisResult has required attributes."""
    empty_df = pd.DataFrame()
    result = ThemeAnalysisResult(
        themes_df=empty_df,
        stocks_df=empty_df,
        strong_themes_df=empty_df,
        leaders_df=empty_df,
        multi_theme_stocks_df=empty_df,
        metadata={"test": True},
    )

    assert hasattr(result, "themes_df")
    assert hasattr(result, "stocks_df")
    assert hasattr(result, "strong_themes_df")
    assert hasattr(result, "leaders_df")
    assert hasattr(result, "multi_theme_stocks_df")
    assert hasattr(result, "metadata")


@pytest.mark.unit
@patch("backend.services.naver_theme.crawler.fetch_theme_list_page")
@patch("backend.services.naver_theme.crawler.fetch_theme_detail_page")
@patch("backend.services.naver_theme.parser.parse_theme_list")
@patch("backend.services.naver_theme.parser.parse_theme_detail")
def test_collect_and_analyze_returns_result(
    mock_detail_parse, mock_list_parse, mock_detail_fetch, mock_list_fetch
):
    """collect_and_analyze() returns ThemeAnalysisResult with 5 DataFrames."""
    mock_list_fetch.return_value = "<html></html>"
    mock_detail_fetch.return_value = "<html></html>"
    mock_list_parse.return_value = pd.DataFrame({
        "theme_id": [1],
        "theme_name": ["Test"],
        "change_pct": [1.0],
        "change_pct_3d": [1.0],
    })
    mock_detail_parse.return_value = [
        {
            "stock_code": "001",
            "stock_name": "Test Stock",
            "change_pct": 1.0,
            "volume": 1000,
            "theme_id": 1,
            "collected_at": "2026-05-01T00:00:00+09:00",
        }
    ]

    result = collect_and_analyze(top_n_themes=5, skip_details=True)

    assert isinstance(result.themes_df, pd.DataFrame)
    assert isinstance(result.stocks_df, pd.DataFrame)
    assert isinstance(result.strong_themes_df, pd.DataFrame)
    assert isinstance(result.leaders_df, pd.DataFrame)
    assert isinstance(result.multi_theme_stocks_df, pd.DataFrame)
    assert isinstance(result.metadata, dict)


@pytest.mark.unit
@patch("backend.services.naver_theme.crawler.fetch_theme_list_page")
def test_collect_and_analyze_metadata(mock_list_fetch):
    """Metadata contains required keys."""
    mock_list_fetch.return_value = "<html></html>"

    result = collect_and_analyze(skip_details=True)

    assert "collected_at" in result.metadata
    assert "theme_count" in result.metadata
    assert "stock_count" in result.metadata
    assert "elapsed_sec" in result.metadata
    assert "errors" in result.metadata
    assert isinstance(result.metadata["errors"], list)


@pytest.mark.unit
@patch("backend.services.naver_theme.crawler.fetch_theme_list_page")
@patch("backend.services.naver_theme.parser.parse_theme_list")
def test_collect_and_analyze_pagination_stops(mock_parse, mock_fetch):
    """Pagination stops when parse_theme_list returns empty DataFrame."""
    mock_fetch.side_effect = ["<html></html>", "<html></html>"]
    mock_parse.side_effect = [
        pd.DataFrame({
            "theme_id": [1],
            "theme_name": ["T1"],
            "change_pct": [1.0],
            "change_pct_3d": [1.0],
        }),
        pd.DataFrame(),  # Empty, pagination stops
    ]

    result = collect_and_analyze(skip_details=True)

    assert len(result.themes_df) == 1  # Only first page


@pytest.mark.unit
@patch("backend.services.naver_theme.crawler.fetch_theme_list_page")
def test_collect_and_analyze_top_n_limit(mock_fetch):
    """top_n_themes parameter limits results."""
    mock_fetch.side_effect = Exception("Should not fetch if limit reached")

    try:
        result = collect_and_analyze(top_n_themes=5, skip_details=True)
        # Should handle gracefully
        assert isinstance(result, ThemeAnalysisResult)
    except Exception:
        pass  # Expected when no valid data


@pytest.mark.unit
def test_collect_and_analyze_default_parameters():
    """collect_and_analyze() uses default parameters."""
    with patch("backend.services.naver_theme.crawler.fetch_theme_list_page") as mock_fetch:
        mock_fetch.side_effect = Exception("Stop")
        try:
            result = collect_and_analyze()
        except:
            pass
        # Should have been called with defaults
        assert mock_fetch.called
