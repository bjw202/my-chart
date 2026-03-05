"""
FnGuide 크롤링 & 재무 분석 모듈

Usage:
    from fnguide.crawler import get_fnguide, get_required_rate
    from fnguide.analysis import fs_analysis, price_analysis
"""

from .analyzer import CompResult, RateHistory, analyze_comp
from .analysis import (
    cal_rim,
    calc_weight_coeff,
    calculate_historical_rim,
    fs_analysis,
    price_analysis,
)
from .crawler import (
    get_fnguide,
    get_required_rate,
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
    "RateHistory",
    "analyze_comp",
    # crawler
    "get_fnguide",
    "get_required_rate",
    "read_consensus",
    "read_fs",
    "read_snapshot",
    # analysis
    "cal_rim",
    "calc_weight_coeff",
    "calculate_historical_rim",
    "fs_analysis",
    "price_analysis",
    # parser
    "convert_string_to_number",
    "remove_E",
    "remove_space",
    "table_parsing",
    "to_num",
]
