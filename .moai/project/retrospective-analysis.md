# KR Stock Screener 프로젝트 회고 분석

## 프로젝트 현재 상태: 성공적 운영 중

**목적**: 이 프로젝트를 처음부터 다시 만든다고 가정할 때, MoAI 워크플로우를 이용해 one-shot prompting으로 성공적으로 만들기 위한 전략을 분석한다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 프로젝트명 | KR Stock Screener |
| 기술 스택 | Python/FastAPI + React/TypeScript + SQLite + TradingView Charts |
| 개발 기간 | 2026-02-27 ~ 2026-03-02 (5일) |
| 총 커밋 수 | 16 |
| Fix 커밋 수 | 7 (44%) |
| Feature 커밋 수 | 7 (44%) |
| 기타 (docs/chore) | 2 (12%) |

---

## 2. 커밋 타임라인

```
Feb 27  ┃ c6d5513  feat: initial commit (my_chart library)
        ┃ 25b6817  chore(mx): @MX tags
        ┃ 863ec44  ★ FIX: SQL injection + connection leaks [SECURITY]
Feb 28  ┃ 5c29dda  feat(web): SPEC-WEB-001 구현 (13,226줄 추가, 103개 파일)
        ┃ b96ef42  ★ FIX: return filter 쿼리 버그 + chart UX [DATA/UX]
Mar 01  ┃ bbd88b7  ★ FIX: pykrx 장애 대응 fallback [API]
        ┃ 65ad3a9  ★ FIX: chart 데이터 수집 범위 확대 [DATA]
        ┃ adfa1e9  ★ FIX: chart 렌더링 방식 변경 [CHART]
        ┃ 2dda8f6  ★ FIX: rightOffset 재적용 [CHART]
        ┃ fb2c316  ★ FIX: StockList 스크롤 동기화 [STATE]
        ┃ 1f4d327  feat: RS값 차트 헤더에 표시
        ┃ 0682b72  feat: DB 업데이트 날짜 표시
        ┃ b3fea20  docs: README 업데이트
        ┃ 6d9a31d  feat: chart cell header UX 개선
Mar 02  ┃ 6603b3e  feat: watchlist + TradingView export
        ┃ 855c1b4  feat: price range measurement tool
```

---

## 3. Fix 커밋 상세 분석

### Fix #1: SQL Injection + Connection Leaks (863ec44)
- **문제**: 기존 my_chart 라이브러리의 13개 f-string SQL 쿼리, connection leak, bare except
- **근본 원인**: 스크립트용으로 작성된 기존 코드를 웹 서비스에 재사용
- **카테고리**: 보안 (Security)
- **예방 가능 여부**: YES
- **필요했던 EARS 요구사항**:
  > "Before reusing existing my_chart SQL queries, the system shall audit and convert all f-string SQL to parameterized queries with context managers."
- **교훈**: 기존 코드를 재사용할 때 보안 감사(security audit)를 SPEC의 선행 조건으로 포함해야 함

### Fix #2: Return Filter 쿼리 버그 + Chart UX (b96ef42)
- **문제**: DB는 수익률을 소수(0.30 = 30%)로 저장하지만, UI는 퍼센트(30)로 전송 → 쿼리가 `chg_1m >= 30` (3000% 수익률)으로 실행됨
- **부수 문제**: 거래정지 종목의 OHLC 0값, 차트 가격축 포맷, StockList 높이 문제
- **근본 원인**: DB 저장 형식과 API 계층 간 데이터 계약(data contract)이 명시되지 않음
- **카테고리**: 데이터 포맷 (Data Format)
- **예방 가능 여부**: YES
- **필요했던 EARS 요구사항**:
  > "When chg_1w/1m/3m values are stored as pct_change() decimals (0.30 = 30%), the API shall divide user-provided percentage thresholds by 100 before SQL WHERE comparison."
  > "When OHLC values contain zeros (trading halt or API error), the system shall sanitize by replacing with nearest non-zero value or dropping the row."
- **교훈**: 데이터 형식 계약서(Data Format Contract)를 SPEC에 명시적으로 포함해야 함

### Fix #3: pykrx API 장애 Fallback (bbd88b7)
- **문제**: pykrx API가 KRX API 변경으로 인해 2026-02-27부터 동작 불능
- **근본 원인**: 외부 API 의존성에 대한 fallback이 불완전
- **카테고리**: 외부 API 통합 (API Integration)
- **예방 가능 여부**: PARTIAL (SPEC 리스크 평가에서 "HIGH 확률"로 이미 식별했으나 fallback 구현이 불완전)
- **필요했던 EARS 요구사항**:
  > "Where pykrx get_market_cap() raises any exception, the system shall fall back to sectormap.xlsx D-day column for market cap data (same unit: 억원)."
- **교훈**: 리스크 평가에서 식별한 항목은 반드시 구체적인 fallback 코드까지 SPEC에 명시해야 함

### Fix #4: Chart 데이터 수집 범위 (65ad3a9)
- **문제**: 1년치 데이터로는 SMA200 계산이 불안정 (연초에 NA 발생)
- **근본 원인**: 기술 지표(SMA200) 안정성을 위한 최소 데이터 윈도우 미계산
- **카테고리**: 데이터 범위 (Data Range)
- **예방 가능 여부**: YES
- **필요했던 EARS 요구사항**:
  > "The system shall collect at least 504 trading days (2 years) of daily OHLCV data to ensure stable SMA200 calculation from day 1 of the display period."
- **교훈**: 기술 지표의 warm-up period를 사전에 계산하고 SPEC에 반영해야 함

### Fix #5: Chart 렌더링 방식 변경 (adfa1e9)
- **문제**: 프론트엔드에서 데이터를 200일로 잘라서 표시 → 사용자가 줌/스크롤 불가
- **올바른 방식**: 전체 2년 데이터 로드 + `timeScale().setVisibleRange()`로 초기 뷰포트 설정
- **근본 원인**: TradingView Lightweight Charts API의 뷰포트 관리 패턴 미숙지
- **카테고리**: 차트 렌더링 (Chart Rendering)
- **예방 가능 여부**: YES (라이브러리 사전 조사 필요)
- **필요했던 EARS 요구사항**:
  > "The system shall load complete chart data to the series and use chart.timeScale().setVisibleRange() for initial viewport display, preserving user's ability to zoom and scroll through full history."
- **교훈**: 외부 라이브러리 사용 시 뷰포트/렌더링 패턴을 사전 조사(research phase)에서 검증해야 함

### Fix #6: rightOffset 재적용 (2dda8f6)
- **문제**: `setVisibleRange()` 호출 후 `rightOffset` 옵션이 무시됨
- **근본 원인**: TradingView API quirk - 초기화 시 설정한 옵션이 setVisibleRange()로 덮어씌워짐
- **카테고리**: 차트 렌더링 (Chart Rendering - Library Quirk)
- **예방 가능 여부**: PARTIAL (라이브러리 문서/이슈 사전 조사로 발견 가능)
- **필요했던 EARS 요구사항**:
  > "After calling setVisibleRange(), the system shall explicitly reapply timeScale options (rightOffset, barSpacing) to ensure chart readability."
- **교훈**: 외부 라이브러리의 known issues/quirks를 research phase에서 GitHub Issues 검색으로 사전 파악

### Fix #7: StockList 스크롤 동기화 (fb2c316)
- **문제**: ChartGrid에서 화살표로 페이지 변경 시 StockList가 따라가지 않음
- **근본 원인**: 두 컴포넌트가 별도의 useScrollSync 인스턴스와 별도의 ref를 사용 → 상태 단절
- **카테고리**: 상태 동기화 (State Sync)
- **예방 가능 여부**: YES
- **필요했던 EARS 요구사항**:
  > "When ChartGrid page changes via any mechanism (arrow keys, pagination buttons, stock item click), the system shall update selectedIndex in NavigationContext, which StockList observes via useEffect to trigger automatic scroll."
- **교훈**: 양방향 동기화(bidirectional sync)는 단일 source of truth (Context)를 통해 구현해야 하며, 이 아키텍처를 SPEC에서 명시해야 함

---

## 4. 카테고리별 분석

| 카테고리 | Fix 수 | 비율 | 예방 가능 |
|----------|--------|------|-----------|
| Chart Rendering (TradingView API) | 3 | 43% | 2/3 (라이브러리 사전 조사) |
| Data Format / Range | 2 | 28% | 2/2 (데이터 계약서) |
| Security (기존 코드) | 1 | 14% | 1/1 (보안 감사 선행) |
| State Sync | 1 | 14% | 1/1 (아키텍처 명시) |

**전체 예방 가능률: 6/7 (86%)**

---

## 5. SPEC 품질 평가

### 잘 된 점 (Strengths)
1. **포괄적 리스크 평가**: pykrx 실패, SQL injection, thread safety 등 주요 리스크 사전 식별
2. **명확한 API 설계**: 6개 엔드포인트의 요청/응답 형식 정의
3. **stock_meta 테이블 스키마**: 완전한 DDL 포함
4. **기술적 접근방식**: Service Bridge Pattern, SQL-First Screening 등 핵심 설계 결정 포함
5. **연구 문서(research.md)**: 기존 코드베이스의 심층 분석

### 부족했던 점 (Gaps)
1. **데이터 형식 계약서 부재**: DB 저장 형식(decimal)과 API 입력 형식(percent) 간 매핑 미정의
2. **TradingView API 패턴 미조사**: 뷰포트 관리, rightOffset 동작 등 라이브러리 특성 누락
3. **기술 지표 warm-up period 미계산**: SMA200의 안정적 계산을 위한 최소 데이터 윈도우 미정의
4. **보안 감사 선행 조건 누락**: 기존 코드 재사용 전 보안 감사를 SPEC 선행 작업으로 명시하지 않음
5. **양방향 동기화 아키텍처 미명시**: ScrollSync의 구체적 상태 관리 패턴 미정의
6. **외부 API fallback 구현 상세 부재**: 리스크는 식별했으나 구체적 fallback 코드/로직 미정의
7. **OHLC 이상값 처리 미정의**: 거래정지 등으로 인한 0값 처리 방식 미명시

### SPEC 완성도 점수: 7/10

---

## 6. One-Shot 성공을 위한 이상적 워크플로우

### Phase 0: 사전 준비 (Pre-Requisites)

#### 0-1. 기존 코드 보안 감사
```
/moai review --security
```
기존 my_chart 라이브러리의 SQL injection, connection leak, bare except를 먼저 수정한 후 웹 서비스 개발에 착수한다. 이것은 SPEC 작업의 선행 조건이다.

#### 0-2. 외부 라이브러리 사전 조사
TradingView Lightweight Charts에 대해 다음을 조사한다:
- 뷰포트 관리 패턴: `setVisibleRange()` vs `fitContent()` vs data slicing
- `rightOffset`, `barSpacing` 등 옵션의 API 호출 순서에 따른 동작
- 차트 인스턴스 생성/파괴 lifecycle
- GitHub Issues에서 known quirks 확인

```
# Context7 MCP로 최신 문서 조회
resolve-library-id("tradingview/lightweight-charts")
get-library-docs(id, topic="setVisibleRange rightOffset viewport")
```

### Phase 1: 계획 (Plan)

```
/moai plan --team "KR Stock Screener Web Service"
```

이상적 SPEC에 반드시 포함해야 하는 추가 섹션:

#### A. 데이터 형식 계약서 (Data Format Contract)

```markdown
## Data Format Contract

### DB Storage Formats
| Column | DB Format | Example | API Input Format | Conversion |
|--------|-----------|---------|------------------|------------|
| chg_1w | decimal | 0.30 | percent (30) | ÷ 100 |
| chg_1m | decimal | 0.30 | percent (30) | ÷ 100 |
| chg_3m | decimal | 0.30 | percent (30) | ÷ 100 |
| market_cap | 억원 (int) | 50000 | 억원 (int) | none |
| rs_12m | 0-100 rating | 85.5 | 0-100 | none |
| close | 원 (real) | 52300.0 | n/a | n/a |

### OHLC Data Quality Rules
- When OHLC contains zero values (trading halt): replace with nearest non-zero in same row
- When all OHLC are zero (full halt day): drop the row entirely
- When Volume is zero but OHLC is valid: keep the row (after-hours trading)
```

#### B. 차트 렌더링 전략 (Chart Rendering Strategy)

```markdown
## Chart Rendering Strategy

### Data Loading
- Backend: Load 504 trading days (2 years) per stock
- Rationale: SMA200 needs 200 data points for stability; extra buffer prevents edge-case NA

### Viewport Management
- Load ALL data points to candleSeries, volumeSeries, MA series
- Set initial viewport: chart.timeScale().setVisibleRange({from, to}) for recent 200 trading days
- MUST reapply rightOffset(5) AFTER setVisibleRange() call (TradingView API quirk)
- Fallback: if setVisibleRange() fails, use fitContent()

### Chart Instance Lifecycle
- Create on mount (useEffect)
- Destroy on unmount or page change: chart.remove()
- DO NOT slice data array for viewport control (breaks zoom/scroll)
```

#### C. 상태 동기화 아키텍처 (State Sync Architecture)

```markdown
## Bidirectional Sync Architecture

Single Source of Truth: NavigationContext.selectedIndex

### StockList → ChartGrid
1. User clicks StockItem
2. Update selectedIndex in NavigationContext
3. ChartGrid observes selectedIndex, calculates page = floor(index / gridSize)
4. ChartGrid navigates to calculated page

### ChartGrid → StockList
1. User presses ← → arrow or clicks pagination
2. ChartGrid updates currentPage AND selectedIndex (first stock of new page)
3. StockList observes selectedIndex via useEffect
4. StockList calls scrollToItem(selectedIndex)

### Key Constraint
- NEVER create separate refs for the same scroll state
- All sync MUST flow through NavigationContext
- useScrollSync hook receives context values, not independent refs
```

#### D. 외부 API Fallback 상세 (External API Fallback Details)

```markdown
## External API Resilience

### pykrx market_cap
- Primary: pykrx.stock.get_market_cap(date)
- Fallback: sectormap.xlsx "D-day" column (unit: 억원)
- Trigger: Any exception from pykrx call
- Verification: Count non-null market_cap after fallback (expect 2551/2551)

### Naver Finance (price_naver)
- Already has retry logic (SPEC-001)
- On failure: skip stock, log warning, continue batch
- Report: {success: N, skipped: M, errors: K}
```

#### E. 기술 지표 요구사항 (Technical Indicator Requirements)

```markdown
## Technical Indicator Stability Requirements

### Minimum Data Window
| Indicator | Required History | Recommended Collection |
|-----------|-----------------|----------------------|
| EMA10 | 10 days | 252 days (1 year) |
| SMA50 | 50 days | 252 days |
| SMA100 | 100 days | 504 days (2 years) |
| SMA200 | 200 days | 504 days (2 years) |

### Collection Strategy
- Daily DB: 730 calendar days (≈504 trading days)
- Chart API: Return 504 trading days
- Frontend: Display 200 trading days initially, full data accessible via zoom/scroll
```

### Phase 2: 실행 (Run)

```
/moai run SPEC-WEB-001
```

실행 시 핵심 주의사항:
1. **Security audit first**: SQL injection 수정 후 구현 시작
2. **Data contract test first**: 데이터 형식 변환 로직에 대한 테스트를 먼저 작성
3. **Chart rendering PoC**: TradingView 뷰포트 관리를 독립 PoC로 먼저 검증
4. **Scroll sync via Context**: 양방향 동기화를 NavigationContext 단일 진실 원천으로 구현

### Phase 3: 동기화 (Sync)

```
/moai sync SPEC-WEB-001
```

---

## 7. One-Shot 프롬프트 전략

### 7-1. 프롬프트에 반드시 포함할 컨텍스트

```
1. 기존 my_chart 라이브러리의 DB 스키마와 데이터 형식 (decimal vs percent)
2. TradingView Lightweight Charts 뷰포트 관리 패턴
3. pykrx API 불안정성과 sectormap.xlsx fallback 전략
4. SMA200 안정성을 위한 최소 504 trading days 수집
5. 양방향 스크롤 동기화의 단일 Context 아키텍처
6. OHLC 이상값(거래정지) 처리 규칙
```

### 7-2. SPEC에 추가해야 할 핵심 EARS 요구사항 (7개)

현재 SPEC에 없어서 fix가 필요했던 요구사항들:

1. **REQ-SEC-PRE**: Before web service implementation, the system shall convert all existing f-string SQL queries to parameterized queries with context managers.

2. **REQ-DATA-001**: When chg_1w/1m/3m filter values are received from the UI as percentages, the API shall divide by 100 to match DB decimal storage format.

3. **REQ-DATA-002**: When OHLC data contains zero values from trading halts, the system shall sanitize (replace single zeros, drop full-zero rows).

4. **REQ-CHART-001**: The system shall load complete 2-year chart data to series and use setVisibleRange() for initial 10-month viewport, NOT data slicing.

5. **REQ-CHART-002**: After setVisibleRange(), the system shall explicitly reapply rightOffset to maintain price axis margin.

6. **REQ-SYNC-001**: All scroll synchronization shall flow through NavigationContext.selectedIndex as single source of truth.

7. **REQ-API-001**: Where pykrx get_market_cap() fails, the system shall fall back to sectormap.xlsx D-day column.

### 7-3. 이상적 프롬프트 구조

```
/moai plan "KR Stock Screener - 기존 my_chart 라이브러리 기반 웹 서비스"

사전 조건:
- 기존 코드 보안 감사 완료 (SQL injection → parameterized queries)
- TradingView Lightweight Charts 뷰포트 관리 패턴 조사 완료

핵심 요구사항:
[위의 REQ-SEC-PRE ~ REQ-API-001 포함]

데이터 형식 계약서:
[위의 Data Format Contract 포함]

차트 렌더링 전략:
[위의 Chart Rendering Strategy 포함]

상태 동기화 아키텍처:
[위의 Bidirectional Sync Architecture 포함]
```

---

## 8. MoAI 워크플로우 최적화 제안

### 8-1. Research Phase 강화

현재 research.md는 기존 코드베이스 분석에 집중하지만, 외부 라이브러리 조사가 부족했다.

**추가 조사 항목**:
- 외부 라이브러리(TradingView, pykrx)의 GitHub Issues/Known Quirks
- Context7 MCP를 통한 최신 API 문서 조회
- 유사 프로젝트의 구현 패턴 참조

### 8-2. Data Contract 섹션 의무화

SPEC에 "Data Format Contract" 섹션을 필수로 포함:
- DB 저장 형식 ↔ API 입/출력 형식 매핑 테이블
- 이상값/NULL 처리 규칙
- 단위 변환 규칙

### 8-3. Library-Specific Behavior 섹션 추가

SPEC에 "Library Integration Notes" 섹션 추가:
- 외부 라이브러리의 알려진 quirks
- API 호출 순서 의존성
- 옵션 우선순위/덮어쓰기 동작

### 8-4. Architecture Decision Records (ADR)

양방향 동기화 같은 복잡한 상호작용은 ADR로 문서화:
- 결정: 단일 Context vs 분산 ref
- 이유: 순환 업데이트 방지
- 결과: 모든 sync가 NavigationContext를 통과

---

## 9. 결론

### 핵심 교훈 요약

| # | 교훈 | 적용 방법 |
|---|------|-----------|
| 1 | 기존 코드 재사용 시 보안 감사를 선행 조건으로 | SPEC에 pre-requisite 섹션 추가 |
| 2 | 데이터 형식 계약서를 SPEC에 명시 | Data Format Contract 섹션 의무화 |
| 3 | 외부 라이브러리의 뷰포트/렌더링 패턴 사전 조사 | Research phase에서 Context7 + GitHub Issues 활용 |
| 4 | 기술 지표의 warm-up period 사전 계산 | 최소 데이터 윈도우를 SPEC에 명시 |
| 5 | 양방향 동기화는 단일 진실 원천으로 설계 | ADR로 아키텍처 결정 문서화 |
| 6 | 리스크 평가 항목에 구체적 fallback 코드 포함 | EARS 요구사항으로 fallback 로직 명세 |
| 7 | 라이브러리 API 호출 순서 의존성 파악 | Library Integration Notes 섹션 추가 |

### One-Shot 성공 확률 예측

현재 프로젝트의 7개 fix 중 6개(86%)는 더 상세한 SPEC으로 예방 가능했다. 위의 전략을 적용하면:

- **Fix 필요 없는 항목**: 6/7 → 86% 감소
- **여전히 발생 가능**: TradingView rightOffset quirk (라이브러리 자체 이슈)
- **예상 One-Shot 성공률**: ~90% (사소한 UX 조정 제외)

### MoAI 워크플로우 개선 포인트

1. `/moai plan`의 research phase에 **외부 라이브러리 조사**를 필수 체크리스트로 추가
2. SPEC 템플릿에 **Data Format Contract** 섹션 추가
3. SPEC 템플릿에 **Library Integration Notes** 섹션 추가
4. 리스크 평가 항목에 **구체적 fallback EARS 요구사항** 연결 의무화
5. 기존 코드 재사용 시 **보안 감사를 pre-requisite**로 자동 추가

---

문서 생성일: 2026-03-03
분석 방법: Agent Teams 병렬 분석 (researcher + analyst)
분석 대상: 전체 git history (16 commits) + SPEC-WEB-001 + 소스 코드
