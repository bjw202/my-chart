# SPEC-KRX-AUTH-001: 인수 기준

## 추적성

- SPEC: SPEC-KRX-AUTH-001
- 참조: spec.md, plan.md

---

## 인수 시나리오

### AC-01: KRX 세션 로그인 성공

```gherkin
Given KRX_ID와 KRX_PW가 .env에 유효한 값으로 설정되어 있다
When 애플리케이션이 시작되어 init_session()이 호출된다
Then login_krx()가 True를 반환한다
And 로그에 "KRX login successful" 메시지가 기록된다
And pykrx webio.Post.read가 인증된 세션을 사용하도록 패치된다
```

### AC-02: KRX 세션 로그인 실패 (잘못된 자격증명)

```gherkin
Given KRX_ID와 KRX_PW가 .env에 잘못된 값으로 설정되어 있다
When 애플리케이션이 시작되어 init_session()이 호출된다
Then login_krx()가 False를 반환한다
And 로그에 경고 메시지가 기록된다
And 애플리케이션은 정상적으로 기동된다 (중단되지 않음)
```

### AC-03: 환경변수 미설정 시 graceful 기동

```gherkin
Given .env 파일이 존재하지 않거나 KRX_ID/KRX_PW가 비어있다
When 애플리케이션이 시작된다
Then init_session()이 로그인을 스킵한다
And 로그에 "KRX credentials not found, skipping login" 경고가 기록된다
And 애플리케이션은 정상적으로 기동된다
And pykrx 호출 실패 시 sectormap 폴백이 동작한다
```

### AC-04: 시가총액 조회 - pykrx 성공 경로

```gherkin
Given KRX 세션이 인증된 상태이다
When get_market_cap_safe("20260303")이 호출된다
Then pykrx stock.get_market_cap("20260303")의 결과가 반환된다
And 반환 타입은 pd.DataFrame이다
And 인덱스가 종목코드(6자리)이다
```

### AC-05: 시가총액 조회 - pykrx 실패 후 sectormap 폴백

```gherkin
Given pykrx stock.get_market_cap() 호출이 실패한다 (Exception 발생)
When get_market_cap_safe("20260303")이 호출된다
Then sectormap.xlsx의 D-day 컬럼에서 시가총액을 로드한다
And 로그에 "pykrx failed, falling back to sectormap" 경고가 기록된다
And 반환 타입은 pd.DataFrame이다
```

### AC-06: 시가총액 조회 - 모든 소스 실패

```gherkin
Given pykrx 호출이 실패하고 sectormap 파일도 읽기 실패한다
When get_market_cap_safe("20260303")이 호출된다
Then 빈 pd.DataFrame이 반환된다
And 로그에 에러 메시지가 기록된다
And 호출자에서 예외가 발생하지 않는다
```

### AC-07: Monkey-Patch 멱등성

```gherkin
Given patch_pykrx_session()이 이미 1회 호출된 상태이다
When patch_pykrx_session()이 다시 호출된다
Then 패치가 중복 적용되지 않는다
And 기존 세션이 유지된다
```

### AC-08: 중복 로그인 자동 처리 (CD011)

```gherkin
Given KRX에 동일 계정으로 이미 로그인되어 있다
When login_krx()가 호출되어 CD011 에러코드를 수신한다
Then skipDup=Y 파라미터로 자동 재시도한다
And 재시도 후 CD001(성공)을 수신하면 True를 반환한다
```

### AC-09: 기존 호출 지점 교체 완료

```gherkin
Given 모든 pykrx 직접 호출이 get_market_cap_safe()로 교체되었다
When registry.py의 get_companies_by_market_cap()이 호출된다
Then get_market_cap_safe()를 통해 시가총액을 조회한다
And 기존과 동일한 결과를 반환한다
```

### AC-10: meta_service.py 기존 폴백 보존

```gherkin
Given backend/services/meta_service.py가 수정되었다
When rebuild_stock_meta()가 실행된다
Then 기존 try/except + sectormap 폴백 로직이 그대로 동작한다
And 인증된 세션을 통해 pykrx 성공률이 향상된다
```

### AC-11: .env 파일 Git 보안

```gherkin
Given .gitignore에 .env 패턴이 포함되어 있다
When 사용자가 .env 파일을 생성한다
Then git status에 .env가 추적 대상으로 나타나지 않는다
```

### AC-12: 로깅 보안 - 비밀번호 미포함

```gherkin
Given KRX 인증이 시도된다
When 로그인 성공 또는 실패 로그가 기록된다
Then 로그에 KRX_PW(비밀번호) 값이 포함되지 않는다
And 로그에 KRX_ID(아이디)만 마스킹 처리되거나 포함된다
```

---

## 품질 게이트

### 테스트 커버리지

- `my_chart/krx_session.py`: 주요 함수 (login_krx, patch_pykrx_session, get_market_cap_safe, init_session) 단위 테스트
- 폴백 경로 테스트: pykrx mock 실패 시 sectormap 폴백 검증
- 환경변수 미설정 테스트: .env 없이 init_session() 정상 동작 검증

### 회귀 테스트

- `backend/services/meta_service.py`의 기존 폴백 동작이 변경되지 않았음을 검증
- 각 교체된 호출 지점에서 반환 타입(pd.DataFrame) 호환성 검증

### 검증 방법

| 항목 | 방법 |
|------|------|
| 세션 로그인 | KRX 계정으로 실제 로그인 후 pykrx 호출 성공 확인 |
| 폴백 동작 | KRX_ID/KRX_PW 미설정 상태에서 sectormap 데이터 반환 확인 |
| Monkey-patch | `webio.Post.read`가 `_session.post`를 호출하는지 확인 |
| 멱등성 | `patch_pykrx_session()` 2회 호출 후 `_patched` 플래그 확인 |
| 보안 | `.env` 파일이 `git status`에 나타나지 않음 확인 |

---

## Definition of Done

- [ ] `my_chart/krx_session.py` 생성 완료 (login_krx, patch_pykrx_session, get_market_cap_safe, init_session)
- [ ] `my_chart/config.py`에 dotenv 로딩 + init_session() 호출 추가
- [ ] `.env.example` 생성 (KRX_ID, KRX_PW 템플릿)
- [ ] `python-dotenv` 의존성 추가
- [ ] 7개 파일의 pykrx 직접 호출을 get_market_cap_safe()로 교체
- [ ] `meta_service.py` 기존 폴백 로직 보존 확인
- [ ] 단위 테스트 작성 및 통과
- [ ] 로그에 비밀번호 미포함 확인
- [ ] .env가 .gitignore에 의해 추적 제외 확인
