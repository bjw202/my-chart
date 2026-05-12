# V2 Handoff: 모바일 네이버 stock 기반 테마 분석 (예비)

> **이 문서의 목적**
> 미래 세션이 zero-context에서 시작해도 SPEC-NAVER-THEME-002(또는 V2)를 즉시 `/moai plan`할 수 있도록 V1 작업 중 발견·결정·진단·외부 자원을 self-contained 형태로 정리한 핸드오프 노트입니다.
> 이 문서는 SPEC이 아니므로 EARS 형식이 아니고 acceptance criteria도 강제되지 않습니다. SPEC 표준 파일(spec/plan/acceptance/research/progress)이 아닌 보조 문서입니다.

| 항목 | 값 |
|---|---|
| 작성일 | 2026-05-01 |
| 후속 SPEC ID | 미정 (`SPEC-NAVER-THEME-002` 권장) |
| 의존 | SPEC-NAVER-THEME-001 V1 (commit `12d81b1`) |
| 작성 트리거 | 사용자 메시지 — "컨텍스트가 모자라니 V2 핸드오프 문서먼저 만들어" |
| 권장 다음 명령 | `/moai plan "SPEC-NAVER-THEME-002: 모바일 stock.naver.com 기반 테마 분석"` |

---

## 1. V1 Ship 요약 (baseline)

### 1.1 V1 commit

- commit hash: `12d81b1`
- 메시지: `feat(naver-theme): SPEC-NAVER-THEME-001 V1 MVP 구현 완료`
- branch: `chore/integrated-main-merge-2026-04-25`
- 33 files changed, +5866 / -2494
- 사전 commit `6c203d3`(phase 1 부분 구현)을 leader 진단으로 14건 부정합 식별 후 옵션 A(전면 재작업) 선택해 V1 ship에 도달

### 1.2 V1 결과 매트릭스

| 항목 | 결과 |
|---|---|
| 14개 AC | ✅ 14/14 PASS (`progress.md` §5 참조) |
| 단위 테스트 | 51개 PASS (`tests/test_naver_theme_{parser,analyzer}.py`) |
| 커버리지 | 99% (`backend.services.naver_theme/*` 240줄 중 3줄 miss) |
| Surgical mod | 9 added (`backend/main.py +2`, `frontend 3파일 +7`) — AC-14 통과 |
| DB mtime | 무변경 (read-only URI 검증) — AC-11 통과 |
| 회귀 (frontend) | vitest 신규 회귀 0건 |
| 회귀 (backend) | naver_theme 관련 0건 (사전 존재 환경 이슈 2건은 V1 범위 외, 본 문서 §11) |

### 1.3 V1 데이터 소스

- 메인: `https://finance.naver.com/sise/theme.naver?&page={n}` (테마 목록, 정적 HTML)
- 상세: `https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}` (테마 상세, 정적 HTML)
- 인코딩: **EUC-KR 강제 설정** 필수 (REQ-NT-NF-002)
- 시가총액: **별도 SQLite read-only DB JOIN** (`stock_meta.market_cap`)
- 핵심 셀렉터: `td a.tltle, td a[href*='code=']` (라이브 페이지 호환 fallback 적용)

---

## 2. 왜 V2가 필요한가 — 사용자 의사결정 흐름

### 2.1 사용자 발견

V1 ship 직후 사용자가 모바일 네이버 stock 사이트(`https://m.stock.naver.com/domestic/home/theme/daily`)를 발견하고 다음을 보고:

- 데스크탑보다 정리가 잘 되어 있음
- 테마를 클릭하면 **테마 자체의 설명**이 잘 나와 있음 (V1 데스크탑 페이지에는 없음)
- 종목 편입사유가 풍부하고 구조화되어 있음

### 2.2 옵션 검토 (이전 turn AskUserQuestion)

4가지 진행 옵션이 제시됨:

- **A** V1 그대로 ship + V2 모바일 SPEC 별도 작성 ✅ **선택됨**
- B V1.1 hotfix: 테마 설명만 모바일에서 보강
- C V1 폐기 + 모바일 기반으로 V1 전면 재작성
- D PoC 후 결정 (V1 commit 보류)

옵션 A의 핵심 사유:
- V1 검증 가치(14 AC + 99% 커버리지)를 보존
- V2는 큰 작업(API 식별 + 비공식 endpoint 안정성 평가)이므로 별도 SPEC이 안전
- 두 사이트의 안정성 분리: V1은 데스크탑이 변경되어도 V2와 독립적

### 2.3 V2의 단일 의도

> **모바일 사이트의 풍부한 정보(테마 설명·종목 설명·시총 직접 노출·미니차트)를 활용해 사용자에게 더 깊이 있는 테마 분석 경험을 제공한다.**
> V1과 동일한 read-only add-on 원칙(기존 4탭 무영향)을 유지하되, 데이터 소스를 데스크탑 정적 HTML에서 모바일 JSON API로 전환한다.

---

## 3. 데스크탑 vs 모바일 정보 격차 매트릭스

| 항목 | 데스크탑 (V1) | 모바일 (V2 후보) | V2 영향 |
|---|---|---|---|
| 테마 자체 설명 | ❌ 없음 | ✅ 있음 (긴 한국어 텍스트) | 신규 컬럼 `theme_description` |
| 종목별 편입사유 | 짧은 텍스트 (`td[1]`) | ✅ 풍부한 구조화 설명 | `inclusion_reason` 풍부화 또는 신규 `stock_description` |
| 시가총액 | DB JOIN 의존 (`mode=ro`) | ✅ 페이지에서 직접 노출 (예: `1조 1,801억`) | `db_join.py` 단순화 또는 제거 |
| 종목 로고 | ❌ | ✅ 페이지 노출 | (V2.1 또는 V3) |
| 미니 차트 (sparkline) | ❌ | ✅ 종목별 1행 미니 차트 | V2 또는 V3, 시계열 차트 일부 대체 |
| 즐겨찾기 별 | ❌ | ✅ | 본 SPEC 범위 외 (별도 사용자 기능) |
| 데이터 형식 | EUC-KR HTML | UTF-8 JSON (Next.js) | `RESPONSE_ENCODING` 상수 제거 |
| 크롤링 라이브러리 | `requests + lxml + BeautifulSoup` | `requests + JSON 파싱` | parser.py 대부분 재작성 |
| 컬럼 인덱스 의존 | `td[1]/td[2]/td[7]/td[8]` 매핑 위험 | 필드명 기반 견고 | parser.py 견고성 개선 |
| 인증 | 불필요 (정적 HTML) | 미확인 (PoC 필요) | §6 PoC 단계 |
| Rate limit | 미관측 | 미확인 (PoC 필요) | §6 PoC 단계 |

---

## 4. 모바일 사이트 기술 진단 (실측)

### 4.1 페이지 유형

`https://m.stock.naver.com/domestic/home/theme/daily`는 **Next.js SPA**.

curl 응답 헤더·HTML 분석 결과:

```text
<!DOCTYPE html><html lang="ko"><head>
  <meta charSet="utf-8"/>
  <meta name="next-head-count" content="13"/>
  <title>Npay 증권</title>
  ...
  <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{
      "userAgent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
      "_sentryTraceData":"...",
      "_sentryBaggage":"sentry-environment=real,
                       sentry-release=stock-web%402026.04.30,
                       sentry-public_key=eab941495e2a457dad78b49208e8db3f,
                       sentry-trace_id=...,
                       sentry-sampled=true"
    }},
    "page":"/domestic/home/theme/daily",
    "query":{},
    "buildId":"d01c07210178cc591fceef53c2a254734895af05",
    "assetPrefix":"htt..."}
  </script>
```

진단:
- `__NEXT_DATA__`에 **데이터가 직렬화되어 있지 않음** (서버 렌더링 시점에 비어 있음)
- 즉 데이터는 클라이언트가 별도 fetch 하는 구조 → **JSON API 호출 패턴**
- buildId는 자주 바뀜 (deploy마다) — endpoint URL이 빌드별로 hash 포함될 가능성도 있음

### 4.2 sentry release

- `stock-web@2026.04.30` — 거의 매일 배포되는 활발한 서비스
- API 변경 가능성 상존, 모니터링 필요

### 4.3 추정 API endpoint (미검증)

다음은 **추정**이며 PoC에서 검증 필요:

- `https://api.stock.naver.com/domestic/home/theme/daily` (목록)
- `https://api.stock.naver.com/domestic/group/theme/{theme_id}` (상세)
- `https://m.stock.naver.com/api/json/sise/themes` (legacy, 미확인)
- `https://m.stock.naver.com/front-api/...` (Next.js BFF 패턴)

leader가 시도한 단발 호출(`https://m.stock.naver.com/api/json/sise/themes?count=20&page=1`, `https://api.stock.naver.com/api/sise/group/theme/today`)은 **확인 불충분**(curl 결과 truncate). 정확한 endpoint는 browser DevTools Network 탭으로 식별 권장.

---

## 5. 첨부 이미지 분석 (전선 테마 페이지)

원본 경로 (사용자 환경): `/Users/byunjungwon/Pictures/OctoCLI/clipboard_1777629894_32588.png`

### 5.1 페이지 헤더

- 좌상단: 뒤로가기 화살표 `<`
- 중앙: 테마명 "**전선**"
- 우상단: "+9.20%" (당일 등락률)

**테마 설명 (이미지 헤더 직하):**
> 각종 전선 및 전람(電纜)제조 판매업체. 인공지능(AI) 기술 발전으로 전력 인프라 수요가 급증하면서 구리 가격 상승세가 지속되는 가운데, 이에 따른 수혜가 기대되고 있음. 특히, 해상풍력과 국가 간 전력망 연계에 필요한 해저 케이블(초고압 직류 송전, HVDC 케이블) 수요가 빠르게 증가하고 있어 전선업체의 차세대 성장 동력으로 부각.

이 텍스트는 V1에는 존재하지 않는 **V2 핵심 차별화 가치**.

### 5.2 컬럼 구조 (테이블 헤더)

| 종목 | (미니 차트) | 현재가 | 거래량·대금 | 시가총액 | (즐겨찾기) |
|---|---|---|---|---|---|

### 5.3 행 단위 정보 (전선 테마 8개 종목 발췌)

각 행 구조:
1. 로고 아이콘 (원형, 색상별)
2. 종목명 + 종목코드 (예: `KBI메탈 / 024840`)
3. 미니 차트 (sparkline, 당일 흐름)
4. 현재가 (예: `5,100`) + 등락 (예: `+1,175 (29.94%)`)
5. 거래량 + 거래대금 (예: `3,917만 / 1,811억`)
6. 시가총액 (예: `1,780억`)
7. 즐겨찾기 별 아이콘
8. **종목 설명** (회색 박스, 예시 4건):

   - **KBI메탈 (024840):** "전선제조용 동선(ROD) 사업 영위. 전선사업(전선 제조/판매)을 영위하는 KBI코스모링크, KBI COSMOLINK-VINA CABLE CO., LTD.를 종속회사로 보유."
   - **대원전선 (006340):** "전력 및 통신 케이블 제조/판매업체. 주요 품목으로는 전력배송전에 사용되는 나선과 전력전선, 전원의 배선용에 사용되는 절연전선, 시내외 통신용으로 사용되는 통신전선 등이 있음."
   - **가온전선 (000500):** "LS그룹 계열사로 전력케이블 및 통신케이블 등을 생산하는 국내 3대 전선 전문 제조업체."
   - **대한전선 (001440):** "초고압케이블 등의 전력선과 소재, 통신케이블 등의 제품을 생산 및 판매하고, 각종 전선 관련 공사를 진행하는 종합 전선업체. 주요 생산 및 판매 품목은 초고압케이블 등 전력선, 소재, 통신케이블, Copper Rod 등."
   - **LS, 일진전기, LS마린솔루션, LS에코에너지** 등 동일 패턴

### 5.4 V1 inclusion_reason vs V2 stock_description 비교

| 측면 | V1 (`inclusion_reason`) | V2 (이미지 기반) |
|---|---|---|
| 길이 | 짧음 (수십 자) | 길고 풍부 (수백 자) |
| 구조 | 평문 | 사업 영역 + 종속회사 등 명시적 항목 포함 가능 |
| 신뢰성 | `td[1]` 인덱스 의존 | JSON 필드명 기반 |

---

## 6. V2 PoC 필수 단계 (SPEC plan 시작 전)

### 6.1 PoC 목표

다음 4가지를 검증하면 V2 SPEC plan을 안전하게 시작 가능:

1. **endpoint 식별:** 테마 목록 + 테마 상세 JSON API의 정확한 URL/method/headers
2. **응답 schema:** 필드명·타입·중첩 구조 (Pydantic 모델 시안)
3. **인증·rate limit:** 익명 호출 가능? 호출 간격 권장? IP block 발생?
4. **안정성:** 1주일 정도 endpoint URL이 동일하게 유지되는가? (deploy build 영향)

### 6.2 PoC 절차 (권장)

#### Step 1 — DevTools Network 추적
1. Chrome/Safari/Firefox에서 `https://m.stock.naver.com/domestic/home/theme/daily` 열기
2. DevTools → Network 탭 → "Fetch/XHR" 필터
3. 페이지 로드 + 테마 클릭 → 상세 페이지 진입
4. 등장하는 모든 JSON 응답 URL을 기록 (예상 2-3개)
5. Request Headers·Cookies·Referer를 캡처

#### Step 2 — curl 재현
```bash
# (예시, 실제 endpoint는 Step 1 결과로 교체)
curl -s -A "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)" \
  -H "Referer: https://m.stock.naver.com/domestic/home/theme/daily" \
  -H "Accept: application/json" \
  "https://api.stock.naver.com/domestic/group/theme/daily" | jq .
```

성공 기준:
- HTTP 200
- 유효한 JSON
- 테마 목록 또는 테마 상세 데이터 포함

#### Step 3 — 응답 schema 정리
- 최소 5개 테마, 5개 종목 응답을 표본화하여 모든 필드 enumerate
- 각 필드 type, nullable 여부, optional 여부 정리
- Pydantic v2 모델 시안 작성 → `.moai/specs/SPEC-NAVER-THEME-002/research.md` 후보

#### Step 4 — 안정성 검증 (선택, 시간 허용 시)
- 7일간 cron으로 endpoint를 매일 1회 호출
- 응답 schema 변동 또는 5xx 비율 측정
- 결과를 `research.md` Risk Assessment 섹션에 추가

### 6.3 PoC 도구

- 권장: 사용자가 직접 browser DevTools (가장 정확)
- 보조: leader가 curl + jq로 재현 검증
- 자동화: Playwright `page.on('response')` hook으로 endpoint 자동 캡처 (V2 e2e 단계에서 활용 가능)

---

## 7. V2 핵심 요구사항 (예비, EARS 변환 전)

### 7.1 기능

| ID 후보 | 요구사항 | 우선순위 |
|---|---|---|
| REQ-NT2-001 | 단일 진입점 `collect_and_analyze_v2`(또는 V1 `collect_and_analyze` 시그니처 유지) 노출 | High |
| REQ-NT2-002 | 모바일 JSON API에서 테마 목록 수집 | High |
| REQ-NT2-003 | 모바일 JSON API에서 테마 상세 수집 (테마 설명 + 종목 설명 + 시총 + 미니차트 데이터) | High |
| REQ-NT2-004 | `theme_description` 신규 컬럼 (V1 `themes_df`에 추가) | High |
| REQ-NT2-005 | `stock_description` 신규 컬럼 (V1 `inclusion_reason` 옆에 추가 또는 대체) | High |
| REQ-NT2-006 | `market_cap` 직접 노출 — `db_join.py` 의존 제거 (또는 fallback) | High |
| REQ-NT2-007 | `mini_chart_points`(선택) — sparkline 데이터 포인트 배열 | Medium |
| REQ-NT2-008 | V1과 동일한 `ThemeAnalysisResult` shape 유지 (frontend 무수정) | High |

### 7.2 비기능

| ID 후보 | 요구사항 |
|---|---|
| REQ-NT2-NF-001 | 매너 호출: 호출 간 sleep ≥ 0.7초, 단일 thread, 모바일 User-Agent 명시 |
| REQ-NT2-NF-002 | UTF-8 JSON 응답 처리 (V1의 EUC-KR 강제 불필요) |
| REQ-NT2-NF-003 | API 5xx/timeout 시 1회 retry, 부분 실패 허용 (V1 동일 패턴) |
| REQ-NT2-NF-004 | 응답 시간 목표: 전체 ≤ 30초, 빠른 모드(`skip_details=True`) ≤ 10초 |
| REQ-NT2-NF-005 | endpoint URL은 config 상수로 분리 (build hash 변경 대응) |

### 7.3 제약

| ID 후보 | 제약 |
|---|---|
| REQ-NT2-C-001 | 인증·쿠키 사용 금지 (익명 호출만) |
| REQ-NT2-C-002 | 기존 4탭 회귀 없음 (V1 AC-12와 동일) |
| REQ-NT2-C-003 | 신규 pip 의존성 추가 금지 |
| REQ-NT2-C-004 | DB INSERT/UPDATE 금지 (V1 AC-11와 동일) — 단 db_join 자체는 V2에서 선택 사용 |

### 7.4 라우팅

| ID 후보 | 엔드포인트 |
|---|---|
| REQ-NT2-R-001 | `GET /api/themes/v2/snapshot` (V1과 충돌 없이 신규 prefix) 또는 `GET /api/themes/snapshot` (V2가 V1 대체 시) |
| REQ-NT2-R-002 | `GET /api/themes/v2/quick` 또는 동일 |

V1과 V2의 cohabitation 전략은 SPEC plan 단계에서 결정 (§9 참조).

---

## 8. V1 → V2 구현 차이 (모듈별)

| 모듈 | V1 (현재) | V2 (예상) | 변경 규모 |
|---|---|---|---|
| `config.py` | URL 2개 + EUC-KR 상수 + sleep 등 | 모바일 endpoint URL + 모바일 UA, EUC-KR 상수 제거 | Small |
| `crawler.py` | requests + EUC-KR 강제 | requests + JSON, `Accept: application/json`, `Referer` 헤더 | Small |
| `parser.py` | BeautifulSoup + lxml + 정규식 | JSON 파싱 (dict access만), 파서 함수 대부분 제거 | Large (대부분 삭제) |
| `analyzer.py` | z-score + groupby | **변경 없음** (동일 입력 shape) | None |
| `service.py` | 페이지네이션 + DB JOIN | 페이지네이션 (있다면) + DB JOIN 제거 | Medium |
| `db_join.py` | sqlite3 mode=ro | **삭제 후보** 또는 fallback (모바일 시총 누락 종목용) | Large |
| `__init__.py` | 진입점 노출 | 동일 | None |
| `routers/themes.py` | snapshot/quick | 동일 (또는 v2 prefix) | None |
| `tests/test_naver_theme_*` | HTML fixture | JSON fixture, parser 테스트 대부분 폐기 | Large |
| Frontend | shape에 의존 | shape 유지하면 무수정 | None (목표) |

핵심 통찰:
- **analyzer.py는 그대로** — V2의 진짜 가치는 데이터 수집·구조화에 있음
- **frontend는 무수정 가능** — `ThemeAnalysisResult` shape를 유지하면 V1과 V2가 호환
- **테스트가 가장 큰 작업** — JSON fixture 신규 + parser 테스트 폐기·재작성

---

## 9. V1·V2 cohabitation 전략 (3가지 옵션)

### Option α: V2가 V1을 즉시 대체 (cutover)
- service/parser/crawler를 V2로 갈아끼움
- routers/themes.py는 동일 endpoint 유지
- 장점: 코드 단순
- 단점: 모바일 API 다운 시 fallback 없음

### Option β: V1·V2 병렬 + config flag로 선택
- `NAVER_THEME_DATA_SOURCE = "desktop" | "mobile"` 환경변수
- service.py가 분기
- 장점: A/B 테스트 가능, 모바일 API 다운 시 desktop fallback
- 단점: 코드량 2배, 장기 유지 부담

### Option γ: V2 신규 endpoint(`/api/themes/v2/...`) + V1은 deprecated
- 사용자가 명시적으로 v2 enpoint 호출
- 장점: V1 회귀 0%, V2 점진 도입
- 단점: 두 endpoint를 frontend가 모두 알아야

**추천:** Option β 또는 γ (안정성 우선). 결정은 SPEC plan에서 manager-spec subagent와 논의.

---

## 10. 위험 평가 (V2 specific)

| 위험 | 가능성 | 영향 | 완화 |
|---|---|---|---|
| 비공식 API 변경 | High (sentry release: 2026-04-30 활발) | 데이터 수집 실패 | endpoint URL config 상수 분리 + 응답 schema 검증 + alert |
| build hash 포함 URL | Medium | URL 자주 변경 | DevTools 추적 시 buildId-free URL 우선 식별 |
| Rate limit / IP block | Medium | 호출 차단 | sleep ≥ 0.7s + 단일 thread + User-Agent 정직 표시 |
| 인증 요구 | Low (익명으로 페이지 접근 가능) | 통합 복잡도 증가 | PoC Step 1에서 헤더 검사 |
| 응답 schema 불완전 (테마 설명 누락) | Medium | `theme_description` NaN | nullable 필드로 처리, optional 표시 |
| 테마 ID 체계 변경 | Low | V1 호환성 깨짐 | V1과 동일한 정수 ID 가정, 다른 체계면 mapping table |
| 모바일 sparkline 데이터 부재 | Medium | REQ-NT2-007 무효 | optional, V2.1로 이연 가능 |

---

## 11. V1 RUN phase에서 발견된 V1 범위 외 항목

이미 `progress.md` §6에 기록된 사항. V2 plan 시 같이 검토:

### 이슈 2 — 사전 존재 환경 충돌
- 증상: `pytest --cov` 시 `ModuleNotFoundError: No module named 'pkg_resources'` 에서 시작해 `numpy/pandas` 이중 import 에러로 collection error
- 영향: `tests/test_krx_session.py`, `tests/test_chart_service.py`
- V1 범위 외 (사용자 결정)
- 별도 SPEC 또는 issue 권장. 가능한 해결책:
  - 옵션: `setuptools` 또는 `importlib.metadata` 폴리필 추가 (Python 3.13에서 `pkg_resources` 제거 영향)
  - 옵션: `backend/services/__init__.py`를 lazy import로 변경 (V1에서는 revert됨)

### V1.5 ish-out
- `GET /api/themes/by-stock/{code}` reverse index endpoint
- `frontend/src/components/MarketOverview/HotThemesStrip.tsx`
- `frontend/src/components/StockList/ThemeChips.tsx`
- `CrossTabParams.themeId / themeName` 추가

V2가 위 항목 일부를 흡수할 수 있음 (특히 `by-stock` reverse index). SPEC plan에서 명시 결정.

---

## 12. Definition of Done (V2 예비)

### 자동 검증

- [ ] 단위 테스트 (JSON fixture 기반) 커버리지 ≥ 85%
- [ ] V1과 동일한 `ThemeAnalysisResult` shape 유지 (frontend 회귀 0건)
- [ ] 라이브 1회 호출 성공 (`@pytest.mark.live`)
- [ ] V1 14개 AC와 동일한 책임 매핑 재검증

### 수동 검증

- [ ] 모바일 API endpoint 변경 빈도 1주일 모니터링 (5xx < 5%, schema 변동 0건)
- [ ] 테마 설명 컬럼 100% 존재 (NaN 허용)
- [ ] 종목 설명 컬럼 90% 이상 존재
- [ ] db_join 의존 제거 또는 fallback 명시 결정

### Cohabitation 결정

- [ ] Option α/β/γ 중 1개 선택 + 합리화 문서화

---

## 13. SPEC-NAVER-THEME-001 RUN phase에서 학습한 교훈

V2 SPEC plan 시 만들지 말아야 할 함정:

1. **컬럼 인덱스 의존 매핑 금지** — V1 parser가 td[1]/td[2]/td[7]/td[8]에 의존했던 결함 재발 방지. JSON 필드명 사용.
2. **인코딩 강제 누락 금지** — V1 crawler.py가 첫 commit에서 EUC-KR을 강제하지 않았던 문제. V2는 UTF-8 기본이지만 `Content-Type: application/json` 명시.
3. **DB 연결 read-only URI** — V1 db_join.py가 `mode=ro` URI를 사용하는 패턴 유지 (V2가 db_join을 fallback으로 쓴다면).
4. **`bare except` 금지** — Python 룰. specific exception (`requests.RequestException`, `json.JSONDecodeError` 등) 분리 catch.
5. **errors는 dict 형식** — `[{"theme_id", "stage", "reason"}]` 일관 유지.
6. **라이브 검증 1회 필수** — V1은 V1 RUN phase에서 라이브 호출을 하지 않아 셀렉터 부정합을 사후 발견. V2는 PoC Step 4에서 라이브 1회 검증을 처음부터 포함.
7. **fixture는 라이브 fetch + synthetic 혼합** — V1 tester가 Option A 라이브 fetch + Option B synthetic을 혼합 사용해 셀렉터 부정합을 노출시킨 패턴이 효과적이었음. V2도 동일 패턴 권장 (단 JSON fixture).

---

## 14. 권장 다음 명령

### 14.1 사용자가 직접 PoC를 마친 경우
```
/moai plan "SPEC-NAVER-THEME-002: 모바일 stock.naver.com 기반 테마 분석 V2 — 테마 설명·종목 설명 풍부화·시가총액 직접 노출. PoC 결과(endpoint, schema)는 .moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md 참조. cohabitation 전략은 옵션 β 또는 γ에서 결정 필요."
```

### 14.2 PoC 자동화도 manager-spec에 위임하고 싶은 경우
```
/moai plan "SPEC-NAVER-THEME-002: 모바일 stock.naver.com 기반 테마 분석 V2. 첫 단계로 PoC를 수행해 endpoint·schema·인증·rate limit을 식별하고 그 결과를 research.md에 기록한 뒤 SPEC을 작성. 컨텍스트는 .moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md 전체 참조."
```

### 14.3 사용자가 V2 시작 시점을 미루고 싶은 경우
- 본 핸드오프 문서를 그대로 두고
- `/moai sync SPEC-NAVER-THEME-001` 우선 진행
- V2는 추후 별도 세션에서 14.1 또는 14.2 명령으로 시작

---

## 15. 참조

### V1 핵심 파일
- `.moai/specs/SPEC-NAVER-THEME-001/spec.md` — V1 SPEC v1.0.0 Approved
- `.moai/specs/SPEC-NAVER-THEME-001/plan.md` — V1 구현 계획
- `.moai/specs/SPEC-NAVER-THEME-001/acceptance.md` — V1 14개 AC
- `.moai/specs/SPEC-NAVER-THEME-001/research.md` — V1 코드베이스 분석
- `.moai/specs/SPEC-NAVER-THEME-001/progress.md` — V1 RUN phase 진행 결과
- `backend/services/naver_theme/{__init__,config,crawler,parser,analyzer,service,db_join}.py` — V1 모듈
- `backend/routers/themes.py` — V1 FastAPI 라우터
- `frontend/src/components/ThemeAnalysis/*` — V1 프론트엔드
- `tests/test_naver_theme_{parser,analyzer}.py` — V1 단위 테스트
- `tests/fixtures/naver_theme/{theme_list_page1,theme_detail_178}.html` — V1 fixture

### V1 commit
- `12d81b1` — `feat(naver-theme): SPEC-NAVER-THEME-001 V1 MVP 구현 완료`

### 모바일 사이트 진입 URL
- `https://m.stock.naver.com/domestic/home/theme/daily`
- `https://m.stock.naver.com/` (메인)

### 사용자 제공 자료
- 클립보드 이미지 (전선 테마 페이지): `/Users/byunjungwon/Pictures/OctoCLI/clipboard_1777629894_32588.png` — 사용자 환경에만 존재
- 본 문서 §5에 텍스트 캡션으로 보존됨

### 외부 문서
- Next.js docs (SPA 분석): `https://nextjs.org/docs`
- Naver Mobile Stock: 공식 API 문서 부재 (비공식 endpoint)

---

## 16. 자체 검증 — 이 핸드오프는 self-contained인가?

다음 질문에 모두 "예"여야 합니다:

- [x] 다음 세션이 본 파일만 읽고 V2를 plan할 수 있는가? → §6 PoC 단계 + §7 요구사항 + §14 명령으로 가능
- [x] V1과 V2의 차이가 명확한가? → §3 매트릭스 + §8 모듈별 차이
- [x] V2의 위험을 알고 있는가? → §10 위험 평가
- [x] V2 PoC를 시작할 수 있는 구체적 단계가 있는가? → §6.2 4단계
- [x] V1 RUN phase 학습이 보존되는가? → §13 교훈
- [x] cohabitation 전략 옵션이 제시되어 있는가? → §9 α/β/γ
- [x] 외부 자원(이미지, URL)이 검색 가능한 형태로 보존되는가? → §5 + §15

---

Version: 1.0.0
Document Type: V2 Handoff Note (non-SPEC, supplementary)
Status: V1 ship 직후 작성, V2 plan 대기
