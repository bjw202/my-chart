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
    _calc_activity_ratios,
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
        "매출채권및기타유동채권", "재고자산", "매입채무및기타유동채무", "매출원가",
    ]
    data = {
        "2020/12": [10000, 500, 400, 20000, 8000, 12000, 600, 0, 100, 50, 200, 150,
                    1000, 800, 900, 7000],
        "2021/12": [11000, 600, 470, 21000, 8500, 12500, 700, 0, 120, 60, 180, 140,
                    1100, 850, 950, 7500],
        "2022/12": [12000, 700, 555, 22000, 9000, 13000, 750, 0, 110, 55, 170, 130,
                    1200, 900, 1000, 8000],
        "2023/12": [13000, 800, 650, 23000, 9500, 13500, 900, 0, 100, 50, 160, 120,
                    1300, 950, 1050, 8500],
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


# ─────────────────────────────────────────────────────────────
# _calc_activity_ratios (unit) — SPEC-DASHBOARD-002
# ─────────────────────────────────────────────────────────────


class TestActivityRatiosUnit:
    @pytest.fixture()
    def ar(self):
        df_fs_ann = _make_df_fs_ann()
        return _calc_activity_ratios(df_fs_ann)

    def test_structure(self, ar):
        """REQ-17: ActivityRatios has all expected fields."""
        assert len(ar.periods) == 4
        assert len(ar.receivable_turnover) == 4
        assert len(ar.receivable_days) == 4
        assert len(ar.inventory_turnover) == 4
        assert len(ar.inventory_days) == 4
        assert len(ar.payable_turnover) == 4
        assert len(ar.payable_days) == 4
        assert len(ar.ccc) == 4
        assert len(ar.asset_turnover) == 4

    def test_first_year_none(self, ar):
        """First year has no prior data => all None."""
        assert ar.receivable_turnover[0] is None
        assert ar.receivable_days[0] is None
        assert ar.inventory_turnover[0] is None
        assert ar.inventory_days[0] is None
        assert ar.payable_turnover[0] is None
        assert ar.payable_days[0] is None
        assert ar.ccc[0] is None
        assert ar.asset_turnover[0] is None

    def test_receivable_turnover(self, ar):
        """REQ-18: receivable_turnover[1] = 11000 / avg(1000, 1100) = 11000/1050."""
        expected = round(11000 / 1050, 2)
        assert ar.receivable_turnover[1] == pytest.approx(expected)

    def test_receivable_days(self, ar):
        """REQ-18: days = round(365 / turnover)."""
        turnover = ar.receivable_turnover[1]
        assert turnover is not None
        assert ar.receivable_days[1] == round(365 / turnover)

    def test_inventory_turnover(self, ar):
        """REQ-19: inventory_turnover[1] = 7500 / avg(800, 850) = 7500/825."""
        expected = round(7500 / 825, 2)
        assert ar.inventory_turnover[1] == pytest.approx(expected)

    def test_inventory_days(self, ar):
        """REQ-19: days = round(365 / turnover)."""
        turnover = ar.inventory_turnover[1]
        assert turnover is not None
        assert ar.inventory_days[1] == round(365 / turnover)

    def test_payable_turnover(self, ar):
        """REQ-20: payable_turnover[1] = 7500 / avg(900, 950) = 7500/925."""
        expected = round(7500 / 925, 2)
        assert ar.payable_turnover[1] == pytest.approx(expected)

    def test_payable_days(self, ar):
        """REQ-20: days = round(365 / turnover)."""
        turnover = ar.payable_turnover[1]
        assert turnover is not None
        assert ar.payable_days[1] == round(365 / turnover)

    def test_ccc(self, ar):
        """REQ-21: CCC = receivable_days + inventory_days - payable_days."""
        for i in range(1, 4):
            rd = ar.receivable_days[i]
            id_ = ar.inventory_days[i]
            pd_ = ar.payable_days[i]
            if rd is not None and id_ is not None and pd_ is not None:
                assert ar.ccc[i] == rd + id_ - pd_

    def test_asset_turnover(self, ar):
        """REQ-21: asset_turnover[1] = 11000 / avg(20000, 21000) = 11000/20500."""
        expected = round(11000 / 20500, 2)
        assert ar.asset_turnover[1] == pytest.approx(expected)

    def test_missing_row(self):
        """REQ-17 edge case: missing row => None values."""
        cols = ["2020/12", "2021/12"]
        data = {
            "2020/12": [10000, 5000, 20000],
            "2021/12": [11000, 5500, 21000],
        }
        df = pd.DataFrame(data, index=["매출액", "매출원가", "자산"], columns=cols)
        ar = _calc_activity_ratios(df)
        # No receivable/inventory/payable rows => all None
        assert all(v is None for v in ar.receivable_turnover)
        assert all(v is None for v in ar.inventory_turnover)
        assert all(v is None for v in ar.payable_turnover)
        assert all(v is None for v in ar.ccc)
        # Asset turnover should still work for year 1
        assert ar.asset_turnover[0] is None
        assert ar.asset_turnover[1] is not None

    def test_samsung_verification(self):
        """SPEC section 4.3: Samsung 005930 verification (3rd year)."""
        cols = ["2020/12", "2021/12", "2022/12", "2023/12"]
        data = {
            "2020/12": [0, 0, 0, 0, 0, 0],
            "2021/12": [3022314, 1900418, 418708, 521879, 587468, 4484245],
            "2022/12": [2589355, 1803886, 432806, 516259, 535497, 4559060],
            "2023/12": [3008709, 1865623, 532460, 517549, 615226, 5145319],
        }
        rows = ["매출액", "매출원가", "매출채권및기타유동채권",
                "재고자산", "매입채무및기타유동채무", "자산"]
        df = pd.DataFrame(data, index=rows, columns=cols)
        ar = _calc_activity_ratios(df)
        # 3rd year (index 2): 2022/12
        # avg_receivable = (418708 + 432806) / 2 = 425757
        # turnover = 2589355 / 425757 = 6.08
        assert ar.receivable_turnover[2] == pytest.approx(6.08, abs=0.01)
        assert ar.receivable_days[2] == round(365 / ar.receivable_turnover[2])
        # 4th year (index 3): 2023/12 (the SPEC verification year)
        # avg_receivable = (432806 + 532460) / 2 = 482633
        # turnover = 3008709 / 482633 = 6.23
        assert ar.receivable_turnover[3] == pytest.approx(6.23, abs=0.01)
        assert ar.receivable_days[3] == round(365 / ar.receivable_turnover[3])
        # inventory: avg = (516259 + 517549) / 2 = 516904, turnover = 1865623/516904 = 3.61
        assert ar.inventory_turnover[3] == pytest.approx(3.61, abs=0.01)
        assert ar.inventory_days[3] == round(365 / ar.inventory_turnover[3])
        # payable: avg = (535497 + 615226) / 2 = 575361.5, turnover = 1865623/575361.5 = 3.24
        assert ar.payable_turnover[3] == pytest.approx(3.24, abs=0.01)
        assert ar.payable_days[3] == round(365 / ar.payable_turnover[3])
        # CCC = 59 + 101 - 113 = 47
        assert ar.ccc[3] == ar.receivable_days[3] + ar.inventory_days[3] - ar.payable_days[3]
        # asset_turnover: avg = (4559060 + 5145319) / 2 = 4852189.5
        assert ar.asset_turnover[3] == pytest.approx(0.62, abs=0.01)
