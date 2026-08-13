# Frozen Fixture Manifest — `aggregation-2026-08-11`

> SPEC-SECTOR-AGGREGATION-001 §8.1 **집계 픽스처**. acceptance.md §8.2 F1~F11 구조 요건을
> 호스팅하며, 게이팅 AC(002 / 007 / 011 / 013 / 014 / 024 / 030 / 045 R1·R3·R4·R5·R6)와
> M1.0-b 골든 baseline 캡처가 이 스냅샷 위에서 실행된다. 날짜 축 픽스처
> (`weekly-2026-08-12/`)는 ① SPEC-SECTOR-GRID-001 소관이며 본 SPEC 은 읽기 전용이다.

## 캡처 메타데이터 · F2~F8 실측 충족값 [기계 판독 블록 — F11]

> **이 블록이 F11 의 단일 원천이다.** AC-SAG-048 은 이 YAML 을 파싱해 **픽스처에서 독립
> 재산출한 실측값과 정확히 일치**하는지 검사한다(F3/F6 은 섹터명 집합까지). AC-SAG-007 /
> AC-SAG-045 R6 은 섹터명을 AC 본문이 아니라 이 블록에서 읽는다. 손으로 값을 적어 넣고
> 픽스처를 다른 상태로 두면 게이트가 RED 가 된다.

```yaml
as_of: "2026-08-11"
captured_at: "2026-08-13 13:27:30"
git_sha: "ac9f547"
source_weekly_db: "Output/stock_data_weekly.db"
source_weekly_db_mtime: "2026-08-12 23:09:34"
source_daily_db: "Output/stock_data_daily.db"
source_daily_db_mtime: "2026-08-12 23:10:28"
source_registry: "Input/sectormap-original.xlsx"
source_registry_mtime: "2026-08-09 22:10:00"
build_command: "python tests/fixtures/frozen/aggregation-2026-08-11/build_fixture.py"

f2_ag5_sector_count: 18
f3_kospi_exactly4_sector_count: 2
f3_kospi_exactly4_sectors: ["디스플레이", "스마트폰"]
f3_kospi_exactly5_sector_count: 1
f3_kospi_exactly5_sectors: ["PCB"]
f4_top_weight_gt_10pct_sector_count: 18
f5_cap_missing_stock_count: 7
f5_rs_missing_sector_count: 10
f6_cap_valid_exactly3_sector_count: 1
f6_cap_valid_exactly3_sectors: ["패션"]
f7_nh_verdict_divergent_stock_count: 35
f8_sma_null_stock_count: 17
```

## 산출물

| 파일 | 내용 |
| --- | --- |
| `weekly.db` | `stock_prices` 20479행 / 385 날짜 / 145 이름(지수 2 포함) + `relative_strength` |
| `daily.db` | `stock_meta`(시총·현재가) + `stock_prices` `[2026-05-08, 2026-08-11]` (`VolumeWon`) |
| `registry.xlsx` | `pd.read_excel(header=8)` 구조. UN-4 dedup 진단용 중복 행 1건 포함 |
| `MANIFEST.md` | 본 문서 — F2~F8 실측 충족값(F11) |

## 날짜 축 정합 (F1 / F9)

| 지표 | 실측값 |
| --- | --- |
| 고유 날짜 수 | **385** |
| 정규 격자 바 수 | **346** |
| `history_grid` 바 수 | **345** |
| CG-3 배제 대표 바 | **0건** |
| `as_of=2026-08-11` → latest | **2026-08-11**, `is_partial_week=True` |
| 3M 앵커 바 `2026-05-08` | True |
| 유효 유니버스 크기 | **135** |

## F2~F8 실측 충족값 [F11 — AC-SAG-048 이 이 값과의 정확한 일치를 요구한다]

| 요건 | 임계 | 실측값 |
| --- | --- | --- |
| **F2** | AG-5 통과 섹터 >= 12 | **18** |
| **F3-a** | `market=kospi` 유효 종목 **정확히 4**인 섹터 == 2 | **2** |
| **F3-b** | `market=kospi` 유효 종목 **정확히 5**인 섹터 >= 1 | **1** |
| **F4** | 최상위 원비중 > 0.10 섹터 >= 3 | **18** |
| **F5-a** | `market_cap` NULL 또는 <= 0 종목 >= 5 | **7** |
| **F5-b** | RS 행 없는 종목을 가진 섹터 >= 3 | **10** |
| **F6** | 유효 시총 종목 **정확히 3**인 섹터 >= 1 | **1** |
| **F7** | 저장 `MAX52` vs `MAX(High) over 364d` 판정이 갈리는 종목 >= 5 | **35** |
| **F8** | `SMA40` 또는 `SMA10`이 NULL인 종목 >= 3 | **17** |

### F3 해당 섹터명 집합 [AC-SAG-007 / 045 R6 이 본 절에서 섹터명을 읽는다]

- `market=kospi` 유효 종목 **정확히 4**: `디스플레이, 스마트폰`
- `market=kospi` 유효 종목 **정확히 5**: `PCB`

### F6 해당 섹터명 집합

- 유효 시총 종목 **정확히 3**: `패션`

### F2 해당 섹터명 집합 (AG-5 통과)

`Auto, PCB, 게임, 내수, 디스플레이, 반도체, 방산, 비철금속, 스마트폰, 유통, 음식료, 인터넷, 조선, 철강, 통신, 패션, 헬스케어, 화장품`

## 갱신 규약

스냅샷 갱신은 명시적 행위다(acceptance.md §8.4 규약 4) — 커밋 메시지에 사유와 새 실측값을
남기고, 위 표의 실측값을 갱신한다. 조용한 재생성을 금지한다. AC-SAG-048 이 본 문서의 실측
기록과 픽스처 재산출값의 일치를 기계적으로 검사하므로, 픽스처만 바꾸고 본 문서를 방치하면
게이트가 RED 가 된다.
