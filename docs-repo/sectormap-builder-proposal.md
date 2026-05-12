# KR Sectormap Builder - 프로젝트 제안서

> FnGuide 데이터 기반 자체 섹터 분류 시스템 구축

## 배경

### 현재 상태

my_chart 프로젝트는 종목 기본 정보를 두 개의 외부 엑셀 파일에 의존한다:

| 파일 | 출처 | 용도 |
| --- | --- | --- |
| `sectormap-original.xlsx` | 세종데이터 (수동 다운로드) | 종목코드, 종목명, 시장, 섹터 분류 (53 컬럼 원본, registry.py가 header=8로 로드 후 6 컬럼만 사용) |
| `basic_data.xlsx` | KRX 정보데이터시스템 (수동 다운로드) | 상장주식수 (시가총액 계산) |

> **참고 (2026-05-12)**: 과거에는 `sectormap.xlsx`(6 컬럼 추출본)와 `sectormap-original.xlsx`(53 컬럼 원본) 두 파일이 공존했으나, 단일 source 통합으로 `sectormap-original.xlsx`만 사용하도록 변경되었다. 본 builder 산출물도 동일 파일명 + 동일 컬럼 구조(header row=8, 6 핵심 컬럼)를 따라야 drop-in 교체가 가능하다.

### 문제

- **세종데이터 의존**: 세종데이터에서 업데이트를 제공하지 않으면 신규 상장/상폐 종목 반영 불가
- **수동 갱신**: 두 파일 모두 사람이 직접 다운로드해야 함
- **갱신 시점 불명**: 세종데이터의 업데이트 주기가 불규칙

### 목표

FnGuide 크롤링 + AI 분류를 통해 `sectormap-original.xlsx`를 자체 생성하는 별도 프로젝트를 구축한다. my_chart와 동일한 엑셀 형식(header row=8, 6 핵심 컬럼 + 47 보조 컬럼)으로 출력하여 기존 시스템에 드롭인 교체 가능하게 한다.

---

## 기술 조사 결과

### FnGuide 스냅샷 페이지에서 얻을 수 있는 데이터

URL: `http://comp.fnguide.com/SVO2/asp/SVD_Main.asp?gicode=A{code}`

| 데이터 | 추출 방식 | 예시 (삼성전자) |
| --- | --- | --- |
| KSE 표준업종 | `span.stxt` 첫 번째 | 코스피 전기.전자 |
| FICS 업종 | `span.stxt` 두 번째 | 반도체 및 관련장비 |
| 사업 요약 | `#bizSummaryContent` | 1969년 설립... DX부문 TV/냉장고... DS부문 DRAM/NAND... |
| 발행주식수 | tbody 파싱 | 보통주/우선주 분리 |
| 시가총액 | tbody 파싱 | 억원 단위 |

### 표준 분류 vs 투자용 분류 비교

| 종목 | KSE 표준업종 | FICS | 세종(투자용) | 문제점 |
| --- | --- | --- | --- | --- |
| 삼성전자 | 전기.전자 | 반도체 및 관련장비 | 반도체 | KSE 너무 대분류 |
| 에코프로비엠 | 전기.전자 | 전자 장비 및 기기 | 배터리 | FICS가 부정확 |
| 한화에어로 | 운송장비.부품 | **상업서비스** | 방산 | FICS가 완전히 틀림 |
| SK | **금융** | **석유 및 가스** | 지주사 | 둘 다 틀림 |
| 삼성SDI | 전기.전자 | 전자 장비 및 기기 | 배터리 | 삼성전자와 구분 불가 |

**결론: KSE/FICS 표준 분류만으로는 투자용 섹터맵을 만들 수 없다. 사업 요약(Summary) 텍스트 기반 커스텀 분류가 필수.**

---

## 핵심 설계 원칙: Taxonomy-First, Classify-Second

### 왜 "전체를 한 번에 봐야" 하는가

한 건씩 순차 분류하면 생기는 문제:

- **일관성 붕괴**: 같은 사업을 "2차전지 소재", "배터리 원자재", "리튬 양극재"로 제각각 분류
- **섹터 남발**: 제한 없이 분류하면 100개+ 섹터 생성
- **경계 모호**: "로봇 자동화 장비"를 기계? 반도체장비? 자동차부품? 기준 없이 판단

### 올바른 접근: 2단계 분리

```
Phase 1: 분류 체계(Taxonomy) 설계
  - 전 종목 Summary를 수집한 뒤
  - 전체를 조감하면서 대분류 25-35개, 중분류 100-130개 프레임워크 확정
  - 분류 기준 문서화 (경계 케이스 포함)

Phase 2: 개별 종목 분류 (Classification)
  - 확정된 프레임워크에 각 종목을 배치
  - AI 자동 분류 + 사람 검수
  - 이 단계는 자동화 가능
```

---

## 현재 세종데이터 분류 체계 역공학

30개 대분류 / \~120개 중분류에서 발견된 설계 원칙:

### 원칙 1: 밸류체인 분리

같은 산업이어도 가치사슬 위치별로 중분류 분리.

```
반도체 (163종목):
  ├── 메모리반도체 (2)     ← 최종 제품
  ├── 비메모리_팹리스 (24)  ← 설계
  ├── 비메모리_Foundry (2) ← 위탁생산
  ├── 반도체_장비 (56)     ← 제조 장비
  ├── 반도체_소재 (28)     ← 원재료
  ├── 반도체_패키징 (13)   ← 후공정
  └── 반도체_테스트 (9)    ← 검사

배터리 (75종목):
  ├── 배터리셀 (2)         ← 최종 제품
  ├── 배터리_소재 (24)     ← 원재료
  ├── 배터리_부품 (19)     ← 부품
  └── 배터리_장비 (30)     ← 제조 장비
```

### 원칙 2: 투자 테마 중심

표준산업분류(KSIC/GICS)에 없는 투자 테마를 독립 섹터로.

```
방산 (19종목)     ← GICS에는 "산업재"의 하위
원자력 (7종목)    ← GICS에는 "유틸리티"의 하위
스마트폰 (45종목) ← GICS에는 "IT"의 하위
```

### 원칙 3: 규모/시장 분리

```
건설_대형 (6) vs 건설_중소형 (34)
석유화학_대형사 (9) vs 석유화학_중소형 (62)
게임_KOSPI (6) vs 게임_KOSDAQ (26)
```

### 원칙 4: 제조/서비스(브랜드/ODM) 분리

```
의류_브랜드 (30) vs 의류_OEMODM (9)
화장품_브랜드 (29) vs 화장품_OEMODM (10) vs 화장품_원부자재 (9)
```

### 원칙 5: 수요 산업 기준

경계 모호한 종목은 최종 수요 산업에 배치.

```
카메라_모듈 (23) → 스마트폰 (스마트폰에 쓰이므로)
디스플레이_장비 (31) → 디스플레이 (반도체장비가 아닌)
```

---

## 제안 프로젝트 구조

```
kr-sectormap/
├── README.md
├── pyproject.toml
│
├── Input/
│   └── basic_data.xlsx          # KRX에서 다운로드 (종목코드, 상장주식수)
│
├── Output/
│   └── sectormap-original.xlsx  # 최종 산출물 (my_chart 호환: header row=8, 6 핵심 컬럼)
│
├── data/
│   ├── raw_summaries.json       # Phase 1 크롤링 결과 (2,500종목 Summary + FICS)
│   └── taxonomy.yaml            # Phase 2 분류 체계 정의
│
├── src/
│   ├── crawl.py                 # FnGuide 스냅샷 크롤링 (Summary, FICS, 시장)
│   ├── taxonomy.py              # 분류 체계 설계 보조 도구
│   ├── classify.py              # 확정된 체계에 종목 자동 분류 (AI)
│   └── build.py                 # sectormap-original.xlsx 생성
│
└── mapping/
    ├── taxonomy_rules.md        # 분류 기준 문서 (경계 케이스 포함)
    └── review_log.md            # 수동 검수 기록
```

---

## 실행 파이프라인

```
Step 1: 종목 리스트 확보
  KRX basic_data.xlsx → 전체 KOSPI+KOSDAQ 종목코드 추출
  (또는 pykrx get_market_ticker_list 사용)

Step 2: FnGuide 크롤링 (crawl.py)
  전 종목 스냅샷 페이지 접근 → Summary + FICS + KSE 업종 수집
  예상 소요: ~20분 (0.5초 간격, 2,500종목)
  출력: data/raw_summaries.json

Step 3: 분류 체계 설계 (taxonomy.py + 사람)
  3-1. FICS 기준으로 초기 그룹핑
  3-2. 각 그룹 내 Summary를 읽으며 투자용 세분화
  3-3. 대분류 25-35개, 중분류 100-130개 확정
  3-4. taxonomy.yaml + taxonomy_rules.md 작성
  출력: data/taxonomy.yaml

Step 4: 자동 분류 (classify.py)
  확정된 taxonomy에 각 종목 배치 (AI 활용)
  Summary 텍스트 → taxonomy의 대분류/중분류 매핑
  출력: 종목별 분류 결과 JSON

Step 5: 사람 검수 + 엑셀 생성 (build.py)
  분류 결과 검토 → 수정 → sectormap-original.xlsx 생성
  my_chart/Input/에 복사하여 즉시 사용 가능
```

---

## 산출물 형식 (my_chart 호환)

```
sectormap-original.xlsx 컬럼 (header row=8 기준):
  종목\n코드     종목코드 (6자리, zero-padded) → registry.py에서 "Code"로 rename
  종목명         → "Name"으로 rename
  시장           KOSPI / KOSDAQ → "Market"으로 rename
  산업명(대)     대분류 섹터 (25-35개)
  산업명(중)     중분류 섹터 (100-130개)
  주요제품       주요 사업/제품 (FnGuide Summary에서 추출)
  (이후 47개 보조 컬럼: 주가변화율, 재무지표 등 — 현재 my_chart는 미사용)
```

my_chart의 `registry.py`가 `pd.read_excel(path, header=8)`로 로드한 뒤 한글→영문 rename + 6 컬럼 select 한다. 파일명과 핵심 컬럼명만 동일하면 코드 변경 없이 교체 가능.

---

## taxonomy.yaml 예시 형식

```yaml
sectors:
  반도체:
    description: "반도체 설계, 제조, 장비, 소재, 패키징, 테스트 전 밸류체인"
    subsectors:
      - name: 메모리반도체
        criteria: "DRAM, NAND 등 메모리 반도체 최종 제품 제조"
      - name: 비메모리_팹리스
        criteria: "반도체 설계만 수행, 자체 fab 없음"
      - name: 반도체_장비
        criteria: "반도체 제조 공정용 장비 (노광, 식각, 증착 등)"
      - name: 반도체_소재
        criteria: "웨이퍼, 포토레지스트, CMP 슬러리 등 공정 소재"
    boundary_rules:
      - "카메라 이미지센서 → 스마트폰 (수요산업 기준)"
      - "반도체 테스트 소켓 → 반도체_테스트 (밸류체인 기준)"

  배터리:
    description: "2차전지(리튬이온) 셀, 소재, 부품, 장비"
    subsectors:
      - name: 배터리셀
        criteria: "리튬이온 배터리 셀 최종 제조 (LG에너지, 삼성SDI 등)"
      - name: 배터리_소재
        criteria: "양극재, 음극재, 전해액, 분리막 등 셀 구성 소재"
    boundary_rules:
      - "전해액 첨가제 → 배터리_소재 (석유화학 아님)"
      - "배터리 관리 시스템(BMS) → 배터리_부품"
```

---

## 기술 요구사항

- Python 3.13+
- requests, beautifulsoup4, lxml (FnGuide 크롤링)
- pandas, openpyxl (엑셀 읽기/쓰기)
- Claude API 또는 OpenAI API (선택, AI 분류에 사용)
- 크롤링 간격: 최소 0.5초 (FnGuide 차단 방지)

---

## 유지보수 계획

| 주기 | 작업 | 자동화 |
| --- | --- | --- |
| 월 1회 | KRX에서 basic_data.xlsx 다운로드 | 수동 (KRX 로그인 필요) |
| 월 1회 | 신규 상장/상폐 종목 확인 | 자동 (코드 비교) |
| 월 1회 | 신규 종목 FnGuide 크롤링 + 분류 | 반자동 (AI 분류 + 검수) |
| 분기 1회 | 분류 체계 검토 (신규 테마 반영) | 수동 |

---

## 리스크와 완화 방안

| 리스크 | 영향 | 완화 |
| --- | --- | --- |
| FnGuide 페이지 구조 변경 | 크롤러 파싱 실패 | 테스트 코드로 감지, 파서 업데이트 |
| FnGuide IP 차단 | 크롤링 불가 | 0.5초 간격, User-Agent 설정, 월 1회만 실행 |
| AI 분류 오류 | 잘못된 섹터 배치 | 전수 검수는 비현실적이므로 시가총액 상위 200종목 우선 검수 |
| 복합 사업 기업 | 분류 애매 | 매출 비중 기준 1차 섹터만 지정 (규칙 문서화) |
| 표준 분류와 괴리 | 외부 데이터 연계 어려움 | FICS 코드를 참조 필드로 보존 |

---

## 참고: my_chart에서의 sectormap 사용처

sectormap-original.xlsx를 교체할 때 영향받는 코드:

| 파일 | 함수 | 역할 |
| --- | --- | --- |
| `my_chart/registry.py` | `_load_sectormap()` | 엑셀 로드 |
| `my_chart/registry.py` | `get_stock_registry()` | Code, Name, Market 추출 |
| `my_chart/registry.py` | `get_sector_registry()` | 전체 컬럼 (섹터 포함) |
| `backend/services/meta_service.py` | `rebuild_stock_meta()` | DB에 섹터 정보 적재 |

**교체 조건**: header row=8 + 핵심 6 컬럼명(`종목\n코드`/`종목명`/`시장`/`산업명(대)`/`산업명(중)`/`주요제품`)이 동일하면 코드 변경 없이 파일만 교체 가능. registry.py가 자체적으로 한글→영문(`Code`/`Name`/`Market`) rename 처리.

---

*작성일: 2026-03-16상태: 제안 단계 (미착수)관련 프로젝트: my_chart (KR Stock Screener)*