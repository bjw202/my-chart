# coding: utf-8
"""SPEC-SECTOR-METRIC-UNIFY-001 M0 — 버블 엔드포인트 특성화(현재 출력 고정 + 불일치 N 측정).

프로덕션 코드를 건드리지 않고, 집계 프로즌 픽스처(aggregation-2026-08-11) 위에서
`/api/sectors/bubble` 의 **현재** 출력을 9조합(period 1w/1m/3m × market all/kospi/kosdaq)
전부 리터럴로 고정한다. 그리고 같은 조합에서 `/api/sectors/ranking` 봉투 `data[]` 와
섹터 **이름으로 조인**해 현재 불일치 섹터 수 N 을 측정한다.

M0 사전 점검(G-1/G-2, frozen 경로 채택 — 합성 DB 불필요):
- G-1: 픽스처가 RS 결측 경로를 실제로 가진다 — AS_OF=2026-08-11 기준 RS 결측 종목
  32개/10개 섹터(방산 18명 중 2결측 — spec 예상 방산 2/18 과 정확히 일치,
  조선 17명 중 3결측 — 개수는 spec 예상 3과 일치, 분모 기준만 상이).
- G-2: daily.db VolumeWon 은 [2026-05-08, 2026-08-11] 65거래일 21,140행,
  NULL 0 — 3M 윈도우(앵커 2026-05-08)를 완전 커버한다.

⚠ 현재 불일치 기록 — M4에서 뒤집힌다.
불일치 정의: 조인된 각 섹터에서 4개 필드쌍 —
  rs_avg          ↔ data[].rs_avg.value
  excess_return   ↔ data[].excess_returns[period].value
  trading_value   ↔ data[].trading_value[period].value
  period_return   ↔ data[].returns[period].value
— 중 어느 하나라도 1e-9 초과 차이(한쪽만 null 인 경우 포함)면 불일치.
data[] 에 행 자체가 없는 섹터(BUBBLE_ONLY)는 모든 쌍이 불일치다.
관찰 결과(9조합 전부): 교집합 내 **전 섹터·전 필드쌍** 불일치 + bubble-only 별도 →
N = 18(= sectors[] 전체) 이다. M4 통일 후 이 파일의 N 단언은 뒤집힌다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"

AS_OF = "2026-08-11"
PERIODS = ("1w", "1m", "3m")
MARKETS = ("all", "kospi", "kosdaq")
TOL = 1e-9

# 조인에서 완전히 일치하는 섹터가 하나도 없다는 관찰값(9조합 공통).
N_TOTAL = 18


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    """집계 프로즌 픽스처에 고정된 TestClient (test_sectors_bubble_market_contract.py 관용)."""
    from fastapi.testclient import TestClient

    from backend.main import app

    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(DAILY_DB)),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        yield TestClient(app)


def _get_bubble(client: Any, period: str, market: str) -> dict[str, Any]:
    resp = client.get("/api/sectors/bubble", params={"period": period, "market": market})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _get_ranking(client: Any, period: str, market: str) -> dict[str, Any]:
    resp = client.get("/api/sectors/ranking",
                      params={"as_of": AS_OF, "market": market, "period": period})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _is_mismatch(a: float | None, b: float | None) -> bool:
    """한쪽만 null 이거나 |a-b| > TOL 이면 불일치."""
    if a is None or b is None:
        return a is not b
    return abs(a - b) > TOL


# 단일 관찰 실행(2026-08-18, HEAD=777f044)에서 생성한 리터럴 —
# 이후 실행은 이 값과 일치해야 한다(특성화: 현재 동작 고정).
# 튜플 순서: (rs_avg, excess_return, period_return, trading_value)
EXPECTED: dict[str, dict[str, dict[str, tuple[float, float, float, float]]]] = {
    "1w": {
        "all": {
            "Auto": (61.14, -1.2868, 3.8303, 1514051627310.0),
            "PCB": (39.34, 4.1107, 9.2278, 1174054685720.0),
            "게임": (53.14, -0.4762, 4.6409, 284758699946.0),
            "내수": (59.51, -3.2578, 1.8593, 157774203995.0),
            "디스플레이": (57.45, 9.2747, 14.3919, 300228216880.0),
            "반도체": (52.18, 8.3293, 13.4464, 29455741829290.0),
            "방산": (48.16, 1.491, 6.6081, 1471308016514.0),
            "비철금속": (63.55, 0.9263, 6.0435, 575033416169.0),
            "스마트폰": (59.96, 4.3624, 9.4795, 563632764130.0),
            "유통": (56.44, -4.3477, 0.7694, 420851322471.0),
            "음식료": (65.13, -4.6628, 0.4543, 610531693950.0),
            "인터넷": (54.7, 0.7887, 5.9058, 1767838940270.0),
            "조선": (36.21, -1.2591, 3.8581, 1209311437240.0),
            "철강": (68.11, -1.4801, 3.637, 419407148165.0),
            "통신": (48.82, 2.5023, 7.6194, 1736188454350.0),
            "패션": (36.59, -5.4662, -0.349, 44854803950.0),
            "헬스케어": (35.67, -0.7847, 4.3325, 1945115094210.0),
            "화장품": (91.17, 8.7955, 13.9127, 2389667670090.0),
        },
        "kospi": {
            "Auto": (72.19, -3.4674, 1.6497, 1438036956100.0),
            "PCB": (29.17, 1.4126, 6.5298, 574112359090.0),
            "게임": (69.5, 0.6507, 5.7678, 195122824700.0),
            "내수": (46.88, -2.9098, 2.2073, 128626773170.0),
            "디스플레이": (60.61, 12.7088, 17.826, 113938248460.0),
            "반도체": (55.95, 5.2437, 10.3608, 27053535827200.0),
            "방산": (48.68, -1.2316, 3.8856, 1409832953850.0),
            "비철금속": (64.83, -0.6126, 4.5045, 225684577070.0),
            "스마트폰": (57.17, 4.9385, 10.0557, 418075463820.0),
            "유통": (60.4, -6.9589, -1.8417, 371289615925.0),
            "음식료": (72.31, -9.0237, -3.9066, 532869236900.0),
            "인터넷": (63.4, -2.2247, 2.8925, 1389810811230.0),
            "조선": (26.49, -1.92, 3.1971, 1159218942980.0),
            "철강": (69.75, -4.6962, 0.4209, 293599255070.0),
            "통신": (45.81, -6.2634, -1.1462, 408200982030.0),
            "패션": (62.29, -13.8966, -8.7794, 15514153200.0),
            "헬스케어": (49.44, -3.0364, 2.0807, 1004517253610.0),
            "화장품": (92.29, 5.6854, 10.8026, 1477101001650.0),
        },
        "kosdaq": {
            "Auto": (48.71, 1.1664, 6.2835, 76014671210.0),
            "PCB": (43.25, 5.1484, 10.2655, 599942326630.0),
            "게임": (49.36, -0.7363, 4.3809, 89635875246.0),
            "내수": (75.76, -3.7052, 1.4119, 29147430825.0),
            "디스플레이": (56.55, 8.2936, 13.4107, 186289968420.0),
            "반도체": (48.41, 11.4149, 16.5321, 2402206002090.0),
            "방산": (47.75, 3.669, 8.7862, 61475062664.0),
            "비철금속": (62.41, 2.2943, 7.4114, 349348839099.0),
            "스마트폰": (60.82, 4.1851, 9.3022, 145557300310.0),
            "유통": (52.48, -1.7366, 3.3805, 49561706546.0),
            "음식료": (57.04, 0.2432, 5.3603, 77662457050.0),
            "인터넷": (48.37, 2.9802, 8.0974, 378028129040.0),
            "조선": (47.15, -0.5155, 4.6016, 50092494260.0),
            "철강": (66.48, 1.736, 6.8532, 125807893095.0),
            "통신": (51.22, 9.5148, 14.6319, 1327987472320.0),
            "패션": (30.17, -3.3586, 1.7586, 29340650750.0),
            "헬스케어": (24.4, 1.0576, 6.1748, 940597840600.0),
            "화장품": (90.05, 11.9057, 17.0228, 912566668440.0),
        },
    },
    "1m": {
        "all": {
            "Auto": (61.14, 20.2007, 16.6591, 1514051627310.0),
            "PCB": (39.34, 1.5689, -1.9727, 1174054685720.0),
            "게임": (53.14, 14.1429, 10.6013, 284758699946.0),
            "내수": (59.51, 9.4995, 5.9579, 157774203995.0),
            "디스플레이": (57.45, 12.6733, 9.1316, 300228216880.0),
            "반도체": (52.18, -0.4298, -3.9714, 29455741829290.0),
            "방산": (48.16, 13.7184, 10.1768, 1471308016514.0),
            "비철금속": (63.55, 18.062, 14.5204, 575033416169.0),
            "스마트폰": (59.96, 17.2086, 13.667, 563632764130.0),
            "유통": (56.44, 4.5151, 0.9734, 420851322471.0),
            "음식료": (65.13, 9.9732, 6.4315, 610531693950.0),
            "인터넷": (54.7, 18.1948, 14.6532, 1767838940270.0),
            "조선": (36.21, 13.3533, 9.8117, 1209311437240.0),
            "철강": (68.11, 16.6077, 13.0661, 419407148165.0),
            "통신": (48.82, 19.0575, 15.5159, 1736188454350.0),
            "패션": (36.59, 15.3261, 11.7844, 44854803950.0),
            "헬스케어": (35.67, 16.9581, 13.4165, 1945115094210.0),
            "화장품": (91.17, 47.1708, 43.6292, 2389667670090.0),
        },
        "kospi": {
            "Auto": (72.19, 10.739, 7.1974, 1438036956100.0),
            "PCB": (29.17, -9.1419, -12.6835, 574112359090.0),
            "게임": (69.5, 16.3216, 12.78, 195122824700.0),
            "내수": (46.88, 11.0971, 7.5555, 128626773170.0),
            "디스플레이": (60.61, 7.4872, 3.9456, 113938248460.0),
            "반도체": (55.95, -0.3794, -3.9211, 27053535827200.0),
            "방산": (48.68, 6.0234, 2.4818, 1409832953850.0),
            "비철금속": (64.83, 20.9059, 17.3643, 225684577070.0),
            "스마트폰": (57.17, 12.5659, 9.0243, 418075463820.0),
            "유통": (60.4, -5.1564, -8.698, 371289615925.0),
            "음식료": (72.31, 10.6099, 7.0683, 532869236900.0),
            "인터넷": (63.4, 11.0861, 7.5445, 1389810811230.0),
            "조선": (26.49, 8.6356, 5.094, 1159218942980.0),
            "철강": (69.75, 14.0841, 10.5425, 293599255070.0),
            "통신": (45.81, 0.8226, -2.7191, 408200982030.0),
            "패션": (62.29, 1.5854, -1.9563, 15514153200.0),
            "헬스케어": (49.44, 12.8059, 9.2642, 1004517253610.0),
            "화장품": (92.29, 27.0612, 23.5196, 1477101001650.0),
        },
        "kosdaq": {
            "Auto": (48.71, 30.8451, 27.3034, 76014671210.0),
            "PCB": (43.25, 5.6885, 2.1469, 599942326630.0),
            "게임": (49.36, 13.6402, 10.0986, 89635875246.0),
            "내수": (75.76, 7.4454, 3.9038, 29147430825.0),
            "디스플레이": (56.55, 14.155, 10.6134, 186289968420.0),
            "반도체": (48.41, -0.4801, -4.0218, 2402206002090.0),
            "방산": (47.75, 19.8744, 16.3328, 61475062664.0),
            "비철금속": (62.41, 15.534, 11.9924, 349348839099.0),
            "스마트폰": (60.82, 18.6372, 15.0956, 145557300310.0),
            "유통": (52.48, 14.1865, 10.6449, 49561706546.0),
            "음식료": (57.04, 9.2568, 5.7152, 77662457050.0),
            "인터넷": (48.37, 23.3648, 19.8232, 378028129040.0),
            "조선": (47.15, 18.6607, 15.1191, 50092494260.0),
            "철강": (66.48, 19.1313, 15.5897, 125807893095.0),
            "통신": (51.22, 33.6455, 30.1038, 1327987472320.0),
            "패션": (30.17, 18.7612, 15.2196, 29340650750.0),
            "헬스케어": (24.4, 20.3554, 16.8138, 940597840600.0),
            "화장품": (90.05, 67.2804, 63.7388, 912566668440.0),
        },
    },
    "3m": {
        "all": {
            "Auto": (61.14, -4.4716, -20.6377, 1514051627310.0),
            "PCB": (39.34, -15.7036, -31.8697, 1174054685720.0),
            "게임": (53.14, 11.7284, -4.4377, 284758699946.0),
            "내수": (59.51, 16.4413, 0.2752, 157774203995.0),
            "디스플레이": (57.45, -2.2603, -18.4265, 300228216880.0),
            "반도체": (52.18, -8.2409, -24.407, 29455741829290.0),
            "방산": (48.16, -12.8562, -29.0223, 1471308016514.0),
            "비철금속": (63.55, -4.5169, -20.683, 575033416169.0),
            "스마트폰": (59.96, -6.0776, -22.2438, 563632764130.0),
            "유통": (56.44, 2.5025, -13.6636, 420851322471.0),
            "음식료": (65.13, 11.0039, -5.1622, 610531693950.0),
            "인터넷": (54.7, 9.2435, -6.9226, 1767838940270.0),
            "조선": (36.21, -9.7658, -25.9319, 1209311437240.0),
            "철강": (68.11, 1.3566, -14.8095, 419407148165.0),
            "통신": (48.82, -6.2403, -22.4064, 1736188454350.0),
            "패션": (36.59, -1.5201, -17.6862, 44854803950.0),
            "헬스케어": (35.67, -4.9337, -21.0998, 1945115094210.0),
            "화장품": (91.17, 40.1223, 23.9562, 2389667670090.0),
        },
        "kospi": {
            "Auto": (72.19, 7.505, -8.6611, 1438036956100.0),
            "PCB": (29.17, -24.0324, -40.1985, 574112359090.0),
            "게임": (69.5, 18.6308, 2.4646, 195122824700.0),
            "내수": (46.88, 10.6303, -5.5358, 128626773170.0),
            "디스플레이": (60.61, 18.4841, 2.3179, 113938248460.0),
            "반도체": (55.95, -11.0543, -27.2205, 27053535827200.0),
            "방산": (48.68, -10.8767, -27.0428, 1409832953850.0),
            "비철금속": (64.83, -2.6164, -18.7825, 225684577070.0),
            "스마트폰": (57.17, -7.4918, -23.6579, 418075463820.0),
            "유통": (60.4, 6.115, -10.0511, 371289615925.0),
            "음식료": (72.31, 11.4357, -4.7304, 532869236900.0),
            "인터넷": (63.4, 12.107, -4.0592, 1389810811230.0),
            "조선": (26.49, -12.8134, -28.9795, 1159218942980.0),
            "철강": (69.75, -5.2309, -21.397, 293599255070.0),
            "통신": (45.81, 2.0624, -14.1037, 408200982030.0),
            "패션": (62.29, 15.1208, -1.0453, 15514153200.0),
            "헬스케어": (49.44, 9.2877, -6.8784, 1004517253610.0),
            "화장품": (92.29, 32.9503, 16.7842, 1477101001650.0),
        },
        "kosdaq": {
            "Auto": (48.71, -17.9452, -34.1113, 76014671210.0),
            "PCB": (43.25, -12.5002, -28.6663, 599942326630.0),
            "게임": (49.36, 10.1356, -6.0305, 89635875246.0),
            "내수": (75.76, 23.9126, 7.7465, 29147430825.0),
            "디스플레이": (56.55, -8.1873, -24.3534, 186289968420.0),
            "반도체": (48.41, -5.4275, -21.5936, 2402206002090.0),
            "방산": (47.75, -14.4397, -30.6058, 61475062664.0),
            "비철금속": (62.41, -6.2062, -22.3723, 349348839099.0),
            "스마트폰": (60.82, -5.6425, -21.8086, 145557300310.0),
            "유통": (52.48, -1.1099, -17.2761, 49561706546.0),
            "음식료": (57.04, 10.5181, -5.6481, 77662457050.0),
            "인터넷": (48.37, 7.161, -9.0051, 378028129040.0),
            "조선": (47.15, -6.3372, -22.5033, 50092494260.0),
            "철강": (66.48, 7.9441, -8.222, 125807893095.0),
            "통신": (51.22, -12.8825, -29.0486, 1327987472320.0),
            "패션": (30.17, -5.6803, -21.8464, 29340650750.0),
            "헬스케어": (24.4, -16.5694, -32.7355, 940597840600.0),
            "화장품": (90.05, 47.2943, 31.1282, 912566668440.0),
        },
    },
}


# (period, market) → sectors[] 에는 있으나 봉투 data[] 에 없는 섹터
# (봉투 쪽 AG-5(구성종목 >= 5) 미달 제외 — kospi 는 F3 의 4종목 섹터 2개 + 패션).
BUBBLE_ONLY: dict[tuple[str, str], frozenset[str]] = {
    ("1w", "all"): frozenset({}),
    ("1w", "kospi"): frozenset({"디스플레이", "스마트폰", "패션"}),
    ("1w", "kosdaq"): frozenset({"패션"}),
    ("1m", "all"): frozenset({}),
    ("1m", "kospi"): frozenset({"디스플레이", "스마트폰", "패션"}),
    ("1m", "kosdaq"): frozenset({"패션"}),
    ("3m", "all"): frozenset({}),
    ("3m", "kospi"): frozenset({"디스플레이", "스마트폰", "패션"}),
    ("3m", "kosdaq"): frozenset({"패션"}),
}


# 봉투 data[] 쪽이 값 대신 reason 기입 null 을 돌려주는 섹터(관찰값, 전 기간 공통):
#   market=all → 패션, 헬스케어 / market=kosdaq → 헬스케어 / market=kospi → 없음
# (kospi 의 패션은 애초 data[] 에 없다 — BUBBLE_ONLY 참조. M3 nullable 스키마의 입력.)
RANKING_NULL_RETURNS: dict[str, frozenset[str]] = {
    "all": frozenset({"패션", "헬스케어"}),
    "kosdaq": frozenset({"헬스케어"}),
    "kospi": frozenset(),
}


# ---------------------------------------------------------------------------
# 1) 특성화: 9조합 현재 출력 고정
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("period", PERIODS)
def test_bubble_characterization_snapshot(client: Any, period: str, market: str) -> None:
    """9조합 각각에서 섹터명 집합과 4개 메트릭 현재값을 리터럴에 고정한다 (M4 에서 뒤집힌다)."""
    body = _get_bubble(client, period, market)
    expected = EXPECTED[period][market]

    assert body["date"] == AS_OF
    assert body["as_of_date"] == AS_OF
    assert body["period"] == period
    assert body["market"] == market
    assert len(body["sectors"]) == len(expected), (
        f"{period}/{market}: sectors 수 {len(body['sectors'])} != {len(expected)}"
    )

    got = {s["name"]: s for s in body["sectors"]}
    assert set(got) == set(expected), (
        f"{period}/{market}: 섹터명 집합이 고정값과 다르다: "
        f"추가={set(got) - set(expected)} 누락={set(expected) - set(got)}"
    )
    for name, (rs_avg, excess_return, period_return, trading_value) in expected.items():
        s = got[name]
        assert s["rs_avg"] == pytest.approx(rs_avg, abs=1e-6), f"{period}/{market}/{name}: rs_avg"
        assert s["excess_return"] == pytest.approx(excess_return, abs=1e-6), (
            f"{period}/{market}/{name}: excess_return")
        assert s["period_return"] == pytest.approx(period_return, abs=1e-6), (
            f"{period}/{market}/{name}: period_return")
        assert s["trading_value"] == pytest.approx(trading_value, abs=1e-6), (
            f"{period}/{market}/{name}: trading_value")


# ---------------------------------------------------------------------------
# 2) 현재 불일치 기록 — M4에서 뒤집힌다: sectors[] ↔ 봉투 data[] 이름 조인, N 측정
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("period", PERIODS)
def test_bubble_vs_ranking_current_mismatch_N(client: Any, period: str, market: str) -> None:
    """⚠ 현재 불일치 기록 — M4에서 뒤집힌다.

    sectors[] 를 봉투 data[] 와 이름 조인해 4개 필드쌍 불일치를 잰다.
    관찰값: 교집합 전 섹터가 4쌍 전부에서 불일치 → N(완전 일치 섹터 없음) == 18.
    """
    bubble = _get_bubble(client, period, market)
    ranking = _get_ranking(client, period, market)

    bmap = {s["name"]: s for s in bubble["sectors"]}
    dmap = {d["name"]: d for d in ranking["data"]}

    bubble_only = frozenset(bmap) - frozenset(dmap)
    assert bubble_only == BUBBLE_ONLY[(period, market)], (
        f"{period}/{market}: bubble-only 집합이 관찰값과 다르다: {sorted(bubble_only)}"
    )
    assert frozenset(dmap) <= frozenset(bmap), "봉투에만 있는 섹터는 관찰된 적 없다"

    per_pair = {"rs_avg": 0, "excess_return": 0, "trading_value": 0, "period_return": 0}
    mismatching: set[str] = set(bubble_only)  # data[] 에 없으면 모든 쌍이 불일치
    for name, b in bmap.items():
        d = dmap.get(name)
        if d is None:
            continue
        pairs = {
            "rs_avg": (b["rs_avg"], d["rs_avg"]["value"]),
            "excess_return": (b["excess_return"], d["excess_returns"][period]["value"]),
            "trading_value": (b["trading_value"], d["trading_value"][period]["value"]),
            "period_return": (b["period_return"], d["returns"][period]["value"]),
        }
        sector_mismatch = False
        for key, (bv, dv) in pairs.items():
            if _is_mismatch(bv, dv):
                per_pair[key] += 1
                sector_mismatch = True
        if sector_mismatch:
            mismatching.add(name)

    n_intersection = len(bmap) - len(bubble_only)
    # 교집합 내 전 섹터가 4쌍 전부에서 불일치한다(관찰값).
    for key, count in per_pair.items():
        assert count == n_intersection, (
            f"{period}/{market}: {key} 불일치 {count} != 교집합 {n_intersection}"
        )
    # N: 완전히 일치하는 섹터가 하나도 없다 — sectors[] 전원 불일치.
    assert len(mismatching) == N_TOTAL, (
        f"{period}/{market}: N={len(mismatching)} != {N_TOTAL}"
    )
    assert mismatching == set(bmap)


# ---------------------------------------------------------------------------
# 3) 봉투 쪽 reason-null 관찰 고정 (M3 nullable 스키마 입력)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market", MARKETS)
def test_ranking_null_returns_names_pinned(client: Any, market: str) -> None:
    """봉투 data[] 에서 returns/excess_returns 값이 null(reason 기입)인 섹터를 고정한다.

    관찰: all → 패션·헬스케어, kosdaq → 헬스케어, kospi → 없음(패션은 data[] 밖).
    """
    expected_null = RANKING_NULL_RETURNS[market]
    for period in PERIODS:
        ranking = _get_ranking(client, period, market)
        null_returns = {d["name"] for d in ranking["data"]
                        if d["returns"][period]["value"] is None}
        null_excess = {d["name"] for d in ranking["data"]
                       if d["excess_returns"][period]["value"] is None}
        assert null_returns == expected_null, (
            f"{period}/{market}: returns null 집합 {sorted(null_returns)} "
            f"!= 관찰값 {sorted(expected_null)}"
        )
        assert null_excess == expected_null, (
            f"{period}/{market}: excess_returns null 집합이 returns null 집합과 다르다"
        )
