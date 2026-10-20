"""SPEC-RS-REBALANCE-001 M2 — `RS_12M_Rating` IBD식(AC-RSR-005)과 섹터 가중치 불변(AC-RSR-016).

AC-RSR-005 기대값은 research.md R10에서 독립 계산해 고정한 리터럴이다. 테스트 안에서
IBD식을 다시 계산해 비교하지 않는다(같은 식 양변 금지). `RS_6M/3M/1M_Rating` 불변
(AC-RSR-006)은 `tests/test_rsr_characterization.py`의 골든 테스트가 맡는다.
"""

from __future__ import annotations

import pytest

from my_chart.db import weekly
from tests.rsr_fixtures import make_weekly_db, price_row, read_rs, registry

_DATE = "2026-01-02"

# research.md R10 입력 (원시 수익률, 소수 비율).
_R10 = {
    "A": dict(RS_1M=-0.10, RS_3M=1.00, RS_6M=1.00, RS_9M=1.00, RS_12M=1.000),
    "B": dict(RS_1M=0.00, RS_3M=0.00, RS_6M=0.50, RS_9M=1.25, RS_12M=2.375),
    "C": dict(RS_1M=0.50, RS_3M=0.10, RS_6M=0.10, RS_9M=0.10, RS_12M=0.100),
    "D": dict(RS_1M=0.05, RS_3M=0.20, RS_6M=0.30, RS_9M=0.40, RS_12M=0.500),
}

# research.md R10 "IBD 비율식" 열 — 손으로 고정한 기대값.
# 대조(같은 표의 다른 열): 현행식 A100/B50/C25/D75, 차분식·12M 단독 A75/B100/C25/D50.
_IBD_EXPECTED = {"A": 100.0, "B": 75.0, "C": 25.0, "D": 50.0}


@pytest.fixture
def r10_db(tmp_path, monkeypatch):
    monkeypatch.setattr(weekly, "REFERENCE_STOCK", "A")
    monkeypatch.setattr(
        weekly,
        "get_stock_registry",
        lambda: registry(("000010", "A"), ("000020", "B"), ("000030", "C"), ("000040", "D")),
    )
    rows = [price_row(name, _DATE, **vals) for name, vals in _R10.items()]
    return make_weekly_db(tmp_path, rows)


def test_ac_rsr_005_rs_12m_rating_is_ratio_based_ibd_percentile(r10_db):
    weekly.generate_rs_db(db_name=r10_db)

    df = read_rs(r10_db).set_index("Name")
    assert df["RS_12M_Rating"].to_dict() == _IBD_EXPECTED


def test_ac_rsr_016_sector_composite_weights_unchanged():
    from my_chart.analysis.sector_metrics import _COMPOSITE_WEIGHTS

    assert _COMPOSITE_WEIGHTS == {"1w": 0.30, "1m": 0.40, "3m": 0.30}
