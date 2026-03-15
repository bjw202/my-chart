# SPEC-KRX-AUTH-001: 구현 계획

## 추적성

- SPEC: SPEC-KRX-AUTH-001
- 참조: spec.md, acceptance.md

---

## 마일스톤

### Primary Goal: 핵심 세션 모듈 + 안전 유틸리티

**범위:** `krx_session.py` 신규 생성 및 `config.py` 수정

| 작업 | 파일 | 설명 |
|------|------|------|
| T-01 | `my_chart/krx_session.py` | KRX 세션 관리 모듈 신규 생성 |
| T-02 | `my_chart/config.py` | python-dotenv 로딩 + `init_session()` 호출 추가 |
| T-03 | `.env.example` | KRX_ID, KRX_PW 템플릿 파일 생성 |
| T-04 | `pyproject.toml` 또는 `requirements.txt` | `python-dotenv` 의존성 추가 |

**완료 기준:**
- `krx_session.py`가 독립적으로 동작 (로그인, 패치, 폴백)
- `.env` 미설정 시에도 애플리케이션 기동 가능
- 단위 테스트 통과

### Secondary Goal: 호출 지점 통합

**범위:** 기존 pykrx 직접 호출을 `get_market_cap_safe()`로 교체

| 작업 | 파일 | 변경 수준 |
|------|------|-----------|
| T-05 | `my_chart/registry.py` | `get_market_cap()` 1곳 교체 |
| T-06 | `my_chart/screening/momentum.py` | `get_market_cap()` 1곳 교체 |
| T-07 | `my_chart/screening/high_stocks.py` | `get_market_cap()` 1곳 교체 |
| T-08 | `my_chart/charting/bulk.py` | `get_market_cap()` 4곳 교체 |
| T-09 | `my_chart/export/tradingview.py` | `get_market_cap()` 3곳 교체 |
| T-10 | `my_chart/db/queries.py` | `get_market_cap()` 1곳 교체 |
| T-11 | `my_chart/analysis/market.py` | `get_market_cap()` 2곳 + `get_market_cap_by_date()` 1곳 교체 |

**완료 기준:**
- `from pykrx import stock` 직접 import가 해당 파일들에서 제거됨
- 모든 시가총액 조회가 `get_market_cap_safe()`를 경유함

### Final Goal: backend 서비스 통합

**범위:** `meta_service.py` 세션 혜택 적용

| 작업 | 파일 | 변경 수준 |
|------|------|-----------|
| T-12 | `backend/services/meta_service.py` | 기존 폴백 로직 보존, `krx_session` 세션 패치 혜택만 수신 |

**완료 기준:**
- 기존 try/except + sectormap 폴백 동작이 그대로 유지됨
- 인증된 세션을 통해 pykrx 호출 성공률 향상

### Optional Goal: 세션 재인증 및 고급 처리

| 작업 | 설명 |
|------|------|
| T-13 | 세션 만료 감지 + 자동 재인증 로직 |
| T-14 | `get_market_cap_by_date_safe()` 유틸리티 (market.py 전용) |
| T-15 | KRX 인증 상태 헬스체크 엔드포인트 (FastAPI) |

---

## 기술 접근

### 1. Monkey-Patch 전략

pykrx는 내부적으로 `webio.Post.read`와 `webio.Get.read` 메서드를 통해 HTTP 요청을 수행한다. 이를 인증된 `requests.Session`을 사용하도록 교체한다.

- **적용 시점**: `config.py` import 시 (애플리케이션 시작)
- **적용 방식**: `webio.Post.read = _session_post_read` / `webio.Get.read = _session_get_read`
- **가드**: `_patched` 플래그로 중복 적용 방지

### 2. 폴백 전략 (3단계)

1. **1차**: pykrx `stock.get_market_cap(date)` (인증 세션)
2. **2차**: `sectormap.xlsx` D-day 컬럼 (억원 단위)
3. **3차**: 빈 DataFrame 반환 (호출자에서 graceful 처리)

### 3. 환경변수 로딩 전략

- `python-dotenv`의 `load_dotenv()`를 `config.py` 상단에서 호출
- `os.getenv("KRX_ID")`, `os.getenv("KRX_PW")`로 읽기
- 값이 없으면 로그인 스킵 (경고 로그)
- 기존 `config.py`의 matplotlib 설정, 경로 상수 등에는 영향 없음

### 4. `get_market_cap_safe()` 반환 타입

기존 `stock.get_market_cap()` 반환값과 동일한 `pd.DataFrame` (인덱스: 종목코드, 컬럼: 시가총액 등)을 유지하여 호출자 변경을 최소화한다. 폴백 시에는 호환되는 구조의 DataFrame을 구성한다.

### 5. `analysis/market.py` 특수 처리

`market.py`의 `stock.get_market_cap_by_date()` 호출은 단건 날짜 조회가 아닌 기간 조회이므로, `get_market_cap_safe()`와 별도로 처리가 필요할 수 있다. 이 호출도 인증 세션의 혜택을 자동으로 받으므로 (monkey-patch 적용), 별도 래퍼 없이도 동작한다. 단, 실패 시 폴백이 필요하면 Optional Goal(T-14)에서 처리한다.

---

## 아키텍처 설계 방향

### 단일 진입점 원칙

모든 pykrx 세션 관련 로직은 `my_chart/krx_session.py` 한 곳에서 관리한다.

### Import 의존성 방향

```
config.py  -->  krx_session.py  -->  pykrx.webio (monkey-patch)
                     |
                     +--> sectormap.xlsx (폴백)
                     |
                     v
           각 모듈에서 get_market_cap_safe() 호출
```

### 기존 코드 변경 최소화

- `from pykrx import stock` -> `from my_chart.krx_session import get_market_cap_safe` 교체
- `stock.get_market_cap(date)` -> `get_market_cap_safe(date)` 교체
- 반환 타입이 동일하므로 후속 코드 변경 불필요

---

## 위험 및 대응

| 위험 | 확률 | 대응 |
|------|------|------|
| pykrx webio 구조 변경 | 낮음 | 버전 핀닝, patch_pykrx_session()에서 ImportError 처리 |
| KRX 로그인 API 변경 | 중간 | login_krx() 실패 시 폴백으로 자동 전환, 로그 모니터링 |
| config.py import 순서 충돌 | 낮음 | dotenv 로딩을 최상단에 배치, matplotlib 설정 이후 세션 초기화 |
| 환형 import (config -> krx_session -> config) | 낮음 | krx_session이 config를 직접 import하지 않도록 설계 (SECTORMAP_PATH를 파라미터로 전달) |
