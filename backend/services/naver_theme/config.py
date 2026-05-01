# 네이버 금융 테마 분석 모듈 — 설정 상수

# 크롤링 URL
NAVER_THEME_LIST_URL = "https://finance.naver.com/sise/theme.naver?&page={n}"
NAVER_THEME_DETAIL_URL = "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}"

# HTTP 설정
CRAWL_DELAY = 0.7  # 초 (네이버 권고)
REQUEST_TIMEOUT = 10  # 초
MAX_RETRIES = 1
USER_AGENT = "KR-Stock-Screener/1.0 (naver_theme_analysis)"
RESPONSE_ENCODING = "euc-kr"  # REQ-NT-NF-002: 네이버 금융 EUC-KR 강제

# 모멘텀 계산 가중치
MOMENTUM_WEIGHT_1D = 0.6  # 1일 등락률 가중치
MOMENTUM_WEIGHT_3D = 0.4  # 3일 등락률 가중치

# 리더 스톡 스코어 가중치 (z-score 기반)
LEADER_SCORE_WEIGHTS = {
    'change_pct': 0.40,   # 등락률
    'volume': 0.30,       # 거래량
    'market_cap': 0.20,   # 시가총액
    'trade_value': 0.10,  # 거래대금
}

# 기본값
DEFAULT_TOP_N_THEMES = 20          # 기본 조회 테마 수
DEFAULT_LEADERS_PER_THEME = 3      # 테마당 리더 스톡 수
