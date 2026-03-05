# SPEC-DASHBOARD-001: Pure unit tests for dashboard helpers and section calculators
"""
Mock-based unit tests that do NOT require live HTTP or @pytest.mark.live.
Covers _safe_loc, _indicator_status, _calc_slope edge cases,
_calc_five_questions, _calc_trend_signals, _calc_profit_waterfall,
_calc_rate_decomposition, and _calc_balance_sheet with synthetic DataFrames.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fnguide.dashboard import (
    _calc_balance_sheet,
    _calc_five_questions,
    _calc_profit_waterfall,
    _calc_rate_decomposition,
    _calc_slope,
    _calc_trend_signals,
    _indicator_status,
    _safe_loc,
    _yoy,
)


# ─────────────────────────────────────────────────────────────
# Synthetic data factories
# ─────────────────────────────────────────────────────────────


def _make_df_anal() -> pd.DataFrame:
    """Create a synthetic df_anal DataFrame mimicking fs_analysis output."""
    cols = ["2021/12", "2022/12", "2023/12", "가중평균", "1순위", "예상"]
    rows = [
        "주주몫", "비지배주주지분", "외부차입", "영업부채",
        "영업자산", "비영업자산",
        "영업이익", "비영업이익", "이자비용", "법인세비용",
        "당기순이익", "지배주주순이익", "비지배주주순이익",
        "영업자산이익률", "비영업자산이익률", "차입이자율", "지배주주ROE",
    ]
    data = {
        "2021/12": [5000, 100, 1000, 800, 4000, 2000,
                    600, 50, 30, 150,
                    470, 450, 20,
                    0.15, 0.025, 0.03, 0.09],
        "2022/12": [5500, 120, 900, 850, 4200, 2100,
                    700, 60, 25, 180,
                    555, 530, 25,
                    0.167, 0.028, 0.028, 0.096],
        "2023/12": [6000, 130, 800, 900, 4500, 2200,
                    800, 70, 20, 200,
                    650, 620, 30,
                    0.178, 0.032, 0.025, 0.103],
        "가중평균": [0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0,
                  0, 0, 0,
                  0.165, 0.029, 0.027, 0.097],
        "1순위": [0] * 17,
        "예상": [6200, 140, 750, 950, 4700, 2300,
                850, 80, 18, 220,
                692, 660, 32,
                0.181, 0.035, 0.024, 0.106],
    }
    return pd.DataFrame(data, index=rows, columns=cols)


def _make_df_fs_ann() -> pd.DataFrame:
    """Create a synthetic df_fs_ann DataFrame."""
    cols = ["2020/12", "2021/12", "2022/12", "2023/12"]
    rows = [
        "매출액", "영업이익", "당기순이익",
        "자산", "부채", "자본",
        "영업활동으로인한현금흐름",
        "단기사채", "단기차입금", "유동금융부채", "사채", "장기차입금",
    ]
    data = {
        "2020/12": [10000, 500, 400, 20000, 8000, 12000, 600, 0, 100, 50, 200, 150],
        "2021/12": [11000, 600, 470, 21000, 8500, 12500, 700, 0, 120, 60, 180, 140],
        "2022/12": [12000, 700, 555, 22000, 9000, 13000, 750, 0, 110, 55, 170, 130],
        "2023/12": [13000, 800, 650, 23000, 9500, 13500, 900, 0, 100, 50, 160, 120],
    }
    return pd.DataFrame(data, index=rows, columns=cols)


def _make_df_financing() -> pd.DataFrame:
    """Create a synthetic df_financing DataFrame."""
    cols = ["2020/12", "2021/12", "2022/12", "2023/12"]
    rows = ["유보이익", "주주투자", "신용조달", "외부차입", "비지배주주지분"]
    data = {
        "2020/12": [3000, 1500, 800, 1000, 100],
        "2021/12": [3500, 1500, 850, 900, 110],
        "2022/12": [4000, 1500, 900, 850, 120],
        "2023/12": [4500, 1500, 950, 800, 130],
    }
    return pd.DataFrame(data, index=rows, columns=cols)


def _make_df_invest() -> pd.DataFrame:
    """Create a synthetic df_invest DataFrame."""
    cols = ["2020/12", "2021/12", "2022/12", "2023/12"]
    rows = ["설비투자", "운전자산", "금융투자", "여유자금"]
    data = {
        "2020/12": [3000, 1000, 500, 900],
        "2021/12": [3200, 1100, 550, 950],
        "2022/12": [3400, 1200, 600, 1000],
        "2023/12": [3600, 1300, 650, 1050],
    }
    return pd.DataFrame(data, index=rows, columns=cols)


# ─────────────────────────────────────────────────────────────
# _safe_loc
# ─────────────────────────────────────────────────────────────


class TestSafeLoc:
    def test_existing_row(self):
        df = pd.DataFrame({"a": [1]}, index=["row1"])
        result = _safe_loc(df, "row1")
        assert result is not None

    def test_missing_row(self):
        df = pd.DataFrame({"a": [1]}, index=["row1"])
        result = _safe_loc(df, "nonexistent")
        assert result is None


# ─────────────────────────────────────────────────────────────
# _indicator_status
# ─────────────────────────────────────────────────────────────


class TestIndicatorStatus:
    def test_lower_is_better_ok(self):
        assert _indicator_status(0.1, (0.3, 0.5), "lower_is_better") == "ok"

    def test_lower_is_better_warn(self):
        assert _indicator_status(0.35, (0.3, 0.5), "lower_is_better") == "warn"

    def test_lower_is_better_danger(self):
        assert _indicator_status(0.6, (0.3, 0.5), "lower_is_better") == "danger"

    def test_higher_is_better_ok(self):
        assert _indicator_status(0.6, (0.3, 0.5), "higher_is_better") == "ok"

    def test_higher_is_better_warn(self):
        assert _indicator_status(0.35, (0.3, 0.5), "higher_is_better") == "warn"

    def test_higher_is_better_danger(self):
        assert _indicator_status(0.2, (0.3, 0.5), "higher_is_better") == "danger"


# ─────────────────────────────────────────────────────────────
# _calc_slope edge cases
# ─────────────────────────────────────────────────────────────


class TestCalcSlopeEdge:
    def test_empty_list(self):
        assert _calc_slope([]) == 0.0

    def test_two_elements(self):
        slope = _calc_slope([1.0, 3.0])
        assert slope == pytest.approx(2.0)


# ─────────────────────────────────────────────────────────────
# _calc_five_questions (unit)
# ─────────────────────────────────────────────────────────────


class TestFiveQuestionsUnit:
    @pytest.fixture()
    def fq(self):
        df_anal = _make_df_anal()
        df_fs_ann = _make_df_fs_ann()
        return _calc_five_questions(df_anal, df_fs_ann, "2023/12")

    def test_returns_five_questions(self, fq):
        assert len(fq.questions) == 5

    def test_q1_spread_positive(self, fq):
        """OA return (17.8%) > borrow rate (2.5%) => ok."""
        assert fq.questions[0].status == "ok"

    def test_q2_roe_above_benchmark(self, fq):
        """ROE (10.3%) > 8% => ok."""
        assert fq.questions[1].status == "ok"

    def test_q3_debt_ratio(self, fq):
        """외부차입(800)/주주몫(6000) = 13.3% < 20% => ok."""
        assert fq.questions[2].status == "ok"

    def test_q4_cash_flow_quality(self, fq):
        """영업CF(900) > 영업이익(800) => ok."""
        assert fq.questions[3].status == "ok"

    def test_q5_avg_roe(self, fq):
        """3yr avg ROE = (9%+9.6%+10.3%)/3 = 9.6% > 8% => ok."""
        assert fq.questions[4].status == "ok"

    def test_verdict_all_ok(self, fq):
        """All 5 ok => verdict '양호'."""
        assert fq.verdict == "양호"

    def test_verdict_보통(self):
        """When exactly 3 ok => '보통'."""
        df_anal = _make_df_anal()
        # Fail Q1 (OA return < borrow rate) and Q2 (ROE < 8%)
        df_anal.loc["영업자산이익률", "2023/12"] = 0.02
        df_anal.loc["차입이자율", "2023/12"] = 0.05
        df_anal.loc["지배주주ROE", "2023/12"] = 0.09
        df_anal.loc["지배주주ROE", "2021/12"] = 0.09
        df_anal.loc["지배주주ROE", "2022/12"] = 0.09
        df_fs_ann = _make_df_fs_ann()
        fq = _calc_five_questions(df_anal, df_fs_ann, "2023/12")
        # Q1=fail, Q2=ok (9%>8%), Q3=ok, Q4=ok, Q5=ok (9%>8%) => 4 ok? No...
        # Actually Q1 fail => only Q2-Q5 ok = 4 ok => 양호
        # Need to fail exactly 2: Q1 and Q5
        df_anal.loc["지배주주ROE", "2023/12"] = 0.03
        df_anal.loc["지배주주ROE", "2021/12"] = 0.03
        df_anal.loc["지배주주ROE", "2022/12"] = 0.03
        # Now Q2=fail (3%<8%), Q5=fail (3%<8%), Q1=fail => 3 fail, 2 ok
        # Need exactly 3 ok: fail Q1 and Q2 only
        df_anal.loc["지배주주ROE", "2023/12"] = 0.09
        df_anal.loc["지배주주ROE", "2021/12"] = 0.09
        df_anal.loc["지배주주ROE", "2022/12"] = 0.09
        # Q1=fail, Q2=ok(9%>8%), Q3=ok, Q4=ok, Q5=ok(9%>8%) => 4 ok => 양호
        # Must also fail Q4: make OCF < op_profit
        df_fs_ann.loc["영업활동으로인한현금흐름", "2023/12"] = 100
        fq = _calc_five_questions(df_anal, df_fs_ann, "2023/12")
        ok_count = sum(1 for q in fq.questions if q.status == "ok")
        assert ok_count == 3
        assert fq.verdict == "보통"

    def test_verdict_주의(self):
        """When <= 2 ok => '주의'."""
        df_anal = _make_df_anal()
        # Fail Q1, Q2, Q5
        df_anal.loc["영업자산이익률", "2023/12"] = 0.02
        df_anal.loc["차입이자율", "2023/12"] = 0.05
        df_anal.loc["지배주주ROE", "2023/12"] = 0.01
        df_anal.loc["지배주주ROE", "2021/12"] = 0.01
        df_anal.loc["지배주주ROE", "2022/12"] = 0.01
        df_fs_ann = _make_df_fs_ann()
        # Also fail Q4 by making OCF < op_profit
        df_fs_ann.loc["영업활동으로인한현금흐름", "2023/12"] = 100
        fq = _calc_five_questions(df_anal, df_fs_ann, "2023/12")
        ok_count = sum(1 for q in fq.questions if q.status == "ok")
        assert ok_count <= 2
        assert fq.verdict == "주의"


# ─────────────────────────────────────────────────────────────
# _calc_trend_signals (unit)
# ─────────────────────────────────────────────────────────────


class TestTrendSignalsUnit:
    @pytest.fixture()
    def ts(self):
        df_anal = _make_df_anal()
        df_fs_ann = _make_df_fs_ann()
        return _calc_trend_signals(df_anal, df_fs_ann)

    def test_returns_6_signals(self, ts):
        assert len(ts.signals) == 6

    def test_revenue_up(self, ts):
        """Revenue is increasing => up."""
        rev = next(s for s in ts.signals if s.name == "매출액")
        assert rev.direction == "up"

    def test_all_directions_valid(self, ts):
        for s in ts.signals:
            assert s.direction in ("up", "flat", "down")

    def test_descriptions_contain_slope(self, ts):
        for s in ts.signals:
            assert "기울기" in s.description


# ─────────────────────────────────────────────────────────────
# _calc_profit_waterfall (unit)
# ─────────────────────────────────────────────────────────────


class TestProfitWaterfallUnit:
    @pytest.fixture()
    def pw(self):
        df_anal = _make_df_anal()
        return _calc_profit_waterfall(df_anal)

    def test_has_8_steps(self, pw):
        assert len(pw.steps) == 8

    def test_step_names(self, pw):
        expected = [
            "영업이익", "비영업이익", "이자비용",
            "세전이익", "법인세비용", "당기순이익",
            "비지배주주순이익", "지배주주순이익",
        ]
        assert [s.name for s in pw.steps] == expected

    def test_operating_profit_value(self, pw):
        assert pw.steps[0].value == pytest.approx(850.0)

    def test_pretax_calculation(self, pw):
        """세전이익 = 영업이익 + 비영업이익 - 이자비용."""
        pretax = pw.steps[0].value + pw.steps[1].value - pw.steps[2].value
        assert pw.steps[3].value == pytest.approx(pretax)


# ─────────────────────────────────────────────────────────────
# _calc_rate_decomposition (unit)
# ─────────────────────────────────────────────────────────────


class TestRateDecompositionUnit:
    @pytest.fixture()
    def rd(self):
        df_anal = _make_df_anal()
        report = {"베타": "1.2"}
        return _calc_rate_decomposition(df_anal, report)

    def test_has_4_periods(self, rd):
        assert len(rd.periods) == 4
        assert rd.periods[-1] == "예상"

    def test_roe_length(self, rd):
        assert len(rd.roe) == 4

    def test_ke_calculated(self, rd):
        """Ke = 3.5% + 1.2 * 6% = 10.7%."""
        assert rd.ke == pytest.approx(0.035 + 1.2 * 0.06)

    def test_spread_calculated(self, rd):
        """spread = expected ROE - Ke."""
        assert rd.spread == pytest.approx(0.106 - (0.035 + 1.2 * 0.06))

    def test_no_beta(self):
        """When report has no beta, ke and spread are None."""
        df_anal = _make_df_anal()
        rd = _calc_rate_decomposition(df_anal, {})
        assert rd.ke is None
        assert rd.spread is None

    def test_invalid_beta(self):
        """When beta is non-numeric, ke and spread are None."""
        df_anal = _make_df_anal()
        rd = _calc_rate_decomposition(df_anal, {"베타": "N/A"})
        assert rd.ke is None
        assert rd.spread is None


# ─────────────────────────────────────────────────────────────
# _calc_balance_sheet (unit)
# ─────────────────────────────────────────────────────────────


class TestBalanceSheetUnit:
    @pytest.fixture()
    def bs(self):
        df_financing = _make_df_financing()
        df_invest = _make_df_invest()
        col = list(df_financing.columns)
        return _calc_balance_sheet(df_financing, df_invest, col)

    def test_4_periods(self, bs):
        assert len(bs.periods) == 4

    def test_financing_keys(self, bs):
        assert set(bs.financing.keys()) == {"신용조달", "외부차입", "주주몫", "비지배주주지분"}

    def test_assets_keys(self, bs):
        assert set(bs.assets.keys()) == {"설비투자", "운전자산", "금융투자", "여유자금"}

    def test_shareholders_equity_sum(self, bs):
        """주주몫 = 유보이익 + 주주투자."""
        assert bs.financing["주주몫"][0] == pytest.approx(3000 + 1500)
        assert bs.financing["주주몫"][-1] == pytest.approx(4500 + 1500)

    def test_list_lengths(self, bs):
        n = len(bs.periods)
        for vals in bs.financing.values():
            assert len(vals) == n
        for vals in bs.assets.values():
            assert len(vals) == n
