# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M2 — 섹터 집계 코어 (규칙 AG-1 ~ AG-7).

담당 AC
-------
* **AC-SAG-002** [게이팅 — 집계 픽스처 · 파생 규칙] 시총가중 회귀 + F12-b / F12-c 집합 동등
* **AC-SAG-003**(응답 절) · **AC-SAG-004** · **AC-SAG-005** · **AC-SAG-006** ·
  **AC-SAG-008** · **AC-SAG-009** · **AC-SAG-010**(응답 절)

§8.3 파생 규칙 원칙 [HARD]
--------------------------
게이팅 기대값을 숫자로 적지 않는다. 테스트 내부 **참조 구현**이 픽스처 DB 에서 원시
컬럼을 직접 읽어 규칙을 다시 구현하며 **프로덕션 경로를 호출하지 않는다**(Lesson #9 —
단언의 양변이 같은 표현식에서 오면 무효). 참조는 가중 규칙만이 아니라 **제외·null 처리
규칙(AG-3 / AG-4 / AG-5 / AG-7)까지** 프로덕션과 동일하게 재현한다.

`as_of` 명시 고정 [HARD · §8.4 규약 8]
--------------------------------------
게이팅 호출은 전부 ``as_of="2026-08-11"`` 을 **명시 인자**로 전달한다. 구현 기본값
(``date.today()``)에 의존하면 W33 이 마감되는 2026-08-17 부터 코드 변경 0줄에 붉어진다.

registry 고정 [HARD]
--------------------
``my_chart.registry.get_sector_registry()`` 는 경로 인자가 없고 모듈 수준에 캐시한다.
집계 진입점에 ``registry_path`` 를 **명시**하고, 캐시를 타는 경로(유효 유니버스 산출)는
``SECTORMAP_PATH`` 패치로 함께 고정한다.
"""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import yaml

from my_chart.analysis.aggregate_types import REASON_INSUFFICIENT, REASON_MISSING

# ---------------------------------------------------------------------------
# 경로 · 상수
# ---------------------------------------------------------------------------

AGG_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = str(AGG_DIR / "weekly.db")
DAILY_DB = str(AGG_DIR / "daily.db")
REGISTRY = str(AGG_DIR / "registry.xlsx")

#: 참조 구현이 쓰는 상한. 프로덕션 상수를 **import 하지 않고** 독립 리터럴로 둔다
#: (§8.3 — 단언의 양변이 같은 표현식에서 오면 무효). 프로덕션 상수와의 일치는
#: `test_reference_cap_matches_production_constant` 가 별도로 단언한다.
WEIGHT_CAP = 0.10

AS_OF = "2026-08-11"                 # §8.4 규약 7 — 사용자 결정으로 고정
ANCHOR_1M = "2026-07-10"             # anchor(t, 28) — MANIFEST `f12_anchor_1m`
MIN_MEMBERS = 5                      # AG-5
MIN_CAP_VALID = 5                    # AG-4
COV_NULL = 0.50                      # AG-7
COV_LOW_CONF = 0.80                  # AG-7
F12B_DELTA = 0.005                   # 0.5%p (소수 스케일)
F12B_MIN_SECTORS = 3                 # AC-SAG-002 크기 절 임계
F12C_MIN_SECTORS = 5                 # AC-SAG-002 순위 절 임계
NH_THRESHOLD = 0.02


def _cap_eff(n: int, cap: float = WEIGHT_CAP) -> float:
    """INV-CAP-1 — 유효 상한. 기대값은 전부 이 함수를 경유한다(리터럴 `0.10` 금지)."""
    return max(cap, 1.0 / n)


# ---------------------------------------------------------------------------
# 참조 구현 (§8.3) — 프로덕션 미import
# ---------------------------------------------------------------------------

def test_reference_cap_matches_production_constant() -> None:
    """참조의 독립 상한 리터럴이 프로덕션 단일 정의 지점과 일치한다(spec.md D3)."""
    from my_chart.analysis.aggregate_types import WEIGHT_CAP as PROD_CAP

    assert WEIGHT_CAP == PROD_CAP


def _ref_capped_weights(caps: list[float], cap: float = WEIGHT_CAP) -> list[float]:
    """상한 재배분 시총가중(동결형). `cap_eff = max(cap, 1/n)`."""
    n = len(caps)
    total = sum(caps)
    if n == 0 or total <= 0:
        return []
    raw = [c / total for c in caps]
    cap_eff = _cap_eff(n, cap)
    w = list(raw)
    frozen: set[int] = set()
    for _ in range(min(n, 20)):
        over = [i for i in range(n) if i not in frozen and w[i] > cap_eff + 1e-15]
        if not over:
            break
        for i in over:
            w[i] = cap_eff
            frozen.add(i)
        free = [i for i in range(n) if i not in frozen]
        s = sum(raw[i] for i in free)
        if not free or s <= 0:
            break
        rem = 1.0 - cap_eff * len(frozen)
        for i in free:
            w[i] = raw[i] * rem / s
    return w


@pytest.fixture(scope="module")
def fixture_raw() -> dict:
    """픽스처 원시 컬럼 — 프로덕션 모듈을 거치지 않고 DB/xlsx 에서 직접 읽는다."""
    reg = pd.read_excel(REGISTRY, header=8).rename(
        columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg["Code"] = reg["Code"].astype(str).str.zfill(6)
    reg = reg[~reg["Code"].duplicated(keep="first")]          # UN-4 dedup
    sector_of = dict(zip(reg["Name"], reg["산업명(대)"]))

    dconn = sqlite3.connect(DAILY_DB)
    try:
        caps = dict(dconn.execute("SELECT name, market_cap FROM stock_meta").fetchall())
        meta_names = {r[0] for r in dconn.execute("SELECT name FROM stock_meta")}
        daily_max = dict(dconn.execute(
            "SELECT Name, MAX(Date) FROM stock_prices GROUP BY Name").fetchall())
    finally:
        dconn.close()

    wconn = sqlite3.connect(WEEKLY_DB)
    try:
        latest = {r[0]: r[1:] for r in wconn.execute(
            "SELECT Name, Close, MAX52, SMA10, SMA40 FROM stock_prices WHERE Date = ?",
            (AS_OF,)).fetchall()}
        base_1m = dict(wconn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (ANCHOR_1M,)).fetchall())
        rs = dict(wconn.execute(
            "SELECT Name, RS_12M_Rating FROM relative_strength WHERE Date = ?",
            (AS_OF,)).fetchall())
    finally:
        wconn.close()

    # 유효 유니버스(UN-3) — registry ∩ stock_meta ∩ 최신바 가격. stale 종목은
    # 픽스처에 없음이 MANIFEST F13 으로 보장되므로 3중 교집합으로 충분하다.
    valid = {n for n in sector_of if n in meta_names and n in latest and n in daily_max}

    members: dict[str, list[str]] = defaultdict(list)
    for n in sorted(valid):
        members[str(sector_of[n])].append(n)

    return {
        "members": dict(members), "caps": caps, "latest": latest,
        "base_1m": base_1m, "rs": rs,
    }


def _ref_return_1m(raw: dict, name: str) -> float | None:
    """`Close(t) / Close(anchor(t, 28)) − 1` — % 스케일 아님(소수)."""
    row = raw["latest"].get(name)
    b = raw["base_1m"].get(name)
    if row is None or row[0] is None or b is None or float(b) == 0:
        return None
    return float(row[0]) / float(b) - 1.0


def _ref_coverage(raw: dict, names: list[str]) -> float:
    """최상위 `coverage_ratio = min(coverage.*)` (O-A6). trading_value 는 미산출."""
    n = len(names)
    rs_ok = sum(1 for x in names if raw["rs"].get(x) is not None)
    nh_ok = 0
    stage_ok = 0
    chg_ok = 0
    for x in names:
        row = raw["latest"].get(x)
        if row is None:
            continue
        close, max52, sma10, _sma40 = row
        if close is not None and max52 is not None and float(max52) > 0:
            nh_ok += 1
        if sma10 is not None:
            stage_ok += 1
        if _ref_return_1m(raw, x) is not None:
            chg_ok += 1
    return min(rs_ok, nh_ok, stage_ok, chg_ok) / n if n else 0.0


def _ref_sector_values(raw: dict, equal_weight: bool = False) -> tuple[dict, set]:
    """§8.3 제외·null 처리 계약을 그대로 재현한 섹터별 1M 시총가중 값.

    Returns:
        ``({섹터: 값(소수)}, {null 로 판정된 섹터})`` — AG-5 통과 섹터만 대상.
    """
    values: dict[str, float] = {}
    nulls: set[str] = set()
    for sector, names in raw["members"].items():
        if len(names) < MIN_MEMBERS:                      # AG-5 — data[] 에서 빠진다
            continue
        rets = {x: _ref_return_1m(raw, x) for x in names}
        avail = [x for x in names if rets[x] is not None]
        cap_members = [x for x in avail
                       if raw["caps"].get(x) is not None and raw["caps"][x] > 0]
        if len(cap_members) < MIN_CAP_VALID:              # AG-4
            nulls.add(sector)
            continue
        if _ref_coverage(raw, names) < COV_NULL:          # AG-7
            nulls.add(sector)
            continue
        if equal_weight:                                  # mut_equal_weight 변형
            values[sector] = sum(rets[x] for x in avail) / len(avail)
            continue
        w = _ref_capped_weights([float(raw["caps"][x]) for x in cap_members])
        values[sector] = sum(wi * rets[x] for wi, x in zip(w, cap_members))
    return values, nulls


def _f12_sets(raw: dict) -> tuple[list[str], list[str]]:
    """F12-b / F12-c 산출 — §8.2 F12 · R-C8 의 **픽스처 속성** 정의를 그대로 쓴다.

    범위는 `market=all` · AG-5 통과 · AG-4 통과 · AG-7 을 **1M 수익률 가용률**에 적용한
    집합이다(§8.2 F12). 프로덕션의 AG-7 은 최상위 `coverage_ratio = min(coverage.*)` 에
    걸리므로 RS 커버리지가 낮은 섹터에서 두 범위가 갈릴 수 있다 — F12 는 "픽스처가
    검출력을 갖는가"를 규정하는 요건이고 AC-SAG-048 이 MANIFEST 를 이 정의로 검증했으므로,
    본 절도 같은 정의를 쓴다. 프로덕션 대조는 위 `_ref_sector_values` 가 담당한다.
    """
    cap_vals: dict[str, float] = {}
    eq_vals: dict[str, float] = {}
    for sector, names in raw["members"].items():
        if len(names) < MIN_MEMBERS:
            continue
        rets = {x: _ref_return_1m(raw, x) for x in names}
        avail = [x for x in names if rets[x] is not None]
        if not avail or len(avail) / len(names) < COV_NULL:
            continue
        cap_members = [x for x in avail
                       if raw["caps"].get(x) is not None and raw["caps"][x] > 0]
        if len(cap_members) < MIN_CAP_VALID:
            continue
        w = _ref_capped_weights([float(raw["caps"][x]) for x in cap_members])
        cap_vals[sector] = sum(wi * rets[x] for wi, x in zip(w, cap_members))
        eq_vals[sector] = sum(rets[x] for x in avail) / len(avail)

    def _ranks(vals: dict[str, float]) -> dict[str, int]:
        return {s: i + 1 for i, s in enumerate(sorted(vals, key=lambda x: (-vals[x], x)))}

    r_cap, r_eq = _ranks(cap_vals), _ranks(eq_vals)
    f12b = sorted(s for s in cap_vals if abs(cap_vals[s] - eq_vals[s]) >= F12B_DELTA)
    f12c = sorted(s for s in cap_vals if r_cap[s] != r_eq[s])
    return f12b, f12c


@pytest.fixture(scope="module")
def manifest() -> dict:
    text = (AGG_DIR / "MANIFEST.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    assert blocks, "MANIFEST.md 에 기계 판독 ```yaml 블록이 없다"
    return yaml.safe_load(blocks[0])


@pytest.fixture(scope="module")
def production():
    """프로덕션 집계 산출물 — registry 를 픽스처로 고정하고 `as_of` 를 명시한다."""
    from my_chart.analysis.sector_metrics import compute_sector_aggregates

    with patch("my_chart.registry.SECTORMAP_PATH", REGISTRY), \
            patch("my_chart.registry._df_sector", None), \
            patch("my_chart.registry._df_stock", None):
        return compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY,
            market="all", as_of=AS_OF)


# ---------------------------------------------------------------------------
# AC-SAG-002 — 시총가중 회귀 [게이팅]
# ---------------------------------------------------------------------------

def test_ac_sag_002_production_matches_independent_reference(production, fixture_raw) -> None:
    """AG-5 통과 전 섹터에서 프로덕션 값 == 독립 참조값 (`1e-9` 이내).

    대조 집합의 제한(§8.3) — 값 단언은 **프로덕션이 non-null 로 보고한 섹터**에 한한다.
    제외 규칙 자체의 불일치는 아래 집합 동등 절이 잡는다.
    """
    ref, _nulls = _ref_sector_values(fixture_raw)
    prod = {a.name: a.returns["1m"].value for a in production.aggregates
            if a.returns["1m"].value is not None}

    assert prod, "프로덕션이 1M 값을 하나도 산출하지 못했다"
    missing_ref = sorted(set(prod) - set(ref))
    assert missing_ref == [], f"프로덕션만 값을 낸 섹터: {missing_ref}"
    for sector, value in sorted(prod.items()):
        # 프로덕션은 % 스케일, 참조는 소수 스케일이다.
        assert value == pytest.approx(ref[sector] * 100, abs=1e-9), (
            f"{sector}: 프로덕션 {value!r} != 참조 {ref[sector] * 100!r}")


def test_ac_sag_002_null_sector_set_equality(production, fixture_raw) -> None:
    """참조가 null 로 판정한 섹터 집합 == 프로덕션이 null 로 보고한 섹터 집합 (§8.3)."""
    _ref, ref_nulls = _ref_sector_values(fixture_raw)
    prod_nulls = {a.name for a in production.aggregates
                  if a.returns["1m"].value is None}
    assert prod_nulls == ref_nulls, (
        f"프로덕션 null {sorted(prod_nulls)} != 참조 null {sorted(ref_nulls)}")
    assert ref_nulls, "null 판정 섹터가 하나도 없다 — AG-4/AG-7 분기가 발화하지 않았다"


def test_ac_sag_002_f12b_delta_set_matches_manifest(manifest, fixture_raw) -> None:
    """크기 절 — `|시총가중 − 등가중| >= 0.5%p` 섹터 **집합**이 MANIFEST 와 동등하고 `>= 3`."""
    f12b, _f12c = _f12_sets(fixture_raw)
    expected = sorted(manifest["f12b_delta_ge_50bp_sectors_1m"])
    assert f12b == expected, f"F12-b 집합 불일치\n실측 {f12b}\nMANIFEST {expected}"
    assert len(f12b) >= F12B_MIN_SECTORS, f"F12-b {len(f12b)} < {F12B_MIN_SECTORS}"


def test_ac_sag_002_f12c_rank_shift_set_matches_manifest(manifest, fixture_raw) -> None:
    """순위 절 — 시총가중 순위 != 등가중 순위인 섹터 **집합**이 MANIFEST 와 동등하고 `>= 5`."""
    _f12b, f12c = _f12_sets(fixture_raw)
    expected = sorted(manifest["f12c_rank_shifted_sectors_1m"])
    assert f12c == expected, f"F12-c 집합 불일치\n실측 {f12c}\nMANIFEST {expected}"
    assert f12c, "F12-c 가 공집합이다 — 시총가중이 순위를 전혀 바꾸지 않았다"
    assert len(f12c) >= F12C_MIN_SECTORS, f"F12-c {len(f12c)} < {F12C_MIN_SECTORS}"


def test_ac_sag_002_mut_equal_weight_is_detectable(production, fixture_raw) -> None:
    """대조 단언 `mut_equal_weight` 의 **검출력 실측**(§8.4 규약 10).

    가중을 `sum/n` 등가중으로 되돌린 변형에서 프로덕션 값과 어긋나는 섹터가 최소 1개
    나와야 한다 — 그렇지 않으면 이 AC 는 무게이팅이다(D16 이 정확히 그 상태였다).
    실제 되돌림 실증은 progress.md §E.2 에 verbatim 으로 기록한다.
    """
    ref_cap, _ = _ref_sector_values(fixture_raw)
    ref_eq, _ = _ref_sector_values(fixture_raw, equal_weight=True)
    prod = {a.name: a.returns["1m"].value for a in production.aggregates
            if a.returns["1m"].value is not None}

    diverging = [s for s in prod
                 if abs(prod[s] - ref_eq[s] * 100) > 1e-9]
    assert len(diverging) >= F12B_MIN_SECTORS, (
        f"등가중 변형과 어긋나는 섹터가 {len(diverging)}개뿐 — 무게이팅이다")
    # 두 참조가 실제로 다른 값을 낸다(변형이 no-op 이 아님).
    assert any(abs(ref_cap[s] - ref_eq[s]) >= F12B_DELTA for s in ref_cap)


# ---------------------------------------------------------------------------
# 순수 합성 섹터 헬퍼 — AC-SAG-003 ~ 010
# ---------------------------------------------------------------------------

def _member(name: str, cap: float | None, ret: float | None,
            rs: float | None = 50.0, nh: bool | None = False,
            stage2: bool | None = False):
    from my_chart.analysis.sector_metrics import _Member

    return _Member(name=name, market_cap=cap,
                   returns={"1w": ret, "1m": ret, "3m": ret},
                   rs=rs, nh=nh, stage2=stage2)


def _aggregate(members: list):
    from my_chart.analysis.sector_metrics import _aggregate_members

    return _aggregate_members("합성", members)[0]


# ---------------------------------------------------------------------------
# AC-SAG-003 — 상한 적용 사실의 노출 (응답 절, 규칙 AG-2)
# ---------------------------------------------------------------------------

def test_ac_sag_003_response_exposes_weight_cap_and_capped_members() -> None:
    """12종목 합성 섹터 `[600, 40×11]` — `weight_cap` + `capped_members` 1건, `== cap_eff`."""
    caps = [600.0] + [40.0] * 11
    agg = _aggregate([_member(f"s{i}", c, 1.0) for i, c in enumerate(caps)])
    cap_eff = _cap_eff(12)

    assert agg.weight_cap == WEIGHT_CAP, "응답에 weight_cap 이 실리지 않았다"
    assert len(agg.capped_members) == 1
    top = agg.capped_members[0]
    assert top.name == "s0"
    assert top.raw_weight == pytest.approx(0.5769230769, abs=1e-9)
    assert top.capped_weight == pytest.approx(cap_eff, abs=1e-9)


def test_ac_sag_003_degenerate_contrast_n6_response() -> None:
    """축퇴 대조 — 같은 비율 6종목에서 `capped_weight == cap_eff(6) != weight_cap`."""
    caps = [600.0] + [88.0] * 5
    agg = _aggregate([_member(f"s{i}", c, 1.0) for i, c in enumerate(caps)])
    cap_eff = _cap_eff(6)

    for m in agg.capped_members:
        assert m.capped_weight == pytest.approx(cap_eff, abs=1e-9)
        assert m.capped_weight != pytest.approx(WEIGHT_CAP, abs=1e-3)


# ---------------------------------------------------------------------------
# AC-SAG-004 — 결측 종목 완전 제외 (분모 규칙)
# ---------------------------------------------------------------------------

def test_ac_sag_004_null_returns_are_excluded_not_zero_filled() -> None:
    """10종목 중 3종목 수익률 NULL — 결과가 "NULL→0 치환" 과 **다르고** 커버리지가 0.7."""
    caps = [10.0 + i for i in range(10)]
    rets = [5.0] * 7 + [None, None, None]
    agg = _aggregate([_member(f"s{i}", caps[i], rets[i]) for i in range(10)])

    assert agg.member_count == 10
    assert agg.valid_count == 7
    assert agg.coverage_ratio.value == pytest.approx(0.7)

    # 유효 7종목이 전부 5.0 이므로 재정규화된 가중평균은 정확히 5.0 이다.
    assert agg.returns["1m"].value == pytest.approx(5.0, abs=1e-9)
    # NULL 을 0 으로 접었다면 값이 5.0 보다 작아진다(가중치 합이 1 이므로 최대 5×0.7 미만).
    zero_filled = _aggregate(
        [_member(f"s{i}", caps[i], rets[i] if rets[i] is not None else 0.0)
         for i in range(10)])
    assert zero_filled.returns["1m"].value < 5.0 - 1e-6
    assert agg.returns["1m"].value != pytest.approx(zero_filled.returns["1m"].value)


def test_ac_sag_004_weights_are_renormalized_over_surviving_members() -> None:
    """결측 제외 후 남은 종목의 가중치 합이 1 이다 — 가중평균이 값 범위 안에 든다."""
    caps = [10.0 + i for i in range(10)]
    rets = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, None, None, None]
    agg = _aggregate([_member(f"s{i}", caps[i], rets[i]) for i in range(10)])
    value = agg.returns["1m"].value
    assert 1.0 - 1e-9 <= value <= 7.0 + 1e-9, (
        f"가중치 합이 1 이 아니다 — 값 {value} 가 유효 범위 [1, 7] 밖이다")


# ---------------------------------------------------------------------------
# AC-SAG-005 — NULL market_cap 처리 (규칙 UN-6 / AG-3)
# ---------------------------------------------------------------------------

def _twenty_members(cap_missing: int = 3, chg_null_name: str | None = None) -> list:
    members = []
    for i in range(20):
        cap = None if i < cap_missing else 100.0 + i
        ret = None if f"s{i}" == chg_null_name else 5.0 + i
        members.append(_member(f"s{i}", cap, ret, rs=50.0 + i, nh=(i % 2 == 0),
                               stage2=(i % 3 == 0)))
    return members


def test_ac_sag_005_null_market_cap_excluded_from_cap_weighted_only() -> None:
    """시총 NULL 3종목이 시총가중에서 빠지고 등가중 지표 분모에는 남는다."""
    agg = _aggregate(_twenty_members())
    trimmed = _aggregate(_twenty_members()[3:])          # 3종목을 제거한 픽스처

    assert agg.member_count == 20, "등가중 분모에서 빠졌다"
    assert agg.returns["1m"].value == pytest.approx(
        trimmed.returns["1m"].value, abs=1e-9), "대체값(1.0/중앙값) 부여 흔적이 있다"
    # 등가중 지표는 20종목 기준이므로 17종목 기준과 다르다.
    assert agg.rs_avg.value != pytest.approx(trimmed.rs_avg.value)
    assert agg.rs_avg.value is not None and agg.nh_pct.value is not None
    assert agg.stage2_pct.value is not None


def test_ac_sag_005_cap_coverage_ratio_is_one_when_all_returns_present() -> None:
    """`cap_coverage_ratio == 1.0` — 유효 시총 종목의 수익률이 전부 존재하는 경우."""
    agg = _aggregate(_twenty_members())
    assert agg.cap_coverage_ratio.value == pytest.approx(1.0, abs=1e-12)


def test_ac_sag_005_cap_coverage_ratio_discriminates_the_retired_definition() -> None:
    """판별 절 — 유효 시총 종목 1개의 수익률만 NULL 로 바꾸면 `< 1.0` 으로 떨어진다.

    폐기된 해석(`유효시총합 / 전체시총합`)은 이 변형에서도 `1.0` 을 유지하므로 이 절이
    두 해석을 판별한다(D18).
    """
    target = "s5"
    agg = _aggregate(_twenty_members(chg_null_name=target))
    caps = {f"s{i}": 100.0 + i for i in range(3, 20)}     # 유효 시총 종목만
    expected = 1 - caps[target] / sum(caps.values())

    assert agg.cap_coverage_ratio.value == pytest.approx(expected, abs=1e-9)
    assert agg.cap_coverage_ratio.value < 1.0


# ---------------------------------------------------------------------------
# AC-SAG-006 — 유효 시총 종목 부족 (규칙 AG-4)
# ---------------------------------------------------------------------------

def test_ac_sag_006_insufficient_cap_valid_members_null_cap_weighted_fields() -> None:
    """유효 시총 종목 3개(최소 5 미만) — 시총가중 null + `insufficient`, 등가중은 값 유지."""
    members = [_member(f"s{i}", None if i >= 3 else 100.0 + i, 5.0 + i)
               for i in range(10)]
    agg = _aggregate(members)

    assert agg.cap_weighted_available is False
    assert agg.returns["1m"].value is None
    assert agg.returns["1m"].reason == REASON_INSUFFICIENT
    assert agg.effective_n.value is None
    assert agg.effective_n.reason == REASON_INSUFFICIENT
    # 등가중 지표는 값을 갖는다.
    assert agg.rs_avg.value is not None
    assert agg.nh_pct.value is not None
    assert agg.stage2_pct.value is not None
    assert agg.member_count == 10


# ---------------------------------------------------------------------------
# AC-SAG-008 — 커버리지 필드 동반 (불변식 AG-6)
# ---------------------------------------------------------------------------

def test_ac_sag_008_every_entry_carries_the_four_coverage_fields(production) -> None:
    """`data[]` 의 **모든** 항목이 4개 필드를 갖는다(누락 0건)."""
    assert production.aggregates, "data[] 가 비었다"
    for a in production.aggregates:
        assert isinstance(a.member_count, int) and a.member_count > 0, a.name
        assert a.valid_count is not None, f"{a.name}: valid_count 누락"
        assert a.coverage_ratio is not None, f"{a.name}: coverage_ratio 누락"
        assert a.cap_coverage_ratio is not None, f"{a.name}: cap_coverage_ratio 누락"
        # 지표별 버킷(O-A6)도 동반한다.
        assert a.coverage is not None and a.valid_counts is not None, a.name


def test_ac_sag_008_top_level_coverage_ratio_is_the_metric_minimum() -> None:
    """최상위 `coverage_ratio == min(coverage.*)` — 한 지표만 비어도 행 전체가 낮아진다."""
    members = [_member(f"s{i}", 100.0 + i, 5.0, rs=None if i < 4 else 50.0)
               for i in range(20)]
    agg = _aggregate(members)
    assert agg.coverage.rs == pytest.approx(0.8)
    assert agg.coverage.chg == pytest.approx(1.0)
    assert agg.coverage_ratio.value == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# AC-SAG-009 — 커버리지 하한 (규칙 AG-7)
# ---------------------------------------------------------------------------

def _sector_with_chg_coverage(valid: int, total: int = 20):
    members = [_member(f"s{i}", 100.0 + i, 5.0 if i < valid else None)
               for i in range(total)]
    return _aggregate(members)


@pytest.mark.parametrize("valid,ratio,expect_value,expect_low_conf", [
    (19, 0.95, True, False),
    (15, 0.75, True, True),
    (9, 0.45, False, False),
])
def test_ac_sag_009_coverage_thresholds(valid, ratio, expect_value, expect_low_conf) -> None:
    """0.95 → 값 + 플래그 없음 / 0.75 → 값 + `low_confidence` / 0.45 → null + `insufficient`."""
    agg = _sector_with_chg_coverage(valid)
    assert agg.coverage_ratio.value == pytest.approx(ratio)
    assert agg.low_confidence is expect_low_conf
    if expect_value:
        assert agg.returns["1m"].value is not None
    else:
        assert agg.returns["1m"].value is None
        assert agg.returns["1m"].reason == REASON_INSUFFICIENT


def test_ac_sag_009_boundaries_are_inclusive() -> None:
    """경계 — 0.80 정확히는 플래그 없음, 0.50 정확히는 값 유지(`< 0.50` 만 null)."""
    at_080 = _sector_with_chg_coverage(16)
    at_050 = _sector_with_chg_coverage(10)

    assert at_080.coverage_ratio.value == pytest.approx(0.80)
    assert at_080.low_confidence is False, "0.80 정확히에 low_confidence 가 붙었다"

    assert at_050.coverage_ratio.value == pytest.approx(0.50)
    assert at_050.returns["1m"].value is not None, "0.50 정확히에서 값이 null 이 됐다"
    assert at_050.low_confidence is True


def test_ac_sag_009_all_missing_returns_report_missing_not_insufficient() -> None:
    """E1 — 전원 수익률 NULL 이면 `missing`(원천 없음)이며 `insufficient` 가 아니다(§9.1)."""
    agg = _aggregate([_member(f"s{i}", 100.0 + i, None) for i in range(10)])
    assert agg.returns["1m"].value is None
    assert agg.returns["1m"].reason == REASON_MISSING
    assert agg.coverage_ratio.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# AC-SAG-010 — effective_n (응답 절)
# ---------------------------------------------------------------------------

def test_ac_sag_010_response_carries_effective_n(production) -> None:
    """시총가중이 가능한 전 섹터에서 `effective_n` 이 값을 갖고 `<= member_count` 다."""
    scored = [a for a in production.aggregates if a.cap_weighted_available]
    assert scored, "시총가중 가능한 섹터가 없다"
    for a in scored:
        assert a.effective_n.value is not None, f"{a.name}: effective_n 누락"
        assert a.effective_n.value <= a.member_count + 1e-9, (
            f"{a.name}: effective_n {a.effective_n.value} > n {a.member_count}")


def test_ac_sag_010_response_effective_n_matches_synthetic_literal() -> None:
    """25종목 합성 `[3000, 100×24]` — 응답 `effective_n == 160/7`."""
    caps = [3000.0] + [100.0] * 24
    agg = _aggregate([_member(f"s{i}", c, 1.0) for i, c in enumerate(caps)])
    assert agg.effective_n.value == pytest.approx(160 / 7, abs=1e-9)
