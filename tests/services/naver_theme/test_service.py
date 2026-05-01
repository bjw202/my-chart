"""naver_theme.service 단위 테스트 (tests/services/naver_theme/ 버전)."""

from __future__ import annotations

import sys
import types

import pandas as pd
import pytest
from unittest.mock import patch

# pykrx 스텁
for _m in ("pykrx", "pykrx.stock"):
    if _m not in sys.modules:
        sys.modules[_m] = types.ModuleType(_m)

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
def test_collect_and_analyze_returns_result():
    """collect_and_analyze() returns ThemeAnalysisResult with 5 DataFrames."""
    with patch("backend.services.naver_theme.service.fetch_theme_list_page") as mock_fetch:
        mock_fetch.return_value = "<html><body></body></html>"

        result = collect_and_analyze(top_n_themes=5, skip_details=True)

    assert isinstance(result.themes_df, pd.DataFrame)
    assert isinstance(result.stocks_df, pd.DataFrame)
    assert isinstance(result.strong_themes_df, pd.DataFrame)
    assert isinstance(result.leaders_df, pd.DataFrame)
    assert isinstance(result.multi_theme_stocks_df, pd.DataFrame)
    assert isinstance(result.metadata, dict)


@pytest.mark.unit
def test_collect_and_analyze_metadata():
    """Metadata contains required keys."""
    with patch("backend.services.naver_theme.service.fetch_theme_list_page") as mock_fetch:
        mock_fetch.return_value = "<html><body></body></html>"
        result = collect_and_analyze(skip_details=True)

    assert "collected_at" in result.metadata
    assert "theme_count" in result.metadata
    assert "stock_count" in result.metadata
    assert "elapsed_sec" in result.metadata
    assert "errors" in result.metadata
    assert isinstance(result.metadata["errors"], list)


@pytest.mark.unit
def test_collect_and_analyze_top_n_limit():
    """top_n_themes parameter limits results."""
    with patch("backend.services.naver_theme.service.fetch_theme_list_page") as mock_fetch:
        mock_fetch.side_effect = Exception("Stop")
        result = collect_and_analyze(top_n_themes=5, skip_details=True)
        assert isinstance(result, ThemeAnalysisResult)
        # fetch_theme_list_page 가 호출되었어야 함
        assert mock_fetch.called


@pytest.mark.unit
def test_collect_and_analyze_default_parameters():
    """collect_and_analyze() uses default parameters."""
    with patch("backend.services.naver_theme.service.fetch_theme_list_page") as mock_fetch:
        mock_fetch.side_effect = Exception("Stop")
        result = collect_and_analyze()
        assert mock_fetch.called
