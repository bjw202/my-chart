# my_chart - 한국 주식시장 분석 도구

한국 주식시장 데이터를 수집, 분석, 시각화하는 포괄적인 Python 라이브러리입니다.

## 주요 기능

- **실시간 주가 데이터**: 네이버 파이낸스 API를 통한 주가 정보 수집
- **기술 지표 계산**: MACD, RSI, 스토캐스틱, 볼린저밴드 등 주요 지표 자동 계산
- **주식 스크리닝**: 모멘텀, 일일 변동, 고주가주 등의 필터링 기능
- **차트 생성**: mplfinance를 이용한 캔들스틱 차트 생성
- **상대강도 지수(RS)**: 개별 주식의 상대강도 점수 계산 및 DB 관리
- **데이터 내보내기**: PowerPoint(PPTX), Excel, TradingView 형식 지원
- **병렬 데이터베이스 처리**: ThreadPoolExecutor를 이용한 빠른 DB 생성 (10개 스레드)
- **SQLite 최적화**: WAL 모드, 배치 삽입, UPSERT 패턴으로 높은 성능

## 설치

### 필수 요구사항

- Python 3.13+
- pip

### 설치 방법

```bash
pip install -e .
```

또는 특정 의존성과 함께 설치:

```bash
pip install -r requirements.txt
```

## 빠른 시작

### 1. 기본 가져오기

```python
from my_chart import price_naver, generate_price_db
```

### 2. 주가 데이터 조회

```python
import pandas as pd
from my_chart import price_naver

# 삼성전자(005930) 2024년 1월 1일부터의 일일 주가 조회
df = price_naver("005930", "20240101")
print(df.head())
```

### 3. 데이터베이스 생성

```python
from my_chart import generate_price_db

# 주간 주가 데이터베이스 생성
# 50개 주식 병렬 처리 (약 0.8초 소요)
generate_price_db()
```

### 4. 기술 지표 계산

```python
from my_chart import price_naver_rs

# 주가 데이터에 기술 지표 추가
df = price_naver("005930", "20240101")
df_with_indicators = price_naver_rs(df)
print(df_with_indicators[['Date', 'Close', 'MA20', 'MA60', 'MACD']].head())
```

## 프로젝트 구조

```
my_chart/
├── price.py           # 네이버 파이낸스 API 데이터 수집
├── registry.py        # 주식 메타데이터 (sectormap.xlsx 기반)
├── indicators.py      # 기술 지표 계산 (MACD, RSI, 등)
├── db/
│   ├── weekly.py      # 주간 주가 DB 생성 (병렬)
│   ├── daily.py       # 일일 주가 DB 생성 (병렬)
│   └── queries.py     # DB 조회 함수
├── screening.py       # 주식 스크리닝 필터
├── charting.py        # 캔들스틱 차트 생성
├── analysis.py        # 시장 분석 및 리포팅
├── export.py          # PPTX/Excel 내보내기
└── config.py          # 설정 및 경로 관리
```

## 중요한 설정

### Input 디렉토리
프로젝트는 주식 정보를 `Input/sectormap.xlsx`에서 읽습니다. 이 파일에는 다음이 포함되어야 합니다:
- KOSPI 주식 목록 (약 833개)
- KOSDAQ 주식 목록 (약 1,719개)
- 각 주식의 섹터 분류 정보

### Output 디렉토리
생성된 데이터베이스 파일들은 자동으로 `Output/` 디렉토리에 저장됩니다:
- `stock_data_weekly.db` - 주간 주가 데이터
- `stock_data_daily.db` - 일일 주가 데이터
- `stock_data_rs.db` - 상대강도 점수 데이터
- `.cache/` - 임시 캐시 디렉토리

## 공개 API

주요 공개 함수들:

| 함수 | 설명 |
|------|------|
| `price_naver(code, start)` | 네이버 파이낸스에서 주가 데이터 조회 |
| `price_naver_rs(df)` | 주가 데이터에 기술 지표 추가 |
| `get_stock_registry()` | 전체 주식 목록 로드 |
| `generate_price_db()` | 주간 주가 DB 생성 (병렬) |
| `price_daily_db()` | 일일 주가 DB 생성 (병렬) |
| `generate_rs_db()` | 상대강도 점수 DB 생성 |

모든 공개 함수는 `my_chart/__init__.py`에서 export됩니다.

## 기술 스택

- **데이터 처리**: pandas, numpy
- **시각화**: mplfinance, matplotlib, pillow
- **데이터 저장**: SQLite (별도 DB 서버 불필요)
- **주식 데이터**: 네이버 파이낸스 API, sectormap.xlsx
- **병렬 처리**: concurrent.futures.ThreadPoolExecutor
- **내보내기**: python-pptx, openpyxl, xlsxwriter

## 플랫폼별 폰트

차트는 각 플랫폼에서 자동으로 적절한 한글 폰트를 선택합니다:
- **macOS**: AppleGothic
- **Windows**: Malgun Gothic
- **Linux**: DejaVu Sans (한글 미지원 - 수동 설정 필요)

## 알려진 이슈

- **pykrx 라이브러리**: 2024년 이후 KRX API가 응답하지 않아 더 이상 사용되지 않습니다. 모든 주식 정보는 sectormap.xlsx에서 로드됩니다.

## 라이선스

MIT License

## 기여

이슈, 풀 리퀘스트, 제안을 환영합니다.

## 개발 정보

- **언어**: Python 3.13
- **구조**: 모듈식 라이브러리 (7개 함수형 서브모듈)
- **테스트**: 8개의 통합 테스트 (SPEC-001 데이터 파이프라인 검증)
- **최신 버전**: 2026-02-27

## 추가 문서

자세한 정보는 `.moai/project/` 디렉토리의 문서를 참고하세요:
- `product.md` - 제품 개요 및 기능
- `structure.md` - 파일 구조 및 아키텍처
- `tech.md` - 기술 스택 및 상세 정보
