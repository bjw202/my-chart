"""V2 모바일 endpoint 상수. URL 변경 시 이 파일만 수정 (REQ-NT2-NF-005)."""

NAVER_MOBILE_BASE_URL = "https://m.stock.naver.com"
NAVER_MOBILE_FRONT_API_PREFIX = "/front-api"
LIST_ENDPOINT_PATH = "/stock/sectors/all"
DETAIL_ENDPOINT_PATH = "/domestic/sector/item/list"

# 라이브 PoC 검증 헤더 (research.md §1.3)
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DEFAULT_REFERER = "https://m.stock.naver.com/domestic/home/theme/daily"
ACCEPT_HEADER = "application/json"

# 매너 호출 정책 (REQ-NT2-NF-001)
REQUEST_SLEEP_SECONDS = 0.7
REQUEST_TIMEOUT_SECONDS = 10
RETRY_BACKOFF_SECONDS = 1.0  # 5xx retry 전 sleep

# 페이지네이션 (research.md §1.2 — 서버 검증 max=50)
LIST_PAGE_SIZE = 50
DETAIL_PAGE_SIZE = 50
LIST_MAX_PAGES = 10  # 264/50≈6 + safety margin

# 응답 시간 목표 (REQ-NT2-NF-004)
SNAPSHOT_TIMEOUT_BUDGET = 30
QUICK_TIMEOUT_BUDGET = 10

# metadata['data_source'] 값
DATA_SOURCE = "naver_mobile_v2"
