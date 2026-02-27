# KR Stock Screener

한국 주식시장(KOSPI/KOSDAQ) ~2,570종목을 스크리닝하는 웹 애플리케이션입니다.
기존 `my_chart` Python 라이브러리 위에 FastAPI 백엔드와 React 프론트엔드를 구축했습니다.

## 아키텍처

```
React (Vite+TS)  ->  FastAPI (Python)  ->  my_chart package  ->  SQLite
                                       ->  stock_meta table   ->  (denormalized)
```

## 빠른 시작

### 백엔드

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn backend.main:app --reload --port 8000
```

API 문서: http://localhost:8000/docs

### 프론트엔드

```bash
cd frontend
pnpm install
pnpm dev
```

개발 서버: http://localhost:5173

### 첫 실행

1. 백엔드와 프론트엔드를 시작합니다
2. "DB 업데이트" 버튼을 클릭합니다 (~2,570종목 수집, 5-30분 소요)
3. 필터를 적용하고 차트 그리드를 탐색합니다

## 주요 기능

- **필터 시스템**: 시가총액, 기간수익률(1D/1W/1M/3M), 기술적 패턴 빌더, RS점수, 시장, 섹터 필터
- **차트 그리드**: TradingView Lightweight Charts (2x2 / 3x3), MA 오버레이, 볼륨바
- **종목 리스트**: 섹터 그룹별 가상화 리스트, 키보드 네비게이션
- **스크롤 동기화**: 차트 그리드와 종목 리스트 간 양방향 동기화
- **DB 업데이트**: SSE 기반 진행률 스트리밍, 백그라운드 일괄 업데이트

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|----------|------|
| POST | `/api/db/update` | DB 업데이트 시작 (백그라운드 태스크) |
| GET | `/api/db/status` | DB 업데이트 진행률 (SSE 스트림) |
| GET | `/api/db/last-updated` | 마지막 업데이트 시각 |
| POST | `/api/screen` | 필터 적용, 섹터별 그룹 결과 반환 |
| GET | `/api/chart/{code}` | 종목 차트 데이터 (OHLCV + MA 오버레이) |
| GET | `/api/sectors` | 필터 드롭다운용 섹터 목록 |

## 필터 유형

- **시가총액**: 최소 기준 (억원)
- **기간수익률**: CHG_1D, CHG_1W, CHG_1M, CHG_3M 최소 %
- **기술적 패턴**: 최대 3개 조건, AND/OR (`Close <= EMA10 x 1.05`)
- **RS점수**: 최소 RS_12M_Rating
- **시장**: KOSPI / KOSDAQ 체크박스
- **섹터**: 산업명(대) 멀티셀렉트

## 기술 스택

- **백엔드**: Python 3.13, FastAPI, uvicorn, sse-starlette
- **프론트엔드**: React 19, TypeScript, Vite, TradingView Lightweight Charts, react-window
- **데이터베이스**: SQLite (WAL mode)
- **데이터 소스**: Naver Finance API, pykrx (한국거래소)

## 프로젝트 구조

```
my_chart/           # 기존 Python 데이터 라이브러리 (가격, 지표, DB)
backend/            # FastAPI API 레이어 (routers, schemas, services)
frontend/           # React + Vite + TypeScript UI
tests/              # pytest 테스트 (166개)
```

## 테스트

```bash
pytest tests/ -q
```

## my_chart 라이브러리

기존 `my_chart` 패키지가 백엔드 데이터 레이어를 담당합니다:

| 함수 | 모듈 | 웹 서비스 역할 |
|------|------|--------------|
| `price_naver()` | price.py | `/api/chart/{code}` 데이터 소스 |
| `get_stock_registry()` | registry.py | `/api/sectors`, 종목 메타데이터 |
| `generate_price_db()` | db/weekly.py | `/api/db/update` 배치 작업 |
| `price_daily_db()` | db/daily.py | `/api/db/update` 일일 배치 |
| `load_price_with_rs()` | db/queries.py | 필터링 데이터 소스 |

## 설정

### Input 디렉토리
주식 정보는 `Input/sectormap_original.xlsx`에서 로드합니다:
- KOSPI 주식 (~833개)
- KOSDAQ 주식 (~1,719개)
- 섹터 분류 정보

### Output 디렉토리
DB 파일은 `Output/` 디렉토리에 저장됩니다:
- `stock_data_weekly.db` - 주간 주가 데이터
- `stock_data_daily.db` - 일일 주가 데이터
- `stock_data_rs.db` - 상대강도 점수 데이터

## 개발 참고

- 단일 프로세스 uvicorn (1 worker) - SQLite 스레드 안전성
- Registry lifespan event에서 사전 초기화
- 인덱싱된 `stock_meta` 테이블에서 파라미터화 SQL 필터링
- 차트 인스턴스 페이지 변경 시 destroy (메모리 누수 방지)

## 라이선스

Private - 로컬 전용.
