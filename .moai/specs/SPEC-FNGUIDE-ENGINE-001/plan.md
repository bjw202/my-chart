# SPEC-FNGUIDE-ENGINE-001: 구현 계획

## 마일스톤

### Primary Goal: Parser 유닛 테스트

**우선순위: High**

- `test_parser.py` 작성
- `to_num()`: 정수, 실수, 빈 문자열, 잘못된 입력 케이스
- `convert_string_to_number()`: 기본 동작, fillna=NaN 옵션, 혼합 데이터
- `remove_E()`, `remove_space()`: 정상/엣지 케이스
- `table_parsing()`: BeautifulSoup Tag를 활용한 실제 HTML 구조 테스트
- 네트워크 의존성 없음, 빠른 실행

### Secondary Goal: Crawler 통합 테스트

**우선순위: High**

- `conftest.py` 작성: session-scope fixture로 크롤링 결과 캐시
- `test_crawler.py` 작성
- `read_fs()`: 연결/별도 종목 각각 테스트
- `read_snapshot()`: report dict 키 검증, DataFrame 구조 검증
- `read_consensus()`: DataFrame 구조, 수치형 데이터 검증
- `get_required_rate()`: 반환값 타입 및 범위 검증
- `get_fnguide()`: 7-tuple 반환 구조 검증
- 에러 케이스: 존재하지 않는 종목 코드
- `@pytest.mark.live` 마커로 네트워크 테스트 구분

### Tertiary Goal: Analysis 로직 테스트

**우선순위: Medium**

- `test_analysis.py` 작성
- `fs_analysis()`: 실제 크롤링 데이터 기반 (session fixture 활용)
  - df_anal 필수 행 존재 확인
  - df_invest 필수 행 존재 확인
  - 이익률 범위 검증 (-100% \~ +100%)
  - 가중평균 계산 정합성
  - 1순위 선택 로직 (추세/비추세)
  - 예상치 컬럼 존재 및 타입 검증
- `calc_weight_coeff()`: 간격별 가중치 parametrize 테스트
- IFRS 별도 종목에 대한 비지배주주지분 0 처리 검증

### Final Goal: End-to-End 테스트

**우선순위: Medium**

- `test_analyzer.py` 작성
- `analyze_comp("005930")`: CompResult 전체 필드 검증
- 복수 종목 테스트 (삼성전자, SK하이닉스, 별도 종목)
- CompResult 데이터 일관성 검증 (주식수 계산, EPS 계산)
- `__str__()` 메서드 정상 동작 확인

---

## 기술적 접근

### 테스트 전략: 라이브 크롤링 Only

- Mock 없이 실제 FnGuide 서버에 HTTP 요청
- session-scope fixture로 동일 종목 중복 크롤링 방지
- `@pytest.mark.live` 마커로 오프라인 실행 시 skip 가능
- 크롤링 간 0.1초 딜레이 유지 (서버 부담 최소화)

### 캐싱 전략

```
conftest.py (session scope)
    samsung_fnguide() -> 삼성전자 전체 데이터 캐시
    samsung_fs() -> 삼성전자 재무제표 캐시
    hynix_fnguide() -> SK하이닉스 전체 데이터 캐시
    required_rate() -> BBB- 금리 캐시
```

- 세션당 종목별 1회만 크롤링
- 여러 테스트 함수가 동일 fixture 공유
- 테스트 실행 시간 최소화

### 파일 구조

```
tests/
    fnguide/
        __init__.py
        conftest.py
        test_parser.py
        test_crawler.py
        test_analysis.py
        test_analyzer.py
```

### 의존성

- pytest &gt;= 7.0
- pytest-asyncio (필요 시)
- beautifulsoup4 (parser 테스트용 HTML 생성)
- 추가 설치 불필요 (fnguide 패키지 의존성으로 충분)

---

## 리스크 및 대응

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| FnGuide 웹사이트 일시 접속 불가 | Crawler/E2E 테스트 실패 | `@pytest.mark.live` skip 처리, CI에서 수동 트리거 |
| FnGuide HTML 구조 변경 | Parser/Crawler 테스트 실패 | 실패 시 구체적 에러 메시지로 변경 지점 파악 |
| IFRS(별도) 종목 미확인 | 별도 재무제표 테스트 불가 | read_fs()로 여러 종목 탐색하여 별도 종목 확인 |
| 크롤링 속도 제한 | 테스트 시간 증가 | session-scope fixture로 최소 크롤링 |
| 종가/시총 등 시점 의존 데이터 | 범위 검증만 가능 | 절대값 대신 범위 기반 assertion |

---

## 추적성 태그

- SPEC: SPEC-FNGUIDE-ENGINE-001
- 관련 파일: `fnguide/parser.py`, `fnguide/crawler.py`, `fnguide/analysis.py`, `fnguide/analyzer.py`