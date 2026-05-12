너는 현재 프로젝트의 코드베이스를 검토하여, 기존 한국 증시 SQLite DB를 **AI 학습/검증 가능한 research DB**로 확장하기 위한 **설계 및 구현 계획**을 수립하는 역할이다.

중요: 지금 당장은 무작정 코드를 작성하지 말고, 먼저 **기존 코드 구조를 정확히 파악한 뒤**, 그 위에 얹는 방식으로 **현실적인 보강 계획**을 제안하라.

---

# 0. 작업 목적

현재 프로젝트에는 한국 증시 데이터를 수집/가공하여 SQLite DB를 구축하는 코드가 이미 존재한다.\
이 DB는 현재 차트 조회, 스크리닝, 종목 메타 스냅샷 용도로는 충분히 유용하다.

하지만 앞으로의 목표는 단순 조회용 DB가 아니라, 다음 목적을 만족하는 **AI/퀀트 리서치용 DB**로 발전시키는 것이다.

## 최종 목표

1. 기술적 셋업(특히 breakout / contraction / EMA 지지 / RS 리더십)의 품질을 학습 가능한 형태로 구조화
2. 후보군 생성 → feature 생성 → forward outcome label 생성 → 랭킹/분류 모델 학습이 가능한 구조 확보
3. 미래 정보 누수 없이(point-in-time) 검증 가능한 데이터 구조 확보
4. 실전 매매와 연결 가능한 백테스트/학습 파이프라인의 기반 DB 구축

즉 현재 DB의 역할을 아래처럼 진화시키는 것이 목적이다.

- 기존: 차트/스크리닝용 DB
- 목표: **feature store + event store + label store + validation-ready research DB**

---

# 1. 현재 DB 스키마 컨텍스트

현재는 2개의 SQLite DB와 4개 테이블이 있다.

## A. stock_data_daily.db

### 1) stock_prices

일별 OHLCV + 이동평균 + 기술 지표. 2년치 데이터 보유.

주요 컬럼:

- Name, Date
- Open, High, Low, Close
- Change
- High52W
- Volume, Volume20MA, VolumeWon
- EMA10, EMA20, SMA21, SMA50, EMA65, SMA100, SMA200
- DailyRange, HLC, Range, ADR20
- FromEMA10, FromEMA20, FromSMA50, FromSMA200
- RS_Line

### 2) stock_meta

스크리닝용 종목별 최신 스냅샷.

주요 컬럼:

- code, name, market, market_cap
- sector_major, sector_minor, product
- close, change_1d
- ema10, ema20, sma50, sma100, sma200
- high52w
- chg_1w, chg_1m, chg_3m
- sma10_w, sma20_w, sma40_w
- rs_12m
- last_updated

---

## B. stock_data_weekly.db

### 3) stock_prices

주간 OHLCV + 기간별 수익률 + 주간 이동평균 + RS raw

주요 컬럼:

- Name, Date
- Open, High, Low, Close, Volume, VolumeSMA10
- CHG_1W, CHG_1M, CHG_2M, CHG_3M, CHG_6M, CHG_9M, CHG_12M
- SMA10, SMA20, SMA40
- SMA40_Trend_1M \~ SMA40_Trend_4M
- MAX10, MAX52, min52, Close_52min
- RS_1M, RS_2M, RS_3M, RS_6M, RS_9M, RS_12M
- RS_Line

### 4) relative_strength

RS raw 값을 전체 종목 기준 백분위 등급으로 변환한 테이블

주요 컬럼:

- Name, Date
- RS_12M_Rating
- RS_6M_Rating
- RS_3M_Rating
- RS_1M_Rating

---

# 2. 현재 파이프라인 컨텍스트

현재 DB 업데이트 파이프라인은 대략 다음 순서다:

- Phase 1: weekly stock_prices 생성
- Phase 2: weekly relative_strength 생성
- Phase 3: daily stock_prices 생성
- Phase 4: daily stock_meta 재구축

구현 특성:

- 약 2,550 종목
- 전체 약 45초
- SQLite WAL 모드
- INSERT OR REPLACE 중심
- 외부 입력 파일(sectormap, basic_data 등) 사용

---

# 3. 현재 구조의 강점

현재 DB는 이미 다음을 상당히 잘 지원한다:

- 일봉/주봉 OHLCV
- 거래량/거래대금
- EMA/SMA 다중 추세 구조
- ADR20, Range, DailyRange 기반 변동성 수축 판단
- 52주 고가/저가 관련 값
- RS_Line, RS raw, RS percentile rating
- market(KOSPI/KOSDAQ), market_cap, sector_major/minor

즉 다음 질문에 답할 기초 데이터는 이미 있다:

- 강한 추세 종목인가?
- 변동성이 수축 중인가?
- 거래량이 말랐는가?
- 52주 고가 근처인가?
- RS 리더인가?
- 어느 섹터에 속하는가?

이 강점은 유지해야 하며, 보강 설계는 기존 구조를 최대한 재사용하는 방향이어야 한다.

---

# 4. 현재 구조의 한계

현재 구조는 조회/스크리닝에는 적합하지만, AI 학습/검증 관점에서는 다음 한계가 있다.

## (1) feature와 label이 분리되어 있지 않음

원천 가격/지표는 있지만, 특정 날짜 기준으로 바로 학습 샘플로 쓸 수 있는 정규화된 feature snapshot 테이블이 없다.

## (2) 이벤트 중심 구조가 없음

모든 날짜를 전부 학습하는 것이 아니라, breakout / contraction / EMA 지지 / RS 리더십 등 **의미 있는 셋업 발생 시점**만 따로 구조화하는 것이 적합한데, 현재는 event table이 없다.

## (3) forward label이 없음

예:

- 5일 후 수익률
- 10일 내 +8% 도달 여부
- 5일 내 -4% 손절 여부
- MFE / MAE\
  이런 미래 결과(label)가 별도로 저장되어 있지 않다.

## (4) 시장 regime 정보가 없음

같은 셋업도 시장 상태에 따라 성과가 다르므로, 지수 기반 시장 상태 테이블이 필요하다.

## (5) point-in-time 정합성 보강 필요

학습/검증용으로는 특정 날짜 기준 “그날까지 알 수 있었던 정보만” 써야 한다.\
최신 스냅샷 테이블(stock_meta)는 그대로 학습용으로 쓰기 위험하다.

## (6) 백테스트 신뢰성 보강 필요

가능하면 survivorship bias, universe snapshot, 거래정지/상장폐지 이력 등을 고려할 구조가 필요하다.

---

# 5. 목표 학습 방향

이 DB는 end-to-end 자동매매용보다는, 다음 구조를 지원하도록 보강하는 것이 목표다.

## 목표 학습 구조

1. 후보군 생성

   - RS 상위
   - 추세 정렬
   - 유동성 확보
   - 52주 고가 근접
   - contraction 또는 pullback 조건

2. feature 생성

   - 추세
   - 수축
   - 거래량
   - 리더십
   - 섹터/시장 상태

3. forward label 생성

   - 성공 확률
   - 실패 확률
   - 기대 상승폭(MFE)
   - 기대 하락폭(MAE)

4. 모델링

   - 좋은 breakout / 나쁜 breakout 분류
   - 기대값 기반 종목 랭킹

즉 핵심 방향은:\
**규칙 기반 후보군 생성 + ML 기반 품질 점수화**이다.

---

# 6. 설계 원칙

코드를 검토할 때 아래 원칙을 반드시 지켜라.

## 원칙 1. 기존 DB를 깨지 말 것

- 기존 `daily stock_prices`, `weekly stock_prices`, `relative_strength`, `stock_meta`는 최대한 유지
- 기존 API/스크리닝과 호환성 보존
- 보강은 가급적 **추가 테이블 / 파생 테이블 / 뷰** 중심

## 원칙 2. 원천 데이터와 학습 데이터를 분리할 것

- 원천 가격/지표 테이블
- 파생 feature 테이블
- event 테이블
- forward label 테이블\
  을 논리적으로 분리

## 원칙 3. point-in-time 정합성을 보장할 것

- 특정 Date의 feature는 그 Date 시점에서 알 수 있었던 정보만 사용
- 미래 수익률, MFE, MAE 등은 반드시 별도 label로 분리
- 누수 위험이 있는 계산은 명확히 차단

## 원칙 4. event-driven 구조를 우선 고려할 것

- 전 종목 전 날짜를 모두 학습하는 구조보다,
- 내 전략상 의미 있는 셋업 발생일을 기준으로 한 event-driven 구조를 우선 제안

## 원칙 5. 단계적으로 구현 가능해야 할 것

- 한 번에 거대한 재설계 금지
- Phase 1 → Phase 2 → Phase 3 식으로 실현 가능한 로드맵 제안

---

# 7. 우선 검토해야 할 신규 구조(초안)

기존 코드/스키마를 검토한 뒤, 아래와 같은 신규 구조가 적절한지 평가하고 구체화하라.

## A. market_regime 계열

목적:

- 시장 상태를 별도 관리
- 모델 입력 및 검증에 활용

후보 예:

- Date
- KOSPI / KOSDAQ 지수 값
- 지수의 SMA/EMA 상하 여부
- breadth 성격 지표(가능 시)
- regime score
- strong / neutral / weak market flag

## B. feature_snapshot 계열

목적:

- 특정 종목, 특정 날짜 기준 학습 입력값 저장
- 원천 컬럼 그대로가 아니라 학습 친화적 파생 feature로 저장

후보 예:

- Close / High52W
- Volume / Volume20MA
- Close / SMA50
- Close / SMA200
- EMA10 gap / EMA20 gap
- ADR contraction 계열
- RS rating / RS slope
- 주봉 추세 정렬 여부
- sector / market / market_cap bucket
- market regime score

## C. setup_events 계열

목적:

- 의미 있는 셋업 발생일만 별도 저장
- event-driven 학습 및 랭킹 기반 제공

예시 셋업:

- breakout 후보
- contraction 후보
- EMA10/EMA20 지지 후보
- RS leader + 52주 고가 근접 후보

## D. forward_labels 계열

목적:

- 미래 결과를 정답(label)로 저장
- feature와 엄격히 분리

후보 예:

- ret_5d / ret_10d / ret_20d
- mfe_10d / mae_10d
- hit_plus_8pct_10d
- hit_minus_4pct_5d
- breakout_success_flag

## E. universe / survivorship 보강

가능하면 검토:

- 특정 날짜 기준 tradable universe snapshot
- 거래정지 / 관리종목 / 상장폐지 관련 처리 구조
- survivorship bias 완화 방안

---

# 8. 네가 해야 할 일

코드베이스를 먼저 읽고, 아래 작업을 수행하라.

## 작업 1. 현재 코드 구조 분석

다음을 찾아라:

- DB 생성/업데이트 관련 파일, 함수, 클래스 위치
- daily / weekly / rs / meta 생성 흐름
- 현재 파이프라인에서 재사용 가능한 부분
- 변경이 필요한 부분
- 가장 안전한 확장 지점

## 작업 2. gap analysis

다음을 정리하라:

- 현재 구조가 학습/검증 관점에서 부족한 점
- 미래 데이터 누수 가능성
- point-in-time 문제 가능성
- 성능/유지보수 이슈
- 스키마/인덱스/생성 로직 상 개선 포인트

## 작업 3. DB 보강 설계안

다음을 제안하라:

- 신규 테이블 또는 뷰 목록
- 각 구조의 목적
- 핵심 컬럼
- 생성 로직 개요
- 기존 테이블과의 관계

## 작업 4. 단계별 구현 계획

예시 형식:

- Phase 1: market_regime + forward_labels
- Phase 2: feature_snapshot + setup_events
- Phase 3: universe/survivorship + 백테스트 보강

각 단계별로 설명할 것:

- 구현 난이도
- 기대 효과
- 리스크
- 기존 코드 변경 범위
- 우선순위

## 작업 5. 마이그레이션 전략

다음을 제안하라:

- 기존 DB를 깨지 않고 additive하게 가는 방법
- SQLite에서 현실적인 구조
- WAL, index, batch insert, materialized table/view 활용 방안
- 기존 업데이트 시간(약 45초)을 크게 훼손하지 않는 전략

## 작업 6. 구현 준비 산출물

가능하면 다음도 포함하라:

- 파일별 수정 예상 목록
- 신규 모듈 제안
- SQL DDL 초안(필요하면)
- 업데이트 파이프라인에 어디에 어떤 phase를 삽입할지
- 테스트 포인트
- 검증 포인트

---

# 9. 출력 형식

반드시 아래 형식으로 답하라.

## 1) Executive Summary

- 현재 구조의 요약
- 가장 큰 부족점 3\~5개
- 추천 확장 방향 한 줄 요약

## 2) Current Code / Data Flow Analysis

- 관련 파일/함수
- 현재 파이프라인 요약
- 확장 포인트

## 3) Gap Analysis

- 학습/검증 관점 이슈
- point-in-time / leakage 이슈
- 백테스트 신뢰성 이슈

## 4) Proposed DB Extension Plan

- 신규 테이블/뷰 제안
- 목적 / 컬럼 / 생성 방식 / 인덱스 / 관계

## 5) Phased Implementation Roadmap

- Phase 1 / 2 / 3
- 난이도 / 효과 / 리스크 / 예상 수정 범위

## 6) Migration & Performance Strategy

- 기존 DB와 호환 방식
- 성능 고려
- 운영 리스크

## 7) Recommended First Step

- 지금 가장 먼저 시작해야 하는 구현 1\~2개

중요:

- 처음부터 거대한 재구축 제안 금지
- 코드 작성 전에 설계/계획을 우선 제시
- 가능하면 실제 코드베이스 구조를 반영한 현실적인 제안을 할 것
- 추상론보다 “어디를 어떻게 바꾸면 되는지”를 우선하라