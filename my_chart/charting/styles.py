"""Shared chart styles for mplfinance."""

from __future__ import annotations

import mplfinance as mpf

from my_chart.config import FONT_NAME


def get_font_name() -> str:
    """Return the configured font name."""
    return FONT_NAME


def get_korean_market_style():
    """Return Korean market mplfinance style (red=up, blue=down)."""
    mc = mpf.make_marketcolors(up="r", down="b", inherit=True)
    return mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle="--",
        rc={"date.autoformatter.day": "%Y-%m-%d", "font.size": 10},
    )
