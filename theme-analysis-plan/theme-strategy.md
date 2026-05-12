# 네이버 테마 분석 — 투자자 관점 융합 전략 (Functional & Design)

> 본 문서는 구현 계획이 아니라 **융합 전략**이다. 실제 SPEC/구현은 별도 `/moai plan`으로 진행된다.
>
> 본 문서의 목적: "네이버 테마 데이터를 어디에·어떤 모습으로 박아 넣을 때 투자자가 가장 많이 쓸 것인가" 에 대한 합의를 만들고, `/moai plan`에 들어갈 BRIEF의 입력값을 확정한다.

---

## 1. Context — 왜 지금 테마 레이어인가

### 1.1 현재 앱이 답해주는 질문 (4-tab 구조)

| 탭 | 답해주는 질문 | 데이터 소스 |
| --- | --- | --- |
| Market Overview | "장 전체 분위기는?" | 마켓 지표, breadth, treemap heatmap, weekly highlights |
| Sector Analysis | "**산업군** 중 어디가 우위인가?" | KRX 표준 산업 분류 (구조적·정적) |
| Stock Explorer | "내 조건에 맞는 종목은?" | 스크리닝 (재무·기술 필터) |
| Chart Grid | "이 종목들 차트를 동시에 보자" | OHLCV + MA |

### 1.2 현재 앱이 못 답하는 질문 (= 테마가 채울 빈자리)

투자자(Jungwon) 관점에서 누락된 질문들:

- **"오늘 시장이 무슨 *내러티브*로 움직이는가?"** — 산업 분류로는 안 보임 (LS, 가온전선, 대한전선이 동반 +10%? → 산업이 아니라 "AI 데이터센터 전력 수요 → 전선주" 내러티브)
- **"이 강세는 단발성인가, 3일 연속인가?"** — 네이버 테마는 1일/3일 등락률을 동시 제공
- **"내 관심 종목이 지금 어떤 테마에 묶여 있는가?"** — 종목 단독 차트로는 안 보임
- **"여러 테마에 걸친 종목은 무엇인가? (= 시장 컨센서스)"** — 다중 테마 등장은 강한 신호
- **"왜 이 종목이 이 테마인가?"** — 네이버 상세 페이지의 **편입사유** 텍스트가 즉답

**결론**: 테마 = "**시장 내러티브 레이어**". Sector Analysis(구조)와는 보완재이지 대체재가 아니다.

### 1.3 Sector vs Theme — 명확한 포지셔닝

| 축 | Sector Analysis (기존) | Theme Analysis (신규) |
| --- | --- | --- |
| 정의 | KRX 표준 산업 분류 | 시장 내러티브 (테마주, 모멘텀 그룹) |
| 안정성 | 정적 (한 종목 = 한 산업) | 동적 (한 종목이 여러 테마, 내일 바뀜) |
| 갱신 | 분기/연 | 일간 (장 중 의미 있음) |
| 분석 도구 | RRG, Bump Chart, Bubble Chart | 모멘텀 랭킹, 주도주, 멀티테마 교집합 |
| 사용자 의도 | "장기 섹터 로테이션 추적" | "오늘 핫한 내러티브 포착" |

이 두 레이어를 **혼동하지 않게** 분리한다. UI에서도 명확히 분리(별도 탭).

---

## 2. Investor JTBD (Jobs-To-Be-Done) — 5개 시나리오

각 시나리오에 우선순위를 매기고, 어디서 어떤 컴포넌트로 답할지 결정한다.

### JTBD-1 (P0) "지금 강한 테마 Top 10이 뭐야?"

- 트리거: 장 중 또는 마감 직후
- 만족 기준: 1초 안에 강세 테마 상위와 등락률을 본다
- 컴포넌트: **Theme Heatmap / Theme Ranking Table** (신규)

### JTBD-2 (P0) "이 테마 안에서 누가 끌고 가?"

- 트리거: 강세 테마를 클릭한 다음
- 만족 기준: 주도주 1\~3개와 그 종목의 편입사유를 즉시 확인
- 컴포넌트: **Theme Detail Panel** (주도주 카드 + 편입사유 툴팁)

### JTBD-3 (P1) "이 종목은 지금 어떤 테마에 들어가 있어?"

- 트리거: Stock Explorer/Chart Grid에서 종목을 보던 중
- 만족 기준: 종목 카드/차트 옆에 현재 소속 테마 칩(chip) 노출, 클릭 시 해당 테마로 이동
- 컴포넌트: **ThemeChips (재사용 가능한 작은 컴포넌트)**

### JTBD-4 (P1) "여러 테마에 동시 등장하는 종목은? (강한 신호)"

- 트리거: 핫 종목 발굴
- 만족 기준: 2개 이상 테마에 등장하는 종목 리스트 + 등장 테마 표시
- 컴포넌트: **Multi-Theme Stocks Widget** (Market Overview 또는 Theme Analysis 탭 내)

### JTBD-5 (P2) "오늘 새로 부상한 테마는? (어제와 비교)"

- 트리거: 데일리 루틴
- 만족 기준: 어제 대비 모멘텀 점수 변화량 큰 테마 표시 (이건 시계열 누적 필요 → V2)
- 컴포넌트: **Rising Themes Banner** (Market Overview 상단)
- **주의**: 본 모듈은 stateless이므로 V1에서는 불가. V2에서 호출자(상위 시스템)가 누적해야 함.

---

## 3. 기능 융합 지점 — 4-tab 구조에 어떻게 박아 넣는가

### 3.1 새 탭 추가: **Theme Analysis** (P0)

현재 `TabNavigation`에 5번째 탭 추가:

```
[Market Overview] [Sector Analysis] [Theme Analysis] [Stock Explorer] [Chart Grid]
```

위치: Sector Analysis 옆 (개념적 인접). `frontend/src/components/TabNavigation/TabNavigation.tsx`의 `TABS` 배열에 한 줄 추가.

**Theme Analysis 탭 내부 레이아웃** (Sector Analysis 패턴 모방):

```
┌────────────────────────────────────────────────────────┐
│ ContextBar (공통 - 이미 있음)                            │
├──────────────────┬─────────────────────────────────────┤
│ Theme Ranking    │  Theme Detail Panel                  │
│ Table            │                                       │
│ (좌측 30%)       │  - 선택된 테마 메타                   │
│                  │  - momentum_score, breadth_ratio      │
│ - 강세 테마 N개  │  - 주도주 카드 3개 (rank 1~3)        │
│ - change_pct     │    · 종목명 / 등락률 / 거래대금       │
│ - change_pct_3d  │    · 편입사유 (말풍선/툴팁)           │
│ - up/flat/down   │  - 전체 종목 테이블 (등락률 정렬)     │
│ - 테마 칩 클릭   │                                       │
│   → 우측 갱신    │  - "차트로 보기" 버튼                  │
│                  │    → Chart Grid 탭으로 이동           │
│                  │      (선택 종목 코드 prefilled)       │
└──────────────────┴─────────────────────────────────────┘
                                     │
                  ┌──────────────────▼───────────────────┐
                  │ Multi-Theme Stocks Widget (하단)      │
                  │ - 2개 이상 테마에 등장하는 종목들     │
                  │ - 종목명 + theme_count + theme_names  │
                  └───────────────────────────────────────┘
```

**Sector Analysis 컴포넌트와의 평행 구조**:

| Sector | Theme |
| --- | --- |
| `SectorRankingTable.tsx` | `ThemeRankingTable.tsx` (신규, 동일 패턴) |
| `SectorDetailPanel.tsx` | `ThemeDetailPanel.tsx` (신규, 동일 패턴) |
| `SectorBubbleChart.tsx` | `ThemeBubbleChart.tsx` (V2 — momentum vs breadth 산점도) |
| `BumpChart.tsx` (랭킹 변동) | `ThemeBumpChart.tsx` (V2 — 시계열 누적 필요) |

**즉, V1은 RankingTable + DetailPanel 두 컴포넌트만 만들면 됨.**

### 3.2 기존 탭에 위젯 침투 (P1)

#### Market Overview 탭

- `HotThemesStrip.tsx` (신규, 한 줄 가로 스트립): 상단 "오늘의 핫 테마 Top 5" + 등락률 칩
  - 클릭 시 Theme Analysis 탭으로 cross-tab 이동 (TabContext의 `crossTabParams` 패턴 재사용)
  - 위치: `MarketOverview.tsx`의 `WeeklyHighlights` 위/아래
  - 새로고침 버튼: 우측에 작게 (온디맨드 강조)

#### Stock Explorer / Chart Grid 탭

- `ThemeChips.tsx` (신규, 작은 칩 컴포넌트): 종목 카드/리스트 행에 부착
  - 종목코드 → 소속 테마 1\~3개 (멀티테마 우선) 칩으로 표시
  - 칩 클릭 → Theme Analysis 탭으로 이동, 해당 테마 자동 선택
  - 데이터: `result.stocks_df`를 `stock_code` 기준 reverse index → `{stock_code: [theme_names]}` (프론트 메모이제이션)
- **위치 예시**: `StockList/StockItem.tsx`의 종목명 옆 작은 회색 칩

#### Sector Analysis 탭

- **무 변경 권장**: 섹터와 테마는 다른 축. 섹터 안에 테마를 끼워 넣으면 의미가 흐려진다.

### 3.3 ContextBar 통합

상단 ContextBar에 "Last theme refresh: 13:24 KST" 같은 메타 정보 작게 추가. 자동 갱신 안 됨을 명시.

### 3.4 백엔드 라우터 (개념만)

API 노출 형태 (구현은 `/moai plan`에서 결정):

| Endpoint | 용도 | JTBD |
| --- | --- | --- |
| `GET /api/themes/snapshot` | 5종 DataFrame 한 번에 | JTBD-1, 2, 4 |
| `GET /api/themes/quick` | `skip_details=True` 빠른 모드 (10초↓) | Market Overview HotThemesStrip 초기 로드 |
| `GET /api/themes/by-stock/{code}` | 종목 → 소속 테마 (서버측 reverse index) | JTBD-3 (ThemeChips) |

---

## 4. 데이터 전략 — 무엇을 *수집*하고 무엇을 *재사용*하는가

### 4.1 네이버에서 가져오는 것 (필수만)

| 필드 | 용도 |
| --- | --- |
| theme_id, theme_name | 테마 식별 |
| change_pct, change_pct_3d | 강세 판단 (momentum_score 입력) |
| up_count, flat_count, down_count | breadth_ratio 입력 |
| top_stocks_preview | 미리보기 |
| stock_code, stock_name | 종목 식별 |
| price, change, change_pct | 일중 등락 |
| volume, trade_value | 자금 흐름 |
| **inclusion_reason** (편입사유) | UX 차별화 — 툴팁/말풍선 |

### 4.2 네이버에서 *가져오지 않는 것*

- ❌ 시가총액 → **본 프로젝트 시작 시 이미 보유** (DB에 master 테이블 존재). `stock_code` JOIN으로 충분.
- ❌ PER, ROE → 본 프로젝트의 `analysis_service`/재무 데이터 활용. 원하면 ThemeDetailPanel에서 재무 탭으로 cross-link.
- ❌ ROE → 영구 미사용 (네이버 종목 메인에도 노출 안 됨, 재무는 별도 경로).

### 4.3 leader_score 공식 — 시총을 *기존 DB에서* 가져온다는 가정으로 유지

원 스펙: `z(change_pct)*0.40 + z(volume)*0.30 + z(market_cap)*0.20 + z(trade_value)*0.10`

선택지 (`/moai plan`에서 확정):

- **A안 (권장)**: 기존 시총 DB JOIN — 공식 그대로. 추가 크롤링 0회. 대형주 리더십 반영.
- **B안**: market_cap 가중치 제거 후 재분배 → `z(change)*0.50 + z(volume)*0.35 + z(trade_value)*0.15`. 단순.
- **C안**: 거래대금 = 가격×거래량이라 사실상 중복 → `z(change)*0.50 + z(volume)*0.30 + z(market_cap_DB)*0.20`로 재구성.

→ **A안 권장**: 본 프로젝트의 강점(시총 DB 보유)을 활용. 네이버 추가 호출 없음.

### 4.4 외부 호출 횟수 (시총 미보강 기준)

- 테마 목록: 7페이지 = **7회**
- 강세 테마 상세: top_n_themes=20 → **20회**
- 시총 보강: **0회** (DB JOIN)
- **합계 27회 / 약 19초** (sleep 0.7s 기준). `skip_details=True`이면 **7회 / 약 5초**로 R10 충족.

→ 원래 80회였던 것을 **1/3로 단축**. 매너 크롤링(R3)·안정성·UX 응답성 모두 개선.

### 4.5 무엇을 캐시할까

본 모듈은 stateless(R1)지만, 호출자(FastAPI 라우터)에서:

- **장 마감 후 결과**: 1시간 캐시 (장중 내러티브 변화 적음)
- **장 중 결과**: 5분 캐시 (네이버 부하 줄이고, 사용자 새로고침 클릭 비용 0)
- `/api/themes/by-stock/{code}`: 서버 메모리에 reverse index 캐시 (TTL = snapshot 캐시와 동일)

캐시 구현은 본 모듈 책임이 아닌 라우터 레이어 책임 → R7 준수.

---

## 5. UX/Design 융합 원칙

### 5.1 시각 언어

- **온디맨드성 강조**: 자동 갱신 안 됨. "🔄 Refresh" 버튼을 **눈에 띄게**, 마지막 갱신 시각을 항상 노출. 사용자가 "이건 라이브가 아니다"를 즉시 인지하도록.
- **모멘텀 색상**: 등락률 → 빨강(상승)/파랑(하락) **한국 시장 관행** 준수. Sector Analysis의 색 토큰과 일관성 유지.
- **편입사유 = 차별화**: 모든 종목 카드에 작은 (i) 아이콘 → 호버/클릭 시 편입사유 말풍선. **이 한 가지가 다른 앱과의 가장 큰 차이.**
- **테마 칩**: 작고 둥근 pill 형태, 회색 배경 + 테마명. 등락률에 따라 살짝 배경색 변화(Hot 테마는 옅은 빨강 톤).

### 5.2 인터랙션 패턴 — 기존 cross-tab 재사용

`TabContext.crossTabParams` 메커니즘이 이미 있음 (`AppContent.tsx:23` — chart-grid로 stockCodes 넘기는 패턴). 이를 그대로 활용:

```
ThemeRankingTable 행 클릭   → ThemeDetailPanel 갱신 (탭 내부)
ThemeDetailPanel "차트로"   → Chart Grid 탭으로 (stockCodes prefilled)
ThemeChips 클릭             → Theme Analysis 탭으로 (theme_id prefilled)
HotThemesStrip 항목 클릭    → Theme Analysis 탭으로 (theme_id prefilled)
```

`crossTabParams`에 `themeId?: number` 필드 추가 한 줄이면 끝.

### 5.3 빈 상태 / 에러 상태

- 빈 themes_df: "지금은 강세 테마가 없어요. 잠시 후 다시 시도해 주세요." + Refresh 버튼 (정상적인 약세장 대응)
- `metadata.errors > 0`: 상단에 작은 노란 배지 "일부 테마 수집 실패 (N건)" + 클릭 시 상세 에러 모달
- 전체 실패 (네이버 차단 등): 친절한 메시지 + 재시도 버튼. 다른 탭은 영향 없음.

### 5.4 모바일 대응

- ThemeRankingTable + ThemeDetailPanel 좌우 분할은 데스크톱만. 모바일은 ranking → tap → detail 풀스크린 전환.
- ThemeChips는 한 줄 horizontal scroll로 처리.
- 네이버 크롤링 응답 시간(약 19초)은 모바일에서 더 큰 페인포인트 → `skip_details=True` 빠른 모드 우선 사용.

### 5.5 접근성

- 등락률 색상에만 의존하지 말고 +/- 부호 명시 (색맹 대응).
- 테마 칩은 `<button>` 의미요소 + aria-label.
- 편입사유 툴팁은 키보드 포커스로도 열림.

---

## 6. 단계별 출시 (Phasing)

### V1 (MVP) — `/moai plan`의 첫 SPEC 범위

**Backend**:

- `backend/services/naver_theme/` 모듈 (5단계 흐름 중 1\~2단계 + DB JOIN)
- `backend/routers/themes.py` 2 엔드포인트: `/snapshot`, `/quick`
- 시총은 DB JOIN, PER/ROE 미사용

**Frontend**:

- 새 탭 "Theme Analysis"
- `ThemeRankingTable` + `ThemeDetailPanel` 2 컴포넌트
- 편입사유 툴팁
- "차트로 보기" cross-tab

**검증**:

- skip_details=True &lt; 10초 (R10)
- 한글 비깨짐
- 부분 실패 허용

### V1.5 — 침투 위젯

- Market Overview에 `HotThemesStrip` (Top 5)
- Stock Explorer/Chart Grid에 `ThemeChips`
- `/api/themes/by-stock/{code}` 엔드포인트
- `crossTabParams.themeId` 추가

### V2 — 시계열·심화

- 호출자 측 일별 누적 저장 (parquet/sqlite)
- "어제 대비 부상한 테마" Banner
- `ThemeBumpChart` (시간대별 모멘텀 변화)
- `ThemeBubbleChart` (momentum × breadth 산점도)
- 멀티테마 종목의 등장 빈도 누적 (강한 신호 가중치)

### V3 — AI 연계

- 기존 `ai_report_service` 활용: "오늘 강세 테마 3개에 대해 1줄 코멘트" 자동 생성
- Codex/Claude CLI 호출하여 테마 동향 요약 → ContextBar에 띄우기

---

## 7. 위험 / 트레이드오프

| 위험 | 영향 | 완화 |
| --- | --- | --- |
| 네이버 페이지 구조 변경 | 파싱 실패 | live 테스트로 PR 시 회귀 감지, 부분 실패 허용 |
| 테마 = 작전주/세력주 이미지 | 사용자 신뢰도 ↓ | 편입사유 텍스트 노출로 "팩트 기반" 차별화. ETF/대형주 위주 테마 우선 표시 옵션 검토. |
| 정보 과부하 | 4-tab → 5-tab으로 늘어남 | Sector Analysis와 명확한 라벨 구분. 첫 사용 시 가벼운 onboarding 툴팁 |
| 응답 시간 19초 | 사용자 이탈 | `skip_details=True` 빠른 모드 우선, 라우터 레벨 캐시, "Loading 중에도 부분 결과 보여주기" SSE 검토(V2) |
| 멀티 테마 신호의 노이즈 | 작전주가 여러 테마에 동시 편입되는 경우 잘못된 신호 | theme_count + 거래대금 + 시총 필터 결합으로 노이즈 감소 |

---

## 8. `/moai plan`에 들어갈 입력값 (확정 사항)

다음 항목은 본 문서로 확정. `/moai plan`은 이를 SPEC으로 분해할 뿐.

 1. **모듈 위치**: `backend/services/naver_theme/`
 2. **API**: `GET /api/themes/snapshot`, `GET /api/themes/quick`, `GET /api/themes/by-stock/{code}` (V1.5 추가)
 3. **시총**: 기존 DB JOIN, 네이버 추가 호출 0
 4. **PER/ROE**: 미사용 (영구 제외)
 5. **편입사유**: stocks_df에 `inclusion_reason` 컬럼으로 보존
 6. **leader_score 공식**: A안 (원 스펙 가중치 유지, market_cap만 DB JOIN)
 7. **신규 탭**: "Theme Analysis" — Sector Analysis 우측에 배치
 8. **신규 컴포넌트 V1**: `ThemeRankingTable`, `ThemeDetailPanel` (Sector 패턴 미러링)
 9. **침투 위젯 V1.5**: `HotThemesStrip`(MarketOverview), `ThemeChips`(StockList/ChartGrid)
10. **캐싱**: 라우터 레벨 (장중 5분 / 마감후 1시간), 본 모듈은 stateless
11. **응답 직렬화**: 각 DataFrame → records list + Pydantic v2 검증
12. **테스트**: parser/analyzer 단위 + `@pytest.mark.live` 통합 1건
13. **언어**: UI 한국어, 코드 주석 한국어, 식별자 영어

---

## 9. 미해결 — `/moai plan`에서 결정 필요

- **Q1**: 캐시 저장소 (메모리 dict / Redis / sqlite) — 현재 프로젝트에 Redis 있는지 확인 필요
- **Q2**: 종목 master 테이블의 시총 컬럼명·갱신 주기 — `analysis_service` 또는 `screen_service`에 이미 있는지 확인
- **Q3**: 우선주(005935) vs 보통주(005930) 표시 정책 — 칩에 둘 다 노출? 보통주만?
- **Q4**: 모바일 우선 vs 데스크톱 우선 — Theme Analysis 탭 레이아웃 결정
- **Q5**: V2의 시계열 누적은 본 프로젝트의 sqlite/parquet 어디에 둘 것인가
- **Q6**: 네이버 ToS 검토 — 매너 크롤링 0.7초 sleep + 식별 가능한 UA가 충분한 보호인지

---

## 10. 검증 — 본 전략이 "맞는 융합"인가

본 전략이 제대로 작동했다면 다음 사용 패턴이 나와야 한다:

1. ✅ 사용자가 아침에 앱 켜자마자 Market Overview의 HotThemesStrip을 본다 → 1초 안에 오늘의 내러티브 인지
2. ✅ 관심 가는 테마 칩 클릭 → Theme Analysis 탭에서 주도주 3개와 편입사유 즉시 확인 → "왜 강한지" 납득
3. ✅ "차트로 보기" → Chart Grid에서 동시 차트 비교
4. ✅ Stock Explorer에서 발굴한 종목 옆에 ThemeChips 표시 → "아, 이 종목이 그 테마에 묶여 있구나" 인지
5. ✅ Sector Analysis는 그대로 → 장기 섹터 로테이션은 별도로 추적

만약 위 흐름 중 어디에서든 사용자가 "왜 이게 여기 있지?" 또는 "이거 어디서 봐야 하지?"가 나오면 **융합 실패** → 재설계.

---

## 11. 사용 시나리오 (ASCII 다이어그램)

### 11.1 탭 네비게이션 변화

```
[BEFORE]  4-tab
┌─────────────────────────────────────────────────────────────────┐
│ [Market Overview] [Sector Analysis] [Stock Explorer] [Chart Grid]│
└─────────────────────────────────────────────────────────────────┘

[AFTER]   5-tab  ── Theme Analysis 신규 (Sector Analysis 우측)
┌──────────────────────────────────────────────────────────────────────────────────┐
│ [Market Overview] [Sector Analysis] [★ Theme Analysis] [Stock Explorer] [Chart Grid]│
└──────────────────────────────────────────────────────────────────────────────────┘
                                            ↑ 신규
```

### 11.2 Theme Analysis 탭 전체 레이아웃

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ContextBar (공통)                              [🔄 갱신: 13:24 KST] [⚡ Quick]    │
├──────────────────────────────────┬───────────────────────────────────────────────┤
│ ◀─── ThemeRankingTable (30%) ───▶│◀────── ThemeDetailPanel (70%) ──────────────▶│
│                                   │                                                │
│ ┌──────────────────────────────┐ │ 📌 선택: 전선                                  │
│ │ # │ 테마명    │ 1d % │3d %  │ │ ──────────────────────────────────────────────│
│ │───┼───────────┼──────┼──────│ │ momentum: 8.2  │  breadth: 0.78  │ 종목수: 9   │
│ │ 1 │ 전선   ◀──┼ +6.1 │+12.3 │ │                                                │
│ │ 2 │ AI반도체  │ +5.4 │ +8.1 │ │ 🏆 주도주 Top 3                                │
│ │ 3 │ 신재생   │ +4.2 │ +5.5 │ │ ┌──────────────────────────────────────────┐ │
│ │ 4 │ 방산     │ +3.8 │ +4.7 │ │ │ ① LS          +8.24%  거래대금 524억    │ │
│ │ 5 │ 바이오   │ +2.9 │ +6.2 │ │ │   💡 LS그룹 지주, LS전선 자회사 보유 ⓘ  │ │
│ │ . │ ...      │      │      │ │ │ ② 가온전선    +11.29% 거래대금 312억    │ │
│ │   │          │      │      │ │ │   💡 LS그룹 계열 전력케이블 제조     ⓘ  │ │
│ │   │ ▲ 행 클릭→ 우측 갱신    │ │ │ ③ 대한전선    +9.96%  거래대금 285억    │ │
│ └──────────────────────────────┘ │ │   💡 초고압케이블·통신케이블 제조    ⓘ  │ │
│                                   │ └──────────────────────────────────────────┘ │
│                                   │                                                │
│                                   │ 전체 종목 (9건) ─ 등락률순  [📊 차트로 보기] │
│                                   │ ┌──────────────────────────────────────────┐ │
│                                   │ │ KBI메탈   +29.94%  편입사유 ⓘ │ □선택  │ │
│                                   │ │ 대원전선  +14.97%  편입사유 ⓘ │ □선택  │ │
│                                   │ │ ...                                       │ │
│                                   │ └──────────────────────────────────────────┘ │
└──────────────────────────────────┴───────────────────────────────────────────────┘
                                                            │
                                                            ▼  (탭 내부 하단)
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 🔥 멀티테마 종목 (2개 이상 테마에 동시 등장 — 시장 컨센서스 시그널)               │
│ ┌─────────────┬───────┬──────────────────────────────────┬──────────┐            │
│ │ 종목         │ 테마수│ 등장 테마                        │ 평균 1d %│            │
│ ├─────────────┼───────┼──────────────────────────────────┼──────────┤            │
│ │ LS           │  3    │ [전선] [AI반도체] [신재생]       │ +6.5%   │            │
│ │ 한화솔루션   │  2    │ [태양광] [신재생]                  │ +4.1%   │            │
│ │ 삼성SDI      │  2    │ [2차전지] [AI반도체]              │ +3.7%   │            │
│ └─────────────┴───────┴──────────────────────────────────┴──────────┘            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 11.3 시나리오 A — 아침 루틴 (JTBD-1 + JTBD-2)

```
[09:05]  사용자 앱 오픈 → Market Overview 탭 (기본 진입)
   │
   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Market Overview tab                                              │
│                                                                   │
│ 🔥 오늘의 핫 테마 (HotThemesStrip)        [상단 1줄, 5개 칩]      │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │
│ │  전선  │ │AI반도체│ │ 신재생 │ │  방산  │ │ 바이오 │         │
│ │ +6.1% ▲│ │ +5.4% ▲│ │ +4.2% ▲│ │ +3.8% ▲│ │ +2.9% ▲│         │
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘         │
│      │                                                            │
│      │ ←── 사용자 시선 1초                                        │
│      │ ←── 클릭                                                   │
│      ▼                                                            │
│  TreemapHeatmap, BreadthChart, WeeklyHighlights (기존)           │
└──────┼──────────────────────────────────────────────────────────┘
       │
       │  cross-tab navigate (themeId=178)
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Theme Analysis tab — [전선] 자동 선택                            │
│                                                                   │
│ ┌──── Ranking ────┐  ┌──── Detail (전선 자동 강조) ────────────┐│
│ │ ▶ 전선         │  │ momentum: 8.2  breadth: 0.78             ││
│ │   AI반도체     │  │                                            ││
│ │   신재생       │  │ 주도주: LS / 가온전선 / 대한전선          ││
│ │                 │  │ 편입사유 ⓘ 호버 → "LS그룹 지주, ..."     ││
│ │                 │  │                                            ││
│ │                 │  │ [📊 차트로 보기]  ←── 클릭                ││
│ └─────────────────┘  └────────────────────────────────────────┘│
└─────────────────────────────────────────────────┼───────────────┘
                                                   │
                          cross-tab (stockCodes=[006260, 가온전선, 대한전선])
                                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Chart Grid tab — 주도주 3종목 동시 차트                          │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐                    │
│ │   LS       │ │ 가온전선   │ │ 대한전선   │                    │
│ │  +8.24%    │ │  +11.29%   │ │  +9.96%    │                    │
│ │ ▁▂▃▅▇█▇    │ │ ▁▁▂▅▇█▇    │ │ ▁▂▄▅▇▆█    │                    │
│ │ MA20 / 60  │ │ MA20 / 60  │ │ MA20 / 60  │                    │
│ └────────────┘ └────────────┘ └────────────┘                    │
│  → 같은 내러티브 종목 동시 비교 → 매수 후보 압축                 │
└─────────────────────────────────────────────────────────────────┘

총 클릭 3회 / 인지~판단 약 8초 (캐시 hit 가정)
```

### 11.4 시나리오 B — 종목→테마 역참조 (JTBD-3)

```
USER 보유종목 점검 중                Stock Explorer
   │
   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Stock Explorer tab — 스크리닝 결과                                   │
│                                                                       │
│ ┌─────────┬──────────┬─────────┬────────┬──────────────────────────┐│
│ │ 종목    │ 종목명   │ 현재가  │등락률 │ ThemeChips (신규 컴포넌트)││
│ ├─────────┼──────────┼─────────┼────────┼──────────────────────────┤│
│ │ 006260  │ LS       │ 453,000 │ +8.24% │ [전선] [AI반도체][신재생]││
│ │         │          │         │        │   ▲                       ││
│ │         │          │         │        │   │ 클릭                   ││
│ │ 005930  │ 삼성전자 │ 71,500  │ +1.2%  │ [AI반도체]                ││
│ │ 003490  │ 대한전선 │ 56,300  │ +9.96% │ [전선] [우주항공]         ││
│ │ 011170  │ 롯데케미컬│ 52,000 │ -0.8%  │ (없음)                    ││
│ └─────────┴──────────┴─────────┴────────┴──────────────────────────┘│
└─────────────────────────────────────────────────┼───────────────────┘
                                                   │
                       cross-tab (themeId=178, source=stock_explorer)
                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Theme Analysis tab — [전선] 자동 선택                                │
│                                                                       │
│   "왜 LS가 이 테마에 묶여있지?" → 편입사유 즉시 확인                 │
│   "전선 테마 자체는 얼마나 강한가?" → momentum/breadth 확인          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

투자자 가치: 내 관심종목이 어떤 *내러티브*로 움직이는지 1클릭 답변
```

### 11.5 시나리오 C — 멀티테마 발굴 (JTBD-4)

```
USER가 "구조적 강세 시그널"을 찾는 중
   │
   ▼
Theme Analysis tab → 하단으로 스크롤
   │
   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 🔥 멀티테마 종목 위젯 (2개 이상 테마 동시 등장)                       │
│                                                                       │
│ ┌─────────────┬───────┬─────────────────────────────┬──────────┐    │
│ │ LS          │ 3개   │ [전선][AI반도체][신재생]    │  +6.5%   │    │
│ │             │       │   ▲                          │          │    │
│ │             │       │   │ 칩 클릭 → 해당 테마      │          │    │
│ │ 한화솔루션  │ 2개   │ [태양광][신재생]              │  +4.1%   │    │
│ │ 삼성SDI     │ 2개   │ [2차전지][AI반도체]           │  +3.7%   │    │
│ │ 두산에너빌리티│ 2개  │ [원전][방산]                  │  +3.2%   │    │
│ └─────────────┴───────┴─────────────────────────────┴──────────┘    │
│                                                                       │
│ 해석:                                                                 │
│  · LS는 3개 내러티브 동시 = 가장 강한 시장 컨센서스                  │
│  · 작전주(1개 테마 단발)와 구조적 강세 종목(다중 테마) 구분 가능     │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.6 데이터 흐름 (백엔드 ↔ 기존 DB)

```
[프론트엔드 호출 1회]   GET /api/themes/snapshot?top_n=20&leaders_per_theme=3
                              │
                              ▼
                    ┌─────────────────────┐
                    │  라우터 캐시 확인   │
                    └──────────┬──────────┘
                       cache hit│cache miss
                  ┌─────────────┴─────────────┐
                  ▼                            ▼
           즉시 응답                 collect_and_analyze() 호출
           (5분 TTL)                          │
                                              ▼
                          ┌──────────────────────────────────┐
                          │ Stage 1: 테마 목록 N페이지       │
                          │   네이버 호출 7회 (자동 페이지   │ ─┐
                          │   네이션 감지)                    │  │
                          │   → themes_df                     │  │
                          └──────────────────────────────────┘  │
                                              │                  │
                                              ▼                  │
                          ┌──────────────────────────────────┐  │
                          │ build_strong_themes(top_n=20)    │  │ 매너 크롤링
                          │   계산만 (호출 0)                 │  │ sleep 0.7s
                          │   → strong_themes_df              │  │ × 27회
                          └──────────────────────────────────┘  │ ≈ 19초
                                              │                  │
                                              ▼                  │
                          ┌──────────────────────────────────┐  │
                          │ Stage 2: 강세 테마 상세 20개      │  │
                          │   네이버 호출 20회                │ ─┘
                          │   → stocks_df (시총=NaN 임시)     │
                          └──────────────────────────────────┘
                                              │
                                              ▼
              ┌───────────────────────────────────────────────────────┐
              │  JOIN 시총 (네이버 추가 호출 없음)                    │
              │  stocks_df.stock_code  ◀───── 기존 프로젝트 DB       │
              │              ON                                        │
              │  master.stock_code → market_cap                       │
              └───────────────────────────────────────────────────────┘
                                              │
                                              ▼
                          ┌──────────────────────────────────┐
                          │ build_leaders(k=3)                │
                          │   z(change)*0.4 + z(vol)*0.3      │
                          │   + z(market_cap)*0.2             │
                          │   + z(trade_value)*0.1            │
                          │   → leaders_df                     │
                          └──────────────────────────────────┘
                                              │
                                              ▼
                          ┌──────────────────────────────────┐
                          │ build_multi_theme_stocks()        │
                          │   stock_code groupby              │
                          │   theme_count >= 2                │
                          │   → multi_theme_stocks_df         │
                          └──────────────────────────────────┘
                                              │
                                              ▼
              ThemeAnalysisResult { 5 DataFrames + metadata }
                                              │
                                              ▼
              FastAPI 라우터: NaN→None, records list, Pydantic 검증
                                              │
                                              ▼
                            JSON 응답 → 프론트엔드


[skip_details=True 모드]: Stage 1만 → 7회 / ≈ 5초 (R10 충족)
```

---

## 12. Critical Files (참조용 — 수정은 `/moai plan`에서)

기능 융합 시 *수정 또는 참조* 대상:

- `frontend/src/components/TabNavigation/TabNavigation.tsx` — 5번째 탭 추가 위치
- `frontend/src/AppContent.tsx` — 새 탭 컨텐트 마운트 위치
- `frontend/src/contexts/TabContext.tsx` — `crossTabParams.themeId` 추가
- `frontend/src/components/SectorAnalysis/SectorRankingTable.tsx` — `ThemeRankingTable` 패턴 모델
- `frontend/src/components/SectorAnalysis/SectorDetailPanel.tsx` — `ThemeDetailPanel` 패턴 모델
- `frontend/src/components/MarketOverview/MarketOverview.tsx` — `HotThemesStrip` 삽입 위치
- `frontend/src/components/StockList/StockItem.tsx` — `ThemeChips` 부착 위치
- `backend/routers/sectors.py` — `themes.py` 라우터 패턴 모델
- `backend/services/sector_service.py` — 시총 DB JOIN 패턴 확인 (`analysis_service.py`도 후보)
- `backend/main.py` — 라우터 등록 위치
- `theme-analysis-plan/theme-request.md` — 요청 원본 (참조)