"""M1.0-b — 골든 baseline 캡처 스크립트 (SPEC-SECTOR-AGGREGATION-001).

**구 구현(現 코드)의 직렬화 응답을 그대로 떠 둔다.** M2가 집계 구현을 교체하면
이 값들은 영구히 재현 불가능해지므로(plan.md §0.2 point of no return), 코드 변경
0줄 상태에서 실행되어야 한다.

핵심 규약:
  - **HTTP 응답에서 캡처한다.** 서비스 반환값의 `model_dump_json()`이 아니라
    FastAPI `response_model` 직렬화를 실제로 통과한 바이트를 뜬다. AC-SAG-047은
    직렬화 응답의 형태를 단언하므로 서비스 레이어 덤프를 뜨면 구조가 어긋난다.
  - **집계 프로즌 픽스처 위에서 캡처한다** (`tests/fixtures/frozen/aggregation-2026-08-11/`).
    라이브 DB로 뜨면 baseline 자체가 드리프트해 R1/R4/R5 비교가 무의미해진다.
  - **기준일 `as_of = 2026-08-11`** (acceptance.md §8 규약 7, 사용자 결정 2026-08-13).
    현행 엔드포인트는 무파라미터이므로 `as_of`는 픽스처의 최신 정규 바로 고정되며,
    캡처 시 응답 `date == "2026-08-11"`을 단언해 실제로 그 기준일임을 확인한다.

실행:
    python tests/fixtures/golden/pre-sector-ux/capture_baseline.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"

AS_OF = "2026-08-11"
CAPTURE_COMMAND = "python tests/fixtures/golden/pre-sector-ux/capture_baseline.py"
FIXTURE_ID = "tests/fixtures/frozen/aggregation-2026-08-11"

# 폐기된 선행 캡처 (acceptance.md §8.6 · §9 DoD). 구 baseline 은 F12 미충족 픽스처
# (`adb1f25` 빌드분 — AG-5 통과 18섹터 중 유효 시총 `n > 10` 이 게임 하나뿐) 위에서
# 떠졌으므로 그 위에서 R1/R4/R5 를 판정하면 v0.4.1 의 결함을 그대로 상속한다.
SUPERSEDED_CAPTURE = "b839cee (2026-08-13 13:45:27) — F12 미충족 픽스처 adb1f25 위에서 캡처, 폐기"

# 현행 `/sectors/ranking`은 무파라미터이며 단일 응답에 세 기간이 모두 실린다
# (plan.md M1.0-b, v0.4.0 정정 D4). 기간별 3파일 캡처는 동일 응답 3부일 뿐이다.
PERIODS = ["w1", "m1", "m3"]


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def capture() -> dict[str, object]:
    """FastAPI 앱에 실제 요청을 태워 직렬화 응답을 캡처한다."""
    from fastapi.testclient import TestClient

    from backend.main import app

    # 구 구현의 `get_sector_registry()`는 경로 인자가 없고 라이브
    # `Input/sectormap-original.xlsx`를 lazy-load 한다. 픽스처 registry로 고정하지
    # 않으면 baseline이 라이브 파일에 묶여 드리프트한다 — 모듈 상수와 lazy 캐시를
    # 함께 눌러 픽스처 사본을 읽게 한다.
    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(DAILY_DB)),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        client = TestClient(app)
        ranking_resp = client.get("/api/sectors/ranking")
        stage_resp = client.get("/api/stage/overview")

    assert ranking_resp.status_code == 200, (
        f"/api/sectors/ranking → {ranking_resp.status_code}: {ranking_resp.text[:400]}"
    )
    assert stage_resp.status_code == 200, (
        f"/api/stage/overview → {stage_resp.status_code}: {stage_resp.text[:400]}"
    )

    ranking = ranking_resp.json()
    stage = stage_resp.json()

    # 기준일 고정 확인 — 다른 날짜에서 떠졌으면 R1/R4/R5 비교가 무효다.
    assert ranking["date"] == AS_OF, f"기준일 불일치: {ranking['date']!r} != {AS_OF!r}"
    assert len(ranking["sectors"]) >= 10, f"섹터 수 부족: {len(ranking['sectors'])}"

    # D12 재도입 방지 — dataclass 필드명이 직렬화에 새어나오면 즉시 실패시킨다.
    raw = json.dumps(ranking, ensure_ascii=False) + json.dumps(stage, ensure_ascii=False)
    assert "sector_excess_return" not in raw, "dataclass 필드명 `sector_excess_return` 누출"
    assert "total_count" not in raw, "존재하지 않는 키 `total_count` 누출"

    # 비축퇴 확인 — 지수 행이 없거나 벤치마크 산출이 실패하면 초과수익률이 원수익률과
    # 동일해지고(초과 = 원 − 0), 그 baseline 위에서는 R1/R4/R5 비교가 무의미해진다.
    diff = [
        s["name"] for s in ranking["sectors"]
        if any(s["excess_returns"].get(p) != s["returns"].get(p) for p in PERIODS)
    ]
    assert diff, "축퇴 baseline — 전 섹터에서 excess_returns == returns (벤치마크 미산출)"

    return {"ranking": ranking, "stage": stage}


def _fixture_manifest_meta() -> tuple[str, str]:
    """집계 픽스처 MANIFEST 의 `git_sha` · `f13_1_superset_of` 를 읽어 온다.

    baseline 이 **어느 픽스처 빌드 위에서 떠졌는지**를 기록으로 남긴다 — 픽스처가
    재빌드되면 baseline 도 재캡처돼야 하고(§8.4 규약 4), 그 판단의 근거가 이 값이다.
    """
    import re

    text = (FIXTURE_DIR / "MANIFEST.md").read_text(encoding="utf-8")
    sha = re.search(r'^git_sha:\s*"([^"]*)"', text, re.M)
    sup = re.search(r'^f13_1_superset_of:\s*"([^"]*)"', text, re.M)
    return (sha.group(1) if sha else "unknown"), (sup.group(1) if sup else "unknown")


def write_manifest(ranking: dict, stage: dict) -> None:
    captured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sha = _git_sha()
    fixture_sha, fixture_superset_of = _fixture_manifest_meta()
    dist = stage["distribution"]

    n_sectors = len(ranking["sectors"])
    n_diff = sum(
        1 for s in ranking["sectors"]
        if any(s["excess_returns"].get(p) != s["returns"].get(p) for p in PERIODS)
    )
    max_gap = max(
        abs((s["excess_returns"].get(p) or 0.0) - (s["returns"].get(p) or 0.0))
        for s in ranking["sectors"] for p in PERIODS
    )

    body = f"""# Golden Baseline Manifest — `pre-sector-ux`

> SPEC-SECTOR-AGGREGATION-001 **M1.0-b**. 구 집계 구현의 직렬화 응답 스냅샷이다.
> M2가 구 구현을 교체한 뒤에는 재현 불가능하다(plan.md §0.2 point of no return).
> AC-SAG-045 R1(등가중 순위 대비) · R4(현행 대비 상승) · R5(min-max 대비 분산 증가)가
> M7에서 이 파일들과 비교한다.

## 캡처 메타데이터 [기계 판독 블록 — AC-SAG-047]

> AC-SAG-047이 이 YAML을 파싱해 각 키가 비어 있지 않은지, `as_of`가 `2026-08-11`인지
> 검사한다. 값을 비우거나 `TBD`/`unknown`으로 두면 게이트가 RED가 된다.

```yaml
as_of: "{AS_OF}"
captured_at: "{captured_at}"
git_sha: "{sha}"
fixture: "{FIXTURE_ID}"
fixture_manifest_git_sha: "{fixture_sha}"
fixture_superset_of: "{fixture_superset_of}"
capture_command: "{CAPTURE_COMMAND}"
periods: [{", ".join(f'"{p}"' for p in PERIODS)}]
golden_baseline_discarded: true
supersedes: "{SUPERSEDED_CAPTURE}"
```

## 산출물

| 파일 | 엔드포인트 | 내용 |
| --- | --- | --- |
| `ranking-current.json` | `GET /api/sectors/ranking` | 무파라미터 응답. `sectors[i].returns.{{w1,m1,m3}}` · `excess_returns.{{w1,m1,m3}}` — 세 기간 전부 |
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
backend.routers.sectors.WEEKLY_DB_PATH → {FIXTURE_ID}/weekly.db
backend.routers.sectors.DAILY_DB_PATH  → {FIXTURE_ID}/daily.db
backend.routers.stage.WEEKLY_DB_PATH   → {FIXTURE_ID}/weekly.db
```

## 폐기 기록 (M1.0-b 재캡처 — acceptance.md §9 DoD · §8.4 규약 4)

**구 baseline 은 폐기됐다.** `{SUPERSEDED_CAPTURE}`

구 baseline 은 F12 미충족 픽스처(`adb1f25` 빌드분 — AG-5 통과 18섹터 중 유효 시총
`n > 10` 이 게임 하나뿐) 위에서 떠졌다. INV-CAP-1 축퇴(`cap_eff = max(0.10, 1/n)`,
`n <= 10` 이면 시총가중 == 등가중)로 AC-SAG-002 가 완전한 무게이팅이 됐고, 그 픽스처는
더 이상 리포에 존재하지 않는다. 그 위에서 R1/R4/R5 를 판정하면 v0.4.1 의 결함을 그대로
상속하므로 재캡처했다. 비가역 경계는 M1.0-b 가 아니라 **M2** 이므로(§8.5) 이 재캡처
경로가 살아 있었다.

현 baseline 이 선 픽스처 빌드: `git_sha={fixture_sha}` · `f13_1_superset_of={fixture_superset_of}`.

## 초과수익률 비축퇴 확인

`excess_returns` 가 `returns` 와 **동일하지 않은** 섹터가 존재함을 캡처 시 단언한다.
지수 행 부재나 벤치마크 산출 실패로 초과수익률이 원수익률로 degenerate 하면 R1/R4/R5
비교가 무의미해지므로, 캡처가 그 상태에서 통과하지 못하게 막는다.

| 지표 | 값 |
| --- | --- |
| `excess != returns` 인 섹터 수 | **{n_diff}** / {n_sectors} |
| 세 기간 최대 절대 격차 `|excess − returns|` | **{max_gap:.6f}** |

## 실측 요약 (캡처 시점)

| 지표 | 값 |
| --- | --- |
| `ranking.date` | `{ranking["date"]}` |
| `len(sectors)` | **{len(ranking["sectors"])}** |
| `distribution.total` | **{dist["total"]}** |
| `distribution` stage1/2/3/4 | {dist["stage1"]} / {dist["stage2"]} / {dist["stage3"]} / {dist["stage4"]} |
| `len(by_sector)` | **{len(stage["by_sector"])}** |
| `len(stage2_candidates)` | **{len(stage["stage2_candidates"])}** |
| `len(all_stocks)` | **{len(stage["all_stocks"])}** |
| `sector_excess_return` 문자열 | **0건** (D12 재도입 방지) |
| `total_count` 문자열 | **0건** (D12 — 실제 키는 `distribution.total`) |
"""
    (OUT_DIR / "MANIFEST.md").write_text(body, encoding="utf-8")


def main() -> None:
    if not WEEKLY_DB.exists():
        raise SystemExit(f"집계 픽스처 없음: {WEEKLY_DB}")

    data = capture()
    ranking, stage = data["ranking"], data["stage"]

    (OUT_DIR / "ranking-current.json").write_text(
        json.dumps(ranking, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "stage-overview.json").write_text(
        json.dumps(stage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_manifest(ranking, stage)

    print(f"captured: date={ranking['date']} sectors={len(ranking['sectors'])} "
          f"total={stage['distribution']['total']}")


if __name__ == "__main__":
    main()
