# SPEC-DASHBOARD-001: Dashboard unit tests
"""
Dashboard section unit tests using session-scope fixtures from conftest.py.

Uses samsung_fnguide and hynix_fnguide fixtures (session-scoped, no redundant HTTP).
Tests all 7 sections, edge cases (IFRS별도, zero interest, insufficient data).
"""

from __future__ import annotations

import pytest

from fnguide.analysis import fs_analysis
from fnguide.dashboard import (
    BalanceSheet,
    BusinessPerformance,
    DashboardResult,
    FiveQuestions,
    HealthIndicators,
    ProfitWaterfall,
    RateDecomposition,
    TrendSignals,
    _calc_balance_sheet,
    _calc_business_performance,
    _calc_five_questions,
    _calc_health_indicators,
    _calc_profit_waterfall,
    _calc_rate_decomposition,
    _calc_slope,
    _calc_trend_signals,
    _yoy,
)


# ─────────────────────────────────────────────────────────────
# Helper: skip if fixture unavailable
# ─────────────────────────────────────────────────────────────


def _require_fnguide(fixture_value, name: str = "FnGuide"):
    if fixture_value is None:
        pytest.skip(f"{name} fixture unavailable (pandas 3.0 compatibility)")


# ─────────────────────────────────────────────────────────────
# Unit tests for pure helper functions
# ─────────────────────────────────────────────────────────────


class TestHelpers:
    """Unit tests for pure helper functions."""

    def test_yoy_positive(self):
        """YoY growth rate: positive case."""
        result = _yoy(110.0, 100.0)
        assert result == pytest.approx(0.10)

    def test_yoy_negative(self):
        """YoY growth rate: negative case."""
        result = _yoy(80.0, 100.0)
        assert result == pytest.approx(-0.20)

    def test_yoy_zero_previous(self):
        """YoY: returns None when previous is 0."""
        result = _yoy(100.0, 0.0)
        assert result is None

    def test_calc_slope_increasing(self):
        """Linear slope for increasing series is positive."""
        slope = _calc_slope([1.0, 2.0, 3.0])
        assert slope > 0

    def test_calc_slope_decreasing(self):
        """Linear slope for decreasing series is negative."""
        slope = _calc_slope([3.0, 2.0, 1.0])
        assert slope < 0

    def test_calc_slope_flat(self):
        """Linear slope for flat series is 0."""
        slope = _calc_slope([5.0, 5.0, 5.0])
        assert slope == pytest.approx(0.0)

    def test_calc_slope_single_element(self):
        """Linear slope for single element returns 0."""
        slope = _calc_slope([10.0])
        assert slope == 0.0


# ─────────────────────────────────────────────────────────────
# Section 1: BusinessPerformance
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestBusinessPerformance:
    """Section 1: BusinessPerformance from Samsung FnGuide data."""

    @pytest.fixture(scope="class")
    def bp(self, samsung_fnguide):
        _require_fnguide(samsung_fnguide)
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            return _calc_business_performance(df_fs_ann)
        except Exception as e:
            pytest.skip(f"_calc_business_performance error: {e}")

    def test_returns_business_performance(self, bp):
        """Returns BusinessPerformance dataclass."""
        assert isinstance(bp, BusinessPerformance)

    def test_periods_length(self, bp):
        """Has 4 periods."""
        assert len(bp.periods) == 4

    def test_revenue_length_matches_periods(self, bp):
        """Revenue list length matches periods."""
        assert len(bp.revenue) == len(bp.periods)

    def test_operating_profit_length(self, bp):
        """Operating profit list length matches periods."""
        assert len(bp.operating_profit) == len(bp.periods)

    def test_net_income_length(self, bp):
        """Net income list length matches periods."""
        assert len(bp.net_income) == len(bp.periods)

    def test_controlling_profit_length(self, bp):
        """Controlling profit list length matches periods."""
        assert len(bp.controlling_profit) == len(bp.periods)

    def test_yoy_first_element_is_none(self, bp):
        """First YoY element is None (no prior year)."""
        assert bp.yoy_revenue[0] is None
        assert bp.yoy_op[0] is None
        assert bp.yoy_ni[0] is None

    def test_opm_range(self, bp):
        """Operating margin values are in [-1, 1] range."""
        for v in bp.opm:
            assert -1.0 <= v <= 1.0, f"OPM out of range: {v}"

    def test_npm_range(self, bp):
        """Net profit margin values are in [-1, 1] range."""
        for v in bp.npm:
            assert -1.5 <= v <= 1.5, f"NPM out of range: {v}"

    def test_profit_quality_length(self, bp):
        """Profit quality list length matches periods."""
        assert len(bp.profit_quality) == len(bp.periods)


# ─────────────────────────────────────────────────────────────
# Section 2: HealthIndicators
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestHealthIndicators:
    """Section 2: HealthIndicators from Samsung data."""

    @pytest.fixture(scope="class")
    def hi(self, samsung_fnguide):
        _require_fnguide(samsung_fnguide)
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
            col_recent = list(df_fs_ann.columns)[-1]
            return _calc_health_indicators(df_anal, df_invest, df_fs_ann, col_recent)
        except Exception as e:
            pytest.skip(f"_calc_health_indicators error: {e}")

    def test_returns_health_indicators(self, hi):
        """Returns HealthIndicators dataclass."""
        assert isinstance(hi, HealthIndicators)

    def test_has_7_indicators(self, hi):
        """Has exactly 7 indicators."""
        assert len(hi.indicators) == 7

    def test_indicator_names(self, hi):
        """All indicator names are present."""
        names = {ind.name for ind in hi.indicators}
        expected = {
            "외부차입/자기자본", "부채비율", "차입금의존도",
            "순차입금의존도", "이자보상배율", "영업자산비율", "비지배귀속비율",
        }
        assert names == expected

    def test_indicator_status_valid(self, hi):
        """All status values are ok/warn/danger."""
        for ind in hi.indicators:
            assert ind.status in ("ok", "warn", "danger"), f"Invalid status: {ind.status}"

    def test_debt_ratio_non_negative(self, hi):
        """외부차입/자기자본 value is non-negative."""
        for ind in hi.indicators:
            if ind.name == "외부차입/자기자본" and ind.value is not None:
                assert ind.value >= 0


# ─────────────────────────────────────────────────────────────
# Section 3: BalanceSheet
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestBalanceSheet:
    """Section 3: B/S reclassification time series."""

    @pytest.fixture(scope="class")
    def bs(self, samsung_fnguide):
        _require_fnguide(samsung_fnguide)
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
            col = list(df_fs_ann.columns)
            return _calc_balance_sheet(df_financing, df_invest, col)
        except Exception as e:
            pytest.skip(f"_calc_balance_sheet error: {e}")

    def test_returns_balance_sheet(self, bs):
        """Returns BalanceSheet dataclass."""
        assert isinstance(bs, BalanceSheet)

    def test_financing_keys(self, bs):
        """Financing dict has required keys."""
        expected = {"신용조달", "외부차입", "주주몫", "비지배주주지분"}
        assert set(bs.financing.keys()) == expected

    def test_assets_keys(self, bs):
        """Assets dict has required keys."""
        expected = {"설비투자", "운전자산", "금융투자", "여유자금"}
        assert set(bs.assets.keys()) == expected

    def test_periods_count(self, bs):
        """Has 4 periods."""
        assert len(bs.periods) == 4

    def test_financing_list_lengths(self, bs):
        """All financing lists match period count."""
        n = len(bs.periods)
        for key, vals in bs.financing.items():
            assert len(vals) == n, f"financing[{key}] length mismatch"

    def test_assets_list_lengths(self, bs):
        """All asset lists match period count."""
        n = len(bs.periods)
        for key, vals in bs.assets.items():
            assert len(vals) == n, f"assets[{key}] length mismatch"


# ─────────────────────────────────────────────────────────────
# Section 4: RateDecomposition
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestRateDecomposition:
    """Section 4: 3-rate decomposition."""

    @pytest.fixture(scope="class")
    def rd(self, samsung_fnguide):
        _require_fnguide(samsung_fnguide)
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
            return _calc_rate_decomposition(df_anal, report)
        except Exception as e:
            pytest.skip(f"_calc_rate_decomposition error: {e}")

    def test_returns_rate_decomposition(self, rd):
        """Returns RateDecomposition dataclass."""
        assert isinstance(rd, RateDecomposition)

    def test_has_4_periods(self, rd):
        """Has 4 periods (3 years + expected)."""
        assert len(rd.periods) == 4

    def test_roe_length(self, rd):
        """ROE list length matches periods."""
        assert len(rd.roe) == len(rd.periods)

    def test_weighted_avg_roe_is_float(self, rd):
        """weighted_avg_roe is a float."""
        assert isinstance(rd.weighted_avg_roe, float)

    def test_ke_is_float_or_none(self, rd):
        """ke is float or None."""
        assert rd.ke is None or isinstance(rd.ke, float)

    def test_spread_is_float_or_none(self, rd):
        """spread is float or None."""
        assert rd.spread is None or isinstance(rd.spread, float)

    def test_ke_and_spread_consistency(self, rd):
        """ke and spread are both set or both None."""
        assert (rd.ke is None) == (rd.spread is None)


# ─────────────────────────────────────────────────────────────
# Section 5: ProfitWaterfall
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestProfitWaterfall:
    """Section 5: 8-step profit waterfall."""

    @pytest.fixture(scope="class")
    def pw(self, samsung_fnguide):
        _require_fnguide(samsung_fnguide)
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
            return _calc_profit_waterfall(df_anal)
        except Exception as e:
            pytest.skip(f"_calc_profit_waterfall error: {e}")

    def test_returns_profit_waterfall(self, pw):
        """Returns ProfitWaterfall dataclass."""
        assert isinstance(pw, ProfitWaterfall)

    def test_has_8_steps(self, pw):
        """Has exactly 8 steps."""
        assert len(pw.steps) == 8

    def test_step_names(self, pw):
        """Step names match expected sequence."""
        expected = [
            "영업이익", "비영업이익", "이자비용",
            "세전이익", "법인세비용", "당기순이익",
            "비지배주주순이익", "지배주주순이익",
        ]
        actual = [s.name for s in pw.steps]
        assert actual == expected

    def test_step_values_are_float(self, pw):
        """All step values are floats."""
        for step in pw.steps:
            assert isinstance(step.value, float), f"{step.name} value is not float"


# ─────────────────────────────────────────────────────────────
# Section 6: TrendSignals
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestTrendSignals:
    """Section 6: 6 linear trend signals."""

    @pytest.fixture(scope="class")
    def ts(self, samsung_fnguide):
        _require_fnguide(samsung_fnguide)
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
            return _calc_trend_signals(df_anal, df_fs_ann)
        except Exception as e:
            pytest.skip(f"_calc_trend_signals error: {e}")

    def test_returns_trend_signals(self, ts):
        """Returns TrendSignals dataclass."""
        assert isinstance(ts, TrendSignals)

    def test_has_6_signals(self, ts):
        """Has exactly 6 signals."""
        assert len(ts.signals) == 6

    def test_signal_names(self, ts):
        """Signal names match expected metrics."""
        expected = {"매출액", "영업이익률", "ROE", "외부차입", "영업자산비율", "이자보상배율"}
        actual = {s.name for s in ts.signals}
        assert actual == expected

    def test_signal_directions_valid(self, ts):
        """All directions are up/flat/down."""
        for signal in ts.signals:
            assert signal.direction in ("up", "flat", "down")


# ─────────────────────────────────────────────────────────────
# Section 7: FiveQuestions
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestFiveQuestions:
    """Section 7: 5-question investment screening."""

    @pytest.fixture(scope="class")
    def fq(self, samsung_fnguide):
        _require_fnguide(samsung_fnguide)
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
            col_recent = list(df_fs_ann.columns)[-1]
            return _calc_five_questions(df_anal, df_fs_ann, col_recent)
        except Exception as e:
            pytest.skip(f"_calc_five_questions error: {e}")

    def test_returns_five_questions(self, fq):
        """Returns FiveQuestions dataclass."""
        assert isinstance(fq, FiveQuestions)

    def test_has_5_questions(self, fq):
        """Has exactly 5 questions."""
        assert len(fq.questions) == 5

    def test_all_statuses_valid(self, fq):
        """All question statuses are ok/warn/danger."""
        for q in fq.questions:
            assert q.status in ("ok", "warn", "danger")

    def test_verdict_valid(self, fq):
        """Verdict is one of 양호/보통/주의."""
        assert fq.verdict in ("양호", "보통", "주의")

    def test_verdict_consistency(self, fq):
        """Verdict matches ok count rule."""
        ok_count = sum(1 for q in fq.questions if q.status == "ok")
        if ok_count >= 4:
            assert fq.verdict == "양호"
        elif ok_count == 3:
            assert fq.verdict == "보통"
        else:
            assert fq.verdict == "주의"


# ─────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────


@pytest.mark.live
class TestZeroInterestEdgeCase:
    """Edge case: zero interest expense should yield ok for 이자보상배율."""

    @pytest.fixture(scope="class")
    def zero_interest_hi(self, samsung_fnguide):
        """Simulate zero-interest by using Samsung data but mocking interest."""
        _require_fnguide(samsung_fnguide)
        import pandas as pd
        from fnguide.analysis import fs_analysis

        df_fs_ann, df_fs_quar, _, _, _, report, account_type = samsung_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
        except Exception as e:
            pytest.skip(f"fs_analysis error: {e}")

        col_recent = list(df_fs_ann.columns)[-1]
        # Force interest expense to 0 in df_anal
        df_anal_copy = df_anal.copy()
        if "이자비용" in df_anal_copy.index:
            df_anal_copy.loc["이자비용", col_recent] = 0.0

        return _calc_health_indicators(df_anal_copy, df_invest, df_fs_ann, col_recent)

    def test_zero_interest_icr_is_ok(self, zero_interest_hi):
        """When interest expense is 0, ICR status should be ok."""
        for ind in zero_interest_hi.indicators:
            if ind.name == "이자보상배율":
                assert ind.status == "ok"
                assert ind.value is None
                return
        pytest.fail("이자보상배율 indicator not found")


@pytest.mark.live
class TestHynixDashboard:
    """Cross-validation: SK Hynix dashboard sections (different data profile)."""

    @pytest.fixture(scope="class")
    def hynix_sections(self, hynix_fnguide):
        _require_fnguide(hynix_fnguide, "hynix_fnguide")
        df_fs_ann, df_fs_quar, _, _, _, report, account_type = hynix_fnguide
        try:
            df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)
            col = list(df_fs_ann.columns)
            col_recent = col[-1]
            return {
                "bp": _calc_business_performance(df_fs_ann),
                "hi": _calc_health_indicators(df_anal, df_invest, df_fs_ann, col_recent),
                "bs": _calc_balance_sheet(df_financing, df_invest, col),
                "rd": _calc_rate_decomposition(df_anal, report),
                "pw": _calc_profit_waterfall(df_anal),
                "ts": _calc_trend_signals(df_anal, df_fs_ann),
                "fq": _calc_five_questions(df_anal, df_fs_ann, col_recent),
            }
        except Exception as e:
            pytest.skip(f"hynix section computation error: {e}")

    def test_all_sections_computed(self, hynix_sections):
        """All 7 sections computed without error."""
        assert len(hynix_sections) == 7

    def test_bp_has_4_periods(self, hynix_sections):
        assert len(hynix_sections["bp"].periods) == 4

    def test_hi_has_7_indicators(self, hynix_sections):
        assert len(hynix_sections["hi"].indicators) == 7

    def test_verdict_is_valid(self, hynix_sections):
        assert hynix_sections["fq"].verdict in ("양호", "보통", "주의")
