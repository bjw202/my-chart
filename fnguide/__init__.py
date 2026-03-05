"""
FnGuide 크롤링 & 재무 분석 모듈

Usage:
    from fnguide.crawler import get_fnguide
    from fnguide.analysis import fs_analysis
"""

from .analyzer import CompResult, ProfitTrend, RateHistory, analyze_comp
from .analysis import (
    calc_weight_coeff,
    fs_analysis,
)
from .dashboard import (
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
    analyze_dashboard,
)
from .crawler import (
    get_fnguide,
    read_consensus,
    read_fs,
    read_snapshot,
)
from .parser import (
    convert_string_to_number,
    remove_E,
    remove_space,
    table_parsing,
    to_num,
)

__all__ = [
    # analyzer
    "CompResult",
    "ProfitTrend",
    "RateHistory",
    "analyze_comp",
    # crawler
    "get_fnguide",
    "read_consensus",
    "read_fs",
    "read_snapshot",
    # analysis
    "calc_weight_coeff",
    "fs_analysis",
    # dashboard
    "BalanceSheet",
    "BusinessPerformance",
    "DashboardResult",
    "FiveQuestion",
    "FiveQuestions",
    "HealthIndicator",
    "HealthIndicators",
    "ProfitWaterfall",
    "ProfitWaterfallStep",
    "RateDecomposition",
    "TrendSignal",
    "TrendSignals",
    "analyze_dashboard",
    # parser
    "convert_string_to_number",
    "remove_E",
    "remove_space",
    "table_parsing",
    "to_num",
]
