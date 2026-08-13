# Frozen Fixture Manifest — `aggregation-2026-08-11`

> SPEC-SECTOR-AGGREGATION-001 §8.1 **집계 픽스처**. acceptance.md §8.2 F1~F13 구조 요건을
> 호스팅하며, 게이팅 AC(002 / 007 / 011 / 012 / 013 / 014 / 024 / 030 / 045 R1·R3·R4·R5-a·R6)와
> M1.0-b 골든 baseline 캡처가 이 스냅샷 위에서 실행된다. 날짜 축 픽스처
> (`weekly-2026-08-12/`)는 ① SPEC-SECTOR-GRID-001 소관이며 본 SPEC 은 읽기 전용이다.
>
> **v0.5.0 재빌드분** — F12(효과 요건) 신설 + F13(재빌드 구성 계약) 신설 + F4/F8 폐지 +
> F7 규약 Y(NULL `MAX52` 제외) 적용. 이전 빌드(`adb1f25`)는 전 섹터 `n <= 10` 축퇴로
> AC-SAG-002 를 무게이팅으로 만들었다(acceptance.md §8.2 F12 블록 · §8.2.1).

## 캡처 메타데이터 · F2~F13 실측 충족값 [기계 판독 블록 — F11]

> **이 블록이 F11 의 단일 원천이다.** AC-SAG-048 은 이 YAML 을 파싱해 **픽스처에서 독립
> 재산출한 실측값과 정확히 일치**하는지 검사한다(F3 / F6 / F12-b / F12-c 는 섹터명 집합까지).
> AC-SAG-007 / AC-SAG-045 R6 은 섹터명을, AC-SAG-002 는 `f12b_*` / `f12c_*` 집합을 AC 본문이
> 아니라 이 블록에서 읽는다. 손으로 값을 적어 넣고 픽스처를 다른 상태로 두면 게이트가 RED 다.

```yaml
as_of: "2026-08-11"
captured_at: "2026-08-13 17:20:30"
git_sha: "a224593"
source_weekly_db: "Output/stock_data_weekly.db"
source_weekly_db_mtime: "2026-08-12 23:09:34"
source_daily_db: "Output/stock_data_daily.db"
source_daily_db_mtime: "2026-08-12 23:10:28"
source_registry: "Input/sectormap-original.xlsx"
source_registry_mtime: "2026-08-09 22:10:00"
build_command: "python tests/fixtures/frozen/aggregation-2026-08-11/build_fixture.py"

synthetic_bar:
  source_live_bar_date: "2026-08-12"
  relabeled_to_date: "2026-08-11"
  transformation: "날짜 라벨만 교체한다 — Close/High/Low/Open/거래량 등 값 컬럼은 라이브 원본 그대로이며 어떤 값도 재계산·보정하지 않는다 (acceptance.md §8.1.1)"
  reproduce_command: "python tests/fixtures/frozen/aggregation-2026-08-11/build_fixture.py"

f2_ag5_sector_count: 18
f2_ag5_sectors: ["Auto", "PCB", "게임", "내수", "디스플레이", "반도체", "방산", "비철금속", "스마트폰", "유통", "음식료", "인터넷", "조선", "철강", "통신", "패션", "헬스케어", "화장품"]
f3_kospi_exactly4_sector_count: 2
f3_kospi_exactly4_sectors: ["디스플레이", "스마트폰"]
f3_kospi_exactly5_sector_count: 1
f3_kospi_exactly5_sectors: ["PCB"]
f5_cap_missing_stock_count: 9
f5_rs_missing_sector_count: 10
f6_cap_valid_exactly3_sector_count: 1
f6_cap_valid_exactly3_sectors: ["패션"]
f7_convention: "Y"
f7_nh_verdict_divergent_stock_count: 24
f7_max52_null_stock_count: 27
f7_convention_x_divergent_stock_count: 51
f9_complete_bar_count: 345
f9_anchor_3m_present: True
f10_meta_missing_stock_count: 0
f10_daily_volume_missing_stock_count: 0
f12a_n_ge_11_top_gt_10pct_sector_count: 17
f12a_sectors: ["Auto", "PCB", "게임", "내수", "디스플레이", "반도체", "방산", "비철금속", "스마트폰", "유통", "음식료", "인터넷", "조선", "철강", "통신", "헬스케어", "화장품"]
f12b_delta_ge_50bp_sector_count: 13
f12b_delta_ge_50bp_sectors_1m: ["Auto", "내수", "디스플레이", "반도체", "방산", "비철금속", "스마트폰", "유통", "인터넷", "조선", "통신", "헬스케어", "화장품"]
f12c_rank_shifted_sector_count: 12
f12c_rank_shifted_sectors_1m: ["Auto", "PCB", "게임", "방산", "스마트폰", "유통", "음식료", "인터넷", "조선", "철강", "통신", "헬스케어"]
f12_eligible_sector_count: 17
f12_anchor_1m: "2026-07-10"
f13_1_superset_of: "adb1f25"
f13_1_baseline_stock_count: 145
f13_1_baseline_list: "f13-1-superset-baseline.tsv"
f13_1_missing_stock_count: 0
f13_2_n_ge_15_sector_count: 17
f13_2_n_ge_15_sectors: ["Auto", "PCB", "게임", "내수", "디스플레이", "반도체", "방산", "비철금속", "스마트폰", "유통", "음식료", "인터넷", "조선", "철강", "통신", "헬스케어", "화장품"]
f13_4_fashion_member_count: 5
f13_4_fashion_cap_valid_count: 3
f13_5_kospi_universe_size: 133
f13_5_kosdaq_universe_size: 188
f13_5_kospi_ag5_sector_count: 15
f13_5_kosdaq_ag5_sector_count: 17
f13_6_as_of_row_count: 323
f13_6_live_source_bar_row_count: 0
```

## 산출물

| 파일 | 내용 |
| --- | --- |
| `weekly.db` | `stock_prices` 31254행 / 385 날짜 / 331 이름(지수 2 포함) + `relative_strength` |
| `daily.db` | `stock_meta`(시총·현재가) + `stock_prices` `[2026-05-08, 2026-08-11]` (`VolumeWon`) |
| `registry.xlsx` | `pd.read_excel(header=8)` 구조. UN-4 dedup 진단용 중복 행 1건 포함 |
| `f13-1-superset-baseline.tsv` | F13-1 기준 종목 목록(`adb1f25` 빌드분 145종목 + 섹터 배정) |
| `MANIFEST.md` | 본 문서 — F2~F13 실측 충족값(F11) |

## 합성 바 (§8.1.1 · F13-6)

라이브 주봉 DB 에는 `2026-08-11` 행이 **존재하지 않는다.** 최신 라이브 바는
`2026-08-12`(수)이며, 빌더가 그 행의 **날짜 라벨만** `2026-08-11`(화)로 교체한다.
값 컬럼은 라이브 원본 그대로다. AC-SAG-046 의 창 일수 리터럴 `{11, 32, 95}` 은 **라벨**
기준으로 계산되므로 이 재라벨링이 그 리터럴의 전제다 — 빠뜨리면 `as_of` 가
`2026-08-12` 가 되어 `{12, 33, 96}` 으로 전부 RED 가 된다.

| 항목 | 값 |
| --- | --- |
| `2026-08-11` 행 수 | **323** (> 0 이어야 한다) |
| `2026-08-12` 행 수 | **0** (0 이어야 한다 — 재라벨링의 구조적 증거) |

## 날짜 축 정합 (F1 / F9)

| 지표 | 실측값 |
| --- | --- |
| 고유 날짜 수 | **385** |
| 정규 격자 바 수 | **346** |
| `history_grid` 바 수 | **345** |
| CG-3 배제 대표 바 | **0건** |
| `as_of=2026-08-11` → latest | **2026-08-11**, `is_partial_week=True` |
| 3M 앵커 바 `2026-05-08` | True |
| 유효 유니버스 크기 | **321** |

## F2~F13 실측 충족값 [F11 — AC-SAG-048 이 이 값과의 정확한 일치를 요구한다]

| 요건 | 임계 | 실측값 | 여유 |
| --- | --- | --- | --- |
| **F2** | AG-5 통과 섹터 >= 12 | **18** | 1.50x |
| **F3-a** | `market=kospi` 유효 종목 **정확히 4**인 섹터 == 2 | **2** | — |
| **F3-b** | `market=kospi` 유효 종목 **정확히 5**인 섹터 >= 1 | **1** | 1/1 |
| **F5-a** | `market_cap` NULL 또는 <= 0 종목 >= 5 | **9** | 1.80x |
| **F5-b** | RS 행 없는 종목을 가진 섹터 >= 3 | **10** | 3.33x |
| **F6** | 유효 시총 종목 **정확히 3**인 섹터 >= 1 | **1** | 1/1 |
| **F7** (규약 Y) | 신고가 판정이 갈리는 종목 >= 5 | **24** | 4.80x |
| **F9** | 완성 바 >= 53 · 3M 앵커 바 존재 | **345** / True | 6.51x |
| **F10** | meta 결측 0 · daily VolumeWon 결측 0 | **0** / **0** | — |
| **F12-a** | `n >= 11` 이고 최상위 원비중 > 0.10 인 섹터 >= 12 | **17** | 1.42x |
| **F12-b** | 1M 시총가중 − 등가중 차 >= 0.5%p 섹터 >= 3 | **13** | 4.33x |
| **F12-c** | 1M 시총가중 순위 != 등가중 순위 섹터 >= 5 | **12** | 2.40x |
| **F13-1** | 상위집합 누락 종목 == 0 | **0** | — |
| **F13-2** | 유효 시총 `n >= 15` 섹터 >= 14 | **17** | 1.21x |
| **F13-3** | F12-b >= 9 **이고** F12-c >= 9 (빌드 목표) | **13** / **12** | 1.33x |
| **F13-4** | 패션 구성 5 / 유효 시총 3 | **5** / **3** | — |
| **F13-5** | 양 시장 비공백 + 각 AG-5 섹터 >= 1 | **15** / **17** | — |
| **F13-6** | `2026-08-11` 행 > 0 이고 `2026-08-12` 행 == 0 | **323** / **0** | — |

### F7 규약 Y vs 규약 X [AC-SAG-024 v0.5.0 · N2]

| 계수 규약 | divergent 종목 수 |
| --- | --- |
| **규약 Y** (NULL `MAX52` 를 분자·분모에서 제외 — **확정 규약**) | **24** |
| 규약 X (NULL `MAX52` → `0.0` 치환, 폐기) | 51 |
| NULL `MAX52` 종목 수 | 27 |

두 값의 차이는 정확히 NULL `MAX52` 종목 수다 — 규약 X 는 `Close >= 0` 을 항상 참으로 만들어
**결측 처리 차이를 실질 판정 차이로 오계상**한다.

### F3 해당 섹터명 집합 [AC-SAG-007 / 045 R6 이 본 절에서 섹터명을 읽는다]

- `market=kospi` 유효 종목 **정확히 4**: `디스플레이, 스마트폰`
- `market=kospi` 유효 종목 **정확히 5**: `PCB`

### F6 해당 섹터명 집합

- 유효 시총 종목 **정확히 3**: `패션`

### F2 해당 섹터명 집합 (AG-5 통과)

`Auto, PCB, 게임, 내수, 디스플레이, 반도체, 방산, 비철금속, 스마트폰, 유통, 음식료, 인터넷, 조선, 철강, 통신, 패션, 헬스케어, 화장품`

### F12-b / F12-c 해당 섹터명 집합 [AC-SAG-002 가 본 절에서 집합을 읽는다]

- **F12-b** (1M `|시총가중 − 등가중| >= 0.5%p`): `Auto, 내수, 디스플레이, 반도체, 방산, 비철금속, 스마트폰, 유통, 인터넷, 조선, 통신, 헬스케어, 화장품`
- **F12-c** (1M 시총가중 순위 != 등가중 순위): `Auto, PCB, 게임, 방산, 스마트폰, 유통, 음식료, 인터넷, 조선, 철강, 통신, 헬스케어`
- F12 대조 대상 섹터(AG-5 통과 ∧ 유효 시총 >= 5): `Auto, PCB, 게임, 내수, 디스플레이, 반도체, 방산, 비철금속, 스마트폰, 유통, 음식료, 인터넷, 조선, 철강, 통신, 헬스케어, 화장품`
- 1M 앵커 바: `2026-07-10`

### F12-a / F13-2 해당 섹터명 집합

- **F12-a** (`n >= 11` ∧ 최상위 원비중 > 0.10): `Auto, PCB, 게임, 내수, 디스플레이, 반도체, 방산, 비철금속, 스마트폰, 유통, 음식료, 인터넷, 조선, 철강, 통신, 헬스케어, 화장품`
- **F13-2** (유효 시총 `n >= 15`): `Auto, PCB, 게임, 내수, 디스플레이, 반도체, 방산, 비철금속, 스마트폰, 유통, 음식료, 인터넷, 조선, 철강, 통신, 헬스케어, 화장품`

### 섹터별 유효 시총 종목 수 (`n`) — INV-CAP-1 축퇴 경계 판정용

`Auto=17, PCB=18, 게임=32, 내수=16, 디스플레이=18, 반도체=18, 방산=18, 비철금속=17, 스마트폰=17, 유통=18, 음식료=17, 인터넷=17, 조선=17, 철강=18, 통신=18, 패션=3, 헬스케어=15, 화장품=18`

## 갱신 규약

스냅샷 갱신은 명시적 행위다(acceptance.md §8.4 규약 4) — 커밋 메시지에 사유와 새 실측값을
남기고, 위 표의 실측값을 갱신한다. 조용한 재생성을 금지한다. AC-SAG-048 이 본 문서의 실측
기록과 픽스처 재산출값의 일치를 기계적으로 검사하므로, 픽스처만 바꾸고 본 문서를 방치하면
게이트가 RED 가 된다.
