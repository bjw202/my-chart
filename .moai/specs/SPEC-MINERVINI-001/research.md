# Mark Minervini 스윙트레이딩 전략 리서치 (기술적 분석)

- SPEC-ID: SPEC-MINERVINI-001
- 작성일: 2026-03-08
- 상태: 리서치 완료
- 목적: 미너비니 SEPA 방법론의 기술적 분석 요소를 한국 주식시장에 적용하기 위한 기초 조사
- 범위: 기술적 분석만 포함 (펀더멘탈 분석은 이 프로젝트에서 다루지 않음)

---

## 1. 스윙트레이더 페르소나: SwingMaster

### 1.1 기본 프로필

| 항목 | 설명 |
|------|------|
| 페르소나 이름 | SwingMaster (스윙마스터) |
| 투자 스타일 | Mark Minervini 스타일 모멘텀 스윙 트레이딩 |
| 매매 주기 | 2주 ~ 3개월 |
| 대상 시장 | KOSPI / KOSDAQ |
| 벤치마크 | KOSPI 지수 |
| 분석 범위 | 기술적 분석 (가격, 거래량, 이동평균, 상대강도) |

### 1.2 투자 철학

- **Stage 2 상승추세 종목만 매매**: 하락 추세나 횡보 구간의 종목은 절대 매수하지 않는다.
- **리더주 집중**: 시장을 이끄는 상대강도(RS) 상위 종목에만 집중한다.
- **최적의 진입점**: VCP(Volatility Contraction Pattern) 패턴의 피봇 포인트에서만 진입한다.
- **엄격한 리스크 관리**: 진입가 대비 -7~8% 손절을 예외 없이 적용한다.
- **소수 정예 포지션**: 3~5개 종목에 집중 투자, 분산보다 확신에 집중한다.
- **시장 환경 필터**: 주요 지수가 하락 추세일 때는 현금 비중을 높인다.

### 1.3 의사결정 프로세스

```
1. 시장 환경 판단 (KOSPI/KOSDAQ 추세 확인)
   ↓
2. Trend Template 8조건 스크리닝 (Stage 2 종목 필터링)
   ↓
3. VCP 패턴 형성 여부 확인 (변동성 수축 + 거래량 감소)
   ↓
4. 피봇 포인트 돌파 시 진입 (거래량 증가 확인)
   ↓
5. 리스크 관리 (손절/익절 규칙 적용)
```

### 1.4 매매 규칙 요약

| 규칙 | 기준 |
|------|------|
| 진입 조건 | Trend Template 8조건 + VCP 피봇 돌파 + 거래량 150%+ |
| 손절 | 진입가 대비 -7~8% 또는 VCP 최종 수축 저점 아래 |
| 익절 | 추세 추종 (이동평균선 이탈 시 또는 목표가 도달) |
| 최대 포지션 | 3~5개 종목 |
| 시장 필터 | KOSPI/KOSDAQ 상승 추세 시에만 매매 |

---

## 2. Mark Minervini 전략 상세

### 2.1 Trend Template (트렌드 템플릿) - 8가지 기술적 조건

Mark Minervini는 저서 *"Think & Trade Like a Champion"*, *"Trade Like a Stock Market Wizard"*에서 주식이 **Stage 2 상승 추세**에 있는지 확인하기 위한 8가지 필수 조건을 제시했다. **하나라도 충족하지 못하면 해당 종목은 후보에서 제외**한다.

| # | 조건 | 구체적 기준 | 비고 |
|---|------|------------|------|
| 1 | 현재가 > 150일 이동평균 AND 200일 이동평균 | 주가가 중/장기 이평선 위에 위치 | 주봉 기준: SMA30 & SMA40 |
| 2 | 150일 이동평균 > 200일 이동평균 | 중기 이평선이 장기 이평선을 상회 | 골든크로스 이후 상태 |
| 3 | 200일 이동평균이 최소 1개월 이상 상승 추세 | 20영업일 전 SMA200 값보다 현재 값이 높아야 함 | 이상적으로 4~5개월 이상 |
| 4 | 50일 이동평균 > 150일 이동평균 AND 200일 이동평균 | 단기 이평선이 중/장기 이평선 모두 상회 | 강한 상승 추세 확인 |
| 5 | 현재가 > 50일 이동평균 | 단기 이평선 위에서 거래 | 눌림목 후 반등 확인 |
| 6 | 현재가 >= 52주 최저가 x 1.25 (25% 이상) | 저점 대비 충분히 상승한 상태 | 30% 이상 권장, 최고의 종목은 100~300%+ |
| 7 | 현재가 >= 52주 최고가 x 0.75 (고점 대비 25% 이내) | 신고가에 가까운 위치 | 고점 돌파 직전이 이상적 |
| 8 | 상대강도(RS) 순위 >= 70 (백분위) | 전체 종목 중 상위 30% 이내의 모멘텀 | 90 이상 강력 선호 |

#### 추가 조건

- **최소 일평균 거래량**: 미국 기준 400,000주 이상 (한국 시장에서는 거래대금 기준 적용 권장)
- **200일 이평 상승 기간**: 짧은 추세에서는 1개월, 긴 추세에서는 5개월 이상 상승해야 함

### 2.2 SEPA (Specific Entry Point Analysis) 방법론 - 기술적 요소

SEPA는 Minervini 전체 트레이딩 시스템의 핵심 프레임워크이다. 이 프로젝트에서는 기술적 분석 요소에 집중한다.

#### 핵심 기술적 구성요소

| 구성요소 | 설명 | 핵심 기준 |
|----------|------|----------|
| **S** - Specific Entry Point | VCP 패턴 완성 후 피봇 포인트 돌파 시점에서 진입 | 거래량 증가 동반 필수 |
| **P** - Price Action | Stage 2 상승 추세 확인 | Trend Template 8조건 충족 |

> 참고: 원래 SEPA에는 Earnings(실적)와 Announcement(촉매) 요소도 포함되지만, 이 프로젝트에서는 기술적 분석만 다루므로 S(진입점)와 P(가격 행동)에 집중한다.

#### 진입 규칙

- 주식이 통합 패턴(consolidation)에서 돌파할 때 진입
- 돌파 시 **거래량 증가** 동반 필수 (평균 대비 최소 150% 이상)
- 여러 지표가 동시에 정렬(align)될 때만 진입
- **최대 손절선: 진입가 대비 -7% ~ -8%** (엄격 적용, 예외 없음)

### 2.3 VCP (Volatility Contraction Pattern) 패턴

VCP는 Minervini의 핵심 차트 패턴으로, 변동성과 거래량이 점진적으로 줄어들면서 **"최소저항선(line of least resistance)"**을 만드는 형태이다.

#### VCP 패턴의 기술적 필수 조건

1. **점진적 수축 (Progressive Contractions)**
   - 각 조정(pullback)의 깊이가 이전보다 작아짐
   - 예시: 1차 수축 20~30% → 2차 수축 10~15% → 3차 수축 5~8%
   - 일반적으로 **2~6번의 수축**으로 구성

2. **거래량 패턴**
   - 조정 시 거래량 감소, 반등 시 거래량 증가
   - 최종 수축 구간에서 거래량이 가장 낮아야 함 (매도 압력 소진 의미)

3. **명확한 피봇 포인트**
   - 최종(가장 타이트한) 수축의 고점이 피봇 포인트
   - 전체 패턴의 고점이 아닌, 마지막 수축의 고점임에 주의

4. **Stage 2 상승 추세 확인**
   - 주가가 50일/150일/200일 이동평균선 위에 위치

5. **상대강도(RS) >= 70**
   - 이상적으로 90 이상

6. **강세 시장 환경**
   - 주요 지수(KOSPI/KOSDAQ)가 상승 추세에 있어야 함

#### VCP 매매 규칙

| 항목 | 규칙 |
|------|------|
| 진입 | 피봇 포인트 돌파 + 높은 거래량 확인 시 |
| 손절 | 최종 수축의 저점 바로 아래 설정 |
| 베이스 깊이 | 첫 번째 수축이 가장 깊고 (20~30%), 이후 점점 얕아져야 함 |
| 전체 베이스 깊이 | 일반적으로 30% 이내 (이상적) |

#### VCP 시각적 구조

```
          ┌─── 1차 고점
          │
    ──────┤
          │    ┌── 2차 고점
  ▲ 가격  │    │
          │  ──┤
          │    │  ┌─ 3차 고점 (피봇 포인트)
          │    │  │
          │  ──┤──┤═══════ ← 돌파!
          │    │  │
 1차 저점─┘    │  │
       (깊음) 2차 3차
              저점 저점
             (중간)(얕음)

    ─────── 시간 ──────────►

    수축 깊이: 25% → 12% → 5%  (점진적 감소)
    거래량:    높음 → 중간 → 낮음 (점진적 감소)
```

---

## 3. 프로그래밍 스크리닝 파라미터 정리

### 3.1 기술적 조건 (Trend Template)

```
# 필수 8조건
T1: Close > SMA(150) AND Close > SMA(200)
T2: SMA(150) > SMA(200)
T3: SMA(200)[today] > SMA(200)[20 trading days ago]  # 1개월 상승 추세
T4: SMA(50) > SMA(150) AND SMA(50) > SMA(200)
T5: Close > SMA(50)
T6: Close >= Low_52W * 1.25  # 52주 최저가 대비 25% 이상 (30% 권장)
T7: Close >= High_52W * 0.75  # 52주 최고가 대비 25% 이내
T8: RS_Rating >= 70  # 상대강도 백분위 순위 (90+ 선호)

# 추가 조건
T9: Avg_Volume(20) >= threshold  # 최소 거래량/거래대금 기준
```

### 3.2 VCP 패턴 감지 파라미터

```
# 수축 감지
V1: contraction_count: 2~6         # 수축 횟수
V2: contraction[n] < contraction[n-1]  # 각 수축의 깊이가 이전보다 작아야 함
V3: volume_avg[contraction_n] < volume_avg[contraction_n-1]  # 거래량 감소 추세

# 돌파 감지
V4: breakout_volume >= avg_volume_20 * 1.5  # 돌파 시 거래량 150%+
V5: close > pivot_point                     # 피봇 포인트 돌파

# 베이스 특성
V6: total_base_depth <= 30%         # 전체 베이스 깊이 30% 이내
V7: final_contraction_depth <= 10%  # 최종 수축 깊이 10% 이내 (이상적)
```

### 3.3 리스크 관리 파라미터

```
R1: max_stop_loss = -7% ~ -8%      # 최대 손절 (절대 초과 금지)
R2: stop_below_pivot_low = True     # 또는 최종 수축 저점 아래 손절
R3: position_sizing = f(stop_distance)  # 손절 거리 기반 포지션 사이징
R4: market_trend_filter = True      # KOSPI/KOSDAQ 상승 추세 시에만 매매
```

---

## 4. 현재 DB 스키마 적합성 분석

### 4.1 DB 구조 개요

| DB 파일 | 테이블 | 용도 |
|---------|--------|------|
| `Output/stock_data_daily.db` | `stock_prices` | 일별 OHLCV + 기술적 지표 (24개 컬럼) |
| `Output/stock_data_daily.db` | `stock_meta` | 스크리닝용 비정규화 스냅샷 (23개 컬럼) |
| `Output/stock_data_weekly.db` | `stock_prices` | 주별 OHLCV + 수익률 + RS (31개 컬럼) |
| `Output/stock_data_weekly.db` | `relative_strength` | RS 백분위 순위 (5개 컬럼) |

### 4.2 Trend Template 조건별 매핑

| # | 조건 | 필요 데이터 | DB 보유 | 매핑 컬럼 | 상태 |
|---|------|------------|:-------:|----------|:----:|
| T1 | Close > SMA150 & SMA200 | SMA150, SMA200 | 부분 | daily: SMA200 있음, **SMA150 없음** | ⚠️ |
| T2 | SMA150 > SMA200 | SMA150, SMA200 | 부분 | SMA200 있음, **SMA150 없음** | ⚠️ |
| T3 | SMA200 상승 추세 (1개월) | SMA200 히스토리 | **있음** | daily `stock_prices`에 날짜별 SMA200 존재, 20영업일 전과 비교 가능 | ✅ |
| T4 | SMA50 > SMA150 & SMA200 | SMA50, SMA150, SMA200 | 부분 | SMA50, SMA200 있음, **SMA150 없음** | ⚠️ |
| T5 | Close > SMA50 | Close, SMA50 | **있음** | daily: Close, SMA50 / meta: close, sma50 | ✅ |
| T6 | Close >= 52주최저가 x 1.25 | Close, 52주최저가 | **있음** | weekly: min52 | ✅ |
| T7 | Close >= 52주최고가 x 0.75 | Close, 52주최고가 | **있음** | daily: High52W / weekly: MAX52 / meta: high52w | ✅ |
| T8 | RS순위 >= 70 | RS Rating (백분위) | **있음** | relative_strength: RS_12M_Rating (0~100) | ✅ |

### 4.3 VCP/SEPA 추가 조건 매핑

| 조건 | 필요 데이터 | DB 보유 | 매핑 컬럼 |
|------|------------|:-------:|----------|
| 거래량 돌파 (150%+) | 당일 Volume, 평균 Volume | ✅ | daily: Volume, Volume20MA |
| 변동성 수축 감지 | 일별 High/Low 히스토리 | ✅ | daily: High, Low, DailyRange(%), ADR20 |
| SMA40(200일) 추세 방향 | SMA40 히스토리 | ✅ | weekly: SMA40_Trend_1M ~ SMA40_Trend_4M (이미 계산됨) |
| 시장 환경 필터 | 지수 데이터 | ✅ | weekly stock_prices에 KOSPI, KOSDAQ 지수 데이터 포함 |

### 4.4 stock_meta 스크리닝 테이블 매핑

현재 `stock_meta` 테이블은 빠른 스크리닝을 위한 비정규화 테이블로, 다음 컬럼을 보유:

| stock_meta 컬럼 | Minervini 용도 | 비고 |
|----------------|---------------|------|
| close | 현재가 비교 기준 | ✅ |
| sma50 | T4, T5 조건 | ✅ |
| sma100 | 참고용 (미너비니 직접 사용 안함) | - |
| sma200 | T1, T2, T3, T4 조건 | ✅ |
| high52w | T7 조건 (52주 최고가) | ✅ |
| rs_12m | T8 조건 (상대강도 백분위) | ✅ |
| sma10_w, sma20_w, sma40_w | 주봉 이평선 비교 | ✅ |
| chg_1w, chg_1m, chg_3m | 모멘텀 확인 | ✅ |
| **sma150 (없음)** | T1, T2, T4 조건 | ⚠️ 추가 필요 |
| **min52w (없음)** | T6 조건 (52주 최저가) | ⚠️ 추가 필요 |

### 4.5 주봉-일봉 이동평균 대응표

Minervini는 미국 시장 기준으로 일봉 이동평균을 사용하지만, 주봉으로 환산하면 다음과 같다:

| 일봉 MA | 주봉 MA | DB 보유 여부 |
|---------|---------|:----------:|
| SMA(50) = 약 10주 | SMA10 | ✅ weekly: SMA10 |
| SMA(150) = 약 30주 | SMA30 | ❌ **없음** |
| SMA(200) = 약 40주 | SMA40 | ✅ weekly: SMA40 |

---

## 5. Gap 분석 및 구현 로드맵

### 5.1 종합 판정

```
┌─────────────────────────────────────────────────────┐
│  미너비니 Trend Template 적용 가능성: 87.5%          │
│  (8개 조건 중 7개 즉시 적용 가능)                    │
│                                                      │
│  ✅ 즉시 가능 (5/8): 조건 3, 5, 6, 7, 8             │
│  ⚠️  SMA150 추가 시 가능 (3/8): 조건 1, 2, 4        │
│                                                      │
│  VCP/SEPA 추가 기능:                                 │
│  ✅ 거래량 돌파 감지 → 즉시 가능                     │
│  ✅ 변동성 수축 데이터 → 즉시 가능                   │
│  ✅ 시장 환경 필터 → 즉시 가능                       │
│  ❌ VCP 자동 감지 → 알고리즘 구현 필요               │
└─────────────────────────────────────────────────────┘
```

### 5.2 구현 우선순위

| 우선순위 | 항목 | 설명 | 난이도 | 영향 범위 |
|:--------:|------|------|:------:|----------|
| **P1** | SMA150 컬럼 추가 (daily) | daily.py에 SMA150 계산 추가 | 낮음 | daily.py, stock_prices 테이블 |
| **P1** | SMA30 컬럼 추가 (weekly) | weekly.py에 SMA30(=150일) 계산 추가 | 낮음 | weekly.py, stock_prices 테이블 |
| **P1** | stock_meta 확장 | sma150, min52w 컬럼 추가 | 낮음 | meta_service.py, stock_meta 테이블 |
| **P2** | Trend Template 스크리너 | 8조건 필터링 로직 구현 | 중간 | screen_service.py 또는 새 모듈 |
| **P2** | SMA200 추세 판별 | 과거 SMA200과 비교하는 쿼리 | 낮음 | queries.py |
| **P3** | VCP 패턴 감지 | 수축 횟수, 깊이, 거래량 패턴 분석 알고리즘 | 높음 | 새 모듈 필요 |
| **P3** | 돌파 알림 | 피봇 돌파 + 거래량 조건 충족 시 알림 | 중간 | 새 모듈 필요 |

### 5.3 DB 스키마 변경 요약

#### daily `stock_prices` 테이블 추가 컬럼

```sql
ALTER TABLE stock_prices ADD COLUMN SMA150 REAL;
```

#### weekly `stock_prices` 테이블 추가 컬럼

```sql
ALTER TABLE stock_prices ADD COLUMN SMA30 REAL;
```

#### `stock_meta` 테이블 추가 컬럼

```sql
ALTER TABLE stock_meta ADD COLUMN sma150 REAL;
ALTER TABLE stock_meta ADD COLUMN min52w REAL;
```

---

## 6. 한국 시장 적용 시 고려사항

### 6.1 차이점 (기술적 분석 관점)

| 항목 | 미국 시장 | 한국 시장 | 대응 방안 |
|------|----------|----------|----------|
| 거래량 기준 | 400,000주 이상 | 거래대금 기준이 더 적합 | VolumeWon(억원) 활용 |
| 가격 제한 | 없음 | 상한가/하한가 30% | 가격제한 히트 종목 별도 표시 |
| 공매도 | 자유 | 제한적 | 하방 압력 약함 → 조정 깊이 다를 수 있음 |
| RS 벤치마크 | S&P 500 | KOSPI | 이미 KOSPI 대비 RS 계산 중 ✅ |
| 거래 시간 | 6.5시간 | 6.5시간 | 동일 |

### 6.2 한국 시장 맞춤 수정 제안

1. **거래대금 필터**: 일평균 거래대금(VolumeWon) 5억원 이상 필터 적용
2. **가격 필터**: 최소 종가 5,000원 이상 (현재 config.py에 MIN_CLOSE_PRICE=5000 설정됨 ✅)
3. **시가총액 필터**: 1,000억원 이상 (유동성 확보)
4. **RS 계산**: 현재 KOSPI 대비 계산 중이므로 그대로 활용 가능
5. **VCP 수축 깊이 조정**: 한국 시장은 상한가/하한가 제한으로 수축 깊이가 미국보다 얕을 수 있음 → 임계값 조정 필요

---

## 7. 참고 자료

### 7.1 서적

- Mark Minervini, *"Trade Like a Stock Market Wizard"* (2013)
- Mark Minervini, *"Think & Trade Like a Champion"* (2017)
- Mark Minervini, *"Mindset Secrets for Winning"* (2019)

### 7.2 웹 리소스

- Deepvue - Minervini Trend Template: https://deepvue.com/screener/minervini-trend-template/
- ChartMill - Minervini Strategy: https://www.chartmill.com/documentation/stock-screener/fundamental-analysis-investing-strategies/464-Mark-Minervini-Strategy-Think-and-Trade-Like-a-Champion-Part-1
- FinerMarketPoints - VCP Criteria: https://www.finermarketpoints.com/post/vcp-criteria-complete-checklist
- TraderLion - VCP Pattern: https://traderlion.com/technical-analysis/volatility-contraction-pattern/
- TrendSpider - VCP Explained: https://trendspider.com/learning-center/volatility-contraction-pattern-vcp/
- QuantStrategy.io - SEPA Strategy: https://quantstrategy.io/blog/sepa-strategy-explained-mastering-trend-following-with-mark/

---

## 8. 다음 단계

이 리서치를 기반으로 SPEC 문서를 작성하고 구현을 진행할 수 있다:

1. **SPEC-MINERVINI-001 작성**: Trend Template 스크리너 기능 명세
2. **DB 스키마 확장**: SMA150, SMA30, min52w 컬럼 추가
3. **스크리너 API 구현**: Trend Template 8조건 + 추가 필터
4. **VCP 감지 알고리즘**: 별도 SPEC으로 분리 (복잡도 높음)
5. **대시보드 연동**: 스크리닝 결과를 기존 대시보드에 통합

---

문서 버전: 1.1.0
작성일: 2026-03-08
수정일: 2026-03-08
변경사항: 펀더멘탈 분석 섹션 제거 (프로젝트 범위 외), 기술적 분석만 유지
작성자: MoAI (SwingMaster 페르소나 리서치)
