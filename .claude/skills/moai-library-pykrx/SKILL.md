---
name: moai-library-pykrx
description: >
  pykrx 한국 주식 시장 데이터 라이브러리 전문가. KOSPI/KOSDAQ 주가 데이터, 시가총액,
  재무 데이터, ETF 데이터 조회 시 사용. pykrx API 파라미터는 버전에 따라 자주 변경되므로
  항상 GitHub에서 최신 정보를 가져온 후 답변.
  Use when working with pykrx, KRX, KOSPI data, KOSDAQ data, 한국 주식 데이터,
  주가 데이터, stock data korea, 시가총액 조회, 종목 데이터.
license: Apache-2.0
compatibility: Designed for Claude Code
allowed-tools: Read, Grep, Glob, WebFetch, WebSearch
user-invocable: false
metadata:
  version: "1.0.0"
  category: "library"
  status: "active"
  updated: "2026-02-27"
  modularized: "false"
  tags: "pykrx, KRX, KOSPI, KOSDAQ, 한국주식, stock, korea"
  related-skills: "moai-lang-python"

# MoAI Extension: Progressive Disclosure
progressive_disclosure:
  enabled: true
  level1_tokens: 100
  level2_tokens: 5000

# MoAI Extension: Triggers
triggers:
  keywords:
    - pykrx
    - KRX
    - KOSPI data
    - KOSDAQ data
    - 한국 주식 데이터
    - 주가 데이터
    - stock data korea
    - 시가총액 조회
    - 종목 데이터
    - 한국거래소
---

## Live Data Protocol

pykrx는 KRX API와 Naver 크롤링 기반으로 동작하기 때문에 API 파라미터가 자주 변경됩니다.
pykrx 관련 질문을 받으면 반드시 아래 순서로 최신 정보를 먼저 확인합니다.

```
# 1. 최신 릴리즈 확인
WebFetch https://api.github.com/repos/sharebook-kr/pykrx/releases/latest

# 2. 알려진 버그/이슈 확인 (특히 KeyError, 빈 DataFrame 이슈)
WebFetch https://api.github.com/repos/sharebook-kr/pykrx/issues?state=open&per_page=20

# 3. API 문서 확인 (파라미터명이 바뀐 경우)
WebFetch https://raw.githubusercontent.com/sharebook-kr/pykrx/master/README.md
```

---

## 현재 버전 정보 (2026-02-27 기준)

- 최신 태그: v1.2.4
- 안정 릴리즈: v1.1.1 (2026-01-24)
- Python 지원: 3.10, 3.11, 3.12, 3.13, 3.14
- 최소 Python: 3.10

v1.1.1 주요 변경사항:
- pyproject.toml + ruff 포맷터 도입으로 CI/CD 현대화
- VCR.py로 네트워크 목 테스트 도입 (휘발성 API 파라미터 대응)
- 금 관련 정보 조회 API 추가
- ETF 정보 조회 HTTP → HTTPS 업그레이드
- Referer 헤더 수정으로 로그인 차단 문제 해결

---

## 설치

```bash
pip install pykrx
```

---

## API 빠른 참조

### 공통 규칙

- 날짜 형식: `YYYYMMDD` (문자열)
- 빈도(freq): `d` (일별), `m` (월별), `y` (연별)
- 반환 타입: 모든 함수는 `pandas.DataFrame` 반환 (단, 티커 목록 함수는 `list`)
- 수정주가 기본값: `adjusted=True`

### 주식(Stock) API

```python
from pykrx import stock

# 티커 목록 조회
tickers = stock.get_market_ticker_list("20190225", market="KOSDAQ")
# market: KOSPI / KOSDAQ / KONEX / ALL

# 종목명 조회
name = stock.get_market_ticker_name("005930")  # 삼성전자

# OHLCV (일봉/월봉/연봉)
df = stock.get_market_ohlcv("20220720", "20220810", "005930")
# 컬럼: 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률
# adjusted=False 로 미수정주가 조회 가능

# 시가총액
df = stock.get_market_cap("20220801", "20220810", "005930")
# 컬럼: 시가총액, 거래량, 거래대금, 상장주식수, 외국인보유주식수

# 특정 날짜 전체 종목 시가총액
df = stock.get_market_cap("20220801")

# 재무 데이터 (BPS, PER, PBR, EPS, DIV, DPS)
df = stock.get_market_fundamental("20220801", "20220810", "005930")

# 주가 등락률
df = stock.get_market_price_change("20220801", "20220810", market="KOSPI")
# 컬럼: 종목명, 시가, 종가, 변동폭, 등락률, 거래량, 거래대금
```

### 투자자별 매매 API

```python
# 날짜별 투자자 매매 금액
df = stock.get_market_trading_value_by_date(
    "20220801", "20220810", "005930",
    on="순매수"  # 순매수 / 매도 / 매수
)

# 날짜별 투자자 매매 수량
df = stock.get_market_trading_volume_by_date(
    "20220801", "20220810", "005930"
)

# 투자자별 순매수 상위 종목
df = stock.get_market_net_purchases_of_equities(
    "20220801", "20220810",
    market="KOSPI",
    investor="외국인"
)
# investor: 개인 / 외국인 / 기관합계 / 금융투자 / 보험 / 투신 / 은행 등
```

### 지수(Index) API

```python
# 지수 티커 목록
tickers = stock.get_index_ticker_list("20220801")
# 예시 반환값: ['1001', '1002', ...] (KOSPI=1001, KOSDAQ=2001)

# 지수명 조회
name = stock.get_index_ticker_name("1001")  # KOSPI

# 지수 OHLCV
df = stock.get_index_ohlcv("20220801", "20220810", "1001")

# 지수 구성 종목
tickers = stock.get_index_portfolio_deposit_file("1001")

# 지수 상장일 목록
df = stock.get_index_listing_date(market="KOSPI")
# market: KRX / KOSPI / KOSDAQ / theme
```

### ETF API

```python
from pykrx import stock

# ETF 티커 목록
tickers = stock.get_etf_ticker_list("20220801")

# ETF OHLCV + NAV
df = stock.get_etf_ohlcv_by_date("20220801", "20220810", "069500")
# 컬럼: NAV, 시가, 고가, 저가, 종가, 거래량, 거래대금, 기초지수

# ETF 괴리율
df = stock.get_etf_price_deviation("20220801", "20220810", "069500")

# ETF 추적오차율
df = stock.get_etf_tracking_error("20220801", "20220810", "069500")

# ETF 구성 종목 (PDF)
df = stock.get_etf_portfolio_deposit_file("069500", "20220801")
# 컬럼: 계약수, 금액, 비중
```

### 공매도(Short Selling) API

```python
# 종목별 공매도 현황 (T+2일 이후 데이터 조회 가능)
df = stock.get_shorting_status_by_date("20220801", "20220810", "005930")

# 날짜별 공매도 상위 50
df = stock.get_shorting_trade_top50("20220801", market="KOSPI")

# 공매도 잔고 상위 50
df = stock.get_shorting_balance_top50("20220801", market="KOSPI")
```

### 채권(Bond) API

```python
from pykrx import bond

# 국고채 수익률
df = bond.get_otc_treasury_yields("20220801", "20220810")
# bond_type: 국고채1년 / 국고채3년 / 국고채5년 / 국고채10년 / 국고채20년
#            국고채30년 / 국민주택1종5년 / 회사채AA- / 회사채BBB- / CD(91일)

df = bond.get_otc_treasury_yields("20220801", "20220810", bond_type="국고채3년")
```

---

## 알려진 이슈 및 워크어라운드

### 현재 오픈 이슈 (2026-02-27 기준)

**[CRITICAL] Issue #276: KRX API 구조 변경으로 서비스 다운**
- 증상: `get_index_ohlcv()` 호출 시 `KeyError: '지수명'` 발생
- 영향: 지수 데이터, 투자자 매매 데이터 조회 실패
- 원인: KRX 측 API 응답 구조 변경 (2026-02-27 19:00 KST~)
- 워크어라운드: pykrx 업데이트 대기, 혹은 직접 KRX OpenAPI 사용

**[BUG] Issue #275: 시가총액 조회 시 빈 DataFrame 반환**
- 증상: `get_market_cap("20260226", "20260227", "005930")` 빈 결과
- 영향: v1.2.3 이상
- 워크어라운드: 날짜를 단일 날짜로 조회하거나 이전 버전 사용

**[BUG] Issue #270: 수정주가 데이터 없음 (adjusted=True)**
- 증상: 장기 기간 조회 시 수정주가 데이터 누락
- 워크어라운드: `adjusted=False` 로 미수정주가 조회 후 직접 조정

### 공통 주의사항

- 공매도 데이터: T+2일 지연 (당일/전날 조회 불가)
- 외국인 보유 데이터: D-2 기준 반영 (D-1은 0 반환)
- KRX API 구조는 변경될 수 있음 → 이슈 발생 시 반드시 GitHub Issues 확인
- 빈 DataFrame 반환 시: 날짜가 거래일인지, 조회 기간이 너무 길지 않은지 확인

---

## 일반적인 사용 패턴

### 삼성전자 최근 30일 주가

```python
from pykrx import stock
from datetime import datetime, timedelta

end = datetime.today().strftime("%Y%m%d")
start = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")

df = stock.get_market_ohlcv(start, end, "005930")
print(df.tail())
```

### KOSPI 전체 종목 시가총액 (특정 날짜)

```python
from pykrx import stock

df = stock.get_market_cap("20260101")
df_sorted = df.sort_values("시가총액", ascending=False)
print(df_sorted.head(10))
```

### 재무 데이터 + 주가 결합

```python
from pykrx import stock

date = "20260101"
tickers = stock.get_market_ticker_list(date, market="KOSPI")

# 재무 데이터
fund_df = stock.get_market_fundamental(date, date)
fund_df.index.name = "ticker"

# 시가총액 데이터
cap_df = stock.get_market_cap(date)

# 결합
combined = fund_df.join(cap_df)
```

### 버전 확인

```python
import pykrx
print(pykrx.__version__)
```

---

## GitHub 참조

- 저장소: https://github.com/sharebook-kr/pykrx
- 이슈 트래커: https://github.com/sharebook-kr/pykrx/issues
- 최신 릴리즈 API: https://api.github.com/repos/sharebook-kr/pykrx/releases/latest
- README (원본): https://raw.githubusercontent.com/sharebook-kr/pykrx/master/README.md

---

## Works Well With

- moai-lang-python: Python 코드 패턴 및 pandas DataFrame 처리
- WebFetch: GitHub Issues/Releases 실시간 확인
- WebSearch: pykrx 관련 최신 커뮤니티 해결책 검색

---

Last Updated: 2026-02-27
Status: Active (v1.2.4 / stable v1.1.1)
