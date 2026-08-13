# Golden Baseline Manifest — `pre-sector-ux`

> SPEC-SECTOR-AGGREGATION-001 **M1.0-b**. 구 집계 구현의 직렬화 응답 스냅샷이다.
> M2가 구 구현을 교체한 뒤에는 재현 불가능하다(plan.md §0.2 point of no return).
> AC-SAG-045 R1(등가중 순위 대비) · R4(현행 대비 상승) · R5(min-max 대비 분산 증가)가
> M7에서 이 파일들과 비교한다.

## 캡처 메타데이터 [기계 판독 블록 — AC-SAG-047]

> AC-SAG-047이 이 YAML을 파싱해 각 키가 비어 있지 않은지, `as_of`가 `2026-08-11`인지
> 검사한다. 값을 비우거나 `TBD`/`unknown`으로 두면 게이트가 RED가 된다.

```yaml
as_of: "2026-08-11"
captured_at: "2026-08-13 17:39:57"
git_sha: "a000add"
fixture: "tests/fixtures/frozen/aggregation-2026-08-11"
fixture_manifest_git_sha: "a224593"
fixture_superset_of: "adb1f25"
capture_command: "python tests/fixtures/golden/pre-sector-ux/capture_baseline.py"
periods: ["w1", "m1", "m3"]
golden_baseline_discarded: true
supersedes: "b839cee (2026-08-13 13:45:27) — F12 미충족 픽스처 adb1f25 위에서 캡처, 폐기"
```

## 산출물

| 파일 | 엔드포인트 | 내용 |
| --- | --- | --- |
| `ranking-current.json` | `GET /api/sectors/ranking` | 무파라미터 응답. `sectors[i].returns.{w1,m1,m3}` · `excess_returns.{w1,m1,m3}` — 세 기간 전부 |
| `stage-overview.json` | `GET /api/stage/overview` | `distribution` · `by_sector[]` · `stage2_candidates[]` · `all_stocks[]` |
| `MANIFEST.md` | — | 본 문서 |

## 왜 기간별 3파일이 아닌가 (plan.md v0.4.0 정정 D4)

현행 `/sectors/ranking`은 **무파라미터**다(`backend/routers/sectors.py:44`
`async def sector_ranking()`). 세 번 호출해도 동일 응답 3부이며, `period` 파라미터는
M6 신설이다. 현행 응답이 이미 세 기간의 원수익률·초과수익률을 모두 싣고 있어
단일 파일에 세 기간이 전부 담긴다 — 기능 손실 없이 파일만 1개로 줄였다.

## 캡처 경로 (직렬화 계약)

`fastapi.testclient.TestClient`로 실제 HTTP 요청을 태워 `response_model` 직렬화를
통과한 응답을 캡처했다. 서비스 반환값의 `model_dump_json()`이 아니다 — AC-SAG-047은
직렬화 응답의 형태를 단언하므로 서비스 레이어 덤프는 구조가 어긋난다.

DB 경로는 라우터 모듈 상수를 패치해 집계 프로즌 픽스처로 고정했다:

```
backend.routers.sectors.WEEKLY_DB_PATH → tests/fixtures/frozen/aggregation-2026-08-11/weekly.db
backend.routers.sectors.DAILY_DB_PATH  → tests/fixtures/frozen/aggregation-2026-08-11/daily.db
backend.routers.stage.WEEKLY_DB_PATH   → tests/fixtures/frozen/aggregation-2026-08-11/weekly.db
```

## 폐기 기록 (M1.0-b 재캡처 — acceptance.md §9 DoD · §8.4 규약 4)

**구 baseline 은 폐기됐다.** `b839cee (2026-08-13 13:45:27) — F12 미충족 픽스처 adb1f25 위에서 캡처, 폐기`

구 baseline 은 F12 미충족 픽스처(`adb1f25` 빌드분 — AG-5 통과 18섹터 중 유효 시총
`n > 10` 이 게임 하나뿐) 위에서 떠졌다. INV-CAP-1 축퇴(`cap_eff = max(0.10, 1/n)`,
`n <= 10` 이면 시총가중 == 등가중)로 AC-SAG-002 가 완전한 무게이팅이 됐고, 그 픽스처는
더 이상 리포에 존재하지 않는다. 그 위에서 R1/R4/R5 를 판정하면 v0.4.1 의 결함을 그대로
상속하므로 재캡처했다. 비가역 경계는 M1.0-b 가 아니라 **M2** 이므로(§8.5) 이 재캡처
경로가 살아 있었다.

현 baseline 이 선 픽스처 빌드: `git_sha=a224593` · `f13_1_superset_of=adb1f25`.

## 초과수익률 비축퇴 확인

`excess_returns` 가 `returns` 와 **동일하지 않은** 섹터가 존재함을 캡처 시 단언한다.
지수 행 부재나 벤치마크 산출 실패로 초과수익률이 원수익률로 degenerate 하면 R1/R4/R5
비교가 무의미해지므로, 캡처가 그 상태에서 통과하지 못하게 막는다.

| 지표 | 값 |
| --- | --- |
| `excess != returns` 인 섹터 수 | **18** / 18 |
| 세 기간 최대 절대 격차 `|excess − returns|` | **16.166200** |

## 실측 요약 (캡처 시점)

| 지표 | 값 |
| --- | --- |
| `ranking.date` | `2026-08-11` |
| `len(sectors)` | **18** |
| `distribution.total` | **321** |
| `distribution` stage1/2/3/4 | 3 / 94 / 9 / 215 |
| `len(by_sector)` | **18** |
| `len(stage2_candidates)` | **11** |
| `len(all_stocks)` | **321** |
| `sector_excess_return` 문자열 | **0건** (D12 재도입 방지) |
| `total_count` 문자열 | **0건** (D12 — 실제 키는 `distribution.total`) |
