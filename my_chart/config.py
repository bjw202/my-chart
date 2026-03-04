"""Constants and configuration for my_chart package."""

from __future__ import annotations

import platform
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm

# .env 파일 로드 (KRX_ID, KRX_PW 등 환경변수)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv 미설치 환경에서도 정상 동작

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
SECTORMAP_PATH = INPUT_DIR / "sectormap_original.xlsx"

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

# KRX 세션 초기화 (환경변수에서 인증 정보를 읽어 pykrx를 monkey-patch하고 로그인)
try:
    from my_chart.krx_session import init_session

    init_session()
except Exception as _krx_exc:
    import logging as _logging

    _logging.getLogger(__name__).warning("KRX 세션 초기화 실패: %s", _krx_exc)
