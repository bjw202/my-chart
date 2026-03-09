# KR Stock Screener

한국 주식시장(KOSPI/KOSDAQ) ~2,570종목을 스크리닝하는 웹 애플리케이션입니다.
기존 `my_chart` Python 라이브러리 위에 FastAPI 백엔드와 React 프론트엔드를 구축했습니다.

## 아키텍처

```
React (Vite+TS)  ->  FastAPI (Python)  ->  my_chart package  ->  SQLite
                                       ->  stock_meta table   ->  (denormalized)
```

## 빠른 시작

### 한 번에 실행 (권장)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd frontend && pnpm install && cd ..

./dev.sh   # 백엔드(8000) + 프론트엔드(5173) 동시 실행
```

### 개별 실행

**백엔드:**

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

API 문서: http://localhost:8000/docs

**프론트엔드:**

```bash
cd frontend
pnpm dev
```

개발 서버: http://localhost:5173

### KRX 세션 인증 설정 (선택사항)

pykrx 라이브러리로 KRX 데이터를 조회할 때 인증을 필요로 할 수 있습니다. 다음과 같이 설정하면 자동으로 인증됩니다:

**1. `.env` 파일 생성:**

`.env.example`을 참고하여 프로젝트 루트에 `.env` 파일을 생성합니다:

```bash
KRX_ID=your_krx_id
KRX_PW=your_krx_password
```

**2. 환경변수 설정:**

- `KRX_ID`: 한국거래소(data.krx.co.kr) 회원 ID
- `KRX_PW`: 한국거래소 회원 비밀번호

앱이 시작될 때 자동으로 다음 작업이 수행됩니다:
- pykrx webio를 인증된 세션으로 monkey-patch
- KRX에 로그인 (3단계 인증 플로우)
- 인증 실패 시 자동으로 sectormap 폴백 모드로 동작

**3. 폴백 메커니즘:**

만약 KRX 로그인이 실패하거나 환경변수가 설정되지 않으면:
1. pykrx 호출 시도 (인증 없음)
2. 실패 시 `Input/sectormap.xlsx`의 D-day 컬럼 사용
3. 폴백 데이터도 없으면 빈 DataFrame 반환

### 첫 실행

1. 백엔드와 프론트엔드를 시작합니다
2. "DB 업데이트" 버튼을 클릭합니다 (~2,570종목 수집, 5-30분 소요)
3. 필터를 적용하고 차트 그리드를 탐색합니다

## 주요 기능

- **필터 시스템**: 시가총액, 기간수익률(1D/1W/1M/3M), 기술적 패턴 빌더, RS점수, 시장, 섹터 필터
- **차트 그리드**: TradingView Lightweight Charts (2x2 / 3x3), MA 오버레이, 볼륨바, RS 값 표시, RS Line (상대강도선, 종가/KOSPI 비율), 마지막 캔들 5봉 여백
- **차트 헤더**: 종목명 · 종목코드 · 섹터그룹(대>중) · 등락률 · RS 점수 한눈에 표시
- **등락폭 측정**: 차트 위 두 지점 클릭으로 가격 등락률(%) 표시, 연속 측정 지원 (측정 완료 후 클릭만으로 즉시 새 측정 시작), 셀별 독립 동작 (아래 상세 설명 참고)
- **종목 리스트**: 섹터 그룹별 가상화 리스트, 키보드 네비게이션
- **스크롤 동기화**: 차트 그리드와 종목 리스트 간 양방향 동기화 (← → 방향키 및 버튼 클릭으로 페이지 이동, 자동 스크롤 연동)
- **관심종목**: 체크 버튼으로 관심 등록/해제, 관심 탭에서 모아보기, TradingView 내보내기
- **DB 업데이트**: SSE 기반 진행률 스트리밍, 백그라운드 일괄 업데이트, DB 기준 최종 날짜 표시

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|----------|------|
| POST | `/api/db/update` | DB 업데이트 시작 (백그라운드 태스크) |
| GET | `/api/db/status` | DB 업데이트 진행률 (SSE 스트림) |
| GET | `/api/db/last-updated` | 마지막 업데이트 시각 및 DB 기준 최종 데이터 날짜 |
| POST | `/api/screen` | 필터 적용, 섹터별 그룹 결과 반환 |
| GET | `/api/chart/{code}` | 종목 차트 데이터 (OHLCV + MA 오버레이 + RS Line) |
| GET | `/api/sectors` | 필터 드롭다운용 섹터 목록 |
| GET | `/api/analysis/{code}` | 종목 재무 분석 (S-RIM 8개 섹션 대시보드) |

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
tests/              # pytest 테스트 (374개)
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
주식 정보는 `Input/sectormap.xlsx`에서 로드합니다:
- KOSPI 주식 (~833개)
- KOSDAQ 주식 (~1,719개)
- 섹터 분류 정보

### Output 디렉토리
DB 파일은 `Output/` 디렉토리에 저장됩니다:
- `stock_data_weekly.db` - 주간 주가 데이터
- `stock_data_daily.db` - 일일 주가 데이터
- `stock_data_rs.db` - 상대강도 점수 데이터

## 등락폭 측정 도구

TradingView의 "Price Range" 측정 도구와 유사한 기능으로, 차트 위 두 지점을 클릭하여 가격 등락률(%)을 측정합니다.

### 사용법

1. 차트 헤더의 `%` 버튼 클릭 또는 `M` 키 → 측정 모드 진입 (커서 crosshair)
2. 차트 위 첫 번째 클릭 → 시작점 고정
3. 마우스 이동 → 실시간 미리보기 (연결 영역 + 라벨)
4. 두 번째 클릭 → 측정 결과 고정 (locked)
5. 측정 결과 상태에서 클릭 → 해당 위치를 시작점으로 즉시 새 측정 시작 (연속 측정)
6. `ESC` / `%` 버튼 재클릭 / `M` 키 → 측정 해제 (idle로 복귀)

### 표시 형식

- 양수: `+20.00%` (초록)
- 음수: `-13.26%` (빨강)

### 상태 머신

```
IDLE ──[% / M]──> MEASURING ──[클릭(시작점)]──> MEASURING* ──[클릭(끝점)]──> LOCKED
IDLE <──[% / M / ESC]── MEASURING
LOCKED ──[클릭]──> MEASURING* (연속 측정: 클릭 위치가 새 시작점)
LOCKED ──[% / M / ESC]──> IDLE
```

### 기술 구현

- `usePriceRangeMeasure` hook: 상태 머신 + lightweight-charts 이벤트 구독
- `PriceRangeOverlay` 컴포넌트: HTML div 기반 오버레이 (pointer-events: none)
- 데이터 좌표(price, time)로 저장, 매 렌더 시 픽셀 좌표로 변환
- 각 차트 셀이 독립적으로 동작 (Context API 불필요)

## 개발 참고

- 단일 프로세스 uvicorn (1 worker) - SQLite 스레드 안전성
- Registry lifespan event에서 사전 초기화
- 인덱싱된 `stock_meta` 테이블에서 파라미터화 SQL 필터링
- 차트 인스턴스 페이지 변경 시 destroy (메모리 누수 방지)

## 라이선스

Private - 로컬 전용.
