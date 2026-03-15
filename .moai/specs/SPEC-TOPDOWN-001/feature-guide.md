# SPEC-TOPDOWN-001: Top-Down 시장분석 시스템 — 화면 구성 가이드

## 개요

**목적**: Top-Down 시장분석 시스템은 시장 사이클 판단에서 시작하여 섹터 회전, 종목 스테이지 분류, 차트 분석까지 일관된 분석 흐름을 제공합니다.

**전체 구조**: 4개의 탭으로 구성된 시스템으로, 각 탭은 시장을 점진적으로 확대(Top-Down) 분석합니다:
1. **Market Overview** (시장 개요) — 시장 사이클과 Breadth 지표 분석
2. **Sector Analysis** (섹터 분석) — 섹터 강도 순위 및 성과 추적
3. **Stock Explorer** (종목 탐색) — 종목의 Weinstein Stage 분류 및 스크리닝
4. **Chart Grid** (차트 그리드) — 선택된 종목의 기술적 분석 차트

**데이터 흐름**:
```
백엔드 API
├─ GET /api/market/overview  → KOSPI/KOSDAQ 현재값, Breadth 지표, 시장 사이클, 12주 히스토리
├─ GET /api/sectors/ranking  → 모든 섹터 성과, RS 평균, 스테이지2 비율 등
└─ GET /api/stage/overview   → 종목 Stage 분포, 섹터별 Stage 분포, Stage2 후보 종목 리스트

프론트엔드 컴포넌트
└─ TabNavigation + ContextBar (공통)
   ├─ MarketOverview (MarketPhaseCard, BreadthChart, MiniHeatmap, WeeklyHighlights)
   ├─ SectorAnalysis (SectorRankingTable, SectorDetailPanel)
   ├─ StockExplorer (StageDistributionBar, StockTable)
   └─ ChartGrid (기존 기능)
```

---

## 공통 UI 요소

### 탭 네비게이션 (TabNavigation)

**위치**: 애플리케이션 최상단

**표시 내용**: 4개의 탭 버튼
- `[Market Overview]` `[Sector Analysis]` `[Stock Explorer]` `[Chart Grid]`

**기본 활성 탭**: Chart Grid (기존 호환성 유지)

**동작**:
- 각 탭을 클릭하면 해당 탭 콘텐츠로 전환
- 각 탭의 내부 상태(스크롤 위치, 필터, 선택 항목)는 보존됨
- 다시 돌아올 때 이전 상태 복원

---

### Context Bar (맥락 바)

**위치**: 탭 네비게이션 바로 아래

**표시 항목**:
1. **시장 사이클 배지**: Bull / Sideways / Bear (색상으로 구분)
2. **Choppy 경고**: 시장이 박스권 박혁 상태일 때 표시
3. **강세 섹터**: 현재 가장 강한 상위 2-3개 섹터 (예: 반도체, IT)
4. **약세 섹터**: 현재 가장 약한 상위 2-3개 섹터 (예: 화학, 금융)

**데이터 소스**:
- `/api/market/overview` — cycle.phase, cycle.choppy
- `/api/sectors/ranking` — 전체 섹터 목록, 각 섹터의 rank 값

**갱신**: 마켓 데이터가 갱신될 때마다 자동 반영

---

## 탭 1: Market Overview (시장 개요)

### 화면 구성

```
┌────────────────────────────────────────────────────┐
│  TabNavigation: [Market Overview] [Sector ...] ... │
├────────────────────────────────────────────────────┤
│  ContextBar: [Bull] | 반도체, IT | 화학, 금융      │
├────────────────────────────────────────────────────┤
│                                                     │
│  ┌─ MarketPhaseCard ─────────────────────────────┐ │
│  │  KOSPI: 2,500 (+0.5%)  [Bull] [Choppy]       │ │
│  │  KOSDAQ: 800 (-0.2%)                         │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ BreadthChart (12주 선차트) ──────────────────┐ │
│  │  % > SMA50 (파란색)                           │ │
│  │  Breadth Score (보라색)                       │ │
│  │  NH-NL Ratio (주황색)                         │ │
│  │  기준선: 60% (과매수), 40% (과매도)           │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ MiniHeatmap ──────────┐ ┌─ WeeklyHighlights─┐ │
│  │ Sector Performance (1W) │ │ Market Phase      │ │
│  │ [반도체] [금융] [화학]  │ │ [Bull] [Choppy]   │ │
│  │ [IT] [자동차] [건설]    │ │                   │ │
│  │ 등 모든 섹터 히트맵     │ │ Biggest Movers    │ │
│  │ (초록=강세, 빨강=약세) │ │ ↑ 반도체 +5      │ │
│  └────────────────────────┘ │ ↓ 금융 -3        │ │
│                             │ ↑ IT +2           │ │
│                             │                   │ │
│                             │ Stage 2 Entry     │ │
│                             │ [Stock Explorer] │ │
│                             └───────────────────┘ │
└────────────────────────────────────────────────────┘
```

### 컴포넌트별 기능

#### MarketPhaseCard
**표시 항목**:
- KOSPI 현재가 (로케일 포맷)
- KOSPI 주간 변화율 (% 단위, 색상: 양수=초록, 음수=빨강)
- KOSDAQ 현재가 (로케일 포맷)
- KOSDAQ 주간 변화율
- 시장 사이클 배지 (Bull / Sideways / Bear)
- Choppy 경고 배지 (있을 때만 표시)

**데이터 소스**: `/api/market/overview`
```json
{
  "kospi": {
    "close": 2500.0,
    "chg_1w": 0.5
  },
  "kosdaq": {
    "close": 800.0,
    "chg_1w": -0.2
  },
  "cycle": {
    "phase": "bull",
    "choppy": false
  }
}
```

#### BreadthChart (12주 선 차트)
**차트 구성**: Lightweight Charts 라이브러리로 렌더링

**3개 시리즈**:
1. **% > SMA50** (파란색, 왼쪽 축)
   - 주가가 50일 이동평균 위에 있는 종목의 비율
   - 60% 이상: 과매수 영역
   - 40% 이하: 과매도 영역

2. **Breadth Score** (보라색, 왼쪽 축)
   - 시장 strength의 종합점수 (0-100)
   - 4가지 지표(SMA50 비율, SMA200 비율, NH-NL 비율, AD 비율)를 0-100으로 정규화하여 평균값
   - 65 이상: 강세, 35 이하: 약세

3. **NH-NL Ratio** (주황색, 오른쪽 축)
   - 52주 신고가 / (신고가 + 신저가)의 비율
   - 0-1 스케일, 0.6 이상: 강세, 0.4 이하: 약세

**기준선**:
- 60% 라인: 과매수 경고
- 40% 라인: 과매도 신호

**데이터 소스**: `/api/market/overview`에서 `breadth_history` 배열
```json
"breadth_history": [
  {
    "date": "2024-01-01",
    "pct_above_sma50": 58.3,
    "breadth_score": 62.1,
    "nh_nl_ratio": 0.58
  },
  ...
]
```

**동작**:
- 마우스 호버 시 특정 날짜의 상세값 표시
- 반응형: 컨테이너 너비 변경에 따라 자동 리사이징

#### MiniHeatmap (섹터 성과 미니 히트맵)
**동작 방식**:
- CSS Grid로 모든 주요 섹터(산업명(대))를 동일한 크기의 셀로 배치
- 각 셀의 배경색은 주간(1W) 수익률에 따라 결정
  - 양수(강세): 초록색 계열 (밝은 초록 ~ 짙은 초록)
  - 음수(약세): 빨강색 계열 (밝은 빨강 ~ 짙은 빨강)

**셀 내용**:
- 섹터명 (예: "반도체", "금융", "IT")
- 주간 수익률 (예: "+1.2%", "-0.8%")

**클릭 동작**:
- 섹터 셀을 클릭하면 Sector Analysis 탭으로 이동하고, 해당 섹터 하이라이트

**데이터 소스**: `/api/sectors/ranking`
```json
"sectors": [
  {
    "name": "반도체",
    "returns": { "w1": 1.2 },
    "rank": 1
  },
  ...
]
```

#### WeeklyHighlights (주간 주목할 점)
**표시 항목**:

1. **Market Phase**: 현재 시장 사이클과 Choppy 플래그
   - 배지 형태로 표시: [Bull], [Choppy]

2. **Biggest Rank Change**: 지난주 대비 순위 변화가 가장 큰 상위 3개 섹터
   - 상향 화살표(↑): 순위 상승
   - 하향 화살표(↓): 순위 하락
   - 대시(−): 변화 없음
   - 예: "↑ 반도체 +5" (5계단 상승)

3. **Stage 2 Entry**: 현재 미구현 (주석으로 Stock Explorer 탭 안내)

**데이터 소스**:
- `/api/market/overview` — cycle 정보
- `/api/sectors/ranking` — 각 섹터의 rank_change 값

---

## 탭 2: Sector Analysis (섹터 분석)

### 화면 구성

```
┌────────────────────────────────────────────────────┐
│  TabNavigation: [Market Overview] [Sector ...] ... │
├────────────────────────────────────────────────────┤
│  ContextBar: [Bull] | 반도체, IT | 화학, 금융      │
├────────────────────────────────────────────────────┤
│                                                     │
│  기간 토글: [1W] [1M] [3M]                          │
│                                                     │
│  ┌─ SectorRankingTable ──────────────────────────┐ │
│  │ Rank │ Sector │ 1W  │ 1M  │ 3M  │ RS Avg│... │ │
│  ├──────┼────────┼─────┼─────┼─────┼───────┼─────┤ │
│  │ 1  ▲ │반도체  │+2.1 │+3.5 │+5.2 │ 75  │... │ │
│  │ 2  ▼ │IT     │+1.8 │+2.1 │+3.0 │ 72  │... │ │
│  │ 3  − │화학   │-0.5 │+1.2 │+0.8 │ 50  │... │ │
│  │ ... │       │     │     │     │     │    │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  (섹터를 선택하면 상세 패널 표시)                   │
│                                                     │
│  ┌─ SectorDetailPanel (반도체 선택 시) ───────────┐ │
│  │ 반도체                                         │ │
│  │                                                 │ │
│  │ 1W 초과수익률: ████░░░░░░ +2.1%                │ │
│  │ 1M 초과수익률: ██████░░░░ +3.5%                │ │
│  │ 3M 초과수익률: █████████░ +5.2%                │ │
│  │                                                 │ │
│  │ RS Avg: 75  │ RS Top %: 45% │ 52W High: 30% │ │
│  │ Stage2 %: 35│ Composite: 68 │ 종목수: 35   │ │
│  │                                                 │
│  │ 서브섹터 분석 - 향후 업데이트에서 제공          │ │
│  └────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

### 컴포넌트별 기능

#### SectorRankingTable (섹터 순위 테이블)

**컬럼 설명**:
| 컬럼 | 설명 |
|------|------|
| Rank | 순위 (1-20) + 순위 변화 화살표 (▲상향, ▼하향, −동일) |
| Sector | 섹터명 (산업명(대)) |
| 1W | 1주간 초과수익률 (KOSPI 대비) |
| 1M | 1개월 초과수익률 |
| 3M | 3개월 초과수익률 |
| RS Avg | 섹터 내 종목들의 평균 Relative Strength 점수 (0-100) |
| RS Top % | RS 점수가 80 이상인 종목의 비율 (%) |
| 52W High % | 52주 신고가 근처인 종목의 비율 (%) |
| Stage 2 % | Stage 2(상승) 상태의 종목 비율 (%) |

**정렬 기능**:
- 모든 컬럼 헤더 클릭 가능
- 같은 컬럼 다시 클릭 시 정렬 방향 토글 (오름차순 ↔ 내림차순)
- 현재 정렬 컬럼의 헤더에 화살표 표시

**색상 코딩**:
- **수익률 컬럼** (1W, 1M, 3M): 초록(양수) ~ 빨강(음수)의 배경색
  - 양수일수록 진한 초록색
  - 음수일수록 진한 빨강색

- **비율 컬럼** (RS Avg, RS Top %, 52W High %, Stage 2 %): 파란색 투명도
  - 값이 클수록 짙은 파란색 배경

**클릭 동작**:
- 섹터 행을 클릭하면 하단에 SectorDetailPanel이 나타남
- 이미 선택된 섹터를 다시 클릭하면 선택 해제

**데이터 소스**: `/api/sectors/ranking`
```json
{
  "date": "2024-01-01",
  "sectors": [
    {
      "name": "반도체",
      "stock_count": 35,
      "returns": { "w1": 2.1, "m1": 3.5, "m3": 5.2 },
      "excess_returns": { "w1": 2.1, "m1": 3.5, "m3": 5.2 },
      "rs_avg": 75,
      "rs_top_pct": 45,
      "nh_pct": 30,
      "stage2_pct": 35,
      "composite_score": 68,
      "rank": 1,
      "rank_change": -2
    },
    ...
  ]
}
```

#### SectorDetailPanel (섹터 상세 패널)

**표시 내용**:

1. **섹터명**: 선택된 섹터 이름 (예: "반도체")

2. **초과수익률 비교 바**: 3개 기간의 초과수익률을 막대 그래프로 시각화
   - 1W 막대
   - 1M 막대
   - 3M 막대
   - 양수=초록, 음수=빨강색으로 색상 구분
   - 옆에 정확한 % 값 표시

3. **메트릭 카드 그리드**: 6개의 메트릭을 카드 형태로 표시
   - RS Avg (예: 75)
   - RS Top % (예: 45%)
   - 52W High % (예: 30%)
   - Stage 2 % (예: 35%)
   - Composite Score (예: 68)
   - Stock Count (예: 35)

4. **서브섹터 분석 안내**: "서브섹터 분석은 향후 업데이트에서 제공 예정"

**기간 토글 동작**:

toolbar의 기간 토글 ([1W], [1M], [3M])을 클릭하면:
- 테이블이 초과수익률 값으로 자동 재정렬
- 상세 패널의 값이 선택된 기간으로 업데이트

**데이터 소스**: `/api/sectors/ranking` (위와 동일)

---

## 탭 3: Stock Explorer (종목 탐색)

### 화면 구성

```
┌────────────────────────────────────────────────────┐
│  TabNavigation: [Market Overview] [Sector ...] ... │
├────────────────────────────────────────────────────┤
│  ContextBar: [Bull] | 반도체, IT | 화학, 금융      │
├────────────────────────────────────────────────────┤
│                                                     │
│  필터: [반도체] ×        선택됨: 2개  [View Charts] │
│                                                     │
│  ┌─ StageDistributionBar ─────────────────────────┐ │
│  │ [S1 45] ████    [S2 120] ██████████            │ │
│  │ [S3 80] █████   [S4 155] ████████████          │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ StockTable ───────────────────────────────────┐ │
│  │ ☐ │ Name  │ Market │ Stage │ RS │ 1M% │ Vol  │ │
│  ├───┼───────┼────────┼───────┼────┼─────┼──────┤ │
│  │ ☑ │ 삼성전│ KOSPI │ S2+  │ 85 │+4.2│ 1.5 │ │
│  │ ☑ │ SK하이│ KOSPI │ S2   │ 72 │+2.1│ 1.2 │ │
│  │ ☐ │ LG전자│ KOSPI │ S2   │ 68 │+1.5│ 0.9 │ │
│  │ ☐ │ 현대차│ KOSPI │ S3   │ 55 │-0.5│ 0.8 │ │
│  │ ... │    │       │       │    │    │     │ │
│  └────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

### 컴포넌트별 기능

#### StageDistributionBar (Stage 분포 막대)

**동작 방식**:
- 전체 시장의 Stage 1/2/3/4 종목 분포를 가로 막대로 표시
- 각 세그먼트의 너비는 비율에 따라 조정

**세그먼트 정보**:
- [S1 45] — Stage 1: 45개 종목
- [S2 120] — Stage 2: 120개 종목
- [S3 80] — Stage 3: 80개 종목
- [S4 155] — Stage 4: 155개 종목

**클릭 필터링**:
- 특정 Stage 세그먼트를 클릭하면 StockTable이 해당 Stage만 표시
- 이미 활성화된 Stage를 다시 클릭하면 필터 해제 (토글)

**색상**:
- S1 (Base): 노란색
- S2 (Advance): 초록색
- S3 (Top): 주황색
- S4 (Decline): 빨강색

**데이터 소스**: `/api/stage/overview`
```json
{
  "distribution": {
    "stage1": 45,
    "stage2": 120,
    "stage3": 80,
    "stage4": 155,
    "total": 400
  }
}
```

#### StockTable (종목 테이블)

**컬럼 설명**:
| 컬럼 | 설명 |
|------|------|
| 체크박스 | 종목 다중 선택 (View Charts 버튼 활성화) |
| Name | 종목명 (예: "삼성전자") |
| Market | KOSPI 또는 KOSDAQ |
| Stage | Stage 배지 (S1/S2/S2+/S3/S4) |
| RS | Relative Strength 점수 (0-100) |
| 1M% | 1개월 수익률 (%) |
| Vol Ratio | 부피 비율 (거래량 / 평균거래량) |

**Stage 배지 색상 및 의미**:
- **S1** (노란색): Base 단계, 정체 또는 상승 준비 중
- **S2** (초록색): Advance 단계, 상승 추세
- **S2+** (진한 초록색, 별 아이콘): Stage 2 Entry 후보
  - 다음 6가지 조건을 모두 만족:
    1. Stage 2 분류
    2. 주가 > SMA50 프록시
    3. 주가 > SMA200 프록시
    4. SMA50 > SMA200 (골든크로스)
    5. 거래량 > 평균거래량 × 1.5
    6. RS 점수 >= 70
- **S3** (주황색): Top 단계, 상승 모멘텀 약화 신호
- **S4** (빨강색): Decline 단계, 하락 추세

**정렬 기능**:
- 모든 컬럼 헤더 클릭 가능
- 현재 정렬 방향 표시 (▲ 오름차순, ▼ 내림차순)

**필터링**:
- **Stage 필터**: StageDistributionBar에서 Stage 선택 시 해당 Stage만 표시
- **Sector 필터**: Sector Analysis 탭에서 클릭 후 이동 시 자동 적용
  - 필터 칩으로 표시되며, × 버튼으로 해제 가능

**다중 선택**:
- 체크박스로 여러 종목 선택 가능
- 선택된 종목 수는 우상단에 표시
- View Charts 버튼이 활성화됨

**데이터 소스**: `/api/stage/overview`
```json
{
  "stage2_candidates": [
    {
      "code": "005930",
      "name": "삼성전자",
      "market": "KOSPI",
      "sector_major": "반도체",
      "sector_minor": "반도체",
      "stage": "2",
      "stage_detail": "Stage 2 Entry",
      "rs_12m": 85,
      "chg_1m": 4.2,
      "volume_ratio": 1.5,
      "close": 70000,
      "sma50": 68000,
      "sma200": 65000
    },
    ...
  ]
}
```

#### View Charts 버튼

**위치**: 우상단 toolbar

**활성화 조건**: 체크박스로 최소 1개 이상의 종목 선택

**동작**:
- 클릭하면 선택된 종목 목록을 Chart Grid 탭으로 전달
- Chart Grid 탭으로 자동 이동
- 선택된 종목들의 차트가 차트 그리드에 나타남

---

## 탭 4: Chart Grid (차트 그리드)

### 현재 기능

**상태**: 기존 Chart Grid 탭의 기능은 변경 없음

**표시 내용**:
- 선택된 종목들의 기술적 분석 차트 (Lightweight Charts)
- 필터바로 종목 검색 및 필터링
- 우측 사이드바에 종목 목록

### SPEC-TOPDOWN-001E 개선사항 (향후 구현)

**Stage/RS 배지 추가**:
- 각 차트 셀 헤더에 Stage 배지 추가 (S1/S2/S2+/S3/S4)
- RS 점수 숫자 표시
- Stock Explorer와 동일한 색상 코딩

---

## 탭 간 연동 (Cross-Tab Navigation)

### Market Overview → Sector Analysis

**트리거**: Market Overview 탭의 MiniHeatmap에서 섹터 셀 클릭

**동작**:
1. Sector Analysis 탭으로 자동 전환
2. 클릭한 섹터가 SectorRankingTable에서 하이라이트
3. SectorDetailPanel이 자동으로 열려 해당 섹터의 상세정보 표시

**예시**: "반도체" 셀 클릭 → Sector Analysis 탭 활성화, 반도체 행 선택, 상세 패널 표시

---

### Sector Analysis → Stock Explorer

**트리거**: Sector Analysis 탭의 SectorDetailPanel에서 서브섹터/종목 클릭 (향후 구현)

**현재 상태**: 서브섹터 분석은 아직 구현되지 않음 (향후 SPEC에서 추가 예정)

---

### Stock Explorer → Chart Grid

**트리거**: Stock Explorer 탭의 StockTable에서 종목 선택 후 View Charts 버튼 클릭

**동작**:
1. 선택된 종목 코드 리스트를 Chart Grid로 전달
2. Chart Grid 탭으로 자동 전환
3. 전달된 종목들의 차트가 차트 그리드에 렌더링

**예시**:
1. 삼성전자(005930), SK하이닉스(000660) 체크박스 선택
2. View Charts 클릭
3. Chart Grid 탭에서 두 종목의 차트가 나란히 표시

---

## 백엔드 API 엔드포인트

### GET /api/market/overview
**응답 요약**:
```
{
  kospi: {
    close: 현재가,
    chg_1w: 주간 변화율,
    sma50, sma200, sma50_slope, sma200_slope
  },
  kosdaq: { ... (같은 구조) },
  breadth: {
    kospi: {
      pct_above_sma50: SMA50 위 종목 비율,
      pct_above_sma200: SMA200 위 종목 비율,
      nh_nl_ratio: 신고가/신저가 비율,
      nh_nl_diff: 신고가 - 신저가,
      ad_ratio: 상승/하락 비율,
      breadth_score: 종합 점수 (0-100)
    },
    kosdaq: { ... (같은 구조) }
  },
  cycle: {
    phase: "bull" | "sideways" | "bear",
    choppy: boolean,
    criteria: [ ... 6개 기준의 결과 ],
    confidence: 신뢰도 (0-100)
  },
  breadth_history: [
    {
      date: "YYYY-MM-DD",
      pct_above_sma50, breadth_score, nh_nl_ratio
    },
    ... (최근 12주 데이터)
  ]
}
```

**갱신 주기**: 주 1회 (매주 금요일 이후)

---

### GET /api/sectors/ranking
**응답 요약**:
```
{
  date: "YYYY-MM-DD",
  sectors: [
    {
      name: "반도체",
      stock_count: 35,
      returns: { w1, m1, m3 },
      excess_returns: { w1, m1, m3 },
      rs_avg: 평균 RS 점수,
      rs_top_pct: RS>=80 비율,
      nh_pct: 52주 신고가 비율,
      stage2_pct: Stage 2 비율,
      composite_score: 종합 점수,
      rank: 현재 순위,
      rank_change: 4주 전 순위 대비 변화
    },
    ... (모든 섹터)
  ]
}
```

**갱신 주기**: 주 1회

---

### GET /api/stage/overview
**응답 요약**:
```
{
  distribution: {
    stage1: 45,
    stage2: 120,
    stage3: 80,
    stage4: 155,
    total: 400
  },
  by_sector: [
    {
      sector: "반도체",
      stage1: 5, stage2: 20, stage3: 5, stage4: 5
    },
    ... (모든 섹터)
  ],
  stage2_candidates: [
    {
      code: "005930",
      name: "삼성전자",
      market: "KOSPI",
      sector_major: "반도체",
      sector_minor: "반도체",
      stage: "2",
      stage_detail: "Stage 2 Entry",
      rs_12m: 85,
      chg_1m: 4.2,
      volume_ratio: 1.5,
      close: 70000,
      sma50: 68000,
      sma200: 65000
    },
    ... (모든 Stage 2 후보)
  ]
}
```

**갱신 주기**: 주 1회

---

## 미구현 / 향후 구현 예정

### SPEC-TOPDOWN-001D 내 미완료 항목

- **Sector Detail Panel의 서브섹터 분석**:
  - 현재: "향후 업데이트에서 제공" 안내 메시지만 표시
  - 향후: 산업명(중) 레벨로 드릴다운하여 상세 분석 추가 예정

- **Sector Detail Panel의 Top 5 Stocks**:
  - 현재 미구현
  - 향후: RS 순위로 정렬한 섹터 내 상위 5개 종목 표시 예정

### SPEC-TOPDOWN-001E 내 미완료 항목

- **Stage 2 Entry 스타의 정확한 조건 검증**:
  - 현재: 6가지 기준을 기반으로 필터링하여 후보 반환
  - UI에서 별 배지로 표시 (향후 구현)

### Phase 2 로드맵

| SPEC | 기능 | 설명 |
|------|------|------|
| SPEC-TOPDOWN-002A | RRG (Relative Rotation Graph) | 4분면 회전 그래프로 섹터 momentum 시각화 |
| SPEC-TOPDOWN-002B | Sector RS Trend Chart | 섹터별 RS 추이 12주 선차트 |
| SPEC-TOPDOWN-002C | Full-size Treemap Heatmap | Finviz 스타일의 대형 섹터 히트맵 |

---

## 마크업 및 스타일 참고

### 주요 CSS 클래스

**탭 관련**:
- `.tab-navigation` — 탭 버튼 컨테이너
- `.tab-btn`, `.tab-btn--active` — 개별 탭 버튼
- `.tab-content` — 각 탭의 콘텐츠 (display: none/flex로 토글)

**시장 개요 탭**:
- `.market-overview` — 전체 컨테이너
- `.market-phase-card` — KOSPI/KOSDAQ 정보 카드
- `.phase-badge`, `.phase-badge--bull/--sideways/--bear` — 시장 사이클 배지
- `.breadth-chart` — Lightweight Charts 컨테이너
- `.mini-heatmap` — 섹터 히트맵 그리드
- `.weekly-highlights` — 주간 주목 섹션

**섹터 분석 탭**:
- `.sector-analysis` — 전체 컨테이너
- `.period-toggle` — 기간 선택 버튼 그룹
- `.sector-ranking-table` — 섹터 순위 테이블
- `.sector-detail-panel` — 상세 패널

**종목 탐색 탭**:
- `.stock-explorer` — 전체 컨테이너
- `.stage-distribution-bar` — Stage 분포 막대
- `.stage-distribution-segment`, `.stage-segment--s1/--s2/--s3/--s4` — 개별 Stage 세그먼트
- `.stock-table` — 종목 테이블
- `.stage-badge--s1/--s2/--s2-strong/--s2-entry/--s3/--s4` — Stage 배지 스타일

---

## 주의사항

### 데이터 갱신
- 모든 API 응답은 주간 주기로 갱신됨 (매주 금요일 이후)
- 프론트엔드는 1시간 TTL의 stale-while-revalidate 캐싱 사용

### Cross-Tab Navigation 상태 관리
- TabContext의 `crossTabParams` 객체로 탭 간 파라미터 전달
- 파라미터 수신 후 `clearCrossTabParams()` 호출하여 정리

### 성능 최적화
- 각 탭의 컴포넌트는 마운트된 상태로 유지 (display: none/block으로 토글)
- Lightweight Charts는 ResizeObserver로 반응형 처리
- 대량 테이블 데이터는 가상 스크롤 고려 (현재: 종목 목록이 많을 경우)

---

**문서 버전**: 1.0
**최종 수정**: 2024-01-15
**담당 팀**: Top-Down Market Analysis Team
