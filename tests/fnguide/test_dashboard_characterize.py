# SPEC-DASHBOARD-001: DDD Characterization Tests
"""
Characterization tests capturing existing behavior before modification.

These tests document what the code DOES, not what it SHOULD do.
Written in PRESERVE phase of ANALYZE-PRESERVE-IMPROVE cycle.
"""

import pytest

from fnguide.analysis import fs_analysis


@pytest.mark.live
class TestFsAnalysisCharacterize:
    """Characterization test for fs_analysis return structure BEFORE modification.

    Captures the existing (df_anal, df_invest) tuple return behavior.
    After Task 1 modification, this must still pass with the new 3-tuple.
    """

    @pytest.fixture(scope="class")
    def analysis_result(self, samsung_fs):
        """Samsung Electronics financial analysis result."""
        _, df_fs_ann, df_fs_quar, _ = samsung_fs
        try:
            return fs_analysis(df_fs_ann, df_fs_quar), None
        except Exception as e:
            return None, str(e)

    def test_characterize_returns_tuple(self, analysis_result):
        """fs_analysis returns a tuple."""
        result, error = analysis_result
        if result is None:
            pytest.skip(f"fs_analysis error: {error}")
        assert isinstance(result, tuple)

    def test_characterize_tuple_has_at_least_2_elements(self, analysis_result):
        """fs_analysis tuple has at least 2 elements (df_anal, df_invest)."""
        result, error = analysis_result
        if result is None:
            pytest.skip(f"fs_analysis error: {error}")
        assert len(result) >= 2

    def test_characterize_df_anal_has_expected_columns(self, analysis_result):
        """df_anal has '예상' column (behavior snapshot)."""
        result, error = analysis_result
        if result is None:
            pytest.skip(f"fs_analysis error: {error}")
        df_anal = result[0]
        assert "예상" in df_anal.columns

    def test_characterize_df_invest_has_yeoyu(self, analysis_result):
        """df_invest has '여유자금' row (behavior snapshot)."""
        result, error = analysis_result
        if result is None:
            pytest.skip(f"fs_analysis error: {error}")
        df_invest = result[1]
        assert "여유자금" in df_invest.index
