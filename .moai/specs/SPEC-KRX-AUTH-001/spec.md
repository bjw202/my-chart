# SPEC-KRX-AUTH-001: KRX 세션 기반 인증 추가 (pykrx 우회)

## 메타데이터

| 항목 | 값 |
|------|-----|
| SPEC ID | SPEC-KRX-AUTH-001 |
| 제목 | KRX Session-Based Authentication for pykrx |
| 생성일 | 2026-03-04 |
| 상태 | Planned |
| 우선순위 | High |
| 담당 | expert-backend |
| 라이프사이클 | spec-first |

---

## 요약

2026년 2월 27일부로 한국거래소(KRX)가 API 접근에 세션 기반 인증을 요구하도록 변경했다. 이로 인해 pykrx의 `stock.get_market_cap()` 호출이 인증 없이는 실패한다. 본 SPEC은 중앙화된 KRX 세션 관리 모듈을 추가하고, 모든 pykrx 호출 경로에 일관된 인증 + 폴백(fallback) 전략을 적용하는 것을 목표로 한다.

---

## 문제 정의

### 현재 상태

- pykrx `stock.get_market_cap(date)` 호출이 프로젝트 전반 **8개 파일, 14개 이상의 호출 지점**에 분산되어 있다.
- `backend/services/meta_service.py`만 유일하게 try/except + sectormap Excel 폴백을 갖추고 있다.
- 나머지 7개 파일은 에러 처리가 없어 KRX 인증 변경 이후 즉시 장애가 발생한다.

### 영향 받는 파일

| 파일 | 호출 패턴 | 에러 처리 |
|------|-----------|-----------|
| `my_chart/registry.py` | `stock.get_market_cap(day)` | 없음 |
| `my_chart/analysis/market.py` | `stock.get_market_cap(day)` (루프 내 다수), `stock.get_market_cap_by_date()` | 없음 |
| `my_chart/screening/momentum.py` | `stock.get_market_cap(date)` | 없음 |
| `my_chart/screening/high_stocks.py` | `stock.get_market_cap(end)` | 없음 |
| `my_chart/charting/bulk.py` | `stock.get_market_cap(day)` (3+개 함수) | 없음 |
| `my_chart/export/tradingview.py` | `stock.get_market_cap(day)` (3개 함수) | 없음 |
| `my_chart/db/queries.py` | `stock.get_market_cap(date)` | 없음 |
| `backend/services/meta_service.py` | `pykrx_stock.get_market_cap(pykrx_date)` | try/except + sectormap 폴백 |

### 근본 원인

KRX가 2026-02-27에 data.krx.co.kr API를 세션 인증 필수로 전환. pykrx 내부의 `webio.Post.read` / `webio.Get.read` 메서드가 인증 쿠키 없는 requests를 보내 실패한다.

---

## 환경 (Environment)

- **Python**: 3.11+ (프로젝트 기준)
- **pykrx**: >= 1.0.30
- **OS**: macOS (1차), Windows/Linux (호환)
- **배포**: 로컬 전용 (localhost)
- **데이터베이스**: SQLite (weekly_price.db, daily_price.db)
- **기존 폴백 데이터**: `Input/sectormap.xlsx` (D-day 컬럼 = 시가총액 억원 단위)

---

## 가정 (Assumptions)

1. KRX 회원 계정(data.krx.co.kr)이 사전에 생성되어 있다.
2. pykrx의 내부 구조(`webio.Post`, `webio.Get`)는 단기간 내 변경되지 않는다.
3. KRX 세션 쿠키는 프로세스 수명 동안 유효하다 (장시간 유지 불필요).
4. `.env` 파일에 KRX_ID, KRX_PW를 저장하는 것이 보안 요구사항을 충족한다 (로컬 전용 앱).
5. sectormap.xlsx의 D-day 컬럼이 시가총액 폴백 데이터로 사용 가능하다.

---

## 요구사항 (Requirements)

### 기능 요구사항

#### FR-01: 중앙 세션 관리 모듈 (Ubiquitous)

시스템은 **항상** `my_chart/krx_session.py`를 통해 KRX 세션 인증을 관리해야 한다.

- `requests.Session`을 단일 인스턴스로 생성한다.
- pykrx `webio.Post.read`와 `webio.Get.read`를 monkey-patch하여 인증된 세션을 사용하도록 한다.
- monkey-patch는 프로세스당 1회만 적용한다 (멱등성 보장).

#### FR-02: KRX 로그인 함수 (Event-Driven)

**WHEN** `login_krx(login_id, login_pw)`가 호출되면 **THEN** KRX data.krx.co.kr에 세션 인증을 수행해야 한다.

- 로그인 페이지(`MDCCOMS001.cmd`) 접근 -> JSP 페이지 접근 -> 로그인 POST(`MDCCOMS001D1.cmd`)의 3단계를 수행한다.
- 중복 로그인 에러(`CD011`)는 `skipDup=Y` 파라미터로 자동 재시도한다.
- 성공 코드(`CD001`) 반환 시 `True`, 실패 시 `False`를 리턴한다.

#### FR-03: 환경변수 기반 인증 정보 로드 (Event-Driven)

**WHEN** 애플리케이션이 시작되면 **THEN** `.env` 파일에서 `KRX_ID`와 `KRX_PW`를 로드해야 한다.

- `python-dotenv`를 사용하여 프로젝트 루트의 `.env` 파일을 읽는다.
- `my_chart/config.py`에서 dotenv 로딩을 수행한다.
- 환경변수가 설정되어 있으면 자동으로 `login_krx()`를 호출하여 세션을 초기화한다.

#### FR-04: 안전한 시가총액 조회 유틸리티 (Event-Driven)

**WHEN** `get_market_cap_safe(date_str)`이 호출되면 **THEN** 다음 순서로 시가총액을 조회해야 한다:

1. pykrx `stock.get_market_cap(date_str)` 시도 (인증 세션 사용)
2. 실패 시 `sectormap.xlsx`의 D-day 컬럼으로 폴백
3. 폴백 데이터도 없으면 빈 DataFrame 반환

#### FR-05: 기존 호출 지점 통합 (Event-Driven)

**WHEN** pykrx `stock.get_market_cap()`이 필요한 상황이면 **THEN** `get_market_cap_safe()`를 통해 호출해야 한다.

- `my_chart/registry.py`, `analysis/market.py`, `screening/momentum.py`, `screening/high_stocks.py`, `charting/bulk.py`, `export/tradingview.py`, `db/queries.py`의 직접 호출을 `get_market_cap_safe()`로 교체한다.
- `backend/services/meta_service.py`는 기존 폴백 로직을 유지하되, 세션 인증의 혜택을 받도록 세션 초기화만 추가한다.

#### FR-06: .gitignore 갱신 (Ubiquitous)

시스템은 **항상** `.env` 파일이 Git에 커밋되지 않도록 해야 한다.

- `.gitignore`에 `.env` 패턴이 이미 포함되어 있음을 확인한다 (현재 확인 완료: 포함됨).

### 비기능 요구사항

#### NFR-01: 세션 재사용성 (State-Driven)

**IF** KRX 세션이 이미 인증된 상태이면 **THEN** 추가 로그인 없이 기존 세션을 재사용해야 한다.

- 전역 `requests.Session` 인스턴스를 모든 pykrx 호출에서 공유한다.

#### NFR-02: 인증 실패 내결함성 (Unwanted)

시스템은 KRX 인증 실패로 인해 전체 애플리케이션이 **중단되지 않아야 한다**.

- 인증 실패 시 경고 로그를 출력하고 pykrx 호출은 폴백으로 처리한다.
- 세션 미인증 상태에서도 앱 기동이 가능해야 한다.

#### NFR-03: Monkey-Patch 안전성 (Unwanted)

시스템은 monkey-patch를 **중복 적용하지 않아야 한다**.

- 이미 패치된 상태인지 확인하는 가드를 포함한다.

#### NFR-04: 로깅 (Ubiquitous)

시스템은 **항상** KRX 인증 시도, 성공/실패, 폴백 전환을 로깅해야 한다.

- `logging` 모듈을 사용한다.
- 민감 정보(비밀번호)는 로그에 포함하지 않는다.

---

## 명세 (Specifications)

### 아키텍처 설계

```
[.env] -- KRX_ID, KRX_PW
   |
   v
[my_chart/config.py] -- dotenv 로딩 + 자동 세션 초기화
   |
   v
[my_chart/krx_session.py] -- 중앙 세션 관리
   |  - requests.Session 싱글턴
   |  - login_krx()
   |  - monkey-patch webio
   |  - get_market_cap_safe()
   |
   v
[pykrx.webio.Post/Get] -- monkey-patched read()
   |
   +---> registry.py
   +---> analysis/market.py
   +---> screening/momentum.py
   +---> screening/high_stocks.py
   +---> charting/bulk.py
   +---> export/tradingview.py
   +---> db/queries.py
   +---> backend/services/meta_service.py
```

### 새 파일

| 파일 | 목적 |
|------|------|
| `my_chart/krx_session.py` | KRX 세션 관리, monkey-patch, `get_market_cap_safe()` |
| `.env.example` | KRX_ID, KRX_PW 템플릿 (빈 값) |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `my_chart/config.py` | `python-dotenv` 로딩 추가, `krx_session.init_session()` 자동 호출 |
| `my_chart/registry.py` | `stock.get_market_cap()` -> `get_market_cap_safe()` 교체 |
| `my_chart/analysis/market.py` | 동일 교체 (다수 호출 지점) |
| `my_chart/screening/momentum.py` | 동일 교체 |
| `my_chart/screening/high_stocks.py` | 동일 교체 |
| `my_chart/charting/bulk.py` | 동일 교체 (3+ 호출 지점) |
| `my_chart/export/tradingview.py` | 동일 교체 (3 호출 지점) |
| `my_chart/db/queries.py` | 동일 교체 |
| `backend/services/meta_service.py` | 기존 폴백 유지, 세션 초기화 혜택만 수신 |
| `pyproject.toml` 또는 `requirements.txt` | `python-dotenv` 의존성 추가 |

### 핵심 모듈 설계: `my_chart/krx_session.py`

```
모듈 구성:
  - _session: requests.Session (모듈 레벨 싱글턴)
  - _patched: bool (monkey-patch 적용 여부 가드)
  - _logged_in: bool (로그인 성공 여부)

공개 함수:
  - patch_pykrx_session() -> None
    - webio.Post.read, webio.Get.read를 _session 사용하도록 패치
    - _patched가 True이면 건너뜀 (멱등)

  - login_krx(login_id: str, login_pw: str) -> bool
    - 3단계 로그인 수행
    - CD011 중복 로그인 자동 처리
    - 성공 시 _logged_in = True 반환

  - init_session() -> None
    - patch_pykrx_session() 호출
    - 환경변수에서 KRX_ID, KRX_PW 읽기
    - 둘 다 있으면 login_krx() 호출
    - 없거나 실패 시 경고 로그만 출력

  - get_market_cap_safe(date_str: str) -> pd.DataFrame
    - 1차: pykrx stock.get_market_cap(date_str) 시도
    - 2차: sectormap.xlsx D-day 컬럼 폴백
    - 3차: 빈 DataFrame 반환
    - 항상 DataFrame 반환 보장
```

### KRX 로그인 플로우

```
1. GET  https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd
2. GET  https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc
3. POST https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd
   - payload: {mbrId, pw, mbrNm:"", telNo:"", di:"", certType:""}
   - 응답: {_error_code: "CD001"} = 성공
   - 응답: {_error_code: "CD011"} = 중복 로그인 -> skipDup=Y 재시도
```

---

## 제약조건

1. pykrx 실패 시(세션 인증 포함) 시가총액은 반드시 `sectormap.xlsx` D-day 컬럼으로 폴백해야 한다.
2. `KRX_ID`, `KRX_PW`는 `.env` 파일에서 로드하며, 코드에 하드코딩하지 않는다.
3. Monkey-patch는 프로세스당 1회만 전역 적용한다 (호출별 적용 금지).
4. 세션은 동일 프로세스 내 모든 pykrx 호출에서 재사용되어야 한다.
5. `backend/services/meta_service.py`의 기존 try/except + sectormap 폴백 로직은 보존한다.
6. `.env` 파일은 절대 Git에 커밋되지 않는다.

---

## 의존성

| 라이브러리 | 용도 | 비고 |
|-----------|------|------|
| `python-dotenv` | `.env` 파일 파싱 | 신규 의존성 |
| `requests` | KRX 세션 HTTP 통신 | 기존 의존성 |
| `pykrx` | 시가총액 데이터 조회 | 기존 의존성, monkey-patch 대상 |
| `pandas` | DataFrame 반환 타입 | 기존 의존성 |
| `openpyxl` | sectormap Excel 읽기 | 기존 의존성 |

---

## 위험 요소

| 위험 | 영향 | 대응 |
|------|------|------|
| pykrx 내부 구조 변경 (`webio` 모듈) | monkey-patch 실패 | pykrx 버전 핀닝, 업데이트 시 패치 검증 |
| KRX 로그인 API 변경 | 인증 실패 | sectormap 폴백으로 서비스 유지, 로그 모니터링 |
| KRX 세션 타임아웃 | 장시간 실행 시 인증 만료 | 프로세스 재시작 또는 세션 재인증 로직 추후 추가 |
| `.env` 미설정 상태 실행 | 인증 없이 pykrx 호출 실패 | 경고 로그 + 폴백 자동 적용, 앱 정상 기동 |

---

## 추적성 태그

- SPEC-KRX-AUTH-001 -> plan.md
- SPEC-KRX-AUTH-001 -> acceptance.md
