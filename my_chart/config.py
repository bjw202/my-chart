"""Constants and configuration for my_chart package."""

from __future__ import annotations

import platform
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm

# Font configuration
if platform.system() == "Darwin":
    FONT_NAME = "AppleGothic"
elif platform.system() == "Windows":
    _font_location = "C:/Windows/Fonts/malgun.ttf"
    FONT_NAME = fm.FontProperties(fname=_font_location).get_name()
else:
    FONT_NAME = "DejaVu Sans"

matplotlib.rc("font", family=FONT_NAME)
matplotlib.rcParams["axes.unicode_minus"] = False

# Reference stock used for date lookups in DB
REFERENCE_STOCK = "삼성전자"

# Paths
INPUT_DIR = Path(__file__).parent.parent / "Input"
OUTPUT_DIR = Path(__file__).parent.parent / "Output"
SECTORMAP_PATH = INPUT_DIR / "sectormap.xlsx"

# Ensure Output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Database names (stored in Output/)
DEFAULT_DB_WEEKLY = str(OUTPUT_DIR / "stock_data_weekly")
DEFAULT_DB_DAILY = str(OUTPUT_DIR / "stock_data_daily")

# PPTX dimensions (16:9 widescreen)
from pptx.util import Cm

PPTX_WIDTH = Cm(33.867)
PPTX_HEIGHT = Cm(19.05)

# Cache directory (auto-created)
CACHE_DIR = Path("./.cache/")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Minimum close price filter
MIN_CLOSE_PRICE = 5000
