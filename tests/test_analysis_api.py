"""FastAPI TestClient tests for GET /api/analysis/{code} endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from fnguide.dashboard import (
    BalanceSheet,
    BusinessPerformance,
    DashboardResult,
    FiveQuestion,
    FiveQuestions,
    HealthIndicator,
    HealthIndicators,
    ProfitWaterfall,
    ProfitWaterfallStep,
    RateDecomposition,
    TrendSignal,
    TrendSignals,
)


# ─────────────────────────────────────────────────────────────
# Minimal test app fixture
# ─────────────────────────────────────────────────────────────


def _make_test_app() -> FastAPI:
    """Create FastAPI app with analysis router only, no lifespan."""

    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app = FastAPI(lifespan=_noop_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from backend.routers.analysis import router as analysis_router

    app.include_router(analysis_router, prefix="/api")
    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_make_test_app())


# ─────────────────────────────────────────────────────────────
# Mock DashboardResult factory
# ─────────────────────────────────────────────────────────────


def _make_mock_dashboard(code: str = "005930") -> DashboardResult:
    """Create a minimal DashboardResult for API response testing."""
    periods_4 = ["2020/12", "2021/12", "2022/12", "2023/12"]
    zeros_4 = [0.0, 0.0, 0.0, 0.0]
    nones_4 = [None, 0.0, 0.0, 0.0]

    bp = BusinessPerformance(
        periods=periods_4,
        revenue=[100.0, 110.0, 120.0, 130.0],
        operating_profit=[10.0, 11.0, 12.0, 13.0],
        net_income=[8.0, 9.0, 10.0, 11.0],
        controlling_profit=[8.0, 9.0, 10.0, 11.0],
        operating_cf=[12.0, 13.0, 14.0, 15.0],
        gpm=[0.3, 0.31, 0.32, 0.33],
        opm=[0.10, 0.10, 0.10, 0.10],
        npm=[0.08, 0.08, 0.08, 0.08],
        yoy_revenue=nones_4,
        yoy_op=nones_4,
        yoy_ni=nones_4,
        profit_quality=[1.2, 1.18, 1.17, 1.15],
    )

    hi = HealthIndicators(indicators=[
        HealthIndicator(name="외부차입/자기자본", value=0.1, threshold="ok:<20%", status="ok"),
        HealthIndicator(name="부채비율", value=0.5, threshold="ok:<100%", status="ok"),
        HealthIndicator(name="차입금의존도", value=0.03, threshold="ok:<5%", status="ok"),
        HealthIndicator(name="순차입금의존도", value=-0.05, threshold="ok:<0", status="ok"),
        HealthIndicator(name="이자보상배율", value=None, threshold="ok:interest=0", status="ok"),
        HealthIndicator(name="영업자산비율", value=0.75, threshold="ok:>70%", status="ok"),
        HealthIndicator(name="비지배귀속비율", value=0.02, threshold="ok:<5%", status="ok"),
    ])

    bs = BalanceSheet(
        periods=periods_4,
        financing={"신용조달": zeros_4, "외부차입": zeros_4, "주주몫": [100.0]*4, "비지배주주지분": zeros_4},
        assets={"설비투자": zeros_4, "운전자산": zeros_4, "금융투자": zeros_4, "여유자금": zeros_4},
    )

    rd = RateDecomposition(
        periods=["-2y", "-1y", "recent", "예상"],
        operating_asset_return=[0.10, 0.11, 0.12, 0.12],
        non_operating_return=[0.02, 0.02, 0.02, 0.02],
        borrowing_rate=[0.03, 0.03, 0.03, 0.03],
        roe=[0.12, 0.13, 0.14, 0.14],
        weighted_avg_roe=0.13,
        ke=0.095,
        spread=0.045,
    )

    pw = ProfitWaterfall(steps=[
        ProfitWaterfallStep(name="영업이익", value=13.0),
        ProfitWaterfallStep(name="비영업이익", value=1.0),
        ProfitWaterfallStep(name="이자비용", value=0.0),
        ProfitWaterfallStep(name="세전이익", value=14.0),
        ProfitWaterfallStep(name="법인세비용", value=3.0),
        ProfitWaterfallStep(name="당기순이익", value=11.0),
        ProfitWaterfallStep(name="비지배주주순이익", value=0.0),
        ProfitWaterfallStep(name="지배주주순이익", value=11.0),
    ])

    ts = TrendSignals(signals=[
        TrendSignal(name="매출액", direction="up", description="slope: +10.0억원/년"),
        TrendSignal(name="영업이익률", direction="flat", description="slope: +0.0000/년"),
        TrendSignal(name="ROE", direction="up", description="slope: +0.0100/년"),
        TrendSignal(name="외부차입", direction="down", description="slope: -5.0억원/년"),
        TrendSignal(name="영업자산비율", direction="flat", description="slope: +0.0000/년"),
        TrendSignal(name="이자보상배율", direction="up", description="slope: +1.0000/년"),
    ])

    fq = FiveQuestions(
        questions=[
            FiveQuestion(question="영업자산이익률 > 차입이자율?", status="ok", detail="12% vs 3%"),
            FiveQuestion(question="ROE > 최소요구수익률(8%)?", status="ok", detail="14% vs 8%"),
            FiveQuestion(question="외부차입/자기자본 < 50%?", status="ok", detail="10%"),
            FiveQuestion(question="영업CF > 영업이익? (이익 품질)", status="ok", detail="115%"),
            FiveQuestion(question="3년 평균 ROE > 8%? (지속 수익성)", status="ok", detail="13%"),
        ],
        verdict="양호",
    )

    return DashboardResult(
        code=code,
        company_name="삼성전자",
        business_performance=bp,
        health_indicators=hi,
        balance_sheet=bs,
        rate_decomposition=rd,
        profit_waterfall=pw,
        trend_signals=ts,
        five_questions=fq,
    )


# ─────────────────────────────────────────────────────────────
# API tests
# ─────────────────────────────────────────────────────────────


class TestAnalysisAPISuccess:
    """Success path: mocked DashboardResult returned correctly."""

    def test_valid_code_returns_200(self, client):
        """Valid 6-digit code with mock returns 200."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        assert resp.status_code == 200

    def test_response_has_code_field(self, client):
        """Response body contains 'code' field matching request."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        data = resp.json()
        assert data["code"] == "005930"

    def test_response_has_company_name(self, client):
        """Response body contains 'company_name' field."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        data = resp.json()
        assert "company_name" in data
        assert data["company_name"] == "삼성전자"

    def test_response_has_7_sections(self, client):
        """Response body contains all 7 section keys."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        data = resp.json()
        expected_keys = {
            "business_performance", "health_indicators", "balance_sheet",
            "rate_decomposition", "profit_waterfall", "trend_signals", "five_questions",
        }
        for key in expected_keys:
            assert key in data, f"Missing section: {key}"

    def test_health_indicators_count(self, client):
        """health_indicators.indicators has 7 items."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        data = resp.json()
        assert len(data["health_indicators"]["indicators"]) == 7

    def test_profit_waterfall_steps_count(self, client):
        """profit_waterfall.steps has 8 items."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        data = resp.json()
        assert len(data["profit_waterfall"]["steps"]) == 8

    def test_five_questions_verdict(self, client):
        """five_questions.verdict is present and valid."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        data = resp.json()
        assert data["five_questions"]["verdict"] in ("양호", "보통", "주의")

    def test_trend_signals_count(self, client):
        """trend_signals.signals has 6 items."""
        mock_result = _make_mock_dashboard("005930")
        with patch("backend.routers.analysis.get_dashboard", return_value=mock_result):
            resp = client.get("/api/analysis/005930")
        data = resp.json()
        assert len(data["trend_signals"]["signals"]) == 6


class TestAnalysisAPIErrors:
    """Error path: invalid code, not found, crawling failure."""

    def test_invalid_code_5digits_returns_422(self, client):
        """5-digit code returns 422 Unprocessable Entity."""
        resp = client.get("/api/analysis/05930")
        assert resp.status_code == 422

    def test_invalid_code_letters_returns_422(self, client):
        """Alpha code returns 422."""
        resp = client.get("/api/analysis/ABCDEF")
        assert resp.status_code == 422

    def test_invalid_code_7digits_returns_422(self, client):
        """7-digit code returns 422."""
        resp = client.get("/api/analysis/0059301")
        assert resp.status_code == 422

    def test_value_error_returns_404(self, client):
        """ValueError from get_dashboard returns 404."""
        with patch(
            "backend.routers.analysis.get_dashboard",
            side_effect=ValueError("Stock not found"),
        ):
            resp = client.get("/api/analysis/999999")
        assert resp.status_code == 404

    def test_connection_error_returns_503(self, client):
        """ConnectionError returns 503."""
        with patch(
            "backend.routers.analysis.get_dashboard",
            side_effect=ConnectionError("FnGuide unreachable"),
        ):
            resp = client.get("/api/analysis/005930")
        assert resp.status_code == 503

    def test_generic_exception_returns_503(self, client):
        """Unexpected exception returns 503."""
        with patch(
            "backend.routers.analysis.get_dashboard",
            side_effect=Exception("Unexpected error"),
        ):
            resp = client.get("/api/analysis/005930")
        assert resp.status_code == 503
